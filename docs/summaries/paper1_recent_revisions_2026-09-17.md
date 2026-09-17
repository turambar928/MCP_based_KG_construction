# Paper 1 近期修改汇总（DMKD 投稿准备）

更新时间：2026-09-17

覆盖范围：2026-09-16 至 2026-09-17 的 Paper 1 集中修订（提交 `012319f` 至 `af7e121`）

目标期刊：*Data Mining and Knowledge Discovery*（DMKD）

## 1. 当前状态

Paper 1 已从以聚合质量分数和提示流程为主的版本，调整为一篇围绕**文本构建知识图谱的受约束修复**展开的论文。当前核心方法定位为：

> **Profile-Conditioned Constrained Neural Repair Policy**
>
> 基于质量画像的受约束神经修复策略

方法由四个相互衔接的部分组成：

1. 将缺陷组织为 Entity、Graph、Context 三个尺度的约束；
2. 用四维质量画像连接图谱诊断和图谱修改；
3. 用轻量神经网络预测是否需要修复，并输出三个尺度的软先验；
4. 对候选修改构造 trial graph，通过恢复型约束、密度限制和破坏性编辑保护决定是否提交。

主实验已经改为实例级 paired KG-repair benchmark。当前论文 PDF 可正常编译，共 27 页；方法、实验、图表、参考文献和运行时代码已经完成一轮一致性核查。

## 2. 导师修改意见的落实方式

导师提出的写作路径是“规则 → 三尺度约束 → profile → 轻量神经网络”，本轮按以下方式落实。

| 导师意见 | 当前论文中的处理 |
| --- | --- |
| 最初工作容易被视为 prompt engineering | LLM 和 prompt 被限制为候选动作来源之一，不再直接定义系统状态或决定是否接受修改 |
| 将零散规则提升为三个尺度的约束条件 | 用 Entity、Graph、Context 三个依赖尺度组织局部结构、全局逻辑和来源语义缺陷 |
| 将问题写成约束优化问题 | 定义图状态、候选动作、图转移、质量效用、恢复边界和有限时域目标 |
| 用 profile 连接分析和修改模块 | 使用 `[q_conn, q_uniq, q_logic, q_sem]` 四维画像作为诊断、路由、trial-state 比较和停止判断的共同接口 |
| 用轻量神经网络提升方法完整性 | `f_phi` 接收四维画像和四个图统计量，输出 repair trigger 与三尺度 soft prior |
| 防止神经或 LLM 模块产生不受控修改 | 所有候选先在临时图上完整重评估，只有满足约束且效用为正的最高分动作才能提交 |

最终形成的技术链条是：

```text
多尺度约束 → 四维质量画像 → 神经决策 → 候选图转移 → 约束门控 → 重新评估与规划
```

## 3. 方法与数学建模修改

### 3.1 图、画像和状态

论文统一使用知识图谱定义：

```math
G=(V,\mathcal{R},E).
```

四个归一化质量维度构成运行时画像：

```math
\mathbf q(G)=
[q_{\mathrm{conn}},q_{\mathrm{uniq}},q_{\mathrm{logic}},q_{\mathrm{sem}}]^\top.
```

神经路由状态由质量画像和图统计量拼接：

```math
\mathbf x_t=[\mathbf s_t;\mathbf g_t].
```

其中图统计量包括节点数、边数、投影密度和违反约束的三元组数。

### 3.2 动作、转移和序列目标

每个候选修复被写为类型化图变换，状态转移为：

```math
G_{t+1}=T(G_t,a_t).
```

论文给出有限时域序列目标：

```math
\max_{a_0,\ldots,a_{T-1}}
\sum_t\gamma^t U(a_t\mid G_t)+\gamma^T\mathcal Q(G_T).
```

实现不声称求得全局最优序列。每轮对当前有限候选集逐一构造 trial graph，选择效用最高的可行动作，提交后重新计算画像、违反集合和神经先验。这一过程准确描述为 **receding-horizon constrained policy**。

### 3.3 恢复型约束

旧的严格下界会导致初始图一旦低于阈值，所有候选动作都不可行。当前改为恢复型边界：

- 已经合格的质量维度不得超过允许幅度退化；
- 尚未达标的维度至少不得继续恶化；
- 硬约束违反、密度和破坏性删除另行检查。

因此系统能够从初始不可行状态逐步恢复，同时保持对副作用的控制。

### 3.4 效用函数和停止条件

运行时效用与论文公式现已统一，包含：

