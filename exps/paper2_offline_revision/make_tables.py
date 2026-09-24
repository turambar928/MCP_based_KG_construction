"""Generate manuscript tables directly from archived analysis outputs."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parents[1]/'paper2'/'tables';DEST.mkdir(exist_ok=True)
NAMES={'random_valid':'Random valid','alternating_valid':'Alternating valid','rule_first_valid':'Rule-first valid','acquire_then_deficit':'Acquire + deficit','DQN':'DQN','Double DQN':'Double DQN','model_informed_lookahead':'Model-informed lookahead','no_graph_features':'No graph features','no_rule_features':'No rule features','no_mask':'No action mask','no_call_penalty':'No call penalty'}

def table(name,caption,label,cols,header,rows,wide=False):
    env='table*' if wide else 'table'
    text='\\begin{'+env+'}[t]\n\\centering\n\\caption{'+caption+'}\n\\label{'+label+'}\n\\footnotesize\n\\setlength{\\tabcolsep}{3pt}\n'
    text+='\\begin{tabular*}{'+('\\textwidth' if wide else '\\columnwidth')+'}{@{\\extracolsep{\\fill}}'+cols+'@{}}\n\\toprule\n'
    text+=' & '.join(header)+' \\\\\n\\midrule\n'
    text+=''.join(' & '.join(r)+' \\\\\n' for r in rows)
    text+='\\bottomrule\n\\end{tabular*}\n\\end{'+env+'}\n'
    (DEST/(name+'.tex')).write_text(text)

def main():
    p=json.loads((HERE/'policy_analysis.json').read_text());s={r['policy']:r for r in p['summary']}
    def metric(r,k):return f"${r[k]:.4f}\\pm{r[k+'_std']:.4f}$"
    def rows(names):
        return [[NAMES[n],metric(s[n],'final_joint'),metric(s[n],'auc18'),f"{s[n]['accounted_calls']:.1f}",f"{s[n]['invalid_actions']:.1f}",f"{s[n]['environment_probes']:.1f}"] for n in names]
    table('offline_policies','Matched policy comparison over ten paired scenarios (mean $\\pm$ sample standard deviation). Calls are accounted acquisition units; all runs make zero API requests. Lookahead alone probes transitions.','tab:rl_ablation','lccrrr',['Policy','Final $\\bar Q$','AUC$_{18}$','Calls','Invalid','Probes'],rows(list(s)[:7]),True)
    table('offline_ablations','Retrained Double-DQN ablations: ten seeds and 250 episodes per variant. All evaluations use the original reward and common 18-step horizon.','tab:offline_ablations','lccrrr',['Variant','Final $\\bar Q$','AUC$_{18}$','Calls','Invalid','Probes'],rows(['Double DQN']+list(s)[7:]),True)
    tests=[]
    for c in p['comparisons']:
        tests.append([NAMES[c['right']],'Final $\\bar Q$' if c['metric']=='final_joint' else 'AUC$_{18}$',f"{c['difference']:+.5f}",f"$[{c['ci_low']:+.5f},{c['ci_high']:+.5f}]$",f"{c['p_holm']:.4f}"])
    table('offline_tests','Full Double DQN minus comparator: paired bootstrap intervals and exact two-sided sign-randomization tests. Holm adjustment covers all ten tests; intervals are pointwise.','tab:offline_tests','llccc',['Comparator','Metric','Difference','95\\% interval','Holm $p$'],tests,True)
    r=json.loads((HERE/'rule_analysis.json').read_text());budget=[]
    for v in r['budget_summary']:
        if v['budget_calls'] not in [100,1000,4000]:continue
        budget.append([str(v['budget_calls']),v['strategy'].capitalize(),str(v['documents']),f"{v['declarations']:.0f}",f"{v['constraint_candidates']:.0f}"])
    table('offline_budget','Equal-call candidate comparison (means over 30 document permutations). Declarations are entity and relation types; constraints are candidate patterns or statements.','tab:equal_budget','rlrrr',['Calls','Strategy','Docs','Decl.','Constraints'],budget)
    execution=[]
    for v in r['execution']:
        execution.append([v['strategy'].capitalize(),str(v['unique_compiled_rules']),str(v['tp']),str(v['fp']),f"{v['recall']:.3f}",f"{v['f1']:.3f}"])
    table('offline_execution','Direct execution of archived typed candidates on RuleTest-94. There are 64 defective and 30 clean cases.','tab:direct_execution','lrrrrr',['Strategy','Patterns','TP','FP','Recall','F1'],execution)
    fam=[]
    for v in r['family_label_check']:
        fam.append([v['strategy'].replace(' only','').replace('Dual strategy','Family union'),str(v['tp']),str(v['fp']),str(v['fn']),f"{v['recall']:.3f}",f"{v['f1']:.3f}"])
    table('offline_families','Hand-implemented family detectors, rescored against stored suite labels. These detectors are separate from the compiled candidate patterns.','tab:rule_family_final_ablation','lrrrrr',['Detector','TP','FP','FN','Recall','F1'],fam)
    report=['# Paper2 离线修订实验结果','', '本轮不调用 API，不下载模型，不修改 Paper1；保留 RL 协同优化与双策略规则生成主线。','',
      '## 策略与消融','', '| 方法 | 最终质量 | AUC（18 步） | 计入调用 | 无效动作 |','|---|---:|---:|---:|---:|']
    for n,v in s.items():report.append(f"| {NAMES[n]} | {v['final_joint']:.5f} | {v['auc18']:.5f} | {v['accounted_calls']:.1f} | {v['invalid_actions']:.1f} |")
    report+=['','40 个新模型共训练 10,000 episodes；原有 20 个 DQN / Double-DQN checkpoint 的最终质量与调用计数复现一致。110 个配对评估结果全部保留。',
      '', '强启发式优于 Double DQN（最终质量 Holm p=0.046875，AUC p=0.01953125）。完整模型优于去掉规则特征的版本，两项指标均经 Holm 校正显著。去掉动作掩码后，平均出现 7.8 次无效动作，最终质量显著下降；AUC 在十项校正后不显著。去掉图特征或调用惩罚的独立增益未通过校正后的检验。',
      '', '这些是已有十个场景的离线追加分析，不是新域测试；显著性不能作为跨域泛化证据。',
      '', '## 规则候选与可执行性','', '同一文档集的双策略 union 使用两倍调用。相同调用预算下，augmentation 的约束候选数高于 dual；dual 没有显示候选数量的成本优势。单策略处理 B 篇文档，dual 处理 B/2 篇，这一覆盖差异保留在表中。',
      '', f"完整日志包含 {r['candidate_occurrences']:,} 条候选记录；可编译为 {r['unique_compiled']:,} 个不同的 allowed/forbidden typed patterns，仅 {r['unique_compiled_with_case_match']} 个与测试记录匹配。直接执行 union 检出 10/64 个缺陷（recall=0.15625，F1=0.27027，FP=0）。手写规则族 union 检出 64/64，二者不能互相替代。",
      '', '## 本轮论文改动','', '- 校正 14 维观测、可行动作掩码、260-episode 探索衰减、规则校准集及模拟调用成本的定义。',
      '- 两个生成算法按实际一调用实现描述；删除版包含原文及被删片段，augmentation 在同一响应中返回补充条款与规则。',
      '- 用配对可行策略与四项真实重训练消融替换旧的主比较，使用统一 AUC 与双侧检验；不再称单步 lookahead 为理论上界。',
      '- 方法图与实验图使用 Times New Roman，提供可编辑 SVG 和矢量 PDF；表格由 JSON 自动生成。',
      '- 修正 MINERVA / DeepPath 归属，以及把 SHACL 基线覆盖不足等同于语言能力不足的表述。',
      '', '## 仍待完成','', '- 将实际生成规则经验证后接入 RL 环境，记录新规则如何改变检测、动作可行性和修复结果。',
      '- 自然缺陷独立标注与未见场景测试。',
      '- 恢复服务后补真实模型成本、语义抽取评估和外部规则方法；仅使用用户允许的非 GPT / Claude 模型。',
      '', '详见 paper2/TODO.md 和本目录 README.md。当前结果完成离线修复，但不能视作 TKDE 投稿证据已充分。']
    (HERE/'report_zh.md').write_text('\n'.join(report)+'\n')
if __name__=='__main__':main()
