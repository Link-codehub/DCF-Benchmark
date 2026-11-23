#!/usr/bin/env python3
"""Build the unified v3 rubric library from v2 atoms plus v3 additions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V2 = ROOT.parent / "dcf_factory_v2"

MAIN, MINOR = "主需", "次需"
WEIGHT = {MAIN: 3, MINOR: 1}
CATEGORIES = ["交付与来源完整性", "历史与会计口径", "经营预测", "三表勾稽", "DCF与估值桥",
              "公式与模型工程", "开放假设与模拟", "多步状态与业务重构", "表达与专业可用性"]
CATEGORY_MAP = {
    "交付与来源完整性": "交付与来源完整性", "联网取数": "交付与来源完整性",
    "历史与会计口径": "历史与会计口径", "输入原样采用与历史口径": "历史与会计口径",
    "经营预测": "经营预测", "行业口径": "经营预测", "分部与管线": "经营预测",
    "三表勾稽": "三表勾稽",
    "DCF与估值桥": "DCF与估值桥", "情景与多方法": "DCF与估值桥",
    "公式与模型工程": "公式与模型工程", "开放假设与模拟": "开放假设与模拟",
    "多步状态与过程": "多步状态与业务重构",
    "表达与专业可用性": "表达与专业可用性", "透明度与可审计性": "表达与专业可用性",
    "呈现与客户可用性": "表达与专业可用性",
}


def normalize_category(item):
    if item["id"].startswith("X-IC-") or item["id"] == "X-IF-003":
        return "公式与模型工程" if item["method"] == "rule" else "表达与专业可用性"
    return CATEGORY_MAP[item["category"]]


# v2 shared atoms -> v3 (family, category, importance, applies_when)
V2_MAP = {
    "01-FILE": ("BC", "交付与来源完整性", MAIN, "all"),
    "01-KEYS": ("BC", "交付与来源完整性", MAIN, "all"),
    "01-UNIT": ("BC", "交付与来源完整性", MINOR, "all"),
    "01-HISTORY": ("D", "多步状态与过程", MAIN, "D 所有后续步骤"),
    "02-FY": ("BC", "历史与会计口径", MAIN, "非年度历史"),
    "02-LTM": ("BC", "历史与会计口径", MAIN, "非年度历史"),
    "02-REPORTED": ("BC", "历史与会计口径", MAIN, "规范化历史"),
    "02-SBC": ("BC", "历史与会计口径", MAIN, "SBC"),
    "02-COLLECT": ("BC", "历史与会计口径", MINOR, "合同负债"),
    "03-DRIVER": ("BC", "经营预测", MAIN, "存量驱动"),
    "03-AVERAGE": ("BC", "经营预测", MAIN, "存量驱动"),
    "03-MARGIN": ("BC", "经营预测", MAIN, "all"),
    "03-CAPEX": ("BC", "经营预测", MINOR, "资本开支重排"),
    "03-NWC": ("BC", "经营预测", MAIN, "all"),
    "03-DAYS": ("BC", "经营预测", MINOR, "营运资本天数法"),
    "03-DEBT": ("BC", "经营预测", MAIN, "债务计划表"),
    "03-LEASE": ("BC", "经营预测", MINOR, "租赁"),
    "03-NOL": ("BC", "经营预测", MINOR, "NOL"),
    "04-BALANCE": ("BC", "三表勾稽", MAIN, "三表"),
    "04-CASH": ("BC", "三表勾稽", MAIN, "三表"),
    "04-RE": ("BC", "三表勾稽", MAIN, "三表"),
    "04-PPE": ("BC", "三表勾稽", MAIN, "资产滚动"),
    "05-FCFF": ("BC", "DCF与估值桥", MAIN, "FCFF 口径"),
    "05-WACC": ("BC", "DCF与估值桥", MAIN, "CAPM"),
    "05-DF": ("BC", "DCF与估值桥", MAIN, "all"),
    "05-DUAL": ("BC", "DCF与估值桥", MAIN, "双终值"),
    "05-TV": ("BC", "DCF与估值桥", MAIN, "all"),
    "05-BRIDGE": ("BC", "DCF与估值桥", MAIN, "all"),
    "05-DILUTION": ("BC", "DCF与估值桥", MINOR, "稀释股数"),
    "05-VPS": ("BC", "DCF与估值桥", MAIN, "all"),
    "05-SENS": ("BC", "DCF与估值桥", MINOR, "估值敏感性"),
    "05-SCENARIO": ("BC", "情景与多方法", MAIN, "情景驱动"),
    "06-FORMULA": ("BC", "公式与模型工程", MAIN, "all"),
    "06-RECALC": ("BC", "公式与模型工程", MAIN, "all"),
    "06-PERTURB1": ("BC", "公式与模型工程", MAIN, "all"),
    "06-PERTURB2": ("BC", "公式与模型工程", MAIN, "all"),
    "06-LINKS": ("BC", "公式与模型工程", MAIN, "all"),
    "06-FREE": ("BC", "公式与模型工程", MINOR, "自由或混合布局"),
    "07-ASSUME": ("E", "开放假设与模拟", MAIN, "开放假设"),
    "07-PATHS": ("E", "开放假设与模拟", MAIN, "Monte Carlo"),
    "07-QUANTILE": ("E", "开放假设与模拟", MAIN, "Monte Carlo"),
    "08-OLD": ("D", "多步状态与过程", MAIN, "D 所有后续步骤"),
    "08-REBASE": ("D", "多步状态与过程", MAIN, "重定基期事件"),
    "08-DISPOSE": ("D", "多步状态与过程", MAIN, "剥离事件"),
    "08-REFINANCE": ("D", "多步状态与过程", MAIN, "融资或资本开支事件"),
    "08-RESTATE": ("D", "多步状态与过程", MAIN, "D 所有后续步骤"),
    "09-MEMO": ("BC", "表达与专业可用性", MINOR, "all"),
    "09-READABLE": ("BC", "表达与专业可用性", MINOR, "all"),
}

# E items whose meaning duplicates a v2 shared atom are dropped.
E_DUPLICATES = {
    "deliver_output_keys": "01-KEYS",
    "dcf_terminal": "05-TV",
    "dcf_equity": "05-BRIDGE",
    "formula_recalc": "06-RECALC",
    "formula_live": "06-FORMULA",
    "mc_paths": "07-PATHS",
    "mc_quantiles": "07-QUANTILE",
}
E_CATEGORY = {"DCF 与估值桥": "DCF与估值桥"}
E_MAIN = {"hist_revenue", "hist_ebit", "hist_partial_revenue", "hist_partial_residual_boundary", "forecast_reinvestment",
          "dcf_fcff", "dcf_discount", "mc_distributions", "mc_dependence", "mc_recompute", "deliver_model",
          "deliver_simulator", "deliver_trials", "llm_driver_derivation", "agent_distribution_rationale",
          "llm_business_chain", "llm_reinvestment_reasoning"}

# v3 additions: (id, family, category, importance, requirement, evidence, applies_when, method)
V3_NEW = [
    ("B-MIXLTM", "BC", "历史与会计口径", MAIN, "混合历史 LTM 由最近完整半年加其后桥接季度构成，不重复计入、不遗漏、不年化", "历史聚合与原始期间", "混合历史拼接", "rule"),
    ("B-NWC-OPEN", "BC", "经营预测", MAIN, "首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额）", "营运资本表首期", "all", "rule"),
    ("B-INTANG-ROLL", "BC", "经营预测", MAIN, "无形资产按期初加新增减摊销独立滚动，不与固定资产合并", "无形资产滚动表", "双资产池", "rule"),
    ("B-INTANG-FCFF", "BC", "DCF与估值桥", MAIN, "无形资产新增在 FCFF 中扣减，摊销作为非现金项加回", "FCFF 表", "双资产池", "rule"),
    ("B-RESIDUAL", "BC", "DCF与估值桥", MAIN, "首个预测段只计入估值日后的经营现金流", "残余期 FCFF", "all", "rule"),
    ("C-SOTP-SEG", "BC", "分部与管线", MAIN, "每个分部有独立的收入、利润率、再投资和 FCFF", "分部预测表", "分部 SOTP", "rule"),
    ("C-SOTP-VAL", "BC", "分部与管线", MAIN, "每个分部按题面指定方法（DCF 或倍数）单独估值", "分部估值表", "分部 SOTP", "rule"),
    ("C-SOTP-SUM", "BC", "分部与管线", MAIN, "SOTP 企业价值等于各分部价值之和，公司层费用按题面处理", "SOTP 汇总", "分部 SOTP", "rule"),
    ("C-SOTP-BRIDGE", "BC", "分部与管线", MAIN, "净债务与稀释股数只在公司层扣减一次，不在分部重复扣减", "SOTP 股权桥", "分部 SOTP", "rule"),
    ("C-PIPE-TIMING", "BC", "分部与管线", MAIN, "未投产或未上市项目在投产日前不产生收入", "项目时间轴", "风险调整管线", "rule"),
    ("C-PIPE-CAPEX", "BC", "分部与管线", MAIN, "建设期支出与投产期收入分别建模并计入对应期间", "项目现金流", "风险调整管线", "rule"),
    ("C-PIPE-PROB", "BC", "分部与管线", MAIN, "成功概率作用于项目现金流或项目价值，不通过调整 WACC 体现", "风险调整 FCFF", "风险调整管线", "rule"),
    ("C-PIPE-SUM", "BC", "分部与管线", MAIN, "公司价值等于各项目风险调整价值之和加已有业务价值", "管线汇总", "风险调整管线", "rule"),
    ("C-CASE-SWITCH", "BC", "情景与多方法", MAIN, "单一情景开关切换后收入、利润率、再投资、FCFF、终值和每股价值同时改变", "Cases 页与 Operating Model", "情景驱动", "rule"),
    ("C-CASE-ISOLATE", "BC", "情景与多方法", MINOR, "每个情景的输出值与独立真值一致，情景之间不相互覆盖", "情景结果表", "情景驱动", "rule"),
    ("C-MULTI-SPLIT", "BC", "情景与多方法", MAIN, "Gordon 与退出倍数估值分别给出，不只输出加权结果", "估值结果", "多方法估值", "rule"),
    ("C-IMPLIED-MULT", "BC", "情景与多方法", MAIN, "由 Gordon 终值反推的隐含 EV/EBITDA 计算正确", "隐含倍数单元格", "多方法估值", "rule"),
    ("C-IMPLIED-G", "BC", "情景与多方法", MAIN, "由退出倍数终值反推的隐含永续增长率计算正确", "隐含增长率单元格", "多方法估值", "rule"),
    ("C-REVERSE", "BC", "情景与多方法", MAIN, "由给定市场价格反推的隐含 WACC 或隐含增长假设正确，且以公式或求解过程得出", "反推单元格", "反向推导", "rule"),
    ("C-RANGE", "BC", "情景与多方法", MINOR, "估值区间的上下界分别来自题面指定的方法和假设范围", "Football Field 表", "估值区间", "rule"),
    ("A-DRIVER", "A", "行业口径", MAIN, "收入由该行业规定的业务驱动构造，而不是单一增长率", "收入预测", "all A", "rule"),
    ("A-METRIC", "A", "行业口径", MAIN, "行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算", "行业指标表", "all A", "rule"),
    ("A-VALUATION", "A", "行业口径", MAIN, "估值方法适配行业（金融用股权现金流或超额收益，房地产用 NOI/NAV 等），不硬套 FCFF", "估值表", "金融、保险、房地产", "rule"),
    ("A-REASON", "A", "行业口径", MINOR, "说明中解释行业驱动与估值结果之间的因果链", "memo.md", "all A", "llm"),
    ("A-SAAS-ARR", "A", "行业口径", MAIN, "期末 ARR 等于期初 ARR 乘净留存率加新签 ARR，收入按期初期末 ARR 平均确认", "ARR 滚动表", "软件与订阅", "rule"),
    ("A-SAAS-CAPRD", "A", "行业口径", MINOR, "资本化研发作为无形资产新增扣减 FCFF，摊销加回", "研发资本化表", "软件与订阅", "rule"),
    ("A-RETAIL-SSS", "A", "行业口径", MAIN, "收入拆为可比门店同店增长与新开店贡献，新店按开业月份折算", "门店收入表", "消费零售与连锁", "rule"),
    ("A-MFG-UTIL", "A", "行业口径", MAIN, "产量不超过有效产能乘利用率上限，扩产在投产后才增加产能", "产能表", "制造与工业设备", "rule"),
    ("A-MFG-YIELD", "A", "行业口径", MAIN, "合格产量等于投入量乘良率，良率在产量和成本链中只作用一次", "投入量、良率、合格产量及销售率", "BOM 制造", "rule"),
    ("A-MFG-BOM", "A", "行业口径", MAIN, "各产品各物料耗用量等于投入量乘 BOM 单耗，耗用成本等于耗用量乘采购价，不以收入成本率替代", "分产品分物料 BOM 明细", "BOM 制造", "rule"),
    ("A-MFG-PURCHASE", "A", "行业口径", MAIN, "采购与耗用及原材料滚动勾稽，采购不得直接作为 COGS", "采购、耗用、原材料和 COGS", "BOM 制造", "rule"),
    ("A-MFG-INVENTORY", "A", "行业口径", MAIN, "原材料、在制品和产成品分别按题面口径滚动，不合并为单一收入比例", "三类存货期初、变动和期末", "BOM 制造", "rule"),
    ("A-PHARMA-FUNNEL", "A", "行业口径", MAIN, "各管线收入由患者基数、诊断及适用比例、渗透率、依从性和净价格逐期构建", "患者漏斗、治疗人次、净价格和收入", "医药与生物科技", "rule"),
    ("A-PHARMA-COMMITRD", "A", "行业口径", MAIN, "上市前承诺研发投入不乘 PoS，已实现费用不因上市延迟删除", "研发费用表、PoS 及上市时点", "研发管线", "rule"),
    ("A-PHARMA-COMMERCIAL", "A", "行业口径", MAIN, "已商业化产品不重复乘研发成功概率", "commercial 现金流与 PoS 开关", "研发管线", "rule"),
    ("A-PHARMA-CLIFF", "A", "行业口径", MAIN, "专利到期后收入按题面侵蚀曲线下降，不延续到期前增长", "产品收入表", "医药与生物科技", "rule"),
    ("A-HEALTH-PAYER", "A", "行业口径", MINOR, "收入按服务量乘各支付方单价加权，支付方结构变化影响均价", "服务收入表", "医疗服务", "rule"),
    ("A-BANK-NII", "A", "行业口径", MAIN, "净利息收入等于平均生息资产乘净息差，资产增长受资本充足率约束", "银行损益表", "银行与金融", "rule"),
    ("A-BANK-EQUITY", "A", "行业口径", MAIN, "使用股权现金流或超额收益模型，以股权成本折现", "银行估值表", "银行与金融", "rule"),
    ("A-INS-CR", "A", "行业口径", MAIN, "承保利润等于已赚保费乘一减综合成本率，投资收益单独计算", "保险损益表", "保险", "rule"),
    ("A-ENERGY-DECLINE", "A", "行业口径", MAIN, "现有储量产量按递减曲线下降，新增产量依赖开发资本开支", "产量表", "能源与资源", "rule"),
    ("A-UTIL-RAB", "A", "行业口径", MAIN, "允许收入等于受监管资产基数乘允许回报率加折旧回收", "监管收入表", "公用事业与基础设施", "rule"),
    ("A-TRANS-LOAD", "A", "行业口径", MINOR, "收入等于运力乘载运率乘单位收益，机队扩张伴随资本开支", "运量表", "交通与物流", "rule"),
    ("A-PLAT-ARPU", "A", "行业口径", MINOR, "收入等于平均用户乘 ARPU，内容或流量成本按题面摊销", "用户收入表", "互联网平台与媒体", "rule"),
    ("A-RE-NAV", "A", "行业口径", MAIN, "物业价值等于 NOI 除以资本化率，NAV 扣除负债", "NAV 表", "房地产", "rule"),
    ("A-SVC-UTIL", "A", "行业口径", MINOR, "收入等于计费人员乘利用率乘人均费率，人员成本与人数联动", "人员收入表", "专业服务与外包", "rule"),
    ("A-EAAS-BASE", "A", "行业口径", MINOR, "服务收入由装机基数乘服务频次乘单价构成，续约率影响装机留存", "装机表", "设备即服务与装机运维", "rule"),
    ("D-FINAL-VALUES", "D", "多步状态与过程", MAIN, "最后一步工作簿的全部输出键与最终独立真值一致", "最终工作簿", "all D", "rule"),
    ("D-FINAL-LIVE", "D", "多步状态与过程", MAIN, "最后一步结果仍为活公式，隐藏扰动可传导", "最终工作簿与扰动", "all D", "rule"),
    ("D-STEP-SNAPSHOT", "D", "多步状态与过程", MAIN, "每一步都保存了独立快照", "各步 pre/post 快照", "all D", "rule"),
    ("D-STEP-VALUES", "D", "多步状态与过程", MAIN, "每一步快照的输出与该步独立真值一致", "各步快照", "all D", "rule"),
    ("D-STEP-SCOPE", "D", "多步状态与过程", MINOR, "每一步只修改该步要求涉及的依赖，未触及的输出保持不变", "相邻快照差异", "all D", "rule"),
    ("D-STEP-LOG", "D", "多步状态与过程", MINOR, "说明中逐步记录修改内容及影响", "memo.md", "all D", "llm"),
    ("W-VALUE", "W", "联网取数", MAIN, "每个要求取数的值与指定权威来源一致（在题面容差内）", "取数表", "all W", "rule"),
    ("W-SOURCE", "W", "联网取数", MAIN, "每个取数注明来源文件、期间和字段或页码，且来源属于允许范围", "取数表", "all W", "rule"),
    ("W-CROSS", "W", "联网取数", MAIN, "至少一项关键数据用第二个独立来源或勾稽关系交叉验证", "交叉验证表", "all W", "rule"),
    ("W-USED", "W", "联网取数", MAIN, "取到的数被模型公式实际引用，而不是另行手填", "模型引用关系", "all W", "rule"),
    ("W-NOFORBID", "W", "联网取数", MAIN, "未使用禁止来源或截止日后的信息", "取数记录", "all W", "agent"),
    ("W-FAILURE", "W", "联网取数", MINOR, "取数失败或数据冲突时如实披露并说明处理方法", "memo.md", "all W", "llm"),
]


def main():
    shared = []
    for path in sorted((V2 / "rubric_library").glob("[0-9][0-9]_*.json")):
        shared.extend(json.loads(path.read_text()))
    rows = []
    for item in shared:
        family, category, importance, applies = V2_MAP[item["id"]]
        rows.append({"id": item["id"], "family": family, "category": category, "requirement": item["text"],
            "evidence": item["evidence"], "applies_when": applies, "method": item["method"],
            "importance": importance, "weight": WEIGHT[importance], "source": "v2-shared", "executor_hint": item["condition"]})
    e_items = {}
    for path in sorted((V2 / "open" / "rubrics").glob("E*.json")):
        for item in json.loads(path.read_text())["rubric_items"]:
            e_items.setdefault(item["id"], item)
    for key, item in e_items.items():
        if key in E_DUPLICATES:
            continue
        importance = MAIN if key in E_MAIN else MINOR
        rows.append({"id": "E-" + key, "family": "E", "category": E_CATEGORY.get(item["category"], item["category"]),
            "requirement": item["pass_condition"], "evidence": item["evidence_location"],
            "applies_when": "E 残余期变体" if key.startswith("hist_partial") else "all E", "method": item["executor"],
            "importance": importance, "weight": WEIGHT[importance], "source": "v2-E", "executor_hint": key})
    for rid, family, category, importance, requirement, evidence, applies, method in V3_NEW:
        rows.append({"id": rid, "family": family, "category": category, "requirement": requirement,
            "evidence": evidence, "applies_when": applies, "method": method,
            "importance": importance, "weight": WEIGHT[importance], "source": "v3-new", "executor_hint": rid})
    distilled_path = ROOT / "rubric_library" / "distilled.json"
    distilled = 0
    split = {
        "X-PR-001": [("X-PR-001a", "硬编码输入单元格使用题面指定的输入颜色"), ("X-PR-001b", "输入单元格颜色与计算单元格颜色不同")],
        "X-IF-001": [("X-IF-001a", "题面要求的每个交付文件均以指定文件名存在"), ("X-IF-001b", "每个交付文件的类型与题面指定类型一致，未以其他类型替代")],
    }
    if distilled_path.is_file():
        for item in json.loads(distilled_path.read_text()):
            importance = item["importance"] if item["importance"] in WEIGHT else MINOR
            parts = split.get(item["id"], [(item["id"], item["requirement"])])
            for rid, requirement in parts:
                rows.append({"id": rid, "family": item["family"], "category": item["category"],
                    "requirement": requirement, "evidence": item.get("evidence", ""),
                    "applies_when": item.get("applies_when", "all"), "method": item.get("method", "rule"),
                    "importance": importance, "weight": WEIGHT[importance],
                    "source": "distilled: " + str(item.get("source", "")), "executor_hint": rid,
                    "support": item.get("support")})
                distilled += 1
    for row in rows:
        row["category"] = normalize_category(row)
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate rubric id"
    assert {r["category"] for r in rows} == set(CATEGORIES), "category mapping must cover all nine categories"
    out = ROOT / "rubric_library"
    out.mkdir(exist_ok=True)
    (out / "library.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {}
    for r in rows:
        counts.setdefault(r["family"], {}).setdefault(r["importance"], 0)
        counts[r["family"]][r["importance"]] += 1
    source_counts = {}
    for r in rows:
        key = r["source"].split(":")[0]
        source_counts[key] = source_counts.get(key, 0) + 1
    family_names = {"BC": "BC 基础（B 时间与会计机制 × C 输出与估值结构）", "A": "A 行业与商业模式", "D": "D 多步修改",
        "E": "E 开放预测与 Monte Carlo", "W": "W 联网取数"}
    lines = ["# v3 统一 Rubric 库（完整版）", "",
        f"共 **{len(rows)}** 条。主需权重 3，次需权重 1。题目生成后由 LLM API 从本库逐条挑选具体 ID，程序再校验必选项与适用性。", "",
        "## 构成", "", "| 来源 | 条数 |", "|---|---:|"]
    labels = {"v2-shared": "v2 F/D 共享原子", "v2-E": "v2 E 评分项（去重后）", "v3-new": "v3 新增（B/C 扩展、A 行业、D、W）",
        "distilled": "外部 benchmark 蒸馏（BTB、BlueFin、FrontierFinance、EMB）"}
    for key, value in source_counts.items():
        lines.append(f"| {labels.get(key, key)} | {value} |")
    lines += ["", "去重说明：E 中与共享原子同义的 " + "、".join(f"`{k}`→`{v}`" for k, v in E_DUPLICATES.items()) + " 已合并。", "",
        "| 类别 | 主需 | 次需 | 合计 |", "|---|---:|---:|---:|"]
    for category in dict.fromkeys(r["category"] for r in rows):
        main = sum(r["category"] == category and r["importance"] == MAIN for r in rows)
        minor = sum(r["category"] == category and r["importance"] == MINOR for r in rows)
        lines.append(f"| {category} | {main} | {minor} | {main + minor} |")
    lines += ["", "字段说明：**具体要求**是可判定 0/1 的原子断言；**证据**是检查位置；**适用**决定挑选器能否选它；"
        "**方法** rule=程序检查，llm=单项 LLM 判定，agent=工具型 Agent 判定。", ""]
    categories = list(dict.fromkeys(r["category"] for r in rows))
    for category in categories:
        cat_rows = [r for r in rows if r["category"] == category]
        lines += [f"## {category}（{len(cat_rows)} 条）", "",
            "| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 | 来源 |", "|---|---|---|---|---|---|---|"]
        for r in cat_rows:
            cells = [r["id"], r["requirement"], r["evidence"], r["applies_when"], r["method"], r["importance"], r["source"]]
            lines.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |")
        lines.append("")
    (out / "LIBRARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"total": len(rows), "distilled": distilled, "by_family": counts, "by_source": source_counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
