"""Industry-pressure to company-choice-system lowering for JaggedThoughts.

The operator language carries candidate strategic responses.  This adapter
recursively enumerates compatible bundles, evaluates their financial
consequences across declared industry scenarios, and exposes global and local
frontiers plus representation residuals.  It never infers evidence or effects
from the option prose.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.common.linear_preference_regions import compile_linear_preference_regions
from ztare.strategy import (
    CandidateEvaluation,
    ClaimDisposition,
    EnumerationResult,
    FrontierScope,
    Neighborhood,
    OperatorGrammar,
    PolicyCondition,
    RepresentationAudit,
    StrategicClaim,
    TypedOperator,
    TypedTerminal,
    build_typed_program,
    compile_policy_action_regions,
    compile_jaggedthoughts_frontier,
    compile_enumeration_result,
)
from ztare.strategy.jaggedthoughts import Program

from .contracts import (
    MetricObservation,
    canonical_timestamp,
    require_finite,
    require_text,
    timestamp_key,
)


PROFILE_SCHEMA = "jaggedthoughts-company-strategy-options-v1"
RESULT_SCHEMA = "jaggedthoughts-company-strategy-frontier-v1"
OBJECTIVES = (
    "earnings_durability",
    "growth",
    "capital_efficiency",
    "downside_resilience",
    "industry_pressure_coverage",
)
ECONOMIC_COORDINATES = (
    ("earnings_durability", "normalized_owner_earnings_retention"),
    ("growth", "forecast_growth"),
    ("capital_efficiency", "reinvestment_efficiency"),
    ("downside_resilience", "downside_owner_earnings_retention"),
)
MECHANISM_ACTIONS = frozenset({
    "commit_capacity", "diversify_scope", "expand_adjacent_scope",
    "focus_resources", "integrate_value_chain", "secure_access", "secure_supply",
})
MECHANISM_BRIDGES = frozenset(OBJECTIVES[:4])
IMPLEMENTATION_EVENT_KINDS = frozenset({
    "adoption", "announcement", "first_public_observation", "completion", "discontinuation",
})
IMPLEMENTATION_STATUSES = frozenset({"planned", "underway", "completed", "discontinued"})
IMPLEMENTATION_TIMING_PRECISIONS = frozenset({"date", "quarter", "year"})
IMPLEMENTATION_MODES = frozenset({
    "acquisition", "capacity_build", "divestiture", "organic_program",
    "partnership", "resource_reallocation", "supply_commitment", "other",
    "unspecified",
})
OUTCOME_ROLES = frozenset({"leading_operating", "terminal_operating"})
OUTCOME_ACQUISITION_MODES = frozenset({
    "point_in_time_observation", "subscription_primary_document",
})


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a nonempty list")
    if any(not isinstance(row, Mapping) for row in value):
        raise ValueError(f"{label} must contain mappings")
    return list(value)


def _refs(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a nonempty list")
    return tuple(sorted({require_text(item, label) for item in value}))


def _vector(value: Any, label: str, *, size: int = 4) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != size:
        raise ValueError(f"{label} must contain {size} objective deltas")
    return tuple(require_finite(item, label) for item in value)


def _option_ids(program: Program) -> tuple[str, ...]:
    if program.terminal_id is not None:
        return (program.terminal_id.removeprefix("option:"),)
    return tuple(sorted(option for child in program.children for option in _option_ids(child)))


def _expression(program: Program) -> str:
    if program.terminal_id is not None:
        return program.terminal_id.removeprefix("option:")
    return f"combine({_expression(program.children[0])}, {_expression(program.children[1])})"


def _feasibility_constraints(
    raw: Any, options: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], set[str]]:
    value = _mapping(raw or {}, "strategy feasibility_constraints")
    references: set[str] = set()
    incompatibilities = []
    incompatibility_ids: set[str] = set()
    for row in value.get("incompatibilities") or ():
        if not isinstance(row, Mapping):
            raise ValueError("strategy incompatibilities must contain mappings")
        constraint_id = require_text(row.get("constraint_id"), "incompatibility constraint_id")
        option_ids = sorted({str(item) for item in row.get("option_ids") or ()})
        if (
            constraint_id in incompatibility_ids
            or len(option_ids) != 2
            or not set(option_ids).issubset(options)
        ):
            raise ValueError(f"invalid strategy incompatibility: {constraint_id}")
        incompatibility_ids.add(constraint_id)
        refs = _refs(row.get("evidence_refs"), f"incompatibility {constraint_id} evidence_refs")
        references.update(refs)
        incompatibilities.append({
            "constraint_id": constraint_id, "option_ids": option_ids,
            "evidence_refs": list(refs), "authority": "dossier_bound",
        })
    prerequisites = []
    for index, row in enumerate(value.get("prerequisites") or ()):
        if not isinstance(row, Mapping):
            raise ValueError("strategy prerequisites must contain mappings")
        option_id = require_text(row.get("option_id"), "prerequisite option_id")
        required = sorted({str(item) for item in row.get("requires") or ()})
        if (
            option_id not in options or not required or option_id in required
            or not set(required).issubset(options)
        ):
            raise ValueError(f"strategy prerequisite {index} crosses the option vocabulary")
        refs = _refs(row.get("evidence_refs"), f"prerequisite {option_id} evidence_refs")
        references.update(refs)
        prerequisites.append({
            "constraint_id": str(row.get("constraint_id") or f"prerequisite:{option_id}"),
            "option_id": option_id, "requires": required,
            "evidence_refs": list(refs),
            "authority": "dossier_bound" if row.get("constraint_id") else "legacy_profile",
        })
    resources = []
    resource_ids: set[str] = set()
    for row in value.get("resources") or ():
        if not isinstance(row, Mapping):
            raise ValueError("strategy resources must contain mappings")
        resource_id = require_text(row.get("resource_id"), "strategy resource_id")
        if resource_id in resource_ids:
            raise ValueError(f"duplicate strategy resource_id: {resource_id}")
        resource_ids.add(resource_id)
        limit = require_finite(row.get("limit"), f"resource {resource_id} limit")
        uses = {
            str(option_id): require_finite(amount, f"resource {resource_id} use")
            for option_id, amount in _mapping(
                row.get("uses"), f"resource {resource_id} uses",
            ).items()
        }
        if limit < 0 or not uses or not set(uses).issubset(options) or any(
            amount < 0 for amount in uses.values()
        ):
            raise ValueError(f"resource {resource_id} requires nonnegative typed uses and limit")
        refs = _refs(row.get("evidence_refs"), f"resource {resource_id} evidence_refs")
        references.update(refs)
        resources.append({
            "constraint_id": str(row.get("constraint_id") or f"resource:{resource_id}"),
            "resource_id": resource_id,
            "unit": require_text(row.get("unit"), f"resource {resource_id} unit"),
            "limit": limit, "uses": dict(sorted(uses.items())),
            "evidence_refs": list(refs),
            "authority": "dossier_bound" if row.get("constraint_id") else "legacy_profile",
        })
    body = {
        "incompatibilities": sorted(incompatibilities, key=lambda row: row["constraint_id"]),
        "prerequisites": sorted(prerequisites, key=lambda row: row["option_id"]),
        "resources": sorted(resources, key=lambda row: row["resource_id"]),
    }
    return {**body, "feasibility_constraints_sha256": stable_sha256(body)}, references


def _compatible_choice_enumeration(
    *,
    grammar: OperatorGrammar,
    options: Mapping[str, Mapping[str, Any]],
    max_bundle_size: int,
    max_depth: int,
    max_programs: int,
    feasibility_constraints: Mapping[str, Any],
) -> tuple[EnumerationResult, dict[str, Any], list[dict[str, Any]]]:
    """Enumerate the associative/commutative option-set quotient with Z3."""
    import z3

    option_ids = tuple(sorted(options))
    if max_bundle_size < 1 or max_bundle_size > len(option_ids):
        raise ValueError("max_bundle_size must be between one and the option count")
    if max_bundle_size > 1 << max_depth:
        raise ValueError("max_depth cannot represent the declared maximum bundle size")
    legacy_incompatible_pairs: set[tuple[str, str]] = set()
    for option_id, option in options.items():
        for rival in option.get("incompatible_with") or ():
            rival_id = str(rival)
            if rival_id not in options or rival_id == option_id:
                raise ValueError(f"option {option_id} has invalid incompatibility {rival_id}")
            legacy_incompatible_pairs.add(tuple(sorted((option_id, rival_id))))
    typed_incompatible_pairs = {
        tuple(map(str, row["option_ids"]))
        for row in feasibility_constraints.get("incompatibilities") or ()
    }
    incompatible_pairs = legacy_incompatible_pairs | typed_incompatible_pairs

    variables = {option_id: z3.Bool(f"strategy_option_{index}") for index, option_id in enumerate(option_ids)}
    cardinality = z3.Sum([z3.If(variables[option_id], 1, 0) for option_id in option_ids])
    solver = z3.Solver()
    solver.add(cardinality >= 1, cardinality <= max_bundle_size)
    for left, right in sorted(incompatible_pairs):
        solver.add(z3.Not(z3.And(variables[left], variables[right])))
    for row in feasibility_constraints.get("prerequisites") or ():
        solver.add(z3.Implies(
            variables[str(row["option_id"])],
            z3.And(*(variables[str(option_id)] for option_id in row["requires"])),
        ))
    for row in feasibility_constraints.get("resources") or ():
        total = z3.Sum(*(
            z3.If(variables[option_id], z3.RealVal(str(amount)), z3.RealVal("0"))
            for option_id, amount in row["uses"].items()
        ))
        solver.add(total <= z3.RealVal(str(row["limit"])))

    bundles: list[tuple[str, ...]] = []
    while solver.check() == z3.sat:
        model = solver.model()
        selected = tuple(
            option_id for option_id in option_ids
            if z3.is_true(model.eval(variables[option_id], model_completion=True))
        )
        bundles.append(selected)
        if len(bundles) > max_programs:
            raise ValueError("max_programs is below the compatible option-set count")
        solver.add(z3.Or(*[
            variable != model.eval(variable, model_completion=True)
            for variable in variables.values()
        ]))
    if solver.check() == z3.unknown:
        raise RuntimeError(f"Z3 could not close the strategy choice space: {solver.reason_unknown()}")

    terminals = {
        option_id: build_typed_program(grammar, terminal_id=f"option:{option_id}")
        for option_id in option_ids
    }

    def program_for(bundle: tuple[str, ...]) -> Program:
        nodes = [terminals[option_id] for option_id in bundle]
        while len(nodes) > 1:
            next_nodes = []
            for index in range(0, len(nodes), 2):
                pair = nodes[index:index + 2]
                next_nodes.append(
                    pair[0] if len(pair) == 1 else build_typed_program(
                        grammar,
                        operator_id="combine_reinforcing_choices",
                        children=pair,
                    )
                )
            nodes = next_nodes
        return nodes[0]

    bundle_rows = tuple(sorted(set(bundles), key=lambda row: (len(row), row)))
    programs = tuple(program_for(bundle) for bundle in bundle_rows)
    enumeration = compile_enumeration_result(
        grammar,
        programs=programs,
        max_depth=max_depth,
        max_programs=max_programs,
    )
    feasible_bundle_set = set(bundle_rows)
    excluded_bundles = []
    for size in range(1, max_bundle_size + 1):
        for bundle in combinations(option_ids, size):
            if bundle in feasible_bundle_set:
                continue
            selected = set(bundle)
            violated = [
                f"incompatible:{left}:{right}"
                for left, right in sorted(incompatible_pairs)
                if {left, right}.issubset(selected)
            ]
            violated.extend(
                f"prerequisite:{row['option_id']}"
                for row in feasibility_constraints.get("prerequisites") or ()
                if str(row["option_id"]) in selected
                and not set(map(str, row["requires"])).issubset(selected)
            )
            violated.extend(
                f"resource:{row['resource_id']}"
                for row in feasibility_constraints.get("resources") or ()
                if sum(
                    Decimal(str(amount))
                    for option_id, amount in row["uses"].items()
                    if option_id in selected
                ) > Decimal(str(row["limit"]))
            )
            if not violated:
                raise RuntimeError("Z3 excluded a strategy bundle without a predicate witness")
            excluded_bundles.append({
                "option_ids": list(bundle),
                "violated_constraint_ids": sorted(set(violated)),
            })
    witnesses = []
    for left, right in sorted(incompatible_pairs):
        probe = z3.Solver()
        probe.set(unsat_core=True)
        labels = {
            "choice_nonempty": "choice_nonempty",
            "bundle_size": "bundle_size",
            **{
                f"incompatible_{index}": f"incompatible:{pair[0]}:{pair[1]}"
                for index, pair in enumerate(sorted(incompatible_pairs))
            },
        }
        probe.assert_and_track(cardinality >= 1, z3.Bool("choice_nonempty"))
        probe.assert_and_track(cardinality <= max_bundle_size, z3.Bool("bundle_size"))
        for index, pair in enumerate(sorted(incompatible_pairs)):
            probe.assert_and_track(
                z3.Not(z3.And(variables[pair[0]], variables[pair[1]])),
                z3.Bool(f"incompatible_{index}"),
            )
        probe.add(variables[left], variables[right])
        verdict = probe.check()
        if verdict != z3.unsat:
            raise RuntimeError("declared incompatible option pair was not solver-infeasible")
        witnesses.append({
            "kind": "incompatible_option_pair",
            "option_ids": [left, right],
            "reasons": [f"incompatible:{left}:{right}"],
            "unsat_core_constraint_ids": sorted(labels[str(label)] for label in probe.unsat_core()),
        })
    for index, row in enumerate(feasibility_constraints.get("prerequisites") or ()):
        option_id = str(row["option_id"])
        required = tuple(map(str, row["requires"]))
        probe = z3.Solver()
        probe.set(unsat_core=True)
        label = z3.Bool(f"prerequisite_{index}")
        probe.assert_and_track(
            z3.Implies(
                variables[option_id],
                z3.And(*(variables[item] for item in required)),
            ), label,
        )
        probe.add(variables[option_id], z3.Or(*(z3.Not(variables[item]) for item in required)))
        if probe.check() != z3.unsat:
            raise RuntimeError("declared prerequisite was not solver-infeasible when violated")
        witnesses.append({
            "kind": "missing_prerequisite", "option_ids": [option_id, *required],
            "reasons": [f"prerequisite:{option_id}:{item}" for item in required],
            "unsat_core_constraint_ids": [f"prerequisite:{option_id}"],
        })
    for index, row in enumerate(feasibility_constraints.get("resources") or ()):
        positive_uses = tuple(
            (str(option_id), Decimal(str(amount)))
            for option_id, amount in row["uses"].items()
            if Decimal(str(amount)) > 0
        )
        limit = Decimal(str(row["limit"]))
        violating = next((
            tuple(option_id for option_id, _amount in subset)
            for size in range(1, min(max_bundle_size, len(positive_uses)) + 1)
            for subset in combinations(positive_uses, size)
            if sum((amount for _option_id, amount in subset), Decimal(0)) > limit
        ), None)
        if violating is None:
            continue
        probe = z3.Solver()
        probe.set(unsat_core=True)
        label = z3.Bool(f"resource_{index}")
        total = z3.Sum(*(
            z3.If(variables[option_id], z3.RealVal(str(amount)), z3.RealVal("0"))
            for option_id, amount in row["uses"].items()
        ))
        probe.assert_and_track(total <= z3.RealVal(str(row["limit"])), label)
        probe.add(*(variables[option_id] for option_id in violating))
        if probe.check() != z3.unsat:
            raise RuntimeError("declared resource violation was not solver-infeasible")
        witnesses.append({
            "kind": "resource_limit", "option_ids": list(violating),
            "resource_id": row["resource_id"], "unit": row["unit"],
            "limit": row["limit"],
            "selected_use": float(sum(
                (Decimal(str(row["uses"][option_id])) for option_id in violating),
                Decimal(0),
            )),
            "reasons": [f"resource:{row['resource_id']}"],
            "unsat_core_constraint_ids": [f"resource:{row['resource_id']}"],
        })
    certificate_body = {
        "schema": "jaggedthoughts-compatible-choice-space-v1",
        "solver": {"name": "z3", "version": z3.get_version_string(), "logic": "QF_LIA/LRA+Bool"},
        "semantic_quotient": "nonempty_commutative_option_sets",
        "quotient_enforced_by": "specialized_set_enumerator_with_one_canonical_balanced_ast",
        "predicate_catalog": [
            {
                "predicate_id": "cardinality_ge",
                "input_types": ["ChoiceSet", "Integer"], "output_type": "Bool",
                "solver_lowering": "Sum(If(selected(option), 1, 0)) >= bound",
                "active_constraint_count": 1,
            },
            {
                "predicate_id": "cardinality_le",
                "input_types": ["ChoiceSet", "Integer"], "output_type": "Bool",
                "solver_lowering": "Sum(If(selected(option), 1, 0)) <= bound",
                "active_constraint_count": 1,
            },
            {
                "predicate_id": "not_all_selected",
                "input_types": ["Option", "Option"], "output_type": "Bool",
                "solver_lowering": "Not(And(selected(left), selected(right)))",
                "active_constraint_count": len(incompatible_pairs),
            },
            {
                "predicate_id": "implies_all_selected",
                "input_types": ["Option", "OptionSet"], "output_type": "Bool",
                "solver_lowering": "Implies(selected(option), And(selected(required)...))",
                "active_constraint_count": len(feasibility_constraints.get("prerequisites") or ()),
            },
            {
                "predicate_id": "linear_sum_le",
                "input_types": ["ResourceUseMap", "Decimal"], "output_type": "Bool",
                "solver_lowering": "Sum(If(selected(option), use(option), 0)) <= limit",
                "active_constraint_count": len(feasibility_constraints.get("resources") or ()),
            },
        ],
        "option_ids": list(option_ids),
        "max_bundle_size": max_bundle_size,
        "incompatible_option_pairs": [list(pair) for pair in sorted(incompatible_pairs)],
        "constraint_authority": {
            "dossier_bound_predicate_count": (
                len(typed_incompatible_pairs)
                + sum(
                    row.get("authority") == "dossier_bound"
                    for kind in ("prerequisites", "resources")
                    for row in feasibility_constraints.get(kind) or ()
                )
            ),
            "legacy_profile_predicate_count": (
                len(legacy_incompatible_pairs - typed_incompatible_pairs)
                + sum(
                    row.get("authority") == "legacy_profile"
                    for kind in ("prerequisites", "resources")
                    for row in feasibility_constraints.get(kind) or ()
                )
            ),
        },
        "feasibility_constraints": dict(feasibility_constraints),
        "feasible_bundle_count": len(bundle_rows),
        "bounded_bundle_count": len(bundle_rows) + len(excluded_bundles),
        "excluded_bundle_count": len(excluded_bundles),
        "feasible_bundles": [
            {"option_ids": list(bundle), "program_id": program.program_id}
            for bundle, program in zip(bundle_rows, programs, strict=True)
        ],
        "excluded_bundles": excluded_bundles,
        "scope_closed": True,
        "use_boundary": (
            "Z3 closes compatibility, cardinality, declared prerequisites, and linear resource "
            "bounds over the option vocabulary. It does not validate authored quantities, option "
            "effects, implementation success, or omitted choices."
        ),
    }
    certificate = {
        **certificate_body,
        "choice_space_sha256": stable_sha256(certificate_body),
    }
    return enumeration, certificate, witnesses


def explain_strategy_bundle_feasibility(
    frontier: Mapping[str, Any], option_ids: Iterable[str],
) -> dict[str, Any]:
    """Explain an option set against the predicates in its Z3 certificate."""
    if frontier.get("schema") != RESULT_SCHEMA:
        raise ValueError(f"frontier must use schema {RESULT_SCHEMA}")
    if isinstance(option_ids, (str, bytes)):
        raise ValueError("option_ids must be an iterable of option identifiers")
    requested = tuple(require_text(value, "strategy option_id") for value in option_ids)
    if len(requested) != len(set(requested)):
        raise ValueError("strategy option bundle cannot contain duplicate option identities")

    certificate = _mapping(frontier.get("choice_space_certificate"), "choice_space_certificate")
    certificate_sha = require_text(
        certificate.get("choice_space_sha256"), "choice_space_sha256",
    )
    certificate_body = {
        key: value for key, value in certificate.items() if key != "choice_space_sha256"
    }
    if stable_sha256(certificate_body) != certificate_sha:
        raise ValueError("choice-space certificate content does not match choice_space_sha256")
    vocabulary = {str(value) for value in certificate.get("option_ids") or ()}
    unknown = sorted(set(requested) - vocabulary)
    if unknown:
        raise ValueError(f"strategy option bundle crosses the certified vocabulary: {unknown}")
    selected = tuple(sorted(requested))
    selected_set = set(selected)
    violations: list[dict[str, Any]] = []

    if not selected:
        violations.append({
            "constraint_id": "choice_nonempty", "kind": "cardinality",
            "predicate": {"operator": "cardinality_ge", "bound": 1},
            "observed_count": 0,
        })
    max_bundle_size = int(certificate["max_bundle_size"])
    if len(selected) > max_bundle_size:
        violations.append({
            "constraint_id": "bundle_size", "kind": "cardinality",
            "predicate": {"operator": "cardinality_le", "bound": max_bundle_size},
            "observed_count": len(selected),
        })
    for pair in certificate.get("incompatible_option_pairs") or ():
        left, right = sorted(map(str, pair))
        if {left, right}.issubset(selected_set):
            violations.append({
                "constraint_id": f"incompatible:{left}:{right}",
                "kind": "incompatible_option_pair",
                "predicate": {"operator": "not_all_selected", "option_ids": [left, right]},
                "observed_selected_option_ids": [left, right],
            })

    constraints = _mapping(certificate.get("feasibility_constraints") or {}, "feasibility_constraints")
    for row in constraints.get("prerequisites") or ():
        option_id = str(row["option_id"])
        required = sorted(map(str, row["requires"]))
        missing = [value for value in required if value not in selected_set]
        if option_id in selected_set and missing:
            violations.append({
                "constraint_id": f"prerequisite:{option_id}",
                "kind": "missing_prerequisite",
                "predicate": {
                    "operator": "implies_all_selected", "if_option_id": option_id,
                    "then_option_ids": required,
                },
                "observed_missing_option_ids": missing,
            })
    for row in constraints.get("resources") or ():
        uses = {
            str(option_id): Decimal(str(amount))
            for option_id, amount in _mapping(row["uses"], "resource uses").items()
        }
        selected_use = sum((uses.get(option_id, Decimal(0)) for option_id in selected), Decimal(0))
        limit = Decimal(str(row["limit"]))
        if selected_use > limit:
            resource_id = str(row["resource_id"])
            violations.append({
                "constraint_id": f"resource:{resource_id}", "kind": "resource_limit",
                "predicate": {
                    "operator": "linear_sum_le", "resource_id": resource_id,
                    "unit": str(row["unit"]), "limit": float(limit),
                },
                "observed_selected_use": float(selected_use),
                "observed_option_uses": {
                    option_id: float(uses[option_id])
                    for option_id in selected if option_id in uses
                },
            })

    feasible_bundles = {
        tuple(sorted(map(str, row["option_ids"])))
        for row in certificate.get("feasible_bundles") or ()
    }
    solver_certificate_membership = selected in feasible_bundles
    if solver_certificate_membership != (not violations):
        raise RuntimeError("strategy predicate explanation disagrees with its Z3 certificate")
    body = {
        "schema": "jaggedthoughts-strategy-bundle-feasibility-explanation-v1",
        "choice_space_sha256": certificate_sha,
        "option_ids": list(selected),
        "feasible": solver_certificate_membership,
        "solver_certificate_membership": solver_certificate_membership,
        "explanation_method": "deterministic_evaluation_of_compiled_z3_predicates",
        "violated_constraint_ids": [row["constraint_id"] for row in violations],
        "violations": violations,
        "capital_authority": False,
    }
    return {**body, "explanation_sha256": stable_sha256(body)}


def _scenario_values(
    option_ids: Iterable[str],
    *,
    scenario: Mapping[str, Any],
    options: Mapping[str, Mapping[str, Any]],
    interactions: list[Mapping[str, Any]],
    pressure_ids: set[str],
) -> tuple[float, ...]:
    base = _vector(scenario.get("base"), f"scenario {scenario.get('id')} base")
    selected = set(option_ids)
    values = list(base)
    addressed: set[str] = set()
    scenario_id = require_text(scenario.get("id"), "scenario id")
    for option_id in sorted(selected):
        option = options[option_id]
        effects = _mapping(option.get("scenario_effects"), f"option {option_id} scenario_effects")
        delta = _vector(effects.get(scenario_id), f"option {option_id} effect for {scenario_id}")
        values = [current + change for current, change in zip(values, delta, strict=True)]
        addressed.update(str(value) for value in option.get("addresses") or ())
    for interaction in interactions:
        required = set(str(value) for value in interaction.get("option_ids") or ())
        if required and required.issubset(selected):
            interaction_id = interaction.get("interaction_id") or interaction.get("id")
            effects = _mapping(
                interaction.get("scenario_effects"),
                f"interaction {interaction_id} scenario_effects",
            )
            delta = _vector(
                effects.get(scenario_id),
                f"interaction {interaction_id} effect for {scenario_id}",
            )
            values = [current + change for current, change in zip(values, delta, strict=True)]
    coverage = len(addressed.intersection(pressure_ids)) / len(pressure_ids) if pressure_ids else 1.0
    return (*values, coverage)


def _economic_proposals(
    scenario_scores: Iterable[Mapping[str, Any]], evidence_refs: Iterable[str]
) -> list[dict[str, Any]]:
    """Lower normalized strategy effects without inventing valuation magnitudes."""
    rows = tuple(scenario_scores)
    proposals = []
    for index, (objective, coordinate) in enumerate(ECONOMIC_COORDINATES):
        values = [float(row["values"][index]) for row in rows]
        direction = "increase" if min(values) > 0 else "decrease" if max(values) < 0 else "mixed_or_flat"
        proposals.append({
            "objective": objective,
            "economic_coordinate": coordinate,
            "direction": direction,
            "normalized_effect_range": [min(values), max(values)],
            "unit": "normalized_directional_score",
            "evidence_refs": sorted(set(evidence_refs)),
            "magnitude_status": "requires_source_bound_calibration",
            "authority": "proposal_only",
        })
    return proposals


def _outcome_contracts(
    option: Mapping[str, Any], option_id: str, evidence_epoch: str,
) -> list[dict[str, Any]]:
    raw = option.get("outcome_contracts") or []
    if not isinstance(raw, list) or any(not isinstance(row, Mapping) for row in raw):
        raise ValueError(f"option {option_id} outcome_contracts must be a list of mappings")
    rows = []
    mechanism = option.get("mechanism")
    mechanism_bridge = (
        str(mechanism.get("economic_bridge") or "")
        if isinstance(mechanism, Mapping) else ""
    )
    scenario_effects = option.get("scenario_effects") or {}
    for contract in raw:
        contract_id = require_text(contract.get("id"), f"option {option_id} outcome contract id")
        direction = require_text(
            contract.get("direction"), f"option {option_id} outcome contract direction",
        )
        comparator = require_text(
            contract.get("comparator"), f"option {option_id} outcome contract comparator",
        )
        if direction not in {"increase", "decrease"}:
            raise ValueError(f"option {option_id} outcome direction must be increase or decrease")
        if comparator not in {"pre_move_baseline", "matched_peer", "industry_baseline"}:
            raise ValueError(f"option {option_id} outcome comparator is unsupported")
        horizon_days = int(contract.get("horizon_days") or 0)
        if not 30 <= horizon_days <= 3650:
            raise ValueError(f"option {option_id} outcome horizon must be in [30, 3650] days")
        measurement_start_at = canonical_timestamp(
            contract.get("measurement_start_at") or evidence_epoch,
            f"option {option_id} outcome measurement_start_at",
        )
        if timestamp_key(measurement_start_at) > timestamp_key(evidence_epoch):
            raise ValueError(f"option {option_id} outcome cannot start after its evidence epoch")
        if timestamp_key(measurement_start_at) + timedelta(days=horizon_days) <= timestamp_key(evidence_epoch):
            raise ValueError(f"option {option_id} outcome target must remain after its evidence epoch")
        outcome_role = require_text(
            contract.get("outcome_role") or "terminal_operating",
            f"option {option_id} outcome role",
        )
        acquisition_mode = require_text(
            contract.get("acquisition_mode") or "subscription_primary_document",
            f"option {option_id} outcome acquisition_mode",
        )
        if outcome_role not in OUTCOME_ROLES:
            raise ValueError(f"option {option_id} outcome role is unsupported")
        if acquisition_mode not in OUTCOME_ACQUISITION_MODES:
            raise ValueError(f"option {option_id} outcome acquisition mode is unsupported")
        raw_coordinate = contract.get("objective_coordinate")
        if raw_coordinate is None:
            objective_coordinate = None
            coordinate_status = "unbound_legacy"
            directions: list[dict[str, Any]] = []
            direction_summary = None
        else:
            objective_coordinate = require_text(
                raw_coordinate, f"option {option_id} outcome objective_coordinate",
            )
            if objective_coordinate != mechanism_bridge:
                raise ValueError(
                    f"option {option_id} outcome objective_coordinate must equal its "
                    "mechanism economic_bridge"
                )
            coordinate_status = "bound"
            coordinate_index = OBJECTIVES.index(objective_coordinate)
            directions = []
            for scenario_id, vector in sorted(scenario_effects.items()):
                checked_vector = _vector(
                    vector, f"option {option_id} scenario {scenario_id} effect",
                )
                value = checked_vector[coordinate_index]
                directions.append({
                    "scenario_id": str(scenario_id),
                    "ordinal_direction": 1 if value > 0 else -1 if value < 0 else 0,
                })
            direction_values = {row["ordinal_direction"] for row in directions}
            direction_summary = (
                "increase" if direction_values == {1}
                else "decrease" if direction_values == {-1}
                else "flat" if direction_values == {0}
                else "mixed"
            )
        body = {
            "contract_id": contract_id,
            "metric_id": require_text(
                contract.get("metric_id"), f"option {option_id} outcome metric_id",
            ),
            "unit": require_text(contract.get("unit"), f"option {option_id} outcome unit"),
            "direction": direction,
            "minimum_effect": require_finite(
                contract.get("minimum_effect", 0), f"option {option_id} minimum_effect",
            ),
            "horizon_days": horizon_days,
            "measurement_start_at": measurement_start_at,
            "outcome_role": outcome_role,
            "acquisition_mode": acquisition_mode,
            "comparator": comparator,
            "objective_coordinate": objective_coordinate,
            "objective_coordinate_status": coordinate_status,
            "ordinal_scenario_direction_hypothesis": directions,
            "ordinal_direction_summary": direction_summary,
            "evidence_refs": list(_refs(
                contract.get("evidence_refs"), f"option {option_id} outcome evidence_refs",
            )),
        }
        if "minimum_effect_basis" in contract:
            basis = require_text(
                contract.get("minimum_effect_basis"),
                f"option {option_id} minimum effect basis",
            )
            if basis not in {"directional_zero", "analyst_forecast", "source_disclosed"}:
                raise ValueError(f"option {option_id} minimum effect basis is unsupported")
            if basis == "directional_zero" and body["minimum_effect"] != 0:
                raise ValueError(
                    f"option {option_id} directional-zero contract requires zero minimum effect"
                )
            threshold_refs = list(_refs(
                contract.get("minimum_effect_source_refs") or body["evidence_refs"],
                f"option {option_id} minimum effect source refs",
            )) if basis == "source_disclosed" else []
            if not set(threshold_refs).issubset(set(body["evidence_refs"])):
                raise ValueError(
                    f"option {option_id} threshold sources must be contract evidence refs"
                )
            body.update({
                "minimum_effect_basis": basis,
                "minimum_effect_rationale": require_text(
                    contract.get("minimum_effect_rationale"),
                    f"option {option_id} minimum effect rationale",
                ),
                "minimum_effect_source_refs": threshold_refs,
            })
        if "metric_locator" in contract:
            body["metric_locator"] = require_text(
                contract.get("metric_locator"),
                f"option {option_id} outcome metric locator",
            )
        if "measurement_source_catalog" in contract:
            raw_sources = contract.get("measurement_source_catalog")
            if not isinstance(raw_sources, list) or any(
                not isinstance(source, Mapping) for source in raw_sources
            ):
                raise ValueError(
                    f"option {option_id} measurement source catalog must be mappings"
                )
            sources = []
            for source in raw_sources:
                source_id = require_text(
                    source.get("id"), f"option {option_id} measurement source id",
                )
                url = require_text(
                    source.get("url"), f"option {option_id} measurement source URL",
                )
                source_kind = require_text(
                    source.get("source_kind"),
                    f"option {option_id} measurement source kind",
                )
                published_at = canonical_timestamp(
                    source.get("published_at"),
                    f"option {option_id} measurement source published_at",
                )
                accessed_at = canonical_timestamp(
                    source.get("accessed_at"),
                    f"option {option_id} measurement source accessed_at",
                )
                supports = list(_refs(
                    source.get("supports"),
                    f"option {option_id} measurement source supports",
                ))
                if (
                    not url.startswith("https://")
                    or source_kind not in {"filing", "issuer"}
                    or timestamp_key(published_at) > timestamp_key(accessed_at)
                    or timestamp_key(accessed_at) > timestamp_key(evidence_epoch)
                ):
                    raise ValueError(
                        f"option {option_id} measurement source boundary is invalid"
                    )
                sources.append({
                    "id": source_id,
                    "title": require_text(
                        source.get("title"),
                        f"option {option_id} measurement source title",
                    ),
                    "url": url,
                    "publisher": require_text(
                        source.get("publisher"),
                        f"option {option_id} measurement source publisher",
                    ),
                    "source_kind": source_kind,
                    "published_at": published_at,
                    "accessed_at": accessed_at,
                    "supports": sorted(supports),
                })
            if (
                len({source["id"] for source in sources}) != len(sources)
                or {source["id"] for source in sources} != set(body["evidence_refs"])
                or not any(
                    {f"metric:{body['metric_id']}", "clock"}.issubset(
                        set(source["supports"])
                    )
                    for source in sources
                )
            ):
                raise ValueError(
                    f"option {option_id} measurement sources must resolve its metric and clock"
                )
            body["measurement_source_catalog"] = sorted(
                sources, key=lambda source: source["id"],
            )
        if "economic_bridge_rationale" in contract:
            body["economic_bridge_rationale"] = require_text(
                contract.get("economic_bridge_rationale"),
                f"option {option_id} outcome economic bridge rationale",
            )
        rows.append({**body, "contract_sha256": stable_sha256(body)})
    if len({row["contract_id"] for row in rows}) != len(rows):
        raise ValueError(f"option {option_id} outcome contract IDs must be unique")
    return sorted(rows, key=lambda row: row["contract_id"])


def _mechanism(option: Mapping[str, Any], option_id: str) -> dict[str, Any] | None:
    raw = option.get("mechanism")
    if raw is None:
        return None
    mechanism = _mapping(raw, f"option {option_id} mechanism")
    action = require_text(mechanism.get("action"), f"option {option_id} mechanism action")
    bridge = require_text(
        mechanism.get("economic_bridge"), f"option {option_id} mechanism economic_bridge",
    )
    if action not in MECHANISM_ACTIONS:
        raise ValueError(f"option {option_id} mechanism action is unsupported")
    if bridge not in MECHANISM_BRIDGES:
        raise ValueError(f"option {option_id} mechanism economic_bridge is unsupported")
    conditions = sorted({
        require_text(value, f"option {option_id} implementation condition")
        for value in mechanism.get("implementation_conditions") or ()
    })
    break_conditions = sorted({
        require_text(value, f"option {option_id} break condition")
        for value in mechanism.get("break_conditions") or ()
    })
    if not conditions or not break_conditions:
        raise ValueError(
            f"option {option_id} mechanism requires implementation_conditions and break_conditions"
        )
    body = {
        "action": action,
        "economic_bridge": bridge,
        "object_id": require_text(
            mechanism.get("object_id"), f"option {option_id} mechanism object_id",
        ),
        "implementation_conditions": conditions,
        "break_conditions": break_conditions,
        "evidence_refs": list(_refs(
            mechanism.get("evidence_refs"), f"option {option_id} mechanism evidence_refs",
        )),
    }
    return {**body, "mechanism_sha256": stable_sha256(body)}


def _implementation_event(
    option: Mapping[str, Any], option_id: str, evidence_epoch: str,
) -> dict[str, Any] | None:
    raw = option.get("implementation_event")
    if raw is None:
        return None
    event = _mapping(raw, f"option {option_id} implementation_event")
    event_kind = require_text(event.get("event_kind"), f"option {option_id} event_kind")
    status_after = require_text(event.get("status_after"), f"option {option_id} status_after")
    implementation_mode = str(event.get("implementation_mode") or "unspecified")
    timing_precision = require_text(
        event.get("timing_precision"), f"option {option_id} timing_precision",
    )
    if event_kind not in IMPLEMENTATION_EVENT_KINDS:
        raise ValueError(f"option {option_id} implementation event_kind is unsupported")
    if status_after not in IMPLEMENTATION_STATUSES:
        raise ValueError(f"option {option_id} implementation status_after is unsupported")
    if implementation_mode not in IMPLEMENTATION_MODES:
        raise ValueError(f"option {option_id} implementation mode is unsupported")
    if timing_precision not in IMPLEMENTATION_TIMING_PRECISIONS:
        raise ValueError(f"option {option_id} implementation timing_precision is unsupported")
    occurred_at = canonical_timestamp(
        event.get("occurred_at"), f"option {option_id} implementation occurred_at",
    )
    available_at = canonical_timestamp(
        event.get("available_at"), f"option {option_id} implementation available_at",
    )
    if timestamp_key(occurred_at) > timestamp_key(available_at):
        raise ValueError(f"option {option_id} implementation cannot be available before it occurred")
    if timestamp_key(available_at) > timestamp_key(evidence_epoch):
        raise ValueError(f"option {option_id} implementation was unavailable at its evidence epoch")
    adoption_like = event_kind in {"adoption", "first_public_observation"} and status_after in {
        "underway", "completed",
    }
    treatment_timing_status = (
        "exact_adoption_event"
        if event_kind == "adoption" and timing_precision == "date" and adoption_like
        else "interval_censored_adoption_event"
        if adoption_like
        else "not_an_adoption_event"
    )
    body = {
        "event_id": require_text(event.get("id"), f"option {option_id} implementation event id"),
        "event_kind": event_kind,
        "implementation_mode": implementation_mode,
        "status_after": status_after,
        "occurred_at": occurred_at,
        "available_at": available_at,
        "timing_precision": timing_precision,
        "treatment_timing_status": treatment_timing_status,
        "source_refs": list(_refs(
            event.get("source_refs"), f"option {option_id} implementation source_refs",
        )),
    }
    return {**body, "implementation_event_sha256": stable_sha256(body)}


def _contingent_policies(
    raw: Any, *, programs: Mapping[str, Mapping[str, Any]],
    company_id: str, grammar_id: str, grammar_version: str, evidence_epoch: str,
    choice_space_sha256: str, reference_fixture: bool,
) -> list[dict[str, Any]]:
    """Compile commitment-plus-recourse policies over Z3-certified bundles."""
    if raw in (None, []):
        return []
    if not isinstance(raw, list) or any(not isinstance(row, Mapping) for row in raw):
        raise ValueError("contingent_policies must be a list of mappings")
    compiled = []
    program_by_bundle = {
        tuple(sorted(set(map(str, row.get("unique_option_ids") or ())))): program_id
        for program_id, row in programs.items()
    }
    for policy in raw:
        policy_id = require_text(policy.get("id"), "contingent policy id")
        raw_commitment = policy.get("commit_option_ids")
        if not isinstance(raw_commitment, list) or not raw_commitment:
            raise ValueError(f"contingent policy {policy_id} needs commit_option_ids")
        commitment_key = tuple(sorted({
            require_text(value, f"contingent policy {policy_id} commitment option")
            for value in raw_commitment
        }))
        commit_id = program_by_bundle.get(commitment_key)
        if commit_id is None:
            raise ValueError(f"contingent policy {policy_id} has an unknown commitment")
        frozen_at = canonical_timestamp(
            policy.get("frozen_at") or evidence_epoch,
            f"contingent policy {policy_id} freeze time",
        )
        commit_at = canonical_timestamp(
            policy.get("commit_not_before") or frozen_at,
            f"contingent policy {policy_id} commitment time",
        )
        recourse_at = canonical_timestamp(
            policy.get("recourse_not_before"),
            f"contingent policy {policy_id} recourse time",
        )
        if (
            timestamp_key(frozen_at) > timestamp_key(evidence_epoch)
            or timestamp_key(commit_at) < timestamp_key(frozen_at)
            or timestamp_key(recourse_at) <= timestamp_key(commit_at)
        ):
            raise ValueError(
                f"contingent policy {policy_id} must freeze commitment before recourse"
            )
        condition_rows = _rows(
            policy.get("conditions"), f"contingent policy {policy_id} conditions",
        )
        conditions = []
        condition_contracts = {}
        for row in condition_rows:
            condition_id = require_text(row.get("id"), "contingent condition id")
            coordinate = require_text(row.get("coordinate"), "contingent condition coordinate")
            if "." in coordinate:
                raise ValueError("contingent condition coordinates cannot contain dots")
            threshold_basis = require_text(
                row.get("threshold_basis"), "contingent condition threshold_basis",
            )
            if threshold_basis not in {
                "source_disclosed", "analyst_hypothesis", "reference_fixture",
            }:
                raise ValueError("contingent condition threshold_basis is unsupported")
            if threshold_basis == "reference_fixture" and not reference_fixture:
                raise ValueError("reference-fixture thresholds require a reference fixture company")
            threshold_rationale = require_text(
                row.get("threshold_rationale"), "contingent condition threshold_rationale",
            )
            unit = require_text(row.get("unit"), "contingent condition unit")
            condition = PolicyCondition(
                condition_id=condition_id, path=f"firm.{coordinate}",
                operator=require_text(row.get("operator"), "contingent condition operator"),
                value=require_finite(row.get("value"), "contingent condition value"),
                evidence_refs=_refs(row.get("evidence_refs"), "contingent condition evidence refs"),
            )
            conditions.append(condition)
            condition_contracts[condition_id] = {
                **condition.to_dict(), "threshold_basis": threshold_basis,
                "threshold_rationale": threshold_rationale, "unit": unit,
            }
        condition_by_id = {row.condition_id: row for row in conditions}
        if not conditions or len(condition_by_id) != len(conditions):
            raise ValueError(f"contingent policy {policy_id} needs unique conditions")

        policy_grammar = OperatorGrammar(
            grammar_id=f"{grammar_id}.contingent.{policy_id}", version=grammar_version,
            terminals=tuple(
                TypedTerminal(
                    terminal_id=f"act::{program_id}", output_type="Policy",
                    description=f"Finish with static bundle {program_id}.",
                )
                for program_id in sorted(programs)
            ) + tuple(
                TypedTerminal(
                    terminal_id=f"when::{row.condition_id}", output_type="Condition",
                    description=f"{row.path} {row.operator} {row.value}",
                )
                for row in sorted(conditions, key=lambda item: item.condition_id)
            ),
            operators=(TypedOperator(
                operator_id="branch", input_types=("Condition", "Policy", "Policy"),
                output_type="Policy",
                description="Select a pre-enumerated recourse bundle from an observed state.",
            ),),
        )
        leaf_ids: set[str] = set()
        used_conditions: set[str] = set()

        def build(node: Any) -> Any:
            if not isinstance(node, Mapping):
                raise ValueError(f"contingent policy {policy_id} has an invalid AST node")
            if set(node) == {"option_ids"}:
                raw_options = node.get("option_ids")
                if not isinstance(raw_options, list) or not raw_options:
                    raise ValueError(f"contingent policy {policy_id} has empty recourse")
                bundle = tuple(sorted({
                    require_text(value, "recourse option id") for value in raw_options
                }))
                program_id = program_by_bundle.get(bundle)
                if program_id is None:
                    raise ValueError(f"contingent policy {policy_id} has an unknown recourse")
                leaf_ids.add(program_id)
                return build_typed_program(
                    policy_grammar, terminal_id=f"act::{program_id}",
                )
            if set(node) != {"condition_id", "if_true", "if_false"}:
                raise ValueError(f"contingent policy {policy_id} branch shape is invalid")
            condition_id = require_text(node.get("condition_id"), "branch condition id")
            if condition_id not in condition_by_id:
                raise ValueError(f"contingent policy {policy_id} uses an unknown condition")
            used_conditions.add(condition_id)
            return build_typed_program(
                policy_grammar, operator_id="branch", children=(
                    build_typed_program(
                        policy_grammar, terminal_id=f"when::{condition_id}",
                    ),
                    build(node["if_true"]), build(node["if_false"]),
                ),
            )

        program = build(policy.get("policy"))
        if used_conditions != set(condition_by_id) or len(leaf_ids) < 2:
            raise ValueError(
                f"contingent policy {policy_id} must use every condition and change recourse"
            )
        commitment = set(programs[commit_id].get("unique_option_ids") or ())
        finals = []
        for program_id in sorted(leaf_ids):
            final_options = set(programs[program_id].get("unique_option_ids") or ())
            if not commitment.issubset(final_options):
                raise ValueError(
                    f"contingent policy {policy_id} recourse cannot reverse its commitment"
                )
            finals.append({
                "program_id": program_id,
                "final_option_ids": sorted(final_options),
                "recourse_option_ids": sorted(final_options - commitment),
                "objective_values": dict(programs[program_id].get("objective_values") or {}),
            })
        regions = compile_policy_action_regions(program=program, conditions=conditions)
        if not (
            regions["scope_closed"] and regions["total_over_condition_space"]
            and regions["deterministic_over_condition_space"]
        ):
            raise ValueError(f"contingent policy {policy_id} does not close its trigger space")
        body = {
            "schema": "jaggedthoughts-company-contingent-policy-v1",
            "company_id": company_id,
            "policy_id": policy_id, "frozen_at": frozen_at,
            "commit_not_before": commit_at, "recourse_not_before": recourse_at,
            "commit_program_id": commit_id,
            "commit_option_ids": sorted(commitment),
            "program": program.to_dict(),
            "conditions": [condition_contracts[row.condition_id] for row in conditions],
            "final_programs": finals, "policy_action_regions": regions,
            "feasibility_receipt": {
                "method": "membership_in_z3_closed_static_choice_space",
                "choice_space_sha256": choice_space_sha256,
                "program_ids": sorted({commit_id, *leaf_ids}),
            },
            "authority": "operating_strategy_proposal_only",
            "capital_authority": False,
            "use_boundary": (
                "Z3 certifies trigger partition and declared bundle feasibility only. "
                "Threshold relevance, outcomes, causality, and investment return remain unsettled."
            ),
        }
        compiled.append({**body, "contingent_policy_sha256": stable_sha256(body)})
    if len({row["policy_id"] for row in compiled}) != len(compiled):
        raise ValueError("contingent policy IDs must be unique")
    return sorted(compiled, key=lambda row: row["policy_id"])


def select_company_contingent_recourse(
    policy: Mapping[str, Any], *, evaluated_at: str,
    observations: Sequence[MetricObservation],
) -> dict[str, Any]:
    """Select one certified recourse bundle from source-timed metric observations."""
    frozen = dict(policy)
    policy_sha = require_text(
        frozen.pop("contingent_policy_sha256", ""), "contingent policy hash",
    )
    if (
        frozen.get("schema") != "jaggedthoughts-company-contingent-policy-v1"
        or stable_sha256(frozen) != policy_sha
    ):
        raise ValueError("contingent policy identity is invalid")
    decision_time = canonical_timestamp(evaluated_at, "contingent recourse evaluated_at")
    if timestamp_key(decision_time) < timestamp_key(str(frozen["recourse_not_before"])):
        raise ValueError("contingent policy recourse is not yet available")

    conditions = tuple(frozen.get("conditions") or ())
    required_metrics = {str(row["path"]).removeprefix("firm.") for row in conditions}
    observed_by_metric: dict[str, MetricObservation] = {}
    for observation in observations:
        if observation.entity_id != frozen["company_id"]:
            raise ValueError("contingent observation crossed company identity")
        if observation.metric_id in observed_by_metric:
            raise ValueError("contingent observations require one revision per metric")
        if (
            timestamp_key(observation.observed_at) < timestamp_key(str(frozen["commit_not_before"]))
            or timestamp_key(observation.observed_at) > timestamp_key(observation.available_at)
            or timestamp_key(observation.available_at) > timestamp_key(decision_time)
        ):
            raise ValueError("contingent observation crossed its point-in-time window")
        observed_by_metric[observation.metric_id] = observation
    if set(observed_by_metric) != required_metrics:
        raise ValueError("contingent observations do not exactly cover policy coordinates")
    for condition in conditions:
        metric_id = str(condition["path"]).removeprefix("firm.")
        if observed_by_metric[metric_id].unit != condition["unit"]:
            raise ValueError("contingent observation unit does not match its threshold")

    def matches(condition: Mapping[str, Any]) -> bool:
        value = observed_by_metric[str(condition["path"]).removeprefix("firm.")].value
        threshold = float(condition["value"])
        return {
            "eq": value == threshold, "ne": value != threshold,
            "gt": value > threshold, "ge": value >= threshold,
            "lt": value < threshold, "le": value <= threshold,
        }[str(condition["operator"])]

    regions = dict(frozen["policy_action_regions"])
    selected_regions = [
        row for row in regions.get("regions") or ()
        if all(matches(condition) for condition in row.get("conditions") or ())
    ]
    if len(selected_regions) != 1:
        raise ValueError("certified contingent policy did not select exactly one region")
    selected_region = selected_regions[0]
    selected_program = next(
        (
            row for row in frozen.get("final_programs") or ()
            if row.get("program_id") == selected_region.get("action_id")
        ),
        None,
    )
    if selected_program is None:
        raise ValueError("selected contingent region has no certified final bundle")
    observation_rows = [
        {
            **observed_by_metric[metric_id].to_dict(),
            "observation_sha256": stable_sha256(observed_by_metric[metric_id].to_dict()),
        }
        for metric_id in sorted(observed_by_metric)
    ]
    body = {
        "schema": "jaggedthoughts-company-contingent-recourse-selection-v1",
        "company_id": frozen["company_id"], "policy_id": frozen["policy_id"],
        "contingent_policy_sha256": policy_sha,
        "policy_action_regions_sha256": regions["policy_action_regions_sha256"],
        "evaluated_at": decision_time, "observations": observation_rows,
        "selected_region_sha256": selected_region["region_sha256"],
        "selected_program_id": selected_program["program_id"],
        "selected_final_option_ids": list(selected_program["final_option_ids"]),
        "selected_recourse_option_ids": list(selected_program["recourse_option_ids"]),
        "authority": "operating_strategy_observation_only", "capital_authority": False,
        "use_boundary": (
            "This receipt selects the compiled branch from point-in-time observations. "
            "It does not establish causal effect, profitability, or investment return."
        ),
    }
    return {**body, "selection_sha256": stable_sha256(body)}


def compile_company_strategy_frontier(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one source-bound industry response option space."""
    if payload.get("schema") != PROFILE_SCHEMA:
        raise ValueError(f"strategy option profile schema must be {PROFILE_SCHEMA}")
    company = _mapping(payload.get("company"), "company")
    company_id = require_text(company.get("id"), "company id")
    lineage_fields = (
        "candidate_leaf", "candidate_sha256", "source_request_sha256",
        "source_dossier_sha256", "strategy_frontier_request_sha256",
    )
    if any(company.get(key) for key in lineage_fields):
        digests = [require_text(company.get(key), f"company {key}") for key in lineage_fields]
        if any(len(value) != 64 for value in digests):
            raise ValueError("strategy frontier candidate lineage requires 64-character hashes")
    evidence_epoch = canonical_timestamp(payload.get("evidence_epoch"), "evidence_epoch")
    industry = _mapping(payload.get("industry_state"), "industry_state")
    require_text(industry.get("boundary"), "industry boundary")
    require_text(industry.get("customer_need"), "industry customer_need")
    industry_refs = _refs(industry.get("evidence_refs"), "industry evidence_refs")
    pressures = _rows(industry.get("pressures"), "industry pressures")
    pressure_ids = {require_text(row.get("id"), "pressure id") for row in pressures}
    if len(pressure_ids) != len(pressures):
        raise ValueError("industry pressure IDs must be unique")
    for row in pressures:
        require_text(row.get("actor_kind"), "pressure actor_kind")
        require_text(row.get("description"), "pressure description")
        _refs(row.get("evidence_refs"), "pressure evidence_refs")

    raw_options = _rows(payload.get("options"), "strategy options")
    options = {require_text(row.get("id"), "strategy option id"): row for row in raw_options}
    if len(options) != len(raw_options):
        raise ValueError("strategy option IDs must be unique")
    scenarios = _rows(payload.get("scenarios"), "strategy scenarios")
    scenario_ids = {require_text(row.get("id"), "scenario id") for row in scenarios}
    if len(scenario_ids) != len(scenarios):
        raise ValueError("strategy scenario IDs must be unique")
    for scenario in scenarios:
        _vector(scenario.get("base"), f"scenario {scenario.get('id')} base")
        _refs(scenario.get("evidence_refs"), "scenario evidence_refs")

    claims: list[StrategicClaim] = []
    dispositions: list[ClaimDisposition] = []
    terminals: list[TypedTerminal] = []
    for option_id, option in sorted(options.items()):
        require_text(option.get("kind"), f"option {option_id} kind")
        description = require_text(option.get("description"), f"option {option_id} description")
        option_refs = _refs(option.get("evidence_refs"), f"option {option_id} evidence_refs")
        addresses = {str(value) for value in option.get("addresses") or ()}
        if not addresses or not addresses.issubset(pressure_ids):
            raise ValueError(f"option {option_id} must address declared industry pressures")
        effects = _mapping(option.get("scenario_effects"), f"option {option_id} scenario_effects")
        if set(effects) != scenario_ids:
            raise ValueError(f"option {option_id} must provide every scenario effect")
        claim_id = f"option-claim:{option_id}"
        status = str(option.get("claim_status") or "unresolved")
        if status not in {"supported", "refuted", "unresolved"}:
            raise ValueError(f"option {option_id} has unsupported claim_status")
        claims.append(StrategicClaim(
            claim_id=claim_id,
            kind="dynamic",
            text=str(option.get("claim") or description),
        ))
        dispositions.append(ClaimDisposition(claim_id, status, option_refs[0]))
        terminals.append(TypedTerminal(
            terminal_id=f"option:{option_id}", output_type="ChoiceSystem",
            claim_ids=(claim_id,), description=description,
        ))

    option_catalog = []
    for option_id, option in sorted(options.items()):
        option_body = {
            "option_id": option_id,
            "kind": str(option["kind"]),
            "description": str(option["description"]),
            "addresses": sorted(str(value) for value in option.get("addresses") or ()),
            "incompatible_with": sorted(
                str(value) for value in option.get("incompatible_with") or ()
            ),
            "claim": str(option.get("claim") or option["description"]),
            "claim_status": str(option.get("claim_status") or "unresolved"),
            "evidence_refs": list(_refs(
                option.get("evidence_refs"), f"option {option_id} evidence_refs",
            )),
            "mechanism": _mechanism(option, option_id),
            "implementation_event": _implementation_event(option, option_id, evidence_epoch),
            "outcome_contracts": _outcome_contracts(option, option_id, evidence_epoch),
        }
        option_catalog.append({**option_body, "option_sha256": stable_sha256(option_body)})

    raw_interactions = payload.get("interactions") or []
    if not isinstance(raw_interactions, list) or any(not isinstance(row, Mapping) for row in raw_interactions):
        raise ValueError("interactions must be a list of mappings")
    interactions = []
    interaction_ids: set[str] = set()
    for interaction in raw_interactions:
        interaction_id = require_text(interaction.get("id"), "interaction id")
        if interaction_id in interaction_ids:
            raise ValueError(f"duplicate interaction id: {interaction_id}")
        interaction_ids.add(interaction_id)
        interaction_options = set(str(value) for value in interaction.get("option_ids") or ())
        if len(interaction_options) < 2 or not interaction_options.issubset(options):
            raise ValueError(f"interaction {interaction_id} must bind at least two declared options")
        effects = _mapping(interaction.get("scenario_effects"), f"interaction {interaction_id} effects")
        if set(effects) != scenario_ids:
            raise ValueError(f"interaction {interaction_id} must provide every scenario effect")
        interaction_body = {
            "interaction_id": interaction_id,
            "option_ids": sorted(interaction_options),
            "scenario_effects": {
                scenario_id: list(_vector(
                    effects[scenario_id],
                    f"interaction {interaction_id} effect for {scenario_id}",
                ))
                for scenario_id in sorted(scenario_ids)
            },
            "evidence_refs": list(_refs(
                interaction.get("evidence_refs"),
                f"interaction {interaction_id} evidence_refs",
            )),
        }
        interactions.append({
            **interaction_body,
            "interaction_sha256": stable_sha256(interaction_body),
        })
    interactions.sort(key=lambda row: row["interaction_id"])
    feasibility_constraints, feasibility_refs = _feasibility_constraints(
        payload.get("feasibility_constraints"), options,
    )

    grammar = OperatorGrammar(
        grammar_id=str(payload.get("grammar_id") or f"jaggedthoughts.investment.company-strategy.{company_id}"),
        version=str(payload.get("version") or "1"),
        terminals=tuple(terminals),
        operators=(TypedOperator(
            operator_id="combine_reinforcing_choices",
            input_types=("ChoiceSystem", "ChoiceSystem"), output_type="ChoiceSystem",
            commutative=True,
            description="Combine compatible strategic responses into one choice system.",
        ),),
    )
    max_depth = int(payload.get("max_depth", 2))
    max_programs = int(payload.get("max_programs", 5000))
    max_bundle_size = int(payload.get("max_bundle_size", 3))
    enumeration, choice_space_certificate, constraint_witnesses = _compatible_choice_enumeration(
        grammar=grammar,
        options=options,
        max_bundle_size=max_bundle_size,
        max_depth=max_depth,
        max_programs=max_programs,
        feasibility_constraints=feasibility_constraints,
    )
    programs = enumeration.programs_of_type("ChoiceSystem")
    evaluations: list[CandidateEvaluation] = []
    program_rows: dict[str, dict[str, Any]] = {}
    global_refs = set(industry_refs)
    for scenario in scenarios:
        global_refs.update(_refs(scenario.get("evidence_refs"), "scenario evidence_refs"))
    global_refs.update(feasibility_refs)
    for program in programs:
        option_ids = _option_ids(program)
        selected_options = set(option_ids)
        active_interactions = [
            interaction for interaction in interactions
            if set(interaction["option_ids"]).issubset(selected_options)
        ]
        scenario_scores = []
        scenario_vectors: list[tuple[float, ...]] = []
        for scenario in scenarios:
            vector = _scenario_values(
                option_ids, scenario=scenario, options=options,
                interactions=interactions, pressure_ids=pressure_ids,
            )
            scenario_vectors.append(vector)
            scenario_scores.append({"scenario_id": scenario["id"], "values": list(vector)})
        values = tuple(min(vector[index] for vector in scenario_vectors) for index in range(len(OBJECTIVES)))
        behavior = tuple(
            f"{row['scenario_id']}|" + ",".join(format(value, ".17g") for value in row["values"])
            for row in scenario_scores
        )
        refs = set(global_refs)
        for option_id in set(option_ids):
            refs.update(_refs(options[option_id].get("evidence_refs"), f"option {option_id} evidence_refs"))
        for interaction in active_interactions:
            refs.update(interaction["evidence_refs"])
        evaluations.append(CandidateEvaluation(
            program_id=program.program_id,
            objective_values=values,
            behavior_signature=behavior,
            evidence_refs=tuple(sorted(refs)),
        ))
        program_rows[program.program_id] = {
            "program_id": program.program_id,
            "expression": _expression(program),
            "option_ids": list(option_ids),
            "unique_option_ids": sorted(set(option_ids)),
            "active_interaction_ids": [
                interaction["interaction_id"] for interaction in active_interactions
            ],
            "active_interaction_sha256s": [
                interaction["interaction_sha256"] for interaction in active_interactions
            ],
            "constraint_reasons": [],
            "objective_values": dict(zip(OBJECTIVES, values, strict=True)),
            "scenario_scores": scenario_scores,
            "evidence_refs": sorted(refs),
            "economic_coordinate_proposals": (
                _economic_proposals(scenario_scores, refs) if scenario_scores else []
            ),
        }

    search_edges: list[tuple[str, str]] = []
    addition_edges: list[tuple[str, str]] = []
    for left, right in combinations(programs, 2):
        left_set = set(program_rows[left.program_id]["unique_option_ids"])
        right_set = set(program_rows[right.program_id]["unique_option_ids"])
        difference = len(left_set.symmetric_difference(right_set))
        if difference == 1:
            search_edges.append((left.program_id, right.program_id))
            addition_edges.append((left.program_id, right.program_id))
        elif difference == 2 and len(left_set) == len(right_set):
            search_edges.append((left.program_id, right.program_id))
    neighborhood = Neighborhood(
        neighborhood_id=f"single-choice-edit:{company_id}:{evidence_epoch}",
        edges=tuple(search_edges),
    )
    representation = _mapping(payload.get("representation") or {}, "representation")
    representation_status = str(representation.get("status") or "residual")
    residuals = tuple(str(value) for value in representation.get("residuals") or (
        "The authored industry boundary, pressures, option vocabulary, and consequence estimates may omit a material strategic distinction.",
    ))
    audit = RepresentationAudit(
        audit_id=str(representation.get("id") or f"company-strategy-representation:{company_id}:{evidence_epoch}"),
        status=representation_status,
        residuals=residuals if representation_status == "residual" else (),
        evidence_refs=tuple(representation.get("evidence_refs") or ()) if representation_status == "passed" else (),
    )
    scope = FrontierScope(
        grammar_id=grammar.grammar_id, grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest, target_type="ChoiceSystem",
        max_depth=max_depth, max_programs=max_programs,
        evaluation_model_id=f"industry-financial-consequences:{company_id}:{evidence_epoch}",
        landscape_mode="endogenous_transition", evidence_epoch=evidence_epoch,
        objective_names=OBJECTIVES, neighborhood_id=neighborhood.neighborhood_id,
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope, enumeration=enumeration, claims=claims,
        claim_dispositions=dispositions, evaluations=evaluations,
        neighborhood=neighborhood, representation_audit=audit,
    )
    frontier_ids = list(certificate.frontier_program_ids)
    local_ids = list(certificate.local_peak_program_ids)
    frontier_set, local_set = set(frontier_ids), set(local_ids)
    edge_rows = []
    for left_id, right_id in addition_edges:
        left_options = set(program_rows[left_id]["unique_option_ids"])
        right_options = set(program_rows[right_id]["unique_option_ids"])
        base_id, target_id = (
            (left_id, right_id) if len(left_options) < len(right_options)
            else (right_id, left_id)
        )
        base, target = program_rows[base_id], program_rows[target_id]
        added_option_id = next(iter(
            set(target["unique_option_ids"]) - set(base["unique_option_ids"])
        ))
        edge_body = {
            "schema": "jaggedthoughts-strategy-one-choice-edge-v1",
            "base_program_id": base_id, "target_program_id": target_id,
            "added_option_id": added_option_id,
            "base_option_ids": base["unique_option_ids"],
            "target_option_ids": target["unique_option_ids"],
            "base_expression": base["expression"], "target_expression": target["expression"],
            "authored_objective_delta": {
                objective: target["objective_values"][objective] - base["objective_values"][objective]
                for objective in OBJECTIVES
            },
            "activated_interaction_ids": sorted(
                set(target["active_interaction_ids"]) - set(base["active_interaction_ids"])
            ),
            "base_is_frontier": base_id in frontier_set,
            "target_is_frontier": target_id in frontier_set,
            "base_is_local_peak": base_id in local_set,
            "target_is_local_peak": target_id in local_set,
            "calibration_status": "requires_observed_transition_and_contrast",
            "capital_authority": False,
        }
        edge_rows.append({**edge_body, "edge_sha256": stable_sha256(edge_body)})
    edge_rows.sort(key=lambda row: (
        row["added_option_id"], row["base_program_id"], row["target_program_id"],
    ))
    neighborhood_body = {
        "schema": "jaggedthoughts-strategy-one-choice-neighborhood-v1",
        "neighborhood_id": neighborhood.neighborhood_id,
        "edge_count": len(edge_rows), "edges": edge_rows,
        "search_edge_count": len(search_edges),
        "substitution_edge_count": len(search_edges) - len(addition_edges),
        "next_activation": (
            "Freeze a point-in-time operating contrast for an observed base-to-target transition."
        ),
        "use_boundary": (
            "Each edge is an authored one-choice contrast. Its delta is a calibration target, "
            "not an observed effect, causal estimate, valuation change, or security return."
        ),
        "capital_authority": False,
    }
    neighborhood_catalog = {
        **neighborhood_body, "neighborhood_sha256": stable_sha256(neighborhood_body),
    }
    pressure_coverage = {
        pressure_id: sorted(
            option_id for option_id, option in options.items()
            if pressure_id in set(option.get("addresses") or ())
        )
        for pressure_id in sorted(pressure_ids)
    }
    objective_weight_regions = compile_linear_preference_regions(
        objective_names=OBJECTIVES,
        alternatives={
            program_id: program_rows[program_id]["objective_values"]
            for program_id in frontier_ids
        },
    ) if frontier_ids else None
    contingent_policies = _contingent_policies(
        payload.get("contingent_policies"), programs=program_rows,
        company_id=company_id,
        grammar_id=grammar.grammar_id, grammar_version=grammar.version,
        evidence_epoch=evidence_epoch,
        choice_space_sha256=choice_space_certificate["choice_space_sha256"],
        reference_fixture=company.get("data_class") == "reference_fixture",
    )
    body: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "compiler_contract_version": 17,
        "company": dict(company),
        "evidence_epoch": evidence_epoch,
        "industry_state": dict(industry),
        "option_catalog": option_catalog,
        "interaction_catalog": interactions,
        "feasibility_constraints": feasibility_constraints,
        "objectives": list(OBJECTIVES),
        "grammar": grammar.to_dict(),
        "enumeration": {
            "program_count": len(programs),
            "method": "z3_associative_commutative_option_set_quotient",
            "exhausted_within_scope": enumeration.exhausted_within_scope,
            "enumeration_digest": enumeration.enumeration_digest,
            "max_depth": max_depth,
            "max_programs": max_programs,
        },
        "choice_space_certificate": choice_space_certificate,
        "constraint_witnesses": constraint_witnesses,
        "programs": [program_rows[program.program_id] for program in programs],
        "contingent_policy_catalog": contingent_policies,
        "frontier_program_ids": frontier_ids,
        "frontier_programs": [program_rows[program_id] for program_id in frontier_ids],
        "local_peak_program_ids": local_ids,
        "local_peak_programs": [program_rows[program_id] for program_id in local_ids],
        "neighborhood": neighborhood_catalog,
        "objective_weight_regions": objective_weight_regions,
        "economic_bridge": {
            "schema": "jaggedthoughts-strategy-economic-coordinate-bridge-v1",
            "coordinate_contract": [
                {"objective": objective, "economic_coordinate": coordinate}
                for objective, coordinate in ECONOMIC_COORDINATES
            ],
            "frontier_proposal_count": sum(
                len(program_rows[program_id]["economic_coordinate_proposals"])
                for program_id in frontier_ids
            ),
            "next_transition": "calibrate_supported_proposal_to_valuation_assumption",
            "capital_authority": False,
        },
        "pressure_to_option_coverage": pressure_coverage,
        "certificate": certificate.to_dict(),
        "scope_closed": certificate.scope_closed,
        "decision_closed": certificate.decision_closed,
        "use_boundary": (
            "The result closes only the declared industry boundary, pressures, option grammar, "
            "scenario effects, depth, and evidence epoch. A local peak is a next-choice trap candidate, not proof of durable advantage."
        ),
    }
    return {**body, "strategy_frontier_sha256": stable_sha256(body)}


__all__ = [
    "OBJECTIVES",
    "ECONOMIC_COORDINATES",
    "MECHANISM_ACTIONS",
    "MECHANISM_BRIDGES",
    "IMPLEMENTATION_EVENT_KINDS",
    "IMPLEMENTATION_STATUSES",
    "IMPLEMENTATION_TIMING_PRECISIONS",
    "IMPLEMENTATION_MODES",
    "OUTCOME_ROLES",
    "OUTCOME_ACQUISITION_MODES",
    "PROFILE_SCHEMA",
    "RESULT_SCHEMA",
    "compile_company_strategy_frontier",
    "explain_strategy_bundle_feasibility",
    "select_company_contingent_recourse",
]
