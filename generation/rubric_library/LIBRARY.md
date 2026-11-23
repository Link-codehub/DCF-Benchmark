# v3 统一 Rubric 库（完整版）

共 **200** 条。主需权重 3，次需权重 1。题目生成后由 LLM API 从本库逐条挑选具体 ID，程序再校验必选项与适用性。

## 构成

| 来源 | 条数 |
|---|---:|
| v2 F/D 共享原子 | 48 |
| v2 E 评分项（去重后） | 28 |
| v3 新增（B/C 扩展、A 行业、D、W） | 59 |
| 外部 benchmark 蒸馏（BTB、BlueFin、FrontierFinance、EMB） | 65 |

去重说明：E 中与共享原子同义的 `deliver_output_keys`→`01-KEYS`、`dcf_terminal`→`05-TV`、`dcf_equity`→`05-BRIDGE`、`formula_recalc`→`06-RECALC`、`formula_live`→`06-FORMULA`、`mc_paths`→`07-PATHS`、`mc_quantiles`→`07-QUANTILE` 已合并。

| 类别 | 主需 | 次需 | 合计 |
|---|---:|---:|---:|
| 交付与来源完整性 | 14 | 4 | 18 |
| 多步状态与业务重构 | 10 | 2 | 12 |
| 历史与会计口径 | 18 | 2 | 20 |
| 经营预测 | 40 | 13 | 53 |
| 三表勾稽 | 4 | 0 | 4 |
| DCF与估值桥 | 17 | 4 | 21 |
| 公式与模型工程 | 17 | 12 | 29 |
| 开放假设与模拟 | 8 | 2 | 10 |
| 表达与专业可用性 | 3 | 30 | 33 |

字段说明：**具体要求**是可判定 0/1 的原子断言；**证据**是检查位置；**适用**决定挑选器能否选它；**方法** rule=程序检查，llm=单项 LLM 判定，agent=工具型 Agent 判定。

## 交付与来源完整性（18 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 | 来源 |
|---|---|---|---|---|---|---|
| 01-FILE | 按要求提交可读取的 Excel 工作簿 | /app/output.xlsx | all | rule | 主需 | v2-shared |
| 01-KEYS | 每一个要求的语义输出键均存在且只有一个数值 | Outputs 或语义键映射 | all | rule | 主需 | v2-shared |
| 01-UNIT | 金额、股数与比率的单位在提交中明确 | 工作簿表头与单位标签 | all | agent | 次需 | v2-shared |
| E-deliver_model | The required primary model artifact exists and parses. | /app/output/model.xlsx or model.json | all E | rule | 主需 | v2-E |
| E-deliver_simulator | The candidate-owned simulate.py exists and parses. | /app/output/simulate.py | all E | rule | 主需 | v2-E |
| E-deliver_trials | simulation.json exists and has the required top-level schema. | simulation.json | all E | rule | 主需 | v2-E |
| E-deliver_memo | memo.md exists and is no more than 700 words. | memo.md | all E | rule | 次需 | v2-E |
| W-VALUE | 每个要求取数的值与指定权威来源一致（在题面容差内） | 取数表 | all W | rule | 主需 | v3-new |
| W-SOURCE | 每个取数注明来源文件、期间和字段或页码，且来源属于允许范围 | 取数表 | all W | rule | 主需 | v3-new |
| W-CROSS | 至少一项关键数据用第二个独立来源或勾稽关系交叉验证 | 交叉验证表 | all W | rule | 主需 | v3-new |
| W-USED | 取到的数被模型公式实际引用，而不是另行手填 | 模型引用关系 | all W | rule | 主需 | v3-new |
| W-NOFORBID | 未使用禁止来源或截止日后的信息 | 取数记录 | all W | agent | 主需 | v3-new |
| W-FAILURE | 取数失败或数据冲突时如实披露并说明处理方法 | memo.md | all W | llm | 次需 | v3-new |
| X-FM-012 | 最终交付不存在 TBD、TODO、fix this、草稿标记、未解析占位符或游离调试单元格。 | 全部交付文件的可见文本、批注与单元格扫描 | 交付最终模型或展示材料 | agent | 次需 | distilled: BankerToolBench（707cba99:68、85670d9d:119 等，Risk & Compliance） |
| X-FM-014 | 交付文件的可见文本及链接中不存在指向其他公司或其他项目的遗留引用。 | 全部交付文件的文本、链接与图表引用 | 基于模板或既有工作簿交付 | agent | 主需 | distilled: BankerToolBench（4e23ce4e:93，Risk & Compliance） |
| X-IF-001a | 题面要求的每个交付文件均以指定文件名存在 | 交付文件清单、扩展名与题面文件要求 | 题面指定文件类型、文件名或交付文件组合 | rule | 主需 | distilled: BankerToolBench（e3c47ea1:32、a31173e3:43 等，Instruction Following） |
| X-IF-001b | 每个交付文件的类型与题面指定类型一致，未以其他类型替代 | 交付文件清单、扩展名与题面文件要求 | 题面指定文件类型、文件名或交付文件组合 | rule | 主需 | distilled: BankerToolBench（e3c47ea1:32、a31173e3:43 等，Instruction Following） |
| X-IF-002 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | 工作簿 sheet 清单与题面结构要求 | 题面指定工作表名称、数量或保留结构 | rule | 主需 | distilled: BankerToolBench（bc55d3e8:39、8a19d926:33 等，Instruction Following） |

