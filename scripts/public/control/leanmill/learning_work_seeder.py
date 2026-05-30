#!/usr/bin/env python3
"""Seed concrete LeanMill learning-unit WorkItems from current station artifacts.

The station contract says what kind of work should happen next. This bridge
turns that into bounded queue work with artifact paths, budgets, and explicit
credit boundaries. It does not award proof value; closure/gap/falsifier credit
still requires Governance Gate receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leanmill_family_specs as family_specs  # noqa: E402
import leanmill_family_spec_probe_signature as probe_signatures  # noqa: E402
from leanmill_factory_config import apply_profile_section, priority_value  # noqa: E402
from leanmill_paths import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, REPAIR_FAMILY_REGISTRY  # noqa: E402
from leanmill_source_search_integrator import _row_records, _sha_file  # noqa: E402


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_PACKET = f"{DEFAULT_DATA_DIR}/residual_family_canary_packets.json"
DEFAULT_ALLOCATOR = f"{DEFAULT_DATA_DIR}/source_family_allocator.json"
DEFAULT_REGISTRY = REPAIR_FAMILY_REGISTRY
DEFAULT_CONTRACT = f"{DEFAULT_DATA_DIR}/station_action_contract.json"
DEFAULT_SOURCE_PLAN = f"{DEFAULT_DATA_DIR}/residual_family_source_plan.json"
DEFAULT_ROW_CONTEXT = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json"
DEFAULT_STATIC_FILTER = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_STATIC_FILTER.json"
DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_EXPAND100_CORPUS = f"{DEFAULT_DATA_DIR}/mcb_expand100_active_corpus.json"
DEFAULT_EVALUATION_HARNESS_SOURCE_DIR = f"{DEFAULT_DATA_DIR}/evaluation_harness_sources"
DEFAULT_EXTRA_CORPORA = [
    "/tmp/rung1/mcb_refill_dedup_after_expand100/mcb_corpus.json",
    DEFAULT_EXPAND100_CORPUS,
    "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_QUEUE.json",
]
DEFAULT_OUT_DIR = f"{DEFAULT_DATA_DIR}/queued_learning_work"
DEFAULT_ROOT_BASE = "/tmp/rung1/leanmill_24x7_learning"
QUARANTINE_REPAIR_FAILURES = {
    "template_contains_placeholder_hole",
    "duplicate_negative_control_body",
    "negative_control_duplicates_positive",
}




THEOREM_NAME_RE = re.compile(r"(?:^|\n)\s*(?:@[^\n]*\n\s*)*(?:public\s+|private\s+|protected\s+|noncomputable\s+|unsafe\s+)*\s*(?:theorem|lemma)\s+([^\s:]+)")
GENERATED_DECL_ROW_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*_\d+_([A-Za-z_][A-Za-z0-9_'.]*)$")

def _read(path: str) -> dict[str, Any]:
    p = Path(path)
    if not path or not p.exists() or not p.is_file():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _priority_base(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY),
        namespace="formula_bases",
        key=key,
        fallback=fallback,
    )


def _family_spec_selection_pairs(path: str) -> set[tuple[str, str]]:
    obj = _read(path) if path else {}
    pairs: set[tuple[str, str]] = set()
    rows = obj.get("selected_rows") or obj.get("rows") or []
    if not isinstance(rows, list):
        return pairs
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("row_id") or row.get("id") or row.get("target_id") or "")
        if not row_id:
            continue
        families = row.get("matched_families") or row.get("families") or []
        if isinstance(families, str):
            families = [families]
        for family in families:
            family_s = str(family or "")
            if family_s:
                pairs.add((family_s, row_id))
    return pairs


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _bounded_slug(value: str, *, max_len: int = 96) -> str:
    slug = _slug(value)
    if len(slug) <= max_len:
        return slug
    digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:12]
    head_len = max(8, max_len - len(digest) - 1)
    return f"{slug[:head_len]}_{digest}"


def _open_or_terminal_exists(cx: Any, work_id: str, *, include_terminal: bool) -> bool:
    statuses = "('queued','claimed','running','done','failed','retired','dead_letter')" if include_terminal else "('queued','claimed','running')"
    row = cx.execute(
        f"SELECT 1 FROM work_items WHERE work_id=? AND status IN {statuses} LIMIT 1",
        (work_id,),
    ).fetchone()
    return row is not None


def _terminal_status_for_work_id(cx: Any, work_id: str) -> str:
    row = cx.execute(
        """
        SELECT status
        FROM work_items
        WHERE work_id=? AND status IN ('done','failed','retired','dead_letter')
        LIMIT 1
        """,
        (work_id,),
    ).fetchone()
    return str(row["status"] or "") if row else ""


def _open_same_family_work_exists(cx: Any, *, kind: str, family: str) -> bool:
    if not family:
        return False
    row = cx.execute(
        """
        SELECT 1
        FROM work_items
        WHERE kind=? AND family=? AND status IN ('queued','claimed','running')
        LIMIT 1
        """,
        (kind, family),
    ).fetchone()
    if row is not None:
        return True
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE kind=? AND status IN ('queued','claimed','running')
        """,
        (kind,),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("family") or "") == family:
            return True
    return False


def _open_same_replenish_group_exists(cx: Any, *, kind: str, replenish_group: str) -> bool:
    if not replenish_group:
        return False
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE kind=? AND status IN ('queued','claimed','running')
        """,
        (kind,),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("replenish_group") or "") == replenish_group:
            return True
    return False


def _recent_terminal_same_family_work_exists(cx: Any, *, kind: str, family: str, cooldown_s: int) -> bool:
    if not family or cooldown_s <= 0:
        return False
    threshold = int(time.time()) - int(cooldown_s)
    row = cx.execute(
        """
        SELECT 1
        FROM work_items
        WHERE kind=? AND family=? AND status IN ('done','failed','retired','dead_letter') AND updated_at >= ?
        LIMIT 1
        """,
        (kind, family, threshold),
    ).fetchone()
    if row is not None:
        return True
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE kind=? AND status IN ('done','failed','retired','dead_letter') AND updated_at >= ?
        """,
        (kind, threshold),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("family") or "") == family:
            return True
    return False


def _recent_terminal_same_replenish_group_exists(cx: Any, *, kind: str, replenish_group: str, cooldown_s: int) -> bool:
    if not replenish_group or cooldown_s <= 0:
        return False
    threshold = int(time.time()) - int(cooldown_s)
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE kind=? AND status IN ('done','failed','retired','dead_letter') AND updated_at >= ?
        """,
        (kind, threshold),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("replenish_group") or "") == replenish_group:
            return True
    return False


def _probe_signature_from_payload(payload: dict[str, Any]) -> str:
    signature = str(payload.get("probe_signature") or "")
    if signature:
        return signature
    packet_path = str(payload.get("packet") or "")
    if not packet_path or not Path(packet_path).exists():
        return ""
    try:
        packet = json.loads(Path(packet_path).read_text(errors="ignore"))
    except json.JSONDecodeError:
        return ""
    tests: list[dict[str, Any]] = []
    for pack in packet.get("packets") or []:
        if isinstance(pack, dict):
            tests.extend([t for t in (pack.get("tests") or []) if isinstance(t, dict)])
    return _probe_signature(str(payload.get("family") or ""), str(payload.get("probe_lane") or ""), tests)


def _recent_terminal_same_probe_signature_exists(cx: Any, *, signature: str, cooldown_s: int) -> bool:
    if not signature or cooldown_s <= 0:
        return False
    threshold = int(time.time()) - int(cooldown_s)
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE kind='repair_canary_probe' AND status IN ('done','failed','retired','dead_letter') AND updated_at >= ?
        """,
        (threshold,),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if _probe_signature_from_payload(payload) == signature:
            return True
    return False


