"""Freeze an external receipt sample before inference; download text only."""
import concurrent.futures
import hashlib
import json
import random
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
REVISION = '27be4271b251c256f695acbade9a801bffe85994'
BASE = f'https://raw.githubusercontent.com/zzzDavid/ICDAR-2019-SROIE/{REVISION}/'
RELATIONS = ['company', 'date', 'address', 'total']


def download(path):
    target = HERE / 'upstream' / path
    if not target.exists():
        response = requests.get(BASE + path, timeout=40)
        response.raise_for_status()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
    return path, hashlib.sha256(target.read_bytes()).hexdigest()


def main():
    ids = sorted(random.Random(20260922).sample(list(range(626)), 60))
    files = ['README.md', 'LICENSE', *[f'data/{kind}/{i:03d}.{ext}'
             for i in ids for kind, ext in [('box', 'csv'), ('key', 'json')]]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        hashes = dict(pool.map(download, files))
    inputs, references = [], []
    for i in ids:
        uid = f'sroie-{i:03d}'
        # Keep transcript order and content. Labels never enter source construction.
        lines = (HERE / f'upstream/data/box/{i:03d}.csv').read_text().splitlines()
        spans = [line.split(',', 8)[8].strip() for line in lines if line.strip()]
        source = ' '.join(spans)
        inputs.append({'case_id': uid, 'domain': 'receipt', 'source_evidence': source,
                       'required_document_node': uid, 'allowed_relations': RELATIONS})
        gold = json.loads((HERE / f'upstream/data/key/{i:03d}.json').read_text())
        references.append({'case_id': uid, 'annotated_relations': list(gold), 'triples': [
            {'head': uid, 'relation': r, 'tail': gold[r]} for r in RELATIONS if r in gold]})
    manifest = {'dataset': 'SROIE, community-corrected trainval mirror',
                'upstream_repository': 'https://github.com/zzzDavid/ICDAR-2019-SROIE',
                'revision': REVISION, 'seed': 20260922, 'population': 626,
                'sample_size': 60, 'sample_ids': [x['case_id'] for x in inputs],
                'selection': 'Uniform sample before inference; no label/support/outcome filtering',
                'source': 'Box transcripts in stored order, joined with one space; no images or coordinates supplied',
                'references': 'Separate upstream company/date/address/total human KIE annotations',
                'missing_reference_fields': 'Unannotated fields are excluded from scoring only; inputs keep all four permitted relations',
                'sha256': hashes}
    for name, records in [('inputs.jsonl', inputs), ('references.jsonl', references)]:
        payload = ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in records)
        target = HERE / name
        if target.exists() and target.read_text() != payload:
            raise RuntimeError(f'Frozen data changed: {name}')
        target.write_text(payload)
        manifest[name + '_sha256'] = hashlib.sha256(payload.encode()).hexdigest()
    path = HERE / 'data_manifest.json'
    if path.exists() and json.loads(path.read_text()) != manifest:
        raise RuntimeError('Frozen manifest changed')
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    print('Frozen 60 independent receipt transcripts and separate human reference records.')


if __name__ == '__main__':
    main()
