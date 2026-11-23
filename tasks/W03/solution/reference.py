#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from w_retrieval import fetch_bytes, load_snapshot, sec_crosscheck, sha_bytes, treasury_value
from w_truth import extract_companyfacts, treasury_csv_url
from w_workbook import build_workbook

ASSUMPTIONS = {
    "AAPL": {"initial_growth": 0.06},
    "COST": {"initial_growth": 0.07},
    "SBUX": {"initial_growth": 0.06},
    "ADBE": {"initial_growth": 0.09},
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--snapshot-dir", help="仅用于本地验证的只读原始快照目录；联网运行不要使用")
    args = parser.parse_args()
    contract = json.load(open(args.input))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    ticker = contract["company"]["ticker"]
    raw_directory = output / "retrieved"
    if args.snapshot_dir:
        facts_bytes, treasury_text = load_snapshot(args.snapshot_dir, ticker)
        facts = json.loads(facts_bytes)
        retrieved_at = "本地冻结快照验证（未声称在线取数）"
        retrieval_mode = "local_snapshot_validation"
    else:
        facts_url = next(row["url"] for row in contract["allowed_sources"] if row["source_id"] == "SEC_COMPANYFACTS")
        facts_bytes = fetch_bytes(facts_url, raw_directory / "companyfacts.json")
        treasury_url = next(row["url"] for row in contract["allowed_sources"] if row["source_id"] == "UST_DAILY")
        treasury_text = fetch_bytes(treasury_url, raw_directory / "treasury.csv")
        facts = json.loads(facts_bytes)
        retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
        retrieval_mode = "online_allowed_sources"
    extracted = extract_companyfacts(facts, contract)
    date, yield_percent = treasury_value(treasury_text, contract["information_cutoff"])
    items = []
    for required in contract["required_fields"]:
        field_id = required["field_id"]
        if field_id == "treasury_10y":
            items.append({"field_id": field_id, "value": yield_percent / 100, "unit": "decimal",
                          "period_start": date, "period_end": date, "source_id": "UST_DAILY",
                          "source_url": next(row["url"] for row in contract["allowed_sources"] if row["source_id"] == "UST_DAILY"),
                          "source_file": "retrieved/treasury.csv", "field": "DGS10",
                          "form": "daily observation", "filed": date, "accession": None,
                          "observed_at": retrieved_at, "status": "success", "error": None,
                          "source_sha256": sha_bytes(treasury_text.encode() if isinstance(treasury_text, str) else treasury_text)})
            continue
        row = extracted[field_id]
        items.append({"field_id": field_id, "value": row["value"], "unit": row["unit"],
                      "period_start": row["start"], "period_end": row["end"],
                      "source_id": "SEC_COMPANYFACTS", "source_url": row["source_url"],
                      "source_file": "retrieved/companyfacts.json", "field": row["tag"],
                      "form": row["form"], "filed": row["filed"], "accession": row["accession"],
                      "observed_at": retrieved_at, "status": "success", "error": None,
                      "source_sha256": sha_bytes(facts_bytes)})
    sources = {"schema_version": "dcf-v3-w-sources-v1", "task_id": contract["task_id"],
               "retrieval_mode": retrieval_mode, "items": items,
               "failures": [], "source_hashes": {"companyfacts": sha_bytes(facts_bytes)}}
    values = {row["field_id"]: row["value"] for row in items}
    difference = values["pretax_income"] - values["income_tax"] - values["net_income_consolidated"]
    checks = [{"check_id": "pretax_to_net_income", "method": "reconciliation",
               "formula": "pretax_income - income_tax - net_income_consolidated", "difference": difference,
               "tolerance": max(0.01, abs(values["net_income_consolidated"]) * 0.02),
               "inputs": {key: values[key] for key in ("pretax_income", "income_tax", "net_income_consolidated")},
               "passed": abs(difference) <= max(0.01, abs(values["net_income_consolidated"]) * 0.02),
               "source": "SEC 同一原始 10-K 的税前利润、所得税与含非控股权益合并净利润勾稽"}]
    checks.extend({"check_id": "sec_tag_alias_" + row["field_id"], **row} for row in sec_crosscheck(facts, contract))
    (output / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2))
    (output / "cross_validation.json").write_text(json.dumps({"checks": checks}, ensure_ascii=False, indent=2))
    mapping = []
    for index, required in enumerate(contract["required_fields"]):
        field_id = required["field_id"]
        mapping.append({"field_id": field_id, "source_item_index": index, "sheet": "Sources",
                        "cell": f"B{index + 2}", "used_by": []})
    assumptions = {**ASSUMPTIONS[ticker], "wacc": values["treasury_10y"] + 0.055, "terminal_growth": 0.025}
    build_workbook(output / "model.xlsx", sources, mapping, assumptions, contract)
    (output / "retrieval_map.json").write_text(json.dumps({"items": mapping}, ensure_ascii=False, indent=2))
    (output / "memo.md").write_text(f"""参考取数及开放估值案例，不是目标价。运行模式：{retrieval_mode}；取数时间/状态：{retrieved_at}。所有 {len(items)} 个字段均使用题面允许的 SEC companyfacts 或美国财政部来源，并记录原始文件 SHA-256、期间、字段及申报号；未取当前股价、现成目标价或截止日后信息。

五年预测为透明示例：初始收入增长 {assumptions['initial_growth']:.2%}，逐年收敛至 2.5%；EBIT 利润率取 FY0 经营利润/收入（{values['operating_income']/values['revenue']:.2%}），有效税率取所得税/税前利润（{values['income_tax']/values['pretax_income']:.2%}）；WACC 为国债收益率加 5.5 个百分点，g=2.5%。D&A、CapEx 与经营 NWC 比率来自 FY0 取数，经营增长必须承担对应再投资。税前利润减所得税与合并净利润的差异为 {difference:.6f} 百万美元；容差为合并净利润的 2%，标签别名对账见 cross_validation.json。

未发生失败时不声称存在失败。若实际网络、来源缺失或字段冲突，必须在 sources.json 标记 failed 并说明处理，不能用零或当前网页信息静默补齐。本参考的本地快照验证不等同于联网访问或 sidecar 白名单生效证明；配置与实际运行状态分别记录。估值是开放模型结果，不是市场价格预测。""")


if __name__ == "__main__":
    main()
