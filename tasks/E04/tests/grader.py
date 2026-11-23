#!/usr/bin/env python3
import argparse
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from e_model import compute

DRIVERS = ("revenue_growth", "ebit_margin", "reinvestment_intensity", "discount_rate")


def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def close(a, b, tolerance=0.001):
    return finite(a) and finite(b) and abs(a - b) <= max(1e-7, abs(b) * tolerance)


def percentile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low = int(position)
    high = math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def recalc(path):
    directory = Path(tempfile.mkdtemp(prefix="dcf-e-recalc"))
    profile = Path(tempfile.mkdtemp(prefix="dcf-e-profile"))
    result = subprocess.run(["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--convert-to",
                             "xlsx:Calc MS Excel 2007 XML", "--outdir", str(directory), str(path)],
                            capture_output=True, text=True, timeout=180)
    target = directory / Path(path).name
    if not target.exists():
        raise RuntimeError("LibreOffice 重算失败：" + (result.stdout + result.stderr)[-400:])
    return target


def excel_model(path, keys):
    calculated = recalc(path)
    formula = load_workbook(path, data_only=False)
    values = load_workbook(calculated, data_only=True)
    for name in ("Outputs", "Assumptions", "Forecast", "DCF"):
        if name not in formula.sheetnames:
            raise ValueError("缺少工作表：" + name)
    out_f, out_v = formula["Outputs"], values["Outputs"]
    lookup = {out_f.cell(row, 1).value: row for row in range(2, out_f.max_row + 1)}
    output = {key: out_v.cell(lookup[key], 3).value for key in keys if key in lookup}
    cells = {key: out_f.cell(lookup[key], 3).value for key in keys if key in lookup}
    a = values["Assumptions"]
    assumptions = {a.cell(row, 1).value: a.cell(row, 2).value for row in range(2, a.max_row + 1) if a.cell(row, 1).value}
    f = values["Forecast"]
    forecast_lookup = {f.cell(row, 1).value: row for row in range(2, f.max_row + 1)}
    forecast = {}
    for key, row in forecast_lookup.items():
        for year in range(1, 6):
            forecast[f"{key}_y{year}"] = f.cell(row, year + 2).value
    for key, value in output.items():
        if key.endswith(tuple("_y" + str(year) for year in range(1, 6))) or key.startswith("residual_"):
            forecast[key] = value
    valuation = dict(assumptions)
    for key in ("enterprise_value", "equity_value", "value_per_share", "wacc", "terminal_growth", "diluted_shares"):
        valuation[key] = output.get(key)
    valuation["discount_years"] = [forecast.get(f"discount_years_y{year}") for year in range(1, 6)]
    valuation["terminal_year_fcff"] = forecast.get("fcff_y5")
    errors = []
    for sheet in values:
        for row in sheet:
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith(("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#NUM!")):
                    errors.append(sheet.title + "!" + cell.coordinate)
    return assumptions, forecast, valuation, output, {"form": "xlsx", "formula_cells": cells, "excel_errors": errors}


def run_recompute(directory, input_path, model, files):
    destination = Path(tempfile.mkdtemp(prefix="dcf-e-recompute-result", dir=directory))
    result = subprocess.run([sys.executable, str(files / "recompute.py"), "--input", str(input_path),
                             "--model", str(model), "--output", str(destination)],
                            capture_output=True, text=True, timeout=120)
    target = destination / "recomputed.json"
    if result.returncode or not target.exists():
        raise ValueError("recompute.py 执行失败：" + (result.stdout + result.stderr)[-400:])
    return json.loads(target.read_text())


