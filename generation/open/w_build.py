#!/usr/bin/env python3
import json
from pathlib import Path

from common import DATA, ROOT, TASKS, blank_environment, dockerfiles, dump, sha, write
from w_truth import FIELDS, make_truth, treasury_csv_url

TASK_PLAN = {
    "W01": {"ticker": "AAPL", "cik": 320193, "name": "Apple Inc.", "ir": "https://investor.apple.com/", "fiscal_year": "FY2024", "fiscal_year_start": "2023-10-01", "fiscal_year_end": "2024-09-28", "asof": "2024-11-27", "treasury_date": "2024-11-27"},
    "W02": {"ticker": "COST", "cik": 909832, "name": "Costco Wholesale Corporation", "ir": "https://investor.costco.com/", "fiscal_year": "FY2024", "fiscal_year_start": "2023-09-04", "fiscal_year_end": "2024-09-01", "asof": "2024-10-31", "treasury_date": "2024-10-31"},
    "W03": {"ticker": "SBUX", "cik": 829224, "name": "Starbucks Corporation", "ir": "https://investor.starbucks.com/", "fiscal_year": "FY2024", "fiscal_year_start": "2023-10-02", "fiscal_year_end": "2024-09-29", "asof": "2024-11-27", "treasury_date": "2024-11-27"},
    "W04": {"ticker": "ADBE", "cik": 796343, "name": "Adobe Inc.", "ir": "https://www.adobe.com/investor-relations.html", "fiscal_year": "FY2024", "fiscal_year_start": "2023-12-02", "fiscal_year_end": "2024-11-29", "asof": "2025-02-14", "treasury_date": "2025-02-14"},
}

SEED_ASSUMPTIONS = {"W01": {"initial_growth": 0.06, "steady_ebit_margin": 0.31, "tax_rate": 0.16},
                    "W02": {"initial_growth": 0.07, "steady_ebit_margin": 0.037, "tax_rate": 0.25},
                    "W03": {"initial_growth": 0.06, "steady_ebit_margin": 0.15, "tax_rate": 0.24},
                    "W04": {"initial_growth": 0.09, "steady_ebit_margin": 0.32, "tax_rate": 0.20}}


