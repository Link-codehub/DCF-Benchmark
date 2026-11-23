"""Shared atomic library. Deterministic selection emits task-specific execution plans."""
from __future__ import annotations
import copy, json

CATEGORIES = ["交付与来源完整性", "历史与会计口径", "经营预测", "三表勾稽", "DCF与估值桥",
              "公式与模型工程", "开放假设与模拟", "多步状态与业务重构", "表达与专业可用性"]
CODES = dict(zip(CATEGORIES, ["DEL", "HIS", "OPS", "STA", "DCF", "ENG", "SIM", "MUL", "PRE"]))


def item(id, category, text, applicability, evidence, condition, method="rule", severity="major"):
    return {"id": id, "category": category, "text": text, "applicability": applicability,
            "evidence": evidence, "condition": condition, "weight": 1, "method": method, "severity": severity}


def library():
    rows = []
    def add(code, text, applicable, evidence, condition, method="rule", severity="major"):
        rows.append(item(code, CATEGORIES[int(code[:2]) - 1], text, applicable, evidence, condition, method, severity))
    add("01-FILE", "按要求提交可读取的 Excel 工作簿", "all", "/app/output.xlsx", "file_exists", severity="critical")
    add("01-KEYS", "每一个要求的语义输出键均存在且只有一个数值", "all", "Outputs 或语义键映射", "required_keys")
    add("01-UNIT", "金额、股数与比率的单位在提交中明确", "all", "工作簿表头与单位标签", "units_documented", "agent")
    add("01-HISTORY", "原始历史事实未被覆盖或删除", "D 后续步骤", "历史原始事实页", "immutable_history")
    add("02-FY", "完整财年历史收入与规范化 EBIT 来自正确期间聚合", "subannual history", "历史聚合与原始期间", "historical_fy")
    add("02-LTM", "LTM 恰包含要求的季度或半年，未重复年化", "subannual history", "历史聚合与估值日", "historical_ltm")
    add("02-REPORTED", "非经常收益未混入规范化经营 EBIT", "normalization", "历史披露与调整", "historical_reported")
    add("02-SBC", "股份支付作为经营成本处理且未在 FCFF 中加回", "SBC", "历史成本与 FCFF 依赖", "numeric_sbc")
    add("02-COLLECT", "现金收款等于确认收入加合同负债增加", "deferred revenue", "现金收款与递延收入", "cash_collections")
    add("03-DRIVER", "期末经营基数等于期初减流失加新增", "queue driver", "经营预测期", "operating_driver")
    add("03-AVERAGE", "收入采用平均经营基数乘以单位收入及期间活动比例", "queue driver", "收入预测", "operating_average")
    add("03-MARGIN", "各期 EBIT 使用本期的分部或核心利润率", "all", "EBIT 预测", "operating_ebit")
    add("03-CAPEX", "资本开支同时包含强度部分与重排新增部分", "capex queue", "资本开支预测", "capex")
    add("03-NWC", "营运资本变动使用正确期初、期末与符号", "all", "营运资本表", "delta_nwc")
    add("03-DAYS", "应收、存货与应付使用实际年度天数口径", "NWC days", "营运资本表", "numeric_days")
    add("03-DEBT", "借款、偿还、利息和期末债务连续滚动", "debt", "债务表", "debt_roll")
    add("03-LEASE", "使用权资产与租赁负债的口径一致", "leases", "租赁滚动与股权桥", "lease")
    add("03-NOL", "NOL 使用不得超过正 EBIT 或可用余额", "NOL", "税务滚动", "nol")
    add("04-BALANCE", "每个预测期资产等于负债加权益", "three statements", "资产负债表", "balance")
    add("04-CASH", "资产负债表现金与现金流量表期末现金一致", "three statements", "现金流量表", "cash_link")
    add("04-RE", "留存收益由净利润滚动且无不透明平衡项", "three statements", "权益滚动", "retained")
    add("04-PPE", "长期资产由期初加新增减折旧摊销滚动", "rolling assets", "资产表", "ppe_roll")
    add("05-FCFF", "FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加", "all", "FCFF 表", "fcff")
    add("05-WACC", "WACC 使用 CAPM 再杠杆和税后债务成本", "CAPM", "折现率计算", "wacc")
    add("05-DF", "折现期从估值日按实际天数计量并遵守年中约定", "all", "折现时间表", "discount_factor")
    add("05-DUAL", "Gordon 与退出终值分别计算再按权重合成", "dual terminal", "终值计算", "dual_terminal")
    add("05-TV", "终值以最后完整年度为时点且以 WACC 折现", "all", "终值现值", "terminal")
    add("05-BRIDGE", "企业价值桥包含全部现金、投资、债务、租赁和少数股权", "all", "股权桥", "equity")
    add("05-DILUTION", "库存股法增量与 RSU 均进入稀释股数", "dilution", "股数桥", "diluted_shares")
    add("05-VPS", "每股价值以股权价值除以稀释股数", "all", "估值结果", "value_per_share")
    add("05-SENS", "敏感性单元格使用各自行列假设而经营预测不变", "sensitivity", "敏感性网格", "sensitivity")
    add("05-SCENARIO", "经营情景切换同时影响需求和利润率并传递至价值", "scenario", "情景结果", "scenario")
    add("06-FORMULA", "每个要求的结果单元格为活公式而非粘贴数值", "all", "结果单元格 XML/openpyxl", "formula", severity="critical")
    add("06-RECALC", "LibreOffice 重算后结果与独立真值一致", "all", "重算后的候选与 expected", "baseline", severity="critical")
    add("06-PERTURB1", "第一组经营及估值/桥接扰动按依赖传导", "all", "隐藏扰动一", "perturbation_1", severity="critical")
    add("06-PERTURB2", "第二组经营及估值/桥接扰动按依赖传导", "all", "隐藏扰动二", "perturbation_2", severity="critical")
    add("06-LINKS", "无外部工作簿链接或公式错误值", "all", "重算工作簿", "links_errors", severity="critical")
    add("06-FREE", "自由布局通过语义键发现而非行号评分", "free_layout/mixed", "工作簿语义映射", "layout_routing")
    add("07-ASSUME", "开放假设有可追溯的证据和适用日期", "open assumptions", "假设说明", "assumption_evidence", "llm")
    add("07-PATHS", "模拟路径满足数量、抽样和相关性约束", "Monte Carlo", "模拟试验", "simulation_paths")
    add("07-QUANTILE", "模拟分位数由试验样本独立计算", "Monte Carlo", "模拟摘要", "simulation_quantiles")
    add("08-OLD", "后续工作簿保留事件前原始输入与状态", "multi-step", "历史/前步状态", "old_state")
    add("08-REBASE", "新实际值重定基期而非覆盖历史", "rebase event", "重定基期行", "rebase")
    add("08-DISPOSE", "处置后的收入、资产、债务同步移除", "disposal event", "事件重述", "disposal")
    add("08-REFINANCE", "融资和资本开支事件同时更新对应滚动表", "financing/capex event", "事件后预测", "refinance")
    add("08-RESTATE", "事件后的 FCFF 与股权桥使用更新后的依赖", "multi-step", "事件后估值", "post_event")
    add("09-MEMO", "提交 memo.md，说明最重要的价值驱动与至少一个局限", "all", "memo.md 说明文字", "memo_drivers", "llm", "minor")
    add("09-READABLE", "中间结构有明确期间与项目标签且不依赖未披露技巧", "all", "工作簿布局", "readability", "agent", "minor")
    return rows


