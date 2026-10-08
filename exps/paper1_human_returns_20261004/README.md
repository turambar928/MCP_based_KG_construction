# Paper1 real annotation returns, 2026-10-04

Public portions of the received packages and the full hash inventory were archived on 2026-10-08: [received archive](received_public/README.md), [file manifest](uploaded_package_manifest_20261008.json). Current results remain the canonical files in this directory; historical manuscript copies are not the current paper.

Both received JSON files pass the original strict validator: A and B each supply 200 D items and 200 E items, with complete labels and required explanations. The public sample hash and coordinator mapping match the original delivery. Input files are never rewritten.

**Current status: adjudication complete.** The author supplied 154 third-person questionnaire decisions (A selected on 30 items, B on 124). All decisions match the completed CSVs, all 400 original rows retain their immutable fields, and all 246 previously concordant items retain their labels. One E acceptability judgment remains U. The original scorer independently reproduces the supplied totals and per-configuration counts. No API was called or human label changed by the importer.

Task D: 95/200 input errors and 86/200 acceptable suggested edits. Task E: 134/200 input errors and 134/199 acceptable actual edits, plus one U. The latter pools five configurations; it is not a single-method or whole-graph accuracy estimate. Workflow and background information come from the author-supplied completion record, not from file validation.

- [Final Chinese report](../../paper1/HUMAN_REVIEW_RESULTS_2026-10-04.md)
- `human_results.json`, `human_results.md`, `per_configuration.csv`: independently recomputed anonymous final aggregates.
- `adjudication_receipt.json`: original questionnaire/CSV hashes, reported workflow and validation receipt.
- `local/adjudicated/`: completed CSVs and raw questionnaire, separate from the preserved earlier handoff.

- [Chinese receipt report](../../paper1/HUMAN_RETURN_CHECK_2026-10-04.md)
- [Coordinator instructions](ADJUDICATION_GUIDE_zh.md)
- `receipt_summary.json`: historical pre-adjudication snapshot, agreement, confusion counts, denominators and input hashes; its pending status records that earlier stage.
- `local/raw/`: byte-identical JSON backups.
- `local/merged/`: original merge-script output, full context, immutable independent labels and blank disputed adjudication cells.
- `local/争议索引.csv`: review index only, not a substitute for the complete adjudication tables.
- `local/Paper1_人工结果裁决包_2026-10-04.zip`: coordinator handoff, with hidden method identities.

Raw returns, notes, source context and the adjudication handoff remain local, excluded from Git. The original uploaded folder is also left untouched and is not included in this commit.

Reproduce from the repository root:

```bash
/tmp/kgbench-local-venv/bin/python exps/paper1_human_returns_20261004/check_returns.py --input 'exps/paper1_人工标注完整包 2'
```

The script uses the original validator and merge code, preserves existing adjudication files, and refuses changed independent fields. A pre-existing handoff ZIP is not replaced. It does not call final scoring or infer semantic-effect categories. Human workflow independence and qualifications cannot be established from file structure alone.

To validate and rescore the completed adjudication separately:

```bash
/tmp/kgbench-local-venv/bin/python exps/paper1_human_returns_20261004/import_adjudication.py --input 'exps/Paper1_真人裁决完成_2026-10-04 2'
```

The importer leaves uploaded files and the earlier `local/merged/` handoff unchanged, scores `local/adjudicated/`, checks agreement with the supplied aggregates and archives only anonymous summaries in Git. It does not apply the uploaded Git patch blindly.
