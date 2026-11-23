"""v3 independent numerical truth. No workbook or expected file is read here."""
import copy
import datetime as dt
import math
import sys
from pathlib import Path

import v2_model as v2


def date(value):
    return dt.date.fromisoformat(value) if isinstance(value, str) else value


def add_year(value):
    return v2.add_year(value)


def history(s):
    if s["time_axis"]["history_frequency"] != "mixed_h1_q":
        return v2.history_truth(s)
    rows = sorted(s["history"], key=lambda r: (r["end"], r["start"]))
    end = s["last_fy_end"]
    fy = [r for r in rows if r["fiscal_year"] == end[:4] and r["end"] <= end]
    h1 = [r for r in rows if r["end"] == end][-1:]
    bridge = [r for r in rows if end < r["end"] <= s["valuation_date"]]
    if len(h1) != 1 or len(bridge) != 1 or bridge[0]["period_type"] != "bridge_quarter":
        raise ValueError("mixed LTM must have one latest H1 and one subsequent bridge quarter")
    def values(group):
        revenue = sum(r["revenue"] for r in group)
        ebit = sum(r["revenue"] - r["operating_cost_ex_sbc"] - r["sbc"] for r in group)
        reported = ebit + sum(r["nonrecurring_gain"] for r in group)
        return revenue, ebit, reported
    a, b = values(fy), values(h1 + bridge)
    return {"fy_revenue": a[0], "fy_normalized_ebit": a[1], "fy_reported_ebit": a[2],
            "ltm_revenue": b[0], "ltm_normalized_ebit": b[1], "ltm_reported_ebit": b[2],
            "ltm_h1_revenue": h1[0]["revenue"], "ltm_bridge_quarter_revenue": bridge[0]["revenue"]}


def operating(s, scenario=None):
    """Use v2 operating arithmetic with v3 semantic dates and accounting consistency."""
    if s.get("history"):
        s = copy.deepcopy(s)
        days = sorted((date(r["end"]) - date(r["start"])).days + 1 for r in s["history"])
        s["time_axis"]["history_frequency"] = "quarterly" if sum(days) / len(days) < 120 else "semiannual"
    rows = v2.operating(s, scenario)
    a = s["assumptions"]
    for i, row in enumerate(rows):
        activity = row["activity"]
        if i == 0:
            start, end = v2.dates(s)[:2]
            activity = (end - max(start, date(s["valuation_date"]))).days / (end - start).days
            scale = activity / row["activity"]
            for key in ("revenue", "ebit", "capex", "sbc"):
                row[key] *= scale
            row["activity"] = activity
            row["fcff"] = row["ebit"] - row["tax"] + row["da"] - row["capex"] - row["delta_nwc"]
        if i == 0 and (s.get("nwc_opening_basis") == "last_fiscal_year_end" or s["c_structure"] not in ("simple_dcf", "three_statements_dcf", "debt_schedule_dcf")):
            row["delta_nwc"] = row["nwc"] - s["opening_nwc"]
            row["fcff"] = row["ebit"] - row["tax"] + row["da"] - row["capex"] - row["delta_nwc"]
        if "intangible_pool" in s["enabled_modules"]:
            opening = s.get("opening_intangible", 0.0) if i == 0 else rows[i - 1]["intangible_close"]
            addition = a["intangible_additions"][i] * activity
            amortization = (opening + addition * .5) * a["intangible_rate"] * row["full_days"] / 365 if "full_days" in row else 0
            if not amortization:
                start = v2.dates(s)[i]
                end = v2.dates(s)[i + 1]
                amortization = (opening + addition * .5) * a["intangible_rate"] * (end - start).days / 365
            close = opening + addition - amortization
            row.update(intangible_additions=addition, intangible_amortization=amortization,
                       intangible_close=close, da=row["da"] + amortization)
        if scenario is not None and "scenario" in s["enabled_modules"]:
            delta = {1: 0, 2: a["upside_reinvestment_delta"], 3: a["downside_reinvestment_delta"]}[scenario]
            old_capex = row["capex"]
            row["capex"] = old_capex * (1 + delta)
            opening_ppe = s["opening_ppe"] if i == 0 else rows[i - 1]["ppe_close"]
            depreciation = (opening_ppe + row["capex"] * .5) * a["ppe_rate"] * (v2.dates(s)[i + 1] - v2.dates(s)[i]).days / 365
            row["da"] += depreciation - row["ppe_depreciation"]
            row["ppe_depreciation"] = depreciation
            row["ppe_close"] = opening_ppe + row["capex"] - depreciation
        statement_open = s.get("opening_nwc_valuation_date", s["opening_nwc"]) if i == 0 else rows[i - 1]["nwc"]
        row["statement_opening_nwc"] = statement_open
        row["statement_delta_nwc"] = row["nwc"] - statement_open
        if "cfo" in row:
            row["accrual_adjustments"] = row["da"] + row["sbc"] - row["statement_delta_nwc"]
            row["cfo"] = row["net_income"] + row["accrual_adjustments"]
            prior_cash = s.get("opening_cash", s["bridge"]["cash"]) if i == 0 else rows[i - 1]["cash_close"]
            borrowing = a.get("new_borrowing", [0] * len(rows))[i] * activity
            repayment = a.get("debt_repayment", [0] * len(rows))[i] * activity
            row["cash_close"] = prior_cash + row["cfo"] - row["capex"] + borrowing - repayment
            row["cash_link"] = 0.0
            row["assets"] = row["cash_close"] + row["operating_current_assets"] + row["ppe_close"] + row["rou_close"] + s["bridge"].get("investments", 0) + row["deferred_tax_asset"]
            row["balance_difference"] = row["assets"] - row["liabilities_equity"]
        row["fcff"] = row["ebit"] - row["tax"] + row["da"] - row["capex"] - row["delta_nwc"] - row.get("intangible_additions", 0)
    return rows


