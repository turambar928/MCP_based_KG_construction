# Literature baseline and execution scope

Source: Lin, Fierro, Li, Hong, Nuzzo, and Sangiovanni-Vincentelli (2025),
*Systematic Evaluation of Knowledge Graph Repair with Large Language Models*.
DOI: https://doi.org/10.48550/arXiv.2507.22419
Read on 2026-09-21: https://arxiv.org/html/2507.22419v1

Section 5 and Figure 5 define five prompt components: primer, violation context,
SHACL manifest context, KG context, and instructions. Table 1 describes manifest
M/S/S_n and graph G/F/F+ variants. We use full-manifest/full-graph M+G because
our document graphs are small and need no context truncation.

Implemented with RDFLib and pySHACL in `protocol.shacl_context`, not a fabricated
"SHACL-like" diagnostic report. Shapes check the declared head, permitted
predicates, maximum one value per field, and nonempty literals. A documented
SPARQL constraint checks literal occurrence in the source text. No shape uses
a gold field value or the set of relations present in the reference graph.

Adaptations, all reported in the manuscript:

1. Document-field triples replace Brick/LUBM/QUDT graphs.
2. Source evidence and its literal-support constraint are supplied to match the
   repair task; this is not part of the original RDF-only prompt.
3. Complete JSON graphs replace SPARQL repair operations. No arbitrary generated
   update is executed against a database.
4. All reports for a document are grouped in one call, including a no-violation
   report if applicable. Original per-violation prompting is not replicated.
5. Generation uses the exact same system instructions and 4,000 completion-token
   cap as the other arms; added context is the treatment. Different input-token
   counts are measured rather than described as an equal-total-token budget.
6. RDF collapses duplicate occurrences; the common JSON input preserves them.
7. The same candidate gate is evaluated on every arm's response, including this
   baseline. Both raw and filtered results are reported.

Label: **Lin-style SHACL context (adapted)**. Do not label this an official-code
reproduction or a demonstration of superiority over every method in Lin et al.
