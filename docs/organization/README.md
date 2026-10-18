# 仓库整理说明

整理日期：2026-10-18。整理前提交：`e660538`。本次整理调整目录和维护脚本，保留两篇当前论文的正文、公式、图表、阅读 PDF、实验数据与代码。

| 论文目录 | 整理前顶层条目 | 整理后顶层条目 |
|---|---:|---:|
| `paper1/` | 54 | 4 |
| `paper2/` | 51 | 17 |
| `paper1 merge/` | 49 | 17 |

顶层条目按非隐藏文件和文件夹计数。必要的源码和编译依赖继续保留在当前目录，历史材料集中归档。

## 现在从哪里开始

| 任务 | 当前位置 |
|---|---|
| Paper1 日常修改 | [paper1 merge/](<../../paper1 merge/README.md>) |
| Paper2 日常修改 | [paper2/](../../paper2/README.md) |
| 老师原稿 | [paper1/zt/](../../paper1/zt/) |
| 数学、实验导读 | 各论文的 `docs/guides/` |
| 论文进度 | 各论文的 `docs/PROGRESS.md` |
| 下载编译 | 各论文根目录的完整 Overleaf ZIP |
| 实验和评分 | [exps/](../../exps/README.md)；保留原路径 |

## 哪些文件需要保留

当前编译只需要 `main.tex`、`sections/`、用到的图片、参考文献、模板和字体。`overleaf/` 是这些文件的完整交付副本；ZIP 用来上传。修改只在论文根目录源码进行，然后运行 `tools/build_overleaf.py` 更新副本。

数学与实验导读、投稿信、进度有阅读和投稿用途，收进 `docs/`。构建脚本收进 `tools/`，当前校验清单收进 `validation/`。未引用的旧图、旧模板、拆分表格和历史日志收进 `archive/`。

`paper1/` 的合并前版本已压缩归档；当前用 `paper1 merge/`。老师 `zt/` 原位保留。`paper1/figure_style.py` 和 Paper2 根目录两份自动核验文档保留原路径，满足实验导入、冻结校验和报告生成的依赖。

## 主要旧位置与新位置

| 旧位置 | 新位置 |
|---|---|
| `paper1/` 的合并前项目 | `paper1/archive/before_repository_cleanup_2026-10-18.zip` |
| `paper1 merge/MATHEMATICS.*`、`EXPERIMENTS.*` | `paper1 merge/docs/guides/` |
| `paper2/MATHEMATICS.*`、`EXPERIMENTS.*` | `paper2/docs/guides/` |
| 论文根目录 `build_*.py` | 各论文的 `tools/` |
| 论文根目录 `OVERLEAF_MANIFEST.json` | 各论文的 `validation/` |
| 合并版的合并对照文档 | `paper1 merge/docs/merge/` |
| 论文根目录的旧编译日志和审计 | 各论文 `archive/records/` |
| 合并版译文的逐段翻译、术语表 | `paper1 merge/translation_zh/source/` |
| 译文的构建与校验脚本、记录 | `translation_zh/tools/`、`translation_zh/validation/` |
| `paper2/figure/` 未用于正文的图 | `paper2/assets/figures/` 或 `paper2/archive/unused_figures/` |
| 根目录 `paper.tex`、`exports/`、`logs/` | `archive/manuscripts/`、`archive/exports/`、`archive/runtime_logs_2025/` |
| 旧的根目录说明和演示图片 | `docs/usage/`、`docs/assets/demo_images/` |
| 旧修改记录、旧译文 | `archive/docs/` |

逐文件位置与整理前 SHA-256 见 [RELOCATION_2026-10-18.json](RELOCATION_2026-10-18.json)。三份论文目录均保存了整理前完整 ZIP；ZIP 内保留原目录前缀。老师稿不包含在这些 ZIP 中，也不加入 Git 提交。恢复旧文件时，解压到单独目录再取所需内容。

## 核对和维护

```bash
python3 scripts/maintenance/check_repository.py
python3 scripts/maintenance/check_repository.py --compile-papers
```

检查涵盖当前论文依赖和正文校验值、原始归档、实验与代码文件、文档链接、老师原稿、Overleaf 内容及独立编译。结果写入 [VALIDATION_2026-10-18.json](VALIDATION_2026-10-18.json)。

本次已核对 2,174 个代码、数据和实验文件，以及 231 个当前文档本地链接。两份 Overleaf ZIP 均解压独立编译，文本和页数与当前 PDF 一致。19 项离线测试通过；Paper2 的 38 个冻结请求通过原校验。老师 9 个文件的路径和内容均保持不变。

Python 缓存、LaTeX 中间文件和旧页面预览可重建。`.venv` 和本地配置继续保留，本地机器配置与凭据不作为项目源码跟踪。
