# DMKD cover letter — author-review draft

Dear Editors,

Please consider “Source-Grounded Constraint Validation for Document-Level Knowledge Graph Repair” for publication as a research article in *Data Mining and Knowledge Discovery*.

The manuscript studies how source text and field constraints can guide repairs to document-level knowledge graphs. It defines an explicit candidate-validation procedure and uses matched prompts and shared model responses to distinguish the effects of diagnostic context, evidence lines, and filtering. The work addresses data cleaning and knowledge representation, with particular attention to when simple alternatives are sufficient.

The evaluation covers controlled defects, actual extraction outputs from three Chinese record collections, independently annotated receipt transcripts, and held-out contract fields. A completed blinded human review of 200 reference discrepancies and 200 system edits distinguishes reference agreement from semantic quality. In a frozen 60-receipt test, indexed evidence improves F1 over Simple by 4.76 points (95% CI: [2.50, 7.26]); later controls do not establish a gain over random context or anchors alone. Indexed contract repair lowers F1 from 46.76% to 44.84%, and its 0.72-point difference from re-extraction has an interval spanning zero. The matched diagnostic-context control does not improve F1, learned selection shows no consistent repair gain, and filtering has a limited candidate-removal effect. We retain the perfect source-copy baseline on serialized records, the contract decline, and low pre-adjudication edit agreement. These results support task-specific evidence-context benefits and an auditable evaluation protocol.

The repository provides code, prompts, sample manifests, predictions, scoring procedures, and aggregate human-review results: https://github.com/turambar928/MCP_based_KG_construction.

Thank you for considering the manuscript.

Sincerely,

Tian Zhou  
Xi'an Jiaotong University  
tianzhou@xjtu.edu.cn  
[Corresponding-author details copied from the current manuscript; confirm before submission.]

---

**Author action before sending:** confirm all authors approve this submission and the manuscript is original and not under consideration elsewhere; then add the corresponding truthful declaration. Confirm the author list, affiliations, funding, conflicts, and contributions using [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md). Remove this note and the bracketed confirmation line from the submitted letter. These statements have not been supplied or confirmed on the authors' behalf.