def wacc(s):
    a = s["assumptions"]
    if "capm" not in s["enabled_modules"]:
        return a["wacc"]
    beta = a["beta_unlevered"] * (1 + (1 - a["tax"]) * a["target_de"])
    ke = a["risk_free"] + beta * a["erp"] + a.get("specific_premium", 0)
    wd = a["target_de"] / (1 + a["target_de"])
    return (1 - wd) * ke + wd * a["cost_of_debt"] * (1 - a["tax"])


def shares(s):
    b = s["bridge"]
    dilution = b.get("options", 0) * max(0, 1 - b.get("strike", 0) / b["share_price"]) if b.get("options") else 0
    return b["shares"] + b.get("rsus", 0) + dilution


def bridge(s, ev):
    b = s["bridge"]
    return ev + b["cash"] + b.get("valuation_cash_adjustment", 0) + b.get("investments", 0) - b["debt"] - b.get("lease_liability", 0) - b.get("minority", 0)


def dcf(s, rows, rate=None, growth=None, multiple=None, method="gordon"):
    a = s["assumptions"]
    r = wacc(s) if rate is None else rate
    g = a["g"] if growth is None else growth
    x = a.get("exit_multiple", 8) if multiple is None else multiple
    flows = [row["ebit"] - row.get("tax", row["ebit"] * a["tax"]) + row["da"] - row["capex"] - row["delta_nwc"] - row.get("intangible_additions", 0) for row in rows]
    pv = [flow * (1 + r) ** -row["discount_time"] for flow, row in zip(flows, rows)]
    ebitda = rows[-1]["ebit"] + rows[-1]["da"]
    tv_g = rows[-1]["fcff"] * (1 + g) / (r - g)
    tv_x = ebitda * x
    terminal = a.get("gordon_weight", 1.0) * tv_g + (1 - a.get("gordon_weight", 1.0)) * tv_x if method == "weighted" else tv_g if method == "gordon" else tv_x
    pv_tv = terminal * (1 + r) ** -rows[-1]["end_time"]
    ev = sum(pv) + pv_tv
    equity = bridge(s, ev)
    return {"wacc": r, "terminal_growth": g, "exit_multiple": x,
            "tv_gordon": tv_g, "tv_exit": tv_x, "terminal_value": terminal,
            "pv_explicit": sum(pv), "pv_terminal": pv_tv,
            "enterprise_value": ev, "equity_value": equity,
            "diluted_shares": shares(s), "value_per_share": equity / shares(s)}


