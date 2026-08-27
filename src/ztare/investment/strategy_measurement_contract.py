"""Acquire measurable contracts for exact, implemented strategy moves."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .strategy_learning import STRATEGY_MOVE_LIBRARY_SCHEMA
from .strategy_event_refinement import effective_exact_implementation_event
from .strategy_options import compile_company_strategy_frontier


STRATEGY_MEASUREMENT_JOB_KIND = "jaggedthoughts_strategy_measurement_research"
STRATEGY_MEASUREMENT_JOB_SCHEMA = "jaggedthoughts-strategy-measurement-job-v1"
STRATEGY_MEASUREMENT_REQUEST_SCHEMA = "jaggedthoughts-strategy-measurement-request-v3"
STRATEGY_MEASUREMENT_RESULT_SCHEMA = "jaggedthoughts-strategy-measurement-result-v2"
_MIN_PROSPECTIVE_RUNWAY_DAYS = 30
_CLASSIFICATIONS = {"contract_found", "metric_or_threshold_gap", "source_gap"}
_CANDIDATE_LINEAGE_FIELDS = (
    "candidate_leaf", "candidate_sha256", "source_request_sha256",
    "source_dossier_sha256", "strategy_frontier_request_sha256",
)
_VALUATION_DRIVER_KINDS = {
    "operating_margin", "owner_earnings_margin", "reinvestment_growth",
    "revenue_growth", "terminal_growth",
}
_RATE_UNITS = {"decimal", "ratio", "percent", "percentage"}


def strategy_valuation_driver_kind(contract: Mapping[str, Any]) -> str | None:
    """Return the declared driver, with a narrow adapter for legacy rate metrics."""
    declared = str(contract.get("valuation_driver") or "")
    if declared in _VALUATION_DRIVER_KINDS:
        return declared
    metric = str(contract.get("metric_id") or "").lower()
    unit = str(contract.get("unit") or "").lower()
    if unit not in _RATE_UNITS:
        return None
    if "margin" in metric:
        return "owner_earnings_margin" if "owner_earnings" in metric else "operating_margin"
    if "revenue" in metric and "growth" in metric:
        return "revenue_growth"
    if "reinvestment" in metric and "growth" in metric:
        return "reinvestment_growth"
    if "terminal" in metric and "growth" in metric:
        return "terminal_growth"
    return None


def strategy_alpha_operating_contract(contract: Mapping[str, Any]) -> bool:
    """Whether a typed terminal operating hurdle can enter strategy alpha."""
    return (
        str(contract.get("outcome_role") or "terminal_operating")
        == "terminal_operating"
        and strategy_valuation_driver_kind(contract) is not None
    )


def _verified(payload: Mapping[str, Any], schema: str, hash_field: str) -> dict[str, Any]:
    body = dict(payload)
    declared = require_text(body.pop(hash_field, ""), hash_field)
    if body.get("schema") != schema or stable_sha256(body) != declared:
        raise ValueError(f"invalid {schema} identity")
    return {**body, hash_field: declared}


def _verified_library(library: Mapping[str, Any]) -> dict[str, Any]:
    return _verified(library, STRATEGY_MOVE_LIBRARY_SCHEMA, "library_sha256")


def normalize_strategy_measurement_parent_profile(
    parent_profile: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    """Migrate the one legacy partial-lineage shape into the current compiler."""
    profile = deepcopy(dict(parent_profile))
    company = dict(profile.get("company") or {})
    present = [field for field in _CANDIDATE_LINEAGE_FIELDS if company.get(field)]
    migration = "none"
    if present and len(present) != len(_CANDIDATE_LINEAGE_FIELDS):
        company["legacy_candidate_lineage"] = {
            field: company[field] for field in present
        }
        for field in _CANDIDATE_LINEAGE_FIELDS:
            company.pop(field, None)
        profile["company"] = company
        migration = "drop_incomplete_legacy_candidate_lineage"
    return profile, migration


def strategy_measurement_event(
    move: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str, str | None]:
    """Return the exact event without rewriting an interval-censored move."""
    event = effective_exact_implementation_event(move)
    if event is None:
        return None, "unavailable", None
    result_sha = event.get("refinement_result_sha256")
    return event, (
        "timing_refinement" if result_sha else "authored_event"
    ), str(result_sha) if result_sha else None


def _measurement_relation(
    event: Mapping[str, Any], measured_at: str,
) -> dict[str, Any]:
    """Classify whether a measurement still inhabits its mechanism's lifetime."""
    if event.get("implementation_mode") != "supply_commitment":
        return {"status": "point_event_followup", "mechanism_effective_until": None}
    raw_until = event.get("mechanism_effective_until")
    if not raw_until:
        raise ValueError("strategy measurement mechanism_window_unresolved")
    effective_until = canonical_timestamp(raw_until, "mechanism effective_until")
    occurred_at = canonical_timestamp(event.get("occurred_at"), "measurement event occurred_at")
    if timestamp_key(effective_until) < timestamp_key(occurred_at):
        raise ValueError("strategy measurement mechanism window ends before its event")
    if timestamp_key(effective_until) < timestamp_key(measured_at):
        raise ValueError("strategy measurement expired_mechanism_gap")
    return {
        "status": "active_mechanism",
        "mechanism_effective_until": effective_until,
    }


