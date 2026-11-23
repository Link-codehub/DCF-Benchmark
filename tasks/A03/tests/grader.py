#!/usr/bin/env python3
"""A03/A04 deterministic semantic-key, dependency and full-sensitivity grader."""
import argparse
import json
import math
import re
import shutil
import subprocess
import traceback
from pathlib import Path
from openpyxl import load_workbook

TOLERANCE_REL = 2e-7
TOLERANCE_ABS = 1e-6


def close(actual, expected):
    return isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isfinite(actual) and abs(actual - expected) <= max(TOLERANCE_ABS, TOLERANCE_REL * abs(expected))


def recalc(source, target, soffice="soffice"):
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    dest = target / "model.xlsx"
    shutil.copy2(source, dest)
    profile = target / "profile"
    profile.mkdir(exist_ok=True)
    out = target / "recalc"
    out.mkdir(exist_ok=True)
    run = subprocess.run([soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--convert-to", "xlsx", "--outdir", str(out), str(dest)], capture_output=True, text=True, timeout=150)
    result = out / "model.xlsx"
    if run.returncode or not result.exists():
        raise RuntimeError(f"LibreOffice: {run.stdout[-400:]} {run.stderr[-400:]}")
    return result


def discover(wb, allowed, formulas=False):
    values, duplicates = {}, []
    for ws in wb.worksheets:
        if not (ws.title.startswith("Results") or ws.title == "Outputs"):
            continue
        for row in ws.iter_rows():
            for cell in row:
                key = cell.value.strip() if isinstance(cell.value, str) else None
                if key not in allowed:
                    continue
                right = ws.cell(cell.row, cell.column + 1).value
                good = isinstance(right, str) and right.startswith("=") if formulas else isinstance(right, (int, float)) and not isinstance(right, bool)
                if good:
                    if key in values:
                        duplicates.append(key)
                    values[key] = right if formulas else float(right)
    return values, duplicates


def perturb(source, target, changes):
    wb = load_workbook(source, data_only=False)
    ws = wb["Inputs"]
    for path, value in changes.items():
        group, field, *rest = path.split(".")
        semantic = path
        vector_index = None
        if group in ("assumptions", "bridge"):
            semantic = path
            if rest and rest[-1].isdigit():
                semantic, vector_index = path.rsplit(".", 1)
                vector_index = int(vector_index)
        else:
            leaf = rest[-1]
            if leaf.isdigit():
                semantic, vector_index = path.rsplit(".", 1)
                vector_index = int(vector_index)
        matches = [row[0].row for row in ws.iter_rows() if row[0].value == semantic]
        if len(matches) != 1:
            raise ValueError(f"missing public input {semantic}")
        ws.cell(matches[0], 3 + (vector_index or 0), value)
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.calculation.calcMode = "auto"
    wb.save(target)


def formula_map(wb):
    result = {}
    for ws in wb:
        for row in ws.iter_rows():
            if row[0].value:
                result[(ws.title, str(row[0].value))] = [cell.value for cell in row[1:] if isinstance(cell.value, str) and cell.value.startswith("=")]
    return result


def a03_dependencies(formulas):
    all_text = "\n".join(v for values in formulas.values() for v in values)
    main = {key: "\n".join(value) for (sheet, key), value in formulas.items() if sheet == "Model"}
    missing_bom = [f"products.{p}.bom_{m}" for p in ("alpha", "beta") for m in ("alloy", "resin", "steel") if f"products.{p}.bom_{m}" not in main.get(f"{p}_{m}_consumption", "")]
    bad_yield = [p for p in ("alpha", "beta") if ".yield" not in main.get(f"{p}_good_volume", "")]
    cogs = main.get("cogs", "")
    purchase_cogs = "material_cogs" not in cogs or "conversion_cogs" not in cogs
    revenue_ratio = bool(re.search(r"(?:revenue|full_revenue).{0,35}(?:cogs_ratio|material_cost_pct)|(?:cogs_ratio|material_cost_pct).{0,35}(?:revenue|full_revenue)", all_text))
    checks = {
        "bom_unit_drivers": not missing_bom,
        "yield_once_in_good_volume": not bad_yield,
        "cogs_is_not_purchases": not purchase_cogs,
        "no_revenue_cost_ratio_substitute": not revenue_ratio,
        "sensitivity_full_grid": all(f"Sens_R{r}_C{c}" in {sheet for sheet, _ in formulas} for r in range(1, 6) for c in range(1, 6)),
        "sensitivity_formula_drivers": all(".sensitivity_" in "\n".join(v for (s, _), values in formulas.items() if s == f"Sens_R{r}_C{c}" for v in values) for r in range(1, 6) for c in range(1, 6)),
    }
    return checks, {"missing_bom": missing_bom, "bad_yield": bad_yield, "purchase_cogs": purchase_cogs}


def a04_dependencies(formulas):
    main = {key: "\n".join(value) for (sheet, key), value in formulas.items() if sheet == "Model"}
    all_text = "\n".join(v for values in formulas.values() for v in values)
    committed = main.get("nova_commit_rd", "")
    prelaunch = [f"p{i}_revenue_p1" in main for i in (1, 2)]
    checks = {
        "prelaunch_revenue_formula": all("IF(" in main.get(f"{p}_revenue", "") for p in ("nova", "astra")),
        "commit_rd_not_pos": "success_probability" not in committed and ".pos" not in committed,
        "commercial_not_pos": "success_probability" not in main.get("marketed_revenue", ""),
        "patient_driver": all("diagnosed" in main.get(f"{p}_treated_patients", "") or "eligible" in main.get(f"{p}_treated_patients", "") for p in ("marketed", "nova", "astra")),
        "nol_80pct_cap": all(".8" in main.get(f"{p}_nol_used", "") for p in ("marketed", "nova", "astra")),
        "pipeline_no_perpetuity": not any(("pipeline_terminal" in key or f"{p}_terminal_value" in key) for (_, key) in formulas),
        "sensitivity_full_grid": all(f"Sens_R{r}_C{c}" in {sheet for sheet, _ in formulas} for r in range(1, 6) for c in range(1, 6)),
        "sensitivity_formula_drivers": all(".sensitivity_" in "\n".join(v for (s, _), values in formulas.items() if s == f"Sens_R{r}_C{c}" for v in values) for r in range(1, 6) for c in range(1, 6)),
    }
    return checks, {"commit_rd_not_pos": "success_probability" not in committed, "commercial_not_pos": "success_probability" not in main.get("marketed_revenue", "")}


def grade(task, candidate, work, soffice="soffice", variants=True):
    task, work = Path(task), Path(work)
    tests_dir = task if (task / "expected.json").is_file() else task / "tests"
    expected = json.loads((tests_dir / "expected.json").read_text())
    spec = json.loads((task / "tests" / "grader_spec.json").read_text())
    report = {"task_id": spec["task_id"], "baseline": {}, "perturbations": [], "dependency_checks": {}, "tolerance": {"absolute": TOLERANCE_ABS, "relative": TOLERANCE_REL}, "reward": 0.0, "passed": False}
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
        dependency, detail = (a03_dependencies if spec["task_id"] == "A03" else a04_dependencies)(formula_map(fwb))
        report["dependency_checks"] = {"passed": all(dependency.values()), "checks": dependency, "detail": detail}
        sensitivity_keys = [k for k in baseline if k.startswith("sensitivity_")]
        sensitivity_bad = [m["key"] for m in mismatches if m["key"] in sensitivity_keys]
        center = "sensitivity_r3_c3"
        report["baseline"] = {"passed": not mismatches and not static and not dup and not fdup and not errors and not links and report["dependency_checks"]["passed"],
            "mismatches": mismatches[:50], "nonformula_or_missing": static[:50], "duplicates": dup + fdup, "errors": errors[:20], "links": links[:20], "checked": len(baseline),
            "sensitivity": {"grid_checked": len(sensitivity_keys), "grid_passed": not sensitivity_bad, "center_key": center, "center_passed": close(values.get(center), baseline["enterprise_value"] if spec["task_id"] == "A03" else baseline["risk_adjusted_enterprise_value"]), "center_actual": values.get(center), "center_expected": baseline.get(center)}}
        if variants:
            for i, variant in enumerate(expected["perturbations"], 1):
                source = work / f"variant_{i}.xlsx"
                perturb(candidate, source, variant["input_changes"])
                recalced = recalc(source, work / f"variant_{i}", soffice)
                values, dup = discover(load_workbook(recalced, data_only=True), variant["expected"])
                mismatches = [{"key": k, "actual": values.get(k), "expected": v} for k, v in variant["expected"].items() if not close(values.get(k), v)]
                report["perturbations"].append({"id": i, "label": variant.get("label"), "passed": not mismatches and not dup, "mismatches": mismatches[:30], "checked": len(variant["expected"])})
        variants_pass = all(p["passed"] for p in report["perturbations"])
        report["passed"] = report["baseline"]["passed"] and variants_pass
        report["reward"] = float(report["passed"])
        report["llm_agent_review"] = {"status": "pending", "included_in_rule_reward": False, "items": ["memo 的行业因果链、可读性及局限披露"]}
    except Exception as error:
        report["error"] = repr(error)
        report["traceback"] = traceback.format_exc()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--report")
    parser.add_argument("--soffice", default="soffice")
    parser.add_argument("--no-variants", action="store_true")
    args = parser.parse_args()
    result = grade(args.task_dir, args.candidate, args.work_dir, args.soffice, not args.no_variants)
    if args.report:
        Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result.get(k) for k in ("task_id", "passed", "reward", "error")}, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
