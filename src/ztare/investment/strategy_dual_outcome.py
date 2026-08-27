"""Join one frozen strategy move to distinct operating and security outcomes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import timestamp_key
from .factor_analysis import PricePoint, load_price_points
from .strategy_alpha_scheduler import STRATEGY_DUAL_OUTCOME_CONTRACT_SCHEMA
from .strategy_learning import candidate_bound_strategy_move


STRATEGY_DUAL_OUTCOME_EPISODES_SCHEMA = "jaggedthoughts-strategy-dual-outcome-episodes-v1"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _valid_hash(payload: Mapping[str, Any], field: str) -> bool:
    claimed = str(payload.get(field) or "")
    return bool(claimed) and claimed == stable_sha256({
        key: value for key, value in payload.items() if key != field
    })


def _price(
    points: Iterable[PricePoint], entity_id: str, *, at: str, side: str,
) -> PricePoint | None:
    rows = [row for row in points if row.entity_id == entity_id]
    eligible = [
        row for row in rows
        if timestamp_key(row.observed_at) <= timestamp_key(at)
        and timestamp_key(row.available_at) <= timestamp_key(at)
    ] if side == "start" else [
        row for row in rows
        if timestamp_key(row.observed_at) >= timestamp_key(at)
    ]
    if not eligible:
        return None
    key = lambda row: (timestamp_key(row.observed_at), row.observation_id)
    return (max if side == "start" else min)(eligible, key=key)


def _factor_controlled_return(
    root: Path, *, run: Mapping[str, Any], settlement: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    control = dict((contract.get("security_outcome") or {}).get("control") or {})
    actual = dict(settlement.get("actual_values") or {})
    result = {
        "control_kind": control.get("kind"),
        "benchmark_active_return": (
            actual.get("active_return")
            if actual.get("active_return") is not None
            else float(actual.get("entity_return") or 0.0)
            - float(actual.get("benchmark_return") or 0.0)
        ),
        "factor_controlled_return": None,
        "realized_factor_returns": {},
        "source_observation_ids": [],
        "source_refs": [],
        "status": "benchmark_controlled_only",
    }
    if control.get("kind") != "frozen_factor_beta_vector":
        return result
    points = load_price_points(
        root / "data" / "observations.csv", as_of=str(settlement["evaluated_at"]),
        metric_id="adjusted_price",
    )
    returns: dict[str, float] = {}
    used: dict[str, PricePoint] = {}
    one_way_cost = float(
        (run.get("settlement_contract") or {}).get("transaction_cost_bps") or 0.0
    ) / 10_000.0
    entry_at = str(
        (settlement.get("return_window_binding") or {}).get("entry_observed_at")
        or run["opened_at"]
    )
    exit_at = str(
        (settlement.get("return_window_settlement") or {}).get("exit_observed_at")
        or run["end_at"]
    )
    for factor in control.get("factors") or ():
        factor_id = str(factor["factor_id"])
        legs = []
        for field, sign in (("long_entity_id", 1.0), ("short_entity_id", -1.0)):
            entity_id = str(factor.get(field) or "")
            if not entity_id:
                continue
            start = _price(points, entity_id, at=entry_at, side="start")
            end = _price(points, entity_id, at=exit_at, side="end")
            if start is None or end is None:
                return {**result, "status": "factor_endpoint_unavailable"}
            leg_gross = sign * (end.value / start.value - 1.0)
            legs.append((1.0 + leg_gross) * (1.0 - one_way_cost) ** 2 - 1.0)
            used[start.observation_id] = start
            used[end.observation_id] = end
        returns[factor_id] = sum(legs)
    factor_benchmark = sum(
        float(beta) * returns[factor_id]
        for factor_id, beta in (control.get("betas") or {}).items()
    )
    return {
        **result,
        "factor_controlled_return": float(actual["entity_return"]) - factor_benchmark,
        "entry_observed_at": entry_at,
        "exit_observed_at": exit_at,
        "realized_factor_returns": returns,
        "source_observation_ids": sorted(used),
        "source_refs": sorted({row.source_ref for row in used.values()}),
        "status": "factor_controlled",
    }


def compile_strategy_security_outcome(
    root: Path, *, run: Mapping[str, Any], settlement: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile the frozen strategy episode's primary investable return target."""

    nomination = dict(
        (((run.get("evidence_packet") or {}).get("discovery_summary") or {})
         .get("strategy_experiment_nomination") or {})
    )
    contract = dict(nomination.get("dual_outcome_contract") or {})
    if (
        contract.get("schema") != STRATEGY_DUAL_OUTCOME_CONTRACT_SCHEMA
        or not _valid_hash(contract, "dual_outcome_contract_sha256")
    ):
        raise ValueError("strategy security outcome requires a valid frozen contract")
    return _factor_controlled_return(
        root, run=run, settlement=settlement, contract=contract,
    )


