#!/usr/bin/env python3
"""Aggregate binary rubric evidence; keep scoring schemes separate and reproducible."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_CATEGORIES = {"公式与模型工程"}
CATEGORY_MAP = {
    "交付与来源完整性": "delivery", "历史与会计口径": "history",
    "经营预测": "operating", "三表勾稽": "statements", "DCF与估值桥": "valuation",
    "公式与模型工程": "formulas", "表达与专业可用性": "presentation",
    "联网取数与来源": "sources", "开放预测与模拟": "open_model",
}


def merge(judgment, row):
    rid = row["id"]
    if row["rubric_method"] == "llm":
        result = judgment.get("llm", {}).get(rid, {})
    else:
        scores = judgment.get("agent", {}).get("scores", {})
        result = {"status": "pass" if scores.get(rid) == 1 else "fail" if scores.get(rid) == 0 else "unscored"}
    return result


def task_score(items, scheme):
    categories = defaultdict(list)
    for row in items:
        if row["status"] not in ("pass", "fail"):
            continue
        categories[row["category"]].append(row)
    details = {}
    earned = possible = 0
    for category, rows in categories.items():
        weight = sum(row["weight"] for row in rows)
        if scheme == "category_gate" and category in GATE_CATEGORIES:
            value = weight if all(row["status"] == "pass" for row in rows) else 0
        elif scheme == "primary_gate":
            primary = [row for row in rows if row["importance"] == "主需"]
            value = weight if all(row["status"] == "pass" for row in primary) else 0
        elif scheme == "hybrid":
            if category in GATE_CATEGORIES:
                value = weight if all(row["status"] == "pass" for row in rows) else 0
            else:
                value = sum(row["weight"] for row in rows if row["status"] == "pass")
        else:
            value = sum(row["weight"] for row in rows if row["status"] == "pass")
        earned += value
        possible += weight
        details[category] = {"earned": value, "possible": weight, "failed": [row["id"] for row in rows if row["status"] == "fail"]}
    return {"score": 100 * earned / possible if possible else 0, "earned": earned, "possible": possible, "categories": details,
            "unscored": [row["id"] for row in items if row["status"] not in ("pass", "fail")]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--judge", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    judgment = json.loads(args.judge.read_text()) if args.judge else {}
    items = []
    for row in data["items"]:
        if row["rubric_method"] in ("llm", "agent"):
            result = merge(judgment, row)
            row = dict(row, **result)
        items.append(row)
    output = {"task": data["task"], "schemes": {scheme: task_score(items, scheme) for scheme in ("atomic", "hybrid", "primary_gate")},
              "items": items}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
