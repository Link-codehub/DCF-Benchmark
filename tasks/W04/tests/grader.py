#!/usr/bin/env python3
import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from openpyxl import load_workbook


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def close(left, right, tolerance=0.001, absolute=1e-7):
    return finite(left) and finite(right) and abs(left - right) <= max(absolute, abs(right) * tolerance)


def recalc(path):
    directory = Path(tempfile.mkdtemp(prefix="dcf-w-recalc"))
    profile = Path(tempfile.mkdtemp(prefix="dcf-w-profile"))
    result = subprocess.run(["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--convert-to",
                             "xlsx:Calc MS Excel 2007 XML", "--outdir", str(directory), str(path)],
                            capture_output=True, text=True, timeout=180)
    target = directory / Path(path).name
    if not target.exists():
        raise RuntimeError("LibreOffice 未生成重算文件：" + (result.stdout + result.stderr)[-400:])
    return target


def rows(sheet):
    return {sheet.cell(row, 1).value: row for row in range(2, sheet.max_row + 1) if sheet.cell(row, 1).value}


def workbook_map(workbook, sheet_name, column=2):
    sheet = workbook[sheet_name]
    lookup = rows(sheet)
    return {key: sheet.cell(row, column).value for key, row in lookup.items()}


def perturb(path):
    results = {}
    for key, delta in (("wacc", 0.005), ("terminal_growth", 0.002)):
        workbook = load_workbook(path, data_only=False)
        assumptions = workbook["Assumptions"]
        lookup = rows(assumptions)
        cell = assumptions.cell(lookup[key], 2)
        cell.value = f"=({cell.value[1:]})+{delta}" if isinstance(cell.value, str) and cell.value.startswith("=") else cell.value + delta
        with tempfile.TemporaryDirectory(prefix="dcf-w-perturb") as tmp:
            changed = Path(tmp) / "model.xlsx"
            workbook.save(changed)
            calculated = load_workbook(recalc(changed), data_only=True)
            results[key] = workbook_map(calculated, "Outputs", 3).get("enterprise_value")
    return results