- 四维画像的加权增益；
- 硬约束违反数量的实际减少；
- 修改风险或干预成本；
- 神经网络给出的尺度先验；
- 候选提供器的置信度。

循环在以下任一条件满足时终止：神经 trigger 低于阈值且不存在硬违反、违反已清空、没有正效用可行动作，或达到有限 horizon。有限 horizon 保证终止，但论文不声称标量画像单调增加或获得全局最优解。

### 3.5 为什么当前不写成强化学习

当前 `f_phi` 使用 BCE 与 masked cross-entropy，在 clean/corrupted 配对样本上进行监督训练。仓库中没有 Paper 1 对应的 transition trajectory、replay buffer、Bellman target、TD loss 或 policy-gradient 更新。

因此，本轮没有恢复旧 DQN/RL 名称。论文保留了状态、动作、转移、效用和有限时域语义，但将可验证的学习部分准确写成“监督训练的轻量神经策略先验”。旧的图谱质量与规则质量协同 RL 更适合 Paper 2 的规则—图谱共同优化范围。这样可以避免审稿人根据代码和实验指出“方法名称与训练机制不符”。

## 4. 指标定义与实现一致性修复

本轮对方法文本和 `content_enhancement/constraint_optimizer.py` 同步进行了以下修正：

| 原问题 | 当前处理 |
| --- | --- |
| 空图 connectivity 被视为满分 | 空图 connectivity 定义为 0 |
| redundancy 的分子可能导致比例超过 1 | 改为三元组相似图各连通分量的可删除比例 |
| 同一条边触发多个逻辑规则时被重复计数 | logic rate 改为“至少违反一项约束的三元组比例” |
| 原始多重边直接用于 density | 改用无自环简单有向投影，结果限制在 `[0,1]` |
| 论文混用了语义 LLM 评分与运行时检测 | 区分 corpus-level LLM evaluator 和在线 deterministic source-support proxy |
| 声称增量更新但代码未实现 | 明确写为完整 trial-graph reassessment，并给出保守复杂度 |
| 训练标签被描述成约束检查器输出 | 改为真实注入缺陷的 provenance 标签 |
| 论文与代码 repair threshold 不一致 | 统一为 `tau_repair=0.05` |
| 权重可能不构成有效加权和 | 运行时自动归一化 |
| 候选按固定顺序遇到即提交 | 每轮评估全部候选，提交最高效用可行动作 |
| 删除会清除重复三元组的全部 occurrence | 每次只删除 multiset 中一个 occurrence |
| fallback router 可能不满足概率单纯形 | 保证始终输出合法 probability simplex |
| hard bonus 按动作类型静态奖励 | 仅在 hard violations 实际减少时奖励 |

## 5. 新增和重构的实验

### 5.1 Paired KG-repair benchmark

新增了可审计的配对修复 benchmark：

- 三个领域：government、finance、environment；
- 1,499 个 clean/corrupted 文档图对；
- 2,998 个真实执行成功的注入缺陷；
- 六类缺陷：missing triple、duplicate triple、invalid relation、reversed edge、unsupported value、hierarchy conflict；
- 按源文档身份进行 70/15/15 分组划分，seed 42，防止文档泄漏；
- held-out test 为 225 个文档，每个领域 75 个，共 450 个缺陷；
- 每个缺陷均保存 clean triple、corrupted triple、类型和来源标识。

API benchmark 加入断点保存、限流恢复、输出长度控制和严格 JSON 转义检查。无效输出保留为端到端失败，不从统计中删除。

### 5.2 对比方法

所有方法在同一 test input 上运行：

1. No Repair；
2. Rule Only；
3. SHACL-style Repair；
4. Direct LLM；
5. ReAct-style Agent；
6. Ours。

Direct LLM、ReAct-style Agent 和 Ours 使用同一个 `claude-haiku-4-5-20251001` 服务模型和 temperature 0，使比较尽量反映修复流程差异，而不是基础模型差异。

### 5.3 主实验结果

| 方法 | 缺陷修复率 | clean-fact 保留率 | over-repair | Triple F1 | 完全图匹配 | 调用/文档 | 延迟/文档 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| No Repair | 0.00% | 100.00% | 0.00% | 76.15% | 0.00% | 0 | — |
| SHACL-style | 0.00% | 100.00% | 0.00% | 79.98% | 0.00% | 0 | — |
| Rule Only | 32.00% | 100.00% | 0.00% | 84.72% | 6.22% | 0 | — |
| Direct LLM | 92.44% | 96.87% | 7.58% | 95.20% | 82.67% | 1 | 7.25 s |
| ReAct-style Agent | 89.11% | 93.24% | 16.67% | 92.13% | 59.56% | 2 | 20.50 s |
| **Ours** | **98.00%** | **99.32%** | **1.67%** | **99.17%** | **93.33%** | **1** | **11.44 s** |

