# Generated-rule scheduling on typed DocRED inputs

This separate experiment preserves Paper2's RL graph–rule co-optimization and dual-strategy generation main line. It does not overwrite the frozen design at `../paper2_generated_policy_protocol` or reuse its old eight-action model weights.

## Prepared data

300 documents from **original DocRED train_annotated** are source-grouped into 180 train / 60 development / 60 test documents. These are new experimental splits, not the official DocRED test set. All entities and their mention types are given. Conflicting types, invalid offsets and duplicate title/source documents are excluded without inferring types from names. See `data_manifest.json`, `membership.json`, `episodes.json` and `exclusions.json`.

Official source: <https://github.com/thunlp/DocRED>. The official Google Drive entry was unreachable. We retrieved the `thunlp/docred` dataset through `hf-mirror.com`; the three compressed files match the SHA-256 LFS object identifiers in the hosted dataset manifest. Download provenance is in `../submission_week_20260929/docred_download.json`. The dataset card metadata says MIT, but its licensing section says more information is needed. Consequently raw texts and local converted copies remain untracked pending redistribution review; code, checksums and split membership are tracked. This is not a claim that a repository MIT license covers underlying Wikipedia content.

## Implemented, not yet trained

`environment.py` implements four actions, response-level acquisition, shared document queues, a four-response budget, ten-step horizon, public 14-dimensional observations, fixed proxy reward, conflict abstention, late-permission logging and emptying protection. It has no reference-label argument. The stored reward can penalize newly revealed violations: that behavior is tested and must not be adjusted based on test performance.

`generation.py` preserves the two generation mechanisms: deletion completion gets original source, deleted-character version and removed fragments; augmentation proposes up to three supplementary clauses. Both may propose allowed and forbidden typed patterns. An allowed pattern is type compatibility, not proof of any specific fact. No relation reference labels are sent to the generator.

`pilot.py` runs ten fixed development documents: 20 rule-generation requests and ten natural graph extractions. It reports parsing, compilation, coverage and final-graph diversity under fixed schedules. These are viability diagnostics, not semantic accuracy or a learned-policy result. All source-containing requests/responses stay under ignored `local/`.

```bash
python3 exps/submission_week_20260929/fetch_data.py
python3 exps/paper2_docred/prepare.py
python3 -m unittest exps.paper2_docred.test_environment exps.paper2_docred.test_generation
/tmp/kgbench-local-venv/bin/python exps/paper2_docred/pilot.py
```

Prerequisites for formal learned-policy claims remain independent rule/edit review, meaningful rule coverage/decision effects, full training/evaluation implementation, a frozen concrete comparator family and label-isolation checks. **The user deferred human work on 2026-09-29.** Do not describe this implementation or its synthetic contract tests as completion of the missing end-to-end experiment. DocRED reference absence alone never establishes a naturally extracted triple is false.

Completed pilot: [Chinese coverage report](report_zh.md), [source-free packet archive](pilot_packets_public.json), [synthetic reward counterexample](reward_viability_zh.md). The pilot does not pass the coverage gate for expanded training.
