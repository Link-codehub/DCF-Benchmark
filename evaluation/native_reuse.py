#!/usr/bin/env python3
"""Reuse v1/v2 native fine-grained reports without reinterpreting workbook labels."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

R01_MAP = {
    "01-FILE": ["B01-S01"], "01-KEYS": ["B01-S01"],
    "02-FY": ["B01-H01", "B01-H02"], "02-LTM": ["B01-H03"],
    "03-MARGIN": ["B01-F03"], "03-NWC": ["B01-W01", "B01-W02"],
    "B-NWC-OPEN": ["B01-W01"], "03-DAYS": ["B01-W01", "B01-W02"],
    "B-INTANG-ROLL": ["B01-F06"], "B-INTANG-FCFF": ["B01-F06", "B01-C01"],
    "A-DRIVER": ["B01-F01", "B01-F02"], "04-PPE": ["B01-F04", "B01-F05"],
    "05-FCFF": ["B01-C01", "B01-C02", "B01-C03"],
    "05-DF": ["B01-T01", "B01-C02", "B01-V04"],
    "05-TV": ["B01-V03", "B01-V04"], "05-BRIDGE": ["B01-V06"],
    "05-VPS": ["B01-V07"], "B-RESIDUAL": ["B01-T01", "B01-F01"],
    "06-FORMULA": ["B01-L01"], "06-RECALC": ["B01-R01"],
    "06-PERTURB1": ["B01-P01"], "06-PERTURB2": ["B01-P02"], "06-LINKS": ["B01-R01"],
}


def grade(task, candidate, work, soffice):
    work.mkdir(parents=True, exist_ok=True)
    report_path = work / "native_report.json"
    if task.name == "R01":
        command = [sys.executable, str(task / "tests" / "grader.py"), "--task-dir", str(task / "tests"),
                   "--candidate", str(candidate), "--soffice", soffice, "--report", str(report_path)]
    else:
        command = [sys.executable, str(task / "tests" / "grader.py"), "--task-dir", str(task / "tests"),
                   "--candidate", str(candidate), "--soffice", soffice, "--report", str(report_path), "--work-dir", str(work / "recalc")]
    result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    (work / "grader_stdout.txt").write_text(result.stdout[-30000:] + result.stderr[-30000:])
    report = json.loads(report_path.read_text()) if report_path.is_file() else {"criteria": [], "error": result.stdout[-500:]}
    native = {row["id"]: row for row in report.get("criteria", [])}
    supplemental = {}
    if task.name == "R02":
        sys.path.insert(0, str(task / "tests"))
        from openpyxl import load_workbook
        from workbook import discover_values
        expected = json.loads((task / "tests" / "expected.json").read_text())
        template = json.loads((task / "tests" / "grader_spec.json").read_text())["output"]["template"]
        recalculations = report.get("diagnostics", {}).get("recalculations", [])
        if recalculations and Path(recalculations[0]).is_file():
            wb = load_workbook(recalculations[0], data_only=True)
            values, _, _ = discover_values(wb, template, expected["baseline"])
            fields = {
                "02-SBC": ["fy_normalized_ebit", "ltm_normalized_ebit"],
                "B-NWC-OPEN": ["nwc_p1", "delta_nwc_p1", "statement_delta_nwc_p1"],
                "B-RESIDUAL": ["activity_p1", "revenue_p1", "fcff_p1"],
                "06-FREE": list(expected["baseline"]),
            }
            for rid, keys in fields.items():
                bad = [key for key in keys if key not in values]
                supplemental[rid] = {"status": "fail" if bad else "pass", "evidence_keys": keys, "missing": bad}
    items = []
    for item in json.loads((task / "rubric.json").read_text())["items"]:
        rid = item["id"]
        if item["method"] != "rule":
            result = {"status": "not_executed"}
        elif task.name == "R02":
            row = native.get(rid)
            result = {"status": "pass" if row and row.get("score") == 1 else "fail" if row else "not_executed", "native_evidence": row}
            if rid in supplemental:
                result = supplemental[rid]
        else:
            ids = R01_MAP.get(rid, [])
            rows = [native[i] for i in ids if i in native]
            result = {"status": "pass" if rows and all(row.get("passed") for row in rows) else "fail" if rows else "not_executed", "native_ids": ids, "native_evidence": rows}
        items.append({k: item[k] for k in ("id", "category", "importance", "weight")} | {"rubric_method": item["method"], **result})
    return {"task": task.name, "candidate": str(candidate), "native_reward": report.get("reward"),
            "native_rule_reward": report.get("rule_reward"), "items": items,
            "semantic_pending": [i["id"] for i in items if i["rubric_method"] != "rule"],
            "unexecuted_rules": [i["id"] for i in items if i["rubric_method"] == "rule" and i["status"] == "not_executed"]}
