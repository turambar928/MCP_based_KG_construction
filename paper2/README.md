# Paper 2: TKDE submission source

当前总览：[进度与下一步（2026-10-08）](PROGRESS.md)。以该文档区分当前任务和下方历史记录。

## 2026-10-08：自动核验协议与离线部分完成

- 已完成上下文绑定的自动核验接口、38 个请求冻结、40 关系 schema 覆盖审计、51 项新旧测试；无可靠硬映射，不从关系名称推断禁止。
- Qwen 实际请求 **1 次**，HTTP 200；请求 `Qwen3.8-27B-no-thinking`，返回 `Qwen/Qwen3.8-27B`，触发模型身份停止条件。0 重试，37 任务未派发；并非服务完全不可达。没有调用 GPT/Claude。
- 三组离线比较共 **240 回放、764 终止路径**，原 80 轨迹一致。出处检查 F1 96.63%、17 修复/4 参考损失；空独立核验与无映射 schema 均 F1 94.02%、0 修复/0 损失。
- automatic/combined **未评估**，不能把接口测试或空判断视为自动核验实验；新训练与人工标签均为 0。
- 下一步：取得平台模型别名及 no-thinking 配置的可核实说明，再另登记身份契约版本修订；不改当前冻结协议、不自动继续请求。实际核验结果就绪后才判断互补与调度空间。

详见 [冻结协议](AUTOMATIC_RULE_REVIEW_PROTOCOL_2026-10-08.md)、[结果与恢复条件](AUTOMATIC_RULE_REVIEW_RESULTS_2026-10-08.md)。以下 10-04 及更早记录为历史状态。


## 规则准入与主实验定位（2026-10-04）

[校验层实现与离线结果](RULE_ADMISSION_RESULTS_2026-10-04.md)已完成：240 回放、27 测试，未调用 API。缺少独立核验依据时 407 候选全部隔离，避免参考损失也失去全部修复；尚未建立语义校验效果，不启动新训练。[主实验与 benchmark 说明](BENCHMARK_GUIDE.md)区分 TNEWS 自定义受控主实验、DocRED 开发验证、生成档案和 RuleTest。本轮无正文或模板修改，不需要替换 Overleaf sections。


## 论文导读（2026-10-08）

- [数学导读：逐节对应论文，含例子和公式](MATHEMATICS.md)
- [实验导读：逐节对应设计、结果和结论](EXPERIMENTS.md)

以上文档已接入最新结果；历史审计与旧实验版本按原档案保留。

## 下一步实验协议（2026-10-04）

后续[四条参考损失审计](RULE_FAILURE_AUDIT_2026-10-04.md)已完成：2 条宽类型禁止、2 条来源矛盾语义缺口；320 次离线屏蔽回放及 5 项测试完成，额外 API 请求 0 次。下一步需要可信的规则校验依据，尚无经验证的自动语义修复器；旧扩训门槛不变。本次新增论文内容仅在 `sections/appendix.tex`，没有增加外部依赖或修改模板。

[完整协议与操作说明](NEXT_EXPERIMENT_PROTOCOL.md)和[执行结果](RULE_FEASIBILITY_RESULTS_2026-10-04.md)放在本目录。新的 20 个开发文档已完成 40 次 Gemma 请求，无运输失败／重试；39 个输出格式合格。完整流程 F1 为 96.63%，但损失 4 条参考事实、augmentation 独有移除为 0，扩训门槛未通过，未启动训练。结果已同步到 experiments、appendix、conclusion 三份 sections 文件；新表内嵌 appendix，无新增外部依赖，模板未改。34 项离线测试和旧结果保留。

## 文件交付约定（2026-10-04）

以后以本论文目录作为完整、最新的 Overleaf 内容交付入口。每次修改将正文、附录、引用的表格、图片和参考文献同步放在本目录的对应位置，检查依赖并验证编译，再 commit / push。不要要求作者从 `exports/`、`docs/` 或多个局部更新包中拼接论文所需文件。

上传时保持目录结构，项目主文件选择 `main.tex`。论文编译所需的项目文件必须留在本目录内；实验原始数据和代码可以在仓库其他位置，但不应成为 Overleaf 编译依赖。已完成旧更新包只作为历史档案，不作为今后的默认交付入口。

