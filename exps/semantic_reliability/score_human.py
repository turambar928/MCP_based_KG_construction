# -*- coding: utf-8 -*-
"""
Compute human-agreement statistics for paper1 §4.3 once human_annotation_sheet.csv is filled:
  - Pearson r between mean human score and the automatic S_sem (Qwen)
  - Pearson r between mean human score and the independent Gemma judge
  - Cohen's kappa between annotators (pairwise mean, on the discrete 0..1 / 0.2 scale)
Writes human_agreement.txt. Run after annotators fill the sheet.
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import cohen_kappa_score

HERE = os.path.dirname(os.path.abspath(__file__))
sheet = pd.read_csv(os.path.join(HERE, "human_annotation_sheet.csv"))
key = pd.read_csv(os.path.join(HERE, "answer_key.csv"))
df = sheet.merge(key[["id", "qwen_score", "gemma_score"]], on="id")

ann_cols = [c for c in ["annotator1_score", "annotator2_score", "annotator3_score"] if c in df.columns]
for c in ann_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")
filled = [c for c in ann_cols if df[c].notna().sum() >= 3]
if not filled:
    print("No annotator columns filled yet — fill human_annotation_sheet.csv first.")
    raise SystemExit

df["human_mean"] = df[filled].mean(axis=1)
d = df.dropna(subset=["human_mean", "qwen_score"])
out = ["==== Human agreement (paper1 §4.3) ===="]
out.append(f"annotators used: {filled}; n={len(d)}")
r_q, p_q = pearsonr(d["human_mean"], d["qwen_score"])
out.append(f"Human vs Qwen S_sem : Pearson r={r_q:.3f} (p={p_q:.1e})")
if d["gemma_score"].notna().sum() > 3:
    r_g, p_g = pearsonr(d["human_mean"], d["gemma_score"])
    out.append(f"Human vs Gemma judge: Pearson r={r_g:.3f} (p={p_g:.1e})")
if len(filled) >= 2:
    # For 6-level ordinal scores, quadratic-weighted kappa (credits near-agreement) and
    # inter-annotator correlation are the appropriate agreement measures; unweighted kappa
    # is overly harsh because it treats 0.8-vs-1.0 the same as 0.0-vs-1.0.
    kq, ku, prs, sps = [], [], [], []
    for i in range(len(filled)):
        for j in range(i + 1, len(filled)):
            dd = df.dropna(subset=[filled[i], filled[j]])
            li = (dd[filled[i]] * 5).round().astype(int)
            lj = (dd[filled[j]] * 5).round().astype(int)
            kq.append(cohen_kappa_score(li, lj, weights="quadratic"))
            ku.append(cohen_kappa_score(li, lj))
            prs.append(pearsonr(dd[filled[i]], dd[filled[j]])[0])
            sps.append(spearmanr(dd[filled[i]], dd[filled[j]])[0])
    # Krippendorff's alpha (ordinal + interval) over all filled raters via the coincidence matrix
    M = df[filled].dropna().to_numpy(float)
    levels = sorted(set(M.flatten())); ix = {v: i for i, v in enumerate(levels)}; V = len(levels)
    o = np.zeros((V, V))
    for u in range(M.shape[0]):
        row = M[u]; mu = len(row)
        for a in range(mu):
            for b in range(mu):
                if a != b:
                    o[ix[row[a]], ix[row[b]]] += 1.0 / (mu - 1)
    nc = o.sum(1); ntot = nc.sum()

    def d_interval(c, k): return (levels[c] - levels[k]) ** 2

    def d_ordinal(c, k):
        lo, hi = min(c, k), max(c, k)
        return (sum(nc[g] for g in range(lo, hi + 1)) - (nc[c] + nc[k]) / 2.0) ** 2

    def alpha(d):
        Do = sum(o[c, k] * d(c, k) for c in range(V) for k in range(V)) / ntot
        De = sum(nc[c] * nc[k] * d(c, k) for c in range(V) for k in range(V)) / (ntot * (ntot - 1))
        return 1 - Do / De

    out.append(f"Inter-annotator agreement over {len(filled)} annotators:")
    out.append(f"  Krippendorff's alpha (ordinal)            = {alpha(d_ordinal):.3f}")
    out.append(f"  Krippendorff's alpha (interval)           = {alpha(d_interval):.3f}")
    out.append(f"  mean pairwise quadratic-weighted kappa    = {np.mean(kq):.3f} (std {np.std(kq):.3f})")
    out.append(f"  mean pairwise unweighted kappa            = {np.mean(ku):.3f}")
    out.append(f"  mean pairwise Pearson r = {np.mean(prs):.3f}  |  Spearman rho = {np.mean(sps):.3f}")
rep = "\n".join(out)
print(rep)
open(os.path.join(HERE, "human_agreement.txt"), "w").write(rep + "\n")