结果采用文档级 5,000 次 bootstrap 计算 95% 置信区间。对相同 450 个缺陷进行 exact two-sided McNemar 检验：

- Ours vs Direct LLM：28 个缺陷仅 Ours 成功，3 个仅 Direct LLM 成功，`p=4.65e-6`；
- Ours vs ReAct-style Agent：42 个仅 Ours 成功，2 个仅 ReAct 成功，`p=1.13e-10`；
- 与 No Repair、Rule Only、SHACL-style 的差异也均达到显著水平。

### 5.4 组件消融

| 配置 | 缺陷修复率 | over-repair | Triple F1 | 完全图匹配 |
| --- | ---: | ---: | ---: | ---: |
| Full | 98.00% | 1.67% | 99.17% | 93.33% |
| w/o Context Reasoning | 32.00% | 0.00% | 84.72% | 6.22% |
| w/o Structural Preprocessing | 92.44% | 7.58% | 95.20% | 82.67% |
| w/o Constraint Gate | 98.00% | 2.27% | 98.95% | 93.33% |

消融支持以下较窄且可验证的结论：context reasoning 负责恢复缺失事实和错误值；结构预处理减少模型可以提前规避的错误；constraint gate 在本次测试中没有增加完整修复数量，但减少了无支持或重复编辑，使 over-repair 降低 0.60 个百分点、F1 提高 0.22 个百分点。

### 5.5 神经路由 sanity check 与成本投影

benchmark 生成 2,998 行 clean/dirty 路由数据，按文档隔离划分为 2,098/450/450。MLP 结构为 `8→32→16`，共有 884 个参数，包含 sigmoid repair head 和三分类 scale-prior head。

在受控注入缺陷映射上：

- repair trigger Accuracy/F1 = 1.000；
- scale prior top-1/macro-F1 = 1.000；
- 平衡测试集仅将 50% 输入路由至修复；
- 结合实测完整修复成本，预计平均从 1.0 call、11.445 s 降至 0.5 call、5.722 s。

论文已明确将该结果称为 controlled-split sanity check 和成本投影，不把它写成自然缺陷上的完美泛化结果。

### 5.6 独立语义可靠性实验

从 Ours 与 No Repair 的输出中按三领域平衡抽取 180 条三元组，使用独立 `google/gemma-4-26B-A4B-it` judge，盲化方法名和 gold label：

- judge score 与 exact gold validity 的 Pearson `r=0.794`；
- Spearman `rho=0.807`；
- 两项 `p<2.4e-40`；
- Ours 平均支持分为 1.000，No Repair 为 0.917；
- 固定 50 条样本以 temperature 0.1 重复五轮，每轮均值均为 0.96，item SD 和 run-mean SD 均为 0。

该实验只支持独立 judge 在当前服务与样本上的相关性和重复性，不替代人工评价。

### 5.7 Neo4j LLM Knowledge Graph Builder 对比

针对“与网上 Text-to-KG 工具比较”的建议，新增了 Neo4j Labs LLM Knowledge Graph Builder 的可复现核心对比：

- 调用 `LLMGraphTransformer`，而不是手工操作网页；
- 使用 45 条平衡 TNEWS 文档；
- 两边使用 `Qwen3.8-27B-no-thinking`、temperature 0 和相同 category/relation vocabulary；
- Ours 分类正确 25/45，Graph Builder 为 24/45；
- 两边不一致的 5 条中，3 条支持 Ours，2 条支持 Graph Builder；
- exact McNemar `p=1.00`。

论文据此只声称在该受控协议下表现 **comparable**，没有声称优于 Neo4j 平台。该实验评价从文本到图谱的更宽 extraction path，与主 paired repair benchmark 分开解释。

### 5.8 失败审计

Ours 未修复 9/450 个缺陷，当前审计覆盖全部失败：

- invalid relation：3；
- missing triple：2；
- reversed edge：1；
- wrong value：3。

九个失败均位于 government 域的长法律依据或多阶段责任字段。当前结论收敛为：source grounding 能减少虚构替换，但长字段的精确 span 恢复仍困难；后续最直接的技术方向是 chunk-aware span selection/copying。

### 5.9 辅助 corpus-level 结果

