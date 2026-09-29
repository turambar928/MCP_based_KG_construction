"""Attribute archived development deletions; references are post-hoc scoring only."""
import collections,json
from pathlib import Path
from exps.paper2_docred_v2.environment import SourceRuleEnvironment
HERE=Path(__file__).resolve().parent

def audit(folder=HERE):
    refs={r['case_id']:r for r in json.loads((folder/'local/pilot_scorer_only.json').read_text())}
    public={r['document']['case_id']:r for r in json.loads((folder/'local/pilot_public.json').read_text())}
    packets=json.loads((folder/'pilot_packets_public.json').read_text());lookup={(p['source_document_id'],p['strategy']):p for p in packets};counts=collections.Counter();details=[]
    for e in json.loads((folder/'pilot_traces.json').read_text()):
        for policy,out in e['policies'].items():
            ids=e['documents'];records=sum([public[c]['records'] for c in ids],[]);gold={(c,*t) for c in ids for t in refs[c]['reference']}
            env=SourceRuleEnvironment(records,{s:[lookup[c,s] for c in ids] for s in ['deletion','augmentation']})
            for event in out['events']:
                scans=env.scan()
                for r in env.records:
                    if r['record_id'] not in event['removed_ids']:continue
                    correct=(r['source_document_id'],r['head_entity_id'],r['relation'],r['tail_entity_id']) in gold
                    source=scans[r['record_id']]['source_contradicted'];counts[(policy,'correct' if correct else 'injected','source' if source else 'type')]+=1
                    details.append(dict(episode=e['episode'],policy=policy,record=r,correct=correct,source_contradicted=source))
                actual=env.step(event['action'])[3];assert json.loads(json.dumps(actual))==event
    (folder/'removal_attribution.json').write_text(json.dumps(details,indent=2)+'\n')
    summary=[dict(policy=k[0],reference_status=k[1],constraint=k[2],count=v) for k,v in sorted(counts.items())]
    (folder/'removal_counts.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

if __name__=='__main__':print(json.dumps(audit(),indent=2))
