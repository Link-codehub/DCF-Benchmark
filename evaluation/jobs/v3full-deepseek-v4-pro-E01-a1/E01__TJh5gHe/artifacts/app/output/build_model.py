#!/usr/bin/env python3
"""Build model.xlsx with Assumptions, Forecast, DCF, Outputs, MC_Trials sheets."""

import openpyxl
from openpyxl.utils import get_column_letter
import json

wb = openpyxl.Workbook()

# ============================================================
# Assumptions sheet
# ============================================================
ws_a = wb.active
ws_a.title = "Assumptions"

# Header
ws_a['A1'] = 'key'
ws_a['B1'] = 'value'
ws_a['C1'] = 'description'

assumptions = [
    ('initial_growth', 0.1400, 'FY1-FY5 annual revenue growth rate'),
    ('steady_ebit_margin', 0.4464, 'EBIT / Revenue (FY2024 level)'),
    ('tax_rate', 0.1823, 'Effective tax rate (FY2024)'),
    ('da_to_revenue', 0.0620, 'D&A as fraction of revenue (FY2024)'),
    ('capex_to_revenue', 0.1814, 'CapEx as fraction of revenue (FY2024, elevated AI infra)'),
    ('nwc_to_revenue', -0.1585, 'Operating NWC as fraction of revenue (FY2024)'),
    ('interest_rate', 0.0450, 'Forward-looking pre-tax cost of debt'),
    ('wacc', 0.0800, 'Weighted average cost of capital'),
    ('terminal_growth', 0.0300, 'Perpetuity growth rate (Gordon)'),
    ('net_debt', 44937, 'Current + non-current debt, FY2024'),
    ('cash_and_investments', 75543, 'Cash + short-term investments, FY2024'),
    ('diluted_shares', 7469, 'Diluted weighted-average shares (millions), FY2024'),
    ('fy24_revenue', 245122, 'FY2024 revenue base'),
    ('fy24_nwc', -38846, 'FY2024 operating NWC base'),
    ('fy24_ebit', 109433, 'FY2024 operating income (EBIT)'),
    ('fy24_eps', 11.80, 'FY2024 diluted EPS'),
]

for i, (k, v, desc) in enumerate(assumptions, start=2):
    ws_a.cell(row=i, column=1, value=k)
    ws_a.cell(row=i, column=2, value=v)
    ws_a.cell(row=i, column=3, value=desc)

# ============================================================
# Forecast sheet (A=key, B=descr, C:G = FY1:FY5)
# ============================================================
ws_f = wb.create_sheet("Forecast")

# Col A = key, Col B = description, Col C-G = FY1-FY5
headers = ['key', 'description', 'FY1', 'FY2', 'FY3', 'FY4', 'FY5']
for j, h in enumerate(headers, 1):
    ws_f.cell(row=1, column=j, value=h)

# Define rows for each metric
keys = [
    'revenue', 'ebit', 'eps', 'da', 'capex', 'delta_nwc',
    'reinvestment_component', 'fcff', 'discount_factor',
    'interest_expense', 'pretax_income', 'net_income'
]

for i, key in enumerate(keys):
    row = i + 2
    ws_f.cell(row=row, column=1, value=key)

# ---- Revenue: FY1 = fy24_rev * (1+g), FYn = prev * (1+g) ----
r_rev = 2  # row for revenue
for yr_idx in range(5):
    col = 3 + yr_idx  # C=3, D=4, ..., G=7
    if yr_idx == 0:
        ws_f.cell(row=r_rev, column=col,
                  value='=Assumptions!B13*(1+Assumptions!B2)')
    else:
        prev_col = get_column_letter(col - 1)
        ws_f.cell(row=r_rev, column=col,
                  value=f'={prev_col}{r_rev}*(1+Assumptions!B2)')

# ---- EBIT: revenue * margin ----
r_ebit = 3
for yr_idx in range(5):
    col = 3 + yr_idx
    ws_f.cell(row=r_ebit, column=col,
              value=f'={get_column_letter(col)}{r_rev}*Assumptions!B3')

