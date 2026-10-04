"""Verify the returned human questionnaire/CSVs and independently rescore a local copy."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
from exps.paper1_human_review.process_returns import fingerprint, frozen_fields, score_folder


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def copy_once(source, destination):
    if destination.exists():
        if destination.read_bytes() != source.read_bytes():
            raise ValueError('Existing archive differs: ' + str(destination))
    else:
        shutil.copy2(source, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    source = args.input
    receipt = read(HERE/'receipt_summary.json')
    flow = read(source/'裁决流程与哈希.json')
    answer_path = source/'真人裁决回答_154of154.json'
    answers = read(answer_path)
    assert answers['format'] == 'paper1-adjudication-questionnaire-v1'
    assert answers['package_version'] == receipt['package_version']
    assert answers['completed'] == answers['total'] == receipt['disputed_items'] == 154
    assert answers['return_sha256'] == flow['source_return_sha256'] == receipt['return_sha256']
    assert sha(answer_path) == flow['answer_sha256']
    for name, expected in flow['files_sha256'].items():
        assert sha(source/'merged'/name) == expected, name
    original = HERE/'local/merged'
    manifest = read(original/'return_manifest.json')
    assert read(source/'merged/return_manifest.json') == manifest
    assert read(source/'merged/independent_agreement.json') == read(original/'independent_agreement.json')
    seen, disputed, choices = set(), set(), Counter()
    for task in ['D','E']:
        rows = csv_rows(source/'merged'/f'{task}_adjudication.csv')
        assert len(rows) == 200
        for row in rows:
            uid = row['task'] + ':' + row['item_id']
            assert row['task'] == task and uid not in seen
            seen.add(uid)
            assert fingerprint(frozen_fields(row)) == manifest['immutable_row_hashes'][uid], uid
            labels = [row['adjudicated_'+f] for f in ['is_error','repair_acceptable']]
            assert all(v in {'0','1','U'} for v in labels), uid
            if row['disagreement'] == 'True':
                disputed.add(uid)
                answer = answers['answers'][uid]
                assert answer['choice'] in {'A','B'}
                choices[answer['choice']] += 1
                prefix = 'annotator_' + answer['choice'].lower() + '_'
                for f in ['is_error','repair_acceptable']:
                    assert row['adjudicated_'+f] == answer[f] == row[prefix+f], uid
                assert answer['notes'].strip() and row['adjudication_notes'] == answer['notes'], uid
            else:
                assert all(row['adjudicated_'+f] == row['annotator_a_'+f] == row['annotator_b_'+f]
                           for f in ['is_error','repair_acceptable']), uid
    assert seen == set(manifest['immutable_row_hashes'])
    assert disputed == set(answers['answers']) and dict(choices) == flow['choice_counts']
    # Preserve the earlier blank handoff. Score only a separate completed copy.
    local = HERE/'local/adjudicated'
    local.mkdir(parents=True, exist_ok=True)
    for name in ['D_adjudication.csv','E_adjudication.csv','return_manifest.json','independent_agreement.json']:
        copy_once(source/'merged'/name, local/name)
    for name in ['真人裁决回答_154of154.json','裁决流程与哈希.json','实验完成说明.md']:
        copy_once(source/name, local/name)
    score_folder(local)
    assert read(local/'human_results.json') == read(source/'merged/human_results.json')
    assert csv_rows(local/'per_configuration.csv') == csv_rows(source/'merged/per_configuration.csv')
    for name in ['human_results.json','human_results.md','per_configuration.csv']:
        copy_once(local/name, HERE/name)
    summary = dict(flow, independent_validation=dict(immutable_rows=400,questionnaire_answers_matched=154,
        concordant_items_preserved=246,original_scorer_results_match=True,pre_adjudication_agreement_unchanged=True,
        prior_handoff_preserved=True,model_api_requests=0,labels_inferred_or_changed_by_importer=0),
        workflow_provenance='Author-supplied completion record; workflow facts are reported, not inferred from file validation.',
        script_sha256=sha(Path(__file__)))
    target=HERE/'adjudication_receipt.json'
    if target.exists():
        assert read(target)==summary, 'Existing adjudication receipt differs'
    else:
        target.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary['independent_validation'],ensure_ascii=False))


if __name__=='__main__':
    main()
