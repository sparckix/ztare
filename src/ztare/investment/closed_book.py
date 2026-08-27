"""Prospective closed-book prediction ledger for JaggedThoughts Capital.

The ledger freezes source-visible evidence and several candidate forecasts
before an outcome window begins.  Historical frontier-model replay has a
separate diagnostic authority because disabling tools cannot remove knowledge
already present in model weights.  Prospective forecasts avoid that temporal
problem: the later outcome does not yet exist when the forecast leaf is stored.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.leanmill.frontier_agent_runtime import FrontierAgentConfig, SubscriptionJSONRole
from ztare.worldmodel.evaluation import compile_evaluation_integrity_receipt

from .adaptive_execution import latest_operator_decision, subscription_runtime_version
from .contracts import canonical_timestamp, timestamp_key
from .golden_store import (
    GoldenEdge, GoldenLeaf, GoldenStore, research_evidence_is_admissible,
)
from .paper_watch import paper_watch_decision
from .evidence_vault import evidence_manifest_ref
from .factor_analysis import load_price_points
from .prospective_return_window import (
    RETURN_WINDOW_BINDING_SCHEMA,
    bind_prospective_return_window,
    compile_prospective_return_window,
    index_return_window_points,
    settle_prospective_return_window,
)
from .research_memory import candidate_strategy_phenotype
from .tournament import (
    BacktestEpisode,
    ObservableSpec,
    WorldModelCandidate,
    WorldModelForecast,
    evaluate_world_model_tournament,
)
from .underwriting_ablation import (
    UNDERWRITING_ABLATION_ARMS,
    compile_underwriting_ablation_action,
    compile_underwriting_ablation_arms,
    compile_underwriting_ablation_status,
)
from .underwriting_method_policy import (
    compile_underwriting_method_policy,
    select_underwriting_method_route,
)


CLOSED_BOOK_RUN_SCHEMA = "jaggedthoughts-closed-book-forecast-run-v1"
CLOSED_BOOK_SETTLEMENT_SCHEMA = "jaggedthoughts-closed-book-settlement-v1"
CLOSED_BOOK_STATUS_SCHEMA = "jaggedthoughts-closed-book-status-v1"
_AGENT_FORECAST_SCHEMA = "jaggedthoughts-closed-book-agent-forecast-v1"
_PROMPT_CONTRACT = "jaggedthoughts-closed-book-forecast-prompt-v1"
_STRATEGY_EXPERIMENT_NOMINATION_SCHEMA = "jaggedthoughts-strategy-alpha-episode-nomination-v1"
_CANDIDATE_PAYOFF_RESULT_SCHEMA = "jaggedthoughts-candidate-payoff-forecast-result-v1"
_DEFAULT_FORECAST_MODEL = (
    os.environ.get("ZTARE_INVESTMENT_FORECAST_MODEL", "gpt-5.6-sol").strip()
    or "gpt-5.6-sol"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _research_program_snapshot(root: Path, dossier: Mapping[str, Any]) -> dict[str, Any] | None:
    """Recover the exact question program that produced a dossier when retained."""
    request_sha = str(dossier.get("request_sha256") or "")
    if len(request_sha) != 64:
        return None
    matches = []
    for path in sorted((root / "research_jobs" / "requests").glob("*.json")):
        request = _read_json(path)
        if request and request.get("request_sha256") == request_sha:
            matches.append((path, request))
    if not matches:
        return {"status": "request_artifact_unavailable", "request_sha256": request_sha}
    if len(matches) != 1:
        raise ValueError("research dossier request identity is ambiguous")
    path, request = matches[0]
    request_body = {key: value for key, value in request.items() if key != "request_sha256"}
    if stable_sha256(request_body) != request_sha:
        raise ValueError("research dossier request content hash mismatch")
    assignment = dict(request.get("research_policy_assignment") or {})
    assignment_sha = str(assignment.get("assignment_sha256") or "")
    if assignment_sha and stable_sha256({
        key: value for key, value in assignment.items() if key != "assignment_sha256"
    }) != assignment_sha:
        raise ValueError("research policy assignment content hash mismatch")
    frontier = dict(request.get("research_question_frontier") or {})
    frontier_sha = str(frontier.get("question_frontier_sha256") or "")
    if frontier_sha and stable_sha256({
        key: value for key, value in frontier.items() if key != "question_frontier_sha256"
    }) != frontier_sha:
        raise ValueError("research question frontier content hash mismatch")
    selected = dict(frontier.get("selected_program") or {})
    assignment_unit = {
        "experiment_id": assignment.get("experiment_id"),
        "assignment_unit_id": assignment.get("assignment_unit_id"),
        "randomization_sha256": assignment.get("randomization_sha256"),
    }
    legacy_pair = {
        "experiment_id": assignment.get("experiment_id"),
        "pair_id": assignment.get("pair_id"),
        "pair_slot": assignment.get("pair_slot"),
    }
    return {
        "status": "bound",
        "available_at": request.get("created_at"),
        "request_sha256": request_sha,
        "request_path": path.relative_to(root).as_posix(),
        "assignment_sha256": assignment_sha or None,
        "assignment_arm_id": assignment.get("arm_id"),
        "assignment_unit_id": assignment.get("assignment_unit_id"),
        "assignment_unit_identity_sha256": (
            stable_sha256(assignment_unit)
            if assignment_unit["assignment_unit_id"] else None
        ),
        "pair_identity_sha256": (
            stable_sha256(legacy_pair) if legacy_pair["pair_id"] else None
        ),
        "question_frontier_sha256": frontier_sha or None,
        "question_program_id": selected.get("program_id"),
        "question_program_sha256": stable_sha256(selected) if selected else None,
        "question_program": {
            key: selected.get(key) for key in (
                "program_id", "atom_ids", "dimensions", "question", "source_plan",
            )
        } if selected else None,
    }


def _field_availability_row(
    *, field_path: str, source_id: str, available_at: str, as_of: str,
    observed_at: str | None = None, source_sha256: str | None = None,
    availability_basis: str,
) -> dict[str, Any]:
    """Bind one forecast-input field group to when its source became usable."""
    cutoff = canonical_timestamp(as_of, "field availability cutoff")
    available = canonical_timestamp(available_at, f"{field_path} available_at")
    if timestamp_key(available) > timestamp_key(cutoff):
        raise ValueError(f"forecast field {field_path} was unavailable at its cutoff")
    row = {
        "field_path": str(field_path),
        "source_id": str(source_id),
        "available_at": available,
        "as_of": cutoff,
        "availability_basis": str(availability_basis),
    }
    if observed_at:
        row["observed_at"] = canonical_timestamp(
            observed_at, f"{field_path} observed_at",
        )
    if source_sha256:
        row["source_sha256"] = str(source_sha256)
    return row


def _field_availability_certificate(
    *, rows: list[dict[str, Any]], required_field_paths: set[str], as_of: str,
) -> dict[str, Any]:
    """Declare both covered and missing forecast-input field groups."""
    ordered = sorted(rows, key=lambda row: (
        row["field_path"], row["source_id"], row["available_at"],
    ))
    covered = {str(row["field_path"]) for row in ordered}
    missing = sorted(required_field_paths - covered)
    body = {
        "schema": "jaggedthoughts-field-availability-certificate-v1",
        "as_of": canonical_timestamp(as_of, "field availability certificate as_of"),
        "rows": ordered,
        "required_field_paths": sorted(required_field_paths),
        "unverified_field_paths": missing,
        "field_group_count": len(required_field_paths),
        "verified_field_group_count": len(required_field_paths) - len(missing),
        "complete": not missing,
    }
    return {**body, "certificate_sha256": stable_sha256(body)}


def _base_field_availability(
    *, entity_price: Mapping[str, Any], benchmark_price: Mapping[str, Any],
    quality: Mapping[str, Any], as_of: str,
) -> list[dict[str, Any]]:
    rows = [
        _field_availability_row(
            field_path="starting_market.entity_price",
            source_id=str(entity_price["source_ref"]),
            available_at=str(entity_price["available_at"]), as_of=as_of,
            observed_at=str(entity_price["observed_at"]),
            availability_basis="point_in_time_observation",
        ),
        _field_availability_row(
            field_path="starting_market.benchmark_price",
            source_id=str(benchmark_price["source_ref"]),
            available_at=str(benchmark_price["available_at"]), as_of=as_of,
            observed_at=str(benchmark_price["observed_at"]),
            availability_basis="point_in_time_observation",
        ),
    ]
    quality_available = quality.get("available_at")
    for field_path in ("company_quality.metrics", "company_quality.scores"):
        for source_ref in quality.get("source_refs") or ():
            if quality_available:
                rows.append(_field_availability_row(
                    field_path=field_path, source_id=str(source_ref),
                    available_at=str(quality_available), as_of=as_of,
                    observed_at=str(quality.get("as_of") or quality_available),
                    source_sha256=str(quality.get("quality_report_sha256") or "") or None,
                    availability_basis="source_bound_derived_report",
                ))
    return rows


def closed_book_agent_output_schema() -> dict[str, Any]:
    """Strict response contract for one sealed prospective forecast."""

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema": {"type": "string", "const": _AGENT_FORECAST_SCHEMA},
            "packet_sha256": {"type": "string"},
            "expected_active_return": {"type": "number"},
            "underperformance_probability": {"type": "number"},
            "target_weight": {"type": "number"},
            "mechanism_summary": {"type": "string"},
            "strongest_rival": {"type": "string"},
            "falsifier": {"type": "string"},
        },
        "required": [
            "schema",
            "packet_sha256",
            "expected_active_return",
            "underperformance_probability",
            "target_weight",
            "mechanism_summary",
            "strongest_rival",
            "falsifier",
        ],
    }


def _price_rows_by_entity(
    root: Path,
    entity_ids: set[str],
    *,
    as_of: str,
) -> dict[str, tuple[dict[str, Any], ...]]:
    cutoff = canonical_timestamp(as_of, "closed-book price cutoff")
    wanted = {entity_id.upper() for entity_id in entity_ids if entity_id}
    if not wanted:
        return {}
    latest: dict[str, dict[str, dict[str, Any]]] = {entity_id: {} for entity_id in wanted}
    for point in load_price_points(
        root / "data" / "observations.csv", as_of=cutoff,
        metric_id="adjusted_price", entity_ids=wanted,
    ):
        row = {
            "observation_id": point.observation_id,
            "entity_id": point.entity_id.upper(),
            "price": point.value,
            "observed_at": point.observed_at,
            "available_at": point.available_at,
            "source_ref": point.source_ref,
        }
        latest[point.entity_id.upper()][point.observed_at] = row
    return {
        entity_id: tuple(sorted(rows.values(), key=lambda row: (
            row["observed_at"], row["observation_id"],
        )))
        for entity_id, rows in latest.items()
    }


def _price_rows(root: Path, entity_id: str, *, as_of: str) -> tuple[dict[str, Any], ...]:
    return _price_rows_by_entity(root, {entity_id}, as_of=as_of).get(entity_id.upper(), ())


def _packet_price_rows(
    root: Path,
    entity_id: str,
    *,
    as_of: str,
    price_rows_by_entity: Mapping[str, tuple[dict[str, Any], ...]] | None,
) -> tuple[dict[str, Any], ...]:
    if price_rows_by_entity is None:
        return _price_rows(root, entity_id, as_of=as_of)
    cutoff = timestamp_key(as_of)
    return tuple(
        row for row in price_rows_by_entity.get(entity_id.upper(), ())
        if timestamp_key(str(row["observed_at"])) <= cutoff
        and timestamp_key(str(row["available_at"])) <= cutoff
    )


def _trailing_return(rows: tuple[dict[str, Any], ...], *, as_of: str, days: int) -> float:
    if not rows:
        raise ValueError("closed-book price series is empty")
    cutoff = timestamp_key(as_of) - timedelta(days=days)
    eligible = [row for row in rows if timestamp_key(row["observed_at"]) <= cutoff]
    start = eligible[-1] if eligible else rows[0]
    return float(rows[-1]["price"]) / float(start["price"]) - 1.0


def _quality_packet(root: Path, entity_id: str, *, as_of: str) -> dict[str, Any]:
    quality = _read_json(root / "quality" / f"{entity_id.lower()}.json")
    if not quality or quality.get("schema") != "jaggedthoughts-company-quality-report-v1":
        raise FileNotFoundError(f"closed-book forecast requires a quality report for {entity_id}")
    if timestamp_key(str(quality.get("available_at") or "")) > timestamp_key(as_of):
        raise ValueError("company-quality evidence was unavailable when the forecast opened")
    return {
        "quality_report_sha256": quality.get("quality_report_sha256"),
        "as_of": quality.get("as_of"),
        "available_at": quality.get("available_at"),
        "coverage": quality.get("coverage"),
        "metrics": quality.get("metrics"),
        "scores": quality.get("scores"),
        "source_refs": quality.get("source_refs"),
    }


def _candidate_quality_packet(
    store: GoldenStore | None, candidate: Mapping[str, Any], *, entity_id: str, as_of: str,
) -> dict[str, Any] | None:
    """Resolve the immutable quality input bound into a discovery candidate."""

    if store is None:
        return None
    expected = str(candidate.get("quality_report_sha256") or "")
    for leaf_sha in candidate.get("input_golden_leaves") or ():
        leaf = store.get_leaf(str(leaf_sha))
        payload = dict(leaf.get("payload") or {})
        if (
            leaf.get("object_kind") != "company_quality_report"
            or str(payload.get("entity_id") or "").upper() != entity_id
            or str(payload.get("quality_report_sha256") or "") != expected
        ):
            continue
        if timestamp_key(str(leaf.get("available_at") or "")) > timestamp_key(as_of):
            raise ValueError("candidate-bound company-quality evidence was unavailable")
        return {
            key: payload.get(key) for key in (
                "quality_report_sha256", "as_of", "available_at", "coverage",
                "metrics", "scores", "source_refs",
            )
        }
    return None


def _evidence_packet(
    root: Path,
    decision: Mapping[str, Any],
    *,
    opened_at: str,
    horizon_days: int,
    price_rows_by_entity: Mapping[str, tuple[dict[str, Any], ...]] | None = None,
) -> dict[str, Any]:
    entity = str((decision.get("entity") or {}).get("entity_id") or "").upper()
    benchmark = str((decision.get("benchmark") or {}).get("entity_id") or "").upper()
    if not entity or not benchmark:
        raise ValueError("closed-book decision requires entity and benchmark identities")
    entity_prices = _packet_price_rows(
        root, entity, as_of=opened_at, price_rows_by_entity=price_rows_by_entity,
    )
    benchmark_prices = _packet_price_rows(
        root, benchmark, as_of=opened_at, price_rows_by_entity=price_rows_by_entity,
    )
    if not entity_prices or not benchmark_prices:
        raise ValueError("closed-book forecast requires source-bound entity and benchmark prices")
    quality = _quality_packet(root, entity, as_of=opened_at)
    valuation = dict((decision.get("valuation_envelope") or {}).get("summary") or {})
    summary = dict(decision.get("summary") or {})
    active_21d = (
        _trailing_return(entity_prices, as_of=opened_at, days=21)
        - _trailing_return(benchmark_prices, as_of=opened_at, days=21)
    )
    active_6m = (
        _trailing_return(entity_prices, as_of=opened_at, days=182)
        - _trailing_return(benchmark_prices, as_of=opened_at, days=182)
    )
    end_at = (
        datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
        + timedelta(days=horizon_days)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    body = {
        "schema": "jaggedthoughts-closed-book-evidence-packet-v1",
        "subject": {
            "kind": "paper_decision",
            "subject_id": decision.get("decision_id"),
            "subject_sha256": decision.get("decision_record_sha256"),
        },
        "decision_id": decision.get("decision_id"),
        "decision_record_sha256": decision.get("decision_record_sha256"),
        "decision_as_of": decision.get("as_of"),
        "opened_at": opened_at,
        "end_at": end_at,
        "horizon_days": horizon_days,
        "entity": dict(decision.get("entity") or {}),
        "benchmark": dict(decision.get("benchmark") or {}),
        "starting_market": {
            "entity_price": entity_prices[-1],
            "benchmark_price": benchmark_prices[-1],
            "entity_return_21d": _trailing_return(entity_prices, as_of=opened_at, days=21),
            "benchmark_return_21d": _trailing_return(benchmark_prices, as_of=opened_at, days=21),
            "active_return_21d": active_21d,
            "entity_return_6m": _trailing_return(entity_prices, as_of=opened_at, days=182),
            "benchmark_return_6m": _trailing_return(benchmark_prices, as_of=opened_at, days=182),
            "active_return_6m": active_6m,
        },
        "valuation_summary": valuation,
        "decision_summary": {
            key: summary.get(key)
            for key in (
                "selected_action_id", "target_weight", "underwriting_hurdle_rate",
                "representation_status", "scope_closed", "decision_closed",
            )
        },
        "company_quality": quality,
        "observable_contract": {
            "active_return": "entity total price return minus benchmark total price return",
            "underperformance_event": "1 when active_return is below zero, else 0",
        },
    }
    availability_rows = _base_field_availability(
        entity_price=entity_prices[-1], benchmark_price=benchmark_prices[-1],
        quality=quality, as_of=opened_at,
    )
    decision_available = decision.get("available_at")
    if decision_available:
        for field_path in ("valuation_summary", "decision_summary"):
            availability_rows.append(_field_availability_row(
                field_path=field_path,
                source_id=f"paper-decision:{decision.get('decision_id')}",
                available_at=str(decision_available), as_of=opened_at,
                observed_at=str(decision.get("as_of") or decision_available),
                source_sha256=str(decision.get("decision_record_sha256") or "") or None,
                availability_basis="typed_decision_artifact",
            ))
    body["field_availability"] = _field_availability_certificate(
        rows=availability_rows,
        required_field_paths={
            "starting_market.entity_price", "starting_market.benchmark_price",
            "company_quality.metrics", "company_quality.scores",
            "valuation_summary", "decision_summary",
        },
        as_of=opened_at,
    )
    required_sources = {
        str(entity_prices[-1]["source_ref"]),
        str(benchmark_prices[-1]["source_ref"]),
        *(str(value) for value in quality.get("source_refs") or ()),
    }
    body["evidence_archive"] = evidence_manifest_ref(
        root, as_of=opened_at, required_source_ids=required_sources,
    )
    return {**body, "packet_sha256": stable_sha256(body)}


def _discovery_evidence_packet(
    root: Path,
    candidate: Mapping[str, Any],
    *,
    candidate_leaf: str,
    opened_at: str,
    horizon_days: int,
    benchmark_id: str,
    probe_weight: float,
    strategy_experiment_nomination: Mapping[str, Any] | None = None,
    price_rows_by_entity: Mapping[str, tuple[dict[str, Any], ...]] | None = None,
    candidate_available_at: str | None = None,
    store: GoldenStore | None = None,
) -> dict[str, Any]:
    """Freeze one discovery leaf without turning it into a decision."""

    entity_kind = str(candidate.get("entity_kind") or "")
    experiment = dict(strategy_experiment_nomination or {})
    experiment_admissible = bool(experiment) and entity_kind == "public_equity"
    if (
        candidate.get("schema") != "jaggedthoughts-discovery-candidate-v1"
        or entity_kind not in {"public_equity", "public_fund"}
        or (
            candidate.get("screen_status") != "qualified"
            and not (experiment_admissible and candidate.get("screen_status") == "monitor")
        )
    ):
        raise ValueError(
            "closed-book discovery subjects must be qualified, except typed public-equity research experiments"
        )
    entity_id = str(candidate.get("entity_id") or "").upper()
    benchmark = str(benchmark_id or "").upper()
    candidate_sha = str(candidate.get("candidate_sha256") or "")
    if not entity_id or not benchmark or not candidate_sha or not candidate_leaf:
        raise ValueError("closed-book discovery subject identity is incomplete")
    if not 0 < probe_weight <= 0.25:
        raise ValueError("closed-book discovery probe_weight must be in (0, 0.25]")
    if experiment:
        claimed = str(experiment.get("nomination_sha256") or "")
        valid_hash = claimed and claimed == stable_sha256({
            key: value for key, value in experiment.items() if key != "nomination_sha256"
        })
        if (
            experiment.get("schema") != _STRATEGY_EXPERIMENT_NOMINATION_SCHEMA
            or not valid_hash
            or experiment.get("capital_authority") is not False
            or float(experiment.get("portfolio_weight") or 0.0) != 0.0
            or experiment.get("rank_changed") is not False
            or experiment.get("expected_return_rank_used") is not False
            or str(experiment.get("entity_id") or "").upper() != entity_id
            or str(experiment.get("candidate_id") or "") != str(candidate.get("candidate_id") or "")
            or str(experiment.get("candidate_sha256") or "") != candidate_sha
            or str(experiment.get("candidate_leaf") or "") != candidate_leaf
            or int(experiment.get("discovery_rank") or 10**9) != int(candidate.get("rank") or 10**9)
            or int(experiment.get("horizon_days") or 0) != horizon_days
        ):
            raise ValueError("strategy experiment nomination identity is invalid")
        nominated_at = canonical_timestamp(experiment.get("nominated_at"), "nomination.nominated_at")
        if timestamp_key(nominated_at) > timestamp_key(opened_at):
            raise ValueError("strategy experiment nomination did not exist when the forecast opened")
    if timestamp_key(str(candidate.get("as_of") or "")) > timestamp_key(opened_at):
        raise ValueError("discovery candidate did not exist when the forecast opened")
    entity_prices = _packet_price_rows(
        root, entity_id, as_of=opened_at, price_rows_by_entity=price_rows_by_entity,
    )
    benchmark_prices = _packet_price_rows(
        root, benchmark, as_of=opened_at, price_rows_by_entity=price_rows_by_entity,
    )
    if not entity_prices or not benchmark_prices:
        raise ValueError("closed-book forecast requires source-bound entity and benchmark prices")
    quality: dict[str, Any] = {}
    fund_characteristics: dict[str, Any] = {}
    if entity_kind == "public_equity":
        quality = (
            _candidate_quality_packet(store, candidate, entity_id=entity_id, as_of=opened_at)
            or _quality_packet(root, entity_id, as_of=opened_at)
        )
        if str(quality.get("quality_report_sha256") or "") != str(candidate.get("quality_report_sha256") or ""):
            raise ValueError("discovery candidate and company-quality evidence epochs differ")
        valuation = dict((candidate.get("valuation") or {}).get("summary") or {})
    else:
        fund_characteristics = dict(candidate.get("fund_evidence") or {})
        valuation = dict(candidate.get("valuation") or {})
    metrics = dict(candidate.get("metrics") or {})
    annual_active = float((
        metrics.get("price_implied_excess_return")
        if entity_kind == "public_equity" else metrics.get("residual_alpha")
    ) or 0.0)
    active_21d = (
        _trailing_return(entity_prices, as_of=opened_at, days=21)
        - _trailing_return(benchmark_prices, as_of=opened_at, days=21)
    )
    active_6m = (
        _trailing_return(entity_prices, as_of=opened_at, days=182)
        - _trailing_return(benchmark_prices, as_of=opened_at, days=182)
    )
    end_at = (
        datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
        + timedelta(days=horizon_days)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    body = {
        "schema": "jaggedthoughts-closed-book-evidence-packet-v1",
        "subject": {
            "kind": "discovery_candidate",
            "subject_id": candidate.get("candidate_id"),
            "subject_sha256": candidate_sha,
            "candidate_leaf": candidate_leaf,
            "experiment_kind": "strategy_phenotype" if experiment else None,
            "experiment_nomination_sha256": experiment.get("nomination_sha256"),
        },
        "decision_id": None,
        "decision_record_sha256": None,
        "decision_as_of": None,
        "opened_at": opened_at,
        "end_at": end_at,
        "horizon_days": horizon_days,
        "entity": {
            "entity_id": entity_id,
            "entity_kind": entity_kind,
            "name": candidate.get("name") or entity_id,
        },
        "benchmark": {"entity_id": benchmark, "name": f"{benchmark} benchmark"},
        "starting_market": {
            "entity_price": entity_prices[-1],
            "benchmark_price": benchmark_prices[-1],
            "entity_return_21d": _trailing_return(entity_prices, as_of=opened_at, days=21),
            "benchmark_return_21d": _trailing_return(benchmark_prices, as_of=opened_at, days=21),
            "active_return_21d": active_21d,
            "entity_return_6m": _trailing_return(entity_prices, as_of=opened_at, days=182),
            "benchmark_return_6m": _trailing_return(benchmark_prices, as_of=opened_at, days=182),
            "active_return_6m": active_6m,
        },
        "valuation_summary": valuation,
        "decision_summary": {
            "selected_action_id": (
                "strategy_phenotype_research_experiment"
                if experiment else "qualified_discovery_shadow_probe"
            ),
            "target_weight": 0.0 if experiment else probe_weight if annual_active > 0 else 0.0,
            "underwriting_hurdle_rate": None,
            "representation_status": "unresearched_discovery_candidate",
            "scope_closed": bool((candidate.get("valuation") or {}).get("expectations_frontier", {}).get("scope_closed")),
            "decision_closed": False,
        },
        "discovery_summary": {
            "candidate_sha256": candidate_sha,
            "screen_status": candidate.get("screen_status"),
            "rank": candidate.get("rank"),
            "rank_score": candidate.get("rank_score"),
            "metrics": metrics,
            "annual_active_return": annual_active,
            "annual_active_return_source": (
                "price_implied_excess_return"
                if entity_kind == "public_equity" else "historical_factor_residual_alpha"
            ),
            "criteria": list(candidate.get("criteria") or ()),
            "probe_weight": 0.0 if experiment else probe_weight,
            "research_priority_is_expected_return": False,
            "strategy_experiment_nomination": experiment or None,
        },
        "company_quality": quality,
        "fund_characteristics": fund_characteristics,
        "observable_contract": {
            "active_return": "entity total price return minus benchmark total price return",
            "underperformance_event": "1 when active_return is below zero, else 0",
        },
    }
    availability_rows = _base_field_availability(
        entity_price=entity_prices[-1], benchmark_price=benchmark_prices[-1],
        quality=quality, as_of=opened_at,
    )
    candidate_field_paths = {
        "valuation_summary", "decision_summary", "discovery_summary",
        *(('fund_characteristics',) if entity_kind == "public_fund" else ()),
    }
    if candidate_available_at:
        for field_path in candidate_field_paths:
            availability_rows.append(_field_availability_row(
                field_path=field_path, source_id=f"golden:{candidate_leaf}",
                available_at=candidate_available_at, as_of=opened_at,
                observed_at=str(candidate.get("as_of") or candidate_available_at),
                source_sha256=candidate_sha,
                availability_basis="content_addressed_candidate_leaf",
            ))
    required_field_paths = {
        "starting_market.entity_price", "starting_market.benchmark_price",
        *candidate_field_paths,
    }
    if entity_kind == "public_equity":
        required_field_paths.update({
            "company_quality.metrics", "company_quality.scores",
        })
    body["field_availability"] = _field_availability_certificate(
        rows=availability_rows, required_field_paths=required_field_paths,
        as_of=opened_at,
    )
    required_sources = {
        str(entity_prices[-1]["source_ref"]),
        str(benchmark_prices[-1]["source_ref"]),
        *(str(value) for value in quality.get("source_refs") or ()),
        *(str(value) for value in fund_characteristics.get("source_refs") or ()),
        *(
            str(value) for value in candidate.get("source_refs") or ()
            if not str(value).startswith("signal:")
        ),
    }
    body["evidence_archive"] = evidence_manifest_ref(
        root, as_of=opened_at, required_source_ids=required_sources,
    )
    return {**body, "packet_sha256": stable_sha256(body)}


def _paper_watch_evidence_packet(
    root: Path,
    decision: Mapping[str, Any],
    *,
    store: GoldenStore,
    owner: str,
    opened_at: str,
    horizon_days: int,
    benchmark_id: str,
    price_rows_by_entity: Mapping[str, tuple[dict[str, Any], ...]] | None = None,
) -> dict[str, Any]:
    """Freeze the research-bearing watch as a forecast subject, at zero weight."""
    evidence = dict(decision.get("evidence") or {})
    candidate_leaf = str(evidence.get("candidate_leaf") or "")
    dossier_leaf = str(evidence.get("dossier_leaf") or "")
    candidate_record = store.get_leaf(candidate_leaf)
    if (
        candidate_record.get("owner") != owner
        or candidate_record.get("object_kind") != "discovery_candidate"
        or timestamp_key(str(candidate_record.get("available_at") or "")) > timestamp_key(opened_at)
    ):
        raise ValueError("paper-watch candidate leaf has incompatible identity or availability")
    candidate = dict(candidate_record.get("payload") or {})
    if (
        str(candidate.get("candidate_sha256") or "") != str(evidence.get("candidate_sha256") or "")
        or str(candidate.get("candidate_sha256") or "") != str(candidate_record.get("epoch") or "")
        or str(candidate.get("entity_id") or "").upper()
        != str((decision.get("entity") or {}).get("entity_id") or "").upper()
    ):
        raise ValueError("paper-watch decision crossed candidate identity")
    if dossier_leaf and not research_evidence_is_admissible(
        store, owner=owner, target_leaf=dossier_leaf, as_of=opened_at,
    ):
        raise ValueError("paper-watch research evidence is unavailable or quarantined")
    dossier_payload: dict[str, Any] = {}
    dossier_available_at: str | None = None
    if dossier_leaf:
        dossier_record = store.get_leaf(dossier_leaf)
        dossier_payload = dict(dossier_record.get("payload") or {})
        dossier_available_at = str(dossier_record.get("available_at") or "") or None
        declared_dossier_sha = str(evidence.get("dossier_sha256") or "")
        if (
            dossier_record.get("owner") != owner
            or dossier_record.get("object_kind") != "candidate_research_dossier"
            or timestamp_key(str(dossier_record.get("available_at") or "")) > timestamp_key(opened_at)
            or (
                declared_dossier_sha
                and str(dossier_payload.get("dossier_sha256") or "") != declared_dossier_sha
            )
        ):
            raise ValueError("paper-watch dossier leaf crossed identity or availability")
        evidence.setdefault("dossier_sha256", dossier_payload.get("dossier_sha256"))
    activated_at = canonical_timestamp(
        decision.get("activated_at"), "paper-watch activated_at",
    )
    if timestamp_key(activated_at) > timestamp_key(opened_at):
        raise ValueError("paper-watch decision did not exist when the forecast opened")
    packet = _discovery_evidence_packet(
        root, candidate, candidate_leaf=candidate_leaf, opened_at=opened_at,
        horizon_days=horizon_days, benchmark_id=benchmark_id, probe_weight=0.05,
        price_rows_by_entity=price_rows_by_entity,
        candidate_available_at=str(candidate_record["available_at"]),
        store=store,
    )
    packet.pop("packet_sha256", None)
    factor = dict((decision.get("underwriting_coordinates") or {}).get("factor") or {})
    compact_factor = {
        key: factor.get(key)
        for key in (
            "status", "factor_analysis_sha256", "betas", "fit",
            "historical_residual_alpha", "assumption_implied_return",
        )
    }
    phenotype, phenotype_refs = candidate_strategy_phenotype(
        store, owner=owner, candidate_leaf=candidate_leaf, as_of=opened_at,
    )
    decision_sha = str(decision.get("decision_sha256") or "")
    research_program = _research_program_snapshot(root, dossier_payload)
    packet.update({
        "subject": {
            "kind": "paper_watch_decision",
            "subject_id": decision.get("decision_id"),
            "subject_sha256": decision_sha,
            "decision_schema": decision.get("schema"),
            "candidate_leaf": candidate_leaf,
            "candidate_sha256": evidence.get("candidate_sha256"),
        },
        "decision_id": decision.get("decision_id"),
        "decision_record_sha256": decision_sha,
        "decision_as_of": activated_at,
        "decision_summary": {
            "selected_action_id": "candidate_bound_researched_paper_watch",
            "target_weight": 0.0,
            "underwriting_hurdle_rate": None,
            "representation_status": "candidate_bound_researched_paper_watch",
            "scope_closed": bool(
                (decision.get("strategy_frontier") or {}).get("scope_closed")
            ),
            "decision_closed": False,
        },
        "research_snapshot": {
            "research": dict(decision.get("research") or {}),
            "business_fingerprint": dict(decision.get("business_fingerprint") or {}),
            "strategy_frontier": decision.get("strategy_frontier"),
            "position_admission": dict(decision.get("position_admission") or {}),
            "underwriting": {
                "valuation": dict(
                    (decision.get("underwriting_coordinates") or {}).get("valuation") or {}
                ),
                "factor": compact_factor,
                "research_priority_is_expected_return": False,
            },
            "evidence": evidence,
            "research_program": research_program,
        },
        "strategy_snapshot": {
            "phenotype": phenotype,
            "source_refs": list(phenotype_refs),
            "frozen_at": opened_at,
        },
    })
    prior_availability = dict(packet.get("field_availability") or {})
    availability_rows = list(prior_availability.get("rows") or ())
    required_field_paths = set(prior_availability.get("required_field_paths") or ())
    watch_paths = {
        "decision_summary", "research_snapshot.evidence",
        "research_snapshot.position_admission",
    }
    for field_path in watch_paths:
        availability_rows.append(_field_availability_row(
            field_path=field_path,
            source_id=f"paper-watch:{decision.get('decision_id')}",
            available_at=activated_at, as_of=opened_at,
            observed_at=activated_at, source_sha256=decision_sha,
            availability_basis="typed_paper_watch_decision",
        ))
    dossier_paths = {
        "research_snapshot.research", "research_snapshot.business_fingerprint",
        "research_snapshot.strategy_frontier", "research_snapshot.underwriting",
        "strategy_snapshot",
    }
    if dossier_available_at:
        for field_path in dossier_paths:
            availability_rows.append(_field_availability_row(
                field_path=field_path, source_id=f"golden:{dossier_leaf}",
                available_at=dossier_available_at, as_of=opened_at,
                observed_at=str(dossier_payload.get("as_of") or dossier_available_at),
                source_sha256=str(dossier_payload.get("dossier_sha256") or "") or None,
                availability_basis="content_addressed_research_dossier",
            ))
    program_path = "research_snapshot.research_program"
    if research_program and research_program.get("available_at"):
        availability_rows.append(_field_availability_row(
            field_path=program_path,
            source_id=f"research-request:{research_program.get('request_sha256')}",
            available_at=str(research_program["available_at"]), as_of=opened_at,
            observed_at=str(research_program["available_at"]),
            source_sha256=str(research_program.get("request_sha256") or "") or None,
            availability_basis="content_addressed_research_request",
        ))
    required_field_paths.update(watch_paths | dossier_paths | {program_path})
    packet["field_availability"] = _field_availability_certificate(
        rows=availability_rows, required_field_paths=required_field_paths,
        as_of=opened_at,
    )
    return {**packet, "packet_sha256": stable_sha256(packet)}


def _underperformance_probability(expected_active_return: float, horizon_days: int) -> float:
    scale = 0.20 * math.sqrt(max(1.0, horizon_days) / 365.25)
    return 1.0 / (1.0 + math.exp(expected_active_return / max(scale, 1e-9)))


def _candidate(
    *,
    candidate_id: str,
    family: str,
    mechanism_ids: tuple[str, ...],
    expected_active_return: float,
    underperformance_probability: float,
    target_weight: float,
    source_refs: tuple[str, ...],
    generated_at: str,
    producer: Mapping[str, Any],
    explanation: Mapping[str, Any],
) -> dict[str, Any]:
    if not math.isfinite(expected_active_return) or not -1 <= expected_active_return <= 3:
        raise ValueError(f"candidate {candidate_id} expected_active_return is outside [-1, 3]")
    if not 0 <= underperformance_probability <= 1 or not 0 <= target_weight <= 1:
        raise ValueError(f"candidate {candidate_id} probability and weight must be in [0, 1]")
    process_version = str(producer.get("process_bundle_sha256") or "")[:16] or "1"
    body = {
        "schema": "jaggedthoughts-closed-book-candidate-forecast-v1",
        "candidate_id": candidate_id,
        "version": process_version,
        "model_family": family,
        "trial_family_id": f"{candidate_id}-v{process_version}",
        "mechanism_ids": list(mechanism_ids),
        "predicted_values": {
            "active_return": expected_active_return,
            "underperformance_event": underperformance_probability,
        },
        "target_weight": target_weight,
        "source_refs": sorted(set(source_refs)),
        "generated_at": generated_at,
        "producer": dict(producer),
        "explanation": dict(explanation),
    }
    return {**body, "forecast_sha256": stable_sha256(body)}


def _sealed_candidate_payoff_result(
    raw: Mapping[str, Any],
    *,
    candidate_leaf: str,
    candidate: Mapping[str, Any],
    benchmark_id: str,
    horizon_days: int,
    opened_at: str,
) -> dict[str, Any]:
    """Validate the authored payoff result at the closed-book trust boundary."""

    row = dict(raw)
    digest = str(row.pop("forecast_result_sha256", ""))
    if row.get("schema") != _CANDIDATE_PAYOFF_RESULT_SCHEMA or stable_sha256(row) != digest:
        raise ValueError("candidate payoff forecast result is unsealed or has the wrong schema")
    if (
        str(row.get("candidate_leaf") or "") != candidate_leaf
        or str(row.get("candidate_sha256") or "")
        != str(candidate.get("candidate_sha256") or "")
        or str(row.get("entity_id") or "").upper()
        != str(candidate.get("entity_id") or "").upper()
        or str(row.get("comparator_entity_id") or "").upper() != benchmark_id.upper()
        or int(row.get("horizon_days") or 0) != horizon_days
    ):
        raise ValueError("candidate payoff forecast crossed closed-book episode identity")
    cutoff = canonical_timestamp(row.get("information_cutoff"), "payoff forecast cutoff")
    horizon_at = canonical_timestamp(row.get("horizon_at"), "payoff forecast horizon")
    if timestamp_key(cutoff) > timestamp_key(opened_at) or timestamp_key(horizon_at) <= timestamp_key(cutoff):
        raise ValueError("candidate payoff forecast chronology is incompatible with the seal")
    actual_days = (timestamp_key(horizon_at) - timestamp_key(cutoff)).total_seconds() / 86_400
    if abs(actual_days - horizon_days) > 1:
        raise ValueError("candidate payoff forecast horizon disagrees with the episode")

    expected = dict(row.get("expected_active_return_interval") or {})
    probability = dict(row.get("underperformance_probability_interval") or {})
    expected_low, expected_high = float(expected["low"]), float(expected["high"])
    probability_low, probability_high = float(probability["low"]), float(probability["high"])
    if (
        not all(math.isfinite(value) for value in (
            expected_low, expected_high, probability_low, probability_high,
        ))
        # Active return is candidate return minus benchmark return.  The
        # payoff compiler admits each leg in [-1, 10], so the difference is
        # bounded by [-11, 11], not by the standalone-asset floor of -1.
        or not -11 <= expected_low <= expected_high <= 11
        or not 0 <= probability_low <= probability_high <= 1
    ):
        raise ValueError("candidate payoff forecast intervals are invalid")
    if any(row.get(field) is not False for field in (
        "market_state_prices_identified", "rank_authority", "portfolio_authority",
        "capital_authority",
    )):
        raise ValueError("candidate payoff forecast may not carry allocation authority")
    return {**row, "forecast_result_sha256": digest}


def _candidate_from_payoff_result(
    result: Mapping[str, Any], *, packet_sha256: str, generated_at: str,
) -> dict[str, Any]:
    expected = dict(result["expected_active_return_interval"])
    probability = dict(result["underperformance_probability_interval"])
    result_sha = str(result["forecast_result_sha256"])
    candidate = _candidate(
        candidate_id="candidate_payoff_forecast",
        family="authored_world_partition",
        mechanism_ids=("typed_world_partition", "interval_payoff_mixture"),
        expected_active_return=(float(expected["low"]) + float(expected["high"])) / 2,
        underperformance_probability=(float(probability["low"]) + float(probability["high"])) / 2,
        target_weight=0.0,
        source_refs=(packet_sha256, result_sha),
        generated_at=generated_at,
        producer={
            "mode": "authored_forecast_contract",
            "contract_sha256": result["contract_sha256"],
            "process_bundle_sha256": result_sha,
        },
        explanation={
            "expected_return_identity": result["expected_return_identity"],
            "physical_probability_identity": result["physical_probability_identity"],
            "portfolio_authority": False,
        },
    )
    body = {
        **{key: value for key, value in candidate.items() if key != "forecast_sha256"},
        "prediction_intervals": {
            "active_return": expected,
            "underperformance_probability": probability,
        },
        "candidate_payoff_forecast_result_sha256": result_sha,
    }
    return {**body, "forecast_sha256": stable_sha256(body)}


def _generation_processes(candidates: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(
        "subscription_llm"
        if str((row.get("producer") or {}).get("mode") or "") == "direct_agent"
        else "deterministic"
        if str((row.get("producer") or {}).get("mode") or "") == "deterministic_program"
        else "unknown"
        for row in candidates
    )


def _deterministic_candidates(packet: Mapping[str, Any], *, generated_at: str) -> list[dict[str, Any]]:
    horizon = int(packet["horizon_days"])
    subject = dict(packet.get("subject") or {})
    sources = (
        str(subject.get("subject_id") or packet.get("decision_id") or "unknown-subject"),
        str(packet["packet_sha256"]),
    )
    valuation = dict(packet.get("valuation_summary") or {})
    summary = dict(packet.get("decision_summary") or {})
    market = dict(packet.get("starting_market") or {})
    discovery = dict(packet.get("discovery_summary") or {})
    entity_kind = str((packet.get("entity") or {}).get("entity_kind") or "public_equity")
    annual_active = float(
        discovery.get("annual_active_return")
        if discovery.get("annual_active_return") is not None
        else valuation.get("price_implied_excess_return") or 0.0
    )
    valuation_active = (
        (1.0 + annual_active) ** (horizon / 365.25) - 1.0
        if annual_active > -1 else -1.0
    )
    momentum_active = float(market.get("active_return_6m") or 0.0)
    engine_weight = float(summary.get("target_weight") or 0.0)
    subject_kind = str(subject.get("kind") or "paper_decision")
    probe_weight = float((packet.get("discovery_summary") or {}).get("probe_weight") or 0.0)
    momentum_weight = (
        probe_weight if subject_kind == "discovery_candidate" and momentum_active > 0
        else 0.25 if momentum_active > 0.025 else 0.10 if momentum_active > 0 else 0.0
    )
    if entity_kind == "public_fund":
        valuation_candidate_id = "jaggedthoughts_fund_factor_value"
        valuation_mechanisms = (
            "historical_factor_residual_alpha", "aggregate_earnings_power",
            "qualified_discovery_shadow_probe",
        )
    else:
        valuation_candidate_id = (
            "jaggedthoughts_discovery_valuation"
            if subject_kind == "discovery_candidate" else "jaggedthoughts_valuation_policy"
        )
        valuation_mechanisms = (
            ("price_implied_excess_return", "qualified_discovery_shadow_probe")
            if subject_kind == "discovery_candidate"
            else ("price_implied_excess_return", "compiled_position_policy")
        )
    return [
        _candidate(
            candidate_id="no_active_edge_control",
            family="historical_control",
            mechanism_ids=("zero_active_return",),
            expected_active_return=0.0,
            underperformance_probability=0.5,
            target_weight=0.0,
            source_refs=sources,
            generated_at=generated_at,
            producer={"mode": "deterministic_program", "implementation": "zero-active-control-v1"},
            explanation={"rule": "predict zero active return and no position"},
        ),
        _candidate(
            candidate_id="six_month_active_momentum_control",
            family="price_momentum",
            mechanism_ids=("active_momentum_persistence",),
            expected_active_return=momentum_active,
            underperformance_probability=_underperformance_probability(momentum_active, horizon),
            target_weight=momentum_weight,
            source_refs=sources,
            generated_at=generated_at,
            producer={"mode": "deterministic_program", "implementation": "six-month-active-momentum-v1"},
            explanation={
                "rule": "carry the trailing 182-calendar-day active return into the forecast horizon",
                "active_return_6m": momentum_active,
            },
        ),
        _candidate(
            candidate_id=valuation_candidate_id,
            family="fundamental_valuation",
            mechanism_ids=valuation_mechanisms,
            expected_active_return=valuation_active,
            underperformance_probability=_underperformance_probability(valuation_active, horizon),
            target_weight=engine_weight,
            source_refs=sources,
            generated_at=generated_at,
            producer={"mode": "deterministic_program", "implementation": "jaggedthoughts-valuation-policy-v1"},
            explanation={
                "annual_active_return_input": annual_active,
                "annual_active_return_source": discovery.get(
                    "annual_active_return_source", "price_implied_excess_return"
                ),
                "horizon_conversion": "(1 + annual_active) ** (horizon_days / 365.25) - 1",
                "policy_weight_source": "frozen decision summary",
            },
        ),
    ]


def _agent_prompt(packet: Mapping[str, Any]) -> str:
    return f"""You are a closed-book investment forecasting lane. The JSON evidence packet below
