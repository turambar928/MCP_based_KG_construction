# API LLM Extraction Benchmark Report

This benchmark uses the API-backed LLM to extract triples directly from raw TNEWS/CLUE titles.
TNEWS labels are used as silver category labels; provided keywords are used as weak silver entity mentions.

## Setup

- Model: `Qwen3.8-27B-no-thinking`
- Documents: 45
- Categories: 15
- API calls attempted: 45
- Runtime: 1190.90s

## Main Results

| Metric | Raw LLM KG | Repaired KG |
| --- | ---: | ---: |
| Parse success | 1.000 | - |
| Category accuracy | 0.556 | 0.556 |
| Keyword recall | 0.178 | 0.178 |
| Documents with triples | 1.000 | 1.000 |
| Avg triples / doc | 3.58 | 3.58 |
| KG quality score | 100.00 | 100.00 |
| Invalid triple rate | 0.000 | 0.000 |
| Duplicate triple rate | 0.000 | 0.000 |

## Interpretation

- Category accuracy evaluates whether the LLM can infer the TNEWS label from the title.
- Keyword recall is a weak proxy for entity extraction coverage, not a gold triple-level recall.
- The repaired KG applies deterministic quality-control rules: remove empty triples, invalid relation labels, invalid categories, self-loops, and exact duplicates.
- This benchmark therefore tests the full API extraction path plus the system's post-extraction quality-control layer.
