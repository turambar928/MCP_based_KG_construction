# Paper 1 近期修改汇总（DMKD 投稿准备）

更新时间：2026-09-17

覆盖范围：2026-09-16 至 2026-09-17 的 Paper 1 集中修订（提交 `012319f` 至 `af7e121`）

目标期刊：*Data Mining and Knowledge Discovery*（DMKD）

## 1. 当前状态

Paper 1 已收窄为**文档级知识图谱的画像条件约束修复**，当前标题为：

> **Profile-Conditioned Constraint-Guided Repair of Document-Level Knowledge Graphs**

Local、graph 和 source 表示同一文档图内部的三种证据范围。论文不再把跨文档对齐、因果推理或大型互联 KG 的通用修复能力作为核心主张。

当前证据链包括：受控配对修复、真实 Text-to-KG 抽取错误、强 Simple Pipeline、候选级 constraint-gate 审计、router 真实混合流执行、leave-one-domain-out、Claude/Gemma 跨模型对照和 1K--50K triples 的 profile scaling。轻量神经 router 没有优于透明的 heuristic/threshold policy，因此已从核心贡献降为可选实现组件；论文不再把它包装成主要性能来源。

当前论文 PDF 可正常编译，共 25 页，无未解析引用、未定义文献或 overfull box。自然错误实验使用结构化字段作为 silver reference；冻结的 200 条差异样本仍须由两名真实标注者独立标注，不能以模型判断替代人工一致性。

## 2. 导师修改意见的落实方式

导师提出的写作路径是“规则 → 三尺度约束 → profile → 轻量神经网络”，本轮按以下方式落实。

| 导师意见 | 当前论文中的处理 |
| --- | --- |
| 最初工作容易被视为 prompt engineering | LLM 和 prompt 被限制为候选动作来源之一，不再直接定义系统状态或决定是否接受修改 |
| 将零散规则提升为三个尺度的约束条件 | 用 Entity、Graph、Context 三个依赖尺度组织局部结构、全局逻辑和来源语义缺陷 |
| 将问题写成约束优化问题 | 定义图状态、候选动作、图转移、质量效用、恢复边界和有限时域目标 |
| 用 profile 连接分析和修改模块 | 使用 `[q_conn, q_uniq, q_logic, q_sem]` 四维画像作为诊断、路由、trial-state 比较和停止判断的共同接口 |
| 用轻量神经网络提升方法完整性 | 保留 `f_phi` 作为画像驱动的可选路由实现，但真实端到端实验显示其与 heuristic/threshold policy 完全相同，因此不再把它列为 headline contribution |
| 防止神经或 LLM 模块产生不受控修改 | 所有候选先在临时图上完整重评估，只有满足约束且效用为正的最高分动作才能提交 |

最终形成的技术链条是：

```text
文档内三类证据 → 四维质量画像 → 候选图转移 → 约束门控 → 重新评估；神经路由为可替换实现
```

## 3. 方法与数学建模修改

### 3.1 图、画像和状态

论文统一使用知识图谱定义：

```math
G=(V,\mathcal{R},E).
```

四个归一化质量维度构成运行时画像：

```math
\mathbf q(G)=
[q_{\mathrm{conn}},q_{\mathrm{uniq}},q_{\mathrm{logic}},q_{\mathrm{sem}}]^\top.
```

神经路由状态由质量画像和图统计量拼接：

```math
\mathbf x_t=[\mathbf s_t;\mathbf g_t].
```

其中图统计量包括节点数、边数、投影密度和违反约束的三元组数。

### 3.2 动作、转移和序列目标

每个候选修复被写为类型化图变换，状态转移为：

```math
G_{t+1}=T(G_t,a_t).
```

论文给出有限时域序列目标：

```math
\max_{a_0,\ldots,a_{T-1}}
\sum_t\gamma^t U(a_t\mid G_t)+\gamma^T\mathcal Q(G_T).
```

实现不声称求得全局最优序列。每轮对当前有限候选集逐一构造 trial graph，选择效用最高的可行动作，提交后重新计算画像、违反集合和神经先验。这一过程准确描述为 **receding-horizon constrained policy**。

### 3.3 恢复型约束

旧的严格下界会导致初始图一旦低于阈值，所有候选动作都不可行。当前改为恢复型边界：

- 已经合格的质量维度不得超过允许幅度退化；
- 尚未达标的维度至少不得继续恶化；
- 硬约束违反、密度和破坏性删除另行检查。

因此系统能够从初始不可行状态逐步恢复，同时保持对副作用的控制。

### 3.4 效用函数和停止条件

运行时效用与论文公式现已统一，包含：

- 四维画像的加权增益；
- 硬约束违反数量的实际减少；
- 修改风险或干预成本；
- 神经网络给出的尺度先验；
- 候选提供器的置信度。

循环在以下任一条件满足时终止：神经 trigger 低于阈值且不存在硬违反、违反已清空、没有正效用可行动作，或达到有限 horizon。有限 horizon 保证终止，但论文不声称标量画像单调增加或获得全局最优解。

### 3.5 为什么当前不写成强化学习

当前 `f_phi` 使用 BCE 与 masked cross-entropy，在 clean/corrupted 配对样本上进行监督训练。仓库中没有 Paper 1 对应的 transition trajectory、replay buffer、Bellman target、TD loss 或 policy-gradient 更新。

因此，本轮没有恢复旧 DQN/RL 名称。论文保留了状态、动作、转移、效用和有限时域语义，但将可验证的学习部分准确写成“监督训练的轻量神经策略先验”。旧的图谱质量与规则质量协同 RL 更适合 Paper 2 的规则—图谱共同优化范围。这样可以避免审稿人根据代码和实验指出“方法名称与训练机制不符”。

### 3.6 数学符号总表

