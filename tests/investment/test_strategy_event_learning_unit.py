from ztare.investment.workspace import _compile_strategy_event_learning_units


def test_closed_event_cannot_inherit_an_unbound_frontier(tmp_path):
    shadow = {
        "event_research_queue": [{
            "entity_id": "CLOSED", "research_request_sha256": "event",
            "move_observation_sha256": "move", "research_priority_rank": 1,
        }],
    }
    acquisition = {"discovery_outcomes": [{
        "entity_id": "CLOSED", "event_research_request_sha256": "event",
        "state": "frontier_closed", "reason": "missing typed input",
    }]}
    result = _compile_strategy_event_learning_units(
        tmp_path, shadow=shadow, acquisition=acquisition, dossiers=(),
        frontiers=({"company": {}, "strategy_frontier_sha256": "unrelated"},),
    )

    unit = result["units"][0]
    assert unit["stage"] == "discovery_frontier_closed"
    assert unit["strategy_frontier_sha256"] is None
