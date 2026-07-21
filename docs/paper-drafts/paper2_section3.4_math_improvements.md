# Paper 2 Section 3.4 数学公式改进说明

## 修改概述

对 Paper 2 的 **Section 3.4 (LLM-Based Dual-Strategy Rule Generation)** 进行了全面的数学公式重组，使其更加严谨、清晰和易读。

---

## 修改 1: Strategy 1 的信息论解释（Deletion Completion）

### ❌ 修改前（问题）

```latex
\textbf{Information-theoretic Interpretation:} Maximize Pointwise Mutual Information (PMI) between rule $r$ and context $C$:
\begin{equation}
\text{PMI}(r; C) = \log \frac{P(r, C)}{P(r)P(C)}
\end{equation}
If the LLM infers rule $r$ under masked context $C_{\text{masked}}$, it indicates high PMI—a signal of strongly constrained rules. The masking probability is set to $p_{\text{mask}} = 0.15$ following BERT's masking strategy.
```

**问题**：
1. ❌ 缺少符号定义（r 和 C 是什么）
2. ❌ 没有量化"high PMI"的具体含义
3. ❌ 缺少置信度计算的数学公式
4. ❌ 没有明确 N=10 和 θ_freq=0.7 的使用方式

---

### ✅ 修改后（改进）

```latex
\textbf{Information-theoretic Interpretation:} The deletion completion strategy discovers implicit constraints by maximizing Pointwise Mutual Information (PMI) between rules and context. Define:
\begin{equation}
\text{PMI}(r; C) = \log \frac{P(r, C)}{P(r) \cdot P(C)}
\end{equation}
where $r$ represents a candidate rule and $C$ denotes the context. High PMI indicates strong statistical dependence: if the LLM consistently infers rule $r$ from masked context $C_{\text{masked}}$, we have $\text{PMI}(r; C) \gg 0$, signaling a strongly constrained rule. Formally, given masking probability $p_{\text{mask}} = 0.15$ (following BERT's masking strategy), we estimate rule confidence as:
\begin{equation}
\text{Confidence}(r) = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}\{\text{LLM}(C_{\text{masked}}^{(i)}) \text{ infers } r\}
\end{equation}
where $N = 10$ is the number of masking iterations, and $\mathbb{I}\{\cdot\}$ is the indicator function. Rules with $\text{Confidence}(r) \geq \theta_{\text{freq}} = 0.7$ are extracted.
```

**改进点**：
1. ✅ 清晰定义了符号：r = candidate rule, C = context
2. ✅ 用数学符号 $\gg 0$ 量化"high PMI"
3. ✅ 添加了 **Confidence 公式**（新增方程）
4. ✅ 明确了 N=10 迭代次数和阈值 θ_freq=0.7
5. ✅ 引入指示函数 $\mathbb{I}\{\cdot\}$ 使表达更严谨

---

## 修改 2: Strategy 2 的信息论解释（Augmentation Expansion）

### ❌ 修改前（问题）

```latex
\textbf{Information-theoretic Interpretation:} LLM-driven data augmentation samples from neighborhoods centered at $T$, enabling robust estimation of posterior probability $P(R | P_{\text{data}})$. A single text $T$ is only one sample from true distribution $P_{\text{data}}$. By generating multiple augmented texts, we approximate:
\begin{equation}
P(R | P_{\text{data}}) \approx \frac{1}{n} \sum_{i=1}^{n} P(R | T_i^{\text{aug}})
\end{equation}
```

**问题**：
1. ❌ **符号混乱**：$P(R | P_{\text{data}})$ 不规范（条件概率的条件应该是随机变量，不是分布）
2. ❌ 缺少邻域采样的数学表示
3. ❌ 没有定义 Support 计算公式
4. ❌ 缺少生成参数的说明（τ, p）

---

### ✅ 修改后（改进）

```latex
\textbf{Information-theoretic Interpretation:} The augmentation expansion strategy provides robust rule estimation through distributional sampling. A single text $T$ represents only one realization from the true data distribution $\mathcal{D}$. LLM-driven augmentation samples from the neighborhood $\mathcal{N}(T)$ centered at $T$, enabling estimation of the posterior rule probability:
\begin{equation}
P(r \mid \mathcal{D}) \approx \mathbb{E}_{T' \sim \mathcal{N}(T)} [P(r \mid T')] \approx \frac{1}{n} \sum_{i=1}^{n} P(r \mid T_i^{\text{aug}})
\end{equation}
where $T_i^{\text{aug}} \sim \text{LLM}(T; \tau=0.8, p=0.9)$ are augmented samples generated with temperature $\tau$ and nucleus sampling parameter $p$. The rule support is computed as:
\begin{equation}
\text{Support}(r) = \frac{|\{i : r \in \text{Rules}(G_i)\}|}{n}
\end{equation}
where $G_i = \text{ExtractKG}(T_i^{\text{aug}})$ is the knowledge graph extracted from the $i$-th augmented text. Rules with $\text{Support}(r) \geq \theta_{\text{support}} = 0.6$ are retained, ensuring robustness across diverse variations.
```

