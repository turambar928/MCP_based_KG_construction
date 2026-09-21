# Independent receipt evaluation

60 fixed SROIE documents; 239 annotated fields; missing address label excluded only in scoring.

|Method|Strict F1|Exact graph|Normalized F1|Preservation|
|---|---:|---:|---:|---:|
|base_gate|0.7915|0.3333|0.8123|0.9944|
|base_raw|0.7944|0.3333|0.8153|1.0000|
|diagnosis_gate|0.7915|0.3333|0.8123|0.9944|
|diagnosis_raw|0.7944|0.3333|0.8153|1.0000|
|input|0.7944|0.3333|0.8153|1.0000|
|rule_only|0.7944|0.3333|0.8153|1.0000|
|shacl_context_gate|0.7956|0.3333|0.8165|0.9944|
|shacl_context_raw|0.7986|0.3333|0.8194|1.0000|
|source_field_copy|0.0000|0.0000|0.0000|0.0000|

Literal source coverage: {'annotated_fields': 239, 'literal_source_fields': 220}.
Rejected candidates: 3; exact reference: 3; normalized reference: 3.

Paired document-bootstrap intervals, randomization comparisons and measured costs are in results.json.
