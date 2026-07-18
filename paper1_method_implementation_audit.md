# Paper1 Method and Implementation Audit

## 中文总览：第三、四章公式与实现对应关系

下表按论文第三章、第四章中出现的主要公式逐一说明其含义、对应项目模块，以及当前实现是否与论文表述一致。

| 公式/定义 | 论文含义 | 对应模块/文件 | 当前实现吻合度 | 需要修改或说明 |
| --- | --- | --- | --- | --- |
| `quality_profile`: `P=[p_ent^T,p_graph^T,p_ctx^T]^T` | 将实体尺度、图尺度、上下文尺度的质量指标拼成统一质量画像 | `exps/*_evaluate.py`, `exps/decision_network/build_dataset.py`, `content_enhancement/constraint_optimizer.py` | 基本吻合 | 运行时已使用 `[S_iso,S_red,S_log,S_sem,n_v,n_e,density,n_viol_feat]`；论文中更宽的候选指标仍属于扩展画像 |
| `constrained_opt`: `max w^T P(G') s.t. L<=P(G')<=U` | 在质量上下界约束下最大化加权质量得分 | `content_enhancement/constraint_optimizer.py`, `content_enhancement/enhancement_executor.py` | 基本吻合 | 当前实现为候选动作级贪心优化和约束门控，不是全局精确求解器 |
| `Q_conn=100(1-r_iso)` | 孤立节点越少，连通性质量越高 | `detect_isolated_nodes()` in `exps/pol_evaluate.py`, `exps/finance_evaluate.py`, `exps/env_evaluate.py` | 吻合 | 已实现，空图边界也有处理 |
| `Sim(t1,t2)` | 用三元组主语、关系、宾语 embedding 相似度判断近重复 | `content_enhancement/constraint_optimizer.py` | 部分吻合 | 运行时已实现 weighted character n-gram cosine 作为无依赖语义近似；实验评估脚本仍主要使用 exact hash |
| `Q_uniq=100(1-r_red)` | 冗余三元组越少，唯一性质量越高 | `detect_redundant_triples()` in `exps/*_evaluate.py`; `MultiScaleConstraintOptimizer._redundant_pairs()` | 基本吻合 | 运行时支持近重复检测；历史实验评估仍是 exact/heuristic 口径 |
| `Q_logic=100(1-r_log)` | 逻辑冲突越少，逻辑一致性越高 | `check_logical_consistency()` in `exps/*_evaluate.py` | 基本吻合 | 建议代码中对冲突率做 `min(1, rate)` 截断，防止节点级冲突过多时超过 1 |
| `Q_sem=(100/K) sum s_k` | 抽样三元组经 LLM/评审器打分后的平均语义合理性 | `evaluate_semantic_consistency()` in `exps/*_evaluate.py`; reliability scripts | 基本吻合 | 论文中固定 `K=50` 的说法需要和实际脚本抽样策略统一 |
| Incremental complexity | 局部图更新后只重算受影响 k-hop 邻域，降低复杂度 | `MultiScaleConstraintOptimizer.optimize_and_apply()` | 部分吻合 | 已实现候选动作后的 bounded local re-assessment；还不是持久化图索引级增量缓存 |
| `decision_net`: `(p_repair,pi)=f_phi([s;g])` | 神经网络判断是否修复，并预测实体/图/上下文缺陷尺度 | `exps/decision_network/train_fphi.py`; `FphiRouter` in `constraint_optimizer.py` | 吻合 | 已训练、已加载、已作为运行时 repair/scale router 使用 |
| `repair_label` | 存在硬违规或质量低于阈值则标记为需要修复 | `exps/decision_network/build_dataset.py` | 概念吻合 | 代码根据 clean/dirty 和注入缺陷来源生成标签，不是直接计算公式 |
| `scale_label` | 根据实体/图/上下文违规数量得到尺度分布 | `exps/decision_network/build_dataset.py` | 基本吻合 | 代码按注入缺陷类型映射尺度并归一化 |
| `decision_loss` | 修复二分类 BCE + 尺度预测 CE | `exps/decision_network/train_fphi.py` | 部分吻合 | 论文写软标签分布；代码实际用 dominant class 的 hard-label CE |
| `action_utility` | 候选修复动作的收益、成本和尺度先验综合打分 | `MultiScaleConstraintOptimizer._utility()` | 吻合 | 已在每个候选动作/动作 bundle 提交前计算 |
| `cost_hierarchy` | 删除成本最高，重类型其次，补全最低 | `MultiScaleConstraintOptimizer.costs` | 基本吻合 | 已实现 delete > retype > complete/add；bundle 使用组合成本 |

## 中文总览：第三、四章算法含义与实现状态

