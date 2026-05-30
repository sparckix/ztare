#!/usr/bin/env python3
"""Convert source-to-canary binding artifacts into guarded probe WorkItems."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, priority_value
from leanmill_source_search_integrator import _binding_task_query_quality, _row_records, _sha_file


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_OUT_DIR = f"{DEFAULT_DATA_DIR}/queued_learning_work"
DEFAULT_ROOT_BASE = "/tmp/rung1/leanmill_24x7_learning"
DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_ALLOCATOR = f"{DEFAULT_DATA_DIR}/source_family_allocator.json"
DEFAULT_EXPAND100_CORPUS = f"{DEFAULT_DATA_DIR}/mcb_expand100_active_corpus.json"
DEFAULT_EXTRA_CORPORA = [
    "/tmp/rung1/mcb_refill_dedup_after_expand100/mcb_corpus.json",
    DEFAULT_EXPAND100_CORPUS,
    "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_QUEUE.json",
]
VALID_BINDING_SCHEMAS = {"leanmill-source-to-canary-binding-v1", "leanmill-source-to-canary-hold-v1"}
NO_PROBE_DECISIONS = {"operator_required", "retired"}
UNVERIFIED_VALUE_DECISIONS = {"exact_gap_candidate", "valid_falsifier"}
SOURCE_BINDING_BLOCK_ACTIONS = {
    "do_not_spend_until_new_evidence",
    "hold_source_binding_until_new_target_evidence",
    "repair_source_strategy_before_more_binding",
}


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


def _bounded_slug(value: str, *, max_prefix: int = 64, hash_len: int = 12) -> str:
    slug = _slug(value)
    digest = hashlib.sha256(value.encode()).hexdigest()[:hash_len]
    if len(slug) <= max_prefix:
        return f"{slug}_{digest}"
    return f"{slug[:max_prefix].rstrip('_')}_{digest}"


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


def _allocator_record(path: str | Path | None, family: str) -> dict[str, Any]:
    obj = _read_json(path)
    if not isinstance(obj, dict):
        return {}
    for rec in obj.get("allocations") or []:
        if not isinstance(rec, dict):
            continue
        if str(rec.get("family") or "") == family:
            return rec
    return {}


def _allocator_blocks_source_binding(path: str | Path | None, family: str) -> tuple[bool, str, dict[str, Any]]:
    if not family:
        return False, "", {}
    rec = _allocator_record(path, family)
    action = str(rec.get("recommended_action") or "")
    return action in SOURCE_BINDING_BLOCK_ACTIONS, action, rec


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _candidate_binding_rows(cx: sqlite3.Connection, limit: int, *, include_rejected: bool = False) -> list[dict[str, Any]]:
    ingested_predicate = (
        "(payload_json NOT LIKE '%source_binding_ingested_at_epoch%' "
        "OR payload_json LIKE '%\"source_binding_ingest_status\":\"rejected_binding_artifact\"%' "
        "OR payload_json LIKE '%\"source_binding_ingest_status\": \"rejected_binding_artifact\"%')"
        if include_rejected
        else "payload_json NOT LIKE '%source_binding_ingested_at_epoch%'"
    )
    rows = cx.execute(
        f"""
        SELECT *
        FROM work_items
        WHERE kind='source_scout_task'
          AND status IN ('done', 'failed')
          AND payload_json LIKE '%source_search_integration_receipt%'
          AND {ingested_predicate}
        ORDER BY updated_at ASC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    return [work_queue.row_to_dict(row) for row in rows]


def _read_text(path: str, limit: int = 50000) -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    text = p.read_text(errors="ignore")
    return text[-limit:] if len(text) > limit else text


def _artifact_paths_from_transcript(text: str) -> list[str]:
    paths: list[str] = []
    for match in re.finditer(r"(?P<path>(?:/[^ \t\r\n)\]]+|analytics/public/leanmill[^ \t\r\n)\]]+)\.json)", text):
        path = match.group("path").rstrip(".,;:")
        if path not in paths:
            paths.append(path)
    return paths


