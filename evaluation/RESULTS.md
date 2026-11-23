# DCFEval 模型实测结果

本次主要由于 API 额度不足，只分别测评了 Kimi K3.1 Pro 的 18 道题和 DeepSeek V4 Pro 的 14 道题。

主口径：每题主需 3、次需 1；公式与模型工程类任一失败整类清零，其余类别逐项累计；模型总分为已完成题目百分制算术平均。只有真实交付才进入分数；断连和无交付不计分，也不计零分。

| 模型 | 完整评分题数 | 百分制得分 | rule 条目通过率 | DCF 核心机制与公式通过率 |
|---|---:|---:|---:|---:|
| deepseek-v4-pro | 14 | 43.43 | 51.13% | 45.04% |
| kimi-k3.1-pro | 18 | 50.80 | 57.31% | 51.62% |

## 逐题成绩

| 题 | 模型 | 百分制得分 | 主要失败项 |
|---|---|---:|---|
| A01 | deepseek-v4-pro | 27.85 | A-SAAS-ARR、03-AVERAGE、A-SAAS-CAPRD、03-MARGIN、03-NWC、B-NWC-OPEN、05-FCFF、05-DF |
| A01 | kimi-k3.1-pro | 29.11 | A-SAAS-ARR、03-AVERAGE、A-SAAS-CAPRD、03-MARGIN、03-NWC、B-NWC-OPEN、05-FCFF、05-DF |
| A02 | deepseek-v4-pro | 36.25 | 03-DRIVER、A-RETAIL-SSS、03-MARGIN、03-NWC、B-NWC-OPEN、05-FCFF、05-DF、B-RESIDUAL |
| A02 | kimi-k3.1-pro | 35.53 | 03-DRIVER、A-RETAIL-SSS、03-MARGIN、03-NWC、B-NWC-OPEN、05-FCFF、05-DF、B-RESIDUAL |
| A03 | kimi-k3.1-pro | 15.15 | 01-FILE、A-DRIVER、A-MFG-UTIL、03-CAPEX、03-MARGIN、03-NWC、A-REASON、05-FCFF |
| A04 | deepseek-v4-pro | 53.33 | A-DRIVER、A-PHARMA-CLIFF、03-MARGIN、05-FCFF、05-DF、06-RECALC、06-PERTURB1、06-PERTURB2 |
| A04 | kimi-k3.1-pro | 50.00 | A-DRIVER、A-PHARMA-CLIFF、03-MARGIN、03-NWC、05-FCFF、05-DF、06-RECALC、06-PERTURB1 |
| A05 | deepseek-v4-pro | 59.02 | A-BANK-NII、A-BANK-EQUITY、06-RECALC、06-PERTURB1、06-PERTURB2 |
| A05 | kimi-k3.1-pro | 54.10 | X-IN-001、A-BANK-NII、A-BANK-EQUITY、06-RECALC、06-PERTURB1、06-PERTURB2 |
| A06 | deepseek-v4-pro | 42.11 | 03-AVERAGE、03-MARGIN、03-NWC、A-ENERGY-DECLINE、05-FCFF、05-DF、06-RECALC、06-PERTURB1 |
| A07 | deepseek-v4-pro | 39.73 | A-UTIL-RAB、A-DRIVER、03-MARGIN、03-NWC、B-NWC-OPEN、A-REASON、05-FCFF、B-RESIDUAL |
| A07 | kimi-k3.1-pro | 44.87 | A-UTIL-RAB、A-DRIVER、03-MARGIN、03-NWC、B-NWC-OPEN、05-FCFF、B-RESIDUAL、06-RECALC |
| A08 | deepseek-v4-pro | 44.44 | A-VALUATION、A-RE-NAV、05-VPS、05-DILUTION、06-RECALC、06-PERTURB1、06-PERTURB2、09-READABLE |
| A08 | kimi-k3.1-pro | 51.85 | A-VALUATION、05-VPS、05-DILUTION、06-RECALC、06-PERTURB1、06-PERTURB2、05-BRIDGE |
| A09 | deepseek-v4-pro | 15.96 | 01-KEYS、X-IN-001、A-DRIVER、A-MFG-UTIL、A-MFG-YIELD、A-MFG-BOM、A-MFG-PURCHASE、A-MFG-INVENTORY |
| BC01 | kimi-k3.1-pro | 26.88 | 02-FY、02-LTM、02-REPORTED、02-SBC、03-DRIVER、03-AVERAGE、03-MARGIN、03-NWC |
| BC03 | kimi-k3.1-pro | 47.37 | 02-FY、02-LTM、02-REPORTED、02-SBC、X-IN-001、03-AVERAGE、03-MARGIN、C-SOTP-SEG |
| BC04 | kimi-k3.1-pro | 41.86 | 02-FY、02-LTM、02-REPORTED、02-SBC、X-IN-001、03-AVERAGE、C-PIPE-SUM、05-TV |
| E01 | deepseek-v4-pro | 43.48 | E-hist_revenue、E-hist_ebit、E-hist_eps、02-SBC、E-dcf_discount、05-TV、05-VPS、E-formula_perturb_g |
| E01 | kimi-k3.1-pro | 68.69 | E-dcf_discount、X-FM-001、E-mc_distributions、E-mc_recompute、E-llm_driver_derivation、X-TA-003、X-TA-009、05-DF |
| E02 | deepseek-v4-pro | 43.41 | 01-KEYS、E-hist_revenue、E-hist_ebit、E-hist_eps、02-SBC、E-llm_reinvestment_reasoning、E-dcf_fcff、E-dcf_discount |
| E03 | kimi-k3.1-pro | 73.24 | E-llm_reinvestment_reasoning、X-FM-001、E-mc_distributions、E-mc_recompute、E-llm_driver_derivation、X-TA-003、X-TA-006、X-TA-009 |
| E04 | deepseek-v4-pro | 37.01 | 01-KEYS、E-deliver_model、02-SBC、E-hist_revenue、E-hist_ebit、E-hist_eps、03-NWC、E-forecast_revenue |
| E04 | kimi-k3.1-pro | 54.33 | 01-KEYS、02-SBC、E-hist_revenue、E-hist_ebit、E-hist_eps、E-llm_reinvestment_reasoning、E-dcf_fcff、E-dcf_discount |
| R02 | kimi-k3.1-pro | 30.34 | 02-FY、02-LTM、02-REPORTED、02-COLLECT、X-IN-007、03-DRIVER、03-AVERAGE、03-NWC |
| W01 | deepseek-v4-pro | 54.21 | 01-KEYS、05-FCFF、X-FM-001、09-MEMO、W-VALUE、W-SOURCE、W-CROSS、W-USED |
| W01 | kimi-k3.1-pro | 66.67 | X-TA-009 |
| W02 | deepseek-v4-pro | 47.37 | 05-FCFF、X-FM-001、09-MEMO、W-SOURCE、W-CROSS、W-USED、W-FAILURE、X-TA-009 |
| W02 | kimi-k3.1-pro | 56.07 | 01-KEYS、05-FCFF、06-FORMULA、X-FM-001、09-MEMO、W-VALUE、W-SOURCE、W-CROSS |
| W03 | deepseek-v4-pro | 63.81 | 01-UNIT、05-FCFF、X-FM-001、09-MEMO、W-CROSS、W-USED、X-TA-004、X-TA-006 |
| W03 | kimi-k3.1-pro | 72.38 | 06-FORMULA、X-FM-001、09-MEMO、W-CROSS、W-USED、X-TA-009 |
| W04 | kimi-k3.1-pro | 96.00 | 09-MEMO、X-TA-009 |

## 高频失败项

| 类别 | Rubric | 失败份数 |
|---|---|---:|
| 公式与模型工程 | 06-RECALC | 19 |
| DCF与估值桥 | 05-DF | 19 |
| 公式与模型工程 | 06-PERTURB1 | 18 |
| 公式与模型工程 | 06-PERTURB2 | 18 |
| DCF与估值桥 | 05-FCFF | 18 |
| 经营预测 | 03-MARGIN | 14 |
| DCF与估值桥 | 05-VPS | 13 |
| DCF与估值桥 | 05-BRIDGE | 13 |
| 经营预测 | 03-NWC | 13 |
| 表达与专业可用性 | X-TA-009 | 12 |
| DCF与估值桥 | B-RESIDUAL | 11 |
| 经营预测 | A-DRIVER | 11 |
| 表达与专业可用性 | X-TA-006 | 11 |
| DCF与估值桥 | 05-TV | 11 |
| 经营预测 | B-NWC-OPEN | 10 |
| 经营预测 | A-METRIC | 9 |
| 公式与模型工程 | X-FM-001 | 8 |
| 经营预测 | 03-AVERAGE | 7 |
| 历史与会计口径 | 02-SBC | 7 |
| 表达与专业可用性 | 09-MEMO | 6 |
