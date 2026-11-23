"""Independent numerical truth; deliberately never reads a workbook or expected.json."""
from __future__ import annotations
import datetime as dt

FLOW = ("revenue", "ebit", "da", "capex", "delta_nwc", "fcff", "discount_factor", "pv_fcff")


def date(value):
    return dt.date.fromisoformat(value) if isinstance(value, str) else value


def add_year(value):
    value = date(value)
    try:
        return value.replace(year=value.year + 1)
    except ValueError:
        return value.replace(year=value.year + 1, day=28)


def dates(s):
    result = [date(s["last_fy_end"])]
    for _ in range(s["horizon"]):
        result.append(add_year(result[-1]))
    return result


def history_truth(s):
    rows = sorted(s["history"], key=lambda r: (r["end"], r["start"]))
    last = [r for r in rows if r["fiscal_year"] == s["last_fy_end"][:4] and r["end"] <= s["last_fy_end"]]
    count = 4 if s["time_axis"]["history_frequency"] == "quarterly" else 2
    recent = [r for r in rows if r["end"] <= s["valuation_date"]][-count:]
    def values(group):
        revenue = sum(r["revenue"] for r in group)
        if s["accounting"]["normalized_history"]:
            ebit = sum(r["revenue"] - r["operating_cost_ex_sbc"] - r["sbc"] for r in group)
            reported = sum(r["revenue"] - r["operating_cost_ex_sbc"] - r["sbc"] + r["nonrecurring_gain"] for r in group)
        else:
            ebit = sum(r["ebit"] for r in group)
            reported = ebit
        return revenue, ebit, reported
    fy, ltm = values(last), values(recent)
    return {"fy_revenue": fy[0], "fy_normalized_ebit": fy[1], "fy_reported_ebit": fy[2],
            "ltm_revenue": ltm[0], "ltm_normalized_ebit": ltm[1], "ltm_reported_ebit": ltm[2]}


