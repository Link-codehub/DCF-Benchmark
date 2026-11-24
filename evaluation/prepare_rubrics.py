#!/usr/bin/env python3
"""Freeze executable rubric scope without changing selector evidence or task truth."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Model evidence is not requested in these workbook-only deliverables. Removing a
# presentational rubric does not imply the memo is exempt from its own llm/agent checks.
DROP_PRESENTATION = {"X-IC-007", "X-IC-008"}
RULE_TO_AGENT = {
    "X-FM-002", "X-FM-003", "X-FM-004", "X-FM-005", "X-FM-006",
    "X-IN-001", "X-IN-002", "X-IN-003", "X-IN-004", "X-IN-005",
    "X-IN-006", "X-IN-007", "X-IN-008", "X-IN-009", "X-TA-002",
}
UNSUPPORTED_DETERMINISTIC = {
    # They require internal layout or an independent presentation, not a semantic
    # output value. They may be explicitly inspected later, but never auto-failed.
    "X-IF-001a", "X-IF-001b", "X-IF-002", "X-FM-007", "X-FM-009",
    "X-FM-010", "X-FM-011", "X-FM-013", "X-FM-015", "X-IC-002",
    "X-IC-003", "X-IC-004", "X-PR-001a", "X-PR-001b", "X-PR-002",
    "X-PR-003", "X-PR-004", "X-PR-005", "X-PR-006", "X-PR-007",
    "X-PR-008", "X-PR-010", "X-PR-011", "X-PR-012", "X-PR-016",
    "X-A-001", "X-A-002",
}


def main():
    audit = []
    for path in sorted((ROOT / "tasks").glob("*/rubric.json")):
        data = json.loads(path.read_text())
        original = json.loads(json.dumps(data))
        kept = []
        for item in data["items"]:
            reason = None
            if item["id"] in DROP_PRESENTATION:
                reason = "本题不要求 PPT/PDF/摘要展示材料；该展示一致性条目不适用"
            elif item["id"] in RULE_TO_AGENT:
                item["original_method"] = item["method"]
                item["method"] = "agent"
                item["execution_note"] = "需结合公开输入与公式依赖做结构判断，不以结果数值碰巧正确替代结构核验"
            elif item["id"] in UNSUPPORTED_DETERMINISTIC and item["method"] == "rule":
                item["method"] = "agent"
                item["execution_note"] = "需检查工作簿结构或公式，不由宏观数值检查推断通过"
            if reason:
                audit.append({"task": data["task_id"], "id": item["id"], "action": "excluded", "reason": reason})
            else:
                kept.append(item)
        data["items"] = kept
        data["weight_total"] = sum(i["weight"] for i in kept)
        data["scope_revision"] = {"version": 1, "original_items": len(original["items"]),
            "executable_items": len(kept), "excluded": [r for r in audit if r["task"] == data["task_id"]],
            "selector_evidence_preserved": "原始挑选 attempts 保留；这些修订不代表原选择器结果"}
        (path.parent / "rubric_original.json").write_text(json.dumps(original, ensure_ascii=False, indent=2) + "\n")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "scoring" / "scope_audit.json").write_text(json.dumps({"version": 1, "changes": audit}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"tasks": len(list((ROOT / "tasks").glob("*/rubric.json"))), "excluded": len(audit)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
