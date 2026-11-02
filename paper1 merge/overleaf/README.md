# Paper1：老师意见合并版完整 Overleaf 项目

更新：2026-11-02。正文、附录、图片、参考文献和 Springer 模板均已包含。

本轮在用户恢复的长版引言上调整行文，保留约 880 词的展开和独立三条贡献。顺序为背景、问题、解决思路、支撑技术、贡献列表，最后一句报告实验结果。摘要和相关工作沿用此前修改。

本次已修正 CUAD 出版信息，补齐 TNEWS/CLUE 与主文 SROIE 引用，并调整相关工作中的引用表述。

## 上传与编译

1. 在 Overleaf 选择 **New Project → Upload Project**，上传 `paper1_merge_overleaf.zip`。
2. 主文件设为根目录的 **main.tex**，编译器设为 **XeLaTeX**。
3. 点击 **Recompile**。也可上传此文件夹的全部文件，保持目录结构。

`main.pdf` 是本版本的阅读预览。项目使用标准 TeX Live，不需要原仓库或外部论文文件。

## 编辑位置

| 文件或目录 | 内容 |
|---|---|
| `main.tex` | 标题、模板、作者信息和章节顺序 |
| `sections/abstract.tex` | 摘要 |
| `sections/introduction.tex` | 第 1 章引言 |
| `sections/related_work.tex` | 第 2 章相关工作 |
| `sections/methodology.tex` | 第 3 章任务与方法、第 4 章实现 |
| `sections/experiments.tex` | 第 5 章实验和全部主文表格 |
| `sections/conclusion.tex` | 第 6 章结论 |
| `sections/declarations.tex` | 作者声明 |
| `sections/appendix.tex` | 附录及其表格 |
| `figure/` | 当前论文使用的 PDF 插图 |
| `references.bib` | 参考文献 |
| `sn-jnl.cls`、`sn-basic.bst` | Springer 模板及文献样式 |
| `latexmkrc` | XeLaTeX 编译设置 |

引言先集中说明三个问题，再说明共享评估概况的思路和支撑技术。词汇与句式保持简单。老师的方法改写和批注已融入第 3、4 两章。

章节文件不再引用其他 TeX 文件。标题、模板、作者信息和已核验实验数值沿用最新基稿。
