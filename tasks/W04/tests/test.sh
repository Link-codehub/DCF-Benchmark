#!/bin/bash
set -u
mkdir -p /logs/verifier
cd /tests
python3 grader.py --input /tests/inputs.json --truth /tests/truth.json --spec /tests/spec.json --artifact-dir /app/output --output-dir /logs/verifier > /logs/verifier/grader.log 2>&1

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
