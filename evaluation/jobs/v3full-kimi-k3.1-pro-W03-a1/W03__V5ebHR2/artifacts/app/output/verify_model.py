from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import zipfile

from openpyxl import load_workbook

OUT = Path('/app/output')
VERIFY = OUT / 'verification'
VERIFY.mkdir(exist_ok=True)
CONTRACT = json.loads(Path('/app/data/retrieval_contract.json').read_text(encoding='utf-8'))
SOURCES = json.loads((OUT / 'sources.json').read_text(encoding='utf-8'))
CROSS = json.loads((OUT / 'cross_validation.json').read_text(encoding='utf-8'))
RETRIEVAL_MAP = json.loads((OUT / 'retrieval_map.json').read_text(encoding='utf-8'))
COMPANYFACTS = json.loads((OUT / 'raw/CIK0000829224.json').read_text(encoding='utf-8'))
MODEL = OUT / 'model.xlsx'


def close(actual, expected, tol=1e-8):
    return math.isclose(actual, expected, rel_tol=tol, abs_tol=tol)


def independent_model(v, wacc, g):
    margin = v['operating_income'] / v['revenue']
    tax = v['income_tax'] / v['pretax_income']
    da_ratio = v['da'] / v['revenue']
    capex_ratio = v['capex'] / v['revenue']
    nwc0 = v['current_assets'] - v['cash'] - v['short_term_investments'] - (v['current_liabilities'] - v['current_debt'])
    revenues = []
    ebit = []
    da = []
    capex = []
    nwc = [nwc0]
    delta_nwc = []
    reinvestment = []
    fcff = []
    factors = []
    pv = []
    previous_revenue = v['revenue']
    growth = []
    for n in range(1, 6):
        rate = 0.03 if n == 1 else 0.03 + (g - 0.03) * (n - 1) / 4
        revenue = previous_revenue * (1 + rate)
        growth.append(rate)
        revenues.append(revenue)
        current_ebit = revenue * margin
        ebit.append(current_ebit)
        da.append(revenue * da_ratio)
        capex.append(revenue * capex_ratio)
        nwc.append(nwc[-1] * (revenue / previous_revenue))
        delta = nwc0 * (revenue / v['revenue'] - 1) if n == 1 else nwc[-1] - nwc[-2]
        delta_nwc.append(delta)
        component = da[-1] - capex[-1] - delta
        reinvestment.append(component)
        current_fcff = current_ebit * (1 - tax) + component
        fcff.append(current_fcff)
        factor = 1 / (1 + wacc) ** n
        factors.append(factor)
        pv.append(current_fcff * factor)
        previous_revenue = revenue
    terminal_value = fcff[-1] * (1 + g) / (wacc - g)
    terminal_pv = terminal_value * factors[-1]
    ev = sum(pv) + terminal_pv
    equity = ev + v['cash'] + v['short_term_investments'] - v['current_debt'] - v['noncurrent_debt']
    per_share = equity / v['diluted_shares']
    return {
        'growth': growth, 'revenue': revenues, 'ebit': ebit, 'da': da, 'capex': capex,
        'nwc': nwc[1:], 'nwc0': nwc0, 'delta_nwc': delta_nwc, 'reinvestment_component': reinvestment,
        'fcff': fcff, 'discount_factor': factors, 'fcff_present_value': pv,
        'terminal_value': terminal_value, 'terminal_present_value': terminal_pv,
        'explicit_pv': sum(pv), 'enterprise_value': ev, 'equity_value': equity, 'value_per_share': per_share,
        'margin': margin, 'tax_rate': tax, 'da_to_revenue': da_ratio, 'capex_to_revenue': capex_ratio,
    }


