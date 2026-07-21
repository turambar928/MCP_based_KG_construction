# API LLM Extraction Benchmark Report

This benchmark uses the API-backed LLM to extract triples directly from raw TNEWS/CLUE titles.
TNEWS labels are used as silver category labels; provided keywords are used as weak silver entity mentions.

## Setup

- Model: `Qwen3.6-35B-A3B-no-thinking`
- Documents: 45
- Categories: 15
- API calls attempted: 45
- Runtime: 48.61s

## Main Results

| Metric | Raw LLM KG | Repaired KG |
| --- | ---: | ---: |
| Parse success | 0.844 | - |
| Category accuracy | 0.467 | 0.467 |
| Keyword recall | 0.131 | 0.122 |
| Documents with triples | 0.844 | 0.844 |
| Avg triples / doc | 2.76 | 2.67 |
| KG quality score | 98.87 | 100.00 |
| Invalid triple rate | 0.032 | 0.000 |
| Duplicate triple rate | 0.000 | 0.000 |

## Interpretation

- Category accuracy evaluates whether the LLM can infer the TNEWS label from the title.
- Keyword recall is a weak proxy for entity extraction coverage, not a gold triple-level recall.
- The repaired KG applies deterministic quality-control rules: remove empty triples, invalid relation labels, invalid categories, self-loops, and exact duplicates.
- This benchmark therefore tests the full API extraction path plus the system's post-extraction quality-control layer.