| 算法 | 论文中作用 | 项目对应实现 | 当前状态 | 建议 |
| --- | --- | --- | --- | --- |
| Abstract Constraint-Driven KG Enhancement | 总体闭环：评估质量、检测违规、选择动作、检查约束、应用修复、收敛停止 | `kg_server_enhanced.py`, `analysis_pipeline.py`, `enhancement_executor.py`, `constraint_optimizer.py` | 基本实现 | 已有运行时闭环；全局最优求解仍采用候选动作级贪心近似 |
| Incremental Quality Metric Update | 小规模编辑后只更新局部受影响指标，避免全图重算 | `MultiScaleConstraintOptimizer.optimize_and_apply()` | 部分实现 | 当前是候选动作后的 bounded re-assessment，不是持久化索引增量缓存 |
| Constraint-Driven Multi-Scale KG Enhancement | 将多尺度质量评估、`f_phi` 路由、硬违规优先、候选动作 utility、可行性检查和增量更新整合成完整增强算法 | `content_enhancement/constraint_optimizer.py`, `enhancement_executor.py`, `kg_server_enhanced.py` | 基本实现 | 已完整串联核心组件；剩余差距是全局优化和持久化增量索引 |

## 中文总览：神经网络输入输出细节

论文中的 `f_phi([s;g])` 在项目里的具体实现如下：

- 输入向量长度为 8：
  `[S_iso, S_red, S_log, S_sem, n_v, n_e, density, n_viol_feat]`
- 其中质量子向量 `s` 为：
  `[S_iso, S_red, S_log, S_sem]`
  - `S_iso`: 孤立节点相关质量得分；
  - `S_red`: 冗余三元组相关质量得分；
  - `S_log`: 逻辑一致性得分；
  - `S_sem`: 语义合理性得分。
- 图统计子向量 `g` 为：
  `[n_v, n_e, density, n_viol_feat]`
  - `n_v`: 节点数；
  - `n_e`: 边/关系数；
  - `density`: 图密度；
  - `n_viol_feat`: 缺陷数量特征，文档中建议明确为 `n_missing + n_dup + n_logconf`。
- 输出为：
  - `p_repair`: 当前样本需要修复的概率；
  - `pi=[pi_entity,pi_graph,pi_context]`: 缺陷更可能属于实体尺度、图尺度、上下文尺度的概率分布。
- 当前实现位置：
  - 数据构建：`exps/decision_network/build_dataset.py`
  - 训练：`exps/decision_network/train_fphi.py`
  - 评估：`exps/decision_network/eval_fphi.py`
- 当前运行时接入：
  - `FphiRouter` 会加载 `fphi_model.npz` 和 `scaler.json`；
  - `MultiScaleConstraintOptimizer` 在候选动作选择前调用 `f_phi`；
  - 若模型文件不可用，会使用同接口 heuristic fallback，保证服务器不崩溃。

This document audits Paper1 Chapter 3/4 method sections against the current project implementation.

Scope:

- Paper files:
  - `paper1/sections/overview.tex`
  - `paper1/sections/implementation.tex`
  - `paper1/sections/experiments.tex`
- Main implementation files:
  - `exps/pol_evaluate.py`, `exps/finance_evaluate.py`, `exps/env_evaluate.py`
  - `content_enhancement/analysis_pipeline.py`
  - `content_enhancement/global_analysis.py`
  - `content_enhancement/entity_detail_analyzer.py`
  - `content_enhancement/logic_analyzer.py`
  - `content_enhancement/enhancement_executor.py`
  - `kg_server_enhanced.py`
  - `exps/decision_network/{build_dataset.py,train_fphi.py,eval_fphi.py}`
  - `exps/external_benchmark_runner.py`
  - `exps/api_llm_extraction_benchmark.py`

## Executive Summary

Overall match:

- The quality-assessment part is mostly implemented, but with simpler operational definitions than the paper states.
- The neural decision network `f_phi` is implemented, evaluated as an experiment, and now loaded by the runtime optimizer.
- The production pipeline now includes a runtime constraint-driven optimization layer:
  - `content_enhancement/constraint_optimizer.py`
  - integrated by `content_enhancement/enhancement_executor.py`
  - exposed through `kg_server_enhanced.py` enhancement summaries.
- The paper's utility function, cost hierarchy, feasibility gate, `f_phi` routing, and local re-assessment loop are now implemented at runtime. The incremental update is implemented as bounded local re-assessment after candidate edits rather than a persistent graph-index cache.
- The new external benchmark has been implemented and added to `paper1/sections/experiments.tex`.
- The requested API-backed LLM extraction benchmark has also been implemented and added to `paper1/sections/experiments.tex`.

Main remaining risks to fix or disclose:

1. `overview.tex` lists many profile metrics that are not implemented or used in experiments: `q_clus`, `q_fit`, `q_comm`, `q_reach`, `q_proc`.
2. `overview.tex` repeats the Graph-Scale properties list twice.
3. `Q_uniq` is now closer to the paper at runtime, but the historical experiment evaluators still use exact triple hashing or heuristic duplicate counting.
4. Incremental metric update is partially implemented as bounded candidate re-assessment, but current evaluation scripts still recompute metrics at graph/report level.
5. The runtime optimizer is candidate-action greedy; it should not be described as a global exact solver.
6. `decision_loss` still differs from the paper if the paper presents `y_scale` as a soft distribution while the training code uses a dominant hard class.

