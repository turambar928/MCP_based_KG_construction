# Episode-scoped automatic review of cached Paper2 rules

Protocol: [Paper2 protocol](../../paper2/AUTOMATIC_RULE_REVIEW_PROTOCOL_2026-10-08.md).

This one-shot development study uses Qwen3.8-27B-no-thinking to review cached Gemma proposals. Automatic judgments are NOT independent human labels and never populate the existing trusted registry. No training, model downloads, new samples or held-out test access. Historical results remain immutable.

The schema audit has zero sound hard mappings: relation names do not define disjointness, and public Wikidata metadata retrieval failed. Schema-only is an abstention control, not a strong functioning schema validator. All decisions are scoped to the initial immutable document pair.

From the repository root:

```bash
/tmp/kgbench-local-venv/bin/python -m unittest exps.paper2_rule_verification_20261008.test_review exps.paper2_rule_admission_20261004.test_admission exps.paper2_rule_failure_audit_20261004.test_audit -v
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_verification_20261008/runner.py freeze
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_verification_20261008/runner.py verify
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_verification_20261008/runner.py status
# Only this command reads credentials and calls a model:
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_verification_20261008/runner.py collect
/tmp/kgbench-local-venv/bin/python exps/paper2_rule_verification_20261008/runner.py analyze
```

`freeze` hashes implementation, inputs and exact requests before collection. Do not edit frozen code. Private source and response files stay in ignored `local/`. Existing licensed local DocRED inputs are required; checksums are not a public dataset distribution. The implementation inherits the existing durable collector with a persistent outage latch. An interrupted unknown delivery is not resent. A latched outage does not automatically resume. No alternate model is used.

`analyze` evaluates all five arms only after all tasks finalize. After a latched outage it evaluates only the three offline arms, marking automatic arms unavailable. It never reports missing model judgments as an empirical zero-accuracy result. All trajectories are materialized before the scorer is opened. The old independent registry remains empty and unchanged.

Synthetic tests establish contracts and arithmetic, not model semantic accuracy. The English prompt is in `review.py`; schema checks are implemented in `parse_review`. A valid quotation alone never proves entailment. The old executor, conflict behavior, rewards and fixed schedules are reused without modification.
