#!/usr/bin/env python3
"""Vector figures for the executed pipeline and 2026-09-21 mechanism audit."""
from pathlib import Path
import json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from figure_style import apply_style,clean_axis,panel_label,save_vector,BLUE,GREEN,ORANGE,GRAY,INK,PALE,GRID
apply_style()
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'exps/paper1_mechanism_audit'
OUT=ROOT/'paper1/figure'


def architecture():
    fig,ax=plt.subplots(figsize=(7.15,2.65));ax.set(xlim=(0,10),ylim=(0,3.55));ax.axis('off')
    colors=[GRAY,BLUE,GREEN,ORANGE]
    titles=['Public input','Normalize + diagnose','Generate candidates','Validate candidates']
    bodies=['Source document X\nDocument node + schema\nInput triple multiset',
            'Remove structural defects\nRecord visible violations\nNo gold-field lookup',
            'One model call\nExact source-span copying\nComplete JSON proposal',
            'Head / relation / support\nDuplicates / cardinality\nAccept or log rejection']
    for i,(title,body,c) in enumerate(zip(titles,bodies,colors)):
        x=.05+i*2.55
        ax.add_patch(FancyBboxPatch((x,1.4),2.25,1.65,boxstyle='round,pad=0.04,rounding_size=0.09',fc=PALE,ec=c,lw=1.0))
        ax.text(x+1.125,2.73,title,ha='center',va='center',weight='bold',fontsize=8)
        ax.text(x+1.125,2.08,body,ha='center',va='center',fontsize=7.4,linespacing=1.6)
        if i<3:ax.annotate('',xy=(x+2.51,2.2),xytext=(x+2.3,2.2),arrowprops={'arrowstyle':'->','color':INK,'lw':1})
    ax.text(5.65,.98,'Same response',fontsize=7.4,ha='center',color=GREEN)
    ax.annotate('',xy=(6.45,.52),xytext=(6.25,1.38),arrowprops={'arrowstyle':'->','color':GREEN,'lw':.9})
    ax.annotate('',xy=(8.22,.52),xytext=(8.8,1.38),arrowprops={'arrowstyle':'->','color':ORANGE,'lw':.9})
    ax.text(7.34,.4,'Paired raw / gated evaluation',ha='center',fontsize=8,weight='bold')
    ax.text(1.52,.4,'Reference graph: scoring only',ha='center',fontsize=7.6,color=GRAY)
    ax.annotate('',xy=(5.9,.4),xytext=(3.1,.4),arrowprops={'arrowstyle':'->','color':GRAY,'lw':.8,'linestyle':'dashed'})
    save_vector(fig,OUT/'method/source_pipeline.pdf')


def natural(results):
    rows={(r['stratum'],r['method']):r for r in results['natural_stratified']}
    copy_result=next(r for r in json.loads((DATA/'source_field_results.json').read_text()) if r['stream']=='natural')
    for stratum in ['all','parsed','parsed_dirty','malformed']:
        rows[(stratum,'source_field_copy')]={'triple_f1':copy_result['triple_f1'],'exact_match':copy_result['exact_match']}
    groups=[('all','All inputs\n(n = 225)'),('parsed','Valid JSON\n(n = 215)'),
            ('parsed_dirty','Imperfect valid JSON\n(n = 67)'),('malformed','Malformed JSON\n(n = 10)')]
    fig,axes=plt.subplots(1,2,figsize=(7.15,2.9),gridspec_kw={'wspace':.35})
    for ax,metric,title in zip(axes,['triple_f1','exact_match'],['Triple F1','Exact graph match']):
        for method,label,color,marker,offset in [('input','Extracted input',GRAY,'o',-.24),('simple','Simple pipeline',ORANGE,'s',-.08),('diagnosis_gate','Diagnosis + Gate',BLUE,'D',.08),('source_field_copy','Source-field Copy',GREEN,'*',.24)]:
            vals=[rows[(g,method)][metric]*100 for g,_ in groups]
            ax.scatter(vals,np.arange(4)+offset,c=color,marker=marker,s=24,label=label,zorder=3,edgecolors='white',linewidths=.4)
        ax.set_yticks(np.arange(4),[label for _,label in groups]);ax.invert_yaxis();ax.set_xlim(-3,104)
        ax.set_xlabel(title+' (%)');clean_axis(ax,'x')
    panel_label(axes[0],'a',-.31);panel_label(axes[1],'b',-.31)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,ncol=2,loc='upper center',bbox_to_anchor=(.5,1.15))
    save_vector(fig,OUT/'experiments/natural_stratified.pdf')


