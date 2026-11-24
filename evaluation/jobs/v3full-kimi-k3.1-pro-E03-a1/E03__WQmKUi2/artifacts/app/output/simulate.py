#!/usr/bin/env python3
"""Target residual-H2 DCF and auditable Monte Carlo, using only the frozen inputs."""

import argparse
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from scipy.special import ndtr
from scipy.stats import beta as beta_distribution

SEED = 2032
N_VALID = 10000
MAX_DRAWS = 200000
ORDERED_NAMES = [
    "revenue_growth",
    "ebit_margin",
    "reinvestment_intensity",
    "discount_rate",
]
DECLARED_CORRELATION = [
    [1.0, 0.35, 0.0, 0.0],
    [0.35, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]
DRIVERS = {
    "revenue_growth": {
        "distribution": "triangular",
        "parameters": {"min": -0.05, "mode": -0.015, "max": 0.04},
        "unit": "decimal annual revenue growth; FY1 applies to prior-year H2",
        "bounds": [-0.05, 0.04],
    },
    "ebit_margin": {
        "distribution": "beta",
        "parameters": {
            "alpha": 7.65,
            "beta": 142.35,
            "min": 0.0,
            "max": 0.10,
            "concentration_alpha_plus_beta": 150.0,
        },
        "unit": "decimal EBIT / sampled-period revenue",
        "bounds": [0.0, 0.10],
    },
    "reinvestment_intensity": {
        "distribution": "triangular",
        "parameters": {"min": -0.02, "mode": 0.004, "max": 0.08},
        "unit": "decimal of trajectory revenue; positive consumes cash",
        "bounds": [-0.02, 0.08],
    },
    "discount_rate": {
        "distribution": "triangular",
        "parameters": {"min": 0.065, "mode": 0.085, "max": 0.115},
        "unit": "decimal annual WACC",
        "bounds": [0.065, 0.115],
    },
}


def triangular_cdf_inverse(u, low, mode, high):
    split = (mode - low) / (high - low)
    return np.where(
        u < split,
        low + np.sqrt(u * (high - low) * (mode - low)),
        high - np.sqrt((1.0 - u) * (high - low) * (high - mode)),
    )


def percentiles(values, probabilities):
    """Linear interpolation at zero-based sorted index (N-1)*q."""
    ordered = sorted(float(x) for x in values)
    n = len(ordered)
    result = {}
    for probability in probabilities:
        position = (n - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        weight = position - lower
        value = ordered[lower] * (1.0 - weight) + ordered[upper] * weight
        result[f"p{int(probability * 100)}"] = value
    return result


def sample_drivers():
    rng = np.random.default_rng(SEED)
    normals = rng.standard_normal((MAX_DRAWS, 2))
    normals[:, 1] = (
        0.35 * normals[:, 0] + math.sqrt(1.0 - 0.35**2) * normals[:, 1]
    )
    uniforms = ndtr(normals)
    growth = triangular_cdf_inverse(uniforms[:, 0], -0.05, -0.015, 0.04)
    margin = beta_distribution.ppf(uniforms[:, 1], 7.65, 142.35)
    reinvestment = triangular_cdf_inverse(
        rng.random(MAX_DRAWS), -0.02, 0.004, 0.08
    )
    discount = triangular_cdf_inverse(
        rng.random(MAX_DRAWS), 0.065, 0.085, 0.115
    )
    raw = np.column_stack((growth, margin, reinvestment, discount))
    legal = (
        np.isfinite(raw).all(axis=1)
        & (growth >= -0.05)
        & (growth <= 0.04)
        & (margin >= 0.0)
        & (margin <= 0.10)
        & (reinvestment >= -0.02)
        & (reinvestment <= 0.08)
        & (discount >= 0.065)
        & (discount <= 0.115)
    )
    accepted = raw[legal][:N_VALID]
    if len(accepted) != N_VALID:
        raise RuntimeError("Insufficient legal Monte Carlo draws")
    rejected = int((~legal).sum())
    return accepted, rejected, int(legal.sum())


def simulate(inputs):
    historical = inputs["historical"]
    fy0 = inputs["last_full_fiscal_year"]
    partial = inputs["reported_partial_period"]
    quarters = partial["quarters"]
    prior_quarters = partial["prior_year_quarters"]
    prior_h2_revenue = historical["revenue"][fy0] - sum(
        quarter["revenue"] for quarter in prior_quarters
    )
    tax_rate = historical["income_tax"][fy0] / historical["pretax_income"][fy0]
    terminal_growth = 0.02
    years = partial["timing"]["discount_years"]
    net_debt = historical["debt_noncurrent"][fy0]
    cash_and_investments = historical["cash"][fy0] + historical["st_investments"][fy0]
    shares = historical["diluted_shares_wavg"][fy0]

    accepted, rejected, legal_draws = sample_drivers()
    trials = []
    values = []
    for path_id, (growth, margin, intensity, wacc) in enumerate(accepted, start=1):
        if not wacc > terminal_growth:
            raise RuntimeError("Terminal growth must remain below sampled WACC")
        trajectory = []
        explicit_pv = 0.0
        revenue_base = prior_h2_revenue
        for index, discount_years in enumerate(years):
            revenue = revenue_base * (1.0 + growth)
            ebit = revenue * margin
            reinvestment = revenue * intensity
            fcff = ebit * (1.0 - tax_rate) - reinvestment
            discount_factor = 1.0 / (1.0 + wacc) ** discount_years
            trajectory.append(
                {
                    "year": f"FY{index + 1}",
                    "revenue": float(revenue),
                    "ebit": float(ebit),
                    "reinvestment": float(reinvestment),
                    "fcff": float(fcff),
                    "discount_factor": float(discount_factor),
                }
            )
            explicit_pv += fcff * discount_factor
            revenue_base = revenue
        terminal_fcff = trajectory[-1]["fcff"] * (1.0 + terminal_growth)
        terminal_value = terminal_fcff / (wacc - terminal_growth)
        enterprise_value = explicit_pv + terminal_value * trajectory[-1]["discount_factor"]
        equity_value = enterprise_value + cash_and_investments - net_debt
        value_per_share = equity_value / shares
        values.append(float(value_per_share))
        trials.append(
            {
                "path_id": path_id,
                "revenue_growth": float(growth),
                "ebit_margin": float(margin),
                "reinvestment_intensity": float(intensity),
                "discount_rate": float(wacc),
                "tax_rate": float(tax_rate),
                "terminal_growth": terminal_growth,
                "discount_years": [float(year) for year in years],
                "net_debt": float(net_debt),
                "cash_and_investments": float(cash_and_investments),
                "diluted_shares": float(shares),
                "value_per_share": float(value_per_share),
                "trajectory": trajectory,
            }
        )

    stats = {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": float(np.mean(values)),
        "std_dev_sample": float(np.std(values, ddof=1)),
        **percentiles(values, [0.10, 0.25, 0.50, 0.75, 0.90]),
    }
    realized = np.corrcoef(accepted, rowvar=False).tolist()
    return {
        "seed": SEED,
        "n_valid": len(values),
        "n_rejected": rejected,
        "method": {
            "name": "numpy.random.default_rng(PCG64); two correlated standard normals followed by inverse-CDF triangular and beta transforms; two independent inverse-CDF triangular drivers",
            "random_generator": "NumPy PCG64 with explicit seed 2032",
            "requested_valid_paths": N_VALID,
            "maximum_raw_draws": MAX_DRAWS,
            "legal_raw_draws_including_unused": legal_draws,
            "acceptance": "Retain finite draws inside declared inclusive bounds and with WACC > terminal_growth; reject all others; report rejected raw draws separately.",
            "sequence": "One MAX_DRAWS x 2 standard-normal matrix is transformed by a Gaussian copula; then two independent uniform vectors are drawn. Only the first N_VALID legal rows are used.",
            "valuation_date": inputs["valuation_date"],
            "fiscal_year_end": partial["timing"]["next_fiscal_year_end"],
            "residual_days": partial["timing"]["remaining_days"],
            "discount_years": years,
            "fy1_scope": "Residual H2 only: prior-year H2 = FY0 revenue - prior-year H1 revenue. FY2-FY5 compound the sampled growth on FY1 residual revenue as required by the path convention.",
            "revenue_rule": "Revenue(t)=Revenue(t-1)*(1+sampled revenue_growth), with Revenue(0)=prior-year H2; growth is constant within each path.",
            "ebit_rule": "EBIT(t)=Revenue(t)*sampled ebit_margin; margin is constant within each path.",
            "reinvestment_rule": "Reinvestment(t)=Revenue(t)*sampled reinvestment_intensity = CapEx + increase in NWC - D&A; positive consumes cash.",
            "fcff_rule": "FCFF=EBIT*(1-tax_rate)-reinvestment. Stock compensation remains in operating costs and is never added back.",
            "tax_rate": tax_rate,
            "terminal_growth": terminal_growth,
            "terminal_value_rule": "FY5_FCFF*(1+terminal_growth)/(path_WACC-terminal_growth), discounted with FY5 discount_factor",
            "equity_bridge": "Enterprise value + 8655 cash and short-term investments - 13904 noncurrent debt, divided by 461.8 diluted shares. Current debt is unavailable (null), not observed as zero; the net-debt proxy is a limitation.",
            "full_year_fy1_output_reconciliation": "Simulation trajectory FY1 is H2 only. Model Outputs FY1 revenue/EBIT/EPS additionally include reported H1 actuals exactly once; simulation values are not discounted a second time.",
            "units": "USD millions except value_per_share in USD; rates decimals; shares millions",
        },
        "drivers": DRIVERS,
        "dependence": {
            "type": "gaussian_copula",
            "ordered_names": ORDERED_NAMES,
            "matrix": DECLARED_CORRELATION,
            "copula_correlation_note": "0.35 is the latent normal correlation for growth and margin; rank/marginal transformation means realized Pearson correlation need not equal 0.35. Other pairs are generated independently.",
            "rationale": "Positive growth-margin dependence reflects scale, fixed-cost absorption and fewer emergency markdowns in stronger demand; independence of the other pairs is a parsimonious limitation, not evidence of no economic dependence.",
        },
        "realized_correlation": {
            "ordered_names": ORDERED_NAMES,
            "matrix": realized,
            "measure": "Pearson correlation across the 10000 retained paths",
        },
        "trials": trials,
        "statistics": stats,
        "percentile_convention": "Sort values ascending; zero-based position (N-1)*q; linear interpolation between floor and ceil ranks. p50 is the median.",
        "limitations": [
            "Open assumptions are analyst scenarios conditioned on the frozen 2025-09-16 information set, not observed market prices or consensus.",
            "The four drivers are held constant within each path; the path FY2-FY5 growth chain starts from residual FY1 H2 and therefore is not a full-year base-case reconciliation.",
            "The triangular and beta bounds are explicit stress assumptions informed by historical volatility, not confidence intervals estimated from a complete quarterly panel.",
            "Only growth and margin are dependent. Reinvestment and discount-rate shocks are independent by construction; macro co-movement and parameter uncertainty are omitted.",
            "Terminal growth is fixed at 0.02 and WACC is bounded above it, so terminal-value uncertainty is incomplete and terminal value remains material.",
            "Current debt, FY1 H2 actual cash flow, comparable sales, traffic and ticket are unavailable or null in the frozen source; null is not treated as an observed zero, and operating narratives are not quantified as facts.",
            "Equity bridge uses FY0 noncurrent debt and FY0 cash plus short-term investments; latest-quarter debt and investments are unavailable. This is a proxy, not a current market capital structure.",
            "The distribution is a conditional DCF sensitivity distribution, not a stock-price forecast or a statement about future realized returns.",
        ],
    }


def recalculate_with_libreoffice(path):
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if not executable:
        return False
    with tempfile.TemporaryDirectory(prefix="target_lo_") as directory:
        subprocess.run(
            [
                executable,
                "--headless",
                "--convert-to",
                "xlsx",
                "--outdir",
                directory,
                str(path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
        )
        recalculated = Path(directory) / path.name
        if not recalculated.exists():
            raise RuntimeError("LibreOffice did not produce a recalculated workbook")
        shutil.copy2(recalculated, path)
    return True


def update_workbook(model_path, simulation):
    workbook = load_workbook(model_path)
    assumptions = workbook["Assumptions"]
    row_by_key = {
        assumptions.cell(row=row, column=1).value: row
        for row in range(1, assumptions.max_row + 1)
    }
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.save(model_path)
    recalculate_with_libreoffice(model_path)
    workbook = load_workbook(model_path)
    assumptions = workbook["Assumptions"]
    row_by_key = {
        assumptions.cell(row=row, column=1).value: row
        for row in range(1, assumptions.max_row + 1)
    }
    simulation_values = {
        "mc_seed": simulation["seed"],
        "mc_n_valid": simulation["n_valid"],
        "mc_n_rejected": simulation["n_rejected"],
        **{
            f"mc_{key}": simulation["statistics"][key]
            for key in ("mean", "p10", "p25", "p50", "p75", "p90")
        },
    }
    for key, value in simulation_values.items():
        if key in row_by_key:
            assumptions.cell(row=row_by_key[key], column=2, value=value)

    if "MC_Trials" in workbook.sheetnames:
        del workbook["MC_Trials"]
    sheet = workbook.create_sheet("MC_Trials")
    headers = ["path_id", *ORDERED_NAMES, "value_per_share"]
    for index in range(1, 6):
        headers.extend(
            f"{field}_y{index}"
            for field in ("revenue", "ebit", "reinvestment", "fcff", "discount_factor")
        )
    sheet.append(headers)
    for trial in simulation["trials"]:
        row = [
            trial["path_id"],
            *(trial[name] for name in ORDERED_NAMES),
            trial["value_per_share"],
        ]
        for year in trial["trajectory"]:
            row.extend(
                year[field]
                for field in ("revenue", "ebit", "reinvestment", "fcff", "discount_factor")
            )
        sheet.append(row)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:AF{sheet.max_row}"
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(fill_type="solid", fgColor="1F4E78")
    widths = {"A": 11, "B": 18, "C": 15, "D": 23, "E": 15, "F": 17}
    for index in range(7, 33):
        widths[sheet.cell(row=1, column=index).column_letter] = 18
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    for row in range(2, sheet.max_row + 1):
        for column in (2, 3, 4, 5):
            sheet.cell(row=row, column=column).number_format = "0.000000"
        sheet.cell(row=row, column=6).number_format = "0.0000"
        for year in range(5):
            start = 7 + year * 5
            for column in range(start, start + 4):
                sheet.cell(row=row, column=column).number_format = "0.0000"
            sheet.cell(row=row, column=start + 4).number_format = "0.000000"
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.save(model_path)
    recalculate_with_libreoffice(model_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as handle:
        inputs = json.load(handle)
    simulation = simulate(inputs)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(simulation, handle, ensure_ascii=False, indent=2, allow_nan=False)
    update_workbook(Path(args.model), simulation)
    print(
        f"seed={SEED} n_valid={simulation['n_valid']} n_rejected={simulation['n_rejected']} "
        f"p50={simulation['statistics']['p50']:.6f} mean={simulation['statistics']['mean']:.6f}"
    )


if __name__ == "__main__":
    main()
