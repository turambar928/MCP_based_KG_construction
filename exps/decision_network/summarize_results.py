# -*- coding: utf-8 -*-
"""Collect train_meta.json + decision_quality.json + efficiency_sim.json into
results_summary.md and emit paper-ready LaTeX table values (paper_values.txt)."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))


def L(p):
    return json.load(open(os.path.join(HERE, p))) if os.path.exists(os.path.join(HERE, p)) else {}


m, dq, ef = L("train_meta.json"), L("decision_quality.json"), L("efficiency_sim.json")
wf, nd = ef.get("with_fphi", {}), ef.get("no_decision_net", {})

md = f"""# f_phi Results Summary (auto-generated)

## Training ([train_meta.json](train_meta.json))
- Architecture: {m.get('arch')}
- Parameters: {m.get('params')}
- Optimizer: {m.get('optimizer')}; Loss: {m.get('loss')}
- Split: {m.get('split')}
- Samples: total={m.get('n_total')}, train={m.get('n_train')}, val={m.get('n_val')}, test={m.get('n_test')}
- Epochs run: {m.get('epochs_run')}, best val loss: {m.get('best_val_loss')}
- Labels: {m.get('label_source')}

## Decision quality on held-out test ([decision_quality.json](decision_quality.json))
- Repair trigger p_repair (tau={dq.get('tau_repair')}): Accuracy={dq.get('repair_accuracy')}, F1={dq.get('repair_f1')}, P={dq.get('repair_precision')}, R={dq.get('repair_recall')}  (n={dq.get('n_test')})
- Scale-prior pi top-1: {dq.get('scale_top1')}  (macro-F1={dq.get('scale_f1_macro')}, n={dq.get('n_test_scale')})

## Efficiency: full (with f_phi) vs no-decision-net ([efficiency_sim.json](efficiency_sim.json))
| Config | Q drop | LLM calls/doc | Latency/doc |
|---|---|---|---|
| No decision net (always repair) | {nd.get('Q_drop_vs_ideal')} | {nd.get('calls_per_doc')} | {nd.get('latency_per_doc')} s |
| Full (with f_phi) | {wf.get('Q_drop_vs_ideal')} | {wf.get('calls_per_doc')} | {wf.get('latency_per_doc')} s |

- Calls saved: {ef.get('calls_saved_pct')}%  (f_phi routes only {ef.get('frac_pred_repair')} of docs to repair)
- False-negative rate (missed defects): {ef.get('false_negative_rate')}
- Per-repair cost source: {ef.get('latency_per_repair_used')} s/doc, {ef.get('calls_per_repair_used')} call/doc
"""
open(os.path.join(HERE, "results_summary.md"), "w", encoding="utf-8").write(md)

# paper-ready values
pv = f"""PAPER VALUES (paper1 §4.4.1)
tab:decision_quality
  Repair trigger p_repair : Accuracy={dq.get('repair_accuracy')}  F1={dq.get('repair_f1')}
  Scale-prior pi (top-1)  : Acc={dq.get('scale_top1')}  macroF1={dq.get('scale_f1_macro')}
tab:decision_ablation
  Full (with f_phi)                 : Q_drop={wf.get('Q_drop_vs_ideal')}  calls/doc={wf.get('calls_per_doc')}  latency/doc={wf.get('latency_per_doc')}s
  No decision net (always repair)   : Q_drop={nd.get('Q_drop_vs_ideal')}  calls/doc={nd.get('calls_per_doc')}  latency/doc={nd.get('latency_per_doc')}s
  calls_saved={ef.get('calls_saved_pct')}%  tau_repair={dq.get('tau_repair')}
Setup paragraph: arch={m.get('arch')}; params={m.get('params')}; {m.get('n_train')}/{m.get('n_val')}/{m.get('n_test')} train/val/test; {m.get('optimizer')}.
"""
open(os.path.join(HERE, "paper_values.txt"), "w", encoding="utf-8").write(pv)
print(md)
print(pv)
