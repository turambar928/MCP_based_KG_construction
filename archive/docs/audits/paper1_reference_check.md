# Paper 1 参考文献与引用核查

检查日期：2026-09-17。范围：`paper1/main.tex` 实际引入的七个 section，以及 `paper1/references.bib` 全部 45 条记录。不把未启用的 `sections/methodology.tex`、旧 ACL 草稿或 Paper 2 混入统计。

本报告替代旧版“完全匹配”报告。引用键能对应，只能证明 LaTeX 引用完整，不能证明文献真实、作者正确，或正文论述得到文献支持。

## 结论与已修正的问题

发现并修正了作者错误、作者遗漏、文献元数据混配、正式发表信息未更新、模型版本引用错误，以及多处引用与论述不匹配。

| 条目 | 检查前的问题 | 修正及依据 |
|---|---|---|
| `ref_lin2025` | 将作者写成 Lin、Bosselut、Chen | 原论文实际为 Tung-Wei Lin、Gabe Fierro、Han Li、Tianzhen Hong、Pierluigi Nuzzo、Alberto Sangiovanni-Vinentelli，已完整替换。[arXiv 原记录](https://arxiv.org/abs/2507.22419) |
| `ref_bian2025` | 作者写成 Ning Bian | 实际为 **Haonan Bian**。[arXiv](https://arxiv.org/abs/2510.20345) |
| `ref_wienand2014` | 第一作者名写成 Dominique | 实际为 **Dominik Wienand**。[出版社 DOI](https://doi.org/10.1007/978-3-319-07443-6_34) |
| `ref_wei2023` | CoT 论文遗漏 Brian Ichter、Fei Xia 两位作者 | 补全 9 位作者、卷 35、页 24824–24837、DOI。当前条目在检查前就已是 **2022 年**，不是再次修改年份。[NeurIPS](https://papers.nips.cc/paper_files/paper/2022/hash/9d5609613524ecf4f15af0f7b31abca4-Abstract-Conference.html) |
| `ref_pan2023` | 仅列前 3 位作者，也未用 `and others` 表示截断 | 补全原记录的 16 位作者。[arXiv](https://arxiv.org/abs/2308.06374) |
| `ref_wang2021` | “Knowledge Graph Quality Assessment: A Survey” + Shuangyin Wang 等 + IEEE Access 的组合未获核实 | **替换文献**为已核实的 Xiangyu Wang 等，*Knowledge graph quality control: A survey*，Fundamental Research **1**(5), 607–626 (2021)。这不是仅改大小写，也不宣称找到了原组合的同一篇论文。[DOI](https://doi.org/10.1016/j.fmre.2021.09.003) |
| `ref_ji2021` | 仅有 2021 在线发表年份，无卷期页 | 采用最终刊期：IEEE TNNLS **33**(2), 494–514 (**2022**)。DOI 内的 2021 是正常的，不需要改 DOI 年份。[DOI](https://doi.org/10.1109/TNNLS.2021.3070843) |
| `ref_pan2025` | Roadmap 仍引用 2023 arXiv 版本 | 更新为 IEEE TKDE **36**(7), 3580–3599 (**2024**) 正式版本。[DOI](https://doi.org/10.1109/TKDE.2024.3352100) |
| `ref_anthropic_claude45` | 标题写 “System Card”，链接实际是 Haiku 产品页 | 改为有日期且题名对应的官方发布文 *Introducing Claude Haiku 4.5*，2025-10-15。[Anthropic](https://www.anthropic.com/news/claude-haiku-4-5) |
| 原 `ref_gemma3`，现 `ref_gemma4` | 实验使用 Gemma 4，但链接是早期 Gemma 模型卡；该旧卡自带 2024 年引用 | 改为 *Gemma 4 Technical Report* (2026), arXiv:2607.02770；同时通过 Gemma 4 官方模型卡和 checkpoint 卡确认 26B A4B instruction-tuned 版本。[报告](https://arxiv.org/abs/2607.02770) / [模型卡](https://ai.google.dev/gemma/docs/core/model_card_4) / [checkpoint](https://huggingface.co/google/gemma-4-26B-A4B-it) |
| `ref_chen2019` | MetaR 的会议名称缺少联合举办的 IJCNLP，缺页码 | 按 ACL Anthology 补为 EMNLP-IJCNLP 2019，**4217–4226**，DOI 10.18653/v1/D19-1431。Crossref 返回 4216–4225，与官方 Anthology 不同，以后者为准。[ACL](https://aclanthology.org/D19-1431/) |
| `ref_white2023` | Prompt Pattern Catalog 仍引用 arXiv | 更新为 PLoP 2023 正式会议版本，DOI 10.64346/PLoP2023p05。官方建议引用年份为 2023，Crossref 在线上线日期为 2024-06-24，采用官方会议引用。[论文集](https://www.plopcon.org/proceedings/plop/2023/05.html) |

同时补充可核实的 DOI、卷期和页码，统一 DBpedia、YAGO、RNNLogic、ProjE、NLP、SHACL、RDF、Gemma 等专名的 BibTeX 大小写保护；修正 `van den Berg` 的姓氏词缀写法；补全 RAG 原论文作者。

`ref_ji2021`、`ref_wei2023`、`ref_pan2025` 等旧引用键暂时保留以兼容已有源文件。键名不参与排版，判断年份应看 `year` 和最终参考文献，而不是键名末尾数字。

## DMKD 引用格式

[DMKD 官方投稿指南](https://link.springer.com/journal/10618/submission-guidelines)明确要求 “Cite references in the text by name and year in parentheses”，且参考文献按作者姓氏排序。原稿使用 `sn-nature` 数字制，不符合该要求。

已改用 `sn-basic`，正文括号引用改为 `\citep`。所需 `sn-basic.bst` 原样取自[Springer Nature 官方模板包](https://cms-resources.apps.public.k8s.springernature.io/springer-cms/rest/v1/content/18782940/data/v12)，下载来源和 SHA-256 记录在证据文件中。

预印本改用 `@misc`、`eprint`、`archivePrefix` 等字段，避免该样式在清理 `journal` 字段标点时将 `2308.06374` 错排成 `230806374`。这是通过检查实际编译 PDF 发现并修复的问题，不只是 `.bib` 文本检查。

## 正文引用的实质性修正

1. **Lin 2025 不支持“LLM 修复忽略逻辑约束”的概括。** 阅读其原文后确认：该文恰恰研究 SHACL 约束违反、violation-inducing operations 和约束感知提示，发现相关约束与图上下文有帮助。引言、Related Work 已据此改写，承认其约束感知修复贡献，保留与本文的具体差异。[原文](https://arxiv.org/html/2507.22419v1)
2. **CoT、RAG 不能证明“现有 KG 系统普遍盲目堆叠工具”。** 已改为分别介绍推理提示、检索增强和 ReAct 的实际作用，将本文缺陷驱动路由表述为研究问题。
3. **NBFNet 不是显式规则挖掘或修复评测系统。** 已改为其广义 Bellman–Ford 路径表示与链接预测机制。
4. **MINERVA 不能直接当作错误修复实验证据。** 已明确它学习图导航策略完成查询回答；MetaR 对应 few-shot link prediction。
5. **通用 Prompt Pattern Catalog、RAG 不是 Text-to-KG 效果的直接证据。** 已区分通用方法、KG 综述与实际 Text-to-KG 应用。
6. **“现有方法没有约束”的说法不准确。** 补回已经在 `.bib` 中但原来未被引用的 AMIE、RuDiK、Guo 2016、Ding 2018，并分别对齐正/负规则发现与约束嵌入学习；缩小引言中的全称否定。
7. **“本文依赖 LLM 动态挖掘约束”的 Related Work 表述缺少实现支撑。** 已改为当前正文明确的领域规则与 trial-graph 检查，不用综述文献替本文证明不存在的功能。

未重跑实验，未改实验数值、模型标识或数据划分；实验段落仅更新引用格式和 Gemma 引用键。

## 核查方法和证据边界

- 以 NeurIPS 官方论文集、ACL Anthology、arXiv 作者/版本记录、W3C 标准、厂商官方发布与模型卡、出版社向 Crossref 登记的元数据为依据。
- **不直接采用标题搜索第一条结果。** 对 DOI 候选同时核对标题与作者；不匹配结果排除。ACM 在 Crossref 中可能将副标题单列，不能据短标题推断原论文不存在。
- Crossref 的 `published` 字段可能是在线首发时间。Zaveri 的 Semantic Web 7(1) 采用 2016 刊期，Paulheim 的 8(3) 采用 2017 刊期；没有机械替换成较早的 online-first 年份。
- 部分 OpenReview、DBLP 页面返回浏览器验证或限流；AAAI 页面访问失败。这些条目使用可取得的 arXiv 论文记录或出版社登记 DOI 核对，没有把 HTTP 200 验证页当作文献内容。
- NeurIPS 2013 TransE 和 2019 pLogicNet 的官方 BibTeX 页码为空；AAAI 部分 DOI 记录不返回页码。保持已验证的会议/卷/年份/DOI 或官方 URL，**不猜页码**。
- Lin 2025 保留经核实的 arXiv 版本；本次没有确认到正式出版记录。这不等于断言它从未正式发表。
- Bian 2025、Pan 的 2023 position paper、Lin 2025 目前仍明确标为预印本；Gemma 4 为公开技术报告。指南还要求文献为已发表或已接受作品，不能将这些条目描述成已确认经过同行评审的正式期刊论文。已核实的正式版本（Pan Roadmap、White Prompt Catalog）均已优先采用，其余发表状态作为投稿前待确认事项保留。
- 旧 Qwen 技术报告 (`ref_qwen2025`，实际 2023 年) 仍保存在 `.bib`，但没有被当前论文引用，不进入最终参考文献。它不能作为 Qwen3.8 型号的依据，未将它强行加到实验中。

逐条原始字段、修正字段及来源保存在 [`paper1_reference_sources.json`](paper1_reference_sources.json)。该文件覆盖全部 45 条，包括未引用的旧 Qwen 条目，便于作者逐项复核。

## 验证结果

- 修改前：45 条 BibTeX，正文引用 40 个独立键，无缺失键；5 条未使用。
- 修改后：45 条 BibTeX，正文引用 44 个独立键，无缺失键、无重复键、无重复 DOI；仅旧 Qwen 条目未使用。
- Tectonic 编译成功，最终 PDF 为 30 页；实际 `.bbl` 恰有 44 条，与正文引用集合完全相等。BibTeX 警告为 0，无未定义引用或 `??`；四个实际引用的预印本/技术报告编号在 PDF 中均保留小数点。
- 已查看正文作者—年份引用和参考文献页面的渲染结果。模板仍有 underfull-box、旧 `algorithm.sty` 编码提示及重复 PDF destination 警告；未将这些无关警告表述成“零警告编译”。
