# Paper1：完整 Overleaf 项目

更新：2026-10-10。正文、附录、图片、参考文献和 Springer 模板文件均已包含。

## 使用方法

1. 在 Overleaf 选择 **New Project → Upload Project**，上传 `paper1_overleaf.zip`。
2. 在项目设置中，将主文件设为根目录的 **main.tex**，编译器设为 **XeLaTeX**。
3. 点击 **Recompile**。也可将此文件夹中的全部文件上传到空项目，保持目录结构。

`main.pdf` 是本版本的阅读预览。上传后从 `main.tex` 重新编译即可生成论文。
本项目只需要 Overleaf 提供的标准 TeX Live，不需要本仓库、Python 或外部论文文件。

## 文件说明

| 文件或目录 | 内容 |
|---|---|
| `main.tex` | 模板、作者信息和章节顺序 |
| `sections/abstract.tex` | 摘要 |
| `sections/introduction.tex` | 引言 |
| `sections/related_work.tex` | 相关工作 |
| `sections/methodology.tex` | 方法与实现；保留论文第 3、4 章 |
| `sections/experiments.tex` | 全部主文实验和表格 |
| `sections/conclusion.tex` | 结论 |
| `sections/declarations.tex` | 作者声明 |
| `sections/appendix.tex` | 全部附录实验和表格 |
| `figure/` | 当前论文使用的 PDF 插图 |
| `references.bib` | 参考文献 |
| `sn-jnl.cls`、`sn-basic.bst` | Springer 模板及参考文献样式 |
| `latexmkrc` | XeLaTeX 编译设置 |

每个章节的内容都在该文件内，章节文件不再引用其他 TeX 文件。
正文、公式、实验数值、章节顺序和作者信息与整理前相同。
