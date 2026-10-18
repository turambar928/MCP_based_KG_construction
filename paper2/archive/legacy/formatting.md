# Paper2 active formatting and build

The active manuscript is `main.tex`, using `IEEEtran` in journal mode.
The `latex/` ACL files are historical and do not control this build.

```bash
cd paper2
tectonic -X compile main.tex --keep-logs
```

The document uses `fontspec`; select XeLaTeX in Overleaf. Times New Roman is
preferred, with bundled TeX Gyre Termes used when it is unavailable.
The complete project is `overleaf/`, also available as `paper2_overleaf.zip`.
Check the current TKDE author instructions before submission for page,
anonymity, and supplement requirements. This repository does not fix a journal
page limit.

Generate the revised publication tables and vector figures from existing results:

```bash
python3 exps/paper2_offline_revision/make_tables.py
python3 exps/paper2_offline_revision/make_figures.py
```

Run those commands at the repository root. The manuscript includes PDFs from
`figure/method/` and `figure/experiments/offline_*.pdf`. Editable SVGs and PNG
previews accompany them. The generator uses Times New Roman, embedded TrueType
fonts, restrained colors, and distinguishable line styles or hatching. Keep
original PNG diagrams and old result figures as historical artifacts; they are
not the active revised figures.

Current tables are merged into `sections/experiments.tex` and `sections/appendix.tex`.
The generator still writes to `tables/` as an analysis archive. After a documented
analysis change, regenerate and copy the affected tables into their chapter,
checking numerical consistency. The Overleaf project has no `tables/` dependency.
Do not stage `main.log` or `main.blg`. `main.pdf` is tracked for review.
