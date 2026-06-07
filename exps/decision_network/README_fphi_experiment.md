# 决策网络 f_φ 实验文档（paper1 §4.4.1）

> 本文档汇总：实验目的、方案、代码位置、结果、如何查看、以及结果在论文中如何撰写。
> 自动生成的最终数值见同目录 [`results_summary.md`](results_summary.md) 与 [`paper_values.txt`](paper_values.txt)。

---

## 1. 这个实验解决什么问题

论文方法论 §3.2《Neural Repair Decision Network》完整定义了一个网络 **f_φ**：
输入质量状态向量 **s**=(S_iso, S_red, S_log, S_sem) + 图统计 **g**，输出
(i) 修复触发概率 `p_repair`，(ii) 尺度先验 **π**∈{entity, graph, context}；
用约束检查器自动派生标签训练（Eq. repair_label / scale_label），损失 = BCE + λ·CE。

**问题**：方法里写了一整节 f_φ，但**代码里零实现**（`grep p_repair/scale_prior/decision_net` 无命中），
实验 §4.4.1 全是 TBD 占位符。审稿人必抓这个“方法-实验脱节”。
本实验**从零训练 f_φ**，补齐 §4.4.1 的三块交付物：训练细节、决策质量表、效率消融表。

---

## 2. 方案（关键设计决策）

### 2.1 实例 = 文档（document）
- 起初尝试“k-hop 子图 over 抽取后的 CSV”——**失败**：CSV 丢了 `node_type`（全 Unknown，
  导致类型冲突规则失效，S_log 恒=100）且冗余在 clean/dirty 里都很高，状态向量无法区分好坏。
- 最终方案：**每个 jsonl 记录 = 一个实例**。原始 jsonl（`政务.jsonl` 等 clean、`政务_低质量.jsonl`
  等 dirty）每条记录自带：
  - 结构化字段（服务事项/权力类型/行驶主体/承办机构/实施依据/责任事项…）
  - dirty 记录额外有 `引入问题`（注入缺陷清单，如 `["层级冲突制造","术语错误"]`）

### 2.2 特征（状态向量 s + 图统计 g）
每条记录用字段建一个**带类型的小图**，确定性检测器算 3 个结构维度 + LLM 算语义维度：
| 维度 | 算法 | 主要捕获的缺陷 |
|---|---|---|
| S_iso | 缺失必填字段率 | 字段缺失 / 孤立节点 |
| S_red | 重复三元组/对象 + 责任事项内重复句子 | 重复三元组 / 冗余信息 |
| S_log | 行政层级反转(行驶主体 vs 承办机构) + 权威作为违法主体 + 类型错误 | 层级冲突 / 关系错误 |
| S_sem | **LLM 打分**（gemma-4-26B，0-1，按域 prompt） | 术语错误 / 信息不一致 / 语义颠倒 |
- g = (|V|, |E|, density, n_violations)。

### 2.3 标签（自监督，无人工标注）
- `y_repair` = 1（dirty 记录有注入缺陷）/ 0（clean 记录）——**天然平衡**。
- `y_scale` = 由 `引入问题` 按下表映射到尺度后取主导尺度：
  - entity ← 重复三元组制造/冗余信息/孤立节点制造/字段缺失
  - graph ← 层级冲突制造/逻辑矛盾/关系错误/实体类型错误
  - context ← 术语错误/信息不一致/格式错误

### 2.4 网络与训练
- **纯 NumPy MLP**：8→32→16→双头(1·sigmoid p_repair + 3·softmax π)，ReLU，Adam，BCE+λ·CE(λ=1)，
  早停。（刻意不用 PyTorch——本机 CUDA 依赖环境损坏，纯 NumPy 自包含、可复现。）
- 70/15/15 按 (domain, y_repair) 分层划分，seed=42。π 的 CE 项只在有缺陷的样本上计算（mask）。

---

## 3. 代码文件位置（全部在 `exps/decision_network/`）

| 文件 | 作用 |
|---|---|
| [`build_dataset.py`](build_dataset.py) | 解析 jsonl → 每文档建图 → 确定性 S_iso/S_red/S_log + g + 标签 → `dataset.csv` + `triples_cache.jsonl` |
| [`score_semantics.py`](score_semantics.py) | 对每文档三元组用 gemma 打语义分 → 填 `dataset.csv` 的 S_sem（断点续传到 `sem_scores.csv`） |
| [`merge_scores.py`](merge_scores.py) | 安全合并：从 `sem_scores.csv` 把 S_sem 灌回 `dataset.csv`（幂等） |
| [`train_fphi.py`](train_fphi.py) | 训练 f_φ → `fphi_model.npz`、`scaler.json`、`splits.json`、`train_meta.json` |
| [`write_efficiency_cost.py`](write_efficiency_cost.py) | 写 `efficiency_real.json`（每次修复的真实成本常数，锚定论文已测数值） |
| [`eval_fphi.py`](eval_fphi.py) | 决策质量(Acc/F1 + π top-1) + 效率消融 → `decision_quality.json`、`efficiency_sim.json` |
| [`summarize_results.py`](summarize_results.py) | 汇总三个 json → `results_summary.md` + `paper_values.txt`（论文可直接抄的数值） |
| [`run_pipeline.sh`](run_pipeline.sh) | **后台编排**：等打分完成 → merge → train → cost → eval → summarize |

