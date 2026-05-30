#!/usr/bin/env python3
"""Shared source-routing helpers for LeanMill upstream lanes."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from leanmill_factory_config import FACTORY_POLICY, read_policy


def source_growth_routing_policy(factory_policy: str | Path = FACTORY_POLICY) -> dict[str, Any]:
    policy = read_policy(factory_policy)
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    obj = operations.get("c_supply_source_growth_routing") if isinstance(operations.get("c_supply_source_growth_routing"), dict) else {}
    return {
        "schema": str(obj.get("schema") or "leanmill-c-supply-source-growth-routing-policy-v1"),
        "source": "factory_policy.operations.c_supply_source_growth_routing" if obj else "controller_default",
        "credit_boundary": str(obj.get("credit_boundary") or "Source-growth routing chooses mining/scout spend only; it grants no C, proof, benchmark, or governance credit."),
        "recent_ratified_seed_promotion_enabled": bool(obj.get("recent_ratified_seed_promotion_enabled", False)),
        "recent_ratified_seed_window_s": int(obj.get("recent_ratified_seed_window_s") or 6 * 60 * 60),
        "recent_ratified_seed_max_promoted_families": int(obj.get("recent_ratified_seed_max_promoted_families") or 2),
        "recent_ratified_seed_prefer_zero_source_spend": bool(obj.get("recent_ratified_seed_prefer_zero_source_spend", False)),
        "ordering_rule": str(obj.get("ordering_rule") or "Apply validated upstream rater order, then move up to N recent ratified-seed families to the front while preserving their relative order."),
        "rationale": str(obj.get("rationale") or "A newly born family with a fresh ratified seed probe needs at least one downstream source pass; otherwise an agentic birth can stall behind older families before conversion potential is measured."),
    }


def recent_ratified_seed_families(queue_db: str | Path, *, window_s: int, now: int | None = None) -> set[str]:
    if not queue_db or not Path(queue_db).exists():
        return set()
    cutoff = int(now if now is not None else time.time()) - max(0, int(window_s))
    out: set[str] = set()
    cx: sqlite3.Connection | None = None
    try:
        cx = sqlite3.connect(str(queue_db))
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            """
            SELECT family, payload_json
            FROM work_items
            WHERE kind='repair_canary_probe'
              AND status='done'
              AND updated_at >= ?
            """,
            (cutoff,),
        ).fetchall()
    except sqlite3.Error:
        return set()
    finally:
        if cx is not None:
            cx.close()
    for row in rows:
        family = str(row["family"] or "")
        if not family:
            continue
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        if str(payload.get("exit_kind") or payload.get("learning_unit_exit") or "") == "ratified_closure":
            out.add(family)
            continue
        for outcome in payload.get("row_outcomes") or []:
            if isinstance(outcome, dict) and int(outcome.get("ratified_closure_count") or 0) > 0:
                out.add(family)
                break
    return out


def promote_recent_ratified_seed_records(
    records: list[dict[str, Any]],
    *,
    policy: dict[str, Any],
    recent_families: set[str],
    family_key: str = "family",
    eligible_status_key: str | None = None,
    eligible_status_value: str = "written",
) -> tuple[list[dict[str, Any]], list[str]]:
    if not bool(policy.get("recent_ratified_seed_promotion_enabled")) or not recent_families:
        return records, []
    limit = max(0, int(policy.get("recent_ratified_seed_max_promoted_families") or 0))
    if limit <= 0:
        return records, []
    promoted: list[dict[str, Any]] = []
    rest: list[dict[str, Any]] = []
    promoted_families: list[str] = []
    for record in records:
        family = str(record.get(family_key) or "") if isinstance(record, dict) else ""
        status_ok = True
        if eligible_status_key:
            status_ok = str(record.get(eligible_status_key) or "") == eligible_status_value
        if len(promoted) < limit and family in recent_families and status_ok:
            promoted.append(record)
            promoted_families.append(family)
        else:
            rest.append(record)
    return [*promoted, *rest], promoted_families


def order_recent_seed_records_for_source_scout(
    records: list[dict[str, Any]],
    *,
    policy: dict[str, Any],
    recent_families: set[str],
) -> list[dict[str, Any]]:
    if not bool(policy.get("recent_ratified_seed_prefer_zero_source_spend")) or not recent_families:
        return records

    def source_spend(record: dict[str, Any]) -> int:
        source_quality = record.get("source_quality") if isinstance(record.get("source_quality"), dict) else {}
        fields = (
            "source_attempts",
            "source_binding_spend",
            "source_binding_probe_done",
            "source_binding_probe_enqueued",
            "source_search_canary_ready_total",
        )
        total = 0
        for field in fields:
            try:
                total += int(source_quality.get(field) or 0)
            except (TypeError, ValueError):
                continue
        return total

    return sorted(
        records,
        key=lambda record: (
            0 if str(record.get("family") or "") in recent_families else 1,
            source_spend(record) if str(record.get("family") or "") in recent_families else 0,
        ),
    )
