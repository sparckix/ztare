"""Residual information coordinates for one theory presentation."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Mapping, Sequence

from ztare.leanmill.equational_baseline import (
    bounded_equational_reduction_analysis,
    direct_equational_consequence_analysis,
)
from ztare.leanmill.finite_structure_baseline import STRUCTURAL_BASELINE_REF
from ztare.leanmill.first_order_baseline import (
    existential_witness_transport_witness,
)
from ztare.leanmill.theory_context import TheoryLandscapeContext
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Formula,
    Term,
    content_hash,
    logical_coordinate_hash,
)
from ztare.research_signals import ResidualYieldCoordinates, residual_information_yield


CHEAP_CONSEQUENCE_EVALUATOR_REF = "leanmill.cheap_consequence_evaluator.v11"
DIRECT_FIRST_ORDER_BASELINE_REF = "leanmill.first_order_logical_deduction.v11"
# Compatibility export for callers that treat the baseline identity as opaque.
DIRECT_EQUATIONAL_BASELINE_REF = DIRECT_FIRST_ORDER_BASELINE_REF
COMBINED_EQUATIONAL_STRUCTURAL_BASELINE_REF = (
    "leanmill.first_order_logical_plus_finite_structure.v9"
)
NO_CHEAP_BASELINE_REF = "leanmill.no_declared_cheap_baseline.v1"
CURRENT_CHEAP_BASELINE_REFS = frozenset(
    {
        DIRECT_FIRST_ORDER_BASELINE_REF,
        COMBINED_EQUATIONAL_STRUCTURAL_BASELINE_REF,
        STRUCTURAL_BASELINE_REF,
        NO_CHEAP_BASELINE_REF,
    }
)
_TARGETED_BRIDGE_STEPS = 6
_TARGETED_BRIDGE_STATES = 1_024
_TARGETED_BRIDGE_LIMIT = 1
_CACHE_LIMIT = 4096
_CACHE: OrderedDict[
    tuple[str, tuple[str, ...], str], "TheoryResidualYield"
] = OrderedDict()
_CACHE_LOCK = RLock()


@dataclass(frozen=True)
class TheoryResidualYield:
    presentation_ids: tuple[str, ...]
    joint_only_consequence_ids: tuple[str, ...]
    cheap_baseline_consequence_ids: tuple[str, ...]
    residual_consequence_ids: tuple[str, ...]
    cheap_baseline_witnesses: Mapping[str, Mapping[str, object]]
    cheap_baseline_inconclusive_ids: tuple[str, ...]
    cheap_baseline_inconclusive_receipts: Mapping[str, Mapping[str, object]]
    structural_baseline: Mapping[str, object] | None
    coordinates: ResidualYieldCoordinates
    schema: str = "leanmill.theory_residual_information_yield.v3"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "presentation_ids": list(self.presentation_ids),
            "joint_only_consequence_ids": list(self.joint_only_consequence_ids),
            "cheap_baseline_consequence_ids": list(
                self.cheap_baseline_consequence_ids
            ),
            "residual_consequence_ids": list(self.residual_consequence_ids),
            "cheap_baseline_witnesses": {
                key: dict(value)
                for key, value in sorted(self.cheap_baseline_witnesses.items())
            },
            "cheap_baseline_inconclusive_ids": list(
                self.cheap_baseline_inconclusive_ids
            ),
            "cheap_baseline_inconclusive_receipts": {
                key: dict(value)
                for key, value in sorted(
                    self.cheap_baseline_inconclusive_receipts.items()
                )
            },
            "structural_baseline": (
                dict(self.structural_baseline)
                if self.structural_baseline is not None
                else None
            ),
            "coordinates": self.coordinates.to_json(),
        }


@dataclass(frozen=True)
class TheoryProgramYield:
    presentation_ids: tuple[str, ...]
    consequence_ids: tuple[str, ...]
    cheap_baseline_consequence_ids: tuple[str, ...]
    residual_prediction_ids: tuple[str, ...]
    cheap_baseline_witnesses: Mapping[str, Mapping[str, object]]
    cheap_baseline_inconclusive_ids: tuple[str, ...]
    cheap_baseline_inconclusive_receipts: Mapping[str, Mapping[str, object]]
    structural_baseline: Mapping[str, object] | None
    coordinates: ResidualYieldCoordinates
    schema: str = "leanmill.theory_program_information_yield.v1"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "presentation_ids": list(self.presentation_ids),
            "consequence_ids": list(self.consequence_ids),
            "cheap_baseline_consequence_ids": list(
                self.cheap_baseline_consequence_ids
            ),
            "residual_prediction_ids": list(self.residual_prediction_ids),
            "cheap_baseline_witnesses": {
                key: dict(value)
                for key, value in sorted(self.cheap_baseline_witnesses.items())
            },
            "cheap_baseline_inconclusive_ids": list(
                self.cheap_baseline_inconclusive_ids
            ),
            "cheap_baseline_inconclusive_receipts": {
                key: dict(value)
                for key, value in sorted(
                    self.cheap_baseline_inconclusive_receipts.items()
                )
            },
            "structural_baseline": (
                dict(self.structural_baseline)
                if self.structural_baseline is not None
                else None
            ),
            "coordinates": self.coordinates.to_json(),
        }


def _term_units(term: Term) -> int:
    return 1 + sum(_term_units(child) for child in term.args)


def _formula_units(formula: Formula) -> int:
    return (
        1
        + len(formula.binders)
        + sum(_term_units(term) for term in formula.terms)
        + sum(_formula_units(child) for child in formula.formulas)
    )


def _witness_premise_hashes(witness: Mapping[str, object]) -> set[str]:
    hashes = {
        str(witness[key])
        for key in ("premise_hash", "carrier_premise_hash", "rewrite_premise_hash")
        if witness.get(key)
    }
    hashes.update(
        str(row.get("premise_hash"))
        for row in witness.get("steps") or ()
        if isinstance(row, Mapping) and row.get("premise_hash")
    )
    return hashes


def _theory_consequence_yield(
    context: TheoryLandscapeContext,
    presentation: Sequence[str],
    *,
    consequence_scope: str,
) -> TheoryResidualYield:
    """Price consequences after cheap deduction and structural conditioning."""

    if consequence_scope not in {"joint_only", "all"}:
        raise ValueError("unsupported theory consequence scope")
    formulas = tuple(dict.fromkeys(str(value) for value in presentation))
    cache_key = (context.context_hash, formulas, consequence_scope)
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if cached is not None:
            _CACHE.move_to_end(cache_key)
            return cached
    presentation_ids = frozenset(formulas)
    joint_only = (
        tuple(
            formula_id
            for formula_id in context.synergy_ids(formulas)
            if formula_id not in presentation_ids
        )
        if consequence_scope == "joint_only"
        else tuple(
            formula_id
            for formula_id in context.closure_ids(formulas)
            if formula_id not in presentation_ids
        )
    )
    axiom_map: dict[str, AxiomFormula] = {
        str(row.formula_id): row.axiom
        for row in getattr(context, "formula_profiles", ())
        if hasattr(row, "formula_id") and isinstance(getattr(row, "axiom", None), AxiomFormula)
    }
    witnesses: dict[str, Mapping[str, object]] = {}
    inconclusive: dict[str, Mapping[str, object]] = {}
    base_axioms = tuple(
        row
        for row in getattr(context, "base_axioms", ())
        if isinstance(row, AxiomFormula)
    )
    structural_baseline = context.cheap_structural_baseline(formulas, joint_only)
    preexplained_structural_ids = {
        str(row)
        for row in (
            structural_baseline.get("explained_formula_ids") or ()
            if isinstance(structural_baseline, Mapping)
            else ()
        )
    }
    has_equational_baseline = all(formula_id in axiom_map for formula_id in formulas)
    if has_equational_baseline:
        premises = base_axioms + tuple(
            axiom_map[formula_id] for formula_id in formulas
        )
        remaining = [
            target_id
            for target_id in joint_only
            if target_id not in preexplained_structural_ids
            and target_id in axiom_map
        ]
        for target_id in remaining:
            analysis = direct_equational_consequence_analysis(
                premises, axiom_map[target_id]
            )
            if analysis.witness is not None:
                witnesses[target_id] = analysis.witness.to_json()
            elif (
                logical_witness := existential_witness_transport_witness(
                    premises, axiom_map[target_id]
                )
            ) is not None:
                witnesses[target_id] = logical_witness.to_json()
            elif (
                analysis.bounded_search is not None
                and analysis.bounded_search.status == "state_cap_saturated"
            ):
                inconclusive[target_id] = analysis.bounded_search.to_json()
    structural_ids: tuple[str, ...] = ()
    structural_active = False
    conditioning_bits = context.incidence.base_mask
    if isinstance(structural_baseline, Mapping):
        forced_templates = structural_baseline.get("forced_templates")
        structural_active = isinstance(forced_templates, list) and bool(
            forced_templates
        )
        if structural_active:
            conditioning_bits = int(
                str(structural_baseline.get("conditioning_bits_hex") or "0"),
                16,
            )
            if (
                not conditioning_bits
                or conditioning_bits & ~context.incidence.base_mask
            ):
                raise ValueError("structural baseline conditioning mask is invalid")
        structural_ids = tuple(
            str(row) for row in structural_baseline.get("explained_formula_ids") or ()
        )
        explanation_map = structural_baseline.get("explanation_map")
        explanation_map = explanation_map if isinstance(explanation_map, Mapping) else {}
        for formula_id in structural_ids:
            if formula_id in witnesses:
                continue
            witnesses[formula_id] = {
                "schema": "leanmill.finite_structure_baseline_witness.v1",
                "authority": "exact_finite_context_template_replay",
                "baseline_ref": STRUCTURAL_BASELINE_REF,
                "formula_id": formula_id,
                "template_ids": [
                    str(row) for row in explanation_map.get(formula_id) or ()
                ],
                "structural_baseline_receipt_sha256": str(
                    structural_baseline.get("receipt_sha256") or ""
                ),
                "claim_boundary": str(
                    structural_baseline.get("claim_boundary") or ""
                ),
            }
    profile_bits = {
        row.attribute_id: row.truth_bits for row in context.incidence.profiles
    }
    object_indices = tuple(
        index
        for index in range(len(context.incidence.object_ids))
        if conditioning_bits & (1 << index)
    )
    description_units = float(
        sum(_formula_units(axiom_map[value].formula) for value in formulas)
        if all(value in axiom_map for value in formulas)
        else len(formulas)
    )
    priced_joint_only = tuple(
        formula_id for formula_id in joint_only if formula_id not in inconclusive
    )
    coordinates = residual_information_yield(
        priced_joint_only,
        tuple(witnesses),
        object_indices,
        lambda candidate_id, index: bool(
            profile_bits[candidate_id] & (1 << int(index))
        ),
        baseline_ref=(
            COMBINED_EQUATIONAL_STRUCTURAL_BASELINE_REF
            if structural_active and has_equational_baseline
            else STRUCTURAL_BASELINE_REF
            if structural_active
            else DIRECT_EQUATIONAL_BASELINE_REF
            if has_equational_baseline
            else NO_CHEAP_BASELINE_REF
        ),
        description_units=description_units,
    )
    result = TheoryResidualYield(
        presentation_ids=formulas,
        joint_only_consequence_ids=joint_only,
        cheap_baseline_consequence_ids=coordinates.baseline_ids,
        residual_consequence_ids=coordinates.residual_ids,
        cheap_baseline_witnesses=witnesses,
        cheap_baseline_inconclusive_ids=tuple(
            formula_id for formula_id in joint_only if formula_id in inconclusive
        ),
        cheap_baseline_inconclusive_receipts=inconclusive,
        structural_baseline=(
            dict(structural_baseline)
            if isinstance(structural_baseline, Mapping)
            else None
        ),
        coordinates=coordinates,
    )
    with _CACHE_LOCK:
        _CACHE[cache_key] = result
        _CACHE.move_to_end(cache_key)
        while len(_CACHE) > _CACHE_LIMIT:
            _CACHE.popitem(last=False)
    return result


def theory_residual_information_yield(
    context: TheoryLandscapeContext,
    presentation: Sequence[str],
) -> TheoryResidualYield:
    """Price conjunction-only consequences for the compact-pack profile."""

    return _theory_consequence_yield(
        context, presentation, consequence_scope="joint_only"
    )


def theory_program_information_yield(
    context: TheoryLandscapeContext,
    presentation: Sequence[str],
) -> TheoryProgramYield:
    """Price every predicted consequence of a candidate theory program.

    Unlike compact-pack synergy, this does not require a consequence to depend
    on the conjunction.  Premise dependency remains an inspectable coordinate
    and can still be tested later by leave-one-out replay.
    """

    raw = _theory_consequence_yield(
        context, presentation, consequence_scope="all"
    )
    return TheoryProgramYield(
        presentation_ids=raw.presentation_ids,
        consequence_ids=raw.joint_only_consequence_ids,
        cheap_baseline_consequence_ids=raw.cheap_baseline_consequence_ids,
        residual_prediction_ids=raw.residual_consequence_ids,
        cheap_baseline_witnesses=raw.cheap_baseline_witnesses,
        cheap_baseline_inconclusive_ids=raw.cheap_baseline_inconclusive_ids,
        cheap_baseline_inconclusive_receipts=raw.cheap_baseline_inconclusive_receipts,
        structural_baseline=raw.structural_baseline,
        coordinates=raw.coordinates,
    )


def _prediction_coordinate_identity(
    context: TheoryLandscapeContext,
    formula_id: str,
) -> dict[str, Any]:
    """Expose lossless product structure without interpreting the substrate."""

    raw = context.anonymous_formula_profile(formula_id).get("formula")
    if not isinstance(raw, Mapping):
        return {
            "prediction_formula_id": formula_id,
            "status": "opaque_coordinate",
            "prediction_atom_ids": [formula_id],
            "prediction_atom_count": 1,
        }
    try:
        formula = Formula.from_json(raw)
    except (TypeError, ValueError):
        return {
            "prediction_formula_id": formula_id,
            "status": "opaque_coordinate",
            "prediction_atom_ids": [formula_id],
            "prediction_atom_count": 1,
        }

    binder_layers = []
    body = formula
    while body.kind == "forall":
        binder_layers.append(body.binders)
        body = body.formulas[0]
    if body.kind != "and":
        return {
            "prediction_formula_id": formula_id,
            "status": "single_coordinate",
            "prediction_atom_ids": [formula_id],
            "prediction_atom_count": 1,
        }

    def conjuncts(value: Formula) -> tuple[Formula, ...]:
        if value.kind != "and":
            return (value,)
        return tuple(
            atom
            for child in value.formulas
            for atom in conjuncts(child)
        )

    atom_hashes = []
    for atom in conjuncts(body):
        for binders in reversed(binder_layers):
            atom = Formula.forall(binders, atom)
        atom_hashes.append(logical_coordinate_hash(atom))
    unique_hashes = sorted(dict.fromkeys(atom_hashes))
    known_coordinates: dict[str, list[str]] = {}
    for candidate_id in context.formula_ids:
        candidate_raw = context.anonymous_formula_profile(candidate_id).get("formula")
        if not isinstance(candidate_raw, Mapping):
            continue
        try:
            candidate = Formula.from_json(candidate_raw)
        except (TypeError, ValueError):
            continue
        known_coordinates.setdefault(
            logical_coordinate_hash(candidate), []
        ).append(candidate_id)
    atoms = [
        {
            "prediction_atom_id": "prediction-atom:" + atom_hash,
            "existing_formula_ids": sorted(known_coordinates.get(atom_hash, ())),
        }
        for atom_hash in unique_hashes
    ]
    return {
        "prediction_formula_id": formula_id,
        "status": "logical_product_requires_separate_coordinates",
        "prediction_atom_ids": [row["prediction_atom_id"] for row in atoms],
        "prediction_atoms": atoms,
        "prediction_atom_count": len(atoms),
        "source_atom_multiplicity": len(atom_hashes),
    }


def prediction_coordinate_normal_form(
    context: TheoryLandscapeContext,
    prediction_formula_ids: Sequence[str],
) -> dict[str, Any]:
    """Receipt the lossless coordinate structure of nominated predictions."""

    predictions = tuple(dict.fromkeys(str(row) for row in prediction_formula_ids))
    if not predictions or len(predictions) != len(tuple(prediction_formula_ids)):
        raise ValueError("prediction-coordinate IDs must be nonempty and unique")
    unknown = set(predictions) - set(context.formula_ids)
    if unknown:
        raise ValueError(
            f"prediction-coordinate normalization contains unknown IDs: {sorted(unknown)}"
        )
    core = {
        "schema": "leanmill.prediction_coordinate_normal_form.v1",
        "context_hash": context.context_hash,
        "predictions": [
            _prediction_coordinate_identity(context, target_id)
            for target_id in predictions
        ],
        "claim_boundary": (
            "decomposes only first-order top-level conjunction under universal "
            "quantifiers; every other shape remains one coordinate"
        ),
        "authority": "host_logical_normalizer",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def profile_theory_program_predictions(
    context: TheoryLandscapeContext,
    presentation: Sequence[str],
    prediction_formula_ids: Sequence[str],
) -> dict[str, Any]:
    """Describe agent-authored predictions on the current semantic chart.

    The chart is an instrument here: it may support, refute, or fail to test a
    prediction.  It does not choose the prediction and its residual-yield
    coordinates are not an admission rule for a :class:`TheoryProgram`.
    """

    hypotheses = tuple(dict.fromkeys(str(value) for value in presentation))
    predictions = tuple(dict.fromkeys(str(value) for value in prediction_formula_ids))
    if not hypotheses or not predictions:
        raise ValueError("theory-program profiling requires hypotheses and predictions")
    if len(hypotheses) != len(tuple(presentation)):
        raise ValueError("theory-program hypotheses must be unique")
    if len(predictions) != len(tuple(prediction_formula_ids)):
        raise ValueError("theory-program predictions must be unique")
    known = set(context.formula_ids)
    unknown = (set(hypotheses) | set(predictions)) - known
    if unknown:
        raise ValueError(f"theory-program profiling contains unknown formula IDs: {sorted(unknown)}")
    if set(hypotheses) & set(predictions):
        raise ValueError("theory-program predictions must be outside its presentation")

    extent_bits = context.incidence.extent_bits(hypotheses)
    program_yield = (
        theory_program_information_yield(context, hypotheses)
        if context.complete
        else None
    )
    residual = set(program_yield.residual_prediction_ids) if program_yield else set()
    cheap = set(program_yield.cheap_baseline_consequence_ids) if program_yield else set()
    inconclusive = (
        set(program_yield.cheap_baseline_inconclusive_ids) if program_yield else set()
    )
    targeted_cheap: dict[str, Mapping[str, object]] = {}
    equational_targeting_available = False
    if program_yield is not None:
        formulas = {
            str(row.formula_id): row.axiom
            for row in context.formula_profiles
            if isinstance(getattr(row, "axiom", None), AxiomFormula)
        }
        equational_targeting_available = all(
            formula_id in formulas for formula_id in hypotheses + predictions
        )
        if equational_targeting_available:
            premises = tuple(context.base_axioms) + tuple(
                formulas[formula_id] for formula_id in hypotheses
            )
            for target_id in predictions:
                if target_id not in residual:
                    continue
                bridge_ids = sorted(
                    (
                        formula_id
                        for formula_id in program_yield.cheap_baseline_consequence_ids
                        if formula_id in formulas
                        and _witness_premise_hashes(
                            program_yield.cheap_baseline_witnesses[formula_id]
                        )
                    ),
                    key=lambda formula_id: (
                        str(
                            program_yield.cheap_baseline_witnesses[formula_id].get(
                                "schema", ""
                            )
                        ).startswith("leanmill.composed_"),
                        _formula_units(formulas[formula_id].formula),
                        formula_id,
                    ),
                )
                for bridge_id in bridge_ids[:_TARGETED_BRIDGE_LIMIT]:
                    bridge_witness = program_yield.cheap_baseline_witnesses.get(
                        bridge_id, {}
                    )
                    if str(bridge_witness.get("schema") or "").startswith(
                        "leanmill.finite_structure_"
                    ):
                        continue
                    analysis = bounded_equational_reduction_analysis(
                        premises + (formulas[bridge_id],),
                        formulas[target_id],
                        max_steps=_TARGETED_BRIDGE_STEPS,
                        max_states_per_side=_TARGETED_BRIDGE_STATES,
                    )
                    if analysis.witness is None:
                        continue
                    local = analysis.witness.to_json()
                    if formulas[bridge_id].semantic_hash not in _witness_premise_hashes(
                        local
                    ):
                        continue
                    core = {
                        "schema": "leanmill.targeted_composed_equational_baseline.v1",
                        "dependency_formula_id": bridge_id,
                        "dependency_witness_receipt": str(
                            bridge_witness.get("receipt_sha256") or ""
                        ),
                        "local_witness": local,
                    }
                    targeted_cheap[target_id] = {
                        **core,
                        "receipt_sha256": content_hash(core),
                    }
                    break
    rows: list[dict[str, Any]] = []
    for target_id in predictions:
        counterexample_id = context.incidence.implication_counterexample_object_id(
            hypotheses, target_id
        )
        premise_ablation = []
        for removed_id in hypotheses:
            reduced = tuple(row for row in hypotheses if row != removed_id)
            reduced_extent = context.incidence.extent_bits(reduced)
            reduced_counterexample = (
                context.incidence.implication_counterexample_object_id(
                    reduced, target_id
                )
            )
            premise_ablation.append(
                {
                    "removed_formula_id": removed_id,
                    "status": (
                        "vacuous_without_premise"
                        if reduced_extent == 0
                        else "refuted_without_premise"
                        if reduced_counterexample is not None
                        else "holds_without_premise"
                    ),
                    "counterexample_object_id": reduced_counterexample,
                }
            )
        if extent_bits == 0:
            chart_status = "vacuous_on_empty_extent"
        elif counterexample_id is not None:
            chart_status = "refuted_in_context"
        elif context.complete:
            chart_status = "holds_on_complete_context"
        else:
            chart_status = "holds_on_observed_context"
        consequence_class = (
            "residual_bounded_consequence"
            if target_id in residual and target_id not in targeted_cheap
            else "cheap_baseline_bounded_consequence"
            if target_id in cheap or target_id in targeted_cheap
            else "baseline_inconclusive_bounded_consequence"
            if target_id in inconclusive
            else "not_a_bounded_consequence"
            if counterexample_id is not None
            else "unpriced_sample_relative_support"
            if not context.complete
            else "bounded_consequence_outside_priced_residual"
        )
        rows.append(
            {
                "prediction_formula_id": target_id,
                "chart_status": chart_status,
                "consequence_class": consequence_class,
                "counterexample_object_id": counterexample_id,
                "premise_ablation": premise_ablation,
                "targeted_cheap_baseline_witness": targeted_cheap.get(target_id),
            }
        )
    core = {
        "schema": "leanmill.theory_program_prediction_profile.v1",
        "context_hash": context.context_hash,
        "context_exact": context.complete,
        "presentation_formula_ids": list(hypotheses),
        "prediction_formula_ids": list(predictions),
        "extent_size": extent_bits.bit_count(),
        "equational_targeting_available": equational_targeting_available,
        "predictions": rows,
        "claim_boundary": (
            "support and refutation are exact only over the frozen context"
            if context.complete
            else "support and refutation are relative to the frozen observed panel"
        ),
        "authority": "host_semantic_diagnostic_only",
    }
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = [
    "CHEAP_CONSEQUENCE_EVALUATOR_REF",
    "COMBINED_EQUATIONAL_STRUCTURAL_BASELINE_REF",
    "CURRENT_CHEAP_BASELINE_REFS",
    "DIRECT_EQUATIONAL_BASELINE_REF",
    "DIRECT_FIRST_ORDER_BASELINE_REF",
    "NO_CHEAP_BASELINE_REF",
    "TheoryProgramYield",
    "TheoryResidualYield",
    "prediction_coordinate_normal_form",
    "profile_theory_program_predictions",
    "theory_program_information_yield",
    "theory_residual_information_yield",
]
