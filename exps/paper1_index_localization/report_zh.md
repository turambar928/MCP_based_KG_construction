# Paper1 证据索引定位分析

既有 60 份收据、240 个参考字段；使用固定索引，参考值仅用于事后定位与评分。

|字段|参考值位置|字段数|Simple 正确|Index 正确|净增加|
|---|---|---:|---:|---:|---:|
|ALL|indexed|188|163|174|11|
|ALL|outside_index|36|26|26|0|
|ALL|not_source_matched|16|0|0|0|
|company|indexed|40|35|38|3|
|company|outside_index|19|10|10|0|
|company|not_source_matched|1|0|0|0|
|address|indexed|45|34|42|8|
|address|outside_index|2|2|2|0|
|address|not_source_matched|13|0|0|0|
|date|indexed|58|58|58|0|
|date|outside_index|1|1|1|0|
|date|not_source_matched|1|0|0|0|
|total|indexed|45|36|36|0|
|total|outside_index|14|13|13|0|
|total|not_source_matched|1|0|0|0|

匹配保留大小写与标点，仅压缩空白。跨行参考必须覆盖实际连续来源跨度；不把不相邻索引行拼起来制造命中。`not_source_matched` 单列，不能当作索引漏检。

多锚点与金额数量仅为可观察竞争代理，不是人工认定的语义候选数量。字段属于同一文档，本报告只做描述性分层，不把 240 个字段当独立统计样本。

复现：`/tmp/kgbench-local-venv/bin/python exps/paper1_index_localization/analyze.py`。该分析不请求模型、不调整索引。
