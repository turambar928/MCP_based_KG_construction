"""Generate the held-out contract table and vector plot from scored outputs."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent


def publish():
    r=json.loads((HERE/'test_results.json').read_text())
    rows=list(csv.DictReader((HERE/'test_per_document.csv').open()))
    names={'initial':'Initial extraction','repair_simple':'Simple repair','repair_index':'Indexed repair','extract_index':'Indexed re-extraction'}
    plt.rcParams.update({'font.family':'Times New Roman','font.size':10,'pdf.fonttype':42,
                         'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(6.2,2.7))
    for i,(arm,name) in enumerate(names.items()):
        values=np.array([float(x['f1'])*100 for x in rows if x['arm']==arm]);rng=np.random.default_rng(20260929)
        low,high=np.quantile(values[rng.integers(0,len(values),(10000,len(values)))].mean(1),[.025,.975])
        color='#B8753C' if arm=='repair_index' else '#386888'
        ax.errorbar(values.mean(),i,xerr=[[values.mean()-low],[high-values.mean()]],fmt='o',color=color,capsize=3,markersize=5,lw=1.3)
        ax.annotate(f'{values.mean():.2f}',(high,i),xytext=(7,0),textcoords='offset points',va='center',fontsize=9,color=color)
    ax.set_yticks(range(4),list(names.values()));ax.invert_yaxis();ax.set_xlabel('Document mean F1 (%) with 95% bootstrap interval')
    ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True);ax.margins(x=.25);fig.tight_layout()
    dest=ROOT/'paper1/figure/experiments'
    for ext in ['pdf','svg']:fig.savefig(dest/('cuad_contracts.'+ext),bbox_inches='tight')
    svg=dest/'cuad_contracts.svg';svg.write_text('\n'.join(x.rstrip() for x in svg.read_text().splitlines())+'\n');plt.close(fig)
    n=r['documents'];p=r['primary'];s=r['summary'];calls=sum(v['actual_requests'] for v in s.values())
    lines=[r'\subsection{Transfer to Contract Fields}',r'\label{sec:eval:cuad}',
           r'We construct a source-span field task from CUAD~\citep{ref_cuad}. Its five fields are document name, agreement date, effective date, expiration date or initial term, and governing law. Contracts must contain at most one distinct whitespace-normalized reference value per field and no more than 40,000 source characters. We retain the full source and verify annotation offsets. Twenty official-training contracts form the development set. The fixed eligibility conditions yield '+str(n)+r' official-test contracts; we use all of them. This evaluates shorter, single-value contracts rather than the full CUAD question-answering task.',
           r'The four outputs are initial extraction, simple repair, indexed repair, and indexed re-extraction. Both repair arms receive the same initial graph. Indexed arms add deterministic field-anchor windows while retaining the full source. All arms use the same Gemma model, field definitions and 4,000-token completion limit. Before collection, we fix JSON-fence handling and assign document IDs by code. We use one development round without changing prompts or eligibility before testing. This comparison isolates source context and access to an old graph; it does not evaluate the sequential selector.',
           r'\begin{table}[t]',r'\centering',r'\caption{CUAD contract-field results on '+str(n)+r' test documents. F1 uses whitespace-normalized exact source spans. Lost counts reference-correct initial facts removed from the output. Initial creation cost is separate from each repair call.}',r'\label{tab:cuad}',r'\small',r'\begin{tabular}{lrrrr}',r'\toprule',r'Output & F1 (\%) & Lost & New incorrect & Requests \\',r'\midrule']
    for a,name in names.items():
        v=s[a];lines.append(f"{name} & {v['f1']*100:.2f} & {v['lost_initial_correct']} & {v['new_incorrect']} & {v['actual_requests']} " + chr(92)*2)
    lines += [r'\bottomrule',r'\end{tabular}',r'\end{table}',
              f"The primary paired indexed-repair minus indexed-extraction difference is {p['difference_pp']:.2f} F1 points (95\\% document-bootstrap interval [{p['ci95_pp'][0]:.2f}, {p['ci95_pp'][1]:.2f}]; paired sign-flip $p={p['p_sign_flip']:.3f}$). The test produces {4*n} outputs from {calls} actual requests including retries. Failed outputs remain empty graphs in scoring. Exact source-span agreement measures agreement with CUAD annotations; independent semantic review of edits remains pending.",
              r'\begin{figure}[t]',r'\centering',r'\includegraphics[width=0.88\textwidth]{figure/experiments/cuad_contracts.pdf}',
              r'\caption{Contract-field comparison. Points are document mean F1; bars are marginal 95\% document-bootstrap intervals. The primary comparison uses a paired interval reported in the text.}',r'\label{fig:cuad}',r'\end{figure}']
    (ROOT/'paper1/sections/cuad_contracts.tex').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':publish()