is the complete tool-visible evidence for one prospective episode. The future outcome does not
yet exist. Tools, web search, shell, and repository access are disabled for this call.

Forecast the entity's price return minus its benchmark's price return over the declared horizon.
Return a probability that this active return will be below zero and a paper target weight in [0,1].
Use the packet's valuation, quality, and market-history coordinates. State one compact mechanism,
the strongest rival, and a falsifier. Do not claim access to evidence outside the packet. Return
only the strict JSON object required by the response schema and preserve packet_sha256 exactly.

EVIDENCE PACKET
{json.dumps(packet, indent=2, sort_keys=True)}
"""


def _ablation_agent_prompt(packet: Mapping[str, Any]) -> str:
    return f"""You are one blinded arm in a prospective investment-research experiment.
The JSON below is your complete visible evidence. Tools, web search, shell, repository access,
and evidence from the other arms are unavailable. Forecast the entity price return minus its
benchmark price return over the declared horizon. Return the probability that active return is
below zero. Use a fixed paper probe: target_weight must be 0.05 when expected_active_return is
positive and 0 otherwise. State one mechanism, rival, and falsifier. Preserve packet_sha256
exactly and return only the strict JSON object required by the response schema.

BLINDED ARM PACKET
{json.dumps(packet, indent=2, sort_keys=True)}
"""


def _validate_agent_forecast(packet: Mapping[str, Any], result: Mapping[str, Any]) -> None:
    if result.get("schema") != _AGENT_FORECAST_SCHEMA:
        raise ValueError("closed-book agent returned the wrong schema")
    if str(result.get("packet_sha256") or "") != packet["packet_sha256"]:
        raise ValueError("closed-book agent changed the evidence packet identity")
    for key in ("mechanism_summary", "strongest_rival", "falsifier"):
        if not str(result.get(key) or "").strip():
            raise ValueError(f"closed-book agent requires {key}")
    expected = float(result["expected_active_return"])
    probability = float(result["underperformance_probability"])
    weight = float(result["target_weight"])
    if not math.isfinite(expected) or not -1 <= expected <= 3:
        raise ValueError("closed-book expected active return is outside [-1, 3]")
    if not 0 <= probability <= 1 or not 0 <= weight <= 1:
        raise ValueError("closed-book probability and target weight must be in [0, 1]")


def _validate_ablation_forecast(
    packet: Mapping[str, Any], result: Mapping[str, Any],
) -> None:
    _validate_agent_forecast(packet, result)
    expected = float(result["expected_active_return"])
    required = 0.05 if expected > 0 else 0.0
    if abs(float(result["target_weight"]) - required) > 1e-12:
        raise ValueError("underwriting ablation requires the fixed 5% positive-edge probe")


def _episode_identity(packet: Mapping[str, Any]) -> str:
    subject = dict(packet.get("subject") or {})
    payoff = dict(packet.get("candidate_payoff_forecast") or {})
    return stable_sha256({
        "entity_id": str((packet.get("entity") or {}).get("entity_id") or ""),
        "subject_kind": str(subject.get("kind") or "paper_decision"),
        "subject_sha256": str(
            subject.get("subject_sha256") or packet.get("decision_record_sha256") or ""
        ),
        "issue_date": str(packet.get("opened_at") or "")[:10],
        "horizon_days": int(packet.get("horizon_days") or 0),
        "experiment_nomination_sha256": str(
            subject.get("experiment_nomination_sha256") or ""
        ),
        "candidate_payoff_forecast_result_sha256": str(
            payoff.get("forecast_result_sha256") or ""
        ),
    })


def _inference_block_identity(packet: Mapping[str, Any]) -> str:
    return stable_sha256({
        "benchmark_id": str((packet.get("benchmark") or {}).get("entity_id") or ""),
        "issue_date": str(packet.get("opened_at") or "")[:10],
        "horizon_days": int(packet.get("horizon_days") or 0),
    })


def _record_leaf(
    *,
    owner: str,
    store_path: Path,
    object_kind: str,
    object_id: str,
    epoch: str,
    occurred_at: str,
    payload: Mapping[str, Any],
    source_refs: tuple[str, ...],
    edge_targets: tuple[tuple[str, str], ...] = (),
) -> str:
    leaf = GoldenLeaf(
        owner=owner,
        object_kind=object_kind,
        object_id=object_id,
        epoch=epoch,
        occurred_at=occurred_at,
        available_at=_utc_now(),
        payload=dict(payload),
        source_refs=source_refs,
    )
    GoldenStore(store_path).append_bundle(
        (leaf,),
        tuple(
            GoldenEdge(leaf.leaf_sha256, target_sha256, relation)
            for target_sha256, relation in edge_targets
        ),
        make_heads=True,
    )
    return leaf.leaf_sha256


def _head_target(
    store_path: Path, owner: str, object_kind: str, object_id: str,
) -> tuple[tuple[str, str], ...]:
    try:
        target = GoldenStore(store_path).head(owner, object_kind, object_id)
    except KeyError:
        return ()
    return ((str(target["leaf_sha256"]), "derived_from"),)


def _open_closed_book_forecast(
    root: Path,
    *,
    owner: str,
    store_path: Path,
    decision_id: str | None = None,
    paper_watch_decision_id: str | None = None,
    candidate_leaf: str | None = None,
    benchmark_id: str = "SPY",
    probe_weight: float = 0.05,
    horizon_days: int = 90,
    config: FrontierAgentConfig | None = None,
    agent_result: Mapping[str, Any] | None = None,
    ablation_agent_results: Mapping[str, Mapping[str, Any]] | None = None,
    payoff_forecast_result: Mapping[str, Any] | None = None,
    strategy_experiment_nomination: Mapping[str, Any] | None = None,
    price_rows_by_entity: Mapping[str, tuple[dict[str, Any], ...]] | None = None,
) -> dict[str, Any]:
    """Freeze one prospective episode and its complete candidate forecast set."""

    if horizon_days < 7 or horizon_days > 730:
        raise ValueError("closed-book horizon_days must be in [7, 730]")
    if sum(bool(value) for value in (decision_id, paper_watch_decision_id, candidate_leaf)) > 1:
        raise ValueError("closed-book subject must identify exactly one source")
    if strategy_experiment_nomination and not candidate_leaf:
        raise ValueError("strategy experiment nominations require a discovery candidate leaf")
    if payoff_forecast_result is not None and (
        not candidate_leaf or strategy_experiment_nomination is not None
    ):
        raise ValueError("candidate payoff forecasts require an un-nominated discovery candidate")
    if sum(value is not None for value in (
        agent_result, ablation_agent_results, payoff_forecast_result,
    )) > 1:
        raise ValueError("closed-book accepts one injected forecast mode")
    opened_at = _utc_now()
    sealed_payoff_result: dict[str, Any] | None = None
    decision_path: Path | None = None
    if paper_watch_decision_id:
        decision_path, decision = paper_watch_decision(root, paper_watch_decision_id)
        packet = _paper_watch_evidence_packet(
            root, decision, store=GoldenStore(store_path), owner=owner,
            opened_at=opened_at, horizon_days=horizon_days, benchmark_id=benchmark_id,
            price_rows_by_entity=price_rows_by_entity,
        )
        subject_target = _head_target(
            store_path, owner,
            (
                "public_equity_paper_decision"
                if decision.get("schema")
                == "jaggedthoughts-public-equity-paper-decision-v1"
                else "public_fund_paper_decision"
            ),
            str(decision["decision_id"]),
        )
    elif candidate_leaf:
        candidate_store = GoldenStore(store_path)
        candidate_record = candidate_store.get_leaf(candidate_leaf)
        if (
            candidate_record.get("owner") != owner
            or candidate_record.get("object_kind") != "discovery_candidate"
            or timestamp_key(str(candidate_record.get("available_at") or "")) > timestamp_key(opened_at)
        ):
            raise ValueError("closed-book candidate leaf has incompatible identity or availability")
        candidate = dict(candidate_record.get("payload") or {})
        if str(candidate.get("candidate_sha256") or "") != str(candidate_record.get("epoch") or ""):
            raise ValueError("closed-book candidate leaf epoch differs from its payload")
        packet = _discovery_evidence_packet(
            root,
            candidate,
            candidate_leaf=candidate_leaf,
            opened_at=opened_at,
            horizon_days=horizon_days,
            benchmark_id=benchmark_id,
            probe_weight=probe_weight,
            strategy_experiment_nomination=strategy_experiment_nomination,
            price_rows_by_entity=price_rows_by_entity,
            candidate_available_at=str(candidate_record["available_at"]),
            store=candidate_store,
        )
        if payoff_forecast_result is not None:
            sealed_payoff_result = _sealed_candidate_payoff_result(
                payoff_forecast_result,
                candidate_leaf=candidate_leaf,
                candidate=candidate,
                benchmark_id=benchmark_id,
                horizon_days=horizon_days,
                opened_at=opened_at,
            )
            packet_body = {
                key: value for key, value in packet.items() if key != "packet_sha256"
            }
            packet_body["candidate_payoff_forecast"] = sealed_payoff_result
            packet = {**packet_body, "packet_sha256": stable_sha256(packet_body)}
        subject_target = ((candidate_leaf, "derived_from"),)
    else:
        decision_path, decision = latest_operator_decision(root, decision_id)
        packet = _evidence_packet(
            root,
            decision,
            opened_at=opened_at,
            horizon_days=horizon_days,
            price_rows_by_entity=price_rows_by_entity,
        )
        subject_target = _head_target(
            store_path,
            str(decision.get("owner") or owner),
            "paper_decision",
            str(decision["decision_id"]),
        )
    subject = dict(packet["subject"])
    archive = dict(packet.get("evidence_archive") or {})
    archive_target = (
        ((str(archive["manifest_leaf_sha256"]), "derived_from"),)
        if archive.get("status") == "covered" and archive.get("manifest_leaf_sha256")
        else ()
    )
    entity_id = str((packet.get("entity") or {}).get("entity_id") or "")
    episode_identity_sha256 = _episode_identity(packet)
    inference_block_id = _inference_block_identity(packet)
    episode_id = (
        f"{entity_id.lower()}-{opened_at[:10]}-{horizon_days}d-"
        f"{episode_identity_sha256[:10]}"
    )
    for existing_path in sorted((root / "closed_book" / "runs").glob("*.json")):
        existing = _read_json(existing_path)
        existing_packet = dict((existing or {}).get("evidence_packet") or {})
        existing_episode_identity = (
            _episode_identity(existing_packet) if existing_packet else
            str((existing or {}).get("episode_identity_sha256") or "")
        )
        if existing and existing_episode_identity == episode_identity_sha256:
            run_head = _head_target(
                store_path, owner, "closed_book_forecast_run", str(existing["run_id"]),
            )
            if run_head and subject_target:
                GoldenStore(store_path).append_edge(GoldenEdge(
                    run_head[0][0], subject_target[0][0], "derived_from",
                ))
            return {
                **existing,
                "ok": existing.get("provider", {}).get("error") is None,
                "replayed": True,
                "run_path": existing_path.relative_to(root).as_posix(),
            }
    if strategy_experiment_nomination:
        from .strategy_alpha_scheduler import (
            compile_strategy_alpha_episode_history,
            strategy_alpha_cohort_policy,
            strategy_alpha_issuance_vetoes,
        )

        history = compile_strategy_alpha_episode_history(root)["episodes"]
        proposed_key = str((
            strategy_experiment_nomination.get("dual_outcome_contract") or {}
        ).get("dual_outcome_episode_key_sha256") or "")
        if proposed_key and any(
            row["dual_outcome_episode_key_sha256"] == proposed_key
            for row in history
        ):
            raise ValueError("strategy-alpha episode identity was already opened")
        if strategy_alpha_issuance_vetoes(
            history,
            proposed_entity_id=str(strategy_experiment_nomination.get("entity_id") or ""),
            proposed_at=opened_at,
            **strategy_alpha_cohort_policy(root),
        ):
            raise ValueError(
                "strategy-alpha issuance requires a new issuer and open cohort capacity"
            )
    run_identity = {
        "episode_id": episode_id,
        "packet_sha256": packet["packet_sha256"],
        "prompt_contract": _PROMPT_CONTRACT,
    }
    run_id = f"closed-book-{stable_sha256(run_identity)[:20]}"
    run_path = root / "closed_book" / "runs" / f"{run_id}.json"
    prior = _read_json(run_path)
    if prior:
        return {**prior, "ok": True, "replayed": True, "run_path": run_path.relative_to(root).as_posix()}

    candidates = _deterministic_candidates(packet, generated_at=opened_at)
    config = config or FrontierAgentConfig(
        runtime="codex",
        model=_DEFAULT_FORECAST_MODEL,
        reasoning_effort="medium",
        timeout_seconds=900,
        visible_workbench=False,
        web_research=False,
    )
    runtime_version = subscription_runtime_version(config.runtime)
    requested_model = str(config.model or "account-default")
    model_identity_complete = requested_model not in {
        "default", "account-default", "account_default",
    }
    process_body = {
        "schema": "jaggedthoughts-forecast-process-bundle-v1",
        "runtime": config.runtime,
        "runtime_version": runtime_version,
        "requested_model": requested_model,
        "resolved_model": requested_model if model_identity_complete else None,
        "model_identity_complete": model_identity_complete,
        "reasoning_effort": config.reasoning_effort,
        "prompt_contract": _PROMPT_CONTRACT,
        "output_schema_sha256": stable_sha256(closed_book_agent_output_schema()),
        "web_research": False,
        "shell_access": False,
        "repository_tool_access": False,
        "candidate_contract": "jaggedthoughts-closed-book-candidate-forecast-v1",
    }
    process_bundle = {**process_body, "process_bundle_sha256": stable_sha256(process_body)}
    if sealed_payoff_result is not None:
        candidates.append(_candidate_from_payoff_result(
            sealed_payoff_result,
            packet_sha256=str(packet["packet_sha256"]),
            generated_at=opened_at,
        ))
    provider_error: str | None = None
    provider_called = False
    provider_ref = ""
    provider_calls: list[dict[str, Any]] = []
    ablation_packets = compile_underwriting_ablation_arms(packet)
    use_ablation = (
        bool(ablation_packets)
        and agent_result is None
        and sealed_payoff_result is None
    )
    if ablation_agent_results is not None and not ablation_packets:
        raise ValueError("underwriting ablation results require a researched paper watch")
    ablation_candidate_ids: dict[str, str] = {}
    underwriting_method_policy = None
    underwriting_method_route = None
    selected_ablation_arms = tuple(UNDERWRITING_ABLATION_ARMS)
    if use_ablation:
        try:
            current_ablation = dict(
                closed_book_status(root).get("underwriting_ablation") or {}
            )
            underwriting_method_policy = compile_underwriting_method_policy(
                current_ablation, compiled_at=opened_at,
            )
            underwriting_method_route = select_underwriting_method_route(
                underwriting_method_policy,
                episode_identity=episode_identity_sha256,
                opened_at=opened_at,
                learning_credit_assignment=(
                    (_read_json(root / "state" / "read_model.json") or {}).get(
                        "learning_credit_assignment"
                    )
                ),
                current_ablation_status=current_ablation,
            )
            selected_ablation_arms = tuple(
                underwriting_method_route["selected_arms"]
            )
        except (KeyError, OSError, TypeError, ValueError):
            underwriting_method_policy = None
            underwriting_method_route = None
    started = time.monotonic()
    if use_ablation:
        mechanism_by_role = {
            "typed_quantitative": ("typed_valuation_factor_market",),
            "typed_plus_fingerprint": (
                "typed_valuation_factor_market", "business_or_fund_fingerprint",
            ),
            "typed_plus_full_research": (
                "typed_valuation_factor_market", "business_or_fund_fingerprint",
                "thesis_rival_strategy_research",
            ),
        }
        errors = []
        for arm_role in selected_ablation_arms:
            arm_packet = ablation_packets[arm_role]
            call_id = stable_sha256({
                "packet_sha256": arm_packet["packet_sha256"],
                "runtime": config.runtime,
                "runtime_version": runtime_version,
                "model": config.model,
                "reasoning_effort": config.reasoning_effort,
                "prompt_contract": _PROMPT_CONTRACT,
            })
            artifact_dir = root / "closed_book" / "agent_calls" / call_id
            arm_ref = artifact_dir.relative_to(root).as_posix()
            result = (
                dict(ablation_agent_results[arm_role])
                if ablation_agent_results is not None and arm_role in ablation_agent_results
                else None
            )
            called = False
            if result is None and ablation_agent_results is None:
                role = SubscriptionJSONRole(
                    role=f"jaggedthoughts_underwriting_ablation_{arm_role}",
                    agent_id=f"jaggedthoughts-ablation-{call_id[:16]}",
                    repo=_repo_root(), artifact_dir=artifact_dir, config=config,
                    output_schema=closed_book_agent_output_schema(),
                )
                try:
                    result = role(_ablation_agent_prompt(arm_packet))
                    called = bool(role.provider_call_count)
                except Exception as error:
                    errors.append(f"{arm_role}:{type(error).__name__}: {error}"[:1_000])
            elif result is None:
                errors.append(f"{arm_role}:injected_result_absent")
            provider_called = provider_called or called
            provider_calls.append({
                "arm_role": arm_role,
                "packet_sha256": arm_packet["packet_sha256"],
                "artifact_ref": arm_ref,
                "called": called,
            })
            if result is None:
                continue
            try:
                _validate_ablation_forecast(arm_packet, result)
                candidate_id = f"underwriting_{arm_role}"
                candidates.append(_candidate(
                    candidate_id=candidate_id,
                    family="underwriting_information_ablation",
                    mechanism_ids=mechanism_by_role[arm_role],
                    expected_active_return=float(result["expected_active_return"]),
                    underperformance_probability=float(result["underperformance_probability"]),
                    target_weight=float(result["target_weight"]),
                    source_refs=(
                        str(arm_packet["packet_sha256"]),
                        arm_ref if called else "injected-agent-result",
                    ),
                    generated_at=_utc_now(),
                    producer={
                        "mode": "direct_agent", "runtime": config.runtime,
                        "runtime_version": runtime_version, "model": config.model,
                        "reasoning_effort": config.reasoning_effort,
                        "prompt_contract": _PROMPT_CONTRACT,
                        "process_bundle_sha256": process_bundle["process_bundle_sha256"],
                    },
                    explanation={
                        "evidence_arm": arm_role,
                        "mechanism_summary": result["mechanism_summary"],
                        "strongest_rival": result["strongest_rival"],
                        "falsifier": result["falsifier"],
                    },
                ))
                ablation_candidate_ids[arm_role] = candidate_id
            except (KeyError, TypeError, ValueError) as error:
                errors.append(f"{arm_role}:{type(error).__name__}: {error}"[:1_000])
        provider_error = "; ".join(errors) or None
    elif agent_result is None and sealed_payoff_result is None:
        call_id = stable_sha256({
            "packet_sha256": packet["packet_sha256"],
            "runtime": config.runtime,
            "runtime_version": runtime_version,
            "model": config.model,
            "reasoning_effort": config.reasoning_effort,
            "prompt_contract": _PROMPT_CONTRACT,
        })
        artifact_dir = root / "closed_book" / "agent_calls" / call_id
        provider_ref = artifact_dir.relative_to(root).as_posix()
        role = SubscriptionJSONRole(
            role="jaggedthoughts_closed_book_forecaster",
            agent_id=f"jaggedthoughts-closed-book-{call_id[:16]}",
            repo=_repo_root(),
            artifact_dir=artifact_dir,
            config=config,
            output_schema=closed_book_agent_output_schema(),
        )
        try:
            agent_result = role(_agent_prompt(packet))
            provider_called = bool(role.provider_call_count)
        except Exception as error:
            provider_error = f"{type(error).__name__}: {error}"[:1_000]
            agent_result = None
    if agent_result is not None and not use_ablation and sealed_payoff_result is None:
        try:
            _validate_agent_forecast(packet, agent_result)
            discovery_subject = subject.get("kind") == "discovery_candidate"
            strategy_experiment = subject.get("experiment_kind") == "strategy_phenotype"
            candidates.append(_candidate(
                candidate_id=(
                    "frontier_discovery_forecast"
                    if discovery_subject else "frontier_closed_book_forecast"
                ),
                family="frontier_agent",
                mechanism_ids=(
                    ("discovery_packet_synthesis", "rival_thesis_forecast")
                    if discovery_subject
                    else ("source_packet_synthesis", "rival_thesis_forecast")
                ),
                expected_active_return=float(agent_result["expected_active_return"]),
                underperformance_probability=float(agent_result["underperformance_probability"]),
                target_weight=(0.0 if strategy_experiment else float(agent_result["target_weight"])),
                source_refs=(str(packet["packet_sha256"]), provider_ref or "injected-agent-result"),
                generated_at=_utc_now(),
                producer={
                    "mode": "direct_agent",
                    "runtime": config.runtime,
                    "runtime_version": runtime_version,
                    "model": config.model,
                    "reasoning_effort": config.reasoning_effort,
                    "prompt_contract": _PROMPT_CONTRACT,
                    "process_bundle_sha256": process_bundle["process_bundle_sha256"],
                },
                explanation={
                    "mechanism_summary": agent_result["mechanism_summary"],
                    "strongest_rival": agent_result["strongest_rival"],
                    "falsifier": agent_result["falsifier"],
                },
            ))
        except (KeyError, TypeError, ValueError) as error:
            provider_error = f"{type(error).__name__}: {error}"[:1_000]

    sealed_at = _utc_now()
    ablation_action = (
        compile_underwriting_ablation_action(
            packet, arm_packets=ablation_packets,
            forecast_candidate_ids=ablation_candidate_ids,
            process_bundle_sha256=process_bundle["process_bundle_sha256"],
            compiled_at=sealed_at,
        )
        if (
            ablation_packets
            and set(selected_ablation_arms) == set(UNDERWRITING_ABLATION_ARMS)
        ) else None
    )
    return_window = compile_prospective_return_window(
        sealed_at=sealed_at,
        horizon_days=horizon_days,
        entity_ids=(entity_id, str((packet.get("benchmark") or {})["entity_id"])),
        transaction_cost_bps=10.0,
    )
    evaluation_integrity = compile_evaluation_integrity_receipt(
        temporal_design="prospective_sealed",
        generation_processes=_generation_processes(candidates),
        source_availability_rows=tuple(
            (packet.get("field_availability") or {}).get("rows") or ()
        ),
        seal_rows=tuple({
            "episode_id": f"{episode_id}:{row['candidate_id']}",
            "sealed_at": sealed_at,
            "episode_start_at": sealed_at,
        } for row in candidates),
    )
    body = {
        "schema": CLOSED_BOOK_RUN_SCHEMA,
        "run_id": run_id,
        "episode_id": episode_id,
        "episode_identity_sha256": episode_identity_sha256,
        "inference_block_id": inference_block_id,
        "status": "pending_outcome",
        "mode": "prospective_shadow",
        "opened_at": opened_at,
        "sealed_at": sealed_at,
        "end_at": packet["end_at"],
        "horizon_days": horizon_days,
        "subject": subject,
        "decision_path": decision_path.relative_to(root).as_posix() if decision_path else None,
        "evidence_packet": packet,
        "candidate_forecasts": candidates,
        "underwriting_information_ablation": ablation_action,
        "underwriting_method_policy": underwriting_method_policy,
        "underwriting_method_route": underwriting_method_route,
        "evaluation_integrity": evaluation_integrity,
        "provider": {
            "runtime": config.runtime,
            "runtime_version": runtime_version,
            "model": config.model,
            "reasoning_effort": config.reasoning_effort,
            "called": provider_called,
            "artifact_ref": provider_ref,
            "ablation_calls": provider_calls,
            "wallclock_s": max(0.0, time.monotonic() - started),
            "error": provider_error,
            "process_bundle": process_bundle,
        },
        "temporal_integrity": {
            "forecast_generated_before_episode_end": True,
            "outcome_existed_at_generation": False,
            "tool_visible_evidence": "exact_packet_only",
            "shell_access": False,
            "repository_tool_access": False,
            "web_access": False,
            "parametric_prior": "unmeasured_preissue_model_memory",
            "data_replay_authority": archive.get(
                "archive_authority", "unarchived_source_packet"
            ),
            "evidence_manifest_ref_sha256": archive.get("ref_sha256"),
            "prospective_engine_evidence_eligible": True,
            "historical_llm_replay_authority": "diagnostic_only",
            "reason": (
                "Prospective settlement tests the full producer after the forecast is frozen. "
                "Historical frontier replay cannot exclude post-cutoff training memory from prompts alone."
            ),
        },
        "settlement_contract": {
            "score_contract_version": "3",
            "prospective_return_window": return_window,
            "transaction_cost_bps": 10.0,
            "cash_return": 0.0,
            "primary_policy_outcome": "active_return_contribution_after_cost",
            "minimum_inference_blocks_for_comparison": 8,
        },
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    run = {**body, "run_sha256": stable_sha256(body)}
    _atomic_json(run_path, run)
    leaf_sha = _record_leaf(
        owner=owner,
        store_path=store_path,
        object_kind="closed_book_forecast_run",
        object_id=run_id,
        epoch=str(packet["packet_sha256"]),
        occurred_at=opened_at,
        payload=run,
        source_refs=(str(subject["subject_id"]), str(packet["packet_sha256"])),
        edge_targets=(*subject_target, *archive_target),
    )
    return {
        **run,
        "ok": provider_error is None,
        "replayed": False,
        "run_path": run_path.relative_to(root).as_posix(),
        "golden_leaf_sha256": leaf_sha,
    }


def open_closed_book_forecast(
    root: Path,
    *,
    owner: str,
    store_path: Path,
    decision_id: str | None = None,
    paper_watch_decision_id: str | None = None,
    candidate_leaf: str | None = None,
    benchmark_id: str = "SPY",
    probe_weight: float = 0.05,
    horizon_days: int = 90,
    config: FrontierAgentConfig | None = None,
    agent_result: Mapping[str, Any] | None = None,
    ablation_agent_results: Mapping[str, Mapping[str, Any]] | None = None,
    payoff_forecast_result: Mapping[str, Any] | None = None,
    strategy_experiment_nomination: Mapping[str, Any] | None = None,
    price_rows_by_entity: Mapping[str, tuple[dict[str, Any], ...]] | None = None,
) -> dict[str, Any]:
    """Freeze one episode once, including across concurrent service processes."""

    lock_path = root / "closed_book" / "open.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # ponytail: one global lock matches today's sequential forecast budget; shard by
    # semantic episode identity only if forecast-opening throughput becomes material.
    with lock_path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return _open_closed_book_forecast(
            root,
            owner=owner,
            store_path=store_path,
            decision_id=decision_id,
            paper_watch_decision_id=paper_watch_decision_id,
            candidate_leaf=candidate_leaf,
            benchmark_id=benchmark_id,
            probe_weight=probe_weight,
            horizon_days=horizon_days,
            config=config,
            agent_result=agent_result,
            ablation_agent_results=ablation_agent_results,
            payoff_forecast_result=payoff_forecast_result,
            strategy_experiment_nomination=strategy_experiment_nomination,
            price_rows_by_entity=price_rows_by_entity,
        )


def _recover_sealed_at(
    run: Mapping[str, Any], *, owner: str, store_path: Path,
) -> str | None:
    """Recover a legacy seal only from the immutable stored run leaf."""

    if run.get("sealed_at"):
        return canonical_timestamp(run["sealed_at"], "closed-book sealed_at")
    try:
        leaf = GoldenStore(store_path).head(
            owner, "closed_book_forecast_run", str(run["run_id"]),
        )
    except KeyError:
        return None
    payload = leaf.get("payload") or {}
    if (
        payload.get("run_id") != run.get("run_id")
        or payload.get("run_sha256") != run.get("run_sha256")
    ):
        return None
    return canonical_timestamp(leaf.get("available_at"), "closed-book recovered seal")


def _return_window_binding(
    root: Path, *, run: Mapping[str, Any], contract: Mapping[str, Any],
    points: Mapping[str, tuple[dict[str, Any], ...]], evaluation_at: str,
    owner: str, store_path: Path,
    point_index: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    path = root / "closed_book" / "return_windows" / f"{run['run_id']}.json"
    prior = _read_json(path)
    if prior and isinstance(prior.get("binding"), Mapping):
        binding = dict(prior["binding"])
        if (
            binding.get("schema") == RETURN_WINDOW_BINDING_SCHEMA
            and binding.get("return_window_sha256") == contract.get("return_window_sha256")
        ):
            return binding
    binding = bind_prospective_return_window(
        contract, points=points, as_of=evaluation_at, point_index=point_index,
    )
    if binding["status"] != "bound":
        return binding
    envelope = {
        "schema": "jaggedthoughts-prospective-return-window-binding-envelope-v1",
        "contract": dict(contract), "binding": binding,
    }
    _atomic_json(path, envelope)
    refs = tuple(sorted({
        str(row["source_ref"])
        for row in binding["entry_points"].values()
    }))
    _record_leaf(
        owner=owner, store_path=store_path,
        object_kind="prospective_return_window_binding",
        object_id=f"{run['run_id']}::return-window",
        epoch=str(contract["return_window_sha256"]),
        occurred_at=str(binding["entry_observed_at"]), payload=envelope,
        source_refs=refs,
        edge_targets=_head_target(
            store_path, owner, "closed_book_forecast_run", str(run["run_id"]),
        ),
    )
    return binding


def settle_due_closed_book_forecasts(
    root: Path,
    *,
    owner: str,
    store_path: Path,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Settle every due forecast from cached point-in-time price observations."""

    evaluation_at = canonical_timestamp(as_of or _utc_now(), "closed-book settlement as_of")
    settled: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    runs: list[tuple[dict[str, Any], Path, dict[str, Any] | None]] = []
    for path in sorted((root / "closed_book" / "runs").glob("*.json")):
        run = _read_json(path)
        if not run or run.get("schema") != CLOSED_BOOK_RUN_SCHEMA:
            continue
        settlement_path = root / "closed_book" / "settlements" / f"{run['run_id']}.json"
        runs.append((run, settlement_path, _read_json(settlement_path)))

    unsettled_entity_ids = {
        str(entity_id)
        for run, _settlement_path, prior in runs if not prior
        for entity_id in (
            ((run.get("evidence_packet") or {}).get("entity") or {}).get("entity_id"),
            ((run.get("evidence_packet") or {}).get("benchmark") or {}).get("entity_id"),
        )
        if entity_id
    }
    prices_by_entity = (
        _price_rows_by_entity(root, unsettled_entity_ids, as_of=evaluation_at)
        if unsettled_entity_ids else {}
    )
    price_index = index_return_window_points(
        prices_by_entity, as_of=evaluation_at,
    ) if prices_by_entity else {}

    for run, settlement_path, prior in runs:
        if prior:
            settled.append(prior)
            continue
        packet = dict(run["evidence_packet"])
        entity_id = str((packet.get("entity") or {}).get("entity_id") or "")
        benchmark_id = str((packet.get("benchmark") or {}).get("entity_id") or "")
        sealed_at = _recover_sealed_at(run, owner=owner, store_path=store_path)
        if sealed_at is None:
            pending.append({"run_id": run["run_id"], "reason": "seal_unrecoverable"})
            continue
        contract = dict(
            (run.get("settlement_contract") or {}).get("prospective_return_window") or {}
        )
        if not contract:
            contract = compile_prospective_return_window(
                sealed_at=sealed_at, horizon_days=int(run["horizon_days"]),
                entity_ids=(entity_id, benchmark_id),
                transaction_cost_bps=float(
                    (run.get("settlement_contract") or {}).get("transaction_cost_bps") or 0.0
                ),
            )
        points = {
            entity_id: prices_by_entity.get(entity_id.upper(), ()),
            benchmark_id: prices_by_entity.get(benchmark_id.upper(), ()),
        }
        binding = _return_window_binding(
            root, run=run, contract=contract, points=points,
            evaluation_at=evaluation_at, owner=owner, store_path=store_path,
            point_index=price_index,
        )
        if binding["status"] != "bound":
            pending.append({"run_id": run["run_id"], "reason": "entry_price_unavailable"})
            continue
        window = settle_prospective_return_window(
            contract, binding, points=points, as_of=evaluation_at,
            point_index=price_index,
        )
        if window["status"] != "settled":
            reason = (
                "horizon_not_reached"
                if timestamp_key(str(binding["scheduled_exit_at"])) > timestamp_key(evaluation_at)
                else "outcome_price_unavailable"
            )
            pending.append({"run_id": run["run_id"], "reason": reason})
            continue
        entity_start = dict(binding["entry_points"][entity_id])
        benchmark_start = dict(binding["entry_points"][benchmark_id])
        entity_end = dict(window["exit_points"][entity_id])
        benchmark_end = dict(window["exit_points"][benchmark_id])
        entity_return = float(window["returns"][entity_id])
        benchmark_return = float(window["returns"][benchmark_id])
        active_return = entity_return - benchmark_return
        underperformed = 1.0 if active_return < 0 else 0.0
        scores: list[dict[str, Any]] = []
        for candidate in run.get("candidate_forecasts") or []:
            predicted = dict(candidate.get("predicted_values") or {})
            weight = float(candidate.get("target_weight") or 0.0)
            book_return = weight * entity_return
            active_contribution = weight * active_return
            score = {
                "candidate_id": candidate["candidate_id"],
                "forecast_sha256": candidate["forecast_sha256"],
                "target_weight": weight,
                "active_return_absolute_error": abs(float(predicted["active_return"]) - active_return),
                "underperformance_brier": (
                    float(predicted["underperformance_event"]) - underperformed
                ) ** 2,
                "book_return_after_cost": book_return,
                "active_return_contribution_after_cost": active_contribution,
                "benchmark_return": benchmark_return,
                "book_excess_return": book_return - benchmark_return,
            }
            intervals = dict(candidate.get("prediction_intervals") or {})
            if intervals:
                active_interval = dict(intervals["active_return"])
                probability_interval = dict(intervals["underperformance_probability"])
                active_low = float(active_interval["low"])
                active_high = float(active_interval["high"])
                probability_low = float(probability_interval["low"])
                probability_high = float(probability_interval["high"])
                score["active_return_interval"] = {
                    "low": active_low,
                    "high": active_high,
                    "contains_actual": active_low <= active_return <= active_high,
                    "miss_distance": max(active_low - active_return, active_return - active_high, 0.0),
                    "width": active_high - active_low,
                }
                brier_endpoints = (
                    (probability_low - underperformed) ** 2,
                    (probability_high - underperformed) ** 2,
                )
                score["underperformance_brier_interval"] = {
                    "low": min(brier_endpoints),
                    "high": max(brier_endpoints),
                }
            scores.append(score)
        evaluation_integrity = compile_evaluation_integrity_receipt(
            temporal_design="prospective_sealed",
            generation_processes=_generation_processes(list(run.get("candidate_forecasts") or [])),
            seal_rows=tuple({
                "episode_id": f"{run['episode_id']}:{row['candidate_id']}",
                "sealed_at": sealed_at,
                "episode_start_at": str(binding["entry_observed_at"]),
            } for row in run.get("candidate_forecasts") or []),
            maturity_rows=({
                "episode_id": str(run["episode_id"]),
                "episode_end_at": str(window["exit_observed_at"]),
                "outcome_available_at": max(
                    str(entity_end["available_at"]), str(benchmark_end["available_at"]),
                ),
                "evaluated_at": evaluation_at,
            },),
        )
        body = {
            "schema": CLOSED_BOOK_SETTLEMENT_SCHEMA,
            "settlement_id": f"{run['run_id']}::settlement",
            "run_id": run["run_id"],
            "run_sha256": run["run_sha256"],
            "episode_id": run["episode_id"],
            "inference_block_id": _inference_block_identity(packet),
            "evaluated_at": evaluation_at,
            "prospective_return_window": contract,
            "return_window_binding": binding,
            "return_window_settlement": window,
            "entity_start_price": entity_start,
            "benchmark_start_price": benchmark_start,
            "entity_end_price": entity_end,
            "benchmark_end_price": benchmark_end,
            "actual_values": {
                "entity_return": entity_return,
                "benchmark_return": benchmark_return,
                "active_return": active_return,
                "underperformance_event": underperformed,
            },
            "candidate_scores": scores,
            "evaluation_integrity": evaluation_integrity,
            "paper_policy_authority": False,
            "capital_authority": False,
        }
        settlement = {**body, "settlement_sha256": stable_sha256(body)}
        _atomic_json(settlement_path, settlement)
        leaf_sha = _record_leaf(
            owner=owner,
            store_path=store_path,
            object_kind="closed_book_forecast_settlement",
            object_id=str(body["settlement_id"]),
            epoch=str(run["run_sha256"]),
            occurred_at=evaluation_at,
            payload=settlement,
            source_refs=(
                str(run["run_id"]), entity_start["source_ref"], benchmark_start["source_ref"],
                entity_end["source_ref"], benchmark_end["source_ref"],
            ),
            edge_targets=tuple(
                (target_sha256, "settles")
                for target_sha256, _ in _head_target(
                    store_path, owner, "closed_book_forecast_run", str(run["run_id"]),
                )
            ),
        )
        settled.append({**settlement, "golden_leaf_sha256": leaf_sha})
    return {
        "schema": "jaggedthoughts-closed-book-settlement-run-v1",
        "evaluated_at": evaluation_at,
        "settled_count": len(settled),
        "pending_count": len(pending),
        "settlements": settled,
        "pending": pending,
        "ok": True,
        "capital_authority": False,
    }


