#!/usr/bin/env python3
import datetime as dt
import importlib.util
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font

from common import DATA, EXP, ROOT, TASKS, blank_environment, copy_public, dockerfiles, dump, sha, test_shell, write

MODULE = ROOT / "e_common.py"
LOADER = importlib.util.spec_from_file_location("dcf_v2_frozen_reader", MODULE)
V2 = importlib.util.module_from_spec(LOADER)
LOADER.loader.exec_module(V2)

TASK_PLAN = {
    "E01": {"source_task_id": "E01", "ticker": "MSFT", "cut": "2024-06-30", "asof": "2024-08-29", "variant": "annual", "shape": "xlsx", "sector": "软件与云计算", "title": "微软：云业务需求、资本开支与开放预测"},
    "E02": {"source_task_id": "E02", "ticker": "DE", "cut": "2024-10-27", "asof": "2024-12-26", "variant": "annual", "shape": "json", "sector": "农业机械周期", "title": "迪尔：农机周期与开放预测"},
    "E03": {"source_task_id": "E03", "ticker": "TGT", "cut": "2025-02-01", "asof": "2025-09-16", "variant": "h1", "shape": "xlsx", "sector": "零售与季节性营运资本", "title": "塔吉特：已报上半年与残余下半年开放预测"},
    "E04": {"source_task_id": "E04", "ticker": "NFLX", "cut": "2024-12-31", "asof": "2025-03-01", "variant": "annual", "shape": "json", "sector": "流媒体订阅与内容投入", "title": "Netflix：订阅经济与内容投入开放预测"},
}

DRIVER_TEXT = {
    "MSFT": "结合商业云需求、数据中心产能和利用率、人工智能基础设施折旧以及承诺需求的期限分析。不要把所有收入视为同一个同质化订阅池。",
    "DE": "结合设备销量、价格与产品组合、生产库存、更新周期及经销商库存分析；区分周期性收入/利润率风险与长期再投资需求。",
    "TGT": "结合可比销售、客流与客单价、季节性库存及假日权重分析。已报上半年是实际值，不得机械年化为全年。",
    "NFLX": "结合付费会员、留存、定价与广告套餐、内容摊销分析。汇总历史无法单独识别各经营变量，应把不可观测量明确标为开放假设。",
}

KEY_DEFINITIONS = [
    ("hist_revenue_fy0", "最近完整财年收入"),
    ("hist_ebit_fy0", "最近完整财年经营利润"),
    ("hist_eps_fy0", "最近完整财年稀释每股收益"),
]


def output_keys(variant):
    keys = list(KEY_DEFINITIONS)
    if variant != "annual":
        keys += [("actual_partial_revenue_y1", "已报离散季度收入之和"),
                 ("actual_partial_ebit_y1", "已报离散季度经营利润之和"),
                 ("residual_revenue_y1", "FY1 仅未报残余期收入"),
                 ("residual_fcff_y1", "FY1 仅未报残余期且计入估值的 FCFF"),
                 ("residual_discount_years", "估值日至 FY1 完整财年末的实际天数/365")]
    for year in range(1, 6):
        for key, label in (("revenue", "完整财年收入"), ("ebit", "完整财年经营利润"),
                           ("eps", "完整财年稀释每股收益"), ("fcff", "计入估值的 FCFF；H1 变体 FY1 仅残余期"),
                           ("discount_factor", "不含额外残余比例的折现因子")):
            keys.append((f"{key}_y{year}", label))
    keys += [("wacc", "加权平均资本成本"), ("terminal_growth", "永续增长率"),
             ("enterprise_value", "企业价值，百万美元"), ("equity_value", "股权价值，百万美元"),
             ("diluted_shares", "稀释股数，百万股"), ("value_per_share", "每股价值，美元"),
             ("mc_n", "有效模拟路径数"), ("mc_p10", "模拟每股价值第10百分位"),
             ("mc_p25", "模拟每股价值第25百分位"), ("mc_p50", "模拟每股价值第50百分位"),
             ("mc_p75", "模拟每股价值第75百分位"), ("mc_p90", "模拟每股价值第90百分位"),
             ("mc_mean", "模拟每股价值均值")]
    return keys


