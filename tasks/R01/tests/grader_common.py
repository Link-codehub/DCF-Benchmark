#!/usr/bin/env python3
"""Deterministic, LibreOffice-backed workbook grader used locally and in Harbor."""
from __future__ import annotations

import copy
import datetime as dt
import json
import math
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from openpyxl import Workbook, load_workbook


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_path(data, path):
    for part in path.split("."):
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data


def recalculate(source, work_dir, soffice):
    """Open and save a workbook with LibreOffice, returning its recalculated copy."""
    source = Path(source).resolve()
    work = Path(work_dir)
    incoming = work / "incoming"
    outgoing = work / "outgoing"
    profile = work / "profile"
    incoming.mkdir(parents=True)
    outgoing.mkdir()
    staged = incoming / "workbook.xlsx"
    staged.write_bytes(source.read_bytes())
    command = [soffice, f"-env:UserInstallation={profile.resolve().as_uri()}", "--headless",
               "--convert-to", "xlsx", "--outdir", str(outgoing), str(staged)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=150)
    calculated = outgoing / "workbook.xlsx"
    if result.returncode != 0 or not calculated.exists():
        raise RuntimeError(f"LibreOffice failed ({result.returncode}): {result.stdout}\n{result.stderr}")
    return calculated


def formula_dependencies(workbook, sheet, cell, seen=None):
    seen = set() if seen is None else seen
    key = (sheet, cell)
    if key in seen:
        return set()
    seen.add(key)
    value = workbook[sheet][cell].value
    if not isinstance(value, str) or not value.startswith("="):
        return set()
    result = set()
    pattern = r"(?:(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_]*))!)?\$?([A-Z]{1,3})\$?([0-9]+)"
    for match in re.finditer(pattern, value):
        other_sheet = match.group(1) or match.group(2) or sheet
        other_cell = match.group(3) + match.group(4)
        if other_sheet not in workbook.sheetnames:
            continue
        result.add((other_sheet, other_cell))
        result.update(formula_dependencies(workbook, other_sheet, other_cell, seen))
    return result


def numeric_equal(actual, expected):
    if isinstance(actual, dt.datetime):
        actual = actual.date()
    if isinstance(actual, dt.date) or isinstance(expected, str) or not isinstance(actual, (int, float)):
        return False
    return math.isfinite(float(actual)) and abs(float(actual) - float(expected)) <= max(0.000001, 0.00000002 * abs(float(expected)))


def update_inputs(path, original, perturbed, destination):
    """Find semantic keys, not fixed input addresses, and apply a hidden fact pack."""
    workbook = load_workbook(path)
    if "Inputs" not in workbook.sheetnames:
        raise ValueError("Inputs sheet is absent; hidden facts cannot be applied")
    ws = workbook["Inputs"]
    changes = {key: perturbed[key] for key in ("valuation_date", "fiscal_year_end")}
    changes["asset_count"] = original["assets"]
    for group in ("opening", "wacc", "terminal", "bridge"):
        for key, value in original[group].items():
            if group == "opening" or (key in perturbed[group] and key != "type"):
                changes[f"{group}.{key}"] = perturbed[group][key]
    for key in ("ppe_depreciation_rate", "intangible_amortization_rate"):
        changes[key] = perturbed[key]
    vector_keys = ["cogs_ratio", "other_opex_ratio", "tax_rate", "ar_days", "inventory_days",
                   "ap_days", "other_nwc_ratio", "capex", "intangible_additions"]
    vector_keys += ["avg_stores", "sales_per_store"] if original["scene"] == "stores" else ["volume", "price"]
    for key in vector_keys:
        source = perturbed[key] if key in perturbed else perturbed["forecast"]
        for j in range(4):
            changes[f"{key}.{j}"] = source[j][key] if key not in perturbed else source[j]
    for j in range(4):
        changes[f"fy_end_{j}"] = perturbed["next_fiscal_year_ends"][j]
    labels = {str(cell.value): cell.row for cell in ws["A"] if cell.value is not None}
    row_keys = {key: (key.rsplit(".", 1)[0] if key.rsplit(".", 1)[-1].isdigit() and not key.startswith(("wacc.", "terminal.", "bridge.")) else key) for key in changes}
    missing = sorted(set(row_keys.values()) - set(labels))
    if missing:
        raise ValueError("missing semantic input labels: " + ", ".join(missing))
    for key, value in changes.items():
        row = labels[row_keys[key]]
        if "." in key and key.rsplit(".", 1)[1].isdigit() and not key.startswith(("wacc.", "terminal.", "bridge.")):
            col = 3 + int(key.rsplit(".", 1)[1])
        else:
            col = 3
        cell = ws.cell(row, col)
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            cell.value = dt.date.fromisoformat(value)
            cell.number_format = "yyyy-mm-dd"
        else:
            cell.value = value
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.save(destination)