def check_workbook_values(path, wacc, g):
    wbv = load_workbook(path, data_only=True)
    v = {i['field_id']: i['value'] for i in SOURCES['items']}
    expected = independent_model(v, wacc, g)
    checks = []

    def record(name, actual, target, tol=1e-8):
        passed = close(actual, target, tol)
        checks.append({'check': name, 'actual': actual, 'expected': target, 'passed': passed})
        assert passed, f'{path}: {name}: {actual} != {target}'

    record('NWC0', wbv['Forecast']['B13'].value, expected['nwc0'])
    for row, key in [(5, 'revenue'), (7, 'ebit'), (11, 'da'), (12, 'capex'), (13, 'nwc'), (14, 'delta_nwc'), (15, 'reinvestment_component'), (16, 'fcff'), (18, 'discount_factor'), (19, 'fcff_present_value')]:
        for n, col in enumerate('CDEFG'):
            record(f'{key}_FY{n+1}', wbv['Forecast'][f'{col}{row}'].value, expected[key][n])
    for n, col in enumerate('CDEFG'):
        record(f'growth_FY{n+1}', wbv['Forecast'][f'{col}6'].value, expected['growth'][n])
    for cell, key in [('C5', 'explicit_pv'), ('C7', 'terminal_value'), ('C9', 'terminal_present_value'), ('C10', 'enterprise_value'), ('C15', 'equity_value'), ('C17', 'value_per_share')]:
        record(key, wbv['DCF'][cell].value, expected[key])
    record('Outputs_EV', wbv['Outputs']['C5'].value, expected['enterprise_value'])
    record('Outputs_equity', wbv['Outputs']['C6'].value, expected['equity_value'])
    record('Outputs_per_share', wbv['Outputs']['C7'].value, expected['value_per_share'])
    record('pretax_to_net_income', wbv['Outputs']['C10'].value, 0.0)
    assert wbv['Outputs']['C11'].value == '通过'
    assert wacc > g
    errors = []
    for ws in wbv.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith(('#REF!', '#VALUE!', '#DIV/0!', '#NAME?', '#N/A')):
                    errors.append(f'{ws.title}!{cell.coordinate}={cell.value}')
    assert not errors, errors
    return {'wacc': wacc, 'terminal_growth': g, 'formula_errors': errors, 'value_checks': checks, 'outputs': {k: expected[k] for k in ['enterprise_value', 'equity_value', 'value_per_share']}, 'fcff': expected['fcff']}


# 结构性检查与来源回溯。
assert zipfile.is_zipfile(MODEL)
wbf = load_workbook(MODEL, data_only=False)
wbv = load_workbook(MODEL, data_only=True)
assert wbf.sheetnames == ['Sources', 'Assumptions', 'Forecast', 'DCF', 'Outputs']
assert [wbf['Sources'][f'{c}4'].value for c in 'ABC'] == ['field_id', '取数值', '单位']
forecast_labels = {wbf['Forecast'][f'A{r}'].value: r for r in range(1, wbf['Forecast'].max_row + 1)}
for key in ['revenue', 'ebit', 'da', 'capex', 'delta_nwc', 'reinvestment_component', 'fcff', 'discount_factor']:
    assert key in forecast_labels
    for col in 'CDEFG':
        cell = wbf['Forecast'][f'{col}{forecast_labels[key]}']
        assert isinstance(cell.value, str) and cell.value.startswith('='), f'{key} {col}不是公式'
for cell in ['C5', 'C6', 'C7']:
    assert isinstance(wbf['Outputs'][cell].value, str) and wbf['Outputs'][cell].value.startswith('=')
for row in range(5, 18):
    assert isinstance(wbf['DCF'][f'C{row}'].value, str) and wbf['DCF'][f'C{row}'].value.startswith('=')

