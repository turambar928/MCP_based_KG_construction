# Paper 1 真人标注交付包

当前状态：**等待两位真实人员标注；无 AI 代填标签。**

- 给 A：[标注者_A.zip](delivery/标注者_A.zip)
- 给 B：[标注者_B.zip](delivery/标注者_B.zip)
- 协调员自留：[协调员.zip](delivery/协调员.zip)
- [标注者详细中文说明](ANNOTATOR_GUIDE_zh.md)
- [协调员发放、合并、裁决、统计说明](COORDINATOR_GUIDE_zh.md)

每位标注者的 ZIP 包含离线 HTML 页面、可填写 XLSX 和详细说明。每人独立完成 D 输入差异 200 条、E 实际修改 200 条。页面支持自动本地保存、筛选未完成项、导入/导出 JSON。建议每次休息前导出备份。两项任务、两位标注者分别统计与管理。

不要将协调员包发给标注者。对外材料隐藏方法、参考判定以及他人标签，保留来源、公开字段、输入图谱及当前操作。原冻结 CSV 和样本 hash 保持不变。

## 在仓库根目录操作

```bash
# 如需重新构建交付模板；不会修改原冻结样本，但会覆盖 delivery 模板。
python3 exps/paper1_human_review/build_package.py

# 收到真实完成文件后执行；不要将完成文件存入 delivery。
python3 exps/paper1_human_review/process_returns.py merge \
  --a returns/paper1_annotator_A.json \
  --b returns/paper1_annotator_B.json \
  --out returns/merged

# 完成裁决列后执行。
python3 exps/paper1_human_review/process_returns.py score --folder returns/merged
```

依赖：Python、openpyxl、Markdown、scikit-learn，以及仓库原有分析环境。HTML 页面填写不需要 Python、账号、网络或模型 API。JSON 和 XLSX 均可交回，选择一份作为正式结果。

合并拒绝未完成标签、身份/ID 错误、0/U 缺少说明；裁决评分拒绝独立标签或原始上下文被改动。kappa 基于裁决前的 0/1/U；退化情况为 null。结果按任务和方法列出实际分母。样本估计的是差异或操作的人工判断，不能当作整图人工 F1。