def _verified_measurement_request(request: Mapping[str, Any]) -> dict[str, Any]:
    verified = _verified(request, STRATEGY_MEASUREMENT_REQUEST_SCHEMA, "request_sha256")
    _measurement_relation(verified["implementation_event"], str(verified["created_at"]))
    return verified


def compile_strategy_measurement_contract_request(
    move: Mapping[str, Any], *, library: Mapping[str, Any],
    parent_profile: Mapping[str, Any], parent_profile_path: str, created_at: str,
) -> dict[str, Any]:
    """Freeze one exact move-to-measurement acquisition question."""
    verified_library = _verified_library(library)
    admitted_move = next((
        row for row in verified_library.get("moves") or ()
        if row.get("move_sha256") == move.get("move_sha256")
    ), None)
    if admitted_move is None or dict(admitted_move) != dict(move):
        raise ValueError("measurement move is not an exact member of the verified library")
    move = admitted_move
    normalized_parent, migration = normalize_strategy_measurement_parent_profile(parent_profile)
    parent = compile_company_strategy_frontier(normalized_parent)
    frontier_sha = require_text(move.get("strategy_frontier_sha256"), "parent frontier")
    frontier_moves = [
        row for row in verified_library.get("moves") or ()
        if row.get("strategy_frontier_sha256") == frontier_sha
    ]
    expected_options = sorted(
        (str(row.get("option_id") or ""), str(row.get("option_sha256") or ""))
        for row in frontier_moves
    )
    parent_options = sorted(
        (str(row.get("option_id") or ""), str(row.get("option_sha256") or ""))
        for row in parent.get("option_catalog") or ()
    )
    if (
        not frontier_moves or expected_options != parent_options
        or {str(row.get("entity_id") or "") for row in frontier_moves}
        != {str((parent.get("company") or {}).get("id") or "")}
        or {canonical_timestamp(row.get("evidence_epoch"), "measurement move epoch")
            for row in frontier_moves} != {str(parent["evidence_epoch"])}
    ):
        raise ValueError("measurement parent differs from its admitted frontier option catalog")
    frontier_binding = (
        "exact_frontier_sha256"
        if parent.get("strategy_frontier_sha256") == frontier_sha
        else "compiler_migration_full_option_catalog"
    )
    option_id = require_text(move.get("option_id"), "measurement option_id")
    event, event_source, refinement_sha = strategy_measurement_event(move)
    existing_contracts = tuple(
        row for row in move.get("outcome_contracts") or () if isinstance(row, Mapping)
    )
    if (
        move.get("claim_status") != "supported"
        or event is None
        or any(strategy_alpha_operating_contract(row) for row in existing_contracts)
    ):
        raise ValueError(
            "measurement acquisition requires a supported exact adoption without a terminal valuation hurdle"
        )
    option = next(
        (row for row in parent.get("option_catalog") or () if row.get("option_id") == option_id),
        None,
    )
    if not option or option.get("option_sha256") != move.get("option_sha256"):
        raise ValueError("measurement move and parent option differ")
    epoch = canonical_timestamp(created_at, "measurement request created_at")
    if timestamp_key(epoch) <= timestamp_key(str(parent["evidence_epoch"])):
        raise ValueError("measurement request must postdate its parent frontier")
    if timestamp_key(canonical_timestamp(
        event.get("available_at"), "measurement event available_at",
    )) > timestamp_key(epoch):
        raise ValueError("measurement event was unavailable when the request was frozen")
    if event_source == "timing_refinement" and timestamp_key(canonical_timestamp(
        (move.get("timing_refinement") or {}).get("assessed_at"),
        "measurement timing refinement assessed_at",
    )) > timestamp_key(epoch):
        raise ValueError("measurement timing refinement postdates its request")
    measurement_relation = _measurement_relation(event, epoch)
    body = {
        "schema": STRATEGY_MEASUREMENT_REQUEST_SCHEMA,
        "request_id": f"strategy-measurement:{str(move['move_sha256'])[:24]}:{epoch[:10]}",
        "created_at": epoch,
        "library_sha256": verified_library["library_sha256"],
        "parent_strategy_frontier_sha256": frontier_sha,
        "parent_profile_path": require_text(parent_profile_path, "parent profile path"),
        "parent_profile_sha256": stable_sha256(parent_profile),
        "parent_profile_recompiled_frontier_sha256": parent["strategy_frontier_sha256"],
        "parent_frontier_binding": frontier_binding,
        "parent_option_catalog_sha256": stable_sha256(parent_options),
        "parent_profile_migration": migration,
        "entity_id": require_text(move.get("entity_id"), "measurement entity_id"),
        "move_sha256": require_text(move.get("move_sha256"), "measurement move hash"),
        "option_id": option_id,
        "option_sha256": require_text(move.get("option_sha256"), "measurement option hash"),
        "mechanism": dict(move.get("mechanism") or {}),
        "implementation_event": dict(event),
        "mechanism_measurement_relation": measurement_relation,
        "implementation_event_source": event_source,
        "timing_refinement_result_sha256": refinement_sha,
        "required_contract_predicate": (
            "valuation_compatible_terminal" if existing_contracts else "any_measurable_contract"
        ),
        "prior_evidence_refs": sorted(map(str, move.get("evidence_refs") or ())),
        "source_classes": ["sec_filing", "issuer_results", "issuer_strategy"],
        "expected_exit": "source_bound_contract_or_typed_gap",
        "capital_authority": False,
    }
    return {**body, "request_sha256": stable_sha256(body)}


