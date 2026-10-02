# Paper1 / Paper2 Overleaf 导入包

2026-10-02 从当前英文稿导出，包含正文、参考文献、表格、当前引用的 PDF 插图和附录。两篇各自独立，不需要上传整个项目仓库，也不需要调用 API。

**10-02 本轮修订已同步。**两个 ZIP 是包含全部附录的完整审阅稿。TKDE 已确认补充材料须与主文分文件提交；当前 Paper2 ZIP 尚未做此拆分，不能直接作为最终投稿包。详见 [投稿准备记录](../../docs/submission_readiness_2026-10-02.md)。

## 上传与编译

1. 在 Overleaf 中选择 **New Project → Upload Project**。
2. 上传 `paper1_overleaf.zip` 或 `paper2_overleaf.zip`；两篇分别创建一个项目。
3. 打开项目设置（Settings / Menu），将 **Main document** 设为根目录的 `main.tex`，将 **Compiler** 设为 **XeLaTeX**。使用平台提供的近期稳定版 TeX Live。
4. 点击 **Recompile**。引用未更新时，使用 **Recompile from scratch** 清理缓存后重编译。
5. 左侧编辑 `sections/` 中的正文；参考文献在 `references.bib`；图在 `figure/`。Paper2 的部分表格在 `tables/`。

压缩包根目录直接包含 `main.tex`。不需要运行 Python、不需要 shell escape，也不需要在线转换 SVG。`latexmkrc` 同样指定 XeLaTeX；仍建议在界面明确选择该编译器。

## 两篇模板与字体

| 项目 | 当前模板 | 字体处理 |
| --- | --- | --- |
| Paper1 | Springer `sn-jnl`，`sn-basic` 样式 | 保留原稿模板与字体设置；已附带 `sn-jnl.cls` 和 `sn-basic.bst` |
| Paper2 | `IEEEtran`，`journal` 模式 | 正文优先使用 Times New Roman；环境缺少时自动使用包内 TeX Gyre Termes |

Paper2 的 `IEEEtran.cls`、`IEEEtran.bst` 由 Overleaf 的标准 TeX Live 提供。这里保留的是当前 IEEE 期刊模板，没有改换另一套 TKDE 模板。Paper1 保留实际作者信息，Paper2 保留原稿的 Anonymous Authors。

Paper2 的字体兼容设置仅存在于导出副本的 `overleaf-fonts.tex`，仓库原稿没有修改。TeX Gyre Termes 为可再分发的 Times 风格字体，四个字形和许可证均放在 `fonts/`；压缩包没有附带商业 Times New Roman 字体。切换字体可能轻微改变断行或分页。PDF 插图保持原文件，其嵌入字体不受正文字体回退影响。

## 导出与验证

- 只收集 `main.tex` 实际引用的依赖，排除未使用的旧稿、旧图、API 配置、原始实验数据和编译缓存。
- `EXPORT_MANIFEST.json` 记录原始文件与导出文件的 SHA-256，方便检查内容一致性。
- 仓库中的 `build_packages.py` 可重新导出两篇 ZIP，`validate_packages.py` 可解压到独立临时目录后检查编译、引用、源文件一致性和 Paper2 的字体回退。
- 本地验证使用 Tectonic 的 XeTeX 引擎，结果见仓库同目录的 `validation.json`；这不等于已经在 Overleaf 云端实测。两个 ZIP 均不依赖仓库外的论文文件。
- 正文、数学、实验数字和插图内容保持原样；此次导出只处理上传与编译所需文件。

在仓库根目录重新生成、验证：

```bash
python3 exports/overleaf_2026-10-02/build_packages.py
python3 exports/overleaf_2026-10-02/validate_packages.py
```

本地验证需要 `tectonic`、`pdftotext`、`pdfinfo`、`pdffonts`，以及已有的 TeX 包缓存；正常上传 Overleaf 不需要这些本地工具。
