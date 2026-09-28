# Paper1 method diagrams

The manuscript uses `image1.pdf`, `image2.pdf`, and `image3.pdf`. Corresponding
SVG masters retain editable text, nodes, and connectors. New raster previews
are named `image1_preview.png`, `image2_preview.png`, and `image3_preview.png`.
The author's original `image1.png`, `image2.png`, and `image3.png` are preserved.

## Rebuild

From the repository root, using system PyGObject, librsvg and pycairo:

```bash
/usr/bin/python3 paper1/figure/method/redraw.py
cd paper1
tectonic -X compile main.tex --only-cached --keep-logs
```

The SVG is generated first and converted directly to vector PDF with embedded
Times New Roman text. No raster images are embedded in these diagrams.
No API calls, model downloads, or experiments are involved. Change `redraw.py`
for reproducible updates; regenerating overwrites edits made directly to SVG.
The older `paper1/make_method_figures.py` remains unchanged as a historical
renderer; running it restores the previous vector designs.

## What the three figures show

1. **Profile-based architecture:** a document-field graph and source, four
   quality components and four graph statistics, neural trigger/scope prior,
   trial-state selection, and one committed edit. This is the sequential
   variant evaluated on fixed proposals, not the one-call filter in Algorithm 1.
   Profile marks identify components, not numerical scores. The small network
   illustrates routing without asserting a layer architecture.
2. **Diagnostic scopes:** one schematic document anchors local, graph and source
   checks. Duplicate facts and an isolated declared node illustrate local
   checks; an out-of-schema relation illustrates graph checks; a literal value
   absent from the source illustrates source support. The isolated node is an
   illustrative declared entity, not a missing field. A source occurrence is
   not itself proof of correct relation assignment. Hierarchy checks, when
   applicable, still require explicit rules as described in the manuscript.
3. **Sequential selector:** candidate bundles and violation-derived edits are
   trialed independently from the same current graph. Feasibility and positive
   utility precede winner selection. Scope prior enters utility, and only one
   edit is committed before reassessment. The figure summarizes utility
   components; coefficients and normalization are specified in the mathematics.
   The 12-step horizon is the fixed-proposal experiment setting.

ALPHA / 42.00 / 49.00 and miniature trial graphs are illustrative examples,
not archived model outputs, experimental measurements, or guaranteed repairs.
The early stopping and trial-state constraints were cross-checked against
`content_enhancement/constraint_optimizer_v2.py` and the active manuscript.
No method claims or experiment results were changed in this visual revision.

## Visual references

The design follows the principles researched for Paper2: numbered stages,
visible intermediate objects, short labels, semantic colors, and external
feedback paths. It uses original vector artwork, not copied figures.

- IRCoT, ACL 2023, Figure 2: https://aclanthology.org/2023.acl-long.557/
- Reasoning on Graphs, ICLR 2024, Figure 2: https://arxiv.org/abs/2310.01061
- Think-on-Graph, ICLR 2024, Figure 2: https://arxiv.org/abs/2307.07697

Colors: blue = local graph/data; green = constraints/accepted states;
orange = source or highlighted edits; purple = neural routing/utility.
Labels and line styles supplement color. Paper1's existing Springer template
is unchanged. These figures are designed for its full text width.
