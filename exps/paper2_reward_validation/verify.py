"""Read-only reconstruction of every saved development/test trajectory."""
import copy,csv,gzip,json,platform,sys
from pathlib import Path
from importlib.metadata import version
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_reward_validation.protocol import HERE,ARMS,POLICIES,DEV_SEEDS,TEST_SEEDS,freeze,seal_test,sha,dump
from exps.paper2_reward_validation.metrics import score
from exps.math_revision_20260925.paper2.policy_study import graph
from exps.paper2_cooptimization.run_experiment import KG,ALLOWED_RELATIONS

def check_split(split,seeds):
    folder=HERE/split
    results=json.loads((folder/'results.json').read_text())
    index={(r['policy'],r['run_seed'],r['scenario_seed']):r for r in results}
    expected={(p,r,s) for p in POLICIES for r in range(10) for s in seeds}
    assert set(index)==expected and len(results)==len(expected)
    with gzip.open(folder/'initial_graphs.jsonl.gz','rt') as f:
        initial={r['scenario_seed']:r for r in map(json.loads,f)}
    clean=graph();trajectories=0;transitions=0
    for run in range(10):
        current=None;seen=set()
        def finish(key,nodes,edges,returns,counts,steps,calls,edits):
            nonlocal trajectories
            r=index[key];start=initial[key[2]]
            computed=score(clean,KG(start['nodes'],start['rels']),KG(nodes,list(edges.values())),start['restoration_targets_scorer_only'])
            for metric,value in computed.items():assert abs(value-r[metric])<1e-10,(key,metric)
            for mode,value in returns.items():assert abs(value-r['counterfactual_returns'][mode])<1e-10
            assert counts==r['new_by_kind']
            assert steps==r['steps'] and calls==r['accounted_calls'] and edits==r['total_edits']
            assert r['actual_api_calls']==r['environment_probes']==0
            connected={e[k] for e in edges.values() for k in ('start_id','end_id') if e[k] in nodes}
            triple_set={(e['start_id'],e['relation_type'],e['end_id']) for e in edges.values()}
            defects={'isolated':len(nodes.keys()-connected),'duplicate':len(edges)-len(triple_set),
                'invalid_relation':sum(e['relation_type'] not in ALLOWED_RELATIONS for e in edges.values()),
                'dangling':sum(e['start_id'] not in nodes or e['end_id'] not in nodes for e in edges.values())}
            assert defects==r['remaining_defects']
            trajectories+=1
        with gzip.open(folder/f'run_{run}'/'transitions.jsonl.gz','rt') as f:
            for row in map(json.loads,f):
                key=row['policy'],row['run_seed'],row['scenario_seed']
                if key!=current:
                    if current is not None:finish(current,nodes,edges,returns,counts,steps,calls,edits)
                    assert key not in seen;seen.add(key);current=key;start=initial[key[2]]
                    nodes=copy.deepcopy(start['nodes']);edges={e['_edge_id']:copy.deepcopy(e) for e in start['rels']}
                    returns=dict.fromkeys(['raw','scaled','zero'],0.)
                    counts=dict.fromkeys(['isolated','duplicate','invalid_relation','dangling'],0);steps=calls=edits=0
                assert row['step_index']==steps and row['mask'][row['action_id']]
                assert abs(row['reward']-sum(row['reward_components'].values()))<1e-10
                assert abs(row['reward']-row['counterfactual_rewards']['scaled'])<1e-10
                for mode in returns:returns[mode]+=.95**steps*row['counterfactual_rewards'][mode]
                for kind in counts:counts[kind]+=row['new_by_kind'][kind]
                d=row['graph_delta']
                for identity in d['removed_edge_ids']:edges.pop(identity)
                for edge in d['updated_edges']:
                    assert edge['_edge_id'] in edges;edges[edge['_edge_id']]=edge
                for edge in d['added_edges']:
                    assert edge['_edge_id'] not in edges;edges[edge['_edge_id']]=edge
                for identity in d['removed_node_ids']:nodes.pop(identity)
                for identity,node in d['added_nodes'].items():assert identity not in nodes;nodes[identity]=node
                steps+=1;calls+=row['calls'];edits+=row['edits'];transitions+=1
            if current is not None:finish(current,nodes,edges,returns,counts,steps,calls,edits)
        assert seen=={key for key in expected if key[1]==run}
    assert trajectories==len(expected)
    return {'passed':True,'trajectories_reconstructed':trajectories,'transitions_checked':transitions}

def main():
    freeze();seal_test()
    legacy=json.loads((ROOT/'exps/math_revision_20260925/manifest.json').read_text())
    for p,h in legacy['source_sha256'].items():assert sha(ROOT/p)==h,p
    episodes=0
    for arm in ARMS:
        for run in range(10):
            folder=HERE/'training'/f'{arm}_{run}'
            rows=list(csv.DictReader((folder/'history.csv').open()))
            assert len(rows)==250 and [int(r['episode']) for r in rows]==list(range(1,251))
            m=json.loads((folder/'complete.json').read_text());assert m['api_calls']==0
            assert sum(int(r['steps']) for r in rows)==m['training_transitions'];episodes+=len(rows)
    ridge_steps=0
    for run in range(10):
        folder=HERE/'ridge'/str(run);m=json.loads((folder/'complete.json').read_text())
        with gzip.open(folder/'rollouts.jsonl.gz','rt') as f:rows=list(map(json.loads,f))
        assert {r['episode'] for r in rows}==set(range(250))
        assert len(rows)==m['training_transitions']
        assert all(r['mask'][r['action']] for r in rows)
        assert m['api_calls']==m['counterfactual_probes']==0 and not m['references_used'];ridge_steps+=len(rows)
    result={'passed':True,'neural_models':40,'neural_episodes':episodes,'ridge_models':10,'ridge_episodes':2500,
        'ridge_transitions':ridge_steps,'training_and_test_seals_match':True,'legacy_sources_match':True,
        'development':check_split('development',DEV_SEEDS),'test':check_split('test',TEST_SEEDS),
        'api_calls':0,'downloads':0,'dependencies':{'python':sys.version,'platform':platform.platform(),
        **{k:version(k) for k in ['numpy','torch','scipy','matplotlib']}}}
    dump(HERE/'verification.json',result)
    paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='artifact_manifest.json']
    dump(HERE/'artifact_manifest.json',{'sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}})
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
