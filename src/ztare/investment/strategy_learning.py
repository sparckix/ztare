"""Outcome-linked, transport-bounded memory for company strategy moves."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from functools import lru_cache
from itertools import combinations
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.strategy import (
    CandidateEvaluation, FrontierScope, Neighborhood, OperatorGrammar,
    RepresentationAudit, TypedOperator, TypedTerminal, build_typed_program,
    compile_enumeration_result, compile_jaggedthoughts_frontier,
)

from .contracts import canonical_timestamp, require_finite, require_refs, require_text, timestamp_key
from .strategy_event_refinement import (
    apply_strategy_event_refinements,
    effective_exact_implementation_event,
)
from .strategy_options import IMPLEMENTATION_MODES, RESULT_SCHEMA


STRATEGY_MOVE_LIBRARY_SCHEMA = "jaggedthoughts-strategy-move-library-v1"
STRATEGY_MOVE_OUTCOME_SCHEMA = "jaggedthoughts-strategy-move-outcome-v1"
STRATEGY_SCENARIO_CALIBRATION_SCHEMA = (
    "jaggedthoughts-strategy-scenario-direction-calibration-v1"
)
STRATEGY_OUTCOME_REQUEST_SCHEMA = "jaggedthoughts-strategy-outcome-research-request-v2"
STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA = (
    "jaggedthoughts-strategy-program-adoption-research-request-v1"
)
STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA = (
    "jaggedthoughts-strategy-program-adoption-research-result-v1"
)
STRATEGY_PROGRAM_OUTCOME_PLAN_SCHEMA = "jaggedthoughts-strategy-program-outcome-plan-v1"
STRATEGY_COHORT_REQUEST_SCHEMA = "jaggedthoughts-strategy-cohort-research-request-v2"
STRATEGY_COHORT_RESULT_SCHEMA = "jaggedthoughts-strategy-cohort-research-result-v2"
STRATEGY_COHORT_PLAN_SCHEMA = "jaggedthoughts-strategy-cohort-research-plan-v2"
STRATEGY_COHORT_QUERY_SCHEMA = "jaggedthoughts-strategy-cohort-query-v1"
STRATEGY_COHORT_COVERAGE_CHAIN_SCHEMA = "jaggedthoughts-strategy-cohort-coverage-chain-v1"
STRATEGY_COHORT_IMPLEMENTATION_STATES = frozenset({
    "committed", "executing", "operational", "completed", "discontinued",
})
STRATEGY_COHORT_RELATIONS = frozenset({"same", "adjacent", "different", "unclear"})
STRATEGY_PHENOTYPE_DIMENSIONS = (
    "strategy_form", "addressed_actor_profile", "implementation_mode",
    "operating_object_scope",
)
STRATEGY_MOVE_CANDIDATE_LINEAGE_FIELDS = (
    "candidate_leaf", "candidate_sha256", "source_request_sha256",
    "source_dossier_sha256", "strategy_frontier_request_sha256",
)


def unique_current_candidates_by_entity(
    candidates: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], frozenset[str]]:
    """Index entities only when one current candidate owns the identity."""

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            grouped[str(candidate.get("entity_id") or "").upper()].append(candidate)
    ambiguous = frozenset(key for key, rows in grouped.items() if key and len(rows) != 1)
    return ({key: rows[0] for key, rows in grouped.items() if key and len(rows) == 1}, ambiguous)


def candidate_bound_strategy_move(
    move: Mapping[str, Any], *, candidate_leaf: str, candidate_sha256: str,
    compatible_source_request_sha256s: Iterable[str] = (),
) -> bool:
    """Return whether a move belongs to the market epoch or its business basis."""

    lineage = [str(move.get(field) or "") for field in STRATEGY_MOVE_CANDIDATE_LINEAGE_FIELDS]
    return (
        all(len(value) == 64 and all(character in "0123456789abcdef" for character in value.lower())
            for value in lineage)
        and (
            (lineage[0] == candidate_leaf and lineage[1] == candidate_sha256)
            or lineage[2] in set(compatible_source_request_sha256s)
        )
    )


def compatible_strategy_source_request_sha256s(
    workspace: str | Path, *, candidate_id: str, candidate_leaf: str,
    candidate_sha256: str,
) -> frozenset[str]:
    """Find source requests sharing the current candidate's frozen business basis."""

    root = Path(workspace).expanduser().resolve()
    directory = root / "research_jobs" / "requests"
    directory_epoch_ns = directory.stat().st_mtime_ns if directory.exists() else -1
    requests = [
        (row, basis_sha) for row, basis_sha in _request_basis_rows(
            str(directory), directory_epoch_ns,
        ) if row.get("candidate_id") == candidate_id
    ]
    current_bases = {
        basis_sha for row, basis_sha in requests
        if row.get("candidate_leaf") == candidate_leaf
        and row.get("candidate_sha256") == candidate_sha256
    }
    if len(current_bases) != 1:
        return frozenset()
    return frozenset(
        str(row["request_sha256"]) for row, basis_sha in requests
        if basis_sha in current_bases
    )


def covered_strategy_source_request_sha256s(
    workspace: str | Path, *, candidate_leaf: str,
) -> frozenset[str]:
    """Resolve the monitored dossier explicitly covering a candidate epoch."""

    return frozenset(covered_strategy_source_request_lineage(
        workspace, candidate_leaf=candidate_leaf,
    ))


def covered_strategy_source_request_lineage(
    workspace: str | Path, *, candidate_leaf: str,
) -> dict[str, str]:
    """Map an admissible covered request to its coverage-leaf receipt."""

    import yaml

    from .golden_store import GoldenStore, research_evidence_is_admissible

    root = Path(workspace).expanduser().resolve()
    try:
        config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8")) or {}
        owner = require_text(config.get("owner"), "investment workspace owner")
        store = GoldenStore(
            root / str(config.get("golden_store") or "state/golden_store.sqlite3")
        )
        coverage = store.head(
            owner, "research_evidence_coverage", f"research-coverage:{candidate_leaf}",
        )
        payload = dict(coverage.get("payload") or {})
        dossier_leaf = str(payload.get("prior_dossier_leaf") or "")
        if (
            not payload.get("covered")
            or payload.get("candidate_leaf") != candidate_leaf
            or not dossier_leaf
            or not research_evidence_is_admissible(
                store, owner=owner, target_leaf=dossier_leaf,
            )
        ):
            return {}
        dossier = store.get_leaf(dossier_leaf)
        request_sha = str((dossier.get("payload") or {}).get("request_sha256") or "")
        return (
            {request_sha: str(coverage["leaf_sha256"])}
            if len(request_sha) == 64
            and all(character in "0123456789abcdef" for character in request_sha.lower())
            else {}
        )
    except (KeyError, OSError, TypeError, ValueError):
        return {}