def compile_strategy_dual_outcome_episodes(root: Path) -> dict[str, Any]:
    """Materialize settlement status without granting the join decision authority."""

    library = _read(root / "institutional_learning" / "strategy_moves" / "latest.json")
    moves = {
        str(row.get("move_sha256") or ""): row for row in library.get("moves") or ()
        if isinstance(row, Mapping)
    }
    settlements = {
        path.stem: _read(path) for path in (root / "closed_book" / "settlements").glob("*.json")
    }
    episodes, gaps = [], []
    for path in sorted((root / "closed_book" / "runs").glob("*.json")):
        run = _read(path)
        nomination = dict(
            (((run.get("evidence_packet") or {}).get("discovery_summary") or {})
             .get("strategy_experiment_nomination") or {})
        )
        contract = dict(nomination.get("dual_outcome_contract") or {})
        if not contract:
            continue
        if (
            contract.get("schema") != STRATEGY_DUAL_OUTCOME_CONTRACT_SCHEMA
            or not _valid_hash(contract, "dual_outcome_contract_sha256")
            or not _valid_hash(nomination, "nomination_sha256")
        ):
            gaps.append({"run_id": run.get("run_id"), "reason": "invalid_frozen_contract"})
            continue
        move = moves.get(str(contract.get("move_sha256") or "")) or {}
        if not candidate_bound_strategy_move(
            move,
            candidate_leaf=str(contract.get("candidate_leaf") or ""),
            candidate_sha256=str(contract.get("candidate_sha256") or ""),
        ):
            gaps.append({"run_id": run.get("run_id"), "reason": "candidate_move_lineage_mismatch"})
            continue
        operating_contract = dict(contract.get("operating_outcome") or {})
        operating_episode = next((
            dict(row) for row in move.get("outcome_episodes") or ()
            if str(row.get("contract_sha256") or "")
            == str(operating_contract.get("contract_sha256") or "")
        ), None)
        settlement = settlements.get(str(run.get("run_id") or ""))
        security = (
            _factor_controlled_return(root, run=run, settlement=settlement, contract=contract)
            if settlement else None
        )
        operating_status = "settled" if operating_episode else "pending"
        security_status = "settled" if settlement else "pending"
        body = {
            "schema": "jaggedthoughts-strategy-dual-outcome-episode-v1",
            "dual_outcome_contract_sha256": contract["dual_outcome_contract_sha256"],
            "dual_outcome_episode_key_sha256": contract["dual_outcome_episode_key_sha256"],
            "entity_id": contract["entity_id"],
            "candidate_leaf": contract["candidate_leaf"],
            "candidate_sha256": contract["candidate_sha256"],
            "move_sha256": contract["move_sha256"],
            "strategy_choice_identity_sha256": contract.get(
                "strategy_choice_identity_sha256"
            ),
            "mechanism_phenotype_sha256": contract["mechanism_phenotype_sha256"],
            "implementation_event_sha256": contract["implementation_event_sha256"],
            "operating_outcome": {
                "status": operating_status,
                "contract": operating_contract,
                "episode": operating_episode,
            },
            "security_outcome": {
                "status": security_status,
                "closed_book_run_id": run.get("run_id"),
                "closed_book_run_sha256": run.get("run_sha256"),
                "opened_at": run.get("opened_at"),
                "end_at": run.get("end_at"),
                "settlement_sha256": (settlement or {}).get("settlement_sha256"),
                "actual": security,
            },
            "joint_status": (
                "settled" if operating_status == security_status == "settled" else "pending"
            ),
            "evidence_use": "existing_law_and_strategy_alpha_promotion_gates_only",
            "direct_research_priority_adjustment": 0.0,
            "portfolio_weight": 0.0,
            "capital_authority": False,
        }
        episodes.append({**body, "episode_sha256": stable_sha256(body)})
    episodes.sort(key=lambda row: (
        str(row["security_outcome"].get("opened_at") or ""),
        str(row["dual_outcome_episode_key_sha256"]),
    ))
    operating_pending = sum(
        row["operating_outcome"]["status"] == "pending" for row in episodes
    )
    security_pending = sum(
        row["security_outcome"]["status"] == "pending" for row in episodes
    )
    settled = sum(row["joint_status"] == "settled" for row in episodes)
    if operating_pending:
        next_due = min(
            str(row["operating_outcome"]["contract"].get("due_at") or "")
            for row in episodes if row["operating_outcome"]["status"] == "pending"
        )
        next_activation = (
            f"Acquire the first admissible post-horizon operating observation at or after {next_due}; "
            "security settlement remains a separate closed-book consequence."
        )
    elif security_pending:
        next_due = min(
            str(row["security_outcome"].get("end_at") or "")
            for row in episodes if row["security_outcome"]["status"] == "pending"
        )
        next_activation = (
            f"Settle the frozen security-return consequence at or after {next_due}; "
            "do not infer investment alpha from the operating result."
        )
    elif settled:
        next_activation = (
            "Evaluate the existing operating-law and strategy-alpha promotion gates; "
            "the joined episode cannot assign attribution or capital authority."
        )
    else:
        next_activation = (
            "Run a capital cycle after an exact strategy adoption, measurable operating "
            "contract, and eligible public-equity candidate coincide."
        )
    body = {
        "schema": STRATEGY_DUAL_OUTCOME_EPISODES_SCHEMA,
        "episode_count": len(episodes),
        "pending_count": len(episodes) - settled,
        "settled_count": settled,
        "operating_pending_count": operating_pending,
        "security_pending_count": security_pending,
        "status": "settled" if settled and settled == len(episodes) else (
            "pending" if episodes else "awaiting_issue"
        ),
        "current_episode": episodes[-1] if episodes else None,
        "next_activation": next_activation,
        "episodes": episodes,
        "gaps": gaps,
        "authority": "promotion_gated_research_priority_input_only",
        "direct_research_priority_adjustment": 0.0,
        "capital_authority": False,
    }
    return {**body, "index_sha256": stable_sha256(body)}


__all__ = [
    "STRATEGY_DUAL_OUTCOME_EPISODES_SCHEMA",
    "compile_strategy_security_outcome",
    "compile_strategy_dual_outcome_episodes",
]
