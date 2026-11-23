"""Public input workbooks and formula-only references; formulas never use expected.json."""
import copy
import datetime as dt
import json
import sys
from pathlib import Path
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter as L
from model import compute, apply_changes, wacc

ROOT = Path(__file__).resolve().parent
import v2_model
import v3_model_alias
sys.modules["model"] = v2_model
import v2_workbook as v2wb
sys.modules["model"] = v3_model_alias


def flatten(s):
    out = {"valuation_date": s["valuation_date"], "last_fy_end": s["last_fy_end"]}
    for key, value in s.items():
        if (key.startswith("opening_") or key == "contributed_capital") and isinstance(value, (int, float)):
            out[key] = value
    for prefix, group in (("a", "assumptions"), ("b", "bridge"), ("m", "market"), ("seg", "segments"), ("proj", "projects")):
        for key, value in s.get(group, {}).items():
            if isinstance(value, dict):
                for sub, item in value.items():
                    if sub == "project_fcff": continue
                    out[f"{prefix}.{key}.{sub}"] = item
            else:
                out[f"{prefix}.{key}"] = value
    out["b.driver"] = s.get("business", {}).get("driver", "industry")
    return out


def public_view(s):
    keep = ("schema_version", "task_id", "family", "step", "company", "b_items", "c_structure", "base_structure",
            "industry", "industry_drivers", "valuation_date", "last_fy_end", "horizon", "history", "time_axis",
            "accounting", "business", "opening_nwc", "opening_ppe", "opening_intangible", "opening_debt", "opening_cash",
            "assumptions", "bridge", "segments", "projects", "market", "events", "nwc_opening_basis",
            "residual_activity", "enabled_modules")
    out = {key: copy.deepcopy(s[key]) for key in keep if key in s}
    out["public_output_keys"] = list(compute(s))
    out["units"] = {"money": "百万元", "shares": "百万股", "rates": "小数"}
    return out