# ---- EPS = (EBIT - interest) * (1-t) / shares ----
# interest = net_debt * interest_rate
# pretax = ebit - interest
# net_income = pretax * (1-t)
# eps = net_income / shares
r_eps = 4
r_int = 11  # interest_expense row
r_pretax = 12
r_ni = 13
for yr_idx in range(5):
    col = 3 + yr_idx
    col_l = get_column_letter(col)
    # interest_expense
    ws_f.cell(row=r_int, column=col, value='=Assumptions!B10*Assumptions!B7')
    # pretax
    ws_f.cell(row=r_pretax, column=col, value=f'={col_l}{r_ebit}-{col_l}{r_int}')
    # net_income
    ws_f.cell(row=r_ni, column=col, value=f'={col_l}{r_pretax}*(1-Assumptions!B4)')
    # eps
    ws_f.cell(row=r_eps, column=col, value=f'={col_l}{r_ni}/Assumptions!B12')

# ---- D&A = revenue * da_to_rev ----
r_da = 5
for yr_idx in range(5):
    col = 3 + yr_idx
    ws_f.cell(row=r_da, column=col,
              value=f'={get_column_letter(col)}{r_rev}*Assumptions!B5')

# ---- CapEx = revenue * capex_to_rev ----
r_capex = 6
for yr_idx in range(5):
    col = 3 + yr_idx
    ws_f.cell(row=r_capex, column=col,
              value=f'={get_column_letter(col)}{r_rev}*Assumptions!B6')

# ---- ΔNWC = rev * nwc_ratio - prev_rev * nwc_ratio ----
r_dnwc = 7
for yr_idx in range(5):
    col = 3 + yr_idx
    col_l = get_column_letter(col)
    if yr_idx == 0:
        ws_f.cell(row=r_dnwc, column=col,
                  value=f'={col_l}{r_rev}*Assumptions!B7-Assumptions!B14')
    else:
        prev_col_l = get_column_letter(col - 1)
        ws_f.cell(row=r_dnwc, column=col,
                  value=f'={col_l}{r_rev}*Assumptions!B7-{prev_col_l}{r_rev}*Assumptions!B7')

# ---- Reinvestment component = D&A - CapEx - ΔNWC ----
r_rc = 8
for yr_idx in range(5):
    col = 3 + yr_idx
    col_l = get_column_letter(col)
    ws_f.cell(row=r_rc, column=col,
              value=f'={col_l}{r_da}-{col_l}{r_capex}-{col_l}{r_dnwc}')

# ---- FCFF = EBIT*(1-t) + reinvestment_component ----
r_fcff = 9
for yr_idx in range(5):
    col = 3 + yr_idx
    col_l = get_column_letter(col)
    ws_f.cell(row=r_fcff, column=col,
              value=f'={col_l}{r_ebit}*(1-Assumptions!B4)+{col_l}{r_rc}')

# ---- Discount factor = 1/(1+WACC)^yr ----
r_df = 10
for yr_idx in range(5):
    col = 3 + yr_idx
    yr = yr_idx + 1
    ws_f.cell(row=r_df, column=col,
              value=f'=1/(1+Assumptions!B8)^{yr}')

# ============================================================
# DCF sheet
# ============================================================
ws_dcf = wb.create_sheet("DCF")

ws_dcf['A1'] = 'item'
ws_dcf['B1'] = 'value'
ws_dcf['C1'] = 'formula_note'

dcf_items = [
    ('pv_fcff_y1', f'=Forecast!C{r_fcff}*Forecast!C{r_df}', 'PV of FY1 FCFF'),
    ('pv_fcff_y2', f'=Forecast!D{r_fcff}*Forecast!D{r_df}', 'PV of FY2 FCFF'),
    ('pv_fcff_y3', f'=Forecast!E{r_fcff}*Forecast!E{r_df}', 'PV of FY3 FCFF'),
    ('pv_fcff_y4', f'=Forecast!F{r_fcff}*Forecast!F{r_df}', 'PV of FY4 FCFF'),
    ('pv_fcff_y5', f'=Forecast!G{r_fcff}*Forecast!G{r_df}', 'PV of FY5 FCFF'),
    ('terminal_fcff', f'=Forecast!G{r_fcff}*(1+Assumptions!B9)', 'FY5 FCFF * (1+g)'),
    ('terminal_value_undisc', f'=B7/(Assumptions!B8-Assumptions!B9)', 
     'TV = FCFF5*(1+g)/(WACC-g)'),
    ('pv_terminal_value', f'=B8*Forecast!G{r_df}', 'Discounted TV'),
    ('enterprise_value', '=B2+B3+B4+B5+B6+B9', 'Sum of PV(FCFF) + PV(TV)'),
    ('equity_value', '=B10+Assumptions!B11-Assumptions!B10', 'EV + Cash - Net Debt'),
    ('value_per_share', '=B11/Assumptions!B12', 'Equity value / diluted shares'),
]

