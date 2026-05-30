#!/usr/bin/env python3
"""Build fresh C-supply demand corpora from current source-demand families.

This stage is deterministic sourcing only: it reads the current C-slice debt,
scans broad row corpora for sibling rows that match demanded family signatures,
and writes family-specific corpora for later static-only C-supply mining. It
runs no proof tools and grants no proof credit.
"""
from __future__ import annotations

import argparse
import ast
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import leanmill_family_specs as family_specs
from leanmill_factory_config import FACTORY_POLICY, read_policy
import leanmill_source_materialization as source_materialization
import leanmill_static_failure_miner as static_miner
from leanmill_paths import DATA_DIR
import leanmill_work_queue as work_queue

DEFAULT_SELECTION = f"{DATA_DIR}/c_supply_batch_c_discriminating_slice.json"
DEFAULT_OUT_DIR = f"{DATA_DIR}/queued_learning_work"
DEFAULT_OUT = f"{DATA_DIR}/c_supply_demand_corpus_builder.json"
DEFAULT_MD = f"{DATA_DIR}/c_supply_demand_corpus_builder.md"
DEFAULT_CHECKPOINT = f"{DATA_DIR}/c_supply_batch_checkpoint.jsonl"
DEFAULT_ROW_CONTEXT = f"{DATA_DIR}/c_supply_batch_row_context.json"
DEFAULT_SOURCE_SNAPSHOT_DIR = f"{DATA_DIR}/evaluation_harness_sources"
DEFAULT_SOURCE_SEARCH_INTEGRATIONS = f"{DATA_DIR}/source_search_integrations"
DEFAULT_SOURCE_CORPORA = [
    "/tmp/rung1/mcb_refill_dedup_after_expand100/mcb_corpus.json",
    f"{DATA_DIR}/mcb_expand100_active_corpus.json",
    "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_QUEUE.json",
    "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json",
]


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _checkpoint_seen_rows(checkpoint: str | Path) -> set[str]:
    return {str(rec.get("row_id") or "") for rec in _read_jsonl(checkpoint) if str(rec.get("row_id") or "")}


def _checkpoint_excluded_rows(checkpoint: str | Path) -> set[str]:
    positive_exits = {
        "raw_closure_candidate",
        "governed_tool_tactic_closure_candidate",
        "ratified_closure",
        "exact_gap",
        "valid_falsifier",
    }
    out: set[str] = set()
    for rec in _read_jsonl(checkpoint):
        row_id = str(rec.get("row_id") or "")
        if row_id and str(rec.get("learning_exit") or "") in positive_exits:
            out.add(row_id)
    return out


def _queue_terminal_nonuseful_rows(queue_db: str | Path) -> set[str]:
    path = Path(queue_db)
    if not path.exists() or not path.is_file():
        return set()
    try:
        cx = sqlite3.connect(str(path))
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            """
            SELECT payload_json
            FROM work_items
            WHERE kind='repair_canary_probe'
              AND status IN ('done','failed','retired','dead_letter')
            """
        ).fetchall()
    except sqlite3.Error:
        return set()
    out: set[str] = set()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("probe_lane") or "") != "family_spec":
            continue
        outcomes = payload.get("row_outcomes") or []
        if isinstance(outcomes, dict):
            outcomes = list(outcomes.values())
        if not isinstance(outcomes, list) or not outcomes:
            shard = payload.get("family_spec_shard") or {}
            outcomes = [{"row_id": str(shard.get("row_id") or ""), "learning_unit_exit": payload.get("learning_unit_exit") or payload.get("exit_kind")}]
        for outcome in outcomes:
            if not isinstance(outcome, dict):
                continue
            row_id = str(outcome.get("row_id") or "")
            exit_kind = str(outcome.get("learning_unit_exit") or payload.get("learning_unit_exit") or payload.get("exit_kind") or "")
            if row_id and exit_kind in {"tested_no_positive_signal", "negative_control_unexpected_pass", "invalid_negative_control"}:
                out.add(row_id)
    return out


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value)).strip("_") or "item"


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("target_id") or "")


