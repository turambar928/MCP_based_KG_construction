# Paper 1 submission-extension experiments

## Strong simple-pipeline baseline on the controlled test set

| Method | Repair | F1 | Exact | Calls | Latency (s) |
|---|---:|---:|---:|---:|---:|
| Direct LLM | 0.924 | 0.952 | 0.827 | 1.000 | 7.248 |
| Simple pipeline | 0.951 | 0.963 | 0.840 | 1.000 | 9.275 |
| Full system | 0.980 | 0.992 | 0.933 | 1.000 | 11.445 |

## Naturally occurring extraction errors

| Method | Docs with errors | Error reduction | F1 | Exact | Calls |
|---|---:|---:|---:|---:|---:|
| Extracted graph (no repair) | 77 | 0.000 | 0.880 | 0.658 | 0.000 |
| Simple pipeline | 77 | -0.592 | 0.881 | 0.671 | 1.000 |
| Full system | 77 | 0.278 | 0.925 | 0.684 | 1.000 |

The natural-error input is produced by a real Claude extraction call from source text; no defect is injected. The structured source fields provide the reference graph.

## Constraint gate

The gate rejected 8 proposals. Reasons: `{"ungrounded": 8}`. Outcomes: `{"prevented_non_gold_triple": 8}`.

## Paired full-vs-simple tests

Controlled defects: `{"n_defects": 450, "full_only_success": 15, "simple_only_success": 2, "mcnemar_p": 0.002349853515625}`.

Natural extraction: `{"mean_triple_f1_difference": 0.04401585529862101, "triple_f1_difference_ci": [0.030672761019510233, 0.05766304761247999], "mean_errors_prevented_per_document": 1.031111111111111, "errors_prevented_ci": [0.7688888888888888, 1.3155555555555556], "wilcoxon_one_sided_p": 3.1767320650219532e-12, "full_only_exact": 3, "simple_only_exact": 0, "exact_match_mcnemar_p": 0.25}`.

## End-to-end router comparison

| Stream | Policy | Route F1 | Triple F1 | Exact | Calls/doc | Latency/doc |
|---|---:|---:|---:|---:|---:|---:|
| controlled | Always repair | 0.667 | 0.992 | 0.949 | 1.000 | 9.671 |
| controlled | Heuristic violations | 1.000 | 0.996 | 0.967 | 0.500 | 5.722 |
| controlled | Learned router | 1.000 | 0.996 | 0.967 | 0.500 | 5.722 |
| controlled | Never repair | 0.000 | 0.881 | 0.500 | 0.000 | 0.000 |
| controlled | Quality threshold | 1.000 | 0.996 | 0.967 | 0.500 | 5.722 |
| controlled | Random 50% | 0.476 | 0.934 | 0.711 | 0.489 | 4.971 |
| natural_extraction | Always repair | 0.292 | 0.958 | 0.824 | 1.000 | 8.087 |
| natural_extraction | Heuristic violations | 0.842 | 0.962 | 0.842 | 0.124 | 1.265 |
| natural_extraction | Learned router | 0.842 | 0.962 | 0.842 | 0.124 | 1.265 |
| natural_extraction | Never repair | 0.000 | 0.940 | 0.829 | 0.000 | 0.000 |
| natural_extraction | Quality threshold | 0.842 | 0.962 | 0.842 | 0.124 | 1.265 |
| natural_extraction | Random 50% | 0.242 | 0.943 | 0.822 | 0.489 | 4.019 |

## Leave-one-domain-out router evaluation

| Held-out | Trigger F1 | Scale top-1 | Scale macro-F1 |
|---|---:|---:|---:|
| environment | 1.000 | 1.000 | 1.000 |
| finance | 1.000 | 1.000 | 1.000 |
| government | 0.999 | 1.000 | 1.000 |

## Cross-model comparison on the fixed 60-case subset

| Model | Method | Repair | F1 | Exact | Latency |
|---|---:|---:|---:|---:|---:|
| Claude Haiku | Direct LLM | 0.958 | 0.970 | 0.867 | 8.188 |
| Claude Haiku | Simple pipeline | 0.958 | 0.966 | 0.833 | 10.523 |
| Claude Haiku | Full system | 0.975 | 0.991 | 0.917 | 10.924 |
| Gemma-4-26B-A4B-it | Direct LLM | 0.958 | 0.988 | 0.883 | 7.259 |
| Gemma-4-26B-A4B-it | Simple pipeline | 0.967 | 0.984 | 0.867 | 6.894 |
| Gemma-4-26B-A4B-it | Full system | 0.983 | 0.990 | 0.917 | 6.333 |

## Human annotation status

A frozen 200-item sample has been prepared. Two independent human labels and adjudication are still required; no model judgment is reported as human agreement.
