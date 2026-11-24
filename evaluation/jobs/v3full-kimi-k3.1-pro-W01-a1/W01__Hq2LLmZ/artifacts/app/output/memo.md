# Apple Inc.（AAPL）FY2024 限定来源五年 DCF 备忘录

## 一、范围、实际取数日与来源

- 信息截止日：**2024-11-27**；建模基期：**FY2024**，期间为 **2023-10-01 至 2024-09-28**。
- 实际取数日：**2026-11-22（UTC）**，记录于 `sources.json` 各项的 `observed_at`。该日期是本次原始响应的实际取得日，不是申报日，也不改变信息截止日。
- SEC companyfacts：`https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json`。实际 GET 返回 HTTP 200；本地原始文件为 `/app/data/source_cache/sec_companyfacts_2026-11-22.json`。
- 美国财政部 2024 年日度收益率 CSV：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page=&_format=csv`。实际 GET 返回 HTTP 200；本地原始文件为 `/app/data/source_cache/ust_daily_2024_2026-11-22.csv`。
- 15 个会计字段均取自同一份 FY2024 10-K：form=`10-K`、filed=`2024-11-01`、accession=`0000320193-24-000123`。逐项核对精确期间、原始单位、标签优先级和 filed；没有采用截止日后重述值。
- 未另行访问公司 IR，因为指定 companyfacts 已取得全部必需会计字段。同一 XBRL 事实与 IR 转载本来也不构成两个独立会计事实。
- 未查询或使用当前或历史股价、现成目标价、市场一致预期，也未使用第三方财经网站或搜索摘要。本备忘录不以股价判断 DCF 是否合理。

## 二、历史取数结果与口径

金额单位为百万美元；稀释股数单位为百万股；收益率为小数。`sources.json` 保留了原始值、原始单位、完整 XBRL 标签、期间、form、filed、accession、来源 URL 和本地文件名。

| field_id | 提交值 | 实际采用 field |
|---|---:|---|
| `revenue` | 391,035 | `RevenueFromContractWithCustomerExcludingAssessedTax` |
| `operating_income` | 123,216 | `OperatingIncomeLoss` |
| `pretax_income` | 123,485 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` |
| `income_tax` | 29,749 | `IncomeTaxExpenseBenefit` |
| `net_income_consolidated` | 93,736 | `NetIncomeLoss` |
| `da` | 11,445 | `DepreciationDepletionAndAmortization` |
| `capex` | 9,447 | `PaymentsToAcquirePropertyPlantAndEquipment` |
| `diluted_shares` | 15,408.095 | `WeightedAverageNumberOfDilutedSharesOutstanding` |
| `cash` | 29,943 | `CashAndCashEquivalentsAtCarryingValue` |
| `short_term_investments` | 35,228 | `MarketableSecuritiesCurrent` |
| `receivables` | 33,410 | `AccountsReceivableNetCurrent` |
| `current_assets` | 152,987 | `AssetsCurrent` |
| `current_liabilities` | 176,392 | `LiabilitiesCurrent` |
| `current_debt` | 10,912 | `LongTermDebtCurrent` |
| `noncurrent_debt` | 85,750 | `LongTermDebtNoncurrent` |
| `treasury_10y` | 0.0425 | `DGS10`，对应官方 CSV 的 `10 Yr` |

具体选择和冲突说明：

1. `net_income_consolidated`：companyfacts 中不存在 `ProfitLoss` 节点，依允许标签顺序回退至 `NetIncomeLoss`，没有以其他期间或其他标签补造“含非控股权益”事实。
2. `short_term_investments`：`ShortTermInvestments` 无节点，依序采用 `MarketableSecuritiesCurrent`。
3. `da`：采用优先级更高的 `DepreciationDepletionAndAmortization`=11,445，未改取同时存在但优先级较低的 `Depreciation`=8,200。这是不同标签的口径选择，不是同一标签的数值冲突。
4. `capex`：原始现金支出 9,447,000,000 美元已为正数，换算后保持 9,447 百万美元，不另改符号。
5. `noncurrent_debt`：采用 `LongTermDebtNoncurrent`=85,750，未采用含当期部分的 `LongTermDebt`=96,662，从而避免在股权桥中重复扣减当期债务。
6. 截止日前、同标签、同期间的合规事实之间未发现数值冲突；逐项候选数量和原始值见 `sources.json`。
7. 财政部在 **2024-11-27** 有非空 `10 Yr`=4.25%，因此无需使用此前日期；模型写为 **0.0425**。工作簿以百分比格式显示为 4.2500%，底层数值仍为 0.0425。

## 三、开放预测假设与理由

所有假设位于 `Assumptions` A/B 列，黄色单元格为可直接修改的开放输入，蓝色单元格为历史推导或联动公式。它们不是市场一致预期。

| 假设 | 基准值 | 理由与处理 |
|---|---:|---|
| `initial_growth` | 4.0000% | 开放情景，不声称来自外部预测；FY1 直接使用。 |
| `steady_ebit_margin` | 31.5102% | 公式为 FY2024 EBIT/收入，预测期保持不变。 |
| `tax_rate` | 24.0912% | 公式为 FY2024 所得税/税前利润，预测期保持不变。 |
| `da_to_revenue` | 2.9268% | 公式为 FY2024 D&A/收入，每年 D&A 随收入变化。 |
| `capex_to_revenue` | 2.4159% | 公式为 FY2024 CapEx/收入，每年 CapEx 随收入变化。 |
| `wacc` | 8.2500% | `treasury_10y + wacc_risk_premium`，即 4.25%+4.00%。4 个百分点利差是开放折现情景，不是历史事实。 |
| `terminal_growth` | 2.5000% | 开放永续增长情景，低于 WACC；FY2–FY5 的收入增长率向该值线性收敛。 |
| 显性期 | 5 年 | 折现年序固定为 1、2、3、4、5。 |