def _open_same_probe_signature_exists(cx: Any, *, signature: str) -> bool:
    if not signature:
        return False
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE kind='repair_canary_probe' AND status IN ('queued','claimed','running')
        """
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if _probe_signature_from_payload(payload) == signature:
            return True
    return False


def _terminal_family_cooldown_for_job(args: argparse.Namespace, job: dict[str, Any]) -> int:
    kind = str(job.get("kind") or "")
    if kind == "repair_canary_probe":
        return 0
    if kind in {"source_request_propose", "decomposition_propose", "canary_propose", "llm_proposal_validate"}:
        return int(args.terminal_proposal_family_cooldown_s)
    if kind in {"agent_repair_task", "source_scout_task"}:
        return int(args.terminal_agent_family_cooldown_s)
    return int(args.terminal_family_cooldown_s)


def _configured_nodes(args: argparse.Namespace) -> list[str]:
    raw = str(args.routing_nodes or "").strip()
    if not raw:
        return []
    nodes: list[str] = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if ":" in token:
            node, weight_raw = token.rsplit(":", 1)
            node = node.strip()
            try:
                weight = max(1, int(weight_raw.strip()))
            except ValueError:
                raise SystemExit(f"invalid routing node weight in {token!r}; use node or node:int")
        else:
            node, weight = token, 1
        if not node:
            continue
        nodes.extend([node] * weight)
    return nodes


def _unique_nodes(nodes: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for node in nodes:
        if node in seen:
            continue
        seen.add(node)
        out.append(node)
    return out


def _current_node_id(args: argparse.Namespace) -> str:
    return str(args.node_id or os.environ.get("LEANMILL_NODE_ID") or "").strip()


def _job_route_key(job: dict[str, Any]) -> str:
    payload = dict(job.get("payload") or {})
    for key in ("probe_signature", "replenish_group", "family"):
        value = str(payload.get(key) or "")
        if value:
            return value
    return str(job.get("work_id") or "")


def _assigned_node(job: dict[str, Any], nodes: list[str]) -> str:
    if not nodes:
        return ""
    key = _job_route_key(job)
    digest = hashlib.sha256(key.encode()).hexdigest()
    return nodes[int(digest[:12], 16) % len(nodes)]


def _route_jobs_for_node(jobs: list[dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    nodes = _configured_nodes(args)
    node_id = _current_node_id(args)
    if not nodes:
        for job in jobs:
            payload = dict(job.get("payload") or {})
            payload.setdefault("node_id", node_id)
            payload.setdefault("routing", {"mode": "unsharded", "node_id": node_id})
            job["payload"] = payload
        return jobs, {"mode": "unsharded", "node_id": node_id, "routing_nodes": [], "kept": len(jobs), "filtered": 0}
    if not node_id:
        raise SystemExit("--routing-nodes requires --node-id or LEANMILL_NODE_ID")
    if node_id not in set(nodes):
        raise SystemExit(f"node_id {node_id!r} is not present in --routing-nodes")
    kept: list[dict[str, Any]] = []
    filtered = 0
    unique_nodes = _unique_nodes(nodes)
    route_counts = {node: 0 for node in unique_nodes}
    for job in jobs:
        assigned = _assigned_node(job, nodes)
        route_counts[assigned] = route_counts.get(assigned, 0) + 1
        payload = dict(job.get("payload") or {})
        payload["node_id"] = node_id
        payload["routing"] = {
            "mode": "deterministic_hash",
            "node_id": node_id,
            "assigned_node_id": assigned,
            "routing_nodes": unique_nodes,
            "weighted_routing_nodes": nodes,
            "route_key_sha256": hashlib.sha256(_job_route_key(job).encode()).hexdigest(),
        }
        job["payload"] = payload
        if assigned == node_id:
            kept.append(job)
        else:
            filtered += 1
    return kept, {
        "mode": "deterministic_hash",
        "node_id": node_id,
        "routing_nodes": unique_nodes,
        "weighted_routing_nodes": nodes,
        "route_counts": route_counts,
        "kept": len(kept),
        "filtered": filtered,
    }


def _learning_work_skip_reason(cx: Any, args: argparse.Namespace, job: dict[str, Any]) -> tuple[str, str] | None:
    """Return (bucket, reason) if an enqueue candidate is duplicate/spend-held.

    Proof probes are learning-unit scoped by their canonical probe signature.
    Proposal/agent/source generation is spend scoped by family or replenish
    group. Keeping the two identities separate prevents both fake replay
    throughput and broad family cooldowns that starve distinct proof checks.
    """
    kind = str(job["kind"])
    payload = dict(job.get("payload") or {})
    work_id = str(job["work_id"])
    family = str(payload.get("family") or "")
    replenish_group = str(payload.get("replenish_group") or "")
    if _open_or_terminal_exists(cx, work_id, include_terminal=False):
        return ("open", "open_exact_work_id")
    terminal_status = _terminal_status_for_work_id(cx, work_id)
    if terminal_status and (terminal_status != "failed" or not args.retry_existing):
        return ("existing", f"terminal_exact_work_id_{terminal_status}")
    if kind == "repair_canary_probe":
        signature = str(payload.get("probe_signature") or "")
        if _open_same_probe_signature_exists(cx, signature=signature):
            return ("open", "open_same_probe_signature")
        if (
            not args.retry_existing
            and _recent_terminal_same_probe_signature_exists(
                cx,
                signature=signature,
                cooldown_s=args.terminal_probe_signature_cooldown_s,
            )
        ):
            return ("existing", "recent_terminal_same_probe_signature")
        if not args.retry_existing and _open_or_terminal_exists(cx, work_id, include_terminal=True):
            return ("existing", "terminal_exact_work_id")
        return None
    if replenish_group and _open_same_replenish_group_exists(cx, kind=kind, replenish_group=replenish_group):
        return ("open", "open_same_replenish_group")
    if not replenish_group and _open_same_family_work_exists(cx, kind=kind, family=family):
        return ("open", "open_same_family_kind")
    terminal_family_cooldown_s = _terminal_family_cooldown_for_job(args, job)
    if (
        not args.retry_existing
        and replenish_group
        and _recent_terminal_same_replenish_group_exists(
            cx,
            kind=kind,
            replenish_group=replenish_group,
            cooldown_s=terminal_family_cooldown_s,
        )
    ):
        return ("existing", "recent_terminal_same_replenish_group")
    if (
        not args.retry_existing
        and not replenish_group
        and _recent_terminal_same_family_work_exists(
            cx,
            kind=kind,
            family=family,
            cooldown_s=terminal_family_cooldown_s,
        )
    ):
        return ("existing", "recent_terminal_same_family_kind")
    if not args.retry_existing and _open_or_terminal_exists(cx, work_id, include_terminal=True):
        return ("existing", "terminal_exact_work_id")
    return None


def _probe_command_timeout_s(args: argparse.Namespace, test_count: int) -> int:
    """Outer command cap for a packet, sized from the per-test wall cap."""
    count = max(1, int(test_count or 1))
    per_test = max(1, int(args.probe_wall_timeout_s))
    return max(int(args.probe_command_timeout_s), count * per_test + int(args.probe_command_timeout_overhead_s))


def _skip(skip_counts: dict[str, int], reason: str) -> None:
    skip_counts[reason] = int(skip_counts.get(reason) or 0) + 1


def _allocator_scores(path: str) -> dict[str, float]:
    obj = _read(path)
    scores: dict[str, float] = {}
    for rec in obj.get("allocations") or []:
        fam = str(rec.get("family") or "")
        if fam:
            scores[fam] = float(rec.get("yield_score") or 0.0)
    return scores


def _registry_probe_scores(path: str) -> dict[str, float]:
    obj = _read(path)
    status_weight = {
        "validated_family": 1000.0,
        "validated_family_requires_true_holdout_check": 850.0,
        "candidate_family": 650.0,
        "seed_only": 250.0,
        "seed_hold": 40.0,
        "inventory_only": -100.0,
        "superseded_family": -500.0,
    }
    scores: dict[str, float] = {}
    for rec in obj.get("families") or []:
        if not isinstance(rec, dict):
            continue
        family = str(rec.get("family") or "")
        if not family:
            continue
        status = str(rec.get("status") or "")
        useful = float(rec.get("useful_outcomes") or 0.0)
        closures = float(rec.get("ratified_proof_closure") or 0.0)
        exact_gaps = float(rec.get("exact_gap") or 0.0)
        falsifiers = float(rec.get("valid_falsifier") or 0.0)
        expected_neg = float(rec.get("negative_controls_expected_fail") or 0.0)
        unexpected_neg = float(rec.get("negative_controls_unexpected_pass") or 0.0)
        heldout_success = float(rec.get("heldout_successes") or 0.0)
        scores[family] = (
            status_weight.get(status, 0.0)
            + 12.0 * useful
            + 6.0 * closures
            + 8.0 * exact_gaps
            + 8.0 * falsifiers
            + min(expected_neg, 20.0)
            + 25.0 * heldout_success
            - 1000.0 * unexpected_neg
        )
    return scores


def _allocator_actions(path: str) -> dict[str, str]:
    obj = _read(path)
    actions: dict[str, str] = {}
    for rec in obj.get("allocations") or []:
        fam = str(rec.get("family") or "")
        if fam:
            actions[fam] = str(rec.get("recommended_action") or "")
    return actions


def _no_spend_families(path: str) -> set[str]:
    return {
        family
        for family, action in _allocator_actions(path).items()
        if action == "do_not_spend_until_new_evidence"
    }


def _source_strategy_repair_families(path: str) -> set[str]:
    return {
        family
        for family, action in _allocator_actions(path).items()
        if action == "repair_source_strategy_before_more_binding"
    }


def _source_binding_hold_families(path: str) -> set[str]:
    return {
        family
        for family, action in _allocator_actions(path).items()
        if action == "hold_source_binding_until_new_target_evidence"
    }


def _retire_no_spend_open_work(cx: Any, *, allocator_path: str, events: str) -> int:
    no_spend = _no_spend_families(allocator_path)
    if not no_spend:
        return 0
    kinds = {
        "agent_repair_task",
        "source_scout_task",
        "llm_proposal_validate",
        "source_request_propose",
        "decomposition_propose",
        "source_search_task",
    }
    rows = cx.execute(
        """
        SELECT work_id, kind, family, payload_json
        FROM work_items
        WHERE status IN ('queued','claimed','running')
        """
    ).fetchall()
    retired = 0
    for row in rows:
        kind = str(row["kind"] or "")
        if kind not in kinds:
            continue
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        family = str(row["family"] or payload.get("family") or "")
        if family not in no_spend:
            continue
        work_queue.update_status(cx, work_id=str(row["work_id"]), status="retired", payload_update={
            "exit_kind": "retired_no_spend_until_new_evidence",
            "retired_by": "leanmill_learning_work_seeder",
            "retire_reason": "source_family_allocator_recommended_do_not_spend_until_new_evidence",
        })
        work_queue.append_event(events, {
            "event_type": "no_spend_open_work_retired",
            "work_id": row["work_id"],
            "payload": {"kind": kind, "family": family},
        })
        retired += 1
    return retired


def _retire_throttled_source_work(cx: Any, *, allocator_path: str, events: str) -> int:
    throttled = _source_strategy_repair_families(allocator_path) | _source_binding_hold_families(allocator_path)
    if not throttled:
        return 0
    rows = cx.execute(
        """
        SELECT work_id, kind, family, payload_json
        FROM work_items
        WHERE status IN ('queued','claimed','running')
        """
    ).fetchall()
    retired = 0
    for row in rows:
        kind = str(row["kind"] or "")
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        family = str(row["family"] or payload.get("family") or "")
        if family not in throttled:
            continue
        hold = family in _source_binding_hold_families(allocator_path)
        expected_exit = str(payload.get("expected_exit") or "")
        proposal_type = str(payload.get("proposal_type") or "")
        retire = False
        if kind in {"source_search_task", "source_request_propose"}:
            retire = hold or proposal_type != "decomposition"
        elif kind == "source_scout_task":
            retire = expected_exit in {"source_request", ""}
        elif kind == "agent_repair_task":
            retire = expected_exit in {"source_request", "source_bound_probe"}
        elif kind == "repair_canary_probe" and hold:
            retire = str(payload.get("probe_lane") or "") == "source_binding"
        elif kind == "llm_proposal_validate" and hold:
            retire = str(payload.get("expected_outcome") or "") in {"source_request", "source_bound_probe", ""}
        if not retire:
            continue
        work_queue.update_status(cx, work_id=str(row["work_id"]), status="retired", payload_update={
            "exit_kind": "retired_source_strategy_repair_required",
            "retired_by": "leanmill_learning_work_seeder",
            "retire_reason": (
                "source_quality_feedback_held_source_binding_until_new_target_evidence"
                if hold else "source_quality_feedback_throttled_source_binding_until_strategy_repair"
            ),
        })
        work_queue.append_event(events, {
            "event_type": "throttled_source_work_retired",
            "work_id": row["work_id"],
            "payload": {"kind": kind, "family": family, "expected_exit": expected_exit},
        })
        retired += 1
    return retired



def _chunks(values: list[str], size: int) -> list[list[str]]:
    n = max(1, int(size or 1))
    return [values[i:i + n] for i in range(0, len(values), n)]

def _source_context(path: str) -> dict[str, Any]:
    obj = _read(path)
    return {
        "corpus": str(obj.get("corpus") or DEFAULT_CORPUS),
        "static_filter": str(obj.get("static_filter") or DEFAULT_STATIC_FILTER),
        "row_context_ready_total": int(obj.get("row_context_ready_total") or 0),
        "candidate_count": int(obj.get("candidate_count") or 0),
    }


def _probe_signature(family: str, lane: str, tests: list[dict[str, Any]]) -> str:
    return probe_signatures.probe_signature(family, lane, tests)


def _family_spec_template_fingerprints(family: str, tests_by_row: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    return {row_id: _probe_signature(family, "family_spec", row_tests) for row_id, row_tests in tests_by_row.items() if row_id}


def _corpus_paths(args: argparse.Namespace) -> list[str]:
    paths: list[str] = []
    for path in [
        str(getattr(args, "family_spec_selection", "") or ""),
        str(getattr(args, "corpus", "") or ""),
        str(getattr(args, "row_context", "") or ""),
        str(_read(getattr(args, "row_context", "")).get("corpus") or ""),
        *DEFAULT_EXTRA_CORPORA,
    ]:
        if path and path not in paths:
            paths.append(path)
    return paths


def _row_records_from_path(path: str) -> list[dict[str, Any]]:
    obj = _read(path)
    rows = _row_records(obj)
    if not rows and isinstance(obj, dict):
        for key in ("selected_rows", "candidate_rows"):
            vals = obj.get(key)
            if isinstance(vals, list):
                rows = vals
                break
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _rows_by_id(paths: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in paths:
        for row in _row_records_from_path(path):
            row_id = str(row.get("row_id") or row.get("id") or "")
            if not row_id:
                continue
            existing = out.get(row_id)
            if existing is None or _row_resolution_quality(row) > _row_resolution_quality(existing):
                out[row_id] = row
    return out


def _row_has_readable_target_file(row: dict[str, Any]) -> bool:
    path = str(row.get("sorried_file") or row.get("source_file") or row.get("file") or "")
    return bool(path) and Path(path).exists() and Path(path).is_file()


def _row_has_mathlib_source_metadata(row: dict[str, Any]) -> bool:
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    return bool(source.get("file")) and bool(
        source.get("mathlib_name")
        or source.get("target_theorem_name")
        or row.get("target_theorem_name")
        or row.get("theorem_name")
    )


def _row_resolution_quality(row: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        1 if _row_has_readable_target_file(row) else 0,
        1 if _row_has_mathlib_source_metadata(row) else 0,
        1 if str(row.get("target_theorem_name") or row.get("theorem_name") or "") else 0,
        1 if str(row.get("goal") or row.get("source_hinge") or "") else 0,
    )


def _mcb_row_suffix(row_id: str) -> str:
    m = re.match(r"^MCB_\d+_(.+)$", row_id)
    return m.group(1) if m else ""


def _executable_rows_by_mcb_suffix(paths: list[str]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, list[dict[str, Any]]] = {}
    for path in paths:
        for row in _row_records_from_path(path):
            if not _row_has_readable_target_file(row):
                continue
            suffix = _mcb_row_suffix(str(row.get("row_id") or row.get("id") or ""))
            if suffix:
                candidates.setdefault(suffix, []).append(row)
    out: dict[str, dict[str, Any]] = {}
    for suffix, rows in candidates.items():
        unique = {str(row.get("row_id") or row.get("id") or ""): row for row in rows}
        unique.pop("", None)
        if len(unique) == 1:
            out[suffix] = next(iter(unique.values()))
    return out


def _append_unique(values: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in values:
        values.append(text)


def _generated_decl_row_suffixes(row: dict[str, Any], requested_row_id: str = "") -> list[str]:
    suffixes: list[str] = []
    for rid in (requested_row_id, str(row.get("row_id") or row.get("id") or "")):
        match = GENERATED_DECL_ROW_ID_RE.match(str(rid or ""))
        if match:
            _append_unique(suffixes, match.group(1))
    return suffixes


def _row_theorem_name_candidates(row: dict[str, Any], requested_row_id: str = "") -> list[str]:
    candidates: list[str] = []
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    # Some corpora mint row ids as PREFIX_ordinal_declarationName, e.g. MCB_008_mellin_comp_rpow.
    # Treat that as a typed naming contract, not as generic underscore parsing.
    # Non-generated ids fall through to explicit metadata, goal parsing, or single-theorem fallback.
    for suffix in _generated_decl_row_suffixes(row, requested_row_id):
        _append_unique(candidates, suffix)
    for key in ("target_theorem_name", "theorem_name", "decl_name", "declaration_name", "target_name", "source_declaration", "mathlib_name"):
        _append_unique(candidates, row.get(key))
        _append_unique(candidates, source.get(key))
    goal = str(row.get("goal") or row.get("source_hinge") or "")
    m = THEOREM_NAME_RE.search(goal)
    if m:
        _append_unique(candidates, m.group(1))
    for rid in (requested_row_id, str(row.get("row_id") or row.get("id") or "")):
        if GENERATED_DECL_ROW_ID_RE.match(str(rid or "")):
            continue
        _append_unique(candidates, rid)
    return candidates


def _find_target_start(text: str, theorem_name: str) -> int:
    if not theorem_name:
        return -1
    pattern = re.compile(
        rf"(^|\n)\s*(?:@[^\n]*\n\s*)*"
        rf"(?:public\s+|private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
        rf"(?:theorem|lemma)\s+{re.escape(theorem_name)}(?=\s|:)"
    )
    match = pattern.search(text)
    if not match:
        return -1
    return match.start(0) + (1 if match.group(1) else 0)


def _line_number_at(text: str, offset: int) -> int:
    if offset < 0:
        return 0
    return text.count("\n", 0, min(offset, len(text))) + 1


def _explicit_target_line(row: dict[str, Any]) -> int:
    for key in ("target_line", "line", "start_line"):
        try:
            value = int(row.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    try:
        return int(source.get("target_line") or source.get("line") or 0)
    except (TypeError, ValueError):
        return 0


def _resolve_probe_target(row: dict[str, Any], requested_row_id: str) -> dict[str, Any]:
    source_file = str(row.get("sorried_file") or row.get("source_file") or row.get("file") or "")
    path = Path(source_file)
    if (not source_file or not path.exists() or not path.is_file()) and requested_row_id:
        source_dir = Path(os.environ.get("LEANMILL_EVALUATION_HARNESS_SOURCE_DIR") or DEFAULT_EVALUATION_HARNESS_SOURCE_DIR)
        fallback = source_dir / f"{requested_row_id}.lean"
        if fallback.exists() and fallback.is_file():
            source_file = str(fallback)
            path = fallback
    if not source_file or not path.exists() or not path.is_file():
        return {"status": "fail", "reason": "missing_source_file", "source_file": source_file}
    try:
        text = path.read_text(errors="ignore")
    except OSError as exc:
        return {"status": "fail", "reason": "source_file_read_failed", "source_file": source_file, "error": str(exc)}
    names = [m.group(1) for m in THEOREM_NAME_RE.finditer(text)]
    explicit_line = _explicit_target_line(row)
    for candidate in _row_theorem_name_candidates(row, requested_row_id):
        start = _find_target_start(text, candidate)
        if start >= 0:
            return {
                "status": "pass",
                "reason": "candidate_name_exact",
                "theorem_name": candidate,
                "target_line": _line_number_at(text, start),
                "source_file": source_file,
                "explicit_target_line": explicit_line or None,
            }
    if explicit_line > 0 and names:
        located = []
        for name in names:
            start = _find_target_start(text, name)
            if start >= 0:
                line = _line_number_at(text, start)
                located.append((abs(line - explicit_line), line > explicit_line, line, name))
        if located:
            located.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
            distance, _after, line, name = located[0]
            if distance <= 3:
                return {
                    "status": "pass",
                    "reason": "explicit_line_nearest",
                    "theorem_name": name,
                    "target_line": line,
                    "source_file": source_file,
                    "explicit_target_line": explicit_line,
                    "line_distance": distance,
                }
    if len(names) == 1:
        start = _find_target_start(text, names[0])
        return {
            "status": "pass",
            "reason": "single_theorem_in_source",
            "theorem_name": names[0],
            "target_line": _line_number_at(text, start),
            "source_file": source_file,
            "explicit_target_line": explicit_line or None,
        }
    return {
        "status": "fail",
        "reason": "target_theorem_not_resolved",
        "source_file": source_file,
        "requested_row_id": requested_row_id,
        "candidate_names": _row_theorem_name_candidates(row, requested_row_id),
        "explicit_target_line": explicit_line or None,
        "source_decl_count": len(names),
        "source_decls": names[:12],
    }


def _normalize_probe_row(row: dict[str, Any], requested_row_id: str = "") -> tuple[dict[str, Any] | None, str, dict[str, Any]]:
    resolution = _resolve_probe_target(row, requested_row_id or str(row.get("row_id") or row.get("id") or ""))
    if resolution.get("status") != "pass":
        return None, str(resolution.get("reason") or "target_resolution_failed"), resolution
    out = dict(row)
    row_id = str(requested_row_id or out.get("row_id") or out.get("id") or "")
    if row_id:
        out["id"] = row_id
        out["row_id"] = row_id
    source_file = str(resolution.get("source_file") or out.get("sorried_file") or out.get("source_file") or out.get("file") or "")
    if source_file:
        out["sorried_file"] = source_file
        out["source_file"] = source_file
    source = out.get("source") if isinstance(out.get("source"), dict) else None
    if source is None:
        source = {"mathlib_name": str(out.get("source_hinge") or resolution.get("theorem_name") or row_id)}
    elif isinstance(out.get("source"), str):
        source = {"mathlib_name": str(out.get("source_hinge") or resolution.get("theorem_name") or row_id), "raw": out.get("source")}
    source.setdefault("target_theorem_name", resolution.get("theorem_name"))
    source.setdefault("target_line", resolution.get("target_line"))
    out["source"] = source
    out["target_line"] = int(resolution.get("target_line") or 0)
    out["target_theorem_name"] = str(resolution.get("theorem_name") or "")
    out["target_resolution_status"] = "pass"
    out["target_resolution"] = resolution
    return out, "", resolution

def _resolve_probe_row(
    requested_row_id: str,
    rows_by_id: dict[str, dict[str, Any]],
    executable_by_suffix: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, str]:
    exact = rows_by_id.get(requested_row_id)
    exact_reason = ""
    if exact is not None:
        resolved, reason, _resolution = _normalize_probe_row(exact, requested_row_id)
        if resolved is not None:
            return resolved, ""
        exact_reason = reason
    suffix = _mcb_row_suffix(requested_row_id)
    alias = executable_by_suffix.get(suffix) if suffix else None
    if alias is not None:
        resolved, reason, resolution = _normalize_probe_row(alias, requested_row_id)
        if resolved is None:
            return None, f"suffix_alias_{reason}"
        resolved["requested_row_id"] = requested_row_id
        resolved["hydrated_from_row_id"] = str(alias.get("row_id") or alias.get("id") or "")
        resolved["hydrated_reason"] = "unique_executable_mcb_suffix_alias"
        resolved["target_resolution"] = {**resolution, "hydrated_from_row_id": resolved["hydrated_from_row_id"]}
        return resolved, ""
    if exact is not None:
        return None, exact_reason or "target_row_has_no_readable_sorried_file"
    return None, "target_row_not_found"


def _probe_corpus_signature(*, family: str, label: str, row_ids: set[str], selected: list[dict[str, Any]], source_corpora: list[dict[str, Any]]) -> str:
    payload = {
        "family": family,
        "label": label,
        "target_row_ids": sorted(row_ids),
        "selected_rows": [
            {
                "row_id": str(row.get("row_id") or ""),
                "source_file": str(row.get("source_file") or row.get("sorried_file") or ""),
                "target_line": row.get("target_line"),
            }
            for row in sorted(selected, key=lambda r: str(r.get("row_id") or ""))
        ],
        "source_corpora": source_corpora,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _find_existing_probe_corpus(out_dir: Path, *, family: str, label: str, signature: str) -> str:
    if not signature:
        return ""
    pattern = f"probe_corpus_{_slug(label)}_{_slug(family)}_*.json"
    for path in sorted(out_dir.glob(pattern), key=lambda p: (-p.stat().st_mtime, str(p))):
        try:
            obj = json.loads(path.read_text(errors="ignore"))
        except json.JSONDecodeError:
            continue
        if str(obj.get("corpus_signature") or "") == signature:
            return str(path)
    return ""


def _write_probe_corpus(args: argparse.Namespace, *, family: str, row_ids: set[str], out_dir: Path, run_id: str, label: str) -> tuple[str, dict[str, Any]]:
    corpus_paths = _corpus_paths(args)
    rows_by_id = _rows_by_id(corpus_paths)
    executable_by_suffix = _executable_rows_by_mcb_suffix(corpus_paths)
    selected: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    for row_id in sorted(row_ids):
        resolved, reason = _resolve_probe_row(row_id, rows_by_id, executable_by_suffix)
        if resolved is None:
            unresolved.append({"row_id": row_id, "reason": reason})
            continue
        selected.append(resolved)
    source_corpora = [
        {"path": path, "sha256": _sha_file(path), "row_count": len(_row_records_from_path(path))}
        for path in corpus_paths
    ]
    signature = _probe_corpus_signature(family=family, label=label, row_ids=row_ids, selected=selected, source_corpora=source_corpora)
    missing_row_ids = [item["row_id"] for item in unresolved]
    existing_path = _find_existing_probe_corpus(out_dir, family=family, label=label, signature=signature)
    if existing_path:
        return existing_path, {
            "target_row_count": len(row_ids),
            "selected_row_count": len(selected),
            "selected_row_ids": [str(row.get("row_id") or "") for row in selected if str(row.get("row_id") or "")],
            "selected_row_targets": {str(row.get("row_id") or ""): {"target_theorem_name": row.get("target_theorem_name"), "target_line": row.get("target_line"), "source_file": row.get("source_file") or row.get("sorried_file")} for row in selected if str(row.get("row_id") or "")},
            "missing_row_ids": missing_row_ids,
            "unresolved_row_reasons": unresolved,
            "source_corpora": source_corpora,
            "corpus_signature": signature,
            "reused_existing_corpus": True,
            "reused_existing_corpus_path": existing_path,
        }
    corpus_path = out_dir / f"probe_corpus_{_bounded_slug(label, max_len=32)}_{_bounded_slug(family, max_len=80)}_{_bounded_slug(run_id, max_len=48)}.json"
    obj = {
        "schema": "leanmill-probe-corpus-v1",
        "created_at_epoch": int(time.time()),
        "family": family,
        "label": label,
        "target_row_ids": sorted(row_ids),
        "missing_row_ids": missing_row_ids,
        "unresolved_row_reasons": unresolved,
        "source_corpora": source_corpora,
        "corpus_signature": signature,
        "dedupe_policy": "content-addressed by family, label, target rows, resolved source files, and source corpus hashes",
        "rows": selected,
    }
    corpus_path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    return str(corpus_path), {
        "target_row_count": len(row_ids),
        "selected_row_count": len(selected),
        "selected_row_ids": [str(row.get("row_id") or "") for row in selected if str(row.get("row_id") or "")],
        "selected_row_targets": {str(row.get("row_id") or ""): {"target_theorem_name": row.get("target_theorem_name"), "target_line": row.get("target_line"), "source_file": row.get("source_file") or row.get("sorried_file")} for row in selected if str(row.get("row_id") or "")},
        "missing_row_ids": obj["missing_row_ids"],
        "unresolved_row_reasons": obj["unresolved_row_reasons"],
        "source_corpora": obj["source_corpora"],
        "corpus_signature": signature,
        "reused_existing_corpus": False,
    }


def _write_probe_static_filter(*, tests: list[dict[str, Any]], out_dir: Path, family: str, run_id: str, label: str) -> str:
    rows: dict[str, list[dict[str, Any]]] = {}
    for test in tests:
        row_id = str(test.get("row_id") or "")
        if not row_id:
            continue
        name = str(test.get("candidate_name") or "")
        if name:
            rows.setdefault(row_id, []).append({
                "name": name,
                "kind": "theorem",
                "name_resolves": True,
                "usable_for_canary_source": True,
                "source_safety_status": f"{label}_candidate",
                "source_order_status": "requires_governance",
            })
        else:
            rows.setdefault(row_id, [])
    obj = {
        "schema": "leanmill-generated-probe-static-filter-v1",
        "family": family,
        "label": label,
        "rows": [
            {
                "row_id": row_id,
                "canary_ready_count": len(candidates),
                "canary_ready_candidates": candidates,
                "row_context_ready_candidates": candidates,
                "target_context_ready_candidates": candidates,
            }
            for row_id, candidates in sorted(rows.items())
        ],
    }
    path = out_dir / f"probe_static_filter_{_bounded_slug(label, max_len=32)}_{_bounded_slug(family, max_len=80)}_{_bounded_slug(run_id, max_len=48)}.json"
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    return str(path)


def _active_corpus_rows(paths: list[str], wanted_rows: set[str], *, limit: int = 24) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    wanted = {str(r) for r in wanted_rows if str(r or "")}
    if not wanted:
        return []
    seen: set[str] = set()
    for path in paths:
        for row in _row_records_from_path(path):
            row_id = str(row.get("row_id") or row.get("id") or "")
            if not row_id or row_id in seen or row_id not in wanted:
                continue
            seen.add(row_id)
            out.append({
                "row_id": row_id,
                "goal": str(row.get("goal") or "")[:420],
                "source": str(row.get("source") or row.get("sorried_file") or "")[:220],
                "corpus": path,
            })
            if len(out) >= max(1, limit):
                return out
    return out


def _recent_family_rejections(queue_db: str, family: str, *, limit: int = 8) -> list[dict[str, Any]]:
    if not Path(queue_db).exists() or not family:
        return []
    cx = work_queue.connect(queue_db)
    rows = cx.execute(
        """
        SELECT kind, status, work_id, payload_json, updated_at
        FROM work_items
        WHERE family=? AND status IN ('failed','retired','dead_letter','done')
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (family, max(1, int(limit * 4))),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        reasons = []
        for key in (
            "exit_kind",
            "source_binding_ingest_status",
            "source_binding_failures",
            "source_search_integration_skipped_reason",
            "llm_proposal_status",
            "failure_class",
        ):
            value = payload.get(key)
            if value:
                reasons.append({key: value})
        quality_failures = []
        for q in payload.get("query_quality") or []:
            if isinstance(q, dict) and not bool(q.get("accepted", True)):
                quality_failures.append({"query": q.get("query"), "failures": q.get("failures")})
        if quality_failures:
            reasons.append({"query_quality_failures": quality_failures[:3]})
        if not reasons:
            continue
        out.append({
            "kind": row["kind"],
            "status": row["status"],
            "work_id": row["work_id"],
            "updated_at": row["updated_at"],
            "reasons": reasons[:5],
        })
        if len(out) >= max(1, limit):
            break
    return out


