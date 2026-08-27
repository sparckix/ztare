"""Issue-time proposal and activation for strategy-alpha forecast bindings."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_refs, require_text, timestamp_key
from .strategy_alpha_tournament import (
    STRATEGY_ALPHA_BINDING_SCHEMA,
    validate_strategy_alpha_binding_abi,
)
from .strategy_learning import (
    candidate_bound_strategy_move,
    compatible_strategy_source_request_sha256s,
    covered_strategy_source_request_sha256s,
    strategy_choice_admission_status,
    unique_current_candidates_by_entity,
)
from .strategy_valuation_bridge import compile_direct_strategy_expectation_residual


STRATEGY_ALPHA_PROPOSAL_SCHEMA = "jaggedthoughts-strategy-alpha-binding-proposal-v1"
STRATEGY_ALPHA_BINDING_STATUS_SCHEMA = "jaggedthoughts-strategy-alpha-binding-status-v1"
STRATEGY_ALPHA_ACTION_REQUEST_SCHEMA = "jaggedthoughts-strategy-alpha-action-request-v1"
STRATEGY_ALPHA_ACTION_PROPOSAL_SCHEMA = "jaggedthoughts-strategy-alpha-action-proposal-v1"
STRATEGY_ALPHA_ISSUANCE_ACTION_SCHEMA = "jaggedthoughts-strategy-alpha-issuance-action-v1"
STRATEGY_ALPHA_ACTIVATION_STATUS_SCHEMA = "jaggedthoughts-strategy-alpha-activation-status-v1"
STRATEGY_ALPHA_ARM_ISOLATION_SCHEMA = "jaggedthoughts-strategy-alpha-arm-isolation-v1"
STRATEGY_ALPHA_PROCEDURE_SCHEMA = "jaggedthoughts-strategy-alpha-procedure-v1"
_ISSUANCE_WINDOW_SECONDS = 300
_DURABILITY = "durable_earnings_expectation"
_STRATEGY = "source_bound_strategy_phenotype"
_TYPED_RESIDUAL = "typed_strategy_expectation_residual"
_VALUATION = {"price_implied_expectations", "price_implied_excess_return"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _hashed(payload: Mapping[str, Any], field: str) -> dict[str, Any]:
    body = dict(payload)
    return {**body, field: stable_sha256(body)}


def _valid_hash(payload: Mapping[str, Any], field: str) -> bool:
    claimed = str(payload.get(field) or "")
    return bool(claimed) and claimed == stable_sha256({
        key: value for key, value in payload.items() if key != field
    })


def _gap(code: str, **context: Any) -> dict[str, Any]:
    return _hashed({"code": code, **context}, "gap_sha256")


def _is_sha(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value.lower())


def _sha256(value: Any, label: str) -> str:
    digest = require_text(value, label).lower()
    if not _is_sha(digest):
        raise ValueError(f"{label} must be a full SHA-256 digest")
    return digest


def _underperformance_probability(expected_active_return: float, horizon_days: int) -> float:
    scale = 0.20 * math.sqrt(max(1.0, horizon_days) / 365.25)
    return 1.0 / (1.0 + math.exp(expected_active_return / max(scale, 1e-9)))


def compile_strategy_alpha_procedure(
    *, runtime: str, model: str, reasoning_effort: str,
    output_schema_sha256: str,
) -> dict[str, Any]:
    """Freeze the probability forecaster procedure independently of episode data."""

    body = {
        "schema": STRATEGY_ALPHA_PROCEDURE_SCHEMA,
        "procedure_version": "priced-operating-hurdle-probability-v2",
        "runtime": require_text(runtime, "strategy procedure runtime"),
        "model": require_text(model, "strategy procedure model"),
        "reasoning_effort": require_text(
            reasoning_effort, "strategy procedure reasoning_effort"
        ),
        "web_research": False,
        "target_masking": (
            "operating_evidence_only; valuation, payoff, and security control excluded"
        ),
        "prompt_contract": "estimate_operating_hurdle_probability_only-v2",
        "output_schema_sha256": _sha256(
            output_schema_sha256, "strategy procedure output_schema_sha256"
        ),
        "residual_compiler": "direct-operating-hurdle-payoff-v1",
        "control_compiler": "valuation-times-durable-earnings-power-v1",
    }
    return _hashed(body, "procedure_sha256")


def strategy_alpha_action_contract(root: Path | None = None) -> dict[str, Any]:
    """Describe the only accepted upstream input for an issue-time binding."""

    relative = "closed_book/strategy_alpha_actions/<action_id>.json"
    return {
        "schema": STRATEGY_ALPHA_ISSUANCE_ACTION_SCHEMA,
        "action_path": (root / relative).as_posix() if root else relative,
        "required_fields": [
            "schema", "action_id", "entity_id", "subject_id", "horizon_days",
            "request_sha256", "nomination_sha256", "dual_outcome_contract_sha256",
            "candidate_leaf", "move_sha256", "implementation_event_sha256",
            "strategy_choice_identity_sha256",
            "information_set_sha256", "available_at", "expires_at",
            "phenotype_sha256", "durability_evidence", "arm_isolation", "arms",
            "strategy_expectation_residual",
            "strategy_procedure",
            "strategy_provider_result", "provider_result_provenance",
            "issuance_contract_version",
            "capital_authority", "action_sha256",
        ],
        "durability_evidence_required_fields": ["available_at", "source_refs"],
        "arm_required_fields": [
            "candidate_id", "mechanism_ids", "predicted_active_return",
            "underperformance_probability", "target_weight", "source_refs", "explanation",
        ],
        "required_arm_roles": ["valuation", "durability", "strategy"],
        "mechanism_contract": {
            "valuation": ["price_implied_expectations|price_implied_excess_return"],
            "durability": [
                "price_implied_expectations|price_implied_excess_return",
                _DURABILITY,
            ],
            "strategy": [
                "price_implied_expectations|price_implied_excess_return",
                _DURABILITY,
                _STRATEGY,
                _TYPED_RESIDUAL,
            ],
        },
        "notes": [
            "Controls are deterministic; the masked strategy call estimates only the operating-hurdle probability.",
            "The action and its evidence must be available before the closed-book run opens.",
            "The exact phenotype must already be admitted by the strategy-move library.",
            "The estimated probability must replay from the hashed subscription result and dispatch receipts.",
        ],
        "capital_authority": False,
    }


def compile_strategy_alpha_arm_views(
    request: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Compile the only evidence view each nested forecast arm may observe."""

    if (
        request.get("schema") != STRATEGY_ALPHA_ACTION_REQUEST_SCHEMA
        or not _valid_hash(request, "request_sha256")
    ):
        raise ValueError("strategy-alpha action request is invalid")
    evidence = dict(request.get("evidence") or {})
    candidate = dict(evidence.get("candidate") or {})
    candidate_identity = {
        key: candidate.get(key) for key in (
            "candidate_id", "candidate_sha256", "entity_id", "as_of", "source_refs",
        )
    }
    common = {
        "entity_id": request["entity_id"],
        "horizon_days": request["horizon_days"],
    }
    dual = dict(evidence.get("dual_outcome_contract") or {})
    operating_only = {
        key: dual.get(key) for key in (
            "dual_outcome_contract_sha256", "entity_id", "candidate_leaf",
            "candidate_sha256", "move_sha256", "strategy_choice_identity_sha256",
            "mechanism_phenotype_sha256", "implementation_event_sha256",
            "strategy_program_attribution", "implementation_available_at",
            "operating_outcome", "frozen_at", "source_refs",
        )
    }
    visible = {
        "valuation": {},
        "durability": {"quality": evidence.get("quality")},
        "strategy": {
            "quality": evidence.get("quality"),
            "exact_move_event": evidence.get("exact_move_event"),
            "operating_hurdle_contract": operating_only,
        },
    }
    excluded = {
        "valuation": [
            "quality", "exact_move_event", "dual_outcome_contract",
            "strategy_expectation_residual",
        ],
        "durability": [
            "exact_move_event", "dual_outcome_contract",
            "strategy_expectation_residual",
        ],
        "strategy": [
            "candidate_valuation", "security_outcome_control",
            "strategy_expectation_residual", "incremental_horizon_payoff",
        ],
    }
    views = {}
    for role in request["required_arms"]:
        body = {
            "schema": "jaggedthoughts-strategy-alpha-arm-view-v1",
            "role": role,
            **common,
            "candidate": {
                **candidate_identity,
                **({"valuation": candidate.get("valuation")} if role != "strategy" else {}),
            },
            "evidence": visible[role],
            "excluded_evidence_sections": excluded[role],
            "web_cutoff_at": request["created_at"],
            "capital_authority": False,
        }
        views[role] = {**body, "arm_view_sha256": stable_sha256(body)}
    return views


