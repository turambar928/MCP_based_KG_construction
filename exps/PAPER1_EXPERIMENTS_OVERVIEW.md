# Paper 1 实验总览（DMKD 投稿版）

更新日期：2026-09-21。

**执行路径更正**：以下早期结果中的 Full System 实际是 Diagnosis + Gate 一次调用流程。它未调用独立多轮优化器。新审计见 `paper1_mechanism_audit/report.md`；旧 router/LODO 和 profile scaling 已被更严格的输入审计与重新计时替代。

论文定位已收窄为 **document-level KG repair**。Local、graph、source 是同一文档图内的三个证据范围；当前结果不支持跨文档对齐、因果推理或大型互联 KG 的通用能力主张。

## 1. 受控配对 benchmark

- 1,499 个 clean/corrupted 文档图，2,998 个 manifest 缺陷；
- 按源文档划分 70/15/15，seed 42；
- 测试集 225 个文档、450 个缺陷；
- 六类缺陷：missing、duplicate、invalid relation、reversed edge、wrong value、hierarchy conflict。

| 方法 | Repair | Preservation | Over-repair | Triple F1 | Exact | Calls | Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct LLM | 0.9244 | 0.9687 | 0.0758 | 0.9520 | 0.8267 | 1 | 7.25 s |
| ReAct-style | 0.8911 | 0.9324 | 0.1667 | 0.9213 | 0.5956 | 2 | 20.50 s |
| **Simple Pipeline** | **0.9511** | 0.9723 | 0.0705 | 0.9634 | 0.8400 | 1 | 9.27 s |
| **Full System** | **0.9800** | **0.9932** | **0.0167** | **0.9917** | **0.9333** | 1 | 11.44 s |

Simple Pipeline 使用相同结构预处理、同一个 Claude、一次调用和去重，但不使用 profile、learned prior、trial-state utility 或 constraint gate。Full 相对 Simple 的逐缺陷结果为 15 个仅 Full 成功、2 个仅 Simple 成功，McNemar `p=0.0023499`。

## 2. 自然抽取错误

对同一 225 篇 held-out 文档重新执行真实 Text-to-KG 调用。抽取器只看到来源文本、required head 和关系词表，看不到 clean graph、corrupted graph 或 defect manifest。结构化来源字段作为 silver reference。

- 225 个输出中 215 个 JSON 解析成功，parse success `0.9556`；
- 10 个 malformed JSON 作为空图端到端失败保留；
- 77/225 个输出图与 reference 不一致；
- 总计 302 个 multiset triple discrepancies；
- 没有人工注入错误，也没有平衡错误数量或类别。

| 方法 | Error reduction | Preservation | Over-repair | Triple F1 | Exact |
|---|---:|---:|---:|---:|---:|
| Extracted graph | 0.0000 | 1.0000 | 0.0000 | 0.8799 | 0.6578 |
| Simple Pipeline | -0.5915 | 0.9971 | 0.2389 | 0.8807 | 0.6711 |
| **Full System** | **0.2775** | **1.0000** | **0.0292** | **0.9248** | **0.6844** |

Full 相对 Simple 的 paired F1 差为 `0.0440`，95% bootstrap CI `[0.0307, 0.0577]`；每文档少 `1.0311` 个错误，95% CI `[0.7689, 1.3156]`，one-sided Wilcoxon `p=3.18e-12`。Exact match 的 3 vs 0 discordance 不显著，`p=0.25`。

### 人工标注状态

已冻结 200 条差异样本：

- 文件：`paper1_submission_extensions/natural_error_annotation_sample.csv`；
- population：302；sample：200；seed：42；
- SHA-256：`27a0dd7b0112c3249440b25ea6c549fa6e1495eb50cc499745aff6d41ada3747`；
- 协议：`paper1_submission_extensions/ANNOTATION_PROTOCOL.md`。

两位独立人工标注者和 adjudication 尚未完成。不得把结构化 reference、Gemma judge 或其他模型输出写成人工一致性。填完后运行 `score_human_annotations.py` 计算 raw agreement、Cohen's kappa 和 adjudicated precision。

## 3. Constraint gate 独立贡献

- 逐 proposal 审计 225 个 controlled Full 输出；
- gate 拒绝 8 个候选，原因全部为 `ungrounded`；
- 8 个全部是 non-gold triple；
- 没有拒绝 reference triple；
- gate 不增加 defect repair 数量，但使 over-repair 从 `0.0227` 降至 `0.0167`，F1 从 `0.9895` 升至 `0.9917`。

