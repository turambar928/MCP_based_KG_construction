"""Freeze requests using public development inputs only, before any model call."""
from collections import Counter
from exps.paper2_rule_verification_20261008.common import *
from exps.paper2_rule_verification_20261008.review import make_task

def context():
    public={x['document']['case_id']:x for x in read(STUDY/'local/public.json')}
    packets=read(STUDY/'packets.json')
    pairs=read(STUDY/'membership.json')['pairs']
    relations=read(ROOT/'exps/paper2_docred/relations.json')
    return public,packets,pairs,relations


def freeze():
    public,packets,pairs,relations=context()
    member={c:pair for pair in pairs for c in pair}
    tasks=[]
    for packet in packets:
        if not packet['rules']: continue
        ids=member[packet['source_document_id']]
        tasks.append(make_task(packet,{c:public[c]['document'] for c in ids},
            sum((public[c]['records'] for c in ids),[]),relations))
    assert len(tasks)==38 and sum(len(p['rules']) for p in packets)==407
    # No exact ontology alignment or reviewed hard-schema source is supplied.
    # Property metadata and dataset relation names do not establish disjointness.
    props=read(HERE/'local/wikidata_properties.json').get('entities',{}) if (HERE/'local/wikidata_properties.json').exists() else {}
    type_ids=sorted({r['pattern'][1] for p in packets for r in p['rules'] if r['family']=='type'})
    schema=dict(version=VERSION, hard_mappings=[], approved_rules=0,
        reason='No reviewed total mapping from DocRED coarse classes to hard property domain/range constraints, including exceptions. Property names/descriptions and recommendation constraints are insufficient.',
        dataset_source='https://github.com/thunlp/DocRED', dataset_relation_file_sha256=sha(ROOT/'exps/paper2_docred/relations.json'),
        relations=[dict(property_id=k,label=relations[k],source='https://www.wikidata.org/wiki/Property:'+k,
            metadata_retrieved=k in props,datatype=props.get(k,{}).get('datatype'),
            constraint_statements=len(props.get(k,{}).get('claims',{}).get('P2302',[])),
            docred_type_mapping='unresolved',verdict='uncertain') for k in type_ids])
    write_once(HERE/'schema_audit.json',schema)
    write_once(HERE/'protocol.json',PROTOCOL)
    write_once(HERE/'local/tasks.json',tasks)
    protected={str(p.relative_to(ROOT)):sha(p) for p in HERE.glob('*.py')}
    protocol_doc=ROOT/'paper2/AUTOMATIC_RULE_REVIEW_PROTOCOL_2026-10-08.md'
    protected[str(protocol_doc.relative_to(ROOT))]=sha(protocol_doc)
    for folder in ('paper2_rule_feasibility_20261004','paper2_docred_v2_round2','paper2_rule_admission_20261004'):
        for p in (ROOT/'exps'/folder).glob('*.py'): protected[str(p.relative_to(ROOT))]=sha(p)
    for p in [ROOT/'exps/papers_readiness_20261002/diagnose_loop.py', ROOT/'exps/paper2_rule_admission_20261004/trust_registry.json',
              STUDY/'local/public.json',STUDY/'local/scorer_only.json',STUDY/'packets.json',STUDY/'traces.json',
              STUDY/'membership.json',ROOT/'exps/paper2_docred/relations.json']:
        protected[str(p.relative_to(ROOT))]=sha(p)
    for p in [HERE/'protocol.json',HERE/'schema_audit.json',HERE/'schema_fetch.json',HERE/'schema_fetch_proxy.json',HERE/'local/tasks.json']:
        protected[str(p.relative_to(ROOT))]=sha(p)
    if props: protected[str((HERE/'local/wikidata_properties.json').relative_to(ROOT))]=sha(HERE/'local/wikidata_properties.json')
    write_once(HERE/'manifest.json',dict(version=VERSION,protected_sha256=protected,
        tasks=[dict(task_id=t['task_id'],request_sha256=digest(t['request'])) for t in tasks],
        scope='Same development cache; references hashed but not opened by request construction; no train/test access.'))
    return tasks


def verify():
    manifest=read(HERE/'manifest.json')
    for name,expected in manifest['protected_sha256'].items():
        if sha(ROOT/name)!=expected: raise ValueError('Frozen artifact changed: '+name)
    tasks=read(HERE/'local/tasks.json')
    if [dict(task_id=t['task_id'],request_sha256=digest(t['request'])) for t in tasks]!=manifest['tasks']:
        raise ValueError('Frozen task mismatch')
    if len(tasks)>40 or any(t['request']['model']!=MODEL for t in tasks):raise ValueError('Forbidden model/budget')
    return tasks
