# CUAD cross-document-type validation

This is a new contract **source-span field repair task**, not official CUAD QA scoring. Sources: [CUAD repository](https://github.com/The-Atticus-Project/cuad), [dataset publisher and CC BY 4.0 statement](https://www.atticusprojectai.org/cuad). Attribution: Hendrycks, Burns, Chen and Ball (2021), *CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review*. Public input copies and reference conversions are derived from CUAD v1; the source archive SHA-256 is in `data_manifest.json`.

The fixed eligibility conditions yield 20 development contracts from official training and **56** contracts from official test. We use every eligible test contract without relaxing the 40,000-character limit or single-value condition. `eligibility.json` records all 510 contracts, including exclusions and an exact source duplicate. This filters the task towards shorter, single-value-compatible contracts; results do not estimate performance across all CUAD contracts.

`protocol.py` only sees source text, field definitions and, for repair, the initial extracted graph. Reference files are scorer-only. All four arms use Gemma, the same source and completion limit, predeclared fence handling and program-assigned document IDs. Evidence windows are deterministic source offsets. The whole source is always supplied. The primary output is before any evidence gate: unsupported or multi-valued outputs remain in scoring. Initial graph creation costs are reported separately.

```bash
python3 exps/submission_week_20260929/fetch_data.py
python3 exps/paper1_cuad/prepare.py
/tmp/kgbench-local-venv/bin/python -m unittest exps.paper1_cuad.test_protocol exps.paper1_cuad.test_analysis
/tmp/kgbench-local-venv/bin/python exps/paper1_cuad/run.py dev
/tmp/kgbench-local-venv/bin/python exps/paper1_cuad/analyze.py dev
# After a recorded development viability decision, with no test-based tuning:
/tmp/kgbench-local-venv/bin/python exps/paper1_cuad/run.py test
/tmp/kgbench-local-venv/bin/python exps/paper1_cuad/analyze.py test
```

The source archive is locally cached under `../submission_week_20260929/sources/cuad_data.zip`; retrieve only `data.zip` from the canonical repository to reproduce. No model checkpoint is needed. Collection reads local credentials without logging them, disables proxies and checkpoints every outcome, including failures. Resuming never retries already checkpointed outcomes. The request ledger may contain a repeated launch intent after interruption; `responses.jsonl` and actual per-response attempts determine counted requests.

`study.json` defines the primary paired comparison and cost accounting. Raw exact F1 is secondary and uses the first official answer span when identical normalized spans repeat; primary F1 normalizes whitespace in both reference and prediction. Scoring code is sealed before opening the held-out test results. Human semantic judgments remain pending; exact span agreement is not a replacement.


## Current collection status (2026-09-29)

Development is complete: 80 outputs / 84 actual requests, all parsed. Indexed repair minus indexed re-extraction is −0.03 pp on these 20 development documents; prompts and eligibility were not retuned.

Test collection is **incomplete: 216/224 outcomes, 262 actual requests, 209 parsed outputs and seven checkpointed transport failures**. Eight outcomes remain unexecuted. Two failed-wave stops occurred; a separate intervening short Gemma probe returned HTTP 200 but did not establish sustained service recovery. See `collection_status.json`, `transport_incident.json` and both collection logs. No primary held-out statistic or final contract figure is reported. On resumption, the seven completed failures remain empty graphs; they are not rerun. `analyze.py test` refuses incomplete collection.
