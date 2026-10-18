> Follow-up, 2026-09-21: the independent SROIE receipt evaluation is now in
> `exps/paper1_external_receipts/`; ready-to-send human review files and Chinese
> instructions are in `exps/paper1_human_review/`. This document preserves the
> preceding audit. Human review remains pending.

# Paper 1 执行路径与投稿证据修订（2026-09-21）

## 结论与投稿状态

本轮完成了可执行的代码修复、机制实验、基线补充、稿件改写和图表更新，但**不能据此宣布达到 DMKD 投稿标准**。两个实质缺口仍在：独立非字段序列化文本的验证，以及真实人员的独立标注。

最重要的新发现：来源文本由 reference 字段值拼接而成。只读取该来源格式和公开 schema 的 Source-field Copy 在 controlled/natural 各 225 条输入上均达到 100% F1 和 exact match，且不调用模型。该结果已经加入主表、主图、摘要与局限，不能被忽略。

## 1. 方法与执行路径对齐

原 98% headline 来自规则预处理、诊断条件生成和输出过滤，没有调用多轮优化器。当前标题改为 **Source-Grounded Constraint Validation for Document-Level Knowledge Graph Repair**，方法公式和 Algorithm 1 改为实际执行的候选验证流程。

真实运行完整优化器：225 controlled + 225 natural，分别使用 learned 与 always-uniform prior，共 900 条记录；保留每个 trial graph、profile、效用与约束判断。源码中来源去空白而 tail 未同步去空白的错误已修复并重跑，另保留 900 条修复前轨迹。受控 repair 仍为 32%，没有增益；自然 F1 修复后为 88.33%。因此不将优化器、RL 或 neural routing 包装为主结果来源。

当前数学只保证生成候选内的 schema/source 可行性及每关系最多一个值的最大基数选择，不保证事实正确性、输入事实完整保留或全局修复最优性。

## 2. 同提示、同候选实验

固定此前已冻结的 60 个文档（每域 20 个），controlled/natural 两种输入条件，base/diagnostic/SHACL 三种上下文。所有新实验只调用 Gemma；GPT/Claude 没有新调用。原 Claude 结果仅离线复用。每个模型响应同时评分 raw 和 gate，避免 gate 消融重新生成候选。

| 条件 | 方法 | n | Repair | Triple F1 | Exact |
|---|---|---:|---:|---:|---:|
| controlled | base_gate | 60 | 0.9750 | 0.9962 | 0.9500 |
| controlled | base_raw | 60 | 0.9750 | 0.9951 | 0.9500 |
| controlled | diagnosis_gate | 60 | 0.9250 | 0.9861 | 0.8333 |
| controlled | diagnosis_raw | 60 | 0.9250 | 0.9850 | 0.8333 |
| controlled | shacl_context_gate | 60 | 0.9500 | 0.9912 | 0.9000 |
| controlled | shacl_context_raw | 60 | 0.9500 | 0.9912 | 0.9000 |
| natural | base_gate | 60 | — | 0.9252 | 0.6667 |
| natural | base_raw | 60 | — | 0.9185 | 0.6667 |
| natural | diagnosis_gate | 60 | — | 0.9147 | 0.6667 |
| natural | diagnosis_raw | 60 | — | 0.9079 | 0.6667 |
| natural | shacl_context_gate | 60 | — | 0.9364 | 0.7000 |
| natural | shacl_context_raw | 60 | — | 0.9322 | 0.7000 |

本次匹配实验不支持诊断上下文的独立优势：controlled 的 diagnostic+gate F1 为 98.61%，低于 base+gate 的 99.62%（差 -1.01 个百分点，95% CI [-1.67, -0.38]）。natural 中 diagnostic+gate 为 91.47%，SHACL-context+gate 为 93.64%，不能声称优于该适配基线。过滤器在 natural diagnostic 输出上提高 F1 约 0.69 个百分点，exact match 不变；360 个响应共拒绝 27 个非 reference 候选，支持有限的候选验证作用。

完整配对 CI 和随机化检验见 `exps/paper1_mechanism_audit/results.json`。以文档为抽样单位，保留同一文档的两个缺陷聚类结构；多机制比较作为探索性估计，不声称 family-wise significance。

## 3. 最接近的约束修复基线

依据 Lin et al. (2025), arXiv:2507.22419, Section 5/Figure 5，实现五段式 M+G SHACL 上下文，并使用真实 pySHACL 校验。为公平比较，将 SPARQL edits 改为完整 JSON，加入相同来源证据，按文档合并为一次调用。这是明确标注的适配，不是官方代码复现，也不代表胜过该工作的所有设定。

## 4. 自然错误与人工审查

按 all/parsed/parsed-dirty/parsed-clean/malformed 分层。215 条 valid JSON 的 F1 从 92.09% 提高至 93.53%；其中 67 条缺陷输入平均 error reduction 为 24.00%，F1 从 74.61% 到 79.22%。148 条初始正确图由旧 Diagnosis + Gate 完整保留。

原冻结 200 条输入差异表不变；新增 200 条实际系统修改盲审。两位标注者看到独立表格，方法身份另存协调员映射。评分脚本保留独立 U 标签，先算 kappa 再单独报告裁决结果；退化的 kappa 报告 null。人工标签仍为空，没有生成虚假一致性数字。

## 5. 撤回旧 router/LODO 部署结论

旧特征从 clean graph 读取 expected_relations，且 S_iso 等定义与 runtime 不一致。旧文件保留用于追溯，但不再作为部署证据。新 gold-free 回放仅使用可观察违反，450 输入中调用比例 6.22%，漏检率 63.64%，输出 F1 94.46%；always-call 为 95.82%。这是缓存结果回放，不是在线调度 latency。

## 6. 规模与图表

重新测量实际诊断 report 的 1K–50K 文档批次计算。内存只表示新建 batch 的 Python allocation peak，来源文本共享，不是完整进程 RSS 或互联 KG 内存。新增流程图、自然分层图、匹配机制图和诊断规模图，并在受控结果图加入 Source-field Copy。活动图均为 Times New Roman 矢量 PDF。

## 7. 复现与运行状态

360 个最终实验请求（重试另计）已全部归档。前期两个批次因网关限流/并发准备问题被整体中止，单独归档且不参与质量比较；没有挑选成功响应。最终子集是旧的固定 60-case 子集，不按新结果选样。本次 cost 表只报告最终批次，第一次中止批次未保存响应，不能反推整次会话总计费。

代码与复现：`exps/paper1_mechanism_audit/README.md`。论文：`paper1/main.tex`、活动 sections 与本地 `paper1/main.pdf`。最后的测试/编译/推送状态见 Git 提交与本轮交付说明。

## 8. 投稿前尚未解决的事项

1. 获取与 reference 字段拼接过程独立的原始自然文本及可靠三元组标注；保留字段复制基线，检验何时其不能解决任务。
2. 完成两位真实标注者的独立审查与裁决；若 reference 存在系统偏差，重新计算结果。
3. 根据上述新证据决定是否仍以方法论文投 DMKD。当前版本提高了透明度，但没有凭空增加技术新颖性。
