# Fixed-policy graph-size control

This study constructs 1, 2, 4 and 8 disjoint, ID-renamed copies of the existing 873-node / 1,083-edge clean base graph. It then applies fresh controlled corruption seeds. It does not construct a large connected natural KG or introduce new document content.

At each scale, ten fixed learned seeds and five shared corruption scenarios compare rate-DDQN, original count-DDQN, development-calibrated small-count DDQN and acquire-then-deficit. All models were trained at the base size; no policy is retrained or selected by these results. There are 800 policy/scenario outcomes, with action and graph-change traces. Evaluation uses the common rate reward; rate, raw-count and fixed-small-count penalties are also tallied on the same trajectories.

This separates the numerical scaling of penalties and measures transfer of fixed policies. It does not alone prove that normalization improves learning across sizes. The small coefficient is calibrated only on the independent development rollouts documented in `../paper2_rate_ablation/calibration.json`.

A separate sequential resource measurement runs the heuristic three times per scale. Time includes environment initialization and the rollout under tracemalloc instrumentation. Memory is peak **traced Python allocations**, excluding the prebuilt clean graph, model loading and native tensors. These values are not total RSS and are not uninstrumented production latency. No API is called.

Reproduce with `python3 -m unittest exps.paper2_scale_control.test_study` and `python3 exps/paper2_scale_control/study.py`. Both the frozen design and the thirty loaded checkpoints are hashed before evaluation. Report all scales, not a selected curve.