| 符号 | 含义 | 当前实现中的对应项 |
| --- | --- | --- |
| $G=(V,\mathcal R,E)$ | 有向有标签多重知识图谱 | entities 与 triples；重复三元组保留 multiplicity |
| $X$ | 与文档图关联的原始文本证据 | `original_text` |
| $m=|E|$ | 当前三元组 occurrence 数 | `n_e` |
| $\mathbf q(G)$ | 四维归一化质量画像 | `[S_iso,S_red,S_log,S_sem]/100` |
| $\mathcal Q(G)$ | 四维画像的加权标量 | `q_score/100` |
| $\mathbf x_t$ | 八维路由状态 | 四个质量分数加节点数、边数、密度、违反数 |
| $\mathcal V_t$ | 第 $t$ 轮检测到的违反集合 | `QualityProfile.violations` |
| $f_\phi$ | 轻量神经路由器 | `FphiRouter` 与 `fphi_model.npz` |
| $p_t$ | 当前图需要修复的概率 | `p_repair` |
| $\boldsymbol\pi_t$ | Entity/Graph/Context 三尺度先验 | `RouterOutput.pi` |
| $\mathcal A(G_t)$ | 当前有限候选动作集合 | recommendations 与 violations 转换后的去重候选 |
| $T(G_t,a)$ | 在临时副本上执行动作 $a$ | `_apply_candidate` |
| $\mathcal A_{\mathrm{feas}}(G_t)$ | 通过恢复、密度和删除保护的候选 | `_check_constraints` |
| $U(a\mid G_t)$ | 候选动作效用 | `_utility` |
| $h(G)$ | hard violations 数量 | `hard=True` 的违反计数 |
| $T$ | 最大决策轮数 | `max_iterations=12` |

需要注意两个计量尺度。论文优化公式使用 $q_i\in[0,1]$；运行时代码为了与实验表格一致，保存 $S_i=100q_i\in[0,100]$，计算效用时再把 `after.q_score-before.q_score` 除以 100。因此公式和代码数值尺度是一致的。

### 3.7 算法一：多尺度质量画像计算

该算法把图 $G$ 和来源文本 $X$ 映射为固定维度画像、辅助图统计量和违反集合：

```text
输入：实体 V、三元组多重集 E、来源文本 X
1. 清洗三元组并建立节点集合；
2. 计算简单有向投影密度与非孤立节点比例；
3. 两两计算三元组相似度，建立相似图并求冗余率；
4. 检查空字段、自环、非法关系、层级反转和悬空端点；
5. 检查每个三元组尾实体是否得到 X 的字面支持；
6. 得到四个质量分数、违反集合和八维路由特征；
7. 返回 QualityProfile。
```

#### 3.7.1 Entity-scale：节点连接质量

将有向多关系图投影为无向图，记节点 $v$ 的无向度为 $\deg_U(v)$。孤立率和连接质量定义为：

```math
r_{\mathrm{iso}}(G)
=\frac{|\{v\in V:\deg_U(v)=0\}|}{|V|},
\qquad
q_{\mathrm{conn}}(G)=1-r_{\mathrm{iso}}(G).
```

空图单独定义为 $q_{\mathrm{conn}}=0$，避免“没有孤立点”被误解成满分。该指标实际度量的是**节点非孤立比例**，不等价于单连通分量比例，也不能证明任意节点间存在路径。论文当前使用 `connectivity` 是沿用质量维度名称，正文已经明确了这一物理含义。

计算只需遍历节点和边，时间复杂度为 $\mathcal O(|V|+m)$，空间复杂度为 $\mathcal O(|V|)$。

#### 3.7.2 Entity-scale：三元组唯一性

对三元组 $t_i=(s_i,r_i,o_i)$ 和 $t_j=(s_j,r_j,o_j)$，计算：

```math
\operatorname{sim}(t_i,t_j)
=\alpha\cos(\mathbf e_{s_i},\mathbf e_{s_j})
+\beta\cos(\mathbf e_{r_i},\mathbf e_{r_j})
+\gamma\cos(\mathbf e_{o_i},\mathbf e_{o_j}),
```

其中 $\alpha+\beta+\gamma=1$。当前轻量实现使用字符 bigram 向量，参数为 $(\alpha,\beta,\gamma)=(0.4,0.2,0.4)$，阈值 $\tau_{\mathrm{dup}}=0.92$。

将每个三元组 occurrence 视为相似图 $H_\tau$ 的一个节点。当相似度达到阈值时连边。设 $c(H_\tau)$ 是连通分量数，每个分量保留一个代表，则可删除数量为 $m-c(H_\tau)$：

```math
r_{\mathrm{red}}(G)=\frac{m-c(H_\tau)}{m},
\qquad
q_{\mathrm{uniq}}(G)=1-r_{\mathrm{red}}(G).
```

当 $m=0$ 时令 $r_{\mathrm{red}}=0$。因为非空图满足 $1\le c(H_\tau)\le m$，所以：

```math
0\le r_{\mathrm{red}}(G)\le\frac{m-1}{m}<1,
\qquad 0<q_{\mathrm{uniq}}(G)\le1.
```

这一写法比“相似 pair 数除以边数”严格，因为大量重复项会产生 $\binom{k}{2}$ 个 pair，旧定义可能超过 1；分量定义始终有界。

#### 3.7.3 Graph-scale：逻辑一致性

设 $\mathcal B_{\mathrm{log}}(G)$ 是至少违反一条适用逻辑规则的三元组集合，则：

```math
r_{\mathrm{log}}(G)=\frac{|\mathcal B_{\mathrm{log}}(G)|}{m},
\qquad
q_{\mathrm{logic}}(G)=1-r_{\mathrm{log}}(G).
```

一个三元组即使触发多条规则，也只在分子中出现一次，因此 $r_{\mathrm{log}}\in[0,1]$。当前在线 hard subset 检查空字段、自环、非法关系标记、行政层级反转和悬空端点。领域级离线评估还包含 government/finance/environment 的 25/29/34 条 type-compatibility 规则。两者范围不同：前者用于每个候选的低成本 commit gate，后者用于 corpus-level 报告。

若逐边检查 $|\mathcal C|$ 条约束，最坏时间复杂度为 $\mathcal O(m|\mathcal C|)$；当前若干在线规则是常数次字符串和集合判断，实际更接近 $\mathcal O(m)$。

#### 3.7.4 Context-scale：来源语义支持

论文区分离线评价量和在线代理量。离线评价从图中固定种子抽取 $K$ 个三元组，由独立 evaluator 给出 $z_k\in[0,1]$：

```math
\widehat q_{\mathrm{sem}}(G;X)=\frac1K\sum_{k=1}^{K}z_k.
```

在线搜索不能对每个 trial graph 都调用 LLM，因此使用确定性来源支持代理：

```math
u(t;X)=\mathbf1[o_t\notin X],
\qquad
q_{\mathrm{sem}}^{\mathrm{proxy}}(G;X)
=1-\frac{1}{\max(1,m)}\sum_{t\in E}u(t;X).
```

该代理检查 object/tail 是否在去空白后的原文中出现。它的优点是确定、便宜、适合 trial evaluation；局限是无法识别同义改写、代词指代或隐含事实。当没有来源文本时返回中性值 0.5，这只表示“缺少证据”，不能解释为 50% 的真实语义正确率。

