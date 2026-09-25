# Paper1 与 Paper2：当前版本完整数学解释及一致性审查

审查日期：2026-09-25。对象是提交 `f10233a` 的当前英文稿、实际被主文件引入的章节，以及相应执行代码。本文只新增审查文档和本地反例，没有修改两篇论文、生产代码、已有实验或人工标注文件，没有调用 API。

先区分三条执行路径：

| 路径 | 数学对象 | 实际机制 | 对应证据 |
|---|---|---|---|
| Paper1 主方法 | 给定模型候选下的字段图约束选择 | 一次生成，确定性筛选 | 主修复结果、匹配 prompt/gate 比较、收据实验 |
| Paper1 顺序变体 | 带学习先验的单步候选效用最大化 | 监督学习 MLP 路由 + trial graph 枚举 | 独立固定 proposal 重放；不能用主方法的 98% 代替 |
| Paper2 | 有限时域图谱/规则序列决策 | 实际 DQN / Double DQN 训练 | 原二十个模型及新增四十个消融模型 |

Paper1 的 `sections/appendix.tex` 当前没有被 `main.tex` 引入；旧文档中的语义评分、PMI、DBSCAN、重复掩码置信度等，不能自动算作当前投稿稿件已经实现或验证的数学。Paper2 的旧 Section 3.4 数学改进文档同样不代表当前运行协议。

本文把“公式错误”“实现不一致”“目标与语义正确性不同”“实验不足”分开。后面标为建议的表达，不是已经替换进论文的新方法。

## 一、Paper1 的主方法

对应源文件：[overview.tex](../../paper1/sections/overview.tex)、[implementation.tex](../../paper1/sections/implementation.tex)。

### 1. 输入是多重集，输出是有字段容量限制的图

一条三元组为 $t=(h,r,o)$：主体、关系、值。输入 $G$ 是多重集，允许一条三元组出现多次。$m_G(t)$ 表示出现次数，$|G|=\sum_t m_G(t)$。

另有来源文本 $X$、指定文档节点 $h_0$、允许关系集合 $\mathcal R_X$。参考图 $G^*$ 用于评分，不应作为生成器的输入。当前任务规定每个关系至多一个非空值。例如：

$$G=\{(d,\text{company},\text{ABC}),(d,\text{total},120)\}.$$

这是一篇文档对应一个字段图的模型。它不直接支持一个作者关系有多个作者等一般 KG 情况；若要支持，需要定义容量 $b_r$，或改用文档—字段实例结构。

**判断：**这是合理的任务限定，不是通用 KG 约束。参考头节点在旧存储布局里来自参考记录，正文已明确把它视为所有方法共同获得的任务元数据；不应混同为允许读取参考值。

### 2. 预处理 $P$ 做什么

$$G_s=P(G;h_0,\mathcal R_X).$$

实际操作为：必要时交换 head/tail，使已知文档节点成为 head；删除不合法 head 或 relation；对最终三元组精确去重。它不调用模型，也不恢复文本中的缺失字段。

反向修正是当前字段任务的约定，并非任意关系都可以交换两端而保持意义。例如一般 KG 中 `A 属于 B` 不能靠交换变成等义关系。此处使用该操作的理由是 schema 已约定“文档 → 字段值”。

### 3. 三个谓词：合法主体、合法字段、字面来源支持

$$H(t)=\mathbf1[h=h_0],\qquad R(t)=\mathbf1[r\in\mathcal R_X],$$

$$S(t;X)=\mathbf1[o\ne\varnothing\ \land\ o\text{ 是 }X\text{ 的子串}].$$

指示函数 $\mathbf1[A]$ 在条件 $A$ 为真时为 1，否则为 0。因此 $HRS=1$ 等价于三个条件同时满足。

这三个检查都可执行，但它们不等于事实正确性：

- $H$ 检查主体身份，不理解主体之间的关系。
- $R$ 检查字段名在词表内，不判断值是否属于这个字段。
- $S$ 检查字符串出现，不判断否定、条件、单位、时间、字段对应关系。

**已执行反例：**来源为 `Subtotal 100; total 120`，候选 `(receipt,total,100)` 会通过全部三个谓词，但总额取错了。`12` 也可能作为 `120` 的子串通过；保留空白或大小写并不等于执行词边界检查。

所以准确表述是“schema 合法且字面可定位的候选”，不能推出“语义正确的候选”。这个结论不否定过滤的用途，只界定它的保证。

### 4. 诊断向量 $D$ 的含义及冗余

$$D(G_s,X)=(n_{\rm dup},I_H,I_R,I_S,\mathcal R(G_s)).$$

其中 $n_{\rm dup}$ 是多余重复次数；$I_H,I_R,I_S$ 是不通过对应检查的下标集合；$\mathcal R(G_s)$ 是当前出现的关系集合。

例如 $I_S=\{i:S(t_i;X)=0\}$。这是**结构化报告**，不需要被解释成一个可微的神经表征。

关键问题：它在预处理之后计算。按当前 $P$ 的定义，重复、错误 head 和不合法 relation 已被删除，因此正常情况下

$$n_{\rm dup}=0,\qquad I_H=I_R=\varnothing.$$

剩下较有信息量的是来源不支持的值和关系出现情况。但“未出现的允许关系”不一定应当存在，因为字段允许缺失。仅靠 $D$ 不能判断语义缺失。

