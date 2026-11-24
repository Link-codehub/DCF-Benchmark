#!/bin/bash
set -u
mkdir -p /logs/verifier
python3 /tests/grader.py --task-dir /tests --report /logs/verifier/report.json
exit 0

mkdir -p /logs/verifier
python3 - <<'PY'
import json
from pathlib import Path
p = next((p for p in [Path('/logs/verifier/details.json'), Path('/logs/verifier/report.json')] if p.is_file()), None)
try:
    d = json.loads(p.read_text()) if p else {}
    value = d.get('reward', d.get('mechanism_score', float(bool(d.get('passed', d.get('rule_passed', False))))))
except Exception:
    value = 0.0
Path('/logs/verifier/reward.txt').write_text(str(value) + chr(10))
Path('/logs/verifier/reward.json').write_text(json.dumps({'reward': value}))
PY
