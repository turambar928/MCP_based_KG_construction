import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "exps" / "decision_network" / "build_from_repair_benchmark.py"
SPEC = importlib.util.spec_from_file_location("build_decision_dataset", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_graph_features_expose_each_quality_deficit():
    clean = [
        {"head": "doc", "relation": "服务事项", "tail": "事项"},
        {"head": "doc", "relation": "行驶主体", "tail": "机构"},
    ]
    case = {"clean_triples": clean, "allowed_relations": ["服务事项", "行驶主体"],
            "evidence_text": "事项 机构"}
    dirty = [clean[0], clean[0], {"head": "wrong", "relation": "UNKNOWN_REL", "tail": "错误"}]
    features = MODULE.graph_features(case, dirty)

    assert features["S_iso"] < 100
    assert features["S_red"] < 100
    assert features["S_log"] < 100
    assert features["S_sem"] < 100
    assert features["n_viol_feat"] >= 4