def make_public(s, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Inputs"
    ws["A1"] = "公开冻结事实、假设与输出键（无答案公式）"
    ws["A2"] = "金额百万元、股数百万股、比率小数。P1 起向量横向位于 C/D/E…；必须保留本页语义键。"
    for col, value in enumerate(("key", "说明", "scalar / P1", "P2", "P3", "P4", "P5", "P6"), 1):
        ws.cell(3, col, value)
    row = 4
    for key, value in flatten(s).items():
        ws.cell(row, 1, key)
        ws.cell(row, 2, "公开事实或假设")
        if isinstance(value, list):
            for i, item in enumerate(value): ws.cell(row, 3 + i, item)
        else:
            if key in ("valuation_date", "last_fy_end"):
                value = dt.date.fromisoformat(value)
                ws.cell(row, 3).number_format = "yyyy-mm-dd"
            ws.cell(row, 3, value)
        row += 1
    history = wb.create_sheet("History")
    headers = ("start", "end", "fiscal_year", "revenue", "ebit", "operating_cost_ex_sbc", "sbc", "nonrecurring_gain", "period_type")
    for col, key in enumerate(headers, 1): history.cell(3, col, key)
    for i, item in enumerate(s.get("history", []), 4):
        for j, key in enumerate(headers, 1):
            value = item.get(key)
            if key in ("start", "end") and value: value = dt.date.fromisoformat(value)
            history.cell(i, j, value)
            if isinstance(value, dt.date): history.cell(i, j).number_format = "yyyy-mm-dd"
    output = wb.create_sheet("Required Keys")
    output.append(("key", "definition"))
    for key in compute(s): output.append((key, "在 Results 页以同名标签加右邻活公式提交；不是坐标模板。"))
    for sheet in wb:
        sheet.freeze_panes = "C4"
        sheet.column_dimensions["A"].width = 43
        sheet.column_dimensions["B"].width = 49
        sheet.sheet_view.showGridLines = False
    wb.save(path)


class FormulaBook:
    def __init__(self, s, wb):
        self.s, self.wb = s, wb
        self.inputs = flatten(s)
        self.locations = {}
        for row in wb["Inputs"].iter_rows(min_row=4):
            if row[0].value: self.locations[row[0].value] = row[0].row
        self.model = wb.create_sheet("Model")
        self.model.append(("key", "scalar / P1", "P2", "P3", "P4", "P5", "P6"))
        self.refs = {}
        self.expected = compute(s)
        self.scalar_keys = set()
        self.period_keys = set()

    def I(self, key, i=None):
        row = self.locations[key]
        col = 3 if i is None else 3 + i
        return f"Inputs!${L(col)}${row}"

    def R(self, key, i=None):
        for prefix in ("gordon_", "exit_", "existing_"):
            if key.startswith(prefix) and key not in self.refs and key[len(prefix):] in self.refs:
                key = key[len(prefix):]
                break
        if key not in self.refs: raise KeyError(f"unbuilt formula {key}")
        if key in self.scalar_keys: return f"Model!$B${self.refs[key]}"
        if i is None: raise TypeError(f"period required for {key}")
        return f"Model!${L(2 + i)}${self.refs[key]}"

    def scalar(self, key, formula):
        self.model.append((key, "=" + formula.lstrip("=")))
        self.refs[key] = self.model.max_row
        self.scalar_keys.add(key)
        return self.R(key)

    def series(self, key, fn):
        row = self.model.max_row + 1
        self.model.cell(row, 1, key)
        self.refs[key] = row
        self.period_keys.add(key)
        for i in range(self.s["horizon"]):
            self.model.cell(row, 2 + i, "=" + fn(i).lstrip("="))
        return key

    def alias(self, key, source):
        return self.scalar(key, self.R(source))

    def history_formulas(self):
        if not self.s.get("history"): return
        s = self.s
        rows = sorted(s["history"], key=lambda x: (x["end"], x["start"]))
        sheet_rows = {id(r): s["history"].index(r) + 4 for r in rows}
        fy = [r for r in rows if r["fiscal_year"] == s["last_fy_end"][:4] and r["end"] <= s["last_fy_end"]]
        if s["time_axis"]["history_frequency"] == "mixed_h1_q":
            h1 = [r for r in rows if r["end"] == s["last_fy_end"]][-1:]
            q = [r for r in rows if s["last_fy_end"] < r["end"] <= s["valuation_date"]]
            ltm = h1 + q
            self.scalar("ltm_h1_revenue", "+".join(f"History!D{sheet_rows[id(r)]}" for r in h1))
            self.scalar("ltm_bridge_quarter_revenue", "+".join(f"History!D{sheet_rows[id(r)]}" for r in q))
        else:
            count = 4 if s["time_axis"]["history_frequency"] == "quarterly" else 2
            ltm = [r for r in rows if r["end"] <= s["valuation_date"]][-count:]
        for prefix, group in (("fy", fy), ("ltm", ltm)):
            for kind in ("revenue", "normalized_ebit", "reported_ebit"):
                terms = []
                for r in group:
                    rr = sheet_rows[id(r)]
                    if kind == "revenue": terms.append(f"History!D{rr}")
                    else:
                        base = f"(History!D{rr}-History!F{rr}-History!G{rr})"
                        terms.append(base + (f"+History!H{rr}" if kind == "reported_ebit" else ""))
                self.scalar(f"{prefix}_{kind}", "+".join(terms))

    def basic(self, prefix="", scenario=None):
        s, a = self.s, self.s["assumptions"]
        def rr(key, i): return self.R(prefix + key, i)
        def ss(key): return self.R(prefix + key)
        endrow = prefix + "internal_end"
        self.series(endrow, lambda i: f"EDATE({self.I('last_fy_end')},{12 * (i + 1)})")
        for i in range(s["horizon"]): self.model.cell(self.refs[endrow], 2 + i).number_format = "yyyy-mm-dd"
        self.series(prefix + "internal_days", lambda i: f"{rr('internal_end', i)}-{self.I('last_fy_end') if i == 0 else rr('internal_end', i - 1)}")
        self.series(prefix + "activity", lambda i: f"({rr('internal_end', i)}-{self.I('valuation_date')})/{rr('internal_days', i)}" if i == 0 else "1")
        gd = md = rd = "0"
        if scenario:
            gd = f"CHOOSE({scenario},0,{self.I('a.upside_demand_delta')},{self.I('a.downside_demand_delta')})"
            md = f"CHOOSE({scenario},0,{self.I('a.upside_margin_delta')},{self.I('a.downside_margin_delta')})"
            rd = f"CHOOSE({scenario},0,{self.I('a.upside_reinvestment_delta')},{self.I('a.downside_reinvestment_delta')})"
        kind = s["business"]["driver"]
        if kind != "volume_price":
            self.refs[prefix + "driver_close"] = self.model.max_row + 2
            self.series(prefix + "driver_open", lambda i: self.I("a.driver_rebase") if "driver_rebase" in a and i == 0 else self.I("a.driver0") if i == 0 else rr("driver_close", i - 1))
            self.series(prefix + "driver_close", lambda i: f"{rr('driver_open', i)}*(1-{self.I('a.attrition_rate', i)})+{self.I('a.driver_add', i)}" + (f"*(1+{gd})" if scenario else ""))
            self.series(prefix + "average_driver", lambda i: f"({rr('driver_open', i)}+{rr('driver_close', i)})/2")
        else:
            self.series(prefix + "driver_close", lambda i: f"{self.I('a.driver0') if i == 0 else rr('driver_close', i - 1)}*(1+{self.I('a.driver_growth', i)}+{gd})")
            self.series(prefix + "average_driver", lambda i: rr("driver_close", i))
        self.series(prefix + "unit_price", lambda i: f"{self.I('a.price_rebase') if 'price_rebase' in a and i == 0 else self.I('a.price0') if i == 0 else rr('unit_price', i - 1)}*(1+{self.I('a.price_growth', i)})")
        units = rr("average_driver", 0)
        if kind == "capacity": units = f"{{units}}*{self.I('a.utilization', 0)}"
        if kind == "installed_base": units = f"{{units}}*{self.I('a.service_frequency', 0)}"
        self.series(prefix + "full_revenue", lambda i: f"{rr('average_driver', i)}" + (f"*{self.I('a.utilization', i)}" if kind == "capacity" else f"*{self.I('a.service_frequency', i)}" if kind == "installed_base" else "") + f"*{rr('unit_price', i)}")
        self.series(prefix + "revenue", lambda i: f"{rr('full_revenue', i)}*{rr('activity', i)}")
        self.series(prefix + "ebit", lambda i: f"{rr('revenue', i)}*({self.I('a.ebit_margin', i)}+{md})")
        capex = lambda i: f"({rr('revenue', i)}*{self.I('a.capex_pct', i)}" + (f"+{self.I('a.extra_capex', i)}*{rr('activity', i)}" if "extra_capex" in a else "") + f")*(1+{rd})"
        self.series(prefix + "capex", capex)
        if "rolling_assets" in s["enabled_modules"] or "intangible_pool" in s["enabled_modules"] or "leases" in s["enabled_modules"]:
            self.series(prefix + "ppe_close", lambda i: "0")
            self.series(prefix + "ppe_depreciation", lambda i: f"({self.I('opening_ppe') if i == 0 else rr('ppe_close', i - 1)}+{rr('capex', i)}*.5)*{self.I('a.ppe_rate')}*{rr('internal_days', i)}/365")
            for i in range(s["horizon"]):
                self.model.cell(self.refs[prefix + "ppe_close"], 2 + i, f"={self.I('opening_ppe') if i == 0 else rr('ppe_close', i - 1)}+{rr('capex', i)}-{rr('ppe_depreciation', i)}")
            self.series(prefix + "da", lambda i: rr("ppe_depreciation", i))
        else:
            self.series(prefix + "da", lambda i: f"{rr('revenue', i)}*{self.I('a.da_pct', i)}")
        if "intangible_pool" in s["enabled_modules"]:
            self.series(prefix + "intangible_close", lambda i: "0")
            self.series(prefix + "intangible_additions", lambda i: f"{self.I('a.intangible_additions', i)}*{rr('activity', i)}")
            self.series(prefix + "intangible_amortization", lambda i: f"({self.I('opening_intangible') if i == 0 else rr('intangible_close', i - 1)}+{rr('intangible_additions', i)}*.5)*{self.I('a.intangible_rate')}*{rr('internal_days', i)}/365")
            for i in range(s["horizon"]):
                self.model.cell(self.refs[prefix + "intangible_close"], 2 + i, f"={self.I('opening_intangible') if i == 0 else rr('intangible_close', i - 1)}+{rr('intangible_additions', i)}-{rr('intangible_amortization', i)}")
            for i in range(s["horizon"]):
                self.model.cell(self.refs[prefix + "da"], 2 + i, f"={rr('ppe_depreciation', i)}+{rr('intangible_amortization', i)}")
        deferred = "deferred_revenue" in s["enabled_modules"]
        self.series(prefix + "deferred_close", lambda i: f"{rr('full_revenue', i)}*{self.I('a.deferred_pct', i)}" if deferred else "0")
        self.series(prefix + "cash_collections", lambda i: f"{rr('revenue', i)}+{rr('deferred_close', i)}-{self.I('opening_deferred') if i == 0 else rr('deferred_close', i - 1)}")
        if "nwc_days" in s["enabled_modules"]:
            self.series(prefix + "nwc", lambda i: f"{rr('full_revenue', i)}*{self.I('a.dso', i)}/365+{rr('full_revenue', i)}*{self.I('a.cogs_ratio', i)}*({self.I('a.dio', i)}-{self.I('a.dpo', i)})/365-{rr('deferred_close', i)}")
        else:
            self.series(prefix + "nwc", lambda i: f"{rr('full_revenue', i)}*{self.I('a.nwc_pct', i)}-{rr('deferred_close', i)}")
        opening_nwc = "opening_nwc"
        self.series(prefix + "delta_nwc", lambda i: f"{rr('nwc', i)}-{self.I(opening_nwc) if i == 0 else rr('nwc', i - 1)}")
        self.refs[prefix + "nol_close"] = self.model.max_row + 2
        self.series(prefix + "nol_used", lambda i: f"MIN({self.I('a.nol0') if i == 0 else rr('nol_close', i - 1)},MAX({rr('ebit', i)},0))")
        self.series(prefix + "nol_close", lambda i: f"{self.I('a.nol0') if i == 0 else rr('nol_close', i - 1)}-{rr('nol_used', i)}+MAX(-{rr('ebit', i)},0)")
        self.series(prefix + "tax", lambda i: f"(MAX({rr('ebit', i)},0)-{rr('nol_used', i)})*{self.I('a.tax')}")
        self.series(prefix + "fcff", lambda i: f"{rr('ebit', i)}-{rr('tax', i)}+{rr('da', i)}-{rr('capex', i)}-{rr('delta_nwc', i)}" + (f"-{rr('intangible_additions', i)}" if "intangible_pool" in s["enabled_modules"] else ""))
        self.series(prefix + "end_time", lambda i: f"({rr('internal_end', i)}-{self.I('valuation_date')})/365")
        self.series(prefix + "discount_time", lambda i: f"{rr('end_time', i)}-" + (f"({rr('internal_end', i)}-{self.I('valuation_date') if i == 0 else rr('internal_end', i - 1)})/730" if s["time_axis"]["midyear"] else "0"))

    def beta(self):
        self.scalar("internal_levered_beta", f"{self.I('a.beta_unlevered')}*(1+(1-{self.I('a.tax')})*{self.I('a.target_de')})")
        self.scalar("internal_cost_equity", f"{self.I('a.risk_free')}+{self.R('internal_levered_beta')}*{self.I('a.erp')}+{self.I('a.specific_premium')}")
        return f"(1-{self.I('a.target_de')}/(1+{self.I('a.target_de')}))*{self.R('internal_cost_equity')}+{self.I('a.target_de')}/(1+{self.I('a.target_de')})*{self.I('a.cost_of_debt')}*(1-{self.I('a.tax')})"

    def wacc_expr(self):
        return self.beta() if "capm" in self.s["enabled_modules"] else self.I("a.wacc")

    def pv(self, prefix="", rate=None, g=None, multiple=None, method="gordon"):
        rate = rate or self.wacc_expr()
        g = g or self.I("a.g")
        multiple = multiple or self.I("a.exit_multiple")
        n, last = self.s["horizon"], self.s["horizon"] - 1
        pv = "+".join(f"{self.R(prefix + 'fcff', i)}*(1+({rate}))^-{self.R(prefix + 'discount_time', i)}" for i in range(n))
        wg = self.s["assumptions"].get("gordon_weight", 1.0) if method == "weighted" else 1.0 if method == "gordon" else 0.0
        tv_g = f"{self.R(prefix + 'fcff', last)}*(1+{g})/(({rate})-{g})"
        tv_x = f"({self.R(prefix + 'ebit', last)}+{self.R(prefix + 'da', last)})*{multiple}"
        tv = f"({wg})*({tv_g})+(1-({wg}))*({tv_x})" if method == "weighted" else tv_g if method == "gordon" else tv_x
        pv_tv = f"({tv})*(1+({rate}))^-{self.R(prefix + 'end_time', last)}"
        return pv, tv_g, tv_x, pv_tv

    def bridge_expr(self, ev):
        return f"({ev})+{self.I('b.cash')}+{self.I('b.valuation_cash_adjustment')}+{self.I('b.investments')}-{self.I('b.debt')}-{self.I('b.lease_liability')}-{self.I('b.minority')}"

    def share_expr(self):
        return f"{self.I('b.shares')}+{self.I('b.rsus')}+IF({self.I('b.share_price')}>{self.I('b.strike')},{self.I('b.options')}*(1-{self.I('b.strike')}/{self.I('b.share_price')}),0)"

    def dcf_block(self, prefix="", rate=None, growth=None, method="gordon"):
        rate = rate or self.wacc_expr()
        growth = growth or self.I("a.g")
        pv, tvg, tvx, pvtv = self.pv(prefix, rate, growth, method="weighted" if method == "weighted" else method)
        tv = f"{self.I('a.gordon_weight')}*({tvg})+(1-{self.I('a.gordon_weight')})*({tvx})" if method == "weighted" else tvg if method == "gordon" else tvx
        pvtv = f"({tv})*(1+({rate}))^-{self.R(prefix + 'end_time', self.s['horizon'] - 1)}"
        if self.s["c_structure"] in ("simple_dcf", "three_statements_dcf", "debt_schedule_dcf"):
            if self.s["assumptions"].get("gordon_weight", 1.0) == 0: tvg = "0"
            if self.s["assumptions"].get("gordon_weight", 1.0) == 1: tvx = "0"
        for key, formula in (("wacc", rate), ("terminal_growth", growth), ("exit_multiple", self.I("a.exit_multiple")),
                             ("tv_gordon", tvg), ("tv_exit", tvx), ("terminal_value", tv),
                             ("pv_explicit", pv), ("pv_terminal", pvtv), ("enterprise_value", f"({pv})+({pvtv})")):
            self.scalar(prefix + key, formula)
        self.scalar(prefix + "equity_value", self.bridge_expr(self.R(prefix + "enterprise_value")))
        self.scalar(prefix + "diluted_shares", self.share_expr())
        self.scalar(prefix + "value_per_share", f"{self.R(prefix + 'equity_value')}/{self.R(prefix + 'diluted_shares')}")

    def copy_key(self, key, source):
        if source in self.refs:
            if source in self.period_keys:
                self.series(key, lambda i, source=source: self.R(source, i))
            else: self.scalar(key, self.R(source))
        else: raise KeyError((key, source))

    def finish(self, path):
        for key in self.expected:
            if key in self.refs: continue
            if key in self.s.get("projects", {}):
                self.scalar(key, self.I("proj." + key.removesuffix("_success_probability") + ".success_probability"))
            elif key.rsplit("_p", 1)[0] in self.refs:
                base, period = key.rsplit("_p", 1)
                if not period.isdigit(): raise KeyError(f"unmapped expected output {key}")
                self.refs[key] = self.refs[base]
                self.period_keys.add(key)
            elif self.expected[key] == 0 and (self.s["c_structure"] in ("simple_dcf", "three_statements_dcf", "debt_schedule_dcf") or "_p" in key):
                self.series(key, lambda j: "0") if "_p" in key else self.scalar(key, "0")
            else: raise KeyError(f"unmapped expected output {self.s['task_id']} {key}")
        out = self.wb.create_sheet("Results")
        out.append(("key", "value"))
        for key in self.expected:
            parts = key.rsplit("_p", 1)
            period = int(parts[1]) - 1 if len(parts) == 2 and parts[1].isdigit() else None
            out.append((key, "=" + self.R(key, period)))
        self.decorate(path)

    def decorate(self, path):
        for ws in self.wb:
            ws.freeze_panes = "B2"
            ws.column_dimensions["A"].width = 48
            ws.column_dimensions["B"].width = 23
            ws.sheet_view.showGridLines = False
        self.wb.calculation.fullCalcOnLoad = True
        self.wb.calculation.forceFullCalc = True
        self.wb.calculation.calcMode = "auto"
        self.wb.save(path)


def public_copy(s):
    wb = load_workbook(s["_public_path"])
    wb.remove(wb["Required Keys"])
    return wb


def make_reference(s, path):
    s = copy.deepcopy(s)
    s["_public_path"] = Path(path).parent.parent / "environment" / "inputs.xlsx"
    if s["family"] == "A":
        return make_industry_reference(s, path)
    if s["c_structure"] in ("simple_dcf", "three_statements_dcf", "debt_schedule_dcf"):
        wb = public_copy(s)
        f = FormulaBook(s, wb)
        f.history_formulas()
        f.basic()
        f.dcf_block(method="weighted")
        standard_reference(s, f)
        return f.finish(path)
    wb = public_copy(s)
    s["_input_sheet"] = wb["Inputs"]
    f = FormulaBook(s, wb)
    f.history_formulas()
    if s["c_structure"] == "multi_method": multi_reference(s, f)
    elif s["c_structure"] == "scenario_operating_model": scenario_reference(s, f)
    elif s["c_structure"] == "segment_sotp": sotp_reference(s, f)
    elif s["c_structure"] == "risk_adjusted_pipeline": pipeline_reference(s, f)
    else: raise ValueError(s["c_structure"])
    f.finish(path)


def standard_reference(s, f):
    n = s["horizon"]
    lease = "leases" in s["enabled_modules"]
    f.series("rou_close", lambda i: "0")
    f.series("rou_additions", lambda i: f"{f.I('a.lease_additions', i)}*{f.R('activity', i)}" if lease else "0")
    f.series("rou_amortization", lambda i: f"({f.I('opening_rou') if i == 0 else f.R('rou_close', i - 1)}+{f.R('rou_additions', i)}*.5)*{f.I('a.rou_rate')}*{f.R('internal_days', i)}/365" if lease else "0")
    for i in range(n):
        f.model.cell(f.refs["rou_close"], 2 + i, f"={f.I('opening_rou') if i == 0 else f.R('rou_close', i - 1)}+{f.R('rou_additions', i)}-{f.R('rou_amortization', i)}")
        f.model.cell(f.refs["da"], 2 + i, "=" + f.R("ppe_depreciation", i) + "+" + f.R("rou_amortization", i))
    f.series("lease_liability_close", lambda i: f"{f.I('b.lease_liability') if i == 0 else f.R('lease_liability_close', i - 1)}+{f.R('rou_additions', i)}")
    f.series("borrowing", lambda i: f"{f.I('a.new_borrowing', i)}*{f.R('activity', i)}")
    f.series("repayment", lambda i: f"{f.I('a.debt_repayment', i)}*{f.R('activity', i)}")
    f.refs["debt_close"] = f.model.max_row + 2
    f.series("interest", lambda i: f"({f.I('opening_debt') if i == 0 else f.R('debt_close', i - 1)}+{f.R('borrowing', i)}*.5)*{f.I('a.interest_rate')}*{f.R('internal_days', i)}/365")
    f.series("debt_close", lambda i: f"{f.I('opening_debt') if i == 0 else f.R('debt_close', i - 1)}-{f.R('repayment', i)}+{f.R('borrowing', i)}")
    f.series("interest_tax_shield", lambda i: f"{f.R('interest', i)}*{f.I('a.tax')}")
    f.series("levered_tax", lambda i: f"{f.R('tax', i)}-{f.R('interest_tax_shield', i)}")
    f.series("cash_taxes", lambda i: f.R("levered_tax", i))
    f.series("tax_accrual", lambda i: "0")
    f.series("deferred_tax_asset", lambda i: "0")
    f.series("net_income", lambda i: f"{f.R('ebit', i)}-{f.R('interest', i)}-{f.R('levered_tax', i)}")
    f.series("sbc", lambda i: f"{f.R('revenue', i)}*{f.I('a.sbc_pct', i)}")
    f.series("sbc_reserve", lambda i: f"{f.I('opening_sbc_reserve')}+{f.R('sbc', i)}" if i == 0 else f"{f.R('sbc_reserve', i - 1)}+{f.R('sbc', i)}")
    f.series("retained_earnings", lambda i: f"{f.I('opening_retained_earnings') if i == 0 else f.R('retained_earnings', i - 1)}+{f.R('net_income', i)}")
    f.series("statement_opening_nwc", lambda i: f.I("opening_nwc_valuation_date") if i == 0 and "opening_nwc_valuation_date" in f.inputs else f.I("opening_nwc") if i == 0 else f.R("nwc", i - 1))
    f.series("statement_delta_nwc", lambda i: f"{f.R('nwc', i)}-{f.R('statement_opening_nwc', i)}")
    f.series("accrual_adjustments", lambda i: f"{f.R('da', i)}+{f.R('sbc', i)}-{f.R('statement_delta_nwc', i)}")
    f.series("cfo", lambda i: f"{f.R('net_income', i)}+{f.R('accrual_adjustments', i)}")
    f.series("cash_close", lambda i: f"{f.I('opening_cash') if i == 0 else f.R('cash_close', i - 1)}+{f.R('cfo', i)}-{f.R('capex', i)}+{f.R('borrowing', i)}-{f.R('repayment', i)}")
    f.series("cash_link", lambda i: f"{f.R('cash_close', i)}-({f.I('opening_cash') if i == 0 else f.R('cash_close', i - 1)}+{f.R('cfo', i)}-{f.R('capex', i)}+{f.R('borrowing', i)}-{f.R('repayment', i)})")
    f.series("operating_current_assets", lambda i: f"{f.R('nwc', i)}+{f.R('deferred_close', i)}")
    f.series("assets", lambda i: f"{f.R('cash_close', i)}+{f.R('operating_current_assets', i)}+{f.R('ppe_close', i)}+{f.R('rou_close', i)}+{f.I('b.investments')}+{f.R('deferred_tax_asset', i)}")
    f.series("liabilities_equity", lambda i: f"{f.R('debt_close', i)}+{f.R('lease_liability_close', i)}+{f.R('deferred_close', i)}+{f.R('retained_earnings', i)}+{f.I('contributed_capital')}+{f.I('b.minority')}+{f.R('sbc_reserve', i)}")
    f.series("balance_difference", lambda i: f"{f.R('assets', i)}-{f.R('liabilities_equity', i)}")
    f.series("discount_factor", lambda i: f"(1+{f.R('wacc')})^-{f.R('discount_time', i)}")
    f.series("pv_fcff", lambda i: f"{f.R('fcff', i)}*{f.R('discount_factor', i)}")
    if "capm" in s["enabled_modules"]:
        f.alias("levered_beta", "internal_levered_beta")
        f.alias("cost_of_equity", "internal_cost_equity")
    else:
        f.scalar("levered_beta", "0")
        f.scalar("cost_of_equity", "0")


def make_industry_reference(s, path):
    wb = public_copy(s)
    industry_reference(s, FormulaBook(s, wb), path)


def multi_reference(s, f):
    f.basic()
    f.dcf_block("gordon_", method="gordon")
    f.dcf_block("exit_", method="exit")
    f.scalar("implied_ev_ebitda_gordon", f"{f.R('gordon_tv_gordon')}/({f.R('ebit', s['horizon'] - 1)}+{f.R('da', s['horizon'] - 1)})")
    f.scalar("implied_g_exit", f"({f.R('gordon_wacc')}*{f.R('exit_tv_exit')}-{f.R('fcff', s['horizon'] - 1)})/({f.R('exit_tv_exit')}+{f.R('fcff', s['horizon'] - 1)})")
    ws = f.wb.create_sheet("Reverse WACC")
    ws.append(("iteration", "low", "high", "trial_wacc", "equity_less_market_target"))
    target = f"{f.I('m.market_price')}*({f.share_expr()})"
    def residual(rate):
        pv, _, _, pvtv = f.pv(rate=rate, method="gordon")
        return f"({pv})+({pvtv})+{f.I('b.cash')}+{f.I('b.valuation_cash_adjustment')}+{f.I('b.investments')}-{f.I('b.debt')}-{f.I('b.lease_liability')}-{f.I('b.minority')}-({target})"
    for i in range(80):
        row = i + 2
        ws.cell(row, 1, i + 1)
        ws.cell(row, 2, f"={f.I('a.g')}+0.021" if i == 0 else f"=IF(E{row-1}>0,D{row-1},B{row-1})")
        ws.cell(row, 3, "=0.3" if i == 0 else f"=IF(E{row-1}>0,C{row-1},D{row-1})")
        ws.cell(row, 4, f"=(B{row}+C{row})/2")
        ws.cell(row, 5, "=" + residual(f"D{row}"))
    f.scalar("implied_wacc_market", "'Reverse WACC'!D81")
    low_rate = f"({f.R('gordon_wacc')}+{f.I('a.valuation_wacc_delta')})"
    high_rate = f"({f.R('gordon_wacc')}-{f.I('a.valuation_wacc_delta')})"
    for key, rate, sign in (("internal_low_a", low_rate, -1), ("internal_low_b", high_rate, -1), ("internal_high_a", low_rate, 1), ("internal_high_b", high_rate, 1)):
        g = f"({f.I('a.g')}{'+' if sign > 0 else '-'}{f.I('a.valuation_g_delta')})"
        pv, _, _, pvtv = f.pv(rate=rate, g=g, method="gordon")
        ev = f"({pv})+({pvtv})"
        f.scalar(key, f"({f.bridge_expr(ev)})/({f.share_expr()})")
    f.scalar("valuation_low_vps", f"MIN({f.R('internal_low_a')},{f.R('internal_low_b')})")
    f.scalar("valuation_high_vps", f"MAX({f.R('internal_high_a')},{f.R('internal_high_b')})")


def scenario_reference(s, f):
    cases = f.wb.create_sheet("Cases")
    cases.append(("case_id", "name"))
    for row, name in enumerate(("Base", "Bull", "Bear"), 1):
        cases.append((row, name))
    cases["C1"] = "唯一情景选择（1=Base、2=Bull、3=Bear）"
    cases["C2"] = f"={f.I('a.scenario')}"
    for case, name in ((1, "base"), (2, "bull"), (3, "bear")):
        p = "case_" + name + "_"
        f.basic(p, case)
        rate = f"({f.wacc_expr()}+CHOOSE({case},0,{f.I('a.upside_wacc_delta')},{f.I('a.downside_wacc_delta')}))"
        f.dcf_block(p, rate=rate)
    active = f"CHOOSE(Cases!$C$2,{f.R('case_base_wacc')},{f.R('case_bull_wacc')},{f.R('case_bear_wacc')})"
    for key in f.expected:
        if key.startswith("case_") or key in f.refs: continue
        if key.endswith(tuple(f"_p{i}" for i in range(1, s["horizon"] + 1))):
            base, period = key.rsplit("_p", 1)
            i = int(period) - 1
            f.series(key, lambda j, base=base: f"CHOOSE(Cases!$C$2,{f.R('case_base_' + base, j)},{f.R('case_bull_' + base, j)},{f.R('case_bear_' + base, j)})")
        else:
            f.scalar(key, f"CHOOSE(Cases!$C$2,{f.R('case_base_' + key)},{f.R('case_bull_' + key)},{f.R('case_bear_' + key)})")


def sotp_reference(s, f):
    evs = []
    for name, z in sorted(s["segments"].items()):
        p = name + "_"
        f.refs[p + "driver_close"] = f.model.max_row + 2
        f.series(p + "driver_open", lambda i, z=z: f.I(f"seg.{name}.driver0") if i == 0 else f.R(p + "driver_close", i - 1))
        f.series(p + "driver_close", lambda i, z=z: f"{f.R(p + 'driver_open', i)}*(1-{f.I(f'seg.{name}.attrition_rate', i)})+{f.I(f'seg.{name}.driver_add', i)}")
        f.series(p + "average_driver", lambda i: f"({f.R(p + 'driver_open', i)}+{f.R(p + 'driver_close', i)})/2")
        f.series(p + "unit_price", lambda i: f"{f.I(f'seg.{name}.price0') if i == 0 else f.R(p + 'unit_price', i - 1)}*(1+{f.I(f'seg.{name}.price_growth', i)})")
        f.series(p + "revenue", lambda i: f"{f.R(p + 'average_driver', i)}*{f.R(p + 'unit_price', i)}" + (f"*(({v2_date(s, i)}-{f.I('valuation_date')})/({v2_date(s, i)}-{f.I('last_fy_end')}))" if i == 0 else ""))
        f.series(p + "ebit", lambda i: f"{f.R(p + 'revenue', i)}*{f.I(f'seg.{name}.ebit_margin', i)}")
        f.series(p + "capex", lambda i: f"{f.R(p + 'revenue', i)}*{f.I(f'seg.{name}.capex_pct', i)}")
        f.series(p + "ppe_close", lambda i: "0")
        f.series(p + "depreciation", lambda i: f"({f.I(f'seg.{name}.opening_ppe') if i == 0 else f.R(p + 'ppe_close', i - 1)}+{f.R(p + 'capex', i)}*.5)*{f.I('a.ppe_rate')}*{days(s, i)}/365")
        for i in range(s["horizon"]): f.model.cell(f.refs[p + "ppe_close"], 2 + i, f"={f.I(f'seg.{name}.opening_ppe') if i == 0 else f.R(p + 'ppe_close', i - 1)}+{f.R(p + 'capex', i)}-{f.R(p + 'depreciation', i)}")
        f.series(p + "da", lambda i: f.R(p + "depreciation", i))
        f.series(p + "tax", lambda i: f"{f.R(p + 'ebit', i)}*{f.I('a.tax')}")
        f.series(p + "nwc", lambda i: f"{f.R(p + 'revenue', i)}" + (f"/(({v2_date(s, i)}-{f.I('valuation_date')})/({v2_date(s, i)}-{f.I('last_fy_end')}))" if i == 0 else "") + f"*{f.I(f'seg.{name}.nwc_pct', i)}")
        f.series(p + "delta_nwc", lambda i: f"{f.R(p + 'nwc', i)}-{f.I(f'seg.{name}.opening_nwc') if i == 0 else f.R(p + 'nwc', i - 1)}")
        f.series(p + "fcff", lambda i: f"{f.R(p + 'ebit', i)}*(1-{f.I('a.tax')})+{f.R(p + 'depreciation', i)}-{f.R(p + 'capex', i)}-{f.R(p + 'delta_nwc', i)}")
        f.series(p + "end_time", lambda i: f"({v2_date(s, i)}-{f.I('valuation_date')})/365")
        f.series(p + "discount_time", lambda i: f"{f.R(p + 'end_time', i)}-" + (f"({v2_date(s, i)}-{f.I('valuation_date') if i == 0 else v2_date(s, i - 1)})/730" if s["time_axis"]["midyear"] else "0"))
        rate = f"({f.wacc_expr()}+{f.I(f'seg.{name}.wacc_delta')})"
        pv, tvg, tvx, pvtv = f.pv(p, rate=rate, method=z["method"])
        for key, formula in (("wacc", rate), ("terminal_growth", f.I("a.g")), ("exit_multiple", f.I("a.exit_multiple")), ("tv_gordon", tvg), ("tv_exit", tvx), ("terminal_value", tvg if z["method"] == "gordon" else tvx), ("pv_explicit", pv), ("pv_terminal", pvtv), ("enterprise_value", f"({pv})+({pvtv})")):
            f.scalar(p + key, formula)
        f.alias(p + "segment_enterprise_value", p + "enterprise_value")
        evs.append(f.R(p + "enterprise_value"))
    f.scalar("sotp_enterprise_value", "+".join(evs))
    f.alias("enterprise_value", "sotp_enterprise_value")
    f.scalar("wacc", f.wacc_expr())
    f.scalar("equity_value", f.bridge_expr(f.R("enterprise_value")))
    f.scalar("diluted_shares", f.share_expr())
    f.scalar("value_per_share", f"{f.R('equity_value')}/{f.R('diluted_shares')}")


def v2_date(s, i):
    row = next(r[0].row for r in s["_input_sheet"].iter_rows() if r[0].value == "last_fy_end")
    return f"EDATE(Inputs!$C${row},{12 * (i + 1)})"


def days(s, i):
    row = next(r[0].row for r in s["_input_sheet"].iter_rows() if r[0].value == "last_fy_end")
    opening = f"Inputs!$C${row}" if i == 0 else v2_date(s, i - 1)
    return f"({v2_date(s, i)}-{opening})"


def pipeline_reference(s, f):
    f.basic("existing_")
    f.dcf_block("existing_")
    pvs = []
    for name, p in s["projects"].items():
        key = name + "_"
        f.series(key + "commissioned", lambda i, name=name: f"--IF({i + 1}>={f.I(f'proj.{name}.commissioning_period')},1,0)")
        f.series(key + "revenue", lambda i, name=name: f"{f.I(f'proj.{name}.project_revenue', i)}*{f.R(key + 'commissioned', i)}*{f.R('existing_activity', i)}")
        f.series(key + "construction_capex", lambda i, name=name: f.I(f"proj.{name}.construction_capex", i))
        f.series(key + "tax_factor", lambda i: f"1-{f.I('a.tax')}")
        f.series(key + "margin", lambda i, name=name: f.I(f"proj.{name}.project_margin"))
        f.series(key + "operating_profit", lambda i, name=name: f"{f.R(key + 'revenue', i)}*{f.R(key + 'margin', i)}")
        f.series(key + "after_tax_operating", lambda i, name=name: f"{f.R(key + 'operating_profit', i)}*{f.R(key + 'tax_factor', i)}")
        f.series(key + "operating_da", lambda i, name=name: f"{f.R(key + 'commissioned', i)}*{f.I(f'proj.{name}.project_da', i)}*{f.R('existing_activity', i)}")
        f.series(key + "operating_capex", lambda i, name=name: f"{f.R(key + 'commissioned', i)}*{f.I(f'proj.{name}.project_operating_capex', i)}")
        f.series(key + "delta_nwc", lambda i, name=name: f"{f.R(key + 'commissioned', i)}*{f.I(f'proj.{name}.project_delta_nwc', i)}")
        f.series(key + "unrisked_fcff", lambda i, name=name: f"{f.R(key + 'after_tax_operating', i)}+{f.R(key + 'operating_da', i)}-{f.R(key + 'operating_capex', i)}-{f.R(key + 'delta_nwc', i)}-{f.R(key + 'construction_capex', i)}")
        f.series(key + "risk_adjusted_fcff", lambda i, name=name: f"{f.R(key + 'unrisked_fcff', i)}*{f.I(f'proj.{name}.success_probability')}")
        f.series(key + "discount_time", lambda i: f.R("existing_discount_time", i))
        f.series(key + "risk_adjusted_pv", lambda i, name=name: f"{f.R(key + 'risk_adjusted_fcff', i)}*(1+{f.wacc_expr()})^-{f.R(key + 'discount_time', i)}")
        f.scalar(key + "success_probability", f.I(f"proj.{name}.success_probability"))
        f.scalar(key + "risk_adjusted_pv_total", "+".join(f.R(key + "risk_adjusted_pv", i) for i in range(s["horizon"])))
        f.alias(key + "risk_adjusted_pv", key + "risk_adjusted_pv_total")
        pvs.append(f.R(key + "risk_adjusted_pv_total"))
    f.scalar("pipeline_risk_adjusted_pv", "+".join(pvs))
    f.scalar("enterprise_value", f"{f.R('existing_enterprise_value')}+{f.R('pipeline_risk_adjusted_pv')}")
    f.scalar("equity_value", f.bridge_expr(f.R("enterprise_value")))
    f.scalar("diluted_shares", f.share_expr())
    f.scalar("value_per_share", f"{f.R('equity_value')}/{f.R('diluted_shares')}")
    f.scalar("wacc", f.wacc_expr())


def industry_reference(s, f, path):
    a, kind, n = s["assumptions"], s["industry"], s["horizon"]
    activity = s.get("residual_activity", 1.0)
    if kind in ("banking", "insurance"):
        if kind == "banking":
            f.series("loans_close", lambda i: f"{f.I('a.opening_loans') if i == 0 else f.R('loans_close', i - 1)}*(1+{f.I('a.loan_growth', i)})")
            f.series("nim", lambda i: f.I("a.nim", i))
            f.series("net_interest_income", lambda i: f"({f.I('a.opening_loans') if i == 0 else f.R('loans_close', i - 1)}+{f.R('loans_close', i)})/2*{f.R('nim', i)}")
            f.series("net_income", lambda i: f"({f.R('net_interest_income', i)}+{f.R('loans_close', i)}*{f.I('a.fee_pct', i)}-{f.R('loans_close', i)}*{f.I('a.cost_pct', i)}-({f.I('a.opening_loans') if i == 0 else f.R('loans_close', i - 1)}+{f.R('loans_close', i)})/2*{f.I('a.credit_cost', i)})*(1-{f.I('a.tax')})")
            f.series("required_equity", lambda i: f"{f.R('loans_close', i)}*{f.I('a.risk_weight')}/{f.I('a.target_capital_ratio')}")
            f.series("equity_close", lambda i: f.R("required_equity", i))
            f.series("fcfe", lambda i: f"{f.R('net_income', i)}-({f.R('required_equity', i)}-{f.I('a.opening_equity') if i == 0 else f.R('equity_close', i - 1)})")
        else:
            f.series("earned_premium", lambda i: f"{f.I('a.opening_premium') if i == 0 else f.R('earned_premium', i - 1)}*(1+{f.I('a.premium_growth', i)})")
            f.series("combined_ratio", lambda i: f.I("a.combined_ratio", i))
            f.series("underwriting_profit", lambda i: f"{f.R('earned_premium', i)}*(1-{f.R('combined_ratio', i)})")
            f.series("investment_income", lambda i: f"{f.I('a.investment_assets')}*{f.I('a.investment_yield', i)}")
            f.series("net_income", lambda i: f"({f.R('underwriting_profit', i)}+{f.R('investment_income', i)})*(1-{f.I('a.tax')})")
            f.series("fcfe", lambda i: f"{f.R('net_income', i)}*(1-{f.I('a.retention_pct', i)})")
        f.series("discount_time", lambda i: str(i + 1 - (.5 if s["time_axis"]["midyear"] else 0)))
        r, g = f.I("a.cost_of_equity"), f.I("a.g")
        f.scalar("equity_cost", r)
        f.scalar("terminal_value", f"{f.R('fcfe', n - 1)}*(1+{g})/({r}-{g})")
        f.scalar("internal_pv_explicit", "+".join(f"{f.R('fcfe', i)}/(1+{r})^{f.R('discount_time', i)}" for i in range(n)))
        f.scalar("equity_value", f"{f.R('internal_pv_explicit')}+{f.R('terminal_value')}/(1+{r})^{n}")
        f.scalar("diluted_shares", f.I("b.shares"))
        f.scalar("value_per_share", f"{f.R('equity_value')}/{f.R('diluted_shares')}")
    elif kind == "real_estate":
        f.series("occupied_area", lambda i: f"{f.I('a.rentable_area')}*{f.I('a.occupancy', i)}")
        f.series("rental_revenue", lambda i: f"{f.R('occupied_area', i)}*{f.I('a.rent_per_unit', i)}")
        f.series("noi", lambda i: f"{f.R('rental_revenue', i)}*(1-{f.I('a.operating_cost_pct', i)})")
        f.series("property_value", lambda i: f"{f.R('noi', i)}/{f.I('a.cap_rate', i)}")
        f.scalar("property_value_at_valuation", f.R("property_value", 0))
        f.scalar("cap_rate", f.I("a.cap_rate", 0))
        f.scalar("nav", f"{f.R('property_value', 0)}+{f.I('b.cash')}-{f.I('b.debt')}-{f.I('a.capex_reserve')}")
        f.alias("equity_value", "nav")
        f.scalar("diluted_shares", f.I("b.shares"))
        f.scalar("value_per_share", f"{f.R('nav')}/{f.R('diluted_shares')}")
    else:
        f.refs["internal_driver_close"] = f.model.max_row + 2
        f.series("internal_driver_open", lambda i: f.I("a.driver0") if i == 0 else f.R("internal_driver_close", i - 1))
        def close(i):
            op = f.R("internal_driver_open", i)
            if kind == "software_subscription": return f"{op}*{f.I('a.net_revenue_retention', i)}+{f.I('a.new_arr', i)}"
            if kind == "retail_chain": return f"{f.I('a.opening_stores')}*(1-{f.I('a.store_closure_rate')})+{f.I('a.new_stores', i)}"
            if kind == "manufacturing": return f"{op}+{f.I('a.capacity_additions', i)}"
            if kind == "pharmaceutical": return f"{op}*(1+" + (f"IF({i + 1}<{f.I('a.cliff_period')},{f.I('a.pre_cliff_growth', i)},-{f.I('a.erosion_rate', i)}))")
            if kind == "energy_resources":
                base = f.I("a.opening_base_production") + "".join(f"*(1-{f.I('a.decline_rate', j)})" for j in range(i + 1))
                additions = "+".join(f"{f.I('a.development_capex', j)}/{f.I('a.capex_per_unit')}" for j in range(i + 1))
                return base + "+" + additions
            if kind == "utilities": return f"{op}+{f.I('a.rate_base_additions', i)}"
            if kind == "internet_platform": return f"{op}*(1-{f.I('a.churn_rate', i)})+{f.I('a.new_users', i)}"
            if kind == "professional_services": return f"{op}+{f.I('a.hiring', i)}"
            if kind == "equipment_service": return f"{op}*{f.I('a.renewal_rate', i)}+{f.I('a.new_installations', i)}"
        f.series("internal_driver_close", close)
        def revenue(i):
            op, cl = f.R("internal_driver_open", i), f.R("internal_driver_close", i)
            if kind == "software_subscription": return f"({op}+{cl})/2*{activity}"
            if kind == "retail_chain": return f"({f.I('a.opening_stores')}*(1-{f.I('a.store_closure_rate')})*{f.I('a.sales_per_store')}*(1+{f.I('a.same_store_growth', i)})+{f.I('a.new_stores', i)}*{f.I('a.sales_per_store')}*{f.I('a.new_store_months', i)}/12)*{activity}"
            if kind == "manufacturing": return f"{cl}*{f.I('a.utilization', i)}*{f.I('a.unit_price', i)}*{activity}"
            if kind == "pharmaceutical": return f"{cl}*{f.I('a.unit_price')}*{activity}"
            if kind == "energy_resources": return f"{cl}*{f.I('a.commodity_price', i)}*{activity}"
            if kind == "utilities": return f"({cl}*{f.I('a.allowed_return', i)}+{cl}*{f.I('a.regulatory_depreciation_rate', i)})*{activity}"
            if kind == "internet_platform": return f"({op}+{cl})/2*{f.I('a.arpu', i)}*{activity}"
            if kind == "professional_services": return f"{cl}*{f.I('a.utilization', i)}*{f.I('a.fee_rate', i)}*{activity}"
            if kind == "equipment_service": return f"({op}+{cl})/2*{f.I('a.service_frequency', i)}*{f.I('a.service_price', i)}*{activity}"
        f.series("revenue", revenue)
        metric = {"software_subscription": "arr_close", "retail_chain": "stores_close", "manufacturing": "effective_volume", "pharmaceutical": "product_volume", "energy_resources": "total_production", "utilities": "rate_base_close", "internet_platform": "users_close", "professional_services": "billable_headcount", "equipment_service": "installed_base_close"}[kind]
        if kind == "manufacturing": f.series(metric, lambda i: f"{f.R('internal_driver_close', i)}*{f.I('a.utilization', i)}")
        else: f.series(metric, lambda i: f.R("internal_driver_close", i))
        f.series("ebit", lambda i: f"{f.R('revenue', i)}*{f.I('a.ebit_margin', i)}")
        def da(i):
            if kind == "utilities": return f"{f.R('internal_driver_close', i)}*{f.I('a.regulatory_depreciation_rate', i)}*{activity}"
            pct = "content_amortization_pct" if kind == "internet_platform" else "da_pct"
            return f"{f.R('revenue', i)}*{f.I('a.' + pct, i)}"
        f.series("da", da)
        def capex(i):
            extra = "0"
            if kind == "software_subscription": extra = f"{f.R('revenue', i)}*{f.I('a.capitalized_rd_pct', i)}"
            if kind == "manufacturing": extra = f"{f.R('revenue', i)}*{f.I('a.extra_capex_pct', i)}"
            if kind == "energy_resources": extra = f"{f.I('a.development_capex', i)}*{activity}"
            if kind == "utilities": extra = f"{f.I('a.rate_base_additions', i)}*{activity}"
            return f"{f.R('revenue', i)}*{f.I('a.capex_pct', i)}+{extra}"
        f.series("capex", capex)
        f.series("nwc", lambda i: f"{f.R('revenue', i)}/{activity}*{f.I('a.nwc_pct', i)}")
        f.series("delta_nwc", lambda i: f"{f.R('nwc', i)}-{f.I('a.opening_nwc') if i == 0 else f.R('nwc', i - 1)}")
        f.series("fcff", lambda i: f"{f.R('ebit', i)}*(1-{f.I('a.tax')})+{f.R('da', i)}-{f.R('capex', i)}-{f.R('delta_nwc', i)}")
        def discount(i):
            if not s.get("residual_activity"): return str(i + 1 - (.5 if s["time_axis"]["midyear"] else 0))
            end = f"EDATE({f.I('last_fy_end')},12)"
            return f"({end}-{f.I('valuation_date')})/365" + (f"+{i}" if i else "") + (f"-(({end}-{f.I('valuation_date')})/730)" if s["time_axis"]["midyear"] and i == 0 else "")
        f.series("discount_time", discount)
        r, g = f.I("a.wacc"), f.I("a.g")
        f.scalar("wacc", r)
        f.scalar("terminal_value", f"{f.R('fcff', n - 1)}*(1+{g})/({r}-{g})")
        f.scalar("pv_terminal", f"{f.R('terminal_value')}/(1+{r})^{f.R('discount_time', n - 1)}")
        f.scalar("internal_pv_explicit", "+".join(f"{f.R('fcff', i)}/(1+{r})^{f.R('discount_time', i)}" for i in range(n)))
        f.scalar("enterprise_value", f"{f.R('internal_pv_explicit')}+{f.R('pv_terminal')}")
        f.scalar("equity_value", f.bridge_expr(f.R("enterprise_value")))
        f.scalar("diluted_shares", f.share_expr())
        f.scalar("value_per_share", f"{f.R('equity_value')}/{f.R('diluted_shares')}")
    f.finish(path)
