# 迪尔：农机周期与开放预测

你是信息截止日 **2024-12-26** 的估值分析师。只可使用 `/app/data/inputs.json` 和等价的 `/app/data/frozen_history.xlsx`；本题离线。禁止使用截止日后的披露、当前股价、现成目标价或市场一致预期。不存在唯一正确的开放假设或目标每股价值。

## 历史证据与五年模型

最近完整财年截止 2024-10-27。行业分析要求：结合设备销量、价格与产品组合、生产库存、更新周期及经销商库存分析；区分周期性收入/利润率风险与长期再投资需求。

建立五个财年的收入、经营利润（EBIT）、稀释 EPS 与 FCFF。解释收入增长、利润率、税率、D&A、CapEx、营运资本和股权桥的来源与适用日期。金额为百万美元，股数为百万股，EPS/每股价值为美元，比率为小数。股份支付是经营成本，不得加回 FCFF。经营 NWC = 流动资产−现金−短期投资−(流动负债−当期债务)。净债务只含当期及非当期债务；股权价值 = 企业价值 + 现金及短期投资 − 净债务。

每年 `reinvestment_component = D&A − CapEx − ΔNWC`；`FCFF = EBIT×(1−税率) + reinvestment_component`；`discount_factor = 1/(1+WACC)^discount_years`。终值采用 Gordon 公式，以 FY5 的 FCFF 为基期并折现到估值日；WACC 必须大于 g。年度变体折现年数为 1,2,3,4,5，FY1 是估值日后第一个完整预测年度。

## 候选自写 Monte Carlo

编写并实际运行 `/app/output/simulate.py`：
`python3 /app/output/simulate.py --input /app/data/inputs.json --model /app/output/model.json --output /app/output/simulation.json`

至少生成 **5,000 条有效路径**，声明 seed **1931**，采用可复现伪随机数发生器。分别抽样收入增长、EBIT 利润率、再投资强度和折现率，不能直接抽每股价值或股价。声明支持的分布（triangular/uniform/normal/lognormal/beta）、数值参数、单位和有限上下界；保留合法抽样并单列拒绝数。增长与利润率要有非零相关性，或说明独立性的证据及局限；给出声明的相关矩阵及所有四个驱动的实际相关矩阵。模拟边界应能从历史波动或明确的压力情景推导。

`simulation.json` 顶层必须含：`seed`、`n_valid`、`n_rejected`、`method`、`drivers`、`dependence`、`realized_correlation`、`trials`、`statistics`、`percentile_convention`、`limitations`。drivers 以四个精确键 `revenue_growth`、`ebit_margin`、`reinvestment_intensity`、`discount_rate` 为索引，每项含 distribution、parameters、unit、bounds。dependence 含 `ordered_names`、4×4 `matrix`，或 `type: independence` 与 explanation。每条 trial 含 `path_id`、上述四个驱动、`value_per_share` 和五行 `trajectory`；每年含 `year/revenue/ebit/reinvestment/fcff/discount_factor`。路径 reinvestment 是资本开支加营运资本增加减 D&A（正值消耗现金），故 `fcff=ebit×(1−tax)−reinvestment`。增长与利润率在一条路径内保持不变；再投资=当年 trajectory.revenue×reinvestment_intensity。终值以 FY5 路径 FCFF 计算，采用该路径折现率。每条路径必须可由评分器独立重算，不能只提交摘要。分位数采用 `(N−1)q` 线性插值或 `nearest_r` 并如实声明。

## 交付物与说明

提交 `/app/output/model.json`，包含对象 `historical`、`assumptions`、`forecast`、`valuation`、`simulation_summary`。historical 使用 Outputs 同名历史键；assumptions 至少包含 `initial_growth`、`terminal_revenue_growth`、`steady_ebit_margin`、`tax_rate`、`da_to_revenue`、`capex_to_revenue`、`nwc_to_revenue`、`interest_rate`、`wacc`、`terminal_growth`、`net_debt`、`cash_and_investments`、`diluted_shares`。forecast 每年包含 `revenue_y1`…`revenue_y5`、`ebit_y*`、`eps_y*`、`da_y*`、`capex_y*`、`delta_nwc_y*`、`reinvestment_component_y*`、`fcff_y*`、`discount_factor_y*`；H1 变体另含实际/残余键。valuation 包含 WACC、g、税率、净债务、现金及投资、稀释股数、企业/股权/每股价值、`discount_years` 五元素数组和 `terminal_year_fcff`；simulation_summary 含 `n_valid`、`p10/p25/p50/p75/p90/mean`。另交 `/app/output/recompute.py`，接受 `--input INPUT --model MODEL --output DIR` 并写 `recomputed.json`。它必须从上述经营假设和公开历史重建每年收入、EBIT、再投资及估值，不得只回显 forecast/valuation 的既有结果。评分会修改经营假设和 WACC/g 后独立执行。

另交 `simulation.json`、`simulate.py`、`memo.md`。memo 不超过 700 个空白分隔词，中文撰写：逐项给出至少三个历史行名/期间/数值/SEC_XBRL 来源，说明可复现的假设推导、公司特定经营因果链、再投资理由、模拟边界与相关性选择，并明确预测不确定性及模型局限。模拟区间是模型条件 DCF 分布，不是股价预测。评分器会重新执行模拟器并独立检查分布、相关性、全部路径算术和分位数；未来实际值及未来股价只在隐藏诊断中出现，不进入评分。
