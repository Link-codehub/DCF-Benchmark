#!/usr/bin/env python3
"""D task per-snapshot scoring using only each step's independent truth."""
import json
from pathlib import Path
from openpyxl import load_workbook
from map_rules import atom_results
import grader as core_grader


def values(workbook, expected):
    found, duplicates = core_grader.discover(workbook, expected)
    return found, duplicates


def compare(task, candidate, step):
    expected = json.loads((task / "tests" / "expected.json").read_text())["baseline"]
    recalculated = core_grader.recalc(candidate, Path("/tmp") / "unused") if False else None
    # Snapshot scoring is performed in a separate temporary directory by caller.
    return expected


def evaluate_steps(task, snapshot_dir, work, soffice):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    step_reports = []
    final_atoms = {}
    for step in sorted((task / "steps").glob("step-*"), key=lambda p: int(p.name.split("-")[1])):
        number = int(step.name.split("-")[1])
        expected = json.loads((step / "tests" / "expected.json").read_text())
        spec = json.loads((step / "tests" / "grader_spec.json").read_text())
        candidate = Path(snapshot_dir) / f"step-{number}.xlsx"
        if not candidate.is_file() and number == max(int(p.name.split("-")[1]) for p in (task / "steps").glob("step-*")):
            candidate = Path(snapshot_dir).parent / "output.xlsx"
        report = {"step": number, "candidate_exists": candidate.is_file(), "atoms": {}, "bad_keys": []}
        if candidate.is_file():
            recalculated = core_grader.recalc(candidate, work / f"step-{number}", soffice)
            wb = load_workbook(recalculated, data_only=True)
            found, duplicates = core_grader.discover(wb, expected["baseline"])
            bad = sorted({key for key, value in expected["baseline"].items() if key not in found or not core_grader.close(found.get(key), value)} | set(duplicates))
            raw = {"baseline": {"mismatches_all": [{"key": key} for key in bad], "nonformula_or_missing_all": [], "duplicates": [], "errors_all": [], "links_all": []}, "baseline_keys": list(expected["baseline"]), "expected": expected["baseline"]}
            report["bad_keys"] = bad
            for rid, fn in atom_results(step, spec, raw).items():
                result = fn()
                report["atoms"][rid] = result
                if number == max(int(p.name.split("-")[1]) for p in (task / "steps").glob("step-*")):
                    final_atoms[rid] = result
            history = load_workbook(step / "environment" / "inputs.xlsx", data_only=False)
            candidate_wb = load_workbook(candidate, data_only=False)
            history_ok = "History" in candidate_wb.sheetnames
            if history_ok:
                for row in history["History"].iter_rows():
                    for cell in row:
                        if candidate_wb["History"][cell.coordinate].value != cell.value:
                            history_ok = False
                            break
            report["history_preserved"] = history_ok
        step_reports.append(report)
    all_steps_ok = all(row["candidate_exists"] for row in step_reports)
    all_values_ok = all(row["candidate_exists"] and not row["bad_keys"] for row in step_reports)
    final = step_reports[-1] if step_reports else {"candidate_exists": False, "bad_keys": ["missing"], "atoms": {}}
    history_ok = all(row.get("history_preserved", False) for row in step_reports)
    atoms = dict(final["atoms"])
    atoms.update({
        "D-FINAL-VALUES": {"status": "pass" if final["candidate_exists"] and not final["bad_keys"] else "fail", "bad_keys": final["bad_keys"][:30]},
        "D-FINAL-LIVE": {"status": "not_executed", "note": "最终快照活公式与扰动由完整最终步评分补充"},
        "D-STEP-SNAPSHOT": {"status": "pass" if all_steps_ok else "fail", "steps": [{"step": r["step"], "present": r["candidate_exists"]} for r in step_reports]},
        "D-STEP-VALUES": {"status": "pass" if all_values_ok else "fail", "steps": [{"step": r["step"], "bad_keys": r["bad_keys"][:20]} for r in step_reports]},
        "D-STEP-SCOPE": {"status": "not_executed", "note": "需要独立结构评审确认每步修改范围；不以最终数值代替"},
        "01-HISTORY": {"status": "pass" if history_ok else "fail"},
        "08-OLD": {"status": "pass" if history_ok and all_steps_ok else "fail"},
    })
    return atoms, step_reports
