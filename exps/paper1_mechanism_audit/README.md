# Paper 1 mechanism and execution-path audit (2026-09-21)

This directory supersedes deployment/mechanism claims in the 2026-09-17
submission extensions. It does not overwrite the original predictions.

## What is being measured

1. **Execution-path alignment.** The archived 98% repair result comes from
   `run_benchmark.ours_method`: rules + diagnostic-context generation +
   `constrain_output`. It never invoked `MultiScaleConstraintOptimizer`.
   `replay_optimizer.py` now invokes that exact optimizer on 225 controlled and
   225 natural inputs, with frozen proposals, default constraints/costs, and two
   routing variants. It archives 900 outcomes with trial graphs and decisions.
2. **Matched context × filtering.** A pre-existing 60-document subset (20/domain)
   is fixed for both controlled and natural inputs. Base, diagnostic, and actual
   SHACL contexts share system instructions, source, structural preprocessing,
   Gemma, temperature zero, and a 4,000-token completion cap. Raw and gated
   outputs reuse exactly the same response. New calls never use GPT or Claude.
3. **Closest-work adaptation.** `BASELINE_ADAPTATION.md` documents the M+G
   context strategy of Lin et al. (2025), actual pySHACL validation, and the
   differences from their original setting. It is an adaptation, not official
   code or an exact reproduction.
4. **Natural-error stratification.** All 225 inputs, 215 valid JSON inputs,
   67 imperfect valid JSON inputs, 148 exact inputs, and ten malformed outputs
   are scored separately against silver references.
5. **Routing correction.** The old `graph_features` computed expected relations
   from the reference graph and differed from the runtime's non-isolation
   feature. Old MLP/LODO results are historical, not deployment evidence. The
   replacement deterministic replay uses only observable input violations and
   is explicitly not an online latency benchmark.
6. **Human review.** The original discrepancy sample is preserved. A separate
   blind sample audits actual edits, including harmful edits. Human labels
   remain unfilled. The agreement scorer preserves independent uncertain (U)
   labels and computes kappa before adjudication.

## Reproduce

```bash
# No API; frozen original proposals and actual runtime:
python3 exps/paper1_mechanism_audit/replay_optimizer.py
python3 exps/paper1_mechanism_audit/additional_checks.py
python3 exps/paper1_mechanism_audit/source_field_baseline.py
python3 exps/paper1_mechanism_audit/archive_statistics.py

# Gemma-only; local ignored api file; environment proxy bypassed:
python3 exps/paper1_mechanism_audit/run_api.py --workers 2

# Offline scoring and figure/table generation:
python3 exps/paper1_mechanism_audit/analyze.py
python3 exps/paper1_mechanism_audit/write_paper_tables.py
python3 paper1/make_audit_figures.py
python3 paper1/make_submission_figures.py
cd paper1 && tectonic -X compile main.tex --keep-logs
```

The runner checkpoints all outcomes. Resume never selectively reruns bad JSON or
HTTP failures. New inference functions accept `PublicInput`, which has no gold
tails, gold relation-presence set, or manifest labels. The scorer has separate
access to the reference graphs. The document node is declared task metadata,
materialized from the legacy benchmark storage layout; this is disclosed and
identical across arms.

The locked final run contains 360 requests before transport retries. The
initial 225-document attempt was aborted because of repeated HTTP 429 responses.
All aborted attempts are archived separately and excluded **in their entirety**;
the final subset was the already frozen cross-model subset, not a subset chosen
by quality. The final run globally spaces requests and records every retry,
returned usage field, request fingerprint, and wall time. Input-token counts are
not equal across the three context arms. The first aborted attempt checkpointed
no outcomes, so its total service usage cannot be reconstructed; reported costs
are final-run-only, not the entire session's billed usage.

Regeneration of `human_review` deliberately refuses to overwrite an existing
frozen manifest. Follow its README to coordinate two real independent annotators.
No claims of human-validated graph F1 or acceptance rates are made before that.

## Interpretation

The sequential optimizer is an experimentally audited alternative; its outcomes
must not be replaced by the better one-call pipeline outcomes. If a matched
comparison is null or negative, preserve it. Diagnostic prompting, deterministic
validation, and neural utility selection are distinct mechanisms. A successful
pipeline does not validate every module present elsewhere in the repository.


## Source-format baseline: unresolved submission limitation

A further audit of `build_benchmark.record_to_graph` shows that source evidence
is serialized from the same field values used to define the reference triples.
The gold-free `source_field_baseline.py` reads only the source and declared
schema. It obtains 1.0000 repair/F1/exact match on controlled inputs and 1.0000
F1/exact match on natural inputs, with zero API calls. This result is included
in the manuscript and primary figure; it is not suppressed as an inconvenient
baseline. Therefore neither current protocol establishes superiority of LLM
repair over direct source reconstruction. Independent, unstructured-source
annotations are needed before treating the draft as ready for DMKD submission.
