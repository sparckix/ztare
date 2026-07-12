"""Residual information coordinates for one theory presentation."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Mapping, Sequence

from ztare.leanmill.equational_baseline import direct_equational_consequence_analysis
from ztare.leanmill.finite_structure_baseline import STRUCTURAL_BASELINE_REF
from ztare.leanmill.theory_context import TheoryLandscapeContext
from ztare.leanmill.theory_ir import AxiomFormula, Formula, Term, content_hash
from ztare.research_signals import ResidualYieldCoordinates, residual_information_yield


DIRECT_EQUATIONAL_BASELINE_REF = "leanmill.bidirectional_equational_deduction.v5"
COMBINED_EQUATIONAL_STRUCTURAL_BASELINE_REF = (
    "leanmill.bidirectional_equational_plus_finite_structure.v3"
)
NO_CHEAP_BASELINE_REF = "leanmill.no_declared_cheap_baseline.v1"
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
        for target_id in joint_only:
            if target_id in preexplained_structural_ids:
                continue
            target = axiom_map.get(target_id)
            if target is None:
                continue
            analysis = direct_equational_consequence_analysis(premises, target)
            witness = analysis.witness
            if witness is not None:
                witnesses[target_id] = witness.to_json()
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
            if target_id in residual
            else "cheap_baseline_bounded_consequence"
            if target_id in cheap
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
            }
        )
    core = {
        "schema": "leanmill.theory_program_prediction_profile.v1",
        "context_hash": context.context_hash,
        "context_exact": context.complete,
        "presentation_formula_ids": list(hypotheses),
        "prediction_formula_ids": list(predictions),
        "extent_size": extent_bits.bit_count(),
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
    "COMBINED_EQUATIONAL_STRUCTURAL_BASELINE_REF",
    "DIRECT_EQUATIONAL_BASELINE_REF",
    "NO_CHEAP_BASELINE_REF",
    "TheoryProgramYield",
    "TheoryResidualYield",
    "profile_theory_program_predictions",
    "theory_program_information_yield",
    "theory_residual_information_yield",
]