旧的四维 `Q_score` 实验仍作为辅助一致性证据保留：完整系统相对 degraded 输入平均提高 8.89 分。它不再承担主实验结论，因为实例级 defect repair、clean-fact preservation 和 triple F1 更直接。

## 6. 实验图和方法图修改

### 6.1 当前图表体系

论文只保留与当前证据链直接对应的图：

- 主修复 benchmark；
- 按缺陷类型的诊断与组件消融；
- 独立语义可靠性；
- 路由效率；
- 完整失败审计；
- 三张方法图。

旧的聚合柱状图、折线图和未被当前主张支持的 convergence、weight sensitivity、web-search ablation 等图已从投稿稿件和活动图目录中移除，避免与当前实验设计混淆。

### 6.2 字体、格式和清晰度

- 所有八张活动图均为 vector PDF；
- 图中文字、粗体和数学标签统一为 Times New Roman；
- 方法图依据作者原 PNG 的结构和视觉元素重新绘制；
- 同时保留原始 PNG、投稿用 PDF 和可编辑 SVG；
- LaTeX 正文只引用 PDF；
- 图表可由 `paper1/make_method_figures.py` 和 `paper1/make_submission_figures.py` 重建；
- 重建图表不需要 API 请求或下载模型。

## 7. 参考文献与 DMKD 格式修改

对 `paper1/references.bib` 全部 45 条记录以及当前正文引用进行了逐条核查，主要修复包括：

- 更正 Lin 2025、Bian 2025、Wienand 2014 的作者信息；
- 补全 CoT、RAG、Pan 等文献的作者；
- 将无法核实的旧 KG quality survey 元数据组合替换为可核实正式文献；
- 将 Ji、Pan Roadmap、White Prompt Catalog 等更新为正式发表信息；
- 将实验中实际使用的 Gemma 4 对齐到对应技术报告和模型卡；
- 补全 DOI、卷期、页码和 BibTeX 大小写保护；
- 修正 NBFNet、MINERVA、MetaR、CoT、RAG 等文献在正文中的作用描述；
- 删除“现有方法都没有约束”等过强概括，补入 AMIE、RuDiK 和约束嵌入相关工作。

DMKD 要求正文采用作者—年份引用并按作者排序。论文已从 `sn-nature` 数字制切换到 Springer Nature 官方 `sn-basic` 样式，正文括号引用统一为 `\citep`。

最终状态：

- 45 条 BibTeX；
- 当前正文引用 44 个独立键；
- 无缺失键、重复键或重复 DOI；
- `.bbl` 中 44 条与正文引用集合完全一致；
- 仅旧 Qwen 技术报告未被当前论文引用；
- BibTeX warning 为 0，无 undefined citation。

仍需在投稿前人工确认 Lin 2025、Bian 2025、Pan position paper 和 Gemma 4 technical report 的最新发表状态，因为当前可核实版本仍属于预印本或技术报告。

## 8. 论文结构与论述调整

当前 DMKD 投稿入口为 `paper1/main.tex`，活动章节为：

- `sections/abstract.tex`；
- `sections/introduction.tex`；
- `sections/related_work.tex`；
- `sections/overview.tex`；
- `sections/implementation.tex`；
- `sections/experiments.tex`；
- `sections/conclusion.tex`。

主要调整包括：

- 摘要、引言和结论改为围绕 paired repair evidence 和受约束神经策略；
- 实验章节由旧的聚合分数叙述重写为 benchmark、baselines、ablation、router、semantic reliability、external comparison 和 failure audit；
- 删除未实现的 retrieval、增量更新和 convergence 声明；
- 删除与 `overview.tex`、`implementation.tex` 重复且内容过时的 `sections/methodology.tex`；
- 明确论文不声称全局最优、自然缺陷完美泛化或外部平台 superiority；
- 旧 ACL 草稿不参与投稿编译。

## 9. 代码、数据和复现材料

| 内容 | 位置 |
| --- | --- |
| DMKD 投稿主文件 | `paper1/main.tex` |
| 方法正文 | `paper1/sections/overview.tex`、`paper1/sections/implementation.tex` |
| 实验正文 | `paper1/sections/experiments.tex` |
| 运行时约束优化器 | `content_enhancement/constraint_optimizer.py` |
| paired benchmark | `exps/paper1_repair_benchmark/` |
| 神经路由实验 | `exps/decision_network/` |
| Neo4j 外部对比 | `exps/neo4j_graph_builder_benchmark/` |
| 方法图生成 | `paper1/make_method_figures.py` |
| 实验图生成 | `paper1/make_submission_figures.py` |
| 方法—实现审计 | `docs/audits/paper1_method_implementation_audit.md` |
| 参考文献审计 | `docs/audits/paper1_reference_check.md` |
| 参考文献证据 | `docs/audits/paper1_reference_sources.json` |

