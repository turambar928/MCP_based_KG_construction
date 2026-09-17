# Paper 2 Co-optimization Benchmark

## Scope

This is an executable controlled-corruption benchmark. TNEWS/CLUE records are converted into graph objects; each graph action mutates that graph and all quality metrics are recomputed after the mutation. Rule actions acquire executable validation modules, and graph repairs are unavailable until their matching module is active. The corruption manifest is private to the environment and is never included in the policy state.

- Clean graph: 873 nodes and 1,083 relations
- Evaluation: 10 paired fixed seeds
- Training: 250 episodes per learned-policy seed
- Network: 14 -> 32 -> 16 -> 8
- Training API calls: 0 (stored rule-generation logs are audited separately)
- Total runtime: 1278.99 seconds

## Results

| Policy | Final joint quality | AUC | Steps to 0.98 | Calls | Edits |
| --- | ---: | ---: | ---: | ---: | ---: |
| Random | 0.9535 +/- 0.0266 | 0.8829 +/- 0.0318 | 19.00 | 8.30 | 151.40 |
| Enhancement Only | 0.6785 +/- 0.0036 | 0.6785 +/- 0.0036 | 19.00 | 0.00 | 0.00 |
| Rule Only | 0.9373 +/- 0.0036 | 0.9225 +/- 0.0036 | 19.00 | 18.00 | 24.00 |
| Alternating | 0.9634 +/- 0.0007 | 0.9261 +/- 0.0020 | 19.00 | 12.00 | 215.00 |
| Rule First Then Fix | 0.9747 +/- 0.0004 | 0.9365 +/- 0.0024 | 19.00 | 8.00 | 232.70 |
| Fix First Then Rule | 0.9330 +/- 0.0036 | 0.8204 +/- 0.0036 | 19.00 | 12.00 | 13.00 |
| Myopic Greedy | 0.9825 +/- 0.0001 | 0.9576 +/- 0.0009 | 13.20 | 4.00 | 242.20 |
| DQN | 0.9813 +/- 0.0017 | 0.9530 +/- 0.0041 | 16.80 | 4.10 | 233.80 |
| Double DQN | 0.9812 +/- 0.0013 | 0.9531 +/- 0.0021 | 17.00 | 4.00 | 234.90 |

## Paired test

Comparison: Double DQN vs Rule First Then Fix (10 paired seeds).
The model-informed myopic policy is reported as an upper-bound diagnostic and is excluded from selection of the non-oracle comparator because it clones the environment and evaluates every one-step transition before acting.

- Final quality difference: 0.0065, 95% paired bootstrap CI [0.0058, 0.0071], one-sided Wilcoxon p=0.000977.
- AUC difference: 0.0166, 95% paired bootstrap CI [0.0156, 0.0178], one-sided Wilcoxon p=0.000977.

## Interpretation limits

The benchmark validates the sequential-control claim, replay buffer, target network, Bellman updates, and actual graph-state transitions. Its defects are controlled injections and its rule modules are executable benchmark validators; therefore it does not estimate unconstrained real-world rule discovery accuracy. Rule-generation quality is evaluated separately using the archived LLM outputs and RuleTest-94.
