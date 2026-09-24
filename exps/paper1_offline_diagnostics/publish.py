"""Concise manuscript and Chinese report for completed post-hoc diagnostics."""
import json,csv,sys,gzip
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_ablation_completion.publish import table
HERE=Path(__file__).resolve().parent

def main():
    d=json.loads((HERE/'results.json').read_text());summary={r['cohort']:r for r in d['summary']};var={(r['cohort'],r['variant']):r for r in d['variant_summary']}
    c,n=summary['controlled'],summary['natural'];vc,vn=var['controlled','no_cost'],var['natural','no_cost']
    text=[r'\paragraph{Where useful edits are lost.}',
      r'We use the stored proposals and trial graphs to locate the selection bottleneck. For each document, we enumerate every subset of its model-proposal bundles and score the resulting graph against the reference. We apply the same edit operations as the runtime but omit its stopping, cost, and feasibility checks. This reference-guided oracle measures the best F1 within those fixed subsets; it is an analysis tool, not a repair method. Detector-generated actions are excluded.', '',
      f"The enumeration covers {d['total_oracle_subsets']:,} subsets across 450 inputs. Table~\\ref{{tab:selection_bottlenecks}} separates candidate availability from stopping and scoring. On controlled inputs, {c['no_initial_violations']} graphs have no detected initial violation, but {c['no_violation_but_imperfect']} still miss reference fields. Of those initial no-violation graphs, {c['no_violation_with_available_improvement']} already have a proposal subset that improves F1. Among evaluated trials, {c['improving_trials_nonpositive']} improve reference F1 but receive non-positive utility. The corresponding natural-input counts are {n['no_violation_with_available_improvement']} graphs and {n['improving_trials_nonpositive']} trial.", '']
    rows=[['Preprocessed graph F1',f"{c['preprocessed_f1']:.4f}",f"{n['preprocessed_f1']:.4f}"],
      ['Uniform optimizer F1',f"{c['optimizer_f1']:.4f}",f"{n['optimizer_f1']:.4f}"],
      ['Fixed-proposal oracle F1',f"{c['oracle_f1']:.4f}",f"{n['oracle_f1']:.4f}"],
      ['Initially no detected violation',c['no_initial_violations'],n['no_initial_violations']],
      ['Imperfect among those graphs',c['no_violation_but_imperfect'],n['no_violation_but_imperfect']],
      ['Improvement available among those graphs',c['no_violation_with_available_improvement'],n['no_violation_with_available_improvement']],
      ['Improving trials with non-positive utility',c['improving_trials_nonpositive'],n['improving_trials_nonpositive']]]
    text.append(table('Post-hoc selection diagnostics on 225 inputs per condition. The oracle uses reference labels only for analysis. Trial counts can exceed document counts.','tab:selection_bottlenecks','lrr','Diagnostic & Controlled & Natural',rows))
    text+=['',f"Removing action cost improves F1 on {vc['improved']} controlled documents, leaves it unchanged on {225-vc['improved']-vc['harmed']}, and harms {vc['harmed']}. On natural inputs it improves {vn['improved']}, leaves {225-vn['improved']-vn['harmed']} unchanged, and harms {vn['harmed']}. The three harmed graphs were already imperfect after preprocessing; none of the 148 exact natural inputs loses F1. The paired controlled change is {100*vc['difference']:.2f} points (95\\% document-bootstrap CI: {100*vc['ci_low']:.2f}--{100*vc['ci_high']:.2f}). These document-level results explain why the same cost change has different effects across the two conditions. No parameters are changed using this analysis."]
    (ROOT/'paper1/sections/offline_diagnostics.tex').write_text('\n'.join(text)+'\n')
    rows=list(csv.DictReader((HERE/'per_case.csv').open()))
    # Fixed deterministic case selection: first case ID meeting each named condition.
    examples={}
    rules={'controlled_undetected_missing':lambda r:r['cohort']=='controlled' and r['initial_no_violations']=='True' and r['oracle_potential']=='True',
      'controlled_benefits_from_no_cost':lambda r:r['cohort']=='controlled' and float(r['no_cost_f1'])>float(r['optimizer_f1'])+1e-12,
      'natural_harmed_by_no_cost':lambda r:r['cohort']=='natural' and float(r['no_cost_f1'])<float(r['optimizer_f1'])-1e-12}
    for name,predicate in rules.items():examples[name]=next(r for r in rows if predicate(r))
    (HERE/'example_selection.json').write_text(json.dumps({'selection':'Lexicographically first case ID matching each named condition; illustrative, not a separate evaluation. Full case outputs are archived.','examples':examples},ensure_ascii=False,indent=2)+'\n')
    all_outputs={(r['cohort'],r['case_id']):r for r in [json.loads(l) for l in (HERE/'case_outputs.jsonl').read_text().splitlines()]}
    traces={(r['cohort'],r['case_id'],r['variant']):r for r in [json.loads(l) for l in gzip.decompress((ROOT/'exps/paper1_ablation_completion/optimizer_traces.jsonl.gz').read_bytes()).splitlines()]}
    case_lines=['# 可复查案例','', '选择规则见 `example_selection.json`。均按指定条件内 case ID 排序取第一个；不是独立测试或人工判例。参考仍为原有 silver 标签。', '']
    def escaped(value):return str(value).replace('|','\\|').replace('\n',' ')
    for name,r in examples.items():
        out=all_outputs[r['cohort'],r['case_id']]
        case_lines += ['## '+name, '', '`'+r['case_id']+'`', '', '|关系|预处理值|原始模型候选值|默认优化器值|无成本值|参考值|','|---|---|---|---|---|---|']
        fields=['preprocessed','raw_proposal','optimizer','no_cost','reference']
        relations=sorted({t['relation'] for f in fields for t in out[f]})
        for relation in relations:
            values=['; '.join(t['tail'] for t in out[f] if t['relation']==relation) or '∅' for f in fields]
            if len(set(values))>1:case_lines.append('|'+escaped(relation)+'|'+'|'.join(map(escaped,values))+'|')
        case_lines+=['', '下表对应完整 head/relation/tail 评分的运行轨迹；上表仅简写 tail，完整三元组见 `case_outputs.jsonl`。', '', '|配置|停止原因|接受动作数|','|---|---|---:|']
        for v in ['uniform_always','no_cost']:
            tr=traces[r['cohort'],r['case_id'],v]
            case_lines.append('|'+v+'|'+tr['audit']['stopped_reason']+'|'+str(tr['applied_count'])+'|')
        case_lines += ['', '|配置|迭代|动作|utility|质量变化（除以100）|动作成本|决策|','|---|---:|---|---:|---:|---:|---|']
        for v in ['uniform_always','no_cost']:
            for trial in traces[r['cohort'],r['case_id'],v]['audit']['decisions']:
                case_lines.append('|'+v+'|'+str(trial['iteration'])+'|'+trial['operation']+'|'+f"{trial['utility']:.6f}|{trial['delta_q']:.6f}|{trial['cost']:.3f}|"+trial['reason']+'|')
        case_lines+=['']
    (HERE/'examples.md').write_text('\n'.join(case_lines).rstrip()+'\n')
    lines=['# Paper 1：服务维护期间的离线机制分析','',
      '不调用 API，不下载模型，不修改参数，不使用正在进行的人工标注。分析对象是已保存的 450 个输入和候选输出；并非新的测试集。','',
      '## 结论','',
      f"1. **停止条件漏掉缺失字段。** 受控输入中 {c['no_initial_violations']} 个图起始时没有被检测出违规，其中 {c['no_violation_but_imperfect']} 个仍不完整；{c['no_violation_with_available_improvement']} 个已有能改善 F1 的候选组合，却没有进入选择。自然输入对应为 {n['no_initial_violations']} 个无违规、{n['no_violation_but_imperfect']} 个不精确、{n['no_violation_with_available_improvement']} 个存在可改善候选。",
      f"2. **候选评分压制正确修改。** 在受控输入实际进入评分的试探中，有 {c['improving_trials_nonpositive']} 次提高参考 F1，却因效用不为正而被拒绝；自然输入为 {n['improving_trials_nonpositive']} 次。计数单位为候选试探，不能当作独立文档。",
      f"3. **放宽成本不是通用修复。** 相对 uniform 基准，受控文档 {vc['improved']} 个改善、{vc['harmed']} 个变差；自然文档 {vn['improved']} 个改善、{vn['harmed']} 个变差。自然数据的 148 个预处理后完全正确输入均未被伤害；损失集中在原本有错的图。",
      '4. **零增益已检查到逐文档输出。** 路由先验、触发器和多项约束开关的零增益不是正负变化相互抵消；完整变更计数见 `variant_summary.csv`。部分其他设置则有输出改变但 F1 不变，因此没有只靠平均值判断。',
      '', '## 固定候选的参考辅助上界','',
      f"穷举 {d['total_oracle_subsets']} 个模型候选编辑子集。每个文档保留原输入或选取已有编辑，不生成新事实；用运行时同一套编辑操作执行，保留重复添加语义。参考标签只用来事后挑选最优子集。",
      '', '|输入|预处理 F1|顺序优化 F1|固定候选 oracle F1|','|---|---:|---:|---:|']
    for r in d['summary']:lines.append(f"|{r['cohort']}|{r['preprocessed_f1']:.4f}|{r['optimizer_f1']:.4f}|{r['oracle_f1']:.4f}|")
    lines+=['','该上界仅适用于这里固定的模型编辑子集，不是生产方法、不是整体框架的理论上界，也不覆盖过滤器、规则候选和重新生成的输出。自然数据仍用原有 silver 参考。','',
      '## 可复查案例','']
    for name,r in examples.items():lines.append(f"- `{name}`：`{r['case_id']}`，优化器 F1={float(r['optimizer_f1']):.4f}，无成本 F1={float(r['no_cost_f1']):.4f}，oracle F1={float(r['oracle_f1']):.4f}。")
    lines+=['','案例按条件内 case ID 排序取第一个，简明字段和决策对照见 [examples.md](examples.md)，完整输入/参考/输出见 `case_outputs.jsonl`。领域分层及预处理后 clean/dirty 分层见 `cost_strata.csv`。这些是探索性机制解释，不做事后调参或新的显著性主张。','',
      '## 对投稿的作用','',
      '本文现在能区分“没有可用候选”和“已有可用候选但检测/打分未采用”，并具体说明成本消融为何跨场景不一致。新增正文小表和案例档案；没有增加需要 API 的任务，也没有把该分析写成额外的独立泛化证据。']
    (HERE/'report.md').write_text('\n'.join(lines)+'\n')
    print('Generated manuscript diagnostics and report.')
if __name__=='__main__':main()
