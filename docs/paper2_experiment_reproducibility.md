# Paper 2 Experiment Reproducibility

The submission source is `paper2/main.tex`. The experiments in that source map to the following artifacts.

## Co-optimization benchmark

- Runner: `exps/paper2_cooptimization/run_experiment.py`
- Input: `data/train.json`
- Formal command: `python3 exps/paper2_cooptimization/run_experiment.py --seeds 10 --episodes 250 --per-label 30`
- Environment: 450 TNEWS/CLUE documents, 873 clean nodes, 1,083 clean relations, four seed-varying controlled defect families, a fixed 180-case rule-validation inventory, eight executable actions, and an 18-step budget
- Learned methods: DQN and Double DQN with independent training for each of ten seeds
- Baselines: random, enhancement only, rule only, alternating, rule-first-then-fix, fix-first-then-rule, and model-informed one-step greedy
- Training API calls: zero
- Runtime: 1,278.99 seconds on CPU

Primary outputs:

- `results.json`: configuration, fixed seeds, statistical tests, summaries, and per-seed records
- `per_seed_results.csv`: paired policy outcomes
- `transitions.csv`: all 1,616 evaluation transitions as `(s,a,r,s',done)` plus graph/rule diagnostics
- `training_history.csv`: 5,000 episode summaries
- `checkpoints/`: ten DQN and ten Double-DQN checkpoints
- `summary.csv`, `report.md`, and PDF/PNG curves

Double DQN versus the strongest non-oracle schedule has a final-quality difference of 0.0065 (95% paired-bootstrap CI [0.0058, 0.0071]) and AUC difference of 0.0166 ([0.0156, 0.0178]); one-sided paired Wilcoxon `p=0.0009765625` for both. The model-informed greedy policy is an upper-bound diagnostic because it clones the environment and evaluates every feasible one-step transition.

## Stored rule-generation ablations

- Candidate replay: `exps/paper2_dual_strategy_ablation.py`
- Full log: 4,728 deletion and 4,728 augmentation calls, all successful
- Full-log candidate counts: 32,955 deletion; 41,683 augmentation; 71,656 union
- Dual gain over the stronger single strategy: 71.9%
- Outputs: `exps/paper2_dual_strategy_ablation/`

- Executable family ablation: `exps/paper2_rule_family_ablation.py`
- Input: `data/rule_test_triples.json`
- Outputs: per-case predictions, confusion matrices, and report in `exps/paper2_rule_family_ablation/`

RuleTest-94 is a designed suite: 30 clean and 64 defective cases. It establishes coverage of the included executable families, not open-world precision or natural defect prevalence.

## External benchmarks

- Deterministic TNEWS and RuleTest runner: `exps/external_benchmark_runner.py`
- SHACL-style baseline: `exps/shacl_baseline/run_shacl_baseline.py`
- API extraction runner: `exps/api_llm_extraction_benchmark.py`

The API runner reads `api`, appends `/v1`, and uses an HTTP client with `trust_env=False` so a server-local proxy cannot intercept the request. The formal run used 45 calls to `Qwen3.8-27B-no-thinking`: parse success 1.000, category accuracy 0.556, weak keyword recall 0.178, and structural quality 100.00 before and after filtering. The no-op repair result is retained as observed.

## Evidence boundaries

The paper no longer reports exploratory cross-domain recall, AMIE/RuDiK/neural-rule scores, the old 80.7 RL score, 37.5% convergence claim, or the simulator reward ablation as main evidence. Those values lack held-out cases, per-case predictions, or real Double-DQN training artifacts. Direct cross-domain and rule-mining comparisons require new labeled sets and archived predictions before they can return to the submission.
