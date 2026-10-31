# Paper1 merge 参考文献检查

检查日期：2026-10-21。对象为当前 `main.tex` 引入的 8 个 section、`references.bib`、英文 PDF 第 26–30 页，以及 Overleaf、ZIP 和中文译文中的文献副本。

**后续修复：2026-10-21，用户确认后已实施下列四项修改。** CUAD 元数据已修正；新增 CLUE 官方文献及 TNEWS 引用；相关工作改为分别说明质量测试与 SHACL；主文收据实验补齐 SROIE 引用。英文、中文及 Overleaf 同步结果见 `validation/REFERENCE_FIX_2026-10-21.json`。下文保留修复前的检查记录与证据。

## 结论

参考文献总体可用。本次核对没有发现题名、作者和链接对应到另一篇论文的情况，但发现 **CUAD 的论文集和卷号错误、TNEWS 缺少数据集引用**。另有两处引用位置或措辞值得调整。具体修正建议如下。

首次检查仅新增本报告和核查证据，当时没有修改论文。以下描述和数字对应修复前状态；后续修复状态见上方说明。

## 一、应修正的问题

### 1. CUAD 的论文集和卷号错误

位置：`references.bib:440`，引用键 `ref_cuad`；英文 PDF 第 27 页。

当前条目写为：

```bibtex
booktitle={Advances in Neural Information Processing Systems},
volume={34},
year={2021}
```

[NeurIPS 官方论文页](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/6ea9ab1baa0efb9e19094440c317e21b-Abstract-round1.html)和其导出的 BibTeX 均表明，该文属于 **Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks，第 1 卷，2021 年**。

当前作者、题名文字和年份正确，但把数据集赛道论文集写成了主会议论文集。当前样式没有显示会议卷号，所以 PDF 看不到错误的 `34`，但源文件仍需修正。

该条目还缺少原文 URL；题名中的 `NLP` 没有用花括号保护，PDF 实际排成了 `nlp`。建议采用：

```bibtex
@inproceedings{ref_cuad,
  title={{CUAD}: An Expert-Annotated {NLP} Dataset for Legal Contract Review},
  author={Hendrycks, Dan and Burns, Collin and Chen, Anya and Ball, Spencer},
  booktitle={Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks},
  volume={1},
  year={2021},
  url={https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/6ea9ab1baa0efb9e19094440c317e21b-Abstract-round1.html}
}
```

官方 BibTeX 的页码为空，因此不补猜测的页码。

### 2. TNEWS 缺少数据集出处，现有引用位置容易混淆

位置：`sections/appendix.tex:418–419`。

当前句子在 “45 balanced TNEWS documents” 后放置 `ref_neo4j_llm_graph_builder`。这条文献介绍的是 Neo4j 软件，不能承担 TNEWS 数据集出处的作用。当前 BibTeX 中也没有 TNEWS/CLUE 文献。