def _source_file(row: dict[str, Any]) -> str:
    return str(row.get("source_file") or row.get("sorried_file") or "").strip()


def _source_file_exists(row: dict[str, Any]) -> bool:
    path = _source_file(row)
    return bool(path) and Path(path).exists() and Path(path).is_file()


def _policy_section(args: argparse.Namespace) -> dict[str, Any]:
    policy = read_policy(getattr(args, "factory_policy", FACTORY_POLICY))
    profile_name = str(getattr(args, "policy_profile", "") or "")
    profile = ((policy.get("profiles") or {}).get(profile_name) or {}) if isinstance(policy.get("profiles"), dict) else {}
    section = profile.get("c_supply_growth_controller") if isinstance(profile, dict) else {}
    return section if isinstance(section, dict) else {}


def _policy_bool(args: argparse.Namespace, key: str, fallback: bool) -> bool:
    section = _policy_section(args)
    value = section.get(key)
    if value is None:
        return bool(fallback)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _policy_int(args: argparse.Namespace, key: str, fallback: int) -> int:
    section = _policy_section(args)
    try:
        return int(section.get(key) if section.get(key) is not None else fallback)
    except (TypeError, ValueError):
        return int(fallback)


def _policy_str(args: argparse.Namespace, key: str, fallback: str) -> str:
    section = _policy_section(args)
    return str(section.get(key) or fallback)


