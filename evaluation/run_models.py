#!/usr/bin/env python3
"""Run selected models on selected Harbor tasks with immutable job names."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
MODELS = ("kimi-k3.1-pro", "deepseek-v4-pro")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--tasks", nargs="+", required=True)
    parser.add_argument("--batch", default="manual")
    args = parser.parse_args()
    config = ROOT / "evaluation" / f"{args.model}.yaml"
    if not config.is_file():
        raise SystemExit(f"缺少模型配置：{config}")
    jobs = ROOT / "evaluation" / "model_jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    for task in args.tasks:
        job = jobs / f"{args.batch}-{args.model}-{task}"
        log = jobs / f"{job.name}.log"
        command = ["harbor", "run", "--config", str(config), "--path", str(ROOT / "tasks" / task),
                   "--job-name", str(job), "--jobs-dir", str(job.parent), "--yes",
                   "--artifact", "/app/output.xlsx", "--artifact", "/app/memo.md", "--artifact", "/app/output"]
        if (ROOT / "tasks" / task / "steps").is_dir():
            command.append("--resume-trajectory")
        env = dict(os.environ, PYTHONPATH=str(ROOT / "evaluation"), LITELLM_LOCAL_MODEL_COST_MAP="true")
        started = time.time()
        with log.open("w") as stream:
            code = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
        record = {"task": task, "model": args.model, "job": str(job.relative_to(ROOT)),
                  "returncode": code, "seconds": round(time.time() - started, 2),
                  "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
        with (jobs / "runs.jsonl").open("a") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
