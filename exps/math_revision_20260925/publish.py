"""Generate revision tables/figures directly from offline outputs."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'paper1'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from figure_style import apply_style
from exps.paper2_offline_revision.make_tables import table,NAMES
HERE=Path(__file__).resolve().parent

def paper1():
    apply_style();results=json.loads((HERE/'paper1/results.json').read_text());summary=results['summary']
    index={(r['cohort'],r['variant']):r for r in summary}
    names=['uniform_absolute','uniform_relative','learned_absolute','learned_relative']
    labels=['Uniform / absolute','Uniform / relative','Learned / absolute','Learned / relative']
    body=[]
    for name,label in zip(names,labels):
        a=index['controlled',name];b=index['natural',name]
        body.append(f"{label} & {a['triple_f1']:.4f} & {b['triple_f1']:.4f} & {a['accepted_edits']} / {b['accepted_edits']} \\\\")
    tex=r'''\begin{table}[t]
\centering
\caption{Version-2 selector on the same archived proposals. Relative priors use the uniform distribution as their zero point. Accepted edits are controlled / natural.}
\label{tab:math_revision_selector}
\small
\begin{tabular}{lrrr}
\toprule
Prior / offset & Controlled F1 & Natural F1 & Accepted \\
\midrule
'''+ '\n'.join(body)+r'''
\bottomrule
\end{tabular}
\end{table}
'''
    (ROOT/'paper1/sections/math_revision_table.tex').write_text(tex)
    fig,axs=plt.subplots(1,2,figsize=(7.15,2.8),layout='constrained')
    for ax,cohort,title in zip(axs,['controlled','natural'],['(a) Controlled defects','(b) Natural extraction inputs']):
        for j,name in enumerate(names):
            r=index[cohort,name]
            ax.scatter(r['triple_f1']*100,j,color=['#65727E','#326C99','#467D64','#B96732'][j],s=28)
            ax.annotate(f" {r['triple_f1']*100:.2f}",(r['triple_f1']*100,j),xytext=(4,0),textcoords='offset points',va='center',fontsize=7)
        ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.set_xlabel('Mean document F1 (%)');ax.set_title(title,loc='left');ax.grid(axis='x',alpha=.2)
        vals=[index[cohort,n]['triple_f1']*100 for n in names];ax.set_xlim(min(vals)-.5,max(vals)+1.4)
    dest=ROOT/'paper1/figure/experiments'
    for ext in ['pdf','svg','png']:fig.savefig(dest/f'math_revision.{ext}',bbox_inches='tight',dpi=220)
    for svg in dest.glob('math_revision*.svg'):
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)

def paper2():
    apply_style();analysis=json.loads((HERE/'paper2/policy_analysis.json').read_text());s={r['policy']:r for r in analysis['summary']}
    def metric(r,k):return f"${r[k]:.4f}\\pm{r[k+'_std']:.4f}$"
    def rows(names):return [[NAMES[n],metric(s[n],'final_joint'),metric(s[n],'auc18'),f"{s[n]['accounted_calls']:.1f}",f"{s[n]['invalid_actions']:.1f}",f"{s[n]['new_violations']:.1f}",f"{s[n]['discounted_return']:.4f}"] for n in names]
    names=['random_valid','alternating_valid','rule_first_valid','acquire_then_deficit','DQN','Double DQN','model_informed_lookahead']
    table('math_revision_policies','Corrected-environment policy comparison over ten paired scenarios (mean $\\pm$ sample standard deviation). Calls are accounted acquisition units.','tab:rl_ablation','lrrrrrr',['Policy','Final quality','AUC$_{18}$','Calls','Invalid','New viol.','Return'],rows(names),wide=True)
    table('math_revision_ablations','Corrected-environment ablations, ten retrained models per setting.','tab:offline_ablations','lrrrrrr',['Setting','Final quality','AUC$_{18}$','Calls','Invalid','New viol.','Return'],rows(['Double DQN','no_graph_features','no_rule_features','no_mask','no_call_penalty']),wide=True)
    tests=[]
    for t in analysis['comparisons']:
        tests.append([NAMES[t['right']], 'Final' if t['metric']=='final_joint' else 'AUC',f"{t['difference']:+.5f}",f"[{t['ci_low']:+.5f}, {t['ci_high']:+.5f}]",f"{t['p_holm']:.4f}"])
    table('math_revision_tests','Full Double DQN minus each comparator in the corrected environment. Intervals are pointwise paired-bootstrap 95\\% intervals; Holm adjusts ten tests.','tab:offline_tests','llrrr',['Comparator','Metric','Difference','95\\% interval','$p_{\\mathrm{Holm}}$'],tests,wide=True)
    rows2=json.loads((HERE/'paper2/policy_results.json').read_text())
    fig,axs=plt.subplots(1,2,figsize=(7.15,2.8),layout='constrained')
    colors=['#326C99','#B96732','#467D64','#775B91']
    for name,label,color,style in zip(['random_valid','rule_first_valid','acquire_then_deficit','Double DQN'],
            ['Random valid','Rule-first valid','Acquire + deficit','Double DQN'],colors,[':', '-.', '--', '-']):
        values=np.array([r['curve18'] for r in rows2 if r['policy']==name]);mean=values.mean(0);sd=values.std(0,ddof=1)
        axs[0].plot(range(19),mean,color=color,ls=style,lw=1.5,label=label)
        axs[0].fill_between(range(19),mean-sd,mean+sd,color=color,alpha=.08)
    axs[0].set(xlabel='Decision step',ylabel='Normalized joint quality',xticks=[0,6,12,18],ylim=(.64,1.01))
    axs[0].legend(loc='lower right',frameon=False,fontsize=7)
    axs[0].set_title('(a) Corrected-environment policies',loc='left')
    comparisons=[r for r in analysis['comparisons'] if r['metric']=='auc18']
    for i,r in enumerate(comparisons):
        axs[1].plot([r['ci_low'],r['ci_high']],[i,i],color=colors[0],lw=1.5)
        axs[1].scatter(r['difference'],i,color=colors[0],s=20,zorder=3)
    axs[1].axvline(0,color='#666666',lw=.8,ls='--')
    axs[1].set_yticks(range(len(comparisons)),[NAMES[r['right']] for r in comparisons])
    axs[1].invert_yaxis();axs[1].set_xlabel('AUC: full minus comparator')
    axs[1].set_title('(b) Paired differences and 95% intervals',loc='left')
    for ax in axs:ax.grid(axis='x',alpha=.15)
    dest=ROOT/'paper2/figure/experiments'
    for ext in ['pdf','svg','png']:fig.savefig(dest/f'math_revision_policy.{ext}',bbox_inches='tight',dpi=220)
    for svg in dest.glob('math_revision*.svg'):
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)
    bridge=json.loads((HERE/'paper2/rule_bridge_results.json').read_text())
    rs=[[r['strategy'].title(),str(r['compiled_active']),str(r['removed_defective_records']),str(r['removed_clean_records']),str(r['remaining_records'])] for r in bridge['summary']]
    table('math_revision_bridge','Offline generated-rule bridge on the previously inspected RuleTest-94 suite. Removal resolves a typed prohibition; it does not reconstruct a reference fact.','tab:rule_bridge','lrrrr',['Packet','Rules','Defect removals','Clean removals','Retained'],rs,wide=True)

if __name__=='__main__':
    {'paper1':paper1,'paper2':paper2}[sys.argv[1]]()
