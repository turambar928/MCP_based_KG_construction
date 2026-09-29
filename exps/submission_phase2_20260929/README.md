# Second submission-preparation stage, 2026-09-29

See `../../docs/submission_phase2_progress_2026-09-29.md` for the current Chinese report and next actions.

- Six separate Gemma development probes passed; `health_results.json` records lengths, exact returned model, one attempt each and parsing. These are health checks, not experimental samples.
- Paper1 resumed eight unseen contract outputs, retained seven existing failures, and completed 224 outputs /270 actual requests. The indexed repair comparison does not establish superiority.
- Paper2 ran two fixed twenty-document development rounds: eighty Gemma requests. Neither passes the full expansion gate, so formal generated-rule training/test/baseline collection is not run. Conditional code and synthetic tests are not empirical results.
- `preservation.json` checks 1,776 pre-existing tracked experiment/method-figure files; `append_only.json` seals the old prefixes of Paper1's two continued JSONL archives. Run `python3 exps/submission_phase2_20260929/verify.py` from the root.
- `tests.log` records sixty passing tests. New source-constraint packets are deterministically recompiled and original-sentence evidence offsets/hash checks are archived under each pilot directory.
- `build_review_packages.py` creates **review drafts**, with scientific/author/journal gates stated in each ZIP. `validate_packages.py` extracts and compiles both packages without workspace dependencies, then compares PDF text. Cached TeX resources and Times New Roman must be installed; fonts are not redistributed.
- Historical experiments and first-stage source packages are unchanged. Source licensing boundaries and pending human reviews are preserved. User changes to `apis` are not included.

New request total is 94: six probes, eight contract continuations, eighty development responses. All use `google/gemma-4-26B-A4B-it`. No GPT/Claude requests or model downloads are performed.
