# Paper2 类型与词汇来源审计

检查 51 个已跟踪节点 CSV、3 个原始文档 JSONL 和 2 个不同任务的抽取 checkpoint。原始三图共 26,270 条边；本次可追溯恢复类型数为 **0**。

`Enhanced` 来自 `scripts/converters/bulk_jsonl_to_csv_enhanced.py` 的固定处理标记，不是实体类型。`Unknown` 和默认 `Other` 同样不用于执行类型规则。

|节点文件|行数|类型统计|
|---|---:|---|
|data/nodes.csv|7|{"水果": 2, "交通工具": 1, "用户": 3, "Unknown": 1}|
|data/qa_bad_report/isolated_nodes.csv|1|{"用户": 1}|
|data/qa_environment_report_1/isolated_nodes.csv|0|{}|
|data/qa_environment_report_2/isolated_nodes.csv|1|{"Unknown": 1}|
|data/qa_environment_report_3/isolated_nodes.csv|0|{}|
|data/qa_finance_report_1/isolated_nodes.csv|0|{}|
|data/qa_finance_report_2/isolated_nodes.csv|0|{}|
|data/qa_finance_report_3/isolated_nodes.csv|0|{}|
|data/qa_gover_report_1/isolated_nodes.csv|0|{}|
|data/qa_report1/isolated_nodes.csv|0|{}|
|data/qa_report2/isolated_nodes.csv|0|{}|
|data/政务_nodes.csv|11122|{"Unknown": 11122}|
|data/政务_test_enhanced_nodes.csv|121|{"Enhanced": 121}|
|data/政务_test_nodes.csv|88|{"Unknown": 88}|
|data/政务_低质量_enhanced_nodes.csv|12765|{"Enhanced": 12765}|
|data/政务_低质量_nodes copy.csv|18230|{"Unknown": 18230}|
|data/政务_低质量_nodes.csv|8951|{"Unknown": 8951}|
|data/环境_2_nodes.csv|189|{"Unknown": 189}|
|data/环境_nodes.csv|60|{"Unknown": 60}|
|data/环境_nodes_1.csv|141|{"Unknown": 141}|
|data/环境_低质量_enhanced_nodes.csv|336|{"Enhanced": 336}|
|data/环境_低质量_nodes.csv|142|{"Unknown": 142}|
|data/金融_2_nodes.csv|148|{"Unknown": 148}|
|data/金融_nodes.csv|70|{"Unknown": 70}|
|data/金融_低质量1_enhanced_nodes.csv|286|{"Enhanced": 286}|
|data/金融_低质量_nodes.csv|115|{"Unknown": 115}|
|evaluate_kg/nodes.csv|7|{"水果": 2, "交通工具": 1, "用户": 3, "Unknown": 1}|
|evaluate_kg/qa_report/isolated_nodes.csv|1|{"用户": 1}|
|exps/_tmp_sc/isolated_nodes.csv|0|{}|
|exps/decision_network/_tmp_eval/isolated_nodes.csv|0|{}|
|exps/qa_environment_1/isolated_nodes.csv|0|{}|
|exps/qa_environment_2/isolated_nodes.csv|0|{}|
|exps/qa_environment_3/isolated_nodes.csv|0|{}|
|exps/qa_finance_1/isolated_nodes.csv|1|{"Unknown": 1}|
|exps/qa_finance_2/isolated_nodes.csv|0|{}|
|exps/qa_finance_3/isolated_nodes.csv|0|{}|
|exps/qa_gover_1/isolated_nodes.csv|0|{}|
|exps/qa_gover_2/isolated_nodes.csv|0|{}|
|exps/qa_gover_3/isolated_nodes.csv|0|{}|
|exps/shacl_baseline/_tmp/isolated_nodes.csv|0|{}|
|exps/政务_低质量_enhanced_nodes.csv|12437|{"Enhanced": 12437}|
|exps/政务_低质量_nodes.csv|8951|{"Unknown": 8951}|
|exps/环境_nodes.csv|137|{"Unknown": 137}|
|exps/环境_低质量_enhanced_nodes.csv|323|{"Enhanced": 323}|
|exps/环境_低质量_nodes.csv|169|{"Unknown": 169}|
|exps/金融_nodes copy.csv|67|{"Unknown": 67}|
|exps/金融_nodes.csv|67|{"Unknown": 67}|
|exps/金融_低质量_enhanced_nodes copy.csv|247|{"Enhanced": 247}|
|exps/金融_低质量_enhanced_nodes.csv|248|{"Enhanced": 248}|
|exps/金融_低质量_nodes copy.csv|147|{"Unknown": 147}|
|exps/金融_低质量_nodes.csv|128|{"Unknown": 128}|

显式类型候选、关系精确映射和每份文件的 SHA256 见 `results.json`。仅数值 ID 相同不足以确认是同一实体；没有同一来源文档／导出映射时不自动回填。

下一步所需输入：每个实体的来源文档 ID、来源跨度、显式类型与类型词表版本；独立核验的人可回填这些字段。API 可以提议类型，但不能同时作为规则有效性或最终编辑的独立参考。当前缺口不能通过直接启动 DDQN 训练解决。

审计只覆盖清单中的本地档案；如另有原始带类型的抽取日志，可以追加新版本审计。
