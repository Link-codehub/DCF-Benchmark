#!/usr/bin/env python3
"""Deterministic v3 semantic-key, live-formula, recalculation and perturbation grader."""
import argparse
import datetime as dt
import json
import math
import shutil
import subprocess
import traceback
from pathlib import Path
from openpyxl import load_workbook


def close(a, b):
    return isinstance(a, (int, float)) and not isinstance(a, bool) and math.isfinite(a) and abs(a - b) <= max(1e-6, 2e-7 * abs(b))


def recalc(source, target, soffice="soffice"):
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    dest = target / "model.xlsx"
    shutil.copy2(source, dest)
    profile = target / "profile"
    profile.mkdir(exist_ok=True)
    out = target / "recalc"
    out.mkdir(exist_ok=True)
    run = subprocess.run([soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--convert-to", "xlsx", "--outdir", str(out), str(dest)], capture_output=True, text=True, timeout=90)
    result = out / "model.xlsx"
    if run.returncode or not result.exists():
        raise RuntimeError(f"LibreOffice: {run.stdout[-300:]} {run.stderr[-300:]}")
    return result


def discover(wb, allowed, formulas=False):
    values, duplicates = {}, []
    for ws in wb.worksheets:
        if not (ws.title.startswith("Results") or ws.title == "Outputs"): continue
        for row in ws.iter_rows():
            for cell in row:
                key = cell.value.strip() if isinstance(cell.value, str) else None
                if key not in allowed: continue
                right = ws.cell(cell.row, cell.column + 1).value
                good = isinstance(right, str) and right.startswith("=") if formulas else isinstance(right, (int, float)) and not isinstance(right, bool)
                if good:
                    if key in values: duplicates.append(key)
                    values[key] = right if formulas else float(right)
    return values, duplicates


def perturb(source, target, changes):
    wb = load_workbook(source, data_only=False)
    ws = wb["Inputs"]
    for key, value in changes.items():
        group, field, *index = key.split(".")
        semantic = key.rsplit(".", 1)[0] if index and index[-1].isdigit() else key
        vector_index = int(index[-1]) if index and index[-1].isdigit() else None
        matches = [row[0].row for row in ws.iter_rows() if row[0].value == semantic]
        if len(matches) != 1: raise ValueError(f"missing public input {semantic}")
        ws.cell(matches[0], 3 + (vector_index if vector_index is not None else 0), value)
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.calculation.calcMode = "auto"
    wb.save(target)


def d_step_checks(task, fwb, spec, step, snapshots):
    original = load_workbook(task / "environment" / "inputs.xlsx", data_only=False)
    history_ok = "History" in fwb.sheetnames
    mismatches = []
    if history_ok:
        for row in original["History"].iter_rows():
            for cell in row:
                if fwb["History"][cell.coordinate].value != cell.value:
                    mismatches.append(cell.coordinate)
                    history_ok = False
    snapshot = snapshots / f"step-{step}.xlsx"
    snapshot_ok = snapshot.is_file()
    formula_ok = True
    if snapshot_ok:
        swb = load_workbook(snapshot, data_only=False)
        formula_ok = sum(isinstance(c.value, str) and c.value.startswith("=") for ws in swb for row in ws for c in row) > 50
    return {"history_preserved": history_ok, "history_mismatches": mismatches[:10],
        "snapshot": str(snapshot), "snapshot_present": snapshot_ok, "snapshot_formulas": formula_ok,
        "passed": history_ok and snapshot_ok and formula_ok}


def grade(task, candidate, work, soffice="soffice", variants=True, step=None, snapshots=None):
    task, work = Path(task), Path(work)
    expected = json.loads((task / "tests" / "expected.json").read_text())
    report = {"task_id": task.name, "baseline": {}, "perturbations": [], "passed": False}
    try:
        recalced = recalc(candidate, work / "base", soffice)
        vwb = load_workbook(recalced, data_only=True)
        fwb = load_workbook(candidate, data_only=False)
        baseline = expected["baseline"]
        values, dup = discover(vwb, baseline)
        formulas, fdup = discover(fwb, baseline, True)
        mismatches = [{"key": k, "actual": values.get(k), "expected": v} for k, v in baseline.items() if not close(values.get(k), v)]
        static = [k for k in baseline if k not in formulas]
        errors = [f"{ws.title}!{c.coordinate}" for ws in vwb for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("#")]
        links = [f"{ws.title}!{c.coordinate}" for ws in fwb for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=") and ("[" in c.value or "http" in c.value)]
        report["baseline"] = {"passed": not mismatches and not static and not dup and not fdup and not errors and not links,
            "mismatches": mismatches[:20], "mismatches_all": mismatches, "nonformula_or_missing": static[:20], "nonformula_or_missing_all": static, "duplicates": dup + fdup, "errors": errors[:10], "errors_all": errors, "links": links[:10], "links_all": links, "checked": len(baseline)}
        if variants:
            for i, variant in enumerate(expected["perturbations"], 1):
                source = work / f"variant_{i}.xlsx"
                perturb(candidate, source, variant["input_changes"])
                recalced = recalc(source, work / f"variant_{i}", soffice)
                values, dup = discover(load_workbook(recalced, data_only=True), variant["expected"])
                mismatches = [{"key": k, "actual": values.get(k), "expected": v} for k, v in variant["expected"].items() if not close(values.get(k), v)]
                report["perturbations"].append({"id": i, "passed": not mismatches and not dup, "mismatches": mismatches[:20], "checked": len(variant["expected"])})
        spec = json.loads((task / "tests" / "grader_spec.json").read_text())
        if step is not None and spec.get("family") == "D":
            directory = Path(snapshots) if snapshots else Path("/app/snapshots")
            report["d_step"] = d_step_checks(task, fwb, spec, step, directory)
        report["passed"] = report["baseline"]["passed"] and all(p["passed"] for p in report["perturbations"]) and report.get("d_step", {}).get("passed", True)
    except Exception as error:
        report["error"] = repr(error)
        report["traceback"] = traceback.format_exc()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--task-dir", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--work-dir", required=True)
    p.add_argument("--report")
    p.add_argument("--soffice", default="soffice")
    p.add_argument("--no-variants", action="store_true")
    p.add_argument("--step", type=int)
    p.add_argument("--snapshots")
    a = p.parse_args()
    result = grade(a.task_dir, a.candidate, a.work_dir, a.soffice, not a.no_variants, a.step, a.snapshots)
    if a.report: Path(a.report).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result.get(k) for k in ("task_id", "passed", "error")}, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__": main()
