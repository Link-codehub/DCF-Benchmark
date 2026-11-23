# Starbucks Corporation（SBUX）：限定来源取数与五年 DCF

信息截止日为 **2024-11-27**，建模基准财年为 **FY2024**。必须先从指定来源取数再建模，不得先猜结果后补来源。所有题面、取数记录、模型标签和 memo 均用中文；语义 ID 与 XBRL 标签保留英文。

## 允许来源与禁止事项

1. SEC EDGAR companyfacts：`https://data.sec.gov/api/xbrl/companyfacts/CIK0000829224.json`；也可使用 SEC Archives 中截止日前已申报的原始 10-K/10-K/A。
2. 公司 IR：`https://investor.starbucks.com/`，仅可核对同一期间的原始申报；同一 XBRL 事实与 IR 转载不构成两个独立会计事实。
3. 美国财政部日度收益率：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page=&_format=csv`，取 **2024-11-27** 的 10 Yr，如该日官方无值则用之前最近观测并写明实际日期。4.25% 在模型中写 0.0425。

仅允许上述 SEC、公司 IR（含申报文件必要的 CDN）和财政部域名。禁止自由搜索当前或历史股价、现成目标价、市场一致预期及截止日后信息；禁止用搜索摘要或第三方财经网站代替原始来源。历史权威真值按 filed≤截止日的 10-K 事实评定，不能取后来重述的同一期间值。

## 必须取回的数据

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

## 提交与公式要求

- `sources.json`：`items` 数组逐项覆盖上表，含 `field_id/value/unit/period_start/period_end/source_id/source_url/source_file/field/form/filed/accession/observed_at/status/error`。成功项必须含实际数值、允许域名 URL、正确期间与字段、申报号和 filed；`observed_at` 是实际取数日，不是申报日。
- `cross_validation.json`：`checks` 数组至少包含 `pretax_to_net_income`，计算 `pretax_income−income_tax−net_income_consolidated` 的 `difference`，引用来源表中三个字段。允许 `abs(difference)<=max(0.01, abs(net_income_consolidated)*0.02)`，超出或缺失必须在 memo 披露，不能强行改成零。
- `retrieval_map.json`：`items` 数组逐项含 `field_id/source_item_index/sheet/cell/used_by`。工作簿 `Sources` 页 A/B/C 列必须是 field_id、取数值、单位，且每个取数字段在 Forecast/Assumptions/DCF 中有活公式实际引用；不能把取数表摆在一旁、在别处另填历史值。
- `model.xlsx`：`Sources`、`Assumptions`、`Forecast`、`DCF`、`Outputs` 五页。Assumptions A/B 列放经营假设；Forecast A 列放语义键、C:G 为 FY1–FY5，含 revenue、ebit、da、capex、delta_nwc、reinvestment_component、fcff、discount_factor；DCF 计算显性期现值、Gordon 终值及股权桥；Outputs A/C 列输出 `enterprise_value/equity_value/value_per_share`。预测、再投资、折现和输出必须是活公式，并能通过 LibreOffice 重算与 WACC/g 扰动。
- `memo.md`：用中文说明实际取数日期、来源、开放预测理由、交叉验证差异及所有失败/冲突；披露“配置存在”不等于“白名单已经验证生效”。不需要也不得寻找股价来判断 DCF 是否合理。

## 模型口径

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