def prior_partial(pack, cfg, quarters):
    if cfg["variant"] == "annual":
        return []
    previous = []
    for quarter in quarters:
        start, end = quarter["period"].split("..")
        prior_end = (dt.date.fromisoformat(end) - dt.timedelta(days=364)).isoformat()
        candidates = []
        for period, value in pack["quarterly"]["revenue"].items():
            a, b = period.split("..")
            if abs((dt.date.fromisoformat(b) - dt.date.fromisoformat(prior_end)).days) <= 7:
                candidates.append((b, period, value))
        if not candidates:
            raise ValueError(f"缺少上年同期季度 {prior_end}")
        _, period, revenue = sorted(candidates)[-1]
        previous.append({"period": period, "end": period.split("..")[1],
                         "revenue": revenue / 1e6,
                         "operating_income": (pack["quarterly"].get("operating_income", {}).get(period) or 0) / 1e6})
    return previous


def build_inputs(cfg):
    original = dict(V2.TASK_PLAN[cfg["source_task_id"]])
    original.update({"task_id": cfg["task_id"], "years": 5, "mc_seed": cfg["mc_seed"],
                     "min_paths": 5000, "asof": cfg["asof"], "cut": cfg["cut"]})
    pack = json.loads((DATA / "packs" / f"{cfg['ticker']}.json").read_text())
    inputs = V2.public_inputs(original, pack, ROOT)
    inputs.update({"schema_version": "dcf-v3-e-frozen-v1", "title": cfg["title"],
                   "valuation_date": cfg["asof"], "information_cutoff": cfg["asof"]})
    inputs["company"]["sector"] = cfg["sector"]
    inputs["business_driver_prompt"] = DRIVER_TEXT[cfg["ticker"]]
    inputs["data_scope"] = {
        "history": "历史来自本地 SEC XBRL 快照；金额和股数均为百万，EPS 为美元，比率为小数。",
        "blanks": "null 表示没有单独可得的字段，不得当作零。",
        "partial_period": "quarters 是离散实际季度而非年初至今累计，不能重复加总；prior_year_quarters 仅提供上年同期收入/经营利润作为残余基数。",
        "forecast_convention": "H1 变体的 FY1 revenue/ebit/eps 是完整财年，da/capex/delta_nwc/reinvestment_component/fcff 均为未报残余期。年度变体全为完整财年。",
        "discount": "折现年数为估值日至对应完整财年末的实际天数/365，其后逐年加一。折现因子=1/(1+WACC)^年数，不再乘残余比例。",
        "price": "不提供当前股价、目标价或市场一致预期；未来实际值和股价仅是隐藏诊断。",
    }
    inputs["restricted_retrieval"] = {"enabled": False, "network": "offline",
                                      "prohibited": ["网络检索", "截止日后信息", "当前股价", "目标价", "市场一致预期"],
                                      "enforcement": "任务及容器均配置为离线；验证记录单独说明实际运行范围。"}
    if cfg["variant"] != "annual":
        actual = inputs["reported_partial_period"]["quarters"]
        future_ends = [x for x in pack["fiscal_year_ends"] if x > cfg["cut"]]
        if not future_ends:
            raise ValueError("冻结数据缺少下一财年末")
        year_end = future_ends[0]
        days = (dt.date.fromisoformat(year_end) - dt.date.fromisoformat(cfg["asof"])).days
        if days <= 0:
            raise ValueError("残余期折现天数必须为正")
        inputs["reported_partial_period"]["timing"] = {
            "residual_start": (dt.date.fromisoformat(actual[-1]["end"]) + dt.timedelta(days=1)).isoformat(),
            "next_fiscal_year_end": year_end, "remaining_days": days, "remaining_years": days / 365,
            "discount_years": [days / 365 + i for i in range(5)], "remaining_fractions": [1] * 5,
        }
        inputs["reported_partial_period"]["prior_year_quarters"] = prior_partial(pack, cfg, actual)
        if len(actual) != 2:
            raise ValueError("H1 必须有两个离散季度")
        for quarter in actual:
            for field in ("revenue", "operating_income"):
                if quarter.get(field) is None:
                    raise ValueError("残余变体缺少数值：" + field)
    else:
        inputs["reported_partial_period"]["timing"] = {"discount_years": [1, 2, 3, 4, 5], "remaining_fractions": [1] * 5}
    return inputs, pack