def _source_scout_context(args: argparse.Namespace, packet: dict[str, Any], family: str) -> dict[str, Any]:
    row_ids = {str(r) for r in (packet.get("rows") or packet.get("seed_rows") or []) if str(r or "")}
    for lead in packet.get("top_leads") or []:
        if isinstance(lead, dict) and str(lead.get("row_id") or ""):
            row_ids.add(str(lead.get("row_id")))
    active_rows = _active_corpus_rows(_corpus_paths(args), row_ids)
    return {
        "schema": "leanmill-source-scout-context-v1",
        "family": family,
        "active_target_rows": active_rows,
        "active_target_row_ids": [r["row_id"] for r in active_rows],
        "source_profile": packet,
        "recent_rejections": _recent_family_rejections(args.queue_db, family),
        "hard_rules": [
            "emit exactly one JSON object",
            "source_query entries must be theorem-shaped, not process/schema language",
            "target row IDs must come from active_target_row_ids or the scout must emit hold/retire",
            "source inventory has no proof credit",
            "matched negative-control ideas are required for candidate canary paths",
        ],
    }


def _packet_tests(packet: dict[str, Any], *, static_filter: str, max_rows: int, max_candidates_per_row: int) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    rows = list(packet.get("selected_rows") or [])[: max(1, max_rows)]
    family = str(packet.get("repair_family") or "")
    for row in rows:
        row_id = str(row.get("row_id") or "")
        names = [str(n) for n in (row.get("candidate_names") or []) if str(n or "")][: max(1, max_candidates_per_row)]
        for name in names:
            nonce = hashlib.sha256(f"{family}:{row_id}:{name}:{static_filter}".encode()).hexdigest()[:10]
            negative_name = f"LeanMill.NegativeControl.{_slug(family)}.{_slug(row_id)}.{nonce}"
            tests.append({
                "packet_id": f"{family}:{row_id}:{name}:positive_source_shape_probe",
                "repair_family": family,
                "row_id": row_id,
                "candidate_name": name,
                "action_family": "apply_easy",
                "test_kind": "positive",
                "expected_outcome": "closure_or_typed_residual",
                "source_credit_eligible": False,
                "clean_solver_credit_eligible": False,
                "credit_type": "repair_canary_probe",
                "static_filter": static_filter,
                "require_positive_source_action": False,
            })
            tests.append({
                "packet_id": f"{family}:{row_id}:{name}:negative_unresolved_sentinel",
                "repair_family": family,
                "row_id": row_id,
                "candidate_name": negative_name,
                "action_family": "apply_easy",
                "test_kind": "negative_control",
                "expected_outcome": "expected_failure",
                "source_credit_eligible": False,
                "clean_solver_credit_eligible": False,
                "credit_type": "negative_control",
                "static_filter": static_filter,
                "negative_control_reason": "unresolved sentinel must not close; any pass is a ratification blocker",
            })
    return tests