**小型实现不一致：**`exps/paper1_mechanism_audit/protocol.py:diagnosis` 使用 `tail not in source`，未单独检查非空。Python 的空串是任意字符串的子串，空 tail 因而未被加入 `unsupported_indices`；正文 $S$ 则明确要求非空。已用 toy 输入复现。候选解析器通常会删除空 tail，不能据此宣称已有数值必然受影响，但定义与诊断实现应该统一。

### 5. 模型生成式是模块定义，不是优化定理

$$C=L_\theta(X,h_0,\mathcal R_X,G_s,D(G_s,X)).$$

$C$ 是有顺序的候选列表，$\theta$ 是已服务模型的参数。Paper1 的实验没有通过本论文损失函数更新 $\theta$。式子说明输入输出依赖关系，不证明模型会恢复事实，也不证明其输出是某个约束问题的最优解。

更完整但无需强行写进正文的表达可以是

$$Y\sim p_\theta(\cdot\mid X,h_0,\mathcal R_X,G_s,D),\qquad C=\operatorname{Parse}(Y).$$

temperature 为零并不构成服务端绝对确定性的数学保证。格式失败应保持在评分分母内；这是评估约定。

### 6. 可行集与最大保留数：命题成立，但保证很窄

先过滤独立不合格项：

$$C_X=\{t\in\operatorname{uniq}(C):H(t)R(t)S(t;X)=1\}.$$

再定义容量约束：

$$\mathcal F(C_X)=\left\{A\subseteq C_X:\sum_{t\in A}\mathbf1[r_t=r]\le1,\ \forall r\in\mathcal R_X\right\}.$$

把候选按关系分组 $C_r=\{t\in C_X:r_t=r\}$。不同关系的分组不重叠，每组容量为一。

**证明：**

1. 任意可行输出每个非空分组最多拿一个，因此 $|A|\le\sum_r\mathbf1[C_r\ne\varnothing]$。
2. 当前算法扫描生成顺序，对每个非空分组保留第一个合格候选，达到这个上界。
3. 因而

$$|\widehat G|=\max_{A\in\mathcal F(C_X)}|A|=\sum_r\mathbf1[C_r\ne\varnothing].$$

这里优化的是**候选数量**。从组合优化角度看，是每组容量为一的划分约束；这个特例的证明只需要上述两步。

它不保证：值选对、修改最少、正确旧事实保留、跨字段一致或不存在冲突。例如 `total=100`、`total=120` 都通过来源检查时，只保留先生成的一个。交换顺序可改变事实准确率，但最优候选数量仍相同。

若今后增加日期前后关系、金额加和等跨字段约束，各组便不再独立，现有证明不能直接沿用。若引入有意义的候选权重 $w(t)$，独立容量问题可按每组最大权重求解，但这也是一个新的目标，不能把现有 first-in-order 算法解释成已经在优化 $w(t)$。

### 7. 算法 1 的过程及复杂度

算法依次执行预处理、诊断、一次完整图生成、解析、按顺序过滤，记录拒绝理由。它返回一个新的完整输出，而非必然对原图作最少编辑。

记输入三元组数为 $n$、候选数为 $k$、一次来源匹配成本为 $c_X$。使用哈希集合时：

$$T_P=O(n),\qquad T_{\rm gate}=O(k(1+c_X)),$$

辅助存储为 $O(k+|\mathcal R_X|)$，这里以三元组操作数为单位，不把任意长字符串当作真实常数成本。朴素子串匹配的保守界可写成 $O(|X||o|)$；实际 Python 实现可能更好。LLM 推理成本另计。

**判断：**主流程的复杂度表述基本合理。它不适用于下面包含两两相似度比较的顺序优化器。

### 8. Evidence Index 与三种字符串口径

令来源由 $m$ 行组成 $X=(\ell_1,\ldots,\ell_m)$。字段 $r$ 的模式匹配函数为 $a_r$：

$$A_r=\{i:a_r(\ell_i)=1\},$$

$$E_r=\bigcup_{i\in A_r}\{i-1,i,i+1,i+2\}\cap\{1,\ldots,m\}.$$

$A_r$ 是锚点，$E_r$ 是一行前文与两行后文的邻域。total 模式另排除 subtotal 锚点。索引给模型提示“优先复查哪些行”，没有提供参考值，也没有硬性规定输出必须来自 $E_r$。所有比较方法仍看到全文。

因此其收益不能直接解释成“减少了模型可见文本”或“保证抽取范围正确”。是否来自定位、额外 token、字段定义或当前图，需要对应消融来区分。

当前有三种不同的文本等价规则：

| 用途 | 变换 | 性质 |
|---|---|---|
| 早期主 gate | 字面 substring（解析后字段已经折叠空白） | 多行文本与解析后的单空格可能不一致 |
| 收据 follow-up gate | $N(s)$：空白段折为一个空格，并首尾 trim | $S_{ws}=\mathbf1[|N(o)|>0\land N(o)\subseteq N(X)]$ |
| 顺序优化器来源评分 | 删除全部空白 | 可能把 `AB C` 与 `A BC` 都变成 `ABC` |
| 次要 normalized F1 | 删除空白并 casefold | 是评分宽容规则，不是事实正确性标签 |

其中 $\subseteq$ 在该表中表示子串匹配，不是数学集合包含。规范化可以减少格式性误拒，但仍不能证明字段语义、否定或金额角色正确。

## 二、Paper1 的顺序优化与神经路由

对应代码：[constraint_optimizer.py](../../content_enhancement/constraint_optimizer.py)、[train_fphi.py](../../exps/decision_network/train_fphi.py)。当前正文仅概要介绍，下面补全实现中的数学。

