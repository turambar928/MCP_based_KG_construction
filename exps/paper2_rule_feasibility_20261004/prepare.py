"""Freeze untouched development pairs and separate runtime inputs from references."""
import importlib.metadata
import math
import random
import sys
from pathlib import Path
from exps.paper2_rule_feasibility_20261004.common import HERE, ROOT, OLD, ARMS, PROTOCOL, read, sha, digest, write_once, read_events
from exps.paper2_rule_feasibility_20261004.generation import request, schema


def history():
    paths = [OLD / 'pilot_manifest.json'] + [ROOT / 'exps' / name / 'pilot_membership.json'
        for name in ('paper2_docred_v2', 'paper2_docred_v2_round2')]
    used = set(read(paths[0])['document_ids'])
    for p in paths[1:]:
        used.update(c for pair in read(p)['pairs'] for c in pair)
    for name in ('paper2_docred', 'paper2_docred_v2', 'paper2_docred_v2_round2', 'paper2_docred_formal'):
        for p in sorted((ROOT / 'exps' / name / 'local').glob('*responses.jsonl')):
            paths.append(p)
            for row in read_events(p):
                used.add(row['case_id'])
    return used, paths


def select_pairs(pairs, used):
    eligible = [pair for pair in pairs if not set(pair) & set(used)]
    if len(eligible) < 10:
        raise ValueError('Insufficient untouched development pairs; no replacement or test access allowed')
    chosen = eligible[:10]
    if len({c for pair in chosen for c in pair}) != 20:
        raise ValueError('Duplicate or malformed development membership')
    return chosen


def construct(pairs, documents, references, relations):
    public, scorer = [], []
    for pair in pairs:
        for index, cid in enumerate(pair):
            doc = documents[cid]
            types = {e['entity_id']: e['type'] for e in doc['entities']}
            gold = sorted({(str(t['h']), t['r'], str(t['t'])) for t in references[cid]['labels']})
            triples, injected = set(gold), []
            rng = random.Random('v2:' + cid)
            if index == 1 and gold:
                target = max(1, math.ceil(.2 * len(gold)))
                attempts = 0
                while len(injected) < target and attempts < target * 100:
                    attempts += 1
                    h, relation, tail = rng.choice(gold)
                    if attempts % 2:
                        relation = rng.choice(sorted(relations))
                    else:
                        tail = rng.choice(sorted(types))
                    candidate = (h, relation, tail)
                    if h == tail or candidate in triples:
                        continue
                    triples.add(candidate)
                    injected.append(candidate)
                if len(injected) != target:
                    raise ValueError('Cannot construct declared corruption; stop without replacing document')
            records = [dict(record_id=cid + ':' + digest(t)[:16], subject_type=types[t[0]],
                relation=t[1], object_type=types[t[2]], source_document_id=cid,
                head_entity_id=t[0], tail_entity_id=t[2]) for t in sorted(triples)]
            public.append(dict(document=doc, records=records))
            scorer.append(dict(case_id=cid, condition='perturbed' if index else 'clean',
                               reference=[list(t) for t in gold], injected=[list(t) for t in injected]))
    return public, scorer


def source_dependencies():
    own = sorted(HERE.glob('*.py'))
    imports = [ROOT / 'exps' / f for f in (
        'paper2_docred/environment.py', 'paper2_docred/generation.py',
        'paper2_docred_v2_round2/environment.py', 'paper2_docred_v2_round2/generation.py',
        'papers_readiness_20261002/output_contract.py', 'papers_readiness_20261002/diagnose_loop.py')]
    return own + imports


def versions():
    return dict(python=sys.version.split()[0], **{p: importlib.metadata.version(p) for p in ['jsonschema', 'httpx']})


def freeze():
    if (HERE / 'local/journal.jsonl').exists():
        raise ValueError('Collection journal already exists; use verify/status, never refreeze')
    used, historical = history()
    all_pairs = read(OLD / 'episodes.json')['dev']
    pairs = select_pairs(all_pairs, used)
    membership = read(OLD / 'membership.json')
    docs = {d['case_id']: d for d in read(OLD / 'local/dev_public.json')}
    refs = {d['case_id']: d for d in read(OLD / 'local/dev_scorer_only.json')}
    for cid in [c for pair in pairs for c in pair]:
        if membership[cid]['split'] != 'dev' or digest(docs[cid]) != membership[cid]['public_sha256'] or digest(refs[cid]) != membership[cid]['reference_sha256']:
            raise ValueError('Source membership/hash mismatch')
    relations = read(OLD / 'relations.json')
    public, scorer = construct(pairs, docs, refs, relations)
    tasks = [dict(task_id=x['document']['case_id'] + '/' + arm, case_id=x['document']['case_id'], arm=arm,
                  request=request(x['document'], arm, relations, x['records'])) for x in public for arm in ARMS]
    random.Random(20261004).shuffle(tasks)
    write_once(HERE / 'protocol.json', PROTOCOL)
    write_once(HERE / 'output.schema.json', schema())
    write_once(HERE / 'local/public.json', public)
    write_once(HERE / 'local/scorer_only.json', scorer)
    write_once(HERE / 'local/requests.json', tasks)
    write_once(HERE / 'membership.json', dict(pairs=pairs, previous_document_ids=sorted(used),
        no_overlap=True, previous_documents=len(used), selected_documents=20,
        remaining_eligible_pairs=len([p for p in all_pairs if not set(p) & used]) - len(pairs)))
    inputs = historical + [OLD / 'episodes.json', OLD / 'membership.json', OLD / 'relations.json',
        OLD / 'data_manifest.json', OLD / 'local/dev_public.json', OLD / 'local/dev_scorer_only.json']
    frozen = [HERE / n for n in ('protocol.json', 'output.schema.json', 'membership.json',
                                 'local/public.json', 'local/scorer_only.json', 'local/requests.json')]
    manifest = dict(version=PROTOCOL['version'], runtime_versions=versions(),
        dependencies_sha256={str(p.relative_to(ROOT)): sha(p) for p in source_dependencies() + inputs + frozen},
        requests=[dict(task_id=t['task_id'], sha256=digest(t['request'])) for t in tasks],
        state='frozen_before_collection', planned_outputs=40, model_api_requests_at_freeze=0)
    write_once(HERE / 'manifest.json', manifest)
    verify()
    return manifest


def verify():
    manifest = read(HERE / 'manifest.json')
    if manifest['runtime_versions'] != versions():
        raise ValueError('Frozen runtime versions changed')
    for p, expected in manifest['dependencies_sha256'].items():
        if sha(ROOT / p) != expected:
            raise ValueError('Frozen dependency changed: ' + p)
    tasks = read(HERE / 'local/requests.json')
    if [dict(task_id=t['task_id'], sha256=digest(t['request'])) for t in tasks] != manifest['requests']:
        raise ValueError('Frozen requests changed')
    used, _ = history()
    chosen = {c for p in read(HERE / 'membership.json')['pairs'] for c in p}
    if chosen & used:
        raise ValueError('Selected development document has since been used by another study')
    return tasks