def _exit_contract(tests: list[dict[str, Any]]) -> dict[str, Any]:
    positives = {str(t.get("packet_id") or ""): t for t in tests if t.get("test_kind") == "positive"}
    negatives = {str(t.get("packet_id") or ""): t for t in tests if t.get("test_kind") == "negative_control"}
    negatives_by_row: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for nid, negative in negatives.items():
        negatives_by_row.setdefault(str(negative.get("row_id") or ""), []).append((nid, negative))
    pairs = []
    used_negatives: set[str] = set()
    for pid in sorted(positives):
        nid = pid.replace(":positive_source_shape_probe", ":negative_unresolved_sentinel")
        if nid in negatives:
            used_negatives.add(nid)
            pairs.append({
                "positive_packet_id": pid,
                "paired_negative_packet_id": nid,
                "closure_validity": "requires_matched_negative_control_expected_failure",
                "unexpected_negative_control_pass_blocks_credit": True,
            })
            continue
        row_id = str(positives[pid].get("row_id") or "")
        row_negatives = [
            candidate
            for candidate in negatives_by_row.get(row_id, [])
            if candidate[0] not in used_negatives
        ]
        if len(row_negatives) == 1:
            fallback_nid = row_negatives[0][0]
            used_negatives.add(fallback_nid)
            pairs.append({
                "positive_packet_id": pid,
                "paired_negative_packet_id": fallback_nid,
                "closure_validity": "requires_matched_negative_control_expected_failure",
                "unexpected_negative_control_pass_blocks_credit": True,
            })
    return {
        "schema": "leanmill-probe-exit-contract-v1",
        "pair_count": len(pairs),
        "pairs": pairs,
        "proof_credit_authority": "governance_gate",
    }


def _ready_probe_packets(args: argparse.Namespace) -> list[dict[str, Any]]:
    obj = _read(args.packet)
    source = _source_context(args.row_context)
    scores = _allocator_scores(args.allocator)
    packets = [
        p for p in (obj.get("packets") or [])
        if str(p.get("state") or "") == "ready_for_canary_build" and p.get("selected_rows")
    ]
    packets.sort(key=lambda p: (scores.get(str(p.get("repair_family") or ""), 0.0), int(p.get("lead_count") or 0)), reverse=True)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or str(int(time.time()))
    seeded: list[dict[str, Any]] = []
    for packet in packets[: max(0, args.max_probe_families)]:
        family = str(packet.get("repair_family") or "unknown_family")
        tests = _packet_tests(
            packet,
            static_filter=source["static_filter"],
            max_rows=args.max_rows_per_family,
            max_candidates_per_row=args.max_candidates_per_row,
        )
        if not tests:
            continue
        probe_signature = _probe_signature(family, "source_shape", tests)
        row_ids = {str(t.get("row_id") or "") for t in tests if str(t.get("row_id") or "")}
        probe_corpus, probe_corpus_meta = _write_probe_corpus(
            args,
            family=family,
            row_ids=row_ids,
            out_dir=out_dir,
            run_id=run_id,
            label="source_shape",
        )
        if probe_corpus_meta["missing_row_ids"]:
            continue
        static_filter = _write_probe_static_filter(
            tests=tests,
            out_dir=out_dir,
            family=family,
            run_id=run_id,
            label="source_shape",
        )
        for test in tests:
            test["static_filter"] = static_filter
        packet_path = out_dir / f"probe_packet_{_bounded_slug(family, max_len=80)}_{_bounded_slug(run_id, max_len=48)}.json"
        packet_obj = {
            "schema": "leanmill-concrete-learning-probe-packet-v1",
            "parent_packet": args.packet,
            "repair_family": family,
            "science_rule": "Generated WorkItems are probes only; value credit requires independent Governance Gate receipts.",
            "credit_boundary": {
                "source_credit_eligible": False,
                "clean_solver_credit_eligible": False,
                "proof_credit_authority": "governance_gate",
                "worker_can_self_ratify": False,
            },
            "exit_contract": _exit_contract(tests),
            "packets": [{**packet, "tests": tests}],
        }
        packet_path.write_text(json.dumps(packet_obj, indent=2, sort_keys=True) + "\n")
        root = Path(args.root_base) / f"probe_{_bounded_slug(family, max_len=80)}_{_bounded_slug(run_id, max_len=48)}"
        seeded.append({
            "kind": "repair_canary_probe",
            "priority": int(_priority_base(args, "family_spec_probe", 140) + scores.get(family, 0.0)),
            "work_id": f"probe:{family}:{run_id}",
            "payload": {
                "work_id": f"probe:{family}:{run_id}",
                "family": family,
                "probe_lane": "source_shape",
                "replenish_group": f"{family}:source_shape",
                "probe_signature": probe_signature,
                "packet": str(packet_path),
                "root": str(root),
                "corpus": probe_corpus,
                "probe_corpus_meta": probe_corpus_meta,
                "static_filter": static_filter,
                "scoreboard": str(root / "scoreboard.json"),
                "limit": min(args.max_tests_per_probe, len(tests)),
                "max_candidates": 1,
                "max_actions": 1,
                "timeout": args.probe_timeout_s,
                "test_wall_timeout": args.probe_wall_timeout_s,
                "command_timeout_s": _probe_command_timeout_s(args, min(args.max_tests_per_probe, len(tests))),
                "backend": args.backend,
                "warm_repl_inline": bool(args.warm_repl_inline),
                "govern_winners": bool(args.govern_winners),
                "credit_boundary": packet_obj["credit_boundary"],
                "exit_contract": packet_obj["exit_contract"],
                "expected_exit": "ratified_closure_or_typed_residual_or_expected_negative_control_failure",
            },
            "artifact_paths": [str(packet_path), probe_corpus, static_filter],
        })
    return seeded


def _family_spec_target_names_by_row(args: argparse.Namespace) -> dict[str, list[str]]:
    paths = [
        str(getattr(args, "row_context", "") or ""),
        str(getattr(args, "family_spec_selection", "") or ""),
    ]
    return family_specs.target_names_by_row_from_context_paths(paths)


