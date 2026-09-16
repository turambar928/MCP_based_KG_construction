# Paper 1 实验总览（DMKD 投稿版）

论文主实验已经改为逐实例、可配对验证的 KG repair benchmark。旧的三域聚合 `Q_score` 仅作为辅助结果，不能再用 `+7.14 / +4.46` 作为主要比较证据。

## 1. 主 benchmark

- 来源：政务、金融、环境三个真实文档域。
- 规模：1,499 个文档图；每个文档包含 clean / corrupted 配对图。
- 缺陷：2,998 个，每例两个实际图修改，涵盖 missing、duplicate、invalid relation、reversed edge、wrong value、hierarchy conflict。
- 划分：按源文档 identity 在污染前做 70/15/15 划分，seed 42，无 UID 交叉。
- 测试集：225 个文档（三域各 75），450 个缺陷。
- 模型公平性：Direct LLM、ReAct-style Agent、Ours 共用 `claude-haiku-4-5-20251001`，temperature 0。

主要产物在 `exps/paper1_repair_benchmark/`：benchmark、manifest、六种方法逐例预测、逐例/逐缺陷指标、bootstrap 区间、McNemar 检验、消融、失败审计、独立 judge 原始输出。

## 2. 主结果

| 方法 | 缺陷修复率 | 干净事实保留 | 过修复率 | Triple F1 | Exact graph | 调用/文档 | 延迟/文档 |
|---|---:|---:|---:|---:|---:|---:|---:|
| No Repair | 0.0000 | 1.0000 | 0.0000 | 0.7615 | 0.0000 | 0 | <0.001 s |
| Rule Only | 0.3200 | 1.0000 | 0.0000 | 0.8472 | 0.0622 | 0 | <0.001 s |
| SHACL-style | 0.0000 | 1.0000 | 0.0000 | 0.7998 | 0.0000 | 0 | <0.001 s |
| Direct LLM | 0.9244 | 0.9687 | 0.0758 | 0.9520 | 0.8267 | 1 | 7.25 s |
| ReAct-style | 0.8911 | 0.9324 | 0.1667 | 0.9213 | 0.5956 | 2 | 20.50 s |
| **Ours** | **0.9800** | **0.9932** | **0.0167** | **0.9917** | **0.9333** | 1 | 11.44 s |

Ours 的缺陷修复率 95% bootstrap CI 为 `[0.9667, 0.9911]`。逐缺陷 McNemar：

- vs Direct LLM：28 个仅 Ours 成功、3 个仅 baseline 成功，`p=4.65e-6`；
- vs ReAct：42 vs 2，`p=1.13e-10`；
- vs Rule Only：298 vs 1，`p=5.89e-88`。

Direct LLM 有一个长政务案例返回非法 JSON，按真实端到端失败计入，没有删除该案例。

## 3. 消融

| 配置 | 缺陷修复率 | 保留率 | 过修复率 | Triple F1 | Exact graph |
|---|---:|---:|---:|---:|---:|
| No context reasoning | 0.3200 | 1.0000 | 0.0000 | 0.8472 | 0.0622 |
| No structural preprocessing | 0.9244 | 0.9687 | 0.0758 | 0.9520 | 0.8267 |
| No constraint gate | 0.9800 | 0.9932 | 0.0227 | 0.9895 | 0.9333 |
| **Full** | **0.9800** | **0.9932** | **0.0167** | **0.9917** | **0.9333** |

正确解读：上下文推理贡献主要修复能力；结构预处理降低模型错误；constraint gate 主要减少无支撑修改，而不是增加新的正确事实。

## 4. 语义可靠性

固定 seed 42 抽取 180 条输出，Ours / No Repair、三域平衡。独立 judge 为 `google/gemma-4-26B-A4B-it`，不提供方法名和 gold label。

- gold validity vs judge：Pearson `r=0.794`，Spearman `rho=0.807`；
- judge 均分：Ours `1.000`，No Repair `0.917`；
- 固定 50 条重复五轮，五轮均值均为 `0.96`，item SD 和 run-mean SD 均为 `0.0`。

这项实验只验证独立 judge 的一致性和服务稳定性，不替代人工评价。

## 5. 决策网络

新 benchmark 生成 2,998 行 clean/dirty 数据，train/validation/test = 2,098/450/450，按文档组隔离。

- repair trigger Accuracy/F1 = 1.0；
- scale prior top-1/macro-F1 = 1.0；
- router 在平衡测试集中只路由 50% 输入；结合真实 Ours 成本，预计从 1.0 call、11.445 s 降到 0.5 call、5.722 s。

论文必须把它写成“受控缺陷映射 sanity check”，不宣称自然缺陷泛化性能。效率数字是“实测门控比例 × 实测单次修复成本”的投影。

## 6. 失败审计

Ours 未修复 9/450 个缺陷，审计覆盖全部失败，不再写“抽样 150 个”：

- invalid relation：3；
- missing triple：2；
- reversed edge：1；
- wrong value：3。

全部位于 government 域的长法律依据或责任事项字段。论文据此把主要后续方向收敛为长文本 chunk / span copy，而不是泛化为无产物支持的四类失败比例。

## 7. 外部平台与辅助证据

- Neo4j LLM Knowledge Graph Builder：45 条 TNEWS、共享模型和 schema 的受控 Text-to-KG 对比。结果为 comparable，不能写 superiority。
- 旧 corpus-level `Q_score`：完整系统从 degraded 平均恢复 8.89 分，保留为辅助一致性证据。

## 8. 复现与论文位置

- 论文：`paper1/sections/experiments.tex`；
- 主图生成：`paper1/make_submission_figures.py`；
- 统计：`analyze_results.py`、`analyze_ablations.py`、`build_failure_audit.py`；
- 独立盲评：`semantic_reliability.py`；
- 路由：`exps/decision_network/`。
