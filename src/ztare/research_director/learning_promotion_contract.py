"""Typed contracts for promoting repeated learning failures into checks.

The operations-intelligence layer can surface many observer-only candidates.
This module decides which of those candidates are strong enough to become a
typed carrier candidate, and records the evidence fields that would make the
promotion auditable instead of vocabulary growth.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ztare.common.kernel_action_schema import (
    KernelActionSchema,
    validate_kernel_action_schema,
)


AGENTIC_ROUTE_OBJECT_REFS = {
    "missing_route_rows_for_high_out_of_loop_share",
    "sparse_route_rows_for_high_out_of_loop_share",
    "ready_workbench_bypasses_without_reason",
    "missing_surface_preparations",
    "transport_metadata_missing",
}

AGENTIC_ROUTE_REQUIRED_FIELDS = (
    "bounded_claim",
    "stable_evaluator",
    "rubric_ready",
    "artifact_surface",
    "workbench_router_decision",
    "why_not_autoresearch",
    "worker_metadata",
    "route_json_ref",
    "action_impact_ref",
    "workbench_evidence_ref",
)

FORECAST_DECISION_USE_OBJECT_REFS = {
    "analytics/public/forecast_pool/decision_use/decision_use_ledger.jsonl",
    "missing_decision_use",
}

REQUIRED_PROMOTION_FIELDS = (
    "candidate_id",
    "source_kind",
    "transition_kind",
    "object_ref",
    "nearest_existing_surface",
    "nearest_confuser",
    "typed_carrier",
    "deterministic_validator",
    "ex_post_usage_criterion",
    "non_claim",
    "kill_criterion",
)

NON_REVIEW_PROMOTION_FIELDS = (
    "recurrence_evidence",
    "primitive_amnesia_note",
)

TYPED_CARRIER_PROMOTION_FIELDS = (
    "carrier_required_fields",
    "action_intelligence_compatibility",
    "source_readiness_effect",
    "kernel_action_schema",
)


@dataclass(frozen=True)
class LearningPromotionContract:
    schema_version: int
    record_type: str
    candidate_id: str
    source_kind: str
    transition_kind: str
    object_ref: str
    promotion_decision: str
    nearest_existing_surface: str
    nearest_confuser: str
    typed_carrier: str
    carrier_required_fields: list[str] = field(default_factory=list)
    deterministic_validator: str = ""
    ex_post_usage_criterion: str = ""
    action_intelligence_compatibility: str = ""
    source_readiness_effect: str = ""
    non_claim: str = ""
    kill_criterion: str = ""
    recurrence_evidence: list[str] = field(default_factory=list)
    primitive_amnesia_note: str = ""
    kernel_action_schema: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_learning_promotion_contract(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a typed promotion contract for an operations learning candidate."""

    source_kind = str(candidate.get("source_kind") or "")
    object_ref = str(candidate.get("object_ref") or "")
    candidate_id = str(candidate.get("candidate_id") or "")
    transition_kind = str(candidate.get("transition_kind") or "")

    if _is_agentic_route_candidate(source_kind, object_ref):
        kernel_action = KernelActionSchema(
            source_kind="operations_intelligence",
            action_family="learning_promotion",
            action_name="agentic_workbench_route_accounting",
            source_summary=(
                "Repeated agentic/autoresearch boundary failures are promoted "
                "only into route-accounting carriers, not into evidence claims."
            ),
            target_mapping=(
                "agentic workbench route gap -> OP-AWR-01 route row + action "
                "intelligence carrier + optional hypothesis projection"
            ),
            nearest_confuser=(
                "out-of-loop artifact volume or worker identity treated as "
                "evidence without a route row, bypass reason, or carrier"
            ),
            falsifier=(
                "a ready autoresearch surface is bypassed without "
                "why_not_autoresearch and action_impact_ref"
            ),
            verification_artifact=(
                "tests/reports/test_operations_intelligence.py::"
                "test_build_tracks_agentic_workbench_action_rows"
            ),
            action_constraints=[
                "do not treat route rows as truth evidence",
                "require source_refs and action-impact compatibility",
                "record missing surfaces instead of hiding them in session memory",
            ],
            evidence_basis="OP-AWR-01, operations_intelligence route coverage, and primitive-amnesia precheck",
            payload={
                "candidate_id": candidate_id,
                "object_ref": object_ref,
                "required_fields": list(AGENTIC_ROUTE_REQUIRED_FIELDS),
            },
        ).to_dict()
        return LearningPromotionContract(
            schema_version=1,
            record_type="ztare_learning_promotion_contract",
            candidate_id=candidate_id,
            source_kind=source_kind,
            transition_kind=transition_kind,
            object_ref=object_ref,
            promotion_decision="promote_to_typed_carrier_candidate",
            nearest_existing_surface=(
                "OP-AWR-01:autoresearch_workbench_routing; "
                "pattern_action_contract.autoresearch_workbench_routing; "
                "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl"
            ),
            nearest_confuser=kernel_action["nearest_confuser"],
            typed_carrier="agentic_workbench_route_accounting",
            carrier_required_fields=list(AGENTIC_ROUTE_REQUIRED_FIELDS),
            deterministic_validator=kernel_action["verification_artifact"],
            ex_post_usage_criterion=(
                "A later operations-intelligence refresh shows the candidate "
                "resolved by route/action rows with source_refs, or the missing "
                "surface is explicitly closed as not worth promoting."
            ),
            action_intelligence_compatibility=(
                "Carrier rows must be representable as action-impact records "
                "with decision_point, candidate_actions, selected_action, "
                "logged_policy, context_features, source_refs, and outcome."
            ),
            source_readiness_effect=(
                "Until paid, this supports triage/source repair only; it must "
                "not drive allocation claims."
            ),
            non_claim=(
                "Does not claim autoresearch output quality, model lift, or "
                "worker superiority."
            ),
            kill_criterion=(
                "Do not promote if the candidate lacks recurrence evidence, "
                "source_refs, or a deterministic validator consuming the carrier."
            ),
            recurrence_evidence=list(candidate.get("source_refs") or []),
            primitive_amnesia_note=(
                "Precheck surfaced nearby primitives "
                "AUTORESEARCH-KERNEL-HEALTH, PREDICTION-LOGGING-DISCRIMINATOR, "
                "OP-AWR-01, and action-intelligence rows; no exact promotion "
                "contract primitive was found."
            ),
            kernel_action_schema=kernel_action,
        ).to_dict()

    if _is_forecast_decision_use_gap(source_kind, object_ref, candidate):
        return LearningPromotionContract(
            schema_version=1,
            record_type="ztare_learning_promotion_contract",
            candidate_id=candidate_id,
            source_kind=source_kind,
            transition_kind=transition_kind,
            object_ref=object_ref,
            promotion_decision="close_as_source_repair_not_primitive",
            nearest_existing_surface=(
                "PREDICTION-LOGGING-DISCRIMINATOR; "
                "PATTERN-012-PREDICTION-LEDGER; "
                "analytics/public/forecast_pool/decision_use/decision_use_ledger.jsonl"
            ),
            nearest_confuser=(
                "treating sparse forecast decision-use rows as a new primitive "
                "instead of repairing the existing causal-use ledger"
            ),
            typed_carrier="forecast_decision_use_source_repair",
            carrier_required_fields=[
                "forecast_contract_id",
                "forecast_aggregate_ref",
                "decision_id",
                "selected_action",
                "decision_changed_before_outcome",
                "outcome_ref",
            ],
            deterministic_validator=(
                "tests/reports/test_operations_intelligence.py::"
                "test_build_extracts_focus_track_intelligence_and_source_health"
            ),
            ex_post_usage_criterion=(
                "A later operations-intelligence refresh shows the decision-use "
                "gap shrinking through rows that bind forecasts to decisions made "
                "before outcome resolution."
            ),
            action_intelligence_compatibility=(
                "Rows should be joinable to action-intelligence or forecast "
                "decision-use records, but they do not themselves prove allocation lift."
            ),
            source_readiness_effect=(
                "Until repaired, forecast-market rows remain source-readiness debt "
                "for allocation and calibration claims."
            ),
            non_claim=(
                "Does not claim forecast skill, decision lift, or a new primitive; "
                "this is a non-promotion until causal-use rows exist."
            ),
            kill_criterion=(
                "Do not promote while the nearest existing prediction logging and "
                "decision-use ledger surfaces can represent the missing evidence."
            ),
            recurrence_evidence=list(candidate.get("source_refs") or []),
            primitive_amnesia_note=(
                "Precheck surfaced PREDICTION-LOGGING-DISCRIMINATOR, "
                "PATTERN-012-PREDICTION-LEDGER, and decision-use ledger surfaces; "
                "this gap is closed as source repair rather than a new primitive."
            ),
        ).to_dict()

    return LearningPromotionContract(
        schema_version=1,
        record_type="ztare_learning_promotion_contract",
        candidate_id=candidate_id,
        source_kind=source_kind,
        transition_kind=transition_kind,
        object_ref=object_ref,
        promotion_decision="review_only",
        nearest_existing_surface="operations_intelligence.learning_candidates",
        nearest_confuser=(
            "treating an observer-only candidate as a promoted primitive without "
            "recurrence evidence, a typed carrier, and a deterministic validator"
        ),
        typed_carrier="none",
        deterministic_validator="none",
        ex_post_usage_criterion="none",
        non_claim="Review-only candidates are not primitive promotions.",
        kill_criterion="Promote only after recurrence, duplicate, carrier, and validator checks are paid.",
        recurrence_evidence=list(candidate.get("source_refs") or []),
    ).to_dict()


