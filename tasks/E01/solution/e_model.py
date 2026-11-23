#!/usr/bin/env python3
import math


def value(row, year, fallback=0.0):
    result = row.get(year)
    return fallback if result is None else float(result)


def historical_nwc(history, year):
    return ((value(history["current_assets"], year) - value(history["cash"], year)
             - value(history["st_investments"], year))
            - (value(history["current_liabilities"], year) - value(history["debt_current"], year)))


def summarize_history(data):
    years = data["fiscal_years"]
    history = data["historical"]
    last = years[-1]
    initial_growth = (value(history["revenue"], last) / value(history["revenue"], years[-4])) ** (1 / 3) - 1
    margin = sum(value(history["operating_income"], year) / value(history["revenue"], year) for year in years[-3:]) / 3
    tax = sum(value(history["income_tax"], year) / value(history["pretax_income"], year) for year in years[-3:]) / 3
    tax = min(0.30, max(0.12, tax))
    revenue = value(history["revenue"], last)
    nwc = historical_nwc(history, last)
    prior_nwc = historical_nwc(history, years[-2])
    return {
        "initial_growth": initial_growth, "steady_ebit_margin": margin, "tax_rate": tax,
        "da_to_revenue": value(history["da"], last) / revenue,
        "capex_to_revenue": value(history["capex"], last) / revenue,
        "nwc_to_revenue": nwc / revenue,
        "initial_revenue": revenue, "initial_nwc": nwc, "initial_shares": value(history["diluted_shares_wavg"], last),
        "growth_observations": [value(history["revenue"], years[i]) / value(history["revenue"], years[i - 1]) - 1 for i in range(1, len(years))],
        "margin_observations": [value(history["operating_income"], year) / value(history["revenue"], year) for year in years],
        "reinvestment_observations": [(value(history["capex"], year) + historical_nwc(history, year) - historical_nwc(history, years[i - 1]) - value(history["da"], year)) / value(history["revenue"], year) for i, year in enumerate(years) if i and historical_nwc(history, year) is not None],
    }


def default_assumptions(data):
    summary = summarize_history(data)
    last = data["fiscal_years"][-1]
    history = data["historical"]
    return {
        "initial_growth": summary["initial_growth"], "terminal_revenue_growth": 0.025,
        "steady_ebit_margin": summary["steady_ebit_margin"], "tax_rate": summary["tax_rate"],
        "da_to_revenue": summary["da_to_revenue"], "capex_to_revenue": summary["capex_to_revenue"],
        "nwc_to_revenue": summary["nwc_to_revenue"], "interest_rate": 0.025,
        "wacc": min(0.13, max(0.075, data["market_observation"]["treasury_10y"] + 0.05)),
        "terminal_growth": 0.025,
        "net_debt": value(history["debt_current"], last) + value(history["debt_noncurrent"], last),
        "cash_and_investments": value(history["cash"], last) + value(history["st_investments"], last),
        "diluted_shares": summary["initial_shares"],
    }


