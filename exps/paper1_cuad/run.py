"""Resumable Gemma-only collection; references never loaded by this module."""
import argparse
import concurrent.futures
import json
import os
import random
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from exps.paper1_cuad.protocol import task, parse, digest
from exps.paper1_online_recovery.run import execute, sha
HERE=Path(__file__).resolve().parent


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def freeze():
    files=[HERE/p for p in ('protocol.py','run.py','prepare.py','test_protocol.py','study.json',
                            'dev_public.jsonl','test_public.jsonl','data_manifest.json')]
    files.append(ROOT/'exps/paper1_online_recovery/run.py')
    manifest={str(p.relative_to(ROOT)):sha(p) for p in files}
    path=HERE/'implementation_manifest.json'
    if path.exists():
        assert json.loads(path.read_text())==manifest,'Frozen code/data changed; create another version'
    else:path.write_text(json.dumps(manifest,indent=2)+'\n')


def run(split):
    freeze()
    if split=='test':
        dev=read(HERE/'dev_responses.jsonl')
        assert len(dev)==4*len(read(HERE/'dev_public.jsonl')),'Complete development collection first'
        assert (HERE/'development_decision.json').exists(),'Record development go/no-go before test'
        assert json.loads((HERE/'development_decision.json').read_text())['proceed_to_test']
    rows=read(HERE/(split+'_public.jsonl'));dest=HERE/(split+'_responses.jsonl')
    done=read(dest);seen={(r['case_id'],r['arm']):r for r in done}
    assert len(seen)==len(done),'Duplicate checkpoint outcomes'
    text=(ROOT/'apis').read_text()
    secret=re.search(r'sk-[A-Za-z0-9_-]+',text).group()
    url=re.search(r'https?://[^\s\x27\x22<>]+',text).group().rstrip('/')
    credentials=(secret,url if url.endswith('/v1') else url+'/v1')
    for arms in [('initial',),('repair_simple','repair_index','extract_index')]:
        tasks=[]
        for row in rows:
            for arm in arms:
                initial=None if arm=='initial' else seen[(row['case_id'],'initial')]['triples']
                t=task(row,arm,initial)
                prior=seen.get((row['case_id'],arm))
                if prior:
                    assert prior['request_sha256']==digest(t['request'])
                else:tasks.append(t)
        random.Random(20260929).shuffle(tasks)
        with concurrent.futures.ThreadPoolExecutor(2) as pool, dest.open('a') as output, (HERE/(split+'_requests.jsonl')).open('a') as requests:
            for off in range(0,len(tasks),2):
                wave=tasks[off:off+2]
                for t in wave:requests.write(json.dumps(t,ensure_ascii=False)+'\n')
                requests.flush();os.fsync(requests.fileno())
                futures=[pool.submit(execute,t,'reextraction',credentials) for t in wave]
                failed=0
                for future in concurrent.futures.as_completed(futures):
                    r=future.result()
                    if r['status']!='transport_error':r['triples'],r['status']=parse(r['raw_response'],r['case_id'])
                    failed+=r['status']=='transport_error'
                    output.write(json.dumps(r,ensure_ascii=False)+'\n');output.flush();os.fsync(output.fileno())
                    seen[(r['case_id'],r['arm'])]=r
                    print(split,len(seen),'/',4*len(rows),r['arm'],r['status'],flush=True)
                if failed==len(wave):
                    raise RuntimeError('All requests in wave failed transport; checkpoints retained, stop batch')
    print('COMPLETE',split,len(seen),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('split',choices=['dev','test']);p.add_argument('--freeze-only',action='store_true');a=p.parse_args()
    freeze() if a.freeze_only else run(a.split)