def validate_learning_promotion_contract(contract: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check that a promotion contract has the required auditable fields."""

    missing: list[str] = []
    for field_name in REQUIRED_PROMOTION_FIELDS:
        value = str(contract.get(field_name) or "").strip()
        if not value or value == "none":
            missing.append(field_name)

    promotion_decision = str(contract.get("promotion_decision") or "").strip()
    if promotion_decision != "review_only":
        for field_name in NON_REVIEW_PROMOTION_FIELDS:
            value = contract.get(field_name)
            if isinstance(value, list):
                if not value:
                    missing.append(field_name)
            elif not str(value or "").strip():
                missing.append(field_name)

    if promotion_decision == "promote_to_typed_carrier_candidate":
        for field_name in TYPED_CARRIER_PROMOTION_FIELDS:
            value = contract.get(field_name)
            if isinstance(value, (dict, list)):
                if not value:
                    missing.append(field_name)
            elif not str(value or "").strip():
                missing.append(field_name)
        kernel_action = contract.get("kernel_action_schema")
        if isinstance(kernel_action, dict) and kernel_action:
            ok, action_missing = validate_kernel_action_schema(kernel_action)
            if not ok:
                missing.extend(
                    f"kernel_action_schema.{field_name}"
                    for field_name in action_missing
                )
        else:
            missing.append("kernel_action_schema")
    return not missing, missing


def _is_agentic_route_candidate(source_kind: str, object_ref: str) -> bool:
    if source_kind != "agentic_workbench":
        return False
    if object_ref in AGENTIC_ROUTE_OBJECT_REFS:
        return True
    return object_ref.startswith("missing_route_rows") or object_ref.startswith("sparse_route_rows")


def _is_forecast_decision_use_gap(
    source_kind: str,
    object_ref: str,
    candidate: dict[str, Any],
) -> bool:
    issue_type = str((candidate.get("proposed_payload") or {}).get("issue_type") or "")
    if source_kind == "forecast_market" and object_ref == "decision_use_gap":
        return True
    if source_kind == "source_health" and (
        issue_type == "missing_decision_use"
        or object_ref in FORECAST_DECISION_USE_OBJECT_REFS
        or "forecast_pool/decision_use" in object_ref
    ):
        return True
    return False