def compile_strategy_alpha_deterministic_controls(
    request: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Freeze transparent valuation and value-quality forecasts for one request."""

    if (
        request.get("schema") != STRATEGY_ALPHA_ACTION_REQUEST_SCHEMA
        or not _valid_hash(request, "request_sha256")
    ):
        raise ValueError("strategy-alpha action request is invalid")
    evidence = dict(request.get("evidence") or {})
    residual = dict(evidence.get("strategy_expectation_residual") or {})
    if (
        residual.get("schema")
        != "jaggedthoughts-direct-strategy-expectation-residual-v1"
        or not _valid_hash(residual, "residual_sha256")
        or residual.get("status") != "compiled"
    ):
        raise ValueError("strategy-alpha request lacks a typed expectation residual")
    horizon = int(request["horizon_days"])
    candidate = dict(evidence.get("candidate") or {})
    annual_valuation = require_finite(
        (((candidate.get("valuation") or {}).get("summary") or {}).get(
            "price_implied_excess_return"
        )),
        "candidate price-implied excess return",
    )
    if annual_valuation <= -1:
        raise ValueError("candidate valuation cannot annualize a return at or below -100%")
    valuation = (1.0 + annual_valuation) ** (horizon / 365.25) - 1.0
    if abs(valuation - require_finite(
        (residual.get("baseline") or {}).get("horizon_active_return"),
        "residual baseline return",
    )) > 1e-12:
        raise ValueError("strategy residual baseline differs from the deterministic valuation control")
    quality = require_finite(
        ((evidence.get("quality") or {}).get("scores") or {}).get(
            "durable_earnings_power"
        ),
        "durable earnings score",
    )
    if not 0 <= quality <= 1:
        raise ValueError("durable earnings score must be in [0, 1]")
    durability = valuation * quality
    views = compile_strategy_alpha_arm_views(request)
    rows = {
        "valuation": {
            "predicted_active_return": valuation,
            "underperformance_probability": _underperformance_probability(
                valuation, horizon
            ),
            "rule": "typed price-implied excess return converted to the frozen horizon",
            "inputs": {"candidate_sha256": candidate.get("candidate_sha256")},
        },
        "durability": {
            "predicted_active_return": durability,
            "underperformance_probability": _underperformance_probability(
                durability, horizon
            ),
            "rule": "valuation * durable_earnings_power",
            "inputs": {
                "valuation_return": valuation,
                "durable_earnings_power": quality,
            },
        },
    }
    return {
        role: _hashed({
            "schema": "jaggedthoughts-strategy-alpha-deterministic-arm-v1",
            "role": role,
            "arm_view_sha256": views[role]["arm_view_sha256"],
            **row,
        }, "deterministic_arm_sha256")
        for role, row in rows.items()
    }


def _exact_phenotypes(
    root: Path, entity_id: str, *, candidate_leaf: str, candidate_sha256: str,
    as_of: str | None = None,
) -> dict[str, dict[str, Any]]:
    library = _read(root / "institutional_learning" / "strategy_moves" / "latest.json")
    admitted = {
        str(row.get("mechanism_phenotype_sha256"))
        for row in library.get("mechanism_phenotypes") or ()
        if isinstance(row, dict)
        and int(row.get("exact_adoption_count") or 0) > 0
        and entity_id in {str(value) for value in row.get("entity_ids") or ()}
    }
    discovery = _read(root / "discovery" / "latest.json")
    candidates, ambiguous_entities = unique_current_candidates_by_entity(
        discovery.get("candidates") or (),
    )
    if entity_id in ambiguous_entities:
        raise ValueError("strategy-alpha entity has ambiguous current candidates")
    candidate_id = str((candidates.get(entity_id) or {}).get("candidate_id") or "")
    compatible_requests = compatible_strategy_source_request_sha256s(
        root, candidate_id=candidate_id, candidate_leaf=candidate_leaf,
        candidate_sha256=candidate_sha256,
    ) | covered_strategy_source_request_sha256s(
        root, candidate_leaf=candidate_leaf,
    )
    grouped: dict[str, dict[str, Any]] = {}
    for move in library.get("moves") or ():
        if (
            not isinstance(move, dict)
            or str(move.get("entity_id") or "") != entity_id
            or (
                as_of is not None
                and timestamp_key(canonical_timestamp(
                    move.get("evidence_epoch"), "move.evidence_epoch",
                )) > timestamp_key(canonical_timestamp(as_of, "strategy evidence as_of"))
            )
            or strategy_choice_admission_status(library, move, as_of=as_of) is None
            or not candidate_bound_strategy_move(
                move, candidate_leaf=candidate_leaf, candidate_sha256=candidate_sha256,
                compatible_source_request_sha256s=compatible_requests,
            )
        ):
            continue
        phenotype_sha = str(move.get("mechanism_phenotype_sha256") or "")
        event = dict(move.get("implementation_event") or {})
        if (
            phenotype_sha not in admitted
            or event.get("treatment_timing_status") != "exact_adoption_event"
            or not _valid_hash(event, "implementation_event_sha256")
            or not event.get("source_refs")
        ):
            continue
        row = grouped.setdefault(phenotype_sha, {
            "phenotype_sha256": phenotype_sha,
            "available_at": str(event.get("available_at") or ""),
            "source_refs": set(),
            "implementation_event_sha256s": [],
            "exact_events": [],
        })
        if timestamp_key(canonical_timestamp(event.get("available_at"), "event.available_at")) > timestamp_key(
            canonical_timestamp(row["available_at"], "phenotype.available_at")
        ):
            row["available_at"] = str(event["available_at"])
        row["source_refs"].update(
            str(value) for value in (
                *(event.get("source_refs") or ()), *(move.get("evidence_refs") or ()),
            )
        )
        row["implementation_event_sha256s"].append(str(event.get("implementation_event_sha256") or ""))
        row["exact_events"].append({
            "move_sha256": str(move.get("move_sha256") or ""),
            "option_id": move.get("option_id"),
            "mechanism": dict(move.get("mechanism") or {}),
            "move_evidence_refs": list(move.get("evidence_refs") or ()),
            "implementation_event_sha256": str(event.get("implementation_event_sha256") or ""),
            "strategy_choice_identity_sha256": str(
                move.get("strategy_choice_identity_sha256") or ""
            ),
            "choice_identity_status": strategy_choice_admission_status(
                library, move, as_of=as_of,
            ),
            "candidate_leaf": candidate_leaf,
            "candidate_sha256": candidate_sha256,
            "candidate_epoch_relation": (
                "exact_market_epoch"
                if move.get("candidate_leaf") == candidate_leaf
                and move.get("candidate_sha256") == candidate_sha256
                else "qualitative_business_basis_compatible"
            ),
            "available_at": str(event.get("available_at") or ""),
            "source_refs": sorted({
                *(str(value) for value in event.get("source_refs") or ()),
                *(str(value) for value in move.get("evidence_refs") or ()),
            }),
            "strategy_program_attribution": dict(
                move.get("strategy_program_attribution") or {}
            ),
            "outcome_contracts": sorted(
                (dict(contract)
                for contract in move.get("outcome_contracts") or ()
                if isinstance(contract, Mapping) and contract.get("contract_sha256")),
                key=lambda contract: str(contract["contract_sha256"]),
            ),
        })
    return {
        key: {
            **value,
            "source_refs": sorted(value["source_refs"]),
            "implementation_event_sha256s": sorted(value["implementation_event_sha256s"]),
            "exact_events": sorted(
                value["exact_events"],
                key=lambda row: (row["move_sha256"], row["implementation_event_sha256"]),
            ),
        }
        for key, value in grouped.items()
    }


def compile_strategy_alpha_action_request(
    root: Path, nomination: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the exact move and current numeric evidence before agent forecasting."""
    if (
        nomination.get("schema") != "jaggedthoughts-strategy-alpha-episode-nomination-v1"
        or not _valid_hash(nomination, "nomination_sha256")
    ):
        raise ValueError("strategy-alpha nomination schema or hash is invalid")
    dual = dict(nomination.get("dual_outcome_contract") or {})
    if (
        dual.get("schema") != "jaggedthoughts-strategy-dual-outcome-contract-v1"
        or not _valid_hash(dual, "dual_outcome_contract_sha256")
    ):
        raise ValueError("strategy-alpha dual-outcome contract is invalid")
    created_at = canonical_timestamp(nomination.get("nominated_at"), "nomination.nominated_at")
    entity_id = require_text(nomination.get("entity_id"), "nomination.entity_id").upper()
    candidate_leaf = require_text(nomination.get("candidate_leaf"), "nomination.candidate_leaf")
    discovery = _read(root / "discovery" / "latest.json")
    record = _read(root / "discovery" / "latest_record.json")
    if (
        not _valid_hash(discovery, "run_sha256")
        or record.get("run_id") != discovery.get("run_id")
        or record.get("run_sha256") != discovery.get("run_sha256")
    ):
        raise ValueError("strategy-alpha discovery identity is invalid")
    _, ambiguous_entities = unique_current_candidates_by_entity(
        discovery.get("candidates") or (),
    )
    if entity_id in ambiguous_entities:
        raise ValueError("strategy-alpha entity has ambiguous current candidates")
    candidate_matches = [
        dict(row) for row in discovery.get("candidates") or ()
        if isinstance(row, Mapping)
        and str(row.get("candidate_id") or "") == str(nomination.get("candidate_id") or "")
        and str(row.get("candidate_sha256") or "") == str(nomination.get("candidate_sha256") or "")
        and str(row.get("entity_id") or "").upper() == entity_id
    ]
    candidate = candidate_matches[0] if len(candidate_matches) == 1 else None
    recorded_leaf = str((record.get("candidate_leaves") or {}).get(
        str(nomination.get("candidate_id") or ""),
    ) or "")
    if (
        candidate is None
        or candidate.get("screen_status") not in {"qualified", "monitor"}
        or not _valid_hash(candidate, "candidate_sha256")
        or not _is_sha(recorded_leaf)
        or candidate_leaf != recorded_leaf
    ):
        raise ValueError("strategy-alpha nomination is not current in discovery")
    phenotype_sha = require_text(
        dual.get("mechanism_phenotype_sha256"), "dual mechanism phenotype",
    )
    choice_sha = _sha256(
        dual.get("strategy_choice_identity_sha256"), "dual strategy choice identity",
    )
    move_sha = require_text(dual.get("move_sha256"), "dual move_sha256")
    event_sha = require_text(
        dual.get("implementation_event_sha256"), "dual implementation_event_sha256",
    )
    exact = _exact_phenotypes(
        root, entity_id, candidate_leaf=candidate_leaf,
        candidate_sha256=str(candidate["candidate_sha256"]),
        as_of=created_at,
    ).get(phenotype_sha) or {}
    event = next((
        row for row in exact.get("exact_events") or ()
        if row.get("move_sha256") == move_sha
        and row.get("implementation_event_sha256") == event_sha
    ), None)
    if event is None:
        raise ValueError("strategy-alpha nomination does not bind an admitted exact move event")
    if event.get("strategy_choice_identity_sha256") != choice_sha:
        raise ValueError("strategy-alpha nomination does not bind the current stable choice identity")
    operating = dict(dual.get("operating_outcome") or {})
    source_contract = next((
        contract for contract in event.get("outcome_contracts") or ()
        if str(contract.get("contract_sha256") or "")
        == str(operating.get("contract_sha256") or "")
    ), None)
    expected_operating = {
        key: source_contract.get(key) for key in (
            "contract_sha256", "metric_id", "unit", "direction", "minimum_effect",
            "comparator", "measurement_start_at", "due_at",
        )
    } if source_contract else None
    if source_contract is None or operating != expected_operating:
        raise ValueError("strategy-alpha operating contract does not belong to the exact move")
    security = dict(dual.get("security_outcome") or {})
    horizon_days = int(nomination.get("horizon_days") or 0)
    expected_dual_identity = {
        "entity_id": entity_id,
        "candidate_leaf": candidate_leaf,
        "candidate_sha256": str(candidate["candidate_sha256"]),
        "move_sha256": move_sha,
        "strategy_choice_identity_sha256": choice_sha,
        "mechanism_phenotype_sha256": phenotype_sha,
        "implementation_event_sha256": event_sha,
        "implementation_available_at": str(event.get("available_at") or ""),
    }
    if any(str(dual.get(key) or "") != value for key, value in expected_dual_identity.items()):
        raise ValueError("strategy-alpha dual contract crossed a frozen identity")
    if (
        int(security.get("horizon_days") or 0) != horizon_days
        or list(nomination.get("mechanism_phenotype_sha256s") or ()) != [phenotype_sha]
        or list(nomination.get("implementation_event_sha256s") or ()) != [event_sha]
        or canonical_timestamp(dual.get("frozen_at"), "dual.frozen_at") != created_at
    ):
        raise ValueError("strategy-alpha dual contract crossed its frozen horizon")
    if dict(dual.get("strategy_program_attribution") or {}) != dict(
        event.get("strategy_program_attribution") or {}
    ):
        raise ValueError("strategy-alpha nomination crossed strategy-program attribution")
    quality = _read(root / "quality" / f"{entity_id.lower()}.json")
    if str(quality.get("quality_report_sha256") or "") != str(
        candidate.get("quality_report_sha256") or ""
    ):
        raise ValueError("strategy-alpha request quality evidence is not current")
    for value, label in (
        (candidate.get("as_of"), "candidate as_of"),
        (quality.get("available_at") or quality.get("as_of"), "quality available_at"),
        (event.get("available_at"), "event available_at"),
        (dual.get("implementation_available_at"), "dual implementation_available_at"),
        (dual.get("frozen_at"), "dual frozen_at"),
    ):
        if timestamp_key(canonical_timestamp(value, label)) > timestamp_key(created_at):
            raise ValueError(f"strategy-alpha request includes post-nomination evidence: {label}")
    residual = compile_direct_strategy_expectation_residual(
        root,
        candidate=candidate,
        quality=quality,
        dual_outcome_contract=dual,
        horizon_days=int(nomination["horizon_days"]),
    )
    evidence = {
        "candidate": {
            key: candidate.get(key) for key in (
                "candidate_id", "candidate_sha256", "entity_id", "as_of", "metrics",
                "source_refs", "valuation", "quality_report_sha256",
            )
        },
        "quality": {
            key: quality.get(key) for key in (
                "quality_report_sha256", "as_of", "available_at", "metrics", "scores",
                "source_refs",
            )
        },
        "exact_move_event": event,
        "dual_outcome_contract": dual,
        "strategy_expectation_residual": residual,
    }
    body = {
        "schema": STRATEGY_ALPHA_ACTION_REQUEST_SCHEMA,
        "request_id": f"strategy-alpha-action:{str(nomination['nomination_sha256'])[:24]}",
        "created_at": created_at, "entity_id": entity_id,
        "subject_id": str(nomination["candidate_id"]),
        "candidate_leaf": candidate_leaf,
        "candidate_sha256": str(candidate["candidate_sha256"]),
        "horizon_days": int(nomination["horizon_days"]),
        "nomination_sha256": str(nomination["nomination_sha256"]),
        "dual_outcome_contract_sha256": str(dual["dual_outcome_contract_sha256"]),
        "phenotype_sha256": phenotype_sha, "move_sha256": move_sha,
        "strategy_choice_identity_sha256": choice_sha,
        "implementation_event_sha256": event_sha,
        "evidence": evidence,
        "required_arms": ["valuation", "durability", "strategy"],
        "target_weight": 0.0,
        "expected_exit": (
            "two_deterministic_controls_plus_one_masked_operating_hurdle_"
            "probability_or_typed_failure"
        ),
        "issuance_contract_version": "subscription-result-provenance-v1",
        "capital_authority": False,
    }
    return _hashed(body, "request_sha256")


def compile_strategy_alpha_issuance_action(
    proposal: Mapping[str, Any], request: Mapping[str, Any], *,
    available_at: str, ttl_hours: int = 24,
) -> dict[str, Any]:
    """Validate subscription output and lower it into the only binding action type."""
    if (
        request.get("schema") != STRATEGY_ALPHA_ACTION_REQUEST_SCHEMA
        or not _valid_hash(request, "request_sha256")
    ):
        raise ValueError("strategy-alpha action request is invalid")
    if proposal.get("schema") != STRATEGY_ALPHA_ACTION_PROPOSAL_SCHEMA:
        raise ValueError("strategy-alpha action proposal schema is invalid")
    for field in (
        "request_sha256", "nomination_sha256", "dual_outcome_contract_sha256",
        "candidate_leaf", "phenotype_sha256", "move_sha256",
        "implementation_event_sha256", "strategy_choice_identity_sha256",
    ):
        if str(proposal.get(field) or "") != str(request.get(field) or ""):
            raise ValueError(f"strategy-alpha proposal differs from request identity: {field}")
    isolation = proposal.get("arm_isolation")
    if not isinstance(isolation, Mapping) or isolation.get("schema") != STRATEGY_ALPHA_ARM_ISOLATION_SCHEMA:
        raise ValueError("strategy-alpha proposal lacks a typed arm-isolation receipt")
    if not _valid_hash(isolation, "isolation_sha256"):
        raise ValueError("strategy-alpha arm-isolation receipt hash is invalid")
    procedure = proposal.get("strategy_procedure")
    if (
        not isinstance(procedure, Mapping)
        or procedure.get("schema") != STRATEGY_ALPHA_PROCEDURE_SCHEMA
        or not _valid_hash(procedure, "procedure_sha256")
        or procedure.get("web_research") is not False
        or "valuation, payoff, and security control excluded"
        not in str(procedure.get("target_masking") or "")
    ):
        raise ValueError("strategy-alpha proposal lacks a valid target-blind procedure")
    provider_result = proposal.get("strategy_provider_result")
    provenance = proposal.get("provider_result_provenance")
    if (
        not isinstance(provider_result, Mapping)
        or provider_result.get("schema")
        != "jaggedthoughts-strategy-alpha-arm-proposal-v1"
        or provider_result.get("role") != "strategy"
        or not isinstance(provenance, Mapping)
        or provenance.get("schema")
        != "jaggedthoughts-subscription-result-provenance-v1"
        or not _valid_hash(provenance, "provenance_sha256")
        or provenance.get("result_sha256") != stable_sha256(provider_result)
        or provenance.get("procedure_sha256") != procedure.get("procedure_sha256")
    ):
        raise ValueError("strategy-alpha proposal lacks subscription result provenance")
    views = compile_strategy_alpha_arm_views(request)
    expected_view_shas = {
        role: view["arm_view_sha256"] for role, view in views.items()
    }
    if isolation.get("generation_mode") != "deterministic_controls_plus_masked_strategy_probability":
        raise ValueError("strategy-alpha action used an unsupported generation mode")
    if dict(isolation.get("arm_view_sha256s") or {}) != expected_view_shas:
        raise ValueError("strategy-alpha arm-isolation view identities do not match")
    generated_at = canonical_timestamp(available_at, "strategy-alpha action available_at")
    if timestamp_key(generated_at) < timestamp_key(str(request["created_at"])):
        raise ValueError("strategy-alpha action cannot precede its request")
    if ttl_hours <= 0:
        raise ValueError("strategy-alpha action ttl_hours must be positive")
    expires_at = (
        timestamp_key(generated_at) + timedelta(hours=ttl_hours)
    ).astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    evidence = dict(request["evidence"])
    candidate_refs = set(require_refs(
        (evidence.get("candidate") or {}).get("source_refs") or (), "candidate source ref",
    ))
    quality_refs = set(require_refs(
        (evidence.get("quality") or {}).get("source_refs") or (), "quality source ref",
    ))
    event_refs = set(require_refs(
        (evidence.get("exact_move_event") or {}).get("source_refs") or (), "event source ref",
    ))
    residual_refs = set(require_refs(
        (evidence.get("strategy_expectation_residual") or {}).get("source_refs") or (),
        "strategy expectation residual source ref",
    ))
    support_refs = {
        "valuation": set(candidate_refs),
        "durability": set(candidate_refs) | set(quality_refs),
        "strategy": (
            set(candidate_refs) | set(quality_refs) | set(event_refs) | set(residual_refs)
        ),
    }
    sources = [
        {
            "source_ref": source_ref,
            "supports": sorted(
                role for role, refs in support_refs.items() if source_ref in refs
            ),
        }
        for source_ref in sorted(set().union(*support_refs.values()))
    ]
    raw_arms = {
        str(row.get("role") or ""): row
        for row in proposal.get("arms") or () if isinstance(row, Mapping)
    }
    if set(raw_arms) != set(request["required_arms"]):
        raise ValueError("strategy-alpha proposal requires exactly three typed arms")
    deterministic = compile_strategy_alpha_deterministic_controls(request)
    residual = dict(evidence.get("strategy_expectation_residual") or {})
    strategy_probability = require_finite(
        raw_arms["strategy"].get("operating_hurdle_probability"),
        "strategy operating-hurdle probability",
    )
    if (
        require_finite(
            provider_result.get("operating_hurdle_probability"),
            "provider operating-hurdle probability",
        ) != strategy_probability
        or provider_result.get("arm_view_sha256")
        != (isolation.get("arm_view_sha256s") or {}).get("strategy")
    ):
        raise ValueError("strategy-alpha strategy arm differs from its provider result")
    if not 0 <= strategy_probability <= 1:
        raise ValueError("strategy operating-hurdle probability must be in [0, 1]")
    expected_values = {
        role: float(row["predicted_active_return"])
        for role, row in deterministic.items()
    }
    expected_values["strategy"] = expected_values["durability"] + strategy_probability * require_finite(
        residual.get("incremental_horizon_payoff"), "strategy incremental horizon payoff",
    )
    mechanisms = {
        "valuation": ["price_implied_expectations"],
        "durability": ["price_implied_expectations", _DURABILITY],
        "strategy": [
            "price_implied_expectations", _DURABILITY, _STRATEGY, _TYPED_RESIDUAL,
        ],
    }
    arms = []
    for role in request["required_arms"]:
        row = raw_arms[role]
        predicted = expected_values[role]
        if role != "strategy":
            for key in ("predicted_active_return", "underperformance_probability"):
                if abs(require_finite(row.get(key), f"{role} {key}") - float(
                    deterministic[role][key]
                )) > 1e-12:
                    raise ValueError(f"{role} control differs from its deterministic program")
        probability = _underperformance_probability(predicted, int(request["horizon_days"]))
        if not -1 <= predicted <= 3 or not 0 <= probability <= 1:
            raise ValueError(f"{role} forecast is outside the declared numeric range")
        refs = support_refs[role]
        explanation = row.get("explanation")
        if not isinstance(explanation, Mapping):
            raise ValueError(f"{role} explanation must be an object")
        arms.append({
            "candidate_id": f"strategy-alpha-{role}:{str(request['request_sha256'])[:16]}",
            "mechanism_ids": mechanisms[role],
            "predicted_active_return": predicted,
            "underperformance_probability": probability,
            "target_weight": 0.0, "source_refs": sorted(refs),
            "explanation": {
                **dict(explanation),
                **({"operating_hurdle_probability": strategy_probability}
                   if role == "strategy" else {}),
            },
        })
    information_set_sha = stable_sha256({
        "request_sha256": request["request_sha256"], "available_at": generated_at,
        "sources": sources,
        "arm_source_refs": {role: sorted(support_refs[role]) for role in support_refs},
    })
    body = {
        "schema": STRATEGY_ALPHA_ISSUANCE_ACTION_SCHEMA,
        "action_id": f"strategy-alpha-action:{str(request['request_sha256'])[:24]}",
        "entity_id": request["entity_id"], "subject_id": request["subject_id"],
        "horizon_days": request["horizon_days"],
        "request_sha256": request["request_sha256"],
        "nomination_sha256": request["nomination_sha256"],
        "dual_outcome_contract_sha256": request["dual_outcome_contract_sha256"],
        "candidate_leaf": request["candidate_leaf"],
        "phenotype_sha256": request["phenotype_sha256"],
        "move_sha256": request["move_sha256"],
        "strategy_choice_identity_sha256": request["strategy_choice_identity_sha256"],
        "implementation_event_sha256": request["implementation_event_sha256"],
        "request_created_at": request["created_at"],
        "available_at": generated_at, "expires_at": expires_at,
        "information_set_sha256": information_set_sha,
        "arm_isolation": dict(isolation),
        "strategy_expectation_residual": residual,
        "strategy_procedure": dict(procedure),
        "strategy_provider_result": dict(provider_result),
        "provider_result_provenance": dict(provenance),
        "operating_hurdle_forecast": {
            "operating_contract_sha256": residual["operating_contract_sha256"],
            "probability": strategy_probability,
        },
        "public_sources": sources,
        "durability_evidence": {
            "available_at": generated_at,
            "source_refs": sorted(quality_refs | support_refs["durability"]),
        },
        "arms": arms, "capital_authority": False,
    }
    return _hashed(body, "action_sha256")


def _role(candidate: Mapping[str, Any]) -> str | None:
    mechanisms = {str(value) for value in candidate.get("mechanism_ids") or ()}
    if {_DURABILITY, _STRATEGY, _TYPED_RESIDUAL} <= mechanisms and mechanisms & _VALUATION:
        return "strategy"
    if (
        _DURABILITY in mechanisms and _STRATEGY not in mechanisms
        and _TYPED_RESIDUAL not in mechanisms and mechanisms & _VALUATION
    ):
        return "durability"
    if (
        mechanisms & _VALUATION and _DURABILITY not in mechanisms
        and _STRATEGY not in mechanisms and _TYPED_RESIDUAL not in mechanisms
    ):
        return "valuation"
    return None


def _action_forecasts(
    action: Mapping[str, Any],
    *,
    packet: Mapping[str, Any],
    opened_at: str,
    phenotype: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    if action.get("schema") != STRATEGY_ALPHA_ISSUANCE_ACTION_SCHEMA or not _valid_hash(
        action, "action_sha256"
    ):
        raise ValueError("strategy-alpha action schema or hash is invalid")
    if action.get("capital_authority") is not False:
        raise ValueError("strategy-alpha action must deny capital authority")
    isolation = action.get("arm_isolation")
    if (
        not isinstance(isolation, Mapping)
        or isolation.get("schema") != STRATEGY_ALPHA_ARM_ISOLATION_SCHEMA
        or not _valid_hash(isolation, "isolation_sha256")
    ):
        raise ValueError("strategy-alpha action lacks a valid arm-isolation receipt")
    view_shas = dict(isolation.get("arm_view_sha256s") or {})
    if set(view_shas) != {"valuation", "durability", "strategy"}:
        raise ValueError("strategy-alpha action lacks all isolated arm views")
    residual = action.get("strategy_expectation_residual")
    if (
        not isinstance(residual, Mapping)
        or residual.get("schema")
        != "jaggedthoughts-direct-strategy-expectation-residual-v1"
        or not _valid_hash(residual, "residual_sha256")
        or residual.get("status") != "compiled"
    ):
        raise ValueError("strategy-alpha action lacks a typed expectation residual")
    procedure = action.get("strategy_procedure")
    if (
        not isinstance(procedure, Mapping)
        or procedure.get("schema") != STRATEGY_ALPHA_PROCEDURE_SCHEMA
        or not _valid_hash(procedure, "procedure_sha256")
    ):
        raise ValueError("strategy-alpha action lacks a frozen procedure identity")
    hurdle_forecast = dict(action.get("operating_hurdle_forecast") or {})
    hurdle_probability = require_finite(
        hurdle_forecast.get("probability"), "operating hurdle probability",
    )
    if (
        not 0 <= hurdle_probability <= 1
        or hurdle_forecast.get("operating_contract_sha256")
        != residual.get("operating_contract_sha256")
    ):
        raise ValueError("strategy-alpha action has an invalid operating-hurdle forecast")
    nomination = dict((packet.get("discovery_summary") or {}).get(
        "strategy_experiment_nomination"
    ) or {})
    dual = dict(nomination.get("dual_outcome_contract") or {})
    if (
        nomination.get("schema") != "jaggedthoughts-strategy-alpha-episode-nomination-v1"
        or not _valid_hash(nomination, "nomination_sha256")
        or dual.get("schema") != "jaggedthoughts-strategy-dual-outcome-contract-v1"
        or not _valid_hash(dual, "dual_outcome_contract_sha256")
    ):
        raise ValueError("strategy-alpha action targets an invalid frozen nomination")
    expected_identity = {
        "nomination_sha256": nomination.get("nomination_sha256"),
        "dual_outcome_contract_sha256": dual.get("dual_outcome_contract_sha256"),
        "candidate_leaf": nomination.get("candidate_leaf"),
        "phenotype_sha256": dual.get("mechanism_phenotype_sha256"),
        "move_sha256": dual.get("move_sha256"),
        "strategy_choice_identity_sha256": dual.get(
            "strategy_choice_identity_sha256"
        ),
        "implementation_event_sha256": dual.get("implementation_event_sha256"),
    }
    for field, expected in expected_identity.items():
        if not expected or str(action.get(field) or "") != str(expected):
            raise ValueError(f"strategy-alpha action differs from frozen nomination: {field}")
    if (
        residual.get("dual_outcome_contract_sha256")
        != dual.get("dual_outcome_contract_sha256")
        or residual.get("move_sha256") != dual.get("move_sha256")
        or residual.get("strategy_choice_identity_sha256")
        != dual.get("strategy_choice_identity_sha256")
    ):
        raise ValueError("strategy-alpha expectation residual crossed the frozen nomination")
    available_at = canonical_timestamp(action.get("available_at"), "action.available_at")
    expires_at = canonical_timestamp(action.get("expires_at"), "action.expires_at")
    request_created_at = canonical_timestamp(
        action.get("request_created_at"), "action.request_created_at",
    )
    opened_key = timestamp_key(canonical_timestamp(opened_at, "opened_at"))
    if not timestamp_key(request_created_at) <= timestamp_key(available_at) <= opened_key <= timestamp_key(expires_at):
        raise ValueError("strategy-alpha action is not valid at issuance")
    durability = action.get("durability_evidence")
    if not isinstance(durability, Mapping):
        raise ValueError("strategy-alpha durability_evidence must be an object")
    durability_available_at = canonical_timestamp(
        durability.get("available_at"), "durability_evidence.available_at",
    )
    if timestamp_key(durability_available_at) > opened_key:
        raise ValueError("durability evidence was unavailable at issuance")
    durability_refs = set(require_refs(
        durability.get("source_refs") or (), "durability evidence source ref",
    ))
    phenotype_refs = set(require_refs(
        phenotype.get("source_refs") or (), "phenotype source ref",
    ))
    information_sha = require_text(
        action.get("information_set_sha256"), "action.information_set_sha256",
    )
    if not _is_sha(information_sha):
        raise ValueError("strategy-alpha action information set is not a SHA-256 digest")
    information_ref = f"information-set:{information_sha}"
    roles: dict[str, dict[str, Any]] = {}
    for arm in action.get("arms") or ():
        if not isinstance(arm, Mapping):
            raise ValueError("strategy-alpha action arms must be objects")
        role = _role(arm)
        if role is None or role in roles:
            raise ValueError("strategy-alpha action must contain one arm for each typed role")
        active_return = require_finite(
            arm.get("predicted_active_return"), f"{role}.predicted_active_return",
        )
        underperformance = require_finite(
            arm.get("underperformance_probability"),
            f"{role}.underperformance_probability",
        )
        weight = require_finite(arm.get("target_weight"), f"{role}.target_weight")
        if not -1 <= active_return <= 3:
            raise ValueError(f"{role} predicted active return is outside [-1, 3]")
        if not 0 <= underperformance <= 1 or not 0 <= weight <= 1:
            raise ValueError(f"{role} probability and weight must be in [0, 1]")
        source_refs = set(require_refs(arm.get("source_refs") or (), f"{role} source ref"))
        if role == "strategy":
            source_refs |= durability_refs
        if role in {"durability", "strategy"} and not durability_refs <= source_refs:
            raise ValueError(f"{role} arm does not cite all durability evidence")
        if role == "strategy" and not phenotype_refs <= source_refs:
            raise ValueError("strategy arm does not cite all phenotype evidence")
        explanation = arm.get("explanation")
        if not isinstance(explanation, Mapping):
            raise ValueError(f"{role}.explanation must be an object")
        if explanation.get("arm_view_sha256") != view_shas[role]:
            raise ValueError(f"{role} forecast does not bind its masked arm view")
        body = {
            "schema": "jaggedthoughts-closed-book-candidate-forecast-v1",
            "candidate_id": require_text(arm.get("candidate_id"), f"{role}.candidate_id"),
            "version": "1",
            "model_family": "strategy_alpha_issuance_action",
            "trial_family_id": f"strategy-alpha-{role}-v1",
            "mechanism_ids": list(arm.get("mechanism_ids") or ()),
            "predicted_values": {
                "active_return": active_return,
                "underperformance_event": underperformance,
                **(
                    {"operating_hurdle_event": hurdle_probability}
                    if role == "strategy" else {}
                ),
            },
            "target_weight": weight,
            "source_refs": sorted(source_refs | {
                information_ref, f"arm-view:{view_shas[role]}",
                *(
                    [f"strategy-residual:{residual['residual_sha256']}"]
                    if role == "strategy" else []
                ),
            }),
            "generated_at": available_at,
            "producer": {
                "mode": "typed_issuance_action",
                "action_id": require_text(action.get("action_id"), "action.action_id"),
                "action_sha256": str(action["action_sha256"]),
                "arm_isolation_sha256": isolation["isolation_sha256"],
                "arm_view_sha256": view_shas[role],
                "forecast_process": (
                    "masked_operating_hurdle_probability"
                    if role == "strategy" else "deterministic_program"
                ),
                "strategy_expectation_residual_sha256": (
                    residual["residual_sha256"] if role == "strategy" else None
                ),
                "strategy_translation_kind": (
                    (residual.get("translation") or {}).get("kind")
                    if role == "strategy" else None
                ),
                "strategy_causal_effect_earned": (
                    bool((residual.get("translation") or {}).get("causal_effect_earned"))
                    if role == "strategy" else False
                ),
                "strategy_procedure_sha256": procedure["procedure_sha256"],
            },
            "explanation": dict(explanation),
        }
        roles[role] = _hashed(body, "forecast_sha256")
    if set(roles) != {"valuation", "durability", "strategy"}:
        raise ValueError("strategy-alpha action must contain valuation, durability, and strategy arms")
    return tuple(roles[role] for role in ("valuation", "durability", "strategy"))


def _action_matches_persisted_request(root: Path, action: Mapping[str, Any]) -> bool:
    """Recompute every numeric action field from its persisted request."""

    try:
        request_sha = _sha256(action.get("request_sha256"), "action request_sha256")
        request = _read(
            root / "closed_book" / "strategy_alpha_action_requests" / f"{request_sha}.json"
        )
        if (
            request.get("schema") != STRATEGY_ALPHA_ACTION_REQUEST_SCHEMA
            or not _valid_hash(request, "request_sha256")
            or request["request_sha256"] != request_sha
        ):
            return False
        for field in (
            "entity_id", "subject_id", "horizon_days", "nomination_sha256",
            "dual_outcome_contract_sha256", "candidate_leaf", "phenotype_sha256",
            "move_sha256", "strategy_choice_identity_sha256",
            "implementation_event_sha256",
        ):
            if str(action.get(field) or "") != str(request.get(field) or ""):
                return False
        residual = dict((request.get("evidence") or {}).get(
            "strategy_expectation_residual"
        ) or {})
        if dict(action.get("strategy_expectation_residual") or {}) != residual:
            return False
        views = compile_strategy_alpha_arm_views(request)
        isolation = dict(action.get("arm_isolation") or {})
        if (
            isolation.get("generation_mode")
            != "deterministic_controls_plus_masked_strategy_probability"
            or dict(isolation.get("arm_view_sha256s") or {}) != {
                role: view["arm_view_sha256"] for role, view in views.items()
            }
        ):
            return False
        procedure = dict(action.get("strategy_procedure") or {})
        if (
            procedure.get("schema") != STRATEGY_ALPHA_PROCEDURE_SCHEMA
            or not _valid_hash(procedure, "procedure_sha256")
        ):
            return False
        provider_result = dict(action.get("strategy_provider_result") or {})
        provenance = dict(action.get("provider_result_provenance") or {})
        if (
            provider_result.get("schema")
            != "jaggedthoughts-strategy-alpha-arm-proposal-v1"
            or provider_result.get("role") != "strategy"
            or provenance.get("schema")
            != "jaggedthoughts-subscription-result-provenance-v1"
            or not _valid_hash(provenance, "provenance_sha256")
            or provenance.get("result_sha256") != stable_sha256(provider_result)
            or provenance.get("procedure_sha256") != procedure.get("procedure_sha256")
        ):
            return False
        for path_field, sha_field in (
            ("result_path", "result_sha256"),
            ("call_receipt_path", "call_receipt_sha256"),
            ("dispatch_receipt_path", "dispatch_receipt_sha256"),
        ):
            artifact_path = (root / require_text(
                provenance.get(path_field), f"provider {path_field}",
            )).resolve()
            artifact_path.relative_to(root.resolve())
            artifact = _read(artifact_path)
            if stable_sha256(artifact) != provenance.get(sha_field):
                return False
        if _read((root / str(provenance["result_path"])).resolve()) != provider_result:
            return False
        controls = compile_strategy_alpha_deterministic_controls(request)
        arms = {_role(row): row for row in action.get("arms") or () if isinstance(row, Mapping)}
        if set(arms) != {"valuation", "durability", "strategy"}:
            return False
        hurdle = dict(action.get("operating_hurdle_forecast") or {})
        probability = require_finite(hurdle.get("probability"), "hurdle probability")
        if (
            not 0 <= probability <= 1
            or require_finite(
                provider_result.get("operating_hurdle_probability"),
                "provider hurdle probability",
            ) != probability
        ):
            return False
        expected = {
            role: float(row["predicted_active_return"])
            for role, row in controls.items()
        }
        expected["strategy"] = expected["durability"] + probability * require_finite(
            residual.get("incremental_horizon_payoff"), "incremental horizon payoff",
        )
        for role, row in arms.items():
            if abs(require_finite(
                row.get("predicted_active_return"),
                f"{role} active return",
            ) - expected[role]) > 1e-12:
                return False
            if abs(require_finite(
                row.get("underperformance_probability"),
                f"{role} underperformance probability",
            ) - _underperformance_probability(
                expected[role], int(action.get("horizon_days") or 0),
            )) > 1e-12:
                return False
            if role == "strategy" and abs(require_finite(
                (row.get("explanation") or {}).get("operating_hurdle_probability"),
                "strategy hurdle probability",
            ) - probability) > 1e-12:
                return False
        return True
    except (OSError, TypeError, ValueError):
        return False


def _eligible_actions(
    root: Path, *, entity_id: str, subject_id: str, horizon_days: int,
    nomination: Mapping[str, Any], opened_at: str,
) -> list[dict[str, Any]]:
    dual = dict(nomination.get("dual_outcome_contract") or {})
    exact = {
        "nomination_sha256": nomination.get("nomination_sha256"),
        "dual_outcome_contract_sha256": dual.get("dual_outcome_contract_sha256"),
        "candidate_leaf": nomination.get("candidate_leaf"),
        "phenotype_sha256": dual.get("mechanism_phenotype_sha256"),
        "move_sha256": dual.get("move_sha256"),
        "strategy_choice_identity_sha256": dual.get(
            "strategy_choice_identity_sha256"
        ),
        "implementation_event_sha256": dual.get("implementation_event_sha256"),
    }
    eligible = []
    for path in sorted((root / "closed_book" / "strategy_alpha_actions").glob("*.json")):
        try:
            action = _read(path)
            if (
                action.get("schema") == STRATEGY_ALPHA_ISSUANCE_ACTION_SCHEMA
                and _valid_hash(action, "action_sha256")
                and str(action.get("entity_id") or "") == entity_id
                and str(action.get("subject_id") or "") == subject_id
                and int(action.get("horizon_days") or 0) == horizon_days
                and all(str(action.get(field) or "") == str(value or "")
                        for field, value in exact.items())
                and timestamp_key(canonical_timestamp(action.get("available_at"), "action.available_at"))
                <= timestamp_key(canonical_timestamp(opened_at, "opened_at"))
                <= timestamp_key(canonical_timestamp(action.get("expires_at"), "action.expires_at"))
                and _action_matches_persisted_request(root, action)
            ):
                eligible.append(action)
        except (OSError, TypeError, ValueError):
            continue
    return eligible


def _write_status(root: Path, run_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    status = _hashed(payload, "activation_status_sha256")
    path = root / "closed_book" / "strategy_alpha_activation_status" / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return {**status, "status_path": path.relative_to(root).as_posix()}


def compile_strategy_alpha_binding_proposal(
    root: Path,
    run_id: str,
    *,
    candidate_forecasts: tuple[Mapping[str, Any], ...] | None = None,
    phenotype_sha256: str | None = None,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Compile a binding proposal; expected missing inputs become hashed gaps."""

    run_id = require_text(run_id, "run_id")
    checked_at = canonical_timestamp(evaluated_at or _now(), "evaluated_at")
    gaps = []
    path = root / "closed_book" / "runs" / f"{run_id}.json"
    try:
        run = _read(path)
    except ValueError as error:
        run = {}
        gaps.append(_gap("closed_book_run_missing_or_invalid", run_id=run_id, detail=str(error)))
    if run and (run.get("schema") != "jaggedthoughts-closed-book-forecast-run-v1" or not _valid_hash(run, "run_sha256")):
        gaps.append(_gap("closed_book_run_hash_invalid", run_id=run_id))
    packet = dict(run.get("evidence_packet") or {})
    nomination = dict((packet.get("discovery_summary") or {}).get(
        "strategy_experiment_nomination"
    ) or {})
    dual = dict(nomination.get("dual_outcome_contract") or {})
    if nomination and (
        nomination.get("schema") != "jaggedthoughts-strategy-alpha-episode-nomination-v1"
        or not _valid_hash(nomination, "nomination_sha256")
        or dual.get("schema") != "jaggedthoughts-strategy-dual-outcome-contract-v1"
        or not _valid_hash(dual, "dual_outcome_contract_sha256")
    ):
        gaps.append(_gap("strategy_experiment_nomination_hash_invalid", run_id=run_id))
    entity_id = str((packet.get("entity") or {}).get("entity_id") or "")
    subject_id = str((packet.get("subject") or {}).get("subject_id") or "")
    opened_at = str(run.get("opened_at") or "")
    if run and subject_id.startswith("fund:"):
        gaps.append(_gap("entity_kind_not_public_equity", run_id=run_id, entity_id=entity_id))
    if run and opened_at:
        elapsed = (timestamp_key(checked_at) - timestamp_key(canonical_timestamp(opened_at, "opened_at"))).total_seconds()
        if elapsed < 0 or elapsed > _ISSUANCE_WINDOW_SECONDS:
            gaps.append(_gap("issuance_window_closed", run_id=run_id, opened_at=opened_at, checked_at=checked_at))

    exact = {}
    if entity_id:
        try:
            exact = _exact_phenotypes(
                root, entity_id,
                candidate_leaf=str(nomination.get("candidate_leaf") or ""),
                candidate_sha256=str(nomination.get("candidate_sha256") or ""),
                as_of=opened_at,
            )
        except (OSError, ValueError) as error:
            gaps.append(_gap("exact_phenotype_evidence_unavailable", run_id=run_id, entity_id=entity_id, detail=str(error)))
    chosen_sha = str(phenotype_sha256 or dual.get("mechanism_phenotype_sha256") or "")
    if not chosen_sha:
        gaps.append(_gap(
            "exact_phenotype_missing" if not exact else "exact_phenotype_ambiguous",
            run_id=run_id, entity_id=entity_id, candidate_phenotype_sha256s=sorted(exact),
        ))
    elif chosen_sha not in exact:
        gaps.append(_gap("exact_phenotype_not_admitted", run_id=run_id, entity_id=entity_id, phenotype_sha256=chosen_sha))
    expected_move_sha = str(dual.get("move_sha256") or "")
    expected_event_sha = str(dual.get("implementation_event_sha256") or "")
    exact_event = next((
        row for row in (exact.get(chosen_sha) or {}).get("exact_events") or ()
        if row.get("move_sha256") == expected_move_sha
        and row.get("implementation_event_sha256") == expected_event_sha
    ), None)
    if run and not nomination:
        gaps.append(_gap("strategy_experiment_nomination_missing", run_id=run_id))
    elif chosen_sha and exact_event is None:
        gaps.append(_gap(
            "exact_move_event_not_admitted", run_id=run_id,
            move_sha256=expected_move_sha,
            implementation_event_sha256=expected_event_sha,
        ))
    elif opened_at and exact_event and timestamp_key(
        canonical_timestamp(exact_event["available_at"], "event.available_at")
    ) > timestamp_key(canonical_timestamp(opened_at, "opened_at")):
        gaps.append(_gap(
            "exact_phenotype_post_issue", run_id=run_id, entity_id=entity_id,
            phenotype_sha256=chosen_sha, available_at=exact_event["available_at"],
        ))

    source_candidates = tuple(candidate_forecasts or run.get("candidate_forecasts") or ())
    roles: dict[str, list[Mapping[str, Any]]] = {"valuation": [], "durability": [], "strategy": []}
    for candidate in source_candidates:
        if not isinstance(candidate, Mapping):
            continue
        role = _role(candidate)
        if role:
            roles[role].append(candidate)
    selected: dict[str, Mapping[str, Any]] = {}
    for role, rows in roles.items():
        if len(rows) != 1:
            gaps.append(_gap(
                f"{role}_forecast_{'missing' if not rows else 'ambiguous'}",
                run_id=run_id,
                candidate_ids=sorted(str(row.get("candidate_id") or "") for row in rows),
            ))
            continue
        candidate = rows[0]
        if not _valid_hash(candidate, "forecast_sha256"):
            gaps.append(_gap(f"{role}_forecast_hash_invalid", run_id=run_id))
            continue
        try:
            generated_at = canonical_timestamp(candidate.get("generated_at"), f"{role}.generated_at")
            require_finite((candidate.get("predicted_values") or {}).get("active_return"), f"{role} active return")
        except ValueError as error:
            gaps.append(_gap(f"{role}_forecast_invalid", run_id=run_id, detail=str(error)))
            continue
        if opened_at and timestamp_key(generated_at) > timestamp_key(canonical_timestamp(opened_at, "opened_at")):
            gaps.append(_gap(f"{role}_forecast_post_issue", run_id=run_id, generated_at=generated_at))
            continue
        selected[role] = candidate

    isolation_shas = {
        str((candidate.get("producer") or {}).get("arm_isolation_sha256") or "")
        for candidate in selected.values()
    }
    arm_view_shas = {
        role: str((candidate.get("producer") or {}).get("arm_view_sha256") or "")
        for role, candidate in selected.items()
    }
    if len(isolation_shas) != 1 or not next(iter(isolation_shas), ""):
        gaps.append(_gap("arm_isolation_receipt_missing_or_ambiguous", run_id=run_id))
    if set(arm_view_shas) != {"valuation", "durability", "strategy"} or any(
        not _is_sha(value) for value in arm_view_shas.values()
    ):
        gaps.append(_gap("masked_arm_view_identity_missing", run_id=run_id))
    residual_shas = {
        str((candidate.get("producer") or {}).get(
            "strategy_expectation_residual_sha256"
        ) or "")
        for role, candidate in selected.items() if role == "strategy"
    }
    if len(residual_shas) != 1 or not _is_sha(next(iter(residual_shas), "")):
        gaps.append(_gap("typed_strategy_expectation_residual_missing", run_id=run_id))
    strategy_producer = dict((selected.get("strategy") or {}).get("producer") or {})
    translation_kind = str(strategy_producer.get("strategy_translation_kind") or "")
    if translation_kind != "direct_operating_hurdle_payoff":
        gaps.append(_gap("strategy_translation_kind_unsupported", run_id=run_id))
    procedure_sha = str(strategy_producer.get("strategy_procedure_sha256") or "")
    if not _is_sha(procedure_sha):
        gaps.append(_gap("strategy_procedure_identity_missing", run_id=run_id))
    action_shas = {
        str((candidate.get("producer") or {}).get("action_sha256") or "")
        for candidate in selected.values()
    }
    if len(action_shas) != 1 or not _is_sha(next(iter(action_shas), "")):
        gaps.append(_gap("strategy_action_identity_missing_or_ambiguous", run_id=run_id))
    hurdle_probability = (selected.get("strategy") or {}).get("predicted_values", {}).get(
        "operating_hurdle_event"
    )
    try:
        hurdle_probability = require_finite(
            hurdle_probability, "strategy operating hurdle probability",
        )
        if not 0 <= hurdle_probability <= 1:
            raise ValueError("probability must be in [0, 1]")
    except ValueError as error:
        gaps.append(_gap(
            "operating_hurdle_probability_invalid", run_id=run_id, detail=str(error),
        ))

    information_refs = None
    if len(selected) == 3:
        ref_sets = [{str(value) for value in row.get("source_refs") or ()} for row in selected.values()]
        information_refs = set.intersection(*ref_sets)
        hashes = {
            value.removeprefix("information-set:") for value in information_refs
            if _is_sha(value.removeprefix("information-set:"))
        }
        if len(hashes) != 1:
            gaps.append(_gap("common_information_set_missing_or_ambiguous", run_id=run_id, common_refs=sorted(information_refs)))
        else:
            information_sha = next(iter(hashes))
            strategy_refs = {str(value) for value in selected["strategy"].get("source_refs") or ()}
            phenotype_evidence = exact_event or {}
            phenotype_refs = set(phenotype_evidence.get("source_refs") or ())
            if not phenotype_refs <= strategy_refs:
                gaps.append(_gap("strategy_forecast_missing_phenotype_sources", run_id=run_id, missing_refs=sorted(phenotype_refs - strategy_refs)))

    report = {
        "schema": "jaggedthoughts-strategy-alpha-binding-proposal-result-v1",
        "run_id": run_id,
        "evaluated_at": checked_at,
        "bindable": not gaps,
        "gaps": sorted(gaps, key=lambda row: row["code"]),
        "capital_authority": False,
    }
    if gaps:
        return _hashed(report, "proposal_result_sha256")
    phenotype = exact_event
    proposal_body = {
        "schema": STRATEGY_ALPHA_PROPOSAL_SCHEMA,
        "run_id": run_id,
        "run_sha256": run["run_sha256"],
        "packet_sha256": packet["packet_sha256"],
        "entity_id": entity_id,
        "information_set_sha256": information_sha,
        "request_frozen_at": canonical_timestamp(
            nomination.get("nominated_at"), "nomination.nominated_at",
        ),
        "bound_at": canonical_timestamp(opened_at, "opened_at"),
        "phenotype_sha256": chosen_sha,
        "phenotype_available_at": canonical_timestamp(phenotype["available_at"], "phenotype.available_at"),
        "phenotype_source_refs": require_refs(phenotype["source_refs"], "phenotype source ref"),
        "nomination_sha256": nomination["nomination_sha256"],
        "dual_outcome_contract_sha256": dual["dual_outcome_contract_sha256"],
        "candidate_leaf": nomination["candidate_leaf"],
        "move_sha256": expected_move_sha,
        "strategy_choice_identity_sha256": dual[
            "strategy_choice_identity_sha256"
        ],
        "implementation_event_sha256": expected_event_sha,
        "arm_isolation_sha256": next(iter(isolation_shas)),
        "arm_view_sha256s": arm_view_shas,
        "strategy_expectation_residual_sha256": next(iter(residual_shas)),
        "strategy_translation_kind": translation_kind,
        "strategy_causal_effect_earned": False,
        "strategy_procedure_sha256": procedure_sha,
        "operating_hurdle_probability": hurdle_probability,
        "operating_contract_sha256": dual["operating_outcome"]["contract_sha256"],
        "action_sha256": next(iter(action_shas)),
        "forecast_candidate_ids": {role: str(selected[role]["candidate_id"]) for role in roles},
        "candidate_forecasts": [dict(selected[role]) for role in roles],
        "compiled_at": checked_at,
        "capital_authority": False,
    }
    proposal = _hashed(proposal_body, "proposal_sha256")
    return _hashed({**report, "proposal": proposal}, "proposal_result_sha256")


def activate_strategy_alpha_binding(root: Path, proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Persist one validated proposal and binding without mutating the closed-book run."""

    if proposal.get("schema") != STRATEGY_ALPHA_PROPOSAL_SCHEMA or not _valid_hash(proposal, "proposal_sha256"):
        raise ValueError("strategy-alpha proposal schema or hash is invalid")
    run_id = require_text(proposal.get("run_id"), "proposal.run_id")
    run = _read(root / "closed_book" / "runs" / f"{run_id}.json")
    if str(run.get("run_sha256") or "") != str(proposal.get("run_sha256") or ""):
        raise ValueError("proposal no longer matches the closed-book run")
    packet = dict(run.get("evidence_packet") or {})
    nomination = dict((packet.get("discovery_summary") or {}).get(
        "strategy_experiment_nomination"
    ) or {})
    actions = _eligible_actions(
        root,
        entity_id=str((packet.get("entity") or {}).get("entity_id") or ""),
        subject_id=str((packet.get("subject") or {}).get("subject_id") or ""),
        horizon_days=int(run.get("horizon_days") or packet.get("horizon_days") or 0),
        nomination=nomination,
        opened_at=str(run.get("opened_at") or ""),
    )
    actions = [
        action for action in actions
        if action.get("action_sha256") == proposal.get("action_sha256")
    ]
    if len(actions) != 1:
        raise ValueError("proposal does not bind one persisted eligible strategy action")
    action = actions[0]
    exact = _exact_phenotypes(
        root, str((packet.get("entity") or {}).get("entity_id") or ""),
        candidate_leaf=str(nomination.get("candidate_leaf") or ""),
        candidate_sha256=str(nomination.get("candidate_sha256") or ""),
        as_of=str(run.get("opened_at") or ""),
    )
    event = next((
        row for row in (exact.get(str(action.get("phenotype_sha256") or "")) or {}).get(
            "exact_events"
        ) or ()
        if row.get("move_sha256") == action.get("move_sha256")
        and row.get("implementation_event_sha256")
        == action.get("implementation_event_sha256")
    ), None)
    if event is None or list(_action_forecasts(
        action, packet=packet, opened_at=str(run["opened_at"]), phenotype=event,
    )) != list(proposal.get("candidate_forecasts") or ()):
        raise ValueError("proposal forecasts were not reconstructed from the persisted action")
    if (root / "closed_book" / "settlements" / f"{run_id}.json").exists():
        raise ValueError("cannot activate a strategy-alpha binding after settlement")
    now = canonical_timestamp(_now(), "activation time")
    elapsed = (timestamp_key(now) - timestamp_key(canonical_timestamp(run["opened_at"], "opened_at"))).total_seconds()
    if elapsed < 0 or elapsed > _ISSUANCE_WINDOW_SECONDS:
        raise ValueError("strategy-alpha activation window is closed")
    binding_body = {
        key: value for key, value in proposal.items()
        if key not in {"schema", "compiled_at", "proposal_sha256"}
    }
    binding = _hashed({
        "schema": STRATEGY_ALPHA_BINDING_SCHEMA,
        **binding_body,
        "proposal_sha256": proposal["proposal_sha256"],
        "activated_at": now,
    }, "binding_sha256")
    proposal_path = root / "closed_book" / "strategy_alpha_proposals" / f"{run_id}.json"
    binding_path = root / "closed_book" / "strategy_alpha_bindings" / f"{run_id}.json"
    for path, payload in ((proposal_path, dict(proposal)), (binding_path, binding)):
        if path.exists():
            if _read(path) != payload:
                raise ValueError(f"divergent strategy-alpha artifact already exists: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)
    return {
        "schema": "jaggedthoughts-strategy-alpha-binding-activation-v1",
        "run_id": run_id,
        "proposal_path": proposal_path.relative_to(root).as_posix(),
        "binding_path": binding_path.relative_to(root).as_posix(),
        "binding_sha256": binding["binding_sha256"],
        "capital_authority": False,
    }


def process_strategy_alpha_issuance_actions(
    root: Path, *, run_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Activate eligible issue-time actions and surface every non-activation."""

    selected = set(run_ids or ())
    paths = sorted((root / "closed_book" / "runs").glob("*.json"))
    if run_ids is not None:
        paths = [path for path in paths if path.stem in selected]
    rows = []
    for path in paths:
        run_id = path.stem
        evaluated_at = _now()
        binding_path = root / "closed_book" / "strategy_alpha_bindings" / f"{run_id}.json"
        if binding_path.exists():
            binding = _read(binding_path)
            rows.append(_write_status(root, run_id, {
                "schema": STRATEGY_ALPHA_ACTIVATION_STATUS_SCHEMA,
                "run_id": run_id,
                "evaluated_at": evaluated_at,
                "status": "bound",
                "binding_sha256": binding.get("binding_sha256"),
                "gaps": [],
                "capital_authority": False,
            }))
            continue
        try:
            run = _read(path)
            packet = dict(run.get("evidence_packet") or {})
            entity_id = str((packet.get("entity") or {}).get("entity_id") or "")
            subject_id = str((packet.get("subject") or {}).get("subject_id") or "")
            nomination = dict((packet.get("discovery_summary") or {}).get(
                "strategy_experiment_nomination"
            ) or {})
            if not nomination:
                rows.append(_write_status(root, run_id, {
                    "schema": STRATEGY_ALPHA_ACTIVATION_STATUS_SCHEMA,
                    "run_id": run_id, "evaluated_at": evaluated_at,
                    "status": "not_strategy_experiment", "gaps": [],
                    "capital_authority": False,
                }))
                continue
            actions = _eligible_actions(
                root,
                entity_id=entity_id,
                subject_id=subject_id,
                horizon_days=int(run.get("horizon_days") or packet.get("horizon_days") or 0),
                nomination=nomination,
                opened_at=str(run.get("opened_at") or ""),
            )
            if len(actions) != 1:
                code = "strategy_alpha_action_missing" if not actions else "strategy_alpha_action_ambiguous"
                proposal_result = compile_strategy_alpha_binding_proposal(
                    root, run_id, evaluated_at=evaluated_at,
                )
                gaps = [_gap(code, run_id=run_id, action_ids=sorted(
                    str(action.get("action_id") or "") for action in actions
                )), *proposal_result["gaps"]]
                rows.append(_write_status(root, run_id, {
                    "schema": STRATEGY_ALPHA_ACTIVATION_STATUS_SCHEMA,
                    "run_id": run_id,
                    "evaluated_at": evaluated_at,
                    "status": "awaiting_typed_action" if not actions else "action_ambiguous",
                    "gaps": sorted(gaps, key=lambda row: row["code"]),
                    "required_action": strategy_alpha_action_contract(root),
                    "capital_authority": False,
                }))
                continue
            action = actions[0]
            phenotype_sha = require_text(action.get("phenotype_sha256"), "action.phenotype_sha256")
            exact = _exact_phenotypes(
                root, entity_id,
                candidate_leaf=str(nomination.get("candidate_leaf") or ""),
                candidate_sha256=str(nomination.get("candidate_sha256") or ""),
                as_of=str(run.get("opened_at") or ""),
            )
            phenotype = next((
                row for row in (exact.get(phenotype_sha) or {}).get("exact_events") or ()
                if row.get("move_sha256") == action.get("move_sha256")
                and row.get("implementation_event_sha256")
                == action.get("implementation_event_sha256")
            ), None)
            if phenotype is None:
                raise ValueError("action does not bind an admitted exact move event")
            forecasts = _action_forecasts(
                action, packet=packet, opened_at=str(run["opened_at"]), phenotype=phenotype,
            )
            proposal_result = compile_strategy_alpha_binding_proposal(
                root,
                run_id,
                candidate_forecasts=forecasts,
                phenotype_sha256=phenotype_sha,
                evaluated_at=evaluated_at,
            )
            if not proposal_result["bindable"]:
                rows.append(_write_status(root, run_id, {
                    "schema": STRATEGY_ALPHA_ACTIVATION_STATUS_SCHEMA,
                    "run_id": run_id,
                    "evaluated_at": evaluated_at,
                    "status": "action_rejected",
                    "action_id": action.get("action_id"),
                    "action_sha256": action.get("action_sha256"),
                    "gaps": proposal_result["gaps"],
                    "capital_authority": False,
                }))
                continue
            activation = activate_strategy_alpha_binding(root, proposal_result["proposal"])
            rows.append(_write_status(root, run_id, {
                "schema": STRATEGY_ALPHA_ACTIVATION_STATUS_SCHEMA,
                "run_id": run_id,
                "evaluated_at": evaluated_at,
                "status": "activated",
                "action_id": action.get("action_id"),
                "action_sha256": action.get("action_sha256"),
                "binding_sha256": activation["binding_sha256"],
                "gaps": [],
                "capital_authority": False,
            }))
        except (KeyError, OSError, TypeError, ValueError) as error:
            rows.append(_write_status(root, run_id, {
                "schema": STRATEGY_ALPHA_ACTIVATION_STATUS_SCHEMA,
                "run_id": run_id,
                "evaluated_at": evaluated_at,
                "status": "action_rejected",
                "gaps": [_gap(
                    "strategy_alpha_action_invalid", run_id=run_id,
                    detail=f"{type(error).__name__}: {error}"[:1_000],
                )],
                "capital_authority": False,
            }))
    return {
        "schema": "jaggedthoughts-strategy-alpha-issuance-cycle-v1",
        "evaluated_at": _now(),
        "run_count": len(rows),
        "activated_count": sum(row["status"] in {"activated", "bound"} for row in rows),
        "rows": rows,
        "action_contract": strategy_alpha_action_contract(root),
        "capital_authority": False,
    }


def strategy_alpha_binding_status(root: Path) -> dict[str, Any]:
    """Report which current closed-book runs can be bound at issuance."""

    rows = []
    gap_counts: dict[str, int] = {}
    activation_statuses = {
        value["run_id"]: value
        for path in sorted(
            (root / "closed_book" / "strategy_alpha_activation_status").glob("*.json")
        )
        if (value := _read(path)).get("run_id")
    }
    for path in sorted((root / "closed_book" / "runs").glob("*.json")):
        run = _read(path)
        nomination = (((run.get("evidence_packet") or {}).get("discovery_summary") or {}).get(
            "strategy_experiment_nomination"
        ))
        if not isinstance(nomination, Mapping):
            continue
        activation = activation_statuses.get(path.stem)
        binding_path = root / "closed_book" / "strategy_alpha_bindings" / path.name
        if binding_path.exists() and activation and activation.get("status") in {"activated", "bound"}:
            binding = _read(binding_path)
            try:
                validate_strategy_alpha_binding_abi(binding)
            except ValueError as error:
                code = "legacy_or_ineligible_binding"
                rows.append({
                    "run_id": path.stem,
                    "status": "ineligible_binding",
                    "bindable": False,
                    "binding_sha256": binding.get("binding_sha256"),
                    "gap_codes": [code],
                    "detail": str(error),
                })
                gap_counts[code] = gap_counts.get(code, 0) + 1
                continue
            rows.append({
                "run_id": path.stem,
                "status": "bound",
                "bindable": False,
                "binding_sha256": activation.get("binding_sha256"),
                "gap_codes": [],
            })
            continue
        result = compile_strategy_alpha_binding_proposal(root, path.stem)
        rows.append({
            "run_id": path.stem,
            "status": "bindable" if result["bindable"] else "blocked",
            "bindable": result["bindable"],
            "gap_codes": [gap["code"] for gap in result["gaps"]],
        })
        for gap in result["gaps"]:
            gap_counts[gap["code"]] = gap_counts.get(gap["code"], 0) + 1
    body = {
        "schema": STRATEGY_ALPHA_BINDING_STATUS_SCHEMA,
        "run_count": len(rows),
        "bound_count": sum(row["status"] == "bound" for row in rows),
        "ineligible_binding_count": sum(
            row["status"] == "ineligible_binding" for row in rows
        ),
        "bindable_count": sum(row["bindable"] for row in rows),
        "gap_counts": dict(sorted(gap_counts.items())),
        "runs": rows,
        "action_contract": strategy_alpha_action_contract(root),
        "activation_statuses": [
            activation_statuses[row["run_id"]]
            for row in rows
            if row["run_id"] in activation_statuses
        ],
        "capital_authority": False,
    }
    return _hashed(body, "status_sha256")


__all__ = [
    "STRATEGY_ALPHA_ACTIVATION_STATUS_SCHEMA",
    "STRATEGY_ALPHA_ACTION_PROPOSAL_SCHEMA",
    "STRATEGY_ALPHA_ACTION_REQUEST_SCHEMA",
    "STRATEGY_ALPHA_ARM_ISOLATION_SCHEMA",
    "STRATEGY_ALPHA_BINDING_STATUS_SCHEMA",
    "STRATEGY_ALPHA_ISSUANCE_ACTION_SCHEMA",
    "STRATEGY_ALPHA_PROPOSAL_SCHEMA",
    "STRATEGY_ALPHA_PROCEDURE_SCHEMA",
    "activate_strategy_alpha_binding",
    "compile_strategy_alpha_action_request",
    "compile_strategy_alpha_arm_views",
    "compile_strategy_alpha_deterministic_controls",
    "compile_strategy_alpha_binding_proposal",
    "compile_strategy_alpha_issuance_action",
    "compile_strategy_alpha_procedure",
    "process_strategy_alpha_issuance_actions",
    "strategy_alpha_action_contract",
    "strategy_alpha_binding_status",
]
