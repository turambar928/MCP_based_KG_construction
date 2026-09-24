"""Publish only completed offline experiments; never score an incomplete API run."""
import json,sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_ablation_completion.publish import table,LABELS
from exps.paper1_ablation_completion.offline import VARIANTS
from paper1.figure_style import apply_style,clean_axis,save_vector,BLUE,ORANGE,GREEN,GRAY
HERE=Path(__file__).resolve().parent;FIG=ROOT/'paper1/figure/experiments'

def main():
    from exps.paper1_ablation_completion.run import verify
    verify();d=json.loads((HERE/'archived_gate_results.json').read_text());o=json.loads((HERE/'optimizer_results.json').read_text())
    assert d['complete'] and len(o['summary'])==26 and all(r['n']==225 for r in o['summary'])
    opt={(r['cohort'],r['variant']):r for r in o['summary']};eff={(r['cohort'],r['removed']):r for r in d['effects_exploratory']}
    text=[r'\subsection{Individual Filter and Optimizer Ablations}',r'\label{sec:eval:individual_ablation}','',
      r'We test the filter checks on the 360 Gemma responses from the matched-context study and the 180 responses from the receipt follow-up. Each response is rescored under eight configurations: all checks, each of five checks removed, duplicate and cardinality checks removed together, and all checks removed. These 4,320 scored outputs share 540 model responses. Candidate order stays fixed. Joint removal tests whether cardinality masks the duplicate check.', '',
      r'Table~\ref{tab:gate_checks} reports full-filter F1 minus each modified-filter F1. We average the paired changes over the three generation arms within each document, then over documents. The filter rejects 28 candidate occurrences, all absent from the references: 11 have the wrong document head and 17 fail source support. Other checks remove no additional candidates. On natural inputs, source support contributes 0.505 F1 points and the head check 0.085 points. Their exploratory effects do not pass Holm correction across the 21 cohort/check comparisons. The response-level audit also records any correct fact displaced when a check is removed.', '']
    rows=[];checks=[('no_duplicate','Duplicate'),('no_head','Document head'),('no_relation','Relation type'),('no_support','Source support'),('no_cardinality','Cardinality'),('no_duplicate_cardinality','Duplicate + cardinality'),('raw','All checks')]
    for v,label in checks:rows.append([label,*[f"{100*eff[c,v]['difference']:+.3f}" for c in ['controlled','natural','receipt']]])
    text.append(table('Paired F1 contribution of filter checks, in percentage points. Each cohort contains 60 documents with three generation arms. Positive values favour the full filter.','tab:gate_checks','lrrr','Removed check(s) & Controlled & Natural & Receipts',rows))
    text+=['',r'\paragraph{Sequential optimizer components.}',
      r'We replay 13 settings on the same fixed proposals for 225 controlled and 225 natural graphs, giving 5,850 outcomes. Every setting starts from the same preprocessed graph. The reference uses an always-on uniform prior. The learned-prior arm keeps its trigger on; the next arm restores the learned trigger. The remaining arms each change one component of the uniform reference. Table~\ref{tab:optimizer_complete} gives scores and accepted action counts.', '']
    rows=[]
    for variant in VARIANTS:
        a=opt['controlled',variant];b=opt['natural',variant]
        rows.append([LABELS[variant],f"{a['triple_f1']:.4f}",f"{b['triple_f1']:.4f}",f"{a['applied']} / {b['applied']}"])
    text.append(table('Executed optimizer ablations with fixed proposals. Accepted counts are edit bundles/actions, shown as controlled / natural.','tab:optimizer_complete','lrrr','Setting & Controlled F1 & Natural F1 & Accepted',rows))
    text+=['',
      r'The local, graph, and source score ablations zero the named quality terms and remove their bounds. Remaining weights keep their original values. Violation detectors, hard-violation reward, candidate generation, and stopping rules remain active. These settings isolate score and bound components. The no-quality-bounds arm removes lower-bound and regression checks while retaining density and empty-graph protection.', '',
      r'On controlled inputs, removing action cost raises F1 from 84.72\% to 89.30\% and defect repair from 32.00\% to 46.89\%. It accepts 68 edits; the reference accepts none. Among the reference\textquotesingle s 220 candidate trials, 218 have non-positive utility and two fail source-quality checks. In another 86 documents, the optimizer stops because it detects no violation. Thus both the stopping profile and the action score limit field restoration.', '',
      r'On natural inputs, removing cost changes F1 from 88.33\% to 88.13\%, with 12 accepted edits instead of nine. More edits therefore do not consistently improve reference accuracy. Removing local or source score/bounds reduces F1 to 87.99\%. The learned prior, learned trigger, density bound, quality bounds, and one-step horizon leave output scores unchanged in this replay. The saved neural weights have the training-feature mismatch discussed in the execution audit; these comparisons measure their runtime effect. Per-candidate traces retain trial graphs, quality profiles, utilities, constraint decisions, and stop reasons.', '',
      r'\begin{figure}[t]',r'\centering',r'\includegraphics[width=0.98\textwidth]{figure/experiments/individual_ablation.pdf}',
      r'\caption{Completed offline ablations. Left: paired F1 contribution of head, source-support, and all filter checks, averaged within each document across generation arms. Right: F1 changes from the always-on uniform optimizer for selected component removals. Bars are marginal 95\% document-bootstrap intervals. All 13 optimizer configurations are reported in Table~\ref{tab:optimizer_complete}.}',r'\label{fig:individual_ablation}',r'\end{figure}']
    (ROOT/'paper1/sections/ablation_offline.tex').write_text('\n'.join(text)+'\n')
    apply_style();fig,axes=plt.subplots(1,2,figsize=(7.6,3.65),gridspec_kw={'width_ratios':[1,1.2]})
    ax=axes[0];groups=[('controlled','Controlled',BLUE,-.18),('natural','Natural',ORANGE,0),('receipt','Receipts',GREEN,.18)]
    for cohort,label,color,offset in groups:
        for y,v in enumerate(['no_head','no_support','raw']):
            r=eff[cohort,v];m=100*r['difference'];ax.errorbar(m,y+offset,xerr=[[max(0,m-100*r['ci_low'])],[max(0,100*r['ci_high']-m)]],fmt='o',color=color,capsize=2,markersize=4,label=label if y==0 else None)
    ax.set_yticks(range(3),['Head check','Source support','All checks']);ax.set_ylim(2.7,-.6);ax.set_title('a  Filter contribution',loc='left');ax.set_xlabel('Full minus removed check(s), F1 points');ax.axvline(0,color=GRAY,ls='--',lw=.8);clean_axis(ax);ax.legend(loc='lower right',fontsize=7)
    ax=axes[1];chosen=['learned_always','no_cost','no_profile_bounds','single_step','no_local_score','no_source_score'];labelnames=['Learned prior','No action cost','No quality bounds','One iteration','No local score/bounds','No source score/bound']
    comparisons={(r['cohort'],r['variant']):r for r in o['contrasts_exploratory']}
    for cohort,label,color,offset in groups[:2]:
        for y,v in enumerate(chosen):
            r=comparisons[cohort,v];m=100*r['difference'];ax.errorbar(m,y+offset,xerr=[[max(0,m-100*r['ci_low'])],[max(0,100*r['ci_high']-m)]],fmt='o',color=color,capsize=2,markersize=4,label=label if y==0 else None)
    ax.set_yticks(range(len(chosen)),labelnames);ax.set_ylim(len(chosen)-.3,-.7);ax.set_title('b  Optimizer components',loc='left');ax.set_xlabel('Variant minus uniform reference, F1 points');ax.axvline(0,color=GRAY,ls='--',lw=.8);clean_axis(ax);ax.legend(loc='upper right',fontsize=7)
    fig.tight_layout(w_pad=2);save_vector(fig,FIG/'individual_ablation.pdf',also_png=True)
    lines=['# Paper 1 消融实验完善记录（2026-09-24）','',
      '## 已完成','',
      '- **优化器：13 种配置 × 225 个文档 × 2 种输入 = 5,850 次离线运行。** 分开检查神经先验、神经触发、先验惩罚、动作成本、密度上界、质量约束、迭代次数、规则候选、模型候选，以及三个质量分项。',
      '- **过滤器：540 条历史 Gemma 响应 × 8 种配置 = 4,320 个评分结果。** 五项检查逐一移除，并联合移除重复/基数检查。全过滤结果逐条核对了旧版实现。',
      '- 保存完整候选试探图、profile、utility、拒绝原因、停止原因、文档配对置信区间和过滤器多重比较校正。',
      '- 论文增加对应表格和 Times New Roman 矢量 PDF 图；更正旧表中并非纯预处理消融的 Direct LLM 标签。',
      '', '## 优化器结果','', '|设置|受控 F1|自然 F1|受控/自然接受修改数|','|---|---:|---:|---:|']
    for v in VARIANTS:
        a=opt['controlled',v];b=opt['natural',v];lines.append(f"|{v}|{a['triple_f1']:.4f}|{b['triple_f1']:.4f}|{a['applied']} / {b['applied']}|")
    lines+=['','主要结论：动作成本压制了受控场景的可用修改，但取消成本并不稳定改善自然错误。默认停止条件看不到不少缺失字段。此次运行没有证明旧神经先验或触发器带来额外增益。三个 score/bound 实验只删除质量分项及其约束，不代表整个尺度的移除。','',
      '## 过滤器结果','', '|移除检查|受控 F1贡献（百分点）|自然 F1贡献|收据 F1贡献|','|---|---:|---:|---:|']
    for v,label in checks:lines.append('|'+label+'|'+'|'.join(f"{100*eff[c,v]['difference']:+.3f}" for c in ['controlled','natural','receipt'])+'|')
    lines+=['','共拒绝 28 个候选出现，均不是精确参考成员：文档头 11 个、来源支持 17 个。其余检查没有新增拦截；零增益是本批候选上的观察，不代表这些检查在所有场景均无用。探索性比较经 21 项 Holm 校正后均未达 0.05。','',
      '## 尚未完成：新 API 对照','',
      '预处理 P × 诊断 D × 过滤 G 的完整匹配实验，以及证据索引的锚点/邻居/随机索引/显式字段定义对照，已冻结输入、提示词、评分和 840 个计划请求。**未取得任何成功模型响应，因此没有写入结果数值。**',
      '', '绕过代理后 HTTP/HTTPS 连接超时；现有代理返回 502；GitHub 直连可达。批量进程已停止。`predictions.jsonl` 保留四个失败结果及 16 次已记录连接尝试；另两项工作线程在连接阶段中止，无模型响应。没有新 GPT 或 Claude 调用，也没有下载权重。',
      '', '恢复服务后可继续当前冻结运行；已有失败按原协议保留，评分为空图。若改用另一个模型或重新开始整批，应另建完整运行目录并记录协议修订，不选择性重跑失败或挑选结果。',
      '', '## 文件入口','',
      '- 协议和运行命令：[README.md](README.md)。',
      '- 优化器结果：[optimizer_results.json](optimizer_results.json)；逐文档结果：[optimizer_per_case.csv](optimizer_per_case.csv)。',
      '- 过滤器结果：[archived_gate_results.json](archived_gate_results.json)；拒绝记录：[archived_gate_rejections.csv](archived_gate_rejections.csv)。',
      '- API 状态：[run_status.json](run_status.json)。',
      '', '人工标注仍在进行，本次未修改标注文件。旧神经路由器的训练特征问题尚未修复，本消融不构成新的训练验证。']
    (HERE/'report.md').write_text('\n'.join(lines)+'\n')
    conclusion=ROOT/'paper1/sections/conclusion.tex'
    current=conclusion.read_text()
    paragraph='Component replays show that action-cost penalties suppress controlled repairs,\nwhile removing them does not improve natural-input F1. In the sampled model\nresponses, filtering acts mainly through source support and document-head checks.\n\n'
    if paragraph not in current:conclusion.write_text(current.replace('These results distinguish',paragraph+'These results distinguish'))
    print('Published completed offline results only.')
if __name__=='__main__':main()
