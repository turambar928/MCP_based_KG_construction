# -*- coding: utf-8 -*-
"""
Train the neural repair decision network f_phi (paper1 §3.2, Eq. decision_net / decision_loss).

Lightweight MLP (pure NumPy, no heavy deps): input [s; g] (8-dim, standardized)
-> 32 -> 16 (ReLU) -> two heads:
  - p_repair  (1 unit, sigmoid)                              supervised by y_repair    (BCE)
  - pi        (3 units, softmax over {entity,graph,context}) supervised by y_scale     (CE)
Joint loss L = BCE(p_repair, y) + lambda * CE(pi, y_scale),  lambda = 1.0.
The scale (CE) term is masked to instances carrying a defect (scale_label != none);
clean instances train the repair head only. Adam optimizer, early stopping on val loss.

Self-supervised labels (no manual annotation): y_repair from injected-defect provenance,
y_scale from defect-type->scale mapping. Saves fphi_model.npz, scaler.json, splits.json,
train_meta.json under exps/decision_network/.
"""
import os
import json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 42
LAMBDA = 1.0
EPOCHS = 4000
LR = 5e-3
PATIENCE = 200
H1, H2 = 32, 16
FEATURES = ["S_iso", "S_red", "S_log", "S_sem", "n_v", "n_e", "density", "n_viol_feat"]
SCALES = ["entity", "graph", "context"]
rng = np.random.default_rng(SEED)


def relu(x):
    return np.maximum(0, x)


def softmax(z):
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def init_params(d_in):
    def w(a, b):
        return rng.standard_normal((a, b)) * np.sqrt(2.0 / a)
    return {
        "W1": w(d_in, H1), "b1": np.zeros(H1),
        "W2": w(H1, H2), "b2": np.zeros(H2),
        "wr": w(H2, 1), "br": np.zeros(1),
        "Ws": w(H2, 3), "bs": np.zeros(3),
    }


def forward(P, X):
    z1 = X @ P["W1"] + P["b1"]; a1 = relu(z1)
    z2 = a1 @ P["W2"] + P["b2"]; a2 = relu(z2)
    logit_r = (a2 @ P["wr"] + P["br"]).ravel()
    logits_s = a2 @ P["Ws"] + P["bs"]
    cache = (X, z1, a1, z2, a2)
    return logit_r, logits_s, cache


def loss_and_grads(P, X, yr, ys, mask):
    n = X.shape[0]
    logit_r, logits_s, (X, z1, a1, z2, a2) = forward(P, X)
    pr = sigmoid(logit_r)
    bce = -np.mean(yr * np.log(pr + 1e-9) + (1 - yr) * np.log(1 - pr + 1e-9))
    ps = softmax(logits_s)
    m = mask.sum() + 1e-6
    ce = -np.sum(mask * np.log(ps[np.arange(n), ys] + 1e-9)) / m
    loss = bce + LAMBDA * ce

    g = {}
    d_logit_r = (pr - yr) / n                                  # (n,)
    d_logits_s = ps.copy()
    d_logits_s[np.arange(n), ys] -= 1.0
    d_logits_s *= (LAMBDA * mask[:, None]) / m                 # (n,3)

    g["wr"] = a2.T @ d_logit_r[:, None]; g["br"] = np.array([d_logit_r.sum()])
    g["Ws"] = a2.T @ d_logits_s; g["bs"] = d_logits_s.sum(0)
    da2 = d_logit_r[:, None] @ P["wr"].T + d_logits_s @ P["Ws"].T
    dz2 = da2 * (z2 > 0)
    g["W2"] = a1.T @ dz2; g["b2"] = dz2.sum(0)
    da1 = dz2 @ P["W2"].T
    dz1 = da1 * (z1 > 0)
    g["W1"] = X.T @ dz1; g["b1"] = dz1.sum(0)
    return loss, g, bce, ce


def stratified_split(df):
    idx_tr, idx_va, idx_te = [], [], []
    for _, grp in df.groupby(["domain", "y_repair"]):
        ii = grp.index.to_numpy().copy(); rng.shuffle(ii)
        n = len(ii); a, b = int(0.7 * n), int(0.85 * n)
        idx_tr += ii[:a].tolist(); idx_va += ii[a:b].tolist(); idx_te += ii[b:].tolist()
    return sorted(idx_tr), sorted(idx_va), sorted(idx_te)


def main():
    df = pd.read_csv(os.path.join(HERE, "dataset.csv"))
    df["n_viol_feat"] = df[["n_missing", "n_dup", "n_logconf"]].sum(axis=1)
    df = df.dropna(subset=["S_sem"]).reset_index(drop=True)

    tr, va, te = stratified_split(df)
    X = df[FEATURES].to_numpy(np.float64)
    mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-6
    Xn = (X - mu) / sd
    yr = df["y_repair"].to_numpy(np.float64)
    sidx = df["scale_label"].map({s: i for i, s in enumerate(SCALES)}).fillna(-1).to_numpy()
    mask = (sidx >= 0).astype(np.float64)
    ys = np.clip(sidx, 0, 2).astype(int)

    P = init_params(len(FEATURES))
    adam = {k: (np.zeros_like(v), np.zeros_like(v)) for k, v in P.items()}
    b1d, b2d, eps, t = 0.9, 0.999, 1e-8, 0
    best, best_P, bad = 1e9, None, 0
    for ep in range(EPOCHS):
        t += 1
        loss, g, _, _ = loss_and_grads(P, Xn[tr], yr[tr], ys[tr], mask[tr])
        for k in P:
            m, v = adam[k]
            m = b1d * m + (1 - b1d) * g[k]
            v = b2d * v + (1 - b2d) * (g[k] ** 2)
            adam[k] = (m, v)
            mh = m / (1 - b1d ** t); vh = v / (1 - b2d ** t)
            P[k] = P[k] - LR * mh / (np.sqrt(vh) + eps)
        vloss = loss_and_grads(P, Xn[va], yr[va], ys[va], mask[va])[0]
        if vloss < best - 1e-5:
            best, best_P, bad = vloss, {k: v.copy() for k, v in P.items()}, 0
        else:
            bad += 1
            if bad >= PATIENCE:
                break

    P = best_P
    np.savez(os.path.join(HERE, "fphi_model.npz"), **P)
    json.dump({"mu": mu.tolist(), "sd": sd.tolist(), "features": FEATURES, "scales": SCALES},
              open(os.path.join(HERE, "scaler.json"), "w"), indent=2)
    json.dump({"train": tr, "val": va, "test": te}, open(os.path.join(HERE, "splits.json"), "w"))
    n_params = int(sum(np.asarray(v).size for v in P.values()))
    meta = {
        "arch": f"MLP {len(FEATURES)}->{H1}->{H2}->(1 sigmoid p_repair + 3 softmax pi), ReLU",
        "params": n_params, "optimizer": f"Adam lr={LR}", "loss": "BCE + λ·CE (masked), λ=%.1f" % LAMBDA,
        "epochs_run": ep + 1, "best_val_loss": round(float(best), 4),
        "n_total": len(df), "n_train": len(tr), "n_val": len(va), "n_test": len(te),
        "split": "70/15/15 stratified by (domain, y_repair), seed=42",
        "label_source": "self-supervised, no manual annotation: y_repair from injected-defect "
                        "provenance; y_scale from defect-type→scale mapping (Eq. repair_label/scale_label)",
        "features": FEATURES, "seed": SEED,
    }
    json.dump(meta, open(os.path.join(HERE, "train_meta.json"), "w"), indent=2, ensure_ascii=False)
    print(json.dumps(meta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
