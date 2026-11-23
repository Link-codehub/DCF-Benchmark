#!/usr/bin/env python3
"""Per-task rubric selection: an LLM picks concrete rubric IDs, then the program validates."""
import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIBRARY = json.loads((ROOT / "rubric_library" / "library.json").read_text())
BY_ID = {r["id"]: r for r in LIBRARY}

# Items every task of a family must carry regardless of the LLM choice.
MANDATORY = {
    "BC": ["01-FILE", "01-KEYS", "03-MARGIN", "03-NWC", "B-NWC-OPEN", "B-RESIDUAL", "05-DF", "05-TV", "05-BRIDGE", "05-VPS",
           "06-FORMULA", "06-RECALC", "06-PERTURB1", "06-PERTURB2", "06-LINKS"],
    "A": ["A-DRIVER", "A-METRIC"],
    "D": ["D-FINAL-VALUES", "D-FINAL-LIVE", "D-STEP-SNAPSHOT", "D-STEP-VALUES", "01-HISTORY", "08-OLD"],
    "E": ["E-deliver_model", "E-deliver_simulator", "E-deliver_trials", "07-PATHS", "07-QUANTILE", "E-mc_recompute"],
    "W": ["W-VALUE", "W-SOURCE", "W-CROSS", "W-USED", "W-NOFORBID"],
}
# Which library families a task family may draw from.
ALLOWED = {"R": {"BC", "A"}, "BC": {"BC"}, "A": {"BC", "A"}, "D": {"BC", "D"}, "E": {"BC", "E"}, "W": {"BC", "W"}}


def call_llm(prompt, model):
    body = json.dumps({"model": model, "max_tokens": 4000, "stream": True, "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": prompt}]}).encode()
    log = []
    for attempt in range(1, 4):
        started = time.time()
        text, error = "", None
        try:
            request = urllib.request.Request(os.environ.get("LLM_JUDGE_BASE", "http://127.0.0.1:4311") + "/v1/messages",
                data=body, headers={"content-type": "application/json", "accept": "text/event-stream"})
            with urllib.request.urlopen(request, timeout=180) as response:
                for raw in response:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    try:
                        event = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "content_block_delta" and event.get("delta", {}).get("type") == "text_delta":
                        text += event["delta"].get("text", "")
                    if event.get("type") == "message_stop" or time.time() - started > 240:
                        break
            start = text.find('{"selected"')
            if start < 0:
                start = text.find("{")
            if start >= 0:
                answer, _ = json.JSONDecoder().raw_decode(text[start:])
                if isinstance(answer, dict) and isinstance(answer.get("selected"), list):
                    log.append({"attempt": attempt, "seconds": round(time.time() - started, 1), "chars": len(text)})
                    return answer, log
            error = "no selected list in response"
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:200]
        log.append({"attempt": attempt, "seconds": round(time.time() - started, 1), "chars": len(text), "error": error})
        time.sleep(5 * attempt)
    return None, log


