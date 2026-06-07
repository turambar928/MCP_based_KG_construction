# -*- coding: utf-8 -*-
"""
Prepare the human-annotation sheet for paper1 §4.3 (the pending 'Human annotators' row of
tab:sem_reliability). Reuses the SAME 180 triples already cross-validated against the
independent LLM judge (rescored_triples.csv), so human ratings can be correlated against both
the Qwen S_sem and the Gemma judge, and inter-annotator agreement (Cohen's kappa) computed.

The sheet is BLIND: it shows only the triple + domain, with empty columns for 2-3 annotators
(score on the same 0/0.2/0.4/0.6/0.8/1.0 scale used by the automatic judge). The mapping back
to the model scores is kept in answer_key.csv (not shown to annotators).
"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
src = pd.read_csv(os.path.join(HERE, "rescored_triples.csv"))

# shuffle so domain/exp order isn't a cue; keep a hidden id to rejoin
src = src.sample(frac=1.0, random_state=7).reset_index(drop=True)
src.insert(0, "id", range(1, len(src) + 1))

DOM = {"government": "政务", "finance": "金融", "environment": "环境"}
sheet = pd.DataFrame({
    "id": src["id"],
    "domain": src["domain"].map(DOM),
    "triple": src["triple"],
    "annotator1_score": "", "annotator2_score": "", "annotator3_score": "",
})
sheet.to_csv(os.path.join(HERE, "human_annotation_sheet.csv"), index=False)
# hidden key with the model scores for later correlation
src[["id", "domain", "exp", "triple", "qwen_score", "gemma_score"]].to_csv(
    os.path.join(HERE, "answer_key.csv"), index=False)

instructions = """# 人工标注说明（paper1 §4.3 语义可靠性 - 人工一致性行）

## 目标
对 180 条三元组的"语义合理性"独立打分，用于验证自动语义评分(S_sem)是否可靠。
请 **2-3 名标注者各自独立** 打分（不要互相商量），填入 human_annotation_sheet.csv 的
annotator1_score / annotator2_score / annotator3_score 列。

## 评分标准（与自动评分一致，0-1，步长 0.2）
- 1.0 完全符合该领域常识与逻辑，关系表述准确
- 0.8 基本合理，仅轻微表述不准
- 0.6 部分合理但有歧义或不够准确
- 0.4 存在明显逻辑问题或术语错误
- 0.2 严重违背常识/逻辑
- 0.0 完全不合理、荒谬

## 重点关注
- 主谓宾是否颠倒/错位；层级关系是否正确（下级不能管理上级）；术语是否准确；信息是否自洽。
- 只看三元组本身的合理性，不要参考任何模型分数（本表未提供，故意保持盲评）。

## 标注完成后
运行 `python3 exps/semantic_reliability/score_human.py` 自动计算：
- 人工分 vs 自动 S_sem(Qwen) 的 Pearson r
- 标注者间一致性 Cohen's κ（两两平均）
结果写入 human_agreement.txt，填入论文 tab:sem_reliability 第二行。
"""
open(os.path.join(HERE, "human_annotation_README.md"), "w", encoding="utf-8").write(instructions)
print(f"wrote human_annotation_sheet.csv ({len(sheet)} triples), answer_key.csv, README.")
print("domains:", dict(src["domain"].value_counts()))
