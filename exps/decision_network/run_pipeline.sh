#!/bin/bash
# Autonomous f_phi pipeline: waits for S_sem scoring to finish, then trains, evaluates,
# and summarizes. Safe to launch with nohup; logs to pipeline.log.
set -e
ROOT=/home/taozifu2025/MCP_based_KG_construction
DN=$ROOT/exps/decision_network
cd $ROOT
source .venv/bin/activate 2>/dev/null || true

echo "[$(date +%H:%M:%S)] waiting for semantic scoring to finish..."
# wait until score_semantics process is gone OR checkpoint reaches the full count
while pgrep -f score_semantics.py >/dev/null 2>&1; do
  n=$(($(wc -l < $DN/sem_scores.csv 2>/dev/null || echo 1) - 1))
  echo "[$(date +%H:%M:%S)] scoring... $n done"
  sleep 30
done
echo "[$(date +%H:%M:%S)] scoring finished."

echo "[$(date +%H:%M:%S)] merge safety + train + cost + eval + summarize"
python3 $DN/merge_scores.py
python3 $DN/train_fphi.py
python3 $DN/write_efficiency_cost.py
python3 $DN/eval_fphi.py
python3 $DN/summarize_results.py
echo "[$(date +%H:%M:%S)] PIPELINE DONE -> see results_summary.md / paper_values.txt"