def _binding_artifact(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    payload = item.get("payload") or {}
    for path in payload.get("artifact_paths") or []:
        obj = _read_json(path)
        if isinstance(obj, dict) and str(obj.get("schema") or "") in VALID_BINDING_SCHEMAS:
            return str(path), obj
    for path in _artifact_paths_from_transcript(_read_text(str(payload.get("output_path") or ""))):
        obj = _read_json(path)
        if isinstance(obj, dict) and str(obj.get("schema") or "") in VALID_BINDING_SCHEMAS:
            return path, obj
    return "", {}


def _validate_binding(obj: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    schema = str(obj.get("schema") or "")
    decision = str(obj.get("decision") or "")
    if schema not in VALID_BINDING_SCHEMAS:
        failures.append("missing_or_invalid_schema")
    if decision in NO_PROBE_DECISIONS:
        if not str(obj.get("family") or ""):
            failures.append("missing_family")
        return failures
    if decision in UNVERIFIED_VALUE_DECISIONS:
        failures.append(f"agent_claimed_{decision}_requires_probe_or_governance")
        return failures
    if decision != "canary_spec":
        failures.append("decision_not_canary_spec")
    if not str(obj.get("family") or ""):
        failures.append("missing_family")
    attempts = _binding_attempts(obj)
    if not isinstance(attempts, list) or not attempts:
        failures.append("missing_positive_source_to_canary_attempts")
        return failures
    for idx, attempt in enumerate(attempts):
        prefix = f"attempt_{idx}"
        if not str((attempt or {}).get("target_row_id") or ""):
            failures.append(f"{prefix}_missing_target_row_id")
        names = (attempt or {}).get("candidate_names") or []
        if not isinstance(names, list) or not [n for n in names if str(n or "")]:
            failures.append(f"{prefix}_missing_candidate_names")
        if not str((attempt or {}).get("matched_negative_control") or ""):
            failures.append(f"{prefix}_missing_matched_negative_control")
    return failures


def _receipt_for_item(payload: dict[str, Any]) -> dict[str, Any]:
    obj = _read_json(str(payload.get("source_search_integration_receipt") or ""))
    return obj if isinstance(obj, dict) else {}


def _allowed_candidate_names(receipt: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for candidate in receipt.get("top_source_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        if not bool(candidate.get("usable_for_canary_source")) or not bool(candidate.get("name_resolves")):
            continue
        name = str(candidate.get("candidate_name") or "")
        if name:
            out.add(name)
    return out


def _allowed_target_row_ids(receipt: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in receipt.get("allowed_binding_target_rows") or []:
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("row_id") or row.get("id") or "")
        if row_id:
            out.add(row_id)
    return out


def _candidate_names(binding: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for attempt in _binding_attempts(binding):
        for name in attempt.get("candidate_names") or []:
            value = str(name or "")
            if value:
                names.add(value)
    return names


def _normalize_candidate_names_to_receipt(binding: dict[str, Any], receipt: dict[str, Any]) -> list[str]:
    """Drop candidate names that were not emitted by the source-search receipt."""
    if str(binding.get("decision") or "") != "canary_spec":
        return []
    allowed = _allowed_candidate_names(receipt)
    if not allowed:
        return []
    removed: list[str] = []
    for attempt in _binding_attempts(binding):
        raw_names = [str(name or "") for name in (attempt.get("candidate_names") or []) if str(name or "")]
        kept: list[str] = []
        for name in raw_names:
            if name in allowed:
                if name not in kept:
                    kept.append(name)
            else:
                removed.append(name)
        if raw_names != kept:
            attempt["candidate_names"] = kept
    if removed:
        binding.setdefault("normalization", {})
        binding["normalization"]["removed_candidate_names_not_in_source_receipt"] = sorted(set(removed))
        binding["normalization"]["candidate_name_rule"] = "Only source-search receipt candidates are passed to Proof Execution."
    return sorted(set(removed))


def _binding_identity_failures(item: dict[str, Any], binding: dict[str, Any], receipt: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    payload = item.get("payload") or {}
    family = str(payload.get("family") or "")
    if str(binding.get("family") or "") and family and str(binding.get("family")) != family:
        failures.append("binding_family_mismatch")
    parent = str(binding.get("parent_work_id") or "")
    if parent and parent != item["work_id"]:
        failures.append("binding_parent_work_id_mismatch")
    receipt_path = str(payload.get("source_search_integration_receipt") or "")
    embedded_receipt = str(binding.get("source_search_integration_receipt") or "")
    if embedded_receipt and embedded_receipt != receipt_path:
        failures.append("binding_receipt_mismatch")
    allowed = _allowed_candidate_names(receipt)
    if str(binding.get("decision") or "") == "canary_spec":
        allowed_rows = _allowed_target_row_ids(receipt)
        if allowed_rows:
            for row_id in sorted(_binding_target_row_ids(binding) - allowed_rows):
                failures.append(f"target_row_not_in_source_receipt:{row_id}")
        if not allowed:
            failures.append("source_receipt_has_no_allowed_candidates")
        else:
            for name in sorted(_candidate_names(binding) - allowed):
                failures.append(f"candidate_not_in_source_receipt:{name}")
    return failures


def _corpus_row_ids(path: str | Path) -> set[str]:
    obj = _read_json(path)
    rows = _row_records(obj)
    if not isinstance(rows, list):
        return set()
    row_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ("row_id", "id"):
            value = str(row.get(key) or "")
            if value:
                row_ids.add(value)
    return row_ids


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or "")


def _row_match_keys(row: dict[str, Any]) -> list[str]:
    raw: list[str] = []
    row_id = _row_id(row)
    raw.append(row_id)
    if row_id.startswith("MCB_"):
        parts = row_id.split("_", 2)
        if len(parts) == 3:
            raw.append(parts[2])
    for key in ("theorem", "metadata_theorem", "target_name", "source_hinge"):
        raw.append(str(row.get(key) or ""))
    out: list[str] = []
    for item in raw:
        key = re.sub(r"[^A-Za-z0-9_.]+", "_", str(item)).strip("_")
        if key and key not in out:
            out.append(key)
    return out


def _corpus_rows(path: str | Path) -> list[dict[str, Any]]:
    obj = _read_json(path)
    rows = _row_records(obj)
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and _row_id(row)]


def _row_has_executable_surface(row: dict[str, Any]) -> bool:
    return bool(str(row.get("sorried_file") or ""))


def _prefer_executable_row(existing: dict[str, Any] | None, candidate: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        return candidate
    if _row_has_executable_surface(existing):
        return existing
    if not _row_has_executable_surface(candidate):
        return existing
    merged = dict(existing)
    merged.update(candidate)
    return merged


def _executable_alias_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not _row_has_executable_surface(row):
            continue
        for key in _row_match_keys(row):
            candidates.setdefault(key, []).append(row)
    out: dict[str, dict[str, Any]] = {}
    for key, vals in candidates.items():
        unique = {_row_id(row): row for row in vals if _row_id(row)}
        if len(unique) == 1:
            out[key] = next(iter(unique.values()))
    return out


def _receipt_corpus_paths(receipt: dict[str, Any], fallback_path: str) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    for meta in receipt.get("active_corpora") or []:
        if not isinstance(meta, dict):
            continue
        path = str(meta.get("path") or "")
        if path:
            paths.append((path, str(meta.get("sha256") or "")))
    if paths:
        return paths
    active = receipt.get("active_corpus") or {}
    path = str(active.get("path") or fallback_path)
    return [(path, str(active.get("sha256") or ""))]


def _fallback_corpus_paths(args: argparse.Namespace) -> list[str]:
    out: list[str] = []
    for path in [str(args.corpus or ""), *[str(p or "") for p in (getattr(args, "extra_corpus", None) or [])]]:
        if path and path not in out:
            out.append(path)
    return out


def _effective_receipt_corpus_paths(receipt: dict[str, Any], args: argparse.Namespace) -> list[tuple[str, str]]:
    paths = _receipt_corpus_paths(receipt, args.corpus)
    seen = {path for path, _ in paths}
    for path in _fallback_corpus_paths(args):
        if path not in seen:
            paths.append((path, ""))
            seen.add(path)
    return paths


def _receipt_corpus_row_ids(receipt: dict[str, Any], args: argparse.Namespace) -> tuple[set[str], list[str]]:
    row_ids: set[str] = set()
    skipped: list[str] = []
    for path, expected_sha in _effective_receipt_corpus_paths(receipt, args):
        if expected_sha and _sha_file(path) != expected_sha:
            skipped.append(f"active_corpus_sha_mismatch:{path}")
            continue
        row_ids.update(_corpus_row_ids(path))
    if not row_ids:
        return row_ids, skipped + ["corpus_rows_unreadable"]
    return row_ids, []


def _build_probe_corpus(binding: dict[str, Any], receipt: dict[str, Any], args: argparse.Namespace, out_path: Path) -> tuple[str, dict[str, Any], list[str]]:
    wanted = _binding_target_row_ids(binding)
    failures: list[str] = []
    rows_by_id: dict[str, dict[str, Any]] = {}
    all_rows: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    for path, expected_sha in _effective_receipt_corpus_paths(receipt, args):
        actual_sha = _sha_file(path)
        inputs.append({"path": path, "sha256": actual_sha, "expected_sha256": expected_sha})
        if expected_sha and actual_sha != expected_sha:
            continue
        for row in _corpus_rows(path):
            all_rows.append(row)
            row_id = _row_id(row)
            rows_by_id[row_id] = _prefer_executable_row(rows_by_id.get(row_id), row)
    missing = sorted(row_id for row_id in wanted if row_id not in rows_by_id)
    failures.extend(f"target_row_not_in_probe_corpus:{row_id}" for row_id in missing)
    selected = [rows_by_id[row_id] for row_id in sorted(wanted) if row_id in rows_by_id]
    aliases = _executable_alias_index(all_rows)
    for idx, row in enumerate(selected):
        if _row_has_executable_surface(row):
            continue
        matched = next((aliases[key] for key in _row_match_keys(row) if key in aliases), None)
        if matched is not None:
            repaired = dict(row)
            repaired.update(matched)
            repaired.update({k: v for k, v in row.items() if k not in {"sorried_file", "target_line", "goal"}})
            repaired["hydrated_from_executable_row_id"] = _row_id(matched)
            selected[idx] = repaired
    for row in selected:
        if not _row_has_executable_surface(row):
            failures.append(f"target_row_missing_sorried_file:{_row_id(row)}")
    if failures:
        return "", {"inputs": inputs, "selected_row_count": len(selected), "target_row_ids": sorted(wanted)}, failures
    if len(inputs) == 1 and selected and len(selected) == len(_corpus_rows(inputs[0]["path"])):
        return inputs[0]["path"], {"inputs": inputs, "selected_row_count": len(selected), "target_row_ids": sorted(wanted)}, []
    obj = {
        "schema": "leanmill-source-binding-probe-corpus-v1",
        "created_at_epoch": _now(),
        "family": binding.get("family"),
        "source_search_integration_receipt": binding.get("source_search_integration_receipt"),
        "source_corpora": inputs,
        "target_row_ids": sorted(wanted),
        "rows": selected,
    }
    _write_json(out_path, obj)
    return str(out_path), {"inputs": inputs, "selected_row_count": len(selected), "target_row_ids": sorted(wanted)}, []


def _binding_target_row_ids(binding: dict[str, Any]) -> set[str]:
    row_ids = {str(row_id) for row_id in binding.get("concrete_target_row_ids") or [] if str(row_id or "")}
    for attempt in _binding_attempts(binding):
        row_id = str((attempt or {}).get("target_row_id") or "")
        if row_id:
            row_ids.add(row_id)
    return row_ids


def _binding_attempts(binding: dict[str, Any]) -> list[dict[str, Any]]:
    attempts = binding.get("positive_source_to_canary_attempts")
    if isinstance(attempts, list) and attempts:
        return [a for a in attempts if isinstance(a, dict)]
    out: list[dict[str, Any]] = []
    for target in binding.get("concrete_targets") or []:
        if not isinstance(target, dict) or str(target.get("binding_status") or "positive") != "positive":
            continue
        neg = target.get("matched_negative_control")
        if isinstance(neg, dict):
            neg_reason = str(neg.get("control_shape") or neg.get("candidate_name") or neg.get("row_id") or "")
        else:
            neg_reason = str(neg or "")
        out.append({
            "target_row_id": str(target.get("row_id") or ""),
            "candidate_names": target.get("candidate_names") or [],
            "action_family": str(target.get("action_family") or "apply_easy"),
            "attempt_shape": str(target.get("target_context_risk") or target.get("source_order_risk") or ""),
            "matched_negative_control": neg_reason,
        })
    return out


def _build_static_filter(binding: dict[str, Any], path: Path, max_candidates_per_attempt: int) -> dict[str, Any]:
    rows_by_id: dict[str, list[dict[str, Any]]] = {}
    for attempt in _binding_attempts(binding):
        row_id = str(attempt.get("target_row_id") or "")
        if not row_id:
            continue
        for name in [str(n) for n in (attempt.get("candidate_names") or []) if str(n or "")][: max(1, max_candidates_per_attempt)]:
            rows_by_id.setdefault(row_id, []).append({
                "name": name,
                "kind": "theorem",
                "name_resolves": True,
                "source_safety_status": "source_binding_agent_candidate",
                "source_order_status": "source_binding_requires_governance",
                "usable_for_canary_source": True,
            })
    rows = [
        {
            "row_id": row_id,
            "canary_ready_count": len(candidates),
            "canary_ready_candidates": candidates,
            "recommended_next_step": "guarded_source_binding_canary_replay",
        }
        for row_id, candidates in sorted(rows_by_id.items())
    ]
    obj = {
        "schema": "leanmill-source-binding-static-filter-v1",
        "family": binding.get("family"),
        "row_count": len(rows),
        "canary_ready_total": sum(len(r["canary_ready_candidates"]) for r in rows),
        "rows": rows,
        "source_policy": {
            "proof_bodies_consumed": False,
            "source_binding_has_no_proof_credit": True,
            "governance_gate_required_before_any_closure_credit": True,
        },
    }
    _write_json(path, obj)
    return obj


def _build_probe_packet(binding: dict[str, Any], *, static_filter: str, path: Path, max_candidates_per_attempt: int) -> dict[str, Any]:
    family = str(binding.get("family") or "unknown_family")
    tests: list[dict[str, Any]] = []
    for attempt in _binding_attempts(binding):
        row_id = str(attempt.get("target_row_id") or "")
        action_family = "apply_easy"
        for name in [str(n) for n in (attempt.get("candidate_names") or []) if str(n or "")][: max(1, max_candidates_per_attempt)]:
            nonce = hashlib.sha256(f"{family}:{row_id}:{name}:{static_filter}".encode()).hexdigest()[:10]
            positive_id = f"{family}:{row_id}:{name}:source_binding_positive"
            negative_id = f"{family}:{row_id}:{name}:source_binding_negative"
            tests.append({
                "packet_id": positive_id,
                "repair_family": family,
                "row_id": row_id,
                "candidate_name": name,
                "action_family": action_family,
                "backend": "repl_step",
                "score_candidates": True,
                "require_positive_source_action": True,
                "test_kind": "positive",
                "expected_outcome": "direct_source_action_or_template_step_residual",
                "source_credit_eligible": False,
                "clean_solver_credit_eligible": False,
                "credit_type": "repair_canary_probe",
                "static_filter": static_filter,
                "source_action_preflight_required": True,
                "binding_attempt_shape": attempt.get("attempt_shape"),
            })
            tests.append({
                "packet_id": negative_id,
                "repair_family": family,
                "row_id": row_id,
                "candidate_name": f"LeanMill.NegativeControl.{_slug(family)}.{_slug(row_id)}.{nonce}",
                "action_family": action_family,
                "test_kind": "negative_control",
                "expected_outcome": "expected_failure",
                "source_credit_eligible": False,
                "clean_solver_credit_eligible": False,
                "credit_type": "negative_control",
                "static_filter": static_filter,
                "negative_control_reason": str(attempt.get("matched_negative_control") or "unresolved sentinel must fail"),
            })
    packet = {
        "schema": "leanmill-concrete-learning-probe-packet-v1",
        "source_binding_schema": binding.get("schema"),
        "repair_family": family,
        "science_rule": "Source binding emits probe work only; value credit requires Governance Gate receipts and matched negative controls.",
        "credit_boundary": {
            "source_credit_eligible": False,
            "clean_solver_credit_eligible": False,
            "proof_credit_authority": "governance_gate",
            "worker_can_self_ratify": False,
        },
        "exit_contract": {
            "schema": "leanmill-probe-exit-contract-v1",
            "proof_credit_authority": "governance_gate",
            "unexpected_negative_control_pass_blocks_credit": True,
            "pair_count": len([t for t in tests if t["test_kind"] == "positive"]),
        },
        "packets": [{
            "repair_family": family,
            "selected_rows": [{"row_id": row_id} for row_id in sorted(_binding_target_row_ids(binding))],
            "tests": tests,
        }],
    }
    _write_json(path, packet)
    return packet


def ingest_one(args: argparse.Namespace, item: dict[str, Any]) -> dict[str, Any]:
    payload = item.get("payload") or {}
    receipt = _receipt_for_item(payload)
    quality_ok, quality = _binding_task_query_quality(payload)
    cx = work_queue.connect(args.queue_db)
    if not quality_ok:
        update = {
            "source_binding_ingested_at_epoch": _now(),
            "source_binding_ingest_status": "retired_low_quality_source_query",
            "exit_kind": "retired_low_quality_source_query",
            "query_quality": quality,
        }
        work_queue.update_status(cx, work_id=item["work_id"], status=item.get("status") or "done", payload_update=update)
        return {"ok": True, "work_id": item["work_id"], "status": "retired_low_quality_source_query"}
    artifact_path, binding = _binding_artifact(item)
    removed_candidate_names = _normalize_candidate_names_to_receipt(binding, receipt)
    failures = _validate_binding(binding)
    failures.extend(_binding_identity_failures(item, binding, receipt))
    binding_rows = _binding_target_row_ids(binding)
    if binding_rows:
        corpus_row_ids, corpus_failures = _receipt_corpus_row_ids(receipt, args)
        failures.extend(corpus_failures)
        if corpus_row_ids:
            missing_target_rows = sorted(binding_rows - corpus_row_ids)
            failures.extend(f"target_row_not_in_corpus:{row_id}" for row_id in missing_target_rows)
    if failures:
        update = {
            "source_binding_ingested_at_epoch": _now(),
            "source_binding_ingest_status": "rejected_binding_artifact",
            "source_binding_failures": failures,
            "source_binding_removed_candidate_names": removed_candidate_names,
            "source_binding_artifact_path": artifact_path,
        }
        work_queue.update_status(cx, work_id=item["work_id"], status=item.get("status") or "done", payload_update=update)
        work_queue.append_event(args.events, {
            "event_type": "source_binding_ingest_rejected",
            "work_id": item["work_id"],
            "payload": {"family": payload.get("family"), "failures": failures},
            "artifact_paths": [artifact_path] if artifact_path else [],
        })
        return {"ok": False, "work_id": item["work_id"], "status": "rejected", "failures": failures}
    decision = str(binding.get("decision") or "")
    if decision in NO_PROBE_DECISIONS:
        update = {
            "source_binding_ingested_at_epoch": _now(),
            "source_binding_ingest_status": f"{decision}_no_probe",
            "source_binding_artifact_path": artifact_path,
            "exit_kind": decision,
            "source_binding_decision": decision,
            "source_binding_removed_candidate_names": removed_candidate_names,
        }
        work_queue.update_status(cx, work_id=item["work_id"], status=item.get("status") or "done", payload_update=update)
        work_queue.append_event(args.events, {
            "event_type": "source_binding_ingest_terminal_no_probe",
            "work_id": item["work_id"],
            "payload": {"family": binding.get("family") or payload.get("family"), "decision": decision},
            "artifact_paths": [artifact_path] if artifact_path else [],
        })
        return {"ok": True, "work_id": item["work_id"], "status": f"{decision}_no_probe"}
    family = str(binding.get("family") or payload.get("family") or "unknown_family")
    allocator_blocks, allocator_action, allocator_rec = _allocator_blocks_source_binding(args.allocator, family)
    if allocator_blocks:
        update = {
            "source_binding_ingested_at_epoch": _now(),
            "source_binding_ingest_status": "retired_allocator_held_source_binding",
            "exit_kind": "retired_source_strategy_repair_required",
            "retire_reason": "source_family_allocator_blocks_source_binding_probe",
            "allocator_action": allocator_action,
            "source_binding_artifact_path": artifact_path,
            "source_binding_removed_candidate_names": removed_candidate_names,
        }
        work_queue.update_status(cx, work_id=item["work_id"], status=item.get("status") or "done", payload_update=update)
        work_queue.append_event(args.events, {
            "event_type": "source_binding_retired_allocator_held",
            "work_id": item["work_id"],
            "payload": {
                "family": family,
                "allocator_action": allocator_action,
                "allocator_status": allocator_rec.get("status"),
                "source_binding_conversion_rate": (allocator_rec.get("source_quality") or {}).get("source_binding_conversion_rate"),
                "reason": "allocator blocked direct source-bound proof probe",
            },
            "artifact_paths": [artifact_path] if artifact_path else [],
        })
        return {
            "ok": True,
            "work_id": item["work_id"],
            "status": "retired_allocator_held_source_binding",
            "allocator_action": allocator_action,
        }
    parent_key = _bounded_slug(str(item["work_id"]), max_prefix=48, hash_len=12)
    family_key = _bounded_slug(family, max_prefix=48, hash_len=8)
    run_id = f"{int(time.time())}_{parent_key}_{uuid.uuid4().hex[:8]}"
    out_dir = Path(args.out_dir)
    static_path = out_dir / f"source_binding_static_filter_{family_key}_{run_id}.json"
    packet_path = out_dir / f"source_binding_probe_packet_{family_key}_{run_id}.json"
    corpus_path = out_dir / f"source_binding_probe_corpus_{family_key}_{run_id}.json"
    root = Path(args.root_base) / f"source_binding_probe_{family_key}_{run_id}"
    static_obj = _build_static_filter(binding, static_path, args.max_candidates_per_attempt)
    packet_obj = _build_probe_packet(binding, static_filter=str(static_path), path=packet_path, max_candidates_per_attempt=args.max_candidates_per_attempt)
    probe_corpus, probe_corpus_meta, probe_corpus_failures = _build_probe_corpus(binding, receipt, args, corpus_path)
    if probe_corpus_failures:
        update = {
            "source_binding_ingested_at_epoch": _now(),
            "source_binding_ingest_status": "rejected_probe_corpus",
            "source_binding_failures": probe_corpus_failures,
            "source_binding_artifact_path": artifact_path,
            "source_binding_probe_corpus_meta": probe_corpus_meta,
            "source_binding_removed_candidate_names": removed_candidate_names,
        }
        work_queue.update_status(cx, work_id=item["work_id"], status=item.get("status") or "done", payload_update=update)
        work_queue.append_event(args.events, {
            "event_type": "source_binding_probe_corpus_rejected",
            "work_id": item["work_id"],
            "payload": {"family": family, "failures": probe_corpus_failures, "probe_corpus_meta": probe_corpus_meta},
            "artifact_paths": [artifact_path, str(static_path), str(packet_path)] if artifact_path else [str(static_path), str(packet_path)],
        })
        return {"ok": False, "work_id": item["work_id"], "status": "rejected_probe_corpus", "failures": probe_corpus_failures}
    test_count = sum(len(packet.get("tests") or []) for packet in packet_obj.get("packets") or [])
    probe_work_id = f"probe:source_binding:{_slug(family)}:{_slug(item['work_id'])}"
    probe_payload = {
        "work_id": probe_work_id,
        "family": family,
        "station": "proof_execution",
        "probe_lane": "source_binding",
        "packet": str(packet_path),
        "root": str(root),
        "corpus": probe_corpus,
        "source_binding_active_corpora": receipt.get("active_corpora") or [receipt.get("active_corpus") or {}],
        "source_binding_probe_corpus_meta": probe_corpus_meta,
        "static_filter": str(static_path),
        "scoreboard": str(root / "scoreboard.json"),
        "limit": min(args.max_tests_per_probe, test_count),
        "max_candidates": 1,
        "max_actions": 1,
        "timeout": args.probe_timeout_s,
        "test_wall_timeout": args.probe_wall_timeout_s,
        "backend": args.backend,
        "warm_repl_inline": bool(args.warm_repl_inline),
        "govern_winners": bool(args.govern_winners),
        "credit_boundary": packet_obj["credit_boundary"],
        "expected_exit": "ratified_closure_or_typed_residual_or_expected_negative_control_failure",
        "source_binding_parent_work_id": item["work_id"],
        "source_binding_removed_candidate_names": removed_candidate_names,
    }
    before = cx.total_changes
    work_queue.enqueue(cx, kind="repair_canary_probe", priority=args.priority, payload=probe_payload, max_attempts=args.max_attempts)
    enqueued = cx.total_changes > before
    update = {
        "source_binding_ingested_at_epoch": _now(),
        "source_binding_ingest_status": "probe_enqueued" if enqueued else "probe_already_present",
        "source_binding_artifact_path": artifact_path,
        "source_binding_removed_candidate_names": removed_candidate_names,
        "source_binding_static_filter": str(static_path),
        "source_binding_probe_packet": str(packet_path),
        "source_binding_probe_corpus": probe_corpus,
        "source_binding_probe_work_id": probe_work_id,
    }
    work_queue.update_status(cx, work_id=item["work_id"], status=item.get("status") or "done", payload_update=update)
    work_queue.append_event(args.events, {
        "event_type": "source_binding_probe_enqueued" if enqueued else "source_binding_probe_already_present",
        "work_id": probe_work_id,
        "payload": {
            "family": family,
            "parent_work_id": item["work_id"],
            "test_count": test_count,
            "static_canary_ready_total": static_obj.get("canary_ready_total"),
        },
        "artifact_paths": [artifact_path, str(static_path), str(packet_path), probe_corpus],
    })
    return {"ok": True, "work_id": item["work_id"], "probe_work_id": probe_work_id, "probe_enqueued": enqueued}


def ingest(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    rows = _candidate_binding_rows(cx, args.scan_limit, include_rejected=bool(args.include_rejected))
    results = []
    for item in rows[: max(0, args.max_ingest)]:
        results.append(ingest_one(args, item))
    payload = {
        "schema": "leanmill-source-binding-ingestion-status-v1",
        "generated_at_epoch": _now(),
        "inspected": len(results),
        "probe_enqueued": sum(1 for r in results if r.get("probe_enqueued")),
        "rejected": sum(1 for r in results if r.get("status") == "rejected"),
        "retired_allocator_held": sum(1 for r in results if r.get("status") == "retired_allocator_held_source_binding"),
        "terminal_no_probe": sum(1 for r in results if str(r.get("status") or "").endswith("_no_probe")),
        "results": results,
    }
    if args.out:
        _write_json(Path(args.out), payload)
    return payload


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_source_binding_ingester_") as td:
        root = Path(td)
        db = str(root / "q.sqlite")
        events = str(root / "events.jsonl")
        binding = root / "binding.json"
        binding.write_text(json.dumps({
            "schema": "leanmill-source-to-canary-binding-v1",
            "family": "fam",
            "decision": "canary_spec",
            "concrete_target_row_ids": ["MCB_X"],
            "positive_source_to_canary_attempts": [{
                "target_row_id": "MCB_X",
                "candidate_names": ["A.good", "A.plausible_but_not_receipt_backed"],
                "matched_negative_control": "omit source",
                "attempt_shape": "apply source",
            }],
        }) + "\n")
        transcript = root / "agent.txt"
        transcript.write_text(f"Candidate packet path: {binding}\n")
        (root / "corpus.json").write_text(json.dumps({"rows": [{"id": "MCB_OTHER"}]}) + "\n")
        (root / "extra_corpus.json").write_text(json.dumps({"source_discovery_queue": [{
            "id": "MCB_X",
            "goal": "Matrix gram PosDef LinearIndependent",
            "sorried_file": str(root / "Dummy.lean"),
            "target_line": 1,
        }]}) + "\n")
        (root / "metadata_corpus.json").write_text(json.dumps({"rows": [{
            "id": "MCB_X",
            "goal": "metadata only row",
            "source_file": "Mathlib/LinearAlgebra/Matrix/PosDef.lean",
        }]}) + "\n")
        receipt = root / "receipt.json"
        receipt.write_text(json.dumps({
            "family": "fam",
            "queries": ["Matrix gram PosDef LinearIndependent"],
            "allowed_binding_target_rows": [{"row_id": "MCB_X"}],
            "top_source_candidates": [{
                "candidate_name": "A.good",
                "usable_for_canary_source": True,
                "name_resolves": True,
            }],
            "active_corpus": {"path": str(root / "corpus.json"), "sha256": _sha_file(root / "corpus.json")},
            "active_corpora": [
                {"path": str(root / "stale_missing.json"), "sha256": "0" * 64, "row_count": 1},
                {"path": str(root / "metadata_corpus.json"), "sha256": _sha_file(root / "metadata_corpus.json"), "row_count": 1},
                {"path": str(root / "corpus.json"), "sha256": _sha_file(root / "corpus.json"), "row_count": 1},
                {"path": str(root / "extra_corpus.json"), "sha256": _sha_file(root / "extra_corpus.json"), "row_count": 1},
            ],
        }) + "\n")
        cx = work_queue.connect(db)
        long_parent_work_id = "source_bind:fam:" + ("very_long_parent_segment_" * 12)
        wid = work_queue.enqueue(cx, kind="source_scout_task", priority=1, payload={
            "work_id": long_parent_work_id,
            "family": "fam",
            "source_search_integration_receipt": str(receipt),
            "output_path": str(transcript),
        })
        work_queue.update_status(cx, work_id=wid, status="done")
        result = ingest(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(root / "status.json"),
            scan_limit=10,
            max_ingest=10,
            out_dir=str(root / "out"),
            root_base=str(root / "runs"),
            corpus=str(root / "corpus.json"),
            max_candidates_per_attempt=1,
            max_tests_per_probe=4,
            probe_timeout_s=120,
            probe_wall_timeout_s=180,
            backend="repl_file",
            warm_repl_inline=False,
            govern_winners=False,
            priority=150,
            max_attempts=1,
            extra_corpus=[str(root / "extra_corpus.json")],
            include_rejected=False,
            allocator=str(root / "missing_allocator.json"),
        ))
        assert result["probe_enqueued"] == 1
        probe = cx.execute("SELECT payload_json FROM work_items WHERE kind='repair_canary_probe'").fetchone()
        assert probe is not None
        probe_payload = json.loads(probe["payload_json"])
        assert str(probe_payload.get("corpus") or "").endswith(".json")
        assert Path(str(probe_payload["corpus"])).exists()
        packet = json.loads(Path(probe_payload["packet"]).read_text())
        positive = next(t for t in packet["packets"][0]["tests"] if t["test_kind"] == "positive")
        assert positive["candidate_name"] == "A.good"
        assert positive["backend"] == "repl_step"
        assert positive["score_candidates"] is True
        assert positive["require_positive_source_action"] is True
        for generated in (root / "out").glob("*.json"):
            assert len(generated.name.encode()) < 255, generated.name

        binding_direct = root / "binding_direct.json"
        binding_direct.write_text(json.dumps({
            "schema": "leanmill-source-to-canary-binding-v1",
            "family": "fam",
            "decision": "retired",
            "concrete_target_row_ids": [],
            "positive_source_to_canary_attempts": [],
        }) + "\n")
        direct_wid = work_queue.enqueue(cx, kind="source_scout_task", priority=1, payload={
            "work_id": "source_bind:fam:direct_artifact",
            "family": "fam",
            "source_search_integration_receipt": str(receipt),
            "artifact_paths": [str(binding_direct)],
        })
        work_queue.update_status(cx, work_id=direct_wid, status="done")
        direct_result = ingest(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(root / "status_direct.json"),
            scan_limit=10,
            max_ingest=10,
            out_dir=str(root / "out"),
            root_base=str(root / "runs"),
            corpus=str(root / "corpus.json"),
            max_candidates_per_attempt=1,
            max_tests_per_probe=4,
            probe_timeout_s=120,
            probe_wall_timeout_s=180,
            backend="repl_file",
            warm_repl_inline=False,
            govern_winners=False,
            priority=150,
            max_attempts=1,
            extra_corpus=[str(root / "extra_corpus.json")],
            include_rejected=False,
            allocator=str(root / "missing_allocator.json"),
        ))
        assert direct_result["terminal_no_probe"] == 1

        unverified_value = root / "binding_unverified_value.json"
        unverified_value.write_text(json.dumps({
            "schema": "leanmill-source-to-canary-binding-v1",
            "family": "fam",
            "decision": "valid_falsifier",
            "concrete_target_row_ids": [],
            "positive_source_to_canary_attempts": [],
        }) + "\n")
        unverified_wid = work_queue.enqueue(cx, kind="source_scout_task", priority=1, payload={
            "work_id": "source_bind:fam:unverified_value",
            "family": "fam",
            "source_search_integration_receipt": str(receipt),
            "artifact_paths": [str(unverified_value)],
        })
        work_queue.update_status(cx, work_id=unverified_wid, status="done")
        unverified_result = ingest(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(root / "status_unverified.json"),
            scan_limit=10,
            max_ingest=10,
            out_dir=str(root / "out"),
            root_base=str(root / "runs"),
            corpus=str(root / "corpus.json"),
            max_candidates_per_attempt=1,
            max_tests_per_probe=4,
            probe_timeout_s=120,
            probe_wall_timeout_s=180,
            backend="repl_file",
            warm_repl_inline=False,
            govern_winners=False,
            priority=150,
            max_attempts=1,
            extra_corpus=[str(root / "extra_corpus.json")],
            include_rejected=False,
            allocator=str(root / "missing_allocator.json"),
        ))
        assert unverified_result["rejected"] == 1
        rejected_payload = json.loads(cx.execute(
            "SELECT payload_json FROM work_items WHERE work_id=?",
            (unverified_wid,),
        ).fetchone()["payload_json"])
        assert "agent_claimed_valid_falsifier_requires_probe_or_governance" in rejected_payload["source_binding_failures"]

        allocator = root / "allocator.json"
        allocator.write_text(json.dumps({
            "allocations": [{
                "family": "held_fam",
                "recommended_action": "hold_source_binding_until_new_target_evidence",
                "status": "seed_only",
                "source_quality": {"source_binding_conversion_rate": 0.0},
            }]
        }) + "\n")
        held_binding = root / "held_binding.json"
        held_binding.write_text(json.dumps({
            "schema": "leanmill-source-to-canary-binding-v1",
            "family": "held_fam",
            "decision": "canary_spec",
            "concrete_target_row_ids": ["MCB_X"],
            "positive_source_to_canary_attempts": [{
                "target_row_id": "MCB_X",
                "candidate_names": ["A.good"],
                "matched_negative_control": "omit source",
            }],
        }) + "\n")
        held_transcript = root / "held_agent.txt"
        held_transcript.write_text(f"Candidate packet path: {held_binding}\n")
        held_receipt = root / "held_receipt.json"
        held_receipt.write_text(json.dumps({
            "family": "held_fam",
            "queries": ["Matrix gram PosDef LinearIndependent"],
            "allowed_binding_target_rows": [{"row_id": "MCB_X"}],
            "top_source_candidates": [{
                "candidate_name": "A.good",
                "usable_for_canary_source": True,
                "name_resolves": True,
            }],
            "active_corpora": [
                {"path": str(root / "extra_corpus.json"), "sha256": _sha_file(root / "extra_corpus.json"), "row_count": 1},
            ],
        }) + "\n")
        held_wid = work_queue.enqueue(cx, kind="source_scout_task", priority=1, payload={
            "work_id": "source_bind:held_fam:allocator_hold",
            "family": "held_fam",
            "source_search_integration_receipt": str(held_receipt),
            "output_path": str(held_transcript),
        })
        work_queue.update_status(cx, work_id=held_wid, status="done")
        held_result = ingest(argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(root / "status_allocator_held.json"),
            scan_limit=10,
            max_ingest=10,
            out_dir=str(root / "out"),
            root_base=str(root / "runs"),
            corpus=str(root / "corpus.json"),
            max_candidates_per_attempt=1,
            max_tests_per_probe=4,
            probe_timeout_s=120,
            probe_wall_timeout_s=180,
            backend="repl_file",
            warm_repl_inline=False,
            govern_winners=False,
            priority=150,
            max_attempts=1,
            extra_corpus=[str(root / "extra_corpus.json")],
            include_rejected=False,
            allocator=str(allocator),
        ))
        assert held_result["retired_allocator_held"] == 1
        held_payload = json.loads(cx.execute(
            "SELECT payload_json FROM work_items WHERE work_id=?",
            (held_wid,),
        ).fetchone()["payload_json"])
        assert held_payload["source_binding_ingest_status"] == "retired_allocator_held_source_binding"
    print("leanmill_source_binding_ingester self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--out", default=f"{DEFAULT_DATA_DIR}/source_binding_ingestion_status.json")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--root-base", default=DEFAULT_ROOT_BASE)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--allocator", default=DEFAULT_ALLOCATOR)
    ap.add_argument("--extra-corpus", action="append", default=list(DEFAULT_EXTRA_CORPORA))
    ap.add_argument("--scan-limit", type=int, default=40)
    ap.add_argument("--max-ingest", type=int, default=8)
    ap.add_argument("--max-candidates-per-attempt", type=int, default=2)
    ap.add_argument("--max-tests-per-probe", type=int, default=6)
    ap.add_argument("--probe-timeout-s", type=int, default=120)
    ap.add_argument("--probe-wall-timeout-s", type=int, default=180)
    ap.add_argument("--backend", choices=["subprocess", "repl", "repl_step", "repl_file"], default="repl_file")
    ap.add_argument("--warm-repl-inline", action="store_true")
    ap.add_argument("--govern-winners", action="store_true")
    ap.add_argument("--priority", type=int, default=150)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--max-attempts", type=int, default=1)
    ap.add_argument("--include-rejected", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if int(args.priority) == 150:
        args.priority = _queue_priority(args, "source_binding_ingester_followup", 150)
    result = ingest(args)
    print(json.dumps({
        "inspected": result["inspected"],
        "probe_enqueued": result["probe_enqueued"],
        "rejected": result["rejected"],
        "retired_allocator_held": result["retired_allocator_held"],
        "out": args.out,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