结论只能写成 conservative validation，不能写成 gate 负责恢复新事实。

## 4. Router：旧部署结论撤回

旧 `graph_features` 读取 clean reference 的 relation presence，且 S_iso 等特征定义与运行时优化器不同。因此旧 neural router 和 LODO 结果仅保留为历史诊断记录，不能证明真实部署泛化。

新分析 `paper1_mechanism_audit/gold_free_router_replay.csv` 只用输入中的 head、relation、重复、基数和来源支持检查。450 个 natural/clean 输入上，visible-violation 策略仅路由 6.22%，但漏掉 63.64% 的缺陷图；F1 为 0.9446，always-call 为 0.9582。该分析是基于真实修复输出的回放，不是在线调度延迟测量。主方法采用 always-call。

## 5. 跨模型结果

固定 60 个 controlled case，每域 20 个，比较 Claude Haiku 与 Gemma 4。三种方法均为相同输入和一次调用预算。

| Model | Method | Repair | F1 | Exact |
|---|---|---:|---:|---:|
| Claude | Direct | 0.958 | 0.970 | 0.867 |
| Claude | Simple | 0.958 | 0.966 | 0.833 |
| Claude | Full | **0.975** | **0.991** | **0.917** |
| Gemma | Direct | 0.958 | 0.988 | 0.883 |
| Gemma | Simple | 0.967 | 0.984 | 0.867 |
| Gemma | Full | **0.983** | **0.990** | **0.917** |

Qwen 和 GPT 端点在最短测试案例上长时间无响应，因此没有生成或填补它们的同任务结果。端点不可用不能解释为模型性能。

## 6. 诊断层规模实验（重新测量）

新规模数据位于 `paper1_mechanism_audit/diagnostic_scaling.csv`，测量实际使用的 input-derived diagnostic report，替代旧的 reference-aware profile 特征。

输入为 1K、5K、10K、50K triples 的独立文档批次。只测诊断计算与单文档重算，不含 LLM 或多轮优化。内存是构造批次的新 Python allocation peak，来源文本与 schema 共用，不能解释为进程 RSS 或大型互联 KG 的内存需求。

## 7. 复现入口

```bash
python3 exps/paper1_submission_extensions/run_api_experiments.py --stages all --workers 3
python3 exps/paper1_submission_extensions/run_scalability.py
python3 exps/paper1_submission_extensions/analyze_experiments.py
python3 paper1/make_method_figures.py
python3 paper1/make_submission_figures.py
cd paper1 && tectonic -X compile main.tex --keep-logs
```

主要目录：

- controlled benchmark：`exps/paper1_repair_benchmark/`；
- 新实验：`exps/paper1_submission_extensions/`；
- router model：`exps/decision_network/`；
- 论文：`paper1/main.tex` 与 `paper1/sections/`；
- 编译稿：`paper1/main.pdf`。

## 8. 2026-09-21 执行与机制审计

- 冻结候选下实际运行完整优化器：900 条执行记录，受控 repair 仍为 0.32，不再将其作为 0.98 headline 的来源。
- 固定旧有 60 个文档、两种输入条件、三种上下文，Gemma 共 360 个请求（重试另计）。各响应同时评分 raw/gated。
- Lin-style SHACL context 使用真实 pySHACL；差异见 `paper1_mechanism_audit/BASELINE_ADAPTATION.md`。
- 排除 malformed JSON 后，215 个图 F1 从 0.9209 提升至 0.9353；67 个缺陷图平均 error reduction 为 0.2400。
- 两名人工标注仍待完成；新增实际系统修改盲审，并修复 U 标签与裁决前 kappa 的统计处理。

完整复现顺序以 `paper1_mechanism_audit/README.md` 为准。


## 9. 必须报告的来源格式基线

`paper1_mechanism_audit/source_field_baseline.py` 只读取来源字符串、公开字段词表和 document node，在 controlled/natural 各 225 条输入上均达到 F1/exact=1。原因是来源证据由同一组 reference 字段值拼接而成。此基线已进入主表和主图，当前实验不能证明 LLM 方法优于直接字段恢复。真正独立、非字段序列化的自然文本与人工参考仍是投稿前的实质缺口。
