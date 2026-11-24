from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
import os
import subprocess
import re
import xml.etree.ElementTree as ET

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path('/app')
OUT = ROOT / 'output'
RAW = OUT / 'raw'
CONTRACT = json.loads((ROOT / 'data/retrieval_contract.json').read_text(encoding='utf-8'))
COMPANYFACTS = json.loads((RAW / 'CIK0000829224.json').read_text(encoding='utf-8'))
SEC_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000829224.json'
UST_URL = 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page=&_format=csv'
FILING_URL = 'https://www.sec.gov/Archives/edgar/data/829224/000082922424000057/sbux-20240929.htm'
OBSERVED_AT = '2026-11-23T00:03:51Z'


def json_write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fetch_time(filename):
    return datetime.fromtimestamp((RAW / filename).stat().st_mtime, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def parse_original_xbrl():
    root = ET.parse(RAW / 'sbux-20240929_htm.xml').getroot()
    ns = '{http://www.xbrl.org/2003/instance}'
    contexts = {}
    for context in root.findall(ns + 'context'):
        period = context.find(ns + 'period')
        contexts[context.attrib['id']] = {
            'start': period.findtext(ns + 'startDate'),
            'end': period.findtext(ns + 'endDate'),
            'instant': period.findtext(ns + 'instant'),
            'has_dimensions': context.find(ns + 'entity/' + ns + 'segment') is not None,
        }
    facts = {}
    for element in root:
        if 'contextRef' not in element.attrib or 'unitRef' not in element.attrib:
            continue
        tag = element.tag.split('}')[-1]
        context = contexts[element.attrib['contextRef']]
        if context['has_dimensions']:
            continue
        if context['start'] == '2023-10-02' and context['end'] == '2024-09-29':
            period = 'FY2024'
        elif context['instant'] == '2024-09-29':
            period = '2024-09-29'
        else:
            continue
        facts.setdefault((tag, period), []).append(float(element.text))
    return facts


original_facts = parse_original_xbrl()
items = []
sec_observed_at = fetch_time('CIK0000829224.json')
original_observed_at = fetch_time('sbux-20240929_htm.xml')

for spec in CONTRACT['required_fields']:
    fid = spec['field_id']
    if fid == 'treasury_10y':
        continue
    chosen = None
    notes = []
    for tag in spec['allowed_tags']:
        tag_data = COMPANYFACTS['facts'].get('us-gaap', {}).get(tag)
        if not tag_data:
            notes.append(f'{tag}:标签不存在')
            continue
        unit = spec['raw_unit']
        candidates = []
        for fact in tag_data.get('units', {}).get(unit, []):
            valid = fact.get('form') in ('10-K', '10-K/A')
            valid = valid and fact.get('filed', '9999-99-99') <= CONTRACT['information_cutoff']
            valid = valid and fact.get('end') == spec['end']
            if spec['kind'] == 'flow':
                valid = valid and fact.get('start') == spec['start']
            if valid:
                candidates.append(fact)
        notes.append(f'{tag}:合规事实{len(candidates)}条')
        if candidates and chosen is None:
            candidates.sort(key=lambda x: (x.get('filed', ''), x.get('accn', '')))
            chosen = (tag, candidates[-1], unit)
    if chosen is None:
        items.append({
            'field_id': fid, 'value': None, 'unit': spec['reported_unit'],
            'period_start': spec.get('start'), 'period_end': spec['end'],
            'source_id': 'SEC_COMPANYFACTS', 'source_url': SEC_URL,
            'source_file': 'CIK0000829224.json', 'field': None, 'form': None,
            'filed': None, 'accession': None, 'observed_at': sec_observed_at,
            'status': 'failed', 'error': '允许标签均无可合规采用的事实；未猜测、未补零',
            'tag_selection_notes': notes,
        })
        continue
    tag, fact, raw_unit = chosen
    value = fact['val'] / 1_000_000
    period = 'FY2024' if spec['kind'] == 'flow' else spec['end']
    matches = original_facts.get((tag, period), [])
    assert matches, f'原始XBRL未找到 {fid}'
    assert all(abs(v - fact['val']) < 0.01 for v in matches), f'原始XBRL数值不一致 {fid}'
    items.append({
        'field_id': fid,
        'value': value,
        'unit': spec['reported_unit'],
        'period_start': spec.get('start'),
        'period_end': spec['end'],
        'source_id': 'SEC_COMPANYFACTS',
        'source_url': SEC_URL,
        'source_file': 'raw/CIK0000829224.json',
        'field': tag,
        'form': fact['form'],
        'filed': fact['filed'],
        'accession': fact['accn'],
        'observed_at': sec_observed_at,
        'status': 'success',
        'error': None,
        'raw_value': fact['val'],
        'raw_unit': raw_unit,
        'tag_selection_notes': notes,
        'selection_rule': '按允许标签顺序取首个期间、单位、form及filed均合规的合并事实；USD或shares除以1,000,000',
        'original_filing_verification': {
            'source_id': 'SEC_COMPANYFACTS',
            'source_url': FILING_URL,
            'source_file': 'raw/sbux-20240929_htm.xml',
            'observed_at': original_observed_at,
            'context': 'FY2024无维度合并上下文' if spec['kind'] == 'flow' else '2024-09-29无维度时点上下文',
            'match': True,
            'note': '同一10-K原始XBRL上下文复核，不构成独立会计事实'
        }
    })

with (RAW / 'ust_daily_2024.csv').open(newline='', encoding='utf-8-sig') as f:
    treasury_rows = list(csv.DictReader(f))
rate_row = next((r for r in treasury_rows if r['Date'] == '11/27/2024' and r['10 Yr'].strip()), None)
assert rate_row is not None, '2024-11-27官方10Yr无值'
items.append({
    'field_id': 'treasury_10y',
    'value': float(rate_row['10 Yr']) / 100,
    'unit': 'decimal',
    'period_start': '2024-11-27',
    'period_end': '2024-11-27',
    'source_id': 'UST_DAILY',
    'source_url': UST_URL,
    'source_file': 'raw/ust_daily_2024.csv',
    'field': 'DGS10',
    'form': 'Daily Treasury Par Yield Curve Rates',
    'filed': '2024-11-27',
    'accession': None,
    'observed_at': fetch_time('ust_daily_2024.csv'),
    'status': 'success',
    'error': None,
    'raw_value': float(rate_row['10 Yr']),
    'raw_unit': 'percent',
    'source_column': '10 Yr',
    'selection_rule': '2024-11-27有官方非空观测，直接采用；4.25%除以100换算为0.0425'
})
assert len(items) == 16
assert [i['field_id'] for i in items] == [s['field_id'] for s in CONTRACT['required_fields']]
assert all(i['status'] == 'success' for i in items)

manifest = {
    'information_cutoff': CONTRACT['information_cutoff'],
    'fiscal_year': 'FY2024',
    'retrieval_policy': '只使用SEC原始申报与财政部；当前网站仅作事实载体，历史值严格限定filed<=2024-11-27',
    'retrieval_attempts': [
        {'url': SEC_URL, 'http_status': 200, 'observed_at': sec_observed_at, 'outcome': '成功'},
        {'url': 'https://www.sec.gov/Archives/edgar/data/829224/000082922424000062/sbux-20240929.htm', 'http_status': 404, 'observed_at': sec_observed_at, 'outcome': '候选申报号路径失败；未用其取数，随后由companyfacts确定正确申报号'},
        {'url': FILING_URL, 'http_status': 200, 'observed_at': original_observed_at, 'outcome': '成功'},
        {'url': 'https://www.sec.gov/Archives/edgar/data/829224/000082922424000057/sbux-20240929_htm.xml', 'http_status': 200, 'observed_at': original_observed_at, 'outcome': '成功'},
        {'url': UST_URL, 'http_status': 200, 'observed_at': fetch_time('ust_daily_2024.csv'), 'outcome': '成功'},
    ],
    'raw_files': [],
    'network': {
        'declared_mode': 'IPv4 sidecar allowlist',
        'runtime_probes': '对data.sec.gov、www.sec.gov及home.treasury.gov使用curl -4，均成功取得目标资源；候选错误路径另有一次404',
        'enforcement_status': '配置存在不等于白名单已经验证生效；本轮只验证允许域名的IPv4可达性，未做阻断对照测试，不能据此确认白名单已经验证生效',
        'ir_used': False,
    },
    'conflicts': [
        {'topic': '合并净利润与归母净利润', 'profit_loss': 3762.3, 'net_income_loss': 3760.9, 'difference': 1.4, 'resolution': '按合同优先采用含非控股权益的ProfitLoss；1.4百万美元为非控股权益'},
        {'topic': '现金标签口径', 'cash_and_cash_equivalents': 'CashAndCashEquivalentsAtCarryingValue无合规事实', 'selected': 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents=3286.2', 'resolution': '严格遵循允许标签顺序；采用值为该标签原值，不声称其与不受限现金相等'},
        {'topic': '债务标签', 'short_term_borrowings': 0.0, 'selected_current_debt': 1248.9, 'resolution': 'LongTermDebtCurrent优先于ShortTermBorrowings；不将零值短期借款另行叠加'},
    ],
}
for filename in ['CIK0000829224.json', 'sbux-20240929.htm', 'sbux-20240929_htm.xml', 'ust_daily_2024.csv']:
    path = RAW / filename
    manifest['raw_files'].append({'file': 'raw/' + filename, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'observed_at': fetch_time(filename)})
json_write(OUT / 'retrieval_log.json', manifest)
json_write(OUT / 'sources.json', {
    'schema_version': 'dcf-v3-w-retrieval-v1',
    'company': CONTRACT['company'],
    'information_cutoff': CONTRACT['information_cutoff'],
    'fiscal_year': CONTRACT['fiscal_year'],
    'items': items,
})

wb = Workbook()
wb.remove(wb.active)
wb.properties.title = 'Starbucks FY2024 基准五年DCF'
wb.properties.subject = '限定来源取数与五年DCF'
wb.properties.creator = 'Kimi Code CLI'
wb.calculation.calcMode = 'auto'
wb.calculation.fullCalcOnLoad = True
wb.calculation.forceFullCalc = True
wb.calculation.calcOnSave = True

navy = '17365D'
blue = '2F75B5'
light_blue = 'D9EAF7'
light_gray = 'E7E6E6'
input_fill = 'FFF2CC'
green = 'E2F0D9'
white = 'FFFFFF'
thin_gray = Side(style='thin', color='B7B7B7')
all_border = Border(left=thin_gray, right=thin_gray, top=thin_gray, bottom=thin_gray)
font_cn = 'Noto Sans CJK SC'
amount_fmt = '#,##0.0;[Red](#,##0.0)'
percent_fmt = '0.00%'
decimal_fmt = '0.0000'
per_share_fmt = '$#,##0.00'


def new_sheet(name, title, subtitle):
    ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    ws['A1'] = title
    ws['A1'].font = Font(name=font_cn, size=16, bold=True, color=white)
    ws['A1'].fill = PatternFill('solid', fgColor=navy)
    ws.merge_cells('A1:H1')
    ws['A2'] = subtitle
    ws['A2'].font = Font(name=font_cn, size=10, color='666666')
    ws.merge_cells('A2:H2')
    ws.freeze_panes = 'A4'
    for row in ws.iter_rows():
        for cell in row:
            cell.font = Font(name=font_cn, size=10)
    return ws


def style_header(ws, row, start, end):
    for col in range(start, end + 1):
        cell = ws.cell(row, col)
        cell.font = Font(name=font_cn, size=10, bold=True, color=white)
        cell.fill = PatternFill('solid', fgColor=blue)
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = all_border


def style_body(ws, min_row, max_row, min_col, max_col):
    for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        for cell in row:
            cell.border = all_border
            cell.alignment = Alignment(vertical='top', wrap_text=True)


# Sources：A/B/C为机器可读的唯一历史取数入口。
sources_ws = new_sheet('Sources', '限定来源取数', '信息截止：2024-11-27；基准：FY2024；金额：百万美元；股数：百万股。原始值只在本页录入。')
headers = ['field_id', '取数值', '单位', '数据项', '期间开始', '期间结束', 'source_id', 'XBRL标签/字段', 'form', 'filed', 'accession', 'source_url', 'observed_at', '状态', 'source_file']
for c, h in enumerate(headers, 1):
    sources_ws.cell(4, c, h)
style_header(sources_ws, 4, 1, len(headers))
source_rows = {}
for r, item in enumerate(items, 5):
    source_rows[item['field_id']] = r
    values = [item['field_id'], item['value'], item['unit'], next(s['label'] for s in CONTRACT['required_fields'] if s['field_id'] == item['field_id']), item['period_start'], item['period_end'], item['source_id'], item['field'], item['form'], item['filed'], item['accession'], item['source_url'], item['observed_at'], item['status'], item['source_file']]
    for c, value in enumerate(values, 1):
        sources_ws.cell(r, c, value)
    sources_ws.cell(r, 2).fill = PatternFill('solid', fgColor=input_fill)
    sources_ws.cell(r, 2).number_format = decimal_fmt if item['unit'] == 'decimal' else amount_fmt
    sources_ws.cell(r, 12).hyperlink = item['source_url']
    sources_ws.cell(r, 12).style = 'Hyperlink'
style_body(sources_ws, 5, 20, 1, len(headers))
sources_ws.auto_filter.ref = f'A4:O20'
sources_ws.freeze_panes = 'D5'
for col, width in {'A': 28, 'B': 14, 'C': 17, 'D': 31, 'E': 13, 'F': 13, 'G': 21, 'H': 73, 'I': 13, 'J': 13, 'K': 24, 'L': 68, 'M': 22, 'N': 12, 'O': 30}.items():
    sources_ws.column_dimensions[col].width = width


def sref(fid):
    return f"Sources!$B${source_rows[fid]}"


# Assumptions：开放假设；历史派生值由Sources公式计算。
assumptions = new_sheet('Assumptions', '经营与估值假设', '黄色为开放输入；绿色为Sources活公式派生。无股价、目标价或市场一致预期输入。')
assumptions['A4'] = '假设键 / 语义ID'
assumptions['B4'] = '取值'
assumptions['C4'] = '单位'
assumptions['D4'] = '中文说明与理由'
assumptions['E4'] = '输入属性'
assumptions['F4'] = 'Sources锚点'
style_header(assumptions, 4, 1, 6)
assumption_rows = {}
assumption_specs = [
    ('initial_growth', 0.03, 'decimal', 'FY1收入增长3%；温和起步的开放情景，FY2–FY5线性收敛至terminal_growth', '开放输入', None),
    ('steady_ebit_margin', f'={sref("operating_income")}/{sref("revenue")}', 'decimal', '以FY2024实际EBIT率为锚，预测期保持不变', 'Sources派生', 'operating_income / revenue'),
    ('tax_rate', f'={sref("income_tax")}/{sref("pretax_income")}', 'decimal', '以FY2024实际所得税费用/税前利润为有效税率', 'Sources派生', 'income_tax / pretax_income'),
    ('da_to_revenue', f'={sref("da")}/{sref("revenue")}', 'decimal', '以FY2024折旧摊销占收入比例为锚', 'Sources派生', 'da / revenue'),
    ('capex_to_revenue', f'={sref("capex")}/{sref("revenue")}', 'decimal', '以FY2024现金资本开支占收入比例为锚', 'Sources派生', 'capex / revenue'),
    ('treasury_10y', f'={sref("treasury_10y")}', 'decimal', '2024-11-27官方10 Yr为4.25%，换算为0.0425', 'Sources派生', 'treasury_10y'),
    ('risk_premium', 0.03, 'decimal', '开放风险溢价假设3个百分点；不是可观察市场一致预期', '开放输入', None),
    ('wacc', '=B10+B11', 'decimal', '简化WACC=10年期国债收益率+开放风险溢价；WACC>g', '公式派生', 'treasury_10y'),
    ('terminal_growth', 0.02, 'decimal', '永续名义增长2%；低于WACC的开放长期情景', '开放输入', None),
]
for row, spec in enumerate(assumption_specs, 5):
    key, value, unit, reason, kind, anchor = spec
    assumption_rows[key] = row
    for col, val in enumerate([key, value, unit, reason, kind, anchor], 1):
        assumptions.cell(row, col, val)
    assumptions.cell(row, 2).number_format = percent_fmt
    if kind == '开放输入':
        assumptions.cell(row, 2).fill = PatternFill('solid', fgColor=input_fill)
    else:
        assumptions.cell(row, 2).fill = PatternFill('solid', fgColor=green)
assumptions['A15'] = 'wacc_minus_g'
assumptions['B15'] = '=B12-B13'
assumptions['C15'] = 'decimal'
assumptions['D15'] = 'Gordon模型要求大于零；同时检查WACC>g'
assumptions['E15'] = '公式校验'
assumptions['F15'] = 'wacc / terminal_growth'
assumptions['B15'].number_format = percent_fmt
assumptions['A16'] = 'wacc_gt_terminal_growth'
assumptions['B16'] = '=IF(B12>B13,"通过","失败")'
assumptions['C16'] = '状态'
assumptions['D16'] = '扰动时必须保持通过'
assumptions['E16'] = '公式校验'
style_body(assumptions, 5, 16, 1, 6)
for col, width in {'A': 30, 'B': 17, 'C': 13, 'D': 65, 'E': 15, 'F': 34}.items():
    assumptions.column_dimensions[col].width = width


def aref(key):
    return f"Assumptions!$B${assumption_rows[key]}"


# Forecast：C:G为FY1-FY5，B列为FY0实际/公式基准。
forecast = new_sheet('Forecast', '五年 FCFF 预测', 'FY1=FY2025E，FY5=FY2029E；C:G严格对应FY1–FY5。NWC按合同保留负营运资本符号。')
forecast['A4'] = '语义键'
forecast['B4'] = 'FY2024A / FY0'
for i, col in enumerate(range(3, 8), 1):
    forecast.cell(4, col, f'FY{i} / FY{2024+i}E')
style_header(forecast, 4, 1, 7)
forecast_rows = {
    'revenue': 5,
    'revenue_growth': 6,
    'ebit': 7,
    'ebit_margin': 8,
    'tax_rate': 9,
    'nopat': 10,
    'da': 11,
    'capex': 12,
    'nwc': 13,
    'delta_nwc': 14,
    'reinvestment_component': 15,
    'fcff': 16,
    'discount_years': 17,
    'discount_factor': 18,
    'fcff_present_value': 19,
}
labels = {
    'revenue': 'revenue', 'revenue_growth': 'revenue_growth', 'ebit': 'ebit', 'ebit_margin': 'ebit_margin',
    'tax_rate': 'tax_rate', 'nopat': 'nopat', 'da': 'da', 'capex': 'capex', 'nwc': 'nwc',
    'delta_nwc': 'delta_nwc', 'reinvestment_component': 'reinvestment_component', 'fcff': 'fcff',
    'discount_years': 'discount_years', 'discount_factor': 'discount_factor', 'fcff_present_value': 'fcff_present_value',
}
for key, row in forecast_rows.items():
    forecast.cell(row, 1, key)
forecast['B5'] = f'={sref("revenue")}'
forecast['B7'] = f'={sref("operating_income")}'
forecast['B8'] = '=B7/B5'
forecast['B9'] = f'={aref("tax_rate")}'
forecast['B10'] = '=B7*(1-B9)'
forecast['B11'] = f'={sref("da")}'
forecast['B12'] = f'={sref("capex")}'
forecast['B13'] = f'={sref("current_assets")}-{sref("cash")}-{sref("short_term_investments")}-({sref("current_liabilities")}-{sref("current_debt")})'
forecast['B15'] = '=B11-B12'
for col in range(3, 8):
    letter = get_column_letter(col)
    prev = get_column_letter(col - 1)
    n = col - 2
    forecast.cell(forecast_rows['revenue_growth'], col, f'={aref("initial_growth")}' if n == 1 else f'={aref("initial_growth")}+({aref("terminal_growth")}-{aref("initial_growth")})*({n}-1)/4')
    forecast.cell(forecast_rows['revenue'], col, f'={prev}{forecast_rows["revenue"]}*(1+{letter}{forecast_rows["revenue_growth"]})')
    forecast.cell(forecast_rows['ebit'], col, f'={letter}{forecast_rows["revenue"]}*{aref("steady_ebit_margin")}')
    forecast.cell(forecast_rows['ebit_margin'], col, f'={letter}{forecast_rows["ebit"]}/{letter}{forecast_rows["revenue"]}')
    forecast.cell(forecast_rows['tax_rate'], col, f'={aref("tax_rate")}')
    forecast.cell(forecast_rows['nopat'], col, f'={letter}{forecast_rows["ebit"]}*(1-{letter}{forecast_rows["tax_rate"]})')
    forecast.cell(forecast_rows['da'], col, f'={letter}{forecast_rows["revenue"]}*{aref("da_to_revenue")}')
    forecast.cell(forecast_rows['capex'], col, f'={letter}{forecast_rows["revenue"]}*{aref("capex_to_revenue")}')
    forecast.cell(forecast_rows['nwc'], col, f'={prev}{forecast_rows["nwc"]}*({letter}{forecast_rows["revenue"]}/{prev}{forecast_rows["revenue"]})')
    forecast.cell(forecast_rows['delta_nwc'], col, f'=$B${forecast_rows["nwc"]}*({letter}{forecast_rows["revenue"]}/$B${forecast_rows["revenue"]}-1)' if n == 1 else f'={letter}{forecast_rows["nwc"]}-{prev}{forecast_rows["nwc"]}')
    forecast.cell(forecast_rows['reinvestment_component'], col, f'={letter}{forecast_rows["da"]}-{letter}{forecast_rows["capex"]}-{letter}{forecast_rows["delta_nwc"]}')
    forecast.cell(forecast_rows['fcff'], col, f'={letter}{forecast_rows["ebit"]}*(1-{aref("tax_rate")})+{letter}{forecast_rows["reinvestment_component"]}')
    forecast.cell(forecast_rows['discount_years'], col, n)
    forecast.cell(forecast_rows['discount_factor'], col, f'=1/(1+{aref("wacc")})^{letter}{forecast_rows["discount_years"]}')
    forecast.cell(forecast_rows['fcff_present_value'], col, f'={letter}{forecast_rows["fcff"]}*{letter}{forecast_rows["discount_factor"]}')
for row in forecast_rows.values():
    for col in range(2, 8):
        forecast.cell(row, col).number_format = amount_fmt
for key in ['revenue_growth', 'ebit_margin', 'tax_rate', 'discount_factor']:
    for col in range(2, 8):
        forecast.cell(forecast_rows[key], col).number_format = percent_fmt if key != 'discount_factor' else '0.000000'
for col in range(2, 8):
    forecast.cell(forecast_rows['discount_years'], col).number_format = '0'
style_body(forecast, 5, 19, 1, 7)
forecast.column_dimensions['A'].width = 30
forecast.column_dimensions['B'].width = 20
for col in range(3, 8):
    forecast.column_dimensions[get_column_letter(col)].width = 18

# DCF：显性期、Gordon终值与股权桥。
dcf = new_sheet('DCF', 'DCF 与股权桥', '单位除特别注明外均为百万美元；终值再折现五年，股权桥不加回任何其他债务或现金项目。')
dcf['A4'] = '语义键'
dcf['B4'] = '单位'
dcf['C4'] = '数值'
dcf['D4'] = '公式与口径'
style_header(dcf, 4, 1, 4)
dcf_rows = {}
dcf_specs = [
    ('explicit_pv', 'USD_millions', '=SUM(Forecast!C19:G19)', 'FY1–FY5 FCFF现值之和'),
    ('terminal_fcff', 'USD_millions', '=Forecast!G16*(1+' + aref('terminal_growth') + ')', 'FY5 FCFF×(1+g)'),
    ('terminal_value', 'USD_millions', '=C6/(' + aref('wacc') + '-' + aref('terminal_growth') + ')', 'Gordon终值，未折现'),
    ('terminal_discount_factor', 'decimal', '=Forecast!G18', 'FY5折现因子，折现五年'),
    ('terminal_present_value', 'USD_millions', '=C7*C8', 'Gordon终值现值'),
    ('enterprise_value', 'USD_millions', '=C5+C9', '显性期现值+终值现值'),
    ('cash', 'USD_millions', '=' + sref('cash'), '按指定现金标签原值加回一次'),
    ('short_term_investments', 'USD_millions', '=' + sref('short_term_investments'), '短期投资加回一次'),
    ('current_debt', 'USD_millions', '=' + sref('current_debt'), 'LongTermDebtCurrent；扣除一次'),
    ('noncurrent_debt', 'USD_millions', '=' + sref('noncurrent_debt'), 'LongTermDebtNoncurrent；扣除一次'),
    ('equity_value', 'USD_millions', '=C10+C11+C12-C13-C14', '企业价值+现金+短期投资−当期债务−非当期债务'),
    ('diluted_shares', 'shares_millions', '=' + sref('diluted_shares'), 'FY2024加权平均稀释股数'),
    ('value_per_share', 'USD_per_share', '=C15/C16', '股权价值/加权平均稀释股数'),
]
for row, (key, unit, formula, desc) in enumerate(dcf_specs, 5):
    dcf_rows[key] = row
    for col, val in enumerate([key, unit, formula, desc], 1):
        dcf.cell(row, col, val)
    dcf.cell(row, 3).number_format = '0.000000' if key == 'terminal_discount_factor' else amount_fmt
style_body(dcf, 5, 17, 1, 4)
for col, width in {'A': 30, 'B': 18, 'C': 20, 'D': 68}.items():
    dcf.column_dimensions[col].width = width

# Outputs：A/C为指定输出，A语义ID，C活公式值。
outputs = new_sheet('Outputs', '估值输出', '输出由DCF活公式引用；本模型不使用股价判断结果是否合理。')
outputs['A4'] = '语义ID'
outputs['B4'] = '单位'
outputs['C4'] = '输出值'
style_header(outputs, 4, 1, 3)
for row, (key, unit, ref) in enumerate([
    ('enterprise_value', 'USD_millions', f'=DCF!C{dcf_rows["enterprise_value"]}'),
    ('equity_value', 'USD_millions', f'=DCF!C{dcf_rows["equity_value"]}'),
    ('value_per_share', 'USD_per_share', f'=DCF!C{dcf_rows["value_per_share"]}'),
], 5):
    outputs.cell(row, 1, key)
    outputs.cell(row, 2, unit)
    outputs.cell(row, 3, ref)
    outputs.cell(row, 3).number_format = per_share_fmt if key == 'value_per_share' else amount_fmt
style_body(outputs, 5, 7, 1, 3)
outputs['A9'] = '历史勾稽（引用Sources）'
outputs['A10'] = 'pretax_income_minus_tax_minus_consolidated_ni'
outputs['B10'] = 'USD_millions'
outputs['C10'] = '=Assumptions!B20'
outputs['C10'].number_format = amount_fmt
outputs['A11'] = 'wacc_gt_terminal_growth'
outputs['B11'] = '状态'
outputs['C11'] = '=Assumptions!B16'
for col, width in {'A': 57, 'B': 18, 'C': 24}.items():
    outputs.column_dimensions[col].width = width

# 全表统一字体与打印设置。
for ws in wb.worksheets:
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.horizontalCentered = False
    for row in ws.iter_rows():
        for cell in row:
            if cell.row > 2 and cell.font.name != font_cn:
                cell.font = Font(name=font_cn, size=cell.font.sz or 10, bold=cell.font.bold, color=cell.font.color)

model_path = OUT / 'model.xlsx'
wb.save(model_path)

# 应收账款只作诊断，不参与NWC以免重复计算。
assumptions['A17'] = 'receivables'
assumptions['B17'] = f'={sref("receivables")}'
assumptions['C17'] = 'USD_millions'
assumptions['D17'] = '应收账款净额诊断引用；已包含于流动资产合计，不再加到NWC，避免重复计算'
assumptions['E17'] = 'Sources派生'
assumptions['F17'] = 'receivables'
assumptions['B17'].number_format = amount_fmt
assumptions['A18'] = 'receivables_to_revenue'
assumptions['B18'] = '=B17/' + sref('revenue')
assumptions['C18'] = 'decimal'
assumptions['D18'] = '仅诊断：FY2024应收账款占合并收入比例，不作为独立预测驱动'
assumptions['E18'] = '公式派生'
assumptions['F18'] = 'receivables / revenue'
assumptions['B18'].number_format = percent_fmt
assumptions['A19'] = 'net_income_consolidated'
assumptions['B19'] = f'={sref("net_income_consolidated")}'
assumptions['C19'] = 'USD_millions'
assumptions['D19'] = '含非控股权益的合并净利润，供勾稽校验；不以归母净利润替代'
assumptions['E19'] = 'Sources派生'
assumptions['F19'] = 'net_income_consolidated'
assumptions['B19'].number_format = amount_fmt
assumptions['A20'] = 'pretax_to_net_income_difference'
assumptions['B20'] = f'={sref("pretax_income")}-{sref("income_tax")}-{sref("net_income_consolidated")}'
assumptions['C20'] = 'USD_millions'
assumptions['D20'] = 'pretax_income−income_tax−net_income_consolidated；不强行改为零'
assumptions['E20'] = '交叉勾稽公式'
assumptions['F20'] = 'pretax_income / income_tax / net_income_consolidated'
assumptions['B20'].number_format = amount_fmt
style_body(assumptions, 17, 20, 1, 6)
wb.save(model_path)

retrieval_map = {'schema_version': 'dcf-v3-w-retrieval-v1', 'workbook': 'model.xlsx', 'source_item_index_base': 0, 'items': []}
for index, item in enumerate(items):
    fid = item['field_id']
    if fid == 'revenue':
        sheet, cell = 'Forecast', 'B5'
    elif fid == 'operating_income':
        sheet, cell = 'Assumptions', 'B6'
    elif fid == 'pretax_income':
        sheet, cell = 'Assumptions', 'B7'
    elif fid == 'income_tax':
        sheet, cell = 'Assumptions', 'B7'
    elif fid == 'net_income_consolidated':
        sheet, cell = 'Assumptions', 'B19'
    elif fid == 'da':
        sheet, cell = 'Assumptions', 'B8'
    elif fid == 'capex':
        sheet, cell = 'Assumptions', 'B9'
    elif fid == 'diluted_shares':
        sheet, cell = 'DCF', 'C16'
    elif fid == 'cash':
        sheet, cell = 'DCF', 'C11'
    elif fid == 'short_term_investments':
        sheet, cell = 'DCF', 'C12'
    elif fid == 'receivables':
        sheet, cell = 'Assumptions', 'B17'
    elif fid == 'current_assets':
        sheet, cell = 'Forecast', 'B13'
    elif fid == 'current_liabilities':
        sheet, cell = 'Forecast', 'B13'
    elif fid == 'current_debt':
        sheet, cell = 'DCF', 'C13'
    elif fid == 'noncurrent_debt':
        sheet, cell = 'DCF', 'C14'
    elif fid == 'treasury_10y':
        sheet, cell = 'Assumptions', 'B10'
    else:
        raise AssertionError(fid)
    source_ref = f'Sources!$B${source_rows[fid]}'
    downstream = []
    for ws in wb.worksheets:
        if ws.title not in ('Assumptions', 'Forecast', 'DCF'):
            continue
        for row in ws.iter_rows():
            for formula_cell in row:
                formula = formula_cell.value
                if isinstance(formula, str) and formula.startswith('=') and source_ref in formula:
                    downstream.append(f'{ws.title}!{formula_cell.coordinate}')
    assert downstream, f'取数字段没有下游公式: {fid}'
    retrieval_map['items'].append({
        'field_id': fid,
        'source_item_index': index,
        'sheet': 'Sources',
        'cell': f'B{source_rows[fid]}',
        'used_by': f'{sheet}!{cell}',
        'downstream_cells': downstream,
        'reference_type': 'live_formula',
        'note': 'Sources页B列为唯一取数值；downstream_cells由工作簿公式扫描取得' if fid != 'receivables' else '应收账款用于诊断；NWC通过流动资产合计计算，不重复加回应收款'
    })
json_write(OUT / 'retrieval_map.json', retrieval_map)

values = {i['field_id']: i['value'] for i in items}
diff = values['pretax_income'] - values['income_tax'] - values['net_income_consolidated']
threshold = max(0.01, abs(values['net_income_consolidated']) * 0.02)
cross = {
    'schema_version': 'dcf-v3-w-retrieval-v1',
    'checks': [{
        'check_id': 'pretax_to_net_income',
        'formula': 'pretax_income - income_tax - net_income_consolidated',
        'source_item_indices': [items.index(next(i for i in items if i['field_id'] == k)) for k in ['pretax_income', 'income_tax', 'net_income_consolidated']],
        'inputs': {
            'pretax_income': {'source_item_index': 2, 'value': values['pretax_income'], 'unit': 'USD_millions'},
            'income_tax': {'source_item_index': 3, 'value': values['income_tax'], 'unit': 'USD_millions'},
            'net_income_consolidated': {'source_item_index': 4, 'value': values['net_income_consolidated'], 'unit': 'USD_millions'},
        },
        'difference': diff,
        'tolerance': threshold,
        'tolerance_formula': 'max(0.01, abs(net_income_consolidated) * 0.02)',
        'status': 'passed' if abs(diff) <= threshold else 'failed',
        'workbook_check': 'Outputs!C10',
        'note': '使用含非控股权益的ProfitLoss，不以归母NetIncomeLoss替代；差异未人为改成零'
    }]
}
json_write(OUT / 'cross_validation.json', cross)

memo = f'''# Starbucks Corporation（SBUX）五年 DCF memo

## 范围与取数

- 信息截止日为 **2024-11-27**，基准财年为 **FY2024**（2023-10-02至2024-09-29）。所有会计值来自同一已申报10-K：申报号 **0000829224-24-000057**，`filed=2024-11-20`，未使用截止日后重述值。
- SEC companyfacts 实际取数时间为 **{sec_observed_at}**，原始文件为 `raw/CIK0000829224.json`。另于 **{original_observed_at}** 取回该10-K原始HTML及 `sbux-20240929_htm.xml`，以无维度合并上下文逐项复核；同一申报的转载或复核不当作第二个独立会计事实。
- 美国财政部日度收益率CSV实际取数时间为 **{fetch_time('ust_daily_2024.csv')}**。2024-11-27有官方10 Yr观测4.25%，模型以小数 **0.0425** 引用，不需要回退日期。
- 金额除以1,000,000转为百万美元；股数除以1,000,000转为百万股。每项的URL、标签、期间、申报号、filed及实际取数时间见 `sources.json`，原始文件哈希见 `retrieval_log.json`。
- 公司IR未用于本次取数；所有会计事实及必要的原始XBRL均已由允许SEC域名直接取得。

## 开放假设与计算口径

- FY1收入增长为3%，FY2–FY5按固定步长线性收敛至永续增长2%。这是开放情景，不是公司指引或市场一致预期。
- EBIT率、有效税率、折旧摊销率和资本开支率分别以FY2024实际值为锚。WACC采用简化透明口径：2024-11-27的10年期国债收益率加3个百分点开放风险溢价，即7.25%。WACC>g为模型约束，而非市场断言。
- FCFF=EBIT×(1−税率)+D&A−CapEx−ΔNWC；折现年序为1至5。终值=FY5 FCFF×(1+g)/(WACC−g)，再乘FY5折现因子。
- FY0经营NWC=流动资产−现金−短期投资−(流动负债−当期债务)=**-4,516.9百万美元**。保留这一负值：FY1 ΔNWC=FY0 NWC×(FY1收入/FY0收入−1)，其后为本年减上年。应收账款已含于流动资产合计，只在Assumptions作诊断引用，不重复加回。
- 股权价值=企业价值+现金+短期投资−当期债务−非当期债务；再除以FY2024加权平均稀释股数。当期与非当期债务分别取一次，不使用含二者之和的LongTermDebt重复扣减。

## 交叉验证、失败与冲突

- `pretax_to_net_income`：4,969.6−1,207.3−3,762.3=**0.0百万美元**；容差为75.246百万美元，检查通过，未强行把差异改成零。
- `ProfitLoss`（含非控股权益）为3,762.3百万美元，归母`NetIncomeLoss`为3,760.9百万美元，差1.4百万美元。按合同采用前者，未混用。
- `CashAndCashEquivalentsAtCarryingValue`无合规事实，故按顺序采用`CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents=3,286.2百万美元`。这是指定标签原值，不额外声称其与不受限现金相等。
- 当期债务优先采用`LongTermDebtCurrent=1,248.9百万美元`；虽有`ShortTermBorrowings=0`这一实际披露，不覆盖优先标签，也不另行叠加。非当期债务为14,319.5百万美元，两者合计15,568.4百万美元，与`LongTermDebt`一致。
- 16项必需字段均成功取数，无缺失补零。曾经请求错误候选申报路径`000082922424000062`得到HTTP 404；未从该路径取数，后按companyfacts给出的正确申报号`000082922424000057`成功取回。此次路径失败不影响必需字段。

## 网络、复核与结果解释

- 运行环境声明采用IPv4 sidecar白名单。本轮使用`curl -4`对data.sec.gov、www.sec.gov与home.treasury.gov的目标请求成功；这只能证明相关允许域名的IPv4可达性。**配置存在不等于白名单已经验证生效**；未执行非允许域名阻断对照测试，因此不能声称白名单已经验证生效。
- `Sources`的A/B/C列为field_id、取数值、单位，下游均用活公式引用。`retrieval_map.json`逐项列出单元格链路。LibreOffice重算及WACC/g扰动结果以最终验证记录为准。
- 未寻找或使用当前或历史股价、现成目标价、市场一致预期，也未用股价判断DCF是否合理。`Outputs`中的企业价值、股权价值和每股价值均为本开放假设情景的模型结果，不是市场目标价。
'''
(OUT / 'memo.md').write_text(memo, encoding='utf-8')

# 工作簿内嵌入结构化取数与勾稽数据，便于只拿到xlsx时复核。
wb = load_workbook(model_path)
wb['Sources']['Q4'] = '完整元数据'
wb['Sources']['Q4'].font = Font(name=font_cn, bold=True, color=white)
wb['Sources']['Q4'].fill = PatternFill('solid', fgColor=blue)
wb['Sources']['Q4'].alignment = Alignment(wrap_text=True)
wb['Sources']['Q5'] = json.dumps({'items': items}, ensure_ascii=False, indent=2)
wb['Sources']['Q5'].alignment = Alignment(wrap_text=True, vertical='top')
wb['Sources'].column_dimensions['Q'].hidden = True
wb.save(model_path)

print('generated sources.json data, workbook, cross_validation.json, retrieval_map.json, memo.md')
print('source rows', source_rows)
print('model bytes', model_path.stat().st_size)
