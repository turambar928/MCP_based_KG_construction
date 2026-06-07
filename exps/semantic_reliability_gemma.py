# -*- coding: utf-8 -*-
"""
Semantic Score Reliability (paper1 §4.3 Independent-model agreement).

Re-score a balanced random sample of triples (3 domains x {Exp2, Exp3}) with an
INDEPENDENT judge model from a different family (google/gemma-4-26B-A4B-it),
using the SAME per-domain evaluation prompt and temperature (0.1) as the original
Qwen3-32B scoring, then measure rank/linear agreement with the Qwen scores.

Outputs:
  exps/semantic_reliability/rescored_triples.csv   (per-triple: qwen vs gemma)
  exps/semantic_reliability/agreement_report.txt   (Pearson r, Spearman rho)
"""
import os
import re
import json
import time
import argparse
import pandas as pd
from openai import OpenAI

# ---------------------------------------------------------------- config
API_KEY = "sk-SLiuoDELfRnOkO8pMdPumnAYhBpb56cXfMWnWDCLTIf8kfIR"
BASE_URL = "http://api.cipsup.cn/v1"
JUDGE_MODEL = "google/gemma-4-26B-A4B-it"   # independent family vs Qwen3-32B
TEMPERATURE = 0.1                            # match original protocol
PER_CELL = 30                               # samples per (domain x exp) cell -> N=180
SEED = 42

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "semantic_reliability")

# (domain_key, exp_label, csv_path)
CELLS = [
    ("government", "Exp2", "qa_gover_2/semantic_evaluation.csv"),
    ("government", "Exp3", "qa_gover_3/semantic_evaluation.csv"),
    ("finance",    "Exp2", "qa_finance_2/semantic_evaluation.csv"),
    ("finance",    "Exp3", "qa_finance_3/semantic_evaluation.csv"),
    ("environment","Exp2", "qa_environment_2/semantic_evaluation.csv"),
    ("environment","Exp3", "qa_environment_3/semantic_evaluation.csv"),
]

