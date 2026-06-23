from ztare.gates.provenance_edge_direction_gate import (
    run_provenance_edge_direction_gate,
)


def test_provenance_edge_direction_construct_passes_clean_edge() -> None:
    result = run_provenance_edge_direction_gate({
        "edge_id": "level522",
        "direction": "construct",
        "source_fields": [
            {"name": "selector", "status": "proved", "artifact": "repo/a.lean"},
            {"name": "selector_bound", "status": "verified", "artifact": "repo/a.lean"},
        ],
        "constructed_fields": ["explicit_witness"],
        "derived_conclusions": ["level521_source"],
        "forbidden_assumed_fields": ["explicit_witness"],
        "same_witness_bindings": [{
            "witness_field": "selector",
            "bound_field": "selector_bound",
        }],
        "endpoint_restatement_forbidden": True,
        "nearest_confuser": "explicit subtype witness only",
        "confuser_distinction": "selector is source and subtype is constructed",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True


def test_provenance_edge_direction_blocks_constructed_field_as_source() -> None:
    result = run_provenance_edge_direction_gate({
        "edge_id": "bad-edge",
        "direction": "construct",
        "source_fields": [{
            "name": "explicit_witness",
            "status": "proved",
            "artifact": "repo/a.lean",
        }],
        "constructed_fields": ["explicit_witness"],
        "derived_conclusions": [],
        "forbidden_assumed_fields": [],
        "nearest_confuser": "self assumption",
        "confuser_distinction": "none",
    }, enforce_block=True)

    assert result["passed"] is False
    assert "constructed_field_listed_as_source" in result["hard_violations_present"]


def test_provenance_edge_direction_blocks_unproved_source() -> None:
    result = run_provenance_edge_direction_gate({
        "edge_id": "bad-edge",
        "direction": "construct",
        "source_fields": [{
            "name": "selector",
            "status": "owed",
            "artifact": "repo/a.lean",
        }],
        "constructed_fields": ["explicit_witness"],
        "derived_conclusions": [],
        "forbidden_assumed_fields": [],
        "nearest_confuser": "owed source",
        "confuser_distinction": "none",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["hard_violations_present"] == ["unproved_source_field"]


def test_provenance_edge_direction_blocks_endpoint_restatement() -> None:
    result = run_provenance_edge_direction_gate({
        "edge_id": "bad-edge",
        "direction": "construct",
        "source_fields": [{
            "name": "selector",
            "status": "proved",
            "artifact": "repo/a.lean",
        }],
        "constructed_fields": ["explicit_witness"],
        "derived_conclusions": [],
        "forbidden_assumed_fields": [],
        "endpoint_restatement_forbidden": True,
        "endpoint_restatement_used": "endpoint capacity as bound",
        "nearest_confuser": "endpoint bound",
        "confuser_distinction": "none",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["hard_violations_present"] == ["endpoint_restatement_used"]


def test_provenance_edge_direction_advisory_mode_passes_incomplete() -> None:
    result = run_provenance_edge_direction_gate({
        "edge_id": "incomplete",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert "direction" in result["missing_fields"]
