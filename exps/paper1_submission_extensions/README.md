# Paper 1 submission-extension experiments

This directory contains the experiments added to address the main DMKD
submission risks: natural extraction errors, a strong simple pipeline, actual
router-controlled execution, constraint-gate auditing, domain/model
generalization, and scaling.

The API runner is resumable and uses `httpx.Client(trust_env=False)` so the
server's local proxy settings are not inherited. It reads the endpoint and key
from the repository-local `api` file and never writes the key to an output.

Run the complete workflow from the repository root:

```bash
python3 exps/paper1_submission_extensions/run_api_experiments.py --stages all --workers 8
python3 exps/paper1_submission_extensions/run_scalability.py
python3 exps/paper1_submission_extensions/analyze_experiments.py
# After two independent annotators and adjudication fill the frozen sheet:
python3 exps/paper1_submission_extensions/score_human_annotations.py
```

The natural-error experiment uses real Claude extraction outputs from 225 held-out
source documents and the structured source fields as reference graphs. The
frozen 200-item annotation sheet still requires two independent human
annotators; model judgments must not be reported as human agreement.
