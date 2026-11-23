#!/bin/bash
set -e
mkdir -p /logs/verifier /app
cp /tests/inputs.xlsx /tests/inputs.json /app/
python3 /tests/grader.py --task-dir /tests --candidate /app/output.xlsx --work-dir /logs/verifier/work --report /logs/verifier/report.json

mkdir -p /logs/verifier
python3 - <<'PY'
import json
from pathlib import Path
p = Path('/logs/verifier/report.json')
try:
    d = json.loads(p.read_text())
    value = d.get('reward', d.get('mechanism_score', float(bool(d.get('passed', d.get('rule_passed', False))))))
except Exception:
    value = 0.0
Path('/logs/verifier/reward.txt').write_text(str(value) + chr(10))
Path('/logs/verifier/reward.json').write_text(json.dumps({'reward': value}))
PY
