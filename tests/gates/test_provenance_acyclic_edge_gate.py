from ztare.gates.provenance_acyclic_edge_gate import (
    run_provenance_acyclic_edge_gate,
)


def test_provenance_acyclic_edge_passes_clean_source_edge() -> None:
    result = run_provenance_acyclic_edge_gate({
        "edge_id": "level524",
        "target_family": "L3AFiniteCofinalEventSelectorSource",
        "source_families": [
            "BadCenterEventPrefixCoversSelectedBadTree",
            "BadCenterCofinalSelectedTreeIncidenceReceipt",
        ],
        "constructed_families": ["L3AFiniteCofinalEventSelectorSource"],
        "forbidden_source_families": [
            "L3AEventPrefixEnumerationTypedCoveragePacketSource",
        ],
        "dependency_edges": [
            {
                "from": "BadCenterEventPrefixCoversSelectedBadTree",
                "to": "L3AFiniteCofinalEventSelectorSource",
            },
            {
                "from": "BadCenterCofinalSelectedTreeIncidenceReceipt",
                "to": "L3AFiniteCofinalEventSelectorSource",
            },
        ],
        "nearest_confuser": "L3AEventPrefixEnumerationTypedCoveragePacketSource",
        "confuser_distinction": "ordinary coverage is a source; typed packet is downstream",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["complete"] is True


def test_provenance_acyclic_edge_blocks_forbidden_downstream_source() -> None:
    result = run_provenance_acyclic_edge_gate({
        "edge_id": "bad-level524",
        "target_family": "L3AFiniteCofinalEventSelectorSource",
        "source_families": ["L3AEventPrefixEnumerationTypedCoveragePacketSource"],
        "constructed_families": ["L3AFiniteCofinalEventSelectorSource"],
        "forbidden_source_families": [
            "L3AEventPrefixEnumerationTypedCoveragePacketSource",
        ],
        "dependency_edges": [],
        "nearest_confuser": "L3AEventPrefixEnumerationTypedCoveragePacketSource",
        "confuser_distinction": "none",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["hard_violations_present"] == [
        "forbidden_downstream_family_used"
    ]


def test_provenance_acyclic_edge_blocks_declared_cycle() -> None:
    result = run_provenance_acyclic_edge_gate({
        "edge_id": "cycle",
        "target_family": "Target",
        "source_families": ["Source"],
        "constructed_families": ["Target"],
        "forbidden_source_families": [],
        "dependency_edges": [
            {"from": "Source", "to": "Target"},
            {"from": "Target", "to": "Source"},
        ],
        "nearest_confuser": "Target-derived Source",
        "confuser_distinction": "none",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["hard_violations_present"] == ["dependency_cycle"]
    assert result["cycle"] == ["Source", "Target", "Source"]


def test_provenance_acyclic_edge_exact_falsey_not_prefix() -> None:
    result = run_provenance_acyclic_edge_gate({
        "edge_id": "edge",
        "target_family": "Target",
        "source_families": ["Source"],
        "constructed_families": ["Target"],
        "forbidden_source_families": ["Forbidden"],
        "dependency_edges": [{"from": "Source", "to": "Target"}],
        "nearest_confuser": "missing because no confuser applies",
        "confuser_distinction": "Source is not target-derived",
    }, enforce_block=True)

    assert result["passed"] is True
    assert result["missing_fields"] == []


def test_provenance_acyclic_edge_exact_falsey_blocks() -> None:
    result = run_provenance_acyclic_edge_gate({
        "edge_id": "edge",
        "target_family": "Target",
        "source_families": ["Source"],
        "constructed_families": ["Target"],
        "forbidden_source_families": ["Forbidden"],
        "dependency_edges": [{"from": "Source", "to": "Target"}],
        "nearest_confuser": "missing",
        "confuser_distinction": "Source is not target-derived",
    }, enforce_block=True)

    assert result["passed"] is False
    assert result["missing_fields"] == ["nearest_confuser"]


def test_provenance_acyclic_edge_advisory_mode_passes_incomplete() -> None:
    result = run_provenance_acyclic_edge_gate({"edge_id": "incomplete"})

    assert result["passed"] is True
    assert result["complete"] is False
    assert "target_family" in result["missing_fields"]
