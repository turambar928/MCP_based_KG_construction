# 2026-10-02 离线投稿准备与闭环诊断

本轮模型 API 请求 0 次，新增训练模型 0 个。Paper1 对齐研究问题与已完成实验，Paper2 保持 RL + 双策略主线，检查现有候选能否支持下一步学习实验。

- [完整离线诊断报告](report_zh.md)、[逐回合结果](loop_diagnostics.json)。共 598 条终止路径，来自两轮共用的 20 个开发文档，而非新测试样本。
- [输出契约提案](proposed_output.schema.json)、[合成合法示例](synthetic_examples.json)、[提示说明草案](proposed_output_instructions.txt)、[原编译器重放核验](contract_audit.json)。未用于新生成，不修改原冻结提示或解析器。
- [人工回收接入说明](human_integration_zh.md)、[可选语义效果空表](human_effects_blank.csv)。原 A/B 标注包保持不变，未生成任何人工结果。
- [本轮投稿准备及剩余项](../../docs/submission_readiness_2026-10-02.md)。

## 复现

在仓库根目录、安装好 `jsonschema`、`openpyxl`、`markdown`、`scikit-learn` 等既有依赖的环境中运行：

```bash
python3 exps/papers_readiness_20261002/output_contract.py
python3 exps/papers_readiness_20261002/diagnose_loop.py
python3 exps/papers_readiness_20261002/publish.py
python3 -m unittest exps.papers_readiness_20261002.test_readiness \
  exps.paper2_docred_v2.test_contracts exps.paper2_docred_v2.test_replay \
  exps.paper2_docred_v2_round2.test_contracts exps.paper2_docred_v2_round2.test_replay
```

本机使用 `/tmp/kgbench-local-venv/bin/python`，合计 40 项测试通过。`publish.py` 只生成本目录报告和 Paper2 新增表格；其他上述脚本只写本目录，不改旧实验文件。

前两项需要原两轮目录中被 Git 忽略的 `local/pilot_public.json`、`local/pilot_scorer_only.json`，契约重放还需 `local/pilot_responses.jsonl`。已有本地档案可以直接运行；仅克隆公开仓库无法重放被排除的原文与原始响应。请依照原实验的数据来源和 manifest 恢复输入，勿为复现本次分析重新调用模型。可先审阅公开规则包、全路径文件和结果。引用偏移与原文核验仍依赖合法取得的原始输入。

## 解释范围

穷举保留原四包预算、十步上限、队列顺序、掩码、奖励与删空保护，不合并不同历史。参考标签仅用于枚举后的评分。可执行预言机是事后最佳可行动作序列；逐项删除上界进一步放宽编辑包约束；二者都不能当作实际可部署策略。

代理质量 AUC 使用初始状态及每步状态，停止后保持终态补齐到十步并采用梯形积分。它衡量既定代理质量，不是事实 F1 的时间积分。全部 80 条历史固定策略轨迹的最终评分、折扣奖励、删除记录与获取计数均已对齐；奖励最大化路径的并列 F1 范围也保留在 JSON。

第二轮最佳可行最终 F1 与先获取后修复相同（95.69%）。这只排除了在**该固定候选集上**通过换调度再提升最终 F1 的空间，未排除成本、时机或不同可靠规则下的学习收益。本次不启动第三轮、不放宽原门槛，也不扩大正式训练。
