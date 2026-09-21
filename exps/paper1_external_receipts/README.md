# Independent receipt-text evaluation for Paper 1

This experiment tests the unchanged document-field repair contract on source
text that was not constructed by serializing its target field values.

## Data and source

- Dataset: SROIE (Huang et al., ICDAR 2019), DOI
  https://doi.org/10.1109/ICDAR.2019.00244, pp. 1516–1520.
- Text/label mirror: https://github.com/zzzDavid/ICDAR-2019-SROIE
- Pinned commit: `27be4271b251c256f695acbade9a801bffe85994`.
- Population: 626 community-corrected trainval receipts with box transcripts
  and KIE label files. This is a fixed external test for this project, not the
  competition's official test leaderboard. No local model training uses these
  documents.
- Sample: 60 documents, uniformly sampled with seed 20260922 before model calls.
  No filtering by model success, label agreement, or literal source coverage.
- Only text and label files are downloaded. Images and model weights are not
  downloaded. Upstream attribution and license are retained under `upstream/`.
  The upstream README describes its corrections to the released competition data.

`inputs.jsonl` contains transcripts in their stored order, joined by spaces,
plus document IDs and the public four-field schema (company/date/address/total).
`references.jsonl` separately contains upstream human KIE values. One sampled
receipt has no address annotation. That field is excluded from scoring for
that receipt only; all four fields are still available in model inputs.
There are 239 annotated fields, 220 of which occur literally in source text.
No reference value is added to or used to reorder the transcript.

## Locked experiment

1. Gemma extracts a graph from each of the 60 texts.
2. Base, diagnostic, and Lin-style SHACL-context arms each repair the same
   extracted input, with shared instructions and preprocessing.
3. Each response is scored raw and through the same gate. Rule-only and the
   existing source-field parser run without API calls or receipt-specific tuning.

All calls use `google/gemma-4-26B-A4B-it`, temperature 0 and a 4,000-token
completion cap. The runner inherits four-second global request spacing,
maximum four transport attempts, two workers, proxy bypass for this API, and
checkpointing that retains failures. No GPT/Claude calls are made.
There are 60 extraction outcomes and 180 repair outcomes; transport retries
are counted separately. Model inputs never load `references.jsonl`.

The extraction pass completed before a pySHACL preparation issue was found:
the source word `SERVICE` was treated by pySHACL's query checker as a forbidden
SPARQL keyword because the literal text was interpolated into query syntax.
The receipt adapter binds source text via an RDF metadata node instead. The
original protocol, amendment reason, and updated manifest are preserved;
no repair had run when this preparation fix was made. No sample or extraction
outcome was changed. The old Chinese mechanism experiment remains frozen.

## Metrics

Primary: macro per-document exact multiset triple F1 and exact graph match.
Secondary: the same scores after removing whitespace and case-folding field
values. Secondary normalization does not change generation or gate behavior.
Unknown/unannotated address is excluded only in scoring; invalid predicates
are still penalized. We also report preservation, harmful edits, error
reduction on imperfect inputs, parsing outcomes and literal-support coverage.

The gate audit records rejected candidates and their exact/normalized reference
membership. Paired comparisons use whole documents, 10,000 bootstrap samples
and sign randomization draws (seed 42). Tests are exploratory. Recorded wall
time includes pacing and request retries and excludes shared extraction/context
preparation; token counts are reported rather than treated as equal.

## Reproduce

From the repository root:

```bash
python3 exps/paper1_external_receipts/prepare.py
# Uses the ignored local api file. Resume skips every completed outcome.
python3 exps/paper1_external_receipts/run.py
python3 exps/paper1_external_receipts/analyze.py
python3 exps/paper1_external_receipts/write_paper.py
cd paper1 && tectonic -X compile main.tex --keep-logs
```

The existing Python environment requires requests/httpx, numpy, rdflib,
pyshacl, matplotlib, and the repository's scoring dependencies. PDF figures
embed Times New Roman using `paper1/figure_style.py`.

Results: `report.md`, `results.json`, `per_case.csv`, `cost.csv`, and
`gate_rejections.csv`. Upstream annotations support this external evaluation;
they do not substitute for the two-person review of Chinese system edits in
`../paper1_human_review/`.

## Post-run normalization check

All three rejected candidates refer to the same correct address in receipt
155. The source contains a double space; the existing JSON parser collapses
candidate whitespace. `whitespace_check.py` applies that same whitespace
collapse to the source before filtering the frozen responses. It makes no new
API calls and preserves the primary table. Base/diagnostic F1 becomes 79.44%,
SHACL F1 79.86%, and graph exact match remains 33.33%. This is a separate
post-run check, not an independently tested improvement. It preserves word
boundaries; it does not concatenate words or change letter case.

Run `python3 exps/paper1_external_receipts/whitespace_check.py` before
`write_paper.py` when rebuilding the full report.