def failed_result(task_id, reason):
    return {"task_id": task_id, "reward": 0.0, "score": 0.0, "passed": False,
            "reason": reason, "criteria": []}


def grade_workbook(task_dir, soffice, candidate_path=None, include_perturbations=True, work_dir=None):
    task_dir = Path(task_dir)
    metadata_dir = task_dir if (task_dir / "grader_spec.json").exists() else task_dir / "tests"
    rubric_path = metadata_dir / "rubrics.json" if (metadata_dir / "rubrics.json").exists() else task_dir / "rubrics.json"
    spec = load_json(metadata_dir / "grader_spec.json")
    expected = load_json(metadata_dir / "expected.json")
    rubrics = load_json(rubric_path)
    candidate = Path(candidate_path) if candidate_path else Path("/app/output.xlsx")
    if not candidate.exists():
        return failed_result(spec["task_id"], f"missing {candidate}")
    try:
        if work_dir:
            work = Path(work_dir) / uuid.uuid4().hex
            work.mkdir(parents=True)
            return _grade_in_work(task_dir, spec, expected, rubrics, candidate, soffice, include_perturbations, work)
        with tempfile.TemporaryDirectory(prefix=f"{spec['task_id']}-grade-") as temp:
            return _grade_in_work(task_dir, spec, expected, rubrics, candidate, soffice, include_perturbations, Path(temp))
    except Exception as exc:
        return failed_result(spec["task_id"], f"grader exception: {type(exc).__name__}: {exc}")