#### 3.7.5 密度和标量画像

多重关系可能连接同一对节点，因此密度只在无自环简单有向投影上计算：

```math
E_{\mathrm{prj}}
=\{(u,v):u\ne v,\ \exists r\ (u,r,v)\in E\},
\qquad
\rho(G)=\frac{|E_{\mathrm{prj}}|}{|V|(|V|-1)}.
```

由 $|E_{\mathrm{prj}}|\le |V|(|V|-1)$ 可知 $\rho\in[0,1]$。四维画像的标量化为：

```math
\mathcal Q(G)=\mathbf w^\top\mathbf q(G),
\qquad
\mathbf w\ge0,\quad\sum_iw_i=1.
```

因此 $\mathcal Q(G)$ 是四个有界指标的凸组合，必有 $\mathcal Q(G)\in[0,1]$。默认权重均为 0.25；代码会对用户提供的非负权重自动归一化。标量 $\mathcal Q$ 用于排序，四个分量仍分别接受约束检查，所以某一维的严重退化不能单纯依靠其他维度的高分抵消。

### 3.8 算法二：基于相似分量的冗余检测

论文的 uniqueness 公式在实现中对应一个“全 pair 比较 + 并查集”的算法：

```text
输入：m 个清洗后的三元组、阈值 tau_dup
1. 对所有 i<j 计算 sim(t_i,t_j)；
2. 若两个三元组完全相同，令相似度为 1；
3. 若 sim>=tau_dup，记录 pair (i,j,sim)；
4. 初始化 m 个并查集分量；
5. 对每个相似 pair 执行 union(i,j)；
6. 统计最终根节点数 c；
7. 返回冗余率 (m-c)/m，并为候选生成保留相似 pair。
```

两两相似计算需要 $\mathcal O(m^2c_{\mathrm{sim}})$ 时间；并查集部分接近 $\mathcal O(m^2\alpha(m))$ 的上界，但通常被文本相似度计算支配。若保存全部相似 pair，最坏空间复杂度为 $\mathcal O(m^2)$。

这一算法把相似关系取传递闭包：若 $A\sim B$ 且 $B\sim C$，即使 $A$ 与 $C$ 未达到阈值，三者仍会进入同一分量。这使结果对“相似链”敏感。当前约束门和逐次删除能降低误删风险，但不能从数学上消除链式过合并；更严格的版本可改用 complete-link 聚类或要求候选与分量代表都超过阈值。

### 3.9 算法三：质量画像驱动的神经路由

#### 3.9.1 输入标准化与前向传播

路由输入为：

```math
\mathbf x=
[Q_{\mathrm{conn}},Q_{\mathrm{uniq}},Q_{\mathrm{logic}},Q_{\mathrm{sem}},
|V|,|E|,\rho,n_{\mathrm{viol}}].
```

只使用训练集均值 $\boldsymbol\mu$ 和标准差 $\boldsymbol\sigma$ 标准化：

```math
\widetilde{\mathbf x}
=(\mathbf x-\boldsymbol\mu)\oslash(\boldsymbol\sigma+\varepsilon).
```

网络前向计算为：

```math
\mathbf h_1=\operatorname{ReLU}(\widetilde{\mathbf x}W_1+b_1),
\qquad
\mathbf h_2=\operatorname{ReLU}(\mathbf h_1W_2+b_2),
```

```math
p_{\mathrm{repair}}=\operatorname{sigmoid}(\mathbf h_2w_r+b_r),
\qquad
\boldsymbol\pi=\operatorname{softmax}(\mathbf h_2W_s+b_s).
```

结构为 $8\rightarrow32\rightarrow16$，两个输出头分别产生一个 repair probability 和三个 scale probabilities。参数量可直接核算：

```math
(8\times32+32)+(32\times16+16)+(16\times1+1)+(16\times3+3)=884.
```

softmax 保证 $\pi_j\ge0$ 且 $\sum_j\pi_j=1$。运行时阈值为 $\tau_{\mathrm{repair}}=0.05$。即使 $p_{\mathrm{repair}}<\tau_{\mathrm{repair}}$，只要存在 hard violation，系统仍必须进入候选评估，防止学习模型屏蔽强制规则。

#### 3.9.2 监督标签

设第 $i$ 个样本的真实注入缺陷集合为 $\mathcal D_i$：

```math
y_i=\mathbf1[\mathcal D_i\ne\emptyset].
```

若 $c_{ij}$ 是样本 $i$ 在尺度 $j$ 上的注入缺陷数，则：

```math
y_i^{\mathrm{scale}}=\arg\max_jc_{ij},
\qquad
m_i=\mathbf1\!\left[\sum_jc_{ij}>0\right].
```

$m_i$ 使 clean 样本只训练 repair head，不训练没有定义的 scale label。clean 和 corrupted 版本按源文档整体进入同一个 train/validation/test partition，从而避免同一文本跨划分泄漏。

#### 3.9.3 联合损失与训练算法

```math
\mathcal L(\phi)=
-\frac1N\sum_i[y_i\log p_i+(1-y_i)\log(1-p_i)]
-\frac{\lambda}{\max(1,\sum_im_i)}
\sum_i m_i\log\pi_{i,y_i^{\mathrm{scale}}}.
```

第一项是所有样本上的 binary cross-entropy；第二项是 dirty 样本上的 masked categorical cross-entropy。当前 $\lambda=1$，Adam learning rate 为 0.005，以 validation loss early stopping。训练算法可以概括为：

```text
1. 按预先分配的文档组加载 train/validation/test；
2. 只用 train 统计量标准化八维特征；
3. 以前向传播得到 repair logit 和 scale logits；
4. 计算 BCE + masked CE；
5. 反向传播并用 Adam 更新参数；
6. validation loss 改善时保存参数，否则累计 patience；
7. patience 达到 200 时停止，恢复最佳参数；
8. 保存模型、scaler、split 与训练元数据。
```

当前模型训练 1,858 个 epoch，最佳 validation loss 为 0.0001。由于标签由受控缺陷直接生成，路由实验的满分应解释为“网络学会了该注入标签映射”，不能解释为自然缺陷检测已经解决。

多缺陷样本被压缩为一个 dominant-scale 类别，发生计数并列时 `argmax` 会按固定类别顺序选一个标签。这是一个有意的轻量化设计，也意味着 $\boldsymbol\pi$ 还不是严格的多标签缺陷分布估计。

#### 3.9.4 无模型时的后备路由

