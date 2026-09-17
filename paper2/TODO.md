# Paper 2 TKDE Submission TODO

Updated: 2026-09-17

This file records the remaining work required before submitting Paper 2 to
*IEEE Transactions on Knowledge and Data Engineering* (TKDE). Completed
controlled experiments should not be rerun unless a code or data change makes
their archived results invalid.

## Current evidence

- [x] Implement executable DQN and Double DQN policies with replay memory,
  target networks, action masking, saved checkpoints, and per-transition logs.
- [x] Evaluate DQN and Double DQN over 10 random seeds and archive confidence
  intervals and paired tests.
- [x] Rerun the API extraction experiment with 45 real calls and report the
  observed no-op repair result without manufacturing an improvement.
- [x] Rerun RuleTest-94, dual-strategy, external benchmark, and SHACL
  experiments from their executable scripts.
- [x] Align the rule counts, figures, tables, and manuscript claims with the
  archived outputs.
- [x] Convert the manuscript to IEEEtran and produce a reproducible 14-page
  PDF.

## P0: required before submission

### 1. Validate naturally occurring graph defects

- [ ] Select one public or independently constructed KG that contains natural
  errors rather than injected corruptions.
- [ ] Freeze the sampling procedure before inspecting system outputs.
- [ ] Sample 200--300 detected cases across type, relation, hierarchy,
  duplication, and missing-fact categories.
- [ ] Create annotation instructions that distinguish detection correctness,
  proposed-repair correctness, and acceptable alternative repairs.
- [ ] Have at least two annotators independently label a shared subset.
- [ ] Report agreement (Cohen's kappa or Krippendorff's alpha), precision by
  defect category, repair acceptance rate, and confidence intervals.
- [ ] Archive the sampled cases, labels, adjudication decisions, and sampling
  manifest.

**Acceptance criterion:** the paper can support a real-data claim without
using RuleTest-94 or the controlled 180-case inventory as evidence of natural
error prevalence.

### 2. Add runnable external and simple-pipeline baselines

- [ ] Run one established rule-mining or KG-repair method, preferably AMIE+,
  AnyBURL, or another method whose inputs and outputs can be aligned fairly.
- [ ] Add an LLM-only baseline using the same source text, model, schema, and
  token budget as the proposed system.
- [ ] Add a strong simple pipeline: deterministic preprocessing, the same LLM
  call, and minimal deterministic postprocessing, without the graph profile or
  learned policy.
- [ ] Keep the existing SHACL-only and fixed-policy baselines.
- [ ] Report quality, invalid-edit rate, calls, tokens, latency, and peak
  memory under a shared evaluation protocol.
- [ ] Archive exact baseline commands, versions, prompts, and predictions.

**Acceptance criterion:** every headline comparison uses either the same model
and budget or explicitly reports the resource difference.

### 3. Isolate the contribution of the learned policy

- [ ] Compare full Double DQN with DQN, a fixed policy, a random valid-action
  policy, a heuristic policy, and the model-informed myopic upper bound.
- [ ] Run `w/o graph profile`, `w/o action mask`, and `fixed reward` ablations.
- [ ] Report final quality, trajectory AUC, invalid actions, online environment
  probes, calls, latency, and across-seed variance.
- [ ] Explain that the myopic policy clones the environment and enumerates
  one-step transitions, so it is an upper bound rather than a deployable
  baseline.
- [ ] Avoid claiming that Double DQN has the highest absolute quality when the
  model-informed upper bound is higher.

**Acceptance criterion:** the paper demonstrates which profile, constraint,
and Double-DQN components produce measurable gains over simpler policies.

## P1: strong additions if time permits

### 4. Measure scalability and incremental-update cost

- [ ] Evaluate at approximately 1K, 5K, 10K, and 50K triples.
- [ ] Vary graph density separately from graph size where possible.
- [ ] Measure profile construction, rule checking, policy inference, repair,
  peak memory, and API calls.
- [ ] Compare incremental profile updates with full-graph recomputation.
- [ ] State the largest graph size supported by the current implementation.

### 5. Strengthen semantic extraction evaluation

- [ ] Manually annotate 50--100 documents for entities, relations, and triples.
- [ ] Report entity-, relation-, and triple-level precision, recall, and F1.
- [ ] Review whether category accuracy and keyword recall use overly strict
  exact matching; freeze any normalization before rerunning evaluation.
- [ ] Include entity normalization and acceptable synonym handling in the
  annotation protocol.

### 6. Test model and domain robustness

- [ ] Repeat a fixed evaluation subset with at least one Qwen-family model and
  one GPT- or Claude-family model.
- [ ] Use identical prompts, decoding settings, schemas, and retry rules.
- [ ] Add leave-one-domain-out evaluation if the datasets permit it.
- [ ] Report performance by unseen relation type as well as by domain.

## P2: manuscript and release preparation

- [ ] Center the contribution statement on multi-scale constraints, the graph
  profile interface, and budget-aware sequential repair.
- [ ] Keep controlled suites explicitly labeled as controlled validation.
- [ ] Match every numerical statement to an archived machine-readable output.
- [ ] Add Code Availability and Data Availability statements with an anonymous
  repository URL for review.
- [ ] Provide one top-level reproduction command and an environment lock file.
- [ ] Check IEEE figure fonts, grayscale legibility, table widths, references,
  author metadata, and supplementary-material references.
- [ ] Perform a final claim-to-evidence audit before submission.

## Recommended execution order

1. Natural-defect sample and annotation protocol.
2. External method and strong simple-pipeline baselines.
3. Double-DQN/profile/action-mask ablations.
4. Scalability and incremental-update experiment.
5. Semantic annotation and cross-model robustness.
6. Final TKDE narrative, availability statements, and submission package.