项目的 `exps/external_benchmark_runner.py` 将此数据标为 TNEWS/CLUE，输入路径为 `data/train.json`。建议把 Neo4j 引用紧接在工具名后，并在 TNEWS 后补 [CLUE 原论文](https://aclanthology.org/2020.coling-main.419/)：

> Liang Xu et al. (2020). CLUE: A Chinese Language Understanding Evaluation Benchmark. Proceedings of the 28th International Conference on Computational Linguistics, 4762–4772. DOI: 10.18653/v1/2020.coling-main.419.

正文可写为：

```latex
We compare our extractor with the LLMGraphTransformer core used by
Neo4j Labs' Graph Builder \citep{ref_neo4j_llm_graph_builder} on
45 balanced TNEWS documents from CLUE \citep{ref_clue2020}.
```

新增 `ref_clue2020` 时应从 ACL 官方 BibTeX 获取完整作者列表。数据版本和抽样记录继续由实验材料说明。

## 二、建议调整的引用表达

### 3. “Rule languages” 与所引论文的定位不够贴合

位置：`sections/related_work.tex:32`。

当前句子：

> Rule languages check the graph's schema (Kontokostas et al. 2014).

引用的真实题名是 *Test-driven Evaluation of Linked Data Quality*，DOI 为 [10.1145/2566486.2568002](https://doi.org/10.1145/2566486.2568002)。它与数据质量检查相关，但将它直接概括为“规则语言”不够准确。

建议保留这篇相关文献，改成更具体的两句：

```latex
Test-based methods check linked-data quality \citep{ref_kontokostas2014}.
SHACL checks graph constraints \citep{ref_shacl2017}.
```

这是引用与措辞的精确化，不是认定该文献与本文无关。引言第 28–29 行用它支持规则检查，问题较小，无须一起大改。

### 4. SROIE 引用只在附录，主实验的出处不够直接

位置：`sections/experiments.tex:395` 开始的收据实验；现有 `ref_sroie2019` 引用位于 `sections/appendix.tex:200`。

SROIE 文献本身的作者、题名、年份、1516–1520 页和 DOI 均与登记信息一致。问题在于主文已经报告收据上的主要结果，读者却要到附录才看到数据集引用。

建议在主文收据实验首句明确写出 SROIE 并引用 `ref_sroie2019`。附录的引用可以保留。不需要新加一条重复文献。

## 三、已核实、不应误改的项目

| 项目 | 核查结果 |
|---|---|
| Ji 的 KG 综述 | 最终刊期为 2022 年、33(2)、494–514。键名 `ref_ji2021` 和 DOI 中的 2021 不代表年份错误。 |
| Wei 的 CoT 论文 | 2022 年、24824–24837 页正确；9 位作者完整。键名 `ref_wei2023` 无须为排版而修改。 |
| Pan 的 Roadmap | 2024 年、36(7)、3580–3599 正确。不要按键名 `ref_pan2025` 改成 2025。 |
| White 的 Prompt Pattern Catalog | Crossref 登记出版社为 The Hillside Group、上线日期为 2024-06-24；但 [PLoP 官方推荐引用](https://www.plopcon.org/proceedings/plop/2023/05.html)明确写 ACM, 2023。当前条目有官方依据，不判为错误，不机械按 Crossref 替换。 |
| Chen 的 MetaR | Crossref 给出 4216–4225，但 [ACL 官方记录](https://aclanthology.org/D19-1431/)为 4217–4226。当前采用官方页码，保留。 |
| Lin 的 KG repair 论文 | arXiv 中的题名与 6 位作者匹配。原文明确有五个提示部分以及完整规则/完整图设置，支持当前方法段对该基线的说明。 |
| Gemma 4 | arXiv:2607.02770 可核实；[官方 checkpoint 卡](https://huggingface.co/google/gemma-4-26B-A4B-it)推荐的作者写法正是 `Gemma Team`。当前模型系列、报告和集体作者写法匹配。 |
| Claude Haiku 4.5 | 当前引用链接对应官方发布文章，题名相符，没有把产品页冒充论文或 System Card。 |
| Neo4j 软件 | 仓库可访问；引用中记录的完整 commit 可通过 GitHub 核实，commit 时间为 2026-07-30，早于条目写明的访问日期。 |
| NBFNet、MINERVA、MetaR、ReAct | 当前正文分别描述链接预测、图路径问答、少样本链接预测、推理与行动；没有把这些文献直接当作本文修复效果的证据。 |

## 四、文献库与投稿格式

- `.bib` 共 47 条；实际引用 43 条；独立编译后的 `.bbl` 也为 43 条，集合完全相同。
- 没有缺失的引用键、重复键或重复 DOI。
- 4 条未引用记录为 `ref_ji2023`、`ref_qwen2025`、`ref_shex2014`、`ref_sirin2007`。它们不会进入当前 PDF，属于可选清理项，不是排版错误；不应为了用完文献库而强行补引用。
- 正文作者—年份制和文末按作者排序符合当前 [DMKD 指南](https://link.springer.com/journal/10618/submission-guidelines)的要求。题名按样式转为句首大写正常；`NLP` 这样的缩写需要单独保护。
- Bian 2025、Pan 2023、Lin 2025 仍标明 arXiv 预印本，Gemma 为技术报告。本次对前三篇检索 Crossref，没有核实到题名及作者对应的正式出版条目。这不等于它们一定没有正式版本。投稿时应复核出版状态及期刊对预印本的处理；不能自行给它们补会议名、期刊名或 DOI。
- 当前没有必要为增加数量而补一批引用。优先修正 CUAD，补 TNEWS 出处，调整相关工作的两句和收据主实验中的引用位置。

## 五、检查证据与验证

本次重新查询了 47 条记录的 DOI/Crossref、arXiv 或官方页面，并针对 CUAD、CLUE、PLoP、MetaR、Lin 方法、Gemma checkpoint、Neo4j commit 和期刊指南补查正式来源。Crossref 初次对 5 条记录限流；后续重试均成功。HTTP 成功仅用于确认取回了页面，核查结论来自题名、作者、卷页及页面正文的对照。

逐项元数据、来源 URL、引用位置、补查结果、验证摘要和本轮源文件 SHA-256 保存在：

`validation/REFERENCE_REVIEW_2026-10-21.json`

在独立目录 `.build/reference_review_2026-10-21/compile/` 编译成功，BibTeX 无警告，LaTeX 无未定义引用。新 PDF 的全部提取文本与当前 `main.pdf` 一致。模板仍有重复 PDF destination 等既有警告，未将本次结果描述为“零警告编译”。

已目检当前 PDF 第 26–30 页。除 CUAD 的 `nlp` 小写外，未发现参考文献乱码或文字越界。正常 URL/DOI 换行不属于链接错误。

主目录、Overleaf 文件夹、Overleaf ZIP、中文译文中的 `references.bib` 内容一致。本次检查发现的问题因此也存在于这些副本；实施修正时应统一同步。
