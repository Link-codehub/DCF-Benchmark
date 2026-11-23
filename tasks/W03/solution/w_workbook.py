#!/usr/bin/env python3
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter


def build_workbook(path, sources, mapping, assumptions, contract):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sources"
    ws.append(["field_id", "value", "unit", "period_start", "period_end", "field", "source_url", "accession", "filed", "status"])
    for row in sources["items"]:
        ws.append([row[key] for key in ("field_id", "value", "unit", "period_start", "period_end", "field", "source_url", "accession", "filed", "status")])
    source_rows = {ws.cell(row, 1).value: row for row in range(2, ws.max_row + 1)}
    def source(key):
        return f"Sources!$B${source_rows[key]}"
    a = wb.create_sheet("Assumptions")
    a.append(["key", "value", "含义"])
    a.append(["initial_revenue", f"={source('revenue')}", "FY0 收入，唯一历史输入来自 Sources"])
    a.append(["initial_nwc", f"={source('current_assets')}-{source('cash')}-{source('short_term_investments')}-({source('current_liabilities')}-{source('current_debt')})", "FY0 经营性 NWC"])
    for key in ("initial_growth", "terminal_growth"):
        a.append([key, assumptions[key], "开放假设"])
    a.append(["steady_ebit_margin", f"={source('operating_income')}/{source('revenue')}", "FY0 经营利润率"])
    a.append(["tax_rate", f"={source('income_tax')}/{source('pretax_income')}", "FY0 现金税率代理"])
    a.append(["wacc", f"={source('treasury_10y')}+0.055", "国债收益率加开放风险补偿"])
    a.append(["da_to_revenue", f"={source('da')}/{source('revenue')}", "FY0 D&A/收入"])
    a.append(["capex_to_revenue", f"={source('capex')}/{source('revenue')}", "FY0 CapEx/收入"])
    a.append(["nwc_to_revenue", "=B3/B2", "FY0 经营 NWC/收入"])
    ar = {a.cell(row, 1).value: row for row in range(2, a.max_row + 1)}
    def assumption(key):
        return f"Assumptions!$B${ar[key]}"
    f = wb.create_sheet("Forecast")
    f.append(["line", "项目"] + [f"FY+{year}" for year in range(1, 6)])
    labels = {"revenue": "收入", "ebit": "经营利润", "da": "折旧与摊销", "capex": "资本开支", "nwc": "期末经营 NWC", "delta_nwc": "经营 NWC 增加", "reinvestment_component": "D&A−CapEx−ΔNWC", "fcff": "无杠杆自由现金流", "discount_factor": "折现因子"}
    for key, label in labels.items():
        f.append([key, label] + [None] * 5)
    fr = {f.cell(row, 1).value: row for row in range(2, f.max_row + 1)}
    for year in range(1, 6):
        column, previous = get_column_letter(year + 2), get_column_letter(year + 1)
        growth = f"({assumption('initial_growth')}+({assumption('terminal_growth')}-{assumption('initial_growth')})*{year - 1}/4)"
        f.cell(fr["revenue"], year + 2, f"={assumption('initial_revenue')}*(1+{growth})" if year == 1 else f"={previous}{fr['revenue']}*(1+{growth})")
        f.cell(fr["ebit"], year + 2, f"={column}{fr['revenue']}*{assumption('steady_ebit_margin')}")
        f.cell(fr["da"], year + 2, f"={column}{fr['revenue']}*{assumption('da_to_revenue')}")
        f.cell(fr["capex"], year + 2, f"={column}{fr['revenue']}*{assumption('capex_to_revenue')}")
        f.cell(fr["nwc"], year + 2, f"={assumption('initial_nwc')}*{column}{fr['revenue']}/{assumption('initial_revenue')}" if year == 1 else f"={column}{fr['revenue']}*{assumption('nwc_to_revenue')}")
        f.cell(fr["delta_nwc"], year + 2, f"={column}{fr['nwc']}-{assumption('initial_nwc')}" if year == 1 else f"={column}{fr['nwc']}-{previous}{fr['nwc']}")
        f.cell(fr["reinvestment_component"], year + 2, f"={column}{fr['da']}-{column}{fr['capex']}-{column}{fr['delta_nwc']}")
        f.cell(fr["fcff"], year + 2, f"={column}{fr['ebit']}*(1-{assumption('tax_rate')})+{column}{fr['reinvestment_component']}")
        f.cell(fr["discount_factor"], year + 2, f"=1/(1+{assumption('wacc')})^{year}")
    d = wb.create_sheet("DCF")
    d.append(["key", "value", "定义"])
    explicit_terms = "+".join(f"Forecast!{get_column_letter(year + 2)}{fr['fcff']}*Forecast!{get_column_letter(year + 2)}{fr['discount_factor']}" for year in range(1, 6))
    entries = [("pv_explicit", f"={explicit_terms}", "显性期现值"),
               ("terminal_value", f"=Forecast!G{fr['fcff']}*(1+{assumption('terminal_growth')})/({assumption('wacc')}-{assumption('terminal_growth')})", "Gordon 终值"),
               ("pv_terminal", f"=B3*Forecast!G{fr['discount_factor']}", "终值现值"),
               ("enterprise_value", "=B2+B4", "企业价值"),
               ("cash", f"={source('cash')}", "现金"),
               ("short_term_investments", f"={source('short_term_investments')}", "短期投资"),
               ("current_debt", f"={source('current_debt')}", "当期债务"),
               ("noncurrent_debt", f"={source('noncurrent_debt')}", "非当期债务"),
               ("diluted_shares", f"={source('diluted_shares')}", "加权平均稀释股数"),
               ("equity_value", "=B5+B6+B7-B8-B9", "股权价值"),
               ("value_per_share", "=B11/B10", "每股价值"),
               ("risk_free_rate", f"={source('treasury_10y')}", "10 年期国债收益率，实际用于 Assumptions 的 WACC"),
               ("receivables", f"={source('receivables')}", "应收账款核验"),
               ("net_income_consolidated", f"={source('net_income_consolidated')}", "合并净利润勾稽"),
               ("pretax_income", f"={source('pretax_income')}", "税前利润勾稽"),
               ("income_tax", f"={source('income_tax')}", "所得税勾稽"),
               ("nwc_reconciliation", f"={assumption('initial_nwc')}", "经营 NWC 勾稽")]
    for row in entries:
        d.append(list(row))
    dr = {d.cell(row, 1).value: row for row in range(2, d.max_row + 1)}
    o = wb.create_sheet("Outputs")
    o.append(["key", "中文定义", "value"])
    for key, label in (("enterprise_value", "企业价值，百万美元"), ("equity_value", "股权价值，百万美元"), ("value_per_share", "每股价值，美元")):
        o.append([key, label, f"=DCF!B{dr[key]}"])
    for sheet in wb:
        sheet.freeze_panes = "C2" if sheet.title == "Forecast" else "A2"
        sheet.column_dimensions["A"].width = 33
        sheet.column_dimensions["B"].width = 28
        sheet.column_dimensions["C"].width = 36
        for cell in sheet[1]:
            cell.font = Font(bold=True)
    ws.column_dimensions["G"].width = 65
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.save(path)
    used = {row["field_id"]: [] for row in sources["items"]}
    for sheet in (a, f, d):
        for row in sheet.iter_rows():
            for cell in row:
                if cell.data_type != "f":
                    continue
                for field_id, source_row in source_rows.items():
                    if f"Sources!$B${source_row}" in cell.value:
                        used[field_id].append(f"{sheet.title}!{cell.coordinate}")
    for item in mapping:
        item["used_by"] = used.get(item["field_id"], [])
