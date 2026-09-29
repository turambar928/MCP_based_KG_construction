"""Materialize source-grouped DocRED data; never infer types from names."""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE=ROOT/'exps/submission_week_20260929/sources'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def write_once(path, value):
    text=json.dumps(value,indent=2,ensure_ascii=False)+'\n'
    if path.exists():assert path.read_text()==text,'Frozen file differs: '+str(path)
    else:path.write_text(text)


def prepare():
    source=SOURCE/'docred_train_annotated.json.gz'
    docs=json.loads(gzip.decompress(source.read_bytes()))
    relations=json.loads(gzip.decompress((SOURCE/'docred_rel_info.json.gz').read_bytes()))
    eligible=[];excluded=[];seen_titles=set();seen_sources=set()
    for d in sorted(docs,key=lambda d:d['title']):
        fingerprint=digest(d['sents'])
        reasons=[]
        if d['title'].casefold() in seen_titles or fingerprint in seen_sources:reasons.append('duplicate_source_or_title')
        seen_titles.add(d['title'].casefold());seen_sources.add(fingerprint)
        entities=[]
        for i,mentions in enumerate(d['vertexSet']):
            types={m['type'] for m in mentions}
            if len(types)!=1 or not mentions:reasons.append('conflicting_or_missing_type');continue
            for m in mentions:
                sid=m['sent_id'];start,end=m['pos']
                if not 0<=sid<len(d['sents']) or not 0<=start<end<=len(d['sents'][sid]):reasons.append('invalid_mention_offsets')
            entities.append(dict(entity_id=str(i),type=next(iter(types)),mentions=mentions))
        if reasons:excluded.append(dict(title=d['title'],reasons=sorted(set(reasons))));continue
        public=dict(case_id='docred-'+fingerprint[:16],title=d['title'],sents=d['sents'],entities=entities)
        gold=dict(case_id=public['case_id'],labels=d['labels'])
        eligible.append((public,gold))
    eligible.sort(key=lambda x:hashlib.sha256(('20260928:'+x[0]['case_id']).encode()).hexdigest())
    assert len(eligible)>=300
    membership={};counts={};episode_manifest={}
    for split,start,end in [('train',0,180),('dev',180,240),('test',240,300)]:
        selected=eligible[start:end]
        # Keep source content and scorer labels local until redistribution terms
        # beyond the dataset card's MIT tag have been resolved.
        local=HERE/'local';local.mkdir(exist_ok=True)
        for suffix,idx in [('public',0),('scorer_only',1)]:
            write_once(local/(split+'_'+suffix+'.json'),[r[idx] for r in selected])
        for public,gold in selected:
            membership[public['case_id']]=dict(split=split,title=public['title'],public_sha256=digest(public),reference_sha256=digest(gold))
        counts[split]=dict(documents=len(selected),entities=sum(len(r[0]['entities']) for r in selected),
                           annotated_relations=sum(len(r[1]['labels']) for r in selected),
                           types=dict(Counter(e['type'] for r,g in selected for e in r['entities'])))
        ids=sorted([r[0]['case_id'] for r in selected],key=lambda x:hashlib.sha256(x.encode()).hexdigest())
        episode_manifest[split]=[ids[i:i+2] for i in range(0,len(ids),2)]
    write_once(HERE/'relations.json',relations)
    write_once(HERE/'membership.json',membership)
    write_once(HERE/'episodes.json',episode_manifest)
    write_once(HERE/'exclusions.json',excluded)
    report=dict(source_dataset='DocRED original train_annotated only; new experimental splits, not official test',
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),total=len(docs),eligible=len(eligible),
                selected=counts,relation_count=len(relations),source_disjoint=True,types='given human-annotated mention types',
                licensing='Dataset card metadata says MIT; licensing prose says More Information Needed. Downloaded source and generated source copies remain local; no claim that repository MIT covers underlying Wikipedia text.',
                human_verification='Deferred by user; no independent semantic approval yet')
    write_once(HERE/'data_manifest.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':prepare()
