"""Structural-transfer adapter for the common kernel action schema."""
from __future__ import annotations

from typing import Any

from src.ztare.common.constraint_isomorphism import (
    ConstraintFingerprint,
    SurfacedIsomorphism,
)
from src.ztare.common.kernel_action_schema import (
    KernelActionSchema,
    render_action_schema_prompt_lines,
)


def action_schema_from_isomorphism(
    iso: SurfacedIsomorphism,
    fingerprint: ConstraintFingerprint | None = None,
    *,
    source_kind: str = "research_isomorphism",
    transfer_mode: str = "deanchor",
) -> dict[str, Any]:
    fp = fingerprint or ConstraintFingerprint(
        constraint_class="unrecorded",
        abstract_form="",
        invariants={},
        forbidden_domain=None,
    )
    return KernelActionSchema(
        record_type="kernel_action_schema",
        source_kind=source_kind,
        action_family="structural_transfer",
        action_name=transfer_mode,
        source_summary=f"{iso.theorem} ({iso.field}): {iso.mechanism}",
        target_mapping=iso.mapping_hint or "unset",
        nearest_confuser=(
            "adjacent semantic analogy from the home field; reject unless the "
            "invariant map, not vocabulary, selects this transfer"
        ),
        falsifier=(
            "the mapped structure fails a target-side check selected before "
            "using the transfer"
        ),
        verification_artifact=(
            "forecast, discriminator, holdout gate, or typed evidence record "
            "that records the target-side check"
        ),
        action_constraints=[
            "do not treat the source field as evidence for the target claim",
            "fill every required action field before using the transfer",
            "reject the nearest confuser before scoring the transfer as useful",
        ],
        evidence_basis="epistemic-generation: action schema beats label-only transfer",
        payload={
            "source_structure": iso.theorem,
            "source_field": iso.field,
            "mechanism": iso.mechanism,
            "invariant_map": dict(iso.invariant_map or {}),
            "fingerprint_constraint_class": fp.constraint_class,
            "fingerprint_invariants": dict(fp.invariants or {}),
        },
    ).to_dict()


def action_schemas_from_legacy_analogy_record(
    record: dict[str, Any],
    *,
    active: bool,
    limit: int = 5,
) -> list[dict[str, Any]]:
    candidates = [
        str(item).strip()
        for item in (record.get("candidate_forms") or [])
        if str(item).strip()
    ][:limit]
    descriptors = [
        str(item).strip()
        for item in (record.get("structural_descriptors") or [])
        if str(item).strip()
    ][:limit]
    if not candidates:
        return []
    mechanism = "; ".join(descriptors) if descriptors else str(record.get("reasoning") or "")
    out: list[dict[str, Any]] = []
    for idx, candidate in enumerate(candidates, start=1):
        out.append(
            KernelActionSchema(
                record_type="kernel_action_schema",
                source_kind="autoresearch_analogy",
                action_family="structural_transfer",
                action_name="active" if active else "observe",
                source_summary=f"{candidate}: {mechanism[:160]}",
                target_mapping="map placeholder variables to substrate features before use",
                nearest_confuser=(
                    "generic curve-fit baseline or same-domain story that matches words "
                    "but not residual structure"
                ),
                falsifier="candidate fails the next deterministic holdout or gate check",
                verification_artifact="fit result, holdout gate result, or eval_history row",
                action_constraints=[
                    "do not import source-domain axioms",
                    "state the target-side mapping before integrating the candidate",
                    "name the nearest generic baseline and why this is not that baseline",
                ],
                evidence_basis=(
                    "epistemic-generation: checked action fields beat analogy labels"
                ),
                payload={
                    "source_structure": candidate,
                    "source_field": "legacy_analogy_candidate",
                    "mechanism": mechanism[:240],
                    "fingerprint_constraint_class": str(
                        record.get("fingerprint", {}).get("shape")
                        if isinstance(record.get("fingerprint"), dict)
                        else ""
                    ),
                    "fingerprint_invariants": {
                        "candidate_index": idx,
                        "structural_descriptors": descriptors,
                    },
                },
            ).to_dict()
        )
    return out


__all__ = [
    "action_schema_from_isomorphism",
    "action_schemas_from_legacy_analogy_record",
    "render_action_schema_prompt_lines",
]
