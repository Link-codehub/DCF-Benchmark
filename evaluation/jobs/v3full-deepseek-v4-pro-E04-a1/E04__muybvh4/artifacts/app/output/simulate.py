#!/usr/bin/env python3
"""Monte Carlo DCF simulation for Netflix (NFLX) valuation.
Simulates 4 drivers: revenue_growth, ebit_margin, reinvestment_intensity, discount_rate.
Growth and margin correlated via Gaussian copula (rho=0.4); others independent.
Seed 2133, >= 5000 valid paths."""

import argparse
import json
import math
import sys

import numpy as np


def parse_args():
    p = argparse.ArgumentParser(
        description="Monte Carlo DCF for Netflix"
    )
    p.add_argument("--input", required=True, help="Path to inputs.json")
    p.add_argument("--model", required=True, help="Path to model.json")
    p.add_argument("--output", required=True, help="Path for simulation.json")
    return p.parse_args()


def triangular_ppf(u, a, b, c):
    """Inverse CDF of triangular distribution.
    a = lower bound, b = upper bound, c = mode."""
    if u <= (c - a) / (b - a):
        return a + math.sqrt(u * (b - a) * (c - a))
    else:
        return b - math.sqrt((1.0 - u) * (b - a) * (b - c))


def norm_cdf_inv(u):
    """Approximation of inverse standard normal CDF (quantile function).
    Uses a rational approximation (Peter Acklam)."""
    if u <= 0.0 or u >= 1.0:
        return float("-inf") if u <= 0.0 else float("inf")

    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]

    u = min(max(u, 1e-15), 1.0 - 1e-15)

    if u < 0.02425:
        # Lower region
        q = math.sqrt(-2.0 * math.log(u))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    elif u > 0.97575:
        # Upper region
        q = math.sqrt(-2.0 * math.log(1.0 - u))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    else:
        # Central region
        q = u - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        )


