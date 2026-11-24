#!/usr/bin/env python3
"""Summarize actual Harbor oracle rewards from every preserved job directory."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = []
    for task in sorted(p for p in (ROOT / "tasks").iterdir() if (p / "rubric.json").is_file()):
        task_rows = []
        for job in sorted((ROOT / "evaluation" / "oracle_jobs").glob(task.name + "*")):
            if not job.is_dir():
                continue
            trials = []
            for trial in job.glob("*__*"):
                metadata_path = trial / "result.json"
                metadata = json.loads(metadata_path.read_text()) if metadata_path.is_file() else {}
                rewards = []
                for reward in sorted(trial.rglob("reward.json")):
                    try:
                        rewards.append(json.loads(reward.read_text()))
                    except (ValueError, OSError):
                        pass
                for reward in sorted(trial.rglob("reward.txt")):
                    if not rewards:
                        try:
                            rewards.append(float(reward.read_text().strip()))
                        except (ValueError, OSError):
                            pass
                trials.append({"trial": trial.name, "exception": metadata.get("exception_info"),
                               "rewards": rewards, "step_results": metadata.get("step_results")})
            task_rows.append({"job": str(job.relative_to(ROOT)), "trials": trials})
        rows.append({"task": task.name, "runs": task_rows})
    (ROOT / "evaluation" / "oracle_summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"tasks": len(rows), "runs": sum(len(r["runs"]) for r in rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