for i, (item, formula, note) in enumerate(dcf_items, start=2):
    ws_dcf.cell(row=i, column=1, value=item)
    ws_dcf.cell(row=i, column=2, value=formula)
    ws_dcf.cell(row=i, column=3, value=note)

# ============================================================
# MC_Trials sheet (will be populated by simulate.py)
# ============================================================
ws_mc = wb.create_sheet("MC_Trials")

ws_mc['A1'] = 'metric'
ws_mc['B1'] = 'value'

mc_stats = [
    ('n_valid', 0),
    ('n_rejected', 0),
    ('seed', 1830),
    ('p10', 0),
    ('p25', 0),
    ('p50', 0),
    ('p75', 0),
    ('p90', 0),
    ('mean', 0),
    ('std', 0),
]

for i, (k, v) in enumerate(mc_stats, start=2):
    ws_mc.cell(row=i, column=1, value=k)
    ws_mc.cell(row=i, column=2, value=v)

# ============================================================
# Outputs sheet (preserve existing structure, fill formula column C)
# ============================================================
ws_o = wb.create_sheet("Outputs")

# Header
ws_o['A1'] = 'key'
ws_o['B1'] = '中文定义'
ws_o['C1'] = 'value'

outputs_map = [
    # (row, key, formula_or_value)
    (2, 'hist_revenue_fy0', '=Assumptions!B13'),
    (3, 'hist_ebit_fy0', '=Assumptions!B15'),
    (4, 'hist_eps_fy0', '=Assumptions!B16'),
    # FY1
    (5, 'revenue_y1', f'=Forecast!C{r_rev}'),
    (6, 'ebit_y1', f'=Forecast!C{r_ebit}'),
    (7, 'eps_y1', f'=Forecast!C{r_eps}'),
    (8, 'fcff_y1', f'=Forecast!C{r_fcff}'),
    (9, 'discount_factor_y1', f'=Forecast!C{r_df}'),
    # FY2
    (10, 'revenue_y2', f'=Forecast!D{r_rev}'),
    (11, 'ebit_y2', f'=Forecast!D{r_ebit}'),
    (12, 'eps_y2', f'=Forecast!D{r_eps}'),
    (13, 'fcff_y2', f'=Forecast!D{r_fcff}'),
    (14, 'discount_factor_y2', f'=Forecast!D{r_df}'),
    # FY3
    (15, 'revenue_y3', f'=Forecast!E{r_rev}'),
    (16, 'ebit_y3', f'=Forecast!E{r_ebit}'),
    (17, 'eps_y3', f'=Forecast!E{r_eps}'),
    (18, 'fcff_y3', f'=Forecast!E{r_fcff}'),
    (19, 'discount_factor_y3', f'=Forecast!E{r_df}'),
    # FY4
    (20, 'revenue_y4', f'=Forecast!F{r_rev}'),
    (21, 'ebit_y4', f'=Forecast!F{r_ebit}'),
    (22, 'eps_y4', f'=Forecast!F{r_eps}'),
    (23, 'fcff_y4', f'=Forecast!F{r_fcff}'),
    (24, 'discount_factor_y4', f'=Forecast!F{r_df}'),
    # FY5
    (25, 'revenue_y5', f'=Forecast!G{r_rev}'),
    (26, 'ebit_y5', f'=Forecast!G{r_ebit}'),
    (27, 'eps_y5', f'=Forecast!G{r_eps}'),
    (28, 'fcff_y5', f'=Forecast!G{r_fcff}'),
    (29, 'discount_factor_y5', f'=Forecast!G{r_df}'),
    # Valuation
    (30, 'wacc', '=Assumptions!B8'),
    (31, 'terminal_growth', '=Assumptions!B9'),
    (32, 'enterprise_value', '=DCF!B10'),
    (33, 'equity_value', '=DCF!B11'),
    (34, 'diluted_shares', '=Assumptions!B12'),
    (35, 'value_per_share', '=DCF!B12'),
    # MC stats
    (36, 'mc_n', '=MC_Trials!B2'),
    (37, 'mc_p10', '=MC_Trials!B6'),
    (38, 'mc_p25', '=MC_Trials!B7'),
    (39, 'mc_p50', '=MC_Trials!B8'),
    (40, 'mc_p75', '=MC_Trials!B9'),
    (41, 'mc_p90', '=MC_Trials!B10'),
    (42, 'mc_mean', '=MC_Trials!B11'),
]

