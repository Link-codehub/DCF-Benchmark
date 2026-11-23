#!/usr/bin/env python3
"""Validate v3 tasks with real LibreOffice recalculation and explicit negative controls."""
import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parent
BASE = ROOT
sys.path.insert(0, str(ROOT / "core"))
from grader import grade


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def static_negative(reference, target):
    wb = load_workbook(reference, data_only=False)
    for ws in wb:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    c.value = 0
    wb.save(target)


def tasks(requested):
    result = []
    for tid in [f"BC{i:02d}" for i in range(1, 17)] + [f"A{i:02d}" for i in range(1, 9)]:
        if requested and tid not in requested: continue
        result.append((tid, BASE / "tasks" / tid, BASE / "tasks" / tid / "solution" / "reference.xlsx"))
    for i in range(1, 5):
        tid = f"D{i:02d}"
        if requested and tid not in requested: continue
        for step in sorted((BASE / "tasks" / tid / "steps").glob("step-*"), key=lambda p: int(p.name.split("-")[1])):
            result.append((f"{tid}/{step.name}", step, step / "solution" / "reference.xlsx"))
    return result


def structure(tid, task, reference):
    spec = json.loads((BASE / "tasks" / tid.split("/")[0] / "spec.json").read_text())
    expected_path = task / "tests" / "expected.json"
    missing = [p for p in ("environment/inputs.xlsx", "environment/inputs.json", "solution/reference.xlsx", "solution/solve.sh", "tests/expected.json", "tests/grader.py") if not (task / p).exists()]
    public = json.loads((task / "environment" / "inputs.json").read_text())
    wb = load_workbook(task / "environment" / "inputs.xlsx", data_only=False)
    formulas = sum(isinstance(c.value, str) and c.value.startswith("=") for ws in wb for row in ws for c in row)
    ref = load_workbook(reference, data_only=False)
    formula_count = sum(isinstance(c.value, str) and c.value.startswith("=") for ws in ref for row in ws for c in row)
    e = json.loads(expected_path.read_text())
    root_ok = (BASE / "tasks" / tid.split("/")[0] / "task.toml").is_file()
    instruction_ok = (task / "instruction.md").is_file()
    if spec["family"] == "D": instruction_ok = instruction_ok and (BASE / "tasks" / tid.split("/")[0] / "instruction.md").is_file()
    forbidden = [k for k in ("expected", "perturbations", "project_fcff") if k in public]
    return {"missing": missing, "public_formulas": formulas, "reference_formulas": formula_count,
        "public_forbidden": forbidden, "two_perturbations": len(e.get("perturbations", [])) >= 2,
        "root_task_toml": root_ok, "instruction": instruction_ok,
        "passed": not missing and not formulas and formula_count > 50 and not forbidden and len(e.get("perturbations", [])) >= 2 and root_ok and instruction_ok}


def d_process(tid, task):
    if not tid.startswith("D"): return None
    root = task.parent.parent
    number = int(task.name.split("-")[1])
    total = len(list((root / "steps").glob("step-*")))
    expected = json.loads((root / "tests" / "expected.json").read_text())
    history_ok = True
    for step in range(1, number + 1):
        source = load_workbook(root / "steps" / f"step-{step}" / "solution" / "reference.xlsx", data_only=False)
        original = load_workbook(root / "steps" / "step-1" / "environment" / "inputs.xlsx", data_only=False)
        if "History" not in source.sheetnames: history_ok = False
        else:
            for row in original["History"].iter_rows():
                for cell in row:
                    if source["History"][cell.coordinate].value != cell.value: history_ok = False
    snapshot_script = (task / "solution" / "snapshot.sh").read_text()
    event_ok = number == 1 or (task / "environment" / "event.json").is_file() and (task / "environment" / "event_inputs.xlsx").is_file() and (task / "solution" / "prior_state.xlsx").is_file()
    return {"step": number, "steps_in_task": total, "original_history_preserved": history_ok,
        "event_and_prior_state_present": event_ok, "snapshot_script_present": f"snapshots/step-{number}.xlsx" in snapshot_script,
        "final_truth_present": expected["final_step"] == total and len(expected["steps"]) == total,
        "passed": history_ok and event_ok and expected["final_step"] == total and len(expected["steps"]) == total and f"snapshots/step-{number}.xlsx" in snapshot_script}


