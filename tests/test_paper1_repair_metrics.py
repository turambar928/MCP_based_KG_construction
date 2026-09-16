import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "exps" / "paper1_repair_benchmark" / "analyze_results.py"
SPEC = importlib.util.spec_from_file_location("repair_metrics", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_case_metrics_rewards_exact_repair_and_penalizes_harmful_edit():
    clean = [
        {"head": "doc", "relation": "服务事项", "tail": "事项"},
        {"head": "doc", "relation": "行驶主体", "tail": "机构"},
    ]
    dirty = [clean[0], {"head": "doc", "relation": "UNKNOWN_REL", "tail": "机构"}]
    case = {
        "case_id": "c", "domain": "government", "evidence_text": "事项 机构",
        "allowed_relations": ["服务事项", "行驶主体"], "clean_triples": clean,
        "corrupted_triples": dirty,
        "defects": [{"defect_id": "d", "defect_type": "invalid_relation",
                     "gold_triple": clean[1], "corrupted_triple": dirty[1]}],
    }
    exact, outcomes = MODULE.case_metrics(case, {"method": "ours", "status": "ok", "triples": clean})
    harmful, _ = MODULE.case_metrics(case, {"method": "bad", "status": "ok", "triples": [clean[0]]})

    assert exact["defect_repair_rate"] == 1.0
    assert exact["repair_precision"] == 1.0
    assert exact["exact_match"] == 1.0
    assert outcomes == {"d": True}
    assert harmful["defect_repair_rate"] == 0.0
    assert harmful["triple_recall"] < exact["triple_recall"]
