"""Source-free costs and deterministic recompilation checks for a complete pilot."""
import importlib,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent

def audit(folder=HERE):
    generator=importlib.import_module('exps.'+folder.name+'.generation')
    public={x['document']['case_id']:x for x in json.loads((folder/'local/pilot_public.json').read_text())}
    relations=json.loads((folder.parent/'paper2_docred/relations.json').read_text())
    responses=[json.loads(l) for l in (folder/'local/pilot_responses.jsonl').read_text().splitlines()]
    packets={(p['source_document_id'],p['strategy']):p for p in json.loads((folder/'pilot_packets_public.json').read_text())}
    costs=[];evidence_count=0
    for row in responses:
        x=public[row['case_id']];ok,rules,_=generator.compile_response(row['raw_response'],x['document'],x['records'],relations)
        assert ok==packets[row['case_id'],row['arm']]['parse_success'] and rules==packets[row['case_id'],row['arm']]['rules']
        for rule in rules:
            for ev in rule.get('evidence',[]):
                sentence=' '.join(x['document']['sents'][ev['sentence_id']]);quote=sentence[ev['start']:ev['end']]
                assert hashlib.sha256(quote.encode()).hexdigest()==ev['quote_sha256'];evidence_count+=1
        costs.append({k:row[k] for k in ['case_id','arm','model','returned_model','transport_status','calls','usage','wall_seconds','attempts','request_sha256','finish_reason']})
    summary=dict(outcomes=len(costs),requests=sum(r['calls'] for r in costs),validated_evidence_spans=evidence_count,latency_sum_seconds=sum(r['wall_seconds'] for r in costs),scope='Summed request latency includes retries/pacing; not batch wall time. Cache replay actual requests zero.')
    for token in ['prompt_tokens','completion_tokens','total_tokens']:
        values=[(r['usage'] or {}).get(token) for r in costs];summary[token]=sum(values) if all(isinstance(x,(int,float)) for x in values) else None
        summary[token+'_available_outcomes']=sum(isinstance(x,(int,float)) for x in values)
    (folder/'collection_costs.json').write_text(json.dumps(dict(summary=summary,outcomes=costs),indent=2)+'\n');return summary

if __name__=='__main__':print(json.dumps(audit(),indent=2))
