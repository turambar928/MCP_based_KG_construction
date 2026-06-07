# f_phi Results Summary (auto-generated)

## Training ([train_meta.json](train_meta.json))
- Architecture: MLP 8->32->16->(1 sigmoid p_repair + 3 softmax pi), ReLU
- Parameters: 884
- Optimizer: Adam lr=0.005; Loss: BCE + λ·CE (masked), λ=1.0
- Split: 70/15/15 stratified by (domain, y_repair), seed=42
- Samples: total=2900, train=2026, val=438, test=436
- Epochs run: 515, best val loss: 1.3758
- Labels: self-supervised, no manual annotation: y_repair from injected-defect provenance; y_scale from defect-type→scale mapping (Eq. repair_label/scale_label)

## Decision quality on held-out test ([decision_quality.json](decision_quality.json))
- Repair trigger p_repair (tau=0.4): Accuracy=0.7959, F1=0.7866, P=0.8241, R=0.7523  (n=436)
- Scale-prior pi top-1: 0.4944  (macro-F1=0.3758, n=180)

## Efficiency: full (with f_phi) vs no-decision-net ([efficiency_sim.json](efficiency_sim.json))
| Config | Q drop | LLM calls/doc | Latency/doc |
|---|---|---|---|
| No decision net (always repair) | 0.0 | 1.0 | 2.8 s |
| Full (with f_phi) | 1.101 | 0.456 | 1.278 s |

- Calls saved: 54.4%  (f_phi routes only 0.456 of docs to repair)
- False-negative rate (missed defects): 0.124
- Per-repair cost source: 2.8 s/doc, 1.0 call/doc
