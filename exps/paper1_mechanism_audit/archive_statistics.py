#!/usr/bin/env python3
"""Document-paired (not defect-independent) inference for archived results."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import *
from exps.paper1_mechanism_audit.analyze import metrics,paired

def main():
    cases={c['case_id']:c for c in read_jsonl(BENCH/'benchmark.jsonl') if c['split']=='test'}
    rows=[]
    for name,path in [('diagnosis_gate',BENCH/'predictions_ours.jsonl'),('simple',EXT/'predictions_simple_pipeline_claude.jsonl'),('direct',BENCH/'predictions_direct_llm.jsonl')]:
        for pred in read_jsonl(path):
            c=cases[pred['case_id']]
            rows.append({'case_id':c['case_id'],'method':name,**metrics(c,c['corrupted_triples'],pred['triples'],'controlled')})
    result={'unit':'source document (two controlled defects remain grouped)','bootstrap_repeats':10000,'seed':42,
            'comparisons':[paired(rows,'diagnosis_gate',baseline) for baseline in ['simple','direct']]}
    (HERE/'archived_document_statistics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
