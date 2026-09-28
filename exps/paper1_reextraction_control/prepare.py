"""Freeze 240 request specifications without executing any request."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_reextraction_control.protocol import ARMS,MODEL,task
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'exps/paper1_receipt_followup/test'

def read(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare():
    rows=read(SOURCE/'inputs.jsonl');graphs={r['case_id']:r['triples'] for r in read(SOURCE/'extraction.jsonl')}
    assert len(rows)==len(graphs)==60 and {r['case_id'] for r in rows}==set(graphs)
    tasks=[task(r,graphs[r['case_id']],a) for r in sorted(rows,key=lambda r:r['case_id']) for a in ARMS]
    serialized=''.join(json.dumps(t,ensure_ascii=False,sort_keys=True)+'\n' for t in tasks)
    deps=[HERE/'protocol.py',HERE/'prepare.py',HERE/'scoring.py',HERE/'test_protocol.py',
          ROOT/'exps/paper1_mechanism_audit/protocol.py',ROOT/'exps/paper1_receipt_followup/protocol.py',
          ROOT/'content_enhancement/source_validation.py',ROOT/'exps/paper1_external_receipts/analyze.py',
          ROOT/'exps/paper1_submission_extensions/analyze_experiments.py',ROOT/'exps/paper1_mechanism_audit/analyze.py']
    manifest={'status':'prepared_only_no_model_responses','scope':'Previously evaluated 60 receipt documents, not a new held-out test.',
        'model':MODEL,'arms':ARMS,'planned_responses':240,'actual_api_calls':0,
        'settings':{'temperature':0,'max_tokens':4000},'primary':'repair_index_gate minus extract_index_gate macro document exact multiset triple F1',
        'secondary':'Other arm contrasts, raw/gate effects, normalized F1, preservation, harm and reported costs; descriptive/exploratory.',
        'statistics':{'unit':'document paired across arms','bootstrap_draws':10000,'two_sided_sign_randomization_draws':10000,'seed':42,'primary_tests':1,'multiplicity':'One primary contrast; secondary contrasts are exploratory.'},
        'cost':'Equal completion cap and one requested outcome per arm. Prompt lengths differ; record actual input/output tokens and all attempts. Initial extraction is an archived shared input, excluded from marginal repair/re-extraction call counts.',
        'failures':'Retain all outcomes including transport/parse failures, scored as empty graphs. No selective reruns. Maximum four transport attempts, two workers, three-second global launch spacing if a separate online runner is later authorized.',
        'mock_policy':'Formal validation refuses mock/synthetic outcome records and requires all 240 unique outcomes.',
        'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [SOURCE/'inputs.jsonl',SOURCE/'extraction.jsonl']},
        'scoring_reference_sha256':sha(SOURCE/'references.jsonl'),
        'code_sha256':{str(p.relative_to(ROOT)):sha(p) for p in deps},
        'requests_sha256':hashlib.sha256(serialized.encode()).hexdigest()}
    manifest=json.loads(json.dumps(manifest))
    p=HERE/'manifest.json'
    if p.exists():
        assert json.loads(p.read_text())==manifest,'Frozen protocol changed; version the study rather than overwrite.'
        assert (HERE/'requests.jsonl').read_text()==serialized
    else:
        (HERE/'requests.jsonl').write_text(serialized)
        p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Prepared 240 requests; executed 0. No response or result file created.')
    return manifest

if __name__=='__main__':prepare()