## 多步状态与业务重构（12 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 | 来源 |
|---|---|---|---|---|---|---|
| 01-HISTORY | 原始历史事实未被覆盖或删除 | 历史原始事实页 | D 所有后续步骤 | rule | 主需 | v2-shared |
| 08-OLD | 后续工作簿保留事件前原始输入与状态 | 历史/前步状态 | D 所有后续步骤 | rule | 主需 | v2-shared |
| 08-REBASE | 新实际值重定基期而非覆盖历史 | 重定基期行 | 重定基期事件 | rule | 主需 | v2-shared |
| 08-DISPOSE | 处置后的收入、资产、债务同步移除 | 事件重述 | 剥离事件 | rule | 主需 | v2-shared |
| 08-REFINANCE | 融资和资本开支事件同时更新对应滚动表 | 事件后预测 | 融资或资本开支事件 | rule | 主需 | v2-shared |
| 08-RESTATE | 事件后的 FCFF 与股权桥使用更新后的依赖 | 事件后估值 | D 所有后续步骤 | rule | 主需 | v2-shared |
| D-FINAL-VALUES | 最后一步工作簿的全部输出键与最终独立真值一致 | 最终工作簿 | all D | rule | 主需 | v3-new |
| D-FINAL-LIVE | 最后一步结果仍为活公式，隐藏扰动可传导 | 最终工作簿与扰动 | all D | rule | 主需 | v3-new |
| D-STEP-SNAPSHOT | 每一步都保存了独立快照 | 各步 pre/post 快照 | all D | rule | 主需 | v3-new |
| D-STEP-VALUES | 每一步快照的输出与该步独立真值一致 | 各步快照 | all D | rule | 主需 | v3-new |
| D-STEP-SCOPE | 每一步只修改该步要求涉及的依赖，未触及的输出保持不变 | 相邻快照差异 | all D | rule | 次需 | v3-new |
| D-STEP-LOG | 说明中逐步记录修改内容及影响 | memo.md | all D | llm | 次需 | v3-new |

## 历史与会计口径（20 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 | 来源 |
|---|---|---|---|---|---|---|
| 02-FY | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | 历史聚合与原始期间 | 非年度历史 | rule | 主需 | v2-shared |
| 02-LTM | LTM 恰包含要求的季度或半年，未重复年化 | 历史聚合与估值日 | 非年度历史 | rule | 主需 | v2-shared |
| 02-REPORTED | 非经常收益未混入规范化经营 EBIT | 历史披露与调整 | 规范化历史 | rule | 主需 | v2-shared |
| 02-SBC | 股份支付作为经营成本处理且未在 FCFF 中加回 | 历史成本与 FCFF 依赖 | SBC | rule | 主需 | v2-shared |
| 02-COLLECT | 现金收款等于确认收入加合同负债增加 | 现金收款与递延收入 | 合同负债 | rule | 次需 | v2-shared |
| E-hist_revenue | FY0 revenue equals the frozen SEC fact within 0.1%. | Outputs.hist_revenue_fy0 or model.json historical | all E | rule | 主需 | v2-E |
| E-hist_ebit | FY0 EBIT equals the frozen SEC fact within 0.1%. | Outputs.hist_ebit_fy0 or model.json historical | all E | rule | 主需 | v2-E |
| E-hist_eps | FY0 diluted EPS equals the frozen SEC fact within 0.1%. | Outputs.hist_eps_fy0 or model.json historical | all E | rule | 次需 | v2-E |
| E-hist_partial_revenue | The actual partial revenue equals the sum of listed discrete quarters, without YTD double-counting. | actual_partial_revenue_y1 | E 残余期变体 | rule | 主需 | v2-E |
| E-hist_partial_residual_boundary | Residual FY1 revenue equals full FY1 revenue minus actual partial revenue. | residual_revenue_y1 | E 残余期变体 | rule | 主需 | v2-E |
| B-MIXLTM | 混合历史 LTM 由最近完整半年加其后桥接季度构成，不重复计入、不遗漏、不年化 | 历史聚合与原始期间 | 混合历史拼接 | rule | 主需 | v3-new |
| X-IN-001 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | 输入假设区、输入包及输入映射 | 题面提供输入值 | rule | 主需 | distilled: BankerToolBench（707cba99:12–14 等，Instruction Following）；FrontierFinance（Historical Data Accuracy） |
| X-IN-002 | 题面指定的恒定输入在其每个适用期间均被原样采用，不出现未经指定的期间变化。 | 假设区与各预测期驱动行 | 题面规定某输入在多个期间保持不变 | rule | 主需 | distilled: BankerToolBench（4e23ce4e:115 等，Instruction Following） |
| X-IN-003 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | 历史窗口、输入推导公式与独立重算 | 题面指定历史推导窗口或公式 | rule | 主需 | distilled: BankerToolBench（707cba99:38 等，Transparency & Auditability）；BlueFin（Formula Correctness） |
| X-IN-004 | 每项模型输入的适用日期均不晚于题面规定的信息截止日。 | 输入来源记录、适用日期与估值截止日 | 题面规定信息截止日 | agent | 主需 | distilled: BankerToolBench（4e23ce4e:74 等，Instruction Following） |
| X-IN-005 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | 历史输入表、期间标签与原始报表 | 使用外部历史财务数据 | rule | 主需 | distilled: BankerToolBench（8a19d926:52 等，Instruction Following）；FrontierFinance（row-1、row-2，Correct Filing and Correct Period） |
| X-IN-006 | 估值桥或比较价格使用题面基准日当天或之前最近一个可用值。 | 估值桥输入、行情或资本化数据的日期 | 使用行情、债务、现金或资本化时点数据 | rule | 主需 | distilled: BankerToolBench（4e23ce4e:69、7f5b9960:108 等，Transparency & Auditability） |
| X-IN-007 | 模型的预测期序列与题面指定的起止期间完全一致。 | 模型期间表头与题面预测区间 | 题面指定显性预测期 | rule | 主需 | distilled: BankerToolBench（707cba99:1 等，Instruction Following）；BlueFin（Formula Correctness）；FrontierFinance（row-1，Pre-Scoring Gating Condition / Correct Filing and Correct Period） |
| X-IN-008 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | 历史与预测列的行标签及公式比较 | 模型同时展示历史期与预测期 | rule | 主需 | distilled: BankerToolBench（7f5b9960:92、960dc224:76 等，Internal Consistency） |
| X-IN-009 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | 历史区单元格内容与输入包对照 | 在历史数据旁构建预测 | rule | 主需 | distilled: BankerToolBench（e3c47ea1:81、bc55d3e8:120 等，Instruction Following、Transparency & Auditability） |

