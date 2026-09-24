"""Matched ablation prompts; references never enter this module."""
import copy,hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_mechanism_audit.protocol import SYSTEM,preprocess,diagnosis,PublicInput,key
from exps.paper1_receipt_followup.protocol import make_prompt as receipt_prompt
MODEL='google/gemma-4-26B-A4B-it'
SEED=20260924
FACTORIAL_ARMS=['p0d0','p0d1','p1d0','p1d1']
INDEX_ARMS=['simple','full','anchors','random','no_def_simple','no_def_full']

def factorial_prompt(inp,arm):
    assert arm in FACTORIAL_ARMS
    p,d=int(arm[1]),int(arm[3])
    structural=preprocess(inp) if p else [dict(t) for t in inp.triples]
    payload={**inp.payload(),'input_triples':structural}
    if d:payload['diagnostic_context']=diagnosis(inp,structural)
    return SYSTEM,json.dumps(payload,ensure_ascii=False,sort_keys=True)

def random_index(index,lines,cid):
    """Fixed random placebo: match fieldwise anchor counts and approximate text length.

    Choose among 128 draws by total anchor-text character length only. The
    selection never consults patterns, field values, references, or outcomes.
    Overlap with actual anchors is permitted and logged, not selected against.
    """
    result={}
    for field,data in index.items():
        rng=random.Random(int(hashlib.sha256(f'{SEED}:{cid}:{field}'.encode()).hexdigest(),16))
        k=len(data['anchor_lines']);target=sum(len(a['text']) for a in data['anchors'])
        candidates=[sorted(rng.sample(range(len(lines)),k)) for _ in range(128)]
        hits=min(candidates,key=lambda hs:abs(sum(len(lines[i]) for i in hs)-target))
        count=len(data['nearby_lines']);near=set(hits)
        near.update(rng.sample([i for i in range(len(lines)) if i not in near],count-len(near)))
        result[field]={'anchor_lines':[i+1 for i in hits],'nearby_lines':[i+1 for i in sorted(near)],
                       'anchors':[{'line':i+1,'text':lines[i]} for i in hits]}
    return result

def index_prompt(row,triples,arm):
    assert arm in INDEX_ARMS
    indexed=arm not in ['simple','no_def_simple']
    _,system,user=receipt_prompt(row,triples,'evidence' if indexed else 'simple')
    payload=json.loads(user)
    if arm.startswith('no_def_'):payload.pop('field_definitions')
    if arm=='anchors':
        for v in payload['field_evidence_index'].values():v['nearby_lines']=list(v['anchor_lines'])
    elif arm=='random':payload['field_evidence_index']=random_index(payload['field_evidence_index'],row['source_lines'],row['case_id'])
    return system,json.dumps(payload,ensure_ascii=False,sort_keys=True)

CHECKS=('duplicate','head','relation','support','cardinality')
def filter_candidates(inp,candidates,disabled=(),whitespace=False):
    """Leave-one-check-out filter, preserving scan order and other checks."""
    active=set(CHECKS)-set(disabled);seen=set();used=set();out=[];rejected=[]
    norm=(lambda x:' '.join(x.split())) if whitespace else (lambda x:x)
    source=norm(inp.source_evidence)
    for raw in candidates:
        t=dict(raw);k=key(t);value=norm(t['tail']);reason=None
        if 'duplicate' in active and k in seen:reason='duplicate'
        elif 'head' in active and t['head']!=inp.required_document_node:reason='head'
        elif 'relation' in active and t['relation'] not in inp.allowed_relations:reason='relation'
        elif 'support' in active and (not value or value not in source):reason='support'
        elif 'cardinality' in active and t['relation'] in used:reason='cardinality'
        if reason:rejected.append({'triple':t,'reason':reason})
        else:out.append(t);used.add(t['relation'])
        seen.add(k)
    return out,rejected