产物文件（运行后生成）：`dataset.csv`、`sem_scores.csv`、`fphi_model.npz`、`*_quality.json`、
`efficiency_sim.json`、`results_summary.md`、`paper_values.txt`、`pipeline.log`、`sem_run.log`。

---

## 4. 如何运行 / 如何查看结果

### 复现全流程
```bash
cd /home/taozifu2025/MCP_based_KG_construction && source .venv/bin/activate
python3 exps/decision_network/build_dataset.py       # 建数据集（无需 LLM，~秒级）
python3 exps/decision_network/score_semantics.py     # 填 S_sem（gemma，~30-40min，可续传）
bash    exps/decision_network/run_pipeline.sh         # 等打分→训练→评测→汇总
```

### 查看结果
- **最终数值**：`cat exps/decision_network/results_summary.md` 和 `paper_values.txt`
- **后台进度**：`tail -f exps/decision_network/pipeline.log`（编排）/ `sem_run.log`（打分）
- **原始 json**：`decision_quality.json`、`efficiency_sim.json`、`train_meta.json`
- **数据集**：`dataset.csv`（每行一个文档实例，含特征+标签）

---

## 5. 实验结果

> ⚠️ 下表为 **S_sem 部分完成(~252/2900)时的预览**，最终结果由后台 `run_pipeline.sh` 在
> 全量 S_sem 完成后写入 [`results_summary.md`](results_summary.md) / [`paper_values.txt`](paper_values.txt)。

**决策质量（test 集）**
- 修复触发 p_repair（τ=0.75）：Accuracy ≈ **0.84**，F1 ≈ **0.81**，Precision ≈ **0.99**，Recall ≈ 0.68
- 尺度先验 π top-1 ≈ **0.50**（3 类随机基线 0.33），macro-F1 ≈ 0.38

**效率消融（完整 vs 去掉 f_φ）**
| 配置 | Q 损失 | LLM 调用/文档 | 延迟/文档 |
|---|---|---|---|
| 去掉决策网络（无条件全修复） | 0 | 1.0 | 2.8 s |
| 完整（带 f_φ 门控） | ~1.4 | ~0.34 | ~0.96 s |
- f_φ 只把 ~34% 文档送去修复 → **节省 ~66% LLM 调用与延迟**，Q 仅降 ~1.4 分。

---

## 6. 结果在论文中如何撰写（paper1 §4.4.1）

目标文件：[`paper1/sections/experiments.tex`](../../paper1/sections/experiments.tex)

1. **`\paragraph{Setup.}`（约 L293）**——填训练细节（抄 `train_meta.json` / `paper_values.txt`）：
   网络结构 `8→32→16→(1 sigmoid + 3 softmax)`、参数量、样本量(train/val/test)、Adam、
   70/15/15 分层划分；保留“监督信号由约束检查器自动派生、无需人工标注”一句。

2. **`tab:decision_quality`（约 L297）**——填 `decision_quality.json`：
   `Repair trigger p_repair` 行 = Accuracy/F1；`Scale-prior π (top-1)` 行 = scale_top1 / macro-F1。

3. **`tab:decision_ablation`（约 L314）**——填 `efficiency_sim.json`：
   两行 Q_score / calls-per-doc / latency-per-doc。**注脚说明**：每次修复成本锚定论文
   `tab:websearch_ablation` 实测的 2.8 s/doc（no-search）与管线 ~1 LLM 调用/doc；
   门控比例由 f_φ 在 test 集的预测实测得到 → 二者相乘即本表（“实测成本 × 实测门控比例”）。

4. **解读句（约 L329）**：f_φ 在几乎不损失 Q（约 -1.4）的前提下削减约 2/3 的 LLM 调用与延迟，
   其价值在效率而非精度——与方法论“soft prior、效率优化”的定位一致。

5. **顺带回填 `tab:hyperparams` 的决策网络行**：`τ_repair`（=eval 选出的值）、`λ`=1.0、
   `θ_Q`=80、`η`/`ε`（方法中的 soft-prior 强度/数值稳定常数，给出所用值）。

6. **`methodology.tex` §3.2** 末尾加一句：指向 §4.4.1 给出 f_φ 的具体结构与训练设置。

### 诚实表述（务必写进论文，别粉饰）
- f_φ 的修复决策**主要由 S_sem 与 S_iso 驱动**；S_red/S_log 在单文档字段层面信号弱
  （冗余/层级缺陷主要存在于抽取后的图层面）。这与退化剖面一致，应如实说明。
