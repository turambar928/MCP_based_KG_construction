# Paper 2 Dual-Strategy Ablation

This report is generated from existing `per_item_rule_suggestions.jsonl` logs. It does not call any LLM API.
The metrics are candidate-rule contribution metrics before the final manual/validation filtering used by the paper's 294-rule table.

## Source: `gov20`

| Strategy | Calls | Candidate rules | Coverage vs dual | Unique vs other | Overlap |
| --- | ---: | ---: | ---: | ---: | ---: |
| deletion | 20 | 285 | 0.483 | 262 | 23 |
| augmentation | 20 | 328 | 0.556 | 305 | 23 |
| dual | 40 | 590 | 1.000 | 567 | 23 |

Dual strategy gain over the stronger single strategy: 79.9%.

| Category | Deletion | Augmentation | Dual |
| --- | ---: | ---: | ---: |
| `entity_types` | 67 | 75 | 131 |
| `relationship_types` | 66 | 61 | 118 |
| `type_conflict_rules_forbidden` | 14 | 37 | 51 |
| `type_conflict_rules_allowed` | 22 | 36 | 58 |
| `hierarchy_rules` | 29 | 41 | 70 |
| `geo_hierarchy_rules` | 7 | 18 | 23 |
| `procedural_rules` | 80 | 60 | 139 |

## Source: `gov_full`

| Strategy | Calls | Candidate rules | Coverage vs dual | Unique vs other | Overlap |
| --- | ---: | ---: | ---: | ---: | ---: |
| deletion | 4728 | 32955 | 0.460 | 29973 | 2982 |
| augmentation | 4728 | 41683 | 0.582 | 38701 | 2982 |
| dual | 9456 | 71656 | 1.000 | 68674 | 2982 |

Dual strategy gain over the stronger single strategy: 71.9%.

| Category | Deletion | Augmentation | Dual |
| --- | ---: | ---: | ---: |
| `entity_types` | 4741 | 4916 | 8469 |
| `relationship_types` | 3445 | 3629 | 6221 |
| `type_conflict_rules_forbidden` | 2540 | 6425 | 8862 |
| `type_conflict_rules_allowed` | 3254 | 6192 | 9281 |
| `hierarchy_rules` | 5041 | 7707 | 12481 |
| `geo_hierarchy_rules` | 986 | 1330 | 2240 |
| `procedural_rules` | 12948 | 11484 | 24102 |

## Interpretation

- Deletion and augmentation both contribute non-overlapping candidate rules, supporting the complementarity claim.
- These values should be reported as candidate-rule ablation results, not as final precision/recall on the manually verified 94-case test set.
- Final precision/recall still requires the manually annotated test labels, which are not present in the current repository.