def _family_spec_probe_jobs(args: argparse.Namespace) -> list[dict[str, Any]]:
    target_names_by_row = _family_spec_target_names_by_row(args)
    specs = family_specs.usable_specs(
        family_specs.load_specs(args.family_spec_dir),
        target_names_by_row=target_names_by_row,
    )
    selection_pairs = _family_spec_selection_pairs(getattr(args, "family_spec_selection", ""))
    allocator_scores = _allocator_scores(args.allocator)
    registry_scores = _registry_probe_scores(args.registry)
    by_family: list[tuple[float, str, dict[str, Any]]] = []
    selection_families = {family for family, _row_id in selection_pairs}
    for spec in specs:
        family = str(spec.get("family") or "")
        templates = [t for t in (spec.get("templates") or []) if isinstance(t, dict)]
        if not family or not templates:
            continue
        if selection_pairs and family not in selection_families:
            continue
        by_family.append((registry_scores.get(family, 0.0) + 0.05 * allocator_scores.get(family, 0.0), family, spec))
    by_family.sort(key=lambda item: (-item[0], item[1]))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or str(int(time.time()))
    jobs: list[dict[str, Any]] = []
    for family_score, family, spec in by_family[: max(0, args.max_family_spec_probe_families)]:
        tests: list[dict[str, Any]] = []
        for template in spec.get("templates") or []:
            if not isinstance(template, dict):
                continue
            row_id = str(template.get("row_id") or "")
            if not row_id:
                continue
            if selection_pairs and (family, row_id) not in selection_pairs:
                continue
            body_lines = family_specs._template_body(template)  # data-normalization helper; no proof credit.
            tests.append({
                "packet_id": f"{family}:{row_id}:{template.get('id') or 'family_spec_template'}",
                "repair_family": family,
                "row_id": row_id,
                "candidate_name": None,
                "action_family": "manual_extra",
                "test_kind": str(template.get("test_kind") or "positive"),
                "expected_outcome": str(template.get("expected_outcome") or ""),
                "backend": str(template.get("backend") or args.backend),
                "timeout": int(template.get("timeout") or args.probe_timeout_s),
                "max_candidates": 1,
                "max_actions": 1,
                "score_candidates": False,
                "require_positive_source_action": False,
                "source_credit_eligible": False,
                "clean_solver_credit_eligible": False,
                "credit_type": "repair_family_spec_probe",
                "static_filter": DEFAULT_STATIC_FILTER,
                "extra_body": body_lines,
                "family_spec_path": str(spec.get("_path") or ""),
            })
        if not tests:
            continue
        row_ids = {str(t.get("row_id") or "") for t in tests if str(t.get("row_id") or "")}
        probe_corpus, probe_corpus_meta = _write_probe_corpus(
            args,
            family=family,
            row_ids=row_ids,
            out_dir=out_dir,
            run_id=run_id,
            label="family_spec",
        )
        selected_row_ids = {str(row_id) for row_id in (probe_corpus_meta.get("selected_row_ids") or []) if str(row_id)}
        if not selected_row_ids:
            continue
        tests = [test for test in tests if str(test.get("row_id") or "") in selected_row_ids]
        if not tests:
            continue
        tests_by_row: dict[str, list[dict[str, Any]]] = {}
        for test in tests:
            tests_by_row.setdefault(str(test.get("row_id") or ""), []).append(test)
        ready_row_ids = [
            row_id for row_id, shard_tests in sorted(tests_by_row.items())
            if row_id and any(str(test.get("test_kind") or "") == "positive" for test in shard_tests)
        ]
        template_fingerprints = _family_spec_template_fingerprints(family, tests_by_row)
        for row_chunk in _chunks(ready_row_ids, getattr(args, "family_spec_probe_rows_per_work_item", 1)):
            shard_tests = [test for row_id in row_chunk for test in tests_by_row.get(row_id, [])]
            if not shard_tests:
                continue
            target_meta = probe_corpus_meta.get("selected_row_targets") if isinstance(probe_corpus_meta, dict) else {}
            if isinstance(target_meta, dict):
                for test in shard_tests:
                    meta = target_meta.get(str(test.get("row_id") or "")) or {}
                    if isinstance(meta, dict):
                        test["target_theorem_name"] = str(meta.get("target_theorem_name") or "")
                        test["target_line"] = int(meta.get("target_line") or 0)
            shard_id = _bounded_slug("__".join(row_chunk), max_len=64)
            probe_signature = _probe_signature(family, "family_spec", shard_tests)
            static_filter = _write_probe_static_filter(
                tests=shard_tests,
                out_dir=out_dir,
                family=f"{family}_{shard_id}",
                run_id=run_id,
                label="family_spec",
            )
            for test in shard_tests:
                test["static_filter"] = static_filter
            family_path_slug = _bounded_slug(family, max_len=64)
            packet_path = out_dir / f"family_spec_probe_packet_{family_path_slug}_{shard_id}_{_bounded_slug(run_id, max_len=48)}.json"
            root = Path(args.root_base) / f"family_spec_probe_{family_path_slug}_{shard_id}_{_bounded_slug(run_id, max_len=48)}"
            selected_rows = [{"row_id": row_id} for row_id in row_chunk]
            packet_obj = {
                "schema": "leanmill-concrete-learning-probe-packet-v1",
                "parent_spec": str(spec.get("_path") or ""),
                "repair_family": family,
                "family_spec_shard": {"mode": "rows", "row_ids": row_chunk},
                "science_rule": "Family-spec probes are executable canaries only; value credit requires Governance Gate receipts and matched controls.",
                "credit_boundary": {
                    "source_credit_eligible": False,
                    "clean_solver_credit_eligible": False,
                    "proof_credit_authority": "governance_gate",
                    "worker_can_self_ratify": False,
                },
                "exit_contract": _exit_contract(shard_tests),
                "packets": [{
                    "repair_family": family,
                    "state": "ready_for_drain",
                    "tests": shard_tests,
                    "selected_rows": selected_rows,
                }],
            }
            packet_path.write_text(json.dumps(packet_obj, indent=2, sort_keys=True) + "\n")
            signature_short = hashlib.sha256(probe_signature.encode()).hexdigest()[:16]
            work_id = f"probe:family_spec:{family}:{shard_id}:{signature_short}"
            priority = int(_priority_base(args, "family_spec_activation_probe", 220) + family_score)
            if str(run_id).startswith("family_birth_activation_"):
                priority = max(priority, int(getattr(args, "family_spec_activation_priority_floor", 0) or 0))
            jobs.append({
                "kind": "repair_canary_probe",
                "priority": priority,
                "work_id": work_id,
                "payload": {
                    "work_id": work_id,
                    "family": family,
                    "probe_lane": "family_spec",
                    "family_spec_shard": {"mode": "rows", "row_ids": row_chunk},
                    "family_spec_template_fingerprints": {row_id: template_fingerprints.get(row_id) for row_id in row_chunk if template_fingerprints.get(row_id)},
                    "replenish_group": f"{family}:family_spec:{hashlib.sha256('|'.join(row_chunk).encode()).hexdigest()[:16]}",
                    "probe_signature": probe_signature,
                    "packet": str(packet_path),
                    "root": str(root),
                    "corpus": probe_corpus,
                    "probe_corpus_meta": probe_corpus_meta,
                    "static_filter": static_filter,
                    "scoreboard": str(root / "scoreboard.json"),
                    "limit": min(args.max_tests_per_probe, len(shard_tests)),
                    "max_candidates": 1,
                    "max_actions": 1,
                    "timeout": args.probe_timeout_s,
                    "test_wall_timeout": args.probe_wall_timeout_s,
                    "command_timeout_s": _probe_command_timeout_s(args, min(args.max_tests_per_probe, len(shard_tests))),
                    "backend": args.backend,
                    "warm_repl_inline": bool(args.warm_repl_inline),
                    "govern_winners": True,
                    "governance_required": True,
                    "credit_boundary": packet_obj["credit_boundary"],
                    "exit_contract": packet_obj["exit_contract"],
                    "expected_exit": "ratified_closure_or_typed_residual_or_expected_negative_control_failure",
                },
                "artifact_paths": [str(packet_path), probe_corpus, static_filter],
            })
    return jobs



def _family_spec_quarantine_repair_jobs(args: argparse.Namespace) -> list[dict[str, Any]]:
    limit = max(0, int(getattr(args, "max_family_spec_repair_jobs", 0) or 0))
    if limit <= 0:
        return []
    specs = family_specs.load_specs(args.family_spec_dir)
    target_names_by_row = _family_spec_target_names_by_row(args)
    failures = [
        f for f in family_specs.validate_specs(specs, target_names_by_row=target_names_by_row)
        if str(f.get("failure") or "") in QUARANTINE_REPAIR_FAILURES
    ]
    by_family: dict[str, list[dict[str, Any]]] = {}
    for failure in failures:
        family = str(failure.get("family") or "")
        path = str(failure.get("path") or "")
        if not family or not path:
            continue
        by_family.setdefault(family, []).append(failure)
    if not by_family:
        return []
    registry_scores = _registry_probe_scores(args.registry)
    run_id = args.run_id or str(int(time.time()))
    jobs: list[dict[str, Any]] = []
    for family, family_failures in sorted(
        by_family.items(),
        key=lambda kv: (-len(kv[1]), -registry_scores.get(kv[0], 0.0), kv[0]),
    )[:limit]:
        target_path = str(family_failures[0].get("path") or "")
        clipped_failures = family_failures[: max(1, int(getattr(args, "family_spec_repair_failures_per_job", 8) or 8))]
        failure_summary = [
            {
                "failure": str(f.get("failure") or ""),
                "row_id": str(f.get("row_id") or ""),
                "template": str(f.get("template") or ""),
                **({"duplicate_of": str(f.get("duplicate_of") or "")} if f.get("duplicate_of") else {}),
            }
            for f in clipped_failures
        ]
        work_id = f"family_spec_patch:{family}:{run_id}"
        task = (
            "Repair LeanMill family-spec supply debt in the target YAML file only. "
            "The current proof-lane refill is duplicate-signature blocked because usable family-spec rows are exhausted. "
            "For each listed quarantined template, either replace the unsafe placeholder `?_` with a mechanically justified Lean body, "
            "make the matched negative control substantively different from the positive and sibling negatives, or remove the exact unsafe template from the YAML. "
            "Do not edit Python, scoreboards, registries, governance receipts, or research logs. Do not add proof credit. "
            "After editing, the target YAML must parse and the target family must have fewer family-spec gate failures than before. "
            "If you cannot safely repair or retire any listed template, do not edit the file; emit JSON with exit_kind operator_required or retired and a concrete reason. "
            f"Target YAML: {target_path}. Quarantined failures: {json.dumps(failure_summary, sort_keys=True)}"
        )
        jobs.append({
            "kind": "agent_repair_task",
            "priority": int(_priority_base(args, "family_quarantine_repair", 210) + min(len(family_failures), 80) + registry_scores.get(family, 0.0)),
            "work_id": work_id,
            "payload": {
                "work_id": work_id,
                "runtime": args.agent_runtime,
                "agent_id": f"leanmill_{args.agent_runtime}_family_spec_patch",
                "station": "repair_registry",
                "family": family,
                "task": task,
                "expected_exit": "family_spec_patch",
                "allowed_paths": [target_path, "/tmp/rung1"],
                "requires_negative_control": False,
                "proof_affecting": False,
                "max_iterations": args.agent_max_iterations,
                "max_wall_time_s": args.agent_max_wall_time_s,
                "family_spec_patch_target": target_path,
                "family_spec_patch_mode": "repair_quarantine",
                "family_spec_quarantine_failures": failure_summary,
                "replenish_group": f"family_spec_patch:{family}",
            },
            "artifact_paths": [target_path],
        })
    return jobs


def _family_spec_generality_jobs(args: argparse.Namespace) -> list[dict[str, Any]]:
    limit = max(0, int(getattr(args, "max_family_spec_generality_jobs", 0) or 0))
    if limit <= 0:
        return []
    specs = family_specs.load_specs(args.family_spec_dir)
    target_names_by_row = _family_spec_target_names_by_row(args)
    reports = family_specs.family_supply_quality(specs, target_names_by_row=target_names_by_row)
    spec_by_family = {str(spec.get("family") or ""): spec for spec in specs}
    registry_scores = _registry_probe_scores(args.registry)
    run_id = args.run_id or str(int(time.time()))
    candidates = [
        r for r in reports
        if int(r.get("blocking_failure_count") or 0) == 0
        and str(r.get("supply_class") or "") in {"probe_ready_with_debt", "not_probe_ready"}
        and ({"shallow_usable_supply", "weak_residual_match_surface", "no_usable_positive_negative_pair"} & set(r.get("gaps") or []))
    ]
    candidates.sort(key=lambda r: (
        int(r.get("usable_pair_rows") or 0),
        int(r.get("generality_score") or 0),
        -registry_scores.get(str(r.get("family") or ""), 0.0),
        str(r.get("family") or ""),
    ))
    jobs: list[dict[str, Any]] = []
    for report in candidates[:limit]:
        family = str(report.get("family") or "")
        spec = spec_by_family.get(family) or {}
        target_path = str(spec.get("_path") or Path(args.family_spec_dir) / f"{_slug(family)}.yaml")
        work_id = f"family_spec_generalize:{family}:{run_id}"
        task = (
            "Improve LeanMill family-spec supply quality in the target YAML file only. "
            "This is no-credit repair-family inventory work, not proof credit. Make the spec more general-purpose by adding "
            "one or two reusable sibling/heldout positive+negative_control row pairs, strengthening residual_match lanes/head_patterns, "
            "or retiring row-local templates that cannot be made reusable. Do not edit Python, scoreboards, registries, governance "
            "receipts, or research logs. After editing, the target YAML must parse, the family-spec gate must not gain failures, "
            "and the supply-quality receipt must show higher usable_pair_rows or a higher generality_score. "
            "If no safe improvement is available, emit JSON with exit_kind operator_required or retired and a concrete blocker. "
            f"Target YAML: {target_path}. Current supply-quality report: {json.dumps(report, sort_keys=True)}"
        )
        jobs.append({
            "kind": "agent_repair_task",
            "priority": int(_priority_base(args, "family_generality_repair", 205) + registry_scores.get(family, 0.0) + max(0, 40 - int(report.get("generality_score") or 0))),
            "work_id": work_id,
            "payload": {
                "work_id": work_id,
                "runtime": args.agent_runtime,
                "agent_id": f"leanmill_{args.agent_runtime}_family_spec_generalizer",
                "station": "repair_registry",
                "family": family,
                "task": task,
                "expected_exit": "family_spec_patch",
                "allowed_paths": [target_path, "/tmp/rung1"],
                "requires_negative_control": False,
                "proof_affecting": False,
                "max_iterations": args.agent_max_iterations,
                "max_wall_time_s": args.agent_max_wall_time_s,
                "family_spec_patch_target": target_path,
                "family_spec_patch_mode": "generalize_family_spec",
                "family_spec_supply_quality": report,
                "replenish_group": f"family_spec_generalize:{family}",
            },
            "artifact_paths": [target_path],
        })
    return jobs

