#!/usr/bin/env python3
"""Map semantic truth fields to rubric atoms and hidden perturbation scopes."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def match(keys, pattern):
    regex = re.compile(pattern)
    return [k for k in keys if regex.search(k)]


def family(spec):
    return spec.get("family")


def predicates(task, spec, keys, report, variant=None):
    b = report.get("baseline", {})
    mismatches = set(variant.get("mismatches_all", variant.get("mismatches", [])) if isinstance(variant, dict) else [])
    mismatches = {x["key"] if isinstance(x, dict) else x for x in mismatches}
    base_bad = {x["key"] if isinstance(x, dict) else x for x in b.get("mismatches_all", b.get("mismatches", []))}
    static = set(b.get("nonformula_or_missing_all", b.get("nonformula_or_missing", [])))
    duplicates = set(b.get("duplicates", []))
    errors = b.get("errors_all", b.get("errors", []))
    links = b.get("links_all", b.get("links", []))
    kind = spec.get("c_structure")
    industry = spec.get("industry")
    def keys_for(pattern):
        return match(keys, pattern)
    def atom(pattern=None, custom=None):
        selected = keys_for(pattern) if pattern else []
        if custom:
            selected += custom(keys)
        selected = sorted(set(selected))
        if variant is not None:
            failed = bool(selected and not set(selected).isdisjoint(mismatches))
            return {"status": "fail" if failed else "pass" if selected else "not_executed", "evidence_keys": selected}
        if not selected:
            return {"status": "not_executed", "evidence_keys": []}
        failed = sorted((base_bad | static | duplicates) & set(selected))
        return {"status": "fail" if failed else "pass", "evidence_keys": selected, "failed_keys": failed[:30]}
    prefix = "(?:case_(?:base|bull|bear)_|segment_(?:alpha|beta)_|existing_|project_(?:atlas|boreal)_|gordon_|exit_)?"
    broad = prefix
    def scoped(pattern):
        return lambda: atom(prefix + pattern)
    scopes = {
        "02-FY": scoped(r"fy_(?:revenue|normalized_ebit)$"),
        "02-LTM": scoped(r"ltm_(?:revenue|normalized_ebit)$"),
        "02-REPORTED": scoped(r"(?:fy|ltm)_reported_ebit$"),
        "02-SBC": scoped(r"(?:fy|ltm)_normalized_ebit$|sbc_p\d+$"),
        "02-COLLECT": scoped(r"cash_collections_p\d+$"),
        "03-DRIVER": scoped(r"(?:driver_close|arr_close|stores_close|users_close|installed_base_close|loans_close)_p\d+$"),
        "03-AVERAGE": scoped(r"(?:average_driver|unit_price|full_revenue|revenue)_p\d+$"),
        "03-MARGIN": scoped(r"ebit_p\d+$"),
        "03-NWC": scoped(r"(?:nwc|delta_nwc)_p\d+$"),
        "B-NWC-OPEN": scoped(r"(?:nwc|delta_nwc|statement_(?:opening_nwc|delta_nwc))_p1$"),
        "03-DAYS": scoped(r"(?:accounts_receivable|inventory|accounts_payable|nwc)_p\d+$"),
        "03-DEBT": scoped(r"(?:debt_close|interest|new_borrowing|debt_repayment)_p\d+$"),
        "03-LEASE": scoped(r"(?:rou_|lease_liability_close)"),
        "03-NOL": scoped(r"(?:nol_close|tax|cash_taxes)_p\d+$"),
        "03-CAPEX": scoped(r"capex_p\d+$"),
        "04-BALANCE": scoped(r"(?:assets|liabilities_equity|balance_difference)_p\d+$"),
        "04-CASH": scoped(r"(?:cash_close|cash_link|cfo)_p\d+$"),
        "04-RE": scoped(r"(?:retained_earnings|net_income)_p\d+$"),
        "04-PPE": scoped(r"(?:ppe_close|ppe_depreciation|depreciation|da|capex)_p\d+$"),
        "05-FCFF": scoped(r"(?:fcff|unrisked_fcff|risk_adjusted_fcff|tax)_p\d+$"),
        "05-WACC": scoped(r"(?:levered_beta|cost_of_equity|wacc)$"),
        "05-DF": scoped(r"(?:discount_time|end_time|discount_factor)_p\d+$"),
        "05-DUAL": lambda: atom(r"(?:^|_)(?:tv_gordon|tv_exit|terminal_value)$"),
        "05-TV": scoped(r"(?:terminal_value|pv_terminal|tv_gordon|tv_exit)$"),
        "05-BRIDGE": lambda: atom(r"(?:^|_)equity_value$|^nav$"),
        "05-DILUTION": lambda: atom(r"(?:^|_)diluted_shares$"),
        "05-VPS": lambda: atom(r"(?:^|_)value_per_share$|^nav$"),
        "05-SENS": lambda: atom(r"valuation_(?:low|high)_vps$"),
        "06-FORMULA": lambda: {"status": "fail" if static else "pass", "failed_keys": sorted(static)[:30], "evidence_keys": sorted(static)},
        "06-RECALC": lambda: {"status": "fail" if base_bad or errors else "pass", "failed_keys": sorted(base_bad)[:30], "evidence_keys": sorted(base_bad)[:30]},
        "06-LINKS": lambda: {"status": "fail" if errors or links else "pass", "failed_keys": (errors + links)[:30]},
        "01-KEYS": lambda: {"status": "fail" if static or duplicates else "pass", "failed_keys": sorted(static | duplicates)[:30]},
        "01-FILE": lambda: {"status": "fail" if report.get("error") else "pass"},
        "06-FREE": lambda: {"status": "pass", "note": "语义键发现器实际读取成功；不依赖固定行号"},
        "C-SOTP-SEG": lambda: atom(r"^segment_(?:alpha|beta)_(?:revenue|ebit|fcff|nwc|capex)_p\d+$"),
        "C-SOTP-VAL": lambda: atom(r"^segment_(?:alpha|beta)_(?:enterprise_value|terminal_value|segment_enterprise_value)$"),
        "C-SOTP-SUM": lambda: atom(r"^(?:enterprise_value|segment_sum|sotp|corporate)"),
        "C-SOTP-BRIDGE": lambda: atom(r"^(?:equity_value|diluted_shares|value_per_share)$"),
        "C-PIPE-TIMING": lambda: atom(r"^project_(?:atlas|boreal)_revenue_p\d+$"),
        "C-PIPE-CAPEX": lambda: atom(r"^project_(?:atlas|boreal)_construction_capex_p\d+$"),
        "C-PIPE-PROB": lambda: atom(r"^project_(?:atlas|boreal)_(?:risk_adjusted_fcff_p\d+|success_probability|risk_adjusted_pv)$"),
        "C-PIPE-SUM": lambda: atom(r"^(?:pipeline_risk_adjusted_pv|enterprise_value|existing_enterprise_value)$"),
        "C-CASE-ISOLATE": lambda: atom(r"^case_(?:base|bull|bear)_(?:value_per_share|enterprise_value|terminal_value)$"),
        "C-MULTI-SPLIT": lambda: atom(r"^(?:gordon|exit)_(?:value_per_share|enterprise_value|terminal_value)$"),
        "C-IMPLIED-MULT": lambda: atom(r"^implied_ev_ebitda_gordon$"),
        "C-IMPLIED-G": lambda: atom(r"^implied_g_exit$"),
        "C-REVERSE": lambda: atom(r"^implied_wacc_market$"),
        "C-RANGE": lambda: atom(r"^valuation_(?:low|high)_vps$"),
        "X-IC-005": lambda: atom(r"^(?:gordon|exit)_pv_explicit$"),
        "X-IC-001": lambda: atom(r"(?:^|_)sensitivity_r3_c3$|center"),
        "X-IF-003": lambda: atom(r"sensitivity_r\d_c\d$"),
        "A-DRIVER": scoped(r"(?:arr_close|stores_close|effective_volume|product_volume|loans_close|total_production|rate_base_close|occupied_area|input|good_volume|sales)_p\d+$"),
        "A-METRIC": scoped(r"(?:arr_close|stores_close|effective_volume|nim|total_production|rate_base_close|occupied_area|good_volume)_p\d+$"),
        "A-SAAS-ARR": scoped(r"(?:arr_close|revenue)_p\d+$"),
        "A-SAAS-CAPRD": scoped(r"(?:capex|da|fcff)_p\d+$"),
        "A-RETAIL-SSS": scoped(r"(?:stores_close|revenue)_p\d+$"),
        "A-MFG-UTIL": scoped(r"(?:effective_volume|effective_capacity|input)_p\d+$"),
        "A-MFG-YIELD": scoped(r"(?:input|good_volume|sales|yield)_p\d+$"),
        "A-MFG-BOM": scoped(r"(?:consumption|consumption_cost)_p\d+$"),
        "A-MFG-PURCHASE": scoped(r"(?:purchase|raw_.*close|cogs)_p\d+$"),
        "A-MFG-INVENTORY": scoped(r"(?:raw_.*close|wip_close|finished_goods_close)_p\d+$"),
        "A-PHARMA-CLIFF": scoped(r"(?:product_volume|revenue)_p\d+$"),
        "A-PHARMA-FUNNEL": scoped(r"(?:patients|treated_patients|doses|revenue)_p\d+$"),
        "A-PHARMA-COMMITRD": scoped(r"(?:committed_rd|prelaunch_selling)_p\d+$"),
        "A-PHARMA-COMMERCIAL": scoped(r"commercial_(?:revenue|cogs|selling|ebit|fcff_before_tax)_p\d+$"),
        "C-PIPE-TIMING": scoped(r"(?:lead|next)_revenue_p\d+$"),
        "C-PIPE-CAPEX": scoped(r"(?:lead|next)_capex_p\d+$"),
        "C-PIPE-PROB": scoped(r"(?:lead|next)_(?:risked_(?:ebit|fcff_before_tax)_p\d+|pos_p\d+|risk_adjusted_pv)$"),
        "C-PIPE-SUM": lambda: atom(r"(?:lead|next)_(?:risk_adjusted|unrisked)_pv$|^(?:risk_adjusted_)?enterprise_value$"),
        "C-PIPE-FINITE": scoped(r"(?:lead|next)_(?:revenue|fcff_before_tax)_p\d+$"),
        "03-NOL": scoped(r"(?:nol_open|nol_used|nol_close|cash_tax)_p\d+$"),
        "A-BANK-NII": scoped(r"(?:loans_close|nim|net_interest_income|required_equity)_p\d+$"),
        "A-BANK-EQUITY": lambda: atom(r"(?:fcfe_p\d+|equity_value|equity_cost|terminal_value)$"),
        "A-ENERGY-DECLINE": scoped(r"(?:total_production|capex)_p\d+$"),
        "A-UTIL-RAB": scoped(r"(?:rate_base_close|revenue|da)_p\d+$"),
        "A-RE-NAV": lambda: atom(r"(?:noi_p\d+|property_value|nav|cap_rate)$"),
        "A-VALUATION": lambda: atom(r"(?:equity_value|nav|fcfe_p\d+|property_value_at_valuation)$"),
        "B-MIXLTM": scoped(r"ltm_(?:revenue|normalized_ebit|h1_revenue|bridge_quarter_revenue)$"),
    }
    # Hidden perturbations: each atom fails only when its evidence was actually
    # changed, rather than any unrelated wrong key zeroing every category.
    if variant is not None:
        scopes["C-CASE-SWITCH"] = scopes["C-CASE-ISOLATE"]
    scopes["B-RESIDUAL"] = scoped(r"(?:activity|revenue|fcff)_p1$")
    scopes["B-INTANG-ROLL"] = scoped(r"intangible_(?:close|amortization|additions)_p\d+$")
    scopes["B-INTANG-FCFF"] = scoped(r"(?:intangible_additions|fcff)_p\d+$")
    scopes["B-NWC-OPEN"] = scoped(r"(?:delta_nwc|nwc)_p1$")
    scopes["02-SBC"] = scoped(r"(?:^|_)(?:fy_normalized_ebit|ltm_normalized_ebit)$")
    return scopes


def atom_results(task, spec, report, variant=None):
    keys = list((variant or {}).get("expected", report.get("expected", {}))) if isinstance(report, dict) else []
    if not keys:
        # Injected by score_candidate for convenience; not persisted in graders.
        keys = report.get("baseline_keys", [])
    return predicates(task, spec, keys, report, variant)