for row, key, formula in outputs_map:
    ws_o.cell(row=row, column=1, value=key)
    ws_o.cell(row=row, column=2, value='')
    ws_o.cell(row=row, column=3, value=formula)

# ============================================================
# Save
# ============================================================
wb.save('/app/output/model.xlsx')
print("model.xlsx built successfully.")

# Quick verification: compute values with data_only=False to confirm formulas
# Also compute with python to verify
print("\n--- Python verification ---")
fy24_rev = 245122
g = 0.14
margin = 0.4464
tax = 0.1823
da_r = 0.062
capex_r = 0.1814
nwc_r = -0.1585
wacc = 0.08
tg = 0.03
net_debt = 44937
cash = 75543
shares = 7469
int_rate = 0.045
fy24_nwc = -38846

revs = []
for yr in range(5):
    if yr == 0:
        r = fy24_rev * (1+g)
    else:
        r = revs[-1] * (1+g)
    revs.append(r)

for yr in range(5):
    r = revs[yr]
    ebit = r * margin
    da = r * da_r
    capex = r * capex_r
    if yr == 0:
        prev_r = fy24_rev
        prev_nwc = fy24_nwc
    else:
        prev_r = revs[yr-1]
        prev_nwc = prev_r * nwc_r
    nwc = r * nwc_r
    dnwc = nwc - prev_nwc
    rc = da - capex - dnwc
    fcff = ebit * (1-tax) + rc
    df = 1/(1+wacc)**(yr+1)
    int_exp = net_debt * int_rate
    pretax = ebit - int_exp
    ni = pretax * (1-tax)
    eps = ni / shares
    print(f"FY{yr+1}: rev={r:,.0f} ebit={ebit:,.0f} eps={eps:.2f} da={da:,.0f} capex={capex:,.0f} dnwc={dnwc:,.0f} rc={rc:,.0f} fcff={fcff:,.0f} df={df:.4f}")

# TV
fcff5 = revs[4] * margin * (1-tax) + (revs[4]*da_r - revs[4]*capex_r - (revs[4]*nwc_r - revs[3]*nwc_r))
tv = fcff5 * (1+tg) / (wacc - tg)
pv_fcffs = 0
for yr in range(5):
    r = revs[yr]
    ebit = r * margin
    da = r * da_r
    capex = r * capex_r
    if yr == 0:
        prev_r = fy24_rev
        prev_nwc = fy24_nwc
    else:
        prev_r = revs[yr-1]
        prev_nwc = prev_r * nwc_r
    nwc = r * nwc_r
    dnwc = nwc - prev_nwc
    rc = da - capex - dnwc
    fcff = ebit * (1-tax) + rc
    pv_fcffs += fcff / (1+wacc)**(yr+1)

pv_tv = tv / (1+wacc)**5
ev = pv_fcffs + pv_tv
eq = ev + cash - net_debt
vps = eq / shares
print(f"\nTV={tv:,.0f}, PV_TV={pv_tv:,.0f}, PV_FCFFs={pv_fcffs:,.0f}")
print(f"EV={ev:,.0f}, Equity={eq:,.0f}, VPS=${vps:.2f}")