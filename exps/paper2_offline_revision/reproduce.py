"""Offline reproduction; default uses archived checkpoints, --train resumes training."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--train',action='store_true');p.add_argument('--workers',type=int,default=4);args=p.parse_args()
    def run(*argv):subprocess.run([sys.executable,*argv],cwd=ROOT,check=True)
    run('-m','unittest','exps.paper2_offline_revision.test_policy','exps.paper2_offline_revision.test_rules')
    base='exps/paper2_offline_revision/'
    if args.train:run(base+'policy_study.py','train','--workers',str(args.workers))
    run(base+'policy_study.py','evaluate');run(base+'analyze_policy.py');run(base+'rule_study.py')
    run(base+'make_tables.py');run(base+'make_figures.py');run(base+'verify.py')
if __name__=='__main__':main()
