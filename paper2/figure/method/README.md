# Paper2 method diagrams

Editable masters: `cooptimization.svg` and `dual_strategy.svg`.
The manuscript includes the corresponding vector PDFs; PNG files are previews.
Text stays editable in SVG. PDFs embed Times New Roman fonts, including
positioned subscript/superscript glyphs without fallback fonts.

## Rebuild

From the repository root, using system PyGObject, librsvg and pycairo:

```bash
/usr/bin/python3 paper2/figure/method/redraw.py
cd paper2
tectonic -X compile main.tex --only-cached --keep-logs
```

The script writes only these two diagrams in SVG, PDF and PNG. No API,
model download, or experiment execution is required. Edit the generator for
reproducible changes; direct SVG edits are overwritten on regeneration.
The historical `exps/paper2_offline_revision/make_figures.py` is unchanged;
running its method-figure routine would restore the historical designs.

## Content and provenance

- **Co-optimization:** fourteen observations, eight masked actions, graph/rule
  transitions, reward feedback, and replay-based Double-DQN learning. Network
  widths are 14–32–16–8; target copying occurs every 100 environment steps.
  Graph drawings and mask values are schematic, not a recorded transition.
  The learned scheduling environment uses the fixed validator registry.
- **Dual strategy:** original text, masked text and removed fragments enter
  deletion completion. Augmentation returns clauses and candidates in one
  call. Exact typed candidates enter a separate offline execution bridge;
  procedural examples are retained candidates, not executable typed rules.
- The shortened English examples translate archived document
  `E06FCBC8B4E263C04595AD197B9A8718`, concerning fire-facility enforcement.
  The source is in `data/政务.jsonl`; deletion and augmentation outputs are
  the first two records of `data/rule_suggestions/per_item_rule_suggestions.jsonl`.
  The illustrated deleted fragment is `经责令改正`; the deletion candidate
  combines the recorded rectification/enforcement statements. The augmentation
  example translates the second added clause (post-penalty reinspection) and
  its procedural candidate. The document card summarizes the source. These
  are explanatory translations, not literal rendered prompts or new results.

## Design references

Borrowed visual principles, not copied artwork:

- IRCoT, ACL 2023, Figure 2: worked examples and consistent color mapping.
  https://aclanthology.org/2023.acl-long.557/
- Reasoning on Graphs, ICLR 2024, Figure 2: numbered stages and visible
  intermediate graph objects. https://arxiv.org/abs/2310.01061
- Think-on-Graph, ICLR 2024, Figure 2: local graph changes and iteration.
  https://arxiv.org/abs/2307.07697

At 174 mm wide, body labels are approximately 7.4–8.2 pt and stage headings
approximately 9.5 pt. Labels, grouping and line style reinforce color.
The manuscript main line and experimental results are unchanged.
