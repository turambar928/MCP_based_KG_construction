# -*- coding: utf-8 -*-
"""
Compute independent-judge agreement for paper1 §4.3 Table (tab:sem_reliability).
Reads exps/semantic_reliability/rescored_triples.csv (qwen_score vs gemma_score)
and reports Pearson r, Spearman rho overall and per-domain, plus mean abs error.
"""
import os
import pandas as pd
from scipy.stats import pearsonr, spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "semantic_reliability")
CSV = os.path.join(OUT_DIR, "rescored_triples.csv")


def block(df, name):
    d = df.dropna(subset=["qwen_score", "gemma_score"])
    n = len(d)
    if n < 3:
        return f"{name:14s} n={n:<4d} (insufficient)"
    r, rp = pearsonr(d["qwen_score"], d["gemma_score"])
    rho, sp = spearmanr(d["qwen_score"], d["gemma_score"])
    mae = (d["qwen_score"] - d["gemma_score"]).abs().mean()
    # exact-agreement on the discrete 0/0.2/.../1.0 scale
    exact = (d["qwen_score"].round(1) == d["gemma_score"].round(1)).mean()
    return (f"{name:14s} n={n:<4d} Pearson r={r:.3f} (p={rp:.1e})  "
            f"Spearman rho={rho:.3f} (p={sp:.1e})  MAE={mae:.3f}  exact={exact:.1%}")


def main():
    df = pd.read_csv(CSV)
    parsed = df["gemma_score"].notna().sum()
    lines = []
    lines.append("==== Semantic Score Reliability: Qwen3-32B vs gemma-4-26B ====")
    lines.append(f"total sampled = {len(df)}, gemma parsed = {parsed}, "
                 f"parse-fail = {len(df) - parsed}")
    lines.append("")
    lines.append(block(df, "OVERALL"))
    lines.append("")
    for dom in ["government", "finance", "environment"]:
        lines.append(block(df[df["domain"] == dom], dom))
    lines.append("")
    for exp in ["Exp2", "Exp3"]:
        lines.append(block(df[df["exp"] == exp], exp))

    report = "\n".join(lines)
    print(report)
    with open(os.path.join(OUT_DIR, "agreement_report.txt"), "w") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()