items = SOURCES['items']
assert len(items) == 16
assert [i['field_id'] for i in items] == [i['field_id'] for i in CONTRACT['required_fields']]
required_metadata = ['field_id', 'value', 'unit', 'period_start', 'period_end', 'source_id', 'source_url', 'source_file', 'field', 'form', 'filed', 'accession', 'observed_at', 'status', 'error']
allowed_domains = {'data.sec.gov', 'www.sec.gov', 'home.treasury.gov'}
raw_checks = []
for spec, item in zip(CONTRACT['required_fields'], items):
    for key in required_metadata:
        assert key in item, f'{item["field_id"]}缺少{key}'
    assert item['status'] == 'success'
    assert item['value'] is not None
    assert item['unit'] == spec['reported_unit']
    assert item['period_end'] == spec.get('end', spec.get('observation_date'))
    assert item.get('period_start') == spec.get('start', spec.get('observation_date'))
    assert item['field'] in spec['allowed_tags']
    assert item['field'] == spec['allowed_tags'][0] or any('合规事实0条' in x or '标签不存在' in x for x in item.get('tag_selection_notes', []))
    assert urlparse(item['source_url']).hostname in allowed_domains
    assert item['observed_at'] and item['observed_at'] != item['filed']
    assert item['error'] is None
    if item['source_id'] == 'SEC_COMPANYFACTS':
        assert item['filed'] <= CONTRACT['information_cutoff']
        assert item['form'] in ('10-K', '10-K/A')
        assert item['accession'] == '0000829224-24-000057'
        unit_data = COMPANYFACTS['facts']['us-gaap'][item['field']]['units'][item['raw_unit']]
        matched = [f for f in unit_data if f.get('accn') == item['accession'] and f.get('form') == item['form'] and f.get('filed') == item['filed'] and f.get('start') == item['period_start'] and f['end'] == item['period_end'] and f['val'] == item['raw_value']]
        assert len(matched) == 1, f'原始事实回溯失败 {item["field_id"]}'
        assert close(item['value'], item['raw_value'] / 1_000_000)
        assert item['original_filing_verification']['match'] is True
        assert urlparse(item['original_filing_verification']['source_url']).hostname in allowed_domains
        raw_checks.append({'field_id': item['field_id'], 'tag': item['field'], 'raw_value': item['raw_value'], 'converted_value': item['value'], 'accession': item['accession'], 'filed': item['filed'], 'match': True})
    else:
        assert item['source_id'] == 'UST_DAILY'
        assert item['period_start'] == item['period_end'] == '2024-11-27'
        assert item['raw_value'] == 4.25 and item['value'] == 0.0425
        assert item['filed'] == '2024-11-27'
        assert item['accession'] is None

for item, mapping in zip(items, RETRIEVAL_MAP['items']):
    assert mapping['field_id'] == item['field_id']
    assert mapping['source_item_index'] == items.index(item)
    assert mapping['sheet'] == 'Sources'
    assert wbf['Sources'][f'A{wbf["Sources"][mapping["cell"]].row}'].value == item['field_id']
    assert close(wbf['Sources'][mapping['cell']].value, item['value'])
    assert mapping['downstream_cells']
    for reference in mapping['downstream_cells']:
        sheet, coordinate = reference.split('!')
        formula = wbf[sheet][coordinate].value
        assert sheet in ('Assumptions', 'Forecast', 'DCF')
        assert isinstance(formula, str) and formula.startswith('=')
        assert f'Sources!$B${wbf["Sources"][mapping["cell"]].row}' in formula
    assert mapping['used_by'] in mapping['downstream_cells']

check = CROSS['checks'][0]
assert check['check_id'] == 'pretax_to_net_income'
assert check['source_item_indices'] == [2, 3, 4]
assert check['inputs']['pretax_income']['source_item_index'] == 2
assert check['inputs']['income_tax']['source_item_index'] == 3
assert check['inputs']['net_income_consolidated']['source_item_index'] == 4
assert close(check['difference'], items[2]['value'] - items[3]['value'] - items[4]['value'])
assert check['difference'] == 0.0 and check['status'] == 'passed'

# 基准文件必须已经由LibreOffice重算并保留缓存。
base = check_workbook_values(MODEL, 0.0725, 0.02)
base_values = base['outputs']

