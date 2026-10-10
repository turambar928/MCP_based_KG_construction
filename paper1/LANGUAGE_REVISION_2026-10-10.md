# Paper1 简单英语修改（2026-10-10）

当前状态：**内容定稿待作者确认**。

本轮按要求修改论文语言：常见词、短句、直接表达。正文、附录、图表说明和投稿信同步修改。

## 写法变化

|原写法|当前写法|
|---|---|
|contemporaneous factorial control|testing cleanup, error reports, and filtering together|
|cohort|input group|
|cardinality|field count|
|adjudication|a third reviewer resolves disagreements|
|determinate edits|edits with a clear decision|
|feasibility checks|checks that decide which edits are allowed|
|serialized records|records that list field names and values|
|“does not establish… / cannot claim…” 等叙述|直接写方法步骤、分数、差值、区间和检验结果|

英文正文的平均句长由约 14 词降至约 10 词；当前扫描没有超过 30 词的句子。

标题改为 **Repairing Document Knowledge Graphs with Source Text and Field Checks**。

引言直接介绍任务、方法和贡献。方法按操作步骤写，首次出现的必要术语用简单句解释。实验段先给比较条件，再给观察结果。讨论写下一步可改进的具体环节。删除预先回应质疑和反复解释结论限制的叙述。

## 内容核对

- 保留 20 张实验表的数值、所有数学公式、图片文件、引用键和标签。
- 生成、过滤及顺序选择仍按各自的实际流程描述；样本、解析规则、统计检验与人工判断口径保持原样。
- 两份中文导读同步英文章节名称；投稿信同步标题与语言风格。
- 作者、单位、邮箱及实际待核定声明保留。
- 本轮未调用模型 API、追加实验或新增人工标注。

## 交付和验收

- [论文 PDF](main.pdf)：独立离线编译，33 页。
- [数学导读](MATHEMATICS.md) / [PDF](MATHEMATICS.pdf)
- [实验导读](EXPERIMENTS.md) / [PDF](EXPERIMENTS.pdf)
- [投稿信](COVER_LETTER.md)
- [内容与语言验证](LANGUAGE_VALIDATION_2026-10-10.json)
- [论文编译记录](LANGUAGE_COMPILE_2026-10-10.log)

论文全页缩略图和首页、合同、人工评价、讨论及结论页面已检查，未发现裁切或重叠。当前编译没有未定义引用或 Overfull。重复离线编译后的 PDF 提取文本一致。两份导读 PDF 全页也已目检。模板已有的 Underfull、重复 PDF 锚点和重编译提示记录在日志中。

所有当前交付文件统一放在 `paper1/`，主文件为 `main.tex`。
