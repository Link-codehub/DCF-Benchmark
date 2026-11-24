#!/usr/bin/env python3
"""
Monte Carlo DCF simulator for MSFT valuation.
Usage: python3 simulate.py --input inputs.json --model model.xlsx --output simulation.json

Samples 4 drivers per path with Gaussian copula + triangular marginals.
Each path is independently reproducible. See memo.md for full documentation.
"""

import argparse
import json
import math
import numpy as np
from scipy import stats
import openpyxl
import sys
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    seed = 1830
    n_min = 5000

    # ── load model assumptions ──
    wb = openpyxl.load_workbook(args.model, data_only=False)
    ws_a = wb['Assumptions']
    assumptions = {}
    for row in ws_a.iter_rows(min_row=2, max_row=ws_a.max_row, values_only=True):
        if row[0] is not None:
            assumptions[row[0]] = row[1]

    tax_rate = float(assumptions['tax_rate'])
    terminal_growth = float(assumptions['terminal_growth'])
    net_debt = float(assumptions['net_debt'])
    cash_and_inv = float(assumptions['cash_and_investments'])
    diluted_shares = float(assumptions['diluted_shares'])
    fy24_revenue = float(assumptions['fy24_revenue'])
    fy24_nwc = float(assumptions['fy24_nwc'])
    base_growth = float(assumptions['initial_growth'])
    base_margin = float(assumptions['steady_ebit_margin'])
    base_da_r = float(assumptions['da_to_revenue'])
    base_capex_r = float(assumptions['capex_to_revenue'])
    nwc_r = float(assumptions['nwc_to_revenue'])

    # Base reinvestment intensity for reference: capex_r + ΔNWC_implied − da_r
    # In steady-state: ΔNWC/rev ≈ nwc_r * g/(1+g)
    base_ri = base_capex_r + nwc_r * base_growth / (1.0 + base_growth) - base_da_r

    # ── Driver definitions ──
    drivers = {
        'revenue_growth': {
            'distribution': 'triangular',
            'parameters': {'min': 0.03, 'mode': 0.14, 'max': 0.28},
            'unit': 'decimal fraction',
            'bounds': [0.03, 0.28]
        },
        'ebit_margin': {
            'distribution': 'triangular',
            'parameters': {'min': 0.35, 'mode': 0.4464, 'max': 0.52},
            'unit': 'decimal fraction',
            'bounds': [0.35, 0.52]
        },
        'reinvestment_intensity': {
            'distribution': 'triangular',
            'parameters': {'min': 0.03, 'mode': round(base_ri, 4), 'max': 0.25},
            'unit': 'decimal fraction of annual revenue',
            'bounds': [0.03, 0.25]
        },
        'discount_rate': {
            'distribution': 'triangular',
            'parameters': {'min': 0.055, 'mode': 0.08, 'max': 0.12},
            'unit': 'decimal fraction',
            'bounds': [0.055, 0.12]
        }
    }

    # ── Target dependence matrix (Gaussian copula) ──
    ordered_names = ['revenue_growth', 'ebit_margin', 'reinvestment_intensity', 'discount_rate']
    target_corr = np.array([
        [1.00, 0.50, 0.40, 0.10],
        [0.50, 1.00, 0.10, -0.05],
        [0.40, 0.10, 1.00, 0.15],
        [0.10, -0.05, 0.15, 1.00]
    ], dtype=float)

    dependence = {
        'ordered_names': ordered_names,
        'matrix': target_corr.tolist(),
        'type': 'Gaussian_copula',
        'note': 'Cholesky-decomposed multivariate normal mapped via inverse-CDF to triangular marginals'
    }

    # Cholesky
    try:
        L = np.linalg.cholesky(target_corr)
    except np.linalg.LinAlgError:
        # Add small ridge if not PD
        eigvals = np.linalg.eigvalsh(target_corr)
        if eigvals[0] <= 0:
            target_corr += np.eye(4) * (abs(eigvals[0]) + 1e-6)
            L = np.linalg.cholesky(target_corr)
            dependence['matrix'] = target_corr.tolist()
            dependence['note'] += '; ridge-adjusted for numerical PD'

    rng = np.random.default_rng(seed)

    # ── Helper: triangular PPF for scipy ──
    def triang_ppf(u, loc, scale, c):
        return stats.triang.ppf(u, c=c, loc=loc, scale=scale)

    # Pre-compute distribution parameters
    dist_params = []
    for name in ordered_names:
        d = drivers[name]
        lo, hi = d['bounds']
        scale = hi - lo
        mode_val = d['parameters']['mode']
        c = (mode_val - lo) / scale
        dist_params.append((name, lo, scale, c))

    # ── Generate samples ──
    batch_size = max(n_min * 3, 20000)  # oversample to handle rejects
    n_drawn = 0
    n_rejected = 0
    trials = []

    while len(trials) < n_min:
        remaining = n_min - len(trials)
        draw_n = max(remaining * 3, 5000)

        # Independent standard normals
        z = rng.standard_normal((4, draw_n))
        # Correlate
        z_corr = L @ z
        # To uniforms
        u = stats.norm.cdf(z_corr)

        for i in range(draw_n):
            if len(trials) >= n_min:
                break

            n_drawn += 1

            # Inverse transform each marginal
            g = triang_ppf(u[0, i], dist_params[0][1], dist_params[0][2], dist_params[0][3])
            m = triang_ppf(u[1, i], dist_params[1][1], dist_params[1][2], dist_params[1][3])
            ri = triang_ppf(u[2, i], dist_params[2][1], dist_params[2][2], dist_params[2][3])
            dr = triang_ppf(u[3, i], dist_params[3][1], dist_params[3][2], dist_params[3][3])

            # Reject if discount_rate <= terminal_growth (WACC > g requirement)
            if dr <= terminal_growth:
                n_rejected += 1
                continue

            # Build 5-year trajectory
            traj = []
            prev_rev = fy24_revenue
            for yr in range(1, 6):
                rev = prev_rev * (1.0 + g)
                ebit = rev * m
                reinv = rev * ri
                fcff = ebit * (1.0 - tax_rate) - reinv
                df = 1.0 / (1.0 + dr) ** yr

                traj.append({
                    'year': yr,
                    'revenue': round(rev, 2),
                    'ebit': round(ebit, 2),
                    'reinvestment': round(reinv, 2),
                    'fcff': round(fcff, 2),
                    'discount_factor': round(df, 6)
                })
                prev_rev = rev

            # Terminal value using Gordon growth with path discount_rate
            fcff_y5 = traj[4]['fcff']
            tv_undisc = fcff_y5 * (1.0 + terminal_growth) / (dr - terminal_growth)
            pv_tv = tv_undisc * traj[4]['discount_factor']

            # PV of FCFFs
            pv_fcffs = sum(t['fcff'] * t['discount_factor'] for t in traj)

            # Enterprise value → equity value → per share
            ev = pv_fcffs + pv_tv
            eq = ev + cash_and_inv - net_debt
            vps = eq / diluted_shares

            trial = {
                'path_id': len(trials) + 1,
                'revenue_growth': round(float(g), 8),
                'ebit_margin': round(float(m), 8),
                'reinvestment_intensity': round(float(ri), 8),
                'discount_rate': round(float(dr), 8),
                'value_per_share': round(float(vps), 2),
                'trajectory': traj
            }
            trials.append(trial)

    # ── Statistics ──
    vps_values = np.array([t['value_per_share'] for t in trials], dtype=float)

    # percentile_convention: nearest_r (N-1)*q interpolation
    def percentile_nearest_r(data, q):
        """nearest-rank: index = round((N-1)*q)"""
        n = len(data)
        idx = int(round((n - 1) * q))
        idx = max(0, min(n - 1, idx))
        return sorted(data)[idx]

    p10 = percentile_nearest_r(vps_values, 0.10)
    p25 = percentile_nearest_r(vps_values, 0.25)
    p50 = percentile_nearest_r(vps_values, 0.50)
    p75 = percentile_nearest_r(vps_values, 0.75)
    p90 = percentile_nearest_r(vps_values, 0.90)

    statistics = {
        'mean': round(float(np.mean(vps_values)), 2),
        'std': round(float(np.std(vps_values, ddof=1)), 2),
        'p10': round(float(p10), 2),
        'p25': round(float(p25), 2),
        'p50': round(float(p50), 2),
        'p75': round(float(p75), 2),
        'p90': round(float(p90), 2),
        'min': round(float(np.min(vps_values)), 2),
        'max': round(float(np.max(vps_values)), 2)
    }

    # ── Realized correlation ──
    driver_samples = np.column_stack([
        [t['revenue_growth'] for t in trials],
        [t['ebit_margin'] for t in trials],
        [t['reinvestment_intensity'] for t in trials],
        [t['discount_rate'] for t in trials]
    ])
    realized_corr = np.corrcoef(driver_samples.T).tolist()

    # ── Assemble output ──
    output = {
        'seed': seed,
        'n_valid': len(trials),
        'n_rejected': n_rejected,
        'method': 'Gaussian copula with Cholesky decomposition, inverse-CDF transform to triangular marginals',
        'drivers': drivers,
        'dependence': dependence,
        'realized_correlation': {
            'ordered_names': ordered_names,
            'matrix': realized_corr
        },
        'trials': trials,
        'statistics': statistics,
        'percentile_convention': 'nearest_r: index = round((N-1)*q)',
        'limitations': [
            'Triangular marginals are symmetric in form but parameters are calibrated to historical ranges and stress scenarios',
            'Gaussian copula imposes linear correlation; tail dependence is zero',
            'Revenue growth and margin held constant across 5-year projection within each path — no path-dependent mean reversion',
            'Reinvestment_intensity bundles capex, NWC changes, and D&A into a single revenue ratio — ignores within-period timing',
            'Tax rate, share count, net debt, and cash held constant',
            'Terminal growth fixed at model assumption; not a sampled driver',
            'Discount rate floor enforced to ensure WACC > g; truncated sample space',
            'No segment-level decomposition (Azure/M365/Windows etc.) — single aggregate revenue pool',
            'Model cutoff 2024-08-29; no post-cutoff information used'
        ]
    }

    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)

    # ── Update model.xlsx MC_Trials sheet ──
    wb = openpyxl.load_workbook(args.model)
    ws_mc = wb['MC_Trials']
    mc_updates = {
        2: len(trials),      # n_valid
        3: n_rejected,       # n_rejected
        4: seed,             # seed
        5: statistics['p10'],
        6: statistics['p25'],
        7: statistics['p50'],
        8: statistics['p75'],
        9: statistics['p90'],
        10: statistics['mean'],
        11: statistics['std'],
    }
    for row, val in mc_updates.items():
        ws_mc.cell(row=row, column=2, value=val)

    wb.save(args.model)

    print(f"Simulation complete: {len(trials)} valid paths, {n_rejected} rejected ({n_drawn} drawn)")
    print(f"Stats: mean={statistics['mean']:.2f}, p50={statistics['p50']:.2f}, p10={statistics['p10']:.2f}, p90={statistics['p90']:.2f}")
    print(f"Target corr G-M: {target_corr[0,1]:.3f}, realized: {realized_corr[0][1]:.4f}")
    print(f"Output written to {args.output}")


if __name__ == '__main__':
    main()