@lru_cache(maxsize=8)
def _request_basis_rows(
    directory: str, directory_epoch_ns: int,
) -> tuple[tuple[dict[str, Any], str], ...]:
    """Validate immutable request bases once per on-disk request epoch."""

    from .research_jobs import validated_research_request_basis_sha256

    rows = []
    root = Path(directory)
    for path in sorted(root.glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(row, Mapping):
                rows.append((dict(row), validated_research_request_basis_sha256(row)))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return tuple(rows)


def strategy_choice_admission_status(
    library: Mapping[str, Any], move: Mapping[str, Any], *, as_of: str | None = None,
) -> str | None:
    """Admit a frozen current choice, or an older choice preserved to current."""

    entity_id = str(move.get("entity_id") or "")
    frontier_sha = str(move.get("strategy_frontier_sha256") or "")
    choice_sha = str(move.get("strategy_choice_identity_sha256") or "")
    if not entity_id or not frontier_sha or not choice_sha:
        return None
    try:
        cutoff = timestamp_key(canonical_timestamp(as_of, "strategy choice as_of")) if as_of else None
        entity_moves = [
            row for row in library.get("moves") or ()
            if isinstance(row, Mapping)
            and str(row.get("entity_id") or "") == entity_id
            and (
                cutoff is None
                or timestamp_key(str(row.get("evidence_epoch") or "1970-01-01T00:00:00Z"))
                <= cutoff
            )
        ]
    except ValueError:
        return None
    try:
        frontiers = sorted({
            (
                timestamp_key(str(row.get("evidence_epoch") or "1970-01-01T00:00:00Z")),
                str(row.get("strategy_frontier_sha256") or ""),
            )
            for row in entity_moves
        })
    except ValueError:
        return None
    if not frontiers or frontier_sha not in {sha for _, sha in frontiers}:
        return None
    option_id = str(move.get("option_id") or "")
    if not any(
        str(row.get("strategy_frontier_sha256") or "") == frontier_sha
        and str(row.get("strategy_choice_identity_sha256") or "") == choice_sha
        and (not option_id or str(row.get("option_id") or "") == option_id)
        for row in entity_moves
    ):
        return None
    latest_frontier = frontiers[-1][1]
    if frontier_sha == latest_frontier:
        return "current_frontier_frozen"

    start = next(index for index, (_, sha) in enumerate(frontiers) if sha == frontier_sha)
    for (earlier_epoch, earlier_sha), (later_epoch, later_sha) in zip(
        frontiers[start:], frontiers[start + 1:], strict=False,
    ):
        matches = [
            row for row in library.get("frontier_evolution") or ()
            if isinstance(row, Mapping)
            and str(row.get("entity_id") or "") == entity_id
            and str(row.get("earlier_strategy_frontier_sha256") or "") == earlier_sha
            and str(row.get("later_strategy_frontier_sha256") or "") == later_sha
        ]
        if len(matches) != 1:
            return None
        evolution = matches[0]
        body = {key: value for key, value in evolution.items() if key != "evolution_sha256"}
        try:
            declared_earlier = timestamp_key(str(evolution["earlier_evidence_epoch"]))
            declared_later = timestamp_key(str(evolution["later_evidence_epoch"]))
        except (KeyError, ValueError):
            return None
        if (
            evolution.get("evolution_sha256") != stable_sha256(body)
            or not declared_earlier < declared_later
            or declared_earlier != earlier_epoch
            or declared_later != later_epoch
        ):
            return None
        continuity = next((
            row for row in evolution.get("strategy_choice_continuity") or ()
            if isinstance(row, Mapping)
            and row.get("status") == "preserved"
            and str(row.get("earlier_strategy_choice_identity_sha256") or "") == choice_sha
            and (not option_id or str(row.get("option_id") or "") == option_id)
        ), None)
        if continuity is None:
            return None
        choice_sha = str(continuity.get("later_strategy_choice_identity_sha256") or "")
        if not any(
            str(row.get("strategy_frontier_sha256") or "") == later_sha
            and str(row.get("strategy_choice_identity_sha256") or "") == choice_sha
            and (not option_id or str(row.get("option_id") or "") == option_id)
            for row in entity_moves
        ):
            return None
    return "preserved_to_current_frontier"


def strategy_cohort_query_identity(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return the stable research-question identity of a cohort request revision."""
    if request.get("schema") != STRATEGY_COHORT_REQUEST_SCHEMA:
        raise ValueError("strategy cohort query requires a cohort research request")
    event_shas = sorted({
        require_text(
            (row.get("implementation_event") or {}).get("implementation_event_sha256"),
            "strategy cohort focal implementation event hash",
        )
        for row in request.get("focal_moves") or ()
        if isinstance(row, Mapping) and isinstance(row.get("implementation_event"), Mapping)
    })
    body = {
        "schema": STRATEGY_COHORT_QUERY_SCHEMA,
        "peer_entity_id": require_text(request.get("peer_entity_id"), "strategy cohort peer"),
        "mechanism_signature_sha256": require_text(
            request.get("mechanism_signature_sha256"), "strategy cohort mechanism signature",
        ),
        "mechanism_phenotype_sha256": require_text(
            request.get("mechanism_phenotype_sha256"), "strategy cohort phenotype",
        ),
        "industry_id": require_text(request.get("industry_id"), "strategy cohort industry"),
        "focal_implementation_event_sha256s": event_shas,
        "required_source_classes": sorted({
            require_text(value, "strategy cohort source class")
            for value in request.get("required_source_classes") or ()
        }),
        "search_start_at": canonical_timestamp(
            request.get("search_start_at"), "strategy cohort query search start",
        ),
    }
    return {**body, "query_sha256": stable_sha256(body)}


def strategy_option_comparison_identity(
    frontier: Mapping[str, Any], option: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the shared phenotype and environment identity for one option."""
    pressure_kind = {
        str(row.get("id")): str(row.get("actor_kind"))
        for row in (frontier.get("industry_state") or {}).get("pressures") or ()
        if isinstance(row, Mapping) and row.get("id") and row.get("actor_kind")
    }
    addressed_actor_kinds = sorted({
        pressure_kind.get(str(value), "unclassified")
        for value in option.get("addresses") or ()
    })
    environment = {
        "industry_boundary": str((frontier.get("industry_state") or {}).get("boundary") or ""),
        "addressed_actor_kinds": addressed_actor_kinds,
        "industry_actor_kinds": sorted(set(pressure_kind.values())),
    }
    mechanism = option.get("mechanism")
    if isinstance(mechanism, Mapping):
        choice = {
            "option_id": str(option.get("option_id") or "").strip().casefold(),
            "kind": str(option.get("kind") or "unclassified").strip().casefold(),
            "action": str(mechanism["action"]).strip().casefold(),
            "economic_bridge": str(mechanism["economic_bridge"]).strip().casefold(),
            "object_id": str(mechanism.get("object_id") or "unspecified").strip().casefold(),
        }
        signature = {
            "action": mechanism["action"],
            "economic_bridge": mechanism["economic_bridge"],
        }
        phenotype = {
            **signature,
            "strategy_form": str(option.get("kind") or "unclassified"),
            "addressed_actor_kinds": addressed_actor_kinds,
            "implementation_mode": str(
                (option.get("implementation_event") or {}).get("implementation_mode")
                or "unspecified"
            ),
        }
    else:
        choice = {
            "option_id": str(option.get("option_id") or "").strip().casefold(),
            "kind": str(option.get("kind") or "unclassified").strip().casefold(),
            "legacy": True,
        }
        signature = {"legacy_kind": str(option.get("kind") or "unclassified")}
        phenotype = signature
    return {
        "strategy_choice_identity": choice,
        "strategy_choice_identity_sha256": stable_sha256(choice),
        "mechanism_signature": signature,
        "mechanism_signature_sha256": stable_sha256(signature),
        "mechanism_phenotype": phenotype,
        "mechanism_phenotype_sha256": stable_sha256(phenotype),
        "environment": environment,
        "environment_sha256": stable_sha256(environment),
    }


def _move_rows(frontier: Mapping[str, Any]) -> list[dict[str, Any]]:
    if frontier.get("schema") != RESULT_SCHEMA:
        raise ValueError("strategy move learning requires compiled company frontiers")
    company = dict(frontier.get("company") or {})
    entity_id = require_text(company.get("id"), "strategy move entity_id")
    frontier_sha = require_text(
        frontier.get("strategy_frontier_sha256"), "strategy frontier sha256",
    )
    lineage_fields = STRATEGY_MOVE_CANDIDATE_LINEAGE_FIELDS
    lineage = (
        {key: str(company[key]) for key in lineage_fields}
        if all(company.get(key) for key in lineage_fields) else {}
    )
    if lineage:
        frontier_body = dict(frontier)
        if frontier_body.pop("strategy_frontier_sha256", "") != stable_sha256(frontier_body):
            raise ValueError("candidate-bound strategy frontier content hash mismatch")
    frontier_programs = frontier.get("frontier_programs") or ()
    local_programs = frontier.get("local_peak_programs") or ()
    rows = []
    for option in frontier.get("option_catalog") or ():
        option_id = require_text(option.get("option_id"), "strategy option_id")
        option_sha = require_text(option.get("option_sha256"), "strategy option sha256")
        frontier_program_ids = sorted(
            str(row["program_id"]) for row in frontier_programs
            if option_id in set(row.get("unique_option_ids") or ())
        )
        local_peak_program_ids = sorted(
            str(row["program_id"]) for row in local_programs
            if option_id in set(row.get("unique_option_ids") or ())
        )
        evidence_epoch = canonical_timestamp(
            frontier.get("evidence_epoch"), "strategy move evidence_epoch",
        )
        identity = {
            "entity_id": entity_id,
            "evidence_epoch": evidence_epoch,
            "strategy_frontier_sha256": frontier_sha,
            "option_sha256": option_sha,
            **lineage,
        }
        comparison = strategy_option_comparison_identity(frontier, option)
        environment = comparison["environment"]
        implementation_event = (
            dict(option["implementation_event"])
            if isinstance(option.get("implementation_event"), Mapping) else None
        )
        mechanism = option.get("mechanism")
        if isinstance(mechanism, Mapping):
            mechanism = dict(mechanism)
            mechanism_status = "typed"
        else:
            mechanism = None
            mechanism_status = "requires_typed_mechanism"
        causal_panel_status = (
            "treatment_event_ready"
            if (implementation_event or {}).get("treatment_timing_status") == "exact_adoption_event"
            else "treatment_timing_interval_censored"
            if (implementation_event or {}).get("treatment_timing_status") == "interval_censored_adoption_event"
            else "requires_adoption_event"
        )
        outcome_contracts = []
        for contract in option.get("outcome_contracts") or ():
            measurement_start_at = str(contract.get("measurement_start_at") or evidence_epoch)
            due_at = timestamp_key(measurement_start_at) + timedelta(
                days=int(contract["horizon_days"])
            )
            outcome_contracts.append({
                **dict(contract),
                "measurement_start_at": measurement_start_at,
                "due_at": due_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
            })
        direction_hypotheses = [{
            "contract_sha256": contract.get("contract_sha256"),
            "objective_coordinate": contract.get("objective_coordinate"),
            "objective_coordinate_status": contract.get(
                "objective_coordinate_status", "unbound_legacy",
            ),
            "ordinal_scenario_direction_hypothesis": list(
                contract.get("ordinal_scenario_direction_hypothesis") or ()
            ),
            "ordinal_direction_summary": contract.get("ordinal_direction_summary"),
        } for contract in outcome_contracts]
        body = {
            "schema": "jaggedthoughts-strategy-move-v1",
            "move_id": f"{entity_id}:{option_id}:{evidence_epoch}",
            **identity,
            "option_id": option_id,
            "kind": str(option.get("kind") or "unclassified"),
            "description": str(option.get("description") or ""),
            "claim_status": str(option.get("claim_status") or "unresolved"),
            "mechanism": mechanism,
            "mechanism_status": mechanism_status,
            "strategy_choice_identity": comparison["strategy_choice_identity"],
            "strategy_choice_identity_sha256": comparison[
                "strategy_choice_identity_sha256"
            ],
            "mechanism_signature": comparison["mechanism_signature"],
            "mechanism_signature_sha256": comparison["mechanism_signature_sha256"],
            "mechanism_phenotype": comparison["mechanism_phenotype"],
            "mechanism_phenotype_sha256": comparison["mechanism_phenotype_sha256"],
            "implementation_event": implementation_event,
            "causal_panel_status": causal_panel_status,
            "environment": environment,
            "environment_sha256": comparison["environment_sha256"],
            "frontier_bundle_count": len(frontier_program_ids),
            "local_peak_bundle_count": len(local_peak_program_ids),
            "strategy_program_attribution": {
                "strategy_frontier_sha256": frontier_sha,
                "frontier_program_ids": frontier_program_ids,
                "local_peak_program_ids": local_peak_program_ids,
                "scope_closed": bool(frontier.get("scope_closed")),
                "decision_closed": bool(frontier.get("decision_closed")),
                "status": "option_event_does_not_establish_integrated_program",
                "program_adoption_evidence_required": True,
                "recursive_frontier_credit_eligible": False,
            },
            "outcome_contracts": outcome_contracts,
            "scenario_direction_hypotheses": direction_hypotheses,
            "evidence_refs": list(option.get("evidence_refs") or ()),
        }
        # Phenotypes are derived comparison projections. Adding or revising one
        # must not mint a new identity for the underlying sourced company move.
        move_identity = {
            key: value for key, value in body.items()
            if key not in {
                "mechanism_phenotype", "mechanism_phenotype_sha256",
                "strategy_program_attribution",
                "scenario_direction_hypotheses",
            }
        }
        rows.append({**body, "move_sha256": stable_sha256(move_identity)})
    return rows


def _outcome_episode(
    raw: Mapping[str, Any], moves: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if raw.get("schema") != STRATEGY_MOVE_OUTCOME_SCHEMA:
        raise ValueError("unsupported strategy move outcome schema")
    move_sha = require_text(raw.get("move_sha256"), "strategy outcome move_sha256")
    move = moves.get(move_sha)
    if move is None:
        raise ValueError("strategy outcome does not bind an exact compiled move")
    contract_sha = require_text(raw.get("contract_sha256"), "strategy outcome contract_sha256")
    contract = next(
        (row for row in move["outcome_contracts"] if row.get("contract_sha256") == contract_sha),
        None,
    )
    if contract is None:
        raise ValueError("strategy outcome does not bind a declared move outcome contract")
    observed_at = canonical_timestamp(raw.get("observed_at"), "strategy outcome observed_at")
    available_at = canonical_timestamp(raw.get("available_at"), "strategy outcome available_at")
    if timestamp_key(observed_at) < timestamp_key(str(contract["due_at"])):
        raise ValueError("strategy outcome cannot settle before its frozen horizon")
    if timestamp_key(available_at) < timestamp_key(observed_at):
        raise ValueError("strategy outcome cannot be available before it is observed")
    unit = require_text(raw.get("unit"), "strategy outcome unit")
    if unit != contract["unit"]:
        raise ValueError("strategy outcome unit differs from its frozen contract")
    baseline = require_finite(raw.get("baseline_value"), "strategy outcome baseline_value")
    outcome = require_finite(raw.get("outcome_value"), "strategy outcome outcome_value")
    effect = outcome - baseline
    comparator_effect = None
    if contract["comparator"] != "pre_move_baseline":
        comparator_effect = (
            require_finite(raw.get("comparator_outcome_value"), "strategy comparator outcome")
            - require_finite(raw.get("comparator_baseline_value"), "strategy comparator baseline")
        )
        effect -= comparator_effect
    signed_effect = effect if contract["direction"] == "increase" else -effect
    minimum = abs(float(contract["minimum_effect"]))
    status = "supports" if signed_effect >= minimum else "contradicts" if signed_effect <= -minimum else "inconclusive"
    source_refs = list(require_refs(
        raw.get("source_refs") or (), "strategy outcome source_ref",
    ))
    hypothesis = next(
        row for row in move.get("scenario_direction_hypotheses") or ()
        if row.get("contract_sha256") == contract_sha
    )
    direction_is_bound = (
        hypothesis.get("objective_coordinate_status") == "bound"
        and hypothesis.get("ordinal_direction_summary") in {"increase", "decrease"}
        and hypothesis.get("ordinal_direction_summary") == contract["direction"]
    )
    calibration_status = (
        "inconclusive" if not direction_is_bound
        else "supports_direction" if status == "supports"
        else "challenges_direction" if status == "contradicts"
        else "inconclusive"
    )
    calibration_reason = (
        "unbound_legacy"
        if hypothesis.get("objective_coordinate_status") != "bound"
        else "non_invariant_direction_without_realized_scenario"
        if hypothesis.get("ordinal_direction_summary") not in {"increase", "decrease"}
        else "ordinal_direction_differs_from_contract_direction"
        if hypothesis.get("ordinal_direction_summary") != contract["direction"]
        else "observed_effect_supports_frozen_direction"
        if calibration_status == "supports_direction"
        else "observed_effect_challenges_frozen_direction"
        if calibration_status == "challenges_direction"
        else "observed_effect_inside_inconclusive_band"
    )
    calibration_body = {
        "schema": STRATEGY_SCENARIO_CALIBRATION_SCHEMA,
        "strategy_frontier_sha256": move["strategy_frontier_sha256"],
        "move_sha256": move_sha,
        "option_sha256": move["option_sha256"],
        "contract_sha256": contract_sha,
        **dict(hypothesis),
        "metric_effect": {
            "metric_id": contract["metric_id"], "unit": unit, "value": effect,
            "observed_direction": (
                "increase" if effect > 0 else "decrease" if effect < 0 else "flat"
            ),
        },
        "contract_direction": contract["direction"],
        "contract_settlement_status": status,
        "status": calibration_status,
        "reason": calibration_reason,
        "realized_scenario_id": None,
        "classification_basis": "frozen_contract_direction_and_minimum_effect",
        "ordinal_magnitude_conversion_performed": False,
        "observed_at": observed_at,
        "available_at": available_at,
        "source_refs": source_refs,
        "capital_authority": False,
    }
    calibration = {
        **calibration_body,
        "calibration_sha256": stable_sha256(calibration_body),
    }
    point_in_time_evidence = None
    if raw.get("point_in_time_evidence") is not None:
        evidence = dict(raw["point_in_time_evidence"])
        source_run_sha = require_text(
            evidence.get("source_run_sha256"), "strategy outcome source run hash",
        )
        snapshot_sha = require_text(
            evidence.get("snapshot_sha256"), "strategy outcome snapshot hash",
        )
        if any(
            len(value) != 64 or any(character not in "0123456789abcdef" for character in value.lower())
            for value in (source_run_sha, snapshot_sha)
        ):
            raise ValueError("strategy outcome point-in-time evidence requires SHA-256 identities")
        point_in_time_evidence = {
            "source_run_sha256": source_run_sha,
            "snapshot_sha256": snapshot_sha,
            "baseline_observation_ids": list(require_refs(
                evidence.get("baseline_observation_ids") or (),
                "strategy outcome baseline observation",
            )),
            "outcome_observation_ids": list(require_refs(
                evidence.get("outcome_observation_ids") or (),
                "strategy outcome observation",
            )),
        }
    body = {
        "schema": "jaggedthoughts-strategy-move-outcome-episode-v1",
        "move_sha256": move_sha,
        "contract_sha256": contract_sha,
        "entity_id": move["entity_id"],
        "move_kind": move["kind"],
        "metric_id": contract["metric_id"],
        "unit": unit,
        "observed_at": observed_at,
        "available_at": available_at,
        "baseline_value": baseline,
        "outcome_value": outcome,
        "comparator_kind": contract["comparator"],
        "comparator_effect": comparator_effect,
        "estimated_effect": effect,
        "status": status,
        "causal_status": (
            "descriptive_before_after" if contract["comparator"] == "pre_move_baseline"
            else "comparator_adjusted_not_yet_parallel_trend_ratified"
        ),
        "point_in_time_evidence": point_in_time_evidence,
        "source_refs": source_refs,
        "scenario_calibration_receipt": calibration,
    }
    return {**body, "episode_sha256": stable_sha256(body)}


def _scenario_calibration_rollup(
    receipts: Iterable[Mapping[str, Any]], bindings: Iterable[Mapping[str, Any]],
) -> tuple[str, str]:
    bindings = tuple(bindings)
    statuses = {str(row.get("status")) for row in receipts}
    bound = any(row.get("objective_coordinate_status") == "bound" for row in bindings)
    has_bindings = any(True for _ in bindings)
    if "challenges_direction" in statuses:
        return "challenges_direction", "review_challenged_direction_in_successor_frontier"
    if "supports_direction" in statuses:
        return "supports_direction", "carry_supported_direction_into_successor_frontier"
    if statuses:
        reasons = {str(row.get("reason")) for row in receipts}
        if "unbound_legacy" in reasons:
            return "inconclusive", "bind_objective_coordinate_in_successor_frontier"
        if reasons & {
            "non_invariant_direction_without_realized_scenario",
            "ordinal_direction_differs_from_contract_direction",
        }:
            return (
                "inconclusive",
                "bind_realized_scenario_or_restate_direction_in_successor_frontier",
            )
        return "inconclusive", "settle_additional_bound_operating_outcome"
    if bound:
        return "awaiting_settlement", "settle_bound_operating_outcome"
    if has_bindings:
        return "unbound_legacy", "bind_objective_coordinate_in_successor_frontier"
    return "no_contract", "author_source_bound_outcome_contract"


def _set_overlap(left: set[str], right: set[str]) -> dict[str, Any]:
    union = left | right
    return {
        "intersection_count": len(left & right),
        "union_count": len(union),
        "jaccard": len(left & right) / len(union) if union else 1.0,
        "added": sorted(right - left),
        "removed": sorted(left - right),
    }


def _frontier_constraint_rows(frontier: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalize the authored feasibility language for adjacent-epoch comparison."""
    constraints = frontier.get("feasibility_constraints") or {}
    rows = []
    typed_pairs: set[tuple[str, str]] = set()
    for raw in constraints.get("incompatibilities") or ():
        option_ids = tuple(sorted(map(str, raw.get("option_ids") or ())))
        if len(option_ids) != 2:
            continue
        typed_pairs.add(option_ids)
        rows.append({
            "predicate_kind": "incompatibility",
            "constraint_id": str(raw.get("constraint_id") or ":".join(option_ids)),
            "operands": {"option_ids": list(option_ids)},
            "evidence_refs": sorted(map(str, raw.get("evidence_refs") or ())),
            "authority": str(raw.get("authority") or "dossier_bound"),
        })
    for raw in constraints.get("prerequisites") or ():
        option_id = str(raw.get("option_id") or "")
        required = sorted(map(str, raw.get("requires") or ()))
        if not option_id or not required:
            continue
        rows.append({
            "predicate_kind": "prerequisite",
            "constraint_id": str(raw.get("constraint_id") or f"prerequisite:{option_id}"),
            "operands": {"option_id": option_id, "requires": required},
            "evidence_refs": sorted(map(str, raw.get("evidence_refs") or ())),
            "authority": str(raw.get("authority") or "legacy_profile"),
        })
    for raw in constraints.get("resources") or ():
        resource_id = str(raw.get("resource_id") or "")
        uses = raw.get("uses") or {}
        if not resource_id or not isinstance(uses, Mapping):
            continue
        rows.append({
            "predicate_kind": "resource_limit",
            "constraint_id": str(raw.get("constraint_id") or f"resource:{resource_id}"),
            "operands": {
                "resource_id": resource_id, "unit": str(raw.get("unit") or ""),
                "limit": raw.get("limit"),
                "uses": dict(sorted((str(key), value) for key, value in uses.items())),
            },
            "evidence_refs": sorted(map(str, raw.get("evidence_refs") or ())),
            "authority": str(raw.get("authority") or "legacy_profile"),
        })
    certificate = frontier.get("choice_space_certificate") or {}
    for pair in certificate.get("incompatible_option_pairs") or ():
        option_ids = tuple(sorted(map(str, pair)))
        if len(option_ids) != 2 or option_ids in typed_pairs:
            continue
        rows.append({
            "predicate_kind": "incompatibility",
            "constraint_id": f"legacy-incompatibility:{':'.join(option_ids)}",
            "operands": {"option_ids": list(option_ids)},
            "evidence_refs": [], "authority": "legacy_profile",
        })
    rows.append({
        "predicate_kind": "cardinality_limit",
        "constraint_id": "max_bundle_size",
        "operands": {"maximum": certificate.get("max_bundle_size")},
        "evidence_refs": [], "authority": "compiler_configuration",
    })
    return sorted(({
        **row, "predicate_sha256": stable_sha256(row),
    } for row in rows), key=lambda row: (
        row["predicate_kind"], row["constraint_id"], row["predicate_sha256"],
    ))


def _frontier_evolution(
    frontiers: Iterable[Mapping[str, Any]], moves: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Compare adjacent authored strategy representations without scoring outcomes."""
    by_entity: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    moves_by_frontier: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for frontier in frontiers:
        by_entity[str((frontier.get("company") or {}).get("id") or "")].append(frontier)
    for move in moves:
        moves_by_frontier[str(move["strategy_frontier_sha256"])].append(move)
    rows = []
    for entity_id, versions in sorted(by_entity.items()):
        ordered = sorted(
            versions,
            key=lambda row: (
                timestamp_key(str(row["evidence_epoch"])),
                str(row["strategy_frontier_sha256"]),
            ),
        )
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            earlier_moves = moves_by_frontier[str(earlier["strategy_frontier_sha256"])]
            later_moves = moves_by_frontier[str(later["strategy_frontier_sha256"])]
            earlier_moves_by_option = {
                str(row["option_id"]): row for row in earlier_moves
            }
            later_moves_by_option = {
                str(row["option_id"]): row for row in later_moves
            }
            earlier_options = {
                str(row["option_id"]): str(row["option_sha256"])
                for row in earlier.get("option_catalog") or ()
            }
            later_options = {
                str(row["option_id"]): str(row["option_sha256"])
                for row in later.get("option_catalog") or ()
            }
            shared_options = set(earlier_options) & set(later_options)
            choice_continuity = [
                {
                    "option_id": option_id,
                    "earlier_strategy_choice_identity_sha256": earlier_moves_by_option[
                        option_id
                    ]["strategy_choice_identity_sha256"],
                    "later_strategy_choice_identity_sha256": later_moves_by_option[
                        option_id
                    ]["strategy_choice_identity_sha256"],
                    "status": (
                        "preserved"
                        if earlier_moves_by_option[option_id][
                            "strategy_choice_identity_sha256"
                        ] == later_moves_by_option[option_id][
                            "strategy_choice_identity_sha256"
                        ]
                        else "semantic_change"
                    ),
                }
                for option_id in sorted(shared_options)
            ]
            earlier_predicates = {
                (row["predicate_kind"], row["constraint_id"]): row
                for row in _frontier_constraint_rows(earlier)
            }
            later_predicates = {
                (row["predicate_kind"], row["constraint_id"]): row
                for row in _frontier_constraint_rows(later)
            }
            shared_predicates = set(earlier_predicates) & set(later_predicates)
            revised_predicates = [{
                "predicate_kind": key[0], "constraint_id": key[1],
                "earlier_predicate_sha256": earlier_predicates[key]["predicate_sha256"],
                "later_predicate_sha256": later_predicates[key]["predicate_sha256"],
            } for key in sorted(shared_predicates) if (
                earlier_predicates[key]["predicate_sha256"]
                != later_predicates[key]["predicate_sha256"]
            )]
            earlier_bundles = {
                "|".join(sorted(map(str, row.get("option_ids") or ())))
                for row in (earlier.get("choice_space_certificate") or {}).get(
                    "feasible_bundles", ()
                )
            }
            later_bundles = {
                "|".join(sorted(map(str, row.get("option_ids") or ())))
                for row in (later.get("choice_space_certificate") or {}).get(
                    "feasible_bundles", ()
                )
            }
            constraint_evolution = {
                "added": [later_predicates[key] for key in sorted(
                    set(later_predicates) - set(earlier_predicates)
                )],
                "removed": [earlier_predicates[key] for key in sorted(
                    set(earlier_predicates) - set(later_predicates)
                )],
                "revised": revised_predicates,
                "preserved_count": sum(
                    earlier_predicates[key]["predicate_sha256"]
                    == later_predicates[key]["predicate_sha256"]
                    for key in shared_predicates
                ),
                "newly_admitted_bundles": sorted(later_bundles - earlier_bundles),
                "newly_excluded_bundles": sorted(earlier_bundles - later_bundles),
                "empirical_counterexample_bound": False,
                "use_boundary": (
                    "This records a source-representation revision. Bundle changes are not "
                    "attributed to one predicate when options or other premises also changed."
                ),
            }
            body = {
                "entity_id": entity_id,
                "earlier_evidence_epoch": earlier["evidence_epoch"],
                "later_evidence_epoch": later["evidence_epoch"],
                "earlier_strategy_frontier_sha256": earlier["strategy_frontier_sha256"],
                "later_strategy_frontier_sha256": later["strategy_frontier_sha256"],
                "option_ids": _set_overlap(set(earlier_options), set(later_options)),
                "unchanged_option_body_count": sum(
                    earlier_options[option_id] == later_options[option_id]
                    for option_id in shared_options
                ),
                "strategy_choice_continuity": choice_continuity,
                "preserved_strategy_choice_count": sum(
                    row["status"] == "preserved" for row in choice_continuity
                ),
                "mechanism_families": _set_overlap(
                    {str(row["mechanism_signature_sha256"]) for row in earlier_moves},
                    {str(row["mechanism_signature_sha256"]) for row in later_moves},
                ),
                "mechanism_phenotypes": _set_overlap(
                    {str(row["mechanism_phenotype_sha256"]) for row in earlier_moves},
                    {str(row["mechanism_phenotype_sha256"]) for row in later_moves},
                ),
                "frontier_option_bundles": _set_overlap(
                    {"|".join(sorted(str(value) for value in row.get("unique_option_ids") or ())) for row in earlier.get("frontier_programs") or ()},
                    {"|".join(sorted(str(value) for value in row.get("unique_option_ids") or ())) for row in later.get("frontier_programs") or ()},
                ),
                "constraint_evolution": constraint_evolution,
                "use_boundary": (
                    "This compares authored representations across evidence epochs. "
                    "Persistence does not establish operating success, causality, or investment return."
                ),
            }
            rows.append({**body, "evolution_sha256": stable_sha256(body)})
    return sorted(rows, key=lambda row: (
        timestamp_key(str(row["later_evidence_epoch"])), row["entity_id"],
        row["evolution_sha256"],
    ))


def compile_strategy_move_library(
    frontiers: Iterable[Mapping[str, Any]], outcomes: Iterable[Mapping[str, Any]] = (),
    *, event_refinement_requests: Iterable[Mapping[str, Any]] = (),
    event_refinement_results: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Compile exact move identities, outcome episodes, and bounded transfer questions."""

    latest: dict[tuple[str, str], Mapping[str, Any]] = {}

    def compiler_rank(frontier: Mapping[str, Any]) -> tuple[int, int, int, int, int, str]:
        company = frontier.get("company") or {}
        certificate = frontier.get("choice_space_certificate") or {}
        neighborhood = frontier.get("neighborhood") or {}
        return (
            int(all(company.get(key) for key in STRATEGY_MOVE_CANDIDATE_LINEAGE_FIELDS)),
            int(frontier.get("compiler_contract_version") or 0),
            len(certificate.get("predicate_catalog") or ()),
            len(neighborhood.get("edges") or ()),
            sum(
                len(row.get("outcome_contracts") or ())
                for row in frontier.get("option_catalog") or ()
            ),
            str(frontier.get("strategy_frontier_sha256") or ""),
        )

    for frontier in frontiers:
        identity = (
            str((frontier.get("company") or {}).get("id") or ""),
            canonical_timestamp(
                frontier.get("evidence_epoch"), "strategy frontier evidence_epoch",
            ),
        )
        rank = compiler_rank(frontier)
        prior = latest.get(identity)
        prior_rank = compiler_rank(prior or {})
        if prior is None or rank > prior_rank:
            latest[identity] = frontier
    moves = [row for frontier in latest.values() for row in _move_rows(frontier)]
    move_by_sha = {row["move_sha256"]: row for row in moves}
    if len(move_by_sha) != len(moves):
        raise ValueError("strategy move identities must be unique")
    episode_by_sha = {}
    for raw in outcomes:
        episode = _outcome_episode(raw, move_by_sha)
        episode_by_sha.setdefault(episode["episode_sha256"], episode)
    episodes = list(episode_by_sha.values())
    episodes_by_move: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        episodes_by_move[episode["move_sha256"]].append(episode)
    for move in moves:
        move["outcome_episodes"] = sorted(
            episodes_by_move.get(move["move_sha256"], ()), key=lambda row: row["available_at"],
        )
        move["learning_status"] = (
            "outcome_observed" if move["outcome_episodes"] else
            "awaiting_outcome_window" if move["outcome_contracts"] else
            "requires_measurable_outcome_contract"
        )
        statuses = {row["status"] for row in move["outcome_episodes"]}
        move["evidence_grade"] = (
            "challenged_by_outcome" if "contradicts" in statuses else
            "comparator_adjusted_outcome_support"
            if any(
                row["status"] == "supports" and row["comparator_kind"] != "pre_move_baseline"
                for row in move["outcome_episodes"]
            ) else
            "descriptive_outcome_support" if "supports" in statuses else
            "inconclusive_outcome" if move["outcome_episodes"] else
            "implementation_observed" if move["implementation_event"] else
            "option_only"
        )
        calibration_receipts = [
            row["scenario_calibration_receipt"] for row in move["outcome_episodes"]
        ]
        calibration_status, calibration_transition = _scenario_calibration_rollup(
            calibration_receipts, move["scenario_direction_hypotheses"],
        )
        move["scenario_calibration_receipts"] = calibration_receipts
        move["scenario_calibration_status"] = calibration_status
        move["scenario_calibration_next_transition"] = calibration_transition
    timing_refinement_count = apply_strategy_event_refinements(
        moves, requests=event_refinement_requests, results=event_refinement_results,
    )

    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    phenotypes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for move in moves:
        families[move["mechanism_signature_sha256"]].append(move)
        phenotypes[move["mechanism_phenotype_sha256"]].append(move)
    frontier_evolution = _frontier_evolution(latest.values(), moves)
    moves_by_frontier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for move in moves:
        moves_by_frontier[str(move["strategy_frontier_sha256"])].append(move)
    frontier_calibrations = []
    for frontier_sha, frontier_moves in sorted(moves_by_frontier.items()):
        receipts = [
            receipt for move in frontier_moves
            for receipt in move["scenario_calibration_receipts"]
        ]
        bindings = [
            binding for move in frontier_moves
            for binding in move["scenario_direction_hypotheses"]
        ]
        status, transition = _scenario_calibration_rollup(receipts, bindings)
        calibration_body = {
            "strategy_frontier_sha256": frontier_sha,
            "move_sha256s": sorted(move["move_sha256"] for move in frontier_moves),
            "calibration_receipt_sha256s": sorted(
                receipt["calibration_sha256"] for receipt in receipts
            ),
            "status": status,
            "next_transition": transition,
            "immutable_frontier": True,
            "capital_authority": False,
        }
        frontier_calibrations.append({
            **calibration_body,
            "frontier_calibration_sha256": stable_sha256(calibration_body),
        })
    family_rows = []
    for mechanism_sha, members in sorted(families.items()):
        member_episodes = [episode for move in members for episode in move["outcome_episodes"]]
        entity_ids = sorted({row["entity_id"] for row in members})
        environment_ids = sorted({row["environment_sha256"] for row in members})
        status_counts = {
            status: sum(row["status"] == status for row in member_episodes)
            for status in ("supports", "contradicts", "inconclusive")
        }
        family_body = {
            "family_id": f"mechanism:{mechanism_sha[:16]}",
            "mechanism_signature_sha256": mechanism_sha,
            "mechanism_signature": members[0]["mechanism_signature"],
            "entity_ids": entity_ids,
            "environment_sha256s": environment_ids,
            "environment_count": len(environment_ids),
            "move_sha256s": sorted(row["move_sha256"] for row in members),
            "outcome_episode_count": len(member_episodes),
            "outcome_status_counts": status_counts,
            "evidence_grade": (
                "challenged_by_outcome" if status_counts["contradicts"] else
                "cross_environment_outcome_support"
                if status_counts["supports"] and len(environment_ids) > 1 else
                "single_environment_outcome_support" if status_counts["supports"] else
                "implementation_observed"
                if any(row["implementation_event"] for row in members) else
                "transfer_question_only"
            ),
            "transport_status": (
                "cross_environment_transfer_question" if len(environment_ids) > 1
                else "within_environment_replication_question" if len(entity_ids) > 1
                else "single_entity_hypothesis"
            ),
            "transfer_requirements": {
                "target_language_restatement": True,
                "target_variables_identified": all(bool(row["outcome_contracts"]) for row in members),
                "explicit_break_case": all(bool((row.get("mechanism") or {}).get("break_conditions")) for row in members),
                "target_falsification_check": all(bool(row["outcome_contracts"]) for row in members),
                "source_bound_implementation_events": all(bool(row["implementation_event"]) for row in members),
                "exact_adoption_timing": all(
                    row["causal_panel_status"] == "treatment_event_ready" for row in members
                ),
                "minimum_distinct_entities": 2,
                "minimum_distinct_environments": 2,
                "requires_causal_design": True,
            },
            "promotion_eligible": False,
        }
        family_rows.append({**family_body, "family_sha256": stable_sha256(family_body)})
    phenotype_rows = []
    for phenotype_sha, members in sorted(phenotypes.items()):
        phenotype_episodes = [
            episode for move in members for episode in move["outcome_episodes"]
        ]
        phenotype_body = {
            "phenotype_id": f"strategy-phenotype:{phenotype_sha[:16]}",
            "mechanism_phenotype_sha256": phenotype_sha,
            "mechanism_phenotype": members[0]["mechanism_phenotype"],
            "mechanism_signature_sha256": members[0]["mechanism_signature_sha256"],
            "entity_ids": sorted({row["entity_id"] for row in members}),
            "move_sha256s": sorted(row["move_sha256"] for row in members),
            "exact_adoption_count": sum(
                row["causal_panel_status"] == "treatment_event_ready" for row in members
            ),
            "outcome_episode_count": len(phenotype_episodes),
            "comparison_status": (
                "outcomes_available" if phenotype_episodes else
                "peer_classification_ready" if any(
                    row["causal_panel_status"] == "treatment_event_ready" for row in members
                ) else "requires_exact_adoption_event"
            ),
            "promotion_eligible": False,
        }
        phenotype_rows.append({
            **phenotype_body,
            "phenotype_sha256": stable_sha256(phenotype_body),
        })
    unsettled_due_dates = sorted(
        contract["due_at"]
        for move in moves for contract in move["outcome_contracts"]
        if not any(
            row["contract_sha256"] == contract["contract_sha256"]
            for row in move["outcome_episodes"]
        )
    )
    body = {
        "schema": STRATEGY_MOVE_LIBRARY_SCHEMA,
        "move_count": len(moves),
        "move_family_count": len(family_rows),
        "mechanism_phenotype_count": len(phenotype_rows),
        "frontier_evolution_pair_count": len(frontier_evolution),
        "measurable_move_count": sum(bool(row["outcome_contracts"]) for row in moves),
        "implementation_observed_move_count": sum(bool(row["implementation_event"]) for row in moves),
        "treatment_event_ready_move_count": sum(
            row["causal_panel_status"] == "treatment_event_ready" for row in moves
        ),
        "interval_censored_treatment_move_count": sum(
            row["causal_panel_status"] == "treatment_timing_interval_censored" for row in moves
        ),
        "timing_refinement_count": timing_refinement_count,
        "outcome_episode_count": len(episodes),
        "scenario_calibration_receipt_count": sum(
            len(row["scenario_calibration_receipts"]) for row in moves
        ),
        "moves": sorted(moves, key=lambda row: (row["entity_id"], row["option_id"])),
        "frontier_calibrations": frontier_calibrations,
        "move_families": family_rows,
        "mechanism_phenotypes": phenotype_rows,
        "frontier_evolution": frontier_evolution,
        "evidence_ladder": [
            "option_only", "implementation_observed", "descriptive_outcome_support",
            "comparator_adjusted_outcome_support", "causal_transport_support",
        ],
        "next_outcome_due_at": unsettled_due_dates[0] if unsettled_due_dates else None,
        "next_activation": (
            f"Acquire and settle the next source-bound business outcome at or after {unsettled_due_dates[0]}."
            if unsettled_due_dates else
            "Calibrate at least one strategy option to a measurable business outcome and comparator."
        ),
        "causal_panel_activation": (
            "Assemble compatible treated and control histories for exact source-bound adoption events."
            if any(row["causal_panel_status"] == "treatment_event_ready" for row in moves)
            else "Acquire a source-bound strategy adoption event before constructing a causal panel."
        ),
        "learning_boundary": (
            "Move families are transport questions. Business outcomes evaluate the operating move; "
            "security returns evaluate the investment. Repeated before-after observations remain "
            "descriptive until the existing causal-learning lane ratifies an estimator and its assumptions."
        ),
        "authority": "research_memory_only",
        "capital_authority": False,
    }
    return {**body, "library_sha256": stable_sha256(body)}


def compile_workspace_strategy_move_library(
    root: str | Path, *, extra_outcomes: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    workspace = Path(root).expanduser().resolve()
    frontiers = []
    for path in sorted((workspace / "strategy_frontiers" / "results").glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(row, Mapping) and row.get("option_catalog"):
            frontiers.append(row)
    outcomes = []
    for path in sorted((workspace / "institutional_learning" / "strategy_outcomes").glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(row, Mapping):
            outcomes.append(row)
    outcomes.extend(dict(row) for row in extra_outcomes)
    refinement_requests = []
    for path in sorted((
        workspace / "research_jobs" / "strategy_event_refinements" / "requests"
    ).glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(row, Mapping):
            refinement_requests.append(row)
    refinement_results = []
    for path in sorted((
        workspace / "institutional_learning" / "strategy_event_refinements" / "results"
    ).glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(row, Mapping):
            refinement_results.append(row)
    return compile_strategy_move_library(
        frontiers, outcomes,
        event_refinement_requests=refinement_requests,
        event_refinement_results=refinement_results,
    )


def due_strategy_outcome_requests(
    library: Mapping[str, Any], *, as_of: str,
) -> list[dict[str, Any]]:
    """Return stable agent requests for every matured, unsettled contract."""
    if library.get("schema") != STRATEGY_MOVE_LIBRARY_SCHEMA:
        raise ValueError("strategy outcome scheduling requires a compiled move library")
    now = canonical_timestamp(as_of, "strategy outcome schedule as_of")
    requests = []
    for move in library.get("moves") or ():
        settled = {
            str(row["contract_sha256"]) for row in move.get("outcome_episodes") or ()
        }
        for contract in move.get("outcome_contracts") or ():
            if (
                str(contract["contract_sha256"]) in settled
                or timestamp_key(str(contract["due_at"])) > timestamp_key(now)
            ):
                continue
            body = {
                "schema": STRATEGY_OUTCOME_REQUEST_SCHEMA,
                "request_id": (
                    f"strategy-outcome:{move['move_sha256'][:16]}:"
                    f"{contract['contract_sha256'][:16]}"
                ),
                "entity_id": move["entity_id"],
                "move_sha256": move["move_sha256"],
                "contract_sha256": contract["contract_sha256"],
                "move_description": move["description"],
                "mechanism": move.get("mechanism"),
                "implementation_event": move.get("implementation_event"),
                "metric_id": contract["metric_id"],
                "unit": contract["unit"],
                "direction": contract["direction"],
                "minimum_effect": contract["minimum_effect"],
                "comparator": contract["comparator"],
                "measurement_start_at": contract["measurement_start_at"],
                "due_at": contract["due_at"],
                "outcome_role": contract.get("outcome_role", "terminal_operating"),
                "acquisition_mode": contract.get(
                    "acquisition_mode", "subscription_primary_document",
                ),
                "evidence_refs": list(contract["evidence_refs"]),
                "required_capability": (
                    "point_in_time_public_source_refresh"
                    if contract.get("acquisition_mode") == "point_in_time_observation"
                    else "subscription_web_research"
                ),
                "expected_exit": "validated_strategy_outcome_or_typed_failure",
                "capital_authority": False,
            }
            for key in ("metric_locator", "measurement_source_catalog"):
                if contract.get(key):
                    body[key] = contract[key]
            requests.append({**body, "request_sha256": stable_sha256(body)})
    return sorted(requests, key=lambda row: (row["due_at"], row["request_id"]))


def due_strategy_program_adoption_requests(
    library: Mapping[str, Any], frontiers: Iterable[Mapping[str, Any]], *, as_of: str,
    results: Iterable[Mapping[str, Any]] = (),
    prior_requests: Iterable[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Freeze same-frontier program-adoption questions without promoting option events."""
    if library.get("schema") != STRATEGY_MOVE_LIBRARY_SCHEMA:
        raise ValueError("strategy program scheduling requires a compiled move library")
    search_end = canonical_timestamp(as_of, "strategy program schedule as_of")
    valid_prior = [dict(row) for row in prior_requests if isinstance(row, Mapping)
        and row.get("schema") == STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA
        and row.get("request_sha256") == stable_sha256({
            key: value for key, value in row.items() if key != "request_sha256"
        })
    ]

    def candidate_set_sha(row: Mapping[str, Any]) -> str:
        return str(row.get("candidate_program_set_sha256") or stable_sha256(
            row.get("candidate_programs") or (),
        ))

    prior_by_identity = {
        (str(row.get("strategy_frontier_sha256")), candidate_set_sha(row)): row
        for row in valid_prior
    }
    prior_by_sha = {str(row["request_sha256"]): row for row in valid_prior}
    settled_identities = {
        (str(request.get("strategy_frontier_sha256")), candidate_set_sha(request))
        for row in results if isinstance(row, Mapping)
        and row.get("schema") == STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA
        and row.get("result_sha256") == stable_sha256({
            key: value for key, value in row.items() if key != "result_sha256"
        })
        and (request := prior_by_sha.get(str(row.get("request_sha256") or ""))) is not None
    }
    moves = {
        (str(row.get("strategy_frontier_sha256")), str(row.get("option_id"))): row
        for row in library.get("moves") or () if isinstance(row, Mapping)
    }
    requests = []
    for frontier in frontiers:
        if frontier.get("schema") != RESULT_SCHEMA:
            continue
        frontier_sha = str(frontier.get("strategy_frontier_sha256") or "")
        company = dict(frontier.get("company") or {})
        entity_id = str(company.get("id") or "").upper()
        lineage = [
            str(company.get(field) or "") for field in (
                "candidate_leaf", "candidate_sha256", "source_dossier_sha256",
            )
        ]
        if any(len(value) != 64 for value in lineage):
            continue
        exact = {
            option_id: move for (sha, option_id), move in moves.items()
            if sha == frontier_sha
            and move.get("causal_panel_status") == "treatment_event_ready"
            and isinstance(move.get("implementation_event"), Mapping)
            and move["implementation_event"].get("source_refs")
        }
        if len(exact) < 2:
            continue
        catalog = {
            str(option.get("option_id")): option
            for option in frontier.get("option_catalog") or ()
            if isinstance(option, Mapping)
        }
        programs: dict[str, dict[str, Any]] = {}
        for role, rows in (
            ("global_frontier", frontier.get("frontier_programs") or ()),
            ("local_peak", frontier.get("local_peak_programs") or ()),
        ):
            for raw in rows:
                if not isinstance(raw, Mapping):
                    continue
                option_ids = sorted({str(value) for value in raw.get("unique_option_ids") or ()})
                if len(set(option_ids) & set(exact)) < 2:
                    continue
                program_id = require_text(raw.get("program_id"), "strategy program id")
                row = programs.setdefault(program_id, {
                    "program_id": program_id,
                    "expression": require_text(raw.get("expression"), "strategy program expression"),
                    "roles": [],
                    "options": [],
                    "excluded_option_ids": [],
                    "source_refs": sorted({str(value) for value in raw.get("evidence_refs") or ()}),
                })
                row["roles"].append(role)
                if not row["options"]:
                    row["options"] = [{
                        "option_id": option_id,
                        "option_sha256": str((catalog.get(option_id) or {}).get("option_sha256") or ""),
                        "move_sha256": str((moves.get((frontier_sha, option_id)) or {}).get("move_sha256") or ""),
                        "observed_exact_implementation_event_sha256": str(
                            ((exact.get(option_id) or {}).get("implementation_event") or {}).get(
                                "implementation_event_sha256"
                            ) or ""
                        ) or None,
                    } for option_id in option_ids]
        for edge in (frontier.get("neighborhood") or {}).get("edges") or ():
            if not isinstance(edge, Mapping) or not (
                edge.get("target_is_frontier") or edge.get("target_is_local_peak")
            ):
                continue
            option_ids = sorted({str(value) for value in edge.get("base_option_ids") or ()})
            if len(set(option_ids) & set(exact)) < 2:
                continue
            program_id = require_text(edge.get("base_program_id"), "one-choice base program id")
            row = programs.setdefault(program_id, {
                "program_id": program_id,
                "expression": require_text(
                    edge.get("base_expression"), "one-choice base expression",
                ),
                "roles": [],
                "options": [],
                "excluded_option_ids": [],
                "source_refs": sorted({
                    str(ref) for option_id in option_ids
                    for ref in (catalog.get(option_id) or {}).get("evidence_refs") or ()
                }),
            })
            row["roles"].append("one_choice_base")
            if edge.get("added_option_id"):
                row["excluded_option_ids"].append(str(edge["added_option_id"]))
            if not row["options"]:
                row["options"] = [{
                    "option_id": option_id,
                    "option_sha256": str((catalog.get(option_id) or {}).get("option_sha256") or ""),
                    "move_sha256": str((moves.get((frontier_sha, option_id)) or {}).get("move_sha256") or ""),
                    "observed_exact_implementation_event_sha256": str(
                        ((exact.get(option_id) or {}).get("implementation_event") or {}).get(
                            "implementation_event_sha256"
                        ) or ""
                    ) or None,
                } for option_id in option_ids]
        if len(programs) < 2:
            continue
        candidate_programs = sorted(programs.values(), key=lambda row: row["program_id"])
        option_sets = [
            {str(option["option_id"]) for option in row["options"]}
            for row in candidate_programs
        ]
        common_option_ids = set.intersection(*option_sets) if option_sets else set()
        for row in candidate_programs:
            row["roles"] = sorted(set(row["roles"]))
            row["excluded_option_ids"] = sorted(set(row["excluded_option_ids"]))
            row["discriminating_option_ids"] = sorted(
                {str(option["option_id"]) for option in row["options"]} - common_option_ids
            )
        candidate_program_set_sha256 = stable_sha256(candidate_programs)
        request_identity = (frontier_sha, candidate_program_set_sha256)
        if request_identity in settled_identities:
            continue
        body = {
            "schema": STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA,
            "request_id": f"strategy-program-adoption:{frontier_sha[:24]}",
            "entity_id": entity_id,
            "candidate_leaf": str(company.get("candidate_leaf") or ""),
            "candidate_sha256": str(company.get("candidate_sha256") or ""),
            "source_dossier_sha256": str(company.get("source_dossier_sha256") or ""),
            "strategy_frontier_sha256": frontier_sha,
            "evidence_epoch": canonical_timestamp(
                frontier.get("evidence_epoch"), "strategy program evidence_epoch",
            ),
            "search_end_at": search_end,
            "observed_exact_option_event_sha256s": sorted({
                str(move["implementation_event"]["implementation_event_sha256"])
                for move in exact.values()
            }),
            "candidate_programs": candidate_programs,
            "candidate_program_set_sha256": candidate_program_set_sha256,
            "common_option_ids": sorted(common_option_ids),
            "classification_set": [
                "exact_integrated_program_adoption", "partial_option_adoption",
                "multiple_integrated_programs_observed", "no_integrated_program_adoption_found",
                "insufficient_source_coverage",
            ],
            "adoption_rule": (
                "Exact program adoption requires source-bound operational or completed events for "
                "every constituent option plus a primary source that links them as one coordinated program."
            ),
            "joint_source_support_rule": (
                "One joint source must support coordinated_program and option:<option_id> for every "
                "constituent of each selected program."
            ),
            "option_events_are_anchors_not_program_adoption": True,
            "required_source_classes": ["sec_filings", "issuer_investor_materials"],
            "required_capability": "subscription_web_research",
            "expected_exit": "source_bound_integrated_program_classification_or_source_gap",
            "program_outcome_credit": False,
            "portfolio_weight": 0.0,
            "capital_authority": False,
        }
        requests.append(prior_by_identity.get(
            request_identity, {**body, "request_sha256": stable_sha256(body)},
        ))
    return sorted(requests, key=lambda row: (row["evidence_epoch"], row["request_id"]))


def compile_strategy_program_adoption_result(
    raw: Mapping[str, Any], request: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one source-backed answer to an immutable integrated-program question."""
    if request.get("schema") != STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA:
        raise ValueError("strategy program result requires a program-adoption request")
    request_sha = require_text(request.get("request_sha256"), "strategy program request hash")
    if request_sha != stable_sha256({
        key: value for key, value in request.items() if key != "request_sha256"
    }):
        raise ValueError("strategy program request content hash mismatch")
    if raw.get("schema") != STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA:
        raise ValueError("unsupported strategy program adoption result schema")
    if raw.get("request_sha256") != request_sha or raw.get("entity_id") != request["entity_id"]:
        raise ValueError("strategy program result crossed its request identity")
    classification = require_text(raw.get("classification"), "strategy program classification")
    if classification not in set(request["classification_set"]):
        raise ValueError("unsupported strategy program classification")
    program_by_id = {
        str(row["program_id"]): row for row in request.get("candidate_programs") or ()
    }
    selected = sorted({require_text(value, "selected strategy program") for value in raw.get("selected_program_ids") or ()})
    if not set(selected).issubset(program_by_id):
        raise ValueError("strategy program result selected an unbound program")
    sources = []
    for raw_source in raw.get("sources") or ():
        source = dict(raw_source) if isinstance(raw_source, Mapping) else {}
        url = require_text(source.get("url"), "strategy program source URL")
        if not url.startswith("https://"):
            raise ValueError("strategy program sources must be HTTPS primary documents")
        kind = require_text(source.get("source_kind"), "strategy program source kind")
        if kind not in {"filing", "issuer"}:
            raise ValueError("strategy program sources must be filings or issuer documents")
        published_at = canonical_timestamp(
            source.get("published_at"), "strategy program source published_at",
        )
        if timestamp_key(published_at) > timestamp_key(str(request["search_end_at"])):
            raise ValueError("strategy program source was unavailable at the frozen search end")
        supports = sorted({
            require_text(value, "strategy program source support")
            for value in source.get("supports") or ()
        })
        if not supports:
            raise ValueError("strategy program sources require a supported claim")
        sources.append({
            "url": url, "source_kind": kind,
            "published_at": published_at, "supports": supports,
        })
    if not sources:
        raise ValueError("strategy program result requires opened primary sources")
    source_urls = {row["url"] for row in sources}
    option_events = []
    for raw_event in raw.get("option_events") or ():
        event = dict(raw_event) if isinstance(raw_event, Mapping) else {}
        option_id = require_text(event.get("option_id"), "strategy program option id")
        refs = sorted({require_text(value, "strategy program event source") for value in event.get("source_urls") or ()})
        if not refs or not set(refs).issubset(source_urls):
            raise ValueError("strategy program option events must bind opened primary sources")
        occurred_at = canonical_timestamp(event.get("occurred_at"), "strategy program event occurred_at")
        available_at = canonical_timestamp(event.get("available_at"), "strategy program event available_at")
        if timestamp_key(available_at) < timestamp_key(occurred_at):
            raise ValueError("strategy program event cannot be available before occurrence")
        if timestamp_key(available_at) > timestamp_key(str(request["search_end_at"])):
            raise ValueError("strategy program event was unavailable at the frozen search end")
        state = require_text(event.get("implementation_state"), "strategy program implementation state")
        if state not in {"operational", "completed"}:
            raise ValueError("program adoption requires operational or completed option events")
        event_body = {
            "option_id": option_id, "occurred_at": occurred_at,
            "available_at": available_at, "implementation_state": state,
            "source_urls": refs,
        }
        option_events.append({**event_body, "event_sha256": stable_sha256(event_body)})
    if len({row["option_id"] for row in option_events}) != len(option_events):
        raise ValueError("strategy program result repeats an option event")
    joint_refs = sorted({
        require_text(value, "strategy program joint-execution source")
        for value in raw.get("joint_execution_source_urls") or ()
    })
    if not set(joint_refs).issubset(source_urls):
        raise ValueError("joint program evidence must bind opened primary sources")
    event_ids = {row["option_id"] for row in option_events}
    request_option_ids = {
        str(option["option_id"])
        for program in program_by_id.values() for option in program["options"]
    }
    if not event_ids.issubset(request_option_ids):
        raise ValueError("strategy program result introduced an unbound option event")
    exact_class = classification == "exact_integrated_program_adoption"
    source_by_url = {row["url"]: row for row in sources}
    coverage = dict(raw.get("coverage") or {})
    full_coverage = bool(
        coverage.get("sec_filings_searched") and coverage.get("issuer_materials_searched")
    )

    def program_discriminators(program_id: str) -> set[str]:
        declared = program_by_id[program_id].get("discriminating_option_ids")
        if declared is not None:
            return set(map(str, declared))
        option_sets = [
            {str(option["option_id"]) for option in row.get("options") or ()}
            for row in program_by_id.values()
        ]
        common = set.intersection(*option_sets) if option_sets else set()
        return {
            str(option["option_id"])
            for option in program_by_id[program_id].get("options") or ()
        } - common

    def joint_source_links(program_id: str) -> bool:
        required = {
            "coordinated_program",
            *(f"option:{row['option_id']}" for row in program_by_id[program_id]["options"]),
        }
        excluded = {
            f"option:{option_id}"
            for option_id in program_by_id[program_id].get("excluded_option_ids") or ()
        }
        return any(
            required.issubset(set(source_by_url[url]["supports"]))
            and not excluded.intersection(source_by_url[url]["supports"])
            for url in joint_refs
        )

    def program_is_discriminated(program_id: str) -> bool:
        positive = program_discriminators(program_id)
        negative = set(map(str, program_by_id[program_id].get("excluded_option_ids") or ()))
        return bool(positive or negative)

    def excluded_events_absent(program_id: str) -> bool:
        excluded = set(map(str, program_by_id[program_id].get("excluded_option_ids") or ()))
        return not excluded.intersection(event_ids)

    if exact_class:
        if len(selected) != 1 or not joint_refs:
            raise ValueError("exact integrated-program adoption requires one program and joint evidence")
        if not program_is_discriminated(selected[0]):
            raise ValueError("exact program cannot be distinguished from its nested rivals")
        if program_by_id[selected[0]].get("excluded_option_ids") and not full_coverage:
            raise ValueError("one-choice base classification requires both primary-source classes")
        if not excluded_events_absent(selected[0]):
            raise ValueError("one-choice base classification observed an excluded added option")
        if not joint_source_links(selected[0]):
            raise ValueError("joint source does not bind every selected-program constituent")
        required_ids = {str(row["option_id"]) for row in program_by_id[selected[0]]["options"]}
        if event_ids != required_ids:
            raise ValueError("exact integrated-program adoption requires every constituent option event")
    elif classification == "multiple_integrated_programs_observed":
        if len(selected) < 2 or not joint_refs:
            raise ValueError("multiple-program classification requires multiple bound programs and joint evidence")
        if any(not program_is_discriminated(program_id) for program_id in selected):
            raise ValueError("selected programs cannot be distinguished from nested rivals")
        if any(not excluded_events_absent(program_id) for program_id in selected):
            raise ValueError("multiple-program classification crosses a negative discriminator")
        if any(not joint_source_links(program_id) for program_id in selected):
            raise ValueError("joint sources do not bind every selected-program constituent")
        required_ids = {
            str(option["option_id"])
            for program_id in selected for option in program_by_id[program_id]["options"]
        }
        if event_ids != required_ids:
            raise ValueError("multiple-program classification requires every selected-program constituent")
    elif selected:
        raise ValueError("non-program classifications cannot select an integrated program")
    if classification == "no_integrated_program_adoption_found" and not full_coverage:
        raise ValueError("negative program search requires both primary-source classes")
    assessed_at = canonical_timestamp(raw.get("assessed_at"), "strategy program assessed_at")
    if timestamp_key(assessed_at) < timestamp_key(str(request["evidence_epoch"])):
        raise ValueError("strategy program assessment precedes the frozen frontier")
    evidence_available_at = max(
        [timestamp_key(row["published_at"]) for row in sources]
        + [timestamp_key(row["available_at"]) for row in option_events]
    )
    if timestamp_key(assessed_at) < evidence_available_at:
        raise ValueError("strategy program assessment precedes its classification evidence")
    if timestamp_key(assessed_at) > timestamp_key(str(request["search_end_at"])):
        raise ValueError("strategy program assessment exceeds the frozen search end")
    body = {
        "schema": STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA,
        "request_sha256": request_sha, "entity_id": request["entity_id"],
        "strategy_frontier_sha256": request["strategy_frontier_sha256"],
        "candidate_program_set_sha256": request.get(
            "candidate_program_set_sha256", stable_sha256(request.get("candidate_programs") or ()),
        ),
        "classification": classification, "selected_program_ids": selected,
        "assessed_at": assessed_at,
        "coverage": {
            "sec_filings_searched": bool(coverage.get("sec_filings_searched")),
            "issuer_materials_searched": bool(coverage.get("issuer_materials_searched")),
            "search_end_at": request["search_end_at"],
        },
        "option_events": sorted(option_events, key=lambda row: row["option_id"]),
        "joint_execution_source_urls": joint_refs,
        "sources": sorted(sources, key=lambda row: row["url"]),
        "rationale": require_text(raw.get("rationale"), "strategy program rationale"),
        "residuals": [
            require_text(value, "strategy program residual") for value in raw.get("residuals") or ()
        ],
        "program_adoption_evidence_eligible": exact_class,
        "recursive_program_outcome_credit_eligible": False,
        "next_activation": (
            "Freeze a source-calibrated program-level operating outcome contract."
            if exact_class else "Acquire evidence that discriminates the remaining program candidates."
        ),
        "classification_authority": "subscription_agent_proposal",
        "portfolio_weight": 0.0, "capital_authority": False,
    }
    return {**body, "result_sha256": stable_sha256(body)}


def compile_strategy_program_outcome_plan(
    result: Mapping[str, Any], request: Mapping[str, Any], library: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze prospective readouts already shared by a confirmed program's moves."""
    verified = compile_strategy_program_adoption_result(result, request)
    if verified.get("result_sha256") != result.get("result_sha256"):
        raise ValueError("strategy program result content hash mismatch")
    if library.get("schema") != STRATEGY_MOVE_LIBRARY_SCHEMA:
        raise ValueError("strategy program outcome planning requires a move library")

    selected = list(verified.get("selected_program_ids") or ())
    program_by_id = {
        str(row["program_id"]): row for row in request.get("candidate_programs") or ()
    }
    if not verified.get("program_adoption_evidence_eligible"):
        body = {
            "schema": STRATEGY_PROGRAM_OUTCOME_PLAN_SCHEMA,
            "request_sha256": request["request_sha256"],
            "result_sha256": verified["result_sha256"],
            "entity_id": request["entity_id"],
            "status": "awaiting_exact_integrated_program",
            "program_id": None, "constituent_option_count": 0,
            "readout_count": 0, "readouts": [],
            "next_activation": verified["next_activation"],
            "causal_program_credit_eligible": False,
            "portfolio_weight": 0.0, "capital_authority": False,
        }
        return {**body, "plan_sha256": stable_sha256(body)}
    if len(selected) != 1:
        raise ValueError("program outcome planning requires one exact integrated program")

    program = program_by_id[selected[0]]
    program_sets = [
        {str(option["option_id"]) for option in row.get("options") or ()}
        for row in program_by_id.values()
    ]
    common_option_ids = set.intersection(*program_sets) if program_sets else set()
    discriminating_option_ids = set(map(
        str, program.get("discriminating_option_ids") or (
            {str(option["option_id"]) for option in program.get("options") or ()}
            - common_option_ids
        ),
    ))
    excluded_option_ids = set(map(str, program.get("excluded_option_ids") or ()))
    negative_discriminator = bool(
        excluded_option_ids and "one_choice_base" in set(program.get("roles") or ())
    )
    moves_by_sha = {
        str(row.get("move_sha256")): row for row in library.get("moves") or ()
        if isinstance(row, Mapping) and row.get("move_sha256")
    }
    signatures: dict[tuple[Any, ...], dict[str, Any]] = {}
    constituent_ids = {str(row["option_id"]) for row in program.get("options") or ()}
    constituent_moves = []
    for option in program.get("options") or ():
        move = moves_by_sha.get(str(option.get("move_sha256") or ""))
        if not move or str(move.get("option_id")) != str(option["option_id"]):
            continue
        constituent_moves.append(move)
        for contract in move.get("outcome_contracts") or ():
            if contract.get("comparator") != "pre_move_baseline":
                continue
            signature = (
                str(contract["metric_id"]), str(contract["unit"]),
                str(contract["direction"]), float(contract["minimum_effect"]),
                int(contract["horizon_days"]), str(contract["comparator"]),
                str(contract.get("outcome_role") or "terminal_operating"),
                str(contract.get("acquisition_mode") or "subscription_primary_document"),
                stable_sha256({
                    "metric_locator": contract.get("metric_locator"),
                    "measurement_source_catalog": contract.get("measurement_source_catalog"),
                }),
            )
            row = signatures.setdefault(signature, {
                "supporting_option_ids": [], "basis_contract_sha256s": [],
            })
            row["supporting_option_ids"].append(str(option["option_id"]))
            row["basis_contract_sha256s"].append(str(contract["contract_sha256"]))

    readouts = []
    for signature, support in sorted(signatures.items()):
        option_ids = sorted(set(support["supporting_option_ids"]))
        if len(option_ids) < 2 or (
            not set(option_ids) & discriminating_option_ids and not negative_discriminator
        ):
            continue
        (
            metric_id, unit, direction, minimum_effect, horizon_days, comparator,
            outcome_role, acquisition_mode, source_definition_sha256,
        ) = signature
        due_at = timestamp_key(str(verified["assessed_at"])) + timedelta(days=horizon_days)
        readout = {
            "result_sha256": verified["result_sha256"],
            "entity_id": request["entity_id"], "program_id": selected[0],
            "metric_id": metric_id, "unit": unit, "direction": direction,
            "minimum_effect": minimum_effect, "horizon_days": horizon_days,
            "comparator": comparator,
            "outcome_role": outcome_role, "acquisition_mode": acquisition_mode,
            "source_definition_sha256": source_definition_sha256,
            "measurement_start_at": verified["assessed_at"],
            "due_at": due_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "supporting_option_ids": option_ids,
            "basis_contract_sha256s": sorted(set(support["basis_contract_sha256s"])),
            "constituent_coverage_count": len(option_ids),
            "constituent_option_count": len(constituent_ids),
            "discriminating_option_ids": sorted(discriminating_option_ids),
            "discriminating_absence_option_ids": sorted(excluded_option_ids),
            "selection_rule": (
                "exact contract signature shared by at least two base-program constituent moves; "
                "the one-choice contrast is the source-classified absence of the added option"
                if negative_discriminator else
                "exact contract signature shared by at least two constituent moves, "
                "including a program-discriminating option"
            ),
        }
        readouts.append({**readout, "readout_sha256": stable_sha256(readout)})
    phenotype_shas = sorted(
        str(row.get("mechanism_phenotype_sha256") or "") for row in constituent_moves
        if row.get("mechanism_phenotype_sha256")
    )
    program_phenotype = {
        "composition_operator": "combine",
        "constituent_mechanism_phenotype_sha256s": phenotype_shas,
        "constituent_count": len(constituent_ids),
    }
    body = {
        "schema": STRATEGY_PROGRAM_OUTCOME_PLAN_SCHEMA,
        "request_sha256": request["request_sha256"],
        "result_sha256": verified["result_sha256"],
        "entity_id": request["entity_id"], "status": (
            "prospective_readouts_frozen" if readouts else
            "missing_program_discriminating_outcome_contract"
        ),
        "program_id": selected[0], "program_expression": program["expression"],
        "program_roles": sorted(set(map(str, program.get("roles") or ()))),
        "program_phenotype": program_phenotype,
        "program_phenotype_sha256": (
            stable_sha256(program_phenotype)
            if len(phenotype_shas) == len(constituent_ids) else None
        ),
        "environment_boundaries": sorted({
            str((row.get("environment") or {}).get("industry_boundary") or "unclassified")
            for row in constituent_moves
        }),
        "constituent_option_count": len(constituent_ids),
        "discriminating_option_ids": sorted(discriminating_option_ids),
        "discriminating_absence_option_ids": sorted(excluded_option_ids),
        "readout_count": len(readouts), "readouts": readouts,
        "next_activation": (
            f"Acquire the frozen operating readouts at or after {min(row['due_at'] for row in readouts)}."
            if readouts else
            "Add a measurable contract shared by a distinguishing option and another constituent."
        ),
        "interpretation_boundary": (
            "A readout measures company performance after the classified program; it does not isolate "
            "the program's causal effect or imply a security return."
        ),
        "causal_program_credit_eligible": False,
        "portfolio_weight": 0.0, "capital_authority": False,
    }
    return {**body, "plan_sha256": stable_sha256(body)}


def compile_strategy_cohort_research_plan(
    library: Mapping[str, Any], market_catalog: Mapping[str, Any], *,
    max_peers_per_family: int = 8, target_control_unit_count: int = 4,
    max_transfer_environments: int = 2, transfer_peers_per_environment: int = 2,
    prior_plan: Mapping[str, Any] | None = None,
    search_end_by_query_sha256: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Select comparable public peers that need strategy-event classification.

    The plan deliberately does not infer that a peer is untreated from a missing
    local event.  It creates a source-search request whose negative result remains
    a provisional not-yet-treated classification.
    """
    if library.get("schema") != STRATEGY_MOVE_LIBRARY_SCHEMA:
        raise ValueError("strategy cohort planning requires a compiled move library")
    if max_peers_per_family < 1:
        raise ValueError("strategy cohort planning requires at least one peer")
    if target_control_unit_count < 1:
        raise ValueError("strategy cohort planning requires at least one target control")
    if max_transfer_environments < 0 or transfer_peers_per_environment < 1:
        raise ValueError("strategy transfer search bounds are invalid")
    if prior_plan and prior_plan.get("schema") != STRATEGY_COHORT_PLAN_SCHEMA:
        raise ValueError("prior strategy cohort plan has an unsupported schema")
    prior_ends = {
        strategy_cohort_query_identity(row)["query_sha256"]: str(row["search_end_at"])
        for row in (prior_plan or {}).get("requests") or ()
        if isinstance(row, Mapping)
    }
    activated_ends = {
        str(key): canonical_timestamp(value, "strategy cohort activated search end")
        for key, value in (search_end_by_query_sha256 or {}).items()
    }
    securities = [
        dict(row) for row in market_catalog.get("securities") or ()
        if isinstance(row, Mapping)
        and row.get("entity_kind") == "public_equity"
        and row.get("security_kind") == "common_equity"
        and row.get("symbol") and row.get("industry")
    ]
    by_symbol = {str(row["symbol"]).upper(): row for row in securities}
    exact_moves = []
    for row in library.get("moves") or ():
        if (
            row.get("causal_panel_status") != "treatment_event_ready"
            or not isinstance(row.get("mechanism"), Mapping)
        ):
            continue
        event = effective_exact_implementation_event(row)
        if event is not None:
            exact_moves.append({**dict(row), "implementation_event": event})
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for move in exact_moves:
        focal = by_symbol.get(str(move["entity_id"]).upper())
        if focal:
            grouped[(str(move["mechanism_phenotype_sha256"]), str(focal["industry"]))].append(move)
    requests = []
    mechanism_environments = []
    transfer_environment_searches = []
    law_blind_environment_probes = []
    for (phenotype_sha, industry), moves in sorted(grouped.items()):
        mechanism_sha = str(moves[0]["mechanism_signature_sha256"])
        focal_ids = {str(row["entity_id"]).upper() for row in moves}
        focal_caps = [
            float(by_symbol[row]["market_cap"])
            for row in focal_ids
            if isinstance(by_symbol.get(row, {}).get("market_cap"), (int, float))
            and float(by_symbol[row]["market_cap"]) > 0
        ]
        anchor = math.exp(sum(math.log(value) for value in focal_caps) / len(focal_caps)) if focal_caps else None

        def peer_rank(row: Mapping[str, Any]) -> tuple[float, str]:
            cap = row.get("market_cap")
            distance = (
                abs(math.log(float(cap) / anchor))
                if anchor and isinstance(cap, (int, float)) and float(cap) > 0 else math.inf
            )
            return distance, str(row["symbol"])

        peers = sorted(
            (row for row in securities if str(row["industry"]) == industry and str(row["symbol"]).upper() not in focal_ids),
            key=peer_rank,
        )[:max_peers_per_family]
        focal_events = sorted(({
            "move_sha256": row["move_sha256"],
            "entity_id": row["entity_id"],
            "option_id": row["option_id"],
            "strategy_form": row["kind"],
            "description": row["description"],
            "mechanism": row["mechanism"],
            "environment": row["environment"],
            "implementation_event": row["implementation_event"],
        } for row in moves), key=lambda row: row["move_sha256"])
        mechanism_environments.append({
            "mechanism_signature_sha256": mechanism_sha,
            "mechanism_signature": moves[0]["mechanism_signature"],
            "mechanism_phenotype_sha256": phenotype_sha,
            "mechanism_phenotype": moves[0]["mechanism_phenotype"],
            "industry_id": industry,
            "focal_moves": focal_events,
            "peer_entity_ids": [str(row["symbol"]).upper() for row in peers],
        })
        created_at = max(
            [str(market_catalog.get("retrieved_at") or "")] +
            [str(row["implementation_event"]["available_at"]) for row in moves]
        )
        created_at = canonical_timestamp(created_at, "strategy cohort request created_at")
        first_event = min(
            timestamp_key(str(row["implementation_event"]["occurred_at"])) for row in moves
        )
        search_start = (first_event - timedelta(days=365 * 5)).isoformat(timespec="seconds").replace("+00:00", "Z")
        def append_request(
            peer: Mapping[str, Any], *, target_industry: str,
            search_role: str, anchor_move_sha256s: Iterable[str] = (),
            request_created_at: str = created_at,
            selection_receipt: Mapping[str, Any] | None = None,
        ) -> None:
            body = {
                "schema": STRATEGY_COHORT_REQUEST_SCHEMA,
                "request_id": (
                    f"strategy-cohort:{phenotype_sha[:16]}:blind:{str(peer['symbol']).lower()}"
                    if search_role == "law_blind_environment_probe" else
                    f"strategy-cohort:{phenotype_sha[:16]}:{str(peer['symbol']).lower()}"
                ),
                "created_at": request_created_at,
                "law_id": "reinforcing-strategy-choice-durability",
                "mechanism_signature_sha256": mechanism_sha,
                "mechanism_signature": moves[0]["mechanism_signature"],
                "mechanism_phenotype_sha256": phenotype_sha,
                "mechanism_phenotype": moves[0]["mechanism_phenotype"],
                "industry_id": target_industry,
                "focal_moves": focal_events,
                "peer_entity_id": str(peer["symbol"]).upper(),
                "peer_name": str(peer.get("name") or peer["symbol"]),
                "peer_security_id": str(peer["security_id"]),
                "search_start_at": search_start,
                "search_end_at": created_at,
                "required_source_classes": ["sec_filings", "issuer_investor_materials"],
                "required_capability": "subscription_web_research",
                "expected_exit": "typed_equivalent_adoption_classification_or_source_gap",
                "control_use_boundary": (
                    "A family-only event is excluded from the focal phenotype panel but cannot be a control. "
                    "No family event found under declared coverage means provisional not-yet-treated, never "
                    "proof that the company was never treated."
                ),
                "capital_authority": False,
            }
            if search_role != "within_environment_control_discovery":
                body.update({
                    "search_role": search_role,
                    "source_industry_id": industry,
                    "selection_boundary": (
                        "Frozen catalog, comparable market-cap band, and stable hash only; "
                        "no non-focal law, adoption, outcome, or support status entered selection."
                        if search_role == "law_blind_environment_probe" else
                        "Same action and economic bridge in a source-bound strategy move; "
                        "outcomes and later classifications were not used for selection."
                    ),
                })
                if anchor_move_sha256s:
                    body["transfer_anchor_move_sha256s"] = sorted(
                        set(anchor_move_sha256s)
                    )
                if selection_receipt:
                    body["law_blind_selection_receipt"] = dict(selection_receipt)
            query_sha = strategy_cohort_query_identity(body)["query_sha256"]
            search_end = prior_ends.get(query_sha, request_created_at)
            if query_sha in activated_ends:
                search_end = max(search_end, activated_ends[query_sha], key=timestamp_key)
            body["created_at"] = body["search_end_at"] = search_end
            body["query_sha256"] = query_sha
            requests.append({**body, "request_sha256": stable_sha256(body)})

        for peer in peers:
            append_request(
                peer, target_industry=industry,
                search_role="within_environment_control_discovery",
            )

        blind_frame = [
            row for row in securities
            if str(row["industry"]) != industry
            and str(row["symbol"]).upper() not in focal_ids
            and (
                not anchor
                or isinstance(row.get("market_cap"), (int, float))
                and float(row["market_cap"]) > 0
                and 0.25 <= float(row["market_cap"]) / anchor <= 4.0
            )
        ]
        blind_frame_ids = sorted(str(row["security_id"]) for row in blind_frame)
        blind_frame_sha256 = stable_sha256({
            "market_catalog_sha256": market_catalog.get("catalog_sha256"),
            "mechanism_phenotype_sha256": phenotype_sha,
            "source_industry_id": industry,
            "eligible_security_ids": blind_frame_ids,
        })
        blind_peer = min(
            blind_frame,
            key=lambda row: stable_sha256({
                "sampling_frame_sha256": blind_frame_sha256,
                "security_id": row["security_id"],
            }),
            default=None,
        )
        blind_industry = str((blind_peer or {}).get("industry") or "")
        if blind_peer:
            selection_receipt = {
                "schema": "jaggedthoughts-law-blind-environment-probe-v1",
                "sampling_frame_sha256": blind_frame_sha256,
                "eligible_security_count": len(blind_frame),
                "selected_security_id": blind_peer["security_id"],
                "selected_industry_id": blind_industry,
                "selection_inputs": [
                    "entity_kind", "source_availability", "market_cap_band",
                    "stable_hash",
                ],
                "excluded_inputs": [
                    "non_focal_strategy_laws", "adoption_classifications",
                    "outcomes", "support_status", "cohort_gap",
                ],
                "reserved_dispatch_share": 0.2,
                "capital_authority": False,
            }
            append_request(
                blind_peer, target_industry=blind_industry,
                search_role="law_blind_environment_probe",
                selection_receipt=selection_receipt,
            )
            law_blind_environment_probes.append({
                "mechanism_phenotype_sha256": phenotype_sha,
                "source_industry_id": industry,
                "target_industry_id": blind_industry,
                "peer_entity_id": str(blind_peer["symbol"]).upper(),
                **selection_receipt,
            })

        bridge_by_industry: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for move in library.get("moves") or ():
            if not isinstance(move, Mapping):
                continue
            entity = str(move.get("entity_id") or "").upper()
            security = by_symbol.get(entity)
            target_industry = str((security or {}).get("industry") or "")
            if (
                move.get("claim_status") != "supported"
                or str(move.get("mechanism_signature_sha256") or "") != mechanism_sha
                or entity in focal_ids or not target_industry or target_industry == industry
            ):
                continue
            bridge_by_industry[target_industry].append(dict(move))
        ranked_transfer = sorted(bridge_by_industry.items(), key=lambda item: (
            -len({str(row.get("entity_id") or "").upper() for row in item[1]}),
            -sum(bool(row.get("implementation_event")) for row in item[1]),
            -sum(
                int(row.get("frontier_bundle_count") or 0)
                + int(row.get("local_peak_bundle_count") or 0)
                for row in item[1]
            ),
            item[0],
        ))[:max_transfer_environments]
        for target_industry, anchors in ranked_transfer:
            anchor_ids = {str(row["entity_id"]).upper() for row in anchors}
            anchor_caps = [
                float(by_symbol[entity]["market_cap"])
                for entity in anchor_ids
                if isinstance(by_symbol.get(entity, {}).get("market_cap"), (int, float))
                and float(by_symbol[entity]["market_cap"]) > 0
            ]
            target_anchor = (
                math.exp(sum(math.log(value) for value in anchor_caps) / len(anchor_caps))
                if anchor_caps else None
            )

            def transfer_rank(peer: Mapping[str, Any]) -> tuple[int, float, str]:
                cap = peer.get("market_cap")
                distance = (
                    abs(math.log(float(cap) / target_anchor))
                    if target_anchor and isinstance(cap, (int, float)) and float(cap) > 0
                    else math.inf
                )
                return (
                    0 if str(peer["symbol"]).upper() in anchor_ids else 1,
                    distance, str(peer["symbol"]),
                )

            transfer_peers = sorted(
                (
                    row for row in securities
                    if str(row["industry"]) == target_industry
                    and str(row["symbol"]).upper()
                    != str((blind_peer or {}).get("symbol") or "").upper()
                ),
                key=transfer_rank,
            )[:transfer_peers_per_environment]
            anchor_shas = sorted(str(row["move_sha256"]) for row in anchors)
            transfer_created_at = canonical_timestamp(max(
                [created_at] + [str(row["evidence_epoch"]) for row in anchors],
                key=timestamp_key,
            ), "strategy transfer request created_at")
            transfer_environment_searches.append({
                "mechanism_signature_sha256": mechanism_sha,
                "mechanism_phenotype_sha256": phenotype_sha,
                "source_industry_id": industry,
                "target_industry_id": target_industry,
                "anchor_entity_ids": sorted(anchor_ids),
                "anchor_move_sha256s": anchor_shas,
                "peer_entity_ids": [str(row["symbol"]).upper() for row in transfer_peers],
                "selection_available_at": transfer_created_at,
                "selection_rule": (
                    "source-bound same-action-and-bridge anchors, then nearest market-cap peers; "
                    "stable identity tie-break"
                ),
            })
            for peer in transfer_peers:
                append_request(
                    peer, target_industry=target_industry,
                    search_role="cross_environment_transfer_discovery",
                    anchor_move_sha256s=anchor_shas,
                    request_created_at=transfer_created_at,
                )
    plan_body = {
        "schema": STRATEGY_COHORT_PLAN_SCHEMA,
        "library_sha256": library["library_sha256"],
        "market_catalog_sha256": market_catalog.get("catalog_sha256"),
        "exact_focal_move_count": len(exact_moves),
        "mechanism_environment_count": len(grouped),
        "max_peers_per_family": max_peers_per_family,
        "target_control_unit_count": target_control_unit_count,
        "adaptive_expansion_cap": 25,
        "mechanism_environments": mechanism_environments,
        "max_transfer_environments": max_transfer_environments,
        "transfer_peers_per_environment": transfer_peers_per_environment,
        "transfer_environment_search_count": len(transfer_environment_searches),
        "transfer_environment_searches": sorted(
            transfer_environment_searches,
            key=lambda row: (
                row["mechanism_phenotype_sha256"], row["target_industry_id"],
            ),
        ),
        "law_blind_environment_probe_count": len(law_blind_environment_probes),
        "law_blind_environment_probes": sorted(
            law_blind_environment_probes,
            key=lambda row: (
                row["mechanism_phenotype_sha256"], row["peer_entity_id"],
            ),
        ),
        "transfer_request_count": sum(
            row.get("search_role") == "cross_environment_transfer_discovery"
            for row in requests
        ),
        "request_count": len(requests),
        "requests": sorted(requests, key=lambda row: row["request_id"]),
        "next_activation": (
            "Separate exact-phenotype adoption, related-family treatment, provisional controls, and source gaps across selected within- and cross-environment peers."
            if requests else "Acquire an exact source-bound adoption event and comparable listed peers."
        ),
        "authority": "research_acquisition_only",
        "capital_authority": False,
    }
    return {**plan_body, "plan_sha256": stable_sha256(plan_body)}


def compile_strategy_cohort_research_result(
    raw: Mapping[str, Any], request: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate an agent's source-backed event classification against its request."""
    if request.get("schema") != STRATEGY_COHORT_REQUEST_SCHEMA:
        raise ValueError("strategy cohort result requires a cohort research request")
    request_sha = require_text(request.get("request_sha256"), "strategy cohort request hash")
    if stable_sha256({key: value for key, value in request.items() if key != "request_sha256"}) != request_sha:
        raise ValueError("strategy cohort request content hash mismatch")
    if raw.get("schema") != STRATEGY_COHORT_RESULT_SCHEMA:
        raise ValueError("unsupported strategy cohort research result schema")
    expected = {
        "request_sha256": request_sha,
        "peer_entity_id": request["peer_entity_id"],
        "mechanism_signature_sha256": request["mechanism_signature_sha256"],
        "mechanism_phenotype_sha256": request["mechanism_phenotype_sha256"],
    }
    if {key: raw.get(key) for key in expected} != expected:
        raise ValueError("strategy cohort result crossed its request identity")
    classification = require_text(raw.get("classification"), "strategy cohort classification")
    if classification not in {
        "phenotype_adoption_found", "family_adoption_only",
        "no_family_adoption_found", "insufficient_source_coverage",
    }:
        raise ValueError("unsupported strategy cohort classification")
    assessed_at = canonical_timestamp(raw.get("assessed_at"), "strategy cohort assessed_at")
    if timestamp_key(assessed_at) < timestamp_key(str(request["created_at"])):
        raise ValueError("strategy cohort assessment precedes its request")
    coverage = dict(raw.get("coverage") or {})
    if (
        coverage.get("search_start_at") != request["search_start_at"]
        or coverage.get("search_end_at") != request["search_end_at"]
    ):
        raise ValueError("strategy cohort result changed its search window")
    sources = []
    for source in raw.get("sources") or ():
        item = dict(source) if isinstance(source, Mapping) else {}
        url = require_text(item.get("url"), "strategy cohort source URL")
        if not url.startswith("https://"):
            raise ValueError("strategy cohort sources must be HTTPS documents")
        source_kind = require_text(item.get("source_kind"), "strategy cohort source kind")
        if source_kind not in {"filing", "issuer"}:
            raise ValueError("strategy cohort sources must be filings or issuer documents")
        raw_published_at = item.get("published_at")
        if isinstance(raw_published_at, str) and len(raw_published_at) == 10:
            raw_published_at = f"{raw_published_at}T00:00:00Z"
        published_at = canonical_timestamp(
            raw_published_at, "strategy cohort source published_at",
        )
        if timestamp_key(published_at) > timestamp_key(str(request["search_end_at"])):
            raise ValueError("strategy cohort source was unavailable at the frozen search end")
        sources.append({
            "url": url, "source_kind": source_kind,
            "published_at": published_at,
            "supports": sorted({require_text(value, "strategy cohort source support") for value in item.get("supports") or ()}),
        })
    if not sources:
        raise ValueError("strategy cohort result requires opened primary sources")
    source_urls = {row["url"] for row in sources}
    events = []
    for event in raw.get("events") or ():
        item = dict(event) if isinstance(event, Mapping) else {}
        occurred_at = canonical_timestamp(item.get("occurred_at"), "strategy cohort event occurred_at")
        available_at = canonical_timestamp(item.get("available_at"), "strategy cohort event available_at")
        if timestamp_key(available_at) < timestamp_key(occurred_at):
            raise ValueError("strategy cohort event cannot be available before occurrence")
        if timestamp_key(available_at) > timestamp_key(str(request["search_end_at"])):
            raise ValueError("strategy cohort event was unavailable at the frozen search end")
        refs = sorted({require_text(value, "strategy cohort event source URL") for value in item.get("source_urls") or ()})
        if not refs or not set(refs).issubset(source_urls):
            raise ValueError("strategy cohort event must bind opened primary sources")
        implementation_mode = require_text(
            item.get("implementation_mode"), "strategy cohort implementation_mode",
        )
        if implementation_mode not in IMPLEMENTATION_MODES - {"unspecified"}:
            raise ValueError("strategy cohort implementation_mode is unsupported")
        implementation_state = require_text(
            item.get("implementation_state"), "strategy cohort implementation_state",
        )
        if implementation_state not in STRATEGY_COHORT_IMPLEMENTATION_STATES:
            raise ValueError("strategy cohort implementation_state is unsupported")
        relation = dict(item.get("focal_relation") or {})
        relation_fields = (
            "strategy_form", "addressed_actor_profile", "implementation_mode",
            "operating_object_scope",
        )
        if set(relation) != set(relation_fields) or any(
            relation.get(field) not in STRATEGY_COHORT_RELATIONS for field in relation_fields
        ):
            raise ValueError("strategy cohort focal_relation is incomplete or unsupported")
        event_body = {
            "event_id": require_text(item.get("event_id"), "strategy cohort event id"),
            "description": require_text(item.get("description"), "strategy cohort event description"),
            "occurred_at": occurred_at, "available_at": available_at,
            "implementation_mode": implementation_mode,
            "implementation_state": implementation_state,
            "focal_relation": {field: relation[field] for field in relation_fields},
            "timing_precision": "date", "source_urls": refs,
        }
        events.append({**event_body, "event_sha256": stable_sha256(event_body)})
    if classification in {"phenotype_adoption_found", "family_adoption_only"} and not events:
        raise ValueError("strategy-adoption classification requires an exact event")
    if classification not in {"phenotype_adoption_found", "family_adoption_only"} and events:
        raise ValueError("non-adoption classifications cannot carry adoption events")
    exact_relation = {
        "strategy_form": "same", "addressed_actor_profile": "same",
        "implementation_mode": "same", "operating_object_scope": "same",
    }
    phenotype_events = [
        row for row in events
        if row["focal_relation"] == exact_relation
        and row["implementation_state"] in {"operational", "completed"}
    ]
    if classification == "phenotype_adoption_found" and not phenotype_events:
        raise ValueError("phenotype adoption requires an operational exact-phenotype event")
    if classification == "family_adoption_only" and phenotype_events:
        raise ValueError("an operational exact-phenotype event cannot be family-only")
    full_coverage = bool(coverage.get("sec_filings_searched") and coverage.get("issuer_materials_searched"))
    if classification == "no_family_adoption_found" and not full_coverage:
        raise ValueError("a negative event search requires both declared primary-source classes")
    body = {
        "schema": STRATEGY_COHORT_RESULT_SCHEMA,
        **expected,
        "classification": classification,
        "assessed_at": assessed_at,
        "coverage": {
            "sec_filings_searched": bool(coverage.get("sec_filings_searched")),
            "issuer_materials_searched": bool(coverage.get("issuer_materials_searched")),
            "search_start_at": request["search_start_at"],
            "search_end_at": request["search_end_at"],
        },
        "events": sorted(events, key=lambda row: (row["occurred_at"], row["event_id"])),
        "phenotype_event_sha256s": sorted(row["event_sha256"] for row in phenotype_events),
        "sources": sorted(sources, key=lambda row: row["url"]),
        "rationale": require_text(raw.get("rationale"), "strategy cohort rationale"),
        "residuals": [require_text(value, "strategy cohort residual") for value in raw.get("residuals") or ()],
        "panel_role": (
            "treated_candidate" if classification == "phenotype_adoption_found" else
            "related_treatment_excluded" if classification == "family_adoption_only" else
            "not_yet_treated_candidate" if classification == "no_family_adoption_found" else
            "excluded_source_gap"
        ),
        "classification_authority": "subscription_agent_proposal",
        "capital_authority": False,
    }
    return {**body, "result_sha256": stable_sha256(body)}


def resolve_strategy_cohort_results(
    plan: Mapping[str, Any], results: Iterable[Mapping[str, Any]], *,
    historical_requests: Iterable[Mapping[str, Any]] = (),
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Bind immutable result revisions to compatible current cohort questions."""
    current = {
        str(row["request_sha256"]): dict(row) for row in plan.get("requests") or ()
        if isinstance(row, Mapping) and row.get("request_sha256")
    }
    current_by_query: dict[str, tuple[str, dict[str, Any]]] = {}
    for request_sha, request in current.items():
        if stable_sha256({key: value for key, value in request.items() if key != "request_sha256"}) != request_sha:
            raise ValueError("strategy cohort request content hash mismatch")
        identity = strategy_cohort_query_identity(request)
        declared_query = str(request.get("query_sha256") or identity["query_sha256"])
        if declared_query != identity["query_sha256"]:
            raise ValueError("strategy cohort query identity hash mismatch")
        if declared_query in current_by_query:
            raise ValueError("strategy cohort plan repeats one semantic query")
        current_by_query[declared_query] = (request_sha, request)

    source_requests = dict(current)
    for row in historical_requests:
        if not isinstance(row, Mapping) or not row.get("request_sha256"):
            continue
        source_requests.setdefault(str(row["request_sha256"]), dict(row))

    candidates: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    rejected_identity = rejected_invalid = 0
    for raw in results:
        if raw.get("schema") != STRATEGY_COHORT_RESULT_SCHEMA:
            continue
        source_request = source_requests.get(str(raw.get("request_sha256") or ""))
        if source_request is None:
            rejected_invalid += 1
            continue
        try:
            result = compile_strategy_cohort_research_result(raw, source_request)
            query_sha = strategy_cohort_query_identity(source_request)["query_sha256"]
        except (TypeError, ValueError):
            rejected_invalid += 1
            continue
        match = current_by_query.get(query_sha)
        if match is None:
            rejected_identity += 1
            continue
        current_sha, current_request = match
        coverage = dict(result.get("coverage") or {})
        if (
            timestamp_key(str(coverage.get("search_end_at")))
            > timestamp_key(str(current_request["search_end_at"]))
        ):
            rejected_invalid += 1
            continue
        candidates[current_sha].append((result, source_request))

    resolved: dict[str, dict[str, Any]] = {}
    bindings = []
    exact_count = recovered_count = 0
    for current_sha, request in sorted(current.items()):
        values = candidates.get(current_sha) or ()
        if not values:
            continue
        ordered = sorted(values, key=lambda row: (
            timestamp_key(str((row[0].get("coverage") or {}).get("search_end_at"))),
            timestamp_key(str(row[0].get("assessed_at"))),
            str(row[0].get("result_sha256") or ""),
        ))
        result, source_request = ordered[-1]
        resolved[current_sha] = result
        exact = str(source_request["request_sha256"]) == current_sha
        exact_count += int(exact)
        recovered_count += int(not exact)
        covered_through = str(result["coverage"]["search_end_at"])
        current_through = str(request["search_end_at"])
        segment_start = str(request["search_start_at"])
        segments = []
        for segment_result, segment_request in ordered:
            segment_end = str(segment_result["coverage"]["search_end_at"])
            segments.append({
                "source_request_sha256": segment_request["request_sha256"],
                "source_result_sha256": segment_result["result_sha256"],
                "classification": segment_result["classification"],
                "search_start_at": segment_start,
                "search_end_at": segment_end,
            })
            segment_start = max(segment_start, segment_end, key=timestamp_key)
        bindings.append({
            "query_sha256": strategy_cohort_query_identity(request)["query_sha256"],
            "current_request_sha256": current_sha,
            "source_request_sha256": source_request["request_sha256"],
            "source_result_sha256": result["result_sha256"],
            "classification": result["classification"],
            "coverage_status": "exact_revision" if exact else "compatible_prefix",
            "covered_search_start_at": result["coverage"]["search_start_at"],
            "covered_through": covered_through,
            "coverage_segments": segments,
            "pending_delta": (
                None if covered_through == current_through else {
                    "after": covered_through,
                    "through": current_through,
                    "activation": "material_primary_source_change_only",
                }
            ),
        })
    body = {
        "schema": STRATEGY_COHORT_COVERAGE_CHAIN_SCHEMA,
        "plan_sha256": plan.get("plan_sha256"),
        "request_count": len(current),
        "bound_result_count": len(resolved),
        "exact_result_count": exact_count,
        "recovered_compatible_result_count": recovered_count,
        "pending_result_count": len(current) - len(resolved),
        "rejected_changed_identity_count": rejected_identity,
        "rejected_invalid_artifact_count": rejected_invalid,
        "bindings": bindings,
        "capital_authority": False,
    }
    return resolved, {**body, "coverage_chain_sha256": stable_sha256(body)}


def compile_strategy_phenotype_projection_frontier(
    plan: Mapping[str, Any], results: Iterable[Mapping[str, Any]],
    *, source_gap_request_sha256s: Iterable[str] = (),
    historical_requests: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Close the bounded grain tradeoff without selecting a causal phenotype."""
    if plan.get("schema") != STRATEGY_COHORT_PLAN_SCHEMA:
        raise ValueError("phenotype projection frontier requires a v2 cohort plan")
    request_by_sha = {
        str(row["request_sha256"]): row for row in plan.get("requests") or ()
    }
    result_by_sha, coverage_chain = resolve_strategy_cohort_results(
        plan, results, historical_requests=historical_requests,
    )
    source_gaps = {
        str(value) for value in source_gap_request_sha256s
        if str(value) in request_by_sha and str(value) not in result_by_sha
    }
    grammar = OperatorGrammar(
        grammar_id="jaggedthoughts-strategy-phenotype-projection",
        version="1",
        terminals=(TypedTerminal("family", "strategy_phenotype_projection"),),
        operators=tuple(
            TypedOperator(
                f"require_{dimension}", ("strategy_phenotype_projection",),
                "strategy_phenotype_projection",
            )
            for dimension in STRATEGY_PHENOTYPE_DIMENSIONS
        ),
    )
    base = build_typed_program(grammar, terminal_id="family")
    programs = []
    fields_by_program: dict[str, tuple[str, ...]] = {}
    for count in range(len(STRATEGY_PHENOTYPE_DIMENSIONS) + 1):
        for fields in combinations(STRATEGY_PHENOTYPE_DIMENSIONS, count):
            program = base
            for field in fields:
                program = build_typed_program(
                    grammar, operator_id=f"require_{field}", children=(program,),
                )
            programs.append(program)
            fields_by_program[program.program_id] = fields
    enumeration = compile_enumeration_result(
        grammar, programs=programs, max_depth=len(STRATEGY_PHENOTYPE_DIMENSIONS),
        max_programs=2 ** len(STRATEGY_PHENOTYPE_DIMENSIONS),
    )
    peer_count = max(1, len(request_by_sha))
    rows = []
    evaluations = []
    for program in programs:
        fields = fields_by_program[program.program_id]
        roles = []
        for request_sha, request in sorted(request_by_sha.items()):
            entity = str(request["peer_entity_id"])
            result = result_by_sha.get(request_sha)
            if result is None:
                roles.append({
                    "entity_id": entity,
                    "role": "source_gap" if request_sha in source_gaps else "pending",
                    "event_sha256s": [],
                })
                continue
            classification = str(result.get("classification") or "")
            if classification == "no_family_adoption_found":
                roles.append({"entity_id": entity, "role": "control_candidate", "event_sha256s": []})
                continue
            if classification == "insufficient_source_coverage":
                roles.append({"entity_id": entity, "role": "source_gap", "event_sha256s": []})
                continue
            matching = [
                row for row in result.get("events") or ()
                if row.get("implementation_state") in {"operational", "completed"}
                and all((row.get("focal_relation") or {}).get(field) == "same" for field in fields)
            ]
            roles.append({
                "entity_id": entity,
                "role": "treated_candidate" if matching else "related_treatment_excluded",
                "event_sha256s": sorted(str(row["event_sha256"]) for row in matching),
            })
        treated = sum(row["role"] == "treated_candidate" for row in roles)
        controls = sum(row["role"] == "control_candidate" for row in roles)
        covered = sum(row["role"] not in {"pending", "source_gap"} for row in roles)
        objectives = (
            treated / peer_count,
            len(fields) / len(STRATEGY_PHENOTYPE_DIMENSIONS),
            controls / peer_count,
            covered / peer_count,
        )
        signature = tuple(
            [f"fields:{','.join(fields) or 'family'}"]
            + [f"{row['entity_id']}:{row['role']}:{','.join(row['event_sha256s'])}" for row in roles]
        )
        refs = tuple(sorted(
            [str(result_by_sha[sha]["result_sha256"]) for sha in result_by_sha]
            + ([stable_sha256({"source_gap_request_sha256s": sorted(source_gaps)})] if source_gaps else [])
        )) or (str(plan["plan_sha256"]),)
        evaluations.append(CandidateEvaluation(
            program_id=program.program_id, objective_values=objectives,
            behavior_signature=signature, evidence_refs=refs,
        ))
        rows.append({
            "program_id": program.program_id,
            "required_relation_fields": list(fields),
            "specificity": objectives[1],
            "treated_candidate_count": treated,
            "control_candidate_count": controls,
            "classified_coverage_count": covered,
            "peer_roles": roles,
        })
    edges = []
    for left in programs:
        left_fields = set(fields_by_program[left.program_id])
        for right in programs:
            right_fields = set(fields_by_program[right.program_id])
            if len(right_fields) == len(left_fields) + 1 and left_fields < right_fields:
                edges.append((left.program_id, right.program_id))
    neighborhood = Neighborhood("one-moderator-edit", tuple(edges))
    epoch = max(
        [str(plan.get("requests", [{}])[0].get("search_end_at") or "1970-01-01T00:00:00Z")]
        + [str(row.get("assessed_at") or "") for row in result_by_sha.values()]
    )
    scope = FrontierScope(
        grammar_id=grammar.grammar_id, grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        target_type="strategy_phenotype_projection",
        max_depth=len(STRATEGY_PHENOTYPE_DIMENSIONS),
        max_programs=2 ** len(STRATEGY_PHENOTYPE_DIMENSIONS),
        evaluation_model_id="coverage-specificity-before-outcome-v1",
        landscape_mode="fixed", evidence_epoch=epoch,
        objective_names=(
            "treated_coverage", "specificity", "control_coverage", "classified_coverage",
        ),
        neighborhood_id=neighborhood.neighborhood_id,
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope, enumeration=enumeration, evaluations=evaluations,
        neighborhood=neighborhood,
        representation_audit=RepresentationAudit(
            "strategy-phenotype-outcome-stability",
            status="residual",
            residuals=("post_treatment_effect_stability_unmeasured",),
            evidence_refs=(),
        ),
    )
    frontier_ids = set(certificate.frontier_program_ids)
    body = {
        "schema": "jaggedthoughts-strategy-phenotype-projection-frontier-v1",
        "plan_sha256": plan["plan_sha256"],
        "grammar": grammar.to_dict(),
        "enumeration": enumeration.to_dict(),
        "projection_count": len(rows),
        "classified_peer_count": len(result_by_sha),
        "coverage_chain_sha256": coverage_chain["coverage_chain_sha256"],
        "recovered_compatible_result_count": coverage_chain["recovered_compatible_result_count"],
        "pending_interval_refresh_count": sum(
            bool(row.get("pending_delta"))
            for row in coverage_chain.get("bindings") or ()
        ),
        "source_gap_peer_count": len(source_gaps),
        "projections": [
            {**row, "frontier_status": "frontier" if row["program_id"] in frontier_ids else "dominated"}
            for row in rows
        ],
        "certificate": certificate.to_dict(),
        "selection_status": "descriptive_frontier_only",
        "next_activation": (
            "Settle all peer classifications, then acquire post-treatment operating histories."
            if (
                len(result_by_sha) + len(source_gaps) < len(request_by_sha)
                or any(row.get("pending_delta") for row in coverage_chain.get("bindings") or ())
            )
            else "Acquire post-treatment operating histories before selecting a causal grain."
        ),
        "use_boundary": (
            "Coverage and specificity close the declared projection grammar. They cannot establish "
            "effect stability, causal validity, transport, or investment return."
        ),
        "capital_authority": False,
    }
    return {**body, "projection_frontier_sha256": stable_sha256(body)}


__all__ = [
    "STRATEGY_MOVE_LIBRARY_SCHEMA",
    "STRATEGY_MOVE_OUTCOME_SCHEMA",
    "STRATEGY_SCENARIO_CALIBRATION_SCHEMA",
    "STRATEGY_MOVE_CANDIDATE_LINEAGE_FIELDS",
    "STRATEGY_OUTCOME_REQUEST_SCHEMA",
    "STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA",
    "STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA",
    "STRATEGY_PROGRAM_OUTCOME_PLAN_SCHEMA",
    "STRATEGY_COHORT_PLAN_SCHEMA",
    "STRATEGY_COHORT_QUERY_SCHEMA",
    "STRATEGY_COHORT_COVERAGE_CHAIN_SCHEMA",
    "STRATEGY_COHORT_REQUEST_SCHEMA",
    "STRATEGY_COHORT_RESULT_SCHEMA",
    "compile_strategy_cohort_research_plan",
    "compile_strategy_cohort_research_result",
    "resolve_strategy_cohort_results",
    "strategy_cohort_query_identity",
    "strategy_option_comparison_identity",
    "candidate_bound_strategy_move",
    "compatible_strategy_source_request_sha256s",
    "strategy_choice_admission_status",
    "unique_current_candidates_by_entity",
    "compile_strategy_phenotype_projection_frontier",
    "compile_strategy_move_library",
    "compile_workspace_strategy_move_library",
    "due_strategy_outcome_requests",
    "due_strategy_program_adoption_requests",
    "compile_strategy_program_adoption_result",
    "compile_strategy_program_outcome_plan",
]
