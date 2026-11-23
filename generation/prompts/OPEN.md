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
