#!/usr/bin/env python3
"""
Monte Carlo DCF simulator for Deere & Co (DE).
Generates ≥5000 valid paths with correlated draws on four drivers,
computing per-path value per share via five-year DCF + Gordon terminal value.

Usage:
    python3 simulate.py --input /app/data/inputs.json --model /app/output/model.json --output /app/output/simulation.json
"""

import argparse
import json
import math
import sys

import numpy as np


# =============================================================================
# Marginal distribution samplers with explicit bounds
# =============================================================================

def sample_triangular(rng, min_v, mode_v, max_v):
    """Sample from triangular(min, mode, max)."""
    return rng.triangular(min_v, mode_v, max_v)


def sample_normal_bounded(rng, mu, sigma, lower, upper):
    """Sample from Normal(mu, sigma) truncated to [lower, upper]."""
    while True:
        x = rng.normal(mu, sigma)
        if lower <= x <= upper:
            return x


# =============================================================================
# Correlated uniform generation via Gaussian copula + Cholesky
# =============================================================================

def make_correlated_uniforms(rng, corr_matrix, n_samples):
    """
    Generate n_samples draws of 4 correlated Uniform(0,1) variables
    using a Gaussian copula with the given Spearman/rank correlation target.
    """
    dim = corr_matrix.shape[0]
    # Cholesky decomposition
    L = np.linalg.cholesky(corr_matrix)
    # Generate independent standard normals
    z = rng.normal(0, 1, size=(n_samples, dim))
    # Correlate them
    z_corr = z @ L.T
    # Transform to uniform via standard normal CDF
    from scipy.stats import norm as scipy_norm
    uniforms = scipy_norm.cdf(z_corr)
    return uniforms


# =============================================================================
# Main simulation
# =============================================================================

