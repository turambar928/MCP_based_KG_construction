# Natural-error annotation protocol

The frozen annotation file is `natural_error_annotation_sample.csv`. Each row
is a discrepancy between a graph extracted from source text and the graph
derived from the source record's structured fields. No discrepancy was
injected by the experiment.

Two annotators must work independently. They should not inspect the system
name, the other annotator's labels, or the manuscript results before finishing
their labels.

For `*_is_error`, enter:

- `1` when the displayed missing or extra triple is an actual extraction error;
- `0` when the extracted graph is acceptable despite differing from the
  structured reference;
- `U` when the source evidence is insufficient or ambiguous.

For `*_repair_acceptable`, enter `1` when adding/removing the displayed triple
would be an acceptable repair, `0` when it would not, and `U` when ambiguous.
Annotators may explain ambiguity or acceptable paraphrases in `notes`.

After both files are complete, resolve disagreements in the adjudication
columns. Report raw agreement and Cohen's kappa separately for error detection
and repair acceptance. Do not treat the structured reference or an LLM judge as
a human annotation.
