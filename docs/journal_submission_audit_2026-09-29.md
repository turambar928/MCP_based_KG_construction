# 投稿要求核查：2026-09-29

核查分“官方已确认”与“仍需确认”，不以经验页数或普通 IEEE 模板代替目标期刊规则。

## DMKD

依据：[官方 Submission Guidelines](https://link.springer.com/journal/10618/submission-guidelines)，本日 HTTP 200，页面哈希在 [来源记录](../exps/submission_week_20260929/journal_sources.json)。

|项目|官方内容|当前状态|
|---|---|---|
|摘要|150–250 words，不含未定义缩写或未指明文献|现有摘要约 190 words；随新增结果更新后再核定|
|关键词|4–6 个|现有 4 个，符合数量要求|
|源码|建议 Springer Nature LaTeX 模板；提交源文件、样式、图和编译 PDF|Paper1 使用 sn-jnl；最终源码包待科学内容冻结|
|题名页|作者、单位、城市／国家、通讯作者及有效邮箱|已有六位作者；城市、最终顺序和信息由作者核定|
|数据声明|所有原创研究必须含 Data Availability Statement|既有正文含复现入口；新增正式声明入口|
|其他声明|Funding / Competing interests / Authors' contributions 等按实际情况填写|不能替作者声称无基金、无利益冲突或已获全体批准|
|匿名要求|页面中的“if double-anonymous”是条件说明|未据此认定 DMKD 双盲；不自动匿名化当前作者信息|
|页数|本次未定位到明确的研究论文页数上限|现有长稿仍应精简，但不虚构硬性页数|

## TKDE

[期刊官网](https://www.computer.org/csdl/journal/tk)及若干站内 author 路径返回同一个 8,211-byte JavaScript 页面，未提供可读的完整投稿要求。Computer Society 作者说明及候选 PDF 路径返回 403。**尚未核实当前常规论文的页数上限、匿名要求、超页条款和专用模板选项。**

Paper2 当前为 `IEEEtran[journal]`，并使用 `fontspec` / Times New Roman，以 Tectonic 编译；这是 IEEE 通用双栏稿件设置，不足以证明已符合 TKDE 最终要求。本轮不凭猜测切换模板或压缩字号。现有字体回退也须在官方格式确认后处理。

## 内容冻结前的作者清单

1. 分别核定两篇论文的作者、顺序、单位、通讯作者与城市；不能把 Paper1 作者直接复制到 Paper2。
2. 提供真实基金、利益冲突和作者贡献声明。
3. 人工实验按最新要求后置；材料包中明确真实完成状态。
4. DocRED 来源文本暂不再分发：数据卡 MIT 标签与正文“More Information Needed”并存；提供下载入口、哈希及转换脚本。
5. 正式投稿前从期刊作者入口／投稿系统核定当前规则，再决定匿名版本与篇幅；不把当前编译 PDF 自动标为符合所有格式要求。