def mechanisms(results):
    if not results['complete']:return
    rows={(r['stream'],r['method']):r for r in results['matched_summary']}
    fig,axes=plt.subplots(1,3,figsize=(7.15,2.7),gridspec_kw={'width_ratios':[1,1,1.1],'wspace':.5})
    names=['base','diagnosis','shacl_context'];labels=['Base','Diagnostic','SHACL context']
    for ax,stream,title in zip(axes[:2],['controlled','natural'],['Controlled (n = 60)','Natural inputs (n = 60)']):
        for i,name in enumerate(names):
            a=rows[stream,name+'_raw'];b=rows[stream,name+'_gate']
            ax.plot([a['triple_f1']*100,b['triple_f1']*100],[i,i],c=GRAY,lw=.8,zorder=1)
            for r,c,m,shift in [(a,GRAY,'o',-.07),(b,BLUE,'D',.07)]:
                v=r['triple_f1']*100;lo,hi=np.array(r['f1_ci'])*100
                ax.errorbar(v,i+shift,xerr=[[v-lo],[hi-v]],fmt=m,color=c,markersize=4,capsize=1.5,lw=.7)
        ax.set_yticks(range(3),labels);ax.invert_yaxis();ax.set_xlabel('Triple F1 (%)');ax.set_title(title)
        vals=[r['f1_ci'][0]*100 for (st,_),r in rows.items() if st==stream]
        ax.set_xlim(max(0,min(vals)-2),101);clean_axis(ax,'x')
    ax=axes[2]
    old=json.loads((ROOT/'exps/paper1_submission_extensions/results.json').read_text())
    ctrl=next(r['triple_f1'] for r in old['synthetic_simple_pipeline'] if r['method']=='Full system')
    nat=next(r['triple_f1'] for r in old['natural_error'] if r['method']=='Full system')
    optim={r['stream']:r['triple_f1'] for r in results['optimizer_summary'] if r['method']=='uniform'}
    for i,(name,a,b) in enumerate([('Controlled',ctrl,optim['controlled']),('Natural',nat,optim['natural'])]):
        ax.plot([b*100,a*100],[i,i],c=GRAY,lw=.8)
        ax.scatter(a*100,i,c=BLUE,marker='D',s=25)
        ax.scatter(b*100,i,c=ORANGE,marker='x',s=30)
    ax.set_yticks([0,1],['Controlled','Natural']);ax.invert_yaxis();ax.set_ylim(1.5,-.5)
    ax.set_xlim(80,102);ax.set_xlabel('Triple F1 (%)');ax.set_title('Archived candidates (n = 225)')
    clean_axis(ax,'x')
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([],[],color=GRAY,marker='o',ls='',label='Raw candidate'),Line2D([],[],color=BLUE,marker='D',ls='',label='Gated pipeline'),Line2D([],[],color=ORANGE,marker='x',ls='',label='Sequential optimizer')],ncol=3,loc='upper center',bbox_to_anchor=(.5,1.13))
    for ax,label in zip(axes,'abc'):panel_label(ax,label,-.18)
    save_vector(fig,OUT/'experiments/matched_mechanisms.pdf')


def scaling():
    d=json.loads((DATA/'additional_checks.json').read_text())['diagnostic_scaling'];x=[r['triples'] for r in d]
    fig,axes=plt.subplots(1,2,figsize=(7.15,2.65),gridspec_kw={'wspace':.35})
    axes[0].plot(x,[r['full_diagnostic_ms'] for r in d],'o-',c=BLUE,label='Full batch')
    axes[0].plot(x,[r['one_doc_update_ms'] for r in d],'s-',c=GREEN,label='One-document update')
    axes[0].set_yscale('log');axes[0].set_ylabel('CPU time (ms; log scale)');axes[0].legend()
    axes[1].plot(x,[r['new_graph_alloc_peak_mb'] for r in d],'D-',c=ORANGE);axes[1].set_ylabel('New Python allocation (MiB)')
    for ax,label in zip(axes,'ab'):
        ax.set_xscale('log');ax.set_xticks(x,['1K','5K','10K','50K']);ax.set_xlabel('Triples in disjoint document batches');clean_axis(ax,'y');panel_label(ax,label,-.17)
    save_vector(fig,OUT/'experiments/diagnostic_scaling.pdf')

if __name__=='__main__':
    architecture()
    results=json.loads((DATA/'results.json').read_text());natural(results);mechanisms(results);scaling()
    print('Wrote executed-pipeline, natural-strata, scaling and (when complete) matched-result vector figures')
