# Conditional generated-rule learning experiment

This runner is prepared for the **second development gate** in `../paper2_docred_v2_round2/pilot_results.json`. Preparation is not a completed experiment: if that gate fails, `run.py freeze` refuses expansion, and no formal collection or training is authorized by this protocol. No old eight-action weights are loaded.

The runtime has a fresh 14→64→64→4 network and masked DQN / Double DQN updates, terminal bootstrap suppression, a fixed 250-episode schedule, and a legacy-reward DDQN comparison. All three use ten seeds, final checkpoints only, and identical cached packets. Unit tests use synthetic fixtures and are excluded from experiment denominators.

When the gate passes, the sequence from the repository root is:

```bash
/tmp/kgbench-local-venv/bin/python -m unittest exps.paper2_docred_formal.test_runtime exps.paper2_docred_formal.test_run
/tmp/kgbench-local-venv/bin/python exps/paper2_docred_formal/run.py freeze
/tmp/kgbench-local-venv/bin/python exps/paper2_docred_formal/run.py collect_train
/tmp/kgbench-local-venv/bin/python exps/paper2_docred_formal/run.py train
/tmp/kgbench-local-venv/bin/python exps/paper2_docred_formal/run.py collect_test
/tmp/kgbench-local-venv/bin/python exps/paper2_docred_formal/analyze.py
```

The fixed source split has 180 training documents (90 pairs) and 60 test documents (30 pairs), with equal clean/perturbed documents in each. Public graph construction and scorer-only references are separate. Generation sees only public records, source text and given entities/types. Formal inference uses public observations and cached packet arrivals; no scorer input is passed to action selection. Returned model identity must match Gemma. Credentials are read without printing, proxies are bypassed, and previous outcomes are never replaced. Raw source/response files stay in ignored `local/`.

Expected nominal generation: 360 training rule responses, 120 test rule responses, 60 test direct repair responses, plus retained retries. The simple comparator uses one direct keep-ID repair call per document, **two per episode**, under the same source and relation permissions. Empty or malformed responses preserve input; valid empty selections receive the same episode-level emptying guard. The scheduler has four available response packets; this is a measured quality/cost comparison, not equal-call performance. Network failure accounting is fixed before calls.

Final evaluation includes stop, acquire-then-repair, repair-when-feasible, uniform-feasible, and the two-call direct comparator. Eight primary tests compare DDQN against DQN and the three main nonlearned comparators for F1 and correct-reference preservation, with Holm correction. Ten paired run-seed means quantify training variation on shared test documents; they are not 600 independent documents. All cached evaluation makes zero API requests; source collection cost is reported separately.

The task measures recovery of independently constructed reference graphs and removal of injected items, not correctness of natural extraction. Human semantic review remains deferred.