def run_simulation(input_path, model_path, output_path):
    # Load inputs
    with open(input_path, 'r') as f:
        inputs = json.load(f)
    with open(model_path, 'r') as f:
        model = json.load(f)

    # Extract constants from model
    a = model['assumptions']
    v = model['valuation']
    rev_fy0 = model['historical']['revenue']['2024-10-27']
    tax_rate = a['tax_rate']
    terminal_g = a['terminal_growth']
    cash = a['cash_and_investments']
    net_debt = a['net_debt']
    diluted_shares = a['diluted_shares']

    # Simulation parameters
    seed = 1931
    target_valid = max(5000, 5000)  # at least 5000
    n_attempt = target_valid * 2  # over-generate to account for rejection

    rng = np.random.default_rng(seed)

    # ---- Declared correlation matrix (4x4) ----
    # Order: revenue_growth, ebit_margin, reinvestment_intensity, discount_rate
    declared_corr = np.array([
        [1.0,  0.50, 0.20, -0.10],
        [0.50, 1.0,  0.15, -0.05],
        [0.20, 0.15, 1.0,   0.00],
        [-0.10,-0.05, 0.00,  1.0 ]
    ], dtype=np.float64)

    # Ensure positive-definite (add small ridge if needed)
    eigvals = np.linalg.eigvalsh(declared_corr)
    if eigvals[0] <= 0:
        declared_corr += np.eye(4) * (abs(eigvals[0]) + 1e-8)

    # Generate correlated uniforms
    n_gen = target_valid * 3
    try:
        uniforms = make_correlated_uniforms(rng, declared_corr, n_gen)
    except Exception:
        # fallback: use numpy multivariate normal directly
        from scipy.stats import norm as scipy_norm
        L = np.linalg.cholesky(declared_corr)
        z = rng.normal(0, 1, size=(n_gen, 4))
        z_corr = z @ L.T
        uniforms = scipy_norm.cdf(z_corr)

    # ---- Distribution definitions ----
    # Driver 0: revenue_growth ~ Triangular(min=-0.12, mode=0.03, max=0.12)
    # Driver 1: ebit_margin ~ Triangular(min=0.12, mode=0.19, max=0.22)
    # Driver 2: reinvestment_intensity ~ Triangular(min=-0.08, mode=0.01, max=0.08)
    # Driver 3: discount_rate ~ Normal(mu=0.085, sigma=0.012) bounded [0.06, 0.12]

    # Transform uniforms to marginals
    drivers_raw = np.zeros((n_gen, 4))
    n_rejected = 0

    for i in range(n_gen):
        u0, u1, u2, u3 = uniforms[i]

        # revenue_growth: triangular
        rg = _triangular_ppf(u0, -0.12, 0.03, 0.12)
        drivers_raw[i, 0] = rg

        # ebit_margin: triangular
        em = _triangular_ppf(u1, 0.12, 0.19, 0.22)
        drivers_raw[i, 1] = em

        # reinvestment_intensity: triangular
        ri = _triangular_ppf(u2, -0.08, 0.01, 0.08)
        drivers_raw[i, 2] = ri

        # discount_rate: normal bounded
        dr = _normal_ppf_bounded(rng, u3, 0.085, 0.012, 0.06, 0.12)
        drivers_raw[i, 3] = dr

    # ---- Build paths ----
    trials = []
    path_id = 0

    for i in range(n_gen):
        rg = drivers_raw[i, 0]  # constant per path
        em = drivers_raw[i, 1]  # constant per path
        ri = drivers_raw[i, 2]  # constant per path
        dr = drivers_raw[i, 3]  # constant per path

        # Check: dr must be > terminal_g
        if dr <= terminal_g:
            n_rejected += 1
            continue

        # Build 5-year trajectory
        trajectory = []
        rev = rev_fy0

        for yr_idx in range(5):
            rev = rev * (1 + rg)
            ebit_val = rev * em
            reinvestment = rev * ri  # capex + dNWC - D&A; positive = cash consumed
            fcff_val = ebit_val * (1 - tax_rate) - reinvestment
            df_val = 1.0 / (1 + dr) ** (yr_idx + 1)

            trajectory.append({
                "year": yr_idx + 1,
                "revenue": round(rev, 2),
                "ebit": round(ebit_val, 2),
                "reinvestment": round(reinvestment, 2),
                "fcff": round(fcff_val, 2),
                "discount_factor": round(df_val, 8)
            })

        # Terminal value (Gordon) using FY5 FCFF
        fcff_y5 = trajectory[4]["fcff"]
        tv_undisc = fcff_y5 * (1 + terminal_g) / (dr - terminal_g)
        pv_tv = tv_undisc / (1 + dr) ** 5

        # PV of FCFFs
        pv_fcff = sum(traj["fcff"] * traj["discount_factor"] for traj in trajectory)

        enterprise_value = pv_fcff + pv_tv
        equity_value = enterprise_value + cash - net_debt
        value_per_share = equity_value / diluted_shares

        trials.append({
            "path_id": path_id,
            "revenue_growth": round(rg, 6),
            "ebit_margin": round(em, 6),
            "reinvestment_intensity": round(ri, 6),
            "discount_rate": round(dr, 6),
            "value_per_share": round(value_per_share, 2),
            "trajectory": trajectory
        })
        path_id += 1

    # Truncate to target_valid if we have more
    n_valid = len(trials)

    # Compute actual correlation matrix from the valid paths
    valid_drivers = np.array([[t["revenue_growth"], t["ebit_margin"],
                               t["reinvestment_intensity"], t["discount_rate"]]
                              for t in trials])
    realized_corr = np.corrcoef(valid_drivers.T).tolist()

    # Compute statistics
    vps_values = np.array([t["value_per_share"] for t in trials])
    # Percentile convention: (N-1)*q linear interpolation
    qs = [0.10, 0.25, 0.50, 0.75, 0.90]
    percentiles = {}
    for q in qs:
        idx = (n_valid - 1) * q
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            pval = float(vps_values[lo]) if lo < n_valid else float(vps_values[-1])
        else:
            frac = idx - lo
            v_sorted = np.sort(vps_values)
            pval = float(v_sorted[lo] * (1 - frac) + v_sorted[hi] * frac)
        percentiles[f"p{int(q*100)}"] = round(pval, 2)

    stats = {
        "p10": percentiles["p10"],
        "p25": percentiles["p25"],
        "p50": percentiles["p50"],
        "p75": percentiles["p75"],
        "p90": percentiles["p90"],
        "mean": round(float(np.mean(vps_values)), 2),
        "std": round(float(np.std(vps_values, ddof=1)), 2),
        "min": round(float(np.min(vps_values)), 2),
        "max": round(float(np.max(vps_values)), 2),
        "skewness": round(float(_skewness(vps_values)), 4),
        "kurtosis": round(float(_kurtosis(vps_values)), 4)
    }

    # Driver distribution summary
    driver_stats = {}
    names = ["revenue_growth", "ebit_margin", "reinvestment_intensity", "discount_rate"]
    for j, name in enumerate(names):
        col = valid_drivers[:, j]
        driver_stats[name] = {
            "mean": round(float(np.mean(col)), 6),
            "std": round(float(np.std(col, ddof=1)), 6),
            "p10": round(float(np.percentile(col, 10)), 6),
            "p50": round(float(np.percentile(col, 50)), 6),
            "p90": round(float(np.percentile(col, 90)), 6)
        }

    # Build output
    output = {
        "seed": seed,
        "n_valid": n_valid,
        "n_rejected": n_rejected,
        "method": "Gaussian copula with Cholesky decomposition; 4 correlated drivers mapped to marginal distributions via inverse CDF",
        "drivers": {
            "revenue_growth": {
                "distribution": "triangular",
                "parameters": {"min": -0.12, "mode": 0.03, "max": 0.12},
                "unit": "fraction (year-over-year revenue growth rate)",
                "bounds": [-0.12, 0.12]
            },
            "ebit_margin": {
                "distribution": "triangular",
                "parameters": {"min": 0.12, "mode": 0.19, "max": 0.22},
                "unit": "fraction (EBIT / Revenue)",
                "bounds": [0.12, 0.22]
            },
            "reinvestment_intensity": {
                "distribution": "triangular",
                "parameters": {"min": -0.08, "mode": 0.01, "max": 0.08},
                "unit": "fraction ((CapEx + ΔNWC − D&A) / Revenue; positive = cash consumed)",
                "bounds": [-0.08, 0.08]
            },
            "discount_rate": {
                "distribution": "normal",
                "parameters": {"mu": 0.085, "sigma": 0.012},
                "unit": "fraction (WACC / discount rate)",
                "bounds": [0.06, 0.12]
            }
        },
        "dependence": {
            "ordered_names": ["revenue_growth", "ebit_margin", "reinvestment_intensity", "discount_rate"],
            "matrix": declared_corr.tolist(),
            "rationale": "Revenue growth and EBIT margin positively correlated (r=0.50) reflecting operating leverage in ag equipment: higher volumes improve absorption of fixed manufacturing costs and enable better pricing. Growth mildly correlated with reinvestment intensity (r=0.20) as expansion requires working capital and capex. Discount rate mildly negatively correlated with growth (r=-0.10) and margin (r=-0.05) reflecting lower risk premia in strong cycle phases.",
            "note": "Correlation structure imposed via Gaussian copula on uniform marginals before inverse-CDF transformation to target distributions."
        },
        "realized_correlation": {
            "ordered_names": ["revenue_growth", "ebit_margin", "reinvestment_intensity", "discount_rate"],
            "matrix": realized_corr
        },
        "trials": trials,
        "statistics": stats,
        "driver_statistics": driver_stats,
        "percentile_convention": "(N-1)*q linear interpolation on sorted value_per_share",
        "limitations": [
            "Growth and margin are constant within each path; no path-dependent evolution or mean reversion across the five forecast years",
            "Reinvestment intensity is assumed constant per path; in reality CapEx and NWC intensity vary with cycle phase",
            "Single-period terminal value assumes immediate convergence to perpetuity; no transitional phase modeled",
            "Correlation structure is static and linear (Gaussian copula); tail dependence not captured",
            "No stochastic tax rate, share count, or debt level — all treated as deterministic",
            "Distributions calibrated from 5-year historical window; may not capture full range of multi-decade agricultural cycles",
            "Captive finance operations (John Deere Financial) are consolidated; separation of manufacturing vs. finance cash flows not attempted due to data limitations",
            "Net debt estimate includes imputed noncurrent debt ($35B) for FY2022-FY2024 where XBRL data is null",
            "Monte Carlo distribution is a model-conditional DCF range, not a market price forecast"
        ]
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Simulation complete: {n_valid} valid paths, {n_rejected} rejected")
    print(f"Value per share: mean={stats['mean']:.2f}, p10={stats['p10']:.2f}, "
          f"p50={stats['p50']:.2f}, p90={stats['p90']:.2f}")
    print(f"Output written to {output_path}")


# =============================================================================
# Inverse CDF (PPF) helpers
# =============================================================================

def _triangular_ppf(u, a, b, c):
    """Inverse CDF for triangular distribution with min=a, mode=c, max=b."""
    if u < 0 or u > 1:
        raise ValueError(f"u out of range: {u}")
    if u <= (c - a) / (b - a):
        return a + math.sqrt(u * (b - a) * (c - a))
    else:
        return b - math.sqrt((1 - u) * (b - a) * (b - c))


def _normal_ppf_bounded(rng, u, mu, sigma, lower, upper):
    """Inverse CDF for truncated normal via rejection sampling from uniform."""
    # Transform uniform to quantile of unbounded normal, then accept if in bounds
    from scipy.stats import norm as scipy_norm
    # Direct quantile approach: use the uniform from the copula
    # But this doesn't respect the truncation. Instead, sample from the
    # truncated distribution directly using the copula uniform as the
    # CDF of the truncated distribution.
    # F_trunc(x) = (Phi((x-mu)/sigma) - Phi((lower-mu)/sigma)) / (Phi((upper-mu)/sigma) - Phi((lower-mu)/sigma))
    alpha = (lower - mu) / sigma
    beta = (upper - mu) / sigma
    from scipy.stats import norm as scipy_norm
    Phi_alpha = scipy_norm.cdf(alpha)
    Phi_beta = scipy_norm.cdf(beta)
    denom = Phi_beta - Phi_alpha
    # u is the CDF value of the truncated normal
    p = Phi_alpha + u * denom
    x = scipy_norm.ppf(p) * sigma + mu
    # Clamp to bounds (numerical)
    return max(lower, min(upper, x))


def _skewness(x):
    n = len(x)
    mu = np.mean(x)
    s = np.std(x, ddof=1)
    if s == 0:
        return 0.0
    return (n / ((n - 1) * (n - 2))) * np.sum(((x - mu) / s) ** 3)


def _kurtosis(x):
    n = len(x)
    mu = np.mean(x)
    s = np.std(x, ddof=1)
    if s == 0:
        return 0.0
    term1 = (n * (n + 1)) / ((n - 1) * (n - 2) * (n - 3))
    term2 = np.sum(((x - mu) / s) ** 4)
    term3 = (3 * (n - 1) ** 2) / ((n - 2) * (n - 3))
    return term1 * term2 - term3


# =============================================================================
# CLI entry point
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monte Carlo DCF simulation")
    parser.add_argument("--input", required=True, help="Path to inputs.json")
    parser.add_argument("--model", required=True, help="Path to model.json")
    parser.add_argument("--output", required=True, help="Path to simulation.json output")
    args = parser.parse_args()

    try:
        import scipy  # noqa: F401
    except ImportError:
        print("ERROR: scipy is required. Install with: pip install scipy", file=sys.stderr)
        sys.exit(1)

    run_simulation(args.input, args.model, args.output)