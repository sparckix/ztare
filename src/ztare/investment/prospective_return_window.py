"""Executable price windows for prospective investment evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_text, timestamp_key


RETURN_WINDOW_SCHEMA = "jaggedthoughts-prospective-return-window-v1"
RETURN_WINDOW_BINDING_SCHEMA = "jaggedthoughts-prospective-return-window-binding-v1"
RETURN_WINDOW_SETTLEMENT_SCHEMA = "jaggedthoughts-prospective-return-window-settlement-v1"


def _valid_hash(payload: Mapping[str, Any], field: str) -> bool:
    claimed = str(payload.get(field) or "")
    return bool(claimed) and claimed == stable_sha256({
        key: value for key, value in payload.items() if key != field
    })


def _point(row: Any) -> dict[str, Any]:
    value = row if isinstance(row, Mapping) else {
        key: getattr(row, key) for key in (
            "entity_id", "value", "observed_at", "available_at",
            "observation_id", "source_ref",
        )
    }
    price = value.get("price", value.get("value"))
    return {
        "entity_id": require_text(value.get("entity_id"), "return-window entity_id").upper(),
        "price": float(price),
        "observed_at": canonical_timestamp(
            value.get("observed_at"), "return-window observed_at"
        ),
        "available_at": canonical_timestamp(
            value.get("available_at"), "return-window available_at"
        ),
        "observation_id": str(value.get("observation_id") or ""),
        "source_ref": require_text(value.get("source_ref"), "return-window source_ref"),
    }


def compile_prospective_return_window(
    *, sealed_at: str, horizon_days: int, entity_ids: Sequence[str],
    transaction_cost_bps: float,
    price_identity: str = "adjusted_close_total_return_proxy",
    maximum_exit_lag_days: int = 10,
) -> dict[str, Any]:
    """Freeze a common post-seal entry and horizon rule."""

    if isinstance(horizon_days, bool) or not 7 <= int(horizon_days) <= 730:
        raise ValueError("return-window horizon_days must be in [7, 730]")
    identities = sorted({require_text(value, "return-window entity_id").upper() for value in entity_ids})
    if len(identities) < 2:
        raise ValueError("return window requires at least two priced identities")
    cost = float(transaction_cost_bps)
    if not 0 <= cost <= 1_000:
        raise ValueError("return-window transaction_cost_bps must be in [0, 1000]")
    if isinstance(maximum_exit_lag_days, bool) or not 1 <= int(maximum_exit_lag_days) <= 30:
        raise ValueError("return-window maximum_exit_lag_days must be in [1, 30]")
    body = {
        "schema": RETURN_WINDOW_SCHEMA,
        "sealed_at": canonical_timestamp(sealed_at, "return-window sealed_at"),
        "horizon_days": int(horizon_days),
        "entity_ids": identities,
        "entry_rule": "earliest_common_observed_at_on_or_after_seal_available_by_binding",
        "exit_rule": "earliest_common_observed_at_on_or_after_entry_plus_horizon_available_by_settlement",
        "maximum_exit_lag_days": int(maximum_exit_lag_days),
        "missing_exit_rule": "require_explicit_corporate_action_or_terminal_outcome_after_lag",
        "price_identity": require_text(price_identity, "return-window price_identity"),
        "transaction_cost_bps": cost,
        "authority": "evaluation_only",
        "capital_authority": False,
    }
    return {**body, "return_window_sha256": stable_sha256(body)}


def _common_point(
    entity_ids: Sequence[str], points: Mapping[str, Sequence[Any]], *,
    on_or_after: str, as_of: str,
    point_index: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
) -> tuple[str, dict[str, dict[str, Any]]] | None:
    threshold = canonical_timestamp(on_or_after, "return-window common-point threshold")
    indexed = point_index or index_return_window_points(points, as_of=as_of)
    eligible = {
        entity_id: {
            observed_at: dict(row)
            for observed_at, row in indexed.get(entity_id, {}).items()
            if observed_at >= threshold
        }
        for entity_id in entity_ids
    }
    common = set.intersection(*(set(eligible[entity_id]) for entity_id in entity_ids))
    if not common:
        return None
    observed_at = min(common, key=timestamp_key)
    return observed_at, {entity_id: eligible[entity_id][observed_at] for entity_id in entity_ids}


def index_return_window_points(
    points: Mapping[str, Sequence[Any]], *, as_of: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Normalize a shared price pool once for many return-window evaluations."""

    cutoff = timestamp_key(canonical_timestamp(as_of, "return-window point-index as_of"))
    indexed: dict[str, dict[str, dict[str, Any]]] = {}
    for entity_id, values in points.items():
        rows: dict[str, dict[str, Any]] = {}
        for raw in values:
            row = _point(raw)
            if row["price"] <= 0 or timestamp_key(row["available_at"]) > cutoff:
                continue
            prior = rows.get(row["observed_at"])
            if prior is None or (row["available_at"], row["observation_id"]) < (
                prior["available_at"], prior["observation_id"],
            ):
                rows[row["observed_at"]] = row
        indexed[str(entity_id).upper()] = rows
    return indexed


