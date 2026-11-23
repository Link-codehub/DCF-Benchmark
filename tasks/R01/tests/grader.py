#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from grader_common import grade_workbook

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--candidate")
    parser.add_argument("--soffice", default="/usr/bin/soffice")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    result = grade_workbook(args.task_dir, args.soffice, args.candidate)
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (report.parent / "reward.txt").write_text(str(result["reward"]) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("task_id", "reward", "passed", "reason") if k in result}, ensure_ascii=False))
    for item in result["criteria"]:
        if not item["passed"]:
            print("FAIL", item["id"], item.get("failed_cells", item.get("error", "")))
