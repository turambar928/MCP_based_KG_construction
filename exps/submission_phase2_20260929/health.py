"""Six independent development-only probes, no retries, Gemma only."""
import concurrent.futures
import datetime
import hashlib
import json
import re
import sys
import time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_cuad.protocol import task,parse,MODEL,digest
from exps.paper1_online_recovery.run import pace
HERE=Path(__file__).resolve().parent


def probe(job,credentials):
    label,request=job;key,url=credentials;pace();start=time.perf_counter()
    row=dict(length_group=label,model=MODEL,request_sha256=digest(request),actual_requests=1,
             started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),usage=None)
    try:
        with httpx.Client(trust_env=False,timeout=httpx.Timeout(150,connect=15)) as client:
            response=client.post(url+'/chat/completions',headers={'Authorization':'Bearer '+key},json=request)
        row['http_status']=response.status_code
        if response.status_code==200:
            body=response.json();row['returned_model']=body.get('model');row['usage']=body.get('usage')
            row['raw_response']=body['choices'][0]['message'].get('content') or ''
            _,row['parse_status']=parse(row['raw_response'],'health-only')
            row['passed']=row['returned_model']==MODEL and row['parse_status']=='ok'
        else:row['passed']=False
    except Exception as e:row.update(passed=False,error_type=type(e).__name__)
    row['seconds']=time.perf_counter()-start
    return row


def main():
    if (HERE/'health_results.json').exists():raise RuntimeError('Health probe already recorded')
    docs=sorted([json.loads(l) for l in (ROOT/'exps/paper1_cuad/dev_public.jsonl').read_text().splitlines()],key=lambda d:len(d['source']))
    jobs=[]
    for label,i in [('short',0),('medium',len(docs)//2),('long',len(docs)-1)]:
        for repeat in range(2):jobs.append((label,task(docs[i],'initial')['request']))
    config=(ROOT/'apis').read_text();key=re.search(r'sk-[A-Za-z0-9_-]+',config).group()
    url=re.search(r'https?://[^\s\x27\x22<>]+',config).group().rstrip('/');credentials=(key,url if url.endswith('/v1') else url+'/v1')
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        for off in range(0,6,2):
            for future in concurrent.futures.as_completed([pool.submit(probe,j,credentials) for j in jobs[off:off+2]]):
                row=future.result();rows.append(row);print(row['length_group'],row['passed'],row.get('http_status'),flush=True)
                (HERE/'health_partial.json').write_text(json.dumps(rows,indent=2)+'\n')
    result=dict(probe_only=True,experimental_results=False,probes=rows,all_passed=all(r['passed'] for r in rows),
                source_lengths={label:len(docs[i]['source']) for label,i in [('short',0),('medium',len(docs)//2),('long',len(docs)-1)]})
    (HERE/'health_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('eligible_to_resume',result['all_passed'],flush=True)


if __name__=='__main__':main()
