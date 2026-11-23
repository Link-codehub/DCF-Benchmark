#!/usr/bin/env python3
"""Frozen real-history task construction; no external answer or simulation engine is shipped."""
import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent
TASK_PLAN = {
    "E01": {"ticker":"MSFT", "cut":"2024-06-30", "variant":"annual", "shape":"xlsx", "sector":"software and cloud", "title":"Microsoft — residual-margin cloud forecast"},
    "E02": {"ticker":"DE", "cut":"2024-10-27", "variant":"annual", "shape":"json", "sector":"agricultural equipment cycle", "title":"Deere — equipment-cycle forecast"},
    "E03": {"ticker":"TGT", "cut":"2025-02-01", "variant":"h1", "shape":"xlsx", "sector":"retail merchandising", "title":"Target — reported H1 and seasonal H2"},
    "E04": {"ticker":"NFLX", "cut":"2024-12-31", "variant":"annual", "shape":"json", "sector":"paid streaming subscriptions", "title":"Netflix — subscription-economics forecast"},
    "E05": {"ticker":"CMG", "cut":"2024-12-31", "variant":"annual", "shape":"xlsx", "sector":"company-operated restaurants", "title":"Chipotle — store expansion and restaurant margins", "restricted":True},
    "E06": {"ticker":"NKE", "cut":"2025-05-31", "variant":"q3", "shape":"json", "sector":"footwear and apparel", "title":"Nike — reported nine months and remaining quarter", "restricted":True},
}
LINES = {
    "revenue":["Revenue","flow"],"cogs":["Cost of revenue","flow"],"gross_profit":["Gross profit","flow"],
    "rnd":["Research and development","flow"],"sga":["Selling, general and administrative","flow"],
    "operating_income":["Operating income","flow"],"interest_expense":["Interest expense","flow"],
    "pretax_income":["Pre-tax income","flow"],"income_tax":["Income tax expense","flow"],
    "net_income":["Net income","flow"],"diluted_shares_wavg":["Diluted weighted-average shares (millions)","shares"],
    "eps_diluted":["Diluted EPS (USD)","eps"],"cash":["Cash and cash equivalents","flow"],
    "st_investments":["Short-term investments","flow"],"receivables":["Accounts receivable, net","flow"],
    "inventory":["Inventory","flow"],"current_assets":["Total current assets","flow"],
    "ppe_net":["Property, plant and equipment, net","flow"],"goodwill":["Goodwill","flow"],
    "total_assets":["Total assets","flow"],"accounts_payable":["Accounts payable","flow"],
    "current_liabilities":["Total current liabilities","flow"],"debt_current":["Current debt","flow"],
    "debt_noncurrent":["Long-term debt","flow"],"total_liabilities":["Total liabilities","flow"],
    "equity":["Shareholders' equity","flow"],"liabilities_and_equity":["Total liabilities and equity","flow"],
    "da":["Depreciation and amortization","flow"],"sbc":["Stock-based compensation","flow"],
    "cfo":["Cash from operations","flow"],"capex":["Capital expenditure (positive cash outflow)","flow"],
    "cfi":["Cash from investing","flow"],"cff":["Cash from financing","flow"],
    "dividends_paid":["Dividends paid (positive cash outflow)","flow"],"buybacks":["Share repurchases (positive cash outflow)","flow"],
}
PROVENANCE = {}
DRIVERS = {
    "MSFT": "Consider commercial demand, cloud capacity and utilization, AI infrastructure depreciation, and the duration of committed demand. Do not treat all revenue as one homogeneous subscription pool.",
    "DE": "Consider equipment volumes, price/mix, production inventory, replacement cycles and dealer inventory. Separate cyclical revenue/margin risk from long-run reinvestment.",
    "TGT": "Consider comparable sales, traffic/ticket, seasonal inventory and the holiday-weighted remainder. Use reported H1 facts and do not annualize H1 mechanically.",
    "NFLX": "Consider paid membership, retention, pricing and content amortization. The aggregate history cannot identify each driver separately; label unobservable operational quantities as open assumptions.",
    "CMG": "Consider new restaurant openings, restaurant-level sales, food/labor inflation and new-unit cash investment. Explain the link between unit growth, margins and capital expenditure.",
    "NKE": "Consider product/channel/geographic mix, inventory clearance and gross-margin recovery. The nine-month actuals are the base; forecast only the residual quarter before subsequent full years.",
}