def public_contract(cfg):
    fields = []
    for field in FIELDS:
        item = {"field_id": field["field_id"], "label": field["label"], "allowed_tags": field["tags"],
                "kind": field["kind"], "raw_unit": field["unit"]}
        if field["kind"] == "market":
            item.update({"observation_date": cfg["treasury_date"], "selection": "该日非空 DGS10 观测；若官方无当日值，只能用之前最近观测并披露实际日期",
                         "reported_unit": "decimal", "allowed_source_ids": ["UST_DAILY"]})
        elif field["kind"] == "flow":
            item.update({"start": cfg["fiscal_year_start"], "end": cfg["fiscal_year_end"], "fiscal_period": "FY",
                         "reported_unit": "USD_millions" if field["unit"] == "USD" else "shares_millions",
                         "allowed_source_ids": ["SEC_COMPANYFACTS", "COMPANY_IR_FILING"]})
        else:
            item.update({"end": cfg["fiscal_year_end"], "reported_unit": "USD_millions",
                         "allowed_source_ids": ["SEC_COMPANYFACTS", "COMPANY_IR_FILING"]})
        fields.append(item)
    return {
        "schema_version": "dcf-v3-w-retrieval-v1", "task_id": cfg["task_id"],
        "company": {"ticker": cfg["ticker"], "cik": cfg["cik"], "name": cfg["name"]},
        "information_cutoff": cfg["asof"], "fiscal_year": cfg["fiscal_year"],
        "fiscal_year_start": cfg["fiscal_year_start"], "fiscal_year_end": cfg["fiscal_year_end"],
        "required_fields": fields,
        "allowed_sources": [
            {"source_id": "SEC_COMPANYFACTS", "publisher": "SEC EDGAR", "domains": ["data.sec.gov", "www.sec.gov"],
             "url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cfg['cik']):010d}.json",
             "scope": "只取 filed 不晚于截止日的 10-K/10-K/A 事实；记录 tag、期间、form、filed、accession 与 URL。"},
            {"source_id": "COMPANY_IR_FILING", "publisher": cfg["name"] + " 投资者关系",
             "domains": [cfg["ir"].split("/")[2], "s22.q4cdn.com", "s201.q4cdn.com", "d18rn0p25nwr6d.cloudfront.net"],
             "url": cfg["ir"], "scope": "用于取回同一 10-K 或作为第二来源核验；必须是截止日前已公开的文件。SEC XBRL 与 IR 转载同一申报不是独立会计事实。"},
            {"source_id": "UST_DAILY", "publisher": "美国财政部", "domains": ["home.treasury.gov"],
             "url": treasury_csv_url(cfg["asof"]), "scope": "Daily Treasury Par Yield Curve Rates 的 10 Yr 字段；百分数换算为小数。"},
        ],
        "prohibited": ["自由搜索当前股价或历史股价", "现成目标价", "市场一致预期", "截止日后才公开的信息", "未披露来源的数据补零"],
        "fetch_failure_schema": {"field_id": "字段 ID", "status": "failed", "value": None,
                                 "source_url": "尝试过的允许 URL", "error": "HTTP/解析/缺失/冲突的简明原因",
                                 "action": "不得猜测；不得用当前网站信息替换截止日快照"},
        "valuation_convention": {
            "forecast_years": 5, "growth": "FY1 使用 initial_growth，FY2–FY5 线性收敛至 terminal_growth",
            "ebit_margin": "预测期保持 steady_ebit_margin", "da_capex": "每年收入乘相应比率",
            "nwc": "经营 NWC=流动资产−现金−短期投资−(流动负债−当期债务)；FY1 ΔNWC=FY0 NWC×(FY1 收入/FY0 收入−1)，其后为本年减上年",
            "fcff": "EBIT×(1−tax_rate)+D&A−CapEx−ΔNWC", "discount_years": [1, 2, 3, 4, 5],
            "terminal": "Gordon，FY5 FCFF×(1+g)/(WACC−g) 再折现五年",
            "equity": "股权价值=企业价值+现金+短期投资−当期债务−非当期债务；每股价值除以加权平均稀释股数",
            "assumptions": "initial_growth、steady_ebit_margin、tax_rate、da_to_revenue、capex_to_revenue、wacc、terminal_growth 为透明开放假设；WACC>g，债务与现金的口径不得重复。",
        },
        "deliverables": ["model.xlsx", "sources.json", "cross_validation.json", "retrieval_map.json", "memo.md"],
        "network": {"declared_mode": "IPv4 sidecar allowlist", "enforcement_status": "配置已提供；是否生效仅以运行验证记录为准，不由本文件声称已生效。"},
    }