## 经营预测（53 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 | 来源 |
|---|---|---|---|---|---|---|
| 03-DRIVER | 期末经营基数等于期初减流失加新增 | 经营预测期 | 存量驱动 | rule | 主需 | v2-shared |
| 03-AVERAGE | 收入采用平均经营基数乘以单位收入及期间活动比例 | 收入预测 | 存量驱动 | rule | 主需 | v2-shared |
| 03-MARGIN | 各期 EBIT 使用本期的分部或核心利润率 | EBIT 预测 | all | rule | 主需 | v2-shared |
| 03-CAPEX | 资本开支同时包含强度部分与重排新增部分 | 资本开支预测 | 资本开支重排 | rule | 次需 | v2-shared |
| 03-NWC | 营运资本变动使用正确期初、期末与符号 | 营运资本表 | all | rule | 主需 | v2-shared |
| 03-DAYS | 应收、存货与应付使用实际年度天数口径 | 营运资本表 | 营运资本天数法 | rule | 次需 | v2-shared |
| 03-DEBT | 借款、偿还、利息和期末债务连续滚动 | 债务表 | 债务计划表 | rule | 主需 | v2-shared |
| 03-LEASE | 使用权资产与租赁负债的口径一致 | 租赁滚动与股权桥 | 租赁 | rule | 次需 | v2-shared |
| 03-NOL | NOL 使用不得超过正 EBIT 或可用余额 | 税务滚动 | NOL | rule | 次需 | v2-shared |
| E-forecast_revenue | Each of the five full-year revenue forecasts is positive and finite. | Forecast revenue_y1..y5 | all E | rule | 次需 | v2-E |
| E-forecast_ebit | Each forecast EBIT is finite and its implied margin is between -50% and 70%. | Forecast ebit_y1..y5 | all E | rule | 次需 | v2-E |
| E-forecast_reinvestment | Each reinvestment component equals D&A minus CapEx minus the change in NWC. | Forecast da/capex/delta_nwc/reinvestment_component | all E | rule | 主需 | v2-E |
| E-llm_business_chain | The forecast states a company-specific operating causal chain that can explain the direction of revenue and EBIT, rather than generic extrapolation. | one-atom judge packet with public business prompt and model values | all E | llm | 主需 | v2-E |
| E-llm_reinvestment_reasoning | The reasoning explains why the operating growth and margin case requires the modeled D&A, capital expenditure and working-capital reinvestment. | one-atom judge packet with numeric reinvestment reconciliation | all E | llm | 主需 | v2-E |
| B-NWC-OPEN | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | 营运资本表首期 | all | rule | 主需 | v3-new |
| B-INTANG-ROLL | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | 无形资产滚动表 | 双资产池 | rule | 主需 | v3-new |
| C-SOTP-SEG | 每个分部有独立的收入、利润率、再投资和 FCFF | 分部预测表 | 分部 SOTP | rule | 主需 | v3-new |
| C-SOTP-VAL | 每个分部按题面指定方法（DCF 或倍数）单独估值 | 分部估值表 | 分部 SOTP | rule | 主需 | v3-new |
| C-SOTP-SUM | SOTP 企业价值等于各分部价值之和，公司层费用按题面处理 | SOTP 汇总 | 分部 SOTP | rule | 主需 | v3-new |
| C-SOTP-BRIDGE | 净债务与稀释股数只在公司层扣减一次，不在分部重复扣减 | SOTP 股权桥 | 分部 SOTP | rule | 主需 | v3-new |
| C-PIPE-TIMING | 未投产或未上市项目在投产日前不产生收入 | 项目时间轴 | 风险调整管线 | rule | 主需 | v3-new |
| C-PIPE-CAPEX | 建设期支出与投产期收入分别建模并计入对应期间 | 项目现金流 | 风险调整管线 | rule | 主需 | v3-new |
| C-PIPE-PROB | 成功概率作用于项目现金流或项目价值，不通过调整 WACC 体现 | 风险调整 FCFF | 风险调整管线 | rule | 主需 | v3-new |
| C-PIPE-SUM | 公司价值等于各项目风险调整价值之和加已有业务价值 | 管线汇总 | 风险调整管线 | rule | 主需 | v3-new |
| A-DRIVER | 收入由该行业规定的业务驱动构造，而不是单一增长率 | 收入预测 | all A | rule | 主需 | v3-new |
| A-METRIC | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | 行业指标表 | all A | rule | 主需 | v3-new |
| A-VALUATION | 估值方法适配行业（金融用股权现金流或超额收益，房地产用 NOI/NAV 等），不硬套 FCFF | 估值表 | 金融、保险、房地产 | rule | 主需 | v3-new |
| A-REASON | 说明中解释行业驱动与估值结果之间的因果链 | memo.md | all A | llm | 次需 | v3-new |
| A-SAAS-ARR | 期末 ARR 等于期初 ARR 乘净留存率加新签 ARR，收入按期初期末 ARR 平均确认 | ARR 滚动表 | 软件与订阅 | rule | 主需 | v3-new |
| A-SAAS-CAPRD | 资本化研发作为无形资产新增扣减 FCFF，摊销加回 | 研发资本化表 | 软件与订阅 | rule | 次需 | v3-new |
| A-RETAIL-SSS | 收入拆为可比门店同店增长与新开店贡献，新店按开业月份折算 | 门店收入表 | 消费零售与连锁 | rule | 主需 | v3-new |
| A-MFG-UTIL | 产量不超过有效产能乘利用率上限，扩产在投产后才增加产能 | 产能表 | 制造与工业设备 | rule | 主需 | v3-new |
| A-MFG-YIELD | 合格产量等于投入量乘良率，良率在产量和成本链中只作用一次 | 投入量、良率、合格产量及销售率 | BOM 制造 | rule | 主需 | v3-new |
| A-MFG-BOM | 各产品各物料耗用量等于投入量乘 BOM 单耗，耗用成本等于耗用量乘采购价，不以收入成本率替代 | 分产品分物料 BOM 明细 | BOM 制造 | rule | 主需 | v3-new |
| A-MFG-PURCHASE | 采购与耗用及原材料滚动勾稽，采购不得直接作为 COGS | 采购、耗用、原材料和 COGS | BOM 制造 | rule | 主需 | v3-new |
| A-MFG-INVENTORY | 原材料、在制品和产成品分别按题面口径滚动，不合并为单一收入比例 | 三类存货期初、变动和期末 | BOM 制造 | rule | 主需 | v3-new |
| A-PHARMA-FUNNEL | 各管线收入由患者基数、诊断及适用比例、渗透率、依从性和净价格逐期构建 | 患者漏斗、治疗人次、净价格和收入 | 医药与生物科技 | rule | 主需 | v3-new |
| A-PHARMA-COMMITRD | 上市前承诺研发投入不乘 PoS，已实现费用不因上市延迟删除 | 研发费用表、PoS 及上市时点 | 研发管线 | rule | 主需 | v3-new |
| A-PHARMA-COMMERCIAL | 已商业化产品不重复乘研发成功概率 | commercial 现金流与 PoS 开关 | 研发管线 | rule | 主需 | v3-new |
| A-PHARMA-CLIFF | 专利到期后收入按题面侵蚀曲线下降，不延续到期前增长 | 产品收入表 | 医药与生物科技 | rule | 主需 | v3-new |
| A-HEALTH-PAYER | 收入按服务量乘各支付方单价加权，支付方结构变化影响均价 | 服务收入表 | 医疗服务 | rule | 次需 | v3-new |
| A-BANK-NII | 净利息收入等于平均生息资产乘净息差，资产增长受资本充足率约束 | 银行损益表 | 银行与金融 | rule | 主需 | v3-new |
| A-BANK-EQUITY | 使用股权现金流或超额收益模型，以股权成本折现 | 银行估值表 | 银行与金融 | rule | 主需 | v3-new |
| A-INS-CR | 承保利润等于已赚保费乘一减综合成本率，投资收益单独计算 | 保险损益表 | 保险 | rule | 主需 | v3-new |
| A-ENERGY-DECLINE | 现有储量产量按递减曲线下降，新增产量依赖开发资本开支 | 产量表 | 能源与资源 | rule | 主需 | v3-new |
| A-UTIL-RAB | 允许收入等于受监管资产基数乘允许回报率加折旧回收 | 监管收入表 | 公用事业与基础设施 | rule | 主需 | v3-new |
| A-TRANS-LOAD | 收入等于运力乘载运率乘单位收益，机队扩张伴随资本开支 | 运量表 | 交通与物流 | rule | 次需 | v3-new |
| A-PLAT-ARPU | 收入等于平均用户乘 ARPU，内容或流量成本按题面摊销 | 用户收入表 | 互联网平台与媒体 | rule | 次需 | v3-new |
| A-RE-NAV | 物业价值等于 NOI 除以资本化率，NAV 扣除负债 | NAV 表 | 房地产 | rule | 主需 | v3-new |
| A-SVC-UTIL | 收入等于计费人员乘利用率乘人均费率，人员成本与人数联动 | 人员收入表 | 专业服务与外包 | rule | 次需 | v3-new |
| A-EAAS-BASE | 服务收入由装机基数乘服务频次乘单价构成，续约率影响装机留存 | 装机表 | 设备即服务与装机运维 | rule | 次需 | v3-new |
| X-A-001 | 群组成员按题面规定的首次获得或首次交易期间确定，后续观察期变化不改变其原始群组归属。 | 客户/业务对象首次期间映射与群组公式 | 题面要求按获得期或首购期进行群组分析 | rule | 主需 | distilled: EMB（N004–N008、N019–N023，Cohort 切片） |
| X-A-002 | 分群汇总仅纳入观察期指标符合题面阈值的记录，各群计数与独立重算的相同阈值筛选结果一致。 | 观察期明细、阈值条件与分群计数公式 | 题面要求按观察期指标阈值分群计数 | rule | 主需 | distilled: EMB（N001–N003、N016–N018，阈值 Cohort 计数） |

