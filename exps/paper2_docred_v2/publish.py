"""Publish development diagnostics from complete results, never held-out claims."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def publish():
    result=json.loads((HERE/'pilot_results.json').read_text());episodes=json.loads((HERE/'pilot_traces.json').read_text())
    names={'stop':'Stop','acquire_then_repair':'Acquire then repair','repair_asap':'Repair when feasible','uniform_feasible':'Uniform feasible'}
    totals={p:{k:sum(e['policies'][p][k] for e in episodes) for k in ['correct_lost','injected_removed','injected_total']} for p in names}
    lines=['# Paper2 源证据约束 v2：开发试验','',f"固定前十个开发 episode，共 20 文档（10 干净、10 扰动）。{result['actual_requests']} 次实际 Gemma 请求，40 份结果；运输失败 {result['transport_failures']}，规则 JSON 成功 {result['parse_success']}/40。",'',
           '|策略|参考恢复 F1 (%)|正确参考保持 (%)|正确参考丢失|注入项移除|平均获取响应|','|---|---:|---:|---:|---:|---:|']
    for p,name in names.items():
        s=result['summary'][p];t=totals[p]
        lines.append(f"|{name}|{100*s['f1']:.2f}|{100*s['correct_preservation']:.2f}|{t['correct_lost']}|{t['injected_removed']}/{t['injected_total']}|{s['accounted_responses']:.2f}|")
    lines+=['',f"规则：{result['rules']}。源证据规则实际触发修复的 episode：{result['source_repair_episodes']}/10。",'',
            '**扩展训练门槛：'+('通过。下一步才可在训练文档生成缓存并重训练。' if result['gate_passed'] else '未通过。本轮不扩大训练或打开测试集。')+'**','',
            '门槛在调用前冻结：源约束至少在两个 episode 造成实际删除；至少一个固定非停止流程在十个 episode 的平均 F1 高于停止，且正确参考保持率不低于 99%。这个保守安全阈值不是 RL 胜出条件。',
            '这些数字只表示参考恢复与注入项移除。扰动由参考图独立构造，真实世界中未标注关系不一定错误。规则引用匹配只验证执行来源，不证明语义蕴含。人工核查后置。',
            '缓存回放实际 API 调用为零；“获取响应”是策略消耗的缓存份数。实际生成请求和重试另计。每个 episode 是两个来源文档；策略重复不增加文档数。',
            '旧十文档自然试验、冻结奖励和负结果保持不变。新试验只运行一轮；上限两轮不是必须调到成功。']
    (HERE/'report_zh.md').write_text('\n'.join(lines)+'\n')
    plt.rcParams.update({'font.family':'Times New Roman','font.size':9,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(7.1,2.6),gridspec_kw={'width_ratios':[1.8,1]})
    for i,p in enumerate(names):
        diffs=[100*(e['policies'][p]['f1']-e['policies']['stop']['f1']) for e in episodes]
        axes[0].scatter(diffs,[i+(j-4.5)*.04 for j in range(10)],s=12,color='#397293',alpha=.65,zorder=2)
        axes[0].scatter([sum(diffs)/10],[i],s=35,marker='D',color='#B86E3C',zorder=3)
        axes[1].scatter([result['summary'][p]['accounted_responses']],[i],s=30,color='#397293')
    axes[0].axvline(0,color='#777777',lw=.7,ls='--');axes[0].set_yticks(range(4),list(names.values()));axes[0].invert_yaxis();axes[0].set_xlabel('Reference F1 change vs. stop (pp)')
    axes[1].set_yticks(range(4),['']*4);axes[1].invert_yaxis();axes[1].set_xlim(-.2,4.3);axes[1].set_xticks([0,1,2,3,4]);axes[1].set_xlabel('Mean acquired responses')
    for ax in axes:
        ax.set_ylim(3.4,-.4);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    fig.tight_layout();dest=ROOT/'paper2/figure/experiments'
    for ext in ['svg','pdf']:fig.savefig(dest/('docred_source_pilot.'+ext),bbox_inches='tight')
    svg=dest/'docred_source_pilot.svg';svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)
    tex=[r'\subsection{Source-Evidence Development Test}',r'\label{app:docred_v2}',
         r'A separate version retains dual-strategy generation and the four-action scheduler, and adds document-scoped source constraints. Each candidate marks a concrete record as supported, contradicted, or insufficient. The compiler validates an exact quote in a numbered original sentence and records its character offsets. Hypothetical augmentation clauses cannot supply evidence. Insufficient evidence causes abstention. Conflicting support and contradiction also cause abstention; type compatibility alone cannot cancel a source contradiction.',
         r'For this version, let $V(g;R)$ be the set of nonconflicting violations and $N$ the initial record count (with denominator one for an empty input). We use $G(g;R)=1-|V(g;R)|/N$ and coverage $C$ over the initial records. The graph-change term compares both graphs under the updated rules:',
         r'\begin{align}',r'r_t={}&0.5\left[G(g_{t+1};R_{t+1})-G(g_t;R_{t+1})\right] \nonumber\\',
         r'&+0.5(C_{t+1}-C_t)-0.004a_t \nonumber\\',r'&-0.00002d_t-|V_{\mathrm{edit},t}|/N,',r'\end{align}',
         r'where $a_t$ counts acquired responses, $d_t$ counts removed records, and $V_{\mathrm{edit},t}=V(g_{t+1};R_{t+1})\setminus V(g_t;R_{t+1})$. Thus acquisition can reveal a violation without being charged for creating it. A two-record synthetic counterexample changes the discounted acquire--repair return from $-0.266519$ to $0.483481$ at discount $0.95$. This is an accounting check, not an empirical quality gain. Source support is still a model judgment; quote validation does not prove its meaning.',
         r'Before calls, we fix the first ten development pairs (20 documents). Each pair contains one reference graph and one reference graph with added endpoint or relation substitutions, numbering $\lceil0.2|G^*|\rceil$. References are used in construction and scoring, not in prompts, observations, or reward. The observations contain 14 public summaries and an action mask; they are not asserted to be a sufficient Markov state. Each episode allows four response acquisitions, two per strategy, and ten steps. The removal operator retains the emptying guard.',
         r'\begin{table}[t]',r'\centering',r'\caption{Source-evidence development diagnostics on ten fixed document pairs. F1 and preservation are episode means. Lost counts removed reference facts. No learned policy is evaluated.}',r'\label{tab:docred_source_pilot}',r'\small',r'\begin{tabular}{lrrr}',r'\hline',r'Schedule & F1 (\%) & Preserved (\%) & Lost \\',r'\hline']
    for p,name in names.items():
        s=result['summary'][p];tex.append(f"{name} & {100*s['f1']:.2f} & {100*s['correct_preservation']:.2f} & {totals[p]['correct_lost']} "+chr(92)*2)
    tex += [r'\hline',r'\end{tabular}',r'\end{table}',
            f"The 40 outputs require {result['actual_requests']} actual Gemma requests. They compile to {result['rules']['type']} type rules, {result['rules']['source_supported']} source-support rules, and {result['rules']['source_contradicted']} source-contradiction rules. Source constraints trigger removals in {result['source_repair_episodes']} of ten episodes. The pre-call expansion gate requires this in at least two episodes and at least one fixed schedule to improve mean reference F1 while preserving at least 99\\% of reference facts.",
            ('The development gate passes; expanded training and held-out evaluation are separate subsequent steps.' if result['gate_passed'] else 'The development gate is not met, so this version is not expanded to learned-policy training or held-out evaluation.'),
            r'These results measure reference recovery and removal of injected items. Independent assessment of natural relations and edits remains pending. Cached schedule replay makes zero API calls; generation requests are counted separately.',
            r'\begin{figure*}[t]',r'\centering',r'\includegraphics[width=0.94\textwidth]{figure/experiments/docred_source_pilot.pdf}',
            r'\caption{Source-evidence development replay. Small points show ten episode-level F1 changes from stop; diamonds show their mean. The right panel shows cached response acquisitions.}',r'\label{fig:docred_source_pilot}',r'\end{figure*}']
    (ROOT/'paper2/sections/docred_source_pilot.tex').write_text('\n'.join(tex)+'\n')

if __name__=='__main__':publish()
