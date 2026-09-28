# Paper 2: TKDE submission source

Remaining submission work is tracked in [TODO.md](TODO.md).

The active manuscript is `main.tex`, now formatted with `IEEEtran`. It describes an executable Double-DQN co-optimization benchmark and separates three types of evidence:

1. actual graph-state transitions for sequential graph/rule control;
2. stored LLM candidate logs for deletion/augmentation contribution;
3. designed executable cases for rule-family coverage.

The old heuristic look-ahead simulator is not used as RL evidence. Unsupported exploratory cross-domain and rule-mining result tables have been removed from the active manuscript.

Build from this directory with:

```bash
tectonic -X compile main.tex --only-cached --keep-logs
```

The latest compiled manuscript is `main.pdf`. Experiment commands and all output mappings are documented in `../docs/paper2_experiment_reproducibility.md`.

Key result directories:

- `../exps/paper2_cooptimization/`
- `../exps/paper2_dual_strategy_ablation/`
- `../exps/paper2_rule_family_ablation/`
- `../exps/external_benchmark/`
- `../exps/api_llm_extraction_benchmark/`
- `../exps/shacl_baseline/`

## Offline revision (2026-09-24)

The title and RL/dual-strategy main line are retained. The earlier comparisons use
feasible-action baselines, a strong acquire-then-deficit heuristic, and forty
retrained ablation models. The generation analysis adds equal-call comparisons
and directly compiled typed-rule execution with source provenance.

The strong heuristic slightly outperforms Double DQN in that controlled
environment. The hand-implemented family union and actual generated-rule
execution are separate results. Connecting validated generated rules to the RL
registry remains a required next experiment.

- Results and revision summary: `../exps/paper2_offline_revision/report_zh.md`
- One-command offline reproduction: `python3 exps/paper2_offline_revision/reproduce.py`
- Source/code/evidence audit: `../exps/paper2_offline_revision/claim_evidence_audit.md`

## Mathematical revision (2026-09-25)

The corrected environment and new training results are under
`../exps/math_revision_20260925/`. It counts newly introduced violations by
identity and records every reward component. A separate government-typed
archive bridge demonstrates rule activation and constraint-removal decisions.
See `../docs/math_revision_2026-09-25.md` for changes and remaining evidence.

## Reward and repair-behavior validation (2026-09-25; active policy comparison)

The latest study compares three fixed introduced-violation penalties and a
public-observation one-step ridge baseline. It trains 40 neural models plus
10 ridge fits, keeps development and reserved corruption scenarios separate,
and evaluates reference-triple F1, occurrence-level relation restoration,
correct-fact preservation, structural violations and common-reward return.

- Protocol and reproduction: [experiment README](../exps/paper2_reward_validation/README.md)
- Full results and interpretation: [Chinese report](../exps/paper2_reward_validation/report_zh.md)
- Reconstructed-trajectory checks: [verification.json](../exps/paper2_reward_validation/verification.json)
- Current manuscript: [main.pdf](main.pdf)

The main policy tables use the new reserved test. The earlier four component
ablations remain in the appendix under their original count penalty; they were
not retrained under the rate penalty. The new test uses unseen corruptions of
the same base graph. Generated-rule integration, natural errors and new domains
remain separate work in TODO.md.
