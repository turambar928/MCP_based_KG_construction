"""Publication artifacts from the coverage audit, not inferred repair accuracy."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'paper1'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from figure_style import apply_style
from exps.paper2_offline_revision.make_tables import table
HERE=Path(__file__).resolve().parent
NAMES={'RuleTest-94':'RuleTest-94','政务':'Government','金融':'Finance','环境':'Environment'}

def main():
    result=json.loads((HERE/'results.json').read_text());coverage=result['coverage']
    union=[r for r in coverage if r['strategy']=='union']
    rows=[[NAMES[r['dataset']],f"{r['records']:,}",f"{r['typed_records']:,}",str(r['matched_rules']),str(r['flagged_records'])] for r in union]
    table('rule_integration_coverage','Exact typed-rule coverage on RuleTest-94 and three archived CSV graph snapshots. All 18,143 compiled patterns are available. A zero in the raw graphs reflects missing node types, not verified absence of defects.',
          'tab:rule_integration_coverage','lrrrr',['Input','Records','Typed','Matching rules','Flagged'],rows,wide=True)
    apply_style();fig,axs=plt.subplots(1,2,figsize=(7.15,2.8),layout='constrained')
    y=np.arange(4);typed=np.array([100*r['typed_records']/r['records'] for r in union])
    axs[0].barh(y,typed,color='#326C99',label='Types available',height=.55)
    axs[0].barh(y,100-typed,left=typed,color='#D6DDE3',label='Types unavailable',height=.55)
    axs[0].set_yticks(y,[NAMES[r['dataset']] for r in union]);axs[0].invert_yaxis()
    for i,r in enumerate(union):axs[0].text(50,i,f"{r['records']:,} records",ha='center',va='center',fontsize=7,color='white' if typed[i] else '#17212B')
    axs[0].set(xlim=(0,100),xlabel='Share of graph records (%)');axs[0].set_title('(a) Type information',loc='left');axs[0].legend(loc='upper center',bbox_to_anchor=(.5,-.22),ncol=2,frameon=False,fontsize=7)
    suite=[r for r in coverage if r['dataset']=='RuleTest-94'];x=np.arange(3);w=.34
    axs[1].bar(x-w/2,[r['matched_rules'] for r in suite],w,color='#326C99',label='Matching patterns')
    axs[1].bar(x+w/2,[r['flagged_records'] for r in suite],w,color='#467D64',label='Flagged records')
    for i,r in enumerate(suite):
        for offset,key in [(-w/2,'matched_rules'),(w/2,'flagged_records')]:axs[1].text(i+offset,r[key]+.25,str(r[key]),ha='center',fontsize=7)
    axs[1].set_xticks(x,['Deletion','Augmentation','Union']);axs[1].set(ylim=(0,12),ylabel='Count');axs[1].set_title('(b) RuleTest-94 execution',loc='left');axs[1].legend(loc='upper center',bbox_to_anchor=(.5,-.22),ncol=2,frameon=False,fontsize=7)
    dest=ROOT/'paper2/figure/experiments'
    for ext in ['pdf','svg','png']:fig.savefig(dest/f'rule_integration_coverage.{ext}',bbox_inches='tight',dpi=220)
    p=dest/'rule_integration_coverage.svg';p.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines())+'\n');plt.close(fig)
    lines=['# Paper2 规则覆盖与策略接口离线审计','',
      '本轮完成接口和机制回放，没有调用 API、推断实体类型或重训练 RL。原八动作环境和已有检查点保持不变。','',
      '## 覆盖结果','', '| 输入 | 记录数 | 类型可用 | 匹配规则 | 被禁止规则标记 |','|---|---:|---:|---:|---:|']
    for r in union:lines.append(f"| {r['dataset']} | {r['records']:,} | {r['typed_records']:,} | {r['matched_rules']} | {r['flagged_records']} |")
    lines += ['', '三份原始图的全部节点类型为 Unknown，共 26,270 条边无法进行类型约束判断。零触发不代表零缺陷，也不能转写成高准确率。快照来自本轮 manifest 指定的 CSV，不与旧 SHACL 表中的输入数量混用。',
      '', 'RuleTest-94 上，删除策略的一条允许模式和一条禁止模式分别匹配十条记录；增强策略无匹配。允许模式不等于缺陷检测。',
      '', '## 接口与顺序回放','',
      '接口提供 reset / observe / available_actions / step；动作是加载删除规则库、加载增强规则库、执行禁止记录移除、停止。observe 仅提供公开统计和掩码。每次获取加载整个存档策略库，不是一条模型请求，不提供训练奖励。',
      '', '四种设置为两种获取顺序 × 立即/延后修复。四个输入共 16 条完整轨迹；RuleTest-94 均删除十条设计缺陷记录、零条设计干净记录。三份原始图均无修改。没有观察到实际顺序收益，因此不启动新训练。',
      '', '实际回放未出现冲突或事后许可。单独的合成单元测试验证：先删除后获取许可会留下可追溯的 late_permissions 事件；延后修复在允许/禁止冲突时弃权。这些单元例子不计入论文样本或效果。',
      '', '## 下一步所需条件','',
      '先取得可信实体类型和适用的规则覆盖，再冻结独立输入与参考标签。当前接口不代替生成规则进入 RL 的完整训练实验，也不证明自然错误修复安全。',
      '', '源规则身份、来源行号、匹配记录和所有移除均保存在压缩 JSONL 中。论文表和 Times New Roman 图由本脚本生成。']
    (HERE/'report_zh.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
