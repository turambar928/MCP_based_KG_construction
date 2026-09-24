"""Frozen paired scoring on the common evaluation budget."""
import itertools,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_cooptimization.run_experiment import write_csv
HERE=Path(__file__).resolve().parent

def paired(values):
    x=np.array(values,float);rng=np.random.default_rng(42)
    boot=x[rng.integers(len(x),size=(10000,len(x)))].mean(1)
    simulated=np.asarray(list(itertools.product([-1,1],repeat=len(x))))@x/len(x)
    return {'difference':float(x.mean()),'ci_low':float(np.quantile(boot,.025)),'ci_high':float(np.quantile(boot,.975)),
      'two_sided_p':float(np.mean(abs(simulated)>=abs(x.mean())-1e-12))}

def holm(rows):
    order=sorted(rows,key=lambda r:r['two_sided_p']);prev=0
    for i,r in enumerate(order):prev=max(prev,min(1.,(len(rows)-i)*r['two_sided_p']));r['p_holm']=prev

def main():
    from exps.paper2_offline_revision.policy_study import freeze,VARIANTS,BASELINES
    freeze();rows=json.loads((HERE/'policy_results.json').read_text());names=BASELINES+['DQN','Double DQN','model_informed_lookahead']+VARIANTS
    assert len(rows)==110 and {(r['policy'],r['run_seed']) for r in rows}=={(p,s) for p in names for s in range(10)}
    summary=[]
    keys=['final_joint','auc18','q_graph','q_rule','steps','invalid_actions','accounted_calls','actual_api_calls','graph_edits','rule_edits','environment_probes','wall_seconds']
    for name in names:
        rs=[r for r in rows if r['policy']==name];item={'policy':name,'n':len(rs)}
        for k in keys:
            item[k]=float(np.mean([r[k] for r in rs]));item[k+'_std']=float(np.std([r[k] for r in rs],ddof=1))
        summary.append(item)
    index={(r['policy'],r['run_seed']):r for r in rows};tests=[]
    for comparator in ['acquire_then_deficit']+VARIANTS:
        for metric in ['final_joint','auc18']:
            diff=[index['Double DQN',s][metric]-index[comparator,s][metric] for s in range(10)]
            tests.append({'left':'Double DQN','right':comparator,'metric':metric,**paired(diff)})
    holm(tests)
    old=json.loads((ROOT/'exps/paper2_cooptimization/results.json').read_text())
    # Original results are compared via their CSV to avoid relying on a report's rounding.
    import csv
    for r in csv.DictReader((ROOT/'exps/paper2_cooptimization/per_seed_results.csv').open()):
        if r['policy'] in ['DQN','Double DQN']:
            now=index[r['policy'],int(r['run_seed'])]
            assert abs(now['final_joint']-float(r['final_joint']))<1e-9
            assert now['accounted_calls']==int(r['calls'])
    write_csv(HERE/'policy_summary.csv',summary);write_csv(HERE/'policy_comparisons.csv',tests)
    result={'summary':summary,'comparisons':tests,'existing_checkpoints_reproduced':20,'primary_comparator':'acquire_then_deficit','api_calls':0}
    (HERE/'policy_analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'summary':[{k:r[k] for k in ['policy','final_joint','auc18','invalid_actions','accounted_calls']} for r in summary],'comparisons':tests},indent=2))
if __name__=='__main__':main()