## 三表勾稽（4 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 | 来源 |
|---|---|---|---|---|---|---|
| 04-BALANCE | 每个预测期资产等于负债加权益 | 资产负债表 | 三表 | rule | 主需 | v2-shared |
| 04-CASH | 资产负债表现金与现金流量表期末现金一致 | 现金流量表 | 三表 | rule | 主需 | v2-shared |
| 04-RE | 留存收益由净利润滚动且无不透明平衡项 | 权益滚动 | 三表 | rule | 主需 | v2-shared |
| 04-PPE | 长期资产由期初加新增减折旧摊销滚动 | 资产表 | 资产滚动 | rule | 主需 | v2-shared |

## DCF与估值桥（21 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 | 来源 |
|---|---|---|---|---|---|---|
| 05-FCFF | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | FCFF 表 | FCFF 口径 | rule | 主需 | v2-shared |
| 05-WACC | WACC 使用 CAPM 再杠杆和税后债务成本 | 折现率计算 | CAPM | rule | 主需 | v2-shared |
| 05-DF | 折现期从估值日按实际天数计量并遵守年中约定 | 折现时间表 | all | rule | 主需 | v2-shared |
| 05-DUAL | Gordon 与退出终值分别计算再按权重合成 | 终值计算 | 双终值 | rule | 主需 | v2-shared |
| 05-TV | 终值以最后完整年度为时点且以 WACC 折现 | 终值现值 | all | rule | 主需 | v2-shared |
| 05-BRIDGE | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | 股权桥 | all | rule | 主需 | v2-shared |
| 05-DILUTION | 库存股法增量与 RSU 均进入稀释股数 | 股数桥 | 稀释股数 | rule | 次需 | v2-shared |
| 05-VPS | 每股价值以股权价值除以稀释股数 | 估值结果 | all | rule | 主需 | v2-shared |
| 05-SENS | 敏感性单元格使用各自行列假设而经营预测不变 | 敏感性网格 | 估值敏感性 | rule | 次需 | v2-shared |
| 05-SCENARIO | 经营情景切换同时影响需求和利润率并传递至价值 | 情景结果 | 情景驱动 | rule | 主需 | v2-shared |
| E-dcf_fcff | Each FCFF equals EBIT times one minus tax plus the reinvestment component. | Forecast and DCF tax_rate | all E | rule | 主需 | v2-E |
| E-dcf_discount | Each discount factor equals one over one plus WACC raised to its stated actual-year fraction. | Forecast discount_factor and DCF discount_years | all E | rule | 主需 | v2-E |
| B-INTANG-FCFF | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | FCFF 表 | 双资产池 | rule | 主需 | v3-new |
| B-RESIDUAL | 首个预测段只计入估值日后的经营现金流 | 残余期 FCFF | all | rule | 主需 | v3-new |
| C-CASE-SWITCH | 单一情景开关切换后收入、利润率、再投资、FCFF、终值和每股价值同时改变 | Cases 页与 Operating Model | 情景驱动 | rule | 主需 | v3-new |
| C-CASE-ISOLATE | 每个情景的输出值与独立真值一致，情景之间不相互覆盖 | 情景结果表 | 情景驱动 | rule | 次需 | v3-new |
| C-MULTI-SPLIT | Gordon 与退出倍数估值分别给出，不只输出加权结果 | 估值结果 | 多方法估值 | rule | 主需 | v3-new |
| C-IMPLIED-MULT | 由 Gordon 终值反推的隐含 EV/EBITDA 计算正确 | 隐含倍数单元格 | 多方法估值 | rule | 主需 | v3-new |
| C-IMPLIED-G | 由退出倍数终值反推的隐含永续增长率计算正确 | 隐含增长率单元格 | 多方法估值 | rule | 主需 | v3-new |
| C-REVERSE | 由给定市场价格反推的隐含 WACC 或隐含增长假设正确，且以公式或求解过程得出 | 反推单元格 | 反向推导 | rule | 主需 | v3-new |
| C-RANGE | 估值区间的上下界分别来自题面指定的方法和假设范围 | Football Field 表 | 估值区间 | rule | 次需 | v3-new |

