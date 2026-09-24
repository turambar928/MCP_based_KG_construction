"""Equal-call candidate analysis and exact typed-constraint execution. No API."""
import csv,gzip,hashlib,json,random,sys
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_cooptimization.run_experiment import write_csv
from exps.paper2_dual_strategy_ablation import aggregate_for,rule_set
HERE=Path(__file__).resolve().parent
LOG=ROOT/'exps/rule_suggestions/per_item_rule_suggestions.jsonl'
DECLARATIONS={'entity_types','relationship_types'}
KINDS={'type_conflict_rules_forbidden':'forbidden','type_conflict_rules_allowed':'allowed'}

def compile_candidate(field,value):
    if field not in KINDS:return None,'declaration' if field in DECLARATIONS else 'unsupported_family'
    if not isinstance(value,(list,tuple)) or len(value)!=3 or not all(isinstance(v,str) and v.strip() for v in value):return None,'malformed'
    return (KINDS[field],tuple(v.strip() for v in value)),'compiled'

def label(row):
    value=row['expected_detection'];assert value in ['pass','fail','specialist_miss']
    return value!='pass'

def predict(rules,row):
    pattern=(row['subject_type'],row['relation'],row['object_type'])
    forbidden=('forbidden',pattern) in rules;allowed=('allowed',pattern) in rules
    # Permission alone does not close the world. Conflicting statements abstain.
    return forbidden and not allowed,forbidden and allowed,allowed