def compute(data, assumptions):
    history = data["historical"]
    fy0 = data["fiscal_years"][-1]
    variant = data["reported_partial_period"]["type"]
    actual = data["reported_partial_period"]["quarters"]
    actual_revenue = sum(float(row["revenue"]) for row in actual)
    actual_ebit = sum(float(row["operating_income"]) for row in actual)
    prior = data["reported_partial_period"].get("prior_year_quarters", [])
    prior_revenue = sum(float(row["revenue"]) for row in prior)
    prior_ebit = sum(float(row.get("operating_income") or 0) for row in prior)
    summary = summarize_history(data)
    initial_revenue = summary["initial_revenue"]
    prior_nwc = summary["initial_nwc"]
    times = data["reported_partial_period"]["timing"]["discount_years"]
    result = {"hist_revenue_fy0": initial_revenue, "hist_ebit_fy0": value(history["operating_income"], fy0),
              "hist_eps_fy0": value(history["eps_diluted"], fy0),
              "actual_partial_revenue_y1": actual_revenue, "actual_partial_ebit_y1": actual_ebit}
    previous_full_revenue = initial_revenue
    previous_residual_revenue = initial_revenue
    previous_full_nwc = prior_nwc
    present_value = 0.0
    for year in range(1, 6):
        growth = assumptions["initial_growth"] + (assumptions["terminal_revenue_growth"] - assumptions["initial_growth"]) * (year - 1) / 4
        if year == 1 and variant != "annual":
            base = prior_revenue or actual_revenue
            residual_revenue = base * (1 + growth)
            full_revenue = actual_revenue + residual_revenue
            residual_ebit = residual_revenue * assumptions["steady_ebit_margin"]
            full_ebit = actual_ebit + residual_ebit
            operating_revenue = residual_revenue
            operating_ebit = residual_ebit
            current_nwc = previous_full_nwc * (full_revenue / previous_full_revenue)
            delta_nwc = current_nwc - previous_full_nwc
            previous_residual_revenue = residual_revenue
        else:
            if year > 1 and variant != "annual":
                full_revenue = previous_full_revenue * (1 + growth)
                full_ebit = full_revenue * assumptions["steady_ebit_margin"]
                operating_revenue = full_revenue
                operating_ebit = full_ebit
                previous_residual_revenue = full_revenue
            else:
                full_revenue = previous_full_revenue * (1 + growth)
                full_ebit = full_revenue * assumptions["steady_ebit_margin"]
                operating_revenue = full_revenue
                operating_ebit = full_ebit
            current_nwc = full_revenue * assumptions["nwc_to_revenue"]
            delta_nwc = current_nwc - previous_full_nwc
        da = operating_revenue * assumptions["da_to_revenue"]
        capex = operating_revenue * assumptions["capex_to_revenue"]
        reinvestment = da - capex - delta_nwc
        fcff = operating_ebit * (1 - assumptions["tax_rate"]) + reinvestment
        discount_years = times[year - 1]
        discount_factor = 1 / (1 + assumptions["wacc"]) ** discount_years
        present_value += fcff * discount_factor
        eps = (full_ebit - assumptions["net_debt"] * assumptions["interest_rate"]) * (1 - assumptions["tax_rate"]) / assumptions["diluted_shares"]
        result.update({f"revenue_y{year}": full_revenue, f"ebit_y{year}": full_ebit, f"eps_y{year}": eps,
                       f"da_y{year}": da, f"capex_y{year}": capex, f"delta_nwc_y{year}": delta_nwc,
                       f"reinvestment_component_y{year}": reinvestment, f"fcff_y{year}": fcff,
                       f"discount_factor_y{year}": discount_factor, f"discount_years_y{year}": discount_years,
                       f"operating_revenue_y{year}": operating_revenue})
        previous_full_revenue = full_revenue
        previous_full_nwc = current_nwc
    result.update({"residual_revenue_y1": result["revenue_y1"] - actual_revenue,
                   "residual_fcff_y1": result["fcff_y1"], "residual_discount_years": times[0]})
    terminal = result["fcff_y5"] * (1 + assumptions["terminal_growth"]) / (assumptions["wacc"] - assumptions["terminal_growth"])
    enterprise = present_value + terminal * result["discount_factor_y5"]
    equity = enterprise + assumptions["cash_and_investments"] - assumptions["net_debt"]
    valuation = {"enterprise_value": enterprise, "equity_value": equity,
                 "value_per_share": equity / assumptions["diluted_shares"],
                 "discount_years": times, "terminal_year_fcff": result["fcff_y5"]}
    return result, valuation


def historical_outputs(data):
    history = data["historical"]
    year = data["fiscal_years"][-1]
    return {"hist_revenue_fy0": value(history["revenue"], year),
            "hist_ebit_fy0": value(history["operating_income"], year),
            "hist_eps_fy0": value(history["eps_diluted"], year)}
