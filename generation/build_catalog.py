#!/usr/bin/env python3
"""Render the complete v3 catalog: process, every task, the full rubric library and per-task selections."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "V3_TASKS_AND_RUBRICS.md"
ORDER = {"BC": 0, "A": 1, "D": 2, "E": 3, "W": 4, "R": 5}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def cell(value):
    return str(value).replace("|", "/").replace("\n", " ")


def task_dirs():
    found = []
    for task in sorted((ROOT / "tasks").glob("*")):
        spec = task / "spec.json"
        if spec.is_file():
            found.append((ORDER.get(load(spec).get("family"), 9), task.name, task))
    return [t for _, _, t in sorted(found)]


def instructions(task):
    found = []
    main = task / "instruction.md"
    if main.is_file():
        found.append(("", main.read_text(encoding="utf-8").strip()))
    steps = sorted(task.glob("steps/*/instruction.md")) or sorted(task.glob("step-*/instruction.md"))
    found.extend((p.parent.name, p.read_text(encoding="utf-8").strip()) for p in steps)
    return found


def spec_block(add, title, path):
    add(f"<details><summary>{title}</summary>")
    add("")
    add("```json")
    add(path.read_text(encoding="utf-8").strip())
    add("```")
    add("")
    add("</details>")
    add("")


def validate_sources(library, tasks):
    assert library, "rubric library is empty"
    library_ids = [r["id"] for r in library]
    assert len(library_ids) == len(set(library_ids)), "duplicate library rubric IDs"
    assert tasks, "no tasks found"
    selected = {}
    for task in tasks:
        assert (task / "instruction.md").is_file(), f"{task.name}: missing instruction.md"
        rubric = load(task / "rubric.json")
        items = rubric["items"]
        assert items, f"{task.name}: empty selected rubrics"
        item_ids = [r["id"] for r in items]
        assert len(item_ids) == len(set(item_ids)), f"{task.name}: duplicate selected rubric IDs"
        unknown = set(item_ids) - set(library_ids)
        assert not unknown, f"{task.name}: selected IDs absent from library: {sorted(unknown)}"
        assert sum(r["weight"] for r in items) == rubric["weight_total"], f"{task.name}: incorrect weight_total"
        selected[task.name] = items
    return selected


def main():
    library = load(ROOT / "rubric_library" / "library.json")
    tasks = task_dirs()
    selected_items = validate_sources(library, tasks)
    lines = []
    add = lines.append
    add("# DCF Eval v3：题目、Rubrics 与生产过程（完整版）")
    add("")
    add("> 本文从 `exp/dcf_factory_v3/` 的源文件直接生成：契约、外部代理提示词、全部题目的 spec 与中文题面、统一 rubric 库，以及每道题由 API 挑出的 rubric。不含隐藏真值和参考答案。")
    add("")
    fam_counts = Counter(load(t / "spec.json")["family"] for t in tasks)
    add("## 1. 总览")
    add("")
    add("| 题族 | 题数 | 构成 |")
    add("|---|---:|---|")
    desc = {"BC": "B 时间与会计机制 × C 输出与估值结构", "A": "固定 BC 基座 × 行业/商业模式", "D": "独立 BC 起点 + 3–4 次结构修改",
        "E": "真实公司冻结历史 + 开放假设 + 自写 Monte Carlo", "W": "指定来源联网取数 + 建模", "R": "历史版本中模型低分题原样复用（v1 B01、v2 F01）"}
    for fam in ORDER:
        add(f"| {fam} | {fam_counts.get(fam, 0)} | {desc[fam]} |")
    add(f"| 合计 | {len(tasks)} | |")
    add("")
    add(f"统一 rubric 库共 **{len(library)}** 条（主需权重 3，次需权重 1）。")
    add("")
    add("## 2. 生产过程")
    add("")
    add("```text")
    add("1. 总控写契约 CONTRACT.md（题族、B/C 菜单、A 行业分类、D/E/W 规则）")
    add("2. 统一 rubric 库：v2 共享原子 + v2 E 评分项（去重）+ v3 新增 + 外部 benchmark 蒸馏")
    add("3. 外部造题代理（Kimi Code CLI，kimi-k3.1-pro）")
    add("     CORE  → BC / A / D 题目、活公式参考、独立真值、验收")
    add("     OPEN  → E / W 题目、参考实现、评分器")
    add("     DISTILL → 外部约 2,380 条细则去重蒸馏")
    add("4. 每题生成后调用 LLM API（claude-opus-5-5）按类别分批，从库中逐条挑选 rubric ID；程序补齐必选项、剔除不适用与编造 ID")
    add("5. 参考答案重算、空白/静态负例验收")
    add("```")
    add("")
    add("外部代理与当前总控会话不共享上下文，只读各自提示词和契约；造题不使用 Harbor，Harbor 只用于被测模型答题。")
    add("")
    add("### 2.1 造题方法")
    add("")
    add("| 题族 | 怎么造 | 怎么核验 |")
    add("|---|---|---|")
    add("| BC | 每题从 B 菜单抽 4–7 项、从 C 菜单抽 1 种结构；16 题须覆盖混合历史 LTM、双资产池、首期 ΔNWC 两种口径，以及 C 的全部七种结构 | 独立 Python 真值 + 活公式参考工作簿，LibreOffice 重算一致；两组隐藏扰动；空白/静态负例被拒 |")
    add("| A | 固定 3–4 个 BC 基座，每题抽 1 个行业大类 + 类内 2–3 个驱动；金融、保险、房地产使用行业适配估值 | 同 BC，另检查行业指标与行业估值口径 |")
    add("| D | 独立新生成一道 BC 结构题（不复用 BC 题族），再做 3–4 次结构性修改；每步保存快照 | 两层：最后一步完整真值与活公式；每一步快照对照该步真值、修改范围、历史未被篡改 |")
    add("| E | 选 4 家 v2 真实公司冻结历史，中文题面；答题者自写 Monte Carlo（≥5,000 路径、指定 seed） | 独立复算分布、相关性、路径算术与分位数；未来实际值与股价只作诊断 |")
    add("| W | 真实上市公司，限定 SEC/公司 IR/国债收益率取数后建模 | 取数值对照权威真值、来源可追溯、交叉验证、取数被模型引用、未用禁止来源 |")
    add("| R | 从历史版本挑真实模型得分低的题原样复用：R01=v1 B01 衡岳流体装备（Kimi 0.56/类别清零 0.44，Claude 0.25）；R02=v2 F01 企业档案订阅（Kimi 0.04–0.10，千问 0）。题面数据、参考答案与评分器沿用原版，只改编号与标题；rubric 由 Opus 5.5 从统一库重挑 | 原评分器在 v3 本地复验：参考 reward=1.0，空白工作簿被拒 |")
    add("")
    add("题面写法：抽样结果只用于造题；题面不出现“B 项”“C 结构”“BC 基座”等标签，而是把抽到的时间口径、历史形式、难点与输出结构写成自然业务要求。")
    add("")
    add("B 菜单：非自然财年；年度/半年/季度/混合历史拼接 LTM；FY 与 LTM 规范化；残余期＋4–6 期预测；实际天数与年中/期末折现；营运资本天数法或比例法及首期 ΔNWC 口径；D&A 比例、固定资产滚动或固定资产＋无形资产双资产池；Gordon/退出/双终值；完整股权桥；现金税与 NOL。")
    add("")
    add("C 菜单：简版 DCF；三表＋DCF；分部经营模型＋SOTP；风险调整管线 DCF；情景驱动 Operating Model；多方法估值与反推（隐含倍数、隐含 g、隐含 WACC、估值区间）；债务计划表＋DCF。")
    add("")
    add("A 行业大类：软件与订阅、消费零售与连锁、制造与工业设备、医药与生物科技、医疗服务、银行与金融、保险、能源与资源、公用事业与基础设施、交通与物流、互联网平台与媒体、房地产、专业服务与外包、设备即服务与装机运维。")
    add("")
    add("### 2.2 Rubric 方法")
    add("")
    add("1. **统一库**：v2 F/D 共享原子与 v2 E 评分项合并，去掉 7 条同义项；补 v3 新增（B/C 扩展、行业、多步、联网）；再从外部 benchmark 约 2,380 条细则蒸馏补缺。")
    add("2. **原子与唯一判定**：每条只判一个点，能无歧义判 0/1；复合条目拆开（如 X-PR-001、X-IF-001 各拆为两条）。")
    add("3. **主需/次需**：取消严重度，主需权重 3、次需权重 1。")
    add("4. **逐题挑选**：题目生成后调用 `claude-opus-5-5`，与造题模型不同家族；按类别分批提交候选，每批只挑适用的具体 ID 并给出理由。")
    add("5. **程序校验**：剔除不存在或不属于该题族的 ID；补齐各题族必选项（如 BC 的输出键、NWC、折现、终值、股权桥、活公式、重算、两组扰动、无外链）；记录哪些是 LLM 选的、哪些是程序补的。")
    add("6. **执行方法**：rule 由程序检查；llm 每条单独调用一次；agent 一次会话评同题一小组，必须留工具证据。")
    add("")
    add("### 2.3 Rubric 库来源")
    add("")
    src = Counter(r["source"].split(":")[0] for r in library)
    labels = {"v2-shared": "v2 F/D 共享原子", "v2-E": "v2 E 评分项（去重后）", "v3-new": "v3 新增（B/C 扩展、行业、多步、联网）",
        "distilled": "外部 benchmark 蒸馏（BTB、BlueFin、FrontierFinance、EMB）"}
    add("| 来源 | 条数 |")
    add("|---|---:|")
    for key, value in src.items():
        add(f"| {labels.get(key, key)} | {value} |")
    add("")
    report = ROOT / "rubric_library" / "distill_report.md"
    if report.is_file():
        add("### 2.4 外部 benchmark 蒸馏报告")
        add("")
        add("\n".join(("##### " + ln.lstrip("#").strip()) if ln.startswith("#") else ln for ln in report.read_text(encoding="utf-8").strip().splitlines()))
        add("")
    add("## 3. 统一 Rubric 库（全部条目）")
    add("")
    add("**具体要求**为可判定 0/1 的原子断言；**方法** rule=程序检查，llm=单项 LLM 判定，agent=工具型 Agent 判定。")
    add("")
    for category in dict.fromkeys(r["category"] for r in library):
        rows = [r for r in library if r["category"] == category]
        add(f"### {category}（{len(rows)} 条）")
        add("")
        add("| ID | 具体要求 | 证据 | 适用 | 方法 | 主/次 |")
        add("|---|---|---|---|---|---|")
        for r in rows:
            add("| " + " | ".join(cell(r[k]) for k in ("id", "requirement", "evidence", "applies_when", "method", "importance")) + " |")
        add("")
    add("## 4. 验收结果")
    add("")
    core_v = load(ROOT / "validation.json")
    open_v = load(ROOT / "open" / "validation.json")
    s = core_v["summary"]
    add(f"**BC/A/D**（`validation.json`）：{s['tasks']} 题、{s['d_steps']} 个 D 步骤；{s['passed']}/{s['validated_workbooks']} 份参考工作簿经 LibreOffice 重算后与独立真值一致，失败 {s['failed']}。每份工作簿两组隐藏扰动均正确传导；空白与静态负例全部被拒绝。")
    add("")
    cov = core_v["coverage"]
    add("C 结构覆盖：" + "；".join(f"{k}：{'、'.join(v)}" for k, v in cov["c_coverage"].items()) + "。")
    add("")
    add(f"B 关键项：混合历史 LTM {'、'.join(cov['mixed_ltm'])}；双资产池 {'、'.join(cov['dual_asset_pool'])}；首期 ΔNWC 用估值日余额 {'、'.join(cov['nwc_valuation_open'])}，用财年末余额 {'、'.join(cov['nwc_fye_open'])}。")
    add("")
    add("**E/W**（`open/validation.json`）：")
    add("")
    add("| 题 | 本地参考 | Harbor 参考 |")
    add("|---|---:|---:|")
    for tid, r in open_v["tasks"].items():
        add(f"| {tid} | {r['local_reference']['reward']} | {r['harbor']['reward'].get('reward') if isinstance(r['harbor'].get('reward'), dict) else r['harbor'].get('reward')} |")
    add("")
    add("限制：" + "；".join(open_v["limitations"]))
    add("")
    for name in ("A09", "A10"):
        path = ROOT / "a_expansion" / f"{name}_validation.json"
        if path.is_file():
            v = load(path)
            add(f"**{name}**（`a_expansion/{name}_validation.json`）：" + json.dumps(v.get("summary", {k: v[k] for k in list(v)[:6]}), ensure_ascii=False)[:1200])
            add("")
    rv = ROOT / "tasks" / "R_validation.json"
    if rv.is_file():
        add("**R01/R02 复用题**（`tasks/R_validation.json`）：" + "；".join(f"{k} 参考 reward={v['reference']}，空白工作簿 reward={v['blank']}" for k, v in load(rv).items()) + "。评分器为原版本，未改动。")
        add("")
    add("> 参考答案满分只说明题目、真值与评分器闭环成立，不代表被测模型能得高分；llm/agent 语义评分尚未执行。")
    add("")
    failed = [(t.name, load(t / "rubric.json").get("failed_batches", [])) for t in tasks if (t / "rubric.json").is_file()]
    failed = [(n, b) for n, b in failed if b]
    if failed:
        add("**Rubric 挑选状态说明：** `llm_ok` 仅表示至少一个类别批次成功。以下题有类别批次失败，该类别只含程序补齐的必选条目：" + "；".join(f"{n}（{'、'.join(b)}）" for n, b in failed) + f"。其余 {len(tasks) - len(failed)} 题没有失败批次。")
        add("")
    picks = [load(t / "rubric.json") for t in tasks if (t / "rubric.json").is_file()]
    if picks:
        add("### 逐题 rubric 挑选统计")
        add("")
        add("| 题族 | 题数 | 每题条数 | 平均程序补齐 |")
        add("|---|---:|---|---:|")
        for fam in ORDER:
            group = [p for p in picks if p["family"] == fam]
            if group:
                counts = [len(p["items"]) for p in group]
                forced = sum(len(p["forced_mandatory"]) for p in group) / len(group)
                add(f"| {fam} | {len(group)} | {min(counts)}–{max(counts)} | {forced:.1f} |")
        add("")
    add("## 5. 全部题目")
    add("")
    add("每题包含完整 spec、完整中文题面和全部选中 rubric；D 题另含各步骤完整 spec 与题面。spec 折叠仅为便于阅读，不作内容截断。")
    add("")
    for task in tasks:
        spec = load(task / "spec.json")
        add(f"### {task.name}（{spec.get('family')}）")
        add("")
        spec_block(add, f"{task.name}｜完整 spec", task / "spec.json")
        for name, text in instructions(task):
            if name:
                add(f"#### {name}")
                add("")
                spec_block(add, f"{task.name}/{name}｜完整 spec", task / "steps" / name / "spec.json")
            body = "\n".join(("##### " + ln.lstrip("#").strip()) if ln.startswith("#") else ln for ln in text.splitlines())
            add(body)
            add("")
        rubric = load(task / "rubric.json")
        items = rubric["items"]
        add(f"#### {task.name} 选用的 rubric（{len(items)} 条，权重合计 {rubric['weight_total']}；挑选模型 `{rubric['selector_model']}`，LLM 成功={rubric['llm_ok']}，程序补齐 {len(rubric['forced_mandatory'])} 条）")
        add("")
        add("| ID | 类别 | 具体要求 | 方法 | 主/次 | 挑选理由 |")
        add("|---|---|---|---|---|---|")
        for r in items:
            add("| " + " | ".join(cell(r[k]) for k in ("id", "category", "requirement", "method", "importance", "reason")) + " |")
        add("")
    add("## 附录：契约与外部代理提示词原文")
    add("")
    for title, path in (("契约 CONTRACT.md", "CONTRACT.md"), ("CORE 提示词", "prompts/CORE.md"), ("OPEN 提示词", "prompts/OPEN.md"), ("DISTILL 提示词", "prompts/DISTILL.md")):
        add(f"### {title}")
        add("")
        add("````text")
        add((ROOT / path).read_text(encoding="utf-8").strip())
        add("````")
        add("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    text = OUT.read_text(encoding="utf-8")
    for path in [task / "spec.json" for task in tasks] + [step / "spec.json" for task in tasks for step in task.glob("steps/step-*")]:
        assert path.read_text(encoding="utf-8").strip() in text, f"spec not written in full: {path}"
    for task in tasks:
        assert f"### {task.name}（" in text, f"missing task: {task.name}"
        for name, instruction in instructions(task):
            body = "\n".join(("##### " + ln.lstrip("#").strip()) if ln.startswith("#") else ln for ln in instruction.splitlines())
            assert body in text, f"instruction not written in full: {task.name}/{name or 'main'}"
        for r in selected_items[task.name]:
            row = "| " + " | ".join(cell(r[k]) for k in ("id", "category", "requirement", "method", "importance", "reason")) + " |"
            assert row in text, f"missing selected rubric: {task.name}/{r['id']}"
    for category in dict.fromkeys(r["category"] for r in library):
        rows = [r for r in library if r["category"] == category]
        assert f"### {category}（{len(rows)} 条）" in text, f"missing category: {category}"
        for r in rows:
            row = "| " + " | ".join(cell(r[k]) for k in ("id", "requirement", "evidence", "applies_when", "method", "importance")) + " |"
            assert row in text, f"missing library rubric: {r['id']}"
    print(json.dumps({"output": str(OUT), "tasks": len(tasks), "families": dict(fam_counts), "library": len(library),
        "with_rubric": len(selected_items), "selected_rubrics": sum(map(len, selected_items.values())),
        "full_specs": len(tasks) + sum(len(list(task.glob("steps/step-*/spec.json"))) for task in tasks),
        "full_instructions": sum(len(instructions(task)) for task in tasks), "bytes": OUT.stat().st_size,
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest()[:16]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