def make_input_workbook(inputs, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Historical"
    ws.append(["冻结历史；金额为百万美元，股数为百万股，EPS 为美元；null 不等于零"])
    ws.append(["line", "item"] + inputs["fiscal_years"])
    for line, (label, _) in V2.LINES.items():
        ws.append([line, label] + [inputs["historical"][line][year] for year in inputs["fiscal_years"]])
    partial = inputs["reported_partial_period"]
    if partial["quarters"]:
        for sheet_name, quarters in (("Reported_Periods", partial["quarters"]), ("Prior_Partial", partial["prior_year_quarters"])):
            sheet = wb.create_sheet(sheet_name)
            sheet.append(["离散季度；仅上年同期页提供收入与经营利润"])
            sheet.append(["line", "item"] + [x["period"] for x in quarters])
            for line in ("revenue", "operating_income"):
                sheet.append([line, line] + [x.get(line) for x in quarters])
            if sheet_name == "Reported_Periods":
                for line in V2.LINES:
                    if line not in ("revenue", "operating_income"):
                        sheet.append([line, line] + [x.get(line) for x in quarters])
    market = wb.create_sheet("Market")
    market.append(["item", "value", "source_id"])
    for line in ("treasury_date", "treasury_10y"):
        market.append([line, inputs["market_observation"][line], "UST_DGS10"])
    market.append(["information_cutoff", inputs["information_cutoff"], "SEC_XBRL"])
    outputs = wb.create_sheet("Outputs")
    outputs.append(["key", "中文定义", "value"])
    for key, definition in output_keys(inputs["reported_partial_period"]["type"]):
        outputs.append([key, definition, None])
    sources = wb.create_sheet("Sources")
    sources.append(["source_id", "publisher", "document", "url", "source_sha256", "retrieval_status"])
    for row in inputs["sources"]:
        sources.append([row.get(key) for key in ("source_id", "publisher", "document", "url", "source_sha256", "retrieval_status")])
    for sheet in wb:
        sheet.freeze_panes = "C3" if sheet.title == "Historical" else "A2"
        sheet.column_dimensions["A"].width = 32
        sheet.column_dimensions["B"].width = 55
        for cell in sheet[1]:
            cell.font = Font(bold=True)
    wb.save(path)


def instruction(cfg, inputs):
    partial = inputs["reported_partial_period"]
    timing = partial["timing"]
    if cfg["shape"] == "xlsx":
        model = f"""提交 `/app/output/model.xlsx`：保留公开工作簿的 `Outputs` 页，并建立 `Assumptions`、`Forecast`、`DCF` 页。Outputs 的 A 列为题给键，C 列必须是活公式；历史、五个预测年度、估值输出均链接到模型，模拟统计链接到 `MC_Trials`。Assumptions 的 A/B 列分别放键和数值，至少包括：`initial_growth`、`terminal_revenue_growth`、`steady_ebit_margin`、`tax_rate`、`da_to_revenue`、`capex_to_revenue`、`nwc_to_revenue`、`interest_rate`、`wacc`、`terminal_growth`、`net_debt`、`cash_and_investments`、`diluted_shares`。Forecast 的 A 列为键，C:G 为 FY1–FY5；必须包含 revenue、ebit、eps、da、capex、delta_nwc、reinvestment_component、fcff、discount_factor。经营预测、再投资、DCF 和股权桥不能粘贴固定结果；评分会实际修改 WACC 与 g 并重算。"""
    else:
        model = """提交 `/app/output/model.json`，包含对象 `historical`、`assumptions`、`forecast`、`valuation`、`simulation_summary`。historical 使用 Outputs 同名历史键；assumptions 至少包含 `initial_growth`、`terminal_revenue_growth`、`steady_ebit_margin`、`tax_rate`、`da_to_revenue`、`capex_to_revenue`、`nwc_to_revenue`、`interest_rate`、`wacc`、`terminal_growth`、`net_debt`、`cash_and_investments`、`diluted_shares`。forecast 每年包含 `revenue_y1`…`revenue_y5`、`ebit_y*`、`eps_y*`、`da_y*`、`capex_y*`、`delta_nwc_y*`、`reinvestment_component_y*`、`fcff_y*`、`discount_factor_y*`；H1 变体另含实际/残余键。valuation 包含 WACC、g、税率、净债务、现金及投资、稀释股数、企业/股权/每股价值、`discount_years` 五元素数组和 `terminal_year_fcff`；simulation_summary 含 `n_valid`、`p10/p25/p50/p75/p90/mean`。另交 `/app/output/recompute.py`，接受 `--input INPUT --model MODEL --output DIR` 并写 `recomputed.json`。它必须从上述经营假设和公开历史重建每年收入、EBIT、再投资及估值，不得只回显 forecast/valuation 的既有结果。评分会修改经营假设和 WACC/g 后独立执行。"""
    residual = ""
    if cfg["variant"] != "annual":
        residual = f"""
### 已报 H1 与残余 H2（本题关键）

- 两个 `Reported_Periods` 离散季度是 FY1 已报实际，只相加一次；`Prior_Partial` 是上年同期 H1，用作残余预测基数。FY1 完整财年收入 = 已报 H1 收入 + 你预测的 H2 收入；EBIT 同理。
- FY1 的 da、capex、delta_nwc、reinvestment_component、fcff 均只指未报 H2。全年 FCFF 可另列，但 `fcff_y1` 与估值只能含 H2，不得把已报现金流再次折现。
- 确定性 H2 收入 = 上年同期 H2 收入 ×(1+本期增长)，H2 EBIT = H2 收入 × 本期 EBIT 利润率；D&A、CapEx 按 H2 收入比例计算。FY1 ΔNWC = 上年 FY0 经营性 NWC ×(FY1 全年收入/FY0 全年收入−1)，FY2 起 = 本年 NWC−上年 NWC。经营性 NWC = 流动资产−现金−短期投资−(流动负债−当期债务)。
- 从估值日 {cfg['asof']} 到 FY1 完整财年末 {timing['next_fiscal_year_end']} 为 {timing['remaining_days']} 天，折现年数={timing['remaining_years']:.12f}，后续逐年加一。FCFF 已经只含 H2，不能再乘残余比例。
- 模拟的 FY1 trajectory.revenue/ebit/reinvestment/fcff 只含 H2，从上年同期 H2 基数起算；FY2–FY5 才是完整财年。模型 Outputs 中的 revenue/ebit/eps 仍是完整财年。
"""
    return f"""# {cfg['title']}

你是信息截止日 **{cfg['asof']}** 的估值分析师。只可使用 `/app/data/inputs.json` 和等价的 `/app/data/frozen_history.xlsx`；本题离线。禁止使用截止日后的披露、当前股价、现成目标价或市场一致预期。不存在唯一正确的开放假设或目标每股价值。

## 历史证据与五年模型

最近完整财年截止 {cfg['cut']}。行业分析要求：{DRIVER_TEXT[cfg['ticker']]}

建立五个财年的收入、经营利润（EBIT）、稀释 EPS 与 FCFF。解释收入增长、利润率、税率、D&A、CapEx、营运资本和股权桥的来源与适用日期。金额为百万美元，股数为百万股，EPS/每股价值为美元，比率为小数。股份支付是经营成本，不得加回 FCFF。经营 NWC = 流动资产−现金−短期投资−(流动负债−当期债务)。净债务只含当期及非当期债务；股权价值 = 企业价值 + 现金及短期投资 − 净债务。

每年 `reinvestment_component = D&A − CapEx − ΔNWC`；`FCFF = EBIT×(1−税率) + reinvestment_component`；`discount_factor = 1/(1+WACC)^discount_years`。终值采用 Gordon 公式，以 FY5 的 FCFF 为基期并折现到估值日；WACC 必须大于 g。年度变体折现年数为 1,2,3,4,5，FY1 是估值日后第一个完整预测年度。
{residual}
## 候选自写 Monte Carlo

编写并实际运行 `/app/output/simulate.py`：
`python3 /app/output/simulate.py --input /app/data/inputs.json --model /app/output/model.{cfg['shape']} --output /app/output/simulation.json`

至少生成 **5,000 条有效路径**，声明 seed **{cfg['mc_seed']}**，采用可复现伪随机数发生器。分别抽样收入增长、EBIT 利润率、再投资强度和折现率，不能直接抽每股价值或股价。声明支持的分布（triangular/uniform/normal/lognormal/beta）、数值参数、单位和有限上下界；保留合法抽样并单列拒绝数。增长与利润率要有非零相关性，或说明独立性的证据及局限；给出声明的相关矩阵及所有四个驱动的实际相关矩阵。模拟边界应能从历史波动或明确的压力情景推导。

`simulation.json` 顶层必须含：`seed`、`n_valid`、`n_rejected`、`method`、`drivers`、`dependence`、`realized_correlation`、`trials`、`statistics`、`percentile_convention`、`limitations`。drivers 以四个精确键 `revenue_growth`、`ebit_margin`、`reinvestment_intensity`、`discount_rate` 为索引，每项含 distribution、parameters、unit、bounds。dependence 含 `ordered_names`、4×4 `matrix`，或 `type: independence` 与 explanation。每条 trial 含 `path_id`、上述四个驱动、`value_per_share` 和五行 `trajectory`；每年含 `year/revenue/ebit/reinvestment/fcff/discount_factor`。路径 reinvestment 是资本开支加营运资本增加减 D&A（正值消耗现金），故 `fcff=ebit×(1−tax)−reinvestment`。增长与利润率在一条路径内保持不变；再投资=当年 trajectory.revenue×reinvestment_intensity。终值以 FY5 路径 FCFF 计算，采用该路径折现率。每条路径必须可由评分器独立重算，不能只提交摘要。分位数采用 `(N−1)q` 线性插值或 `nearest_r` 并如实声明。

## 交付物与说明

{model}

另交 `simulation.json`、`simulate.py`、`memo.md`。memo 不超过 700 个空白分隔词，中文撰写：逐项给出至少三个历史行名/期间/数值/SEC_XBRL 来源，说明可复现的假设推导、公司特定经营因果链、再投资理由、模拟边界与相关性选择，并明确预测不确定性及模型局限。模拟区间是模型条件 DCF 分布，不是股价预测。评分器会重新执行模拟器并独立检查分布、相关性、全部路径算术和分位数；未来实际值及未来股价只在隐藏诊断中出现，不进入评分。
"""


def make_truth(cfg, inputs, pack):
    future_years = [year for year in pack["fiscal_year_ends"] if year > cfg["cut"]][:3]
    actuals = {}
    for year in future_years:
        actuals[year] = {key: pack["annual"].get(key, {}).get(year) if key == "eps_diluted"
                         else (pack["annual"].get(key, {}).get(year) / 1e6
                               if pack["annual"].get(key, {}).get(year) is not None else None)
                         for key in ("revenue", "operating_income", "eps_diluted")}
    prices = {date: value for date, value in pack.get("daily_close", {}).items() if date > cfg["asof"]}
    return {"task_id": cfg["task_id"], "cutoff": cfg["asof"], "mc_seed": cfg["mc_seed"],
            "min_paths": 5000, "historical": inputs["historical"],
            "public_partial_periods": inputs["reported_partial_period"]["quarters"],
            "output_keys": [key for key, _ in output_keys(cfg["variant"])],
            "future_actuals": actuals, "future_prices": prices,
            "diagnostic_only": ["future_actuals", "future_prices"],
            "limitations": ["未来实际值和股价不进入机制得分或开放判断。",
                            "真实公司回测可能存在训练记忆泄漏，无法排除。",
                            "股价为未复权历史收盘，仅作诊断。",
                            "SEC 标准标签不能完整识别分部与经营单位。"]}


def build(task_id):
    cfg = dict(TASK_PLAN[task_id])
    cfg.update({"task_id": task_id, "family": "E", "years": 5, "min_paths": 5000,
                "mc_seed": 1729 + int(task_id[1:]) * 101})
    task = TASKS / task_id
    blank_environment(task)
    inputs, pack = build_inputs(cfg)
    dump(task / "environment/data/inputs.json", inputs)
    make_input_workbook(inputs, task / "environment/data/frozen_history.xlsx")
    write(task / "instruction.md", instruction(cfg, inputs))
    spec = {key: value for key, value in cfg.items() if key != "title"}
    spec.update({"schema_version": "dcf-v3-task-v1", "language": "zh-CN",
                 "required_artifacts": [f"model.{cfg['shape']}", "simulate.py", "simulation.json", "memo.md"] + (["recompute.py"] if cfg["shape"] == "json" else []),
                 "output_keys": [key for key, _ in output_keys(cfg["variant"])],
                 "frozen_source_sha256": {"pack": sha(DATA / "packs" / f"{cfg['ticker']}.json"),
                                           "companyfacts": sha(DATA / "raw" / f"{cfg['ticker']}_facts.json"),
                                           "treasury": sha(DATA / "raw/DGS10.csv")},
                 "future_data_role": "diagnostic_only",
                 "mechanical_check_families": ["historical", "forecast", "valuation", "formula", "simulation"],
                 "nonmechanical_status": "not_selected_not_scored_here"})
    dump(task / "spec.json", spec)
    dump(task / "tests/spec.json", spec)
    dump(task / "tests/truth.json", make_truth(cfg, inputs, pack))
    copy_public(task)
    dockerfiles(task)
    write(task / "environment/docker-compose.yaml", "services:\n  main:\n    network_mode: none\n")
    write(task / "task.toml", f'''schema_version = "1.4"
artifacts = ["/app/output"]
[metadata]
category = "dcf-open-forecast-simulation"
difficulty = "very-hard"
network = "offline"
tags = ["E", "{cfg['ticker']}", "{cfg['variant']}", "{cfg['shape']}"]
disable_web_search = true
[agent]
timeout_sec = 5400.0
network_mode = "no-network"
[verifier]
timeout_sec = 1800.0
environment_mode = "separate"
[verifier.environment]
network_mode = "no-network"
[environment]
network_mode = "no-network"
build_timeout_sec = 900.0
cpus = 2
memory_mb = 4096
storage_mb = 4096
''')
    write(task / "tests/grader.py", (ROOT / "e_grader.py").read_text())
    write(task / "tests/e_model.py", (ROOT / "e_model.py").read_text())
    write(task / "tests/test.sh", test_shell(), executable=True)
    write(task / "solution/reference.py", (ROOT / "e_reference.py").read_text())
    write(task / "solution/e_model.py", (ROOT / "e_model.py").read_text())
    write(task / "solution/e_simulator.py", (ROOT / "e_simulator.py").read_text())
    write(task / "solution/solve.sh", f'''#!/bin/bash
set -euo pipefail
mkdir -p /app/output
python3 /solution/reference.py --input /app/data/inputs.json --output /app/output
python3 /app/output/simulate.py --input /app/data/inputs.json --model /app/output/model.{cfg['shape']} --output /app/output/simulation.json
''', executable=True)
    return {"task_id": task_id, "family": "E", "ticker": cfg["ticker"], "cutoff": cfg["asof"],
            "shape": cfg["shape"], "variant": cfg["variant"], "seed": cfg["mc_seed"],
            "inputs_sha256": sha(task / "environment/data/inputs.json")}
