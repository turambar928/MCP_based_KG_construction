#!/usr/bin/env python3
"""Locked Gemma-only protocol: same prompt instructions, budget and inputs.

All outcomes including parse/HTTP errors are final once checkpointed. Resume
never selectively reruns failures. API keys and exception messages are not saved.
"""
from __future__ import annotations
import argparse,json,re,sys,time,hashlib,random,threading
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import *
from exps.paper1_repair_benchmark.run_benchmark import parse_triples


PACE_LOCK=threading.Lock()
NEXT_REQUEST=0.0
def pace(delay=0.0):
    global NEXT_REQUEST
    with PACE_LOCK:
        now=time.monotonic()
        NEXT_REQUEST=max(NEXT_REQUEST,now+delay)
        wait=max(0,NEXT_REQUEST-now)
        NEXT_REQUEST+=4.0
    if wait:time.sleep(wait)

def config():
    text=(ROOT/'api').read_text()
    key=re.search(r'sk-[A-Za-z0-9_-]+',text).group()
    url=re.search(r'https?://[^\s]+',text).group().rstrip('/')
    return key,url if url.endswith('/v1') else url+'/v1'


def execute(task,credentials):
    stream,arm,inp,sysmsg,user=task
    payload={'model':MODEL,'temperature':0,'max_tokens':4000,
             'messages':[{'role':'system','content':sysmsg},{'role':'user','content':user}]}
    key,url=credentials
    started=time.perf_counter();attempts=[];raw='';status='not_run';usage={};finish=None
    # At most four attempts on transport/5xx/429 errors; parse failures are retained.
    with httpx.Client(trust_env=False,timeout=httpx.Timeout(150,connect=15)) as client:
        for attempt in range(4):
            pace()
            t=time.perf_counter()
            try:
                response=client.post(url+'/chat/completions',headers={'Authorization':'Bearer '+key},json=payload)
                attempts.append({'http_status':response.status_code,'seconds':time.perf_counter()-t})
                if response.status_code==200:
                    body=response.json();raw=body['choices'][0]['message'].get('content') or ''
                    usage=body.get('usage',{});finish=body['choices'][0].get('finish_reason')
                    triples,status=parse_triples(raw);break
                status='http_'+str(response.status_code)
                if response.status_code not in [429,500,502,503,504]: break
            except Exception as exc:
                status=type(exc).__name__;attempts.append({'error_type':status,'seconds':time.perf_counter()-t})
            if attempt<3:
                if status=='http_429':pace(45)
                else:time.sleep(5)
        else: triples=[]
    if status!='ok':triples=[]
    return {'case_id':inp.case_id,'domain':inp.domain,'stream':stream,'arm':arm,'model':MODEL,
            'status':status,'triples':triples,'raw_response':raw,'usage':usage,'finish_reason':finish,
            'attempts':attempts,'calls':len(attempts),'wall_seconds':time.perf_counter()-started,
            'request_sha256':digest(payload),'input_sha256':digest(inp.payload())}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--limit',type=int,default=0)
    args=parser.parse_args()
    assert MODEL=='google/gemma-4-26B-A4B-it'  # no GPT/Claude calls permitted
    cases=sorted([c for c in read_jsonl(BENCH/'benchmark.jsonl') if c['split']=='test'],key=lambda c:c['case_id'])
    frozen_ids={r['case_id'] for r in read_jsonl(EXT/'cross_model_gemma_full.jsonl')}
    assert len(frozen_ids)==60
    cases=[c for c in cases if c['case_id'] in frozen_ids]
    if args.limit:cases=cases[:args.limit]
    extract={r['case_id']:r for r in read_jsonl(EXT/'natural_extraction_claude.jsonl')}
    tasks=[(stream,arm,public_input(c,c['corrupted_triples'] if stream=='controlled' else extract[c['case_id']]['triples']))
           for c in cases for stream in ['controlled','natural'] for arm in ['base','diagnosis','shacl_context']]
    random.Random(20260921).shuffle(tasks)
    manifest={'model':MODEL,'temperature':0,'max_tokens':4000,'case_ids':[c['case_id'] for c in cases],
              'arms':['base','diagnosis','shacl_context'],'streams':['controlled','natural'],
              'seed':20260921,'max_attempts':4,'failures_retained':True,'global_request_spacing_seconds':4,
              'subset':'same pre-existing 60-case cross-model subset (20/domain); selected without outcome screening',
              'natural_inputs':'archived Claude extraction; no new Claude calls',
              'protocol_sha256':hashlib.sha256((HERE/'protocol.py').read_bytes()).hexdigest()}
    dest=HERE/('pilot' if args.limit else 'run');dest.mkdir(exist_ok=True)
    mp=dest/'manifest.json'
    if mp.exists(): assert json.loads(mp.read_text())==manifest,'Protocol changed; use a new run directory'
    else:mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    out=dest/'predictions.jsonl'
    existing={(r['stream'],r['arm'],r['case_id']) for r in read_jsonl(out)}
    pending=[t for t in tasks if (t[0],t[1],t[2].case_id) not in existing]
    print('tasks',len(tasks),'pending',len(pending),'model',MODEL,flush=True)
    if not pending:return
    prepared=[]
    for index,(stream,arm,inp) in enumerate(pending,1):
        sysmsg,user=make_prompt(inp,arm)
        prepared.append((stream,arm,inp,sysmsg,user))
        if index%150==0: print('prepared',index,flush=True)
    credentials=config()
    with ThreadPoolExecutor(max_workers=args.workers) as pool,out.open('a') as handle:
        futures=[pool.submit(execute,t,credentials) for t in prepared]
        for i,f in enumerate(as_completed(futures),1):
            row=f.result();handle.write(json.dumps(row,ensure_ascii=False)+'\n');handle.flush()
            if i%15==0 or row['status']!='ok' or i==len(pending):
                print(i,'/',len(pending),row['stream'],row['arm'],row['status'],flush=True)

if __name__=='__main__':main()
