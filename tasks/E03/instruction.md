# 塔吉特：已报上半年与残余下半年开放预测

你是信息截止日 **2025-09-16** 的估值分析师。只可使用 `/app/data/inputs.json` 和等价的 `/app/data/frozen_history.xlsx`；本题离线。禁止使用截止日后的披露、当前股价、现成目标价或市场一致预期。不存在唯一正确的开放假设或目标每股价值。

## 历史证据与五年模型

最近完整财年截止 2025-02-01。行业分析要求：结合可比销售、客流与客单价、季节性库存及假日权重分析。已报上半年是实际值，不得机械年化为全年。

建立五个财年的收入、经营利润（EBIT）、稀释 EPS 与 FCFF。解释收入增长、利润率、税率、D&A、CapEx、营运资本和股权桥的来源与适用日期。金额为百万美元，股数为百万股，EPS/每股价值为美元，比率为小数。股份支付是经营成本，不得加回 FCFF。经营 NWC = 流动资产−现金−短期投资−(流动负债−当期债务)。净债务只含当期及非当期债务；股权价值 = 企业价值 + 现金及短期投资 − 净债务。

每年 `reinvestment_component = D&A − CapEx − ΔNWC`；`FCFF = EBIT×(1−税率) + reinvestment_component`；`discount_factor = 1/(1+WACC)^discount_years`。终值采用 Gordon 公式，以 FY5 的 FCFF 为基期并折现到估值日；WACC 必须大于 g。年度变体折现年数为 1,2,3,4,5，FY1 是估值日后第一个完整预测年度。

### 已报 H1 与残余 H2（本题关键）

- 两个 `Reported_Periods` 离散季度是 FY1 已报实际，只相加一次；`Prior_Partial` 是上年同期 H1，用作残余预测基数。FY1 完整财年收入 = 已报 H1 收入 + 你预测的 H2 收入；EBIT 同理。
- FY1 的 da、capex、delta_nwc、reinvestment_component、fcff 均只指未报 H2。全年 FCFF 可另列，但 `fcff_y1` 与估值只能含 H2，不得把已报现金流再次折现。
- 确定性 H2 收入 = 上年同期 H2 收入 ×(1+本期增长)，H2 EBIT = H2 收入 × 本期 EBIT 利润率；D&A、CapEx 按 H2 收入比例计算。FY1 ΔNWC = 上年 FY0 经营性 NWC ×(FY1 全年收入/FY0 全年收入−1)，FY2 起 = 本年 NWC−上年 NWC。经营性 NWC = 流动资产−现金−短期投资−(流动负债−当期债务)。
- 从估值日 2025-09-16 到 FY1 完整财年末 2026-01-31 为 137 天，折现年数=0.375342465753，后续逐年加一。FCFF 已经只含 H2，不能再乘残余比例。
- 模拟的 FY1 trajectory.revenue/ebit/reinvestment/fcff 只含 H2，从上年同期 H2 基数起算；FY2–FY5 才是完整财年。模型 Outputs 中的 revenue/ebit/eps 仍是完整财年。

## 候选自写 Monte Carlo

编写并实际运行 `/app/output/simulate.py`：
`python3 /app/output/simulate.py --input /app/data/inputs.json --model /app/output/model.xlsx --output /app/output/simulation.json`

至少生成 **5,000 条有效路径**，声明 seed **2032**，采用可复现伪随机数发生器。分别抽样收入增长、EBIT 利润率、再投资强度和折现率，不能直接抽每股价值或股价。声明支持的分布（triangular/uniform/normal/lognormal/beta）、数值参数、单位和有限上下界；保留合法抽样并单列拒绝数。增长与利润率要有非零相关性，或说明独立性的证据及局限；给出声明的相关矩阵及所有四个驱动的实际相关矩阵。模拟边界应能从历史波动或明确的压力情景推导。

`simulation.json` 顶层必须含：`seed`、`n_valid`、`n_rejected`、`method`、`drivers`、`dependence`、`realized_correlation`、`trials`、`statistics`、`percentile_convention`、`limitations`。drivers 以四个精确键 `revenue_growth`、`ebit_margin`、`reinvestment_intensity`、`discount_rate` 为索引，每项含 distribution、parameters、unit、bounds。dependence 含 `ordered_names`、4×4 `matrix`，或 `type: independence` 与 explanation。每条 trial 含 `path_id`、上述四个驱动、`value_per_share` 和五行 `trajectory`；每年含 `year/revenue/ebit/reinvestment/fcff/discount_factor`。路径 reinvestment 是资本开支加营运资本增加减 D&A（正值消耗现金），故 `fcff=ebit×(1−tax)−reinvestment`。增长与利润率在一条路径内保持不变；再投资=当年 trajectory.revenue×reinvestment_intensity。终值以 FY5 路径 FCFF 计算，采用该路径折现率。每条路径必须可由评分器独立重算，不能只提交摘要。分位数采用 `(N−1)q` 线性插值或 `nearest_r` 并如实声明。

## 交付物与说明

提交 `/app/output/model.xlsx`：保留公开工作簿的 `Outputs` 页，并建立 `Assumptions`、`Forecast`、`DCF` 页。Outputs 的 A 列为题给键，C 列必须是活公式；历史、五个预测年度、估值输出均链接到模型，模拟统计链接到 `MC_Trials`。Assumptions 的 A/B 列分别放键和数值，至少包括：`initial_growth`、`terminal_revenue_growth`、`steady_ebit_margin`、`tax_rate`、`da_to_revenue`、`capex_to_revenue`、`nwc_to_revenue`、`interest_rate`、`wacc`、`terminal_growth`、`net_debt`、`cash_and_investments`、`diluted_shares`。Forecast 的 A 列为键，C:G 为 FY1–FY5；必须包含 revenue、ebit、eps、da、capex、delta_nwc、reinvestment_component、fcff、discount_factor。经营预测、再投资、DCF 和股权桥不能粘贴固定结果；评分会实际修改 WACC 与 g 并重算。

另交 `simulation.json`、`simulate.py`、`memo.md`。memo 不超过 700 个空白分隔词，中文撰写：逐项给出至少三个历史行名/期间/数值/SEC_XBRL 来源，说明可复现的假设推导、公司特定经营因果链、再投资理由、模拟边界与相关性选择，并明确预测不确定性及模型局限。模拟区间是模型条件 DCF 分布，不是股价预测。评分器会重新执行模拟器并独立检查分布、相关性、全部路径算术和分位数；未来实际值及未来股价只在隐藏诊断中出现，不进入评分。
