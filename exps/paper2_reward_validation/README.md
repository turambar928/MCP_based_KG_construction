# Paper2 reward and repair-behavior validation

This is a new offline follow-up. Prior environments, model checkpoints and output hashes remain unchanged. Paper1, credentials and human annotation packages are outside this work.

## Frozen protocol

`training_manifest.json` pins three penalties: raw count (`0.01*N`), initial-size rate (`sum w[k]*new[k]/D[k,0]`), and zero. Only this term changes; graph/rule operators, masks, 14 features, network and all other costs remain unchanged. There is no coefficient search or development-based selection.

The four neural arms are DDQN/count, DDQN/rate, DDQN/zero, and DQN/rate: ten seeds per arm, 250 episodes per seed. Ridge models learn three one-step effects from 250 independent feasible-random episodes per seed; they use only the same 14 observed features and feasibility mask. Ridge alpha is 1, intercept unpenalized, feature scaling fit per action on training data only. Negative cost predictions are clipped to zero. Public reward components supply targets; no reference labels, private relation records or simulator probes enter baseline decisions.

Training seeds are 20000–20009; ridge rollout seeds are 30000–30009. Development uses 920000–920019. Test uses 930000–930029 only after all checkpoints and scoring code have been sealed in `test_manifest.json`. These are unseen corruptions of the same 450-document graph, not unseen documents/domains.

## Commands

Use the existing environment (no installation/download):

```bash
KG_PYTHON=/tmp/kgbench-local-venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
$KG_PYTHON exps/paper2_reward_validation/protocol.py freeze
$KG_PYTHON exps/paper2_reward_validation/test_study.py
$KG_PYTHON exps/paper2_reward_validation/audit.py
$KG_PYTHON exps/paper2_reward_validation/train.py --workers 8
$KG_PYTHON exps/paper2_reward_validation/risk_baseline.py --workers 4
$KG_PYTHON exps/paper2_reward_validation/evaluation.py development --workers 8
$KG_PYTHON exps/paper2_reward_validation/analyze.py development
$KG_PYTHON exps/paper2_reward_validation/protocol.py seal
$KG_PYTHON exps/paper2_reward_validation/evaluation.py test --workers 8
$KG_PYTHON exps/paper2_reward_validation/analyze.py test
$KG_PYTHON exps/paper2_reward_validation/publish.py
$KG_PYTHON exps/paper2_reward_validation/verify.py
tectonic -X compile paper2/main.tex --only-cached --keep-logs
```

Completed training and evaluation blocks are reused; incomplete blocks restart from their fixed seed. To deliberately regenerate completed artifacts, use a separate checkout and move output directories aside. Do not rewrite source manifests to accommodate code changes: create a new version instead. Diagnostic and publication scripts do not alter training or scoring.

## Artifacts and interpretation

- `action_audit.jsonl.gz` branches on the **old** ten scenarios; its privileged probes are diagnostic, not a deployable baseline.
- `training/` has 40 neural checkpoints and histories; `ridge/` has 10 fitted models and their observable training rollouts.
- `development/` holds 1,600 evaluations; `test/` holds 2,400 policy/run/scenario outcomes. Repeated deterministic baselines are not independent observations.
- Initial graphs and stepwise graph deltas allow trajectory reconstruction. Scorer-only labels/fact changes are separate from policy arguments.
- `fact_f1` uses unique exact reference triples, so duplicate occurrence removal does not destroy a retained fact. Illegal-relation restoration requires the original edge identity to regain its reference relation: deletion earns no restoration credit.
- All evaluation returns use the rate penalty. Count and zero counterfactual returns are also saved. Actual API calls and inference-time environment probes are zero.
- Tests average the thirty scenarios within each seed first; ten seed means support paired bootstrap and exact sign randomization. Holm covers four comparators × two primary metrics. Inference is conditional on the fixed scenario set, not a claim of population/domain transfer.

Times New Roman vector PDF/SVG figures and manuscript tables are generated from saved analysis outputs. `report_zh.md` reports all arms, including negative results.

## Completed validation

The 15 focused regression tests passed. Full graph-delta reconstruction checked
all 4,000 evaluation trajectories and 71,817 transitions (28,710 development,
43,107 test), including masks, final reference metrics, residual defects,
reward decompositions and cumulative costs. Frozen training, model, scoring and
legacy-source hashes match. `verification.json` records installed dependencies;
`artifact_manifest.json` hashes the released study files. Figure PDFs embed
Times New Roman and the manuscript builds with cached TeX resources.

On the reserved test, count-penalty DDQN reaches 94.67% triple F1 and restores no
invalid relations. Rate-penalty DDQN reaches 99.49% and 94.00% (both count-rate
contrasts have Holm p=0.015625). Zero-penalty DDQN, ridge and acquire-then-deficit
have higher mean F1 than rate DDQN; those prespecified contrasts do not pass
Holm correction. See the report for uncertainty and all results. The fixed-size
comparison changes effective penalty strength as well as scaling; it does not
establish a normalization advantage across graph sizes.
