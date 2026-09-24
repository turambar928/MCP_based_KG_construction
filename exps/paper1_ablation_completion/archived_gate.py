"""Complete individual-filter ablations on archived Gemma responses, no API."""
import json,sys,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_ablation_completion.protocol import CHECKS,filter_candidates,key
from exps.paper1_ablation_completion.analyze import load_data,inp_object,score,summarize,write_csv,paired_stats,holm
from exps.paper1_mechanism_audit.protocol import read_jsonl,gate
from exps.paper1_receipt_followup.protocol import filter_response
HERE=Path(__file__).resolve().parent
VARIANTS={'full':(),**{'no_'+c:(c,) for c in CHECKS},'no_duplicate_cardinality':('duplicate','cardinality'),'raw':CHECKS}
def main():
    from exps.paper1_ablation_completion.run import verify
    verify()
    paths=['exps/paper1_mechanism_audit/run/predictions.jsonl','exps/paper1_receipt_followup/test/repairs.jsonl','exps/paper1_receipt_followup/test/inputs.jsonl','exps/paper1_ablation_completion/archived_gate.py']
    manifest={'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'design':'Same-response eight filter configurations; 360 archived matched Gemma and 180 archived receipt Gemma responses, cohorts separate. F1 marginal effects average generation arms within documents. Holm across 21 exploratory contrasts (7 removals times 3 cohorts). No API calls.'}
    lock=HERE/'archived_gate_manifest.json'
    if lock.exists():assert json.loads(lock.read_text())==manifest
    else:lock.write_text(json.dumps(manifest,indent=2)+'\n')
    inputs,cases,refs=load_data();preds=[]
    for r in read_jsonl(ROOT/paths[0]):preds.append({**r,'cohort':r['stream']})
    for r in read_jsonl(ROOT/paths[1]):preds.append({**r,'cohort':'receipt'})
    assert len(preds)==540
    receipt_inputs={r['case_id']:r for r in read_jsonl(ROOT/paths[2])}
    per=[];rejs=[];changed=[]
    for row in preds:
        assert row['model']=='google/gemma-4-26B-A4B-it'
        r=inputs[row['cohort'],row['case_id']];inp=inp_object(r)
        reference=refs[r['case_id']]['triples'] if r['cohort']=='receipt' else cases[r['case_id']]['clean_triples'];gold=Counter(map(key,reference))
        full,rej=filter_candidates(inp,row['triples'],whitespace=r['cohort']=='receipt')
        original=filter_response(receipt_inputs[r['case_id']],row['triples'])[0] if r['cohort']=='receipt' else gate(inp,row['triples'])[0]
        assert full==original,'Mismatch with published filtering'
        for variant,disabled in VARIANTS.items():
            out,rejected=filter_candidates(inp,row['triples'],disabled,r['cohort']=='receipt');m=score(r,out,cases,refs)
            per.append({'cohort':r['cohort'],'case_id':r['case_id'],'arm':row['arm'],'gate_variant':variant,**m})
            a,b=Counter(map(key,full)),Counter(map(key,out));new=b-a;lost=a-b
            changed.append({'cohort':r['cohort'],'case_id':r['case_id'],'arm':row['arm'],'gate_variant':variant,
              'added_occurrences':sum(new.values()),'removed_occurrences':sum(lost.values()),
              'added_correct_occurrences':sum(((b&gold)-(a&gold)).values()),'removed_correct_occurrences':sum(((a&gold)-(b&gold)).values())})
        for x in rej:rejs.append({'cohort':r['cohort'],'case_id':r['case_id'],'arm':row['arm'],'reason':x['reason'],'reference_member':key(x['triple']) in gold,'triple':json.dumps(x['triple'],ensure_ascii=False)})
    summary=summarize(per,['cohort','arm','gate_variant']);idx={(r['cohort'],r['case_id'],r['arm'],r['gate_variant']):r['triple_f1'] for r in per};effects=[]
    for cohort in ['controlled','natural','receipt']:
        ids=sorted({cid for c,cid,a,v in idx if c==cohort});arms=sorted({a for c,cid,a,v in idx if c==cohort})
        for v in list(VARIANTS)[1:]:
            effects.append({'cohort':cohort,'removed':v,'responses':len(ids)*len(arms),**paired_stats([np.mean([idx[cohort,cid,a,'full']-idx[cohort,cid,a,v] for a in arms]) for cid in ids])})
    holm(effects)
    activations=[{'cohort':c,'reason':reason,'rejections':sum(r['cohort']==c and r['reason']==reason for r in rejs),'affected_responses':len({(r['case_id'],r['arm']) for r in rejs if r['cohort']==c and r['reason']==reason}),'reference_members':sum(r['cohort']==c and r['reason']==reason and r['reference_member'] for r in rejs)} for c in ['controlled','natural','receipt'] for reason in CHECKS]
    for name,rs in [('archived_gate_per_case',per),('archived_gate_summary',summary),('archived_gate_effects',effects),('archived_gate_rejections',rejs),('archived_gate_changes',changed),('archived_gate_activation',activations)]:write_csv(HERE/(name+'.csv'),rs)
    result={'complete':True,'responses':len(preds),'scored_configurations':len(per),'summary':summary,'effects_exploratory':effects,'activations':activations}
    (HERE/'archived_gate_results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'responses':540,'scored_configurations':len(per),'activations':activations,'effects':effects},indent=2))
if __name__=='__main__':main()
