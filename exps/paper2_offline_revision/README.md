# Paper2: offline revision study

This study preserves the RL graph–rule co-optimization and dual-strategy
rule-generation design. It makes **zero API calls** and downloads no models.
Original source, checkpoints, and historical experiments remain unchanged.

## Reproduce from the repository root

```bash
python3 exps/paper2_offline_revision/reproduce.py
```

This verifies the seven focused unit tests, evaluates archived checkpoints,
replays stored candidates, regenerates tables/figures, and checks the results.
It requires the source data and rule log already present in this repository.
`requirements-offline.txt` records the exact installed direct dependencies;
`environment.json` records the platform and package versions. Install dependencies
in a separate environment only if missing; no installation is part of this runner.
Times New Roman must be installed to reproduce the figure typography.

To resume any missing ablation training:

```bash
python3 exps/paper2_offline_revision/reproduce.py --train --workers 4
```

The 40 completed runs are cached under `training/`. To train from scratch, use a
separate checkout and move that directory aside there. Each variant uses ten
seeds and 250 episodes. Four CPU worker processes took approximately 11 minutes
in the recorded environment. Training times are measurements, not reproducible
constants. Checkpoints store weights and configuration, not optimizer state for
mid-episode resumption.

Build the paper separately:

```bash
cd paper2
tectonic -X compile main.tex --keep-logs
```

## Policy design and interpretation

- Frozen source/configuration: `policy_manifest.json`. Training and evaluation
  fail if the frozen runner, tests, analyzer, original environment, original
  results, source data, or original checkpoints change.
- New baselines: random-valid, alternating-valid, rule-first-valid, and a fixed
  acquire-then-deficit heuristic. All receive the same observation and mask.
- New retrained variants: no explicit graph features, no explicit rule features,
  no behavioral/Bellman action mask, and no call penalty during training.
- Every evaluation uses the original reward/cost and an 18-step horizon.
  Trapezoidal AUC carries terminal quality to step 18. The historical
  duration-normalized AUC is retained only in its original archive.
- Ten existing scenarios, not ten new held-out graphs. A training seed is paired
  with one evaluation scenario; the bootstrap resamples these pairs.
- Exact two-sided sign randomization uses all 1,024 assignments. Ten planned
  contrasts share a Holm correction. Bootstrap intervals are pointwise.
- The mask conveys information about feasible rule/graph operations even when
  explicit features are removed. These ablations do not remove all implicit
  knowledge of rule availability or graph defects.
- Accounted calls are simulated acquisition units; actual API requests are zero.
  Local evaluation time excludes environment construction and includes transition
  execution; lookahead also includes cloned probes. It is not model latency.
- `model_informed_lookahead` is an information-advantaged one-step comparator,
  not a mathematical upper bound.

The strong heuristic slightly outperforms Double DQN. Rule features improve both
reported metrics after correction. Action masking improves final quality; its
AUC contrast does not survive correction. The graph-feature and call-penalty
contrasts do not independently establish gains.

## Rule design and interpretation

`rule_manifest.json` freezes the inputs, explicit-label mapping, exact execution
semantics, budgets, and sampling seeds. At B calls, single-strategy sampling covers
B documents; dual sampling covers B/2 documents twice. Thirty seeded permutations
of the same paired-document inventory describe sampling spread, not independent
experimental replications. Counts separate type declarations from constraints.

`candidate_execution_audit.jsonl.gz` retains all 181,851 candidate occurrences.
`rule_lineage.jsonl.gz` connects 18,143 compiled patterns to source lines and
candidate positions. Only exact allowed/forbidden subject-type/relation/object-type
triples are compiled, trimming outer whitespace. Other families remain in the
archive; no semantic rewrites are inferred. Unseen allowed patterns do not reject
a case. Simultaneous permission and prohibition abstain and retain the case in
scoring. Each of the three strategy results scores all 94 cases.

Labels come from `expected_detection`: `pass` is negative; `fail` and
`specialist_miss` are positive. These are designed suite labels, not independently
collected human annotations. The hand-implemented family detectors are rescored
with these stored labels in `family_label_check.csv`. Their 64/64 detection must
not be substituted for the generated union's 10/64 detection.

A unit test exposed undefined specificity for a toy all-positive input. The fix
returns null for undefined metric denominators. The pre-fix manifest and
`rule_scoring_correction.json` record that change; the formal RuleTest-94 output
is SHA-identical before and after the correction.

## File map

| Files | Purpose |
|---|---|
| `policy_study.py`, `analyze_policy.py` | Frozen training, evaluation, paired inference |
| `training/*/{checkpoint.pt,history.csv,complete.json}` | Forty completed runs |
| `policy_results.json`, `policy_transitions.jsonl` | 110 outcomes and full transitions |
| `policy_summary.csv`, `policy_comparisons.csv` | Summaries and paired tests |
| `baseline_*` | Early baseline-only scoring archive |
| `rule_study.py`, `budget_*.csv` | Equal-call candidate comparisons |
| `rule_execution.csv`, `rule_case_predictions.csv` | Direct execution results |
| `family_label_check.csv` | Separate hand-implemented detectors |
| `prompts/` | Literal current templates, translations, and hashes |
| `make_tables.py`, `make_figures.py` | Publication artifacts from result JSON |
| `verify.py`, `verification.json` | Completeness and scoring checks |
| `report_zh.md` | Results and revision summary in Chinese |
| `claim_evidence_audit.md` | Manuscript/code/evidence mapping and remaining gaps |

This completes the offline follow-up, not the missing integration of generated
rules into the RL registry. See `paper2/TODO.md` for the remaining experiments.
