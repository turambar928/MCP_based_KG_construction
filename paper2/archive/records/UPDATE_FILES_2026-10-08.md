# Paper2 本轮替换文件（2026-10-08）

本轮保持论文主线和作者在 Overleaf 的模板。新表内嵌附录，未增加外部图片/表格依赖。

## Overleaf 需要替换的文件

- `sections/methodology.tex`：补充候选与文档对绑定、核验与规则获取分离、类型核验适用范围。
- `sections/experiments.tex`：补充真实完成的三组准入覆盖比较。
- `sections/appendix.tex`：新增 240 回放的说明及内嵌结果表。
- `sections/conclusion.tex`：说明当前核验依据不足时，阻止误删也会失去有效覆盖。

可直接替换以上四个文件，也可整体替换当前 `sections/`。保留你已调整的 `main.tex`、模板及原有 `tables/`、`figure/`、参考文献。完整 paper2 文件夹仍包含全部编译依赖。

`main.pdf` 已更新，为本地现有模板的 21 页合并审阅稿，不代表作者云端排版或正式投稿限页检查已通过。隔离目录编译成功，无未定义引用/交叉引用、无 overfull；仍有原字体替代、underfull 及 Tectonic 的 bbl 重跑提示。重复构建后新增表与文字显示正常，表格位于本地 PDF 第 16 页。

## 同步说明文档

- `AUTOMATIC_RULE_REVIEW_PROTOCOL_2026-10-08.md`：调用前冻结的协议。
- `AUTOMATIC_RULE_REVIEW_RESULTS_2026-10-08.md`：执行结果、实际请求成本、停止原因和下一步。
- `MATHEMATICS.md`、`EXPERIMENTS.md`：新增机制公式与本轮实验解读。
- `BENCHMARK_GUIDE.md`、`TODO.md`、`README.md`：更新状态和入口。
- 仓库 `docs/papers_next_steps_2026-09-28.md`：更新两篇论文下一步。

## 未完成的在线部分

仅派发一次 Qwen 请求；服务 HTTP 200，但请求 `Qwen3.8-27B-no-thinking` 返回 `Qwen/Qwen3.8-27B`，触发冻结协议的停止条件。37 个任务未派发，automatic/combined 两组未评估。本轮三组离线结果不等于自动核验有效。需核实平台别名和 no-thinking 配置后，另登记身份契约修订；本版本没有自动续跑入口或新训练授权。

没有修改 Paper1、人工原始文件、用户 API 配置、TKDE 模板或旧冻结实验。
