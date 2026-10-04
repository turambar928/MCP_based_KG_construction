# Paper1 人工回收接入与语义效果补充说明

最新状态（2026-10-04）：两位标注者各 400 条 JSON 已回收并通过原接入校验，D 76 条、E 78 条存在分歧，待真人裁决；未生成最终人工结果。见 [回收检查](../../paper1/HUMAN_RETURN_CHECK_2026-10-04.md)。下文为 10-02 原接入说明，可选语义效果表仍未完成，不由模型填写。

## 1. 原任务的回收顺序

保留 [原交付包及说明](../paper1_human_review/README.md)。每人独立填写 D 输入差异 200 条、E 实际修改 200 条。收到两份真实 JSON 或 XLSX 后，在仓库根目录执行：

```bash
python3 exps/paper1_human_review/process_returns.py merge \
  --a returns/paper1_annotator_A.json \
  --b returns/paper1_annotator_B.json \
  --out returns/merged
# 由真人完成分歧裁决列后：
python3 exps/paper1_human_review/process_returns.py score --folder returns/merged
```

完成文件放在独立 `returns/` 目录，不覆盖 `delivery/` 模板。先保存原始独立标签，再计算一致性，然后裁决。原程序拒绝空标签、重复/错误 ID、身份或版本不符，以及需要理由但未填的情况；裁决评分还检查原始标签与上下文未被改写。一致性按裁决前 0/1/U 计算，报告分母、未知和退化情况，不用裁决后的标签提高一致性。

## 2. 为什么另有可选空表

原包包含 `is_error` 和 `repair_acceptable`，它们不能唯一推出“纯格式变化”。例如 `0/1` 还可能是语义等价的替代写法。若论文要分别报告修对、改坏和纯格式变化，需要真人明确判断；不应从原两列自动猜测。

[human_effects_blank.csv](human_effects_blank.csv) 仅列出原 E 任务的 200 个冻结 ID，所有判断列均为空。它是**可选的后续补充任务**，不改变原 A/B 任务，也不把未填写状态视为没有误修。协调员应利用原包中的来源、修改前后值和操作上下文，另存填好的副本。若希望报告这项新分类的一致性，需要两人分别判断并另行计算一致性；单份补充表只能报告相应人工复核计数。

| `semantic_effect` | 定义与边界 |
|---|---|
| `repaired` | 编辑前存在语义/事实错误，编辑后已修正，且未同时引入新的语义错误。仅因严格字符串评分变化不能判此类。 |
| `harmed` | 编辑使原正确事实错误或丢失，或引入新的错误；若同时有修对和损害，归此类并说明两者。 |
| `format_only` | 事实含义前后相同，差异仅在空格、大小写、标点等表示层面。须由人确认等义。 |
| `ineffective` | 原语义错误仍未解决，且未产生可确认的新损害。 |
| `other_acceptable` | 有可接受的等价表述或其他合理变化，但不属于纯格式变化；说明依据。 |
| `uncertain` | 来源不足、含义有歧义或不能可靠判定；明确写出原因，不强行归类。 |

每项都须填写 `evidence_notes`，说明来源与判断依据。分类只针对冻结的具体操作；不能外推为整图人工 F1。

```bash
# 只有需要额外空白副本时执行；拒绝覆盖已有文件。
python3 exps/papers_readiness_20261002/human_effects.py template returns/effects_blank.csv
# 全部 200 项经真人判断并附依据后执行；空表/部分表会被拒绝。
python3 exps/papers_readiness_20261002/human_effects.py score returns/effects_completed.csv
```

本轮合成测试仅验证读入边界，没有产生人类一致性系数或语义修复率。Paper2 的独立规则/编辑审查仍未安排，本文件不能替代该项工作。
