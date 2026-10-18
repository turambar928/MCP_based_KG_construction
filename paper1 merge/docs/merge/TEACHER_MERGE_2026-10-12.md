# Paper1 老师意见合并对照

更新：2026-10-12。状态：**内容定稿待作者确认**。

本版把老师的“问题—检查—约束—选择—执行”思路融入现有结构。英文使用短句，先讲目的，再讲步骤和公式。所有修改都在 `paper1 merge/`。原 `paper1/`、`paper1/zt/` 和 `paper2/` 保持原样。

## 采用的基稿与结构

完整项目来自 `paper1/overleaf/`，基稿提交为 `e8757f60e86eda6dafd2b5e5ba98907d5f0b8b91`。老师意见以 `paper1/zt/method.tex` 为主，同时吸收 `overview.tex`、`introduction.tex` 和 `related.tex` 的组织思路。

`sections/` 仍有 8 个文件。第 3、4 两章同放在 [methodology.tex](../../sections/methodology.tex) 中：

| 论文位置 | 内容 |
|---|---|
| 3 Task and Method | 任务、检查与修复模块，说明两条修复路径 |
| 3.1 Input Cleanup and Error Report | 先说明错误类型，再给出清理和报告 |
| 3.2 Generating a Graph from Source Text | 模型根据原文提出完整图 |
| 3.3 Checking the Generated Triples | 来源、字段和单值约束及过滤数量公式 |
| 3.4 Field Meanings and Source Lines | 字段含义、固定行提示和空白规则 |
| 4.1 Repair Steps | 主流程与 Algorithm 1 |
| 4.2 Prompt and Rule Settings | 共用提示词和 SHACL 对照 |
| 4.3 Scale-Aware Routing and Edit Actions | 先讲选择目的，再给评分、网络、训练与编辑成本 |
| 4.4 Trial Checks and Repair Loop | 完整试改评分、允许条件和 Algorithm 2 |

第 5 章实验、附录、作者声明、标题、作者信息、模板、文献库和全部图片沿用基稿。三张方法图继续使用原 PDF：`image2.pdf` 为 Figure 1，`image1.pdf` 为 Figure 2，`image3.pdf` 为 Figure 3。

## method.tex 中的 14 条批注

行号指原始 `paper1/zt/method.tex`。每条批注都有一个落实位置。下表保留老师的原话片段，完整原话仍在原文件中。

| 批注行 | 老师原话片段 | 合并后的处理与定位 |
|---|---|---|
| 8 | “more about the enhancement module” | 第 3 章开头说明检查模块怎样接入修复模块，并介绍生成过滤和逐次选编辑两条路径；`sec:framework`。 |
| 23 | “why we have this module. how we connect the problem with the solution” | 3.1 用重复、非法字段、来源不符三个例子说明为什么要分组检查；`sec:framework:profile`。 |
| 24 | “meaning of topic sentence is not clear” | 3.1 首句改为 “Different errors need different checks.”，随后逐一解释三类错误。 |
| 27 | “need a topic sentence” | 三类 scope 前说明它们分别检查局部错误、图规则和原文证据；4.3.1 首句说明 profile 使用四个分数。 |
| 28 | “tedious. no insight there” | scope 只保留当前任务中的含义和具体例子；四个分数按错误率统一计算，后接用途说明。 |
| 31 | “explain the equation and its insight. condense tedious details about normailzation” | 3.3 解释来源要求、字段计数和最大保留数量；4.4 在选择公式后解释“约束决定允许范围，得分决定顺序”；`eq:eligible_candidates`、`eq:admissible_subsets`、`eq:selection_size`、`eq:constrained_opt`。 |
| 49 | “quality state vector vs quality assessment profile” | 正文统一称 assessment profile。主流程用报告 `D`，选择器用评分 `s`；4.3.1 明确两者在各自流程中的作用；`eq:diagnostic_context`、`eq:quality_state`。 |
| 64 | “add a topic paragraph … reason and insight … equation enviroments” | 4.3.1 先说明四项分数的检查目标，再显示评分、错误率和密度公式，解释各分子和分母；`eq:quality_state`、`eq:profile_rates`、`eq:routing_inputs`。3.1 也显示三个字段检查公式；`eq:diagnostic_predicates`。 |
| 74 | “rename … to ‘scale-aware routing’ … totally remove it” | 改为 Scale-Aware Routing and Edit Actions；引言、摘要、结论及导读同步使用 scale-aware routing，正文删除泛称 neural decision。 |
| 75 | “what to update and how to update? … routing mechanism based on the profile” | 4.3 开头先提出选下一项编辑的问题，再解释 profile、scope 权重和试改得分怎样支持选择；`sec:method:decision`。 |
| 81 | “merge … logic … conflict … costs … profile … model” | 路由与动作合入 4.3。开头说明编辑可能冲突，随后介绍 profile、网络和训练，最后给候选编辑与成本。4.4 比较每次试改的收益和代价；`sec:impl:optimizer_audit`、`sec:method:modalities`。 |
| 83 | “do not emphasize ‘lightweight’ … Add another paragraph” | 4.3 开头只说明选择任务；4.3.2 再给 8→32→16 结构、ReLU、两类输出和 884 个参数；`eq:decision_net`、`eq:decision_loss`。 |
| 118 | “merge this subsubsection with the previous one” | 原路由与执行方式合在同一 4.3 小节；4.3.3 紧接网络和训练介绍三种编辑及组合成本；`eq:cost_hierarchy`。 |
| 136 | “introduce the whole process(loop) and algorithm” | 4.4 按复制图试改、重新评分、检查边界、选最高正分编辑、更新 profile、停止的顺序说明全过程；`eq:action_utility`、`alg:enhancement`。 |

## 按当前实现落实老师思路

