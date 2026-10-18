# Paper1 当前稿：老师意见合并版

更新：2026-10-18。状态：**内容定稿待作者确认**。当前引言已按老师 `zt` 稿的论文结构重写。

## 阅读与下载

- [英文论文 PDF](main.pdf) · [完整中文译文 PDF](main_zh.pdf)
- [完整 Overleaf ZIP](paper1_merge_overleaf.zip) · [Overleaf 文件夹](overleaf/)
- [数学导读](docs/guides/MATHEMATICS.md) · [PDF](docs/guides/MATHEMATICS.pdf)
- [实验导读](docs/guides/EXPERIMENTS.md) · [PDF](docs/guides/EXPERIMENTS.pdf)
- [老师稿与之前版本的区别](docs/merge/VERSION_COMPARISON_AND_MERGE.md) · [PDF](docs/merge/VERSION_COMPARISON_AND_MERGE.pdf)
- [老师方法批注对照](docs/merge/TEACHER_MERGE_2026-10-12.md)
- [进度](docs/PROGRESS.md) · [投稿信](docs/submission/COVER_LETTER.md) · [作者待核定事项](docs/submission/SUBMISSION_CHECKLIST.md)

英文和中文论文均为 37 页。Overleaf 选择 **Upload Project** 上传 ZIP，主文件选 `main.tex`，编译器选 **XeLaTeX**。

## 修改哪里

| 位置 | 用途 |
|---|---|
| `main.tex` | 标题、作者信息、模板设置和章节顺序 |
| `sections/` | 8 个当前章节文件；`methodology.tex` 同时包含第 3、4 章 |
| `figure/`、`references.bib`、`sn-jnl.cls`、`sn-basic.bst` | 当前编译所需图片、文献和模板 |
| `docs/guides/` | 数学与实验导读 |
| `docs/merge/`、`docs/submission/` | 合并说明、投稿材料 |
| `translation_zh/` | 完整中文译文源码；[构建说明](translation_zh/README.md) |
| `tools/` | 构建与校验脚本 |
| `validation/` | 当前依赖清单、编译日志和检查结果 |
| `archive/` | 整理前完整快照、旧日志和历史审计记录 |

修改根目录的 `sections/`，再用构建脚本同步交付副本。`overleaf/` 由脚本生成。

## 构建与检查

在仓库根目录执行：

```bash
python3 'paper1 merge/tools/build_manuscript.py' --log-date 2026-10-18
python3 'paper1 merge/tools/build_overleaf.py'
python3 'paper1 merge/tools/verify_merge.py' --report-date 2026-10-18 --compile-zip
```

导读重建：`python3 'paper1 merge/tools/build_guides.py'`。更新合并对照 PDF 时加 `--names VERSION_COMPARISON_AND_MERGE`。

本机脚本使用 Tectonic；导读还需要 Pandoc 和 Noto CJK 字体。当前 [合并校验](validation/MERGE_VALIDATION_2026-10-18.json)、[排版记录](validation/VISUAL_REVIEW_2026-10-18.json)及 [Overleaf 文件清单](validation/OVERLEAF_MANIFEST.json)均在 `validation/`。

本次只整理文件位置，英文正文、中文正文和实验结果保持一致。合并前 Paper1 已完整归档，老师原稿仍在 `../paper1/zt/`。[仓库整理说明](../docs/organization/README.md)记录新旧位置。
