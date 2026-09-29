# Paper1 service-recovery experiments

Both batches completed on 2026-09-28; analysis and manuscript integration continued on 2026-09-29. Only `google/gemma-4-26B-A4B-it` was called, directly through the laboratory service with environment proxies disabled. No GPT/Claude API calls or model downloads were made.

|Batch|Outcomes / actual requests|Transport|Parsing|
|---|---:|---|---|
|Repair vs extraction|240 / 240|All HTTP 200; no retries|All 240 fail the frozen strict parser because of enclosing Markdown JSON fences|
|Factorial / index controls|840 / 840|All HTTP 200; no retries|All 840 pass this study's original parser, which already handles fences|

These protocols have different frozen parsing rules; do not combine their parsing denominators. The 240 study preserves its strict primary results in `../paper1_reextraction_control/results.json`. Its separately labelled fence-compatible analysis was added after inspecting early response formatting, before reference scoring. The document-ID normalization diagnostic is also post-hoc; it attributes errors without changing relation/value outputs. Neither is a new preregistered result. See [format amendment](format_amendment.md), [240 report](reextraction/report_zh.md), and [840 report](ablation/report_zh.md).

The old 840-study outage records remain unchanged. New results are a full contemporaneous batch; old failure outcomes were not silently replaced. Both studies reuse already evaluated documents. Every request retains the raw response, model identity, request hash, usage, attempts and wall time. Wall time includes pacing and retries; usage is actual returned usage. Old historical candidates used by offline studies required no API calls.

Run in an environment containing the repository dependencies (the recorded run used `/tmp/kgbench-local-venv/bin/python`):

```bash
python3 -m unittest exps.paper1_online_recovery.test_runner exps.paper1_online_recovery.test_format
python3 exps/paper1_reextraction_control/scoring.py validate --responses exps/paper1_online_recovery/reextraction/predictions.jsonl
python3 exps/paper1_online_recovery/analyze_reextraction.py
python3 exps/paper1_online_recovery/head_diagnostic.py
python3 exps/paper1_online_recovery/analyze_ablation.py
python3 exps/paper1_online_recovery/publish_ablation.py
```

These analysis commands make no model requests. The strict scoring CLI refuses to overwrite an existing result. `run.py` has resumable request collection but is not needed now: both batches are complete. Execution uses two workers, global three-second launch spacing, 150-second read/15-second connect timeouts and at most four transport attempts. Completed outcomes, including failures, are never rerun automatically.
