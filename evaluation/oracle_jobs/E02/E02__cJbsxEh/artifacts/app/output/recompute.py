#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--model',required=True);p.add_argument('--output',required=True);a=p.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parent));from e_model import compute
model=json.load(open(a.model));forecast,valuation=compute(json.load(open(a.input)),model['assumptions']);result={'historical':{k:v for k,v in forecast.items() if k.startswith(('hist_','actual_partial_'))},'assumptions':model['assumptions'],'forecast':forecast,'valuation':{**model['assumptions'],**valuation}}
Path(a.output).mkdir(parents=True,exist_ok=True);json.dump(result,open(Path(a.output)/'recomputed.json','w'),indent=2)
