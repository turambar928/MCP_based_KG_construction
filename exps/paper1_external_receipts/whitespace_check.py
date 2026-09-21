"""Post-run whitespace consistency check on the SAME frozen responses; no API."""
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import gate,read_jsonl
from exps.paper1_external_receipts.run import input_object
from exps.paper1_external_receipts.analyze import score_case
HERE=Path(__file__).resolve().parent


def whitespace_gate(inp,candidates):
    # The fixed JSON parser already collapses whitespace in candidate values.
    # Apply the same operation to the source before the unchanged gate.
    source=' '.join(inp.source_evidence.split())
    return gate(replace(inp,source_evidence=source),candidates)


def main():
    inp={x['case_id']:x for x in read_jsonl(HERE/'inputs.jsonl')}
    ref={x['case_id']:x for x in read_jsonl(HERE/'references.jsonl')}
    initial={x['case_id']:x for x in read_jsonl(HERE/'extraction.jsonl')}
    predictions=read_jsonl(HERE/'repairs.jsonl');assert len(predictions)==180
    rows=[]
    for arm in ['base','diagnosis','shacl_context']:
        metrics=[];changes=[]
        for row in predictions:
            if row['arm']!=arm:continue
            cid=row['case_id'];public=input_object(inp[cid],initial[cid]['triples'])
            before,_=gate(public,row['triples']);after,rejected=whitespace_gate(public,row['triples'])
            if before!=after:changes.append(cid)
            metrics.append(score_case(initial[cid]['triples'],after,ref[cid]))
        rows.append({'arm':arm,'n':len(metrics),'changed_cases':changes,
                     'triple_f1':float(np.mean([m['triple_f1'] for m in metrics])),
                     'exact_match':float(np.mean([m['exact_match'] for m in metrics]))})
    result={'status':'post-run sensitivity check, not the locked primary comparison',
            'change':'collapse source whitespace just as the existing JSON parser does for candidate values',
            'new_model_calls':0,'results':rows}
    (HERE/'whitespace_sensitivity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
