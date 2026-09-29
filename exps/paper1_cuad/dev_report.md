# CUAD dev results

Documents: 20. Exact source-span field agreement; not the official CUAD QA metric.

|Arm|F1 (%)|Correct facts lost|New incorrect facts|Failed outputs|Actual requests|
|---|---:|---:|---:|---:|---:|
|initial|46.56|0|0|0|20|
|repair_simple|47.78|0|1|0|21|
|repair_index|47.56|0|6|0|21|
|extract_index|47.58|2|14|0|22|

Primary indexed repair − indexed extraction: -0.03 pp, 95% paired CI [-4.5, 4.444444444444444], sign-flip p=1.00000.

Repair costs exclude initial creation, listed separately in initial; paired workflow cost is initial+repair. Latency includes pacing and retries; summed latency is not batch wall time.

Human semantic review is pending.
