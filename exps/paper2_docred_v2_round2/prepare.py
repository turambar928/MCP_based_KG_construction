"""Reference-only controlled construction, separate from runtime generation/scoring."""
import json,random,math
from pathlib import Path
from exps.paper2_docred.prepare import digest,write_once
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'paper2_docred'


def prepare(split='dev',pilot=True):
    pairs=json.loads((OLD/'episodes.json').read_text())[split]
    if pilot:pairs=pairs[:10]
    docs={d['case_id']:d for d in json.loads((OLD/'local'/f'{split}_public.json').read_text())}
    refs={d['case_id']:d for d in json.loads((OLD/'local'/f'{split}_scorer_only.json').read_text())}
    relations=json.loads((OLD/'relations.json').read_text());inputs=[];score=[]
    for pair in pairs:
        for idx,cid in enumerate(pair):
            doc=docs[cid];types={e['entity_id']:e['type'] for e in doc['entities']}
            gold=sorted({(str(t['h']),t['r'],str(t['t'])) for t in refs[cid]['labels']})
            triples=set(gold);injected=[];rng=random.Random('v2:'+cid)
            # Add substitutions rather than replace references: known retention denominator.
            if idx==1 and gold:
                target=max(1,math.ceil(.2*len(gold)));tries=0
                while len(injected)<target and tries<target*100:
                    tries+=1;h,r,t=rng.choice(gold)
                    if tries%2:r=rng.choice(sorted(relations))
                    else:t=rng.choice(sorted(types))
                    candidate=(h,r,t)
                    if h==t or candidate in triples:continue
                    triples.add(candidate);injected.append(candidate)
                if len(injected)!=target:raise ValueError('Cannot construct fixed corruption count')
            records=[dict(record_id=cid+':'+digest(t)[:16],subject_type=types[t[0]],relation=t[1],object_type=types[t[2]],source_document_id=cid,head_entity_id=t[0],tail_entity_id=t[2]) for t in sorted(triples)]
            inputs.append(dict(document=doc,records=records))
            score.append(dict(case_id=cid,condition='perturbed' if idx else 'clean',reference=[list(t) for t in gold],injected=[list(t) for t in injected]))
    local=HERE/'local';local.mkdir(exist_ok=True)
    prefix='pilot' if pilot else split
    write_once(local/(prefix+'_public.json'),inputs);write_once(local/(prefix+'_scorer_only.json'),score)
    write_once(HERE/(prefix+'_membership.json'),dict(pairs=pairs,public_sha256=digest(inputs),reference_sha256=digest(score),construction='Equal clean/perturbed; add ceil(20% reference size) endpoint/relation substitutions. Not natural error truth.'))
    return inputs,pairs

if __name__=='__main__':prepare()
