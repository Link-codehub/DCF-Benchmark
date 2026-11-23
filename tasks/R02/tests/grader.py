#!/usr/bin/env python3
"""Generic rubric executor. Numerical truths are read only from independently computed expected.json."""
import argparse, datetime as dt, hashlib, json, math, os, re, shutil, subprocess, tempfile, traceback
from pathlib import Path
from openpyxl import load_workbook
from workbook import discover_values, discover_formulas


def close(actual, expected):
    return isinstance(actual, (int, float)) and math.isfinite(actual) and abs(actual - expected) <= max(1e-6, 2e-8 * abs(expected))


def recalc(source, target, soffice):
    target = Path(target).resolve(); target.mkdir(parents=True, exist_ok=True)
    dest = target / source.name
    shutil.copy2(source, dest)
    profile = target / "profile"; profile.mkdir(exist_ok=True)
    command = [soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--convert-to", "xlsx", "--outdir", str(target / "recalc"), str(dest)]
    run = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
    result = target / "recalc" / source.name
    if run.returncode or not result.exists():
        raise RuntimeError(f"LibreOffice recalc failed: {run.stdout[-500:]} {run.stderr[-500:]}")
    return result


def perturb(source, target, changes):
    wb = load_workbook(source)
    if "Inputs" not in wb.sheetnames: raise ValueError("candidate must preserve the public semantic Inputs sheet")
    ws = wb["Inputs"]
    for key, expected in changes.items():
        group, field, *vector = key.split(".")
        semantic = group + "." + field
        matches = [row[0].row for row in ws.iter_rows() if row[0].value == semantic]
        if len(matches) != 1: raise ValueError(f"candidate input key {semantic} not found exactly once")
        col = 3 + int(vector[0]) if vector else 3
        cell = ws.cell(matches[0], col)
        old = cell.value
        if not isinstance(old, (int, float)): raise ValueError(f"input {semantic} is not numeric")
        cell.value = expected
    # Remove formulas with external workbook references before recalculation; do not add answer formulas.
    wb.calculation.fullCalcOnLoad = True; wb.calculation.forceFullCalc = True; wb.calculation.calcMode = "auto"
    wb.save(target)


def grade(task_dir, candidate=None, soffice="soffice", work_dir=None, variants=True, previous=None):
    task = Path(task_dir)
    hidden = task if (task / "expected.json").is_file() else task / "tests"
    expected = json.loads((hidden / "expected.json").read_text())
    spec = json.loads((hidden / "grader_spec.json").read_text())
    rubric = json.loads((hidden / "rubric.json").read_text())
    candidate = Path(candidate or "/app/output.xlsx")
    work = Path(work_dir or tempfile.mkdtemp(prefix="dcf-v2-grade-")).resolve(); work.mkdir(parents=True, exist_ok=True)
    results = {r["id"]: {"id": r["id"], "category": r["category"], "method": r["method"], "score": 0,
        "applicable": True, "evidence": r["evidence"], "detail": "not executed"} for r in rubric["criteria"]}
    diagnostics = {"candidate": str(candidate), "work_dir": str(work), "recalculations": [], "perturbations": []}
    if not candidate.exists():
        reason = "missing candidate workbook"
        for r in results.values(): r["detail"] = reason
    else:
        try:
            recalced = recalc(candidate, work / "base", soffice)
            diagnostics["recalculations"].append(str(recalced))
            vwb = load_workbook(recalced, data_only=True, read_only=False)
            fwb = load_workbook(recalced, data_only=False, read_only=False)
            template = spec["output"]["template"]
            baseline = expected["baseline"]
            values, evidence, fixed_values = discover_values(vwb, template, baseline)
            formulas, formula_evidence, fixed_formulas = discover_formulas(fwb, template, baseline)
            diagnostics["mixed_fixed_keys"] = fixed_values["fixed"]
            diagnostics["duplicate_output_keys"] = fixed_values["duplicates"]
            diagnostics["semantic_cells"] = len(values); diagnostics["formula_cells"] = len(formulas)
            diagnostics["layout_routing"] = template
            diagnostics["formula_error_cells"] = [f"{ws.title}!{c.coordinate}:{c.value}" for ws in vwb for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("#")]
            diagnostics["external_links"] = [f"{ws.title}!{c.coordinate}" for ws in fwb for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=") and ("[" in c.value or "http:" in c.value or "https:" in c.value)]
            def numeric_keys(keys):
                if not keys: return False, {"error": "rule resolved to an empty output-key set"}
                missing = [k for k in keys if k not in values]
                bad = [{"key": k, "actual": values.get(k), "expected": baseline[k], "cell": evidence.get(k)} for k in keys if k in baseline and (k not in values or not close(values[k], baseline[k]))]
                return not missing and not bad, ({"missing": missing, "mismatch": bad[:20]} if missing or bad else {"checked": len(keys)})
            for r in rubric["criteria"]:
                if r["method"] != "rule": continue
                check = r.get("check", {"kind": r["condition"]}); kind = check["kind"]
                passed = False; detail = "unmapped rule"
                if kind == "file_exists": passed = True; detail = str(candidate)
                elif kind == "required_keys":
                    missing = [k for k in baseline if k not in values]
                    if template == "mixed":
                        fixed_expected = [k for k in baseline if "_p" not in k and not k.startswith("sens_") and "scenario_vps" not in k]
                        missing += [k + "@Outputs" for k in fixed_expected if k not in fixed_values["fixed"]]
                    passed = not missing and not fixed_values["duplicates"] and not fixed_formulas["duplicates"]
                    detail = {"missing": missing, "duplicate_output_keys": sorted(set(fixed_values["duplicates"] + fixed_formulas["duplicates"]))}
                elif kind == "numeric": passed, detail = numeric_keys(check["keys"])
                elif kind == "numeric_prefix":
                    keys = []
                    for key in baseline:
                        for prefix in check["prefixes"]:
                            if key == prefix or key.startswith(prefix + "_p") or (prefix == "sens_" and key.startswith("sens_")) or (prefix == "scenario_vps" and "scenario_vps" in key):
                                keys.append(key)
                                break
                    passed, detail = numeric_keys(keys)
                elif kind == "formula":
                    missing = [k for k in baseline if k not in formulas]; passed = not missing; detail = {"nonformula_or_missing": missing[:30]}
                elif kind == "baseline": passed, detail = numeric_keys(list(baseline))
                elif kind == "links_errors": passed = not diagnostics["formula_error_cells"] and not diagnostics["external_links"]; detail = {"errors": diagnostics["formula_error_cells"][:10], "links": diagnostics["external_links"][:10]}
                elif kind == "layout_routing": passed = bool(values); detail = {"mode": template, "discovery": "fixed Outputs column B" if template == "fixed_outputs" else "semantic key then right/below value"}
                elif kind == "immutable_history":
                    public = json.loads((hidden / "public_history_contract.json").read_text())
                    original = json.loads((hidden / "original_history.json").read_text())
                    if "History" not in fwb.sheetnames: passed = False; detail = {"error": "candidate lacks preserved History sheet"}
                    else:
                        actual = [[fwb["History"].cell(i, j).value for j in range(1, 9)] for i in range(4, 4 + len(original))]
                        wanted = [[r.get(k) for k in ("start", "end", "fiscal_year", "revenue", "ebit", "operating_cost_ex_sbc", "sbc", "nonrecurring_gain")] for r in original]
                        def normalize(x): return x.isoformat()[:10] if isinstance(x, (dt.date, dt.datetime)) else x
                        passed = [[normalize(x) for x in row] for row in actual] == [[normalize(x) for x in row] for row in wanted]
                        detail = {"candidate_history_matches_original": passed, "history_records": len(original)}
                elif kind == "old_state":
                    if spec.get("step", 1) == 1:
                        passed = "History" in fwb.sheetnames; detail = {"preserved_original_history": passed}
                    else:
                        supplied = Path(previous) if previous else Path("/app/pre_step_output.xlsx")
                        prior_path = work / "candidate_pre_step_output.xlsx"
                        if supplied.is_file():
                            shutil.copy2(supplied, prior_path)
                        if not prior_path.is_file():
                            passed = False; detail = {"error": "candidate pre_step_output.xlsx not provided"}
                        else:
                            prior = load_workbook(prior_path, data_only=False)
                            prior_formula_count = sum(c.data_type == "f" for ws in prior for row in ws.iter_rows() for c in row)
                            prior_values_path = recalc(prior_path, work / "prior_state", soffice)
                            prior_values = load_workbook(prior_values_path, data_only=True)
                            cached_outputs, _, _ = discover_values(prior_values, spec["output"]["template"], expected["prior_baseline"])
                            value_ok = bool(cached_outputs) and all(k in cached_outputs and close(cached_outputs[k], v) for k, v in expected["prior_baseline"].items())
                            passed = value_ok and prior_formula_count > 50
                            detail = {"live_prior_formulas": prior_formula_count, "prior_baseline_matches": value_ok, "source": str(prior_path), "snapshot_required": "/app/pre_step_output.xlsx"}
                elif kind == "rebase": passed, detail = numeric_keys(["driver_close_p1", "unit_price_p1", "revenue_p1"])
                elif kind == "disposal": passed, detail = numeric_keys(["segment_revenue_p1", "ebit_p1", "ppe_close_p1"])
                elif kind == "refinance": passed, detail = numeric_keys(["capex_p1", "interest_p1", "debt_close_p1"])
                elif kind == "post_event": passed, detail = numeric_keys(["fcff_p1", "terminal_value", "equity_value", "value_per_share"])
                elif kind.startswith("perturbation_"): continue
                results[r["id"]].update(score=int(passed), detail=detail)
            if variants:
                for variant_i, variant in enumerate(expected["perturbations"], 1):
                    vid = f"06-PERTURB{variant_i}"
                    try:
                        variant_source = work / f"perturbation_{variant_i}.xlsx"
                        perturb(candidate, variant_source, variant["input_changes"])
                        vr = recalc(variant_source, work / f"perturb_{variant_i}", soffice)
                        vvalues, vevidence, _ = discover_values(load_workbook(vr, data_only=True), template, variant["expected"])
                        mismatches = [{"key": k, "actual": vvalues.get(k), "expected": v} for k, v in variant["expected"].items() if k not in vvalues or not close(vvalues[k], v)]
                        passed = not mismatches
                        detail = {"input_changes": variant["input_changes"], "mismatch": mismatches[:20], "checked": len(variant["expected"])}
                    except Exception as e:
                        passed = False; detail = {"error": repr(e)}
                    results[vid].update(score=int(passed), detail=detail)
                    diagnostics["perturbations"].append({"id": vid, "passed": passed})
        except Exception as e:
            diagnostics["exception"] = traceback.format_exc()
            for r in results.values(): r["detail"] = repr(e)
    categories = {}
    category_weights = rubric.get("category_weights", {})
    for r in rubric["criteria"]:
        if r["method"] != "rule" or not r.get("applicable", True): continue
        bucket = categories.setdefault(r["category"], {"weight": category_weights.get(r["category"], r["weight"]), "passed": True, "failed_items": []})
        result = results[r["id"]]
        if not result["score"]: bucket["passed"] = False; bucket["failed_items"].append(r["id"])
    for value in categories.values(): value["score"] = value["weight"] if value["passed"] else 0
    earned = sum(v["score"] for v in categories.values())
    rule_weight = earned
    all_rule_weight = sum(v["weight"] for v in categories.values())
    judge_pending = [r["id"] for r in rubric["criteria"] if r["method"] != "rule"]
    return {"task_id": spec["task_id"], "score": earned, "max_score": all_rule_weight,
        "reward": round(rule_weight / all_rule_weight, 8) if all_rule_weight else 0,
        "rule_score": rule_weight, "rule_max_score": all_rule_weight,
        "rule_reward": round(rule_weight / all_rule_weight, 8) if all_rule_weight else 0,
        "judge_pending": judge_pending, "passed": earned == all_rule_weight and not judge_pending,
        "rule_passed": rule_weight == all_rule_weight, "categories": categories,
        "criteria": list(results.values()), "diagnostics": diagnostics}


def main():
    p = argparse.ArgumentParser(); p.add_argument("--task-dir", default=str(Path(__file__).resolve().parent.parent)); p.add_argument("--candidate"); p.add_argument("--soffice", default=os.environ.get("SOFFICE", "soffice")); p.add_argument("--report", default="/logs/verifier/report.json"); p.add_argument("--work-dir"); p.add_argument("--no-variants", action="store_true"); p.add_argument("--previous")
    a = p.parse_args()
    report = Path(a.report); report.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = grade(a.task_dir, a.candidate, a.soffice, a.work_dir, not a.no_variants, a.previous)
    except Exception as error:
        result = {"task_id": Path(a.task_dir).name, "reward": 0.0, "rule_reward": 0.0, "passed": False, "rule_passed": False, "criteria": [], "error": repr(error), "traceback": traceback.format_exc()}
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (report.parent / "reward.txt").write_text(str(result["reward"]) + "\n")
    print(json.dumps({k: result[k] for k in ("task_id", "reward", "rule_reward", "passed", "rule_passed")}, ensure_ascii=False))
    for r in result["criteria"]:
        if r["applicable"] and r["method"] == "rule" and not r["score"]: print("FAIL", r["id"], json.dumps(r["detail"], ensure_ascii=False)[:600])

if __name__ == "__main__": main()
