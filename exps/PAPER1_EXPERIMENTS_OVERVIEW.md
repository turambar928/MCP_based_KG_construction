# Paper 1 实验总览（DMKD 投稿版）

更新日期：2026-09-17。

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

## 4. Router 真实端到端执行

新增 225 个 clean graph 的真实 Full System 调用，与原有 225 个 dirty 调用组合成 mixed stream。被路由的文档使用实际输出、calls 和 latency；skip 返回输入，不再使用成本投影。

- controlled stream：learned / heuristic / threshold 完全相同，route F1 `1.000`，calls/doc `0.500`；
- natural stream：三者仍完全相同，route F1 `0.842`，FN rate `0.273`，FP rate `0`，calls/doc `0.124`；
- learned router 没有证明独立优于透明策略，因此已从 headline contribution 降为 optional implementation。

Leave-one-domain-out 的 controlled trigger F1 为 environment `1.000`、finance `1.000`、government `0.999`；这只是受控缺陷映射的跨域 sanity check。

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

## 6. Profile scaling

基于真实文档图构造 1K、5K、10K、50K triples 的 disjoint batch。Full profile 为 7 次 CPU 中位数，单文档 incremental update 为 200 次中位数。

| Triples | Documents | Full profile | Incremental | Graph state |
|---:|---:|---:|---:|---:|
| 1K | 143 | 1.48 ms | 0.011 ms | 0.34 MB |
| 5K | 715 | 7.81 ms | 0.012 ms | 1.70 MB |
| 10K | 1,430 | 17.38 ms | 0.029 ms | 3.42 MB |
| 50K | 7,149 | 85.68 ms | 0.012 ms | 17.15 MB |

这里只测部署时的八维 routing profile，不包含 LLM latency 或 all-pairs semantic duplicate search。

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
