# Paper2 章节内容更新包（2026-10-04）

本包只同步 Paper2 的论证与实验组织。TKDE 模板由作者在 Overleaf 维护，本轮未改 `main.tex`、文档类、导言区、字体、版心或图文件。

## 已上传章节但出现 No PDF：先补缺失表格

之前的局部包只含六个章节，漏带了部分 Overleaf 版本尚未包含的 `tables/offline_loop_ceiling.tex`。这是打包遗漏，不是你的 TKDE 模板有问题。

最小修复：下载 `paper2_missing_table_fix.zip`，解压后把其中 `tables/offline_loop_ceiling.tex` 放入 Overleaf 项目根目录的 `tables/` 文件夹，然后选择 **Recompile from scratch**。不需要重新替换章节或模板。`Citation/Reference undefined` 可能由本次提前中断引起；修复后若仍出现，检查文献库和引用配置。`Underfull` 是排版警告，不是此次停止原因。

## 同步到你的 Overleaf 项目

重新下载已修正的 `paper2_sections_update.zip`。它包含下面六个更新章节，以及从这些章节递归引用的所有 `.tex` 内容依赖（`tables/` 表格和其他子章节）。保留目录结构，按需要同步到已有项目：

|文件|改动|
|---|---|
|`sections/abstract.tex`|明确训练结果来自固定规则注册表，补充生成规则执行研究的定位。|
|`sections/introduction.tex`|把调度、候选生成、修复覆盖连接起来；贡献描述引用当前奖励下的消融。|
|`sections/methodology.tex`|解释注册表中的删除/增强动作与实际文本生成的关系；区分八动作学习环境、四命令回放桥和响应级开发环境。公式与算法原样保留。|
|`sections/experiments.tex`|按调度、生成、执行及开发验证组织证据；正文保留主要比较和负结果，压缩过程性说明。|
|`sections/conclusion.tex`|对应三个实验阶段归纳结论，指出可靠候选及有效调度问题是后续学习整合的前提。|
|`sections/appendix.tex`|接收原正文中的规则家族检查、SHACL/TNEWS/抽取辅助测试、类型审计、详细计时及复现记录。|

这些文件沿用 `sections/`、`tables/` 和 `figure/` 路径。此前“无新增依赖文件”的说明只对当时本地仓库成立，未覆盖你较早导出的 Overleaf 项目；修正版会同时携带 `tables/offline_loop_ceiling.tex` 等内容依赖。`experiments.tex` 与 `appendix.tex` 必须同步，因为部分内容和引用已移动。LaTeX 会重新计算章节、图表编号，不要在 Overleaf 手工固定旧编号。

如果你已经将附录独立成补充文件，请把 `appendix.tex` 的内容改动合并到对应文件，并保留你设置的跨文件引用；本包不改变该安排。如果你还修改过这六个文件内的格式命令，可参照 `content_changes.patch` 合并文字改动，以保留自己的设置。补丁中的原路径带 `paper2/`，仅作为逐项查看差异的入口。

不要用旧的完整 Overleaf ZIP 覆盖已调好的项目。本包没有 `main.tex`、模板、参考文献、字体或图片；它依赖你现有的完整项目，不能单独创建一份可编译论文。

## 核对范围

所有原有标签和外部输入均保留。六个文件中的 14 个 equation 环境、2 个算法、3 个内嵌表格和 7 个图形环境与修改前逐项一致；其余公式、图表所在文件也保持不变。

修正后还从更新 ZIP 解压全部 TeX 内容依赖到独立项目进行编译（另供既有模板、参考文献和图片），并单独核对最小修复包补齐缺失表格。`dependency_validation.json` 记录该次检查。

原 `validation.json` 与 `compile.log` 保留章节修订时的检查记录。本地编译使用仓库原有模板及缓存的 Tectonic，仅核验内容依赖与引用，不代表已访问或验证你在 Overleaf 中的新 TKDE 模板。`validation.json` 记录来源哈希与检查结果，`compile.log` 保留模板原有警告。

本轮模型 API 请求为零，未新增或重跑实验。旧中文译文和 10-02 完整 Overleaf 包仍对应各自标注日期；本轮局部更新以此包为准。