### 9. 四维质量 profile

令 $V$ 包含声明实体和所有三元组端点，$m$ 为边数，$I$ 为孤立节点数。运行时的四分量为：

$$Q_{inc}=100(1-I/|V|),$$

$$Q_{uniq}=100\,c/m,$$

其中 $c$ 是“相似三元组图”的连通分量数。任意两条三元组达到相似阈值就连边，连通分量内保留一个代表的解释给出冗余率 $(m-c)/m$。

实际相似度不是训练 embedding，而是字符 bigram 频数向量的余弦相似度：

$$\operatorname{sim}(t_i,t_j)=0.4\cos(v_{h_i},v_{h_j})+0.2\cos(v_{r_i},v_{r_j})+0.4\cos(v_{o_i},v_{o_j}),$$

阈值为 0.92。相似度阈值关系不具传递性，A 类似 B、B 类似 C 不保证 A 类似 C；连通分量去重是一种建模选择，不能被称为逻辑上的等价事实合并。

设被至少一条已实现逻辑规则标记的边数为 $B$，来源不支持的尾值数为 $U$：

$$Q_{rule}=100(1-B/m),\qquad Q_{src}=100(1-U/m).$$

逻辑比例按“违反规则的边”去重，但后面的 hard-violation 奖励按“规则违反记录”计数，两者分母不同。一个三元组可触发多条 hard violation。

来源为空但存在边时，代码设 $Q_{src}=50$；无边时，uniqueness、rule 和 source 分量均为 100。这些是边界约定，不是校准后的正确概率。

最终 profile score 为

$$Q_p(G)=\sum_{j=1}^4w_jQ_j(G),\quad w_j\ge0,\quad\sum_jw_j=1,$$

默认四个权重均为 1/4，因此 $Q_p\in[0,100]$。加权平均可作为代理目标，但不同方面可以互相补偿，不能自动充当事实正确率。

**关键反例：**来源包含 company 和 total，仅保留正确 company，运行时四分量均为 100，且没有 violation。因此“profile 满分”或“无检测违反”不能推出字段完整。这解释了缺失字段修复为何会被停止规则直接跳过。

对只有指定文档实体、值都由边端点引入的非空字段星形图，所有节点天然与一条边关联，$Q_{inc}$ 几乎恒为 100。因此把它叫“完整性”尤其不合适。

### 10. 节点密度、逻辑规则的实现问题

密度定义为无自环、有向简单投影上的

$$\rho(G)=\frac{|\{(h,o):\exists r,(h,r,o)\in G,h\ne o\}|}{|V|(|V|-1)}.$$

这比直接用多关系边数作分子合理，保证 $\rho\le1$。单中心字段星形图若有 $n$ 个节点，则 $\rho\le1/n\le0.5$（$n\ge2$），所以默认上限 0.75 对这类规范图通常不可能触发。无作用的 density 消融不等于它已经有效防止过密修复。

另有两处代码问题：

1. `_nodes` 先把所有边端点加进 $V$，随后 `_logic_violations` 检查端点是否不属于 $V$。按这个定义，dangling-endpoint 检查对有效解析边不可触发。若需发现“未声明节点”，应另外维护声明节点集合，不能和端点闭包混用。
2. `_hierarchy_reversal` 对“管理、监管、上级、隶属于”共用“低级主体 → 高级客体”为错的模式。但 `甲县 隶属于 乙省` 的方向通常正确。已复现该误报。关系方向必须分别定义，不能只靠层级关键词判断。

以上是顺序优化器的问题，不能直接归为主 gate 的错误；它们执行的是不同检查。

### 11. 神经网络 $f_\phi$ 实际上在学什么

输入为八维向量

$$z=[Q_{inc},Q_{uniq},Q_{rule},Q_{src},|V|,|E|,\rho,n_{viol}],$$

先用训练集统计量标准化，随后

$$h_1=\operatorname{ReLU}(W_1\widetilde z+b_1),\quad
h_2=\operatorname{ReLU}(W_2h_1+b_2),$$

$$p_{repair}=\sigma(w_r^Th_2+b_r),\qquad
\pi=\operatorname{softmax}(W_sh_2+b_s).$$

网络结构是 $8\to32\to16\to(1+3)$，共 884 个参数。repair head 输出二分类分数；scope head 输出 entity、graph、context 的三类分布。

训练损失为

$$\mathcal L=\frac1N\sum_i\operatorname{BCE}(p_i,y_i)+
\lambda\frac{\sum_i m_i[-\log\pi_{i,c_i}]}{\sum_i m_i+\epsilon},\qquad\lambda=1,$$

$m_i$ 只允许有缺陷类别的样本参与 scope 分类。$y_i,c_i$ 来自注入缺陷及其类别映射，训练采用 Adam。

**判断：**这是有监督多任务分类，不是 Bellman 更新或 policy-gradient RL。它可以给 RL 系统提供先验，但训练这个网络本身不构成 RL。$\pi$ 是缺陷类别的预测，不是已经学习到的动作长期价值；两者不能互换。

**严重一致性问题：**旧训练特征 `S_iso` 用的是

$$100\left(1-\frac{|R_{gold}\setminus R_{present}|}{\max(1,|R_{gold}|)}\right),$$

其中 $R_{gold}$ 来自参考图。运行时同名特征却是“非孤立节点比例”。前者需要推理时不应获得的参考字段存在信息，后者在字段图中经常恒为 100。缺陷计数及其他特征口径也有差异。训练集按文档分组能阻止跨划分复制，但不能消除这种 oracle feature 与运行时语义不一致。

