# Paper 2: TKDE submission source

当前总览：[进度与下一步（2026-10-10）](PROGRESS.md)。以该文档区分当前任务和下方历史记录。

## 最新完整 Overleaf 项目（2026-10-10）

- [下载完整 ZIP](paper2_overleaf.zip)：在 Overleaf 选择 Upload Project 上传。
- [干净项目文件夹](overleaf/)：只含编译所需文件、字体、说明和论文 PDF。
- 主文件：`main.tex`；编译器：**XeLaTeX**。无需从其他目录拼接文件。

`sections/` 已从 12 个文件整理为 7 个：摘要、引言、相关工作、方法、实验、结论、附录。实验小文件和表格已并入所属章节，章节文件不再引用其他 TeX 文件。项目不需要 `tables/`。根目录的 `tables/` 保留为表格生成档案，整理前章节保存在 `archive/before_overleaf_cleanup_2026-10-10/`。

正文、公式、数值、章节顺序和匿名作者信息保持原样。正文优先使用 Times New Roman；缺少时自动使用项目内的 TeX Gyre Termes。验证见 [整理验证](OVERLEAF_VALIDATION_2026-10-10.json)。以后默认交付 `overleaf/` 和 `paper2_overleaf.zip`。

## 当前交付：简单英语版（2026-10-10）

当前本地标题为 **Knowledge Graph Repair with Reinforcement Learning and Two Rule Prompts**。主文、当前引用的附录、算法标题及图表说明使用常见词和短句。删除防御性叙述，直接报告比较条件、分数、差值和实际操作。

- [论文 PDF](main.pdf)
- [语言修改记录](LANGUAGE_REVISION_2026-10-10.md)
- [独立编译与内容验证](LANGUAGE_VALIDATION_2026-10-10.json)
- [数学导读](MATHEMATICS.md) / [PDF](MATHEMATICS.pdf)
- [实验导读](EXPERIMENTS.md) / [PDF](EXPERIMENTS.pdf)

语言稿已完成。数学公式、表格数值、图片资产、样本、统计规则和匿名作者信息保留；本轮 API 与新增实验均为 0。后续实验和作者云端模板按进度记录处理。向既有 Overleaf 项目同步时保留作者的模板设置，更新标题与内容文件。

以下为原任务与实验历史记录。

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

- [数学导读：逐节对应论文，含例子和公式](MATHEMATICS.md) · [PDF 阅读版](MATHEMATICS.pdf)
- [实验导读：逐节对应设计、结果和结论](EXPERIMENTS.md) · [PDF 阅读版](EXPERIMENTS.pdf)

以上文档已接入最新结果；历史审计与旧实验版本按原档案保留。

## 下一步实验协议（2026-10-04）

后续[四条参考损失审计](RULE_FAILURE_AUDIT_2026-10-04.md)已完成：2 条宽类型禁止、2 条来源矛盾语义缺口；320 次离线屏蔽回放及 5 项测试完成，额外 API 请求 0 次。下一步需要可信的规则校验依据，尚无经验证的自动语义修复器；旧扩训门槛不变。本次新增论文内容仅在 `sections/appendix.tex`，没有增加外部依赖或修改模板。

[完整协议与操作说明](NEXT_EXPERIMENT_PROTOCOL.md)和[执行结果](RULE_FEASIBILITY_RESULTS_2026-10-04.md)放在本目录。新的 20 个开发文档已完成 40 次 Gemma 请求，无运输失败／重试；39 个输出格式合格。完整流程 F1 为 96.63%，但损失 4 条参考事实、augmentation 独有移除为 0，扩训门槛未通过，未启动训练。结果已同步到 experiments、appendix、conclusion 三份 sections 文件；新表内嵌 appendix，无新增外部依赖，模板未改。34 项离线测试和旧结果保留。

## 文件交付约定（2026-10-10）

论文目录保留源码、进度和实验记录；`overleaf/` 是下载后可直接编译的完整交付入口。每次修改根目录源码后，更新 PDF，再运行 `python3 paper2/build_overleaf.py` 同步干净文件夹和 ZIP，检查依赖并验证编译，再 commit / push。

上传时保持目录结构，项目主文件选择 `main.tex`，编译器选择 XeLaTeX。实验原始数据和代码不作为 Overleaf 编译依赖。旧更新包只作为历史档案。

本完整项目沿用当前本地 `IEEEtran` journal 模板，可作为独立新项目编译。作者云端 TKDE 模板尚未同步到本地；向该既有项目同步正文时，保留其模板和 `main.tex`。

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
