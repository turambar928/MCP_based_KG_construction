# Receipt repair follow-up: development and untouched test

This study follows the independent 60-receipt experiment in
`../paper1_external_receipts/`. That earlier sample is used only for error
analysis. No annotation files from the ongoing two-person review are read or
changed.

## Question and change

On the earlier sample, base and diagnostic repairs reproduce all 60 input
graphs. Of 239 reference fields, 190 match exactly. Among the 49 mismatches,
27 are case/whitespace, punctuation or amount-format differences; ten involve
span boundaries, eight a different source value, and four a reference value
absent from normalized source. These are mechanical categories, not additional
human factual judgments. Details are in `prior_error_analysis.json` and
`prior_error_cases.csv`.

The new comparison gives every repair arm the same explicit definitions of
company/date/address/total and the same indexed source lines. The definitions
clarify registered issuer vs trading brand, full address boundaries, date vs
time, and final payable amount vs subtotal/cash/change. Three arms differ only
in extra context:

- **Simple schema-aware pipeline:** shared schema, source lines and input graph.
- **Field-evidence index:** the same input plus deterministic line anchors and
  neighbours for each field. Receipt patterns locate company, address, date,
  and total evidence. The index contains source positions/text, not reference
  values or a selected target answer.
- **SHACL context:** the same input plus the actual pySHACL report and graph
  context from the previous documented Lin-style adaptation.

`content_enhancement/source_validation.py` fixes whitespace handling for
candidate validation. Both source and candidate whitespace are collapsed,
with word boundaries, case and punctuation preserved. Each raw response is
scored through this common filter. The old literal filter is also scored
offline as a sensitivity comparison. The prior experiment files remain frozen.
A 540-response offline regression confirms the only changed old outputs are
the three occurrences of the known address-space mismatch.

## Split and freeze

The source is the same pinned SROIE mirror, commit
`27be4271b251c256f695acbade9a801bffe85994`. Sampling removes the 60 earlier
IDs, then draws 80 unused IDs with seed 20260923: 20 development documents and
60 test documents. The groups are disjoint. This is document-level transfer
within the receipt collection, not a vendor-disjoint or new-domain test.

Test reference files are not downloaded until all 180 test repairs have
completed. One fixed evidence-index design is evaluated on development data;
all three arms are retained for test, regardless of their development ranking.
The runner freezes code hashes, exact prompts, model settings, the test input
hash, development result hash and primary comparison before test calls. Resumes
reuse saved prompts and never selectively rerun failures.

The primary contrast is **evidence+gate minus simple+gate macro exact triple
F1**. Other contrasts are secondary. Exact graph match, case/space-normalized
F1, preservation, harmful edits, field-level transitions, input/output tokens
and measured request times are also reported. Bootstrap and sign randomization
resample whole documents, 10,000 draws with seed 42. Missing upstream labels
are excluded from scoring for that field only; all four fields remain in the
public schema. A scoring lock records analysis-file hashes before test.

## Calls and reproducibility

Only `google/gemma-4-26B-A4B-it` is permitted. Temperature 0, max 4,000 output
tokens, two workers, global four-second request spacing, and maximum four
transport attempts match the previous run. API configuration comes from the
ignored `api` file; the request client bypasses environment proxies. No model
weights or receipt images are downloaded. Failed/malformed outcomes remain in
the denominator. Test labels and reference differences never enter prompts.

```bash
python3 exps/paper1_receipt_followup/error_analysis.py
python3 exps/paper1_receipt_followup/prepare.py
python3 exps/paper1_receipt_followup/run.py dev
python3 exps/paper1_receipt_followup/analyze.py dev
# Inspect development results, then freeze the method and analysis before test.
python3 exps/paper1_receipt_followup/scoring_lock.py
python3 exps/paper1_receipt_followup/run.py lock
python3 exps/paper1_receipt_followup/run.py test
# This refuses to download test labels before 180 test repairs are present.
python3 exps/paper1_receipt_followup/prepare.py --test-references
python3 exps/paper1_receipt_followup/analyze.py test
python3 exps/paper1_receipt_followup/write_paper.py
cd paper1 && tectonic -X compile main.tex --keep-logs
```

Dependencies are the existing Python analysis environment (httpx, requests,
NumPy, rdflib, pyshacl, matplotlib). Exact repair prompts, requests, raw outputs,
usage, per-case scores and field transitions are archived by split. Upstream
attribution/license remain in `../paper1_external_receipts/upstream/`.
Wall times include API pacing/retry waits, but exclude context preparation and
shared initial extraction; extraction costs are reported separately.
