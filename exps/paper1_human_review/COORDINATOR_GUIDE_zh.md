# Paper 1 真人标注说明（协调员版）

## 1. 发放与保密

把 `delivery/标注者_A.zip` 交给标注者 A，把 `delivery/标注者_B.zip` 交给标注者 B。每包有详细中文说明、离线 HTML 页面和 XLSX 表格。不要把整个仓库、另一人的文件、`coordinator/private_mapping.json` 或论文结果一起发给标注者。

两人应具备中文阅读能力，能区分发布机构、受理机构、日期、法规依据等字段。先用说明中的虚构例子理解规则，不要共同讨论正式样本。允许分批完成，不以快速完成或高一致率为目标。若需要补充一条通用规则，同步告知两人并记录版本；不要给某位标注者透露具体条目的正确答案。

本包沿用两个已冻结样本，各 200 条，没有替换难例或挑选正确修改：

- D：`paper1_submission_extensions/natural_error_annotation_sample.csv` 中的输入/参考差异。对外隐藏了 `system_reference_label`、`missing_gold_triple` 等暗示答案的字段，补上完整输入图谱与公开 schema。
- E：`paper1_mechanism_audit/human_review/` 中的真实操作。隐藏方法名及配置。来自五种配置共 598 个操作的简单随机样本。

公开样本 hash、原文件 hash 和交付 ZIP hash 见 `delivery/manifest.json`。原冻结文件保持不变。不要重新运行原抽样程序覆盖文件，也不要向旧文件填入编造的人工标签。

## 2. 收回文件

每位标注者交一份最终 JSON（页面导出）或 XLSX。请把文件放到自行建立的 `returns/` 目录并保留原件。例如：

```text
returns/paper1_annotator_A.json
returns/paper1_annotator_B.json
```

原始文件不要先行改成一致。合并脚本会检查版本、标注者身份（JSON）、400 个唯一 ID、任务范围、0/1/U 标签、0/U 的解释，以及 XLSX 中的原文/图谱字段未改。A/B 的两个标签必须全部完成；仍无法判断的填 U。JSON 仅收回标签和备注，来源内容由冻结包重建。

在仓库根目录运行（仅本地处理，不调用 API）：

```bash
python3 exps/paper1_human_review/process_returns.py merge \
  --a returns/paper1_annotator_A.json \
  --b returns/paper1_annotator_B.json \
  --out returns/merged
```

`--a`/`--b` 也支持 `.xlsx`。脚本拒绝覆盖已有输出目录。生成：

- `D_adjudication.csv`、`E_adjudication.csv`：独立标签、原文、图谱、操作、争议标记及空白裁决列；一致条目自动把相同标签复制到裁决列，原标签完整保留。
- `independent_agreement.json`：裁决前的一致率、Cohen's kappa、U 数量。
- `return_manifest.json`：两份返回文件的 SHA-256，以及每条独立标签和上下文的 hash。

如果校验失败，把缺项退回相应标注者。不要由协调员代填独立标签。

## 3. 裁决

裁决者阅读两个独立理由及原文，填写 `adjudicated_is_error`、`adjudicated_repair_acceptable`、`adjudication_notes`。可以由第三位熟悉任务的人承担；若由两位标注者讨论达成一致，应在论文中如实说明。

只修改裁决三列。对未决/矛盾条目保留 U，不强迫得到 0/1。原始独立标签及备注不改。两人一致的条目也可经检查作不同裁决，但需说明理由。不要查看方法身份后决定标签。

完成裁决后：

```bash
python3 exps/paper1_human_review/process_returns.py score --folder returns/merged
```

脚本重新核对独立字段，拒绝裁决列空白；输出 `human_results.json`、`per_configuration.csv` 和 `human_results.md`。原始一致率计算包含 U，裁决后可接受率只用非 U 条目，并单列 U 数量。全部同类时 kappa 无定义，输出 null，不解释为 1。

## 4. 论文应报告什么

分别报告 D 和 E 的样本量、抽样方式、标注者背景、是否先进行练习、独立流程、两项任务各自的一致率/kappa/U 比例、裁决人员和流程、裁决后的分子分母。E 还需报告每种方法实际抽到多少条，不能假设五种方法各 40 条。

D 估计“被自动参考判为差异的条目中，多少是实际错误”；E 估计“被抽中的操作有多少可接受”。两者都不是对所有图谱重新做完整标注，不能直接产出 human-validated whole-graph F1、全体缺陷召回率或总体系统准确率。抽样单位是操作/差异，同文档可能多条；如进一步做显著性检验，应按文档聚类，不能把重复文档当独立样本。

新增的 SROIE 实验使用公开数据提供的人工 KIE 标签，和本次两人独立复核是两件事。不能用公开数据存在人工标签来声称本次复核已经完成。

## 5. 完成后回填

将匿名化结果与本轮代码关联归档，保留返回原件和版本信息。收到真实文件前，论文应写“人工复核待完成”；不要填入一致率预估值。标签文件属于真实研究结果，收到后可再由助手运行上述校验、统计、更新论文和图表并提交推送。