五年收入增长依次为 **4.0000%、3.6250%、3.2500%、2.8750%、2.5000%**。预测 EBIT、D&A 和 CapEx 分别按收入乘相应假设；有效税率保持不变。

FY0 经营 NWC 依题定公式计算为：

`152,987−29,943−35,228−(176,392−10,912) = −77,664` 百万美元。

预测 NWC 按收入相对 FY0 的比例延伸。FY1 ΔNWC 使用 `FY0 NWC×(FY1收入/FY0收入−1)`，其后为本年 NWC 减上年 NWC。由于基期 NWC 为负，预测 ΔNWC 也为负，FCFF 中减去该负值会提高 FCFF；这是题定口径的结果，未自行改成零或替换口径。

`reinvestment_component=CapEx−D&A+ΔNWC`，且：

`FCFF=EBIT×(1−tax_rate)+D&A−CapEx−ΔNWC=NOPAT−reinvestment_component`。

## 四、估值结果与股权桥

下表是上述开放假设下的模型结果，不是目标价或市场预测。金额除每股价值外均为百万美元。

| 项目 | 数值 |
|---|---:|
| FY1–FY5 FCFF | 102,457.56；105,880.40；109,018.63；111,839.04；114,310.95 |
| 显性期 FCFF 现值 | 429,302.03 |
| Gordon 终值（FY5 时点） | 2,037,716.93 |
| 终值现值（再折现五年） | 1,370,895.43 |
| `enterprise_value` | **1,800,197.46** |
| 加：现金及现金等价物 | 29,943.00 |
| 加：短期投资 | 35,228.00 |
| 减：当期债务 | 10,912.00 |
| 减：非当期债务 | 85,750.00 |
| `equity_value` | **1,768,706.46** |
| 除以：加权平均稀释股数（百万股） | 15,408.095 |
| `value_per_share`（美元/股） | **114.79** |

终值为 `FY5 FCFF×(1+g)/(WACC−g)`，并使用 FY5 折现因子再折现五年。现金、短期投资各加一次，当期、非当期债务各减一次。终值现值约占企业价值 **76.15%**，因此估值对 WACC 和 g 敏感。

## 五、交叉勾稽与失败/冲突披露

`cross_validation.json` 的 `pretax_to_net_income` 直接引用来源表中的三个字段：

`pretax_income−income_tax−net_income_consolidated = 123,485−29,749−93,736 = 0`。

容差为 `max(0.01,abs(93,736)×0.02)=1,874.72` 百万美元，故检查通过。差异没有被人为改成零；工作簿 `DCF!B19:B21` 也以活公式独立计算差异、容差和状态。

- **必需字段失败：无。** 16 个必需字段全部成功，未静默补零。
- **补充请求失败：** SEC 原始 10-K HTML `https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm` 的补充 GET 返回 **HTTP 403**。该事件已记录在 `sources.json` 的 `supplemental_fetch_events`。没有据此填数，也没有转向未允许来源；全部必需字段已由成功的 companyfacts 和财政部响应取得，因此它不是某个必需字段的取数失败。
- **冲突：** 合规同标签事实之间未发现数值冲突；标签回退和不同标签的选择已在第二节披露。
- **其他告警：** LibreOffice 命令行出现 `javaldx`/`Unknown IO error` 文本告警，但确实生成了重算文件；后续缓存值、独立数值复算和扰动测试均通过，未把该文本告警当作重算成功本身。

## 六、LibreOffice 重算与扰动验收

最终 `model.xlsx` 经 **LibreOffice 7.4.7.2** 无界面模式重算并另存，随后以 `data_only=True` 检查缓存值。共检查 **133 个公式**，未发现空缓存或 Excel 错误。`Sources` A/B/C 严格为 field_id、取数值和单位；16 项均有 `Forecast`、`Assumptions` 或 `DCF` 中的直接活公式引用，映射见 `retrieval_map.json`。

独立 Python 算式重新计算了五年收入、NWC、ΔNWC、FCFF、折现、终值、股权桥和每股价值，与 LibreOffice 缓存结果一致。四组扰动均在临时副本上执行，并保持 WACC>g：

| 情景 | WACC | g | 每股价值（美元） | 验收结果 |
|---|---:|---:|---:|---|
| 基准 | 8.25% | 2.50% | 114.7907 | 基准 |
| WACC 上升 1 个百分点 | 9.25% | 2.50% | 97.4738 | 折现因子和估值下降，通过 |
| WACC 下降 1 个百分点 | 7.25% | 2.50% | 139.3990 | 折现因子和估值上升，通过 |
| g 上升 0.5 个百分点 | 8.25% | 3.00% | 125.4853 | 终值和估值上升，通过 |
| g 下降 0.5 个百分点 | 8.25% | 2.00% | 105.8059 | 终值和估值下降，通过 |

最终交付的 `model.xlsx` 是恢复基准假设后重算的版本；扰动副本保存在 `/app/data/sensitivity/`，没有混入 `/app/output/`。

## 七、网络白名单声明

题面声明配置存在于 `environment/docker-compose.yaml` 和 `task.toml`。**配置存在不等于白名单已经验证生效。**

本次运行时仅对指定 SEC 与财政部 URL 进行了 IPv4 的 HEAD 探测及实际 GET；两者 GET 均返回 HTTP 200。这只能证明两个允许来源在本次运行网络中可访问，**不能证明 sidecar 白名单整体已生效，也不能证明非白名单域名会被拒绝**。未做非白名单拒绝控制测试，因此白名单生效状态应记为“未验证”，而不是“已生效”。
