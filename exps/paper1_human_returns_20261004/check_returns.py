"""Validate received independent human labels and prepare a blind adjudication handoff.

No model calls, inferred labels, or final adjudicated scoring.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
from exps.paper1_human_review.build_package import items
from exps.paper1_human_review.process_returns import read_return, identity, fingerprint, frozen_fields, merge, write_csv
from exps.paper1_submission_extensions.score_human_annotations import agreement


def save(path, value):
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if path.exists() and path.read_text() != text:
        raise ValueError('Output differs; preserve existing review: ' + str(path))
    path.write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    public, mapping = items()
    expected = {identity(r): r for r in public}
    package = json.loads((args.input / 'manifest.json').read_text())
    assert fingerprint(public) == package['public_items_sha256']
    assert mapping == json.loads((args.input / 'coordinator/private_mapping.json').read_text())
    paths = {who: args.input / f'annotator_{who}/paper1_annotator_{who}.json' for who in ['A', 'B']}
    labels = {who: read_return(p, who, expected) for who, p in paths.items()}
    hashes = {who: hashlib.sha256(p.read_bytes()).hexdigest() for who, p in paths.items()}
    local = HERE / 'local'
    raw = local / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    for who, path in paths.items():
        target = raw / path.name
        if target.exists():
            assert target.read_bytes() == path.read_bytes()
        else:
            shutil.copy2(path, target)
    merged = local / 'merged'
    if not merged.exists():
        merge(paths['A'], paths['B'], merged)
    manifest = json.loads((merged / 'return_manifest.json').read_text())
    assert manifest['a_sha256'] == hashes['A'] and manifest['b_sha256'] == hashes['B']
    results, disputes = {}, []
    for task in ['D', 'E']:
        with (merged / f'{task}_adjudication.csv').open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 200
        for row in rows:
            uid = identity(row)
            assert fingerprint(frozen_fields(row)) == manifest['immutable_row_hashes'][':'.join(uid)]
            for who, prefix in [('A', 'annotator_a'), ('B', 'annotator_b')]:
                assert all(row[prefix + '_' + k] == labels[who][uid][k] for k in ['is_error', 'repair_acceptable', 'notes'])
        metrics = {}
        for field in ['is_error', 'repair_acceptable']:
            a = [r['annotator_a_' + field] for r in rows]
            b = [r['annotator_b_' + field] for r in rows]
            metrics[field] = dict(agreement(a, b), agreed=sum(x == y for x, y in zip(a, b)),
                disagreements=sum(x != y for x, y in zip(a, b)),
                confusion_a_then_b=dict(Counter(x + '/' + y for x, y in zip(a, b))),
                label_counts={who: dict(Counter(labels[who][identity(r)][field] for r in rows)) for who in ['A', 'B']})
        selected = [r for r in rows if r['disagreement'] == 'True']
        for r in selected:
            disputes.append({k: r[k] for k in ['task', 'item_id', 'operation', 'annotator_a_is_error', 'annotator_b_is_error',
                'annotator_a_repair_acceptable', 'annotator_b_repair_acceptable', 'annotator_a_notes', 'annotator_b_notes']})
        results[task] = dict(n=200,disputed_items=len(selected),agreed_items=200-len(selected),
            initially_disputed_decisions=sum(v['disagreements'] for v in metrics.values()),metrics=metrics,
            repair_disagreement_by_operation={op: dict(n=sum(r['operation']==op for r in rows),
                confusion_a_then_b=dict(Counter(r['annotator_a_repair_acceptable']+'/'+r['annotator_b_repair_acceptable']
                    for r in rows if r['operation']==op))) for op in ['add','remove']})
    summary = dict(status='independent_returns_complete_adjudication_pending',
        package_version=package['version'],frozen_public_sample_hash_verified=True,
        return_sha256=hashes,independent_rows_per_annotator=400,
        disputed_items=len(disputes),initially_disputed_decisions=sum(r['initially_disputed_decisions'] for r in results.values()),
        model_api_requests=0,labels_changed=0,human_workflow_independence='not inferable from files alone',
        tasks=results,final_adjudicated_scores='not computed; requires real adjudication',
        scope='Sampled input discrepancies and actual edits; not whole-graph F1 or overall error recall.')
    save(HERE/'receipt_summary.json', summary)
    independent = json.loads((merged/'independent_agreement.json').read_text())
    assert all(independent[t][f] == {k: results[t]['metrics'][f][k] for k in independent[t][f]} for t in results for f in results[t]['metrics'])
    write_csv(local/'争议索引.csv', disputes)
    # Freeze a coordinator handoff once; never replace an edited adjudication package.
    target = local / 'Paper1_人工结果裁决包_2026-10-04.zip'
    if not target.exists():
        with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(merged.iterdir()):
                z.write(path, 'merged/' + path.name)
            z.write(local/'争议索引.csv','争议索引.csv')
            z.write(HERE/'ADJUDICATION_GUIDE_zh.md','先读我_裁决说明.md')
            z.write(HERE/'receipt_summary.json','receipt_summary.json')
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[who] for who,p in paths.items())
    print(json.dumps(dict(disputed_items=len(disputes),disputed_decisions=summary['initially_disputed_decisions'],zip=str(target)),ensure_ascii=False))


if __name__=='__main__':
    main()