def _grade_in_work(task_dir, spec, expected, rubrics, candidate, soffice, include_perturbations, work):
    try:
        base_book = recalculate(candidate, work / "base", soffice)
        formulas = load_workbook(base_book, data_only=False)
        values = load_workbook(base_book, data_only=True)
    except Exception as exc:
        return failed_result(spec["task_id"], f"cannot recalculate: {exc}")
    errors = []
    for ws in formulas.worksheets:
        value_ws = values[ws.title]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    cached = value_ws[cell.coordinate].value
                    if cached is None or (isinstance(cached, str) and cached.startswith("#")):
                        errors.append(f"{ws.title}!{cell.coordinate}={cached}")
                if isinstance(cell.value, str) and ("[" in cell.value or "]" in cell.value):
                    errors.append(f"external-link-like formula {ws.title}!{cell.coordinate}")
    results = []
    for criterion in rubrics["criteria"]:
        detail = {"id": criterion["id"], "weight": criterion["weight"], "earned": 0.0,
                  "passed": False, "category": criterion["category"]}
        kind = criterion["kind"]
        checks = criterion.get("checks", [])
        try:
            if kind == "structure":
                missing_sheets = [name for name in ("Inputs", "Historical", "Forecast", "Valuation", "Checks")
                                  if name not in formulas.sheetnames]
                missing_labels = []
                for address, text in criterion.get("labels", {}).items():
                    sheet, cell = address.split("!")
                    if sheet not in formulas.sheetnames or str(formulas[sheet][cell].value).strip() != text:
                        missing_labels.append(address)
                detail["missing_sheets"] = missing_sheets
                detail["missing_labels"] = missing_labels
                passed = not missing_sheets and not missing_labels
            elif kind == "recalc":
                passed = not errors
                detail["formula_errors"] = errors[:40]
                detail["error_count"] = len(errors)
            elif kind == "numeric":
                observations, failures = {}, []
                for check in checks:
                    address = check["cell"]
                    sheet, cell = address.split("!")
                    want = resolve_path(expected["baseline"], check["expected_path"])
                    got = values[sheet][cell].value if sheet in values.sheetnames else None
                    observations[address] = {"actual": got, "expected": want}
                    if sheet not in values.sheetnames or not numeric_equal(got, want):
                        failures.append(address)
                detail["observations"] = observations
                detail["failed_cells"] = failures
                passed = not failures
            elif kind == "formula":
                failures = []
                for address in criterion["cells"]:
                    sheet, cell = address.split("!")
                    if sheet not in formulas.sheetnames:
                        failures.append(address)
                        continue
                    formula = formulas[sheet][cell].value
                    dependencies = formula_dependencies(formulas, sheet, cell)
                    linked = any(s == "Inputs" for s, _ in dependencies)
                    if address in criterion.get("input_free_cells", []):
                        linked = linked or any(s == "Forecast" for s, _ in dependencies)
                    if not isinstance(formula, str) or not formula.startswith("=") or not linked:
                        failures.append(address)
                detail["failed_cells"] = failures
                passed = not failures
            elif kind == "perturbation":
                if not include_perturbations:
                    detail["skipped"] = True
                    passed = False
                    detail["earned"] = 0
                    results.append(detail)
                    continue
                index = criterion["perturbation_index"]
                changed = work / f"perturbed_{index}.xlsx"
                update_inputs(base_book, spec, spec["perturbations"][index], changed)
                pert_book = recalculate(changed, work / f"perturbation_{index}", soffice)
                pert_values = load_workbook(pert_book, data_only=True)
                observations, failures = {}, []
                for check in checks:
                    sheet, cell = check["cell"].split("!")
                    want = resolve_path(expected["perturbations"][index], check["expected_path"])
                    got = pert_values[sheet][cell].value if sheet in pert_values.sheetnames else None
                    observations[check["cell"]] = {"actual": got, "expected": want}
                    if sheet not in pert_values.sheetnames or not numeric_equal(got, want):
                        failures.append(check["cell"])
                detail["observations"] = observations
                detail["failed_cells"] = failures
                passed = not failures
            else:
                raise ValueError(f"unknown rubric kind: {kind}")
        except Exception as exc:
            passed = False
            detail["error"] = f"{type(exc).__name__}: {exc}"
        detail["passed"] = bool(passed)
        detail["earned"] = criterion["weight"] if passed else 0.0
        results.append(detail)
    raw_score = round(sum(item["earned"] for item in results), 6)
    failed_ids = {item["id"].rsplit("-", 1)[-1] for item in results if not item["passed"]}
    score = raw_score
    if "L01" in failed_ids:
        score = min(score, 25.0)
    if "P01" in failed_ids or "P02" in failed_ids:
        score = min(score, 60.0)
    if "R01" in failed_ids:
        score = min(score, 20.0)
    score = round(score, 6)
    return {"task_id": spec["task_id"], "reward": round(score / 100, 6), "score": score,
            "raw_score_before_formula_gates": raw_score,
            "passed": all(item["passed"] for item in results), "criteria": results,
            "candidate": str(candidate), "recalculation_engine": soffice}


def make_static_negative(task_dir, destination):
    """A maximally deceptive all-static workbook: correct base numbers, no live formulas."""
    task_dir = Path(task_dir)
    reference = load_workbook(task_dir / "solution/reference.xlsx", data_only=False)
    expected = load_json(task_dir / "tests/expected.json")["baseline"]
    rubric = load_json(task_dir / "rubrics.json")
    wb = Workbook()
    wb.remove(wb.active)
    for source in reference.worksheets:
        ws = wb.create_sheet(source.title)
        for row in source.iter_rows():
            for cell in row:
                if cell.value is not None and not (isinstance(cell.value, str) and cell.value.startswith("=")):
                    ws[cell.coordinate] = cell.value
    for criterion in rubric["criteria"]:
        if criterion["kind"] != "numeric":
            continue
        for check in criterion.get("checks", []):
            sheet, cell = check["cell"].split("!")
            wb[sheet][cell] = resolve_path(expected, check["expected_path"])
    wb.save(destination)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--candidate")
    parser.add_argument("--soffice", default=os.environ.get("SOFFICE", "/usr/bin/soffice"))
    parser.add_argument("--report", default="/logs/verifier/report.json")
    args = parser.parse_args()
    report = grade_workbook(args.task_dir, args.soffice, args.candidate)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reward_path = report_path.parent / "reward.txt"
    reward_path.write_text(f"{report['reward']}\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("task_id", "reward", "passed", "reason") if k in report}, ensure_ascii=False))
    for item in report["criteria"]:
        if not item["passed"]:
            print("FAIL", item["id"], item.get("failed_cells", item.get("error", item.get("missing_labels", ""))))


if __name__ == "__main__":
    main()
