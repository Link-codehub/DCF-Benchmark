#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


NUMERIC_ASSUMPTIONS = (
    "initial_growth",
    "terminal_revenue_growth",
    "steady_ebit_margin",
    "tax_rate",
    "da_to_revenue",
    "capex_to_revenue",
    "nwc_to_revenue",
    "interest_rate",
    "wacc",
    "terminal_growth",
    "net_debt",
    "cash_and_investments",
    "diluted_shares",
    "annual_diluted_share_change",
)


def require_finite(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def build_recomputation(input_data, assumptions):
    for name in NUMERIC_ASSUMPTIONS:
        require_finite(f"assumptions.{name}", assumptions.get(name))

    a = {name: float(assumptions[name]) for name in NUMERIC_ASSUMPTIONS}
    if not 0 <= a["tax_rate"] < 1:
        raise ValueError("tax_rate must be in [0, 1)")
    if a["initial_growth"] <= -1 or a["terminal_revenue_growth"] <= -1:
        raise ValueError("revenue growth rates must exceed -100%")
    if a["wacc"] <= a["terminal_growth"]:
        raise ValueError("WACC must exceed terminal growth")
    if a["diluted_shares"] <= 0 or a["annual_diluted_share_change"] <= -1:
        raise ValueError("share count must be positive and annual share change must exceed -100%")
    if a["da_to_revenue"] < 0 or a["capex_to_revenue"] < 0:
        raise ValueError("D&A and CapEx ratios cannot be negative")
    if a["net_debt"] < 0 or a["interest_rate"] < 0:
        raise ValueError("gross debt and interest rate cannot be negative")

    periods = input_data["fiscal_years"]
    fy0 = input_data["last_full_fiscal_year"]
    if fy0 != periods[-1]:
        raise ValueError("the last full fiscal year must be the final historical period")
    historical = input_data["historical"]
    base_revenue = require_finite("historical revenue", historical["revenue"][fy0])
    base_ebit = require_finite("historical EBIT", historical["operating_income"][fy0])
    st_investments = historical["st_investments"][fy0]
    if st_investments is None:
        raise ValueError("FY0 short-term investments are required for operating NWC")
    base_nwc = (
        historical["current_assets"][fy0]
        - historical["cash"][fy0]
        - st_investments
        - (historical["current_liabilities"][fy0] - historical["debt_current"][fy0])
    )
    base_margin = base_ebit / base_revenue
    base_shares = a["diluted_shares"]
    annual_interest = a["net_debt"] * a["interest_rate"]

    forecast = {}
    rows = []
    revenue = base_revenue
    previous_nwc = base_nwc
    previous_shares = base_shares
    pv_explicit = 0.0

    for index in range(1, 6):
        growth = a["terminal_revenue_growth"] + (
            a["initial_growth"] - a["terminal_revenue_growth"]
        ) * (5 - index) / 4
        revenue *= 1 + growth
        margin = base_margin + (a["steady_ebit_margin"] - base_margin) * index / 5
        ebit = revenue * margin
        da = revenue * a["da_to_revenue"]
        capex = revenue * a["capex_to_revenue"]
        nwc = revenue * a["nwc_to_revenue"]
        delta_nwc = nwc - previous_nwc
        reinvestment_component = da - capex - delta_nwc
        fcff = ebit * (1 - a["tax_rate"]) + reinvestment_component
        discount_factor = 1 / (1 + a["wacc"]) ** index

        ending_shares = previous_shares * (1 + a["annual_diluted_share_change"])
        average_shares = (previous_shares + ending_shares) / 2
        pretax_income = ebit - annual_interest
        income_tax = max(0.0, pretax_income * a["tax_rate"])
        net_income = pretax_income - income_tax
        eps = net_income / average_shares

        forecast[f"revenue_y{index}"] = revenue
        forecast[f"ebit_y{index}"] = ebit
        forecast[f"eps_y{index}"] = eps
        forecast[f"da_y{index}"] = da
        forecast[f"capex_y{index}"] = capex
        forecast[f"delta_nwc_y{index}"] = delta_nwc
        forecast[f"reinvestment_component_y{index}"] = reinvestment_component
        forecast[f"fcff_y{index}"] = fcff
        forecast[f"discount_factor_y{index}"] = discount_factor
        forecast[f"revenue_growth_y{index}"] = growth
        forecast[f"ebit_margin_y{index}"] = margin
        forecast[f"nwc_y{index}"] = nwc
        forecast[f"net_income_y{index}"] = net_income
        forecast[f"diluted_shares_y{index}"] = average_shares

        rows.append({
            "year": int(fy0[:4]) + index,
            "revenue": revenue,
            "ebit": ebit,
            "reinvestment_component": reinvestment_component,
            "fcff": fcff,
            "discount_factor": discount_factor,
        })
        pv_explicit += fcff * discount_factor
        previous_nwc = nwc
        previous_shares = ending_shares

    terminal_fcff = forecast["fcff_y5"]
    terminal_value = terminal_fcff * (1 + a["terminal_growth"]) / (
        a["wacc"] - a["terminal_growth"]
    )
    pv_terminal = terminal_value * forecast["discount_factor_y5"]
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value + a["cash_and_investments"] - a["net_debt"]
    value_per_share = equity_value / base_shares

    valuation = {
        "wacc": a["wacc"],
        "g": a["terminal_growth"],
        "terminal_growth": a["terminal_growth"],
        "tax_rate": a["tax_rate"],
        "net_debt": a["net_debt"],
        "cash_and_investments": a["cash_and_investments"],
        "diluted_shares": base_shares,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "value_per_share": value_per_share,
        "discount_years": [1, 2, 3, 4, 5],
        "terminal_year_fcff": terminal_fcff,
        "terminal_value_at_fy5": terminal_value,
        "pv_explicit_fcff": pv_explicit,
        "pv_terminal_value": pv_terminal,
    }
    return {
        "forecast": forecast,
        "valuation": valuation,
        "reconstruction": {
            "fy0": fy0,
            "base_revenue": base_revenue,
            "base_operating_nwc": base_nwc,
            "base_ebit_margin": base_margin,
            "annual_interest_expense": annual_interest,
            "rows": rows,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Rebuild Netflix forecasts and DCF from operating assumptions")
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as handle:
        input_data = json.load(handle)
    with open(args.model, encoding="utf-8") as handle:
        model = json.load(handle)
    result = build_recomputation(input_data, model["assumptions"])
    result["recompute_checks"] = {
        "source": "operating assumptions and public frozen history only",
        "forecast_or_valuation_results_read": False,
        "fcff_identity_max_absolute_error": max(
            abs(
                result["forecast"][f"fcff_y{i}"]
                - result["forecast"][f"ebit_y{i}"] * (1 - model["assumptions"]["tax_rate"])
                - result["forecast"][f"reinvestment_component_y{i}"]
            )
            for i in range(1, 6)
        ),
    }

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "recomputed.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(f"Wrote {output_path}; value_per_share={result['valuation']['value_per_share']:.6f}")


if __name__ == "__main__":
    main()