**改进点**：
1. ✅ **修正符号**：$P(R | P_{\text{data}})$ → $P(r \mid \mathcal{D})$（规范的条件概率表示）
2. ✅ 引入邻域符号 $\mathcal{N}(T)$ 和期望符号 $\mathbb{E}_{T' \sim \mathcal{N}(T)}$
3. ✅ **添加 Support 公式**（新增方程）
4. ✅ 明确生成过程：$T_i^{\text{aug}} \sim \text{LLM}(T; \tau=0.8, p=0.9)$
5. ✅ 将单个规则 r 和规则集 R 区分清楚

---

## 修改 3: 去重算法的数学表达（Rule Aggregation and Deduplication）

### ❌ 修改前（问题）

```latex
\subsubsection{Rule Aggregation and Deduplication}

The final rule set combines both strategies with deduplication:
\begin{equation}
R^* = \text{Deduplicate}(R_{\text{deletion}} \cup R_{\text{augmentation}})
\end{equation}

\textbf{Deduplication Algorithm:}
\begin{enumerate}
    \item \textit{Semantic Clustering}: Embed rules using sentence transformers and cluster with DBSCAN ($\epsilon = 0.3$)
    \item \textit{Subsumption Check}: Within each cluster, identify subsumption relationships (e.g., "government agencies issue penalties" subsumes "environmental bureaus issue penalties")
    \item \textit{Generalization}: Keep most general rule in each cluster while preserving specific rules that add unique constraints
\end{enumerate}
```

**问题**：
1. ❌ 只有文字描述，缺少数学公式
2. ❌ 没有距离度量的定义
3. ❌ 没有包含关系的数学符号
4. ❌ 最终规则选择没有数学表达

---

### ✅ 修改后（改进）

```latex
\subsubsection{Rule Aggregation and Deduplication}

The final rule set combines both strategies with deduplication to remove redundant rules while preserving coverage:
\begin{equation}
R^* = \text{Deduplicate}(R_{\text{deletion}} \cup R_{\text{augmentation}})
\end{equation}

\textbf{Deduplication Algorithm:}

\textbf{Step 1 - Semantic Clustering:} Embed each rule as $\mathbf{e}_r = f_{\text{embed}}(\text{rule\_text})$ using sentence transformers, where $\mathbf{e}_r \in \mathbb{R}^d$ ($d=768$). Apply DBSCAN clustering with:
\begin{equation}
\text{dist}(r_i, r_j) = 1 - \cos(\mathbf{e}_{r_i}, \mathbf{e}_{r_j}) = 1 - \frac{\mathbf{e}_{r_i} \cdot \mathbf{e}_{r_j}}{\|\mathbf{e}_{r_i}\| \|\mathbf{e}_{r_j}\|}
\end{equation}
with radius $\epsilon = 0.3$ and $\text{minPts} = 2$.

\textbf{Step 2 - Subsumption Check:} Within each cluster $\mathcal{C}_k$, identify subsumption relationships. Rule $r_i$ subsumes $r_j$ (denoted $r_i \sqsupseteq r_j$) if:
\begin{equation}
\text{Entities}(r_j) \subset \text{Entities}(r_i) \land \text{Semantics}(r_i) \implies \text{Semantics}(r_j)
\end{equation}
For example, "government agencies issue penalties" $\sqsupseteq$ "environmental bureaus issue penalties" (since environmental bureaus $\subset$ government agencies).

\textbf{Step 3 - Rule Selection:} For each cluster $\mathcal{C}_k$, construct the subsumption partial order and retain:
\begin{equation}
R_k^* = \{r \in \mathcal{C}_k : \nexists r' \in \mathcal{C}_k, r' \sqsupseteq r \land r' \neq r\}
\end{equation}
This keeps maximally general rules while preserving specific rules that add unique constraints not covered by generalizations.

The final deduplicated rule set is $R^* = \bigcup_{k=1}^{K} R_k^*$ where $K$ is the number of clusters.
```

**改进点**：
1. ✅ **添加距离度量公式**（新增方程）：明确余弦距离的计算
2. ✅ 引入 embedding 向量 $\mathbf{e}_r \in \mathbb{R}^{768}$
3. ✅ **添加包含关系公式**（新增方程）：使用集合论符号 $\subset$ 和逻辑符号 $\land, \implies$
4. ✅ 引入包含关系符号 $\sqsupseteq$（标准的偏序符号）
5. ✅ **添加规则选择公式**（新增方程）：使用集合构造符 $\{r : \ldots\}$ 和存在量词 $\nexists$
6. ✅ 添加最终聚合公式：$R^* = \bigcup_{k=1}^{K} R_k^*$

---

## 总体改进统计

### 新增数学公式

| 位置 | 新增公式 | 作用 |
|-----|---------|------|
| Strategy 1 | $\text{Confidence}(r) = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}\{\ldots\}$ | 量化规则置信度 |
| Strategy 2 | $P(r \mid \mathcal{D}) \approx \mathbb{E}_{T' \sim \mathcal{N}(T)} [P(r \mid T')]$ | 规范后验概率表示 |
| Strategy 2 | $\text{Support}(r) = \frac{\|\{i : r \in \text{Rules}(G_i)\}\|}{n}$ | 定义支持度计算 |
| Dedup | $\text{dist}(r_i, r_j) = 1 - \cos(\mathbf{e}_{r_i}, \mathbf{e}_{r_j})$ | 定义距离度量 |
| Dedup | $\text{Entities}(r_j) \subset \text{Entities}(r_i) \land \ldots$ | 定义包含关系 |
| Dedup | $R_k^* = \{r \in \mathcal{C}_k : \nexists r' \ldots\}$ | 定义规则选择 |

**共新增 6 个数学公式**

---

### 符号规范化

| 修改前 | 修改后 | 说明 |
|-------|--------|------|
| $P(R \| P_{\text{data}})$ | $P(r \mid \mathcal{D})$ | 条件概率规范化 |
| "high PMI" | $\text{PMI}(r; C) \gg 0$ | 用数学符号量化 |
| 文字描述"subsumes" | $r_i \sqsupseteq r_j$ | 引入偏序符号 |
| $\frac{P(r,C)}{P(r)P(C)}$ | $\frac{P(r,C)}{P(r) \cdot P(C)}$ | 使用显式乘号 |
| "R" (规则集) | "r" (单个规则) | 区分集合和元素 |

---

### 数学严谨性提升

1. ✅ **符号定义清晰**：所有符号在首次使用时定义
2. ✅ **公式完整性**：从文字描述转为完整数学公式
3. ✅ **逻辑连贯性**：公式之间有明确的推导关系
4. ✅ **表示规范性**：使用标准数学符号（$\mathbb{E}$, $\mathcal{N}$, $\sqsupseteq$, $\nexists$）
5. ✅ **可计算性**：所有公式都可直接实现为代码

---

## 修改文件

**文件路径**: `/home/taozifu2025/MCP_based_KG_construction/paper_part2.tex`

**修改行数**: 528-612 (约85行)

**影响范围**:
- Section 3.4.1: Strategy 1 - Deletion Completion Strategy
- Section 3.4.2: Strategy 2 - Augmentation Expansion Strategy
- Section 3.4.3: Rule Aggregation and Deduplication

---

## 修改前后对比示例

### Example 1: Confidence 计算

**修改前**：只有文字描述
> "Rules with Frequency ≥ 0.7 are extracted"

**修改后**：完整数学公式
```math
Confidence(r) = (1/N) Σ_{i=1}^N 𝕀{LLM(C_masked^(i)) infers r}
Rules with Confidence(r) ≥ 0.7 are extracted
```

---

### Example 2: 包含关系

**修改前**：文字描述
> "government agencies issue penalties" subsumes "environmental bureaus issue penalties"

**修改后**：数学公式 + 文字解释
```math
r_i ⊒ r_j  if  Entities(r_j) ⊂ Entities(r_i) ∧ Semantics(r_i) ⟹ Semantics(r_j)

例如："government agencies issue penalties" ⊒ "environmental bureaus issue penalties"
（因为 environmental bureaus ⊂ government agencies）
```

---

## 验证检查清单

- ✅ 所有新增公式都有明确的符号定义
- ✅ 公式编号连续，没有跳号
- ✅ LaTeX 编译无错误
- ✅ 数学符号使用一致（例如：都用 $\mid$ 而不是 $|$ 表示条件概率）
- ✅ 移除了不必要的引用（ref_devlin2019）
- ✅ 保持了原有的算法伪代码不变
- ✅ 保持了文字解释和例子不变

---

## 总结

通过这次修改，Section 3.4 的数学表达从**文字描述为主**提升到**严谨的数学公式体系**，使得：

1. **可读性提升**：读者可以直接通过数学公式理解算法逻辑
2. **可复现性提升**：每个公式都可直接转换为代码实现
3. **学术规范性提升**：符合顶级会议的数学表达标准
4. **逻辑完整性提升**：公式之间有明确的推导链

这些改进使 Paper 2 的理论基础更加坚实，便于审稿人理解创新点的数学原理。