def main():
    args = parse_args()

    with open(args.input) as f:
        inp = json.load(f)
    with open(args.model) as f:
        model = json.load(f)

    seed = 2133
    rng = np.random.RandomState(seed)

    # --- Extract fixed parameters from model ---
    tax_rate = model["assumptions"]["tax_rate"]
    terminal_g = model["assumptions"]["terminal_growth"]
    shares = model["assumptions"]["diluted_shares"]
    net_debt = model["assumptions"]["net_debt"]
    cash_inv = model["assumptions"]["cash_and_investments"]
    fy0_revenue = inp["historical"]["revenue"]["2024-12-31"]

    # --- Driver distributions (all triangular) ---
    # Bounds derived from historical volatility and stress scenarios:
    #   revenue_growth: FY20-24 range [6.46%, 18.81%], triangular min captures
    #     competitive saturation, max captures strong ad-tier adoption.
    #   ebit_margin: FY20-24 range [17.82%, 26.71%] with upward trend;
    #     min reflects content cost escalation, max reflects mature operating leverage.
    #   reinvestment_intensity: historical (capex+Δnwc-D&A)/rev range [-2.86%, 3.46%];
    #     negative = D&A exceeds tangible reinvestment (content amortisation effect).
    #   discount_rate: base WACC 8.5%; min reflects lower ERP, max reflects higher beta / rate risk.

    growth_params = {"min": 0.02, "mode": 0.09, "max": 0.20}
    margin_params = {"min": 0.22, "mode": 0.29, "max": 0.36}
    reinv_params = {"min": -0.05, "mode": -0.01, "max": 0.04}
    disc_params = {"min": 0.065, "mode": 0.085, "max": 0.12}

    # --- Declared dependence ---
    # revenue_growth and ebit_margin: positive correlation expected because
    # subscriber/add-tier growth drives operating leverage (content cost
    # amortised over larger base).  Set rho = 0.4.
    # reinvestment_intensity and discount_rate: independent (no established
    # structural link in the literature for this firm).
    rho_gm = 0.4
    declared_matrix = [
        [1.0, 0.4, 0.0, 0.0],
        [0.4, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]

    # Cholesky factor of 2x2 correlation submatrix for (growth, margin)
    L_11 = 1.0
    L_21 = rho_gm
    L_22 = math.sqrt(1.0 - rho_gm * rho_gm)

    n_target = 5000
    n_generated = 0
    n_rejected = 0
    trials = []

    all_g = []
    all_m = []
    all_r = []
    all_d = []

    while len(trials) < n_target:
        n_generated += 1

        # --- Correlated sampling: revenue_growth & ebit_margin ---
        z1 = rng.normal()
        z2 = rng.normal()
        x1 = z1
        x2 = L_21 * z1 + L_22 * z2  # corr(x1, x2) ≈ rho_gm

        # Convert to uniforms via normal CDF
        U1 = 0.5 * (1.0 + math.erf(x1 / math.sqrt(2.0)))
        U2 = 0.5 * (1.0 + math.erf(x2 / math.sqrt(2.0)))

        growth = triangular_ppf(
            U1, growth_params["min"], growth_params["max"], growth_params["mode"]
        )
        margin = triangular_ppf(
            U2, margin_params["min"], margin_params["max"], margin_params["mode"]
        )

        # --- Independent sampling ---
        U3 = rng.uniform()
        U4 = rng.uniform()
        reinv_intensity = triangular_ppf(
            U3, reinv_params["min"], reinv_params["max"], reinv_params["mode"]
        )
        disc_rate = triangular_ppf(
            U4, disc_params["min"], disc_params["max"], disc_params["mode"]
        )

        # --- Gate checks ---
        if disc_rate <= terminal_g:
            n_rejected += 1
            continue

        # --- Build 5-year trajectory ---
        trajectory = []
        rev = fy0_revenue
        for yr in range(1, 6):
            rev = rev * (1.0 + growth)
            ebit = rev * margin
            reinvestment = rev * reinv_intensity  # CapEx+ΔNWC-D&A
            fcff = ebit * (1.0 - tax_rate) - reinvestment
            disc_factor = 1.0 / (1.0 + disc_rate) ** yr
            trajectory.append(
                {
                    "year": yr,
                    "revenue": round(rev, 6),
                    "ebit": round(ebit, 6),
                    "reinvestment": round(reinvestment, 6),
                    "fcff": round(fcff, 6),
                    "discount_factor": round(disc_factor, 10),
                }
            )

        # --- Terminal value (Gordon growth, FY5 FCFF base) ---
        terminal_fcff = trajectory[4]["fcff"]
        tv = terminal_fcff * (1.0 + terminal_g) / (disc_rate - terminal_g)
        pv_tv = tv * trajectory[4]["discount_factor"]

        # --- PV of explicit FCFFs ---
        pv_explicit = sum(
            t["fcff"] * t["discount_factor"] for t in trajectory
        )

        ev = pv_explicit + pv_tv
        equity_val = ev + cash_inv - net_debt
        vps = equity_val / shares

        if vps <= 0.0 or vps > 500.0:
            n_rejected += 1
            continue

        all_g.append(growth)
        all_m.append(margin)
        all_r.append(reinv_intensity)
        all_d.append(disc_rate)

        trials.append(
            {
                "path_id": len(trials),
                "revenue_growth": round(growth, 6),
                "ebit_margin": round(margin, 6),
                "reinvestment_intensity": round(reinv_intensity, 6),
                "discount_rate": round(disc_rate, 6),
                "value_per_share": round(vps, 4),
                "trajectory": trajectory,
            }
        )

    # --- Realized correlation matrix ---
    realized_corr = np.corrcoef(
        [all_g, all_m, all_r, all_d]
    ).tolist()
    # Round for cleanliness
    realized_corr = [
        [round(v, 6) for v in row] for row in realized_corr
    ]

    # --- Statistics ---
    vps_vals = [t["value_per_share"] for t in trials]
    vps_sorted = sorted(vps_vals)
    n_valid = len(vps_sorted)

    def percentile_nearest(data, q):
        """nearest_r: index = round(q * (N-1))."""
        idx = int(round(q * (n_valid - 1)))
        idx = max(0, min(idx, n_valid - 1))
        return data[idx]

    p10 = percentile_nearest(vps_sorted, 0.10)
    p25 = percentile_nearest(vps_sorted, 0.25)
    p50 = percentile_nearest(vps_sorted, 0.50)
    p75 = percentile_nearest(vps_sorted, 0.75)
    p90 = percentile_nearest(vps_sorted, 0.90)
    mean_vps = sum(vps_vals) / n_valid
    std_vps = float(np.std(vps_vals))

    drivers_info = {
        "revenue_growth": {
            "distribution": "triangular",
            "parameters": growth_params,
            "unit": "decimal (annual)",
            "bounds": [growth_params["min"], growth_params["max"]],
        },
        "ebit_margin": {
            "distribution": "triangular",
            "parameters": margin_params,
            "unit": "decimal",
            "bounds": [margin_params["min"], margin_params["max"]],
        },
        "reinvestment_intensity": {
            "distribution": "triangular",
            "parameters": reinv_params,
            "unit": "decimal (fraction of revenue)",
            "bounds": [reinv_params["min"], reinv_params["max"]],
        },
        "discount_rate": {
            "distribution": "triangular",
            "parameters": disc_params,
            "unit": "decimal",
            "bounds": [disc_params["min"], disc_params["max"]],
        },
    }

    output = {
        "seed": seed,
        "n_valid": n_valid,
        "n_rejected": n_rejected,
        "method": (
            "Gaussian copula for revenue_growth–ebit_margin pair (rho=0.4); "
            "independent triangular draws for reinvestment_intensity and "
            "discount_rate.  Growth and margin constant within a path; "
            "reinvestment = revenue × intensity; "
            "FCFF = EBIT×(1−tax) − reinvestment; "
            "terminal value via Gordon growth on FY5 FCFF, discounted at "
            "path-specific discount rate."
        ),
        "drivers": drivers_info,
        "dependence": {
            "ordered_names": [
                "revenue_growth",
                "ebit_margin",
                "reinvestment_intensity",
                "discount_rate",
            ],
            "matrix": declared_matrix,
        },
        "realized_correlation": realized_corr,
        "trials": trials,
        "statistics": {
            "p10": round(p10, 4),
            "p25": round(p25, 4),
            "p50": round(p50, 4),
            "p75": round(p75, 4),
            "p90": round(p90, 4),
            "mean": round(mean_vps, 4),
            "std": round(std_vps, 4),
            "min": round(min(vps_vals), 4),
            "max": round(max(vps_vals), 4),
        },
        "percentile_convention": "nearest_r: percentile index = round(q * (N-1))",
        "limitations": (
            "Triangular distributions symmetrically approximate true driver uncertainty; "
            "growth and margin held constant within a path ignoring year-to-year dynamics; "
            "reinvestment intensity assumed independent of growth/margin; "
            "discount rate held constant per path; "
            "terminal value uses constant terminal_g across all paths; "
            "no path-dependent capital-structure or content-cycle feedback; "
            "correlation limited to the growth–margin pair at fixed rho=0.4; "
            "no time-varying volatility structure. "
            "Simulation interval is model-conditional DCF distribution, NOT a stock-price prediction."
        ),
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"n_valid={n_valid}  n_rejected={n_rejected}  n_generated={n_generated}")
    print(
        f"VPS: mean={mean_vps:.2f}  p50={p50:.2f}  "
        f"p10={p10:.2f}  p25={p25:.2f}  p75={p75:.2f}  p90={p90:.2f}"
    )
    print(f"Realized growth-margin corr: {realized_corr[0][1]:.4f}")


if __name__ == "__main__":
    main()