"""Gemma-only natural extraction then matched repairs on frozen external text."""
import concurrent.futures
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from exps.paper1_mechanism_audit.protocol import PublicInput, MODEL, SYSTEM, make_prompt, read_jsonl, preprocess
from exps.paper1_mechanism_audit.run_api import config, execute
from exps.paper1_external_receipts.shacl import receipt_shacl_context

HERE = Path(__file__).resolve().parent
EXTRACT_SYSTEM = ('Extract a document-level knowledge graph from the supplied receipt text. '
    'Return the COMPLETE graph as strict JSON: '
    '{"triples":[{"head":"...","relation":"...","tail":"..."}]}. '
    'Use the required document node and allowed relations. '
    'Copy exact source spans, emit at most one nonempty value per relation, and omit unsupported facts.')


def input_object(row, triples=()):
    return PublicInput(row['case_id'], row['domain'], row['source_evidence'],
                       row['required_document_node'], tuple(row['allowed_relations']), tuple(triples))


def run_stage(tasks, path, credentials):
    existing = {(r['case_id'], r['arm']) for r in read_jsonl(path)}
    pending = [t for t in tasks if (t[2].case_id, t[1]) not in existing]
    print(path.name, 'pending', len(pending), flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool, path.open('a') as f:
        futures = [pool.submit(execute, t, credentials) for t in pending]
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            row = future.result()
            f.write(json.dumps(row, ensure_ascii=False) + '\n'); f.flush()
            if i % 10 == 0 or row['status'] != 'ok':
                print(path.name, i, '/', len(pending), row['status'], flush=True)


def main():
    assert MODEL == 'google/gemma-4-26B-A4B-it'
    rows = read_jsonl(HERE / 'inputs.jsonl')
    assert len(rows) == 60 and len({x['case_id'] for x in rows}) == 60
    manifest = {'model': MODEL, 'temperature': 0, 'max_tokens': 4000,
                'seed': 20260922, 'case_ids': [r['case_id'] for r in rows],
                'stages': {'extract': 60, 'repair': 180}, 'arms': ['base','diagnosis','shacl_context'],
                'source_kind': 'independent receipt transcripts', 'raw_gate_response_shared': True,
                'max_attempts': 4, 'request_spacing_seconds': 4, 'failures_retained': True,
                'primary_metric': 'per-document exact multiset triple F1 against upstream human KIE labels',
                'secondary_metric': 'case-insensitive whitespace-removed triple F1',
                'labels_excluded_from_inference': True, 'extraction_prompt': EXTRACT_SYSTEM,
                'repair_prompt': SYSTEM,
                'inputs_sha256': hashlib.sha256((HERE/'inputs.jsonl').read_bytes()).hexdigest(),
                'protocol_sha256': hashlib.sha256((ROOT/'exps/paper1_mechanism_audit/protocol.py').read_bytes()).hexdigest(),
                'receipt_shacl_sha256': hashlib.sha256((HERE/'shacl.py').read_bytes()).hexdigest(),
                'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    path = HERE / 'run_manifest.json'
    if path.exists():
        assert json.loads(path.read_text()) == manifest, 'Frozen protocol changed'
    else:
        path.write_text(json.dumps(manifest, indent=2) + '\n')
    credentials = config()
    tasks = []
    for row in rows:
        inp = input_object(row)
        tasks.append(('external', 'extract', inp, EXTRACT_SYSTEM, json.dumps(inp.payload(), ensure_ascii=False)))
    random.Random(20260922).shuffle(tasks)
    run_stage(tasks, HERE/'extraction.jsonl', credentials)
    initial = {r['case_id']: r for r in read_jsonl(HERE/'extraction.jsonl')}
    assert len(initial) == 60
    tasks = []
    # SHACL preparation is sequential; inference does not read references.jsonl.
    for row in rows:
        inp = input_object(row, initial[row['case_id']]['triples'])
        for arm in ['base','diagnosis','shacl_context']:
            if arm == 'shacl_context':
                system = SYSTEM
                structural = preprocess(inp)
                payload = {**inp.payload(), 'input_triples': structural,
                           'shacl_context': receipt_shacl_context(inp, structural)}
                user = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            else:
                system, user = make_prompt(inp, arm)
            tasks.append(('external', arm, inp, system, user))
    random.Random(20260922).shuffle(tasks)
    run_stage(tasks, HERE/'repairs.jsonl', credentials)
    print('All 240 extraction/repair outcomes checkpointed.', flush=True)


if __name__ == '__main__':
    main()
