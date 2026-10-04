# Paper1 real annotation returns, 2026-10-04

Both received JSON files pass the original strict validator: A and B each supply 200 D items and 200 E items, with complete labels and required explanations. The public sample hash and coordinator mapping match the original delivery. Input files are never rewritten.

**Status: independent returns complete; adjudication pending.** There are 154 disputed items (D 76, E 78), covering 214 individual label decisions. No model supplied or changed a label; no API was called. No final adjudicated scores or manuscript results were produced.

- [Chinese receipt report](../../paper1/HUMAN_RETURN_CHECK_2026-10-04.md)
- [Coordinator instructions](ADJUDICATION_GUIDE_zh.md)
- `receipt_summary.json`: pre-adjudication agreement, confusion counts, denominators and input hashes.
- `local/raw/`: byte-identical JSON backups.
- `local/merged/`: original merge-script output, full context, immutable independent labels and blank disputed adjudication cells.
- `local/争议索引.csv`: review index only, not a substitute for the complete adjudication tables.
- `local/Paper1_人工结果裁决包_2026-10-04.zip`: coordinator handoff, with hidden method identities.

Raw returns, notes, source context and the adjudication handoff remain local, excluded from Git. The original uploaded folder is also left untouched and is not included in this commit.

Reproduce from the repository root:

```bash
/tmp/kgbench-local-venv/bin/python exps/paper1_human_returns_20261004/check_returns.py --input 'exps/paper1_人工标注完整包 2'
```

The script uses the original validator and merge code, preserves existing adjudication files, and refuses changed independent fields. A pre-existing handoff ZIP is not replaced. It does not call final scoring or infer semantic-effect categories. Human workflow independence and qualifications cannot be established from file structure alone.