# ---------------------------------------------------------------- per-domain prompts
# Identical rubric to the original Qwen3-32B scoring (pol/finance/env _evaluate.py).
PROMPTS = {
    "government": """
        你是一个政务知识图谱质量评估专家。请严格评估以下政务领域三元组的语义合理性，重点关注：

        1. 政务关系的准确性：政府机构层级关系、行政管辖关系、政策适用关系等
        2. 语义逻辑性：主谓宾关系是否符合政务常识，是否存在颠倒、错位等问题
        3. 行政层级合理性：上下级关系是否正确，管辖范围是否合理
        4. 政务术语准确性：是否使用了正确的政务专业术语和表述

        评分标准（0-1分）：
        1.0分: 完全符合政务常识和行政逻辑，关系表述准确
        0.8分: 基本合理，但可能存在轻微的表述不准确
        0.6分: 部分合理但有歧义或不够准确
        0.4分: 存在明显的逻辑问题或术语使用错误
        0.2分: 严重违背政务常识或行政逻辑
        0.0分: 完全不合理、荒谬或违反基本常识

        特别注意：
        - 政府机构不能管理其上级机构
        - 下级地区不能管辖上级地区
        - 政策法规的适用范围和层级要符合实际
        - 服务事项的主体和客体关系要正确

        请直接返回纯JSON格式，不要包含任何额外文本或代码块标记：
        {"score": 分数值, "reason": "简要说明原因"}
    """,
    "finance": """
        你是一个金融知识图谱质量评估专家。请严格评估以下金融领域三元组的语义合理性，重点关注：

        1. 金融监管关系的准确性：监管机构与被监管机构的层级关系、监管权限范围等
        2. 金融业务逻辑性：银行、证券、保险、基金等业务关系是否符合金融常识
        3. 金融法规合规性：处罚关系、审批关系是否符合金融监管法规
        4. 金融术语准确性：是否使用了正确的金融专业术语和表述

        评分标准（0-1分）：
        1.0分: 完全符合金融常识和监管逻辑，关系表述准确
        0.8分: 基本合理，但可能存在轻微的表述不准确
        0.6分: 部分合理但有歧义或不够准确
        0.4分: 存在明显的逻辑问题或术语使用错误
        0.2分: 严重违背金融常识或监管逻辑
        0.0分: 完全不合理、荒谬或违反基本常识

        特别注意：
        - 被监管机构不能监管监管机构
        - 下级金融机构不能管理上级机构
        - 金融产品与机构的从属关系要正确
        - 客户与金融机构的服务关系要合理

        请直接返回纯JSON格式，不要包含任何额外文本或代码块标记：
        {"score": 分数值, "reason": "简要说明原因"}
    """,
    "environment": """
        你是一个环境知识图谱质量评估专家。请严格评估以下环境领域三元组的语义合理性，重点关注：

        1. 环境监管关系的准确性：监管机构与被监管对象的层级关系、监管权限范围等
        2. 环境污染逻辑性：企业-污染物-环境要素的关系是否符合环保常识
        3. 环境治理合规性：污染治理、环境许可、执法处罚关系是否符合环保法规
        4. 环境术语准确性：是否使用了正确的环保专业术语和表述

        评分标准（0-1分）：
        1.0分: 完全符合环保常识和监管逻辑，关系表述准确
        0.8分: 基本合理，但可能存在轻微的表述不准确
        0.6分: 部分合理但有歧义或不够准确
        0.4分: 存在明显的逻辑问题或术语使用错误
        0.2分: 严重违背环保常识或监管逻辑
        0.0分: 完全不合理、荒谬或违反基本常识

        特别注意：
        - 被监管企业不能监管环保部门
        - 下级环保部门不能管理上级环保部门
        - 污染物与治理设施的关系要正确
        - 企业与环境要素的影响关系要合理

        请直接返回纯JSON格式，不要包含任何额外文本或代码块标记：
        {"score": 分数值, "reason": "简要说明原因"}
    """,
}

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def parse_response(content):
    """Robust JSON / score extraction (mirrors pol_evaluate.parse_ai_response)."""
    content = content.strip()
    # strip <think>...</think> if present
    content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
    for cand in (content,
                 content[7:] if content.startswith("```json") else content,
                 content.strip("`").strip()):
        try:
            obj = json.loads(cand)
            return float(obj.get("score")), str(obj.get("reason", ""))
        except Exception:
            pass
    m = re.search(r"\{[\s\S]*\}", content)
    if m:
        try:
            obj = json.loads(m.group())
            return float(obj.get("score")), str(obj.get("reason", ""))
        except Exception:
            pass
    sm = re.search(r'"?score"?\s*[:：]\s*([0-9]*\.?[0-9]+)', content)
    if sm:
        return float(sm.group(1)), "regex-extracted"
    return None, f"UNPARSEABLE: {content[:120]}"


def score_triple(domain, triple, max_retry=3):
    prompt = PROMPTS[domain] + f"\n评估以下三元组的合理性:\n{triple}"
    for attempt in range(max_retry):
        try:
            resp = client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=TEMPERATURE,
            )
            score, reason = parse_response(resp.choices[0].message.content or "")
            if score is not None:
                return max(0.0, min(1.0, score)), reason
        except Exception as e:
            reason = f"API error: {e}"
            time.sleep(2.0 * (attempt + 1))
    return None, reason


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cell", type=int, default=PER_CELL)
    ap.add_argument("--limit", type=int, default=0, help="debug: cap total triples")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    total = 0
    for domain, exp, rel in CELLS:
        path = os.path.join(HERE, rel)
        df = pd.read_csv(path)
        df = df[df["score"] >= 0].dropna(subset=["triple", "score"])
        k = min(args.per_cell, len(df))
        sample = df.sample(n=k, random_state=SEED)
        print(f"[{domain} {exp}] sampling {k} / {len(df)} triples")
        for _, r in sample.iterrows():
            triple = str(r["triple"]).strip()
            qwen = float(r["score"])
            g_score, g_reason = score_triple(domain, triple)
            rows.append({
                "domain": domain, "exp": exp, "triple": triple,
                "qwen_score": qwen, "gemma_score": g_score, "gemma_reason": g_reason,
            })
            total += 1
            tag = "OK" if g_score is not None else "FAIL"
            print(f"  [{tag}] qwen={qwen:.2f} gemma={g_score} | {triple[:40]}")
            time.sleep(1.0)
            if args.limit and total >= args.limit:
                break
        if args.limit and total >= args.limit:
            break

    out_csv = os.path.join(OUT_DIR, "rescored_triples.csv")
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print(f"\nSaved {len(rows)} rows -> {out_csv}")
    print("Run analyze_reliability.py to compute correlations.")


if __name__ == "__main__":
    main()