def solve_rate(fn, low, high):
    flo, fhi = fn(low), fn(high)
    if flo * fhi > 0:
        raise ValueError(f"reverse valuation has no bracketed solution: {flo}, {fhi}")
    for _ in range(200):
        mid = (low + high) / 2
        fm = fn(mid)
        if abs(fm) < 1e-10:
            return mid
        if flo * fm <= 0:
            high, fhi = mid, fm
        else:
            low, flo = mid, fm
    return (low + high) / 2


def compute(s):
    family = s["family"]
    if family == "A":
        return industry(s)
    structure = s["c_structure"]
    rows = operating(s)
    if structure == "multi_method":
        return multi(s, rows)
    if structure == "scenario_operating_model":
        return scenarios(s)
    if structure == "segment_sotp":
        return sotp(s, rows)
    if structure == "risk_adjusted_pipeline":
        return pipeline(s, rows)
    out = history(s)
    out.update(v2.valuation(s, rows))
    for i, row in enumerate(rows):
        for k, value in row.items():
            out[f"{k}_p{i + 1}"] = value
    return {k: float(v) for k, v in out.items()}


def multi(s, rows):
    gordon = dcf(s, rows, method="gordon")
    exit_ = dcf(s, rows, method="exit")
    out = history(s)
    for prefix, value in (("gordon", gordon), ("exit", exit_)):
        for key, item in value.items():
            out[f"{prefix}_{key}"] = item
    a = s["assumptions"]
    r, g, x = gordon["wacc"], a["g"], a["exit_multiple"]
    out["implied_ev_ebitda_gordon"] = gordon["tv_gordon"] / (rows[-1]["ebit"] + rows[-1]["da"])
    f, m = rows[-1]["fcff"], exit_["tv_exit"]
    out["implied_g_exit"] = (r * m - f) / (m + f)
    target = s["market"]["market_price"] * shares(s)
    def difference(rate):
        return bridge(s, dcf(s, rows, rate=rate, method="gordon")["enterprise_value"]) - target
    out["implied_wacc_market"] = solve_rate(difference, a["g"] + .021, .30)
    for i, row in enumerate(rows):
        for k in ("revenue", "ebit", "da", "capex", "delta_nwc", "fcff", "discount_time"):
            out[f"{k}_p{i + 1}"] = row[k]
    low = dcf(s, rows, rate=r + a["valuation_wacc_delta"], growth=g - a["valuation_g_delta"], method="gordon")
    high = dcf(s, rows, rate=r - a["valuation_wacc_delta"], growth=g + a["valuation_g_delta"], method="gordon")
    out["valuation_low_vps"] = min(low["value_per_share"], high["value_per_share"])
    out["valuation_high_vps"] = max(low["value_per_share"], high["value_per_share"])
    return {k: float(v) for k, v in out.items()}


def scenarios(s):
    out = history(s)
    a = s["assumptions"]
    names = ((1, "base"), (2, "bull"), (3, "bear"))
    for case, name in names:
        rows = operating(s, case)
        delta = {1: 0, 2: a["upside_wacc_delta"], 3: a["downside_wacc_delta"]}[case]
        value = dcf(s, rows, rate=wacc(s) + delta)
        for i, row in enumerate(rows):
            for k in ("driver_close", "average_driver", "unit_price", "revenue", "ebit", "da", "capex", "delta_nwc", "fcff", "discount_time"):
                out[f"case_{name}_{k}_p{i + 1}"] = row[k]
        for key, item in value.items():
            out[f"case_{name}_{key}"] = item
    active = a["scenario"]
    name = dict(names)[active]
    for i in range(s["horizon"]):
        for k in ("driver_close", "average_driver", "unit_price", "revenue", "ebit", "da", "capex", "delta_nwc", "fcff", "discount_time"):
            out[f"{k}_p{i + 1}"] = out[f"case_{name}_{k}_p{i + 1}"]
    for key in dcf(s, operating(s, active), rate=wacc(s) + {1: 0, 2: a["upside_wacc_delta"], 3: a["downside_wacc_delta"]}[active]):
        out[key] = out[f"case_{name}_{key}"]
    return {k: float(v) for k, v in out.items()}