def _source_or_proposal_jobs(args: argparse.Namespace) -> list[dict[str, Any]]:
    packet_obj = _read(args.packet)
    plan = _read(args.source_plan)
    allocator = _read(args.allocator)
    run_id = args.run_id or str(int(time.time()))
    ready_families = {
        str(p.get("repair_family") or "")
        for p in (packet_obj.get("packets") or [])
        if str(p.get("state") or "") == "ready_for_canary_build"
    }
    jobs: list[dict[str, Any]] = []
    source_packets = {str(p.get("repair_family") or ""): p for p in plan.get("packets") or []}
    no_spend = _no_spend_families(args.allocator)
    source_hold = _source_binding_hold_families(args.allocator)
    for rec in allocator.get("allocations") or []:
        if len(jobs) >= max(0, args.max_proposal_jobs):
            break
        family = str(rec.get("family") or "")
        action = str(rec.get("recommended_action") or "")
        if family in no_spend:
            continue
        if not family or family in ready_families:
            continue
        proposal_type = (
            "decomposition"
            if family in source_hold
            else "source_request" if action in {"seek_heldout_validation", "seek_sibling_or_hold", "seek_first_useful_exit_or_retire"} else "decomposition"
        )
        source_packet = source_packets.get(family) or {}
        scout_context = _source_scout_context(args, source_packet, family)
        if proposal_type == "source_request" and not scout_context.get("active_target_row_ids"):
            proposal_type = "decomposition"
        context = {
            "allocator": rec,
            "source_packet": source_packet,
            "source_scout_context": scout_context,
            "blocked_edge": (
                "source_binding_held_until_new_target_evidence"
                if family in source_hold
                else
                "no_active_target_rows_for_safe_source_request"
                if proposal_type == "decomposition" and not scout_context.get("active_target_row_ids")
                else ""
            ),
            "station_contract": _read(args.contract).get("station_contracts") or [],
            "anti_laundering": {
                "proposal_has_no_credit": True,
                "governance_gate_is_only_ratifier": True,
                "exact_gap_or_falsifier_requires_separate_validation": True,
            },
        }
        jobs.append({
            "kind": "source_request_propose" if proposal_type == "source_request" else "decomposition_propose",
            "priority": int(_priority_base(args, "proposal_from_allocator", 105) + float(rec.get("yield_score") or 0.0)),
            "work_id": f"proposal:{family}:{proposal_type}:{run_id}",
            "payload": {
                "work_id": f"proposal:{family}:{proposal_type}:{run_id}",
                "family": family,
                "proposal_type": proposal_type,
                "expected_outcome": "source_request" if proposal_type == "source_request" else "decomposition",
                "credit_type": "none",
                "context": context,
                "max_output_tokens": args.proposal_max_tokens,
            },
            "artifact_paths": [],
        })
    if len(jobs) < max(0, args.max_proposal_jobs):
        already = {str(job["payload"].get("family") or "") for job in jobs}
        for packet in plan.get("packets") or []:
            if len(jobs) >= max(0, args.max_proposal_jobs):
                break
            family = str(packet.get("repair_family") or "")
            if not family or family in already:
                continue
            if family in no_spend:
                continue
            if family in source_hold:
                continue
            if int(packet.get("lead_count") or 0) > 0:
                continue
            scout_context = _source_scout_context(args, packet, family)
            if not scout_context.get("active_target_row_ids"):
                continue
            context = {
                "source_packet": packet,
                "source_scout_context": scout_context,
                "station_contract": _read(args.contract).get("station_contracts") or [],
                "request": "propose targeted LeanSearch queries or row/source constraints that could produce target-context-ready sibling or heldout leads",
                "anti_laundering": {
                    "proposal_has_no_credit": True,
                    "governance_gate_is_only_ratifier": True,
                    "source_search_result_is_candidate_inventory_only": True,
                },
            }
            work_id = f"proposal:{family}:source_expansion:{run_id}"
            jobs.append({
                "kind": "source_request_propose",
                "priority": _priority_base(args, "source_expansion_proposal", 88),
                "work_id": work_id,
                "payload": {
                    "work_id": work_id,
                    "family": family,
                    "proposal_type": "source_request",
                    "expected_outcome": "source_request",
                    "credit_type": "none",
                    "context": context,
                    "max_output_tokens": args.proposal_max_tokens,
                },
                "artifact_paths": [],
            })
            already.add(family)
    return jobs


def _agent_jobs(args: argparse.Namespace) -> list[dict[str, Any]]:
    allocator = _read(args.allocator)
    packet_obj = _read(args.packet)
    source_plan = _read(args.source_plan)
    run_id = args.run_id or str(int(time.time()))
    ready = {
        str(p.get("repair_family") or ""): p
        for p in packet_obj.get("packets") or []
        if str(p.get("state") or "") == "ready_for_canary_build"
    }
    sibling_jobs: list[dict[str, Any]] = []
    no_spend = _no_spend_families(args.allocator)
    source_strategy_repair = _source_strategy_repair_families(args.allocator)
    source_hold = _source_binding_hold_families(args.allocator)
    source_packets = {str(p.get("repair_family") or ""): p for p in source_plan.get("packets") or []}
    strategy_jobs: list[dict[str, Any]] = []
    for rec in allocator.get("allocations") or []:
        if len(strategy_jobs) + len(sibling_jobs) >= max(0, args.max_agent_jobs):
            break
        family = str(rec.get("family") or "")
        if not family:
            continue
        if family in no_spend:
            continue
        if family in source_strategy_repair:
            source_packet = source_packets.get(family) or {}
            scout_context = _source_scout_context(args, source_packet, family)
            task = (
                "Repair the source strategy for this LeanMill family before any more source-bound probes. "
                "Recent source-bound work has produced no governed value, so do not return broad topic search. "
                "Return exactly one JSON object with `proposal_type` set to `source_strategy_repair`, "
                "`credit_type` set to `none`, and `expected_outcome` set to `source_strategy_repair`. "
                "Include `failure_diagnosis`, `changed_source_contract`, `required_row_features`, "
                "`queries_to_try`, `queries_to_forbid`, `corpus_expansion_requests`, "
                "`negative_control_ideas`, `retire_if_missing`, and `mechanical_validation_checks`. "
                "`corpus_expansion_requests` must name concrete missing row IDs, the source file or corpus path "
                "that would make each row active, and the expected learning-unit exit unlocked by the expansion. "
                "Queries must use theorem heads, carriers, coercions, directionality, hypotheses, or exact API names; "
                "avoid broad natural-language topics. Do not edit registries, scoreboards, governance receipts, or "
                "research logs. Do not claim proof value."
            )
            work_id = f"source_strategy:{family}:repair:{run_id}"
            strategy_jobs.append({
                "kind": "source_scout_task",
                "priority": int(_priority_base(args, "source_strategy_repair_agent", 125) + float(rec.get("yield_score") or 0.0)),
                "work_id": work_id,
                "payload": {
                    "work_id": work_id,
                    "runtime": args.agent_runtime,
                    "agent_id": f"leanmill_{args.agent_runtime}_source_strategy_repair",
                    "station": "source_qualification",
                    "family": family,
                    "task": (
                        task
                        + "\nAllocator record:\n"
                        + json.dumps(rec, indent=2, sort_keys=True)[:9000]
                        + "\nSource-scout context:\n"
                        + json.dumps(scout_context, indent=2, sort_keys=True)[:9000]
                    ),
                    "expected_exit": "source_strategy_repair",
                    "source_scout_context": scout_context,
                    "allowed_paths": [
                        "analytics/public/leanmill",
                        "scripts/public/control",
                        "/tmp/rung1",
                    ],
                    "requires_negative_control": False,
                    "proof_affecting": False,
                    "max_iterations": args.agent_max_iterations,
                    "max_wall_time_s": args.agent_max_wall_time_s,
                },
                "artifact_paths": [],
            })
            continue
        packet = ready.get(family)
        task = (
            "Inspect the current LeanMill family state and produce sibling or heldout candidates "
            "with a matched negative-control idea. Do not edit scoreboards, registries, governance "
            "reports, or research logs. Output only candidate artifacts/checks and reasons to retire if no safe sibling exists."
        )
        expected_exit = "sibling_candidates"
        if family in source_hold:
            expected_exit = "sibling_or_heldout_target_evidence"
            task += (
                " Source-bound probes for this family are currently held because recent source-bound work produced "
                "no governed value. Do not propose another source-bound probe. Produce independent target evidence: "
                "new sibling rows, heldout rows, exact-gap candidates, falsifier candidates, or a tested hold/retire reason. "
                "Return exactly one JSON object. Source requests are forbidden in this lane while the allocator holds "
                "source binding. If independent target evidence exists, use `proposal_type:\"decomposition\"`, "
                "`credit_type:\"none\"`, `expected_outcome:\"hold\"`, include concrete `target_row_ids`, "
                "`sibling_or_heldout_constraints`, `negative_control_ideas`, and `next_probe_contract`. "
                "If no safe route exists, use `proposal_type:\"decomposition\"`, `expected_outcome:\"hold\"` or "
                "`\"retire\"`, and name the blocked edge."
            )
        if packet:
            task += f"\nCurrent ready packet rows: {json.dumps(packet.get('selected_rows') or [], sort_keys=True)[:4000]}"
        work_id = f"agent:{family}:sibling_or_heldout:{run_id}"
        sibling_jobs.append({
            "kind": "agent_repair_task",
            "priority": int(_priority_base(args, "sibling_or_heldout_agent", 95) + float(rec.get("yield_score") or 0.0)),
            "work_id": work_id,
            "payload": {
                "work_id": work_id,
                "runtime": args.agent_runtime,
                "agent_id": f"leanmill_{args.agent_runtime}_sibling_hunter",
                "station": "repair_registry",
                "family": family,
                "task": task,
                "expected_exit": expected_exit,
                "allowed_paths": [
                    "analytics/public/leanmill",
                    "scripts/public/control",
                    "/tmp/rung1",
                ],
                "requires_negative_control": False,
                "proof_affecting": False,
                "max_iterations": args.agent_max_iterations,
                "max_wall_time_s": args.agent_max_wall_time_s,
            },
            "artifact_paths": [],
        })
    scout_jobs: list[dict[str, Any]] = []
    sibling_families = {str(job["payload"].get("family") or "") for job in sibling_jobs}
    sparse_packets = [
        p for p in (source_plan.get("packets") or [])
        if str(p.get("repair_family") or "") and int(p.get("lead_count") or 0) == 0
    ]
    for packet in sparse_packets:
        family = str(packet.get("repair_family") or "")
        if family in sibling_families:
            continue
        if family in no_spend:
            continue
        scout_context = _source_scout_context(args, packet, family)
        if not scout_context.get("active_target_row_ids"):
            continue
        task = (
            "Create search leverage for this residual family, not proof credit. Inspect the family source profile, "
            "residual/source artifacts, and nearby rows. "
            "Return exactly one JSON object when a search route is safe: "
            "{\"family\":\"...\",\"proposal_type\":\"source_request\",\"hypothesis\":\"...\","
            "\"credit_type\":\"none\",\"expected_outcome\":\"source_request\","
            "\"source_query\":[{\"schema\":\"leanmill-source-query-contract-v1\",\"kind\":\"declaration_ref\",\"decl_name\":\"Namespace.decl_name\",\"rationale\":\"...\"}],"
            "\"target_row_ids\":[\"...\"]}. "
            "The `source_query` list must contain 5-8 typed query objects, each tied to a row or theorem-shape reason. "
            "For `declaration_ref`, `decl_name` must be namespaced and contain a dot. For `theorem_shape`, include structural Lean signals. "
            "`target_row_ids` must be copied only from `active_target_row_ids` in the context. "
            "Also include `sibling_or_heldout_constraints`, `source_order_risks`, `target_context_risks`, and `negative_control_ideas`. "
            "If no source route is safe, return JSON with `proposal_type` set to `decomposition`, `expected_outcome` set to `hold` or `retire`, and a concrete blocked edge. "
            "Prefer theorem-head, carrier, coercion, directionality, and hypothesis-shape language over broad "
            "natural-language topic labels. Do not edit registries, scoreboards, governance receipts, or research "
            "logs. Do not claim proof value. Use the provided source-scout context as the authority for active target rows "
            "and recent rejection classes."
        )
        work_id = f"source_scout:{family}:queries_or_hold:{run_id}"
        scout_jobs.append({
            "kind": "source_scout_task",
            "priority": _priority_base(args, "source_scout_sparse_packet", 110),
            "work_id": work_id,
            "payload": {
                "work_id": work_id,
                "runtime": args.agent_runtime,
                "agent_id": f"leanmill_{args.agent_runtime}_source_scout",
                "station": "source_qualification",
                "family": family,
                "task": task + f"\nSource-scout context:\n{json.dumps(scout_context, indent=2, sort_keys=True)[:9000]}",
                "expected_exit": "source_request",
                "source_scout_context": scout_context,
                "allowed_paths": [
                    "analytics/public/leanmill",
                    "scripts/public/control",
                    "/tmp/rung1",
                ],
                "requires_negative_control": False,
                "proof_affecting": False,
                "max_iterations": args.agent_max_iterations,
                "max_wall_time_s": args.agent_max_wall_time_s,
            },
            "artifact_paths": [],
        })
    jobs: list[dict[str, Any]] = []
    buckets = [strategy_jobs, sibling_jobs, scout_jobs]
    while any(buckets) and len(jobs) < max(0, args.max_agent_jobs):
        for bucket in buckets:
            if bucket and len(jobs) < max(0, args.max_agent_jobs):
                jobs.append(bucket.pop(0))
    return jobs


