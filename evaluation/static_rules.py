#!/usr/bin/env python3
"""Deterministic deliverable and public-input preservation checks."""
from pathlib import Path
from openpyxl import load_workbook


def input_map(workbook):
    if "Inputs" not in workbook.sheetnames:
        return {}
    return {row[0].value: [cell.value for cell in row[1:] if cell.value is not None]
            for row in workbook["Inputs"].iter_rows() if isinstance(row[0].value, str) and row[0].value}


def compare_input_maps(public, candidate):
    mismatches = []
    for key, values in public.items():
        actual = candidate.get(key)
        if actual is None:
            mismatches.append({"key": key, "reason": "missing_semantic_input"})
            continue
        for index, expected in enumerate(values):
            if index >= len(actual):
                mismatches.append({"key": key, "index": index, "reason": "missing_value"})
                continue
            value = actual[index]
            if isinstance(expected, str) and expected.startswith("=") and isinstance(value, str) and value.startswith("="):
                # Input sheets may be re-emitted with equivalent formulas. An LLM
                # judge must inspect those; plain numeric inputs are checked here.
                continue
            if value != expected:
                mismatches.append({"key": key, "index": index, "expected": expected, "actual": value})
    return mismatches


def evaluate(task, candidate, item):
    candidate = Path(candidate)
    if not candidate.is_file():
        return {"status": "fail", "reason": "missing_workbook"}
    workbook = load_workbook(candidate, data_only=False)
    rid = item["id"]
    if rid == "X-IF-001a":
        memo = candidate.parent / "memo.md"
        missing = [] if memo.is_file() and memo.stat().st_size else ["memo.md"]
        return {"status": "fail" if missing else "pass", "missing": missing}
    if rid == "X-IF-002":
        required = ["Inputs"] + [name for name in workbook.sheetnames if name.startswith("Results") or name == "Outputs"]
        passed = "Inputs" in workbook.sheetnames and len(required) >= 2
        return {"status": "pass" if passed else "fail", "required": required, "actual": workbook.sheetnames}
    if rid in ("X-IN-001", "X-IN-002"):
        public = load_workbook(task / "environment" / "inputs.xlsx", data_only=False)
        bad = compare_input_maps(input_map(public), input_map(workbook))
        return {"status": "fail" if bad else "pass", "mismatches": bad[:30]}
    if rid == "X-FM-007":
        try:
            calculation = workbook.calculation
            iterative = bool(calculation.iterate)
            return {"status": "fail" if iterative else "pass", "iterative_calculation_enabled": iterative}
        except Exception as exc:
            return {"status": "not_executed", "reason": str(exc)}
    if rid in ("X-FM-009", "X-FM-010"):
        forbidden = ("OFFSET(", "INDIRECT(", "NOW(", "TODAY(", "RAND(", "RANDBETWEEN(") if rid == "X-FM-009" else None
        bad = []
        for sheet in workbook:
            for row in sheet.iter_rows():
                for cell in row:
                    value = cell.value
                    if not isinstance(value, str) or not value.startswith("="):
                        continue
                    if forbidden and any(token in value.upper() for token in forbidden):
                        bad.append(sheet.title + "!" + cell.coordinate)
                    if rid == "X-FM-010" and any(token in value.upper() for token in ("SUM(", "NPV(")) and re_whole_range(value):
                        bad.append(sheet.title + "!" + cell.coordinate)
        return {"status": "fail" if bad else "pass", "violations": bad[:30]}
    return {"status": "not_executed"}


def re_whole_range(formula):
    import re
    return bool(re.search(r"(?:SUM|NPV)\([^)]*\b[A-Z]{1,3}:[A-Z]{1,3}\b|(?:SUM|NPV)\([^)]*\b\d+:\d+\b", formula, re.I))
