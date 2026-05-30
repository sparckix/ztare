#!/usr/bin/env python3
"""Seed subscription-agent public-source scouting tasks for LeanMill.

This lane is intentionally upstream of proof value. Subscription agents may
look for public Lean/mathlib source leads when their runtime supports external
lookup, but their output must be typed source-query JSON. Downstream gates then
run LeanSearch/static qualification before any proof probe exists.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
import sys
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, priority_value, read_policy
from leanmill_family_specs import load_specs
from leanmill_source_routing import (
    order_recent_seed_records_for_source_scout,
    promote_recent_ratified_seed_records,
    recent_ratified_seed_families,
    source_growth_routing_policy,
)


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_ALLOCATOR = f"{DEFAULT_DATA_DIR}/source_family_allocator.json"
DEFAULT_SOURCE_PLAN = f"{DEFAULT_DATA_DIR}/residual_family_source_plan.json"
DEFAULT_BENCHMARK_PREP = f"{DEFAULT_DATA_DIR}/evaluation_harness_prep.json"
DEFAULT_OUT = f"{DEFAULT_DATA_DIR}/external_source_scout_seed_plan.json"
DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_EXPAND100_CORPUS = f"{DEFAULT_DATA_DIR}/mcb_expand100_active_corpus.json"
DEFAULT_EXTRA_CORPUS = [
    "/tmp/rung1/mcb_refill_dedup_after_expand100/mcb_corpus.json",
    DEFAULT_EXPAND100_CORPUS,
    "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_QUEUE.json",
]
DEFAULT_SPEC_DIR = "analytics/public/leanmill/repair_families"


def _queue_priority(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY),
        namespace="work_queue",
        key=key,
        fallback=fallback,
    )


FAMILY_HINTS: dict[str, list[str]] = {
    "ennreal_tsum_condensation_planner": ["ENNReal", "tsum", "Summable", "NNReal", "condensation"],
    "convolution_argument_planner": ["MeasureTheory", "convolution", "mconv", "conv", "lintegral"],
    "complex_limit_causeq_planner": ["Complex", "CauSeq", "norm", "tendsto", "exp"],
    "cusp_function_qparam_periodic_planner": ["periodic", "cusp", "qParam", "eventually", "isLo"],
    "iff_direction_planner": ["iff", "constructor", "geom_mean", "arith_mean", "weighted"],
    "gram_posdef_linear_independent_planner": ["Matrix.PosDef", "Gram", "LinearIndependent"],
    "interval_alignment_planner": ["Ioc", "interval", "sum", "Nat", "Finset"],
    "lpnorm_hasSum_packaging_planner": ["Lp", "HasSum", "Summable", "ENNReal", "norm"],
    "spectral_eigenvalue_nonneg_planner": ["spectrum", "eigenvalue", "nonneg", "SelfAdjoint"],
    "spectral_rayleigh_extremum_planner": ["Rayleigh", "spectrum", "Eigen", "InnerProductSpace"],
}

SOURCE_SCOUT_BLOCK_ACTIONS = {
    "do_not_spend_until_new_evidence",
    "hold_source_binding_until_new_target_evidence",
    "repair_source_strategy_before_more_binding",
}


def _read(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _apply_policy_profile(args: argparse.Namespace) -> dict[str, Any]:
    profile_name = str(getattr(args, "policy_profile", "") or "")
    if not profile_name:
        return {"name": "", "key_count": 0, "keys": []}
    policy = read_policy(getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY))
    profile = ((policy.get("profiles") or {}).get(profile_name) or {}) if isinstance(policy.get("profiles"), dict) else {}
    runner = profile.get("runner") if isinstance(profile, dict) else {}
    runner = runner if isinstance(runner, dict) else {}
    applied: dict[str, Any] = {}
    mapping = {
        "external_source_scout_runtimes": "runtimes",
        "external_source_scout_max_families": "max_families",
        "external_source_scout_tasks_per_family": "tasks_per_family",
        "external_source_scout_max_target_rows": "max_target_rows",
        "external_source_scout_avoid_open_family_duplicates": "avoid_open_family_duplicates",
        "agent_max_iterations": "agent_max_iterations",
        "agent_max_wall_time_s": "agent_max_wall_time_s",
    }
    for policy_key, arg_key in mapping.items():
        if policy_key in runner and hasattr(args, arg_key):
            setattr(args, arg_key, runner[policy_key])
            applied[arg_key] = runner[policy_key]
    if int(getattr(args, "max_enqueued", 0) or 0) <= 0 and "external_source_scout_max_enqueued" in runner:
        args.max_enqueued = runner["external_source_scout_max_enqueued"]
        applied["max_enqueued"] = runner["external_source_scout_max_enqueued"]
    receipt = {
        "name": profile_name,
        "path": str(getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY)),
        "section": "runner",
        "key_count": len(applied),
        "keys": sorted(applied),
        "source": "factory_policy.profile.runner",
        "credit_boundary": "Policy application selects source-scout routing only; it grants no proof or C credit.",
    }
    setattr(args, "_policy_profile_runner_applied", receipt)
    return receipt


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _row_records(obj: Any) -> list[Any]:
    if isinstance(obj, list):
        return obj
    if not isinstance(obj, dict):
        return []
    for key in ("rows", "source_discovery_queue", "queue", "items"):
        rows = obj.get(key)
        if isinstance(rows, list):
            return rows
    return []


def _spec_hints_by_family(spec_dir: str | Path = DEFAULT_SPEC_DIR) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for spec in load_specs(spec_dir):
        family = str(spec.get("family") or "").strip()
        if not family:
            continue
        match = spec.get("residual_match") if isinstance(spec.get("residual_match"), dict) else {}
        hints: list[str] = []
        for key in ("head_patterns", "lanes", "residual_classes", "row_ids"):
            values = match.get(key) if isinstance(match.get(key), list) else []
            for value in values:
                text = str(value or "").strip()
                if text and text not in hints:
                    hints.append(text)
        out[family] = hints[:16]
    return out


def _family_hints(family: str, spec_hints: dict[str, list[str]]) -> list[str]:
    hints = list(FAMILY_HINTS.get(family, []))
    for hint in spec_hints.get(family, []):
        if hint not in hints:
            hints.append(hint)
    return hints[:16]


def _active_rows_by_id(paths: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in paths:
        obj = _read(path)
        for row in _row_records(obj):
            if not isinstance(row, dict):
                continue
            rid = str(row.get("row_id") or row.get("id") or "")
            if not rid or rid in out:
                continue
            out[rid] = {
                "row_id": rid,
                "source": "active_corpus",
                "corpus_path": path,
                "source_file": row.get("source_file") or row.get("sorried_file") or row.get("source"),
                "goal": str(row.get("goal") or row.get("source_hinge") or "")[:500],
            }
    return out


def _active_row(active: dict[str, dict[str, Any]], row_id: str, *, source: str, extra: dict[str, Any] | None = None) -> dict[str, Any] | None:
    row = active.get(str(row_id or ""))
    if not row:
        return None
    out = dict(row)
    out["source"] = source
    if extra:
        out.update({k: v for k, v in extra.items() if v is not None})
    return out


def _family_rows(
    source_plan: dict[str, Any],
    benchmark: dict[str, Any],
    family: str,
    *,
    limit: int,
    active: dict[str, dict[str, Any]],
    hints: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for packet in source_plan.get("packets") or []:
        if str(packet.get("repair_family") or "") != family:
            continue
        for row_id in [*(packet.get("rows") or []), *(packet.get("seed_rows") or [])]:
            rid = str(row_id or "")
            row = _active_row(active, rid, source="source_plan")
            if row and rid not in seen:
                seen.add(rid)
                rows.append(row)
        for lead in packet.get("top_leads") or []:
            if not isinstance(lead, dict):
                continue
            rid = str(lead.get("row_id") or "")
            row = _active_row(active, rid, source="source_plan_top_lead")
            if row and rid not in seen:
                seen.add(rid)
                rows.append(row)
    hint_set = {h.lower() for h in hints}
    for bucket in (benchmark.get("tiers") or {}).values():
        for row in bucket if isinstance(bucket, list) else []:
            if not isinstance(row, dict):
                continue
            rid = str(row.get("row_id") or "")
            if not rid or rid in seen:
                continue
            active_row = _active_row(active, rid, source="evaluation_harness_prep", extra={
                "source_file": row.get("source_file"),
                "candidate_count": row.get("candidate_count"),
                "row_context_resolved_count": row.get("row_context_resolved_count"),
            })
            if not active_row:
                continue
            hay = " ".join(str(row.get(k) or "") for k in ("row_id", "source_file", "status")).lower()
            if hint_set and not any(h in hay for h in hint_set):
                continue
            seen.add(rid)
            rows.append(active_row)
            if len(rows) >= limit:
                return rows
    if hint_set:
        for active_row in active.values():
            rid = str(active_row.get("row_id") or "")
            if not rid or rid in seen:
                continue
            hay = " ".join(str(active_row.get(k) or "") for k in ("row_id", "source_file", "goal")).lower()
            if not any(h in hay for h in hint_set):
                continue
            seen.add(rid)
            row = dict(active_row)
            row["source"] = "active_corpus_family_hint"
            rows.append(row)
            if len(rows) >= limit:
                return rows
    return rows[:limit]


def _prompt(*, family: str, allocator_record: dict[str, Any], rows: list[dict[str, Any]], runtime: str, hints: list[str]) -> str:
    return f"""You are a LeanMill public-source scout for one repair family.

