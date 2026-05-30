#!/usr/bin/env python3
"""Integrate qualified source-search runs into bounded LeanMill work.

Source search produces candidate inventory only. This bridge turns successful
source-search artifacts into explicit source-to-canary binding tasks for a
subscription agent or later deterministic compiler. It never awards proof
credit; Governance Gate remains the only proof-credit authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import (
    FACTORY_POLICY as DEFAULT_FACTORY_POLICY,
    apply_profile_section,
    priority_value,
)
from leanmill_family_specs import load_specs
from leanmill_paths import REPAIR_FAMILY_SPEC_DIR
from leanmill_source_query_contract import queries_pass_gate


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_OUT_DIR = f"{DEFAULT_DATA_DIR}/source_search_integrations"
DEFAULT_EXPAND100_CORPUS = f"{DEFAULT_DATA_DIR}/mcb_expand100_active_corpus.json"
DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_EXTRA_CORPORA = [
    "/tmp/rung1/mcb_refill_dedup_after_expand100/mcb_corpus.json",
    DEFAULT_EXPAND100_CORPUS,
    "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_QUEUE.json",
]
DEFAULT_RESIDUAL_PLAN = f"{DEFAULT_DATA_DIR}/residual_plan_final.json"
DEFAULT_CANARY_PACKETS = f"{DEFAULT_DATA_DIR}/residual_family_canary_packets.json"
DEFAULT_STATIC_FILTER = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_STATIC_FILTER.json"
DEFAULT_REPAIR_FAMILY_SPEC_DIR = str(REPAIR_FAMILY_SPEC_DIR)
RETRY_VERSION = "family_spec_seed_rows_v1"
DETERMINISTIC_BINDING_VERSION = "allowlist_receipt_binding_v1"


def _now() -> int:
    return int(time.time())


def _queue_priority(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY),
        namespace="work_queue",
        key=key,
        fallback=fallback,
    )


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _bounded_slug(value: str, *, max_prefix: int = 72, hash_len: int = 12) -> str:
    slug = _slug(value)
    digest = hashlib.sha256(value.encode()).hexdigest()[:hash_len]
    if len(slug) <= max_prefix:
        return f"{slug}_{digest}"
    return f"{slug[:max_prefix].rstrip('_')}_{digest}"


def _integration_artifact_stem(family: str, work_id: str) -> str:
    """Return a filesystem-safe, provenance-preserving receipt basename."""
    return (
        f"{_bounded_slug(family, max_prefix=48, hash_len=8)}_"
        f"{_bounded_slug(work_id, max_prefix=64, hash_len=12)}"
    )


def _read_json(path: str | Path | None) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _sha_file(path: str | Path) -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_search_rows(cx: sqlite3.Connection, limit: int, *, retry_held_target_holds: bool = False) -> list[dict[str, Any]]:
    retry_clause = ""
    if retry_held_target_holds:
        retry_clause = """
          OR (
            status='done'
            AND json_extract(payload_json, '$.exit_kind')='source_search_integrated_hold'
            AND COALESCE(json_extract(payload_json, '$.source_search_integration_retry_version'), '') != ?
          )
        """
    rows = cx.execute(
        f"""
        SELECT *
        FROM work_items
        WHERE kind='source_search_task'
          AND (
            (status='done' AND json_extract(payload_json, '$.source_search_integrated_at_epoch') IS NULL)
            {retry_clause}
          )
        ORDER BY updated_at ASC
        LIMIT ?
        """,
        (RETRY_VERSION, int(limit)) if retry_held_target_holds else (int(limit),),
    ).fetchall()
    return [work_queue.row_to_dict(row) for row in rows]


def _rejected_binding_rows(cx: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = cx.execute(
        """
        SELECT *
        FROM work_items
        WHERE kind='source_scout_task'
          AND status IN ('done', 'failed')
          AND work_id NOT LIKE 'source_bind_auto:%'
          AND json_extract(payload_json, '$.source_binding_ingest_status')='rejected_binding_artifact'
          AND json_extract(payload_json, '$.source_binding_deterministic_recovery_at_epoch') IS NULL
          AND json_extract(payload_json, '$.source_search_integration_receipt') IS NOT NULL
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    return [work_queue.row_to_dict(row) for row in rows]