## 公式与模型工程（29 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 | 来源 |
|---|---|---|---|---|---|---|
| 06-FORMULA | 每个要求的结果单元格为活公式而非粘贴数值 | 结果单元格 XML/openpyxl | all | rule | 主需 | v2-shared |
| 06-RECALC | LibreOffice 重算后结果与独立真值一致 | 重算后的候选与 expected | all | rule | 主需 | v2-shared |
| 06-PERTURB1 | 第一组经营及估值/桥接扰动按依赖传导 | 隐藏扰动一 | all | rule | 主需 | v2-shared |
| 06-PERTURB2 | 第二组经营及估值/桥接扰动按依赖传导 | 隐藏扰动二 | all | rule | 主需 | v2-shared |
| 06-LINKS | 无外部工作簿链接或公式错误值 | 重算工作簿 | all | rule | 主需 | v2-shared |
| 06-FREE | 自由布局通过语义键发现而非行号评分 | 工作簿语义映射 | 自由或混合布局 | rule | 次需 | v2-shared |
| E-formula_perturb_wacc | A +0.5 percentage-point WACC perturbation decreases enterprise value. | fresh recalculation after WACC perturbation | all E | rule | 次需 | v2-E |
| E-formula_perturb_g | A +0.2 percentage-point terminal-growth perturbation increases enterprise value. | fresh recalculation after terminal-growth perturbation | all E | rule | 次需 | v2-E |
| X-FM-001 | 题面要求集中管理的每个业务假设均在假设区拥有独立的可见输入单元格。 | 假设区、输入单元格与模型公式 | 题面要求集中管理可调整假设 | rule | 主需 | distilled: BankerToolBench（7f5b9960:81、b957a435:82 等，Transparency & Auditability）；FrontierFinance（row-25，Assumptions） |
| X-FM-002 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | 计算公式 XML、公式常量扫描及输入引用 | 模型含可调业务或估值假设 | rule | 主需 | distilled: BankerToolBench（55fd995a:96 等，Transparency & Auditability）；FrontierFinance（row-66，No Hardcoded Values in Formulas） |
| X-FM-003 | 同一业务或估值假设仅有一个权威输入单元格，每个使用该假设的下游公式均可追溯至该单元格。 | 输入依赖图及重复硬编码扫描 | 同一假设被多个计算模块使用 | rule | 主需 | distilled: BankerToolBench（e3c47ea1:113、bc55d3e8:117 等，Internal Consistency） |
| X-FM-004 | 下游行项通过工作簿内活引用取得已在上游模块计算的对应值，未另行重填或独立重算。 | 跨表引用公式、上游输出行与下游行 | 题面要求集成已有计算模块或原始数据表 | rule | 主需 | distilled: BankerToolBench（a31173e3:97 等，Transparency & Auditability）；BlueFin（Model Integration）；FrontierFinance（Calculation Transparency and Auditability） |
| X-FM-005 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | 各计算区期间表头与逐列公式 | 多个计算区按期间排列 | rule | 主需 | distilled: BankerToolBench（c292330e:84、8a19d926:110 等，Internal Consistency） |
| X-FM-006 | 除题面明确允许的过渡期外，同一预测行各期公式具有相同的相对引用模式。 | 预测行公式 R1C1 规范化比较 | 多期预测使用同一计算逻辑 | rule | 次需 | distilled: BankerToolBench（b957a435:79、8a19d926:63 等，Technical Correctness）；BlueFin（Formula Correctness） |
| X-FM-007 | 估值计算链不存在未声明的循环引用。 | 公式依赖图与循环检测 | 交付 Excel 模型 | rule | 主需 | distilled: BankerToolBench（b957a435:134、bc55d3e8:113 等，Risk & Compliance）；FrontierFinance（row-73） |
| X-FM-008 | 题面要求有意循环计算时，模型具有可关闭该循环路径的明确开关。 | 循环开关单元格及开关前后的依赖路径 | 题面要求可控的循环计算 | rule | 次需 | distilled: BankerToolBench（b957a435:115、8a19d926:99 等，Risk & Compliance） |
| X-FM-009 | 影响估值输出的公式不使用 OFFSET、INDIRECT、NOW、TODAY、RAND 或 RANDBETWEEN。 | 估值依赖链公式文本 | 交付 Excel 估值模型 | rule | 次需 | distilled: BankerToolBench（707cba99:80、7f5b9960:74 等，Risk & Compliance） |
| X-FM-010 | 汇总、求和与折现公式的引用范围均有明确起止单元格，不包含整行或整列引用。 | SUM、NPV 及聚合公式范围 | 模型含区域汇总或折现公式 | rule | 次需 | distilled: BankerToolBench（707cba99:79、e3c47ea1:116 等，Risk & Compliance） |
| X-FM-011 | 分母可能为零或空值的除法公式具有 IF 分母判断或 IFERROR 保护。 | 除法公式及零/空分母情景 | 模型含可能为零或空的分母 | rule | 次需 | distilled: BankerToolBench（6a2f5cf8:115、ceba18d0:88 等，Risk & Compliance） |
| X-FM-013 | 模型计算逻辑所在区域不存在隐藏行或隐藏列。 | 工作表行列隐藏属性及计算依赖区 | 工作簿未获授权隐藏计算逻辑 | rule | 次需 | distilled: BankerToolBench（6801c651:110，Risk & Compliance） |
| X-FM-015 | 题面允许的有意循环计算在迭代重算后收敛，输出不随额外迭代发生超出题面容差的变化。 | 迭代设置与连续两次重算结果 | 题面允许循环计算 | rule | 主需 | distilled: BankerToolBench（b957a435:134、907e3e2e:120 等，Risk & Compliance） |
| X-IC-001 | 敏感性表中与基准行列假设相交的单元格，其值与模型相同口径基准输出的相对差异不超过题面容差；题面未给容差时为 0.1%。 | 敏感性轴、中心格与模型基准输出 | 敏感性网格包含全部基准假设组合 | rule | 主需 | distilled: BankerToolBench（e3c47ea1:44、960dc224:48 等，Internal Consistency）；FrontierFinance（row-60，Sensitivity Analysis） |
| X-IC-002 | 每条敏感性轴的完整值序列与题面指定的起点、终点及步长完全一致。 | 敏感性轴单元格与题面轴定义 | 题面规定敏感性轴或区间 | rule | 主需 | distilled: BankerToolBench（7f5b9960:54、bc55d3e8:29 等，Instruction Following）；FrontierFinance（row-60，Sensitivity Analysis） |
| X-IC-003 | 在现金流与永续增长率保持为正且 WACC 大于永续增长率时，敏感性网格中折现率单调上升对应估值结果不上升。 | 敏感性网格与对应变量重算 | 折现率敏感性的其余条件满足正终值分母 | rule | 次需 | distilled: BankerToolBench（e3c47ea1:51，Technical Correctness） |
| X-IC-004 | 敏感性轴中题面指定的基准假设位于该轴的中心位置。 | 敏感性轴值序列与题面基准假设 | 题面要求敏感性轴以基准假设为中心 | rule | 次需 | distilled: BankerToolBench（bc55d3e8:39、6801c651:43 等，Internal Consistency） |
| X-IC-005 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | 各估值方法的显性期现值引用与合计 | 同一模型使用多种终值方法 | rule | 主需 | distilled: BankerToolBench（7f5b9960:101，Internal Consistency）；FrontierFinance（row-57，Method Reconciliation and Preference） |
| X-IC-006 | 隐含价相对现价的溢价率按“隐含价 ÷ 同口径现价 − 1”计算，绝对差异不超过题面容差。 | 隐含价、现价与溢价/折价输出 | 要求输出相对现价的溢价、折价或上行空间 | rule | 主需 | distilled: BankerToolBench（7f5b9960:112 等，Internal Consistency）；BlueFin（Output Validation） |
| X-IC-008 | PDF 的页数、页面顺序及每页文字和数值与其 PPT 导出源逐页一致。 | PPT 与 PDF 逐页文本及页面对象映射 | 同时要求 PPT 及其 PDF 导出版本 | rule | 次需 | distilled: BankerToolBench（4e23ce4e:87、e3c47ea1:67 等，Internal Consistency） |
| X-IF-003 | 敏感性网格的每个结果值均与模型在相同行列输入下的重算值一致，容差按题面规定。 | 敏感性全网格、行列输入与逐格模型重算 | 要求敏感性网格基于完整模型逐格求值 | rule | 主需 | distilled: BankerToolBench（ceba18d0:103、73450a4d:83 等，Internal Consistency） |

