"""Generic exact observation-by-hypothesis adapter for evidence-induced campaigns."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ztare.common.finite_incidence_context import build_incidence_context
from ztare.leanmill.evidence_theory_context import (
    EvidenceHypothesisProfile,
    EvidenceObjectRecord,
    EvidenceTheoryContext,
)
from ztare.leanmill.theory_ir import TheorySignature, content_hash


ADAPTER_ID = "generic_finite_evidence.v1"


def _normalized(config: Mapping[str, Any]):
    objects = tuple(sorted(
        (
            str(row["object_id"]),
            str(row.get("stratum_id") or "declared_observation"),
            dict(row.get("payload") or {}),
        )
        for row in config.get("objects") or ()
    ))
    object_ids = tuple(row[0] for row in objects)
    if not objects or len(set(object_ids)) != len(objects):
        raise ValueError("generic evidence adapter requires unique finite objects")
    hypotheses = tuple(sorted(
        (
            str(row["hypothesis_id"]),
            tuple(sorted(str(item) for item in row.get("satisfied_object_ids") or ())),
            dict(row.get("anonymous_shape") or {}),
            dict(row.get("payload") or {}),
        )
        for row in config.get("hypotheses") or ()
    ))
    if not hypotheses or len({row[0] for row in hypotheses}) != len(hypotheses):
        raise ValueError("generic evidence adapter requires unique executable hypotheses")
    allowed = set(object_ids)
    if any(set(row[1]) - allowed for row in hypotheses):
        raise ValueError("hypothesis satisfaction references an unknown object")
    return objects, hypotheses


def preflight_blueprint(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    formula_grammar: Mapping[str, Any],
    strata: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    del formula_grammar
    del strata
    objects, hypotheses = _normalized(adapter_config)
    if not signature.sorts:
        raise ValueError("generic evidence campaign requires a typed observation sort")
    completeness_ref = str(adapter_config.get("completeness_ref") or "")
    if not completeness_ref:
        raise ValueError("exact generic evidence campaigns require a completeness_ref")
    return {
        "formula_count": len(hypotheses),
        "labeled_model_count": len(objects),
        "truth_cell_count": len(objects) * len(hypotheses),
        "complete_census_available": True,
        "context_kind": "evidence_incidence",
        "completeness_ref": completeness_ref,
    }


def build_evidence_context(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    strata: Sequence[Mapping[str, Any]],
) -> EvidenceTheoryContext:
    del strata
    objects, hypotheses = _normalized(adapter_config)
    positions = {row[0]: index for index, row in enumerate(objects)}
    truth: dict[str, int] = {}
    for hypothesis_id, satisfied, _shape, _payload in hypotheses:
        bits = 0
        for object_id in satisfied:
            bits |= 1 << positions[object_id]
        truth[hypothesis_id] = bits
    completeness_ref = str(adapter_config.get("completeness_ref") or "")
    incidence = build_incidence_context(
        object_ids=tuple(row[0] for row in objects),
        attribute_truth_bits=truth,
        exact=True,
        completeness_ref=completeness_ref,
        provenance_refs={
            row[0]: "hypothesis:" + content_hash(row[3]) for row in hypotheses
        },
    )
    hypothesis_map = {row[0]: row for row in hypotheses}
    return EvidenceTheoryContext(
        signature=signature,
        adapter_id=ADAPTER_ID,
        incidence=incidence,
        formula_profiles=tuple(
            EvidenceHypothesisProfile(
                formula_id=profile.attribute_id,
                truth_bits=profile.truth_bits,
                anonymous_shape=hypothesis_map[profile.attribute_id][2],
                payload=hypothesis_map[profile.attribute_id][3],
            )
            for profile in incidence.profiles
        ),
        object_records=tuple(
            EvidenceObjectRecord(model_id=row[0], stratum_id=row[1], payload=row[2])
            for row in objects
        ),
        completeness_receipt_digest=completeness_ref,
    )


__all__ = ["ADAPTER_ID", "build_evidence_context", "preflight_blueprint"]
