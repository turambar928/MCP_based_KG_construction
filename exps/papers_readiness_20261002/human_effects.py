"""Optional, human-completed semantic-effect sidecar; never infers human labels."""
import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from exps.paper1_human_review.build_package import items

FIELDS = ['task', 'item_id', 'semantic_effect', 'evidence_notes']
EFFECTS = ('repaired', 'harmed', 'format_only', 'ineffective', 'other_acceptable', 'uncertain')


def validate(rows, expected):
    seen = set()
    for row in rows:
        key = (row.get('task'), row.get('item_id'))
        if key in seen or key not in expected:
            raise ValueError('Duplicate or unknown item')
        seen.add(key)
        if row.get('semantic_effect') not in EFFECTS or not row.get('evidence_notes', '').strip():
            raise ValueError('Real effect judgment and supporting notes required for every item')
    if seen != expected:
        raise ValueError('Missing items; partial files are not scored')
    return {effect: sum(r['semantic_effect'] == effect for r in rows) for effect in EFFECTS}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['template', 'score'])
    p.add_argument('path', type=Path)
    a = p.parse_args()
    public, _ = items()
    expected = {(r['task'], r['item_id']) for r in public if r['task'] == 'E'}
    if a.command == 'template':
        with a.path.open('x', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
            w.writeheader()
            w.writerows(dict(task=t, item_id=i, semantic_effect='', evidence_notes='') for t, i in sorted(expected))
        print('Created blank optional sidecar; no human result produced.')
    else:
        with a.path.open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != FIELDS:
                raise ValueError('Unexpected columns')
            counts = validate(list(reader), expected)
        print(json.dumps(dict(scope='Human-completed sampled operation effects; not whole-graph F1.',
                              n=len(expected), counts=counts), indent=2))


if __name__ == '__main__':
    main()
