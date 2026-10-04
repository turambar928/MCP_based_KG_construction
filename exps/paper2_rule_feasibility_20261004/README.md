# Paper2 independent rule-feasibility development protocol

Frozen 2026-10-04; **no model requests or training performed**.

The full Chinese protocol is in [paper2/NEXT_EXPERIMENT_PROTOCOL.md](../../paper2/NEXT_EXPERIMENT_PROTOCOL.md), alongside the manuscript. This directory implements that protocol. It does not change the old two-round study or unblock its formal runner.

- 10 untouched existing dev pairs / 20 documents, excluding all prior pilot memberships and logged responses.
- 40 planned outputs, Gemma `google/gemma-4-26B-A4B-it` only, maximum two dispatches per task. No model fallback.
- Fixed original round-2 environment; no learned-policy results.
- Four numerical gates: schema usability, source-necessary reference recovery, safe strategy complementarity, and diagnostic decision opportunity.
- A pass only permits consideration of a separately frozen formal design. Quote provenance does not certify semantics; post-hoc oracle savings are not measured online savings.

## Commands

From the repository root, using Python 3.10.12 and the versions in `requirements.txt` (already installed in `/tmp/kgbench-local-venv`):

```bash
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_feasibility_20261004/runner.py verify
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_feasibility_20261004/runner.py status
/tmp/kgbench-local-venv/bin/python -m unittest exps.paper2_rule_feasibility_20261004.test_pipeline exps.paper2_docred_v2_round2.test_contracts -v
```

Only the following explicit command reads credentials and calls the network; **it has not been run**:

```bash
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_feasibility_20261004/runner.py collect
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_feasibility_20261004/runner.py analyze
```

Set both `PAPER2_API_KEY` and `PAPER2_BASE_URL` securely, or provide an unambiguous existing `apis` file. The client bypasses environment proxies and disallows redirects. Do not commit credentials. Frozen dependencies are checked before collection. Do not alter frozen Python files, requests or source data after collection begins.

`freeze` has already run. On a fresh licensed-data checkout it can recreate the local input artifacts only if original files/logs, hashes and runtime versions match; missing local archives are not silently downloaded. Obtain DocRED using its original access and license conditions, and retain the original preparation artifacts under `paper2_docred/local` and historical response logs. See [the original study](../paper2_docred/README.md). Public JSON manifests alone are not the raw dataset.

## Artifacts and accounting

|Artifact|Meaning|
|---|---|
|`protocol.json`, `output.schema.json`|Pre-collection protocol and schema|
|`membership.json`|Selected and excluded document IDs; ordered pairs|
|`manifest.json`|Code/input/runtime/request hashes; freeze-time state, not a live progress counter|
|`validation.json`|Offline validation snapshot; no empirical model results|
|`local/public.json`, `local/requests.json`|Ignored source inputs and exact request bodies|
|`local/scorer_only.json`|Ignored scoring references and controlled injection membership|
|`local/journal.jsonl`|Created only by collection: append-only dispatch/response/outcome log|
|`packets.json`, `traces.json`, `costs.json`, `results.json`|Created only after all outcomes are finalized; absent until actual analysis|
|`local/compiler_audit.json`|Full rejected candidates, kept local|

Collection journals persist a dispatch intent before I/O. Unknown interrupted deliveries are never resent automatically and are reported separately. Observed attempts include failed requests; packet acquisitions in offline schedules are not additional API requests. No output-format repair retries or sample replacements are permitted. Partial/corrupt journals fail closed; preserve them for recovery.

All experiment outputs use immutable writes. Tests create synthetic responses only in temporary directories. The integration test checks the full 40-output flow without a network client and does not create study results.

## Source layout

- `prepare.py`: development exclusions, deterministic graph construction, freeze/verify.
- `generation.py`: explicit prospective output contract, prompt rendering and compiler.
- `runner.py`: Gemma-only transport, durable accounting, resume and CLI.
- `analyze.py`: public-input fixed schedules, scorer-only diagnostics and gates.
- `test_pipeline.py`: parser, transport, interruption, replay, attribution, gates and offline integration tests.

Raw source text, raw responses and scorer references stay under ignored `local/`. Public compiled quote evidence contains offsets and hashes, not quotation text. Existing manuscripts and historical results are unchanged.
