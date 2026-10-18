# Paper2 当前稿

题名：*Knowledge Graph Repair with Reinforcement Learning and Two Rule Prompts*。使用 IEEE 期刊模板，当前为匿名作者版本。

## 阅读与下载

- [论文 PDF](main.pdf)
- [完整 Overleaf ZIP](paper2_overleaf.zip) · [Overleaf 文件夹](overleaf/)
- [数学导读](docs/guides/MATHEMATICS.md) · [PDF](docs/guides/MATHEMATICS.pdf)
- [实验导读](docs/guides/EXPERIMENTS.md) · [PDF](docs/guides/EXPERIMENTS.pdf)
- [进度与下一步](docs/PROGRESS.md) · [任务清单](docs/TODO.md)
- [主实验与 benchmark 说明](docs/guides/BENCHMARK_GUIDE.md)
- [下一步实验协议](docs/protocols/NEXT_EXPERIMENT_PROTOCOL.md)

在 Overleaf 选择 **Upload Project** 上传 ZIP，主文件选 `main.tex`，编译器选 **XeLaTeX**。完整包自带备用字体。向作者已有的云端项目同步内容时，按其模板设置操作。

## 修改哪里

| 位置 | 用途 |
|---|---|
| `main.tex`、`sections/` | 当前正文和 7 个章节文件，表格已内嵌 |
| `figure/`、`fonts/`、`references.bib` | 当前编译需要的图片、字体和文献 |
| `docs/` | 导读、进度、协议、结果解释和投稿草稿 |
| `tools/` | Overleaf 打包与方法图绘制脚本 |
| `assets/` | 可编辑 SVG 图稿及预览 |
| `validation/` | 当前 Overleaf 依赖清单 |
| `archive/` | 整理前完整快照、旧模板、旧表格、未引用图片和旧审计记录 |

根目录两份 `AUTOMATIC_RULE_REVIEW_*.md` 保留原路径，供冻结实验的校验与报告脚本使用：[冻结协议](AUTOMATIC_RULE_REVIEW_PROTOCOL_2026-10-08.md)、[结果和恢复条件](AUTOMATIC_RULE_REVIEW_RESULTS_2026-10-08.md)。

## 当前实验状态

自动核验曾发出 1 次请求，返回模型标识未满足冻结协议，另 37 个任务未派发。下一步先核实模型别名和配置，再按协议处理后续结果。具体结果与待办以 [PROGRESS](docs/PROGRESS.md) 为准。

实验代码和保存的输出仍在 `../exps/`；[复现说明](../docs/paper2_experiment_reproducibility.md)保留实验对应关系。

## 构建

修改根目录源码后，在仓库根目录更新交付包：

```bash
python3 paper2/tools/build_overleaf.py
python3 scripts/maintenance/check_repository.py --compile-papers
```

打包读取当前 PDF。需要修改正文并生成新 PDF 时，先在本目录用 XeLaTeX 或 Tectonic 编译 `main.tex`，再打包。

本次整理保留正文、公式和实验数值。[整理说明与迁移清单](../docs/organization/README.md)可用于查找旧文件。
