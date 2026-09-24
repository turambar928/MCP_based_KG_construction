"""Freeze all prompts, then run a Gemma-only contemporaneous matched study."""
import argparse,concurrent.futures,hashlib,json,random,re,sys,threading,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_ablation_completion.protocol import *
from exps.paper1_mechanism_audit.protocol import read_jsonl,public_input,digest
from exps.paper1_external_receipts.run import input_object
from exps.paper1_repair_benchmark.run_benchmark import parse_triples
HERE=Path(__file__).resolve().parent
FILES=['exps/paper1_ablation_completion/'+p for p in ['protocol.py','run.py','analyze.py','offline.py','test_protocol.py']]+[
'exps/paper1_mechanism_audit/protocol.py','exps/paper1_mechanism_audit/replay_optimizer.py',
'exps/paper1_receipt_followup/protocol.py','exps/paper1_external_receipts/analyze.py',
'exps/paper1_repair_benchmark/run_benchmark.py','exps/paper1_repair_benchmark/analyze_results.py',
'exps/paper1_submission_extensions/analyze_experiments.py','content_enhancement/constraint_optimizer.py',
'content_enhancement/source_validation.py','exps/paper1_external_receipts/run.py',
'exps/paper1_mechanism_audit/analyze.py','exps/decision_network/fphi_model.npz','exps/decision_network/scaler.json']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def hashes():return {p:sha(ROOT/p) for p in FILES}
def freeze():
    tasks=[];inputs=[]
    old=json.loads((ROOT/'exps/paper1_mechanism_audit/run/manifest.json').read_text())
    ids=set(old['case_ids'])
    cases={r['case_id']:r for r in read_jsonl(ROOT/'exps/paper1_repair_benchmark/benchmark.jsonl') if r['case_id'] in ids}
    extraction={r['case_id']:r for r in read_jsonl(ROOT/'exps/paper1_submission_extensions/natural_extraction_claude.jsonl')}
    for cohort in ['controlled','natural']:
        for cid in sorted(ids):
            c=cases[cid];inp=public_input(c,c['corrupted_triples'] if cohort=='controlled' else extraction[cid]['triples'])
            inputs.append({'cohort':cohort,'case_id':cid,'domain':inp.domain,**inp.payload()})
            for arm in FACTORIAL_ARMS:
                system,user=factorial_prompt(inp,arm)
                tasks.append({'cohort':cohort,'case_id':cid,'arm':arm,'system':system,'user':user})
    receipts=ROOT/'exps/paper1_receipt_followup/test'
    extraction={r['case_id']:r for r in read_jsonl(receipts/'extraction.jsonl')}
    for row in read_jsonl(receipts/'inputs.jsonl'):
        inp=input_object(row,extraction[row['case_id']]['triples'])
        inputs.append({'cohort':'receipt','case_id':inp.case_id,'domain':inp.domain,**inp.payload()})
        for arm in INDEX_ARMS:
            system,user=index_prompt(row,list(inp.triples),arm)
            tasks.append({'cohort':'receipt','case_id':inp.case_id,'arm':arm,'system':system,'user':user})
    for name,records in [('inputs.jsonl',inputs),('prompts.jsonl',tasks)]:
        p=HERE/name;s=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records)
        if p.exists():assert p.read_text()==s
        else:p.write_text(s)
    source_paths=['exps/paper1_repair_benchmark/benchmark.jsonl','exps/paper1_submission_extensions/natural_extraction_claude.jsonl',
     'exps/paper1_mechanism_audit/run/manifest.json','exps/paper1_receipt_followup/test/inputs.jsonl',
     'exps/paper1_receipt_followup/test/extraction.jsonl','exps/paper1_receipt_followup/test/references.jsonl',
     'exps/paper1_repair_benchmark/predictions_ours.jsonl','exps/paper1_submission_extensions/natural_repairs_full_claude.jsonl']
    manifest={'model':MODEL,'temperature':0,'max_tokens':4000,'seed':SEED,'spacing_seconds':3,'workers':2,'max_attempts':4,
     'code_sha256':hashes(),'source_sha256':{p:sha(ROOT/p) for p in source_paths},'prompts_sha256':sha(HERE/'prompts.jsonl'),
     'inputs_sha256':sha(HERE/'inputs.jsonl'),'expected_requests':len(tasks),
     'cohorts':{'controlled':60,'natural':60,'receipt':60},'factorial_arms':FACTORIAL_ARMS,'index_arms':INDEX_ARMS,
     'primary_metric':'per-document exact multiset triple F1',
     'factorial_effects':'P,D,G main effects averaged over other factors; PD,PG,DG,PDG interactions secondary; separate by input condition',
     'receipt_contrasts':[['full','simple'],['full','random'],['full','anchors'],['full','no_def_full'],['simple','no_def_simple']],
     'statistics':'10000 whole-document bootstrap and two-sided sign randomization, seed 42; Holm across six factorial main effects and separately five receipt comparisons; interactions exploratory',
     'scope':'Follow-up on previously evaluated fixed cases. No new holdout claim. All arms rerun contemporaneously; no selective outcome retries.',
     'random_control':'128 seeded draws selected by anchor text length only; same anchor and nearby counts per field. Approximate, not exact token matching. One fixed realization.',
     'offline':'same-response gate leave-one-out + duplicate/cardinality joint removal; separate fixed-proposal optimizer ablations',
     'credentials':'read local apis; no credentials archived; httpx trust_env=False'}
    p=HERE/'manifest.json'
    if p.exists():assert json.loads(p.read_text())==manifest
    else:
        assert not (HERE/'predictions.jsonl').exists();p.write_text(json.dumps(manifest,indent=2)+'\n')
    print('Frozen',len(tasks),'repair requests; references are scoring-only.',flush=True)

