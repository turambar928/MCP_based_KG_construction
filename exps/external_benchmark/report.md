# External Benchmark Report

All benchmarks are local and deterministic; no LLM/API calls are used.

## TNEWS/CLUE End-to-End KG Quality Benchmark

- Documents: 3000
- Categories: 15
- Runtime: 0.101s

| Stage | Nodes | Relations | Isolated | Duplicate | Invalid Rel. | Dangling | Q |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| clean | 10871 | 20827 | 0.000 | 0.004 | 0.000 | 0.000 | 99.89 |
| corrupted | 11414 | 22909 | 0.048 | 0.086 | 0.050 | 0.000 | 94.93 |
| repaired | 10822 | 19799 | 0.000 | 0.000 | 0.000 | 0.000 | 100.00 |

Quality recovery from corrupted state toward the ideal-quality target: 100.0%.

## RuleTest-94 Detection Benchmark

Label distribution: `{'pass': 30, 'fail': 60, 'specialist_miss': 4}`

| Detector | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| expert | 1.000 | 0.469 | 0.638 | 0.638 | 30 | 0 | 30 | 34 |
| system | 1.000 | 1.000 | 1.000 | 1.000 | 64 | 0 | 30 | 0 |

The system detector extends expert structural checks with complex procedural/missing-field and specialist-rule checks.

## Scope and Limitations

- The TNEWS/CLUE benchmark evaluates the local KG quality-enhancement pipeline under deterministic extraction and injected defects; it does not measure LLM extraction quality.
- RuleTest-94 is a labeled local rule-detection benchmark. Its perfect system score should be interpreted as passing this designed rule suite, not as evidence of universal real-world precision.
- The API information in `apis` can be used to add an LLM-extraction benchmark mode later, but this run intentionally avoids network/model variance.
