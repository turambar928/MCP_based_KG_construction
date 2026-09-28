# Archive-rule coverage and policy interface

This offline study extends the earlier fixed-order bridge without changing the
TNEWS RL environment, reward-validation results or checkpoints. It does not
train a policy or call any model. [report_zh.md](report_zh.md) gives the findings.

## Inputs and semantics

The inputs are RuleTest-94, the original `data/{政务,金融,环境}_{nodes,relationships}.csv`
pairs and the existing rule-lineage archive. CSV row occurrences remain distinct;
node IDs resolve endpoints. Missing endpoints and absent/Unknown node types cause
abstention. Only outer whitespace is normalized; no aliases, type inference or
reference-based mapping is used. These CSV snapshots differ from the earlier
SHACL baseline inputs and must not be given that table's denominators.

Rules retain their original identifiers and source document/strategy/line/ordinal.
Allowed patterns do not close the world; a matching permission and prohibition
cause abstention. Original suite IDs and expected labels are stored only in the
scorer map. Runtime records have neutral IDs, and policies see aggregate counts.

## Interface

`ArchiveReplay.reset()` returns a public observation. `observe()` contains record,
type-availability, flag, conflict and active-rule counts, acquired strategy names,
remaining budget and the action mask. `available_actions()` returns booleans for
`acquire_deletion`, `acquire_augmentation`, `repair`, and `stop`.

`step(action)` returns `(observation, done, event)`; it has **no reward output**.
An acquisition loads that strategy's entire archived compiled bank, retaining
lineage shared by both strategies. Its archived-response count is a provenance
quantity, never a one-call generation cost. Loading an acquired bank again is
rejected. Repair removes currently unopposed forbidden matches; deleting the
entire nonempty record set is blocked. Stop and a six-decision limit terminate
replay. This four-action mechanism interface does not replace the eight-action
trained RL environment or imply checkpoint compatibility.

A later permission for an already removed record produces a `late_permissions`
event. Records are not silently recreated. The same event records activated
rules, detections, removed records, before/after observations and local elapsed
time. Timings cover step execution, not API latency or total data loading.

## Run without network

```bash
KG_PYTHON=/tmp/kgbench-local-venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
$KG_PYTHON exps/paper2_rule_integration/audit.py
$KG_PYTHON -m unittest exps.paper2_rule_integration.test_runtime exps.paper1_reextraction_control.test_protocol
$KG_PYTHON exps/paper2_rule_integration/publish.py
$KG_PYTHON exps/paper2_rule_integration/verify.py
```

Run `paper1_reextraction_control/prepare.py` before verification on a fresh checkout.
No package downloads are needed. The installed experiment Python environment is
used. Old frozen scripts and manifests are never rewritten.

## Artifacts

- `rules_public.jsonl.gz`, `records_public.jsonl.gz`: explicit runtime inputs.
- `rule_matches.jsonl.gz`, `record_matches.jsonl.gz`: complete per-rule/per-record
  coverage for deletion, augmentation and union, including nonmatches.
- `schedule_traces.jsonl.gz`: 16 full replays (4 datasets × 2 acquisition orders
  × immediate/deferred removal). Synthetic unit examples are excluded.
- `results.json`: coverage and observed actions; factual accuracy is null where
  independent semantic labels are absent. Suite scores use designed labels only.
- `input_manifest.json`: original input hashes. `preservation.json` protects all
  1,461 pre-existing tracked experiment/input/implementation files, including
  the human annotation materials. `verification.json` checks their preservation,
  actual trajectory replay, frozen Paper1 prompts and the absence of online results.

Known result: the three raw graphs provide no entity types, and RuleTest-94 has
only one effective forbidden pattern from deletion. The schedules produce the
same final records. Completing meaningful learned scheduling requires trusted
type information, useful rule coverage and separate evaluation labels first.
