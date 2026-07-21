# Paper 2 Revision Plan

This README records the next revision steps for Paper 2: *Reinforcement Learning for Knowledge Graph Co-optimization: A Dual-Strategy Rule Generation Framework*.

## Current Status

The paper already has a clear core idea:

- RL is used as a meta-policy to decide when to enhance the graph and when to generate/refine rules.
- Dual-strategy LLM rule generation combines deletion completion and augmentation expansion.
- Experiments report rule-generation gains, RL strategy ablation, cross-domain transfer, baseline comparison, and failure analysis.

Recent consistency fixes have been applied:

- RL reward/state now use `Q_online(R)` instead of an ambiguous `Q(R)`.
- Offline rule quality is separated as `Q_eval(R)`, with `Unique(R)` treated as a post-hoc metric.
- LLM backbone is consistently described as Qwen-32B.
- Over-strong claims about 100% precision, small-sample reliability, and cross-domain generalization have been softened.
- The `156 hierarchical rules` inconsistency was corrected to match the experiment table: 31 hierarchical rules and 88 procedural rules.

## Completed in Current Pass

- Added an evaluation-pool table that separates the 94-case primary verified set, domain held-out sets, and the 150-case auxiliary failure-analysis pool.
- Added baseline protocol text explaining how AMIE, RuDiK, and Neural Rule Learning are adapted and what information they do not receive.
- Added a rule materialization and validation subsection explaining how LLM constraints become structured executable rules.
- Added a running example from generated value constraint to detected KG violation.
- Added and ran `exps/paper2_dual_strategy_ablation.py`, producing candidate-level deletion/augmentation/dual ablation results from stored LLM generation logs.
- Added and ran `exps/external_benchmark_runner.py`, producing a local external benchmark report on TNEWS/CLUE KG quality enhancement and RuleTest-94 rule detection.
- Renamed cross-domain evaluation as seed-rule transfer rather than broad zero-shot generalization.
- Reduced remaining overclaims such as "first framework", "full range", and "fundamentally solving".

External benchmark outputs:

- `exps/external_benchmark/report.md`
- `exps/external_benchmark/results.json`
- `exps/external_benchmark/rule_test_predictions_system.csv`
- `exps/external_benchmark/rule_test_predictions_expert.csv`

## Priority 1: Must Fix Before Submission

### 1. Clarify Dataset and Evaluation Protocol

Status: largely completed in `experiments.tex`. Remaining work is to verify whether the domain held-out set sizes can be disclosed.

Problem:

- The paper uses 94 manually annotated cases as the primary evaluation set.
- Cross-domain recall values are much higher than the aggregate rule recall in the main performance table.
- Failure analysis uses an additional 150 undetected defects from development runs.

Revision plan:

- Add a compact table in the experiment setup that distinguishes:
  - primary manually verified test set: 94 cases;
  - cross-domain held-out cases: domain-specific evaluation pool;
  - auxiliary failure-analysis pool: 150 sampled undetected defects from development runs.
- Explicitly state which tables use which evaluation pool.
- Avoid describing all recall values as the same metric. Use names such as:
  - `aggregate rule-set recall` for Table `rule_performance`;
  - `domain-level detection recall` for Table `cross_domain`.

### 2. Strengthen Baseline Fairness Description

Status: partially completed in `experiments.tex`. Remaining work depends on whether baseline numbers are from reimplementation, adapted runs, or literature references.

Problem:

- AMIE, RuDiK, and Neural Rule Learning are listed as baselines, but the paper does not fully explain how they were run or adapted to quality-rule detection.
- Reviewers may question whether the comparison is fair because these methods were designed for structural rule mining, not source-text-aware quality constraints.

Revision plan:

- Add a paragraph before the baseline table:
  - input given to each baseline;
  - how mined rules are mapped to the four defect types;
  - same test set and same precision/recall calculation;
  - limitations of baselines due to lack of source-text access.
- If the baseline numbers are from reimplementation, say so.
- If any numbers are literature-reported or estimated, do not present them as direct apples-to-apples results.

### 3. Make Rule Generation Pipeline More Executable

Status: completed at the method-description level in `methodology.tex`. Remaining work is to ensure code/released artifacts match the described JSON fields and validation thresholds.

Problem:

- The method still contains abstract steps such as `Compare`, `MineCommonPatterns`, `SynthesizeRule`, and subsumption checking.
- Reviewers need to understand how LLM text output becomes executable quality rules.

Revision plan:

- Add a short subsection after the two generation algorithms:
  - LLM output is parsed into JSON rule records.
  - Rules are normalized into four types: `attr_required`, `rel_type`, `value_constraint`, `order_constraint`.
  - Low-confidence rules are filtered by frequency/support thresholds.
  - Candidate rules are validated on clean/defective cases before entering the rule set.
  - Deduplication is applied after validation.
- Include one complete example from text -> LLM constraint -> JSON rule -> detected violation.

### 4. Add Statistical Details for Reported Significance

Status: partially completed for McNemar's test wording. Still needs exact p-values or a conservative replacement if exact values are unavailable.

