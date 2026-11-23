#!/bin/bash
set -euo pipefail
mkdir -p /app/output
python3 /solution/reference.py --input /app/data/inputs.json --output /app/output
python3 /app/output/simulate.py --input /app/data/inputs.json --model /app/output/model.json --output /app/output/simulation.json
