#!/usr/bin/env python3
"""Workbook-internal deterministic checks for presentation-neutral formula structure."""
from pathlib import Path
import re
from openpyxl import load_workbook


def visible_period_formulas(workbook, prefixes):
    found = []
    for sheet in workbook:
        if sheet.sheet_state != "visible":
            continue
        for row in sheet.iter_rows():
            label = row[0].value
            if not isinstance(label, str):
                continue
            normalized = label.strip().lower().replace(" ", "_")
            if not any(normalized == p or normalized.startswith(p + "_") for p in prefixes):
                continue
            formulas = [c.value for c in row[1:] if isinstance(c.value, str) and c.value.startswith("=")]
            if formulas:
                found.append({"sheet": sheet.title, "label": label, "count": len(formulas), "formulas": formulas[:6]})
    return found


def checks(path):
    wb = load_workbook(path, data_only=False)
    periods = visible_period_formulas(wb, ["discount_time", "discount_factor", "end_time"])
    fcff = visible_period_formulas(wb, ["fcff", "ebit", "da", "capex", "delta_nwc", "tax"])
    tv = visible_period_formulas(wb, ["terminal_value", "tv_gordon", "tv_exit"])
    return {
        "X-TA-004": bool(periods),
        "X-TA-006": {name: any(row["label"].strip().lower().replace(" ", "_").startswith(name) for row in fcff) for name in ("fcff", "ebit", "da", "capex", "delta_nwc", "tax")},
        "X-TA-007": bool(tv),
    }


def evaluate(path, item):
    result = checks(path)
    rid = item["id"]
    if rid in ("X-TA-004", "X-TA-007"):
        passed = result[rid]
        return {"status": "pass" if passed else "fail", "evidence": result}
    if rid == "X-TA-006":
        required = ("ebit", "da", "capex", "delta_nwc")
        passed = all(result[rid][name] for name in required)
        return {"status": "pass" if passed else "fail", "evidence": result[rid]}
    return {"status": "not_executed"}
