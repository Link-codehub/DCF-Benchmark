#!/usr/bin/env python3
import argparse
import json
import statistics
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
import sys
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from e_model import compute, default_assumptions, historical_outputs, summarize_history

RECOMPUTE = r'''#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--model',required=True);p.add_argument('--output',required=True);a=p.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parent));from e_model import compute
model=json.load(open(a.model));forecast,valuation=compute(json.load(open(a.input)),model['assumptions']);result={'historical':{k:v for k,v in forecast.items() if k.startswith(('hist_','actual_partial_'))},'assumptions':model['assumptions'],'forecast':forecast,'valuation':{**model['assumptions'],**valuation}}
Path(a.output).mkdir(parents=True,exist_ok=True);json.dump(result,open(Path(a.output)/'recomputed.json','w'),indent=2)
'''

RECOMPUTE = r'''#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--model',required=True);p.add_argument('--output',required=True);a=p.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parent));from e_model import compute
model=json.load(open(a.model));forecast,valuation=compute(json.load(open(a.input)),model['assumptions']);result={'historical':{k:v for k,v in forecast.items() if k.startswith(('hist_','actual_partial_'))},'assumptions':model['assumptions'],'forecast':forecast,'valuation':{**model['assumptions'],**valuation}}
Path(a.output).mkdir(parents=True,exist_ok=True);json.dump(result,open(Path(a.output)/'recomputed.json','w'),indent=2)
'''


def memo(data, assumptions):
    history = data["historical"]
    years = data["fiscal_years"]
    last = years[-1]
    summary = summarize_history(data)
    ticker = data["company"]["ticker"]
    mechanisms = {
        "MSFT": "云与人工智能需求只有在数据中心投产并达到利用率后转为收入；前期 CapEx 与折旧先于现金回报，故增长向成熟水平收敛而资本强度不立即消失。",
        "DE": "农机更新、价格组合与经销商库存共同影响销量和利润率；周期回落会同时压缩收入与经营杠杆，工厂及库存投入须随周期调整。",
        "TGT": "客流、客单价和假日商品组合决定 H2 收入，节前备货占用营运资本；不把 H1 机械年化，且残余期预测保留库存季节性。",
        "NFLX": "会员留存、定价及广告套餐推动收入，内容投入和摊销影响 EBIT；汇总 SEC 数据不能识别会员或内容现金支出，故再投资只是明确代理。",
    }
    bounds = simulation_parameters(data, assumptions)["drivers"]
    return f"""参考开放案例，不是目标答案。FY {last} 收入 {summary['initial_revenue']:,.3f}、EBIT {historical_outputs(data)['hist_ebit_fy0']:,.3f}、稀释 EPS {historical_outputs(data)['hist_eps_fy0']:.4f}，均来自 SEC_XBRL 对应年度。初始增长采用 ({summary['initial_revenue']:,.3f}/{data['historical']['revenue'][years[-4]]:,.3f})^(1/3)−1={assumptions['initial_growth']:.6f}，逐步收敛到 2.5%；经营利润率采用最近三年 EBIT/收入均值 {assumptions['steady_ebit_margin']:.6f}。

{mechanisms[ticker]} FY {last} D&A/收入={assumptions['da_to_revenue']:.6f}、CapEx/收入={assumptions['capex_to_revenue']:.6f}，经营性 NWC/收入={assumptions['nwc_to_revenue']:.6f}，来源同为 SEC_XBRL 该期现金、流动资产、流动负债和债务行。增长所需的资本开支与营运资本通过 D&A−CapEx−ΔNWC 进入 FCFF，不能假定无成本扩张。

WACC={assumptions['wacc']:.6f}，以冻结国债收益率 {data['market_observation']['treasury_10y']:.4f}（{data['market_observation']['treasury_date']}，UST_DGS10）加 5% 风险补偿并设边界；g=2.5% 是开放假设。预测存在显著不确定性，历史经营驱动和汇总再投资代理可能失真。

模拟增长采用截断正态，中心 {bounds['revenue_growth']['mu']:.4f}、标准差 {bounds['revenue_growth']['sigma']:.4f}（历史年度增长样本波动）；利润率标准差 {bounds['ebit_margin']['sigma']:.4f}（历史利润率波动）。再投资三角分布 {bounds['reinvestment_intensity']['min']:.4f} 至 {bounds['reinvestment_intensity']['max']:.4f}，由历史 CapEx+ΔNWC−D&A 占收入观测并留压力余量。折现率均匀分布于 {bounds['discount_rate']['min']:.4f} 至 {bounds['discount_rate']['max']:.4f}，保证高于 g。增长与利润率相关系数设 0.25，表达需求与经营杠杆的同向冲击，其他驱动独立。模拟是条件 FCFF/DCF 离散度，不是股价预测；短样本、边界、相关性与训练记忆泄漏均为局限，未使用截止日后信息。"""