Resolved since the first audit:

- `f_phi` is now loaded by `FphiRouter` inside `content_enhancement/constraint_optimizer.py`; if model files are unavailable, a heuristic router preserves the same interface.
- Eq. `action_utility` and Eq. `cost_hierarchy` are now executed by `MultiScaleConstraintOptimizer` before committing candidate actions.
- `EnhancementExecutor` now commits only actions that pass utility and feasibility checks.

## Runtime Implementation Added After Audit

New module:

- `content_enhancement/constraint_optimizer.py`

What it implements:

- Multi-scale quality profile:
  `[S_iso, S_red, S_log, S_sem, n_v, n_e, density, n_viol_feat]`
- Runtime `f_phi` inference:
  - loads `exps/decision_network/fphi_model.npz`
  - loads `exps/decision_network/scaler.json`
  - returns `p_repair` and `pi=[pi_entity,pi_graph,pi_context]`
- Semantic redundancy approximation for `Q_uniq`:
  - exact duplicate match;
  - weighted character n-gram cosine over `(subject, relation, object)` as a dependency-light embedding proxy.
- Constraint detection:
  - isolated nodes;
  - redundant triples;
  - empty triples;
  - invalid relation markers;
  - self-loops;
  - hierarchy reversals;
  - dangling endpoints.
- Candidate action generation:
  - consumes `LogicAnalyzer` recommendations;
  - also generates automatic candidates from detected hard violations when LLM-generated actions are absent.
- Utility-based selection:
  - computes `Delta Q`;
  - applies operation cost hierarchy;
  - incorporates `f_phi` scale prior;
  - gives hard graph repairs priority when they improve logical consistency.
- Constraint gate:
  - checks lower quality bounds;
  - checks density upper bound;
  - rejects destructive empty-graph deletions;
  - rejects actions that regress any quality dimension too strongly.
- Bundle actions:
  - multi-step repairs such as "remove reversed edge + add corrected edge" are evaluated as one feasible action plan.

Integration changes:

- `content_enhancement/enhancement_executor.py`
  - now calls `MultiScaleConstraintOptimizer.optimize_and_apply()`;
  - no longer blindly applies all `LogicAnalyzer` add/remove instructions;
  - records optimizer diagnostics in `enhancement_summary.constraint_optimizer`.
- `kg_server_enhanced.py`
  - preserves the optimizer diagnostics in MCP tool output instead of overwriting the enhancement summary.
- `content_enhancement/global_analysis.py`
  - now has a fallback tokenizer when `jieba` is not installed, so analysis import does not fail.
- `content_enhancement/__init__.py`
  - now uses tolerant imports and fixes the `enhance_knowledge_graph()` helper signature.

Validation performed:

- `python3 -m py_compile content_enhancement/__init__.py content_enhancement/global_analysis.py content_enhancement/constraint_optimizer.py content_enhancement/enhancement_executor.py kg_server_enhanced.py`
- Local hierarchy-reversal repair test:
  - input triple: `县环保局 --管理--> 省生态环境厅`
  - generated/selected action: remove reversed edge + add `省生态环境厅 --管理--> 县环保局`
  - `S_log: 0.0 -> 100.0`
  - `q_score: 75.0 -> 100.0`
  - router source: `f_phi`

## Added Benchmark Result

I added a new external benchmark subsection to:

- `paper1/sections/experiments.tex`

Implemented runner:

- `exps/external_benchmark_runner.py`

Outputs:

- `exps/external_benchmark/report.md`
- `exps/external_benchmark/results.json`
- `exps/external_benchmark/rule_test_predictions_system.csv`
- `exps/external_benchmark/rule_test_predictions_expert.csv`

Results added to the paper:

| Benchmark | Main Result |
| --- | --- |
| TNEWS/CLUE KG quality benchmark | `Q_score` improves from `94.93` to `100.00` after repair |
| RuleTest-94 expert baseline | Precision `1.000`, Recall `0.469`, F1 `0.638` |
| RuleTest-94 system detector | Precision `1.000`, Recall `1.000`, F1 `1.000` |
| API LLM extraction benchmark | Parse success `0.844`; category accuracy `0.467`; `Q_score` improves from `98.87` to `100.00` |

Interpretation:

- This benchmark tests the deterministic quality-control and repair layer.
- It does not test open-domain LLM triple extraction quality.
- The separate API-backed benchmark below tests the raw-title to LLM-triples to repaired-KG path.

## Added API-backed LLM Extraction Benchmark

Implemented runner:

- `exps/api_llm_extraction_benchmark.py`