def score(rules,cases):
    counts=Counter();preds=[]
    for c in cases:
        pred,conflict,permit=predict(rules,c);gold=label(c)
        counts['tp' if pred and gold else 'fp' if pred else 'fn' if gold else 'tn']+=1
        counts['conflicts']+=conflict
        preds.append({'triple_id':c['triple_id'],'gold':gold,'prediction':pred,'conflict':conflict,'explicit_allow':permit})
    tp,fp,fn,tn=(counts[k] for k in ['tp','fp','fn','tn'])
    return {**{k:counts[k] for k in ['tp','fp','fn','tn','conflicts']},'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,'specificity':tn/(tn+fp) if tn+fp else None},preds

def main():
    paths=[Path(__file__),HERE/'test_rules.py',LOG,ROOT/'data/rule_test_triples.json',ROOT/'exps/paper2_dual_strategy_ablation.py',ROOT/'rule_generate_scripts/generate_rules_from_gov_texts.py']
    manifest={'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
      'budgets':[100,500,1000,2000,4000],'sampling_seeds':list(range(30)),
      'equal_call_protocol':'Same shuffled paired-document inventory per seed. Single strategy uses B documents once each; dual uses both strategies on first B/2 documents. Counts are candidate diversity, not correctness. Report document coverage explicitly.',
      'execution':'Exact subject-type/relation/object-type matching only; forbidden flags, allowed permits; absent allowed entries imply nothing. Conflict abstains. Labels read expected_detection directly, specialist_miss means defective. No aliases or semantic rewriting.',
      'scope':'Designed-suite execution audit of archived candidates. Not independent natural-error or end-to-end RL evidence.'}
    path=HERE/'rule_manifest.json'
    if path.exists():assert json.loads(path.read_text())==manifest
    else:path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    rows=[json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    assert len(rows)==9456
    paired=defaultdict(dict)
    for r in rows:
        assert r['strategy'] not in paired[r['unid']];paired[r['unid']][r['strategy']]=r
    assert len(paired)==4728 and all(set(v)=={'deletion','augmentation'} for v in paired.values())
    candidates={}
    for cid,arms in paired.items():
        for arm,r in arms.items():candidates[cid,arm]=rule_set(aggregate_for([r],arm))
    budgets=[]
    for seed in range(30):
        ids=sorted(paired);random.Random(seed).shuffle(ids)
        for budget in manifest['budgets']:
            for arm in ['deletion','augmentation','dual']:
                chosen=ids[:budget//2 if arm=='dual' else budget];pool=set()
                for cid in chosen:
                    for strategy in ['deletion','augmentation'] if arm=='dual' else [arm]:pool|=candidates[cid,strategy]
                declarations=sum(x.split('::',1)[0] in DECLARATIONS for x in pool)
                budgets.append({'seed':seed,'budget_calls':budget,'strategy':arm,'documents':len(chosen),'unique_candidates':len(pool),'declarations':declarations,'constraint_candidates':len(pool)-declarations})
    budget_summary=[]
    for budget in manifest['budgets']:
        for arm in ['deletion','augmentation','dual']:
            rs=[r for r in budgets if r['budget_calls']==budget and r['strategy']==arm]
            row={'budget_calls':budget,'strategy':arm,'documents':rs[0]['documents'],'sampling_seeds':30}
            for k in ['unique_candidates','declarations','constraint_candidates']:
                a=[r[k] for r in rs];row[k]=float(np.mean(a));row[k+'_p025']=float(np.quantile(a,.025));row[k+'_p975']=float(np.quantile(a,.975))
            budget_summary.append(row)
    cases=json.loads((ROOT/'data/rule_test_triples.json').read_text());assert len(cases)==94
    assert len({c['triple_id'] for c in cases})==94
    stypes={c['subject_type'] for c in cases};otypes={c['object_type'] for c in cases};relations={c['relation'] for c in cases}
    rule_provenance=defaultdict(list);audit=[];status=Counter()
    for line,r in enumerate(rows,1):
        proposal=r['llm_result'].get('proposed_rules') or {}
        for field,values in proposal.items():
            if not isinstance(values,list):
                audit.append({'source_line':line,'unid':r['unid'],'strategy':r['strategy'],'field':field,'value':values,'status':'malformed_container'});status[r['strategy'],'malformed_container']+=1;continue
            for ordinal,value in enumerate(values):
                rule,state=compile_candidate(field,value)
                record={'source_line':line,'unid':r['unid'],'strategy':r['strategy'],'field':field,'ordinal':ordinal,'value':value,'status':state}
                if rule:
                    rule_provenance[rule].append({k:record[k] for k in ['source_line','unid','strategy','field','ordinal']})
                    pat=rule[1];hits=[c['triple_id'] for c in cases if (c['subject_type'],c['relation'],c['object_type'])==pat]
                    record['case_ids']=hits
                    record['mapping']='matched' if hits else 'mapped_unmatched' if pat[0] in stypes and pat[1] in relations and pat[2] in otypes else 'unmapped_vocabulary'
                audit.append(record);status[r['strategy'],record['status']]+=1
    raw=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in audit).encode()
    with (HERE/'candidate_execution_audit.jsonl.gz').open('wb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as z:z.write(raw)
    lineage=[]
    for (kind,pattern),origins in sorted(rule_provenance.items()):
        rule_id=hashlib.sha256(json.dumps([kind,pattern],ensure_ascii=False).encode()).hexdigest()[:16]
        lineage.append({'rule_id':rule_id,'kind':kind,'pattern':pattern,'sources':origins,
          'matched_cases':[c['triple_id'] for c in cases if (c['subject_type'],c['relation'],c['object_type'])==pattern]})
    with (HERE/'rule_lineage.jsonl.gz').open('wb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as z:z.write(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in lineage).encode())
    execution=[];case_predictions=[]
    for arm in ['deletion','augmentation','dual']:
        active={rule for rule,origins in rule_provenance.items() if arm=='dual' or any(o['strategy']==arm for o in origins)}
        metrics,preds=score(active,cases);execution.append({'strategy':arm,'unique_compiled_rules':len(active),**metrics})
        for p in preds:case_predictions.append({'strategy':arm,**p})
    # Re-score original family detectors against stored labels instead of deriving labels from a detector.
    sys.path.insert(0,str(ROOT/'exps'))
    from paper2_rule_family_ablation import DETECTORS
    families=[]
    for name,detector in DETECTORS.items():
        tp=fp=fn=tn=0
        for c in cases:
            pred,_=detector(c);gold=label(c);tp+=pred and gold;fp+=pred and not gold;fn+=not pred and gold;tn+=not pred and not gold
        families.append({'strategy':name,'tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn),'f1':2*tp/(2*tp+fp+fn)})
    for name,rs in [('budget_per_sample',budgets),('budget_summary',budget_summary),('rule_execution',execution),('rule_case_predictions',case_predictions),('family_label_check',families)]:write_csv(HERE/(name+'.csv'),rs)
    outcome={'calls_in_archived_log':9456,'documents':4728,'candidate_occurrences':len(audit),'status':{'|'.join(k):v for k,v in status.items()},
      'unique_compiled':len(lineage),'unique_compiled_with_case_match':sum(bool(r['matched_cases']) for r in lineage),
      'mapping_occurrences':dict(Counter(r.get('mapping','not_compiled') for r in audit)),
      'execution':execution,'family_label_check':families,'budget_summary':budget_summary,
      'audit_uncompressed_sha256':hashlib.sha256(raw).hexdigest()}
    (HERE/'rule_analysis.json').write_text(json.dumps(outcome,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:outcome[k] for k in ['candidate_occurrences','unique_compiled','unique_compiled_with_case_match','mapping_occurrences','execution','family_label_check']},indent=2))
if __name__=='__main__':main()
