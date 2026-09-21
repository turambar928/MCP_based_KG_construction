# Paper 1 execution-path and mechanism audit

API run complete: True (360/360 records).

All new calls use Gemma. References are accessed only by the scorer.

| Study | Stream/stratum | Method | n | Repair | F1 | Exact |
|---|---|---|---:|---:|---:|---:|
| Source-field copy | controlled | source_field_copy | 225 | 1.0000 | 1.0000 | 1.0000 |
| Source-field copy | natural | source_field_copy | 225 | -- | 1.0000 | 1.0000 |
| Archived natural strata | all | diagnosis_gate | 225 | -- | 0.9248 | 0.6844 |
| Archived natural strata | all | input | 225 | -- | 0.8799 | 0.6578 |
| Archived natural strata | all | simple | 225 | -- | 0.8807 | 0.6711 |
| Archived natural strata | malformed | diagnosis_gate | 10 | -- | 0.6991 | 0.0000 |
| Archived natural strata | malformed | input | 10 | -- | 0.0000 | 0.0000 |
| Archived natural strata | malformed | simple | 10 | -- | 0.7143 | 0.0000 |
| Archived natural strata | parsed | diagnosis_gate | 215 | -- | 0.9353 | 0.7163 |
| Archived natural strata | parsed | input | 215 | -- | 0.9209 | 0.6884 |
| Archived natural strata | parsed | simple | 215 | -- | 0.8885 | 0.7023 |
| Archived natural strata | parsed_clean | diagnosis_gate | 148 | -- | 1.0000 | 1.0000 |
| Archived natural strata | parsed_clean | input | 148 | -- | 1.0000 | 1.0000 |
| Archived natural strata | parsed_clean | simple | 148 | -- | 0.9981 | 0.9932 |
| Archived natural strata | parsed_dirty | diagnosis_gate | 67 | -- | 0.7922 | 0.0896 |
| Archived natural strata | parsed_dirty | input | 67 | -- | 0.7461 | 0.0000 |
| Archived natural strata | parsed_dirty | simple | 67 | -- | 0.6464 | 0.0597 |
| Executed optimizer | controlled | learned | 225 | 0.3200 | 0.8472 | 0.0622 |
| Executed optimizer | controlled | uniform | 225 | 0.3200 | 0.8472 | 0.0622 |
| Executed optimizer | natural | learned | 225 | -- | 0.8833 | 0.6578 |
| Executed optimizer | natural | uniform | 225 | -- | 0.8833 | 0.6578 |
| Matched Gemma | controlled | base_gate | 60 | 0.9750 | 0.9962 | 0.9500 |
| Matched Gemma | controlled | base_raw | 60 | 0.9750 | 0.9951 | 0.9500 |
| Matched Gemma | controlled | diagnosis_gate | 60 | 0.9250 | 0.9861 | 0.8333 |
| Matched Gemma | controlled | diagnosis_raw | 60 | 0.9250 | 0.9850 | 0.8333 |
| Matched Gemma | controlled | shacl_context_gate | 60 | 0.9500 | 0.9912 | 0.9000 |
| Matched Gemma | controlled | shacl_context_raw | 60 | 0.9500 | 0.9912 | 0.9000 |
| Matched Gemma | natural | base_gate | 60 | -- | 0.9252 | 0.6667 |
| Matched Gemma | natural | base_raw | 60 | -- | 0.9185 | 0.6667 |
| Matched Gemma | natural | diagnosis_gate | 60 | -- | 0.9147 | 0.6667 |
| Matched Gemma | natural | diagnosis_raw | 60 | -- | 0.9079 | 0.6667 |
| Matched Gemma | natural | shacl_context_gate | 60 | -- | 0.9364 | 0.7000 |
| Matched Gemma | natural | shacl_context_raw | 60 | -- | 0.9322 | 0.7000 |

## Interpretation boundaries

- The deterministic source-field baseline obtains perfect recovery because the source evidence serializes the reference fields; current data cannot establish superiority over direct source reconstruction.
- Optimizer replay applies real trial-state selection to frozen proposals; it is not an additional model call or a trained RL policy.
- Old router features read reference relation presence; old router/LODO results are withdrawn as deployment evidence.
- The SHACL-context arm implements the M+G context design in Lin et al. (2025), Section 5, adapted to document fields and JSON full-graph output. It is not an official-code reproduction.
- The API budget is matched by call count and completion cap, not by input-token count. Raw and gated outputs within each arm share exactly the same response.
- Natural-reference evaluation remains silver; independent human annotations are pending.
