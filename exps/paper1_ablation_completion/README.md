# Paper 1: matched component ablations (2026-09-24)

## Current status

Completed: 5,850 optimizer replay outcomes and 4,320 gate scores from 540 archived Gemma responses. See [report.md](report.md).

**New API experiments are incomplete.** The user confirmed scheduled service maintenance from September 24 through September 26, 2026. No further API checks or calls will be made during maintenance. The service timed out even with proxies bypassed. Four failure records are retained (16 recorded connection attempts); no successful model responses were received. The batch process was stopped. No factorial or index ablation outcome is reported. Planned protocols below are distinguished from completed offline results.

## Purpose and scope

Separate three questions: which steps help the one-call repair pipeline, which receipt evidence-index features help, and which switches affect the separately executed sequential optimizer. This follow-up reuses previously evaluated cases; it is not an additional untouched test set. No human-review material is read or changed.

## Locked design

- **Controlled / natural:** the same fixed 60 Chinese documents per condition; four contemporaneous calls per document for preprocessing P × diagnostic context D. Every response is scored both raw and filtered (G), giving eight configurations per condition. The system prompt, source, schema, model and generation settings stay fixed. Diagnosis uses the graph actually passed to that arm.
- **Receipts:** the existing 60-document follow-up test set; six contemporaneous arms: simple schema prompt, full evidence index, anchors without neighbour indices, random index, simple without explicit field definitions, and full index without explicit field definitions. All retain the complete numbered transcript. Neighbour ablation removes index pointers, not access to those source lines. Definition ablation removes the explicit definitions object, not relation names or all instructions.
- **Random control:** one fixed seeded realization per document/field, matched on anchor count and neighbour-index count. Select among 128 draws using anchor-text character-length difference alone; no semantic or reference-based selection. True anchors may overlap random ones. This is approximate character-length matching, not token matching; `placebo_diagnostics.csv` reports overlap and lengths and `cost.csv` reports tokens.
- **API:** 840 requested outcomes, only `google/gemma-4-26B-A4B-it`, temperature 0, completion cap 4,000, two workers, 3-second global launch spacing, at most four transport attempts. Responses and failures are saved immediately. Parse failures are not retried. All failed outcomes score as empty graphs. Credentials are read from local `apis`; proxies are bypassed. No model weights are downloaded.
- **Cost:** each P/D or index arm gets one completion request, with transport retries recorded. Raw and filtered scores share this request. Different context lengths are measured, not claimed to be token-identical. `wall_seconds` includes pacing and retry delay, so is operational request time rather than isolated model inference latency.

`manifest.json` freezes exact prompts, public inputs, runtime/scoring code, dependencies, archived inputs/proposals, and router weights/scaler before the first request. Gold references are accessed by scoring only. The required document head is declared task metadata historically stored in the benchmark reference record; no reference tails, relation-presence labels or injected defect labels enter prompts.

## Statistics

Primary metric: mean per-document exact multiset triple F1. For P, D, G, average paired differences over the other factors within each document. PD, PG and DG are differences of differences averaged over the remaining factor; PDG is the three-way contrast. Bootstrap and two-sided sign-randomization tests use 10,000 whole-document draws, seed 42. Holm adjustment is applied jointly to six primary effects (three factors × two conditions), and separately to the five predeclared receipt contrasts. Interactions and optimizer comparisons are exploratory. Confidence intervals are marginal 95% intervals, not multiplicity-adjusted intervals. Shared documents remain paired and are never counted as independent replicates across arms.

## Same-response filtering

Each stored response is scored with all checks, with each of five checks removed, with duplicate and cardinality jointly removed, and with all checks removed. Scan order stays fixed. Disabling source support can let an earlier false candidate consume a relation slot and displace a later correct candidate. Duplicate and cardinality checks can mask each other, so both individual and joint switches are necessary. Report actual candidate rejection reasons and reference membership; zero effect means no measured benefit in these responses, not that a check is universally unnecessary.

## Sequential optimizer: 13 variants × 225 documents × 2 conditions

The archived model proposals are reused without additional calls. Every variant starts from the same structurally preprocessed graph and uses the same per-relation edit-bundle adapter. The production optimizer source is unchanged. Full per-candidate trial graphs, profiles, utilities, decisions and stop reasons are saved.

| Variant | Change from always-on uniform reference |
|---|---|
| `uniform_always` | Actual production optimizer, uniform scale prior, repair probability 1 |
| `learned_always` | Archived neural scale prior, repair probability still 1 |
| `learned_trigger` | Archived neural prior and probability; compare with `learned_always` to isolate the trigger |
| `no_prior` | Set prior coefficient eta to zero |
| `no_cost` | Remove operation-cost penalty |
| `no_density` | Remove density upper bound |
| `no_profile_bounds` | Remove four profile lower-bound/regression checks; retain density and empty-graph protection |
| `single_step` | One iteration instead of default maximum 12 |
| `no_rule_candidates` | Remove detector-generated actions; keep fixed model proposals |
| `rule_only` | Remove model proposals; keep detector-generated actions |
| `no_local_score` | Zero non-isolation and non-redundancy quality terms and remove their bounds |
| `no_graph_score` | Zero logical-quality term and remove its bound |
| `no_source_score` | Zero source-support quality term and remove its bound |

The last three are **score/bound component ablations**, not removal of an entire assessment scale: violation detection, stopping rules, hard-violation reward and candidate generation remain active. Remaining quality weights retain original magnitudes; they are not renormalized. The old neural training features do not match deployment features and used reference relation presence. These replays measure the effect of existing weights; they do not validate neural training or establish an RL learning benefit.

## Run and inspect

```bash
python3 -m unittest exps.paper1_ablation_completion.test_protocol
python3 exps/paper1_ablation_completion/run.py freeze
python3 -u exps/paper1_ablation_completion/run.py run
python3 exps/paper1_ablation_completion/offline.py
python3 exps/paper1_ablation_completion/archive_traces.py
python3 exps/paper1_ablation_completion/archived_gate.py
python3 exps/paper1_ablation_completion/publish_offline.py
python3 exps/paper1_ablation_completion/validate_completed.py
# Only after all 840 API outcomes are available:
python3 exps/paper1_ablation_completion/analyze.py
python3 exps/paper1_ablation_completion/publish.py
```

Re-running `run` resumes missing outcomes only. `verify()` refuses changed frozen dependencies. Old study files and locks remain unchanged. Human annotations are still an independent pending evaluation; this study does not replace them.

The completed archived-filter analysis uses separate source hashes in `archived_gate_manifest.json`. It averages three generation arms within each of 60 documents per cohort and applies Holm adjustment across 21 exploratory contrasts. The full filter is checked against the original code for every response.

Full traces are committed as `optimizer_traces.jsonl.gz` (lossless compression). `trace_archive.json` records compressed and original SHA-256 hashes. Use `gzip -dk optimizer_traces.jsonl.gz` to restore the JSONL when it is not already present. Original JSONL is locally retained and Git-ignored to avoid storing 32 MB of repeated trial states.
