"""Public facts, formula-only reference workbook, and semantic layout discovery."""
from __future__ import annotations
import datetime as dt, json
from pathlib import Path
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter as L
from model import compute, FLOW


def path_value(s, key):
    target = s
    for p in key.split("."):
        target = target[p]
    return target


def flatten_inputs(s):
    out = {"valuation_date": s["valuation_date"], "last_fy_end": s["last_fy_end"],
        "opening_nwc": s["opening_nwc"], "opening_ppe": s.get("opening_ppe", 0),
        "opening_rou": s.get("opening_rou", 0), "opening_retained_earnings": s.get("opening_retained_earnings", 0),
        "contributed_capital": s.get("contributed_capital", 0), "opening_deferred": s.get("opening_deferred", 0),
        "opening_debt": s.get("opening_debt", s["bridge"]["debt"]), "opening_sbc_reserve": s.get("opening_sbc_reserve", 0),
        "opening_cash": s.get("opening_cash", s["bridge"]["cash"])}
    for group in ("assumptions", "bridge"):
        for k, v in s[group].items(): out[group[0] + "." + k] = v
    out["b.driver"] = s["business"]["driver"]
    return out


def input_layout(s):
    result = {}
    r = 4
    for key, value in flatten_inputs(s).items():
        if isinstance(value, list):
            result[key] = {i: f"{L(3 + i)}{r}" for i in range(len(value))}
        else: result[key] = {"scalar": f"C{r}"}
        r += 1
    return result


def make_public(s, path):
    wb = Workbook(); ws = wb.active; ws.title = "Inputs"
    ws["A1"] = "原始事实与假设 / Original frozen facts and assumptions"
    ws["A2"] = "金额：百万元；股数：百万股；比率为小数。预测向量自 P1 起。除固定 Outputs 键外不提供公式或行布局。"
    for c, v in enumerate(("key", "说明", "scalar / P1", "P2", "P3", "P4", "P5", "P6"), 1): ws.cell(3, c, v)
    for key, value in flatten_inputs(s).items():
        mapping = input_layout(s)[key]
        r = int((mapping["scalar"] if "scalar" in mapping else mapping[0])[1:])
        ws.cell(r, 1, key)
        ws.cell(r, 2, "原始事实" if key.startswith("b.") else "公开假设或口径")
        if isinstance(value, list):
            for i, x in enumerate(value): ws.cell(r, 3 + i, x)
        else:
            if key.endswith("date") or key.endswith("fy_end"): value = dt.date.fromisoformat(value)
            ws.cell(r, 3, value)
            if isinstance(value, dt.date): ws.cell(r, 3).number_format = "yyyy-mm-dd"
    h = wb.create_sheet("History")
    headers = ("start", "end", "fiscal_year", "revenue", "ebit", "operating_cost_ex_sbc", "sbc", "nonrecurring_gain")
    for j, key in enumerate(headers, 1): h.cell(3, j, key)
    for i, row in enumerate(s["history"], 4):
        for j, key in enumerate(headers, 1):
            if key in row:
                value = dt.date.fromisoformat(row[key]) if key in ("start", "end") else row[key]
                h.cell(i, j, value)
                if isinstance(value, dt.date): h.cell(i, j).number_format = "yyyy-mm-dd"
    if s.get("event_type") == "rebase":
        event = wb.create_sheet("Event History")
        facts = s["event_public_facts"]
        event.append(["field", "value", "interpretation"])
        for key in ("actual_period", "actual_revenue", "actual_driver_close", "actual_unit_revenue", "driver_rebase", "price_rebase", "rule"):
            event.append([key, json.dumps(facts[key], ensure_ascii=False) if isinstance(facts[key], dict) else facts[key], "新增事件事实，不回写History"])
    o = wb.create_sheet("Outputs")
    o["A1"], o["B1"] = "key", "value"
    o["A2"] = "固定Outputs键：B列活公式；混合期间键在Results Detail。" if s["output"]["template"] != "free_layout" else "自由布局键清单：不是坐标模板。标签右邻或下邻公式。"
    for i, key in enumerate(compute(s), 3): o.cell(i, 1, key)
    if s["output"]["template"] == "free_layout": o.title = "Required Keys"
    for sheet in wb:
        sheet.column_dimensions["A"].width = 35
        sheet.column_dimensions["B"].width = 40
        sheet.freeze_panes = "C4"
    wb.save(path)


