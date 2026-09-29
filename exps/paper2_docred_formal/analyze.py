"""Held-out evaluation after training seal; references never enter action selection."""
import itertools,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from exps.paper2_docred_formal.runtime import Network,rollout
from exps.paper2_docred_formal.run import HERE,verify,sha
from exps.paper2_docred_v2_round2.pilot import metrics


def paired(a,b):
    d=np.array(a)-np.array(b);rng=np.random.default_rng(20260929);ci=np.quantile(d[rng.integers(0,len(d),(10000,len(d)))].mean(1),[.025,.975])
    permutations=np.array(list(itertools.product([-1,1],repeat=len(d))))
    p=float(np.mean(np.abs((permutations*d).mean(1))>=abs(d.mean())-1e-12))
    return dict(difference_pp=float(d.mean()*100),ci95_pp=(ci*100).tolist(),p=p)


def holm(rows):
    ordered=sorted(range(len(rows)),key=lambda i:rows[i]['p']);maximum=0
    for rank,i in enumerate(ordered):maximum=max(maximum,min(1,(len(rows)-rank)*rows[i]['p']));rows[i]['p_holm']=maximum
    return rows


def evaluate():
    verify();seal=json.loads((HERE/'training_seal.json').read_text());assert all(sha(ROOT/p)==h for p,h in seal['weights'].items())
    assert seal['evaluation_code_sha256']==sha(Path(__file__))
    cache=json.loads((HERE/'test_cache.json').read_text());refs={r['case_id']:r for r in json.loads((HERE/'local/test_scorer_only.json').read_text())};simple=json.loads((HERE/'simple_outputs.json').read_text())
    rows=[];traces=[];policies=['ddqn','dqn','legacy_ddqn','stop','acquire_then_repair','repair_asap','uniform_feasible','simple']
    for seed in range(20000,20010):
        for policy in policies:
            model=None
            if policy in ['ddqn','dqn','legacy_ddqn']:
                model=Network();weights=torch.load(HERE/'training'/f'{policy}_{seed}'/'checkpoint.pt',map_location='cpu',weights_only=True);assert weights['variant']==policy and weights['seed']==seed
                model.load_state_dict(weights['state_dict']);model.eval()
            for i,item in enumerate(cache):
                if policy=='simple':
                    selected=sum([simple[c]['records'] for c in item['documents']],[]);guard=not selected and bool(item['records'])
                    result=dict(records=item['records'] if guard else selected,events=[],acquired=2,actual_api_calls=0,emptying_guard=guard)
                else:result=rollout(item,policy,seed*1000+i,model)
                # Runtime has completed; scorer-only references are not passed to it.
                gold={(c,*t) for c in item['documents'] for t in refs[c]['reference']};injected={(c,*t) for c in item['documents'] for t in refs[c]['injected']}
                score=metrics(result['records'],gold,injected)
                rows.append(dict(seed=seed,policy=policy,episode=i,**score,acquired=result['acquired']))
                traces.append(dict(seed=seed,policy=policy,episode=i,**result))
    means={p:[{k:float(np.mean([r[k] for r in rows if r['seed']==s and r['policy']==p])) for k in ['f1','correct_preservation','acquired','correct_lost','injected_removed']} for s in range(20000,20010)] for p in policies}
    contrasts=[]
    for p in ['dqn','acquire_then_repair','repair_asap','simple']:
        for k in ['f1','correct_preservation']:contrasts.append(dict(comparator=p,metric=k,**paired([r[k] for r in means['ddqn']],[r[k] for r in means[p]])))
    result=dict(documents=60,episodes=30,run_seeds=10,independent_documents=60,summary={p:{k:float(np.mean([r[k] for r in v])) for k in v[0]} for p,v in means.items()},seed_means=means,primary=holm(contrasts),scope='Controlled reference recovery. Seed repetition is training variability, not new documents. No human semantic claims.',cache_replay_actual_api_calls=0)
    for name,value in [('test_results.json',result),('test_scores.json',rows),('test_traces.json',traces)]:
        path=HERE/name
        if path.exists():assert json.loads(path.read_text())==value,'Existing result differs'
        else:path.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='seed_means'},indent=2))

if __name__=='__main__':evaluate()
