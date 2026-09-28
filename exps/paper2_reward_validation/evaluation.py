"""Shared-information development/test evaluation, with separate reference scoring."""
import argparse,concurrent.futures,copy,gzip,json,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from exps.paper2_reward_validation.protocol import *
from exps.paper2_reward_validation.environment import RewardEnvironment,RewardConfig
from exps.paper2_reward_validation.risk_baseline import RiskRidge
from exps.paper2_reward_validation.metrics import score,fact_changes,restoration_labels,graph_delta
from exps.math_revision_20260925.paper2.policy_study import graph,choose_simple
from exps.paper2_cooptimization.run_experiment import QNetwork,set_all_seeds

def choose(policy,model,state,mask,step,rng):
    """Only observable features/mask: no environment or reference argument."""
    if not mask.any():return None,{}
    if policy=='risk_ridge':return model.choose(state,mask)
    if policy not in ARMS:return choose_simple(policy,state,mask,step,rng),{}
    with torch.no_grad():
        q=model(torch.tensor(state).unsqueeze(0)).masked_fill(torch.tensor(~mask).unsqueeze(0),-torch.inf)
        return int(q.argmax(1).item()),{}

def load_models(run):
    models={}
    for arm in ARMS:
        saved=torch.load(HERE/'training'/f'{arm}_{run}'/'checkpoint.pt',weights_only=True,map_location='cpu')
        model=QNetwork(14,8);model.load_state_dict(saved['model_state_dict']);model.eval();models[arm]=model
    models['risk_ridge']=RiskRidge.load(HERE/'ridge'/str(run)/'model.npz')
    return models

def evaluate_run(task):
    split,run=task;dest=HERE/split/f'run_{run}';dest.mkdir(parents=True,exist_ok=True)
    if (dest/'complete.json').exists():return json.loads((dest/'results.json').read_text())
    set_all_seeds(42);clean=graph();models=load_models(run);results=[]
    seeds=DEV_SEEDS if split=='development' else TEST_SEEDS
    with gzip.open(dest/'transitions.jsonl.gz','wt') as handle:
        for scenario in seeds:
            for policy in POLICIES:
                env=RewardEnvironment(clean,scenario,reward_config=RewardConfig('scaled'))
                initial=copy.deepcopy(env.graph);targets=restoration_labels(env)
                curve=[env.normalized_joint_quality()];reward_sums=dict.fromkeys(['raw','scaled','zero'],0.)
                new_counts=dict.fromkeys(['isolated','duplicate','invalid_relation','dangling'],0)
                changes=dict.fromkeys(['added_correct_facts','added_wrong_facts','removed_correct_facts','removed_wrong_facts'],0)
                action_counts={};rng=random.Random(70000+run*1000000+scenario);start=time.perf_counter();nsteps=0
                for step in range(18):
                    state=env.state();mask=env.available_action_mask().astype(bool)
                    action,prediction=choose(policy,models.get(policy),state,mask,step,rng)
                    if action is None:break
                    assert mask[action]
                    before=copy.deepcopy(env.graph);next_state,reward,done,info=env.step(action);nsteps+=1
                    assert abs(reward-sum(info['reward_components'].values()))<1e-9
                    change=fact_changes(clean,before,env.graph);delta=graph_delta(before,env.graph)
                    for mode in reward_sums:reward_sums[mode]+=.95**step*info['counterfactual_rewards'][mode]
                    for kind in new_counts:new_counts[kind]+=info['new_by_kind'][kind]
                    for k in changes:changes[k]+=change[k]
                    action_counts[info['action']]=action_counts.get(info['action'],0)+1
                    curve.append(env.normalized_joint_quality())
                    row={'policy':policy,'run_seed':run,'scenario_seed':scenario,'step_index':step,
                        'state':state.tolist(),'mask':mask.tolist(),'action_id':action,'next_state':next_state.tolist(),
                        'reward':reward,'done':done,'prediction':prediction,'fact_changes_scorer_only':change,'graph_delta':delta,**info}
                    handle.write(json.dumps(row)+'\n')
                    if done:break
                padded=curve+[curve[-1]]*(19-len(curve));assert len(padded)==19
                result={'policy':policy,'run_seed':run,'scenario_seed':scenario,**score(clean,initial,env.graph,targets),
                    'final_joint':env.normalized_joint_quality(),'auc18':float(np.trapz(padded)/18),
                    'accounted_calls':env.total_calls,'total_edits':env.total_edits,'steps':nsteps,
                    'new_violations':sum(new_counts.values()),'new_by_kind':new_counts,'action_counts':action_counts,
                    'remaining_defects':env.defect_counts(),'curve18':padded,'discounted_return':reward_sums['scaled'],
                    'counterfactual_returns':reward_sums,**changes,'wall_seconds':time.perf_counter()-start,
                    'actual_api_calls':0,'environment_probes':0}
                results.append(result)
    dump(dest/'results.json',results);dump(dest/'complete.json',{'split':split,'run_seed':run,'episodes':len(results),'api_calls':0})
    return results

def main():
    p=argparse.ArgumentParser();p.add_argument('split',choices=['development','test']);p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    freeze()
    if a.split=='test':seal_test()
    folder=HERE/a.split;folder.mkdir(exist_ok=True)
    clean=graph();seeds=DEV_SEEDS if a.split=='development' else TEST_SEEDS
    # Independent initial snapshots make every graph-delta trajectory replayable.
    with gzip.open(folder/'initial_graphs.jsonl.gz','wt') as f:
        for seed in seeds:
            env=RewardEnvironment(clean,seed)
            f.write(json.dumps({'scenario_seed':seed,'nodes':env.graph.nodes,'rels':env.graph.rels,
                'restoration_targets_scorer_only':restoration_labels(env)})+'\n')
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        for rows in pool.map(evaluate_run,[(a.split,r) for r in range(10)]):
            results.extend(rows);print(a.split,'completed seed block',len(results),flush=True)
    expected={(p,r,s) for p in POLICIES for r in range(10) for s in seeds}
    assert {(r['policy'],r['run_seed'],r['scenario_seed']) for r in results}==expected
    assert len(results)==len(expected)
    assert all(r['actual_api_calls']==0 and r['environment_probes']==0 for r in results)
    dump(folder/'results.json',results)
    dump(folder/'verification.json',{'passed':True,'evaluation_episodes':len(results),'distinct_scenarios':len(seeds),
        'mode':'All predefined policies retained; no validation selection.','api_calls':0})
if __name__=='__main__':main()
