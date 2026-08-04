from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
    plan_observed_action_frontier,
)


def test_witnessed_section_never_invents_a_fiber_member():
    rows = [
        PartialActionObservation(
            source={"state": "a"},
            operation="move",
            successor={"state": "b"},
            evidence_ref="bank#0",
        )
    ]
    system = build_partial_action_system(
        rows,
        project=lambda raw: raw["state"],
        effect=lambda _s, _a, _n, source, target: (source, target),
        projection_id="projection-v1",
    )

    assert system.passed_section
    assert system.representative("a") is rows[0].source
    assert system.representative("b") is rows[0].successor


def test_multiple_effects_for_one_source_operation_are_not_merged():
    rows = [
        PartialActionObservation(
            source={"state": "same", "hidden": 0},
            operation="step",
            successor={"state": "left"},
            evidence_ref="bank#0",
        ),
        PartialActionObservation(
            source={"state": "same", "hidden": 1},
            operation="step",
            successor={"state": "right"},
            evidence_ref="bank#1",
        ),
    ]
    system = build_partial_action_system(
        rows,
        project=lambda raw: raw["state"],
        effect=lambda _s, _a, _n, source, target: (source, target),
        projection_id="projection-v1",
    )

    relation = system.noncommuting_relations[("same", "step")]
    assert relation == frozenset({
        ("same", "left"),
        ("same", "right"),
    })
    relation_receipt = system.to_receipt()["noncommuting_relations"][0]
    assert relation_receipt["relation_evidence_refs"] == [
        "bank#0",
        "bank#1",
    ]
    assert {
        tuple(row["evidence_refs"])
        for row in relation_receipt["effect_witnesses"]
    } == {("bank#0",), ("bank#1",)}


def test_exception_rank_opposes_support_volume():
    common = [
        PartialActionObservation(
            source=("ordinary", index),
            operation=0,
            successor=("ordinary", index + 1),
            evidence_ref=f"bank#{index}",
        )
        for index in range(8)
    ]
    rare = PartialActionObservation(
        source=("exception", 0),
        operation=0,
        successor=("exception", 1),
        evidence_ref="bank#rare",
    )
    system = build_partial_action_system(
        [*common, rare],
        project=lambda raw: raw,
        effect=lambda source, _a, _n, _sk, _tk: (
            "rare" if source[0] == "exception" else "ordinary"
        ),
        projection_id="projection-v1",
        exceptional_weight=lambda row, _effect: (
            5.0 if row.evidence_ref == "bank#rare" else 0.0
        ),
    )

    assert system.ranked[0].effect == "rare"
    assert system.ranked[0].support == 1


def test_boundary_is_partiality_not_a_synthetic_successor():
    row = PartialActionObservation(
        source="terminal",
        operation="advance",
        successor=None,
        evidence_ref="trace#7",
        boundary_kind="reset_boundary",
    )
    system = build_partial_action_system(
        [row],
        project=lambda raw: raw,
        effect=lambda *_args: (_ for _ in ()).throw(AssertionError()),
        projection_id="projection-v1",
    )

    ranked = system.ranked[0]
    assert ranked.boundary_kind == "reset_boundary"
    assert ranked.effect == ("boundary", "reset_boundary")


def test_observed_frontier_traverses_witnessed_edges_but_not_boundaries():
    rows = [
        PartialActionObservation(
            source="start",
            operation=0,
            successor="middle",
            evidence_ref="bank#0",
        ),
        PartialActionObservation(
            source="middle",
            operation=0,
            successor=None,
            evidence_ref="bank#1",
            boundary_kind="reset_boundary",
        ),
    ]
    system = build_partial_action_system(
        rows,
        project=lambda raw: raw,
        effect=lambda source, operation, target, *_keys: (
            source, operation, target
        ),
        projection_id="projection-v1",
        exceptional_weight=lambda row, _effect: (
            5.0 if row.source == "start" else 0.0
        ),
    )
    plan = plan_observed_action_frontier(
        system,
        start_key="start",
        operations=(0, 1),
    )

    assert plan.status == "frontier_pair_found"
    assert plan.actions == (0, 1)
    assert "reset" not in plan.actions


def test_observed_frontier_does_not_invent_branch_resolution():
    rows = [
        PartialActionObservation(
            source="start",
            operation=0,
            successor="left",
            evidence_ref="bank#0",
        ),
        PartialActionObservation(
            source="start",
            operation=0,
            successor="right",
            evidence_ref="bank#1",
        ),
    ]
    system = build_partial_action_system(
        rows,
        project=lambda raw: raw,
        effect=lambda _source, _operation, target, *_keys: target,
        projection_id="projection-v1",
    )
    plan = plan_observed_action_frontier(
        system,
        start_key="start",
        operations=(0, 1),
    )

    assert plan.status == "frontier_pair_found"
    assert plan.actions == (1,)
    assert plan.ambiguous_edges_on_path == 0


def test_observed_frontier_does_not_cross_boundary_contaminated_relation():
    rows = [
        PartialActionObservation(
            source="start",
            operation=0,
            successor="middle",
            evidence_ref="bank#0",
        ),
        PartialActionObservation(
            source="start",
            operation=0,
            successor=None,
            evidence_ref="bank#1",
            boundary_kind="control_exclusion",
        ),
    ]
    system = build_partial_action_system(
        rows,
        project=lambda raw: raw,
        effect=lambda _source, _operation, target, *_keys: target,
        projection_id="projection-v1",
    )
    plan = plan_observed_action_frontier(
        system,
        start_key="start",
        operations=(0,),
    )

    assert plan.status == "observed_frontier_exhausted"
    assert plan.reachable_nodes == 1
