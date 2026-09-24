"""Render completed results into manuscript tables and Times New Roman vector plots."""
import json,sys,csv
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from paper1.figure_style import apply_style,clean_axis,save_vector,BLUE,ORANGE,GREEN,GRAY
from exps.paper1_ablation_completion.analyze import write_csv
HERE=Path(__file__).resolve().parent
SECTION=ROOT/'paper1/sections/ablation_completion.tex';FIG=ROOT/'paper1/figure/experiments'
LABELS={'uniform_always':'Always-on uniform','learned_always':'Learned prior, always on','learned_trigger':'Learned prior and trigger','no_prior':'No prior penalty','no_cost':'No action cost','no_density':'No density bound','no_profile_bounds':'No quality bounds','single_step':'One iteration','no_rule_candidates':'No rule candidates','rule_only':'Rule candidates only','no_local_score':'No local score/bounds','no_graph_score':'No graph score/bound','no_source_score':'No source score/bound'}
INDEX_LABELS={'simple':'Simple','full':'Full index','anchors':'Anchors only','random':'Random index','no_def_simple':'Simple, no definitions','no_def_full':'Index, no definitions'}
def table(caption,label,cols,header,rows):
    return '\n'.join([r'\begin{table}[t]',r'\centering',r'\caption{'+caption+'}',r'\label{'+label+'}',r'\small',r'\begin{tabular}{'+cols+'}',r'\toprule',header+r' \\',r'\midrule',*[' & '.join(map(str,r))+r' \\' for r in rows],r'\bottomrule',r'\end{tabular}',r'\end{table}'])