def closed_book_price_refresh_entity_ids(
    root: Path, *, as_of: str | None = None,
) -> list[str]:
    """Return identities needed to bind an entry or observe a due exit."""

    evaluated = canonical_timestamp(as_of or _utc_now(), "closed-book price refresh as_of")
    base = root / "closed_book"
    settled = {
        str(row.get("run_id") or "")
        for path in (base / "settlements").glob("*.json")
        if (row := _read_json(path))
    }
    entity_ids: set[str] = set()
    for path in sorted((base / "runs").glob("*.json")):
        run = _read_json(path)
        if (
            not run
            or run.get("schema") != CLOSED_BOOK_RUN_SCHEMA
            or str(run.get("run_id") or "") in settled
        ):
            continue
        binding = dict((_read_json(
            base / "return_windows" / f"{run['run_id']}.json"
        ) or {}).get("binding") or {})
        if (
            binding.get("status") == "bound"
            and timestamp_key(evaluated) < timestamp_key(str(binding["scheduled_exit_at"]))
        ):
            continue
        packet = run.get("evidence_packet") or {}
        for key in ("entity", "benchmark"):
            entity_id = str((packet.get(key) or {}).get("entity_id") or "").upper()
            if entity_id:
                entity_ids.add(entity_id)
    return sorted(entity_ids)


