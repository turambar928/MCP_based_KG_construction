"""Vector manuscript figures from archived offline results; no network access."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
HERE=Path(__file__).resolve().parent
PAPER=HERE.parents[1]/'paper2'
plt.rcParams.update({'font.family':'Times New Roman','font.size':10,'pdf.fonttype':42,'ps.fonttype':42,
 'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'axes.labelsize':10,
 'xtick.labelsize':9,'ytick.labelsize':9,'legend.fontsize':9,'savefig.dpi':240})
COLORS=['#326C99','#B96732','#467D64','#775B91','#65727E']

def save(fig,folder,name):
    dest=PAPER/'figure'/folder;dest.mkdir(parents=True,exist_ok=True)
    for ext in ['pdf','svg','png']:fig.savefig(dest/f'{name}.{ext}',bbox_inches='tight',pad_inches=.05)
    svg=dest/f'{name}.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)

def box(ax,x,y,w,h,title,body,color=COLORS[0]):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.08,rounding_size=0.10',
                 linewidth=1.05,edgecolor=color,facecolor='#F7F9FB'))
    ax.text(x+w/2,y+h-.25,title,ha='center',va='top',fontsize=10.5,fontweight='bold',color=color)
    ax.text(x+w/2,y+(h-.42)/2,body,ha='center',va='center',fontsize=9.5,linespacing=1.35)

def arrow(ax,a,b,label=None,dashed=False):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,linewidth=1.1,
                               color='#51606A',linestyle='--' if dashed else '-'))
    if label:ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.10,label,ha='center',va='bottom',fontsize=9)

def method_figures():
    fig,ax=plt.subplots(figsize=(7.15,3.35));ax.set(xlim=(-.15,12.15),ylim=(-.25,5.45));ax.axis('off')
    box(ax,.05,2.30,3.20,1.70,'Graph and active rules','Mutate graph records\nAcquire / prune validators')
    box(ax,4.25,2.30,3.20,1.70,'Observed state and mask','14 observed features\n8-action feasibility mask')
    box(ax,8.40,2.30,3.35,1.70,'Double-DQN policy','Online + target networks\nReplay and masked values')
    arrow(ax,(3.33,3.16),(4.15,3.16));arrow(ax,(7.53,3.16),(8.30,3.16))
    ax.plot([10.08,10.08,1.65,1.65],[2.22,1.67,1.67,2.17],color='#51606A',lw=1.1)
    arrow(ax,(1.65,1.86),(1.65,2.20))
    ax.text(5.9,1.78,'Choose one graph or rule action; recompute quality and reward',ha='center',fontsize=9.5)
    ax.text(5.9,4.64,'Budgeted graph–rule co-optimization',ha='center',fontsize=12,fontweight='bold')
    box(ax,.05,-.05,5.35,1.12,'Controlled scheduling environment','Fixed validator registry; no API calls',COLORS[2])
    box(ax,6.38,-.05,5.37,1.12,'Dual-strategy generation archive','Separate candidate and execution studies',COLORS[1])
    save(fig,'method','cooptimization')
    fig,ax=plt.subplots(figsize=(7.15,3.2));ax.set(xlim=(-.1,12.2),ylim=(-.15,5.25));ax.axis('off')
    box(ax,.05,1.90,2.0,1.30,'Source text','Text and identifier')
    box(ax,2.9,3.05,4.0,1.65,'Deletion completion','Original + masked text + spans\nOne call → rule candidates',COLORS[0])
    box(ax,2.9,.60,4.0,1.65,'Augmentation expansion','Source → up to three clauses\nOne call → rule candidates',COLORS[1])
    arrow(ax,(2.15,2.7),(2.80,3.65));arrow(ax,(2.15,2.35),(2.80,1.5))
    box(ax,7.75,1.55,4.15,2.05,'Traceable candidate archive','Declarations / constraint candidates\nExact typed-rule execution\nFree-text candidates retained',COLORS[2])
    arrow(ax,(7.0,3.85),(7.65,3.0));arrow(ax,(7.0,1.45),(7.65,2.13))
    ax.text(6,-.02,'Equal-call comparison: B documents for one strategy; B/2 documents for both',ha='center',fontsize=9.5)
    save(fig,'method','dual_strategy')

def result_figures():
    policy=json.loads((HERE/'policy_analysis.json').read_text());rows=json.loads((HERE/'policy_results.json').read_text())
    summary={r['policy']:r for r in policy['summary']}
    fig,axs=plt.subplots(1,2,figsize=(7.15,2.8),layout='constrained')
    names=['random_valid','rule_first_valid','acquire_then_deficit','Double DQN']
    labels=['Random valid','Rule-first valid','Acquire + deficit','Double DQN']
    for name,label,c,ls in zip(names,labels,COLORS,[':', '-.', '--', '-']):
        a=np.array([r['curve18'] for r in rows if r['policy']==name]);m=a.mean(0);s=a.std(0,ddof=1)
        axs[0].plot(range(19),m,color=c,ls=ls,lw=1.7,label=label)
        axs[0].fill_between(range(19),m-s,m+s,color=c,alpha=.08)
    axs[0].set(xlabel='Decision step',ylabel='Normalized joint quality',xticks=[0,6,12,18],ylim=(.64,1.01))
    axs[0].legend(loc='lower right',frameon=False,fontsize=8);axs[0].set_title('(a) Matched feasible-action policies',loc='left',fontsize=10)
    comps=[r for r in policy['comparisons'] if r['metric']=='auc18']
    short={'acquire_then_deficit':'Acquire + deficit','no_graph_features':'No graph features','no_rule_features':'No rule features','no_mask':'No mask','no_call_penalty':'No call penalty'}
    for i,r in enumerate(comps):
        axs[1].plot([r['ci_low'],r['ci_high']],[i,i],color=COLORS[0],lw=1.8)
        axs[1].scatter(r['difference'],i,color=COLORS[0],s=20,zorder=3)
    axs[1].axvline(0,color='#666666',lw=.8,ls='--');axs[1].set_yticks(range(len(comps)),[short[r['right']] for r in comps])
    axs[1].invert_yaxis();axs[1].set_xlabel('AUC difference: full − comparator');axs[1].set_title('(b) Paired differences and 95% intervals',loc='left',fontsize=10)
    for ax in axs:ax.grid(axis='x',alpha=.15)
    save(fig,'experiments','offline_policy')
    rule=json.loads((HERE/'rule_analysis.json').read_text())
    fig,axs=plt.subplots(1,2,figsize=(7.15,2.7),layout='constrained')
    for strategy,label,c,marker,ls in zip(['deletion','augmentation','dual'],['Deletion','Augmentation','Dual'],COLORS,['o','s','^'],[':', '--','-']):
        rs=[r for r in rule['budget_summary'] if r['strategy']==strategy];x=[r['budget_calls'] for r in rs]
        axs[0].plot(x,[r['constraint_candidates'] for r in rs],label=label,c=c,marker=marker,ms=3,lw=1.4,ls=ls)
        axs[0].fill_between(x,[r['constraint_candidates_p025'] for r in rs],[r['constraint_candidates_p975'] for r in rs],color=c,alpha=.13)
    axs[0].set(xlabel='Archived model calls',ylabel='Distinct constraint candidates',xticks=[0,1000,2000,4000])
    axs[0].ticklabel_format(axis='y',style='sci',scilimits=(3,3));axs[0].legend(frameon=False,fontsize=8)
    axs[0].set_title('(a) Equal-call candidate diversity',loc='left',fontsize=10)
    rows2=rule['execution'];x=np.arange(3);w=.32
    axs[1].bar(x-w/2,[r['recall'] for r in rows2],w,label='Direct typed execution',color=COLORS[0])
    fam=rule['family_label_check']
    axs[1].bar(x+w/2,[r['recall'] for r in fam],w,label='Hand-implemented family',color='#FFFFFF',edgecolor=COLORS[1],hatch='///')
    axs[1].set(xticks=x,xticklabels=['Deletion','Augmentation','Union'],ylabel='Recall on 64 defective cases',ylim=(0,1.27),yticks=[0,.25,.5,.75,1])
    axs[1].legend(frameon=False,loc='upper left',fontsize=8);axs[1].set_title('(b) Execution paths on RuleTest-94',loc='left',fontsize=10)
    save(fig,'experiments','offline_rules')

if __name__=='__main__':method_figures();result_figures()
