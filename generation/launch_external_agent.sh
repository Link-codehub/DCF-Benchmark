#!/bin/bash
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "Usage: $0 <workdir> <prompt-file> [model]" >&2
  exit 2
fi

mkdir -p "$1"
workdir=$(cd "$1" && pwd)
prompt_file=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
model=${3:-kimi-k3.1-pro}
cd "$workdir"

export KIMI_MODEL_BASE_URL=http://127.0.0.1:4310
export KIMI_MODEL_PROVIDER_TYPE=anthropic
export KIMI_MODEL_API_KEY=dummy
export KIMI_MODEL_MAX_CONTEXT_SIZE=1048576
export KIMI_MODEL_MAX_OUTPUT_SIZE=64000
export KIMI_MODEL_CAPABILITIES=thinking,tool_use
export KIMI_MODEL_THINKING_EFFORT=max
export KIMI_MODEL_THINKING_KEEP=off
export HTTP_PROXY=
export HTTPS_PROXY=
export ALL_PROXY=

export NO_COLOR=true
export TERM=dumb
/opt/homebrew/bin/kimi -m "$model" -p "$(cat "$prompt_file")" \
  > "$workdir/agent.raw.log" 2>&1

python3 - "$workdir/agent.raw.log" "$workdir/agent.clean.log" <<'PY'
import pathlib
import re
import sys
raw = pathlib.Path(sys.argv[1]).read_bytes().decode("utf-8", "replace")
raw = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", raw)
raw = re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)", "", raw)
pathlib.Path(sys.argv[2]).write_text(raw.replace("\r", "\n"), encoding="utf-8")
PY