def run_one(item, soffice, artifacts, quick=False):
    tid, task, reference = item
    result = {"task_id": tid, "path": str(task.relative_to(BASE)), "structure": structure(tid, task, reference), "status": "running"}
    work = artifacts / tid.replace("/", "_")
    work.mkdir(parents=True, exist_ok=True)
    try:
        step = int(task.name.split("-")[1]) if tid.startswith("D") else None
        snapshots = work / "snapshots"
        if step is not None:
            snapshots.mkdir(exist_ok=True)
            shutil.copy2(reference, snapshots / f"step-{step}.xlsx")
        r = grade(task, reference, work / "reference", soffice, variants=True, step=step, snapshots=snapshots)
        dump(work / "reference.json", r)
        result["reference"] = {"passed": r["passed"], "baseline": r.get("baseline"), "perturbations": r.get("perturbations"), "error": r.get("error")}
        if not quick:
            blank = work / "blank.xlsx"
            Workbook().save(blank)
            neg = grade(task, blank, work / "blank", soffice, variants=False)
            result["blank_negative"] = {"rejected": not neg["passed"]}
            static = work / "static.xlsx"
            static_negative(reference, static)
            neg = grade(task, static, work / "static", soffice, variants=False)
            result["static_negative"] = {"rejected": not neg["passed"], "baseline": neg.get("baseline")}
        result["d_process"] = d_process(tid, task)
        result["status"] = "rule_passed" if r["passed"] and result["structure"]["passed"] and (result["d_process"] is None or result["d_process"]["passed"]) else "failed"
        if not quick and (not result["blank_negative"]["rejected"] or not result["static_negative"]["rejected"]):
            result["status"] = "negative_audit_failed"
    except Exception as e:
        import traceback
        result["status"] = "error"
        result["error"] = repr(e)
        result["traceback"] = traceback.format_exc()
    return result


def coverage():
    specs = []
    for i in range(1, 17): specs.append(json.loads((BASE / "tasks" / f"BC{i:02d}" / "spec.json").read_text()))
    by_c = {}
    for s in specs: by_c.setdefault(s["c_structure"], []).append(s["task_id"])
    industries = []
    bases = set()
    for i in range(1, 9):
        s = json.loads((BASE / "tasks" / f"A{i:02d}" / "spec.json").read_text())
        industries.append({"task_id": s["task_id"], "industry": s["industry"], "drivers": s["industry_drivers"], "base_structure": s["base_structure"]})
        bases.add(s["base_structure"])
    dsteps = {}
    for i in range(1, 5):
        s = json.loads((BASE / "tasks" / f"D{i:02d}" / "spec.json").read_text())
        dsteps[s["task_id"]] = {"steps": len(s["steps"]), "events": [x["event_type"] for x in s["steps"]], "c_structure": s["c_structure"], "b_items": s["b_items"]}
    return {"bc_count": len(specs), "a_count": 8, "d_count": 4, "d_steps": sum(v["steps"] for v in dsteps.values()),
        "b_item_coverage": sorted({x for s in specs for x in s["b_items"]}), "c_coverage": by_c,
        "mixed_ltm": [s["task_id"] for s in specs if "mixed_ltm" in s["b_items"]],
        "dual_asset_pool": [s["task_id"] for s in specs if "dual_asset_pool" in s["b_items"]],
        "nwc_valuation_open": [s["task_id"] for s in specs if "nwc_valuation_open" in s["b_items"]],
        "nwc_fye_open": [s["task_id"] for s in specs if "nwc_fye_open" in s["b_items"]],
        "industries": industries, "base_structures": sorted(bases), "d": dsteps}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", nargs="*")
    p.add_argument("--all", action="store_true")
    p.add_argument("--soffice", default="soffice")
    p.add_argument("--artifacts", default=str(ROOT / "validation_artifacts"))
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--quick", action="store_true")
    a = p.parse_args()
    soffice = shutil.which(a.soffice) or "/opt/homebrew/bin/soffice"
    selected = tasks(a.tasks)
    artifacts = Path(a.artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        pending = {pool.submit(run_one, item, soffice, artifacts, a.quick): item[0] for item in selected}
        for future in as_completed(pending):
            r = future.result()
            results.append(r)
            print(r["status"].upper(), r["task_id"], r.get("error", ""), flush=True)
    results.sort(key=lambda r: r["task_id"])
    report = {"schema_version": "v3.0", "run_at": dt.datetime.now(dt.timezone.utc).isoformat(), "soffice": soffice,
        "coverage": coverage(), "summary": {"tasks": 28, "d_steps": coverage()["d_steps"], "validated_workbooks": len(results),
            "passed": sum(r["status"] == "rule_passed" for r in results), "failed": sum(r["status"] != "rule_passed" for r in results),
            "scope": "BC/A/D only; no E/W generation or validation"},
        "tasks": results}
    dump(ROOT / "validation.json", report)
    dump(ROOT / "RUN_META.json", {"seed": 391731, "generation": "python3 generate.py", "validation": "python3 validate.py --all",
        "python": sys.version, "platform": platform.platform(), "soffice": soffice,
        "code_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [ROOT / "generate.py", ROOT / "validate.py", *sorted((ROOT / "core").glob("*.py"))]}})
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__": main()