def make_reference(s, path):
    wb = Workbook(); wb.remove(wb.active)
    from openpyxl import load_workbook as loader
    public_path = Path(path).parent.parent / "environment" / "inputs.xlsx"
    public = loader(public_path)
    for sheet in public:
        if sheet.title in ("Inputs", "History", "Event History"):
            target = wb.create_sheet(sheet.title)
            for row in sheet:
                for cell in row:
                    target[cell.coordinate] = cell.value
                    target[cell.coordinate].number_format = cell.number_format
    layout = input_layout(s)
    def ref(key, i=None):
        c = layout[key]["scalar" if i is None else i]
        return f"Inputs!${c[0]}${c[1:]}"
    def a(key, i=None): return ref("a." + key, i)
    def b(key): return ref("b." + key)
    hist = wb.create_sheet("Historical")
    hist.append(["metric", "value"])
    rows = sorted(s["history"], key=lambda r: (r["end"], r["start"]))
    last = [r for r in rows if r["fiscal_year"] == s["last_fy_end"][:4] and r["end"] <= s["last_fy_end"]]
    count = 4 if s["time_axis"]["history_frequency"] == "quarterly" else 2
    recent = [r for r in rows if r["end"] <= s["valuation_date"]][-count:]
    index = {id(r): rows.index(r) + 4 for r in rows}
    for prefix, group in (("fy", last), ("ltm", recent)):
        refs = [f"History!D{index[id(r)]}" for r in group]
        hist.append([prefix + "_revenue", "=SUM(" + ",".join(refs) + ")"])
        if s["accounting"]["normalized_history"]:
            normal = [f"(History!D{index[id(r)]}-History!F{index[id(r)]}-History!G{index[id(r)]})" for r in group]
            reported = [f"(History!D{index[id(r)]}-History!F{index[id(r)]}-History!G{index[id(r)]}+History!H{index[id(r)]})" for r in group]
            hist.append([prefix + "_normalized_ebit", "=" + "+".join(normal)])
            hist.append([prefix + "_reported_ebit", "=" + "+".join(reported)])
        else:
            normal = [f"History!E{index[id(r)]}" for r in group]
            hist.append([prefix + "_normalized_ebit", "=" + "+".join(normal)])
            hist.append([prefix + "_reported_ebit", "=" + "+".join(normal)])
    hrow = {hist.cell(r, 1).value: f"Historical!$B${r}" for r in range(2, hist.max_row + 1)}
    def model_sheet(name, scenario=None):
        m = wb.create_sheet(name); row = {}; n = s["horizon"]
        m.cell(1, 1, "项目")
        for i in range(n): m.cell(1, 2 + i, f"P{i + 1}")
        def line(key, label, fn):
            row[key] = row.get(key, m.max_row + 1)
            for i in range(n): m.cell(row[key], 2 + i, "=" + fn(i, L(2 + i), L(1 + i)))
            m.cell(row[key], 1, label)
            if key in ("end", "start"):
                for i in range(n): m.cell(row[key], 2 + i).number_format = "yyyy-mm-dd"
        def R(key, i): return f"{L(2 + i)}{row[key]}"
        def P(key, i): return f"{L(1 + i)}{row[key]}"
        line("end", "期末", lambda i, c, p: f"EDATE({ref('last_fy_end')},{12 * (i + 1)})")
        line("start", "期间开始", lambda i, c, p: ref("valuation_date") if i == 0 else f"{P('end', i)}+1")
        line("days", "期间天数", lambda i, c, p: f"{R('end', i)}-{ref('last_fy_end') if i == 0 else P('end', i)}")
        line("activity", "剩余活动比例", lambda i, c, p: f"({R('end', i)}-{ref('valuation_date')})/{R('days', i)}" if i == 0 else "1")
        kind = s["business"]["driver"]; ass = s["assumptions"]
        case = a("scenario") if scenario is None else str(scenario)
        gd = f"CHOOSE({case},0,{a('upside_demand_delta')},{a('downside_demand_delta')})" if "scenario" in s["enabled_modules"] else "0"
        md = f"CHOOSE({case},0,{a('upside_margin_delta')},{a('downside_margin_delta')})" if "scenario" in s["enabled_modules"] else "0"
        if kind != "volume_price":
            line("driver_open", "经营基数期初", lambda i, c, p: (a("driver_rebase") if "driver_rebase" in ass else a("driver0")) if i == 0 else f"{p}{row['driver_open']+3}")
            line("attrition", "流失", lambda i, c, p: f"{R('driver_open', i)}*{a('attrition_rate', i)}")
            line("driver_add", "新增", lambda i, c, p: f"{a('driver_add', i)}*(1+{gd})" if kind == "capacity" or "scenario" in s["enabled_modules"] else a("driver_add", i))
            line("driver_close", "经营基数期末", lambda i, c, p: f"{R('driver_open', i)}-{R('attrition', i)}+{R('driver_add', i)}")
            line("average_driver", "平均经营基数", lambda i, c, p: f"({R('driver_open', i)}+{R('driver_close', i)})/2")
            units = "average_driver"
            if kind == "installed_base":
                line("service_activity", "服务次数", lambda i, c, p: f"{R('average_driver', i)}*{a('service_frequency', i)}")
                units = "service_activity"
            elif kind == "capacity":
                line("utilization", "产能利用率", lambda i, c, p: a("utilization", i))
                line("activity_units", "有效产量", lambda i, c, p: f"{R('average_driver', i)}*{R('utilization', i)}")
                units = "activity_units"
        else:
            row["average_driver"] = m.max_row + 2
            line("driver_close", "销量", lambda i, c, p: f"{a('driver0') if i == 0 else P('driver_close', i)}*(1+{a('driver_growth', i)}+{gd})")
            units = "driver_close"
            line("average_driver", "销量（输出）", lambda i, c, p: R("driver_close", i))
        line("unit_price", "单位收入", lambda i, c, p: f"{a('price_rebase') if 'price_rebase' in ass and i == 0 else a('price0') if i == 0 else P('unit_price', i)}*(1+{a('price_growth', i)})")
        line("full_revenue", "完整年度核心收入", lambda i, c, p: f"{R(units, i)}*{R('unit_price', i)}")
        line("segment_revenue", "分部收入", lambda i, c, p: f"{a('segment_revenue', i)}*{R('activity', i)}" if "segment_revenue" in ass else "0")
        line("revenue", "本期收入", lambda i, c, p: f"({R('full_revenue', i)}+{a('segment_revenue', i) if 'segment_revenue' in ass else '0'})*{R('activity', i)}")
        line("ebit", "EBIT", lambda i, c, p: f"{R('full_revenue', i)}*{R('activity', i)}*({a('ebit_margin', i)}+{md})+{R('segment_revenue', i)}*({a('segment_margin', i) if 'segment_margin' in ass else '0'})")
        line("capex", "资本开支", lambda i, c, p: f"{R('revenue', i)}*{a('capex_pct', i)}" + (f"+{a('extra_capex', i)}*{R('activity', i)}" if "extra_capex" in ass else ""))
        row["ppe_close"] = m.max_row + 2
        line("ppe_depreciation", "固定资产折旧", lambda i, c, p: f"({ref('opening_ppe') if i == 0 else P('ppe_close', i)}+{R('capex', i)}*0.5)*{a('ppe_rate')}*{R('days', i)}/365")
        line("ppe_close", "固定资产期末", lambda i, c, p: f"{ref('opening_ppe') if i == 0 else P('ppe_close', i)}+{R('capex', i)}-{R('ppe_depreciation', i)}")
        row["rou_close"] = m.max_row + 3
        line("rou_additions", "新增使用权资产", lambda i, c, p: f"{a('lease_additions', i)}*{R('activity', i)}" if "leases" in s["enabled_modules"] else "0")
        line("rou_amortization", "使用权资产摊销", lambda i, c, p: f"({ref('opening_rou') if i == 0 else P('rou_close', i)}+{R('rou_additions', i)}*0.5)*{a('rou_rate')}*{R('days', i)}/365" if "leases" in s["enabled_modules"] else "0")
        line("rou_close", "使用权资产期末", lambda i, c, p: f"{ref('opening_rou') if i == 0 else P('rou_close', i)}+{R('rou_additions', i)}-{R('rou_amortization', i)}")
        line("lease_liability_close", "租赁负债期末", lambda i, c, p: f"{b('lease_liability')}+{R('rou_additions', i)}" if i == 0 else f"{P('lease_liability_close', i)}+{R('rou_additions', i)}")
        if "rolling_assets" in s["enabled_modules"] or "leases" in s["enabled_modules"]:
            line("da", "折旧摊销", lambda i, c, p: f"{R('ppe_depreciation', i)}+{R('rou_amortization', i)}")
        else: line("da", "折旧摊销", lambda i, c, p: f"{R('revenue', i)}*{a('da_pct', i)}")
        line("deferred_close", "合同负债期末", lambda i, c, p: f"{R('full_revenue', i)}*{a('deferred_pct', i)}" if "deferred_revenue" in s["enabled_modules"] else "0")
        line("cash_collections", "现金收款", lambda i, c, p: f"{R('revenue', i)}+{R('deferred_close', i)}-{ref('opening_deferred') if i == 0 else P('deferred_close', i)}")
        if "nwc_days" in s["enabled_modules"]:
            line("nwc", "NWC 期末", lambda i, c, p: f"{R('full_revenue', i)}*{a('dso', i)}/365+{R('full_revenue', i)}*{a('cogs_ratio', i)}*({a('dio', i)}-{a('dpo', i)})/365-{R('deferred_close', i)}")
        else: line("nwc", "NWC 期末", lambda i, c, p: f"{R('full_revenue', i)}*{a('nwc_pct', i)}-{R('deferred_close', i)}")
        line("delta_nwc", "NWC 增量", lambda i, c, p: f"{R('nwc', i)}-{ref('opening_nwc') if i == 0 else P('nwc', i)}")
        row["nol_close"] = m.max_row + 2
        line("nol_used", "NOL 使用", lambda i, c, p: f"MIN({ref('a.nol0') if i == 0 else P('nol_close', i)},MAX({R('ebit', i)},0))")
        line("nol_close", "NOL 期末", lambda i, c, p: f"{ref('a.nol0') if i == 0 else P('nol_close', i)}-{R('nol_used', i)}+MAX(-{R('ebit', i)},0)")
        line("tax", "无杠杆现金税", lambda i, c, p: f"(MAX({R('ebit', i)},0)-{R('nol_used', i)})*{a('tax')}")
        line("fcff", "FCFF", lambda i, c, p: f"{R('ebit', i)}-{R('tax', i)}+{R('da', i)}-{R('capex', i)}-{R('delta_nwc', i)}")
        line("borrowing", "新增借款", lambda i, c, p: f"{a('new_borrowing', i)}*{R('activity', i)}")
        line("repayment", "偿还借款", lambda i, c, p: f"{a('debt_repayment', i)}*{R('activity', i)}")
        row["debt_close"] = m.max_row + 2
        line("interest", "利息", lambda i, c, p: f"({ref('opening_debt') if i == 0 else P('debt_close', i)}+{R('borrowing', i)}*0.5)*{a('interest_rate')}*{R('days', i)}/365")
        line("debt_close", "债务期末", lambda i, c, p: f"{ref('opening_debt') if i == 0 else P('debt_close', i)}-{R('repayment', i)}+{R('borrowing', i)}")
        line("interest_tax_shield", "利息税盾", lambda i, c, p: f"{R('interest', i)}*{a('tax')}")
        line("levered_tax", "利息后现金税", lambda i, c, p: f"{R('tax', i)}-{R('interest_tax_shield', i)}")
        line("cash_taxes", "现金税款", lambda i, c, p: R("levered_tax", i))
        line("tax_accrual", "税项应计调整", lambda i, c, p: "0")
        line("deferred_tax_asset", "未确认递延税资产诊断", lambda i, c, p: "0")
        line("net_income", "净利润", lambda i, c, p: f"{R('ebit', i)}-{R('interest', i)}-{R('levered_tax', i)}")
        line("sbc", "非现金股份支付", lambda i, c, p: f"{R('revenue', i)}*{a('sbc_pct', i)}")
        row["sbc_reserve"] = m.max_row + 2
        line("retained_earnings", "留存收益", lambda i, c, p: f"{ref('opening_retained_earnings') if i == 0 else P('retained_earnings', i)}+{R('net_income', i)}")
        line("sbc_reserve", "股份支付权益储备", lambda i, c, p: f"{ref('opening_sbc_reserve')}+{R('sbc', i)}" if i == 0 else f"{P('sbc_reserve', i)}+{R('sbc', i)}")
        line("accrual_adjustments", "应计到现金调整", lambda i, c, p: f"{R('da', i)}+{R('sbc', i)}-{R('delta_nwc', i)}")
        line("cfo", "经营现金流", lambda i, c, p: f"{R('net_income', i)}+{R('accrual_adjustments', i)}")
        line("cash_close", "现金期末", lambda i, c, p: f"{ref('opening_cash')}+{R('cfo', i)}-{R('capex', i)}+{R('borrowing', i)}-{R('repayment', i)}" if i == 0 else f"{P('cash_close', i)}+{R('cfo', i)}-{R('capex', i)}+{R('borrowing', i)}-{R('repayment', i)}")
        line("operating_current_assets", "经营流动资产", lambda i, c, p: f"{R('nwc', i)}+{R('deferred_close', i)}")
        line("assets", "资产合计", lambda i, c, p: f"{R('cash_close', i)}+{R('operating_current_assets', i)}+{R('ppe_close', i)}+{R('rou_close', i)}+{b('investments')}+{R('deferred_tax_asset', i)}")
        line("cash_link", "现金衔接差额", lambda i, c, p: f"{R('cash_close', i)}-({ref('opening_cash') if i == 0 else P('cash_close', i)}+{R('cfo', i)}-{R('capex', i)}+{R('borrowing', i)}-{R('repayment', i)})")
        line("liabilities_equity", "负债及权益合计", lambda i, c, p: f"{R('debt_close', i)}+{R('lease_liability_close', i)}+{R('deferred_close', i)}+{R('retained_earnings', i)}+{ref('contributed_capital')}+{b('minority')}+{R('sbc_reserve', i)}")
        line("balance_difference", "配平差额", lambda i, c, p: f"{R('assets', i)}-{R('liabilities_equity', i)}")
        line("end_time", "期末距估值日年数", lambda i, c, p: f"({R('end', i)}-{ref('valuation_date')})/365")
        line("discount_time", "折现年数", lambda i, c, p: f"{R('end_time', i)}-" + (f"({R('end', i)}-{ref('valuation_date') if i == 0 else P('end', i)})/730" if s["time_axis"]["midyear"] else "0"))
        line("discount_factor", "折现因子", lambda i, c, p: f"(1+Valuation!$B$2)^-{R('discount_time', i)}")
        line("pv_fcff", "FCFF 现值", lambda i, c, p: f"{R('fcff', i)}*{R('discount_factor', i)}")
        m.column_dimensions["A"].width = 32
        return row
    model_rows = {"base": model_sheet("Model")}
    if "scenario" in s["enabled_modules"]:
        model_rows["upside"] = model_sheet("Upside", 2); model_rows["downside"] = model_sheet("Downside", 3)
    v = wb.create_sheet("Valuation", 1); v["A1"], v["B1"] = "估值项目", "数值"
    vr = {"wacc": 2}
    if "scenario" in s["enabled_modules"]:
        for key in ("base_scenario_vps", "upside_scenario_vps", "downside_scenario_vps"):
            vr[key] = max(vr.values()) + 1
    scalar_order = ["levered_beta", "cost_of_equity", "debt_weight", "pv_explicit", "tv_gordon", "tv_exit", "terminal_value", "pv_terminal", "enterprise_value", "equity_value", "option_dilution", "diluted_shares", "value_per_share"]
    for number, key in enumerate(scalar_order, max(vr.values()) + 1): vr[key] = number
    def scalar(key, formula):
        v.cell(vr[key], 1, key); v.cell(vr[key], 2, "=" + formula); return f"Valuation!$B${vr[key]}"
    def S(key): return f"Valuation!$B${vr[key]}"
    a_ = s["assumptions"]
    if "capm" in s["enabled_modules"]:
        scalar("levered_beta", f"{a('beta_unlevered')}*(1+(1-{a('tax')})*{a('target_de')})")
        scalar("cost_of_equity", f"{a('risk_free')}+{S('levered_beta')}*{a('erp')}+{a('specific_premium')}")
        scalar("debt_weight", f"{a('target_de')}/(1+{a('target_de')})")
        wacc_formula = f"(1-{S('debt_weight')})*{S('cost_of_equity')}+{S('debt_weight')}*{a('cost_of_debt')}*(1-{a('tax')})"
        v["A2"] = "wacc"; v["B2"] = "=" + wacc_formula
    else:
        scalar("levered_beta", "0")
        scalar("cost_of_equity", "0")
        scalar("debt_weight", "0")
        v["A2"] = "wacc"; v["B2"] = "=" + a("wacc")
    def mr(key, i): return f"Model!{L(2 + i)}{model_rows['base'][key]}"
    scalar("pv_explicit", f"SUM(Model!B{model_rows['base']['pv_fcff']}:{L(1 + s['horizon'])}{model_rows['base']['pv_fcff']})")
    last = s["horizon"] - 1
    wg = a("gordon_weight")
    scalar("tv_gordon", f"{mr('fcff', last)}*(1+{a('g')})/({S('wacc')}-{a('g')})" if s["assumptions"].get("gordon_weight", 1) > 0 else "0")
    scalar("tv_exit", f"({mr('ebit', last)}+{mr('da', last)})*{a('exit_multiple')}" if s["assumptions"].get("gordon_weight", 1) < 1 else "0")
    scalar("terminal_value", f"{wg}*{S('tv_gordon')}+(1-{wg})*{S('tv_exit')}")
    scalar("pv_terminal", f"{S('terminal_value')}*(1+{S('wacc')})^-{mr('end_time', last)}")
    scalar("enterprise_value", f"{S('pv_explicit')}+{S('pv_terminal')}")
    br = s["bridge"]
    scalar("equity_value", f"{S('enterprise_value')}+{b('cash')}+{b('valuation_cash_adjustment')}+{b('investments')}-{b('debt')}-{b('lease_liability')}-{b('minority')}")
    scalar("option_dilution", f"IF({b('share_price')}>{b('strike')},{b('options')}*(1-{b('strike')}/{b('share_price')}),0)")
    scalar("diluted_shares", f"{b('shares')}+{b('rsus')}+{S('option_dilution')}")
    scalar("value_per_share", f"{S('equity_value')}/{S('diluted_shares')}")
    if "scenario" in s["enabled_modules"]:
        for name, case in (("base", "Model"), ("upside", "Upside"), ("downside", "Downside")):
            rr = model_rows[name]
            f = "+".join(f"{case}!{L(2+i)}{rr['fcff']}*(1+{S('wacc')})^-{case}!{L(2+i)}{rr['discount_time']}" for i in range(s["horizon"]))
            f += f"+({wg}*{case}!{L(2+last)}{rr['fcff']}*(1+{a('g')})/({S('wacc')}-{a('g')})+(1-{wg})*({case}!{L(2+last)}{rr['ebit']}+{case}!{L(2+last)}{rr['da']})*{a('exit_multiple')})*(1+{S('wacc')})^-{case}!{L(2+last)}{rr['end_time']}"
            f += f"+{b('cash')}+{b('valuation_cash_adjustment')}+{b('investments')}-{b('debt')}-{b('lease_liability')}-{b('minority')}"
            scalar(name + "_scenario_vps", f"({f})/{S('diluted_shares')}")
    if "valuation_sensitivity" in s["enabled_modules"]:
        for i in range(len(a_["wacc_deltas"])):
            for j in range(len(a_["g_deltas"])):
                vr[f"sens_r{i+1}c{j+1}"] = max(vr.values()) + 1
        rr = model_rows["base"]
        for i, dw in enumerate(a_["wacc_deltas"]):
            for j, dg in enumerate(a_["g_deltas"]):
                w = f"({S('wacc')}+{a('wacc_deltas', i)})"; g = f"({a('g')}+{a('g_deltas', j)})"
                f = "+".join(f"Model!{L(2+i)}{rr['fcff']}*(1+{w})^-Model!{L(2+i)}{rr['discount_time']}" for i in range(s["horizon"]))
                f += f"+({wg}*{mr('fcff', last)}*(1+{g})/({w}-{g})+(1-{wg})*({mr('ebit', last)}+{mr('da', last)})*{a('exit_multiple')})*(1+{w})^-{mr('end_time', last)}"
                f += f"+{b('cash')}+{b('valuation_cash_adjustment')}+{b('investments')}-{b('debt')}-{b('lease_liability')}-{b('minority')}"
                scalar(f"sens_r{i+1}c{j+1}", f"({f})/{S('diluted_shares')}")
    mode = s["output"]["template"]
    fixed = wb.create_sheet("Outputs") if mode != "free_layout" else None
    detail = wb.create_sheet("Results") if mode == "free_layout" else wb.create_sheet("Results Detail") if mode == "mixed" else None
    o = fixed or detail
    o["A1"], o["B1"] = "key", "value"
    for i, key in enumerate(compute(s), 2):
        if key in hrow: formula = "=" + hrow[key]
        elif key in vr: formula = "=" + S(key)
        elif "_p" in key:
            base, p = key.rsplit("_p", 1)
            formula = f"=Model!{L(1+int(p))}{model_rows['base'][base]}"
        else: raise KeyError(key)
        if mode == "fixed_outputs" or (mode == "mixed" and "_p" not in key and not key.startswith("sens_") and "scenario_vps" not in key):
            o.cell(i, 1, key); o.cell(i, 2, formula)
        else:
            o = detail
            label_row = 2 + (i - 2) // 3 * 3
            label_col = 1 + (i - 2) % 3 * 3
            o.cell(label_row, label_col, key); o.cell(label_row, label_col + 1, formula)
    for sheet in wb:
        sheet.freeze_panes = "B2"
        sheet.column_dimensions["A"].width = 34
        sheet.column_dimensions["B"].width = 19
        sheet.sheet_view.showGridLines = False
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.calculation.calcMode = "auto"
    wb.save(path)


