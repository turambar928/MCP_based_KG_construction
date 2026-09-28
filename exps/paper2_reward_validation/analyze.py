"""Seed-level paired analysis; scenarios are averaged before inferential tests."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
from exps.paper2_reward_validation.protocol import *
from exps.paper2_offline_revision.analyze_policy import paired,holm
from exps.paper2_cooptimization.run_experiment import write_csv

METRICS=['fact_f1','invalid_relation_repair_rate','correct_fact_preservation','lost_initial_correct_facts',
 'remaining_wrong_facts','missing_reference_facts','new_wrong_facts_final','final_duplicate_excess',
 'final_joint','auc18','accounted_calls','total_edits','steps','new_violations','discounted_return',
 'added_correct_facts','added_wrong_facts','removed_correct_facts','removed_wrong_facts','wall_seconds']

def analyze(split):
    freeze()
    if split=='test':seal_test()
    rows=json.loads((HERE/split/'results.json').read_text());seeds=DEV_SEEDS if split=='development' else TEST_SEEDS
    assert len(rows)==len(POLICIES)*10*len(seeds)
    per_seed=[]
    for policy in POLICIES:
        for run in range(10):
            rs=[r for r in rows if r['policy']==policy and r['run_seed']==run];assert len(rs)==len(seeds)
            values={'policy':policy,'run_seed':run,**{k:float(np.mean([r[k] for r in rs])) for k in METRICS}}
            for kind in ['isolated','duplicate','invalid_relation','dangling']:
                values['remaining_'+kind]=float(np.mean([r['remaining_defects'][kind] for r in rs]))
                values['introduced_'+kind]=float(np.mean([r['new_by_kind'][kind] for r in rs]))
            values['relation_repair_actions']=float(np.mean([r['action_counts'].get('relation_repair',0) for r in rs]))
            values['raw_discounted_return']=float(np.mean([r['counterfactual_returns']['raw'] for r in rs]))
            per_seed.append(values)
    keys=[k for k in per_seed[0] if k not in ['policy','run_seed']];summary=[]
    for policy in POLICIES:
        rs=[r for r in per_seed if r['policy']==policy];out={'policy':policy,'n_training_seeds':10,'scenarios_per_seed':len(seeds)}
        for k in keys:out[k]=float(np.mean([r[k] for r in rs]));out[k+'_std']=float(np.std([r[k] for r in rs],ddof=1))
        summary.append(out)
    tests=[]
    if split=='test':
        index={(r['policy'],r['run_seed']):r for r in per_seed}
        for comparator in PRIMARY_COMPARATORS:
            for metric in PRIMARY_METRICS:
                diff=[index['ddqn_scaled',s][metric]-index[comparator,s][metric] for s in range(10)]
                tests.append({'left':'ddqn_scaled','right':comparator,'metric':metric,**paired(diff)})
        holm(tests)
    result={'split':split,'summary':summary,'comparisons':tests,'unit':'Ten run-seed means, each averaged over the same fixed scenario set.',
        'scope':'Controlled structural references and unseen corruption seeds; no new documents/domains or natural-error labels.',
        'actual_api_calls':0,'reward_for_all_policy_returns':'scaled','scenarios':len(seeds),'evaluation_episodes':len(rows)}
    dump(HERE/split/'analysis.json',result);write_csv(HERE/split/'seed_means.csv',per_seed);write_csv(HERE/split/'summary.csv',summary)
    if tests:write_csv(HERE/split/'comparisons.csv',tests)
    print(json.dumps({'split':split,'summary':[{k:r[k] for k in ['policy','fact_f1','invalid_relation_repair_rate','new_violations','accounted_calls']} for r in summary]},indent=2))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('split',choices=['development','test']);analyze(a.parse_args().split)