模型文件或 NumPy 不可用时，系统根据三个尺度的质量缺口构造后备策略：

```math
d_{\mathrm{entity}}=[100-\min(S_{\mathrm{iso}},S_{\mathrm{red}})]_+,
```

```math
d_{\mathrm{graph}}=[100-S_{\mathrm{log}}]_+,
\qquad
d_{\mathrm{context}}=[100-S_{\mathrm{sem}}]_+.
```

当总缺口大于 0 时令 $\pi_j=d_j/\sum_kd_k$，否则使用均匀分布。该分支保证输出仍在概率单纯形中，使生产环境可以继续运行；论文的神经路由实验结果来自已训练模型，不把 fallback 当作学习贡献。

### 3.10 算法四：候选动作构造与图转移

候选动作有四种：

| 动作 | 图上的含义 | 当前风险成本 |
| --- | --- | ---: |
| `complete/add` | 增加一个尚不存在的三元组 | 0.06 |
| `delete/remove` | 删除多重集中一个匹配 occurrence | 0.30 |
| `retype` | 保持 head/tail，替换关系类型 | 0.16 |
| `bundle` | 原子执行多个子动作 | 子动作成本之和 |

候选来自两条路径：外部 recommendation provider，以及当前违反集合自动导出的确定性动作。自动映射包括：

- hierarchy reversal → 删除反向边并添加正确方向的原子 bundle；
- self-loop、empty field、invalid relation → 删除相应 occurrence；
- redundant triple → 删除相似 pair 中的一个 occurrence。

isolated node 和 semantic low evidence 只触发诊断，本身没有足够信息生成正确事实，必须依靠 source-grounded 或 LLM recommendation provider 提供候选。这一边界很重要：constraint detector 能发现问题，并不意味着它总能独立构造正确答案。

候选首先统一字段名和操作名，再以 `(operation, scale, canonical payload)` 为签名去重；相同动作只保留 confidence 最高的实例。bundle 在同一个 trial graph 中原子执行。删除动作只移除一个 occurrence，因此对于完全重复的事实，可以留下一个代表而不会一次清空多重集。

该算法只定义“允许考虑哪些动作”，不保证正确动作一定出现在 $\mathcal A(G)$ 中。因此系统修复召回率的理论上限受 candidate providers 的覆盖率限制。

### 3.11 算法五：恢复型约束门

对第 $i$ 个质量维度设下界 $\ell_i$ 和单步最大允许退化 $\delta_i$：

```math
b_i(q)=
\begin{cases}
\max\{\ell_i,q-\delta_i\},&q\ge\ell_i,\\
q,&q<\ell_i.
\end{cases}
```

候选 $a$ 的 trial state 必须满足：

```math
q_i(T(G,a))\ge b_i(q_i(G)),\quad\forall i,
```

```math
\rho(T(G,a))\le\rho_{\max},
```

并通过 destructive-edit guards。默认百分制下界为：

```text
S_iso >= 55, S_red >= 55, S_log >= 60, S_sem >= 45,
density <= 0.75, delta_i = 2 percentage points.
```

这等价于：

- 如果某维已经达标，下一状态既不能跌破下界，也不能单步下降超过 2 分；
- 如果某维尚未达标，下一状态至少不能比当前更差；
- 删除不能把一个原本非空的图变成空图。

旧的约束若直接要求所有 trial state 立即满足 $q_i\ge\ell_i$，会使初始低质量图没有任何可行动作。恢复边界允许低于阈值的图分多步改善，并保证欠缺维度不继续恶化。

当前 gate 没有单独写出 $h(T(G,a))\le h(G)$ 这一硬违反单调约束。hard violation 的减少通过 utility 奖励，新增 hard violation 则主要通过 $q_{\mathrm{logic}}$、下界和最大退化条件间接阻止。若以后要声称“hard violations 绝不增加”，应在可行性集合中显式增加该不等式并补相应测试；当前论文只保证已写明的一步可行性条件。

### 3.12 算法六：候选效用计算与一步选择

设画像增益为：

```math
\Delta\mathcal Q(a\mid G)=\mathcal Q(T(G,a))-\mathcal Q(G),
```

hard violation 的归一化正向减少为：

```math
g_h(a\mid G)=
\frac{[h(G)-h(T(G,a))]_+}{\max(1,h(G))}.
```

动作效用是：

```math
U(a\mid G)=
\Delta\mathcal Q(a\mid G)
+\kappa g_h(a\mid G)
-\beta c(a)
+\eta\log(\max\{\pi_{\sigma(a)},\pi_{\min}\}+\epsilon_{\log})
+\zeta\operatorname{conf}(a).
```

各项作用如下：

1. $\Delta\mathcal Q$：奖励 trial graph 的整体质量提升；
2. $\kappa g_h$：只奖励实际减少 hard violations 的动作；
3. $-\beta c(a)$：抑制高风险干预，特别是删除；
4. $\eta\log(\cdot)$：让路由器偏好的尺度更容易被选择，但不能绕过约束；
5. $\zeta\operatorname{conf}(a)$：保留候选提供器的置信度信息。

默认参数为：

```text
kappa=0.20, beta=0.35, eta=0.05, zeta=0.02,
pi_min=0.05, epsilon_log=1e-6.
```

对数先验项通常非正，因为 $0<\pi_j\le1$。它不是额外奖励常数，而是对低先验尺度施加更大的负偏置；`pi_min` 防止 $\log0$ 和极端惩罚。置信度项最多约为 0.02，因此不能轻易压过质量损失和删除成本。

每轮只在可行且正效用的候选中选择：

```math
a_t^*=\arg\max_{a\in\mathcal A_{\mathrm{feas}}(G_t)}U(a\mid G_t),
\qquad U(a_t^*\mid G_t)>0.
```

这是对当前有限候选集合的精确一步最优，不是对所有可能图编辑的全局最优，也不是对长度 $T$ 的动作序列进行穷举。

#### 3.12.1 数值示例

假设一个 delete 候选使加权质量从 0.6500 提升到 0.7375，hard violations 从 2 降为 1，graph-scale prior 为 0.60，候选置信度为 0.90。则：

```math
\Delta\mathcal Q=0.0875,\qquad g_h=(2-1)/2=0.5,
```

```math
U\approx0.0875+0.20\times0.5-0.35\times0.30
+0.05\log(0.60)+0.02\times0.90
\approx0.075.
```

若该动作同时通过恢复边界、密度和删除保护，则因 $U>0$ 可以进入最终比较。这个例子也说明删除成本会抵消相当一部分画像增益；只有质量改善、hard violation 减少或高可信候选足够强时，删除才会被接受。

