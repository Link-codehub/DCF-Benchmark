#!/usr/bin/env python3
"""A10 semantic-key, live-formula, full-sensitivity and pipeline dependency grader."""
import argparse
import json
import math
import re
import shutil
import subprocess
import traceback
from pathlib import Path
from openpyxl import load_workbook

TOLERANCE_REL = 1e-6
TOLERANCE_ABS = 1e-8
PRODUCTS = ("commercial", "lead", "next")
SHEETS = ("Model",) + tuple(f"Sens_R{r}_C{c}" for r in range(1, 6) for c in range(1, 6))


def close(actual, expected):
    return (isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isfinite(actual)
            and abs(actual - expected) <= max(TOLERANCE_ABS, TOLERANCE_REL * abs(expected)))


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
        semantic, vector_index = path, None
        if path.split(".")[-1].isdigit():
            semantic, index = path.rsplit(".", 1)
            vector_index = int(index)
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


def normalized(formulas, sheet, key):
    expressions = formulas.get((sheet, key), [])
    if not formulas:
        return ""
    wb = formulas["workbook"]
    input_rows = {row[0].value: row[0].row for row in wb["Inputs"].iter_rows() if row[0].value}
    locations = {}
    for ws in wb:
        for row in ws.iter_rows():
            if row[0].value:
                for cell in row[1:]:
                    locations[(ws.title, cell.coordinate)] = str(row[0].value)
    def replace(match):
        quoted, plain, coordinate = match.groups()
        target_sheet = (quoted or plain).strip("'") if (quoted or plain) else sheet
        if target_sheet == "Inputs":
            row = int(re.search(r"\d+", coordinate).group())
            semantic = next((name for name, source_row in input_rows.items() if source_row == row), coordinate)
        else:
            semantic = locations.get((target_sheet, coordinate.replace("$", "")), coordinate)
        return f" {semantic} "
    reference = r"(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_]*))?!?(\$?[A-Z]{1,3}\$?\d+)"
    resolved = [re.sub(reference, replace, expression) for expression in expressions]
    return re.sub(r"\s+", "", "\n".join(resolved)).lower()


def dependency_checks(wb):
    formulas = formula_map(wb)
    formulas["workbook"] = wb
    checks, details = {}, {}
    revenue_errors, pos_errors, wacc_errors, terminal_errors, nol_errors, sensitivity_errors = [], [], [], [], [], []
    for sheet in SHEETS:
        for name in ("lead", "next"):
            revenue = normalized(formulas, sheet, f"{name}_revenue")
            treated = normalized(formulas, sheet, f"{name}_treated_patients")
            penetration = normalized(formulas, sheet, f"{name}_penetration")
            annual = normalized(formulas, sheet, f"{name}_annual_revenue")
            patients = normalized(formulas, sheet, f"{name}_patients")
            doses = normalized(formulas, sheet, f"{name}_doses")
            if (f"{name}_annual_revenue" not in revenue or f"products.{name}.patient_base" not in patients
                    or f"products.{name}.net_price_per_dose" not in annual or f"{name}_relative_launch" not in penetration
                    or f"{name}_penetration" not in treated or f"products.{name}.adherence" not in doses
                    or f"{name}_patients" not in treated or f"{name}_doses" not in annual):
                revenue_errors.append(f"{sheet}:{name}_funnel")
            risked = normalized(formulas, sheet, f"{name}_risked_fcff_before_tax")
            if f"{name}_pos" not in risked or f"{name}_operating_fcff_before_tax" not in risked:
                pos_errors.append(f"{sheet}:{name}_operating_pos")
            committed = normalized(formulas, sheet, f"{name}_committed_rd")
            if f"products.{name}.committed_rd_amounts" not in committed or f"{name}_pos" in committed or "pos" in committed:
                pos_errors.append(f"{sheet}:{name}_committed_pos")
            if any(f"{name}_pos" in normalized(formulas, sheet, key) for key in (f"{name}_committed_rd", f"{name}_prelaunch_selling")):
                pos_errors.append(f"{sheet}:{name}_prelaunch_pos")
            terminal = normalized(formulas, sheet, f"risked_{name}_pipeline_pv")
            if not terminal or "gordon" in terminal or "assumptions.g" in terminal or "commercial_terminal_value" in terminal:
                terminal_errors.append(f"{sheet}:{name}_finite_pv")
            if len(formulas.get((sheet, f"{name}_risked_fcff_before_tax"), [])) != 8 or len(formulas.get((sheet, f"{name}_risked_ebit"), [])) != 8:
                terminal_errors.append(f"{sheet}:{name}_horizon")
        commercial = normalized(formulas, sheet, "commercial_fcff_before_tax")
        if "pos" in commercial:
            pos_errors.append(f"{sheet}:commercial_pos")
        for key in ("wacc", "risked_enterprise_value"):
            if "pos" in normalized(formulas, sheet, key):
                wacc_errors.append(f"{sheet}:{key}")
        for mode in ("risked", "unrisked"):
            used = normalized(formulas, sheet, f"{mode}_nol_used")
            if "min" not in used or f"{mode}_nol_open" not in used or "assumptions.nol_use_limit" not in used or f"{mode}_ebt" not in used:
                nol_errors.append(f"{sheet}:{mode}_nol_limit")
        if len(formulas.get((sheet, "risked_enterprise_value"), [])) != 1:
            sensitivity_errors.append(f"{sheet}:enterprise_value")
    for r in range(1, 6):
        for c in range(1, 6):
            sheet = f"Sens_R{r}_C{c}"
            if sheet not in wb.sheetnames:
                sensitivity_errors.append(f"{sheet}:missing")
                continue
            launch = normalized(formulas, sheet, "lead_launch")
            pos = normalized(formulas, sheet, "lead_pos")
            if "assumptions.sensitivity_lead_delay" not in launch or "products.lead.launch_period" not in launch:
                sensitivity_errors.append(f"{sheet}:delay")
            if "assumptions.sensitivity_pos_multiplier" not in pos or "min(1" not in pos:
                sensitivity_errors.append(f"{sheet}:pos_cap")
            for key in ("lead_revenue", "lead_committed_rd", "lead_prelaunch_selling", "risked_nol_used", "unrisked_nol_used", "risked_enterprise_value"):
                if not formulas.get((sheet, key)):
                    sensitivity_errors.append(f"{sheet}:{key}")
    checks.update(pipeline_funnel_and_prelaunch_revenue=not revenue_errors,
                  pos_only_pipeline_operating=not pos_errors,
                  pos_not_in_wacc=not wacc_errors,
                  finite_pipeline_no_gordon=not terminal_errors,
                  nol_80_percent_limit=not nol_errors,
                  sensitivity_25_full_recalculation=not sensitivity_errors)
    details.update(revenue_errors=revenue_errors, pos_errors=pos_errors, wacc_errors=wacc_errors,
                   terminal_errors=terminal_errors, nol_errors=nol_errors, sensitivity_errors=sensitivity_errors)
    return checks, details