def output_locations(wb, template, allowed, formulas=False):
    allowed = set(allowed)
    result = {}; evidence = {}; fixed = set(); duplicates = set()
    def accept(key, cell):
        if key not in allowed: return
        if key in result:
            duplicates.add(key)
            return
        value = cell.value
        good = isinstance(value, str) and value.startswith("=") if formulas else isinstance(value, (int, float)) and not isinstance(value, bool)
        if good:
            result[key] = value if formulas else float(value)
            evidence[key] = f"{cell.parent.title}!{cell.coordinate}"
    if template in ("fixed_outputs", "mixed"):
        if "Outputs" not in wb.sheetnames: return result, evidence, {"fixed": sorted(fixed), "duplicates": sorted(duplicates)}
        for row in wb["Outputs"].iter_rows():
            if isinstance(row[0].value, str) and len(row) > 1:
                key = row[0].value.strip()
                before = len(result)
                accept(key, row[1])
                if len(result) > before: fixed.add(key)
        if template == "fixed_outputs": return result, evidence, {"fixed": sorted(fixed), "duplicates": sorted(duplicates)}
    for ws in wb.worksheets:
        if not ws.title.startswith("Results"): continue
        for row in ws.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str): continue
                key = cell.value.strip()
                if key not in allowed or (template == "mixed" and "_p" not in key and not key.startswith("sens_") and "scenario_vps" not in key): continue
                right = ws.cell(cell.row, cell.column + 1)
                if right.value is None: accept(key, ws.cell(cell.row + 1, cell.column))
                else: accept(key, right)
    return result, evidence, {"fixed": sorted(fixed), "duplicates": sorted(duplicates)}


def discover_values(wb, template, allowed=None):
    return output_locations(wb, template, allowed or [], False)


def discover_formulas(wb, template, allowed=None):
    return output_locations(wb, template, allowed or [], True)
