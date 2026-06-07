# -*- coding: utf-8 -*-
"""
Fill the S_sem dimension of the f_phi dataset with the real LLM assessment (Qwen3-32B),
mirroring the paper's semantic-scoring protocol (§ Semantic Scoring Protocol, temp=0.1).

One LLM call per document: the model scores the overall semantic plausibility of the
document's field-derived triples on [0,1]. Updates dataset.csv in place (S_sem, sem_observed).
Concurrency keeps wall-clock low. Reads triples_cache.jsonl produced by build_dataset.py.
"""
import os
import re
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
API_KEY = "sk-SLiuoDELfRnOkO8pMdPumnAYhBpb56cXfMWnWDCLTIf8kfIR"
BASE_URL = "http://api.cipsup.cn/v1"
MODEL = "google/gemma-4-26B-A4B-it"   # judge model for the S_sem INPUT feature (endpoint throughput;
                                      # Qwen was throttled). Feeds f_phi's state vector, not a reported metric.
TEMPERATURE = 0.1
WORKERS = 8
CKPT = None  # set in main

DOMAIN_NAME = {"government": "政务", "finance": "金融", "environment": "环境"}

client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=25, max_retries=0)
_lock = threading.Lock()


def build_prompt(domain, triples):
    dom = DOMAIN_NAME[domain]
    body = "\n".join(f"- {t}" for t in triples[:20])
    return f"""你是一个{dom}知识图谱质量评估专家。下面是从同一条{dom}记录抽取的若干三元组。
请综合评估这些三元组整体的语义合理性，重点关注：关系是否符合{dom}常识、主谓宾是否颠倒/错位、
术语是否准确、信息是否自洽一致、层级关系是否正确。

三元组：
{body}

请只输出纯JSON（不要任何多余文字或代码块标记）：
{{"score": 0到1之间的小数, "reason": "简要原因"}}"""


def parse_score(content):
    content = re.sub(r"<think>[\s\S]*?</think>", "", content or "").strip()
    for cand in (content, content.strip("`").strip()):
        try:
            return float(json.loads(cand)["score"])
        except Exception:
            pass
    m = re.search(r"\{[\s\S]*\}", content)
    if m:
        try:
            return float(json.loads(m.group())["score"])
        except Exception:
            pass
    sm = re.search(r'"?score"?\s*[:：]\s*([0-9]*\.?[0-9]+)', content)
    return float(sm.group(1)) if sm else None


def score_one(rec, retry=3):
    triples = rec["triples"]
    if not triples:
        return rec["uid"], None
    prompt = build_prompt(rec["domain"], triples)
    for a in range(retry):
        try:
            r = client.chat.completions.create(
                model=MODEL, temperature=TEMPERATURE,
                messages=[{"role": "user", "content": prompt}])
            s = parse_score(r.choices[0].message.content)
            if s is not None:
                return rec["uid"], max(0.0, min(1.0, s))
        except Exception:
            time.sleep(1.5 * (a + 1))
    return rec["uid"], None


def main():
    ckpt = os.path.join(HERE, "sem_scores.csv")          # resumable checkpoint (uid,score)
    cache = [json.loads(l) for l in open(os.path.join(HERE, "triples_cache.jsonl"), encoding="utf-8")]
    df = pd.read_csv(os.path.join(HERE, "dataset.csv"))

    scores = {}
    if os.path.exists(ckpt):
        prev = pd.read_csv(ckpt)
        scores = {str(u): (None if pd.isna(s) else float(s)) for u, s in zip(prev["uid"], prev["score"])}
        print(f"resuming: {len(scores)} already scored", flush=True)
    todo = [rec for rec in cache if str(rec["uid"]) not in scores]
    total = len(cache)
    fh = open(ckpt, "a", encoding="utf-8")
    if os.path.getsize(ckpt) == 0 if os.path.exists(ckpt) else True:
        fh.write("uid,score\n"); fh.flush()
    done = [len(scores)]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(score_one, rec): rec["uid"] for rec in todo}
        for fut in as_completed(futs):
            uid, s = fut.result()
            scores[str(uid)] = s
            with _lock:
                fh.write(f"{uid},{'' if s is None else s}\n"); fh.flush()
            done[0] += 1
            if done[0] % 50 == 0:
                print(f"{done[0]}/{total} scored", flush=True)
    fh.close()

    df["S_sem"] = df["uid"].map(lambda u: (scores.get(u) * 100.0) if scores.get(u) is not None else float("nan"))
    df["sem_observed"] = df["uid"].map(lambda u: 1 if scores.get(u) is not None else 0)
    # impute missing by domain+variant mean
    for (dom, var), grp in df.groupby(["domain", "variant"]):
        m = grp.loc[grp["sem_observed"] == 1, "S_sem"].mean()
        if pd.isna(m):
            m = df.loc[df["sem_observed"] == 1, "S_sem"].mean()
        mask = (df["domain"] == dom) & (df["variant"] == var) & (df["S_sem"].isna())
        df.loc[mask, "S_sem"] = m
    df["S_sem"] = df["S_sem"].round(3)
    df.to_csv(os.path.join(HERE, "dataset.csv"), index=False)
    print(f"\nfilled S_sem for {sum(1 for v in scores.values() if v is not None)}/{total} docs")
    print(df.groupby("y_repair")["S_sem"].mean().round(2).to_string())


if __name__ == "__main__":
    main()
