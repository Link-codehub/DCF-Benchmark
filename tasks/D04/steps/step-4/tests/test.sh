#!/bin/bash
set -e
mkdir -p /logs/verifier /app
if [ ! -f /app/inputs.xlsx ]; then cp /tests/inputs.xlsx /app/; fi
if [ ! -f /app/inputs.json ]; then cp /tests/inputs.json /app/; fi
if [ -f /tests/event.json ]; then cp /tests/event.json /tests/event_inputs.xlsx /tests/event_inputs.json /app/; fi
python3 /tests/grader.py --step 4 --task-dir /tests --candidate /app/output.xlsx --work-dir /logs/verifier/work --report /logs/verifier/report.json

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
