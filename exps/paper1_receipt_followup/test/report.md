# Receipt follow-up: test

60 documents, 240 annotated fields.

|Method|F1|Exact graph|Normalized F1|Preservation|
|---|---:|---:|---:|---:|
|evidence_gate|0.8351|0.4000|0.8643|0.9306|
|evidence_raw|0.8333|0.4000|0.8625|0.9306|
|evidence_strict_gate|0.8351|0.4000|0.8643|0.9306|
|input|0.7833|0.3500|0.7958|1.0000|
|input_gate|0.7833|0.3500|0.7958|1.0000|
|shacl_gate|0.7833|0.2833|0.8042|0.9347|
|shacl_raw|0.7833|0.2833|0.8042|0.9347|
|shacl_strict_gate|0.7833|0.2833|0.8042|0.9347|
|simple_gate|0.7875|0.2833|0.8083|0.9250|
|simple_raw|0.7875|0.2833|0.8083|0.9250|
|simple_strict_gate|0.7875|0.2833|0.8083|0.9250|

Primary comparison: {"left": "evidence_gate", "right": "simple_gate", "n": 60, "triple_f1": {"difference": 0.04761904761904762, "ci": [0.025, 0.07263392857142836], "paired_randomization_p": 0.00039996000399960006}, "exact_match": {"difference": 0.11666666666666667, "ci": [0.05, 0.2], "paired_randomization_p": 0.015998400159984}}

Graph changes: {"simple": 31, "evidence": 39, "shacl": 28}
