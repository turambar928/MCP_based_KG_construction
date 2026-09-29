"""Strict results plus explicitly post-observation code-fence sensitivity; zero calls."""
import hashlib,json,re,sys
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from exps.paper1_online_recovery.run import strict_parse,read,MODEL
from exps.paper1_reextraction_control.scoring import validate
from exps.paper1_mechanism_audit.analyze import paired
from exps.paper1_external_receipts.analyze import score_case
from exps.paper1_receipt_followup.protocol import filter_response
from exps.paper1_ablation_completion.analyze import write_csv
HERE=Path(__file__).resolve().parent/'reextraction';SOURCE=ROOT/'exps/paper1_receipt_followup/test'
FENCE=re.compile(r'\A```(?:json)?\s*\n(.*?)\n```\Z',re.S|re.I)
def compatibility(raw):
    text=raw.strip();match=FENCE.fullmatch(text)
    out,status=strict_parse(match.group(1) if match else text)
    return out,status,bool(match)
def main():
    rows=read(HERE/'predictions.jsonl');tasks=read(ROOT/'exps/paper1_reextraction_control/requests.jsonl');validate(rows,tasks)
    inputs={r['case_id']:r for r in read(SOURCE/'inputs.jsonl')};initial={r['case_id']:r['triples'] for r in read(SOURCE/'extraction.jsonl')};refs={r['case_id']:r for r in read(SOURCE/'references.jsonl')}
    per=[];format_rows=[];summary=[];primaries=[];cost=[]
    for mode in ['frozen_strict','post_observation_fence_compatibility']:
        records=[]
        for r in rows:
            cid=r['case_id'];out=r['triples'];status=r['status'];wrapped=False
            if mode!='frozen_strict' and status!='transport_error':out,status,wrapped=compatibility(r['raw_response'])
            if mode!='frozen_strict':format_rows.append({'case_id':cid,'arm':r['arm'],'original_status':r['status'],'compatibility_status':status,'enclosing_fence':wrapped,'raw_response_sha256':hashlib.sha256(r['raw_response'].encode()).hexdigest()})
            filtered,_=filter_response(inputs[cid],out)
            for gate,triples in [('raw',out),('gate',filtered)]:records.append({'analysis':mode,'case_id':cid,'method':r['arm']+'_'+gate,**score_case(initial[cid],triples,refs[cid])})
        per+=records
        for method in sorted({r['method'] for r in records}):
            rs=[r for r in records if r['method']==method]
            summary.append({'analysis':mode,'method':method,'n':len(rs),**{k:float(np.mean([r[k] for r in rs])) for k in ['triple_f1','normalized_f1','exact_match','clean_fact_preservation','overrepair_rate']}})
        primaries.append({'analysis':mode,**paired(records,'repair_index_gate','extract_index_gate')})
    for arm in sorted({r['arm'] for r in rows}):
        rs=[r for r in rows if r['arm']==arm];d={'arm':arm,'outcomes':len(rs),'requests':sum(len(r['attempts']) for r in rs),'strict_ok':sum(r['status']=='ok' for r in rs),'compatible_ok':sum(r['compatibility_status']=='ok' for r in format_rows if r['arm']==arm),'mean_wall_seconds_including_pacing':float(np.mean([r['wall_seconds'] for r in rs]))}
        for key in ['prompt_tokens','completion_tokens','total_tokens']:
            vals=[r['usage'].get(key) for r in rs if isinstance(r['usage'].get(key),(int,float))]
            d[key+'_known']=len(vals);d[key+'_mean_known']=float(np.mean(vals)) if vals else None
        cost.append(d)
    result={'strict_status':dict(Counter(r['status'] for r in rows)),'compatibility_status':dict(Counter(r['compatibility_status'] for r in format_rows)),'summary':summary,'primary_contrasts':primaries,'cost':cost,'analysis_scope':'240 actual frozen Gemma responses; strict primary unchanged. Secondary parser registered after observing fences in early responses, before reference scoring. Reused 60 receipts, not an untouched test.','sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),HERE/'predictions.jsonl',HERE.parent/'format_amendment.md']}}
    (HERE/'analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');write_csv(HERE/'summary.csv',summary);write_csv(HERE/'per_case.csv',per);write_csv(HERE/'format_audit.csv',format_rows);write_csv(HERE/'cost.csv',cost)
    lines=['# 修复／重新抽取同期对照','','240 个 Gemma 请求全部 HTTP 200，无运输重试；全部响应包裹在 Markdown JSON 代码围栏中。因此冻结的严格 JSON 主分析有 240 个格式失败，所有组 F1=0，不能据此判断修复的语义收益。','', '下表为**观察格式问题后加入的兼容性分析**：仅去除整段外围代码围栏，使用原字段 schema 检查；所有响应一视同仁，没有额外 API 调用。原始响应和严格失败记录完整保留。','','|方法|F1|规范化 F1|原正确事实保持|过度修复率|','|---|---:|---:|---:|---:|']
    for r in summary:
        if r['analysis']!='frozen_strict':lines.append(f"|{r['method']}|{r['triple_f1']:.5f}|{r['normalized_f1']:.5f}|{r['clean_fact_preservation']:.5f}|{r['overrepair_rate']:.5f}|")
    lines+=['','带索引 repair − extract（过滤后，文档配对）：`'+json.dumps(primaries[1]['triple_f1'])+'`。','', '旧图与同字段定义、同来源、同完成预算同时对照；仍复用既有 60 文档，不构成独立跨任务泛化。成本来自实际 usage 和每请求 wall time（包含限速等待及重试），见 cost.csv。','', '原严格协议结果另保存在 `../paper1_reextraction_control/results.json`（相对 exps 目录）。不得把兼容结果标为预注册主结果。']
    (HERE/'report_zh.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'status':result['compatibility_status'],'contrasts':primaries[1],'summary':summary[8:]},indent=2))
if __name__=='__main__':main()
