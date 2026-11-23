#!/bin/bash
set -u
mkdir -p /logs/verifier
SOFFICE=/usr/bin/soffice python3 /tests/grader.py --task-dir /tests --report /logs/verifier/report.json
python3 - <<'PY'
import json
from pathlib import Path
_primary = Path('/logs/verifier')
_reward = 0.0
try:
    if not (_primary/'reward.txt').exists():
        _r = json.loads((_primary/'report.json').read_text())
        _reward = float(_r.get('reward', _r.get('mechanism_score', 0)))
    else:
        _reward = float((_primary/'reward.txt').read_text())
except Exception:
    pass
_primary.mkdir(parents=True, exist_ok=True)
(_primary/'reward.txt').write_text(str(_reward))
(_primary/'reward.json').unlink(missing_ok=True)

PY
exit 0
