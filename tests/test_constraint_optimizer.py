from content_enhancement.constraint_optimizer import (
    CandidateAction,
    MultiScaleConstraintOptimizer,
    QualityProfile,
)


def profile(**overrides):
    values = {
        "S_iso": 100.0,
        "S_red": 100.0,
        "S_log": 100.0,
        "S_sem": 100.0,
        "n_v": 2,
        "n_e": 1,
        "density": 0.5,
        "n_viol_feat": 0,
        "q_score": 100.0,
        "violations": [],
    }
    values.update(overrides)
    return QualityProfile(**values)


def test_profile_rates_are_bounded_for_multigraphs_and_duplicate_components():
    optimizer = MultiScaleConstraintOptimizer()
    entities = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
    triples = [
        {"head": "A", "relation": "r", "tail": "B"},
        {"head": "A", "relation": "r", "tail": "B"},
        {"head": "A", "relation": "r", "tail": "B"},
        {"head": "B", "relation": "different", "tail": "C"},
    ]

    assessed = optimizer.assess(entities, triples, "ABC")

    assert assessed.S_red == 50.0  # two removable rows in one 3-row component
    assert 0.0 <= assessed.density <= 1.0


def test_empty_graph_does_not_receive_perfect_connectivity():
    assessed = MultiScaleConstraintOptimizer().assess([], [], "")
    assert assessed.S_iso == 0.0


def test_fallback_router_always_returns_probability_simplex():
    optimizer = MultiScaleConstraintOptimizer()
    optimizer.router.available = False
    routed = optimizer.route(profile())
    assert abs(sum(routed.pi.values()) - 1.0) < 1e-12
    assert all(value >= 0.0 for value in routed.pi.values())


def test_restoration_constraint_allows_progress_below_lower_bound():
    optimizer = MultiScaleConstraintOptimizer()
    action = CandidateAction("complete", {}, {}, "entity", 1.0)

    feasible, _ = optimizer._check_constraints(
        profile(S_iso=40.0), profile(S_iso=45.0), action
    )
    regresses, reason = optimizer._check_constraints(
        profile(S_iso=40.0), profile(S_iso=39.0), action
    )

    assert feasible
    assert not regresses
    assert reason == "deficit_regression:S_iso"


def test_receding_horizon_policy_repairs_hierarchy_reversal():
    optimizer = MultiScaleConstraintOptimizer(max_iterations=4)
    entities = [{"name": "县环保局"}, {"name": "省生态环境厅"}]
    triples = [{"head": "县环保局", "relation": "管理", "tail": "省生态环境厅"}]

    enhanced, applied, audit = optimizer.optimize_and_apply(
        entities, triples, [], "县环保局由省生态环境厅管理"
    )

    assert {tuple((t["head"], t["relation"], t["tail"])) for t in enhanced} == {
        ("省生态环境厅", "管理", "县环保局")
    }
    assert len(applied) == 1
    assert audit["final_profile"]["S_log"] == 100.0
    assert any(d["accepted"] for d in audit["decisions"])


def test_source_support_normalizes_whitespace_on_both_sides():
    optimizer = MultiScaleConstraintOptimizer()
    supported = [("doc", "field", "office A")]
    assert optimizer._semantic_penalty(supported, "office A is responsible") == 0.0
    assert optimizer._semantic_penalty(supported, "office B is responsible") == 1.0
