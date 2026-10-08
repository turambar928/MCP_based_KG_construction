# Paper2 数学导读：对照论文理解规则、奖励和强化学习

更新：2026-10-08。按当前论文的章节顺序解释。本文只改说明方式，没有修改论文算法或实验。

如果只想先理解方法，可以先读每节的解释和例子，暂时跳过公式；需要核对时再看符号。

可以把系统想成一个整理资料的人：手里有一张可能出错的信息表，也有一些检查规则。他每一步要决定：**先找新规则，还是先修已有问题？** Paper2 用强化学习研究这个选择。

## 先找到论文里的对应位置

TKDE 模板用 III、IV 表示第三、第四章；III-B 表示第三章第二小节。云端若改了顺序，以英文标题为准。

|本导读|论文位置|解释的问题|
|---|---|---|
|1—2|III-B Quality Assessment Model|怎样评价图和规则|
|3|III-C / Environment and Policy Observation|策略看到什么，可以做什么|
|4—5|III-C / Reward and Double DQN|如何给行动打分，怎样训练|
|6|III-D LLM-Based Dual-Strategy Rule Generation，Algorithms 1、2|两种规则生成算法|
|7|III-E Offline Generated-Rule Bridge|文字规则怎样变成可执行检查|
|8|III-E 的 response-level 段落；附录 C-A Source-Evidence Development Test|新文档环境为什么使用另一套奖励|
|9|III-E 的 admission 段落；附录 D-A Context-Bound Admission and Coverage|规则经过核验后才能进入执行器|
|10|IV-B / Matched Policies and Measures；IV-D；附录 D、E|F1、过程分数、穷举和统计怎么读|

先区分：**现有 RL 主实验使用固定规则库；DocRED 新环境使用实际生成候选，但新环境的正式 RL 训练还没完成。** 下面不会把这两套结果当成一套。

## 1. 图质量：四种常见结构错误还有多少

**对应论文：**III-B 的 Graph Quality，[methodology.tex](sections/methodology.tex)，`eq:kg_quality`。

|错误|普通例子|错误比例|
|---|---|---|
|孤立节点|表里留下一个名字，但和任何记录都不相连|$I_r$|
|重复边|同一条记录写了两遍|$D_r$|
|非法关系|字段名不在允许名单里|$V_r$|
|悬空边|记录指向一个不存在的实体编号|$L_r$|

“好”的比例就是 1 减去错误比例。四种比例加权求和：

$$
Q_G=0.20(1-I_r)+0.20(1-D_r)+0.30(1-V_r)+0.30(1-L_r).
$$

例如只有重复问题，重复率为 10%，其余错误为零，那么 $Q_G=0.98$。这表示结构分数高，不表示 98% 的事实经过真人确认。

孤立比例按节点数计算，其余按边的出现次数计算；分母至少取 1。执行器还禁止把原本非空的图删空，避免通过“全部删除”刷高结构分。

## 2. 规则质量：检查规则是否好用

**对应论文：**III-B 的 Rule Quality，[methodology.tex](sections/methodology.tex)，`eq:qr_online`。

把规则用于一份固定的 180 案例检查清单，统计：

$$
\operatorname{Precision}=\frac{TP}{TP+FP},\qquad
\operatorname{Recall}=\frac{TP}{TP+FN}.
$$

$TP$ 是正确报错，$FP$ 是把正常项误报成错误，$FN$ 是漏掉的错误。例如报出 10 个问题，其中 8 个真有问题，precision 就是 80%。

Coverage 是四类缺陷中，有多少类已经有对应检查模块。最终：

$$
Q_R=0.35\operatorname{Precision}+0.35\operatorname{Recall}
+0.30\operatorname{Coverage}.
$$

空规则库按零分处理。这些检查表现来自受控实验预设的校准清单，不是每一步让真人重做评价，也不是对任意新生成规则的正确率保证。

图质量和规则质量合起来，展示时使用：

$$
\bar Q=\frac{Q_G+0.4Q_R}{1.4}.
$$

除以 1.4 是为了把尺度放回 0—1。这个综合分与参考 F1 是两个指标。固定规则库里的最佳 $Q_R$ 约 0.9409，因此即使图完全无结构缺陷，综合分最高也只有约 0.9831，而非 1。这是该规则库的限制。

## 3. 策略的“观察”和“动作”

**对应论文：**III-C 的 Environment and Policy Observation，[methodology.tex](sections/methodology.tex)。

策略不会直接看到所有内部资料，而是看到 14 个数：

$$
o_t=[S_1,S_2,S_3,S_4,P,R,C,
\widetilde n_I,\widetilde n_D,\widetilde n_V,\widetilde n_L,
\widetilde b,\rho_{\rm valid},\rho_{\rm noisy}].
$$

