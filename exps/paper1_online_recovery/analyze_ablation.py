"""Verify recovered outcomes, then execute the unchanged frozen statistical analysis."""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_online_recovery.run import freeze,read,payload,identify,MODEL
from exps.paper1_mechanism_audit.protocol import digest
from exps.paper1_repair_benchmark.run_benchmark import parse_triples
from exps.paper1_ablation_completion import analyze

def main():
 dest,tasks=freeze('ablation');rows=read(dest/'predictions.jsonl');expected={identify(r,'ablation'):r for r in tasks}
 assert len(rows)==len(expected)==840 and len({identify(r,'ablation') for r in rows})==840
 for row in rows:
  task=expected[identify(row,'ablation')]
  assert row['model']==MODEL and row['request_sha256']==digest(payload(task,'ablation'))
  if row['status']=='ok':
   assert row['returned_model']==MODEL
   ts,status=parse_triples(row['raw_response']);assert ts==row['triples'] and status=='ok'
  else:assert row['triples']==[]
  # Frozen analyzer uses zero for absent usage: refuse it if usage is missing.
  for key in ['prompt_tokens','completion_tokens']:assert isinstance(row['usage'].get(key),(int,float)), 'Missing usage requires a separate missing-aware cost analysis'
 source=ROOT/'exps/paper1_ablation_completion'
 for name in ['inputs.jsonl','prompts.jsonl']:
  target=dest/name
  if target.exists():assert target.read_bytes()==(source/name).read_bytes()
  else:shutil.copyfile(source/name,target)
 analyze.HERE=dest;analyze.main()
 (dest/'validation.json').write_text(json.dumps({'outcomes':840,'frozen_payload_hashes_match':True,'raw_parse_agreement':True,'usage_present_all_outcomes':True,'model':MODEL,'source_analyzer_sha256':hashlib.sha256(Path(analyze.__file__).read_bytes()).hexdigest()},indent=2)+'\n')
if __name__=='__main__':main()
