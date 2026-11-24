#!/usr/bin/env python3
"""Run every task's Harbor oracle and preserve machine-readable reward evidence."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", nargs="*")
    parser.add_argument("--jobs-dir", type=Path, default=ROOT / "evaluation" / "oracle_jobs")
    parser.add_argument("--provider", default="ipv4_docker_environment:IPv4DockerEnvironment")
    parser.add_argument("--rerun", action="store_true", help="Use fresh job directories instead of the original evidence paths")
    args = parser.parse_args()
    args.jobs_dir.mkdir(parents=True, exist_ok=True)
    tasks = args.tasks or [p.name for p in sorted((ROOT / "tasks").iterdir()) if (p / "rubric.json").is_file()]
    config = ROOT / "evaluation" / "oracle.yaml"
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "evaluation"), LITELLM_LOCAL_MODEL_COST_MAP="true")
    rerun_suffix = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S") if args.rerun else ""
    summary = []
    for task in tasks:
        job = args.jobs_dir / (task + rerun_suffix)
        log = args.jobs_dir / f"{task}{rerun_suffix}.log"
        started = time.time()
        command = ["harbor", "run", "--config", str(config), "--path", str(ROOT / "tasks" / task),
                   "--agent", "oracle", "--job-name", str(job), "--jobs-dir", str(job.parent), "--yes"]
        with log.open("w") as stream:
            result = subprocess.run(command, cwd=ROOT, env=environment, stdout=stream, stderr=subprocess.STDOUT)
        rewards = []
        for trial in job.glob("*__*"):
            result_path = trial / "result.json"
            metadata = json.loads(result_path.read_text()) if result_path.is_file() else {}
            step_rewards = []
            for reward in sorted(trial.rglob("reward.json")):
                try:
                    step_rewards.append({"path": str(reward.relative_to(trial)), "reward": json.loads(reward.read_text())})
                except (ValueError, OSError):
                    pass
            rewards.append({"trial": trial.name, "model": (metadata.get("config", {}).get("agent") or {}).get("model_name"),
                            "exception": metadata.get("exception_info"), "step_results": metadata.get("step_results"), "rewards": step_rewards})
        summary.append({"task": task, "returncode": result.returncode, "seconds": round(time.time() - started, 2),
                        "job": str(job.relative_to(ROOT)), "log": str(log.relative_to(ROOT)), "trials": rewards,
                        "task_sha256": sha(ROOT / "tasks" / task / "task.toml")})
        result_path = ROOT / "evaluation" / "oracle_results.json"
        prior = json.loads(result_path.read_text()) if result_path.is_file() else {"tasks": []}
        merged = {row["task"]: row for row in prior.get("tasks", []) if row["task"] not in tasks}
        merged.update({row["task"]: row for row in summary})
        result_path.write_text(json.dumps({"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                                           "provider": args.provider, "tasks": list(merged.values())}, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(summary[-1] | {"trials": len(rewards)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