def due_strategy_measurement_contract_requests(
    library: Mapping[str, Any], *,
    parent_profiles: Mapping[str, tuple[str, Mapping[str, Any]]], as_of: str,
    prior_requests: Iterable[Mapping[str, Any]] = (),
    prior_results: Iterable[Mapping[str, Any]] = (), max_requests: int = 4,
) -> list[dict[str, Any]]:
    """Select only current exact adoptions that still lack a measurable contract."""
    verified = _verified_library(library)
    request_rows = tuple(row for row in prior_requests if isinstance(row, Mapping))
    result_rows = tuple(row for row in prior_results if isinstance(row, Mapping))
    request_by_move = {str(row.get("move_sha256") or ""): row for row in request_rows}
    result_by_request = {str(row.get("request_sha256") or ""): row for row in result_rows}

    def satisfied(request: Mapping[str, Any], result: Mapping[str, Any]) -> bool:
        if result.get("classification") != "contract_found":
            return False
        contracts = tuple(
            row for row in result.get("contracts") or () if isinstance(row, Mapping)
        )
        return bool(contracts) and (
            request.get("required_contract_predicate") != "valuation_compatible_terminal"
            or any(strategy_alpha_operating_contract(row) for row in contracts)
        )
    latest_epoch = {}
    for move in verified.get("moves") or ():
        entity = str(move.get("entity_id") or "")
        epoch = canonical_timestamp(move.get("evidence_epoch"), "measurement move epoch")
        if entity not in latest_epoch or timestamp_key(epoch) > timestamp_key(latest_epoch[entity]):
            latest_epoch[entity] = epoch
    requests = []
    selected_frontiers = set()
    settled_parent_frontiers = {
        str(request.get("parent_strategy_frontier_sha256") or "")
        for request in request_rows
        if any(
            strategy_alpha_operating_contract(contract)
            for contract in (
                result_by_request.get(str(request.get("request_sha256") or "")) or {}
            ).get("contracts") or ()
            if isinstance(contract, Mapping)
        )
    }
    for move in verified.get("moves") or ():
        move_sha = str(move.get("move_sha256") or "")
        parent = parent_profiles.get(str(move.get("strategy_frontier_sha256") or ""))
        if (
            not parent or not move_sha
            or canonical_timestamp(move.get("evidence_epoch"), "measurement move epoch")
            != latest_epoch.get(str(move.get("entity_id") or ""))
        ):
            continue
        path, profile = parent
        frontier_sha = str(move.get("strategy_frontier_sha256") or "")
        if frontier_sha in selected_frontiers or frontier_sha in settled_parent_frontiers:
            continue
        prior = request_by_move.get(move_sha)
        prior_result = result_by_request.get(str((prior or {}).get("request_sha256") or ""))
        if prior_result:
            if satisfied(prior or {}, prior_result):
                continue
            retry_at = timestamp_key(str(prior_result.get("assessed_at"))) + timedelta(days=90)
            if timestamp_key(as_of) < retry_at:
                continue
        try:
            request = prior if prior and not prior_result else compile_strategy_measurement_contract_request(
                move, library=verified, parent_profile=profile,
                parent_profile_path=path, created_at=as_of,
            )
            _verified_measurement_request(request)
            requests.append(dict(request))
            selected_frontiers.add(frontier_sha)
        except ValueError:
            continue
    return sorted(requests, key=lambda row: (row["entity_id"], row["option_id"]))[:max_requests]


