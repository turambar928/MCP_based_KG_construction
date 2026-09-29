"""Figures, tables and a factual report for the completed 840-response recovery."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent/'ablation'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=json.loads((HERE/'results.json').read_text())
plt.rcParams.update({'font.family':'Times New Roman','font.size':10,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(8.2,3.3),gridspec_kw={'width_ratios':[1,1.25]})
colors=['#32688E','#BB7342']
for i,cohort in enumerate(['controlled','natural']):
 rs=[next(x for x in r['factorial_effects'] if x['cohort']==cohort and x['effect']==e) for e in ['P','D','G']]
 y=[j+(i-.5)*.20 for j in range(3)];x=[100*a['difference'] for a in rs]
 axes[0].errorbar(x,y,xerr=[[100*(a['difference']-a['ci_low']) for a in rs],[100*(a['ci_high']-a['difference']) for a in rs]],fmt='o',markersize=4,color=colors[i],capsize=2,linewidth=1.1,label=cohort.title())
axes[0].set_yticks(range(3),['Preprocessing','Diagnosis','Gate']);axes[0].invert_yaxis();axes[0].legend(frameon=False,fontsize=9,loc='lower left');axes[0].set_title('(a) Factorial main effects',loc='left',fontsize=11)
rs=r['receipt_contrasts'];xs=[100*a['difference'] for a in rs]
axes[1].errorbar(xs,range(5),xerr=[[100*(a['difference']-a['ci_low']) for a in rs],[100*(a['ci_high']-a['difference']) for a in rs]],fmt='o',markersize=4,color=colors[0],capsize=2,linewidth=1.1)
axes[1].set_yticks(range(5),['Full − Simple','Full − Random','Full − Anchors','Full − No-def. full','Simple − No-def. simple']);axes[1].invert_yaxis();axes[1].set_title('(b) Receipt context contrasts',loc='left',fontsize=11)
for ax in axes:ax.axvline(0,color='#8D969E',lw=.7,ls='--');ax.set_xlabel('Paired F1 change (percentage points)');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
fig.tight_layout(w_pad=2.5);dest=ROOT/'paper1/figure/experiments';fig.savefig(dest/'recovery_ablation.pdf',bbox_inches='tight');fig.savefig(dest/'recovery_ablation.svg',bbox_inches='tight');plt.close(fig)
lines=[r'\subsection{Contemporaneous Factorial and Evidence Controls}',r'\label{sec:eval:recovery_ablation}',
r'After service recovery, we execute the frozen 840-request protocol as one new Gemma batch. All responses return and parse successfully without retries. Four generation settings cross preprocessing ($P$) and diagnostic context ($D$) on sixty controlled and sixty natural inputs (480 responses). Filtering ($G$) is scored with and without the same checks on each response. The other 360 responses compare six receipt-context settings on the sixty follow-up documents. These are reused evaluation documents; the original interrupted batch remains archived separately.',
r'\begin{table}[t]',r'\centering',r'\caption{Factorial main effects in F1 percentage points, averaged over the other two switches. Each cohort has sixty paired documents. Intervals are marginal 95\% document-bootstrap intervals; $p_H$ uses Holm correction over six main effects.}',r'\label{tab:recovery_factorial}',r'\small',r'\begin{tabular}{llrrr}',r'\toprule',r'Input & Component & Change & 95\% interval & $p_H$ \\',r'\midrule']
for cohort in ['controlled','natural']:
 for e,label in [('P','Preprocessing'),('D','Diagnosis'),('G','Gate')]:
  a=next(x for x in r['factorial_effects'] if x['cohort']==cohort and x['effect']==e)
  lines.append(f"{cohort.title()} & {label} & {100*a['difference']:+.3f} & [{100*a['ci_low']:.3f}, {100*a['ci_high']:.3f}] & {a['p_holm']:.3f} \\\\")
lines += [r'\bottomrule',r'\end{tabular}',r'\end{table}',
r'None of the six main effects passes Holm correction (Table~\ref{tab:recovery_factorial}). Diagnostic context has a negative mean effect in both cohorts. Gate improves mean F1 by 0.164 points on controlled inputs and 0.707 points on natural inputs. Its full-check audit rejects 47 candidate occurrences across all cohorts: 17 have wrong heads and 30 lack source support; none exactly matches a reference triple. Interactions and per-check removals are released with the paired scores.',
r'\begin{table}[t]',r'\centering',r'\caption{Receipt context controls with the same model, source and output budget. All rows include the same filter; sixty documents per row. Random context approximately matches index character length, not exact token count.}',r'\label{tab:recovery_index}',r'\small',r'\begin{tabular}{lrr}',r'\toprule',r'Context & Exact F1 & Normalized F1 \\',r'\midrule']
for arm,label in [('simple','Simple'),('full','Full index'),('anchors','Anchors only'),('random','Random index'),('no_def_simple','Simple, no definitions'),('no_def_full','Full index, no definitions')]:
 a=next(x for x in r['summary'] if x['cohort']=='receipt' and x['arm']==arm and x['g']==1)
 lines.append(f"{label} & {a['triple_f1']:.4f} & {a['normalized_f1']:.4f} \\\\")
lines += [r'\bottomrule',r'\end{tabular}',r'\end{table}',
r'The full index leads Simple by 4.35 F1 points (95\% CI: 1.25 to 7.86), but the contrast has $p_H=0.065$ across the five prespecified comparisons. Full and anchors-only have identical mean F1; full minus random is 1.85 points (CI: $[-0.65,4.52]$, $p_H=0.696$). Removing field definitions from the full index lowers F1 by 8.81 points (CI: $[4.23,13.39]$, $p_H=0.006$), whereas definitions do not improve the simple arm in this batch. These controls support the combination of field definitions and indexed context, while leaving the added value of neighbouring lines and targeted rather than random context unresolved.',
r'\begin{figure}[t]',r'\centering',r'\includegraphics[width=0.98\textwidth]{figure/experiments/recovery_ablation.pdf}',r'\caption{Completed recovery controls. Points show paired mean F1 differences and bars show marginal 95\% document-bootstrap intervals. Main-effect and receipt-contrast families receive separate Holm corrections; intervals are not multiplicity-adjusted.}',r'\label{fig:recovery_ablation}',r'\end{figure}']
(ROOT/'paper1/sections/recovery_ablation.tex').write_text('\n\n'.join(lines)+'\n')
report=['# Paper1 840 请求恢复批次','','840 次 Gemma 请求、840 个成功解析响应、无重试。480 条用于 P×D 生成／G 同响应配对；360 条用于 6 个收据索引条件。旧停机 4 条失败未动。','', '主效应 P、D、G 的 6 个比较均未通过 Holm 校正。诊断上下文在两组的均值为负；门控的平均增益分别为 0.164 和 0.707 个百分点。','', '|收据比较|F1 增益（百分点）|95% 区间|Holm p|','|---|---:|---|---:|']
for a in r['receipt_contrasts']:report.append(f"|{a['left']} − {a['right']}|{100*a['difference']:.3f}|[{100*a['ci_low']:.3f}, {100*a['ci_high']:.3f}]|{a['p_holm']:.4f}|")
report+=['','完整索引与仅锚点均值相同，相对随机索引的优势尚不明确；字段定义对完整索引组有显著作用。不能把结果写成每个复杂模块都带来独立增益。','', '统计按冻结协议执行：10,000 次文档配对 bootstrap／随机化；6 个主效应、5 个收据对照分开 Holm 校正；交互作用为探索结果。随机索引近似字符长度匹配，不是严格等 token。','', '所有 usage 均有返回；cost.csv 包含真实请求及均值。wall time 包含限速等待；不使用未核实单价。模型身份、请求哈希和原始响应解析一致性均已核验。','', '复现：`python exps/paper1_online_recovery/analyze_ablation.py`；图表生成：`python exps/paper1_online_recovery/publish_ablation.py`。冻结原代码、输入和停机记录保持不变。']
(HERE/'report_zh.md').write_text('\n'.join(report)+'\n')

# Normalize Matplotlib path-line whitespace for clean repository diffs.
svg_path=ROOT/'paper1/figure/experiments/recovery_ablation.svg'
svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines())+'\n')