def simulation_parameters(data, assumptions):
    summary = summarize_history(data)
    margin = assumptions["steady_ebit_margin"]
    correlation = 0.25
    reinv = summary["reinvestment_observations"]
    lower = min(-0.03, min(reinv) - 0.01)
    upper = max(0.08, max(reinv) + 0.01)
    return {
        "assumptions": {
            "mc_growth_margin_correlation": correlation,
            "mc_growth_sigma": max(0.02, statistics.stdev(summary["growth_observations"])),
            "mc_margin_sigma": max(0.01, statistics.stdev(summary["margin_observations"])),
            "mc_reinvestment_min": lower, "mc_reinvestment_max": upper,
            "mc_reinvestment_mode": sum(reinv) / len(reinv),
            "mc_discount_min": max(0.07, assumptions["terminal_growth"] + 0.03), "mc_discount_max": 0.13,
        },
        "drivers": {"revenue_growth": {"mu": assumptions["initial_growth"], "sigma": max(0.02, statistics.stdev(summary["growth_observations"]))},
                    "ebit_margin": {"mu": margin, "sigma": max(0.01, statistics.stdev(summary["margin_observations"]))},
                    "reinvestment_intensity": {"min": lower, "max": upper, "mode": sum(reinv) / len(reinv)},
                    "discount_rate": {"min": max(0.07, assumptions["terminal_growth"] + 0.03), "max": 0.13}},
    }


