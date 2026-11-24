#!/usr/bin/env python3
"""Native E/W rule execution with selected-rubric mappings."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

E_MAP = {
    "01-FILE": ["E-deliver_model"], "02-SBC": ["E-hist_ebit"],
    "03-MARGIN": ["E-forecast_ebit"], "03-NWC": ["E-forecast_reinvestment"],
    "05-DF": ["E-dcf_discount"], "05-BRIDGE": ["05-BRIDGE"],
    "06-LINKS": ["06-RECALC"], "X-FM-001": ["E-deterministic_model"],
}
W_MAP = {
    "01-KEYS": ["W-VALUE"], "03-MARGIN": ["W-OPERATING-RECALC"],
    "03-NWC": ["W-OPERATING-RECALC"], "B-NWC-OPEN": ["W-OPERATING-RECALC"],
    "05-DF": ["05-FCFF"], "06-LINKS": ["06-RECALC"],
    "X-FM-001": ["W-USED", "W-SOURCE-PERTURB"],
}


def grade(task, artifact, work):
    work.mkdir(parents=True, exist_ok=True)
    tests = task / "tests"
    command = [sys.executable, str(tests / "grader.py"), "--artifact-dir", str(artifact),
               "--input", str(tests / "inputs.json"), "--truth", str(tests / "truth.json"),
               "--spec", str(tests / "spec.json"), "--output-dir", str(work)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=900)
    (work / "grader_stdout.txt").write_text(run.stdout[-30000:] + run.stderr[-30000:])
    report = json.loads((work / "details.json").read_text()) if (work / "details.json").is_file() else {"checks": {}}
    checks = report.get("checks", {})
    mapping = E_MAP if task.name.startswith("E") else W_MAP
    items = []
    for item in json.loads((task / "rubric.json").read_text())["items"]:
        rid = item["id"]
        ids = mapping.get(rid, [rid])
        rows = [checks[i] for i in ids if i in checks]
        if item["method"] != "rule":
            result = {"status": "not_executed"}
        else:
            result = {"status": "pass" if rows and all(row["passed"] for row in rows) else "fail" if rows else "not_executed",
                      "native_ids": ids, "native_evidence": rows}
        items.append({k: item[k] for k in ("id", "category", "importance", "weight")} | {"rubric_method": item["method"], **result})
    return {"task": task.name, "artifact": str(artifact), "native_reward": report.get("reward"),
            "native_gate_failures": report.get("hard_gate_failures"), "items": items,
            "semantic_pending": [i["id"] for i in items if i["rubric_method"] != "rule"],
            "unexecuted_rules": [i["id"] for i in items if i["rubric_method"] == "rule" and i["status"] == "not_executed"],
            "forecast_accuracy_diagnostic": report.get("forecast_accuracy_diagnostic"),
            "market_calibration_diagnostic": report.get("market_calibration_diagnostic")}
