# Adobe Inc.（ADBE）限定来源五年 DCF 备忘录

## 结论与基准口径

信息截止日为 **2025-02-14**，历史建模基期为 **FY2024（2023-12-02至2024-11-29）**。本模型只在 `Sources` 页保存一次取数值，其他页通过活公式引用；金额单位为百万美元，股数单位为百万股。

在 `initial_growth=10%`、`wacc=8.47%`、`terminal_growth=3%` 的开放基准情景下：

- `enterprise_value`：**138,629.09 百万美元**；
- `equity_value`：**140,887.09 百万美元**；
- `value_per_share`：**313.29 美元/股**。

上述每股价值使用 FY2024 加权平均稀释股数 449.7 百万股，严格遵循题定口径。它不是市场价格，也不是对市场价格高低的判断。本次没有查询或使用股价、现成目标价或市场一致预期。

## 实际取数日期与来源

实际取数日均为 **2026-11-23**（UTC；`observed_at` 不是申报日）：

1. SEC companyfacts：`https://data.sec.gov/api/xbrl/companyfacts/CIK0000796343.json`，取回时间 02:10:37Z，本地原始留档 `adobe_companyfacts.json`。只选择 `form=10-K/10-K/A`、`filed<=2025-02-14` 且期间、单位严格匹配的事实。
2. 同一 SEC 原始 10-K：`https://www.sec.gov/Archives/edgar/data/796343/000079634325000004/adbe-20241129.htm`，用于核对同一 accession 的内联 XBRL 数值。15 项 SEC 事实均匹配，未发现数值冲突。该文件与 companyfacts 的同一申报事实不构成两个独立会计事实。
3. 美国财政部指定日度 CSV：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2025/all?type=daily_treasury_yield_curve&field_tdr_date_value=2025&page=&_format=csv`，取回时间 02:10:59Z，本地原始留档 `treasury_2025_daily_rates.csv`。仅选 2025-02-14 的 `10 Yr=4.47`，换算为 `treasury_10y=0.0447`，无需回退日期。

所有 15 项 SEC 会计事实均来自 **10-K、filed=2025-01-13、accession=0000796343-25-000004**。虽然 companyfacts 和全年财政部 CSV 在实际取回时含有其他日期记录，筛选与建模没有采用截止日后才公开的会计事实，也没有采用目标日之后的收益率观测。财政部的 `filed` 与 `accession` 不适用，故记录为 `null`，其观测期间为 2025-02-14，字段映射为 `DGS10` 对应官方 CSV 的 `10 Yr`。

## 取数结果与标签回退

| field_id | 取数值 | 单位 | 实际字段 |
|---|---:|---|---|
| `revenue` | 21,505 | USD_millions | `Revenues` |
| `operating_income` | 6,741 | USD_millions | `OperatingIncomeLoss` |
| `pretax_income` | 6,931 | USD_millions | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` |
| `income_tax` | 1,371 | USD_millions | `IncomeTaxExpenseBenefit` |
| `net_income_consolidated` | 5,560 | USD_millions | `NetIncomeLoss` |
| `da` | 857 | USD_millions | `DepreciationDepletionAndAmortization` |
| `capex` | 183 | USD_millions | `PaymentsToAcquirePropertyPlantAndEquipment` |
| `diluted_shares` | 449.7 | shares_millions | `WeightedAverageNumberOfDilutedSharesOutstanding` |
| `cash` | 7,613 | USD_millions | `CashAndCashEquivalentsAtCarryingValue` |
| `short_term_investments` | 273 | USD_millions | `ShortTermInvestments` |
| `receivables` | 2,072 | USD_millions | `AccountsReceivableNetCurrent` |
| `current_assets` | 11,232 | USD_millions | `AssetsCurrent` |
| `current_liabilities` | 10,521 | USD_millions | `LiabilitiesCurrent` |
| `current_debt` | 1,499 | USD_millions | `DebtCurrent` |
| `noncurrent_debt` | 4,129 | USD_millions | `LongTermDebt` |
| `treasury_10y` | 0.0447 | decimal | `DGS10`（CSV 列 `10 Yr`） |

标签严格按题定顺序回退，而不是先选数值再补标签：

- `RevenueFromContractWithCustomerExcludingAssessedTax` 在 companyfacts 的 `us-gaap` 命名空间不存在，故采用 `Revenues`。
- `ProfitLoss` 同样不存在，故采用 `NetIncomeLoss`。原始 10-K 未披露非控股权益，该合并净利润与归母展示金额一致；没有混用不同期间的归母值，也没有虚构 `ProfitLoss`。
- `LongTermDebtCurrent` 与 `LongTermDebtNoncurrent` 存在标签，但没有同时符合本期、单位和 filed 条件的 10-K 事实，故分别采用 `DebtCurrent=1,499` 与 `LongTermDebt=4,129`。
- 折旧摊销采用允许标签对应的 857，不以附注中仅针对固定资产的折旧金额替代；资本开支保持现金流出正数 183。

