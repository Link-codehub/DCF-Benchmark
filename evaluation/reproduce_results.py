#!/usr/bin/env python3
"""Recompute rules and semantic judgments from preserved model artifacts."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", nargs="*")
    parser.add_argument("--semantic", action="store_true", help="Call the configured judge model for llm/agent items")
    parser.add_argument("--judge-model", default="claude-opus-5-5")
    args = parser.parse_args()
    records = json.loads((ROOT / "evaluation" / "evidence_index.json").read_text())
    seen = set()
    for record in records:
        task, model, job = record["task"], record["model"], record["job"]
        if (task, model, job) in seen or (args.tasks and task not in args.tasks):
            continue
        seen.add((task, model, job))
        directory = ROOT / "evaluation" / "jobs" / job
        trial = next(directory.glob("*__*"), None)
        if trial is None:
            continue
        artifact = trial / "artifacts" / "app" / "output" if task.startswith(("E", "W")) else trial / "artifacts" / "app" / "output.xlsx"
        if not artifact.exists():
            continue
        output = ROOT / "evaluation" / "recomputed" / model / task / f"{job}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, str(ROOT / "evaluation" / "score_candidate.py"), task, str(artifact), str(output)],
                       cwd=ROOT, check=True)
        if args.semantic:
            subprocess.run([sys.executable, str(ROOT / "evaluation" / "judge.py"), task, str(artifact),
                            str(ROOT / "evaluation" / "recomputed_judges" / model / task / f"{job}.json"),
                            "--model", args.judge_model], cwd=ROOT, check=True)
        print(json.dumps({"task": task, "model": model, "result": str(output.relative_to(ROOT))}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
