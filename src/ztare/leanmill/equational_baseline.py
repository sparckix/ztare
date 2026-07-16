"""Cheap, deterministic deduction baseline for universally quantified equations."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterator, Mapping, Sequence

from ztare.leanmill.theory_ir import AxiomFormula, Term, content_hash


_GROWTH_POLICY = "root_or_direct_child_with_target_subterms"
_CLOSED_GROWTH_POLICY = "root_or_direct_child"
_MAX_FRESH_VARIABLES_PER_REWRITE = 2
_MAX_INSTANTIATION_TERMS = 16
_SHALLOW_INSTANTIATION_STEPS = 2
_SHALLOW_INSTANTIATION_STATES = 256


@dataclass(frozen=True)
class DirectRewriteWitness:
    carrier_premise_hash: str
    rewrite_premise_hash: str
    rewritten_side: str
    rewrite_orientation: str
    subterm_path: tuple[int, ...]
    target_hash: str
    schema: str = "leanmill.direct_equational_rewrite.v1"

    def to_json(self) -> dict[str, object]:
        core = {
            "schema": self.schema,
            "carrier_premise_hash": self.carrier_premise_hash,
            "rewrite_premise_hash": self.rewrite_premise_hash,
            "rewritten_side": self.rewritten_side,
            "rewrite_orientation": self.rewrite_orientation,
            "subterm_path": list(self.subterm_path),
            "target_hash": self.target_hash,
        }
        return {**core, "receipt_sha256": content_hash(core)}


@dataclass(frozen=True)
class SubstitutionInstanceWitness:
    premise_hash: str
    target_hash: str
    target_side_order: str
    substitution: Mapping[str, object]
    schema: str = "leanmill.equational_substitution_instance.v1"

    def to_json(self) -> dict[str, object]:
        core = {
            "schema": self.schema,
            "premise_hash": self.premise_hash,
            "target_hash": self.target_hash,
            "target_side_order": self.target_side_order,
            "substitution": dict(sorted(self.substitution.items())),
        }
        return {**core, "receipt_sha256": content_hash(core)}


@dataclass(frozen=True)
class BoundedRewriteReductionWitness:
    target_hash: str
    steps: tuple[Mapping[str, object], ...]
    normal_form: Mapping[str, object]
    max_steps: int
    max_states_per_side: int
    explored_left_states: int
    explored_right_states: int
    growth_policy: str = _GROWTH_POLICY
    schema: str = "leanmill.bounded_equational_reduction.v3"

    def to_json(self) -> dict[str, object]:
        core = {
            "schema": self.schema,
            "target_hash": self.target_hash,
            "steps": [dict(row) for row in self.steps],
            "normal_form": dict(self.normal_form),
            "max_steps": self.max_steps,
            "max_states_per_side": self.max_states_per_side,
            "explored_left_states": self.explored_left_states,
            "explored_right_states": self.explored_right_states,
            "growth_policy": self.growth_policy,
        }
        return {**core, "receipt_sha256": content_hash(core)}


@dataclass(frozen=True)
class BoundedRewriteSearchReceipt:
    target_hash: str
    status: str
    max_steps: int
    max_states_per_side: int
    explored_left_states: int
    explored_right_states: int
    saturated_sides: tuple[str, ...]
    growth_policy: str = _GROWTH_POLICY
    schema: str = "leanmill.bounded_equational_search.v2"

    def to_json(self) -> dict[str, object]:
        core = {
            "schema": self.schema,
            "target_hash": self.target_hash,
            "status": self.status,
            "max_steps": self.max_steps,
            "max_states_per_side": self.max_states_per_side,
            "explored_left_states": self.explored_left_states,
            "explored_right_states": self.explored_right_states,
            "saturated_sides": list(self.saturated_sides),
            "growth_policy": self.growth_policy,
            "claim_boundary": (
                "one join found inside the bounded rewrite graph"
                if self.status == "proved"
                else "bounded search saturation is inconclusive"
                if self.status == "state_cap_saturated"
                else "no join inside the fully explored bounded rewrite graph"
            ),
        }
        return {**core, "receipt_sha256": content_hash(core)}


@dataclass(frozen=True)
class EquationalConsequenceAnalysis:
    witness: (
        SubstitutionInstanceWitness
        | DirectRewriteWitness
        | BoundedRewriteReductionWitness
        | None
    )
    bounded_search: BoundedRewriteSearchReceipt | None = None


def _equation(axiom: AxiomFormula) -> tuple[Term, Term, Mapping[str, str]] | None:
    formula = axiom.formula
    sorts: dict[str, str] = {}
    while formula.kind == "forall":
        sorts.update({binder.name: binder.sort for binder in formula.binders})
        formula = formula.formulas[0]
    if formula.kind != "eq":
        return None
    return formula.terms[0], formula.terms[1], sorts


def _match(pattern: Term, value: Term, bindings: dict[str, Term]) -> bool:
    if pattern.kind == "var":
        prior = bindings.get(pattern.name)
        if prior is None:
            bindings[pattern.name] = value
            return True
        return prior == value
    if value.kind != "app" or pattern.name != value.name or len(pattern.args) != len(value.args):
        return False
    return all(_match(left, right, bindings) for left, right in zip(pattern.args, value.args, strict=True))


def _instantiate(template: Term, bindings: Mapping[str, Term]) -> Term | None:
    if template.kind == "var":
        return bindings.get(template.name)
    args: list[Term] = []
    for child in template.args:
        value = _instantiate(child, bindings)
        if value is None:
            return None
        args.append(value)
    return Term.app(template.name, *args)


def _variable_names(term: Term) -> tuple[str, ...]:
    names: dict[str, None] = {}

    def visit(value: Term) -> None:
        if value.kind == "var":
            names.setdefault(value.name, None)
            return
        for child in value.args:
            visit(child)

    visit(term)
    return tuple(names)


def _subterms(*terms: Term) -> tuple[Term, ...]:
    values: dict[Term, None] = {}

    def visit(value: Term) -> None:
        values.setdefault(value, None)
        for child in value.args:
            visit(child)

    for term in terms:
        visit(term)
    return tuple(values)[:_MAX_INSTANTIATION_TERMS]


def _instantiate_variants(
    template: Term,
    bindings: Mapping[str, Term],
    instantiation_terms: Sequence[Term],
) -> Iterator[Term]:
    """Instantiate variables absent from the matched orientation, within a finite pool."""

    missing = tuple(
        name for name in _variable_names(template) if name not in bindings
    )
    if len(missing) > _MAX_FRESH_VARIABLES_PER_REWRITE:
        return
    choices = product(instantiation_terms, repeat=len(missing)) if missing else ((),)
    for values in choices:
        completed = dict(bindings)
        completed.update(zip(missing, values, strict=True))
        instantiated = _instantiate(template, completed)
        if instantiated is not None:
            yield instantiated


def _term_json(term: Term) -> dict[str, object]:
    return term.to_json()


def _single_sorted(*sort_maps: Mapping[str, str]) -> bool:
    return len({sort_name for sorts in sort_maps for sort_name in sorts.values()}) == 1


def substitution_instance_witness(
    premise: AxiomFormula,
    target: AxiomFormula,
) -> SubstitutionInstanceWitness | None:
    """Receipt a target that is a direct substitution instance of one premise."""

    premise_equation = _equation(premise)
    target_equation = _equation(target)
    if premise_equation is None or target_equation is None:
        return None
    premise_left, premise_right, premise_sorts = premise_equation
    target_left, target_right, target_sorts = target_equation
    if not _single_sorted(premise_sorts, target_sorts):
        # Term nodes do not carry inferred sorts, so cross-sort substitutions
        # cannot yet be checked without the surrounding signature.
        return None
    for side_order, candidate_left, candidate_right in (
        ("as_declared", target_left, target_right),
        ("swapped", target_right, target_left),
    ):
        bindings: dict[str, Term] = {}
        if not _match(premise_left, candidate_left, bindings):
            continue
        if not _match(premise_right, candidate_right, bindings):
            continue
        return SubstitutionInstanceWitness(
            premise_hash=premise.semantic_hash,
            target_hash=target.semantic_hash,
            target_side_order=side_order,
            substitution={name: _term_json(value) for name, value in bindings.items()},
        )
    return None


def _one_step_rewrites(
    value: Term,
    pattern: Term,
    replacement: Term,
    *,
    path: tuple[int, ...] = (),
    instantiation_terms: Sequence[Term] = (),
) -> Iterator[tuple[Term, tuple[int, ...]]]:
    bindings: dict[str, Term] = {}
    if _match(pattern, value, bindings):
        for rewritten in _instantiate_variants(
            replacement, bindings, instantiation_terms
        ):
            if rewritten != value:
                yield rewritten, path
    if value.kind != "app":
        return
    for index, child in enumerate(value.args):
        for rewritten_child, child_path in _one_step_rewrites(
            child,
            pattern,
            replacement,
            path=path + (index,),
            instantiation_terms=instantiation_terms,
        ):
            args = list(value.args)
            args[index] = rewritten_child
            yield Term.app(value.name, *args), child_path


def _canonical_equation(
    left: Term,
    right: Term,
    sorts: Mapping[str, str],
) -> tuple[object, ...]:
    def orientation(first: Term, second: Term) -> tuple[object, ...]:
        names: dict[str, int] = {}

        def term(value: Term) -> tuple[object, ...]:
            if value.kind == "var":
                if value.name not in names:
                    names[value.name] = len(names)
                return ("var", names[value.name], sorts.get(value.name, ""))
            return ("app", value.name, tuple(term(child) for child in value.args))

        return (term(first), term(second))

    return min(orientation(left, right), orientation(right, left))


def direct_joint_rewrite_witness(
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
) -> DirectRewriteWitness | None:
    """Return a witness when two distinct premises yield target in one rewrite."""

    if len(premises) < 2:
        return None
    target_equation = _equation(target)
    if target_equation is None:
        return None
    target_left, target_right, target_sorts = target_equation
    target_canonical = _canonical_equation(target_left, target_right, target_sorts)
    parsed = [_equation(premise) for premise in premises]
    declared_sorts = set(target_sorts.values())
    for equation in parsed:
        if equation is not None:
            declared_sorts.update(equation[2].values())
    if len(declared_sorts) != 1:
        # Term nodes do not carry inferred result sorts. Stay conservative until
        # a signature-aware matcher can prove a many-sorted rewrite is typed.
        return None
    for carrier_index, carrier in enumerate(parsed):
        if carrier is None:
            continue
        carrier_left, carrier_right, carrier_sorts = carrier
        for rewrite_index, rule in enumerate(parsed):
            if carrier_index == rewrite_index or rule is None:
                continue
            rule_left, rule_right, _rule_sorts = rule
            for orientation, pattern, replacement in (
                ("left_to_right", rule_left, rule_right),
                ("right_to_left", rule_right, rule_left),
            ):
                for side_index, side in enumerate((carrier_left, carrier_right)):
                    term_pool = _subterms(
                        target_left, target_right, carrier_left, carrier_right
                    )
                    for rewritten, path in _one_step_rewrites(
                        side,
                        pattern,
                        replacement,
                        instantiation_terms=term_pool,
                    ):
                        result_left, result_right = (
                            (rewritten, carrier_right)
                            if side_index == 0
                            else (carrier_left, rewritten)
                        )
                        if _canonical_equation(
                            result_left, result_right, carrier_sorts
                        ) != target_canonical:
                            continue
                        return DirectRewriteWitness(
                            carrier_premise_hash=premises[carrier_index].semantic_hash,
                            rewrite_premise_hash=premises[rewrite_index].semantic_hash,
                            rewritten_side="left" if side_index == 0 else "right",
                            rewrite_orientation=orientation,
                            subterm_path=path,
                            target_hash=target.semantic_hash,
                        )
    return None


def _term_units(term: Term) -> int:
    return 1 + sum(_term_units(child) for child in term.args)


def bounded_equational_reduction_analysis(
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
    *,
    max_steps: int = 8,
    max_states_per_side: int = 4_096,
    instantiate_fresh_variables: bool = True,
) -> EquationalConsequenceAnalysis:
    """Join target sides or receipt why the bounded search is inconclusive."""

    if max_steps < 1 or max_states_per_side < 2:
        raise ValueError("bounded equational reduction requires positive bounds")
    target_equation = _equation(target)
    parsed = tuple(
        (premise, _equation(premise)) for premise in premises
    )
    if target_equation is None or any(equation is None for _premise, equation in parsed):
        return EquationalConsequenceAnalysis(None)
    target_left, target_right, target_sorts = target_equation
    declared_sorts = set(target_sorts.values())
    for _premise, equation in parsed:
        assert equation is not None
        declared_sorts.update(equation[2].values())
    if len(declared_sorts) != 1:
        return EquationalConsequenceAnalysis(None)

    max_term_units = max(32, _term_units(target_left) + _term_units(target_right) + 4 * max_steps)
    InternalStep = tuple[str, str, tuple[int, ...], Term]
    left_paths: dict[Term, tuple[InternalStep, ...]] = {target_left: ()}
    right_paths: dict[Term, tuple[InternalStep, ...]] = {target_right: ()}
    left_frontier: tuple[Term, ...] = (target_left,)
    right_frontier: tuple[Term, ...] = (target_right,)

    def expand(
        frontier: tuple[Term, ...],
        paths: dict[Term, tuple[InternalStep, ...]],
    ) -> tuple[tuple[Term, ...], bool]:
        candidates: dict[
            Term,
            tuple[
                tuple[int, int, int, str, str, tuple[int, ...]],
                tuple[InternalStep, ...],
            ],
        ] = {}
        for value in frontier:
            prefix = paths[value]
            value_units = _term_units(value)
            term_pool = (
                _subterms(target_left, target_right, value)
                if instantiate_fresh_variables
                else ()
            )
            for premise, equation in parsed:
                assert equation is not None
                rule_left, rule_right, _rule_sorts = equation
                for orientation, pattern, replacement in (
                    ("left_to_right", rule_left, rule_right),
                    ("right_to_left", rule_right, rule_left),
                ):
                    for rewritten, path in _one_step_rewrites(
                        value,
                        pattern,
                        replacement,
                        instantiation_terms=term_pool,
                    ):
                        rewritten_units = _term_units(rewritten)
                        if rewritten_units > value_units and len(path) > 1:
                            # Variable-to-large-term equations otherwise expand
                            # independently at every deep subterm and make a cheap
                            # negative check more expensive than its boundary.
                            continue
                        if rewritten in paths or rewritten_units > max_term_units:
                            continue
                        step_path = prefix + (
                            (
                                premise.semantic_hash,
                                orientation,
                                path,
                                rewritten,
                            ),
                        )
                        priority = (
                            max(0, rewritten_units - value_units),
                            rewritten_units,
                            len(path),
                            premise.semantic_hash,
                            orientation,
                            path,
                        )
                        prior = candidates.get(rewritten)
                        if prior is None or priority < prior[0]:
                            candidates[rewritten] = (priority, step_path)
        room = max(0, max_states_per_side - len(paths))
        ordered = sorted(candidates.items(), key=lambda item: item[1][0])
        next_frontier: list[Term] = []
        for rewritten, (_priority, step_path) in ordered[:room]:
            paths[rewritten] = step_path
            next_frontier.append(rewritten)
        return tuple(next_frontier), len(ordered) > room

    meeting: Term | None = target_left if target_left == target_right else None
    saturated_sides: set[str] = set()
    for _depth in range(max_steps):
        if meeting is not None:
            break
        expand_left = bool(left_frontier) and (
            not right_frontier or len(left_frontier) <= len(right_frontier)
        )
        if expand_left:
            left_frontier, saturated = expand(left_frontier, left_paths)
            if saturated:
                saturated_sides.add("left")
            candidates = (value for value in left_frontier if value in right_paths)
        else:
            right_frontier, saturated = expand(right_frontier, right_paths)
            if saturated:
                saturated_sides.add("right")
            candidates = (value for value in right_frontier if value in left_paths)
        meeting = next(
            (
                value
                for value in candidates
                if len(left_paths[value]) + len(right_paths[value]) <= max_steps
            ),
            None,
        )
        if not left_frontier and not right_frontier:
            break

    search_status = (
        "proved"
        if meeting is not None
        else "state_cap_saturated"
        if saturated_sides
        else "exhausted_no_join"
    )
    search_receipt = BoundedRewriteSearchReceipt(
        target_hash=target.semantic_hash,
        status=search_status,
        max_steps=max_steps,
        max_states_per_side=max_states_per_side,
        explored_left_states=len(left_paths),
        explored_right_states=len(right_paths),
        saturated_sides=tuple(sorted(saturated_sides)),
        growth_policy=(
            _GROWTH_POLICY
            if instantiate_fresh_variables
            else _CLOSED_GROWTH_POLICY
        ),
    )
    if meeting is None:
        return EquationalConsequenceAnalysis(None, search_receipt)
    left = target_left
    right = target_right
    receipt_steps: list[Mapping[str, object]] = []
    for side, path_steps in (
        ("left", left_paths[meeting]),
        ("right", right_paths[meeting]),
    ):
        for premise_hash, orientation, subterm_path, rewritten in path_steps:
            if side == "left":
                left = rewritten
            else:
                right = rewritten
            receipt_steps.append(
                {
                    "premise_hash": premise_hash,
                    "rewritten_side": side,
                    "rewrite_orientation": orientation,
                    "subterm_path": list(subterm_path),
                    "result_left": _term_json(left),
                    "result_right": _term_json(right),
                }
            )
    if not receipt_steps or left != right:
        return EquationalConsequenceAnalysis(None, search_receipt)
    witness = BoundedRewriteReductionWitness(
        target_hash=target.semantic_hash,
        steps=tuple(receipt_steps),
        normal_form=_term_json(meeting),
        max_steps=max_steps,
        max_states_per_side=max_states_per_side,
        explored_left_states=len(left_paths),
        explored_right_states=len(right_paths),
        growth_policy=(
            _GROWTH_POLICY
            if instantiate_fresh_variables
            else _CLOSED_GROWTH_POLICY
        ),
    )
    return EquationalConsequenceAnalysis(witness, search_receipt)


def bounded_equational_reduction_witness(
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
    *,
    max_steps: int = 8,
    max_states_per_side: int = 4_096,
) -> BoundedRewriteReductionWitness | None:
    """Compatibility wrapper returning only a positive reduction witness."""

    analysis = bounded_equational_reduction_analysis(
        premises,
        target,
        max_steps=max_steps,
        max_states_per_side=max_states_per_side,
    )
    witness = analysis.witness
    return witness if isinstance(witness, BoundedRewriteReductionWitness) else None


def direct_equational_consequence_analysis(
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
) -> EquationalConsequenceAnalysis:
    """Return the cheapest witness plus any bounded-search disposition."""

    # Non-equational background laws constrain the finite model class but are
    # not rewrite rules.  They must not disable deduction from the equational
    # fragment that accompanies them.
    equations = tuple(premise for premise in premises if _equation(premise) is not None)
    for premise in equations:
        witness = substitution_instance_witness(premise, target)
        if witness is not None:
            return EquationalConsequenceAnalysis(witness)
    direct = direct_joint_rewrite_witness(equations, target)
    if direct is not None:
        return EquationalConsequenceAnalysis(direct)
    shallow = bounded_equational_reduction_analysis(
        equations,
        target,
        max_steps=_SHALLOW_INSTANTIATION_STEPS,
        max_states_per_side=_SHALLOW_INSTANTIATION_STATES,
    )
    if shallow.witness is not None:
        return shallow
    return bounded_equational_reduction_analysis(
        equations,
        target,
        instantiate_fresh_variables=False,
    )


def direct_equational_consequence_witness(
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
) -> (
    SubstitutionInstanceWitness
    | DirectRewriteWitness
    | BoundedRewriteReductionWitness
    | None
):
    """Compatibility wrapper returning only a positive consequence witness."""

    return direct_equational_consequence_analysis(premises, target).witness


__all__ = [
    "BoundedRewriteReductionWitness",
    "BoundedRewriteSearchReceipt",
    "DirectRewriteWitness",
    "EquationalConsequenceAnalysis",
    "SubstitutionInstanceWitness",
    "bounded_equational_reduction_analysis",
    "bounded_equational_reduction_witness",
    "direct_equational_consequence_analysis",
    "direct_equational_consequence_witness",
    "direct_joint_rewrite_witness",
    "substitution_instance_witness",
]
