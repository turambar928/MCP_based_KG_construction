# Paper1：论文源码与 Overleaf 内容入口

当前总览：[进度与下一步（2026-10-10）](PROGRESS.md)。以该文档区分当前任务和下方历史记录。

## 最新完整 Overleaf 项目（2026-10-10）

- [下载完整 ZIP](paper1_overleaf.zip)：在 Overleaf 选择 Upload Project 上传。
- [干净项目文件夹](overleaf/)：只含编译所需文件、说明和论文 PDF。
- 主文件：`main.tex`；编译器：**XeLaTeX**。无需从其他目录拼接文件。

`sections/` 已从 29 个文件整理为 8 个：摘要、引言、相关工作、方法与实现、实验、结论、作者声明、附录。实验小文件和表格已并入所属章节，章节文件不再引用其他 TeX 文件。整理前源码保存在 `archive/before_overleaf_cleanup_2026-10-10/`。

正文、公式、数值、章节顺序和作者信息保持原样。依赖、独立编译、PDF 内容及字体检查见 [整理验证](OVERLEAF_VALIDATION_2026-10-10.json)。以后默认交付 `overleaf/` 和 `paper1_overleaf.zip`。

## 论文导读（2026-10-10）

- [数学导读：逐节对应论文，含例子和公式](MATHEMATICS.md) · [PDF 阅读版](MATHEMATICS.pdf)
- [实验导读：逐节对应设计、结果和结论](EXPERIMENTS.md) · [PDF 阅读版](EXPERIMENTS.pdf)

以上文档已接入最新结果；历史审计与旧实验版本按原档案保留。

## 当前交付：简单英语版（2026-10-10）

**内容定稿待作者确认。** 当前标题为 “Repairing Document Knowledge Graphs with Source Text and Field Checks”。主文、附录和图表说明使用简单词与短句，结果采用直接数字比较。投稿信与两份导读同步。

- [论文 PDF](main.pdf)
- [语言修改说明](LANGUAGE_REVISION_2026-10-10.md)
- [独立编译与内容验证](LANGUAGE_VALIDATION_2026-10-10.json)
- [投稿信](COVER_LETTER.md) / [作者待核定事项](SUBMISSION_CHECKLIST.md)

实验结果、方法公式、统计检验及作者信息保留。上一轮说明见 [实验组织记录](FINAL_REVIEW_2026-10-10.md)。

## 人工回收检查（2026-10-04）

两位标注者各 400 条已完成回收，154 条分歧由第三人裁决，原评分器复算一致。D 输入错误 95/200、建议操作接受 86/200；E 实际操作接受 134/199，另 1 条 U。后者是五种配置的合并抽样结果。详见 [最终人工结果](HUMAN_REVIEW_RESULTS_2026-10-04.md)。摘要、实验、结论、数据声明四份 sections 已更新，表格内嵌，无新增外部依赖，模板未改。

## 文件交付约定（2026-10-10）

论文目录保留源码、进度和实验记录；`overleaf/` 是下载后可直接编译的完整交付入口。每次修改根目录源码后，更新 PDF，再运行 `python3 paper1/build_overleaf.py` 同步干净文件夹和 ZIP，检查依赖并验证编译，再 commit / push。

上传时保持目录结构，项目主文件选择 `main.tex`，编译器选择 XeLaTeX。实验原始数据和代码不作为 Overleaf 编译依赖。旧更新包只作为历史档案。

当前主稿为 `main.tex`，章节在 `sections/`，插图在 `figure/`，参考文献为 `references.bib`。本目录包含所需的 Springer 类文件及参考文献样式。当前编译预览为 `main.pdf`。
