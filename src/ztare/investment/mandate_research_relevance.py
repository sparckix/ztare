"""Bind research subjects to the household decisions they could implement."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .contracts import require_finite, require_text
from .household_mandate_frontier import HOUSEHOLD_MANDATE_FRONTIER_SCHEMA
from .sleeve_implementation import SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA


MANDATE_RESEARCH_RELEVANCE_SCHEMA = "jaggedthoughts-mandate-research-relevance-v1"


def _sealed(
    raw: Mapping[str, Any], *, schema: str, digest_field: str, label: str,
) -> dict[str, Any]:
    body = dict(raw)
    digest = str(body.pop(digest_field, ""))
    if body.get("schema") != schema or len(digest) != 64 or stable_sha256(body) != digest:
        raise ValueError(f"invalid {label} identity")
    return {**body, digest_field: digest}


def _decision_classes(frontier: Mapping[str, Any]) -> tuple[list[dict[str, Any]], set[str]]:
    classes = [dict(row) for row in frontier.get("decision_classes") or ()]
    if len(classes) != int(frontier.get("decision_class_count") or 0) or not classes:
        raise ValueError("mandate frontier decision-class count mismatch")
    sleeve_ids: set[str] | None = None
    seen: set[str] = set()
    for row in classes:
        decision_id = require_text(row.get("decision_id"), "mandate decision_id")
        weights = {
            str(key): require_finite(value, f"{decision_id}.{key}")
            for key, value in (row.get("selected_sleeve_weights") or {}).items()
        }
        if decision_id in seen or decision_id != stable_sha256({"selected_sleeve_weights": weights}):
            raise ValueError("mandate decision identity mismatch")
        if any(value < 0 or value > 1 for value in weights.values()):
            raise ValueError("mandate sleeve weights must be in [0, 1]")
        if sleeve_ids is not None and set(weights) != sleeve_ids:
            raise ValueError("mandate decisions must share one sleeve universe")
        sleeve_ids, row["selected_sleeve_weights"] = set(weights), weights
        seen.add(decision_id)
    return classes, sleeve_ids or set()


def _subject_sleeves(
    implementation: Mapping[str, Any], sleeve_ids: set[str],
) -> dict[str, str]:
    bound: dict[str, str] = {}
    seen_sleeves: set[str] = set()
    for sleeve in implementation.get("sleeves") or ():
        sleeve_id = require_text(sleeve.get("sleeve_id"), "implementation sleeve_id")
        if sleeve_id not in sleeve_ids:
            raise ValueError("implementation and mandate sleeve universes differ")
        seen_sleeves.add(sleeve_id)
        for instrument in sleeve.get("eligible_instruments") or ():
            identity = instrument.get("identity") if isinstance(instrument, Mapping) else {}
            entity = str((identity or {}).get("subject_id") or "").upper()
            if not entity or instrument.get("research_eligible") is not True:
                continue
            if entity in bound and bound[entity] != sleeve_id:
                raise ValueError(f"research subject {entity} is bound to multiple sleeves")
            bound[entity] = sleeve_id
    if seen_sleeves != sleeve_ids:
        raise ValueError("implementation and mandate sleeve universes differ")
    return bound


def compile_mandate_research_relevance(
    jobs: Sequence[Mapping[str, Any]], *,
    household_mandate_frontier: Mapping[str, Any],
    sleeve_implementation_frontier: Mapping[str, Any],
) -> dict[str, Any]:
    """Annotate already-admissible jobs without changing their eligibility or order."""
    mandate = _sealed(
        household_mandate_frontier, schema=HOUSEHOLD_MANDATE_FRONTIER_SCHEMA,
        digest_field="mandate_frontier_sha256", label="household mandate frontier",
    )
    implementation = _sealed(
        sleeve_implementation_frontier, schema=SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA,
        digest_field="sleeve_implementation_sha256", label="sleeve implementation frontier",
    )
    if mandate.get("basis_sha256") != implementation.get("basis_sha256"):
        raise ValueError("mandate and implementation basis identities differ")
    classes, sleeve_ids = _decision_classes(mandate)
    bound = _subject_sleeves(implementation, sleeve_ids)

    rows = []
    for raw in sorted(jobs, key=lambda row: str(row.get("work_id") or "")):
        work_id = require_text(raw.get("work_id"), "research work_id")
        if raw.get("status") != "queued":
            raise ValueError("mandate relevance accepts already-admissible queued jobs only")
        payload = raw.get("payload") if isinstance(raw.get("payload"), Mapping) else {}
        entity = str(payload.get("entity_id") or "").upper()
        sleeve_id = bound.get(entity)
        declared_sleeve = str(payload.get("implementation_sleeve_id") or "") or None
        if declared_sleeve and sleeve_id and declared_sleeve != sleeve_id:
            raise ValueError(f"research job {work_id} crossed its implementation sleeve identity")
        if sleeve_id:
            covered = [
                str(row["decision_id"]) for row in classes
                if row["selected_sleeve_weights"][sleeve_id] > 0
            ]
            maximum_weight = max(
                row["selected_sleeve_weights"][sleeve_id] for row in classes
            )
            status = "bound_active" if covered else "bound_inactive"
        else:
            covered, maximum_weight = [], None
            status = "entity_identity_absent" if not entity else "sleeve_identity_unbound"
        body = {
            "schema": MANDATE_RESEARCH_RELEVANCE_SCHEMA,
            "work_id": work_id,
            "entity_id": entity or None,
            "binding_status": status,
            "implementation_sleeve_id": sleeve_id,
            "covered_mandate_decision_ids": sorted(covered),
            "covered_decision_class_count": len(covered),
            "total_decision_class_count": len(classes),
            "decision_class_coverage_fraction": round(len(covered) / len(classes), 8),
            "maximum_planning_weight_upper_bound": (
                round(maximum_weight, 8) if maximum_weight is not None else None
            ),
            "scoreable": maximum_weight is not None,
            "mandate_frontier_sha256": household_mandate_frontier["mandate_frontier_sha256"],
            "sleeve_implementation_sha256": sleeve_implementation_frontier[
                "sleeve_implementation_sha256"
            ],
            "meaning": (
                "Maximum declared planning weight in the subject's evidence-bound sleeve; "
                "an upper bound on implementation relevance, not expected alpha or probability."
            ),
            "authority": "research_priority_annotation_only",
            "queue_mutation_authority": False,
            "capital_authority": False,
        }
        rows.append({**body, "relevance_sha256": stable_sha256(body)})
    body = {
        "schema": "jaggedthoughts-mandate-research-relevance-batch-v1",
        "mandate_frontier_sha256": household_mandate_frontier["mandate_frontier_sha256"],
        "sleeve_implementation_sha256": sleeve_implementation_frontier[
            "sleeve_implementation_sha256"
        ],
        "rows": rows,
        "bound_job_count": sum(row["scoreable"] for row in rows),
        "unbound_job_count": sum(not row["scoreable"] for row in rows),
        "queue_mutation_authority": False,
        "capital_authority": False,
    }
    return {**body, "batch_sha256": stable_sha256(body)}


__all__ = [
    "MANDATE_RESEARCH_RELEVANCE_SCHEMA", "compile_mandate_research_relevance",
]
