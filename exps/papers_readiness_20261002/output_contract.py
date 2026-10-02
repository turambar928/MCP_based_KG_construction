"""Offline-only proposal for a future rule-output contract, not an online round.

The old compiler and frozen prompts remain unchanged. Schema validation only
checks structure; the original compiler still checks vocabulary and provenance.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from jsonschema import Draft202012Validator
from exps.paper2_docred_v2_round2.generation import compile_response

HERE = Path(__file__).resolve().parent


def schema():
    evidence = dict(type='array', minItems=1, items=dict(type='object', additionalProperties=False,
        required=['sentence_id', 'quote'], properties={
            'sentence_id': dict(type='integer', minimum=0), 'quote': dict(type='string', minLength=1)}))
    common = dict(type='object', additionalProperties=False)
    type_rule = dict(common, required=['family', 'kind', 'pattern'], properties={
        'family': {'const': 'type'}, 'kind': {'enum': ['allowed', 'forbidden']},
        'pattern': dict(type='array', minItems=3, maxItems=3, items=dict(type='string', minLength=1))})
    source_rule = dict(common, required=['family', 'record_id', 'verdict', 'evidence'], properties={
        'family': {'const': 'source'}, 'record_id': dict(type='string', minLength=1),
        'verdict': {'enum': ['supported', 'contradicted']}, 'evidence': evidence})
    insufficient = dict(common, required=['family', 'record_id', 'verdict', 'evidence'], properties={
        'family': {'const': 'source'}, 'record_id': dict(type='string', minLength=1),
        'verdict': {'const': 'insufficient'}, 'evidence': dict(type='array', maxItems=0)})
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            'title': 'Offline proposed rule-output contract; not a deployed experiment',
            **common, 'required': ['supplementary_clauses', 'rules'], 'properties': {
                'supplementary_clauses': dict(type='array', maxItems=3, items=dict(type='string')),
                'rules': dict(type='array', maxItems=20, items={'oneOf': [type_rule, source_rule, insufficient]})}}


def examples():
    """All examples are synthetic and each enum contains one concrete value."""
    rules = [dict(family='type', kind='allowed', pattern=['MISC', 'P50', 'PER']),
             dict(family='type', kind='forbidden', pattern=['TIME', 'P50', 'PER']),
             dict(family='source', record_id='synthetic:0', verdict='supported',
                  evidence=[dict(sentence_id=0, quote='Alice wrote Book A.')]),
             dict(family='source', record_id='synthetic:1', verdict='contradicted',
                  evidence=[dict(sentence_id=1, quote='Bob did not write Book A.')]),
             dict(family='source', record_id='synthetic:2', verdict='insufficient', evidence=[])]
    return [dict(supplementary_clauses=[], rules=[r]) for r in rules] + [dict(supplementary_clauses=[], rules=[])]


INSTRUCTIONS = """Offline contract proposal, not a third development round.
Return exactly one JSON object, without a Markdown fence or surrounding text.
Use the supplied output schema. Each kind must be exactly "allowed" or exactly
"forbidden"; never concatenate choices. Each verdict must be exactly one of
"supported", "contradicted", or "insufficient". The examples are synthetic:
replace their IDs, vocabulary and quotations with the supplied document data.
Use only the supplied type and relation vocabulary. At most 20 rules total and
at most three supplementary clauses are permitted. A supported or contradicted
source rule needs an exact quotation from a numbered ORIGINAL sentence.
Absence of evidence is insufficient, not contradiction. Hypothetical augmented
clauses cannot serve as evidence. Type compatibility is not factual support.
For insufficient evidence use evidence: []. If no justified rule is available,
return {"supplementary_clauses":[],"rules":[]}. Do not pad the candidate list.
This interface draft does not authorize requests or establish semantic validity.
"""


def main():
    spec = schema()
    Draft202012Validator.check_schema(spec)
    validator = Draft202012Validator(spec)
    for example in examples():
        validator.validate(example)
    (HERE / 'proposed_output.schema.json').write_text(json.dumps(spec, indent=2) + '\n')
    (HERE / 'synthetic_examples.json').write_text(json.dumps(examples(), indent=2) + '\n')
    (HERE / 'proposed_output_instructions.txt').write_text(INSTRUCTIONS)
    counts = {}
    for name in ('paper2_docred_v2', 'paper2_docred_v2_round2'):
        folder = ROOT / 'exps' / name
        public = {x['document']['case_id']: x for x in json.loads((folder / 'local/pilot_public.json').read_text())}
        relations = json.loads((ROOT / 'exps/paper2_docred/relations.json').read_text())
        archived = {(p['source_document_id'], p['strategy']): p for p in json.loads((folder / 'pilot_packets_public.json').read_text())}
        rows = [json.loads(line) for line in (folder / 'local/pilot_responses.jsonl').read_text().splitlines()]
        from collections import Counter
        rejects = Counter()
        for row in rows:
            source = public[row['case_id']]
            ok, rules, rejection = compile_response(row['raw_response'], source['document'], source['records'], relations)
            old = archived[row['case_id'], row['arm']]
            assert ok == old['parse_success'] and rules == old['rules']
            assert [{'ordinal': r.get('ordinal'), 'reason': r['reason']} for r in rejection] == old['rejections']
            rejects.update(r['reason'] for r in rejection)
        counts[name] = dict(responses=len(rows), historical_compiler_replay_identical=True, rejection_counts=dict(rejects))
    (HERE / 'contract_audit.json').write_text(json.dumps(dict(status='offline_proposal_only', actual_api_requests=0,
        schema_examples_valid=len(examples()), historical_replays=counts,
        boundary='Old responses are not reinterpreted with the new schema; malformed, truncated and invalid-enum outputs retain their original scores.'), indent=2) + '\n')
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()