Outputs:

- `exps/api_llm_extraction_benchmark/report.md`
- `exps/api_llm_extraction_benchmark/results.json`
- `exps/api_llm_extraction_benchmark/predictions.csv`

Setup:

- Model: `Qwen3.6-35B-A3B-no-thinking`
- API endpoint and key: parsed from local `apis`
- Dataset: balanced 45-document TNEWS/CLUE subset across 15 categories
- Pipeline: raw Chinese news title -> API LLM JSON triples -> deterministic KG quality-control repair

Results added to the paper:

| Metric | Raw LLM KG | Repaired KG |
| --- | ---: | ---: |
| Parse success | 0.844 | - |
| Category accuracy | 0.467 | 0.467 |
| Keyword recall | 0.131 | 0.122 |
| Documents with triples | 0.844 | 0.844 |
| Avg triples/doc | 2.76 | 2.67 |
| Invalid triple rate | 0.032 | 0.000 |
| Duplicate triple rate | 0.000 | 0.000 |
| `Q_score` | 98.87 | 100.00 |

Interpretation:

- This is the requested API/LLM end-to-end extraction benchmark.
- It is not a gold triple-level F1 benchmark because TNEWS provides labels and keywords, not human-annotated KG triples.
- Category accuracy uses the TNEWS label as a silver label.
- Keyword recall uses the dataset keyword field as weak entity supervision.
- The main evidence it adds is that the system can sanitize real API LLM outputs, not only deterministic locally extracted triples.

## Chapter 3: Framework Overview and Problem Formulation

### Problem Statement and Core Insight

Paper claim:

- KG quality should be diagnosed by intrinsic graph-theoretic properties, not only downstream task performance.
- The quality profile tells the system what to update.
- Constraint-driven enhancement decides how to update while avoiding reward hacking.

Implementation match:

- Mostly implemented after the runtime optimizer update.
- Intrinsic metrics are implemented in the evaluation scripts:
  - isolated-node rate;
  - redundant-triple rate;
  - logical conflict rate;
  - semantic score via API judge.
- Runtime quality profiling is implemented in `content_enhancement/constraint_optimizer.py`.
- The actual live enhancement pipeline in `kg_server_enhanced.py` performs:
  1. text quality assessment;
  2. optional knowledge completion;
  3. KG construction;
  4. analysis;
  5. constraint-gated enhancement;
  6. export.
- The optimizer is implemented as candidate-action greedy selection with feasibility gates. It does not claim global exact optimization.

### Entity-Scale Properties

Paper metrics:

- `q_conn`: node connectivity.
- `q_clus`: local clustering.
- `q_uniq`: triple uniqueness.

Implementation:

| Metric | Implemented? | Code |
| --- | --- | --- |
| `q_conn` / isolation | Yes | `detect_isolated_nodes()` in `exps/*_evaluate.py` |
| `q_uniq` / redundancy | Yes, simplified | `detect_redundant_triples()` in `exps/*_evaluate.py` |
| `q_clus` / local clustering | Not used in experiments | No direct implementation found in evaluator |

Important mismatch:

- The paper says `q_uniq` uses embedding similarity.
- The runtime optimizer now implements a dependency-light semantic similarity proxy using weighted character n-gram cosine over subject/relation/object.
- The historical experiment evaluators still use SHA-256 exact triple hashes.
- The decision-network dataset builder uses duplicate triples, repeated objects, and repeated clauses as heuristic redundancy.

Recommended implementation/paper note:

- For strict consistency with Eq. `sim`, a real embedding encoder can replace the current n-gram cosine backend.
- The current project is closer to the formula than before, but experiments and runtime still use different redundancy backends.

### Graph-Scale Properties

Paper metrics:

- `q_fit`: degree distribution fitting.
- `q_logic`: logical consistency.
- `q_comm`: community modularity.
- `q_reach`: global reachability.

Implementation:

| Metric | Implemented? | Code |
| --- | --- | --- |
| `q_logic` | Yes | `check_logical_consistency()` in `exps/*_evaluate.py` |
| invalid relation checks | Yes | `无效关系类型` rules |
| type conflict checks | Yes | `类型冲突规则` |
| government/geographic hierarchy checks | Yes | `_check_government_hierarchy_conflicts()`, `_check_geographical_hierarchy_conflicts()` |
| `q_fit` | No | No matching implementation found |
| `q_comm` | No | No matching implementation found |
| `q_reach` | Not explicitly | largest component not used as paper metric |

Important mismatch:

- `overview.tex` lists graph-scale metrics more broadly than experiments actually use.
- The Graph-Scale item list is duplicated in `overview.tex`.

Recommended paper adjustment:

- Remove the duplicated graph-scale list.
- State that the implemented graph-scale metric is logical consistency, while degree fitting/community/reachability are optional profile extensions.

### Context-Scale Properties

Paper metrics:

