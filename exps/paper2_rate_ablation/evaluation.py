"""Common rate-reward evaluation, explicit scorer-only fact labels and replay deltas."""
import concurrent.futures,copy,gzip,json,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from exps.paper2_rate_ablation.protocol import *
from exps.math_revision_20260925.paper2.policy_study import graph,choose_simple,observe
from exps.paper2_cooptimization.run_experiment import QNetwork,set_all_seeds
from exps.paper2_reward_validation.environment import RewardEnvironment
from exps.paper2_reward_validation.metrics import score,fact_changes,restoration_labels,graph_delta

def evaluate_run(run):
    set_all_seeds(42);dest=HERE/'evaluation'/f'run_{run}';dest.mkdir(parents=True,exist_ok=True)
    if (dest/'complete.json').exists():return json.loads((dest/'results.json').read_text())
    clean=graph();models={};results=[]
    for policy in POLICIES[:-1]:
        base=ROOT/'exps/paper2_reward_validation' if policy=='ddqn_scaled' else HERE
        saved=torch.load(base/'training'/f'{policy}_{run}'/'checkpoint.pt',weights_only=True,map_location='cpu')
        model=QNetwork(14,8);model.load_state_dict(saved['model_state_dict']);model.eval();models[policy]=model
    with gzip.open(dest/'transitions.jsonl.gz','wt') as f:
        for seed in TEST_SEEDS:
            for policy in POLICIES:
                env=RewardEnvironment(clean,seed);initial=copy.deepcopy(env.graph);targets=restoration_labels(env);invalid=0;curve=[env.normalized_joint_quality()];changes=Counter();reward_sum=0.;begin=time.perf_counter()
                rng=random.Random(70000+run*1000000+seed)
                for step in range(18):
                    state=env.state();mask=env.available_action_mask().astype(bool)
                    if not mask.any():break
                    effective=np.ones(8,bool) if policy=='no_mask' else mask;obs=observe(state,policy)
                    if policy=='acquire_then_deficit':action=choose_simple(policy,state,mask,step,rng)
                    else:
                        with torch.no_grad():action=int(models[policy](torch.tensor(obs).unsqueeze(0)).masked_fill(torch.tensor(~effective).unsqueeze(0),-torch.inf).argmax(1).item())
                    invalid+=not bool(mask[action]);before=copy.deepcopy(env.graph)
                    next_state,reward,done,info=env.step(action);reward_sum+=.95**step*reward;change=fact_changes(clean,before,env.graph);changes.update(change);curve.append(env.normalized_joint_quality())
                    f.write(json.dumps({'policy':policy,'run_seed':run,'scenario_seed':seed,'step':step,'state':state.tolist(),'observed_state':obs.tolist(),'mask':mask.tolist(),'effective_mask':effective.tolist(),'action':action,'reward':reward,'done':done,'scorer_only_fact_changes':change,'graph_delta':graph_delta(before,env.graph),**info})+'\n')
                    if done:break
                padded=curve+[curve[-1]]*(19-len(curve))
                results.append({'policy':policy,'run_seed':run,'scenario_seed':seed,**score(clean,initial,env.graph,targets),'final_joint':curve[-1],'auc18':float(np.trapz(padded)/18),'accounted_calls':env.total_calls,'invalid_actions':int(invalid),'steps':env.step_index,'discounted_scaled_return':reward_sum,**changes,'wall_seconds':time.perf_counter()-begin,'actual_api_calls':0})
    dump(dest/'results.json',results);dump(dest/'complete.json',{'episodes':len(results),'api_calls':0});return results
from collections import Counter

def main():
    freeze();paths=sorted((HERE/'training').glob('*/checkpoint.pt'));assert len(paths)==50
    seal={'checkpoints':{str(p.relative_to(ROOT)):sha(p) for p in paths},'manifest_sha256':sha(HERE/'manifest.json')}
    p=HERE/'test_seal.json'
    if p.exists():assert json.loads(p.read_text())==seal
    else:dump(p,seal)
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as pool:
        for rs in pool.map(evaluate_run,range(10)):results+=rs;print('evaluated',len(results),flush=True)
    assert len(results)==2100 and len({(r['policy'],r['run_seed'],r['scenario_seed']) for r in results})==2100
    dump(HERE/'results.json',results)
if __name__=='__main__':main()