**没有取数失败项，没有缺失补零，没有未解决的数值冲突。** `sources.json` 的 `failures` 与 `conflicts` 均为空；各字段保留了原始值、换算后值、URL、期间、标签、form、filed、accession、实际取数日及回退说明。

## 开放预测假设与理由

本模型是一个透明、可修改的基准情景，不声称预测来自公司指引或市场预期。七个题定假设均位于 `Assumptions` A/B 列：

- `initial_growth=10%`：FY1 采用温和减速的收入增长情景；FY2–FY5 每年增速分别线性收敛为 8.25%、6.50%、4.75%、3.00%。10% 是开放输入，不是由历史结果倒推的“正确答案”。
- `steady_ebit_margin=6741/21505=31.3462%`：以 FY2024 实际经营利润率保持不变，隔离利润率变化对估值的额外影响。
- `tax_rate=1371/6931=19.7807%`：以 FY2024 实际有效税率作为预测税率，保持口径一致。
- `da_to_revenue=857/21505=3.9847%`、`capex_to_revenue=183/21505=0.8510%`：以 FY2024 实际比率预测，避免另行引入未披露的资产开支计划。
- `wacc=0.0447+0.04=0.0847`：以指定财政部 10 年期收益率加 4 个百分点估值利差。该利差是开放的折现率情景输入，并非从禁止来源取得的股权风险溢价或市场共识。
- `terminal_growth=3%`：开放永续名义增长情景，且严格低于 WACC。

经营 NWC 为 `11,232−7,613−273−(10,521−1,499)=−5,676` 百万美元。保留该负值及由此产生的负 ΔNWC，不人为改成零或正数。应收账款已经包含在流动资产内，只在 `Forecast!B20` 做扣减核对，不再重复加入 NWC 或股权桥。

`reinvestment_component` 定义为 **D&A−CapEx−ΔNWC**，因此 `fcff=NOPAT+reinvestment_component`，展开即 `EBIT×(1−tax_rate)+D&A−CapEx−ΔNWC`。显性期按 1–5 年折现；终值为 `FY5 FCFF×(1+g)/(WACC−g)` 并用 FY5 折现因子再折现五年。股权桥中的净现金为 `7,613+273−1,499−4,129=2,258` 百万美元，现金和短期投资各加一次，当期与非当期债务各减一次。

## 交叉验证与差异

`pretax_to_net_income` 的真实计算为：

`6,931−1,371−5,560=0.00` 百万美元。

容差为 `max(0.01,abs(5,560)×2%)=111.20` 百万美元，差额在容差内并通过检查。该零差额是取数计算结果，不是强行修改得到。`cross_validation.json` 引用了 `sources.json` 中三个字段的零基索引、JSON 路径、数值与英文标签；`Forecast!B21` 和 `Assumptions!B13:B15` 也通过活公式重复核对。

FY2024 经营 NWC 检查保留 −5,676 百万美元；流动资产扣除应收账款为 `11,232−2,072=9,160` 百万美元。未发现失败检查或口径冲突。

## 重算与扰动验证

最终交付的 `model.xlsx` 已通过 LibreOffice 无界面模式真实重算并保存，随后以 `data_only=True` 读取缓存值：五页结构正确、所有公式缓存均存在、全簿没有公式错误。独立 Python 算式复算的五年 FCFF、显性期现值 31,445.58、终值 160,944.51、终值现值 107,183.51、企业价值、股权价值及每股价值均与工作簿一致。16 个取数字段在 `retrieval_map.json` 中均有真实的下游活公式引用。

以下扰动均在独立临时副本中完成，基准交付文件未被改写：

| 情景 | WACC | 永续 g | 每股价值（美元） |
|---|---:|---:|---:|
| 基准 | 8.47% | 3.00% | 313.29 |
| WACC 上升100基点 | 9.47% | 3.00% | 265.57 |
| WACC 下降100基点 | 7.47% | 3.00% | 382.36 |
| 永续增速上升100基点 | 8.47% | 4.00% | 380.00 |
| 永续增速下降100基点 | 8.47% | 2.00% | 267.19 |

方向均符合 DCF 数学关系。另以 WACC=2%、g=3% 测试防错条件，终值及估值输出返回 `#N/A`，符合 WACC 必须大于 g 的要求。

## 网络探测边界

题面及公开合同声明存在 IPv4 sidecar 白名单配置，但 **“配置存在”不等于“白名单已经验证生效”**。本次运行时仅以 IPv4 探测题面允许的 SEC companyfacts 与财政部指定 CSV，二者均返回 HTTP 200；随后同一 SEC Archives 原始 10-K 也成功取回。

这些结果只证明上述允许地址在探测时可访问，不能单独证明 sidecar 白名单已生效，也不能证明非允许域名会被拦截。为遵守“仅允许上述域名”的限制，本次没有对非白名单域名做反证探测，也未审计配置文件本身；因此 memo 不作白名单生效声明。
