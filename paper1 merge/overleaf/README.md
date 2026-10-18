# Paper1：老师意见合并版完整 Overleaf 项目

更新：2026-10-18。正文、附录、图片、参考文献和 Springer 模板均已包含。

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

本轮按老师 `zt/introduction.tex` 的论述顺序重写第 1 章：研究背景、抽取质量问题、现有方法、多尺度评估、约束、路由、整体方法、实验概览和贡献。词汇与句式保持简单。老师的方法改写和批注已融入第 3、4 两章。

章节文件不再引用其他 TeX 文件。标题、模板、作者信息和已核验实验数值沿用最新基稿。
