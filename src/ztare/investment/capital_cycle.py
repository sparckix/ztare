"""Recurring paper-capital operating contract for JaggedThoughts Capital.

The cycle does not invent another security score. It joins the latest discovery
population, operator decisions, strategy/research coverage, portfolio state,
and prospective forecast ledger into one daily answer: deploy paper risk, keep
cash, research, repair evidence, or await settlement.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key
from .institutional_learning import compile_law_policy_influence
from .golden_store import GoldenStore
from .market_state_forecast import market_state_cycle_due
from .paper_watch import paper_watch_decisions
from .portfolio_policy import PRIMARY_HORIZON_DAYS, portfolio_policy_status
from .point_in_time_replay import sealed_walk_forward_status
from .strategy_dual_outcome import compile_strategy_dual_outcome_episodes
from .strategy_law_induction import (
    CAUSAL_LAW_INFLUENCE_SET_SCHEMA,
    STRATEGY_LAW_INDUCTION_SCHEMA,
    compile_causal_law_target_influence,
)
from .strategy_learning import STRATEGY_MOVE_LIBRARY_SCHEMA


CAPITAL_CYCLE_POLICY_SCHEMA = "jaggedthoughts-capital-cycle-policy-v1"
OPPORTUNITY_BOOK_SCHEMA = "jaggedthoughts-opportunity-book-v1"
CAPITAL_CYCLE_RUN_SCHEMA = "jaggedthoughts-capital-cycle-run-v1"
CAPITAL_CYCLE_STATUS_SCHEMA = "jaggedthoughts-capital-cycle-status-v1"
SETTLEMENT_READINESS_SCHEMA = "jaggedthoughts-settlement-readiness-v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def default_capital_cycle_policy() -> dict[str, Any]:
    """Return the editable default cadence, forecast budget, and risk ceiling."""

    return {
        "schema": CAPITAL_CYCLE_POLICY_SCHEMA,
        "enabled": True,
        "poll_seconds": 300,
        "include_operator_drafts_in_forecasts": True,
        "include_qualified_discovery_in_forecasts": True,
        "discovery_benchmark_id": "SPY",
        "discovery_probe_weight": 0.05,
        "max_new_forecast_episodes_per_cycle": 4,
        "forecast_windows": [
            {"horizon_days": 21, "cadence_days": 21},
            {"horizon_days": 90, "cadence_days": 90},
            {"horizon_days": 365, "cadence_days": 365},
        ],
        "market_state_forecast_windows": [
            {"horizon_days": 90, "cadence_days": 7},
            {"horizon_days": 365, "cadence_days": 30},
        ],
        "strategy_event_archive_refresh_cadence_days": 1,
        "max_research_queue": 10,
        "portfolio_policy_horizon_days": PRIMARY_HORIZON_DAYS,
        "portfolio_policy_gross_weight": 0.50,
        "portfolio_policy_max_position_weight": 0.15,
        "portfolio_policy_diagnostic_risk_aversion": 3.0,
        "paper_watch_auto_enrollment": {
            "enabled": False,
            "actor_id": "capital-cycle-paper-watch-policy-v1",
            "max_new_per_cycle": 4,
            "scope": "current_eligible_zero_weight_only",
        },
        "kernel_removal_trial": {
            "enabled": True,
            "horizon_days": 90,
            "maximum_independent_blocks": 8,
        },
        "risk": {
            "max_gross_paper_weight": 0.80,
            "max_single_name_weight": 0.10,
            "minimum_cash_weight": 0.20,
        },
        "authority": "paper_shadow",
    }


def load_capital_cycle_policy(path: str | Path) -> dict[str, Any]:
    """Load and validate one operator-editable capital-cycle policy."""

    source = Path(path).expanduser().resolve()
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping) or raw.get("schema") != CAPITAL_CYCLE_POLICY_SCHEMA:
        raise ValueError(f"capital-cycle policy schema must be {CAPITAL_CYCLE_POLICY_SCHEMA}")
    policy = dict(raw)
    if int(policy.get("poll_seconds") or 0) < 5:
        raise ValueError("capital-cycle poll_seconds must be at least five")
    maximum = int(policy.get("max_new_forecast_episodes_per_cycle") or 0)
    if maximum < 0 or maximum > 20:
        raise ValueError("capital-cycle forecast budget must be in [0, 20]")
    probe_weight = float(policy.get("discovery_probe_weight") or 0.05)
    if not 0 < probe_weight <= 0.25:
        raise ValueError("capital-cycle discovery_probe_weight must be in (0, 0.25]")
    windows = policy.get("forecast_windows")
    if not isinstance(windows, list) or not windows:
        raise ValueError("capital-cycle policy needs forecast_windows")
    normalized_windows: list[dict[str, int]] = []
    for row in windows:
        if not isinstance(row, Mapping):
            raise ValueError("capital-cycle forecast windows must be objects")
        horizon = int(row.get("horizon_days") or 0)
        cadence = int(row.get("cadence_days") or 0)
        if not 7 <= horizon <= 730 or cadence < horizon:
            raise ValueError("forecast horizon must be [7,730] and cadence cannot overlap it")
        normalized_windows.append({"horizon_days": horizon, "cadence_days": cadence})
    market_windows = policy.get("market_state_forecast_windows") or []
    if not isinstance(market_windows, list):
        raise ValueError("market-state forecast windows must be a list")
    normalized_market_windows: list[dict[str, int]] = []
    for row in market_windows:
        if not isinstance(row, Mapping):
            raise ValueError("market-state forecast windows must be objects")
        horizon = int(row.get("horizon_days") or 0)
        cadence = int(row.get("cadence_days") or 0)
        if horizon not in {90, 365} or not 1 <= cadence <= horizon:
            raise ValueError("market-state forecasts require 90/365-day horizons and cadence in [1, horizon]")
        normalized_market_windows.append({"horizon_days": horizon, "cadence_days": cadence})
    strategy_event_cadence = int(
        policy.get("strategy_event_archive_refresh_cadence_days") or 1
    )
    if not 1 <= strategy_event_cadence <= 7:
        raise ValueError("strategy-event archive cadence must be in [1, 7] days")
    risk = dict(policy.get("risk") or {})
    gross = float(risk.get("max_gross_paper_weight") or 0)
    single = float(risk.get("max_single_name_weight") or 0)
    cash = float(risk.get("minimum_cash_weight") or 0)
    if not 0 < single <= gross <= 1 or not 0 <= cash < 1 or gross > 1 - cash + 1e-12:
        raise ValueError("capital-cycle risk ceilings are incompatible")
    policy_horizon = int(
        policy.get("portfolio_policy_horizon_days") or PRIMARY_HORIZON_DAYS
    )
    policy_gross = float(policy.get("portfolio_policy_gross_weight") or 0.50)
    policy_maximum = float(policy.get("portfolio_policy_max_position_weight") or 0.15)
    policy_risk_aversion = float(
        policy.get("portfolio_policy_diagnostic_risk_aversion", 3.0)
    )
    if policy_horizon not in {21, 90, 365} or not 0 < policy_maximum <= policy_gross <= 1:
        raise ValueError("portfolio-policy horizon or weight bounds are invalid")
    if not 0 <= policy_risk_aversion <= 100:
        raise ValueError("portfolio-policy diagnostic risk aversion must be in [0, 100]")
    watch_enrollment = dict(policy.get("paper_watch_auto_enrollment") or {})
    watch_limit = int(watch_enrollment.get("max_new_per_cycle") or 0)
    if not 0 <= watch_limit <= 20:
        raise ValueError("paper-watch auto-enrollment budget must be in [0, 20]")
    watch_scope = str(
        watch_enrollment.get("scope") or "current_eligible_zero_weight_only"
    )
    if watch_scope != "current_eligible_zero_weight_only":
        raise ValueError("paper-watch auto-enrollment permits current eligible zero-weight watches only")
    watch_actor = str(
        watch_enrollment.get("actor_id") or "capital-cycle-paper-watch-policy-v1"
    ).strip()
    if not watch_actor:
        raise ValueError("paper-watch auto-enrollment requires an actor_id")
    removal = dict(policy.get("kernel_removal_trial") or {})
    removal_horizon = int(removal.get("horizon_days") or 90)
    removal_maximum = int(removal.get("maximum_independent_blocks") or 8)
    if (
        removal_horizon not in {row["horizon_days"] for row in normalized_windows}
        or not 1 <= removal_maximum <= 40
    ):
        raise ValueError("kernel removal trial requires a declared horizon and 1-40 blocks")
    body = {
        **policy,
        "forecast_windows": normalized_windows,
        "market_state_forecast_windows": normalized_market_windows,
        "strategy_event_archive_refresh_cadence_days": strategy_event_cadence,
        "portfolio_policy_horizon_days": policy_horizon,
        "portfolio_policy_gross_weight": policy_gross,
        "portfolio_policy_max_position_weight": policy_maximum,
        "portfolio_policy_diagnostic_risk_aversion": policy_risk_aversion,
        "paper_watch_auto_enrollment": {
            "enabled": bool(watch_enrollment.get("enabled", False)),
            "actor_id": watch_actor,
            "max_new_per_cycle": watch_limit,
            "scope": watch_scope,
        },
        "kernel_removal_trial": {
            "enabled": bool(removal.get("enabled", False)),
            "horizon_days": removal_horizon,
            "maximum_independent_blocks": removal_maximum,
        },
        "max_new_forecast_episodes_per_cycle": maximum,
        "include_qualified_discovery_in_forecasts": bool(
            policy.get("include_qualified_discovery_in_forecasts", False)
        ),
        "discovery_benchmark_id": str(policy.get("discovery_benchmark_id") or "SPY").upper(),
        "discovery_probe_weight": probe_weight,
        "max_research_queue": int(policy.get("max_research_queue") or 10),
        "risk": {
            "max_gross_paper_weight": gross,
            "max_single_name_weight": single,
            "minimum_cash_weight": cash,
        },
    }
    return {**body, "policy_sha256": stable_sha256(body), "policy_path": str(source)}


def operator_forecast_decisions(
    root: Path, *, include_drafts: bool,
) -> tuple[dict[str, Any], ...]:
    """Select at most one latest operator decision per entity for forecasting."""

    allowed = {"active", "draft"} if include_drafts else {"active"}
    latest: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "decisions").glob("*.json")):
        row = _read_json(path)
        lifecycle = dict((row or {}).get("profile_lifecycle") or {})
        if (
            not row
            or row.get("schema") != "jaggedthoughts-investment-decision-v1"
            or lifecycle.get("data_class") != "operator"
            or lifecycle.get("stage") not in allowed
        ):
            continue
        entity_id = str((row.get("entity") or {}).get("entity_id") or "").upper()
        if not entity_id:
            continue
        candidate = {**row, "decision_path": path.relative_to(root).as_posix()}
        current = latest.get(entity_id)
        if current is None or (str(candidate.get("as_of") or ""), str(candidate["decision_id"])) > (
            str(current.get("as_of") or ""), str(current["decision_id"]),
        ):
            latest[entity_id] = candidate
    return tuple(latest[key] for key in sorted(latest))


def _due_paper_watch_enrollments(
    root: Path, *, policy: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Return eligible proposal epochs still missing their zero-weight watch."""

    enrollment = dict(policy.get("paper_watch_auto_enrollment") or {})
    if not enrollment.get("enabled") or int(enrollment.get("max_new_per_cycle") or 0) < 1:
        return ()
    watched = {
        (
            str((row.get("entity") or {}).get("entity_kind") or ""),
            str((row.get("entity") or {}).get("entity_id") or "").upper(),
            str((row.get("evidence") or {}).get("candidate_leaf") or ""),
            str((row.get("evidence") or {}).get("dossier_leaf") or ""),
        )
        for row in paper_watch_decisions(root)
    }
    due = []
    for directory in ("equities", "funds"):
        audit = _read_json(root / "paper_proposals" / directory / "latest.json") or {}
        for row in audit.get("rows") or ():
            proposal = row.get("proposal") if isinstance(row, Mapping) else None
            if not isinstance(proposal, Mapping):
                continue
            entity = dict(proposal.get("entity") or {})
            evidence = dict(proposal.get("evidence") or {})
            identity = (
                str(entity.get("entity_kind") or ""),
                str(entity.get("entity_id") or "").upper(),
                str(evidence.get("candidate_leaf") or ""),
                str(evidence.get("dossier_leaf") or ""),
            )
            if (
                row.get("activation_eligible") is True
                and not row.get("blockers")
                and proposal.get("activation_eligible") is True
                and not proposal.get("activation_blockers")
                and float((proposal.get("paper_policy") or {}).get("target_weight", -1)) == 0
                and all(identity)
                and identity not in watched
            ):
                due.append({
                    "entity_kind": identity[0], "entity_id": identity[1],
                    "candidate_leaf": identity[2], "dossier_leaf": identity[3],
                    "proposal_sha256": proposal.get("proposal_sha256"),
                })
    return tuple(sorted(due, key=lambda row: (row["entity_kind"], row["entity_id"])))