def strategy_measurement_output_schema() -> dict[str, Any]:
    text = {"type": "string", "minLength": 1}
    source = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "id": text, "title": text, "url": {"type": "string", "pattern": "^https://"},
            "publisher": text, "source_kind": {
                "type": "string", "enum": ["filing", "issuer"],
            },
            "published_at": text, "accessed_at": text,
            "supports": {"type": "array", "items": text, "minItems": 1},
        },
        "required": [
            "id", "title", "url", "publisher", "source_kind", "published_at",
            "accessed_at", "supports",
        ],
    }
    contract = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "contract_id": text, "metric_id": text, "unit": text,
            "valuation_driver": {
                "type": "string", "enum": sorted(_VALUATION_DRIVER_KINDS),
            },
            "direction": {"type": "string", "enum": ["increase", "decrease"]},
            "minimum_effect": {"type": "number", "minimum": 0},
            "minimum_effect_basis": {
                "type": "string", "enum": ["directional_zero", "source_disclosed"],
            },
            "minimum_effect_rationale": text,
            "minimum_effect_source_refs": {"type": "array", "items": text},
            "horizon_days": {"type": "integer", "minimum": 30, "maximum": 3650},
            "measurement_start_at": text,
            "comparator": {"type": "string", "const": "pre_move_baseline"},
            "outcome_role": {"type": "string", "enum": ["leading_operating", "terminal_operating"]},
            "acquisition_mode": {"type": "string", "const": "subscription_primary_document"},
            "objective_coordinate": text,
            "metric_locator": text,
            "economic_bridge_rationale": text,
            "evidence_refs": {"type": "array", "items": text, "minItems": 1},
        },
        "required": [
            "contract_id", "metric_id", "unit", "direction", "minimum_effect",
            "minimum_effect_basis", "minimum_effect_rationale", "minimum_effect_source_refs",
            "horizon_days", "measurement_start_at", "comparator", "outcome_role",
            "acquisition_mode", "objective_coordinate", "metric_locator",
            "economic_bridge_rationale", "evidence_refs",
        ],
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object", "additionalProperties": False,
        "properties": {
            "schema": {"type": "string", "const": STRATEGY_MEASUREMENT_RESULT_SCHEMA},
            "request_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "move_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "option_id": text, "assessed_at": text,
            "classification": {"type": "string", "enum": sorted(_CLASSIFICATIONS)},
            "contracts": {"type": "array", "items": contract, "maxItems": 2},
            "sources": {"type": "array", "items": source},
            "residuals": {"type": "array", "items": text},
            "capital_authority": {"type": "boolean", "const": False},
        },
        "required": [
            "schema", "request_sha256", "move_sha256", "option_id", "assessed_at",
            "classification", "contracts", "sources", "residuals", "capital_authority",
        ],
    }


