#!/usr/bin/env python3
import csv
import datetime as dt
import hashlib
import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


def sha_bytes(content):
    return hashlib.sha256(content).hexdigest()


def fetch_bytes(url, output=None):
    request = urllib.request.Request(url, headers={"User-Agent": "dcf-eval-v3-research"})
    with urllib.request.urlopen(request, timeout=60) as response:
        content = response.read()
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(content)
    return content


def load_snapshot(directory, ticker):
    directory = Path(directory)
    return (directory / f"{ticker}_facts.json").read_bytes(), (directory / "DGS10.csv").read_text()


def sec_crosscheck(facts, contract):
    cik = int(contract["company"]["cik"])
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{cik}-facts.json"
    rows = []
    for entry in contract["required_fields"]:
        if entry["kind"] == "market":
            continue
        values = []
        for tag in entry["allowed_tags"]:
            concept = facts.get("facts", {}).get("us-gaap", {}).get(tag, {})
            for unit, observations in concept.get("units", {}).items():
                if unit != entry["raw_unit"]:
                    continue
                for row in observations:
                    if row.get("form") not in ("10-K", "10-K/A") or row.get("filed", "9999") > contract["information_cutoff"] or row.get("end") != entry["end"]:
                        continue
                    if entry["kind"] == "flow" and row.get("start") != entry.get("start"):
                        continue
                    values.append(row["val"])
        rows.append({"field_id": entry["field_id"], "method": "tag_alias_reconciliation",
                     "values": sorted(set(values)), "matches": len(set(values)) <= 1,
                     "source_url": url,
                     "explanation": "原始 companyfacts 内允许标签的事实一致性检查；不是独立审计意见。"})
    return rows


def treasury_rows(content):
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    if text.lstrip().startswith("observation_date"):
        rows = list(csv.DictReader(io.StringIO(text)))
        return [{"date": row.get("observation_date", row.get("Date", "")), "value": row.get("DGS10", row.get("10 Yr", ""))} for row in rows]
    rows = list(csv.DictReader(io.StringIO(text)))
    result = []
    for row in rows:
        raw_date = row.get("Date", row.get("date", ""))
        try:
            date = dt.datetime.strptime(raw_date, "%m/%d/%Y").date().isoformat()
        except ValueError:
            date = raw_date
        result.append({"date": date, "value": row.get("10 Yr", row.get("DGS10", ""))})
    return result


def treasury_value(content, cutoff):
    candidates = []
    for row in treasury_rows(content):
        if row["date"] > cutoff or str(row["value"]).strip() in ("", ".", "ND"):
            continue
        try:
            value = float(row["value"])
        except (TypeError, ValueError):
            continue
        candidates.append((row["date"], value))
    if not candidates:
        raise ValueError("截止日前无 10 年期收益率")
    return sorted(candidates)[-1]
