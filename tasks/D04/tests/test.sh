#!/bin/bash
set -euo pipefail
python3 - <<'PY'
import json
from pathlib import Path
reports=sorted(Path('/logs/verifier/steps').glob('step-*/reward.json'))
values=[json.loads(p.read_text()).get('reward',0) for p in reports]
reward=sum(values)/len(values) if values else 0.0
Path('/logs/verifier/reward.txt').write_text(str(reward)+chr(10))
Path('/logs/verifier/reward.json').write_text(json.dumps({'reward':reward}))
PY