## 开放假设与模拟（10 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 | 来源 |
|---|---|---|---|---|---|---|
| 07-ASSUME | 开放假设有可追溯的证据和适用日期 | 假设说明 | 开放假设 | llm | 主需 | v2-shared |
| 07-PATHS | 模拟路径满足数量、抽样和相关性约束 | 模拟试验 | Monte Carlo | rule | 主需 | v2-shared |
| 07-QUANTILE | 模拟分位数由试验样本独立计算 | 模拟摘要 | Monte Carlo | rule | 主需 | v2-shared |
| E-mc_seed | The declared seed equals the task seed. | simulation.json seed | all E | rule | 次需 | v2-E |
| E-mc_distributions | Every required driver has a supported distribution, legal numeric parameters, declared bounds, and sample statistics within method-aware tolerances. | drivers and trials | all E | rule | 主需 | v2-E |
| E-mc_dependence | The realized correlation matrix agrees with the declared dependence structure, or the independence explanation is supported by realized cross-driver correlations. | dependence and trials | all E | rule | 主需 | v2-E |
| E-mc_recompute | Every sampled path's DCF value independently recomputes from its drivers and the deterministic model within 0.5%. | trials and independent grader path arithmetic | all E | rule | 主需 | v2-E |
| E-mc_not_degenerate | The value distribution is non-degenerate and has more than 100 distinct values. | trials.value_per_share | all E | rule | 次需 | v2-E |
| E-llm_driver_derivation | The cited historical observations are explicitly connected to each material forecast driver by a reproducible derivation, not merely listed. | one-atom judge packet: memo, verified citations and deterministic forecast | all E | llm | 主需 | v2-E |
| E-agent_distribution_rationale | The selected uncertainty bounds and dependence rationale are justified from supplied historical evidence without invoking unavailable post-cutoff information. | agent group packet; read-only artifact and source-inspection tools | all E | agent | 主需 | v2-E |

