"""One-step ridge baseline learned from separate feasible-random rollouts."""
import argparse,concurrent.futures,gzip,json,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
from exps.paper2_reward_validation.protocol import HERE,CFG,dump,freeze
from exps.paper2_reward_validation.environment import RewardEnvironment,RewardConfig
from exps.math_revision_20260925.paper2.policy_study import graph

class RiskRidge:
    def __init__(self,mu,sd,coef):self.mu=mu;self.sd=sd;self.coef=coef
    @classmethod
    def fit(cls,observations,actions,targets):
        observations=np.asarray(observations,float);actions=np.asarray(actions);targets=np.asarray(targets,float)
        means=[];scales=[];weights=[]
        for action in range(8):
            x=observations[actions==action];y=targets[actions==action]
            if len(x)<2:raise ValueError('Insufficient training examples for action '+str(action))
            mu=x.mean(0);sd=np.maximum(x.std(0),1e-6)
            z=np.column_stack([np.ones(len(x)),(x-mu)/sd]);penalty=np.eye(15);penalty[0,0]=0.
            coef=np.linalg.solve(z.T@z+penalty,z.T@y)
            means.append(mu);scales.append(sd);weights.append(coef)
        return cls(np.asarray(means),np.asarray(scales),np.asarray(weights))
    @classmethod
    def load(cls,path):
        with np.load(path,allow_pickle=False) as f:return cls(f['mu'],f['sd'],f['coef'])
    def predict(self,state):
        x=(np.asarray(state)-self.mu)/self.sd
        z=np.column_stack([np.ones(8),x]);pred=np.einsum('ai,aij->aj',z,self.coef)
        assert np.isfinite(pred).all()
        pred[:,1:]=np.maximum(0.,pred[:,1:])
        return pred
    def choose(self,state,mask):
        feasible=np.flatnonzero(mask)
        if not len(feasible):return None,{}
        pred=self.predict(state);calls=np.asarray([0,0,0,0,1,1,2,0])
        scores=pred[:,0]-.00002*pred[:,1]-pred[:,2]-.004*calls
        action=int(feasible[np.argmax(scores[feasible])])
        return action,{'predicted_components':pred.tolist(),'feasible_predicted_rewards':[float(scores[a]) if mask[a] else None for a in range(8)]}

def train_one(run):
    dest=HERE/'ridge'/str(run)
    if (dest/'complete.json').exists():return {'run':run,'cached':True}
    dest.mkdir(parents=True,exist_ok=True);started=time.perf_counter();seed=30000+run;rng=random.Random(seed)
    clean=graph();xs=[];actions=[];ys=[];episodes=[]
    with gzip.open(dest/'rollouts.jsonl.gz','wt') as handle:
        for episode in range(250):
            env=RewardEnvironment(clean,seed*100000+episode,reward_config=RewardConfig('scaled'))
            for step in range(18):
                state=env.state();mask=env.available_action_mask().astype(bool);feasible=np.flatnonzero(mask)
                if not len(feasible):break
                action=int(rng.choice(feasible));nxt,reward,done,info=env.step(action)
                targets=[info['reward_components']['quality_gain'],info['edits'],info['scaled_new_burden']]
                xs.append(state.tolist());actions.append(action);ys.append(targets)
                handle.write(json.dumps({'episode':episode,'scenario_seed':seed*100000+episode,'step':step,
                    'state':state.tolist(),'mask':mask.tolist(),'action':action,'targets':targets,'reward':reward,'next_state':nxt.tolist(),'done':done})+'\n')
                if done:break
            episodes.append(step+1)
    model=RiskRidge.fit(xs,actions,ys)
    np.savez(dest/'model.npz',mu=model.mu,sd=model.sd,coef=model.coef)
    result={'run':run,'training_seed':seed,'episodes':250,'training_transitions':len(xs),
        'action_counts':np.bincount(actions,minlength=8).tolist(),'alpha':1.,'wall_seconds':time.perf_counter()-started,
        'references_used':False,'counterfactual_probes':0,'api_calls':0}
    dump(dest/'complete.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);a=p.parse_args();freeze()
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        for r in pool.map(train_one,range(10)):print(json.dumps(r),flush=True)
