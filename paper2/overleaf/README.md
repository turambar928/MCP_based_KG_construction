# Paper2：完整 Overleaf 项目

更新：2026-10-10。正文、附录、图片、参考文献和字体文件均已包含。

## 使用方法

1. 在 Overleaf 选择 **New Project → Upload Project**，上传 `paper2_overleaf.zip`。
2. 在项目设置中，将主文件设为根目录的 **main.tex**，编译器设为 **XeLaTeX**。
3. 点击 **Recompile**。也可将此文件夹中的全部文件上传到空项目，保持目录结构。

`main.pdf` 是本版本的阅读预览。上传后从 `main.tex` 重新编译即可生成论文。
本项目只需要 Overleaf 提供的标准 TeX Live，不需要本仓库、Python 或外部论文文件。

## 文件说明

| 文件或目录 | 内容 |
|---|---|
| `main.tex` | IEEE 期刊模板、匿名作者信息和章节顺序 |
| `sections/abstract.tex` | 摘要 |
| `sections/introduction.tex` | 引言 |
| `sections/related_work.tex` | 相关工作 |
| `sections/methodology.tex` | 方法 |
| `sections/experiments.tex` | 全部主文实验和表格 |
| `sections/conclusion.tex` | 结论 |
| `sections/appendix.tex` | 全部附录实验和表格 |
| `figure/` | 当前论文使用的 PDF 插图 |
| `references.bib` | 参考文献 |
| `fonts/` | TeX Gyre Termes 字体、来源和许可证 |
| `latexmkrc` | XeLaTeX 编译设置 |

每个章节的内容都在该文件内，章节文件不再引用其他 TeX 文件，也不需要单独的 `tables/` 文件夹。
项目使用本地现有的 `IEEEtran` journal 模板；`IEEEtran.cls` 和 `IEEEtran.bst` 由 Overleaf 标准 TeX Live 提供。
正文优先使用 Times New Roman。没有该字体时，自动使用项目内的 TeX Gyre Termes。
正文、公式、实验数值、章节顺序和匿名作者信息与整理前相同。
