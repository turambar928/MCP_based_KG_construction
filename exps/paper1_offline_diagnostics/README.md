# Paper 1 offline selection diagnostics

This is a **post-hoc descriptive analysis** of already evaluated cases. It uses no API, no new model, no new learned parameters, and no human-review files. References remain the same silver labels used by the original study.

The script verifies the frozen ablation dependencies and records its own source hashes before producing results. It reads the losslessly compressed 5,850 optimizer traces and existing proposals, then:

1. Enumerates every subset of each document's per-relation model edit bundles, using the actual runtime edit semantics (including suppression of duplicate additions). An oracle picks the largest reference F1, breaking ties by fewer selected actions and then subset index. Empty subset is allowed. This diagnostic ignores feasibility, utility, stopping and rule-generated actions, so it is an upper bound **only within this fixed model-bundle subset family**. It is not a deployable method or a framework-wide upper bound.
2. Counts initial no-violation graphs that remain imperfect, lack entire reference relations, or already contain a proposal subset that can improve F1. Initial absence of violations differs from stopping after successful edits.
3. Scores each archived trial against references to distinguish useful edits rejected by non-positive utility from feasibility rejection. These counts are trial occurrences, not independent cases.
4. Counts changed outputs and F1 wins/losses for every ablation, pairing by document. It reports cost effects by original domain and by post-preprocessing exactness. No-clean-harm means exact triple equality to the existing reference, not independently adjudicated correctness.
5. Selects illustrative cases deterministically by the first case ID satisfying each stated condition. Complete outputs for all 450 inputs are archived.

Intervals resample whole documents 10,000 times, seed 42. All comparisons are exploratory. No parameters are tuned, and no confirmatory significance claims are made.

```bash
python3 -m unittest exps.paper1_offline_diagnostics.test_oracle
python3 exps/paper1_offline_diagnostics/analyze.py
python3 exps/paper1_offline_diagnostics/publish.py
```

See [report.md](report.md), [results.json](results.json), [cost_strata.csv](cost_strata.csv), and [variant_summary.csv](variant_summary.csv). The analysis script refuses silent edits to its own hash or its inputs after the manifest has been created.