def json_model(artifact, input_path):
    if not (artifact / "recompute.py").exists():
        raise ValueError("JSON 模型缺少 recompute.py")
    with tempfile.TemporaryDirectory(prefix="dcf-e-json") as tmp:
        directory = Path(tmp)
        files = directory / "scripts"
        files.mkdir()
        for path in artifact.glob("*.py"):
            shutil.copy2(path, files / path.name)
        declared = json.loads((artifact / "model.json").read_text())
        recomputed = run_recompute(directory, input_path, artifact / "model.json", files)
        assumptions = recomputed.get("assumptions", {})
        forecast = recomputed.get("forecast", {})
        valuation = recomputed.get("valuation", {})
        output = {**recomputed.get("historical", {}), **forecast, **valuation}
        for key in ("fcff_y1", "fcff_y5", "revenue_y1", "enterprise_value", "equity_value", "value_per_share"):
            group = "valuation" if key in ("enterprise_value", "equity_value", "value_per_share") else "forecast"
            if not close(declared.get(group, {}).get(key), recomputed.get(group, {}).get(key), 0.001):
                raise ValueError("声明模型与 recompute.py 不一致：" + key)
        perturbations = {}
        for key, delta in (("initial_growth", 0.01), ("steady_ebit_margin", 0.01), ("wacc", 0.005), ("terminal_growth", 0.002)):
            changed = json.loads(json.dumps(declared))
            changed["assumptions"][key] = changed["assumptions"].get(key, 0) + delta
            model_path = directory / (key + ".json")
            model_path.write_text(json.dumps(changed))
            perturbations[key] = run_recompute(directory, input_path, model_path, files)
        return assumptions, forecast, valuation, output, {"form": "json", "formula_cells": {}, "excel_errors": [], "perturbations": perturbations}


def perturb_excel(path, base_enterprise):
    results = {}
    for key, delta in (("wacc", 0.005), ("terminal_growth", 0.002)):
        workbook = load_workbook(path, data_only=False)
        sheet = workbook["Assumptions"]
        rows = {sheet.cell(row, 1).value: row for row in range(2, sheet.max_row + 1)}
        if key not in rows:
            return {}
        cell = sheet.cell(rows[key], 2)
        cell.value = ("=(" + cell.value[1:] + ")+" + str(delta)) if isinstance(cell.value, str) and cell.value.startswith("=") else cell.value + delta
        with tempfile.TemporaryDirectory(prefix="dcf-e-perturb") as tmp:
            changed = Path(tmp) / "model.xlsx"
            workbook.save(changed)
            calculated = load_workbook(recalc(changed), data_only=True)
            output = calculated["Outputs"]
            lookup = {output.cell(row, 1).value: row for row in range(2, output.max_row + 1)}
            results[key] = output.cell(lookup["enterprise_value"], 3).value
    return results


def correlation(x, y):
    if len(x) < 2:
        return 0
    sx, sy = statistics.stdev(x), statistics.stdev(y)
    if sx == 0 or sy == 0:
        return 0
    mx, my = statistics.fmean(x), statistics.fmean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / ((len(x) - 1) * sx * sy)