def instruction(cfg, contract):
    rows = []
    for field in contract["required_fields"]:
        period = field.get("observation_date") or ((field.get("start", "") + " 至 ") if field.get("start") else "截至 ") + field["end"]
        rows.append(f"| `{field['field_id']}` | {field['label']} | {period} | {field['reported_unit']} | {'、'.join(field['allowed_tags'])} |")
    return f"""# {cfg['name']}（{cfg['ticker']}）：限定来源取数与五年 DCF

信息截止日为 **{cfg['asof']}**，建模基准财年为 **{cfg['fiscal_year']}**。必须先从指定来源取数再建模，不得先猜结果后补来源。所有题面、取数记录、模型标签和 memo 均用中文；语义 ID 与 XBRL 标签保留英文。

## 允许来源与禁止事项

1. SEC EDGAR companyfacts：`{contract['allowed_sources'][0]['url']}`；也可使用 SEC Archives 中截止日前已申报的原始 10-K/10-K/A。
2. 公司 IR：`{cfg['ir']}`，仅可核对同一期间的原始申报；同一 XBRL 事实与 IR 转载不构成两个独立会计事实。
3. 美国财政部日度收益率：`{contract['allowed_sources'][2]['url']}`，取 **{cfg['treasury_date']}** 的 10 Yr，如该日官方无值则用之前最近观测并写明实际日期。4.25% 在模型中写 0.0425。

仅允许上述 SEC、公司 IR（含申报文件必要的 CDN）和财政部域名。禁止自由搜索当前或历史股价、现成目标价、市场一致预期及截止日后信息；禁止用搜索摘要或第三方财经网站代替原始来源。历史权威真值按 filed≤截止日的 10-K 事实评定，不能取后来重述的同一期间值。

## 必须取回的数据

| 语义 ID | 数据项 | 期间 | 提交单位 | 允许标签（按顺序使用首个有合规事实的标签） |
|---|---|---|---|---|
{chr(10).join(rows)}

金额须换算为百万美元，股数换算为百万股。`net_income_consolidated` 是含非控股权益的合并净利润（优先 ProfitLoss），不得与归母净利润混用。资本开支用现金流出正数。缺失不是零：取数失败必须在 sources.json 记录 failed、允许 URL、错误及处理，不得编造或静默补零。

## 提交与公式要求

- `sources.json`：`items` 数组逐项覆盖上表，含 `field_id/value/unit/period_start/period_end/source_id/source_url/source_file/field/form/filed/accession/observed_at/status/error`。成功项必须含实际数值、允许域名 URL、正确期间与字段、申报号和 filed；`observed_at` 是实际取数日，不是申报日。
- `cross_validation.json`：`checks` 数组至少包含 `pretax_to_net_income`，计算 `pretax_income−income_tax−net_income_consolidated` 的 `difference`，引用来源表中三个字段。允许 `abs(difference)<=max(0.01, abs(net_income_consolidated)*0.02)`，超出或缺失必须在 memo 披露，不能强行改成零。
- `retrieval_map.json`：`items` 数组逐项含 `field_id/source_item_index/sheet/cell/used_by`。工作簿 `Sources` 页 A/B/C 列必须是 field_id、取数值、单位，且每个取数字段在 Forecast/Assumptions/DCF 中有活公式实际引用；不能把取数表摆在一旁、在别处另填历史值。
- `model.xlsx`：`Sources`、`Assumptions`、`Forecast`、`DCF`、`Outputs` 五页。Assumptions A/B 列放经营假设；Forecast A 列放语义键、C:G 为 FY1–FY5，含 revenue、ebit、da、capex、delta_nwc、reinvestment_component、fcff、discount_factor；DCF 计算显性期现值、Gordon 终值及股权桥；Outputs A/C 列输出 `enterprise_value/equity_value/value_per_share`。预测、再投资、折现和输出必须是活公式，并能通过 LibreOffice 重算与 WACC/g 扰动。
- `memo.md`：用中文说明实际取数日期、来源、开放预测理由、交叉验证差异及所有失败/冲突；披露“配置存在”不等于“白名单已经验证生效”。不需要也不得寻找股价来判断 DCF 是否合理。

## 模型口径

{json.dumps(contract['valuation_convention'], ensure_ascii=False, indent=2)}

公开合同 `/app/data/retrieval_contract.json` 包含相同字段、允许来源和公式约定。运行网络由 IPv4 sidecar 白名单限制，配置已写入 environment/docker-compose.yaml 和 task.toml；生效状态只能根据运行时探测报告说明。独立评分器会按隐藏原始 SEC 快照和容差核验取数值、来源/期间/字段、交叉勾稽及模型引用链，并重算工作簿。未执行的语言与禁止来源语义评审不会自动算通过。
"""