def bind_prospective_return_window(
    contract: Mapping[str, Any], *, points: Mapping[str, Sequence[Any]], as_of: str,
    point_index: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Bind the first synchronized tradable observation after the seal."""

    if contract.get("schema") != RETURN_WINDOW_SCHEMA or not _valid_hash(
        contract, "return_window_sha256"
    ):
        raise ValueError("prospective return-window contract is invalid")
    evaluated_at = canonical_timestamp(as_of, "return-window binding as_of")
    match = _common_point(
        list(contract["entity_ids"]), points,
        on_or_after=str(contract["sealed_at"]), as_of=evaluated_at,
        point_index=point_index,
    )
    if match is None:
        body = {
            "schema": RETURN_WINDOW_BINDING_SCHEMA,
            "return_window_sha256": contract["return_window_sha256"],
            "status": "pending_entry",
            "evaluated_at": evaluated_at,
            "entry_observed_at": None,
            "scheduled_exit_at": None,
            "entry_points": {},
            "capital_authority": False,
        }
    else:
        entry_at, entries = match
        scheduled_exit = (
            datetime.fromisoformat(entry_at.replace("Z", "+00:00"))
            + timedelta(days=int(contract["horizon_days"]))
        ).isoformat(timespec="seconds").replace("+00:00", "Z")
        body = {
            "schema": RETURN_WINDOW_BINDING_SCHEMA,
            "return_window_sha256": contract["return_window_sha256"],
            "status": "bound",
            "evaluated_at": evaluated_at,
            "entry_observed_at": entry_at,
            "scheduled_exit_at": scheduled_exit,
            "entry_points": entries,
            "capital_authority": False,
        }
    return {**body, "binding_sha256": stable_sha256(body)}


def settle_prospective_return_window(
    contract: Mapping[str, Any], binding: Mapping[str, Any], *,
    points: Mapping[str, Sequence[Any]], as_of: str,
    point_index: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Settle a bound window at the first synchronized point after its horizon."""

    if (
        binding.get("schema") != RETURN_WINDOW_BINDING_SCHEMA
        or not _valid_hash(binding, "binding_sha256")
        or binding.get("return_window_sha256") != contract.get("return_window_sha256")
        or binding.get("status") != "bound"
    ):
        raise ValueError("prospective return-window binding is invalid or pending")
    evaluated_at = canonical_timestamp(as_of, "return-window settlement as_of")
    effective_index = point_index or index_return_window_points(
        points, as_of=evaluated_at,
    )
    match = _common_point(
        list(contract["entity_ids"]), points,
        on_or_after=str(binding["scheduled_exit_at"]), as_of=evaluated_at,
        point_index=effective_index,
    )
    if match is None:
        terminal_due_at = (
            datetime.fromisoformat(str(binding["scheduled_exit_at"]).replace("Z", "+00:00"))
            + timedelta(days=int(contract.get("maximum_exit_lag_days") or 10))
        ).isoformat(timespec="seconds").replace("+00:00", "Z")
        terminal_due = timestamp_key(evaluated_at) >= timestamp_key(terminal_due_at)
        threshold = str(binding["scheduled_exit_at"])
        missing = sorted(
            entity_id for entity_id in contract["entity_ids"]
            if not any(observed_at >= threshold for observed_at in (
                effective_index.get(entity_id, {})
            ))
        )
        body = {
            "schema": RETURN_WINDOW_SETTLEMENT_SCHEMA,
            "return_window_sha256": contract["return_window_sha256"],
            "binding_sha256": binding["binding_sha256"],
            "status": "terminal_outcome_required" if terminal_due else "pending_exit",
            "evaluated_at": evaluated_at,
            "terminal_outcome_due_at": terminal_due_at,
            "missing_entity_ids": missing,
            "exit_observed_at": None,
            "exit_points": {},
            "returns": {},
            "capital_authority": False,
        }
    else:
        exit_at, exits = match
        entries = dict(binding["entry_points"])
        gross_returns = {
            entity_id: float(exits[entity_id]["price"]) / float(entries[entity_id]["price"]) - 1.0
            for entity_id in contract["entity_ids"]
        }
        one_way_cost = float(contract["transaction_cost_bps"]) / 10_000.0
        returns = {
            entity_id: (1.0 + value) * (1.0 - one_way_cost) ** 2 - 1.0
            for entity_id, value in gross_returns.items()
        }
        body = {
            "schema": RETURN_WINDOW_SETTLEMENT_SCHEMA,
            "return_window_sha256": contract["return_window_sha256"],
            "binding_sha256": binding["binding_sha256"],
            "status": "settled",
            "evaluated_at": evaluated_at,
            "exit_observed_at": exit_at,
            "exit_points": exits,
            "gross_returns": gross_returns,
            "returns": returns,
            "round_trip_transaction_cost_bps": 2.0 * float(contract["transaction_cost_bps"]),
            "capital_authority": False,
        }
    return {**body, "window_settlement_sha256": stable_sha256(body)}


__all__ = [
    "RETURN_WINDOW_BINDING_SCHEMA", "RETURN_WINDOW_SCHEMA",
    "RETURN_WINDOW_SETTLEMENT_SCHEMA", "bind_prospective_return_window",
    "compile_prospective_return_window", "index_return_window_points",
    "settle_prospective_return_window",
]