def select(s, expected_keys):
    selected = []
    def applicable(row):
        app = row["applicability"]
        if app == "all": return True
        if app == "subannual history": return s["time_axis"]["history_frequency"] in ("quarterly", "semiannual")
        if app == "normalization": return s["accounting"]["normalized_history"]
        if app == "SBC": return "sbc" in s["enabled_modules"]
        if app == "deferred revenue": return "deferred_revenue" in s["enabled_modules"]
        if app == "queue driver": return s["business"]["driver"] != "volume_price"
        if app == "capex queue": return "extra_capex" in s["assumptions"]
        if app == "NWC days": return "nwc_days" in s["enabled_modules"]
        if app == "debt": return "debt_schedule" in s["enabled_modules"]
        if app == "leases": return "leases" in s["enabled_modules"]
        if app == "NOL": return "nol" in s["enabled_modules"]
        if app == "three statements": return "three_statements" in s["enabled_modules"]
        if app == "rolling assets": return "rolling_assets" in s["enabled_modules"] or "leases" in s["enabled_modules"]
        if app == "CAPM": return "capm" in s["enabled_modules"]
        if app == "dual terminal": return "dual_terminal" in s["enabled_modules"]
        if app == "dilution": return "dilution" in s["enabled_modules"]
        if app == "sensitivity": return "valuation_sensitivity" in s["enabled_modules"]
        if app == "scenario": return "scenario" in s["enabled_modules"]
        if app == "free_layout/mixed": return s["output"]["template"] in ("free_layout", "mixed")
        if app == "D 后续步骤": return s["family"] == "D" and s.get("step", 1) > 1
        if app == "multi-step": return s["family"] == "D" and s.get("step", 1) > 1
        if app == "rebase event": return s.get("event_type") == "rebase"
        if app == "disposal event": return s.get("event_type") == "disposal"
        if app == "financing/capex event": return s.get("event_type") == "financing"
        if app == "open assumptions": return "open_assumptions" in s["enabled_modules"]
        if app == "Monte Carlo": return "monte_carlo" in s["enabled_modules"]
        return False
    for row in library():
        if applicable(row):
            row = copy.deepcopy(row)
            if row["method"] == "rule":
                if row["condition"].startswith("historical_"):
                    keys = [k for k in expected_keys if k.startswith(row["condition"].split("_")[1] + "_")]
                    if row["condition"] == "historical_reported": keys = ["fy_reported_ebit", "ltm_reported_ebit"]
                    row["check"] = {"kind": "numeric", "keys": keys}
                elif row["condition"] in ("cash_collections", "capex", "delta_nwc", "debt_roll", "nol", "fcff", "discount_factor", "equity", "diluted_shares", "value_per_share", "lease"):
                    keymap = {"cash_collections": ["cash_collections"], "capex": ["capex"], "delta_nwc": ["delta_nwc"],
                        "debt_roll": ["debt_close", "interest"], "nol": ["nol_close", "tax"], "fcff": ["fcff"],
                        "discount_factor": ["discount_factor"], "equity": ["equity_value"], "diluted_shares": ["diluted_shares"], "value_per_share": ["value_per_share"],
                        "lease": ["rou_close", "rou_amortization"]}
                    row["check"] = {"kind": "numeric_prefix", "prefixes": keymap[row["condition"]]}
                elif row["condition"].startswith("operating_"):
                    prefix = {"operating_driver": "driver_close", "operating_average": "average_driver", "operating_ebit": "ebit"}[row["condition"]]
                    row["check"] = {"kind": "numeric_prefix", "prefixes": [prefix]}
                elif row["condition"] == "wacc": row["check"] = {"kind": "numeric", "keys": ["levered_beta", "cost_of_equity", "wacc"]}
                elif row["condition"] == "dual_terminal": row["check"] = {"kind": "numeric", "keys": ["tv_gordon", "tv_exit", "terminal_value"]}
                elif row["condition"] == "terminal": row["check"] = {"kind": "numeric", "keys": ["terminal_value", "pv_terminal"]}
                elif row["condition"] in ("balance", "cash_link", "retained", "ppe_roll"):
                    prefix = {"balance": "balance_difference", "cash_link": "cash_link", "retained": "retained_earnings", "ppe_roll": "ppe_close"}[row["condition"]]
                    row["check"] = {"kind": "numeric_prefix", "prefixes": [prefix]}
                elif row["condition"] in ("numeric_sbc", "numeric_days"):
                    row["check"] = {"kind": "numeric", "keys": ["fy_normalized_ebit", "ltm_normalized_ebit"]} if row["condition"] == "numeric_sbc" else {"kind": "numeric_prefix", "prefixes": ["delta_nwc"]}
                elif row["condition"] in ("scenario", "sensitivity"):
                    prefix = "scenario_vps" if row["condition"] == "scenario" else "sens_"
                    row["check"] = {"kind": "numeric_prefix", "prefixes": [prefix]}
                else: row["check"] = {"kind": row["condition"]}
            selected.append(row)
    weights = {"交付与来源完整性": 8, "历史与会计口径": 10, "经营预测": 18, "三表勾稽": 10,
        "DCF与估值桥": 24, "公式与模型工程": 20, "开放假设与模拟": 0, "多步状态与业务重构": 6, "表达与专业可用性": 4}
    if s["family"] == "D": weights["多步状态与业务重构"] = 12; weights["经营预测"] = 15; weights["DCF与估值桥"] = 21
    if not any(r["category"] == "历史与会计口径" for r in selected): weights["历史与会计口径"] = 0
    if not any(r["category"] == "三表勾稽" for r in selected): weights["三表勾稽"] = 0
    if not any(r["category"] == "开放假设与模拟" for r in selected): weights["开放假设与模拟"] = 0
    if not any(r["method"] == "rule" and r["category"] == "多步状态与业务重构" for r in selected): weights["多步状态与业务重构"] = 0
    for r in selected: r["weight"] = weights[r["category"]]
    return selected


