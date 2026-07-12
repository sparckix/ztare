"""Complete finite-model adapter for typed first-order signatures."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from math import factorial, prod
from typing import Any, Mapping, Sequence

from ztare.leanmill.finite_model import (
    FiniteModel,
    canonicalize_finite_model,
    evaluate_formula,
    finite_interpretation_count,
    iter_finite_models,
)
from ztare.leanmill.finite_table_model_finder import (
    enumerate_finite_models_smt,
    find_finite_countermodel,
)
from ztare.leanmill.equational_formula_universe import (
    EQUATIONAL_GRAMMAR_SCHEMA,
    enumerate_universal_equations,
    equational_formula_universe_receipt,
)
from ztare.leanmill.theory_ir import AxiomFormula, TheorySignature, content_hash, validate_axioms
from ztare.leanmill.finite_model_universe import finite_model_record_weight


ADAPTER_ID = "generic_fol_finite.v1"
_EXHAUSTIVE_TABLES = "exhaustive_tables"
_SMT_EXACT = "smt_exact"


def _model_generation_config(adapter_config: Mapping[str, Any]) -> dict[str, Any]:
    raw = adapter_config.get("model_generation")
    if raw is None:
        return {"mode": _EXHAUSTIVE_TABLES}
    if not isinstance(raw, Mapping):
        raise ValueError("model_generation must be an object")
    unknown = set(raw) - {
        "mode",
        "max_canonical_models_per_stratum",
        "timeout_ms_per_stratum",
    }
    if unknown:
        raise ValueError(f"model_generation has unknown fields: {sorted(unknown)}")
    mode = str(raw.get("mode") or "")
    if mode not in {_EXHAUSTIVE_TABLES, _SMT_EXACT}:
        raise ValueError("model_generation.mode must be exhaustive_tables or smt_exact")
    if mode == _EXHAUSTIVE_TABLES:
        if set(raw) - {"mode"}:
            raise ValueError("exhaustive_tables does not accept SMT bounds")
        return {"mode": mode}
    model_cap = raw.get("max_canonical_models_per_stratum", 5_000)
    timeout_ms = raw.get("timeout_ms_per_stratum", 300_000)
    if type(model_cap) is not int or model_cap < 1:
        raise ValueError("max_canonical_models_per_stratum must be positive")
    if type(timeout_ms) is not int or timeout_ms < 1:
        raise ValueError("timeout_ms_per_stratum must be positive")
    return {
        "mode": mode,
        "max_canonical_models_per_stratum": model_cap,
        "timeout_ms_per_stratum": timeout_ms,
    }


def _validate_adapter_config(adapter_config: Mapping[str, Any]) -> None:
    unknown = set(adapter_config) - {
        "formula_universe",
        "isomorphism_quotient",
        "max_relabelings_per_model",
        "model_generation",
        "functor_image",
    }
    if unknown:
        raise ValueError(
            f"generic finite adapter has unknown configuration: {sorted(unknown)}"
        )
    quotient = adapter_config.get("isomorphism_quotient", True)
    cap = adapter_config.get("max_relabelings_per_model", 720)
    if type(quotient) is not bool:
        raise ValueError("isomorphism_quotient must be boolean")
    if type(cap) is not int or cap < 1:
        raise ValueError("max_relabelings_per_model must be a positive integer")
    _model_generation_config(adapter_config)
    image = adapter_config.get("functor_image")
    if image is not None:
        required = {
            "receipt_sha256", "source_context_hash", "source_object_count",
            "canonical_model_count",
        }
        if not isinstance(image, Mapping) or set(image) != required:
            raise ValueError("functor_image must carry its exact provenance summary")
        if any(
            not str(image[key])
            for key in ("receipt_sha256", "source_context_hash")
        ):
            raise ValueError("functor_image provenance cannot be empty")
        if any(
            type(image[key]) is not int or image[key] < 1
            for key in ("source_object_count", "canonical_model_count")
        ):
            raise ValueError("functor_image counts must be positive integers")


def _quotient_config(adapter_config: Mapping[str, Any]) -> tuple[bool, int]:
    _validate_adapter_config(adapter_config)
    return (
        bool(adapter_config.get("isomorphism_quotient", True)),
        int(adapter_config.get("max_relabelings_per_model", 720)),
    )


def build_fixed_size_countermodel_finder(
    *, signature: TheorySignature, adapter_config: Mapping[str, Any]
):
    _validate_adapter_config(adapter_config)
    return partial(find_finite_countermodel, signature)


def build_formulas(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    formula_grammar: Mapping[str, Any],
) -> tuple[AxiomFormula, ...]:
    _validate_adapter_config(adapter_config)
    rows = adapter_config.get("formula_universe")
    if rows is not None:
        if not isinstance(rows, list) or not rows:
            raise ValueError("typed formula_universe must be a nonempty list")
        formulas = tuple(AxiomFormula.from_json(row) for row in rows)
    elif formula_grammar.get("schema") == EQUATIONAL_GRAMMAR_SCHEMA:
        formulas = tuple(
            row.axiom for row in enumerate_universal_equations(signature, formula_grammar)
        )
    else:
        raise ValueError(
            "generic finite adapter requires a host-enumerable formula grammar"
        )
    validate_axioms(signature, formulas)
    return formulas


def preflight_blueprint(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    formula_grammar: Mapping[str, Any],
    strata: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    _validate_adapter_config(adapter_config)
    formulas = build_formulas(
        signature,
        adapter_config=adapter_config,
        formula_grammar=formula_grammar,
    )
    labeled = 0
    context_model_budget_upper_bound = 0
    canonical_model_budget_upper_bound = 0
    quotient, relabeling_cap = _quotient_config(adapter_config)
    generation = _model_generation_config(adapter_config)
    image = adapter_config.get("functor_image")
    for row in strata:
        sizes = {str(key): int(value) for key, value in dict(row["sort_sizes"]).items()}
        stratum_labeled = finite_interpretation_count(signature, sizes)
        labeled += stratum_labeled
        relabelings = prod(factorial(size) for size in sizes.values())
        if quotient and relabelings > relabeling_cap:
            raise ValueError(
                "generic finite isomorphism quotient exceeds max_relabelings_per_model"
            )
        if generation["mode"] == _SMT_EXACT:
            canonical_cap = int(generation["max_canonical_models_per_stratum"])
            canonical_model_budget_upper_bound += canonical_cap
            context_model_budget_upper_bound += canonical_cap * (
                relabelings if quotient else 1
            )
        else:
            canonical_model_budget_upper_bound += stratum_labeled
            context_model_budget_upper_bound += stratum_labeled
    if image is not None:
        labeled = int(image["source_object_count"])
        canonical_model_budget_upper_bound = int(image["canonical_model_count"])
        context_model_budget_upper_bound = canonical_model_budget_upper_bound
    result = {
        "formula_count": len(formulas),
        "labeled_model_count": labeled,
        "context_model_budget_upper_bound": context_model_budget_upper_bound,
        "truth_cell_budget_upper_bound": (
            len(formulas) * canonical_model_budget_upper_bound
        ),
        "complete_census_available": True,
        "model_generation": (
            {"mode": "deterministic_pointwise_functor_image"}
            if image is not None else dict(generation)
        ),
        "census_completion_policy": (
            "complete_relative_to_frozen_source_functor"
            if image is not None
            else "materialization_requires_final_solver_unsat"
            if generation["mode"] == _SMT_EXACT
            else "exhaustive_table_iteration"
        ),
        "quotient_policy": (
            "sortwise_isomorphism_canonicalization.v1"
            if quotient
            else "labeled_models_no_isomorphism_quotient.v1"
        ),
        "max_relabelings_per_model": relabeling_cap,
    }
    if image is not None:
        result["functor_image"] = dict(image)
    if formula_grammar.get("schema") == EQUATIONAL_GRAMMAR_SCHEMA:
        result["formula_universe_receipt"] = equational_formula_universe_receipt(
            signature, formula_grammar, formulas=formulas
        )
    return result


@dataclass(frozen=True)
class GenericFiniteModelRecord:
    model_id: str
    stratum_id: str
    model: FiniteModel
    multiplicity: int = 1
    schema: str = "leanmill.generic_finite_model_record.v1"

    def __post_init__(self) -> None:
        if type(self.multiplicity) is not int or self.multiplicity < 1:
            raise ValueError("generic finite model multiplicity must be positive")

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "model_id": self.model_id,
            "stratum_id": self.stratum_id,
            "model": self.model.to_json(),
            "multiplicity": self.multiplicity,
        }


@dataclass(frozen=True)
class GenericFiniteUniverseReceipt:
    signature_hash: str
    strata: tuple[tuple[tuple[str, int], ...], ...]
    base_axiom_hashes: tuple[str, ...]
    labeled_interpretation_count: int
    accepted_labeled_count: int
    canonical_model_count: int
    model_order_digest: str
    quotient_policy: str
    generation_policy: str = "exhaustive_table_iteration.v1"
    stratum_enumeration_receipts: tuple[Mapping[str, Any], ...] = ()
    functor_image_receipt: Mapping[str, Any] = field(default_factory=dict)
    complete: bool = True
    schema: str = "leanmill.generic_finite_model_universe.v2"

    @property
    def receipt_digest(self) -> str:
        return content_hash(self.to_json(include_digest=False))

    @property
    def declared_strata(self) -> tuple[Mapping[str, Any], ...]:
        return tuple({"sort_sizes": dict(row)} for row in self.strata)

    def to_json(self, *, include_digest: bool = True) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "signature_sha256": self.signature_hash,
            "strata": [dict(row) for row in self.strata],
            "base_axiom_sha256s": list(self.base_axiom_hashes),
            "labeled_interpretation_count": self.labeled_interpretation_count,
            "accepted_labeled_count": self.accepted_labeled_count,
            "canonical_model_count": self.canonical_model_count,
            "model_order_digest": self.model_order_digest,
            "quotient_policy": self.quotient_policy,
            "complete": self.complete,
        }
        if self.schema == "leanmill.generic_finite_model_universe.v3":
            core["generation_policy"] = self.generation_policy
            core["stratum_enumeration_receipts"] = [
                dict(row) for row in self.stratum_enumeration_receipts
            ]
        if self.schema == "leanmill.generic_finite_model_universe.v4":
            core["generation_policy"] = self.generation_policy
            core["functor_image_receipt"] = dict(self.functor_image_receipt)
        if self.schema == "leanmill.generic_finite_model_universe.v1":
            core.pop("canonical_model_count")
        return {**core, "receipt_sha256": content_hash(core)} if include_digest else core


@dataclass(frozen=True)
class GenericFiniteModelUniverse:
    signature: TheorySignature
    models: tuple[GenericFiniteModelRecord, ...]
    receipt: GenericFiniteUniverseReceipt

    @property
    def adapter_id(self) -> str:
        return ADAPTER_ID

    @property
    def model_ids(self) -> tuple[str, ...]:
        return tuple(row.model_id for row in self.models)

    def __post_init__(self) -> None:
        if not self.receipt.complete or self.receipt.signature_hash != self.signature.content_hash:
            raise ValueError("generic finite universe receipt mismatch")
        if self.receipt.model_order_digest != content_hash({"model_ids": list(self.model_ids)}):
            raise ValueError("generic finite universe model order mismatch")
        if self.receipt.canonical_model_count != len(self.models):
            raise ValueError("generic finite universe canonical count mismatch")
        if self.receipt.accepted_labeled_count != sum(
            row.multiplicity for row in self.models
        ):
            raise ValueError("generic finite universe multiplicity mismatch")

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "leanmill.model_universe_envelope.v1",
            "adapter_id": self.adapter_id,
            "signature": self.signature.to_json(),
            "receipt": self.receipt.to_json(),
            "models": [row.to_json() for row in self.models],
        }


def _stratum_id(sort_sizes: Mapping[str, int]) -> str:
    return "sort_sizes:" + ",".join(f"{key}={value}" for key, value in sorted(sort_sizes.items()))


def build_model_universe(
    signature: TheorySignature,
    *,
    strata: Sequence[Mapping[str, Any]],
    base_axioms: Sequence[AxiomFormula] = (),
    adapter_config: Mapping[str, Any] | None = None,
) -> GenericFiniteModelUniverse:
    adapter_config = dict(adapter_config or {})
    if adapter_config.get("functor_image") is not None:
        raise ValueError("functor images must replay from a frozen snapshot")
    quotient, relabeling_cap = _quotient_config(adapter_config)
    generation = _model_generation_config(adapter_config)
    validate_axioms(signature, base_axioms)
    normalized = tuple(
        tuple(sorted((str(key), int(value)) for key, value in dict(row["sort_sizes"]).items()))
        for row in strata
    )
    if not normalized:
        raise ValueError("generic finite adapter requires at least one stratum")
    if len(set(normalized)) != len(normalized):
        raise ValueError("generic finite adapter strata must be unique")
    representatives: dict[str, tuple[str, FiniteModel, int]] = {}
    enumeration_receipts: list[Mapping[str, Any]] = []
    labeled = 0
    accepted = 0
    for stratum in normalized:
        sizes = dict(stratum)
        labeled += finite_interpretation_count(signature, sizes)
        if generation["mode"] == _SMT_EXACT:
            enumeration = enumerate_finite_models_smt(
                signature,
                sort_sizes=sizes,
                base_axioms=base_axioms,
                quotient_isomorphisms=quotient,
                max_relabelings_per_model=relabeling_cap,
                max_canonical_models=int(
                    generation["max_canonical_models_per_stratum"]
                ),
                timeout_ms=int(generation["timeout_ms_per_stratum"]),
            )
            enumeration_receipts.append(enumeration.receipt.to_json())
            if not enumeration.receipt.complete:
                raise ValueError(
                    "exact SMT census did not exhaust stratum "
                    f"{_stratum_id(sizes)}: {enumeration.receipt.status}: "
                    f"{enumeration.receipt.reason}"
                )
            model_rows = tuple(
                (row.model, row.multiplicity) for row in enumeration.model_classes
            )
        else:
            def exhaustive_model_rows():
                for raw_model in iter_finite_models(signature, sizes):
                    if not all(
                        evaluate_formula(signature, axiom.formula, raw_model)
                        for axiom in base_axioms
                    ):
                        continue
                    model = (
                        canonicalize_finite_model(
                            signature,
                            raw_model,
                            max_relabelings=relabeling_cap,
                        )
                        if quotient
                        else raw_model
                    )
                    yield model, 1

            model_rows = exhaustive_model_rows()
        for model, multiplicity in model_rows:
            accepted += multiplicity
            model_id = "model:" + content_hash(
                {"signature_sha256": signature.content_hash, "model": model.to_json()}
            )
            prior = representatives.get(model_id)
            representatives[model_id] = (
                _stratum_id(sizes),
                model,
                multiplicity if prior is None else prior[2] + multiplicity,
            )
    records = [
        GenericFiniteModelRecord(
            model_id=model_id,
            stratum_id=stratum_id,
            model=model,
            multiplicity=multiplicity,
        )
        for model_id, (stratum_id, model, multiplicity) in representatives.items()
    ]
    records.sort(key=lambda row: row.model_id)
    ids = tuple(row.model_id for row in records)
    receipt = GenericFiniteUniverseReceipt(
        signature_hash=signature.content_hash,
        strata=normalized,
        base_axiom_hashes=tuple(sorted(row.semantic_hash for row in base_axioms)),
        labeled_interpretation_count=labeled,
        accepted_labeled_count=accepted,
        canonical_model_count=len(records),
        model_order_digest=content_hash({"model_ids": list(ids)}),
        quotient_policy=(
            "sortwise_isomorphism_canonicalization.v1"
            if quotient
            else "labeled_models_no_isomorphism_quotient.v1"
        ),
        generation_policy=(
            "smt_isomorphism_class_enumeration.v1"
            if generation["mode"] == _SMT_EXACT
            else "exhaustive_table_iteration.v1"
        ),
        stratum_enumeration_receipts=tuple(enumeration_receipts),
        schema=(
            "leanmill.generic_finite_model_universe.v3"
            if generation["mode"] == _SMT_EXACT
            else "leanmill.generic_finite_model_universe.v2"
        ),
    )
    return GenericFiniteModelUniverse(signature, tuple(records), receipt)


def build_model_universe_image(
    signature: TheorySignature,
    *,
    source_models: Sequence[tuple[str, FiniteModel, int]],
    source_context_hash: str,
    functor_id: str,
    application_receipt_sha256: str,
    max_relabelings_per_model: int = 720,
) -> tuple[GenericFiniteModelUniverse, dict[str, Any]]:
    """Canonicalize the complete pointwise image of a frozen finite family."""

    if not source_models or not source_context_hash or not functor_id:
        raise ValueError("model-universe image requires source models and provenance")
    representatives: dict[str, tuple[FiniteModel, int]] = {}
    source_to_model: dict[str, str] = {}
    strata = set()
    for source_id, raw_model, multiplicity in source_models:
        if not source_id or source_id in source_to_model or multiplicity < 1:
            raise ValueError("model-universe image source identities must be unique")
        model = canonicalize_finite_model(
            signature, raw_model, max_relabelings=max_relabelings_per_model
        )
        model_id = "model:" + content_hash(
            {"signature_sha256": signature.content_hash, "model": model.to_json()}
        )
        prior = representatives.get(model_id)
        representatives[model_id] = (
            model,
            multiplicity + (0 if prior is None else prior[1]),
        )
        source_to_model[source_id] = model_id
        strata.add(tuple(model.sort_sizes))
    records = tuple(
        GenericFiniteModelRecord(
            model_id=model_id,
            stratum_id=_stratum_id(dict(model.sort_sizes)),
            model=model,
            multiplicity=multiplicity,
        )
        for model_id, (model, multiplicity) in sorted(representatives.items())
    )
    mapping_digest = content_hash(source_to_model)
    derivation = {
        "schema": "leanmill.finite_model_functor_image.v1",
        "source_context_hash": source_context_hash,
        "functor_id": functor_id,
        "application_receipt_sha256": application_receipt_sha256,
        "source_object_count": len(source_models),
        "canonical_image_model_count": len(records),
        "source_to_image_model_digest": mapping_digest,
        "complete_relative_to_source": True,
    }
    receipt = GenericFiniteUniverseReceipt(
        signature_hash=signature.content_hash,
        strata=tuple(sorted(strata)),
        base_axiom_hashes=(),
        labeled_interpretation_count=sum(row[2] for row in source_models),
        accepted_labeled_count=sum(row.multiplicity for row in records),
        canonical_model_count=len(records),
        model_order_digest=content_hash(
            {"model_ids": [row.model_id for row in records]}
        ),
        quotient_policy="functor_image_then_sortwise_isomorphism.v1",
        generation_policy="deterministic_pointwise_functor_image.v1",
        functor_image_receipt=derivation,
        schema="leanmill.generic_finite_model_universe.v4",
    )
    universe = GenericFiniteModelUniverse(signature, records, receipt)
    transition_core = {**derivation, "source_to_image_model": source_to_model}
    return universe, {
        **transition_core,
        "receipt_sha256": content_hash(transition_core),
    }


def build_context_from_functor_application(
    source_context: Any,
    application: Mapping[str, Any],
    *,
    formula_grammar: Mapping[str, Any],
):
    """Apply a receipted pointwise model functor and build its exact image chart."""

    core = {key: value for key, value in application.items() if key != "receipt_sha256"}
    if (
        application.get("schema") != "leanmill.finite_model_functor_application.v1"
        or application.get("receipt_sha256") != content_hash(core)
        or application.get("context_hash") != source_context.context_hash
    ):
        raise ValueError("finite-model functor application does not replay")
    signature = TheorySignature.from_json(application["signature"])
    source = {row.model_id: row for row in source_context.universe.models}
    rows = application.get("models")
    if not isinstance(rows, Mapping) or not rows or not set(rows) <= set(source):
        raise ValueError("finite-model functor image has invalid source coverage")
    universe, receipt = build_model_universe_image(
        signature,
        source_models=tuple(
            (
                model_id,
                FiniteModel.from_json(model),
                finite_model_record_weight(source[model_id]),
            )
            for model_id, model in rows.items()
        ),
        source_context_hash=source_context.context_hash,
        functor_id=str(application["functor_id"]),
        application_receipt_sha256=str(application["receipt_sha256"]),
    )
    from ztare.leanmill.finite_theory_context import build_formal_theory_context

    formulas = build_formulas(signature, adapter_config={}, formula_grammar=formula_grammar)
    return build_formal_theory_context(
        signature=signature, formulas=formulas, universe=universe
    ), receipt


def load_model_universe(value: Mapping[str, Any]) -> GenericFiniteModelUniverse:
    if value.get("adapter_id") != ADAPTER_ID:
        raise ValueError("generic finite universe adapter ID")
    signature = TheorySignature.from_json(value["signature"])
    row = value["receipt"]
    receipt = GenericFiniteUniverseReceipt(
        signature_hash=str(row["signature_sha256"]),
        strata=tuple(
            tuple(sorted((str(key), int(item)) for key, item in dict(stratum).items()))
            for stratum in row["strata"]
        ),
        base_axiom_hashes=tuple(str(item) for item in row["base_axiom_sha256s"]),
        labeled_interpretation_count=int(row["labeled_interpretation_count"]),
        accepted_labeled_count=int(row["accepted_labeled_count"]),
        canonical_model_count=int(row.get("canonical_model_count", len(value["models"]))),
        model_order_digest=str(row["model_order_digest"]),
        quotient_policy=str(
            row.get("quotient_policy")
            or "labeled_models_no_isomorphism_quotient.v1"
        ),
        generation_policy=str(
            row.get("generation_policy") or "exhaustive_table_iteration.v1"
        ),
        stratum_enumeration_receipts=tuple(
            dict(item) for item in row.get("stratum_enumeration_receipts") or ()
        ),
        functor_image_receipt=dict(row.get("functor_image_receipt") or {}),
        complete=row.get("complete") is True,
        schema=str(row["schema"]),
    )
    if row.get("receipt_sha256") != receipt.receipt_digest:
        raise ValueError("generic finite universe receipt hash")
    models = tuple(
        GenericFiniteModelRecord(
            model_id=str(item["model_id"]),
            stratum_id=str(item["stratum_id"]),
            model=FiniteModel.from_json(item["model"]),
            multiplicity=int(item.get("multiplicity", 1)),
            schema=str(item["schema"]),
        )
        for item in value["models"]
    )
    for record in models:
        expected = "model:" + content_hash(
            {"signature_sha256": signature.content_hash, "model": record.model.to_json()}
        )
        if record.model_id != expected:
            raise ValueError("generic finite model identity")
    return GenericFiniteModelUniverse(signature, models, receipt)


CAPABILITIES = {
    "fixed_size_countermodel_finder": build_fixed_size_countermodel_finder,
}


__all__ = [
    "ADAPTER_ID", "CAPABILITIES", "GenericFiniteModelRecord", "GenericFiniteModelUniverse",
    "GenericFiniteUniverseReceipt", "build_context_from_functor_application", "build_model_universe_image", "build_model_universe", "load_model_universe",
    "build_fixed_size_countermodel_finder", "build_formulas", "preflight_blueprint",
]
