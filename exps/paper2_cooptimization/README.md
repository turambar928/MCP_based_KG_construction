# Executable co-optimization benchmark

Run the formal experiment from the repository root:

```bash
python3 exps/paper2_cooptimization/run_experiment.py --seeds 10 --episodes 250 --per-label 30
```

The runner constructs a TNEWS/CLUE graph, injects four controlled defect families per seed, and applies every selected graph operation to the graph object. Rule actions activate executable validation modules; the policy never observes the corruption manifest. DQN and Double DQN share the 14-32-16-8 network, replay settings, exploration schedule, and paired evaluation scenarios.

`Myopic Greedy` clones the environment and evaluates every feasible one-step action. It is retained as a model-informed upper bound and excluded when selecting the strongest non-oracle baseline for the paired hypothesis test.

See `report.md` for results and `results.json` for the complete configuration and statistical output.