def write(path, text, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n")


def source_metadata(cfg, base):
    raw = base / "data" / "raw"
    fact_path = raw / f"{cfg['ticker']}_facts.json"
    data = json.loads(fact_path.read_text())
    events = []
    for taxonomy in data.get("facts", {}).values():
        for concept in taxonomy.values():
            for values in concept.get("units", {}).values():
                for row in values:
                    if row.get("form") not in ("10-K", "10-Q", "10-K/A", "10-Q/A"):
                        continue
                    if row.get("end", "0000") <= cfg["cut"] and row.get("filed", "9999") <= cfg["asof"]:
                        events.append({k:row[k] for k in ("end","filed","form","accn") if k in row})
    latest = max(events, key=lambda x:(x.get("filed",""),x.get("end","")), default=None)
    treasury = raw / "DGS10.csv"
    pack = json.loads((base / "data" / "packs" / (cfg["ticker"] + ".json")).read_text())
    cik = int(pack["cik"])
    url = "https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json" % cik
    return [
        {"source_id":"SEC_XBRL", "publisher":"US Securities and Exchange Commission", "document":"companyfacts XBRL; historical facts extracted using the disclosed tag-priority map", "url":url, "accession": latest.get("accn") if latest else "NOT_VERIFIED", "filing_form": latest.get("form") if latest else "NOT_VERIFIED", "period_end": latest.get("end") if latest else cfg["cut"], "filed": latest.get("filed") if latest else "NOT_VERIFIED", "retrieval_status":"local snapshot; hash verified, not retrieved by this generator", "source_sha256":sha(fact_path)},
        {"source_id":"UST_DGS10", "publisher":"US Treasury / Federal Reserve DGS10 mirror in supplied snapshot", "document":"Daily 10-year Treasury constant maturity yield; last observation on or before cutoff", "url":"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve", "filed":"daily observation", "retrieval_status":"local DGS10 CSV; hash verified; original retrieval timestamp not recorded", "source_sha256":sha(treasury)},
        {"source_id":"HISTORICAL_PRICE", "publisher":"Nasdaq supplied snapshot", "document":"Unadjusted daily close used only for market diagnostics", "url":f"https://api.nasdaq.com/api/quote/{cfg['ticker']}/historical?assetclass=stocks", "filed":"daily observations", "retrieval_status":"local snapshot; hash verified; not a permitted E05/E06 retrieval source", "source_sha256":sha(raw / f"{cfg['ticker']}_px.json")},
    ]


def yield_on(base, date):
    values=[]
    for line in (base/"data"/"raw"/"DGS10.csv").read_text().splitlines()[1:]:
        fields=line.split(",")
        if len(fields)>=2 and fields[0]<=date and fields[1] not in ("", "."):
            values.append((fields[0],float(fields[1])/100))
    if not values:
        raise ValueError(f"no Treasury yield on or before {date}")
    return values[-1]


def periods(cfg, pack):
    years=[x for x in pack["fiscal_year_ends"] if x<=cfg["cut"]][-5:]
    if len(years)<5:
        raise ValueError("insufficient historical annual periods")
    stub=[]
    if cfg["variant"] in ("h1","q3"):
        start=dt.date.fromisoformat(cfg["cut"])+dt.timedelta(days=1)
        available=sorted((k for k in pack["quarterly"]["revenue"] if dt.date.fromisoformat(k.split("..")[0])>=start-dt.timedelta(days=7)), key=lambda k:k.split("..")[1])
        for key in available:
            a,b=map(dt.date.fromisoformat,key.split(".."))
            if a>=start-dt.timedelta(days=7) and (not stub or a<=dt.date.fromisoformat(stub[-1].split("..")[1])+dt.timedelta(days=7)):
                stub.append(key)
            if len(stub)==(2 if cfg["variant"]=="h1" else 3):
                break
        need=2 if cfg["variant"]=="h1" else 3
        if len(stub)<need:
            raise ValueError(f"missing {cfg['variant']} discrete quarters")
    return years,stub


def prepare():
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    for task_id,cfg in TASK_PLAN.items():
        cfg["task_id"]=task_id
        cfg["years"]=5
        cfg["mc_seed"]=1729+int(task_id[1:])*101
        cfg["min_paths"]=5000
        if cfg["variant"]=="h1":
            pack=json.loads((ROOT_SOURCE/"data"/"packs"/f"{cfg['ticker']}.json").read_text())
            start=dt.date.fromisoformat(cfg["cut"])+dt.timedelta(days=1)
            keys=sorted(k for k in pack["quarterly"]["revenue"] if dt.date.fromisoformat(k.split("..")[0])>=start-dt.timedelta(days=7))
            cfg["asof"]=(dt.date.fromisoformat(keys[1].split("..")[1])+dt.timedelta(days=45)).isoformat()
        elif cfg["variant"]=="q3":
            pack=json.loads((ROOT_SOURCE/"data"/"packs"/f"{cfg['ticker']}.json").read_text())
            start=dt.date.fromisoformat(cfg["cut"])+dt.timedelta(days=1)
            keys=sorted(k for k in pack["quarterly"]["revenue"] if dt.date.fromisoformat(k.split("..")[0])>=start-dt.timedelta(days=7))
            cfg["asof"]=(dt.date.fromisoformat(keys[2].split("..")[1])+dt.timedelta(days=45)).isoformat()
        else:
            pack=json.loads((ROOT_SOURCE/"data"/"packs"/f"{cfg['ticker']}.json").read_text())
            cfg["asof"]=(dt.date.fromisoformat(cfg["cut"])+dt.timedelta(days=60)).isoformat()
    return now


def history(cfg, pack, years, stub):
    values={}
    for key in LINES:
        values[key]={y:pack["annual"].get(key,{}).get(y) for y in years}
    observed=[]
    for period in stub:
        end=period.split("..")[1]
        item={"period":period,"end":end}
        for key,(label,kind) in LINES.items():
            if key in pack["annual"] and kind!="flow" or key in ("cash","st_investments","receivables","inventory","current_assets","ppe_net","goodwill","total_assets","accounts_payable","current_liabilities","debt_current","debt_noncurrent","total_liabilities","equity","liabilities_and_equity"):
                item[key]=pack["quarterly"].get(key,{}).get(end)
            else:
                item[key]=pack["quarterly"].get(key,{}).get(period)
        observed.append(item)
    return values,observed


def public_inputs(cfg, pack, base):
    years,stub=periods(cfg,pack)
    values,observed=history(cfg,pack,years,stub)
    yd,yr=yield_on(base,cfg["asof"])
    def convert(v,kind):
        if v is None:return None
        return v if kind=="eps" else round(v/1e6,6)
    statements={k:{y:convert(v,LINES[k][1]) for y,v in rows.items()} for k,rows in values.items()}
    statements["operating_income_raw_sec"] = dict(statements["operating_income"])
    statements["operating_income_basis"] = "reported_operating_income"
    if all(v is None for v in statements["operating_income"].values()):
        for y in years:
            gp=statements["gross_profit"][y];sga=statements["sga"][y]
            statements["operating_income"][y]=gp-sga if gp is not None and sga is not None else None
        statements["operating_income_basis"] = "gross_profit_minus_sga_proxy; not a directly reported SEC OperatingIncomeLoss fact"
    actual=[]
    for row in observed:
        item={"period":row["period"],"end":row["end"],"operating_income_raw_sec":convert(row.get('operating_income'),'flow')}
        for k,(label,kind) in LINES.items():
            item[k]=convert(row.get(k),kind)
        if item['operating_income'] is None and item['gross_profit'] is not None and item['sga'] is not None:
            item['operating_income']=item['gross_profit']-item['sga']
            item['operating_income_basis']='gross_profit_minus_sga_proxy; not directly reported'
        actual.append(item)
    timing=None
    if actual:
        from datetime import date
        next_end=(dt.date.fromisoformat(actual[-1]['end'])+dt.timedelta(days=91 if cfg['variant']=='q3' else 182)).isoformat()
        residual_start=(dt.date.fromisoformat(actual[-1]['end'])+dt.timedelta(days=1)).isoformat()
        days=(dt.date.fromisoformat(next_end)-dt.date.fromisoformat(cfg['asof'])).days
        timing={'residual_start':residual_start,'next_fiscal_year_end':next_end,'remaining_days':days,'remaining_years':days/365,'discount_years':[days/365+i for i in range(5)],'remaining_fractions':[1]*5}
    return {
        "schema_version":"dcf-open-frozen-v1", "task_id":cfg["task_id"], "title":cfg["title"],
        "company":{"ticker":cfg["ticker"],"cik":pack["cik"],"name":pack["name"],"sector":cfg["sector"]},
        "information_cutoff":cfg["asof"], "valuation_date":cfg["asof"], "units":"USD millions, shares millions, EPS USD; rates decimals",
        "fiscal_years":years, "last_full_fiscal_year":cfg["cut"], "historical":statements,
        "reported_partial_period":{"type":cfg["variant"],"quarters":actual,"remaining":("H2" if cfg["variant"]=="h1" else "Q4" if cfg["variant"]=="q3" else None),"timing":timing},
        "market_observation":{"treasury_10y":yr,"treasury_date":yd,"source_id":"UST_DGS10"},
        "sources":source_metadata(cfg,base),
        "data_scope":{"tag_priority":"exp/data/fetch_sec.py disclosed deterministic SEC XBRL tag-priority map; later filed values in local snapshot may revise same periods", "blanks":"null means not separately available; it is not evidence of zero", "partial_period":"discrete reported quarters, not year-to-date; use only those listed", "price":"not supplied as an assumption truth; no price target or consensus is supplied"},
        "restricted_retrieval":{"enabled":bool(cfg.get("restricted")),"allowed_domains":["data.sec.gov","www.sec.gov","home.treasury.gov","ir.chipotle.com"] if cfg["ticker"]=="CMG" else ["data.sec.gov","www.sec.gov","home.treasury.gov","investors.nike.com"] if cfg["ticker"]=="NKE" else [], "prohibited":["general web search","current market data","consensus or price targets","post-cutoff filings"], "fallback":"inputs.json and frozen_history.xlsx are the canonical complete task version; if any retrieval fails, use them unchanged", "enforcement":"E01-E04 are physically offline. E05-E06 declare retrieval policy only; default local Harbor does not enforce domain allowlists. No external access is required."},
        "business_driver_prompt":DRIVERS[cfg["ticker"]],
    }


def workbook(inputs,path):
    wb=Workbook()
    ws=wb.active;ws.title="Historical"
    ws.append(["Frozen historical statements; USD millions except EPS; shares in millions"])
    ws.append(["line","item"]+inputs["fiscal_years"])
    for key,(label,kind) in LINES.items():
        ws.append([key,label]+[inputs["historical"][key][y] for y in inputs["fiscal_years"]])
    if inputs["reported_partial_period"]["quarters"]:
        q=wb.create_sheet("Reported_Periods")
        quarters=inputs["reported_partial_period"]["quarters"]
        q.append(["Discrete reported quarters; balance-sheet items only at each listed date"])
        q.append(["line","item"]+[x["period"] for x in quarters])
        for key,(label,kind) in LINES.items():
            q.append([key,label]+[x.get(key) for x in quarters])
    m=wb.create_sheet("Market")
    m.append(["item","value","source_id"])
    for key in ("valuation_date","treasury_date","treasury_10y"):
        m.append([key,inputs["market_observation"].get(key,inputs.get(key)),"UST_DGS10"])
    m.append(["information_cutoff",inputs["information_cutoff"],"SEC_XBRL"])
    o=wb.create_sheet("Outputs")
    o.append(["key","definition","value"])
    for key,definition in output_contract(inputs["reported_partial_period"]["type"]):
        o.append([key,definition,None])
    s=wb.create_sheet("Sources")
    s.append(["source_id","publisher","document","period_end","filed","accession","url","source_sha256","retrieval_status"])
    for row in inputs["sources"]:
        s.append([row.get(k) for k in ("source_id","publisher","document","period_end","filed","accession","url","source_sha256","retrieval_status")])
    for sheet in wb:
        sheet.freeze_panes="C3" if sheet.title in ("Historical","Reported_Periods") else "A2"
        sheet.column_dimensions["A"].width=30;sheet.column_dimensions["B"].width=50
        for cell in sheet[1]:cell.font=Font(bold=True)
    wb.save(path)


def output_contract(variant):
    keys=[("hist_revenue_fy0","last full-year revenue"),("hist_ebit_fy0","last full-year EBIT"),("hist_eps_fy0","last full-year diluted EPS")]
    if variant!="annual":
        keys += [("actual_partial_revenue_y1","sum of reported discrete partial-year revenue"),("actual_partial_ebit_y1","sum of reported discrete partial-year EBIT"),("residual_revenue_y1","forecast revenue only after the reported periods"),("residual_fcff_y1","forecast FCFF only after the reported periods"),("residual_discount_years","actual fraction of year to the residual-period cash-flow timing point")]
    for y in range(1,6):
        keys += [(f"revenue_y{y}","full fiscal-year revenue; actual plus residual for FY1 when applicable"),(f"ebit_y{y}","full fiscal-year EBIT"),(f"eps_y{y}","full fiscal-year diluted EPS"),(f"fcff_y{y}","full fiscal-year FCFF"),(f"discount_factor_y{y}","factor for remaining cash flow only")]
    keys += [("wacc","weighted average cost of capital"),("terminal_growth","Gordon growth rate"),("enterprise_value","USD millions"),("equity_value","USD millions"),("diluted_shares","millions"),("value_per_share","USD"),("mc_n","number of valid, independently simulated paths"),("mc_p10","10th percentile of simulated value per share"),("mc_p25","25th percentile"),("mc_p50","50th percentile"),("mc_p75","75th percentile"),("mc_p90","90th percentile"),("mc_mean","mean of simulated value per share")]
    return keys


def instruction(cfg,inputs):
    stub=cfg["variant"]!="annual"
    shape="""Produce `/app/output/model.xlsx` with a `Forecast` sheet (rows named `revenue_y1` ... `revenue_y5`, `ebit_y1` ... `ebit_y5`, `fcff_y1` ... `fcff_y5`, with years in columns C:G), an `Assumptions` sheet, a `DCF` sheet, and the supplied `Outputs` sheet. Fill Outputs column C with live formulas linked to the model; Monte Carlo outputs must be Excel formulas over a `MC_Trials` sheet. Do not put simulation formulas or precomputed answers in the public inputs.""" if cfg["shape"]=="xlsx" else """Produce `/app/output/model.json` with numeric `historical`, `forecast`, `valuation`, and `simulation_summary` objects. Each forecast object maps `revenue_y1`...`revenue_y5`, `ebit_y1`...`ebit_y5`, `eps_y1`...`eps_y5`, `fcff_y1`...`fcff_y5` and `discount_factor_y1`...`discount_factor_y5` to numbers. Include numeric `wacc`, `terminal_growth`, `tax_rate`, `net_debt`, `cash_and_investments`, `diluted_shares`, `discount_years` (list), `remaining_fractions` (list), and `terminal_year_fcff` directly in `valuation`. Also submit `/app/output/recompute.py` implementing the deterministic forecast and valuation calculations; it must accept `--input INPUT --model MODEL --output DIR` and write `recomputed.json`. The grader runs it independently; never use it as a Monte Carlo shortcut."""
    return f"""# {cfg['title']}

You are an equity analyst at the frozen information cutoff **{cfg['asof']}**. Do not use facts filed or observed after that date. The task is an open forecast, not a search for consensus or a target DCF answer.

## Evidence and forecast
Use the complete frozen history in `/app/data/inputs.json` and the identical `/app/data/frozen_history.xlsx`. Every cited historical number must carry a `source_id` matching the supplied sources. {DRIVERS[cfg['ticker']]}
Build five fiscal years of driver-based revenue, EBIT, EPS and FCFF forecasts. Reconcile operating growth, operating margin, taxes, depreciation, capital expenditure and the change in operating working capital. State the net-debt and diluted-share bridge. You may choose a defensible WACC and terminal growth; they are not unique truths.
{('The listed discrete quarters are already actual. Forecast only the remaining '+inputs['reported_partial_period']['remaining']+' of FY1, add actual and residual amounts for full-year FY1, and include only residual FY1 FCFF in enterprise value. Use an actual-day fractional discount period; do not discount or count already-reported cash flow again.') if stub else 'Use annual cash flows from the valuation date; explicitly state and implement full-year or mid-year discount timing consistently.'}

## Monte Carlo — implement it yourself
Create `/app/output/simulate.py` and run it with `--input /app/data/inputs.json --model /app/output/{('model.xlsx' if cfg['shape']=='xlsx' else 'model.json')} --output /app/output/simulation.json`. It must generate at least **5,000 valid paths**, seed **{cfg['mc_seed']}**, and sample revenue growth, EBIT margin, reinvestment intensity, and discount rate. Use declared distributions and finite legal bounds. Correlate growth and margin or document a reasoned independence choice; show the realized cross-driver correlation matrix. Every path must produce a traceable DCF value using your model and reinvestment internally consistent with its EBIT. Keep all valid draws; report rejected/invalid draws separately. Do not sample a share price or directly sample the final value per share.

The JSON simulation schema is: `seed`, `n_valid`, `n_rejected`, `method` (your own description), `drivers` (name -> distribution, numeric parameters and units), `dependence` (matrix and ordered names, or independence explanation), `trials` (a list of at least 5,000 objects containing `path_id`, the exact keys `revenue_growth`, `ebit_margin`, `reinvestment_intensity`, `discount_rate`, `value_per_share`, and `trajectory`), `statistics` (`p10`,`p25`,`p50`,`p75`,`p90`,`mean`), and `limitations`. Each `trajectory` is a five-element list with `year`, `revenue`, `ebit`, `reinvestment`, `fcff`, `discount_factor`. Define FCFF = EBIT*(1-tax)-reinvestment and discount_factor = remaining_fraction/(1+discount_rate)^discount_years for each year. The final year's FCFF enters your Gordon terminal value. For a residual-period FY1, trajectory FCFF must be residual-only; full-year FY1 forecast revenue/EBIT remain actual plus residual. Declare `percentile_convention` (`linear interpolation at (N-1)q` or `nearest_r`). Use a reproducible PRNG; different statistically valid methods and those percentile conventions are accepted. Random draws themselves are allowed constants. The grader independently recomputes your model, annual path arithmetic, distributions, correlations and quantiles rather than replaying a supplied engine.

## Deliverables
{shape}
- `/app/output/simulate.py` and `/app/output/simulation.json`.
- `/app/output/memo.md`: no more than 700 words. For each material forecast driver, give a named historical row/period/value, a derivation, a business mechanism, and the reinvestment implication. State sampling bounds and correlation rationale. Do not substitute prose length or a source identifier for this evidence.

## Data access
{('Only the following direct HTTPS domains are permitted: '+', '.join(inputs['restricted_retrieval']['allowed_domains'])+'. Free web search and current quotes are prohibited. This default Harbor configuration does not enforce that domain list: the restriction is a task rule, not a claim of technical enforcement. Retrieval is optional. If it fails or conflicts, use the complete frozen package unchanged; do not change its cutoff or mix a new snapshot.') if cfg.get('restricted') else 'This task is offline. Do not use the network or later company knowledge.'}
Historical data were extracted from the supplied local SEC XBRL snapshots, not fetched by this task generator. Snapshot hashes and extraction limits are provided. Missing values are not automatically zero. Later realized outcomes are deliberately withheld and, if ever released, would be diagnostics rather than an assumption target. Any forecaster may have training-memory leakage; this is an unavoidable limitation of the backtest.
"""


def truth(cfg,pack,inputs):
    later=[y for y in pack["fiscal_year_ends"] if y>cfg["cut"]][:3]
    actual={}
    for y in later:
        actual[y]={k:pack["annual"].get(k,{}).get(y) if k=="eps_diluted" or pack["annual"].get(k,{}).get(y) is None else pack["annual"][k][y]/1e6 for k in ("revenue","operating_income","eps_diluted")}
    prices=pack.get("daily_close",{})
    cutoff=cfg["asof"]
    future={d:v for d,v in prices.items() if d>cutoff}
    return {"task_id":cfg["task_id"],"cutoff":cutoff,"future_actuals":actual,"future_prices":future,
            "historical":inputs["historical"],"output_keys":[k for k,_ in output_contract(cfg["variant"])],
            "limitations":["Future actuals and prices are independent diagnostics, never used in mechanism or open-judgment score.","Model training-memory leakage cannot be excluded.","Unadjusted price history is a market diagnostic only; no median-to-price assumption truth.","Original remote retrieval timestamps are not preserved; only local snapshot hashes were verified.","The SEC standardized tags do not expose full segment/unit drivers."]}


def build_task(task_id,generator_seed,base):
    base=Path(base).resolve()
    global ROOT_SOURCE
    ROOT_SOURCE=base
    prepare_once(task_id,base)
    cfg=TASK_PLAN[task_id]
    pack=json.loads((base/"data"/"packs"/f"{cfg['ticker']}.json").read_text())
    inputs=public_inputs(cfg,pack,base)
    task=ROOT.parent/"tasks"/task_id
    shutil.rmtree(task,ignore_errors=True)
    for directory in ("environment/data","tests","solution"):(task/directory).mkdir(parents=True,exist_ok=True)
    dump(task/"environment"/"data"/"inputs.json",inputs)
    workbook(inputs,task/"environment"/"data"/"frozen_history.xlsx")
    write(task/"environment"/"Dockerfile","FROM dcfbench-agent:v1\nWORKDIR /app\nCOPY data /app/data\nRUN mkdir -p /app/output\n")
    write(task/"environment"/"docker-compose.yaml","services:\n  main:\n    network_mode: none\n")
    write(task/"instruction.md",instruction(cfg,inputs))
    write(task/"task.toml",f'''schema_version = "1.4"
artifacts = ["/app/output"]
[metadata]
category = "dcf-open-forecast-simulation"
difficulty = "very-hard"
network = "{'offline-fallback-restricted-retrieval-policy' if cfg.get('restricted') else 'offline'}"
tags = ["E", "{cfg['ticker']}", "{cfg['variant']}", "{cfg['shape']}"]
disable_web_search = true
[agent]
timeout_sec = 5400.0
network_mode = "no-network"
[verifier]
timeout_sec = 1800.0
environment_mode = "separate"
[verifier.environment]
network_mode = "no-network"
[environment]
network_mode = "no-network"
build_timeout_sec = 900.0
cpus = 2
memory_mb = 4096
storage_mb = 4096
''')
    dump(task/"tests"/"truth.json",truth(cfg,pack,inputs))
    spec={k:v for k,v in cfg.items() if k not in ("title",)}
    spec["dimension_selection"]={"scenario":cfg["sector"],"time_axis":cfg["variant"],"data_provision":"restricted retrieval declaration plus canonical frozen fallback" if cfg.get("restricted") else "complete frozen snapshot","business_drivers":DRIVERS[cfg["ticker"]],"output_mode":cfg["shape"],"simulation":"candidate-owned independent Monte Carlo with at least 5000 paths"}
    spec["source_snapshot_sha256"]=sha(base/"data"/"packs"/f"{cfg['ticker']}.json")
    dump(ROOT/"specs"/f"{task_id}.json",spec)
    (ROOT/"rubrics").mkdir(exist_ok=True)
    from rubric_factory import build_rubric
    dump(ROOT/"rubrics"/f"{task_id}.json",build_rubric(cfg))
    write(task/"tests"/"grader.py",(ROOT/"grader.py").read_text())
    import shutil as _shutil
    _shutil.copy2(ROOT/"rubrics"/f"{task_id}.json", task/"tests"/"rubric.json")
    _shutil.copy2(task/"environment"/"data"/"inputs.json", task/"tests"/"inputs.json")
    write(task/"tests"/"test.sh","#!/bin/bash\nset -u\nmkdir -p /logs/verifier\ncd /tests\npython3 grader.py --input /tests/inputs.json --artifact-dir /app/output --output-dir /logs/verifier > /logs/verifier/grader.log 2>&1\n",True)
    write(task/"tests"/"Dockerfile","FROM dcfbench-base:v1\nCOPY . /tests/\nRUN chmod +x /tests/test.sh\n")
    write(task/"solution"/"solve.sh",f'''#!/bin/bash
set -euo pipefail
mkdir -p /app/output
python3 /solution/reference.py --input /app/data/inputs.json --output /app/output
python3 /app/output/simulate.py --input /app/data/inputs.json --model /app/output/{'model.xlsx' if cfg['shape']=='xlsx' else 'model.json'} --output /app/output/simulation.json
''',True)
    from reference import reference_source
    write(task/"solution"/"reference.py",reference_source())
    return {"task_id":task_id,"ticker":cfg["ticker"],"cutoff":cfg["asof"],"shape":cfg["shape"],"variant":cfg["variant"],"path":f"../tasks/{task_id}","inputs_sha256":sha(task/"environment"/"data"/"inputs.json")}


def prepare_once(task_id,base):
    global ROOT_SOURCE
    ROOT_SOURCE=base
    if "asof" in TASK_PLAN[task_id]:return
    for cid,cfg in TASK_PLAN.items():
        cfg["task_id"] = cid
        cfg["years"] = 5
        cfg["mc_seed"] = 1729 + int(cid[1:]) * 101
        cfg["min_paths"] = 5000
        pack=json.loads((base/"data"/"packs"/f"{cfg['ticker']}.json").read_text())
        if cfg["variant"]!="annual":
            start=dt.date.fromisoformat(cfg["cut"])+dt.timedelta(days=1)
            keys=sorted((k for k in pack["quarterly"]["revenue"] if dt.date.fromisoformat(k.split("..")[0])>=start-dt.timedelta(days=7)),key=lambda k:k.split("..")[1])
            if cid=="E03":keys=[k for k in keys if k.split("..")[1]<=cfg.get("partial_cut","2025-08-02")]
            need=2 if cfg["variant"]=="h1" else 3
            if len(keys)<need:raise ValueError(f"insufficient quarters for {cid}")
            cfg["asof"]=(dt.date.fromisoformat(keys[need-1].split("..")[1])+dt.timedelta(days=45)).isoformat()
        else:
            cfg["asof"]=(dt.date.fromisoformat(cfg["cut"])+dt.timedelta(days=60)).isoformat()
