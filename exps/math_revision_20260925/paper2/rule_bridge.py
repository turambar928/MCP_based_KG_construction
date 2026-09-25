"""Archive-to-execution mechanism prototype, separate from TNEWS scheduling."""
import copy,gzip,hashlib,json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from exps.paper2_offline_revision.rule_study import compile_candidate,predict,label
HERE=Path(__file__).resolve().parent

class RuleBridge:
    """No test labels or inferred aliases are used by this runtime."""
    def __init__(self, rows):
        self.rows=copy.deepcopy(rows)
        self.active={}
        self.rejections=[]
    def acquire(self, candidates):
        before=len(self.active)
        for entry in candidates:
            compiled,reason=compile_candidate(entry['field'],entry['value'])
            if compiled is None:
                self.rejections.append({'candidate_id':entry['candidate_id'],'reason':reason})
            else:
                rid=entry['candidate_id']
                previous=self.active.get(rid,{}).get('sources',[])
                combined={json.dumps(s,sort_keys=True):s for s in previous+entry.get('sources',[])}
                self.active[rid]={'compiled':compiled,'sources':list(combined.values())}
        return len(self.active)-before
    def scan(self):
        rules={r['compiled'] for r in self.active.values()}
        result=[]
        for row in self.rows:
            pred,conflict,permit=predict(rules,row)
            pattern=(row['subject_type'],row['relation'],row['object_type'])
            ids=[rid for rid,rec in self.active.items() if rec['compiled'][1]==pattern]
            result.append({'triple_id':row['triple_id'],'violation':bool(pred),'conflict':bool(conflict),
                'explicit_permission':bool(permit),'rule_ids':ids})
        return result
    def action_mask(self):
        return {'remove_forbidden':any(r['violation'] for r in self.scan())}
    def repair(self):
        # Conservative constraint removal only. No inferred replacement facts.
        matches=[r for r in self.scan() if r['violation']]
        ids={r['triple_id'] for r in matches}
        self.rows=[r for r in self.rows if r['triple_id'] not in ids]
        return matches

def main():
    path=ROOT/'exps/paper2_offline_revision/rule_lineage.jsonl.gz'
    with gzip.open(path,'rt') as f:lineage=[json.loads(line) for line in f]
    original=json.loads((ROOT/'data/rule_test_triples.json').read_text())
    # Labels removed before runtime; preserved separately for descriptive scoring.
    rows=[{k:v for k,v in r.items() if k not in {'expected_detection','data_quality'}} for r in original]
    packets={}
    for strategy in ['deletion','augmentation']:
        packets[strategy]=[{'candidate_id':r['rule_id'],'field':'type_conflict_rules_'+r['kind'],
            'value':r['pattern'],'sources':[s for s in r['sources'] if s['strategy']==strategy]}
            for r in sorted(lineage,key=lambda r:r['rule_id']) if any(s['strategy']==strategy for s in r['sources'])]
    traces=[];summaries=[]
    for strategy in ['deletion','augmentation','union']:
        env=RuleBridge(rows);trace=[{'stage':'initial','mask':env.action_mask(),'n_records':len(env.rows)}]
        stages=['deletion','augmentation'] if strategy=='union' else [strategy]
        for stage in stages:
            n=env.acquire(packets[stage]);scan=env.scan()
            trace.append({'stage':'acquire_'+stage,'new_rules':n,'active_rules':len(env.active),'mask':env.action_mask(),
                'n_violations':sum(r['violation'] for r in scan),'n_conflicts':sum(r['conflict'] for r in scan),
                'matching_records':[r for r in scan if r['rule_ids']]})
        removed=env.repair();ids={r['triple_id'] for r in removed}
        trace.append({'stage':'remove_forbidden','removed':removed,'mask':env.action_mask(),'n_records':len(env.rows)})
        summaries.append({'strategy':strategy,'compiled_active':len(env.active),'removed_records':len(ids),
            'removed_defective_records':sum(r['triple_id'] in ids and label(r) for r in original),
            'removed_clean_records':sum(r['triple_id'] in ids and not label(r) for r in original),
            'retained_clean_records':sum(r['triple_id'] not in ids and not label(r) for r in original),
            'remaining_records':len(env.rows),'inferred_replacement_facts':0,'api_calls':0})
        traces.append({'strategy':strategy,'trace':trace})
    # Explicitly synthetic interface checks, never added to empirical denominators.
    probe={'subject_type':'A','relation':'r','object_type':'B','triple_id':'probe'}
    e=RuleBridge([probe]);e.acquire([{'candidate_id':'f','field':'type_conflict_rules_forbidden','value':['A','r','B']}])
    assert e.action_mask()['remove_forbidden']
    e.acquire([{'candidate_id':'a','field':'type_conflict_rules_allowed','value':['A','r','B']},
        {'candidate_id':'u','field':'procedural_rules','value':'unsupported'},
        {'candidate_id':'m','field':'type_conflict_rules_forbidden','value':['A','r']}])
    assert not e.action_mask()['remove_forbidden'] and e.scan()[0]['conflict'] and len(e.rejections)==2
    result={'scope':'Mechanism prototype on the previously inspected designed RuleTest-94 suite; no fresh holdout, no TNEWS mapping, no factual restoration claim.',
        'summary':summaries,'traces':traces,'synthetic_interface_checks':{'conflict_abstention':True,'rejections':e.rejections},
        'unsupported_archive_candidates':'Preserved in the unchanged candidate_execution_audit.jsonl.gz; only typed compiled entries enter packets.',
        'input_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,ROOT/'data/rule_test_triples.json']},'api_calls':0}
    (HERE/'rule_bridge_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summaries,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
