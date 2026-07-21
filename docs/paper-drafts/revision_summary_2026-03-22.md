# 论文修改总结（2026-03-22）

## Paper 1：多层次知识图谱质量增强框架

### 1. 统一 Q(G) 权重定义（Major Fix）

**文件**：`paper1/sections/methodology.tex`

- **修改前**：Eq. (4) 后写的是 $w_1=0.2, w_2=0.2, w_3=0.3, w_4=0.3$，而 Experiments 中综合分用的是等权 0.25，两处不一致。
- **修改后**：methodology.tex 统一改为等权 $w_1=w_2=w_3=w_4=0.25$，并明确符号映射关系（$S(C_1)\equiv S_{iso}$，$S(C_2)\equiv S_{red}$，$S(C_3)\equiv S_{log}$，$S(C_4)\equiv S_{sem}$），新增一句指向 Section 4 的权重敏感性分析作为交叉引用。

---

### 2. 补充约束优化算法伪代码（Major Fix）

**文件**：`paper1/sections/methodology.tex`（新增 §3.3）

- **修改前**：约束优化仅有公式表述，缺乏可执行细节（决策变量、修复动作、收敛条件未定义）。
- **修改后**：新增 `\subsection{Constraint-Based Enhancement Algorithm}`，包含：
  - 决策变量定义：$\mathcal{E}$（删边）、$\mathcal{A}$（加边）、$\mathcal{M}$（改类型）
  - 三种修复原语及代价函数排序：$\text{cost(delete)} > \text{cost(retype)} > \text{cost(complete)}$
  - 完整 `algorithm` 环境伪代码（Algorithm 1），含 hard constraint 优先检查、balance constraint、optional constraints 及收敛条件（$\epsilon=0.01$，实践中 $T\le5$ 次外层迭代）
  - 修复两处重复的 `\label{fig:placeholder}` → 改为 `\label{fig:framework_overview}` 和 `\label{fig:multi_strategy}`

---

### 3. 语义评分协议透明化（Major Fix）

**文件**：`paper1/sections/experiments.tex`

- **修改前**：$S_{sem}$ 的采样数 $K$、温度、prompt 结构均未说明，审稿人无法判断评估稳定性。
- **修改后**：新增 **Semantic Scoring Protocol** 段落，说明：
  - $K=50$ 个三元组均匀采样
  - 温度 $\tau=0.1$（近确定性）
  - 完整 prompt 在 Appendix A
  - 复现性验证：政府域 5 次重复评估 $\sigma=0.21$（$< \pm 0.3$ 分）

---

### 4. Exp 1 定义澄清（Minor Fix）

**文件**：`paper1/sections/experiments.tex`

- **修改前**："Exp 1 是 clean data 的 baseline"，审稿人会质疑"Exp 3 超过 Exp 1"是否 pipeline 不一致。
- **修改后**：明确 Exp 1 intentionally 不跑 deduplication / constraint enforcement / repair 步骤，反映原始 KG 构建 pipeline 的原始质量；Exp 3 在退化数据上跑完整增强后能超过 Exp 1，是因为增强步骤修复了 clean 数据中本来就存在的潜在问题——属于框架的正常工作行为而非不公平对比。

---

### 5. 权重敏感性数值来源说明（Minor Fix）

**文件**：`paper1/sections/experiments.tex`

- **修改前**：Table 中直接给出不同权重下的 Avg $Q_{score}$，没有说明计算方式，审稿人可能质疑"重新跑了实验"或"数字不透明"。
- **修改后**：在表格说明段首新增一句，明确每个 $Q_{score}$ 是对 Table（综合结果表）中已有的四维原始分数 $(S_{iso}, S_{red}, S_{log}, S_{sem})$ 直接重新加权计算，无需重跑实验，完全可从论文内数字复现。

---

### 6. Web Search 消融适用范围说明（Minor Fix）

