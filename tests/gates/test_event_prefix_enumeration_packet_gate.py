from ztare.gates.event_prefix_enumeration_packet_gate import (
    REQUIRED_FIELDS,
    run_event_prefix_enumeration_packet_gate,
)


def test_event_prefix_enumeration_packet_advisory_mode_passes_incomplete() -> None:
    result = run_event_prefix_enumeration_packet_gate({
        "target_family": "L3A target prefix",
        "ordinary_coverage_only": "coverage exists",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert result["weak_substitutes_present"] == ["ordinary_coverage_only"]


def test_event_prefix_enumeration_packet_weak_substitute_is_advisory() -> None:
    result = run_event_prefix_enumeration_packet_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "typed_packet_assumed": "confuser only",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["weak_substitutes_present"] == ["typed_packet_assumed"]


def test_event_prefix_enumeration_packet_hard_violation_blocks() -> None:
    result = run_event_prefix_enumeration_packet_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "typed_packet_assumed_without_enumeration": "packet supplied directly",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["hard_violations_present"] == [
        "typed_packet_assumed_without_enumeration"
    ]


def test_event_prefix_enumeration_packet_falsey_is_exact_not_prefix() -> None:
    result = run_event_prefix_enumeration_packet_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "selected_bad_node_event_prefix_enumeration":
            "missing because enumeration theorem is pending",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["missing_fields"] == []
