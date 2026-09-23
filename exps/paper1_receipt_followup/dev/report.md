# Receipt follow-up: dev

20 documents, 80 annotated fields.

|Method|F1|Exact graph|Normalized F1|Preservation|
|---|---:|---:|---:|---:|
|evidence_gate|0.8500|0.4000|0.8500|0.9500|
|evidence_raw|0.8500|0.4000|0.8500|0.9500|
|evidence_strict_gate|0.8500|0.4000|0.8500|0.9500|
|input|0.8000|0.5000|0.8000|1.0000|
|input_gate|0.8000|0.5000|0.8000|1.0000|
|shacl_gate|0.8000|0.3000|0.8000|0.9500|
|shacl_raw|0.8000|0.3000|0.8000|0.9500|
|shacl_strict_gate|0.8000|0.3000|0.8000|0.9500|
|simple_gate|0.8250|0.3500|0.8250|0.9375|
|simple_raw|0.8250|0.3500|0.8250|0.9375|
|simple_strict_gate|0.8250|0.3500|0.8250|0.9375|

Primary comparison: {"left": "evidence_gate", "right": "simple_gate", "n": 20, "triple_f1": {"difference": 0.025, "ci": [-0.025, 0.075], "paired_randomization_p": 0.6219378062193781}, "exact_match": {"difference": 0.05, "ci": [-0.1, 0.2], "paired_randomization_p": 1.0}}

Graph changes: {"simple": 11, "evidence": 11, "shacl": 10}