- π top-1≈0.5 属**中等**：entity 尺度可分性最好，graph/context 受限于确定性检测器能力——
  定位为“组件级可改进项”，非架构缺陷。
- S_sem 特征用 gemma-4-26B 计算（因 Qwen 端点当时被限流）；它是 f_φ 的**输入特征**，
  非论文上报的 S_sem 指标，不影响其它实验。

---

## 6½. 这个结果意味着什么、有什么影响（重要，先读这段）

**一句话结论**：核心交付物（效率门控）很稳；受影响的只是一个"软提示"指标 π，而它在方法论里
本就被定位为"软偏置、不影响正确性"——所以影响有限，关键是论文里怎么表述。

### (a)「S_red/S_log 信号弱」是什么意思
状态向量 4 维里：**S_iso（字段缺失）和 S_sem（LLM 语义）** 能清楚区分干净 vs 退化文档；
**S_red（冗余）和 S_log（层级冲突）** 在单文档字段层面几乎区分不出好坏。
**根因**：冗余/层级缺陷是注入在**抽取后的图层面/跨文档**的，而我从**单条文档的结构化字段**
计算这两维时信号不在那里。这是**特征计算口径**问题，不是 f_φ 网络架构缺陷。

### (b)「π top-1 中等」是什么意思
π 预测"缺陷属于 entity/graph/context 哪个尺度"，top-1≈0.50（3 类瞎猜=0.33）。要判 graph 尺度
得靠 S_log 发力，但 S_log 不发力 → 能认出 entity(靠 S_iso)和 context(靠 S_sem)，分不清 graph，故中等。

### (c) 影响分三块
| 受影响对象 | 程度 | 说明 |
|---|---|---|
| **p_repair（修不修）** | ✅ 几乎无影响 | Acc 0.84/F1 0.81/精确率 0.99，靠 S_sem+S_iso 就够；效率消融"省 ~66% 调用"成立 |
| **π（修哪个尺度）** | ⚠️ 中等，被影响的地方 | top-1 0.5，不强 |
| **论文整体主张** | ✅ 基本不受损 | 见下 |

**为何论文主张基本不受损**：方法论 §3.2 把 π 定位为 *"a soft bias rather than a hard gate"*
（Eq. routing_bias: ũ = u + η·log(π)）。π 只给修复优先级加软提示，真正保证正确性的是后续
**约束优化器（硬约束检查）兜底**。所以 π 中等也不会修错——与方法论设定自洽。
而真正要卖的价值点（**效率门控**：挡掉 ~66% 无需修的文档、Q 仅降 1.4）证据很硬。

### (d) 对审稿的影响 & 选择
- **好处**：哪怕 π 中等，也远胜于 §4.4.1 留 TBD 占位符（方法写了整节网络却零实验 = 拒稿级硬伤）。
- **风险**：审稿人可能注意到 π top-1=0.5 偏低并追问——**有诚实解释（软提示+约束兜底）即可化解**；
  真正危险的是反过来吹 π 很准。所以"如实标注"是保护，不是拖后腿。
- **三个选项（建议 A）**：
  - **A. 如实报告（推荐）**：f_φ 价值写成**效率门控**（强证据），π 写成"软先验、正确性由约束优化器保证"，
    "S_red/S_log 文档级信号弱"作为 limitation 一句带过。诚实、自洽、省事。
  - **B. 增强 S_red/S_log 特征**：对每文档跑真实 KG 抽取(走 MCP，贵且端点限流)，在子图上算两维 → π 或可升。
    工作量大、回报不确定，不建议现在做。
  - **C. 弱化 π 篇幅**：主推 p_repair 那张表，π 一句带过，降低暴露面。

> **本质**：这不是"实验失败"，而是"实验诚实地告诉你 f_φ 的强项在效率、弱项在尺度细分"，
> 而后者恰被方法论设计成无关紧要(软提示)。按 A 写反而显得工作严谨。全量 S_sem 出来后数字会再稳，
> 定性结论不变。

---

## 7. 局限 / 注意
- 标签来自“注入缺陷 provenance”，是 Eq. repair_label 的一种合法自监督实现；`引入问题` 仅作标签，
  不作为特征，避免循环。
- 效率表是“实测每修复成本 × 实测门控比例”，非端到端重跑整条增强管线（端点限流 + MCP 服务较脆）。
  若日后端点空闲，可用 `bulk_jsonl_to_csv_enhanced.py` 跑端到端做进一步验证。
- 金融/环境图谱小，gov 主导数据集；per-domain 决策质量对 fin/env 不宜过度解读。

---

## 8. 当前状态
- ✅ build_dataset / train / eval / summarize 全链路已跑通（partial 数据验证无误）
- 🔄 S_sem 打分后台运行中（`sem_run.log`），完成后 `run_pipeline.sh` 自动训练+评测+汇总
- ⏭ 待人工：把 `paper_values.txt` 的数值填进 `experiments.tex` §4.4.1（见第 6 节）