def _rejected_auto_binding_rows(cx: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = cx.execute(
        """
        SELECT *
        FROM work_items
        WHERE kind='source_scout_task'
          AND status IN ('done', 'failed')
          AND work_id LIKE 'source_bind_auto:%'
          AND json_extract(payload_json, '$.source_binding_ingest_status')='rejected_binding_artifact'
          AND json_extract(payload_json, '$.source_binding_unrecoverable_at_epoch') IS NULL
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    return [work_queue.row_to_dict(row) for row in rows]


def _artifact_by_suffix(payload: dict[str, Any], suffix: str) -> str:
    for path in payload.get("artifact_paths") or []:
        if str(path).endswith(suffix):
            return str(path)
    return ""


def _static_filter_path(payload: dict[str, Any]) -> str:
    path = _artifact_by_suffix(payload, "static_filter.json")
    if path:
        return path
    for path in payload.get("artifact_paths") or []:
        obj = _read_json(path)
        if isinstance(obj, dict) and str(obj.get("schema") or "") == "leansearch-static-filter-v1":
            return str(path)
    return ""


def _top_source_candidates(static_obj: dict[str, Any], max_candidates: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in static_obj.get("rows") or []:
        row_id = str(row.get("row_id") or "")
        for cand in row.get("canary_ready_candidates") or []:
            name = str(cand.get("name") or "")
            if not name:
                continue
            if not bool(cand.get("usable_for_canary_source")) or not bool(cand.get("name_resolves")):
                continue
            key = (row_id, name)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "source_search_row_id": row_id,
                "candidate_name": name,
                "candidate_kind": cand.get("kind"),
                "module_name": cand.get("module_name"),
                "source_safety_status": cand.get("source_safety_status"),
                "source_order_status": cand.get("source_order_status"),
                "usable_for_canary_source": bool(cand.get("usable_for_canary_source")),
                "name_resolves": bool(cand.get("name_resolves")),
            })
            if len(out) >= max(1, int(max_candidates)):
                return out
    return out


def _append_unique_row_id(rows: list[str], row_id: str) -> None:
    rid = str(row_id or "")
    if rid and rid not in rows:
        rows.append(rid)


def _read_family_seed_rows(path: str, family: str) -> list[str]:
    obj = _read_json(path)
    if not isinstance(obj, dict):
        return []
    rows: list[str] = []
    for packet in obj.get("packets") or []:
        if str(packet.get("repair_family") or "") == family:
            for row_id in packet.get("rows") or packet.get("seed_rows") or []:
                _append_unique_row_id(rows, str(row_id or ""))
            for row in packet.get("selected_rows") or []:
                _append_unique_row_id(rows, str((row or {}).get("row_id") or ""))
    return rows[:20]


def _read_family_spec_seed_rows(spec_dir: str, family: str) -> list[str]:
    rows: list[str] = []
    for spec in load_specs(spec_dir):
        if str(spec.get("family") or "") != family:
            continue
        match = spec.get("residual_match") if isinstance(spec.get("residual_match"), dict) else {}
        for row_id in match.get("row_ids") or []:
            _append_unique_row_id(rows, str(row_id or ""))
        for template in spec.get("templates") or []:
            if isinstance(template, dict):
                _append_unique_row_id(rows, str(template.get("row_id") or ""))
        break
    return rows[:40]


def _read_seed_rows(canary_packets: str, family_spec_dir: str, family: str) -> list[str]:
    rows: list[str] = []
    for row_id in _read_family_seed_rows(canary_packets, family):
        _append_unique_row_id(rows, row_id)
    for row_id in _read_family_spec_seed_rows(family_spec_dir, family):
        _append_unique_row_id(rows, row_id)
    return rows[:40]


def _read_active_corpus_rows(path: str, *, limit: int = 80) -> list[dict[str, Any]]:
    obj = _read_json(path)
    rows = _row_records(obj)
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("row_id") or row.get("id") or "")
        if not row_id:
            continue
        out.append({
            "row_id": row_id,
            "goal": str(row.get("goal") or row.get("source_hinge") or "")[:500],
            "source": str(row.get("source") or row.get("sorried_file") or row.get("source_file") or "")[:220],
        })
        if len(out) >= max(1, int(limit)):
            break
    return out


def _active_corpus_rows_by_id(path: str) -> dict[str, dict[str, Any]]:
    obj = _read_json(path)
    rows = _row_records(obj)
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("row_id") or row.get("id") or "")
        if not row_id:
            continue
        out[row_id] = {
            "row_id": row_id,
            "goal": str(row.get("goal") or row.get("source_hinge") or "")[:500],
            "source": str(row.get("source") or row.get("sorried_file") or row.get("source_file") or "")[:220],
        }
    return out


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


def _active_corpus_rows_by_id_many(paths: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in paths:
        for row_id, row in _active_corpus_rows_by_id(path).items():
            if row_id not in out:
                out[row_id] = {**row, "corpus_path": path}
    return out


def _row_suffix(row_id: str) -> str:
    match = re.match(r"^MCB_\d+_(.+)$", str(row_id or ""))
    return match.group(1) if match else ""


def _active_corpus_rows_by_unique_suffix(active: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row_id, row in active.items():
        suffix = _row_suffix(row_id)
        if suffix:
            buckets.setdefault(suffix, []).append(row)
    return {suffix: rows[0] for suffix, rows in buckets.items() if len(rows) == 1}


def _read_active_corpus_rows_many(paths: list[str], *, limit: int = 80) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        for row in _read_active_corpus_rows(path, limit=limit):
            row_id = str(row.get("row_id") or "")
            if row_id and row_id not in seen:
                seen.add(row_id)
                out.append({**row, "corpus_path": path})
            if len(out) >= max(1, int(limit)):
                return out
    return out


def _corpus_paths(args: argparse.Namespace) -> list[str]:
    paths: list[str] = []
    for path in [str(args.corpus or ""), *[str(p or "") for p in (getattr(args, "extra_corpus", None) or [])]]:
        if path and path not in paths:
            paths.append(path)
    return paths


def _corpus_meta(paths: list[str]) -> list[dict[str, Any]]:
    metas: list[dict[str, Any]] = []
    for path in paths:
        obj = _read_json(path)
        rows = _row_records(obj)
        metas.append({
            "path": path,
            "sha256": _sha_file(path),
            "row_count": len(rows) if isinstance(rows, list) else 0,
        })
    return metas


def _allowed_binding_target_rows(
    *,
    corpus_paths: list[str],
    seed_rows: list[str],
    proposed_target_rows: list[str],
    candidates: list[dict[str, Any]],
    limit: int = 20,
) -> tuple[list[dict[str, Any]], list[str]]:
    active = _active_corpus_rows_by_id_many(corpus_paths)
    active_by_suffix = _active_corpus_rows_by_unique_suffix(active)
    allowed_ids: list[str] = []
    allowed_rows: list[dict[str, Any]] = []
    unresolved: list[str] = []

    def append_row(row_id: str) -> None:
        rid = str(row_id or "")
        if not rid:
            return
        row = active.get(rid)
        if not row:
            suffix = _row_suffix(rid)
            row = active_by_suffix.get(suffix) if suffix else None
            if row:
                row = {
                    **row,
                    "requested_row_id": rid,
                    "alias_resolution": "unique_mcb_theorem_suffix",
                }
        if not row:
            if rid not in unresolved:
                unresolved.append(rid)
            return
        active_row_id = str(row.get("row_id") or "")
        if active_row_id and active_row_id not in allowed_ids:
            allowed_ids.append(active_row_id)
            allowed_rows.append(row)

    for row_id in seed_rows:
        append_row(row_id)
    for row_id in proposed_target_rows:
        append_row(row_id)
    for candidate in candidates:
        append_row(str(candidate.get("source_search_row_id") or ""))
    return allowed_rows[: max(1, int(limit))], unresolved


def _queries_pass_gate(queries: list[Any], family: str) -> tuple[bool, list[dict[str, Any]]]:
    return queries_pass_gate(queries, family)


def _build_receipt(args: argparse.Namespace, item: dict[str, Any]) -> dict[str, Any]:
    payload = item.get("payload") or {}
    family = str(payload.get("family") or "unknown_family")
    static_path = _static_filter_path(payload)
    static_obj = _read_json(static_path)
    if not isinstance(static_obj, dict):
        static_obj = {}
    candidates = _top_source_candidates(static_obj, args.max_source_candidates)
    ready_total = int((payload.get("static_summary") or {}).get("canary_ready_total") or static_obj.get("canary_ready_total") or 0)
    summary_path = _artifact_by_suffix(payload, "summary.json")
    queries = payload.get("queries") or []
    proposed_target_rows = [str(r) for r in (payload.get("target_row_ids") or []) if str(r or "")]
    queries_ok, query_quality = _queries_pass_gate(queries, family)
    seed_rows = _read_seed_rows(args.canary_packets, args.family_spec_dir, family)
    allowed_target_rows, unresolved_target_rows = _allowed_binding_target_rows(
        corpus_paths=_corpus_paths(args),
        seed_rows=seed_rows,
        proposed_target_rows=proposed_target_rows,
        candidates=candidates,
    )
    inherited_failures = [
        q for q in (payload.get("query_quality") or [])
        if isinstance(q, dict) and not bool(q.get("accepted", True))
    ]
    blockers: list[str] = []
    if not queries_ok:
        blockers.append("low_quality_source_queries")
    if ready_total < args.min_canary_ready:
        blockers.append("insufficient_canary_ready_sources")
    if not candidates:
        blockers.append("no_ready_source_candidates")
    if not allowed_target_rows:
        blockers.append("no_allowed_active_binding_target_rows")
    receipt = {
        "schema": "leanmill-source-search-integration-v1",
        "created_at_epoch": _now(),
        "source_search_work_id": item["work_id"],
        "family": family,
        "queries": queries,
        "query_quality": query_quality,
        "rejected_query_quality": inherited_failures[:8],
        "source_search_summary": {
            "ready_total": ready_total,
            "source_summary": payload.get("source_summary") or {},
            "static_summary": payload.get("static_summary") or {},
        },
        "artifact_inputs": {
            "summary": summary_path,
            "static_filter": static_path,
            "source_packet": _artifact_by_suffix(payload, "source_packet.json"),
        },
        "top_source_candidates": candidates,
        "seed_or_prior_rows": seed_rows,
        "proposed_target_row_ids": proposed_target_rows,
        "active_corpus_rows": _read_active_corpus_rows_many(_corpus_paths(args)),
        "allowed_binding_target_rows": allowed_target_rows,
        "unresolved_binding_target_rows": unresolved_target_rows,
        "active_corpus": {
            "path": args.corpus,
            "sha256": _sha_file(args.corpus),
        },
        "active_corpora": _corpus_meta(_corpus_paths(args)),
        "exit_contract": {
            "expected_exit": "canary_spec_or_hold_or_retire",
            "proof_credit_authority": "governance_gate",
            "source_search_has_no_proof_credit": True,
            "agent_can_not_ratify": True,
            "must_pair_positive_with_negative_control": True,
        },
        "integration_decision": (
            "enqueue_source_to_canary_binding"
            if queries_ok and ready_total >= args.min_canary_ready and candidates and allowed_target_rows
            else "hold_low_quality_or_no_enough_sources"
        ),
        "integration_blockers": blockers,
    }
    return receipt


def _binding_task_query_quality(payload: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    receipt_path = str(payload.get("source_search_integration_receipt") or "")
    receipt = _read_json(receipt_path)
    if not isinstance(receipt, dict):
        return True, []
    return _queries_pass_gate(receipt.get("queries") or [], str(receipt.get("family") or payload.get("family") or ""))


def retire_low_quality_bindings(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    rows = cx.execute(
        """
        SELECT *
        FROM work_items
        WHERE kind='source_scout_task'
          AND status='queued'
          AND payload_json LIKE '%source_search_integration_receipt%'
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (int(args.max_retire_scan),),
    ).fetchall()
    retired: list[dict[str, Any]] = []
    for row in rows:
        item = work_queue.row_to_dict(row)
        payload = item.get("payload") or {}
        ok, quality = _binding_task_query_quality(payload)
        if ok:
            continue
        update = {
            "exit_kind": "retired_low_quality_source_query",
            "retired_at_epoch": _now(),
            "retire_reason": "source-to-canary binding came from process-shaped or non-theorem-shaped source queries",
            "query_quality": quality,
        }
        work_queue.update_status(cx, work_id=item["work_id"], status="retired", payload_update=update)
        work_queue.append_event(args.events, {
            "event_type": "source_to_canary_binding_retired_low_quality",
            "work_id": item["work_id"],
            "payload": {
                "family": payload.get("family"),
                "retire_reason": update["retire_reason"],
                "query_quality": quality,
            },
            "artifact_paths": [str(payload.get("source_search_integration_receipt") or "")],
        })
        retired.append({"work_id": item["work_id"], "family": payload.get("family"), "quality": quality})
    return {"retired": retired, "retired_count": len(retired), "scanned": len(rows)}


def _task_prompt(receipt: dict[str, Any], args: argparse.Namespace, *, bind_work_id: str, receipt_path: str) -> str:
    allowed_target_rows = [
        str((row or {}).get("row_id") or "")
        for row in (receipt.get("allowed_binding_target_rows") or [])
        if str((row or {}).get("row_id") or "")
    ]
    allowed_candidate_names = [
        str((cand or {}).get("candidate_name") or "")
        for cand in (receipt.get("top_source_candidates") or [])
        if str((cand or {}).get("candidate_name") or "")
    ]
    return (
        "Use this source-search receipt as candidate inventory only; "
        "do not award proof credit and do not edit scoreboards, registries, research logs, or governance receipts.\n\n"
        "Goal: bind the source candidates to concrete residual-family rows or sibling/heldout rows, then emit one of: "
        "canary_spec, retired, or operator_required. Do not declare exact gaps or valid falsifiers from this lane; "
        "those require a probe/governance lane receipt.\n\n"
        "Hard allowlists, copied exactly:\n"
        f"- allowed_target_row_ids: {json.dumps(allowed_target_rows, sort_keys=True)}\n"
        f"- allowed_candidate_names: {json.dumps(allowed_candidate_names, sort_keys=True)}\n"
        "If a target row or candidate name is not in these allowlists, do not use it. "
        "If the allowlists leave no safe binding, emit `retired` or `operator_required`; do not invent a row ID/name and do not emit an empty canary_spec.\n\n"
        "Required output: write one JSON artifact under `/tmp/rung1` or `analytics/public/leanmill` and print its exact path. "
        "The artifact must have schema `leanmill-source-to-canary-binding-v1` and this shape:\n"
        "{\n"
        '  "schema": "leanmill-source-to-canary-binding-v1",\n'
        f'  "family": "{receipt.get("family")}",\n'
        f'  "parent_work_id": "{bind_work_id}",\n'
        f'  "source_search_integration_receipt": "{receipt_path}",\n'
        '  "decision": "canary_spec|retired|operator_required",\n'
        '  "concrete_target_row_ids": ["..."],\n'
        '  "positive_source_to_canary_attempts": [{\n'
        '    "target_row_id": "...",\n'
        '    "candidate_names": ["..."],\n'
        '    "action_family": "apply_easy|rw|simp|exact_gap|decomposition",\n'
        '    "attempt_shape": "...",\n'
        '    "matched_negative_control": "..."\n'
        "  }],\n"
        '  "source_order_risks": ["..."],\n'
        '  "target_context_risks": ["..."]\n'
        "}\n\n"
        f"Identity rule: `parent_work_id` must equal `{bind_work_id}` and `source_search_integration_receipt` must equal `{receipt_path}`. "
        "Target-row rule: every `target_row_id` must be copied exactly from `allowed_binding_target_rows[].row_id` in the receipt. "
        "Do not use row IDs from query text, source-search comments, or `seed_or_prior_rows` unless the same ID is listed in `allowed_binding_target_rows`. "
        "Candidate-name rule: every `candidate_names[]` entry must come from `top_source_candidates[].candidate_name` unless you mark the artifact `operator_required` and explain why. "
        "Control rule: every positive attempt must include a matched negative control that should fail if the source route is spurious.\n\n"
        "Rules: candidate source names are not proof value; compile-only results still need Governance Gate; "
        "if no independent sibling or heldout row can be bound safely, emit retired or operator_required with the blocked edge.\n\n"
        f"Default corpus: {args.corpus}\n"
        f"Default residual plan: {args.residual_plan}\n"
        f"Default static filter: {args.static_filter}\n\n"
        f"Receipt:\n{json.dumps(receipt, indent=2, sort_keys=True)[:12000]}\n"
    )


def _deterministic_binding(receipt: dict[str, Any], *, bind_work_id: str, receipt_path: str, args: argparse.Namespace) -> dict[str, Any]:
    candidates = [
        str(c.get("candidate_name") or "")
        for c in (receipt.get("top_source_candidates") or [])
        if str(c.get("candidate_name") or "")
    ][: max(1, int(args.deterministic_binding_candidates_per_row))]
    rows = [
        str(r.get("row_id") or "")
        for r in (receipt.get("allowed_binding_target_rows") or [])
        if str(r.get("row_id") or "")
    ][: max(1, int(args.deterministic_binding_max_rows))]
    attempts = []
    for row_id in rows:
        attempts.append({
            "target_row_id": row_id,
            "candidate_names": candidates,
            "action_family": "apply_easy",
            "attempt_shape": "deterministic allowlist source-to-canary probe; Proof Execution must test exact/simpa/apply and controls",
            "matched_negative_control": f"unresolved sentinel for {row_id} must fail if source route is spurious",
        })
    return {
        "schema": "leanmill-source-to-canary-binding-v1",
        "family": receipt.get("family"),
        "parent_work_id": bind_work_id,
        "source_search_integration_receipt": receipt_path,
        "decision": "canary_spec",
        "binding_compiler": DETERMINISTIC_BINDING_VERSION,
        "concrete_target_row_ids": rows,
        "positive_source_to_canary_attempts": attempts,
        "source_order_risks": ["deterministic bridge uses source-search receipt allowlist only; proof credit remains disabled"],
        "target_context_risks": ["candidate may be an internal lemma rather than a direct proof; source-action preflight must classify residuals"],
        "credit_boundary": {
            "source_credit_eligible": False,
            "clean_solver_credit_eligible": False,
            "repair_canary_credit_only": True,
            "proof_credit_authority": "governance_gate",
            "worker_can_self_ratify": False,
        },
    }


def _record_binding_work(
    args: argparse.Namespace,
    *,
    item: dict[str, Any],
    receipt: dict[str, Any],
    receipt_path: str,
    md_path: str,
) -> tuple[str, bool, str]:
    family = str(receipt["family"])
    if args.binding_mode == "agent":
        bind_work_id = f"source_bind:{_slug(family)}:{_slug(item['work_id'])}"
        payload = {
            "work_id": bind_work_id,
            "runtime": args.agent_runtime,
            "agent_id": f"leanmill_{args.agent_runtime}_source_integrator",
            "station": "source_qualification",
            "family": family,
            "task": _task_prompt(receipt, args, bind_work_id=bind_work_id, receipt_path=receipt_path),
            "expected_exit": "canary_spec",
            "allowed_paths": [
                "analytics/public/leanmill",
                "scripts/public/control",
                "/tmp/rung1",
            ],
            "requires_negative_control": False,
            "proof_affecting": False,
            "max_iterations": args.agent_max_iterations,
            "max_wall_time_s": args.agent_max_wall_time_s,
            "parent_work_id": item["work_id"],
            "source_search_integration_receipt": receipt_path,
            "credit_boundary": receipt["exit_contract"],
        }
        cx = work_queue.connect(args.queue_db)
        before = cx.total_changes
        work_queue.enqueue(cx, kind="source_scout_task", priority=args.priority, payload=payload, max_attempts=args.max_attempts)
        return bind_work_id, cx.total_changes > before, "agent"

    bind_work_id = f"source_bind_auto:{_slug(family)}:{_slug(item['work_id'])}"
    binding_path = Path(args.out_dir) / f"{_bounded_slug(family, max_prefix=48, hash_len=8)}_{_bounded_slug(item['work_id'], max_prefix=64, hash_len=12)}_binding.json"
    binding = _deterministic_binding(receipt, bind_work_id=bind_work_id, receipt_path=receipt_path, args=args)
    _write_json(binding_path, binding)
    payload = {
        "work_id": bind_work_id,
        "runtime": "deterministic",
        "agent_id": "leanmill_deterministic_source_binding_compiler",
        "station": "source_qualification",
        "family": family,
        "expected_exit": "canary_spec",
        "exit_kind": "source_binding_compiled",
        "source_binding_compiler": DETERMINISTIC_BINDING_VERSION,
        "parent_work_id": item["work_id"],
        "source_search_integration_receipt": receipt_path,
        "artifact_paths": [receipt_path, md_path, str(binding_path)],
        "credit_boundary": receipt["exit_contract"],
    }
    cx = work_queue.connect(args.queue_db)
    before = cx.total_changes
    work_queue.record_terminal_item(cx, kind="source_scout_task", status="done", priority=args.priority, payload=payload, max_attempts=1)
    return bind_work_id, cx.total_changes > before, "deterministic"


def recover_rejected_bindings(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    rows = _rejected_binding_rows(cx, args.max_recover)
    recovered: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    def mark_unrecoverable(item: dict[str, Any], reason: str, receipt_path: str = "") -> None:
        work_queue.update_status(cx, work_id=item["work_id"], status=item.get("status") or "done", payload_update={
            "source_binding_unrecoverable_at_epoch": _now(),
            "source_binding_recovery_status": f"unrecoverable_{reason}",
        })
        work_queue.append_event(args.events, {
            "event_type": "source_binding_rejection_marked_unrecoverable",
            "work_id": item["work_id"],
            "payload": {
                "family": (item.get("payload") or {}).get("family"),
                "reason": reason,
            },
            "artifact_paths": [receipt_path] if receipt_path else [],
        })

    for item in _rejected_auto_binding_rows(cx, args.max_recover):
        payload = item.get("payload") or {}
        receipt_path = str(payload.get("source_search_integration_receipt") or "")
        mark_unrecoverable(item, "auto_binding_rejected_after_recovery", receipt_path)
        skipped.append({"work_id": item["work_id"], "reason": "auto_binding_rejected_after_recovery"})

    for item in rows:
        payload = item.get("payload") or {}
        receipt_path = str(payload.get("source_search_integration_receipt") or "")
        receipt = _read_json(receipt_path)
        if not isinstance(receipt, dict):
            mark_unrecoverable(item, "missing_receipt", receipt_path)
            skipped.append({"work_id": item["work_id"], "reason": "missing_receipt"})
            continue
        if receipt.get("integration_decision") != "enqueue_source_to_canary_binding":
            mark_unrecoverable(item, "receipt_not_binding_ready", receipt_path)
            skipped.append({"work_id": item["work_id"], "reason": "receipt_not_binding_ready"})
            continue
        candidates = receipt.get("top_source_candidates") or []
        allowed_rows = receipt.get("allowed_binding_target_rows") or []
        if not candidates or not allowed_rows:
            mark_unrecoverable(item, "receipt_missing_candidates_or_rows", receipt_path)
            skipped.append({"work_id": item["work_id"], "reason": "receipt_missing_candidates_or_rows"})
            continue
        bind_work_id, created, mode = _record_binding_work(
            args,
            item={"work_id": f"recovery:{item['work_id']}"},
            receipt=receipt,
            receipt_path=receipt_path,
            md_path=str(Path(receipt_path).with_suffix(".md")),
        )
        work_queue.update_status(cx, work_id=item["work_id"], status=item.get("status") or "done", payload_update={
            "source_binding_deterministic_recovery_at_epoch": _now(),
            "source_binding_deterministic_recovery_work_id": bind_work_id,
            "source_binding_deterministic_recovery_mode": mode,
        })
        work_queue.append_event(args.events, {
            "event_type": "source_binding_rejection_recovered_deterministically",
            "work_id": bind_work_id,
            "payload": {
                "family": receipt.get("family") or payload.get("family"),
                "recovered_from_work_id": item["work_id"],
                "created": created,
                "binding_mode": mode,
            },
            "artifact_paths": [receipt_path],
        })
        recovered.append({"work_id": item["work_id"], "recovery_work_id": bind_work_id, "created": created})
    return {
        "schema": "leanmill-source-binding-rejection-recovery-v1",
        "recovered_count": len(recovered),
        "skipped_count": len(skipped),
        "recovered": recovered,
        "skipped": skipped,
    }


def integrate_one(args: argparse.Namespace, item: dict[str, Any]) -> dict[str, Any]:
    receipt = _build_receipt(args, item)
    out_dir = Path(args.out_dir)
    out_path = out_dir / f"{_integration_artifact_stem(str(receipt['family']), str(item['work_id']))}.json"
    md_path = out_path.with_suffix(".md")
    _write_json(out_path, receipt)
    md_path.write_text(
        "\n".join([
            f"# Source Search Integration: {receipt['family']}",
            "",
            f"- source search work: `{item['work_id']}`",
            f"- decision: `{receipt['integration_decision']}`",
            f"- ready candidates: `{receipt['source_search_summary']['ready_total']}`",
            f"- proof credit authority: `{receipt['exit_contract']['proof_credit_authority']}`",
            "",
            "Top candidates:",
            *[
                f"- `{c['candidate_name']}` from `{c.get('module_name') or ''}`"
                for c in receipt.get("top_source_candidates") or []
            ],
            "",
        ]),
        encoding="utf-8",
    )
    result: dict[str, Any] = {
        "ok": True,
        "exit_kind": "source_search_integrated",
        "source_search_integrated_at_epoch": _now(),
        "source_search_integration_receipt": str(out_path),
        "artifact_paths": [*list(item.get("payload", {}).get("artifact_paths") or []), str(out_path), str(md_path)],
        "integration_decision": receipt["integration_decision"],
    }
    if receipt["integration_decision"] != "enqueue_source_to_canary_binding":
        result["exit_kind"] = "source_search_integrated_hold"
        return result

    bind_work_id, enqueued, binding_mode = _record_binding_work(
        args,
        item=item,
        receipt=receipt,
        receipt_path=str(out_path),
        md_path=str(md_path),
    )
    work_queue.append_event(args.events, {
        "event_type": "source_to_canary_binding_compiled" if binding_mode == "deterministic" else ("source_to_canary_binding_enqueued" if enqueued else "source_to_canary_binding_already_present"),
        "work_id": bind_work_id,
        "payload": {
            "family": receipt["family"],
            "parent_work_id": item["work_id"],
            "expected_exit": "canary_spec",
            "source_search_integration_receipt": str(out_path),
            "binding_mode": binding_mode,
        },
        "artifact_paths": [str(out_path), str(md_path)],
    })
    result["enqueued_binding_work_id"] = bind_work_id
    result["binding_task_enqueued"] = bool(enqueued)
    result["binding_mode"] = binding_mode
    return result


def work_once(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    rows = _source_search_rows(cx, limit=1, retry_held_target_holds=args.retry_held_target_holds)
    if not rows:
        return {"claimed": False}
    item = rows[0]
    payload = item.get("payload") or {}
    retrying_hold = str(payload.get("exit_kind") or "") == "source_search_integrated_hold"
    if not payload.get("ok"):
        work_queue.update_status(cx, work_id=item["work_id"], status="done", payload_update={
            "source_search_integrated_at_epoch": _now(),
            "source_search_integration_skipped_reason": "source_search_not_ok",
        })
        return {"claimed": True, "work_id": item["work_id"], "status": "skipped", "reason": "source_search_not_ok"}
    result = integrate_one(args, item)
    if retrying_hold:
        result["source_search_integration_retry_version"] = RETRY_VERSION
        result["source_search_integration_retried_at_epoch"] = _now()
    work_queue.update_status(cx, work_id=item["work_id"], status="done", payload_update=result)
    work_queue.append_event(args.events, {
        "event_type": "source_search_integrator_retried_hold_done" if retrying_hold else "source_search_integrator_done",
        "work_id": item["work_id"],
        "payload": {
            "family": payload.get("family"),
            "exit_kind": result.get("exit_kind"),
            "binding_task_enqueued": result.get("binding_task_enqueued"),
            "enqueued_binding_work_id": result.get("enqueued_binding_work_id"),
            "retry_version": RETRY_VERSION if retrying_hold else "",
        },
        "artifact_paths": result.get("artifact_paths") or [],
    })
    return {"claimed": True, "work_id": item["work_id"], "status": "done", "exit_kind": result.get("exit_kind")}


def daemon_loop(args: argparse.Namespace) -> dict[str, Any]:
    completed = 0
    idle_ticks = 0
    last: dict[str, Any] = {}
    while True:
        if args.max_tasks and completed >= args.max_tasks:
            break
        result = work_once(args)
        last = result
        if result.get("claimed"):
            completed += 1
            idle_ticks = 0
            print(json.dumps({"daemon": args.worker_id, "task_result": result}, sort_keys=True), flush=True)
            continue
        idle_ticks += 1
        print(json.dumps({"daemon": args.worker_id, "idle": True}, sort_keys=True), flush=True)
        if args.max_idle_ticks and idle_ticks >= args.max_idle_ticks:
            break
        time.sleep(max(1, int(args.idle_sleep_s)))
    return {"daemon": args.worker_id, "completed_tasks": completed, "last_result": last}


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_source_integrator_") as td:
        root = Path(td)
        db = str(root / "q.sqlite")
        events = str(root / "events.jsonl")
        static = root / "static_filter.json"
        summary = root / "summary.json"
        static.write_text(json.dumps({
            "schema": "leansearch-static-filter-v1",
            "canary_ready_total": 1,
            "rows": [{
                "row_id": "MCB_X",
                "canary_ready_candidates": [{
                    "name": "Matrix.linearIndependent_of_posDef_gram",
                    "kind": "theorem",
                    "module_name": "Mathlib.Analysis.InnerProductSpace.GramMatrix",
                    "name_resolves": True,
                    "usable_for_canary_source": True,
                }],
            }],
        }) + "\n")
        summary.write_text(json.dumps({"schema": "leanmill-source-search-result-v1"}) + "\n")
        corpus = root / "corpus.json"
        corpus.write_text(json.dumps({"rows": [
            {"id": "MCB_X", "goal": "Matrix gram PosDef LinearIndependent"},
            {"id": "MCB_012_isBigO_rpow_top_log_smul", "goal": "Big-O rpow top log smul"},
        ]}) + "\n")
        packets = root / "packets.json"
        packets.write_text(json.dumps({"packets": [{
            "repair_family": "gram_posdef_linear_independent_planner",
            "seed_rows": ["MCB_X"],
        }]}) + "\n")
        spec_dir = root / "repair_families"
        spec_dir.mkdir()
        (spec_dir / "spec_only_planner.yaml").write_text(
            "family: spec_only_planner\n"
            "version: 1\n"
            "status: seed_only\n"
            "credit:\n"
            "  source_credit_eligible: false\n"
            "  clean_solver_credit_eligible: false\n"
            "residual_match:\n"
            "  row_ids:\n"
            "    - MCB_X\n"
            "templates: []\n"
        )
        cx = work_queue.connect(db)
        wid = "source_search:fam:test"
        work_queue.enqueue(cx, kind="source_search_task", priority=1, payload={
            "work_id": wid,
            "family": "gram_posdef_linear_independent_planner",
            "ok": True,
            "queries": ["gram positive definite LinearIndependent"],
            "static_summary": {"canary_ready_total": 1},
            "artifact_paths": [str(static), str(summary)],
        })
        work_queue.update_status(cx, work_id=wid, status="done")
        result = work_once(argparse.Namespace(
            queue_db=db,
            events=events,
            worker_id="self-test",
            out_dir=str(root / "out"),
            min_canary_ready=1,
            max_source_candidates=3,
            canary_packets=str(packets),
            family_spec_dir=str(root / "repair_families"),
            corpus=str(corpus),
            extra_corpus=[],
            residual_plan="residual.json",
            static_filter="static.json",
            binding_mode="deterministic",
            deterministic_binding_max_rows=3,
            deterministic_binding_candidates_per_row=2,
            agent_runtime="codex",
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            priority=120,
            max_attempts=1,
            retry_held_target_holds=False,
            max_recover=10,
        ))
        assert result["claimed"] is True
        row = cx.execute("SELECT payload_json FROM work_items WHERE work_id=?", (wid,)).fetchone()
        assert row and "source_search_integrated_at_epoch" in row["payload_json"]
        row_payload = json.loads(row["payload_json"])
        receipt_path = str(row_payload["source_search_integration_receipt"])
        bind = cx.execute("SELECT payload_json, status FROM work_items WHERE kind='source_scout_task'").fetchone()
        assert bind is not None and bind["status"] == "done"
        bind_payload = json.loads(bind["payload_json"])
        binding_artifact = next(Path(p) for p in bind_payload["artifact_paths"] if str(p).endswith("_binding.json"))
        binding = json.loads(binding_artifact.read_text())
        assert binding["parent_work_id"] == bind_payload["work_id"]
        assert binding["positive_source_to_canary_attempts"][0]["candidate_names"] == ["Matrix.linearIndependent_of_posDef_gram"]

        alias_rows, unresolved = _allowed_binding_target_rows(
            corpus_paths=[str(corpus)],
            seed_rows=[],
            proposed_target_rows=["MCB_009_isBigO_rpow_top_log_smul", "MCB_404_missing"],
            candidates=[],
        )
        assert [r["row_id"] for r in alias_rows] == ["MCB_012_isBigO_rpow_top_log_smul"]
        assert alias_rows[0]["requested_row_id"] == "MCB_009_isBigO_rpow_top_log_smul"
        assert alias_rows[0]["alias_resolution"] == "unique_mcb_theorem_suffix"
        assert unresolved == ["MCB_404_missing"]

        pruned_wid = "source_search:fam:pruned"
        work_queue.enqueue(cx, kind="source_search_task", priority=1, payload={
            "work_id": pruned_wid,
            "family": "gram_posdef_linear_independent_planner",
            "ok": True,
            "queries": ["Matrix.PosDef.gram", "LinearIndependent.gram_matrix", "Matrix.linearIndependent_of_posDef_gram"],
            "target_row_ids": ["MCB_X"],
            "query_quality": [
                {"query": "bad process text", "accepted": False, "failures": ["process_or_control_language:leanmill"]},
            ],
            "static_summary": {"canary_ready_total": 1},
            "artifact_paths": [str(static), str(summary)],
        })
        work_queue.update_status(cx, work_id=pruned_wid, status="done")
        pruned_result = work_once(argparse.Namespace(
            queue_db=db,
            events=events,
            worker_id="self-test",
            out_dir=str(root / "out"),
            min_canary_ready=1,
            max_source_candidates=3,
            canary_packets=str(packets),
            family_spec_dir=str(root / "repair_families"),
            corpus=str(corpus),
            extra_corpus=[],
            residual_plan="residual.json",
            static_filter="static.json",
            binding_mode="deterministic",
            deterministic_binding_max_rows=3,
            deterministic_binding_candidates_per_row=2,
            agent_runtime="codex",
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            priority=120,
            max_attempts=1,
            retry_held_target_holds=False,
            max_recover=10,
        ))
        assert pruned_result["claimed"] is True and pruned_result["exit_kind"] == "source_search_integrated"

        spec_only_wid = "source_search:spec_only:test"
        work_queue.enqueue(cx, kind="source_search_task", priority=1, payload={
            "work_id": spec_only_wid,
            "family": "spec_only_planner",
            "ok": True,
            "queries": ["gram positive definite LinearIndependent"],
            "static_summary": {"canary_ready_total": 1},
            "artifact_paths": [str(static), str(summary)],
        })
        work_queue.update_status(cx, work_id=spec_only_wid, status="done")
        spec_only_result = work_once(argparse.Namespace(
            queue_db=db,
            events=events,
            worker_id="self-test",
            out_dir=str(root / "out"),
            min_canary_ready=1,
            max_source_candidates=3,
            canary_packets=str(packets),
            family_spec_dir=str(spec_dir),
            corpus=str(corpus),
            extra_corpus=[],
            residual_plan="residual.json",
            static_filter="static.json",
            binding_mode="deterministic",
            deterministic_binding_max_rows=3,
            deterministic_binding_candidates_per_row=2,
            agent_runtime="codex",
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            priority=120,
            max_attempts=1,
            retry_held_target_holds=False,
            max_recover=10,
        ))
        assert spec_only_result["claimed"] is True and spec_only_result["exit_kind"] == "source_search_integrated"
        spec_only_payload = json.loads(cx.execute("SELECT payload_json FROM work_items WHERE work_id=?", (spec_only_wid,)).fetchone()["payload_json"])
        spec_only_receipt = json.loads(Path(spec_only_payload["source_search_integration_receipt"]).read_text())
        assert [r["row_id"] for r in spec_only_receipt["allowed_binding_target_rows"]] == ["MCB_X"]

        long_id = "source_search:" + ":".join(["agent_output_review"] * 20)
        long_family = "gram_posdef_linear_independent_planner_" + "_".join(["heldout"] * 20)
        work_queue.enqueue(cx, kind="source_search_task", priority=1, payload={
            "work_id": long_id,
            "family": long_family,
            "ok": True,
            "queries": ["gram positive definite LinearIndependent"],
            "target_row_ids": ["MCB_X"],
            "static_summary": {"canary_ready_total": 1},
            "artifact_paths": [str(static), str(summary)],
        })
        work_queue.update_status(cx, work_id=long_id, status="done")
        long_result = work_once(argparse.Namespace(
            queue_db=db,
            events=events,
            worker_id="self-test",
            out_dir=str(root / "out"),
            min_canary_ready=1,
            max_source_candidates=3,
            canary_packets=str(packets),
            family_spec_dir=str(root / "repair_families"),
            corpus=str(corpus),
            extra_corpus=[],
            residual_plan="residual.json",
            static_filter="static.json",
            binding_mode="deterministic",
            deterministic_binding_max_rows=3,
            deterministic_binding_candidates_per_row=2,
            agent_runtime="codex",
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            priority=120,
            max_attempts=1,
            retry_held_target_holds=False,
            max_recover=10,
        ))
        assert long_result["claimed"] is True
        long_payload = json.loads(cx.execute("SELECT payload_json FROM work_items WHERE work_id=?", (long_id,)).fetchone()["payload_json"])
        long_receipt = Path(long_payload["source_search_integration_receipt"])
        assert long_receipt.exists()
        assert len(long_receipt.name) < 180
        work_queue.update_status(cx, work_id=bind_payload["work_id"], status="done", payload_update={
            "source_binding_ingest_status": "rejected_binding_artifact",
        })
        ignored_auto_recovery = recover_rejected_bindings(argparse.Namespace(
            queue_db=db,
            events=events,
            worker_id="self-test",
            out_dir=str(root / "out"),
            min_canary_ready=1,
            max_source_candidates=3,
            canary_packets=str(packets),
            family_spec_dir=str(root / "repair_families"),
            corpus=str(corpus),
            extra_corpus=[],
            residual_plan="residual.json",
            static_filter="static.json",
            binding_mode="deterministic",
            deterministic_binding_max_rows=3,
            deterministic_binding_candidates_per_row=2,
            agent_runtime="codex",
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            priority=120,
            max_attempts=1,
            retry_held_target_holds=False,
            max_recover=10,
        ))
        assert ignored_auto_recovery["recovered_count"] == 0
        legacy_bind_work_id = "source_bind:gram_posdef_linear_independent_planner:legacy_agent_binding"
        work_queue.record_terminal_item(cx, kind="source_scout_task", status="done", priority=120, payload={
            "work_id": legacy_bind_work_id,
            "runtime": "codex",
            "family": "gram_posdef_linear_independent_planner",
            "source_binding_ingest_status": "rejected_binding_artifact",
            "source_search_integration_receipt": receipt_path,
            "artifact_paths": [receipt_path],
        }, max_attempts=1)
        recovery = recover_rejected_bindings(argparse.Namespace(
            queue_db=db,
            events=events,
            worker_id="self-test",
            out_dir=str(root / "out"),
            min_canary_ready=1,
            max_source_candidates=3,
            canary_packets=str(packets),
            family_spec_dir=str(root / "repair_families"),
            corpus=str(corpus),
            extra_corpus=[],
            residual_plan="residual.json",
            static_filter="static.json",
            binding_mode="deterministic",
            deterministic_binding_max_rows=3,
            deterministic_binding_candidates_per_row=2,
            agent_runtime="codex",
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            priority=120,
            max_attempts=1,
            retry_held_target_holds=False,
            max_recover=10,
        ))
        assert recovery["recovered_count"] == 1
        recovered_work_id = recovery["recovered"][0]["recovery_work_id"]
        work_queue.update_status(cx, work_id=recovered_work_id, status="done", payload_update={
            "source_binding_ingest_status": "rejected_binding_artifact",
        })
        second_recovery = recover_rejected_bindings(argparse.Namespace(
            queue_db=db,
            events=events,
            worker_id="self-test",
            out_dir=str(root / "out"),
            min_canary_ready=1,
            max_source_candidates=3,
            canary_packets=str(packets),
            family_spec_dir=str(root / "repair_families"),
            corpus=str(corpus),
            extra_corpus=[],
            residual_plan="residual.json",
            static_filter="static.json",
            binding_mode="deterministic",
            deterministic_binding_max_rows=3,
            deterministic_binding_candidates_per_row=2,
            agent_runtime="codex",
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            priority=120,
            max_attempts=1,
            retry_held_target_holds=False,
            max_recover=10,
        ))
        assert second_recovery["recovered_count"] == 0
        ok, quality = _queries_pass_gate(
            ["Matrix.PosDef.gram", "LinearIndependent.gram_matrix"],
            "gram_posdef_linear_independent_planner",
        )
        assert ok and quality[0]["query_kind"] == "declaration_ref"
    print("leanmill_source_search_integrator self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="source-search-integrator-local")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--min-canary-ready", type=int, default=1)
    ap.add_argument("--max-source-candidates", type=int, default=12)
    ap.add_argument("--canary-packets", default=DEFAULT_CANARY_PACKETS)
    ap.add_argument("--family-spec-dir", default=DEFAULT_REPAIR_FAMILY_SPEC_DIR)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--extra-corpus", action="append", default=list(DEFAULT_EXTRA_CORPORA))
    ap.add_argument("--residual-plan", default=DEFAULT_RESIDUAL_PLAN)
    ap.add_argument("--static-filter", default=DEFAULT_STATIC_FILTER)
    ap.add_argument("--binding-mode", choices=["deterministic", "agent"], default="deterministic")
    ap.add_argument("--deterministic-binding-max-rows", type=int, default=3)
    ap.add_argument("--deterministic-binding-candidates-per-row", type=int, default=2)
    ap.add_argument("--agent-runtime", choices=["codex", "claude"], default="codex")
    ap.add_argument("--agent-max-iterations", type=int, default=3)
    ap.add_argument("--agent-max-wall-time-s", type=int, default=1200)
    ap.add_argument("--priority", type=int, default=120)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--max-attempts", type=int, default=1)
    ap.add_argument("--retry-held-target-holds", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--idle-sleep-s", type=int, default=15)
    ap.add_argument("--max-tasks", type=int, default=0)
    ap.add_argument("--max-idle-ticks", type=int, default=0)
    ap.add_argument("--retire-low-quality-bindings", action="store_true")
    ap.add_argument("--recover-rejected-bindings", action="store_true")
    ap.add_argument("--max-recover", type=int, default=20)
    ap.add_argument("--recovery-status-out", default="")
    ap.add_argument("--max-retire-scan", type=int, default=100)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    apply_profile_section(args, section="source_search_integrator")
    if int(args.priority) == 120:
        args.priority = _queue_priority(args, "source_search_integrator_followup", 120)
    if args.retire_low_quality_bindings:
        print(json.dumps(retire_low_quality_bindings(args), sort_keys=True))
        return 0
    if args.recover_rejected_bindings:
        result = recover_rejected_bindings(args)
        if args.recovery_status_out:
            _write_json(Path(args.recovery_status_out), result)
        print(json.dumps({
            "schema": result["schema"],
            "recovered_count": result["recovered_count"],
            "skipped_count": result["skipped_count"],
            "recovery_status_out": args.recovery_status_out,
        }, sort_keys=True))
        return 0
    if args.daemon:
        print(json.dumps(daemon_loop(args), sort_keys=True))
        return 0
    result = work_once(args)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
