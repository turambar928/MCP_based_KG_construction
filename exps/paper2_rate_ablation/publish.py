"""Integrate current-reward results without changing the Paper2 method line."""
import json,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
r=json.loads((HERE/'analysis.json').read_text());ss={x['policy']:x for x in r['summary']}
with (HERE/'seed_means.csv').open() as f:seeds=list(csv.DictReader(f))
order=['ddqn_scaled','no_graph_features','no_rule_features','no_mask','no_call_penalty','small_count','acquire_then_deficit']
labels=['Rate DDQN','No graph features','No rule features','No action mask','No call penalty','Small count penalty','Acquire-then-deficit']
plt.rcParams.update({'font.family':'Times New Roman','font.size':10,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(7.4,3.4),sharey=True)
for ax,metric,title in zip(axes,['fact_f1','invalid_relation_repair_rate'],['(a) Reference-triple F1','(b) Invalid relations restored']):
 for i,p in enumerate(order):
  vals=[100*float(x[metric]) for x in seeds if x['policy']==p];offset=np.linspace(-.11,.11,len(vals))
  ax.scatter(vals,i+offset,s=11,color='#AABCCB',alpha=.8,zorder=2)
  ax.scatter([100*ss[p][metric]],[i],s=30,marker='D',color='#32688E',zorder=3)
 ax.set_title(title,fontsize=11,loc='left');ax.set_xlabel('Percent');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
axes[0].set_yticks(range(len(order)),labels);axes[0].invert_yaxis();fig.tight_layout(w_pad=2)
folder=ROOT/'paper2/figure/experiments';fig.savefig(folder/'rate_ablation.pdf',bbox_inches='tight');fig.savefig(folder/'rate_ablation.svg',bbox_inches='tight');plt.close(fig)
lines=[r'\subsubsection{Components under the Rate Reward}',r'\label{sec:rate_ablation}',
r'We add five settings under the current transitions: remove graph features, remove rule features, remove the action mask, remove the training call penalty, or use a calibrated small count penalty. Ten seeds and 250 episodes per setting give fifty new models. The ten existing rate-DDQN checkpoints supply the matched complete-policy reference. All settings are evaluated on thirty further corruption seeds of the same base graph, giving 2,100 policy--seed--scenario outcomes including the heuristic. No model is selected by these outcomes.',
r'The feature removals zero the specified observation entries during training and evaluation. Other observations and the action mask remain available. The no-mask setting selects from all eight actions in both behavior and target updates. Unavailable graph actions can be no-ops, and repeated rule acquisition can incur call cost; the underlying operators are unchanged. The no-call-cost setting removes only that training reward term. Evaluation uses the common rate reward.',
r'\begin{table}[t]',r'\centering',r'\caption{Current-reward component study. Values average ten seed means, each over thirty common scenarios. Calls are simulated acquisition units; actual API requests are zero.}',r'\label{tab:rate_ablation}',r'\scriptsize',r'\begin{tabular}{lrrrr}',r'\toprule',r'Setting & F1 & Restoration & Calls & Unavailable \\',r'\midrule']
for p,label in zip(order,labels):
 a=ss[p];lines.append(f"{label} & {a['fact_f1']:.4f} & {a['invalid_relation_repair_rate']:.4f} & {a['accounted_calls']:.2f} & {a['invalid_actions']:.2f} \\\\")
lines += [r'\bottomrule',r'\end{tabular}',r'\end{table}',
r'Removing the mask lowers F1 by 2.50 points (95\% seed-bootstrap CI: $[-3.45,-1.62]$; Holm $p=0.0234$) and produces 8.26 unavailable selections per episode. It is the only contrast passing correction across twelve F1/restoration comparisons. Removing rule features also lowers mean F1 and raises acquisition cost, but its corrected test does not establish a stable effect across seeds. Every setting preserves initially correct reference facts in this controlled environment. The heuristic again has the highest mean F1 (99.91\%).',
r'\paragraph{Penalty magnitude control.}',
r'We calibrate a fixed count coefficient using twenty development rollouts with uniformly sampled feasible actions. The coefficient is the total rate burden divided by the total number of introduced violations: $\alpha=0.000164493$. This uses observed transitions, not reference facts or test outcomes. Small-count DDQN reaches 99.05\% F1, compared with 99.52\% for rate DDQN; the paired difference is $-0.47$ points (CI: $[-1.73,0.46]$, Holm $p=1$). At the base size, these results do not separate the benefit of rate normalization from a much smaller count coefficient.',
r'\begin{figure*}[t]',r'\centering',r'\includegraphics[width=0.93\textwidth]{figure/experiments/rate_ablation.pdf}',r'\caption{Current-reward ablations and the calibrated count control. Small dots show all ten training-seed means; diamonds show their average. Each seed mean uses thirty shared corruption scenarios. The heuristic is deterministic.}',r'\label{fig:rate_ablation}',r'\end{figure*}']
(ROOT/'paper2/sections/rate_ablation.tex').write_text('\n\n'.join(lines)+'\n')
p=ROOT/'paper2/sections/experiments.tex';s=p.read_text();s=s.replace('Earlier component ablations provide a separate analysis of features, masking and call cost.','Current-reward ablations isolate features, masking, call cost and penalty magnitude.')
s=s.replace('Those ablations establish results under the earlier count penalty; the new reward comparison does not retrain those four component variants.','Those ablations describe the earlier count penalty. The following study repeats the component switches under the current rate reward.')
needle=r'\subsection{Dual-Strategy Candidate Generation}'
if r'\input{sections/rate_ablation}' not in s:s=s.replace(needle,r'\input{sections/rate_ablation}'+'\n\n'+needle)
s=s.replace('Their node types are all \\texttt{Unknown}, leaving 26,270 edges without the type information required by the archived patterns.','Their node types are all \\texttt{Unknown}, leaving 26,270 edges without the type information required by the archived patterns. A further provenance audit checks 51 tracked node CSV files, the three original document JSONL files and two separate-task extraction checkpoints. It restores no traceable types for these graphs. In the enhanced exports, \\texttt{Enhanced} is assigned by the converter as a processing tag, not an entity class; numeric IDs alone do not establish identity across exports.')
s=s.replace('At this graph size, the rate variant also reduces the effective penalty coefficient; the comparison does not isolate normalization from a smaller count coefficient. Testing varied graph sizes and repair risks would distinguish those effects.','The calibrated small-count control is close to rate DDQN at the base size, with no significant paired difference. Separate disjoint-replication tests examine fixed-policy behavior and penalty scaling; connected graphs and varied repair risks remain different settings.')
s=s.replace('Per-run training durations and evaluation timings are archived.','The current-reward component and small-count study adds fifty trained models, again with zero API requests. Per-run training durations and evaluation timings are archived.')
p.write_text(s)

# Normalize Matplotlib path-line whitespace for clean repository diffs.
svg_path=ROOT/'paper2/figure/experiments/rate_ablation.svg'
svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines())+'\n')