def grade(artifact, input_path, truth, spec, output_dir):
    artifact, output_dir = Path(artifact), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(input_path).read_text())
    checks = {}

    def check(item, passed, evidence=None, weight=3):
        checks[item] = {"passed": bool(passed), "evidence": evidence, "weight": weight, "method": "rule"}

    memo = (artifact / "memo.md").read_text(errors="replace") if (artifact / "memo.md").exists() else ""
    try:
        if spec["shape"] == "xlsx":
            if not (artifact / "model.xlsx").exists():
                raise ValueError("缺少 model.xlsx")
            assumptions, forecast, valuation, output, meta = excel_model(artifact / "model.xlsx", truth["output_keys"])
        else:
            if not (artifact / "model.json").exists():
                raise ValueError("缺少 model.json")
            assumptions, forecast, valuation, output, meta = json_model(artifact, input_path)
        check("E-deliver_model", True, meta["form"])
    except Exception as error:
        assumptions, forecast, valuation, output = {}, {}, {}, {}
        meta = {"form": spec["shape"], "formula_cells": {}, "excel_errors": [str(error)]}
        check("E-deliver_model", False, str(error)[:400])
    check("E-deliver_simulator", (artifact / "simulate.py").exists() and (artifact / "simulate.py").stat().st_size > 100)
    try:
        simulation = json.loads((artifact / "simulation.json").read_text())
        required = ("seed", "n_valid", "n_rejected", "drivers", "dependence", "trials", "statistics", "percentile_convention")
        check("E-deliver_trials", all(key in simulation for key in required))
    except Exception as error:
        simulation = {}
        check("E-deliver_trials", False, str(error)[:300])
    check("E-deliver_memo", bool(memo.strip()) and len(memo.split()) <= 700, len(memo.split()), weight=1)
    output = dict(output)
    stats = simulation.get("statistics", {}) if isinstance(simulation.get("statistics"), dict) else {}
    output.update({"mc_n": simulation.get("n_valid"), "mc_mean": stats.get("mean"), **{f"mc_p{q}": stats.get(f"p{q}") for q in (10, 25, 50, 75, 90)}})
    missing = [key for key in truth["output_keys"] if not finite(output.get(key))]
    check("01-KEYS", not missing, missing)
    history = truth["historical"]
    fy0 = data["fiscal_years"][-1]
    for item, key, field in (("E-hist_revenue", "hist_revenue_fy0", "revenue"), ("E-hist_ebit", "hist_ebit_fy0", "operating_income"), ("E-hist_eps", "hist_eps_fy0", "eps_diluted")):
        check(item, close(output.get(key), history[field][fy0], 0.001), output.get(key), weight=3 if field != "eps_diluted" else 1)
    quarters = truth.get("public_partial_periods", [])
    if quarters:
        actual_revenue = sum(row["revenue"] for row in quarters)
        actual_ebit = sum(row["operating_income"] for row in quarters)
        check("E-hist_partial_revenue", close(output.get("actual_partial_revenue_y1"), actual_revenue, 0.001), actual_revenue)
        check("E-hist_partial_residual_boundary", close(forecast.get("residual_revenue_y1"), (forecast.get("revenue_y1") or 0) - actual_revenue, 0.001))
        check("E-hist_partial_ebit", close(output.get("actual_partial_ebit_y1"), actual_ebit, 0.001))
    check("E-forecast_revenue", all(finite(forecast.get(f"revenue_y{year}")) and forecast[f"revenue_y{year}"] > 0 for year in range(1, 6)), weight=1)
    check("E-forecast_ebit", all(finite(forecast.get(f"ebit_y{year}")) and finite(forecast.get(f"revenue_y{year}")) and forecast[f"revenue_y{year}"] > 0 and -0.5 <= forecast[f"ebit_y{year}"] / forecast[f"revenue_y{year}"] <= 0.7 for year in range(1, 6)), weight=1)
    reinvestment_ok = True
    for year in range(1, 6):
        da, capex, delta = (forecast.get(f"{key}_y{year}") for key in ("da", "capex", "delta_nwc"))
        reinvestment_ok = reinvestment_ok and all(finite(x) for x in (da, capex, delta)) and close(forecast.get(f"reinvestment_component_y{year}"), da - capex - delta, 0.001) if all(finite(x) for x in (da, capex, delta)) else False
    check("E-forecast_reinvestment", reinvestment_ok)
    tax = assumptions.get("tax_rate")
    actual_ebit_y1 = output.get("actual_partial_ebit_y1", 0) if quarters else 0
    check("E-dcf_fcff", finite(tax) and 0 <= tax <= 0.5 and all(close(forecast.get(f"fcff_y{year}"), ((forecast.get(f"ebit_y{year}") or 0) - (actual_ebit_y1 if year == 1 else 0)) * (1 - tax) + (forecast.get(f"reinvestment_component_y{year}") or 0), 0.001) for year in range(1, 6)))
    times = data["reported_partial_period"]["timing"]["discount_years"]
    wacc, growth = assumptions.get("wacc"), assumptions.get("terminal_growth")
    check("E-dcf_discount", finite(wacc) and wacc > 0 and all(close(forecast.get(f"discount_factor_y{year}"), 1 / (1 + wacc) ** times[year - 1], 0.0001) for year in range(1, 6)) if finite(wacc) else False)
    enterprise = None
    if finite(wacc) and finite(growth) and wacc > growth and all(finite(forecast.get(f"fcff_y{year}")) and finite(forecast.get(f"discount_factor_y{year}")) for year in range(1, 6)):
        enterprise = sum(forecast[f"fcff_y{year}"] * forecast[f"discount_factor_y{year}"] for year in range(1, 6))
        enterprise += forecast["fcff_y5"] * (1 + growth) / (wacc - growth) * forecast["discount_factor_y5"]
    check("05-TV", close(valuation.get("enterprise_value"), enterprise, 0.002), enterprise)
    shares, debt, cash = assumptions.get("diluted_shares"), assumptions.get("net_debt"), assumptions.get("cash_and_investments")
    equity = enterprise + cash - debt if enterprise is not None and finite(cash) and finite(debt) else None
    check("05-BRIDGE", close(valuation.get("equity_value"), equity, 0.002))
    check("05-VPS", equity is not None and finite(shares) and shares > 0 and close(valuation.get("value_per_share"), equity / shares, 0.002))
    formula_cells = meta["formula_cells"]
    non_mc = [key for key in truth["output_keys"] if not key.startswith("mc_")]
    formula_ok = all(isinstance(formula_cells.get(key), str) and formula_cells[key].startswith("=") for key in non_mc) if meta["form"] == "xlsx" else bool(forecast)
    check("06-FORMULA", formula_ok)
    check("06-RECALC", not meta["excel_errors"], meta["excel_errors"])
    try:
        expected_forecast, expected_valuation = compute(data, assumptions)
        deterministic_fields = [f"{key}_y{year}" for year in range(1, 6) for key in ("revenue", "ebit", "eps", "da", "capex", "delta_nwc", "reinvestment_component", "fcff", "discount_factor")]
        differences = [key for key in deterministic_fields if not close(forecast.get(key), expected_forecast.get(key), 0.001)]
        check("E-deterministic_model", not differences and close(valuation.get("enterprise_value"), expected_valuation["enterprise_value"], 0.001), differences[:8])
    except Exception as error:
        check("E-deterministic_model", False, str(error)[:300])
    if enterprise is not None:
        try:
            if meta["form"] == "xlsx":
                changed = perturb_excel(artifact / "model.xlsx", enterprise)
                wacc_value, growth_value = changed.get("wacc"), changed.get("terminal_growth")
            else:
                changed = meta["perturbations"]
                wacc_value, growth_value = changed["wacc"]["valuation"]["enterprise_value"], changed["terminal_growth"]["valuation"]["enterprise_value"]
                check("E-operating_perturb", changed["initial_growth"]["forecast"]["revenue_y1"] > forecast["revenue_y1"] and changed["steady_ebit_margin"]["forecast"]["ebit_y1"] > forecast["ebit_y1"])
            check("E-formula_perturb_wacc", finite(wacc_value) and wacc_value < enterprise, wacc_value, weight=1)
            check("E-formula_perturb_g", finite(growth_value) and growth_value > enterprise, growth_value, weight=1)
        except Exception as error:
            check("E-formula_perturb_wacc", False, str(error)[:300], weight=1)
            check("E-formula_perturb_g", False, str(error)[:300], weight=1)
    else:
        check("E-formula_perturb_wacc", False, weight=1)
        check("E-formula_perturb_g", False, weight=1)
    trials = simulation.get("trials") if isinstance(simulation.get("trials"), list) else []
    valid = [row for row in trials if isinstance(row, dict) and finite(row.get("path_id")) and finite(row.get("value_per_share"))]
    check("07-PATHS", len(trials) >= spec["min_paths"] and len(valid) == len(trials) and len({row["path_id"] for row in valid}) == len(valid) and simulation.get("n_valid") == len(valid), len(valid))
    check("E-mc_seed", simulation.get("seed") == truth["mc_seed"], simulation.get("seed"), weight=1)
    distributions = simulation.get("drivers", {}) if isinstance(simulation.get("drivers"), dict) else {}
    distribution_details = {}
    for name in DRIVERS:
        entry = distributions.get(name, {})
        kind = entry.get("distribution")
        family = "normal" if isinstance(kind, str) and kind.startswith("normal") else kind
        parameters, bounds = entry.get("parameters", {}), entry.get("bounds", {})
        samples = [row.get(name) for row in valid]
        legal = family in ("normal", "triangular", "uniform", "lognormal", "beta") and isinstance(parameters, dict) and isinstance(bounds, dict)
        legal = legal and finite(bounds.get("min")) and finite(bounds.get("max")) and bounds["min"] < bounds["max"]
        required = {"normal": ("mu", "sigma"), "triangular": ("min", "max", "mode"), "uniform": ("min", "max"), "lognormal": ("mu", "sigma"), "beta": ("alpha", "beta")}.get(family, ())
        legal = legal and all(finite(parameters.get(key)) for key in required)
        if legal:
            legal = all(finite(x) and bounds["min"] - 1e-10 <= x <= bounds["max"] + 1e-10 for x in samples) and len(set(samples)) > 100
            if family in ("normal", "lognormal"):
                legal = legal and parameters["sigma"] > 0
            if family == "triangular":
                legal = legal and bounds["min"] <= parameters["min"] <= parameters["mode"] <= parameters["max"] <= bounds["max"]
            if family == "uniform":
                legal = legal and bounds["min"] <= parameters["min"] < parameters["max"] <= bounds["max"]
            if family == "beta":
                legal = legal and parameters["alpha"] > 0 and parameters["beta"] > 0
            if name == "discount_rate":
                legal = legal and finite(growth) and bounds["min"] > growth + 0.005
        if legal:
            mean, sd = statistics.fmean(samples), statistics.stdev(samples)
            theoretical = ((parameters["min"] + parameters["max"] + parameters["mode"]) / 3 if family == "triangular" else (parameters["min"] + parameters["max"]) / 2 if family == "uniform" else parameters.get("mu"))
            tolerance = max(0.025 * (bounds["max"] - bounds["min"]), 7 * sd / math.sqrt(len(samples)))
            legal = abs(mean - theoretical) <= tolerance
        distribution_details[name] = {"legal": legal, "distribution": kind}
    check("E-mc_distributions", all(row["legal"] for row in distribution_details.values()), distribution_details)
    dependence = simulation.get("dependence", {}) if isinstance(simulation.get("dependence"), dict) else {}
    realized = [[correlation([row.get(name) for row in valid], [row.get(other) for row in valid]) if all(finite(row.get(name)) and finite(row.get(other)) for row in valid) else 99 for other in DRIVERS] for name in DRIVERS]
    dependence_ok = False
    if dependence.get("type") == "independence" and dependence.get("explanation"):
        dependence_ok = all(abs(realized[i][j]) < 0.06 for i in range(4) for j in range(4) if i != j)
    matrix = dependence.get("matrix")
    if dependence.get("ordered_names") == list(DRIVERS) and isinstance(matrix, list) and len(matrix) == 4 and all(isinstance(row, list) and len(row) == 4 for row in matrix):
        dependence_ok = all(finite(matrix[i][j]) and abs(matrix[i][j] - realized[i][j]) <= 0.08 for i in range(4) for j in range(4))
        dependence_ok = dependence_ok and (abs(matrix[0][1]) >= 0.05 or dependence.get("type") == "independence")
    check("E-mc_dependence", dependence_ok, {"realized": realized})
    path_errors = []
    partial = data["reported_partial_period"]["type"] != "annual"
    if partial:
        base = sum(row["revenue"] for row in data["reported_partial_period"]["prior_year_quarters"])
    else:
        base = history["revenue"][fy0]
    initial_growth = assumptions.get("initial_growth")
    terminal_revenue_growth = assumptions.get("terminal_revenue_growth")
    for row in valid:
        trajectory = row.get("trajectory")
        if not isinstance(trajectory, list) or len(trajectory) != 5 or not all(finite(row.get(name)) for name in DRIVERS) or not finite(tax) or not finite(initial_growth) or not finite(terminal_revenue_growth) or not finite(growth) or not finite(shares) or shares <= 0 or not finite(debt) or not finite(cash):
            path_errors.append({"path": row.get("path_id"), "error": "缺少路径或模型数值"})
            continue
        revenue = base
        present_value = 0
        failed = False
        for year, annual in enumerate(trajectory, 1):
            revenue *= 1 + row["revenue_growth"]
            if partial and year > 1:
                first_growth = initial_growth
                revenue = history["revenue"][fy0] * (1 + first_growth) * (1 + row["revenue_growth"]) ** (year - 1)
            ebit = revenue * row["ebit_margin"]
            reinvestment = revenue * row["reinvestment_intensity"]
            fcff = ebit * (1 - tax) - reinvestment
            factor = 1 / (1 + row["discount_rate"]) ** times[year - 1]
            if not all(finite(annual.get(key)) for key in ("year", "revenue", "ebit", "reinvestment", "fcff", "discount_factor")):
                failed = True
                break
            if annual["year"] != year or not close(annual["revenue"], revenue, 0.002) or not close(annual["ebit"], ebit, 0.002) or not close(annual["reinvestment"], reinvestment, 0.002) or not close(annual["fcff"], fcff, 0.002) or not close(annual["discount_factor"], factor, 0.002):
                failed = True
                break
            present_value += fcff * factor
        if failed or row["discount_rate"] <= growth:
            path_errors.append({"path": row.get("path_id"), "error": "年度路径算术失败"})
            continue
        present_value += fcff * (1 + growth) / (row["discount_rate"] - growth) * factor
        expected_value = (present_value + cash - debt) / shares
        if not close(row["value_per_share"], expected_value, 0.005):
            path_errors.append({"path": row.get("path_id"), "submitted": row["value_per_share"], "independent": expected_value})
        if len(path_errors) >= 5:
            break
    check("E-mc_recompute", len(valid) >= spec["min_paths"] and not path_errors, path_errors)
    values = [row["value_per_share"] for row in valid]
    expected_stats = {f"p{int(q * 100)}": percentile(values, q) for q in (0.1, 0.25, 0.5, 0.75, 0.9)} if values else {}
    if values:
        expected_stats["mean"] = statistics.fmean(values)
    quantile_ok = bool(values) and all(close(stats.get(key), value, 1e-7) for key, value in expected_stats.items())
    if not quantile_ok and simulation.get("percentile_convention") == "nearest_r" and values:
        ordered = sorted(values)
        quantile_ok = all(close(stats.get(f"p{int(q * 100)}"), ordered[min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1)], 1e-7) for q in (0.1, 0.25, 0.5, 0.75, 0.9)) and close(stats.get("mean"), expected_stats["mean"], 1e-7)
    check("07-QUANTILE", len(values) >= spec["min_paths"] and quantile_ok)
    check("E-mc_not_degenerate", len(set(values)) > 100 and values and percentile(values, 0.1) < percentile(values, 0.9), weight=1)
    citations = []
    if "SEC_XBRL" in memo:
        numbers = []
        for token in re.findall(r"(?<![\d.])-?\d[\d,]*(?:\.\d+)?", memo):
            try:
                numbers.append(float(token.replace(",", "")))
            except ValueError:
                pass
        for period in set(re.findall(r"20\d{2}-\d{2}-\d{2}", memo)):
            for field, series in history.items():
                if period in series and isinstance(series[period], (int, float)):
                    for number in numbers:
                        if close(number, series[period], 0.002):
                            citations.append({"source": "SEC_XBRL", "period": period, "field": field, "value": number})
    check("E-evidence_numeric_citations", len(citations) >= 3, citations[:6], weight=1)
    check("E-evidence_limits", bool(re.search("不确定|局限|记忆泄漏", memo)) and bool(re.search("独立|相关", memo)), weight=1)
    simulator_rerun = {"status": "not_run"}
    if (artifact / "simulate.py").exists() and simulation:
        try:
            with tempfile.TemporaryDirectory(prefix="dcf-e-rerun") as tmp:
                directory = Path(tmp)
                model_name = "model.xlsx" if spec["shape"] == "xlsx" else "model.json"
                shutil.copy2(artifact / model_name, directory / model_name)
                if (artifact / "simulation_parameters.json").exists():
                    shutil.copy2(artifact / "simulation_parameters.json", directory / "simulation_parameters.json")
                    input_copy = directory / "inputs.json"
                    shutil.copy2(input_path, input_copy)
                    run_input = input_copy
                else:
                    run_input = input_path
                output_path = directory / "simulation.json"
                result = subprocess.run([sys.executable, str(artifact / "simulate.py"), "--input", str(run_input), "--model", str(directory / model_name), "--output", str(output_path)], capture_output=True, text=True, timeout=180)
                if result.returncode or not output_path.exists():
                    raise RuntimeError((result.stdout + result.stderr)[-400:])
                rerun = json.loads(output_path.read_text())
                rerun_values = [row["value_per_share"] for row in rerun.get("trials", [])]
                same = rerun.get("seed") == simulation.get("seed") and rerun.get("n_valid") == simulation.get("n_valid") and len(rerun_values) == len(values) and close(percentile(rerun_values, 0.5), percentile(values, 0.5), 1e-8)
                simulator_rerun = {"status": "passed" if same else "failed", "n": len(rerun_values)}
        except Exception as error:
            simulator_rerun = {"status": "failed", "error": str(error)[:400]}
    check("E-simulator_rerun", simulator_rerun["status"] == "passed", simulator_rerun)
    diagnostic = {}
    for year, actual in truth.get("future_actuals", {}).items():
        forecast_year = list(truth["future_actuals"]).index(year) + 1
        diagnostic[year] = {name: {"absolute_percentage_error": abs(forecast[f"{name}_y{forecast_year}"] - actual[field]) / max(1, abs(actual[field]))}
                            for name, field in (("revenue", "revenue"), ("ebit", "operating_income"), ("eps", "eps_diluted"))
                            if finite(forecast.get(f"{name}_y{forecast_year}")) and finite(actual.get(field)) and actual[field] != 0}
    prices = list(truth.get("future_prices", {}).values())
    market = {"future_price_p10_p90_coverage": percentile(values, 0.1) <= prices[-1] <= percentile(values, 0.9) if prices and values else None,
              "future_price_count": len(prices), "role": "diagnostic_only"}
    weight = sum(row["weight"] for row in checks.values())
    score = sum(row["weight"] for row in checks.values() if row["passed"]) / weight if weight else 0
    hard_gate_ids = ("E-deliver_model", "06-FORMULA", "06-RECALC", "E-formula_perturb_wacc", "E-formula_perturb_g", "E-deterministic_model")
    if quarters:
        hard_gate_ids += ("E-hist_partial_revenue", "E-hist_partial_residual_boundary", "E-hist_partial_ebit")
    gates = [item for item in hard_gate_ids if not checks.get(item, {}).get("passed", False)]
    if gates:
        score = 0
    result = {"schema_version": "dcf-v3-e-grade-v1", "task_id": truth["task_id"], "reward": round(score, 6),
              "mechanism_score": round(score, 6), "hard_gate_failures": gates, "checks": checks,
              "forecast_accuracy_diagnostic": diagnostic, "market_calibration_diagnostic": market,
              "nonmechanical_judgments": {"status": "not_run", "reason": "本验证未选择或执行 llm/agent rubric，不将缺失评审当作通过。"},
              "diagnostics_do_not_affect_reward": True}
    (output_dir / "details.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (output_dir / "reward.json").write_text(json.dumps({"reward": result["reward"], "mechanism_score": result["mechanism_score"]}, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--input", default=str(HERE / "inputs.json"))
    parser.add_argument("--truth", default=str(HERE / "truth.json"))
    parser.add_argument("--spec", default=str(HERE / "spec.json"))
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    truth = json.loads(Path(args.truth).read_text())
    spec = json.loads(Path(args.spec).read_text())
    result = grade(args.artifact_dir, args.input, truth, spec, args.output_dir)
    print(json.dumps({"reward": result["reward"], "failed": [key for key, value in result["checks"].items() if not value["passed"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
