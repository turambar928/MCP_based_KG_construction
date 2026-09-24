# English translations of the current prompt builders

These are translations, not the literal prompts sent in historical calls. The
literal Chinese builder outputs with placeholders are `deletion_zh.txt` and
`augmentation_zh.txt`; their SHA-256 hashes are in `manifest.json`. The archive
does not retain every rendered prompt or decoding configuration. The current
script defaults are Qwen3-32B, temperature 0.2, five deletion spans of at most six
characters, and three added clauses. No new model calls were made for this export.

## Deletion completion

You are an expert in extracting rules for government-service knowledge graphs.
We randomly deleted short phrases from a government-service description, leaving
some rule information missing. Read the original and modified text. Using their
context and government-service knowledge, infer the missing rules and express
them as reusable knowledge-graph validation rules.

Output JSON only, following this schema, without extra text or code fences:

```json
{
  "strategy": "deletion",
  "service_item": "...",
  "analysis": "...",
  "removed_fragments": ["..."],
  "missing_rule_candidates": ["..."],
  "proposed_rules": {
    "entity_types": ["..."],
    "relationship_types": ["..."],
    "type_conflict_rules_forbidden": [["subordinate agency", "manages", "superior agency"]],
    "type_conflict_rules_allowed": [["government agency", "issues", "policy"]],
    "hierarchy_rules": ["..."],
    "geo_hierarchy_rules": [["province", "governs", "city"], ["city", "governs", "district or county"]],
    "procedural_rules": ["..."]
  }
}
```

Service item: `{service_item}`

Original text: `{original_text}`

Modified text: `{masked_text}`

Removed fragments: `["{removed_fragment}"]`

In `proposed_rules`, use general types and relations where possible instead of
only specific entity names.

## Augmentation expansion

You are an expert in extracting rules for government-service knowledge graphs.
Draft at most three reasonable supplementary clauses (`added_clauses`) for the
given government-service description, keeping them truthful and compliant. Based
on these additions, express reusable knowledge-graph validation rules.

Output JSON only, following this schema, without extra text or code fences:

```json
{
  "strategy": "augmentation",
  "service_item": "...",
  "analysis": "...",
  "added_clauses": ["..."],
  "proposed_rules": {
    "entity_types": ["..."],
    "relationship_types": ["..."],
    "type_conflict_rules_forbidden": [["regulated entity", "supervises", "regulatory agency"]],
    "type_conflict_rules_allowed": [["government agency", "applies to", "region"]],
    "hierarchy_rules": ["..."],
    "geo_hierarchy_rules": [["country", "governs", "province"], ["province", "governs", "city"]],
    "procedural_rules": ["..."]
  }
}
```

Service item: `{service_item}`

Original text: `{original_text}`

Keep `proposed_rules` general where possible; avoid listing only specific entity
names. The truthfulness instruction is part of the prompt, not an independently
verified property of the responses.
