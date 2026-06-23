"""Typed validation for graph-shaped carriers.

This module is a schema and receipt guard, not a graph engine. Algorithms stay
with standard libraries or substrate adapters; this layer only checks that a
graph diagnostic has enough provenance and decision effect to be reused across
in-loop and out-of-loop workflows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


REGISTERED_GRAPH_KINDS = frozenset(
    {
        "probability_dag",
        "primitive_capability_graph",
        "constraint_basin_graph",
        "source_claim_graph",
        "code_dependency_graph",
    }
)

DECISION_EFFECTS = frozenset(
    {
        "strategy_change",
        "no_strategy_change",
        "misleading_or_noise",
    }
)

STRATEGY_CHANGE_FIELDS = frozenset(
    {
        "selected_next_discriminator",
        "route_change",
        "briefing_change",
        "projection_change",
    }
)


@dataclass(frozen=True)
class GraphValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def canonical_graph_kind_specs() -> dict[str, dict[str, str]]:
    """Return the initial graph-kind registry used by docs and validators."""
    return {
        "probability_dag": {
            "status": "generic_now",
            "typical_consumer": "autoresearch_loop.compute_dag_steering_context",
        },
        "primitive_capability_graph": {
            "status": "generic_now_curated",
            "typical_consumer": "primitive_tick_surface._load_graph_bonus",
        },
        "constraint_basin_graph": {
            "status": "generic_after_adapter",
            "typical_consumer": "substrate workmap or graph diagnostic pattern",
        },
        "source_claim_graph": {
            "status": "generic_now",
            "typical_consumer": "autoresearch trace or recovery planning",
        },
        "code_dependency_graph": {
            "status": "planned",
            "typical_consumer": "reproduction-cost or setup-risk routing",
        },
    }


def validate_graph_carrier(payload: dict[str, Any]) -> GraphValidationResult:
    """Validate a graph-carrier payload without interpreting graph contents."""
    errors: list[str] = []
    warnings: list[str] = []

    required_strings = (
        "graph_id",
        "graph_kind",
        "producer",
        "consumer",
        "freshness_rule",
        "noise_filter",
    )
    for key in required_strings:
        if not _nonempty_string(payload.get(key)):
            errors.append(f"{key} must be a non-empty string")

    kind = payload.get("graph_kind")
    if _nonempty_string(kind) and kind not in REGISTERED_GRAPH_KINDS:
        if not _nonempty_string(payload.get("new_kind_rationale")):
            errors.append(
                "graph_kind is unregistered; add new_kind_rationale or register the kind"
            )
        else:
            warnings.append(f"unregistered graph_kind accepted with rationale: {kind}")

    _require_nonempty_sequence(payload, "source_artifacts", errors)
    _require_vocabulary(payload, "node_vocabulary", errors)
    _require_vocabulary(payload, "edge_vocabulary", errors)
    _validate_count(payload, "node_count", errors)
    _validate_count(payload, "edge_count", errors)
    _validate_diagnostics(payload, errors, warnings)
    _validate_decision_receipt(payload, errors)

    library_anchor = payload.get("library_anchor")
    literature_anchor = payload.get("literature_anchor")
    if not _nonempty_string(library_anchor):
        warnings.append("library_anchor is missing; prefer naming NetworkX, igraph, or adapter")
    if not _nonempty_string(literature_anchor):
        warnings.append("literature_anchor is missing; cite nearest method family when available")

    if payload.get("non_use") is not None and not _nonempty_string(payload.get("non_use")):
        errors.append("non_use must be a non-empty string when provided")

    return GraphValidationResult(ok=not errors, errors=errors, warnings=warnings)


def validate_graph_carrier_summary(payload: dict[str, Any]) -> GraphValidationResult:
    """Validate the compact graph-carrier view used by trace/action readers.

    Full graph carriers carry producer, consumer, vocabulary, diagnostics, and
    source-method anchors. Trace rows intentionally keep only the fields needed
    by downstream routing. This guard checks that the compact row is still bound
    to graph identity, current source artifacts, counts, a valid decision
    receipt, and a successful producer validation.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for key in ("graph_id", "graph_kind"):
        if not _nonempty_string(payload.get(key)):
            errors.append(f"{key} must be a non-empty string")

    kind = payload.get("graph_kind")
    if _nonempty_string(kind) and kind not in REGISTERED_GRAPH_KINDS:
        errors.append(f"graph_kind is unregistered in compact summary: {kind}")

    _require_nonempty_sequence(payload, "source_artifacts", errors)
    _require_required_count(payload, "node_count", errors)
    _require_required_count(payload, "edge_count", errors)
    _validate_decision_receipt(payload, errors)
    _validate_embedded_validation(payload, errors, warnings)

    return GraphValidationResult(ok=not errors, errors=errors, warnings=warnings)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_nonempty_sequence(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{key} must be a non-empty list")
        return
    if not all(_nonempty_string(item) for item in value):
        errors.append(f"{key} entries must be non-empty strings")


def _require_vocabulary(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    value = payload.get(key)
    if isinstance(value, list) and value and all(_nonempty_string(item) for item in value):
        return
    if isinstance(value, dict) and value and all(_nonempty_string(str(k)) for k in value):
        return
    errors.append(f"{key} must be a non-empty list or dict")


def _validate_count(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    if key not in payload:
        return
    value = payload.get(key)
    if not isinstance(value, int) or value < 0:
        errors.append(f"{key} must be a non-negative integer when provided")


def _require_required_count(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, int) or value < 0:
        errors.append(f"{key} must be a non-negative integer")


def _validate_diagnostics(
    payload: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, list) or not diagnostics:
        errors.append("diagnostics must be a non-empty list")
        return
    for idx, row in enumerate(diagnostics):
        if not isinstance(row, dict):
            errors.append(f"diagnostics[{idx}] must be an object")
            continue
        if not _nonempty_string(row.get("method")):
            errors.append(f"diagnostics[{idx}].method must be a non-empty string")
        if not _nonempty_string(row.get("result_summary")):
            errors.append(f"diagnostics[{idx}].result_summary must be a non-empty string")
        if not _nonempty_string(row.get("baseline")):
            warnings.append(f"diagnostics[{idx}].baseline is missing")


def _validate_decision_receipt(payload: dict[str, Any], errors: list[str]) -> None:
    receipt = payload.get("decision_receipt")
    if not isinstance(receipt, dict):
        errors.append("decision_receipt must be an object")
        return
    effect = receipt.get("effect")
    if effect not in DECISION_EFFECTS:
        errors.append(
            "decision_receipt.effect must be one of "
            + ", ".join(sorted(DECISION_EFFECTS))
        )
        return
    if effect == "strategy_change":
        if not any(_nonempty_string(receipt.get(key)) for key in STRATEGY_CHANGE_FIELDS):
            errors.append(
                "strategy_change receipt must name selected_next_discriminator, "
                "route_change, briefing_change, or projection_change"
            )
    elif not _nonempty_string(receipt.get("reason")):
        errors.append(f"{effect} receipt must include reason")


def _validate_embedded_validation(
    payload: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    validation = payload.get("validation")
    if not isinstance(validation, dict):
        errors.append("validation must be an object")
        return
    if validation.get("ok") is not True:
        errors.append("validation.ok must be true")
    validation_errors = validation.get("errors")
    if validation_errors not in (None, []):
        errors.append("validation.errors must be empty when validation.ok is true")
    validation_warnings = validation.get("warnings")
    if validation_warnings not in (None, []) and not isinstance(validation_warnings, list):
        warnings.append("validation.warnings should be a list when provided")
