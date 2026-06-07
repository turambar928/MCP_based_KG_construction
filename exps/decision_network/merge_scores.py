# -*- coding: utf-8 -*-
"""Safety merge: ensure dataset.csv S_sem is filled from the sem_scores.csv checkpoint
(idempotent). Runs before training in case score_semantics.py was interrupted."""
import os, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(HERE, "dataset.csv"))
ck = os.path.join(HERE, "sem_scores.csv")
if os.path.exists(ck):
    sc = pd.read_csv(ck)
    sc = sc.dropna(subset=["score"])
    m = {str(u): float(s) * 100.0 for u, s in zip(sc["uid"], sc["score"])}
    obs = df["uid"].astype(str).map(lambda u: u in m)
    df["S_sem"] = df["uid"].astype(str).map(lambda u: m.get(u))
    df["sem_observed"] = obs.astype(int)
    for (dom, var), grp in df.groupby(["domain", "variant"]):
        mean = grp.loc[grp["sem_observed"] == 1, "S_sem"].mean()
        if pd.isna(mean):
            mean = df.loc[df["sem_observed"] == 1, "S_sem"].mean()
        mask = (df["domain"] == dom) & (df["variant"] == var) & (df["S_sem"].isna())
        df.loc[mask, "S_sem"] = mean
    df["S_sem"] = df["S_sem"].round(3)
    df.to_csv(os.path.join(HERE, "dataset.csv"), index=False)
    print(f"merged S_sem: observed={int(df['sem_observed'].sum())}/{len(df)}")
else:
    print("no checkpoint found")
