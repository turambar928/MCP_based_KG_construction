"""Publish the offline diagnosis without changing historical result files."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    report = json.loads((HERE / 'loop_diagnostics.json').read_text())
    summaries = [x['summary'] for x in report['results']]
    lines = ['# Paper2 闭环可行性：离线穷举诊断', '',
        '两轮使用同一 20 个开发文档、10 个双文档回合。保留原规则包、四动作、队列顺序、四响应预算、十步上限及防删空约束。枚举全部可行动作序列，包括提前停止；不调用 API、不训练、不更改旧评分。', '',
        '## 1. 现有候选下还能修多少', '',
        '|轮次|终止路径数|停止 F1|可执行调度预言机 F1|逐项删除放宽上界 F1|代理回报最优 F1|预言机正确丢失|预言机移除注入项|',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for i, s in enumerate(summaries, 1):
        lines.append(f"|{i}|{s['terminal_paths']}|{100*s['stop_f1']:.2f}%|{100*s['executable_oracle_f1']:.2f}%|{100*s['selective_upper_f1']:.2f}%|{100*s['reward_optimum_f1']:.2f}%|{s['oracle_correct_lost']}|{s['oracle_injected_removed']}|")
    lines += ['', '可执行预言机在每个回合用参考 F1 事后选最优可行路径。放宽上界允许从所有实际可删除记录的并集中，仅挑注入项逐条删除，忽略编辑包限制。两者均只作诊断，不能作为策略输入或部署基线。代理最优只按既定折扣奖励选路径；最优奖励并列时的 F1 范围也保存在 JSON。', '',
        '第一轮可执行预言机比先获取后修复高 0.86 个百分点，但奖励最优路径的 F1 为 91.63%，低于停止的 94.42%。这表明修正发现/编辑记账后，错误规则仍可能让代理奖励偏离参考事实质量。不能将记账修复等同于语义安全。', '',
        '第二轮预言机、逐项删除放宽上界和固定先获取后修复均为 95.69%。全部可恢复收益来自删除策略的类型约束；增强没有独有可删除注入项，来源约束没有修复触发。当前固定候选库没有额外的最终 F1 空间，不支持直接扩大 RL 训练。', '',
        '## 2. 规则来源与实际命中', '',
        '下表一次性加载指定策略/家族的全部归档规则，报告考虑许可冲突后的唯一记录标记数。只供诊断，不把假设性分组写成已训练策略。', '',
        '|轮次|规则库/家族|标记注入项|标记正确参考|冲突记录|',
        '|---|---|---:|---:|---:|']
    for i, s in enumerate(summaries, 1):
        for bank, v in s['banks'].items():
            lines.append(f"|{i}|{bank}|{v['injected_flagged']}|{v['correct_flagged']}|{v['conflicts']}|")
    lines += ['', '第二轮 deletion/all 的 7 个注入项都是相对 augmentation/all 的独有命中。第一轮来源规则来自增强，单独加载时标记 4 个注入项和 2 个正确参考事实；这些计数不能当作自然语义准确率。', '',
        '## 3. 顺序、成本与中间质量', '',
        '|轮次|全部四包加载后的终态有差异回合数|四包加载且完成所有可行修复后仍有差异|相同四包预算下回报有差异|迟到许可路径数|参考预言机平均获取包数|',
        '|---|---:|---:|---:|---:|---:|']
    for i, s in enumerate(summaries, 1):
        lines.append(f"|{i}|{s['episodes_with_full_budget_final_variation']}|{s['episodes_with_full_budget_drained_variation']}|{s['episodes_with_full_budget_return_variation']}|{s['late_permission_paths']}|{s['oracle_mean_acquisitions']:.2f}|")
    lines += ['', '第二轮第一列的差异包含“加载完后仍选择不修复”，不能单凭它声称获取顺序改善终态。完成全部可行修复后，第二轮各顺序终态相同；第一轮仍有一个回合受到顺序影响。第一轮穷举找到 15 条迟到许可路径，而早期四个固定流程的结果保持原样。', '',
        '全部 10 个回合都有同预算的折扣回报差异，说明中间质量与获取顺序仍可影响代理目标。JSON 保留每条路径的获取数、折扣回报、十步补齐的代理质量 AUC 和终态；这不是已证明的实际调用节省。参考预言机的 0.80/0.60 获取包数依赖事后标签，不能宣传为可实现成本收益。', '',
        '## 4. 决定', '',
        '- 保持原扩展门槛失败和正式训练未运行状态。没有第三轮生成，没有测试集选择。',
        '- 新输出契约仅为离线提案，验证互斥枚举、family、空结果、候选上限及原始引用；不保证会产生语义正确的来源矛盾规则。',
        '- 若未来另立协议，应先验证规则是否可靠、两策略是否带来实际互补，以及是否存在可测的预算/顺序收益，再决定是否训练。不能靠重复训练现有第二轮候选库获得额外最终 F1。', '',
        '原始四种固定流程的全部 80 条轨迹评分已与枚举结果对齐。598 条穷举路径是同 20 个开发文档上的事后分析，不是 598 个新样本；原文和原始响应未重新分发。']
    (HERE / 'report_zh.md').write_text('\n'.join(lines) + '\n')
    table = [r'\begin{table}[t]', r'\centering',
        r'\caption{Post-hoc exhaustive scheduling on the same ten development pairs per round. F1 is averaged over pairs. Oracles use reference labels only for analysis.}',
        r'\label{tab:offline_loop_ceiling}', r'\footnotesize', r'\begin{tabular}{lrr}', r'\toprule',
        r'Diagnostic & Round 1 & Round 2 \\', r'\midrule']
    rows = [('Feasible terminal paths', 'terminal_paths', False), ('Stop F1 (\%)', 'stop_f1', True),
        ('Executable oracle F1 (\%)', 'executable_oracle_f1', True),
        ('Selective-removal upper F1 (\%)', 'selective_upper_f1', True),
        ('Reward-optimal F1 (\%)', 'reward_optimum_f1', True),
        ('Oracle correct facts lost', 'oracle_correct_lost', False),
        ('Oracle injected items removed', 'oracle_injected_removed', False)]
    for label, key, percent in rows:
        cells = [f'{100*s[key]:.2f}' if percent else str(s[key]) for s in summaries]
        table.append(label + ' & ' + ' & '.join(cells) + r' \\')
    table += [r'\bottomrule', r'\end{tabular}', r'\end{table}', '']
    (ROOT / 'paper2/tables/offline_loop_ceiling.tex').write_text('\n'.join(table))


if __name__ == '__main__':
    main()
