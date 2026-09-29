"""Publish the complete fixed-policy size sweep and measured resource scope."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
s=json.loads((HERE/'summary.json').read_text());resources=json.loads((HERE/'resources.json').read_text());scales=[1,2,4,8]
assert len(resources)==12
plt.rcParams.update({'font.family':'Times New Roman','font.size':10,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(7.5,2.8))
for policy,label,color,marker in [('ddqn_scaled','Rate DDQN','#32688E','o'),('small_count','Small-count DDQN','#BB7342','s'),('ddqn_raw','Original count DDQN','#818792','^'),('acquire_then_deficit','Acquire-then-deficit','#568271','D')]:
 rows=[next(r for r in s if r['policy']==policy and r['scale']==n) for n in scales]
 axes[0].plot(scales,[100*r['fact_f1'] for r in rows],label=label,color=color,marker=marker,markersize=4,linewidth=1.2)
rows=[next(r for r in s if r['policy']=='acquire_then_deficit' and r['scale']==n) for n in scales]
for key,label,color,marker in [('rate_penalty_sum','Rate','#32688E','o'),('fixed_small_count_penalty_sum','Calibrated count','#BB7342','s'),('raw_penalty_sum','Original count','#818792','^')]:
 values=[r[key] for r in rows];assert min(values)>0
 axes[1].plot(scales,values,label=label,color=color,marker=marker,markersize=4,linewidth=1.2)
axes[0].set_ylabel('Reference-triple F1 (%)');axes[0].set_title('(a) Fixed-policy transfer',loc='left',fontsize=11)
axes[1].set_yscale('log');axes[1].set_ylabel('Summed penalty (log scale)');axes[1].set_title('(b) Same heuristic trajectories',loc='left',fontsize=11)
for ax in axes:
 ax.set_xscale('log',base=2);ax.set_xticks(scales,[str(n) for n in scales]);ax.set_xlabel('Disjoint copies of the base graph');ax.grid(alpha=.15);ax.set_axisbelow(True);ax.legend(frameon=False,fontsize=8,loc='best')
fig.tight_layout(w_pad=2);folder=ROOT/'paper2/figure/experiments';fig.savefig(folder/'scale_control.pdf',bbox_inches='tight');fig.savefig(folder/'scale_control.svg',bbox_inches='tight');plt.close(fig)
lines=[r'\subsubsection{Fixed Policies across Replicated Graph Sizes}',r'\label{sec:scale_control}',
r'We form one, two, four and eight disjoint copies of the clean base graph, with separate node IDs. The largest clean input has 6,984 nodes and 8,664 edges. At each size, ten fixed policy seeds and five common corruption seeds compare rate, original-count and small-count DDQN with acquire-then-deficit, giving 800 outcomes. All models were trained only at the base size. This sweep repeats the same content; it tests fixed-policy transfer rather than new documents or a large connected KG.',
r'\begin{figure*}[t]',r'\centering',r'\includegraphics[width=0.94\textwidth]{figure/experiments/scale_control.pdf}',r'\caption{Disjoint graph-size control. (a) Mean F1 over ten model seeds and five corruption scenarios at each size. (b) Three penalties evaluated on the same heuristic trajectories. Curves are descriptive; no model is retrained or selected by size.}',r'\label{fig:scale_control}',r'\end{figure*}',
r'\begin{table}[t]',r'\centering',r'\caption{Separate sequential heuristic resource measurement, three repeats per size. Time includes environment construction and rollout with \texttt{tracemalloc}. Memory is peak traced Python allocation, excluding the prebuilt clean graph and native tensor storage; it is not total RSS.}',r'\label{tab:scale_resources}',r'\scriptsize',r'\begin{tabular}{rrrr}',r'\toprule',r'Clean edges & Copies & Median seconds & Median peak MiB \\',r'\midrule']
report=['# Paper2 小计数与跨规模控制','','4 个规模 × 4 策略 × 10 模型种子 × 5 扰动场景 = 800 次评估。全部使用基础规模训练的冻结策略；没有额外训练或 API 调用。','', '|复制数|Rate F1|小计数 F1|原计数 F1|启发式 F1|','|---:|---:|---:|---:|---:|']
for n in scales:
 rs=[r for r in resources if r['scale']==n];seconds=float(np.median([r['seconds_with_tracemalloc'] for r in rs]));mem=float(np.median([r['peak_python_bytes']/2**20 for r in rs]))
 lines.append(f"{1083*n:,} & {n} & {seconds:.3f} & {mem:.2f} \\\\")
 vals=[next(r['fact_f1'] for r in s if r['policy']==p and r['scale']==n) for p in ['ddqn_scaled','small_count','ddqn_raw','acquire_then_deficit']];report.append('|'+str(n)+'|'+'|'.join(f'{v:.5f}' for v in vals)+'|')
lines += [r'\bottomrule',r'\end{tabular}',r'\end{table}']
one=next(r for r in s if r['policy']=='acquire_then_deficit' and r['scale']==1);eight=next(r for r in s if r['policy']=='acquire_then_deficit' and r['scale']==8)
ratio=eight['fixed_small_count_penalty_sum']/one['fixed_small_count_penalty_sum'];rr=eight['rate_penalty_sum']/one['rate_penalty_sum']
lines += [f"On the heuristic trajectories, increasing from one to eight copies multiplies the fixed small-count burden by {ratio:.2f}, compared with {rr:.2f} for the rate burden. This measures how the penalties scale on matched behavior. Fixed-policy outcomes and same-trajectory penalties do not establish an advantage for rate-based learning across sizes; that would require training comparisons at those sizes."]
(ROOT/'paper2/sections/scale_control.tex').write_text('\n\n'.join(lines)+'\n')
p=ROOT/'paper2/sections/experiments.tex';text=p.read_text();needle=r'\input{sections/rate_ablation}'
if r'\input{sections/scale_control}' not in text:text=text.replace(needle,needle+'\n'+r'\input{sections/scale_control}')
p.write_text(text)
report+=['',f'同一启发式轨迹的惩罚计账：1→8 份图，小计数总负担变为 {ratio:.2f} 倍，rate 负担变为 {rr:.2f} 倍。不能由这些固定策略曲线声称跨规模训练优势。','', '最大清洁图 6,984 节点、8,664 边；这是不相连副本，不是真实大型连通图或新领域。规模测量的 12 次资源回放单独存档；时间含环境构建及 tracemalloc 开销，内存仅为 Python 跟踪分配峰值，不是总 RSS，不含预建清洁图和原生张量。','', '详细点值见 summary.csv、resources.csv，全部轨迹、模型哈希和冻结协议均保留。实际 API 调用为 0。']
(HERE/'report_zh.md').write_text('\n'.join(report)+'\n')

# Normalize Matplotlib path-line whitespace for clean repository diffs.
svg_path=ROOT/'paper2/figure/experiments/scale_control.svg'
svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines())+'\n')
