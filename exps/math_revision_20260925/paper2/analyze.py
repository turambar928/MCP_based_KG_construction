"""Corrected-environment paired analysis with fixed legacy follow-up scenarios."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from exps.paper2_offline_revision.analyze_policy import paired,holm
from exps.paper2_cooptimization.run_experiment import write_csv
from exps.math_revision_20260925.paper2.policy_study import freeze,VARIANTS,BASELINES
HERE=Path(__file__).resolve().parent

def main():
    freeze();rows=json.loads((HERE/'policy_results.json').read_text())
    names=BASELINES+['model_informed_lookahead']+VARIANTS
    assert len(rows)==110 and {(r['policy'],r['run_seed']) for r in rows}=={(n,s) for n in names for s in range(10)}
    assert len(list((HERE/'training').glob('*/complete.json')))==60
    keys=['final_joint','auc18','q_graph','q_rule','steps','invalid_actions','accounted_calls','actual_api_calls','graph_edits','rule_edits','new_violations','environment_probes','wall_seconds']
    transitions=[json.loads(line) for line in (HERE/'policy_transitions.jsonl').read_text().splitlines()]
    for row in rows:
        trace=[r for r in transitions if r['policy']==row['policy'] and r['run_seed']==row['run_seed']]
        row['discounted_return']=sum(.95**i*r['reward'] for i,r in enumerate(trace))
        row['undiscounted_return']=sum(r['reward'] for r in trace)
    keys+=['discounted_return','undiscounted_return']
    summary=[]
    for name in names:
        rs=[r for r in rows if r['policy']==name];item={'policy':name,'n':len(rs)}
        for k in keys:
            item[k]=float(np.mean([r[k] for r in rs]));item[k+'_std']=float(np.std([r[k] for r in rs],ddof=1))
        summary.append(item)
    index={(r['policy'],r['run_seed']):r for r in rows};tests=[]
    for comparator in ['acquire_then_deficit']+VARIANTS[2:]:
        for metric in ['final_joint','auc18']:
            tests.append({'left':'Double DQN','right':comparator,'metric':metric,**paired([index['Double DQN',s][metric]-index[comparator,s][metric] for s in range(10)])})
    holm(tests)
    transitions=[json.loads(line) for line in (HERE/'policy_transitions.jsonl').read_text().splitlines()]
    assert all(abs(r['reward']-sum(r['reward_components'].values()))<1e-9 for r in transitions)
    assert all(r['new_violations']==sum(v[-1] for v in r['introduced_violation_ids']) for r in transitions)
    histories=[json.loads(p.read_text()) for p in (HERE/'training').glob('*/complete.json')]
    output={'summary':summary,'comparisons':tests,'completed_training_runs':len(histories),
        'completed_training_episodes':sum(r['episodes'] for r in histories),'transitions':len(transitions),
        'summed_training_wall_seconds':sum(r['wall_seconds'] for r in histories),'api_calls':0,
        'scope':'Corrected environment; existing follow-up scenarios; no fresh holdout; all policies retrained or reevaluated.',
        'reward_invariants_verified':True}
    (HERE/'policy_analysis.json').write_text(json.dumps(output,indent=2)+'\n')
    write_csv(HERE/'policy_summary.csv',summary);write_csv(HERE/'policy_comparisons.csv',tests)
    print(json.dumps({'summary':[{k:r[k] for k in ['policy','final_joint','auc18','accounted_calls','new_violations']} for r in summary],'comparisons':tests},indent=2))
if __name__=='__main__':main()
