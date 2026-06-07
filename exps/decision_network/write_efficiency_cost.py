# -*- coding: utf-8 -*-
"""
Write efficiency_real.json — the per-repair cost constants used by eval_fphi.py to turn
f_phi's measured gating ratio into calls/doc and latency/doc.

These constants are anchored to REAL measurements already in paper1:
  - latency_per_repair = 2.8 s/doc  : the paper's measured "No-Search (LLM-only fallback)"
    enhancement latency (Table tab:websearch_ablation, government domain) — i.e. the cost of
    actually running one enhancement pass on a document.
  - calls_per_repair  = 1.0         : the enhancement pipeline issues ~1 LLM call/doc
    (content_enhancement/logic_analyzer.py fact-check+inference call).
  - mean_gain         = 8.89        : mean comprehensive-quality gain of a repaired document
    (Exp3 avg 80.74 - Exp2 avg 71.85, paper §4.2).
So the efficiency table = (measured per-repair cost) x (measured f_phi gating ratio).
"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
cost = {
    "calls_per_repair": 1.0,
    "latency_per_repair": 2.8,
    "mean_gain": 8.89,
    "source": "latency=paper tab:websearch_ablation no-search 2.8s/doc; calls=pipeline ~1 LLM/doc; "
              "mean_gain=Exp3-Exp2 avg (80.74-71.85).",
}
json.dump(cost, open(os.path.join(HERE, "efficiency_real.json"), "w"), indent=2, ensure_ascii=False)
print("wrote efficiency_real.json:", cost)
