"""Data-only alpha/gamma materializations for finite language successors.

A staged producer materializes alpha(source), gamma(alpha(source)), and
abstract/generated pairs.  The host checks those bytes and persists a reviewed
snapshot; it never imports campaign-generated Python.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ztare.common.artifact_refs import canonical_sha256_ref
from ztare.leanmill.finite_model import (
    FiniteModel,
    canonicalize_finite_model,
    evaluate_axiom,
    validate_model,
)
from ztare.leanmill.finite_table_model_finder import FiniteModelSearchReceipt
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    content_hash,
    validate_axiom,
    validate_axioms,
)

CANDIDATE_SCHEMA = "leanmill.materialized_generative_representation.v1"
REVIEWED_SCHEMA = "leanmill.reviewed_generative_representation.v1"
APPLICATION_SCHEMA = "leanmill.generative_functor_application.v1"
ISOMORPHISM_POLICY = "sortwise_isomorphism.v1"


def _unsigned(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "receipt_sha256"}


def _signed(core: Mapping[str, Any]) -> dict[str, Any]:
    return {**core, "receipt_sha256": content_hash(core)}


def _sizes(value: Mapping[str, int]) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, Mapping) or not value or any(
        not isinstance(name, str) or type(size) is not int or size < 1
        for name, size in value.items()
    ):
        raise ValueError("representation strata require positive named sort sizes")
    return tuple(sorted(value.items()))


def _candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(value)
    core = _unsigned(row)
    required = {
        "schema", "request_id", "gap_id", "context_hash", "codec_id",
        "raw_signature", "abstract_signature", "raw_base_axioms",
        "source_alpha_models", "source_lowered_models", "generated_batches",
        "generator_provenance_refs", "max_relabelings", "isomorphism_policy",
    }
    if (
        row.get("schema") != CANDIDATE_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or set(core) != required
        or core.get("isomorphism_policy") != ISOMORPHISM_POLICY
        or not all(str(core.get(key) or "") for key in ("request_id", "gap_id", "context_hash", "codec_id"))
        or not tuple(core.get("generator_provenance_refs") or ())
        or not all(
            str(ref) for ref in core.get("generator_provenance_refs") or ()
        )
        or not isinstance(core.get("generated_batches"), list)
        or not core["generated_batches"]
        or type(core.get("max_relabelings")) is not int
        or core["max_relabelings"] < 1
    ):
        raise ValueError("materialized generative representation identity changed")
    return row


def _replay_candidate(
    value: Mapping[str, Any], source_context: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = _candidate(value)
    raw = TheorySignature.from_json(candidate["raw_signature"])
    abstract = TheorySignature.from_json(candidate["abstract_signature"])
    base = tuple(AxiomFormula.from_json(row) for row in candidate["raw_base_axioms"])
    validate_axioms(raw, base)
    if (
        candidate["context_hash"] != source_context.context_hash
        or raw.content_hash != source_context.signature.content_hash
        or {row.semantic_hash for row in base}
        != {row.semantic_hash for row in source_context.base_axioms}
    ):
        raise ValueError("representation crossed its frozen raw theory")
    source = {row.model_id: row.model for row in source_context.universe.models}
    alpha, lowered = candidate["source_alpha_models"], candidate["source_lowered_models"]
    if (
        not isinstance(alpha, Mapping)
        or not isinstance(lowered, Mapping)
        or set(alpha) != set(source)
        or set(lowered) != set(source)
    ):
        raise ValueError("representation source coverage is not exact")
    cap = int(candidate["max_relabelings"])
    for model_id, original in source.items():
        a, r = FiniteModel.from_json(alpha[model_id]), FiniteModel.from_json(lowered[model_id])
        validate_model(abstract, a)
        validate_model(raw, r)
        if canonicalize_finite_model(raw, original, max_relabelings=cap) != canonicalize_finite_model(
            raw, r, max_relabelings=cap
        ):
            raise ValueError("raw-alpha-gamma roundtrip failed up to isomorphism")
        if not all(evaluate_axiom(raw, law, r) for law in base):
            raise ValueError("source gamma image violates a raw base law")
    seen_strata: set[tuple[tuple[str, int], ...]] = set()
    for batch in candidate["generated_batches"]:
        if not isinstance(batch, Mapping) or set(batch) != {
            "raw_sort_sizes", "abstract_sort_sizes", "models", "generator_ref"
        }:
            raise ValueError("generated representation batch fields changed")
        raw_sizes, abstract_sizes = _sizes(batch["raw_sort_sizes"]), _sizes(batch["abstract_sort_sizes"])
        if (
            abstract_sizes in seen_strata
            or not str(batch.get("generator_ref") or "")
            or not isinstance(batch.get("models"), list)
            or not batch["models"]
        ):
            raise ValueError("generated representation stratum is ambiguous")
        seen_strata.add(abstract_sizes)
        seen_models: set[str] = set()
        for pair in batch["models"]:
            if not isinstance(pair, Mapping) or set(pair) != {"abstract_model", "raw_model"}:
                raise ValueError("generated representation pair fields changed")
            a, r = FiniteModel.from_json(pair["abstract_model"]), FiniteModel.from_json(pair["raw_model"])
            if a.sort_sizes != abstract_sizes or r.sort_sizes != raw_sizes:
                raise ValueError("generated representation crossed strata")
            validate_model(abstract, a)
            validate_model(raw, r)
            canonical = canonicalize_finite_model(abstract, a, max_relabelings=cap)
            if canonical != a or content_hash(a.to_json()) in seen_models:
                raise ValueError("generated abstract models must be unique canonical classes")
            seen_models.add(content_hash(a.to_json()))
            if not all(evaluate_axiom(raw, law, r) for law in base):
                raise ValueError("generated gamma image violates a raw base law")
    host = _signed({
        "schema": "leanmill.generative_representation_conformance.v1",
        "ok": True,
        "interface": CANDIDATE_SCHEMA,
        "candidate_receipt_sha256": candidate["receipt_sha256"],
        "request_id": candidate["request_id"], "gap_id": candidate["gap_id"],
        "context_hash": candidate["context_hash"], "codec_id": candidate["codec_id"],
        "source_object_count": len(source),
        "generated_strata": [
            {"raw_sort_sizes": dict(row["raw_sort_sizes"]), "abstract_sort_sizes": dict(row["abstract_sort_sizes"])}
            for row in candidate["generated_batches"]
        ],
        "source_roundtrip_up_to_isomorphism": True, "raw_law_replay": True,
        "execution_boundary": "materialized_data_only_no_generated_code_import",
    })
    return candidate, host


def validate_materialized_generative_candidate(
    value: Mapping[str, Any], source_context: Any
) -> dict[str, Any]:
    """Return the exact host receipt for one data-only candidate."""
    return _replay_candidate(value, source_context)[1]


@dataclass(frozen=True)
class ReviewedGenerativeRepresentation:
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        row, core = dict(self.payload), _unsigned(self.payload)
        if (
            row.get("schema") != REVIEWED_SCHEMA
            or row.get("receipt_sha256") != content_hash(core)
            or set(core) != {"schema", "candidate", "host_conformance", "independent_review", "claim_boundary"}
        ):
            raise ValueError("reviewed generative representation does not replay")
        candidate = _candidate(core["candidate"])
        host, review = core["host_conformance"], core["independent_review"]
        host_ref = canonical_sha256_ref(
            host.get("receipt_sha256") if isinstance(host, Mapping) else None
        )
        review_refs = {
            canonical_sha256_ref(ref) for ref in review.get("evidence_refs") or ()
        } if isinstance(review, Mapping) else set()
        if (
            not isinstance(host, Mapping) or host.get("receipt_sha256") != content_hash(_unsigned(host))
            or host.get("schema") != "leanmill.generative_representation_conformance.v1"
            or host.get("ok") is not True or host.get("interface") != CANDIDATE_SCHEMA
            or host.get("candidate_receipt_sha256") != candidate["receipt_sha256"]
            or not isinstance(review, Mapping) or review.get("accepted") is not True
            or not str(review.get("reviewer_ref") or "")
            or host_ref not in review_refs
        ):
            raise ValueError("representation review is not host-bound")

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "ReviewedGenerativeRepresentation":
        return cls(dict(value))

    def to_json(self) -> dict[str, Any]:
        return dict(self.payload)

    @property
    def candidate(self) -> Mapping[str, Any]:
        return self.payload["candidate"]

    @property
    def source_context_hash(self) -> str:
        return str(self.candidate["context_hash"])

    @property
    def raw_signature(self) -> TheorySignature:
        return TheorySignature.from_json(self.candidate["raw_signature"])

    @property
    def abstract_signature(self) -> TheorySignature:
        return TheorySignature.from_json(self.candidate["abstract_signature"])

    @property
    def generated_batches(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self.candidate["generated_batches"])

    @property
    def receipt_sha256(self) -> str:
        return str(self.payload["receipt_sha256"])

    @property
    def source_application(self) -> Mapping[str, Any]:
        return _signed({
            "schema": "leanmill.finite_model_functor_application.v1",
            "gap_id": self.candidate["gap_id"], "context_hash": self.source_context_hash,
            "functor_id": self.candidate["codec_id"],
            "signature": self.candidate["abstract_signature"],
            "models": self.candidate["source_alpha_models"],
        })

    @property
    def query_strata(self) -> tuple[Mapping[str, Any], ...]:
        return tuple({"sort_sizes": dict(row["abstract_sort_sizes"])} for row in self.generated_batches)

    def validate_source_roundtrip(self, source_context: Any) -> None:
        _candidate_row, expected = _replay_candidate(self.candidate, source_context)
        if dict(self.payload["host_conformance"]) != expected:
            raise ValueError("representation host conformance changed after review")


def admit_materialized_generative_representation(
    value: Mapping[str, Any],
    *,
    source_context: Any,
    host_conformance: Mapping[str, Any],
    independent_review: Mapping[str, Any],
) -> tuple[ReviewedGenerativeRepresentation, dict[str, Any]]:
    """Bind a host-replayed candidate to the independent Forge review."""
    candidate, expected = _replay_candidate(value, source_context)
    if dict(host_conformance) != expected:
        raise ValueError("generative candidate host receipt changed before admission")
    reviewed = ReviewedGenerativeRepresentation.from_json(_signed({
        "schema": REVIEWED_SCHEMA, "candidate": candidate,
        "host_conformance": expected, "independent_review": dict(independent_review),
        "claim_boundary": "reviewed materialized fixed strata; generator completeness remains a proof obligation",
    }))
    reviewed.validate_source_roundtrip(source_context)
    application = _signed({
        "schema": APPLICATION_SCHEMA,
        "source_application": dict(reviewed.source_application),
        "representation": reviewed.to_json(),
    })
    return reviewed, application


def unpack_generative_application(
    application: Mapping[str, Any], source_context: Any
) -> tuple[dict[str, Any], ReviewedGenerativeRepresentation | None]:
    if application.get("schema") != APPLICATION_SCHEMA:
        return dict(application), None
    core = _unsigned(application)
    if application.get("receipt_sha256") != content_hash(core) or set(core) != {
        "schema", "source_application", "representation"
    }:
        raise ValueError("generative functor application does not replay")
    reviewed = ReviewedGenerativeRepresentation.from_json(application["representation"])
    reviewed.validate_source_roundtrip(source_context)
    source = dict(application["source_application"])
    if source != dict(reviewed.source_application):
        raise ValueError("generative application changed its alpha image")
    return source, reviewed


def build_generative_countermodel_finder(reviewed: ReviewedGenerativeRepresentation):
    signature = reviewed.abstract_signature
    batches = {_sizes(row["abstract_sort_sizes"]): row for row in reviewed.generated_batches}

    def find(
        premises: Sequence[AxiomFormula], target: AxiomFormula, *,
        sort_sizes: Mapping[str, int] | None = None, carrier_size: int | None = None,
        base_axioms: Sequence[AxiomFormula] = (), timeout_ms: int = 30_000,
    ) -> FiniteModelSearchReceipt:
        if sort_sizes is None:
            if carrier_size is None or len(signature.sorts) != 1:
                raise ValueError("representation search requires a complete size vector")
            sort_sizes = {signature.sorts[0].name: carrier_size}
        query, premises, base_axioms = _sizes(sort_sizes), tuple(premises), tuple(base_axioms)
        if set(dict(query)) != set(signature.sort_map) or type(timeout_ms) is not int or timeout_ms < 1:
            raise ValueError("invalid representation search boundary")
        for law in (*base_axioms, *premises, target):
            validate_axiom(signature, law)
        common = {
            "signature_hash": signature.content_hash, "sort_sizes": query,
            "base_formula_ids": tuple("formula:" + row.semantic_hash for row in base_axioms),
            "premise_formula_ids": tuple("formula:" + row.semantic_hash for row in premises),
            "target_formula_id": "formula:" + target.semantic_hash,
            "solver": "reviewed_generative_representation:" + reviewed.receipt_sha256,
            "timeout_ms": timeout_ms,
        }
        batch = batches.get(query)
        if batch is None:
            return FiniteModelSearchReceipt(status="unknown", reason="no reviewed generation for this stratum", **common)
        premise_models = []
        for pair in batch["models"]:
            model = FiniteModel.from_json(pair["abstract_model"])
            if all(evaluate_axiom(signature, law, model) for law in (*base_axioms, *premises)):
                premise_models.append(model)
                if not evaluate_axiom(signature, target, model):
                    return FiniteModelSearchReceipt(status="countermodel_found", witness=model, **common)
        return FiniteModelSearchReceipt(
            status="unknown",
            reason=(
                "reviewed batch contains no countermodel; generator exhaustiveness "
                "is not host-certified"
                if premise_models
                else "reviewed batch contains no premise model"
            ),
            **common,
        )

    return find


__all__ = [
    "APPLICATION_SCHEMA", "CANDIDATE_SCHEMA", "ISOMORPHISM_POLICY",
    "ReviewedGenerativeRepresentation", "admit_materialized_generative_representation",
    "build_generative_countermodel_finder", "unpack_generative_application",
    "validate_materialized_generative_candidate",
]
