# Format-only secondary analysis (2026-09-28)

The first 16 returned re-extraction responses were HTTP 200 and contained a complete JSON object inside a Markdown `json` fence. The frozen strict parser classifies them as parse errors. This was noticed before any outcome/reference scoring of this new batch.

The original 240 requests, runner, raw responses, strict parse statuses and primary analysis remain unchanged. A separately labelled **post-observation format-compatibility sensitivity analysis** will remove only one enclosing triple-backtick fence (`json` or no language tag), then apply the identical strict JSON/triple schema checks to every response in every arm. No prose extraction, JSON repair, key renaming, field/value editing, outcome-dependent selection, or extra model request is allowed. Responses that still fail remain empty graphs. Report both strict and compatibility results, the actual recovered count per arm, and the original raw response hashes. This is not a preregistered primary result.

The 840-response protocol already uses its frozen permissive `parse_triples` parser; it is not replaced with this secondary parser. Cost and transport outcomes are identical across parsing analyses.