def operating(s, scenario=None):
    a = s["assumptions"]
    h = s["horizon"]
    case = a.get("scenario", 1) if scenario is None else scenario
    growth_delta = {1: 0.0, 2: a.get("upside_demand_delta", 0), 3: a.get("downside_demand_delta", 0)}[case]
    margin_delta = {1: 0.0, 2: a.get("upside_margin_delta", 0), 3: a.get("downside_margin_delta", 0)}[case]
    kind = s["business"]["driver"]
    driver = a.get("driver_rebase", a["driver0"])
    price = a.get("price_rebase", a["price0"])
    b = s["bridge"]
    prev_deferred = s.get("opening_deferred", 0.0) if "deferred_revenue" in s["enabled_modules"] else 0.0
    prev_operating_current_assets = (s.get("opening_debt", b["debt"]) + (b.get("lease_liability", 0.0) if "leases" in s["enabled_modules"] else 0.0)
        + s.get("opening_retained_earnings", 0.0) + s.get("contributed_capital", 0.0) + b.get("minority", 0.0)
        + s.get("opening_sbc_reserve", 0.0) + prev_deferred - s.get("opening_cash", b["cash"]) - b.get("investments", 0.0)
        - s.get("opening_ppe", 0.0) - (s.get("opening_rou", 0.0) if "leases" in s["enabled_modules"] else 0.0))
    prev_nwc = prev_operating_current_assets - prev_deferred
    prev_ppe = s.get("opening_ppe", 0.0)
    prev_rou = s.get("opening_rou", 0.0) if "leases" in s["enabled_modules"] else 0.0
    prev_lease = b.get("lease_liability", 0.0) if "leases" in s["enabled_modules"] else 0.0
    prev_debt = s.get("opening_debt", b["debt"])
    prev_nol = a.get("nol0", 0.0)
    prev_levered_nol = prev_nol
    deferred_tax_asset = 0.0
    cash = s.get("opening_cash", b["cash"])
    re = s.get("opening_retained_earnings", 0.0)
    capital = s.get("contributed_capital", 0.0)
    sbc_reserve = s.get("opening_sbc_reserve", 0.0)
    result = []
    for i in range(h):
        start = dates(s)[i]
        end = dates(s)[i + 1]
        val = date(s["valuation_date"])
        activity = ((end - max(start, val)).days / (end - start).days) if i == 0 else 1.0
        if activity <= 0:
            raise ValueError("valuation must precede the first forecast fiscal year end")
        opening_driver = driver
        if kind in ("subscription", "stores", "capacity", "installed_base"):
            attrition = driver * a.get("attrition_rate", [0] * h)[i]
            additions = a["driver_add"][i]
            if kind == "capacity" or "scenario" in s["enabled_modules"]:
                additions *= 1 + growth_delta
            driver = driver - attrition + additions
            average_driver = (opening_driver + driver) / 2
            if kind == "installed_base":
                activity_units = average_driver * a["service_frequency"][i]
            elif kind == "capacity":
                activity_units = average_driver * a["utilization"][i]
            else:
                activity_units = average_driver
        else:
            driver *= 1 + a["driver_growth"][i] + growth_delta
            activity_units = driver
        price *= 1 + a["price_growth"][i]
        full_revenue = activity_units * price
        core_revenue = full_revenue * activity
        segment_revenue = a.get("segment_revenue", [0] * h)[i] * activity
        revenue = core_revenue + segment_revenue
        core_ebit = core_revenue * (a["ebit_margin"][i] + margin_delta)
        segment_ebit = segment_revenue * a.get("segment_margin", [0] * h)[i]
        ebit = core_ebit + segment_ebit
        capex = revenue * a["capex_pct"][i] + a.get("extra_capex", [0] * h)[i] * activity
        ppe_dep = (prev_ppe + capex * .5) * a.get("ppe_rate", 0) * (end - start).days / 365
        ppe_close = prev_ppe + capex - ppe_dep
        rou_add = a.get("lease_additions", [0] * h)[i] * activity if "leases" in s["enabled_modules"] else 0.0
        rou_amort = (prev_rou + rou_add * .5) * a.get("rou_rate", 0) * (end - start).days / 365 if "leases" in s["enabled_modules"] else 0.0
        rou_close = prev_rou + rou_add - rou_amort
        lease_close = prev_lease + rou_add
        da = ppe_dep + rou_amort if "rolling_assets" in s["enabled_modules"] or "leases" in s["enabled_modules"] else revenue * a.get("da_pct", [0] * h)[i]
        deferred = full_revenue * a.get("deferred_pct", [0] * h)[i] if "deferred_revenue" in s["enabled_modules"] else 0.0
        delta_deferred = deferred - prev_deferred
        if "nwc_days" in s["enabled_modules"]:
            full_cogs = full_revenue * a["cogs_ratio"][i]
            nwc = full_revenue * a["dso"][i] / 365 + full_cogs * (a["dio"][i] - a["dpo"][i]) / 365 - deferred
        else:
            nwc = full_revenue * a["nwc_pct"][i] - deferred
        dnwc = nwc - prev_nwc
        taxable_before_nol = max(ebit, 0)
        nol_used = min(prev_nol, taxable_before_nol)
        tax = (taxable_before_nol - nol_used) * a["tax"]
        nol_close = prev_nol - nol_used + max(-ebit, 0)
        fcff = ebit - tax + da - capex - dnwc
        repayment = a.get("debt_repayment", [0] * h)[i] * activity
        borrowing = a.get("new_borrowing", [0] * h)[i] * activity
        interest = (prev_debt + borrowing * .5) * a.get("interest_rate", 0) * (end - start).days / 365
        debt = prev_debt - repayment + borrowing
        interest_tax_shield = interest * a["tax"]
        levered_tax = tax - interest_tax_shield
        prev_levered_nol = nol_close
        ni = ebit - interest - levered_tax
        sbc = revenue * a.get("sbc_pct", [0] * h)[i]
        sbc_reserve += sbc
        re_close = re + ni
        cash_taxes = levered_tax
        tax_accrual = 0.0
        deferred_tax_asset = 0.0
        cfo = ni + da + sbc - dnwc
        cash_close = cash + cfo - capex + borrowing - repayment
        operating_current_assets = nwc + deferred
        assets = cash_close + operating_current_assets + ppe_close + rou_close + b.get("investments", 0.0) + deferred_tax_asset
        liabilities_equity = debt + lease_close + deferred + re_close + capital + b.get("minority", 0.0) + sbc_reserve
        end_t = (end - val).days / 365
        interval = (end - max(start, val)).days / 365
        t = end_t - (interval / 2 if s["time_axis"]["midyear"] else 0)
        result.append({"activity": activity, "driver_close": driver, "average_driver": average_driver if kind != "volume_price" else driver,
            "unit_price": price, "full_revenue": full_revenue, "segment_revenue": segment_revenue,
            "revenue": revenue, "ebit": ebit, "capex": capex, "ppe_depreciation": ppe_dep,
            "ppe_close": ppe_close, "rou_additions": rou_add, "rou_amortization": rou_amort, "rou_close": rou_close,
            "da": da, "deferred_close": deferred, "cash_collections": revenue + delta_deferred,
            "nwc": nwc, "delta_nwc": dnwc, "nol_close": nol_close, "tax": tax, "fcff": fcff,
            "interest": interest, "debt_close": debt, "net_income": ni, "retained_earnings": re_close,
            "sbc": sbc, "sbc_reserve": sbc_reserve, "levered_tax": levered_tax, "cash_taxes": cash_taxes,
            "interest_tax_shield": interest_tax_shield, "deferred_tax_asset": deferred_tax_asset, "tax_accrual": tax_accrual,
            "accrual_adjustments": da + sbc - dnwc,
            "cfo": cfo, "cash_close": cash_close, "cash_link": cash_close - (cash + cfo - capex + borrowing - repayment),
            "operating_current_assets": operating_current_assets, "lease_liability_close": lease_close,
            "assets": assets, "liabilities_equity": liabilities_equity, "balance_difference": assets - liabilities_equity,
            "end_time": end_t, "discount_time": t})
        prev_nwc, prev_deferred, prev_ppe, prev_rou, prev_debt, prev_nol = nwc, deferred, ppe_close, rou_close, debt, nol_close
        prev_lease = lease_close
        cash, re = cash_close, re_close
    return result


