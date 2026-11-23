你是 DCF Eval v3 A 行业扩充的独立造题代理，不是答题代理。只负责 **A10**。

## 目标

把 `/Users/link/Desktop/Finance Bench/exp/dcf_factory_v3/tasks/A10/` 做成与题面一致的**完整可验收题包**。

- 权威题面：`a_expansion/A04_INSTRUCTION.md`（原编号为 A04 的医药管线草案）（中文，不要改写其业务口径；若发现题面自相矛盾或无法唯一计算，最小修订并在报告中逐条说明）。
- 没有现成 spec，你需按题面设计全部公开假设：商业化产品、两个管线的患者漏斗、上市年份、LOE、承诺研发、商业化准备费、PoS、NOL、股权桥；数值须经济合理。
- 这是**新增题**，新建 `tasks/A10/` 目录。A01–A08 是已完成的原题，**一律不得修改或覆盖**。
- 题面草案中的编号、公司名要改为：编号 `A10`，公司名 `濯川生物`（避免与 A03“衡铸工业”、A04“澜序医药”重名）；标题与正文中的旧编号和旧公司名一并替换。

## 必须交付（写入 `tasks/A10/`）

- `instruction.md`：上述权威题面。
- `spec.json`：`family: "A"`，含 `task_id`、`industry`、`industry_name`、`base_structure`、`industry_drivers`、全部公开假设。
- `environment/inputs.json`、`environment/inputs.xlsx`：只给事实、假设、语义键和 `public_output_keys`，不给公式模板或答案。
- `solution/reference.xlsx`（活公式，可经 LibreOffice 重算）、`solution/memo.md`、`solution/solve.sh`。
- `tests/expected.json`：**独立 Python 计算**的真值（不能从 reference 反读），含基准值、至少两组隐藏扰动的真值、以及 5×5 敏感性网格每格真值。
- `tests/grader.py`、`tests/test.sh`、`task.toml`：沿用其他 A 题的同名文件结构（参考 `tasks/A01/`、`tasks/A05/`），保证 Harbor 可运行。

## 必须实际运行的验收

把验收结果写入 `a_expansion/A10_validation.json`：
1. 参考工作簿经 LibreOffice 重算后，全部 `public_output_keys` 与独立真值一致（相对误差 ≤1e-6）；
2. 两组隐藏扰动正确传导；
3. 5×5 敏感性每格与真值一致，中心格等于基准；
4. 负例被拒绝：空白工作簿、静态粘贴数值、以及本题专项错误（管线上市前产生收入；承诺研发乘 PoS；commercial 乘 PoS；PoS 改 WACC；管线峰值现金流用 Gordon 永久资本化；NOL 超过 80% 限额）。

## 约束

- 只新建或修改 `tasks/A10/`、`a/A10.json`、`a_expansion/` 下以 A10 开头的文件。不要改其他题（尤其 A01–A08）、`generate.py`、`validate.py`、`validation.json`、rubric 库或 v2。
- 可只读复用 `core/model.py`、`core/workbook.py`、`core/grader.py`、`generate.py` 的写法。
- 先做通基准值，再加扰动、敏感性和负例；失败如实写入报告，不得把失败说成通过。
- 不读长日志和图片。模型 API 在 `http://127.0.0.1:4310/v1/messages`，不读写密钥。
- 最终回复简述：题包文件、验收结果、对题面的修订（如有）。