def grade(artifact, contract, truth, spec, output_dir):
    artifact, output_dir = Path(artifact), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checks = {}
    def check(item, passed, evidence=None, weight=3):
        checks[item] = {"passed": bool(passed), "evidence": evidence, "weight": weight, "method": "rule"}
    def load(name):
        try:
            return json.loads((artifact / name).read_text())
        except Exception:
            return {}
    sources = load("sources.json")
    cross = load("cross_validation.json")
    mapping = load("retrieval_map.json")
    memo = (artifact / "memo.md").read_text(errors="replace") if (artifact / "memo.md").exists() else ""
    required = {field["field_id"]: field for field in contract["required_fields"]}
    expected = truth["fields"]
    source_rows = sources.get("items") if isinstance(sources.get("items"), list) else []
    indexed = {}
    duplicates = []
    for row in source_rows:
        field_id = row.get("field_id") if isinstance(row, dict) else None
        if field_id in indexed:
            duplicates.append(field_id)
        if isinstance(row, dict) and field_id:
            indexed[field_id] = row
    missing = [key for key in required if key not in indexed]
    value_failures, source_failures = [], []
    allowed = {host for source in contract["allowed_sources"] for host in source["domains"]}
    for field_id, requirement in required.items():
        row = indexed.get(field_id, {})
        truth_row = expected[field_id]
        tolerance = truth_row["tolerance"]
        if not close(row.get("value"), truth_row["value"], tolerance["relative"], tolerance["absolute"]) or row.get("status") != "success" or row.get("unit") != requirement["reported_unit"]:
            value_failures.append(field_id)
        url = row.get("source_url", "")
        host = urlsplit(url).hostname or ""
        permitted = host in allowed and urlsplit(url).scheme == "https"
        correct_period = row.get("period_end") == truth_row["end"]
        if requirement["kind"] == "flow":
            correct_period = correct_period and row.get("period_start") == truth_row["start"]
        correct_tag = row.get("field") == truth_row["tag"] or row.get("field") in requirement["allowed_tags"]
        cutoff_ok = not row.get("filed") or row.get("filed") <= contract["information_cutoff"]
        provenance = bool(row.get("source_file") and row.get("observed_at"))
        if field_id != "treasury_10y":
            provenance = provenance and row.get("accession") == truth_row["accession"] and row.get("form") in ("10-K", "10-K/A")
        if not all((permitted, correct_period, correct_tag, cutoff_ok, provenance)):
            source_failures.append({"field_id": field_id, "url_allowed": permitted, "period": correct_period,
                                    "tag": correct_tag, "cutoff": cutoff_ok, "provenance": provenance})
    check("W-VALUE", not duplicates and not missing and not value_failures, {"missing": missing, "incorrect": value_failures, "duplicates": duplicates})
    check("W-SOURCE", not duplicates and not missing and not source_failures, source_failures)
    cross_checks = cross.get("checks") if isinstance(cross.get("checks"), list) else []
    recon = next((row for row in cross_checks if row.get("check_id") == "pretax_to_net_income"), {})
    inputs = recon.get("inputs", {})
    expected_difference = expected["pretax_income"]["value"] - expected["income_tax"]["value"] - expected["net_income_consolidated"]["value"]
    difference_ok = close(recon.get("difference"), expected_difference, 1e-8, 1e-6)
    inputs_ok = all(close(inputs.get(key), expected[key]["value"], 0.001) for key in ("pretax_income", "income_tax", "net_income_consolidated"))
    tolerance = recon.get("tolerance")
    disclosed = abs(expected_difference) <= max(0.01, abs(expected["net_income_consolidated"]["value"]) * 0.02) or "差异" in memo
    check("W-CROSS", difference_ok and inputs_ok and finite(tolerance) and tolerance >= 0 and disclosed, {"expected_difference": expected_difference, "submitted": recon.get("difference")})
    meta = {}
    try:
        if not (artifact / "model.xlsx").exists():
            raise ValueError("缺少 model.xlsx")
        formula = load_workbook(artifact / "model.xlsx", data_only=False)
        calculated_path = recalc(artifact / "model.xlsx")
        values = load_workbook(calculated_path, data_only=True)
        for sheet in ("Sources", "Assumptions", "Forecast", "DCF", "Outputs"):
            if sheet not in formula.sheetnames:
                raise ValueError("缺少工作表：" + sheet)
        meta["formula"] = formula
        meta["values"] = values
        check("01-FILE", True)
    except Exception as error:
        check("01-FILE", False, str(error)[:400])
    used_failures = []
    map_rows = mapping.get("items") if isinstance(mapping.get("items"), list) else []
    map_index = {row.get("field_id"): row for row in map_rows if isinstance(row, dict) and row.get("field_id")}
    if meta:
        formulas, values = meta["formula"], meta["values"]
        source_sheet, value_source = formulas["Sources"], values["Sources"]
        sheet_lookup = rows(source_sheet)
        actual_references = {key: [] for key in required}
        for sheet_name in ("Assumptions", "Forecast", "DCF"):
            for row in formulas[sheet_name].iter_rows():
                for cell in row:
                    if cell.data_type == "f":
                        for field_id, field_row in sheet_lookup.items():
                            if f"Sources!$B${field_row}" in cell.value:
                                actual_references.setdefault(field_id, []).append(f"{sheet_name}!{cell.coordinate}")
        for field_id in required:
            row = map_index.get(field_id, {})
            source_index = row.get("source_item_index")
            source_row = source_rows[source_index] if isinstance(source_index, int) and not isinstance(source_index, bool) and 0 <= source_index < len(source_rows) else {}
            cell = row.get("cell", "")
            coordinate_ok = row.get("sheet") == "Sources" and cell.startswith("B") and cell[1:].isdigit()
            if coordinate_ok:
                row_number = int(cell[1:])
                coordinate_ok = source_sheet.cell(row_number, 1).value == field_id and source_sheet.cell(row_number, 2).data_type != "f"
            value_ok = close(value_source.cell(int(cell[1:]), 2).value, expected[field_id]["value"], 0.001) if coordinate_ok else False
            if not (coordinate_ok and value_ok and source_row.get("field_id") == field_id and actual_references.get(field_id) and set(row.get("used_by", [])) == set(actual_references[field_id])):
                used_failures.append({"field_id": field_id, "actual_references": actual_references.get(field_id), "declared": row.get("used_by")})
    else:
        used_failures = list(required)
    check("W-USED", not used_failures and len(map_index) == len(required), used_failures)
    outputs, forecast, assumptions = {}, {}, {}
    if meta:
        values = meta["values"]
        outputs = workbook_map(values, "Outputs", 3)
        assumptions = workbook_map(values, "Assumptions")
        forecast_sheet = values["Forecast"]
        lookup = rows(forecast_sheet)
        for key, row in lookup.items():
            for year in range(1, 6):
                forecast[f"{key}_y{year}"] = forecast_sheet.cell(row, year + 2).value
    tax, wacc, g = assumptions.get("tax_rate"), assumptions.get("wacc"), assumptions.get("terminal_growth")
    valuation_ok = True
    enterprise = None
    if finite(tax) and 0 <= tax <= 0.5 and finite(wacc) and finite(g) and wacc > g:
        for year in range(1, 6):
            row = {key: forecast.get(f"{key}_y{year}") for key in ("revenue", "ebit", "da", "capex", "delta_nwc", "reinvestment_component", "fcff", "discount_factor")}
            valuation_ok = valuation_ok and all(finite(value) for value in row.values()) and close(row["reinvestment_component"], row["da"] - row["capex"] - row["delta_nwc"], 0.001) and close(row["fcff"], row["ebit"] * (1 - tax) + row["reinvestment_component"], 0.001) and close(row["discount_factor"], 1 / (1 + wacc) ** year, 0.001)
        enterprise = sum(forecast[f"fcff_y{year}"] / (1 + wacc) ** year for year in range(1, 6)) + forecast["fcff_y5"] * (1 + g) / (wacc - g) / (1 + wacc) ** 5
    else:
        valuation_ok = False
    operating_ok = all(finite(forecast.get(f"revenue_y{year}")) and forecast[f"revenue_y{year}"] > 0 for year in range(1, 6))
    expected_margin = expected["operating_income"]["value"] / expected["revenue"]["value"]
    operating_ok = operating_ok and close(assumptions.get("steady_ebit_margin"), expected_margin, 1e-8)
    if operating_ok:
        for year in range(1, 6):
            expected_revenue = expected["revenue"]["value"] * (1 + assumptions["initial_growth"]) if year == 1 else forecast.get(f"revenue_y{year - 1}", 0) * (1 + assumptions["initial_growth"] + (g - assumptions["initial_growth"]) * (year - 1) / 4)
            operating_ok = operating_ok and close(forecast.get(f"revenue_y{year}"), expected_revenue, 0.0001)
            operating_ok = operating_ok and close(forecast.get(f"ebit_y{year}"), forecast.get(f"revenue_y{year}", 0) * expected_margin, 0.0001)
    check("W-OPERATING-RECALC", operating_ok)
    check("05-FCFF", valuation_ok)
    check("05-TV", close(outputs.get("enterprise_value"), enterprise, 0.001), enterprise)
    equity = enterprise + expected["cash"]["value"] + expected["short_term_investments"]["value"] - expected["current_debt"]["value"] - expected["noncurrent_debt"]["value"] if enterprise is not None else None
    check("05-BRIDGE", close(outputs.get("equity_value"), equity, 0.001), equity)
    check("05-VPS", equity is not None and close(outputs.get("value_per_share"), equity / expected["diluted_shares"]["value"], 0.001))
    formula_ok = bool(meta)
    if meta:
        output_sheet = meta["formula"]["Outputs"]
        formula_ok = all(output_sheet.cell(row, 3).data_type == "f" for row in range(2, output_sheet.max_row + 1))
        for row in meta["formula"]["Forecast"].iter_rows(min_row=2, min_col=3, max_col=7):
            formula_ok = formula_ok and all(cell.data_type == "f" for cell in row)
    check("06-FORMULA", formula_ok)
    check("06-RECALC", bool(meta) and all(finite(outputs.get(key)) for key in ("enterprise_value", "equity_value", "value_per_share")))
    if meta and enterprise is not None:
        try:
            changed = perturb(artifact / "model.xlsx")
            check("06-PERTURB1", finite(changed.get("wacc")) and changed["wacc"] < enterprise, changed.get("wacc"))
            check("06-PERTURB2", finite(changed.get("terminal_growth")) and changed["terminal_growth"] > enterprise, changed.get("terminal_growth"))
        except Exception as error:
            check("06-PERTURB1", False, str(error)[:400])
            check("06-PERTURB2", False, str(error)[:400])
    else:
        check("06-PERTURB1", False)
        check("06-PERTURB2", False)
    if meta:
        try:
            changed_workbook = load_workbook(artifact / "model.xlsx", data_only=False)
            changed_sources = changed_workbook["Sources"]
            source_lookup = rows(changed_sources)
            revenue_cell = changed_sources.cell(source_lookup["revenue"], 2)
            revenue_cell.value = revenue_cell.value * 1.05
            changed_sources.cell(source_lookup["operating_income"], 2).value *= 1.05
            with tempfile.TemporaryDirectory(prefix="dcf-w-source-perturb") as tmp:
                changed_path = Path(tmp) / "model.xlsx"
                changed_workbook.save(changed_path)
                changed_values = load_workbook(recalc(changed_path), data_only=True)
                changed_enterprise = workbook_map(changed_values, "Outputs", 3).get("enterprise_value")
                changed_revenue = workbook_map(changed_values, "Forecast", 3).get("revenue")
            check("W-SOURCE-PERTURB", finite(changed_enterprise) and changed_enterprise > enterprise and close(changed_revenue, forecast["revenue_y1"] * 1.05, 0.001), {"enterprise_value": changed_enterprise, "revenue_y1": changed_revenue})
        except Exception as error:
            check("W-SOURCE-PERTURB", False, str(error)[:400])
    else:
        check("W-SOURCE-PERTURB", False)
    declared_failures = sources.get("failures", []) if isinstance(sources.get("failures"), list) else []
    failed_items = [row for row in source_rows if row.get("status") == "failed"]
    disclosure = all(row.get("error") and row.get("action") for row in failed_items + declared_failures)
    check("W-FAILURE-RECORD", disclosure, {"failed_items": len(failed_items), "memo_present": bool(memo.strip())}, weight=1)
    weight = sum(row["weight"] for row in checks.values())
    score = sum(row["weight"] for row in checks.values() if row["passed"]) / weight if weight else 0
    gates = [key for key in ("01-FILE", "W-VALUE", "W-SOURCE", "W-USED", "06-FORMULA", "06-RECALC", "06-PERTURB1", "06-PERTURB2", "W-SOURCE-PERTURB", "W-OPERATING-RECALC") if not checks.get(key, {}).get("passed")]
    if gates:
        score = 0
    result = {"schema_version": "dcf-v3-w-grade-v1", "task_id": spec["task_id"], "reward": round(score, 6),
              "mechanism_score": round(score, 6), "hard_gate_failures": gates, "checks": checks,
              "nonmechanical_judgments": {"W-NOFORBID": {"status": "not_run", "reason": "禁止来源与截止日使用需独立代理检查全部取数行为；仅验证已声明来源不代表完整行为审计。"},
                                           "W-FAILURE": {"status": "not_run", "reason": "memo 语义说明需独立 llm 评审，未执行不记通过。"}},
              "source_truth_scope": "仅核验截止日前原始 SEC 快照与 DGS10 本地序列，不把生成器本地验证视为候选联网成功。"}
    (output_dir / "details.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (output_dir / "reward.json").write_text(json.dumps({"reward": result["reward"], "mechanism_score": result["mechanism_score"]}, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--truth", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = grade(args.artifact_dir, json.load(open(args.input)), json.load(open(args.truth)), json.load(open(args.spec)), args.output_dir)
    print(json.dumps({"reward": result["reward"], "failed": [key for key, value in result["checks"].items() if not value["passed"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
