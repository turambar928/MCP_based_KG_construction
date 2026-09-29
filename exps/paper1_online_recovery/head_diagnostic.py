"""Post-hoc document-ID error attribution on the same responses; no model calls."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_online_recovery.analyze_reextraction import HERE,SOURCE,compatibility,read,score_case,filter_response,paired,write_csv

def main():
 rows=read(HERE/'predictions.jsonl');inputs={r['case_id']:r for r in read(SOURCE/'inputs.jsonl')};refs={r['case_id']:r for r in read(SOURCE/'references.jsonl')};initial={r['case_id']:r['triples'] for r in read(SOURCE/'extraction.jsonl')};per=[];audit=[]
 for r in rows:
  cid=r['case_id'];ts,status,_=compatibility(r['raw_response']);head=inputs[cid]['required_document_node'];bad=sum(t['head']!=head for t in ts)
  normalized=[dict(t,head=head) for t in ts];out,_=filter_response(inputs[cid],normalized)
  per.append({'case_id':cid,'method':r['arm']+'_gate',**score_case(initial[cid],out,refs[cid])});audit.append({'case_id':cid,'arm':r['arm'],'wrong_head_triples':bad,'wrong_head_graph':int(bad>0)})
 summary=[]
 for arm in sorted({r['arm'] for r in rows}):
  rs=[r for r in per if r['method']==arm+'_gate'];aa=[r for r in audit if r['arm']==arm]
  summary.append({'arm':arm,'f1_head_normalized':float(np.mean([r['triple_f1'] for r in rs])),'normalized_f1_head_normalized':float(np.mean([r['normalized_f1'] for r in rs])),'wrong_head_graphs':sum(r['wrong_head_graph'] for r in aa),'wrong_head_triples':sum(r['wrong_head_triples'] for r in aa)})
 result={'status':'Post-hoc error attribution, not the frozen primary or a new model run.','operation':'Set every returned head to the public required_document_node before the same filter; keep relations/tails/order unchanged, applied uniformly to all four arms.','summary':summary,'paired':paired(per,'repair_index_gate','extract_index_gate')}
 (HERE/'head_diagnostic.json').write_text(json.dumps(result,indent=2)+'\n');write_csv(HERE/'head_diagnostic_cases.csv',per);write_csv(HERE/'head_errors.csv',audit);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
