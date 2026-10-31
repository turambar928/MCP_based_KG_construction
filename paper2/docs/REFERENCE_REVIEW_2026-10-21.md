# Paper2 参考文献核查与补充

日期：2026-10-21。范围：当前 `main.tex`、7 个章节文件、`references.bib`、PDF 和完整 Overleaf 项目。

## 完成结果

正文实际引用由 **17 篇增至 30 篇**。修订前文献库已有 30 条，但其中 13 条没有正文引用。此次新增 10 条相关文献，启用 3 条原有相关文献，移出 10 条仍未使用的条目。当前文献库和 PDF 均为 30 篇，每篇都有明确引用位置。

英文正文继续使用简单词汇和短句。新增内容集中在研究背景、质量检查、规则学习和实际方法出处。实验结论、数字、公式、表格、图片和匿名作者信息保持不变。

## 新增的 13 篇实际引用

| 文献 | 引用用途 |
|---|---|
| Ji et al., 2022，KG 综述 | 引言中的知识图谱背景 |
| Paulheim, 2017，Knowledge Graph Refinement | 引言和相关工作中的图修复任务 |
| Zaveri et al., 2016，Quality Assessment for Linked Data | 相关工作中的质量维度 |
| Kontokostas et al., 2014，Test-driven Evaluation | 基于测试的数据质量检查 |
| Paulheim and Bizer, 2014，Statistical Distributions | 统计分布用于发现错误 |
| Qu and Tang, 2019，pLogicNet | 逻辑规则与图嵌入的结合 |
| Qu et al., 2021，RNNLogic | 规则生成器与答案预测器的联合训练 |
| Kingma and Ba, 2015，Adam | 实际使用的优化器 |
| Qwen Team, 2025，Qwen3 Technical Report | 生成脚本的 Qwen3-32B 默认模型 |
| Xu et al., 2020，CLUE | TNEWS/CLUE 数据集出处 |
| Holm, 1979 | 多重比较校正 |
| Gemma Team, 2026，Gemma 4 Technical Report | 文档开发测试使用的 Gemma 模型 |
| Wilson, 1927 | RuleTest-94 的 Wilson 区间 |

Zaveri、Paulheim and Bizer、Wilson 原已在文献库中，此次修正或补齐信息后加入正文。其余 10 篇为新增条目。DocRED 原已在附录引用，此次也在主实验首次介绍数据时引用。

Qwen3 文献只放在明确写有 Qwen3-32B 默认设置的位置。单独抽取测试中的 `Qwen3.8-27B-no-thinking` 原始记录保留，未用 Qwen3 报告替它证明模型身份。Gemma 文献与 `exps/paper2_rule_feasibility_20261004/common.py` 等实验文件记录的 `google/gemma-4-26B-A4B-it` 相符。

## 已修正的文献信息

| 原问题 | 处理 |
|---|---|
| Zaveri 条目写作 *Quality Assessment Methodologies for Linked Open Data*，与给定 DOI 的正式题名不一致 | 改为 *Quality Assessment for Linked Data: A Survey*；保留正确卷期、页码和 2016 刊期 |
| KEPLER 用 `@inproceedings` 表示 TACL 期刊论文 | 改为 `@article`，补齐 7 位作者、卷 9、176–194 页和 DOI |
| SHACL 被写成期刊论文 | 改为 `@misc`，明确 W3C Recommendation，并给出固定版本标准页 |
| ShEx 被写成期刊论文 | 改为会议论文，补齐作者、32–40 页和 DOI |
| KG-BERT 把 arXiv 当作会议名称 | 改为预印本，补齐 3 位作者、编号和链接 |
| CoT 被写成期刊论文 | 改为 NeurIPS 会议论文，补齐 9 位作者、卷 35、24824–24837 页和 DOI |
| RuDiK 缺少卷期页码，PVLDB 条目类型不准确 | 采用原文首页的 PVLDB 11(12), 1946–1949 (2018)，补齐 3 位作者和 DOI，改为 `@article` |
| DeepPath、Multi-Hop Reward Shaping 的会议名称简写且缺页码 | 按 ACL Anthology 补齐会议名称、页码、DOI 和链接 |
| DQN、Double DQN、Neural LP、ReAct 等只写部分作者或缺来源 | 补齐可核实作者、正式会议或期刊信息以及 DOI/原文 URL |
| 多个缩写可能被样式转成小写 | 为 KG-BERT、BERT、KEPLER、ReAct、RuDiK、Qwen3、SHACL 等保留大小写 |
| 新增 URL 含下划线时原模板编译失败 | 在 `main.tex` 加载标准 `url` 包及 `hyphens` 选项，支持链接字符和换行 |