- `q_sem`: semantic appropriateness.
- `q_proc`: process-causal completeness.

Implementation:

| Metric | Implemented? | Code |
| --- | --- | --- |
| `q_sem` | Yes | `evaluate_semantic_consistency()` in `exps/*_evaluate.py` |
| independent scoring reliability | Yes | `exps/semantic_reliability_gemma.py`, `exps/analyze_reliability.py` |
| human agreement | Partly/materials + results in paper | `exps/semantic_reliability/*` |
| `q_proc` | Partly via rules/logic prompts | No standalone metric implementation |

Important mismatch:

- The paper describes process-causal completeness as a formal profile component.
- The code handles process/procedure issues through rule checks, prompts, or RuleTest-style detection, not as an independent `q_proc` score.

Recommended paper adjustment:

- Either remove `q_proc` from the formal profile or label it as an extension used through procedural rules rather than as a numeric score.

## Formula-by-Formula Audit

### Eq. `quality_profile`

Paper:

```tex
\mathbf{P} = [\mathbf{p}_{ent}^\top, \mathbf{p}_{graph}^\top, \mathbf{p}_{ctx}^\top]^\top \in [0,1]^D
```

Meaning:

- Concatenates all normalized quality metrics across entity, graph, and context scales.
- `p_ent`: entity-scale feature subvector.
- `p_graph`: graph-scale feature subvector.
- `p_ctx`: context-scale feature subvector.
- `D`: total number of features.

Corresponding implementation:

- In experiments, the operational state is closer to four scores:
  - `S_iso`;
  - `S_red`;
  - `S_log`;
  - `S_sem`.
- In `f_phi`, the actual input includes an 8-dimensional vector:
  - `S_iso`;
  - `S_red`;
  - `S_log`;
  - `S_sem`;
  - `n_v`;
  - `n_e`;
  - `density`;
  - `n_viol_feat`.

Code:

- `exps/decision_network/build_dataset.py`
- `exps/decision_network/train_fphi.py`

Correctness:

- Mathematically correct.
- The implementation uses a smaller realized profile than the full vector described in `overview.tex`.

Recommended wording:

- "The full profile formulation is general; the implemented experiments instantiate it with four quality scores and four graph statistics."

### Eq. `constrained_opt`

Paper:

```tex
\max_{G'} \mathbf{w}^\top \mathbf{P}(G')
\quad \text{s.t.} \quad \mathbf{L} \leq \mathbf{P}(G') \leq \mathbf{U}
```

Meaning:

- Find an enhanced graph `G'` with maximal weighted quality.
- `w`: non-negative metric weights.
- `L`: lower-bound quality constraints.
- `U`: upper-bound anti-overoptimization constraints.

Corresponding implementation:

- Implemented at runtime by `content_enhancement/constraint_optimizer.py`.
- The optimizer evaluates candidate actions or action bundles, estimates quality gain, applies operation cost, uses the `f_phi` scale prior, and commits only feasible actions.
- The implementation is a candidate-action greedy optimizer rather than a global exact solver over all possible `G'`.

Correctness:

- Formula is correct as an abstract constrained optimization problem.
- Runtime implementation enforces lower quality bounds and density upper bound at candidate commit time.

Recommended wording:

- It is accurate to say the execution layer approximates Eq. `constrained_opt` through candidate-level constrained optimization.
- Avoid claiming global optimality.

### Eq. `q_conn`

Paper:

```tex
Q_conn = 100(1-r_iso), 
r_iso = |{e in V | deg(e)=0}| / |V|
```

Meaning:

- Measures non-isolated node ratio.
- Higher score means better connectivity.

Implementation:

- `detect_isolated_nodes()` in `exps/pol_evaluate.py`, `exps/finance_evaluate.py`, `exps/env_evaluate.py`.
- Computes connected nodes from relation endpoints and divides isolated node count by total nodes.

Correctness:

- Correct and implemented.
- Edge case `|V|=0` is handled in code.

### Eq. `sim`

Paper:

```tex
Sim(t1,t2) = alpha cos(e_s1,e_s2) + beta cos(e_r1,e_r2) + gamma cos(e_o1,e_o2)
```

Meaning:

- Weighted semantic similarity between two triples.
- Used to mark near-duplicate triples.
- `alpha + beta + gamma = 1`.

Implementation:

- Not implemented in the main evaluators.
- Evaluators use exact triple hash:
  - `start_id-relation_type-end_id`.
- No embedding model is used for redundancy scoring in `exps/*_evaluate.py`.

Correctness:

- Formula is mathematically reasonable.
- It does not match the current evaluator implementation.

Recommended action:

- Either implement embedding-based deduplication or revise the paper to exact-hash deduplication.

### Eq. `q_uniq`

Paper:

```tex
Q_uniq = 100(1-r_red)
```

Meaning:

- Converts redundant-triple rate into a quality score.

Implementation:

