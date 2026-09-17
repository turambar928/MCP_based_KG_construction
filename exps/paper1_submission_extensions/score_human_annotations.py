#!/usr/bin/env python3
"""Score the frozen two-annotator natural-error sheet after labels are filled."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from sklearn.metrics import cohen_kappa_score


HERE = Path(__file__).resolve().parent
INPUT = HERE / "natural_error_annotation_sample.csv"
OUTPUT = HERE / "human_annotation_results.json"


def binary(rows, column: str) -> list[int]:
    values = [row[column].strip() for row in rows]
    invalid = sorted({value for value in values if value not in {"0", "1"}})
    if invalid:
        raise RuntimeError(
            f"Column {column} is incomplete or contains non-binary labels: {invalid}. "
            "Resolve U labels during adjudication before scoring."
        )
    return [int(value) for value in values]


def agreement(a: list[int], b: list[int]) -> dict[str, float]:
    return {
        "n": len(a),
        "raw_agreement": sum(x == y for x, y in zip(a, b)) / len(a),
        "cohen_kappa": float(cohen_kappa_score(a, b)),
        "annotator_a_positive_rate": sum(a) / len(a),
        "annotator_b_positive_rate": sum(b) / len(b),
    }


def main() -> None:
    with INPUT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    error_a = binary(rows, "annotator_a_is_error")
    error_b = binary(rows, "annotator_b_is_error")
    repair_a = binary(rows, "annotator_a_repair_acceptable")
    repair_b = binary(rows, "annotator_b_repair_acceptable")
    adjudicated_error = binary(rows, "adjudicated_is_error")
    adjudicated_repair = binary(rows, "adjudicated_repair_acceptable")
    result = {
        "error_detection_agreement": agreement(error_a, error_b),
        "repair_acceptance_agreement": agreement(repair_a, repair_b),
        "adjudicated_error_precision": sum(adjudicated_error) / len(adjudicated_error),
        "adjudicated_repair_acceptance": sum(adjudicated_repair) / len(adjudicated_repair),
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
