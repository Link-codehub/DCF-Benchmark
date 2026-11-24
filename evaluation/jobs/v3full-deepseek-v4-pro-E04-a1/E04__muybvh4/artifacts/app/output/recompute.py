#!/usr/bin/env python3
"""Independent recomputation of Netflix DCF model.
Reads model.json for assumptions, inputs.json for historical FY0 anchors,
and independently rebuilds revenue, EBIT, reinvestment, FCFF, and valuation.
Does NOT echo model.json's forecast/valuation values directly."""

import argparse
import json
import os


def main():
    p = argparse.ArgumentParser(
        description="Independently recompute Netflix DCF from assumptions."
    )
    p.add_argument("--input", required=True, help="Path to inputs.json")
    p.add_argument("--model", required=True, help="Path to model.json")
    p.add_argument("--output", required=True, help="Output directory for recomputed.json")
    args = p.parse_args()

    with open(args.input) as f:
        inp = json.load(f)
    with open(args.model) as f:
        model = json.load(f)

    hist = inp["historical"]
    assumptions = model["assumptions"]

    # --- Extract assumptions ---
    growth_rates = assumptions["growth_rates"]
    ebit_margins = assumptions["ebit_margins"]
    tax_rate = assumptions["tax_rate"]
    da_pct = assumptions["da_to_revenue"]
    capex_pct = assumptions["capex_to_revenue"]
    nwc_pct = assumptions["nwc_to_revenue"]
    wacc = assumptions["wacc"]
    terminal_g = assumptions["terminal_growth"]
    shares = assumptions["diluted_shares"]
    net_debt = assumptions["net_debt"]
    cash_inv = assumptions["cash_and_investments"]

    # --- Historical anchors ---
    fy0_revenue = hist["revenue"]["2024-12-31"]

    # Compute FY0 NWC from raw history (independent of model.json)
    ca0 = hist["current_assets"]["2024-12-31"]
    cash0 = hist["cash"]["2024-12-31"]
    sti0 = hist["st_investments"]["2024-12-31"] or 0.0
    cl0 = hist["current_liabilities"]["2024-12-31"]
    cd0 = hist["debt_current"]["2024-12-31"] or 0.0
    fy0_nwc = ca0 - cash0 - sti0 - (cl0 - cd0)

    # --- Build revenue series ---
    revs = []
    r_prev = fy0_revenue
    for g in growth_rates:
        r_next = r_prev * (1.0 + g)
        revs.append(r_next)
        r_prev = r_next

    # --- EBIT ---
    ebits = [revs[i] * ebit_margins[i] for i in range(5)]

    # --- D&A, CapEx, NWC ---
    das = [revs[i] * da_pct for i in range(5)]
    capexs = [revs[i] * capex_pct for i in range(5)]
    nwcs = [revs[i] * nwc_pct for i in range(5)]

    # --- ΔNWC ---
    p_nwc = fy0_nwc
    delta_nwcs = []
    for i in range(5):
        dn = nwcs[i] - p_nwc
        delta_nwcs.append(dn)
        p_nwc = nwcs[i]

    # --- Reinvestment component (D&A - CapEx - ΔNWC) ---
    reinv_comps = [das[i] - capexs[i] - delta_nwcs[i] for i in range(5)]

    # --- FCFF = EBIT*(1-tax) + reinv_component ---
    fcffs = [ebits[i] * (1.0 - tax_rate) + reinv_comps[i] for i in range(5)]

    # --- Discount factors ---
    disc_years = [1, 2, 3, 4, 5]
    disc_factors = [1.0 / (1.0 + wacc) ** y for y in disc_years]

    # --- PV explicit period ---
    pv_explicit = sum(fcffs[i] * disc_factors[i] for i in range(5))

    # --- Terminal value (Gordon growth) ---
    terminal_fcff = fcffs[4]
    if wacc <= terminal_g:
        raise ValueError(f"WACC ({wacc}) must be > terminal growth ({terminal_g})")
    tv = terminal_fcff * (1.0 + terminal_g) / (wacc - terminal_g)
    pv_tv = tv * disc_factors[4]

    # --- Enterprise & equity value ---
    enterprise_value = pv_explicit + pv_tv
    equity_value = enterprise_value + cash_inv - net_debt
    value_per_share = equity_value / shares

    # --- Build output ---
    forecast = {}
    for i in range(5):
        yi = i + 1
        forecast[f"revenue_y{yi}"] = round(revs[i], 6)
        forecast[f"ebit_y{yi}"] = round(ebits[i], 6)
        forecast[f"da_y{yi}"] = round(das[i], 6)
        forecast[f"capex_y{yi}"] = round(capexs[i], 6)
        forecast[f"delta_nwc_y{yi}"] = round(delta_nwcs[i], 6)
        forecast[f"reinvestment_component_y{yi}"] = round(reinv_comps[i], 6)
        forecast[f"fcff_y{yi}"] = round(fcffs[i], 6)
        forecast[f"discount_factor_y{yi}"] = round(disc_factors[i], 10)

    valuation = {
        "wacc": wacc,
        "terminal_growth": terminal_g,
        "tax_rate": tax_rate,
        "net_debt": round(net_debt, 6),
        "cash_and_investments": round(cash_inv, 6),
        "diluted_shares": round(shares, 6),
        "enterprise_value": round(enterprise_value, 6),
        "equity_value": round(equity_value, 6),
        "value_per_share": round(value_per_share, 6),
        "discount_years": disc_years,
        "terminal_year_fcff": round(terminal_fcff, 6),
    }

    result = {
        "recomputed": {
            "fy0_revenue": fy0_revenue,
            "fy0_nwc": round(fy0_nwc, 6),
            "growth_rates_used": growth_rates,
            "ebit_margins_used": ebit_margins,
            "forecast": forecast,
            "valuation": valuation,
        }
    }

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, "recomputed.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"recomputed.json written to {out_path}")
    print(f"Value per share: {value_per_share:.2f}")


if __name__ == "__main__":
    main()