### 3.13 算法七：Profile-Conditioned Constrained KG Repair 主循环

论文中的正式 Algorithm 1 是整个系统的控制算法，可展开为：

```text
输入：初始图 G0、来源文本 X、候选提供器集合、最大轮数 T
G <- G0
for t = 0,...,T-1:
    profile, violations <- Assess(G, X)
    p_repair, pi <- f_phi(profile, graph statistics)
    if p_repair < tau_repair and no hard violation:
        break
    candidates <- external recommendations
                  union actions derived from current violations
    normalize and deduplicate candidates
    for every current candidate a:
        G_trial <- T(G, a) on a deep copy
        profile_trial <- Assess(G_trial, X)
        feasible <- restoration, density and destructive-edit checks
        utility <- U(a | G)
    retain candidates with feasible=true and utility>0
    if retained set is empty:
        break
    commit the candidate with maximum utility
    recompute everything from the new graph in the next round
return G
```

实现还记录每个候选的接受状态、效用、质量变化、hard violation 变化、成本、拒绝原因和 router 输出，形成可审计的 decision trace。同一“图状态—候选签名”组合不会重复试评估，避免无效循环。

该过程称为 receding-horizon replanning，因为它保留有限时域目标的序列语义，却在每一步只解当前的一步子问题，提交后依据新状态重新规划。它与静态 greedy 的差别是画像、违反集合、候选和神经 prior 每轮都会重新计算；它与完整 model-predictive control 的差别是没有向前展开多个未来层级。

### 3.14 数学性质与可证明边界

#### 3.14.1 指标有界性

四个质量维度均由比例或 `[0,1]` evaluator 均值得到，因此都在 $[0,1]$。非负归一化权重的凸组合仍在 $[0,1]$。密度使用简单有向投影，也严格位于 $[0,1]$。这些性质防止某一个异常计数把总质量推出定义域。

#### 3.14.2 一步可行性保持

初始图不要求满足全部下界。对任意被提交的动作，算法先显式检查 $q_i(G_{t+1})\ge b_i(q_i(G_t))$、密度上界和 destructive guards。由提交规则可直接得到：每个已提交转移都满足当前定义的一步可行性条件。

进一步地，如果某一维 $q_i(G_t)<\ell_i$，则 $q_i(G_{t+1})\ge q_i(G_t)$；因此该欠缺维度在被接受序列上单调不降。如果某一维已经达标，则下一步不会跌破 $\ell_i$，并且下降幅度不超过 $\delta_i$。

#### 3.14.3 有限终止性

主循环最多执行 $T=12$ 轮，每轮最多提交一个动作。因此无论候选是否重复，算法都在有限步内终止。实际还可能因低 repair probability、无违反或无正效用可行动作提前停止。

#### 3.14.4 一步最优性

设本轮经去重后候选有限，且每个候选都完成相同的 trial assessment。`argmax` 保证被选动作在本轮正效用可行候选中具有最大 $U$。若存在同分动作，Python `max` 取候选顺序中首先出现者；这不会影响最大效用值，但可能影响后续路径。

#### 3.14.5 不能推出的性质

当前数学模型不能推出以下更强结论：

- 不能保证找到全局最优修复序列，因为没有枚举 $|\mathcal A|^T$ 条路径；
- 不能保证每一步 $\mathcal Q(G)$ 单调增加，因为 hard-violation bonus 可能允许小幅标量下降；
- 不能保证修复所有缺陷，因为正确动作可能没有被 candidate providers 提出；
- 不能保证自然缺陷上的路由准确率，因为训练标签来自合成注入 provenance；
- 不能保证语义事实在世界知识层面为真，在线 proxy 只验证来源文本支持；
- 不能保证相似分量中的所有 pair 都直接超过阈值，因为连通分量包含传递闭包。

这些不是公式错误，而是当前方法的适用边界。论文已经避免把一步约束策略写成全局优化器或强化学习最优策略。

### 3.15 总体复杂度分析

设每个决策轮最多有 $C$ 个候选，图有 $m$ 条三元组，逻辑规则集为 $\mathcal C$，一次文本相似计算和来源匹配的成本分别为 $c_{\mathrm{sim}}$ 与 $c_X$。每个候选都完整重算画像，故保守上界为：

```math
\mathcal O\!\left(
TC[m^2c_{\mathrm{sim}}+m|\mathcal C|+mc_X]
\right).
```

各部分来源为：

- duplicate similarity：$\mathcal O(m^2c_{\mathrm{sim}})$；
- connectivity 与 density：$\mathcal O(|V|+m)$；
- logical checks：最坏 $\mathcal O(m|\mathcal C|)$；
- source-support proxy：$\mathcal O(mc_X)$；
- 884 参数 MLP 推理：相对上述图评估可视为常数开销；
- 对 $C$ 个分数取最大值：$\mathcal O(C)$。

当前 benchmark 是小型 document-level graph，完整重评估换来了定义简单和结果可审计。若扩展到大型 KG，主要瓶颈是 $m^2$ 的相似度比较和每个候选的重复画像计算，可采用相似度索引、局部受影响集合、缓存或分批候选筛选降低成本；这些优化尚未作为当前实验实现声明。

### 3.16 严谨性总体判断

当前数学部分的优点是：指标定义有界；多重图密度和重复率不再出现越界；初始低质量图可以通过恢复边界逐步改善；神经网络的训练目标与代码一致；效用中的每一项都有明确实现；主算法具有有限终止性和一步可行性保证。

当前最需要谨慎表述的地方有四项：

1. `connectivity` 是非孤立比例，不是全图连通度；
2. 监督路由是受控缺陷上的策略先验，不是 RL，也不证明自然缺陷泛化；
3. receding-horizon 算法只在当前候选集上一步最优，不保证全局最优；
4. 在线 semantic proxy 是 source support，不是开放世界 factual correctness。

另外有三处适合在投稿前继续收紧，但不影响当前实现运行：

- 严格来说，允许重复三元组时不应写 $E\subseteq V\times\mathcal R\times V$，更精确的写法是 $E\in\mathsf{Multi}(V\times\mathcal R\times V)$，即笛卡尔积上的有限多重集；
- 空图的 connectivity 为 0，而 uniqueness、logic 和 semantic proxy 因“没有反例”取得 1。四维 gate 会保留这个区别，但不能只看空图的标量平均分；
- `dangling_endpoint` 检查目前在代码中存在，但节点集合同时吸收了所有 triple endpoint，因此按当前 `_nodes` 定义通常不会触发。若要检查实体表与三元组端点的一致性，应另外保留“声明实体集合”。

