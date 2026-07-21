# Repository Map

This document records the cleaned repository layout and where to put new files.

## Top-Level Runtime Files

- `kg_server.py`, `kg_server_enhanced.py`: MCP server entry points.
- `kg_client.py`, `kg_client_enhanced.py`: client-side examples and interactive clients.
- `data_quality.py`, `knowledge_completion.py`, `kg_utils.py`, `kg_visualizer.py`: core KG construction and enhancement modules.
- `LLM_entity_extract.py`: LLM-based entity extraction utility.
- `paper.tex`: legacy/root paper draft kept in place to avoid breaking local references.

## Main Directories

- `content_enhancement/`: implementation modules for quality analysis, constraint optimization, and KG enhancement.
- `evaluate_kg/`: KG quality evaluation scripts and sample node/relation inputs.
- `data/`: source datasets, generated KG CSVs, and rule-test datasets.
- `exps/`: experiment scripts, benchmark runners, result reports, figures, and model artifacts.
- `paper1/`: Paper 1 LaTeX source, figures, references, and section files.
- `paper2/`: Paper 2 LaTeX source, figures, references, and section files.
- `rule_generate_scripts/`: rule-generation and rule-evaluation scripts used by the paper experiments.
- `scripts/`: utility scripts that are not core runtime modules.
- `tests/`: test files.
- `outputs/`: generated graph exports and other non-source outputs.
- `logs/`: historical run logs.

## Utility Script Layout

- `scripts/converters/`: JSONL/CSV/Neo4j conversion scripts.
- `scripts/data_generation/`: dataset fetching and low-quality dataset generation scripts.
- `scripts/monitoring/`: result inspection and progress monitoring scripts.
- `scripts/`: small legacy crawlers and sports-data examples.

## Documentation Layout

- `docs/audits/`: paper-to-implementation audits and reference checks.
- `docs/usage/`: usage notes for evaluation and CSV workflows.
- `docs/summaries/`: method explanations and high-level technical notes.
- `docs/paper-drafts/`: older paper fragments, revision summaries, and paper-specific draft notes.

## Experiment Outputs

- `exps/decision_network/`: decision-network dataset, model artifact, metrics, and reproducibility metadata.
- `exps/external_benchmark/`: local external benchmark results.
- `exps/api_llm_extraction_benchmark/`: API/LLM extraction benchmark results.
- `exps/paper2_dual_strategy_ablation/`: deletion/augmentation/dual-strategy ablation results.
- `outputs/graph_exports/`: generated HTML/Cypher/TSV/TXT graph exports.

## Placement Rules

- Put reusable implementation code in the existing core modules or `content_enhancement/`.
- Put one-off experiment scripts under `exps/` if they produce paper results.
- Put reusable utility scripts under `scripts/`.
- Put final paper content only under `paper1/` or `paper2/`.
- Put generated artifacts under `outputs/` or the relevant `exps/<experiment_name>/` folder.
- Put paper review notes, audit notes, and revision summaries under `docs/`.
