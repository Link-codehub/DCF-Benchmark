# DCF Eval v3：题目、Rubrics 与生产过程（完整版）

> 本文从 `exp/dcf_factory_v3/` 的源文件直接生成：契约、外部代理提示词、全部题目的 spec 与中文题面、统一 rubric 库，以及每道题由 API 挑出的 rubric。不含隐藏真值和参考答案。

## 1. 总览

| 题族 | 题数 | 构成 |
|---|---:|---|
| BC | 16 | B 时间与会计机制 × C 输出与估值结构 |
| A | 9 | 固定 BC 基座 × 行业/商业模式 |
| D | 4 | 独立 BC 起点 + 3–4 次结构修改 |
| E | 4 | 真实公司冻结历史 + 开放假设 + 自写 Monte Carlo |
| W | 4 | 指定来源联网取数 + 建模 |
| R | 2 | 历史版本中模型低分题原样复用（v1 B01、v2 F01） |
| 合计 | 39 | |

统一 rubric 库共 **200** 条（主需权重 3，次需权重 1）。

## 2. 生产过程

```text
1. 总控写契约 CONTRACT.md（题族、B/C 菜单、A 行业分类、D/E/W 规则）
2. 统一 rubric 库：v2 共享原子 + v2 E 评分项（去重）+ v3 新增 + 外部 benchmark 蒸馏
3. 外部造题代理（Kimi Code CLI，kimi-k3.1-pro）
     CORE  → BC / A / D 题目、活公式参考、独立真值、验收
     OPEN  → E / W 题目、参考实现、评分器
     DISTILL → 外部约 2,380 条细则去重蒸馏
4. 每题生成后调用 LLM API（claude-opus-5-5）按类别分批，从库中逐条挑选 rubric ID；程序补齐必选项、剔除不适用与编造 ID
5. 参考答案重算、空白/静态负例验收
```

外部代理与当前总控会话不共享上下文，只读各自提示词和契约；造题不使用 Harbor，Harbor 只用于被测模型答题。

### 2.1 造题方法

| 题族 | 怎么造 | 怎么核验 |
|---|---|---|
| BC | 每题从 B 菜单抽 4–7 项、从 C 菜单抽 1 种结构；16 题须覆盖混合历史 LTM、双资产池、首期 ΔNWC 两种口径，以及 C 的全部七种结构 | 独立 Python 真值 + 活公式参考工作簿，LibreOffice 重算一致；两组隐藏扰动；空白/静态负例被拒 |
| A | 固定 3–4 个 BC 基座，每题抽 1 个行业大类 + 类内 2–3 个驱动；金融、保险、房地产使用行业适配估值 | 同 BC，另检查行业指标与行业估值口径 |
| D | 独立新生成一道 BC 结构题（不复用 BC 题族），再做 3–4 次结构性修改；每步保存快照 | 两层：最后一步完整真值与活公式；每一步快照对照该步真值、修改范围、历史未被篡改 |
| E | 选 4 家 v2 真实公司冻结历史，中文题面；答题者自写 Monte Carlo（≥5,000 路径、指定 seed） | 独立复算分布、相关性、路径算术与分位数；未来实际值与股价只作诊断 |
| W | 真实上市公司，限定 SEC/公司 IR/国债收益率取数后建模 | 取数值对照权威真值、来源可追溯、交叉验证、取数被模型引用、未用禁止来源 |
| R | 从历史版本挑真实模型得分低的题原样复用：R01=v1 B01 衡岳流体装备（Kimi 0.56/类别清零 0.44，Claude 0.25）；R02=v2 F01 企业档案订阅（Kimi 0.04–0.10，千问 0）。题面数据、参考答案与评分器沿用原版，只改编号与标题；rubric 由 Opus 5.5 从统一库重挑 | 原评分器在 v3 本地复验：参考 reward=1.0，空白工作簿被拒 |

题面写法：抽样结果只用于造题；题面不出现“B 项”“C 结构”“BC 基座”等标签，而是把抽到的时间口径、历史形式、难点与输出结构写成自然业务要求。

B 菜单：非自然财年；年度/半年/季度/混合历史拼接 LTM；FY 与 LTM 规范化；残余期＋4–6 期预测；实际天数与年中/期末折现；营运资本天数法或比例法及首期 ΔNWC 口径；D&A 比例、固定资产滚动或固定资产＋无形资产双资产池；Gordon/退出/双终值；完整股权桥；现金税与 NOL。

C 菜单：简版 DCF；三表＋DCF；分部经营模型＋SOTP；风险调整管线 DCF；情景驱动 Operating Model；多方法估值与反推（隐含倍数、隐含 g、隐含 WACC、估值区间）；债务计划表＋DCF。

A 行业大类：软件与订阅、消费零售与连锁、制造与工业设备、医药与生物科技、医疗服务、银行与金融、保险、能源与资源、公用事业与基础设施、交通与物流、互联网平台与媒体、房地产、专业服务与外包、设备即服务与装机运维。

### 2.2 Rubric 方法

1. **统一库**：v2 F/D 共享原子与 v2 E 评分项合并，去掉 7 条同义项；补 v3 新增（B/C 扩展、行业、多步、联网）；再从外部 benchmark 约 2,380 条细则蒸馏补缺。
2. **原子与唯一判定**：每条只判一个点，能无歧义判 0/1；复合条目拆开（如 X-PR-001、X-IF-001 各拆为两条）。
3. **主需/次需**：取消严重度，主需权重 3、次需权重 1。
4. **逐题挑选**：题目生成后调用 `claude-opus-5-5`，与造题模型不同家族；按类别分批提交候选，每批只挑适用的具体 ID 并给出理由。
5. **程序校验**：剔除不存在或不属于该题族的 ID；补齐各题族必选项（如 BC 的输出键、NWC、折现、终值、股权桥、活公式、重算、两组扰动、无外链）；记录哪些是 LLM 选的、哪些是程序补的。
6. **执行方法**：rule 由程序检查；llm 每条单独调用一次；agent 一次会话评同题一小组，必须留工具证据。

### 2.3 Rubric 库来源

| 来源 | 条数 |
|---|---:|
| v2 F/D 共享原子 | 48 |
| v2 E 评分项（去重后） | 28 |
| v3 新增（B/C 扩展、行业、多步、联网） | 59 |
| 外部 benchmark 蒸馏（BTB、BlueFin、FrontierFinance、EMB） | 65 |

### 2.4 外部 benchmark 蒸馏报告

##### DCF Eval v3 外部 rubric 蒸馏报告

##### 结果摘要

- 输入现有库 128 条；外部原始评分项 **2,380 条**；最终新增 **63 条**，全部 `family=BC`。
- 原始条目互斥处置：仅被现有库覆盖 **1,319 条**；含新点并在外部语料内部合并 **980 条**；因不原子、不可唯一判定或过度题目专属而删除 **81 条**。合计 **2,380 条**。
- 其中 **553 条**原始项同时含“现有库已覆盖原子”和“新增原子”；**1,441 条**含多个不同映射。因此原子映射数与原始条目处置数是不同口径，不能直接相加。
- 新增方法分布：`rule` 46、`agent` 14、`llm` 3；重要性分布：`主需` 29、`次需` 34。
- 未新增空泛的“合理、专业、清晰、有风险意识”要求；也没有把 BTB 的 `Risk & Compliance` 类别名误当作投资风险披露证据。

##### 来源与处置统计

| 来源 | 原始条目 | 仅现有库覆盖 | 含新点并合并 | 删除 | 新点支持数* | 至少获其支持的新 ID 数** |
|---|---:|---:|---:|---:|---:|---:|
| BankerToolBench | 2,218 | 1,227 | 917 | 74 | 1,134 | 57 |
| BlueFin | 39 | 27 | 12 | 0 | 16 | 10 |
| FrontierFinance | 73 | 29 | 37 | 7 | 49 | 16 |
| EMB | 50 | 36 | 14 | 0 | 14 | 2 |
| 合计 | 2,380 | 1,319 | 980 | 81 | 1,213 | 63（去重后） |

\* 新点支持数是“原始条目—新 ID”的映射数；同一原始条目可含多个独立检查。`distilled.json` 的 `support` 对同一原文支持同一新 ID 只计一次。
\** 一个新 ID 可得到多个来源支持，因此各来源的新 ID 数不能相加。

##### 聚类、泛化与去重方法

1. **结构化读取**：用 Python 解析 BTB 的 `aggregated_rubric_json`、BlueFin 的 `rubric.sections`、FrontierFinance CSV 与 EMB JSONL，按来源、类别、权重及原始 ID 建立索引；不把整段原文输出到对话上下文。
2. **主题聚类**：先按三表勾稽、历史与会计口径、经营预测、FCFF、WACC、终值、折现、股权桥、敏感性、公式工程、来源与审计、呈现、风险与合规等主题做多标签聚类；再对候选缺口逐条建立现有 ID／新 ID／删除原因映射。
3. **机制优先的语义去重**：数值答案和中间值断言优先归入 `06-RECALC`；扰动传导归入 `06-PERTURB1/2`；主链路公式与行业机制归入相应现有 ID。即使公司、年份、指标或金额不同，也不新增同义检查。
4. **原子拆分**：把输入采用与结果真值、输入集中与公式内嵌常数、循环存在与循环控制、敏感性轴与中心格、展示一致性与文件导出一致性分别处理。原始条目的多个原子可以分别映射到现有库和新库。
5. **删除与分档合并**：删除纯题目专属模板偏好、无客观比较对象的美观描述和不能无歧义判 0/1 的要求。FrontierFinance 同一子项的分数档按“是否存在可判定的检查点”合并，不按档数重复支持。
6. **适用范围控制**：呈现类检查仅在题面或建模规范明确要求时启用；EMB 群组检查仅在相应群组任务启用；E/W 专属条目不视为已经覆盖通用 BC 场景。

##### 现有库覆盖而不再新增的主要主题

| 主题 | 代表性现有 ID | 处理 |
|---|---|---|
| 数值输出、中间值与公式机制真值 | `06-RECALC`（映射 1,317 次） | 把具体公司、年度和金额泛化为独立重算，不新增同义断言。 |
| 隐藏扰动与状态切换 | `06-PERTURB1`、`06-PERTURB2`、`C-CASE-SWITCH` | 检查实际传导和重算，不把各输入的扰动分别新增。 |
| 三表勾稽与滚动表 | `04-BALANCE`、`04-CASH`、`04-RE`、`04-PPE`、`03-DEBT`、`03-NWC` | 资产=负债+权益、现金勾稽、留存收益滚动、资产与债务滚动均保留现有机制。 |
| FCFF、WACC、折现、终值 | `05-FCFF`、`05-WACC`、`05-DF`、`05-TV` | 覆盖无杠杆现金流、CAPM/再杠杆、折现期、Gordon 与退出倍数终值。 |
| 股权桥、稀释股数与每股价值 | `05-BRIDGE`、`05-DILUTION`、`05-VPS` | 净债务与其他桥接项、库存股法/RSU、股权价值除以股数均不重复新增。 |
| 分部、管线、情景与多方法 | `C-SOTP-*`、`C-PIPE-*`、`C-CASE-*`、`C-MULTI-SPLIT` | 通用 BC 机制已覆盖，不再为特定药物、分部或情景另设条目。 |
| 一般可读性、单位和活公式 | `09-READABLE`、`01-UNIT`、`06-FORMULA`、`06-LINKS` | 普通标签、单位、结果公式及错误/外链检查不新增；仅补充题面明确要求的更具体结构或格式。 |

覆盖映射允许一个原始条目对应多个现有 ID；报告中的“仅现有库覆盖”只统计不含新点的原始条目，复合条目另计入“含新点并合并”。逐条映射保存在 `_distill_agent/work/manual_mapping.json`。

##### 最终新增按类别分布

| 类别 | 条数 | 主要补缺 |
|---|---:|---|
| 呈现与客户可用性 | 16 | 题面规定的颜色、数字格式、可读边界、WCAG、合并单元格、字体、期间区分、逐页结构、对象标识及打印设置。 |
| 公式与模型工程 | 14 | 集中输入、无内嵌常数、单一输入源、跨表活引用、期间对齐、公式一致性、循环控制、易变函数、范围、分母及全网格重算。 |
| 透明度与可审计性 | 10 | 来源记录、调整金额与处理说明、折现期、历史锚点、FCFF 与终值组成、方法选择与开放假设推导。 |
| 输入原样采用与历史口径 | 9 | 给定输入、恒定驱动、历史推导、截止日、期间类型、预测期、历史定义及实际值保留。 |
| 内部一致性与交叉核对 | 8 | 敏感性中心格与轴序列、方向、共用显性期现值、溢价率、模型—展示一致性及 PDF 导出。 |
| 交付与来源完整性 | 4 | 文件类型/文件名/组合、指定 sheet 名称与数量、占位符及其他项目遗留引用。 |
| 经营预测 | 2 | EMB 的获得期群组归属与观察期阈值分群。 |
| **合计** | **63** | 全部 BC；未为凑数新增 A/D/E/W 专属项。 |

##### 原子性与唯一判定自查

- 每条只检查一个对象或关系；复合原文被拆分而非把多个独立检查写进一条新要求。
- 数值类要求有输入包、独立重算、同口径输出或题面阈值为比较对象；容差优先使用题面值，未指定时才采用条目明确的默认值或精确比较。
- 结构类要求有可观察对象：文件/sheet、单元格公式、引用链、来源字段、数字格式、页数或对象边界。需要读取工作簿的标为 `agent`，开放推理标为 `llm`。
- 原始条目中有 **81 条**因不原子、不可唯一判定或过度题目专属而删除；其中 BTB 74 条、FrontierFinance 7 条。
- 原始复合项的拆分由 **1,441 条多映射原始项**记录；外部重复语料合并为 **980 条含新点原始项**，支持最终 63 个新 ID。未另行保留不可复核的“草稿删除/拆分”计数。
- 全部 63 个新 ID 都有非零支持；没有任务专属公司名、固定增长率、固定 cohort 数字或指定日期进入 `requirement`。

##### 限制与审计说明

- EMB `M003-scratch_rubric.jsonl` 第 50 个物理行（N050）尾部被截断，不能作为完整 JSON 解析。其 `id`、`weight`、`text`、`category` 完整可读，已只保留这些字段，未推测尾部引用信息；N050 的零值检查由现有 `06-RECALC` 覆盖。
- 本地模型接口用于辅助语义复核：大上下文并发请求出现 500/超时后，改用 6 条小批量串行，仅成功复核前 18 条，随后接口继续停滞并停止。未把接口调用当作全量语义审查；最终全量统计来自可复现的 Python 逐条映射、非展示类与高风险映射人工审查、随机抽样及字段校验。
- 本报告不声称所有原文都可通过纯规则自动评分；`llm` 与 `agent` 已用于需要语义一致性或工具读取工作簿的项目。
- 本代理未写入 `library.json` 或 v2 目录，未读取图片或密钥。任务开始时的去重基准为 `library.json` 128 条，其规范化内容哈希为 `759bbdc5…065e`。最终校验时发现外部进程已将本输出的 63 个 X-ID 追加进主库，使其变为 191 条（文件时间 21:39:50）；该变化不是本代理执行，未擅自回滚或覆盖。去重映射仍以最初的 128 个 ID 为基准。

## 3. 统一 Rubric 库（全部条目）

**具体要求**为可判定 0/1 的原子断言；**方法** rule=程序检查，llm=单项 LLM 判定，agent=工具型 Agent 判定。

### 交付与来源完整性（18 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 |
|---|---|---|---|---|---|
| 01-FILE | 按要求提交可读取的 Excel 工作簿 | /app/output.xlsx | all | rule | 主需 |
| 01-KEYS | 每一个要求的语义输出键均存在且只有一个数值 | Outputs 或语义键映射 | all | rule | 主需 |
| 01-UNIT | 金额、股数与比率的单位在提交中明确 | 工作簿表头与单位标签 | all | agent | 次需 |
| E-deliver_model | The required primary model artifact exists and parses. | /app/output/model.xlsx or model.json | all E | rule | 主需 |
| E-deliver_simulator | The candidate-owned simulate.py exists and parses. | /app/output/simulate.py | all E | rule | 主需 |
| E-deliver_trials | simulation.json exists and has the required top-level schema. | simulation.json | all E | rule | 主需 |
| E-deliver_memo | memo.md exists and is no more than 700 words. | memo.md | all E | rule | 次需 |
| W-VALUE | 每个要求取数的值与指定权威来源一致（在题面容差内） | 取数表 | all W | rule | 主需 |
| W-SOURCE | 每个取数注明来源文件、期间和字段或页码，且来源属于允许范围 | 取数表 | all W | rule | 主需 |
| W-CROSS | 至少一项关键数据用第二个独立来源或勾稽关系交叉验证 | 交叉验证表 | all W | rule | 主需 |
| W-USED | 取到的数被模型公式实际引用，而不是另行手填 | 模型引用关系 | all W | rule | 主需 |
| W-NOFORBID | 未使用禁止来源或截止日后的信息 | 取数记录 | all W | agent | 主需 |
| W-FAILURE | 取数失败或数据冲突时如实披露并说明处理方法 | memo.md | all W | llm | 次需 |
| X-FM-012 | 最终交付不存在 TBD、TODO、fix this、草稿标记、未解析占位符或游离调试单元格。 | 全部交付文件的可见文本、批注与单元格扫描 | 交付最终模型或展示材料 | agent | 次需 |
| X-FM-014 | 交付文件的可见文本及链接中不存在指向其他公司或其他项目的遗留引用。 | 全部交付文件的文本、链接与图表引用 | 基于模板或既有工作簿交付 | agent | 主需 |
| X-IF-001a | 题面要求的每个交付文件均以指定文件名存在 | 交付文件清单、扩展名与题面文件要求 | 题面指定文件类型、文件名或交付文件组合 | rule | 主需 |
| X-IF-001b | 每个交付文件的类型与题面指定类型一致，未以其他类型替代 | 交付文件清单、扩展名与题面文件要求 | 题面指定文件类型、文件名或交付文件组合 | rule | 主需 |
| X-IF-002 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | 工作簿 sheet 清单与题面结构要求 | 题面指定工作表名称、数量或保留结构 | rule | 主需 |

### 多步状态与业务重构（12 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 |
|---|---|---|---|---|---|
| 01-HISTORY | 原始历史事实未被覆盖或删除 | 历史原始事实页 | D 所有后续步骤 | rule | 主需 |
| 08-OLD | 后续工作簿保留事件前原始输入与状态 | 历史/前步状态 | D 所有后续步骤 | rule | 主需 |
| 08-REBASE | 新实际值重定基期而非覆盖历史 | 重定基期行 | 重定基期事件 | rule | 主需 |
| 08-DISPOSE | 处置后的收入、资产、债务同步移除 | 事件重述 | 剥离事件 | rule | 主需 |
| 08-REFINANCE | 融资和资本开支事件同时更新对应滚动表 | 事件后预测 | 融资或资本开支事件 | rule | 主需 |
| 08-RESTATE | 事件后的 FCFF 与股权桥使用更新后的依赖 | 事件后估值 | D 所有后续步骤 | rule | 主需 |
| D-FINAL-VALUES | 最后一步工作簿的全部输出键与最终独立真值一致 | 最终工作簿 | all D | rule | 主需 |
| D-FINAL-LIVE | 最后一步结果仍为活公式，隐藏扰动可传导 | 最终工作簿与扰动 | all D | rule | 主需 |
| D-STEP-SNAPSHOT | 每一步都保存了独立快照 | 各步 pre/post 快照 | all D | rule | 主需 |
| D-STEP-VALUES | 每一步快照的输出与该步独立真值一致 | 各步快照 | all D | rule | 主需 |
| D-STEP-SCOPE | 每一步只修改该步要求涉及的依赖，未触及的输出保持不变 | 相邻快照差异 | all D | rule | 次需 |
| D-STEP-LOG | 说明中逐步记录修改内容及影响 | memo.md | all D | llm | 次需 |

### 历史与会计口径（20 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 |
|---|---|---|---|---|---|
| 02-FY | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | 历史聚合与原始期间 | 非年度历史 | rule | 主需 |
| 02-LTM | LTM 恰包含要求的季度或半年，未重复年化 | 历史聚合与估值日 | 非年度历史 | rule | 主需 |
| 02-REPORTED | 非经常收益未混入规范化经营 EBIT | 历史披露与调整 | 规范化历史 | rule | 主需 |
| 02-SBC | 股份支付作为经营成本处理且未在 FCFF 中加回 | 历史成本与 FCFF 依赖 | SBC | rule | 主需 |
| 02-COLLECT | 现金收款等于确认收入加合同负债增加 | 现金收款与递延收入 | 合同负债 | rule | 次需 |
| E-hist_revenue | FY0 revenue equals the frozen SEC fact within 0.1%. | Outputs.hist_revenue_fy0 or model.json historical | all E | rule | 主需 |
| E-hist_ebit | FY0 EBIT equals the frozen SEC fact within 0.1%. | Outputs.hist_ebit_fy0 or model.json historical | all E | rule | 主需 |
| E-hist_eps | FY0 diluted EPS equals the frozen SEC fact within 0.1%. | Outputs.hist_eps_fy0 or model.json historical | all E | rule | 次需 |
| E-hist_partial_revenue | The actual partial revenue equals the sum of listed discrete quarters, without YTD double-counting. | actual_partial_revenue_y1 | E 残余期变体 | rule | 主需 |
| E-hist_partial_residual_boundary | Residual FY1 revenue equals full FY1 revenue minus actual partial revenue. | residual_revenue_y1 | E 残余期变体 | rule | 主需 |
| B-MIXLTM | 混合历史 LTM 由最近完整半年加其后桥接季度构成，不重复计入、不遗漏、不年化 | 历史聚合与原始期间 | 混合历史拼接 | rule | 主需 |
| X-IN-001 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | 输入假设区、输入包及输入映射 | 题面提供输入值 | rule | 主需 |
| X-IN-002 | 题面指定的恒定输入在其每个适用期间均被原样采用，不出现未经指定的期间变化。 | 假设区与各预测期驱动行 | 题面规定某输入在多个期间保持不变 | rule | 主需 |
| X-IN-003 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | 历史窗口、输入推导公式与独立重算 | 题面指定历史推导窗口或公式 | rule | 主需 |
| X-IN-004 | 每项模型输入的适用日期均不晚于题面规定的信息截止日。 | 输入来源记录、适用日期与估值截止日 | 题面规定信息截止日 | agent | 主需 |
| X-IN-005 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | 历史输入表、期间标签与原始报表 | 使用外部历史财务数据 | rule | 主需 |
| X-IN-006 | 估值桥或比较价格使用题面基准日当天或之前最近一个可用值。 | 估值桥输入、行情或资本化数据的日期 | 使用行情、债务、现金或资本化时点数据 | rule | 主需 |
| X-IN-007 | 模型的预测期序列与题面指定的起止期间完全一致。 | 模型期间表头与题面预测区间 | 题面指定显性预测期 | rule | 主需 |
| X-IN-008 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | 历史与预测列的行标签及公式比较 | 模型同时展示历史期与预测期 | rule | 主需 |
| X-IN-009 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | 历史区单元格内容与输入包对照 | 在历史数据旁构建预测 | rule | 主需 |

### 经营预测（53 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 |
|---|---|---|---|---|---|
| 03-DRIVER | 期末经营基数等于期初减流失加新增 | 经营预测期 | 存量驱动 | rule | 主需 |
| 03-AVERAGE | 收入采用平均经营基数乘以单位收入及期间活动比例 | 收入预测 | 存量驱动 | rule | 主需 |
| 03-MARGIN | 各期 EBIT 使用本期的分部或核心利润率 | EBIT 预测 | all | rule | 主需 |
| 03-CAPEX | 资本开支同时包含强度部分与重排新增部分 | 资本开支预测 | 资本开支重排 | rule | 次需 |
| 03-NWC | 营运资本变动使用正确期初、期末与符号 | 营运资本表 | all | rule | 主需 |
| 03-DAYS | 应收、存货与应付使用实际年度天数口径 | 营运资本表 | 营运资本天数法 | rule | 次需 |
| 03-DEBT | 借款、偿还、利息和期末债务连续滚动 | 债务表 | 债务计划表 | rule | 主需 |
| 03-LEASE | 使用权资产与租赁负债的口径一致 | 租赁滚动与股权桥 | 租赁 | rule | 次需 |
| 03-NOL | NOL 使用不得超过正 EBIT 或可用余额 | 税务滚动 | NOL | rule | 次需 |
| E-forecast_revenue | Each of the five full-year revenue forecasts is positive and finite. | Forecast revenue_y1..y5 | all E | rule | 次需 |
| E-forecast_ebit | Each forecast EBIT is finite and its implied margin is between -50% and 70%. | Forecast ebit_y1..y5 | all E | rule | 次需 |
| E-forecast_reinvestment | Each reinvestment component equals D&A minus CapEx minus the change in NWC. | Forecast da/capex/delta_nwc/reinvestment_component | all E | rule | 主需 |
| E-llm_business_chain | The forecast states a company-specific operating causal chain that can explain the direction of revenue and EBIT, rather than generic extrapolation. | one-atom judge packet with public business prompt and model values | all E | llm | 主需 |
| E-llm_reinvestment_reasoning | The reasoning explains why the operating growth and margin case requires the modeled D&A, capital expenditure and working-capital reinvestment. | one-atom judge packet with numeric reinvestment reconciliation | all E | llm | 主需 |
| B-NWC-OPEN | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | 营运资本表首期 | all | rule | 主需 |
| B-INTANG-ROLL | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | 无形资产滚动表 | 双资产池 | rule | 主需 |
| C-SOTP-SEG | 每个分部有独立的收入、利润率、再投资和 FCFF | 分部预测表 | 分部 SOTP | rule | 主需 |
| C-SOTP-VAL | 每个分部按题面指定方法（DCF 或倍数）单独估值 | 分部估值表 | 分部 SOTP | rule | 主需 |
| C-SOTP-SUM | SOTP 企业价值等于各分部价值之和，公司层费用按题面处理 | SOTP 汇总 | 分部 SOTP | rule | 主需 |
| C-SOTP-BRIDGE | 净债务与稀释股数只在公司层扣减一次，不在分部重复扣减 | SOTP 股权桥 | 分部 SOTP | rule | 主需 |
| C-PIPE-TIMING | 未投产或未上市项目在投产日前不产生收入 | 项目时间轴 | 风险调整管线 | rule | 主需 |
| C-PIPE-CAPEX | 建设期支出与投产期收入分别建模并计入对应期间 | 项目现金流 | 风险调整管线 | rule | 主需 |
| C-PIPE-PROB | 成功概率作用于项目现金流或项目价值，不通过调整 WACC 体现 | 风险调整 FCFF | 风险调整管线 | rule | 主需 |
| C-PIPE-SUM | 公司价值等于各项目风险调整价值之和加已有业务价值 | 管线汇总 | 风险调整管线 | rule | 主需 |
| A-DRIVER | 收入由该行业规定的业务驱动构造，而不是单一增长率 | 收入预测 | all A | rule | 主需 |
| A-METRIC | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | 行业指标表 | all A | rule | 主需 |
| A-VALUATION | 估值方法适配行业（金融用股权现金流或超额收益，房地产用 NOI/NAV 等），不硬套 FCFF | 估值表 | 金融、保险、房地产 | rule | 主需 |
| A-REASON | 说明中解释行业驱动与估值结果之间的因果链 | memo.md | all A | llm | 次需 |
| A-SAAS-ARR | 期末 ARR 等于期初 ARR 乘净留存率加新签 ARR，收入按期初期末 ARR 平均确认 | ARR 滚动表 | 软件与订阅 | rule | 主需 |
| A-SAAS-CAPRD | 资本化研发作为无形资产新增扣减 FCFF，摊销加回 | 研发资本化表 | 软件与订阅 | rule | 次需 |
| A-RETAIL-SSS | 收入拆为可比门店同店增长与新开店贡献，新店按开业月份折算 | 门店收入表 | 消费零售与连锁 | rule | 主需 |
| A-MFG-UTIL | 产量不超过有效产能乘利用率上限，扩产在投产后才增加产能 | 产能表 | 制造与工业设备 | rule | 主需 |
| A-MFG-YIELD | 合格产量等于投入量乘良率，良率在产量和成本链中只作用一次 | 投入量、良率、合格产量及销售率 | BOM 制造 | rule | 主需 |
| A-MFG-BOM | 各产品各物料耗用量等于投入量乘 BOM 单耗，耗用成本等于耗用量乘采购价，不以收入成本率替代 | 分产品分物料 BOM 明细 | BOM 制造 | rule | 主需 |
| A-MFG-PURCHASE | 采购与耗用及原材料滚动勾稽，采购不得直接作为 COGS | 采购、耗用、原材料和 COGS | BOM 制造 | rule | 主需 |
| A-MFG-INVENTORY | 原材料、在制品和产成品分别按题面口径滚动，不合并为单一收入比例 | 三类存货期初、变动和期末 | BOM 制造 | rule | 主需 |
| A-PHARMA-FUNNEL | 各管线收入由患者基数、诊断及适用比例、渗透率、依从性和净价格逐期构建 | 患者漏斗、治疗人次、净价格和收入 | 医药与生物科技 | rule | 主需 |
| A-PHARMA-COMMITRD | 上市前承诺研发投入不乘 PoS，已实现费用不因上市延迟删除 | 研发费用表、PoS 及上市时点 | 研发管线 | rule | 主需 |
| A-PHARMA-COMMERCIAL | 已商业化产品不重复乘研发成功概率 | commercial 现金流与 PoS 开关 | 研发管线 | rule | 主需 |
| A-PHARMA-CLIFF | 专利到期后收入按题面侵蚀曲线下降，不延续到期前增长 | 产品收入表 | 医药与生物科技 | rule | 主需 |
| A-HEALTH-PAYER | 收入按服务量乘各支付方单价加权，支付方结构变化影响均价 | 服务收入表 | 医疗服务 | rule | 次需 |
| A-BANK-NII | 净利息收入等于平均生息资产乘净息差，资产增长受资本充足率约束 | 银行损益表 | 银行与金融 | rule | 主需 |
| A-BANK-EQUITY | 使用股权现金流或超额收益模型，以股权成本折现 | 银行估值表 | 银行与金融 | rule | 主需 |
| A-INS-CR | 承保利润等于已赚保费乘一减综合成本率，投资收益单独计算 | 保险损益表 | 保险 | rule | 主需 |
| A-ENERGY-DECLINE | 现有储量产量按递减曲线下降，新增产量依赖开发资本开支 | 产量表 | 能源与资源 | rule | 主需 |
| A-UTIL-RAB | 允许收入等于受监管资产基数乘允许回报率加折旧回收 | 监管收入表 | 公用事业与基础设施 | rule | 主需 |
| A-TRANS-LOAD | 收入等于运力乘载运率乘单位收益，机队扩张伴随资本开支 | 运量表 | 交通与物流 | rule | 次需 |
| A-PLAT-ARPU | 收入等于平均用户乘 ARPU，内容或流量成本按题面摊销 | 用户收入表 | 互联网平台与媒体 | rule | 次需 |
| A-RE-NAV | 物业价值等于 NOI 除以资本化率，NAV 扣除负债 | NAV 表 | 房地产 | rule | 主需 |
| A-SVC-UTIL | 收入等于计费人员乘利用率乘人均费率，人员成本与人数联动 | 人员收入表 | 专业服务与外包 | rule | 次需 |
| A-EAAS-BASE | 服务收入由装机基数乘服务频次乘单价构成，续约率影响装机留存 | 装机表 | 设备即服务与装机运维 | rule | 次需 |
| X-A-001 | 群组成员按题面规定的首次获得或首次交易期间确定，后续观察期变化不改变其原始群组归属。 | 客户/业务对象首次期间映射与群组公式 | 题面要求按获得期或首购期进行群组分析 | rule | 主需 |
| X-A-002 | 分群汇总仅纳入观察期指标符合题面阈值的记录，各群计数与独立重算的相同阈值筛选结果一致。 | 观察期明细、阈值条件与分群计数公式 | 题面要求按观察期指标阈值分群计数 | rule | 主需 |

### 三表勾稽（4 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 |
|---|---|---|---|---|---|
| 04-BALANCE | 每个预测期资产等于负债加权益 | 资产负债表 | 三表 | rule | 主需 |
| 04-CASH | 资产负债表现金与现金流量表期末现金一致 | 现金流量表 | 三表 | rule | 主需 |
| 04-RE | 留存收益由净利润滚动且无不透明平衡项 | 权益滚动 | 三表 | rule | 主需 |
| 04-PPE | 长期资产由期初加新增减折旧摊销滚动 | 资产表 | 资产滚动 | rule | 主需 |

### DCF与估值桥（21 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 |
|---|---|---|---|---|---|
| 05-FCFF | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | FCFF 表 | FCFF 口径 | rule | 主需 |
| 05-WACC | WACC 使用 CAPM 再杠杆和税后债务成本 | 折现率计算 | CAPM | rule | 主需 |
| 05-DF | 折现期从估值日按实际天数计量并遵守年中约定 | 折现时间表 | all | rule | 主需 |
| 05-DUAL | Gordon 与退出终值分别计算再按权重合成 | 终值计算 | 双终值 | rule | 主需 |
| 05-TV | 终值以最后完整年度为时点且以 WACC 折现 | 终值现值 | all | rule | 主需 |
| 05-BRIDGE | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | 股权桥 | all | rule | 主需 |
| 05-DILUTION | 库存股法增量与 RSU 均进入稀释股数 | 股数桥 | 稀释股数 | rule | 次需 |
| 05-VPS | 每股价值以股权价值除以稀释股数 | 估值结果 | all | rule | 主需 |
| 05-SENS | 敏感性单元格使用各自行列假设而经营预测不变 | 敏感性网格 | 估值敏感性 | rule | 次需 |
| 05-SCENARIO | 经营情景切换同时影响需求和利润率并传递至价值 | 情景结果 | 情景驱动 | rule | 主需 |
| E-dcf_fcff | Each FCFF equals EBIT times one minus tax plus the reinvestment component. | Forecast and DCF tax_rate | all E | rule | 主需 |
| E-dcf_discount | Each discount factor equals one over one plus WACC raised to its stated actual-year fraction. | Forecast discount_factor and DCF discount_years | all E | rule | 主需 |
| B-INTANG-FCFF | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | FCFF 表 | 双资产池 | rule | 主需 |
| B-RESIDUAL | 首个预测段只计入估值日后的经营现金流 | 残余期 FCFF | all | rule | 主需 |
| C-CASE-SWITCH | 单一情景开关切换后收入、利润率、再投资、FCFF、终值和每股价值同时改变 | Cases 页与 Operating Model | 情景驱动 | rule | 主需 |
| C-CASE-ISOLATE | 每个情景的输出值与独立真值一致，情景之间不相互覆盖 | 情景结果表 | 情景驱动 | rule | 次需 |
| C-MULTI-SPLIT | Gordon 与退出倍数估值分别给出，不只输出加权结果 | 估值结果 | 多方法估值 | rule | 主需 |
| C-IMPLIED-MULT | 由 Gordon 终值反推的隐含 EV/EBITDA 计算正确 | 隐含倍数单元格 | 多方法估值 | rule | 主需 |
| C-IMPLIED-G | 由退出倍数终值反推的隐含永续增长率计算正确 | 隐含增长率单元格 | 多方法估值 | rule | 主需 |
| C-REVERSE | 由给定市场价格反推的隐含 WACC 或隐含增长假设正确，且以公式或求解过程得出 | 反推单元格 | 反向推导 | rule | 主需 |
| C-RANGE | 估值区间的上下界分别来自题面指定的方法和假设范围 | Football Field 表 | 估值区间 | rule | 次需 |

### 公式与模型工程（29 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 |
|---|---|---|---|---|---|
| 06-FORMULA | 每个要求的结果单元格为活公式而非粘贴数值 | 结果单元格 XML/openpyxl | all | rule | 主需 |
| 06-RECALC | LibreOffice 重算后结果与独立真值一致 | 重算后的候选与 expected | all | rule | 主需 |
| 06-PERTURB1 | 第一组经营及估值/桥接扰动按依赖传导 | 隐藏扰动一 | all | rule | 主需 |
| 06-PERTURB2 | 第二组经营及估值/桥接扰动按依赖传导 | 隐藏扰动二 | all | rule | 主需 |
| 06-LINKS | 无外部工作簿链接或公式错误值 | 重算工作簿 | all | rule | 主需 |
| 06-FREE | 自由布局通过语义键发现而非行号评分 | 工作簿语义映射 | 自由或混合布局 | rule | 次需 |
| E-formula_perturb_wacc | A +0.5 percentage-point WACC perturbation decreases enterprise value. | fresh recalculation after WACC perturbation | all E | rule | 次需 |
| E-formula_perturb_g | A +0.2 percentage-point terminal-growth perturbation increases enterprise value. | fresh recalculation after terminal-growth perturbation | all E | rule | 次需 |
| X-FM-001 | 题面要求集中管理的每个业务假设均在假设区拥有独立的可见输入单元格。 | 假设区、输入单元格与模型公式 | 题面要求集中管理可调整假设 | rule | 主需 |
| X-FM-002 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | 计算公式 XML、公式常量扫描及输入引用 | 模型含可调业务或估值假设 | rule | 主需 |
| X-FM-003 | 同一业务或估值假设仅有一个权威输入单元格，每个使用该假设的下游公式均可追溯至该单元格。 | 输入依赖图及重复硬编码扫描 | 同一假设被多个计算模块使用 | rule | 主需 |
| X-FM-004 | 下游行项通过工作簿内活引用取得已在上游模块计算的对应值，未另行重填或独立重算。 | 跨表引用公式、上游输出行与下游行 | 题面要求集成已有计算模块或原始数据表 | rule | 主需 |
| X-FM-005 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | 各计算区期间表头与逐列公式 | 多个计算区按期间排列 | rule | 主需 |
| X-FM-006 | 除题面明确允许的过渡期外，同一预测行各期公式具有相同的相对引用模式。 | 预测行公式 R1C1 规范化比较 | 多期预测使用同一计算逻辑 | rule | 次需 |
| X-FM-007 | 估值计算链不存在未声明的循环引用。 | 公式依赖图与循环检测 | 交付 Excel 模型 | rule | 主需 |
| X-FM-008 | 题面要求有意循环计算时，模型具有可关闭该循环路径的明确开关。 | 循环开关单元格及开关前后的依赖路径 | 题面要求可控的循环计算 | rule | 次需 |
| X-FM-009 | 影响估值输出的公式不使用 OFFSET、INDIRECT、NOW、TODAY、RAND 或 RANDBETWEEN。 | 估值依赖链公式文本 | 交付 Excel 估值模型 | rule | 次需 |
| X-FM-010 | 汇总、求和与折现公式的引用范围均有明确起止单元格，不包含整行或整列引用。 | SUM、NPV 及聚合公式范围 | 模型含区域汇总或折现公式 | rule | 次需 |
| X-FM-011 | 分母可能为零或空值的除法公式具有 IF 分母判断或 IFERROR 保护。 | 除法公式及零/空分母情景 | 模型含可能为零或空的分母 | rule | 次需 |
| X-FM-013 | 模型计算逻辑所在区域不存在隐藏行或隐藏列。 | 工作表行列隐藏属性及计算依赖区 | 工作簿未获授权隐藏计算逻辑 | rule | 次需 |
| X-FM-015 | 题面允许的有意循环计算在迭代重算后收敛，输出不随额外迭代发生超出题面容差的变化。 | 迭代设置与连续两次重算结果 | 题面允许循环计算 | rule | 主需 |
| X-IC-001 | 敏感性表中与基准行列假设相交的单元格，其值与模型相同口径基准输出的相对差异不超过题面容差；题面未给容差时为 0.1%。 | 敏感性轴、中心格与模型基准输出 | 敏感性网格包含全部基准假设组合 | rule | 主需 |
| X-IC-002 | 每条敏感性轴的完整值序列与题面指定的起点、终点及步长完全一致。 | 敏感性轴单元格与题面轴定义 | 题面规定敏感性轴或区间 | rule | 主需 |
| X-IC-003 | 在现金流与永续增长率保持为正且 WACC 大于永续增长率时，敏感性网格中折现率单调上升对应估值结果不上升。 | 敏感性网格与对应变量重算 | 折现率敏感性的其余条件满足正终值分母 | rule | 次需 |
| X-IC-004 | 敏感性轴中题面指定的基准假设位于该轴的中心位置。 | 敏感性轴值序列与题面基准假设 | 题面要求敏感性轴以基准假设为中心 | rule | 次需 |
| X-IC-005 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | 各估值方法的显性期现值引用与合计 | 同一模型使用多种终值方法 | rule | 主需 |
| X-IC-006 | 隐含价相对现价的溢价率按“隐含价 ÷ 同口径现价 − 1”计算，绝对差异不超过题面容差。 | 隐含价、现价与溢价/折价输出 | 要求输出相对现价的溢价、折价或上行空间 | rule | 主需 |
| X-IC-008 | PDF 的页数、页面顺序及每页文字和数值与其 PPT 导出源逐页一致。 | PPT 与 PDF 逐页文本及页面对象映射 | 同时要求 PPT 及其 PDF 导出版本 | rule | 次需 |
| X-IF-003 | 敏感性网格的每个结果值均与模型在相同行列输入下的重算值一致，容差按题面规定。 | 敏感性全网格、行列输入与逐格模型重算 | 要求敏感性网格基于完整模型逐格求值 | rule | 主需 |

### 开放假设与模拟（10 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 |
|---|---|---|---|---|---|
| 07-ASSUME | 开放假设有可追溯的证据和适用日期 | 假设说明 | 开放假设 | llm | 主需 |
| 07-PATHS | 模拟路径满足数量、抽样和相关性约束 | 模拟试验 | Monte Carlo | rule | 主需 |
| 07-QUANTILE | 模拟分位数由试验样本独立计算 | 模拟摘要 | Monte Carlo | rule | 主需 |
| E-mc_seed | The declared seed equals the task seed. | simulation.json seed | all E | rule | 次需 |
| E-mc_distributions | Every required driver has a supported distribution, legal numeric parameters, declared bounds, and sample statistics within method-aware tolerances. | drivers and trials | all E | rule | 主需 |
| E-mc_dependence | The realized correlation matrix agrees with the declared dependence structure, or the independence explanation is supported by realized cross-driver correlations. | dependence and trials | all E | rule | 主需 |
| E-mc_recompute | Every sampled path's DCF value independently recomputes from its drivers and the deterministic model within 0.5%. | trials and independent grader path arithmetic | all E | rule | 主需 |
| E-mc_not_degenerate | The value distribution is non-degenerate and has more than 100 distinct values. | trials.value_per_share | all E | rule | 次需 |
| E-llm_driver_derivation | The cited historical observations are explicitly connected to each material forecast driver by a reproducible derivation, not merely listed. | one-atom judge packet: memo, verified citations and deterministic forecast | all E | llm | 主需 |
| E-agent_distribution_rationale | The selected uncertainty bounds and dependence rationale are justified from supplied historical evidence without invoking unavailable post-cutoff information. | agent group packet; read-only artifact and source-inspection tools | all E | agent | 主需 |

### 表达与专业可用性（33 条）

| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 |
|---|---|---|---|---|---|
| 09-MEMO | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | memo.md 说明文字 | all | llm | 次需 |
| 09-READABLE | 中间结构有明确期间与项目标签且不依赖未披露技巧 | 工作簿布局 | all | agent | 次需 |
| E-evidence_numeric_citations | At least three memo citations identify a real source, historical period, and value matching the frozen fact. | memo.md and public frozen inputs | all E | rule | 次需 |
| E-evidence_limits | The memo explicitly discloses forecast uncertainty and the independence or correlation choice. | memo.md | all E | rule | 次需 |
| E-agent_interval_interpretation | The interpretation distinguishes model-implied FCFF/DCF dispersion from a market-price forecast and states material simulation limitations. | agent group packet; read-only artifact and source-inspection tools | all E | agent | 次需 |
| X-IC-007 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | 展示材料数值与模型输出映射 | 同时交付模型与展示或摘要材料 | agent | 主需 |
| X-TA-001 | 每项外部输入均有可定位的来源记录，记录至少含文档或数据集名称及对应财务期间或数据日期。 | 输入来源字段、单元格批注或来源清单 | 使用题面之外的申报、行情或行业数据 | agent | 主需 |
| X-TA-002 | 每项非经常性调整均单独记录调整金额。 | 历史规范化调整表及原始披露 | 存在非经常性历史调整 | rule | 主需 |
| X-TA-003 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | 会计处理说明、调整表与相关报表公式 | 题面要求规范化或特定会计处理 | llm | 次需 |
| X-TA-004 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | 折现时间表与逐期折现公式 | 构建 DCF 折现模型 | agent | 次需 |
| X-TA-005 | 用于外推或推导预测的历史锚定期间数值在模型中可见。 | 历史锚定列、预测驱动与公式引用 | 预测输入由历史数据外推或推导 | agent | 次需 |
| X-TA-006 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | FCFF 明细行及公式引用 | 题面要求展示 FCFF 构建 | agent | 次需 |
| X-TA-007 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | 终值计算区、终期指标行与假设单元格 | 使用 Gordon 或退出倍数终值 | agent | 次需 |
| X-TA-008 | 题面要求解释方法选择时，说明明确指出所选估值方法，并给出至少一项与该公司数据或模型结果对应的依据。 | 估值说明、方法比较表与公司特定输入 | 题面要求比较或选择估值方法 | llm | 次需 |
| X-TA-009 | 每个开放性预测假设均有书面推导，包含历史观察值及由该观察值到假设值的计算或映射关系。 | 假设说明、历史观察值与预测输入对照 | 预测假设需自行确定而非题面给定 | llm | 次需 |
| X-TA-010 | 按题面指定历史窗口推导的预测输入旁有可见的历史观察值或计算过程，能由该观察值复算得到预测输入。 | 历史观察值、预测输入推导公式与相邻说明 | 预测输入按题面给定规则从历史数据推导 | agent | 次需 |
| X-PR-001a | 硬编码输入单元格使用题面指定的输入颜色 | 输入及公式单元格字体/填充颜色与单元格类型 | 题面或建模规范要求输入颜色编码 | rule | 次需 |
| X-PR-001b | 输入单元格颜色与计算单元格颜色不同 | 输入及公式单元格字体/填充颜色与单元格类型 | 题面或建模规范要求输入颜色编码 | rule | 次需 |
| X-PR-002 | 工作簿公式单元格的字体颜色与题面规定的公式类型颜色映射一致。 | 同表及跨表公式、字体颜色 | 题面或建模规范要求区分公式与跨表链接 | rule | 次需 |
| X-PR-003 | 财务金额负数按题面约定以括号显示，不使用前导负号代替括号。 | 负数单元格数字格式与显示文本 | 题面或建模规范要求会计括号负数格式 | rule | 次需 |
| X-PR-004 | 达到千位及以上的财务金额使用千分位分隔符显示。 | 财务金额单元格数字格式 | 题面或建模规范要求千分位格式 | rule | 次需 |
| X-PR-005 | 每个规定输出的显示小数位数等于题面指定位数。 | 输出数字格式与显示值 | 题面指定显示小数位数 | rule | 次需 |
| X-PR-006 | 估值倍数的显示格式与题面指定的倍数格式完全一致，包含指定的小数位数与 x 后缀。 | 倍数输出单元格数字格式 | 输出估值倍数 | rule | 次需 |
| X-PR-007 | 增长率、利润率、税率及折现率等比率输出以百分比格式显示。 | 比率输出行数字格式 | 输出比率或百分比指标 | rule | 次需 |
| X-PR-008 | 同一行各期间的数字格式一致。 | 逐行各期数字格式串比较 | 按期间展示同一指标 | rule | 次需 |
| X-PR-009 | 可见表格的文本与数值未被列宽、行高或相邻对象遮挡，显示结果不含 #### 或截断标签。 | 工作簿及展示文件的显示长度、对象边界与截断检查 | 交付含可见表格的工作簿或展示文件 | agent | 次需 |
| X-PR-010 | 题面要求 AA 对比度时，标题或副标题文字颜色与填充颜色的 WCAG 相对亮度对比度至少为 4.5:1。 | 标题单元格字体/填充色及对比度计算 | 题面要求 WCAG AA 文本对比度 | rule | 次需 |
| X-PR-011 | 数据区、输入区或计算区内不存在合并单元格。 | 工作表 merged_cells 范围与数据区映射 | 题面禁止计算或数据区域合并 | rule | 次需 |
| X-PR-012 | 正文非空单元格使用题面指定的统一字体家族。 | 正文非空单元格字体属性 | 题面或建模规范规定统一字体 | rule | 次需 |
| X-PR-013 | 历史期与预测期通过 A/E 等期间标签、分组表头或视觉分隔明确区分。 | 期间表头、分组标签或分隔样式 | 历史期与预测期并列展示 | agent | 次需 |
| X-PR-014 | PPT 或 PDF 的页数与页面顺序符合题面指定的逐页内容要求。 | PPT/PDF 页数、页面文字与题面对照 | 题面指定 PPT 或 PDF 的逐页结构 | agent | 次需 |
| X-PR-015 | 模型标题区明确标识题面估值对象的名称或代码。 | 模型首页或分析页标题区文本 | 题面要求模型标识或封面 | agent | 次需 |
| X-PR-016 | 指定输出区的打印区域、页面方向及缩放设置与题面逐项一致。 | 工作表 print_area、orientation 与 fitToWidth 设置 | 题面指定打印布局 | rule | 次需 |

## 4. 验收结果

**BC/A/D**（`validation.json`）：28 题、16 个 D 步骤；40/40 份参考工作簿经 LibreOffice 重算后与独立真值一致，失败 0。每份工作簿两组隐藏扰动均正确传导；空白与静态负例全部被拒绝。

C 结构覆盖：simple_dcf：BC01、BC08、BC15；three_statements_dcf：BC02、BC13；segment_sotp：BC03、BC09；risk_adjusted_pipeline：BC04、BC10；scenario_operating_model：BC05、BC11、BC16；multi_method：BC06、BC12；debt_schedule_dcf：BC07、BC14。

B 关键项：混合历史 LTM BC08、BC09、BC11、BC12、BC14；双资产池 BC10、BC11、BC12、BC16；首期 ΔNWC 用估值日余额 BC01、BC03、BC04、BC05、BC07、BC11、BC12、BC14、BC15，用财年末余额 BC02、BC06、BC08、BC09、BC10、BC13、BC16。

**E/W**（`open/validation.json`）：

| 题 | 本地参考 | Harbor 参考 |
|---|---:|---:|
| E01 | 1.0 | 1.0 |
| E02 | 1.0 | 1.0 |
| E03 | 1.0 | 1.0 |
| E04 | 1.0 | 1.0 |
| W01 | 1.0 | 1.0 |
| W02 | 1.0 | 1.0 |
| W03 | 1.0 | 1.0 |
| W04 | 1.0 | 1.0 |

限制：未来实际值及股价仅为诊断，不参与 reward；真实公司回测仍可能存在训练记忆泄漏。；W 真值由本地原始 SEC 快照和 DGS10 序列核验，保留原文件 SHA-256；不声称冻结文件是本次重新下载。；IR 允许用于核对，但实测首页均 403；不能依赖 IR 作为唯一取数来源。；普通默认 docker provider 不支持这些网络模式，需要使用已验证的 IPv4 provider。；机械评分与 Harbor oracle 通过不代表未执行的 llm/agent 语义评审通过。

**A09**（`a_expansion/A09_validation.json`）：{"schema_version": "v3.0", "task_id": "A09", "passed": true, "soffice": "/opt/homebrew/bin/soffice", "reference_recalculation": {"passed": true, "report": "a_expansion/A09_reference_report.json", "public_keys_checked": 218, "max_relative_error": 1.4039029826447501e-14, "mismatches": [], "dependency_checks": {"passed": true, "checks": {"bom_not_revenue_ratio": true, "cogs_excludes_purchases": true, "yield_applied_once": true, "three_inventory_pools_separate": true, "sensitivity_25_independent_sheets": true, "sensitivity_full_recalculation": true}, "detail": {"missing_bom": [], "yield_errors": [], "inventory_errors": [], "missing_sensitivity_sheets": [], "sensitivity_errors": []}}}, "hidden_perturbations": [{"id": 1, "label": "bom_capacity_price_bridge", "passed": true, "mismatches": [], "checked": 218, "max_relative_error": 1.1583650406256259e-14}, {"id": 2, "label": "inventory_capex_payment_bridge", "passed": true, "mismatches": [], "checked": 218, "max_relative_error": 2.4346471761066057e-14}]}

**R01/R02 复用题**（`tasks/R_validation.json`）：R01 参考 reward=1.0，空白工作簿 reward=0.01；R02 参考 reward=1.0，空白工作簿 reward=0.0。评分器为原版本，未改动。

> 参考答案满分只说明题目、真值与评分器闭环成立，不代表被测模型能得高分；llm/agent 语义评分尚未执行。

**Rubric 挑选状态说明：** `llm_ok` 仅表示至少一个类别批次成功。以下题有类别批次失败，该类别只含程序补齐的必选条目：A04（交付与来源完整性）。其余 38 题没有失败批次。

### 逐题 rubric 挑选统计

| 题族 | 题数 | 每题条数 | 平均程序补齐 |
|---|---:|---|---:|
| BC | 16 | 42–54 | 0.1 |
| A | 9 | 32–42 | 3.3 |
| D | 4 | 56–68 | 0.8 |
| E | 4 | 54–61 | 5.0 |
| W | 4 | 41–42 | 3.0 |
| R | 2 | 29–36 | 0.5 |

## 5. 全部题目

每题包含完整 spec、完整中文题面和全部选中 rubric；D 题另含各步骤完整 spec 与题面。spec 折叠仅为便于阅读，不作内容截断。

### BC01（BC）

<details><summary>BC01｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC01",
  "seed": 392708,
  "candidate_index": 10,
  "family": "BC",
  "step": 1,
  "company": "栖岸云档",
  "dimension_selection": {
    "scenario": "特种涂层产线",
    "difficulty": "L2: 依赖深度7，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "capacity",
    "valuation_mechanism": "exit",
    "accounting_basis": "SBC经营成本",
    "output_mode": "three_statements_dcf",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "debt_schedule",
    "dilution",
    "three_statements",
    "nwc_days"
  ],
  "selection_rationale": {
    "scenario": "特种涂层产线要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "capacity",
    "unit": "千吨年产能",
    "price_unit": "百万元/千吨",
    "description": "特种涂层产线"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-12-21",
  "last_fy_end": "2025-08-31",
  "horizon": 5,
  "history": [
    {
      "start": "2022-09-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 465.719082,
      "ebit": 48.118698,
      "operating_cost_ex_sbc": 381.411504,
      "sbc": 11.336848,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-03-01",
      "end": "2023-08-31",
      "fiscal_year": "2023",
      "revenue": 478.213984,
      "ebit": 51.76253,
      "operating_cost_ex_sbc": 389.734034,
      "sbc": 11.641008,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-09-01",
      "end": "2024-02-29",
      "fiscal_year": "2024",
      "revenue": 490.708886,
      "ebit": 55.529313,
      "operating_cost_ex_sbc": 397.956731,
      "sbc": 11.945167,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-03-01",
      "end": "2024-08-31",
      "fiscal_year": "2024",
      "revenue": 503.203789,
      "ebit": 59.419048,
      "operating_cost_ex_sbc": 406.079593,
      "sbc": 12.249327,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-09-01",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "revenue": 515.698691,
      "ebit": 63.431734,
      "operating_cost_ex_sbc": 414.102622,
      "sbc": 12.553486,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-03-01",
      "end": "2025-08-31",
      "fiscal_year": "2025",
      "revenue": 528.193593,
      "ebit": 67.567371,
      "operating_cost_ex_sbc": 422.025816,
      "sbc": 12.857645,
      "nonrecurring_gain": 6.244924
    }
  ],
  "opening_nwc": 368.678,
  "opening_deferred": 0.0,
  "opening_ppe": 339.14,
  "opening_rou": 0.0,
  "opening_debt": 218.8,
  "opening_retained_earnings": 175.04,
  "contributed_capital": 426.66,
  "opening_cash": 109.4,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 122,
    "price0": 12.1178556,
    "driver_add": [
      9.76,
      11.102,
      12.444,
      13.786,
      15.128
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.107,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 7.8,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 120.34,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      19.692,
      19.692,
      19.692,
      19.692,
      19.692
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      27.35,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      10.94,
      21.88,
      32.82,
      43.76,
      54.699999999999996
    ],
    "beta_unlevered": 0.84,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "utilization": [
      0.74,
      0.758,
      0.776,
      0.794,
      0.8119999999999999
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      19.7,
      23.7,
      27.7,
      31.7,
      35.7
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 109.4,
    "debt": 218.8,
    "investments": 16.41,
    "lease_liability": 0.0,
    "minority": 13.128,
    "valuation_cash_adjustment": 13.128,
    "shares": 140,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 14.0
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 368.678,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 426.66,
    "opening_cash": 109.4,
    "opening_operating_current_assets": 368.678,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 103.3,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "simple_dcf",
  "c_structure_definition": "简版 DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge"
    ],
    "c": "simple_dcf"
  },
  "market": {
    "market_price": 13.91
  }
}
```

</details>

##### BC01｜栖岸云档估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题交付单一主体的 DCF：从经营预测推出 FCFF，折现后经股权桥得到每股价值。
公司财年截至每年 8 月 31 日，最近完整财年末为 `2025-08-31`，估值日 `2025-12-21` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
建立 EBIT、无杠杆现金税、折旧摊销、资本开支与 ΔNWC 到 FCFF 的完整桥，再折现并完成股权桥。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC01 选用的 rubric（47 条，权重合计 123；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值必需 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需output.xlsx与memo.md |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需Results页并保留Inputs页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史须聚合为完整财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 存在非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作为经营成本处理 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 产能含新增与流失滚动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均产能×价格×残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率给定 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期ΔNWC期末差额与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用估值日余额 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用营运资本天数法 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 启用债务计划表 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | FCFF要求NOL抵扣限额 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 新增无形资产独立摊销 |
| 04-BALANCE | 三表勾稽 | 每个预测期资产等于负债加权益 | rule | 主需 | spec启用三表模块 |
| 04-CASH | 三表勾稽 | 资产负债表现金与现金流量表期末现金一致 | rule | 主需 | 现金从opening_cash滚动 |
| 04-RE | 三表勾稽 | 留存收益由净利润滚动且无不透明平衡项 | rule | 主需 | 给出期初留存收益需滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用资产滚动模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面要求FCFF完整桥 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数与年中折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 库存股期权与RSU稀释 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值必然涉及 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅计估值日后活动 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 重算对比独立真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示扰动检查 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示两组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 自由布局语义键发现 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 债务利息易致循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo.md |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需期间与项目标签 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入包数值须一致 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM推导 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加5期预测序列 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 原始披露期不得改写 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 存在非经常收益需规范化剔除 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数年中折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 题面要求完整FCFF桥 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 退出倍数终值需引用可见单元格 |

### BC02（BC）

<details><summary>BC02｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC02",
  "seed": 393685,
  "candidate_index": 17,
  "family": "BC",
  "step": 1,
  "company": "澄川精密",
  "dimension_selection": {
    "scenario": "城市补给门店",
    "difficulty": "L3: 依赖深度7，显式6期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "stores",
    "valuation_mechanism": "gordon",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "debt_schedule_dcf",
    "output_template": "mixed",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "debt_schedule",
    "capm",
    "nol",
    "rolling_assets",
    "nol",
    "three_statements"
  ],
  "selection_rationale": {
    "scenario": "城市补给门店要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "stores",
    "unit": "家",
    "price_unit": "百万元/店/年",
    "description": "城市补给门店"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-09-03",
  "last_fy_end": "2026-05-31",
  "horizon": 6,
  "history": [
    {
      "start": "2023-12-01",
      "end": "2024-02-29",
      "fiscal_year": "2024",
      "revenue": 236.774098,
      "ebit": 24.449955,
      "operating_cost_ex_sbc": 193.669187,
      "sbc": 5.756508,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-03-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 243.126574,
      "ebit": 26.30145,
      "operating_cost_ex_sbc": 197.895115,
      "sbc": 5.91095,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-06-01",
      "end": "2024-08-31",
      "fiscal_year": "2025",
      "revenue": 249.47905,
      "ebit": 28.215418,
      "operating_cost_ex_sbc": 202.070351,
      "sbc": 6.065393,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-09-01",
      "end": "2024-11-30",
      "fiscal_year": "2025",
      "revenue": 255.831525,
      "ebit": 30.191861,
      "operating_cost_ex_sbc": 206.194894,
      "sbc": 6.219837,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-12-01",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "revenue": 262.184001,
      "ebit": 32.230777,
      "operating_cost_ex_sbc": 210.268744,
      "sbc": 6.374279,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-03-01",
      "end": "2025-05-31",
      "fiscal_year": "2025",
      "revenue": 268.536477,
      "ebit": 34.332166,
      "operating_cost_ex_sbc": 214.291902,
      "sbc": 6.528723,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-06-01",
      "end": "2025-08-31",
      "fiscal_year": "2026",
      "revenue": 274.888953,
      "ebit": 36.49603,
      "operating_cost_ex_sbc": 218.264367,
      "sbc": 6.683165,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-09-01",
      "end": "2025-11-30",
      "fiscal_year": "2026",
      "revenue": 281.241429,
      "ebit": 38.722367,
      "operating_cost_ex_sbc": 222.186139,
      "sbc": 6.837608,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-12-01",
      "end": "2026-02-28",
      "fiscal_year": "2026",
      "revenue": 287.593904,
      "ebit": 41.011178,
      "operating_cost_ex_sbc": 226.057219,
      "sbc": 6.992051,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2026-03-01",
      "end": "2026-05-31",
      "fiscal_year": "2026",
      "revenue": 293.94638,
      "ebit": 43.362463,
      "operating_cost_ex_sbc": 229.877605,
      "sbc": 7.146494,
      "nonrecurring_gain": 3.471033
    }
  ],
  "opening_nwc": 409.057188,
  "opening_deferred": 0.0,
  "opening_ppe": 344.41,
  "opening_rou": 0.0,
  "opening_debt": 222.2,
  "opening_retained_earnings": 177.76,
  "contributed_capital": 433.29,
  "opening_cash": 111.1,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 157,
    "price0": 7.0764331,
    "driver_add": [
      12.56,
      14.287,
      16.014,
      17.741,
      19.468,
      21.195
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054,
      0.045
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065,
      0.07
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022,
      0.02
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188,
      0.195
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065,
      0.069
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186,
      0.192
    ],
    "tax": 0.235,
    "wacc": 0.105,
    "g": 0.024,
    "gordon_weight": 1.0,
    "exit_multiple": 8.4,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51,
      52
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58,
      57
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47,
      48
    ],
    "nol0": 122.21,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      19.997999999999998,
      19.997999999999998,
      19.997999999999998,
      19.997999999999998,
      19.997999999999998,
      19.997999999999998
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      27.775000000000002,
      0,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      11.11,
      22.22,
      33.33,
      44.44,
      55.55,
      66.66
    ],
    "beta_unlevered": 0.8,
    "target_de": 0.33,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      21.4,
      25.4,
      29.4,
      33.4,
      37.4,
      41.4
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 111.1,
    "debt": 222.2,
    "investments": 16.665,
    "lease_liability": 0.0,
    "minority": 13.332,
    "valuation_cash_adjustment": 13.332,
    "shares": 161,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 16.1
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 374.407,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 433.29,
    "opening_cash": 111.1,
    "opening_operating_current_assets": 374.407,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 110.6,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge",
    "cash_tax_nol"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "cash_tax_nol": "现金税与 NOL"
  },
  "c_structure": "three_statements_dcf",
  "c_structure_definition": "三表＋DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge",
      "cash_tax_nol"
    ],
    "c": "three_statements_dcf"
  },
  "opening_nwc_last_fye": 409.057188,
  "opening_nwc_valuation_date": 374.407,
  "market": {
    "market_price": 14.82
  }
}
```

</details>

##### BC02｜澄川精密估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题需先搭建利润表、资产负债表和现金流量表三张预测报表，再在其上完成 DCF。
公司财年截至每年 5 月 31 日，最近完整财年末为 `2026-05-31`，估值日 `2026-09-03` 落在财年中间。预测共 6 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
公司期初有可结转的税务亏损（nol0）：现金税须先用亏损抵减应税利润，并逐期滚动亏损余额，不能直接按 EBIT×税率计税。
三表须勾稽：现金与现金流量表一致、留存收益由净利润滚动、资产等于负债加权益，不得使用不透明平衡项。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC02 选用的 rubric（50 条，权重合计 130；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需output.xlsx与memo.md |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 季度历史需聚合非自然财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 末季含非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 门店存量含流失与新增 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 门店驱动收入需平均基数 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率不同 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | NWC变动期初期末与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用最近财年末余额 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用DSO/DIO/DPO天数法 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 启用债务计划表 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | 启用NOL模块 |
| 04-BALANCE | 三表勾稽 | 每个预测期资产等于负债加权益 | rule | 主需 | 题面要求资产等于负债加权益 |
| 04-CASH | 三表勾稽 | 资产负债表现金与现金流量表期末现金一致 | rule | 主需 | 题面要求现金与现金流量表一致 |
| 04-RE | 三表勾稽 | 留存收益由净利润滚动且无不透明平衡项 | rule | 主需 | 题面要求留存收益滚动无平衡项 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用资产滚动且三表必需 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 无杠杆FCFF为DCF核心 |
| 05-WACC | DCF与估值桥 | WACC 使用 CAPM 再杠杆和税后债务成本 | rule | 主需 | 启用CAPM模块 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 题面要求实际天数期末折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 题面含库存股期权与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值为必然输出 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 题面要求残期仅计估值日后 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不得硬编码假设 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | 残期加多期需列对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 债务利息易致循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo.md |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需期间项目标签 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须与输入包一致 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM须按题面推导 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 季度/财年/LTM不得混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加6个完整财年 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径历史预测一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 须保留历史事实 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史含非经常收益需单列调整 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | DCF需拆分FCFF各组成项 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值引用可见单元格 |

### BC03（BC）

<details><summary>BC03｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC03",
  "seed": 394662,
  "candidate_index": 0,
  "family": "BC",
  "step": 1,
  "company": "岚衡多业",
  "dimension_selection": {
    "scenario": "企业档案订阅",
    "difficulty": "L1: 依赖深度6，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "subscription",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "SBC经营成本",
    "output_mode": "segment_dcf",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets"
  ],
  "selection_rationale": {
    "scenario": "企业档案订阅要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "subscription",
    "unit": "千家客户",
    "price_unit": "百万元/千家客户/年",
    "description": "企业档案订阅"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2024-05-10",
  "last_fy_end": "2024-02-28",
  "horizon": 4,
  "history": [
    {
      "start": "2021-09-01",
      "end": "2021-11-30",
      "fiscal_year": "2022",
      "revenue": 266.090471,
      "ebit": 27.461718,
      "operating_cost_ex_sbc": 217.376666,
      "sbc": 6.461175,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2021-12-01",
      "end": "2022-02-28",
      "fiscal_year": "2022",
      "revenue": 273.229484,
      "ebit": 29.541281,
      "operating_cost_ex_sbc": 222.1199,
      "sbc": 6.634523,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-03-01",
      "end": "2022-05-31",
      "fiscal_year": "2023",
      "revenue": 280.368497,
      "ebit": 31.691014,
      "operating_cost_ex_sbc": 226.806235,
      "sbc": 6.807872,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-06-01",
      "end": "2022-08-31",
      "fiscal_year": "2023",
      "revenue": 287.507509,
      "ebit": 33.910916,
      "operating_cost_ex_sbc": 231.435673,
      "sbc": 6.981221,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-09-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 294.646522,
      "ebit": 36.200987,
      "operating_cost_ex_sbc": 236.008213,
      "sbc": 7.154569,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-12-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 301.785535,
      "ebit": 38.561227,
      "operating_cost_ex_sbc": 240.523854,
      "sbc": 7.327918,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-03-01",
      "end": "2023-05-28",
      "fiscal_year": "2024",
      "revenue": 308.924547,
      "ebit": 40.991637,
      "operating_cost_ex_sbc": 244.982597,
      "sbc": 7.501266,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-05-29",
      "end": "2023-08-28",
      "fiscal_year": "2024",
      "revenue": 316.06356,
      "ebit": 43.492216,
      "operating_cost_ex_sbc": 249.384442,
      "sbc": 7.674615,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-08-29",
      "end": "2023-11-28",
      "fiscal_year": "2024",
      "revenue": 323.202573,
      "ebit": 46.062965,
      "operating_cost_ex_sbc": 253.729389,
      "sbc": 7.847963,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-11-29",
      "end": "2024-02-28",
      "fiscal_year": "2024",
      "revenue": 330.341585,
      "ebit": 48.703883,
      "operating_cost_ex_sbc": 258.017438,
      "sbc": 8.021311,
      "nonrecurring_gain": 3.89593
    }
  ],
  "opening_nwc": 420.239,
  "opening_deferred": 0,
  "opening_ppe": 386.57,
  "opening_rou": 0,
  "opening_debt": 249.4,
  "opening_retained_earnings": 199.52,
  "contributed_capital": 486.33,
  "opening_cash": 124.7,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 72,
    "price0": 17.3194444,
    "driver_add": [
      5.76,
      6.552,
      7.344,
      8.136
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.103,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 7.8,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 137.17,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      31.175,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.47,
      24.94,
      37.410000000000004,
      49.88
    ],
    "beta_unlevered": 0.76,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      23.1,
      27.1,
      31.1,
      35.1
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 124.7,
    "debt": 249.4,
    "investments": 18.705,
    "lease_liability": 0,
    "minority": 14.964,
    "valuation_cash_adjustment": 14.964,
    "shares": 110,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 11.0
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 513.764,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 486.33,
    "opening_cash": 124.7,
    "opening_operating_current_assets": 513.764,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 117.9,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "segment_sotp",
  "c_structure_definition": "分部经营模型＋SOTP",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge"
    ],
    "c": "segment_sotp"
  },
  "market": {
    "market_price": 15.73
  },
  "segments": {
    "segment_alpha": {
      "driver0": 80,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055
      ],
      "driver_add": [
        10.2,
        11.2,
        12.2,
        13.2
      ],
      "price0": 8.46,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997
      ],
      "ebit_margin": [
        0.19,
        0.193,
        0.196,
        0.199
      ],
      "capex_pct": [
        0.065,
        0.065,
        0.065,
        0.065
      ],
      "nwc_pct": [
        0.14,
        0.14,
        0.14,
        0.14
      ],
      "opening_nwc": 56,
      "opening_ppe": 133,
      "wacc_delta": -0.007,
      "method": "gordon"
    },
    "segment_beta": {
      "driver0": 105,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055
      ],
      "driver_add": [
        12.2,
        13.2,
        14.2,
        15.2
      ],
      "price0": 10.56,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997
      ],
      "ebit_margin": [
        0.225,
        0.228,
        0.231,
        0.234
      ],
      "capex_pct": [
        0.079,
        0.079,
        0.079,
        0.079
      ],
      "nwc_pct": [
        0.185,
        0.185,
        0.185,
        0.185
      ],
      "opening_nwc": 85,
      "opening_ppe": 191,
      "wacc_delta": 0.005999999999999999,
      "method": "exit"
    }
  }
}
```

</details>

##### BC03｜岚衡多业估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司由两个经营特征不同的分部组成，需要分别建模估值，再按分部加总（SOTP）得到公司价值。
公司财年截至每年 2 月 28 日，最近完整财年末为 `2024-02-28`，估值日 `2024-05-10` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
两个分部各自独立预测经营基数、单位收入、利润率、资本开支、折旧、NWC 与 FCFF，分别按题设 DCF 或退出倍数估值。公司层净债务和稀释股数只在加总后使用一次。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC03 选用的 rubric（49 条，权重合计 131；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值公式 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需output.xlsx与memo.md |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需Results页并保留Inputs页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 季度历史需按非自然财年聚合 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 末季含非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 订阅客户存量含流失与新增 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 收入按平均客户数及残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 分部EBIT按各期利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期ΔNWC期初期末与符号 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用营运资本天数法 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期ΔNWC用估值日余额 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 新增无形资产需独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用rolling_assets模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 分部FCFF必需口径 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数年中折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | 双终值机制题设 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 库存股期权与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值输出 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 新增无形资产需扣减 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅估值日后活动 |
| C-MULTI-SPLIT | DCF与估值桥 | Gordon 与退出倍数估值分别给出，不只输出加权结果 | rule | 主需 | 分部分别用DCF或退出倍数估值 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第一组 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第二组 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 题面禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由，按键发现 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需清晰期间标签 |
| C-SOTP-SEG | 经营预测 | 每个分部有独立的收入、利润率、再投资和 FCFF | rule | 主需 | 题面要求分部独立预测 |
| C-SOTP-VAL | 经营预测 | 每个分部按题面指定方法（DCF 或倍数）单独估值 | rule | 主需 | 分部按DCF或倍数估值 |
| C-SOTP-SUM | 经营预测 | SOTP 企业价值等于各分部价值之和，公司层费用按题面处理 | rule | 主需 | SOTP加总分部价值 |
| C-SOTP-BRIDGE | 经营预测 | 净债务与稀释股数只在公司层扣减一次，不在分部重复扣减 | rule | 主需 | 净债务股数仅用一次 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入值 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM须按题设窗口 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加4期预测序列 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径历史预测一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 须保留历史事实不被覆盖 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | 双终值机制共用显性期现值 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史含非经常收益需单独调整 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数年中折现需显示期数 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 分部FCFF构建须分项可见 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 双终值须引用终期指标与假设 |

### BC04（BC）

<details><summary>BC04｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC04",
  "seed": 395639,
  "candidate_index": 7,
  "family": "BC",
  "step": 1,
  "company": "微禾生科",
  "dimension_selection": {
    "scenario": "商用设备巡检",
    "difficulty": "L1: 依赖深度6，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "installed_base",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "dcf_only",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "capm",
    "nwc_days"
  ],
  "selection_rationale": {
    "scenario": "商用设备巡检要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "installed_base",
    "unit": "千台",
    "price_unit": "百万元/台次",
    "description": "商用设备巡检"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-05-24",
  "last_fy_end": "2025-10-31",
  "horizon": 5,
  "history": [
    {
      "start": "2022-11-01",
      "end": "2023-04-30",
      "fiscal_year": "2023",
      "revenue": 525.58146,
      "ebit": 54.211746,
      "operating_cost_ex_sbc": 428.826462,
      "sbc": 12.746182,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-05-01",
      "end": "2023-10-31",
      "fiscal_year": "2023",
      "revenue": 539.682426,
      "ebit": 58.316979,
      "operating_cost_ex_sbc": 438.183603,
      "sbc": 13.088153,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-11-01",
      "end": "2024-04-30",
      "fiscal_year": "2024",
      "revenue": 553.783392,
      "ebit": 62.560732,
      "operating_cost_ex_sbc": 447.4285,
      "sbc": 13.430124,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-05-01",
      "end": "2024-10-31",
      "fiscal_year": "2024",
      "revenue": 567.884358,
      "ebit": 66.943006,
      "operating_cost_ex_sbc": 456.561151,
      "sbc": 13.772095,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-11-01",
      "end": "2025-04-30",
      "fiscal_year": "2025",
      "revenue": 581.985324,
      "ebit": 71.463799,
      "operating_cost_ex_sbc": 465.581558,
      "sbc": 14.114065,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-05-01",
      "end": "2025-10-31",
      "fiscal_year": "2025",
      "revenue": 596.08629,
      "ebit": 76.123113,
      "operating_cost_ex_sbc": 474.48972,
      "sbc": 14.456036,
      "nonrecurring_gain": 7.021258
    }
  ],
  "opening_nwc": 414.51,
  "opening_deferred": 0,
  "opening_ppe": 381.3,
  "opening_rou": 0,
  "opening_debt": 246.0,
  "opening_retained_earnings": 196.8,
  "contributed_capital": 479.7,
  "opening_cash": 123.0,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 107,
    "price0": 3.5922897,
    "driver_add": [
      8.56,
      9.737,
      10.914,
      12.091,
      13.268
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.109,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 8.4,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 135.3,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      30.75,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.3,
      24.6,
      36.900000000000006,
      49.2,
      61.5
    ],
    "beta_unlevered": 0.88,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "service_frequency": [
      3.2,
      3.2800000000000002,
      3.3600000000000003,
      3.4400000000000004,
      3.52
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      24.8,
      28.8,
      32.8,
      36.8,
      40.8
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 123.0,
    "debt": 246.0,
    "investments": 18.45,
    "lease_liability": 0,
    "minority": 14.76,
    "valuation_cash_adjustment": 14.76,
    "shares": 131,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 13.1
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 414.51,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 479.7,
    "opening_cash": 123.0,
    "opening_operating_current_assets": 414.51,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 125.2,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "risk_adjusted_pipeline",
  "c_structure_definition": "风险调整管线 DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge"
    ],
    "c": "risk_adjusted_pipeline"
  },
  "market": {
    "market_price": 16.64
  },
  "projects": {
    "project_atlas": {
      "commissioning_period": 2,
      "construction_capex": [
        76,
        0,
        0,
        0,
        0
      ],
      "project_revenue": [
        105.8,
        121.8,
        137.8,
        153.8,
        169.8
      ],
      "project_margin": 0.21,
      "project_da": [
        7,
        9,
        11,
        13,
        15
      ],
      "project_operating_capex": [
        8,
        8,
        8,
        8,
        8
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5,
        6
      ],
      "project_fcff": [
        -76,
        17.56717,
        21.13757,
        24.70797,
        28.27837
      ],
      "success_probability": 0.67
    },
    "project_boreal": {
      "commissioning_period": 3,
      "construction_capex": [
        0,
        105,
        0,
        0,
        0
      ],
      "project_revenue": [
        128.8,
        144.8,
        160.8,
        176.8,
        192.8
      ],
      "project_margin": 0.245,
      "project_da": [
        7,
        9,
        11,
        13,
        15
      ],
      "project_operating_capex": [
        11,
        11,
        11,
        11,
        11
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5,
        6
      ],
      "project_fcff": [
        0,
        -105,
        26.13794,
        30.13674,
        34.13554
      ],
      "success_probability": 0.53
    }
  }
}
```

</details>

##### BC04｜微禾生科估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司价值由已有业务和两个在建项目组成，项目需按投产时间和成功概率做风险调整后估值。
公司财年截至每年 10 月 31 日，最近完整财年末为 `2025-10-31`，估值日 `2026-05-24` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
项目投产期之前收入必须为零；建设期支出独立计入对应期间。项目经营 FCFF 单列后乘成功概率，概率不得加到 WACC。已有业务价值与项目风险调整现值分开列示后相加。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC04 选用的 rubric（50 条，权重合计 132；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 1 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须提交output.xlsx工作簿 |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一且为数值 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需同时交付xlsx与memo.md |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需Results页及保留Inputs页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史需聚合完整财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 存在非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 装机基数滚动驱动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均基数及残期比例算收入 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期ΔNWC用估值日余额 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用NWC天数法 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | FCFF约束NOL抵扣 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 新增无形资产独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用资产滚动模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为必然核心 |
| 05-WACC | DCF与估值桥 | WACC 使用 CAPM 再杠杆和税后债务成本 | rule | 主需 | 启用CAPM模块 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数期末折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | 估值机制为双终值 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 期权库存股法与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值必然输出 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题面含新增无形资产 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅含估值日后活动 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | BC题有独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 自由布局按语义键发现 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo说明驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需明确期间与项目标签 |
| C-PIPE-TIMING | 经营预测 | 未投产或未上市项目在投产日前不产生收入 | rule | 主需 | 题面要求投产前收入为零 |
| C-PIPE-CAPEX | 经营预测 | 建设期支出与投产期收入分别建模并计入对应期间 | rule | 主需 | 建设期支出独立计入对应期 |
| C-PIPE-PROB | 经营预测 | 成功概率作用于项目现金流或项目价值，不通过调整 WACC 体现 | rule | 主需 | 概率乘FCFF不加WACC |
| C-PIPE-SUM | 经营预测 | 公司价值等于各项目风险调整价值之和加已有业务价值 | rule | 主需 | 已有业务与项目价值分列相加 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入值 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM须按题面推导 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 半年期、财年与LTM不得混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加5期预测序列须一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 历史披露期不得被改写 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | spec为双终值机制 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史含非经常收益需规范化 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF构建必然涉及 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 双终值引用终期指标 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 程序强制必选项 |

### BC05（BC）

<details><summary>BC05｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC05",
  "seed": 396616,
  "candidate_index": 14,
  "family": "BC",
  "step": 1,
  "company": "杉湾冷链",
  "dimension_selection": {
    "scenario": "区域低温加工",
    "difficulty": "L2: 依赖深度7，显式6期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "capacity",
    "valuation_mechanism": "exit",
    "accounting_basis": "SBC经营成本",
    "output_mode": "three_statements_dcf",
    "output_template": "mixed",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days",
    "scenario"
  ],
  "selection_rationale": {
    "scenario": "区域低温加工要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "capacity",
    "unit": "千吨年产能",
    "price_unit": "百万元/千吨",
    "description": "区域低温加工"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2027-03-07",
  "last_fy_end": "2026-08-31",
  "horizon": 6,
  "history": [
    {
      "start": "2024-03-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 186.749977,
      "ebit": 19.251712,
      "operating_cost_ex_sbc": 152.181098,
      "sbc": 4.52334,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-06-01",
      "end": "2024-08-31",
      "fiscal_year": "2024",
      "revenue": 191.760343,
      "ebit": 20.709566,
      "operating_cost_ex_sbc": 155.501742,
      "sbc": 4.644699,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-09-01",
      "end": "2024-11-30",
      "fiscal_year": "2025",
      "revenue": 196.770708,
      "ebit": 22.21661,
      "operating_cost_ex_sbc": 158.782553,
      "sbc": 4.766056,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-12-01",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "revenue": 201.781073,
      "ebit": 23.772846,
      "operating_cost_ex_sbc": 162.023531,
      "sbc": 4.887415,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-03-01",
      "end": "2025-05-31",
      "fiscal_year": "2025",
      "revenue": 206.791438,
      "ebit": 25.378274,
      "operating_cost_ex_sbc": 165.224675,
      "sbc": 5.008772,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-06-01",
      "end": "2025-08-31",
      "fiscal_year": "2025",
      "revenue": 211.801804,
      "ebit": 27.032892,
      "operating_cost_ex_sbc": 168.385986,
      "sbc": 5.13013,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-09-01",
      "end": "2025-11-30",
      "fiscal_year": "2026",
      "revenue": 216.812169,
      "ebit": 28.736703,
      "operating_cost_ex_sbc": 171.507464,
      "sbc": 5.251488,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-12-01",
      "end": "2026-02-28",
      "fiscal_year": "2026",
      "revenue": 221.822534,
      "ebit": 30.489704,
      "operating_cost_ex_sbc": 174.589108,
      "sbc": 5.372846,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2026-03-01",
      "end": "2026-05-31",
      "fiscal_year": "2026",
      "revenue": 226.832899,
      "ebit": 32.291897,
      "operating_cost_ex_sbc": 177.63092,
      "sbc": 5.494204,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2026-06-01",
      "end": "2026-08-31",
      "fiscal_year": "2026",
      "revenue": 231.843265,
      "ebit": 34.143281,
      "operating_cost_ex_sbc": 180.632898,
      "sbc": 5.615562,
      "nonrecurring_gain": 2.727463
    }
  ],
  "opening_nwc": 294.201,
  "opening_deferred": 0,
  "opening_ppe": 270.63,
  "opening_rou": 0,
  "opening_debt": 174.6,
  "opening_retained_earnings": 139.68,
  "contributed_capital": 340.47,
  "opening_cash": 87.3,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 142,
    "price0": 8.3079558,
    "driver_add": [
      11.36,
      12.922,
      14.484,
      16.046,
      17.608,
      19.17
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054,
      0.045
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065,
      0.07
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022,
      0.02
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188,
      0.195
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065,
      0.069
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186,
      0.192
    ],
    "tax": 0.235,
    "wacc": 0.107,
    "g": 0.024,
    "gordon_weight": 1.0,
    "exit_multiple": 9.0,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51,
      52
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58,
      57
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47,
      48
    ],
    "nol0": 96.03,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      21.825000000000003,
      0,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      8.73,
      17.46,
      26.19,
      34.92,
      43.650000000000006,
      52.38
    ],
    "beta_unlevered": 0.84,
    "target_de": 0.33,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "utilization": [
      0.74,
      0.758,
      0.776,
      0.794,
      0.8119999999999999,
      0.83
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      26.5,
      30.5,
      34.5,
      38.5,
      42.5,
      46.5
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 87.3,
    "debt": 174.6,
    "investments": 13.095,
    "lease_liability": 0,
    "minority": 10.476,
    "valuation_cash_adjustment": 10.476,
    "shares": 152,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 15.2
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 294.201,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 340.47,
    "opening_cash": 87.3,
    "opening_operating_current_assets": 294.201,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 132.5,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge",
    "dual_terminal"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_terminal": "Gordon、退出倍数、双终值加权"
  },
  "c_structure": "scenario_operating_model",
  "c_structure_definition": "情景驱动 Operating Model",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "dual_terminal"
    ],
    "c": "scenario_operating_model"
  },
  "market": {
    "market_price": 17.55
  }
}
```

</details>

##### BC05｜杉湾冷链估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

管理层给出 Base、Bull、Bear 三套经营方案，需要搭建可一键切换情景的经营模型并完成 DCF。
公司财年截至每年 8 月 31 日，最近完整财年末为 `2026-08-31`，估值日 `2027-03-07` 落在财年中间。预测共 6 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
终值的 Gordon 永续增长法与退出倍数法都要单独列示；按输入中的 Gordon 权重（本题为 100%）计入估值。
设置 `Cases` 页，唯一选择格链接 `a.scenario`（1=Base、2=Bull、3=Bear）。需求、利润率、再投资、FCFF、终值与每股价值必须随同一开关联动；另分别保留三情景独立输出，不能只交一张敏感性表。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC05 选用的 rubric（51 条，权重合计 135；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | Results页输出键唯一数值 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | output.xlsx与memo.md须存在 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 须有Inputs/Cases/Results页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 季度历史需按非自然财年聚合 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 末季含非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面要求SBC作经营成本 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 产能含新增与流失滚动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 收入按平均产能与残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率向量 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期NWC差额与符号 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用营运资本天数法 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 三表含借还款计划 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用估值日余额 |
| 04-BALANCE | 三表勾稽 | 每个预测期资产等于负债加权益 | rule | 主需 | 三表输出模式需资产负债平衡 |
| 04-CASH | 三表勾稽 | 资产负债表现金与现金流量表期末现金一致 | rule | 主需 | 现金从opening_cash滚动需一致 |
| 04-RE | 三表勾稽 | 留存收益由净利润滚动且无不透明平衡项 | rule | 主需 | 三表留存收益需净利润滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用rolling_assets模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为估值核心 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数年中折现明确要求 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | 题面要求双终值加权 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 库存股期权与RSU稀释 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值为必需输出 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅计估值日后活动 |
| C-CASE-SWITCH | DCF与估值桥 | 单一情景开关切换后收入、利润率、再投资、FCFF、终值和每股价值同时改变 | rule | 主需 | 题面要求单一开关全链联动 |
| C-CASE-ISOLATE | DCF与估值桥 | 每个情景的输出值与独立真值一致，情景之间不相互覆盖 | rule | 次需 | 要求三情景独立输出 |
| C-MULTI-SPLIT | DCF与估值桥 | Gordon 与退出倍数估值分别给出，不只输出加权结果 | rule | 主需 | 题面列Gordon与退出倍数 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为唯一活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 重算对比独立真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第一组 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第二组 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 自由布局语义键发现 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 利息债务易致循环引用 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入值须与输入包一致 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM推导需正确 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 季度/财年/LTM不得混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加6期预测序列 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 须保留历史事实 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | Gordon与退出倍数双终值 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 末期存在非经常收益需剔除 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数年中折现需显示期数 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF需拆分各组成项 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon与退出倍数终值 |

### BC06（BC）

<details><summary>BC06｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC06",
  "seed": 397593,
  "candidate_index": 21,
  "family": "BC",
  "step": 1,
  "company": "远岱材料",
  "dimension_selection": {
    "scenario": "远程运维席位",
    "difficulty": "L3: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "subscription",
    "valuation_mechanism": "gordon",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "debt_schedule_dcf",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets",
    "dual_terminal"
  ],
  "selection_rationale": {
    "scenario": "远程运维席位要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": true
  },
  "business": {
    "driver": "subscription",
    "unit": "千席位",
    "price_unit": "百万元/千席位/年",
    "description": "远程运维席位"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2024-11-18",
  "last_fy_end": "2024-05-31",
  "horizon": 4,
  "history": [
    {
      "start": "2021-12-01",
      "end": "2022-02-28",
      "fiscal_year": "2022",
      "revenue": 263.44632,
      "ebit": 27.142939,
      "operating_cost_ex_sbc": 214.413231,
      "sbc": 6.373091,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-03-01",
      "end": "2022-05-31",
      "fiscal_year": "2022",
      "revenue": 270.514392,
      "ebit": 29.198362,
      "operating_cost_ex_sbc": 219.091802,
      "sbc": 6.544077,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-06-01",
      "end": "2022-08-31",
      "fiscal_year": "2023",
      "revenue": 277.582464,
      "ebit": 31.323141,
      "operating_cost_ex_sbc": 223.71425,
      "sbc": 6.715062,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-09-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 284.650536,
      "ebit": 33.517274,
      "operating_cost_ex_sbc": 228.280576,
      "sbc": 6.886047,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-12-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 291.718608,
      "ebit": 35.780761,
      "operating_cost_ex_sbc": 232.790779,
      "sbc": 7.057033,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-03-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 298.78668,
      "ebit": 38.113604,
      "operating_cost_ex_sbc": 237.24486,
      "sbc": 7.228018,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-06-01",
      "end": "2023-08-31",
      "fiscal_year": "2024",
      "revenue": 305.854752,
      "ebit": 40.515801,
      "operating_cost_ex_sbc": 241.642818,
      "sbc": 7.399003,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-09-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 312.922824,
      "ebit": 42.987354,
      "operating_cost_ex_sbc": 245.984655,
      "sbc": 7.569989,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-12-01",
      "end": "2024-02-29",
      "fiscal_year": "2024",
      "revenue": 319.990896,
      "ebit": 45.528261,
      "operating_cost_ex_sbc": 250.270368,
      "sbc": 7.740974,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-03-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 327.058968,
      "ebit": 48.138522,
      "operating_cost_ex_sbc": 254.499959,
      "sbc": 7.91196,
      "nonrecurring_gain": 3.842818
    }
  ],
  "opening_nwc": 432.52904,
  "opening_deferred": 0,
  "opening_ppe": 381.3,
  "opening_rou": 0,
  "opening_debt": 246.0,
  "opening_retained_earnings": 196.8,
  "contributed_capital": 479.7,
  "opening_cash": 123.0,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 177,
    "price0": 6.9491525,
    "driver_add": [
      14.16,
      16.107,
      18.054,
      20.001
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.1052,
    "g": 0.022,
    "gordon_weight": 0.6,
    "exit_multiple": 8.1,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 135.3,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      30.75,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.3,
      24.6,
      36.900000000000006,
      49.2
    ],
    "beta_unlevered": 0.8,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      28.2,
      32.2,
      36.2,
      40.2
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 123.0,
    "debt": 246.0,
    "investments": 18.45,
    "lease_liability": 0,
    "minority": 14.76,
    "valuation_cash_adjustment": 14.76,
    "shares": 173,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 17.3
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 488.31,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 479.7,
    "opening_cash": 123.0,
    "opening_operating_current_assets": 488.31,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 139.8,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge",
    "dual_terminal"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_terminal": "Gordon、退出倍数、双终值加权"
  },
  "c_structure": "multi_method",
  "c_structure_definition": "多方法估值与反推",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge",
      "dual_terminal"
    ],
    "c": "multi_method"
  },
  "opening_nwc_last_fye": 432.52904,
  "opening_nwc_valuation_date": 396.06,
  "market": {
    "market_price": 18.46
  }
}
```

</details>

##### BC06｜远岱材料估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题不只要一个目标价：需用 Gordon 与退出倍数两种方法分别估值，做反向推导，并给出估值区间。
公司财年截至每年 5 月 31 日，最近完整财年末为 `2024-05-31`，估值日 `2024-11-18` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
分别给出 Gordon 与退出倍数的终值、EV、股权价值和每股价值，不得加权成一个数。由 Gordon 终值反推隐含 EV/EBITDA，由退出倍数反推隐含 g，并用给定股价在工作簿内以公式迭代/求解隐含 WACC；Football Field 按给定折现率和增长区间。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC06 选用的 rubric（51 条，权重合计 131；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值活公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需output.xlsx与memo.md |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需Inputs页及Results页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 季度历史需按非自然财年聚合 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 末季含非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC须作经营成本 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 订阅席位含新增与流失 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均席位乘价格及残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率给定 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期ΔNWC差额与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用最近财年末余额 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用nwc_days模块 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 债务计划表输出模式 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 新增无形资产独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用rolling_assets模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为估值核心 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 题面要求实际天数期末折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 桥含库存股期权与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 需分别给出每股价值 |
| 05-SENS | DCF与估值桥 | 敏感性单元格使用各自行列假设而经营预测不变 | rule | 次需 | Football Field按折现率增长区间 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题面含新增无形资产 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅含估值日后活动 |
| C-MULTI-SPLIT | DCF与估值桥 | Gordon 与退出倍数估值分别给出，不只输出加权结果 | rule | 主需 | 题面要求两法分别给出不加权 |
| C-IMPLIED-MULT | DCF与估值桥 | 由 Gordon 终值反推的隐含 EV/EBITDA 计算正确 | rule | 主需 | 要求Gordon反推隐含EV/EBITDA |
| C-IMPLIED-G | DCF与估值桥 | 由退出倍数终值反推的隐含永续增长率计算正确 | rule | 主需 | 要求退出倍数反推隐含g |
| C-REVERSE | DCF与估值桥 | 由给定市场价格反推的隐含 WACC 或隐含增长假设正确，且以公式或求解过程得出 | rule | 主需 | 要求按股价公式求隐含WACC |
| C-RANGE | DCF与估值桥 | 估值区间的上下界分别来自题面指定的方法和假设范围 | rule | 次需 | Football Field按指定区间 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | BC题需独立数值真值核对 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查执行扰动一 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查执行扰动二 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页自由布局按键发现 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo.md |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需期间与项目标签 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 需聚合财年及估值日LTM |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加4个完整财年 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径须一致 |
| X-IC-001 | 公式与模型工程 | 敏感性表中与基准行列假设相交的单元格，其值与模型相同口径基准输出的相对差异不超过题面容差；题面未给容差时为 0.1%。 | rule | 主需 | Football Field 含基准组合 |
| X-IC-002 | 公式与模型工程 | 每条敏感性轴的完整值序列与题面指定的起点、终点及步长完全一致。 | rule | 主需 | 折现率与增长区间按给定值 |
| X-IC-003 | 公式与模型工程 | 在现金流与永续增长率保持为正且 WACC 大于永续增长率时，敏感性网格中折现率单调上升对应估值结果不上升。 | rule | 次需 | WACC 上升估值不升 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | Gordon 与退出倍数共用显性期现值 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 末季非经常收益需单独剔除 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数折现期需可见 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon与退出终值须引用单元格 |

### BC07（BC）

<details><summary>BC07｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC07",
  "seed": 398570,
  "candidate_index": 4,
  "family": "BC",
  "step": 1,
  "company": "沐原家居",
  "dimension_selection": {
    "scenario": "精密连接组件",
    "difficulty": "L1: 依赖深度6，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "volume_price",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "SBC经营成本",
    "output_mode": "segment_dcf",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets",
    "debt_schedule"
  ],
  "selection_rationale": {
    "scenario": "精密连接组件要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "volume_price",
    "unit": "百万件",
    "price_unit": "百万元/百万件",
    "description": "精密连接组件"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-07-26",
  "last_fy_end": "2025-02-28",
  "horizon": 5,
  "history": [
    {
      "start": "2022-03-01",
      "end": "2022-08-31",
      "fiscal_year": "2023",
      "revenue": 505.674279,
      "ebit": 52.070529,
      "operating_cost_ex_sbc": 411.045853,
      "sbc": 12.217682,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-09-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 519.24115,
      "ebit": 56.013617,
      "operating_cost_ex_sbc": 420.015015,
      "sbc": 12.545474,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-03-01",
      "end": "2023-08-31",
      "fiscal_year": "2024",
      "revenue": 532.808021,
      "ebit": 60.089753,
      "operating_cost_ex_sbc": 428.876586,
      "sbc": 12.873265,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-09-01",
      "end": "2024-02-29",
      "fiscal_year": "2025",
      "revenue": 546.374892,
      "ebit": 64.298939,
      "operating_cost_ex_sbc": 437.630567,
      "sbc": 13.201057,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-03-01",
      "end": "2024-08-31",
      "fiscal_year": "2025",
      "revenue": 559.941763,
      "ebit": 68.641174,
      "operating_cost_ex_sbc": 446.276957,
      "sbc": 13.528848,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-09-01",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "revenue": 573.508634,
      "ebit": 73.116457,
      "operating_cost_ex_sbc": 454.815756,
      "sbc": 13.85664,
      "nonrecurring_gain": 6.730133
    }
  ],
  "opening_nwc": 397.323,
  "opening_deferred": 0.0,
  "opening_ppe": 365.49,
  "opening_rou": 0.0,
  "opening_debt": 235.8,
  "opening_retained_earnings": 188.64,
  "contributed_capital": 459.81,
  "opening_cash": 117.9,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 92,
    "price0": 12.8152174,
    "driver_add": [
      7.36,
      8.372,
      9.384,
      10.396,
      11.408
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.103,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 9.0,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 129.69,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      21.221999999999998,
      21.221999999999998,
      21.221999999999998,
      21.221999999999998,
      21.221999999999998
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      29.475,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      11.790000000000001,
      23.580000000000002,
      35.370000000000005,
      47.160000000000004,
      58.95
    ],
    "beta_unlevered": 0.76,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      29.9,
      33.9,
      37.9,
      41.9,
      45.9
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 117.9,
    "debt": 235.8,
    "investments": 17.685,
    "lease_liability": 0.0,
    "minority": 14.148,
    "valuation_cash_adjustment": 14.148,
    "shares": 122,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 12.2
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 397.323,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 459.81,
    "opening_cash": 117.9,
    "opening_operating_current_assets": 397.323,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 147.1,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge",
    "debt_schedule"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "debt_schedule": "债务计划表"
  },
  "c_structure": "debt_schedule_dcf",
  "c_structure_definition": "债务计划表＋DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "debt_schedule"
    ],
    "c": "debt_schedule_dcf"
  },
  "market": {
    "market_price": 19.37
  }
}
```

</details>

##### BC07｜沐原家居估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司在预测期内有新增借款和还款安排，需要在 DCF 之外建立完整的债务计划表。
公司财年截至每年 2 月 28 日，最近完整财年末为 `2025-02-28`，估值日 `2025-07-26` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
借款、偿还、利息与期末债务逐期滚动连续，融资现金流与 FCFF 分离。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC07 选用的 rubric（50 条，权重合计 132；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读取的output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 公开输出键须唯一且为数值 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需交付output.xlsx与memo.md |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 要求Results页并保留Inputs页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史需聚合完整财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 存在非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC为经营成本不得加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 存在新增与流失驱动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 收入由平均基数乘单价及残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期给定EBIT利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期ΔNWC期初期末与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期须用估值日余额 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用营运资本天数模块 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 题面要求债务计划表 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | 约束规定NOL抵扣上限 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 新增无形资产需独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用资产滚动模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面规定FCFF口径 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数年中折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | 双终值机制 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 股权桥含现金债务少数股权 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 期权库存股法及RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值必然输出 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题面提及新增无形资产 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 残期仅计估值日后 |
| C-MULTI-SPLIT | DCF与估值桥 | Gordon 与退出倍数估值分别给出，不只输出加权结果 | rule | 主需 | 双终值机制需分别给出 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 重算对比独立真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第一组 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第二组 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 自由布局语义键发现 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不嵌假设常数 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | 多期列对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 债务利息易致循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求提交memo |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 要求可追溯模型需期间标签 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入值 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM须按历史推导 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 半年期、财年、LTM不得混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加5期预测序列 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 原始披露期不得改写 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | 双终值须共用显性期现值 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 存在非经常收益需规范化剔除 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数年中折现需显示期数 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | DCF需拆分FCFF各组成项 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 双终值需引用终期指标与假设 |

### BC08（BC）

<details><summary>BC08｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC08",
  "seed": 399547,
  "candidate_index": 11,
  "family": "BC",
  "step": 1,
  "company": "序光档案",
  "dimension_selection": {
    "scenario": "楼宇监测装机服务",
    "difficulty": "L2: 依赖深度6，显式6期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "installed_base",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "dcf_only",
    "output_template": "mixed",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "debt_schedule",
    "nwc_days"
  ],
  "selection_rationale": {
    "scenario": "楼宇监测装机服务要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "mixed_h1_q",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "installed_base",
    "unit": "千台",
    "price_unit": "百万元/台次",
    "description": "楼宇监测装机服务"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2027-02-14",
  "last_fy_end": "2026-10-31",
  "horizon": 6,
  "history": [
    {
      "start": "2023-11-01",
      "end": "2024-04-30",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 313.1,
      "operating_cost_ex_sbc": 247,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-05-01",
      "end": "2024-10-31",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 498.1,
      "operating_cost_ex_sbc": 392,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2024-11-01",
      "end": "2025-04-30",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 333.1,
      "operating_cost_ex_sbc": 261,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-05-01",
      "end": "2025-10-31",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 518.1,
      "operating_cost_ex_sbc": 406,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2025-11-01",
      "end": "2026-04-30",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 353.1,
      "operating_cost_ex_sbc": 275,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2026-05-01",
      "end": "2026-10-31",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 538.1,
      "operating_cost_ex_sbc": 420,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2026-11-01",
      "end": "2027-01-31",
      "fiscal_year": "2027",
      "period_type": "bridge_quarter",
      "revenue": 286.09999999999997,
      "operating_cost_ex_sbc": 215.2,
      "sbc": 5.7,
      "nonrecurring_gain": 1.1
    }
  ],
  "opening_nwc": 384.216244,
  "opening_deferred": 0.0,
  "opening_ppe": 323.33,
  "opening_rou": 0.0,
  "opening_debt": 208.6,
  "opening_retained_earnings": 166.88,
  "contributed_capital": 406.77,
  "opening_cash": 104.3,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 127,
    "price0": 2.566437,
    "driver_add": [
      10.16,
      11.557,
      12.954,
      14.351,
      15.748,
      17.145
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054,
      0.045
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065,
      0.07
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022,
      0.02
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188,
      0.195
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065,
      0.069
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186,
      0.192
    ],
    "tax": 0.235,
    "wacc": 0.109,
    "g": 0.024,
    "gordon_weight": 1.0,
    "exit_multiple": 8.1,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51,
      52
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58,
      57
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47,
      48
    ],
    "nol0": 114.73,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      18.773999999999997,
      18.773999999999997,
      18.773999999999997,
      18.773999999999997,
      18.773999999999997,
      18.773999999999997
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      26.075000000000003,
      0,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      10.43,
      20.86,
      31.29,
      41.72,
      52.15,
      62.58
    ],
    "beta_unlevered": 0.88,
    "target_de": 0.33,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "service_frequency": [
      3.2,
      3.2800000000000002,
      3.3600000000000003,
      3.4400000000000004,
      3.52,
      3.6
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      31.6,
      35.6,
      39.6,
      43.6,
      47.6,
      51.6
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 104.3,
    "debt": 208.6,
    "investments": 15.645,
    "lease_liability": 0.0,
    "minority": 12.516,
    "valuation_cash_adjustment": 12.516,
    "shares": 143,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 14.3
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 351.491,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 406.77,
    "opening_cash": 104.3,
    "opening_operating_current_assets": 351.491,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 154.4,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "mixed_ltm",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "simple_dcf",
  "c_structure_definition": "简版 DCF",
  "structure": {
    "b": [
      "mixed_ltm",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge"
    ],
    "c": "simple_dcf"
  },
  "opening_nwc_last_fye": 384.216244,
  "opening_nwc_valuation_date": 351.491,
  "market": {
    "market_price": 20.28
  }
}
```

</details>

##### BC08｜序光档案估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题交付单一主体的 DCF：从经营预测推出 FCFF，折现后经股权桥得到每股价值。
最近完整财年末为 `2026-10-31`，估值日为 `2027-02-14`。预测共 6 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
建立 EBIT、无杠杆现金税、折旧摊销、资本开支与 ΔNWC 到 FCFF 的完整桥，再折现并完成股权桥。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC08 选用的 rubric（42 条，权重合计 110；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值公式 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需output.xlsx与memo.md |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史需聚合完整财年 |
| B-MIXLTM | 历史与会计口径 | 混合历史 LTM 由最近完整半年加其后桥接季度构成，不重复计入、不遗漏、不年化 | rule | 主需 | 题面明确半年加桥接季度LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 历史含非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作经营成本不得加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 装机存量含流失与新增 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 存量驱动收入含残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率向量 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC期末差额与符号 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用营运资本天数法 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 启用债务计划表 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用最近财年末余额 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 新增无形资产独立滚动 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面要求完整FCFF桥 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数/365期末折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | spec为双终值机制 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面列明股权桥各项 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 题面要求库存股期权与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值为必然输出 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题面含新增无形资产 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅含估值日后活动 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页自由布局按键发现 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需期间项目标签 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入值 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | LTM指定半年加桥接季窗口 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 半年与季度不得混作财年 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加6期预测序列 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 须保留历史事实不被覆盖 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史含非经常收益需规范化 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 题面要求FCFF完整桥 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 双终值机制需引用可见单元格 |

### BC09（BC）

<details><summary>BC09｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC09",
  "seed": 400524,
  "candidate_index": 18,
  "family": "BC",
  "step": 1,
  "company": "洲禾联合",
  "dimension_selection": {
    "scenario": "特种涂层产线",
    "difficulty": "L3: 依赖深度8，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "capacity",
    "valuation_mechanism": "exit",
    "accounting_basis": "SBC经营成本",
    "output_mode": "three_statements_dcf",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days"
  ],
  "selection_rationale": {
    "scenario": "特种涂层产线要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "mixed_h1_q",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "capacity",
    "unit": "千吨年产能",
    "price_unit": "百万元/千吨",
    "description": "特种涂层产线"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2024-12-14",
  "last_fy_end": "2024-08-31",
  "horizon": 4,
  "history": [
    {
      "start": "2021-09-01",
      "end": "2022-02-28",
      "fiscal_year": "2022",
      "period_type": "half_year",
      "revenue": 327.8,
      "operating_cost_ex_sbc": 247,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-03-01",
      "end": "2022-08-31",
      "fiscal_year": "2022",
      "period_type": "half_year",
      "revenue": 512.8,
      "operating_cost_ex_sbc": 392,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2022-09-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "period_type": "half_year",
      "revenue": 347.8,
      "operating_cost_ex_sbc": 261,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-03-01",
      "end": "2023-08-31",
      "fiscal_year": "2023",
      "period_type": "half_year",
      "revenue": 532.8,
      "operating_cost_ex_sbc": 406,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2023-09-01",
      "end": "2024-02-29",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 367.8,
      "operating_cost_ex_sbc": 275,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-03-01",
      "end": "2024-08-31",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 552.8,
      "operating_cost_ex_sbc": 420,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2024-09-01",
      "end": "2024-11-30",
      "fiscal_year": "2025",
      "period_type": "bridge_quarter",
      "revenue": 298.0,
      "operating_cost_ex_sbc": 215.2,
      "sbc": 5.7,
      "nonrecurring_gain": 1.1
    }
  ],
  "opening_nwc": 402.846952,
  "opening_deferred": 0,
  "opening_ppe": 339.14,
  "opening_rou": 0,
  "opening_debt": 218.8,
  "opening_retained_earnings": 175.04,
  "contributed_capital": 426.66,
  "opening_cash": 109.4,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 162,
    "price0": 9.1257925,
    "driver_add": [
      12.96,
      14.742,
      16.524,
      18.306
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.107,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 120.34,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      27.35,
      0,
      0,
      0
    ],
    "debt_repayment": [
      10.94,
      21.88,
      32.82,
      43.76
    ],
    "beta_unlevered": 0.84,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "utilization": [
      0.74,
      0.758,
      0.776,
      0.794
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      33.3,
      37.3,
      41.3,
      45.3
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 109.4,
    "debt": 218.8,
    "investments": 16.41,
    "lease_liability": 0,
    "minority": 13.128,
    "valuation_cash_adjustment": 13.128,
    "shares": 164,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 16.4
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 450.728,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 426.66,
    "opening_cash": 109.4,
    "opening_operating_current_assets": 450.728,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 161.7,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "mixed_ltm",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "segment_sotp",
  "c_structure_definition": "分部经营模型＋SOTP",
  "structure": {
    "b": [
      "mixed_ltm",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge"
    ],
    "c": "segment_sotp"
  },
  "opening_nwc_last_fye": 402.846952,
  "opening_nwc_valuation_date": 368.678,
  "market": {
    "market_price": 21.19
  },
  "segments": {
    "segment_alpha": {
      "driver0": 98,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055
      ],
      "driver_add": [
        12.6,
        13.6,
        14.6,
        15.6
      ],
      "price0": 9.78,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997
      ],
      "ebit_margin": [
        0.19,
        0.193,
        0.196,
        0.199
      ],
      "capex_pct": [
        0.065,
        0.065,
        0.065,
        0.065
      ],
      "nwc_pct": [
        0.14,
        0.14,
        0.14,
        0.14
      ],
      "opening_nwc": 62,
      "opening_ppe": 145,
      "wacc_delta": -0.007,
      "method": "gordon"
    },
    "segment_beta": {
      "driver0": 123,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055
      ],
      "driver_add": [
        14.6,
        15.6,
        16.6,
        17.6
      ],
      "price0": 11.88,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997
      ],
      "ebit_margin": [
        0.225,
        0.228,
        0.231,
        0.234
      ],
      "capex_pct": [
        0.079,
        0.079,
        0.079,
        0.079
      ],
      "nwc_pct": [
        0.185,
        0.185,
        0.185,
        0.185
      ],
      "opening_nwc": 91,
      "opening_ppe": 203,
      "wacc_delta": 0.005999999999999999,
      "method": "exit"
    }
  }
}
```

</details>

##### BC09｜洲禾联合估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司由两个经营特征不同的分部组成，需要分别建模估值，再按分部加总（SOTP）得到公司价值。
最近完整财年末为 `2024-08-31`，估值日为 `2024-12-14`。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
两个分部各自独立预测经营基数、单位收入、利润率、资本开支、折旧、NWC 与 FCFF，分别按题设 DCF 或退出倍数估值。公司层净债务和稀释股数只在加总后使用一次。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC09 选用的 rubric（52 条，权重合计 138；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值公式 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需xlsx与memo.md两文件 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 指定Results与Inputs页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史需聚合完整财年 |
| B-MIXLTM | 历史与会计口径 | 混合历史 LTM 由最近完整半年加其后桥接季度构成，不重复计入、不遗漏、不年化 | rule | 主需 | 题面明确半年加桥接季LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC为经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 产能含新增与流失 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 产能存量驱动收入 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | NWC变动符号与期间 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用NWC天数模块 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 三表含借还款计划 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | 给定NOL抵扣约束 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用财年末余额 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 新增无形资产独立滚动 |
| 04-BALANCE | 三表勾稽 | 每个预测期资产等于负债加权益 | rule | 主需 | 三表输出需资产负债平衡 |
| 04-CASH | 三表勾稽 | 资产负债表现金与现金流量表期末现金一致 | rule | 主需 | 现金从期初滚动需勾稽 |
| 04-RE | 三表勾稽 | 留存收益由净利润滚动且无不透明平衡项 | rule | 主需 | 三表留存收益需净利润滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用滚动资产模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 分部FCFF口径必需 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数加年中折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 库存股期权与RSU稀释 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值必然输出 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题面含新增无形资产 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅含估值日后活动 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | BC题有独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由按键发现 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需期间项目标签 |
| C-SOTP-SEG | 经营预测 | 每个分部有独立的收入、利润率、再投资和 FCFF | rule | 主需 | 题面要求分部独立预测 |
| C-SOTP-VAL | 经营预测 | 每个分部按题面指定方法（DCF 或倍数）单独估值 | rule | 主需 | 分部分别DCF或倍数估值 |
| C-SOTP-SUM | 经营预测 | SOTP 企业价值等于各分部价值之和，公司层费用按题面处理 | rule | 主需 | SOTP加总为企业价值 |
| C-SOTP-BRIDGE | 经营预测 | 净债务与稀释股数只在公司层扣减一次，不在分部重复扣减 | rule | 主需 | 净债务股数仅加总后用一次 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入值 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | LTM指定半年加桥接季度窗口 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 半年与季度混合，不得混用期间 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加4个完整预测期 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | SBC与非经常项口径须一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 原始披露期不得改写 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo需与模型数值一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史含非经常收益需规范化 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数年中折现需显示期数 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 分部FCFF构建需分项列示 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 退出倍数终值需引用可见单元格 |

### BC10（BC）

<details><summary>BC10｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC10",
  "seed": 401501,
  "candidate_index": 1,
  "family": "BC",
  "step": 1,
  "company": "沛源新材",
  "dimension_selection": {
    "scenario": "城市补给门店",
    "difficulty": "L1: 依赖深度5，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "stores",
    "valuation_mechanism": "gordon",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "debt_schedule_dcf",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets",
    "intangible_pool"
  ],
  "selection_rationale": {
    "scenario": "城市补给门店要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "stores",
    "unit": "家",
    "price_unit": "百万元/店/年",
    "description": "城市补给门店"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-08-30",
  "last_fy_end": "2025-05-31",
  "horizon": 5,
  "history": [
    {
      "start": "2022-06-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 339.234,
      "ebit": 34.873255,
      "operating_cost_ex_sbc": 274.727847,
      "sbc": 8.165847,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-12-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 348.3354,
      "ebit": 37.514064,
      "operating_cost_ex_sbc": 280.722504,
      "sbc": 8.384931,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-06-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 357.4368,
      "ebit": 40.24398,
      "operating_cost_ex_sbc": 286.64525,
      "sbc": 8.604014,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-12-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 366.5382,
      "ebit": 43.063002,
      "operating_cost_ex_sbc": 292.496087,
      "sbc": 8.823098,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-06-01",
      "end": "2024-11-30",
      "fiscal_year": "2025",
      "revenue": 375.6396,
      "ebit": 45.971132,
      "operating_cost_ex_sbc": 298.275014,
      "sbc": 9.042182,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-12-01",
      "end": "2025-05-31",
      "fiscal_year": "2025",
      "revenue": 384.741,
      "ebit": 48.968369,
      "operating_cost_ex_sbc": 303.982032,
      "sbc": 9.261266,
      "nonrecurring_gain": 4.498172
    }
  ],
  "opening_nwc": 291.062704,
  "opening_deferred": 0,
  "opening_ppe": 244.28,
  "opening_rou": 0,
  "opening_debt": 157.6,
  "opening_retained_earnings": 126.08,
  "contributed_capital": 307.32,
  "opening_cash": 78.8,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 77,
    "price0": 10.2337662,
    "driver_add": [
      6.16,
      7.007,
      7.854,
      8.701,
      9.548
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.105,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 8.1,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 86.68,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      19.700000000000003,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      7.88,
      15.76,
      23.64,
      31.52,
      39.4
    ],
    "beta_unlevered": 0.8,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      35.0,
      39.0,
      43.0,
      47.0,
      51.0
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 78.8,
    "debt": 157.6,
    "investments": 11.82,
    "lease_liability": 0,
    "minority": 9.456,
    "valuation_cash_adjustment": 9.456,
    "shares": 113,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 11.3
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 265.556,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 307.32,
    "opening_cash": 78.8,
    "opening_operating_current_assets": 265.556,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 169.0,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge",
    "dual_asset_pool"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_asset_pool": "固定资产＋无形资产双资产池"
  },
  "c_structure": "risk_adjusted_pipeline",
  "c_structure_definition": "风险调整管线 DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge",
      "dual_asset_pool"
    ],
    "c": "risk_adjusted_pipeline"
  },
  "opening_nwc_last_fye": 291.062704,
  "opening_nwc_valuation_date": 265.556,
  "market": {
    "market_price": 22.1
  },
  "projects": {
    "project_atlas": {
      "commissioning_period": 2,
      "construction_capex": [
        94,
        0,
        0,
        0,
        0
      ],
      "project_revenue": [
        122.0,
        138.0,
        154.0,
        170.0,
        186.0
      ],
      "project_margin": 0.21,
      "project_da": [
        7,
        9,
        11,
        13,
        15
      ],
      "project_operating_capex": [
        8,
        8,
        8,
        8,
        8
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5,
        6
      ],
      "project_fcff": [
        -94,
        20.1697,
        23.7401,
        27.3105,
        30.8809
      ],
      "success_probability": 0.67
    },
    "project_boreal": {
      "commissioning_period": 3,
      "construction_capex": [
        0,
        123,
        0,
        0,
        0
      ],
      "project_revenue": [
        145.0,
        161.0,
        177.0,
        193.0,
        209.0
      ],
      "project_margin": 0.245,
      "project_da": [
        7,
        9,
        11,
        13,
        15
      ],
      "project_operating_capex": [
        11,
        11,
        11,
        11,
        11
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5,
        6
      ],
      "project_fcff": [
        0,
        -123,
        29.174225,
        33.173025,
        37.171825
      ],
      "success_probability": 0.53
    }
  }
}
```

</details>

##### BC10｜沛源新材估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司价值由已有业务和两个在建项目组成，项目需按投产时间和成功概率做风险调整后估值。
公司财年截至每年 5 月 31 日，最近完整财年末为 `2025-05-31`，估值日 `2025-08-30` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
固定资产与无形资产分别滚动：期初＋新增－折旧/摊销＝期末；无形资产新增扣 FCFF，摊销加回，不能与固定资产混池。
项目投产期之前收入必须为零；建设期支出独立计入对应期间。项目经营 FCFF 单列后乘成功概率，概率不得加到 WACC。已有业务价值与项目风险调整现值分开列示后相加。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC10 选用的 rubric（52 条，权重合计 136；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值活公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | output.xlsx与memo.md须存在 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需Results页并保留Inputs页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史需聚合完整财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 末期含非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作为经营成本处理 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 门店数含新增与流失滚动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 门店驱动收入构造 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率不同 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | NWC变动符号与后续期差额 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用最近财年末余额 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用nwc_days模块 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 输出含债务计划表 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | 存在NOL抵扣约束 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 双资产池独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 题面要求固定与无形资产分别滚动 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为本题核心 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数/365期末折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 要求库存股期权与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值为必然输出 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 双资产池无形资产处理 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 残期只计估值日后活动 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为唯一数值活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 有独立数值真值需重算比对 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第一组扰动检查 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第二组扰动检查 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 自由布局按键名发现 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 假设不得硬编码入公式 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 估值链不得有未声明循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo说明驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| C-PIPE-TIMING | 经营预测 | 未投产或未上市项目在投产日前不产生收入 | rule | 主需 | 题面要求投产前收入为零 |
| C-PIPE-CAPEX | 经营预测 | 建设期支出与投产期收入分别建模并计入对应期间 | rule | 主需 | 建设期支出独立计入对应期 |
| C-PIPE-PROB | 经营预测 | 成功概率作用于项目现金流或项目价值，不通过调整 WACC 体现 | rule | 主需 | 概率乘FCFF不加到WACC |
| C-PIPE-SUM | 经营预测 | 公司价值等于各项目风险调整价值之和加已有业务价值 | rule | 主需 | 已有业务与项目价值相加 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入值 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM须按规定推导 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 半年期、财年与LTM不得混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加5期预测序列须一致 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径前后一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 原始披露期不得改写 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史存在非经常收益需单列 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF各组成需独立列示 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值需引用可见单元格 |

### BC11（BC）

<details><summary>BC11｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC11",
  "seed": 402478,
  "candidate_index": 8,
  "family": "BC",
  "step": 1,
  "company": "栖云办公",
  "dimension_selection": {
    "scenario": "企业档案订阅",
    "difficulty": "L2: 依赖深度6，显式6期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "subscription",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "SBC经营成本",
    "output_mode": "segment_dcf",
    "output_template": "mixed",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets",
    "intangible_pool",
    "scenario"
  ],
  "selection_rationale": {
    "scenario": "企业档案订阅要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "mixed_h1_q",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "subscription",
    "unit": "千家客户",
    "price_unit": "百万元/千家客户/年",
    "description": "企业档案订阅"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-06-11",
  "last_fy_end": "2026-02-28",
  "horizon": 6,
  "history": [
    {
      "start": "2023-03-01",
      "end": "2023-08-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 306.8,
      "operating_cost_ex_sbc": 247,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-08-29",
      "end": "2024-02-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 491.8,
      "operating_cost_ex_sbc": 392,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2024-02-29",
      "end": "2024-08-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 326.8,
      "operating_cost_ex_sbc": 261,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-08-29",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 511.8,
      "operating_cost_ex_sbc": 406,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2025-03-01",
      "end": "2025-08-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 346.8,
      "operating_cost_ex_sbc": 275,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-08-29",
      "end": "2026-02-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 531.8,
      "operating_cost_ex_sbc": 420,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2026-03-01",
      "end": "2026-05-28",
      "fiscal_year": "2027",
      "period_type": "bridge_quarter",
      "revenue": 281.0,
      "operating_cost_ex_sbc": 215.2,
      "sbc": 5.7,
      "nonrecurring_gain": 1.1
    }
  ],
  "opening_nwc": 334.304,
  "opening_deferred": 0,
  "opening_ppe": 307.52,
  "opening_rou": 0,
  "opening_debt": 198.4,
  "opening_retained_earnings": 158.72,
  "contributed_capital": 386.88,
  "opening_cash": 99.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 112,
    "price0": 8.8571429,
    "driver_add": [
      8.96,
      10.192,
      11.424,
      12.656,
      13.888,
      15.12
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054,
      0.045
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065,
      0.07
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022,
      0.02
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188,
      0.195
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065,
      0.069
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186,
      0.192
    ],
    "tax": 0.235,
    "wacc": 0.103,
    "g": 0.024,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51,
      52
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58,
      57
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47,
      48
    ],
    "nol0": 109.12,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      24.8,
      0,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      9.92,
      19.84,
      29.759999999999998,
      39.68,
      49.6,
      59.519999999999996
    ],
    "beta_unlevered": 0.76,
    "target_de": 0.33,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      36.7,
      40.7,
      44.7,
      48.7,
      52.7,
      56.7
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 99.2,
    "debt": 198.4,
    "investments": 14.88,
    "lease_liability": 0,
    "minority": 11.904,
    "valuation_cash_adjustment": 11.904,
    "shares": 134,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 13.4
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 334.304,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 386.88,
    "opening_cash": 99.2,
    "opening_operating_current_assets": 334.304,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 176.3,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "mixed_ltm",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge",
    "dual_asset_pool"
  ],
  "b_item_definitions": {
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_asset_pool": "固定资产＋无形资产双资产池"
  },
  "c_structure": "scenario_operating_model",
  "c_structure_definition": "情景驱动 Operating Model",
  "structure": {
    "b": [
      "mixed_ltm",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "dual_asset_pool"
    ],
    "c": "scenario_operating_model"
  },
  "market": {
    "market_price": 23.01
  }
}
```

</details>

##### BC11｜栖云办公估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

管理层给出 Base、Bull、Bear 三套经营方案，需要搭建可一键切换情景的经营模型并完成 DCF。
最近完整财年末为 `2026-02-28`，估值日为 `2026-06-11`。预测共 6 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
固定资产与无形资产分别滚动：期初＋新增－折旧/摊销＝期末；无形资产新增扣 FCFF，摊销加回，不能与固定资产混池。
设置 `Cases` 页，唯一选择格链接 `a.scenario`（1=Base、2=Bull、3=Bear）。需求、利润率、再投资、FCFF、终值与每股价值必须随同一开关联动；另分别保留三情景独立输出，不能只交一张敏感性表。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC11 选用的 rubric（47 条，权重合计 123；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值活公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定百万元/百万股/小数 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | output.xlsx与memo.md须存在 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 须有Inputs/Cases/Results页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 题面要求完整财年聚合 |
| B-MIXLTM | 历史与会计口径 | 混合历史 LTM 由最近完整半年加其后桥接季度构成，不重复计入、不遗漏、不年化 | rule | 主需 | 半年加桥接季度拼LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 非经常项需规范化剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC为经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 订阅客户期初减流失加新增 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT用当期利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期ΔNWC期初期末与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期ΔNWC须用估值日余额 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 题面要求无形资产独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 题面要求固定资产与无形资产分别滚动 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径必然涉及 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 题面要求实际天数年中折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | spec为双终值机制 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 库存股期权与RSU稀释 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 需输出每股价值 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 无形资产池明确要求 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 残期只计估值日后活动 |
| C-CASE-SWITCH | DCF与估值桥 | 单一情景开关切换后收入、利润率、再投资、FCFF、终值和每股价值同时改变 | rule | 主需 | 题面要求单一开关全链联动 |
| C-CASE-ISOLATE | DCF与估值桥 | 每个情景的输出值与独立真值一致，情景之间不相互覆盖 | rule | 次需 | 要求三情景独立输出 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为唯一数值活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第一组 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第二组 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由按键发现 |
| X-FM-003 | 公式与模型工程 | 同一业务或估值假设仅有一个权威输入单元格，每个使用该假设的下游公式均可追溯至该单元格。 | rule | 主需 | 情景唯一选择格全链联动 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo说明驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型，期间标签可判定 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入须与输入包一致 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | LTM指定半年加桥接季窗口 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 半年与季度期间不得混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加6期预测序列 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | SBC规范化口径一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 原始披露期不得改写 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | 双终值须共用显性期现值 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 非经常收益需单独规范化 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数年中折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF各构成项需可识别 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 双终值须引用可见单元格 |

### BC12（BC）

<details><summary>BC12｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC12",
  "seed": 403455,
  "candidate_index": 15,
  "family": "BC",
  "step": 1,
  "company": "朔方芯材",
  "dimension_selection": {
    "scenario": "商用设备巡检",
    "difficulty": "L2: 依赖深度8，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "installed_base",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "dcf_only",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days",
    "intangible_pool"
  ],
  "selection_rationale": {
    "scenario": "商用设备巡检要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "mixed_h1_q",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": true
  },
  "business": {
    "driver": "installed_base",
    "unit": "千台",
    "price_unit": "百万元/台次",
    "description": "商用设备巡检"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-02-14",
  "last_fy_end": "2024-10-31",
  "horizon": 4,
  "history": [
    {
      "start": "2021-11-01",
      "end": "2022-04-30",
      "fiscal_year": "2022",
      "period_type": "half_year",
      "revenue": 321.5,
      "operating_cost_ex_sbc": 247,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-05-01",
      "end": "2022-10-31",
      "fiscal_year": "2022",
      "period_type": "half_year",
      "revenue": 506.5,
      "operating_cost_ex_sbc": 392,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2022-11-01",
      "end": "2023-04-30",
      "fiscal_year": "2023",
      "period_type": "half_year",
      "revenue": 341.5,
      "operating_cost_ex_sbc": 261,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-05-01",
      "end": "2023-10-31",
      "fiscal_year": "2023",
      "period_type": "half_year",
      "revenue": 526.5,
      "operating_cost_ex_sbc": 406,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2023-11-01",
      "end": "2024-04-30",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 361.5,
      "operating_cost_ex_sbc": 275,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-05-01",
      "end": "2024-10-31",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 546.5,
      "operating_cost_ex_sbc": 420,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2024-11-01",
      "end": "2025-01-31",
      "fiscal_year": "2025",
      "period_type": "bridge_quarter",
      "revenue": 292.9,
      "operating_cost_ex_sbc": 215.2,
      "sbc": 5.7,
      "nonrecurring_gain": 1.1
    }
  ],
  "opening_nwc": 390.586,
  "opening_deferred": 0,
  "opening_ppe": 376.03,
  "opening_rou": 0,
  "opening_debt": 242.6,
  "opening_retained_earnings": 194.08,
  "contributed_capital": 473.07,
  "opening_cash": 121.3,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 147,
    "price0": 2.5786565,
    "driver_add": [
      11.76,
      13.377,
      14.994,
      16.611
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.10940000000000001,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 7.8,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 133.43,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      30.325000000000003,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.13,
      24.26,
      36.39,
      48.52
    ],
    "beta_unlevered": 0.88,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "service_frequency": [
      3.2,
      3.2800000000000002,
      3.3600000000000003,
      3.4400000000000004
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      38.4,
      42.4,
      46.4,
      50.4
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 121.3,
    "debt": 242.6,
    "investments": 18.195,
    "lease_liability": 0,
    "minority": 14.556,
    "valuation_cash_adjustment": 14.556,
    "shares": 155,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 15.5
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 481.561,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 473.07,
    "opening_cash": 121.3,
    "opening_operating_current_assets": 481.561,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 183.6,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "mixed_ltm",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge",
    "dual_asset_pool"
  ],
  "b_item_definitions": {
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_asset_pool": "固定资产＋无形资产双资产池"
  },
  "c_structure": "multi_method",
  "c_structure_definition": "多方法估值与反推",
  "structure": {
    "b": [
      "mixed_ltm",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "dual_asset_pool"
    ],
    "c": "multi_method"
  },
  "market": {
    "market_price": 23.92
  }
}
```

</details>

##### BC12｜朔方芯材估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题不只要一个目标价：需用 Gordon 与退出倍数两种方法分别估值，做反向推导，并给出估值区间。
最近完整财年末为 `2024-10-31`，估值日为 `2025-02-14`。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
固定资产与无形资产分别滚动：期初＋新增－折旧/摊销＝期末；无形资产新增扣 FCFF，摊销加回，不能与固定资产混池。
分别给出 Gordon 与退出倍数的终值、EV、股权价值和每股价值，不得加权成一个数。由 Gordon 终值反推隐含 EV/EBITDA，由退出倍数反推隐含 g，并用给定股价在工作簿内以公式迭代/求解隐含 WACC；Football Field 按给定折现率和增长区间。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC12 选用的 rubric（54 条，权重合计 138；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面指定百万元/百万股/小数 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需output.xlsx与memo.md |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需Results前缀页与Inputs页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史需聚合成完整财年 |
| B-MIXLTM | 历史与会计口径 | 混合历史 LTM 由最近完整半年加其后桥接季度构成，不重复计入、不遗漏、不年化 | rule | 主需 | 题面要求半年加桥接季度构成LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC为经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 装机量含流失与新增滚动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均基数乘单价及残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率不同 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期ΔNWC符号与差额 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用估值日余额 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用NWC天数模块 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | spec约束NOL抵扣上限 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 题面要求无形资产独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 题面要求固定资产与无形资产分别滚动 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面规定FCFF口径 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数期末折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 库存股期权与RSU稀释 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 需分别给出每股价值 |
| 05-SENS | DCF与估值桥 | 敏感性单元格使用各自行列假设而经营预测不变 | rule | 次需 | Football Field按折现率增长区间 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 无形资产新增扣减摊销加回 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅含估值日后活动 |
| C-MULTI-SPLIT | DCF与估值桥 | Gordon 与退出倍数估值分别给出，不只输出加权结果 | rule | 主需 | 题面要求两种终值分别给出 |
| C-IMPLIED-MULT | DCF与估值桥 | 由 Gordon 终值反推的隐含 EV/EBITDA 计算正确 | rule | 主需 | 要求Gordon反推隐含EV/EBITDA |
| C-IMPLIED-G | DCF与估值桥 | 由退出倍数终值反推的隐含永续增长率计算正确 | rule | 主需 | 要求退出倍数反推隐含g |
| C-REVERSE | DCF与估值桥 | 由给定市场价格反推的隐含 WACC 或隐含增长假设正确，且以公式或求解过程得出 | rule | 主需 | 要求用股价公式求解隐含WACC |
| C-RANGE | DCF与估值桥 | 估值区间的上下界分别来自题面指定的方法和假设范围 | rule | 次需 | Football Field按给定区间 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第一组 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第二组 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由按键发现 |
| X-IF-003 | 公式与模型工程 | 敏感性网格的每个结果值均与模型在相同行列输入下的重算值一致，容差按题面规定。 | rule | 主需 | Football Field区间须与模型一致 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入须与输入包一致 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | LTM指定半年加桥接季度 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 半年/季度混合须正确聚合 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加4期预测序列 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径须一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 原始披露期不得改写 |
| X-IC-001 | 公式与模型工程 | 敏感性表中与基准行列假设相交的单元格，其值与模型相同口径基准输出的相对差异不超过题面容差；题面未给容差时为 0.1%。 | rule | 主需 | Football Field含基准组合 |
| X-IC-002 | 公式与模型工程 | 每条敏感性轴的完整值序列与题面指定的起点、终点及步长完全一致。 | rule | 主需 | 题面给定折现率与增长区间 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | Gordon与退出倍数双终值 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 非经常收益需单独规范化调整 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数折现期须可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF各组成项须分行 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 双终值须引用可见单元格 |

### BC13（BC）

<details><summary>BC13｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC13",
  "seed": 404432,
  "candidate_index": 22,
  "family": "BC",
  "step": 1,
  "company": "白榆医械",
  "dimension_selection": {
    "scenario": "区域低温加工",
    "difficulty": "L3: 依赖深度8，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "capacity",
    "valuation_mechanism": "exit",
    "accounting_basis": "SBC经营成本",
    "output_mode": "three_statements_dcf",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "debt_schedule",
    "capm",
    "nol",
    "three_statements",
    "nwc_days",
    "nol",
    "three_statements"
  ],
  "selection_rationale": {
    "scenario": "区域低温加工要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "capacity",
    "unit": "千吨年产能",
    "price_unit": "百万元/千吨",
    "description": "区域低温加工"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-03-09",
  "last_fy_end": "2025-08-31",
  "horizon": 5,
  "history": [
    {
      "start": "2022-09-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 524.136087,
      "ebit": 53.791461,
      "operating_cost_ex_sbc": 422.899592,
      "sbc": 12.570016,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-03-01",
      "end": "2023-08-31",
      "fiscal_year": "2023",
      "revenue": 538.198275,
      "ebit": 57.864868,
      "operating_cost_ex_sbc": 432.127407,
      "sbc": 12.90726,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-09-01",
      "end": "2024-02-29",
      "fiscal_year": "2024",
      "revenue": 552.260462,
      "ebit": 62.075721,
      "operating_cost_ex_sbc": 441.244529,
      "sbc": 13.244504,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-03-01",
      "end": "2024-08-31",
      "fiscal_year": "2024",
      "revenue": 566.32265,
      "ebit": 66.424021,
      "operating_cost_ex_sbc": 450.250957,
      "sbc": 13.581749,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-09-01",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "revenue": 580.384838,
      "ebit": 70.909766,
      "operating_cost_ex_sbc": 459.146691,
      "sbc": 13.918993,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-03-01",
      "end": "2025-08-31",
      "fiscal_year": "2025",
      "revenue": 594.447025,
      "ebit": 75.532958,
      "operating_cost_ex_sbc": 467.931732,
      "sbc": 14.256237,
      "nonrecurring_gain": 6.924216
    }
  ],
  "opening_nwc": 446.318604,
  "opening_deferred": 0.0,
  "opening_ppe": 376.03,
  "opening_rou": 0.0,
  "opening_debt": 242.6,
  "opening_retained_earnings": 194.08,
  "contributed_capital": 473.07,
  "opening_cash": 121.3,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 182,
    "price0": 9.006534,
    "driver_add": [
      14.56,
      16.562,
      18.564,
      20.566,
      22.568
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.107,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 8.4,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 133.43,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      21.834,
      21.834,
      21.834,
      21.834,
      21.834
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      30.325000000000003,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.13,
      24.26,
      36.39,
      48.52,
      60.650000000000006
    ],
    "beta_unlevered": 0.84,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "utilization": [
      0.74,
      0.758,
      0.776,
      0.794,
      0.8119999999999999
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      40.1,
      44.1,
      48.1,
      52.1,
      56.1
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 121.3,
    "debt": 242.6,
    "investments": 18.195,
    "lease_liability": 0.0,
    "minority": 14.556,
    "valuation_cash_adjustment": 14.556,
    "shares": 176,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 17.6
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 408.781,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 473.07,
    "opening_cash": 121.3,
    "opening_operating_current_assets": 408.781,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 190.9,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge",
    "cash_tax_nol"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "cash_tax_nol": "现金税与 NOL"
  },
  "c_structure": "three_statements_dcf",
  "c_structure_definition": "三表＋DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge",
      "cash_tax_nol"
    ],
    "c": "three_statements_dcf"
  },
  "opening_nwc_last_fye": 446.318604,
  "opening_nwc_valuation_date": 408.781,
  "market": {
    "market_price": 24.83
  }
}
```

</details>

##### BC13｜白榆医械估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题需先搭建利润表、资产负债表和现金流量表三张预测报表，再在其上完成 DCF。
公司财年截至每年 8 月 31 日，最近完整财年末为 `2025-08-31`，估值日 `2026-03-09` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
公司期初有可结转的税务亏损（nol0）：现金税须先用亏损抵减应税利润，并逐期滚动亏损余额，不能直接按 EBIT×税率计税。
三表须勾稽：现金与现金流量表一致、留存收益由净利润滚动、资产等于负债加权益，不得使用不透明平衡项。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC13 选用的 rubric（45 条，权重合计 119；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值公式 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需output.xlsx与memo.md |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史需聚合完整财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 存在非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC为经营成本不得加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 产能流失与新增滚动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均产能×价格×残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | NWC变动符号与期间 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用最近财年末余额 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 启用债务计划表 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | 题面要求NOL抵扣 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 新增无形资产独立滚动 |
| 04-BALANCE | 三表勾稽 | 每个预测期资产等于负债加权益 | rule | 主需 | 题面要求资产等于负债加权益 |
| 04-CASH | 三表勾稽 | 资产负债表现金与现金流量表期末现金一致 | rule | 主需 | 题面要求现金与现金流量表一致 |
| 04-RE | 三表勾稽 | 留存收益由净利润滚动且无不透明平衡项 | rule | 主需 | 题面要求留存收益滚动无平衡项 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用rolling_assets模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面规定FCFF口径 |
| 05-WACC | DCF与估值桥 | WACC 使用 CAPM 再杠杆和税后债务成本 | rule | 主需 | 启用CAPM模块 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数年中折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 期权与RSU须进入稀释股数 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值必然涉及 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题面含新增无形资产 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 残期只计估值日后 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | BC题有独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 自由布局按语义键发现 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求memo说明驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入须与输入包一致 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM推导 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加5期预测序列 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 原始披露期不得改写 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 存在非经常收益需规范化 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数年中折现期 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF各组成项需可识别 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 退出倍数终值引用 |

### BC14（BC）

<details><summary>BC14｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC14",
  "seed": 405409,
  "candidate_index": 5,
  "family": "BC",
  "step": 1,
  "company": "鹿原装备",
  "dimension_selection": {
    "scenario": "远程运维席位",
    "difficulty": "L1: 依赖深度6，显式6期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "subscription",
    "valuation_mechanism": "gordon",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "debt_schedule_dcf",
    "output_template": "mixed",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "dilution",
    "rolling_assets",
    "debt_schedule"
  ],
  "selection_rationale": {
    "scenario": "远程运维席位要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "mixed_h1_q",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "subscription",
    "unit": "千席位",
    "price_unit": "百万元/千席位/年",
    "description": "远程运维席位"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-09-14",
  "last_fy_end": "2026-05-31",
  "horizon": 6,
  "history": [
    {
      "start": "2023-06-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 300.5,
      "operating_cost_ex_sbc": 247,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-12-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 485.5,
      "operating_cost_ex_sbc": 392,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2024-06-01",
      "end": "2024-11-30",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 320.5,
      "operating_cost_ex_sbc": 261,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-12-01",
      "end": "2025-05-31",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 505.5,
      "operating_cost_ex_sbc": 406,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2025-06-01",
      "end": "2025-11-30",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 340.5,
      "operating_cost_ex_sbc": 275,
      "sbc": 9.5,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-12-01",
      "end": "2026-05-31",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 525.5,
      "operating_cost_ex_sbc": 420,
      "sbc": 10.5,
      "nonrecurring_gain": 2.2
    },
    {
      "start": "2026-06-01",
      "end": "2026-08-31",
      "fiscal_year": "2027",
      "period_type": "bridge_quarter",
      "revenue": 275.9,
      "operating_cost_ex_sbc": 215.2,
      "sbc": 5.7,
      "nonrecurring_gain": 1.1
    }
  ],
  "opening_nwc": 408.781,
  "opening_deferred": 0.0,
  "opening_ppe": 376.03,
  "opening_rou": 0.0,
  "opening_debt": 242.6,
  "opening_retained_earnings": 194.08,
  "contributed_capital": 473.07,
  "opening_cash": 121.3,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 97,
    "price0": 12.5051546,
    "driver_add": [
      7.76,
      8.827,
      9.894,
      10.961,
      12.028,
      13.095
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054,
      0.045
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065,
      0.07
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022,
      0.02
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188,
      0.195
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065,
      0.069
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186,
      0.192
    ],
    "tax": 0.235,
    "wacc": 0.105,
    "g": 0.024,
    "gordon_weight": 1.0,
    "exit_multiple": 7.8,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51,
      52
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58,
      57
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47,
      48
    ],
    "nol0": 133.43,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      21.834,
      21.834,
      21.834,
      21.834,
      21.834,
      21.834
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      30.325000000000003,
      0,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.13,
      24.26,
      36.39,
      48.52,
      60.650000000000006,
      72.78
    ],
    "beta_unlevered": 0.8,
    "target_de": 0.33,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      41.8,
      45.8,
      49.8,
      53.8,
      57.8,
      61.8
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 121.3,
    "debt": 242.6,
    "investments": 18.195,
    "lease_liability": 0.0,
    "minority": 14.556,
    "valuation_cash_adjustment": 14.556,
    "shares": 125,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 12.5
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 408.781,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 473.07,
    "opening_cash": 121.3,
    "opening_operating_current_assets": 408.781,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 198.2,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "mixed_ltm",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge",
    "debt_schedule"
  ],
  "b_item_definitions": {
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "debt_schedule": "债务计划表"
  },
  "c_structure": "debt_schedule_dcf",
  "c_structure_definition": "债务计划表＋DCF",
  "structure": {
    "b": [
      "mixed_ltm",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "debt_schedule"
    ],
    "c": "debt_schedule_dcf"
  },
  "market": {
    "market_price": 25.74
  }
}
```

</details>

##### BC14｜鹿原装备估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司在预测期内有新增借款和还款安排，需要在 DCF 之外建立完整的债务计划表。
最近完整财年末为 `2026-05-31`，估值日为 `2026-09-14`。预测共 6 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
借款、偿还、利息与期末债务逐期滚动连续，融资现金流与 FCFF 分离。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC14 选用的 rubric（45 条，权重合计 117；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交output.xlsx工作簿 |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 公开输出键须唯一数值 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面明确金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需xlsx与memo.md两文件 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 要求Results页与保留Inputs页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年数据聚合为完整财年 |
| B-MIXLTM | 历史与会计口径 | 混合历史 LTM 由最近完整半年加其后桥接季度构成，不重复计入、不遗漏、不年化 | rule | 主需 | 题面要求半年加桥接季度LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 历史含非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作经营成本，不在FCFF中加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 订阅席位存量含流失与新增 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 收入按平均席位与残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率向量 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期NWC差额与符号 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用营运资本天数模块 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 题面要求债务计划表滚动 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用估值日余额 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 题面含新增无形资产 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用资产滚动模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为核心 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数期末折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 期权库存股法与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值必然涉及 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题面提及新增无形资产 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅估值日后经营 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第一组 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第二组 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 自由布局语义键发现 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 扰动需假设不硬编码 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | 多期预测折现列对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 债务利息易产生循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo.md |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入值 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | LTM指定半年加桥接季度窗口 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加6期预测序列须一致 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史含非经常收益需规范化 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF需与融资分离构建 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值引用可见单元格 |

### BC15（BC）

<details><summary>BC15｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC15",
  "seed": 406386,
  "candidate_index": 12,
  "family": "BC",
  "step": 1,
  "company": "韶光文旅",
  "dimension_selection": {
    "scenario": "精密连接组件",
    "difficulty": "L2: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "volume_price",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "SBC经营成本",
    "output_mode": "segment_dcf",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "deferred_revenue",
    "debt_schedule",
    "capm",
    "nwc_days",
    "rolling_assets",
    "dual_terminal"
  ],
  "selection_rationale": {
    "scenario": "精密连接组件要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "volume_price",
    "unit": "百万件",
    "price_unit": "百万元/百万件",
    "description": "精密连接组件"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2024-07-27",
  "last_fy_end": "2024-02-28",
  "horizon": 4,
  "history": [
    {
      "start": "2021-09-01",
      "end": "2021-11-30",
      "fiscal_year": "2022",
      "revenue": 251.668865,
      "ebit": 25.79993,
      "operating_cost_ex_sbc": 202.559491,
      "sbc": 6.020758,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2021-12-01",
      "end": "2022-02-28",
      "fiscal_year": "2022",
      "revenue": 258.420956,
      "ebit": 27.753652,
      "operating_cost_ex_sbc": 206.979409,
      "sbc": 6.18229,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-03-01",
      "end": "2022-05-31",
      "fiscal_year": "2023",
      "revenue": 265.173048,
      "ebit": 29.773299,
      "operating_cost_ex_sbc": 211.346308,
      "sbc": 6.343823,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-06-01",
      "end": "2022-08-31",
      "fiscal_year": "2023",
      "revenue": 271.92514,
      "ebit": 31.858868,
      "operating_cost_ex_sbc": 215.660186,
      "sbc": 6.505355,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-09-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 278.677231,
      "ebit": 34.01036,
      "operating_cost_ex_sbc": 219.921045,
      "sbc": 6.666888,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-12-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 285.429323,
      "ebit": 36.227776,
      "operating_cost_ex_sbc": 224.128884,
      "sbc": 6.82842,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-03-01",
      "end": "2023-05-28",
      "fiscal_year": "2024",
      "revenue": 292.181414,
      "ebit": 38.511114,
      "operating_cost_ex_sbc": 228.283703,
      "sbc": 6.989953,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-05-29",
      "end": "2023-08-28",
      "fiscal_year": "2024",
      "revenue": 298.933506,
      "ebit": 40.860376,
      "operating_cost_ex_sbc": 232.385503,
      "sbc": 7.151485,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-08-29",
      "end": "2023-11-28",
      "fiscal_year": "2024",
      "revenue": 305.685597,
      "ebit": 43.275561,
      "operating_cost_ex_sbc": 236.434283,
      "sbc": 7.313018,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-11-29",
      "end": "2024-02-28",
      "fiscal_year": "2024",
      "revenue": 312.437688,
      "ebit": 45.75667,
      "operating_cost_ex_sbc": 240.430043,
      "sbc": 7.47455,
      "nonrecurring_gain": 3.630369
    }
  ],
  "opening_nwc": 391.594,
  "opening_deferred": 87.15,
  "opening_ppe": 360.22,
  "opening_rou": 0.0,
  "opening_debt": 232.4,
  "opening_retained_earnings": 185.92,
  "contributed_capital": 453.18,
  "opening_cash": 116.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 132,
    "price0": 8.8030303,
    "driver_add": [
      10.56,
      12.012,
      13.464,
      14.916
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.103,
    "g": 0.022,
    "gordon_weight": 0.6,
    "exit_multiple": 8.4,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 127.82000000000001,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      20.915999999999997,
      20.915999999999997,
      20.915999999999997,
      20.915999999999997
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      29.05,
      0,
      0,
      0
    ],
    "debt_repayment": [
      11.620000000000001,
      23.240000000000002,
      34.86,
      46.480000000000004
    ],
    "beta_unlevered": 0.76,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      43.5,
      47.5,
      51.5,
      55.5
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 116.2,
    "debt": 232.4,
    "investments": 17.43,
    "lease_liability": 0.0,
    "minority": 13.944,
    "valuation_cash_adjustment": 13.944,
    "shares": 146,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 14.6
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 478.744,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 453.18,
    "opening_cash": 116.2,
    "opening_operating_current_assets": 478.744,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 205.5,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge",
    "dual_terminal"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_terminal": "Gordon、退出倍数、双终值加权"
  },
  "c_structure": "simple_dcf",
  "c_structure_definition": "简版 DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "dual_terminal"
    ],
    "c": "simple_dcf"
  },
  "market": {
    "market_price": 26.65
  }
}
```

</details>

##### BC15｜韶光文旅估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题交付单一主体的 DCF：从经营预测推出 FCFF，折现后经股权桥得到每股价值。
公司财年截至每年 2 月 28 日，最近完整财年末为 `2024-02-28`，估值日 `2024-07-27` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
终值同时用 Gordon 永续增长法和退出倍数法计算，再按 Gordon 60%、退出倍数 40% 的权重加权，两种终值都要单独列示。
建立 EBIT、无杠杆现金税、折旧摊销、资本开支与 ΔNWC 到 FCFF 的完整桥，再折现并完成股权桥。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC15 选用的 rubric（48 条，权重合计 124；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须交付可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定百万元/小数单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需output.xlsx与memo.md |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 季度历史需聚合完整财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 存在非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作经营成本 |
| 02-COLLECT | 历史与会计口径 | 现金收款等于确认收入加合同负债增加 | rule | 次需 | 启用合同负债收款口径 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 存量驱动含流失与新增 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 收入按平均基数及残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率向量 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC期末与符号正确 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用营运资本天数法 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 启用债务计划表 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用估值日余额 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用资产滚动模块，需PPE滚动 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面要求完整FCFF桥 |
| 05-WACC | DCF与估值桥 | WACC 使用 CAPM 再杠杆和税后债务成本 | rule | 主需 | 启用CAPM模块 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数年中折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | 要求双终值加权 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 桥含库存股期权与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 股权桥终点每股价值 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 残期只计估值日后活动 |
| C-MULTI-SPLIT | DCF与估值桥 | Gordon 与退出倍数估值分别给出，不只输出加权结果 | rule | 主需 | 题面要求Gordon与退出倍数双终值 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 重算对比独立真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第一组 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏扰动第二组 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页自由布局按键发现 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 债务利息与现金滚动易成循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需清晰期间标签 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入值须与输入包一致 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM推导 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 季度/财年/LTM不可混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加4个完整财年 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 须保留Inputs历史事实 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | 双终值共用显性期现值 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 非经常收益需单独剔除 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数年中折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 题面要求完整FCFF桥 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon与退出倍数双终值 |

### BC16（BC）

<details><summary>BC16｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "BC16",
  "seed": 407363,
  "candidate_index": 19,
  "family": "BC",
  "step": 1,
  "company": "连岳智造",
  "dimension_selection": {
    "scenario": "楼宇监测装机服务",
    "difficulty": "L3: 依赖深度7，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "installed_base",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "dcf_only",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days",
    "intangible_pool",
    "scenario"
  ],
  "selection_rationale": {
    "scenario": "楼宇监测装机服务要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "installed_base",
    "unit": "千台",
    "price_unit": "百万元/台次",
    "description": "楼宇监测装机服务"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-03-13",
  "last_fy_end": "2025-10-31",
  "horizon": 5,
  "history": [
    {
      "start": "2022-11-01",
      "end": "2023-04-30",
      "fiscal_year": "2023",
      "revenue": 393.364086,
      "ebit": 40.303642,
      "operating_cost_ex_sbc": 316.215936,
      "sbc": 9.399014,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-05-01",
      "end": "2023-10-31",
      "fiscal_year": "2023",
      "revenue": 403.917757,
      "ebit": 43.355672,
      "operating_cost_ex_sbc": 323.115877,
      "sbc": 9.651183,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-11-01",
      "end": "2024-04-30",
      "fiscal_year": "2024",
      "revenue": 414.471427,
      "ebit": 46.510684,
      "operating_cost_ex_sbc": 329.933048,
      "sbc": 9.903352,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-05-01",
      "end": "2024-10-31",
      "fiscal_year": "2024",
      "revenue": 425.025098,
      "ebit": 49.768679,
      "operating_cost_ex_sbc": 336.667451,
      "sbc": 10.15552,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2024-11-01",
      "end": "2025-04-30",
      "fiscal_year": "2025",
      "revenue": 435.578768,
      "ebit": 53.129656,
      "operating_cost_ex_sbc": 343.319084,
      "sbc": 10.407689,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2025-05-01",
      "end": "2025-10-31",
      "fiscal_year": "2025",
      "revenue": 446.132439,
      "ebit": 56.593616,
      "operating_cost_ex_sbc": 349.887948,
      "sbc": 10.659858,
      "nonrecurring_gain": 5.177464
    }
  ],
  "opening_nwc": 334.534356,
  "opening_deferred": 0,
  "opening_ppe": 281.17,
  "opening_rou": 0,
  "opening_debt": 181.4,
  "opening_retained_earnings": 145.12,
  "contributed_capital": 353.73,
  "opening_cash": 90.7,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 167,
    "price0": 1.6972305,
    "driver_add": [
      13.36,
      15.197,
      17.034,
      18.871,
      20.708
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.109,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 9.0,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 99.77,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      22.675,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      9.07,
      18.14,
      27.21,
      36.28,
      45.35
    ],
    "beta_unlevered": 0.88,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "service_frequency": [
      3.2,
      3.2800000000000002,
      3.3600000000000003,
      3.4400000000000004,
      3.52
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      45.2,
      49.2,
      53.2,
      57.2,
      61.2
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 90.7,
    "debt": 181.4,
    "investments": 13.605,
    "lease_liability": 0,
    "minority": 10.884,
    "valuation_cash_adjustment": 10.884,
    "shares": 167,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 16.7
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 305.659,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 353.73,
    "opening_cash": 90.7,
    "opening_operating_current_assets": 305.659,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 212.8,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge",
    "dual_asset_pool"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_asset_pool": "固定资产＋无形资产双资产池"
  },
  "c_structure": "scenario_operating_model",
  "c_structure_definition": "情景驱动 Operating Model",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge",
      "dual_asset_pool"
    ],
    "c": "scenario_operating_model"
  },
  "opening_nwc_last_fye": 334.534356,
  "opening_nwc_valuation_date": 305.659,
  "market": {
    "market_price": 27.56
  }
}
```

</details>

##### BC16｜连岳智造估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

管理层给出 Base、Bull、Bear 三套经营方案，需要搭建可一键切换情景的经营模型并完成 DCF。
公司财年截至每年 10 月 31 日，最近完整财年末为 `2025-10-31`，估值日 `2026-03-13` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
固定资产与无形资产分别滚动：期初＋新增－折旧/摊销＝期末；无形资产新增扣 FCFF，摊销加回，不能与固定资产混池。
设置 `Cases` 页，唯一选择格链接 `a.scenario`（1=Base、2=Bull、3=Bear）。需求、利润率、再投资、FCFF、终值与每股价值必须随同一开关联动；另分别保留三情景独立输出，不能只交一张敏感性表。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### BC16 选用的 rubric（49 条，权重合计 125；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | output.xlsx与memo.md指定 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 要求Inputs/Cases/Results页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史需聚合完整财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 存在非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 装机存量驱动滚动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均装机基数乘单价及残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | NWC变动符号与相邻期差 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用营运资本天数模块 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | 约束要求NOL孰低抵扣 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用最近财年末余额 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 题面要求无形资产独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 题面要求固定资产与无形资产分池滚动 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面明确FCFF口径 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数期末折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | 双终值机制按权重合成 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 股权桥含现金投资债务少数股权 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 期权库存股法与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值必需输出 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 无形资产新增扣减摊销加回 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅含估值日后活动 |
| C-CASE-SWITCH | DCF与估值桥 | 单一情景开关切换后收入、利润率、再投资、FCFF、终值和每股价值同时改变 | rule | 主需 | 题面要求单一开关全链联动 |
| C-CASE-ISOLATE | DCF与估值桥 | 每个情景的输出值与独立真值一致，情景之间不相互覆盖 | rule | 次需 | 要求三情景独立输出 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为唯一数值活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页自由布局按键发现 |
| X-FM-003 | 公式与模型工程 | 同一业务或估值假设仅有一个权威输入单元格，每个使用该假设的下游公式均可追溯至该单元格。 | rule | 主需 | 情景唯一选择格链接a.scenario |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo.md |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入值 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM须正确推导 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 半年期不得与财年/LTM混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加5个完整财年 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径须一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 原始披露期不得改写 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | 双终值须共用显性期现值 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 非经常收益需单独剔除记录 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF构成需逐项列示 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 双终值需引用可见单元格 |

### A01（A）

<details><summary>A01｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "A01",
  "family": "A",
  "company": "弦庭软科",
  "industry": "software_subscription",
  "industry_name": "软件与订阅 SaaS",
  "base_structure": "P-ARR中枢",
  "industry_drivers": [
    "ARR 净留存与新签",
    "平均 ARR 收入确认",
    "资本化研发"
  ],
  "valuation_date": "2025-09-27",
  "last_fy_end": "2025-06-30",
  "horizon": 5,
  "time_axis": {
    "midyear": false,
    "history_frequency": "annual",
    "day_count": "actual/365"
  },
  "accounting": {
    "sbc_expense": true,
    "industry_valuation": true
  },
  "residual_activity": 0.7561643835616438,
  "enabled_modules": [
    "industry_driver",
    "residual_period"
  ],
  "history": [],
  "bridge": {
    "cash": 139,
    "debt": 203,
    "investments": 25,
    "lease_liability": 13,
    "minority": 6,
    "valuation_cash_adjustment": 0,
    "shares": 75,
    "rsus": 1.2,
    "options": 0,
    "strike": 0,
    "share_price": 15
  },
  "assumptions": {
    "tax": 0.23,
    "wacc": 0.1,
    "g": 0.025,
    "driver0": 730,
    "ebit_margin": [
      0.16,
      0.164,
      0.168,
      0.17200000000000001,
      0.176
    ],
    "da_pct": [
      0.052,
      0.052,
      0.052,
      0.052,
      0.052
    ],
    "capex_pct": [
      0.065,
      0.065,
      0.065,
      0.065,
      0.065
    ],
    "nwc_pct": [
      0.13,
      0.13,
      0.13,
      0.13,
      0.13
    ],
    "opening_nwc": 63,
    "net_revenue_retention": [
      1.04,
      1.045,
      1.05,
      1.055,
      1.06
    ],
    "new_arr": [
      98,
      111,
      124,
      137,
      150
    ],
    "capitalized_rd_pct": [
      0.075,
      0.075,
      0.075,
      0.075,
      0.075
    ]
  }
}
```

</details>

##### A01｜弦庭软科估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司属于**软件与订阅 SaaS**。经营预测必须以ARR 净留存与新签、平均 ARR 收入确认、资本化研发为驱动搭建行业经营表，不得只用单一增长率外推。
最近完整财年末为 `2025-06-30`，估值日 `2025-09-27` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，经营量按残期天数比例计入，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个预测期末。
收入、利润率、再投资和营运资本须从行业驱动连接到 DCF；SBC 是经营成本且不在 FCFF 加回。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### A01 选用的 rubric（38 条，权重合计 92；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 3 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读取的output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键须唯一且为数值 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额、股数与比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需交付output.xlsx与memo.md |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需有Results页并保留Inputs页 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面明确SBC不加回FCFF |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | ARR按净留存与新签滚动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 收入按平均ARR确认 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT用当期利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC期初期末及符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用给定期初NWC 63 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为必然要求 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | actual/365且非年中 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值时点与折现 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 桥含现金投资债务租赁少数 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | RSU需计入稀释股数 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值计算 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示扰动检查 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需清晰标签 |
| A-SAAS-ARR | 经营预测 | 期末 ARR 等于期初 ARR 乘净留存率加新签 ARR，收入按期初期末 ARR 平均确认 | rule | 主需 | ARR滚动与平均确认收入 |
| A-SAAS-CAPRD | 经营预测 | 资本化研发作为无形资产新增扣减 FCFF，摊销加回 | rule | 次需 | 资本化研发为指定驱动 |
| A-REASON | 经营预测 | 说明中解释行业驱动与估值结果之间的因果链 | llm | 次需 | memo须说明价值驱动 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入值须与输入包一致 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 5年显性预测期须一致 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-003 | 表达与专业可用性 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | llm | 次需 | SBC与资本化研发处理须一致 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 残余期折现期须可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 驱动须连接至FCFF各项 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 给定g用Gordon终值 |
| A-DRIVER | 经营预测 | 收入由该行业规定的业务驱动构造，而不是单一增长率 | rule | 主需 | 程序强制必选项 |
| A-METRIC | 经营预测 | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | rule | 主需 | 程序强制必选项 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 程序强制必选项 |

### A02（A）

<details><summary>A02｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "A02",
  "family": "A",
  "company": "榉邻商业",
  "industry": "retail_chain",
  "industry_name": "消费零售与连锁",
  "base_structure": "P-自有基座",
  "industry_drivers": [
    "同店销售增长",
    "开关店与新店月份",
    "店均收入"
  ],
  "valuation_date": "2025-01-06",
  "last_fy_end": "2024-09-30",
  "horizon": 5,
  "time_axis": {
    "midyear": true,
    "history_frequency": "annual",
    "day_count": "actual/365"
  },
  "accounting": {
    "sbc_expense": true,
    "industry_valuation": true
  },
  "residual_activity": 0.7315068493150685,
  "enabled_modules": [
    "industry_driver",
    "residual_period"
  ],
  "history": [],
  "bridge": {
    "cash": 148,
    "debt": 216,
    "investments": 26,
    "lease_liability": 14,
    "minority": 7,
    "valuation_cash_adjustment": 0,
    "shares": 78,
    "rsus": 1.2,
    "options": 0,
    "strike": 0,
    "share_price": 15
  },
  "assumptions": {
    "tax": 0.23,
    "wacc": 0.101,
    "g": 0.025,
    "driver0": 428,
    "ebit_margin": [
      0.16,
      0.164,
      0.168,
      0.17200000000000001,
      0.176
    ],
    "da_pct": [
      0.052,
      0.052,
      0.052,
      0.052,
      0.052
    ],
    "capex_pct": [
      0.065,
      0.065,
      0.065,
      0.065,
      0.065
    ],
    "nwc_pct": [
      0.13,
      0.13,
      0.13,
      0.13,
      0.13
    ],
    "opening_nwc": 67,
    "opening_stores": 213,
    "store_closure_rate": 0.018,
    "new_stores": [
      17,
      19,
      21,
      23,
      25
    ],
    "sales_per_store": 5.7,
    "same_store_growth": [
      0.036,
      0.033999999999999996,
      0.032,
      0.03,
      0.027999999999999997
    ],
    "new_store_months": [
      5,
      6,
      7,
      6,
      5
    ]
  }
}
```

</details>

##### A02｜榉邻商业估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司属于**消费零售与连锁**。经营预测必须以同店销售增长、开关店与新店月份、店均收入为驱动搭建行业经营表，不得只用单一增长率外推。
最近完整财年末为 `2024-09-30`，估值日 `2025-01-06` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，经营量按残期天数比例计入，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个预测期末。
收入、利润率、再投资和营运资本须从行业驱动连接到 DCF；SBC 是经营成本且不在 FCFF 加回。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### A02 选用的 rubric（39 条，权重合计 97；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 3 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须提交可读取的output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | output.xlsx与memo.md须存在 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 须有Results页并保留Inputs页 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面要求SBC不加回FCFF |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 门店期初减关店加新开 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 门店数×店均收入×新店月份 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率逐年给定 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 期初营运资本67与变动符号 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径必然涉及 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 年中约定与实际天数 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值时点与折现 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 桥含租赁与少数股权 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 存在RSU需计入稀释 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值必然输出 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 启用残余期模块 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不得硬编码假设 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | Excel模型不应有循环引用 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo说明驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| A-RETAIL-SSS | 经营预测 | 收入拆为可比门店同店增长与新开店贡献，新店按开业月份折算 | rule | 主需 | 同店与新店月份拆分收入 |
| A-REASON | 经营预测 | 说明中解释行业驱动与估值结果之间的因果链 | llm | 次需 | memo需说明价值驱动 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入包数值须原样采用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 5年显性预测期须一致 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| X-TA-003 | 表达与专业可用性 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | llm | 次需 | SBC处理需与说明一致 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 年中及残余期折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF各组成项需独立呈现 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值需引用可见单元格 |
| A-DRIVER | 经营预测 | 收入由该行业规定的业务驱动构造，而不是单一增长率 | rule | 主需 | 程序强制必选项 |
| A-METRIC | 经营预测 | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | rule | 主需 | 程序强制必选项 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 程序强制必选项 |

### A03（A）

<details><summary>A03｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "A03",
  "family": "A",
  "company": "衡铸工业",
  "industry": "manufacturing",
  "industry_name": "制造与工业设备",
  "base_structure": "N-期中滚动",
  "industry_drivers": [
    "投产产能与利用率",
    "产品价格",
    "维护与扩产资本开支"
  ],
  "valuation_date": "2026-03-17",
  "last_fy_end": "2025-11-30",
  "horizon": 4,
  "time_axis": {
    "midyear": false,
    "history_frequency": "annual",
    "day_count": "actual/365"
  },
  "accounting": {
    "sbc_expense": true,
    "industry_valuation": true
  },
  "residual_activity": 0.7068493150684931,
  "enabled_modules": [
    "industry_driver",
    "residual_period"
  ],
  "history": [],
  "bridge": {
    "cash": 157,
    "debt": 229,
    "investments": 27,
    "lease_liability": 15,
    "minority": 8,
    "valuation_cash_adjustment": 0,
    "shares": 81,
    "rsus": 1.2,
    "options": 0,
    "strike": 0,
    "share_price": 15
  },
  "assumptions": {
    "tax": 0.23,
    "wacc": 0.10200000000000001,
    "g": 0.025,
    "driver0": 420,
    "ebit_margin": [
      0.16,
      0.164,
      0.168,
      0.17200000000000001
    ],
    "da_pct": [
      0.052,
      0.052,
      0.052,
      0.052
    ],
    "capex_pct": [
      0.065,
      0.065,
      0.065,
      0.065
    ],
    "nwc_pct": [
      0.13,
      0.13,
      0.13,
      0.13
    ],
    "opening_nwc": 71,
    "capacity_additions": [
      0,
      42,
      0,
      36,
      0
    ],
    "utilization": [
      0.72,
      0.74,
      0.76,
      0.78
    ],
    "unit_price": [
      2.35,
      2.40405,
      2.4581000000000004,
      2.51215
    ],
    "extra_capex_pct": [
      0.018,
      0.018,
      0.018,
      0.018
    ]
  }
}
```

</details>

##### A03｜衡铸工业估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司属于**制造与工业设备**。经营预测必须以投产产能与利用率、产品价格、维护与扩产资本开支为驱动搭建行业经营表，不得只用单一增长率外推。
最近完整财年末为 `2025-11-30`，估值日 `2026-03-17` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，经营量按残期天数比例计入，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个预测期末。
收入、利润率、再投资和营运资本须从行业驱动连接到 DCF；SBC 是经营成本且不在 FCFF 加回。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### A03 选用的 rubric（41 条，权重合计 101；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 1 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定单位口径 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需xlsx与memo.md两文件 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需Results页及保留Inputs页 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面明确SBC为经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 产能按期初加新增滚动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均产能×利用率×价格×活动比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT用本期利润率 |
| 03-CAPEX | 经营预测 | 资本开支同时包含强度部分与重排新增部分 | rule | 次需 | 维护加扩产资本开支 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC期初期末与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用给定期初NWC 71 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径且SBC不加回 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | actual/365，非年中折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值时点与折现 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 桥含现金投资债务租赁少数 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 存在RSU需计入稀释 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值计算 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 启用残余期模块 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 有独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示扰动检查 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示两组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 假设不得硬编码入公式 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | 期中滚动期间列须对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 估值链不得循环引用 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo含驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求模型可追溯 |
| A-DRIVER | 经营预测 | 收入由该行业规定的业务驱动构造，而不是单一增长率 | rule | 主需 | 题面要求产能利用率价格驱动收入 |
| A-MFG-UTIL | 经营预测 | 产量不超过有效产能乘利用率上限，扩产在投产后才增加产能 | rule | 主需 | 制造业产能投产与利用率约束 |
| A-REASON | 经营预测 | 说明中解释行业驱动与估值结果之间的因果链 | llm | 次需 | memo须说明主要价值驱动 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入包数值须原样采用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 4期加残余期须一致 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| X-TA-003 | 表达与专业可用性 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | llm | 次需 | SBC处理说明须与模型一致 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 期中滚动需可见折现期 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 驱动须连接FCFF各行项 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值须引用可见单元格 |
| A-METRIC | 经营预测 | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | rule | 主需 | 程序强制必选项 |

### A04（A）

<details><summary>A04｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "A04",
  "family": "A",
  "company": "澜序医药",
  "industry": "pharmaceutical",
  "industry_name": "医药与生物科技",
  "base_structure": "E-事件终值",
  "industry_drivers": [
    "核心产品量",
    "专利悬崖侵蚀",
    "研发后利润率"
  ],
  "valuation_date": "2024-07-25",
  "last_fy_end": "2024-03-31",
  "horizon": 5,
  "time_axis": {
    "midyear": true,
    "history_frequency": "annual",
    "day_count": "actual/365"
  },
  "accounting": {
    "sbc_expense": true,
    "industry_valuation": true
  },
  "residual_activity": 0.6821917808219178,
  "enabled_modules": [
    "industry_driver",
    "residual_period"
  ],
  "history": [],
  "bridge": {
    "cash": 166,
    "debt": 242,
    "investments": 28,
    "lease_liability": 16,
    "minority": 9,
    "valuation_cash_adjustment": 0,
    "shares": 84,
    "rsus": 1.2,
    "options": 0,
    "strike": 0,
    "share_price": 15
  },
  "assumptions": {
    "tax": 0.23,
    "wacc": 0.10300000000000001,
    "g": 0.025,
    "driver0": 165,
    "ebit_margin": [
      0.16,
      0.164,
      0.168,
      0.17200000000000001,
      0.176
    ],
    "da_pct": [
      0.052,
      0.052,
      0.052,
      0.052,
      0.052
    ],
    "capex_pct": [
      0.065,
      0.065,
      0.065,
      0.065,
      0.065
    ],
    "nwc_pct": [
      0.13,
      0.13,
      0.13,
      0.13,
      0.13
    ],
    "opening_nwc": 75,
    "pre_cliff_growth": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cliff_period": 3,
    "erosion_rate": [
      0.28,
      0.28,
      0.28,
      0.28,
      0.28
    ],
    "unit_price": 4.9
  }
}
```

</details>

##### A04｜澜序医药估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司属于**医药与生物科技**。经营预测必须以核心产品量、专利悬崖侵蚀、研发后利润率为驱动搭建行业经营表，不得只用单一增长率外推。
最近完整财年末为 `2024-03-31`，估值日 `2024-07-25` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，经营量按残期天数比例计入，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个预测期末。
收入、利润率、再投资和营运资本须从行业驱动连接到 DCF；SBC 是经营成本且不在 FCFF 加回。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### A04 选用的 rubric（35 条，权重合计 87；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 4 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面明确要求SBC不加回 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率向量 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 营运资本变动期初期末与符号 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 驱动须连接至FCFF口径 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 年中约定与actual/365 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | E-事件终值需正确折现 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 含现金投资债务租赁少数股权 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | RSU需计入稀释股数 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值为必需输出 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 启用残余期模块 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 重算对比独立真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面要求扰动检查 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 第二组扰动检查 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不得硬编码假设 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | 年中折现期间对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 交付Excel无循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| A-DRIVER | 行业口径 | 收入由该行业规定的业务驱动构造，而不是单一增长率 | rule | 主需 | 收入须由产品量与单价构造 |
| A-PHARMA-CLIFF | 行业口径 | 专利到期后收入按题面侵蚀曲线下降，不延续到期前增长 | rule | 主需 | 专利悬崖侵蚀为指定驱动 |
| A-REASON | 行业口径 | 说明中解释行业驱动与估值结果之间的因果链 | llm | 次需 | memo须说明价值驱动 |
| X-IN-001 | 输入原样采用与历史口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入包取值须原样一致 |
| X-IN-007 | 输入原样采用与历史口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 5年显性预测期须一致 |
| X-IC-007 | 内部一致性与交叉核对 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-003 | 透明度与可审计性 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | llm | 次需 | SBC处理须与模型一致 |
| X-TA-004 | 透明度与可审计性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 年中及残余期折现期需可见 |
| X-TA-006 | 透明度与可审计性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 驱动须连接FCFF各项 |
| X-TA-007 | 透明度与可审计性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值引用可见单元格 |
| A-METRIC | 行业口径 | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | rule | 主需 | 程序强制必选项 |
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 程序强制必选项 |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 程序强制必选项 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 程序强制必选项 |

### A05（A）

<details><summary>A05｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "A05",
  "family": "A",
  "company": "敦衡银行",
  "industry": "banking",
  "industry_name": "银行与金融",
  "base_structure": "P-ARR中枢",
  "industry_drivers": [
    "平均生息资产与净息差",
    "贷款增长与资本充足率",
    "股权现金流"
  ],
  "valuation_date": "2025-11-02",
  "last_fy_end": "2025-06-30",
  "horizon": 5,
  "time_axis": {
    "midyear": false,
    "history_frequency": "annual",
    "day_count": "actual/365"
  },
  "accounting": {
    "sbc_expense": true,
    "industry_valuation": true
  },
  "residual_activity": 0.6575342465753424,
  "enabled_modules": [
    "industry_driver",
    "residual_period"
  ],
  "history": [],
  "bridge": {
    "cash": 175,
    "debt": 255,
    "investments": 29,
    "lease_liability": 17,
    "minority": 10,
    "valuation_cash_adjustment": 0,
    "shares": 87,
    "rsus": 1.2,
    "options": 0,
    "strike": 0,
    "share_price": 15
  },
  "assumptions": {
    "tax": 0.23,
    "wacc": 0.10400000000000001,
    "g": 0.027,
    "driver0": 500,
    "ebit_margin": [
      0.16,
      0.164,
      0.168,
      0.17200000000000001,
      0.176
    ],
    "da_pct": [
      0.052,
      0.052,
      0.052,
      0.052,
      0.052
    ],
    "capex_pct": [
      0.065,
      0.065,
      0.065,
      0.065,
      0.065
    ],
    "nwc_pct": [
      0.13,
      0.13,
      0.13,
      0.13,
      0.13
    ],
    "opening_nwc": 79,
    "opening_loans": 16400,
    "opening_equity": 1840,
    "loan_growth": [
      0.065,
      0.061,
      0.057,
      0.053000000000000005,
      0.049
    ],
    "risk_weight": 0.72,
    "target_capital_ratio": 0.115,
    "nim": [
      0.027,
      0.0275,
      0.028,
      0.0285,
      0.028999999999999998
    ],
    "fee_pct": [
      0.004,
      0.004,
      0.004,
      0.004,
      0.004
    ],
    "cost_pct": [
      0.014,
      0.014,
      0.014,
      0.014,
      0.014
    ],
    "credit_cost": [
      0.0035,
      0.0035,
      0.0035,
      0.0035,
      0.0035
    ],
    "cost_of_equity": 0.108
  }
}
```

</details>

##### A05｜敦衡银行估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司属于**银行与金融**。经营预测必须以平均生息资产与净息差、贷款增长与资本充足率、股权现金流为驱动搭建行业经营表，不得只用单一增长率外推。
最近完整财年末为 `2025-06-30`，估值日为 `2025-11-02`。预测 5 个完整年度，按第 1 至第 5 年整年折现，采用期末惯例，终值在第 5 年末。
按平均生息资产×净息差计算净利息收入，按风险加权资产与目标资本充足率滚动所需权益。使用股权现金流并以股权成本折现，**不得使用 FCFF/WACC**。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### A05 选用的 rubric（32 条，权重合计 80；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 7 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值活公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 指定output.xlsx与memo.md |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均生息资产×净息差×活动比例 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 估值日实际天数折现 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | RSU需计入稀释股数 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值计算 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 启用残余期模块 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查执行扰动一 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查执行扰动二 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由按键发现 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求memo说明驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需清晰标签 |
| A-BANK-NII | 经营预测 | 净利息收入等于平均生息资产乘净息差，资产增长受资本充足率约束 | rule | 主需 | 题面要求生息资产×净息差及资本约束 |
| A-BANK-EQUITY | 经营预测 | 使用股权现金流或超额收益模型，以股权成本折现 | rule | 主需 | 要求股权现金流按股权成本折现 |
| A-REASON | 经营预测 | 说明中解释行业驱动与估值结果之间的因果链 | llm | 次需 | memo需说明主要价值驱动 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入须与输入包一致 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 5年显性预测期须一致 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 股权现金流折现需展示折现期 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值引用终期与g |
| A-DRIVER | 经营预测 | 收入由该行业规定的业务驱动构造，而不是单一增长率 | rule | 主需 | 程序强制必选项 |
| A-METRIC | 经营预测 | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | rule | 主需 | 程序强制必选项 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 程序强制必选项 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 程序强制必选项 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 程序强制必选项 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 程序强制必选项 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 程序强制必选项 |

### A06（A）

<details><summary>A06｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "A06",
  "family": "A",
  "company": "岫原能源",
  "industry": "energy_resources",
  "industry_name": "能源与资源",
  "base_structure": "P-自有基座",
  "industry_drivers": [
    "现有储量递减",
    "开发资本开支新增产量",
    "商品价格"
  ],
  "valuation_date": "2025-02-11",
  "last_fy_end": "2024-09-30",
  "horizon": 4,
  "time_axis": {
    "midyear": true,
    "history_frequency": "annual",
    "day_count": "actual/365"
  },
  "accounting": {
    "sbc_expense": true,
    "industry_valuation": true
  },
  "residual_activity": 0.6328767123287671,
  "enabled_modules": [
    "industry_driver",
    "residual_period"
  ],
  "history": [],
  "bridge": {
    "cash": 184,
    "debt": 268,
    "investments": 30,
    "lease_liability": 18,
    "minority": 11,
    "valuation_cash_adjustment": 0,
    "shares": 90,
    "rsus": 1.2,
    "options": 0,
    "strike": 0,
    "share_price": 15
  },
  "assumptions": {
    "tax": 0.23,
    "wacc": 0.10500000000000001,
    "g": 0.025,
    "driver0": 524,
    "ebit_margin": [
      0.16,
      0.164,
      0.168,
      0.17200000000000001
    ],
    "da_pct": [
      0.052,
      0.052,
      0.052,
      0.052
    ],
    "capex_pct": [
      0.065,
      0.065,
      0.065,
      0.065
    ],
    "nwc_pct": [
      0.13,
      0.13,
      0.13,
      0.13
    ],
    "opening_nwc": 83,
    "opening_base_production": 380,
    "decline_rate": [
      0.08,
      0.077,
      0.074,
      0.07100000000000001
    ],
    "development_capex": [
      165,
      185,
      205,
      225
    ],
    "capex_per_unit": 4.3,
    "commodity_price": [
      1.94,
      1.99,
      2.04,
      2.09
    ]
  }
}
```

</details>

##### A06｜岫原能源估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司属于**能源与资源**。经营预测必须以现有储量递减、开发资本开支新增产量、商品价格为驱动搭建行业经营表，不得只用单一增长率外推。
最近完整财年末为 `2024-09-30`，估值日 `2025-02-11` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，经营量按残期天数比例计入，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个预测期末。
收入、利润率、再投资和营运资本须从行业驱动连接到 DCF；SBC 是经营成本且不在 FCFF 加回。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### A06 选用的 rubric（40 条，权重合计 100；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 1 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值活公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 指定output.xlsx与memo.md |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 要求Results页与保留Inputs页 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面要求SBC为经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 产量期初减递减加新增 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均产量乘价格及活动比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率 |
| 03-CAPEX | 经营预测 | 资本开支同时包含强度部分与重排新增部分 | rule | 次需 | 强度capex加开发capex |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 营运资本变动符号与期间 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用给定期初NWC |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为必然涉及 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 年中约定与实际天数 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | Gordon终值时点与折现 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 股权桥含现金投资债务租赁少数 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | RSU进入稀释股数 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值计算 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 启用残余期模块 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面要求扰动检查 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面要求两组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不得硬编码假设 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | 多期预测折现列对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 估值链无循环引用 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo含驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| A-DRIVER | 经营预测 | 收入由该行业规定的业务驱动构造，而不是单一增长率 | rule | 主需 | 收入须由产量×价格驱动 |
| A-ENERGY-DECLINE | 经营预测 | 现有储量产量按递减曲线下降，新增产量依赖开发资本开支 | rule | 主需 | 储量递减与开发资本开支新增产量 |
| A-REASON | 经营预测 | 说明中解释行业驱动与估值结果之间的因果链 | llm | 次需 | memo须说明主要价值驱动 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入须与输入包一致 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 预测期须为4年 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 年中折现与残余期需可见期数 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 驱动连接FCFF各组成项 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值引用可见单元格 |
| A-METRIC | 经营预测 | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | rule | 主需 | 程序强制必选项 |

### A07（A）

<details><summary>A07｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "A07",
  "family": "A",
  "company": "砚川公用",
  "industry": "utilities",
  "industry_name": "公用事业与基础设施",
  "base_structure": "N-期中滚动",
  "industry_drivers": [
    "受监管资产基数",
    "允许回报率与折旧回收",
    "长期资本开支"
  ],
  "valuation_date": "2026-04-22",
  "last_fy_end": "2025-11-30",
  "horizon": 5,
  "time_axis": {
    "midyear": false,
    "history_frequency": "annual",
    "day_count": "actual/365"
  },
  "accounting": {
    "sbc_expense": true,
    "industry_valuation": true
  },
  "residual_activity": 0.6082191780821918,
  "enabled_modules": [
    "industry_driver",
    "residual_period"
  ],
  "history": [],
  "bridge": {
    "cash": 193,
    "debt": 281,
    "investments": 31,
    "lease_liability": 19,
    "minority": 12,
    "valuation_cash_adjustment": 0,
    "shares": 93,
    "rsus": 1.2,
    "options": 0,
    "strike": 0,
    "share_price": 15
  },
  "assumptions": {
    "tax": 0.23,
    "wacc": 0.10600000000000001,
    "g": 0.025,
    "driver0": 1520,
    "ebit_margin": [
      0.16,
      0.164,
      0.168,
      0.17200000000000001,
      0.176
    ],
    "da_pct": [
      0.052,
      0.052,
      0.052,
      0.052,
      0.052
    ],
    "capex_pct": [
      0.065,
      0.065,
      0.065,
      0.065,
      0.065
    ],
    "nwc_pct": [
      0.13,
      0.13,
      0.13,
      0.13,
      0.13
    ],
    "opening_nwc": 87,
    "rate_base_additions": [
      90,
      98,
      106,
      114,
      122
    ],
    "allowed_return": [
      0.068,
      0.068,
      0.068,
      0.068,
      0.068
    ],
    "regulatory_depreciation_rate": [
      0.037,
      0.037,
      0.037,
      0.037,
      0.037
    ]
  }
}
```

</details>

##### A07｜砚川公用估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司属于**公用事业与基础设施**。经营预测必须以受监管资产基数、允许回报率与折旧回收、长期资本开支为驱动搭建行业经营表，不得只用单一增长率外推。
最近完整财年末为 `2025-11-30`，估值日 `2026-04-22` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，经营量按残期天数比例计入，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个预测期末。
收入、利润率、再投资和营运资本须从行业驱动连接到 DCF；SBC 是经营成本且不在 FCFF 加回。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### A07 选用的 rubric（40 条，权重合计 100；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 1 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键须唯一数值 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定单位口径 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 需output.xlsx与memo.md |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面明确SBC为经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 监管资产基数期初加新增减折旧 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均资产基数×回报率×活动比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT用当期利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC期初期末与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用指定期初NWC 87 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 监管资产基数需期初加新增减折旧滚动 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径且SBC不加回 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | actual/365折现期,非年中 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值时点与折现必涉及 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 桥含现金投资债务租赁少数 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | RSU需计入稀释股数 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值必输出 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 启用残余期模块 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查含扰动一 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查含扰动二 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不得嵌入假设常数 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | 五期预测须列对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 交付Excel须无循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo含驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯模型需期间与项目标签 |
| A-DRIVER | 经营预测 | 收入由该行业规定的业务驱动构造，而不是单一增长率 | rule | 主需 | 题面禁止单一增长率外推 |
| A-UTIL-RAB | 经营预测 | 允许收入等于受监管资产基数乘允许回报率加折旧回收 | rule | 主需 | 允许收入按RAB回报加折旧 |
| A-REASON | 经营预测 | 说明中解释行业驱动与估值结果之间的因果链 | llm | 次需 | memo需说明价值驱动 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入值须与输入包一致 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 5年显性预测期须一致 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| X-TA-003 | 表达与专业可用性 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | llm | 次需 | SBC处理须说明与模型一致 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 期中滚动需展示折现期 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF须由驱动连接构建 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 使用Gordon终值g |
| A-METRIC | 经营预测 | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | rule | 主需 | 程序强制必选项 |

### A08（A）

<details><summary>A08｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "A08",
  "family": "A",
  "company": "栖桐置业",
  "industry": "real_estate",
  "industry_name": "房地产",
  "base_structure": "E-事件终值",
  "industry_drivers": [
    "可租面积与出租率",
    "单位租金",
    "NOI 资本化率与 NAV"
  ],
  "valuation_date": "2024-08-30",
  "last_fy_end": "2024-03-31",
  "horizon": 5,
  "time_axis": {
    "midyear": true,
    "history_frequency": "annual",
    "day_count": "actual/365"
  },
  "accounting": {
    "sbc_expense": true,
    "industry_valuation": true
  },
  "residual_activity": 0.5835616438356165,
  "enabled_modules": [
    "industry_driver",
    "residual_period"
  ],
  "history": [],
  "bridge": {
    "cash": 202,
    "debt": 294,
    "investments": 32,
    "lease_liability": 20,
    "minority": 13,
    "valuation_cash_adjustment": 0,
    "shares": 96,
    "rsus": 1.2,
    "options": 0,
    "strike": 0,
    "share_price": 15
  },
  "assumptions": {
    "tax": 0.23,
    "wacc": 0.10700000000000001,
    "g": 0.025,
    "driver0": 572,
    "ebit_margin": [
      0.16,
      0.164,
      0.168,
      0.17200000000000001,
      0.176
    ],
    "da_pct": [
      0.052,
      0.052,
      0.052,
      0.052,
      0.052
    ],
    "capex_pct": [
      0.065,
      0.065,
      0.065,
      0.065,
      0.065
    ],
    "nwc_pct": [
      0.13,
      0.13,
      0.13,
      0.13,
      0.13
    ],
    "opening_nwc": 91,
    "rentable_area": 98000,
    "occupancy": [
      0.91,
      0.925,
      0.93,
      0.94,
      0.94
    ],
    "rent_per_unit": [
      0.0031,
      0.00318,
      0.00326,
      0.00334,
      0.00342
    ],
    "operating_cost_pct": [
      0.29,
      0.29,
      0.29,
      0.29,
      0.29
    ],
    "cap_rate": [
      0.061,
      0.061,
      0.061,
      0.061,
      0.061
    ],
    "capex_reserve": 28
  }
}
```

</details>

##### A08｜栖桐置业估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司属于**房地产**。经营预测必须以可租面积与出租率、单位租金、NOI 资本化率与 NAV为驱动搭建行业经营表，不得只用单一增长率外推。
最近完整财年末为 `2024-03-31`，估值日为 `2024-08-30`，预测 5 期经营数据。
按面积×出租率×单位租金计算收入，扣经营成本得到 NOI；以首个预测期 NOI/资本化率得到估值日物业价值，再加现金、减债务和资本开支储备得到 NAV。**不得使用 FCFF/WACC。**

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

#### A08 选用的 rubric（32 条，权重合计 84；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 7 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需交付可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 指定output.xlsx与memo.md |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需Results页并保留Inputs页 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | NAV每股需除稀释股数 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 存在RSU需计入稀释 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查执行第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查执行第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 题面禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 租金等假设不得硬编码 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | NAV链不应有循环引用 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求memo说明驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可追溯经营表需期间与项目标签 |
| A-DRIVER | 经营预测 | 收入由该行业规定的业务驱动构造，而不是单一增长率 | rule | 主需 | 收入按面积×出租率×租金 |
| A-METRIC | 经营预测 | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | rule | 主需 | NOI按扣经营成本口径 |
| A-VALUATION | 经营预测 | 估值方法适配行业（金融用股权现金流或超额收益，房地产用 NOI/NAV 等），不硬套 FCFF | rule | 主需 | 禁用FCFF/WACC |
| A-RE-NAV | 经营预测 | 物业价值等于 NOI 除以资本化率，NAV 扣除负债 | rule | 主需 | NOI/资本化率及NAV桥 |
| A-REASON | 经营预测 | 说明中解释行业驱动与估值结果之间的因果链 | llm | 次需 | memo需说明价值驱动 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入包数值须一致 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 预测期为5年需一致 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 程序强制必选项 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 程序强制必选项 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 程序强制必选项 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 程序强制必选项 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 程序强制必选项 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 程序强制必选项 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 程序强制必选项 |

### A09（A）

<details><summary>A09｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "A09",
  "family": "A",
  "company": "铖序精工",
  "industry": "manufacturing",
  "industry_name": "制造与工业设备",
  "base_structure": "N-期中滚动",
  "industry_drivers": [
    "两产品产能、投入量与单次良率",
    "两产品三物料 BOM 与采购",
    "三类存货、资本开支与实际天数 DCF"
  ],
  "valuation_date": "2026-03-17",
  "last_fy_end": "2025-11-30",
  "horizon": 5,
  "time_axis": {
    "midyear": false,
    "history_frequency": "annual",
    "day_count": "actual/365",
    "terminal_convention": "last_fiscal_year_end"
  },
  "accounting": {
    "sbc_expense": true,
    "industry_valuation": true,
    "inventory_basis": "current_standard_cost_excluding_depreciation"
  },
  "enabled_modules": [
    "bom_manufacturing",
    "inventory_rollforward",
    "residual_period",
    "operating_sensitivity"
  ],
  "history": [],
  "opening": {
    "ppe": 690.0,
    "accounts_receivable": 248.0,
    "raw_alloy": 86.0,
    "raw_resin": 58.0,
    "raw_steel": 74.0,
    "wip": 64.0,
    "finished_goods": 82.0,
    "accounts_payable": 142.0
  },
  "assumptions": {
    "tax": 0.23,
    "wacc": 0.102,
    "g": 0.025,
    "ppe_depreciation_rate": 0.085,
    "fixed_capex": [
      74.0,
      79.0,
      82.0,
      87.0,
      91.0
    ],
    "expansion_capex": [
      28.0,
      48.0,
      18.0,
      44.0,
      20.0
    ],
    "selling_expense_pct": [
      0.061,
      0.06,
      0.059,
      0.058,
      0.057
    ],
    "admin_expense": [
      51.0,
      54.0,
      57.0,
      60.0,
      63.0
    ],
    "sbc": [
      13.0,
      14.0,
      15.0,
      16.0,
      17.0
    ],
    "fixed_manufacturing_cost": [
      108.0,
      114.0,
      120.0,
      126.0,
      132.0
    ],
    "ar_days": [
      57.0,
      56.0,
      55.0,
      54.0,
      53.0
    ],
    "raw_days": [
      25.0,
      24.0,
      23.0,
      22.0,
      21.0
    ],
    "wip_days": [
      18.0,
      18.0,
      17.0,
      17.0,
      16.0
    ],
    "fg_days": [
      30.0,
      29.0,
      28.0,
      27.0,
      26.0
    ],
    "ap_days": [
      42.0,
      42.0,
      41.0,
      41.0,
      40.0
    ],
    "sensitivity_alloy_multiplier": [
      0.9,
      0.95,
      1.0,
      1.05,
      1.1
    ],
    "sensitivity_yield_multiplier": [
      0.94,
      0.97,
      1.0,
      1.03,
      1.06
    ]
  },
  "products": {
    "alpha": {
      "name": "阿尔法阀组",
      "capacity": [
        400.0,
        430.0,
        460.0,
        490.0,
        520.0
      ],
      "utilization": [
        0.74,
        0.75,
        0.76,
        0.77,
        0.78
      ],
      "demand": [
        305.0,
        330.0,
        360.0,
        390.0,
        420.0
      ],
      "yield": [
        0.9,
        0.915,
        0.925,
        0.935,
        0.94
      ],
      "sell_through": [
        0.97,
        0.975,
        0.98,
        0.985,
        0.99
      ],
      "unit_price": [
        7.05,
        7.25,
        7.44,
        7.62,
        7.86
      ],
      "conversion_cost_per_input": [
        0.16,
        0.165,
        0.17,
        0.175,
        0.18
      ],
      "bom_alloy": [
        1.35,
        1.34,
        1.33,
        1.32,
        1.31
      ],
      "bom_resin": [
        2.1,
        2.08,
        2.06,
        2.04,
        2.02
      ],
      "bom_steel": [
        3.4,
        3.37,
        3.34,
        3.31,
        3.28
      ]
    },
    "beta": {
      "name": "贝塔执行器",
      "capacity": [
        270.0,
        270.0,
        295.0,
        320.0,
        345.0
      ],
      "utilization": [
        0.7,
        0.72,
        0.74,
        0.76,
        0.78
      ],
      "demand": [
        181.0,
        190.0,
        209.0,
        236.0,
        260.0
      ],
      "yield": [
        0.86,
        0.875,
        0.89,
        0.905,
        0.915
      ],
      "sell_through": [
        0.96,
        0.965,
        0.97,
        0.975,
        0.98
      ],
      "unit_price": [
        9.24,
        9.51,
        9.78,
        10.08,
        10.38
      ],
      "conversion_cost_per_input": [
        0.21,
        0.216,
        0.222,
        0.228,
        0.234
      ],
      "bom_alloy": [
        1.65,
        1.64,
        1.63,
        1.62,
        1.61
      ],
      "bom_resin": [
        1.7,
        1.69,
        1.68,
        1.67,
        1.66
      ],
      "bom_steel": [
        2.4,
        2.39,
        2.38,
        2.37,
        2.36
      ]
    }
  },
  "materials": {
    "alloy": {
      "name": "合金料",
      "purchase_price": [
        1.25,
        1.31,
        1.37,
        1.42,
        1.48
      ]
    },
    "resin": {
      "name": "工程树脂",
      "purchase_price": [
        0.44,
        0.46,
        0.48,
        0.5,
        0.52
      ]
    },
    "steel": {
      "name": "特种钢",
      "purchase_price": [
        0.8,
        0.82,
        0.85,
        0.88,
        0.91
      ]
    }
  },
  "bridge": {
    "cash": 157.0,
    "debt": 229.0,
    "investments": 27.0,
    "lease_liability": 15.0,
    "minority": 8.0,
    "valuation_cash_adjustment": 0.0,
    "shares": 81.0,
    "rsus": 1.2,
    "options": 2.4,
    "strike": 12.0,
    "share_price": 15.0
  },
  "sensitivity": {
    "row_driver": "beta yield multiplier",
    "column_driver": "alloy price multiplier",
    "center": [
      3,
      3
    ],
    "yield_cap": 0.999
  }
}
```

</details>

##### A09｜铖序精工 BOM 制造估值

你是估值分析师。读取 `/app/inputs.xlsx` 和 `/app/inputs.json`，建立可追溯的活公式经营模型及 DCF，交付 `/app/output.xlsx` 和 `/app/memo.md`。禁止联网、外部工作簿链接或用结果常数替代公式。公司属于制造与工业设备行业，以 BOM 单耗、良率与采购驱动成本。

##### 时间、单位与输入

- 估值日 2026-03-17，最近财年末 2025-11-30。预测为估值日至 2026-11-30 的残余段及随后四个完整财年，共五段。第一段经营流量、资本开支和存量释放按估值日后活动比例计；完整年度用于决定产能、销量、耗用及期末余额。实际天数/365，期末折现，Gordon 终值位于最后完整财年末。
- 金额为百万元，数量为千件，材料单耗为材料单位/千件投入，材料采购价为百万元/材料单位；产品售价为百万元/千件，转化成本为百万元/千件投入。金额及单位以 Inputs 键名说明为准。材料耗用量与采购量均以材料单位计量，材料耗用成本、采购成本及存货金额均以百万元计量。
- 两个产品 `alpha`、`beta` 分别建模；共用 `alloy`、`resin`、`steel` 三类材料。首段活动比例、财年和日期由输入日期公式计算，不得手工给定另一套日期。

##### 经营、BOM 与存货口径

1. 每产品有效产能=产能×利用率；投入量=min(有效产能, 订单需求)，因此投入不得超过有效产能。合格产量=投入量×良率，良率只作用一次；销量=合格产量×销售率。收入=销量×产品售价。不要用收入乘材料成本率替代 BOM。
2. 每产品、每材料、每期耗用量=该产品投入量×对应 BOM 单耗；耗用成本=耗用量×该材料采购价。再跨产品汇总每种材料的耗用量及成本。产品转化成本按投入量×单位转化成本，销售结转的材料及转化成本分别按产品销售率计。
3. 每材料期末原材料金额=该材料全年耗用成本×原材料天数/全年实际天数。原材料滚动的金额口径为：期末原材料金额=按本期活动比例释放的期初原材料金额＋采购成本－当期耗用成本。首段采购量=全年耗用量×活动比例＋(期末原材料金额－估值日期初原材料金额×活动比例)/当期采购价；后续完整财年活动比例为 1，将式中“估值日期初原材料”替换为相邻期初原材料。采购成本=采购量×当期采购价。该公式保证期末原材料金额=期初原材料金额×活动比例＋采购成本－全年耗用成本×活动比例；只有首段释放活动比例的期初存量，完整财年保留并滚入下一期。采购不是 COGS。
4. 在制品期末=(材料耗用成本＋转化成本＋固定制造成本)×在制品天数/全年实际天数；产成品期末=材料及转化销售成本×产成品天数/全年实际天数。原料、在制品、产成品分别滚动，不得合并成一个收入比例。
5. 应收=全年收入×应收天数/全年实际天数；应付=采购成本×付款天数/全年实际天数。NWC=应收＋三类材料原材料＋在制品＋产成品－应付。首期变动用估值日实际余额，后续用相邻期末差额；不要在 FCFF 中既扣 NWC 变动又重复扣采购或库存变动。
6. 折旧前 EBIT=收入－销售材料及转化成本－固定制造成本－销售费用－管理费用－SBC，残余段乘活动比例。SBC 是经营成本且不加回。固定资产按期初＋资本开支－折旧滚动；资本开支含维护及扩产，首段乘活动比例。折旧=(期初固定资产＋当期资本开支×50%)×年折旧率×全年实际天数/365。现金税=MAX(0, EBIT－折旧)×税率。FCFF=EBIT－折旧－现金税＋折旧－资本开支－ΔNWC。

##### 估值与经营敏感性

用 WACC 对五段 FCFF 按实际天数折现，Gordon 终值=末期 FCFF×(1+g)/(WACC－g)，在末期实际日期折现。股权价值=企业价值＋现金＋估值现金调整＋投资－债务－租赁负债－少数股权。稀释股数包括普通股、RSU 和库存股法期权。

提交合金采购价乘数（列）×贝塔良率乘数（行）的 **5×5 企业价值敏感性**。每格必须分别把对应乘数应用于全部五期合金价格或贝塔良率，重新计算收入、BOM 耗用及采购、三类存货、COGS、NWC、资本开支、折旧、现金税、FCFF、终值和企业价值；不能只做收入缩放、终值缩放、二维插值或链接中心格。良率上限为 99.9%。中心格须等于基准企业价值。

##### 结果键与交付检查

在 `Results` 页逐项放置 `inputs.json` 的 `public_output_keys`：键名右邻为唯一数值活公式，键不得重复。中间表布局自由，但必须保留 `Inputs` 原始语义键、数值向量及单位，并显示关键计算链而非只交估值页。`Required Keys` 提供键口径，不是坐标模板。

`memo.md` 简述产能/良率、材料采购和库存对价值的驱动，以及至少一个局限。隐藏检查会重算两组经营、营运资本、估值及股权桥扰动，并核对全部敏感性网格及关键公式依赖。

#### A09 选用的 rubric（42 条，权重合计 106；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 3 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须交付可读 output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | Results 键唯一数值公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面要求保留单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 指定 output.xlsx 与 memo.md |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面要求SBC为经营成本不加回 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 须保留并一致使用输入包数值 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 题面指定残余段加四完整财年 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | NWC变动期初期末与符号 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 天数法用全年实际天数 |
| A-DRIVER | 经营预测 | 收入由该行业规定的业务驱动构造，而不是单一增长率 | rule | 主需 | 收入由产能良率销量驱动 |
| A-REASON | 经营预测 | 说明中解释行业驱动与估值结果之间的因果链 | llm | 次需 | memo需解释驱动与价值 |
| A-MFG-UTIL | 经营预测 | 产量不超过有效产能乘利用率上限，扩产在投产后才增加产能 | rule | 主需 | 投入不超有效产能 |
| A-MFG-YIELD | 经营预测 | 合格产量等于投入量乘良率，良率在产量和成本链中只作用一次 | rule | 主需 | 良率只作用一次 |
| A-MFG-BOM | 经营预测 | 各产品各物料耗用量等于投入量乘 BOM 单耗，耗用成本等于耗用量乘采购价，不以收入成本率替代 | rule | 主需 | BOM耗用量与成本 |
| A-MFG-PURCHASE | 经营预测 | 采购与耗用及原材料滚动勾稽，采购不得直接作为 COGS | rule | 主需 | 采购与原料滚动勾稽 |
| A-MFG-INVENTORY | 经营预测 | 原材料、在制品和产成品分别按题面口径滚动，不合并为单一收入比例 | rule | 主需 | 三类存货分别滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 题面要求固定资产滚动 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面给定FCFF口径 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数期末折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在末财年末折现 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面列明股权桥项目 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | RSU与库存股法期权 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 稀释每股价值 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段残余期按活动比例 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果键须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 存在独立数值真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 中间表布局自由 |
| X-IC-001 | 公式与模型工程 | 敏感性表中与基准行列假设相交的单元格，其值与模型相同口径基准输出的相对差异不超过题面容差；题面未给容差时为 0.1%。 | rule | 主需 | 中心格须等于基准EV |
| X-IC-002 | 公式与模型工程 | 每条敏感性轴的完整值序列与题面指定的起点、终点及步长完全一致。 | rule | 主需 | 乘数轴由输入指定 |
| X-IF-003 | 公式与模型工程 | 敏感性网格的每个结果值均与模型在相同行列输入下的重算值一致，容差按题面规定。 | rule | 主需 | 每格须全模型重算 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求提交memo含驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 要求显示关键计算链 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数期末折现需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 题面给出FCFF分项构建 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 使用Gordon终值 |
| A-METRIC | 经营预测 | 行业关键指标（如净留存、同店、净息差、综合成本率、出租率）按题面口径计算 | rule | 主需 | 程序强制必选项 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 程序强制必选项 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 程序强制必选项 |

### D01（D）

<details><summary>D01｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D01",
  "seed": 412248,
  "candidate_index": 6,
  "family": "D",
  "company": "砾川数科",
  "dimension_selection": {
    "scenario": "区域低温加工",
    "difficulty": "L1: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "capacity",
    "valuation_mechanism": "exit",
    "accounting_basis": "SBC经营成本",
    "output_mode": "three_statements_dcf",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days"
  ],
  "selection_rationale": {
    "scenario": "区域低温加工要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "capacity",
    "unit": "千吨年产能",
    "price_unit": "百万元/千吨",
    "description": "区域低温加工"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-03-05",
  "last_fy_end": "2024-08-31",
  "horizon": 4,
  "history": [
    {
      "start": "2022-03-01",
      "end": "2022-05-31",
      "fiscal_year": "2022",
      "revenue": 247.496366,
      "ebit": 25.28879,
      "operating_cost_ex_sbc": 197.741294,
      "sbc": 5.877544,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-06-01",
      "end": "2022-08-31",
      "fiscal_year": "2022",
      "revenue": 254.506512,
      "ebit": 27.573806,
      "operating_cost_ex_sbc": 202.426078,
      "sbc": 6.405235,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2022-09-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 261.51666,
      "ebit": 29.92344,
      "operating_cost_ex_sbc": 207.059102,
      "sbc": 6.932925,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2022-12-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 268.526806,
      "ebit": 32.33769,
      "operating_cost_ex_sbc": 211.640368,
      "sbc": 7.460615,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2023-03-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 275.536952,
      "ebit": 34.816558,
      "operating_cost_ex_sbc": 216.169876,
      "sbc": 7.988305,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2023-06-01",
      "end": "2023-08-31",
      "fiscal_year": "2023",
      "revenue": 282.547099,
      "ebit": 37.360043,
      "operating_cost_ex_sbc": 220.647626,
      "sbc": 8.515996,
      "nonrecurring_gain": 1.85
    },
    {
      "start": "2023-09-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 289.557245,
      "ebit": 39.968145,
      "operating_cost_ex_sbc": 225.073615,
      "sbc": 9.043686,
      "nonrecurring_gain": 2.22
    },
    {
      "start": "2023-12-01",
      "end": "2024-02-29",
      "fiscal_year": "2024",
      "revenue": 296.567391,
      "ebit": 42.640864,
      "operating_cost_ex_sbc": 229.447848,
      "sbc": 9.571376,
      "nonrecurring_gain": 2.59
    },
    {
      "start": "2024-03-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 303.577537,
      "ebit": 45.3782,
      "operating_cost_ex_sbc": 233.770321,
      "sbc": 10.099066,
      "nonrecurring_gain": 2.96
    },
    {
      "start": "2024-06-01",
      "end": "2024-08-31",
      "fiscal_year": "2024",
      "revenue": 310.587684,
      "ebit": 48.180153,
      "operating_cost_ex_sbc": 238.041036,
      "sbc": 10.626757,
      "nonrecurring_gain": 6.874015
    }
  ],
  "opening_nwc": 303.483176,
  "opening_deferred": 0,
  "opening_ppe": 254.82,
  "opening_rou": 0,
  "opening_debt": 164.4,
  "opening_retained_earnings": 131.52,
  "contributed_capital": 320.58,
  "opening_cash": 82.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 120.7,
    "price0": 12.2298092583,
    "driver_add": [
      8.16,
      9.282,
      10.404,
      11.526
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.11570000000000001,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.1,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 90.42,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      20.55,
      0,
      0,
      0
    ],
    "debt_repayment": [
      8.22,
      16.44,
      24.660000000000004,
      32.88
    ],
    "beta_unlevered": 0.84,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "utilization": [
      0.74,
      0.758,
      0.776,
      0.794
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      53.7,
      57.7,
      61.7,
      65.7
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 82.2,
    "debt": 164.4,
    "investments": 12.33,
    "lease_liability": 0,
    "minority": 9.864,
    "valuation_cash_adjustment": 9.864,
    "shares": 128,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 12.8
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 338.664,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 320.58,
    "opening_cash": 82.2,
    "opening_operating_current_assets": 338.664,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 249.3,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "multi_method",
  "c_structure_definition": "多方法估值与反推",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge"
    ],
    "c": "multi_method"
  },
  "opening_nwc_last_fye": 303.483176,
  "opening_nwc_valuation_date": 277.014,
  "market": {
    "market_price": 32.11
  },
  "event_public_facts": {
    "type": "baseline",
    "description": "建立基座模型，保存第 1 步快照。"
  },
  "event_type": "baseline",
  "steps": [
    {
      "step": 1,
      "event_type": "baseline",
      "task_id": "D01"
    },
    {
      "step": 2,
      "event_type": "rebase",
      "task_id": "D01_S2"
    },
    {
      "step": 3,
      "event_type": "financing_and_capex_rearrangement",
      "task_id": "D01_S3"
    },
    {
      "step": 4,
      "event_type": "terminal_method_change",
      "task_id": "D01_S4"
    }
  ],
  "independent_from_BC": true
}
```

</details>

##### D01｜砾川数科估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题不只要一个目标价：需用 Gordon 与退出倍数两种方法分别估值，做反向推导，并给出估值区间。
公司财年截至每年 8 月 31 日，最近完整财年末为 `2024-08-31`，估值日 `2025-03-05` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
分别给出 Gordon 与退出倍数的终值、EV、股权价值和每股价值，不得加权成一个数。由 Gordon 终值反推隐含 EV/EBITDA，由退出倍数反推隐含 g，并用给定股价在工作簿内以公式迭代/求解隐含 WACC；Football Field 按给定折现率和增长区间。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

每步完成后将对应工作簿保存为 `/app/snapshots/step-N.xlsx`；不得覆盖前步快照。

本题包含连续结构事件；按 `steps/step-N/instruction.md` 顺序执行。

#### step-1

<details><summary>D01/step-1｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D01",
  "seed": 412248,
  "candidate_index": 6,
  "family": "D",
  "step": 1,
  "company": "砾川数科",
  "dimension_selection": {
    "scenario": "区域低温加工",
    "difficulty": "L1: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "capacity",
    "valuation_mechanism": "exit",
    "accounting_basis": "SBC经营成本",
    "output_mode": "three_statements_dcf",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days"
  ],
  "selection_rationale": {
    "scenario": "区域低温加工要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "capacity",
    "unit": "千吨年产能",
    "price_unit": "百万元/千吨",
    "description": "区域低温加工"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-03-05",
  "last_fy_end": "2024-08-31",
  "horizon": 4,
  "history": [
    {
      "start": "2022-03-01",
      "end": "2022-05-31",
      "fiscal_year": "2022",
      "revenue": 247.496366,
      "ebit": 25.28879,
      "operating_cost_ex_sbc": 197.741294,
      "sbc": 5.877544,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-06-01",
      "end": "2022-08-31",
      "fiscal_year": "2022",
      "revenue": 254.506512,
      "ebit": 27.573806,
      "operating_cost_ex_sbc": 202.426078,
      "sbc": 6.405235,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2022-09-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 261.51666,
      "ebit": 29.92344,
      "operating_cost_ex_sbc": 207.059102,
      "sbc": 6.932925,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2022-12-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 268.526806,
      "ebit": 32.33769,
      "operating_cost_ex_sbc": 211.640368,
      "sbc": 7.460615,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2023-03-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 275.536952,
      "ebit": 34.816558,
      "operating_cost_ex_sbc": 216.169876,
      "sbc": 7.988305,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2023-06-01",
      "end": "2023-08-31",
      "fiscal_year": "2023",
      "revenue": 282.547099,
      "ebit": 37.360043,
      "operating_cost_ex_sbc": 220.647626,
      "sbc": 8.515996,
      "nonrecurring_gain": 1.85
    },
    {
      "start": "2023-09-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 289.557245,
      "ebit": 39.968145,
      "operating_cost_ex_sbc": 225.073615,
      "sbc": 9.043686,
      "nonrecurring_gain": 2.22
    },
    {
      "start": "2023-12-01",
      "end": "2024-02-29",
      "fiscal_year": "2024",
      "revenue": 296.567391,
      "ebit": 42.640864,
      "operating_cost_ex_sbc": 229.447848,
      "sbc": 9.571376,
      "nonrecurring_gain": 2.59
    },
    {
      "start": "2024-03-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 303.577537,
      "ebit": 45.3782,
      "operating_cost_ex_sbc": 233.770321,
      "sbc": 10.099066,
      "nonrecurring_gain": 2.96
    },
    {
      "start": "2024-06-01",
      "end": "2024-08-31",
      "fiscal_year": "2024",
      "revenue": 310.587684,
      "ebit": 48.180153,
      "operating_cost_ex_sbc": 238.041036,
      "sbc": 10.626757,
      "nonrecurring_gain": 6.874015
    }
  ],
  "opening_nwc": 303.483176,
  "opening_deferred": 0,
  "opening_ppe": 254.82,
  "opening_rou": 0,
  "opening_debt": 164.4,
  "opening_retained_earnings": 131.52,
  "contributed_capital": 320.58,
  "opening_cash": 82.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 120.7,
    "price0": 12.2298092583,
    "driver_add": [
      8.16,
      9.282,
      10.404,
      11.526
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.11570000000000001,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.1,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 90.42,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      20.55,
      0,
      0,
      0
    ],
    "debt_repayment": [
      8.22,
      16.44,
      24.660000000000004,
      32.88
    ],
    "beta_unlevered": 0.84,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "utilization": [
      0.74,
      0.758,
      0.776,
      0.794
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      53.7,
      57.7,
      61.7,
      65.7
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 82.2,
    "debt": 164.4,
    "investments": 12.33,
    "lease_liability": 0,
    "minority": 9.864,
    "valuation_cash_adjustment": 9.864,
    "shares": 128,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 12.8
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 338.664,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 320.58,
    "opening_cash": 82.2,
    "opening_operating_current_assets": 338.664,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 249.3,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "multi_method",
  "c_structure_definition": "多方法估值与反推",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge"
    ],
    "c": "multi_method"
  },
  "opening_nwc_last_fye": 303.483176,
  "opening_nwc_valuation_date": 277.014,
  "market": {
    "market_price": 32.11
  },
  "event_public_facts": {
    "type": "baseline",
    "description": "建立基座模型，保存第 1 步快照。"
  },
  "event_type": "baseline"
}
```

</details>

##### D01｜砾川数科估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题不只要一个目标价：需用 Gordon 与退出倍数两种方法分别估值，做反向推导，并给出估值区间。
公司财年截至每年 8 月 31 日，最近完整财年末为 `2024-08-31`，估值日 `2025-03-05` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
分别给出 Gordon 与退出倍数的终值、EV、股权价值和每股价值，不得加权成一个数。由 Gordon 终值反推隐含 EV/EBITDA，由退出倍数反推隐含 g，并用给定股价在工作簿内以公式迭代/求解隐含 WACC；Football Field 按给定折现率和增长区间。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

每步完成后将对应工作簿保存为 `/app/snapshots/step-N.xlsx`；不得覆盖前步快照。

#### step-2

<details><summary>D01/step-2｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D01_S2",
  "seed": 412248,
  "candidate_index": 6,
  "family": "D",
  "step": 2,
  "company": "砾川数科",
  "dimension_selection": {
    "scenario": "区域低温加工",
    "difficulty": "L1: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "capacity",
    "valuation_mechanism": "exit",
    "accounting_basis": "SBC经营成本",
    "output_mode": "three_statements_dcf",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days"
  ],
  "selection_rationale": {
    "scenario": "区域低温加工要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "capacity",
    "unit": "千吨年产能",
    "price_unit": "百万元/千吨",
    "description": "区域低温加工"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-03-05",
  "last_fy_end": "2024-08-31",
  "horizon": 4,
  "history": [
    {
      "start": "2022-03-01",
      "end": "2022-05-31",
      "fiscal_year": "2022",
      "revenue": 247.496366,
      "ebit": 25.28879,
      "operating_cost_ex_sbc": 197.741294,
      "sbc": 5.877544,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-06-01",
      "end": "2022-08-31",
      "fiscal_year": "2022",
      "revenue": 254.506512,
      "ebit": 27.573806,
      "operating_cost_ex_sbc": 202.426078,
      "sbc": 6.405235,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2022-09-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 261.51666,
      "ebit": 29.92344,
      "operating_cost_ex_sbc": 207.059102,
      "sbc": 6.932925,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2022-12-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 268.526806,
      "ebit": 32.33769,
      "operating_cost_ex_sbc": 211.640368,
      "sbc": 7.460615,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2023-03-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 275.536952,
      "ebit": 34.816558,
      "operating_cost_ex_sbc": 216.169876,
      "sbc": 7.988305,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2023-06-01",
      "end": "2023-08-31",
      "fiscal_year": "2023",
      "revenue": 282.547099,
      "ebit": 37.360043,
      "operating_cost_ex_sbc": 220.647626,
      "sbc": 8.515996,
      "nonrecurring_gain": 1.85
    },
    {
      "start": "2023-09-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 289.557245,
      "ebit": 39.968145,
      "operating_cost_ex_sbc": 225.073615,
      "sbc": 9.043686,
      "nonrecurring_gain": 2.22
    },
    {
      "start": "2023-12-01",
      "end": "2024-02-29",
      "fiscal_year": "2024",
      "revenue": 296.567391,
      "ebit": 42.640864,
      "operating_cost_ex_sbc": 229.447848,
      "sbc": 9.571376,
      "nonrecurring_gain": 2.59
    },
    {
      "start": "2024-03-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 303.577537,
      "ebit": 45.3782,
      "operating_cost_ex_sbc": 233.770321,
      "sbc": 10.099066,
      "nonrecurring_gain": 2.96
    },
    {
      "start": "2024-06-01",
      "end": "2024-08-31",
      "fiscal_year": "2024",
      "revenue": 310.587684,
      "ebit": 48.180153,
      "operating_cost_ex_sbc": 238.041036,
      "sbc": 10.626757,
      "nonrecurring_gain": 6.874015
    }
  ],
  "opening_nwc": 303.483176,
  "opening_deferred": 0,
  "opening_ppe": 254.82,
  "opening_rou": 0,
  "opening_debt": 164.4,
  "opening_retained_earnings": 131.52,
  "contributed_capital": 320.58,
  "opening_cash": 82.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 120.7,
    "price0": 12.2298092583,
    "driver_add": [
      8.16,
      9.282,
      10.404,
      11.526
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.11570000000000001,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.1,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 90.42,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      20.55,
      0,
      0,
      0
    ],
    "debt_repayment": [
      8.22,
      16.44,
      24.660000000000004,
      32.88
    ],
    "beta_unlevered": 0.84,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "utilization": [
      0.74,
      0.758,
      0.776,
      0.794
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      53.7,
      57.7,
      61.7,
      65.7
    ],
    "intangible_rate": 0.16,
    "driver_rebase": 131.2009,
    "price_rebase": 12.60893
  },
  "bridge": {
    "cash": 82.2,
    "debt": 164.4,
    "investments": 12.33,
    "lease_liability": 0,
    "minority": 9.864,
    "valuation_cash_adjustment": 9.864,
    "shares": 128,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 12.8
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 338.664,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 320.58,
    "opening_cash": 82.2,
    "opening_operating_current_assets": 338.664,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 249.3,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "multi_method",
  "c_structure_definition": "多方法估值与反推",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge"
    ],
    "c": "multi_method"
  },
  "opening_nwc_last_fye": 303.483176,
  "opening_nwc_valuation_date": 277.014,
  "market": {
    "market_price": 32.11
  },
  "event_public_facts": {
    "type": "rebase",
    "description": "新增实际期间经营基数和单位收入，重定预测基期，原历史不变",
    "driver_rebase": 131.2009,
    "price_rebase": 12.60893
  },
  "event_type": "rebase"
}
```

</details>

##### D01_S2｜砾川数科估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题不只要一个目标价：需用 Gordon 与退出倍数两种方法分别估值，做反向推导，并给出估值区间。
公司财年截至每年 8 月 31 日，最近完整财年末为 `2024-08-31`，估值日 `2025-03-05` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
分别给出 Gordon 与退出倍数的终值、EV、股权价值和每股价值，不得加权成一个数。由 Gordon 终值反推隐含 EV/EBITDA，由退出倍数反推隐含 g，并用给定股价在工作簿内以公式迭代/求解隐含 WACC；Football Field 按给定折现率和增长区间。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 2 步修改：基期重定
新增实际期间经营基数和单位收入，重定预测基期，原历史不变。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-2.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### step-3

<details><summary>D01/step-3｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D01_S3",
  "seed": 412248,
  "candidate_index": 6,
  "family": "D",
  "step": 3,
  "company": "砾川数科",
  "dimension_selection": {
    "scenario": "区域低温加工",
    "difficulty": "L1: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "capacity",
    "valuation_mechanism": "exit",
    "accounting_basis": "SBC经营成本",
    "output_mode": "three_statements_dcf",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days"
  ],
  "selection_rationale": {
    "scenario": "区域低温加工要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "capacity",
    "unit": "千吨年产能",
    "price_unit": "百万元/千吨",
    "description": "区域低温加工"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-03-05",
  "last_fy_end": "2024-08-31",
  "horizon": 4,
  "history": [
    {
      "start": "2022-03-01",
      "end": "2022-05-31",
      "fiscal_year": "2022",
      "revenue": 247.496366,
      "ebit": 25.28879,
      "operating_cost_ex_sbc": 197.741294,
      "sbc": 5.877544,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-06-01",
      "end": "2022-08-31",
      "fiscal_year": "2022",
      "revenue": 254.506512,
      "ebit": 27.573806,
      "operating_cost_ex_sbc": 202.426078,
      "sbc": 6.405235,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2022-09-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 261.51666,
      "ebit": 29.92344,
      "operating_cost_ex_sbc": 207.059102,
      "sbc": 6.932925,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2022-12-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 268.526806,
      "ebit": 32.33769,
      "operating_cost_ex_sbc": 211.640368,
      "sbc": 7.460615,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2023-03-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 275.536952,
      "ebit": 34.816558,
      "operating_cost_ex_sbc": 216.169876,
      "sbc": 7.988305,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2023-06-01",
      "end": "2023-08-31",
      "fiscal_year": "2023",
      "revenue": 282.547099,
      "ebit": 37.360043,
      "operating_cost_ex_sbc": 220.647626,
      "sbc": 8.515996,
      "nonrecurring_gain": 1.85
    },
    {
      "start": "2023-09-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 289.557245,
      "ebit": 39.968145,
      "operating_cost_ex_sbc": 225.073615,
      "sbc": 9.043686,
      "nonrecurring_gain": 2.22
    },
    {
      "start": "2023-12-01",
      "end": "2024-02-29",
      "fiscal_year": "2024",
      "revenue": 296.567391,
      "ebit": 42.640864,
      "operating_cost_ex_sbc": 229.447848,
      "sbc": 9.571376,
      "nonrecurring_gain": 2.59
    },
    {
      "start": "2024-03-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 303.577537,
      "ebit": 45.3782,
      "operating_cost_ex_sbc": 233.770321,
      "sbc": 10.099066,
      "nonrecurring_gain": 2.96
    },
    {
      "start": "2024-06-01",
      "end": "2024-08-31",
      "fiscal_year": "2024",
      "revenue": 310.587684,
      "ebit": 48.180153,
      "operating_cost_ex_sbc": 238.041036,
      "sbc": 10.626757,
      "nonrecurring_gain": 6.874015
    }
  ],
  "opening_nwc": 303.483176,
  "opening_deferred": 0,
  "opening_ppe": 254.82,
  "opening_rou": 0,
  "opening_debt": 164.4,
  "opening_retained_earnings": 131.52,
  "contributed_capital": 320.58,
  "opening_cash": 82.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 120.7,
    "price0": 12.2298092583,
    "driver_add": [
      8.16,
      9.282,
      10.404,
      11.526
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.11570000000000001,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.1,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 90.42,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      92,
      0,
      15,
      0
    ],
    "debt_repayment": [
      0,
      14,
      22,
      28
    ],
    "beta_unlevered": 0.84,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "utilization": [
      0.74,
      0.758,
      0.776,
      0.794
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      53.7,
      57.7,
      61.7,
      65.7
    ],
    "intangible_rate": 0.16,
    "driver_rebase": 131.2009,
    "price_rebase": 12.60893,
    "extra_capex": [
      66,
      24,
      0,
      0
    ]
  },
  "bridge": {
    "cash": 82.2,
    "debt": 164.4,
    "investments": 12.33,
    "lease_liability": 0,
    "minority": 9.864,
    "valuation_cash_adjustment": 9.864,
    "shares": 128,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 12.8
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 338.664,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 320.58,
    "opening_cash": 82.2,
    "opening_operating_current_assets": 338.664,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 249.3,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "multi_method",
  "c_structure_definition": "多方法估值与反推",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge"
    ],
    "c": "multi_method"
  },
  "opening_nwc_last_fye": 303.483176,
  "opening_nwc_valuation_date": 277.014,
  "market": {
    "market_price": 32.11
  },
  "event_public_facts": {
    "type": "financing_and_capex_rearrangement",
    "description": "扩产支出重排并新增/偿还借款；固定资产和债务滚动同步更新，FCFF 与利息分开",
    "extra_capex": [
      66,
      24,
      0,
      0
    ]
  },
  "event_type": "financing_and_capex_rearrangement"
}
```

</details>

##### D01_S3｜砾川数科估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题不只要一个目标价：需用 Gordon 与退出倍数两种方法分别估值，做反向推导，并给出估值区间。
公司财年截至每年 8 月 31 日，最近完整财年末为 `2024-08-31`，估值日 `2025-03-05` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
分别给出 Gordon 与退出倍数的终值、EV、股权价值和每股价值，不得加权成一个数。由 Gordon 终值反推隐含 EV/EBITDA，由退出倍数反推隐含 g，并用给定股价在工作簿内以公式迭代/求解隐含 WACC；Football Field 按给定折现率和增长区间。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 3 步修改：扩产与融资重排
扩产支出重排并新增/偿还借款；固定资产和债务滚动同步更新，FCFF 与利息分开。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-3.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### step-4

<details><summary>D01/step-4｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D01_S4",
  "seed": 412248,
  "candidate_index": 6,
  "family": "D",
  "step": 4,
  "company": "砾川数科",
  "dimension_selection": {
    "scenario": "区域低温加工",
    "difficulty": "L1: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "capacity",
    "valuation_mechanism": "exit",
    "accounting_basis": "SBC经营成本",
    "output_mode": "three_statements_dcf",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days"
  ],
  "selection_rationale": {
    "scenario": "区域低温加工要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "semiannual",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "capacity",
    "unit": "千吨年产能",
    "price_unit": "百万元/千吨",
    "description": "区域低温加工"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-03-05",
  "last_fy_end": "2024-08-31",
  "horizon": 4,
  "history": [
    {
      "start": "2022-03-01",
      "end": "2022-05-31",
      "fiscal_year": "2022",
      "revenue": 247.496366,
      "ebit": 25.28879,
      "operating_cost_ex_sbc": 197.741294,
      "sbc": 5.877544,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-06-01",
      "end": "2022-08-31",
      "fiscal_year": "2022",
      "revenue": 254.506512,
      "ebit": 27.573806,
      "operating_cost_ex_sbc": 202.426078,
      "sbc": 6.405235,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2022-09-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 261.51666,
      "ebit": 29.92344,
      "operating_cost_ex_sbc": 207.059102,
      "sbc": 6.932925,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2022-12-01",
      "end": "2023-02-28",
      "fiscal_year": "2023",
      "revenue": 268.526806,
      "ebit": 32.33769,
      "operating_cost_ex_sbc": 211.640368,
      "sbc": 7.460615,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2023-03-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 275.536952,
      "ebit": 34.816558,
      "operating_cost_ex_sbc": 216.169876,
      "sbc": 7.988305,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2023-06-01",
      "end": "2023-08-31",
      "fiscal_year": "2023",
      "revenue": 282.547099,
      "ebit": 37.360043,
      "operating_cost_ex_sbc": 220.647626,
      "sbc": 8.515996,
      "nonrecurring_gain": 1.85
    },
    {
      "start": "2023-09-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 289.557245,
      "ebit": 39.968145,
      "operating_cost_ex_sbc": 225.073615,
      "sbc": 9.043686,
      "nonrecurring_gain": 2.22
    },
    {
      "start": "2023-12-01",
      "end": "2024-02-29",
      "fiscal_year": "2024",
      "revenue": 296.567391,
      "ebit": 42.640864,
      "operating_cost_ex_sbc": 229.447848,
      "sbc": 9.571376,
      "nonrecurring_gain": 2.59
    },
    {
      "start": "2024-03-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 303.577537,
      "ebit": 45.3782,
      "operating_cost_ex_sbc": 233.770321,
      "sbc": 10.099066,
      "nonrecurring_gain": 2.96
    },
    {
      "start": "2024-06-01",
      "end": "2024-08-31",
      "fiscal_year": "2024",
      "revenue": 310.587684,
      "ebit": 48.180153,
      "operating_cost_ex_sbc": 238.041036,
      "sbc": 10.626757,
      "nonrecurring_gain": 6.874015
    }
  ],
  "opening_nwc": 303.483176,
  "opening_deferred": 0,
  "opening_ppe": 254.82,
  "opening_rou": 0,
  "opening_debt": 164.4,
  "opening_retained_earnings": 131.52,
  "contributed_capital": 320.58,
  "opening_cash": 82.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 120.7,
    "price0": 12.2298092583,
    "driver_add": [
      8.16,
      9.282,
      10.404,
      11.526
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.11570000000000001,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7075,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 90.42,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      92,
      0,
      15,
      0
    ],
    "debt_repayment": [
      0,
      14,
      22,
      28
    ],
    "beta_unlevered": 0.84,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "utilization": [
      0.74,
      0.758,
      0.776,
      0.794
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      53.7,
      57.7,
      61.7,
      65.7
    ],
    "intangible_rate": 0.16,
    "driver_rebase": 131.2009,
    "price_rebase": 12.60893,
    "extra_capex": [
      66,
      24,
      0,
      0
    ]
  },
  "bridge": {
    "cash": 82.2,
    "debt": 164.4,
    "investments": 12.33,
    "lease_liability": 0,
    "minority": 9.864,
    "valuation_cash_adjustment": 9.864,
    "shares": 128,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 12.8
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 338.664,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 320.58,
    "opening_cash": 82.2,
    "opening_operating_current_assets": 338.664,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 249.3,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "multi_method",
  "c_structure_definition": "多方法估值与反推",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge"
    ],
    "c": "multi_method"
  },
  "opening_nwc_last_fye": 303.483176,
  "opening_nwc_valuation_date": 277.014,
  "market": {
    "market_price": 32.11
  },
  "event_public_facts": {
    "type": "terminal_method_change",
    "description": "退出估值改为新的可比交易倍数，保留 Gordon 路径用于对照并更新反推",
    "exit_multiple": 8.7075
  },
  "event_type": "terminal_method_change"
}
```

</details>

##### D01_S4｜砾川数科估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题不只要一个目标价：需用 Gordon 与退出倍数两种方法分别估值，做反向推导，并给出估值区间。
公司财年截至每年 8 月 31 日，最近完整财年末为 `2024-08-31`，估值日 `2025-03-05` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据按半年度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
分别给出 Gordon 与退出倍数的终值、EV、股权价值和每股价值，不得加权成一个数。由 Gordon 终值反推隐含 EV/EBITDA，由退出倍数反推隐含 g，并用给定股价在工作簿内以公式迭代/求解隐含 WACC；Football Field 按给定折现率和增长区间。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 4 步修改：终值方法变更
退出估值改为新的可比交易倍数，保留 Gordon 路径用于对照并更新反推。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-4.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### D01 选用的 rubric（68 条，权重合计 180；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 1 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键唯一数值公式 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | output、memo及各步快照须存在 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需Inputs页及Results开头页 |
| 01-HISTORY | 多步状态与业务重构 | 原始历史事实未被覆盖或删除 | rule | 主需 | 题面要求保留历史事实 |
| 08-RESTATE | 多步状态与业务重构 | 事件后的 FCFF 与股权桥使用更新后的依赖 | rule | 主需 | 事件后FCFF与股权桥需更新 |
| D-FINAL-VALUES | 多步状态与业务重构 | 最后一步工作簿的全部输出键与最终独立真值一致 | rule | 主需 | 最终输出键需与真值一致 |
| D-FINAL-LIVE | 多步状态与业务重构 | 最后一步结果仍为活公式，隐藏扰动可传导 | rule | 主需 | 要求活公式且扰动可传导 |
| D-STEP-SNAPSHOT | 多步状态与业务重构 | 每一步都保存了独立快照 | rule | 主需 | 要求每步保存独立快照 |
| D-STEP-VALUES | 多步状态与业务重构 | 每一步快照的输出与该步独立真值一致 | rule | 主需 | 每步快照输出需正确 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 季度历史需按非自然财年聚合 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 非经常收益不入规范化EBIT |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作为经营成本 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 产能存量含新增与流失 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均产能乘价格及残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期差额及符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用最近财年末余额 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用营运资本天数法 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 有借款偿还利息计划 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | 给定期初NOL余额 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 题面含新增无形资产 |
| 04-BALANCE | 三表勾稽 | 每个预测期资产等于负债加权益 | rule | 主需 | spec要求三表模型 |
| 04-CASH | 三表勾稽 | 资产负债表现金与现金流量表期末现金一致 | rule | 主需 | 题面要求现金从期初滚动 |
| 04-RE | 三表勾稽 | 留存收益由净利润滚动且无不透明平衡项 | rule | 主需 | 三表需留存收益滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用rolling_assets模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为估值核心 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 题面要求实际天数年中折现 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 题面含库存股期权与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 需分别给出每股价值 |
| 05-SENS | DCF与估值桥 | 敏感性单元格使用各自行列假设而经营预测不变 | rule | 次需 | Football Field按折现率增长区间 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题面含新增无形资产 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅含估值日后活动 |
| C-MULTI-SPLIT | DCF与估值桥 | Gordon 与退出倍数估值分别给出，不只输出加权结果 | rule | 主需 | 题面要求两法分别给出不加权 |
| C-IMPLIED-MULT | DCF与估值桥 | 由 Gordon 终值反推的隐含 EV/EBITDA 计算正确 | rule | 主需 | 要求Gordon反推隐含倍数 |
| C-IMPLIED-G | DCF与估值桥 | 由退出倍数终值反推的隐含永续增长率计算正确 | rule | 主需 | 要求退出倍数反推隐含g |
| C-REVERSE | DCF与估值桥 | 由给定市场价格反推的隐含 WACC 或隐含增长假设正确，且以公式或求解过程得出 | rule | 主需 | 要求股价公式求解隐含WACC |
| C-RANGE | DCF与估值桥 | 估值区间的上下界分别来自题面指定的方法和假设范围 | rule | 次需 | Football Field按给定区间 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果键须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 重算须与真值一致 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 扰动需假设不硬编码 |
| X-FM-003 | 公式与模型工程 | 同一业务或估值假设仅有一个权威输入单元格，每个使用该假设的下游公式均可追溯至该单元格。 | rule | 主需 | 假设须单一来源可追溯 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | 残期加多期须列对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 隐含WACC求解防循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM推导 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 季度/财年/LTM不得混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加4期完整年度 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 须保留历史事实 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | Gordon与退出倍数共用显性期现值 |
| X-IC-002 | 公式与模型工程 | 每条敏感性轴的完整值序列与题面指定的起点、终点及步长完全一致。 | rule | 主需 | Football Field区间按给定值 |
| X-IC-001 | 公式与模型工程 | 敏感性表中与基准行列假设相交的单元格，其值与模型相同口径基准输出的相对差异不超过题面容差；题面未给容差时为 0.1%。 | rule | 主需 | 敏感性基准格应等于基准输出 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史存在非经常收益需剔除 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数年中折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | DCF需拆分FCFF各构成 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon与退出倍数终值 |
| 08-OLD | 多步状态与业务重构 | 后续工作簿保留事件前原始输入与状态 | rule | 主需 | 程序强制必选项 |

### D02（D）

<details><summary>D02｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D02",
  "seed": 413225,
  "candidate_index": 13,
  "family": "D",
  "company": "星榫食品",
  "dimension_selection": {
    "scenario": "远程运维席位",
    "difficulty": "L2: 依赖深度6，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "subscription",
    "valuation_mechanism": "gordon",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "debt_schedule_dcf",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets",
    "scenario"
  ],
  "selection_rationale": {
    "scenario": "远程运维席位要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "subscription",
    "unit": "千席位",
    "price_unit": "百万元/千席位/年",
    "description": "远程运维席位"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-11-16",
  "last_fy_end": "2025-05-31",
  "horizon": 5,
  "history": [
    {
      "start": "2022-06-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 585.353261,
      "ebit": 59.777883,
      "operating_cost_ex_sbc": 467.107069,
      "sbc": 13.884012,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-12-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 601.42786,
      "ebit": 64.674617,
      "operating_cost_ex_sbc": 477.669506,
      "sbc": 14.62651,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2023-06-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 617.50246,
      "ebit": 69.724094,
      "operating_cost_ex_sbc": 488.109678,
      "sbc": 15.369008,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2023-12-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 633.57706,
      "ebit": 74.926313,
      "operating_cost_ex_sbc": 498.427585,
      "sbc": 16.111506,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2024-06-01",
      "end": "2024-11-30",
      "fiscal_year": "2025",
      "revenue": 649.65166,
      "ebit": 80.281275,
      "operating_cost_ex_sbc": 508.623229,
      "sbc": 16.854003,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2024-12-01",
      "end": "2025-05-31",
      "fiscal_year": "2025",
      "revenue": 665.726259,
      "ebit": 85.788979,
      "operating_cost_ex_sbc": 518.696607,
      "sbc": 17.596501,
      "nonrecurring_gain": 9.498034
    }
  ],
  "opening_nwc": 311.388,
  "opening_deferred": 0,
  "opening_ppe": 286.44,
  "opening_rou": 0,
  "opening_debt": 184.8,
  "opening_retained_earnings": 147.84,
  "contributed_capital": 360.36,
  "opening_cash": 92.4,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 174.4,
    "price0": 7.661780968,
    "driver_add": [
      10.96,
      12.467,
      13.974,
      15.481,
      16.988
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.105,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 101.64,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      23.1,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      9.24,
      18.48,
      27.72,
      36.96,
      46.2
    ],
    "beta_unlevered": 0.8,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      55.4,
      59.4,
      63.4,
      67.4,
      71.4
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 92.4,
    "debt": 184.8,
    "investments": 13.86,
    "lease_liability": 0,
    "minority": 11.088,
    "valuation_cash_adjustment": 11.088,
    "shares": 149,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 14.9
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 311.388,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 360.36,
    "opening_cash": 92.4,
    "opening_operating_current_assets": 311.388,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 256.6,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge",
    "dual_terminal"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_terminal": "Gordon、退出倍数、双终值加权"
  },
  "c_structure": "scenario_operating_model",
  "c_structure_definition": "情景驱动 Operating Model",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "dual_terminal"
    ],
    "c": "scenario_operating_model"
  },
  "market": {
    "market_price": 33.02
  },
  "event_public_facts": {
    "type": "baseline",
    "description": "建立基座模型，保存第 1 步快照。"
  },
  "event_type": "baseline",
  "steps": [
    {
      "step": 1,
      "event_type": "baseline",
      "task_id": "D02"
    },
    {
      "step": 2,
      "event_type": "scenario_switch",
      "task_id": "D02_S2"
    },
    {
      "step": 3,
      "event_type": "financing_and_capex_rearrangement",
      "task_id": "D02_S3"
    },
    {
      "step": 4,
      "event_type": "terminal_method_change",
      "task_id": "D02_S4"
    }
  ],
  "independent_from_BC": true
}
```

</details>

##### D02｜星榫食品估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

管理层给出 Base、Bull、Bear 三套经营方案，需要搭建可一键切换情景的经营模型并完成 DCF。
公司财年截至每年 5 月 31 日，最近完整财年末为 `2025-05-31`，估值日 `2025-11-16` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
终值的 Gordon 永续增长法与退出倍数法都要单独列示；按输入中的 Gordon 权重（本题为 100%）计入估值。
设置 `Cases` 页，唯一选择格链接 `a.scenario`（1=Base、2=Bull、3=Bear）。需求、利润率、再投资、FCFF、终值与每股价值必须随同一开关联动；另分别保留三情景独立输出，不能只交一张敏感性表。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

每步完成后将对应工作簿保存为 `/app/snapshots/step-N.xlsx`；不得覆盖前步快照。

本题包含连续结构事件；按 `steps/step-N/instruction.md` 顺序执行。

#### step-1

<details><summary>D02/step-1｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D02",
  "seed": 413225,
  "candidate_index": 13,
  "family": "D",
  "step": 1,
  "company": "星榫食品",
  "dimension_selection": {
    "scenario": "远程运维席位",
    "difficulty": "L2: 依赖深度6，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "subscription",
    "valuation_mechanism": "gordon",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "debt_schedule_dcf",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets",
    "scenario"
  ],
  "selection_rationale": {
    "scenario": "远程运维席位要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "subscription",
    "unit": "千席位",
    "price_unit": "百万元/千席位/年",
    "description": "远程运维席位"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-11-16",
  "last_fy_end": "2025-05-31",
  "horizon": 5,
  "history": [
    {
      "start": "2022-06-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 585.353261,
      "ebit": 59.777883,
      "operating_cost_ex_sbc": 467.107069,
      "sbc": 13.884012,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-12-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 601.42786,
      "ebit": 64.674617,
      "operating_cost_ex_sbc": 477.669506,
      "sbc": 14.62651,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2023-06-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 617.50246,
      "ebit": 69.724094,
      "operating_cost_ex_sbc": 488.109678,
      "sbc": 15.369008,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2023-12-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 633.57706,
      "ebit": 74.926313,
      "operating_cost_ex_sbc": 498.427585,
      "sbc": 16.111506,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2024-06-01",
      "end": "2024-11-30",
      "fiscal_year": "2025",
      "revenue": 649.65166,
      "ebit": 80.281275,
      "operating_cost_ex_sbc": 508.623229,
      "sbc": 16.854003,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2024-12-01",
      "end": "2025-05-31",
      "fiscal_year": "2025",
      "revenue": 665.726259,
      "ebit": 85.788979,
      "operating_cost_ex_sbc": 518.696607,
      "sbc": 17.596501,
      "nonrecurring_gain": 9.498034
    }
  ],
  "opening_nwc": 311.388,
  "opening_deferred": 0,
  "opening_ppe": 286.44,
  "opening_rou": 0,
  "opening_debt": 184.8,
  "opening_retained_earnings": 147.84,
  "contributed_capital": 360.36,
  "opening_cash": 92.4,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 174.4,
    "price0": 7.661780968,
    "driver_add": [
      10.96,
      12.467,
      13.974,
      15.481,
      16.988
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.105,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 101.64,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      23.1,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      9.24,
      18.48,
      27.72,
      36.96,
      46.2
    ],
    "beta_unlevered": 0.8,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      55.4,
      59.4,
      63.4,
      67.4,
      71.4
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 92.4,
    "debt": 184.8,
    "investments": 13.86,
    "lease_liability": 0,
    "minority": 11.088,
    "valuation_cash_adjustment": 11.088,
    "shares": 149,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 14.9
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 311.388,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 360.36,
    "opening_cash": 92.4,
    "opening_operating_current_assets": 311.388,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 256.6,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge",
    "dual_terminal"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_terminal": "Gordon、退出倍数、双终值加权"
  },
  "c_structure": "scenario_operating_model",
  "c_structure_definition": "情景驱动 Operating Model",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "dual_terminal"
    ],
    "c": "scenario_operating_model"
  },
  "market": {
    "market_price": 33.02
  },
  "event_public_facts": {
    "type": "baseline",
    "description": "建立基座模型，保存第 1 步快照。"
  },
  "event_type": "baseline"
}
```

</details>

##### D02｜星榫食品估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

管理层给出 Base、Bull、Bear 三套经营方案，需要搭建可一键切换情景的经营模型并完成 DCF。
公司财年截至每年 5 月 31 日，最近完整财年末为 `2025-05-31`，估值日 `2025-11-16` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
终值的 Gordon 永续增长法与退出倍数法都要单独列示；按输入中的 Gordon 权重（本题为 100%）计入估值。
设置 `Cases` 页，唯一选择格链接 `a.scenario`（1=Base、2=Bull、3=Bear）。需求、利润率、再投资、FCFF、终值与每股价值必须随同一开关联动；另分别保留三情景独立输出，不能只交一张敏感性表。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

每步完成后将对应工作簿保存为 `/app/snapshots/step-N.xlsx`；不得覆盖前步快照。

#### step-2

<details><summary>D02/step-2｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D02_S2",
  "seed": 413225,
  "candidate_index": 13,
  "family": "D",
  "step": 2,
  "company": "星榫食品",
  "dimension_selection": {
    "scenario": "远程运维席位",
    "difficulty": "L2: 依赖深度6，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "subscription",
    "valuation_mechanism": "gordon",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "debt_schedule_dcf",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets",
    "scenario"
  ],
  "selection_rationale": {
    "scenario": "远程运维席位要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "subscription",
    "unit": "千席位",
    "price_unit": "百万元/千席位/年",
    "description": "远程运维席位"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-11-16",
  "last_fy_end": "2025-05-31",
  "horizon": 5,
  "history": [
    {
      "start": "2022-06-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 585.353261,
      "ebit": 59.777883,
      "operating_cost_ex_sbc": 467.107069,
      "sbc": 13.884012,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-12-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 601.42786,
      "ebit": 64.674617,
      "operating_cost_ex_sbc": 477.669506,
      "sbc": 14.62651,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2023-06-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 617.50246,
      "ebit": 69.724094,
      "operating_cost_ex_sbc": 488.109678,
      "sbc": 15.369008,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2023-12-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 633.57706,
      "ebit": 74.926313,
      "operating_cost_ex_sbc": 498.427585,
      "sbc": 16.111506,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2024-06-01",
      "end": "2024-11-30",
      "fiscal_year": "2025",
      "revenue": 649.65166,
      "ebit": 80.281275,
      "operating_cost_ex_sbc": 508.623229,
      "sbc": 16.854003,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2024-12-01",
      "end": "2025-05-31",
      "fiscal_year": "2025",
      "revenue": 665.726259,
      "ebit": 85.788979,
      "operating_cost_ex_sbc": 518.696607,
      "sbc": 17.596501,
      "nonrecurring_gain": 9.498034
    }
  ],
  "opening_nwc": 311.388,
  "opening_deferred": 0,
  "opening_ppe": 286.44,
  "opening_rou": 0,
  "opening_debt": 184.8,
  "opening_retained_earnings": 147.84,
  "contributed_capital": 360.36,
  "opening_cash": 92.4,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 174.4,
    "price0": 7.661780968,
    "driver_add": [
      10.96,
      12.467,
      13.974,
      15.481,
      16.988
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.105,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 101.64,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      23.1,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      9.24,
      18.48,
      27.72,
      36.96,
      46.2
    ],
    "beta_unlevered": 0.8,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 2,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      55.4,
      59.4,
      63.4,
      67.4,
      71.4
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 92.4,
    "debt": 184.8,
    "investments": 13.86,
    "lease_liability": 0,
    "minority": 11.088,
    "valuation_cash_adjustment": 11.088,
    "shares": 149,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 14.9
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 311.388,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 360.36,
    "opening_cash": 92.4,
    "opening_operating_current_assets": 311.388,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 256.6,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge",
    "dual_terminal"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_terminal": "Gordon、退出倍数、双终值加权"
  },
  "c_structure": "scenario_operating_model",
  "c_structure_definition": "情景驱动 Operating Model",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "dual_terminal"
    ],
    "c": "scenario_operating_model"
  },
  "market": {
    "market_price": 33.02
  },
  "event_public_facts": {
    "type": "scenario_switch",
    "description": "董事会批准 Bull 经营方案：需求、利润率、再投资、FCFF、终值和每股价值由同一开关切换",
    "scenario": 2
  },
  "event_type": "scenario_switch"
}
```

</details>

##### D02_S2｜星榫食品估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

管理层给出 Base、Bull、Bear 三套经营方案，需要搭建可一键切换情景的经营模型并完成 DCF。
公司财年截至每年 5 月 31 日，最近完整财年末为 `2025-05-31`，估值日 `2025-11-16` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
终值的 Gordon 永续增长法与退出倍数法都要单独列示；按输入中的 Gordon 权重（本题为 100%）计入估值。
设置 `Cases` 页，唯一选择格链接 `a.scenario`（1=Base、2=Bull、3=Bear）。需求、利润率、再投资、FCFF、终值与每股价值必须随同一开关联动；另分别保留三情景独立输出，不能只交一张敏感性表。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 2 步修改：经营情景切换
董事会批准 Bull 经营方案：需求、利润率、再投资、FCFF、终值和每股价值由同一开关切换。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-2.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### step-3

<details><summary>D02/step-3｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D02_S3",
  "seed": 413225,
  "candidate_index": 13,
  "family": "D",
  "step": 3,
  "company": "星榫食品",
  "dimension_selection": {
    "scenario": "远程运维席位",
    "difficulty": "L2: 依赖深度6，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "subscription",
    "valuation_mechanism": "gordon",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "debt_schedule_dcf",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets",
    "scenario"
  ],
  "selection_rationale": {
    "scenario": "远程运维席位要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "subscription",
    "unit": "千席位",
    "price_unit": "百万元/千席位/年",
    "description": "远程运维席位"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-11-16",
  "last_fy_end": "2025-05-31",
  "horizon": 5,
  "history": [
    {
      "start": "2022-06-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 585.353261,
      "ebit": 59.777883,
      "operating_cost_ex_sbc": 467.107069,
      "sbc": 13.884012,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-12-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 601.42786,
      "ebit": 64.674617,
      "operating_cost_ex_sbc": 477.669506,
      "sbc": 14.62651,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2023-06-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 617.50246,
      "ebit": 69.724094,
      "operating_cost_ex_sbc": 488.109678,
      "sbc": 15.369008,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2023-12-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 633.57706,
      "ebit": 74.926313,
      "operating_cost_ex_sbc": 498.427585,
      "sbc": 16.111506,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2024-06-01",
      "end": "2024-11-30",
      "fiscal_year": "2025",
      "revenue": 649.65166,
      "ebit": 80.281275,
      "operating_cost_ex_sbc": 508.623229,
      "sbc": 16.854003,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2024-12-01",
      "end": "2025-05-31",
      "fiscal_year": "2025",
      "revenue": 665.726259,
      "ebit": 85.788979,
      "operating_cost_ex_sbc": 518.696607,
      "sbc": 17.596501,
      "nonrecurring_gain": 9.498034
    }
  ],
  "opening_nwc": 311.388,
  "opening_deferred": 0,
  "opening_ppe": 286.44,
  "opening_rou": 0,
  "opening_debt": 184.8,
  "opening_retained_earnings": 147.84,
  "contributed_capital": 360.36,
  "opening_cash": 92.4,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 174.4,
    "price0": 7.661780968,
    "driver_add": [
      10.96,
      12.467,
      13.974,
      15.481,
      16.988
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.105,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 101.64,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      92,
      0,
      15,
      0,
      0
    ],
    "debt_repayment": [
      0,
      14,
      22,
      28,
      34
    ],
    "beta_unlevered": 0.8,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 2,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      55.4,
      59.4,
      63.4,
      67.4,
      71.4
    ],
    "intangible_rate": 0.16,
    "extra_capex": [
      66,
      24,
      0,
      0,
      0
    ]
  },
  "bridge": {
    "cash": 92.4,
    "debt": 184.8,
    "investments": 13.86,
    "lease_liability": 0,
    "minority": 11.088,
    "valuation_cash_adjustment": 11.088,
    "shares": 149,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 14.9
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 311.388,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 360.36,
    "opening_cash": 92.4,
    "opening_operating_current_assets": 311.388,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 256.6,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge",
    "dual_terminal"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_terminal": "Gordon、退出倍数、双终值加权"
  },
  "c_structure": "scenario_operating_model",
  "c_structure_definition": "情景驱动 Operating Model",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "dual_terminal"
    ],
    "c": "scenario_operating_model"
  },
  "market": {
    "market_price": 33.02
  },
  "event_public_facts": {
    "type": "financing_and_capex_rearrangement",
    "description": "扩产支出重排并新增/偿还借款；固定资产和债务滚动同步更新，FCFF 与利息分开",
    "extra_capex": [
      66,
      24,
      0,
      0,
      0
    ]
  },
  "event_type": "financing_and_capex_rearrangement"
}
```

</details>

##### D02_S3｜星榫食品估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

管理层给出 Base、Bull、Bear 三套经营方案，需要搭建可一键切换情景的经营模型并完成 DCF。
公司财年截至每年 5 月 31 日，最近完整财年末为 `2025-05-31`，估值日 `2025-11-16` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
终值的 Gordon 永续增长法与退出倍数法都要单独列示；按输入中的 Gordon 权重（本题为 100%）计入估值。
设置 `Cases` 页，唯一选择格链接 `a.scenario`（1=Base、2=Bull、3=Bear）。需求、利润率、再投资、FCFF、终值与每股价值必须随同一开关联动；另分别保留三情景独立输出，不能只交一张敏感性表。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 3 步修改：扩产与融资重排
扩产支出重排并新增/偿还借款；固定资产和债务滚动同步更新，FCFF 与利息分开。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-3.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### step-4

<details><summary>D02/step-4｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D02_S4",
  "seed": 413225,
  "candidate_index": 13,
  "family": "D",
  "step": 4,
  "company": "星榫食品",
  "dimension_selection": {
    "scenario": "远程运维席位",
    "difficulty": "L2: 依赖深度6，显式5期",
    "time_axis": "非自然财年+semiannual历史+实际天数残期",
    "business_driver": "subscription",
    "valuation_mechanism": "gordon",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "debt_schedule_dcf",
    "output_template": "free_layout",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets"
  ],
  "selection_rationale": {
    "scenario": "远程运维席位要求独立的单位与价格口径",
    "time_axis": "6个半年披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "subscription",
    "unit": "千席位",
    "price_unit": "百万元/千席位/年",
    "description": "远程运维席位"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-11-16",
  "last_fy_end": "2025-05-31",
  "horizon": 5,
  "history": [
    {
      "start": "2022-06-01",
      "end": "2022-11-30",
      "fiscal_year": "2023",
      "revenue": 585.353261,
      "ebit": 59.777883,
      "operating_cost_ex_sbc": 467.107069,
      "sbc": 13.884012,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-12-01",
      "end": "2023-05-31",
      "fiscal_year": "2023",
      "revenue": 601.42786,
      "ebit": 64.674617,
      "operating_cost_ex_sbc": 477.669506,
      "sbc": 14.62651,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2023-06-01",
      "end": "2023-11-30",
      "fiscal_year": "2024",
      "revenue": 617.50246,
      "ebit": 69.724094,
      "operating_cost_ex_sbc": 488.109678,
      "sbc": 15.369008,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2023-12-01",
      "end": "2024-05-31",
      "fiscal_year": "2024",
      "revenue": 633.57706,
      "ebit": 74.926313,
      "operating_cost_ex_sbc": 498.427585,
      "sbc": 16.111506,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2024-06-01",
      "end": "2024-11-30",
      "fiscal_year": "2025",
      "revenue": 649.65166,
      "ebit": 80.281275,
      "operating_cost_ex_sbc": 508.623229,
      "sbc": 16.854003,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2024-12-01",
      "end": "2025-05-31",
      "fiscal_year": "2025",
      "revenue": 665.726259,
      "ebit": 85.788979,
      "operating_cost_ex_sbc": 518.696607,
      "sbc": 17.596501,
      "nonrecurring_gain": 9.498034
    }
  ],
  "opening_nwc": 311.388,
  "opening_deferred": 0,
  "opening_ppe": 286.44,
  "opening_rou": 0,
  "opening_debt": 184.8,
  "opening_retained_earnings": 147.84,
  "contributed_capital": 360.36,
  "opening_cash": 92.4,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 185.736,
    "price0": 7.4702364438,
    "driver_add": [
      10.96,
      12.467,
      13.974,
      15.481,
      16.988
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186
    ],
    "tax": 0.235,
    "wacc": 0.105,
    "g": 0.023,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47
    ],
    "nol0": 101.64,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      92,
      0,
      15,
      0,
      0
    ],
    "debt_repayment": [
      0,
      14,
      22,
      28,
      34
    ],
    "beta_unlevered": 0.8,
    "target_de": 0.30000000000000004,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      55.4,
      59.4,
      63.4,
      67.4,
      71.4
    ],
    "intangible_rate": 0.16,
    "extra_capex": [
      66,
      24,
      0,
      0,
      0
    ]
  },
  "bridge": {
    "cash": 92.4,
    "debt": 184.8,
    "investments": 13.86,
    "lease_liability": 0,
    "minority": 11.088,
    "valuation_cash_adjustment": 11.088,
    "shares": 149,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 14.9
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 311.388,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 360.36,
    "opening_cash": 92.4,
    "opening_operating_current_assets": 311.388,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 256.6,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "multi_method",
  "c_structure_definition": "情景驱动 Operating Model",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge",
      "dual_terminal"
    ],
    "c": "scenario_operating_model"
  },
  "market": {
    "market_price": 33.02
  },
  "event_public_facts": {
    "type": "terminal_method_change",
    "description": "不再使用情景加权终值；分别输出 Gordon 与退出估值，反推隐含倍数、g 和市场隐含 WACC"
  },
  "event_type": "terminal_method_change"
}
```

</details>

##### D02_S4｜星榫食品估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

本题不只要一个目标价：需用 Gordon 与退出倍数两种方法分别估值，做反向推导，并给出估值区间。
公司财年截至每年 5 月 31 日，最近完整财年末为 `2025-05-31`，估值日 `2025-11-16` 落在财年中间。预测共 5 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
分别给出 Gordon 与退出倍数的终值、EV、股权价值和每股价值，不得加权成一个数。由 Gordon 终值反推隐含 EV/EBITDA，由退出倍数反推隐含 g，并用给定股价在工作簿内以公式迭代/求解隐含 WACC；Football Field 按给定折现率和增长区间。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 4 步修改：终值方法变更
不再使用情景加权终值；分别输出 Gordon 与退出估值，反推隐含倍数、g 和市场隐含 WACC。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-4.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### D02 选用的 rubric（56 条，权重合计 148；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 1 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读取output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | Results页输出键唯一且为数值 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 指定output、memo及快照文件 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 需Inputs、Cases、Results页 |
| 01-HISTORY | 多步状态与业务重构 | 原始历史事实未被覆盖或删除 | rule | 主需 | 题面要求保留历史事实 |
| D-FINAL-VALUES | 多步状态与业务重构 | 最后一步工作簿的全部输出键与最终独立真值一致 | rule | 主需 | 最终输出键需与真值一致 |
| D-FINAL-LIVE | 多步状态与业务重构 | 最后一步结果仍为活公式，隐藏扰动可传导 | rule | 主需 | 要求活公式且隐藏扰动可传导 |
| D-STEP-SNAPSHOT | 多步状态与业务重构 | 每一步都保存了独立快照 | rule | 主需 | 要求每步独立保存快照 |
| D-STEP-VALUES | 多步状态与业务重构 | 每一步快照的输出与该步独立真值一致 | rule | 主需 | 每步快照结果需正确 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史需聚合完整财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作为经营成本 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 订阅席位含新增与流失 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均席位×单价×残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期NWC差额及符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用估值日余额 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用营运资本天数模块 |
| 03-DEBT | 经营预测 | 借款、偿还、利息和期末债务连续滚动 | rule | 主需 | 债务计划表输出模式 |
| 03-NOL | 经营预测 | NOL 使用不得超过正 EBIT 或可用余额 | rule | 次需 | NOL抵扣约束 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 新增无形资产独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用rolling_assets模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为题面约束 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数期末折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | B项要求双终值加权 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 股权桥含各项调整 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 期权与RSU稀释 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值输出 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 含新增无形资产 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 估值日在财年中间 |
| C-CASE-SWITCH | DCF与估值桥 | 单一情景开关切换后收入、利润率、再投资、FCFF、终值和每股价值同时改变 | rule | 主需 | 题面要求单开关全链联动 |
| C-CASE-ISOLATE | DCF与估值桥 | 每个情景的输出值与独立真值一致，情景之间不相互覆盖 | rule | 次需 | 要求三情景独立输出 |
| C-MULTI-SPLIT | DCF与估值桥 | Gordon 与退出倍数估值分别给出，不只输出加权结果 | rule | 主需 | B项列Gordon与退出倍数 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 重算对比独立真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示两组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示两组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页自由布局 |
| X-FM-003 | 公式与模型工程 | 同一业务或估值假设仅有一个权威输入单元格，每个使用该假设的下游公式均可追溯至该单元格。 | rule | 主需 | 情景唯一选择格驱动全链 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面明确要求memo含驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型，需期间标签 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM须正确推导 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加5期预测序列 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径须一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 原始披露期不得改写 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | Gordon与退出倍数双终值共用显性期现值 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史含非经常收益需规范化 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF各组成需可追溯 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值引用可见单元格 |
| 08-OLD | 多步状态与业务重构 | 后续工作簿保留事件前原始输入与状态 | rule | 主需 | 程序强制必选项 |

### D03（D）

<details><summary>D03｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D03",
  "seed": 414202,
  "candidate_index": 20,
  "family": "D",
  "company": "衡浦组合",
  "dimension_selection": {
    "scenario": "精密连接组件",
    "difficulty": "L3: 依赖深度7，显式6期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "volume_price",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "SBC经营成本",
    "output_mode": "segment_dcf",
    "output_template": "mixed",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets"
  ],
  "selection_rationale": {
    "scenario": "精密连接组件要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "mixed_h1_q",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "volume_price",
    "unit": "百万件",
    "price_unit": "百万元/百万件",
    "description": "精密连接组件"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-06-11",
  "last_fy_end": "2026-02-28",
  "horizon": 6,
  "history": [
    {
      "start": "2023-03-01",
      "end": "2023-08-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 504.64,
      "operating_cost_ex_sbc": 375.44,
      "sbc": 14.44,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-08-29",
      "end": "2024-02-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 786.21,
      "operating_cost_ex_sbc": 596.21,
      "sbc": 16.33,
      "nonrecurring_gain": 3.714
    },
    {
      "start": "2024-02-29",
      "end": "2024-08-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 535.78,
      "operating_cost_ex_sbc": 397.46,
      "sbc": 15.18,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2024-08-29",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 817.35,
      "operating_cost_ex_sbc": 618.23,
      "sbc": 17.07,
      "nonrecurring_gain": 4.454
    },
    {
      "start": "2025-03-01",
      "end": "2025-08-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 566.92,
      "operating_cost_ex_sbc": 419.48,
      "sbc": 15.92,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2025-08-29",
      "end": "2026-02-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 848.49,
      "operating_cost_ex_sbc": 640.25,
      "sbc": 17.81,
      "nonrecurring_gain": 5.194
    },
    {
      "start": "2026-03-01",
      "end": "2026-05-28",
      "fiscal_year": "2027",
      "period_type": "bridge_quarter",
      "revenue": 460.348,
      "operating_cost_ex_sbc": 329.324,
      "sbc": 10.884,
      "nonrecurring_gain": 3.892
    }
  ],
  "opening_nwc": 334.304,
  "opening_deferred": 0,
  "opening_ppe": 307.52,
  "opening_rou": 0,
  "opening_debt": 198.4,
  "opening_retained_earnings": 158.72,
  "contributed_capital": 386.88,
  "opening_cash": 99.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 228.1,
    "price0": 6.6267907431,
    "driver_add": [
      13.76,
      15.652,
      17.544,
      19.436,
      21.328,
      23.22
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054,
      0.045
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065,
      0.07
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022,
      0.02
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188,
      0.195
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065,
      0.069
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186,
      0.192
    ],
    "tax": 0.235,
    "wacc": 0.103,
    "g": 0.024,
    "gordon_weight": 1.0,
    "exit_multiple": 7.8,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51,
      52
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58,
      57
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47,
      48
    ],
    "nol0": 109.12,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      24.8,
      0,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      9.92,
      19.84,
      29.759999999999998,
      39.68,
      49.6,
      59.519999999999996
    ],
    "beta_unlevered": 0.76,
    "target_de": 0.33,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      57.1,
      61.1,
      65.1,
      69.1,
      73.1,
      77.1
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 99.2,
    "debt": 198.4,
    "investments": 14.88,
    "lease_liability": 0,
    "minority": 11.904,
    "valuation_cash_adjustment": 11.904,
    "shares": 170,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 17.0
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 334.304,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 386.88,
    "opening_cash": 99.2,
    "opening_operating_current_assets": 334.304,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 263.9,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "mixed_ltm",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "segment_sotp",
  "c_structure_definition": "分部经营模型＋SOTP",
  "structure": {
    "b": [
      "mixed_ltm",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge"
    ],
    "c": "segment_sotp"
  },
  "market": {
    "market_price": 33.93
  },
  "segments": {
    "segment_alpha": {
      "driver0": 140,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        18.200000000000003,
        19.200000000000003,
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003
      ],
      "price0": 12.86,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.19,
        0.193,
        0.196,
        0.199,
        0.202,
        0.20500000000000002
      ],
      "capex_pct": [
        0.065,
        0.065,
        0.065,
        0.065,
        0.065,
        0.065
      ],
      "nwc_pct": [
        0.14,
        0.14,
        0.14,
        0.14,
        0.14,
        0.14
      ],
      "opening_nwc": 76,
      "opening_ppe": 173,
      "wacc_delta": -0.007,
      "method": "gordon"
    },
    "segment_beta": {
      "driver0": 165,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003,
        24.200000000000003,
        25.200000000000003
      ],
      "price0": 14.96,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.225,
        0.228,
        0.231,
        0.234,
        0.23700000000000002,
        0.24
      ],
      "capex_pct": [
        0.079,
        0.079,
        0.079,
        0.079,
        0.079,
        0.079
      ],
      "nwc_pct": [
        0.185,
        0.185,
        0.185,
        0.185,
        0.185,
        0.185
      ],
      "opening_nwc": 105,
      "opening_ppe": 231,
      "wacc_delta": 0.005999999999999999,
      "method": "exit"
    }
  },
  "event_public_facts": {
    "type": "baseline",
    "description": "建立基座模型，保存第 1 步快照。"
  },
  "event_type": "baseline",
  "steps": [
    {
      "step": 1,
      "event_type": "baseline",
      "task_id": "D03"
    },
    {
      "step": 2,
      "event_type": "disposal",
      "task_id": "D03_S2"
    },
    {
      "step": 3,
      "event_type": "acquisition",
      "task_id": "D03_S3"
    },
    {
      "step": 4,
      "event_type": "nwc_opening_basis_change",
      "task_id": "D03_S4"
    }
  ],
  "independent_from_BC": true
}
```

</details>

##### D03｜衡浦组合估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司由两个经营特征不同的分部组成，需要分别建模估值，再按分部加总（SOTP）得到公司价值。
最近完整财年末为 `2026-02-28`，估值日为 `2026-06-11`。预测共 6 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
两个分部各自独立预测经营基数、单位收入、利润率、资本开支、折旧、NWC 与 FCFF，分别按题设 DCF 或退出倍数估值。公司层净债务和稀释股数只在加总后使用一次。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

每步完成后将对应工作簿保存为 `/app/snapshots/step-N.xlsx`；不得覆盖前步快照。

本题包含连续结构事件；按 `steps/step-N/instruction.md` 顺序执行。

#### step-1

<details><summary>D03/step-1｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D03",
  "seed": 414202,
  "candidate_index": 20,
  "family": "D",
  "step": 1,
  "company": "衡浦组合",
  "dimension_selection": {
    "scenario": "精密连接组件",
    "difficulty": "L3: 依赖深度7，显式6期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "volume_price",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "SBC经营成本",
    "output_mode": "segment_dcf",
    "output_template": "mixed",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets"
  ],
  "selection_rationale": {
    "scenario": "精密连接组件要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "mixed_h1_q",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "volume_price",
    "unit": "百万件",
    "price_unit": "百万元/百万件",
    "description": "精密连接组件"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-06-11",
  "last_fy_end": "2026-02-28",
  "horizon": 6,
  "history": [
    {
      "start": "2023-03-01",
      "end": "2023-08-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 504.64,
      "operating_cost_ex_sbc": 375.44,
      "sbc": 14.44,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-08-29",
      "end": "2024-02-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 786.21,
      "operating_cost_ex_sbc": 596.21,
      "sbc": 16.33,
      "nonrecurring_gain": 3.714
    },
    {
      "start": "2024-02-29",
      "end": "2024-08-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 535.78,
      "operating_cost_ex_sbc": 397.46,
      "sbc": 15.18,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2024-08-29",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 817.35,
      "operating_cost_ex_sbc": 618.23,
      "sbc": 17.07,
      "nonrecurring_gain": 4.454
    },
    {
      "start": "2025-03-01",
      "end": "2025-08-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 566.92,
      "operating_cost_ex_sbc": 419.48,
      "sbc": 15.92,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2025-08-29",
      "end": "2026-02-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 848.49,
      "operating_cost_ex_sbc": 640.25,
      "sbc": 17.81,
      "nonrecurring_gain": 5.194
    },
    {
      "start": "2026-03-01",
      "end": "2026-05-28",
      "fiscal_year": "2027",
      "period_type": "bridge_quarter",
      "revenue": 460.348,
      "operating_cost_ex_sbc": 329.324,
      "sbc": 10.884,
      "nonrecurring_gain": 3.892
    }
  ],
  "opening_nwc": 334.304,
  "opening_deferred": 0,
  "opening_ppe": 307.52,
  "opening_rou": 0,
  "opening_debt": 198.4,
  "opening_retained_earnings": 158.72,
  "contributed_capital": 386.88,
  "opening_cash": 99.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 228.1,
    "price0": 6.6267907431,
    "driver_add": [
      13.76,
      15.652,
      17.544,
      19.436,
      21.328,
      23.22
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054,
      0.045
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065,
      0.07
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022,
      0.02
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188,
      0.195
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065,
      0.069
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186,
      0.192
    ],
    "tax": 0.235,
    "wacc": 0.103,
    "g": 0.024,
    "gordon_weight": 1.0,
    "exit_multiple": 7.8,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51,
      52
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58,
      57
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47,
      48
    ],
    "nol0": 109.12,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      24.8,
      0,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      9.92,
      19.84,
      29.759999999999998,
      39.68,
      49.6,
      59.519999999999996
    ],
    "beta_unlevered": 0.76,
    "target_de": 0.33,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      57.1,
      61.1,
      65.1,
      69.1,
      73.1,
      77.1
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 99.2,
    "debt": 198.4,
    "investments": 14.88,
    "lease_liability": 0,
    "minority": 11.904,
    "valuation_cash_adjustment": 11.904,
    "shares": 170,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 17.0
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 334.304,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 386.88,
    "opening_cash": 99.2,
    "opening_operating_current_assets": 334.304,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 263.9,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "mixed_ltm",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "segment_sotp",
  "c_structure_definition": "分部经营模型＋SOTP",
  "structure": {
    "b": [
      "mixed_ltm",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge"
    ],
    "c": "segment_sotp"
  },
  "market": {
    "market_price": 33.93
  },
  "segments": {
    "segment_alpha": {
      "driver0": 140,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        18.200000000000003,
        19.200000000000003,
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003
      ],
      "price0": 12.86,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.19,
        0.193,
        0.196,
        0.199,
        0.202,
        0.20500000000000002
      ],
      "capex_pct": [
        0.065,
        0.065,
        0.065,
        0.065,
        0.065,
        0.065
      ],
      "nwc_pct": [
        0.14,
        0.14,
        0.14,
        0.14,
        0.14,
        0.14
      ],
      "opening_nwc": 76,
      "opening_ppe": 173,
      "wacc_delta": -0.007,
      "method": "gordon"
    },
    "segment_beta": {
      "driver0": 165,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003,
        24.200000000000003,
        25.200000000000003
      ],
      "price0": 14.96,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.225,
        0.228,
        0.231,
        0.234,
        0.23700000000000002,
        0.24
      ],
      "capex_pct": [
        0.079,
        0.079,
        0.079,
        0.079,
        0.079,
        0.079
      ],
      "nwc_pct": [
        0.185,
        0.185,
        0.185,
        0.185,
        0.185,
        0.185
      ],
      "opening_nwc": 105,
      "opening_ppe": 231,
      "wacc_delta": 0.005999999999999999,
      "method": "exit"
    }
  },
  "event_public_facts": {
    "type": "baseline",
    "description": "建立基座模型，保存第 1 步快照。"
  },
  "event_type": "baseline"
}
```

</details>

##### D03｜衡浦组合估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司由两个经营特征不同的分部组成，需要分别建模估值，再按分部加总（SOTP）得到公司价值。
最近完整财年末为 `2026-02-28`，估值日为 `2026-06-11`。预测共 6 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
两个分部各自独立预测经营基数、单位收入、利润率、资本开支、折旧、NWC 与 FCFF，分别按题设 DCF 或退出倍数估值。公司层净债务和稀释股数只在加总后使用一次。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

每步完成后将对应工作簿保存为 `/app/snapshots/step-N.xlsx`；不得覆盖前步快照。

#### step-2

<details><summary>D03/step-2｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D03_S2",
  "seed": 414202,
  "candidate_index": 20,
  "family": "D",
  "step": 2,
  "company": "衡浦组合",
  "dimension_selection": {
    "scenario": "精密连接组件",
    "difficulty": "L3: 依赖深度7，显式6期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "volume_price",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "SBC经营成本",
    "output_mode": "segment_dcf",
    "output_template": "mixed",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets"
  ],
  "selection_rationale": {
    "scenario": "精密连接组件要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "mixed_h1_q",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "volume_price",
    "unit": "百万件",
    "price_unit": "百万元/百万件",
    "description": "精密连接组件"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-06-11",
  "last_fy_end": "2026-02-28",
  "horizon": 6,
  "history": [
    {
      "start": "2023-03-01",
      "end": "2023-08-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 504.64,
      "operating_cost_ex_sbc": 375.44,
      "sbc": 14.44,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-08-29",
      "end": "2024-02-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 786.21,
      "operating_cost_ex_sbc": 596.21,
      "sbc": 16.33,
      "nonrecurring_gain": 3.714
    },
    {
      "start": "2024-02-29",
      "end": "2024-08-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 535.78,
      "operating_cost_ex_sbc": 397.46,
      "sbc": 15.18,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2024-08-29",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 817.35,
      "operating_cost_ex_sbc": 618.23,
      "sbc": 17.07,
      "nonrecurring_gain": 4.454
    },
    {
      "start": "2025-03-01",
      "end": "2025-08-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 566.92,
      "operating_cost_ex_sbc": 419.48,
      "sbc": 15.92,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2025-08-29",
      "end": "2026-02-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 848.49,
      "operating_cost_ex_sbc": 640.25,
      "sbc": 17.81,
      "nonrecurring_gain": 5.194
    },
    {
      "start": "2026-03-01",
      "end": "2026-05-28",
      "fiscal_year": "2027",
      "period_type": "bridge_quarter",
      "revenue": 460.348,
      "operating_cost_ex_sbc": 329.324,
      "sbc": 10.884,
      "nonrecurring_gain": 3.892
    }
  ],
  "opening_nwc": 334.304,
  "opening_deferred": 0,
  "opening_ppe": 307.52,
  "opening_rou": 0,
  "opening_debt": 198.4,
  "opening_retained_earnings": 158.72,
  "contributed_capital": 386.88,
  "opening_cash": 99.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 228.1,
    "price0": 6.6267907431,
    "driver_add": [
      13.76,
      15.652,
      17.544,
      19.436,
      21.328,
      23.22
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054,
      0.045
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065,
      0.07
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022,
      0.02
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188,
      0.195
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065,
      0.069
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186,
      0.192
    ],
    "tax": 0.235,
    "wacc": 0.103,
    "g": 0.024,
    "gordon_weight": 1.0,
    "exit_multiple": 7.8,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51,
      52
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58,
      57
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47,
      48
    ],
    "nol0": 109.12,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      24.8,
      0,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      9.92,
      19.84,
      29.759999999999998,
      39.68,
      49.6,
      59.519999999999996
    ],
    "beta_unlevered": 0.76,
    "target_de": 0.33,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      57.1,
      61.1,
      65.1,
      69.1,
      73.1,
      77.1
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 99.2,
    "debt": 166.656,
    "investments": 14.88,
    "lease_liability": 0,
    "minority": 11.904,
    "valuation_cash_adjustment": 49.403999999999996,
    "shares": 170,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 17.0
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 334.304,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 386.88,
    "opening_cash": 99.2,
    "opening_operating_current_assets": 334.304,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 263.9,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "mixed_ltm",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "segment_sotp",
  "c_structure_definition": "分部经营模型＋SOTP",
  "structure": {
    "b": [
      "mixed_ltm",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge"
    ],
    "c": "segment_sotp"
  },
  "market": {
    "market_price": 33.93
  },
  "segments": {
    "segment_alpha": {
      "driver0": 140,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        18.200000000000003,
        19.200000000000003,
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003
      ],
      "price0": 12.86,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.19,
        0.193,
        0.196,
        0.199,
        0.202,
        0.20500000000000002
      ],
      "capex_pct": [
        0.065,
        0.065,
        0.065,
        0.065,
        0.065,
        0.065
      ],
      "nwc_pct": [
        0.14,
        0.14,
        0.14,
        0.14,
        0.14,
        0.14
      ],
      "opening_nwc": 76,
      "opening_ppe": 173,
      "wacc_delta": -0.007,
      "method": "gordon"
    },
    "segment_beta": {
      "driver0": 128.7,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003,
        24.200000000000003,
        25.200000000000003
      ],
      "price0": 14.96,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.225,
        0.228,
        0.231,
        0.234,
        0.23700000000000002,
        0.24
      ],
      "capex_pct": [
        0.079,
        0.079,
        0.079,
        0.079,
        0.079,
        0.079
      ],
      "nwc_pct": [
        0.185,
        0.185,
        0.185,
        0.185,
        0.185,
        0.185
      ],
      "opening_nwc": 105,
      "opening_ppe": 168.63,
      "wacc_delta": 0.005999999999999999,
      "method": "exit"
    }
  },
  "event_public_facts": {
    "type": "disposal",
    "description": "剥离 Beta 分部的一个区域经营单元，收入基数、资产和债务同步移除；处置净现金进入股权桥",
    "segment": "segment_beta"
  },
  "event_type": "disposal"
}
```

</details>

##### D03_S2｜衡浦组合估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司由两个经营特征不同的分部组成，需要分别建模估值，再按分部加总（SOTP）得到公司价值。
最近完整财年末为 `2026-02-28`，估值日为 `2026-06-11`。预测共 6 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
两个分部各自独立预测经营基数、单位收入、利润率、资本开支、折旧、NWC 与 FCFF，分别按题设 DCF 或退出倍数估值。公司层净债务和稀释股数只在加总后使用一次。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 2 步修改：业务剥离
剥离 Beta 分部的一个区域经营单元，收入基数、资产和债务同步移除；处置净现金进入股权桥。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-2.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### step-3

<details><summary>D03/step-3｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D03_S3",
  "seed": 414202,
  "candidate_index": 20,
  "family": "D",
  "step": 3,
  "company": "衡浦组合",
  "dimension_selection": {
    "scenario": "精密连接组件",
    "difficulty": "L3: 依赖深度7，显式6期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "volume_price",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "SBC经营成本",
    "output_mode": "segment_dcf",
    "output_template": "mixed",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets"
  ],
  "selection_rationale": {
    "scenario": "精密连接组件要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "mixed_h1_q",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "volume_price",
    "unit": "百万件",
    "price_unit": "百万元/百万件",
    "description": "精密连接组件"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-06-11",
  "last_fy_end": "2026-02-28",
  "horizon": 6,
  "history": [
    {
      "start": "2023-03-01",
      "end": "2023-08-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 504.64,
      "operating_cost_ex_sbc": 375.44,
      "sbc": 14.44,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-08-29",
      "end": "2024-02-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 786.21,
      "operating_cost_ex_sbc": 596.21,
      "sbc": 16.33,
      "nonrecurring_gain": 3.714
    },
    {
      "start": "2024-02-29",
      "end": "2024-08-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 535.78,
      "operating_cost_ex_sbc": 397.46,
      "sbc": 15.18,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2024-08-29",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 817.35,
      "operating_cost_ex_sbc": 618.23,
      "sbc": 17.07,
      "nonrecurring_gain": 4.454
    },
    {
      "start": "2025-03-01",
      "end": "2025-08-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 566.92,
      "operating_cost_ex_sbc": 419.48,
      "sbc": 15.92,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2025-08-29",
      "end": "2026-02-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 848.49,
      "operating_cost_ex_sbc": 640.25,
      "sbc": 17.81,
      "nonrecurring_gain": 5.194
    },
    {
      "start": "2026-03-01",
      "end": "2026-05-28",
      "fiscal_year": "2027",
      "period_type": "bridge_quarter",
      "revenue": 460.348,
      "operating_cost_ex_sbc": 329.324,
      "sbc": 10.884,
      "nonrecurring_gain": 3.892
    }
  ],
  "opening_nwc": 334.304,
  "opening_deferred": 0,
  "opening_ppe": 307.52,
  "opening_rou": 0,
  "opening_debt": 198.4,
  "opening_retained_earnings": 158.72,
  "contributed_capital": 386.88,
  "opening_cash": 99.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 228.1,
    "price0": 6.6267907431,
    "driver_add": [
      13.76,
      15.652,
      17.544,
      19.436,
      21.328,
      23.22
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054,
      0.045
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065,
      0.07
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022,
      0.02
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188,
      0.195
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065,
      0.069
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186,
      0.192
    ],
    "tax": 0.235,
    "wacc": 0.103,
    "g": 0.024,
    "gordon_weight": 1.0,
    "exit_multiple": 7.8,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51,
      52
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58,
      57
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47,
      48
    ],
    "nol0": 109.12,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      24.8,
      0,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      9.92,
      19.84,
      29.759999999999998,
      39.68,
      49.6,
      59.519999999999996
    ],
    "beta_unlevered": 0.76,
    "target_de": 0.33,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      57.1,
      61.1,
      65.1,
      69.1,
      73.1,
      77.1
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 99.2,
    "debt": 251.656,
    "investments": 14.88,
    "lease_liability": 0,
    "minority": 11.904,
    "valuation_cash_adjustment": 4.403999999999996,
    "shares": 170,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 17.0
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 334.304,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 386.88,
    "opening_cash": 99.2,
    "opening_operating_current_assets": 334.304,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 263.9,
  "nwc_opening_basis": "valuation_date",
  "b_items": [
    "mixed_ltm",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "segment_sotp",
  "c_structure_definition": "分部经营模型＋SOTP",
  "structure": {
    "b": [
      "mixed_ltm",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge"
    ],
    "c": "segment_sotp"
  },
  "market": {
    "market_price": 33.93
  },
  "segments": {
    "segment_alpha": {
      "driver0": 140,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        18.200000000000003,
        19.200000000000003,
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003
      ],
      "price0": 12.86,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.19,
        0.193,
        0.196,
        0.199,
        0.202,
        0.20500000000000002
      ],
      "capex_pct": [
        0.065,
        0.065,
        0.065,
        0.065,
        0.065,
        0.065
      ],
      "nwc_pct": [
        0.14,
        0.14,
        0.14,
        0.14,
        0.14,
        0.14
      ],
      "opening_nwc": 76,
      "opening_ppe": 173,
      "wacc_delta": -0.007,
      "method": "gordon"
    },
    "segment_beta": {
      "driver0": 128.7,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003,
        24.200000000000003,
        25.200000000000003
      ],
      "price0": 14.96,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.225,
        0.228,
        0.231,
        0.234,
        0.23700000000000002,
        0.24
      ],
      "capex_pct": [
        0.079,
        0.079,
        0.079,
        0.079,
        0.079,
        0.079
      ],
      "nwc_pct": [
        0.185,
        0.185,
        0.185,
        0.185,
        0.185,
        0.185
      ],
      "opening_nwc": 105,
      "opening_ppe": 168.63,
      "wacc_delta": 0.005999999999999999,
      "method": "exit"
    },
    "segment_gamma": {
      "driver0": 58,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        18.200000000000003,
        19.200000000000003,
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003
      ],
      "price0": 11.4,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.19,
        0.193,
        0.196,
        0.199,
        0.202,
        0.20500000000000002
      ],
      "capex_pct": [
        0.065,
        0.065,
        0.065,
        0.065,
        0.065,
        0.065
      ],
      "nwc_pct": [
        0.14,
        0.14,
        0.14,
        0.14,
        0.14,
        0.14
      ],
      "opening_nwc": 23,
      "opening_ppe": 67,
      "wacc_delta": 0.005,
      "method": "exit"
    }
  },
  "event_public_facts": {
    "type": "acquisition",
    "description": "收购 Gamma 独立分部并以其自身驱动、利润率、再投资和退出倍数估值；净债务与现金调整只在公司层一次",
    "segment": "segment_gamma"
  },
  "event_type": "acquisition"
}
```

</details>

##### D03_S3｜衡浦组合估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司由两个经营特征不同的分部组成，需要分别建模估值，再按分部加总（SOTP）得到公司价值。
最近完整财年末为 `2026-02-28`，估值日为 `2026-06-11`。预测共 6 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **估值日余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
两个分部各自独立预测经营基数、单位收入、利润率、资本开支、折旧、NWC 与 FCFF，分别按题设 DCF 或退出倍数估值。公司层净债务和稀释股数只在加总后使用一次。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 3 步修改：收购新分部
收购 Gamma 独立分部并以其自身驱动、利润率、再投资和退出倍数估值；净债务与现金调整只在公司层一次。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-3.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### step-4

<details><summary>D03/step-4｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D03_S4",
  "seed": 414202,
  "candidate_index": 20,
  "family": "D",
  "step": 4,
  "company": "衡浦组合",
  "dimension_selection": {
    "scenario": "精密连接组件",
    "difficulty": "L3: 依赖深度7，显式6期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "volume_price",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "SBC经营成本",
    "output_mode": "segment_dcf",
    "output_template": "mixed",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "nwc_days",
    "rolling_assets"
  ],
  "selection_rationale": {
    "scenario": "精密连接组件要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "mixed_h1_q",
    "midyear": true,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": false
  },
  "business": {
    "driver": "volume_price",
    "unit": "百万件",
    "price_unit": "百万元/百万件",
    "description": "精密连接组件"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2026-06-11",
  "last_fy_end": "2026-02-28",
  "horizon": 6,
  "history": [
    {
      "start": "2023-03-01",
      "end": "2023-08-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 504.64,
      "operating_cost_ex_sbc": 375.44,
      "sbc": 14.44,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2023-08-29",
      "end": "2024-02-28",
      "fiscal_year": "2024",
      "period_type": "half_year",
      "revenue": 786.21,
      "operating_cost_ex_sbc": 596.21,
      "sbc": 16.33,
      "nonrecurring_gain": 3.714
    },
    {
      "start": "2024-02-29",
      "end": "2024-08-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 535.78,
      "operating_cost_ex_sbc": 397.46,
      "sbc": 15.18,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2024-08-29",
      "end": "2025-02-28",
      "fiscal_year": "2025",
      "period_type": "half_year",
      "revenue": 817.35,
      "operating_cost_ex_sbc": 618.23,
      "sbc": 17.07,
      "nonrecurring_gain": 4.454
    },
    {
      "start": "2025-03-01",
      "end": "2025-08-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 566.92,
      "operating_cost_ex_sbc": 419.48,
      "sbc": 15.92,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2025-08-29",
      "end": "2026-02-28",
      "fiscal_year": "2026",
      "period_type": "half_year",
      "revenue": 848.49,
      "operating_cost_ex_sbc": 640.25,
      "sbc": 17.81,
      "nonrecurring_gain": 5.194
    },
    {
      "start": "2026-03-01",
      "end": "2026-05-28",
      "fiscal_year": "2027",
      "period_type": "bridge_quarter",
      "revenue": 460.348,
      "operating_cost_ex_sbc": 329.324,
      "sbc": 10.884,
      "nonrecurring_gain": 3.892
    }
  ],
  "opening_nwc": 314.90272,
  "opening_deferred": 0,
  "opening_ppe": 307.52,
  "opening_rou": 0,
  "opening_debt": 198.4,
  "opening_retained_earnings": 158.72,
  "contributed_capital": 386.88,
  "opening_cash": 99.2,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 228.1,
    "price0": 6.6267907431,
    "driver_add": [
      13.76,
      15.652,
      17.544,
      19.436,
      21.328,
      23.22
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063,
      0.054,
      0.045
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06,
      0.065,
      0.07
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024,
      0.022,
      0.02
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181,
      0.188,
      0.195
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061,
      0.065,
      0.069
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18,
      0.186,
      0.192
    ],
    "tax": 0.235,
    "wacc": 0.103,
    "g": 0.024,
    "gordon_weight": 1.0,
    "exit_multiple": 7.8,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50,
      51,
      52
    ],
    "dio": [
      62,
      61,
      60,
      59,
      58,
      57
    ],
    "dpo": [
      43,
      44,
      45,
      46,
      47,
      48
    ],
    "nol0": 109.12,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      24.8,
      0,
      0,
      0,
      0,
      0
    ],
    "debt_repayment": [
      9.92,
      19.84,
      29.759999999999998,
      39.68,
      49.6,
      59.519999999999996
    ],
    "beta_unlevered": 0.76,
    "target_de": 0.33,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      57.1,
      61.1,
      65.1,
      69.1,
      73.1,
      77.1
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 99.2,
    "debt": 251.656,
    "investments": 14.88,
    "lease_liability": 0,
    "minority": 11.904,
    "valuation_cash_adjustment": 4.403999999999996,
    "shares": 170,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 17.0
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 334.304,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 386.88,
    "opening_cash": 99.2,
    "opening_operating_current_assets": 334.304,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 263.9,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "mixed_ltm",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_valuation_open",
    "equity_bridge"
  ],
  "b_item_definitions": {
    "mixed_ltm": "半年＋桥接季度的混合历史拼接 LTM",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_valuation_open": "营运资本天数或比例法；首期 ΔNWC 用估值日余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥"
  },
  "c_structure": "segment_sotp",
  "c_structure_definition": "分部经营模型＋SOTP",
  "structure": {
    "b": [
      "mixed_ltm",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_valuation_open",
      "equity_bridge"
    ],
    "c": "segment_sotp"
  },
  "market": {
    "market_price": 33.93
  },
  "segments": {
    "segment_alpha": {
      "driver0": 140,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        18.200000000000003,
        19.200000000000003,
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003
      ],
      "price0": 12.86,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.19,
        0.193,
        0.196,
        0.199,
        0.202,
        0.20500000000000002
      ],
      "capex_pct": [
        0.065,
        0.065,
        0.065,
        0.065,
        0.065,
        0.065
      ],
      "nwc_pct": [
        0.14,
        0.14,
        0.14,
        0.14,
        0.14,
        0.14
      ],
      "opening_nwc": 76,
      "opening_ppe": 173,
      "wacc_delta": -0.007,
      "method": "gordon"
    },
    "segment_beta": {
      "driver0": 128.7,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003,
        24.200000000000003,
        25.200000000000003
      ],
      "price0": 14.96,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.225,
        0.228,
        0.231,
        0.234,
        0.23700000000000002,
        0.24
      ],
      "capex_pct": [
        0.079,
        0.079,
        0.079,
        0.079,
        0.079,
        0.079
      ],
      "nwc_pct": [
        0.185,
        0.185,
        0.185,
        0.185,
        0.185,
        0.185
      ],
      "opening_nwc": 105,
      "opening_ppe": 168.63,
      "wacc_delta": 0.005999999999999999,
      "method": "exit"
    },
    "segment_gamma": {
      "driver0": 58,
      "attrition_rate": [
        0.04,
        0.045,
        0.05,
        0.055,
        0.06,
        0.065
      ],
      "driver_add": [
        18.200000000000003,
        19.200000000000003,
        20.200000000000003,
        21.200000000000003,
        22.200000000000003,
        23.200000000000003
      ],
      "price0": 11.4,
      "price_growth": [
        0.022,
        0.024,
        0.026,
        0.027999999999999997,
        0.03,
        0.032
      ],
      "ebit_margin": [
        0.19,
        0.193,
        0.196,
        0.199,
        0.202,
        0.20500000000000002
      ],
      "capex_pct": [
        0.065,
        0.065,
        0.065,
        0.065,
        0.065,
        0.065
      ],
      "nwc_pct": [
        0.14,
        0.14,
        0.14,
        0.14,
        0.14,
        0.14
      ],
      "opening_nwc": 23,
      "opening_ppe": 67,
      "wacc_delta": 0.005,
      "method": "exit"
    }
  },
  "opening_nwc_valuation_date": 334.304,
  "opening_nwc_last_fye": 314.90272,
  "event_public_facts": {
    "type": "nwc_opening_basis_change",
    "description": "从本步起，首期 ΔNWC 改用最近财年末余额，保留估值日 NWC 事实用于勾稽",
    "opening_nwc_last_fye": 314.90272
  },
  "event_type": "nwc_opening_basis_change"
}
```

</details>

##### D03_S4｜衡浦组合估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司由两个经营特征不同的分部组成，需要分别建模估值，再按分部加总（SOTP）得到公司价值。
最近完整财年末为 `2026-02-28`，估值日为 `2026-06-11`。预测共 6 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用年中惯例，终值落在最后一个完整财年末。
历史数据由完整财年、其后的一个半年和再后面的一个桥接季度拼接而成。LTM 只能由这个半年与桥接季度组成，必须显示两段来源，不得重复、遗漏或年化。SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
两个分部各自独立预测经营基数、单位收入、利润率、资本开支、折旧、NWC 与 FCFF，分别按题设 DCF 或退出倍数估值。公司层净债务和稀释股数只在加总后使用一次。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 4 步修改：营运资本期初口径变更
从本步起，首期 ΔNWC 改用最近财年末余额，保留估值日 NWC 事实用于勾稽。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-4.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### D03 选用的 rubric（59 条，权重合计 157；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 公开输出键唯一数值 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定金额股数比率单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | output、memo及各步快照须存在 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 须有Results页并保留Inputs页 |
| 01-HISTORY | 多步状态与业务重构 | 原始历史事实未被覆盖或删除 | rule | 主需 | 题面禁止改写原始历史 |
| 08-OLD | 多步状态与业务重构 | 后续工作簿保留事件前原始输入与状态 | rule | 主需 | 后续步需保留原始输入 |
| D-FINAL-VALUES | 多步状态与业务重构 | 最后一步工作簿的全部输出键与最终独立真值一致 | rule | 主需 | 最终输出键需正确 |
| D-FINAL-LIVE | 多步状态与业务重构 | 最后一步结果仍为活公式，隐藏扰动可传导 | rule | 主需 | 隐藏扰动需活公式传导 |
| D-STEP-SNAPSHOT | 多步状态与业务重构 | 每一步都保存了独立快照 | rule | 主需 | 题面要求逐步保存快照 |
| D-STEP-VALUES | 多步状态与业务重构 | 每一步快照的输出与该步独立真值一致 | rule | 主需 | 每步快照值需正确 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史需聚合为完整财年 |
| B-MIXLTM | 历史与会计口径 | 混合历史 LTM 由最近完整半年加其后桥接季度构成，不重复计入、不遗漏、不年化 | rule | 主需 | 题面要求半年加桥接季度LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 历史含非经常收益需剔除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC为经营成本不加回 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 存量驱动含流失与新增 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均基数乘价及残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 分部各期利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期NWC差额与符号 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用NWC天数法 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用估值日余额 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 新增无形资产独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 启用滚动资产模块 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 分部需计算FCFF |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 题面要求实际天数年中折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | 题设双终值机制 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 题面要求库存股期权与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值必然涉及 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题面涉及新增无形资产 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段只含估值日后活动 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 结果须为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 重算对比独立真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查第一组扰动 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏检查第二组扰动 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页布局自由 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不得硬编码假设 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | 残期加多期需列对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 利息债务链易成循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求memo说明驱动与局限 |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 要求可追溯模型及LTM来源显示 |
| C-SOTP-SEG | 经营预测 | 每个分部有独立的收入、利润率、再投资和 FCFF | rule | 主需 | 题面要求分部独立预测 |
| C-SOTP-VAL | 经营预测 | 每个分部按题面指定方法（DCF 或倍数）单独估值 | rule | 主需 | 分部分别按DCF或倍数估值 |
| C-SOTP-SUM | 经营预测 | SOTP 企业价值等于各分部价值之和，公司层费用按题面处理 | rule | 主需 | SOTP加总为企业价值 |
| C-SOTP-BRIDGE | 经营预测 | 净债务与稀释股数只在公司层扣减一次，不在分部重复扣减 | rule | 主需 | 净债务和股数只用一次 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须保留原始输入 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | LTM指定半年加桥接季度窗口 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 半年与季度混合期间不得混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加6期预测序列 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 原始披露期不得改写 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | 双终值法须共用显性期现值 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史含非经常收益需规范化 |
| X-TA-003 | 表达与专业可用性 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | llm | 次需 | SBC与非经常项规范化须说明一致 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数年中折现需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 分部FCFF各构成项须独立显示 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon与退出倍数终值 |

### D04（D）

<details><summary>D04｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D04",
  "seed": 415179,
  "candidate_index": 3,
  "family": "D",
  "company": "禾汐药业",
  "dimension_selection": {
    "scenario": "楼宇监测装机服务",
    "difficulty": "L1: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "installed_base",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "dcf_only",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days",
    "intangible_pool"
  ],
  "selection_rationale": {
    "scenario": "楼宇监测装机服务要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": true
  },
  "business": {
    "driver": "installed_base",
    "unit": "千台",
    "price_unit": "百万元/台次",
    "description": "楼宇监测装机服务"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-03-09",
  "last_fy_end": "2024-10-31",
  "horizon": 4,
  "history": [
    {
      "start": "2022-05-01",
      "end": "2022-07-31",
      "fiscal_year": "2022",
      "revenue": 434.180198,
      "ebit": 44.291501,
      "operating_cost_ex_sbc": 345.628899,
      "sbc": 10.273268,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-08-01",
      "end": "2022-10-31",
      "fiscal_year": "2022",
      "revenue": 446.198936,
      "ebit": 48.015515,
      "operating_cost_ex_sbc": 353.540641,
      "sbc": 10.918892,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2022-11-01",
      "end": "2023-01-31",
      "fiscal_year": "2023",
      "revenue": 458.217672,
      "ebit": 51.852701,
      "operating_cost_ex_sbc": 361.361914,
      "sbc": 11.564516,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2023-02-01",
      "end": "2023-04-30",
      "fiscal_year": "2023",
      "revenue": 470.236409,
      "ebit": 55.80306,
      "operating_cost_ex_sbc": 369.09272,
      "sbc": 12.210141,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2023-05-01",
      "end": "2023-07-31",
      "fiscal_year": "2023",
      "revenue": 482.255147,
      "ebit": 59.86659,
      "operating_cost_ex_sbc": 376.733059,
      "sbc": 12.855765,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2023-08-01",
      "end": "2023-10-31",
      "fiscal_year": "2023",
      "revenue": 494.273882,
      "ebit": 64.043294,
      "operating_cost_ex_sbc": 384.282928,
      "sbc": 13.50139,
      "nonrecurring_gain": 1.85
    },
    {
      "start": "2023-11-01",
      "end": "2024-01-31",
      "fiscal_year": "2024",
      "revenue": 506.29262,
      "ebit": 68.333168,
      "operating_cost_ex_sbc": 391.742329,
      "sbc": 14.147013,
      "nonrecurring_gain": 2.22
    },
    {
      "start": "2024-02-01",
      "end": "2024-04-30",
      "fiscal_year": "2024",
      "revenue": 518.311357,
      "ebit": 72.736216,
      "operating_cost_ex_sbc": 399.111263,
      "sbc": 14.792638,
      "nonrecurring_gain": 2.59
    },
    {
      "start": "2024-05-01",
      "end": "2024-07-31",
      "fiscal_year": "2024",
      "revenue": 530.330095,
      "ebit": 77.252435,
      "operating_cost_ex_sbc": 406.389729,
      "sbc": 15.438261,
      "nonrecurring_gain": 2.96
    },
    {
      "start": "2024-08-01",
      "end": "2024-10-31",
      "fiscal_year": "2024",
      "revenue": 542.348831,
      "ebit": 81.881827,
      "operating_cost_ex_sbc": 413.577726,
      "sbc": 16.083884,
      "nonrecurring_gain": 9.524529
    }
  ],
  "opening_nwc": 438.462856,
  "opening_deferred": 0,
  "opening_ppe": 386.57,
  "opening_rou": 0,
  "opening_debt": 249.4,
  "opening_retained_earnings": 199.52,
  "contributed_capital": 486.33,
  "opening_cash": 124.7,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 161.8,
    "price0": 5.204791705400001,
    "driver_add": [
      6.96,
      7.917,
      8.874,
      9.831
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.109,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 137.17,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      31.175,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.47,
      24.94,
      37.410000000000004,
      49.88
    ],
    "beta_unlevered": 0.88,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "service_frequency": [
      3.2,
      3.2800000000000002,
      3.3600000000000003,
      3.4400000000000004
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      58.8,
      62.8,
      66.8,
      70.8
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 124.7,
    "debt": 249.4,
    "investments": 18.705,
    "lease_liability": 0,
    "minority": 14.964,
    "valuation_cash_adjustment": 14.964,
    "shares": 119,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 11.9
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 495.059,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 486.33,
    "opening_cash": 124.7,
    "opening_operating_current_assets": 495.059,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 271.2,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge",
    "dual_asset_pool"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_asset_pool": "固定资产＋无形资产双资产池"
  },
  "c_structure": "risk_adjusted_pipeline",
  "c_structure_definition": "风险调整管线 DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge",
      "dual_asset_pool"
    ],
    "c": "risk_adjusted_pipeline"
  },
  "opening_nwc_last_fye": 438.462856,
  "opening_nwc_valuation_date": 401.534,
  "market": {
    "market_price": 34.84
  },
  "projects": {
    "project_atlas": {
      "commissioning_period": 2,
      "construction_capex": [
        136,
        0,
        0,
        0
      ],
      "project_revenue": [
        159.8,
        175.8,
        191.8,
        207.8
      ],
      "project_margin": 0.21,
      "project_da": [
        7,
        9,
        11,
        13
      ],
      "project_operating_capex": [
        8,
        8,
        8,
        8
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5
      ],
      "project_fcff": [
        -136,
        26.24227,
        29.81267,
        33.38307
      ],
      "success_probability": 0.67
    },
    "project_boreal": {
      "commissioning_period": 3,
      "construction_capex": [
        0,
        165,
        0,
        0
      ],
      "project_revenue": [
        182.8,
        198.8,
        214.8,
        230.8
      ],
      "project_margin": 0.245,
      "project_da": [
        7,
        9,
        11,
        13
      ],
      "project_operating_capex": [
        11,
        11,
        11,
        11
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5
      ],
      "project_fcff": [
        0,
        -165,
        36.25889,
        40.25769
      ],
      "success_probability": 0.53
    }
  },
  "event_public_facts": {
    "type": "baseline",
    "description": "建立基座模型，保存第 1 步快照。"
  },
  "event_type": "baseline",
  "steps": [
    {
      "step": 1,
      "event_type": "baseline",
      "task_id": "D04"
    },
    {
      "step": 2,
      "event_type": "commissioning_and_capex_rearrangement",
      "task_id": "D04_S2"
    },
    {
      "step": 3,
      "event_type": "project_capex_and_scope_revision",
      "task_id": "D04_S3"
    },
    {
      "step": 4,
      "event_type": "nwc_opening_basis_change",
      "task_id": "D04_S4"
    }
  ],
  "independent_from_BC": true
}
```

</details>

##### D04｜禾汐药业估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司价值由已有业务和两个在建项目组成，项目需按投产时间和成功概率做风险调整后估值。
公司财年截至每年 10 月 31 日，最近完整财年末为 `2024-10-31`，估值日 `2025-03-09` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
固定资产与无形资产分别滚动：期初＋新增－折旧/摊销＝期末；无形资产新增扣 FCFF，摊销加回，不能与固定资产混池。
项目投产期之前收入必须为零；建设期支出独立计入对应期间。项目经营 FCFF 单列后乘成功概率，概率不得加到 WACC。已有业务价值与项目风险调整现值分开列示后相加。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

每步完成后将对应工作簿保存为 `/app/snapshots/step-N.xlsx`；不得覆盖前步快照。

本题包含连续结构事件；按 `steps/step-N/instruction.md` 顺序执行。

#### step-1

<details><summary>D04/step-1｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D04",
  "seed": 415179,
  "candidate_index": 3,
  "family": "D",
  "step": 1,
  "company": "禾汐药业",
  "dimension_selection": {
    "scenario": "楼宇监测装机服务",
    "difficulty": "L1: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "installed_base",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "dcf_only",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days",
    "intangible_pool"
  ],
  "selection_rationale": {
    "scenario": "楼宇监测装机服务要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": true
  },
  "business": {
    "driver": "installed_base",
    "unit": "千台",
    "price_unit": "百万元/台次",
    "description": "楼宇监测装机服务"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-03-09",
  "last_fy_end": "2024-10-31",
  "horizon": 4,
  "history": [
    {
      "start": "2022-05-01",
      "end": "2022-07-31",
      "fiscal_year": "2022",
      "revenue": 434.180198,
      "ebit": 44.291501,
      "operating_cost_ex_sbc": 345.628899,
      "sbc": 10.273268,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-08-01",
      "end": "2022-10-31",
      "fiscal_year": "2022",
      "revenue": 446.198936,
      "ebit": 48.015515,
      "operating_cost_ex_sbc": 353.540641,
      "sbc": 10.918892,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2022-11-01",
      "end": "2023-01-31",
      "fiscal_year": "2023",
      "revenue": 458.217672,
      "ebit": 51.852701,
      "operating_cost_ex_sbc": 361.361914,
      "sbc": 11.564516,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2023-02-01",
      "end": "2023-04-30",
      "fiscal_year": "2023",
      "revenue": 470.236409,
      "ebit": 55.80306,
      "operating_cost_ex_sbc": 369.09272,
      "sbc": 12.210141,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2023-05-01",
      "end": "2023-07-31",
      "fiscal_year": "2023",
      "revenue": 482.255147,
      "ebit": 59.86659,
      "operating_cost_ex_sbc": 376.733059,
      "sbc": 12.855765,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2023-08-01",
      "end": "2023-10-31",
      "fiscal_year": "2023",
      "revenue": 494.273882,
      "ebit": 64.043294,
      "operating_cost_ex_sbc": 384.282928,
      "sbc": 13.50139,
      "nonrecurring_gain": 1.85
    },
    {
      "start": "2023-11-01",
      "end": "2024-01-31",
      "fiscal_year": "2024",
      "revenue": 506.29262,
      "ebit": 68.333168,
      "operating_cost_ex_sbc": 391.742329,
      "sbc": 14.147013,
      "nonrecurring_gain": 2.22
    },
    {
      "start": "2024-02-01",
      "end": "2024-04-30",
      "fiscal_year": "2024",
      "revenue": 518.311357,
      "ebit": 72.736216,
      "operating_cost_ex_sbc": 399.111263,
      "sbc": 14.792638,
      "nonrecurring_gain": 2.59
    },
    {
      "start": "2024-05-01",
      "end": "2024-07-31",
      "fiscal_year": "2024",
      "revenue": 530.330095,
      "ebit": 77.252435,
      "operating_cost_ex_sbc": 406.389729,
      "sbc": 15.438261,
      "nonrecurring_gain": 2.96
    },
    {
      "start": "2024-08-01",
      "end": "2024-10-31",
      "fiscal_year": "2024",
      "revenue": 542.348831,
      "ebit": 81.881827,
      "operating_cost_ex_sbc": 413.577726,
      "sbc": 16.083884,
      "nonrecurring_gain": 9.524529
    }
  ],
  "opening_nwc": 438.462856,
  "opening_deferred": 0,
  "opening_ppe": 386.57,
  "opening_rou": 0,
  "opening_debt": 249.4,
  "opening_retained_earnings": 199.52,
  "contributed_capital": 486.33,
  "opening_cash": 124.7,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 161.8,
    "price0": 5.204791705400001,
    "driver_add": [
      6.96,
      7.917,
      8.874,
      9.831
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.109,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 137.17,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      31.175,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.47,
      24.94,
      37.410000000000004,
      49.88
    ],
    "beta_unlevered": 0.88,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "service_frequency": [
      3.2,
      3.2800000000000002,
      3.3600000000000003,
      3.4400000000000004
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      58.8,
      62.8,
      66.8,
      70.8
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 124.7,
    "debt": 249.4,
    "investments": 18.705,
    "lease_liability": 0,
    "minority": 14.964,
    "valuation_cash_adjustment": 14.964,
    "shares": 119,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 11.9
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 495.059,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 486.33,
    "opening_cash": 124.7,
    "opening_operating_current_assets": 495.059,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 271.2,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge",
    "dual_asset_pool"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_asset_pool": "固定资产＋无形资产双资产池"
  },
  "c_structure": "risk_adjusted_pipeline",
  "c_structure_definition": "风险调整管线 DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge",
      "dual_asset_pool"
    ],
    "c": "risk_adjusted_pipeline"
  },
  "opening_nwc_last_fye": 438.462856,
  "opening_nwc_valuation_date": 401.534,
  "market": {
    "market_price": 34.84
  },
  "projects": {
    "project_atlas": {
      "commissioning_period": 2,
      "construction_capex": [
        136,
        0,
        0,
        0
      ],
      "project_revenue": [
        159.8,
        175.8,
        191.8,
        207.8
      ],
      "project_margin": 0.21,
      "project_da": [
        7,
        9,
        11,
        13
      ],
      "project_operating_capex": [
        8,
        8,
        8,
        8
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5
      ],
      "project_fcff": [
        -136,
        26.24227,
        29.81267,
        33.38307
      ],
      "success_probability": 0.67
    },
    "project_boreal": {
      "commissioning_period": 3,
      "construction_capex": [
        0,
        165,
        0,
        0
      ],
      "project_revenue": [
        182.8,
        198.8,
        214.8,
        230.8
      ],
      "project_margin": 0.245,
      "project_da": [
        7,
        9,
        11,
        13
      ],
      "project_operating_capex": [
        11,
        11,
        11,
        11
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5
      ],
      "project_fcff": [
        0,
        -165,
        36.25889,
        40.25769
      ],
      "success_probability": 0.53
    }
  },
  "event_public_facts": {
    "type": "baseline",
    "description": "建立基座模型，保存第 1 步快照。"
  },
  "event_type": "baseline"
}
```

</details>

##### D04｜禾汐药业估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司价值由已有业务和两个在建项目组成，项目需按投产时间和成功概率做风险调整后估值。
公司财年截至每年 10 月 31 日，最近完整财年末为 `2024-10-31`，估值日 `2025-03-09` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
固定资产与无形资产分别滚动：期初＋新增－折旧/摊销＝期末；无形资产新增扣 FCFF，摊销加回，不能与固定资产混池。
项目投产期之前收入必须为零；建设期支出独立计入对应期间。项目经营 FCFF 单列后乘成功概率，概率不得加到 WACC。已有业务价值与项目风险调整现值分开列示后相加。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

每步完成后将对应工作簿保存为 `/app/snapshots/step-N.xlsx`；不得覆盖前步快照。

#### step-2

<details><summary>D04/step-2｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D04_S2",
  "seed": 415179,
  "candidate_index": 3,
  "family": "D",
  "step": 2,
  "company": "禾汐药业",
  "dimension_selection": {
    "scenario": "楼宇监测装机服务",
    "difficulty": "L1: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "installed_base",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "dcf_only",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days",
    "intangible_pool"
  ],
  "selection_rationale": {
    "scenario": "楼宇监测装机服务要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": true
  },
  "business": {
    "driver": "installed_base",
    "unit": "千台",
    "price_unit": "百万元/台次",
    "description": "楼宇监测装机服务"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-03-09",
  "last_fy_end": "2024-10-31",
  "horizon": 4,
  "history": [
    {
      "start": "2022-05-01",
      "end": "2022-07-31",
      "fiscal_year": "2022",
      "revenue": 434.180198,
      "ebit": 44.291501,
      "operating_cost_ex_sbc": 345.628899,
      "sbc": 10.273268,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-08-01",
      "end": "2022-10-31",
      "fiscal_year": "2022",
      "revenue": 446.198936,
      "ebit": 48.015515,
      "operating_cost_ex_sbc": 353.540641,
      "sbc": 10.918892,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2022-11-01",
      "end": "2023-01-31",
      "fiscal_year": "2023",
      "revenue": 458.217672,
      "ebit": 51.852701,
      "operating_cost_ex_sbc": 361.361914,
      "sbc": 11.564516,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2023-02-01",
      "end": "2023-04-30",
      "fiscal_year": "2023",
      "revenue": 470.236409,
      "ebit": 55.80306,
      "operating_cost_ex_sbc": 369.09272,
      "sbc": 12.210141,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2023-05-01",
      "end": "2023-07-31",
      "fiscal_year": "2023",
      "revenue": 482.255147,
      "ebit": 59.86659,
      "operating_cost_ex_sbc": 376.733059,
      "sbc": 12.855765,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2023-08-01",
      "end": "2023-10-31",
      "fiscal_year": "2023",
      "revenue": 494.273882,
      "ebit": 64.043294,
      "operating_cost_ex_sbc": 384.282928,
      "sbc": 13.50139,
      "nonrecurring_gain": 1.85
    },
    {
      "start": "2023-11-01",
      "end": "2024-01-31",
      "fiscal_year": "2024",
      "revenue": 506.29262,
      "ebit": 68.333168,
      "operating_cost_ex_sbc": 391.742329,
      "sbc": 14.147013,
      "nonrecurring_gain": 2.22
    },
    {
      "start": "2024-02-01",
      "end": "2024-04-30",
      "fiscal_year": "2024",
      "revenue": 518.311357,
      "ebit": 72.736216,
      "operating_cost_ex_sbc": 399.111263,
      "sbc": 14.792638,
      "nonrecurring_gain": 2.59
    },
    {
      "start": "2024-05-01",
      "end": "2024-07-31",
      "fiscal_year": "2024",
      "revenue": 530.330095,
      "ebit": 77.252435,
      "operating_cost_ex_sbc": 406.389729,
      "sbc": 15.438261,
      "nonrecurring_gain": 2.96
    },
    {
      "start": "2024-08-01",
      "end": "2024-10-31",
      "fiscal_year": "2024",
      "revenue": 542.348831,
      "ebit": 81.881827,
      "operating_cost_ex_sbc": 413.577726,
      "sbc": 16.083884,
      "nonrecurring_gain": 9.524529
    }
  ],
  "opening_nwc": 438.462856,
  "opening_deferred": 0,
  "opening_ppe": 386.57,
  "opening_rou": 0,
  "opening_debt": 249.4,
  "opening_retained_earnings": 199.52,
  "contributed_capital": 486.33,
  "opening_cash": 124.7,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 161.8,
    "price0": 5.204791705400001,
    "driver_add": [
      6.96,
      7.917,
      8.874,
      9.831
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.109,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 137.17,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      31.175,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.47,
      24.94,
      37.410000000000004,
      49.88
    ],
    "beta_unlevered": 0.88,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "service_frequency": [
      3.2,
      3.2800000000000002,
      3.3600000000000003,
      3.4400000000000004
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      58.8,
      62.8,
      66.8,
      70.8
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 124.7,
    "debt": 249.4,
    "investments": 18.705,
    "lease_liability": 0,
    "minority": 14.964,
    "valuation_cash_adjustment": 14.964,
    "shares": 119,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 11.9
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 495.059,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 486.33,
    "opening_cash": 124.7,
    "opening_operating_current_assets": 495.059,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 271.2,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge",
    "dual_asset_pool"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_asset_pool": "固定资产＋无形资产双资产池"
  },
  "c_structure": "risk_adjusted_pipeline",
  "c_structure_definition": "风险调整管线 DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge",
      "dual_asset_pool"
    ],
    "c": "risk_adjusted_pipeline"
  },
  "opening_nwc_last_fye": 438.462856,
  "opening_nwc_valuation_date": 401.534,
  "market": {
    "market_price": 34.84
  },
  "projects": {
    "project_atlas": {
      "commissioning_period": 2,
      "construction_capex": [
        136,
        0,
        0,
        0
      ],
      "project_revenue": [
        159.8,
        175.8,
        191.8,
        207.8
      ],
      "project_margin": 0.21,
      "project_da": [
        7,
        9,
        11,
        13
      ],
      "project_operating_capex": [
        8,
        8,
        8,
        8
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5
      ],
      "project_fcff": [
        -136,
        26.24227,
        29.81267,
        33.38307
      ],
      "success_probability": 0.67
    },
    "project_boreal": {
      "commissioning_period": 4,
      "construction_capex": [
        0,
        48,
        42,
        0
      ],
      "project_revenue": [
        182.8,
        198.8,
        214.8,
        230.8
      ],
      "project_margin": 0.245,
      "project_da": [
        7,
        9,
        11,
        13
      ],
      "project_operating_capex": [
        11,
        11,
        11,
        11
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5
      ],
      "project_fcff": [
        0,
        -165,
        36.25889,
        40.25769
      ],
      "success_probability": 0.53
    }
  },
  "event_public_facts": {
    "type": "commissioning_and_capex_rearrangement",
    "description": "Boreal 延后一个期间投产，建设支出移至 P2/P3；投产前仍无收入",
    "project": "project_boreal"
  },
  "event_type": "commissioning_and_capex_rearrangement"
}
```

</details>

##### D04_S2｜禾汐药业估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司价值由已有业务和两个在建项目组成，项目需按投产时间和成功概率做风险调整后估值。
公司财年截至每年 10 月 31 日，最近完整财年末为 `2024-10-31`，估值日 `2025-03-09` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
固定资产与无形资产分别滚动：期初＋新增－折旧/摊销＝期末；无形资产新增扣 FCFF，摊销加回，不能与固定资产混池。
项目投产期之前收入必须为零；建设期支出独立计入对应期间。项目经营 FCFF 单列后乘成功概率，概率不得加到 WACC。已有业务价值与项目风险调整现值分开列示后相加。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 2 步修改：项目延期投产与建设支出重排
Boreal 延后一个期间投产，建设支出移至 P2/P3；投产前仍无收入。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-2.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### step-3

<details><summary>D04/step-3｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D04_S3",
  "seed": 415179,
  "candidate_index": 3,
  "family": "D",
  "step": 3,
  "company": "禾汐药业",
  "dimension_selection": {
    "scenario": "楼宇监测装机服务",
    "difficulty": "L1: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "installed_base",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "dcf_only",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days",
    "intangible_pool"
  ],
  "selection_rationale": {
    "scenario": "楼宇监测装机服务要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": true
  },
  "business": {
    "driver": "installed_base",
    "unit": "千台",
    "price_unit": "百万元/台次",
    "description": "楼宇监测装机服务"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-03-09",
  "last_fy_end": "2024-10-31",
  "horizon": 4,
  "history": [
    {
      "start": "2022-05-01",
      "end": "2022-07-31",
      "fiscal_year": "2022",
      "revenue": 434.180198,
      "ebit": 44.291501,
      "operating_cost_ex_sbc": 345.628899,
      "sbc": 10.273268,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-08-01",
      "end": "2022-10-31",
      "fiscal_year": "2022",
      "revenue": 446.198936,
      "ebit": 48.015515,
      "operating_cost_ex_sbc": 353.540641,
      "sbc": 10.918892,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2022-11-01",
      "end": "2023-01-31",
      "fiscal_year": "2023",
      "revenue": 458.217672,
      "ebit": 51.852701,
      "operating_cost_ex_sbc": 361.361914,
      "sbc": 11.564516,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2023-02-01",
      "end": "2023-04-30",
      "fiscal_year": "2023",
      "revenue": 470.236409,
      "ebit": 55.80306,
      "operating_cost_ex_sbc": 369.09272,
      "sbc": 12.210141,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2023-05-01",
      "end": "2023-07-31",
      "fiscal_year": "2023",
      "revenue": 482.255147,
      "ebit": 59.86659,
      "operating_cost_ex_sbc": 376.733059,
      "sbc": 12.855765,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2023-08-01",
      "end": "2023-10-31",
      "fiscal_year": "2023",
      "revenue": 494.273882,
      "ebit": 64.043294,
      "operating_cost_ex_sbc": 384.282928,
      "sbc": 13.50139,
      "nonrecurring_gain": 1.85
    },
    {
      "start": "2023-11-01",
      "end": "2024-01-31",
      "fiscal_year": "2024",
      "revenue": 506.29262,
      "ebit": 68.333168,
      "operating_cost_ex_sbc": 391.742329,
      "sbc": 14.147013,
      "nonrecurring_gain": 2.22
    },
    {
      "start": "2024-02-01",
      "end": "2024-04-30",
      "fiscal_year": "2024",
      "revenue": 518.311357,
      "ebit": 72.736216,
      "operating_cost_ex_sbc": 399.111263,
      "sbc": 14.792638,
      "nonrecurring_gain": 2.59
    },
    {
      "start": "2024-05-01",
      "end": "2024-07-31",
      "fiscal_year": "2024",
      "revenue": 530.330095,
      "ebit": 77.252435,
      "operating_cost_ex_sbc": 406.389729,
      "sbc": 15.438261,
      "nonrecurring_gain": 2.96
    },
    {
      "start": "2024-08-01",
      "end": "2024-10-31",
      "fiscal_year": "2024",
      "revenue": 542.348831,
      "ebit": 81.881827,
      "operating_cost_ex_sbc": 413.577726,
      "sbc": 16.083884,
      "nonrecurring_gain": 9.524529
    }
  ],
  "opening_nwc": 438.462856,
  "opening_deferred": 0,
  "opening_ppe": 386.57,
  "opening_rou": 0,
  "opening_debt": 249.4,
  "opening_retained_earnings": 199.52,
  "contributed_capital": 486.33,
  "opening_cash": 124.7,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 161.8,
    "price0": 5.204791705400001,
    "driver_add": [
      6.96,
      7.917,
      8.874,
      9.831
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.109,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 137.17,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      31.175,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.47,
      24.94,
      37.410000000000004,
      49.88
    ],
    "beta_unlevered": 0.88,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "service_frequency": [
      3.2,
      3.2800000000000002,
      3.3600000000000003,
      3.4400000000000004
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      58.8,
      62.8,
      66.8,
      70.8
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 124.7,
    "debt": 249.4,
    "investments": 18.705,
    "lease_liability": 0,
    "minority": 14.964,
    "valuation_cash_adjustment": 14.964,
    "shares": 119,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 11.9
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 495.059,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 486.33,
    "opening_cash": 124.7,
    "opening_operating_current_assets": 495.059,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 271.2,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge",
    "dual_asset_pool"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_asset_pool": "固定资产＋无形资产双资产池"
  },
  "c_structure": "risk_adjusted_pipeline",
  "c_structure_definition": "风险调整管线 DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge",
      "dual_asset_pool"
    ],
    "c": "risk_adjusted_pipeline"
  },
  "opening_nwc_last_fye": 438.462856,
  "opening_nwc_valuation_date": 401.534,
  "market": {
    "market_price": 34.84
  },
  "projects": {
    "project_atlas": {
      "commissioning_period": 2,
      "construction_capex": [
        136,
        0,
        0,
        0
      ],
      "project_revenue": [
        159.8,
        175.8,
        191.8,
        207.8
      ],
      "project_margin": 0.21,
      "project_da": [
        7,
        9,
        11,
        13
      ],
      "project_operating_capex": [
        8,
        8,
        8,
        8
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5
      ],
      "project_fcff": [
        -136,
        26.24227,
        29.81267,
        33.38307
      ],
      "success_probability": 0.67
    },
    "project_boreal": {
      "commissioning_period": 4,
      "construction_capex": [
        0,
        48,
        42,
        0
      ],
      "project_revenue": [
        151.724,
        165.004,
        178.284,
        191.564
      ],
      "project_margin": 0.245,
      "project_da": [
        7,
        9,
        11,
        13
      ],
      "project_operating_capex": [
        11,
        11,
        11,
        11
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5
      ],
      "project_fcff": [
        0,
        -165,
        36.25889,
        40.25769
      ],
      "success_probability": 0.53
    }
  },
  "event_public_facts": {
    "type": "project_capex_and_scope_revision",
    "description": "项目规模重排，收入与建设开支按本步事件输入更新，概率继续作用于项目现金流",
    "project": "project_boreal"
  },
  "event_type": "project_capex_and_scope_revision"
}
```

</details>

##### D04_S3｜禾汐药业估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司价值由已有业务和两个在建项目组成，项目需按投产时间和成功概率做风险调整后估值。
公司财年截至每年 10 月 31 日，最近完整财年末为 `2024-10-31`，估值日 `2025-03-09` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
固定资产与无形资产分别滚动：期初＋新增－折旧/摊销＝期末；无形资产新增扣 FCFF，摊销加回，不能与固定资产混池。
项目投产期之前收入必须为零；建设期支出独立计入对应期间。项目经营 FCFF 单列后乘成功概率，概率不得加到 WACC。已有业务价值与项目风险调整现值分开列示后相加。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 3 步修改：项目规模与建设支出调整
项目规模重排，收入与建设开支按本步事件输入更新，概率继续作用于项目现金流。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-3.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### step-4

<details><summary>D04/step-4｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "D04_S4",
  "seed": 415179,
  "candidate_index": 3,
  "family": "D",
  "step": 4,
  "company": "禾汐药业",
  "dimension_selection": {
    "scenario": "楼宇监测装机服务",
    "difficulty": "L1: 依赖深度7，显式4期",
    "time_axis": "非自然财年+quarterly历史+实际天数残期",
    "business_driver": "installed_base",
    "valuation_mechanism": "dual_terminal",
    "accounting_basis": "应计无杠杆现金税",
    "output_mode": "dcf_only",
    "output_template": "fixed_outputs",
    "data_provision": "complete_frozen"
  },
  "enabled_modules": [
    "residual_period",
    "working_capital",
    "rolling_assets",
    "nwc_days",
    "intangible_pool"
  ],
  "selection_rationale": {
    "scenario": "楼宇监测装机服务要求独立的单位与价格口径",
    "time_axis": "10个季度披露期，需聚合财年/LTM并处理残期",
    "business_driver": "新增、流失、利用率或服务频次改变收入构造而非仅改增长率",
    "valuation_mechanism": "终值与折现时点依赖显式预测",
    "output_mode": "要求相应经营、债务或三表中间证据，结果键保持统一",
    "output_template": "固定坐标、语义发现或两者分流"
  },
  "source_and_choice": {
    "source": "本生成器按独立 SHA256 子种子生成场景参数、历史数据和预测假设",
    "choice": "索引保证场景/输出/时间覆盖，种子扰动规模与路径，模块约束过滤非法组合"
  },
  "time_axis": {
    "history_frequency": "quarterly",
    "midyear": false,
    "day_count": "actual/365",
    "terminal_at_last_fye": true
  },
  "accounting": {
    "normalized_history": true,
    "sbc_expense": true,
    "lease_in_debt": true
  },
  "business": {
    "driver": "installed_base",
    "unit": "千台",
    "price_unit": "百万元/台次",
    "description": "楼宇监测装机服务"
  },
  "output": {
    "template": "free_layout"
  },
  "valuation_date": "2025-03-09",
  "last_fy_end": "2024-10-31",
  "horizon": 4,
  "history": [
    {
      "start": "2022-05-01",
      "end": "2022-07-31",
      "fiscal_year": "2022",
      "revenue": 434.180198,
      "ebit": 44.291501,
      "operating_cost_ex_sbc": 345.628899,
      "sbc": 10.273268,
      "nonrecurring_gain": 0.0
    },
    {
      "start": "2022-08-01",
      "end": "2022-10-31",
      "fiscal_year": "2022",
      "revenue": 446.198936,
      "ebit": 48.015515,
      "operating_cost_ex_sbc": 353.540641,
      "sbc": 10.918892,
      "nonrecurring_gain": 0.37
    },
    {
      "start": "2022-11-01",
      "end": "2023-01-31",
      "fiscal_year": "2023",
      "revenue": 458.217672,
      "ebit": 51.852701,
      "operating_cost_ex_sbc": 361.361914,
      "sbc": 11.564516,
      "nonrecurring_gain": 0.74
    },
    {
      "start": "2023-02-01",
      "end": "2023-04-30",
      "fiscal_year": "2023",
      "revenue": 470.236409,
      "ebit": 55.80306,
      "operating_cost_ex_sbc": 369.09272,
      "sbc": 12.210141,
      "nonrecurring_gain": 1.11
    },
    {
      "start": "2023-05-01",
      "end": "2023-07-31",
      "fiscal_year": "2023",
      "revenue": 482.255147,
      "ebit": 59.86659,
      "operating_cost_ex_sbc": 376.733059,
      "sbc": 12.855765,
      "nonrecurring_gain": 1.48
    },
    {
      "start": "2023-08-01",
      "end": "2023-10-31",
      "fiscal_year": "2023",
      "revenue": 494.273882,
      "ebit": 64.043294,
      "operating_cost_ex_sbc": 384.282928,
      "sbc": 13.50139,
      "nonrecurring_gain": 1.85
    },
    {
      "start": "2023-11-01",
      "end": "2024-01-31",
      "fiscal_year": "2024",
      "revenue": 506.29262,
      "ebit": 68.333168,
      "operating_cost_ex_sbc": 391.742329,
      "sbc": 14.147013,
      "nonrecurring_gain": 2.22
    },
    {
      "start": "2024-02-01",
      "end": "2024-04-30",
      "fiscal_year": "2024",
      "revenue": 518.311357,
      "ebit": 72.736216,
      "operating_cost_ex_sbc": 399.111263,
      "sbc": 14.792638,
      "nonrecurring_gain": 2.59
    },
    {
      "start": "2024-05-01",
      "end": "2024-07-31",
      "fiscal_year": "2024",
      "revenue": 530.330095,
      "ebit": 77.252435,
      "operating_cost_ex_sbc": 406.389729,
      "sbc": 15.438261,
      "nonrecurring_gain": 2.96
    },
    {
      "start": "2024-08-01",
      "end": "2024-10-31",
      "fiscal_year": "2024",
      "revenue": 542.348831,
      "ebit": 81.881827,
      "operating_cost_ex_sbc": 413.577726,
      "sbc": 16.083884,
      "nonrecurring_gain": 9.524529
    }
  ],
  "opening_nwc": 411.77046,
  "opening_deferred": 0,
  "opening_ppe": 386.57,
  "opening_rou": 0,
  "opening_debt": 249.4,
  "opening_retained_earnings": 199.52,
  "contributed_capital": 486.33,
  "opening_cash": 124.7,
  "opening_sbc_reserve": 0.0,
  "assumptions": {
    "driver0": 161.8,
    "price0": 5.204791705400001,
    "driver_add": [
      6.96,
      7.917,
      8.874,
      9.831
    ],
    "driver_growth": [
      0.09,
      0.081,
      0.072,
      0.063
    ],
    "attrition_rate": [
      0.045,
      0.05,
      0.055,
      0.06
    ],
    "price_growth": [
      0.03,
      0.028,
      0.026,
      0.024
    ],
    "ebit_margin": [
      0.16,
      0.167,
      0.174,
      0.181
    ],
    "da_pct": [
      0.04,
      0.042,
      0.04,
      0.042
    ],
    "capex_pct": [
      0.061,
      0.065,
      0.069,
      0.061
    ],
    "nwc_pct": [
      0.18,
      0.186,
      0.192,
      0.18
    ],
    "tax": 0.235,
    "wacc": 0.109,
    "g": 0.022,
    "gordon_weight": 1.0,
    "exit_multiple": 8.7,
    "deferred_pct": [
      0.08,
      0.08,
      0.08,
      0.08
    ],
    "cogs_ratio": [
      0.48,
      0.48,
      0.48,
      0.48
    ],
    "dso": [
      47,
      48,
      49,
      50
    ],
    "dio": [
      62,
      61,
      60,
      59
    ],
    "dpo": [
      43,
      44,
      45,
      46
    ],
    "nol0": 137.17,
    "ppe_rate": 0.13,
    "rou_rate": 0.2,
    "lease_additions": [
      0,
      0,
      0,
      0
    ],
    "interest_rate": 0.052,
    "new_borrowing": [
      31.175,
      0,
      0,
      0
    ],
    "debt_repayment": [
      12.47,
      24.94,
      37.410000000000004,
      49.88
    ],
    "beta_unlevered": 0.88,
    "target_de": 0.27,
    "risk_free": 0.034,
    "erp": 0.049,
    "specific_premium": 0.006,
    "cost_of_debt": 0.053,
    "scenario": 1,
    "upside_demand_delta": 0.025,
    "downside_demand_delta": -0.025,
    "upside_margin_delta": 0.012,
    "downside_margin_delta": -0.014,
    "wacc_deltas": [
      -0.01,
      0,
      0.01
    ],
    "g_deltas": [
      -0.005,
      0,
      0.005
    ],
    "service_frequency": [
      3.2,
      3.2800000000000002,
      3.3600000000000003,
      3.4400000000000004
    ],
    "sbc_pct": [
      0.025,
      0.025,
      0.025,
      0.025
    ],
    "upside_reinvestment_delta": 0.12,
    "downside_reinvestment_delta": -0.1,
    "upside_wacc_delta": -0.005,
    "downside_wacc_delta": 0.006,
    "valuation_wacc_delta": 0.0075,
    "valuation_g_delta": 0.004,
    "intangible_additions": [
      58.8,
      62.8,
      66.8,
      70.8
    ],
    "intangible_rate": 0.16
  },
  "bridge": {
    "cash": 124.7,
    "debt": 249.4,
    "investments": 18.705,
    "lease_liability": 0,
    "minority": 14.964,
    "valuation_cash_adjustment": 14.964,
    "shares": 119,
    "rsus": 2.4,
    "options": 6.0,
    "strike": 7.0,
    "share_price": 11.9
  },
  "multi_step_events": [],
  "perturbations": [],
  "constraints": {
    "money_unit": "百万元",
    "share_unit": "百万股",
    "history": "原始披露期不得改写；SBC为经营成本；非经常收益不属于规范化EBIT",
    "fcff": "EBIT-无杠杆现金税+折旧摊销-资本开支-NWC增加；NOL按可用额与正EBIT孰低抵扣",
    "residual": "第一期按估值日至财年末实际天数占完整财年天数比例计入经营活动；余额NWC仍按完整年度驱动；首期NWC增量=期末余额-估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额",
    "deferred": "启用合同负债时，期末按完整年度核心收入比例；现金收款=本期收入+期末合同负债-估值日合同负债（后续减上期末）；FCFF营运资本扣除合同负债，资产负债表单列该负债。未启用模块的对应诊断输出为0",
    "inputs": "候选保留公开Inputs语义键；标量在C列，向量C/D/E…对应P1/P2/P3…，预测可自由布局但必须链接这些输入",
    "discount": "实际天数/365；年中法扣除现金流间隔的一半；终值在最后完整财年末",
    "terminal": "Gordon与退出终值分别计算，按gordon_weight加权；退出基于最后完整期EBITDA",
    "equity": "EV+现金+投资-借款-租赁负债-少数股权；库存股法期权增量加RSU",
    "debt": "利息按期初债务加半数新增借款乘实际天数/365；债务和资产独立滚动",
    "three_statements": "经营流动资产与合同负债分列。SBC已含于EBIT且为非现金费用，CFO加回并计入权益储备，FCFF不加回；净利润=EBIT-利息-利息后现金税，利息税盾与无杠杆现金税分开；现金仅由CFO、资本开支及融资滚动"
  },
  "opening_operating_current_assets": 495.059,
  "opening_balance_facts": {
    "basis": "独立历史资产负债事实：经营流动资产、合同负债、借款、租赁、现金、投资、留存收益、实收资本和少数股东权益分别列示；期初经营流动资产使已披露历史报表闭合，不参与任何预测期倒挤",
    "contributed_capital": 486.33,
    "opening_cash": 124.7,
    "opening_operating_current_assets": 495.059,
    "opening_sbc_reserve": 0.0
  },
  "opening_intangible": 271.2,
  "nwc_opening_basis": "last_fiscal_year_end",
  "b_items": [
    "fiscal_timing",
    "history_normalization",
    "residual_period",
    "actual_day_discount",
    "nwc_fye_open",
    "equity_bridge",
    "dual_asset_pool"
  ],
  "b_item_definitions": {
    "fiscal_timing": "非自然财年；估值日在财年中间",
    "history_normalization": "完整财年聚合、LTM，SBC 与非经常项规范化",
    "residual_period": "残余期＋完整年度预测（4–6 期）",
    "actual_day_discount": "实际天数，年中/期末折现，终值在最后完整财年末",
    "nwc_fye_open": "营运资本天数或比例法；首期 ΔNWC 用最近财年末余额",
    "equity_bridge": "现金、投资、债务、租赁、少数股权、库存股期权、RSU 股权桥",
    "dual_asset_pool": "固定资产＋无形资产双资产池"
  },
  "c_structure": "risk_adjusted_pipeline",
  "c_structure_definition": "风险调整管线 DCF",
  "structure": {
    "b": [
      "fiscal_timing",
      "history_normalization",
      "residual_period",
      "actual_day_discount",
      "nwc_fye_open",
      "equity_bridge",
      "dual_asset_pool"
    ],
    "c": "risk_adjusted_pipeline"
  },
  "opening_nwc_last_fye": 411.77046,
  "opening_nwc_valuation_date": 438.462856,
  "market": {
    "market_price": 34.84
  },
  "projects": {
    "project_atlas": {
      "commissioning_period": 2,
      "construction_capex": [
        136,
        0,
        0,
        0
      ],
      "project_revenue": [
        159.8,
        175.8,
        191.8,
        207.8
      ],
      "project_margin": 0.21,
      "project_da": [
        7,
        9,
        11,
        13
      ],
      "project_operating_capex": [
        8,
        8,
        8,
        8
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5
      ],
      "project_fcff": [
        -136,
        26.24227,
        29.81267,
        33.38307
      ],
      "success_probability": 0.67
    },
    "project_boreal": {
      "commissioning_period": 4,
      "construction_capex": [
        0,
        48,
        42,
        0
      ],
      "project_revenue": [
        151.724,
        165.004,
        178.284,
        191.564
      ],
      "project_margin": 0.245,
      "project_da": [
        7,
        9,
        11,
        13
      ],
      "project_operating_capex": [
        11,
        11,
        11,
        11
      ],
      "project_delta_nwc": [
        2,
        3,
        4,
        5
      ],
      "project_fcff": [
        0,
        -165,
        36.25889,
        40.25769
      ],
      "success_probability": 0.53
    }
  },
  "event_public_facts": {
    "type": "nwc_opening_basis_change",
    "description": "从本步起，首期 ΔNWC 改用最近财年末余额，保留估值日 NWC 事实用于勾稽",
    "opening_nwc_last_fye": 411.77046
  },
  "event_type": "nwc_opening_basis_change"
}
```

</details>

##### D04_S4｜禾汐药业估值建模

你是估值分析师。根据 `/app/inputs.xlsx` 与 `/app/inputs.json` 建立可追溯的活公式模型，保存为 `/app/output.xlsx`，另写 `/app/memo.md` 说明主要价值驱动与至少一个局限。禁止联网和外部工作簿链接。

公司价值由已有业务和两个在建项目组成，项目需按投产时间和成功概率做风险调整后估值。
公司财年截至每年 10 月 31 日，最近完整财年末为 `2024-10-31`，估值日 `2025-03-09` 落在财年中间。预测共 4 期：第 1 期是估值日到本财年末的残余期，只包含估值日后的经营活动，折旧摊销、资本开支及新增无形资产按残期活动比例计，期末营运资本仍按完整年度驱动；其后为完整财年。折现时间按实际天数/365 计算，采用期末惯例，终值落在最后一个完整财年末。
历史数据按季度提供，需自行汇总出最近完整财年和截至估值日的 LTM；SBC 作为经营成本保留，非经常收益从规范化 EBIT 中剔除。
营运资本按周转天数或收入比例驱动。第 1 期 ΔNWC 以 **最近财年末余额** 为期初，之后各期为相邻期末余额之差。合同负债如启用，只在营运资本中计一次，现金收款等于收入加合同负债增加。预测现金从 opening_cash 滚动。
从企业价值到每股价值：加现金、估值日现金调整和投资，减债务、租赁负债和少数股东权益；稀释股数包含 RSU 和按库存股法计算的期权。
固定资产与无形资产分别滚动：期初＋新增－折旧/摊销＝期末；无形资产新增扣 FCFF，摊销加回，不能与固定资产混池。
项目投产期之前收入必须为零；建设期支出独立计入对应期间。项目经营 FCFF 单列后乘成功概率，概率不得加到 WACC。已有业务价值与项目风险调整现值分开列示后相加。

##### 交付与输出键
在名称以 `Results` 开头的页中，将公开 `public_output_keys` 的每个键作为标签，右邻单元格放唯一数值活公式。结果页布局自由但键不得重复、不得粘贴常数。保留 `Inputs` 页原始语义键、历史事实及 C/D/E… 向量。金额百万元、股数百万股、比率小数。
隐藏检查会重算并执行两组经营、估值与股权桥扰动。

##### 第 4 步修改：营运资本期初口径变更
从本步起，首期 ΔNWC 改用最近财年末余额，保留估值日 NWC 事实用于勾稽。
读取 `/app/event.json`、`/app/event_inputs.xlsx` 与 `/app/event_inputs.json`，在上一步工作簿上修改受影响的依赖，原始 `History` 不得覆盖或删除。
先把上一步文件保存为 `/app/pre_step_output.xlsx`，再保存本步 `/app/output.xlsx`，并将本步快照保存到 `/app/snapshots/step-4.xlsx`。第 1 步同样保存 `/app/snapshots/step-1.xlsx`。

#### D04 选用的 rubric（57 条，权重合计 153；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 1 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须提交可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键须唯一数值 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | output/memo/快照须按名存在 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 须有Results页并保留Inputs页 |
| 01-HISTORY | 多步状态与业务重构 | 原始历史事实未被覆盖或删除 | rule | 主需 | 题面要求保留历史事实 |
| 08-RESTATE | 多步状态与业务重构 | 事件后的 FCFF 与股权桥使用更新后的依赖 | rule | 主需 | 事件后FCFF与股权桥需更新 |
| D-FINAL-VALUES | 多步状态与业务重构 | 最后一步工作簿的全部输出键与最终独立真值一致 | rule | 主需 | 最终输出键需与真值一致 |
| D-FINAL-LIVE | 多步状态与业务重构 | 最后一步结果仍为活公式，隐藏扰动可传导 | rule | 主需 | 要求活公式且隐藏扰动 |
| D-STEP-SNAPSHOT | 多步状态与业务重构 | 每一步都保存了独立快照 | rule | 主需 | 要求每步保存独立快照 |
| D-STEP-VALUES | 多步状态与业务重构 | 每一步快照的输出与该步独立真值一致 | rule | 主需 | 每步快照需正确 |
| D-STEP-SCOPE | 多步状态与业务重构 | 每一步只修改该步要求涉及的依赖，未触及的输出保持不变 | rule | 次需 | 多步修改须限定范围 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 季度历史需聚合非自然财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 题面要求截至估值日LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 非经常收益不入规范化EBIT |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | SBC作为经营成本 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 装机存量驱动滚动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 平均装机基数与残期比例 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续期ΔNWC期末差与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期用最近财年末余额 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 启用NWC天数法 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 题面要求无形资产独立滚动 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 题面要求固定资产与无形资产分池滚动 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为核心 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 题面要求实际天数期末折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | spec估值机制为双终值 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值在最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 题面含库存股期权与RSU |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值为DCF输出 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题面要求无形资产扣减加回 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅含估值日后活动 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为唯一活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 隐藏检查会重算比对 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示两组扰动之一 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示两组扰动之二 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部工作簿链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 结果页为自由布局 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求提交memo.md |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 题面要求可追溯模型 |
| C-PIPE-TIMING | 经营预测 | 未投产或未上市项目在投产日前不产生收入 | rule | 主需 | 题面要求投产前收入为零 |
| C-PIPE-CAPEX | 经营预测 | 建设期支出与投产期收入分别建模并计入对应期间 | rule | 主需 | 建设期支出独立计入对应期 |
| C-PIPE-PROB | 经营预测 | 成功概率作用于项目现金流或项目价值，不通过调整 WACC 体现 | rule | 主需 | 概率乘现金流不加WACC |
| C-PIPE-SUM | 经营预测 | 公司价值等于各项目风险调整价值之和加已有业务价值 | rule | 主需 | 已有业务与项目价值分列相加 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 输入值须与输入包一致 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 财年聚合与LTM推导 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 季度/财年/LTM不得混用 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 预测4期加残期 |
| X-IN-008 | 历史与会计口径 | 同一指标在历史列与预测列使用相同的行项定义，未改变其构成项。 | rule | 主需 | 规范化EBIT口径一致 |
| X-IN-009 | 历史与会计口径 | 历史实际值单元格保留原始数值或原始公式，未被预测公式覆盖。 | rule | 主需 | 须保留历史事实 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | 双终值须共用显性期现值 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 历史含非经常收益需规范化 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 实际天数折现期需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF各组成项需独立列示 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 双终值需引用可见单元格 |
| 08-OLD | 多步状态与业务重构 | 后续工作簿保留事件前原始输入与状态 | rule | 主需 | 程序强制必选项 |

### E01（E）

<details><summary>E01｜完整 spec</summary>

```json
{
  "source_task_id": "E01",
  "ticker": "MSFT",
  "cut": "2024-06-30",
  "asof": "2024-08-29",
  "variant": "annual",
  "shape": "xlsx",
  "sector": "软件与云计算",
  "task_id": "E01",
  "family": "E",
  "years": 5,
  "min_paths": 5000,
  "mc_seed": 1830,
  "schema_version": "dcf-v3-task-v1",
  "language": "zh-CN",
  "required_artifacts": [
    "model.xlsx",
    "simulate.py",
    "simulation.json",
    "memo.md"
  ],
  "output_keys": [
    "hist_revenue_fy0",
    "hist_ebit_fy0",
    "hist_eps_fy0",
    "revenue_y1",
    "ebit_y1",
    "eps_y1",
    "fcff_y1",
    "discount_factor_y1",
    "revenue_y2",
    "ebit_y2",
    "eps_y2",
    "fcff_y2",
    "discount_factor_y2",
    "revenue_y3",
    "ebit_y3",
    "eps_y3",
    "fcff_y3",
    "discount_factor_y3",
    "revenue_y4",
    "ebit_y4",
    "eps_y4",
    "fcff_y4",
    "discount_factor_y4",
    "revenue_y5",
    "ebit_y5",
    "eps_y5",
    "fcff_y5",
    "discount_factor_y5",
    "wacc",
    "terminal_growth",
    "enterprise_value",
    "equity_value",
    "diluted_shares",
    "value_per_share",
    "mc_n",
    "mc_p10",
    "mc_p25",
    "mc_p50",
    "mc_p75",
    "mc_p90",
    "mc_mean"
  ],
  "frozen_source_sha256": {
    "pack": "4e8928acbe31cb676f5d9db8129b43be6e4cc97d2d238458b708cadf5b28c30c",
    "companyfacts": "8c1903c041f5c27e86ed15f37debb1f41882b7904bba129ef9edc76478b1e8ea",
    "treasury": "7e66e6c4d14dec358ccbaadd9b6d11d66e74c141e0df9caa8879d0f634668556"
  },
  "future_data_role": "diagnostic_only",
  "mechanical_check_families": [
    "historical",
    "forecast",
    "valuation",
    "formula",
    "simulation"
  ],
  "nonmechanical_status": "not_selected_not_scored_here"
}
```

</details>

##### 微软：云业务需求、资本开支与开放预测

你是信息截止日 **2024-08-29** 的估值分析师。只可使用 `/app/data/inputs.json` 和等价的 `/app/data/frozen_history.xlsx`；本题离线。禁止使用截止日后的披露、当前股价、现成目标价或市场一致预期。不存在唯一正确的开放假设或目标每股价值。

##### 历史证据与五年模型

最近完整财年截止 2024-06-30。行业分析要求：结合商业云需求、数据中心产能和利用率、人工智能基础设施折旧以及承诺需求的期限分析。不要把所有收入视为同一个同质化订阅池。

建立五个财年的收入、经营利润（EBIT）、稀释 EPS 与 FCFF。解释收入增长、利润率、税率、D&A、CapEx、营运资本和股权桥的来源与适用日期。金额为百万美元，股数为百万股，EPS/每股价值为美元，比率为小数。股份支付是经营成本，不得加回 FCFF。经营 NWC = 流动资产−现金−短期投资−(流动负债−当期债务)。净债务只含当期及非当期债务；股权价值 = 企业价值 + 现金及短期投资 − 净债务。

每年 `reinvestment_component = D&A − CapEx − ΔNWC`；`FCFF = EBIT×(1−税率) + reinvestment_component`；`discount_factor = 1/(1+WACC)^discount_years`。终值采用 Gordon 公式，以 FY5 的 FCFF 为基期并折现到估值日；WACC 必须大于 g。年度变体折现年数为 1,2,3,4,5，FY1 是估值日后第一个完整预测年度。

##### 候选自写 Monte Carlo

编写并实际运行 `/app/output/simulate.py`：
`python3 /app/output/simulate.py --input /app/data/inputs.json --model /app/output/model.xlsx --output /app/output/simulation.json`

至少生成 **5,000 条有效路径**，声明 seed **1830**，采用可复现伪随机数发生器。分别抽样收入增长、EBIT 利润率、再投资强度和折现率，不能直接抽每股价值或股价。声明支持的分布（triangular/uniform/normal/lognormal/beta）、数值参数、单位和有限上下界；保留合法抽样并单列拒绝数。增长与利润率要有非零相关性，或说明独立性的证据及局限；给出声明的相关矩阵及所有四个驱动的实际相关矩阵。模拟边界应能从历史波动或明确的压力情景推导。

`simulation.json` 顶层必须含：`seed`、`n_valid`、`n_rejected`、`method`、`drivers`、`dependence`、`realized_correlation`、`trials`、`statistics`、`percentile_convention`、`limitations`。drivers 以四个精确键 `revenue_growth`、`ebit_margin`、`reinvestment_intensity`、`discount_rate` 为索引，每项含 distribution、parameters、unit、bounds。dependence 含 `ordered_names`、4×4 `matrix`，或 `type: independence` 与 explanation。每条 trial 含 `path_id`、上述四个驱动、`value_per_share` 和五行 `trajectory`；每年含 `year/revenue/ebit/reinvestment/fcff/discount_factor`。路径 reinvestment 是资本开支加营运资本增加减 D&A（正值消耗现金），故 `fcff=ebit×(1−tax)−reinvestment`。增长与利润率在一条路径内保持不变；再投资=当年 trajectory.revenue×reinvestment_intensity。终值以 FY5 路径 FCFF 计算，采用该路径折现率。每条路径必须可由评分器独立重算，不能只提交摘要。分位数采用 `(N−1)q` 线性插值或 `nearest_r` 并如实声明。

##### 交付物与说明

提交 `/app/output/model.xlsx`：保留公开工作簿的 `Outputs` 页，并建立 `Assumptions`、`Forecast`、`DCF` 页。Outputs 的 A 列为题给键，C 列必须是活公式；历史、五个预测年度、估值输出均链接到模型，模拟统计链接到 `MC_Trials`。Assumptions 的 A/B 列分别放键和数值，至少包括：`initial_growth`、`terminal_revenue_growth`、`steady_ebit_margin`、`tax_rate`、`da_to_revenue`、`capex_to_revenue`、`nwc_to_revenue`、`interest_rate`、`wacc`、`terminal_growth`、`net_debt`、`cash_and_investments`、`diluted_shares`。Forecast 的 A 列为键，C:G 为 FY1–FY5；必须包含 revenue、ebit、eps、da、capex、delta_nwc、reinvestment_component、fcff、discount_factor。经营预测、再投资、DCF 和股权桥不能粘贴固定结果；评分会实际修改 WACC 与 g 并重算。

另交 `simulation.json`、`simulate.py`、`memo.md`。memo 不超过 700 个空白分隔词，中文撰写：逐项给出至少三个历史行名/期间/数值/SEC_XBRL 来源，说明可复现的假设推导、公司特定经营因果链、再投资理由、模拟边界与相关性选择，并明确预测不确定性及模型局限。模拟区间是模型条件 DCF 分布，不是股价预测。评分器会重新执行模拟器并独立检查分布、相关性、全部路径算术和分位数；未来实际值及未来股价只在隐藏诊断中出现，不进入评分。

#### E01 选用的 rubric（58 条，权重合计 140；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 4 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| E-deliver_model | 交付与来源完整性 | The required primary model artifact exists and parses. | rule | 主需 | model.xlsx须存在可解析 |
| E-deliver_simulator | 交付与来源完整性 | The candidate-owned simulate.py exists and parses. | rule | 主需 | simulate.py须存在可解析 |
| E-deliver_trials | 交付与来源完整性 | simulation.json exists and has the required top-level schema. | rule | 主需 | simulation.json顶层schema |
| E-deliver_memo | 交付与来源完整性 | memo.md exists and is no more than 700 words. | rule | 次需 | memo存在且≤700词 |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | Outputs须含全部题给键 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 题面规定单位及drivers单位 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 指定工作表名称须存在 |
| E-hist_revenue | 历史与会计口径 | FY0 revenue equals the frozen SEC fact within 0.1%. | rule | 主需 | FY0收入须符合SEC事实 |
| E-hist_ebit | 历史与会计口径 | FY0 EBIT equals the frozen SEC fact within 0.1%. | rule | 主需 | FY0 EBIT须符合SEC事实 |
| E-hist_eps | 历史与会计口径 | FY0 diluted EPS equals the frozen SEC fact within 0.1%. | rule | 次需 | FY0稀释EPS须符合SEC事实 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面明确SBC不得加回 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | EBIT按各期利润率计算 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC期初期末与符号 |
| E-forecast_revenue | 经营预测 | Each of the five full-year revenue forecasts is positive and finite. | rule | 次需 | 五年收入正且有限 |
| E-forecast_ebit | 经营预测 | Each forecast EBIT is finite and its implied margin is between -50% and 70%. | rule | 次需 | EBIT有限且利润率合理 |
| E-forecast_reinvestment | 经营预测 | Each reinvestment component equals D&A minus CapEx minus the change in NWC. | rule | 主需 | 再投资组件公式核对 |
| E-llm_business_chain | 经营预测 | The forecast states a company-specific operating causal chain that can explain the direction of revenue and EBIT, rather than generic extrapolation. | llm | 主需 | memo要求公司经营因果链 |
| E-llm_reinvestment_reasoning | 经营预测 | The reasoning explains why the operating growth and margin case requires the modeled D&A, capital expenditure and working-capital reinvestment. | llm | 主需 | memo要求再投资理由 |
| E-dcf_fcff | DCF与估值桥 | Each FCFF equals EBIT times one minus tax plus the reinvestment component. | rule | 主需 | 题面明确FCFF公式 |
| E-dcf_discount | DCF与估值桥 | Each discount factor equals one over one plus WACC raised to its stated actual-year fraction. | rule | 主需 | 折现因子公式明确 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | Gordon终值基于FY5折现 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值为必需输出 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | Outputs C列须为活公式 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 重算需无外链和错误值 |
| E-formula_perturb_wacc | 公式与模型工程 | A +0.5 percentage-point WACC perturbation decreases enterprise value. | rule | 次需 | 评分会修改WACC重算 |
| E-formula_perturb_g | 公式与模型工程 | A +0.2 percentage-point terminal-growth perturbation increases enterprise value. | rule | 次需 | 评分会修改g重算 |
| X-FM-001 | 公式与模型工程 | 题面要求集中管理的每个业务假设均在假设区拥有独立的可见输入单元格。 | rule | 主需 | Assumptions页须列必需键 |
| X-FM-003 | 公式与模型工程 | 同一业务或估值假设仅有一个权威输入单元格，每个使用该假设的下游公式均可追溯至该单元格。 | rule | 主需 | 假设须单一来源可追溯 |
| X-FM-004 | 公式与模型工程 | 下游行项通过工作簿内活引用取得已在上游模块计算的对应值，未另行重填或独立重算。 | rule | 主需 | 输出须链接模型与MC_Trials |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | Forecast C:G期间对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 估值链不得有循环引用 |
| 07-PATHS | 开放假设与模拟 | 模拟路径满足数量、抽样和相关性约束 | rule | 主需 | 有效路径≥5000 |
| 07-QUANTILE | 开放假设与模拟 | 模拟分位数由试验样本独立计算 | rule | 主需 | 分位数需由路径独立重算 |
| E-mc_seed | 开放假设与模拟 | The declared seed equals the task seed. | rule | 次需 | 声明seed须为1830 |
| E-mc_distributions | 开放假设与模拟 | Every required driver has a supported distribution, legal numeric parameters, declared bounds, and sample statistics within method-aware tolerances. | rule | 主需 | 四驱动分布、参数与边界 |
| E-mc_dependence | 开放假设与模拟 | The realized correlation matrix agrees with the declared dependence structure, or the independence explanation is supported by realized cross-driver correlations. | rule | 主需 | 实际相关与声明结构一致 |
| E-mc_recompute | 开放假设与模拟 | Every sampled path's DCF value independently recomputes from its drivers and the deterministic model within 0.5%. | rule | 主需 | 逐路径DCF值可重算 |
| E-mc_not_degenerate | 开放假设与模拟 | The value distribution is non-degenerate and has more than 100 distinct values. | rule | 次需 | 价值分布须非退化 |
| E-llm_driver_derivation | 开放假设与模拟 | The cited historical observations are explicitly connected to each material forecast driver by a reproducible derivation, not merely listed. | llm | 主需 | 历史数据可推导出驱动 |
| E-agent_distribution_rationale | 开放假设与模拟 | The selected uncertainty bounds and dependence rationale are justified from supplied historical evidence without invoking unavailable post-cutoff information. | agent | 主需 | 边界与相关性有历史依据 |
| E-evidence_numeric_citations | 表达与专业可用性 | At least three memo citations identify a real source, historical period, and value matching the frozen fact. | rule | 次需 | 题面要求三条历史数据引用 |
| E-evidence_limits | 表达与专业可用性 | The memo explicitly discloses forecast uncertainty and the independence or correlation choice. | rule | 次需 | 要求披露不确定性与相关性选择 |
| E-agent_interval_interpretation | 表达与专业可用性 | The interpretation distinguishes model-implied FCFF/DCF dispersion from a market-price forecast and states material simulation limitations. | agent | 次需 | 要求区分DCF分布与股价预测 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 题面给定NWC与净债务公式 |
| X-IN-004 | 历史与会计口径 | 每项模型输入的适用日期均不晚于题面规定的信息截止日。 | agent | 主需 | 信息截止日2024-08-29 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 历史须用财年数据 |
| X-IN-006 | 历史与会计口径 | 估值桥或比较价格使用题面基准日当天或之前最近一个可用值。 | rule | 主需 | 股权桥现金债务取时点值 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 指定五个财年预测期 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| X-TA-003 | 表达与专业可用性 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | llm | 次需 | 题面指定SBC、NWC、净债务处理 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 年度折现年数须可见 |
| X-TA-005 | 表达与专业可用性 | 用于外推或推导预测的历史锚定期间数值在模型中可见。 | agent | 次需 | 预测由历史锚定推导 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值须引用单元格 |
| X-TA-009 | 表达与专业可用性 | 每个开放性预测假设均有书面推导，包含历史观察值及由该观察值到假设值的计算或映射关系。 | llm | 次需 | 开放假设须书面推导 |
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 程序强制必选项 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 程序强制必选项 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 程序强制必选项 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 程序强制必选项 |

### E02（E）

<details><summary>E02｜完整 spec</summary>

```json
{
  "source_task_id": "E02",
  "ticker": "DE",
  "cut": "2024-10-27",
  "asof": "2024-12-26",
  "variant": "annual",
  "shape": "json",
  "sector": "农业机械周期",
  "task_id": "E02",
  "family": "E",
  "years": 5,
  "min_paths": 5000,
  "mc_seed": 1931,
  "schema_version": "dcf-v3-task-v1",
  "language": "zh-CN",
  "required_artifacts": [
    "model.json",
    "simulate.py",
    "simulation.json",
    "memo.md",
    "recompute.py"
  ],
  "output_keys": [
    "hist_revenue_fy0",
    "hist_ebit_fy0",
    "hist_eps_fy0",
    "revenue_y1",
    "ebit_y1",
    "eps_y1",
    "fcff_y1",
    "discount_factor_y1",
    "revenue_y2",
    "ebit_y2",
    "eps_y2",
    "fcff_y2",
    "discount_factor_y2",
    "revenue_y3",
    "ebit_y3",
    "eps_y3",
    "fcff_y3",
    "discount_factor_y3",
    "revenue_y4",
    "ebit_y4",
    "eps_y4",
    "fcff_y4",
    "discount_factor_y4",
    "revenue_y5",
    "ebit_y5",
    "eps_y5",
    "fcff_y5",
    "discount_factor_y5",
    "wacc",
    "terminal_growth",
    "enterprise_value",
    "equity_value",
    "diluted_shares",
    "value_per_share",
    "mc_n",
    "mc_p10",
    "mc_p25",
    "mc_p50",
    "mc_p75",
    "mc_p90",
    "mc_mean"
  ],
  "frozen_source_sha256": {
    "pack": "de95c0201e4dccf3afb45a82d7974a124a167f9de16ed44d3911a97c75211e59",
    "companyfacts": "b845478ca3e2c2a83471cfb92524b33d83ec47fd3c1c68614f3f2487f1606b6c",
    "treasury": "7e66e6c4d14dec358ccbaadd9b6d11d66e74c141e0df9caa8879d0f634668556"
  },
  "future_data_role": "diagnostic_only",
  "mechanical_check_families": [
    "historical",
    "forecast",
    "valuation",
    "formula",
    "simulation"
  ],
  "nonmechanical_status": "not_selected_not_scored_here"
}
```

</details>

##### 迪尔：农机周期与开放预测

你是信息截止日 **2024-12-26** 的估值分析师。只可使用 `/app/data/inputs.json` 和等价的 `/app/data/frozen_history.xlsx`；本题离线。禁止使用截止日后的披露、当前股价、现成目标价或市场一致预期。不存在唯一正确的开放假设或目标每股价值。

##### 历史证据与五年模型

最近完整财年截止 2024-10-27。行业分析要求：结合设备销量、价格与产品组合、生产库存、更新周期及经销商库存分析；区分周期性收入/利润率风险与长期再投资需求。

建立五个财年的收入、经营利润（EBIT）、稀释 EPS 与 FCFF。解释收入增长、利润率、税率、D&A、CapEx、营运资本和股权桥的来源与适用日期。金额为百万美元，股数为百万股，EPS/每股价值为美元，比率为小数。股份支付是经营成本，不得加回 FCFF。经营 NWC = 流动资产−现金−短期投资−(流动负债−当期债务)。净债务只含当期及非当期债务；股权价值 = 企业价值 + 现金及短期投资 − 净债务。

每年 `reinvestment_component = D&A − CapEx − ΔNWC`；`FCFF = EBIT×(1−税率) + reinvestment_component`；`discount_factor = 1/(1+WACC)^discount_years`。终值采用 Gordon 公式，以 FY5 的 FCFF 为基期并折现到估值日；WACC 必须大于 g。年度变体折现年数为 1,2,3,4,5，FY1 是估值日后第一个完整预测年度。

##### 候选自写 Monte Carlo

编写并实际运行 `/app/output/simulate.py`：
`python3 /app/output/simulate.py --input /app/data/inputs.json --model /app/output/model.json --output /app/output/simulation.json`

至少生成 **5,000 条有效路径**，声明 seed **1931**，采用可复现伪随机数发生器。分别抽样收入增长、EBIT 利润率、再投资强度和折现率，不能直接抽每股价值或股价。声明支持的分布（triangular/uniform/normal/lognormal/beta）、数值参数、单位和有限上下界；保留合法抽样并单列拒绝数。增长与利润率要有非零相关性，或说明独立性的证据及局限；给出声明的相关矩阵及所有四个驱动的实际相关矩阵。模拟边界应能从历史波动或明确的压力情景推导。

`simulation.json` 顶层必须含：`seed`、`n_valid`、`n_rejected`、`method`、`drivers`、`dependence`、`realized_correlation`、`trials`、`statistics`、`percentile_convention`、`limitations`。drivers 以四个精确键 `revenue_growth`、`ebit_margin`、`reinvestment_intensity`、`discount_rate` 为索引，每项含 distribution、parameters、unit、bounds。dependence 含 `ordered_names`、4×4 `matrix`，或 `type: independence` 与 explanation。每条 trial 含 `path_id`、上述四个驱动、`value_per_share` 和五行 `trajectory`；每年含 `year/revenue/ebit/reinvestment/fcff/discount_factor`。路径 reinvestment 是资本开支加营运资本增加减 D&A（正值消耗现金），故 `fcff=ebit×(1−tax)−reinvestment`。增长与利润率在一条路径内保持不变；再投资=当年 trajectory.revenue×reinvestment_intensity。终值以 FY5 路径 FCFF 计算，采用该路径折现率。每条路径必须可由评分器独立重算，不能只提交摘要。分位数采用 `(N−1)q` 线性插值或 `nearest_r` 并如实声明。

##### 交付物与说明

提交 `/app/output/model.json`，包含对象 `historical`、`assumptions`、`forecast`、`valuation`、`simulation_summary`。historical 使用 Outputs 同名历史键；assumptions 至少包含 `initial_growth`、`terminal_revenue_growth`、`steady_ebit_margin`、`tax_rate`、`da_to_revenue`、`capex_to_revenue`、`nwc_to_revenue`、`interest_rate`、`wacc`、`terminal_growth`、`net_debt`、`cash_and_investments`、`diluted_shares`。forecast 每年包含 `revenue_y1`…`revenue_y5`、`ebit_y*`、`eps_y*`、`da_y*`、`capex_y*`、`delta_nwc_y*`、`reinvestment_component_y*`、`fcff_y*`、`discount_factor_y*`；H1 变体另含实际/残余键。valuation 包含 WACC、g、税率、净债务、现金及投资、稀释股数、企业/股权/每股价值、`discount_years` 五元素数组和 `terminal_year_fcff`；simulation_summary 含 `n_valid`、`p10/p25/p50/p75/p90/mean`。另交 `/app/output/recompute.py`，接受 `--input INPUT --model MODEL --output DIR` 并写 `recomputed.json`。它必须从上述经营假设和公开历史重建每年收入、EBIT、再投资及估值，不得只回显 forecast/valuation 的既有结果。评分会修改经营假设和 WACC/g 后独立执行。

另交 `simulation.json`、`simulate.py`、`memo.md`。memo 不超过 700 个空白分隔词，中文撰写：逐项给出至少三个历史行名/期间/数值/SEC_XBRL 来源，说明可复现的假设推导、公司特定经营因果链、再投资理由、模拟边界与相关性选择，并明确预测不确定性及模型局限。模拟区间是模型条件 DCF 分布，不是股价预测。评分器会重新执行模拟器并独立检查分布、相关性、全部路径算术和分位数；未来实际值及未来股价只在隐藏诊断中出现，不进入评分。

#### E02 选用的 rubric（54 条，权重合计 132；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 6 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 输出键须齐全且为数值 |
| E-deliver_model | 交付与来源完整性 | The required primary model artifact exists and parses. | rule | 主需 | model.json须存在可解析 |
| E-deliver_simulator | 交付与来源完整性 | The candidate-owned simulate.py exists and parses. | rule | 主需 | simulate.py须存在可解析 |
| E-deliver_trials | 交付与来源完整性 | simulation.json exists and has the required top-level schema. | rule | 主需 | simulation.json顶层schema |
| E-deliver_memo | 交付与来源完整性 | memo.md exists and is no more than 700 words. | rule | 次需 | memo存在且≤700词 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 含recompute.py五文件齐全 |
| E-hist_revenue | 历史与会计口径 | FY0 revenue equals the frozen SEC fact within 0.1%. | rule | 主需 | FY0收入须核对SEC事实 |
| E-hist_ebit | 历史与会计口径 | FY0 EBIT equals the frozen SEC fact within 0.1%. | rule | 主需 | FY0 EBIT须核对SEC事实 |
| E-hist_eps | 历史与会计口径 | FY0 diluted EPS equals the frozen SEC fact within 0.1%. | rule | 次需 | FY0稀释EPS须核对 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面明确SBC不得加回 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各年EBIT按当期利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC期初期末与符号 |
| E-forecast_revenue | 经营预测 | Each of the five full-year revenue forecasts is positive and finite. | rule | 次需 | 五年收入为正且有限 |
| E-forecast_ebit | 经营预测 | Each forecast EBIT is finite and its implied margin is between -50% and 70%. | rule | 次需 | EBIT利润率合理区间 |
| E-forecast_reinvestment | 经营预测 | Each reinvestment component equals D&A minus CapEx minus the change in NWC. | rule | 主需 | 再投资公式题面明定 |
| E-llm_business_chain | 经营预测 | The forecast states a company-specific operating causal chain that can explain the direction of revenue and EBIT, rather than generic extrapolation. | llm | 主需 | memo要求公司因果链 |
| E-llm_reinvestment_reasoning | 经营预测 | The reasoning explains why the operating growth and margin case requires the modeled D&A, capital expenditure and working-capital reinvestment. | llm | 主需 | memo要求再投资理由 |
| E-dcf_fcff | DCF与估值桥 | Each FCFF equals EBIT times one minus tax plus the reinvestment component. | rule | 主需 | 题面规定FCFF公式 |
| E-dcf_discount | DCF与估值桥 | Each discount factor equals one over one plus WACC raised to its stated actual-year fraction. | rule | 主需 | 折现因子按1..5年计算 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | Gordon终值以FY5为基并折现 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值=股权/稀释股数 |
| E-formula_perturb_wacc | 公式与模型工程 | A +0.5 percentage-point WACC perturbation decreases enterprise value. | rule | 次需 | WACC上调应降低企业价值 |
| E-formula_perturb_g | 公式与模型工程 | A +0.2 percentage-point terminal-growth perturbation increases enterprise value. | rule | 次需 | g上调应提高企业价值 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 模拟器不得硬编码假设常数 |
| 07-ASSUME | 开放假设与模拟 | 开放假设有可追溯的证据和适用日期 | llm | 主需 | 要求假设来源与适用日期 |
| 07-PATHS | 开放假设与模拟 | 模拟路径满足数量、抽样和相关性约束 | rule | 主需 | 至少5000条有效路径 |
| 07-QUANTILE | 开放假设与模拟 | 模拟分位数由试验样本独立计算 | rule | 主需 | 分位数需由路径独立重算 |
| E-mc_seed | 开放假设与模拟 | The declared seed equals the task seed. | rule | 次需 | 声明seed须为1931 |
| E-mc_distributions | 开放假设与模拟 | Every required driver has a supported distribution, legal numeric parameters, declared bounds, and sample statistics within method-aware tolerances. | rule | 主需 | 四驱动分布参数与边界 |
| E-mc_dependence | 开放假设与模拟 | The realized correlation matrix agrees with the declared dependence structure, or the independence explanation is supported by realized cross-driver correlations. | rule | 主需 | 相关矩阵声明与实现一致 |
| E-mc_recompute | 开放假设与模拟 | Every sampled path's DCF value independently recomputes from its drivers and the deterministic model within 0.5%. | rule | 主需 | 逐路径DCF算术重算 |
| E-mc_not_degenerate | 开放假设与模拟 | The value distribution is non-degenerate and has more than 100 distinct values. | rule | 次需 | 价值分布非退化 |
| E-llm_driver_derivation | 开放假设与模拟 | The cited historical observations are explicitly connected to each material forecast driver by a reproducible derivation, not merely listed. | llm | 主需 | 历史数据到驱动的推导 |
| E-agent_distribution_rationale | 开放假设与模拟 | The selected uncertainty bounds and dependence rationale are justified from supplied historical evidence without invoking unavailable post-cutoff information. | agent | 主需 | 边界与相关性须有历史依据 |
| E-evidence_numeric_citations | 表达与专业可用性 | At least three memo citations identify a real source, historical period, and value matching the frozen fact. | rule | 次需 | 题面要求三处历史数值引用 |
| E-evidence_limits | 表达与专业可用性 | The memo explicitly discloses forecast uncertainty and the independence or correlation choice. | rule | 次需 | 要求披露不确定性与相关性选择 |
| E-agent_interval_interpretation | 表达与专业可用性 | The interpretation distinguishes model-implied FCFF/DCF dispersion from a market-price forecast and states material simulation limitations. | agent | 次需 | 要求区分DCF分布与股价预测 |
| X-IN-002 | 历史与会计口径 | 题面指定的恒定输入在其每个适用期间均被原样采用，不出现未经指定的期间变化。 | rule | 主需 | 路径内增长与利润率须恒定 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | NWC与净债务公式已指定 |
| X-IN-004 | 历史与会计口径 | 每项模型输入的适用日期均不晚于题面规定的信息截止日。 | agent | 主需 | 信息截止日2024-12-26 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 历史须用完整财年口径 |
| X-IN-006 | 历史与会计口径 | 估值桥或比较价格使用题面基准日当天或之前最近一个可用值。 | rule | 主需 | 债务现金须取基准日前值 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 五个财年预测期 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| X-TA-003 | 表达与专业可用性 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | llm | 次需 | SBC、NWC、净债务口径指定 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 要求discount_years数组 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF分项键为必需 |
| X-TA-009 | 表达与专业可用性 | 每个开放性预测假设均有书面推导，包含历史观察值及由该观察值到假设值的计算或映射关系。 | llm | 次需 | 开放假设需书面推导 |
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 程序强制必选项 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 程序强制必选项 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 程序强制必选项 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 程序强制必选项 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 程序强制必选项 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 程序强制必选项 |

### E03（E）

<details><summary>E03｜完整 spec</summary>

```json
{
  "source_task_id": "E03",
  "ticker": "TGT",
  "cut": "2025-02-01",
  "asof": "2025-09-16",
  "variant": "h1",
  "shape": "xlsx",
  "sector": "零售与季节性营运资本",
  "task_id": "E03",
  "family": "E",
  "years": 5,
  "min_paths": 5000,
  "mc_seed": 2032,
  "schema_version": "dcf-v3-task-v1",
  "language": "zh-CN",
  "required_artifacts": [
    "model.xlsx",
    "simulate.py",
    "simulation.json",
    "memo.md"
  ],
  "output_keys": [
    "hist_revenue_fy0",
    "hist_ebit_fy0",
    "hist_eps_fy0",
    "actual_partial_revenue_y1",
    "actual_partial_ebit_y1",
    "residual_revenue_y1",
    "residual_fcff_y1",
    "residual_discount_years",
    "revenue_y1",
    "ebit_y1",
    "eps_y1",
    "fcff_y1",
    "discount_factor_y1",
    "revenue_y2",
    "ebit_y2",
    "eps_y2",
    "fcff_y2",
    "discount_factor_y2",
    "revenue_y3",
    "ebit_y3",
    "eps_y3",
    "fcff_y3",
    "discount_factor_y3",
    "revenue_y4",
    "ebit_y4",
    "eps_y4",
    "fcff_y4",
    "discount_factor_y4",
    "revenue_y5",
    "ebit_y5",
    "eps_y5",
    "fcff_y5",
    "discount_factor_y5",
    "wacc",
    "terminal_growth",
    "enterprise_value",
    "equity_value",
    "diluted_shares",
    "value_per_share",
    "mc_n",
    "mc_p10",
    "mc_p25",
    "mc_p50",
    "mc_p75",
    "mc_p90",
    "mc_mean"
  ],
  "frozen_source_sha256": {
    "pack": "e1d371e8a53f6fc21800f10595efba4fa4226c90df8c9ad5969d75c0f43a9198",
    "companyfacts": "eb15a2cd524e99ff27675db78840d039ec4a68b9cc2dcb10accbcb299933a487",
    "treasury": "7e66e6c4d14dec358ccbaadd9b6d11d66e74c141e0df9caa8879d0f634668556"
  },
  "future_data_role": "diagnostic_only",
  "mechanical_check_families": [
    "historical",
    "forecast",
    "valuation",
    "formula",
    "simulation"
  ],
  "nonmechanical_status": "not_selected_not_scored_here"
}
```

</details>

##### 塔吉特：已报上半年与残余下半年开放预测

你是信息截止日 **2025-09-16** 的估值分析师。只可使用 `/app/data/inputs.json` 和等价的 `/app/data/frozen_history.xlsx`；本题离线。禁止使用截止日后的披露、当前股价、现成目标价或市场一致预期。不存在唯一正确的开放假设或目标每股价值。

##### 历史证据与五年模型

最近完整财年截止 2025-02-01。行业分析要求：结合可比销售、客流与客单价、季节性库存及假日权重分析。已报上半年是实际值，不得机械年化为全年。

建立五个财年的收入、经营利润（EBIT）、稀释 EPS 与 FCFF。解释收入增长、利润率、税率、D&A、CapEx、营运资本和股权桥的来源与适用日期。金额为百万美元，股数为百万股，EPS/每股价值为美元，比率为小数。股份支付是经营成本，不得加回 FCFF。经营 NWC = 流动资产−现金−短期投资−(流动负债−当期债务)。净债务只含当期及非当期债务；股权价值 = 企业价值 + 现金及短期投资 − 净债务。

每年 `reinvestment_component = D&A − CapEx − ΔNWC`；`FCFF = EBIT×(1−税率) + reinvestment_component`；`discount_factor = 1/(1+WACC)^discount_years`。终值采用 Gordon 公式，以 FY5 的 FCFF 为基期并折现到估值日；WACC 必须大于 g。年度变体折现年数为 1,2,3,4,5，FY1 是估值日后第一个完整预测年度。

##### 已报 H1 与残余 H2（本题关键）

- 两个 `Reported_Periods` 离散季度是 FY1 已报实际，只相加一次；`Prior_Partial` 是上年同期 H1，用作残余预测基数。FY1 完整财年收入 = 已报 H1 收入 + 你预测的 H2 收入；EBIT 同理。
- FY1 的 da、capex、delta_nwc、reinvestment_component、fcff 均只指未报 H2。全年 FCFF 可另列，但 `fcff_y1` 与估值只能含 H2，不得把已报现金流再次折现。
- 确定性 H2 收入 = 上年同期 H2 收入 ×(1+本期增长)，H2 EBIT = H2 收入 × 本期 EBIT 利润率；D&A、CapEx 按 H2 收入比例计算。FY1 ΔNWC = 上年 FY0 经营性 NWC ×(FY1 全年收入/FY0 全年收入−1)，FY2 起 = 本年 NWC−上年 NWC。经营性 NWC = 流动资产−现金−短期投资−(流动负债−当期债务)。
- 从估值日 2025-09-16 到 FY1 完整财年末 2026-01-31 为 137 天，折现年数=0.375342465753，后续逐年加一。FCFF 已经只含 H2，不能再乘残余比例。
- 模拟的 FY1 trajectory.revenue/ebit/reinvestment/fcff 只含 H2，从上年同期 H2 基数起算；FY2–FY5 才是完整财年。模型 Outputs 中的 revenue/ebit/eps 仍是完整财年。

##### 候选自写 Monte Carlo

编写并实际运行 `/app/output/simulate.py`：
`python3 /app/output/simulate.py --input /app/data/inputs.json --model /app/output/model.xlsx --output /app/output/simulation.json`

至少生成 **5,000 条有效路径**，声明 seed **2032**，采用可复现伪随机数发生器。分别抽样收入增长、EBIT 利润率、再投资强度和折现率，不能直接抽每股价值或股价。声明支持的分布（triangular/uniform/normal/lognormal/beta）、数值参数、单位和有限上下界；保留合法抽样并单列拒绝数。增长与利润率要有非零相关性，或说明独立性的证据及局限；给出声明的相关矩阵及所有四个驱动的实际相关矩阵。模拟边界应能从历史波动或明确的压力情景推导。

`simulation.json` 顶层必须含：`seed`、`n_valid`、`n_rejected`、`method`、`drivers`、`dependence`、`realized_correlation`、`trials`、`statistics`、`percentile_convention`、`limitations`。drivers 以四个精确键 `revenue_growth`、`ebit_margin`、`reinvestment_intensity`、`discount_rate` 为索引，每项含 distribution、parameters、unit、bounds。dependence 含 `ordered_names`、4×4 `matrix`，或 `type: independence` 与 explanation。每条 trial 含 `path_id`、上述四个驱动、`value_per_share` 和五行 `trajectory`；每年含 `year/revenue/ebit/reinvestment/fcff/discount_factor`。路径 reinvestment 是资本开支加营运资本增加减 D&A（正值消耗现金），故 `fcff=ebit×(1−tax)−reinvestment`。增长与利润率在一条路径内保持不变；再投资=当年 trajectory.revenue×reinvestment_intensity。终值以 FY5 路径 FCFF 计算，采用该路径折现率。每条路径必须可由评分器独立重算，不能只提交摘要。分位数采用 `(N−1)q` 线性插值或 `nearest_r` 并如实声明。

##### 交付物与说明

提交 `/app/output/model.xlsx`：保留公开工作簿的 `Outputs` 页，并建立 `Assumptions`、`Forecast`、`DCF` 页。Outputs 的 A 列为题给键，C 列必须是活公式；历史、五个预测年度、估值输出均链接到模型，模拟统计链接到 `MC_Trials`。Assumptions 的 A/B 列分别放键和数值，至少包括：`initial_growth`、`terminal_revenue_growth`、`steady_ebit_margin`、`tax_rate`、`da_to_revenue`、`capex_to_revenue`、`nwc_to_revenue`、`interest_rate`、`wacc`、`terminal_growth`、`net_debt`、`cash_and_investments`、`diluted_shares`。Forecast 的 A 列为键，C:G 为 FY1–FY5；必须包含 revenue、ebit、eps、da、capex、delta_nwc、reinvestment_component、fcff、discount_factor。经营预测、再投资、DCF 和股权桥不能粘贴固定结果；评分会实际修改 WACC 与 g 并重算。

另交 `simulation.json`、`simulate.py`、`memo.md`。memo 不超过 700 个空白分隔词，中文撰写：逐项给出至少三个历史行名/期间/数值/SEC_XBRL 来源，说明可复现的假设推导、公司特定经营因果链、再投资理由、模拟边界与相关性选择，并明确预测不确定性及模型局限。模拟区间是模型条件 DCF 分布，不是股价预测。评分器会重新执行模拟器并独立检查分布、相关性、全部路径算术和分位数；未来实际值及未来股价只在隐藏诊断中出现，不进入评分。

#### E03 选用的 rubric（61 条，权重合计 151；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 4 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| E-deliver_model | 交付与来源完整性 | The required primary model artifact exists and parses. | rule | 主需 | model.xlsx须存在可解析 |
| E-deliver_simulator | 交付与来源完整性 | The candidate-owned simulate.py exists and parses. | rule | 主需 | 须提交simulate.py |
| E-deliver_trials | 交付与来源完整性 | simulation.json exists and has the required top-level schema. | rule | 主需 | simulation.json顶层schema |
| E-deliver_memo | 交付与来源完整性 | memo.md exists and is no more than 700 words. | rule | 次需 | memo须存在且≤700词 |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | Outputs须含全部题给键 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 指定工作表名称须存在 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面明确SBC不得加回 |
| E-hist_revenue | 历史与会计口径 | FY0 revenue equals the frozen SEC fact within 0.1%. | rule | 主需 | FY0收入历史事实 |
| E-hist_ebit | 历史与会计口径 | FY0 EBIT equals the frozen SEC fact within 0.1%. | rule | 主需 | FY0 EBIT历史事实 |
| E-hist_eps | 历史与会计口径 | FY0 diluted EPS equals the frozen SEC fact within 0.1%. | rule | 次需 | FY0稀释EPS历史事实 |
| E-hist_partial_revenue | 历史与会计口径 | The actual partial revenue equals the sum of listed discrete quarters, without YTD double-counting. | rule | 主需 | 已报H1两季相加一次 |
| E-hist_partial_residual_boundary | 历史与会计口径 | Residual FY1 revenue equals full FY1 revenue minus actual partial revenue. | rule | 主需 | H2残余=全年减已报H1 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | H2及各年EBIT用本期利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | FY2起ΔNWC期初期末与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | FY1ΔNWC以FY0经营NWC为基 |
| E-forecast_revenue | 经营预测 | Each of the five full-year revenue forecasts is positive and finite. | rule | 次需 | 五年收入为正且有限 |
| E-forecast_ebit | 经营预测 | Each forecast EBIT is finite and its implied margin is between -50% and 70%. | rule | 次需 | EBIT有限且利润率合理 |
| E-forecast_reinvestment | 经营预测 | Each reinvestment component equals D&A minus CapEx minus the change in NWC. | rule | 主需 | 再投资分量公式一致 |
| E-llm_business_chain | 经营预测 | The forecast states a company-specific operating causal chain that can explain the direction of revenue and EBIT, rather than generic extrapolation. | llm | 主需 | memo要求公司特定因果链 |
| E-llm_reinvestment_reasoning | 经营预测 | The reasoning explains why the operating growth and margin case requires the modeled D&A, capital expenditure and working-capital reinvestment. | llm | 主需 | memo要求再投资理由 |
| E-dcf_fcff | DCF与估值桥 | Each FCFF equals EBIT times one minus tax plus the reinvestment component. | rule | 主需 | 题面给定FCFF公式 |
| E-dcf_discount | DCF与估值桥 | Each discount factor equals one over one plus WACC raised to its stated actual-year fraction. | rule | 主需 | 折现因子按实际年数 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | Gordon终值以FY5折现 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值=股权/稀释股 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | FY1仅含残余H2现金流 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | Outputs C列须为活公式 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 工作簿须可重算无错误 |
| E-formula_perturb_wacc | 公式与模型工程 | A +0.5 percentage-point WACC perturbation decreases enterprise value. | rule | 次需 | 评分会修改WACC重算 |
| E-formula_perturb_g | 公式与模型工程 | A +0.2 percentage-point terminal-growth perturbation increases enterprise value. | rule | 次需 | 评分会修改g重算 |
| X-FM-001 | 公式与模型工程 | 题面要求集中管理的每个业务假设均在假设区拥有独立的可见输入单元格。 | rule | 主需 | Assumptions页须列必备键 |
| X-FM-004 | 公式与模型工程 | 下游行项通过工作簿内活引用取得已在上游模块计算的对应值，未另行重填或独立重算。 | rule | 主需 | 输出须链接模型与MC_Trials |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | Forecast C:G列须对齐期间 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 估值链不得有循环引用 |
| 07-PATHS | 开放假设与模拟 | 模拟路径满足数量、抽样和相关性约束 | rule | 主需 | 有效路径至少5000条 |
| 07-QUANTILE | 开放假设与模拟 | 模拟分位数由试验样本独立计算 | rule | 主需 | 分位数由样本独立重算 |
| E-mc_seed | 开放假设与模拟 | The declared seed equals the task seed. | rule | 次需 | seed须为2032 |
| E-mc_distributions | 开放假设与模拟 | Every required driver has a supported distribution, legal numeric parameters, declared bounds, and sample statistics within method-aware tolerances. | rule | 主需 | 四驱动分布、参数与边界合法 |
| E-mc_dependence | 开放假设与模拟 | The realized correlation matrix agrees with the declared dependence structure, or the independence explanation is supported by realized cross-driver correlations. | rule | 主需 | 实际相关与声明结构一致 |
| E-mc_recompute | 开放假设与模拟 | Every sampled path's DCF value independently recomputes from its drivers and the deterministic model within 0.5%. | rule | 主需 | 逐路径DCF可独立重算 |
| E-llm_driver_derivation | 开放假设与模拟 | The cited historical observations are explicitly connected to each material forecast driver by a reproducible derivation, not merely listed. | llm | 主需 | 历史证据可复现推导驱动 |
| E-agent_distribution_rationale | 开放假设与模拟 | The selected uncertainty bounds and dependence rationale are justified from supplied historical evidence without invoking unavailable post-cutoff information. | agent | 主需 | 边界与相关性有历史依据 |
| E-evidence_numeric_citations | 表达与专业可用性 | At least three memo citations identify a real source, historical period, and value matching the frozen fact. | rule | 次需 | 题面要求三项历史引用 |
| E-evidence_limits | 表达与专业可用性 | The memo explicitly discloses forecast uncertainty and the independence or correlation choice. | rule | 次需 | 须披露不确定性与相关性选择 |
| E-agent_interval_interpretation | 表达与专业可用性 | The interpretation distinguishes model-implied FCFF/DCF dispersion from a market-price forecast and states material simulation limitations. | agent | 次需 | 须区分DCF分布与股价预测 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 折现年数及历史输入需与输入包一致 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | 题面规定NWC及H2推导公式 |
| X-IN-004 | 历史与会计口径 | 每项模型输入的适用日期均不晚于题面规定的信息截止日。 | agent | 主需 | 信息截止日2025-09-16 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 已报H1与完整财年不得混用 |
| X-IN-006 | 历史与会计口径 | 估值桥或比较价格使用题面基准日当天或之前最近一个可用值。 | rule | 主需 | 债务和现金须取估值日前值 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 预测期须为FY1至FY5 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-003 | 表达与专业可用性 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | llm | 次需 | SBC、NWC、净债务处理需一致 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 残余0.375起的折现年数 |
| X-TA-005 | 表达与专业可用性 | 用于外推或推导预测的历史锚定期间数值在模型中可见。 | agent | 次需 | 上年H2基数等锚定可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF各组成需分行 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值引用单元格 |
| X-TA-009 | 表达与专业可用性 | 每个开放性预测假设均有书面推导，包含历史观察值及由该观察值到假设值的计算或映射关系。 | llm | 次需 | 开放假设需书面推导 |
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 程序强制必选项 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 程序强制必选项 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 程序强制必选项 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 程序强制必选项 |

### E04（E）

<details><summary>E04｜完整 spec</summary>

```json
{
  "source_task_id": "E04",
  "ticker": "NFLX",
  "cut": "2024-12-31",
  "asof": "2025-03-01",
  "variant": "annual",
  "shape": "json",
  "sector": "流媒体订阅与内容投入",
  "task_id": "E04",
  "family": "E",
  "years": 5,
  "min_paths": 5000,
  "mc_seed": 2133,
  "schema_version": "dcf-v3-task-v1",
  "language": "zh-CN",
  "required_artifacts": [
    "model.json",
    "simulate.py",
    "simulation.json",
    "memo.md",
    "recompute.py"
  ],
  "output_keys": [
    "hist_revenue_fy0",
    "hist_ebit_fy0",
    "hist_eps_fy0",
    "revenue_y1",
    "ebit_y1",
    "eps_y1",
    "fcff_y1",
    "discount_factor_y1",
    "revenue_y2",
    "ebit_y2",
    "eps_y2",
    "fcff_y2",
    "discount_factor_y2",
    "revenue_y3",
    "ebit_y3",
    "eps_y3",
    "fcff_y3",
    "discount_factor_y3",
    "revenue_y4",
    "ebit_y4",
    "eps_y4",
    "fcff_y4",
    "discount_factor_y4",
    "revenue_y5",
    "ebit_y5",
    "eps_y5",
    "fcff_y5",
    "discount_factor_y5",
    "wacc",
    "terminal_growth",
    "enterprise_value",
    "equity_value",
    "diluted_shares",
    "value_per_share",
    "mc_n",
    "mc_p10",
    "mc_p25",
    "mc_p50",
    "mc_p75",
    "mc_p90",
    "mc_mean"
  ],
  "frozen_source_sha256": {
    "pack": "3a19b7f6ffb2534c3cc47006fe8c920f40838d8b4d353fcd9c9fed5c2c6aa6f6",
    "companyfacts": "fd31bc147b36495f6912e063188aea71434077236f4e995268620b47fda99e61",
    "treasury": "7e66e6c4d14dec358ccbaadd9b6d11d66e74c141e0df9caa8879d0f634668556"
  },
  "future_data_role": "diagnostic_only",
  "mechanical_check_families": [
    "historical",
    "forecast",
    "valuation",
    "formula",
    "simulation"
  ],
  "nonmechanical_status": "not_selected_not_scored_here"
}
```

</details>

##### Netflix：订阅经济与内容投入开放预测

你是信息截止日 **2025-03-01** 的估值分析师。只可使用 `/app/data/inputs.json` 和等价的 `/app/data/frozen_history.xlsx`；本题离线。禁止使用截止日后的披露、当前股价、现成目标价或市场一致预期。不存在唯一正确的开放假设或目标每股价值。

##### 历史证据与五年模型

最近完整财年截止 2024-12-31。行业分析要求：结合付费会员、留存、定价与广告套餐、内容摊销分析。汇总历史无法单独识别各经营变量，应把不可观测量明确标为开放假设。

建立五个财年的收入、经营利润（EBIT）、稀释 EPS 与 FCFF。解释收入增长、利润率、税率、D&A、CapEx、营运资本和股权桥的来源与适用日期。金额为百万美元，股数为百万股，EPS/每股价值为美元，比率为小数。股份支付是经营成本，不得加回 FCFF。经营 NWC = 流动资产−现金−短期投资−(流动负债−当期债务)。净债务只含当期及非当期债务；股权价值 = 企业价值 + 现金及短期投资 − 净债务。

每年 `reinvestment_component = D&A − CapEx − ΔNWC`；`FCFF = EBIT×(1−税率) + reinvestment_component`；`discount_factor = 1/(1+WACC)^discount_years`。终值采用 Gordon 公式，以 FY5 的 FCFF 为基期并折现到估值日；WACC 必须大于 g。年度变体折现年数为 1,2,3,4,5，FY1 是估值日后第一个完整预测年度。

##### 候选自写 Monte Carlo

编写并实际运行 `/app/output/simulate.py`：
`python3 /app/output/simulate.py --input /app/data/inputs.json --model /app/output/model.json --output /app/output/simulation.json`

至少生成 **5,000 条有效路径**，声明 seed **2133**，采用可复现伪随机数发生器。分别抽样收入增长、EBIT 利润率、再投资强度和折现率，不能直接抽每股价值或股价。声明支持的分布（triangular/uniform/normal/lognormal/beta）、数值参数、单位和有限上下界；保留合法抽样并单列拒绝数。增长与利润率要有非零相关性，或说明独立性的证据及局限；给出声明的相关矩阵及所有四个驱动的实际相关矩阵。模拟边界应能从历史波动或明确的压力情景推导。

`simulation.json` 顶层必须含：`seed`、`n_valid`、`n_rejected`、`method`、`drivers`、`dependence`、`realized_correlation`、`trials`、`statistics`、`percentile_convention`、`limitations`。drivers 以四个精确键 `revenue_growth`、`ebit_margin`、`reinvestment_intensity`、`discount_rate` 为索引，每项含 distribution、parameters、unit、bounds。dependence 含 `ordered_names`、4×4 `matrix`，或 `type: independence` 与 explanation。每条 trial 含 `path_id`、上述四个驱动、`value_per_share` 和五行 `trajectory`；每年含 `year/revenue/ebit/reinvestment/fcff/discount_factor`。路径 reinvestment 是资本开支加营运资本增加减 D&A（正值消耗现金），故 `fcff=ebit×(1−tax)−reinvestment`。增长与利润率在一条路径内保持不变；再投资=当年 trajectory.revenue×reinvestment_intensity。终值以 FY5 路径 FCFF 计算，采用该路径折现率。每条路径必须可由评分器独立重算，不能只提交摘要。分位数采用 `(N−1)q` 线性插值或 `nearest_r` 并如实声明。

##### 交付物与说明

提交 `/app/output/model.json`，包含对象 `historical`、`assumptions`、`forecast`、`valuation`、`simulation_summary`。historical 使用 Outputs 同名历史键；assumptions 至少包含 `initial_growth`、`terminal_revenue_growth`、`steady_ebit_margin`、`tax_rate`、`da_to_revenue`、`capex_to_revenue`、`nwc_to_revenue`、`interest_rate`、`wacc`、`terminal_growth`、`net_debt`、`cash_and_investments`、`diluted_shares`。forecast 每年包含 `revenue_y1`…`revenue_y5`、`ebit_y*`、`eps_y*`、`da_y*`、`capex_y*`、`delta_nwc_y*`、`reinvestment_component_y*`、`fcff_y*`、`discount_factor_y*`；H1 变体另含实际/残余键。valuation 包含 WACC、g、税率、净债务、现金及投资、稀释股数、企业/股权/每股价值、`discount_years` 五元素数组和 `terminal_year_fcff`；simulation_summary 含 `n_valid`、`p10/p25/p50/p75/p90/mean`。另交 `/app/output/recompute.py`，接受 `--input INPUT --model MODEL --output DIR` 并写 `recomputed.json`。它必须从上述经营假设和公开历史重建每年收入、EBIT、再投资及估值，不得只回显 forecast/valuation 的既有结果。评分会修改经营假设和 WACC/g 后独立执行。

另交 `simulation.json`、`simulate.py`、`memo.md`。memo 不超过 700 个空白分隔词，中文撰写：逐项给出至少三个历史行名/期间/数值/SEC_XBRL 来源，说明可复现的假设推导、公司特定经营因果链、再投资理由、模拟边界与相关性选择，并明确预测不确定性及模型局限。模拟区间是模型条件 DCF 分布，不是股价预测。评分器会重新执行模拟器并独立检查分布、相关性、全部路径算术和分位数；未来实际值及未来股价只在隐藏诊断中出现，不进入评分。

#### E04 选用的 rubric（54 条，权重合计 130；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 6 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | output_keys须齐全且为数值 |
| E-deliver_model | 交付与来源完整性 | The required primary model artifact exists and parses. | rule | 主需 | model.json须存在可解析 |
| E-deliver_simulator | 交付与来源完整性 | The candidate-owned simulate.py exists and parses. | rule | 主需 | simulate.py须存在可解析 |
| E-deliver_trials | 交付与来源完整性 | simulation.json exists and has the required top-level schema. | rule | 主需 | simulation.json顶层schema |
| E-deliver_memo | 交付与来源完整性 | memo.md exists and is no more than 700 words. | rule | 次需 | memo限700词 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 含recompute.py等全部文件 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面明确SBC不得加回FCFF |
| E-hist_revenue | 历史与会计口径 | FY0 revenue equals the frozen SEC fact within 0.1%. | rule | 主需 | FY0收入须匹配SEC事实 |
| E-hist_ebit | 历史与会计口径 | FY0 EBIT equals the frozen SEC fact within 0.1%. | rule | 主需 | FY0 EBIT须匹配SEC事实 |
| E-hist_eps | 历史与会计口径 | FY0 diluted EPS equals the frozen SEC fact within 0.1%. | rule | 次需 | FY0稀释EPS须匹配SEC |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC期初期末与符号 |
| E-forecast_revenue | 经营预测 | Each of the five full-year revenue forecasts is positive and finite. | rule | 次需 | 五年收入为正且有限 |
| E-forecast_ebit | 经营预测 | Each forecast EBIT is finite and its implied margin is between -50% and 70%. | rule | 次需 | EBIT有限且利润率合理 |
| E-forecast_reinvestment | 经营预测 | Each reinvestment component equals D&A minus CapEx minus the change in NWC. | rule | 主需 | 再投资公式题面明确 |
| E-llm_business_chain | 经营预测 | The forecast states a company-specific operating causal chain that can explain the direction of revenue and EBIT, rather than generic extrapolation. | llm | 主需 | memo要求公司因果链 |
| E-llm_reinvestment_reasoning | 经营预测 | The reasoning explains why the operating growth and margin case requires the modeled D&A, capital expenditure and working-capital reinvestment. | llm | 主需 | memo要求再投资理由 |
| E-dcf_fcff | DCF与估值桥 | Each FCFF equals EBIT times one minus tax plus the reinvestment component. | rule | 主需 | 题面规定FCFF公式 |
| E-dcf_discount | DCF与估值桥 | Each discount factor equals one over one plus WACC raised to its stated actual-year fraction. | rule | 主需 | 折现因子公式明确 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | Gordon终值以FY5折现 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值需除稀释股数 |
| E-formula_perturb_wacc | 公式与模型工程 | A +0.5 percentage-point WACC perturbation decreases enterprise value. | rule | 次需 | WACC上调EV应下降 |
| E-formula_perturb_g | 公式与模型工程 | A +0.2 percentage-point terminal-growth perturbation increases enterprise value. | rule | 次需 | g上调EV应上升 |
| 07-ASSUME | 开放假设与模拟 | 开放假设有可追溯的证据和适用日期 | llm | 主需 | 假设需注明来源与适用日期 |
| 07-PATHS | 开放假设与模拟 | 模拟路径满足数量、抽样和相关性约束 | rule | 主需 | 有效路径数至少5000 |
| 07-QUANTILE | 开放假设与模拟 | 模拟分位数由试验样本独立计算 | rule | 主需 | 分位数需由路径独立重算 |
| E-mc_seed | 开放假设与模拟 | The declared seed equals the task seed. | rule | 次需 | seed须为2133 |
| E-mc_distributions | 开放假设与模拟 | Every required driver has a supported distribution, legal numeric parameters, declared bounds, and sample statistics within method-aware tolerances. | rule | 主需 | 四驱动分布、参数与边界合法 |
| E-mc_dependence | 开放假设与模拟 | The realized correlation matrix agrees with the declared dependence structure, or the independence explanation is supported by realized cross-driver correlations. | rule | 主需 | 实际相关与声明相关一致 |
| E-mc_recompute | 开放假设与模拟 | Every sampled path's DCF value independently recomputes from its drivers and the deterministic model within 0.5%. | rule | 主需 | 逐路径DCF可独立重算 |
| E-mc_not_degenerate | 开放假设与模拟 | The value distribution is non-degenerate and has more than 100 distinct values. | rule | 次需 | 价值分布不应退化 |
| E-llm_driver_derivation | 开放假设与模拟 | The cited historical observations are explicitly connected to each material forecast driver by a reproducible derivation, not merely listed. | llm | 主需 | 历史数据到驱动可复现推导 |
| E-agent_distribution_rationale | 开放假设与模拟 | The selected uncertainty bounds and dependence rationale are justified from supplied historical evidence without invoking unavailable post-cutoff information. | agent | 主需 | 边界与相关性需历史论证 |
| E-evidence_numeric_citations | 表达与专业可用性 | At least three memo citations identify a real source, historical period, and value matching the frozen fact. | rule | 次需 | 题面要求至少三项历史引用 |
| E-evidence_limits | 表达与专业可用性 | The memo explicitly discloses forecast uncertainty and the independence or correlation choice. | rule | 次需 | 须披露不确定性与相关性选择 |
| E-agent_interval_interpretation | 表达与专业可用性 | The interpretation distinguishes model-implied FCFF/DCF dispersion from a market-price forecast and states material simulation limitations. | agent | 次需 | 须区分DCF分布与股价预测 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 历史键须与输入包一致 |
| X-IN-002 | 历史与会计口径 | 题面指定的恒定输入在其每个适用期间均被原样采用，不出现未经指定的期间变化。 | rule | 主需 | 路径内增长与利润率恒定 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | NWC与净债务公式指定 |
| X-IN-004 | 历史与会计口径 | 每项模型输入的适用日期均不晚于题面规定的信息截止日。 | agent | 主需 | 信息截止日2025-03-01 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 年度变体须用财年数据 |
| X-IN-006 | 历史与会计口径 | 估值桥或比较价格使用题面基准日当天或之前最近一个可用值。 | rule | 主需 | 现金债务取最近可用值 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 五个财年预测期 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| X-TA-003 | 表达与专业可用性 | 每项指定会计事项的书面处理说明均与模型实际处理一致。 | llm | 次需 | SBC与NWC处理须一致 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 要求discount_years数组 |
| X-TA-005 | 表达与专业可用性 | 用于外推或推导预测的历史锚定期间数值在模型中可见。 | agent | 次需 | historical锚定值须可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF分项须单列 |
| X-TA-009 | 表达与专业可用性 | 每个开放性预测假设均有书面推导，包含历史观察值及由该观察值到假设值的计算或映射关系。 | llm | 次需 | 开放假设需书面推导 |
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 程序强制必选项 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 程序强制必选项 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 程序强制必选项 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 程序强制必选项 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 程序强制必选项 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 程序强制必选项 |

### W01（W）

<details><summary>W01｜完整 spec</summary>

```json
{
  "ticker": "AAPL",
  "cik": 320193,
  "name": "Apple Inc.",
  "ir": "https://investor.apple.com/",
  "fiscal_year": "FY2024",
  "fiscal_year_start": "2023-10-01",
  "fiscal_year_end": "2024-09-28",
  "asof": "2024-11-27",
  "treasury_date": "2024-11-27",
  "task_id": "W01",
  "family": "W",
  "schema_version": "dcf-v3-task-v1",
  "language": "zh-CN",
  "required_fields": [
    "revenue",
    "operating_income",
    "pretax_income",
    "income_tax",
    "net_income_consolidated",
    "da",
    "capex",
    "diluted_shares",
    "cash",
    "short_term_investments",
    "receivables",
    "current_assets",
    "current_liabilities",
    "current_debt",
    "noncurrent_debt",
    "treasury_10y"
  ],
  "allowed_sources": [
    {
      "source_id": "SEC_COMPANYFACTS",
      "domains": [
        "data.sec.gov",
        "www.sec.gov"
      ],
      "url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
    },
    {
      "source_id": "COMPANY_IR_FILING",
      "domains": [
        "investor.apple.com",
        "s22.q4cdn.com",
        "s201.q4cdn.com",
        "d18rn0p25nwr6d.cloudfront.net"
      ],
      "url": "https://investor.apple.com/"
    },
    {
      "source_id": "UST_DAILY",
      "domains": [
        "home.treasury.gov"
      ],
      "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page=&_format=csv"
    }
  ],
  "required_artifacts": [
    "model.xlsx",
    "sources.json",
    "cross_validation.json",
    "retrieval_map.json",
    "memo.md"
  ],
  "valuation_assumptions": {
    "initial_growth": 0.06,
    "steady_ebit_margin": 0.31,
    "tax_rate": 0.16
  },
  "source_snapshot_sha256": {
    "../data/raw/AAPL_facts.json": "f085735b4d08fb116ade18d24247ffabe11df8eb52eae6556b165831f15ef1ad",
    "../data/raw/DGS10.csv": "7e66e6c4d14dec358ccbaadd9b6d11d66e74c141e0df9caa8879d0f634668556"
  },
  "network": {
    "mode": "allowlist",
    "sidecar": "dcf-ipv4-gost-egress:v1",
    "configured": true,
    "verified": false,
    "status": "not_verified_by_generation"
  },
  "nonmechanical_status": "W-NOFORBID 与 W-FAILURE 需另行语义/代理评审，本次机械评分不自动给分。"
}
```

</details>

##### Apple Inc.（AAPL）：限定来源取数与五年 DCF

信息截止日为 **2024-11-27**，建模基准财年为 **FY2024**。必须先从指定来源取数再建模，不得先猜结果后补来源。所有题面、取数记录、模型标签和 memo 均用中文；语义 ID 与 XBRL 标签保留英文。

##### 允许来源与禁止事项

1. SEC EDGAR companyfacts：`https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json`；也可使用 SEC Archives 中截止日前已申报的原始 10-K/10-K/A。
2. 公司 IR：`https://investor.apple.com/`，仅可核对同一期间的原始申报；同一 XBRL 事实与 IR 转载不构成两个独立会计事实。
3. 美国财政部日度收益率：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page=&_format=csv`，取 **2024-11-27** 的 10 Yr，如该日官方无值则用之前最近观测并写明实际日期。4.25% 在模型中写 0.0425。

仅允许上述 SEC、公司 IR（含申报文件必要的 CDN）和财政部域名。禁止自由搜索当前或历史股价、现成目标价、市场一致预期及截止日后信息；禁止用搜索摘要或第三方财经网站代替原始来源。历史权威真值按 filed≤截止日的 10-K 事实评定，不能取后来重述的同一期间值。

##### 必须取回的数据

| 语义 ID | 数据项 | 期间 | 提交单位 | 允许标签（按顺序使用首个有合规事实的标签） |
|---|---|---|---|---|
| `revenue` | 合并收入 | 2023-10-01 至 2024-09-28 | USD_millions | RevenueFromContractWithCustomerExcludingAssessedTax、Revenues、SalesRevenueNet、RevenueFromContractWithCustomerIncludingAssessedTax |
| `operating_income` | 经营利润（EBIT） | 2023-10-01 至 2024-09-28 | USD_millions | OperatingIncomeLoss |
| `pretax_income` | 税前利润 | 2023-10-01 至 2024-09-28 | USD_millions | IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest、IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments |
| `income_tax` | 所得税费用 | 2023-10-01 至 2024-09-28 | USD_millions | IncomeTaxExpenseBenefit |
| `net_income_consolidated` | 含非控股权益的合并净利润 | 2023-10-01 至 2024-09-28 | USD_millions | ProfitLoss、NetIncomeLoss |
| `da` | 折旧与摊销 | 2023-10-01 至 2024-09-28 | USD_millions | DepreciationDepletionAndAmortization、DepreciationAmortizationAndAccretionNet、DepreciationAndAmortization、Depreciation |
| `capex` | 购置固定资产现金支出（正数） | 2023-10-01 至 2024-09-28 | USD_millions | PaymentsToAcquirePropertyPlantAndEquipment、PaymentsToAcquireProductiveAssets |
| `diluted_shares` | 加权平均稀释股数 | 2023-10-01 至 2024-09-28 | shares_millions | WeightedAverageNumberOfDilutedSharesOutstanding |
| `cash` | 现金及现金等价物 | 截至 2024-09-28 | USD_millions | CashAndCashEquivalentsAtCarryingValue、CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents |
| `short_term_investments` | 短期投资 | 截至 2024-09-28 | USD_millions | ShortTermInvestments、MarketableSecuritiesCurrent、AvailableForSaleSecuritiesDebtSecuritiesCurrent |
| `receivables` | 应收账款净额 | 截至 2024-09-28 | USD_millions | AccountsReceivableNetCurrent、ReceivablesNetCurrent |
| `current_assets` | 流动资产合计 | 截至 2024-09-28 | USD_millions | AssetsCurrent |
| `current_liabilities` | 流动负债合计 | 截至 2024-09-28 | USD_millions | LiabilitiesCurrent |
| `current_debt` | 当期债务 | 截至 2024-09-28 | USD_millions | LongTermDebtCurrent、DebtCurrent、ShortTermBorrowings |
| `noncurrent_debt` | 非当期债务 | 截至 2024-09-28 | USD_millions | LongTermDebtNoncurrent、LongTermDebt |
| `treasury_10y` | 10 年期美国国债固定期限收益率 | 2024-11-27 | decimal | DGS10 |

金额须换算为百万美元，股数换算为百万股。`net_income_consolidated` 是含非控股权益的合并净利润（优先 ProfitLoss），不得与归母净利润混用。资本开支用现金流出正数。缺失不是零：取数失败必须在 sources.json 记录 failed、允许 URL、错误及处理，不得编造或静默补零。

##### 提交与公式要求

- `sources.json`：`items` 数组逐项覆盖上表，含 `field_id/value/unit/period_start/period_end/source_id/source_url/source_file/field/form/filed/accession/observed_at/status/error`。成功项必须含实际数值、允许域名 URL、正确期间与字段、申报号和 filed；`observed_at` 是实际取数日，不是申报日。
- `cross_validation.json`：`checks` 数组至少包含 `pretax_to_net_income`，计算 `pretax_income−income_tax−net_income_consolidated` 的 `difference`，引用来源表中三个字段。允许 `abs(difference)<=max(0.01, abs(net_income_consolidated)*0.02)`，超出或缺失必须在 memo 披露，不能强行改成零。
- `retrieval_map.json`：`items` 数组逐项含 `field_id/source_item_index/sheet/cell/used_by`。工作簿 `Sources` 页 A/B/C 列必须是 field_id、取数值、单位，且每个取数字段在 Forecast/Assumptions/DCF 中有活公式实际引用；不能把取数表摆在一旁、在别处另填历史值。
- `model.xlsx`：`Sources`、`Assumptions`、`Forecast`、`DCF`、`Outputs` 五页。Assumptions A/B 列放经营假设；Forecast A 列放语义键、C:G 为 FY1–FY5，含 revenue、ebit、da、capex、delta_nwc、reinvestment_component、fcff、discount_factor；DCF 计算显性期现值、Gordon 终值及股权桥；Outputs A/C 列输出 `enterprise_value/equity_value/value_per_share`。预测、再投资、折现和输出必须是活公式，并能通过 LibreOffice 重算与 WACC/g 扰动。
- `memo.md`：用中文说明实际取数日期、来源、开放预测理由、交叉验证差异及所有失败/冲突；披露“配置存在”不等于“白名单已经验证生效”。不需要也不得寻找股价来判断 DCF 是否合理。

##### 模型口径

{
  "forecast_years": 5,
  "growth": "FY1 使用 initial_growth，FY2–FY5 线性收敛至 terminal_growth",
  "ebit_margin": "预测期保持 steady_ebit_margin",
  "da_capex": "每年收入乘相应比率",
  "nwc": "经营 NWC=流动资产−现金−短期投资−(流动负债−当期债务)；FY1 ΔNWC=FY0 NWC×(FY1 收入/FY0 收入−1)，其后为本年减上年",
  "fcff": "EBIT×(1−tax_rate)+D&A−CapEx−ΔNWC",
  "discount_years": [
    1,
    2,
    3,
    4,
    5
  ],
  "terminal": "Gordon，FY5 FCFF×(1+g)/(WACC−g) 再折现五年",
  "equity": "股权价值=企业价值+现金+短期投资−当期债务−非当期债务；每股价值除以加权平均稀释股数",
  "assumptions": "initial_growth、steady_ebit_margin、tax_rate、da_to_revenue、capex_to_revenue、wacc、terminal_growth 为透明开放假设；WACC>g，债务与现金的口径不得重复。"
}

公开合同 `/app/data/retrieval_contract.json` 包含相同字段、允许来源和公式约定。运行网络由 IPv4 sidecar 白名单限制，配置已写入 environment/docker-compose.yaml 和 task.toml；生效状态只能根据运行时探测报告说明。独立评分器会按隐藏原始 SEC 快照和容差核验取数值、来源/期间/字段、交叉勾稽及模型引用链，并重算工作簿。未执行的语言与禁止来源语义评审不会自动算通过。

#### W01 选用的 rubric（42 条，权重合计 110；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 4 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 五个交付文件须按名存在 |
| X-IF-001b | 交付与来源完整性 | 每个交付文件的类型与题面指定类型一致，未以其他类型替代 | rule | 主需 | xlsx/json/md类型须一致 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 指定五个工作表名称 |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | Outputs三个键须唯一数值 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | 取数须标明单位 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各期EBIT用稳态利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | FY2起ΔNWC期初期末与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | FY1 ΔNWC以FY0余额为基 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面规定FCFF公式 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | Gordon终值折现五年 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值除稀释股数 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求预测与输出为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 要求LibreOffice重算 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 模型须无外链与错误值 |
| X-FM-001 | 公式与模型工程 | 题面要求集中管理的每个业务假设均在假设区拥有独立的可见输入单元格。 | rule | 主需 | Assumptions页集中放假设 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不得硬编码假设 |
| X-FM-004 | 公式与模型工程 | 下游行项通过工作簿内活引用取得已在上游模块计算的对应值，未另行重填或独立重算。 | rule | 主需 | 取数须被活公式引用 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | FY1–FY5各行列对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 估值链无循环引用 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求提交中文memo |
| W-VALUE | 交付与来源完整性 | 每个要求取数的值与指定权威来源一致（在题面容差内） | rule | 主需 | 取数值须符合权威10-K事实 |
| W-SOURCE | 交付与来源完整性 | 每个取数注明来源文件、期间和字段或页码，且来源属于允许范围 | rule | 主需 | sources.json须记录来源与期间 |
| W-CROSS | 交付与来源完整性 | 至少一项关键数据用第二个独立来源或勾稽关系交叉验证 | rule | 主需 | 要求税前至净利勾稽校验 |
| W-USED | 交付与来源完整性 | 取到的数被模型公式实际引用，而不是另行手填 | rule | 主需 | 取数须被活公式引用 |
| W-FAILURE | 交付与来源完整性 | 取数失败或数据冲突时如实披露并说明处理方法 | llm | 次需 | 失败与冲突须在memo披露 |
| X-IN-002 | 历史与会计口径 | 题面指定的恒定输入在其每个适用期间均被原样采用，不出现未经指定的期间变化。 | rule | 主需 | EBIT利润率预测期保持不变 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | FY0经营NWC按指定公式推导 |
| X-IN-004 | 历史与会计口径 | 每项模型输入的适用日期均不晚于题面规定的信息截止日。 | agent | 主需 | filed不晚于截止日 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 须用FY2024财年期间 |
| X-IN-006 | 历史与会计口径 | 估值桥或比较价格使用题面基准日当天或之前最近一个可用值。 | rule | 主需 | 10年国债取截止日或之前最近值 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 显性预测期为FY1–FY5 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型一致 |
| X-TA-001 | 表达与专业可用性 | 每项外部输入均有可定位的来源记录，记录至少含文档或数据集名称及对应财务期间或数据日期。 | agent | 主需 | 外部取数需可定位来源记录 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 题面规定折现期1-5 |
| X-TA-005 | 表达与专业可用性 | 用于外推或推导预测的历史锚定期间数值在模型中可见。 | agent | 次需 | FY0收入与NWC锚定值需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | Forecast要求FCFF分项行 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值需引用可见单元格 |
| X-TA-009 | 表达与专业可用性 | 每个开放性预测假设均有书面推导，包含历史观察值及由该观察值到假设值的计算或映射关系。 | llm | 次需 | 开放假设需书面推导 |
| W-NOFORBID | 交付与来源完整性 | 未使用禁止来源或截止日后的信息 | agent | 主需 | 程序强制必选项 |
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 程序强制必选项 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 程序强制必选项 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 程序强制必选项 |

### W02（W）

<details><summary>W02｜完整 spec</summary>

```json
{
  "ticker": "COST",
  "cik": 909832,
  "name": "Costco Wholesale Corporation",
  "ir": "https://investor.costco.com/",
  "fiscal_year": "FY2024",
  "fiscal_year_start": "2023-09-04",
  "fiscal_year_end": "2024-09-01",
  "asof": "2024-10-31",
  "treasury_date": "2024-10-31",
  "task_id": "W02",
  "family": "W",
  "schema_version": "dcf-v3-task-v1",
  "language": "zh-CN",
  "required_fields": [
    "revenue",
    "operating_income",
    "pretax_income",
    "income_tax",
    "net_income_consolidated",
    "da",
    "capex",
    "diluted_shares",
    "cash",
    "short_term_investments",
    "receivables",
    "current_assets",
    "current_liabilities",
    "current_debt",
    "noncurrent_debt",
    "treasury_10y"
  ],
  "allowed_sources": [
    {
      "source_id": "SEC_COMPANYFACTS",
      "domains": [
        "data.sec.gov",
        "www.sec.gov"
      ],
      "url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000909832.json"
    },
    {
      "source_id": "COMPANY_IR_FILING",
      "domains": [
        "investor.costco.com",
        "s22.q4cdn.com",
        "s201.q4cdn.com",
        "d18rn0p25nwr6d.cloudfront.net"
      ],
      "url": "https://investor.costco.com/"
    },
    {
      "source_id": "UST_DAILY",
      "domains": [
        "home.treasury.gov"
      ],
      "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page=&_format=csv"
    }
  ],
  "required_artifacts": [
    "model.xlsx",
    "sources.json",
    "cross_validation.json",
    "retrieval_map.json",
    "memo.md"
  ],
  "valuation_assumptions": {
    "initial_growth": 0.07,
    "steady_ebit_margin": 0.037,
    "tax_rate": 0.25
  },
  "source_snapshot_sha256": {
    "../data/raw/COST_facts.json": "b675ced201b27ede2b0d26ca6fd873befe96a1afa9679339a2d0b964187dcdff",
    "../data/raw/DGS10.csv": "7e66e6c4d14dec358ccbaadd9b6d11d66e74c141e0df9caa8879d0f634668556"
  },
  "network": {
    "mode": "allowlist",
    "sidecar": "dcf-ipv4-gost-egress:v1",
    "configured": true,
    "verified": false,
    "status": "not_verified_by_generation"
  },
  "nonmechanical_status": "W-NOFORBID 与 W-FAILURE 需另行语义/代理评审，本次机械评分不自动给分。"
}
```

</details>

##### Costco Wholesale Corporation（COST）：限定来源取数与五年 DCF

信息截止日为 **2024-10-31**，建模基准财年为 **FY2024**。必须先从指定来源取数再建模，不得先猜结果后补来源。所有题面、取数记录、模型标签和 memo 均用中文；语义 ID 与 XBRL 标签保留英文。

##### 允许来源与禁止事项

1. SEC EDGAR companyfacts：`https://data.sec.gov/api/xbrl/companyfacts/CIK0000909832.json`；也可使用 SEC Archives 中截止日前已申报的原始 10-K/10-K/A。
2. 公司 IR：`https://investor.costco.com/`，仅可核对同一期间的原始申报；同一 XBRL 事实与 IR 转载不构成两个独立会计事实。
3. 美国财政部日度收益率：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page=&_format=csv`，取 **2024-10-31** 的 10 Yr，如该日官方无值则用之前最近观测并写明实际日期。4.25% 在模型中写 0.0425。

仅允许上述 SEC、公司 IR（含申报文件必要的 CDN）和财政部域名。禁止自由搜索当前或历史股价、现成目标价、市场一致预期及截止日后信息；禁止用搜索摘要或第三方财经网站代替原始来源。历史权威真值按 filed≤截止日的 10-K 事实评定，不能取后来重述的同一期间值。

##### 必须取回的数据

| 语义 ID | 数据项 | 期间 | 提交单位 | 允许标签（按顺序使用首个有合规事实的标签） |
|---|---|---|---|---|
| `revenue` | 合并收入 | 2023-09-04 至 2024-09-01 | USD_millions | RevenueFromContractWithCustomerExcludingAssessedTax、Revenues、SalesRevenueNet、RevenueFromContractWithCustomerIncludingAssessedTax |
| `operating_income` | 经营利润（EBIT） | 2023-09-04 至 2024-09-01 | USD_millions | OperatingIncomeLoss |
| `pretax_income` | 税前利润 | 2023-09-04 至 2024-09-01 | USD_millions | IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest、IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments |
| `income_tax` | 所得税费用 | 2023-09-04 至 2024-09-01 | USD_millions | IncomeTaxExpenseBenefit |
| `net_income_consolidated` | 含非控股权益的合并净利润 | 2023-09-04 至 2024-09-01 | USD_millions | ProfitLoss、NetIncomeLoss |
| `da` | 折旧与摊销 | 2023-09-04 至 2024-09-01 | USD_millions | DepreciationDepletionAndAmortization、DepreciationAmortizationAndAccretionNet、DepreciationAndAmortization、Depreciation |
| `capex` | 购置固定资产现金支出（正数） | 2023-09-04 至 2024-09-01 | USD_millions | PaymentsToAcquirePropertyPlantAndEquipment、PaymentsToAcquireProductiveAssets |
| `diluted_shares` | 加权平均稀释股数 | 2023-09-04 至 2024-09-01 | shares_millions | WeightedAverageNumberOfDilutedSharesOutstanding |
| `cash` | 现金及现金等价物 | 截至 2024-09-01 | USD_millions | CashAndCashEquivalentsAtCarryingValue、CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents |
| `short_term_investments` | 短期投资 | 截至 2024-09-01 | USD_millions | ShortTermInvestments、MarketableSecuritiesCurrent、AvailableForSaleSecuritiesDebtSecuritiesCurrent |
| `receivables` | 应收账款净额 | 截至 2024-09-01 | USD_millions | AccountsReceivableNetCurrent、ReceivablesNetCurrent |
| `current_assets` | 流动资产合计 | 截至 2024-09-01 | USD_millions | AssetsCurrent |
| `current_liabilities` | 流动负债合计 | 截至 2024-09-01 | USD_millions | LiabilitiesCurrent |
| `current_debt` | 当期债务 | 截至 2024-09-01 | USD_millions | LongTermDebtCurrent、DebtCurrent、ShortTermBorrowings |
| `noncurrent_debt` | 非当期债务 | 截至 2024-09-01 | USD_millions | LongTermDebtNoncurrent、LongTermDebt |
| `treasury_10y` | 10 年期美国国债固定期限收益率 | 2024-10-31 | decimal | DGS10 |

金额须换算为百万美元，股数换算为百万股。`net_income_consolidated` 是含非控股权益的合并净利润（优先 ProfitLoss），不得与归母净利润混用。资本开支用现金流出正数。缺失不是零：取数失败必须在 sources.json 记录 failed、允许 URL、错误及处理，不得编造或静默补零。

##### 提交与公式要求

- `sources.json`：`items` 数组逐项覆盖上表，含 `field_id/value/unit/period_start/period_end/source_id/source_url/source_file/field/form/filed/accession/observed_at/status/error`。成功项必须含实际数值、允许域名 URL、正确期间与字段、申报号和 filed；`observed_at` 是实际取数日，不是申报日。
- `cross_validation.json`：`checks` 数组至少包含 `pretax_to_net_income`，计算 `pretax_income−income_tax−net_income_consolidated` 的 `difference`，引用来源表中三个字段。允许 `abs(difference)<=max(0.01, abs(net_income_consolidated)*0.02)`，超出或缺失必须在 memo 披露，不能强行改成零。
- `retrieval_map.json`：`items` 数组逐项含 `field_id/source_item_index/sheet/cell/used_by`。工作簿 `Sources` 页 A/B/C 列必须是 field_id、取数值、单位，且每个取数字段在 Forecast/Assumptions/DCF 中有活公式实际引用；不能把取数表摆在一旁、在别处另填历史值。
- `model.xlsx`：`Sources`、`Assumptions`、`Forecast`、`DCF`、`Outputs` 五页。Assumptions A/B 列放经营假设；Forecast A 列放语义键、C:G 为 FY1–FY5，含 revenue、ebit、da、capex、delta_nwc、reinvestment_component、fcff、discount_factor；DCF 计算显性期现值、Gordon 终值及股权桥；Outputs A/C 列输出 `enterprise_value/equity_value/value_per_share`。预测、再投资、折现和输出必须是活公式，并能通过 LibreOffice 重算与 WACC/g 扰动。
- `memo.md`：用中文说明实际取数日期、来源、开放预测理由、交叉验证差异及所有失败/冲突；披露“配置存在”不等于“白名单已经验证生效”。不需要也不得寻找股价来判断 DCF 是否合理。

##### 模型口径

{
  "forecast_years": 5,
  "growth": "FY1 使用 initial_growth，FY2–FY5 线性收敛至 terminal_growth",
  "ebit_margin": "预测期保持 steady_ebit_margin",
  "da_capex": "每年收入乘相应比率",
  "nwc": "经营 NWC=流动资产−现金−短期投资−(流动负债−当期债务)；FY1 ΔNWC=FY0 NWC×(FY1 收入/FY0 收入−1)，其后为本年减上年",
  "fcff": "EBIT×(1−tax_rate)+D&A−CapEx−ΔNWC",
  "discount_years": [
    1,
    2,
    3,
    4,
    5
  ],
  "terminal": "Gordon，FY5 FCFF×(1+g)/(WACC−g) 再折现五年",
  "equity": "股权价值=企业价值+现金+短期投资−当期债务−非当期债务；每股价值除以加权平均稀释股数",
  "assumptions": "initial_growth、steady_ebit_margin、tax_rate、da_to_revenue、capex_to_revenue、wacc、terminal_growth 为透明开放假设；WACC>g，债务与现金的口径不得重复。"
}

公开合同 `/app/data/retrieval_contract.json` 包含相同字段、允许来源和公式约定。运行网络由 IPv4 sidecar 白名单限制，配置已写入 environment/docker-compose.yaml 和 task.toml；生效状态只能根据运行时探测报告说明。独立评分器会按隐藏原始 SEC 快照和容差核验取数值、来源/期间/字段、交叉勾稽及模型引用链，并重算工作簿。未执行的语言与禁止来源语义评审不会自动算通过。

#### W02 选用的 rubric（42 条，权重合计 110；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 2 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须交付可读取 model.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | Outputs 三个输出键须唯一 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | Sources 页 C 列须写单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 五个交付文件须按名提交 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 指定五个工作表名 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | EBIT按稳态利润率逐年计算 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC期初期末与符号正确 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期ΔNWC用FY0 NWC口径 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面规定FCFF公式 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | Gordon终值FY5折现五年 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值除以稀释股数 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 要求LibreOffice重算 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 模型须无错误值 |
| X-FM-001 | 公式与模型工程 | 题面要求集中管理的每个业务假设均在假设区拥有独立的可见输入单元格。 | rule | 主需 | Assumptions集中放假设 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不得硬编码假设 |
| X-FM-004 | 公式与模型工程 | 下游行项通过工作簿内活引用取得已在上游模块计算的对应值，未另行重填或独立重算。 | rule | 主需 | 取数须被活公式引用 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | FY1–FY5列对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 估值链无循环引用 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求提交memo.md |
| W-VALUE | 交付与来源完整性 | 每个要求取数的值与指定权威来源一致（在题面容差内） | rule | 主需 | 题面要求按权威10-K取数 |
| W-SOURCE | 交付与来源完整性 | 每个取数注明来源文件、期间和字段或页码，且来源属于允许范围 | rule | 主需 | sources.json需记录来源期间字段 |
| W-CROSS | 交付与来源完整性 | 至少一项关键数据用第二个独立来源或勾稽关系交叉验证 | rule | 主需 | 要求pretax_to_net_income勾稽 |
| W-USED | 交付与来源完整性 | 取到的数被模型公式实际引用，而不是另行手填 | rule | 主需 | 取数须被活公式引用 |
| W-NOFORBID | 交付与来源完整性 | 未使用禁止来源或截止日后的信息 | agent | 主需 | 题面明确禁止来源与截止后信息 |
| W-FAILURE | 交付与来源完整性 | 取数失败或数据冲突时如实披露并说明处理方法 | llm | 次需 | 要求如实记录失败与冲突 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 题面给定估值假设值 |
| X-IN-002 | 历史与会计口径 | 题面指定的恒定输入在其每个适用期间均被原样采用，不出现未经指定的期间变化。 | rule | 主需 | EBIT率与税率预测期恒定 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | NWC按指定公式推导 |
| X-IN-004 | 历史与会计口径 | 每项模型输入的适用日期均不晚于题面规定的信息截止日。 | agent | 主需 | 取数须不晚于截止日 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 须用FY2024财年期间 |
| X-IN-006 | 历史与会计口径 | 估值桥或比较价格使用题面基准日当天或之前最近一个可用值。 | rule | 主需 | 10Y取基准日或前最近值 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 五年显性预测期 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo数值须与模型输出一致 |
| X-TA-001 | 表达与专业可用性 | 每项外部输入均有可定位的来源记录，记录至少含文档或数据集名称及对应财务期间或数据日期。 | agent | 主需 | 取数项须有可定位来源记录 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 题面规定折现期1-5 |
| X-TA-005 | 表达与专业可用性 | 用于外推或推导预测的历史锚定期间数值在模型中可见。 | agent | 次需 | FY0收入与NWC锚定须可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 题面要求FCFF分行项 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值须引用可见单元格 |
| X-TA-009 | 表达与专业可用性 | 每个开放性预测假设均有书面推导，包含历史观察值及由该观察值到假设值的计算或映射关系。 | llm | 次需 | 开放假设须说明推导理由 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 程序强制必选项 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 程序强制必选项 |

### W03（W）

<details><summary>W03｜完整 spec</summary>

```json
{
  "ticker": "SBUX",
  "cik": 829224,
  "name": "Starbucks Corporation",
  "ir": "https://investor.starbucks.com/",
  "fiscal_year": "FY2024",
  "fiscal_year_start": "2023-10-02",
  "fiscal_year_end": "2024-09-29",
  "asof": "2024-11-27",
  "treasury_date": "2024-11-27",
  "task_id": "W03",
  "family": "W",
  "schema_version": "dcf-v3-task-v1",
  "language": "zh-CN",
  "required_fields": [
    "revenue",
    "operating_income",
    "pretax_income",
    "income_tax",
    "net_income_consolidated",
    "da",
    "capex",
    "diluted_shares",
    "cash",
    "short_term_investments",
    "receivables",
    "current_assets",
    "current_liabilities",
    "current_debt",
    "noncurrent_debt",
    "treasury_10y"
  ],
  "allowed_sources": [
    {
      "source_id": "SEC_COMPANYFACTS",
      "domains": [
        "data.sec.gov",
        "www.sec.gov"
      ],
      "url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000829224.json"
    },
    {
      "source_id": "COMPANY_IR_FILING",
      "domains": [
        "investor.starbucks.com",
        "s22.q4cdn.com",
        "s201.q4cdn.com",
        "d18rn0p25nwr6d.cloudfront.net"
      ],
      "url": "https://investor.starbucks.com/"
    },
    {
      "source_id": "UST_DAILY",
      "domains": [
        "home.treasury.gov"
      ],
      "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page=&_format=csv"
    }
  ],
  "required_artifacts": [
    "model.xlsx",
    "sources.json",
    "cross_validation.json",
    "retrieval_map.json",
    "memo.md"
  ],
  "valuation_assumptions": {
    "initial_growth": 0.06,
    "steady_ebit_margin": 0.15,
    "tax_rate": 0.24
  },
  "source_snapshot_sha256": {
    "../data/raw/SBUX_facts.json": "0deec882c9ad1727f308f0279acd19cbfa52669bb724fdcd1ce75d970d67015e",
    "../data/raw/DGS10.csv": "7e66e6c4d14dec358ccbaadd9b6d11d66e74c141e0df9caa8879d0f634668556"
  },
  "network": {
    "mode": "allowlist",
    "sidecar": "dcf-ipv4-gost-egress:v1",
    "configured": true,
    "verified": false,
    "status": "not_verified_by_generation"
  },
  "nonmechanical_status": "W-NOFORBID 与 W-FAILURE 需另行语义/代理评审，本次机械评分不自动给分。"
}
```

</details>

##### Starbucks Corporation（SBUX）：限定来源取数与五年 DCF

信息截止日为 **2024-11-27**，建模基准财年为 **FY2024**。必须先从指定来源取数再建模，不得先猜结果后补来源。所有题面、取数记录、模型标签和 memo 均用中文；语义 ID 与 XBRL 标签保留英文。

##### 允许来源与禁止事项

1. SEC EDGAR companyfacts：`https://data.sec.gov/api/xbrl/companyfacts/CIK0000829224.json`；也可使用 SEC Archives 中截止日前已申报的原始 10-K/10-K/A。
2. 公司 IR：`https://investor.starbucks.com/`，仅可核对同一期间的原始申报；同一 XBRL 事实与 IR 转载不构成两个独立会计事实。
3. 美国财政部日度收益率：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page=&_format=csv`，取 **2024-11-27** 的 10 Yr，如该日官方无值则用之前最近观测并写明实际日期。4.25% 在模型中写 0.0425。

仅允许上述 SEC、公司 IR（含申报文件必要的 CDN）和财政部域名。禁止自由搜索当前或历史股价、现成目标价、市场一致预期及截止日后信息；禁止用搜索摘要或第三方财经网站代替原始来源。历史权威真值按 filed≤截止日的 10-K 事实评定，不能取后来重述的同一期间值。

##### 必须取回的数据

| 语义 ID | 数据项 | 期间 | 提交单位 | 允许标签（按顺序使用首个有合规事实的标签） |
|---|---|---|---|---|
| `revenue` | 合并收入 | 2023-10-02 至 2024-09-29 | USD_millions | RevenueFromContractWithCustomerExcludingAssessedTax、Revenues、SalesRevenueNet、RevenueFromContractWithCustomerIncludingAssessedTax |
| `operating_income` | 经营利润（EBIT） | 2023-10-02 至 2024-09-29 | USD_millions | OperatingIncomeLoss |
| `pretax_income` | 税前利润 | 2023-10-02 至 2024-09-29 | USD_millions | IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest、IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments |
| `income_tax` | 所得税费用 | 2023-10-02 至 2024-09-29 | USD_millions | IncomeTaxExpenseBenefit |
| `net_income_consolidated` | 含非控股权益的合并净利润 | 2023-10-02 至 2024-09-29 | USD_millions | ProfitLoss、NetIncomeLoss |
| `da` | 折旧与摊销 | 2023-10-02 至 2024-09-29 | USD_millions | DepreciationDepletionAndAmortization、DepreciationAmortizationAndAccretionNet、DepreciationAndAmortization、Depreciation |
| `capex` | 购置固定资产现金支出（正数） | 2023-10-02 至 2024-09-29 | USD_millions | PaymentsToAcquirePropertyPlantAndEquipment、PaymentsToAcquireProductiveAssets |
| `diluted_shares` | 加权平均稀释股数 | 2023-10-02 至 2024-09-29 | shares_millions | WeightedAverageNumberOfDilutedSharesOutstanding |
| `cash` | 现金及现金等价物 | 截至 2024-09-29 | USD_millions | CashAndCashEquivalentsAtCarryingValue、CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents |
| `short_term_investments` | 短期投资 | 截至 2024-09-29 | USD_millions | ShortTermInvestments、MarketableSecuritiesCurrent、AvailableForSaleSecuritiesDebtSecuritiesCurrent |
| `receivables` | 应收账款净额 | 截至 2024-09-29 | USD_millions | AccountsReceivableNetCurrent、ReceivablesNetCurrent |
| `current_assets` | 流动资产合计 | 截至 2024-09-29 | USD_millions | AssetsCurrent |
| `current_liabilities` | 流动负债合计 | 截至 2024-09-29 | USD_millions | LiabilitiesCurrent |
| `current_debt` | 当期债务 | 截至 2024-09-29 | USD_millions | LongTermDebtCurrent、DebtCurrent、ShortTermBorrowings |
| `noncurrent_debt` | 非当期债务 | 截至 2024-09-29 | USD_millions | LongTermDebtNoncurrent、LongTermDebt |
| `treasury_10y` | 10 年期美国国债固定期限收益率 | 2024-11-27 | decimal | DGS10 |

金额须换算为百万美元，股数换算为百万股。`net_income_consolidated` 是含非控股权益的合并净利润（优先 ProfitLoss），不得与归母净利润混用。资本开支用现金流出正数。缺失不是零：取数失败必须在 sources.json 记录 failed、允许 URL、错误及处理，不得编造或静默补零。

##### 提交与公式要求

- `sources.json`：`items` 数组逐项覆盖上表，含 `field_id/value/unit/period_start/period_end/source_id/source_url/source_file/field/form/filed/accession/observed_at/status/error`。成功项必须含实际数值、允许域名 URL、正确期间与字段、申报号和 filed；`observed_at` 是实际取数日，不是申报日。
- `cross_validation.json`：`checks` 数组至少包含 `pretax_to_net_income`，计算 `pretax_income−income_tax−net_income_consolidated` 的 `difference`，引用来源表中三个字段。允许 `abs(difference)<=max(0.01, abs(net_income_consolidated)*0.02)`，超出或缺失必须在 memo 披露，不能强行改成零。
- `retrieval_map.json`：`items` 数组逐项含 `field_id/source_item_index/sheet/cell/used_by`。工作簿 `Sources` 页 A/B/C 列必须是 field_id、取数值、单位，且每个取数字段在 Forecast/Assumptions/DCF 中有活公式实际引用；不能把取数表摆在一旁、在别处另填历史值。
- `model.xlsx`：`Sources`、`Assumptions`、`Forecast`、`DCF`、`Outputs` 五页。Assumptions A/B 列放经营假设；Forecast A 列放语义键、C:G 为 FY1–FY5，含 revenue、ebit、da、capex、delta_nwc、reinvestment_component、fcff、discount_factor；DCF 计算显性期现值、Gordon 终值及股权桥；Outputs A/C 列输出 `enterprise_value/equity_value/value_per_share`。预测、再投资、折现和输出必须是活公式，并能通过 LibreOffice 重算与 WACC/g 扰动。
- `memo.md`：用中文说明实际取数日期、来源、开放预测理由、交叉验证差异及所有失败/冲突；披露“配置存在”不等于“白名单已经验证生效”。不需要也不得寻找股价来判断 DCF 是否合理。

##### 模型口径

{
  "forecast_years": 5,
  "growth": "FY1 使用 initial_growth，FY2–FY5 线性收敛至 terminal_growth",
  "ebit_margin": "预测期保持 steady_ebit_margin",
  "da_capex": "每年收入乘相应比率",
  "nwc": "经营 NWC=流动资产−现金−短期投资−(流动负债−当期债务)；FY1 ΔNWC=FY0 NWC×(FY1 收入/FY0 收入−1)，其后为本年减上年",
  "fcff": "EBIT×(1−tax_rate)+D&A−CapEx−ΔNWC",
  "discount_years": [
    1,
    2,
    3,
    4,
    5
  ],
  "terminal": "Gordon，FY5 FCFF×(1+g)/(WACC−g) 再折现五年",
  "equity": "股权价值=企业价值+现金+短期投资−当期债务−非当期债务；每股价值除以加权平均稀释股数",
  "assumptions": "initial_growth、steady_ebit_margin、tax_rate、da_to_revenue、capex_to_revenue、wacc、terminal_growth 为透明开放假设；WACC>g，债务与现金的口径不得重复。"
}

公开合同 `/app/data/retrieval_contract.json` 包含相同字段、允许来源和公式约定。运行网络由 IPv4 sidecar 白名单限制，配置已写入 environment/docker-compose.yaml 和 task.toml；生效状态只能根据运行时探测报告说明。独立评分器会按隐藏原始 SEC 快照和容差核验取数值、来源/期间/字段、交叉勾稽及模型引用链，并重算工作簿。未执行的语言与禁止来源语义评审不会自动算通过。

#### W03 选用的 rubric（42 条，权重合计 108；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 4 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须交付可读model.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | Outputs三个语义键须唯一数值 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | Sources须列单位且换算 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 五个指定交付文件须存在 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 指定五个工作表名称 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 预测期EBIT按稳态利润率 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC期初期末与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期ΔNWC用FY0经营NWC |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面规定FCFF公式 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | Gordon终值FY5折现 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值除稀释股数 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求预测与输出为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 要求LibreOffice重算 |
| X-FM-001 | 公式与模型工程 | 题面要求集中管理的每个业务假设均在假设区拥有独立的可见输入单元格。 | rule | 主需 | Assumptions页集中开放假设 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不得硬编码假设 |
| X-FM-004 | 公式与模型工程 | 下游行项通过工作簿内活引用取得已在上游模块计算的对应值，未另行重填或独立重算。 | rule | 主需 | 取数须经Sources活引用 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | FY1–FY5固定C:G列对齐 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求提交memo.md |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 要求FY1–FY5期间及中文标签 |
| W-VALUE | 交付与来源完整性 | 每个要求取数的值与指定权威来源一致（在题面容差内） | rule | 主需 | 16项取数须与10-K/财政部一致 |
| W-SOURCE | 交付与来源完整性 | 每个取数注明来源文件、期间和字段或页码，且来源属于允许范围 | rule | 主需 | sources.json须含来源期间字段 |
| W-CROSS | 交付与来源完整性 | 至少一项关键数据用第二个独立来源或勾稽关系交叉验证 | rule | 主需 | 要求税前-税-净利勾稽 |
| W-USED | 交付与来源完整性 | 取到的数被模型公式实际引用，而不是另行手填 | rule | 主需 | Sources页须被活公式引用 |
| W-FAILURE | 交付与来源完整性 | 取数失败或数据冲突时如实披露并说明处理方法 | llm | 次需 | 失败/冲突须记录并披露 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 题面给定增长、利润率、税率假设 |
| X-IN-002 | 历史与会计口径 | 题面指定的恒定输入在其每个适用期间均被原样采用，不出现未经指定的期间变化。 | rule | 主需 | 预测期保持稳态EBIT利润率 |
| X-IN-003 | 历史与会计口径 | 从历史数据推导的输入使用题面指定的历史窗口与公式，推导结果与独立重算值一致。 | rule | 主需 | FY0经营NWC公式已指定 |
| X-IN-004 | 历史与会计口径 | 每项模型输入的适用日期均不晚于题面规定的信息截止日。 | agent | 主需 | filed须不晚于截止日 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 须用FY2024财年期间数据 |
| X-IN-006 | 历史与会计口径 | 估值桥或比较价格使用题面基准日当天或之前最近一个可用值。 | rule | 主需 | 国债收益率取基准日或之前最近值 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 显性预测期为FY1–FY5 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo 数值须与模型一致 |
| X-TA-001 | 表达与专业可用性 | 每项外部输入均有可定位的来源记录，记录至少含文档或数据集名称及对应财务期间或数据日期。 | agent | 主需 | 外部取数需可定位来源记录 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 折现期1-5需可见 |
| X-TA-005 | 表达与专业可用性 | 用于外推或推导预测的历史锚定期间数值在模型中可见。 | agent | 次需 | FY0收入与NWC锚点需可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 题面要求FCFF分项行 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值引用FY5与g |
| X-TA-009 | 表达与专业可用性 | 每个开放性预测假设均有书面推导，包含历史观察值及由该观察值到假设值的计算或映射关系。 | llm | 次需 | memo须说明开放假设理由 |
| W-NOFORBID | 交付与来源完整性 | 未使用禁止来源或截止日后的信息 | agent | 主需 | 程序强制必选项 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 程序强制必选项 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 程序强制必选项 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 程序强制必选项 |

### W04（W）

<details><summary>W04｜完整 spec</summary>

```json
{
  "ticker": "ADBE",
  "cik": 796343,
  "name": "Adobe Inc.",
  "ir": "https://www.adobe.com/investor-relations.html",
  "fiscal_year": "FY2024",
  "fiscal_year_start": "2023-12-02",
  "fiscal_year_end": "2024-11-29",
  "asof": "2025-02-14",
  "treasury_date": "2025-02-14",
  "task_id": "W04",
  "family": "W",
  "schema_version": "dcf-v3-task-v1",
  "language": "zh-CN",
  "required_fields": [
    "revenue",
    "operating_income",
    "pretax_income",
    "income_tax",
    "net_income_consolidated",
    "da",
    "capex",
    "diluted_shares",
    "cash",
    "short_term_investments",
    "receivables",
    "current_assets",
    "current_liabilities",
    "current_debt",
    "noncurrent_debt",
    "treasury_10y"
  ],
  "allowed_sources": [
    {
      "source_id": "SEC_COMPANYFACTS",
      "domains": [
        "data.sec.gov",
        "www.sec.gov"
      ],
      "url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000796343.json"
    },
    {
      "source_id": "COMPANY_IR_FILING",
      "domains": [
        "www.adobe.com",
        "s22.q4cdn.com",
        "s201.q4cdn.com",
        "d18rn0p25nwr6d.cloudfront.net"
      ],
      "url": "https://www.adobe.com/investor-relations.html"
    },
    {
      "source_id": "UST_DAILY",
      "domains": [
        "home.treasury.gov"
      ],
      "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2025/all?type=daily_treasury_yield_curve&field_tdr_date_value=2025&page=&_format=csv"
    }
  ],
  "required_artifacts": [
    "model.xlsx",
    "sources.json",
    "cross_validation.json",
    "retrieval_map.json",
    "memo.md"
  ],
  "valuation_assumptions": {
    "initial_growth": 0.09,
    "steady_ebit_margin": 0.32,
    "tax_rate": 0.2
  },
  "source_snapshot_sha256": {
    "../data/raw/ADBE_facts.json": "86a5689aa9aa7b0f9e95be21b48b0305376e014c8dbf3b8bb3b4b131f1b6a0c4",
    "../data/raw/DGS10.csv": "7e66e6c4d14dec358ccbaadd9b6d11d66e74c141e0df9caa8879d0f634668556"
  },
  "network": {
    "mode": "allowlist",
    "sidecar": "dcf-ipv4-gost-egress:v1",
    "configured": true,
    "verified": false,
    "status": "not_verified_by_generation"
  },
  "nonmechanical_status": "W-NOFORBID 与 W-FAILURE 需另行语义/代理评审，本次机械评分不自动给分。"
}
```

</details>

##### Adobe Inc.（ADBE）：限定来源取数与五年 DCF

信息截止日为 **2025-02-14**，建模基准财年为 **FY2024**。必须先从指定来源取数再建模，不得先猜结果后补来源。所有题面、取数记录、模型标签和 memo 均用中文；语义 ID 与 XBRL 标签保留英文。

##### 允许来源与禁止事项

1. SEC EDGAR companyfacts：`https://data.sec.gov/api/xbrl/companyfacts/CIK0000796343.json`；也可使用 SEC Archives 中截止日前已申报的原始 10-K/10-K/A。
2. 公司 IR：`https://www.adobe.com/investor-relations.html`，仅可核对同一期间的原始申报；同一 XBRL 事实与 IR 转载不构成两个独立会计事实。
3. 美国财政部日度收益率：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2025/all?type=daily_treasury_yield_curve&field_tdr_date_value=2025&page=&_format=csv`，取 **2025-02-14** 的 10 Yr，如该日官方无值则用之前最近观测并写明实际日期。4.25% 在模型中写 0.0425。

仅允许上述 SEC、公司 IR（含申报文件必要的 CDN）和财政部域名。禁止自由搜索当前或历史股价、现成目标价、市场一致预期及截止日后信息；禁止用搜索摘要或第三方财经网站代替原始来源。历史权威真值按 filed≤截止日的 10-K 事实评定，不能取后来重述的同一期间值。

##### 必须取回的数据

| 语义 ID | 数据项 | 期间 | 提交单位 | 允许标签（按顺序使用首个有合规事实的标签） |
|---|---|---|---|---|
| `revenue` | 合并收入 | 2023-12-02 至 2024-11-29 | USD_millions | RevenueFromContractWithCustomerExcludingAssessedTax、Revenues、SalesRevenueNet、RevenueFromContractWithCustomerIncludingAssessedTax |
| `operating_income` | 经营利润（EBIT） | 2023-12-02 至 2024-11-29 | USD_millions | OperatingIncomeLoss |
| `pretax_income` | 税前利润 | 2023-12-02 至 2024-11-29 | USD_millions | IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest、IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments |
| `income_tax` | 所得税费用 | 2023-12-02 至 2024-11-29 | USD_millions | IncomeTaxExpenseBenefit |
| `net_income_consolidated` | 含非控股权益的合并净利润 | 2023-12-02 至 2024-11-29 | USD_millions | ProfitLoss、NetIncomeLoss |
| `da` | 折旧与摊销 | 2023-12-02 至 2024-11-29 | USD_millions | DepreciationDepletionAndAmortization、DepreciationAmortizationAndAccretionNet、DepreciationAndAmortization、Depreciation |
| `capex` | 购置固定资产现金支出（正数） | 2023-12-02 至 2024-11-29 | USD_millions | PaymentsToAcquirePropertyPlantAndEquipment、PaymentsToAcquireProductiveAssets |
| `diluted_shares` | 加权平均稀释股数 | 2023-12-02 至 2024-11-29 | shares_millions | WeightedAverageNumberOfDilutedSharesOutstanding |
| `cash` | 现金及现金等价物 | 截至 2024-11-29 | USD_millions | CashAndCashEquivalentsAtCarryingValue、CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents |
| `short_term_investments` | 短期投资 | 截至 2024-11-29 | USD_millions | ShortTermInvestments、MarketableSecuritiesCurrent、AvailableForSaleSecuritiesDebtSecuritiesCurrent |
| `receivables` | 应收账款净额 | 截至 2024-11-29 | USD_millions | AccountsReceivableNetCurrent、ReceivablesNetCurrent |
| `current_assets` | 流动资产合计 | 截至 2024-11-29 | USD_millions | AssetsCurrent |
| `current_liabilities` | 流动负债合计 | 截至 2024-11-29 | USD_millions | LiabilitiesCurrent |
| `current_debt` | 当期债务 | 截至 2024-11-29 | USD_millions | LongTermDebtCurrent、DebtCurrent、ShortTermBorrowings |
| `noncurrent_debt` | 非当期债务 | 截至 2024-11-29 | USD_millions | LongTermDebtNoncurrent、LongTermDebt |
| `treasury_10y` | 10 年期美国国债固定期限收益率 | 2025-02-14 | decimal | DGS10 |

金额须换算为百万美元，股数换算为百万股。`net_income_consolidated` 是含非控股权益的合并净利润（优先 ProfitLoss），不得与归母净利润混用。资本开支用现金流出正数。缺失不是零：取数失败必须在 sources.json 记录 failed、允许 URL、错误及处理，不得编造或静默补零。

##### 提交与公式要求

- `sources.json`：`items` 数组逐项覆盖上表，含 `field_id/value/unit/period_start/period_end/source_id/source_url/source_file/field/form/filed/accession/observed_at/status/error`。成功项必须含实际数值、允许域名 URL、正确期间与字段、申报号和 filed；`observed_at` 是实际取数日，不是申报日。
- `cross_validation.json`：`checks` 数组至少包含 `pretax_to_net_income`，计算 `pretax_income−income_tax−net_income_consolidated` 的 `difference`，引用来源表中三个字段。允许 `abs(difference)<=max(0.01, abs(net_income_consolidated)*0.02)`，超出或缺失必须在 memo 披露，不能强行改成零。
- `retrieval_map.json`：`items` 数组逐项含 `field_id/source_item_index/sheet/cell/used_by`。工作簿 `Sources` 页 A/B/C 列必须是 field_id、取数值、单位，且每个取数字段在 Forecast/Assumptions/DCF 中有活公式实际引用；不能把取数表摆在一旁、在别处另填历史值。
- `model.xlsx`：`Sources`、`Assumptions`、`Forecast`、`DCF`、`Outputs` 五页。Assumptions A/B 列放经营假设；Forecast A 列放语义键、C:G 为 FY1–FY5，含 revenue、ebit、da、capex、delta_nwc、reinvestment_component、fcff、discount_factor；DCF 计算显性期现值、Gordon 终值及股权桥；Outputs A/C 列输出 `enterprise_value/equity_value/value_per_share`。预测、再投资、折现和输出必须是活公式，并能通过 LibreOffice 重算与 WACC/g 扰动。
- `memo.md`：用中文说明实际取数日期、来源、开放预测理由、交叉验证差异及所有失败/冲突；披露“配置存在”不等于“白名单已经验证生效”。不需要也不得寻找股价来判断 DCF 是否合理。

##### 模型口径

{
  "forecast_years": 5,
  "growth": "FY1 使用 initial_growth，FY2–FY5 线性收敛至 terminal_growth",
  "ebit_margin": "预测期保持 steady_ebit_margin",
  "da_capex": "每年收入乘相应比率",
  "nwc": "经营 NWC=流动资产−现金−短期投资−(流动负债−当期债务)；FY1 ΔNWC=FY0 NWC×(FY1 收入/FY0 收入−1)，其后为本年减上年",
  "fcff": "EBIT×(1−tax_rate)+D&A−CapEx−ΔNWC",
  "discount_years": [
    1,
    2,
    3,
    4,
    5
  ],
  "terminal": "Gordon，FY5 FCFF×(1+g)/(WACC−g) 再折现五年",
  "equity": "股权价值=企业价值+现金+短期投资−当期债务−非当期债务；每股价值除以加权平均稀释股数",
  "assumptions": "initial_growth、steady_ebit_margin、tax_rate、da_to_revenue、capex_to_revenue、wacc、terminal_growth 为透明开放假设；WACC>g，债务与现金的口径不得重复。"
}

公开合同 `/app/data/retrieval_contract.json` 包含相同字段、允许来源和公式约定。运行网络由 IPv4 sidecar 白名单限制，配置已写入 environment/docker-compose.yaml 和 task.toml；生效状态只能根据运行时探测报告说明。独立评分器会按隐藏原始 SEC 快照和容差核验取数值、来源/期间/字段、交叉勾稽及模型引用链，并重算工作簿。未执行的语言与禁止来源语义评审不会自动算通过。

#### W04 选用的 rubric（41 条，权重合计 107；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 2 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须交付可读model.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | Outputs三键须唯一数值 |
| 01-UNIT | 交付与来源完整性 | 金额、股数与比率的单位在提交中明确 | agent | 次需 | Sources须列明单位 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 五个指定交付文件 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 指定五个工作表名 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | EBIT按稳态利润率逐期计算 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | ΔNWC符号及后续年差分 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | FY1 ΔNWC用FY0 NWC口径 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面规定FCFF公式 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | Gordon终值按FY5折现 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值除以稀释股数 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 要求LibreOffice重算 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 无外链及错误值 |
| X-FM-001 | 公式与模型工程 | 题面要求集中管理的每个业务假设均在假设区拥有独立的可见输入单元格。 | rule | 主需 | Assumptions页集中放假设 |
| X-FM-002 | 公式与模型工程 | 抽样计算公式未直接嵌入业务假设数值常数，题面允许的数学常数除外。 | rule | 主需 | 公式不得硬编码假设 |
| X-FM-004 | 公式与模型工程 | 下游行项通过工作簿内活引用取得已在上游模块计算的对应值，未另行重填或独立重算。 | rule | 主需 | 取数须被活公式引用 |
| X-FM-005 | 公式与模型工程 | 同一期间在相关预测、现金流、折现期及现值行中占据相同列，不存在一期错位。 | rule | 主需 | FY1–FY5同列对齐 |
| X-FM-007 | 公式与模型工程 | 估值计算链不存在未声明的循环引用。 | rule | 主需 | 估值链不应有循环 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求提交中文memo.md |
| W-VALUE | 交付与来源完整性 | 每个要求取数的值与指定权威来源一致（在题面容差内） | rule | 主需 | 取数值须与10-K一致 |
| W-SOURCE | 交付与来源完整性 | 每个取数注明来源文件、期间和字段或页码，且来源属于允许范围 | rule | 主需 | sources.json记录来源期间字段 |
| W-CROSS | 交付与来源完整性 | 至少一项关键数据用第二个独立来源或勾稽关系交叉验证 | rule | 主需 | 要求税前到净利勾稽 |
| W-USED | 交付与来源完整性 | 取到的数被模型公式实际引用，而不是另行手填 | rule | 主需 | 取数须被活公式引用 |
| W-NOFORBID | 交付与来源完整性 | 未使用禁止来源或截止日后的信息 | agent | 主需 | 禁止非白名单及截止后信息 |
| W-FAILURE | 交付与来源完整性 | 取数失败或数据冲突时如实披露并说明处理方法 | llm | 次需 | 失败须记录并在memo披露 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | 增长、利润率、税率给定值须一致 |
| X-IN-002 | 历史与会计口径 | 题面指定的恒定输入在其每个适用期间均被原样采用，不出现未经指定的期间变化。 | rule | 主需 | 预测期 EBIT 利润率保持不变 |
| X-IN-004 | 历史与会计口径 | 每项模型输入的适用日期均不晚于题面规定的信息截止日。 | agent | 主需 | 取数须早于截止日 2025-02-14 |
| X-IN-005 | 历史与会计口径 | 历史财务行项使用题面指定的期间类型，未把财年、日历年、LTM、YTD 或单季数值混作同一期间输入。 | rule | 主需 | 须用 FY2024 财年期间 |
| X-IN-006 | 历史与会计口径 | 估值桥或比较价格使用题面基准日当天或之前最近一个可用值。 | rule | 主需 | 国债收益率取基准日或之前最近值 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 预测期须为 FY1–FY5 五年 |
| X-IC-007 | 表达与专业可用性 | 摘要、幻灯片或 PDF 展示的每个模型数值与对应模型输出的相对差异不超过题面容差；题面未给容差时按显示精度相等。 | agent | 主需 | memo 数值须与模型输出一致 |
| X-TA-001 | 表达与专业可用性 | 每项外部输入均有可定位的来源记录，记录至少含文档或数据集名称及对应财务期间或数据日期。 | agent | 主需 | 取数须有可定位来源记录 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 折现期1-5须可见 |
| X-TA-005 | 表达与专业可用性 | 用于外推或推导预测的历史锚定期间数值在模型中可见。 | agent | 次需 | FY0锚定值须在模型可见 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 要求FCFF分项行 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值引用单元格 |
| X-TA-009 | 表达与专业可用性 | 每个开放性预测假设均有书面推导，包含历史观察值及由该观察值到假设值的计算或映射关系。 | llm | 次需 | 开放假设需书面推导 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 程序强制必选项 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 程序强制必选项 |

### R01（R）

<details><summary>R01｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "R01",
  "family": "R",
  "company": "衡岳流体装备",
  "reused_from": "exp/dcf_factory/B/tasks/B01（v1 B 方案）",
  "reuse_reason": "历史版本中真实模型得分低、暴露出实质建模错误；原样复用题面数据、参考答案和评分器",
  "prior_scores": {
    "kimi-k3.1-pro": "0.564（类别清零后 0.435）",
    "claude-opus-5-5": "0.250（原始 87.5/100，公式门槛封顶；类别清零后 0.821）",
    "qwen3.8-max": "连接中断，无交付，不计分"
  },
  "observed_failures": [
    "首段年中折现时点错（Kimi 0.3137，应为 0.1274）",
    "半年历史聚合到财年错位",
    "缺语义标签导致隐藏扰动无法执行",
    "Forecast 活公式失效（Claude）"
  ],
  "theme": "非自然财年、半年历史、残期＋3 个完整财年、实际天数折现、固定资产与无形资产滚动",
  "grader": "原版本评分器（tests/grader.py），参考答案在 v3 本地复验 reward=1.0，空白工作簿被拒"
}
```

</details>

##### R01｜衡岳流体装备残期 DCF 估值

从空白工作簿建立可重算模型，仅使用 `/app/inputs.xlsx` 和 `/app/inputs.json`。二者事实一致，若显示格式不同，以 JSON 的语义键和数值为准。禁止联网；所有假设已给全，不需要开放判断。
最终交付 `/app/output.xlsx`。不得提交已有参考文件、静态答案或只有最终结果的表格。

##### 一、单位与公开事实

金额均为百万元；股数为百万股；每股价值为元。日期为公历日期。历史收入、成本、费用均是披露期实际金额，余额是估值日时点数。公开输入无未来数据、无估值答案。
最近完整财年末为 2025-09-30，估值日为 2026-02-13。预测覆盖本财年余下残期及随后三个完整财年，共四段：2026-09-30, 2027-09-30, 2028-09-30, 2029-09-30。历史表为半年披露；完整财年取上下半年之和，LTM 取最近两个半年之和。

##### 二、历史与 LTM

历史表为半年披露；完整财年取上下半年之和，LTM 取最近两个半年之和。
完整年度 EBIT = 完整年度收入 - 完整年度销货成本 - 完整年度其他经营费用；LTM EBIT 同理。公开历史行已经标记所属财年。资产负债表余额不加总。
估值日 NWC = 应收账款 + 存货 - 应付账款 + 其他经营净营运资本，使用 opening 组的时点数。LTM 只用于历史分析与理解年化口径，不用于替代下述残期预测。

##### 三、预测驱动与营运资本

完整年度收入 = 销量 × 平均单价。销量为全年数量，平均单价为百万元/数量单位。
本财年完整年度天数 = 2026-09-30 - 2025-09-30（日期差，不加一天）。残期活动比例 = (2026-09-30 - 估值日) / 本财年完整年度天数。首段收入、销货成本、其他经营费用、资本开支、无形资产新增均 = 对应完整年度金额 × 残期活动比例。随后三段的活动比例为 1。
销货成本 = 本段收入 × 对应年度成本率；其他经营费用 = 本段收入 × 对应年度费用率；EBIT = 收入 - 成本 - 费用；现金税 = EBIT × 现金税率；NOPAT = EBIT - 现金税。无亏损抵免、利息费用不再重复扣除。
应收 = 完整年度收入 × 应收天数/365；存货 = 完整年度销货成本 × 存货天数/365；应付 = 完整年度销货成本 × 应付天数/365；其他经营净营运资本 = 完整年度收入 × 给定比率。NWC = 应收 + 存货 - 应付 + 其他经营净营运资本。
首段 NWC 增量 = 本财年末 NWC - 估值日 NWC；后续 = 本年末 NWC - 上年末 NWC。即使首段只预测残期，也不得把营运资本余额乘残期比例。

##### 四、资产滚动与 FCFF

固定资产：期末净额 = 期初净额 + 资本开支 - 折旧。首段期初为估值日固定资产净额，后续期初为上一期末。期间比例 = 本段实际天数/365；首段即财年末与上一财年末的实际天数/365，非残期活动比例。
现有固定资产折旧 = 期初净额 × 年折旧率 × 期间比例；新采购折旧 = 本段资本开支 × 年折旧率 × 期间比例 × 0.5。固定资产折旧 = 两者之和。
若 asset_count=2，启用无形资产，滚动方式相同：期初 + 新增 - 摊销 = 期末；现有资产摊销 = 期初净额 × 年摊销率 × 期间比例；新增资产摊销 = 本段新增 × 年摊销率 × 期间比例 × 0.5。D&A = 固定资产折旧 + 无形资产摊销。若 asset_count=1，仅使用固定资产池：Forecast 第 23–26 行的无形期初、新增、摊销、期末均填公式零，原始输入中未使用的无形余额字段不进入 FCFF 或股权桥。
FCFF = NOPAT + D&A - 资本开支 - 无形资产新增 - NWC 增量。首段已是残期现金流，不得再乘残期比例；后续完整年也不得再乘期间比例。

##### 五、WACC、时间轴、终值与股权桥

WACC = 股权权重 × 股权成本 + (1-股权权重) × 税前债务成本 × (1-债务税盾税率)。所有参数均来自输入，不自行估算 Beta 或风险溢价。
首段期末累计年数 = (本财年末 - 估值日)/365；后续各段期末累计年数 = 上一段累计年数 + 本段实际天数/365。年中折现：各段折现指数 = 期末累计年数 - 本段实际天数/(2×365)。
每段现值 = FCFF / (1+WACC)^折现指数。明确预测期价值为四段现值之和。Gordon：终值 = 最后完整财年 FCFF × (1+g) / (WACC-g)。
终值发生在最后完整财年末，其折现指数 = 最后一段期末累计年数；即使采用年中折现也不得再减半年或后移一年。终值现值 = 终值 / (1+WACC)^终值折现指数。EV = 明确预测期价值 + 终值现值。
股权价值 = EV + 现金及等价物 + 非经营投资 - 短期借款 - 长期借款 - 少数股东权益 + 其他非经营调整。稀释股数 = 基础股数 + 稀释增量；每股价值 = 股权价值 / 稀释股数。

##### 六、输出页、单元格与公式要求

只提交一个 `/app/output.xlsx`，至少包含 `Inputs`、`Historical`、`Forecast`、`Valuation`、`Checks` 五页。必须自己创建工作表、标签和公式。
`Inputs` 页第一列按公开 `inputs.json` 的语义键书写输入标签（如 `valuation_date`、`wacc.cost_of_equity`、`capex`），历史与预测数组按同一行四列排放。允许复制原始输入内容，但不得改变原始事实。公开文件未提供任何模板或输出公式。
`Historical`：第 3 行依次为期间、收入、销货成本、其他经营费用、EBIT。第 4 行起每个完整财年一行（按时间升序），最后再加 LTM 一行；`G4` 为估值日 NWC。所有经营聚合必须公式链接 Inputs。
`Forecast`：B:E 为残期及随后三个完整财年。第 5–39 行项目如下，单元格必须放在对应行。A13 必须为“本预测段收入”，A34 必须为“FCFF”。

- 第 5 行：期间类型。
- 第 6 行：现金流期间开始（残期为估值日）。
- 第 7 行：财年末。
- 第 8 行：资产折旧期间比例（实际天数/365）。
- 第 9 行：经营活动比例（残期天数/财年天数）。
- 第 10 行：销量/平均营业门店。
- 第 11 行：平均单价/年化单店收入。
- 第 12 行：完整年度收入（驱动口径）。
- 第 13 行：本预测段收入。
- 第 14 行：本预测段销货成本。
- 第 15 行：本预测段其他经营费用。
- 第 16 行：EBIT。
- 第 17 行：现金税。
- 第 18 行：NOPAT。
- 第 19 行：期初固定资产净额。
- 第 20 行：资本开支。
- 第 21 行：固定资产折旧。
- 第 22 行：期末固定资产净额。
- 第 23 行：期初无形资产净额。
- 第 24 行：无形资产新增。
- 第 25 行：无形资产摊销。
- 第 26 行：期末无形资产净额。
- 第 27 行：折旧与摊销。
- 第 28 行：应收账款（期末）。
- 第 29 行：存货（期末）。
- 第 30 行：应付账款（期末）。
- 第 31 行：其他经营净营运资本（期末）。
- 第 32 行：NWC（期末）。
- 第 33 行：NWC 增量。
- 第 34 行：FCFF。
- 第 35 行：期末累计折现年数。
- 第 36 行：现金流折现年数。
- 第 37 行：折现因子。
- 第 38 行：FCFF 现值。
- 第 39 行：EBITDA。

`Valuation`：A 列为项目，B 列为数值。A21 必须为“每股价值（元）”。固定映射如下。

- B6：明确预测期 FCFF 现值。
- B7：终值（最后完整财年末）。
- B8：终值折现年数。
- B9：终值现值。
- B10：企业价值 EV。
- B11：+现金及等价物。
- B12：+非经营投资。
- B13：-短期借款。
- B14：-长期借款。
- B15：-少数股东权益。
- B16：+其他非经营调整。
- B17：股权价值。
- B18：基础股数。
- B19：稀释增量。
- B20：稀释股数。
- B21：每股价值（元）。
- B22：WACC。
- B23：永续增长率。
- B24：退出 EBITDA 倍数。

`Checks` 页自行设置勾稽检查，至少验证：残期比例、首段 NWC 增量、最后一年资产滚动、EV 加总、终值时点、Gordon 时 WACC>g（或退出倍数为正）。不得用检查页代替公式联动。

除输入、日期和说明文字外，历史聚合、预测、DCF、终值、股权桥均须是依赖 Inputs 的活公式；禁止使用宏、Data Table、外部链接、Excel 专属函数或隐藏脚本。评分将用 LibreOffice 重算，并修改估值日、驱动、营运资本、WACC、终值与桥接输入后再次核对。

请自行用 LibreOffice 重算并打开检查；不要只保存未计算公式。

#### R01 选用的 rubric（29 条，权重合计 79；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 0 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 须交付可读output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 固定单元格映射输出 |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 指定五个工作表名称 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 半年历史聚合到财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | LTM为最近两个半年之和 |
| X-IN-001 | 历史与会计口径 | 题面给定的每个输入值均与输入包一致，相对差异不超过题面容差；题面未给容差时精确相等。 | rule | 主需 | Inputs页须与输入包一致 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 残期加三个完整财年共四段 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 各年成本率费用率分别适用 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 后续段NWC增量期初期末与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首段用估值日NWC为期初 |
| 03-DAYS | 经营预测 | 应收、存货与应付使用实际年度天数口径 | rule | 次需 | 营运资本按全年额×天数/365 |
| B-INTANG-ROLL | 经营预测 | 无形资产按期初加新增减摊销独立滚动，不与固定资产合并 | rule | 主需 | 无形资产独立滚动 |
| A-DRIVER | 经营预测 | 收入由该行业规定的业务驱动构造，而不是单一增长率 | rule | 主需 | 收入=销量×平均单价 |
| 04-PPE | 三表勾稽 | 长期资产由期初加新增减折旧摊销滚动 | rule | 主需 | 题面要求固定与无形资产滚动 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | FCFF口径为核心公式 |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数年中折现，曾出错 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值时点与折现明确规定 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 题面要求完整股权桥 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 每股价值除以稀释股数 |
| B-INTANG-FCFF | DCF与估值桥 | 无形资产新增在 FCFF 中扣减，摊销作为非现金项加回 | rule | 主需 | 题含无形资产滚动 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 残期首段为题目核心 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 题面要求结果单元格为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | LibreOffice重算须与真值一致 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 题面明示隐藏扰动核对 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 第二组扰动传导检验 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接与错误值 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 题面要求第35-36行折现年数 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | FCFF各组成项须独立成行 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | Gordon终值须引用可见单元格 |

### R02（R）

<details><summary>R02｜完整 spec</summary>

```json
{
  "schema_version": "v3.0",
  "task_id": "R02",
  "family": "R",
  "company": "企业档案订阅",
  "reused_from": "exp/dcf_factory_v2/tasks/F01（v2 F 方案）",
  "reuse_reason": "历史版本中真实模型得分低、暴露出实质建模错误；原样复用题面数据、参考答案和评分器",
  "prior_scores": {
    "kimi-k3.1-pro": "旧版 0.040 ×3，最终版 0.100",
    "qwen3.8-max": "多次 0.0（多数为断连无交付，不作能力结论）"
  },
  "observed_failures": [
    "缺新语义输出键",
    "历史 EBIT、客户驱动、现金收款与合同负债、NWC、DCF 和扰动传导均有差异"
  ],
  "theme": "订阅客户新增/流失/定价、合同负债与现金收款、季度历史、残期、双终值加权、稀释股权桥",
  "grader": "原版本评分器（tests/grader.py），参考答案在 v3 本地复验 reward=1.0，空白工作簿被拒"
}
```

</details>

##### R02｜企业档案订阅经营预测与估值

你是估值分析师。根据 `/app/inputs.xlsx` 和 `/app/inputs.json` 建立公式驱动的模型，保存为 `/app/output.xlsx`。禁止网络与外部链接。

##### 业务与时间范围
- 场景：企业档案订阅；经营单位：千家客户；收入单价口径：百万元/千家客户/年。
- 估值日 `2024-05-10`，最近完整财年末 `2024-02-28`，显式预测 `4` 期；原始历史按季度披露。
- 汇总最近完整财年与截至估值日的LTM。金额百万元、股数百万股、比率小数。SBC计入经营成本；非经常收益不属于规范化经营EBIT。
- 首个预测段只包含估值日后经营活动，采用实际天数/365及年中折现惯例；终值位于最后完整财年末。余额型营运资本仍使用完整年度经营驱动；首期变化为首个期末余额减估值日余额（余额不按残期活动比例缩放），后续为相邻期末差额。

##### 建模目标
- 结合客户新增、流失和定价，构建订阅客户经营预测；不得把期末客户数直接当作全期平均。
- 区分订阅/服务收入确认与合同负债、现金收款及营运资本；采用Inputs提供的deferred_pct口径。
- 分别展示永续增长与退出倍数终值，再按gordon_weight合成。
- 从EBIT、现金税、折旧摊销、再投资及营运资本变化构建无杠杆FCFF，再折现、计算终值并完成EV到稀释每股价值的桥接。债务、租赁及少数股权的口径见Inputs。

##### 输出与可审计性
在 `Outputs` 页以 A 列键名、同行 B 列公式提交结果；中间模型自由。
要求的键见 `/app/inputs.json` 的 `public_output_keys` 及公开键清单。另提交 `/app/memo.md`，简述最重要的价值驱动和至少一个模型局限。保留公开 `Inputs` 页语义键与 C/D/E… 的 P1/P2… 向量，预测、历史聚合和估值须由这些输入的活公式计算。不得粘贴完整数值模型代替公式。LibreOffice重算与隐藏输入扰动将用于检查依赖传导。

#### R02 选用的 rubric（36 条，权重合计 92；挑选模型 `claude-opus-5-5`，LLM 成功=True，程序补齐 1 条）

| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |
|---|---|---|---|---|---|
| 01-FILE | 交付与来源完整性 | 按要求提交可读取的 Excel 工作簿 | rule | 主需 | 需提交可读取output.xlsx |
| 01-KEYS | 交付与来源完整性 | 每一个要求的语义输出键均存在且只有一个数值 | rule | 主需 | 历史失败含缺输出键 |
| X-IF-001a | 交付与来源完整性 | 题面要求的每个交付文件均以指定文件名存在 | rule | 主需 | 须交付output.xlsx与memo.md |
| X-IF-002 | 交付与来源完整性 | 题面要求的工作表名称及数量与工作簿实际结构完全一致，未以默认名称替代指定名称。 | rule | 主需 | 指定Outputs页并保留Inputs页 |
| 02-FY | 历史与会计口径 | 完整财年历史收入与规范化 EBIT 来自正确期间聚合 | rule | 主需 | 季度历史需聚合完整财年 |
| 02-LTM | 历史与会计口径 | LTM 恰包含要求的季度或半年，未重复年化 | rule | 主需 | 要求截至估值日的LTM |
| 02-REPORTED | 历史与会计口径 | 非经常收益未混入规范化经营 EBIT | rule | 主需 | 非经常收益须排除 |
| 02-SBC | 历史与会计口径 | 股份支付作为经营成本处理且未在 FCFF 中加回 | rule | 主需 | 题面规定SBC计入经营成本 |
| 02-COLLECT | 历史与会计口径 | 现金收款等于确认收入加合同负债增加 | rule | 次需 | 现金收款与合同负债勾稽 |
| X-IN-007 | 历史与会计口径 | 模型的预测期序列与题面指定的起止期间完全一致。 | rule | 主需 | 指定残期加4期预测 |
| 03-DRIVER | 经营预测 | 期末经营基数等于期初减流失加新增 | rule | 主需 | 客户期初减流失加新增滚动 |
| 03-AVERAGE | 经营预测 | 收入采用平均经营基数乘以单位收入及期间活动比例 | rule | 主需 | 题面禁止以期末客户代平均 |
| 03-NWC | 经营预测 | 营运资本变动使用正确期初、期末与符号 | rule | 主需 | 营运资本变化期末与符号 |
| B-NWC-OPEN | 经营预测 | 首期 ΔNWC 使用题面指定的期初余额口径（估值日余额或最近财年末余额） | rule | 主需 | 首期以估值日余额为期初 |
| 05-FCFF | DCF与估值桥 | FCFF 从无杠杆税后 EBIT 出发并扣除再投资与营运资本增加 | rule | 主需 | 题面要求EBIT起算无杠杆FCFF |
| 05-DF | DCF与估值桥 | 折现期从估值日按实际天数计量并遵守年中约定 | rule | 主需 | 实际天数/365及年中折现 |
| 05-DUAL | DCF与估值桥 | Gordon 与退出终值分别计算再按权重合成 | rule | 主需 | 双终值分别计算并按权重合成 |
| 05-TV | DCF与估值桥 | 终值以最后完整年度为时点且以 WACC 折现 | rule | 主需 | 终值位于最后完整财年末 |
| 05-BRIDGE | DCF与估值桥 | 企业价值桥包含全部现金、投资、债务、租赁和少数股权 | rule | 主需 | 债务租赁少数股权桥接 |
| 05-DILUTION | DCF与估值桥 | 库存股法增量与 RSU 均进入稀释股数 | rule | 次需 | 稀释股权桥 |
| 05-VPS | DCF与估值桥 | 每股价值以股权价值除以稀释股数 | rule | 主需 | 要求稀释每股价值 |
| B-RESIDUAL | DCF与估值桥 | 首个预测段只计入估值日后的经营现金流 | rule | 主需 | 首段仅含估值日后活动 |
| 06-FORMULA | 公式与模型工程 | 每个要求的结果单元格为活公式而非粘贴数值 | rule | 主需 | 要求Outputs为活公式 |
| 06-RECALC | 公式与模型工程 | LibreOffice 重算后结果与独立真值一致 | rule | 主需 | 重算对比独立真值 |
| 06-PERTURB1 | 公式与模型工程 | 第一组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 隐藏输入扰动传导 |
| 06-PERTURB2 | 公式与模型工程 | 第二组经营及估值/桥接扰动按依赖传导 | rule | 主需 | 第二组扰动传导 |
| 06-LINKS | 公式与模型工程 | 无外部工作簿链接或公式错误值 | rule | 主需 | 禁止外部链接 |
| 06-FREE | 公式与模型工程 | 自由布局通过语义键发现而非行号评分 | rule | 次需 | 中间模型自由按键评分 |
| X-IC-005 | 公式与模型工程 | 仅终值方法不同的估值版本共用同一份显性预测期现金流现值合计。 | rule | 主需 | 双终值共用预测期现值 |
| 09-MEMO | 表达与专业可用性 | 提交 memo.md，说明最重要的价值驱动与至少一个局限 | llm | 次需 | 题面要求提交memo |
| 09-READABLE | 表达与专业可用性 | 中间结构有明确期间与项目标签且不依赖未披露技巧 | agent | 次需 | 可审计性要求标签清晰 |
| X-TA-002 | 表达与专业可用性 | 每项非经常性调整均单独记录调整金额。 | rule | 主需 | 非经常收益需剔除 |
| X-TA-004 | 表达与专业可用性 | 逐期折现期数值显示在可见的折现期行或等效时间表中。 | agent | 次需 | 残期与年中折现需展示 |
| X-TA-006 | 表达与专业可用性 | FCFF 的 EBIT、税项、折旧摊销、资本开支及营运资本变动各自显示为独立可识别的行项。 | agent | 次需 | 题面要求FCFF构建 |
| X-TA-007 | 表达与专业可用性 | 终值公式直接引用模型中可见的终期指标单元格与终值假设单元格。 | agent | 次需 | 双终值公式需引用可见单元格 |
| 03-MARGIN | 经营预测 | 各期 EBIT 使用本期的分部或核心利润率 | rule | 主需 | 程序强制必选项 |

## 附录：契约与外部代理提示词原文

### 契约 CONTRACT.md

````text
# DCF Eval v3：分类重构契约

v2（`exp/dcf_factory_v2/`）保留不动，只作为可复用代码和失败案例参考。v3 在新目录重建流程。

## 1. 题族划分

| 题族 | 构成 | 说明 |
|---|---|---|
| **BC** | B（时间与会计机制）× C（输出与估值结构） | 基础题族，组合抽样，变化最大 |
| **A** | 固定少量 BC 基座 × 行业/商业模式 | 只换行业驱动和口径，BC 结构基本固定 |
| **D** | 独立新生成的 BC 结构题 + 3–4 次连续修改 | 起点不复用 BC 题族的任何题目；每步修改独立核验，最后结果单独核验 |
| **E** | 真实公司冻结历史 + 开放假设 + 自写 Monte Carlo | 沿用 v2 E 思路，**题面改为中文**，共 4 题 |
| **W** | 限定来源联网取数 + 建模 | 单独题族，额外检查取数、交叉验证与填入 |

A 不再与 BC 混在同一题里随机交叉；A 用固定几个 BC 基座，让行业维度成为主要变量。

## 2. B 维度菜单（必须全部可抽到）

- 非自然财年；估值日在财年中间
- 历史频率：年度、半年、季度，**以及半年＋桥接季度的混合历史拼接 LTM**
- 完整财年聚合、LTM，SBC 与非经常项规范化
- 残余期＋完整年度预测（4–6 期）
- 实际天数，年中/期末折现，终值在最后完整财年末
- 营运资本：天数法、余额比例法；**首期 ΔNWC 必须写清用估值日余额还是最近财年末余额**，题面与真值同口径
- 长期资产：D&A 比例、固定资产滚动、**固定资产＋无形资产双资产池**（无形资产独立新增、摊销并在 FCFF 中扣减）
- 终值：Gordon、退出倍数、双终值加权
- 股权桥：现金、投资、债务、租赁、少数股权、库存股期权、RSU
- 税：现金税、NOL

## 3. C 维度菜单（输出与估值结构）

1. 简版 DCF
2. 三表＋DCF
3. **分部经营模型＋SOTP**：分部经营预测 → 分部再投资与 FCFF → 分部折现或倍数 → 加总 → 公司层净债务与稀释股数桥
4. **风险调整管线 DCF**：投产时间 × 规模 × 价格 × 成功概率 → 项目级风险调整 FCFF → 汇总；未投产不得产生收入；建设期支出与投产收入分离；成功概率作用于项目现金流，不调 WACC
5. **情景驱动 Operating Model**：Cases 页切换 Base/Bull/Bear，收入、利润率、再投资、FCFF、终值、每股价值联动；不同于 WACC×g 敏感性
6. **多方法估值与反推**：Gordon 与退出倍数分别估值；由 Gordon 终值反推隐含 EV/EBITDA；由退出倍数反推隐含 g；由市场价反推隐含 WACC 或增长；输出估值区间（Football Field）
7. 债务计划表＋DCF

BC 题每题抽 4–7 个 B 项 + 1 个 C 结构；组合须合法且可解释。

题面写法：抽样结果只用于造题，题面中不得出现“B 项”“C 结构”“BC 基座”或基座代码，应把抽到的时间口径、历史形式、难点和输出结构直接写成自然的业务要求（例如“公司财年截至每年 2 月 28 日，估值日落在财年中间”）。A、D 题同理；D 的步骤事件使用中文事件名。

## 4. A：行业 / 商业模式

按行业或商业模式分大类，再在类内抽样具体驱动；v2 的细场景只作为驱动模板参考。

| 大类 | 典型驱动与口径 |
|---|---|
| 软件与订阅 SaaS | ARR、净留存、获客成本、合同负债、资本化研发 |
| 消费零售与连锁 | 门店开关、同店增长、坪效、租赁 |
| 制造与工业设备 | 量价、产能利用率、维护资本开支、存货天数 |
| 医药与生物科技 | 管线、成功概率、专利悬崖、研发费用 |
| 医疗服务 | 床位/门诊量、支付方结构、人员成本 |
| 银行与金融 | 净息差、贷款增长、资本充足率；股权现金流/超额收益估值，不用 FCFF |
| 保险 | 保费、综合成本率、投资收益 |
| 能源与资源 | 储量、产量递减、商品价格、开发资本开支 |
| 公用事业与基础设施 | 受监管资产基数、允许回报率、长期折旧 |
| 交通与物流 | 运力、载运率、单位收益、机队资本开支 |
| 互联网平台与媒体 | 用户、ARPU、内容摊销、广告与订阅混合 |
| 房地产 | NOI、出租率、资本化率、NAV |
| 专业服务与外包 | 人员数、利用率、人均费率 |
| 设备即服务与装机运维 | 装机基数、服务频次、续约率 |

A 题：固定 3–4 个 BC 基座，每题抽 1 个行业大类 + 类内 2–3 个驱动。金融、保险、房地产等必须使用行业适配估值口径，不能硬套 FCFF。

## 5. D：多步修改

- 起点是一道**独立新生成**的 BC 结构题（新公司、新数据、新 B/C 组合），不复用 BC 题族中的任何题目；随后 3–4 次修改，每次是结构性变化（实际值重定基期、剥离、并购、融资与资本开支重排、口径变化、情景切换、终值方法变化等），不能只改增长率。
- 核验两层：
  1. **最终结果**：最后一版工作簿的数值、勾稽、活公式、扰动传导全部正确，不是硬编码；
  2. **过程**：每步保存快照，逐步检查该步要求的修改是否正确完成，旧历史未被篡改，前一步结果仍可复算。

## 6. E：开放预测与 Monte Carlo

沿用 v2 E 的真实公司冻结历史和独立模拟评分思路，**题面全部改为中文**。

## 7. W：联网取数

- 只允许指定来源（SEC、公司 IR、国债收益率等），禁止自由搜索当前股价答案。
- 额外 rubric：取数值与权威来源一致、来源可追溯（文件/期间/页码或字段）、至少一项交叉验证、取到的数确实被模型引用、取数失败时如实报告。

## 8. Rubric 库

- 统一一个库，合并 v2 的 F/D 共享原子和 E 评分项，去重。
- 每条字段：`id`、`family`（BC 基础 / A / D / E / W）、`category`、`requirement`（具体可判定要求）、`evidence`、`applies_when`、`method`（rule/llm/agent）、`importance`（**主需=3，次需=1**）。
- 取消“严重度”字段。
- 类别内是否全有或全失、类别权重另行配置；默认按主需/次需权重加总。
- BC 条目是所有题的基础；A、D、E、W 各有专属条目。

## 9. 选择流程

题目生成后，调用 LLM API（默认 `claude-opus-5-5`，与造题模型 `kimi-k3.1-pro` 不同家族，避免同一模型既定评分范围又被评分），输入题目 spec 和题面，从库中**逐条挑选具体 rubric ID**（不是挑类目），并说明理由；程序再校验：必选的 BC 基础项不能缺，条目必须适用，ID 必须存在。

## 10. 规模

首版：BC 16、A 8、D 4（每题 4–5 步）、E 4、W 4，共 36 题。
````

### CORE 提示词

````text
你是 DCF Eval v3 的独立造题生成代理，不是答题代理。请在 `/Users/link/Desktop/Finance Bench/exp/dcf_factory_v3` 实际实现并运行生成管线，不要只写方案。

## 先读

1. `CONTRACT.md`：v3 硬性契约（题族、B/C 维度菜单、A 行业分类、D 多步、E 中文、W 联网）。
2. `rubric_library/LIBRARY.md`：统一评分库。你**不负责挑 rubric**；但你生成的真值和输出键必须能支撑库中相关条目被程序检查。
3. 可复用代码（只读，不要改 v2）：`../dcf_factory_v2/core/model.py`、`workbook.py`、`grader.py`、`generate.py`，`../dcf_factory_v2/open/`。v2 已修好的财务口径（残期只缩放经营流量、合同负债只计一次、预测期初现金用 opening_cash、SBC 不进 FCFF、类别权重只计一次）必须沿用。

## 你负责

- `bc/`、`a/`、`d/`：BC 16 题、A 8 题、D 4 题（每题 1 个 BC 基座 + 3–4 次修改，共 4–5 步）。
- `tasks/<ID>/`：每题 `spec.json`、`instruction.md`（**中文**）、`environment/`（公开输入）、`solution/`（活公式参考）、`tests/expected.json`（独立数值真值，至少两组隐藏扰动）、`task.toml`。
- `validate.py` 与 `validation.json`：参考工作簿经 LibreOffice 重算后与真值一致；空白/静态负例被拒绝。

E 与 W 由另一位代理负责，不要生成。

## BC 题要求

- 每题从 B 菜单抽 4–7 项、从 C 菜单抽 1 个结构，写入 `spec.json` 的 `b_items` 与 `c_structure`。
- 16 题必须覆盖：混合历史拼接 LTM、固定资产+无形资产双资产池、首期 ΔNWC 两种口径，以及 C 的全部七种结构（分部 SOTP、风险调整管线、情景驱动 Operating Model、多方法估值与反推各至少 2 题）。
- 分部 SOTP 必须是真正的多分部独立预测与估值，不是在总收入上加一块分部收入。
- 风险调整管线：投产前无收入；建设期支出与投产收入分离；成功概率作用于项目现金流。
- 情景驱动：一个 Cases 开关联动收入、利润率、再投资、FCFF、终值、每股价值。
- 多方法：分别输出 Gordon 与退出倍数价值、隐含 EV/EBITDA、隐含 g、由给定股价反推的隐含 WACC。

## A 题要求

- 固定 3–4 个 BC 基座结构，8 题按 `CONTRACT.md` 第 4 节的行业/商业模式大类抽样，至少覆盖：软件订阅、零售连锁、制造、医药、银行或保险、能源或公用事业、房地产或平台中的 7 类。
- 金融、保险、房地产必须使用行业适配估值（股权现金流/超额收益、NAV 等），不得硬套 FCFF。
- `spec.json` 写 `industry`、`base_structure`、`industry_drivers`。

## D 题要求

- 每题起点是一道**独立新生成**的 BC 结构题：新虚拟公司、新数据、新的 B/C 组合，不得复用 `tasks/BC*` 中任何题目的 spec、数据或题面。之后 3–4 次结构性修改（重定基期、剥离、并购、融资与资本开支重排、口径变化、情景切换、终值方法变化等），不能只改增长率。
- 每步独立 `instruction.md`、事件输入、该步独立真值；要求答题者每步保存快照 `/app/snapshots/step-N.xlsx`。
- 真值分两层：最后一步完整真值；每一步的该步真值。

## 质量与约束

- 题面中文，原创虚拟公司，不复制外部 benchmark 原题或数值。
- 公开输入只给事实、假设和输出键，不给完整公式模板或答案。
- 先端到端做通 2 题再扩量；未通过的题标记原因，不得把失败说成通过，不得擅自缩减题数。
- 不读长日志和图片；不创建 AGENTS.md 或无关文档。模型 API 在 `http://127.0.0.1:4310/v1/messages`，不读写密钥。
- 最终回复简述：生成了哪些题、各覆盖了哪些 B/C/行业项、验证结果与失败原因。
````

### OPEN 提示词

````text
你是 DCF Eval v3 开放预测与联网取数方向的独立造题生成代理，不是答题代理。请在 `/Users/link/Desktop/Finance Bench/exp/dcf_factory_v3` 实际生成题目并运行验证。

## 先读

1. `CONTRACT.md` 第 6、7 节。
2. `rubric_library/LIBRARY.md` 的 E 与 W 部分；你不挑 rubric，但输出 schema 必须让这些条目可被程序检查。
3. 可复用：`../dcf_factory_v2/open/`（e_common.py、grader.py、reference.py、rubric_factory.py），只读，不改 v2。

## E：4 题

- 从 v2 E01–E06 中选 4 家公司（至少保留一个 H1 或 Q3 残余期变体，以及 xlsx 与 json 两种输出形态），基于其截止日和冻结数据重建，**题面全部改为中文**，保留：答题者自写 Monte Carlo（≥5,000 路径、指定 seed）、独立评分器检查分布/相关性/路径算术/分位数、未来实际值和股价只作诊断。
- 输出到 `tasks/E01`–`E04`，每题 `spec.json`（`family: "E"`）、`instruction.md`、`environment/`、`solution/`、`tests/`、`task.toml`。

## W：4 题

- 真实上市公司，要求答题者从**指定来源**（SEC EDGAR、公司 IR、美国国债收益率）取数后建模估值；禁止自由搜索当前股价或现成目标价。
- 每题明确列出必须取的数据项（如某财年收入、经营利润、资本开支、稀释股数、10 年期国债收益率）、期间和允许来源。
- 隐藏真值：这些取数项的权威值（从本地已有 SEC 快照 `../data/` 核实，记录来源与 hash），以及允许容差。
- 要求答题者输出取数表（值、来源 URL/文件、期间、字段）、交叉验证表、模型中引用这些取数单元格。
- 网络通过现有 IPv4 sidecar 白名单限制（参考 `../dcf_factory/ipv4_egress/` 和 v2 的 docker-compose），并在 task.toml 中如实标注；不得声称未经验证的网络限制已生效。
- 输出到 `tasks/W01`–`W04`，`spec.json` 写 `family: "W"`、`required_fields`、`allowed_sources`。

## 约束

题面中文；先做通 E01 与 W01 再扩量；失败如实记录；不读长日志和图片；不创建无关文档；模型 API 在 `http://127.0.0.1:4310/v1/messages`，不读写密钥。最终回复简述生成与验证结果。
````

### DISTILL 提示词

````text
你是 DCF Eval v3 的 rubric 蒸馏代理。任务：把外部 benchmark 的原始评分细则，提炼成**可复用的通用原子 rubric**，补充进 v3 统一库。你不出题、不答题。

## 输入（只读）

- 现有 v3 库：`/Users/link/Desktop/Finance Bench/exp/dcf_factory_v3/rubric_library/library.json`（128 条，已去重）。
- 外部原始 rubric（`/Users/link/Desktop/Finance Bench/research/raw/`）：
  - `btb_dcf_tasks.json`：BankerToolBench 19 道 DCF 题，字段 `aggregated_rubric_json`，约 2,218 条，类别有 Technical Correctness、Instruction Following、Client Readiness & Presentation、Internal Consistency、Transparency & Auditability、Risk & Compliance；
  - `bluefin_ttwo_dcf.json`：BlueFin TTWO 题，字段 `rubric.sections`，39 条；
  - `frontierfinance/dcf_rubric.csv`：73 条，含 gating 条件；
  - `emb/M003-scratch_rubric.jsonl`：50 条（文件很大，逐行读，不要一次读全）。
- 背景：`/Users/link/Desktop/Finance Bench/research/DCF_Benchmark_题目与评分整理.md` 第 1、2 部分和附录 A。

## 做法

1. 用 Python 脚本读取全部原始条目，**不要把原文整段打印进上下文**；按主题聚类（例如三表勾稽、WACC、终值、股权桥、敏感性、格式、引用、硬编码、来源、风险披露等）。
2. 把题目专属断言（如“增长率=4.5%”“Dec-19 的 cohort=47”）**泛化**为通用条目（如“题面给定的增长率输入被原样采用并应用于每个预测年”）。
3. 去重是重点。外部约 2,380 条与现有 128 条、以及外部各 benchmark 之间都有大量重复：
   - 与现有库语义相同或被现有条目覆盖的，**一律不新增**，在报告里记录它被哪个现有 ID 覆盖；
   - 外部条目之间重复的，只保留一条泛化版本，并在 `support` 里累计支持条数；
   - 现有 128 条已覆盖主要建模机制，新增应集中在现有库确实缺的检查点（例如呈现与客户可用性、透明度与可审计性、风险披露、输入原样采用、常见陷阱），不要为凑数把同一检查换说法重复写。
4. 每条新条目必须同时满足：
   - **原子化**：一条只判一个点。出现“且”“以及”“和……都”把两个独立检查连在一起的，必须拆开或删掉；
   - **唯一判定**：给定答案，能无歧义地判 0 或 1。写清阈值、比较对象或判定条件；“合理”“清晰”“专业”这类无法判定的词不能单独作为标准，要改写成可观察的条件，否则删掉。
5. 写完后自查：逐条检查原子化和唯一判定，不合格的修改或删除；在报告中给出被删除和拆分的数量。

## 输出

写入 `/Users/link/Desktop/Finance Bench/exp/dcf_factory_v3/rubric_library/distilled.json`，为 JSON 数组，每条字段：

- `id`：前缀 `X-`，如 `X-TC-001`；
- `family`：`BC`、`A`、`D`、`E`、`W` 之一（大多数应为 BC 通用项）；
- `category`：沿用现有库类别，必要时可新增（如“呈现与客户可用性”“透明度与可审计性”“风险与合规披露”）；
- `requirement`：中文，一条具体可判定的要求；
- `evidence`：去哪里找证据；
- `applies_when`：适用条件；
- `method`：`rule`、`llm` 或 `agent`；能用程序检查的写 `rule`，主观判断写 `llm`，需要工具读工作簿的写 `agent`；
- `importance`：`主需` 或 `次需`；
- `source`：来源 benchmark 名称和代表性原始条目 ID 或类别；
- `support`：原始语料中支持该条目的大致条数。

另写 `distill_report.md`：说明聚类方法、每个来源贡献了多少条、哪些主题因与现有库重复而未新增。

## 约束

目标是补缺，不设下限：新增条数以去重后的真实缺口为准，预计几十条，**宁缺毋滥**。报告中给出：原始条目数、被现有库覆盖而丢弃的数量、外部内部合并的数量、因不原子或不可判定而删除的数量、最终新增数量。不修改 `library.json` 和 v2 目录。不读图片。模型 API 在 `http://127.0.0.1:4310/v1/messages`，不读写密钥。最终回复简述上述数字和新增条目按类别、来源的分布。

## 续跑说明

`_distill_agent/work/` 下已有上一轮的中间结果（raw_entries.json、inventory.json、rule_clusters.json、rule_classified.json、semantic/）。先检查它们是否完整可用，可用就直接复用，不要重新全量抽取；不可用再重做。
````
