#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
python3 - <<'PY'
import json
from pathlib import Path
values=[]
for p in sorted(Path('/logs/verifier/steps').glob('step-*/reward.json')):
    values.append(json.loads(p.read_text()).get('reward', 0))
reward=sum(values)/len(values) if values else 0.0
Path('/logs/verifier/reward.txt').write_text(str(reward)+chr(10))
Path('/logs/verifier/reward.json').write_text(json.dumps({'reward':reward}))
PY