def make_workbook(data, assumptions, model, valuation, path, source):
    wb = load_workbook(source)
    a = wb.create_sheet("Assumptions")
    a.append(["key", "value", "证据或开放假设"])
    for key, value in assumptions.items():
        a.append([key, value, "SEC_XBRL 历史推导或开放假设"])
    for index, year in enumerate(data["reported_partial_period"]["timing"]["discount_years"], 1):
        a.append([f"discount_years_{index}", year, "估值日至完整财年末实际天数/365"])
    summary = summarize_history(data)
    a.append(["initial_revenue", summary["initial_revenue"], "FY0 SEC_XBRL 收入"])
    a.append(["initial_nwc", summary["initial_nwc"], "FY0 经营性 NWC"])
    a.append(["actual_partial_revenue_y1", model["actual_partial_revenue_y1"], "仅示例引用；正式公式见 Forecast"])
    a.append(["actual_partial_ebit_y1", model["actual_partial_ebit_y1"], "仅示例引用；正式公式见 Forecast"])
    a.append(["prior_partial_revenue", sum(row["revenue"] for row in data["reported_partial_period"].get("prior_year_quarters", [])), "上年同期 H1"])
    rows = {a.cell(row, 1).value: row for row in range(2, a.max_row + 1)}
    def ref(key):
        return f"Assumptions!$B${rows[key]}"
    f = wb.create_sheet("Forecast")
    f.append(["line", "中文项目"] + [f"FY+{year}" for year in range(1, 6)])
    labels = {"revenue": "完整财年收入", "ebit": "完整财年 EBIT", "da": "计入期的 D&A", "capex": "计入期的 CapEx", "delta_nwc": "营运资本增加", "nwc": "期末经营性 NWC", "reinvestment_component": "D&A−CapEx−ΔNWC", "fcff": "计入估值的 FCFF", "eps": "完整财年 EPS", "discount_factor": "折现因子", "discount_years": "折现年数"}
    for key in labels:
        f.append([key, labels[key]] + [None] * 5)
    fr = {f.cell(row, 1).value: row for row in range(2, f.max_row + 1)}
    partial = data["reported_partial_period"]["type"] != "annual"
    for year in range(1, 6):
        column = get_column_letter(year + 2)
        previous = get_column_letter(year + 1)
        growth = f"({ref('initial_growth')}+({ref('terminal_revenue_growth')}-{ref('initial_growth')})*{year - 1}/4)"
        if year == 1:
            revenue = f"={ref('initial_revenue')}*(1+{growth})" if not partial else f"={ref('actual_partial_revenue_y1')}+{ref('prior_partial_revenue')}*(1+{growth})"
        else:
            revenue = f"={previous}{fr['revenue']}*(1+{growth})"
        f.cell(fr["revenue"], year + 2, revenue)
        if year == 1 and partial:
            f.cell(fr["ebit"], year + 2, f"={ref('actual_partial_ebit_y1')}+({column}{fr['revenue']}-{ref('actual_partial_revenue_y1')})*{ref('steady_ebit_margin')}")
            operating = f"({column}{fr['revenue']}-{ref('actual_partial_revenue_y1')})"
            nwc = f"={ref('initial_nwc')}*{column}{fr['revenue']}/{ref('initial_revenue')}"
            delta = f"={column}{fr['nwc']}-{ref('initial_nwc')}"
        else:
            f.cell(fr["ebit"], year + 2, f"={column}{fr['revenue']}*{ref('steady_ebit_margin')}")
            operating = f"{column}{fr['revenue']}"
            nwc = f"={column}{fr['revenue']}*{ref('nwc_to_revenue')}"
            delta = f"={column}{fr['nwc']}-{ref('initial_nwc')}" if year == 1 else f"={column}{fr['nwc']}-{previous}{fr['nwc']}"
        f.cell(fr["nwc"], year + 2, nwc)
        f.cell(fr["delta_nwc"], year + 2, delta)
        f.cell(fr["da"], year + 2, f"={operating}*{ref('da_to_revenue')}")
        f.cell(fr["capex"], year + 2, f"={operating}*{ref('capex_to_revenue')}")
        f.cell(fr["reinvestment_component"], year + 2, f"={column}{fr['da']}-{column}{fr['capex']}-{column}{fr['delta_nwc']}")
        operating_ebit = f"({column}{fr['ebit']}-{ref('actual_partial_ebit_y1')})" if year == 1 and partial else f"{column}{fr['ebit']}"
        f.cell(fr["fcff"], year + 2, f"={operating_ebit}*(1-{ref('tax_rate')})+{column}{fr['reinvestment_component']}")
        f.cell(fr["eps"], year + 2, f"=({column}{fr['ebit']}-{ref('net_debt')}*{ref('interest_rate')})*(1-{ref('tax_rate')})/{ref('diluted_shares')}")
        f.cell(fr["discount_years"], year + 2, f"={ref(f'discount_years_{year}')}")
        f.cell(fr["discount_factor"], year + 2, f"=1/(1+{ref('wacc')})^{column}{fr['discount_years']}")
    d = wb.create_sheet("DCF")
    d.append(["key", "value"])
    for key in ("pv_explicit", "terminal_value", "pv_terminal", "enterprise_value", "equity_value", "value_per_share"):
        d.append([key, None])
    dr = {d.cell(row, 1).value: row for row in range(2, d.max_row + 1)}
    d.cell(dr["pv_explicit"], 2, f"=SUMPRODUCT(Forecast!C{fr['fcff']}:G{fr['fcff']},Forecast!C{fr['discount_factor']}:G{fr['discount_factor']})")
    d.cell(dr["terminal_value"], 2, f"=Forecast!G{fr['fcff']}*(1+{ref('terminal_growth')})/({ref('wacc')}-{ref('terminal_growth')})")
    d.cell(dr["pv_terminal"], 2, f"=B{dr['terminal_value']}*Forecast!G{fr['discount_factor']}")
    d.cell(dr["enterprise_value"], 2, f"=B{dr['pv_explicit']}+B{dr['pv_terminal']}")
    d.cell(dr["equity_value"], 2, f"=B{dr['enterprise_value']}+{ref('cash_and_investments')}-{ref('net_debt')}")
    d.cell(dr["value_per_share"], 2, f"=B{dr['equity_value']}/{ref('diluted_shares')}")
    o = wb["Outputs"]
    output_rows = {o.cell(row, 1).value: row for row in range(2, o.max_row + 1)}
    history_rows = {wb["Historical"].cell(row, 1).value: row for row in range(3, wb["Historical"].max_row + 1)}
    for key, raw in (("hist_revenue_fy0", "revenue"), ("hist_ebit_fy0", "operating_income"), ("hist_eps_fy0", "eps_diluted")):
        o.cell(output_rows[key], 3, f"=Historical!G{history_rows[raw]}")
    for year in range(1, 6):
        column = get_column_letter(year + 2)
        for key in ("revenue", "ebit", "eps", "fcff", "discount_factor"):
            o.cell(output_rows[f"{key}_y{year}"], 3, f"=Forecast!{column}{fr[key]}")
    for key in ("actual_partial_revenue_y1", "actual_partial_ebit_y1", "residual_revenue_y1", "residual_fcff_y1", "residual_discount_years"):
        if key not in output_rows:
            continue
        if key.startswith("actual_partial"):
            field = "revenue" if "revenue" in key else "ebit"
            source_key = "steady_ebit_margin"
            value = model[key]
            a.append([key + "_formula", value, "历史实际参考，仅参考解"])
            o.cell(output_rows[key], 3, f"={ref('actual_partial_' + field + '_y1')}")
        elif key == "residual_revenue_y1":
            o.cell(output_rows[key], 3, f"=Forecast!C{fr['revenue']}-{ref('actual_partial_revenue_y1')}")
        elif key == "residual_fcff_y1":
            o.cell(output_rows[key], 3, f"=Forecast!C{fr['fcff']}")
        else:
            o.cell(output_rows[key], 3, f"={ref('discount_years_1')}")
    for key in ("wacc", "terminal_growth", "diluted_shares"):
        o.cell(output_rows[key], 3, f"={ref(key)}")
    for key in ("enterprise_value", "equity_value", "value_per_share"):
        o.cell(output_rows[key], 3, f"=DCF!B{dr[key]}")
    for sheet in (a, f, d):
        sheet.column_dimensions["A"].width = 34
        sheet.column_dimensions["B"].width = 36
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data = json.load(open(args.input))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "e_model.py").write_text((HERE / "e_model.py").read_text())
    assumptions = default_assumptions(data)
    assumptions.update(simulation_parameters(data, assumptions)["assumptions"])
    forecast, valuation = compute(data, assumptions)
    (output / "simulate.py").write_text((HERE / "e_simulator.py").read_text())
    (output / "recompute.py").write_text(RECOMPUTE)
    (output / "memo.md").write_text(memo(data, assumptions))
    (output / "model.json").write_text(json.dumps({"historical": {key: value for key, value in forecast.items() if key.startswith(("hist_", "actual_partial_"))}, "assumptions": assumptions, "forecast": forecast, "valuation": {**assumptions, **valuation}, "simulation_summary": {}}, indent=2))
    if data["task_id"] in ("E01", "E03"):
        make_workbook(data, assumptions, forecast, valuation, output / "model.xlsx", Path(args.input).with_name("frozen_history.xlsx"))
        (output / "model.json").unlink()
    print(json.dumps({"task": data["task_id"], "value_per_share": valuation["value_per_share"]}))


if __name__ == "__main__":
    main()