作者已在 Overleaf 调整 TKDE 格式；该云端新版模板尚未同步到本目录。内容修订不能覆盖作者的模板设置。当前同步到既有 Overleaf 项目时保留作者的 `main.tex` 和模板文件；后续取得云端版本后再以其作为本目录的模板基准。

Remaining submission work is tracked in [TODO.md](TODO.md).

The active manuscript is `main.tex`, now formatted with `IEEEtran`. It describes an executable Double-DQN co-optimization benchmark and separates three types of evidence:

1. actual graph-state transitions for sequential graph/rule control;
2. stored LLM candidate logs for deletion/augmentation contribution;
3. designed executable cases for rule-family coverage.

The old heuristic look-ahead simulator is not used as RL evidence. Unsupported exploratory cross-domain and rule-mining result tables have been removed from the active manuscript.

Build from this directory with:

```bash
tectonic -X compile main.tex --only-cached --keep-logs
```

The latest compiled manuscript is `main.pdf`. Experiment commands and all output mappings are documented in `../docs/paper2_experiment_reproducibility.md`.

Key result directories:

- `../exps/paper2_cooptimization/`
- `../exps/paper2_dual_strategy_ablation/`
- `../exps/paper2_rule_family_ablation/`
- `../exps/external_benchmark/`
- `../exps/api_llm_extraction_benchmark/`
- `../exps/shacl_baseline/`

## Offline revision (2026-09-24)

The title and RL/dual-strategy main line are retained. The earlier comparisons use
feasible-action baselines, a strong acquire-then-deficit heuristic, and forty
retrained ablation models. The generation analysis adds equal-call comparisons
and directly compiled typed-rule execution with source provenance.

The strong heuristic slightly outperforms Double DQN in that controlled
environment. The hand-implemented family union and actual generated-rule
execution are separate results. Connecting validated generated rules to the RL
registry remains a required next experiment.

- Results and revision summary: `../exps/paper2_offline_revision/report_zh.md`
- One-command offline reproduction: `python3 exps/paper2_offline_revision/reproduce.py`
- Source/code/evidence audit: `../exps/paper2_offline_revision/claim_evidence_audit.md`

## Mathematical revision (2026-09-25)

The corrected environment and new training results are under
`../exps/math_revision_20260925/`. It counts newly introduced violations by
identity and records every reward component. A separate government-typed
archive bridge demonstrates rule activation and constraint-removal decisions.
See `../docs/math_revision_2026-09-25.md` for changes and remaining evidence.

## Reward and repair-behavior validation (2026-09-25; active policy comparison)

The latest study compares three fixed introduced-violation penalties and a
public-observation one-step ridge baseline. It trains 40 neural models plus
10 ridge fits, keeps development and reserved corruption scenarios separate,
and evaluates reference-triple F1, occurrence-level relation restoration,
correct-fact preservation, structural violations and common-reward return.

- Protocol and reproduction: [experiment README](../exps/paper2_reward_validation/README.md)
- Full results and interpretation: [Chinese report](../exps/paper2_reward_validation/report_zh.md)
- Reconstructed-trajectory checks: [verification.json](../exps/paper2_reward_validation/verification.json)
- Current manuscript: [main.pdf](main.pdf)

The main policy tables use the new reserved test. The earlier four component
ablations remain in the appendix under their original count penalty; they were
not retrained under the rate penalty. The new test uses unseen corruptions of
the same base graph. Generated-rule integration, natural errors and new domains
remain separate work in TODO.md.

## Archive-rule interface and coverage audit (2026-09-28)

The independent four-command adapter supports public-observation schedules over
archived deletion/augmentation rule banks. Sixteen replays cover two acquisition
orders and immediate/deferred removal on four inputs. RuleTest-94 gives identical
final records across schedules; the three original CSV graphs lack entity types.
This is a mechanism and coverage audit, not a new trained-policy comparison.

- [Results](../exps/paper2_rule_integration/report_zh.md)
- [Interface, commands and artifacts](../exps/paper2_rule_integration/README.md)

Trusted entity types and useful rule coverage are prerequisites for the next
learned-scheduling experiment. The existing eight-action environment is unchanged.