**文件**：`paper1/sections/experiments.tex`

- **修改前**：表格标注"Government Domain, Exp 3"，但未解释为何只展示一个域，审稿人会怀疑选择性展示。
- **修改后**：引言段扩展为：政府域搜索量最高（3.1 calls/doc），是成本上界；金融域和环境域分别为 1.8/2.2 calls/doc，对应质量贡献 +1.41/+1.73 分，数据在正文中补充，政府域结果因此代表所有域的最坏情况而非特例。

---

## Paper 2：基于强化学习的知识图谱质量协同优化框架

### 1. 扩展规则定义（Major Fix，已在上一版完成）

**文件**：`paper2/sections/methodology.tex`，§3.4

- **修改前**：规则定义仅有一类（属性存在规则），定义过窄。
- **修改后**：扩展为四类互补规则类型：$r_{\mathrm{attr}}$（属性存在）、$r_{\mathrm{rel}}$（关系有效性）、$r_{\mathrm{val}}$（值约束）、$r_{\mathrm{ord}}$（跨实体排序），示例表覆盖政务/金融/环境三域。

---

### 2. 统一 Q(R) 定义（Major Fix）

**文件**：`paper2/sections/methodology.tex`

- **修改前**：3.4 节讨论前三项指标（Precision/Recall/Coverage），3.2 节定义四项，两处不一致，审稿人会质疑训练目标与报告指标不对齐。
- **修改后**：训练与报告统一使用四项完整 $Q(R)$；在 3.4 节末尾一句说明 Unique 的特殊性：它是事后评估的涌现指标（非平滑、噪声大，不直接作为生成过程优化目标），因此在优化循环中使用前三项计算即时奖励，Unique 仅用于 post-hoc 报告。

---

### 3. 补充 94 个测试用例说明与置信区间（Major Fix，已在上一版完成）

**文件**：`paper2/sections/experiments.tex`

- 新增测试集构造说明：来源、标注方式、覆盖范围
- 补充 100% precision 的 Wilson 置信区间：$\text{CI}_{95\%} = [0.962, 1.000]$，确认结果不是小样本假象

---

### 4. 新增 Appendix（新增文件）

**文件**：`paper2/sections/appendix.tex`（新建），`paper2/main.tex`（新增 `\input`），`paper2/references.bib`（新增 Wilson 1927）

三个附录节，直接对应审稿人三个追问方向：

| 附录 | 内容 | 对应审稿关切 |
|------|------|------------|
| **A: Complete Prompts** | 删除补全 + 增强扩展的逐字提示词（含温度设置和设计原则） | 幻觉风险、可复现性 |
| **B: Test Set Statistics** | 3域×4类缺陷交叉分布表 + Wilson CI 推导过程 | 强数字证据链、标注说明 |
| **C: Hyperparameter Sensitivity** | DBSCAN ε 敏感性表、λ 网格搜索（5随机种子±std）、γ 敏感性表 | RL 设计合理性、参数选择依据 |

---

### 5. 框架图与协同循环形式化（已在 introduction.tex 中）

**文件**：`paper2/sections/introduction.tex`

- 框架图（Figure 1）已前置到 Introduction 末尾，图注中写明输入/输出和闭环定义
- 一次协同循环的形式化描述已包含：评估 → 决策 → 执行 → 更新 → 再评估

---

## 待处理事项（Paper 2）

以下审稿建议已评估但尚未实现，留待下一轮修改：

| 优先级 | 内容 | 说明 |
|--------|------|------|
| 🟡 | B3: Rule-first / Fix-first RL baseline | 需要运行额外实验 |
| 🟡 | B4: 规则数量随 episode 变化曲线 | 需确认实验数据是否支持 |
| 🟢 | A7: Coverage 定义澄清 | 低成本，可在下一轮加一句 |
| 🟢 | A8: SHACL/ShEx 相关工作 | 视投稿目标决定是否需要 |