def segment_rows(s, name):
    """Each segment independently rolls demand, price, margin, NWC and assets."""
    z = s["segments"][name]
    a = s["assumptions"]
    result = []
    nwc = z["opening_nwc"]
    ppe = z["opening_ppe"]
    for i in range(s["horizon"]):
        start, end = v2.dates(s)[i:i + 2]
        activity = (end - max(start, date(s["valuation_date"]))).days / (end - start).days if i == 0 else 1
        opening = z["driver0"] if i == 0 else result[-1]["driver_close"]
        close = opening * (1 - z["attrition_rate"][i]) + z["driver_add"][i]
        average = (opening + close) / 2
        price = z["price0"] if i == 0 else result[-1]["unit_price"]
        price *= 1 + z["price_growth"][i]
        full_revenue = average * price
        revenue = full_revenue * activity
        ebit = revenue * z["ebit_margin"][i]
        capex = revenue * z["capex_pct"][i]
        depreciation = (ppe + capex * .5) * a["ppe_rate"] * (end - start).days / 365
        ppe_close = ppe + capex - depreciation
        new_nwc = full_revenue * z["nwc_pct"][i]
        delta_nwc = new_nwc - nwc
        fcff = ebit * (1 - a["tax"]) + depreciation - capex - delta_nwc
        end_time = (end - date(s["valuation_date"])).days / 365
        interval = (end - max(start, date(s["valuation_date"]))).days / 365
        result.append({"driver_close": close, "average_driver": average, "unit_price": price,
            "revenue": revenue, "ebit": ebit, "capex": capex, "depreciation": depreciation,
            "da": depreciation, "ppe_close": ppe_close, "nwc": new_nwc, "delta_nwc": delta_nwc,
            "fcff": fcff, "end_time": end_time,
            "discount_time": end_time - (interval / 2 if s["time_axis"]["midyear"] else 0)})
        nwc, ppe = new_nwc, ppe_close
    return result


def sotp(s, rows):
    out = history(s)
    ev = 0
    for name in sorted(s["segments"]):
        sr = segment_rows(s, name)
        z = s["segments"][name]
        for i, row in enumerate(sr):
            for k, value in row.items():
                out[f"{name}_{k}_p{i + 1}"] = value
        value = dcf(s, sr, rate=wacc(s) + z["wacc_delta"], method=z["method"])
        for k, item in value.items():
            if k not in ("equity_value", "diluted_shares", "value_per_share"):
                out[f"{name}_{k}"] = item
        out[f"{name}_segment_enterprise_value"] = value["enterprise_value"]
        ev += value["enterprise_value"]
    out["sotp_enterprise_value"] = ev
    out["enterprise_value"] = ev
    out["equity_value"] = bridge(s, ev)
    out["diluted_shares"] = shares(s)
    out["value_per_share"] = out["equity_value"] / shares(s)
    out["wacc"] = wacc(s)
    return {k: float(v) for k, v in out.items()}