def _normalize_source_shape(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    source = out.get("source")
    if isinstance(source, str) and source.strip().startswith("{"):
        try:
            parsed = ast.literal_eval(source)
        except (SyntaxError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            out["source"] = parsed
    return out


def _materialize_row_source_if_needed(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if _source_file_exists(row):
        return {"status": "already_present", "row_id": _row_id(row), "source_file": _source_file(row)}
    if not bool(getattr(args, "materialize_missing_source_files", False)):
        return {"status": "not_requested", "row_id": _row_id(row), "source_file": _source_file(row)}
    receipt = source_materialization.materialize_row_sources(
        [row],
        out_dir=getattr(args, "source_snapshot_dir", DEFAULT_SOURCE_SNAPSHOT_DIR),
        mathlib_root=getattr(args, "mathlib_root", ""),
    )
    receipts = receipt.get("receipts") if isinstance(receipt.get("receipts"), list) else []
    item = dict(receipts[0]) if receipts and isinstance(receipts[0], dict) else {"status": receipt.get("status")}
    item["target_resolution_status"] = row.get("target_resolution_status")
    item["source_file_after"] = _source_file(row)
    return item


def _source_demand_families(selection: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for req in selection.get("source_demand_requests") or []:
        if not isinstance(req, dict):
            continue
        if str(req.get("recommended_action") or "") != "source_similar_static_fail_rows":
            continue
        family = str(req.get("family") or "")
        if family and family not in seen:
            seen.add(family)
            out.append(family)
    return out


def _row_context_known_rows(row_context: str | Path) -> set[str]:
    obj = _read_json(row_context) or {}
    return {_row_id(row) for row in static_miner._iter_rows(obj) if _row_id(row)}


def _selection_known_rows(selection: dict[str, Any]) -> set[str]:
    out = {str(x) for x in (selection.get("selected_rows_order") or []) if str(x)}
    for row in selection.get("rows") or []:
        if isinstance(row, dict) and str(row.get("row_id") or ""):
            out.add(str(row.get("row_id") or ""))
    for row in selection.get("selected_rows") or []:
        if isinstance(row, dict) and str(row.get("row_id") or ""):
            out.add(str(row.get("row_id") or ""))
    return out


def _iter_source_rows(paths: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows_by_id: dict[str, dict[str, Any]] = {}
    meta: list[dict[str, Any]] = []
    for path in paths:
        obj = _read_json(path) or {}
        rows = static_miner._iter_rows(obj)
        meta.append({"path": path, "exists": Path(path).exists(), "row_count": len(rows)})
        for row in rows:
            rid = _row_id(row)
            if rid and rid not in rows_by_id:
                rec = dict(row)
                rec["row_id"] = rid
                rec.setdefault("c_supply_demand_source_corpus", path)
                rows_by_id[rid] = rec
    return list(rows_by_id.values()), meta


def _source_search_integration_paths(args: argparse.Namespace) -> list[Path]:
    root = Path(_policy_str(args, "source_search_integration_dir", DEFAULT_SOURCE_SEARCH_INTEGRATIONS))
    if not root.exists() or not root.is_dir():
        return []
    window_s = max(0, _policy_int(args, "source_search_integration_window_s", 24 * 60 * 60))
    cutoff = int(time.time()) - window_s if window_s > 0 else 0
    paths = [p for p in root.glob("*.json") if p.is_file()]
    if cutoff:
        paths = [p for p in paths if int(p.stat().st_mtime) >= cutoff]
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return paths[: max(0, _policy_int(args, "source_search_integration_receipt_limit", 200))]


def _rows_from_source_search_integrations(
    args: argparse.Namespace,
    *,
    demanded: list[str],
    known_rows: set[str],
    family_has_controls: dict[str, bool],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    enabled = _policy_bool(args, "source_search_integration_feed_enabled", False)
    if not enabled:
        return {}, {
            "enabled": False,
            "reason": "disabled_by_policy",
            "credit_boundary": "source-search integration rows are routing-only when enabled; they grant no C, benchmark, governance, or proof credit",
        }
    demanded_set = set(demanded)
    rows_per_family = max(0, _policy_int(args, "source_search_integration_rows_per_family", 12))
    by_family: dict[str, list[dict[str, Any]]] = {family: [] for family in demanded}
    seen_by_family: dict[str, set[str]] = {family: set() for family in demanded}
    receipt_count = 0
    accepted_receipt_count = 0
    blocked_receipt_count = 0
    candidate_count = 0
    accepted_row_count = 0
    blocked_examples: list[dict[str, Any]] = []
    accepted_examples: list[dict[str, Any]] = []
    for path in _source_search_integration_paths(args):
        receipt_count += 1
        receipt = _read_json(path)
        if not isinstance(receipt, dict):
            continue
        family = str(receipt.get("family") or "")
        blockers = [str(x) for x in (receipt.get("integration_blockers") or []) if str(x)]
        if family not in demanded_set:
            continue
        if not family_has_controls.get(family):
            blocked_receipt_count += 1
            if len(blocked_examples) < 10:
                blocked_examples.append({"family": family, "path": str(path), "reason": "family_missing_negative_controls"})
            continue
        if str(receipt.get("integration_decision") or "") != "enqueue_source_to_canary_binding" or blockers:
            blocked_receipt_count += 1
            if len(blocked_examples) < 10:
                blocked_examples.append({"family": family, "path": str(path), "reason": "integration_not_binding_ready", "blockers": blockers})
            continue
        accepted_receipt_count += 1
        for raw_row in receipt.get("allowed_binding_target_rows") or []:
            if not isinstance(raw_row, dict):
                continue
            candidate_count += 1
            if len(by_family.get(family, [])) >= rows_per_family:
                continue
            row = _normalize_source_shape(raw_row)
            row_id = _row_id(row)
            if not row_id or row_id in known_rows or row_id in seen_by_family[family]:
                continue
            seen_by_family[family].add(row_id)
            row.setdefault("row_id", row_id)
            row["c_supply_demand_source_corpus"] = "source_search_integration"
            row["source_search_integration_receipt"] = str(path)
            mat = _materialize_row_source_if_needed(row, args)
            if not _source_file_exists(row):
                if len(blocked_examples) < 10:
                    blocked_examples.append({
                        "family": family,
                        "row_id": row_id,
                        "path": str(path),
                        "reason": "source_search_row_not_materialized",
                        "materialization_status": mat.get("status"),
                        "materialization_reason": mat.get("reason"),
                    })
                continue
            by_family[family].append({
                "row_id": row_id,
                "hit_count": max(1, _policy_int(args, "source_search_integration_routing_hit_count", 2)),
                "confidence": 0.72,
                "matched_features": ["source_search_integration_receipt"],
                "source_corpus": "source_search_integration",
                "source_search_integration_receipt": str(path),
                "row": row,
            })
            accepted_row_count += 1
            if len(accepted_examples) < 10:
                accepted_examples.append({"family": family, "row_id": row_id, "source_file": _source_file(row), "path": str(path)})
    summary = {
        "enabled": True,
        "receipt_count": receipt_count,
        "accepted_receipt_count": accepted_receipt_count,
        "blocked_receipt_count": blocked_receipt_count,
        "candidate_row_count": candidate_count,
        "accepted_row_count": accepted_row_count,
        "rows_per_family": rows_per_family,
        "examples": accepted_examples,
        "blocked_examples": blocked_examples,
        "rule": _policy_str(
            args,
            "source_search_integration_rule",
            "Binding-ready source-search integration receipts may seed C-supply demand corpora as routing-only rows; static/probe gates still decide all credit.",
        ),
        "credit_boundary": "source-search integration rows are routing-only; they grant no C, benchmark, governance, or proof credit",
    }
    return {family: rows for family, rows in by_family.items() if rows}, summary


TARGET_REFERENCE_TEMPLATE_FAILURES = {
    "positive_template_references_target_theorem",
    "negative_control_references_target_theorem",
}


def _target_reference_quarantine_count(specs: list[dict[str, Any]], target_names_by_row: dict[str, list[str]]) -> int:
    return sum(
        1
        for failure in family_specs.validate_specs(specs, target_names_by_row=target_names_by_row)
        if str(failure.get("failure") or "") in TARGET_REFERENCE_TEMPLATE_FAILURES
    )


def _family_signature_index(
    spec_dir: str,
    *,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    raw_specs = family_specs.load_specs(spec_dir)
    specs = family_specs.usable_specs(raw_specs, target_names_by_row=target_names_by_row)
    signatures = static_miner._family_signatures(specs)
    filter_summary = {
        "target_context_row_count": len(target_names_by_row or {}),
        "target_reference_quarantine_count": _target_reference_quarantine_count(raw_specs, target_names_by_row or {}),
        "usable_family_signature_count": len(signatures),
        "rationale": "source-demand signatures are built only from family specs after row-target quarantine",
    }
    return (
        {str(s.get("family") or ""): s for s in signatures if str(s.get("family") or "")},
        {str(s.get("family") or ""): s for s in specs if str(s.get("family") or "")},
        filter_summary,
    )


def build(args: argparse.Namespace) -> dict[str, Any]:
    selection = _read_json(args.selection) or {}
    demanded = _source_demand_families(selection)
    selection_known_rows = _selection_known_rows(selection)
    checkpoint_seen_rows = _checkpoint_seen_rows(args.checkpoint)
    historical_excluded_rows = _checkpoint_excluded_rows(args.checkpoint).union(_queue_terminal_nonuseful_rows(args.queue_db))
    known_rows = set(selection_known_rows)
    known_rows.update(checkpoint_seen_rows)
    known_rows.update(historical_excluded_rows)
    target_names_by_row = family_specs.target_names_by_row_from_context_paths([args.row_context])
    signature_by_family, _spec_by_family, target_filter = _family_signature_index(
        args.spec_dir,
        target_names_by_row=target_names_by_row,
    )
    source_paths = [str(p) for p in (args.source_corpus or [])] or list(DEFAULT_SOURCE_CORPORA)
    rows, source_meta = _iter_source_rows(source_paths)
    run_id = args.run_id or str(int(time.time()))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    family_hits: dict[str, list[dict[str, Any]]] = {family: [] for family in demanded}
    missing_source_by_family: dict[str, int] = {family: 0 for family in demanded}
    missing_source_examples: dict[str, list[dict[str, Any]]] = {family: [] for family in demanded}
    materialization_counts: dict[str, int] = {}
    materialization_examples: list[dict[str, Any]] = []
    missing_signature_families = [family for family in demanded if family not in signature_by_family]
    scanned = 0
    for row in rows:
        row_id = _row_id(row)
        if not row_id or row_id in known_rows:
            continue
        scanned += 1
        matches = static_miner._match_families(row, list(signature_by_family.values()), min_hits=int(args.min_signature_hits))
        if not matches:
            continue
        for match in matches:
            family = str(match.get("family") or "")
            if family not in family_hits:
                continue
            if not match.get("has_negative_controls"):
                continue
            if not bool(getattr(args, "allow_missing_source_file", False)) and not _source_file_exists(row):
                mat = _materialize_row_source_if_needed(row, args)
                status = str(mat.get("status") or "unknown")
                materialization_counts[status] = materialization_counts.get(status, 0) + 1
                if len(materialization_examples) < 12:
                    materialization_examples.append({
                        "row_id": row_id,
                        "family": family,
                        "status": status,
                        "source_file_after": mat.get("source_file_after") or mat.get("source_file"),
                        "target_resolution_status": mat.get("target_resolution_status"),
                        "materialization_source": mat.get("materialization_source"),
                        "reason": mat.get("reason"),
                    })
                if _source_file_exists(row):
                    pass
                else:
                    missing_source_by_family[family] += 1
                    examples = missing_source_examples.setdefault(family, [])
                    if len(examples) < 5:
                        examples.append({
                            "row_id": row_id,
                            "source_file": _source_file(row),
                            "source_corpus": row.get("c_supply_demand_source_corpus"),
                            "materialization_status": status,
                        })
                    continue
            if not bool(getattr(args, "allow_missing_source_file", False)) and not _source_file_exists(row):
                missing_source_by_family[family] += 1
                examples = missing_source_examples.setdefault(family, [])
                if len(examples) < 5:
                    examples.append({
                        "row_id": row_id,
                        "source_file": _source_file(row),
                        "source_corpus": row.get("c_supply_demand_source_corpus"),
                    })
                continue
            item = {
                "row_id": row_id,
                "hit_count": int(match.get("hit_count") or 0),
                "confidence": float(match.get("confidence") or 0.0),
                "matched_features": match.get("matched_features") or [],
                "source_corpus": row.get("c_supply_demand_source_corpus"),
                "row": row,
            }
            family_hits[family].append(item)

    integration_hits, source_search_integration_feed = _rows_from_source_search_integrations(
        args,
        demanded=demanded,
        known_rows=known_rows,
        family_has_controls={
            family: bool(signature_by_family.get(family, {}).get("has_negative_controls"))
            for family in demanded
        },
    )
    for family, hits in integration_hits.items():
        family_hits.setdefault(family, []).extend(hits)

    corpora: list[dict[str, Any]] = []
    for family in demanded:
        hits_by_row: dict[str, dict[str, Any]] = {}
        for hit in family_hits.get(family) or []:
            row_id = str(hit.get("row_id") or "")
            prev = hits_by_row.get(row_id)
            if prev is None or (int(hit.get("hit_count") or 0), float(hit.get("confidence") or 0.0)) > (int(prev.get("hit_count") or 0), float(prev.get("confidence") or 0.0)):
                hits_by_row[row_id] = hit
        hits = sorted(hits_by_row.values(), key=lambda h: (-int(h.get("hit_count") or 0), -float(h.get("confidence") or 0.0), str(h.get("row_id") or "")))
        selected = hits[: max(0, int(args.rows_per_family))]
        if not selected:
            corpora.append({"family": family, "row_count": 0, "path": None, "status": "no_rows_selected"})
            continue
        path = out_dir / f"probe_corpus_family_spec_{_slug(family)}_demand_{run_id}.json"
        corpus = {
            "schema": "leanmill-c-supply-demand-corpus-v1",
            "created_at_epoch": int(time.time()),
            "family": family,
            "label": "family_spec_demand_sibling",
            "run_id": run_id,
            "selection": args.selection,
            "credit_boundary": "sourcing only; static C-supply miner and governance decide value",
            "source_corpora": source_meta,
            "excluded_known_selection_row_count": len(known_rows),
            "min_signature_hits": int(args.min_signature_hits),
            "target_row_ids": [str(hit.get("row_id") or "") for hit in selected],
            "match_receipts": [
                {k: v for k, v in hit.items() if k != "row"}
                for hit in selected
            ],
            "rows": [hit["row"] for hit in selected],
        }
        _write_json(path, corpus)
        corpora.append({
            "family": family,
            "row_count": len(corpus["rows"]),
            "path": str(path),
            "status": "written",
            "top_rows": corpus["target_row_ids"][:10],
        })

    result = {
        "schema": "leanmill-c-supply-demand-corpus-builder-v1",
        "run_id": run_id,
        "selection": args.selection,
        "source_family_count": len(demanded),
        "source_families": demanded,
        "missing_signature_families": missing_signature_families,
        "known_selection_row_count": len(known_rows),
        "selection_known_row_count": len(selection_known_rows),
        "checkpoint_seen_row_count": len(checkpoint_seen_rows),
        "row_context_known_row_count": len(_row_context_known_rows(args.row_context)),
        "row_context_exclusion_policy": "metadata_only_not_excluded",
        "target_aware_family_template_filter": target_filter,
        "historical_excluded_row_count": len(historical_excluded_rows),
        "source_corpora": source_meta,
        "source_row_count": len(rows),
        "scanned_new_row_count": scanned,
        "missing_source_file_candidate_count": sum(missing_source_by_family.values()),
        "missing_source_file_candidate_counts_by_family": dict(sorted((k, v) for k, v in missing_source_by_family.items() if v)),
        "missing_source_file_candidate_examples": {
            k: v for k, v in sorted(missing_source_examples.items()) if v
        },
        "source_materialization": {
            "enabled": bool(getattr(args, "materialize_missing_source_files", False)),
            "source_snapshot_dir": str(getattr(args, "source_snapshot_dir", "")),
            "counts": dict(sorted(materialization_counts.items())),
            "examples": materialization_examples,
            "credit_boundary": "source materialization only; no static, C, benchmark, or proof credit",
        },
        "source_search_integration_feed": source_search_integration_feed,
        "source_file_filter": {
            "require_existing_source_file": not bool(getattr(args, "allow_missing_source_file", False)),
            "credit_boundary": "source-file existence is an executable-sourcing precondition only; it grants no static, C, benchmark, or proof credit",
        },
        "rows_per_family": int(args.rows_per_family),
        "min_signature_hits": int(args.min_signature_hits),
        "corpora_written_count": sum(1 for c in corpora if c.get("status") == "written"),
        "total_rows_written": sum(int(c.get("row_count") or 0) for c in corpora),
        "corpora": corpora,
    }
    if args.out:
        _write_json(args.out, result)
    if args.md:
        _write_md(args.md, result)
    return result


def _write_md(path: str | Path, result: dict[str, Any]) -> None:
    lines = [
        "# LeanMill C-Supply Demand Corpus Builder",
        "",
        f"- run_id: `{result['run_id']}`",
        f"- source_family_count: `{result['source_family_count']}`",
        f"- source_row_count: `{result['source_row_count']}`",
        f"- scanned_new_row_count: `{result['scanned_new_row_count']}`",
        f"- missing_source_file_candidate_count: `{result.get('missing_source_file_candidate_count', 0)}`",
        f"- corpora_written_count: `{result['corpora_written_count']}`",
        f"- total_rows_written: `{result['total_rows_written']}`",
        "",
        "| family | rows | status | path |",
        "|---|---:|---|---|",
    ]
    for row in result.get("corpora") or []:
        lines.append(f"| {row.get('family')} | {row.get('row_count')} | {row.get('status')} | {row.get('path')} |")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_c_supply_demand_corpus_") as td:
        root = Path(td)
        spec_dir = root / "specs"
        spec_dir.mkdir()
        (spec_dir / "fam.yaml").write_text("""
family: fam
status: candidate_family
residual_match:
  head_patterns: [AlphaToken, BetaToken]
templates:
  - id: pos
    row_id: design
    test_kind: positive
    body_lines: [trivial]
  - id: neg
    row_id: design
    test_kind: negative_control
    body_lines: [exact False.elim]
""")
        (spec_dir / "leaky.yaml").write_text("""
family: leaky
status: candidate_family
residual_match:
  head_patterns: [AlphaToken, BetaToken]
templates:
  - id: pos
    row_id: design
    test_kind: positive
    body_lines: [exact design]
  - id: neg
    row_id: design
    test_kind: negative_control
    body_lines: [trivial]
""")
        sel = root / "selection.json"
        sel.write_text(json.dumps({
            "selected_rows_order": ["old"],
            "source_demand_requests": [
                {"family": "fam", "recommended_action": "source_similar_static_fail_rows"},
                {"family": "leaky", "recommended_action": "source_similar_static_fail_rows"},
            ],
        }) + "\n")
        src = root / "src.lean"
        src.write_text("theorem r1 : True := by\n  trivial\n-- AlphaToken BetaToken\n")
        corpus = root / "corpus.json"
        corpus.write_text(json.dumps({"rows": [
            {"row_id": "old", "goal": "AlphaToken BetaToken", "source_file": str(src)},
            {"row_id": "new", "goal": "AlphaToken BetaToken", "source_file": str(src)},
            {"row_id": "missing_source", "goal": "theorem missing_source_target : True := by\n-- AlphaToken BetaToken", "source_file": str(root / "missing.lean")},
        ]}) + "\n")
        row_context = root / "row_context.json"
        row_context.write_text(json.dumps({"rows": [
            {"row_id": "new", "source_file": str(src)},
            {"row_id": "design", "target_theorem_name": "design", "source_file": str(src)},
        ]}) + "\n")
        result = build(argparse.Namespace(selection=str(sel), row_context=str(row_context), spec_dir=str(spec_dir), source_corpus=[str(corpus)], out_dir=str(root / "out"), out=None, md=None, run_id="x", rows_per_family=5, min_signature_hits=2, checkpoint=str(root / "ck.jsonl"), queue_db=str(root / "q.sqlite"), allow_missing_source_file=False, materialize_missing_source_files=False, source_snapshot_dir=str(root / "snapshots"), mathlib_root=""))
        assert result["corpora_written_count"] == 1, result
        assert result["total_rows_written"] == 1, result
        assert result["missing_source_file_candidate_count"] == 1, result
        assert "leaky" in result["missing_signature_families"], result
        assert result["target_aware_family_template_filter"]["target_reference_quarantine_count"] == 1, result
        assert result["row_context_exclusion_policy"] == "metadata_only_not_excluded", result
        written = _read_json(result["corpora"][0]["path"])
        assert written["rows"][0]["row_id"] == "new", written
        ck = root / "ck.jsonl"
        ck.write_text(json.dumps({"row_id": "new", "arm": "public_tool_static", "learning_exit": "tested_no_positive_signal"}) + "\n")
        checkpoint_seen_blocked = build(argparse.Namespace(selection=str(sel), row_context=str(row_context), spec_dir=str(spec_dir), source_corpus=[str(corpus)], out_dir=str(root / "out2"), out=None, md=None, run_id="y", rows_per_family=5, min_signature_hits=2, checkpoint=str(ck), queue_db=str(root / "q.sqlite"), allow_missing_source_file=False, materialize_missing_source_files=False, source_snapshot_dir=str(root / "snapshots"), mathlib_root=""))
        assert checkpoint_seen_blocked["corpora_written_count"] == 0, checkpoint_seen_blocked
        assert checkpoint_seen_blocked["checkpoint_seen_row_count"] == 1, checkpoint_seen_blocked
        materialized = build(argparse.Namespace(selection=str(sel), row_context=str(row_context), spec_dir=str(spec_dir), source_corpus=[str(corpus)], out_dir=str(root / "out3"), out=None, md=None, run_id="z", rows_per_family=5, min_signature_hits=2, checkpoint=str(root / "empty_ck.jsonl"), queue_db=str(root / "q.sqlite"), allow_missing_source_file=False, materialize_missing_source_files=True, source_snapshot_dir=str(root / "snapshots"), mathlib_root=""))
        assert materialized["missing_source_file_candidate_count"] == 0, materialized
        assert materialized["source_materialization"]["counts"].get("materialized") == 1, materialized
        assert materialized["corpora_written_count"] == 1 and materialized["total_rows_written"] == 2, materialized
        mathlib = root / "Mathlib"
        mathlib_source = mathlib / "Analysis" / "Test.lean"
        mathlib_source.parent.mkdir(parents=True, exist_ok=True)
        mathlib_source.write_text(
            "import Mathlib\n\n"
            "theorem external_target : True := by\n"
            "  trivial\n",
            encoding="utf-8",
        )
        integration_dir = root / "integrations"
        integration_dir.mkdir()
        (integration_dir / "source_ready.json").write_text(json.dumps({
            "schema": "leanmill-source-search-integration-v1",
            "family": "fam",
            "integration_decision": "enqueue_source_to_canary_binding",
            "integration_blockers": [],
            "allowed_binding_target_rows": [{
                "row_id": "MCB_099_external_target",
                "goal": "external source row without AlphaToken BetaToken signature",
                "source": {"mathlib_name": "external_target", "file": "Analysis/Test.lean"},
            }],
        }) + "\n")
        policy = root / "policy.json"
        policy.write_text(json.dumps({
            "profiles": {
                "unit": {
                    "c_supply_growth_controller": {
                        "source_search_integration_feed_enabled": True,
                        "source_search_integration_dir": str(integration_dir),
                        "source_search_integration_receipt_limit": 10,
                        "source_search_integration_rows_per_family": 2,
                        "source_search_integration_window_s": 86400,
                    }
                }
            }
        }) + "\n")
        empty_corpus = root / "empty_corpus.json"
        empty_corpus.write_text(json.dumps({"rows": []}) + "\n")
        integration_result = build(argparse.Namespace(selection=str(sel), row_context=str(row_context), spec_dir=str(spec_dir), source_corpus=[str(empty_corpus)], out_dir=str(root / "out4"), out=None, md=None, run_id="integration", rows_per_family=5, min_signature_hits=2, checkpoint=str(root / "empty_ck2.jsonl"), queue_db=str(root / "q.sqlite"), allow_missing_source_file=False, materialize_missing_source_files=True, source_snapshot_dir=str(root / "integration_snapshots"), mathlib_root=str(mathlib), factory_policy=str(policy), policy_profile="unit"))
        assert integration_result["source_search_integration_feed"]["accepted_row_count"] == 1, integration_result
        assert integration_result["corpora_written_count"] == 1 and integration_result["total_rows_written"] == 1, integration_result
        integration_written = _read_json(integration_result["corpora"][0]["path"])
        assert integration_written["rows"][0]["row_id"] == "MCB_099_external_target", integration_written
        assert Path(integration_written["rows"][0]["source_file"]).exists(), integration_written
    print("leanmill_c_supply_demand_corpus_builder self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", default=DEFAULT_SELECTION)
    ap.add_argument("--spec-dir", default=family_specs.DEFAULT_SPEC_DIR)
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--source-corpus", action="append", default=[])
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--rows-per-family", type=int, default=40)
    ap.add_argument("--min-signature-hits", type=int, default=2)
    ap.add_argument("--allow-missing-source-file", action="store_true")
    ap.add_argument("--materialize-missing-source-files", action="store_true")
    ap.add_argument("--source-snapshot-dir", default=DEFAULT_SOURCE_SNAPSHOT_DIR)
    ap.add_argument("--mathlib-root", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = build(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "run_id": result["run_id"],
        "source_family_count": result["source_family_count"],
        "corpora_written_count": result["corpora_written_count"],
        "total_rows_written": result["total_rows_written"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
