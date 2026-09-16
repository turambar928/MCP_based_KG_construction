# Neo4j LLM Graph Builder Comparison

This benchmark compares the public Neo4j LLM Graph Builder core extractor with our extraction and validation path under the same model, schema, temperature, input sample, and concurrency.

## Setup

- Model: `Qwen3.8-27B-no-thinking`
- Documents: 45 balanced TNEWS titles
- Categories: 15
- Random seed: `20260716`
- Workers: 1
- Neo4j Graph Builder commit inspected: `5ff7af3e9bb9226e1bbecd02f70f8d98697727a7`
- Neo4j extractor: `langchain-neo4j==0.10.0` `LLMGraphTransformer`

## Results

| System | Parse | Cat. acc. | Keyword recall | Doc. coverage | Triples/doc | Invalid | Duplicate | Time (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Neo4j LLM Graph Builder | 1.000 | 0.533 | 0.164 | 0.978 | 3.22 | 0.000 | 0.000 | 1079.38 |
| Ours (one-pass extraction) | 1.000 | 0.556 | 0.178 | 1.000 | 3.42 | 0.000 | 0.000 | 783.59 |
| Ours + constraint validation | 1.000 | 0.556 | 0.178 | 1.000 | 3.42 | 0.000 | 0.000 | 783.59 |

## Paired category audit

- Both correct: 22
- Neo4j only correct: 2
- Ours only correct: 3
- Both wrong: 18
- Exact two-sided McNemar p-value: 1.000

## Interpretation boundaries

- TNEWS supplies category labels and weak entity keywords, not gold triples; category accuracy and keyword recall are therefore silver-label indicators.
- The comparison targets Text-to-KG extraction and post-extraction structural validation. It does not measure every semantic fact against a gold graph.
- The Neo4j baseline is its reproducible core extractor with a custom schema, which the public Graph Builder interface supports; no Neo4j database is needed to evaluate extracted graph documents.
