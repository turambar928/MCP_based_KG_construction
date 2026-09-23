"""Author-facing summary of the completed follow-up, generated from archived scores."""
import csv,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent

def main():
    dev=json.loads((HERE/'dev/results.json').read_text());test=json.loads((HERE/'test/results.json').read_text())
    assert dev['complete'] and test['complete']
    rows={r['method']:r for r in test['summary']};primary=test['primary_comparison']['triple_f1']
    lines=['# Paper 1：字段证据定位与独立测试（2026-09-23）','','## 完成内容','',
      '本轮独立于正在进行的真人标注。旧标注包、样本和标签未改动。新 API 调用全部使用 Gemma，不使用 GPT/Claude，也不下载模型。','',
      '1. 分析旧 60 份收据：239 个有标注字段中 190 个严格匹配；49 个差异中，27 个为大小写/空白/标点/金额格式，10 个为取值边界，8 个为来源中另一个值，4 个为规范化后仍不在来源中的参考值。这是程序分类，不是假装增加了人工真值。',
      '2. 新增 `content_enhancement/source_validation.py`，统一来源和候选空白处理，同时保留词边界、大小写与标点。回放 540 条旧响应，只改变此前同一个地址在三组中的误删；旧中文实验结果不变。',
      '3. 为修复提供明确字段定义，区别公司注册名与商号、完整地址、日期与时间、应付金额与小计/现金/找零。简单、证据索引、SHACL 三组均获得同样定义和编号原文行。',
      '4. 证据索引仅增加可复现的字段锚点和邻近行，不提供参考值。与简单基线之间只差这个上下文，便于判断它的独立作用。',
      '5. 从旧样本以外固定抽取 20 条开发与 60 条测试文档，三组 ID 和规范化原文均不重复。只评估一版证据定位设计，再冻结代码、提示、主比较和评分规则。测试参考标签在全部测试预测结束后才下载。','',
      '## 开发与测试结果','',
      '|阶段|方法|文档数|严格 F1|全图匹配|忽略大小写/空白 F1|','|---|---|---:|---:|---:|---:|']
    for phase,result in [('开发',dev),('独立测试',test)]:
        mapping={r['method']:r for r in result['summary']}
        for method,label in [('input','初始提取'),('simple_gate','简单流程'),('evidence_gate','字段证据索引'),('shacl_gate','SHACL 上下文')]:
            r=mapping[method];lines.append(f"|{phase}|{label}|{r['n']}|{r['triple_f1']:.4f}|{r['exact_match']:.4f}|{r['normalized_f1']:.4f}|")
    lo,hi=primary['ci']
    lines+=['',f"预先固定的主比较（证据索引 − 简单流程）：F1 差 {primary['difference']*100:.2f} 个百分点，95% CI [{lo*100:.2f}, {hi*100:.2f}]，双侧配对随机化 p={primary['paired_randomization_p']:.4f}。",'',
      '正文保留严格匹配主结果；金额去货币前缀和千位逗号后的数值正确率单列，不把格式变化等同于金额错误。开发集上失去严格匹配的四个原正确字段均属于此类金额写法变化。', '',
      '## 判断与下一步','']
    if lo>0:lines+=['这批新测试中，证据索引相对共享字段定义的简单流程取得了正向、区间不含零的 F1 差异。其适用范围仍是收据字段修复，需与全文其他数据结果一起解释。']
    elif hi<0:lines+=['这批新测试中，证据索引的 F1 低于简单流程。应保留简单流程为实际选择，论文如实报告证据索引的负结果。']
    else:lines+=['主比较的区间包含零，证据索引尚未显示相对简单流程的稳定独立优势。应把整套修复相对初始提取的变化，与索引单个模块的贡献分开。不要把前者归因给后者。']
    changes=[r for r in test['field_transitions'] if r['method']=='evidence_gate']
    restored=sum(r['output_exact'] for r in changes if r['initial_category']!='exact')
    imperfect=sum(r['n'] for r in changes if r['initial_category']!='exact')
    lost=sum(r['n']-r['output_exact'] for r in changes if r['initial_category']=='exact')
    fields=list(csv.DictReader((HERE/'test/per_field.csv').open()))
    loss_categories=Counter(r['output_category'] for r in fields if r['method']=='evidence_gate' and r['input_exact']=='True' and r['output_exact']=='False')
    lines+=['',f'测试集的证据索引恢复了 {imperfect} 个非精确匹配字段中的 {restored} 个，同时让 {lost} 个原精确匹配字段失去匹配，其中 {loss_categories["amount_surface_format"]} 个只改变金额格式。逐字段变化已写入正文；总分提升不能解释为所有修改都正确。',
      '这轮结果支持同一收据集合中新文档上的证据定位作用，不代表已经验证跨文档推理、其他领域或新的模型。简单流程与索引组的调用次数相同，但索引组输入 token 更多，成本数据已保留。',
      '', '过滤器只拒绝了一个拼接错误的地址，索引组 F1 因此增加约 0.18 个百分点，其余两组不变。索引的主要增益出现在生成阶段。']
    requests=sum(r['requests'] for result in [dev,test] for r in result['cost'])
    lines+=['','## 复现与文件','',f'两阶段共 {requests} 次实际请求（含重试）；原始响应、准确提示、token 用量、逐例分数、字段变化和拒绝记录分别归档在 `dev/`、`test/`。',
      '', '- 实验入口：`exps/paper1_receipt_followup/README.md`。',
      '- 方法锁：`test_lock.json`；评分锁：`scoring_lock.json`。',
      '- 测试结果：`test/report.md`、`test/results.json`、`test/field_transitions.csv`。',
      '- 新图：`paper1/figure/experiments/receipt_followup.pdf`，Times New Roman 矢量图。',
      '- 最新稿：`paper1/main.pdf`。正文继续使用简洁句式，结果与局限分开陈述。',
      '- 真人标注继续独立进行，收到真实文件后再合并、裁决和统计。']
    (ROOT/'docs/summaries/paper1_receipt_followup_2026-09-23.md').write_text('\n'.join(lines)+'\n')
    print('Wrote follow-up revision summary.')
if __name__=='__main__':main()