Use the local mathlib lemma index if useful
(`analytics/public/queries/lean/mathlib_lemma_index.json`), public Lean/mathlib
knowledge, and external lookup if your CLI runtime supports it (mathlib docs,
LeanSearch-style declaration names, GitHub mathlib source, public theorem names).
Do not rely on private files or unavailable proof bodies. Do not claim proof value.

Return exactly one JSON object. Prefer this shape:
{{
  "family": "{family}",
  "proposal_type": "source_request",
  "hypothesis": "... why these declarations/source shapes fit the target rows ...",
  "credit_type": "none",
  "expected_outcome": "source_request",
  "source_query": [
    {{"schema":"leanmill-source-query-contract-v1","kind":"declaration_ref","decl_name":"Namespace.decl_name","rationale":"..."}},
    {{"schema":"leanmill-source-query-contract-v1","kind":"theorem_shape","query":"lemma ... : ...","rationale":"..."}}
  ],
  "target_row_ids": ["..."],
  "sibling_or_heldout_constraints": ["..."],
  "source_order_risks": ["..."],
  "target_context_risks": ["..."],
  "negative_control_ideas": ["..."]
}}

Hard rules:
- Emit 5-8 `source_query` entries so downstream pruning can still leave enough usable leads.
- Use theorem/declaration names or compact Lean theorem shapes, not broad topics.
- For `kind:"declaration_ref"`, `decl_name` must be namespaced and contain a dot
  such as `ENNReal.tsum_eq_iSup_sum`, `MeasureTheory.MeasurePreserving.lintegral_comp`,
  or `Filter.Tendsto.comp`. Unqualified names like `HasSum` or `tsum_eq` are rejected.