只要论文继续保持这些边界，当前数学建模与实现总体一致，足以支撑“多尺度约束 + 质量画像 + 神经路由 + 受约束图转移”的核心贡献。

### 3.17 算法、公式与代码对应关系

本节为解释方便拆分出七个算法模块；当前论文正式编号的只有总体控制循环 Algorithm 1，其余模块以公式、段落和函数形式实现。对应关系如下：

| 数学或算法模块 | 论文位置 | 主要实现 |
| --- | --- | --- |
| 四维画像与八维状态 | `overview.tex` Eqs. quality profile/state；`implementation.tex` Eqs. connectivity–density | `MultiScaleConstraintOptimizer.assess` |
| 相似图与分量冗余率 | `implementation.tex` Eqs. similarity/uniqueness | `_triple_sim`、`_redundant_pairs`、`_redundant_excess_rate` |
| 逻辑与来源支持 | `implementation.tex` Eqs. logic/semantic proxy | `_logic_violations`、`_semantic_penalty` |
| 神经路由前向传播 | `implementation.tex` Eq. decision network | `FphiRouter.predict` |
| 路由监督与联合损失 | `implementation.tex` Eqs. repair label/scale label/loss | `exps/decision_network/train_fphi.py` |
| 候选动作与图转移 | `overview.tex` Eq. graph transition | `_recommendations_to_actions`、`_violations_to_actions`、`_apply_candidate` |
| 恢复型可行性集合 | `overview.tex` Eqs. restoration boundary/constrained set | `_check_constraints` |
| 候选效用与风险成本 | `implementation.tex` Eqs. utility/cost | `_utility` |
| 一步选择与滚动重规划 | `implementation.tex` Eq. policy action；`overview.tex` Algorithm 1 | `optimize_and_apply` |

## 4. 指标定义与实现一致性修复

本轮对方法文本和 `content_enhancement/constraint_optimizer.py` 同步进行了以下修正：

| 原问题 | 当前处理 |
| --- | --- |
| 空图 connectivity 被视为满分 | 空图 connectivity 定义为 0 |
| redundancy 的分子可能导致比例超过 1 | 改为三元组相似图各连通分量的可删除比例 |
| 同一条边触发多个逻辑规则时被重复计数 | logic rate 改为“至少违反一项约束的三元组比例” |
| 原始多重边直接用于 density | 改用无自环简单有向投影，结果限制在 `[0,1]` |
| 论文混用了语义 LLM 评分与运行时检测 | 区分 corpus-level LLM evaluator 和在线 deterministic source-support proxy |
| 声称增量更新但代码未实现 | 明确写为完整 trial-graph reassessment，并给出保守复杂度 |
| 训练标签被描述成约束检查器输出 | 改为真实注入缺陷的 provenance 标签 |
| 论文与代码 repair threshold 不一致 | 统一为 `tau_repair=0.05` |
| 权重可能不构成有效加权和 | 运行时自动归一化 |
| 候选按固定顺序遇到即提交 | 每轮评估全部候选，提交最高效用可行动作 |
| 删除会清除重复三元组的全部 occurrence | 每次只删除 multiset 中一个 occurrence |
| fallback router 可能不满足概率单纯形 | 保证始终输出合法 probability simplex |
| hard bonus 按动作类型静态奖励 | 仅在 hard violations 实际减少时奖励 |

## 5. 新增和重构的实验

### 5.1 受控配对 benchmark 与强 Simple Pipeline

主 benchmark 包含 1,499 个 clean/corrupted 文档图、2,998 个 manifested defects，并按源文档以 70/15/15 划分。测试集有 225 个文档和 450 个缺陷。

| 方法 | 缺陷修复率 | Preservation | Over-repair | Triple F1 | Exact |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct LLM | 0.9244 | 0.9687 | 0.0758 | 0.9520 | 0.8267 |
| ReAct-style | 0.8911 | 0.9324 | 0.1667 | 0.9213 | 0.5956 |
| Simple Pipeline | 0.9511 | 0.9723 | 0.0705 | 0.9634 | 0.8400 |
| Full System | **0.9800** | **0.9932** | **0.0167** | **0.9917** | **0.9333** |

Simple Pipeline 使用与 Full System 相同的结构预处理、Claude 模型、一次调用预算和去重，但不使用 profile、learned prior、trial-state utility 或 constraint gate。Full 相对 Simple 有 15 个仅 Full 成功、2 个仅 Simple 成功的缺陷，exact McNemar `p=0.0023499`。这组比较直接检验完整框架是否超越“规则预处理 + 一次 LLM + 简单后处理”。

### 5.2 自然抽取错误

对同一 225 篇 held-out 来源文档执行新的 Text-to-KG 调用。抽取器只看到来源文本、required head 和关系词表，看不到 clean graph、corrupted graph 或 defect manifest，因此该实验没有人工注入缺陷，也没有平衡错误数或错误类别。

- 215/225 个输出可解析；10 个 malformed JSON 作为空图端到端失败保留；
- 77/225 个抽取图与 structured silver reference 不一致；
- 共计 302 个 multiset triple discrepancies。

| 方法 | Error reduction | Preservation | Over-repair | Triple F1 | Exact |
| --- | ---: | ---: | ---: | ---: | ---: |
| Extracted graph | 0.0000 | 1.0000 | 0.0000 | 0.8799 | 0.6578 |
| Simple Pipeline | -0.5915 | 0.9971 | 0.2389 | 0.8807 | 0.6711 |
| Full System | **0.2775** | **1.0000** | **0.0292** | **0.9248** | **0.6844** |

Full 相对 Simple 的 paired F1 差为 `0.04402`，95% bootstrap CI `[0.03067, 0.05766]`；每文档少 `1.0311` 个错误，95% CI `[0.7689, 1.3156]`，one-sided Wilcoxon `p=3.18e-12`。Exact match 的 discordance 为 3 vs 0，`p=0.25`，因此不宣称 exact-match 显著优势。

已冻结 200 条人工复核样本，seed 为 42，SHA-256 为 `27a0dd7b0112c3249440b25ea6c549fa6e1495eb50cc499745aff6d41ada3747`。两名独立人工标注者与 adjudication 尚未完成。仓库已提供标注协议、冻结表格和 Cohen's kappa 统计脚本；当前论文只把结构化字段称为 silver reference，不冒充人工 gold standard。