def verify():
    m=json.loads((HERE/'manifest.json').read_text());assert m['code_sha256']==hashes(),'Frozen code changed'
    assert m['prompts_sha256']==sha(HERE/'prompts.jsonl') and m['inputs_sha256']==sha(HERE/'inputs.jsonl')
    for p,h in m['source_sha256'].items():assert sha(ROOT/p)==h,p
    return m
LOCK=threading.Lock();NEXT=0.
def pace(cooldown=0.):
    global NEXT
    with LOCK:
        now=time.monotonic();NEXT=max(NEXT,now+cooldown);delay=NEXT-now;NEXT+=3
    if delay:time.sleep(delay)
def execute(task,credentials):
    assert MODEL=='google/gemma-4-26B-A4B-it'
    payload={'model':MODEL,'temperature':0,'max_tokens':4000,'messages':[{'role':'system','content':task['system']},{'role':'user','content':task['user']}]}
    secret,url=credentials;start=time.perf_counter();attempts=[];raw='';status='not_run';usage={};finish=None;triples=[]
    with httpx.Client(trust_env=False,timeout=httpx.Timeout(150,connect=15)) as client:
        for attempt in range(4):
            pace();sent=time.perf_counter()
            try:
                response=client.post(url+'/chat/completions',headers={'Authorization':'Bearer '+secret},json=payload)
                attempts.append({'http_status':response.status_code,'seconds':time.perf_counter()-sent})
                if response.status_code==200:
                    body=response.json();raw=body['choices'][0]['message'].get('content') or '';usage=body.get('usage',{});finish=body['choices'][0].get('finish_reason')
                    triples,status=parse_triples(raw);break
                status='http_'+str(response.status_code)
                if response.status_code not in [429,500,502,503,504]:break
            except Exception as exc:
                status=type(exc).__name__;attempts.append({'error_type':status,'seconds':time.perf_counter()-sent})
            if attempt<3:pace(30 if status=='http_429' else 5)
    if status!='ok':triples=[]
    return {k:task[k] for k in ['cohort','case_id','arm']}|{'model':MODEL,'status':status,'triples':triples,'raw_response':raw,'usage':usage,'finish_reason':finish,
     'attempts':attempts,'calls':len(attempts),'wall_seconds':time.perf_counter()-start,'request_sha256':digest(payload)}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run']);a=parser.parse_args()
    if a.mode=='freeze':freeze();return
    verify();s=(ROOT/'apis').read_text();keymatch=re.search(r'sk-[A-Za-z0-9_-]+',s);urlmatch=re.search(r'https?://[^\s]+',s)
    assert keymatch and urlmatch,'Missing API configuration'
    url=urlmatch.group().rstrip('/');url=url if url.endswith('/v1') else url+'/v1';credentials=(keymatch.group(),url)
    dest=HERE/'predictions.jsonl';done={(r['cohort'],r['case_id'],r['arm']) for r in read_jsonl(dest)}
    tasks=[t for t in read_jsonl(HERE/'prompts.jsonl') if (t['cohort'],t['case_id'],t['arm']) not in done]
    random.Random(SEED).shuffle(tasks);print('Pending:',len(tasks),'model:',MODEL,flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool,dest.open('a') as f:
        futures=[pool.submit(execute,t,credentials) for t in tasks]
        for n,future in enumerate(concurrent.futures.as_completed(futures),1):
            result=future.result()
            f.write(json.dumps(result,ensure_ascii=False)+'\n');f.flush()
            if n%10==0 or result['status']!='ok':print(len(done)+n,'/ 840',result['cohort'],result['arm'],result['status'],flush=True)
    print('All outcomes retained.',flush=True)
if __name__=='__main__':main()
