# Paper 1 Method–Implementation Audit

Updated: 2026-09-17

## Current formulation

Paper 1 is formulated as a profile-conditioned constrained sequential decision problem.
The operational method consists of:

1. a four-dimensional quality profile
   `[Q_conn, Q_uniq, Q_logic, Q_sem]`;
2. an eight-dimensional router input that appends
   `[|V|, |E|, projected density, violation count]`;
3. a supervised neural router that predicts a repair trigger and a soft prior over
   entity, graph, and context scales;
4. typed candidate graph transformations proposed by deterministic rules,
   source-grounded modules, or LLM reasoning;
5. complete trial-graph assessment, restoration-aware feasibility checks, and
   highest-utility one-step selection;
6. re-assessment and re-planning after each committed action.

The active paper sources are:

- `paper1/sections/overview.tex`
- `paper1/sections/implementation.tex`

## Resolved consistency issues

| Earlier issue | Current resolution |
| --- | --- |
| Overview listed nine metrics while runtime used four | Operational profile is explicitly four-dimensional; auxiliary graph statistics are separated from optimized quality dimensions |
| Global graph optimizer wording exceeded the implementation | Method is a finite-horizon sequential objective solved by receding-horizon candidate evaluation; no global optimum is claimed |
| Strict lower bounds blocked recovery from an initially infeasible graph | Restoration boundary preserves feasible dimensions and requires deficient dimensions not to deteriorate |
| Density used raw multigraph edge count | Density now uses the loop-free simple directed projection and remains in `[0,1]` |
| Redundant-pair count divided by edge count could exceed one | Redundancy is the removable fraction induced by connected components of the triple-similarity graph |
| Multiple logical violations on one edge inflated the rate | Logical conflict is the fraction of triples with at least one violation |
| Empty graph received perfect connectivity | Empty-graph connectivity is defined as zero |
| LLM semantic mean was conflated with runtime checking | Corpus-level LLM evaluation and deterministic online source-support proxy are defined separately |
| Claimed incremental update was not implemented | Paper states complete trial-graph reassessment and gives its conservative complexity |
| Repair labels were described as constraint-checker labels | Labels are explicitly defined from controlled corruption provenance |
| Runtime threshold differed from validation threshold | Both use `tau_repair = 0.05` |
| Utility equation omitted implementation terms | Paper and runtime now include quality gain, hard-violation reduction, intervention cost, scale prior, and proposal confidence |
| Runtime scanned candidates in a fixed order | Runtime evaluates all current candidates, commits the best feasible positive-utility action, and re-plans |

## Why Paper 1 is not labelled as reinforcement learning

The router in `exps/decision_network/train_fphi.py` is trained with BCE and masked
cross-entropy from paired clean/corrupted examples. It is not trained from transition
tuples, discounted returns, Bellman targets, policy gradients, or online interaction.
Calling this component DQN or reinforcement learning would therefore be unsupported.

The earlier RL formulation jointly optimized graph quality and rule-set quality. That
topic belongs to Paper 2's rule–graph co-optimization scope. Paper 1 instead uses a
constrained neural policy: it retains explicit state, action, transition, reward-like
utility, and finite-horizon semantics, while accurately identifying its learning signal
as synthetic supervised data and its online solver as receding-horizon constrained
search.

## Validation

- `python3 -m py_compile content_enhancement/constraint_optimizer.py`
- targeted optimizer and decision-data tests: 8 passed
- active LaTeX labels and references: no duplicates or unresolved references
- `tectonic --keep-logs --keep-intermediates main.tex`: successful, 27-page PDF

The remaining TeX messages are layout underfull-box warnings and a pre-existing
encoding warning from `algorithm.sty`; there are no undefined citations, unresolved
references, overfull boxes, or compilation errors from the revised method.
