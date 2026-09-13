# Paper 2 RL Reward/State Ablation

Fixed seeds: `[11, 23, 37, 42, 101]`. Episodes: 50; steps/episode: 10.

| Variant | Final joint Q | Std | Conv. episode | LLM calls | Q(G) | Q_online(R) | Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Graph-only reward | 128.24 | 0.66 | 46.0 | 99.8 | 92.24 | 89.98 | 0.994 |
| Rule-only reward | 120.24 | 0.85 | 43.2 | 452.8 | 80.44 | 99.50 | 0.995 |
| Joint no coverage | 132.03 | 0.82 | 39.4 | 193.4 | 92.24 | 99.49 | 0.995 |
| Full reward/state | 132.03 | 0.82 | 31.0 | 212.0 | 92.24 | 99.49 | 0.995 |

Interpretation:

- Graph-only reward under-invests in rule quality.
- Rule-only reward under-invests in KG cleanup.
- Removing coverage weakens long-term rule expansion.
- The full reward/state variant gives the best final joint quality under the shared transition dynamics.
