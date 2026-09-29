"""Publish current v2 table; historical experiments and plots remain archived."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'results.json').read_text());m=json.loads((HERE/'manifest.json').read_text())
labels=['Always-on uniform','Learned prior, always on','Learned prior and trigger','No prior penalty','No action cost','No density bound','No quality bounds','One iteration','No rule candidates','Rule candidates only','No local score/bounds','No graph score/bound','No source score/bound']
lines=[r'\paragraph{Current sequential optimizer components.}',
r'We replay the current version-2 selector on fixed proposals for 225 controlled and 225 natural inputs. Thirteen settings give 5,850 outcomes under the default absolute prior. Repeating all settings with the relative-to-uniform offset gives 5,850 sensitivity outcomes. Both use the shared \texttt{public-profile-v2} features and retrained router; the earlier version-1 files remain in the archive. The main one-call results are separate from this selector study.',
r'The reference uses an always-on uniform prior. Each setting changes its named component; the trigger comparison instead uses the always-on learned prior as its reference. Score removals zero the named terms and remove their bounds without rescaling other weights. Detectors and hard-violation rewards stay active. Removing rule candidates excludes both detector actions and explicit source-field additions, while retaining diagnostic profiles and the fixed model proposals.',
r'\begin{table}[t]',r'\centering',r'\caption{Current version-2 optimizer, default absolute prior. Accepted counts are actions or bundles, shown as controlled / natural. Each F1 averages 225 documents.}',r'\label{tab:optimizer_complete}',r'\small',r'\begin{tabular}{lrrr}',r'\toprule',r'Setting & Controlled F1 & Natural F1 & Accepted \\',r'\midrule']
for v,label in zip(m['variants'],labels):
 a=next(s for s in r['summary'] if s['prior']=='absolute_primary' and s['cohort']=='controlled' and s['variant']==v);b=next(s for s in r['summary'] if s['prior']=='absolute_primary' and s['cohort']=='natural' and s['variant']==v)
 lines.append(f"{label} & {a['triple_f1']:.4f} & {b['triple_f1']:.4f} & {a['applied']} / {b['applied']} \\\\")
lines += [r'\bottomrule',r'\end{tabular}',r'\end{table}',
r'The default uniform selector reaches 84.72\% F1 on controlled inputs and accepts no edits. Removing action cost raises F1 to 89.30\%, with 68 accepted actions. On natural inputs, the uniform reference reaches 88.33\%; the learned prior and trigger reach 87.99\%. No setting loses an initially correct reference fact in either cohort. The learned router therefore shows no consistent repair benefit here. Per-document contrasts, candidate trials, rejection reasons, and stop reasons are released. Holm correction covers the 24 component comparisons separately for each prior offset.',
r'\paragraph{Router training and prior sensitivity.}',
r'The version-2 router uses an $8\!\rightarrow\!32\!\rightarrow\!16$ network with one repair output and three scope outputs (884 parameters). The scaler is fitted on 2,098 training rows; validation and test each have 450 rows, grouped by document. Controlled repair and scope classification both reach 100\%. These supervised labels follow the injected defects and measure their recognition.',
r'\input{sections/math_revision_table}',
r'Table~\ref{tab:math_revision_selector} shows the four router/offset combinations from the earlier v2 check, also covered by the expanded replay. With the learned prior, the relative offset raises controlled F1 from 84.72\% to 89.29\%, while natural-input F1 falls from 87.99\% to 87.64\%. The uniform alternatives give identical outputs. The default remains unchanged. These previously evaluated proposals allow an execution comparison, not a new holdout evaluation.']
(ROOT/'paper1/sections/v2_ablation.tex').write_text('\n\n'.join(lines)+'\n')
p=ROOT/'paper1/sections/ablation_offline.tex';s=p.read_text();start=s.index(r'\paragraph{Sequential optimizer components.}') if r'\paragraph{Sequential optimizer components.}' in s else s.index(r'\input{sections/v2_ablation}')
p.write_text(s[:start]+r'\input{sections/v2_ablation}'+'\n')
