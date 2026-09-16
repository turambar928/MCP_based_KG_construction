# 决策网络 `f_phi` 实验（投稿版）

该实验只验证论文中的 repair trigger 和 scale prior 已实现，并能学习受控 benchmark 的缺陷映射。它不用于宣称自然缺陷上的泛化性能。

## 数据与防泄漏

数据由 `exps/paper1_repair_benchmark/benchmark.jsonl` 生成：1,499 个源文档，每个生成一行 clean 和一行 dirty，共 2,998 行。源文档在污染前已经按组分配到 train/validation/test，因此 clean/dirty 对不会跨集合。

- train：2,098 行；
- validation：450 行；
- test：450 行；
- UID 交集：0；
- seed：42。

标签来自注入 provenance：dirty 行的 `y_repair=1`，缺陷类型映射到 entity / graph / context scale。标签不作为输入特征。

## 模型

NumPy MLP：`8 -> 32 -> 16 -> (1 sigmoid repair head + 3 softmax scale head)`，884 个参数。优化器 Adam，学习率 0.005；损失为 BCE + masked cross entropy，`lambda=1.0`。

## 结果

- repair trigger：Accuracy = 1.000，F1 = 1.000；
- scale prior：top-1 = 1.000，macro-F1 = 1.000；
- 测试集 clean/dirty 平衡，门控路由 50% 输入；
- 主 repair benchmark 实测 Ours 成本为 1 call、11.445 s / repaired document；
- 投影后门控成本为 0.5 call、5.722 s / input，未漏掉受控缺陷。

这些数字是受控缺陷映射 sanity check。效率是“实测单次修复成本 × 实测门控比例”的投影，不是第二次端到端计时。

## 复现

```bash
python3 exps/decision_network/build_from_repair_benchmark.py
python3 exps/decision_network/train_fphi.py
python3 exps/decision_network/write_efficiency_cost.py
python3 exps/decision_network/eval_fphi.py
python3 exps/decision_network/summarize_results.py
```

关键产物：`dataset_meta.json`、`splits.json`、`train_meta.json`、`decision_quality.json`、`efficiency_real.json`、`efficiency_sim.json`、`results_summary.md`。