### 5.3 Constraint gate 独立贡献

对 225 个受控 Full System 输出执行 proposal-level audit：gate 共拒绝 8 个候选，原因全部是 `ungrounded`；8 个均为 non-gold triple，没有拒绝任何 reference triple。Gate 不增加缺陷修复数，但把 over-repair 从 `0.0227` 降至 `0.0167`，并把 F1 从 `0.9895` 提高到 `0.9917`。因此论文把它的作用限定为 conservative validation，而不是事实恢复的主要来源。

### 5.4 Router 真实端到端执行

新增 225 个 clean graph 的真实 Full System 调用，并与 225 个 dirty graph 组合为 mixed stream。被路由的样本使用真实输出、API calls 和 latency；skip 直接返回输入，不再以成本投影替代执行。

- controlled stream：learned、heuristic、threshold 的 route F1 均为 `1.000`，calls/doc 均为 `0.500`；
- natural stream：三者 route F1 均为 `0.842`，FN rate 为 `0.273`，FP rate 为 `0`，calls/doc 为 `0.124`；
- natural stream 中 learned policy 的 triple F1 为 `0.9615`，always route 为 `0.9582`，never route 为 `0.9400`。

Learned router 与 heuristic/threshold policy 完全相同，没有证据支持独立增益。该结果促使论文将 neural router 从 headline contribution 降为 optional implementation。

### 5.5 泛化实验

Leave-one-domain-out controlled routing 在 environment、finance、government 上的 trigger F1 分别为 `1.000`、`1.000`、`0.999`，scale top-1 均为 `1.000`。它只说明受控缺陷映射可跨当前三个领域迁移，不代表自然 OOD 错误已经解决。

固定 60 个 controlled cases、每域 20 个，使用相同输入与调用预算比较 Claude Haiku 和 Gemma 4：

| 模型 | 方法 | Repair | F1 | Exact |
| --- | --- | ---: | ---: | ---: |
| Claude | Direct | 0.958 | 0.970 | 0.867 |
| Claude | Simple | 0.958 | 0.966 | 0.833 |
| Claude | Full | **0.975** | **0.991** | **0.917** |
| Gemma | Direct | 0.958 | 0.988 | 0.883 |
| Gemma | Simple | 0.967 | 0.984 | 0.867 |
| Gemma | Full | **0.983** | **0.990** | **0.917** |

Qwen 和 GPT 端点在最短样本上长时间无响应，没有生成可比较结果。论文没有把端点不可用解释为模型质量。

### 5.6 Profile scaling

使用真实文档图构造 1K、5K、10K 和 50K triples 的 disjoint batches。Full profile 报告 7 次 CPU 运行的中位数，单文档 incremental update 报告 200 次中位数。

| Triples | Documents | Full profile | Incremental | Graph state |
| ---: | ---: | ---: | ---: | ---: |
| 1K | 143 | 1.48 ms | 0.011 ms | 0.34 MB |
| 5K | 715 | 7.81 ms | 0.012 ms | 1.70 MB |
| 10K | 1,430 | 17.38 ms | 0.029 ms | 3.42 MB |
| 50K | 7,149 | 85.68 ms | 0.012 ms | 17.15 MB |

该结果只测部署时使用的八维 routing profile，不包含 LLM latency 或 quadratic semantic duplicate search，论文已明确这一边界。

### 5.7 保留的辅助实验

独立 Gemma semantic judge、Neo4j LLM Knowledge Graph Builder 小规模对比、失败审计和旧 corpus-level quality score 仍作为辅助证据保留。它们不承担自然错误、完整机制增益或大规模 KG 能力的核心结论。

## 6. 实验图和方法图修改

### 6.1 当前图表体系

活动稿件实际引用四个 vector PDF 文件：三张方法图，以及一张汇总 controlled、natural-error、gate、router、cross-model 和 scaling 结果的多面板实验图。旧的诊断、语义可靠性、路由与失败审计 PDF 仍可由脚本重建并用于补充材料，但不计入当前正文的活动图文件。

旧的聚合柱状图、折线图和未被当前主张支持的 convergence、weight sensitivity、web-search ablation 等图已从投稿稿件和活动图目录中移除，避免与当前实验设计混淆。

### 6.2 字体、格式和清晰度

- 当前正文引用的四个图文件均为 vector PDF；
- 图中文字、粗体和数学标签统一为 Times New Roman；
- 方法图依据作者原 PNG 的结构和视觉元素重新绘制；
- 同时保留原始 PNG、投稿用 PDF 和可编辑 SVG；
- LaTeX 正文只引用 PDF；
- 图表可由 `paper1/make_method_figures.py` 和 `paper1/make_submission_figures.py` 重建；
- 重建图表不需要 API 请求或下载模型。

## 7. 参考文献与 DMKD 格式修改

对 `paper1/references.bib` 全部 45 条记录以及当前正文引用进行了逐条核查，主要修复包括：

- 更正 Lin 2025、Bian 2025、Wienand 2014 的作者信息；
- 补全 CoT、RAG、Pan 等文献的作者；
- 将无法核实的旧 KG quality survey 元数据组合替换为可核实正式文献；
- 将 Ji、Pan Roadmap、White Prompt Catalog 等更新为正式发表信息；
- 将实验中实际使用的 Gemma 4 对齐到对应技术报告和模型卡；
- 补全 DOI、卷期、页码和 BibTeX 大小写保护；
- 修正 NBFNet、MINERVA、MetaR、CoT、RAG 等文献在正文中的作用描述；
- 删除“现有方法都没有约束”等过强概括，补入 AMIE、RuDiK 和约束嵌入相关工作。

DMKD 要求正文采用作者—年份引用并按作者排序。论文已从 `sn-nature` 数字制切换到 Springer Nature 官方 `sn-basic` 样式，正文括号引用统一为 `\citep`。

最终状态：

- 45 条 BibTeX；
- 当前正文引用 44 个独立键；
- 无缺失键、重复键或重复 DOI；
- `.bbl` 中 44 条与正文引用集合完全一致；
- 仅旧 Qwen 技术报告未被当前论文引用；
- BibTeX warning 为 0，无 undefined citation。

仍需在投稿前人工确认 Lin 2025、Bian 2025、Pan position paper 和 Gemma 4 technical report 的最新发表状态，因为当前可核实版本仍属于预印本或技术报告。

## 8. 论文结构与论述调整

当前 DMKD 投稿入口为 `paper1/main.tex`，活动章节为：

