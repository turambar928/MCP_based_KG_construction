# Offline mathematical revision, 2026-09-25

This directory contains versioned corrections for both manuscripts. No API calls or model downloads are required. It does not overwrite frozen prior experiments or human annotation data.

## Run

Use the existing local environment with NumPy, Pandas, PyTorch, SciPy and Matplotlib. In this workspace:

```bash
KG_PYTHON=/tmp/kgbench-local-venv/bin/python
$KG_PYTHON exps/math_revision_20260925/reproduce.py verify
$KG_PYTHON exps/math_revision_20260925/reproduce.py replay
$KG_PYTHON exps/math_revision_20260925/reproduce.py publish
```

Retraining is explicit:

```bash
$KG_PYTHON exps/math_revision_20260925/reproduce.py train --workers 4
```

Paper2 skips completed runs. To train again from scratch, copy the experiment to a separate checkout and move its `paper2/training` outputs aside first. Completed checkpoints are never silently overwritten. Interrupted runs without `complete.json` restart from their fixed seed. Publication requires the locally cached Tectonic bundle and Times New Roman; no fallback font or network fetch is requested.

## Paper1

- `paper1/input_contract.json` describes the public input migration, eight shared features, fixed prior comparisons and input hashes.
- `paper1/public_inputs.jsonl.gz` contains the actual public graph inputs; no reference relations/tails or defect labels appear as extra features.
- `paper1/router/` contains the shared-profile dataset, train/validation/test partitions, checkpoint, versioned scaler, training settings, predictions and calibration metrics.
- `paper1/optimizer_traces.jsonl.gz` contains 1,800 fixed-candidate outcomes including trial graphs, profiles and decisions. `results.json` and `optimizer_per_case.csv` retain scores and exploratory paired comparisons.
- Original absolute-log utility remains the runtime default. Relative-to-uniform utility is a predefined sensitivity comparison, not selected as best on the reused tests.
- Feature-version mismatch rejects old checkpoints with an explicit uniform fallback. Production callers can supply `TaskContext`; omitted entity types use an open-world interpretation.

## Paper2

- `paper2/environment.py` counts introduced violations by stable identity, protects against empty-graph edits, records reward decomposition and handles empty action sets.
- `paper2/policy_manifest.json` freezes environment/trainer sources and seeds before training.
- `paper2/training/` contains 60 completed models: DQN, DDQN and four ablations, ten seeds each, 250 episodes per seed.
- `paper2/policy_results.json` and `policy_transitions.jsonl` retain all 110 evaluations; `policy_analysis.json` contains paired statistics and reward-invariant verification.
- `paper2/rule_bridge.py` demonstrates exact generated-rule activation, detection, feasibility changes and record removal on the same previously inspected government-typed suite. It is separate from TNEWS scheduling and does not train an additional policy.
- The bridge keeps unsupported/conflict/no-match outcomes. Removing a prohibited record is not inferred factual restoration; no labels enter runtime decisions.

## Interpretation and preservation

The Paper1 candidates and Paper2 evaluation scenarios were previously observed. The new outputs are corrected execution and retraining results, not new held-out generalization evidence. All accounted model calls in Paper2 are environment cost units; actual requests equal zero. Completed-run wall times exclude discarded partial runs and are not end-to-end LLM latency.

`test_revision.py` covers behavioral counterexamples, input isolation, all-row feature agreement and unchanged legacy hashes. `manifest.json` records current source fingerprints and archived artifact hashes. `reproduce.py verify` checks source integrity and behavioral tests; timing-sensitive output bytes need not match after replay.

The Chinese explanation is in [the revision report](../../docs/math_revision_2026-09-25.md). The original mathematical audit remains a historical snapshot.
