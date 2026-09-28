# Paper1: repair versus re-extraction — prepared, not executed

**Status: 240 requests specified, zero requests executed, no formal outcomes.**
No API client or credential reader is provided in this directory. Mock responses
exist only in unit-test memory and cannot be accepted as formal results.

## Frozen design

Use the same 60 receipts from the earlier follow-up test and the same archived
initial extraction outputs. This is a matched follow-up on previously evaluated
documents, not a new held-out corpus. It does not overwrite the separate frozen
840-request ablation or combine its outcomes with this study.

| Arm | Initial graph supplied | Evidence index |
|---|---|---|
| repair_simple | Yes, common structural preprocessing | No |
| repair_index | Yes, same preprocessing | Yes |
| extract_simple | No graph or diagnostic context | No |
| extract_index | No graph or diagnostic context | Yes |

All four receive identical public document IDs, schema, field definitions, full
source text and numbered source lines. The two indexed arms receive the identical
index. Only the task-specific opening instruction changes between repair and
extraction; all common output/source constraints are identical. No labels enter
prompt creation. Original graph values may naturally occur in the shared source;
they are not supplied as graph proposals to the extraction arms.

The future model is `google/gemma-4-26B-A4B-it`, temperature 0, completion cap
4,000. All 240 outcomes must be collected contemporaneously; historical outputs
are not substituted for arms. A later authorized online runner should use two
workers, three-second global launch spacing and at most four transport attempts.
Transport/parse failures remain in the denominator as empty graphs. Input token
lengths are measured, not asserted equal; marginal calls exclude the archived
initial extraction. No GPT/Claude requests are permitted.

The sole primary comparison is **repair_index+gate minus extract_index+gate**
macro document exact multiset triple F1. Bootstrap confidence intervals and
2-sided sign randomization use 10,000 whole-document draws, seed 42. Other arms,
normalized F1, preservation, harm, filtering and costs are secondary/descriptive.
Missing reference fields are excluded only during scoring using the existing
scorer. Raw and gated outputs share each response.

## Offline commands

```bash
KG_PYTHON=/tmp/kgbench-local-venv/bin/python
$KG_PYTHON -m unittest exps.paper1_reextraction_control.test_protocol
$KG_PYTHON exps/paper1_reextraction_control/prepare.py
# Only after collecting all actual authorized responses:
$KG_PYTHON exps/paper1_reextraction_control/scoring.py validate --responses /path/to/actual_responses.jsonl
$KG_PYTHON exps/paper1_reextraction_control/scoring.py score --responses /path/to/actual_responses.jsonl
```

`prepare` checks an existing lock rather than replacing it. New model settings,
new inputs or changed code require a separately versioned study. `requests.jsonl`
holds the actual four-arm request bodies and hashes; `manifest.json` pins inputs,
code, reference file hash and statistics. Reference contents are read only when
formal outcomes are scored.

## Response interface

Each JSONL row must contain `kind="model_response"`, `is_mock=false`, `case_id`,
`arm`, `model`, `prompt_sha256`, `status` (`ok`, `parse_error`, `transport_error`),
`raw_response`, `triples`, `attempts`, `usage`, and measured `wall_seconds`.
`attempts` preserves 1–4 attempt records. `usage` records returned token counts;
unreported counts are null, not zero. `raw_response` preserves the full decoded
assistant content. Successful content must be the requested strict JSON with a
`triples` list and string head/relation/tail fields; unparseable content is a
parse failure. Transport failures use empty content; all failures use empty
triples. Save status/error information with attempts without credentials.

The importer checks model, prompt, exact case/arm coverage, raw/parsed agreement,
unique outcomes, and mock flags before allowing any result file. An existing
formal result is never overwritten. These checks enforce the data contract;
they do not independently authenticate who produced a manually supplied file.

Artificial validator fixtures use a synthetic case ID, remain in memory, and
produce only pass/fail test results. No empirical scores or manuscript values
are generated from them. The original annotator packages remain untouched.