def pipeline(s, base_rows):
    out = history(s)
    value = dcf(s, base_rows)
    for k, item in value.items():
        out["existing_" + k] = item
    total = value["enterprise_value"]
    a = s["assumptions"]
    for name, p in s["projects"].items():
        flows = []
        for i in range(s["horizon"]):
            commissioned = i + 1 >= p["commissioning_period"]
            revenue = p["project_revenue"][i] * base_rows[i]["activity"] if commissioned else 0.0
            da = p["project_da"][i] * base_rows[i]["activity"] if commissioned else 0.0
            capex = p["project_operating_capex"][i] if commissioned else 0.0
            dnwc = p["project_delta_nwc"][i] if commissioned else 0.0
            flows.append(revenue * p["project_margin"] * (1 - a["tax"]) + da - p["construction_capex"][i] - capex - dnwc)
        total += p["success_probability"] * sum(flow * (1 + wacc(s)) ** -base_rows[i]["discount_time"] for i, flow in enumerate(flows))
        for i, flow in enumerate(flows):
            commissioned = i + 1 >= p["commissioning_period"]
            out[f"{name}_revenue_p{i + 1}"] = p["project_revenue"][i] * base_rows[i]["activity"] if commissioned else 0.0
            out[f"{name}_construction_capex_p{i + 1}"] = p["construction_capex"][i]
            out[f"{name}_unrisked_fcff_p{i + 1}"] = flow
            out[f"{name}_risk_adjusted_fcff_p{i + 1}"] = flow * p["success_probability"]
            out[f"{name}_discount_time_p{i + 1}"] = base_rows[i]["discount_time"]
        out[f"{name}_success_probability"] = p["success_probability"]
        out[f"{name}_risk_adjusted_pv"] = p["success_probability"] * sum(flow * (1 + wacc(s)) ** -base_rows[i]["discount_time"] for i, flow in enumerate(flows))
    out["pipeline_risk_adjusted_pv"] = total - value["enterprise_value"]
    out["enterprise_value"] = total
    out["equity_value"] = bridge(s, total)
    out["diluted_shares"] = shares(s)
    out["value_per_share"] = out["equity_value"] / shares(s)
    out["wacc"] = wacc(s)
    for i, row in enumerate(base_rows):
        for k in ("revenue", "ebit", "capex", "da", "delta_nwc", "fcff"):
            out[f"existing_{k}_p{i + 1}"] = row[k]
    return {k: float(v) for k, v in out.items()}