Problem:

- The paper reports `p < 0.01`, but the test statistic, paired samples, and compared outputs are not described.

Revision plan:

- For RL ablation:
  - report the paired seeds used for the t-test;
  - compare RL dynamic selection against the best heuristic baseline.
- For rule-detection comparison:
  - clarify that McNemar's test is computed over paired per-case detection outcomes.
- Add exact p-values if available. If not, replace `p < 0.01` with a more conservative statement.

## Priority 2: Strongly Recommended

### 5. Add Dual-Strategy Ablation

Status: completed at the candidate-rule contribution level. Outputs are in `exps/paper2_dual_strategy_ablation/`; the main text now reports the 20-item controlled log plus full-log robustness. Final precision/recall by strategy still requires the missing manually annotated 94-case labels.

Problem:

- The paper claims deletion completion and augmentation expansion are complementary, but experiments do not isolate their contributions.

Revision plan:

- Add one ablation table:

| Method | Rules | Precision | Recall | Coverage | Unique |
| --- | ---: | ---: | ---: | ---: | ---: |
| Deletion only | TBD | TBD | TBD | TBD | TBD |
| Augmentation only | TBD | TBD | TBD | TBD | TBD |
| Dual strategy | 294 | 1.000 | 0.269 | 1.000 | 0.400 |

- If there is no time to rerun, add this as a limitation/future experiment rather than fabricating values.

### 6. Add Reward/State Ablation

Status: not fully runnable from the current repository. The paper already contains reward-weight sensitivity in the appendix, but a true graph-only/rule-only/state-component DQN ablation requires either the original DQN training environment/logs or a recreated simulator.

Problem:

- The paper says `Q_online(R)` is important, but there is no ablation showing what happens when rule quality is removed or weakened.

Revision plan:

- Add variants:
  - graph-only reward: `Q(G)`;
  - rule-only reward: `Q_online(R)`;
  - joint reward without coverage;
  - full reward.
- Report convergence episode and final joint quality.

### 7. Clarify Cost and Efficiency

Problem:

- The method uses LLM calls and RL training, so reviewers will ask whether the gains justify the cost.

Revision plan:

- Add a small cost table:
  - number of LLM calls per domain;
  - average rule-generation time;
  - RL training time;
  - estimated API cost;
  - cost reduction from caching or rule reuse if available.
- Compare RL dynamic selection with fixed strategies on number of actions/LLM calls until convergence.

### 8. Improve Cross-Domain Transfer Explanation

Status: partially completed by renaming the section and clarifying seed-rule transfer. A no-transfer baseline still requires additional experiment data.

Problem:

- Finance and Environment use 20 transferred government rules, so the setting is not pure zero-shot transfer.

Revision plan:

- Rename the subsection from broad "Cross-Domain Generalization" to "Cross-Domain Transfer with Seed Rules".
- Explain why government rules can transfer.
- Add a no-transfer baseline if available:
  - with 20 seed rules;
  - without transferred seed rules.

## Priority 3: Polish and Risk Reduction

### 9. Reduce Overclaiming in Novelty

Status: largely completed in the main text. Continue checking future edits for absolute wording.

Problem:

- Phrases such as "fundamentally solving" or "first RL framework" may be challenged.

Revision plan:

- Replace absolute claims with defensible wording:
  - "addresses" instead of "solves";
  - "to our knowledge, among the first" instead of "first";
  - "observed precision" instead of "maintains precision".

### 10. Make Terminology Consistent

Use these terms consistently:

- `Q(G)`: graph quality.
- `Q_online(R)`: online rule quality used in RL state and reward.
- `Q_eval(R)`: offline rule evaluation score including `Unique(R)`.
- `aggregate rule-set recall`: Table `rule_performance`.
- `domain-level detection recall`: Table `cross_domain`.
- `observed precision`: precision measured on the manually verified set.

### 11. Add Reproducibility Details

Problem:

- Some hyperparameters are present, but random seeds, exact splits, and rule-validation implementation are not fully specified.

Revision plan:

- Add:
  - random seeds;
  - train/dev/test split policy;
  - LLM decoding settings;
  - rule-validation thresholds;
  - whether LLM outputs were manually filtered.

### 12. Add Error Examples in a Compact Table

Problem:

- Failure analysis is mostly textual.

Revision plan:

- Add a table with columns:
  - domain;
  - missed defect;
  - expected rule;
  - system output;
  - failure category;
  - planned fix.

## Items Not Covered Here

The following are LaTeX or Overleaf-side issues and are intentionally not handled in this revision plan:

- missing or mismatched image filenames;
- package imports for `algorithm`, `algorithmic`, or custom macros;
- template-specific keyword environment issues;
- figure placement and final formatting.

## Recommended Revision Order

1. Fix dataset/evaluation protocol description.
2. Add baseline fairness paragraph.
3. Make the LLM-to-rule pipeline executable and concrete.
4. Add or conservatively qualify statistical significance.
5. Add dual-strategy and reward ablations if experimental resources are available.
6. Polish novelty claims and terminology after the technical sections are stable.
