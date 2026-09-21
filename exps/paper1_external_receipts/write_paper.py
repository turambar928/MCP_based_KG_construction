"""Generate receipt tables/figure and the concise abstract from completed results."""
import json
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
HERE=Path(__file__).resolve().parent

def pct(v):return f'{100*v:.2f}'

def main():
    result=json.loads((HERE/'results.json').read_text());assert result['complete']
    sensitivity=json.loads((HERE/'whitespace_sensitivity.json').read_text())
    ws={r['arm']:r for r in sensitivity['results']}
    rows={r['method']:r for r in result['summary']}
    original=rows['input'];base=rows['base_gate'];diag=rows['diagnosis_gate'];shacl=rows['shacl_context_gate']
    comparisons={(x['left'],x['right']):x for x in result['paired']}
    difference=comparisons['diagnosis_gate','base_gate']['triple_f1']
    delta=difference['difference'];lo,hi=difference['ci']
    labels={'input':'Extracted input','rule_only':'Rule Only','source_field_copy':'Source-field Copy',
        'base_raw':'Base, raw','base_gate':'Base, gate','diagnosis_raw':'Diagnostic, raw','diagnosis_gate':'Diagnostic, gate',
        'shacl_context_raw':'SHACL context, raw','shacl_context_gate':'SHACL context, gate'}
    section=r'''\subsection{External Receipt Text}
\label{sec:eval:external_receipts}

We use SROIE receipt transcriptions and human key-information labels
\citep{ref_sroie2019} to test repair outside the Chinese record collections.
A fixed random sample contains 60 of the 626 documents in the
community-corrected trainval mirror (seed 20260922). Text lines are joined
in their stored order. The model receives this text and the four field
names: company, date, address, and total. Field values are read separately
by the scorer. One receipt lacks an address annotation, giving 239 evaluated
fields; the missing annotation is excluded from scoring for every method.
All four fields remain available to the model.

A Gemma call first extracts each graph. The three repair contexts then
receive the same extracted graph, using the settings in
Section~\ref{sec:impl:enhancement}. Sampling and settings were fixed before
inference. This gives 60 extraction calls and 180 repair outcomes, each of
which is scored before and after filtering. We reuse the source-copy and
structural baselines without receipt-specific tuning. The primary score
uses exact triple matching. A secondary score ignores case and whitespace
in field values to separate these formatting differences from other errors.

\begin{table*}[t]
\centering
\caption{External SROIE results on 60 receipt transcripts. Exact match is over
annotated fields. Normalized F1 ignores case and whitespace in values.}
\label{tab:external_receipts}
\small
\begin{tabular}{lrrrr}
\toprule
Method & Triple F1 & Exact match & Normalized F1 & Preservation \\
\midrule
'''
    for method,label in labels.items():
        row=rows[method]
        section+=f"{label} & {row['triple_f1']:.4f} & {row['exact_match']:.4f} & {row['normalized_f1']:.4f} & {row['clean_fact_preservation']:.4f} \\\\\n"
    section+=r'''\bottomrule
\end{tabular}
\end{table*}

'''
    section+=f'''The extracted graphs reach {pct(original['triple_f1'])}\\% F1.
After filtering, base, diagnostic, and SHACL contexts reach
{pct(base['triple_f1'])}\\%, {pct(diag['triple_f1'])}\\%, and {pct(shacl['triple_f1'])}\\%, respectively
(Table~\\ref{{tab:external_receipts}}). The diagnostic--base difference is
${pct(delta)}$ points (95\\% CI: $[{pct(lo)}, {pct(hi)}]$;
paired randomization $p={difference['paired_randomization_p']:.4f}$).
The field-copy parser reaches {pct(rows['source_field_copy']['triple_f1'])}\\% F1 on these transcripts,
compared with 100\\% on the serialized records.

Of the 239 reference values, 220 occur literally in the transcripts.
The other 19 values are absent as exact source strings.
Across the 180 repair responses, filtering rejects {result['rejected_candidates']} candidate occurrences,
all matching a reference value. They concern the same address in three arms:
the source contains a double space, while the JSON parser collapses candidate
whitespace. A post-run check applies the same whitespace normalization to the
source and retains this address in all three arms. With the original responses,
F1 becomes {pct(ws['base']['triple_f1'])}\\% for base and diagnostic contexts
and {pct(ws['shacl_context']['triple_f1'])}\\% for SHACL context; exact graph
match remains {pct(ws['base']['exact_match'])}\\%. The main table keeps the fixed
protocol results, and the separate check identifies the effect of this
normalization mismatch.

'''
    cost={r['arm']:r for r in result['cost']}
    section+=f'''The run contains {sum(r['calls'] for r in result['cost'])} recorded requests,
including retries, and {result['status_counts'].get('ok',0)} successfully parsed outcomes.
Mean repair request times are {cost['base']['mean_wall_seconds']:.2f},
{cost['diagnosis']['mean_wall_seconds']:.2f}, and {cost['shacl_context']['mean_wall_seconds']:.2f} seconds
for base, diagnostic, and SHACL contexts. Their mean input lengths are
{cost['base']['mean_input_tokens']:.0f}, {cost['diagnosis']['mean_input_tokens']:.0f}, and
{cost['shacl_context']['mean_input_tokens']:.0f} tokens. These times include
request pacing and exclude shared extraction and context preparation.

'''
    section+=r'''\begin{figure}[t]
\centering
\includegraphics[width=0.98\textwidth]{figure/experiments/external_receipts.pdf}
\caption{Repair on independent receipt text. Points show mean triple F1 and
95\% document-bootstrap intervals. Raw and gated results share model responses;
the dashed line marks the extracted input.}
\label{fig:external_receipts}
\end{figure}
'''
    (ROOT/'paper1/sections/external_receipts.tex').write_text(section)
    abstract=r'''\abstract{
Knowledge graphs extracted from documents can contain missing fields and
incorrect values. We study repair using the source text, a declared field
schema, and a language model. The pipeline normalizes the input graph,
generates a complete candidate graph, and checks its heads, relations,
source spans, and field counts. Experiments separate the effects of diagnostic
context and candidate filtering by sharing instructions and scoring each
response before and after validation. On 225 document graphs with 450
controlled defects, Diagnosis + Gate repairs 98.00\% of defects. On 225 actual
extraction outputs, it raises triple F1 from 87.99\% to 92.48\%. A source-field
parser recovers all references in this serialized-record setting.
We therefore also evaluate 60 independently annotated SROIE receipt transcripts.
'''
    abstract+=f'''Their extracted graphs reach {pct(original['triple_f1'])}\\% F1;
base, diagnostic, and SHACL contexts with filtering reach
{pct(base['triple_f1'])}\\%, {pct(diag['triple_f1'])}\\%, and {pct(shacl['triple_f1'])}\\%.
'''
    abstract+=r'''The matched results show that added diagnostic context is not consistently
helpful. The results also show how source format and text normalization affect
repair scores. Code, prompts, predictions, and
annotation materials are available for further evaluation.
}
\keywords{Knowledge Graph Repair, Source Grounding, Constraint Validation, Document Extraction}
'''
    (ROOT/'paper1/sections/abstract.tex').write_text(abstract)
    conclusion=r'''\section{Conclusion}
\label{sec:conclusion}

We studied document-graph repair through source-based candidate generation
and field validation. The pipeline combines structural normalization, an
optional diagnostic report, one model call, and a deterministic filter.
Matched comparisons separate the effects of context and filtering.

On the Chinese record benchmark, Diagnosis + Gate repairs 98.00\% of
controlled defects and improves naturally extracted graphs from 87.99\% to
92.48\% F1. Direct field copying reaches 100\% on the serialized source format.
The external receipt test adds independent text and human field labels.
'''
    conclusion+=f'''Base, diagnostic, and SHACL contexts with filtering reach
{pct(base['triple_f1'])}\\%, {pct(diag['triple_f1'])}\\%, and {pct(shacl['triple_f1'])}\\% F1
on 60 receipts, compared with {pct(original['triple_f1'])}\\% for the extracted inputs.
'''
    conclusion+=r'''
These results show that diagnostic prompts, candidate generation, and
validation should be assessed separately. More context does not consistently
improve repair. Consistent source and candidate normalization prevents
avoidable rejection of valid fields. The next steps are to complete independent review of
sampled edits and test relation-aware checks across a wider range of documents.
'''
    (ROOT/'paper1/sections/conclusion.tex').write_text(conclusion)
    sys.path.insert(0,str(ROOT/'paper1'))
    from figure_style import apply_style, clean_axis, panel_label, save_vector, BLUE, GREEN, GRAY
    import matplotlib.pyplot as plt
    apply_style()
    fig,axes=plt.subplots(1,2,figsize=(7.15,2.7),gridspec_kw={'wspace':.5})
    for ax,metric,title in zip(axes,['triple_f1','normalized_f1'],['Exact-value scoring','Case/space-normalized scoring']):
        for i,arm in enumerate(['base','diagnosis','shacl_context']):
            for post,color,marker,shift in [('raw',GRAY,'o',-.09),('gate',BLUE,'D',.09)]:
                row=rows[arm+'_'+post];value=row[metric]*100
                low,high=np.array(row['f1_ci' if metric=='triple_f1' else 'normalized_f1_ci'])*100
                ax.errorbar(value,i+shift,xerr=[[value-low],[high-value]],fmt=marker,color=color,markersize=4,capsize=2,lw=.8,label=post if i==0 else None)
        ax.axvline(original[metric]*100,color=GREEN,ls='--',lw=1,label='Extracted input')
        ax.set_yticks([0,1,2],['Base','Diagnostic','SHACL context']);ax.invert_yaxis();ax.set_xlabel('Triple F1 (%)');ax.set_title(title);clean_axis(ax,'x')
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([],[],color=GRAY,marker='o',ls='',label='Raw response'),Line2D([],[],color=BLUE,marker='D',ls='',label='Filtered response'),Line2D([],[],color=GREEN,ls='--',label='Extracted input')],ncol=3,loc='upper center',bbox_to_anchor=(.5,1.12))
    for ax,label in zip(axes,'ab'):panel_label(ax,label,-.18)
    save_vector(fig,ROOT/'paper1/figure/experiments/external_receipts.pdf')
    print('Wrote receipt section, vector figure, abstract and conclusion.')

if __name__=='__main__':main()
