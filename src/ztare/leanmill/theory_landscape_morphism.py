"""Checked equational interpretations plus exploratory landscape fingerprints.

Fingerprints may nominate a comparison but carry no transport authority.  A
transportable interpretation must instead map source operations to typed target
terms, survive finite countermodel search, witness non-collapse, and discharge
its translated axioms through the governed Lean consequence boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from ztare.common.constraint_isomorphism import (
    ConstraintMorphism,
    ConstraintSignature,
)
from ztare.leanmill.finite_theory_context import FormalTheoryContext
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    Term,
    TheorySignature,
    content_hash,
    theory_content_hash,
    validate_axiom,
    validate_axioms,
)


CHECKED_INTERPRETATION_SCHEMA = "leanmill.equational_interpretation.v1"
CHECKED_INTERPRETATION_PLAN_SCHEMA = (
    "leanmill.checked_equational_interpretation_plan.v1"
)
CHECKED_INTERPRETATION_ADMISSION_SCHEMA = (
    "leanmill.checked_equational_interpretation_admission.v1"
)


@dataclass(frozen=True)
class EquationalOperationImage:
    """A typed target-term template for one source operation."""

    source_operation: str
    parameters: tuple[str, ...]
    body: Term
    schema: str = "leanmill.equational_operation_image.v1"

    def __post_init__(self) -> None:
        if (
            self.schema != "leanmill.equational_operation_image.v1"
            or not self.source_operation
            or len(set(self.parameters)) != len(self.parameters)
            or any(not value for value in self.parameters)
            or not isinstance(self.body, Term)
        ):
            raise ValueError("equational operation image is malformed")
        # Reuse Binder's identifier validation without assigning a sort yet.
        for parameter in self.parameters:
            Binder(parameter, "Carrier")

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_operation": self.source_operation,
            "parameters": list(self.parameters),
            "body": self.body.to_json(),
        }

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "EquationalOperationImage":
        required = {"schema", "source_operation", "parameters", "body"}
        if set(value) != required:
            raise ValueError("equational operation image fields differ")
        parameters = value.get("parameters")
        body = value.get("body")
        if not isinstance(parameters, list) or not all(
            isinstance(row, str) for row in parameters
        ) or not isinstance(body, Mapping):
            raise TypeError("equational operation image payload is malformed")
        return cls(
            source_operation=str(value.get("source_operation") or ""),
            parameters=tuple(parameters),
            body=Term.from_json(body),
            schema=str(value.get("schema") or ""),
        )


@dataclass(frozen=True)
class EquationalTheoryInterpretation:
    """Frozen signature interpretation from source operations to target terms."""

    source_signature_hash: str
    target_signature_hash: str
    sort_map: tuple[tuple[str, str], ...]
    operation_images: tuple[EquationalOperationImage, ...]
    schema: str = CHECKED_INTERPRETATION_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "sort_map", tuple(sorted(self.sort_map)))
        object.__setattr__(
            self,
            "operation_images",
            tuple(sorted(self.operation_images, key=lambda row: row.source_operation)),
        )
        if (
            self.schema != CHECKED_INTERPRETATION_SCHEMA
            or len(self.source_signature_hash) != 64
            or len(self.target_signature_hash) != 64
            or any(
                character not in "0123456789abcdef"
                for digest in (
                    self.source_signature_hash,
                    self.target_signature_hash,
                )
                for character in digest
            )
            or len({row[0] for row in self.sort_map}) != len(self.sort_map)
            or len({row.source_operation for row in self.operation_images})
            != len(self.operation_images)
        ):
            raise ValueError("equational interpretation identity is malformed")

    @property
    def sort_mapping(self) -> dict[str, str]:
        return dict(self.sort_map)

    @property
    def image_mapping(self) -> dict[str, EquationalOperationImage]:
        return {row.source_operation: row for row in self.operation_images}

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_signature_hash": self.source_signature_hash,
            "target_signature_hash": self.target_signature_hash,
            "sort_map": [list(row) for row in self.sort_map],
            "operation_images": [row.to_json() for row in self.operation_images],
        }

    @property
    def interpretation_id(self) -> str:
        return "theory-interpretation:" + content_hash(self.to_json())

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "EquationalTheoryInterpretation":
        required = {
            "schema",
            "source_signature_hash",
            "target_signature_hash",
            "sort_map",
            "operation_images",
        }
        if set(value) != required:
            raise ValueError("equational interpretation fields differ")
        sort_map = value.get("sort_map")
        images = value.get("operation_images")
        if (
            not isinstance(sort_map, list)
            or any(
                not isinstance(row, list)
                or len(row) != 2
                or not all(isinstance(item, str) for item in row)
                for row in sort_map
            )
            or not isinstance(images, list)
            or any(not isinstance(row, Mapping) for row in images)
        ):
            raise TypeError("equational interpretation payload is malformed")
        return cls(
            source_signature_hash=str(value.get("source_signature_hash") or ""),
            target_signature_hash=str(value.get("target_signature_hash") or ""),
            sort_map=tuple((row[0], row[1]) for row in sort_map),
            operation_images=tuple(
                EquationalOperationImage.from_json(row) for row in images
            ),
            schema=str(value.get("schema") or ""),
        )


def _term_sort(
    signature: TheorySignature,
    term: Term,
    environment: Mapping[str, str],
) -> str:
    if term.kind == "var":
        if term.name not in environment:
            raise ValueError(f"operation image contains free variable: {term.name}")
        return str(environment[term.name])
    operation = signature.operation_map.get(term.name)
    if operation is None:
        raise ValueError(f"operation image uses unknown target symbol: {term.name}")
    if len(term.args) != len(operation.arg_sorts):
        raise ValueError("operation image target application has the wrong arity")
    actual = tuple(_term_sort(signature, row, environment) for row in term.args)
    if actual != operation.arg_sorts:
        raise ValueError("operation image target application has the wrong sorts")
    return operation.result_sort


def validate_equational_interpretation(
    interpretation: EquationalTheoryInterpretation,
    source_signature: TheorySignature,
    target_signature: TheorySignature,
) -> None:
    """Validate total coverage and the type of every operation image."""

    if (
        interpretation.source_signature_hash != source_signature.content_hash
        or interpretation.target_signature_hash != target_signature.content_hash
    ):
        raise ValueError("equational interpretation crossed a frozen signature")
    if source_signature.relations:
        raise ValueError("checked equational interpretation does not map relations")
    sort_map = interpretation.sort_mapping
    if set(sort_map) != set(source_signature.sort_map):
        raise ValueError("equational interpretation must map every source sort")
    if any(value not in target_signature.sort_map for value in sort_map.values()):
        raise ValueError("equational interpretation names an unknown target sort")
    images = interpretation.image_mapping
    if set(images) != set(source_signature.operation_map):
        raise ValueError("equational interpretation must map every source operation")
    for name, source_operation in source_signature.operation_map.items():
        image = images[name]
        if len(image.parameters) != len(source_operation.arg_sorts):
            raise ValueError("equational operation image has the wrong arity")
        environment = {
            parameter: sort_map[sort]
            for parameter, sort in zip(
                image.parameters, source_operation.arg_sorts, strict=True
            )
        }
        result_sort = _term_sort(target_signature, image.body, environment)
        if result_sort != sort_map[source_operation.result_sort]:
            raise ValueError("equational operation image has the wrong result sort")


def build_equational_interpretation(
    source_signature: TheorySignature,
    target_signature: TheorySignature,
    *,
    sort_map: Mapping[str, str],
    operation_images: Mapping[str, EquationalOperationImage],
) -> EquationalTheoryInterpretation:
    interpretation = EquationalTheoryInterpretation(
        source_signature_hash=source_signature.content_hash,
        target_signature_hash=target_signature.content_hash,
        sort_map=tuple((str(key), str(value)) for key, value in sort_map.items()),
        operation_images=tuple(operation_images.values()),
    )
    validate_equational_interpretation(
        interpretation, source_signature, target_signature
    )
    return interpretation


def _substitute_term(term: Term, values: Mapping[str, Term]) -> Term:
    if term.kind == "var":
        return values.get(term.name, term)
    return Term.app(
        term.name, *(_substitute_term(row, values) for row in term.args)
    )


def translate_interpreted_term(
    term: Term,
    interpretation: EquationalTheoryInterpretation,
    source_signature: TheorySignature,
    target_signature: TheorySignature,
) -> Term:
    validate_equational_interpretation(
        interpretation, source_signature, target_signature
    )
    if term.kind == "var":
        return term
    source_operation = source_signature.operation_map.get(term.name)
    if source_operation is None or len(term.args) != len(source_operation.arg_sorts):
        raise ValueError("source term uses an unknown operation or wrong arity")
    translated_args = tuple(
        translate_interpreted_term(
            row, interpretation, source_signature, target_signature
        )
        for row in term.args
    )
    image = interpretation.image_mapping[term.name]
    return _substitute_term(
        image.body, dict(zip(image.parameters, translated_args, strict=True))
    )


def _translate_formula(
    formula: Formula,
    interpretation: EquationalTheoryInterpretation,
    source_signature: TheorySignature,
    target_signature: TheorySignature,
) -> Formula:
    if formula.kind == "rel":
        raise ValueError("checked equational interpretation cannot translate relations")
    terms = tuple(
        translate_interpreted_term(
            row, interpretation, source_signature, target_signature
        )
        for row in formula.terms
    )
    children = tuple(
        _translate_formula(
            row, interpretation, source_signature, target_signature
        )
        for row in formula.formulas
    )
    binders = tuple(
        Binder(row.name, interpretation.sort_mapping[row.sort])
        for row in formula.binders
    )
    return Formula(
        kind=formula.kind,
        terms=terms,
        formulas=children,
        binders=binders,
        relation=None,
    )


def translate_interpreted_axiom(
    axiom: AxiomFormula,
    interpretation: EquationalTheoryInterpretation,
    source_signature: TheorySignature,
    target_signature: TheorySignature,
) -> AxiomFormula:
    validate_axiom(source_signature, axiom)
    translated_formula = _translate_formula(
        axiom.formula, interpretation, source_signature, target_signature
    )
    translated = AxiomFormula(
        name=(
            "interpreted_"
            + axiom.name[:32]
            + "_"
            + axiom.semantic_hash[:10]
        ),
        formula=translated_formula,
    )
    validate_axiom(target_signature, translated)
    return translated


def _term_uses_target_operation(term: Term) -> bool:
    return term.kind == "app" or any(
        _term_uses_target_operation(row) for row in term.args
    )


def _noncollapse_receipt(
    interpretation: EquationalTheoryInterpretation,
    source_signature: TheorySignature,
    target_signature: TheorySignature,
    target_axioms: Sequence[AxiomFormula],
    target_model: Any | None,
) -> dict[str, Any]:
    from ztare.leanmill.finite_model import (
        FiniteModel,
        evaluate_axiom,
        evaluate_formula,
        validate_model,
    )

    if target_model is None:
        core = {
            "schema": "leanmill.interpretation_noncollapse.v1",
            "interpretation_id": interpretation.interpretation_id,
            "status": "missing_target_model",
            "target_model_sha256": None,
            "operation_image": None,
            "probe_semantic_hash": None,
            "authority": "exact_finite_target_model_replay",
        }
        return {**core, "receipt_sha256": content_hash(core)}
    if not isinstance(target_model, FiniteModel):
        raise TypeError("interpretation noncollapse witness must be a FiniteModel")
    validate_model(target_signature, target_model)
    if not all(
        evaluate_axiom(target_signature, axiom, target_model)
        for axiom in target_axioms
    ):
        raise ValueError("interpretation noncollapse model violates target axioms")
    selected: tuple[EquationalOperationImage, AxiomFormula] | None = None
    for image in interpretation.operation_images:
        source_operation = source_signature.operation_map[image.source_operation]
        if not source_operation.arg_sorts or not _term_uses_target_operation(image.body):
            continue
        left_binders = tuple(
            Binder(f"_left_{index}", interpretation.sort_mapping[sort])
            for index, sort in enumerate(source_operation.arg_sorts)
        )
        right_binders = tuple(
            Binder(f"_right_{index}", interpretation.sort_mapping[sort])
            for index, sort in enumerate(source_operation.arg_sorts)
        )
        left = _substitute_term(
            image.body,
            {
                parameter: Term.var(binder.name)
                for parameter, binder in zip(
                    image.parameters, left_binders, strict=True
                )
            },
        )
        right = _substitute_term(
            image.body,
            {
                parameter: Term.var(binder.name)
                for parameter, binder in zip(
                    image.parameters, right_binders, strict=True
                )
            },
        )
        probe = AxiomFormula(
            name="interpretation_noncollapse_probe",
            formula=Formula.exists(
                (*left_binders, *right_binders),
                Formula.negate(Formula.eq(left, right)),
            ),
        )
        validate_axiom(target_signature, probe)
        if evaluate_formula(target_signature, probe.formula, target_model):
            selected = (image, probe)
            break
    core = {
        "schema": "leanmill.interpretation_noncollapse.v1",
        "interpretation_id": interpretation.interpretation_id,
        "status": "witnessed" if selected is not None else "collapsed_on_target_model",
        "target_model_sha256": target_model.content_hash(target_signature),
        "operation_image": (
            selected[0].source_operation if selected is not None else None
        ),
        "probe_semantic_hash": (
            selected[1].semantic_hash if selected is not None else None
        ),
        "authority": "exact_finite_target_model_replay",
    }
    return {**core, "receipt_sha256": content_hash(core)}


@dataclass(frozen=True)
class CheckedEquationalInterpretationPlan:
    interpretation: EquationalTheoryInterpretation
    source_theory_hash: str
    target_theory_hash: str
    translated_axioms: tuple[AxiomFormula, ...]
    finite_implication_receipt: Mapping[str, Any]
    noncollapse_receipt: Mapping[str, Any]
    lean_tasks: tuple[Any, ...]
    schema: str = CHECKED_INTERPRETATION_PLAN_SCHEMA

    @property
    def status(self) -> str:
        from ztare.leanmill.finite_model import COUNTERMODEL, UNKNOWN

        finite_status = str(self.finite_implication_receipt.get("status") or "")
        if finite_status == COUNTERMODEL:
            return "refuted_by_finite_countermodel"
        if self.noncollapse_receipt.get("status") != "witnessed":
            return "awaiting_noncollapse_witness"
        if finite_status == UNKNOWN:
            return "finite_check_unknown"
        return "bounded_supported_awaiting_lean"

    def to_json(self) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "interpretation": self.interpretation.to_json(),
            "interpretation_id": self.interpretation.interpretation_id,
            "source_theory_hash": self.source_theory_hash,
            "target_theory_hash": self.target_theory_hash,
            "translated_axioms": [row.to_json() for row in self.translated_axioms],
            "finite_implication_receipt": dict(self.finite_implication_receipt),
            "noncollapse_receipt": dict(self.noncollapse_receipt),
            "lean_tasks": [row.to_json() for row in self.lean_tasks],
            "status": self.status,
            "claim_boundary": (
                "finite replay may refute; carrier-independent interpretation "
                "credit requires every generated Lean obligation"
            ),
        }
        return {**core, "plan_sha256": content_hash(core)}


def prepare_checked_equational_interpretation(
    source_signature: TheorySignature,
    source_axioms: Sequence[AxiomFormula],
    target_signature: TheorySignature,
    target_axioms: Sequence[AxiomFormula],
    interpretation: EquationalTheoryInterpretation,
    *,
    bounds: Any | None = None,
    target_model: Any | None = None,
) -> CheckedEquationalInterpretationPlan:
    """Translate axioms, run the finite kill, and emit Lean obligations."""

    from ztare.leanmill.finite_model import FiniteSearchBounds, certify_implication
    from ztare.leanmill.lean_consequence_bridge import render_lean_consequence_task

    source_axioms = tuple(source_axioms)
    target_axioms = tuple(target_axioms)
    validate_axioms(source_signature, source_axioms)
    validate_axioms(target_signature, target_axioms)
    validate_equational_interpretation(
        interpretation, source_signature, target_signature
    )
    translated = tuple(
        translate_interpreted_axiom(
            row, interpretation, source_signature, target_signature
        )
        for row in source_axioms
    )
    finite = certify_implication(
        target_signature,
        target_axioms,
        translated,
        bounds or FiniteSearchBounds(),
    ).to_json()
    noncollapse = _noncollapse_receipt(
        interpretation,
        source_signature,
        target_signature,
        target_axioms,
        target_model,
    )
    tasks = tuple(
        render_lean_consequence_task(target_signature, target_axioms, row)
        for row in translated
    )
    return CheckedEquationalInterpretationPlan(
        interpretation=interpretation,
        source_theory_hash=theory_content_hash(source_signature, source_axioms),
        target_theory_hash=theory_content_hash(target_signature, target_axioms),
        translated_axioms=translated,
        finite_implication_receipt=finite,
        noncollapse_receipt=noncollapse,
        lean_tasks=tasks,
    )


def admit_checked_equational_interpretation(
    plan: CheckedEquationalInterpretationPlan,
    *,
    proof_texts: Mapping[str, str],
    compile_fn: Callable[[str], bool | None],
    axiom_audit_fn: Callable[[str, str], tuple[bool, bool, Sequence[str]]],
) -> dict[str, Any]:
    """Kernel-recheck every obligation before admitting the interpretation."""

    from ztare.leanmill.lean_consequence_bridge import (
        recheck_governed_lean_consequence,
    )

    if plan.status == "refuted_by_finite_countermodel":
        raise ValueError("finite countermodel refutes the interpretation")
    if plan.noncollapse_receipt.get("status") != "witnessed":
        raise ValueError("interpretation lacks a noncollapse witness")
    expected = {row.task_id for row in plan.lean_tasks}
    if set(proof_texts) != expected:
        raise ValueError("interpretation proof bundle differs from its obligations")
    attempts = []
    accepted_statuses = {"proved_attributed", "proved_unattributed"}
    for task in plan.lean_tasks:
        attempt = recheck_governed_lean_consequence(
            task,
            str(proof_texts[task.task_id]),
            compile_fn=compile_fn,
            axiom_audit_fn=axiom_audit_fn,
            solver_entry=(
                "ztare.leanmill.theory_landscape_morphism."
                "admit_checked_equational_interpretation"
            ),
        )
        attempts.append(attempt.to_json())
    all_checked = all(row.get("status") in accepted_statuses for row in attempts)
    core = {
        "schema": CHECKED_INTERPRETATION_ADMISSION_SCHEMA,
        "interpretation_id": plan.interpretation.interpretation_id,
        "plan_sha256": plan.to_json()["plan_sha256"],
        "source_theory_hash": plan.source_theory_hash,
        "target_theory_hash": plan.target_theory_hash,
        "translated_axiom_hashes": [
            row.semantic_hash for row in plan.translated_axioms
        ],
        "finite_implication_receipt_sha256": plan.finite_implication_receipt.get(
            "receipt_sha256"
        ),
        "noncollapse_receipt_sha256": plan.noncollapse_receipt.get(
            "receipt_sha256"
        ),
        "lean_attempts": attempts,
        "status": "checked" if all_checked else "unresolved",
        "transport_authority_eligible": all_checked,
        "claim_boundary": (
            "signature interpretation only; no fullness, faithfulness, "
            "isomorphism, novelty, or target-conjecture proof claim"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def transport_axiom_through_checked_interpretation(
    axiom: AxiomFormula,
    interpretation: EquationalTheoryInterpretation,
    source_signature: TheorySignature,
    target_signature: TheorySignature,
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    """Produce a target conjecture only from an admitted interpretation."""

    core = {
        key: value for key, value in admission.items() if key != "receipt_sha256"
    }
    if (
        admission.get("schema") != CHECKED_INTERPRETATION_ADMISSION_SCHEMA
        or admission.get("receipt_sha256") != content_hash(core)
        or admission.get("status") != "checked"
        or admission.get("transport_authority_eligible") is not True
        or admission.get("interpretation_id") != interpretation.interpretation_id
    ):
        raise ValueError("axiom transport lacks a checked interpretation")
    translated = translate_interpreted_axiom(
        axiom, interpretation, source_signature, target_signature
    )
    transport_core = {
        "schema": "leanmill.checked_interpretation_axiom_transport.v1",
        "interpretation_id": interpretation.interpretation_id,
        "interpretation_admission_sha256": admission["receipt_sha256"],
        "source_axiom_sha256": axiom.content_hash,
        "target_axiom": translated.to_json(),
        "target_axiom_sha256": translated.content_hash,
        "status": "transported_pending_target_adjudication",
        "claim_boundary": "translation only; target provability is not implied by this receipt",
    }
    return {**transport_core, "receipt_sha256": content_hash(transport_core)}


@dataclass(frozen=True)
class TheoryLandscapeFingerprint:
    context_hash: str
    semantic_formula_class_sizes: tuple[int, ...]
    node_extent_sizes: tuple[int, ...]
    node_closure_sizes: tuple[int, ...]
    minimal_basis_sizes: tuple[int, ...]
    cover_edges: tuple[tuple[str, str], ...]
    synergy_size_histogram: tuple[tuple[int, int], ...]
    stratum_model_counts: tuple[tuple[int, int], ...]
    schema: str = "leanmill.theory_landscape_fingerprint.v1"

    @property
    def fingerprint_id(self) -> str:
        return "landscape:" + content_hash(self.to_json())

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "context_hash": self.context_hash,
            "semantic_formula_class_sizes": list(self.semantic_formula_class_sizes),
            "node_extent_sizes": list(self.node_extent_sizes),
            "node_closure_sizes": list(self.node_closure_sizes),
            "minimal_basis_sizes": list(self.minimal_basis_sizes),
            "cover_edges": [list(row) for row in self.cover_edges],
            "synergy_size_histogram": [list(row) for row in self.synergy_size_histogram],
            "stratum_model_counts": [list(row) for row in self.stratum_model_counts],
        }


def _cover_edges(nodes: tuple[Any, ...]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    ordered = sorted(nodes, key=lambda row: (row.closure_bits.bit_count(), row.node_id))
    for lower in ordered:
        supers = [
            upper for upper in ordered
            if lower.closure_bits != upper.closure_bits
            and lower.closure_bits & ~upper.closure_bits == 0
        ]
        minimal: list[Any] = []
        for upper in supers:
            if any(mid.closure_bits & ~upper.closure_bits == 0 for mid in minimal):
                continue
            minimal.append(upper)
        rows.extend((lower.node_id, upper.node_id) for upper in minimal)
    return tuple(sorted(rows))


def build_landscape_fingerprint(
    context: FormalTheoryContext, *, max_presentation_size: int = 2
) -> TheoryLandscapeFingerprint:
    nodes = context.generated_theory_nodes(max_presentation_size=max_presentation_size)
    synergy_hist: dict[int, int] = {}
    for node in nodes:
        for generator in node.minimal_generators:
            if len(generator) < 2:
                continue
            size = len(context.synergy_ids(generator))
            synergy_hist[size] = synergy_hist.get(size, 0) + 1
    strata: dict[int, int] = {}
    for model in context.universe.models:
        strata[model.carrier_size] = strata.get(model.carrier_size, 0) + 1
    return TheoryLandscapeFingerprint(
        context_hash=context.context_hash,
        semantic_formula_class_sizes=tuple(sorted(len(row) for row in context.semantic_formula_classes())),
        node_extent_sizes=tuple(sorted(row.extent_bits.bit_count() for row in nodes)),
        node_closure_sizes=tuple(sorted(row.closure_bits.bit_count() for row in nodes)),
        minimal_basis_sizes=tuple(
            sorted(min(map(len, row.minimal_generators)) for row in nodes)
        ),
        cover_edges=_cover_edges(nodes),
        synergy_size_histogram=tuple(sorted(synergy_hist.items())),
        stratum_model_counts=tuple(sorted(strata.items())),
    )


def propose_landscape_transport(
    source: TheoryLandscapeFingerprint,
    target: TheoryLandscapeFingerprint,
) -> ConstraintMorphism:
    """Nominate a mapping; all preservation obligations remain pending."""
    source_sig = ConstraintSignature(
        name="source_theory_landscape",
        components={
            "semantic_partition": "sequence",
            "closure_node_spectrum": "sequence",
            "cover_relation": "relation",
            "synergy_motif_spectrum": "sequence",
        },
    )
    target_sig = ConstraintSignature(
        name="target_theory_landscape",
        components=dict(source_sig.components),
    )
    component_map = {
        key: {
            "target": key,
            "source_type": value,
            "target_type": value,
            "transform": "anonymous_structural_match",
        }
        for key, value in source_sig.components.items()
    }
    obligations = [
        {
            "claim": f"preserve {key} under compiled target mapping",
            "status": "pending",
            "source_ref": source.fingerprint_id,
            "target_ref": target.fingerprint_id,
        }
        for key in component_map
    ]
    return ConstraintMorphism(
        source_signature=source_sig,
        target_signature=target_sig,
        component_map=component_map,
        preservation_obligations=obligations,
        target_discriminator={
            "kind": "target_context_replay",
            "target_context_hash": target.context_hash,
            "reject_on": "mapped formula, definition, or query fails local incidence evaluation",
        },
        relation="embedding",
    )


def test_compiled_landscape_mapping(
    morphism: ConstraintMorphism,
    *,
    compiled_mapping: Mapping[str, str],
    target_test: Callable[[Mapping[str, str]], bool],
) -> dict[str, Any]:
    required = set(morphism.component_map)
    if set(compiled_mapping) != required:
        raise ValueError("compiled mapping must cover every proposed component")
    passed = target_test(compiled_mapping) is True
    core = {
        "schema": "leanmill.compiled_landscape_mapping_test.v1",
        "morphism_hash": morphism.content_hash(),
        "compiled_mapping": dict(sorted(compiled_mapping.items())),
        "target_context_hash": morphism.target_discriminator.get("target_context_hash"),
        "status": "passed_local_target_test" if passed else "refuted",
        "axiom_authority_eligible": False,
        "next_gate": "separate signed obligation verification" if passed else "none",
    }
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = [
    "CHECKED_INTERPRETATION_ADMISSION_SCHEMA",
    "CHECKED_INTERPRETATION_PLAN_SCHEMA",
    "CHECKED_INTERPRETATION_SCHEMA",
    "CheckedEquationalInterpretationPlan",
    "EquationalOperationImage",
    "EquationalTheoryInterpretation",
    "TheoryLandscapeFingerprint",
    "admit_checked_equational_interpretation",
    "build_equational_interpretation",
    "build_landscape_fingerprint",
    "prepare_checked_equational_interpretation",
    "propose_landscape_transport",
    "test_compiled_landscape_mapping",
    "translate_interpreted_axiom",
    "translate_interpreted_term",
    "transport_axiom_through_checked_interpretation",
    "validate_equational_interpretation",
]
