# CUAD test results

Documents: 56. Exact source-span field agreement; not the official CUAD QA metric.

|Arm|F1 (%)|Correct facts lost|New incorrect facts|Failed outputs|Actual requests|
|---|---:|---:|---:|---:|---:|
|initial|46.76|0|0|0|59|
|repair_simple|43.35|7|2|3|71|
|repair_index|44.84|5|12|2|69|
|extract_index|44.12|8|32|2|71|

Primary indexed repair − indexed extraction: 0.72 pp, 95% paired CI [-4.801622732426304, 6.481009070294784], sign-flip p=0.81010.

Repair costs exclude initial creation, listed separately in initial; paired workflow cost is initial+repair. Latency includes pacing and retries; summed latency is not batch wall time.

Human semantic review is pending.
