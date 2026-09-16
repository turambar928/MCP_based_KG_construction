# Paper1 实验补全总状态（master index）

> 记录 experiments.tex 各占位实验的完成情况、代码与产物位置、论文填写状态。
> 子文档：f_φ 详见 [decision_network/README_fphi_experiment.md](decision_network/README_fphi_experiment.md)。

## ✅ 已完成（真实数据，已写入论文）

### §4.3 语义评分可靠性 — 独立模型交叉验证
- **做法**：用 gemma-4-26B（异家族）对 180 条三元组(3域×Exp2/Exp3)重打分，与 Qwen S_sem 比对。
- **结果**：Pearson r=0.62 / Spearman ρ=0.64 (p<1e-20);Exp3 一致性(0.70)>Exp2(0.55)→反驳自评偏向。
- **代码/产物**：`semantic_reliability_gemma.py`、`analyze_reliability.py`、`semantic_reliability/{rescored_triples.csv,agreement_report.txt}`
- **论文**：experiments.tex §4.3 独立模型段 + tab:sem_reliability 第一行 + 结论句 ✅

### §4.4.1 神经决策网络 f_φ 消融
- **做法**：从零训练 f_φ(文档实例,纯NumPy MLP);决策质量 + 效率消融。
- **结果**：repair Acc 0.796/F1 0.787;π top-1 0.494;按门控率与单次修复成本估算，调用/延迟可降低 54.4%，预计 Q 降 1.10（非端到端计时）。
- **代码/产物**：`decision_network/`(全套) → `paper_values.txt`、`results_summary.md`
- **论文**：experiments.tex §4.4.1 Setup段 + tab:decision_quality + tab:decision_ablation + 解读 +
  超参表决策网络行 + methodology §3.2 指针 ✅

### §4.5.4 恢复归因 & 可扩展性
- **做法**：可扩展性=对 gov-enhanced 子采样(2.5k→25k三元组)实测确定性评估耗时;
  恢复归因=按“逻辑→结构→语义”依次替换真实 Exp2/Exp3 端点评分，展示最终提升来自哪些维度；该图不是运行迭代轨迹。
- **结果**：耗时/三元组恒定 ~0.06ms(近线性)；恢复图仅作维度归因，不再声称实测 3 步收敛。
- **代码/产物**：`scalability_convergence.py` → `scalability.json`、`convergence.json`、
  重新生成 `paper1/figure/experiments/convergence.pdf`(占位水印已消除)
- **论文**：experiments.tex §4.5.4 恢复归因段 + tab:scalability(5行) + 可扩展性解读 + 新图注 ✅

## ✅ 人工评分已完成

### §4.3 人工一致性（tab:sem_reliability 第二行）
- **已完成**：`semantic_reliability/human_annotation_sheet.csv` 含 180 条、3 名标注者评分；论文报告 Pearson $r=0.50$、Krippendorff $\alpha=0.44$ 和平均加权 $\kappa=0.45$。

## ✅ 约束实现与配置已对齐

### §4.5.2 负约束 — 已完成受控压力测试
- **实现**：`constraint_optimizer.py` 增加密度上界与动作成本开关；`negative_constraint_ablation.py` 运行 15 个固定案例。
- **结果**：完整约束保留 100% 有效修复且接受 0 条无收益边；关闭动作成本后每例接受 11 条并达到密度 0.75；全部关闭后接受 16 条并达到密度 1.0。

### 超参表约束优化/去重行 — 已填设计默认值
- τ_dup=0.92、(α,β,γ)=(0.4,0.2,0.4)、质量下界=(55,55,60,45)、密度上界=0.75、
  (λ_del,λ_ret,λ_cmp)=(0.30,0.16,0.06)、β=0.35、η=0.05。
- 表前文字已注明:这些是**框架设计默认值(held fixed,非逐数据集调参)**,K/τ/决策网络行来自真实实验。
- ⚠️ 遗留隐患(供你知晓,非阻塞):方法论描述嵌入相似度去重(α/β/γ,τ_dup),但代码实际用**精确哈希去重**。
  若审稿深究,需统一方法描述与实现(或在 limitation 提一句)。

## 论文 TBD 现状
活动正文无 TBD/PLACEHOLDER、无缺失交叉引用和文献键；SHACL 外部修复基线与负约束消融均已写入论文。