- Implemented with exact duplicate rate in `detect_redundant_triples()`.
- `build_dataset.py` also uses duplicate triples/repeated objects/repeated clauses as document-level redundancy features.

Correctness:

- The score formula is correct.
- The definition of `r_red` must match implementation. Currently paper says semantic duplicate; code uses exact/heuristic duplicate.

### Eq. `q_logic`

Paper:

```tex
Q_logic = 100(1-r_log)
```

Meaning:

- Converts logical-conflict rate into a quality score.

Implementation:

- Implemented in `check_logical_consistency()`.
- Includes invalid node types, invalid relations, type conflict rules, government hierarchy conflicts, and geographic hierarchy conflicts.

Correctness:

- Formula is correct if `r_log in [0,1]`.
- Implementation computes conflict count divided by number of relationships. Since conflicts may include invalid nodes plus relationship conflicts, `r_log` can theoretically exceed 1 if many node-level conflicts exist. In practice this likely does not happen often.

Recommended implementation improvement:

- Clamp `conflict_rate = min(1.0, conflict_count / max(1, len(relationships)))`.

### Eq. `q_sem`

Paper:

```tex
Q_sem = (100/K) sum_{k=1}^{K} s_k
```

Meaning:

- Average LLM semantic plausibility score over sampled triples.
- Scores are scaled to `[0,100]`.

Implementation:

- `evaluate_semantic_consistency()` samples relations and calls Qwen via API.
- Existing experiments also use independent Gemma rescoring for reliability.

Correctness:

- Formula is correct.
- There is a minor protocol mismatch:
  - Paper says `K=50`.
  - Evaluator config uses `semantic_eval_sample_size = 0.1`.
  - Some experiment scripts use fixed samples.

Recommended action:

- Make the paper's sampling statement match the actual scripts used for the reported results.

### Incremental Complexity Formula

Paper:

```tex
O(n_delta d_max^k + |DeltaE| n_delta d_max^k + |R_local| n_delta d_max^k + |E_delta| c_LLM)
```

Meaning:

- Estimates the cost of updating only a local affected neighborhood after a graph edit.

Implementation:

- Runtime enhancement uses bounded local re-assessment after each candidate action in `MultiScaleConstraintOptimizer.optimize_and_apply()`.
- Candidate actions are evaluated on trial graphs before commit, and only committed if the resulting profile satisfies constraints.
- Current experiment evaluators still recompute metrics from loaded CSVs.
- No persistent graph-index cache is implemented.

Correctness:

- Reasonable as a design/algorithmic complexity claim.
- Runtime implementation partially matches the intent, but not the full persistent incremental algorithm.

### Eq. `decision_net`

Paper:

```tex
(p_repair, pi) = f_phi([s;g]), 
p_repair in [0,1], pi in Delta^2
```

Meaning:

- Neural router predicts whether repair is needed and which structural scale is most likely responsible.
- `p_repair`: binary repair probability.
- `pi`: 3-way distribution over entity/graph/context.

Implementation:

- Implemented in `exps/decision_network/train_fphi.py`.
- Architecture:
  - input: 8 dimensions;
  - hidden layers: `8 -> 32 -> 16`;
  - repair head: 1 sigmoid output;
  - scale head: 3-way softmax.

Actual input vector:

```text
[S_iso, S_red, S_log, S_sem, n_v, n_e, density, n_viol_feat]
```

Subvector interpretation:

- `s = [S_iso, S_red, S_log, S_sem]`
  - quality scores;
  - each corresponds to one quality dimension.
- `g = [n_v, n_e, density, n_viol_feat]`
  - graph/document statistics;
  - `n_viol_feat = n_missing + n_dup + n_logconf`.

Output:

- `p_repair`: probability that the document/KG instance needs repair.
- `pi = [pi_entity, pi_graph, pi_context]`: predicted defect scale prior.

Correctness:

- Implemented and now aligned with the paper at runtime.
- `FphiRouter` loads the trained NumPy model and scaler from `exps/decision_network`.
- `MultiScaleConstraintOptimizer` calls `f_phi` before candidate selection and records `p_repair`/`pi` in the enhancement summary.

### Eq. `repair_label`

Paper:

```tex
y = 1[V_hard(G) != empty or Q(G) < theta_Q]
```

Meaning:

- A self-supervised binary repair label.
- Repair is needed if hard violations exist or quality is below threshold.

Implementation:

- `build_dataset.py` uses:
  - `y_repair = 1` for dirty/injected-defect corpus;
  - `y_repair = 0` for clean corpus.

Correctness:

- Conceptually aligned because dirty samples are generated by known defects.
- Not exactly the same as the formula, because the code does not compute `V_hard` or `Q < theta_Q` to assign the label.

Recommended wording:

- "In the implementation, `y` is derived from injected-defect provenance, which operationalizes Eq. `repair_label` for the controlled degradation setting."

### Eq. `scale_label`

