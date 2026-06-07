# -*- coding: utf-8 -*-
"""
Evaluate f_phi for paper1 §4.4.1:
  (1) Decision quality on the held-out test split  -> tab:decision_quality
      - p_repair: Accuracy, F1 (binary repair/skip) at tau_repair chosen on val
      - scale-prior pi: top-1 accuracy (argmax pi vs dominant defect scale), on defect-bearing docs
  (2) Efficiency simulation (cross-check for tab:decision_ablation):
      derive LLM-calls/doc, latency/doc and Q_score for "Full (with f_phi gating)" vs
      "No decision net (always repair)" from the test-set confusion matrix and a measured
      per-repair cost constant. Q-loss = false-negative rate x mean per-doc quality gain.

Writes decision_quality.json and efficiency_sim.json under exps/decision_network/.
"""
import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

HERE = os.path.dirname(os.path.abspath(__file__))
SCALES = ["entity", "graph", "context"]
# measured per-repair cost constants (filled from run_efficiency_real.py; defaults are placeholders
# overridden if efficiency_real.json exists)
DEFAULT_CALLS_PER_REPAIR = 1.0
DEFAULT_LATENCY_PER_REPAIR = 2.8     # s/doc when a repair is executed (no-search path baseline)
MEAN_GAIN = 8.9                       # mean Q gain per repaired doc (Exp2->Exp3 avg, paper §4.2)


def relu(x): return np.maximum(0, x)
def sigmoid(x): return 1 / (1 + np.exp(-x))
def softmax(z):
    z = z - z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)


def load_model():
    P = dict(np.load(os.path.join(HERE, "fphi_model.npz")))
    sc = json.load(open(os.path.join(HERE, "scaler.json")))
    return P, sc


def forward(P, X):
    a1 = relu(X @ P["W1"] + P["b1"])
    a2 = relu(a1 @ P["W2"] + P["b2"])
    pr = sigmoid((a2 @ P["wr"] + P["br"]).ravel())
    ps = softmax(a2 @ P["Ws"] + P["bs"])
    return pr, ps


def main():
    P, sc = load_model()
    feats, mu, sd = sc["features"], np.array(sc["mu"]), np.array(sc["sd"])
    df = pd.read_csv(os.path.join(HERE, "dataset.csv"))
    df["n_viol_feat"] = df[["n_missing", "n_dup", "n_logconf"]].sum(axis=1)
    df = df.dropna(subset=["S_sem"]).reset_index(drop=True)
    splits = json.load(open(os.path.join(HERE, "splits.json")))
    va, te = splits["val"], splits["test"]

    X = (df[feats].to_numpy(float) - mu) / sd
    yr = df["y_repair"].to_numpy(int)
    sidx = df["scale_label"].map({s: i for i, s in enumerate(SCALES)}).fillna(-1).to_numpy().astype(int)
    pr, ps = forward(P, X)

    # choose tau on val to maximize F1
    best_tau, best_f1 = 0.5, -1
    for tau in np.linspace(0.05, 0.95, 19):
        f1 = f1_score(yr[va], (pr[va] >= tau).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1, best_tau = f1, float(tau)

    pred_te = (pr[te] >= best_tau).astype(int)
    dq = {
        "tau_repair": round(best_tau, 3),
        "repair_accuracy": round(accuracy_score(yr[te], pred_te), 4),
        "repair_f1": round(f1_score(yr[te], pred_te, zero_division=0), 4),
        "repair_precision": round(precision_score(yr[te], pred_te, zero_division=0), 4),
        "repair_recall": round(recall_score(yr[te], pred_te, zero_division=0), 4),
        "n_test": len(te),
    }
    # scale top-1 on defect-bearing test docs
    te_def = [i for i in te if sidx[i] >= 0]
    pi_pred = ps[te_def].argmax(1)
    dq["scale_top1"] = round(accuracy_score(sidx[te_def], pi_pred), 4)
    dq["scale_f1_macro"] = round(f1_score(sidx[te_def], pi_pred, average="macro", zero_division=0), 4)
    dq["n_test_scale"] = len(te_def)
    json.dump(dq, open(os.path.join(HERE, "decision_quality.json"), "w"), indent=2)
    print("== decision quality ==\n", json.dumps(dq, indent=2))

    # ---- efficiency simulation from confusion matrix on test set ----
    real_path = os.path.join(HERE, "efficiency_real.json")
    cpr = DEFAULT_CALLS_PER_REPAIR; lpr = DEFAULT_LATENCY_PER_REPAIR; mg = MEAN_GAIN
    if os.path.exists(real_path):
        r = json.load(open(real_path))
        cpr = r.get("calls_per_repair", cpr); lpr = r.get("latency_per_repair", lpr)
        mg = r.get("mean_gain", mg)
    globals()["MEAN_GAIN"] = mg

    n = len(te)
    frac_pred_repair = pred_te.mean()                          # docs f_phi sends to repair
    fn = ((pred_te == 0) & (yr[te] == 1)).mean()               # missed real defects
    # no-decision-net repairs every doc; f_phi repairs only predicted-positives
    sim = {
        "calls_per_repair_used": cpr, "latency_per_repair_used": lpr, "mean_gain_used": MEAN_GAIN,
        "no_decision_net": {"calls_per_doc": round(cpr, 3),
                             "latency_per_doc": round(lpr, 3),
                             "Q_drop_vs_ideal": 0.0},
        "with_fphi": {"calls_per_doc": round(cpr * frac_pred_repair, 3),
                      "latency_per_doc": round(lpr * frac_pred_repair, 3),
                      "Q_drop_vs_ideal": round(fn * MEAN_GAIN, 3)},
        "calls_saved_pct": round((1 - frac_pred_repair) * 100, 1),
        "frac_pred_repair": round(float(frac_pred_repair), 3),
        "false_negative_rate": round(float(fn), 3),
    }
    json.dump(sim, open(os.path.join(HERE, "efficiency_sim.json"), "w"), indent=2)
    print("\n== efficiency simulation ==\n", json.dumps(sim, indent=2))


if __name__ == "__main__":
    main()
