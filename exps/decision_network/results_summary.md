# f_phi Results Summary (auto-generated)

## Training ([train_meta.json](train_meta.json))
- Architecture: MLP 8->32->16->(1 sigmoid p_repair + 3 softmax pi), ReLU
- Parameters: 884
- Optimizer: Adam lr=0.005; Loss: BCE + λ·CE (masked), λ=1.0
- Split: preassigned document-group 70/15/15 split from repair benchmark, seed=42
- Samples: total=2998, train=2098, val=450, test=450
- Epochs run: 1858, best val loss: 0.0001
- Labels: self-supervised, no manual annotation: y_repair from injected-defect provenance; y_scale from defect-type→scale mapping (Eq. repair_label/scale_label)

## Decision quality on held-out test ([decision_quality.json](decision_quality.json))
- Repair trigger p_repair (tau=0.05): Accuracy=1.0, F1=1.0, P=1.0, R=1.0  (n=450)
- Scale-prior pi top-1: 1.0  (macro-F1=1.0, n=225)

## Efficiency: full (with f_phi) vs no-decision-net ([efficiency_sim.json](efficiency_sim.json))
| Config | Q drop | LLM calls/doc | Latency/doc |
|---|---|---|---|
| No decision net (always repair) | 0.0 | 1.0 | 2.8 s |
| Full (with f_phi) | 0.0 | 0.5 | 1.4 s |

- Calls saved: 50.0%  (f_phi routes only 0.5 of docs to repair)
- False-negative rate (missed defects): 0.0
- Per-repair cost source: 2.8 s/doc, 1.0 call/doc