def due_forecast_windows(
    root: Path,
    *,
    policy: Mapping[str, Any],
    as_of: str | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return non-overlapping decision or qualified-discovery episodes currently due."""

    evaluation_at = canonical_timestamp(as_of or _utc_now(), "capital-cycle forecast as_of")
    decisions = operator_forecast_decisions(
        root,
        include_drafts=bool(policy.get("include_operator_drafts_in_forecasts", False)),
    )
    watches = paper_watch_decisions(root)
    watch_entities = {
        str((row.get("entity") or {}).get("entity_id") or "").upper() for row in watches
    }
    decision_entities = {
        str((row.get("entity") or {}).get("entity_id") or "").upper() for row in decisions
    } | watch_entities
    discovery_subjects: list[dict[str, Any]] = []
    if policy.get("include_qualified_discovery_in_forecasts"):
        discovery = _read_json(root / "discovery" / "latest.json") or {}
        record = _read_json(root / "discovery" / "latest_record.json") or {}
        leaves = record.get("candidate_leaves") if isinstance(record.get("candidate_leaves"), Mapping) else {}
        for candidate in discovery.get("candidates") or ():
            if (
                not isinstance(candidate, Mapping)
                or candidate.get("entity_kind") not in {"public_equity", "public_fund"}
                or candidate.get("screen_status") != "qualified"
            ):
                continue
            entity_id = str(candidate.get("entity_id") or "").upper()
            candidate_id = str(candidate.get("candidate_id") or "")
            candidate_leaf = str(leaves.get(candidate_id) or "")
            if entity_id and entity_id not in decision_entities and candidate_leaf:
                discovery_subjects.append({
                    "entity_id": entity_id,
                    "candidate_id": candidate_id,
                    "candidate_leaf": candidate_leaf,
                    "rank": int(candidate.get("rank") or 10**9),
                })
    opened_by_key: dict[tuple[str, int], str] = {}
    opened_watch_keys: set[tuple[tuple[str, ...], int]] = set()
    protected_until_by_horizon: dict[int, str] = {}
    cohort_dates_by_horizon: dict[int, set[str]] = {}
    for path in (root / "closed_book" / "runs").glob("*.json"):
        run = _read_json(path)
        packet = dict((run or {}).get("evidence_packet") or {})
        if not run or not packet:
            continue
        run_id = str(run.get("run_id") or "")
        binding = _read_json(
            root / "closed_book" / "return_windows" / f"{run_id}.json"
        ) or {}
        if not (
            (run.get("settlement_contract") or {}).get("prospective_return_window")
            or (binding.get("binding") or {}).get("status") == "bound"
        ):
            continue
        key = (
            str((packet.get("entity") or {}).get("entity_id") or "").upper(),
            int(run.get("horizon_days") or 0),
        )
        subject = dict(run.get("subject") or {})
        if subject.get("kind") == "paper_watch_decision" and subject.get("subject_sha256"):
            research_evidence = dict(
                ((packet.get("research_snapshot") or {}).get("evidence") or {})
            )
            candidate_leaf = str(subject.get("candidate_leaf") or "")
            dossier_leaf = str(research_evidence.get("dossier_leaf") or "")
            information_identity = (
                ("evidence", candidate_leaf, dossier_leaf)
                if candidate_leaf and dossier_leaf else
                ("decision", str(subject["subject_sha256"]))
            )
            opened_watch_keys.add((information_identity, key[1]))
        opened_at = str(run.get("opened_at") or "")
        horizon = key[1]
        opened_by_key[key] = max(opened_by_key.get(key, ""), opened_at)
        cohort_dates_by_horizon.setdefault(horizon, set()).add(opened_at[:10])
        protected_until = str(
            (binding.get("binding") or {}).get("scheduled_exit_at")
            or run.get("end_at") or ""
        )
        if protected_until:
            protected_until_by_horizon[horizon] = max(
                protected_until_by_horizon.get(horizon, ""), protected_until,
            )

    def lane_accepts(horizon: int) -> bool:
        if evaluation_at[:10] in cohort_dates_by_horizon.get(horizon, set()):
            return True
        protected_until = protected_until_by_horizon.get(horizon)
        return not protected_until or timestamp_key(evaluation_at) > timestamp_key(protected_until)

    due: list[dict[str, Any]] = []
    for watch in watches:
        for window in policy.get("forecast_windows") or []:
            horizon = int(window["horizon_days"])
            evidence = dict(watch.get("evidence") or {})
            candidate_leaf = str(evidence.get("candidate_leaf") or "")
            dossier_leaf = str(evidence.get("dossier_leaf") or "")
            information_identity = (
                ("evidence", candidate_leaf, dossier_leaf)
                if candidate_leaf and dossier_leaf else
                ("decision", str(watch["decision_sha256"]))
            )
            watch_key = (information_identity, horizon)
            information_upgrade_due = watch_key not in opened_watch_keys
            if not lane_accepts(horizon) and not information_upgrade_due:
                continue
            entity_id = str((watch.get("entity") or {}).get("entity_id") or "").upper()
            prior = opened_by_key.get((entity_id, horizon))
            if prior and not information_upgrade_due:
                elapsed_days = (
                    timestamp_key(evaluation_at) - timestamp_key(prior)
                ).total_seconds() / 86_400
                if elapsed_days < int(window["cadence_days"]):
                    continue
            due.append({
                "subject_kind": "paper_watch_decision",
                "paper_watch_decision_id": watch["decision_id"],
                "paper_watch_decision_sha256": watch["decision_sha256"],
                "decision_id": None,
                "candidate_leaf": evidence["candidate_leaf"],
                "entity_id": entity_id,
                "profile_stage": "researched_paper_watch",
                "rank": int((watch.get("candidate_identity") or {}).get("rank") or 10**9),
                "horizon_days": horizon,
                "cadence_days": int(window["cadence_days"]),
                "prior_opened_at": prior,
                "information_upgrade_due": information_upgrade_due,
            })
    for decision in decisions:
        if str((decision.get("entity") or {}).get("entity_id") or "").upper() in watch_entities:
            continue
        for window in policy.get("forecast_windows") or []:
            horizon = int(window["horizon_days"])
            if not lane_accepts(horizon):
                continue
            entity_id = str((decision.get("entity") or {}).get("entity_id") or "").upper()
            prior = opened_by_key.get((entity_id, horizon))
            if prior:
                elapsed_days = (
                    timestamp_key(evaluation_at) - timestamp_key(prior)
                ).total_seconds() / 86_400
                if elapsed_days < int(window["cadence_days"]):
                    continue
            due.append({
                "subject_kind": "paper_decision",
                "decision_id": decision["decision_id"],
                "candidate_leaf": None,
                "entity_id": entity_id,
                "profile_stage": (decision.get("profile_lifecycle") or {}).get("stage"),
                "horizon_days": horizon,
                "cadence_days": int(window["cadence_days"]),
                "prior_opened_at": prior,
            })
    for subject in discovery_subjects:
        for window in policy.get("forecast_windows") or []:
            horizon = int(window["horizon_days"])
            if not lane_accepts(horizon):
                continue
            entity_id = subject["entity_id"]
            prior = opened_by_key.get((entity_id, horizon))
            if prior:
                elapsed_days = (
                    timestamp_key(evaluation_at) - timestamp_key(prior)
                ).total_seconds() / 86_400
                if elapsed_days < int(window["cadence_days"]):
                    continue
            due.append({
                "subject_kind": "discovery_candidate",
                "decision_id": None,
                "candidate_id": subject["candidate_id"],
                "candidate_leaf": subject["candidate_leaf"],
                "entity_id": entity_id,
                "profile_stage": "qualified_discovery",
                "rank": subject["rank"],
                "horizon_days": horizon,
                "cadence_days": int(window["cadence_days"]),
                "prior_opened_at": prior,
            })
    stage_rank = {
        "researched_paper_watch": 0, "active": 1, "draft": 2,
        "qualified_discovery": 3,
    }
    due.sort(key=lambda row: (
        stage_rank.get(str(row["profile_stage"]), 3),
        int(row.get("rank") or 0),
        row["horizon_days"],
        row["entity_id"],
    ))
    return tuple(due)


def _research_indexes(
    root: Path,
) -> tuple[set[str], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    dossiers: set[str] = set()
    for path in (root / "research" / "dossiers").glob("*.json"):
        row = _read_json(path)
        if row and row.get("candidate_leaf"):
            dossiers.add(str(row["candidate_leaf"]))
    coverage: dict[str, dict[str, Any]] = {}
    workspace_path = root / "workspace.yaml"
    raw = yaml.safe_load(workspace_path.read_text(encoding="utf-8")) if workspace_path.is_file() else {}
    config = dict(raw) if isinstance(raw, Mapping) else {}
    store_path = root / str(config.get("golden_store") or "state/golden_store.sqlite3")
    if store_path.exists():
        store = GoldenStore(store_path)
        seen_coverage_candidates: set[str] = set()
        for metadata in store.list_leaves(
            owner=str(config.get("owner") or "operator-paper-book"),
            object_kind="research_evidence_coverage", limit=10_000,
        ):
            payload = store.get_leaf(str(metadata["leaf_sha256"])).get("payload") or {}
            candidate_leaf = str(payload.get("candidate_leaf") or "")
            if not candidate_leaf or candidate_leaf in seen_coverage_candidates:
                continue
            seen_coverage_candidates.add(candidate_leaf)
            if payload.get("covered"):
                coverage[candidate_leaf] = {
                    "coverage_leaf": metadata["leaf_sha256"],
                    "prior_dossier_leaf": payload.get("prior_dossier_leaf"),
                    "accepted_reassessment_count": len(
                        payload.get("accepted_reassessment_leaves") or ()
                    ),
                    "scope": payload.get("scope"),
                }
    strategy: dict[str, dict[str, Any]] = {}
    strategy_rank: dict[str, tuple[Any, bool, str]] = {}
    for path in (root / "strategy_frontiers" / "results").glob("*.json"):
        row = _read_json(path)
        entity_id = str(((row or {}).get("company") or {}).get("id") or "").upper()
        if row and entity_id and (row.get("company") or {}).get("data_class") != "reference_fixture":
            rank = (
                timestamp_key(str(row.get("evidence_epoch") or "1970-01-01T00:00:00Z")),
                bool(row.get("economic_bridge")),
                str(row.get("strategy_frontier_sha256") or ""),
            )
            if rank <= strategy_rank.get(entity_id, (timestamp_key("1970-01-01T00:00:00Z"), False, "")):
                continue
            strategy_rank[entity_id] = rank
            strategy[entity_id] = {
                "strategy_frontier_sha256": row.get("strategy_frontier_sha256"),
                "program_count": (row.get("enumeration") or {}).get("program_count"),
                "frontier_count": len(row.get("frontier_program_ids") or []),
                "local_peak_count": len(row.get("local_peak_program_ids") or []),
                "scope_closed": row.get("scope_closed"),
                "decision_closed": row.get("decision_closed"),
                "economic_proposal_count": (row.get("economic_bridge") or {}).get("frontier_proposal_count"),
                "result_path": path.relative_to(root).as_posix(),
            }
    return dossiers, coverage, strategy


def _activation_class(screen_status: str, entity_kind: str) -> tuple[str, str]:
    if screen_status == "qualified" and entity_kind == "public_fund":
        return "fund_review_ready", "Review portfolio valuation, exposure, concentration, fees, liquidity, and tax fit."
    return {
        "qualified": ("underwriting_ready", "Review the qualified candidate for an inactive draft."),
        "monitor": ("research_or_wait", "Test the named residual or await the next source epoch."),
        "needs_valuation_evidence": (
            "acquire_valuation", "Acquire issuer or holdings valuation evidence before ranking it as cheap."
        ),
        "stale_evidence": ("repair_source", "Refresh the candidate's own stale source before reuse."),
        "blocked": ("repair_input", "Repair the typed missing input before analysis."),
    }.get(screen_status, ("inspect", "Inspect the candidate's typed status."))


def compile_opportunity_book(
    root: Path,
    *,
    policy: Mapping[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Compile the latest discovery population into a paper-capital action book."""

    completed_at = canonical_timestamp(generated_at or _utc_now(), "opportunity book generated_at")
    discovery = _read_json(root / "discovery" / "latest.json")
    if not discovery or discovery.get("schema") != "jaggedthoughts-discovery-run-v1":
        raise FileNotFoundError("capital cycle requires a compiled discovery/latest.json")
    decisions = operator_forecast_decisions(root, include_drafts=True)
    decision_by_entity = {
        str((row.get("entity") or {}).get("entity_id") or "").upper(): row for row in decisions
    }
    dossiers, research_coverage, strategy = _research_indexes(root)
    discovery_record = _read_json(root / "discovery" / "latest_record.json") or {}
    candidate_leaves = (
        discovery_record.get("candidate_leaves")
        if isinstance(discovery_record.get("candidate_leaves"), Mapping) else {}
    )
    discovery_candidates = [
        row for row in discovery.get("candidates") or () if isinstance(row, Mapping)
    ]
    law_influence = compile_law_policy_influence(
        discovery_candidates,
        _read_json(root / "institutional_learning" / "latest.json"),
        generated_at=completed_at,
    )
    strategy_laws = _read_json(
        root / "institutional_learning" / "strategy_laws" / "latest.json"
    ) or {}
    strategy_moves = _read_json(
        root / "institutional_learning" / "strategy_moves" / "latest.json"
    ) or {}
    market_catalog = _read_json(root / "universe" / "catalog-latest.json") or {}
    causal_inputs_ready = (
        strategy_laws.get("schema") == STRATEGY_LAW_INDUCTION_SCHEMA
        and strategy_moves.get("schema") == STRATEGY_MOVE_LIBRARY_SCHEMA
        and market_catalog.get("schema") == "jaggedthoughts-public-market-catalog-v1"
    )
    if causal_inputs_ready:
        causal_law_influence = compile_causal_law_target_influence(
            discovery_candidates, strategy_laws, strategy_moves, market_catalog,
            generated_at=completed_at,
        )
    else:
        causal_body = {
            "schema": CAUSAL_LAW_INFLUENCE_SET_SCHEMA,
            "generated_at": completed_at,
            "candidate_count": len(discovery_candidates),
            "active_application_count": 0, "active_candidate_count": 0,
            "candidates": [{
                "candidate_id": row.get("candidate_id"),
                "candidate_sha256": row.get("candidate_sha256"),
                "entity_id": row.get("entity_id"), "adjustment": 0.0,
                "active_law_count": 0, "influence_sha256s": [],
                "screen_status_before": row.get("screen_status"),
                "screen_status_after": row.get("screen_status"),
                "authority": "paper_research_priority_only", "capital_authority": False,
            } for row in discovery_candidates],
            "attempts": [], "status": "awaiting_typed_inputs",
            "missing_inputs": [
                name for name, ready in (
                    ("strategy_laws", strategy_laws.get("schema") == STRATEGY_LAW_INDUCTION_SCHEMA),
                    ("strategy_moves", strategy_moves.get("schema") == STRATEGY_MOVE_LIBRARY_SCHEMA),
                    ("market_catalog", market_catalog.get("schema") == "jaggedthoughts-public-market-catalog-v1"),
                ) if not ready
            ],
            "research_priority_only": True, "screen_status_mutable": False,
            "authority": "paper_research_priority_only", "capital_authority": False,
        }
        causal_law_influence = {
            **causal_body, "influence_set_sha256": stable_sha256(causal_body),
        }
    influence_by_candidate = {
        str(row["candidate_identity"]): row for row in law_influence["candidates"]
    }
    causal_by_candidate = {
        str(row["candidate_id"]): row for row in causal_law_influence["candidates"]
    }
    rows: list[dict[str, Any]] = []
    for candidate in discovery_candidates:
        entity_id = str(candidate.get("entity_id") or "").upper()
        screen = str(candidate.get("screen_status") or "blocked")
        entity_kind = str(candidate.get("entity_kind") or "")
        activation_class, action = _activation_class(screen, entity_kind)
        metrics = dict(candidate.get("metrics") or {})
        decision = decision_by_entity.get(entity_id)
        lifecycle = dict((decision or {}).get("profile_lifecycle") or {})
        identity = str(candidate.get("candidate_id") or entity_id)
        candidate_leaf = str(candidate_leaves.get(identity) or "")
        coverage = research_coverage.get(candidate_leaf)
        influence = influence_by_candidate.get(identity) or {
            "adjustment": 0.0, "active_law_count": 0, "contributions": [],
        }
        causal_influence = causal_by_candidate.get(identity) or {
            "adjustment": 0.0, "active_law_count": 0, "influence_sha256s": [],
        }
        base_priority = candidate.get("rank_score")
        learned_priority = (
            float(base_priority) + float(influence["adjustment"])
            + float(causal_influence["adjustment"])
            if base_priority is not None else None
        )
        rows.append({
            "candidate_id": candidate.get("candidate_id"),
            "candidate_sha256": candidate.get("candidate_sha256"),
            "rank": candidate.get("rank"),
            "research_rank": candidate.get("research_rank"),
            "potential_rank": candidate.get("potential_rank"),
            "research_priority_score": candidate.get("rank_score"),
            "learned_research_priority_score": learned_priority,
            "law_policy_influence": influence,
            "causal_law_target_influence": causal_influence,
            "research_priority_is_expected_return": False,
            "entity_id": entity_id,
            "name": candidate.get("name"),
            "entity_kind": entity_kind,
            "screen_status": screen,
            "activation_class": activation_class,
            "next_action": action,
            "kernel_next_activation": candidate.get("next_activation"),
            "economic_coordinates": {
                key: metrics.get(key) for key in (
                    "price_implied_excess_return", "factor_implied_return", "implied_growth",
                    "earnings_power_margin", "quality", "maximum_drawdown", "residual_alpha",
                )
            },
            "research": {
                "dossier_available": candidate_leaf in dossiers or bool(
                    coverage and coverage.get("covered")
                ),
                "evidence_coverage": (
                    {"kind": "candidate_bound_dossier", "candidate_leaf": candidate_leaf}
                    if candidate_leaf in dossiers else
                    {"kind": "monitored_dossier_bridge", **coverage}
                    if coverage and coverage.get("covered") else None
                ),
                "strategy_frontier": strategy.get(entity_id),
                "research_prompt": candidate.get("research_prompt"),
            },
            "paper_decision": ({
                "decision_id": decision.get("decision_id"),
                "decision_record_sha256": decision.get("decision_record_sha256"),
                "stage": lifecycle.get("stage"),
                "selected_action_id": (decision.get("summary") or {}).get("selected_action_id"),
                "target_weight": (decision.get("summary") or {}).get("target_weight"),
            } if decision else None),
            "criteria": candidate.get("criteria") or [],
            "source_refs": candidate.get("source_refs") or [],
        })
    active_positions = []
    for entity_id, decision in sorted(decision_by_entity.items()):
        lifecycle = dict(decision.get("profile_lifecycle") or {})
        if lifecycle.get("stage") != "active":
            continue
        weight = float((decision.get("summary") or {}).get("target_weight") or 0.0)
        active_positions.append({
            "entity_id": entity_id,
            "decision_id": decision["decision_id"],
            "target_weight": weight,
            "selected_action_id": (decision.get("summary") or {}).get("selected_action_id"),
        })
    gross = sum(float(row["target_weight"]) for row in active_positions)
    risk = dict(policy.get("risk") or {})
    violations = []
    if gross > float(risk["max_gross_paper_weight"]) + 1e-12:
        violations.append("gross_paper_weight_exceeds_ceiling")
    if any(float(row["target_weight"]) > float(risk["max_single_name_weight"]) + 1e-12 for row in active_positions):
        violations.append("single_name_weight_exceeds_ceiling")
    if 1.0 - gross < float(risk["minimum_cash_weight"]) - 1e-12:
        violations.append("cash_weight_below_floor")
    learning_adjustment_applied = bool(
        law_influence.get("active_law_count")
        or causal_law_influence.get("active_application_count")
    )
    equity_lane = sorted(
        (
            row for row in rows
            if row["entity_kind"] == "public_equity"
            and row["learned_research_priority_score"] is not None
        ),
        key=lambda row: (
            -float(row["learned_research_priority_score"]),
            int((row.get("potential_rank") or {}).get("rank") or 10**9),
            row["entity_id"],
        ),
    )
    for lane_rank, row in enumerate(equity_lane, start=1):
        row["learned_potential_rank"] = {
            **(
                {
                    "scope": "public_equity", "rank": lane_rank,
                    "ranked_count": len(equity_lane),
                    "adjusted_native_score": row["learned_research_priority_score"],
                }
                if learning_adjustment_applied else dict(row.get("potential_rank") or {})
            ),
            "law_adjustment_applied": learning_adjustment_applied,
        }
    fund_lane = sorted(
        (
            row for row in rows
            if row["entity_kind"] == "public_fund" and row.get("potential_rank")
        ),
        key=lambda row: (
            int(row["potential_rank"]["rank"]), row["entity_id"],
        ),
    )
    for row in fund_lane:
        row["learned_potential_rank"] = {
            **dict(row["potential_rank"]),
            "law_adjustment_applied": False,
        }
    for row in rows:
        row.setdefault("learned_potential_rank", None)
    rows.sort(key=lambda row: (
        row["screen_status"] != "qualified",
        row["learned_potential_rank"] is None,
        int((row["learned_potential_rank"] or {}).get("rank") or 10**9),
        str(row["entity_kind"]), row["entity_id"],
    ))
    learned_research_rank = 0
    for row in rows:
        row["learned_research_rank"] = None
        if row["screen_status"] == "qualified":
            learned_research_rank += 1
            row["learned_research_rank"] = learned_research_rank
    qualified = [row for row in rows if row["screen_status"] == "qualified"]
    underwriting_ready = [row for row in qualified if row["entity_kind"] == "public_equity"]
    fund_review_ready = [row for row in qualified if row["entity_kind"] == "public_fund"]
    research = [row for row in rows if row["screen_status"] in {"monitor", "needs_valuation_evidence"}]
    repair = [row for row in rows if row["screen_status"] in {"stale_evidence", "blocked"}]
    body = {
        "schema": OPPORTUNITY_BOOK_SCHEMA,
        "book_id": f"opportunity-book-{str(discovery['run_sha256'])[:16]}",
        "generated_at": completed_at,
        "discovery_run_id": discovery["run_id"],
        "discovery_run_sha256": discovery["run_sha256"],
        "policy_sha256": policy["policy_sha256"],
        "candidate_count": len(rows),
        "qualified_count": len(qualified),
        "research_count": len(research),
        "repair_count": len(repair),
        "law_policy_influence": law_influence,
        "causal_law_target_influence": causal_law_influence,
        "candidates": rows,
        "underwriting_ready": underwriting_ready,
        "fund_review_ready": fund_review_ready,
        "research_queue": research[: int(policy.get("max_research_queue") or 10)],
        "repair_queue": repair,
        "active_positions": active_positions,
        "paper_posture": {
            "state": "deployed" if gross > 0 else "cash",
            "gross_target_weight": gross,
            "cash_weight": 1.0 - gross,
            "risk_policy": risk,
            "violations": violations,
            "admissible": not violations,
            "reason": (
                "No active paper decision currently earns risk."
                if gross == 0 else "Active paper decisions remain inside declared risk ceilings."
            ),
        },
        "next_action": (
            qualified[0]["next_action"] if qualified
            else research[0]["next_action"] if research
            else repair[0]["next_action"] if repair
            else "Refresh the public-source universe."
        ),
        "authority": "paper_shadow",
        "capital_authority": False,
        "source_refs": sorted({
            f"discovery:{discovery['run_sha256']}",
            *(
                f"decision:{row.get('decision_record_sha256')}"
                for row in decisions if row.get("decision_record_sha256")
            ),
            *(
                [f"institutional-learning:{law_influence['learning_state_sha256']}"]
                if law_influence.get("learning_state_sha256") else []
            ),
        }),
    }
    return {**body, "book_sha256": stable_sha256(body)}


def settlement_readiness(root: Path, *, as_of: str | None = None) -> dict[str, Any]:
    """Project issued, due, and blocked prospective outcomes without settling them."""

    evaluated_at = canonical_timestamp(as_of or _utc_now(), "settlement readiness as_of")

    def horizon_lane(directory: str, schema: str) -> dict[str, Any]:
        settlement_ids = {
            str((_read_json(path) or {}).get("run_id") or "")
            for path in (root / directory / "settlements").glob("*.json")
        }
        pending = []
        issued = 0
        issued_ids = set()
        quarantined = []
        for path in sorted((root / directory / "runs").glob("*.json")):
            run = _read_json(path)
            if not run or run.get("schema") != schema or not run.get("end_at"):
                continue
            issued += 1
            run_id = str(run.get("run_id") or "")
            issued_ids.add(run_id)
            if run_id in settlement_ids:
                continue
            window_contract = (
                (run.get("settlement_contract") or {}).get("prospective_return_window")
            )
            binding_artifact = _read_json(
                root / directory / "return_windows" / f"{run_id}.json"
            ) or {}
            binding = binding_artifact.get("binding") or {}
            if not window_contract and not binding:
                quarantined.append({
                    "run_id": run_id,
                    "status": "quarantined_legacy_pre_entry_contract",
                })
                continue
            if binding.get("status") != "bound":
                pending.append({
                    "run_id": run_id,
                    "end_at": None,
                    "status": "awaiting_postseal_entry_binding",
                })
                continue
            end_at = canonical_timestamp(
                binding["scheduled_exit_at"], f"{directory} scheduled_exit_at",
            )
            pending.append({
                "run_id": run_id,
                "end_at": end_at,
                "status": (
                    "due_awaiting_point_in_time_outcome"
                    if timestamp_key(end_at) <= timestamp_key(evaluated_at)
                    else "awaiting_horizon"
                ),
            })
        due = [row for row in pending if row["status"].startswith("due_")]
        return {
            "issued_count": issued,
            "settled_count": len(settlement_ids & issued_ids),
            "pending_count": len(pending),
            "due_count": len(due),
            "due_run_ids": [row["run_id"] for row in due],
            "next_due_at": min(
                (row["end_at"] for row in pending if row["end_at"]), default=None,
            ),
            "runs": pending,
            "quarantined_count": len(quarantined),
            "quarantined_runs": quarantined,
        }

    closed_book = horizon_lane(
        "closed_book", "jaggedthoughts-closed-book-forecast-run-v1",
    )
    portfolio_policy = horizon_lane(
        "portfolio_policy", "jaggedthoughts-portfolio-policy-run-v1",
    )
    dual = compile_strategy_dual_outcome_episodes(root)
    library = _read_json(root / "institutional_learning" / "strategy_moves" / "latest.json") or {}
    exact_moves = []
    for move in library.get("moves") or ():
        event = move.get("implementation_event") if isinstance(move, Mapping) else None
        if not isinstance(event, Mapping) or event.get("treatment_timing_status") != "exact_adoption_event":
            continue
        try:
            available_at = canonical_timestamp(event.get("available_at"), "strategy event available_at")
        except ValueError:
            continue
        if timestamp_key(available_at) <= timestamp_key(evaluated_at):
            exact_moves.append(move)
    operating_contract_count = sum(len(row.get("outcome_contracts") or ()) for row in exact_moves)
    dual_due = []
    future_dual_dates = []
    for episode in dual.get("episodes") or ():
        operating = episode["operating_outcome"]
        security = episode["security_outcome"]
        if operating["status"] == "pending" and operating["contract"].get("due_at"):
            due_at = canonical_timestamp(operating["contract"]["due_at"], "operating due_at")
            (dual_due if timestamp_key(due_at) <= timestamp_key(evaluated_at) else future_dual_dates).append({
                "episode_key": episode["dual_outcome_episode_key_sha256"],
                "outcome": "operating", "due_at": due_at,
            })
        if security["status"] == "pending" and security.get("end_at"):
            due_at = canonical_timestamp(security["end_at"], "security end_at")
            (dual_due if timestamp_key(due_at) <= timestamp_key(evaluated_at) else future_dual_dates).append({
                "episode_key": episode["dual_outcome_episode_key_sha256"],
                "outcome": "security", "due_at": due_at,
            })
    if dual.get("episode_count"):
        issuance_status = "issued"
    elif exact_moves and not operating_contract_count:
        issuance_status = "blocked_missing_operating_outcome_contract"
    elif exact_moves:
        issuance_status = "awaiting_eligible_candidate_issue"
    else:
        issuance_status = "awaiting_exact_adoption_event"
    strategy_dual = {
        "issued_count": int(dual.get("episode_count") or 0),
        "settled_count": int(dual.get("settled_count") or 0),
        "pending_count": int(dual.get("pending_count") or 0),
        "due_outcome_count": len(dual_due),
        "due_outcomes": dual_due,
        "next_due_at": min((row["due_at"] for row in future_dual_dates), default=None),
        "exact_adoption_move_count": len(exact_moves),
        "declared_operating_contract_count": operating_contract_count,
        "issuance_status": issuance_status,
        "next_activation": dual.get("next_activation"),
    }
    body = {
        "schema": SETTLEMENT_READINESS_SCHEMA,
        "evaluated_at": evaluated_at,
        "closed_book": closed_book,
        "portfolio_policy": portfolio_policy,
        "strategy_dual": strategy_dual,
        "trigger_contract": {
            "closed_book": "capital_cycle_service",
            "portfolio_policy": "capital_cycle_service",
            "strategy_dual_operating": "subscription_research_then_institutional_learning",
            "strategy_dual_security": "capital_cycle_service_via_closed_book",
        },
        "capital_authority": False,
    }
    return {**body, "readiness_sha256": stable_sha256(body)}


def capital_cycle_status(
    root: Path,
    *,
    as_of: str | None = None,
    policy_path: str | Path | None = None,
    owner: str = "operator-paper-book",
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return current capital-cycle state and its event-driven due reasons."""

    policy_source = Path(policy_path).expanduser().resolve() if policy_path else root / "capital_cycle.yaml"
    if not policy_source.is_file():
        return {
            "schema": CAPITAL_CYCLE_STATUS_SCHEMA, "enabled": False,
            "configured": False, "due": False, "capital_authority": False,
        }
    policy = load_capital_cycle_policy(policy_source)
    latest_run = _read_json(root / "capital_cycles" / "latest.json")
    latest_book = _read_json(root / "opportunity_books" / "latest.json")
    discovery = _read_json(root / "discovery" / "latest.json")
    learning = _read_json(root / "institutional_learning" / "latest.json")
    due_windows = due_forecast_windows(root, policy=policy, as_of=as_of)
    evaluation_at = canonical_timestamp(as_of or _utc_now(), "capital-cycle status as_of")
    readiness = settlement_readiness(root, as_of=evaluation_at)
    due_watch_enrollments = _due_paper_watch_enrollments(root, policy=policy)
    market_state_due = market_state_cycle_due(
        root, windows=policy.get("market_state_forecast_windows") or (), as_of=evaluation_at,
    )
    strategy_source_check = _read_json(
        root / "institutional_learning" / "strategy_path_shadow" / "source-check.json"
    )
    last_strategy_source_check = str(
        (strategy_source_check or {}).get("checked_at") or "1970-01-01T00:00:00Z"
    )
    strategy_source_refresh_due = (
        timestamp_key(evaluation_at) - timestamp_key(last_strategy_source_check)
        >= timedelta(days=int(policy["strategy_event_archive_refresh_cadence_days"]))
    )
    portfolio_policy = portfolio_policy_status(root)
    walk_forward_profile = root / "point_in_time_replay" / "sealed_walk_forward_seed.json"
    try:
        walk_forward = (
            sealed_walk_forward_status(
                root, walk_forward_profile, as_of=evaluation_at,
                owner=owner, store_path=store_path,
            )
            if walk_forward_profile.is_file() else {
                "schema": "jaggedthoughts-sealed-walk-forward-status-v1",
                "status": "profile_missing", "periodic_activation_due": False,
                "capital_authority": False,
            }
        )
    except (KeyError, OSError, TypeError, ValueError) as error:
        walk_forward = {
            "schema": "jaggedthoughts-sealed-walk-forward-status-v1",
            "status": "error", "periodic_activation_due": False,
            "error": f"{type(error).__name__}: {error}"[:1_000],
            "capital_authority": False,
        }
    matured = list(readiness["closed_book"]["due_run_ids"])
    learning_sha = str((learning or {}).get("state_sha256") or "")
    reasons = []
    if not latest_run:
        reasons.append("no_capital_cycle_run")
    if discovery and str(discovery.get("run_sha256") or "") != str(
        (latest_run or {}).get("discovery_run_sha256") or ""
    ):
        reasons.append("new_discovery_epoch")
    if learning_sha and learning_sha != str(
        (((latest_run or {}).get("institutional_learning") or {}).get("state") or {}).get(
            "state_sha256"
        ) or ""
    ):
        reasons.append("new_institutional_learning_epoch")
    if due_windows:
        reasons.append("forecast_window_due")
    if matured:
        reasons.append("forecast_settlement_due")
    if due_watch_enrollments:
        reasons.append("paper_watch_enrollment_due")
    if market_state_due["due_horizons"]:
        reasons.append("market_state_forecast_due")
    if market_state_due["matured_run_ids"]:
        reasons.append("market_state_settlement_due")
    if strategy_source_refresh_due:
        reasons.append("strategy_event_archive_refresh_due")
    latest_policy_run = portfolio_policy.get("latest_run") or {}
    latest_policy_book = str(latest_policy_run.get("opportunity_book_sha256") or "")
    current_book = str((latest_book or {}).get("book_sha256") or "")
    if current_book and not int(portfolio_policy.get("pending_count") or 0) and (
        not latest_policy_run or latest_policy_book != current_book
    ):
        reasons.append("portfolio_policy_due")
    if readiness["portfolio_policy"]["due_count"]:
        reasons.append("portfolio_policy_settlement_due")
    if walk_forward.get("periodic_activation_due"):
        reasons.append("sealed_walk_forward_due")
    service = _read_json(root / "state" / "capital_cycle_service.json")
    return {
        "schema": CAPITAL_CYCLE_STATUS_SCHEMA,
        "configured": True,
        "enabled": bool(policy.get("enabled")),
        "policy": policy,
        "due": bool(reasons) and bool(policy.get("enabled")),
        "due_reasons": reasons,
        "due_forecast_windows": list(due_windows),
        "matured_run_ids": matured,
        "due_paper_watch_enrollments": list(due_watch_enrollments),
        "market_state_due": market_state_due,
        "strategy_event_archive_refresh_due": strategy_source_refresh_due,
        "strategy_event_archive_last_checked_at": last_strategy_source_check,
        "portfolio_policy": portfolio_policy,
        "sealed_walk_forward": walk_forward,
        "settlement_readiness": readiness,
        "latest_run": latest_run,
        "latest_book": latest_book,
        "service": service,
        "capital_authority": False,
    }


__all__ = [
    "CAPITAL_CYCLE_POLICY_SCHEMA",
    "CAPITAL_CYCLE_RUN_SCHEMA",
    "CAPITAL_CYCLE_STATUS_SCHEMA",
    "OPPORTUNITY_BOOK_SCHEMA",
    "SETTLEMENT_READINESS_SCHEMA",
    "capital_cycle_status",
    "compile_opportunity_book",
    "default_capital_cycle_policy",
    "due_forecast_windows",
    "load_capital_cycle_policy",
    "operator_forecast_decisions",
    "settlement_readiness",
]
