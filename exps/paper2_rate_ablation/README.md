# Current rate-reward component study

Fifty new models, five fixed variants × ten training seeds × 250 episodes, compare graph features, rule features, action masking, call cost and a development-calibrated small count penalty. The ten existing complete rate-DDQN models supply the seed/budget-matched baseline. Evaluation uses thirty new controlled corruption seeds on the same base graph, with a deterministic acquire-then-deficit control: 2,100 episodes total.

`manifest.json` predates training; `test_seal.json` pins all fifty checkpoints before evaluation. `calibration.json` records twenty development rollouts and the fixed coefficient 0.00016449255758142737. References enter only the scorer, not observation removal, coefficient fitting or policy action selection. No checkpoint/seed selection is performed.

**Clarification of the frozen `no_mask` description:** the manifest's phrase “environment rejects unavailable actions with existing penalty” is imprecise. The unchanged runtime executes its existing operators: a graph action without its module is a no-op, while repeated rule acquisition can still incur the normal call cost. There is no added blanket invalid-action penalty. The experiment removes the policy mask in both behavior and target selection; results count selections forbidden by the original availability mask. No runtime or outcome was changed to make the prose true.

All evaluation returns use the common rate reward, including models trained without call cost or with the small count coefficient. Calls are simulated acquisition units; actual API calls are zero. Full transition deltas, scorer-only fact changes and seeds are retained. This remains a registry study, not generated-rule RL or unseen-domain validation.

```bash
python3 -m unittest exps.paper2_rate_ablation.test_study
python3 exps/paper2_rate_ablation/train.py --workers 6
python3 exps/paper2_rate_ablation/evaluation.py
python3 exps/paper2_rate_ablation/analyze.py
```

Completed training/evaluation blocks are resumed from disk; protocol or checkpoint hash changes are refused. Results and interpretation are in `report_zh.md`; the separate disjoint-replication test is in `../paper2_scale_control/`.
