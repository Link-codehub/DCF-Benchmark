#!/bin/bash
set -euo pipefail
mkdir -p /app/output
python3 /solution/reference.py --input /app/data/retrieval_contract.json --output /app/output
