# Context-bound rule admission: offline prototype

This version adds an admission boundary before the frozen DocRED executor. It checks public provenance, then requires independently supplied, pinned attestations before **any** proposed rule can enter the active rule set. It does not infer entailment, create reviewer labels, call a model, or alter the earlier failed expansion gate.

The canonical explanation and numerical results are in [Paper2's report](../../paper2/RULE_ADMISSION_RESULTS_2026-10-04.md). Benchmark definitions are in [BENCHMARK_GUIDE.md](../../paper2/BENCHMARK_GUIDE.md).

## Reproduce

Run from the repository root, using installed dependencies:

```bash
/tmp/kgbench-local-venv/bin/python -m unittest exps.paper2_rule_admission_20261004.test_admission exps.paper2_rule_failure_audit_20261004.test_audit -v
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_admission_20261004/run.py
```

The replay needs the existing licensed local public-input and scorer files from the frozen 10-04 study. No downloads, raw-response regeneration, API access or training occur. All policies finish before scorer references are opened. Generated artifacts are write-once; a changed trusted registry must be evaluated as a new study, not overwrite this result.

## What is implemented

- `admission.py`: mechanical provenance checks; immutable binding of candidate, response, source, all episode documents/records and relation vocabulary; externally pinned registry loading; explicit quarantine/validation decisions; projection into the unchanged executor contract.
- `trust_registry.json`: empty trust roots. No independent semantic attestations or authoritative rule schema have been supplied for this batch.
- `run.py`: original, provenance-only and validation-required arms, each with the same eight policies and ten document pairs (240 replays).
- `decisions.json`: proposed/grounded/validated/admitted status for each candidate occurrence, reason and hashes. Raw quotes/text are excluded.
- `replays.json`: fixed schedules, acquisition/activation counts, removals, reward components and scorer-only outcomes.
- `results.json`: aggregate metrics and protected input/code hashes.
- `test_admission.py`: 22 synthetic tests, including successful externally approved activation, state invalidation and preserved executor protections. The five existing audit tests also pass. Synthetic attestations are temporary fixtures, not added to the real registry or empirical denominators.

`admitted` means eligible for activation. A rule becomes active only when its packet is acquired by the schedule. Validation of an unacquired packet cannot provide the policy with active coverage. Duplicate occurrences are retained in candidate counts; the executor still deduplicates active rule keys.

## External evidence contract

Only the operator selects trusted artifacts. A model's self-reported confidence, `validated` field or quote is not an authority. Hash pinning verifies artifact integrity, not semantic truth or reviewer independence.

A manifest has `version` and `trusted_sources`. Each source supplies `source_id`, `kind` (`independent_review` or `trusted_schema_review`), a relative `path`, and the SHA-256 of that file's bytes. Paths stay under the manifest directory; private evidence can be under ignored `local/`.

The artifact has exactly:

- `version`: `context-bound-rule-admission-v1`;
- `source_id` and `kind`: matching the manifest;
- `authority`: the actual reviewer or accountable schema-review authority, never a model-invented attribution;
- `decisions`: rows with `binding`, `verdict`, `basis`, `rationale`.

A decision's `binding` is the full binding object exported in `decisions.json`. It binds the exact rule, generating response, source document, **all documents/records in the execution episode**, and relation vocabulary. A type rule can affect the partner document, so approving only its originating document would be insufficient. This prototype deliberately uses narrow episode-scoped attestations; it is not a universal ontology-validation engine.

`verdict` is `approve`, `reject`, or `uncertain`. `basis` identifies the independent judgment or the authoritative schema definitions and their scope; `rationale` explains why this concrete rule follows. All matching decisions must approve; rejection/uncertainty causes quarantine. A schema review can validate a type rule but cannot certify a source-entailment claim. A source rule needs an independent review, plus valid original-source quote offsets/hashes.

For prospective evaluation, independent decisions should cover all sampled candidate types and be obtained without reference labels or injection identities. Approving only the currently known successful deletions would introduce selection leakage. The interface cannot establish that independence by itself; the study protocol and actual reviewers must provide it.

There is intentionally no auto-approval command and no filled real-evidence example. When genuine evidence arrives, preserve this empty-registry baseline, bind it to a new protocol and evaluate acceptance accuracy, coverage, edits, costs and strategy complementarity on appropriate samples.

## Result interpretation

407 compiled candidates pass mechanical grounding, but zero have independent approval. Provenance-only execution exactly reproduces all 80 original traces: 96.63% F1, 17 injected-item removals and four reference losses for acquire-then-repair. Requiring independent validation admits none: 94.02% F1, no repair, no reference loss. This demonstrates enforcement and the missing validation evidence; it does **not** demonstrate a better semantic validator, repaired factual errors, or improved learning.

Unvalidated permission/support rules are also quarantined, so they cannot earn coverage rewards or veto certified prohibitions. The old conflict, late-permission and empty-graph rules remain unchanged. Historical candidates, judgments, gates, training environments and scores remain frozen.