scenarios = [
    ('wacc_up_50bp', 0.0775, 0.02),
    ('wacc_down_50bp', 0.0675, 0.02),
    ('g_up_25bp', 0.0725, 0.0225),
    ('g_down_25bp', 0.0725, 0.0175),
    ('combined_up', 0.0775, 0.0225),
]
scenario_results = []
for name, wacc, g in scenarios:
    input_path = VERIFY / f'{name}_input.xlsx'
    out_dir = VERIFY / name
    out_dir.mkdir(exist_ok=True)
    wb = load_workbook(MODEL, data_only=False)
    wb['Assumptions']['B11'] = wacc - 0.0425
    wb['Assumptions']['B13'] = g
    wb.calculation.calcMode = 'auto'
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.save(input_path)
    result = subprocess.run(['libreoffice', '--headless', '--convert-to', 'xlsx', '--outdir', str(out_dir), str(input_path)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    recalculated = out_dir / input_path.name
    assert recalculated.exists()
    checked = check_workbook_values(recalculated, wacc, g)
    checked['scenario'] = name
    checked['libreoffice_stdout'] = result.stdout.strip()
    checked['libreoffice_stderr'] = result.stderr.strip()
    scenario_results.append(checked)

by_name = {s['scenario']: s for s in scenario_results}
assert by_name['wacc_up_50bp']['outputs']['enterprise_value'] < base_values['enterprise_value']
assert by_name['wacc_down_50bp']['outputs']['enterprise_value'] > base_values['enterprise_value']
assert by_name['g_up_25bp']['outputs']['enterprise_value'] > base_values['enterprise_value']
assert by_name['g_down_25bp']['outputs']['enterprise_value'] < base_values['enterprise_value']
assert by_name['combined_up']['outputs']['enterprise_value'] > by_name['wacc_up_50bp']['outputs']['enterprise_value']

# 再次确认最终交付文件仍为基准参数且保留公式和缓存。
wbf = load_workbook(MODEL, data_only=False)
wbv = load_workbook(MODEL, data_only=True)
assert close(wbv['Assumptions']['B12'].value, 0.0725)
assert close(wbv['Assumptions']['B13'].value, 0.02)
assert close(wbv['Outputs']['C7'].value, base_values['value_per_share'])
assert wbf['Assumptions']['B12'].value == '=B10+B11'

validation = {
    'observed_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
    'libreoffice_version': subprocess.run(['libreoffice', '--version'], capture_output=True, text=True, check=True).stdout.strip(),
    'status': 'passed',
    'workbook': 'model.xlsx',
    'workbook_sha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
    'sheet_structure': wbf.sheetnames,
    'sources_schema_and_raw_fact_checks': raw_checks,
    'retrieval_map_items': len(RETRIEVAL_MAP['items']),
    'cross_validation': check,
    'baseline_recalculation': base,
    'scenarios': scenario_results,
    'sensitivity_directions': {
        'wacc_up_50bp': 'EV下降，符合预期', 'wacc_down_50bp': 'EV上升，符合预期',
        'g_up_25bp': 'EV上升，符合预期', 'g_down_25bp': 'EV下降，符合预期',
        'combined_up': 'WACC上升且g上升时，EV高于仅WACC上升情形，符合预期'
    },
    'final_model_unchanged_after_sensitivity': True,
    'source_domains_observed': sorted({urlparse(i['source_url']).hostname for i in items}),
    'network_claim': '仅验证允许域名的IPv4可达性，不声称白名单已经验证生效',
}
(VERIFY / 'validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
summary = {
    'status': 'passed',
    'baseline_outputs': base_values,
    'scenarios': {s['scenario']: s['outputs'] for s in scenario_results},
    'raw_fact_checks': len(raw_checks),
    'retrieval_map_items': len(RETRIEVAL_MAP['items']),
    'baseline_formula_checks': len(base['value_checks']),
    'libreoffice_version': validation['libreoffice_version'],
    'workbook_sha256': validation['workbook_sha256'],
}
(OUT / 'verification_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