def rubric(s, expected):
    criteria = select(s, list(expected))
    weights = {r["category"]: r["weight"] for r in criteria}
    rule_categories = list(dict.fromkeys(r["category"] for r in criteria if r["method"] == "rule"))
    rule_weight = sum(weights[category] for category in rule_categories)
    return {"task_id": s["task_id"], "category_rule": "同一类任一适用原子项失败，该类得分为零；每个类别仅计一次权重，无额外封顶",
        "category_weights": weights,
        "score_range": [0, 100], "rule_score_range": [0, rule_weight],
        "judge_calls": {"llm": "每次仅一个原子项", "agent": "每次同一题一个相关小组", "schema": {"score": "0|1", "evidence": "string"}},
        "judge_input": {"public_instruction": "instruction.md", "candidate": "/app/output.xlsx", "rubric_item": "one item or related group", "expected_numbers": "never sent"},
        "output_mode": s["output"], "criteria": criteria}


def write_library(root):
    rows = library()
    root.mkdir(parents=True, exist_ok=True)
    manifest = {"version": "v2.0", "categories": CATEGORIES, "atomic_count": len(rows), "methods": ["rule", "llm", "agent"]}
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for i, category in enumerate(CATEGORIES, 1):
        (root / f"{i:02d}_{CODES[category]}.json").write_text(json.dumps([r for r in rows if r["category"] == category], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
