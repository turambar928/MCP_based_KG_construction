# Paper2 简单英语修改（2026-10-10）

当前状态：**本轮语言内容稿已完成**。后续实验任务与作者云端模板按 [进度记录](PROGRESS.md) 处理。

本轮采用与 Paper1 相同的写法：常见词、短句、直接表达。修改范围包括主文、当前引用的附录、算法标题、图表说明和表头。

## 写法变化

|原写法|当前写法|
|---|---|
|validator registry|fixed rule library|
|feasibility mask|action mask，并说明它列出允许的动作|
|elicitation task|prompt task 或直接说明模型读什么、输出什么|
|provenance|source links / original source|
|materialization|compiling|
|abstention|skip the decision|
|supplementary clauses|extra sentences|
|without establishing / cannot be attributed / remain unestablished|直接写分数、区间、统计量或实际操作|

正文平均句长由约 14.6 词降至约 9.7 词；当前扫描没有超过 30 词的句子。

本地标题改为 **Knowledge Graph Repair with Reinforcement Learning and Two Rule Prompts**。

RL、Double DQN、两种规则生成方式仍是论文主线。方法按输入、动作和输出说明；必要术语用简单句解释。结果直接给比较条件、分数、差值和对应操作。固定规则库的训练与生成规则的固定流程各按实际流程报告。

## 内容核对

- 保留 19 张当前实验表的数值和 15 个显示数学块。
- 保留图片资产、参考文献、引用标签、样本分母、统计方法及冻结协议。
- 保留当前匿名作者设置；本地 `main.tex` 仅改标题。
- 两份中文导读同步新英文章节名，并重新导出 PDF。
- 本轮没有调用模型 API、追加实验、增加训练或新增人工标签。
- 历史协议、停止记录与未引用的旧版本按原档案保留。

## 交付与验收

- [论文 PDF](main.pdf)：独立离线编译，18 页。
- [数学导读](MATHEMATICS.md) / [PDF](MATHEMATICS.pdf)
- [实验导读](EXPERIMENTS.md) / [PDF](EXPERIMENTS.pdf)
- [内容与语言验证](LANGUAGE_VALIDATION_2026-10-10.json)
- [论文编译日志](LANGUAGE_COMPILE_2026-10-10.log)

论文全 18 页及两份导读 PDF 已目检，未发现裁切或重叠。重复离线编译后的提取文本一致。当前没有 Overfull 或未定义引用。字体路径、Underfull 和模板重编译提示记录在日志中。

所有修改文件放在 `paper2/`。作者云端模板继续保留；同步内容时更新标题与引用的章节、表格及图片，保持作者已有模板设置。
