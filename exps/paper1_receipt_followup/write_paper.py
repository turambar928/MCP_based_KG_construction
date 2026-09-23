"""Render the locked follow-up results without modifying primary measurements."""
import csv,json,sys
from collections import Counter
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
HERE=Path(__file__).resolve().parent

def pct(x):return f'{100*x:.2f}'
def main():
    dev=json.loads((HERE/'dev/results.json').read_text());test=json.loads((HERE/'test/results.json').read_text())
    assert test['complete'] and test['n_documents']==60
    rows={r['method']:r for r in test['summary']};d={r['method']:r for r in dev['summary']}
    original=rows['input'];base=rows['simple_gate'];index=rows['evidence_gate'];shacl=rows['shacl_gate']
    primary=test['primary_comparison']['triple_f1'];lo,hi=primary['ci']
    fields=list(csv.DictReader((HERE/'test/per_field.csv').open()))
    compare={(x['left'],x['right']):x for x in test['paired']}
    base_gain=compare['simple_gate','input']['triple_f1']
    cost={r['arm']:r for r in test['cost']}
    section=r'''\subsection{Field-Evidence Follow-up on New Documents}
\label{sec:eval:receipt_followup}

The first receipt study suggests that visible schema violations miss many
field-selection errors. Base and diagnostic prompts return all 60 input
graphs unchanged. Of 239 reference fields, 190 match exactly. The 49
mismatches include 27 case, spacing, punctuation, or amount-format differences,
ten span-boundary differences, eight different source values, and four values
absent from the normalized source. These categories describe reference
mismatches; they separate formatting from other repair targets.

We develop the field-evidence index in
Section~\ref{sec:framework:field_evidence} on 20 new receipts, then freeze it
before testing 60 further receipts. The original 60, development 20, and test
60 documents have disjoint IDs and no identical normalized transcripts.
The sample is fixed with seed 20260923. Test labels are downloaded only after
all test predictions are stored. Every arm receives the same field
definitions, numbered source lines, input graph, and instructions. Simple
uses these inputs directly; Evidence Index adds field anchors; SHACL adds
validation context. All three share the whitespace-consistent filter.

'''
    section+=f'''Development F1 is {pct(d['input']['triple_f1'])}\\% for the extracted graphs,
{pct(d['simple_gate']['triple_f1'])}\\% for Simple,
{pct(d['evidence_gate']['triple_f1'])}\\% for Evidence Index, and
{pct(d['shacl_gate']['triple_f1'])}\\% for SHACL. We retain one fixed index design
and all three arms for the test. The primary comparison, frozen with the code
and scoring rules, is Evidence Index minus Simple in document-mean triple F1.

'''
    section+=r'''\begin{table*}[t]
\centering
\caption{Frozen follow-up on 60 new receipts. All repair arms share field
 definitions and source lines. Gate uses consistent whitespace matching.
 Exact match is over annotated fields.}
\label{tab:receipt_followup}
\small
\begin{tabular}{lrrrr}
\toprule
Method & Triple F1 & Exact graph & Normalized F1 & Preservation \\
\midrule
'''
    labels={'input':'Extracted input','simple_raw':'Simple, raw','simple_gate':'Simple, gate',
            'evidence_raw':'Evidence Index, raw','evidence_gate':'Evidence Index, gate',
            'shacl_raw':'SHACL context, raw','shacl_gate':'SHACL context, gate'}
    for method,label in labels.items():
        r=rows[method];section+=f"{label} & {r['triple_f1']:.4f} & {r['exact_match']:.4f} & {r['normalized_f1']:.4f} & {r['clean_fact_preservation']:.4f} \\\\\n"
    section+=r'''\bottomrule
\end{tabular}
\end{table*}

'''
    section+=f'''On the new test, extracted graphs reach {pct(original['triple_f1'])}\\% F1.
Simple, Evidence Index, and SHACL with filtering reach
{pct(base['triple_f1'])}\\%, {pct(index['triple_f1'])}\\%, and {pct(shacl['triple_f1'])}\\%, respectively
(Table~\\ref{{tab:receipt_followup}}). Simple changes F1 by
${pct(base_gain['difference'])}$ points relative to the input
(95\\% CI: $[{pct(base_gain['ci'][0])}, {pct(base_gain['ci'][1])}]$).
The primary Evidence Index--Simple difference is
${pct(primary['difference'])}$ points (95\\% CI: $[{pct(lo)}, {pct(hi)}]$;
two-sided paired randomization $p={primary['paired_randomization_p']:.4f}$).
Exact graph match is {pct(base['exact_match'])}\\%, {pct(index['exact_match'])}\\%, and
{pct(shacl['exact_match'])}\\% for the three repair arms.

'''
    amounts=test['amount_value_accuracy']
    transitions=test['field_transitions']
    for method,label in [('simple_gate','Simple'),('evidence_gate','Evidence Index'),('shacl_gate','SHACL')]:
        values=[r for r in transitions if r['method']==method]
        repaired=sum(r['output_exact'] for r in values if r['initial_category']!='exact')
        total=sum(r['n'] for r in values if r['initial_category']!='exact')
        losses=sum(r['n']-r['output_exact'] for r in values if r['initial_category']=='exact')
        section+=f'{label} restores {repaired} of {total} initially non-exact field values and changes {losses} initially exact values to non-exact values.\n'
    by_category={r['initial_category']:r for r in transitions if r['method']=='evidence_gate'}
    loss_categories=Counter(r['output_category'] for r in fields if r['method']=='evidence_gate' and r['input_exact']=='True' and r['output_exact']=='False')
    section+=f'''The index restores {by_category['punctuation_only']['output_exact']} punctuation-only
differences and {by_category['span_boundary']['output_exact']} span-boundary differences.
Of its lost exact matches, {loss_categories['amount_surface_format']} preserve the numeric amount
but change its display format.
'''
    section+=f'''A separate numeric check removes currency prefixes and thousands separators
from the total field. Its accuracy is
{amounts['input']['correct']}/{amounts['input']['n']} for the input,
{amounts['simple_gate']['correct']}/{amounts['simple_gate']['n']} for Simple,
{amounts['evidence_gate']['correct']}/{amounts['evidence_gate']['n']} for Evidence Index, and
{amounts['shacl_gate']['correct']}/{amounts['shacl_gate']['n']} for SHACL.
This check distinguishes a changed amount from a changed display format.

Filtering rejects {test['rejected_candidate_occurrences']} candidate occurrence;
{test['reference_candidates_rejected']} rejected candidates match a reference value.
The rejected address joins source fragments into a span absent from the text.
Filtering changes Evidence Index F1 by
{pct(compare['evidence_gate','evidence_raw']['triple_f1']['difference'])} points
and leaves the other two arms unchanged.

The three arms change {test['changed_graphs']['simple']}, {test['changed_graphs']['evidence']}, and
{test['changed_graphs']['shacl']} of the 60 input graphs.
Mean repair request times are {cost['simple']['mean_wall_seconds']:.2f},
{cost['evidence']['mean_wall_seconds']:.2f}, and {cost['shacl']['mean_wall_seconds']:.2f} seconds,
with {cost['simple']['mean_input_tokens']:.0f}, {cost['evidence']['mean_input_tokens']:.0f}, and
{cost['shacl']['mean_input_tokens']:.0f} input tokens. The run contains
{sum(r['requests'] for r in test['cost'])} actual requests for 60 extraction and 180 repair outcomes.
Raw and gated scores share responses; request times include pacing and retries.

'''
    section+=r'''\begin{figure}[t]
\centering
\includegraphics[width=0.98\textwidth]{figure/experiments/receipt_followup.pdf}
\caption{Follow-up on new receipts. Left: mean triple F1 with 95\% document-bootstrap
intervals. Right: paired F1 changes; intervals resample whole documents.
All repair methods share field definitions and source lines.}
\label{fig:receipt_followup}
\end{figure}
'''
    (ROOT/'paper1/sections/receipt_followup.tex').write_text(section)
    abstract=r'''\abstract{
Knowledge graphs extracted from documents can contain missing fields and
incorrect values. We study repair using source text, a field schema, and a
language model. The pipeline normalizes the input, generates a candidate
graph, and checks its heads, relations, source spans, and field counts.
On 225 document graphs with 450 controlled defects, Diagnosis + Gate repairs
98.00\% of defects. On 225 actual extraction outputs, it raises triple F1
from 87.99\% to 92.48\%. Direct field copying recovers all references in this
serialized-record setting. We also study independently annotated receipt
transcripts. An initial 60-document test identifies field-selection and text
normalization errors. A follow-up uses 20 development documents and a frozen
60-document test to compare shared field definitions, a field-evidence index,
and SHACL context.
'''
    abstract+=f'''On this new test, extracted graphs reach {pct(original['triple_f1'])}\\% F1;
Simple, Evidence Index, and SHACL with filtering reach
{pct(base['triple_f1'])}\\%, {pct(index['triple_f1'])}\\%, and {pct(shacl['triple_f1'])}\\%.
The paired Evidence Index--Simple difference is {pct(primary['difference'])} points
(95\\% CI: {pct(lo)} to {pct(hi)}).
'''
    abstract+=r'''The matched comparisons measure the added effects of evidence context and
candidate filtering within schema-aware repair. Code, prompts, predictions, and annotation materials
are available for further evaluation.
}
\keywords{Knowledge Graph Repair, Source Grounding, Constraint Validation, Document Extraction}
'''
    (ROOT/'paper1/sections/abstract.tex').write_text(abstract)
    conclusion=r'''\section{Conclusion}
\label{sec:conclusion}

We studied document-graph repair through source-based generation and field
validation. The method combines structural normalization, optional diagnostic
context, one model call, and candidate filtering. On the Chinese record
benchmark, Diagnosis + Gate repairs 98.00\% of controlled defects and raises
F1 on extracted graphs from 87.99\% to 92.48\%. Direct field copying reaches
100\% on that source format.

Independent receipt text reveals different problems: field boundaries,
alternative source values, and inconsistent text normalization. We correct
whitespace handling and compare shared field definitions with an added
source-evidence index on new documents.
'''
    conclusion+=f'''On the frozen 60-document test, Simple, Evidence Index, and SHACL reach
{pct(base['triple_f1'])}\\%, {pct(index['triple_f1'])}\\%, and {pct(shacl['triple_f1'])}\\% F1,
compared with {pct(original['triple_f1'])}\\% for extracted inputs.
The paired index contribution is {pct(primary['difference'])} points, with a
95\\% interval from {pct(lo)} to {pct(hi)}.
'''
    conclusion+=r'''
These results distinguish the full schema-aware repair step from the added
effects of evidence context and filtering. Remaining work includes independent review
of sampled edits, relation-aware validation, and tests on a wider range of
document schemas.
'''
    (ROOT/'paper1/sections/conclusion.tex').write_text(conclusion)
    sys.path.insert(0,str(ROOT/'paper1'))
    from figure_style import apply_style,clean_axis,panel_label,save_vector,BLUE,GREEN,ORANGE,GRAY
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    apply_style();fig,axes=plt.subplots(1,2,figsize=(7.15,2.8),gridspec_kw={'wspace':.55})
    for i,(method,label,color) in enumerate([('input','Extracted input',GRAY),('simple_gate','Simple',BLUE),('evidence_gate','Evidence Index',GREEN),('shacl_gate','SHACL context',ORANGE)]):
        r=rows[method];value=r['triple_f1']*100;low,high=np.array(r['f1_ci'])*100
        axes[0].errorbar(value,i,xerr=[[value-low],[high-value]],fmt='o',color=color,capsize=2,markersize=4,lw=.8)
    axes[0].set_yticks(range(4),['Extracted input','Simple','Evidence Index','SHACL context']);axes[0].invert_yaxis();axes[0].set_xlabel('Triple F1 (%)');clean_axis(axes[0],'x')
    axes[1].axvline(0,c=GRAY,lw=.8,ls='--')
    pairs=[('simple_gate','input','Simple − input',BLUE),('evidence_gate','simple_gate','Index − simple',GREEN),('evidence_gate','shacl_gate','Index − SHACL',ORANGE)]
    for i,(a,b,label,color) in enumerate(pairs):
        r=compare[a,b]['triple_f1'];value=r['difference']*100;low,high=np.array(r['ci'])*100
        axes[1].errorbar(value,i,xerr=[[value-low],[high-value]],fmt='D',color=color,capsize=2,markersize=4,lw=.8)
    axes[1].set_yticks(range(3),[x[2] for x in pairs]);axes[1].invert_yaxis();axes[1].set_xlabel('Paired F1 difference (points)');clean_axis(axes[1],'x')
    panel_label(axes[0],'a',-.18);panel_label(axes[1],'b',-.18)
    save_vector(fig,ROOT/'paper1/figure/experiments/receipt_followup.pdf')
    print('Wrote follow-up section, abstract, conclusion, and Times New Roman vector figure.')
if __name__=='__main__':main()
