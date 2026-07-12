"""LeanMill binding for exact or sampled evidence-by-hypothesis contexts."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.finite_incidence_context import FiniteIncidenceContext
from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.finite_theory_context import SemanticTheoryNode
from ztare.leanmill.theory_ir import TheorySignature, content_hash


EVIDENCE_CONTEXT_SCHEMA = "leanmill.evidence_theory_context.v1"


@dataclass(frozen=True)
class EvidenceObjectRecord:
    model_id: str
    stratum_id: str
    payload: Mapping[str, Any]
    schema: str = "leanmill.evidence_object_record.v1"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "object_id": self.model_id,
            "stratum_id": self.stratum_id,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class EvidenceHypothesisProfile:
    formula_id: str
    truth_bits: int
    anonymous_shape: Mapping[str, Any]
    payload: Mapping[str, Any]
    schema: str = "leanmill.evidence_hypothesis_profile.v1"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "hypothesis_id": self.formula_id,
            "truth_bits_hex": hex(self.truth_bits),
            "anonymous_shape": dict(self.anonymous_shape),
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class EvidenceTheoryContext:
    signature: TheorySignature
    adapter_id: str
    incidence: FiniteIncidenceContext
    formula_profiles: tuple[EvidenceHypothesisProfile, ...]
    object_records: tuple[EvidenceObjectRecord, ...]
    completeness_receipt_digest: str
    base_axioms: tuple[Any, ...] = ()
    schema: str = EVIDENCE_CONTEXT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != EVIDENCE_CONTEXT_SCHEMA:
            raise ValueError("unsupported evidence context schema")
        if tuple(row.formula_id for row in self.formula_profiles) != self.incidence.attribute_ids:
            raise ValueError("evidence hypothesis order differs from incidence context")
        if tuple(row.model_id for row in self.object_records) != self.incidence.object_ids:
            raise ValueError("evidence object order differs from incidence context")
        for profile, incidence_profile in zip(
            self.formula_profiles, self.incidence.profiles, strict=True
        ):
            if profile.truth_bits != incidence_profile.truth_bits:
                raise ValueError("evidence truth profile differs from incidence context")
        if self.incidence.exact and self.completeness_receipt_digest != self.incidence.completeness_ref:
            raise ValueError("exact evidence context completeness receipt mismatch")

    @property
    def context_hash(self) -> str:
        return content_hash(
            {
                "schema": self.schema,
                "signature_hash": self.signature.content_hash,
                "adapter_id": self.adapter_id,
                "incidence_context_hash": self.incidence.context_hash,
                "completeness_receipt_digest": self.completeness_receipt_digest,
                "hypothesis_ids": list(self.formula_ids),
                "object_ids": list(self.object_ids),
            }
        )

    @property
    def formula_ids(self) -> tuple[str, ...]:
        return tuple(row.formula_id for row in self.formula_profiles)

    @property
    def object_ids(self) -> tuple[str, ...]:
        return tuple(row.model_id for row in self.object_records)

    @property
    def complete(self) -> bool:
        return self.incidence.exact

    @property
    def object_identity_policy(self) -> str:
        return "declared_evidence_object_identity.v1"

    @property
    def object_contrast_admissible(self) -> bool:
        return True

    def anonymous_formula_profile(self, formula_id: str) -> dict[str, Any]:
        profile = next(
            (row for row in self.formula_profiles if row.formula_id == formula_id),
            None,
        )
        if profile is None:
            raise ValueError("unknown hypothesis ID in evidence context")
        return {
            "formula_id": formula_id,
            "truth_count": profile.truth_bits.bit_count(),
            "formula": dict(profile.anonymous_shape),
        }

    def anonymous_object_profile(self, object_id: str) -> dict[str, Any]:
        try:
            record = self._objects()[object_id]
        except KeyError as exc:
            raise ValueError("unknown evidence object in frozen context") from exc
        return {
            "object_id": record.model_id,
            "stratum_id": record.stratum_id,
            "object_kind": "evidence_record",
            "payload": dict(record.payload),
        }

    def _objects(self) -> dict[str, EvidenceObjectRecord]:
        return {row.model_id: row for row in self.object_records}

    def extent_model_ids(self, formula_ids: Iterable[str]) -> tuple[str, ...]:
        return self.incidence.extent_object_ids(formula_ids)

    def closure_ids(self, formula_ids: Iterable[str]) -> tuple[str, ...]:
        return self.incidence.closure_ids(formula_ids)

    def semantic_formula_classes(self) -> tuple[tuple[str, ...], ...]:
        return self.incidence.semantic_attribute_classes()

    def synergy_ids(self, presentation: Sequence[str]) -> tuple[str, ...]:
        return self.incidence.synergy_ids(presentation)

    def cheap_structural_baseline(
        self,
        presentation: Sequence[str],
        candidate_formula_ids: Sequence[str],
    ) -> Mapping[str, Any] | None:
        """Evidence adapters may supply their own typed shortcut baseline later."""

        del presentation, candidate_formula_ids
        return None

    def independence_witness(
        self,
        presentation: Sequence[str],
        target_formula_id: str,
    ) -> EvidenceObjectRecord | None:
        object_id = self.incidence.independence_object_id(
            presentation, target_formula_id
        )
        return self._objects().get(object_id) if object_id else None

    def separation_witness(
        self,
        left_formula_ids: Iterable[str],
        right_formula_ids: Iterable[str],
    ) -> EvidenceObjectRecord | None:
        object_id = self.incidence.separation_object_id(
            left_formula_ids, right_formula_ids
        )
        return self._objects().get(object_id) if object_id else None

    def generated_theory_nodes(
        self,
        *,
        max_presentation_size: int,
        semantic_quotient: bool = False,
    ) -> tuple[SemanticTheoryNode, ...]:
        return tuple(
            SemanticTheoryNode.from_concept(
                row,
                formal_context_hash=self.context_hash,
            )
            for row in self.incidence.generated_concepts(
                max_presentation_size=max_presentation_size,
                semantic_quotient=semantic_quotient,
            )
        )

    def to_json(self) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "context_hash": self.context_hash,
            "signature": self.signature.to_json(),
            "adapter_id": self.adapter_id,
            "incidence": self.incidence.to_json(),
            "formula_profiles": [row.to_json() for row in self.formula_profiles],
            "object_records": [row.to_json() for row in self.object_records],
            "completeness_receipt_digest": self.completeness_receipt_digest,
        }
        return {**core, "snapshot_sha256": content_hash(core)}


def save_evidence_theory_context(
    context: EvidenceTheoryContext,
    path: str | Path,
) -> Path:
    return write_json_atomic(path, context.to_json())


def load_evidence_theory_context(path: str | Path) -> EvidenceTheoryContext:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping) or raw.get("schema") != EVIDENCE_CONTEXT_SCHEMA:
        raise ValueError("unsupported evidence theory snapshot")
    unsigned = dict(raw)
    supplied_snapshot = unsigned.pop("snapshot_sha256", None)
    if supplied_snapshot != content_hash(unsigned):
        raise ValueError("evidence theory snapshot digest mismatch")
    incidence_row = raw["incidence"]
    profiles = tuple(
        EvidenceHypothesisProfile(
            formula_id=str(row["hypothesis_id"]),
            truth_bits=int(str(row["truth_bits_hex"]), 16),
            anonymous_shape=dict(row["anonymous_shape"]),
            payload=dict(row["payload"]),
            schema=str(row["schema"]),
        )
        for row in raw["formula_profiles"]
    )
    incidence = FiniteIncidenceContext.from_json(incidence_row)
    context = EvidenceTheoryContext(
        signature=TheorySignature.from_json(raw["signature"]),
        adapter_id=str(raw["adapter_id"]),
        incidence=incidence,
        formula_profiles=profiles,
        object_records=tuple(
            EvidenceObjectRecord(
                model_id=str(row["object_id"]),
                stratum_id=str(row["stratum_id"]),
                payload=dict(row["payload"]),
                schema=str(row["schema"]),
            )
            for row in raw["object_records"]
        ),
        completeness_receipt_digest=str(raw["completeness_receipt_digest"]),
    )
    if context.context_hash != raw.get("context_hash"):
        raise ValueError("evidence theory context hash mismatch")
    return context


__all__ = [
    "EVIDENCE_CONTEXT_SCHEMA", "EvidenceHypothesisProfile",
    "EvidenceObjectRecord", "EvidenceTheoryContext",
    "load_evidence_theory_context", "save_evidence_theory_context",
]
