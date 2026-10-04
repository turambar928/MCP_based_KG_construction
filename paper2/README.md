# Paper 2: TKDE submission source

## 下一步实验协议（2026-10-04）

[完整协议与操作说明](NEXT_EXPERIMENT_PROTOCOL.md)已放在本目录。已冻结新的 20 个开发文档、40 个 Gemma 请求体，并完成采集、断点恢复、固定策略比较和验收脚本；34 项离线测试通过。实际请求 0 次、训练 0 次。旧两轮实验及正式训练阻断保留。此轮没有修改正文或模板，无需再次替换 Overleaf sections。

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
