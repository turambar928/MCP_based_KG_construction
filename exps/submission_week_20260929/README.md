# Submission week execution

Plan: [2026-09-29 through 2026-10-05](../../docs/submission_week_2026-09-29.md).

This directory records source provenance, validation and progress. Dataset downloads are data only, never model weights. Local source copies are excluded from Git until redistribution conditions have been checked; URLs and cryptographic hashes remain available.

Existing human packages, experimental results, model checkpoints and method figures are protected by `preservation.json`. No human judgments are supplied by a model. A prepared experiment is not a completed result.


## Completed stage and continuation

See [Chinese delivery report](../../docs/submission_week_progress_2026-09-29.md) and [weekly ledger](../../docs/submission_week_2026-09-29.md).

- Paper1: development complete; test collection interrupted at 216/224 outcomes with seven retained transport failures and eight pending tasks. No primary held-out score or figure has been reported.
- Paper2: source-grouped data and four-action environment ready; ten-document development pilot fails the rule-effect coverage gate. No new learned policy is claimed.
- Twenty new tests pass. `verification.json` checks 1,679 historical files, method figures, split isolation, frozen code and request identities.
- `packages/` contains review drafts, source/PDF files and explicit unresolved submission gates. `clean_build_validation.json` records compilation after extraction to temporary standalone directories.
- Human verification was deferred by the user. No human judgments were filled by a model.

Data-only reproduction: `python3 exps/submission_week_20260929/fetch_data.py` retrieves and verifies pinned archives; cached valid copies are not downloaded again. Credentials are never included in these artifacts.

After service recovery, use the Paper1 README's resume command; completed failures remain fixed. Finish scoring and publication only when all 224 outcomes exist. Paper2 needs a new frozen design resolving coverage and acquisition incentives before meaningful formal training.