def build(task_id):
    cfg = dict(TASK_PLAN[task_id])
    cfg["task_id"] = task_id
    task = TASKS / task_id
    blank_environment(task)
    contract = public_contract(cfg)
    truth = make_truth({**contract, "ticker": cfg["ticker"], "cik": cfg["cik"], "asof": cfg["asof"]})
    dump(task / "environment/data/retrieval_contract.json", contract)
    dump(task / "environment/data/inputs.json", contract)
    dump(task / "tests/truth.json", truth)
    dump(task / "tests/inputs.json", contract)
    write(task / "instruction.md", instruction(cfg, contract))
    spec = {**cfg, "family": "W", "schema_version": "dcf-v3-task-v1", "language": "zh-CN",
            "required_fields": [field["field_id"] for field in FIELDS],
            "allowed_sources": [{"source_id": source["source_id"], "domains": source["domains"], "url": source["url"]} for source in contract["allowed_sources"]],
            "required_artifacts": ["model.xlsx", "sources.json", "cross_validation.json", "retrieval_map.json", "memo.md"],
            "valuation_assumptions": SEED_ASSUMPTIONS[task_id],
            "source_snapshot_sha256": {row["file"]: row["sha256"] for row in truth["source_files"]},
            "network": {"mode": "allowlist", "sidecar": "dcf-ipv4-gost-egress:v1", "configured": True,
                        "verified": False, "status": "not_verified_by_generation"},
            "nonmechanical_status": "W-NOFORBID 与 W-FAILURE 需另行语义/代理评审，本次机械评分不自动给分。"}
    dump(task / "spec.json", spec)
    dump(task / "tests/spec.json", spec)
    dockerfiles(task)
    allowed = sorted({host for source in contract["allowed_sources"] for host in source["domains"]})
    write(task / "environment/docker-compose.yaml", f'''services:
  dcf-egress-firewall:
    image: dcf-ipv4-gost-egress:v1
    build:
      context: {ROOT.parent.parent / 'dcf_factory/ipv4_egress/gost'}
      dockerfile: Dockerfile
    entrypoint: ["/opt/egress-sidecar/entrypoint.sh"]
    environment:
      EGRESS_CONTROL_INITIAL_NETWORK_MODE: allowlist
      EGRESS_CONTROL_INITIAL_ALLOWED_HOSTS: "{' '.join(allowed)}"
    init: true
    cap_add: [NET_ADMIN, NET_RAW]
    healthcheck:
      test: ["CMD", "test", "-f", "/tmp/dcf-egress-ready"]
      interval: 1s
      timeout: 5s
      retries: 30
  main:
    network_mode: service:dcf-egress-firewall
    depends_on:
      dcf-egress-firewall:
        condition: service_healthy
''')
    host_array = ", ".join(json.dumps(host) for host in allowed)
    write(task / "task.toml", f'''schema_version = "1.4"
artifacts = ["/app/output"]
[metadata]
category = "dcf-restricted-retrieval"
difficulty = "very-hard"
network = "allowlist-configured-runtime-verification-required"
network_policy = "IPv4 GOST sidecar；配置文件存在不代表已验证生效，详见 open/validation.json"
disable_web_search = true
tags = ["W", "{cfg['ticker']}", "SEC", "Treasury", "allowlist"]
[agent]
timeout_sec = 5400.0
network_mode = "allowlist"
allowed_hosts = [{host_array}]
[verifier]
timeout_sec = 1800.0
environment_mode = "separate"
[verifier.environment]
network_mode = "no-network"
[environment]
network_mode = "allowlist"
allowed_hosts = [{host_array}]
build_timeout_sec = 900.0
cpus = 2
memory_mb = 4096
storage_mb = 4096
''')
    write(task / "tests/grader.py", (ROOT / "w_grader.py").read_text())
    write(task / "tests/test.sh", "#!/bin/bash\nset -u\nmkdir -p /logs/verifier\ncd /tests\npython3 grader.py --input /tests/inputs.json --truth /tests/truth.json --spec /tests/spec.json --artifact-dir /app/output --output-dir /logs/verifier > /logs/verifier/grader.log 2>&1\n", executable=True)
    write(task / "solution/reference.py", (ROOT / "w_reference.py").read_text())
    write(task / "solution/w_retrieval.py", (ROOT / "w_retrieval.py").read_text())
    write(task / "solution/w_truth.py", (ROOT / "w_truth.py").read_text())
    write(task / "solution/w_workbook.py", (ROOT / "w_workbook.py").read_text())
    write(task / "solution/solve.sh", "#!/bin/bash\nset -euo pipefail\nmkdir -p /app/output\npython3 /solution/reference.py --input /app/data/retrieval_contract.json --output /app/output\n", executable=True)
    return {"task_id": task_id, "family": "W", "ticker": cfg["ticker"], "cutoff": cfg["asof"],
            "required_fields": len(FIELDS), "source_files": truth["source_files"]}
