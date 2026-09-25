"""Explicit offline reproduction; never invokes archived network runners."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent

def run(*args):
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    subprocess.run(args,cwd=ROOT,env=env,check=True)

def py(path,*args):run(sys.executable,str(HERE/path),*args)

def verify():
    m=json.loads((HERE/'manifest.json').read_text())
    for p,h in m['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    py('test_revision.py')
    p=json.loads((HERE/'paper2/policy_analysis.json').read_text())
    assert p['completed_training_runs']==60 and p['completed_training_episodes']==15000 and p['api_calls']==0
    print('Source hashes, regression tests and completed training inventory verified.')

def replay():
    py('paper1/study.py','evaluate');py('paper1/study.py','replay')
    py('paper2/policy_study.py','evaluate');py('paper2/analyze.py');py('paper2/rule_bridge.py')

def publish():
    py('publish.py','paper1');py('publish.py','paper2')
    for paper in ['paper1','paper2']:run('tectonic','-X','compile',f'{paper}/main.tex','--only-cached','--keep-logs')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['verify','replay','train','publish']);parser.add_argument('--workers',type=int,default=4);a=parser.parse_args()
    if a.mode=='verify':verify()
    elif a.mode=='publish':publish()
    elif a.mode=='replay':replay()
    else:
        py('paper1/study.py','build');py('paper1/router/train.py')
        py('paper2/policy_study.py','train','--workers',str(a.workers));replay()
if __name__=='__main__':main()
