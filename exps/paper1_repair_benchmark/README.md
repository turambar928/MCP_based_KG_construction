# Paper 1 paired KG-repair benchmark

This directory contains the submission-facing, instance-level experiment for
Paper 1. It complements the earlier corpus-level quality scores with a paired
benchmark in which every injected defect has a clean target and an audit
record.

## Protocol

- Source corpora: government, finance, and environment JSONL files under
  `exps/`.
- Sampling: 500 source documents per domain where available.
- Split: 70/15/15 by source-document identity before corruption, seed 42.
- Corruption: two actual graph mutations per document, selected from missing
  triple, duplicate triple, invalid relation, reversed edge, unsupported value,
  and hierarchy conflict.
- Held-out test set: 225 documents (75 per domain), 450 manifested defects.
- Shared repair model: `claude-haiku-4-5-20251001`, temperature 0.
- Independent semantic judge: `google/gemma-4-26B-A4B-it`.

The API key is read from the ignored local `api` file and is never written to
an artifact.

## Reproduction

```bash
python3 exps/paper1_repair_benchmark/build_benchmark.py
python3 exps/paper1_repair_benchmark/run_benchmark.py --split test --workers 4
python3 exps/paper1_repair_benchmark/analyze_results.py
python3 exps/paper1_repair_benchmark/analyze_ablations.py
python3 exps/paper1_repair_benchmark/build_failure_audit.py
python3 exps/paper1_repair_benchmark/semantic_reliability.py
```

API-backed runs are checkpointed after every ten completed cases and resume
only non-`ok` cases. `run_benchmark.py` evaluates the following methods on
identical inputs:

- no repair;
- deterministic rule repair;
- SHACL-style canonical-head and allowed-predicate repair;
- one-pass direct LLM repair;
- a two-call ReAct-style diagnose/act agent;
- the full source-grounded, multi-scale, constraint-gated method.

## Primary outputs

- `benchmark.jsonl`, `manifest.jsonl`: paired cases and defect provenance;
- `predictions_*.jsonl`: exact per-case outputs, statuses, calls, latency, and
  raw model responses;
- `per_case_metrics.csv`, `per_defect_metrics.csv`: instance-level metrics;
- `summary.csv`, `summary.json`: domain and overall bootstrap summaries;
- `pairwise_mcnemar.json`: exact paired defect-repair tests;
- `failure_audit_*.csv`: all unresolved defects and the fixed-seed audit sample;
- `semantic_*`: independent-judge scores, raw responses, and five-run
  stability results.

`Q_score` is retained as a secondary diagnostic. The primary outcomes are
defect repair rate, edit precision/recall, clean-fact preservation,
over-repair rate, triple F1, calls, and latency.
