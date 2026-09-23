"""Freeze disjoint development/test documents; keep test labels unopened until scoring."""
import argparse,concurrent.futures,hashlib,json,random,sys,time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_external_receipts.prepare import REVISION,BASE,RELATIONS
HERE=Path(__file__).resolve().parent
OLD=ROOT/'exps/paper1_external_receipts'

def fetch(path):
    target=HERE/'upstream'/path
    if not target.exists():
        for attempt in range(3):
            try:
                r=requests.get(BASE+path,timeout=40);r.raise_for_status()
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(r.content);break
            except requests.RequestException:
                if attempt==2:raise
                time.sleep(2)
    return path,hashlib.sha256(target.read_bytes()).hexdigest()

def frozen_write(path,text):
    if path.exists() and path.read_text()!=text:raise RuntimeError('Frozen file differs: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)

def jsonl(path,rows):frozen_write(path,''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--test-references',action='store_true');args=parser.parse_args()
    old=json.loads((OLD/'data_manifest.json').read_text())['sample_ids']
    available=[i for i in range(626) if f'sroie-{i:03d}' not in old]
    picked=random.Random(20260923).sample(available,80)
    groups={'dev':sorted(picked[:20]),'test':sorted(picked[20:])}
    if args.test_references:
        lock=HERE/'test_lock.json'
        assert lock.exists(), 'Freeze the method before opening test references'
        predictions=HERE/'test/repairs.jsonl'
        assert predictions.exists() and len(predictions.read_text().splitlines())==180,'Score only after all test repairs'
        group_names=['test'];paths=[f'data/key/{i:03d}.json' for i in groups['test']]
    else:
        group_names=['dev'];paths=[f'data/box/{i:03d}.csv' for i in picked]+[f'data/key/{i:03d}.json' for i in groups['dev']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:hashes=dict(pool.map(fetch,paths))
    for split,ids in groups.items():
        if args.test_references:break
        records=[]
        for i in ids:
            lines=(HERE/f'upstream/data/box/{i:03d}.csv').read_text().splitlines()
            spans=[line.split(',',8)[8].strip() for line in lines if line.strip()]
            cid=f'sroie-{i:03d}'
            records.append({'case_id':cid,'domain':'receipt','source_evidence':' '.join(spans),
                            'source_lines':spans,'required_document_node':cid,'allowed_relations':RELATIONS})
        jsonl(HERE/split/'inputs.jsonl',records)
    for split in group_names:
        refs=[]
        for i in groups[split]:
            d=json.loads((HERE/f'upstream/data/key/{i:03d}.json').read_text());cid=f'sroie-{i:03d}'
            refs.append({'case_id':cid,'annotated_relations':list(d),'triples':[{'head':cid,'relation':k,'tail':d[k]} for k in RELATIONS if k in d]})
        jsonl(HERE/split/'references.jsonl',refs)
    manifest={'revision':REVISION,'seed':20260923,'population':626,'prior_sample_excluded':old,
              'dev':[f'sroie-{i:03d}' for i in groups['dev']], 'test':[f'sroie-{i:03d}' for i in groups['test']],
              'selection':'Uniform draw from unused document IDs before inference; first 20 dev, next 60 test; no outcome filtering',
              'sha256':hashes}
    frozen_write(HERE/('test_reference_manifest.json' if args.test_references else 'split_manifest.json'),json.dumps(manifest,indent=2)+'\n')
    print('Prepared', 'test reference labels after prediction freeze' if args.test_references else '20 dev / 60 test inputs; test labels not downloaded',flush=True)
if __name__=='__main__':main()