def valuation(s, rows, wacc=None, growth=None, scenario=None):
    a = s["assumptions"]
    if wacc is None:
        if "capm" in s["enabled_modules"]:
            beta = a["beta_unlevered"] * (1 + (1 - a["tax"]) * a["target_de"])
            ke = a["risk_free"] + beta * a["erp"] + a.get("specific_premium", 0)
            wd = a["target_de"] / (1 + a["target_de"])
            wacc = (1 - wd) * ke + wd * a["cost_of_debt"] * (1 - a["tax"])
        else:
            beta = ke = 0.0
            wacc = a["wacc"]
    else:
        beta = ke = 0.0
    g = a["g"] if growth is None else growth
    wg = a.get("gordon_weight", 1.0)
    if wg > 0 and wacc - g < .02:
        raise ValueError("WACC less perpetual growth must be at least 2%")
    dfs = [(1 + wacc) ** -r["discount_time"] for r in rows]
    pv_rows = [r["fcff"] * df for r, df in zip(rows, dfs)]
    ebitda = rows[-1]["ebit"] + rows[-1]["da"]
    tv_g = rows[-1]["fcff"] * (1 + g) / (wacc - g) if wg else 0.0
    tv_x = ebitda * a.get("exit_multiple", 0) if wg < 1 else 0.0
    tv = wg * tv_g + (1 - wg) * tv_x
    pv_tv = tv * (1 + wacc) ** -rows[-1]["end_time"]
    pv_explicit = sum(pv_rows)
    ev = pv_explicit + pv_tv
    b = s["bridge"]
    lease = b.get("lease_liability", 0)
    debt = b["debt"] + lease
    equity = ev + b["cash"] + b.get("valuation_cash_adjustment", 0) + b.get("investments", 0) - debt - b.get("minority", 0)
    tsm = b.get("options", 0) * max(0, 1 - b.get("strike", 0) / b["share_price"]) if b.get("options", 0) else 0
    shares = b["shares"] + b.get("rsus", 0) + tsm
    out = {"levered_beta": beta, "cost_of_equity": ke, "wacc": wacc, "pv_explicit": pv_explicit,
        "tv_gordon": tv_g, "tv_exit": tv_x, "terminal_value": tv, "pv_terminal": pv_tv,
        "enterprise_value": ev, "equity_value": equity, "diluted_shares": shares, "value_per_share": equity / shares}
    for i, (r, df, pv) in enumerate(zip(rows, dfs, pv_rows)):
        out[f"discount_factor_p{i + 1}"] = df
        out[f"pv_fcff_p{i + 1}"] = pv
    return out


def compute(s):
    rows = operating(s)
    out = history_truth(s)
    out.update(valuation(s, rows))
    for i, r in enumerate(rows):
        for k, v in r.items():
            out[f"{k}_p{i + 1}"] = v
    a = s["assumptions"]
    if "scenario" in s["enabled_modules"]:
        for case, name in ((1, "base"), (2, "upside"), (3, "downside")):
            alt = operating(s, case)
            out[f"{name}_scenario_vps"] = valuation(s, alt, scenario=case)["value_per_share"]
    if "valuation_sensitivity" in s["enabled_modules"]:
        w = out["wacc"]
        for i, dw in enumerate(a["wacc_deltas"]):
            for j, dg in enumerate(a["g_deltas"]):
                out[f"sens_r{i + 1}c{j + 1}"] = valuation(s, rows, w + dw, a["g"] + dg)["value_per_share"]
    return {k: float(v) for k, v in out.items()}