## 表达与专业可用性（33 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 | 来源 |
|---|---|---|---|---|---|---|
| 09-MEMO | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | memo.md 说明文字 | all | llm | 次需 | v2-shared |
| 09-READABLE | 中间结构有明确期间与项目标签且不依赖未披露技巧 | 工作簿布局 | all | agent | 次需 | v2-shared |
| E-evidence_numeric_citations | At least three memo citations identify a real source, historical period, and value matching the frozen fact. | memo.md and public frozen inputs | all E | rule | 次需 | v2-E |
| E-evidence_limits | The memo explicitly discloses forecast uncertainty and the independence or correlation choice. | memo.md | all E | rule | 次需 | v2-E |
| E-agent_interval_interpretation | The interpretation distinguishes model-implied FCFF/DCF dispersion from a market-price forecast and states material simulation limitations. | agent group packet; read-only artifact and source-inspection tools | all E | agent | 次需 | v2-E |
| X-IC-007 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | 展示材料数值与模型输出映射 | 同时交付模型与展示或摘要材料 | agent | 主需 | distilled: BankerToolBench（e3c47ea1:65、8a19d926:110 等，Internal Consistency） |
| X-TA-001 | 每项外部输入均有可定位的来源记录，记录至少含文档或数据集名称及对应财务期间或数据日期。 | 输入来源字段、单元格批注或来源清单 | 使用题面之外的申报、行情或行业数据 | agent | 主需 | distilled: BankerToolBench（7f5b9960:110、85670d9d:99 等）；FrontierFinance（row-3，Source Compliance） |
| X-TA-002 | 每项非经常性调整均单独记录调整金额。 | 历史规范化调整表及原始披露 | 存在非经常性历史调整 | rule | 主需 | distilled: FrontierFinance（row-13，Non-Recurring Items and Accounting Treatment） |
| X-TA-003 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | 会计处理说明、调整表与相关报表公式 | 题面要求规范化或特定会计处理 | llm | 次需 | distilled: FrontierFinance（row-13，Non-Recurring Items and Accounting Treatment） |
| X-TA-004 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | 折现时间表与逐期折现公式 | 构建 DCF 折现模型 | agent | 次需 | distilled: BankerToolBench（4e23ce4e:67、7f5b9960:94 等）；FrontierFinance（row-33，Discount Period Timeline Table） |
| X-TA-005 | 用于外推或推导预测的历史锚定期间数值在模型中可见。 | 历史锚定列、预测驱动与公式引用 | 预测输入由历史数据外推或推导 | agent | 次需 | distilled: BankerToolBench（e3c47ea1:79、7f5b9960:123 等，Transparency & Auditability） |
| X-TA-006 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | FCFF 明细行及公式引用 | 题面要求展示 FCFF 构建 | agent | 次需 | distilled: BankerToolBench（a31173e3:46、6801c651:87 等，Client Readiness & Presentation） |
| X-TA-007 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | 终值计算区、终期指标行与假设单元格 | 使用 Gordon 或退出倍数终值 | agent | 次需 | distilled: BankerToolBench（a31173e3:96、960dc224:86 等，Transparency & Auditability） |
| X-TA-008 | 题面要求解释方法选择时，说明明确指出所选估值方法，并给出至少一项与该公司数据或模型结果对应的依据。 | 估值说明、方法比较表与公司特定输入 | 题面要求比较或选择估值方法 | llm | 次需 | distilled: FrontierFinance（row-57，Method Reconciliation and Preference） |
| X-TA-009 | 每个开放性预测假设均有书面推导，包含历史观察值及由该观察值到假设值的计算或映射关系。 | 假设说明、历史观察值与预测输入对照 | 预测假设需自行确定而非题面给定 | llm | 次需 | distilled: FrontierFinance（row-17、row-21、row-25，Operating Forecast）；BankerToolBench（85670d9d:99） |
| X-TA-010 | 按题面指定历史窗口推导的预测输入旁有可见的历史观察值或计算过程，能由该观察值复算得到预测输入。 | 历史观察值、预测输入推导公式与相邻说明 | 预测输入按题面给定规则从历史数据推导 | agent | 次需 | distilled: BankerToolBench（4e23ce4e:90、6801c651:85 等，Transparency & Auditability） |
| X-PR-001a | 硬编码输入单元格使用题面指定的输入颜色 | 输入及公式单元格字体/填充颜色与单元格类型 | 题面或建模规范要求输入颜色编码 | rule | 次需 | distilled: BankerToolBench（707cba99:27、7f5b9960:115 等，Client Readiness & Presentation） |
| X-PR-001b | 输入单元格颜色与计算单元格颜色不同 | 输入及公式单元格字体/填充颜色与单元格类型 | 题面或建模规范要求输入颜色编码 | rule | 次需 | distilled: BankerToolBench（707cba99:27、7f5b9960:115 等，Client Readiness & Presentation） |
| X-PR-002 | 工作簿公式单元格的字体颜色与题面规定的公式类型颜色映射一致。 | 同表及跨表公式、字体颜色 | 题面或建模规范要求区分公式与跨表链接 | rule | 次需 | distilled: BankerToolBench（707cba99:54、4e23ce4e:144 等，Client Readiness & Presentation） |
| X-PR-003 | 财务金额负数按题面约定以括号显示，不使用前导负号代替括号。 | 负数单元格数字格式与显示文本 | 题面或建模规范要求会计括号负数格式 | rule | 次需 | distilled: BankerToolBench（707cba99:55、7f5b9960:114 等，Client Readiness & Presentation） |
| X-PR-004 | 达到千位及以上的财务金额使用千分位分隔符显示。 | 财务金额单元格数字格式 | 题面或建模规范要求千分位格式 | rule | 次需 | distilled: BankerToolBench（4e23ce4e:48、85670d9d:129 等，Client Readiness & Presentation） |
| X-PR-005 | 每个规定输出的显示小数位数等于题面指定位数。 | 输出数字格式与显示值 | 题面指定显示小数位数 | rule | 次需 | distilled: BankerToolBench（4e23ce4e:42、bc55d3e8:117 等）；BlueFin（66497c9d-19bc-4ee9-a9c8-3665686b0ed8:d1ea811d-2153-46ca-915f-1162da9d5e2e，Presentation） |
| X-PR-006 | 估值倍数的显示格式与题面指定的倍数格式完全一致，包含指定的小数位数与 x 后缀。 | 倍数输出单元格数字格式 | 输出估值倍数 | rule | 次需 | distilled: BankerToolBench（7f5b9960:121、8a19d926:93 等，Client Readiness & Presentation） |
| X-PR-007 | 增长率、利润率、税率及折现率等比率输出以百分比格式显示。 | 比率输出行数字格式 | 输出比率或百分比指标 | rule | 次需 | distilled: BankerToolBench（bc55d3e8:128、c292330e:101 等，Client Readiness & Presentation） |
| X-PR-008 | 同一行各期间的数字格式一致。 | 逐行各期数字格式串比较 | 按期间展示同一指标 | rule | 次需 | distilled: BankerToolBench（7f5b9960:86、c292330e:86 等，Client Readiness & Presentation） |
| X-PR-009 | 可见表格的文本与数值未被列宽、行高或相邻对象遮挡，显示结果不含 #### 或截断标签。 | 工作簿及展示文件的显示长度、对象边界与截断检查 | 交付含可见表格的工作簿或展示文件 | agent | 次需 | distilled: BankerToolBench（e3c47ea1:68 等，Client Readiness & Presentation）；BlueFin（Pitfalls） |
| X-PR-010 | 题面要求 AA 对比度时，标题或副标题文字颜色与填充颜色的 WCAG 相对亮度对比度至少为 4.5:1。 | 标题单元格字体/填充色及对比度计算 | 题面要求 WCAG AA 文本对比度 | rule | 次需 | distilled: BlueFin（Pitfalls） |
| X-PR-011 | 数据区、输入区或计算区内不存在合并单元格。 | 工作表 merged_cells 范围与数据区映射 | 题面禁止计算或数据区域合并 | rule | 次需 | distilled: BankerToolBench（85670d9d:135、8a19d926:103 等，Client Readiness & Presentation） |
| X-PR-012 | 正文非空单元格使用题面指定的统一字体家族。 | 正文非空单元格字体属性 | 题面或建模规范规定统一字体 | rule | 次需 | distilled: BankerToolBench（7f5b9960:123、e3c47ea1:74 等，Client Readiness & Presentation） |
| X-PR-013 | 历史期与预测期通过 A/E 等期间标签、分组表头或视觉分隔明确区分。 | 期间表头、分组标签或分隔样式 | 历史期与预测期并列展示 | agent | 次需 | distilled: BankerToolBench（707cba99:63、bc55d3e8:126 等，Client Readiness & Presentation）；BlueFin（Presentation） |
| X-PR-014 | PPT 或 PDF 的页数与页面顺序符合题面指定的逐页内容要求。 | PPT/PDF 页数、页面文字与题面对照 | 题面指定 PPT 或 PDF 的逐页结构 | agent | 次需 | distilled: BankerToolBench（707cba99:29、907e3e2e:99 等，Instruction Following） |
| X-PR-015 | 模型标题区明确标识题面估值对象的名称或代码。 | 模型首页或分析页标题区文本 | 题面要求模型标识或封面 | agent | 次需 | distilled: BankerToolBench（707cba99:25、b957a435:118 等，Instruction Following）；BlueFin（66497c9d-19bc-4ee9-a9c8-3665686b0ed8:5ba92f78-f6ea-41a3-80b7-8de368733a3f，Presentation） |
| X-PR-016 | 指定输出区的打印区域、页面方向及缩放设置与题面逐项一致。 | 工作表 print_area、orientation 与 fitToWidth 设置 | 题面指定打印布局 | rule | 次需 | distilled: BankerToolBench（b8be8b2f:90，Client Readiness & Presentation） |
