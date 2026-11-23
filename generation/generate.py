#!/usr/bin/env python3
"""Generate original virtual-company BC/A/D tasks with independent truth and live formulas."""
import argparse
import copy
import datetime as dt
import hashlib
import json
import random
import shutil
import sys
from pathlib import Path
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "core"))
from model import compute, apply_changes
import importlib.util
_v2core = ROOT / "legacy_v2"
import v2_model
import v3_model_alias
sys.modules["model"] = v2_model
sys.path.insert(0, str(_v2core))
import v2_workbook
sys.modules["workbook"] = v2_workbook
import rubrics
sys.path.pop()
_spec = importlib.util.spec_from_file_location("v2_generate", _v2core / "generate.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
v2_spec = _module.make_spec
sys.modules.pop("workbook")
sys.modules["model"] = v3_model_alias
_wspec = importlib.util.spec_from_file_location("workbook", ROOT / "core" / "workbook.py")
_wmodule = importlib.util.module_from_spec(_wspec)
sys.modules["workbook"] = _wmodule
_wspec.loader.exec_module(_wmodule)
make_public, make_reference, public_view = _wmodule.make_public, _wmodule.make_reference, _wmodule.public_view

B = {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "dual_asset_pool": "固定资产＋无形资产双资产池",
    "dual_terminal": "Gordon、退出倍数、双终值加权",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "cash_tax_nol": "现金税与 NOL",
    "debt_schedule": "债务计划表",
}
C = {
    "simple_dcf": "简版 DCF",
    "three_statements_dcf": "三表＋DCF",
    "segment_sotp": "分部经营模型＋SOTP",
    "risk_adjusted_pipeline": "风险调整管线 DCF",
    "scenario_operating_model": "情景驱动 Operating Model",
    "multi_method": "多方法估值与反推",
    "debt_schedule_dcf": "债务计划表＋DCF",
}
PLAN = {
    "BC01": ("simple_dcf", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge"]),
    "BC02": ("three_statements_dcf", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_fye_open", "equity_bridge", "cash_tax_nol"]),
    "BC03": ("segment_sotp", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge"]),
    "BC04": ("risk_adjusted_pipeline", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge"]),
    "BC05": ("scenario_operating_model", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge", "dual_terminal"]),
    "BC06": ("multi_method", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_fye_open", "equity_bridge", "dual_terminal"]),
    "BC07": ("debt_schedule_dcf", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge", "debt_schedule"]),
    "BC08": ("simple_dcf", ["mixed_ltm", "history_normalization", "residual_period", "actual_day_discount", "nwc_fye_open", "equity_bridge"]),
    "BC09": ("segment_sotp", ["mixed_ltm", "history_normalization", "residual_period", "actual_day_discount", "nwc_fye_open", "equity_bridge"]),
    "BC10": ("risk_adjusted_pipeline", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_fye_open", "equity_bridge", "dual_asset_pool"]),
    "BC11": ("scenario_operating_model", ["mixed_ltm", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge", "dual_asset_pool"]),
    "BC12": ("multi_method", ["mixed_ltm", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge", "dual_asset_pool"]),
    "BC13": ("three_statements_dcf", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_fye_open", "equity_bridge", "cash_tax_nol"]),
    "BC14": ("debt_schedule_dcf", ["mixed_ltm", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge", "debt_schedule"]),
    "BC15": ("simple_dcf", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge", "dual_terminal"]),
    "BC16": ("scenario_operating_model", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_fye_open", "equity_bridge", "dual_asset_pool"]),
}
DPLAN = {
    "D01": ("multi_method", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_fye_open", "equity_bridge"]),
    "D02": ("scenario_operating_model", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge", "dual_terminal"]),
    "D03": ("segment_sotp", ["mixed_ltm", "history_normalization", "residual_period", "actual_day_discount", "nwc_valuation_open", "equity_bridge"]),
    "D04": ("risk_adjusted_pipeline", ["fiscal_timing", "history_normalization", "residual_period", "actual_day_discount", "nwc_fye_open", "equity_bridge", "dual_asset_pool"]),
}
COMPANIES = ["栖岸云档", "澄川精密", "岚衡多业", "微禾生科", "杉湾冷链", "远岱材料", "沐原家居", "序光档案", "洲禾联合", "沛源新材", "栖云办公", "朔方芯材", "白榆医械", "鹿原装备", "韶光文旅", "连岳智造"]
DCOMPANIES = ["砾川数科", "星榫食品", "衡浦组合", "禾汐药业"]
BASE = ["P-ARR中枢", "P-自有基座", "N-期中滚动", "E-事件终值"]
INDUSTRIES = ["software_subscription", "retail_chain", "manufacturing", "pharmaceutical", "banking", "energy_resources", "utilities", "real_estate"]
INDUSTRY_NAMES = {"software_subscription": "软件与订阅 SaaS", "retail_chain": "消费零售与连锁", "manufacturing": "制造与工业设备", "pharmaceutical": "医药与生物科技", "banking": "银行与金融", "insurance": "保险", "energy_resources": "能源与资源", "utilities": "公用事业与基础设施", "real_estate": "房地产", "internet_platform": "互联网平台与媒体", "professional_services": "专业服务与外包", "equipment_service": "设备即服务与装机运维"}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write(path, text, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable: path.chmod(0o755)


def base(tid, index, family="BC"):
    # Data and company names are newly seeded v3 choices; v2 is used only as a financial arithmetic primitive.
    s = v2_spec((index * 7 + 3) % 24, 391731 + index * 977, "F")
    s.update(schema_version="v3.0", task_id=tid, family=family, company=COMPANIES[index - 1] if family == "BC" else DCOMPANIES[int(tid[1:]) - 1])
    s["history"] = copy.deepcopy(s["history"])
    s["history"] = [dict(row, revenue=round(row["revenue"] * (1.037 + index * .0013), 6),
                         ebit=round(row["ebit"] * (1.021 + index * .0007), 6),
                         operating_cost_ex_sbc=round(row["operating_cost_ex_sbc"] * 1.037, 6),
                         sbc=round(row["sbc"] * 1.011, 6),
                         nonrecurring_gain=round(row["nonrecurring_gain"] * 1.023, 6)) for row in s["history"]]
    s["output"] = {"template": "free_layout"}
    s["assumptions"].pop("segment_revenue", None)
    s["assumptions"].pop("segment_margin", None)
    s["perturbations"] = []
    s["assumptions"]["gordon_weight"] = 1.0
    s["assumptions"]["scenario"] = 1
    s["assumptions"]["upside_reinvestment_delta"] = .12
    s["assumptions"]["downside_reinvestment_delta"] = -.10
    s["assumptions"]["upside_wacc_delta"] = -.005
    s["assumptions"]["downside_wacc_delta"] = .006
    s["assumptions"]["valuation_wacc_delta"] = .0075
    s["assumptions"]["valuation_g_delta"] = .004
    s["assumptions"]["intangible_additions"] = [round(18 + index * 1.7 + i * 4, 3) for i in range(s["horizon"])]
    s["assumptions"]["intangible_rate"] = .16
    s["opening_intangible"] = round(96 + index * 7.3, 3)
    s["nwc_opening_basis"] = "valuation_date"
    s["enabled_modules"] = list(dict.fromkeys(s["enabled_modules"] + ["nwc_days", "rolling_assets"]))
    s["enabled_modules"] = [m for m in s["enabled_modules"] if m not in ("scenario", "valuation_sensitivity", "dual_terminal")]
    s["time_axis"]["history_frequency"] = "semiannual" if index % 2 else "quarterly"
    if s["c_structure"] if "c_structure" in s else False: del s["c_structure"]
    return s


def mixed_history(s):
    fy = dt.date.fromisoformat(s["last_fy_end"])
    # Preserve independent H1 and bridge-quarter facts; no H1 is re-annualized.
    rows = []
    for year_offset in (-2, -1, 0):
        end = dt.date(fy.year + year_offset, fy.month, fy.day)
        start_h1 = dt.date(end.year - 1, end.month, end.day) + dt.timedelta(days=1)
        start_h2 = dt.date(end.year, end.month, end.day)
        # Half-year dates are created by calendar month arithmetic below.
        def minus_month(d, months):
            year, month = divmod(d.year * 12 + d.month - 1 - months, 12)
            month += 1
            return dt.date(year, month, min(d.day, [31,29 if year%4==0 and (year%100 or year%400==0) else 28,31,30,31,30,31,31,30,31,30,31][month-1]))
        h1start = minus_month(end, 12) + dt.timedelta(days=1)
        h2start = minus_month(end, 6) + dt.timedelta(days=1)
        for j, (start, finish) in enumerate(((h1start, minus_month(end, 6)), (h2start, end))):
            rows.append({"start": start.isoformat(), "end": finish.isoformat(), "fiscal_year": str(end.year), "period_type": "half_year",
                "revenue": round(330 + year_offset * 20 + j * 185 + s["candidate_index"] * 2.1, 6),
                "operating_cost_ex_sbc": 275 + year_offset * 14 + j * 145,
                "sbc": 9.5 + j, "nonrecurring_gain": 2.2 if j == 1 else 0.0})
    qend = minus_month(fy, -3)
    qstart = fy + dt.timedelta(days=1)
    assert 89 <= (qend - qstart).days + 1 <= 92, (qstart, qend)
    s["valuation_date"] = (qend + dt.timedelta(days=14)).isoformat()
    assert qend < dt.date.fromisoformat(s["valuation_date"]), (qend, s["valuation_date"])
    rows.append({"start": qstart.isoformat(), "end": qend.isoformat(), "fiscal_year": str(fy.year + 1), "period_type": "bridge_quarter",
                 "revenue": 267.4 + s["candidate_index"] * 1.7, "operating_cost_ex_sbc": 215.2, "sbc": 5.7, "nonrecurring_gain": 1.1})
    s["history"] = rows
    s["time_axis"]["history_frequency"] = "mixed_h1_q"


def choose_bc(tid, index, structure, bitems, family="BC"):
    s = base(tid, index, family)
    s["b_items"] = bitems
    s["b_item_definitions"] = {key: B[key] for key in bitems}
    s["c_structure"] = structure
    s["c_structure_definition"] = C[structure]
    if structure not in ("simple_dcf", "three_statements_dcf", "debt_schedule_dcf"):
        s["enabled_modules"] = [m for m in s["enabled_modules"] if m in ("residual_period", "working_capital", "nwc_days", "rolling_assets", "capm")]
        s["opening_deferred"] = 0
        s["opening_rou"] = 0
        s["assumptions"]["lease_additions"] = [0] * s["horizon"]
        s["bridge"]["lease_liability"] = 0
    s["structure"] = {"b": bitems, "c": structure}
    if "mixed_ltm" in bitems: mixed_history(s)
    if "nwc_fye_open" in bitems:
        s["nwc_opening_basis"] = "last_fiscal_year_end"
        s["opening_nwc_last_fye"] = round(s["opening_nwc"] * 1.084 + 3.2, 6)
        s["opening_nwc_valuation_date"] = s["opening_nwc"]
        s["opening_nwc"] = s["opening_nwc_last_fye"]
    else: s["nwc_opening_basis"] = "valuation_date"
    if "dual_terminal" in bitems:
        s["assumptions"]["gordon_weight"] = .6
        s["enabled_modules"].append("dual_terminal")
    if "cash_tax_nol" in bitems: s["enabled_modules"].append("nol")
    if "dual_asset_pool" in bitems: s["enabled_modules"].append("intangible_pool")
    if structure == "three_statements_dcf": s["enabled_modules"].append("three_statements")
    if structure == "debt_schedule_dcf": s["enabled_modules"].append("debt_schedule")
    s["market"] = {"market_price": round(13 + index * .91, 4)}
    if structure == "multi_method":
        s["assumptions"]["wacc"] = .101 + index * .0007
        if "capm" in s["enabled_modules"]: s["enabled_modules"].remove("capm")
    if structure == "scenario_operating_model":
        s["enabled_modules"].append("scenario")
        s["assumptions"]["gordon_weight"] = 1.0
        s["enabled_modules"] = [m for m in s["enabled_modules"] if m != "dual_terminal"]
    if structure == "segment_sotp":
        s["segments"] = {}
        for name, offset in (("segment_alpha", 0), ("segment_beta", 1)):
            s["segments"][name] = {"driver0": 71 + index * 3 + offset * 25,
                "attrition_rate": [.04, .045, .05, .055, .06, .065][:s["horizon"]],
                "driver_add": [9 + index * .4 + offset * 2 + i for i in range(s["horizon"])],
                "price0": round(7.8 + index * .22 + offset * 2.1, 4), "price_growth": [.022 + .002 * i for i in range(s["horizon"])],
                "ebit_margin": [.19 + offset * .035 + .003 * i for i in range(s["horizon"])],
                "capex_pct": [.065 + offset * .014 for _ in range(s["horizon"])],
                "nwc_pct": [.14 + offset * .045 for _ in range(s["horizon"])],
                "opening_nwc": 53 + index + offset * 29, "opening_ppe": 127 + index * 2 + offset * 58,
                "wacc_delta": -.007 + offset * .013, "method": "gordon" if offset == 0 else "exit"}
    if structure == "risk_adjusted_pipeline":
        s["projects"] = {}
        for name, offset in (("project_atlas", 0), ("project_boreal", 1)):
            cp = [0] * s["horizon"]
            cp[offset] = round(64 + index * 3 + offset * 29, 3)
            revenue = [round(95 + index * 2.7 + i * 16 + offset * 23, 4) for i in range(s["horizon"])]
            flow = []
            for i in range(s["horizon"]):
                active = (i + 1) >= offset + 2
                activity = (dt.date.fromisoformat(s["last_fy_end"]).replace(year=dt.date.fromisoformat(s["last_fy_end"]).year + 1) - dt.date.fromisoformat(s["valuation_date"])).days / 365 if i == 0 else 1
                rev = revenue[i] * activity if active else 0
                flow.append(round(rev * (.21 + offset * .035) * (1 - s["assumptions"]["tax"]) + (7 + i * 2) * activity - cp[i] - (8 + offset * 3) - (2 + i) if active else -cp[i], 6))
            s["projects"][name] = {"commissioning_period": offset + 2, "construction_capex": cp,
                "project_revenue": revenue, "project_margin": .21 + offset * .035,
                "project_da": [7 + i * 2 for i in range(s["horizon"])], "project_operating_capex": [8 + offset * 3] * s["horizon"],
                "project_delta_nwc": [2 + i for i in range(s["horizon"])], "project_fcff": flow, "success_probability": .67 - offset * .14}
    return s


def industry(tid, i, kind):
    n = 4 if i % 3 == 0 else 5
    fy = dt.date(2024 + i % 2, [3, 6, 9, 11][i % 4], [31, 30, 30, 30][i % 4])
    valuation = fy + dt.timedelta(days=80 + i * 9)
    end = dt.date(fy.year + 1, fy.month, fy.day)
    activity = (end - valuation).days / (end - fy).days
    s = {"schema_version": "v3.0", "task_id": tid, "family": "A", "company": ["弦庭软科", "榉邻商业", "衡铸工业", "澜序医药", "敦衡银行", "岫原能源", "砚川公用", "栖桐置业"][i - 1],
        "industry": kind, "industry_name": INDUSTRY_NAMES[kind], "base_structure": BASE[(i - 1) % 4],
        "industry_drivers": [], "valuation_date": valuation.isoformat(), "last_fy_end": fy.isoformat(), "horizon": n,
        "time_axis": {"midyear": i % 2 == 0, "history_frequency": "annual", "day_count": "actual/365"},
        "accounting": {"sbc_expense": True, "industry_valuation": True}, "residual_activity": activity,
        "enabled_modules": ["industry_driver", "residual_period"], "history": [],
        "bridge": {"cash": 130 + i * 9, "debt": 190 + i * 13, "investments": 24 + i, "lease_liability": 12 + i,
                   "minority": 5 + i, "valuation_cash_adjustment": 0, "shares": 72 + i * 3, "rsus": 1.2, "options": 0, "strike": 0, "share_price": 15},
        "assumptions": {"tax": .23, "wacc": .099 + i * .001, "g": .025, "driver0": 380 + i * 24, "ebit_margin": [.16 + .004 * j for j in range(n)],
            "da_pct": [.052] * n, "capex_pct": [.065] * n, "nwc_pct": [.13] * n, "opening_nwc": 59 + i * 4}}
    a = s["assumptions"]
    if kind == "software_subscription":
        a.update(driver0=730, net_revenue_retention=[1.04 + .005 * j for j in range(n)], new_arr=[98 + j * 13 for j in range(n)], capitalized_rd_pct=[.075] * n)
        s["industry_drivers"] = ["ARR 净留存与新签", "平均 ARR 收入确认", "资本化研发"]
    elif kind == "retail_chain":
        a.update(opening_stores=213, store_closure_rate=.018, new_stores=[17 + j * 2 for j in range(n)], sales_per_store=5.7, same_store_growth=[.036 - .002 * j for j in range(n)], new_store_months=[5, 6, 7, 6, 5])
        s["industry_drivers"] = ["同店销售增长", "开关店与新店月份", "店均收入"]
    elif kind == "manufacturing":
        a.update(driver0=420, capacity_additions=[0, 42, 0, 36, 0], utilization=[.72 + .02 * j for j in range(n)], unit_price=[2.35 * (1 + .023 * j) for j in range(n)], extra_capex_pct=[.018] * n)
        s["industry_drivers"] = ["投产产能与利用率", "产品价格", "维护与扩产资本开支"]
    elif kind == "pharmaceutical":
        a.update(driver0=165, pre_cliff_growth=[.08] * n, cliff_period=3, erosion_rate=[.28] * n, unit_price=4.9)
        s["industry_drivers"] = ["核心产品量", "专利悬崖侵蚀", "研发后利润率"]
    elif kind == "banking":
        a.update(opening_loans=16400, opening_equity=1840, loan_growth=[.065 - .004 * j for j in range(n)], risk_weight=.72, target_capital_ratio=.115, nim=[.027 + .0005 * j for j in range(n)], fee_pct=[.004] * n, cost_pct=[.014] * n, credit_cost=[.0035] * n, cost_of_equity=.108, g=.027)
        s["industry_drivers"] = ["平均生息资产与净息差", "贷款增长与资本充足率", "股权现金流"]
    elif kind == "energy_resources":
        a.update(opening_base_production=380, decline_rate=[.08 - .003 * j for j in range(n)], development_capex=[165 + j * 20 for j in range(n)], capex_per_unit=4.3, commodity_price=[1.94 + j * .05 for j in range(n)])
        s["industry_drivers"] = ["现有储量递减", "开发资本开支新增产量", "商品价格"]
    elif kind == "utilities":
        a.update(driver0=1520, rate_base_additions=[90 + j * 8 for j in range(n)], allowed_return=[.068] * n, regulatory_depreciation_rate=[.037] * n)
        s["industry_drivers"] = ["受监管资产基数", "允许回报率与折旧回收", "长期资本开支"]
    elif kind == "real_estate":
        a.update(rentable_area=98000, occupancy=[.91, .925, .93, .94, .94], rent_per_unit=[.0031 + j * .00008 for j in range(n)], operating_cost_pct=[.29] * n, cap_rate=[.061] * n, capex_reserve=28)
        s["industry_drivers"] = ["可租面积与出租率", "单位租金", "NOI 资本化率与 NAV"]
    return s


def changes_for(s):
    a = s["assumptions"]
    if s["family"] == "A":
        kind = s["industry"]
        if kind == "banking": return [{"a.nim.0": a["nim"][0] * 1.06, "a.loan_growth.1": a["loan_growth"][1] * 1.08, "a.cost_of_equity": a["cost_of_equity"] + .003}, {"a.credit_cost.0": a["credit_cost"][0] * 1.12, "a.g": a["g"] - .002, "b.shares": s["bridge"]["shares"] * 1.025}]
        if kind == "real_estate": return [{"a.occupancy.0": a["occupancy"][0] * 1.025, "a.cap_rate.0": a["cap_rate"][0] * .97}, {"a.rent_per_unit.1": a["rent_per_unit"][1] * 1.04, "b.debt": s["bridge"]["debt"] * .94}]
        keys = {"software_subscription": "new_arr", "retail_chain": "same_store_growth", "manufacturing": "utilization", "pharmaceutical": "erosion_rate", "energy_resources": "commodity_price", "utilities": "allowed_return", "internet_platform": "arpu"}[kind]
        return [{f"a.{keys}.0": a[keys][0] * 1.04, "a.ebit_margin.1": a["ebit_margin"][1] + .003, "a.wacc": a["wacc"] + .004, "b.cash": s["bridge"]["cash"] + 13}, {f"a.{keys}.1": a[keys][1] * .96, "a.capex_pct.2": a["capex_pct"][2] * 1.14, "a.g": a["g"] - .002, "b.debt": s["bridge"]["debt"] * 1.06}]
    c = s["c_structure"]
    if c == "segment_sotp":
        name = sorted(s["segments"])[0]
        z = s["segments"][name]
        return [{f"seg.{name}.driver_add.0": z["driver_add"][0] * 1.12, f"seg.{name}.ebit_margin.1": z["ebit_margin"][1] + .004, "a.wacc": a["wacc"] + .004, "b.cash": s["bridge"]["cash"] + 12}, {f"seg.{name}.price_growth.1": z["price_growth"][1] * 1.15, "a.exit_multiple": a["exit_multiple"] * .96, "b.debt": s["bridge"]["debt"] * 1.07}]
    if c == "risk_adjusted_pipeline":
        name = sorted(s["projects"])[0]
        p = s["projects"][name]
        return [{f"proj.{name}.project_revenue.2": p["project_revenue"][2] * 1.12, f"proj.{name}.success_probability": p["success_probability"] * .94, "a.wacc": a["wacc"] + .004, "b.cash": s["bridge"]["cash"] + 11}, {f"proj.{name}.construction_capex.0": p["construction_capex"][0] * 1.1, "a.ebit_margin.1": a["ebit_margin"][1] + .004, "b.debt": s["bridge"]["debt"] * 1.06}]
    key = "driver_add" if s["business"]["driver"] != "volume_price" else "driver_growth"
    return [{f"a.{key}.0": a[key][0] * 1.09, "a.ebit_margin.1": a["ebit_margin"][1] + .003, "a.wacc": a["wacc"] + .004, "b.cash": s["bridge"]["cash"] + 12}, {"a.price_growth.1": a["price_growth"][1] * 1.13, "a.capex_pct.2": a["capex_pct"][2] * 1.1, "a.g": a["g"] - .002, "b.debt": s["bridge"]["debt"] * 1.08}]


def expected(s):
    result = {"baseline": compute(s), "perturbations": []}
    for i, changes in enumerate(changes_for(s), 1):
        result["perturbations"].append({"label": f"hidden_operating_valuation_bridge_{i}", "input_changes": changes, "expected": compute(apply_changes(s, changes))})
    return result


EVENT_NAMES = {"rebase": "基期重定", "financing_and_capex_rearrangement": "扩产与融资重排", "terminal_method_change": "终值方法变更",
    "scenario_switch": "经营情景切换", "disposal": "业务剥离", "acquisition": "收购新分部", "nwc_opening_basis_change": "营运资本期初口径变更",
    "commissioning_and_capex_rearrangement": "项目延期投产与建设支出重排", "project_capex_and_scope_revision": "项目规模与建设支出调整"}
STRUCTURE_LEAD = {
    "simple_dcf": "本题交付单一主体的 DCF：从经营预测推出 FCFF，折现后经股权桥得到每股价值。",
    "three_statements_dcf": "本题需先搭建利润表、资产负债表和现金流量表三张预测报表，再在其上完成 DCF。",
    "segment_sotp": "公司由两个经营特征不同的分部组成，需要分别建模估值，再按分部加总（SOTP）得到公司价值。",
    "risk_adjusted_pipeline": "公司价值由已有业务和两个在建项目组成，项目需按投产时间和成功概率做风险调整后估值。",
    "scenario_operating_model": "管理层给出 Base、Bull、Bear 三套经营方案，需要搭建可一键切换情景的经营模型并完成 DCF。",
    "multi_method": "本题不只要一个目标价：需用 Gordon 与退出倍数两种方法分别估值，做反向推导，并给出估值区间。",
    "debt_schedule_dcf": "公司在预测期内有新增借款和还款安排，需要在 DCF 之外建立完整的债务计划表。",
}


def _md(d):
    d = dt.date.fromisoformat(d)
    return f"{d.month} 月 {d.day} 日"


def _bc_body(s):
    b, a, n = s["b_items"], s["assumptions"], s["horizon"]
    vd, fye = s["valuation_date"], s["last_fy_end"]
    conv = "年中" if s["time_axis"]["midyear"] else "期末"
    freq = s["time_axis"]["history_frequency"]
    lines = [STRUCTURE_LEAD[s["c_structure"]]]
    timing = f"公司财年截至每年 {_md(fye)}，最近完整财年末为 `{fye}`，估值日 `{vd}` 落在财年中间。" if "fiscal_timing" in b else f"最近完整财年末为 `{fye}`，估值日为 `{vd}`。"
    lines += [timing + f"预测共 {n} 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用{conv}惯例，终值落在最后一个完整财年末。"]
    if freq == "mixed_h1_q":
        lines += ["历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。"]
    else:
        lines += [f"历史数据按{'半年度' if freq == 'semiannual' else '季度' if freq == 'quarterly' else '期间'}提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。"]
    basis = "估值日余额" if s["nwc_opening_basis"] == "valuation_date" else "最近财年末余额"
    lines += [f"营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **{basis}** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。"]
    lines += ["从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。"]
    if "dual_terminal" in b and s["c_structure"] != "multi_method":
        w = a.get("gordon_weight", 1.0)
        if w < 1: lines += [f"终值同时用 Gordon 永续增长法和退出倍数法计算，再按 Gordon {w:.0%}、退出倍数 {1 - w:.0%} 的权重加权，两种终值都要单独列示。"]
        else: lines += ["终值的 Gordon 永续增长法与退出倍数法都要单独列示；按输入中的 Gordon 权重（本题为 100%）计入估值。"]
    if "cash_tax_nol" in b: lines += ["公司期初有可结转的税务亏损（nol0）：现金税须先用亏损抵减应税利润，并逐期滚动亏损余额，不能直接按 EBIT×税率计税。"]
    if "dual_asset_pool" in b: lines += ["固定资产与无形资产分别滚动：期初＋新增－折旧/摊销＝期末；无形资产新增扣 FCFF，摊销加回，不能与固定资产混池。"]
    c = s["c_structure"]
    if c == "segment_sotp": lines += ["两个分部各自独立预测经营基数、单位收入、利润率、资本开支、折旧、NWC 与 FCFF，分别按题设 DCF 或退出倍数估值。公司层净债务和稀释股数只在加总后使用一次。"]
    if c == "risk_adjusted_pipeline": lines += ["项目投产期之前收入必须为零；建设期支出独立计入对应期间。项目经营 FCFF 单列后乘成功概率，概率不得加到 WACC。已有业务价值与项目风险调整现值分开列示后相加。"]
    if c == "scenario_operating_model": lines += ["设置 `Cases` 页，唯一选择格链接 `a.scenario`（1=Base、2=Bull、3=Bear）。需求、利润率、再投资、FCFF、终值与每股价值必须随同一开关联动；另分别保留三情景独立输出，不能只交一张敏感性表。"]
    if c == "multi_method": lines += ["分别给出 Gordon 与退出倍数的终值、EV、股权价值和每股价值，不得加权成一个数。由 Gordon 终值反推隐含 EV/EBITDA，由退出倍数反推隐含 g，并用给定股价在工作簿内以公式迭代/求解隐含 WACC；Football Field 按给定折现率和增长区间。"]
    if c == "three_statements_dcf": lines += ["三表须勾稽：现金与现金流量表一致、留存收益由净利润滚动、资产等于负债加权益，不得使用不透明平衡项。"]
    if c == "debt_schedule_dcf" or "debt_schedule" in b: lines += ["借款、偿还、利息与期末债务逐期滚动连续，融资现金流与 FCFF 分离。"]
    if c == "simple_dcf": lines += ["建立 EBIT、无杠杆现金税、折旧摊销、资本开支与 ΔNWC 到 FCFF 的完整桥，再折现并完成股权桥。"]
    return lines


def _a_body(s):
    kind, n = s["industry"], s["horizon"]
    conv = "年中" if s["time_axis"]["midyear"] else "期末"
    lines = [f"公司属于**{s['industry_name']}**。经营预测必须以{'、'.join(s['industry_drivers'])}为驱动搭建行业经营表，不得只用单一增长率外推。"]
    if kind == "banking":
        lines += [f"最近完整财年末为 `{s['last_fy_end']}`，估值日为 `{s['valuation_date']}`。预测 {n} 个完整年度，按第 1 至第 {n} 年整年折现，采用{conv}惯例，终值在第 {n} 年末。",
                  "按平均生息资产×净息差计算净利息收入，按风险加权资产与目标资本充足率滚动所需权益。使用股权现金流并以股权成本折现，**不得使用 FCFF/WACC**。"]
    elif kind == "real_estate":
        lines += [f"最近完整财年末为 `{s['last_fy_end']}`，估值日为 `{s['valuation_date']}`，预测 {n} 期经营数据。",
                  "按面积×出租率×单位租金计算收入，扣经营成本得到 NOI；以首个预测期 NOI/资本化率得到估值日物业价值，再加现金、减债务和资本开支储备得到 NAV。**不得使用 FCFF/WACC。**"]
    else:
        lines += [f"最近完整财年末为 `{s['last_fy_end']}`，估值日 `{s['valuation_date']}` 落在财年中间。预测共 {n} 期：第 1 期是估值日到本财年末的残余期，经营量按残期天数比例计入，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用{conv}惯例，终值落在最后一个预测期末。",
                  "收入、利润率、再投资和营运资本须从行业驱动连接到 DCF；SBC 是经营成本且不在 FCFF 加回。"]
    return lines


def instruction(s, step=None):
    tid, company = s["task_id"], s["company"]
    lines = [f"# {tid}｜{company}估值建模", "", "你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。", ""]
    lines += _a_body(s) if s["family"] == "A" else _bc_body(s)
    lines += ["", "## 交付与输出键", "在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。", "隐藏检查会重算并执行两组经营、估值与股权桥扰动。"]
    if step is not None and step > 1:
        detail = s.get("event_public_facts", {}).get("description", "按事件输入重连受影响的经营、资产、融资与估值依赖。")
        lines += ["", f"## 第 {step} 步修改：{EVENT_NAMES.get(s.get('event_type'), '结构调整')}", detail.rstrip("。") + "。", "读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。", "先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-" + str(step) + ".xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。"]
    elif s["family"] == "D": lines += ["", "每步完成后将对应工作簿保存为 `/app/snapshots/step-N.xlsx`；不得覆盖前步快照。"]
    return "\n".join(lines) + "\n"


def task_toml(s, d_steps=None):
    base = '''schema_version = "1.4"
artifacts = ["/app/output.xlsx", "/app/memo.md"]
[task]
name = "dcf-v3/%s"
version = "3.0.0"
description = "原创造题：独立真值、活公式与隐藏扰动"
[metadata]
difficulty = "hard"
category = "finance"
[environment]
network_mode = "no-network"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 4096
[agent]
timeout_sec = 3600.0
disable_web_search = true
network_mode = "no-network"
[verifier]
timeout_sec = 900.0
environment_mode = "shared"
''' % s["task_id"].lower()
    if d_steps:
        base += 'multi_step_reward_strategy = "mean"\n'
        for i in range(1, d_steps + 1): base += f'[[steps]]\nname = "step-{i}"\n[steps.verifier]\ntimeout_sec = 900.0\n'
    return base


def common_files(task, s, d_step=False):
    save(task / "environment" / "inputs.json", public_view(s))
    save(task / "tests" / "expected.json", expected(s))
    save(task / "tests" / "grader_spec.json", s)
    for name in ("grader.py",): shutil.copy2(ROOT / "core" / name, task / "tests" / name)
    save(task / "tests" / "public_history.json", s.get("history", []))
    test_script = '''#!/bin/bash
set -e
mkdir -p /logs/verifier /app
cp /task/environment/inputs.xlsx /task/environment/inputs.json /app/
if [ -f /task/environment/event.json ]; then cp /task/environment/event.json /task/environment/event_inputs.xlsx /task/environment/event_inputs.json /app/; fi
python3 /tests/grader.py --task-dir /tests --candidate /app/output.xlsx --work-dir /logs/verifier/work --report /logs/verifier/report.json
'''
    write(task / "tests" / "test.sh", test_script, True)
    write(task / "tests" / "Dockerfile", "FROM dcfbench-base:v1\nCOPY . /tests/\nRUN chmod +x /tests/test.sh\n")
    write(task / "solution" / "solve.sh", '#!/bin/bash\nset -euo pipefail\ncp "$(dirname "$0")/reference.xlsx" /app/output.xlsx\ncp "$(dirname "$0")/memo.md" /app/memo.md\n', True)
    write(task / "solution" / "memo.md", f"# {s['task_id']} 参考说明\n\n本题以行业/经营驱动、利润率、再投资与估值桥构成因果链；所有输出由公开输入的活公式计算。\n\n局限：这是原创虚拟企业的冻结假设模型，不是实际市场预测或投资建议；机械外推未覆盖未披露的经营风险。\n")
    write(task / "environment" / "Dockerfile", "FROM dcfbench-agent:v1\nWORKDIR /app\nCOPY inputs.xlsx inputs.json /app/\nRUN mkdir -p /app/snapshots\n")
    write(task / "environment" / "docker-compose.yaml", "services:\n  main:\n    network_mode: none\n")


def build_one(s, task=None, instruction_step=None):
    task = Path(task or ROOT / "tasks" / s["task_id"])
    if task.exists(): shutil.rmtree(task)
    for d in ("environment", "solution", "tests"): (task / d).mkdir(parents=True, exist_ok=True)
    save(task / "spec.json", s)
    save(ROOT / s["family"].lower() / f"{s['task_id']}.json", s)
    make_public(s, task / "environment" / "inputs.xlsx")
    make_reference(s, task / "solution" / "reference.xlsx")
    common_files(task, s)
    write(task / "instruction.md", instruction(s, instruction_step))
    write(task / "task.toml", task_toml(s))
    return task


def d_steps(base_s, i):
    s1 = base_s
    steps = [s1]
    s2 = copy.deepcopy(s1)
    s2["task_id"] = s1["task_id"] + "_S2"
    s2["step"] = 2
    if i == 1:
        s2["assumptions"]["driver_rebase"] = round(s1["assumptions"]["driver0"] * 1.087, 4)
        s2["assumptions"]["price_rebase"] = round(s1["assumptions"]["price0"] * 1.031, 5)
        event = {"type": "rebase", "description": "新增实际期间经营基数和单位收入，重定预测基期，原历史不变", "driver_rebase": s2["assumptions"]["driver_rebase"], "price_rebase": s2["assumptions"]["price_rebase"]}
    elif i == 2:
        s2["assumptions"]["scenario"] = 2
        event = {"type": "scenario_switch", "description": "董事会批准 Bull 经营方案：需求、利润率、再投资、FCFF、终值和每股价值由同一开关切换", "scenario": 2}
    elif i == 3:
        z = s2["segments"]["segment_beta"]
        z["driver0"] = round(z["driver0"] * .78, 4)
        z["opening_ppe"] = round(z["opening_ppe"] * .73, 4)
        s2["bridge"]["debt"] = round(s1["bridge"]["debt"] * .84, 4)
        s2["bridge"]["valuation_cash_adjustment"] += 37.5
        event = {"type": "disposal", "description": "剥离 Beta 分部的一个区域经营单元，收入基数、资产和债务同步移除；处置净现金进入股权桥", "segment": "segment_beta"}
    else:
        p = s2["projects"]["project_boreal"]
        p["commissioning_period"] = 4
        p["construction_capex"] = [0, 48, 42, 0, 0, 0][:s1["horizon"]]
        event = {"type": "commissioning_and_capex_rearrangement", "description": "Boreal 延后一个期间投产，建设支出移至 P2/P3；投产前仍无收入", "project": "project_boreal"}
    steps.append(s2)
    s3 = copy.deepcopy(s2)
    s3["task_id"] = s1["task_id"] + "_S3"
    s3["step"] = 3
    if s1["c_structure"] == "segment_sotp":
        s3["segments"]["segment_gamma"] = copy.deepcopy(s2["segments"]["segment_alpha"])
        s3["segments"]["segment_gamma"].update(driver0=58, price0=11.4, opening_nwc=23, opening_ppe=67, wacc_delta=.005, method="exit")
        s3["bridge"]["debt"] += 85
        s3["bridge"]["valuation_cash_adjustment"] -= 45
        event3 = {"type": "acquisition", "description": "收购 Gamma 独立分部并以其自身驱动、利润率、再投资和退出倍数估值；净债务与现金调整只在公司层一次", "segment": "segment_gamma"}
    elif s1["c_structure"] == "risk_adjusted_pipeline":
        p = s3["projects"]["project_boreal"]
        # Recompute project truth from changed construction and commissioning assumptions.
        p["project_revenue"] = [x * .83 for x in p["project_revenue"]]
        event3 = {"type": "project_capex_and_scope_revision", "description": "项目规模重排，收入与建设开支按本步事件输入更新，概率继续作用于项目现金流", "project": "project_boreal"}
    else:
        s3["assumptions"]["extra_capex"] = [66, 24, 0, 0, 0][:s1["horizon"]]
        s3["assumptions"]["new_borrowing"] = [92, 0, 15, 0, 0][:s1["horizon"]]
        s3["assumptions"]["debt_repayment"] = [0, 14, 22, 28, 34][:s1["horizon"]]
        event3 = {"type": "financing_and_capex_rearrangement", "description": "扩产支出重排并新增/偿还借款；固定资产和债务滚动同步更新，FCFF 与利息分开", "extra_capex": s3["assumptions"]["extra_capex"]}
    steps.append(s3)
    s4 = copy.deepcopy(s3)
    s4["task_id"] = s1["task_id"] + "_S4"
    s4["step"] = 4
    if s4["c_structure"] == "scenario_operating_model":
        s4["c_structure"] = "multi_method"
        s4["assumptions"]["driver0"] *= 1.065
        s4["assumptions"]["price0"] *= .975
        s4["assumptions"]["scenario"] = 1
        s4["enabled_modules"] = [m for m in s4["enabled_modules"] if m != "scenario"]
        s4["b_items"] = [x for x in s4["b_items"] if x != "dual_terminal"]
        s4["b_item_definitions"] = {k: B[k] for k in s4["b_items"]}
        event4 = {"type": "terminal_method_change", "description": "不再使用情景加权终值；分别输出 Gordon 与退出估值，反推隐含倍数、g 和市场隐含 WACC"}
    elif s4["c_structure"] == "multi_method":
        s4["assumptions"]["exit_multiple"] *= 1.075
        event4 = {"type": "terminal_method_change", "description": "退出估值改为新的可比交易倍数，保留 Gordon 路径用于对照并更新反推", "exit_multiple": s4["assumptions"]["exit_multiple"]}
    else:
        s4["nwc_opening_basis"] = "last_fiscal_year_end"
        s4["opening_nwc_valuation_date"] = s4["opening_nwc"]
        s4["opening_nwc_last_fye"] = round(s4["opening_nwc"] * .93 + 4, 5)
        s4["opening_nwc"] = s4["opening_nwc_last_fye"]
        event4 = {"type": "nwc_opening_basis_change", "description": "从本步起，首期 ΔNWC 改用最近财年末余额，保留估值日 NWC 事实用于勾稽", "opening_nwc_last_fye": s4["opening_nwc_last_fye"]}
    steps.append(s4)
    for n, s in enumerate(steps, 1):
        s["step"] = n
        s["event_public_facts"] = {"type": "baseline", "description": "建立基座模型，保存第 1 步快照。"} if n == 1 else event if n == 2 else event3 if n == 3 else event4
        s["event_type"] = s["event_public_facts"]["type"]
    return steps


def build_d(i):
    c, bitems = DPLAN[f"D{i:02d}"]
    s = choose_bc(f"D{i:02d}", i + 20, c, bitems, "D")
    # Independently change frozen facts and time origin rather than reusing any BC dataset.
    s["company"] = DCOMPANIES[i - 1]
    for j, row in enumerate(s["history"]):
        for key in ("revenue", "ebit", "operating_cost_ex_sbc", "sbc", "nonrecurring_gain"):
            if key in row: row[key] = round(row[key] * (1.31 + .07 * i) + j * .37, 6)
    s["assumptions"]["driver0"] += 18.7 * i
    s["assumptions"]["price0"] *= 1.11 + i * .013
    steps = d_steps(s, i)
    root = ROOT / "tasks" / f"D{i:02d}"
    if root.exists(): shutil.rmtree(root)
    (root / "solution").mkdir(parents=True, exist_ok=True)
    write(root / "instruction.md", instruction(s) + "\n本题包含连续结构事件；按 `steps/step-N/instruction.md` 顺序执行。\n")
    save(root / "spec.json", {**{k: v for k, v in s.items() if k != "step"}, "steps": [{"step": q["step"], "event_type": q["event_type"], "task_id": q["task_id"]} for q in steps], "independent_from_BC": True})
    save(ROOT / "d" / f"D{i:02d}.json", json.loads((root / "spec.json").read_text()))
    write(root / "task.toml", task_toml(s, len(steps)))
    for q in steps:
        n = q["step"]
        step = root / "steps" / f"step-{n}"
        build_one(q, step, n)
        (step / "task.toml").unlink()
        write(step / "solution" / "snapshot.sh", f'#!/bin/bash\nset -euo pipefail\nmkdir -p /app/snapshots\ncp "$(dirname "$0")/reference.xlsx" /app/output.xlsx\ncp "$(dirname "$0")/reference.xlsx" /app/snapshots/step-{n}.xlsx\n', True)
        test_path = step / "tests" / "test.sh"
        test_path.write_text(test_path.read_text().replace("python3 /tests/grader.py", f"python3 /tests/grader.py --step {n}"), encoding="utf-8")
        if n > 1:
            previous = steps[n - 2]
            event = {"step": n, **q["event_public_facts"], "instructions": "只重连本步事件影响的依赖；原始历史与前步快照不可改写", "previous_state": public_view(previous), "new_inputs": public_view(q)}
            save(step / "environment" / "event.json", event)
            shutil.copy2(step / "environment" / "inputs.xlsx", step / "environment" / "event_inputs.xlsx")
            shutil.copy2(step / "environment" / "inputs.json", step / "environment" / "event_inputs.json")
            shutil.copy2(root / "steps" / f"step-{n-1}" / "solution" / "reference.xlsx", step / "solution" / "prior_state.xlsx")
        shutil.copy2(step / "solution" / "reference.xlsx", root / "solution" / f"step-{n}.xlsx")
    save(root / "tests" / "expected.json", {"final_step": len(steps), "baseline": compute(steps[-1]), "perturbations": expected(steps[-1])["perturbations"], "steps": [{"step": q["step"], "expected": compute(q)} for q in steps]})
    return root


def generate(tasks=None):
    wanted = set(tasks or PLAN)
    for tid, (c, b) in PLAN.items():
        if tid not in wanted: continue
        build_one(choose_bc(tid, int(tid[2:]), c, b))
        print("GENERATED", tid, flush=True)
    if not tasks or any(t.startswith("A") for t in tasks):
        for i, kind in enumerate(INDUSTRIES, 1):
            tid = f"A{i:02d}"
            if tasks and tid not in wanted: continue
            build_one(industry(tid, i, kind))
            print("GENERATED", tid, flush=True)
    if not tasks or any(t.startswith("D") for t in tasks):
        for i in range(1, 5):
            tid = f"D{i:02d}"
            if tasks and tid not in wanted: continue
            build_d(i)
            print("GENERATED", tid, flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", nargs="*")
    a = p.parse_args()
    generate(a.tasks)


if __name__ == "__main__": main()
