#!/bin/bash
set -euo pipefail
for step in 1 2 3 4; do
  bash "/solution/steps/step-${step}/solution/solve.sh"
done
