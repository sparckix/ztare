"""Compile outcome-testable strategy laws from the frozen phenotype frontier.

The strategy-learning module owns enumeration and frontier closure.  This
consumer binds its surviving projection programs to causal evidence contracts,
keeps outcome evidence out of program selection, and exposes the exact gates
that still prevent policy review.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .institutional_learning import LEARNING_STATE_SCHEMA, STRATEGY_REGULARITY_SCHEMA
from .strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    STRATEGY_MOVE_LIBRARY_SCHEMA,
    STRATEGY_PHENOTYPE_DIMENSIONS,
)


STRATEGY_LAW_INDUCTION_SCHEMA = "jaggedthoughts-strategy-law-induction-v1"
STRATEGY_LAW_PROGRAM_SCHEMA = "jaggedthoughts-strategy-law-program-v1"
CAUSAL_LAW_TARGET_INFLUENCE_SCHEMA = "jaggedthoughts-causal-law-target-influence-v1"
CAUSAL_LAW_INFLUENCE_SET_SCHEMA = "jaggedthoughts-causal-law-influence-set-v1"
STRATEGY_LAW_INDUCTION_AVAILABLE_AT = "2026-08-13T14:10:00Z"
_PROJECTION_SCHEMA = "jaggedthoughts-strategy-phenotype-projection-frontier-v1"
_DIMENSION_PATHS = {
    "strategy_form": "phenotype.strategy_form",
    "addressed_actor_profile": "phenotype.addressed_actor_kinds",
    "implementation_mode": "move.implementation_event.implementation_mode",
    "operating_object_scope": "move.mechanism.object_id",
}


def _require_schema(payload: Mapping[str, Any], schema: str, label: str) -> None:
    if payload.get("schema") != schema:
        raise ValueError(f"{label} schema must be {schema}")


def _source_boundary(
    plan: Mapping[str, Any], projection: Mapping[str, Any], generated_at: str,
) -> tuple[str, list[str]]:
    values = [
        STRATEGY_LAW_INDUCTION_AVAILABLE_AT,
        str(((projection.get("certificate") or {}).get("scope") or {}).get("evidence_epoch") or ""),
        *(
            str(row.get("created_at") or "")
            for row in plan.get("requests") or () if isinstance(row, Mapping)
        ),
    ]
    available = sorted(
        {canonical_timestamp(value, "strategy law source availability") for value in values if value},
        key=timestamp_key,
    )
    if timestamp_key(generated_at) < timestamp_key(available[-1]):
        raise ValueError("strategy law induction predates its source evidence")
    return available[-1], available


def _families(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for raw in plan.get("mechanism_environments") or ():
        if not isinstance(raw, Mapping):
            continue
        phenotype = dict(raw.get("mechanism_phenotype") or {})
        phenotype_sha = str(raw.get("mechanism_phenotype_sha256") or "")
        signature_sha = str(raw.get("mechanism_signature_sha256") or "")
        if len(phenotype_sha) != 64 or len(signature_sha) != 64:
            raise ValueError("strategy family requires exact phenotype and signature hashes")
        rows.append({
            "mechanism_signature_sha256": signature_sha,
            "mechanism_phenotype_sha256": phenotype_sha,
            "mechanism_phenotype": phenotype,
            "industry_id": str(raw.get("industry_id") or "unclassified"),
            "focal_move_sha256s": sorted({
                str(row.get("move_sha256")) for row in raw.get("focal_moves") or ()
                if isinstance(row, Mapping) and row.get("move_sha256")
            }),
            "implementation_event_sha256s": sorted({
                str((row.get("implementation_event") or {}).get("implementation_event_sha256"))
                for row in raw.get("focal_moves") or () if isinstance(row, Mapping)
                and isinstance(row.get("implementation_event"), Mapping)
                and (row.get("implementation_event") or {}).get("implementation_event_sha256")
            }),
        })
    return sorted(rows, key=lambda row: (
        row["mechanism_signature_sha256"], row["mechanism_phenotype_sha256"],
    ))


def _program_ast(families: Iterable[Mapping[str, Any]], fields: Iterable[str]) -> dict[str, Any]:
    field_rows = tuple(sorted(set(fields)))
    alternatives = []
    for family in families:
        phenotype = dict(family["mechanism_phenotype"])
        predicates = [
            {
                "operator": "eq", "input_type": "strategy_phenotype",
                "path": "phenotype.action", "value": phenotype.get("action"),
            },
            {
                "operator": "eq", "input_type": "strategy_phenotype",
                "path": "phenotype.economic_bridge", "value": phenotype.get("economic_bridge"),
            },
            *(
                {
                    "operator": "same_as_focal", "input_type": "strategy_move",
                    "path": _DIMENSION_PATHS[field], "dimension": field,
                }
                for field in field_rows
            ),
            {
                "operator": "is_exact_adoption", "input_type": "strategy_move",
                "path": "move.implementation_event.treatment_timing_status",
            },
        ]
        alternatives.append({
            "operator": "all_of", "output_type": "strategy_episode_predicate",
            "family_sha256": family["mechanism_signature_sha256"],
            "arguments": predicates,
        })
    return {
        "operator": "any_of", "output_type": "strategy_episode_predicate",
        "arguments": alternatives,
    }


def _episode_value(
    path: str, *, move: Mapping[str, Any], environment: Mapping[str, Any],
) -> Any:
    if path.startswith("phenotype."):
        value: Any = move.get("mechanism_phenotype") or {}
        parts = path.split(".")[1:]
    elif path.startswith("move."):
        value = move
        parts = path.split(".")[1:]
    elif path.startswith("environment."):
        value = environment
        parts = path.split(".")[1:]
    else:
        raise ValueError(f"unsupported strategy predicate path: {path}")
    for part in parts:
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def evaluate_strategy_episode_predicate(
    program: Mapping[str, Any], *, move: Mapping[str, Any],
    environment: Mapping[str, Any], focal_move: Mapping[str, Any] | None = None,
    family_sha256: str | None = None,
) -> bool:
    """Execute the bounded strategy-law predicate language on one episode."""
    operator = str(program.get("operator") or "")
    if operator in {"all_of", "any_of"}:
        program_family = str(program.get("family_sha256") or "")
        if program_family and program_family != str(family_sha256 or ""):
            return False
        arguments = program.get("arguments")
        if not isinstance(arguments, list):
            raise ValueError(f"strategy predicate {operator} requires argument list")
        values = (
            evaluate_strategy_episode_predicate(
                argument, move=move, environment=environment,
                focal_move=focal_move, family_sha256=family_sha256,
            )
            for argument in arguments
        )
        return all(values) if operator == "all_of" else any(values)
    path = require_text(program.get("path"), f"strategy predicate {operator} path")
    observed = _episode_value(path, move=move, environment=environment)
    if operator == "eq":
        return observed == program.get("value")
    if operator == "ne":
        return observed != program.get("value")
    if operator == "same_as_focal":
        if focal_move is None:
            return False
        return observed is not None and observed == _episode_value(
            path, move=focal_move, environment=environment,
        )
    if operator == "is_exact_adoption":
        return observed == "exact_adoption_event"
    raise ValueError(f"unsupported strategy predicate operator: {operator}")


def _observational_behavior(row: Mapping[str, Any]) -> tuple[str, ...]:
    roles = tuple(sorted(
        f"{item.get('entity_id')}:{item.get('role')}:{','.join(item.get('event_sha256s') or ())}"
        for item in row.get("peer_roles") or () if isinstance(item, Mapping)
    ))
    return roles or ("no_peer_behavior_observed",)


def _frontier_representatives(
    projection: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    frontier_ids = set((projection.get("certificate") or {}).get("frontier_program_ids") or ())
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for raw in projection.get("projections") or ():
        row = dict(raw)
        row["required_relation_fields"] = sorted(set(row.get("required_relation_fields") or ()))
        row["observational_behavior"] = _observational_behavior(row)
        groups[row["observational_behavior"]].append(row)
    representatives, equivalents = [], []
    for behavior, members in sorted(groups.items()):
        if not any(str(row.get("program_id")) in frontier_ids for row in members):
            continue
        ordered = sorted(members, key=lambda row: (
            len(row["required_relation_fields"]),
            tuple(row["required_relation_fields"]), str(row.get("program_id")),
        ))
        representative = ordered[0]
        representatives.append(representative)
        equivalents.extend({
            "program_id": str(row["program_id"]),
            "representative_program_id": str(representative["program_id"]),
            "behavior_signature_sha256": stable_sha256(list(behavior)),
            "kind": "current_evidence_observational_equivalence",
        } for row in ordered[1:])
    return sorted(representatives, key=lambda row: str(row["program_id"])), sorted(
        equivalents, key=lambda row: row["program_id"],
    )


def _regularities(state: Mapping[str, Any], phenotype_shas: set[str]) -> list[dict[str, Any]]:
    rows = []
    for evaluation in state.get("evaluations") or ():
        regularity = dict((evaluation or {}).get("strategy_regularity") or {})
        if regularity.get("schema") != STRATEGY_REGULARITY_SCHEMA:
            continue
        identity = dict(regularity.get("regularity_identity") or {})
        if str(identity.get("mechanism_phenotype_sha256") or "") not in phenotype_shas:
            continue
        rows.append({
            "evaluation": dict(evaluation),
            "regularity": regularity,
            "phenotype_sha256": str(identity["mechanism_phenotype_sha256"]),
        })
    return sorted(rows, key=lambda row: str(row["regularity"].get("law_key") or ""))


def _baseline_rows(
    regularities: Iterable[Mapping[str, Any]], prior_candidate: Mapping[str, Any] | None,
) -> list[str]:
    if prior_candidate:
        return sorted(set(
            (prior_candidate.get("selection_boundary") or {}).get(
                "excluded_prospective_panel_row_sha256s", ()
            )
        ))
    return sorted({
        str(value)
        for row in regularities
        for value in ((row["regularity"].get("provenance") or {}).get(
            "prospective_panel_row_sha256s", ()
        ))
    })


def _gate(gate_id: str, passed: bool, observed: Any, required: Any, missing: str | None) -> dict[str, Any]:
    return {
        "gate_id": gate_id, "passed": bool(passed), "observed": observed,
        "required": required, "missing_evidence": None if passed else missing,
    }


def _evidence_gates(
    row: Mapping[str, Any], fields: set[str], families: list[dict[str, Any]],
    regularities: list[dict[str, Any]], baseline_rows: list[str], request_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    current_rows = sorted({
        str(value)
        for item in regularities
        for value in ((item["regularity"].get("provenance") or {}).get(
            "prospective_panel_row_sha256s", ()
        ))
    })
    new_rows = sorted(set(current_rows) - set(baseline_rows))
    aggregates_temporally_clean = not baseline_rows
    holdouts = [dict(item["regularity"].get("prospective_holdout") or {}) for item in regularities]
    observed_rows = [dict(value.get("observed") or {}) for value in holdouts]
    required_rows = [dict(value.get("required") or {}) for value in holdouts]
    required_treated = max((int(value.get("treated_units") or 0) for value in required_rows), default=4)
    required_controls = max((int(value.get("control_units") or 0) for value in required_rows), default=4)
    required_environments = max((int(value.get("transfer_environments") or 0) for value in required_rows), default=2)
    treated = sum(int(value.get("independent_treated_units") or 0) for value in observed_rows)
    controls = sum(int(value.get("bounded_control_units") or 0) for value in observed_rows)
    environments = sum(int(value.get("transfer_environments") or 0) for value in observed_rows)
    cells = sum(int(value.get("group_time_cells") or 0) for value in observed_rows)
    event_shas = sorted({
        str(value) for holdout in holdouts
        for value in holdout.get("independent_treatment_event_sha256s") or ()
    })
    multiplicity_rows = [
        dict(value)
        for item in regularities
        for value in ((item["evaluation"].get("multiplicity") or {}).get("rows") or ())
    ]
    counterexamples = [
        {**dict(value), "law_key": item["regularity"].get("law_key")}
        for item in regularities for value in item["regularity"].get("counterexamples") or ()
    ]
    omitted = sorted(set(STRATEGY_PHENOTYPE_DIMENSIONS) - fields)
    eligible_phenotypes = {
        item["phenotype_sha256"] for item in regularities
        if (item["regularity"].get("prospective_holdout") or {}).get("eligible")
    }
    family_by_sha = {row["mechanism_phenotype_sha256"]: row for row in families}
    diversity = {
        field: len({
            stable_sha256((family_by_sha[sha].get("mechanism_phenotype") or {}).get(
                "addressed_actor_kinds" if field == "addressed_actor_profile" else field,
                "unavailable",
            ))
            for sha in eligible_phenotypes if sha in family_by_sha
        })
        for field in omitted
    }
    classified = int(row.get("classified_coverage_count") or 0)
    causal_eligible = bool(regularities) and aggregates_temporally_clean
    gates = [
        _gate(
            "cohort_identity_coverage", classified >= request_count, classified, request_count,
            f"{max(0, request_count - classified)} planned peer classifications",
        ),
        _gate(
            "bounded_treated_and_controls",
            causal_eligible and treated >= required_treated and controls >= required_controls,
            {"independent_treated_units": treated, "bounded_control_units": controls},
            {"independent_treated_units": required_treated, "bounded_control_units": required_controls},
            (
                f"{max(0, required_treated - treated)} independent treated units and "
                f"{max(0, required_controls - controls)} bounded control units"
            ),
        ),
        _gate(
            "prospective_holdout", causal_eligible and bool(new_rows) and bool(event_shas) and cells > 0,
            {"new_panel_rows": len(new_rows), "independent_events": len(event_shas), "group_time_cells": cells},
            {"new_panel_rows": 1, "independent_events": 1, "group_time_cells": 1},
            (
                "availability-filtered raw panel rows are required because the selection baseline already contained outcomes"
                if baseline_rows and new_rows else "post-boundary treatment events and group-time outcome cells"
            ),
        ),
        _gate(
            "power_and_direction",
            causal_eligible and bool(holdouts) and all(value.get("eligible") for value in holdouts)
            and not counterexamples,
            [value.get("power_status") for value in holdouts], "all strata eligible at declared power",
            "a directionally supported effect with the declared minimum detectable effect",
        ),
        _gate(
            "multiplicity", bool(multiplicity_rows)
            and all(bool(value.get("rejected_at_alpha")) for value in multiplicity_rows),
            len(multiplicity_rows), "one BH-FDR decision for every scored law × environment trial",
            "settled law-environment p-values that survive the frozen BH-FDR family",
        ),
        _gate(
            "transfer_environments", causal_eligible and environments >= required_environments,
            environments, required_environments,
            f"{max(0, required_environments - environments)} independent transfer environments",
        ),
        _gate(
            "omitted_moderator_transfer", all(value >= 2 for value in diversity.values()),
            diversity, {field: 2 for field in omitted},
            "two prospectively eligible phenotype values for every omitted moderator",
        ),
    ]
    return gates, counterexamples


def _refinements(
    candidate_id: str, ast: Mapping[str, Any], counterexamples: Iterable[Mapping[str, Any]],
    available_at: str,
) -> list[dict[str, Any]]:
    rows = []
    for witness in counterexamples:
        field, value = str(witness.get("field") or ""), witness.get("value")
        if not field or value is None:
            continue
        body = {
            "parent_law_identity_sha256": candidate_id,
            "created_at": available_at, "not_before": available_at,
            "program": {
                "operator": "all_of", "output_type": "strategy_episode_predicate",
                "arguments": [dict(ast), {
                    "operator": "ne", "input_type": "strategy_environment",
                    "path": f"environment.{field}", "value": value,
                }],
            },
            "selection_counterexample": dict(witness),
            "status": "conjectured_refinement_awaiting_new_holdout",
            "capital_authority": False,
        }
        rows.append({**body, "refinement_sha256": stable_sha256(body)})
    return sorted(rows, key=lambda row: row["refinement_sha256"])


def _effect_estimate(
    regularities: list[dict[str, Any]], gates: list[dict[str, Any]],
    counterexamples: list[dict[str, Any]],
) -> dict[str, Any]:
    gate_by_id = {row["gate_id"]: row for row in gates}
    rows = []
    for item in regularities:
        regularity = item["regularity"]
        diagnostics = dict(regularity.get("diagnostics") or {})
        refs = sorted({
            str(value) for value in (regularity.get("provenance") or {}).get("source_refs") or ()
            if value
        })
        for effect in diagnostics.get("transport_effects") or ():
            estimate = effect.get("estimate") if isinstance(effect, Mapping) else None
            interval = effect.get("resampling_interval_95") if isinstance(effect, Mapping) else None
            environment = dict(effect.get("environment") or {}) if isinstance(effect, Mapping) else {}
            environment_sha = str(effect.get("environment_sha256") or "") if isinstance(effect, Mapping) else ""
            horizon = dict(effect.get("horizon") or {}) if isinstance(effect, Mapping) else {}
            if not (
                isinstance(estimate, (int, float))
                and isinstance(interval, list) and len(interval) == 2
                and regularity.get("outcome_unit") and environment
                and environment_sha == stable_sha256(environment) and refs
                and horizon.get("kind") == "calendar_days_after_adoption"
                and isinstance(horizon.get("minimum"), int)
                and isinstance(horizon.get("maximum"), int)
                and 0 <= horizon["minimum"] <= horizon["maximum"]
            ):
                continue
            rows.append({
                "law_key": regularity.get("law_key"),
                "metric_id": (regularity.get("regularity_identity") or {}).get("outcome_metric_id"),
                "unit": regularity["outcome_unit"],
                "estimate": float(estimate), "interval_95": [float(value) for value in interval],
                "environment": environment,
                "environment_sha256": environment_sha,
                "horizon": horizon,
                "group_time_cell_sha256s": list(effect.get("group_time_cell_sha256s") or ()),
                "treated_unit_ids": sorted(map(str, effect.get("treated_unit_ids") or ())),
                "control_unit_ids": sorted(map(str, effect.get("control_unit_ids") or ())),
                "source_refs": refs,
                "regularity_evidence_sha256": regularity.get("regularity_evidence_sha256"),
            })
    blockers = []
    if not rows:
        blockers.append("no_source_bound_effect_with_unit_interval_and_environment")
    for gate_id in (
        "bounded_treated_and_controls", "prospective_holdout", "power_and_direction",
        "multiplicity", "transfer_environments", "omitted_moderator_transfer",
    ):
        if not (gate_by_id.get(gate_id) or {}).get("passed"):
            blockers.append(gate_id)
    units = {row["unit"] for row in rows}
    metrics = {row["metric_id"] for row in rows}
    if len(units) > 1:
        blockers.append("incompatible_outcome_units")
    if len(metrics) > 1:
        blockers.append("incompatible_outcome_metrics")
    if counterexamples:
        blockers.append("transport_counterexample_present")
    body = {
        "status": "transported_magnitude_available" if not blockers else "proposal_only",
        "metric_id": next(iter(metrics), "earnings_durability"),
        "unit": next(iter(units), None),
        "estimates": rows,
        "blockers": sorted(set(blockers)),
        "consumer_contract": (
            "A consumer must bind one antecedent-matched target move plus the exact metric, unit, and causal environment."
        ),
        "valuation_consumable_without_binding": False,
    }
    return {**body, "effect_contract_sha256": stable_sha256(body)}


def assess_strategy_effect_transport(
    candidate: Mapping[str, Any], move_library: Mapping[str, Any], *,
    target_move_sha256: str, target_environment: Mapping[str, Any], as_of: str,
) -> dict[str, Any]:
    """Prove that one target move satisfies a frozen strategy-law antecedent."""

    _require_schema(candidate, STRATEGY_LAW_PROGRAM_SCHEMA, "strategy law candidate")
    _require_schema(move_library, STRATEGY_MOVE_LIBRARY_SCHEMA, "strategy move library")
    epoch = canonical_timestamp(as_of, "strategy effect target as_of")
    moves = {
        str(row.get("move_sha256") or ""): dict(row)
        for row in move_library.get("moves") or () if isinstance(row, Mapping)
    }
    target = moves.get(str(target_move_sha256))
    if target is None:
        raise ValueError("target strategy move is absent from the move library")
    environment = dict(target_environment)
    environment_sha = stable_sha256(environment)
    blockers = []
    if timestamp_key(epoch) < timestamp_key(str(candidate["not_before"])):
        blockers.append("law_not_yet_available")
    if target.get("evidence_epoch") and timestamp_key(str(target["evidence_epoch"])) > timestamp_key(epoch):
        blockers.append("target_move_not_yet_available")
    event = dict(target.get("implementation_event") or {})
    if (
        target.get("causal_panel_status") != "treatment_event_ready"
        or event.get("treatment_timing_status") != "exact_adoption_event"
    ):
        blockers.append("target_lacks_exact_adoption_event")
    if event.get("available_at") and timestamp_key(str(event["available_at"])) > timestamp_key(epoch):
        blockers.append("target_adoption_not_yet_available")

    cohort = dict(candidate.get("cohort_identity") or {})
    event_sha = str(event.get("implementation_event_sha256") or "")
    training_entities = set(map(str, cohort.get("training_entity_ids") or ()))
    training_events = set(map(str, cohort.get("implementation_event_sha256s") or ()))
    training_rows = set(map(str, cohort.get("training_panel_row_sha256s") or ()))
    if not event_sha:
        blockers.append("target_event_identity_missing")
    if str(target_move_sha256) in set(map(str, cohort.get("focal_move_sha256s") or ())):
        blockers.append("target_move_in_training_support")
    if str(target.get("entity_id") or "").upper() in training_entities:
        blockers.append("target_entity_in_training_support")
    if event_sha and event_sha in training_events:
        blockers.append("target_event_in_training_support")
    admitted_outcomes = [
        row for row in target.get("outcome_episodes") or ()
        if isinstance(row, Mapping)
        and row.get("available_at")
        and timestamp_key(str(row["available_at"])) <= timestamp_key(epoch)
    ]
    if admitted_outcomes:
        blockers.append("target_outcome_already_available")
    target_rows = {
        str(value)
        for row in admitted_outcomes
        for key in (
            "panel_row_sha256", "causal_panel_row_sha256",
            "group_time_cell_sha256", "episode_sha256",
        )
        if row.get(key)
        for value in (row[key],)
    }
    if target_rows & training_rows:
        blockers.append("target_panel_row_in_training_support")

    signature = str(target.get("mechanism_signature_sha256") or "")
    phenotype = str(target.get("mechanism_phenotype_sha256") or "")
    if signature not in set(candidate["law_identity"]["mechanism_signature_sha256s"]):
        blockers.append("target_mechanism_signature_mismatch")
    if (
        environment.get("mechanism_signature_sha256") != signature
        or environment.get("mechanism_phenotype_sha256") != phenotype
    ):
        blockers.append("target_causal_environment_mismatch")

    focal_shas = set(candidate["cohort_identity"]["focal_move_sha256s"])
    focal_moves = [
        move for move_sha, move in moves.items()
        if move_sha in focal_shas and move.get("mechanism_signature_sha256") == signature
    ]
    fields = list(candidate.get("required_relation_fields") or ())
    program = candidate.get("program")
    if not isinstance(program, Mapping):
        raise ValueError("strategy law candidate requires executable predicate program")
    matched_focals = [
        str(focal["move_sha256"])
        for focal in focal_moves
        if evaluate_strategy_episode_predicate(
            program, move=target, environment=environment, focal_move=focal,
            family_sha256=signature,
        )
    ]
    if not matched_focals:
        blockers.append("target_fails_frontier_selected_relation_program")
    matched_counterexamples = [
        dict(row) for row in candidate.get("counterexamples") or ()
        if row.get("field") and environment.get(str(row["field"])) == row.get("value")
    ]
    if matched_counterexamples:
        blockers.append("target_matches_transport_counterexample")
    body = {
        "schema": "jaggedthoughts-strategy-effect-transport-assessment-v1",
        "law_identity_sha256": candidate.get("law_identity_sha256"),
        "target_move_sha256": target_move_sha256,
        "target_entity_id": str(target.get("entity_id") or "").upper(),
        "target_event_sha256": event_sha or None,
        "target_evidence_epoch": target.get("evidence_epoch"),
        "target_event_available_at": event.get("available_at"),
        "target_outcome_available_count": len(admitted_outcomes),
        "target_environment": environment,
        "target_environment_sha256": environment_sha,
        "as_of": epoch,
        "required_relation_fields": fields,
        "matched_focal_move_sha256s": sorted(matched_focals),
        "matched_counterexamples": matched_counterexamples,
        "training_overlap": {
            "entity_ids": sorted({str(target.get("entity_id") or "").upper()} & training_entities),
            "move_sha256s": sorted({str(target_move_sha256)} & focal_shas),
            "event_sha256s": sorted({event_sha} & training_events) if event_sha else [],
            "panel_row_sha256s": sorted(target_rows & training_rows),
        },
        "status": "antecedent_matched" if not blockers else "proposal_only",
        "blockers": sorted(set(blockers)),
        "capital_authority": False,
    }
    return {**body, "assessment_sha256": stable_sha256(body)}


def bind_strategy_effect(
    candidate: Mapping[str, Any], move_library: Mapping[str, Any], *,
    target_move_sha256: str, target_environment: Mapping[str, Any],
    metric_id: str, unit: str, as_of: str,
) -> dict[str, Any]:
    """Bind one transported magnitude after target-antecedent verification."""

    contract = dict(candidate.get("effect_estimate") or {})
    assessment = assess_strategy_effect_transport(
        candidate, move_library, target_move_sha256=target_move_sha256,
        target_environment=target_environment, as_of=as_of,
    )
    matches = [
        row for row in contract.get("estimates") or ()
        if row.get("metric_id") == metric_id and row.get("unit") == unit
        and row.get("environment_sha256") == assessment["target_environment_sha256"]
        and row.get("environment") == assessment["target_environment"]
    ]
    blockers = [*contract.get("blockers", ()), *assessment["blockers"]]
    if contract.get("status") != "transported_magnitude_available":
        blockers.append("transported_magnitude_not_available")
    if not matches:
        blockers.append("target_metric_unit_or_environment_mismatch")
    body = {
        "law_identity_sha256": candidate.get("law_identity_sha256"),
        "antecedent_assessment": assessment,
        "target": {
            "metric_id": metric_id, "unit": unit,
            "move_sha256": target_move_sha256,
            "environment": assessment["target_environment"],
            "environment_sha256": assessment["target_environment_sha256"],
        },
        "status": "bound_for_model_proposal" if not blockers else "proposal_only",
        "transported_effects": matches if not blockers else [],
        "blockers": sorted(set(blockers)),
        "capital_authority": False,
    }
    return {**body, "binding_sha256": stable_sha256(body)}


def compile_causal_law_target_influence(
    discovery_candidates: Sequence[Mapping[str, Any]],
    induction: Mapping[str, Any], move_library: Mapping[str, Any],
    market_catalog: Mapping[str, Any], *, generated_at: str,
    per_law_adjustment: float = 0.025, max_total_adjustment: float = 0.05,
) -> dict[str, Any]:
    """Route out-of-sample causal strategy laws into bounded research ordering."""
    _require_schema(induction, STRATEGY_LAW_INDUCTION_SCHEMA, "strategy law induction")
    _require_schema(move_library, STRATEGY_MOVE_LIBRARY_SCHEMA, "strategy move library")
    if market_catalog.get("schema") != "jaggedthoughts-public-market-catalog-v1":
        raise ValueError("market catalog schema must be jaggedthoughts-public-market-catalog-v1")
    epoch = canonical_timestamp(generated_at, "causal law influence generated_at")
    increment = require_finite(per_law_adjustment, "causal law per-law adjustment")
    maximum = require_finite(max_total_adjustment, "causal law total adjustment")
    if not 0 < increment <= maximum <= 0.10:
        raise ValueError("causal law influence bounds must satisfy 0 < per-law <= total <= 0.10")

    moves_by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in move_library.get("moves") or ():
        if isinstance(raw, Mapping) and raw.get("entity_id") and raw.get("move_sha256"):
            moves_by_entity[str(raw["entity_id"]).upper()].append(dict(raw))
    securities = {
        str(row.get("symbol") or "").upper(): dict(row)
        for row in market_catalog.get("securities") or ()
        if isinstance(row, Mapping) and row.get("symbol")
    }
    laws = sorted((
        dict(row) for row in induction.get("candidates") or ()
        if isinstance(row, Mapping)
        and row.get("policy_review_eligible")
        and (row.get("effect_estimate") or {}).get("status")
        == "transported_magnitude_available"
    ), key=lambda row: str(row.get("law_identity_sha256") or ""))
    attempts: list[dict[str, Any]] = []
    summaries = []
    for raw_candidate in discovery_candidates:
        candidate = dict(raw_candidate)
        entity = require_text(candidate.get("entity_id"), "causal law target entity_id").upper()
        candidate_sha = require_text(
            candidate.get("candidate_sha256"), "causal law target candidate_sha256",
        )
        candidate_body = {key: value for key, value in candidate.items() if key != "candidate_sha256"}
        if stable_sha256(candidate_body) != candidate_sha:
            raise ValueError("causal law influence candidate content hash mismatch")
        candidate_as_of = canonical_timestamp(
            candidate.get("as_of"), "causal law target candidate as_of",
        )
        future_candidate_inputs = sorted({
            str(row.get("available_at"))
            for row in candidate.get("input_compatibility") or ()
            if isinstance(row, Mapping) and row.get("available_at")
            and timestamp_key(str(row["available_at"])) > timestamp_key(candidate_as_of)
        })
        security = securities.get(entity)
        candidate_attempts = []
        for law in laws:
            law_body = {key: value for key, value in law.items() if key != "candidate_sha256"}
            if law.get("candidate_sha256") != stable_sha256(law_body):
                raise ValueError("causal law program content hash mismatch")
            for estimate in (law.get("effect_estimate") or {}).get("estimates") or ():
                if not isinstance(estimate, Mapping):
                    continue
                effect_horizon = dict(estimate.get("horizon") or {})
                for move in sorted(moves_by_entity.get(entity, ()), key=lambda row: str(row["move_sha256"])):
                    target_environment = {
                        "industry_id": str((security or {}).get("industry") or ""),
                        "mechanism_signature_sha256": str(
                            move.get("mechanism_signature_sha256") or ""
                        ),
                        "mechanism_phenotype_sha256": str(
                            move.get("mechanism_phenotype_sha256") or ""
                        ),
                    }
                    assessment = assess_strategy_effect_transport(
                        law, move_library,
                        target_move_sha256=str(move["move_sha256"]),
                        target_environment=target_environment, as_of=epoch,
                    )
                    expected_contract_direction = (
                        "increase" if (law.get("falsifiable_consequence") or {}).get(
                            "expected_direction"
                        ) == "positive" else "decrease"
                    )
                    matching_contracts = sorted((
                        dict(contract) for contract in move.get("outcome_contracts") or ()
                        if isinstance(contract, Mapping)
                        and contract.get("metric_id") == estimate.get("metric_id")
                        and contract.get("unit") == estimate.get("unit")
                        and contract.get("direction") == expected_contract_direction
                        and isinstance(contract.get("horizon_days"), int)
                        and effect_horizon.get("kind") == "calendar_days_after_adoption"
                        and int(effect_horizon.get("minimum", -1))
                        <= int(contract["horizon_days"])
                        <= int(effect_horizon.get("maximum", -1))
                    ), key=lambda row: str(row.get("contract_sha256") or ""))
                    contract = matching_contracts[0] if matching_contracts else None
                    blockers = list(assessment["blockers"])
                    if security is None:
                        blockers.append("target_market_identity_missing")
                    elif security.get("available_at") and timestamp_key(
                        str(security["available_at"])
                    ) > timestamp_key(epoch):
                        blockers.append("target_market_identity_not_yet_available")
                    if timestamp_key(candidate_as_of) > timestamp_key(epoch):
                        blockers.append("target_candidate_not_yet_available")
                    if future_candidate_inputs:
                        blockers.append("target_candidate_contains_future_input")
                    if str(move.get("entity_id") or "").upper() != entity:
                        blockers.append("candidate_move_entity_mismatch")
                    if dict(estimate.get("environment") or {}) != target_environment:
                        blockers.append("target_causal_environment_mismatch")
                    if contract is None:
                        blockers.append("target_metric_unit_horizon_or_direction_mismatch")
                    blockers = sorted(set(blockers))
                    body = {
                        "schema": CAUSAL_LAW_TARGET_INFLUENCE_SCHEMA,
                        "decision_epoch": epoch,
                        "law_identity_sha256": law.get("law_identity_sha256"),
                        "law_candidate_sha256": law.get("candidate_sha256"),
                        "candidate": {
                            "candidate_id": candidate.get("candidate_id"),
                            "candidate_sha256": candidate_sha,
                            "entity_id": entity,
                            "as_of": candidate_as_of,
                        },
                        "target": {
                            "move_sha256": move.get("move_sha256"),
                            "event_sha256": assessment.get("target_event_sha256"),
                            "environment": target_environment,
                            "environment_sha256": stable_sha256(target_environment),
                            "outcome_contract_sha256": (contract or {}).get("contract_sha256"),
                        },
                        "effect": {
                            "metric_id": estimate.get("metric_id"),
                            "unit": estimate.get("unit"),
                            "interval_95": list(estimate.get("interval_95") or ()),
                            "horizon": effect_horizon,
                        },
                        "compatibility": {
                            "metric": estimate.get("metric_id") == (contract or {}).get("metric_id"),
                            "unit": estimate.get("unit") == (contract or {}).get("unit"),
                            "horizon": bool(contract),
                            "environment": dict(estimate.get("environment") or {})
                            == target_environment,
                            "direction": (contract or {}).get("direction")
                            == expected_contract_direction,
                        },
                        "chronology": {
                            "law_not_before": law.get("not_before"),
                            "candidate_as_of": candidate_as_of,
                            "candidate_future_input_available_at": future_candidate_inputs,
                            "market_identity_available_at": (security or {}).get("available_at"),
                            "move_evidence_epoch": move.get("evidence_epoch"),
                            "event_available_at": assessment.get("target_event_available_at"),
                            "target_outcome_available_count": assessment.get(
                                "target_outcome_available_count"
                            ),
                        },
                        "entity_identity": {
                            "candidate_entity_id": entity,
                            "move_entity_id": str(move.get("entity_id") or "").upper(),
                            "matched": str(move.get("entity_id") or "").upper() == entity,
                        },
                        "antecedent_assessment_sha256": assessment["assessment_sha256"],
                        "training_overlap": assessment["training_overlap"],
                        "blockers": blockers,
                        "status": "eligible_research_influence" if not blockers else "suppressed",
                        "research_priority_adjustment": increment if not blockers else 0.0,
                        "research_priority_only": True,
                        "screen_status_before": candidate.get("screen_status"),
                        "screen_status_after": candidate.get("screen_status"),
                        "authority": "paper_research_priority_only",
                        "capital_authority": False,
                    }
                    receipt = {**body, "influence_sha256": stable_sha256(body)}
                    attempts.append(receipt)
                    candidate_attempts.append(receipt)
        eligible_by_law = {}
        for row in sorted(candidate_attempts, key=lambda value: value["influence_sha256"]):
            if row["status"] == "eligible_research_influence":
                eligible_by_law.setdefault(str(row["law_identity_sha256"]), row)
        adjustment = min(maximum, increment * len(eligible_by_law))
        summaries.append({
            "candidate_id": candidate.get("candidate_id"),
            "candidate_sha256": candidate_sha, "entity_id": entity,
            "adjustment": adjustment,
            "active_law_count": len(eligible_by_law),
            "influence_sha256s": sorted(
                row["influence_sha256"] for row in eligible_by_law.values()
            ),
            "screen_status_before": candidate.get("screen_status"),
            "screen_status_after": candidate.get("screen_status"),
            "authority": "paper_research_priority_only", "capital_authority": False,
        })
    body = {
        "schema": CAUSAL_LAW_INFLUENCE_SET_SCHEMA,
        "generated_at": epoch,
        "input": {
            "induction_sha256": induction.get("induction_sha256"),
            "move_library_sha256": move_library.get("library_sha256"),
            "market_catalog_sha256": market_catalog.get("catalog_sha256"),
        },
        "candidate_count": len(summaries),
        "active_application_count": sum(
            row["status"] == "eligible_research_influence" for row in attempts
        ),
        "active_candidate_count": sum(bool(row["active_law_count"]) for row in summaries),
        "candidates": summaries,
        "attempts": sorted(attempts, key=lambda row: row["influence_sha256"]),
        "bounds": {
            "per_law_adjustment": increment, "max_total_adjustment": maximum,
        },
        "status": "active" if any(row["active_law_count"] for row in summaries) else "no_eligible_target",
        "research_priority_only": True,
        "screen_status_mutable": False,
        "authority": "paper_research_priority_only", "capital_authority": False,
    }
    return {**body, "influence_set_sha256": stable_sha256(body)}


def compile_strategy_law_induction(
    move_library: Mapping[str, Any], cohort_plan: Mapping[str, Any],
    projection_frontier: Mapping[str, Any], learning_state: Mapping[str, Any],
    *, generated_at: str, prior: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind frozen projection programs to prospective causal-law gates."""

    _require_schema(move_library, STRATEGY_MOVE_LIBRARY_SCHEMA, "strategy move library")
    _require_schema(cohort_plan, STRATEGY_COHORT_PLAN_SCHEMA, "strategy cohort plan")
    _require_schema(projection_frontier, _PROJECTION_SCHEMA, "strategy projection frontier")
    _require_schema(learning_state, LEARNING_STATE_SCHEMA, "institutional learning state")
    if prior is not None:
        _require_schema(prior, STRATEGY_LAW_INDUCTION_SCHEMA, "prior strategy law induction")
    if projection_frontier.get("plan_sha256") != cohort_plan.get("plan_sha256"):
        raise ValueError("strategy law induction crossed cohort-plan identity")
    epoch = canonical_timestamp(generated_at, "strategy law induction generated_at")
    source_boundary, source_availability = _source_boundary(cohort_plan, projection_frontier, epoch)
    families = _families(cohort_plan)
    if not families:
        raise ValueError("strategy law induction requires a focal mechanism family")
    move_by_sha = {
        str(row.get("move_sha256")): dict(row)
        for row in move_library.get("moves") or ()
        if isinstance(row, Mapping) and row.get("move_sha256")
    }
    move_shas = set(move_by_sha)
    unknown_focal = {
        value for family in families for value in family["focal_move_sha256s"] if value not in move_shas
    }
    if unknown_focal:
        raise ValueError("strategy law induction focal moves are absent from the move library")
    phenotype_shas = {row["mechanism_phenotype_sha256"] for row in families}
    regularities = _regularities(learning_state, phenotype_shas)
    prior_by_identity = {
        str(row.get("law_identity_sha256")): row for row in (prior or {}).get("candidates") or ()
    }
    request_count = len(cohort_plan.get("requests") or ())
    programs, equivalence = _frontier_representatives(projection_frontier)
    source_frontier_ids = set(
        (projection_frontier.get("certificate") or {}).get("frontier_program_ids") or ()
    )
    candidates = []
    for row in programs:
        fields = set(row["required_relation_fields"])
        identity = {
            "mechanism_signature_sha256s": sorted({
                family["mechanism_signature_sha256"] for family in families
            }),
            "projection_program_id": str(row["program_id"]),
            "outcome_metric_id": "earnings_durability",
            "estimator_id": "group_time_att_unadjusted",
        }
        identity_sha = stable_sha256(identity)
        previous = prior_by_identity.get(identity_sha)
        created_at = str(previous.get("created_at")) if previous else epoch
        not_before = str(previous.get("not_before")) if previous else epoch
        ast = _program_ast(families, fields)
        baseline = _baseline_rows(regularities, previous)
        gates, counterexamples = _evidence_gates(
            row, fields, families, regularities, baseline, request_count,
        )
        effect_estimate = _effect_estimate(regularities, gates, counterexamples)
        focal_move_shas = sorted({
            value for family in families for value in family["focal_move_sha256s"]
        })
        training_entities = sorted({
            str(peer.get("entity_id") or "").upper()
            for peer in row.get("peer_roles") or ()
            if isinstance(peer, Mapping) and peer.get("entity_id")
        } | {
            str(move_by_sha[value].get("entity_id") or "").upper()
            for value in focal_move_shas
            if value in move_by_sha and move_by_sha[value].get("entity_id")
        })
        training_events = sorted({
            value for family in families for value in family["implementation_event_sha256s"]
        } | {
            str(event)
            for peer in row.get("peer_roles") or () if isinstance(peer, Mapping)
            for event in peer.get("event_sha256s") or ()
        })
        training_panel_rows = sorted({
            *baseline,
            *(
                str(cell)
                for estimate in effect_estimate.get("estimates") or ()
                for cell in estimate.get("group_time_cell_sha256s") or ()
            ),
        })
        eligible = all(value["passed"] for value in gates) and not counterexamples
        status = (
            "challenged_by_counterexample" if counterexamples else
            "eligible_for_policy_review" if eligible else
            "blocked_awaiting_prospective_outcomes"
            if not any((item["regularity"].get("provenance") or {}).get(
                "prospective_panel_row_sha256s"
            ) for item in regularities) else "blocked_inference_gates"
        )
        candidate = {
            "schema": STRATEGY_LAW_PROGRAM_SCHEMA,
            "law_identity": identity, "law_identity_sha256": identity_sha,
            "created_at": created_at, "not_before": not_before,
            "source_projection_program_ids": sorted({
                str(row["program_id"]), *(
                    value["program_id"] for value in equivalence
                    if value["representative_program_id"] == row["program_id"]
                ),
            }),
            "source_frontier_program_ids": sorted(
                source_frontier_ids & {
                    str(row["program_id"]), *(
                        value["program_id"] for value in equivalence
                        if value["representative_program_id"] == row["program_id"]
                    ),
                }
            ),
            "required_relation_fields": sorted(fields),
            "program": ast,
            "falsifiable_consequence": {
                "outcome_metric_id": "earnings_durability", "expected_direction": "positive",
                "estimator": "group_time_att_unadjusted",
                "comparator_identity": "bounded_never_or_not_yet_treated",
                "minimum_meaningful_effect": 0.05,
            },
            "cohort_identity": {
                "plan_sha256": cohort_plan["plan_sha256"],
                "request_sha256s": sorted(str(value["request_sha256"]) for value in cohort_plan.get("requests") or ()),
                "peer_roles": sorted(row.get("peer_roles") or (), key=lambda value: (
                    str(value.get("entity_id")), str(value.get("role")),
                )),
                "focal_move_sha256s": focal_move_shas,
                "implementation_event_sha256s": training_events,
                "training_entity_ids": training_entities,
                "training_panel_row_sha256s": training_panel_rows,
            },
            "selection_boundary": {
                "source_available_at": source_availability,
                "source_boundary": source_boundary,
                "excluded_prospective_panel_row_sha256s": baseline,
                "rule": "Outcome evidence cannot choose a program; only rows arriving after not_before may challenge or support it.",
            },
            "evidence_gates": gates,
            "counterexamples": counterexamples,
            "cegar_refinements": _refinements(identity_sha, ast, counterexamples, epoch),
            "effect_estimate": effect_estimate,
            "missing_evidence": [
                value["missing_evidence"] for value in gates if not value["passed"]
            ],
            "status": status, "policy_review_eligible": eligible,
            "authority": "strategy_learning_shadow_only", "capital_authority": False,
        }
        target_applications = []
        if effect_estimate["status"] == "transported_magnitude_available":
            for estimate in effect_estimate["estimates"]:
                environment = dict(estimate["environment"])
                for move in move_library.get("moves") or ():
                    if (
                        not isinstance(move, Mapping)
                        or move.get("mechanism_phenotype_sha256")
                        != environment.get("mechanism_phenotype_sha256")
                    ):
                        continue
                    target_applications.append(bind_strategy_effect(
                        candidate, move_library,
                        target_move_sha256=str(move.get("move_sha256") or ""),
                        target_environment=environment,
                        metric_id=str(estimate["metric_id"]), unit=str(estimate["unit"]),
                        as_of=epoch,
                    ))
        candidate["target_applications"] = sorted(
            target_applications, key=lambda value: value["binding_sha256"],
        )
        candidates.append({**candidate, "candidate_sha256": stable_sha256(candidate)})
    candidates.sort(key=lambda row: row["law_identity_sha256"])
    subsumption = []
    for general in candidates:
        left = set(general["required_relation_fields"])
        for specific in candidates:
            right = set(specific["required_relation_fields"])
            if left < right:
                subsumption.append({
                    "general_law_identity_sha256": general["law_identity_sha256"],
                    "specific_law_identity_sha256": specific["law_identity_sha256"],
                    "added_relation_fields": sorted(right - left),
                    "meaning": "logical antecedent subsumption; outcome transport remains unproven",
                })
    body = {
        "schema": STRATEGY_LAW_INDUCTION_SCHEMA, "generated_at": epoch,
        "input": {
            "move_library_sha256": move_library.get("library_sha256"),
            "cohort_plan_sha256": cohort_plan.get("plan_sha256"),
            "projection_frontier_sha256": projection_frontier.get("projection_frontier_sha256"),
            "learning_state_sha256": learning_state.get("state_sha256"),
            "prior_induction_sha256": (prior or {}).get("induction_sha256"),
        },
        "type_contract": {
            "antecedent": "strategy_episode_predicate",
            "phenotype": "strategy_phenotype", "environment": "strategy_environment",
            "move": "strategy_move", "outcome": "typed_metric_delta",
            "operators": ["eq", "same_as_focal", "is_exact_adoption", "all_of", "any_of", "ne"],
        },
        "source_program_count": len(projection_frontier.get("projections") or ()),
        "source_frontier_count": len((projection_frontier.get("certificate") or {}).get("frontier_program_ids") or ()),
        "candidate_count": len(candidates),
        "eligible_candidate_count": sum(row["policy_review_eligible"] for row in candidates),
        "challenged_candidate_count": sum(row["status"] == "challenged_by_counterexample" for row in candidates),
        "candidates": candidates,
        "frontier_closure": {
            "source_certificate_sha256": (projection_frontier.get("certificate") or {}).get("certificate_sha256"),
            "observational_equivalence": equivalence,
            "subsumption": sorted(subsumption, key=lambda row: (
                row["general_law_identity_sha256"], row["specific_law_identity_sha256"],
            )),
            "reopen_rule": "A new peer role or outcome behavior reopens observational equivalence and frontier membership.",
        },
        "status": (
            "policy_review_candidates_available"
            if any(row["policy_review_eligible"] for row in candidates)
            else "falsifiable_laws_blocked_on_declared_evidence"
        ),
        "next_activation": sorted({
            gap for row in candidates for gap in row["missing_evidence"]
        }),
        "authority": "strategy_learning_shadow_only", "capital_authority": False,
    }
    return {**body, "induction_sha256": stable_sha256(body)}


__all__ = [
    "CAUSAL_LAW_INFLUENCE_SET_SCHEMA", "CAUSAL_LAW_TARGET_INFLUENCE_SCHEMA",
    "STRATEGY_LAW_INDUCTION_SCHEMA", "STRATEGY_LAW_PROGRAM_SCHEMA",
    "assess_strategy_effect_transport", "bind_strategy_effect",
    "compile_causal_law_target_influence",
    "compile_strategy_law_induction", "evaluate_strategy_episode_predicate",
]
