"""Paper2-only publication artifacts from frozen audit and test outputs."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'paper1'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from figure_style import apply_style
from exps.paper2_offline_revision.make_tables import table
HERE=Path(__file__).resolve().parent
NAMES={'ddqn_raw':'DDQN (count)','ddqn_scaled':'DDQN (rate)','ddqn_zero':'DDQN (zero)',
 'dqn_scaled':'DQN (rate)','risk_ridge':'One-step ridge','acquire_then_deficit':'Acquire + deficit',
 'rule_first_valid':'Rule-first valid','random_valid':'Random valid'}
COLORS=['#775B91','#326C99','#B96732','#467D64','#65727E']

def save(fig,name):
    dest=ROOT/'paper2/figure/experiments'
    for ext in ['pdf','svg','png']:fig.savefig(dest/f'{name}.{ext}',bbox_inches='tight',dpi=220)
    p=dest/f'{name}.svg';p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n');plt.close(fig)

def main():
    apply_style();analysis=json.loads((HERE/'test/analysis.json').read_text());audit=json.loads((HERE/'audit_summary.json').read_text())
    s={r['policy']:r for r in analysis['summary']};rs=[]
    seed_rows=list(csv.DictReader((HERE/'test/seed_means.csv').open()))
    for n,r in s.items():
        rs.append([NAMES[n],f"${100*r['fact_f1']:.2f}\\pm{100*r['fact_f1_std']:.2f}$",
            f"${100*r['invalid_relation_repair_rate']:.2f}\\pm{100*r['invalid_relation_repair_rate_std']:.2f}$",
            f"{100*r['correct_fact_preservation']:.2f}",f"{r['new_violations']:.2f}",f"{r['accounted_calls']:.2f}",f"{r['discounted_return']:.4f}"])
    table('reward_validation','Reward validation on thirty unseen corruption scenarios of the same base graph. Means and standard deviations are over ten run-seed means. F1 uses unique reference triples; restoration requires the original erroneous edge to regain its reference relation. All returns use the rate penalty.','tab:reward_validation','lrrrrrr',
        ['Policy','Triple F1 (\\%)','Restored (\\%)','Preserved (\\%)','New viol.','Calls','Return'],rs,wide=True)
    tests=[]
    for r in analysis['comparisons']:
        tests.append([NAMES[r['right']], 'Triple F1' if r['metric']=='fact_f1' else 'Restoration',
            f"{100*r['difference']:+.3f}",f"$[{100*r['ci_low']:+.3f},{100*r['ci_high']:+.3f}]$",f"{r['p_holm']:.4f}"])
    table('reward_validation_tests','DDQN with rate penalty minus comparator, in percentage points. Intervals resample ten run-seed means; each mean covers the same thirty scenarios. Exact sign-randomization tests are Holm-adjusted over eight contrasts.','tab:reward_validation_tests','llrrr',
        ['Comparator','Metric','Difference','95\\% interval','Holm $p$'],tests,wide=True)
    kernel=audit['kernel_probes'];labels=['Quality gain','Edit cost','Count penalty','Rate penalty']
    vals=[np.mean([r['first']['reward_components']['quality_gain'] for r in kernel]),
          np.mean([r['first']['reward_components']['edits'] for r in kernel]),
          -np.mean([r['first']['safety_penalties']['raw'] for r in kernel]),
          -np.mean([r['first']['safety_penalties']['scaled'] for r in kernel])]
    fig,axs=plt.subplots(1,2,figsize=(7.15,2.8),layout='constrained')
    axs[0].barh(range(4),vals,color=[COLORS[1],COLORS[4],COLORS[2],COLORS[3]])
    axs[0].set_yticks(range(4),labels);axs[0].invert_yaxis();axs[0].axvline(0,color='#777777',lw=.7);axs[0].set_xlabel('Mean reward component')
    axs[0].set_title('(a) First relation-repair action',loc='left')
    x=np.arange(3);w=.34
    first=[np.mean([r['first']['counterfactual_rewards'][m] for r in kernel]) for m in ['raw','scaled','zero']]
    two=[np.mean([r['two_step_returns'][m] for r in kernel]) for m in ['raw','scaled','zero']]
    axs[1].bar(x-w/2,first,w,label='Relation repair',color=COLORS[1]);axs[1].bar(x+w/2,two,w,label='Repair then deduplicate',color=COLORS[3])
    axs[1].axhline(0,color='#777777',lw=.7);axs[1].set_xticks(x,['Count','Rate','Zero']);axs[1].set_ylabel('Discounted return');axs[1].legend(fontsize=7,frameon=False)
    axs[1].set_title('(b) One- and two-action returns',loc='left')
    save(fig,'reward_action_audit')
    fig,axs=plt.subplots(1,2,figsize=(7.15,3.0),layout='constrained')
    names=['ddqn_raw','ddqn_scaled','ddqn_zero','risk_ridge','acquire_then_deficit']
    for i,n in enumerate(names):
        r=s[n];points=[100*float(v['invalid_relation_repair_rate']) for v in seed_rows if v['policy']==n]
        axs[0].barh(i,100*r['invalid_relation_repair_rate'],color=COLORS[i],height=.58,alpha=.16)
        axs[0].scatter(points,i+np.linspace(-.15,.15,10),s=14,color=COLORS[i],alpha=.55,zorder=3)
        axs[0].scatter(100*r['invalid_relation_repair_rate'],i,s=32,color=COLORS[i],marker='D',edgecolor='white',lw=.5,zorder=4)
        axs[0].text(104,i,f"{100*r['invalid_relation_repair_rate']:.1f}%",ha='left',va='center',fontsize=7,color='#17212B')
        axs[1].scatter(r['new_violations'],r['remaining_invalid_relation'],color=COLORS[i],s=36,label=NAMES[n],marker=['o','s','^','D','v'][i])
    axs[0].set_yticks(range(len(names)),[NAMES[n] for n in names]);axs[0].invert_yaxis();axs[0].set(xlim=(-3,120),xlabel='Original invalid relations restored (%)');axs[0].set_xticks([0,25,50,75,100]);axs[0].set_title('(a) Repair completion across seeds',loc='left')
    axs[1].set(xlabel='Introduced structural violations',ylabel='Remaining invalid relations (log scale)',yscale='log',ylim=(.4,100))
    axs[1].set_yticks([.5,1,3,10,60],['0.5','1','3','10','60']);axs[1].minorticks_off()
    axs[1].legend(fontsize=6.8,frameon=False,loc='upper right');axs[1].set_title('(b) Structural effects',loc='left')
    for ax in axs:ax.grid(axis='x',alpha=.15)
    save(fig,'reward_validation')
    report=['# Paper2 奖励与修复行为验证结果','',
      '保持 RL 与双策略生成主线；本实验不改 Paper1，不调用 API，不下载模型。新测试仅是同一基础图的未见扰动，不是新文档或自然错误测试。',
      '', '## 审计结论','',
      f"重放 {audit['replayed_trajectories']} 条旧轨迹，检查 {audit['one_step_branches']} 个可行动作分支。关系恢复产生的新增违规均须按日志类别解释，不能等同于新增错误事实。",
      f"在十个旧场景的统一操作探针中，第一次关系恢复平均质量增益为 {vals[0]:.6f}；原计数惩罚为 {vals[2]:.6f}，固定初始规模的比率惩罚为 {vals[3]:.6f}。",
      '', '## 测试结果','', '| 策略 | 参考三元组 F1 | 非法关系恢复率 | 正确事实保留 | 新违规 | 计账调用 |','|---|---:|---:|---:|---:|---:|']
    for n,r in s.items():report.append(f"| {NAMES[n]} | {r['fact_f1']:.5f} | {r['invalid_relation_repair_rate']:.5f} | {r['correct_fact_preservation']:.5f} | {r['new_violations']:.2f} | {r['accounted_calls']:.2f} |")
    report+=['','测试集上，计数惩罚 DDQN 仍完全回避关系恢复。比率惩罚恢复了修复行为，但其 F1 与恢复率均值低于零惩罚、ridge 和强启发式；相应主要对照均未通过八项 Holm 校正。相对于原计数惩罚，两项指标均通过校正（p=0.015625）。不能把未显著差异解读为等效，也不能宣称 DDQN 已优于简单策略。', '', '比率惩罚 DDQN 的恢复率种子间标准差为 12.44 个百分点，提示仍有训练不稳定性；新版图保留全部种子均值。所有方法均保留了初始正确事实，新增违规均为重复项；这取决于受控修复算子的可信恢复记录，不能外推为自然错误上的安全性。', '', '## 配对推断','', '先在三十个场景取平均，再以十个独立训练／运行种子为统计单位。八项主要检验一次性进行 Holm 校正；区间只描述给定测试场景集合下的种子变动。','']
    for r in analysis['comparisons']:report.append(f"- Rate DDQN − {NAMES[r['right']]}，{r['metric']}：差值 {r['difference']:.6f}，95% CI [{r['ci_low']:.6f}, {r['ci_high']:.6f}]，Holm p={r['p_holm']:.6f}。")
    report+=['','## 解释边界','', '所有策略的累计回报统一用比率惩罚计算；原计数与零惩罚回报另存，不能直接把各自训练奖励的高低作为公平优势。',
       '', '40 个神经模型共完成 10,000 回合；10 个简单基线各使用额外独立的 250 回合随机探索。神经模型与基线每次都限 250 回合，但训练访问状态和监督形式不同；基线拟合的是公开反馈的三个分项，不是神经网络价值函数。',
       '', '候选系数、种子和训练轮数未根据开发／测试结果调整。若零惩罚或简单策略效果相近，应据此收窄奖励或 RL 的独立贡献，而不是继续择优调参。',
       '', '当前固定基础图上的比率惩罚同时减小了有效惩罚系数；这一对照不能单独证明归一化优于一个更小的计数系数，也没有验证跨图规模稳定性。', '', '生成规则进入 RL、独立语义标注、新文档类型和真实 API 成本仍需另做。']
    (HERE/'report_zh.md').write_text('\n'.join(report)+'\n')
if __name__=='__main__':main()