主 benchmark 的复现顺序：

```bash
python3 exps/paper1_repair_benchmark/build_benchmark.py
python3 exps/paper1_repair_benchmark/run_benchmark.py --split test --workers 4
python3 exps/paper1_repair_benchmark/analyze_results.py
python3 exps/paper1_repair_benchmark/analyze_ablations.py
python3 exps/paper1_repair_benchmark/build_failure_audit.py
python3 exps/paper1_repair_benchmark/semantic_reliability.py
```

API key 只从被 Git 忽略的本地 `api` 文件读取，不写入论文、日志汇总或实验产物。本轮没有下载本地模型。

## 10. 验证结果

最近一次方法修订后的验证结果：

- `constraint_optimizer.py` Python 编译检查通过；
- optimizer 与 decision-data 定向测试通过；
- 当前 59 个 LaTeX label 唯一，引用均可解析；
- Tectonic 编译成功，生成 27 页 `paper1/main.pdf`；
- 无 unresolved references、undefined citations 或 overfull box；
- 方法图 PDF 已确认使用嵌入式 Times New Roman，且为矢量内容；
- 剩余信息为模板已有的 underfull-box、旧 `algorithm.sty` 编码和 Tectonic 重跑提示，不影响当前编译结果。

## 11. 近期提交索引

以下提交共同构成本轮修订，按时间顺序列出：

| 提交 | 内容 |
| --- | --- |
| `012319f` | 增加 Neo4j Text-to-KG 对比 |
| `93dfbf2` | 补齐投稿关键 baseline 与 ablation |
| `2d4ea1f` | 固定 corruption 和 split 的可复现性 |
| `e91bb3a` | 建立 paired repair benchmark |
| `a236b57` | 增加统一 benchmark runner 和指标测试 |
| `12a0826` | 加入 API 限流恢复 |
| `5e3ad20` | 按文档隔离重新训练 router，消除数据泄漏 |
| `07b95f1` | 将 benchmark 对齐到可用共享模型 |
| `a784811` | 删除无实现支持的 retrieval 和 convergence 声明 |
| `0f0a90e` | 增加可复现 failure audit |
| `92295a2` | 增加组件消融分析 |
| `12ab12e` | 增加独立语义可靠性协议 |
| `3d8de9f` | 修正 environment clean semantic score |
| `b761c96` | 对齐 environment aggregate score |
| `0c1b1b9` | 增加 paired benchmark 文档 |
| `9fa97f1` | 防止修复输出被截断 |
| `dc3a0fb` | 强制 baseline 输出合法 JSON escaping |
| `35eaf5b` | 归档完整 benchmark 结果与预测 |
| `5538e79` | 完成语义可靠性和路由成本验证 |
| `52f610f` | 将论文评价中心切换到 paired repair benchmark |
| `820fec6` | 明确 DMKD 投稿源文件和构建入口 |
| `0846a44` | 重做投稿图并清理旧图 |
| `3966ff2` | 全图 Times New Roman，方法图重建为矢量版本 |
| `d34e701` | 核查参考文献并对齐 DMKD 引用格式 |
| `af7e121` | 正式化受约束神经修复策略并同步实现 |

## 12. 当前投稿前检查重点

当前版本已经达到“可以进入投稿前精修”的状态。剩余工作应集中在以下事项，而不再扩展新的大规模方法分支：

1. 由作者和导师确认标题、贡献列表与“constrained neural repair policy”的最终措辞；
2. 对照 DMKD 最新 author checklist 检查匿名、声明、数据与代码可用性、图表尺寸和补充材料；
3. 人工通读 27 页 PDF，检查分页、浮动体位置、表格字号和英文表达；
4. 再次核实四条预印本/技术报告是否已有正式发表版本；
5. 确认 benchmark 中共享模型与独立 judge 的可复现访问说明适合公开；
6. 若不新增方法，只处理审稿风险最高的“方法—实验逐项对应”和“自然缺陷外推边界”。

这份汇总记录的是当前仓库中的最终状态。若它与较早的草稿、旧图或旧实验说明冲突，应以当前 `paper1/main.tex`、活动 sections、归档 benchmark 结果以及两份审计报告为准。
