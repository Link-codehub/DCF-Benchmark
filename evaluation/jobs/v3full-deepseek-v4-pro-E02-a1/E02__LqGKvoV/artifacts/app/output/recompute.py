#!/usr/bin/env python3
"""
recompute.py — Independently reconstruct DCF valuation from operating assumptions
and public historical data. Does NOT echo model.json forecast/valuation fields.

Usage:
    python3 recompute.py --input INPUT --model MODEL --output DIR
    Writes DIR/recomputed.json
"""

import argparse
import json
import math
import os
import sys


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def recompute(input_path, model_path, output_dir):
    inputs = load_json(input_path)
    model = load_json(model_path)

    h = inputs['historical']
    a = model['assumptions']
    v = model.get('valuation', {})

    # ── Extract base year data ──────────────────────────────────────────
    rev_fy0 = h['revenue']['2024-10-27']
    ebit_fy0 = h['operating_income']['2024-10-27']
    eps_fy0 = h['eps_diluted']['2024-10-27']

    # ── Extract assumptions ─────────────────────────────────────────────
    tax_rate = a['tax_rate']
    wacc = a['wacc']
    terminal_g = a['terminal_growth']
    da_pct = a['da_to_revenue']
    capex_pct = a['capex_to_revenue']
    nwc_pct = a['nwc_to_revenue']
    net_debt = a['net_debt']
    cash = a['cash_and_investments']
    shares = a['diluted_shares']
    int_rate = a['interest_rate']
    rev_growth_path = a['revenue_growth_path']
    ebit_margin_path = a['ebit_margin_path']
    total_debt_path = a.get('total_debt_forecast', [50000, 49000, 48000, 47000, 46000])
    shares_path = a.get('shares_forecast', [274.0, 271.0, 268.0, 265.0, 262.0])

    # ── Reconstruct NWC base ────────────────────────────────────────────
    nwc_fy0 = rev_fy0 * nwc_pct

    # ── Build five-year forecast ────────────────────────────────────────
    rev = []
    ebit = []
    da = []
    capex = []
    nwc = []
    delta_nwc = []
    reinv = []
    fcff = []
    df = []
    interest = []
    pretax = []
    net_income = []
    eps = []

    rev_prev = rev_fy0
    nwc_prev = nwc_fy0

    for i in range(5):
        # Revenue
        r = rev_prev * (1 + rev_growth_path[i])
        rev.append(r)
        rev_prev = r

        # EBIT
        op = r * ebit_margin_path[i]
        ebit.append(op)

        # D&A and CapEx (proportional to revenue)
        da_val = r * da_pct
        capex_val = r * capex_pct
        da.append(da_val)
        capex.append(capex_val)

        # NWC
        nwc_val = r * nwc_pct
        nwc.append(nwc_val)
        dn = nwc_val - nwc_prev
        delta_nwc.append(dn)
        nwc_prev = nwc_val

        # Reinvestment component: D&A − CapEx − ΔNWC
        r_inv = da_val - capex_val - dn
        reinv.append(r_inv)

        # FCFF = EBIT × (1 − tax) + reinvestment_component
        f = op * (1 - tax_rate) + r_inv
        fcff.append(f)

        # Discount factor
        d = 1.0 / (1 + wacc) ** (i + 1)
        df.append(d)

        # Interest expense
        int_val = total_debt_path[i] * int_rate
        interest.append(int_val)

        # Net income
        pt = op - int_val
        pretax.append(pt)
        ni = pt * (1 - tax_rate)
        net_income.append(ni)
        eps_val = ni / shares_path[i]
        eps.append(eps_val)

    # ── Valuation ───────────────────────────────────────────────────────
    pv_fcff = [fcff[i] * df[i] for i in range(5)]
    pv_fcff_sum = sum(pv_fcff)

    tv_undisc = fcff[4] * (1 + terminal_g) / (wacc - terminal_g)
    pv_tv = tv_undisc * df[4]

    enterprise_value = pv_fcff_sum + pv_tv
    equity_value = enterprise_value + cash - net_debt
    value_per_share = equity_value / shares

    # ── Build output ────────────────────────────────────────────────────
    forecast = {}
    for i in range(5):
        yi = i + 1
        forecast.update({
            f"revenue_y{yi}": round(rev[i], 2),
            f"ebit_y{yi}": round(ebit[i], 2),
            f"eps_y{yi}": round(eps[i], 2),
            f"da_y{yi}": round(da[i], 2),
            f"capex_y{yi}": round(capex[i], 2),
            f"delta_nwc_y{yi}": round(delta_nwc[i], 2),
            f"nwc_y{yi}": round(nwc[i], 2),
            f"reinvestment_component_y{yi}": round(reinv[i], 2),
            f"fcff_y{yi}": round(fcff[i], 2),
            f"discount_factor_y{yi}": round(df[i], 8),
            f"interest_expense_y{yi}": round(interest[i], 2),
            f"pretax_income_y{yi}": round(pretax[i], 2),
            f"net_income_y{yi}": round(net_income[i], 2)
        })

    recomputed = {
        "historical": {
            "revenue_fy0": rev_fy0,
            "ebit_fy0": ebit_fy0,
            "eps_fy0": eps_fy0,
            "nwc_fy0": round(nwc_fy0, 2)
        },
        "assumptions_used": {
            "revenue_growth_path": rev_growth_path,
            "ebit_margin_path": ebit_margin_path,
            "tax_rate": tax_rate,
            "da_to_revenue": da_pct,
            "capex_to_revenue": capex_pct,
            "nwc_to_revenue": nwc_pct,
            "interest_rate": int_rate,
            "wacc": wacc,
            "terminal_growth": terminal_g,
            "net_debt": net_debt,
            "cash_and_investments": cash,
            "diluted_shares": shares
        },
        "forecast": forecast,
        "valuation": {
            "wacc": wacc,
            "terminal_growth": terminal_g,
            "tax_rate": tax_rate,
            "net_debt": net_debt,
            "cash_and_investments": cash,
            "diluted_shares": shares,
            "discount_years": [1.0, 2.0, 3.0, 4.0, 5.0],
            "terminal_year_fcff": round(fcff[4], 2),
            "pv_fcff_sum": round(pv_fcff_sum, 2),
            "terminal_value_undiscounted": round(tv_undisc, 2),
            "pv_terminal_value": round(pv_tv, 2),
            "enterprise_value": round(enterprise_value, 2),
            "equity_value": round(equity_value, 2),
            "value_per_share": round(value_per_share, 2)
        }
    }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'recomputed.json')
    with open(output_path, 'w') as f:
        json.dump(recomputed, f, indent=2)

    print(f"Recomputed valuation written to {output_path}")
    print(f"  Value per share: {value_per_share:.2f}")
    print(f"  Enterprise value: {enterprise_value:.2f}")
    print(f"  PV of FCFFs: {pv_fcff_sum:.2f}")
    print(f"  PV of terminal value: {pv_tv:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Independently reconstruct DCF valuation from model assumptions")
    parser.add_argument("--input", required=True, help="Path to inputs.json")
    parser.add_argument("--model", required=True, help="Path to model.json")
    parser.add_argument("--output", required=True, help="Output directory for recomputed.json")
    args = parser.parse_args()

    recompute(args.input, args.model, args.output)