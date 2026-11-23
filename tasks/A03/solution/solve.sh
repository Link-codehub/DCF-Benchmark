#!/bin/bash
set -euo pipefail
cp "$(dirname "$0")/reference.xlsx" /app/output.xlsx
cp "$(dirname "$0")/memo.md" /app/memo.md
