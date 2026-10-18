# MCP 知识图谱项目

项目包含知识图谱构建与修复代码、两篇论文，以及对应的实验记录。论文当前入口如下。

| 要做什么 | 打开哪里 |
|---|---|
| 修改、阅读 Paper1 当前稿 | [paper1 merge/](<paper1 merge/README.md>) |
| 修改、阅读 Paper2 当前稿 | [paper2/](paper2/README.md) |
| 下载 Paper1 完整 Overleaf 项目 | [paper1_merge_overleaf.zip](<paper1 merge/paper1_merge_overleaf.zip>) |
| 下载 Paper2 完整 Overleaf 项目 | [paper2_overleaf.zip](paper2/paper2_overleaf.zip) |
| 阅读 Paper1 完整中文译文 | [main_zh.pdf](<paper1 merge/main_zh.pdf>) |
| 看老师的原稿、合并前的 Paper1 | [paper1/](paper1/README.md) |
| 找文件、了解本次整理 | [目录说明与迁移清单](docs/organization/README.md) |

## 目录怎么分

| 目录或文件 | 用途 |
|---|---|
| `paper1 merge/`、`paper2/` | 两篇论文的当前源码、PDF 和 Overleaf 交付包 |
| `paper1/` | 合并前 Paper1 的压缩归档、老师原稿，以及实验使用的画图样式文件 |
| `content_enhancement/`、`evaluate_kg/` | 图谱检查、修复和评价代码 |
| `exps/` | 实验代码、冻结配置、输出和评分结果；[实验索引](exps/README.md) |
| `data/` | 数据集、图谱 CSV 和规则测试数据 |
| `scripts/`、`rule_generate_scripts/` | 数据转换、数据准备、监控和规则工具 |
| `tests/` | 离线验证和原有测试 |
| `docs/` | 使用说明、方法解释和目录说明 |
| `archive/` | 旧论文、旧导出包、历史文档和运行日志 |
| `outputs/` | 程序生成的图谱等输出 |
| `kg_server*.py`、`kg_client*.py` 等根目录 Python 文件 | 原有程序入口和模块；保留路径以便现有命令和实验继续使用 |

## 论文目录里的文件都需要吗

- `main.tex`、`sections/`、`figure/`、文献、模板和字体：当前论文的编译输入。
- `main.pdf`：当前阅读版。Paper1 的 `main_zh.pdf` 是完整中文译文。
- `overleaf/` 和 ZIP：从当前源码生成的交付副本。日常修改根目录源码，下载时用 ZIP。
- `docs/`：数学与实验导读、进度、合并说明和投稿材料；不参与论文编译。
- `tools/`、`validation/`：构建工具和核对记录；不需要上传到 Overleaf。
- `archive/`：历史版本和旧材料，已退出当前编译流程，保留以便追溯。

上传 Overleaf 时选择完整 ZIP，主文件选 `main.tex`，编译器选 **XeLaTeX**。

## 运行程序

在仓库根目录执行：

```bash
uv sync
uv run kg_server.py
```

API 配置保存在本地 `.env` 或 `apis`。配置示例是 `.env.example`、`apis.example`。

详细使用方法见 [中文说明](docs/usage/SYSTEM_USAGE_ZH.md)、[英文说明](docs/usage/SYSTEM_USAGE_EN.md)。本次目录整理保留实验、数据和运行模块的内容，不调用模型或重跑实验。
