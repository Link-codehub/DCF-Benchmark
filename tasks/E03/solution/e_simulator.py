#!/usr/bin/env python3
import argparse
import json
import math
import random
import statistics
from pathlib import Path
from openpyxl import load_workbook

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--model", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
data = json.load(open(args.input))
if args.model.endswith(".json"):
    assumptions = json.load(open(args.model))["assumptions"]
else:
    workbook = load_workbook(args.model, data_only=False)
    sheet = workbook["Assumptions"]
    assumptions = {sheet.cell(row, 1).value: sheet.cell(row, 2).value
                   for row in range(2, sheet.max_row + 1) if sheet.cell(row, 1).value}
seed = 1729 + int(data["task_id"][1:]) * 101
rng = random.Random(seed)
partial = data["reported_partial_period"]
fy0 = data["fiscal_years"][-1]
base_revenue = (data["historical"]["revenue"][fy0] if partial["type"] == "annual"
                else sum(row["revenue"] for row in partial["prior_year_quarters"]))
discount_years = partial["timing"]["discount_years"]
tax = assumptions["tax_rate"]
g = assumptions["terminal_growth"]
rho = assumptions["mc_growth_margin_correlation"]
trials, values = [], []


def percentile(series, q):
    series = sorted(series)
    position = (len(series) - 1) * q
    low, high = int(position), math.ceil(position)
    return series[low] + (series[high] - series[low]) * (position - low)


for index in range(6000):
    z1, z2 = rng.gauss(0, 1), rng.gauss(0, 1)
    growth = assumptions["initial_growth"] + assumptions["mc_growth_sigma"] * z1
    margin = assumptions["steady_ebit_margin"] + assumptions["mc_margin_sigma"] * (rho * z1 + math.sqrt(1 - rho * rho) * z2)
    growth = min(0.25, max(-0.15, growth))
    margin = min(0.60, max(0.02, margin))
    intensity = rng.triangular(assumptions["mc_reinvestment_min"], assumptions["mc_reinvestment_max"], assumptions["mc_reinvestment_mode"])
    rate = rng.uniform(assumptions["mc_discount_min"], assumptions["mc_discount_max"])
    revenue = base_revenue
    present_value = 0
    trajectory = []
    for year in range(1, 6):
        revenue *= 1 + growth
        if year > 1 and partial["type"] != "annual":
            revenue = data["historical"]["revenue"][fy0] * (1 + assumptions["initial_growth"]) * (1 + growth) ** (year - 1)
        ebit = revenue * margin
        reinvestment = revenue * intensity
        fcff = ebit * (1 - tax) - reinvestment
        factor = 1 / (1 + rate) ** discount_years[year - 1]
        present_value += fcff * factor
        trajectory.append({"year": year, "revenue": revenue, "ebit": ebit,
                           "reinvestment": reinvestment, "fcff": fcff, "discount_factor": factor})
    present_value += fcff * (1 + g) / (rate - g) * trajectory[-1]["discount_factor"]
    value = (present_value + assumptions["cash_and_investments"] - assumptions["net_debt"]) / assumptions["diluted_shares"]
    values.append(value)
    trials.append({"path_id": index + 1, "revenue_growth": growth, "ebit_margin": margin,
                   "reinvestment_intensity": intensity, "discount_rate": rate,
                   "value_per_share": value, "trajectory": trajectory})


def correlation(left, right):
    mean_left, mean_right = statistics.fmean(left), statistics.fmean(right)
    sd_left, sd_right = statistics.stdev(left), statistics.stdev(right)
    return sum((x - mean_left) * (y - mean_right) for x, y in zip(left, right)) / ((len(left) - 1) * sd_left * sd_right)


names = ["revenue_growth", "ebit_margin", "reinvestment_intensity", "discount_rate"]
matrix = [[correlation([row[name] for row in trials], [row[other] for row in trials]) for other in names] for name in names]
drivers = {
    "revenue_growth": {"distribution": "normal_truncated", "parameters": {"mu": assumptions["initial_growth"], "sigma": assumptions["mc_growth_sigma"]}, "unit": "ratio", "bounds": {"min": -0.15, "max": 0.25}},
    "ebit_margin": {"distribution": "normal_truncated", "parameters": {"mu": assumptions["steady_ebit_margin"], "sigma": assumptions["mc_margin_sigma"]}, "unit": "ratio", "bounds": {"min": 0.02, "max": 0.60}},
    "reinvestment_intensity": {"distribution": "triangular", "parameters": {"min": assumptions["mc_reinvestment_min"], "max": assumptions["mc_reinvestment_max"], "mode": assumptions["mc_reinvestment_mode"]}, "unit": "ratio", "bounds": {"min": assumptions["mc_reinvestment_min"], "max": assumptions["mc_reinvestment_max"]}},
    "discount_rate": {"distribution": "uniform", "parameters": {"min": assumptions["mc_discount_min"], "max": assumptions["mc_discount_max"]}, "unit": "ratio", "bounds": {"min": assumptions["mc_discount_min"], "max": assumptions["mc_discount_max"]}},
}
result = {
    "seed": seed, "n_valid": len(trials), "n_rejected": 0,
    "method": "共同标准正态冲击经 Cholesky 变换产生增长与利润率相关性；截断到声明边界；每条路径保持增长和利润率不变。",
    "drivers": drivers,
    "dependence": {"type": "correlated", "ordered_names": names,
                   "matrix": [[1, rho, 0, 0], [rho, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]},
    "realized_correlation": {"ordered_names": names, "matrix": matrix},
    "trials": trials,
    "statistics": {**{f"p{int(q * 100)}": percentile(values, q) for q in (0.1, 0.25, 0.5, 0.75, 0.9)}, "mean": statistics.fmean(values)},
    "percentile_convention": "linear interpolation at (N-1)q",
    "limitations": "模型条件 DCF 分布而非市场价格预测；短历史不能可靠识别联合分布，截断和相关性均为明确简化。",
}
json.dump(result, open(args.output, "w"))
if args.model.endswith(".xlsx"):
    workbook = load_workbook(args.model, data_only=False)
    if "MC_Trials" in workbook.sheetnames:
        del workbook["MC_Trials"]
    mc = workbook.create_sheet("MC_Trials")
    columns = list(trials[0])
    mc.append(columns)
    for row in trials:
        mc.append([json.dumps(row[key], ensure_ascii=False) if key == "trajectory" else row[key] for key in columns])
    output = workbook["Outputs"]
    rows = {output.cell(row, 1).value: row for row in range(2, output.max_row + 1)}
    value_range = "MC_Trials!$F$2:$F$6001"
    for key, q in (("mc_p10", 0.1), ("mc_p25", 0.25), ("mc_p50", 0.5), ("mc_p75", 0.75), ("mc_p90", 0.9)):
        output.cell(rows[key], 3, f"=PERCENTILE({value_range},{q})")
    output.cell(rows["mc_mean"], 3, f"=AVERAGE({value_range})")
    output.cell(rows["mc_n"], 3, f"=COUNT({value_range})")
    workbook.save(args.model)