- For `kind:"theorem_shape"`, include structural Lean signals: constants, binders,
  theorem head, carrier type, or target relation. Do not emit one-word topics.
- `target_row_ids` must be copied exactly from the active target rows below.
- Do not use row IDs from memory, older benchmark prep, source-plan hints, or query text unless that row ID is listed below.
- If no safe public-source route exists, emit `proposal_type:"decomposition"`,
  `expected_outcome:"hold"` or `"retire"`, and a concrete blocked edge.
- This is source inventory only. Governance Gate is the only proof-credit authority.
- Do not edit registries, scoreboards, governance receipts, or research logs.

Runtime: {runtime}
Family: {family}
Family hints: {json.dumps(hints, sort_keys=True)}
Allocator record:
{json.dumps(allocator_record, indent=2, sort_keys=True)[:5000]}
Target rows:
{json.dumps(rows, indent=2, sort_keys=True)[:5000]}
"""


def _work_exists(cx: Any, work_id: str) -> bool:
    return cx.execute("SELECT 1 FROM work_items WHERE work_id=? LIMIT 1", (work_id,)).fetchone() is not None


def _open_source_scout_family_counts(queue_db: str | Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    p = Path(queue_db)
    if not p.exists():
        return counts
    cx = work_queue.connect(str(p))
    try:
        rows = cx.execute(
            "SELECT payload_json FROM work_items WHERE kind='source_scout_task' AND status IN ('queued','running')"
        ).fetchall()
    finally:
        cx.close()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
        family = str(payload.get("family") or "").strip()
        if family:
            counts[family] += 1
    return counts


def build(args: argparse.Namespace) -> dict[str, Any]:
    allocator = _read(args.allocator)
    source_plan = _read(args.source_plan)
    benchmark = _read(args.benchmark_prep)
    corpus_paths = [str(args.corpus or ""), *[str(p or "") for p in (args.extra_corpus or [])]]
    active = _active_rows_by_id([p for p in corpus_paths if p])
    spec_hints = _spec_hints_by_family()
    run_id = args.run_id or str(int(time.time()))
    runtimes = [r.strip() for r in args.runtimes.split(",") if r.strip()]
    avoid_open_family_duplicates = bool(getattr(args, "avoid_open_family_duplicates", True))
    open_family_counts = _open_source_scout_family_counts(args.queue_db) if avoid_open_family_duplicates else Counter()
    records = [
        rec for rec in (allocator.get("allocations") or [])
        if isinstance(rec, dict)
        and str(rec.get("family") or "")
        and str(rec.get("recommended_action") or "") not in SOURCE_SCOUT_BLOCK_ACTIONS
    ]
    records.sort(key=lambda r: float(r.get("yield_score") or 0.0), reverse=True)
    routing_policy = source_growth_routing_policy(getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY))
    recent_families = recent_ratified_seed_families(
        args.queue_db,
        window_s=int(routing_policy.get("recent_ratified_seed_window_s") or 0),
    )
    promotion_recent_families = set(recent_families)
    if avoid_open_family_duplicates:
        promotion_recent_families = {family for family in promotion_recent_families if open_family_counts.get(family, 0) <= 0}
    records = order_recent_seed_records_for_source_scout(
        records,
        policy=routing_policy,
        recent_families=promotion_recent_families,
    )
    records, promoted_families = promote_recent_ratified_seed_records(
        records,
        policy=routing_policy,
        recent_families=promotion_recent_families,
    )
    jobs: list[dict[str, Any]] = []
    skipped_open_family: list[dict[str, Any]] = []
    for rec in records[: max(0, args.max_families)]:
        family = str(rec.get("family") or "")
        if avoid_open_family_duplicates and open_family_counts.get(family, 0) > 0:
            skipped_open_family.append({
                "family": family,
                "open_count": int(open_family_counts.get(family, 0)),
                "yield_score": rec.get("yield_score"),
            })
            continue
        hints = _family_hints(family, spec_hints)
        rows = _family_rows(source_plan, benchmark, family, limit=args.max_target_rows, active=active, hints=hints)
        if not rows:
            continue
        for runtime in runtimes[: max(1, args.tasks_per_family)]:
            work_id = f"external_source_scout:{_slug(family)}:{_slug(runtime)}:{run_id}"
            jobs.append({
                "kind": "source_scout_task",
                "priority": int(args.priority + float(rec.get("yield_score") or 0.0)),
                "work_id": work_id,
                "payload": {
                    "work_id": work_id,
                    "runtime": runtime,
                    "agent_id": f"leanmill_{runtime}_external_source_scout",
                    "station": "source_qualification",
                    "family": family,
                    "task": _prompt(family=family, allocator_record=rec, rows=rows, runtime=runtime, hints=hints),
                    "expected_exit": "source_request",
                    "source_scout_mode": "subscription_public_external",
                    "target_rows": rows,
                    "allowed_paths": [
                        "analytics/public/leanmill",
                        "analytics/public/queries/lean/mathlib_lemma_index.json",
                        "scripts/public/control",
                        "src/ztare/common",
                        "/tmp/rung1",
                    ],
                    "requires_negative_control": False,
                    "proof_affecting": False,
                    "max_iterations": args.agent_max_iterations,
                    "max_wall_time_s": args.agent_max_wall_time_s,
                    "credit_boundary": {
                        "source_search_has_no_proof_credit": True,
                        "proof_credit_authority": "governance_gate",
                        "worker_can_self_ratify": False,
                    },
                },
            })
    payload = {
        "schema": "leanmill-external-source-scout-seed-plan-v1",
        "generated_at_epoch": int(time.time()),
        "dry_run": not args.enqueue,
        "policy_profile_application": getattr(args, "_policy_profile_runner_applied", {"name": "", "key_count": 0, "keys": []}),
        "job_count": len(jobs),
        "active_corpus_paths": [p for p in corpus_paths if p],
        "active_row_count": len(active),
        "avoid_open_family_duplicates": avoid_open_family_duplicates,
        "open_source_scout_family_counts": dict(sorted(open_family_counts.items())),
        "source_growth_routing_policy": {
            **routing_policy,
            "recent_ratified_seed_family_count": len(recent_families),
            "recent_ratified_seed_families_sample": sorted(recent_families)[:12],
            "recent_ratified_seed_open_family_suppressed": sorted(set(recent_families) - set(promotion_recent_families))[:12],
            "promoted_families": promoted_families,
            "credit_boundary": "source-scout family promotion routes upstream source inventory only; no proof, C, benchmark, or governance credit",
        },
        "spec_hint_family_count": len(spec_hints),
        "skipped_open_family_count": len(skipped_open_family),
        "skipped_open_families": skipped_open_family[:20],
        "jobs": jobs,
        "anti_laundering_rule": "External source scouts emit source_request proposals only; source retrieval/static filtering and Governance Gate own downstream truth.",
    }
    if args.enqueue:
        cx = work_queue.connect(args.queue_db)
        enqueued = 0
        skipped_existing = 0
        enqueued_jobs: list[dict[str, Any]] = []
        for job in jobs:
            if args.max_enqueued and enqueued >= args.max_enqueued:
                break
            if _work_exists(cx, str(job["work_id"])):
                skipped_existing += 1
                continue
            work_queue.enqueue(cx, kind=str(job["kind"]), priority=int(job["priority"]), payload=dict(job["payload"]), max_attempts=1)
            work_queue.append_event(args.events, {
                "event_type": "external_source_scout_enqueued",
                "work_id": job["work_id"],
                "payload": {
                    "family": job["payload"]["family"],
                    "runtime": job["payload"]["runtime"],
                    "target_row_count": len(job["payload"]["target_rows"]),
                    "expected_exit": job["payload"]["expected_exit"],
                },
            })
            enqueued += 1
            enqueued_jobs.append({
                "work_id": job["work_id"],
                "family": job["payload"]["family"],
                "runtime": job["payload"]["runtime"],
                "target_row_count": len(job["payload"]["target_rows"]),
            })
        payload["enqueued"] = enqueued
        payload["skipped_existing"] = skipped_existing
        payload["enqueued_jobs"] = enqueued_jobs
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_external_source_scout_") as td:
        allocator = Path(td) / "allocator.json"
        source_plan = Path(td) / "source_plan.json"
        benchmark = Path(td) / "benchmark.json"
        corpus = Path(td) / "corpus.json"
        db = Path(td) / "q.sqlite"
        events = Path(td) / "events.jsonl"
        allocator.write_text(json.dumps({"allocations": [{"family": "ennreal_tsum_condensation_planner", "yield_score": 10}]}) + "\n")
        source_plan.write_text(json.dumps({"packets": [{"repair_family": "ennreal_tsum_condensation_planner", "rows": ["MCB_A", "STALE"]}]}) + "\n")
        benchmark.write_text(json.dumps({"tiers": {"t": [{"row_id": "STALE", "source_file": "ENNReal.lean"}]}}) + "\n")
        corpus.write_text(json.dumps({"rows": [{"row_id": "MCB_A", "goal": "ENNReal tsum", "source_file": "active.lean"}]}) + "\n")
        out = Path(td) / "out.json"
        result = build(argparse.Namespace(
            allocator=str(allocator),
            source_plan=str(source_plan),
            benchmark_prep=str(benchmark),
            corpus=str(corpus),
            extra_corpus=[],
            out=str(out),
            queue_db=str(db),
            events=str(events),
            run_id="test",
            runtimes="codex,claude",
            max_families=1,
            tasks_per_family=2,
            max_target_rows=4,
            priority=100,
            factory_policy=DEFAULT_FACTORY_POLICY,
            policy_profile="",
            enqueue=True,
            max_enqueued=10,
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            avoid_open_family_duplicates=True,
        ))
        assert result["enqueued"] == 2
        assert result["jobs"][0]["payload"]["target_rows"][0]["row_id"] == "MCB_A"
        assert all(r["row_id"] != "STALE" for job in result["jobs"] for r in job["payload"]["target_rows"])
        fallback_rows = _family_rows(
            {},
            {},
            "needle_family",
            limit=2,
            active={"ROW_HINT": {"row_id": "ROW_HINT", "goal": "has special_needle bridge", "source_file": "Active.lean"}},
            hints=["special_needle"],
        )
        assert len(fallback_rows) == 1 and fallback_rows[0]["source"] == "active_corpus_family_hint", fallback_rows
        cx = work_queue.connect(str(db))
        assert cx.execute("SELECT COUNT(*) AS n FROM work_items WHERE kind='source_scout_task'").fetchone()["n"] == 2
        duplicate_family = build(argparse.Namespace(
            allocator=str(allocator),
            source_plan=str(source_plan),
            benchmark_prep=str(benchmark),
            corpus=str(corpus),
            extra_corpus=[],
            out=str(out),
            queue_db=str(db),
            events=str(events),
            run_id="second",
            runtimes="codex",
            max_families=1,
            tasks_per_family=1,
            max_target_rows=4,
            priority=100,
            factory_policy=DEFAULT_FACTORY_POLICY,
            policy_profile="",
            enqueue=False,
            max_enqueued=10,
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            avoid_open_family_duplicates=True,
        ))
        assert duplicate_family["job_count"] == 0 and duplicate_family["skipped_open_family_count"] == 1, duplicate_family
        allocator.write_text(json.dumps({"allocations": [{
            "family": "ennreal_tsum_condensation_planner",
            "yield_score": 10,
            "recommended_action": "hold_source_binding_until_new_target_evidence",
        }]}) + "\n")
        held = build(argparse.Namespace(
            allocator=str(allocator),
            source_plan=str(source_plan),
            benchmark_prep=str(benchmark),
            corpus=str(corpus),
            extra_corpus=[],
            out=str(out),
            queue_db=str(db),
            events=str(events),
            run_id="held",
            runtimes="codex,claude",
            max_families=1,
            tasks_per_family=2,
            max_target_rows=4,
            priority=100,
            factory_policy=DEFAULT_FACTORY_POLICY,
            policy_profile="",
            enqueue=False,
            max_enqueued=10,
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            avoid_open_family_duplicates=True,
        ))
        assert held["job_count"] == 0
        policy = Path(td) / "policy.json"
        policy.write_text(json.dumps({
            "profiles": {
                "unit": {
                    "runner": {
                        "external_source_scout_runtimes": "codex",
                        "external_source_scout_max_families": 1,
                        "external_source_scout_tasks_per_family": 1,
                        "external_source_scout_max_target_rows": 2,
                        "external_source_scout_avoid_open_family_duplicates": False,
                        "external_source_scout_max_enqueued": 1,
                        "agent_max_iterations": 2,
                        "agent_max_wall_time_s": 600,
                    },
                },
            },
        }) + "\n")
        policy_args = argparse.Namespace(
            allocator=str(allocator),
            source_plan=str(source_plan),
            benchmark_prep=str(benchmark),
            corpus=str(corpus),
            extra_corpus=[],
            out=str(out),
            queue_db=str(db),
            events=str(events),
            run_id="policy",
            runtimes="claude",
            max_families=8,
            tasks_per_family=2,
            max_target_rows=8,
            priority=100,
            factory_policy=str(policy),
            policy_profile="unit",
            enqueue=False,
            max_enqueued=0,
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            avoid_open_family_duplicates=True,
        )
        receipt = _apply_policy_profile(policy_args)
        assert receipt["key_count"] >= 6, receipt
        assert policy_args.runtimes == "codex" and policy_args.max_enqueued == 1, vars(policy_args)
        assert policy_args.avoid_open_family_duplicates is False, vars(policy_args)
        promoted_db = Path(td) / "promoted.sqlite"
        promoted_events = Path(td) / "promoted_events.jsonl"
        promoted_policy = Path(td) / "promoted_policy.json"
        promoted_allocator = Path(td) / "promoted_allocator.json"
        promoted_benchmark = Path(td) / "promoted_benchmark.json"
        promoted_corpus = Path(td) / "promoted_corpus.json"
        promoted_policy.write_text(json.dumps({
            "operations": {
                "c_supply_source_growth_routing": {
                    "recent_ratified_seed_promotion_enabled": True,
                    "recent_ratified_seed_window_s": 3600,
                    "recent_ratified_seed_max_promoted_families": 1,
                    "recent_ratified_seed_prefer_zero_source_spend": True,
                },
            },
        }) + "\n")
        promoted_allocator.write_text(json.dumps({"allocations": [
            {"family": "older_fam", "yield_score": 1000, "recommended_action": "review"},
            {"family": "fam_new", "yield_score": 1, "recommended_action": "seek_heldout_validation"},
        ]}) + "\n")
        promoted_benchmark.write_text(json.dumps({"tiers": {"t": [
            {"row_id": "ROW_NEW", "source_file": "FamNew.lean"},
            {"row_id": "ROW_OLD", "source_file": "Older.lean"},
        ]}}) + "\n")
        promoted_corpus.write_text(json.dumps({"rows": [
            {"row_id": "ROW_NEW", "goal": "fam new target", "source_file": "FamNew.lean"},
            {"row_id": "ROW_OLD", "goal": "older target", "source_file": "Older.lean"},
        ]}) + "\n")
        promoted_cx = work_queue.connect(str(promoted_db))
        work_queue.enqueue(promoted_cx, kind="repair_canary_probe", priority=1, payload={
            "work_id": "probe:fam_new:seed",
            "family": "fam_new",
            "exit_kind": "ratified_closure",
        })
        work_queue.update_status(promoted_cx, work_id="probe:fam_new:seed", status="done")
        work_queue.enqueue(promoted_cx, kind="repair_canary_probe", priority=1, payload={
            "work_id": "probe:older_fam:seed",
            "family": "older_fam",
            "exit_kind": "ratified_closure",
        })
        work_queue.update_status(promoted_cx, work_id="probe:older_fam:seed", status="done")
        work_queue.enqueue(promoted_cx, kind="source_scout_task", priority=1, payload={
            "work_id": "external_source_scout:older_fam:open",
            "family": "older_fam",
        })
        promoted = build(argparse.Namespace(
            allocator=str(promoted_allocator),
            source_plan=str(source_plan),
            benchmark_prep=str(promoted_benchmark),
            corpus=str(promoted_corpus),
            extra_corpus=[],
            out=str(out),
            queue_db=str(promoted_db),
            events=str(promoted_events),
            run_id="promoted",
            runtimes="codex",
            max_families=1,
            tasks_per_family=1,
            max_target_rows=2,
            priority=100,
            factory_policy=str(promoted_policy),
            policy_profile="",
            enqueue=False,
            max_enqueued=0,
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            avoid_open_family_duplicates=True,
        ))
        assert promoted["jobs"][0]["payload"]["family"] == "fam_new", promoted
        assert promoted["source_growth_routing_policy"]["promoted_families"] == ["fam_new"], promoted["source_growth_routing_policy"]
        assert "older_fam" in promoted["source_growth_routing_policy"]["recent_ratified_seed_open_family_suppressed"], promoted["source_growth_routing_policy"]
    print("leanmill_external_source_scout_seeder self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allocator", default=DEFAULT_ALLOCATOR)
    ap.add_argument("--source-plan", default=DEFAULT_SOURCE_PLAN)
    ap.add_argument("--benchmark-prep", default=DEFAULT_BENCHMARK_PREP)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--extra-corpus", action="append", default=list(DEFAULT_EXTRA_CORPUS))
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--runtimes", default="codex,claude")
    ap.add_argument("--max-families", type=int, default=8)
    ap.add_argument("--tasks-per-family", type=int, default=2)
    ap.add_argument("--max-target-rows", type=int, default=8)
    ap.add_argument("--avoid-open-family-duplicates", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--priority", type=int, default=160)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--enqueue", action="store_true")
    ap.add_argument("--max-enqueued", type=int, default=0)
    ap.add_argument("--agent-max-iterations", type=int, default=3)
    ap.add_argument("--agent-max-wall-time-s", type=int, default=1200)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    _apply_policy_profile(args)
    if int(args.priority) == 160:
        args.priority = _queue_priority(args, "external_source_scout_seed", 160)
    result = build(args)
    print(json.dumps({
        "dry_run": result["dry_run"],
        "job_count": result["job_count"],
        "enqueued": result.get("enqueued", 0),
        "skipped_existing": result.get("skipped_existing", 0),
        "out": args.out,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
