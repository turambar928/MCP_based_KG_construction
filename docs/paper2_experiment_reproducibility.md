# Paper 2 Experiment Reproducibility

This note maps the main Paper 2 experiments to the scripts and result artifacts in the repository.

## Main Experimental Blocks

### 1. Rule Generation Quantity and Performance

- Paper section: `paper2/sections/experiments.tex`
- Script source: `exps/paper2_dual_strategy_ablation.py`
- Inputs: stored `per_item_rule_suggestions.jsonl` logs
- Outputs:
  - `exps/paper2_dual_strategy_ablation/report.md`
  - `exps/paper2_dual_strategy_ablation/dual_strategy_ablation.csv`
  - `exps/paper2_dual_strategy_ablation/dual_strategy_ablation.json`

### 2. Rule-Family Final Ablation

- Paper section: `paper2/sections/experiments.tex`
- Script source: `exps/paper2_rule_family_ablation.py`
- Inputs: `data/rule_test_triples.json`
- Outputs:
  - `exps/paper2_rule_family_ablation/report.md`
  - `exps/paper2_rule_family_ablation/results.json`
  - `exps/paper2_rule_family_ablation/summary.csv`

Interpretation:

- This is a deterministic executable rule-family ablation.
- It supports the complementarity claim.
- It is not a per-rule provenance labeling experiment.

### 3. RL Reward/State Ablation

- Paper section: `paper2/sections/experiments.tex`
- Script source: `exps/paper2_rl_reward_state_ablation.py`
- Inputs: fixed-seed simulator
- Outputs:
  - `exps/paper2_rl_reward_state_ablation/report.md`
  - `exps/paper2_rl_reward_state_ablation/results.json`
  - `exps/paper2_rl_reward_state_ablation/summary.csv`

Interpretation:

- This validates the reward/state design under controlled transition dynamics.
- It is not a deployment or LLM-runtime benchmark.

### 4. External Local Benchmarks

- Paper section: `paper2/sections/experiments.tex`
- Script source: `exps/external_benchmark_runner.py`
- Inputs:
  - `data/train.json`
  - `data/rule_test_triples.json`
- Outputs:
  - `exps/external_benchmark/report.md`
  - `exps/external_benchmark/results.json`
  - `exps/external_benchmark/rule_test_predictions_expert.csv`
  - `exps/external_benchmark/rule_test_predictions_system.csv`

### 5. API-Backed LLM Extraction Benchmark

- Paper section: `paper2/sections/experiments.tex`
- Script source: `exps/api_llm_extraction_benchmark.py`
- Inputs: local TNEWS/CLUE sample
- Outputs:
  - `exps/api_llm_extraction_benchmark/report.md`
  - `exps/api_llm_extraction_benchmark/results.json`
  - `exps/api_llm_extraction_benchmark/predictions.csv`

Interpretation:

- This is the only Paper 2 benchmark that makes API calls.
- It measures parsing, category inference, weak entity recall, and quality repair.

### 6. SHACL-Style Structural Baseline

- Paper section: `paper2/sections/experiments.tex`
- Script source: `exps/shacl_baseline/run_shacl_baseline.py`
- Outputs:
  - `exps/shacl_baseline/shacl_results.json`

### 7. Runtime / Cost Accounting

- Paper section: `paper2/sections/experiments.tex`
- Sources:
  - `exps/decision_network/results_summary.md`
  - `exps/decision_network/train_meta.json`
  - `exps/decision_network/efficiency_sim.json`
  - `exps/decision_network/efficiency_real.json`

## Boundary Rules

- `RuleTest-94` is the primary manually verified benchmark.
- Candidate-level ablation is about rule generation diversity, not final detection accuracy.
- Rule-family ablation is about executable coverage of defect families.
- RL reward/state ablation is a simulator validation, not a deployment benchmark.
- Deterministic local benchmarks should be treated separately from API-backed benchmarks.

## Recommended Citation Discipline

- Use `aggregate rule-set recall` for the main rule-performance table.
- Use `domain-level detection recall` for cross-domain results.
- Use `observed precision` for the manually verified set.
- Use `benchmark-suite coverage` for RuleTest-94 and deterministic local benchmarks.

