#!/usr/bin/env python3
"""DCF Eval v2: constrained multidimensional composition, F24 + D6, fully reproducible."""
import argparse, copy, datetime as dt, hashlib, json, random, shutil, sys
from pathlib import Path
from model import compute
from rubrics import rubric, write_library
from workbook import make_public, make_reference, input_layout

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
SCENES = [
    ("subscription", "企业档案订阅", "千家客户", "百万元/千家客户/年"),
    ("stores", "城市补给门店", "家", "百万元/店/年"),
    ("capacity", "特种涂层产线", "千吨年产能", "百万元/千吨"),
    ("installed_base", "楼宇监测装机服务", "千台", "百万元/台次"),
    ("volume_price", "精密连接组件", "百万件", "百万元/百万件"),
    ("subscription", "远程运维席位", "千席位", "百万元/千席位/年"),
    ("capacity", "区域低温加工", "千吨年产能", "百万元/千吨"),
    ("installed_base", "商用设备巡检", "千台", "百万元/台次"),
]
EVENTS = ["rebase", "disposal", "financing", "rebase", "financing", "disposal"]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_months(value, months):
    index = value.year * 12 + value.month - 1 + months
    year, month = divmod(index, 12)
    days = [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    current = [31, 29 if value.year % 4 == 0 and (value.year % 100 or value.year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = days[month] if value.day == current[value.month - 1] else min(value.day, days[month])
    return dt.date(year, month + 1, day)


def choose_dimensions(index, family, rng):
    if family == "F":
        driver = SCENES[index % len(SCENES)][0]
        frequency = "quarterly" if index % 3 != 1 else "semiannual"
        horizon = 4 + index % 3
        templates = ["fixed_outputs", "free_layout", "mixed"]
        template = templates[index % 3]
        level = 1 + index // 8
        terminal = "dual_terminal" if index % 4 in (0, 3) else "gordon" if index % 4 == 1 else "exit"
    else:
        driver = ["subscription", "capacity", "stores", "installed_base", "volume_price", "capacity"][index]
        frequency = "semiannual" if index % 2 == 0 else "quarterly"
        horizon = 4
        template = ["fixed_outputs", "free_layout", "mixed"][index % 3]
        level = 3
        terminal = "dual_terminal" if index % 2 == 0 else "gordon"
    modules = ["residual_period", "working_capital"]
    if terminal == "dual_terminal": modules += ["dual_terminal"]
    if index % 3 == 0 or family == "D": modules += ["deferred_revenue"]
    if index % 4 >= 2 or family == "D": modules += ["rolling_assets"]
    if index % 4 == 1 or (family == "D" and index % 2): modules += ["nwc_days"]
    if level >= 2 or family == "D": modules += ["debt_schedule"]
    if index % 5 == 2 or family == "D": modules += ["capm"]
    if index % 5 == 0: modules += ["dilution"]
    if index % 6 == 3 or family == "D": modules += ["leases"]
    if level == 3 or family == "D": modules += ["nol"]
    if index % 5 == 4 or family == "D": modules += ["scenario"]
    if index % 4 == 2: modules += ["valuation_sensitivity"]
    outputs = ["dcf_only", "segment_dcf", "debt_schedule_dcf", "three_statements_dcf"]
    output_mode = outputs[(index + 1) % len(outputs)] if family == "F" else "event_restatement_dcf"
    if output_mode == "three_statements_dcf": modules.append("three_statements")
    return {"scenario": SCENES[index % len(SCENES)][1] if family == "F" else "事件驱动" + SCENES[index % len(SCENES)][1],
        "difficulty": f"L{level}: 依赖深度{4 + len(modules) // 2}，显式{horizon}期",
        "time_axis": f"非自然财年+{frequency}历史+实际天数残期", "business_driver": driver,
        "valuation_mechanism": terminal, "accounting_basis": "SBC经营成本" if index % 2 == 0 else "应计无杠杆现金税",
        "output_mode": output_mode, "output_template": template, "data_provision": "complete_frozen"}, modules, horizon


def make_spec(index, seed, family="F", step=1, parent=None):
    if parent is not None:
        s = copy.deepcopy(parent)
        event = EVENTS[index]
        s["task_id"] = f"D{index + 1:02d}_S{step}"; s["step"] = step; s["event_type"] = event
        s["perturbations"] = []
        s["multi_step_events"].append({"step": step, "type": event, "public_input": "新增事件输入，历史原始事实保持不可改写"})
        a = s["assumptions"]
        if event == "rebase":
            a["driver_rebase"] = round(a["driver0"] * 1.09, 6)
            a["price_rebase"] = round(a["price0"] * 1.025, 6)
            months = 6 if s["time_axis"]["history_frequency"] == "semiannual" else 3
            event_end = add_months(dt.date.fromisoformat(s["last_fy_end"]), months)
            event_start = dt.date.fromisoformat(s["last_fy_end"]) + dt.timedelta(days=1)
            actual_revenue = round(a["driver_rebase"] * a["price_rebase"] * months / 12, 6)
            s["event_public_facts"] = {"actual_period": {"start": event_start.isoformat(), "end": event_end.isoformat(), "months": months},
                "actual_revenue": actual_revenue, "actual_driver_close": a["driver_rebase"], "actual_unit_revenue": a["price_rebase"],
                "driver_rebase": a["driver_rebase"], "price_rebase": a["price_rebase"],
                "rule": "Event History新增已实现期；原始History不可改写。预测以新实际经营基数和单位收入重定基期并重述后续预测，不重写历史聚合。"}
            s["multi_step_events"][-1]["actual_period"] = s["event_public_facts"]["actual_period"]
        elif event == "disposal":
            s["enabled_modules"] = list(dict.fromkeys(s["enabled_modules"] + ["segment_disposal"]))
            a["segment_revenue"] = [round(x * .72, 4) for x in a.get("segment_revenue", [75 + index * 9] * s["horizon"])]
            a["segment_margin"] = [0] * s["horizon"]
            a["driver_add"] = [round(x * .9, 4) for x in a["driver_add"]]
            s["opening_ppe"] = round(s["opening_ppe"] * .8, 4)
            s["bridge"]["debt"] = round(s["bridge"]["debt"] * .85, 4)
            s["opening_debt"] = s["bridge"]["debt"]
            disposed_ppe = round(parent["opening_ppe"] - s["opening_ppe"], 4)
            debt_reduction = round(parent["opening_debt"] - s["opening_debt"], 4)
            retained_proceeds = round(disposed_ppe - debt_reduction, 4)
            s["bridge"]["valuation_cash_adjustment"] = round(s["bridge"]["valuation_cash_adjustment"] + retained_proceeds, 6)
            s["opening_cash"] = round(s["opening_cash"] + retained_proceeds, 6)
            s["opening_balance_facts"]["opening_cash"] = s["opening_cash"]
            s["event_public_facts"] = {"disposal": "按被剥离固定资产的账面净值出售辅助业务，不产生处置损益；所得先偿还指定债务，剩余现金留存在估值日现金调整中。其余经营资产、合同负债和期初权益不变，从本步起不再预测被剥离业务的收入和利润", "new_segment_revenue": a["segment_revenue"], "opening_ppe": s["opening_ppe"], "opening_debt": s["opening_debt"], "disposal_proceeds": disposed_ppe, "debt_reduction": debt_reduction, "retained_proceeds": retained_proceeds, "disposal_gain": 0.0}
        else:
            s["enabled_modules"] = list(dict.fromkeys(s["enabled_modules"] + ["financing", "capex_queue"]))
            a["extra_capex"] = [90 + index * 8, 0, -25, 0]
            a["new_borrowing"] = [70 + index * 5, 0, 0, 0]
            a["debt_repayment"] = [15, 25, 30, 35]
            s["event_public_facts"] = {"financing": "首期提款并偿付后续本金；扩产开支重排，第二期的预留支出转为维护支出抵减", "new_borrowing": a["new_borrowing"], "debt_repayment": a["debt_repayment"], "extra_capex": a["extra_capex"]}
        s["dimension_selection"]["output_mode"] = "event_restatement_dcf"
        s["dimension_selection"]["difficulty"] += "+结构事件"
        s["source_and_choice"]["event_source"] = "同一虚拟企业的后续冻结公告，独立于历史记录"
        add_perturbations(s)
        return s
    rng = random.Random(int.from_bytes(hashlib.sha256(f"v2/{family}/{seed}/{index}".encode()).digest()[:8], "big"))
    dims, modules, horizon = choose_dimensions(index, family, rng)
    kind, scene, unit, price_unit = SCENES[index % len(SCENES)]
    if family == "D": kind = ["subscription", "capacity", "stores", "installed_base", "volume_price", "capacity"][index]
    fy = dt.date(2024 + index % 3, [2, 5, 8, 10][index % 4], [28, 31, 31, 31][index % 4])
    val = fy + dt.timedelta(days=72 + (index * 19) % 150)
    step_months = 3 if "quarterly" in dims["time_axis"] else 6
    count = 10 if step_months == 3 else 6
    dates = [fy]
    for _ in range(count): dates.insert(0, add_months(dates[0], -step_months))
    history = []
    for i, end in enumerate(dates[1:]):
        year = end.year if (end.month, end.day) <= (fy.month, fy.day) else end.year + 1
        history.append({"start": (dates[i] + dt.timedelta(days=1)).isoformat(), "end": end.isoformat(), "fiscal_year": str(year)})
    scale = rng.randrange(720, 1250, 17)
    base_driver = 72 + index * 5
    for i, h in enumerate(history):
        annual = scale * (.82 + .022 * i)
        h["revenue"] = round(annual * step_months / 12, 6)
        h["ebit"] = round(h["revenue"] * (.105 + .005 * i), 6)
        h["operating_cost_ex_sbc"] = round(h["revenue"] * (.82 - .004 * i), 6)
        h["sbc"] = round(h["revenue"] * .025, 6)
        h["nonrecurring_gain"] = round(h["revenue"] * (.012 if i == len(history) - 1 else 0), 6)
    a = {"driver0": base_driver, "price0": round(scale / base_driver, 7),
        "driver_add": [round(base_driver * (.08 + .011 * i), 5) for i in range(horizon)],
        "driver_growth": [round(.09 - .009 * i, 6) for i in range(horizon)],
        "attrition_rate": [round(.045 + .005 * i, 6) for i in range(horizon)],
        "price_growth": [round(.03 - .002 * i, 6) for i in range(horizon)],
        "ebit_margin": [round(.16 + .007 * i, 6) for i in range(horizon)],
        "da_pct": [.04 + .002 * (i % 2) for i in range(horizon)],
        "capex_pct": [.061 + .004 * (i % 3) for i in range(horizon)],
        "nwc_pct": [.18 + .006 * (i % 3) for i in range(horizon)],
        "tax": .235, "wacc": .103 + .002 * (index % 4), "g": .022 + .001 * (index % 3),
        "gordon_weight": .55 if "dual_terminal" in modules else 1.0 if dims["valuation_mechanism"] == "gordon" else 0.0,
        "exit_multiple": 7.8 + .3 * (index % 5), "deferred_pct": [.08] * horizon,
        "cogs_ratio": [.48] * horizon, "dso": [47 + i for i in range(horizon)],
        "dio": [62 - i for i in range(horizon)], "dpo": [43 + i for i in range(horizon)],
        "nol0": scale * .11, "ppe_rate": .13, "rou_rate": .2,
        "lease_additions": [scale * .018] * horizon,
        "interest_rate": .052, "new_borrowing": [scale * .025 if i == 0 else 0 for i in range(horizon)],
        "debt_repayment": [scale * .01 * (i + 1) for i in range(horizon)],
        "beta_unlevered": .76 + .04 * (index % 4), "target_de": .27 + .03 * (index % 3),
        "risk_free": .034, "erp": .049, "specific_premium": .006,
        "cost_of_debt": .053, "scenario": 1,
        "upside_demand_delta": .025, "downside_demand_delta": -.025,
        "upside_margin_delta": .012, "downside_margin_delta": -.014,
        "wacc_deltas": [-.01, 0, .01], "g_deltas": [-.005, 0, .005]}
    if kind == "capacity":
        a["utilization"] = [.74 + .018 * i for i in range(horizon)]
        a["price0"] = round(scale / base_driver / .74, 7)
    if kind == "installed_base":
        a["service_frequency"] = [3.2 + .08 * i for i in range(horizon)]
        a["price0"] = round(scale / base_driver / 3.2, 7)
    if dims["output_mode"] == "segment_dcf":
        a["segment_revenue"] = [round(scale * (.08 + .01 * i), 5) for i in range(horizon)]
        a["segment_margin"] = [.07 + .005 * i for i in range(horizon)]
    bridge = {"cash": round(scale * .1, 5), "debt": round(scale * .2, 5), "investments": round(scale * .015, 5),
        "lease_liability": round(scale * .065, 5) if "leases" in modules else 0.0,
        "minority": round(scale * .012, 5), "valuation_cash_adjustment": round(scale * .1 * .12, 5), "shares": 110 + index * 3, "rsus": 2.4,
        "options": 6.0, "strike": 7.0, "share_price": 11.0 + index * .3}
    s = {"schema_version": "v2.0", "task_id": f"{family}{index + 1:02d}" + (f"_S{step}" if family == "D" else ""),
        "seed": seed, "candidate_index": index, "family": family, "step": step, "company": scene,
        "dimension_selection": dims, "enabled_modules": modules,
        "selection_rationale": {"scenario": f"{scene}要求独立的单位与价格口径", "time_axis": f"{count}个{'季度' if step_months == 3 else '半年'}披露期，需聚合财年/LTM并处理残期",
            "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率", "valuation_mechanism": "终值与折现时点依赖显式预测",
            "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一", "output_template": "固定坐标、语义发现或两者分流"},
        "source_and_choice": {"source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设", "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"},
        "time_axis": {"history_frequency": "quarterly" if step_months == 3 else "semiannual", "midyear": index % 2 == 0, "day_count": "actual/365", "terminal_at_last_fye": True},
        "accounting": {"normalized_history": True, "sbc_expense": True, "lease_in_debt": "leases" in modules},
        "business": {"driver": kind, "unit": unit, "price_unit": price_unit, "description": scene},
        "output": {"mode": dims["output_mode"], "template": dims["output_template"], "fixed_sheet": "Outputs"},
        "valuation_date": val.isoformat(), "last_fy_end": fy.isoformat(), "horizon": horizon, "history": history,
        "opening_nwc": 0.0, "opening_deferred": round(scale * .075, 6),
        "opening_ppe": round(scale * .31, 6), "opening_rou": round(scale * .08, 6),
        "opening_debt": bridge["debt"], "opening_retained_earnings": round(scale * .16, 6), "contributed_capital": round(scale * .39, 6),
        "opening_cash": bridge["cash"], "opening_sbc_reserve": 0.0,
        "assumptions": a, "bridge": bridge, "multi_step_events": [], "perturbations": [],
        "constraints": {"money_unit": "百万元", "share_unit": "百万股", "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
            "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
            "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
            "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
            "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
            "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
            "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
            "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
            "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
            "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"}}
    if "deferred_revenue" not in modules: s["opening_deferred"] = 0.0
    if "leases" not in modules: s["opening_rou"] = 0.0
    s["opening_operating_current_assets"] = round(s["opening_debt"] + bridge["lease_liability"] + s["opening_deferred"] + s["opening_retained_earnings"] + s["contributed_capital"] + bridge["minority"] + s["opening_sbc_reserve"] - s["opening_cash"] - bridge["investments"] - s["opening_ppe"] - s["opening_rou"], 6)
    s["opening_nwc"] = round(s["opening_operating_current_assets"] - s["opening_deferred"], 6)
    s["opening_balance_facts"] = {"basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
        "contributed_capital": s["contributed_capital"], "opening_cash": s["opening_cash"], "opening_operating_current_assets": s["opening_operating_current_assets"], "opening_sbc_reserve": 0.0}
    a["sbc_pct"] = [.025] * horizon
    add_perturbations(s)
    if family == "D":
        s["multi_step_events"] = [{"step": 1, "type": "baseline", "public_input": "原始经营、历史与估值输入"}]
    return s


def add_perturbations(s):
    a = s["assumptions"]
    op1 = "driver_add" if s["business"]["driver"] != "volume_price" else "driver_growth"
    changes1 = {f"a.{op1}.0": 1.14, "a.ebit_margin.1": 1.06, "a.wacc" if "capm" not in s["enabled_modules"] else "a.erp": 1.045, "b.valuation_cash_adjustment": 1.12}
    op2 = "utilization" if s["business"]["driver"] == "capacity" else "service_frequency" if s["business"]["driver"] == "installed_base" else "price_growth"
    changes2 = {f"a.{op2}.1": 1.035, "a.capex_pct.2": 1.15, "a.g": .93, "b.debt": 1.09}
    for label, changes in (("operating_wacc_bridge", changes1), ("operating_reinvestment_terminal_bridge", changes2)):
        p = copy.deepcopy(s); p["perturbations"] = []
        for key, factor in changes.items():
            parts = key.split("."); target = p
            for part in parts[:-1]:
                if part == "a": part = "assumptions"
                elif part == "b": part = "bridge"
                target = target[part]
            leaf = parts[-1]
            if leaf.isdigit(): target[int(leaf)] *= factor
            else: target[leaf] *= factor
        p["perturbation_label"] = label
        p["perturbation_input_changes"] = changes
        s["perturbations"].append(p)


def instruction(s, native_step=False):
    output = s["output"]
    if output["template"] == "fixed_outputs":
        layout = "在 `Outputs` 页以 A 列键名、同行 B 列公式提交结果；中间模型自由。"
    elif output["template"] == "free_layout":
        layout = "在以 `Results` 开头的结果页，以语义键名标签加右邻或下邻公式提交结果；不指定行号。每个键只能有一个有效输出。"
    else:
        layout = "历史与估值标量在 `Outputs` A/B 列；期间项、情景与敏感性项在以 `Results` 开头的结果页按键名标签加右邻或下邻公式提交。"
    drivers = {
        "subscription": "结合客户新增、流失和定价，构建订阅客户经营预测；不得把期末客户数直接当作全期平均。",
        "stores": "结合门店开关店节奏与店均收入构建经营预测；开关店在期内产生的收入贡献需要合理处理。",
        "capacity": "结合投产队列、产能利用率与加工价格构建预测；未投产产能不能提前贡献收入。",
        "installed_base": "结合装机留存、服务频次与单次服务价格构建预测；装机量与服务工作量不能混同。",
        "volume_price": "分部预测销量与单价，体现价格和销量的不同变化路径。",
    }
    goals = [drivers[s["business"]["driver"]]]
    if "deferred_revenue" in s["enabled_modules"]:
        goals.append("区分订阅/服务收入确认与合同负债、现金收款及营运资本；采用Inputs提供的deferred_pct口径。")
    if "nwc_days" in s["enabled_modules"]:
        goals.append("用公开的应收、存货和应付天数假设构建营运资本，并说明期间变动的现金影响。")
    if "rolling_assets" in s["enabled_modules"] or "leases" in s["enabled_modules"]:
        goals.append("用资产滚动支持资本开支、折旧摊销与再投资；新增资产按当期半期计提约定处理。")
    if "debt_schedule" in s["enabled_modules"]:
        goals.append("建立借款、偿还与利息的滚动表，并保持无杠杆现金流与融资流分离。")
    if "capm" in s["enabled_modules"]:
        goals.append("根据给定的风险参数和目标资本结构推导WACC，清晰展示beta再杠杆过程。")
    if "three_statements" in s["enabled_modules"]:
        goals.append("提供相互勾稽的预测利润、现金、资产与权益；现金衔接和留存收益必须可追溯，不允许不透明plug。SBC为非现金费用，CFO加回并计权益储备，FCFF不加回；区分利息后现金税与FCFF无杠杆现金税，合同负债在净营运资本中只计一次。")
    if "scenario" in s["enabled_modules"]:
        goals.append("提供基准、乐观、悲观三种经营情景及其估值结果，情景由Inputs中的选择和差异假设驱动。")
    if "valuation_sensitivity" in s["enabled_modules"]:
        goals.append("给出WACC与永续增长率变化下的每股价值敏感性；经营预测不应因估值敏感性而重造。")
    if "dual_terminal" in s["enabled_modules"]:
        goals.append("分别展示永续增长与退出倍数终值，再按gordon_weight合成。")
    if s["family"] == "D" and s["step"] > 1:
        goals.append("读取本步新事件，重连受影响的经营、资产/融资与估值依赖；不得修改原始History或把前步公式替换为静态数。开始修改前先把未改动的前步工作簿另存为 `/app/pre_step_output.xlsx`，然后更新 `/app/output.xlsx`；不得用答案文件替代该快照。")
    action = "修改现有的 `/app/output.xlsx`，保留前步模型和原始历史，读取本步 `/app/event.json` 与 `/app/event_inputs.xlsx`。" if native_step and s["step"] > 1 else "根据 `/app/inputs.xlsx` 和 `/app/inputs.json` 建立公式驱动的模型，保存为 `/app/output.xlsx`。"
    return f"""# {s['task_id']}｜{s['company']} 经营预测与估值

你是估值分析师。{action}禁止网络与外部链接。

## 业务与时间范围
- 场景：{s['business']['description']}；经营单位：{s['business']['unit']}；收入单价口径：{s['business']['price_unit']}。
- 估值日 `{s['valuation_date']}`，最近完整财年末 `{s['last_fy_end']}`，显式预测 `{s['horizon']}` 期；原始历史为{s['time_axis']['history_frequency']}披露期。
- 汇总最近完整财年与截至估值日的LTM。金额百万元、股数百万股、比率小数。SBC计入经营成本；非经常收益不属于规范化经营EBIT。
- 首个预测段只包含估值日后经营活动，采用实际天数/365及{'年中' if s['time_axis']['midyear'] else '期末'}折现惯例；终值位于最后完整财年末。余额型营运资本仍使用完整年度经营驱动；首期变化为首个期末余额减估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额。

## 建模目标
{chr(10).join('- ' + goal for goal in goals)}
- 从EBIT、现金税、折旧摊销、再投资及营运资本变化构建无杠杆FCFF，再折现、计算终值并完成EV到稀释每股价值的桥接。债务、租赁及少数股权的口径见Inputs。

## 输出与可审计性
{layout}
要求的键见 `/app/inputs.json` 的 `public_output_keys` 及公开键清单。另提交 `/app/memo.md`，简述最重要的价值驱动和至少一个模型局限。保留公开 `Inputs` 页语义键与 C/D/E… 的 P1/P2… 向量，预测、历史聚合和估值须由这些输入的活公式计算。不得粘贴完整数值模型代替公式。LibreOffice重算与隐藏输入扰动将用于检查依赖传导。
"""

def public_view(s):
    result = copy.deepcopy(s)
    result.pop("perturbations", None)
    result["public_output_keys"] = list(compute(s))
    return result


def write_hidden_bundle(s, public, task):
    expected = {"baseline": compute(s), "perturbations": [], "input_layout": input_layout(s)}
    for p in s["perturbations"]:
        changes = {}
        for key, factor in p["perturbation_input_changes"].items():
            parts = key.split("."); target = s
            for part in parts[:-1]: target = target[{"a": "assumptions", "b": "bridge"}.get(part, part)]
            leaf = parts[-1]
            original = target[int(leaf)] if leaf.isdigit() else target[leaf]
            changes[key] = original * factor
        expected["perturbations"].append({"label": p["perturbation_label"], "input_changes": changes, "expected": compute(p)})
    if s["family"] == "D" and s["step"] > 1:
        prior_path = ROOT / "specs" / f"{s['task_id'][:3]}_S1.json"
        if not prior_path.is_file():
            raise FileNotFoundError(f"missing frozen step-one specification: {prior_path}")
        expected["prior_baseline"] = compute(json.loads(prior_path.read_text()))
    save(task / "tests" / "expected.json", expected)
    save(task / "tests" / "grader_spec.json", s)
    save(task / "tests" / "original_history.json", s["history"])
    save(task / "tests" / "public_history_contract.json", {"history": public["history"]})
    rb = rubric(s, expected["baseline"])
    save(task / "rubric.json", rb)
    (task / "solution" / "memo.md").write_text(f"# {s['task_id']} 参考说明\n\n价值驱动：{s['business']['description']}的经营基数、单位收入、利润率、再投资、折现率和终值假设共同影响估值。\n\n局限：这是冻结假设下的机械参考实现，不是市场预测或投资建议；未对经营假设做开放性实证校准。\n", encoding="utf-8")
    save(task / "tests" / "rubric.json", rb)
    for name in ("grader.py", "workbook.py", "model.py"): shutil.copy2(ROOT / name, task / "tests" / name)


def build(s, metadata_only=False):
    tid = s["task_id"]
    relative = Path(tid[:3]) / f"S{s['step']}" if s["family"] == "D" else Path(tid)
    task = BASE / "tasks" / relative
    if task.exists() and not metadata_only: shutil.rmtree(task)
    for folder in ("environment", "solution", "tests"): (task / folder).mkdir(parents=True, exist_ok=True)
    save(ROOT / "specs" / f"{tid}.json", s)
    public = public_view(s)
    save(task / "environment" / "inputs.json", public)
    if metadata_only: save(task / "tests" / "grader_spec.json", s)
    if s["family"] == "D" and s["step"] > 1:
        save(task / "environment" / "event.json", s["event_public_facts"])
        prior = task.parent / "S1" / "solution" / "reference.xlsx"
        if not metadata_only: shutil.copy2(prior, task / "solution" / "prior_state.xlsx")
    if not metadata_only:
        make_public(s, task / "environment" / "inputs.xlsx")
        make_reference(s, task / "solution" / "reference.xlsx")
        write_hidden_bundle(s, public, task)
        if s["family"] == "D" and s["step"] > 1: shutil.copy2(task / "solution" / "prior_state.xlsx", task / "tests" / "prior_state.xlsx")
    (task / "instruction.md").write_text(instruction(s), encoding="utf-8")
    (task / "task.toml").write_text(f'''schema_version = "1.4"
artifacts = ["/app/output.xlsx", "/app/memo.md"]
[task]
name = "dcf-v2/{tid.lower()}"
version = "2.0.0"
description = "Multidimensional DCF with independent expected and live-formula reference"
authors = []
keywords = ["DCF", "multidimensional", "LibreOffice", "semantic-rubric"]
[metadata]
difficulty = "hard"
category = "finance"
tags = ["dcf-v2", "{s['business']['driver']}", "{s['output']['template']}"]
[environment]
network_mode = "no-network"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 4096
gpus = 0
mcp_servers = []
[agent]
timeout_sec = 2400.0
disable_web_search = true
network_mode = "allowlist"
allowed_hosts = ["host.docker.internal"]
[verifier]
timeout_sec = 600.0
environment_mode = "shared"
[environment.env]
[verifier.env]
[solution.env]
''', encoding="utf-8")
    files = ["inputs.xlsx", "inputs.json"] + (["event.json"] if s["family"] == "D" and s["step"] > 1 else [])
    (task / "environment" / "Dockerfile").write_text("FROM dcfbench-agent:v1\nWORKDIR /app\nCOPY " + " ".join(files) + " /app/\n", encoding="utf-8")
    (task / "environment" / "docker-compose.yaml").write_text('''services:
  dcf-egress-firewall:
    image: dcf-ipv4-gost-egress:v1
    entrypoint: ["/opt/egress-sidecar/entrypoint.sh"]
    environment:
      EGRESS_CONTROL_INITIAL_NETWORK_MODE: no-network
      EGRESS_CONTROL_INITIAL_ALLOWED_HOSTS: host.docker.internal
    init: true
    cap_add: [NET_ADMIN, NET_RAW]
    healthcheck:
      test: ["CMD", "test", "-f", "/tmp/dcf-egress-ready"]
      interval: 1s
      timeout: 5s
      retries: 30
  main:
    network_mode: service:dcf-egress-firewall
    depends_on:
      dcf-egress-firewall:
        condition: service_healthy
''', encoding="utf-8")
    script(task / "solution" / "solve.sh", '#!/bin/bash\nset -euo pipefail\ncp "$(dirname "$0")/reference.xlsx" /app/output.xlsx\ncp "$(dirname "$0")/memo.md" /app/memo.md\n')
    script(task / "tests" / "test.sh", '#!/bin/bash\nset -u\nmkdir -p /logs/verifier\npython3 /tests/grader.py --task-dir /tests --report /logs/verifier/report.json\nexit 0\n')
    for name in ("grader.py", "workbook.py", "model.py"): shutil.copy2(ROOT / name, task / "tests" / name)
    return task


def build_native_multistep(base, second, metadata_only=False):
    root = BASE / "tasks" / base["task_id"][:3]
    if metadata_only:
        for number, s in ((1, base), (2, second)):
            step = root / "steps" / f"step-{number}"
            (step / "instruction.md").write_text(instruction(s, native_step=True), encoding="utf-8")
            save(step / "tests" / "grader_spec.json", s)
            public = public_view(s)
            if number == 1: save(root / "environment" / "inputs.json", public)
            else: save(step / "workdir" / "event_inputs.json", public)
        return
    for step in (1, 2):
        legacy = ROOT / "legacy_steps" / f"{base['task_id'][:3]}_S{step}"
        if (root / f"S{step}").exists():
            if legacy.exists(): shutil.rmtree(legacy)
            shutil.move(str(root / f"S{step}"), str(legacy))
    for folder in ("steps", "environment", "task.toml"):
        target = root / folder
        if target.is_dir(): shutil.rmtree(target)
        elif target.exists(): target.unlink()
    (root / "environment").mkdir(parents=True, exist_ok=True)
    (root / "steps" / "step-1").mkdir(parents=True, exist_ok=True)
    (root / "steps" / "step-2").mkdir(parents=True, exist_ok=True)
    for file in ("inputs.xlsx", "inputs.json"):
        shutil.copy2(ROOT / "legacy_steps" / f"{base['task_id'][:3]}_S1" / "environment" / file, root / "environment" / file)
    (root / "environment" / "Dockerfile").write_text("FROM dcfbench-agent:v1\nWORKDIR /app\nCOPY inputs.xlsx inputs.json /app/\n", encoding="utf-8")
    (root / "environment" / "docker-compose.yaml").write_text('''services:
  dcf-egress-firewall:
    image: dcf-ipv4-gost-egress:v1
    entrypoint: ["/opt/egress-sidecar/entrypoint.sh"]
    environment:
      EGRESS_CONTROL_INITIAL_NETWORK_MODE: no-network
      EGRESS_CONTROL_INITIAL_ALLOWED_HOSTS: host.docker.internal
    init: true
    cap_add: [NET_ADMIN, NET_RAW]
    healthcheck:
      test: ["CMD", "test", "-f", "/tmp/dcf-egress-ready"]
      interval: 1s
      timeout: 5s
      retries: 30
  main:
    network_mode: service:dcf-egress-firewall
    depends_on:
      dcf-egress-firewall:
        condition: service_healthy
''', encoding="utf-8")
    (root / "task.toml").write_text(f'''schema_version = "1.4"
artifacts = ["/app/output.xlsx", "/app/memo.md"]
multi_step_reward_strategy = "mean"
[task]
name = "dcf-v2/{base['task_id'][:3].lower()}"
version = "2.0.0"
description = "Native Harbor multi-step DCF with persistent live formulas and structural event"
authors = []
keywords = ["DCF", "multi-step", "persistent-environment"]
[metadata]
difficulty = "hard"
category = "finance"
[environment]
network_mode = "no-network"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 4096
gpus = 0
mcp_servers = []
workdir = "/app"
[agent]
timeout_sec = 2400.0
disable_web_search = true
network_mode = "allowlist"
allowed_hosts = ["host.docker.internal"]
[verifier]
timeout_sec = 600.0
environment_mode = "shared"
[environment.env]
[verifier.env]
[solution.env]
[[steps]]
name = "step-1"
[steps.verifier]
timeout_sec = 600.0
[[steps]]
name = "step-2"
[steps.healthcheck]
command = "test -f /app/output.xlsx"
interval_sec = 1
timeout_sec = 5
retries = 3
[steps.verifier]
timeout_sec = 600.0
''', encoding="utf-8")
    for number, s in ((1, base), (2, second)):
        step = root / "steps" / f"step-{number}"
        legacy = ROOT / "legacy_steps" / f"{base['task_id'][:3]}_S{number}"
        for folder in ("tests", "solution", "workdir"): (step / folder).mkdir(exist_ok=True)
        (step / "instruction.md").write_text(instruction(s, native_step=True), encoding="utf-8")
        write_hidden_bundle(s, public_view(s), step)
        shutil.copy2(legacy / "solution" / "reference.xlsx", step / "solution" / "reference.xlsx")
        shutil.copy2(legacy / "solution" / "memo.md", step / "solution" / "memo.md")
        if number == 1:
            script(step / "solution" / "solve.sh", '#!/bin/bash\nset -euo pipefail\ncp "$(dirname "$0")/reference.xlsx" /app/output.xlsx\ncp "$(dirname "$0")/memo.md" /app/memo.md\n')
        else:
            shutil.copy2(ROOT / "legacy_steps" / f"{base['task_id'][:3]}_S1" / "solution" / "reference.xlsx", step / "solution" / "prior_state.xlsx")
            shutil.copy2(legacy / "environment" / "event.json", step / "workdir" / "event.json")
            shutil.copy2(legacy / "environment" / "inputs.xlsx", step / "workdir" / "event_inputs.xlsx")
            save(step / "workdir" / "event_inputs.json", public_view(s))
            script(step / "solution" / "solve.sh", '''#!/bin/bash
set -euo pipefail
if [ ! -f /app/output.xlsx ]; then bash "$(dirname "$0")/restore_step1.sh"; fi
python3 "$(dirname "$0")/native_event.py" /app/output.xlsx "$(dirname "$0")/reference.xlsx" /app/event_inputs.json
cp "$(dirname "$0")/memo.md" /app/memo.md
''')
            script(step / "solution" / "restore_step1.sh", '#!/bin/bash\nset -euo pipefail\ncp "$(dirname "$0")/prior_state.xlsx" /app/output.xlsx\n')
            shutil.copy2(ROOT / "native_event.py", step / "solution" / "native_event.py")
            shutil.copy2(step / "solution" / "prior_state.xlsx", step / "tests" / "prior_state.xlsx")
        script(step / "tests" / "test.sh", '#!/bin/bash\nset -u\nmkdir -p /logs/verifier\npython3 /tests/grader.py --task-dir /tests --report /logs/verifier/report.json\nexit 0\n')
    return root


def script(path, text):
    path.write_text(text, encoding="utf-8"); path.chmod(0o755)


def generate_all(n=30, seed=20261122, index_offset=0, tasks=None, metadata_only=False):
    write_library(BASE / "rubric_library")
    if not metadata_only:
        for old in (BASE / "tasks").glob("D??_S?"):
            if old.is_dir(): shutil.rmtree(old)
    made = []; parents = {}
    for i in range(index_offset, index_offset + n):
        family = "F" if i < 24 else "D"; index = i if family == "F" else i - 24
        base = make_spec(index, seed, family)
        if family == "F":
            if tasks and base["task_id"] not in tasks: continue
            build(base, metadata_only); made.append(base["task_id"]); print("GENERATED", base["task_id"], flush=True)
        else:
            parents[index] = base
            second = make_spec(index, seed, family, 2, base)
            if tasks and base["task_id"] not in tasks and second["task_id"] not in tasks and f"D{index+1:02d}" not in tasks: continue
            build(base, metadata_only)
            build(second, metadata_only)
            build_native_multistep(base, second, metadata_only)
            made.append(base["task_id"][:3]); print("GENERATED_NATIVE", base["task_id"][:3], flush=True)
    save(ROOT / "generation_record.json", {"seed": seed, "index_offset": index_offset, "n": n, "generated": made, "metadata_only": metadata_only})
    return made


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=30); p.add_argument("--seed", type=int, default=20261122); p.add_argument("--index-offset", type=int, default=0); p.add_argument("--tasks", nargs="*"); p.add_argument("--metadata-only", action="store_true")
    a = p.parse_args()
    if a.n < 1 or a.index_offset < 0: p.error("n must be positive; index-offset nonnegative")
    generate_all(a.n, a.seed, a.index_offset, a.tasks, a.metadata_only)

if __name__ == "__main__": main()
