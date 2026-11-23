你是 DCF Eval v3 A 行业扩充的独立造题代理，不是答题代理。只负责 **A09**。

## 目标

把 `/Users/link/Desktop/Finance Bench/exp/dcf_factory_v3/tasks/A09/` 做成与题面一致的**完整可验收题包**。

- 权威题面：`a_expansion/a03_instruction.md`（原编号为 A03 的 BOM 制造草案）（中文，不要改写其业务口径；若发现题面自相矛盾或无法唯一计算，最小修订并在报告中逐条说明）。
- 公开假设以 `a_expansion/spec_A03.json` 为起点；REVIEW.md 指出其价格、耗用与采购量纲需审阅，你必须核对量纲使经济情景合理，再定稿。
- 这是**新增题**，新建 `tasks/A09/` 目录。A01–A08 是已完成的原题，**一律不得修改或覆盖**。
- 题面草案中的编号、公司名要改为：编号 `A09`，公司名 `铖序精工`（避免与 A03“衡铸工业”、A04“澜序医药”重名）；标题与正文中的旧编号和旧公司名一并替换。

## 必须交付（写入 `tasks/A09/`）

- `instruction.md`：上述权威题面。
- `spec.json`：`family: "A"`，含 `task_id`、`industry`、`industry_name`、`base_structure`、`industry_drivers`、全部公开假设。
- `environment/inputs.json`、`environment/inputs.xlsx`：只给事实、假设、语义键和 `public_output_keys`，不给公式模板或答案。
- `solution/reference.xlsx`（活公式，可经 LibreOffice 重算）、`solution/memo.md`、`solution/solve.sh`。
- `tests/expected.json`：**独立 Python 计算**的真值（不能从 reference 反读），含基准值、至少两组隐藏扰动的真值、以及 5×5 敏感性网格每格真值。
- `tests/grader.py`、`tests/test.sh`、`task.toml`：沿用其他 A 题的同名文件结构（参考 `tasks/A01/`、`tasks/A05/`），保证 Harbor 可运行。

## 必须实际运行的验收

把验收结果写入 `a_expansion/A09_validation.json`：
1. 参考工作簿经 LibreOffice 重算后，全部 `public_output_keys` 与独立真值一致（相对误差 ≤1e-6）；
2. 两组隐藏扰动正确传导；
3. 5×5 敏感性每格与真值一致，中心格等于基准；
4. 负例被拒绝：空白工作簿、静态粘贴数值、以及本题专项错误（用收入乘材料成本率替代 BOM；良率作用两次；采购计入 COGS；三类存货合并为单一比例）。

## 约束

- 只新建或修改 `tasks/A09/`、`a/A09.json`、`a_expansion/` 下以 A09 开头的文件。不要改其他题（尤其 A01–A08）、`generate.py`、`validate.py`、`validation.json`、rubric 库或 v2。
- 可只读复用 `core/model.py`、`core/workbook.py`、`core/grader.py`、`generate.py` 的写法。
- 先做通基准值，再加扰动、敏感性和负例；失败如实写入报告，不得把失败说成通过。
- 不读长日志和图片。模型 API 在 `http://127.0.0.1:4310/v1/messages`，不读写密钥。
- 最终回复简述：题包文件、验收结果、对题面的修订（如有）。
