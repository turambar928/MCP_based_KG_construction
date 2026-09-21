# Blind review of actual system edits

Status: no human annotation has been completed by the assistant.

The original frozen 200-item sheet in `../../paper1_submission_extensions/`
checks input/reference discrepancies. This separate sample checks **actual
system edits**, including harmful additions or deletions. It is sampled without
reference-quality screening from five configurations, with provenance hidden in
the annotator files. Neither model judgments nor structured-reference matches
are substituted for human labels.

Give annotator A only `annotator_a.csv` and annotator B only `annotator_b.csv`,
plus these instructions. Do not share `coordinator_mapping.csv`, paper results,
or the other annotator's sheet. Work independently from the source text.

For each row:

- `is_error`: does the edit address an actual defect of the input? For an
  addition, was that fact missing and needed? For a removal, was the removed
  triple wrong or an excess duplicate? Use 1, 0, or U (uncertain).
- `repair_acceptable`: is this specific addition/removal justified by the source
  and field schema? Inspect the complete input and output, including whether a
  correct fact was replaced with a wrong value. Use 1, 0, or U.
- `notes`: explain ambiguous references, acceptable paraphrases, unsupported
  relations, or harmful loss of correct information.

The coordinator merges the independently completed sheets by item ID:

```bash
python3 exps/paper1_mechanism_audit/merge_human_review.py
```

Fill adjudication columns in `merged_for_adjudication.csv` without changing
independent labels, then score:

```bash
python3 exps/paper1_submission_extensions/score_human_annotations.py \
  --input exps/paper1_mechanism_audit/human_review/merged_for_adjudication.csv \
  --output exps/paper1_mechanism_audit/human_review/results.json
```

Cohen's kappa is computed on original 0/1/U labels; post-adjudication accuracy is
separate. Report sampling denominators and per-configuration sample counts.
This edit sample estimates acceptance of sampled edits; it does not yield a
human-validated whole-graph F1 or repair recall on all documents.