def compile_strategy_measurement_contract_result(
    raw: Mapping[str, Any], request: Mapping[str, Any], *, accepted_at: str | None = None,
) -> dict[str, Any]:
    """Validate a web-research result against its exact frozen move."""
    req = _verified_measurement_request(request)
    if {
        "schema": raw.get("schema"), "request_sha256": raw.get("request_sha256"),
        "move_sha256": raw.get("move_sha256"), "option_id": raw.get("option_id"),
        "capital_authority": raw.get("capital_authority"),
    } != {
        "schema": STRATEGY_MEASUREMENT_RESULT_SCHEMA, "request_sha256": req["request_sha256"],
        "move_sha256": req["move_sha256"], "option_id": req["option_id"],
        "capital_authority": False,
    }:
        raise ValueError("measurement result differs from its frozen move identity")
    assessed_at = canonical_timestamp(accepted_at or raw.get("assessed_at"), "measurement assessed_at")
    if timestamp_key(assessed_at) < timestamp_key(str(req["created_at"])):
        raise ValueError("measurement result predates its request")
    classification = require_text(raw.get("classification"), "measurement classification")
    if classification not in _CLASSIFICATIONS:
        raise ValueError("unsupported measurement classification")
    residuals = sorted({
        require_text(value, "measurement residual")
        for value in raw.get("residuals") or ()
    })
    if classification != "contract_found" and not residuals:
        raise ValueError("a measurement gap requires a specific residual")
    sources = [dict(row) for row in raw.get("sources") or () if isinstance(row, Mapping)]
    source_ids = set()
    source_supports: dict[str, set[str]] = {}
    for source in sources:
        source_id = require_text(source.get("id"), "measurement source id")
        if source_id in source_ids or source.get("source_kind") not in {"filing", "issuer"}:
            raise ValueError("measurement sources must be unique primary public documents")
        if not str(source.get("url") or "").startswith("https://"):
            raise ValueError("measurement source URL must use https")
        published = canonical_timestamp(source.get("published_at"), "measurement source published_at")
        accessed = canonical_timestamp(source.get("accessed_at"), "measurement source accessed_at")
        if (
            timestamp_key(published) > timestamp_key(accessed)
            or timestamp_key(accessed) < timestamp_key(str(req["created_at"]))
            or timestamp_key(accessed) > timestamp_key(assessed_at)
        ):
            raise ValueError("measurement source chronology is invalid")
        supports = {
            require_text(value, "measurement source support")
            for value in source.get("supports") or ()
        }
        if not supports:
            raise ValueError("measurement source requires a claim locator")
        source.update({
            "published_at": published, "accessed_at": accessed,
            "supports": sorted(supports),
        })
        source_ids.add(source_id)
        source_supports[source_id] = supports
    contracts = [dict(row) for row in raw.get("contracts") or () if isinstance(row, Mapping)]
    if (classification == "contract_found") != bool(contracts) or len(contracts) > 2:
        raise ValueError("measurement classification and contract count disagree")
    if classification == "contract_found" and not sources:
        raise ValueError("a measurement contract requires opened primary sources")
    if classification == "metric_or_threshold_gap" and not sources:
        raise ValueError("a metric gap requires an opened primary-source search")
    bridge = str((req.get("mechanism") or {}).get("economic_bridge") or "")
    normalized_contracts = []
    for contract in contracts:
        direction = require_text(contract.get("direction"), "measurement direction")
        comparator = require_text(contract.get("comparator"), "measurement comparator")
        role = require_text(contract.get("outcome_role"), "measurement outcome role")
        mode = require_text(contract.get("acquisition_mode"), "measurement acquisition mode")
        basis = require_text(contract.get("minimum_effect_basis"), "measurement effect basis")
        if direction not in {"increase", "decrease"} or comparator != "pre_move_baseline":
            raise ValueError("unsupported measurement direction or comparator")
        if role not in {"leading_operating", "terminal_operating"} or mode != "subscription_primary_document":
            raise ValueError("unsupported measurement role or acquisition mode")
        if basis not in {"directional_zero", "source_disclosed"}:
            raise ValueError("unsupported minimum-effect basis")
        effect = require_finite(contract.get("minimum_effect"), "measurement minimum effect")
        horizon = int(contract.get("horizon_days") or 0)
        start = canonical_timestamp(contract.get("measurement_start_at"), "measurement start")
        refs = sorted(set(map(str, contract.get("evidence_refs") or ())))
        threshold_refs = sorted(set(map(str, contract.get("minimum_effect_source_refs") or ())))
        if effect < 0 or not 30 <= horizon <= 3650 or not refs or not set(refs).issubset(source_ids):
            raise ValueError("measurement contract numeric or source boundary is invalid")
        metric_id = require_text(contract.get("metric_id"), "measurement metric id")
        valuation_driver = contract.get("valuation_driver")
        if valuation_driver is not None and valuation_driver not in _VALUATION_DRIVER_KINDS:
            raise ValueError("measurement valuation driver is unsupported")
        if not any(
            {f"metric:{metric_id}", "clock"}.issubset(source_supports[source_id])
            for source_id in refs
        ):
            raise ValueError("measurement metric and clock need one source-bound locator")
        if basis == "directional_zero" and effect != 0:
            raise ValueError("directional-zero contract requires zero minimum effect")
        if basis == "source_disclosed" and (not threshold_refs or not set(threshold_refs).issubset(set(refs))):
            raise ValueError("source-disclosed threshold requires bound sources")
        if basis == "source_disclosed" and not any(
            "threshold" in source_supports[source_id] for source_id in threshold_refs
        ):
            raise ValueError("source-disclosed threshold lacks a source locator")
        if basis != "source_disclosed" and threshold_refs:
            raise ValueError("non-source threshold cannot cite threshold sources")
        if (
            timestamp_key(start) < timestamp_key(str(req["created_at"]))
            or timestamp_key(start) > timestamp_key(assessed_at)
            or timestamp_key(start) + timedelta(days=horizon)
            < timestamp_key(assessed_at) + timedelta(days=_MIN_PROSPECTIVE_RUNWAY_DAYS)
        ):
            raise ValueError("measurement clock requires a post-freeze prospective runway")
        mechanism_until = (req.get("mechanism_measurement_relation") or {}).get(
            "mechanism_effective_until"
        )
        if mechanism_until and timestamp_key(start) + timedelta(days=horizon) > timestamp_key(
            str(mechanism_until)
        ):
            raise ValueError("measurement horizon outlives its active mechanism")
        if contract.get("objective_coordinate") != bridge:
            raise ValueError("measurement contract targets another economic coordinate")
        normalized_contracts.append({
            "contract_id": require_text(contract.get("contract_id"), "measurement contract id"),
            "metric_id": metric_id,
            "unit": require_text(contract.get("unit"), "measurement unit"),
            "direction": direction, "minimum_effect": effect,
            "minimum_effect_basis": basis,
            "minimum_effect_rationale": require_text(contract.get("minimum_effect_rationale"), "measurement effect rationale"),
            "minimum_effect_source_refs": threshold_refs, "horizon_days": horizon,
            "measurement_start_at": start, "comparator": comparator,
            "outcome_role": role, "acquisition_mode": mode,
            "objective_coordinate": bridge,
            "metric_locator": require_text(
                contract.get("metric_locator"), "measurement metric locator",
            ),
            "economic_bridge_rationale": require_text(
                contract.get("economic_bridge_rationale"),
                "measurement economic bridge rationale",
            ),
            "evidence_refs": refs,
            **({"valuation_driver": require_text(
                valuation_driver, "measurement valuation driver",
            )} if contract.get("valuation_driver") is not None else {}),
        })
    if len({row["contract_id"] for row in normalized_contracts}) != len(normalized_contracts):
        raise ValueError("measurement contract IDs must be unique")
    if len({row["outcome_role"] for row in normalized_contracts}) != len(normalized_contracts):
        raise ValueError("measurement outcome roles must be unique")
    if (
        req.get("required_contract_predicate") == "valuation_compatible_terminal"
        and classification == "contract_found"
        and not any(strategy_alpha_operating_contract(row) for row in normalized_contracts)
    ):
        raise ValueError("measurement result lacks the required terminal valuation hurdle")
    body = {
        "schema": STRATEGY_MEASUREMENT_RESULT_SCHEMA,
        "request_sha256": req["request_sha256"], "move_sha256": req["move_sha256"],
        "option_id": req["option_id"], "assessed_at": assessed_at,
        "classification": classification, "contracts": normalized_contracts,
        "sources": sources, "residuals": residuals,
        "capital_authority": False,
    }
    result = {**body, "result_sha256": stable_sha256(body)}
    if raw.get("result_sha256") not in {None, result["result_sha256"]}:
        raise ValueError("measurement result content hash mismatch")
    return result


