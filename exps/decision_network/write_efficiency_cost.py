# -*- coding: utf-8 -*-
"""Derive per-repair cost from the archived held-out repair benchmark."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SUMMARY = os.path.join(HERE, "..", "paper1_repair_benchmark", "summary.json")
rows = json.load(open(SUMMARY, encoding="utf-8"))
overall = {(row["method"], row["domain"]): row for row in rows}
ours = overall[("ours", "ALL")]
no_repair = overall[("no_repair", "ALL")]
cost = {
    "calls_per_repair": ours["calls"],
    "latency_per_repair": ours["latency_sec"],
    "mean_defect_repair_gain": ours["defect_repair_rate"] - no_repair["defect_repair_rate"],
    "source": "exps/paper1_repair_benchmark/summary.json; held-out test mean for Ours (225 documents)",
}
json.dump(cost, open(os.path.join(HERE, "efficiency_real.json"), "w"), indent=2, ensure_ascii=False)
print("wrote efficiency_real.json:", cost)
