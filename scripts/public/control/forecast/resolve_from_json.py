#!/usr/bin/env python3
"""Resolve a forecast-pool contract from a JSON payload file.

This is a narrow wrapper for VPS use: it avoids fragile shell quoting for
resolution notes and JSON-list fields while still delegating all authority and
ordering checks to the forecast pool CLI.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pool as forecast_pool


DEFAULTS: dict[str, Any] = {
    "success_bool": None,
    "actual_cost_agent_minutes": None,
    "compile_status": None,
    "sorry_delta": None,
    "goal_delta": None,
    "error_type": None,
    "artifact_hash": None,
    "artifact_path": None,
    "resolution_note": "",
    "realized_failure_mode_ids_json": "[]",
    "failure_mode_preconditioner_used": None,
    "preconditioner_source": None,
    "preconditioner_effect": None,
    "decision_changed_bool": None,
    "old_next_action": None,
    "new_next_action": None,
    "externality_tags_json": "[]",
    "negative_externality_tags_json": "[]",
    "counterfactual_value_bucket": None,
    "changed_by_forecast_ids_json": "[]",
    "voided": False,
    "allow_no_independent_forecaster": False,
    "no_independent_forecaster_reason": None,
}

LIST_ALIASES = {
    "realized_failure_mode_ids": "realized_failure_mode_ids_json",
    "externality_tags": "externality_tags_json",
    "negative_externality_tags": "negative_externality_tags_json",
    "changed_by_forecast_ids": "changed_by_forecast_ids_json",
}


def _load_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"resolve payload must be JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"resolve payload must be a JSON object: {path}")
    return payload


def _as_json_list(value: Any, field: str) -> str:
    if isinstance(value, str):
        parsed = forecast_pool.parse_json_list(value, f"{field} JSON")
        return json.dumps(parsed)
    if not isinstance(value, list):
        raise SystemExit(f"{field} must be a JSON list or encoded JSON list")
    return json.dumps([str(item) for item in value])


def namespace_from_payload(payload: dict[str, Any], *,
                           allow_extra: bool = False) -> argparse.Namespace:
    fields = dict(DEFAULTS)
    allowed = set(DEFAULTS) | {"contract_id"} | set(LIST_ALIASES)
    extra = sorted(set(payload) - allowed)
    if extra and not allow_extra:
        raise SystemExit("unknown resolve payload fields: " + ", ".join(extra))
    if "contract_id" not in payload or not str(payload["contract_id"]).strip():
        raise SystemExit("resolve payload requires contract_id")
    fields["contract_id"] = str(payload["contract_id"])
    for key, value in payload.items():
        if key in LIST_ALIASES:
            fields[LIST_ALIASES[key]] = _as_json_list(value, key)
        elif key in fields:
            fields[key] = value
    for key in (
        "realized_failure_mode_ids_json",
        "externality_tags_json",
        "negative_externality_tags_json",
        "changed_by_forecast_ids_json",
    ):
        fields[key] = _as_json_list(fields[key], key)
    if fields["success_bool"] is None and not fields["voided"]:
        raise SystemExit("resolve payload requires success_bool unless voided is true")
    return argparse.Namespace(**fields)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", required=True, type=Path)
    ap.add_argument("--allow-extra", action="store_true")
    args = ap.parse_args(argv)
    payload = _load_payload(args.json)
    ns = namespace_from_payload(payload, allow_extra=args.allow_extra)
    return forecast_pool.cmd_resolve(ns)


if __name__ == "__main__":
    raise SystemExit(main())