def build_strategy_measurement_successor_profile(
    parent_profile: Mapping[str, Any], request: Mapping[str, Any], result: Mapping[str, Any],
) -> dict[str, Any]:
    """Copy the parent and append only contracts supported by one exact receipt."""
    req = _verified_measurement_request(request)
    res = _verified(result, STRATEGY_MEASUREMENT_RESULT_SCHEMA, "result_sha256")
    normalized_parent, migration = normalize_strategy_measurement_parent_profile(parent_profile)
    parent = compile_company_strategy_frontier(normalized_parent)
    if (
        stable_sha256(parent_profile) != req["parent_profile_sha256"]
        or parent["strategy_frontier_sha256"]
        != req["parent_profile_recompiled_frontier_sha256"]
        or stable_sha256(sorted(
            (str(row.get("option_id") or ""), str(row.get("option_sha256") or ""))
            for row in parent.get("option_catalog") or ()
        )) != req["parent_option_catalog_sha256"]
        or migration != req["parent_profile_migration"]
        or res["request_sha256"] != req["request_sha256"]
        or res["classification"] != "contract_found"
    ):
        raise ValueError("measurement successor identities are incompatible")
    successor = normalized_parent
    successor["evidence_epoch"] = res["assessed_at"]
    company = dict(successor.get("company") or {})
    lineage = list(company.get("strategy_measurement_lineage") or ())
    lineage.append({
        "parent_strategy_frontier_sha256": req["parent_strategy_frontier_sha256"],
        "request_sha256": req["request_sha256"],
        "result_sha256": res["result_sha256"], "sources": res["sources"],
        "effective_implementation_event_sha256": req["implementation_event"][
            "implementation_event_sha256"
        ],
        "timing_refinement_result_sha256": req.get("timing_refinement_result_sha256"),
    })
    company["strategy_measurement_lineage"] = lineage
    successor["company"] = company
    target = next((row for row in successor.get("options") or () if row.get("id") == req["option_id"]), None)
    if target is None:
        raise ValueError("measurement successor target option is absent")
    sources = {str(row["id"]): dict(row) for row in res["sources"]}
    additions = [
        {
            "id": row["contract_id"],
            **{key: value for key, value in row.items() if key != "contract_id"},
            "measurement_source_catalog": [
                sources[source_id] for source_id in row["evidence_refs"]
            ],
        }
        for row in res["contracts"]
    ]
    existing = list(target.get("outcome_contracts") or ())
    if {str(row.get("id") or "") for row in existing} & {
        str(row.get("id") or "") for row in additions
    }:
        raise ValueError("measurement successor cannot replace an existing contract")
    target["outcome_contracts"] = [*existing, *additions]
    if req.get("implementation_event_source") == "timing_refinement":
        event = req["implementation_event"]
        target["implementation_event"] = {
            "id": event["event_id"], "event_kind": "adoption",
            "implementation_mode": event["implementation_mode"],
            "status_after": event["status_after"],
            "occurred_at": event["occurred_at"], "available_at": event["available_at"],
            "timing_precision": "date", "source_refs": event["source_refs"],
        }
    compile_company_strategy_frontier(successor)
    return successor


def dump_strategy_measurement_successor_yaml(path: str | Path, profile: Mapping[str, Any]) -> None:
    Path(path).write_text(yaml.safe_dump(dict(profile), sort_keys=False, allow_unicode=True), encoding="utf-8")


__all__ = [
    "STRATEGY_MEASUREMENT_JOB_KIND", "STRATEGY_MEASUREMENT_JOB_SCHEMA",
    "STRATEGY_MEASUREMENT_REQUEST_SCHEMA", "STRATEGY_MEASUREMENT_RESULT_SCHEMA",
    "build_strategy_measurement_successor_profile",
    "compile_strategy_measurement_contract_request",
    "compile_strategy_measurement_contract_result",
    "due_strategy_measurement_contract_requests",
    "normalize_strategy_measurement_parent_profile", "strategy_measurement_output_schema",
    "strategy_alpha_operating_contract", "strategy_measurement_event",
    "strategy_valuation_driver_kind",
]