前四个是图分数，$P,R,C$ 是规则的 precision、recall、coverage；接着是四种缺陷相对初始数量的比例、剩余步数比例，以及两类模块的激活比例。

这里 $o_t$ 是第 $t$ 步的简要观察。它像只看报表摘要：两张不同的图可能有相同的 14 个数，所以不能认定它包含了作出最优决策所需的全部信息。

八种动作分为三组：

|动作|作用|
|---|---|
|去孤立、去重、恢复非法关系、清理悬空边|修改图|
|获取 deletion 模块、获取 augmentation 模块、各取一个|增加固定规则库中的检查能力|
|prune|移除低精度模块|

**动作掩码**就是一张“现在允许做什么”的清单：没有启用去重检查器，就先不允许执行相关修复。通常基线也获得同一清单，以保证比较公平。

主实验中恢复关系用到了环境私存的损坏前记录，策略读不到这些答案；这让受控环境有可信的恢复操作，不等于真实错误也已经有同样可靠的修法。

## 4. 奖励：一次操作到底值不值得做

**对应论文：**III-C 的 Reward and Double DQN，`eq:reward_def`、`eq:safety_modes`。

$$
r_t=\Delta Q_G+0.4\Delta Q_R
-0.004C_{\rm call}-2\times10^{-5}C_{\rm edit}-P_t.
$$

从左到右读成：**图变好了多少＋规则变好了多少−获取成本−编辑成本−新错误惩罚。** $\Delta$ 表示“操作后减操作前”。

$C_{\rm call}$ 在主 RL 实验里只是模拟成本单位，训练没有发 HTTP 请求。$C_{\rm edit}$ 记录图和规则的改动次数。不能把它们直接读成真实费用。

### 为什么必须数“新产生的错误”

$$
N_{\rm new}=|\mathcal V(G_{t+1})\setminus_m\mathcal V(G_t)|.
$$

$\mathcal V$ 是带身份的错误列表；$\setminus_m$ 表示按身份和重复次数取差。删掉一条悬空边后，可能留下一个孤立节点：错误总数没变，但新错误确实产生了。只比较总数会漏掉它。

### 三种惩罚在比较什么

$$
P_t^{\rm count}=0.01\sum_k n_{k,t},\qquad
P_t^{\rm rate}=\sum_k w_k\frac{n_{k,t}}{D_{k,0}},\qquad
P_t^{\rm zero}=0.
$$

$n_{k,t}$ 是第 $k$ 类新错误数，$w_k$ 是图分数中的权重，$D_{k,0}$ 是初始节点数或边数，至少为 1。

- count：每出现一个新结构错误，扣固定分。
- rate：结合原图大小扣分；大图中的一个重复项占比更小。
- zero：不加这项惩罚，作为对照。

分母固定为初始规模，不能靠删小图来改变扣分标准。旧 count 惩罚曾让模型不愿恢复正确关系，因为恢复过程可能暂时造成重复。rate 缓解了这个问题，但没有证明“所有安全问题都解决了”。

### 为什么系统还在意“早点修好”

训练考虑未来奖励，但越远的奖励权重越小，折扣因子 $\gamma=0.95$。令 $J_t=Q_G(G_t)+0.4Q_R(R_t)$，论文展开为：

$$
\sum_{t=0}^{T-1}\gamma^t(J_{t+1}-J_t)
=-J_0+\gamma^{T-1}J_T
+(1-\gamma)\sum_{t=1}^{T-1}\gamma^{t-1}J_t.
$$

不必逐项背下来。它的含义是：**不仅看最后好不好，也奖励中间阶段早点变好。** 只有 $\gamma=1$ 时才只剩起点与终点之差。

## 5. Double DQN：从反复尝试中学习选动作

**对应论文：**III-C 的 Reward and Double DQN，[methodology.tex](sections/methodology.tex)。

网络 $Q_\theta(o,a)$ 预测：“现在做动作 $a$，以后大概能拿到多少总奖励？”它不是图质量 $Q_G$，也不是动作概率。网络结构为 14→32→16→8，最后八个数分别评价八个动作。

Double DQN 用两个网络分工：在线网络挑选下一步，更新较慢的目标网络给这个选择估值。

$$
a^*=\arg\max_{a'\in\mathcal A_{t+1}}Q_\theta(o_{t+1},a'),
$$
$$
y_t=\begin{cases}
r_t,&\text{episode ends or no feasible action},\\
r_t+\gamma Q_{\theta^-}(o_{t+1},a^*),&\text{otherwise}.
\end{cases}
$$