方法说明以现有代码和已有测试为准，新增公式把已有程序步骤写清楚。

| 老师的设计思路 | 本版对应内容 | 核对来源 |
|---|---|---|
| 三类检查支持定位问题 | 局部重复与节点连接、文档 ID 与字段规则、原文值匹配 | `content_enhancement/constraint_optimizer_v2.py`；`exps/paper1_mechanism_audit/protocol.py` |
| 多项分数形成 profile | 节点连接、字符对相似组、不同违规三元组比例、去空白来源匹配；四项取平均 | `MultiScaleConstraintOptimizer.assess`、`_redundant_excess_rate`、`_semantic_penalty` |
| profile 驱动路由 | 四个分数和四个图统计量，经训练集缩放后输入 884 参数网络 | `FphiRouter.predict`；`exps/math_revision_20260925/paper1/router/train.py` |
| 说明网络怎样得到 | 已知注入缺陷给修复标签和主要 scope 标签；干净图只训练修复输出；按文档分组 | `exps/math_revision_20260925/paper1/study.py`；`scale_targets`；`loss_and_grads` |
| 不同动作有不同代价 | 删除 0.30、改关系 0.16、添加 0.06；组合动作按总成本计 | `MultiScaleConstraintOptimizer.__init__`、`_utility` |
| 在每轮选择最好的允许动作 | 完整图试改得分含质量差、违规减少、成本、scope 先验和候选置信度 | `_optimize_and_apply`、`_utility` |
| 约束界定可提交编辑 | 四项下界 55/55/60/45、每项最多回退 2 点、密度上界 0.75、非空图保持非空 | `_check_constraints` |
| 迭代过程有明确终点 | 最高正分允许编辑被提交；无编辑、低触发分或达到 12 轮时停止；同一图和候选组合只试一次 | `_optimize_and_apply`；`exps/math_revision_20260925/paper1/study.py` |

当前 context 指文档原文。方法说明采用已有的字段检查和原文匹配。候选来自规则及已保存的模型输出。路由标签来自注入缺陷，试改按完整图评分。循环写成程序实际使用的停止条件。这些内容替换老师旧稿中的跨文档因果检查、在线外部检索、检查器自标注、局部近似评分和“五轮收敛”描述。

主流程与顺序选择器各有算法和测试。98.00% 修复率对应生成与过滤路径；路由与逐次选择对应 5.4 和附录 A.2 的独立配置。原实验值和配置名称保持不变。

## 其他老师文件怎样处理

| 老师文件 | 合并方式 |
|---|---|
| `overview.tex` | 吸收检查与修复模块连接的思路，写入第 3 章开头；框架图放到 4.3 的路由路径中。 |
| `introduction.tex` | 按“检查哪些问题—留下哪些改变—怎样选编辑”组织引言，贡献与现有方法、测试对应。 |
| `related.tex` | 保留构建与检查、质量与 scope、修复与动作选择三类相关工作；使用现有文献库。 |
| `method.tex` | 作为主要意见源，14 条批注全部落到上表位置。 |
| `abstract.tex`、`conclusion.tex` | 与新的方法表达同步，实验数字沿用当前基稿。 |
| `methodology.tex`、`implementation.tex` | 作为历史设计资料核对；具体方法由当前代码和实验配置说明。 |
| `experiments.tex` | 实验使用当前基稿；老师文件中的 +8.89、+2.30 和 web-search 测试留在原历史文件中。 |

来源核对：老师 `abstract.tex` 和 `methodology.tex` 与 Git 提交 `48466c6` 的对应章节逐字节相同，`implementation.tex` 与 `8bd240a` 的对应章节逐字节相同。`method.tex` 含本轮主要改写和批注。老师的实验稿引用 8 个旧实验图片路径；现有项目使用当前结果对应的图片。

## 老师稿中的未定义引用

原文献库中有 8 个未定义键。合并版按具体论点使用库内已有来源，文献库文件保持原样。

| 未定义键 | 本版处理 |
|---|---|
| `ref_zhu2023`、`ref_wu2022` | 引言改写为一般 KG 背景，使用 `ref_ji2021`；旧稿的特定应用例子省去。 |
| `ref_chen2022` | 一般图谱修复背景使用 `ref_paulheim2017`。 |
| `ref_bansal2023` | 规则与图检查使用 `ref_kontokostas2014`。 |
| `ref_sun2019` | 向量与连接预测背景使用 `ref_bordes2013`、`ref_wang2017`。 |
| `ref_liu2024` | LLM 与 KG 的一般背景使用 `ref_pan2023`，SHACL 修复使用 `ref_lin2025`。 |
| `ref_wang2020` | 一般质量背景使用 `ref_wang2021`；pLogicNet 的具体介绍使用现有 `ref_qu2019`。 |
| `ref_zhang2023` | LLM 与 KG 的综述使用 `ref_bian2025`、`ref_pan2025`。 |

## 同步材料和验证

摘要、引言、相关工作、方法、结论、投稿信和两份中文导读已同步。完整论文、干净 Overleaf 项目、ZIP 和验证记录都在本目录。

[完整论文](../../main.pdf) · [完整 Overleaf ZIP](../../paper1_merge_overleaf.zip) · [数学导读](../guides/MATHEMATICS.pdf) · [实验导读](../guides/EXPERIMENTS.pdf) · [验证记录](../../archive/records/MERGE_VALIDATION_2026-10-12.json)

原目录校验覆盖全部 323 个文件，并检查文件路径集合。编译使用本机 Tectonic 的 XeTeX 引擎；Overleaf 设置为 XeLaTeX。作者声明继续按实际信息核定，清单见 [SUBMISSION_CHECKLIST.md](../submission/SUBMISSION_CHECKLIST.md)。
