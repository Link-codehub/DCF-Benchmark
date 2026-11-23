#!/usr/bin/env python3
"""A09 semantic-key, live-formula, full-sensitivity and BOM dependency grader."""
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
PRODUCTS = ("alpha", "beta")
MATERIALS = ("alloy", "resin", "steel")


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
        parts = path.split(".")
        semantic = path
        vector_index = None
        if parts[-1].isdigit():
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
        target_sheet = (quoted or plain or sheet).strip("'")
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
    checks = {}
    details = {}
    missing_bom = []
    for sheet in ("Model",):
        for p in PRODUCTS:
            for m in MATERIALS:
                expression = normalized(formulas, sheet, f"{p}_{m}_consumption")
                if f"products.{p}.bom_{m}" not in expression or f"{p}_input" not in expression:
                    missing_bom.append(f"{sheet}:{p}_{m}_consumption")
        material_cogs = normalized(formulas, sheet, "material_cogs_full")
        cogs = normalized(formulas, sheet, "cogs_full")
        for p in PRODUCTS:
            for m in MATERIALS:
                if f"{p}_{m}_consumption_cost" not in material_cogs:
                    missing_bom.append(f"material_cogs_full:{p}_{m}")
    checks["bom_not_revenue_ratio"] = not missing_bom and not re.search(r"full_revenue|revenue|material_cost_pct|cogs_ratio", material_cogs)
    checks["cogs_excludes_purchases"] = "purchase" not in cogs and "purchase" not in material_cogs and "material_cogs_full" in cogs and "conversion_cogs_full" in cogs
    yield_errors = []
    for sheet in ("Model",):
        for p in PRODUCTS:
            good = normalized(formulas, sheet, f"{p}_good_volume")
            sales = normalized(formulas, sheet, f"{p}_sales")
            if f"{p}_input" not in good or f"{p}_capped_yield" not in good:
                yield_errors.append(f"{p}_good_volume")
            if f"{p}_good_volume" not in sales or "yield" in sales:
                yield_errors.append(f"{p}_sales")
    checks["yield_applied_once"] = not yield_errors
    raw_errors = []
    for sheet in ("Model",):
        for m in MATERIALS:
            raw = normalized(formulas, sheet, f"raw_{m}_close")
            if f"{m}_consumption_cost" not in raw or "assumptions.raw_days" not in raw or "revenue" in raw:
                raw_errors.append(f"raw_{m}_close")
        wip = normalized(formulas, sheet, "wip_close")
        fg = normalized(formulas, sheet, "finished_goods_close")
        if not all(x in wip for x in ("material_consumption_cost", "conversion_full", "assumptions.fixed_manufacturing_cost", "assumptions.wip_days")) or "revenue" in wip:
            raw_errors.append("wip_close")
        if "cogs_full" not in fg or "assumptions.fg_days" not in fg or "revenue" in fg:
            raw_errors.append("finished_goods_close")
        nwc = normalized(formulas, sheet, "nwc")
        if not all(x in nwc for x in ("accounts_receivable", "accounts_payable", "wip_close", "finished_goods_close", *(f"raw_{m}_close" for m in MATERIALS))):
            raw_errors.append("nwc")
    checks["three_inventory_pools_separate"] = not raw_errors
    missing_sheets = [f"Sens_R{r}_C{c}" for r in range(1, 6) for c in range(1, 6) if f"Sens_R{r}_C{c}" not in wb.sheetnames]
    checks["sensitivity_25_independent_sheets"] = not missing_sheets
    sensitivity_errors = []
    for r in range(1, 6):
        for c in range(1, 6):
            sheet = f"Sens_R{r}_C{c}"
            alloy = normalized(formulas, sheet, "alpha_alloy_consumption_cost")
            beta = normalized(formulas, sheet, "beta_yield")
            alloy_cells = {f"${chr(67 + c - 1)}${row[0].row}" for row in wb["Inputs"].iter_rows() if row[0].value == "assumptions.sensitivity_alloy_multiplier"}
            yield_cells = {f"${chr(67 + r - 1)}${row[0].row}" for row in wb["Inputs"].iter_rows() if row[0].value == "assumptions.sensitivity_yield_multiplier"}
            raw_alloy = "".join(formulas.get((sheet, "alpha_alloy_consumption_cost"), []))
            raw_beta = "".join(formulas.get((sheet, "beta_yield"), []))
            if "assumptions.sensitivity_alloy_multiplier" not in alloy or not any(cell in raw_alloy for cell in alloy_cells):
                sensitivity_errors.append(f"{sheet}:alloy_multiplier")
            if "assumptions.sensitivity_yield_multiplier" not in beta or not any(cell in raw_beta for cell in yield_cells) or "min(0.999" not in normalized(formulas, sheet, "beta_capped_yield"):
                sensitivity_errors.append(f"{sheet}:yield_multiplier_or_cap")
            for key in ("alpha_input", "beta_input", "material_cogs_full", "cogs_full", "wip_close", "finished_goods_close", "nwc", "capex", "da", "cash_tax", "fcff"):
                if len(formulas.get((sheet, key), [])) != 5:
                    sensitivity_errors.append(f"{sheet}:{key}_not_full_horizon")
            if not formulas.get((sheet, "enterprise_value")):
                sensitivity_errors.append(f"{sheet}:enterprise_value_not_formula")
            material_cogs = normalized(formulas, sheet, "material_cogs_full")
            if "full_revenue" in material_cogs or not all(f"{p}_{m}_consumption_cost" in material_cogs for p in PRODUCTS for m in MATERIALS):
                sensitivity_errors.append(f"{sheet}:bom")
    checks["sensitivity_full_recalculation"] = not sensitivity_errors
    details.update(missing_bom=missing_bom, yield_errors=yield_errors, inventory_errors=raw_errors,
                   missing_sensitivity_sheets=missing_sheets, sensitivity_errors=sensitivity_errors)
    return checks, details


def max_relative_error(values, expected):
    worst = 0.0
    for key, target in expected.items():
        actual = values.get(key)
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return None
        denominator = max(abs(target), 1e-12)
        worst = max(worst, abs(actual - target) / denominator)
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
        report["dependency_checks"] = {"passed": all(dependency.values()), "checks": dependency, "detail": detail}
        sensitivity_keys = [k for k in baseline if k.startswith("sensitivity_")]
        sensitivity_bad = [m["key"] for m in mismatches if m["key"] in sensitivity_keys]
        center = "sensitivity_r3_c3"
        report["baseline"] = {
            "passed": not mismatches and not static and not dup and not fdup and not errors and not links and report["dependency_checks"]["passed"],
            "mismatches": mismatches[:50], "mismatches_all": mismatches, "nonformula_or_missing": static[:50], "nonformula_or_missing_all": static, "duplicates": dup + fdup,
            "errors": errors[:20], "errors_all": errors, "links": links[:20], "links_all": links, "checked": len(baseline),
            "max_relative_error": max_relative_error(values, baseline),
            "sensitivity": {"grid_checked": len(sensitivity_keys), "grid_passed": not sensitivity_bad,
                            "center_key": center, "center_passed": close(values.get(center), baseline["enterprise_value"]),
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
                                                "mismatches": mismatches[:50], "mismatches_all": mismatches, "checked": len(variant["expected"]),
                                                "max_relative_error": max_relative_error(values, variant["expected"])})
        report["passed"] = report["baseline"]["passed"] and all(p["passed"] for p in report["perturbations"])
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
