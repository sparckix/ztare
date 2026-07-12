from ztare.scenarios.decision_state import compile_decision_state, diff_decision_states
from ztare.scenarios.governed_types import GovernedEdge, GovernedElement, GovernedState


def _state(*edges, with_gap=False):
    elements = [
        GovernedElement("thesis", "thesis", "Ship the product"),
        GovernedElement("source", "evidence", "Pilot met its target", source_key="pilot"),
    ]
    if with_gap:
        elements.append(GovernedElement("gap", "gap", "Production behavior is unknown"))
    return GovernedState(elements, list(edges))


def test_decision_state_is_the_authoritative_crisp_posture():
    supported = compile_decision_state(
        _state(GovernedEdge("source", "SUPPORTS", "thesis", "W2"))
    ).to_payload()
    assert supported["status"] == "SUPPORTED"
    assert supported["posture"] == "proceed"
    assert supported["trust_floor"] == "cited"
    assert supported["strength"]["status"] == "CONTESTED"

    blocked = compile_decision_state(
        _state(GovernedEdge("source", "SUPPORTS", "thesis", "W2"), with_gap=True)
    ).to_payload()
    assert blocked["status"] == "BLOCKED"
    assert blocked["posture"] == "investigate"
    assert blocked["next_test"]["id"] == "gap"


def test_decision_fingerprint_changes_when_admitted_structure_changes():
    unsupported = compile_decision_state(_state()).to_payload()
    supported = compile_decision_state(
        _state(GovernedEdge("source", "SUPPORTS", "thesis", "W2"))
    ).to_payload()
    assert unsupported["status"] == "BLOCKED"
    assert unsupported["strength"]["status"] == "UNSUPPORTED"
    assert unsupported["fingerprint"] != supported["fingerprint"]


def test_decision_delta_reports_status_transition():
    before = compile_decision_state(_state()).to_payload()
    after = compile_decision_state(
        _state(GovernedEdge("source", "SUPPORTS", "thesis", "W2"))
    ).to_payload()

    delta = diff_decision_states(before, after)

    assert delta["schema"] == "ztare-decision-delta-v1"
    assert delta["decision_changed"] is True
    assert delta["status"] == {"from": "BLOCKED", "to": "SUPPORTED", "changed": True}
    assert "status" in delta["changed_fields"]
    assert delta["from_fingerprint"] != delta["to_fingerprint"]


def test_decision_delta_distinguishes_metadata_from_decision_change():
    before = compile_decision_state(_state()).to_payload()
    after = dict(before)
    after["counts"] = {**before["counts"], "evidence": before["counts"]["evidence"] + 1}

    delta = diff_decision_states(before, after)

    assert delta["changed"] is True
    assert delta["decision_changed"] is False
    assert delta["changed_fields"] == ["counts"]
    assert delta["summary"].startswith("Decision held")


def test_decision_delta_is_stable_when_nothing_changed():
    state = compile_decision_state(_state()).to_payload()
    delta = diff_decision_states(state, state)

    assert delta["changed"] is False
    assert delta["decision_changed"] is False
    assert delta["changed_fields"] == []
    assert delta["strength_delta"] == [0.0, 0.0, 0.0, 0.0]
