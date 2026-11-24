# Apple Inc.（AAPL）DCF 建模备忘录

## 取数记录

- **取数日期**：2026-11-22（模拟运行日）
- **信息截止日**：2024-11-27
- **建模基准财年**：FY2024（2023-10-01 至 2024-09-28）
- **10-K 申报号**：0000320193-24-000123
- **10-K 申报日（filed）**：2024-11-01（在截止日前，合规）

### 来源

| 来源 ID | URL | 说明 |
|---|---|---|
| SEC_COMPANYFACTS | `https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json` | SEC EDGAR XBRL companyfacts API，CIK 320193 |
| UST_DAILY | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all` | 美国财政部日度收益率曲线 |

### 取数结果

所有 16 个 SEC 字段和 1 个财政部字段均成功取回，无失败项。

| field_id | 值 | 单位 | 使用的 XBRL 标签 |
|---|---|---|---|
| revenue | 391,035 | USD_millions | RevenueFromContractWithCustomerExcludingAssessedTax |
| operating_income | 123,216 | USD_millions | OperatingIncomeLoss |
| pretax_income | 123,485 | USD_millions | IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest |
| income_tax | 29,749 | USD_millions | IncomeTaxExpenseBenefit |
| net_income_consolidated | 93,736 | USD_millions | NetIncomeLoss |
| da | 11,445 | USD_millions | DepreciationDepletionAndAmortization |
| capex | 9,447 | USD_millions | PaymentsToAcquirePropertyPlantAndEquipment |
| diluted_shares | 15,408.095 | shares_millions | WeightedAverageNumberOfDilutedSharesOutstanding |
| cash | 29,943 | USD_millions | CashAndCashEquivalentsAtCarryingValue |
| short_term_investments | 35,228 | USD_millions | MarketableSecuritiesCurrent |
| receivables | 33,410 | USD_millions | AccountsReceivableNetCurrent |
| current_assets | 152,987 | USD_millions | AssetsCurrent |
| current_liabilities | 176,392 | USD_millions | LiabilitiesCurrent |
| current_debt | 10,912 | USD_millions | LongTermDebtCurrent |
| noncurrent_debt | 85,750 | USD_millions | LongTermDebtNoncurrent |
| treasury_10y | 0.0425（4.25%） | decimal | DGS10，观测日 2024-11-27 |

### 标签选择说明

- **revenue**：优先使用 `RevenueFromContractWithCustomerExcludingAssessedTax`，在 SEC companyfacts 中有合规 10-K 期间事实。`Revenues` 标签虽有数据但不是 FY2024 的 10-K（是更早期间的旧标签）。
- **da**：优先使用 `DepreciationDepletionAndAmortization`（11,445M），注意 `Depreciation`（8,200M）仅为折旧部分，不含摊销，不符合"折旧与摊销"需求，已按标签顺序优先取前者。
- **short_term_investments**：`ShortTermInvestments` 在 SEC companyfacts 中不存在，使用 `MarketableSecuritiesCurrent`。
- **receivables**：使用 `AccountsReceivableNetCurrent`，`ReceivablesNetCurrent` 不存在。
- **current_debt**：使用 `LongTermDebtCurrent`，`DebtCurrent` 和 `ShortTermBorrowings` 均不存在。
- **noncurrent_debt**：使用 `LongTermDebtNoncurrent`（85,750M），`LongTermDebt`（96,662M）包含当期部分，会导致与 current_debt 重复口径。按标签顺序优先取 `LongTermDebtNoncurrent`。
- **net_income_consolidated**：`ProfitLoss` 不存在，使用 `NetIncomeLoss`（93,736M）。Apple 无非控股权益，此值等同于归母净利润。

### treasury_10y 取数

2024-11-27 的美国财政部 CSV 中，`DGS10`（10 Yr）列值为 4.25，换算为小数 0.0425。该日有官方观测值，无需使用之前日期。此值记录在 sources.json 中，但不作为 WACC 的直接输入；WACC 是 Assumptions 页中的独立假设，treasury_10y 作为市场参考利率提供。

## 交叉验证

### pretax_to_net_income 验证

- pretax_income − income_tax − net_income_consolidated = 123,485 − 29,749 − 93,736 = 0
- 容差：max(0.01, 93,736 × 0.02) = 1,874.72
- 差异 = 0，在容差范围内，验证通过。

## 预测假设与理由

本模型使用以下开放假设（Assumptions 页 A/B 列透明展示）：

| 假设 | 值 | 理由 |
|---|---|---|
| initial_growth | 5.0% | 基于 FY2024 收入增速约 2%，考虑到 Apple 服务收入增长和 AI 产品周期潜力，设定略高于近期增速的初始增长率 |
| terminal_growth | 2.5% | 与长期名义 GDP 增长率一致，反映成熟科技企业的稳态增长水平。远低于 WACC（9%）满足 WACC > g 约束 |
| steady_ebit_margin | ~31.51%（公式引用 Sources） | 保持 FY2024 实际经营利润率水平，反映成熟的成本结构和定价能力 |
| tax_rate | ~24.09%（公式引用 Sources） | FY2024 实际有效税率 |
| da_to_revenue | ~2.93%（公式引用 Sources） | FY2024 实际比率，反映资本密集度 |
| capex_to_revenue | ~2.42%（公式引用 Sources） | FY2024 实际比率 |
| wacc | 9.0% | 基于 CAPM 假设：无风险利率约 4.25%（匹配 treasury_10y），股权风险溢价约 5%，Beta 约 1.0，加上债务成本调整。为透明开放假设，可通过 Assumptions 页直接修改 |
| forecast_years | 5 | 标准显性预测期 |
| 增长收敛 | FY1 用 initial_growth，FY2–FY5 线性收敛至 terminal_growth | 避免悬崖效应 |

## 经营 NWC 说明

FY0 NWC = 152,987 − 29,943 − 35,228 − (176,392 − 10,912) = −77,664（百万美元），为负数。这反映了 Apple 的轻资产运营模式：应付账款等经营性负债远大于经营性流动资产（扣除现金和短期投资后）。负 NWC 是 Apple 商业模式的特征，在 DCF 中正确反映为 FCFF 的增加项（ΔNWC 为负时增加 FCFF）。

## 模型结果

| 指标 | 值 |
|---|---|
| 显性期 FCFF 现值合计 | 430,460 百万美元 |
| Gordon 终值 | 1,846,454 百万美元 |
| 终值现值 | 1,200,068 百万美元 |
| **企业价值** | **1,630,528 百万美元** |
| 加：现金及现金等价物 | 29,943 百万美元 |
| 加：短期投资 | 35,228 百万美元 |
| 减：当期债务 | (10,912) 百万美元 |
| 减：非当期债务 | (85,750) 百万美元 |
| **股权价值** | **1,599,037 百万美元** |
| 稀释股数 | 15,408.095 百万股 |
| **每股价值** | **$103.78** |

## 模型稳健性（WACC/g 扰动）

经 LibreOffice 重新计算验证：

- WACC 从 9% 提高到 10%：每股价值从 $103.78 降至 $89.66
- 终值增长率从 2.5% 提高到 3.0%：每股价值从 $103.78 升至 $112.21
- 初始增长率从 5% 提高到 6%：每股价值从 $103.78 升至 $106.29

所有活公式均对扰动产生合理方向性响应，确认模型无硬编码值。

## 网络白名单说明

网络配置（IPv4 sidecar 白名单）已写入 `environment/docker-compose.yaml` 和 `task.toml`。"配置存在"不等于"白名单已经验证生效"。在本次运行中，`FetchURL` 工具对 `data.sec.gov` 和 `home.treasury.gov` 均返回网络错误，但通过 `curl` 命令行（Bash 工具）成功从两个域名获取了数据，表明纯 HTTP 层的连接可用。FetchURL 工具可能因 User-Agent 或 JavaScript 渲染要求等原因失败，最终通过 curl 完成取数。本备忘录如实记录这一情况。

## 失败与冲突

无取数失败项。所有 17 个字段均成功从允许来源取回合规数据。无来源冲突（所有 SEC 字段来自同一份 10-K，不存在同一期间的多份申报）。pretax_to_net_income 交叉验证差异为 0，无超出容差问题。

## 禁止事项合规确认

- 未搜索当前或历史股价
- 未使用现成目标价或市场一致预期
- 未使用截止日（2024-11-27）后的信息
- 未使用禁止的第三方财经网站
- 未编造或静默补零任何缺失数据
- DCF 结果仅基于允许来源数据与透明假设，不依赖股价来"校验"合理性