$\arg\max$ 表示“挑分数最高的”；$\mathcal A_{t+1}$ 是下一步允许的动作；$\theta^-$ 表示目标网络。比如当前得到 0.1 分，下一步预计还有 0.2 分，则目标值是 $0.1+0.95\times0.2=0.29$。

训练让当前预测接近这个目标：

$$
\mathcal L=\mathbb E[\operatorname{Huber}(Q_\theta(o_t,a_t)-y_t)].
$$

$\mathbb E$ 可理解为取一批经验的平均。Huber 损失对小误差像平方扣分，对大误差改为较缓的线性扣分，避免个别大误差主导更新。

**算法步骤：**重置图 → 选动作 → 执行并拿到奖励 → 保存这一步经验 → 从旧经验中抽样训练 → 定期复制目标网络 → 开始下一轮。每个模型训练 250 回合，最多 18 步/回合，目标网络每 100 步更新。

训练初期多尝试随机动作，后期更多采用自己的预测。实际探索率按 260 回合衰减，因此第 250 回合结束时约为 0.0902，还没有降到设定下限 0.05。

## 6. Algorithms 1、2：两种方式提出规则

**对应论文：**III-D，[methodology.tex](sections/methodology.tex)，`alg:deletion_completion`、`alg:augmentation_expansion`；完整提示在附录 A。

|算法|怎样做|容易误解的地方|
|---|---|---|
|Algorithm 1：Deletion Completion|从原文删掉短片段，把原文、删改版和被删片段一起交给模型，提出规则|模型仍看到原文，不是盲猜缺失内容|
|Algorithm 2：Augmentation Expansion|让模型在一次响应中提出补充子句和规则候选|假设补充句不能当成真实来源证据；不是每补一句就额外调用一次|

两种候选集合记为 $R_D,R_A$：

$$
|R_D\cup R_A|=|R_D|+|R_A|-|R_D\cap R_A|.
$$

例如第一种提出 10 条、第二种 12 条，其中 4 条重复，合起来有 18 条。**合起来更多，可能只是因为调用了两次。** 要判断是否划算，还要在相同调用次数下比较，并检查这些候选能否真正执行。

## 7. 规则执行：提出一句话之后，还得能匹配到记录

**对应论文：**III-D 的 Rule Materialization；III-E Offline Generated-Rule Bridge，`sec:rule_bridge_method`。

一个类型规则可以写为：主体类型、关系、对象类型。例如“人物—任职于—组织”。匹配条件是：

$$
\operatorname{match}(r,x)=\mathbf1[
(\operatorname{type}(h_x),p_x,\operatorname{type}(o_x))=r].
$$

$x$ 是要检查的记录，$p_x$ 是它的关系。程序只在类型和关系能对上时使用这条规则，不自动猜类型或别名。

- allowed：这个类型组合被允许，不表示具体事实一定正确。
- forbidden：这个组合被禁止，可以触发检查。
- 同时允许与禁止：有冲突，先不删。
- 没有允许规则：不能自动理解为禁止。

桥接流程是：解析规则 → 获取指定规则包 → 找到匹配与冲突 → 删除无冲突的禁止项 → 重新检查。仅能执行的桥接接口还不是一个已经训练好的新 RL 策略。

## 8. DocRED 新环境：发现旧问题不该被当成制造新问题

**对应论文：**III-E 的 Response-level development environment；[docred_source_pilot.tex](sections/docred_source_pilot.tex)，附录 C-A。以下是实现奖励的详细展开。

新环境每次处理两篇文档，四个动作是：获取 deletion 响应、获取 augmentation 响应、修复、停止。最多获取四包、做十步，和前面的八动作环境不同。

记录还可以得到具体来源的 supported（支持）或 contradicted（矛盾）判断。类型许可不等于事实支持；明确来源支持与删除依据冲突时，程序弃权。

令 $T_A,T_F$ 分别表示类型允许/禁止，$S,C$ 分别表示来源支持/矛盾：

$$
\operatorname{Conflict}=(T_A\land T_F)\lor(S\land C)\lor(S\land T_F),
$$
$$
\operatorname{Violation}=\neg\operatorname{Conflict}\land
[C\lor(T_F\land\neg T_A\land\neg S)].
$$

$\lor$ 是“或者”，$\neg$ 是“不是”。这两行主要是在说：**有冲突先不删；没有冲突时，明确矛盾或未被支持抵消的类型禁止可以触发删除。**

新奖励比较修改前后的图时，固定使用同一套更新后的规则：