- `sections/abstract.tex`；
- `sections/introduction.tex`；
- `sections/related_work.tex`；
- `sections/overview.tex`；
- `sections/implementation.tex`；
- `sections/experiments.tex`；
- `sections/conclusion.tex`。

主要调整包括：

- 摘要、引言和结论改为围绕 document-level、profile-conditioned、constraint-guided repair；
- 实验章节重写为 controlled benchmark、natural extraction errors、strong simple baseline、gate audit、真实 router execution、generalization 和 scaling；
- 删除未实现的 retrieval、增量更新和 convergence 声明；
- 删除与 `overview.tex`、`implementation.tex` 重复且内容过时的 `sections/methodology.tex`；
- 明确论文不声称全局最优、跨文档/因果能力、自然缺陷完美泛化或外部平台 superiority；
- 旧 ACL 草稿不参与投稿编译。

## 9. 代码、数据和复现材料

| 内容 | 位置 |
| --- | --- |
| DMKD 投稿主文件 | `paper1/main.tex` |
| 方法正文 | `paper1/sections/overview.tex`、`paper1/sections/implementation.tex` |
| 实验正文 | `paper1/sections/experiments.tex` |
| 运行时约束优化器 | `content_enhancement/constraint_optimizer.py` |
| paired benchmark | `exps/paper1_repair_benchmark/` |
| 六项投稿扩展实验 | `exps/paper1_submission_extensions/` |
| 神经路由实验 | `exps/decision_network/` |
| Neo4j 外部对比 | `exps/neo4j_graph_builder_benchmark/` |
| 方法图生成 | `paper1/make_method_figures.py` |
| 实验图生成 | `paper1/make_submission_figures.py` |
| 方法—实现审计 | `docs/audits/paper1_method_implementation_audit.md` |
| 参考文献审计 | `docs/audits/paper1_reference_check.md` |
| 参考文献证据 | `docs/audits/paper1_reference_sources.json` |

主 benchmark 的复现顺序：

```bash
python3 exps/paper1_repair_benchmark/build_benchmark.py
python3 exps/paper1_repair_benchmark/run_benchmark.py --split test --workers 4
python3 exps/paper1_repair_benchmark/analyze_results.py
python3 exps/paper1_repair_benchmark/analyze_ablations.py
python3 exps/paper1_repair_benchmark/build_failure_audit.py
python3 exps/paper1_repair_benchmark/semantic_reliability.py
```

六项投稿扩展的复现顺序：

```bash
python3 exps/paper1_submission_extensions/run_api_experiments.py --stages all --workers 3
python3 exps/paper1_submission_extensions/run_scalability.py
python3 exps/paper1_submission_extensions/analyze_experiments.py
# 两名独立标注者和 adjudication 完成后再运行：
python3 exps/paper1_submission_extensions/score_human_annotations.py
```

API key 只从被 Git 忽略的本地 `api` 文件读取，不写入论文、日志汇总或实验产物。本轮没有下载本地模型。

## 10. 验证结果

本轮六项投稿扩展完成后的验证结果：

- 新实验分析和规模脚本可通过 Python 编译检查；
- 自然错误、Simple Pipeline、gate audit、真实 router、LODO/跨模型和 scaling 的归档结果可由统一分析脚本读取；
- 当前 LaTeX 引用均可解析；
- Tectonic 编译成功，生成 25 页 `paper1/main.pdf`；
- 无 unresolved references、undefined citations 或 overfull box；
- 当前四个活动图文件均为矢量 PDF，字体为 Times New Roman；
- 剩余信息为模板已有的 underfull-box、旧 `algorithm.sty` 编码和 Tectonic bbl 重跑提示，不影响当前编译结果。

## 11. 近期提交索引

以下提交共同构成本轮修订，按时间顺序列出：

| 提交 | 内容 |
| --- | --- |
| `012319f` | 增加 Neo4j Text-to-KG 对比 |
| `93dfbf2` | 补齐投稿关键 baseline 与 ablation |
| `2d4ea1f` | 固定 corruption 和 split 的可复现性 |
| `e91bb3a` | 建立 paired repair benchmark |
| `a236b57` | 增加统一 benchmark runner 和指标测试 |
| `12a0826` | 加入 API 限流恢复 |
| `5e3ad20` | 按文档隔离重新训练 router，消除数据泄漏 |
| `07b95f1` | 将 benchmark 对齐到可用共享模型 |
| `a784811` | 删除无实现支持的 retrieval 和 convergence 声明 |
| `0f0a90e` | 增加可复现 failure audit |
| `92295a2` | 增加组件消融分析 |
| `12ab12e` | 增加独立语义可靠性协议 |
| `3d8de9f` | 修正 environment clean semantic score |
| `b761c96` | 对齐 environment aggregate score |
| `0c1b1b9` | 增加 paired benchmark 文档 |
| `9fa97f1` | 防止修复输出被截断 |
| `dc3a0fb` | 强制 baseline 输出合法 JSON escaping |
| `35eaf5b` | 归档完整 benchmark 结果与预测 |
| `5538e79` | 完成语义可靠性和路由成本验证 |
| `52f610f` | 将论文评价中心切换到 paired repair benchmark |
| `820fec6` | 明确 DMKD 投稿源文件和构建入口 |
| `0846a44` | 重做投稿图并清理旧图 |
| `3966ff2` | 全图 Times New Roman，方法图重建为矢量版本 |
| `d34e701` | 核查参考文献并对齐 DMKD 引用格式 |
| `af7e121` | 正式化受约束神经修复策略并同步实现 |

## 12. 当前投稿前检查重点

六项自动化实验、论文改写和复现材料已经完成。投稿前剩余重点为：

1. 安排两名真实标注者独立填写冻结的 200 条自然差异样本，并在 adjudication 后运行 `score_human_annotations.py`；
2. 由作者和导师确认收窄后的标题与贡献列表；
3. 对照 DMKD 最新 author checklist 检查匿名、声明、代码/数据链接、图表尺寸和补充材料；
4. 人工通读 25 页 PDF，检查分页、浮动体位置、表格字号和英文表达；
5. 再次核实仍为预印本或技术报告的参考文献是否已有正式版本。

除真实人工标注外，不再需要新增一条大规模实验分支。若人工复核发现 silver reference 有系统偏差，应据实重算 natural-error 指标并更新论文，不应保留当前数值。

这份汇总记录当前仓库状态。若它与较早草稿、旧图或旧实验说明冲突，应以 `paper1/main.tex`、活动 sections、`exps/paper1_submission_extensions/` 的归档结果和审计报告为准。