因此旧高分类分数不能当作上线路由有效性的证明。当前论文已把旧路由结论降为历史证据；若继续把它作为有效组件，应先用同一个、仅依赖公共输入的特征函数重新构造数据并训练。不要直接重训原脚本后沿用它的标签泄漏特征。

### 12. 单步效用函数与成本为什么挡住修复

对候选动作 $a$，令试探图为 $G'=T(G,a)$。实际效用为

$$U(a)=\frac{Q_p(G')-Q_p(G)}{100}
+0.20\frac{\max(0,H(G)-H(G'))}{\max(1,H(G))}
-0.35c(a)
+0.05\log(\max(\pi_{scale(a)},0.05)+10^{-6})
+0.02\,conf(a).$$

这里 $H(G)$ 是 hard-violation 记录数，区别于主方法的 head 谓词 $H(t)$。默认成本为 add/complete 0.06、delete 0.30、retype 0.16；bundle 按其中原子动作成本求和。这里的成本是设定的效用系数，不是已经测得的 API 费用。

顺序选择规则是

$$a_t\in\arg\max_{a\in\mathcal A_t^{feas}}U_t(a),\qquad\text{只在 }U_t(a_t)>0\text{ 时接受}.$$

即每一步把有限候选都放入 trial graph，选择当前效用最大的可行项。它没有学习未来价值，也没有全局编辑序列最优性保证。

**默认阈值的具体推导：**假设没有 hard-violation 收益，使用均匀 scope prior $1/3$，proposal confidence 为 0.7，则

$$0.05\log(1/3+10^{-6})\approx-0.0549305,\quad0.02\times0.7=0.014.$$

- 添加一条：必须 $\Delta Q_p/100>0.021+0.0549305-0.014=0.0619305$，即 profile 提高 **6.193 分**以上。
- 删除旧值再添加新值的替换：成本 $0.30+0.06=0.36$，必须 profile 提高 **16.693 分**以上。

假如旧值和新值都在来源中、字段也合法，语义上替换是正确的，但 profile 可能几乎不变，因而被拒绝。对一个已满分但缺字段的图，补字段也不能提升 profile。

另一个重要点：均匀 prior 对候选排序贡献相同，但它不是对接受决策无影响的常数，因为算法与零比较。它把全体候选的接受门槛抬高了。若以后想让 prior 只作相对偏好，可研究相对均匀基准的项 $\eta\log(\widetilde\pi/(1/3))$，但这会改变方法，需要开发集选择和重新评估，不能无实验地宣称改善。

clamp 后的 prior 没有重新归一化，因而其 log 项最好解释成有界偏好惩罚，而不是严格的对数概率目标。

### 13. 约束是局部可行性恢复，不是一次投影到全可行域

设分量下限为 $l_j$。实际检查分两种情况：

$$q_j\ge l_j\Rightarrow q'_j\ge l_j,$$

$$q_j<l_j\Rightarrow q'_j\ge q_j.$$

同时要求 $q'_j\ge q_j-2$，并检查密度上限。默认下限为 55、55、60、45。

输入已经达标时，保护它不跌破下限；输入不达标时，允许逐步改善，而不是要求一步达到下限。这是合理的 restoration 设计。但它允许已达标分量小幅下降，且 $U>0$ 包含硬违反奖励和置信度项，所以不能推出每步 $Q_p$ 严格上升，更不能推出 F1 上升。

最多 12 步、候选与状态缓存保证实现有停止控制。其停止条件还包括低 repair 分数且没有 hard violation、无 detected violation、无正效用可行候选。这些是算法停止规则，不是“真实错误已全部修复”的证书。

逐步优化器每次 profile 的冗余检查包含 $O(m^2)$ 次相似度比较。若每轮 $K$ 个候选、最多 $T$ 轮，忽略字符串长度时总体可达 $O(TKm^2)$，另加图复制与编辑。不能用主 gate 的近线性复杂度来描述这条路径。

## 三、Paper2 的 RL 数学

对应：[methodology.tex](../../paper2/sections/methodology.tex)、[run_experiment.py](../../exps/paper2_cooptimization/run_experiment.py)。

### 14. 图质量是四类结构缺陷的加权补量

令节点数为 $n$、关系记录数为 $m$，隔离节点、重复关系的多余份数、不合法关系、悬空边的计数依次为 $d_I,d_D,d_V,d_L$：

$$I_r=d_I/\max(1,n),\quad D_r=d_D/\max(1,m),$$
$$V_r=d_V/\max(1,m),\quad L_r=d_L/\max(1,m).$$

$$S(C_1)=1-I_r,\ S(C_2)=1-D_r,\ S(C_3)=1-V_r,\ S(C_4)=1-L_r,$$

$$Q_G=0.2S(C_1)+0.2S(C_2)+0.3S(C_3)+0.3S(C_4).$$

分量在代码中截断到 $[0,1]$。权重非负且和为一，所以 $Q_G\in[0,1]$。

**含义边界：**这是当前四类结构缺陷的代理目标。删除事实可能降低结构缺陷比例，因此高 $Q_G$ 不保证完整性、语义正确性或原事实保留。按当前分母约定，空图四项全为 1；当前动作、任务实例和终止条件限制了这种退化，但质量公式本身没有排除它。

### 15. 在线规则质量来自固定校准库

对 active rule set $R$，每条注册规则给出一个固定预测集合 $P_r$，并集为

$$P_R=\bigcup_{r\in R}P_r.$$

在预设 180-case 校准库存储的 120 个正例、60 个负例上，

$$Precision=\frac{TP}{TP+FP},\quad Recall=\frac{TP}{120},\quad
Coverage=\frac{\#\text{已激活高质量规则族}}4,$$

$$Q_R=0.35Precision+0.35Recall+0.30Coverage.$$

无预测时 precision 约定为 0；空 active set 时 recall 和 coverage 也为 0。这些约定可执行，但空集合的 precision=0 是奖励设计，不是统计估计。

四个高质量模块各命中 27 个不重叠正例和两个不重叠负例。若只激活 $k\ge1$ 个高质量模块：

$$Precision=27/29,\quad Recall=27k/120=0.225k,\quad Coverage=k/4,$$

$$Q_R(k)=0.35(27/29)+0.15375k.$$

| 高质量模块数 | $Q_R$ |
|---:|---:|
| 0 | 0 |
| 1 | 0.4796121 |
| 2 | 0.6333621 |
| 3 | 0.7871121 |
| 4 | 0.9408621 |

因此 registry 获取收益相当规律：先买好规则、再修图很容易成为强策略。这不是 DDQN 数学错误，而是环境不足以充分区分复杂策略的一个结构性原因。

### 16. 联合目标与可达分数上界

定义未归一化联合分数

$$J_t=Q_G(G_t)+0.4Q_R(R_t),$$

以及展示用的加权平均

$$\bar Q_t=J_t/1.4.$$

名义上 $\bar Q\in[0,1]$。不过固定 registry 中四个良好规则最多覆盖 108/120 个正例；其他三个低质量模块在四个好模块齐全时只增加假阳性，不提供新真阳性。

本轮枚举全部 $2^7=128$ 个 registry 子集，确认

$$\max_RQ_R=0.9408620689655172,$$

$$\bar Q\le\frac{1+0.4\times0.9408620689655172}{1.4}
=0.9831034482758622.$$

这是**固定校准库及规则库存下的分数上界**，不证明每个图都能在 18 步内达到。它和之前错误地把单步 greedy 称为“理论上界”是不同的概念。

Double DQN 的 0.98122 是接近这个结构分数上限的加权质量，并非 98.122% 的真实三元组都正确。归一化公式本身没有错；错的是把它当作事实准确率或天然可达 1 的指标来解读。

### 17. 完整状态与 14 维观测

完整状态可表示为

$$s_t=(G_t,R_t,b_t,d_0,M),$$

其中 $b_t$ 为剩余预算，$d_0$ 为初始缺陷计数，$M$ 为环境私有的关系恢复记录。完整状态下局部转移可以定义为有限时域 MDP。

网络输入为

$$o_t=[S_1,S_2,S_3,S_4,P,R,C,
\widetilde d_I,\widetilde d_D,\widetilde d_V,\widetilde d_L,
\widetilde b,\rho_{valid},\rho_{noisy}],$$

$$\widetilde d_j=d_{j,t}/\max(1,d_{j,0}),\quad\widetilde b=(18-t)/18.$$

$\rho_{valid}$ 是四个良好模块的激活比例，$\rho_{noisy}$ 是三个低质量模块的激活比例。观测被截断到 $[0,1.5]$。

**两个重要性质：**

1. 当前 $Coverage=\rho_{valid}$，所以第 7 与第 13 个输入（零基索引 6、12）完全重复。它不是实现崩溃，但不能称为十四个相互独立的信息维度。去规则特征消融已同时去掉二者。
2. $o_t$ 加上可行 mask 也不一定是充分 Markov 状态。聚合统计没有完整图结构。

**已运行的状态混叠反例：**四个存在节点 $a,b,c,d$，另有不存在节点 $z$，所有关系均为 MENTIONS，active rules 相同。

- 图 A：$a\to b,b\to c,d\to z$。
- 图 B：$a\to b,c\to d,a\to z$。

两图节点数、边数、四种缺陷计数、14 维观测和 mask 全部相同。执行 dangling cleanup 后：A 出现一个孤立节点 d，B 不出现孤立节点。奖励分别约 0.04998 和 0.09998，终止判断也不同。

因此不能把 $Q(o,a)$ 当作在充分状态上精确满足 Bellman 方程的 $Q^*(s,a)$。当前稿件已承认观测不保证充分性，这是正确的限定。可把方法理解为部分可观测输入上的值函数近似，未来考虑历史、规则身份或更完整结构表征。

### 18. 八种动作与可行掩码

前四种动作为隔离节点删除、重复关系清理、不合法关系恢复、悬空边清理；每次处理约剩余同类问题的 60%，即非空时 $\lceil0.6d\rceil$。

后四种为 deletion acquisition、augmentation acquisition、mixed acquisition、低精度规则剪枝。前两种各激活固定列表的下一条模块；mixed 从两族各取一条尚未激活的良好模块，良好模块取完后可激活 noisy mixed。prune 保留校准 precision 至少 0.5 的模块。

可行动作集合为

$$\mathcal A_t=\{a:m_t(a)=1\}.$$

图修复通常需要该类 validator 已启用且缺陷仍存在。mask 由完整图和 active rule 身份计算，不必能从十四个聚合值重建。公平基线必须看到相同 mask；no-mask ablation 去掉的是这种动作权限控制和训练 target 中的 mask。

这里的 rule acquisition **没有调用 LLM，也没有执行生成日志中的某条新规则**。此外，RL registry 的 deletion-family 指隔离/悬空检测器，RuleTest 手写 deletion-family 指程序/缺字段/特殊规则，LLM deletion 则是一种生成任务；三者名字相同，不代表已经建立了语义对应关系。

### 19. 奖励函数及折扣目标

$$r_t=J_{t+1}-J_t-0.004C_{call}-2\times10^{-5}C_{edit}-0.01N_{new}.$$

call 分别按单族 1、mixed 2 计入；这是模拟成本。edit 同时计图编辑和 active rule 数量变化。不能把这两种代价当成已实测的真实 API 请求或 tokens。

实际优化的目标为

$$\max_\pi\mathbb E_\pi\left[\sum_{t=0}^{T-1}\gamma^tr_t\right],\qquad\gamma=0.95.$$

若 $\gamma=1$，不考虑成本时增量可望远镜相消为 $J_T-J_0$。但当前 $\gamma<1$，精确展开是

$$\sum_{t=0}^{T-1}\gamma^t(J_{t+1}-J_t)
=-J_0+(1-\gamma)\sum_{t=1}^{T-1}\gamma^{t-1}J_t+\gamma^{T-1}J_T.$$

因此既重视最终质量，也奖励较早获得质量；它不是仅最大化 final quality。费用同样折扣，所以训练目标也不是简单的“最终质量减未折扣总调用费用”。这可以是合理设计，但应写清楚。不能直接套用 potential-based shaping 的策略不变性结论，后者的形式包含 $\gamma\Phi(s')-\Phi(s)$，且依赖基准奖励与条件。

**已确认的实现缺口：**$N_{new}$ 当前由算子固定返回 0，不会检测新违反。上面的图 A 删除悬空边后新增一个孤立节点，但返回的 `new_violations` 仍为 0。$Q_G$ 的重算会反映部分后果，然而额外的 $-0.01N_{new}$ 项确实没有工作。稿件已披露该项 inactive；如要宣称独立安全惩罚有效，需要补实现并重训/重评。

### 20. Double DQN 的选择、估值与梯度

这里的 $Q(o,a;\theta)$ 是**累计奖励预测值**，不是上面的图质量 $Q_G$，也不是动作概率。

在线网络 $\theta$ 选择下一动作：

$$a^*=\arg\max_{a'\in\mathcal A_{t+1}}Q(o_{t+1},a';\theta).$$

目标网络 $\theta^-$ 对该动作估值：

$$y_t=r_t+\gamma(1-d_t)Q(o_{t+1},a^*;\theta^-).$$

$d_t=1$ 时不 bootstrap。空可行集也应单独令 bootstrap 为零。标准 DQN 则用

$$y_t^{DQN}=r_t+\gamma(1-d_t)\max_{a'\in\mathcal A_{t+1}}Q(o_{t+1},a';\theta^-).$$

Double DQN 将选择与估值分开，目的是减少同一估计噪声被 max 放大的倾向，不是保证它一定比 DQN 好。

损失为 Huber：

$$\mathcal L=\mathbb E[\ell(Q(o_t,a_t;\theta)-y_t)],$$

$$\ell(\delta)=\begin{cases}\tfrac12\delta^2,&|\delta|\le1,\\|\delta|-\tfrac12,&|\delta|>1.\end{cases}$$

计算 $y_t$ 时停止梯度；梯度只通过在线网络当前动作输出回传。网络为 $14\to32\to16\to8$，ReLU，共 1,144 个参数。Adam 学习率 0.002，batch 64，replay 20,000，warm-up 128，梯度范数裁剪到 5，每 100 个环境步复制 target 参数。

每个模型训练 250 episodes。探索率是

$$\epsilon_e=1-0.95\min(1,e/260),$$

末个零基 episode $e=249$ 得到 0.0901923，尚未达到最低 0.05。当前稿件这里已经修正，与代码一致。

**小型扩展注意事项：**原始 DDQN trainer 用有限数值检查处理下一步 bootstrap，未显式处理全零 next mask 下在线网络 argmax 返回 0 的分支；新消融 trainer 显式检查 `next_masks.any`。当前 registry 总有 acquisition 或 prune 可行，此分支不影响现有可达状态，但推广动作空间时应统一为显式空集合处理。

### 21. AUC 衡量全过程质量，不是分类 ROC-AUC

$$AUC_{18}=\frac1{18}\sum_{t=0}^{17}\frac{\bar Q_t+\bar Q_{t+1}}2.$$

它是 18 步上的平均轨迹质量，包含初始状态，共 19 个质量值。若第 $k<18$ 步终止，之后都补 $\bar Q_k$。这样各策略面积可比，不会因为轨迹长短不同而改变分母。

AUC 与折扣增量奖励都偏好较早改善，但权重不同，二者不是同一目标。终止条件 $Q_G\ge0.999,Q_R\ge0.90$ 也不等同于零缺陷；较大图中少数剩余缺陷可满足该阈值。

## 四、Paper2 双策略生成与规则执行数学

### 22. 删除与扩展是两种候选提议分布

删除策略：从文本 $T$ 删除若干短字符跨度，得到 $T^-$ 和被删片段 $F$：

$$R_D\sim L_\theta(\cdot\mid T,T^-,F,\text{schema}).$$

原文也给模型，因此是对照式规则 elicitation，不是模型只凭残文推断缺失事实。默认最多五个起点、每段最多六个字符，一次调用。

augmentation：

$$(A,R_A)\sim L_\theta(\cdot\mid T,\text{schema}),$$

一个响应返回最多三条补充条款 $A$ 和由此建议的规则候选 $R_A$，并没有先多次生成图再统计规则频次。

当前定义自洽。旧稿的 $P(r\mid\mathcal D)\approx\mathbb E_{T'\sim\mathcal N(T)}P(r\mid T')$ 没有真实数据分布采样依据；LLM 的邻域扩写不自动构成对真实规则 posterior 的无偏估计。旧的重复掩码频次也不是当前调用协议。本轮解释不把这些旧式子当作已成立理论。

### 23. 并集增长与等预算增长是两个问题

相同文档集上，

$$|R_D\cup R_A|=|R_D|+|R_A|-|R_D\cap R_A|.$$

full archive 有 32,955、41,683、71,656 个分类候选，由此交集为 2,982，并集相对 augmentation 增加

$$\frac{71,656-41,683}{41,683}\approx71.9\%.$$

这是正确算术，但并集用了两倍调用，且候选包含 entity/relation declarations，不能解释为规则正确率或等成本优势。

在 $B$ 次调用预算下，单策略处理 $B$ 篇文档，dual 处理 $B/2$ 篇，每篇调用两个策略。比较应写为 $R_D^{(B)},R_A^{(B)},R_{dual}^{(B)}$，并明确文档覆盖不同。当前等预算结果是 augmentation 的约束候选数量高于 dual；不与同文档互补结论矛盾。

三十次文档排列来自同一份固定日志，只刻画有限日志的采样变化，不是三十次独立模型生成实验，也不能估计跨模型或自然规则语义的置信区间。

### 24. 直接执行只支持精确 typed patterns

可编译模式为 $r=(\tau_s,p,\tau_o)$，记录 $x$ 的匹配函数是

$$M_r(x)=\mathbf1[(type(s_x),p_x,type(o_x))=r].$$

allowed 与 forbidden 必须分别解释。设 $F_x$ 表示命中至少一个 forbidden，$A_x$ 表示命中至少一个 allowed：

- $F_x=1,A_x=0$：输出缺陷。
- $F_x=0,A_x=1$：明确许可，不输出缺陷。
- $F_x=A_x=0$：未命中，不代表已经验证正确。
- $F_x=A_x=1$：冲突，记录 abstention，评分仍保留该案例。

因此代码的阳性输出为 $F_x(1-A_x)$，另存冲突位 $F_xA_x$。正文 $V_r$ 作为 forbidden pattern 的公式正确；若讨论任意 allowed pattern，应称为匹配函数，不能一律叫违反函数。

对 RuleTest-94，$TP=10,FP=0,FN=54,TN=30$：

$$Precision=1,\quad Recall=10/64=0.15625,$$

$$F1=\frac{2TP}{2TP+FP+FN}=\frac{20}{74}=0.270270.$$

augmentation 无阳性预测，precision 分母为零，所以 undefined；不能记为“100% precision”。全部 case 都要留在分母，不能删掉未命中或冲突案例。

18,143 个唯一可编译模式只有两个命中当前 suite；这是词表和可执行语义的衔接问题。手写 family union 的 64/64 是另一个函数的输出，并不证明 LLM 生成规则有 100% 检出率。目前 RL 的固定 registry 也不是这两个命中模式，三条证据链必须分开。

## 五、两篇论文的评分与统计解释

### 25. Paper1 的 multiset F1 与修改指标

用 $g_t=m_{G^*}(t)$、$y_t=m_{\widehat G}(t)$，正确三元组份数为

$$TP=\sum_t\min(g_t,y_t),\quad P=TP/\sum_ty_t,\quad R=TP/\sum_tg_t,$$

$$F1=2PR/(P+R).$$

重复的多余份数可以降低 precision，所以这里不应先把重复全部压成集合再评分。空输出在当前 scorer 中取 F1=0。表中通常先算每篇文档 F1 再平均，是 macro F1，不是把所有文档合成一个大图后的 micro F1。

输入 $G_0$ 与参考共同拥有的 multiset $C=G_0\cap G^*$ 给出 preservation：

$$Preservation=|\widehat G\cap C|/|C|.$$

当没有原始正确事实时，代码约定为 1。它不意味着系统完成了事实恢复。

令所需新增/删除为 $A^*=G^*\setminus G_0,D^*=G_0\setminus G^*$，实际新增/删除为 $A=G_1\setminus G_0,D=G_0\setminus G_1$。这些差集都按 multiplicity 的正差计算。

$$GoodEdits=|A\cap A^*|+|D\cap D^*|,$$

$$OverRepair=\frac{|A|+|D|-GoodEdits}{|A|+|D|}.$$

没有编辑时 over-repair 约定为零。该指标是相对参考的 harmful-edit 比例，不是被修改文档的比例，也不等于 $1-Preservation$。

controlled defect repair 是逐注入缺陷检查。duplicate 要求恢复正确 multiplicity；其他替换型缺陷要求正确 triple 存在且错误 triple 移除；missing 检查正确 triple 恢复。某个缺陷 repaired 不代表整图 exact。

自然错误用

$$d(G,G^*)=\sum_t|m_G(t)-m_{G^*}(t)|,$$

$$ER=1-d(G_1,G^*)/d(G_0,G^*)$$

在初始不完美文档上平均，避免初始距离为零。替换错误值一般涉及一删一增，所以对称差计为两份，不是一个语义错误。负 ER 代表错误增加。

**重要区分：**旧 `analyze_results.py` 中还有一个使用参考 recall 的 `q_score`，它是 scorer 的离线指标，与可部署的 runtime $Q_p$ 不同。不能因为名称都叫 quality score 就把参考 recall 输入运行时优化器。

收据 normalized F1 去空白并忽略大小写，只衡量格式宽容后的精确匹配。它不能替代人工语义判断，也不能认为所有格式等价都是事实等价。

### 26. 配对比较、bootstrap、随机化与 Holm

对相同文档/场景上的两个方法，以 $d_i=m_i^A-m_i^B$ 为单位，报告

$$\bar d=\frac1n\sum_i d_i.$$

bootstrap 重采样整个文档或场景对；同一文档的两个注入缺陷、三个生成 arm 不能被当成完全独立样本。Paper1 新 gate 分析先在文档内对三个 arm 的差值取平均，再跨文档统计，符合这个原则。

配对符号随机化使用 $\epsilon_i\in\{-1,1\}$，比较

$$\left|\frac1n\sum_i\epsilon_id_i\right|\ge|\bar d|.$$

Paper2 十个场景枚举全部 $2^{10}$ 种符号。这里“exact”是指在零假设的配对交换/符号对称条件下枚举精确，而不是无条件证明因果或泛化。

十个检验的 Holm 校正先排序 $p_{(1)}\le\dots\le p_{(10)}$，调整值为

$$p^{adj}_{(i)}=\min\left(1,\max_{j\le i}(10-j+1)p_{(j)}\right).$$

95% pointwise bootstrap 区间和经过 Holm 的显著性是两种口径；某个区间不跨零而校正后 p>0.05 可以同时出现。不能只挑其中更有利的一项。

Paper2 当前结果：规则特征 removal 对 final 和 AUC 都显著；mask removal 对 final 显著，但 AUC 校正后 p=0.0781；graph features 与 call penalty 的独立增益不显著。不能把它概括为全部四个组件都得到证实。对强启发式的两项差异显著，但方向是 DDQN 略差。

所有新 Paper2 比较复用了十个已有场景，且每个训练种子与一个场景配对。因此区间混合了训练与场景变化，不能分解两种方差，更不是新领域泛化区间。

Paper1 旧 defect-level McNemar 比较需要注意每篇文档两个缺陷可能相关；新增按文档配对的检验更适合主推断。人工设计 suite 的 Wilson precision 区间即使很高，也不补足独立随机抽样与自然错误分布的缺失。

## 六、问题分级与建议处理顺序

| 优先级 | 问题 | 类型 | 当前影响与建议 |
|---|---|---|---|
| 高 | Paper1 旧路由训练使用参考字段信息，且与 runtime 特征语义不同 | 实现/评估一致性 | 若恢复路由贡献主张，先统一 gold-free 特征再训练与评估 |
| 高 | Paper1 profile 不衡量缺字段，无 violation 即停止 | 目标不充分 | 用可观测的字段证据/缺失候选机制补足，不能仅改停止描述 |
| 高 | Paper1 first-in-order 最大保留数量不保证事实、最小编辑或保留 | 保证边界 | 现有数量命题保留，但不得扩张其含义 |
| 高 | Paper2 generated rules 尚未进入 RL registry | 方法与证据链断开 | 建立生成→验证→激活动作→修复的可重放闭环 |
| 高 | Paper2 $N_{new}$ 恒为零且真实操作可能新增缺陷 | 实现缺口，正文已披露 | 要主张安全奖励有效，必须实际检测并重训/重评 |
| 中 | Paper2 聚合观测与 mask 不保证 Markov 性 | 理论适用条件，正文已披露 | 保持近似/部分观测表述，或增加历史与结构信息 |
| 中 | Paper1 utility 的 cost 与 log-prior 抬高接受阈值 | 目标尺度设计 | 开发集检查系数、无硬收益的阈值及局部边界，不用测试集调参 |
| 中 | Paper1 层级方向共用规则导致 `隶属于` 误报 | 明确代码问题 | 按 relation 定义方向，并增加正确/反例 |
| 中 | Paper1 dangling 检查使用端点闭包 | 明确代码问题 | 分开声明节点集合与实际出现节点集合 |
| 中 | Paper2 固定规则收益规律、启发式略强 | 实验对研究问题支撑不足 | 用更有差异且未见的规则质量/到达次序测试策略必要性 |
| 低 | Paper1 诊断空值条件与 $S$ 不一致 | 边界实现问题 | 显式检查非空；回放确认是否影响现有案例 |
| 低 | Paper2 Coverage 与 valid fraction 重复 | 表征冗余 | 说明十四个输入非十四个独立信息，精简需另做消融 |
| 低 | 空图分数、无预测 precision、宏/微平均等边界 | 定义口径 | 在复现说明明确，不与语义正确率混用 |

**整体判断：**Paper1 的约束选择等式有一个正确且容易证明的保证；Paper2 的奖励、DDQN target 和统一 AUC 也有标准、可执行的数学定义。当前最需要解决的不是增加公式数量，而是保证这些公式的输入、含义和执行路径确实覆盖论文希望解释的行为。监督路由不能被叫作已训练的 RL；结构高分不能被叫作事实高准确率；规则族测试不能代替生成规则的执行效果。

## 七、如何核查本次结论

```bash
python3 docs/math_audit_2026-09-25/check_examples.py
```

它只调用本地实现，构造小例子并枚举 128 个注册规则子集；不训练、不调用 API、不覆盖已有实验。结果见 [checked_examples.json](checked_examples.json)。源码 SHA 也保存在该文件中。

反例能否定过强的普遍保证，但不能估计它在真实任务中的发生频率。本文没有据反例重新计算或替换已有论文表格，也没有声称完成新增 benchmark。
