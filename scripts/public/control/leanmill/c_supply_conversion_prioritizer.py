#!/usr/bin/env python3
"""Policy-owned queue reprioritizer for strict C-supply conversion.

This is a routing controller only. It does not create work, validate proof
value, refresh timestamps to fake freshness, or mark rows credit-ready. It
changes queued priority for bounded C-supply repair/probe/source lanes so the
next claim favors underrepresented families and source breadth while the
factory is short of the strict C target.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY, c_supply_breadth_policy_from_policy, read_policy
from leanmill_paths import DATA_DIR


DEFAULT_OUT = f"{DATA_DIR}/c_supply_conversion_prioritizer.json"
DEFAULT_INTELLIGENCE = f"{DATA_DIR}/leanmill_factory_intelligence.json"
DEFAULT_QUEUE_DB = work_queue.DEFAULT_DB
DEFAULT_EVENTS = work_queue.DEFAULT_EVENTS

AGENT_KINDS = {"agent_repair_task", "subscription_agent_task", "agent_task", "agent_repair"}
CONVERSION_AGENT_MODES = {
    "c_supply_template_backfill",
    "family_spec_positive_repair",
    "family_birth_candidate",
}
SOURCE_KINDS = {"source_scout_task", "source_search_task", "llm_proposal_validate"}


def _now() -> int:
    return int(time.time())


def _read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _write_json(path: str | Path, obj: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _int(obj: dict[str, Any], key: str, fallback: int) -> int:
    try:
        return int(obj.get(key) if obj.get(key) is not None else fallback)
    except (TypeError, ValueError):
        return int(fallback)


def _bool(obj: dict[str, Any], key: str, fallback: bool) -> bool:
    val = obj.get(key)
    if val is None:
        return fallback
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _policy(policy: dict[str, Any]) -> dict[str, Any]:
    ops = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    obj = ops.get("c_supply_conversion_prioritizer") if isinstance(ops.get("c_supply_conversion_prioritizer"), dict) else {}
    priority = ops.get("priority_policy") if isinstance(ops.get("priority_policy"), dict) else {}
    formula = priority.get("formula_bases") if isinstance(priority.get("formula_bases"), dict) else {}
    workq = priority.get("work_queue") if isinstance(priority.get("work_queue"), dict) else {}
    floors = obj.get("priority_floors") if isinstance(obj.get("priority_floors"), dict) else {}

    def floor(key: str, fallback: int) -> int:
        return _int(floors, key, fallback)

    agent_base = _int(formula, "c_supply_template_backfill", 230)
    family_birth_base = _int(formula, "family_birth_candidate", 225)
    probe_base = _int(formula, "family_spec_activation_probe", _int(formula, "family_spec_probe", 140))
    source_base = _int(workq, "external_source_scout_seed", 160)
    return {
        "schema": "leanmill-c-supply-conversion-prioritizer-policy-v1",
        "source": "factory_policy" if obj else "fallback",
        "enabled": _bool(obj, "enabled", True),
        "max_updates_per_cycle": max(1, _int(obj, "max_updates_per_cycle", 80)),
        "max_examined": max(1, _int(obj, "max_examined", 400)),
        "per_family_full_priority_budget": max(1, _int(obj, "per_family_full_priority_budget", 2)),
        "same_family_priority_step_down": max(0, _int(obj, "same_family_priority_step_down", 3)),
        "allow_family_spread_demote": _bool(obj, "allow_family_spread_demote", True),
        "allow_demote_overrepresented": _bool(obj, "allow_demote_overrepresented", True),
        "priority_floors": {
            "agent_uncredited_family": floor("agent_uncredited_family", agent_base + 45),
            "agent_underrepresented_family": floor("agent_underrepresented_family", agent_base + 20),
            "agent_overrepresented_family": floor("agent_overrepresented_family", agent_base - 25),
            "family_birth_candidate": floor("family_birth_candidate", family_birth_base + 55),
            "probe_uncredited_family": floor("probe_uncredited_family", probe_base + 45),
            "probe_underrepresented_family": floor("probe_underrepresented_family", probe_base + 20),
            "probe_overrepresented_family": floor("probe_overrepresented_family", probe_base - 10),
            "source_uncredited_family": floor("source_uncredited_family", source_base + 35),
            "source_underrepresented_family": floor("source_underrepresented_family", source_base + 15),
            "source_overrepresented_family": floor("source_overrepresented_family", source_base - 20),
        },
        "rationale": str(
            obj.get("rationale")
            or (
                "When strict C count or breadth is short, queued conversion work should favor "
                "uncredited and underrepresented families before spending more agent/probe slots "
                "on already-concentrated families. This changes routing only; governance remains "
                "the proof-credit authority."
            )
        ),
    }


def _credit_model(intelligence: dict[str, Any], policy_obj: dict[str, Any]) -> dict[str, Any]:
    model = intelligence.get("c_supply_credit_ready_read_model")
    if not isinstance(model, dict):
        model = {}
    breadth = c_supply_breadth_policy_from_policy(policy_obj)
    credit_ready_count = _int(model, "credit_ready_count", 0)
    target_rows = int(breadth["target_credit_ready_rows"])
    minimum_rows = int(breadth.get("minimum_credit_ready_rows", target_rows))
    growth_goal_rows = int(breadth.get("growth_goal_credit_ready_rows", target_rows))
    counts = model.get("credit_ready_family_counts") if isinstance(model.get("credit_ready_family_counts"), dict) else {}
    clean_counts: dict[str, int] = {}
    for family, count in counts.items():
        try:
            clean_counts[str(family)] = int(count or 0)
        except (TypeError, ValueError):
            continue
    return {
        "credit_ready_count": credit_ready_count,
        "remaining_to_target": _int(model, "remaining_to_target", max(0, target_rows - credit_ready_count)),
        "remaining_to_growth_goal": _int(model, "remaining_to_growth_goal", max(0, growth_goal_rows - credit_ready_count)),
        "target_credit_ready_rows": _int(model, "target_credit_ready_rows", target_rows),
        "minimum_credit_ready_rows": _int(model, "minimum_credit_ready_rows", minimum_rows),
        "growth_goal_credit_ready_rows": _int(model, "growth_goal_credit_ready_rows", growth_goal_rows),
        "continue_after_minimum_floor": bool(breadth.get("continue_after_minimum_floor", True)),
        "credit_ready_family_counts": clean_counts,
        "breadth_policy": breadth,
        "breadth_blockers": model.get("breadth_blockers") if isinstance(model.get("breadth_blockers"), list) else [],
    }


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        obj = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _family(row: sqlite3.Row, payload: dict[str, Any]) -> str:
    return str(payload.get("family") or row["family"] or "")


def _work_class(kind: str, payload: dict[str, Any]) -> str:
    if kind in AGENT_KINDS:
        mode = str(payload.get("family_spec_patch_mode") or "")
        if mode in CONVERSION_AGENT_MODES:
            return f"agent:{mode}"
    if kind == "repair_canary_probe" and str(payload.get("probe_lane") or "") == "family_spec":
        return "probe:family_spec"
    if kind in SOURCE_KINDS:
        expected = str(payload.get("expected_outcome") or payload.get("expected_exit") or "")
        mode = str(payload.get("source_scout_mode") or "")
        if expected == "source_request" or mode == "subscription_public_external" or kind == "source_search_task":
            return f"source:{kind}"
    return ""


def _target_priority(
    *,
    work_class: str,
    family_count: int,
    max_per_family: int,
    floors: dict[str, int],
) -> int:
    overrepresented = family_count >= max_per_family
    uncredited = family_count <= 0
    if work_class == "agent:family_birth_candidate":
        return int(floors["family_birth_candidate"])
    if work_class.startswith("agent:"):
        if uncredited:
            return int(floors["agent_uncredited_family"])
        if overrepresented:
            return int(floors["agent_overrepresented_family"])
        return int(floors["agent_underrepresented_family"])
    if work_class == "probe:family_spec":
        if uncredited:
            return int(floors["probe_uncredited_family"])
        if overrepresented:
            return int(floors["probe_overrepresented_family"])
        return int(floors["probe_underrepresented_family"])
    if work_class.startswith("source:"):
        if uncredited:
            return int(floors["source_uncredited_family"])
        if overrepresented:
            return int(floors["source_overrepresented_family"])
        return int(floors["source_underrepresented_family"])
    return 0


def _priority_with_family_spread(base: int, *, family_rank: int, policy_rec: dict[str, Any]) -> int:
    free = int(policy_rec["per_family_full_priority_budget"])
    step = int(policy_rec["same_family_priority_step_down"])
    if family_rank <= free or step <= 0:
        return int(base)
    return max(1, int(base) - (family_rank - free) * step)


def _candidate_rows(cx: sqlite3.Connection, *, limit: int) -> list[sqlite3.Row]:
    return cx.execute(
        """
        SELECT *
        FROM work_items
        WHERE status='queued'
          AND attempts < max_attempts
          AND kind IN (
            'agent_repair_task',
            'subscription_agent_task',
            'agent_task',
            'agent_repair',
            'repair_canary_probe',
            'source_scout_task',
            'source_search_task',
            'llm_proposal_validate'
          )
        ORDER BY priority DESC, created_at ASC
        LIMIT ?
        """,
        (max(1, int(limit)),),
    ).fetchall()


def prioritize(args: argparse.Namespace) -> dict[str, Any]:
    policy_obj = read_policy(args.factory_policy)
    policy_rec = _policy(policy_obj)
    intelligence = _read_json(args.intelligence)
    credit = _credit_model(intelligence, policy_obj)
    now = _now()
    result: dict[str, Any] = {
        "schema": "leanmill-c-supply-conversion-prioritizer-v1",
        "generated_at_epoch": now,
        "queue_db": args.queue_db,
        "intelligence": args.intelligence,
        "factory_policy": args.factory_policy,
        "policy": policy_rec,
        "credit_model": credit,
        "examined": 0,
        "eligible": 0,
        "updated": 0,
        "skipped": [],
        "updates": [],
        "status": "skipped",
        "reason": "",
    }
    if not policy_rec["enabled"]:
        result["reason"] = "policy_disabled"
        _write_json(args.out, result)
        return result
    if (
        not bool(credit.get("continue_after_minimum_floor", True))
        and int(credit["remaining_to_target"]) <= 0
        and not credit["breadth_blockers"]
    ):
        result["reason"] = "strict_c_minimum_and_breadth_satisfied"
        _write_json(args.out, result)
        return result
    if (
        bool(credit.get("continue_after_minimum_floor", True))
        and int(credit.get("remaining_to_growth_goal", 0)) <= 0
        and not credit["breadth_blockers"]
    ):
        result["reason"] = "strict_c_growth_goal_and_breadth_satisfied"
        _write_json(args.out, result)
        return result

    cx = work_queue.connect(args.queue_db)
    rows = _candidate_rows(cx, limit=int(policy_rec["max_examined"]))
    result["examined"] = len(rows)
    family_rank: Counter[str] = Counter()
    by_class: Counter[str] = Counter()
    by_family: Counter[str] = Counter()
    updates: list[dict[str, Any]] = []
    floors = policy_rec["priority_floors"]
    max_per_family = int(credit["breadth_policy"]["max_credit_ready_rows_per_family_before_warning"])
    credit_counts = credit["credit_ready_family_counts"]
    for row in rows:
        payload = _payload(row)
        work_class = _work_class(str(row["kind"]), payload)
        if not work_class:
            continue
        family = _family(row, payload)
        if not family:
            continue
        result["eligible"] += 1
        family_rank[family] += 1
        by_class[work_class] += 1
        by_family[family] += 1
        old_priority = int(row["priority"])
        family_count = int(credit_counts.get(family, 0))
        target = _target_priority(
            work_class=work_class,
            family_count=family_count,
            max_per_family=max_per_family,
            floors=floors,
        )
        target = _priority_with_family_spread(target, family_rank=family_rank[family], policy_rec=policy_rec)
        overrepresented = family_count >= max_per_family
        family_spread_demote = (
            target < old_priority
            and family_rank[family] > int(policy_rec["per_family_full_priority_budget"])
            and bool(policy_rec["allow_family_spread_demote"])
        )
        overrepresented_demote = overrepresented and bool(policy_rec["allow_demote_overrepresented"]) and target < old_priority
        should_update = target > old_priority or family_spread_demote or overrepresented_demote
        if not should_update:
            continue
        reason = (
            "uncredited_family_conversion_priority"
            if family_count <= 0 and target > old_priority else
            "same_family_spread_deprioritized"
            if family_spread_demote else
            "overrepresented_family_deprioritized"
            if overrepresented_demote else
            "underrepresented_family_conversion_priority"
        )
        updates.append({
            "work_id": row["work_id"],
            "kind": row["kind"],
            "work_class": work_class,
            "family": family,
            "old_priority": old_priority,
            "new_priority": int(target),
            "credit_ready_family_count": family_count,
            "reason": reason,
        })
        if len(updates) >= int(policy_rec["max_updates_per_cycle"]):
            break

    if not args.dry_run and updates:
        for rec in updates:
            # Deliberately leave updated_at unchanged. This is queue routing, not
            # candidate freshness; the restart gate must not be satisfied by a
            # timestamp-only priority refresh.
            cx.execute(
                "UPDATE work_items SET priority=? WHERE work_id=? AND status='queued'",
                (int(rec["new_priority"]), str(rec["work_id"])),
            )
        cx.commit()
        work_queue.append_event(args.events, {
            "event_type": "c_supply_conversion_priorities_rebalanced",
            "payload": {
                "updated": len(updates),
                "dry_run": False,
                "credit_model": credit,
                "by_class_examined": dict(sorted(by_class.items())),
                "by_family_examined": dict(sorted(by_family.items())),
                "updates": updates[:80],
                "policy_rationale": policy_rec["rationale"],
            },
            "artifact_paths": [args.out],
        })
    cx.close()

    result.update({
        "status": "pass",
        "dry_run": bool(args.dry_run),
        "updated": len(updates),
        "updates": updates,
        "by_class_examined": dict(sorted(by_class.items())),
        "by_family_examined": dict(sorted(by_family.items())),
    })
    _write_json(args.out, result)
    return result


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_c_supply_prioritizer_") as td:
        root = Path(td)
        db = str(root / "q.sqlite")
        events = str(root / "events.jsonl")
        intelligence = root / "intel.json"
        policy = root / "policy.json"
        out = root / "out.json"
        policy.write_text(json.dumps({
            "operations": {
                "c_supply_breadth_policy": {
                    "target_credit_ready_rows": 20,
                    "max_credit_ready_rows_per_family_before_warning": 4,
                },
                "c_supply_conversion_prioritizer": {
                    "enabled": True,
                    "max_updates_per_cycle": 10,
                    "per_family_full_priority_budget": 1,
                    "same_family_priority_step_down": 5,
                    "allow_family_spread_demote": True,
                    "priority_floors": {
                        "agent_uncredited_family": 280,
                        "agent_underrepresented_family": 250,
                        "agent_overrepresented_family": 200,
                        "probe_uncredited_family": 270,
                        "probe_underrepresented_family": 240,
                        "probe_overrepresented_family": 190,
                        "source_uncredited_family": 220,
                        "source_underrepresented_family": 200,
                        "source_overrepresented_family": 150,
                        "family_birth_candidate": 290,
                    },
                },
            }
        }) + "\n")
        intelligence.write_text(json.dumps({
            "c_supply_credit_ready_read_model": {
                "credit_ready_count": 15,
                "remaining_to_target": 5,
                "credit_ready_family_counts": {"over": 4, "some": 1, "low": 1},
                "breadth_blockers": ["family_breadth_target_not_met"],
            }
        }) + "\n")
        cx = work_queue.connect(db)
        work_queue.enqueue(cx, kind="agent_repair_task", priority=230, payload={
            "work_id": "over-agent",
            "family": "over",
            "family_spec_patch_mode": "family_spec_positive_repair",
        })
        work_queue.enqueue(cx, kind="agent_repair_task", priority=210, payload={
            "work_id": "new-agent-1",
            "family": "new",
            "family_spec_patch_mode": "family_spec_positive_repair",
        })
        work_queue.enqueue(cx, kind="agent_repair_task", priority=210, payload={
            "work_id": "new-agent-2",
            "family": "new",
            "family_spec_patch_mode": "family_spec_positive_repair",
        })
        work_queue.enqueue(cx, kind="repair_canary_probe", priority=1000, payload={
            "work_id": "some-probe",
            "family": "some",
            "probe_lane": "family_spec",
        })
        work_queue.enqueue(cx, kind="repair_canary_probe", priority=999, payload={
            "work_id": "some-probe-2",
            "family": "some",
            "probe_lane": "family_spec",
        })
        work_queue.enqueue(cx, kind="repair_canary_probe", priority=140, payload={
            "work_id": "low-probe",
            "family": "low",
            "probe_lane": "family_spec",
        })
        res = prioritize(argparse.Namespace(
            queue_db=db,
            events=events,
            intelligence=str(intelligence),
            factory_policy=str(policy),
            out=str(out),
            dry_run=False,
        ))
        assert res["updated"] == 5, res
        rows = {
            row["work_id"]: row["priority"]
            for row in cx.execute("SELECT work_id, priority FROM work_items").fetchall()
        }
        assert rows["new-agent-1"] == 280, rows
        assert rows["new-agent-2"] == 275, rows
        assert rows["over-agent"] == 200, rows
        assert rows["some-probe"] == 1000, rows
        assert rows["some-probe-2"] == 235, rows
        assert rows["low-probe"] == 240, rows
        assert any(
            rec["work_id"] == "some-probe-2" and rec["reason"] == "same_family_spread_deprioritized"
            for rec in res["updates"]
        ), res["updates"]
        assert "c_supply_conversion_priorities_rebalanced" in Path(events).read_text()
        cx.close()
    print("leanmill_c_supply_conversion_prioritizer self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=DEFAULT_QUEUE_DB)
    ap.add_argument("--events", default=DEFAULT_EVENTS)
    ap.add_argument("--intelligence", default=DEFAULT_INTELLIGENCE)
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = prioritize(args)
    print(json.dumps({
        "status": result.get("status"),
        "updated": result.get("updated"),
        "eligible": result.get("eligible"),
        "out": args.out,
        "reason": result.get("reason"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
