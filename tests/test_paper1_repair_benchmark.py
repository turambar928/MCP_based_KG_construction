import importlib.util
from collections import Counter
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "exps" / "paper1_repair_benchmark" / "build_benchmark.py"
SPEC = importlib.util.spec_from_file_location("build_benchmark", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_corruption_manifest_matches_actual_graph_edits():
    clean = [
        {"head": "doc", "relation": "服务事项", "tail": "行政许可"},
        {"head": "doc", "relation": "行驶主体", "tail": "某市政府"},
        {"head": "doc", "relation": "承办机构", "tail": "某区政府"},
        {"head": "doc", "relation": "实施依据", "tail": "某法"},
    ]
    dirty1, defects1 = MODULE.corrupt_graph("government", "case-1", clean, 42)
    dirty2, defects2 = MODULE.corrupt_graph("government", "case-1", clean, 42)

    assert dirty1 == dirty2
    assert defects1 == defects2
    assert len(defects1) == 2
    assert len({d["source_triple_index"] for d in defects1}) == 2
    assert all(d["gold_triple"] in clean for d in defects1)
    assert Counter(tuple(t.values()) for t in dirty1) != Counter(tuple(t.values()) for t in clean)
