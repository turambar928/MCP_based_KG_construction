"""Offline preservation checks and replay of every recorded action."""
import gzip,hashlib,json,socket,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_rule_integration.runtime import ArchiveReplay
from exps.paper2_rule_integration.audit import load_rules,load_data,dump
from exps.paper1_reextraction_control.prepare import prepare
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    preserved=json.loads((HERE/'preservation.json').read_text())['sha256']
    for p,h in preserved.items():assert sha(ROOT/p)==h,p
    manifest=json.loads((HERE/'input_manifest.json').read_text())
    for p,h in manifest['sha256'].items():assert sha(ROOT/p)==h,p
    transitions=0
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Network forbidden in verification')):
        _,packets,counts=load_rules();data,labels,_,types=load_data()
        assert types==manifest['node_type_counts']
        with gzip.open(HERE/'schedule_traces.jsonl.gz','rt') as f:traces=[json.loads(l) for l in f]
        assert len(traces)==16
        for trace in traces:
            s=trace['summary'];env=ArchiveReplay(data[s['dataset']],packets,counts)
            assert env.observe()==trace['initial_observation']
            for saved in trace['events']:
                _,_,event=env.step(saved['action'])
                for key in saved:
                    if key!='wall_seconds':assert event[key]==saved[key],(s['dataset'],key)
                transitions+=1
            assert env.done and len(env.records)==s['remaining_records']
            assert len(env.removed)==s['removed_records'] and len(env.active)==s['active_rules']
            assert s['factual_accuracy'] is None
            if s['dataset']=='RuleTest-94':
                assert sum(labels[k]['defective'] for k in env.removed)==s['removed_designed_defects']==10
                assert sum(not labels[k]['defective'] for k in env.removed)==s['removed_designed_clean']==0
            else:assert not env.removed
        paper1=prepare()
        assert paper1['planned_responses']==240
        assert not (ROOT/'exps/paper1_reextraction_control/results.json').exists()
        assert not (ROOT/'exps/paper1_reextraction_control/responses.jsonl').exists()
    result={'passed':True,'protected_legacy_files':len(preserved),'replayed_trajectories':len(traces),
            'replayed_steps':transitions,'paper1_prepared_requests':240,'paper1_formal_results':0,
            'actual_api_calls':0,'network_blocked_during_verification':True,'new_policy_training':False,
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted(HERE.glob('*.py'))}}
    dump(HERE/'verification.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
