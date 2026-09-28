"""Strict response ingestion and offline scoring; never makes model requests."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_reextraction_control.protocol import MODEL
from exps.paper1_external_receipts.analyze import score_case
from exps.paper1_receipt_followup.protocol import filter_response
from exps.paper1_mechanism_audit.analyze import paired
HERE=Path(__file__).resolve().parent


def validate_outcome(row,expected):
    if row.get('kind')!='model_response' or row.get('is_mock') is not False:
        raise ValueError('Formal scoring refuses mock/synthetic or unclassified records')
    if row.get('model')!=MODEL:raise ValueError('Unexpected model')
    key=(row['case_id'],row['arm'])
    if key not in expected or row.get('prompt_sha256')!=expected[key]['prompt_sha256']:
        raise ValueError('Case/arm/prompt mismatch')
    if row.get('status') not in ('ok','transport_error','parse_error'):
        raise ValueError('Unknown outcome status')
    if not isinstance(row.get('attempts'),list) or not 1<=len(row['attempts'])<=4:
        raise ValueError('Preserve one to four transport attempt records')
    if not isinstance(row.get('wall_seconds'),(float,int)) or row['wall_seconds']<0:
        raise ValueError('Missing measured time')
    if not isinstance(row.get('usage'),dict):raise ValueError('Missing usage object; use null for unreported token counts')
    if not isinstance(row.get('raw_response'),str):raise ValueError('Preserve raw response text, empty for transport failures')
    if row['status']=='ok':
        try:
            body=json.loads(row['raw_response']);triples=body['triples']
            assert isinstance(triples,list)
            assert all(isinstance(t,dict) and all(isinstance(t.get(k),str) for k in ('head','relation','tail')) for t in triples)
        except (ValueError,TypeError,KeyError,AssertionError) as e:raise ValueError('Invalid successful JSON response') from e
        if row.get('triples')!=triples:raise ValueError('Parsed triples disagree with raw response')
    else:
        if row.get('triples')!=[]:raise ValueError('Failed outcomes must carry an empty graph')
    return key


def validate(rows,tasks):
    expected={(t['case_id'],t['arm']):t for t in tasks};seen=set()
    if len(rows)!=len(expected):raise ValueError('Wait for all 240 outcomes, including failures')
    for row in rows:
        key=validate_outcome(row,expected)
        if key in seen:raise ValueError('Duplicate outcome')
        seen.add(key)
    if seen!=set(expected):raise ValueError('Incomplete outcomes')


def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['validate','score']);p.add_argument('--responses',type=Path,required=True);args=p.parse_args()
    from exps.paper1_reextraction_control.prepare import prepare,read,SOURCE
    prepare();tasks=read(HERE/'requests.jsonl');rows=read(args.responses);validate(rows,tasks)
    if args.operation=='validate':print('All 240 formal outcomes validated.');return
    inputs={r['case_id']:r for r in read(SOURCE/'inputs.jsonl')}
    initial={r['case_id']:r['triples'] for r in read(SOURCE/'extraction.jsonl')}
    refs={r['case_id']:r for r in read(SOURCE/'references.jsonl')}
    records=[]
    for row in rows:
        cid=row['case_id'];raw=row['triples'];filtered,_=filter_response(inputs[cid],raw)
        for kind,triples in [('raw',raw),('gate',filtered)]:
            records.append({'case_id':cid,'method':row['arm']+'_'+kind,**score_case(initial[cid],triples,refs[cid])})
    import numpy as np
    summaries=[]
    for method in sorted({r['method'] for r in records}):
        rs=[r for r in records if r['method']==method]
        summaries.append({'method':method,'n':len(rs),**{k:float(np.mean([r[k] for r in rs])) for k in
            ('triple_f1','normalized_f1','exact_match','clean_fact_preservation','overrepair_rate')}})
    result={'kind':'formal_model_result','complete':True,'n_documents':60,'summary':summaries,
            'primary':{'left':'repair_index_gate','right':'extract_index_gate','n':60,
                       'triple_f1':paired(records,'repair_index_gate','extract_index_gate')['triple_f1']},'per_case':records,
            'status_counts':{status:sum(r['status']==status for r in rows) for status in ('ok','parse_error','transport_error')},
            'cost_records':[{k:r[k] for k in ('case_id','arm','usage','attempts','wall_seconds')} for r in rows]}
    out=HERE/'results.json'
    with out.open('x') as f:f.write(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print('Formal results saved; source responses must remain archived.')

if __name__=='__main__':main()
