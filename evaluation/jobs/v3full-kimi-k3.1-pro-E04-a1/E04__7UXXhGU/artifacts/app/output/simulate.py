#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path

import numpy as np


SEED = 2133
N_PATHS = 8000
DRIVER_NAMES = [
    "revenue_growth",
    "ebit_margin",
    "reinvestment_intensity",
    "discount_rate",
]
DRIVERS = {
    "revenue_growth": {
        "distribution": "triangular",
        "parameters": {"left": -0.02, "mode": 0.09, "right": 0.20},
        "unit": "decimal annual revenue growth, constant within a path",
        "bounds": [-0.02, 0.20],
    },
    "ebit_margin": {
        "distribution": "triangular",
        "parameters": {"left": 0.12, "mode": 0.30, "right": 0.40},
        "unit": "decimal EBIT / revenue, constant within a path",
        "bounds": [0.12, 0.40],
    },
    "reinvestment_intensity": {
        "distribution": "triangular",
        "parameters": {"left": -0.08, "mode": 0.006, "right": 0.10},
        "unit": "decimal of annual revenue; CapEx plus NWC increase minus D&A; positive consumes cash",
        "bounds": [-0.08, 0.10],
    },
    "discount_rate": {
        "distribution": "triangular",
        "parameters": {"left": 0.065, "mode": 0.086, "right": 0.12},
        "unit": "decimal annual WACC",
        "bounds": [0.065, 0.12],
    },
}


def finite_assumption(assumptions, name):
    value = assumptions[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"assumptions.{name} must be finite")
    return float(value)