def overlap_cluster_ids(
    settlements: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> dict[str, str]:
    """Cluster connected overlapping tradable windows into one inference block."""

    intervals: list[tuple[datetime, datetime, str, str, str]] = []
    for row in settlements:
        binding = row.get("return_window_binding") or {}
        outcome = row.get("return_window_settlement") or {}
        start = str(binding.get("entry_observed_at") or "")
        end = str(outcome.get("exit_observed_at") or "")
        run_id = str(row.get("run_id") or "")
        if start and end and run_id:
            intervals.append((timestamp_key(start), timestamp_key(end), start, end, run_id))
    intervals.sort(key=lambda row: (row[0], row[1], row[4]))
    groups: list[list[tuple[datetime, datetime, str, str, str]]] = []
    group_end: datetime | None = None
    for interval in intervals:
        if group_end is None or interval[0] > group_end:
            groups.append([interval])
            group_end = interval[1]
        else:
            groups[-1].append(interval)
            group_end = max(group_end, interval[1])
    result: dict[str, str] = {}
    for group in groups:
        block_id = stable_sha256({
            "identity": "overlapping_tradable_return_window_component",
            "start_at": min(row[2] for row in group),
            "end_at": max(row[3] for row in group),
            "run_ids": sorted(row[4] for row in group),
        })
        result.update({row[4]: block_id for row in group})
    return result


def _canonical_episode_runs(
    runs: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> tuple[tuple[dict[str, Any], ...], dict[str, str]]:
    """Keep the earliest immutable run when concurrent opens share one identity."""

    canonical: list[dict[str, Any]] = []
    owner_by_identity: dict[str, str] = {}
    duplicate_of: dict[str, str] = {}
    for run in sorted(runs, key=lambda row: (
        str(row.get("opened_at") or ""), str(row.get("sealed_at") or ""),
        str(row.get("run_id") or ""),
    )):
        run_id = str(run.get("run_id") or "")
        identity = str(run.get("episode_identity_sha256") or "")
        prior = owner_by_identity.get(identity) if identity else None
        if prior:
            duplicate_of[run_id] = prior
        else:
            canonical.append(run)
            if identity:
                owner_by_identity[identity] = run_id
    return tuple(canonical), duplicate_of


def _scoreboard(settlements: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for settlement in settlements:
        for score in settlement.get("candidate_scores") or []:
            grouped.setdefault(str(score["candidate_id"]), []).append(score)
    rows: list[dict[str, Any]] = []
    for candidate_id, scores in sorted(grouped.items()):
        rows.append({
            "candidate_id": candidate_id,
            "episode_count": len(scores),
            "mean_active_return_absolute_error": sum(
                float(row["active_return_absolute_error"]) for row in scores
            ) / len(scores),
            "mean_underperformance_brier": sum(
                float(row["underperformance_brier"]) for row in scores
            ) / len(scores),
            "mean_book_excess_return": sum(
                float(row["book_excess_return"]) for row in scores
            ) / len(scores),
            "mean_active_return_contribution_after_cost": sum(
                float(row.get("active_return_contribution_after_cost", row["book_excess_return"]))
                for row in scores
            ) / len(scores),
            "primary_policy_outcome": "active_return_contribution_after_cost",
        })
    block_count = len(set(overlap_cluster_ids(settlements).values()))
    return {
        "candidate_rows": rows,
        "inference_block_count": block_count,
        "minimum_inference_blocks": 8,
        "comparison_ready": block_count >= 8 and len(rows) >= 2,
        "block_identity": "connected_components_of_overlapping_tradable_return_windows",
        "authority": "descriptive" if block_count else "pending_outcomes",
    }


def _forecast_learning(
    runs: tuple[dict[str, Any], ...],
    settlements: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    """Compile exact-bundle forecast evidence without inventing component credit."""

    settlement_by_run = {
        str(row.get("run_id") or ""): row for row in settlements if row.get("run_id")
    }
    statistical_blocks = overlap_cluster_ids(settlements)
    bundle_rows: dict[str, list[dict[str, Any]]] = {}
    disagreements: list[dict[str, Any]] = []
    for run in runs:
        packet = dict(run.get("evidence_packet") or {})
        forecasts = tuple(
            row for row in run.get("candidate_forecasts") or () if isinstance(row, Mapping)
        )
        if not packet or not forecasts:
            continue
        entity_id = str((packet.get("entity") or {}).get("entity_id") or "")
        benchmark_id = str((packet.get("benchmark") or {}).get("entity_id") or "")
        subject_kind = str((packet.get("subject") or {}).get("kind") or "paper_decision")
        horizon_days = int(run.get("horizon_days") or packet.get("horizon_days") or 0)
        predictions = [float((row.get("predicted_values") or {})["active_return"]) for row in forecasts]
        prediction_mean = sum(predictions) / len(predictions)
        prediction_sd = math.sqrt(
            sum((value - prediction_mean) ** 2 for value in predictions) / len(predictions)
        )
        high = max(forecasts, key=lambda row: float((row.get("predicted_values") or {})["active_return"]))
        low = min(forecasts, key=lambda row: float((row.get("predicted_values") or {})["active_return"]))
        settlement = settlement_by_run.get(str(run.get("run_id") or ""))
        disagreements.append({
            "run_id": run.get("run_id"),
            "episode_id": run.get("episode_id"),
            "entity_id": entity_id,
            "subject_kind": subject_kind,
            "benchmark_id": benchmark_id,
            "horizon_days": horizon_days,
            "opened_at": run.get("opened_at"),
            "end_at": run.get("end_at"),
            "status": "settled" if settlement else "pending",
            "forecast_count": len(forecasts),
            "active_return_mean": prediction_mean,
            "active_return_standard_deviation": prediction_sd,
            "active_return_range": max(predictions) - min(predictions),
            "highest_forecast": {
                "candidate_id": high.get("candidate_id"),
                "active_return": max(predictions),
            },
            "lowest_forecast": {
                "candidate_id": low.get("candidate_id"),
                "active_return": min(predictions),
            },
        })
        score_by_candidate = {
            str(row.get("candidate_id") or ""): row
            for row in (settlement or {}).get("candidate_scores") or ()
            if isinstance(row, Mapping)
        }
        for forecast in forecasts:
            mechanism_ids = tuple(sorted({
                str(value) for value in forecast.get("mechanism_ids") or () if str(value)
            }))
            bundle = {
                "subject_kind": subject_kind,
                "model_family": str(forecast.get("model_family") or "unspecified"),
                "version": str(forecast.get("version") or "1"),
                "mechanism_ids": list(mechanism_ids),
                "observable_ids": ["active_return", "underperformance_event"],
                "horizon_days": horizon_days,
            }
            bundle_sha = stable_sha256(bundle)
            score = score_by_candidate.get(str(forecast.get("candidate_id") or ""))
            row = {
                "bundle_sha256": bundle_sha,
                "bundle": bundle,
                "candidate_id": forecast.get("candidate_id"),
                "forecast_sha256": forecast.get("forecast_sha256"),
                "run_id": run.get("run_id"),
                "episode_id": run.get("episode_id"),
                "inference_block_id": statistical_blocks.get(str(run.get("run_id") or "")),
                "entity_id": entity_id,
                "subject_kind": subject_kind,
                "benchmark_id": benchmark_id,
                "packet_sha256": packet.get("packet_sha256"),
                "opened_at": run.get("opened_at"),
                "end_at": run.get("end_at"),
                "status": "settled" if score else "pending",
                "predicted_values": dict(forecast.get("predicted_values") or {}),
                "target_weight": float(forecast.get("target_weight") or 0.0),
                "settled_scores": dict(score) if score else None,
            }
            bundle_rows.setdefault(bundle_sha, []).append(row)

    bundles = []
    for bundle_sha, rows in sorted(bundle_rows.items()):
        settled = [row for row in rows if row["settled_scores"]]
        entities = sorted({row["entity_id"] for row in settled})
        blocks = sorted({str(row["inference_block_id"]) for row in settled})
        def settled_mean(metric: str) -> float | None:
            values = [float(row["settled_scores"][metric]) for row in settled]
            return sum(values) / len(values) if values else None
        bundles.append({
            "bundle_sha256": bundle_sha,
            "bundle": rows[0]["bundle"],
            "episode_count": len(rows),
            "settled_count": len(settled),
            "pending_count": len(rows) - len(settled),
            "settled_entity_ids": entities,
            "settled_entity_count": len(entities),
            "inference_block_count": len(blocks),
            "cross_entity_observed": len(entities) > 1,
            "comparison_ready": len(blocks) >= 8,
            "mean_active_return_absolute_error": settled_mean("active_return_absolute_error"),
            "mean_underperformance_brier": settled_mean("underperformance_brier"),
            "mean_book_excess_return": settled_mean("book_excess_return"),
            "episodes": sorted(rows, key=lambda row: (str(row["opened_at"]), str(row["episode_id"]))),
        })
    disagreements.sort(
        key=lambda row: (-float(row["active_return_range"]), str(row["end_at"]), str(row["entity_id"]))
    )
    body = {
        "schema": "jaggedthoughts-forecast-learning-memory-v1",
        "identity": "exact_mechanism_bundle_by_horizon_and_observable_contract",
        "bundle_count": len(bundles),
        "settled_bundle_count": sum(bool(row["settled_count"]) for row in bundles),
        "cross_entity_bundle_count": sum(bool(row["cross_entity_observed"]) for row in bundles),
        "comparison_ready_bundle_count": sum(bool(row["comparison_ready"]) for row in bundles),
        "bundles": bundles,
        "disagreement_queue": disagreements,
        "credit_boundary": (
            "A settlement updates the exact mechanism bundle that issued the forecast. "
            "It does not identify the contribution of one mechanism inside a bundle."
        ),
        "transfer_boundary": (
            "Cross-entity reuse is descriptive until the same bundle has comparable settled "
            "inference blocks and survives the world-model tournament."
        ),
        "disagreement_boundary": (
            "Forecast dispersion identifies a future discriminator; it is neither confidence "
            "nor expected return."
        ),
        "capital_authority": False,
    }
    return {**body, "forecast_learning_sha256": stable_sha256(body)}


def _world_model_tournament(
    runs: tuple[dict[str, Any], ...],
    settlements: tuple[dict[str, Any], ...],
) -> dict[str, Any] | None:
    """Lower one comparable settled cohort into the shared world-model contract."""

    run_by_id = {str(row.get("run_id") or ""): row for row in runs}
    statistical_blocks = overlap_cluster_ids(settlements)
    cohorts: dict[
        tuple[int, tuple[str, ...], str], list[tuple[dict[str, Any], dict[str, Any]]]
    ] = {}
    for settlement in settlements:
        run = run_by_id.get(str(settlement.get("run_id") or ""))
        if not run or str(settlement.get("run_id") or "") not in statistical_blocks:
            continue
        candidate_ids = tuple(sorted(
            str(row.get("candidate_id") or "")
            for row in run.get("candidate_forecasts") or []
            if row.get("candidate_id")
        ))
        if not candidate_ids:
            continue
        process_bundle = dict((run.get("provider") or {}).get("process_bundle") or {})
        process_bundle_sha = str(process_bundle.get("process_bundle_sha256") or "")
        if not process_bundle_sha:
            process_bundle_sha = f"legacy:{stable_sha256(run.get('provider') or {})}"
        cohorts.setdefault((
            int(run.get("horizon_days") or 0), candidate_ids, process_bundle_sha,
        ), []).append(
            (run, settlement)
        )
    if not cohorts:
        return None
    cohort_key, rows = max(
        cohorts.items(),
        key=lambda item: (
            len(item[1]),
            max(str(pair[1].get("evaluated_at") or "") for pair in item[1]),
            item[0],
        ),
    )
    horizon_days, candidate_ids, process_bundle_sha = cohort_key
    first_candidates = {
        str(row["candidate_id"]): row
        for row in rows[0][0].get("candidate_forecasts") or []
    }
    models = tuple(WorldModelCandidate(
        model_id=candidate_id,
        version=str(first_candidates[candidate_id].get("version") or "1"),
        model_family=str(first_candidates[candidate_id].get("model_family") or "unspecified"),
        trial_family_id=str(
            first_candidates[candidate_id].get("trial_family_id") or f"{candidate_id}-v1"
        ),
        mechanism_ids=tuple(
            str(value) for value in first_candidates[candidate_id].get("mechanism_ids") or ()
        ),
        linked_observable_ids=(),
        source_refs=(
            f"producer:{candidate_id}",
            f"producer-mode:{(first_candidates[candidate_id].get('producer') or {}).get('mode')}",
        ),
        generation_process=(
            "subscription_llm"
            if str((first_candidates[candidate_id].get("producer") or {}).get("mode") or "") == "direct_agent"
            else "deterministic"
            if str((first_candidates[candidate_id].get("producer") or {}).get("mode") or "") == "deterministic_program"
            else "unknown"
        ),
    ) for candidate_id in candidate_ids)
    episodes: list[BacktestEpisode] = []
    forecasts: list[WorldModelForecast] = []
    for run, settlement in rows:
        actual = dict(settlement["actual_values"])
        packet = dict(run["evidence_packet"])
        episodes.append(BacktestEpisode(
            episode_id=str(run["episode_id"]),
            inference_block_id=statistical_blocks[str(run["run_id"])],
            entity_id=str((packet.get("entity") or {}).get("entity_id") or ""),
            start_at=str(settlement["return_window_binding"]["entry_observed_at"]),
            end_at=str(settlement["return_window_settlement"]["exit_observed_at"]),
            outcome_available_at=str(settlement["evaluated_at"]),
            starting_weight=0.0,
            asset_return=float(actual["entity_return"]),
            benchmark_return=float(actual["benchmark_return"]),
            cash_return=float(run["settlement_contract"].get("cash_return") or 0.0),
            actual_values={
                "active_return": float(actual["active_return"]),
                "underperformance_event": float(actual["underperformance_event"]),
            },
            source_refs=(
                str(settlement["entity_end_price"]["source_ref"]),
                str(settlement["benchmark_end_price"]["source_ref"]),
                str(run["run_id"]),
            ),
        ))
        for candidate in run.get("candidate_forecasts") or []:
            forecasts.append(WorldModelForecast(
                model_id=str(candidate["candidate_id"]),
                episode_id=str(run["episode_id"]),
                trained_through=str(run["opened_at"]),
                issued_at=str(run.get("sealed_at") or run["opened_at"]),
                predicted_values={
                    "active_return": float(candidate["predicted_values"]["active_return"]),
                    "underperformance_event": float(
                        candidate["predicted_values"]["underperformance_event"]
                    ),
                },
                target_weight=float(candidate.get("target_weight") or 0.0),
                source_refs=tuple(sorted({
                    str(packet["packet_sha256"]), str(candidate["forecast_sha256"]),
                    *(str(value) for value in candidate.get("source_refs") or ()),
                })),
            ))
    as_of = max(str(settlement["evaluated_at"]) for _, settlement in rows)
    result = evaluate_world_model_tournament(
        tournament_id=f"closed-book::{horizon_days}d::{stable_sha256(cohort_key)[:12]}",
        owner="jaggedthoughts-closed-book-ledger",
        as_of=as_of,
        mode="prospective_shadow",
        baseline_model_id="no_active_edge_control",
        observables=(
            ObservableSpec("active_return", "decimal_return", "absolute", 0.10, 0.70),
            ObservableSpec(
                "underperformance_event", "probability", "brier", 1.0, 0.30,
            ),
        ),
        models=models,
        episodes=tuple(episodes),
        forecasts=tuple(forecasts),
        transaction_cost_bps=float(rows[0][0]["settlement_contract"]["transaction_cost_bps"]),
        declared_trial_family_ids=tuple(model.trial_family_id for model in models),
        source_refs=tuple(
            sorted({
                str(run["run_id"]) for run, _ in rows
            } | {
                str(settlement["settlement_sha256"]) for _, settlement in rows
            })
        ),
        min_inference_blocks=8,
        periods_per_year=365.25 / max(1, horizon_days),
    )
    selected_process = dict((rows[0][0].get("provider") or {}).get("process_bundle") or {})
    requires_model_identity = any(
        str((candidate.get("producer") or {}).get("mode") or "") == "direct_agent"
        for candidate in rows[0][0].get("candidate_forecasts") or ()
    )
    process_identity_complete = (
        not requires_model_identity or selected_process.get("model_identity_complete") is True
    )
    return {
        **result,
        "engine_evidence_eligible": bool(
            result.get("inference_sufficient") and process_identity_complete
        ),
        "process_identity_complete": process_identity_complete,
        "promotion_blockers": (
            [] if process_identity_complete else ["subscription_resolved_model_identity_unavailable"]
        ),
        "cohort": {
            "horizon_days": horizon_days,
            "candidate_ids": list(candidate_ids),
            "process_bundle_sha256": process_bundle_sha,
            "process_bundle": selected_process,
            "included_settlement_count": len(rows),
            "excluded_settlement_count": len(settlements) - len(rows),
        },
        "temporal_note": (
            "trained_through denotes the producer's issue-time information boundary; "
            "the frontier producer's parametric source attribution remains unmeasured."
        ),
    }


def closed_book_status(root: Path) -> dict[str, Any]:
    """Project prospective runs, settlements, and temporal-interpretation rules."""

    runs: list[dict[str, Any]] = []
    for path in (root / "closed_book" / "runs").glob("*.json"):
        row = _read_json(path)
        if row and row.get("schema") == CLOSED_BOOK_RUN_SCHEMA:
            runs.append({**row, "run_path": path.relative_to(root).as_posix()})
    runs.sort(key=lambda row: (str(row.get("opened_at") or ""), str(row.get("run_id") or "")), reverse=True)
    settlements: list[dict[str, Any]] = []
    for path in (root / "closed_book" / "settlements").glob("*.json"):
        row = _read_json(path)
        if row and row.get("schema") == CLOSED_BOOK_SETTLEMENT_SCHEMA:
            settlements.append({**row, "settlement_path": path.relative_to(root).as_posix()})
    settlements.sort(key=lambda row: str(row.get("evaluated_at") or ""), reverse=True)
    evidence_runs, duplicate_of = _canonical_episode_runs(runs)
    evidence_run_ids = {str(row.get("run_id") or "") for row in evidence_runs}
    evidence_settlements = tuple(
        row for row in settlements if str(row.get("run_id") or "") in evidence_run_ids
    )
    settled_ids = {str(row.get("run_id") or "") for row in evidence_settlements}
    compact_runs = []
    for run in runs:
        run_id = str(run.get("run_id") or "")
        subject = dict(run.get("subject") or {})
        entity = dict((run.get("evidence_packet") or {}).get("entity") or {})
        binding = dict((_read_json(
            root / "closed_book" / "return_windows" / f"{run_id}.json"
        ) or {}).get("binding") or {})
        ablation = dict(run.get("underwriting_information_ablation") or {})
        compact_runs.append({
            "run_id": run_id,
            "subject": {
                "kind": subject.get("kind"),
                "subject_id": subject.get("subject_id"),
            },
            "entity": {
                "entity_id": entity.get("entity_id"),
                "name": entity.get("name"),
            },
            "end_at": (
                binding.get("scheduled_exit_at")
                if binding.get("status") == "bound" else
                run.get("end_at") if run_id in settled_ids else None
            ),
            "scheduled_end_at": (
                binding.get("scheduled_exit_at")
                if binding.get("status") == "bound" else run.get("end_at")
            ),
            "status": (
                "duplicate_episode_excluded" if run_id in duplicate_of else
                "settled" if run_id in settled_ids else
                "awaiting_horizon" if binding.get("status") == "bound" else
                "awaiting_postseal_entry_binding"
            ),
            "canonical_run_id": duplicate_of.get(run_id),
            "underwriting_ablation": ({
                "status": ablation.get("status"),
                "arms": [
                    row.get("role") for row in ablation.get("arms") or ()
                    if isinstance(row, Mapping) and row.get("role")
                ],
            } if ablation else None),
            "run_path": run.get("run_path"),
        })
    evidence_runs = tuple(sorted(
        evidence_runs,
        key=lambda row: (str(row.get("opened_at") or ""), str(row.get("run_id") or "")),
        reverse=True,
    ))
    latest = evidence_runs[0] if evidence_runs else None
    world_model = _world_model_tournament(evidence_runs, evidence_settlements)
    forecast_learning = _forecast_learning(evidence_runs, evidence_settlements)
    underwriting_ablation = compile_underwriting_ablation_status(
        evidence_runs, evidence_settlements,
        inference_block_ids=overlap_cluster_ids(evidence_settlements),
    )
    return {
        "schema": CLOSED_BOOK_STATUS_SCHEMA,
        "enabled": True,
        "run_count": len(runs),
        "evidence_eligible_run_count": len(evidence_runs),
        "duplicate_run_count": len(duplicate_of),
        "duplicate_runs": [
            {"run_id": run_id, "canonical_run_id": canonical_run_id}
            for run_id, canonical_run_id in sorted(duplicate_of.items())
        ],
        "pending_count": sum(
            str(row.get("run_id") or "") not in settled_ids for row in evidence_runs
        ),
        "settled_count": len(evidence_settlements),
        "raw_settled_count": len(settlements),
        "runs": compact_runs,
        "latest_run": latest,
        "latest_settlement": evidence_settlements[0] if evidence_settlements else None,
        "evaluation_integrity": (
            (evidence_settlements[0].get("evaluation_integrity") if evidence_settlements else None)
            or ((latest or {}).get("evaluation_integrity") if latest else None)
        ),
        "scoreboard": _scoreboard(evidence_settlements),
        "world_model_tournament": world_model,
        "forecast_learning": forecast_learning,
        "underwriting_ablation": underwriting_ablation,
        "temporal_policy": {
            "prospective_shadow": "eligible to evaluate the full frozen engine after settlement",
            "historical_deterministic_replay": "diagnostic until selection trials and later prospective evidence are counted",
            "historical_frontier_replay": "diagnostic only unless an external clean control identifies temporal leakage",
            "web_disabled_is_not_training_memory_isolation": True,
        },
        "capital_authority": False,
    }


__all__ = [
    "CLOSED_BOOK_RUN_SCHEMA",
    "CLOSED_BOOK_SETTLEMENT_SCHEMA",
    "CLOSED_BOOK_STATUS_SCHEMA",
    "closed_book_agent_output_schema",
    "closed_book_price_refresh_entity_ids",
    "closed_book_status",
    "open_closed_book_forecast",
    "settle_due_closed_book_forecasts",
]
