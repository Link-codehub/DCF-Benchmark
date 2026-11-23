#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from common import ROOT, V3, dump, sha
from e_build import TASK_PLAN as E_PLAN, build as build_e
from w_build import TASK_PLAN as W_PLAN, build as build_w


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tasks", nargs="*", default=["E01", "W01"])
    args = parser.parse_args()
    requested = args.tasks or ["E01", "W01"]
    records = []
    for task_id in requested:
        if task_id in E_PLAN:
            record = build_e(task_id)
        elif task_id in W_PLAN:
            record = build_w(task_id)
        else:
            raise ValueError("未知任务：" + task_id)
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    manifest = {"schema_version": "dcf-v3-open-generation-v1", "generator": "open/generate.py",
                "tasks": records, "v2_modified": False, "model_api_called": False,
                "secrets_read_or_written": False,
                "generator_sha256": {path.name: sha(path) for path in sorted(ROOT.glob("*.py"))}}
    dump(ROOT / "generation.json", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
