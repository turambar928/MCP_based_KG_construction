"""Fixed-weight transfer over disjoint graph replications; no API or fitting."""
import concurrent.futures,copy,gzip,hashlib,json,random,sys,time,tracemalloc
from pathlib import Path
from collections import Counter
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.math_revision_20260925.paper2.policy_study import graph,choose_simple
from exps.paper2_cooptimization.run_experiment import KG,QNetwork,set_all_seeds
from exps.paper2_reward_validation.environment import RewardEnvironment
from exps.paper2_reward_validation.metrics import score,restoration_labels,graph_delta
from exps.paper1_ablation_completion.analyze import write_csv
HERE=Path(__file__).resolve().parent
SCALES=[1,2,4,8];SEEDS=list(range(960000,960005));POLICIES=['ddqn_scaled','ddqn_raw','small_count','acquire_then_deficit']
def replicate(g,n):
    nodes={};rels=[]
    for i in range(n):
        prefix=f'copy{i}:'
        for k,v in g.nodes.items():nodes[prefix+k]={**v,'id':prefix+k}
        for r in g.rels:rels.append({**r,'start_id':prefix+r['start_id'],'end_id':prefix+r['end_id']})
    return KG(nodes,rels)
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def freeze():
    paths=[Path(__file__),HERE/'test_study.py',ROOT/'exps/paper2_rate_ablation/calibration.json',ROOT/'exps/paper2_reward_validation/environment.py',ROOT/'exps/math_revision_20260925/paper2/environment.py',ROOT/'exps/math_revision_20260925/paper2/policy_study.py',ROOT/'exps/paper2_cooptimization/run_experiment.py',ROOT/'exps/paper2_reward_validation/metrics.py']
    m={'scales':SCALES,'scenarios':SEEDS,'training_seeds':list(range(10)),'policies':POLICIES,'scope':'Disjoint ID-renamed replications of the same base graph, 1/2/4/8 copies. Not natural connected-KG growth or new domains. Frozen policies trained only at base size.','evaluation_episodes':800,'timing':'Main wall time covers 18-step rollout, inference and trace construction, excludes model loading and env construction. Dedicated resource measurements separately include env init+heuristic rollout.','memory':'Dedicated sequential tracemalloc peak Python allocations for environment+heuristic; excludes prebuilt clean graph, native tensor allocations and loaded weights. Not total RSS. Three repeats per scale, no API.','statistics':'Descriptive seed-mean ranges and means over 5 fixed corruption seeds at each scale; no new confirmatory superiority tests.','sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'api_calls':0}
    p=HERE/'manifest.json'
    if p.exists():assert json.loads(p.read_text())==m
    else:dump(p,m)
def run_one(run):
    set_all_seeds(42);dest=HERE/'evaluation'/str(run);dest.mkdir(parents=True,exist_ok=True)
    if (dest/'results.json').exists():return json.loads((dest/'results.json').read_text())
    models={};rows=[];base=graph();coefficient=json.loads((ROOT/'exps/paper2_rate_ablation/calibration.json').read_text())['coefficient']
    for policy in POLICIES[:-1]:
        folder=ROOT/'exps'/('paper2_rate_ablation' if policy=='small_count' else 'paper2_reward_validation')
        ck=torch.load(folder/'training'/f'{policy}_{run}'/'checkpoint.pt',map_location='cpu',weights_only=True)
        model=QNetwork(14,8);model.load_state_dict(ck['model_state_dict']);model.eval();models[policy]=model
    with gzip.open(dest/'traces.jsonl.gz','wt') as f:
        for scale in SCALES:
            clean=replicate(base,scale)
            for seed in SEEDS:
                for policy in POLICIES:
                    env=RewardEnvironment(clean,seed);initial=copy.deepcopy(env.graph);targets=restoration_labels(env);rate=0.;small=0.;raw=0.;begin=time.perf_counter();events=[]
                    for step in range(18):
                        state=env.state();mask=env.available_action_mask().astype(bool)
                        if not mask.any():break
                        if policy=='acquire_then_deficit':a=choose_simple(policy,state,mask,step,random.Random(seed))
                        else:
                            with torch.no_grad():a=int(models[policy](torch.tensor(state).unsqueeze(0)).masked_fill(torch.tensor(~mask).unsqueeze(0),-torch.inf).argmax(1).item())
                        before=copy.deepcopy(env.graph);_,reward,done,info=env.step(a)
                        rate+=info['scaled_new_burden'];small+=coefficient*info['new_violations'];raw+=.01*info['new_violations']
                        events.append({'step':step,'action':a,'state':state.tolist(),'mask':mask.tolist(),'reward':reward,'graph_delta':graph_delta(before,env.graph),**info})
                        if done:break
                    row={'run_seed':run,'scale':scale,'scenario':seed,'policy':policy,'clean_nodes':len(clean.nodes),'clean_edges':len(clean.rels),**score(clean,initial,env.graph,targets),'accounted_calls':env.total_calls,'steps':env.step_index,'rate_penalty_sum':rate,'fixed_small_count_penalty_sum':small,'raw_penalty_sum':raw,'wall_seconds':time.perf_counter()-begin,'api_calls':0}
                    rows.append(row);f.write(json.dumps({'result':row,'events':events})+'\n')
    dump(dest/'results.json',rows);return rows
def resource_measurement():
    set_all_seeds(42);base=graph();rows=[]
    for scale in SCALES:
        clean=replicate(base,scale)
        for repeat in range(3):
            tracemalloc.start();begin=time.perf_counter();env=RewardEnvironment(clean,960000+repeat)
            for step in range(18):
                state=env.state();mask=env.available_action_mask().astype(bool)
                if not mask.any():break
                a=choose_simple('acquire_then_deficit',state,mask,step,random.Random(42));_,_,done,_=env.step(a)
                if done:break
            seconds=time.perf_counter()-begin;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            rows.append({'scale':scale,'repeat':repeat,'clean_nodes':len(clean.nodes),'clean_edges':len(clean.rels),'seconds_with_tracemalloc':seconds,'peak_python_bytes':peak,'actual_api_calls':0})
    dump(HERE/'resources.json',rows);write_csv(HERE/'resources.csv',rows)
def main():
    freeze();paths=[]
    for p in POLICIES[:-1]:
        folder=ROOT/'exps'/('paper2_rate_ablation' if p=='small_count' else 'paper2_reward_validation')
        paths+=list((folder/'training').glob(p+'_*/checkpoint.pt'))
    assert len(paths)==30
    seal={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};p=HERE/'model_seal.json'
    if p.exists():assert json.loads(p.read_text())==seal
    else:dump(p,seal)
    rows=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for rs in pool.map(run_one,range(10)):rows+=rs;print('scale outcomes',len(rows),flush=True)
    assert len(rows)==800;dump(HERE/'results.json',rows);summary=[]
    for scale in SCALES:
        for policy in POLICIES:
            rs=[r for r in rows if r['scale']==scale and r['policy']==policy]
            summary.append({'scale':scale,'policy':policy,'n':len(rs),**{k:float(np.mean([r[k] for r in rs])) for k in ['fact_f1','invalid_relation_repair_rate','correct_fact_preservation','accounted_calls','rate_penalty_sum','fixed_small_count_penalty_sum','raw_penalty_sum','wall_seconds']}})
    dump(HERE/'summary.json',summary);write_csv(HERE/'summary.csv',summary);resource_measurement()
if __name__=='__main__':main()