Paper:

```tex
y_scale = Normalize(|V_entity|, |V_graph|, |V_context|)
```

Meaning:

- Produces a scale distribution from counts of violations at each scale.

Implementation:

- `build_dataset.py` maps injected defect types to scales:
  - entity: duplicate, redundancy, isolated node, field missing;
  - graph: hierarchy conflict, logical contradiction, relationship error, entity-type error;
  - context: terminology error, information inconsistency, format error.
- It counts mapped defects and normalizes them.

Correctness:

- Mostly aligned.
- The implementation uses injected defect provenance rather than detected violation counts.

### Eq. `decision_loss`

Paper:

```tex
L(phi) = BCE(p_repair,y) + lambda m_scale CE(y_scale, pi)
```

Meaning:

- Binary classification loss for repair/no-repair.
- Cross-entropy loss for scale routing.
- `m_scale` masks scale loss for clean/no-defect instances.

Implementation:

- Implemented in `train_fphi.py`.
- `BCE` is used for repair head.
- `CE` is used for scale head.
- Mask is applied to defect-bearing instances.

Important mismatch:

- Paper defines `y_scale` as a normalized vector.
- The implementation trains the scale head using a single class index derived from `scale_label`, not a soft target distribution.

Recommended action:

- Either revise the formula to dominant-class CE:
  `CE(argmax(y_scale), pi)`;
- or modify training to use soft-label cross entropy:
  `-sum_j y_scale_j log pi_j`.

### Eq. `action_utility`

Paper:

```tex
U(a|v) = DeltaQ_hat(a|v) - beta cost(a) + eta log(pi_sigma(v)+epsilon_log)
```

Meaning:

- Scores candidate repair actions.
- Rewards local quality gain.
- Penalizes cost/destructiveness.
- Biases action selection toward the neural predicted scale.

Implementation:

- Implemented in `MultiScaleConstraintOptimizer._utility()`.
- It computes:
  - normalized quality gain `Delta Q`;
  - operation cost penalty;
  - `f_phi` scale-prior term;
  - a hard-constraint bonus for graph repairs that improve or preserve logical consistency.
- `EnhancementExecutor` now delegates candidate selection and application to the optimizer instead of directly applying all analyzer actions.

Correctness:

- Formula is plausible.
- It is now implemented as a runtime action selector.

Recommended action:

- Remaining improvement: calibrate `beta`, `eta`, and operation costs on a larger validation set.

### Eq. `cost_hierarchy`

Paper:

```tex
cost(a) = lambda_del if delete
        = lambda_ret if retype
        = lambda_cmp if complete
lambda_del > lambda_ret > lambda_cmp
```

Meaning:

- Deletion is most costly/destructive.
- Retyping is intermediate.
- Completion is least destructive.

Implementation:

- Implemented in `MultiScaleConstraintOptimizer.costs`.
- Current hierarchy:
  - `delete/remove`: highest cost;
  - `retype`: intermediate cost;
  - `complete/add`: lowest cost;
  - `bundle`: sum/combined action cost.
- The executor still exposes mostly add/remove plans from upstream analyzers, but the optimizer supports `retype` candidates if supplied.

Correctness:

- Formula is correct as a design prior.
- Runtime implementation now follows the hierarchy.

Recommended action:

- Add more upstream analyzers that emit explicit `retype` actions to make that branch more frequently exercised.

## Algorithm Audit

### Algorithm `abstract`: Abstract Constraint-Driven KG Enhancement

Meaning:

- High-level closed loop:
  1. assess graph;
  2. detect violations;
  3. select action;
  4. check constraints;
  5. apply action;
  6. stop on convergence.

Implementation match:

- `kg_server_enhanced.py` has a broad end-to-end pipeline:
  1. data quality assessment;
  2. knowledge completion;
  3. KG construction;
  4. analysis;
  5. enhancement;
  6. export.
- `content_enhancement/constraint_optimizer.py` now implements `Assess`, `DetectViolations`, `SelectAction`, `CheckConstraints`, and `Apply` at candidate-action level.

Status:

- Mostly implemented.
- Correct as architectural pseudocode.

### Algorithm `incremental`: Incremental Quality Metric Update

Meaning:

- Avoids full recomputation after small graph edits.
- Recomputes only affected k-hop neighborhood.

Implementation match:

- Runtime enhancement performs bounded re-assessment around each candidate action.
- Current evaluators still recompute metrics from the graph/CSV.
- No persistent graph-index cache is implemented.

Status:

- Partially implemented.

Recommended action:

- Implement a persistent affected-neighborhood cache if exact Algorithm `incremental` needs to be claimed literally.

### Algorithm `enhancement`: Constraint-Driven Multi-Scale KG Enhancement

Meaning:

- Complete enhancement loop using:
  - multi-scale evaluation;
  - `f_phi` repair/scale routing;
  - hard violation priority;
  - utility-based candidate actions;
  - feasibility checks;
  - incremental metric updates.

