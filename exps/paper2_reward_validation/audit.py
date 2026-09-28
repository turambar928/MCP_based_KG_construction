"""Privileged branch diagnostics on already observed trajectories, never a baseline."""
import copy,gzip,json,sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
from exps.paper2_reward_validation.protocol import HERE,dump
from exps.paper2_reward_validation.environment import RewardEnvironment,RewardConfig,VALID_DETECTORS
from exps.paper2_reward_validation.metrics import fact_changes,score,restoration_labels,graph_delta
from exps.math_revision_20260925.paper2.policy_study import graph

def main():
    clean=graph();source=ROOT/'exps/math_revision_20260925/paper2/policy_transitions.jsonl'
    grouped=defaultdict(list)
    for line in source.open():
        row=json.loads(line)
        if row['policy'] in ['Double DQN','acquire_then_deficit']:grouped[row['policy'],row['run_seed']].append(row)
    rows=[];actual=[];branches=0
    with gzip.open(HERE/'action_audit.jsonl.gz','wt') as f:
        for (policy,run),trajectory in sorted(grouped.items()):
            e=RewardEnvironment(clean,900000+run,reward_config=RewardConfig('raw'))
            initial=copy.deepcopy(e.graph);labels=restoration_labels(e)
            for recorded in trajectory:
                np.testing.assert_allclose(e.state(),recorded['state'],atol=1e-8)
                np.testing.assert_array_equal(e.available_action_mask(),recorded['mask'])
                mask=e.available_action_mask()
                for action in np.flatnonzero(mask):
                    branch=e.clone();before=copy.deepcopy(branch.graph);_,reward,done,info=branch.step(int(action));branches+=1
                    item={'source_policy':policy,'run_seed':run,'source_step':recorded['step'],'trial_action':int(action),
                        'state':e.state().tolist(),'mask':mask.tolist(),'reward_raw':reward,
                        'fact_changes_scorer_only':fact_changes(clean,before,branch.graph),'graph_delta':graph_delta(before,branch.graph),**info}
                    if action==2:
                        follow={'executed':False,'reason':'terminal_or_no_duplicate_action'}
                        two=dict(info['counterfactual_rewards']);saved=copy.deepcopy(branch.graph)
                        if not done and branch.available_action_mask()[1]:
                            _,r2,done2,info2=branch.step(1)
                            follow={'executed':True,'reward_raw':r2,'fact_changes_scorer_only':fact_changes(clean,saved,branch.graph),**info2}
                            two={k:two[k]+.95*info2['counterfactual_rewards'][k] for k in two}
                        item['dedup_followup']=follow;item['two_step_returns']=two
                        rows.append(item)
                    f.write(json.dumps(item)+'\n')
                _,reward,done,info=e.step(recorded['action_id'])
                assert abs(reward-recorded['reward'])<1e-8
            actual.append({'policy':policy,'run_seed':run,**score(clean,initial,e.graph,labels),
                'remaining_defects':e.defect_counts(),'relation_repair_actions':sum(r['action_id']==2 for r in trajectory)})
    # Matched kernel probe with all validators active, before any mutation.
    kernel=[]
    for seed in range(900000,900010):
        e=RewardEnvironment(clean,seed,reward_config=RewardConfig('raw'));e.active_rules=set(VALID_DETECTORS)
        before=copy.deepcopy(e.graph);_,r,done,i=e.step(2);middle=copy.deepcopy(e.graph);_,r2,_,j=e.step(1)
        kernel.append({'seed':seed,'first':i,'second':j,'first_fact_changes':fact_changes(clean,before,middle),
            'second_fact_changes':fact_changes(clean,middle,e.graph),
            'two_step_returns':{m:i['counterfactual_rewards'][m]+.95*j['counterfactual_rewards'][m] for m in ['raw','scaled','zero']}})
    summary={'scope':'Privileged counterfactual diagnostics on previously inspected scenes; no future probes available to evaluated policies.',
        'replayed_trajectories':len(actual),'one_step_branches':branches,'relation_branches':len(rows),'actual_outcomes':actual,
        'kernel_probes':kernel,'relation_branch_means':{},'api_calls':0}
    for policy in ['Double DQN','acquire_then_deficit']:
        rs=[r for r in rows if r['source_policy']==policy]
        summary['relation_branch_means'][policy]={'n':len(rs),'negative_raw_fraction':float(np.mean([r['reward_raw']<0 for r in rs])),
            'added_wrong_facts':sum(r['fact_changes_scorer_only']['added_wrong_facts'] for r in rs),
            'removed_correct_facts':sum(r['fact_changes_scorer_only']['removed_correct_facts'] for r in rs),
            'new_by_kind':{k:sum(r['new_by_kind'][k] for r in rs) for k in ['isolated','duplicate','invalid_relation','dangling']},
            'first_returns':{m:float(np.mean([r['counterfactual_rewards'][m] for r in rs])) for m in ['raw','scaled','zero']},
            'two_step_returns':{m:float(np.mean([r['two_step_returns'][m] for r in rs])) for m in ['raw','scaled','zero']}}
    dump(HERE/'audit_summary.json',summary)
    print(json.dumps({'replayed':len(actual),'branches':branches,'relation_branch_means':summary['relation_branch_means']},indent=2))
if __name__=='__main__':main()