def fmt(r):return f"{100*r['difference']:+.2f} points (95\\% CI: $[{100*r['ci_low']:.2f},{100*r['ci_high']:.2f}]$; Holm $p={r['p_holm']:.4f}$)"
def main():
    d=json.loads((HERE/'results.json').read_text());o=json.loads((HERE/'optimizer_results.json').read_text());assert d['complete']
    summary={(r['cohort'],r['arm'],r['g']):r for r in d['summary']};opt={(r['cohort'],r['variant']):r for r in o['summary']}
    effects={(r['cohort'],r['effect']):r for r in d['factorial_effects']};contrasts={(r['left'],r['right']):r for r in d['receipt_contrasts']}
    text=[r'\subsection{Matched Component Ablations}',r'\label{sec:eval:factorial}',r'\label{sec:eval:individual_ablation}','',
      r'We rerun four preprocessing--diagnostic configurations on the same 60 documents under both controlled and natural-input conditions. Each response is scored with and without filtering, giving a $2\times2\times2$ design. The factors are structural preprocessing ($P$), input-derived diagnostics ($D$), and candidate filtering ($G$). All calls use Gemma, the same system prompt, source and schema, temperature zero, and a 4,000-token completion cap. Diagnostics describe the graph supplied in that arm. The 480 responses are generated in shuffled order. These are follow-up measurements on previously evaluated documents.',
      '',r'The primary effects average each factor\textquotesingle s paired F1 change over the other two factors within a document. We use 10,000 document-bootstrap draws for 95\% intervals and paired sign randomization for $p$ values. Holm correction covers the six primary effects across the two input conditions. Interactions are reported in the result archive. Table~\ref{tab:factorial_complete} gives all eight settings.', '']
    rows=[]
    for p in [0,1]:
        for diag in [0,1]:
            for g in [0,1]:
                a=summary['controlled',f'p{p}d{diag}',g];b=summary['natural',f'p{p}d{diag}',g]
                rows.append([p,diag,g,f"{a['repair']:.4f}",f"{a['triple_f1']:.4f}",f"{b['triple_f1']:.4f}"])
    text.append(table('Matched factorial results on 60 documents per condition. Filtering shares the raw model response.','tab:factorial_complete','cccrrr',r'$P$ & $D$ & $G$ & Controlled repair & Controlled F1 & Natural F1',rows))
    for cohort,label in [('controlled','controlled'),('natural','natural-input')]:
        text+=['',f"On {label} graphs, the preprocessing effect is {fmt(effects[cohort,'P'])}. The diagnostic effect is {fmt(effects[cohort,'D'])}; the filtering effect is {fmt(effects[cohort,'G'])}."]
    text+=['',r'\begin{figure}[t]',r'\centering',r'\includegraphics[width=0.98\textwidth]{figure/experiments/ablation_effects.pdf}',r'\caption{Paired component effects in F1 percentage points. Left and middle: factorial main effects on 60 documents per condition. Right: five receipt-index contrasts on 60 documents. Bars are marginal 95\% document-bootstrap intervals; the vertical line marks zero.}',r'\label{fig:ablation_effects}',r'\end{figure}','',r'\paragraph{Individual filtering checks.}',
      r'We also remove each check from the same responses. Removing duplicate and cardinality checks together tests their overlap. All variants retain the original candidate order; an earlier accepted value can consume the field slot. Table~\ref{tab:gate_checks} averages full-filter F1 minus each modified-filter F1 over documents and generation arms. A zero entry records no change on these candidates.','']
    gate={(r['cohort'],r['arm'],r['gate_variant']):r for r in d['gate_summary']};grows=[]
    for variant,label in [('no_duplicate','Duplicate'),('no_head','Head'),('no_relation','Relation'),('no_support','Source support'),('no_cardinality','Cardinality'),('no_duplicate_cardinality','Duplicate + cardinality'),('raw','All checks')]:
        vals=[]
        for cohort in ['controlled','natural','receipt']:
            arms=sorted({a for c,a,v in gate if c==cohort})
            vals.append(100*np.mean([gate[cohort,a,'full']['triple_f1']-gate[cohort,a,variant]['triple_f1'] for a in arms]))
        grows.append([label,*[f'{v:+.3f}' for v in vals]])
    text.append(table('F1 contribution of filtering checks, in percentage points. Each column averages paired response differences, not independent replications across arms.','tab:gate_checks','lrrr','Removed check(s) & Controlled & Natural & Receipts',grows))
    nrej=sum(d['rejections'].values());goldrej=sum(v for k,v in d['rejections'].items() if k.endswith('|True'))
    text+=['',f"Across the 840 responses, the full filter rejects {nrej} candidate occurrences; {goldrej} are exact reference members. Rejection reasons and per-document outcomes are available in the experiment archive.",'',r'\paragraph{Sequential selection.}',
      r'We isolate 13 settings of the executed optimizer using the same stored proposals on 225 controlled and 225 natural graphs (5,850 replay outcomes). The reference uses an always-on uniform prior. We then change only the listed setting, except that the learned trigger is compared with the always-on learned prior. Score/bound removals zero the named quality terms and remove their bounds while retaining the other weights, violation detectors, and stopping rules. Thus they test score components rather than whole assessment scales.','']
    from exps.paper1_ablation_completion.offline import VARIANTS
    rows=[]
    for variant in VARIANTS:
        a=opt['controlled',variant];b=opt['natural',variant]
        rows.append([LABELS[variant],f"{a['triple_f1']:.4f}",f"{b['triple_f1']:.4f}",f"{a['applied']} / {b['applied']}"])
    text.append(table('Executed optimizer ablations with fixed proposals. Accepted counts are edit bundles/actions, shown as controlled / natural.','tab:optimizer_complete','lrrr','Setting & Controlled F1 & Natural F1 & Accepted',rows))
    a=opt['controlled','no_cost'];base=opt['controlled','uniform_always'];b=opt['natural','no_cost'];nat=opt['natural','uniform_always']
    text+=['',f"Removing action cost changes controlled F1 from {100*base['triple_f1']:.2f}\\% to {100*a['triple_f1']:.2f}\\%, with {a['applied']} accepted edits instead of {base['applied']}. Natural-input F1 changes from {100*nat['triple_f1']:.2f}\\% to {100*b['triple_f1']:.2f}\\%. This separates cost-induced rejection from the effect of the learned prior. The archived neural prior and trigger yield the same output scores as the uniform reference. The stored neural weights retain the training-feature issue described earlier; these switches measure their runtime effect. Full traces include every candidate score, constraint decision, and stopping reason."]
    SECTION.write_text('\n'.join(text)+'\n')
    text=[r'\subsection{Evidence-Index Component Ablations}',r'\label{sec:eval:index_ablation}','',
      r'On the same 60 receipt test documents, we run six contemporaneous Gemma arms (360 responses). All use the complete numbered transcript and identical generation settings. Anchors Only removes neighbouring-line pointers from the index. Random Index preserves each field\textquotesingle s anchor and neighbour counts, with one seeded random draw selected by anchor-text length alone. The definitions variants remove the explicit field-definitions object while retaining field names and shared instructions. These comparisons test index components on the existing sample.','']
    rows=[]
    for arm in ['simple','full','anchors','random','no_def_simple','no_def_full']:
        r=summary['receipt',arm,1];c=next(x for x in d['cost'] if x['cohort']=='receipt' and x['arm']==arm)
        rows.append([INDEX_LABELS[arm],f"{r['triple_f1']:.4f}",f"{r['normalized_f1']:.4f}",f"{r['exact_match']:.4f}",f"{c['mean_input_tokens']:.0f}"])
    text.append(table('Receipt-index ablations, all with the same output filter. Normalized F1 ignores case and whitespace. Tokens are measured mean input tokens per call.','tab:index_complete','lrrrr','Arm & F1 & Normalized F1 & Exact & Tokens',rows))
    for (left,right),r in contrasts.items():text+=['',f"{INDEX_LABELS[left]} minus {INDEX_LABELS[right]} gives {fmt(r)}."]
    text+=['',r'Holm correction covers these five predeclared contrasts. The random control matches counts and approximate anchor-text length; actual token counts differ. The archive reports anchor overlap and text lengths. Raw and filtered scores, request counts, and request times are also retained.']
    (ROOT/'paper1/sections/index_ablation.tex').write_text('\n'.join(text)+'\n')
    apply_style();fig,axes=plt.subplots(1,3,figsize=(8.8,3.1),gridspec_kw={'width_ratios':[1,1,1.5]})
    for ax,cohort,title in zip(axes[:2],['controlled','natural'],['a  Controlled inputs','b  Natural inputs']):
        rs=[effects[cohort,k] for k in ['P','D','G']]
        for y,r in enumerate(rs):
            m=100*r['difference'];ax.errorbar(m,y,xerr=[[m-100*r['ci_low']],[100*r['ci_high']-m]],fmt='o',color=BLUE if cohort=='controlled' else ORANGE,capsize=2,markersize=4)
        ax.set_yticks(range(3),['Preprocessing','Diagnostics','Filtering']);ax.set_ylim(2.7,-.7);ax.set_title(title,loc='left');ax.axvline(0,color=GRAY,lw=.8,ls='--');clean_axis(ax);ax.set_xlabel('F1 change (percentage points)')
    ax=axes[2];labels=['Full − simple','Full − random','Full − anchors','Full − no definitions','Simple − no definitions']
    for y,r in enumerate(d['receipt_contrasts']):
        m=100*r['difference'];ax.errorbar(m,y,xerr=[[m-100*r['ci_low']],[100*r['ci_high']-m]],fmt='o',color=GREEN,capsize=2,markersize=4)
    ax.set_yticks(range(5),labels);ax.set_ylim(5,-1);ax.set_title('c  Receipt index',loc='left');ax.axvline(0,color=GRAY,lw=.8,ls='--');clean_axis(ax);ax.set_xlabel('F1 change (percentage points)')
    fig.tight_layout(w_pad=1.8);save_vector(fig,FIG/'ablation_effects.pdf',also_png=True)
    # Reproducible machine-readable reporting summary and a concise review document.
    lines=['# Paper 1 消融补充结果','',f"Gemma 修复结果：{d['n_responses']}；实际请求（含重试）：{d['requests']}；状态：{d['status']}。",'',
      '## 主流程因子效应','', '|输入|因素|F1变化（百分点）|95% CI|Holm p|','|---|---|---:|---|---:|']
    for r in d['factorial_effects']:
        if len(r['effect'])==1:lines.append(f"|{r['cohort']}|{r['effect']}|{100*r['difference']:+.3f}|[{100*r['ci_low']:.3f}, {100*r['ci_high']:.3f}]|{r['p_holm']:.4f}|")
    lines+=['','## 证据索引','', '|对比|F1变化（百分点）|95% CI|Holm p|','|---|---:|---|---:|']
    for r in d['receipt_contrasts']:lines.append(f"|{r['left']} − {r['right']}|{100*r['difference']:+.3f}|[{100*r['ci_low']:.3f}, {100*r['ci_high']:.3f}]|{r['p_holm']:.4f}|")
    lines+=['','## 优化器','', '|设置|受控 F1|自然 F1|受控/自然接受修改数|','|---|---:|---:|---:|']
    for variant in VARIANTS:
        a=opt['controlled',variant];b=opt['natural',variant];lines.append(f"|{variant}|{a['triple_f1']:.4f}|{b['triple_f1']:.4f}|{a['applied']} / {b['applied']}|")
    lines+=['','## 解释与完成范围','',
      '- 新实验单独控制预处理和诊断；旧表的 Direct LLM 行已改名，避免被当成纯预处理消融。',
      '- 同一响应分别关闭过滤检查，并联合关闭重复/基数检查，保留扫描顺序及其相互影响。',
      '- 优化器补齐 13 种配置、5,850 条真实运行轨迹；这是对固定候选的选择实验，不增加模型调用。',
      '- 三个 score/bound 消融仅删除质量分项及约束；不是把整个尺度或检测器删除。',
      '- 新调用仅 Gemma；历史 Claude 输出仅作为既有数据读取。没有下载模型。',
      '- 复用了先前评估过的文档；随机索引只有一个固定实现，字符长度近似匹配，token 未强行匹配。',
      '- 人工标注仍待回收；旧神经路由器的训练特征问题仍存在，本实验不构成新的路由器训练验证。',
      '- 统计含配对置信区间、多重比较校正及交互项；负结果和失败均保留。',
      '', '详细协议见 [README.md](README.md)，完整统计见 [results.json](results.json)。']
    (HERE/'report.md').write_text('\n'.join(lines)+'\n')
    manuscript=ROOT/'paper1/sections/experiments.tex'
    current=manuscript.read_text().replace(r'\input{sections/ablation_offline}',r'\input{sections/ablation_completion}')
    if r'\input{sections/index_ablation}' not in current:current=current.replace(r'\input{sections/receipt_followup}',r'\input{sections/receipt_followup}'+'\n'+r'\input{sections/index_ablation}')
    manuscript.write_text(current)
    print('Wrote two manuscript sections, vector figure, and report.')
if __name__=='__main__':main()
