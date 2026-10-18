# 实验索引

实验代码、冻结协议、模型输出、检查日志和评分结果保留原目录。先从下列入口寻找论文当前使用的结果，各目录中的 README 记录复现命令。

| Paper1 | 内容 |
|---|---|
| [paper1_repair_benchmark/](paper1_repair_benchmark/README.md) | 中文记录的受控缺陷和模型抽取输出 |
| [paper1_mechanism_audit/](paper1_mechanism_audit/README.md) | 组件、门控、诊断和编辑选择对照 |
| [paper1_receipt_followup/](paper1_receipt_followup/README.md) | 新收据主测试及后续对照 |
| [paper1_cuad/](paper1_cuad/README.md) | 合同迁移测试 |
| [paper1_human_review/](paper1_human_review/README.md)、[人工回收](paper1_human_returns_20261004/README.md) | 人工评价和裁决 |
| [math_revision_20260925/](math_revision_20260925/README.md) | 数学修订、路由器及相关重放 |

| Paper2 | 内容 |
|---|---|
| [paper2_reward_validation/](paper2_reward_validation/README.md) | 奖励与主策略比较 |
| [paper2_rate_ablation/](paper2_rate_ablation/README.md) | rate 奖励消融 |
| [paper2_rule_integration/](paper2_rule_integration/README.md) | 规则执行与覆盖 |
| [paper2_rule_feasibility_20261004/](paper2_rule_feasibility_20261004/README.md) | 新文档规则执行 |
| [paper2_rule_admission_20261004/](paper2_rule_admission_20261004/README.md) | 规则准入 |
| [paper2_rule_verification_20261008/](paper2_rule_verification_20261008/README.md) | 冻结的自动核验测试 |

其他目录保留各次实验和早期比较。论文到结果的完整映射见 [Paper1 实验导读](<../paper1 merge/docs/guides/EXPERIMENTS.md>)、[Paper2 实验导读](../paper2/docs/guides/EXPERIMENTS.md)和 [Paper2 复现说明](../docs/paper2_experiment_reproducibility.md)。

历史 `write_paper.py`、`publish.py` 等脚本可能会写入合并前的 `paper1/`。需要复现历史发布过程时先把归档解压到单独目录；当前论文的交付使用各论文 `tools/`。本次整理没有执行训练、实验或模型请求。