$$
\begin{aligned}
r_t={}&0.5[\Phi(g_{t+1};R_{t+1})-\Phi(g_t;R_{t+1})]\\
&+0.5[C(R_{t+1})-C(R_t)]-0.004a_t-0.00002d_t
-\frac{|V_{{\rm edit},t}|}{N}.
\end{aligned}
$$

这里 $N$ 是初始记录数（至少为 1）；$\Phi=1-\text{违规数}/N$；$C(R)$ 是原始记录被规则无冲突覆盖的比例；$a_t,d_t$ 是获取和删除数量；$V_{\rm edit}$ 只数修改新制造的违规。

想象刚拿到一把更好的尺子，发现桌子原来就歪了。这个问题不是尺子造成的。对应地，新增规则发现旧错误，不该被罚成“引入新错误”。

**仍有一个问题：**如果尺子本身错了，系统可能删掉正确记录并得到正奖励。当前删除操作不会让剩余记录出现新的局部违规，新违规惩罚可能一直为零；把零前面的系数调大不能纠正坏规则。

## 9. 规则准入：先核验，再允许策略获取

**对应论文：**III-E 的 Context-bound rule admission；附录 D-A，[appendix.tex](sections/appendix.tex)，`app:rule_admission`。本节公式是对文字机制的简写，自动核验效果尚未完成评估。

每个判断都绑定候选、原文、初始图、关系词表和生成响应。输入变了，旧批准就不能直接搬过来。

对一个类型候选，先找本对文档中所有匹配记录，再逐个判断。聚合规则很简单：任何一项拒绝就拒绝；每项都批准才批准；没有匹配或证据不足则不确定。

$$
a(r)=\begin{cases}
\mathrm{reject},&\text{any matching record is rejected},\\
\mathrm{approve},&\text{nonempty matches are all approved},\\
\mathrm{uncertain},&\text{otherwise}.
\end{cases}
$$

批准只是“可以使用”，还要等策略真正获取所属响应包才激活：

$$
R_t=\{r:\operatorname{grounded}(r)=1,\ a(r)=\mathrm{approve},\ p(r)\in A_t\}.
$$

$p(r)$ 是规则所属包，$A_t$ 是已经获取的包集合。核验器不能把没有获取的规则提前送给策略。

schema 与模型联合时，明确拒绝优先；没有拒绝时，任一有效批准可准入。本轮没有可靠的 schema 硬映射，因此 schema 全部是不确定。模型自动判断也不等于独立人工标签。

“引用能找到”只证明出处存在。原文没有说某件事，不能推出它说了这件事是假的。当前输入图只做删除；如果以后新增或改写记录，需要重新核验相关范围。

## 10. 实验的几个数学量该怎么读

**对应论文：**IV-B 的 Matched Policies and Measures、Inference；IV-D；附录 D、E。

**F1：**$F_T$ 是输出事实集合，$F^*$ 是参考集合：

$$
F1=\frac{2|F_T\cap F^*|}{|F_T|+|F^*|}.
$$

它同时考虑漏掉和多出的事实。关系恢复率更严格：原坏边必须还在，而且关系名修对；直接删除坏边不算恢复。

**过程 AUC：**

$$
\operatorname{AUC}_{18}=\frac1{18}\sum_{t=0}^{17}
\frac{\bar Q_t+\bar Q_{t+1}}2.
$$

可理解为 18 步里的平均过程质量；提前结束后用最后分数补齐。它不是分类任务的 ROC-AUC，也不是上面的 F1。

**Oracle：**把当前有限预算内所有可行动作顺序都试一遍，再用参考答案挑最高分：

$$
F_i^{\rm safe}=\max_{\tau:\operatorname{Preservation}_i(\tau)\ge0.99}F_i(\tau).
$$

$i$ 表示文档对，$\tau$ 表示一条操作顺序。它帮助判断“即便选得最好还有多少提升空间”，但用了答案，不能当作实际策略。

**统计单位：**RL 主比较先对每个种子的 30 个场景取平均，再比较 10 个种子；DocRED 用 10 个文档对。不能把所有重复回放都当独立样本。平均保留率先逐对算再平均，所以不一定等于把所有正确条目直接合并后的比例。

## 读完后应记住什么

Paper2 的 RL 是真实训练的；奖励和掩码会影响行为。但固定规则库上的学习结果，不能自动证明真实生成规则已经可靠。**当前最需要验证的是：好规则能否带来有用且互补的修复，随后再判断学习调度是否值得。**

对应数据和结论见 [实验导读](EXPERIMENTS.md)，当前状态见 [PROGRESS.md](PROGRESS.md)。自动核验的细节留在 [冻结协议](AUTOMATIC_RULE_REVIEW_PROTOCOL_2026-10-08.md)，需要时再查。