def percentile(values, q):
    ordered = np.sort(np.asarray(values, dtype=float))
    position = (len(ordered) - 1) * q
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    weight = position - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def main():
    parser = argparse.ArgumentParser(description="Reproducible path-level Netflix DCF Monte Carlo")
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as handle:
        input_data = json.load(handle)
    with open(args.model, encoding="utf-8") as handle:
        model = json.load(handle)
    assumptions = model["assumptions"]
    tax_rate = finite_assumption(assumptions, "tax_rate")
    terminal_growth = finite_assumption(assumptions, "terminal_growth")
    net_debt = finite_assumption(assumptions, "net_debt")
    cash_and_investments = finite_assumption(assumptions, "cash_and_investments")
    diluted_shares = finite_assumption(assumptions, "diluted_shares")
    if not 0 <= tax_rate < 1 or diluted_shares <= 0 or net_debt < 0:
        raise ValueError("invalid tax rate, gross debt, or diluted shares")
    if input_data["reported_partial_period"]["type"] != "annual":
        raise ValueError("this simulator implements the full-fiscal-year annual variant")
    if input_data["reported_partial_period"]["timing"]["discount_years"] != [1, 2, 3, 4, 5]:
        raise ValueError("annual discount years must be 1 through 5")

    fy0 = input_data["last_full_fiscal_year"]
    base_revenue = float(input_data["historical"]["revenue"][fy0])
    first_year = int(fy0[:4]) + 1
    min_wacc = DRIVERS["discount_rate"]["bounds"][0]
    if min_wacc <= terminal_growth:
        raise ValueError("the WACC distribution must lie above terminal growth")

    correlation = np.array([
        [1.0, 0.35, 0.0, 0.0],
        [0.35, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])
    rng = np.random.Generator(np.random.PCG64(SEED))
    standard_normals = rng.standard_normal((N_PATHS, 4))
    correlated_normals = standard_normals @ np.linalg.cholesky(correlation).T
    normal_cdf = np.fromiter(
        (0.5 * (1.0 + math.erf(value / math.sqrt(2.0))) for value in correlated_normals[:, :2].flat),
        dtype=float,
        count=N_PATHS * 2,
    ).reshape(N_PATHS, 2)
    uniforms = np.empty((N_PATHS, 4))
    uniforms[:, :2] = normal_cdf
    uniforms[:, 2:] = rng.random((N_PATHS, 2))
    samples = np.empty((N_PATHS, 4))
    for column, name in enumerate(DRIVER_NAMES):
        p = DRIVERS[name]["parameters"]
        left, mode, right = p["left"], p["mode"], p["right"]
        span = right - left
        mode_fraction = (mode - left) / span
        u = uniforms[:, column]
        samples[:, column] = np.where(
            u < mode_fraction,
            left + np.sqrt(u * (mode - left) * span),
            right - np.sqrt((1 - u) * (right - mode) * span),
        )

    valid_mask = (
        np.all(np.isfinite(samples), axis=1)
        & (samples[:, 3] > terminal_growth)
        & (samples[:, 0] > -1)
        & (samples[:, 1] >= 0)
    )
    for column, name in enumerate(DRIVER_NAMES):
        lower, upper = DRIVERS[name]["bounds"]
        valid_mask &= (samples[:, column] >= lower) & (samples[:, column] <= upper)
    rejected_count = int(np.size(valid_mask) - np.count_nonzero(valid_mask))
    if not np.all(valid_mask):
        raise RuntimeError("unexpected rejected draws; inspect finite bounds before continuing")

    accepted_samples = samples[valid_mask]
    if len(accepted_samples) < 5000:
        raise RuntimeError("fewer than 5,000 valid paths")

    trials = []
    values = []
    for path_index in range(len(accepted_samples)):
        growth, margin, intensity, wacc = (float(value) for value in accepted_samples[path_index])
        revenue = base_revenue
        trajectory = []
        pv_explicit = 0.0
        for year_offset in range(1, 6):
            revenue *= 1 + growth
            ebit = revenue * margin
            reinvestment = revenue * intensity
            fcff = ebit * (1 - tax_rate) - reinvestment
            discount_factor = 1 / (1 + wacc) ** year_offset
            trajectory.append({
                "year": first_year + year_offset - 1,
                "revenue": revenue,
                "ebit": ebit,
                "reinvestment": reinvestment,
                "fcff": fcff,
                "discount_factor": discount_factor,
            })
            pv_explicit += fcff * discount_factor
        terminal_fcff = trajectory[-1]["fcff"]
        terminal_value = terminal_fcff * (1 + terminal_growth) / (wacc - terminal_growth)
        enterprise_value = pv_explicit + terminal_value * trajectory[-1]["discount_factor"]
        equity_value = enterprise_value + cash_and_investments - net_debt
        value_per_share = equity_value / diluted_shares
        if not math.isfinite(value_per_share):
            raise RuntimeError("non-finite path value")
        trials.append({
            "path_id": path_index + 1,
            "revenue_growth": growth,
            "ebit_margin": margin,
            "reinvestment_intensity": intensity,
            "discount_rate": wacc,
            "value_per_share": value_per_share,
            "trajectory": trajectory,
        })
        values.append(value_per_share)

    n_valid = len(accepted_samples)
    statistics = {
        "n_valid": n_valid,
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "p10": percentile(values, 0.10),
        "p25": percentile(values, 0.25),
        "p50": percentile(values, 0.50),
        "p75": percentile(values, 0.75),
        "p90": percentile(values, 0.90),
        "mean": float(np.mean(values)),
        "std_sample": float(np.std(values, ddof=1)),
    }
    output = {
        "seed": SEED,
        "n_valid": n_valid,
        "n_rejected": rejected_count,
        "method": {
            "name": "bounded triangular Monte Carlo with Gaussian copula",
            "random_generator": "numpy.random.Generator(numpy.random.PCG64(2133))",
            "draw_procedure": "Generate N x 4 standard normals, apply the lower Cholesky factor, transform the first two columns through the scalar standard-normal CDF, and replace the last two columns with independent Generator.random uniforms. Apply analytic inverse triangular CDFs.",
            "validity": "Retain only finite draws inside declared inclusive bounds with revenue growth > -1, nonnegative EBIT margin, and WACC > terminal g. n_rejected counts invalid generated paths.",
            "terminal_value": "FY5 FCFF * (1 + terminal_growth) / (path WACC - terminal_growth), discounted by path FY5 discount factor",
            "fixed_inputs": {
                "fy0": fy0,
                "base_revenue": base_revenue,
                "tax_rate": tax_rate,
                "terminal_growth": terminal_growth,
                "net_debt": net_debt,
                "cash_and_investments": cash_and_investments,
                "diluted_shares": diluted_shares,
                "discount_years": [1, 2, 3, 4, 5],
            },
        },
        "drivers": DRIVERS,
        "dependence": {
            "type": "gaussian_copula",
            "ordered_names": DRIVER_NAMES,
            "matrix": correlation.tolist(),
            "matrix_interpretation": "Pearson correlation of pre-copula Gaussian scores, not an exact target for realized triangular Pearson correlations",
            "explanation": "Revenue growth and EBIT margin have positively correlated Gaussian scores (0.35), representing shared subscription/advertising execution. Reinvestment intensity and WACC have independent scores; aggregate history cannot identify these causal relationships.",
        },
        "realized_correlation": {
            "type": "pearson",
            "ordered_names": DRIVER_NAMES,
            "matrix": np.corrcoef(accepted_samples, rowvar=False).tolist(),
        },
        "trials": trials,
        "statistics": statistics,
        "percentile_convention": "linear: sort N values; h=(N-1)q; value=x[floor(h)]+(h-floor(h))*(x[ceil(h)]-x[floor(h)]); zero-based indices",
        "limitations": [
            "The distribution is conditional on analyst-selected triangular bounds and a Gaussian copula; it is not a stock-price forecast or a market consensus estimate.",
            "Four fiscal-year growth observations and five margin observations cannot identify joint operating dynamics; the 0.35 growth/margin score correlation is an open assumption.",
            "Membership, churn/retention, price, advertising ARPU, content cash spend, and content amortization are not separately available in the frozen history.",
            "Constant path growth, margin, and reinvestment intensity omit competitive responses, content cycles, annual state transitions, and stochastic terminal growth.",
            "Reinvestment is a reduced-form cash-flow proxy; it does not separately reconstruct content-asset investment. SBC remains an operating cost and is not added back.",
            "Tax, cash/investments, gross debt, and shares are fixed at their disclosed model assumptions; no financing feedback or repurchase-price model is simulated.",
            "Terminal value is highly sensitive to the WACC-g spread. The simulation terminal growth is fixed at the model assumption, 3%, below every sampled WACC.",
        ],
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(f"Wrote {output_path}; n_valid={n_valid}, n_rejected={rejected_count}")
    print(json.dumps(statistics, indent=2))


if __name__ == "__main__":
    main()
