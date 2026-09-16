import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "data_generation" / "generate_low_quality_dataset.py"
SPEC = importlib.util.spec_from_file_location("low_quality_generator", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
LowQualityDataGenerator = MODULE.LowQualityDataGenerator


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_generator_is_reproducible_and_logs_only_actual_changes(tmp_path):
    source = tmp_path / "source.jsonl"
    rows = [
        {
            "统一发布平台unid": f"doc-{i}",
            "服务事项": "行政处罚事项",
            "权力类型": "行政处罚",
            "行驶主体": "某市政府",
            "承办机构": "某区政府",
            "实施依据": "中华人民共和国行政处罚法",
            "监管电话": "029-12345",
            "责任事项": "违法主体：某企业\n处罚日期：2024-01-01",
        }
        for i in range(8)
    ]
    source.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")

    outputs = []
    manifests = []
    for run in (1, 2):
        output = tmp_path / f"dirty-{run}.jsonl"
        manifest = tmp_path / f"manifest-{run}.jsonl"
        LowQualityDataGenerator().generate_low_quality_dataset(
            str(source), str(output), corruption_rate=1.0, issues_per_record=2,
            seed=42, manifest_file=str(manifest),
        )
        outputs.append(output.read_text(encoding="utf-8"))
        manifests.append(manifest.read_text(encoding="utf-8"))

    assert outputs[0] == outputs[1]
    assert manifests[0] == manifests[1]

    dirty = _read_jsonl(tmp_path / "dirty-1.jsonl")
    manifest = _read_jsonl(tmp_path / "manifest-1.jsonl")
    assert {row["统一发布平台unid"] for row in dirty} == {row["统一发布平台unid"] for row in rows}
    assert manifest
    for change in manifest:
        assert change["original_value"] != change["corrupted_value"]
        assert change["document_id"].startswith("doc-")
        assert change["seed"] == 42
