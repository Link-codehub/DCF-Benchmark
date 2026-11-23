#!/bin/bash
set -euo pipefail
mkdir -p /app/snapshots
cp "$(dirname "$0")/reference.xlsx" /app/output.xlsx
cp "$(dirname "$0")/memo.md" /app/memo.md
cp "$(dirname "$0")/reference.xlsx" /app/snapshots/step-2.xlsx
