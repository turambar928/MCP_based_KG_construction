import itertools,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_rate_ablation.protocol import *
from exps.paper1_ablation_completion.analyze import holm,write_csv
METRICS=['fact_f1','invalid_relation_repair_rate','correct_fact_preservation','accounted_calls','invalid_actions','final_joint','auc18','lost_initial_correct_facts']
def stats(a):
 a=np.asarray(a,float);rng=np.random.default_rng(42);boot=a[rng.integers(len(a),size=(10000,len(a)))].mean(1)
 vals=(np.array(list(itertools.product([-1,1],repeat=len(a))))*a).mean(1)
 return {'difference':float(a.mean()),'ci_low':float(np.quantile(boot,.025)),'ci_high':float(np.quantile(boot,.975)),'p':float(np.mean(abs(vals)>=abs(a.mean())-1e-12))}
def main():
 freeze();rows=json.loads((HERE/'results.json').read_text());means=[]
 for p in POLICIES:
  for run in range(10):
   rs=[r for r in rows if r['policy']==p and r['run_seed']==run];assert len(rs)==30
   means.append({'policy':p,'run_seed':run,**{k:float(np.mean([r[k] for r in rs])) for k in METRICS}})
 summary=[]
 for p in POLICIES:
  rs=[r for r in means if r['policy']==p];summary.append({'policy':p,**{k:float(np.mean([r[k] for r in rs])) for k in METRICS},'f1_seed_sd':float(np.std([r['fact_f1'] for r in rs],ddof=1))})
 contrasts=[]
 for p in POLICIES[1:]:
  for k in METRICS[:2]:
   a=[next(r[k] for r in means if r['policy']==p and r['run_seed']==s)-next(r[k] for r in means if r['policy']=='ddqn_scaled' and r['run_seed']==s) for s in range(10)]
   contrasts.append({'policy':p,'baseline':'ddqn_scaled','metric':k,**stats(a)})
 holm(contrasts);dump(HERE/'analysis.json',{'summary':summary,'contrasts':contrasts,'unit':'10 training seed means over 30 shared scenarios','api_calls':0})
 write_csv(HERE/'summary.csv',summary);write_csv(HERE/'seed_means.csv',means);write_csv(HERE/'contrasts.csv',contrasts)
 lines=['# Paper2 当前 rate 奖励组件消融','','50 次新训练 × 250 episodes，10 个既有完整 DDQN 模型作为配对基线；7 策略 × 10 种子 × 30 扰动 = 2,100 次评估。','', '这些是同一个 450 文档基础图的新扰动，不是未见文档、自然缺陷或生成规则参与训练的证据。','','|策略|Fact F1|关系恢复率|保持率|计账调用|不可用动作|','|---|---:|---:|---:|---:|---:|']
 for r in summary:lines.append(f"|{r['policy']}|{r['fact_f1']:.5f}|{r['invalid_relation_repair_rate']:.5f}|{r['correct_fact_preservation']:.5f}|{r['accounted_calls']:.2f}|{r['invalid_actions']:.2f}|")
 lines+=['','小计数系数 = '+str(calibration()['coefficient'])+'，仅由 20 个开发场景的随机可行动作轨迹校准，不使用参考事实或测试结果选择。','', '调用数为环境计账；实际 API 调用为 0。统计单位是训练种子（每个种子先平均 30 场景），12 个预定 F1／恢复率比较统一 Holm 校正。完整逐步图差分、动作、观测、奖励及模型权重均已保存。']
 (HERE/'report_zh.md').write_text('\n'.join(lines)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