def invariant_checks(wb, spec):
    failures = []
    for sheet in SHEETS:
        ws = wb[sheet]
        rows = {row[0].value: row[0].row for row in ws.iter_rows() if row[0].value}
        for name in ("lead", "next"):
            scenario_launch = ws.cell(rows[f"{name}_launch"], 2).value
            for i in range(int(scenario_launch) - 1):
                value = ws.cell(rows[f"{name}_revenue"], 2 + i).value
                if not isinstance(value, (int, float)) or abs(value) > 1e-8:
                    failures.append(f"{sheet}:{name}_revenue_p{i + 1}")
            for mode in ("risked", "unrisked"):
                for i in range(8):
                    used = ws.cell(rows[f"{mode}_nol_used"], 2 + i).value
                    ebt = ws.cell(rows[f"{mode}_ebt"], 2 + i).value
                    opening = ws.cell(rows[f"{mode}_nol_open"], 2 + i).value
                    close_value = ws.cell(rows[f"{mode}_nol_close"], 2 + i).value
                    if not all(isinstance(x, (int, float)) for x in (used, ebt, opening, close_value)) or used < -1e-8 or used > opening + 1e-8 or used > max(0, ebt) * spec["assumptions"]["nol_use_limit"] + 1e-7 or close_value < -1e-8:
                        failures.append(f"{sheet}:{mode}_nol_p{i + 1}")
    return failures


def max_relative_error(values, expected):
    worst = 0.0
    for key, target in expected.items():
        actual = values.get(key)
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return None
        worst = max(worst, abs(actual - target) / max(abs(target), 1.0))
    return worst


def grade(task, candidate, work, soffice="soffice", variants=True):
    task, work = Path(task), Path(work)
    tests_dir = task if (task / "expected.json").is_file() else task / "tests"
    expected = json.loads((tests_dir / "expected.json").read_text())
    spec = json.loads((tests_dir / "grader_spec.json").read_text())
    report = {"task_id": spec["task_id"], "baseline": {}, "perturbations": [], "dependency_checks": {},
              "tolerance": {"absolute": TOLERANCE_ABS, "relative": TOLERANCE_REL}, "reward": 0.0, "passed": False}
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
        dependency, detail = dependency_checks(fwb)
        invariant_failures = invariant_checks(vwb, spec)
        dependency["recalculated_business_invariants"] = not invariant_failures
        detail["invariant_failures"] = invariant_failures
        report["dependency_checks"] = {"passed": all(dependency.values()), "checks": dependency, "detail": detail}
        sensitivity_bad = [m["key"] for m in mismatches if m["key"].startswith("sensitivity_")]
        center = "sensitivity_r3_c3"
        report["baseline"] = {
            "passed": not mismatches and not static and not dup and not fdup and not errors and not links and report["dependency_checks"]["passed"],
            "mismatches": mismatches[:50], "nonformula_or_missing": static[:50], "duplicates": dup + fdup,
            "errors": errors[:20], "links": links[:20], "checked": len(baseline),
            "max_relative_error": max_relative_error(values, baseline),
            "sensitivity": {"grid_checked": len([k for k in baseline if k.startswith("sensitivity_")]), "grid_passed": not sensitivity_bad,
                            "center_key": center, "center_passed": close(values.get(center), baseline["risk_adjusted_enterprise_value"]),
                            "center_actual": values.get(center), "center_expected": baseline.get(center)},
        }
        if variants:
            for i, variant in enumerate(expected["perturbations"], 1):
                source = work / f"variant_{i}.xlsx"
                perturb(candidate, source, variant["input_changes"])
                recalced = recalc(source, work / f"variant_{i}", soffice)
                values, dup = discover(load_workbook(recalced, data_only=True), variant["expected"])
                mismatches = [{"key": k, "actual": values.get(k), "expected": v} for k, v in variant["expected"].items() if not close(values.get(k), v)]
                report["perturbations"].append({"id": i, "label": variant.get("label"), "passed": not mismatches and not dup,
                                                "mismatches": mismatches[:50], "checked": len(variant["expected"]),
                                                "max_relative_error": max_relative_error(values, variant["expected"])})
        report["passed"] = report["baseline"]["passed"] and all(p["passed"] for p in report["perturbations"])
        report["reward"] = float(report["passed"])
        report["llm_agent_review"] = {"status": "pending", "included_in_rule_reward": False, "items": ["memo 的管线因果链、可读性及局限披露"]}
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