def select(task_dir, model):
    task_dir = Path(task_dir)
    spec = json.loads((task_dir / "spec.json").read_text())
    family = spec["family"]
    instruction = (task_dir / "instruction.md").read_text()
    pool = [r for r in LIBRARY if r["family"] in ALLOWED[family]]
    structure = spec.get("c_structure")
    modules = set(spec.get("enabled_modules", []))
    excluded = {"X-IC-007", "X-IC-008"}
    if structure != "multi_method":
        excluded |= {"C-MULTI-SPLIT", "X-IC-005", "C-IMPLIED-MULT", "C-IMPLIED-G", "C-REVERSE", "C-RANGE"}
    if structure not in ("three_statements_dcf", "debt_schedule_dcf"):
        excluded |= {"04-BALANCE", "04-CASH", "04-RE"}
    if "debt_schedule" not in modules and structure != "debt_schedule_dcf":
        excluded.add("03-DEBT")
    if "dual_terminal" not in modules:
        excluded.add("05-DUAL")
    if "intangible_pool" not in modules and family not in ("R",):
        excluded |= {"B-INTANG-ROLL", "B-INTANG-FCFF"}
    if "mixed_ltm" not in spec.get("b_items", []):
        excluded.add("B-MIXLTM")
    if "scenario" not in modules:
        excluded |= {"C-CASE-SWITCH", "C-CASE-ISOLATE"}
    if structure not in ("simple_dcf", "three_statements_dcf", "debt_schedule_dcf") and not spec.get("segments"):
        excluded.add("04-PPE")
    if not spec.get("assumptions", {}).get("lease_additions") and not spec.get("bridge", {}).get("lease_liability"):
        excluded.add("03-LEASE")
    if not spec.get("assumptions", {}).get("sensitivity_alloy_multiplier"):
        excluded |= {"X-IC-001", "X-IC-002", "X-IC-003", "X-IC-004"}
    pool = [r for r in pool if r["id"] not in excluded]
    scope = {
        "E": "E 题为开放预测：答题者自定假设并自写 Monte Carlo；不存在隐藏输入扰动，不存在固定数值真值，输出为固定 schema；评分重点是历史事实、机制一致性、模拟正确性与假设论证。",
        "W": "W 题为联网取数后建模：重点是取数值、来源、交叉验证、取数被模型引用，以及模型机制正确。",
        "BC": "BC 题为确定性建模：存在独立数值真值与隐藏输入扰动。",
        "A": "A 题为行业适配建模：存在独立数值真值，重点是行业驱动与行业估值口径。",
        "D": "D 题为多步修改：重点是最终结果与每一步快照。",
        "R": "R 题是从历史版本复用、模型曾得低分的确定性建模题：存在独立数值真值与隐藏输入扰动；评分重点与 BC 相同，涉及经营驱动时也可挑行业驱动类条目。",
    }[family]
    header = ("你是 DCF 评测的评分设计者。根据题目 spec 和题面，从下面这一批候选中挑选**适用于本题的具体 rubric ID**。\n"
        f"题族说明：{scope}\n"
        "挑选标准：只挑同时满足以下三点的条目——(1) 题面明确要求或该题族必然涉及；(2) 能用本题交付物判定 0/1；"
        "(3) 不与本批已选条目重复检查同一点。题面未要求的格式、颜色、打印、PPT/PDF 等呈现项不要挑。"
        "宁少勿多；一批里没有适用条目时返回空列表。不要编造 ID；理由不超过 15 字。只返回 JSON："
        '{"selected":[{"id":"...","reason":"..."}]}\n\n'
        f"## 题目 spec\n{json.dumps(spec, ensure_ascii=False)[:5000]}\n\n## 题面\n{instruction[:5000]}\n\n## 本批候选\n")
    batches = {}
    for r in pool:
        batches.setdefault(r["category"], []).append(r)
    answer, attempts = {"selected": []}, {}
    failed_batches = []
    for category, rows in batches.items():
        catalog = "\n".join(f"{r['id']} | {r['importance']} | 适用:{r['applies_when']} | {r['requirement']}" for r in rows)
        part, log = call_llm(header + catalog, model)
        attempts[category] = log
        if part is None:
            failed_batches.append(category)
        else:
            answer["selected"].extend(part.get("selected", []))
    if len(failed_batches) == len(batches):
        answer = None
    picked, reasons, invalid = [], {}, []
    for entry in (answer or {}).get("selected", []):
        rid = entry.get("id")
        if rid in BY_ID and BY_ID[rid]["family"] in ALLOWED[family]:
            if rid not in picked:
                picked.append(rid)
                reasons[rid] = entry.get("reason", "")
        else:
            invalid.append(rid)
    forced = []
    for rid in MANDATORY.get(family, []):
        if rid in BY_ID and rid not in picked:
            picked.append(rid)
            forced.append(rid)
            reasons[rid] = "程序强制必选项"
    base_needed = {"R": MANDATORY["BC"], "BC": MANDATORY["BC"], "A": MANDATORY["BC"], "D": MANDATORY["BC"],
        "E": ["01-FILE", "01-KEYS", "05-DF", "05-TV", "05-BRIDGE", "05-VPS", "06-FORMULA", "06-RECALC", "06-LINKS"],
        "W": ["01-FILE", "01-KEYS", "03-MARGIN", "03-NWC", "05-DF", "05-TV", "05-BRIDGE", "05-VPS", "06-FORMULA", "06-RECALC", "06-LINKS"]}[family]
    if family != "BC":
        for rid in base_needed:
            if rid not in picked:
                picked.append(rid)
                forced.append(rid)
                reasons[rid] = "程序强制必选项"
    if family in ("E", "W"):
        dropped = {"06-PERTURB1", "06-PERTURB2"}
        picked = [r for r in picked if r not in dropped]
    items = [dict(BY_ID[r], reason=reasons[r]) for r in picked]
    result = {"task_id": spec["task_id"], "family": family, "selector_model": model, "llm_attempts": attempts,
        "llm_ok": answer is not None, "failed_batches": failed_batches, "invalid_ids_dropped": invalid, "forced_mandatory": forced,
        "weight_total": sum(i["weight"] for i in items), "items": items}
    (task_dir / "rubric.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", nargs="+")
    parser.add_argument("--model", default="claude-opus-5-5")
    args = parser.parse_args()
    for task in args.tasks:
        r = select(task, args.model)
        print(json.dumps({k: r[k] for k in ("task_id", "family", "llm_ok", "invalid_ids_dropped", "forced_mandatory", "weight_total")} | {"n": len(r["items"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
