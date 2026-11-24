#!/usr/bin/env python3
"""Score one candidate against selected rubric atoms, preserving raw evidence."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generation" / "core"))
import grader as core_grader
from map_rules import atom_results


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(mod)
    return mod


def atomic_core(task, candidate, work, soffice):
    expected = json.loads((task / "tests" / "expected.json").read_text())
    spec = json.loads((task / "tests" / "grader_spec.json").read_text())
    custom = task.name in ("A09", "A10")
    grader = module(task / "tests" / "grader.py", f"grader_{task.name}")
    report = grader.grade(task, candidate, work, soffice, True)
    report["expected"] = expected["baseline"]
    report["baseline_keys"] = list(expected["baseline"])
    output = {}
    for rid, fn in atom_results(task, spec, report).items():
        result = fn()
        result["method"] = "rule"
        output[rid] = result
    for index, variant in enumerate(report.get("perturbations", []), 1):
        result = {"status": "fail" if not variant.get("passed") else "pass", "method": "rule",
                  "evidence": {"id": variant.get("id"), "checked": variant.get("checked"), "mismatches": variant.get("mismatches_all", variant.get("mismatches", []))[:20]}}
        output[f"06-PERTURB{index}"] = result
    if custom:
        dependency = report.get("dependency_checks", {}).get("checks", {})
        mapping = {"bom_not_revenue_ratio": "A-MFG-BOM", "cogs_excludes_purchases": "A-MFG-PURCHASE",
                   "yield_applied_once": "A-MFG-YIELD", "three_inventory_pools_separate": "A-MFG-INVENTORY",
                   "sensitivity_25_independent_sheets": "X-IF-003", "sensitivity_full_recalculation": "X-IF-003"}
        for key, rid in mapping.items():
            if key in dependency:
                output[rid] = {"status": "pass" if dependency[key] else "fail", "method": "rule", "evidence": {"dependency_check": key}}
    output["rule_report_path"] = str(work / "rule_report.json")
    (work / "rule_report.json").write_text(json.dumps({k: v for k, v in report.items() if k not in ("expected", "baseline_keys")}, ensure_ascii=False, indent=2) + "\n")
    return output, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--soffice", default="/opt/homebrew/bin/soffice")
    parser.add_argument("--memo", type=Path)
    args = parser.parse_args()
    task = ROOT / "tasks" / args.task
    work = args.output.with_suffix("")
    work.mkdir(parents=True, exist_ok=True)
    selected = json.loads((task / "rubric.json").read_text())
    if args.task.startswith("R"):
        from native_reuse import grade as native_grade
        payload = native_grade(task, args.candidate, work, args.soffice)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"task": args.task, "native_reward": payload.get("native_reward"), "unexecuted_rules": payload["unexecuted_rules"]}, ensure_ascii=False))
        return
    if args.task.startswith(("E", "W")):
        from native_open import grade as native_open_grade
        artifact = args.candidate if args.candidate.is_dir() else args.candidate.parent
        payload = native_open_grade(task, artifact, work)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"task": args.task, "native_reward": payload.get("native_reward"), "unexecuted_rules": payload["unexecuted_rules"]}, ensure_ascii=False))
        return
    if args.task.startswith("D"):
        from multistep import evaluate_steps
        snapshot_dir = args.candidate.parent / "snapshots"
        atoms, step_reports = evaluate_steps(task, snapshot_dir, work, args.soffice)
        final_step = task / "steps" / f"step-{len(step_reports)}"
        final_expected = json.loads((final_step / "tests" / "expected.json").read_text())
        formulas, duplicate_formulas = core_grader.discover(__import__("openpyxl").load_workbook(args.candidate, data_only=False), final_expected["baseline"], formulas=True)
        live_ok = not duplicate_formulas and all(key in formulas for key in final_expected["baseline"])
        atoms["D-FINAL-LIVE"] = {"status": "pass" if live_ok else "fail", "nonformula_or_duplicate": sorted(set(final_expected["baseline"]) - set(formulas))[:30]}
        from structure_rules import evaluate as structure_evaluate
        from static_rules import evaluate as static_evaluate
        results = []
        for item in selected["items"]:
            rid = item["id"]
            result = atoms.get(rid, {"status": "not_executed", "reason": "需要独立语义/结构评审或最终步扰动检查"})
            if rid in ("X-TA-004", "X-TA-006", "X-TA-007"):
                result = structure_evaluate(args.candidate, item)
                result["method"] = "rule"
            elif rid in ("X-IF-001a", "X-IF-002", "X-IN-001", "X-IN-002", "X-FM-007", "X-FM-009", "X-FM-010"):
                result = static_evaluate(task, args.candidate, item)
                result["method"] = "rule"
            results.append({k: item[k] for k in ("id", "category", "importance", "weight", "method")} | {"rubric_method": item["method"], **result})
        payload = {"task": args.task, "candidate": str(args.candidate), "items": results, "steps": step_reports,
                   "semantic_pending": [r["id"] for r in results if r["rubric_method"] != "rule"],
                   "unexecuted_rules": [r["id"] for r in results if r["rubric_method"] == "rule" and r["status"] == "not_executed"]}
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"task": args.task, "atoms": len(results), "unexecuted_rules": payload["unexecuted_rules"]}, ensure_ascii=False))
        return
    atoms, raw = atomic_core(task, args.candidate, work, args.soffice)
    from structure_rules import evaluate as structure_evaluate
    from static_rules import evaluate as static_evaluate
    results = []
    for item in selected["items"]:
        rid = item["id"]
        result = atoms.get(rid, {"status": "not_executed", "reason": "该条需要独立语义/结构评审，不能从数值结果推断"})
        if rid in ("X-TA-004", "X-TA-006", "X-TA-007"):
            result = structure_evaluate(args.candidate, item)
            result["method"] = "rule"
        elif rid in ("X-IF-001a", "X-IF-002", "X-IN-001", "X-IN-002", "X-FM-007", "X-FM-009", "X-FM-010"):
            result = static_evaluate(task, args.candidate, item)
            result["method"] = "rule"
        results.append({k: item[k] for k in ("id", "category", "importance", "weight", "method")} | {"rubric_method": item["method"], **result})
    payload = {"task": args.task, "candidate": str(args.candidate), "rule_passed": raw.get("passed"),
               "items": results, "semantic_pending": [r["id"] for r in results if r["rubric_method"] in ("llm", "agent")],
               "unexecuted_rules": [r["id"] for r in results if r["rubric_method"] == "rule" and r["status"] == "not_executed"]}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"task": args.task, "rule_passed": raw.get("passed"), "atoms": len(results),
                      "unexecuted_rules": payload["unexecuted_rules"], "semantic_pending": len(payload["semantic_pending"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