RuDiK 保留本稿原来引用的演示论文 *RuDiK: Rule Discovery in Knowledge Bases*。它与 Paper1 引用的 ICDE 论文 *Robust Discovery of Positive and Negative Rules in Knowledge Bases* 是两篇作品，本次没有混合它们的题名和出版信息。

Adam 的引用同时放在准确的位置：Adam 对应学习率，折扣系数单独描述。公式和两个参数值不变。

## 来源与核查方法

- 共有文献采用本次 Paper1 核查中取得的 Crossref、arXiv、W3C、NeurIPS 与 ACL 记录，并逐项对应到 Paper2 当前条目。
- DeepPath、Multi-Hop Reward Shaping、KEPLER 和 DocRED 使用 ACL 官方记录。Neural LP 使用 NeurIPS 官方 BibTeX。RuDiK 使用 [PVLDB 原文](https://www.vldb.org/pvldb/vol11/p1946-ortona.pdf)和对应 DOI 登记。
- DQN、Double DQN、Wilson 的出版信息使用出版社登记的 Crossref 记录；Adam 与 KG-BERT 使用 arXiv 原记录，Adam 按 ICLR 2015 会议版本引用。
- Qwen3 与 Gemma 4 采用各自官方模型卡推荐的集体作者引用，不把团队名称当作个人姓名处理。
- Holm 的 JSTOR 原页本轮返回访问限制。作者缩写、题名、年份、卷和页码通过 [R 官方 `p.adjust` 文档](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/p.adjust.html)交叉核对。未将访问受限页面算作已读原文，也未添加猜测的 DOI。
- DBLP 的 RuDiK 页面返回浏览器验证，未采用其响应正文。题名搜索返回的无关论文没有用于补元数据。
- 预印本与技术报告明确标明 arXiv。正式题名保留原文；简单英语要求用于本文新增叙述。

逐条条目、来源、引用位置和验证信息见 `validation/REFERENCE_UPDATE_2026-10-21.json`。原有未使用条目可从 Git 历史和整理前归档追溯。

## 交付与验证

- 主目录和 Overleaf 文献库一致：30 条，正文引用 30 个独立键，编译后的 `.bbl` 为 30 条。
- 无缺失引用键、重复键或重复 DOI；没有靠 `\nocite` 加入未使用文献。
- 英文 PDF 为 19 页。主目录编译和 ZIP 独立解压编译成功，两份 PDF 的提取文本一致。
- 数值序列、公式、表格内容和图片引用与修改前逐项比较一致。没有新增实验、训练或模型调用。
- 已目检第 1、2、4、5、6、10、12、18、19 页，覆盖新增正文及完整参考文献页。未发现引用缺失、文字越界或乱码。
- BibTeX 无警告；最终编译无未定义引用、字体缺字或 overfull 警告。模板仍有部分 underfull 排版提示及既有 `algorithm.sty` 编码提示。
- 历史目录整理与实验冻结记录保留，本轮使用新的引用验证记录。

交付：[论文 PDF](../main.pdf) · [完整 Overleaf ZIP](../paper2_overleaf.zip) · [Overleaf 文件夹](../overleaf/)。
