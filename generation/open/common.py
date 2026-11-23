#!/usr/bin/env python3
import datetime as dt
import hashlib
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V3 = ROOT.parent
EXP = V3.parent
DATA = ROOT / "data"
TASKS = V3 / "tasks"


def write(path, text, executable=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def dump(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def close(a, b, tolerance=0.001):
    return finite(a) and finite(b) and abs(a - b) <= max(1e-7, abs(b) * tolerance)


def percentile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low = int(position)
    high = math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def recalc(path):
    path = Path(path).resolve()
    temporary = Path(tempfile.mkdtemp(prefix="dcf-v3-recalc"))
    profile = Path(tempfile.mkdtemp(prefix="dcf-v3-profile"))
    result = subprocess.run(
        ["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--convert-to",
         "xlsx:Calc MS Excel 2007 XML", "--outdir", str(temporary), str(path)],
        capture_output=True, text=True, timeout=180)
    target = temporary / path.name
    if not target.exists():
        raise RuntimeError("LibreOffice 未生成重算工作簿：" + (result.stdout + result.stderr)[-500:])
    return target


def blank_environment(task):
    import shutil
    shutil.rmtree(task, ignore_errors=True)
    for directory in ("environment/data", "solution", "tests"):
        (task / directory).mkdir(parents=True, exist_ok=True)


def copy_public(task, tests_name="inputs.json"):
    import shutil
    shutil.copy2(task / "environment/data" / tests_name, task / "tests" / tests_name)


def dockerfiles(task):
    write(task / "environment/Dockerfile", "FROM dcfbench-agent:v1\nWORKDIR /app\nCOPY data /app/data\nRUN mkdir -p /app/output\n")
    write(task / "tests/Dockerfile", "FROM dcfbench-base:v1\nCOPY . /tests/\nRUN chmod +x /tests/test.sh\n")


def test_shell():
    return "#!/bin/bash\nset -u\nmkdir -p /logs/verifier\ncd /tests\npython3 grader.py --input /tests/inputs.json --truth /tests/truth.json --spec /tests/spec.json --artifact-dir /app/output --output-dir /logs/verifier > /logs/verifier/grader.log 2>&1\n"


def fiscal_nwc(row):
    if row.get("current_assets") is None or row.get("current_liabilities") is None:
        return None
    cash = row.get("cash") or 0
    investments = row.get("st_investments") or 0
    current_debt = row.get("debt_current") or 0
    return ((row["current_assets"] - cash - investments)
            - (row["current_liabilities"] - current_debt))


def yield_on(date):
    rows = []
    for raw in (DATA / "raw/DGS10.csv").read_text().splitlines()[1:]:
        fields = raw.split(",")
        if len(fields) >= 2 and fields[0] <= date and fields[1] not in ("", "."):
            rows.append((fields[0], float(fields[1]) / 100))
    if not rows:
        raise ValueError("截止日前无国债收益率")
    return rows[-1]


def source_record(ticker, cik):
    path = DATA / "raw" / f"{ticker}_facts.json"
    return {
        "source_id": "SEC_XBRL",
        "publisher": "美国证券交易委员会",
        "document": "SEC companyfacts XBRL 本地冻结快照",
        "url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json",
        "local_snapshot": f"../data/raw/{ticker}_facts.json",
        "source_sha256": sha(path),
        "retrieval_status": "生成时仅核验本地冻结文件及原始事实，未声称重新联网下载",
    }


def command_record(command, cwd=None, timeout=300):
    import time
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {"command": [str(x) for x in command], "returncode": result.returncode,
                "seconds": round(time.monotonic() - started, 2),
                "output_tail": (result.stdout + result.stderr)[-1200:]}
    except subprocess.TimeoutExpired:
        return {"command": [str(x) for x in command], "returncode": 124,
                "seconds": round(time.monotonic() - started, 2), "output_tail": "执行超时"}