def industry(s):
    """Industry-adapted equity/residual-income or NAV models, never FCFF for financials or RE."""
    a, b = s["assumptions"], s["bridge"]
    out = {}
    n = s["horizon"]
    activity = s.get("residual_activity", 1.0)
    kind = s["industry"]
    if kind == "banking":
        loans, equity = a["opening_loans"], a["opening_equity"]
        rows = []
        for i in range(n):
            close_loans = loans * (1 + a["loan_growth"][i])
            required_equity = close_loans * a["risk_weight"] / a["target_capital_ratio"]
            beginning_required = loans * a["risk_weight"] / a["target_capital_ratio"]
            capital_headroom = equity - beginning_required
            nii = (loans + close_loans) / 2 * a["nim"][i]
            pp = nii + close_loans * a["fee_pct"][i] - close_loans * a["cost_pct"][i] - (loans + close_loans) / 2 * a["credit_cost"][i]
            ni = pp * (1 - a["tax"])
            # Dividends distribute excess current capital first; FCFE is net income less required capital increase.
            fcfe = ni - max(0, required_equity - equity) + max(0, equity - beginning_required)
            equity = max(equity + ni - ni, required_equity)
            equity = required_equity
            rows.append({"loans_close": close_loans, "nim": a["nim"][i], "net_interest_income": nii,
                "net_income": ni, "required_equity": required_equity, "fcfe": fcfe,
                "equity_close": equity})
            loans = close_loans
        r, g = a["cost_of_equity"], a["g"]
        pv = sum(row["fcfe"] / (1 + r) ** (i + 1 - (0.5 if s["time_axis"]["midyear"] else 0)) for i, row in enumerate(rows))
        terminal = rows[-1]["fcfe"] * (1 + g) / (r - g)
        value = pv + terminal / (1 + r) ** n
        for i, row in enumerate(rows):
            for k, v in row.items(): out[f"{k}_p{i+1}"] = v
        out.update(equity_value=value, equity_cost=r, terminal_value=terminal, diluted_shares=b["shares"], value_per_share=value / b["shares"])
    elif kind == "real_estate":
        values, rows = [], []
        for i in range(n):
            occupied = a["rentable_area"] * a["occupancy"][i]
            rent = occupied * a["rent_per_unit"][i]
            noi = rent * (1 - a["operating_cost_pct"][i])
            value = noi / a["cap_rate"][i]
            values.append(value)
            rows.append({"occupied_area": occupied, "rental_revenue": rent, "noi": noi, "property_value": value})
        nav = values[0] + b["cash"] - b["debt"] - a.get("capex_reserve", 0)
        for i, row in enumerate(rows):
            for k, v in row.items(): out[f"{k}_p{i+1}"] = v
        out.update(property_value_at_valuation=values[0], nav=nav, equity_value=nav, cap_rate=a["cap_rate"][0], diluted_shares=b["shares"], value_per_share=nav / b["shares"])
    elif kind == "insurance":
        rows = []
        for i in range(n):
            premium = a["opening_premium"] * math.prod(1 + x for x in a["premium_growth"][:i + 1])
            underwriting = premium * (1 - a["combined_ratio"][i])
            investment = a["investment_assets"] * a["investment_yield"][i]
            ni = (underwriting + investment) * (1 - a["tax"])
            fcfe = ni * (1 - a["retention_pct"][i])
            rows.append({"earned_premium": premium, "combined_ratio": a["combined_ratio"][i], "underwriting_profit": underwriting, "investment_income": investment, "net_income": ni, "fcfe": fcfe})
        r, g = a["cost_of_equity"], a["g"]
        value = sum(row["fcfe"] / (1 + r) ** (i + 1 - (.5 if s["time_axis"]["midyear"] else 0)) for i, row in enumerate(rows))
        terminal = rows[-1]["fcfe"] * (1 + g) / (r - g)
        value += terminal / (1 + r) ** n
        for i, row in enumerate(rows):
            for k, v in row.items(): out[f"{k}_p{i+1}"] = v
        out.update(equity_value=value, equity_cost=r, terminal_value=terminal, diluted_shares=b["shares"], value_per_share=value / b["shares"])
    else:
        rows = []
        driver = a["driver0"]
        for i in range(n):
            opening = driver
            if kind == "software_subscription":
                driver = driver * a["net_revenue_retention"][i] + a["new_arr"][i]
                revenue = (opening + driver) / 2 * activity
                metric = driver
                metric_key = "arr_close"
                extra = revenue * a["capitalized_rd_pct"][i]
                da = revenue * a["da_pct"][i]
            elif kind == "retail_chain":
                comparable = a["opening_stores"] * (1 - a.get("store_closure_rate", 0))
                driver = comparable + a["new_stores"][i]
                comp_rev = comparable * a["sales_per_store"] * (1 + a["same_store_growth"][i])
                new_rev = a["new_stores"][i] * a["sales_per_store"] * a["new_store_months"][i] / 12
                revenue = (comp_rev + new_rev) * activity
                metric = driver
                metric_key = "stores_close"
                extra, da = 0.0, revenue * a["da_pct"][i]
            elif kind == "manufacturing":
                driver = driver + a["capacity_additions"][i]
                volume = driver * a["utilization"][i]
                revenue = volume * a["unit_price"][i] * activity
                metric = volume
                metric_key = "effective_volume"
                extra, da = revenue * a["extra_capex_pct"][i], revenue * a["da_pct"][i]
            elif kind == "pharmaceutical":
                driver = driver * (1 + a["pre_cliff_growth"][i]) if i < a["cliff_period"] - 1 else driver * (1 - a["erosion_rate"][i])
                revenue = driver * a["unit_price"] * activity
                metric, metric_key = driver, "product_volume"
                extra, da = 0.0, revenue * a["da_pct"][i]
            elif kind == "energy_resources":
                base = a["opening_base_production"]
                for x in a["decline_rate"][:i + 1]: base *= 1 - x
                new = sum(a["development_capex"][j] / a["capex_per_unit"] for j in range(i + 1))
                driver = base + new
                revenue = driver * a["commodity_price"][i] * activity
                metric, metric_key = driver, "total_production"
                extra, da = a["development_capex"][i] * activity, revenue * a["da_pct"][i]
            elif kind == "utilities":
                driver = driver + a["rate_base_additions"][i]
                depreciation = driver * a["regulatory_depreciation_rate"][i]
                revenue = (driver * a["allowed_return"][i] + depreciation) * activity
                metric, metric_key = driver, "rate_base_close"
                extra, da = a["rate_base_additions"][i] * activity, depreciation * activity
            elif kind == "internet_platform":
                driver = driver * (1 - a["churn_rate"][i]) + a["new_users"][i]
                revenue = (opening + driver) / 2 * a["arpu"][i] * activity
                metric, metric_key = driver, "users_close"
                extra, da = 0.0, revenue * a["content_amortization_pct"][i]
            elif kind == "professional_services":
                driver = driver + a["hiring"][i]
                revenue = driver * a["utilization"][i] * a["fee_rate"][i] * activity
                metric, metric_key = driver, "billable_headcount"
                extra, da = 0.0, revenue * a["da_pct"][i]
            elif kind == "equipment_service":
                driver = driver * a["renewal_rate"][i] + a["new_installations"][i]
                revenue = (opening + driver) / 2 * a["service_frequency"][i] * a["service_price"][i] * activity
                metric, metric_key = driver, "installed_base_close"
                extra, da = 0.0, revenue * a["da_pct"][i]
            else:
                raise ValueError(kind)
            ebit = revenue * a["ebit_margin"][i]
            capex = revenue * a["capex_pct"][i] + extra
            nwc = revenue / activity * a["nwc_pct"][i] if activity else revenue * a["nwc_pct"][i]
            prior_nwc = a["opening_nwc"] if i == 0 else rows[-1]["nwc"]
            dnwc = nwc - prior_nwc
            fcff = ebit * (1 - a["tax"]) + da - capex - dnwc
            rows.append({metric_key: metric, "revenue": revenue, "ebit": ebit, "capex": capex, "da": da, "nwc": nwc, "delta_nwc": dnwc, "fcff": fcff})
        discount = [.5 + i if s["time_axis"]["midyear"] else 1 + i for i in range(n)]
        if s.get("residual_activity"):
            end = add_year(s["last_fy_end"])
            first_end = (end - date(s["valuation_date"])).days / 365
            interval = (end - date(s["valuation_date"])).days / 365
            discount = [first_end - (interval / 2 if s["time_axis"]["midyear"] else 0)] + [first_end + i for i in range(1, n)]
        r, g = a["wacc"], a["g"]
        pv = sum(row["fcff"] / (1 + r) ** discount[i] for i, row in enumerate(rows))
        terminal = rows[-1]["fcff"] * (1 + g) / (r - g)
        ev = pv + terminal / (1 + r) ** discount[-1]
        equity = bridge(s, ev)
        for i, row in enumerate(rows):
            for k, v in row.items(): out[f"{k}_p{i+1}"] = v
            out[f"discount_time_p{i+1}"] = discount[i]
        out.update(wacc=r, terminal_value=terminal, pv_terminal=terminal / (1 + r) ** discount[-1], enterprise_value=ev, equity_value=equity, diluted_shares=shares(s), value_per_share=equity / shares(s))
    return {k: float(v) for k, v in out.items()}


def apply_changes(s, changes):
    result = copy.deepcopy(s)
    for key, value in changes.items():
        target = result
        parts = key.split(".")
        for part in parts[:-1]:
            part = {"a": "assumptions", "b": "bridge", "seg": "segments", "proj": "projects", "m": "market"}.get(part, part)
            target = target[int(part)] if isinstance(target, list) else target[part]
        leaf = parts[-1]
        if isinstance(target, list): target[int(leaf)] = value
        else: target[leaf] = value
    return result
