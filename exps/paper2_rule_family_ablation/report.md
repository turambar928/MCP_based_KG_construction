# Paper 2 Rule-Family Final Ablation

This benchmark evaluates executable rule families on RuleTest-94.
It complements the candidate-count ablation and should be interpreted as a deterministic rule-family ablation, not as per-rule provenance labeling.

Label distribution: `{'pass': 30, 'hierarchy_reversal': 10, 'absurd_relation': 10, 'reverse_supervision': 10, 'procedural_or_missing': 30, 'specialist_rule': 4}`

| Strategy | Precision | Recall | F1 | Accuracy | Family coverage | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Deletion-family only | 1.000 | 0.531 | 0.694 | 0.681 | 0.400 | 34 | 0 | 30 | 30 |
| Augmentation-family only | 1.000 | 0.469 | 0.638 | 0.638 | 0.600 | 30 | 0 | 30 | 34 |
| Dual strategy | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 64 | 0 | 30 | 0 |

Interpretation:

- Deletion-family rules cover procedural/missing-field and specialist constraints.
- Augmentation-family rules cover structural relation, hierarchy, and type-direction constraints.
- The dual strategy is the union and reaches full coverage on this designed benchmark.
