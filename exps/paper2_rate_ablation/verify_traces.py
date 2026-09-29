"""Independently reconstruct every evaluation graph from the saved deltas."""
import copy,gzip,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_rate_ablation.protocol import HERE,TEST_SEEDS,dump,freeze
from exps.paper2_reward_validation.environment import RewardEnvironment
from exps.paper2_reward_validation.metrics import score,restoration_labels
from exps.paper2_cooptimization.run_experiment import KG,ACTION_NAMES,set_all_seeds
from exps.math_revision_20260925.paper2.policy_study import graph,observe

def main():
 freeze();set_all_seeds(42);clean=graph();starts={}
 for seed in TEST_SEEDS:
  env=RewardEnvironment(clean,seed);starts[seed]=(copy.deepcopy(env.graph),restoration_labels(env))
 expected={(r['policy'],r['run_seed'],r['scenario_seed']):r for r in json.loads((HERE/'results.json').read_text())}
 episodes=0;transitions=0;seen=set()
 for p in sorted((HERE/'evaluation').glob('*/transitions.jsonl.gz')):
  with gzip.open(p,'rt') as f:rows=[json.loads(l) for l in f]
  groups={}
  for r in rows:groups.setdefault((r['policy'],r['run_seed'],r['scenario_seed']),[]).append(r)
  for ident,rs in groups.items():
   assert ident not in seen;seen.add(ident);initial,targets=starts[ident[2]];nodes=copy.deepcopy(initial.nodes);edges={r['_edge_id']:dict(r) for r in initial.rels};invalid=0
   for r in rs:
    assert abs(sum(r['reward_components'].values())-r['reward'])<1e-9
    np.testing.assert_array_equal(observe(np.asarray(r['state']),ident[0]),r['observed_state'])
    action=ACTION_NAMES.index(r['action']);invalid+=not r['mask'][action]
    if ident[0]!='no_mask':assert r['mask'][action]
    else:assert all(r['effective_mask'])
    d=r['graph_delta']
    for k in d['removed_edge_ids']:assert k in edges;del edges[k]
    for e in d['added_edges']:assert e['_edge_id'] not in edges;edges[e['_edge_id']]=e
    for e in d['updated_edges']:assert e['_edge_id'] in edges;edges[e['_edge_id']]=e
    for k in d['removed_node_ids']:assert k in nodes;del nodes[k]
    for k,v in d['added_nodes'].items():assert k not in nodes;nodes[k]=v
    transitions+=1
   final=KG(nodes,list(edges.values()));actual=score(clean,initial,final,targets);reference=expected[ident]
   for k,v in actual.items():assert abs(v-reference[k])<1e-12,(ident,k)
   assert invalid==reference['invalid_actions'];assert len(rs)==reference['steps'];episodes+=1
 assert episodes==2100 and seen==set(expected)
 dump(HERE/'trace_verification.json',{'passed':True,'episodes':episodes,'transitions':transitions,'checks':['graph delta identities and reconstruction','all final reference metrics','observed feature masking','available-action accounting','reward decomposition'],'actual_api_calls':0})
 print('Verified',episodes,'episodes and',transitions,'transitions')
if __name__=='__main__':main()
