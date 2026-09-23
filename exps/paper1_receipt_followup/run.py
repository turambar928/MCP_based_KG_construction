"""Run dev then a hash-locked test, using only Gemma. Save exact request prompts."""
import argparse,hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import MODEL,read_jsonl
from exps.paper1_mechanism_audit.run_api import execute,config
from exps.paper1_external_receipts.run import EXTRACT_SYSTEM,input_object,run_stage
from exps.paper1_receipt_followup.protocol import make_prompt
HERE=Path(__file__).resolve().parent
HASH_FILES=['exps/paper1_receipt_followup/protocol.py','exps/paper1_receipt_followup/run.py',
 'content_enhancement/source_validation.py','exps/paper1_external_receipts/shacl.py',
 'exps/paper1_external_receipts/run.py','exps/paper1_mechanism_audit/run_api.py',
 'exps/paper1_mechanism_audit/protocol.py','exps/paper1_repair_benchmark/run_benchmark.py']

def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in HASH_FILES}

def lock():
    assert (HERE/'dev/results.json').exists(),'Finish and inspect development results first'
    record={'model':MODEL,'temperature':0,'max_tokens':4000,'seed':20260923,'code_sha256':hashes(),
        'test_inputs_sha256':hashlib.sha256((HERE/'test/inputs.jsonl').read_bytes()).hexdigest(),
        'dev_results_sha256':hashlib.sha256((HERE/'dev/results.json').read_bytes()).hexdigest(),
        'arms':['simple','evidence','shacl'],'primary_comparison':'evidence_gate minus simple_gate macro exact triple F1',
        'secondary_comparisons':['simple_gate vs input','evidence_gate vs shacl_gate','same-response filtering'],
        'scope':'same receipt collection, unseen document IDs; 20 dev, 60 test, prior 60 excluded',
        'normalization':'source and candidates share whitespace collapse; preserve case, punctuation, word boundaries',
        'selection':'one evidence-index design evaluated on development data; retain all three test arms regardless of development ordering',
        'test_labels':'not downloaded or read before completing all test predictions',
        'failures_retained':True,'reference_field_omissions':'exclude only missing annotated relations during scoring',
        'statistics':'whole-document bootstrap and two-sided sign randomization, 10000 draws, seed 42; primary comparison predeclared',
        'retried_requests':'at most four transport attempts; 4-second global pacing, two workers'}
    path=HERE/'test_lock.json'
    if path.exists():assert json.loads(path.read_text())==record
    else:path.write_text(json.dumps(record,indent=2)+'\n')
    print('Test protocol locked; no test labels read.',flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['dev','lock','test']);args=p.parse_args()
    assert MODEL=='google/gemma-4-26B-A4B-it'
    if args.stage=='lock':lock();return
    split=args.stage;dest=HERE/split;rows=read_jsonl(dest/'inputs.jsonl');n=20 if split=='dev' else 60
    assert len(rows)==n
    if split=='test':
        fixed=json.loads((HERE/'test_lock.json').read_text())
        assert fixed['code_sha256']==hashes(),'Method changed after freezing'
        assert fixed['test_inputs_sha256']==hashlib.sha256((dest/'inputs.jsonl').read_bytes()).hexdigest()
    manifest={'model':MODEL,'n_documents':n,'code_sha256':hashes(),'input_sha256':hashlib.sha256((dest/'inputs.jsonl').read_bytes()).hexdigest(),
              'max_tokens':4000,'temperature':0,'arms':['simple','evidence','shacl'],'seed':20260923}
    path=dest/'run_manifest.json'
    if path.exists():assert json.loads(path.read_text())==manifest,'Run protocol changed'
    else:path.write_text(json.dumps(manifest,indent=2)+'\n')
    credentials=config();tasks=[]
    for row in rows:
        inp=input_object(row)
        tasks.append((split,'extract',inp,EXTRACT_SYSTEM,json.dumps(inp.payload(),ensure_ascii=False)))
    random.Random(20260923).shuffle(tasks)
    run_stage(tasks,dest/'extraction.jsonl',credentials)
    start={r['case_id']:r for r in read_jsonl(dest/'extraction.jsonl')};assert len(start)==n
    prompt_file=dest/'repair_prompts.jsonl'
    if prompt_file.exists():
        saved=read_jsonl(prompt_file);lookup={r['case_id']:r for r in rows}
        tasks=[(split,x['arm'],input_object(lookup[x['case_id']],start[x['case_id']]['triples']),x['system'],x['user']) for x in saved]
    else:
        tasks=[];saved=[]
        for row in rows:
            for arm in ['simple','evidence','shacl']:
                inp,system,user=make_prompt(row,start[row['case_id']]['triples'],arm)
                # Hashing/storage uses the original public input; prompt normalization is explicit.
                original=input_object(row,start[row['case_id']]['triples'])
                tasks.append((split,arm,original,system,user))
                saved.append({'case_id':row['case_id'],'arm':arm,'system':system,'user':user})
        prompt_file.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in saved))
    random.Random(20260923).shuffle(tasks)
    run_stage(tasks,dest/'repairs.jsonl',credentials)
    print(split,'complete:',n,'extractions and',n*3,'repairs',flush=True)
if __name__=='__main__':main()
