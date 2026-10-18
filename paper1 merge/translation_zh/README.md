# Paper1 合并版完整中文译文

译文日期：2026-10-18。

下载：[完整中文 PDF](../main_zh.pdf)，共 37 页。对应的英文文件是 [main.pdf](../main.pdf)，英文题名为 *Repairing Document Knowledge Graphs with Source Text and Field Checks*。

本轮同步英文稿按老师引言结构所作的改写。中英文引言均覆盖研究背景、抽取质量问题、现有方法、评估、约束、路由及贡献。对应源码和英文 PDF 的校验值见 [来源清单](validation/SOURCE_MANIFEST.json)。

译文覆盖摘要、引言、相关工作、任务与方法、实现、实验、结论、声明和完整附录。包含原稿的 16 个独立公式、21 张表、11 幅图、2 个算法和 43 条参考文献。公式符号、表格数值和引用关系与英文稿逐项核对。

正文、标题、表头、图注和算法说明译为中文。原图保留，末尾附有全部 11 幅图的英文标注中文对照。作者姓名、模型标识和程序名称保留原文。参考文献保留原始题名、作者与出版信息，便于检索。

## 文件与重建

- `main.tex` 和 `sections/`：可编辑的中文 LaTeX，保留与英文稿相同的 8 个章节文件。
- `figure/`、`references.bib`、`sn-jnl.cls`、`sn-basic.bst`：本译文使用的图片、文献和模板。
- `figure_text_zh.tex`：译文附页中的原图文字对照。
- `source/`：逐段译文 `prose_*.txt`，以及标题、图表说明和术语对照 TSV。
- `tools/`：译文构建与校验脚本。
- [来源校验值](validation/SOURCE_MANIFEST.json)、[翻译覆盖记录](validation/TRANSLATION_COVERAGE.json)、[内容验证](validation/VALIDATION.json)：对应版本与核对结果。
- [页面目检记录](validation/VISUAL_REVIEW.json)：检查标题页、正文、公式、算法、表格、参考文献和全部附录页面。

在仓库根目录运行：

```bash
python3 'paper1 merge/translation_zh/tools/build_translation.py'
python3 'paper1 merge/translation_zh/tools/verify_translation.py'
```

重建需要 Tectonic、缓存中的标准 LaTeX 包，以及 Noto Serif/Sans/Mono CJK 字体。已生成的 PDF 内嵌字体，可直接阅读。译文脚本只读取对应版本的英文稿。本次目录整理保持中英文正文及 PDF 内容不变。
