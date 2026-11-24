# Starbucks Corporation (SBUX) 五期 DCF — 建模备忘录

## 实际取数日期

- 取数执行日：**2026-11-23**
- 信息截止日：**2024-11-27**
- 建模基准财年：**FY2024**（2023-10-02 至 2024-09-29）

## 数据来源

### 1. SEC EDGAR XBRL Company Facts

- URL：`https://data.sec.gov/api/xbrl/companyfacts/CIK0000829224.json`
- 提取方式：通过 HTTP GET，带 User-Agent 标头（SEC 服务器需要）
- 网络可达性：curl 测试返回 HTTP 200
- 使用事实：仅取 filed ≤ 2024-11-27 的 10-K 事实
- 实际申报文件：accession `0000829224-24-000057`，filed `2024-11-20`，form `10-K`
- 共提取 16 项 SEC 字段，全部成功

### 2. 美国财政部日度收益率

- URL：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page=&_format=csv`
- 网络可达性：curl 测试返回 HTTP 200
- 2024-11-27 的 **10 Yr** 字段确认为 **4.25**（百分数），换算为 0.0425
- 该日官方有当日观测值，无需回退

### 3. 公司 IR

- 未单独使用。SEC XBRL 已覆盖全部所需会计事实，IR 仅作为备选第二来源。

## 开放预测假设说明

| 假设 | 取值 | 理由 |
|------|------|------|
| initial_growth | 3.0% | 参考 FY2024 收入 YoY 增速约 0.6%；FY2023→FY2024 为 +0.56%，取略高于近期的温和恢复增速 |
| terminal_growth | 2.5% | 接近名义 GDP 长期增速预期，略低于 WACC 的 8.5% |
| wacc | 8.5% | 高于当前 10 年国债 4.25%，包含权益风险溢价；WACC(8.5%) > terminal_growth(2.5%) 满足模型要求 |
| steady_ebit_margin | 14.95%（FY2024 实际值） | FY2024 经营利润率作为稳态假设；FY2023 为 16.3%，取保守的近期低点 |
| da_to_revenue | 4.40%（FY2024 实际值） | 折旧与摊销占收入比 |
| capex_to_revenue | 7.68%（FY2024 实际值） | 资本开支占收入比；FY2024 资本开支较 FY2023 有显著增长 |
| tax_rate | 24.29%（FY2024 有效税率） | income_tax / pretax_income = 1207.3 / 4969.6 |

以上假设均为透明开放参数，可在 `model.xlsx` 的 `Assumptions` 页直接修改。修改后通过 LibreOffice 重算即可获得更新后的估值。

## 交叉验证

- **pretax_to_net_income 勾稽**：4969.6 − 1207.3 − 3762.3 = **0.00**
- 容忍上限：max(0.01, abs(3762.3) × 0.02) = 75.25
- 差异 0.00 远在容忍范围内，**通过**。
- 三项均来自同一份 10-K (filed 2024-11-20, accn 0000829224-24-000057)，不存在来源不一致问题。

## 失败与冲突披露

### cash 字段

- **首选标签 `CashAndCashEquivalentsAtCarryingValue`** 在 us-gaap 中无 FY2024 10-K 事实（end=2024-09-29, filed≤2024-11-27 条件下无匹配项）。
- 按标签顺序使用其次的 **`CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`**，值 = 3,286.2 百万美元。
- **影响**：该值包含受限现金，可能导致现金及现金等价物被高估。但此值为 FY2024 10-K 披露的合并资产负债表现金行，具有可追溯性。股权价值由此可能略高（受限现金不可用于偿债或分配）。

### 其他字段

- 全部 15 项 SEC 字段成功从 FY2024 10-K 提取，无缺失、无冲突、无静默补零。

## 网络执行状态

"配置存在"不等于"白名单已经验证生效"。`retrieval_contract.json` 声明了 IPv4 sidecar allowlist 配置已写入 environment/docker-compose.yaml 和 task.toml，但以下为实际运行时观测：

- SEC EDGAR（data.sec.gov）：**curl 直接可达**（HTTP 200），但 FetchURL 工具因 CORS / 渲染限制失败；使用 curl 作为后备成功
- 美国财政部（home.treasury.gov）：**可达**（HTTP 200），FetchURL 同样失败，curl 成功
- 未尝试禁止来源域名，无法验证白名单拒绝行为

白名单生效状态只能由运行时探测报告确认，本文件不声称已生效。

## 模型验证

- **LibreOffice 7.4 重算验证通过**：将所有公式页（Forecast、DCF、Outputs）通过 LibreOffice Calc headless 重算后与 Python 独立计算逐项对比，所有值完全一致。
- NWC_FY0 = -4,516.90（负值反映经营性流动负债大于经营性流动资产，符合零售/餐饮行业的典型负 NWC 特征）
- 最终估值：企业价值 52,235.40 百万美元，股权价值 40,210.20 百万美元，每股 35.36 美元

## 建模日期

建模执行于 **2026-11-23**。所有数据截至 **2024-11-27**，未使用截止日后信息。