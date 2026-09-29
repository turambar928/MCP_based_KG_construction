# Second development round

See `amendment.json`: only public record rendering and semantic instructions change. All 20 documents, compiler rules, actions, reward coefficients and the expansion gate are retained. This is the last permitted development round; if it fails, no expansion follows. The first round remains in `../paper2_docred_v2`.

# Source-evidence scheduler v2

A separate development experiment preserving Paper2's RL graph–rule co-optimization and dual-strategy generation. Historical environments, natural extraction outputs and counterexamples are unchanged. The fixed protocol is `protocol.json`; request/code hashes precede calls in `pilot_manifest.json`.

## Scope and separation

The first ten pairs in the existing development episode manifest supply twenty documents. Every pair contains one clean reference graph and one graph with `ceil(0.2 * reference size)` additional endpoint/relation substitutions. References are used only to construct these controlled inputs and to score their recovery. The generator sees original text, given entities/types, and the current public records, never labels identifying injected records. Absence from DocRED's reference set is not a natural factual error label.

`prepare.py` constructs local public/scorer files separately. `generation.py` validates source quotes and candidate identity. `environment.py` reads compiled packets and public records only. `pilot.py` freezes, collects, compiles, then scores fixed schedules. Original source text, raw responses and full rejection candidates remain ignored in `local/`; hashes, source-free packets, rejection reasons and trajectories can be distributed. Quote hashes/offsets permit local verification without redistributing source text. Dataset licensing caveats and download instructions are inherited from `../paper2_docred/README.md`.

## Math and safeguards

Write `V(g; R)` for the nonconflicting flagged record set, `N=max(1,initial record count)`, `G=1-|V|/N`, and `C` for nonconflicting coverage of initial records. The fixed-rule graph delta compares before/after graphs under **the same post-acquisition rule set**. Acquisition-revealed flags are logged separately from `V_edit=V(g_next;R_next)-V(g_before;R_next)`. The reward is `0.5 delta_G_fixed + 0.5 delta_C - 0.004 acquisitions - 0.00002 deletions - |V_edit|/N`.

With one flagged record among two initial records, acquisition earns 0.246 and repair 0.24998: the two-step discounted return is 0.483481. Legacy reward mode gives −0.504 then 0.24998, returning −0.266519. These are synthetic accounting examples, not measured repair quality. Coverage is unchanged when a flagged record is removed because its denominator and target set stay fixed. In this removal-only environment, removing a record cannot create a new record-local violation; the edit penalty is therefore zero. That does not establish semantic safety or a global monotonicity guarantee. Generated wrong constraints can still remove correct facts.

Source verdicts are supported / contradicted / insufficient; insufficient is audit-only. Evidence must be a nonempty exact substring of a numbered **original** sentence. The compiler calculates offsets; model-supplied offsets are not trusted. Augmentation clauses are hypothetical and cannot supply evidence. Quote validity is provenance, not semantic entailment. Specific source contradiction is not canceled by generic type compatibility. Conflicting support/contradiction and support/type-prohibition cause abstention. Emptying protection blocks deletion of every remaining record. Late support for a previously deleted record is logged; it does not silently restore the record.

The four actions are acquire-deletion / acquire-augmentation / repair / stop, with four response packets, two per strategy, horizon ten, discount .95. The 14 summaries are partial observations, not a proven Markov-sufficient state. No old eight-action checkpoints are reused. Cached replay has zero real API calls, separately from accounted acquired packets.

## Commands

From the repository root, with `/tmp/kgbench-local-venv/bin/python`:

```bash
python -m unittest exps.paper2_docred_v2_round2.test_contracts exps.paper2_docred_v2_round2.test_replay
python exps/paper2_docred_v2_round2/pilot.py freeze
python exps/paper2_docred_v2_round2/pilot.py collect
python exps/paper2_docred_v2_round2/pilot.py analyze
python exps/paper2_docred_v2_round2/publish.py
```

`collect` uses only `google/gemma-4-26B-A4B-it`, verifies the returned model, bypasses proxies, and resumes unseen tasks without replacing failures. It reads credentials from `apis` without printing them. At most two versioned development rounds are permitted. No third round is permitted, and results cannot be made favorable by swapping documents. The second-round empirical outcome and expansion decision are in `report_zh.md` once all forty outputs have been collected.

Expanded learning is conditional on the frozen gate. If it passes, train DDQN, DQN and legacy-reward DDQN from scratch (ten seeds ×250 episodes each), shared cached packets and budgets; compare with the frozen simple schedules and same-model two-call direct repair. Freeze concrete architecture, baseline prompts, scoring and eight-test Holm family before formal collection/training. Seed repetitions do not increase the number of independent documents. A gate pass alone is not an end-to-end learned-policy result.
