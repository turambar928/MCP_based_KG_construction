# Paper2 reference-loss audit (offline, post-hoc)

This audit traces all four reference-backed losses in the frozen 2026-10-04 Gemma batch. It makes zero API calls, trains no policy and supplies no human labels. The full Chinese explanation and proposed mechanism are in [paper2/RULE_FAILURE_AUDIT_2026-10-04.md](../../paper2/RULE_FAILURE_AUDIT_2026-10-04.md).

From the repository root:

```bash
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_failure_audit_20261004/audit.py
/tmp/kgbench-local-venv/bin/python -m unittest exps.paper2_rule_failure_audit_20261004.test_audit -v
```

Requires the frozen original study and its licensed local source files / raw response journal. No data is downloaded. Uses the original frozen environment, compiler and fixed schedules unchanged. Historical hashes are checked before and after execution.

Artifacts:

- `cases.json`: all four reference losses, matched rules, pre-edit conflict states, quote provenance and surface co-mention checks. Human semantic verdicts remain null.
- `local/source_dossiers.json`: full source documents for the four cases; ignored by Git.
- `replays.json`: 4 rule-admission variants × 8 fixed policies × 10 pairs = 320 replays, including the unchanged baseline.
- `summary.json`: all policy aggregates, historical hash checks and unchanged-gate boundary.
- `validation.json`: tests and delivery checks.

The family filters are **diagnostic quarantine prototypes**, not a validated semantic gate. They do not consult reference labels or protect selected record IDs. Baseline compilation and all 80 original trajectories must match exactly before scoring the filtered runs. The scorer references are read only after replay.

Quarantining both prohibition families prevents all four reference losses but also all repairs. Quarantining source contradictions retains 14 injected-item removals and two reference losses. Neither result changes the original failed expansion gate or establishes a new method on unseen data.

Public quote evidence contains offsets/hashes and co-mention booleans, not raw quotation text. Co-mention does not establish contradiction; source-level interpretation in the Chinese report is assistant analysis, not independent human annotation.
