# Paper1 老师意见合并版

更新：2026-10-12。状态：**内容定稿待作者确认**。

所有新修改和交付文件都在本目录。原 `paper1/`、其中的 `zt/` 以及 `paper2/` 保持原样。

## 阅读与下载

- [完整论文 PDF](main.pdf)
- [完整 Overleaf ZIP](paper1_merge_overleaf.zip)
- [干净的 Overleaf 文件夹](overleaf/)
- [老师意见合并对照](TEACHER_MERGE_2026-10-12.md)
- [老师稿与之前版本的关键区别及处理说明](VERSION_COMPARISON_AND_MERGE.md) · [PDF](VERSION_COMPARISON_AND_MERGE.pdf)
- [数学导读](MATHEMATICS.md) · [PDF](MATHEMATICS.pdf)
- [实验导读](EXPERIMENTS.md) · [PDF](EXPERIMENTS.pdf)

在 Overleaf 中选择 **New Project → Upload Project**，上传 ZIP。主文件选 **main.tex**，编译器选 **XeLaTeX**。

## 当前结构

`sections/` 保留 8 个文件。`methodology.tex` 内仍有第 3 章 Task and Method、第 4 章 Implementation。第 5 章实验及附录沿用最新结果。

老师的意见按“问题—检查—约束—选择—执行”合入。第 4 章将路由、候选编辑、训练和试改循环放在一起。三张现有方法图继续使用 PDF 文件。

实验正文、附录、作者声明、文献库、主模板及图片均保留基稿内容。方法新增的公式按当前代码解释已有步骤，没有新增实验或训练。

## 验证和更新

论文 PDF 共 36 页，数学导读 7 页，实验导读 8 页。Overleaf 包含 26 个文件。ZIP 已解压独立编译，输出文本与本目录的论文 PDF 完全一致。老师 14 条批注、全部引用和本地依赖已核对，原目录 323 个文件的路径与校验值均保持不变。

- [原目录文件校验清单](SOURCE_MANIFEST_2026-10-12.json)
- [合并与编译验证](MERGE_VALIDATION_2026-10-12.json)
- [PDF 排版目检记录](VISUAL_REVIEW_2026-10-12.json)
- [当前进度](PROGRESS.md)
- [作者待核定事项](SUBMISSION_CHECKLIST.md)
- [投稿信草稿](COVER_LETTER.md)

只在本目录更新源码。从仓库根目录执行：

1. `python3 "paper1 merge/build_manuscript.py"` 编译论文 PDF。
2. `python3 "paper1 merge/build_guides.py"` 编译两份中文导读 PDF。
3. `python3 "paper1 merge/build_overleaf.py"` 更新完整 Overleaf 文件夹和 ZIP。
4. `python3 "paper1 merge/verify_merge.py" --compile-zip` 校验原目录、实验和依赖，并从 ZIP 独立编译。

本机编译脚本使用 Tectonic 的 XeTeX 引擎，导读另需 Pandoc 和 Noto CJK 字体。Overleaf 使用 XeLaTeX。

更新版本比较说明的 PDF：`python3 "paper1 merge/build_guides.py" --names VERSION_COMPARISON_AND_MERGE`。
