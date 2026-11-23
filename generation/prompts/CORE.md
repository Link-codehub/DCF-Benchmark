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