Implementation match:

- Components are now integrated:
  - assessment: `MultiScaleConstraintOptimizer.assess()`;
  - `f_phi`: `FphiRouter`;
  - violation detection: `assess()` + `_violations_to_actions()`;
  - utility scoring: `_utility()`;
  - feasibility checking: `_check_constraints()`;
  - application: `_apply_candidate()`;
  - server pipeline: `kg_server_enhanced.py`.
- The loop is candidate-action greedy and supports action bundles.

Status:

- Mostly implemented at runtime.

Recommended action:

- It is now reasonable to claim that the runtime system executes the core algorithmic components.
- Avoid claiming global optimality or persistent-cache incremental complexity.

## Generated Artifacts and What They Correspond To

### Quality reports

Examples:

- `exps/qa_gover_*/quality_scores.json`
- `exps/qa_finance_*/quality_scores.json`
- `exps/qa_environment_*/quality_scores.json`

Generated by:

- `exps/pol_evaluate.py`
- `exps/finance_evaluate.py`
- `exps/env_evaluate.py`

Correspond to:

- `S_iso`;
- `S_red`;
- `S_log`;
- `S_sem`;
- `Q_score`.

### Decision-network artifacts

Files:

- `exps/decision_network/dataset.csv`
- `exps/decision_network/fphi_model.npz`
- `exps/decision_network/scaler.json`
- `exps/decision_network/splits.json`
- `exps/decision_network/train_meta.json`
- `exps/decision_network/decision_quality.json`
- `exps/decision_network/efficiency_sim.json`

Correspond to:

- Eq. `decision_net`;
- Eq. `repair_label`;
- Eq. `scale_label`;
- Eq. `decision_loss`;
- decision-network ablation in experiments.

### External benchmark artifacts

Files:

- `exps/external_benchmark_runner.py`
- `exps/external_benchmark/report.md`
- `exps/external_benchmark/results.json`
- `exps/external_benchmark/rule_test_predictions_system.csv`
- `exps/external_benchmark/rule_test_predictions_expert.csv`

Correspond to:

- Newly added benchmark in `paper1/sections/experiments.tex`.
- Tests local quality control and rule execution.

### API LLM extraction benchmark artifacts

Files:

- `exps/api_llm_extraction_benchmark.py`
- `exps/api_llm_extraction_benchmark/report.md`
- `exps/api_llm_extraction_benchmark/results.json`
- `exps/api_llm_extraction_benchmark/predictions.csv`

Correspond to:

- Newly added API-backed end-to-end extraction benchmark in `paper1/sections/experiments.tex`.
- Tests raw text -> API LLM triples -> repaired KG.
- Uses TNEWS labels and keywords as silver/weak supervision.

## Does the Project Need Another Benchmark?

Current status:

- The paper now has two additional external benchmark settings:
  - TNEWS/CLUE out-of-domain KG quality benchmark;
  - RuleTest-94 labeled rule detection benchmark.
  - API-backed TNEWS LLM extraction benchmark.

This is enough to support:

- deterministic quality-control robustness;
- rule-layer coverage;
- out-of-domain structural repair on non-regulatory text.
- API LLM output sanitization after open-domain extraction.

Still missing if the paper wants to claim gold-standard open-domain extraction quality:

- A human-annotated triple-level benchmark with gold subject-relation-object labels.
- The current API benchmark uses TNEWS labels and keywords as silver/weak supervision, so it supports end-to-end system testing but not strict triple-level precision/recall claims.

## Recommended Fixes Before Submission

High priority:

1. Remove duplicate Graph-Scale bullet list in `overview.tex`.
2. Align redundancy description with implementation:
   - runtime now has character n-gram semantic similarity;
   - experiment evaluators still use exact-hash/heuristic duplicate detection;
   - decide whether to unify all evaluators to the runtime similarity backend.
3. Align `decision_loss` formula with hard-label implementation or change implementation to soft-label CE.
4. Clarify the incremental-update claim:
   - runtime uses bounded candidate re-assessment;
   - no persistent graph-index cache is implemented.
5. Keep the limitation that the optimizer is candidate-action greedy, not a global exact solver.

Medium priority:

1. Add a small implementation paragraph explaining the runtime `f_phi` input vector:
   `[S_iso, S_red, S_log, S_sem, |V|, |E|, density, n_viol_feat]`.
2. Explain that `n_viol_feat = n_missing + n_dup + n_logconf`.
3. Add one sentence that clean instances mask the scale loss.
4. Add a note that `RuleTest-94` is a designed benchmark suite, not a natural production distribution.

Low priority:

1. Add upstream analyzers that emit more explicit `retype` actions.
2. Replace character n-gram similarity with a real embedding encoder if runtime dependencies allow it.
3. Add a human-annotated triple-level benchmark if the target venue expects extraction F1.
