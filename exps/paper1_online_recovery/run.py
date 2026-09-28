"""Authorized Gemma-only execution of frozen studies, with separate recovery outputs."""
import argparse,concurrent.futures,datetime,hashlib,json,os,random,re,sys,threading,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
HERE=Path(__file__).resolve().parent
MODEL='google/gemma-4-26B-A4B-it'
LOCK=threading.Lock();NEXT=0.
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()] if Path(p).exists() else []
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def pace(cooldown=0):
 global NEXT
 with LOCK:
  t=time.monotonic();NEXT=max(t+cooldown,NEXT);delay=NEXT-t;NEXT+=3
 time.sleep(max(0,delay))
def payload(task,study):
 if study=='reextraction':p=task['request']
 else:p={'model':MODEL,'temperature':0,'max_tokens':4000,'messages':[{'role':'system','content':task['system']},{'role':'user','content':task['user']}]}
 if p['model']!=MODEL:raise ValueError('Only frozen Gemma model is allowed')
 return p
def strict_parse(raw):
 try:
  triples=json.loads(raw)['triples']
  if not isinstance(triples,list) or not all(isinstance(t,dict) and all(isinstance(t.get(k),str) for k in ['head','relation','tail']) for t in triples):raise ValueError()
  return triples,'ok'
 except (ValueError,TypeError,KeyError):return [],'parse_error'
def execute(task,study,credentials):
 from exps.paper1_mechanism_audit.protocol import digest
 from exps.paper1_repair_benchmark.run_benchmark import parse_triples
 p=payload(task,study);secret,url=credentials;beg=time.perf_counter();attempts=[];raw='';triples=[];status='transport_error';usage={k:None for k in ['prompt_tokens','completion_tokens','total_tokens']};finish=None;returned=None
 with httpx.Client(trust_env=False,timeout=httpx.Timeout(150,connect=15)) as client:
  for i in range(4):
   pace();t=time.perf_counter();attempt={'started_utc':now()}
   retry=False
   try:
    response=client.post(url+'/chat/completions',headers={'Authorization':'Bearer '+secret},json=p)
    attempt['http_status']=response.status_code
    if response.status_code==200:
     body=response.json();returned=body.get('model');choice=body['choices'][0];raw=choice.get('message',{}).get('content') or '';finish=choice.get('finish_reason');usage=body.get('usage') or usage
     attempt['returned_model']=returned
     if returned!=MODEL:status='transport_error';attempt['error_type']='ModelIdentityMismatch';raw=''
     else:triples,status=strict_parse(raw) if study=='reextraction' else parse_triples(raw)
    else:retry=response.status_code in [429,500,502,503,504]
   except Exception as e:attempt['error_type']=type(e).__name__;retry=True
   attempt['seconds']=time.perf_counter()-t;attempts.append(attempt)
   if not retry:break
   if i<3:pace(30 if attempt.get('http_status')==429 else 5)
 if status!='ok':triples=[]
 row={'case_id':task['case_id'],'arm':task['arm'],'model':MODEL,'status':status,'triples':triples,'raw_response':raw,'usage':usage,'finish_reason':finish,'returned_model':returned,'attempts':attempts,'calls':len(attempts),'wall_seconds':time.perf_counter()-beg,'request_sha256':digest(p)}
 if study=='reextraction':row.update(kind='model_response',is_mock=False,prompt_sha256=task['prompt_sha256'])
 else:row['cohort']=task['cohort']
 return row

def identify(row,study):return (row['case_id'],row['arm']) if study=='reextraction' else (row['cohort'],row['case_id'],row['arm'])
def freeze(study):
 dest=HERE/study;dest.mkdir(exist_ok=True)
 if study=='reextraction':
  from exps.paper1_reextraction_control.prepare import prepare
  prepare();source=ROOT/'exps/paper1_reextraction_control';tasks=read(source/'requests.jsonl');expected=240
 else:
  from exps.paper1_ablation_completion.run import verify
  verify();source=ROOT/'exps/paper1_ablation_completion';tasks=read(source/'prompts.jsonl');expected=840
  assert all(r['status']!='ok' for r in read(source/'predictions.jsonl'))
 assert len(tasks)==expected and len({identify(t,study) for t in tasks})==expected
 for task in tasks:payload(task,study)
 deps=[source/'manifest.json',source/('requests.jsonl' if study=='reextraction' else 'prompts.jsonl'),Path(__file__),HERE/'test_runner.py']
 if study=='ablation':deps += [source/'inputs.jsonl',source/'predictions.jsonl']
 manifest={'study':study,'model':MODEL,'expected_outcomes':expected,'workers':2,'spacing_seconds':3,'max_attempts':4,'read_timeout_seconds':150,'connect_timeout_seconds':15,'seed':20260928,'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in deps},'amendment':'Service recovered after confirmed outage. Full contemporaneous new batch; old failed batch retained unchanged. Frozen prompts, parser and statistical plan retained. Missing usage stays null. No response is rerun after checkpointing.','study_scope':'Existing evaluated documents; not an untouched held-out study.','authorization':'User requested execution of papers_next_steps_2026-09-28.md on 2026-09-28.'}
 m=dest/'manifest.json'
 if m.exists():assert json.loads(m.read_text())==manifest,'Recovery dependencies changed; use a new version'
 else:m.write_text(json.dumps(manifest,indent=2)+'\n')
 return dest,tasks

def run(study):
 dest,tasks=freeze(study);done=read(dest/'predictions.jsonl');seen={identify(r,study) for r in done};assert len(seen)==len(done)
 expected={identify(t,study):t for t in tasks};assert seen<=set(expected)
 if study=='reextraction':
  from exps.paper1_reextraction_control.scoring import validate_outcome
  for r in done:validate_outcome(r,expected)
 tasks=[t for t in tasks if identify(t,study) not in seen];random.Random(20260928).shuffle(tasks)
 if not tasks:print(study,'already complete',flush=True);return
 config=(ROOT/'apis').read_text();secret=re.search(r'sk-[A-Za-z0-9_-]+',config).group();url=re.search(r'https?://[^\s\x27\x22<>]+',config).group().rstrip('/');url=url if url.endswith('/v1') else url+'/v1'
 print(study,'pending',len(tasks),'model',MODEL,flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool,(dest/'predictions.jsonl').open('a') as f:
  # Bounded waves keep the process resumable and prevent an unbounded request queue.
  for off in range(0,len(tasks),2):
   futures=[pool.submit(execute,t,study,(secret,url)) for t in tasks[off:off+2]]
   for fut in concurrent.futures.as_completed(futures):
    r=fut.result()
    if study=='reextraction':validate_outcome(r,expected)
    f.write(json.dumps(r,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno());done.append(r)
    if len(done)%10==0 or r['status']!='ok':print(study,len(done),'/',len(expected),r['status'],flush=True)
 rows=read(dest/'predictions.jsonl');assert len(rows)==len(expected)
 (dest/'completion.json').write_text(json.dumps({'finished_utc':now(),'outcomes':len(rows),'actual_requests':sum(r['calls'] for r in rows),'status':{s:sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})}},indent=2)+'\n')
 print(study,'COMPLETE',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('study',choices=['reextraction','ablation']);p.add_argument('--freeze-only',action='store_true');a=p.parse_args()
 freeze(a.study) if a.freeze_only else run(a.study)
