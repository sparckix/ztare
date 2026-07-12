"""Deterministic finite-band design for the quarantined AxiomPack lane.

The module defines a pilot surface only.  It reuses the shared theory IR,
finite-model bounds, signed shadow manifest, and experiment-pricing adapter;
it does not execute a prover or grant proof credit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Hashable, Iterable, Mapping, Sequence

from ztare.leanmill.axiom_pack import (
    DEFAULT_CHEAP_FILTER_POLICY,
    AxiomPackBlueprint,
)
from ztare.leanmill.axiom_yield import (
    ShadowTask,
    build_shadow_task_manifest,
    rank_shadow_tasks,
)
from ztare.leanmill.finite_model import FiniteSearchBounds
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    SortDecl,
    Term,
    TheorySignature,
    content_hash,
    theory_content_hash,
    validate_axioms,
)


BAND_PILOT_SCHEMA = "leanmill.axiom_pack_band_pilot.v1"
BAND_PREREGISTRATION_SCHEMA = "leanmill.axiom_pack_band_preregistration.v1"
BAND_HELDOUT_TASK_SCHEMA = "leanmill.axiom_pack_band_heldout_task.v1"
BAND_PROPOSER_BRIEF_SCHEMA = "leanmill.axiom_pack_band_proposer_brief.v1"
BAND_SOURCE_SCHEMA = "leanmill.axiom_pack_band_source.v1"
BAND_CARRIER_SIZE = 3
BAND_MAX_INTERPRETATIONS = 100_000

_CANDIDATE_SPECS = (
    (
        "endpoint_repeat_delete",
        "xyx",
        "xy",
        "same_support_endpoint_recurrence",
        (2, 4),
        ("delete_repeat",),
    ),
    (
        "interior_swap_same_endpoints",
        "xyzx",
        "xzyx",
        "same_support_interior_interchange",
        (4, 6),
        ("swap_interior",),
    ),
    (
        "opposite_endpoint_repeat_delete",
        "xyx",
        "yx",
        "same_support_opposite_orientation",
        (2, 4),
        ("delete_repeat", "reverse_orientation"),
    ),
)

_CONTROL_SPECS = (
    ("control_semilattice", "xy", "yx"),
    ("control_left_zero", "xy", "x"),
    ("control_right_zero", "xy", "y"),
    ("control_singleton", "x", "y"),
)

_RETAINED_WITNESS_SPECS = (
    ("retain_noncommutative_model", "xy", "yx"),
    ("retain_non_left_zero_model", "xy", "x"),
    ("retain_non_right_zero_model", "xy", "y"),
    ("retain_nonsingleton_model", "x", "y"),
)

_WORD_HELDOUT_SPECS = (
    ("heldout_first_occurrence_long", "long_repeat_deletion", "xyzwxy", "xyzw"),
    ("heldout_contextual_repeat_deletion", "contextual_repeat_deletion", "uxvyxw", "uxvyw"),
    ("heldout_reverse_product_absorption", "reverse_product_absorption", "xyyx", "xy"),
    ("heldout_nested_sandwich_reduction", "nested_repeat_deletion", "xyxzw", "xyzw"),
    (
        "heldout_contextual_interior_interchange",
        "contextual_interior_interchange",
        "uxyzxv",
        "uxzyxv",
    ),
    ("heldout_contextual_endpoint_reduction", "contextual_endpoint_reduction", "uxyxzxv", "uxyzxv"),
    ("heldout_dual_orientation", "orientation_control", "xyzx", "yzx"),
)


def _mul(left: Term, right: Term) -> Term:
    return Term.app("mul", left, right)


def _word(letters: str) -> Term:
    if not letters:
        raise ValueError("a band word cannot be empty")
    result = Term.var(letters[0])
    for letter in letters[1:]:
        result = _mul(result, Term.var(letter))
    return result


def _binders(letters: str) -> tuple[Binder, ...]:
    return tuple(Binder(letter, "B") for letter in dict.fromkeys(letters))


def _word_axiom(name: str, left: str, right: str) -> AxiomFormula:
    return AxiomFormula(
        name,
        Formula.forall(
            _binders(left + right),
            Formula.eq(_word(left), _word(right)),
        ),
    )


def _band_signature() -> TheorySignature:
    return TheorySignature(
        name="FiniteBand",
        sorts=(SortDecl("B"),),
        operations=(OperationSymbol("mul", ("B", "B"), "B"),),
    )


def _band_base_axioms() -> tuple[AxiomFormula, ...]:
    x, y, z = Term.var("x"), Term.var("y"), Term.var("z")
    return (
        AxiomFormula(
            "mul_assoc",
            Formula.forall(
                _binders("xyz"),
                Formula.eq(_mul(_mul(x, y), z), _mul(x, _mul(y, z))),
            ),
        ),
        AxiomFormula(
            "mul_idempotent",
            Formula.forall(_binders("x"), Formula.eq(_mul(x, x), x)),
        ),
    )


def _candidate_axioms() -> tuple[AxiomFormula, ...]:
    return tuple(
        _word_axiom(name, left, right)
        for name, left, right, *_metadata in _CANDIDATE_SPECS
    )


def _candidate_templates(
    candidates: Sequence[AxiomFormula],
) -> list[dict[str, Any]]:
    metadata = {
        name: (family, word_range, operations)
        for name, _left, _right, family, word_range, operations in _CANDIDATE_SPECS
    }
    return [
        {
            "name": axiom.name,
            "formula": axiom.formula.to_json(),
            "statement": f"Typed short-word seed for {family.replace('_', ' ')}.",
            "family": family,
            "generation_contract": {
                "word_length_range": list(word_range),
                "operations": list(operations),
                "same_variable_support": True,
                "symmetry_closure": ["variable_renaming", "word_reversal"],
                "exclude_heldout_alpha_equivalents": True,
            },
        }
        for axiom in candidates
        for family, word_range, operations in (metadata[axiom.name],)
    ]


def _collapse_controls() -> tuple[AxiomFormula, ...]:
    return tuple(
        _word_axiom(name, left, right) for name, left, right in _CONTROL_SPECS
    )


def _retained_model_constraints() -> tuple[AxiomFormula, ...]:
    return tuple(
        AxiomFormula(
            name,
            Formula.exists(
                _binders(left + right),
                Formula.negate(Formula.eq(_word(left), _word(right))),
            ),
        )
        for name, left, right in _RETAINED_WITNESS_SPECS
    )


def _retained_model_bounds() -> FiniteSearchBounds:
    return FiniteSearchBounds(
        min_carrier_size=BAND_CARRIER_SIZE,
        max_carrier_size=BAND_CARRIER_SIZE,
        max_interpretations=BAND_MAX_INTERPRETATIONS,
    )


@dataclass(frozen=True)
class BandHeldoutTask:
    task_id: str
    family: str
    formula: AxiomFormula
    budget_units: int = 1_200
    split: str = "eval"
    schema: str = BAND_HELDOUT_TASK_SCHEMA

    def _input_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "task_id": self.task_id,
            "family": self.family,
            "formula": self.formula.to_json(),
        }

    @property
    def input_digest(self) -> str:
        return "sha256:" + content_hash(self._input_payload())

    def to_shadow_task(self) -> ShadowTask:
        return ShadowTask(
            task_id=self.task_id,
            input_digest=self.input_digest,
            budget_units=self.budget_units,
            split=self.split,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            **self._input_payload(),
            "input_digest": self.input_digest,
            "budget_units": self.budget_units,
            "budget_kind": "tokens",
            "split": self.split,
        }


def _implication_task(
    task_id: str,
    family: str,
    antecedent: Formula,
    consequent: Formula,
    letters: str,
) -> BandHeldoutTask:
    return BandHeldoutTask(
        task_id=task_id,
        family=family,
        formula=AxiomFormula(
            task_id,
            Formula.forall(_binders(letters), Formula.implies(antecedent, consequent)),
        ),
    )


def _heldout_tasks() -> tuple[BandHeldoutTask, ...]:
    x, y = Term.var("x"), Term.var("y")
    tasks = [
        BandHeldoutTask(name, family, _word_axiom(name, left, right))
        for name, family, left, right in _WORD_HELDOUT_SPECS
    ]
    tasks.extend(
        (
            _implication_task(
                "heldout_prefix_order_antisymmetry",
                "prefix_order",
                Formula.conjunction(
                    Formula.eq(_mul(x, y), y),
                    Formula.eq(_mul(y, x), x),
                ),
                Formula.eq(x, y),
                "xy",
            ),
            _implication_task(
                "heldout_prefix_order_left_monotone",
                "prefix_order",
                Formula.eq(_mul(x, y), y),
                Formula.eq(_word("zxzy"), _word("zy")),
                "xyz",
            ),
        )
    )
    return tuple(tasks)


def _blueprint(
    signature: TheorySignature,
    base_axioms: Sequence[AxiomFormula],
    candidate: AxiomFormula,
) -> AxiomPackBlueprint:
    controls = tuple(axiom.name for axiom in _collapse_controls())
    policy = {
        **DEFAULT_CHEAP_FILTER_POLICY,
        "max_finite_carrier_size": BAND_CARRIER_SIZE,
        "semantic_min_carrier_size": BAND_CARRIER_SIZE,
        "semantic_max_carrier_size": BAND_CARRIER_SIZE,
        "semantic_max_interpretations": BAND_MAX_INTERPRETATIONS,
        "required_retained_model_size": BAND_CARRIER_SIZE,
        "excluded_collapse_controls": list(controls),
    }
    return AxiomPackBlueprint(
        name=f"finite_band_causal_pilot_{candidate.name}",
        domain="finite_band_subvarieties",
        nl_statement=(
            "Propose short conditional laws over an associative idempotent binary operation, "
            "then test whether they help on separately frozen sibling tasks."
        ),
        semantic_intent=(
            "Measure attributable proof-task lift while retaining a noncollapsed three-element "
            "band and keeping the pilot quarantined."
        ),
        target_structure_family="finite bands with one binary operation",
        current_theory="associative idempotent magmas",
        residuals=[
            "long word reductions require repeated local rewrites",
            "orientation-sensitive consequences are easy to conflate",
            "strong short laws can collapse the finite model class",
        ],
        forbidden_shortcuts=[
            "Do not add a held-out formula or an alpha-equivalent restatement as a candidate.",
            "Do not treat finite-model survival as proof credit.",
            "Do not run downstream yield before the size-three retained-model check passes.",
            "Do not merge reversal-dual task outcomes.",
        ],
        candidate_axiom_templates=_candidate_templates((candidate,)),
        theory_signature=signature.to_json(),
        base_axioms=[axiom.to_json() for axiom in base_axioms],
        base_theory_resolved=True,
        cheap_filter_policy=policy,
        provenance=["leanmill_finite_band_quarantined_pilot_design"],
    )


@dataclass(frozen=True)
class BandPilotDesign:
    blueprints: tuple[AxiomPackBlueprint, ...]
    signature: TheorySignature
    base_axioms: tuple[AxiomFormula, ...]
    candidate_axioms: tuple[AxiomFormula, ...]
    heldout_tasks: tuple[BandHeldoutTask, ...]
    collapse_controls: tuple[AxiomFormula, ...]
    retained_model_constraints: tuple[AxiomFormula, ...]
    retained_model_bounds: FiniteSearchBounds
    schema: str = BAND_PILOT_SCHEMA

    def __post_init__(self) -> None:
        validate_axioms(
            self.signature,
            (
                *self.base_axioms,
                *self.candidate_axioms,
                *self.collapse_controls,
                *self.retained_model_constraints,
                *(task.formula for task in self.heldout_tasks),
            ),
        )
        if (
            self.retained_model_bounds.min_carrier_size != BAND_CARRIER_SIZE
            or self.retained_model_bounds.max_carrier_size != BAND_CARRIER_SIZE
        ):
            raise ValueError("the band pilot requires an exact size-three retained model")

    @property
    def base_theory_digest(self) -> str:
        return theory_content_hash(self.signature, self.base_axioms)

    @property
    def shadow_tasks(self) -> tuple[ShadowTask, ...]:
        return tuple(task.to_shadow_task() for task in self.heldout_tasks)

    def proposer_brief(self) -> dict[str, Any]:
        """Return the deanchored proposer view, excluding operator-only surfaces."""

        core = {
            "schema": BAND_PROPOSER_BRIEF_SCHEMA,
            "purpose": "candidate_generation_only",
            "operator_only_surfaces_exposed": False,
            "base_theory": {
                "content_frozen": True,
                "signed_receipt_present": False,
                "digest": self.base_theory_digest,
                "signature": self.signature.to_json(),
                "axioms": [axiom.to_json() for axiom in self.base_axioms],
            },
            "residual_class": "finite_band_short_word_rewrite_compression",
            "proposal_source_refs": sorted(self.source_catalog()),
            "generation_grammar": {
                "formula_kind": "universally_quantified_word_equality",
                "word_length_range": [2, 6],
                "max_distinct_variables": 4,
                "same_variable_support": True,
                "allowed_edits": ["delete_one_repeat", "permute_two_interior_occurrences"],
                "symmetry_closure": ["variable_renaming", "word_reversal"],
                "target_overlap_check": "external_fail_closed",
            },
        }
        return {**core, "brief_digest": "sha256:" + content_hash(core)}

    def source_catalog(self) -> dict[str, dict[str, Any]]:
        """Frozen structural sources that an agent may reference by identity."""

        source = {
            "schema": BAND_SOURCE_SCHEMA,
            "ref": "finite_band_short_word_rewrite",
            "base_theory_digest": self.base_theory_digest,
            "residual_class": "finite_band_short_word_rewrite_compression",
            "generation_grammar": {
                "formula_kind": "universally_quantified_word_equality",
                "word_length_range": [2, 6],
                "max_distinct_variables": 4,
                "same_variable_support": True,
                "allowed_edits": ["delete_one_repeat", "permute_two_interior_occurrences"],
            },
        }
        return {str(source["ref"]): source}

    def retained_model_probe_axiom(self, candidate: AxiomFormula) -> AxiomFormula:
        """Build a closed stress query without modifying the candidate pack."""

        if candidate.content_hash not in {
            item.content_hash for item in self.candidate_axioms
        }:
            raise ValueError("retained-model probes require a declared family candidate")
        return AxiomFormula(
            f"stress_probe_{candidate.name}",
            Formula.conjunction(
                candidate.formula,
                *(constraint.formula for constraint in self.retained_model_constraints),
            ),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": "quarantined_design",
            "experiment_executed": False,
            "benchmark_result": False,
            "novelty_result": False,
            "candidate_family_blueprints": [
                blueprint.to_json() for blueprint in self.blueprints
            ],
            "base_theory_digest": self.base_theory_digest,
            "heldout_manifest_requirement": {
                "required_before_candidate_generation": True,
                "signed_manifest_present": False,
                "candidate_pack_bound": False,
                "tasks": [task.to_json() for task in self.heldout_tasks],
            },
            "collapse_controls": [axiom.to_json() for axiom in self.collapse_controls],
            "retained_model_requirement": {
                "status": "required_not_run",
                "constraint_role": "stress_only_conjunction",
                "part_of_base_theory": False,
                "part_of_candidate_pack": False,
                "exact_carrier_size": BAND_CARRIER_SIZE,
                "bounds": self.retained_model_bounds.to_json(),
                "constraints": [
                    axiom.to_json() for axiom in self.retained_model_constraints
                ],
                "excluded_controls": [axiom.name for axiom in self.collapse_controls],
            },
        }


def finite_band_pilot_design() -> BandPilotDesign:
    """Construct the deterministic, quarantined finite-band pilot design."""

    signature = _band_signature()
    base_axioms = _band_base_axioms()
    candidate_axioms = _candidate_axioms()
    return BandPilotDesign(
        blueprints=tuple(
            _blueprint(signature, base_axioms, candidate)
            for candidate in candidate_axioms
        ),
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        heldout_tasks=_heldout_tasks(),
        collapse_controls=_collapse_controls(),
        retained_model_constraints=_retained_model_constraints(),
        retained_model_bounds=_retained_model_bounds(),
    )


def _word_from_term(term: Term) -> tuple[str, ...] | None:
    if term.kind == "var":
        return (term.name,)
    if term.kind != "app" or term.name != "mul" or len(term.args) != 2:
        return None
    left = _word_from_term(term.args[0])
    right = _word_from_term(term.args[1])
    return None if left is None or right is None else left + right


def _delete_one_repeat(longer: tuple[str, ...], shorter: tuple[str, ...]) -> bool:
    if len(longer) != len(shorter) + 1:
        return False
    for index, item in enumerate(longer):
        if item in longer[:index] + longer[index + 1 :] and longer[:index] + longer[index + 1 :] == shorter:
            return True
    return False


def _interior_swap(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    if len(left) != len(right) or len(left) < 4 or left[0] != right[0] or left[-1] != right[-1]:
        return False
    changed = [index for index in range(1, len(left) - 1) if left[index] != right[index]]
    return (
        len(changed) == 2
        and left[changed[0]] == right[changed[1]]
        and left[changed[1]] == right[changed[0]]
    )


def validate_band_candidate_axiom(
    candidate: AxiomFormula | Mapping[str, Any],
    *,
    design: BandPilotDesign | None = None,
) -> None:
    """Enforce the pre-registered finite-band generation population in host code."""

    pilot = design or finite_band_pilot_design()
    axiom = candidate if isinstance(candidate, AxiomFormula) else AxiomFormula.from_json(candidate)
    validate_axioms(pilot.signature, (axiom,))
    formula = axiom.formula
    if formula.kind != "forall" or len(formula.formulas) != 1 or formula.formulas[0].kind != "eq":
        raise ValueError("candidate must be a universally quantified word equality")
    equality = formula.formulas[0]
    left = _word_from_term(equality.terms[0])
    right = _word_from_term(equality.terms[1])
    if left is None or right is None:
        raise ValueError("candidate terms must be words over mul")
    if not (2 <= len(left) <= 6 and 2 <= len(right) <= 6):
        raise ValueError("candidate word lengths must be in [2, 6]")
    if set(left) != set(right) or len(set(left)) > 4:
        raise ValueError("candidate must preserve support with at most four variables")
    if not (_delete_one_repeat(left, right) or _delete_one_repeat(right, left) or _interior_swap(left, right)):
        raise ValueError("candidate is outside the registered rewrite grammar")
    forbidden = {
        item.semantic_hash
        for item in (*pilot.base_axioms, *pilot.collapse_controls, *(task.formula for task in pilot.heldout_tasks))
    }
    if axiom.semantic_hash in forbidden:
        raise ValueError("candidate duplicates a base, control, or heldout law")


def build_band_heldout_manifest(
    *,
    admission_digests: Mapping[str, str],
    private_key_pem: str,
    verifier_ref: str,
    manifest_evidence_ref: str,
    design: BandPilotDesign | None = None,
) -> dict[str, Any]:
    """Freeze the held-out tasks through the shared signed manifest contract."""

    pilot = design or finite_band_pilot_design()
    return build_shadow_task_manifest(
        tasks=pilot.shadow_tasks,
        base_theory_digest=pilot.base_theory_digest,
        admission_digests=admission_digests,
        private_key_pem=private_key_pem,
        verifier_ref=verifier_ref,
        manifest_evidence_ref=manifest_evidence_ref,
    )


def build_band_preregistration(
    *,
    admission_digests: Mapping[str, str],
    private_key_pem: str,
    verifier_ref: str,
    manifest_evidence_ref: str,
    design: BandPilotDesign | None = None,
) -> dict[str, Any]:
    """Create the operator packet and separate proposer view for the band pilot."""

    pilot = design or finite_band_pilot_design()
    manifest = build_band_heldout_manifest(
        admission_digests=admission_digests,
        private_key_pem=private_key_pem,
        verifier_ref=verifier_ref,
        manifest_evidence_ref=manifest_evidence_ref,
        design=pilot,
    )
    proposer_view = pilot.proposer_brief()
    operator_core = {
        "schema": BAND_PREREGISTRATION_SCHEMA,
        "status": "pre_registered",
        "experiment_executed": False,
        "novelty_result": False,
        "design": pilot.to_json(),
        "manifest": manifest,
        "task_count": len(pilot.heldout_tasks),
        "task_family_count": len({task.family for task in pilot.heldout_tasks}),
        "proposer_view_digest": "sha256:" + content_hash(proposer_view),
    }
    return {
        **operator_core,
        "operator_packet": operator_core,
        "proposer_view": proposer_view,
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }


def rank_band_heldout_tasks(
    *,
    committee: Sequence[Any],
    predict: Callable[[Any, ShadowTask], Hashable],
    size_fn: Callable[[Any], int],
    previously_observed_task_ids: Iterable[str] = (),
    weights: tuple[float, float, float] = (1.0, 1.0, 1.0),
    design: BandPilotDesign | None = None,
) -> dict[str, Any]:
    """Price held-out tasks through the shared information-yield adapter."""

    pilot = design or finite_band_pilot_design()
    return rank_shadow_tasks(
        committee=committee,
        tasks=pilot.shadow_tasks,
        predict=predict,
        size_fn=size_fn,
        previously_observed_task_ids=previously_observed_task_ids,
        weights=weights,
    )


__all__ = [
    "BAND_CARRIER_SIZE",
    "BAND_HELDOUT_TASK_SCHEMA",
    "BAND_MAX_INTERPRETATIONS",
    "BAND_PILOT_SCHEMA",
    "BAND_PREREGISTRATION_SCHEMA",
    "BAND_PROPOSER_BRIEF_SCHEMA",
    "BAND_SOURCE_SCHEMA",
    "BandHeldoutTask",
    "BandPilotDesign",
    "build_band_heldout_manifest",
    "build_band_preregistration",
    "finite_band_pilot_design",
    "rank_band_heldout_tasks",
    "validate_band_candidate_axiom",
]
