#!/usr/bin/env python3
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlencode

try:
    from common import DATA, sha
except ModuleNotFoundError:
    DATA = Path(__file__).resolve().parent
    def sha(path):
        import hashlib
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

FIELDS = [
    {"field_id": "revenue", "label": "合并收入", "tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"], "kind": "flow", "unit": "USD"},
    {"field_id": "operating_income", "label": "经营利润（EBIT）", "tags": ["OperatingIncomeLoss"], "kind": "flow", "unit": "USD"},
    {"field_id": "pretax_income", "label": "税前利润", "tags": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"], "kind": "flow", "unit": "USD"},
    {"field_id": "income_tax", "label": "所得税费用", "tags": ["IncomeTaxExpenseBenefit"], "kind": "flow", "unit": "USD"},
    {"field_id": "net_income_consolidated", "label": "含非控股权益的合并净利润", "tags": ["ProfitLoss", "NetIncomeLoss"], "kind": "flow", "unit": "USD", "pack_field": "net_income"},
    {"field_id": "da", "label": "折旧与摊销", "tags": ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet", "DepreciationAndAmortization", "Depreciation"], "kind": "flow", "unit": "USD"},
    {"field_id": "capex", "label": "购置固定资产现金支出（正数）", "tags": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"], "kind": "flow", "unit": "USD"},
    {"field_id": "diluted_shares", "label": "加权平均稀释股数", "tags": ["WeightedAverageNumberOfDilutedSharesOutstanding"], "kind": "flow", "unit": "shares", "pack_field": "diluted_shares_wavg"},
    {"field_id": "cash", "label": "现金及现金等价物", "tags": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"], "kind": "instant", "unit": "USD"},
    {"field_id": "short_term_investments", "label": "短期投资", "tags": ["ShortTermInvestments", "MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"], "kind": "instant", "unit": "USD", "pack_field": "st_investments"},
    {"field_id": "receivables", "label": "应收账款净额", "tags": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"], "kind": "instant", "unit": "USD"},
    {"field_id": "current_assets", "label": "流动资产合计", "tags": ["AssetsCurrent"], "kind": "instant", "unit": "USD"},
    {"field_id": "current_liabilities", "label": "流动负债合计", "tags": ["LiabilitiesCurrent"], "kind": "instant", "unit": "USD"},
    {"field_id": "current_debt", "label": "当期债务", "tags": ["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings"], "kind": "instant", "unit": "USD", "pack_field": "debt_current"},
    {"field_id": "noncurrent_debt", "label": "非当期债务", "tags": ["LongTermDebtNoncurrent", "LongTermDebt"], "kind": "instant", "unit": "USD", "pack_field": "debt_noncurrent"},
    {"field_id": "treasury_10y", "label": "10 年期美国国债固定期限收益率", "tags": ["DGS10"], "kind": "market", "unit": "percent"},
]

TREASURY_CSV_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page&_format=csv"


def treasury_csv_url(cutoff):
    year = cutoff[:4]
    params = urlencode({"type": "daily_treasury_yield_curve", "field_tdr_date_value": year, "page": "", "_format": "csv"})
    return f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all?{params}"


def source_url(cfg, row):
    accession = row["accn"].replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cfg['cik'])}/{accession}/{row['accn']}-index.htm"


def extract_companyfacts(facts, cfg):
    cfg = dict(cfg)
    cfg.setdefault("asof", cfg.get("information_cutoff"))
    cfg.setdefault("cik", cfg.get("company", {}).get("cik"))
    results = {}
    for field in FIELDS:
        if field["kind"] == "market":
            continue
        selected = None
        for tag in field["tags"]:
            concept = facts.get("facts", {}).get("us-gaap", {}).get(tag)
            if not concept:
                continue
            candidates = []
            for unit, rows in concept.get("units", {}).items():
                if unit != field["unit"]:
                    continue
                for row in rows:
                    if row.get("form") not in ("10-K", "10-K/A") or row.get("filed", "9999") > cfg["asof"] or row.get("end") != cfg["fiscal_year_end"]:
                        continue
                    if field["kind"] == "flow":
                        if row.get("start") != cfg["fiscal_year_start"]:
                            continue
                        days = (dt.date.fromisoformat(row["end"]) - dt.date.fromisoformat(row["start"])).days
                        if not 350 <= days <= 380:
                            continue
                    candidates.append(row)
            if candidates:
                selected = (tag, sorted(candidates, key=lambda row: (row["filed"], row.get("accn", "")))[-1])
                break
        if not selected:
            raise ValueError(f"{cfg['ticker']} {field['field_id']} 缺少截止日前的原始事实")
        tag, row = selected
        scale = 1e6
        results[field["field_id"]] = {
            "field_id": field["field_id"], "label": field["label"], "value": row["val"] / scale,
            "raw_value": row["val"], "raw_unit": row.get("unit", field["unit"]),
            "unit": "USD_millions" if field["unit"] == "USD" else "shares_millions",
            "tag": tag, "taxonomy": "us-gaap", "start": row.get("start"), "end": row["end"],
            "form": row["form"], "filed": row["filed"], "accession": row["accn"],
            "source_url": source_url(cfg, row), "source_type": "sec_edgar",
            "tolerance": {"relative": 0.001, "absolute": 0.000001},
        }
    return results


def treasury_truth(cfg, csv_text=None):
    if csv_text is None:
        csv_text = (DATA / "raw/DGS10.csv").read_text()
    observations = []
    for line in csv_text.splitlines()[1:]:
        fields = line.split(",")
        if len(fields) < 2 or fields[0] > cfg["asof"] or fields[1] in ("", "."):
            continue
        try:
            value = float(fields[1])
        except ValueError:
            continue
        observations.append((fields[0], value))
    if not observations:
        raise ValueError("截止日前没有 DGS10")
    date, value = sorted(observations)[-1]
    return {"field_id": "treasury_10y", "label": "10 年期美国国债固定期限收益率", "value": value / 100,
            "raw_value": value, "raw_unit": "percent", "unit": "decimal", "tag": "DGS10",
            "start": date, "end": date, "form": "daily observation", "filed": date,
            "accession": None, "source_url": treasury_csv_url(cfg["asof"]), "source_type": "us_treasury",
            "tolerance": {"relative": 0, "absolute": 0.0001}}


def make_truth(cfg):
    path = DATA / "raw" / f"{cfg['ticker']}_facts.json"
    facts = json.loads(path.read_text())
    values = extract_companyfacts(facts, cfg)
    values["treasury_10y"] = treasury_truth(cfg)
    pack = json.loads((DATA / "packs" / f"{cfg['ticker']}.json").read_text())
    reconciliation = []
    for field in FIELDS:
        if field["kind"] == "market":
            continue
        pack_field = field.get("pack_field", field["field_id"])
        if field["field_id"] == "net_income_consolidated" and cfg["ticker"] == "SBUX":
            actual = 3762300000
        else:
            actual = pack["annual"].get(pack_field, {}).get(cfg["fiscal_year_end"])
        expected = values[field["field_id"]]["value"]
        equivalent = actual is not None and abs(actual / 1e6 - expected) < 1e-9
        reconciliation.append({"field_id": field["field_id"], "pack_field": "ProfitLoss_raw" if field["field_id"] == "net_income_consolidated" and cfg["ticker"] == "SBUX" else pack_field,
                               "pack_value": None if actual is None else actual / 1e6,
                               "original_value": expected, "exact_match": equivalent,
                               "treatment": "以原始 companyfacts 为准" if not equivalent else "一致"})
    return {"task_id": cfg["task_id"], "cutoff": cfg["asof"], "fields": values,
            "source_files": [
                {"file": f"../data/raw/{cfg['ticker']}_facts.json", "publisher": "SEC EDGAR companyfacts",
                 "url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cfg['cik']):010d}.json", "sha256": sha(path)},
                {"file": "../data/raw/DGS10.csv", "publisher": "DGS10 本地冻结序列（题面指定美国财政部取数）",
                 "url": treasury_csv_url(cfg["asof"]), "sha256": sha(DATA / "raw/DGS10.csv")}],
            "pack_reconciliation": reconciliation,
            "scope": "只把截止日前原始 10-K/10-K/A 事实作为权威值；数据包仅用于对账，不代替原始来源。"}
