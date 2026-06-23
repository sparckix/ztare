from __future__ import annotations

from ztare.research_director.learning_promotion_contract import (
    build_learning_promotion_contract,
    validate_learning_promotion_contract,
)


def _agentic_candidate() -> dict[str, object]:
    return {
        "candidate_id": "agentic:missing_surface_preparations",
        "source_kind": "agentic_workbench",
        "transition_kind": "source_repair",
        "object_ref": "missing_surface_preparations",
        "source_refs": [
            "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl"
        ],
    }


def test_agentic_route_promotion_contract_is_valid_with_audit_fields() -> None:
    contract = build_learning_promotion_contract(_agentic_candidate())

    ok, missing = validate_learning_promotion_contract(contract)

    assert ok is True
    assert missing == []
    assert contract["promotion_decision"] == "promote_to_typed_carrier_candidate"
    assert contract["recurrence_evidence"]
    assert contract["primitive_amnesia_note"]
    assert contract["action_intelligence_compatibility"]
    assert contract["source_readiness_effect"]
    assert contract["kernel_action_schema"]["record_type"] == "kernel_action_schema"


def test_non_review_promotion_requires_recurrence_evidence() -> None:
    contract = build_learning_promotion_contract(_agentic_candidate())
    contract["recurrence_evidence"] = []

    ok, missing = validate_learning_promotion_contract(contract)

    assert ok is False
    assert "recurrence_evidence" in missing


def test_non_review_promotion_requires_primitive_amnesia_note() -> None:
    contract = build_learning_promotion_contract(_agentic_candidate())
    contract["primitive_amnesia_note"] = ""

    ok, missing = validate_learning_promotion_contract(contract)

    assert ok is False
    assert "primitive_amnesia_note" in missing


def test_typed_carrier_promotion_requires_action_intelligence_compatibility() -> None:
    contract = build_learning_promotion_contract(_agentic_candidate())
    contract["action_intelligence_compatibility"] = ""

    ok, missing = validate_learning_promotion_contract(contract)

    assert ok is False
    assert "action_intelligence_compatibility" in missing


def test_typed_carrier_promotion_validates_kernel_action_schema() -> None:
    contract = build_learning_promotion_contract(_agentic_candidate())
    contract["kernel_action_schema"] = {"record_type": "kernel_action_schema"}

    ok, missing = validate_learning_promotion_contract(contract)

    assert ok is False
    assert "kernel_action_schema.target_mapping" in missing
    assert "kernel_action_schema.nearest_confuser" in missing
    assert "kernel_action_schema.falsifier" in missing
    assert "kernel_action_schema.verification_artifact" in missing


def test_forecast_decision_use_gap_is_valid_source_repair_not_promotion() -> None:
    contract = build_learning_promotion_contract(
        {
            "candidate_id": "forecast:decision_use_gap",
            "source_kind": "forecast_market",
            "transition_kind": "source_repair",
            "object_ref": "decision_use_gap",
            "source_refs": [
                "analytics/public/forecast_pool/decision_use/decision_use_ledger.jsonl"
            ],
        }
    )

    ok, missing = validate_learning_promotion_contract(contract)

    assert ok is True
    assert missing == []
    assert contract["promotion_decision"] == "close_as_source_repair_not_primitive"
    assert contract["typed_carrier"] == "forecast_decision_use_source_repair"