def build(args: argparse.Namespace) -> dict[str, Any]:
    probe_jobs = [*_family_spec_probe_jobs(args), *_ready_probe_packets(args)]
    family_spec_repair_jobs = _family_spec_quarantine_repair_jobs(args)
    family_spec_generality_jobs = _family_spec_generality_jobs(args)
    proposal_jobs = _source_or_proposal_jobs(args)
    agent_jobs = _agent_jobs(args)
    if args.max_total_jobs:
        jobs = []
        buckets = [probe_jobs, family_spec_repair_jobs, family_spec_generality_jobs, proposal_jobs, agent_jobs]
        while any(buckets) and len(jobs) < max(0, args.max_total_jobs):
            for bucket in buckets:
                if bucket and len(jobs) < max(0, args.max_total_jobs):
                    jobs.append(bucket.pop(0))
    else:
        jobs = [*probe_jobs, *family_spec_repair_jobs, *family_spec_generality_jobs, *proposal_jobs, *agent_jobs]

    generated_job_count = len(jobs)
    jobs, routing = _route_jobs_for_node(jobs, args)

    payload = {
        "schema": "leanmill-learning-work-seed-plan-v1",
        "generated_at_epoch": int(time.time()),
        "dry_run": not args.enqueue,
        "generated_job_count": generated_job_count,
        "job_count": len(jobs),
        "routing": routing,
        "bucket_counts": {
            "probe": sum(1 for job in jobs if job.get("kind") == "repair_canary_probe"),
            "proposal": sum(1 for job in jobs if str(job.get("kind") or "") in {"source_request_propose", "decomposition_propose", "canary_propose", "llm_proposal_validate"}),
            "agent": sum(1 for job in jobs if job.get("kind") in {"agent_repair_task", "source_scout_task"}),
            "family_spec_repair": sum(1 for job in jobs if str((job.get("payload") or {}).get("family_spec_patch_mode") or "") == "repair_quarantine"),
            "family_spec_generalize": sum(1 for job in jobs if str((job.get("payload") or {}).get("family_spec_patch_mode") or "") == "generalize_family_spec"),
            "family_spec_patch": sum(1 for job in jobs if str((job.get("payload") or {}).get("expected_exit") or "") == "family_spec_patch"),
        },
        "jobs": jobs,
        "anti_laundering_rule": "Seeder emits bounded work only; proof value requires Governance Gate artifacts.",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.enqueue:
        cx = work_queue.connect(args.queue_db)
        retired_no_spend_open = _retire_no_spend_open_work(cx, allocator_path=args.allocator, events=args.events)
        retired_throttled_source_open = _retire_throttled_source_work(cx, allocator_path=args.allocator, events=args.events)
        enqueued = skipped_open = skipped_existing = 0
        skip_counts: dict[str, int] = {}
        enqueued_jobs: list[dict[str, Any]] = []
        for job in jobs:
            if args.max_enqueued and enqueued >= args.max_enqueued:
                break
            work_id = str(job["work_id"])
            family = str(job["payload"].get("family") or "")
            skip_decision = _learning_work_skip_reason(cx, args, job)
            if skip_decision is not None:
                bucket, reason = skip_decision
                if bucket == "open":
                    skipped_open += 1
                else:
                    skipped_existing += 1
                _skip(skip_counts, reason)
                continue
            work_queue.enqueue(
                cx,
                kind=str(job["kind"]),
                priority=int(job["priority"]),
                payload=dict(job["payload"]),
                max_attempts=args.max_attempts,
            )
            work_queue.append_event(args.events, {
                "event_type": "learning_work_enqueued",
                "work_id": work_id,
                "payload": {
                    "kind": job["kind"],
                    "family": job["payload"].get("family"),
                    "expected_exit": job["payload"].get("expected_exit"),
                    "credit_boundary": job["payload"].get("credit_boundary") or {"proof_credit_authority": "governance_gate"},
                },
                "artifact_paths": job.get("artifact_paths") or [],
            })
            enqueued += 1
            enqueued_jobs.append({
                "work_id": work_id,
                "kind": str(job["kind"]),
                "family": family,
                "expected_exit": job["payload"].get("expected_exit") or job["payload"].get("expected_outcome"),
            })
        payload["enqueued"] = enqueued
        payload["enqueued_jobs"] = enqueued_jobs
        payload["skipped_open"] = skipped_open
        payload["skipped_existing"] = skipped_existing
        payload["skip_counts"] = skip_counts
        payload["cooldowns"] = {
            "terminal_family_cooldown_s": int(args.terminal_family_cooldown_s),
            "terminal_proposal_family_cooldown_s": int(args.terminal_proposal_family_cooldown_s),
            "terminal_agent_family_cooldown_s": int(args.terminal_agent_family_cooldown_s),
            "terminal_probe_signature_cooldown_s": int(args.terminal_probe_signature_cooldown_s),
        }
        payload["retired_no_spend_open"] = retired_no_spend_open
        payload["retired_throttled_source_open"] = retired_throttled_source_open
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    obj = {
        "repair_family": "fam",
        "selected_rows": [{"row_id": "r1", "candidate_names": ["A.ok", "B.ok"]}],
    }
    tests = _packet_tests(obj, static_filter="sf.json", max_rows=1, max_candidates_per_row=1)
    assert len(tests) == 2
    assert tests[0]["source_credit_eligible"] is False
    assert tests[1]["test_kind"] == "negative_control"
    sig1 = _probe_signature("fam", "source_shape", tests)
    sig2 = _probe_signature("fam", "source_shape", list(reversed(tests)))
    assert sig1 == sig2
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_learning_work_seeder_") as td:
        primary = Path(td) / "primary.json"
        refill = Path(td) / "refill.json"
        primary.write_text(json.dumps({"rows": [{"row_id": "old", "goal": "old goal"}]}) + "\n")
        refill.write_text(json.dumps({"rows": [{"row_id": "new", "goal": "new goal", "source": "refill"}]}) + "\n")
        active = _active_corpus_rows([str(primary), str(refill)], {"new"})
        assert [row["row_id"] for row in active] == ["new"]
        assert active[0]["corpus"] == str(refill)
        stale = Path(td) / "stale.json"
        executable_file = Path(td) / "mcb_14_unique_alias_for_selftest.lean"
        executable_file.write_text("theorem other_decl : True := by\n  trivial\n\ntheorem unique_alias_for_selftest : True := by\n  trivial\n")
        expanded = Path(td) / "expanded.json"
        stale.write_text(json.dumps({"rows": [{
            "row_id": "MCB_999_unique_alias_for_selftest",
            "sorried_file": "Mathlib/Analysis/PSeries.lean",
            "target_line": 1,
        }]}) + "\n")
        expanded.write_text(json.dumps({"rows": [{
            "row_id": "MCB_014_unique_alias_for_selftest",
            "sorried_file": str(executable_file),
            "target_line": 1,
        }]}) + "\n")
        row_context = Path(td) / "row_context.json"
        row_context.write_text(json.dumps({"corpus": str(expanded)}) + "\n")
        corpus_args = argparse.Namespace(corpus=str(stale), row_context=str(row_context), out_dir=td)
        corpus_path, meta = _write_probe_corpus(
            corpus_args,
            family="fam",
            row_ids={"MCB_999_unique_alias_for_selftest"},
            out_dir=Path(td),
            run_id="alias",
            label="family_spec",
        )
        hydrated_obj = json.loads(Path(corpus_path).read_text())
        hydrated_rows = hydrated_obj["rows"]
        assert not meta["missing_row_ids"]
        assert hydrated_obj.get("corpus_signature")
        assert meta.get("reused_existing_corpus") is False
        assert hydrated_rows[0]["row_id"] == "MCB_999_unique_alias_for_selftest"
        assert hydrated_rows[0]["hydrated_from_row_id"] == "MCB_014_unique_alias_for_selftest"
        assert hydrated_rows[0]["sorried_file"] == str(executable_file)
        assert hydrated_rows[0]["target_theorem_name"] == "unique_alias_for_selftest", hydrated_rows[0]
        assert hydrated_rows[0]["target_line"] == 3, hydrated_rows[0]
        mismatch_file = Path(td) / "mcb_8_mellin_comp_rpow.lean"
        mismatch_file.write_text("theorem MellinConvergent.const_smul : True := by\n  trivial\n\ntheorem mellin_comp_rpow : True := by\n  trivial\n")
        mismatch_row = {
            "row_id": "MCB_008_mellin_comp_rpow",
            "source_file": str(mismatch_file),
            "goal": "theorem MellinConvergent.const_smul : True := by",
        }
        mismatch_resolved, mismatch_reason, mismatch_resolution = _normalize_probe_row(mismatch_row, "MCB_008_mellin_comp_rpow")
        assert mismatch_resolved is not None, mismatch_resolution
        assert mismatch_resolved["target_theorem_name"] == "mellin_comp_rpow", mismatch_resolved
        assert mismatch_resolved["target_line"] == 3, mismatch_resolved
        ambiguous_file = Path(td) / "ambiguous.lean"
        ambiguous_file.write_text("theorem alpha : True := by\n  trivial\n\ntheorem beta : True := by\n  trivial\n")
        ambiguous_row = {"row_id": "MCB_123_gamma", "source_file": str(ambiguous_file)}
        ambiguous_resolved, ambiguous_reason, ambiguous_resolution = _normalize_probe_row(ambiguous_row, "MCB_123_gamma")
        assert ambiguous_resolved is None, ambiguous_resolution
        assert ambiguous_reason == "target_theorem_not_resolved", ambiguous_resolution
        fallback_source_dir = Path(td) / "evaluation_harness_sources"
        fallback_source_dir.mkdir()
        fallback_file = fallback_source_dir / "MCB_555_fallback_target.lean"
        fallback_file.write_text("theorem fallback_target : True := by\n  trivial\n")
        old_fallback_dir = os.environ.get("LEANMILL_EVALUATION_HARNESS_SOURCE_DIR")
        try:
            os.environ["LEANMILL_EVALUATION_HARNESS_SOURCE_DIR"] = str(fallback_source_dir)
            fallback_resolved, fallback_reason, fallback_resolution = _normalize_probe_row(
                {"row_id": "MCB_555_fallback_target", "source_file": str(Path(td) / "missing.lean")},
                "MCB_555_fallback_target",
            )
            fallback_corpus = Path(td) / "fallback_corpus.json"
            fallback_corpus.write_text(json.dumps({"rows": [{
                "row_id": "MCB_555_fallback_target",
                "source_file": str(Path(td) / "missing.lean"),
            }]}) + "\n")
            fallback_corpus_path, fallback_meta = _write_probe_corpus(
                argparse.Namespace(corpus=str(fallback_corpus), row_context="", family_spec_selection=""),
                family="fam",
                row_ids={"MCB_555_fallback_target"},
                out_dir=Path(td),
                run_id="fallback",
                label="family_spec",
            )
            stale_selection = Path(td) / "stale_selection.json"
            rich_row_context = Path(td) / "rich_row_context.json"
            suffix_mismatch_file = fallback_source_dir / "MCB_065_toPMap_adjoint_eq_adjoint_toPMap.lean"
            suffix_mismatch_file.write_text(
                "theorem toPMap_adjoint_eq_adjoint_toPMap_of_dense : True := by\n  trivial\n"
            )
            stale_selection.write_text(json.dumps({"selected_rows": [{
                "row_id": "MCB_065_toPMap_adjoint_eq_adjoint_toPMap",
                "source_file": str(Path(td) / "stale_missing.lean"),
                "target_theorem_name": None,
            }]}) + "\n")
            rich_row_context.write_text(json.dumps({"rows": [{
                "row_id": "MCB_065_toPMap_adjoint_eq_adjoint_toPMap",
                "source_file": str(Path(td) / "also_missing.lean"),
                "source": {
                    "file": "Analysis/InnerProductSpace/LinearPMap.lean",
                    "mathlib_name": "toPMap_adjoint_eq_adjoint_toPMap_of_dense",
                },
            }]}) + "\n")
            mismatch_corpus_path, mismatch_meta = _write_probe_corpus(
                argparse.Namespace(corpus="", row_context=str(rich_row_context), family_spec_selection=str(stale_selection)),
                family="fam",
                row_ids={"MCB_065_toPMap_adjoint_eq_adjoint_toPMap"},
                out_dir=Path(td),
                run_id="rich_metadata",
                label="family_spec",
            )
        finally:
            if old_fallback_dir is None:
                os.environ.pop("LEANMILL_EVALUATION_HARNESS_SOURCE_DIR", None)
            else:
                os.environ["LEANMILL_EVALUATION_HARNESS_SOURCE_DIR"] = old_fallback_dir
        assert fallback_resolved is not None, fallback_resolution
        assert fallback_resolved["source_file"] == str(fallback_file), fallback_resolved
        assert fallback_resolved["target_theorem_name"] == "fallback_target", fallback_resolved
        assert not fallback_meta["missing_row_ids"], fallback_meta
        assert json.loads(Path(fallback_corpus_path).read_text())["rows"][0]["source_file"] == str(fallback_file)
        assert not mismatch_meta["missing_row_ids"], mismatch_meta
        mismatch_row = json.loads(Path(mismatch_corpus_path).read_text())["rows"][0]
        assert mismatch_row["target_theorem_name"] == "toPMap_adjoint_eq_adjoint_toPMap_of_dense", mismatch_row
        assert mismatch_row["source_file"] == str(suffix_mismatch_file), mismatch_row
        assert "mellin_comp_rpow" in _row_theorem_name_candidates({"row_id": "MCB_008_mellin_comp_rpow"}, "MCB_008_mellin_comp_rpow")
        non_generated_candidates = _row_theorem_name_candidates({"row_id": "v135_bohr_add"}, "v135_bohr_add")
        assert "add" not in non_generated_candidates, non_generated_candidates
        long_filter = _write_probe_static_filter(
            tests=[{"row_id": "MCB_001_" + "x" * 160, "candidate_name": "", "extra_body": ["trivial"]}],
            out_dir=Path(td),
            family="family_" + "y" * 220,
            run_id="run_" + "z" * 220,
            label="family_spec",
        )
        assert len(Path(long_filter).name.encode()) < 255, Path(long_filter).name
        corpus_path_2, meta_2 = _write_probe_corpus(
            corpus_args,
            family="fam",
            row_ids={"MCB_999_unique_alias_for_selftest"},
            out_dir=Path(td),
            run_id="alias_second",
            label="family_spec",
        )
        assert corpus_path_2 == corpus_path
        assert meta_2.get("reused_existing_corpus") is True
        db = str(Path(td) / "q.sqlite")
        cx = work_queue.connect(db)
        work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="done", priority=1, payload={
            "work_id": "probe1",
            "family": "fam",
            "probe_lane": "source_shape",
            "probe_signature": sig1,
        })
        assert _recent_terminal_same_probe_signature_exists(cx, signature=sig1, cooldown_s=3600)
        work_queue.enqueue(cx, kind="repair_canary_probe", priority=2, payload={
            "work_id": "probe2",
            "family": "fam",
            "probe_lane": "source_shape",
            "probe_signature": sig1,
        })
        assert _open_same_probe_signature_exists(cx, signature=sig1)
        sig3 = _probe_signature("fam", "source_shape", [{**tests[0], "row_id": "r2"}])
        assert sig3 != sig1
        distinct_probe = {
            "kind": "repair_canary_probe",
            "payload": {
                "family": "fam",
                "probe_lane": "source_shape",
                "probe_signature": sig3,
                "replenish_group": "fam:source_shape",
            },
        }
        assert _terminal_family_cooldown_for_job(argparse.Namespace(), distinct_probe) == 0
        assert not _recent_terminal_same_probe_signature_exists(cx, signature=sig3, cooldown_s=3600)
        route_args = argparse.Namespace(node_id="node-a", routing_nodes="node-a,node-b:2")
        routed, receipt = _route_jobs_for_node([
            {"work_id": "a", "payload": {"probe_signature": "sig-a"}},
            {"work_id": "b", "payload": {"probe_signature": "sig-b"}},
            {"work_id": "c", "payload": {"probe_signature": "sig-c"}},
        ], route_args)
        assert receipt["mode"] == "deterministic_hash"
        assert receipt["kept"] == len(routed)
        assert all((job["payload"].get("routing") or {}).get("assigned_node_id") == "node-a" for job in routed)
        selection = Path(td) / "selection.json"
        selection.write_text(json.dumps({"selected_rows": [{"row_id": "r1", "matched_families": ["fam"]}]}) + "\n")
        assert _chunks(["a", "b", "c"], 2) == [["a", "b"], ["c"]]
        assert _family_spec_selection_pairs(str(selection)) == {("fam", "r1")}
        exact_terminal_job = {
            "kind": "repair_canary_probe",
            "work_id": "probe-terminal-done",
            "payload": {
                "work_id": "probe-terminal-done",
                "family": "fam",
                "probe_lane": "family_spec",
                "probe_signature": "sig-terminal",
            },
        }
        work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="done", priority=1, payload=exact_terminal_job["payload"])
        retry_args = argparse.Namespace(
            retry_existing=True,
            terminal_probe_signature_cooldown_s=3600,
            terminal_family_cooldown_s=3600,
            terminal_proposal_family_cooldown_s=3600,
            terminal_agent_family_cooldown_s=3600,
        )
        assert _learning_work_skip_reason(cx, retry_args, exact_terminal_job) == ("existing", "terminal_exact_work_id_done")
        failed_terminal_job = {**exact_terminal_job, "work_id": "probe-terminal-failed", "payload": {**exact_terminal_job["payload"], "work_id": "probe-terminal-failed", "probe_signature": "sig-terminal-failed"}}
        work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="failed", priority=1, payload=failed_terminal_job["payload"])
        assert _learning_work_skip_reason(cx, retry_args, failed_terminal_job) is None
        priority_spec_dir = Path(td) / "priority_specs"
        priority_spec_dir.mkdir()
        (priority_spec_dir / "fam.yaml").write_text("""family: fam
version: 1
status: seed_only
residual_match:
  head_patterns: [fam]
credit:
  source_credit_eligible: false
  clean_solver_credit_eligible: false
templates:
  - id: fam_pos
    row_id: MCB_999_unique_alias_for_selftest
    test_kind: positive
    body: |
      trivial
  - id: fam_neg
    row_id: MCB_999_unique_alias_for_selftest
    test_kind: negative_control
    body: |
      exact False.elim (by trivial)
""")
        priority_args = argparse.Namespace(**vars(retry_args))
        priority_args.family_spec_activation_priority_floor = 999
        priority_args.run_id = "family_birth_activation_selftest"
        priority_args.max_family_spec_probe_families = 1
        priority_args.family_spec_selection = ""
        priority_args.family_spec_dir = str(priority_spec_dir)
        priority_args.allocator = str(Path(td) / "missing_allocator.json")
        priority_args.registry = str(Path(td) / "missing_registry.json")
        priority_args.corpus = str(stale)
        priority_args.row_context = str(row_context)
        priority_args.out_dir = str(Path(td) / "priority_out")
        priority_args.root_base = str(Path(td) / "priority_roots")
        priority_args.max_tests_per_probe = 4
        priority_args.family_spec_probe_rows_per_work_item = 1
        priority_args.probe_timeout_s = 120
        priority_args.probe_wall_timeout_s = 180
        priority_args.probe_command_timeout_s = 900
        priority_args.probe_command_timeout_overhead_s = 120
        priority_args.backend = "repl_file"
        priority_args.warm_repl_inline = True
        priority_args.govern_winners = True
        priority_jobs = _family_spec_probe_jobs(priority_args)
        assert priority_jobs and min(int(job["priority"]) for job in priority_jobs) >= 999
        selection_only_file = Path(td) / "mcb_777_selection_only_target.lean"
        selection_only_file.write_text("theorem selection_only_target : True := by\n  trivial\n")
        selection_only = Path(td) / "selection_only.json"
        selection_only.write_text(json.dumps({
            "selected_rows": [{
                "row_id": "MCB_777_selection_only_target",
                "matched_families": ["fam2"],
                "source_file": str(selection_only_file),
                "target_theorem_name": "selection_only_target",
            }],
        }) + "\n")
        selection_only_spec_dir = Path(td) / "selection_only_specs"
        selection_only_spec_dir.mkdir()
        (selection_only_spec_dir / "fam2.yaml").write_text("""family: fam2
version: 1
status: seed_only
residual_match:
  head_patterns: [fam2]
credit:
  source_credit_eligible: false
  clean_solver_credit_eligible: false
templates:
  - id: fam2_pos
    row_id: MCB_777_selection_only_target
    test_kind: positive
    body: |
      trivial
  - id: fam2_neg
    row_id: MCB_777_selection_only_target
    test_kind: negative_control
    body: |
      exact False.elim (by trivial)
""")
        selection_only_args = argparse.Namespace(**vars(priority_args))
        selection_only_args.family_spec_selection = str(selection_only)
        selection_only_args.family_spec_dir = str(selection_only_spec_dir)
        selection_only_args.corpus = ""
        selection_only_args.row_context = str(Path(td) / "missing_row_context.json")
        selection_only_args.out_dir = str(Path(td) / "selection_only_out")
        selection_only_jobs = _family_spec_probe_jobs(selection_only_args)
        assert len(selection_only_jobs) == 1, selection_only_jobs
        selection_probe = json.loads(Path(selection_only_jobs[0]["payload"]["corpus"]).read_text())
        assert selection_probe["rows"][0]["row_id"] == "MCB_777_selection_only_target", selection_probe
        assert selection_probe["rows"][0]["target_theorem_name"] == "selection_only_target", selection_probe
    print("leanmill_learning_work_seeder self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", default=DEFAULT_PACKET)
    ap.add_argument("--allocator", default=DEFAULT_ALLOCATOR)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--contract", default=DEFAULT_CONTRACT)
    ap.add_argument("--source-plan", default=DEFAULT_SOURCE_PLAN)
    ap.add_argument("--family-spec-dir", default=family_specs.DEFAULT_SPEC_DIR)
    ap.add_argument("--family-spec-selection", default="", help="Optional C-slice selection JSON; when set, only enqueue family_spec probes for selected (family,row) pairs.")
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--root-base", default=DEFAULT_ROOT_BASE)
    ap.add_argument("--out", default=f"{DEFAULT_DATA_DIR}/learning_work_seed_plan.json")
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--node-id", default="")
    ap.add_argument("--routing-nodes", default="", help="comma-separated deterministic routing node ids; use node:weight for weighted shards")
    ap.add_argument("--enqueue", action="store_true")
    ap.add_argument("--retry-existing", action="store_true")
    ap.add_argument("--terminal-family-cooldown-s", type=int, default=3600)
    ap.add_argument("--terminal-proposal-family-cooldown-s", type=int, default=900)
    ap.add_argument("--terminal-agent-family-cooldown-s", type=int, default=900)
    ap.add_argument("--terminal-probe-signature-cooldown-s", type=int, default=6 * 60 * 60)
    ap.add_argument("--max-attempts", type=int, default=1)
    ap.add_argument("--max-total-jobs", type=int, default=12)
    ap.add_argument("--max-enqueued", type=int, default=0)
    ap.add_argument("--max-probe-families", type=int, default=4)
    ap.add_argument("--max-family-spec-probe-families", type=int, default=2)
    ap.add_argument("--max-rows-per-family", type=int, default=2)
    ap.add_argument("--max-candidates-per-row", type=int, default=1)
    ap.add_argument("--max-tests-per-probe", type=int, default=4)
    ap.add_argument("--family-spec-probe-rows-per-work-item", type=int, default=1)
    ap.add_argument("--family-spec-activation-priority-floor", type=int, default=0)
    ap.add_argument("--max-proposal-jobs", type=int, default=4)
    ap.add_argument("--proposal-max-tokens", type=int, default=1200)
    ap.add_argument("--max-agent-jobs", type=int, default=1)
    ap.add_argument("--max-family-spec-repair-jobs", type=int, default=0)
    ap.add_argument("--max-family-spec-generality-jobs", type=int, default=0)
    ap.add_argument("--family-spec-repair-failures-per-job", type=int, default=8)
    ap.add_argument("--agent-runtime", choices=["codex", "claude"], default="codex")
    ap.add_argument("--agent-max-iterations", type=int, default=3)
    ap.add_argument("--agent-max-wall-time-s", type=int, default=1200)
    ap.add_argument("--backend", choices=["subprocess", "repl", "repl_step", "repl_file"], default="repl_file")
    ap.add_argument("--probe-timeout-s", type=int, default=120)
    ap.add_argument("--probe-wall-timeout-s", type=int, default=180)
    ap.add_argument("--probe-command-timeout-s", type=int, default=900)
    ap.add_argument("--probe-command-timeout-overhead-s", type=int, default=120)
    ap.add_argument("--warm-repl-inline", action="store_true")
    ap.add_argument("--govern-winners", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    apply_profile_section(args, section="learning_work_seeder")
    result = build(args)
    print(json.dumps({
        "job_count": result["job_count"],
        "dry_run": result["dry_run"],
        "enqueued": result.get("enqueued", 0),
        "skipped_open": result.get("skipped_open", 0),
        "skipped_existing": result.get("skipped_existing", 0),
        "skip_counts": result.get("skip_counts", {}),
        "out": args.out,
        "routing": result.get("routing", {}),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
