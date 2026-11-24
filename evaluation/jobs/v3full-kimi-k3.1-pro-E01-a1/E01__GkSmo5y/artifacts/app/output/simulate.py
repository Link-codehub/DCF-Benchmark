#!/usr/bin/env python3
"""Offline, reproducible driver-based DCF Monte Carlo for the supplied MSFT snapshot."""

import argparse
import copy
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

SEED = 1830
N_VALID = 6000
NAMES = ["revenue_growth", "ebit_margin", "reinvestment_intensity", "discount_rate"]
DRIVER_CONFIG = {
    "revenue_growth": {
        "distribution": "triangular",
        "parameters": {"low": 0.04, "mode": 0.125, "high": 0.20},
        "unit": "decimal annual revenue growth; 0.10 = 10%",
        "bounds": [0.04, 0.20],
    },
    "ebit_margin": {
        "distribution": "triangular",
        "parameters": {"low": 0.30, "mode": 0.435, "high": 0.50},
        "unit": "decimal EBIT / revenue",
        "bounds": [0.30, 0.50],
    },
    "reinvestment_intensity": {
        "distribution": "lognormal",
        "parameters": {"median": 0.10, "sigma": 0.28},
        "unit": "decimal net reinvestment / revenue; positive uses cash",
        "bounds": [0.07, 0.24],
    },
    "discount_rate": {
        "distribution": "uniform",
        "parameters": {"low": 0.065, "high": 0.115},
        "unit": "decimal annual nominal discount rate",
        "bounds": [0.065, 0.115],
    },
}
COPULA = [
    [1.0, 0.35, 0.0, 0.0],
    [0.35, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]


def marginal(uniform, name, config):
    """Inverse-CDF sampling with finite rejection bounds for every family."""
    kind = config["distribution"]
    p = config["parameters"]
    low, high = config["bounds"]
    uniform = np.clip(uniform, 1e-12, 1.0 - 1e-12)
    if kind == "triangular":
        mode = p["mode"]
        if not low <= mode <= high:
            raise ValueError(f"{name}: triangular mode outside bounds")
        return _triangular(uniform, low, mode, high)
    if kind == "uniform":
        return low + uniform * (high - low)
    if kind in ("normal", "lognormal"):
        from scipy.special import ndtri

        z = ndtri(uniform)
        value = p["mean"] + p["sd"] * z if kind == "normal" else p["median"] * np.exp(p["sigma"] * z)
        return value
    if kind == "beta":
        from scipy.special import betaincinv

        return low + (high - low) * betaincinv(p["alpha"], p["beta"], uniform)
    raise ValueError(f"{name}: unsupported distribution {kind}")


def _triangular(u, low, mode, high):
    split = (mode - low) / (high - low)
    return np.where(
        u < split,
        low + np.sqrt(u * (high - low) * (mode - low)),
        high - np.sqrt((1.0 - u) * (high - low) * (high - mode)),
    )


def sample_drivers(rng, count, config=None, copula=None):
    config = config or DRIVER_CONFIG
    copula = np.asarray(copula if copula is not None else COPULA, dtype=float)
    if copula.shape != (4, 4) or not np.allclose(copula, copula.T):
        raise ValueError("dependence matrix must be symmetric 4x4")
    if np.linalg.eigvalsh(copula).min() <= 0:
        raise ValueError("dependence matrix must be positive definite")
    z = rng.multivariate_normal(np.zeros(4), copula, size=count)
    from scipy.special import ndtr

    uniforms = ndtr(z)
    values = {name: marginal(uniforms[:, i], name, config[name]) for i, name in enumerate(NAMES)}
    accepted = np.ones(count, dtype=bool)
    for name in NAMES:
        low, high = config[name]["bounds"]
        if not (math.isfinite(low) and math.isfinite(high) and low < high):
            raise ValueError(f"{name}: finite increasing bounds are required")
        accepted &= np.isfinite(values[name]) & (values[name] >= low) & (values[name] <= high)
    return {name: values[name][accepted] for name in NAMES}, int((~accepted).sum())


def history(h):
    y = h["fiscal_years"][-1]
    d = h["historical"]
    cash = d["cash"][y] + d["st_investments"][y]
    debt = d["debt_current"][y] + d["debt_noncurrent"][y]
    nwc = d["current_assets"][y] - cash - (d["current_liabilities"][y] - d["debt_current"][y])
    prior = h["fiscal_years"][-2]
    average_debt = (debt + d["debt_current"][prior] + d["debt_noncurrent"][prior]) / 2
    tax = d["income_tax"][y] / d["pretax_income"][y]
    return {
        "fiscal_year": y,
        "revenue": d["revenue"][y],
        "cash_and_investments": cash,
        "net_debt": debt,
        "nwc": nwc,
        "tax_rate": tax,
        "interest_rate": d["interest_expense"][y] / average_debt,
        "diluted_shares": d["diluted_shares_wavg"][y],
    }


def valuation_parameters(model_path, h, base):
    assumptions = {}
    if model_path and Path(model_path).exists():
        wb = load_workbook(model_path, data_only=True, read_only=True)
        if "Assumptions" not in wb.sheetnames:
            raise ValueError("model workbook has no Assumptions sheet")
        ws = wb["Assumptions"]
        for row in ws.iter_rows(min_row=2, max_col=2, values_only=True):
            if isinstance(row[0], str) and row[0].strip():
                assumptions[row[0]] = row[1]
        wb.close()
    terminal_growth = float(assumptions.get("terminal_growth", 0.03))
    shares = float(base["diluted_shares"])
    start_revenue = float(base["revenue"])
    tax_rate = float(base["tax_rate"])
    cash = float(base["cash_and_investments"])
    net_debt = float(base["net_debt"])
    if model_path and Path(model_path).exists():
        # The simulation's independent driver grid starts at the same historical revenue.
        # Tax, terminal growth and the dated equity bridge are read from the saved model.
        tax_rate = float(assumptions.get("tax_rate", tax_rate))
        shares = float(assumptions.get("diluted_shares", shares))
        cash = float(assumptions.get("cash_and_investments", cash))
        net_debt = float(assumptions.get("net_debt", net_debt))
    valuation_date = date.fromisoformat(h["valuation_date"])
    first_end = date.fromisoformat(h["fiscal_years"][-1]).year + 1
    years = [(date(first_end + i, 6, 30) - valuation_date).days / 365 for i in range(5)]
    return {
        "start_revenue": start_revenue,
        "tax_rate": tax_rate,
        "terminal_growth": terminal_growth,
        "cash_and_investments": cash,
        "net_debt": net_debt,
        "diluted_shares": shares,
        "discount_years": years,
        "fiscal_years": [f"{first_end + i}-06-30" for i in range(5)],
    }


def percentile_linear(values, q):
    """NumPy (N-1)q linear interpolation, stated explicitly for audit."""
    ordered = np.sort(np.asarray(values, dtype=float))
    position = (len(ordered) - 1) * q
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    fraction = position - lower
    return float(ordered[lower] * (1 - fraction) + ordered[upper] * fraction)


def simulate(h, model_path, n_valid=N_VALID, seed=SEED):
    base = history(h)
    p = valuation_parameters(model_path, h, base)
    rng = np.random.Generator(np.random.PCG64(seed))
    accepted = []
    rejected = 0
    while len(accepted) < n_valid:
        batch, count = sample_drivers(rng, n_valid - len(accepted))
        rejected += count
        accepted.extend([{name: float(batch[name][i]) for name in NAMES} for i in range(len(batch[NAMES[0]]))])
    trials = []
    values = []
    for path_id, drivers in enumerate(accepted[:n_valid], 1):
        revenue = p["start_revenue"]
        trajectory = []
        pv_fcff = 0.0
        for i in range(5):
            revenue *= 1 + drivers["revenue_growth"]
            ebit = revenue * drivers["ebit_margin"]
            reinvestment = revenue * drivers["reinvestment_intensity"]
            fcff = ebit * (1 - p["tax_rate"]) - reinvestment
            discount_factor = 1 / (1 + drivers["discount_rate"]) ** p["discount_years"][i]
            pv_fcff += fcff * discount_factor
            trajectory.append({
                "year": p["fiscal_years"][i],
                "revenue": revenue,
                "ebit": ebit,
                "reinvestment": reinvestment,
                "fcff": fcff,
                "discount_factor": discount_factor,
            })
        if trajectory[-1]["fcff"] <= 0 or drivers["discount_rate"] <= p["terminal_growth"]:
            raise ValueError("invalid terminal-value path")
        terminal_fcff = trajectory[-1]["fcff"] * (1 + p["terminal_growth"])
        terminal_value = terminal_fcff / (drivers["discount_rate"] - p["terminal_growth"])
        enterprise_value = pv_fcff + terminal_value * trajectory[-1]["discount_factor"]
        equity_value = enterprise_value + p["cash_and_investments"] - p["net_debt"]
        value_per_share = equity_value / p["diluted_shares"]
        trials.append({"path_id": path_id, **drivers, "value_per_share": value_per_share, "trajectory": trajectory})
        values.append(value_per_share)
    matrix = np.corrcoef(np.column_stack([[t[name] for t in trials] for name in NAMES]), rowvar=False)
    quantiles = {f"p{q}": percentile_linear(values, q / 100) for q in (1, 5, 10, 25, 50, 75, 90, 95, 99)}
    statistics = {
        "metric": "value_per_share",
        "unit": "USD per diluted share",
        "mean": float(np.mean(values)),
        "standard_deviation": float(np.std(values, ddof=1)),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        **quantiles,
        "percentiles": quantiles,
        "terminal_growth": p["terminal_growth"],
        "tax_rate": p["tax_rate"],
        "valuation_date": h["valuation_date"],
        "discount_years": p["discount_years"],
        "equity_bridge": {
            "cash_and_short_term_investments": p["cash_and_investments"],
            "net_debt": p["net_debt"],
            "diluted_shares": p["diluted_shares"],
            "unit": "USD millions and diluted shares millions",
        },
    }
    return {
        "seed": seed,
        "n_valid": len(trials),
        "n_rejected": rejected,
        "method": {
            "name": "Gaussian copula with inverse-CDF marginal transforms and post-sampling finite-bound rejection",
            "random_generator": "NumPy PCG64 (64-bit); one seeded Generator drives all draws",
            "random_draw_order": "correlated standard-normal 4-vectors in driver-config order, then marginal transforms",
            "n_requested": n_valid,
            "batch_size": "exactly the remaining valid paths per iteration; no surplus accepted paths",
            "rejection": "Nonfinite or outside inclusive driver bounds is rejected and replaced; n_rejected counts every excluded candidate draw",
            "valuation": "Five full fiscal years; constant growth and margin within a path; FY5 Gordon terminal FCFF; actual-date discount periods",
            "formula": "FCFF=EBIT*(1-tax)-reinvestment; TV=FCFF_FY5*(1+g)/(r-g); per-share=(PV(FCFF)+PV(TV)+cash+ST investments-net debt)/diluted shares",
            "source_model": str(model_path) if model_path else None,
            "valuation_parameters": p,
        },
        "drivers": copy.deepcopy(DRIVER_CONFIG),
        "dependence": {
            "type": "gaussian_copula",
            "ordered_names": NAMES,
            "matrix": COPULA,
            "parameter_meaning": "Pearson correlations of latent standard normals, before nonlinear marginal transforms; realized driver correlations are separately reported",
            "rationale": "0.35 latent growth-margin correlation represents shared demand/scale benefits despite AI depreciation; zero cross-correlations are simplifying assumptions, not proof of independence",
        },
        "realized_correlation": {
            "method": "Pearson sample correlation on accepted realized driver values",
            "ordered_names": NAMES,
            "matrix": matrix.tolist(),
        },
        "trials": trials,
        "statistics": statistics,
        "percentile_convention": {
            "name": "linear",
            "formula": "Sort N values; position=(N-1)*q, zero-based; linearly interpolate between floor and ceiling ranks",
            "quantiles_reported": [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99],
        },
        "limitations": [
            "Conditional DCF distribution, not a stock-price forecast, trading range, probability of return or market consensus",
            "Frozen inputs contain consolidated financials only; cloud demand, data-center capacity/utilization and commitment-duration effects are unobserved scenario assumptions",
            "Four observations of annual growth cannot identify a reliable dependence structure; copula correlations are judgmental and nonlinear transforms alter realized correlations",
            "Growth and EBIT margin are constant within each path, unlike the fading-growth deterministic model; no within-path mean reversion, cyclicality or parameter learning",
            "Reinvestment is an independent revenue-scaled net amount, not a pathwise roll-forward of PP&E, depreciation lives, capacity utilization or working-capital accounts; SBC remains an operating cost",
            "Tax, terminal growth, net debt, cash and diluted shares are fixed; no financing feedback, buybacks, dilution, acquisitions, tax changes or joint tail dependence",
            "Triangular support and truncated lognormal bounds are judgmental stress limits informed by historical volatility; they are not calibrated probabilities of future outcomes",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as f:
        h = json.load(f)
    result = simulate(h, args.model)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({"seed": result["seed"], "n_valid": result["n_valid"], "n_rejected": result["n_rejected"], "statistics": result["statistics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
