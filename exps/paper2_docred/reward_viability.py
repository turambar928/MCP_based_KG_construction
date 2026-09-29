"""Synthetic analytic counterexample, never counted as an empirical experiment."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper2_docred.environment import GeneratedRuleEnvironment
from exps.paper2_docred.test_environment import fixture
HERE=Path(__file__).resolve().parent


def main():
    records,packets=fixture()
    for p in packets['deletion']:
        p['rules']=[dict(kind='forbidden',pattern=['PER','born','ORG'])]
    env=GeneratedRuleEnvironment(records,packets)
    acquire=env.step('acquire_deletion')[1];repair=env.step('repair')[1]
    discounted=acquire+.95*repair
    formula=-.004-.525/len(records)-.95*.00002
    assert abs(discounted-formula)<1e-12 and discounted<0
    report=dict(kind='synthetic_analytic_counterexample_not_empirical_evaluation',initial_records=2,
                acquisition_reward=acquire,repair_reward=repair,discounted_return=discounted,
                immediate_stop_return=0.,formula='-0.004 - 0.525/N - 0.95*0.00002 < 0 for N >= 2',
                assumptions=['Initially uncovered records, one newly forbidden record, no conflicts.',
                             'Acquisition adds only that rule; repair removes only that record.',
                             'Reward as in generated-rule-scheduler-design-v1, discount 0.95.'],
                conclusion='The acquire-then-repair path has negative return despite removing the newly detected violation. This is an incentive limitation in the frozen design, not an implementation discrepancy or a universal proof that stop is optimal over all action paths.',
                changes_to_frozen_protocol=False,api_calls=0)
    (HERE/'reward_viability.json').write_text(json.dumps(report,indent=2)+'\n')
    (HERE/'reward_viability_zh.md').write_text('''# 四动作设计的离线奖励反例

本文件是合成验收案例与代数分析，不计入任何真实数据效果分母，调用 API 为 0。冻结协议及奖励代码保持不变。

令初始图有 N≥2 条记录，尚无活跃规则；获取的唯一新规则恰好将其中一条标成 forbidden，且没有冲突。获取时图潜能下降 1/N，规则覆盖潜能增加 1/N，两项各乘 0.5，正好抵消。再扣获取成本 0.004 和新揭示违规 1/N，因此获取奖励为 −0.004−1/N。

随后删除这一条记录，图潜能增加 1/N；覆盖潜能基于初始记录集合计算，因此不变。修复奖励为 0.5/N−0.00002。折扣 γ=0.95 时，两步回报为：

`−0.004 − 0.525/N − 0.95×0.00002 < 0`。

立即停止得到 0。N=2 的实际环境运行分别得到 −0.504、0.24998，两步折扣回报 −0.266519。也就是说，这条“先发现、再修复”路径受奖励抑制。这个反例不证明所有场景或所有路径下 stop 都最优，也不判断规则是否语义正确。

问题来自把“获取规则后新发现的违规”与“编辑新造成的违规”一起惩罚。当前原设计已披露这种风险；本轮给出可执行反例。下一版本应在独立开发协议中明确两类事件的奖励语义，并检查发现／修复的净激励，再冻结训练设计。不能在正式测试结果上调系数，也不能把本次实现描述成已证明有效的 RL 闭环。
''')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
