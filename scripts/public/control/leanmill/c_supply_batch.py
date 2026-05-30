#!/usr/bin/env python3
"""Batch C-discriminating supply mining across family-specific corpora.

This is the operational wrapper around the safe sourcing pipeline:
family-specific corpora -> static-only mining -> aggregate static failures ->
C-discriminating gate -> optional freeze. It does not run Path C.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
import leanmill_c_discriminating_slice_prep as c_prep
import leanmill_c_slice_freezer as freezer
import leanmill_static_failure_miner as miner
from leanmill_factory_config import read_policy
from leanmill_paths import DATA_DIR, FACTORY_POLICY

DEFAULT_OUT = f"{DATA_DIR}/c_supply_batch_status.json"
DEFAULT_MD = f"{DATA_DIR}/c_supply_batch_status.md"
DEFAULT_AGG_CHECKPOINT = f"{DATA_DIR}/c_supply_batch_checkpoint.jsonl"
DEFAULT_AGG_ROW_CONTEXT = f"{DATA_DIR}/c_supply_batch_row_context.json"
DEFAULT_SELECTION = f"{DATA_DIR}/c_supply_batch_c_discriminating_slice.json"
DEFAULT_SELECTION_MD = f"{DATA_DIR}/c_supply_batch_c_discriminating_slice.md"
DEFAULT_SELECTED_ROW_CONTEXT = f"{DATA_DIR}/c_supply_batch_c_discriminating_row_context.json"
DEFAULT_FREEZE = f"{DATA_DIR}/c_supply_batch_c_discriminating_slice_frozen.json"
DEFAULT_REPORT_DIR = f"{DATA_DIR}/c_supply_batch_reports"
DEFAULT_CORPUS_GLOBS = [f"{DATA_DIR}/queued_learning_work/probe_corpus_family_spec_*.json"]
DEFAULT_SHARED_OUTPUT_LOCK = f"{DATA_DIR}/c_supply_batch.lock"
DEFAULT_STATIC_MINER_LEASE_TTL_S = 1800


def _family_corpus_pattern(family: str) -> str:
    return f"{DATA_DIR}/queued_learning_work/probe_corpus_family_spec_{_slug(family)}_*.json"


def _source_demand_families(selection_path: str | Path) -> list[str]:
    obj = _read_json(selection_path) or {}
    families: list[str] = []
    seen: set[str] = set()
    for req in obj.get("source_demand_requests") or []:
        if not isinstance(req, dict):
            continue
        if str(req.get("recommended_action") or "") != "source_similar_static_fail_rows":
            continue
        family = str(req.get("family") or "")
        if family and family not in seen:
            seen.add(family)
            families.append(family)
    return families


def _source_demand_corpus_globs(selection_path: str | Path) -> list[str]:
    return [_family_corpus_pattern(family) for family in _source_demand_families(selection_path)]


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


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


def _write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    order: list[tuple[str, str, str]] = []
    for row in rows:
        key = (str(row.get("run_id") or ""), str(row.get("row_id") or ""), str(row.get("arm") or ""))
        if key not in by_key:
            order.append(key)
            by_key[key] = row
            continue
        by_key[key] = _better_static_record(by_key[key], row)
    p.write_text("".join(json.dumps(by_key[key], sort_keys=True) + "\n" for key in order))


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("target_id") or "")


def _iter_rows(obj: Any) -> list[dict[str, Any]]:
    return miner._iter_rows(obj)


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _policy_ops(path: str | Path) -> dict[str, Any]:
    obj = read_policy(path)
    ops = obj.get("operations") if isinstance(obj, dict) else {}
    return ops if isinstance(ops, dict) else {}


def _policy_supply(path: str | Path) -> dict[str, Any]:
    supply = _policy_ops(path).get("c_discriminating_supply")
    return supply if isinstance(supply, dict) else {}


def _policy_int(policy: dict[str, Any], key: str, fallback: int) -> int:
    try:
        return int(policy.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _policy_list(policy: dict[str, Any], key: str, fallback: list[str]) -> list[str]:
    value = policy.get(key, fallback)
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return list(fallback)
    return [str(x) for x in value if str(x)]


def _default_selection_paths() -> dict[str, str]:
    return {
        "aggregate_checkpoint": DEFAULT_AGG_CHECKPOINT,
        "aggregate_row_context": DEFAULT_AGG_ROW_CONTEXT,
        "selection_out": DEFAULT_SELECTION,
        "selection_md": DEFAULT_SELECTION_MD,
        "selected_row_context_out": DEFAULT_SELECTED_ROW_CONTEXT,
        "freeze_out": DEFAULT_FREEZE,
    }


def _isolate_default_selection_outputs_for_custom_status(args: argparse.Namespace) -> dict[str, str]:
    if not getattr(args, "out", None) or str(args.out) == str(DEFAULT_OUT):
        return {}
    changed: dict[str, str] = {}
    base = Path(args.out)
    stem = base.stem
    parent = base.parent
    replacements = {
        "aggregate_checkpoint": parent / f"{stem}_checkpoint.jsonl",
        "aggregate_row_context": parent / f"{stem}_row_context.json",
        "selection_out": parent / f"{stem}_c_discriminating_slice.json",
        "selection_md": parent / f"{stem}_c_discriminating_slice.md",
        "selected_row_context_out": parent / f"{stem}_c_discriminating_row_context.json",
        "freeze_out": parent / f"{stem}_c_discriminating_slice_frozen.json",
    }
    for attr, default in _default_selection_paths().items():
        if str(getattr(args, attr)) == str(default):
            value = str(replacements[attr])
            setattr(args, attr, value)
            changed[attr] = value
    return changed


def _uses_shared_dashboard_outputs(args: argparse.Namespace) -> bool:
    shared = {
        str(DEFAULT_OUT),
        str(DEFAULT_AGG_CHECKPOINT),
        str(DEFAULT_AGG_ROW_CONTEXT),
        str(DEFAULT_SELECTION),
        str(DEFAULT_SELECTION_MD),
        str(DEFAULT_SELECTED_ROW_CONTEXT),
        str(DEFAULT_FREEZE),
    }
    observed = {
        str(args.out),
        str(args.aggregate_checkpoint),
        str(args.aggregate_row_context),
        str(args.selection_out),
        str(args.selection_md),
        str(args.selected_row_context_out),
        str(args.freeze_out),
    }
    return bool(shared & observed)


def _forbid_self_correction_shared_outputs(args: argparse.Namespace, *, run_id: str) -> None:
    if not str(run_id or "").startswith("self_correct_"):
        return
    if not _uses_shared_dashboard_outputs(args):
        return
    raise SystemExit(
        "refusing self-correction c-supply run against shared dashboard outputs; "
        "use an isolated --out path so canonical factory state is not overwritten"
    )


def _artifact_role(args: argparse.Namespace, *, run_id: str) -> str:
    if str(args.out or "") == str(DEFAULT_OUT):
        return "canonical"
    if str(run_id or "").startswith("self_correct_"):
        return "self_correction"
    return "diagnostic"


def _artifact_key(prefix: str, *, run_id: str, role: str) -> str:
    if role == "canonical":
        return prefix
    return f"{role}.{prefix}.{_slug(run_id or str(int(time.time())))}"


def _record_batch_artifact_refs(args: argparse.Namespace, result: dict[str, Any]) -> None:
    if not args.out:
        return
    role = _artifact_role(args, run_id=str(result.get("run_id") or ""))
    payload = {
        "status": result.get("status"),
        "run_id": result.get("run_id"),
        "role_rule": "DEFAULT_OUT is canonical; self_correct_* custom outputs are self_correction; other custom outputs are diagnostic",
    }
    refs = [
        ("c_supply_batch_status", args.out, payload),
        ("c_supply_batch_selection", result.get("selection", {}).get("out"), {"run_id": result.get("run_id")}),
        ("c_supply_batch_freeze", result.get("freeze", {}).get("out") if isinstance(result.get("freeze"), dict) else args.freeze_out, {"run_id": result.get("run_id")}),
    ]
    try:
        cx = work_queue.connect(work_queue.DEFAULT_DB)
        for prefix, path, extra in refs:
            if not path:
                continue
            work_queue.record_artifact_ref(
                cx,
                artifact_key=_artifact_key(prefix, run_id=str(result.get("run_id") or ""), role=role),
                role=role,
                path=str(path),
                producer="leanmill_c_supply_batch",
                payload=extra,
                run_id=str(result.get("run_id") or ""),
            )
    except Exception:
        # Artifact registry is observability; the batch result itself remains
        # authoritative only after deterministic consumers re-read the files.
        return


@contextlib.contextmanager
def _shared_output_lock(args: argparse.Namespace):
    lock_file = str(getattr(args, "shared_output_lock", "") or "")
    if not lock_file or not _uses_shared_dashboard_outputs(args):
        yield
        return
    path = Path(lock_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps({"run_id": getattr(args, "run_id", ""), "locked_at_epoch": int(time.time())}, sort_keys=True) + "\n")
        fh.flush()
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _corpus_paths(globs: list[str], *, max_corpora: int, corpus_offset: int = 0) -> list[str]:
    paths: list[Path] = []
    for pattern in globs:
        base = Path(pattern)
        matches = sorted(Path().glob(pattern)) if not base.is_absolute() else sorted(base.parent.glob(base.name))
        paths.extend(p for p in matches if p.is_file())
    # Favor recently generated corpora while keeping deterministic path order among equal mtimes.
    paths = sorted(set(paths), key=lambda p: (-p.stat().st_mtime, str(p)))
    start = max(0, int(corpus_offset))
    end = start + max(0, int(max_corpora))
    return [str(p) for p in paths[start:end]]


def _with_target_resolution(row: dict[str, Any]) -> dict[str, Any]:
    rec = dict(row)
    if str(rec.get("target_resolution_status") or ""):
        return rec
    source_file = str(rec.get("source_file") or rec.get("sorried_file") or "")
    if source_file and Path(source_file).exists() and Path(source_file).is_file():
        rec["target_resolution_status"] = "pass"
        rec["target_resolution_source"] = "c_supply_batch_source_file_exists"
    else:
        rec["target_resolution_status"] = "missing_source_file"
        rec["target_resolution_source"] = "c_supply_batch_source_file_exists"
    return rec


def _merge_rows(corpus_paths: list[str], selected_ids: set[str] | None = None) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in corpus_paths:
        for row in _iter_rows(_read_json(path) or {}):
            rid = _row_id(row)
            if not rid:
                continue
            if selected_ids is not None and rid not in selected_ids:
                continue
            rec = _with_target_resolution(row)
            rec["row_id"] = rid
            rec.setdefault("c_supply_source_corpus", path)
            rows.setdefault(rid, rec)
    return list(rows.values())



def _checkpoint_paths(report_dir: str | Path) -> list[Path]:
    root = Path(report_dir)
    if not root.exists():
        return []
    return sorted(root.glob("*.static_failure_checkpoint.jsonl"))


NON_REUSABLE_STATIC_CACHE_EXITS = {
    "harness_candidate_build_failure",
    "harness_no_candidates",
    "target_kind_audit_failure",
    "wall_timeout_hit",
}


def _is_positive_static_record(rec: dict[str, Any]) -> bool:
    return str(rec.get("learning_exit") or "") in miner.POSITIVE_EXITS


def _is_reusable_static_cache_record(rec: dict[str, Any]) -> bool:
    return str(rec.get("learning_exit") or "") not in NON_REUSABLE_STATIC_CACHE_EXITS


def _better_static_record(current: dict[str, Any] | None, candidate: dict[str, Any]) -> dict[str, Any]:
    if current is None:
        return candidate
    # If any static run found a public-tool positive, that dominates older no-signal
    # records for C-slice safety.
    if _is_positive_static_record(candidate) and not _is_positive_static_record(current):
        return candidate
    if _is_positive_static_record(current) and not _is_positive_static_record(candidate):
        return current
    if bool(candidate.get("supply_candidate")) and not bool(current.get("supply_candidate")):
        return candidate
    return current


def _global_static_cache(report_dir: str | Path) -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    for checkpoint in _checkpoint_paths(report_dir):
        for rec in _read_jsonl(checkpoint):
            if str(rec.get("arm") or "") != "public_tool_static":
                continue
            row_id = str(rec.get("row_id") or "")
            if not row_id:
                continue
            cache[row_id] = _better_static_record(cache.get(row_id), rec)
    return cache


def _seed_checkpoint_from_cache(
    *,
    checkpoint: str | Path,
    corpus_rows: list[dict[str, Any]],
    cache: dict[str, dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    existing = _read_jsonl(checkpoint)
    existing_current = {
        str(rec.get("row_id") or "")
        for rec in existing
        if str(rec.get("run_id") or "") == run_id and str(rec.get("row_id") or "")
    }
    seeded = []
    for row in corpus_rows:
        row_id = _row_id(row)
        if not row_id or row_id in existing_current or row_id not in cache:
            continue
        if not _is_reusable_static_cache_record(cache[row_id]):
            continue
        rec = dict(cache[row_id])
        rec["run_id"] = run_id
        rec["cached_static_result"] = True
        rec["cached_static_result_source_run_id"] = cache[row_id].get("run_id")
        rec["cached_static_result_source_corpus"] = cache[row_id].get("c_supply_source_corpus")
        seeded.append(rec)
        existing_current.add(row_id)
    if seeded:
        p = Path(checkpoint)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as fh:
            for rec in seeded:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return {"seeded_cached_static_results": len(seeded)}

def _build_unlocked(args: argparse.Namespace) -> dict[str, Any]:
    isolated_default_selection_outputs = _isolate_default_selection_outputs_for_custom_status(args)
    policy = _policy_supply(args.factory_policy)
    budget_profile = str(getattr(args, "budget_profile", "") or "")
    budget_profiles = policy.get("budget_profiles") if isinstance(policy.get("budget_profiles"), dict) else {}
    if budget_profile:
        selected_budget = budget_profiles.get(budget_profile)
        if not isinstance(selected_budget, dict):
            raise SystemExit(f"unknown c_supply budget profile: {budget_profile}")
        merged_policy = dict(policy)
        merged_policy.update(selected_budget)
        policy = merged_policy
    source_demand_selection = str(args.source_demand_selection or DEFAULT_SELECTION)
    source_demand_families: list[str] = []
    source_demand_corpus_globs: list[str] = []
    if bool(args.source_demand_only):
        source_demand_families = _source_demand_families(source_demand_selection)
        source_demand_corpus_globs = _source_demand_corpus_globs(source_demand_selection)
    corpus_globs = list(args.corpus_glob or []) or source_demand_corpus_globs or _policy_list(policy, "corpus_globs", DEFAULT_CORPUS_GLOBS)
    max_corpora = int(args.max_corpora if args.max_corpora is not None else _policy_int(policy, "max_corpora_per_batch", 8))
    max_new_rows_per_corpus = int(args.max_new_rows_per_corpus if args.max_new_rows_per_corpus is not None else _policy_int(policy, "max_new_rows_per_corpus", 8))
    corpus_offset = int(args.corpus_offset if args.corpus_offset is not None else _policy_int(policy, "corpus_offset", 0))
    limit_per_corpus = int(args.limit_per_corpus if args.limit_per_corpus is not None else _policy_int(policy, "limit_per_corpus", 40))
    min_signature_hits = int(args.min_signature_hits if args.min_signature_hits is not None else _policy_int(policy, "min_signature_hits", 2))
    min_freeze_rows = int(args.min_freeze_rows if args.min_freeze_rows is not None else _policy_int(policy, "min_freeze_rows", 20))
    max_tool_calls = int(args.max_tool_calls if args.max_tool_calls is not None else _policy_int(policy, "max_tool_calls", 9))
    per_candidate_timeout_s = int(args.per_candidate_timeout_s if args.per_candidate_timeout_s is not None else _policy_int(policy, "per_candidate_timeout_s", 30))
    static_miner_lease_ttl_s = _policy_int(policy, "static_miner_lease_ttl_s", DEFAULT_STATIC_MINER_LEASE_TTL_S)
    wall_timeout_s = int(
        args.wall_timeout_s
        if args.wall_timeout_s is not None
        else _policy_int(policy, "batch_wall_timeout_s", _policy_int(policy, "wall_timeout_s", 180))
    )
    reuse_static_results = bool(args.reuse_static_results_across_runs if args.reuse_static_results_across_runs is not None else policy.get("reuse_static_results_across_runs", True))
    run_id = args.run_id or f"c_supply_batch_{int(time.time())}"
    _forbid_self_correction_shared_outputs(args, run_id=run_id)
    selection_run_id = "" if reuse_static_results else run_id
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    corpora = _corpus_paths(corpus_globs, max_corpora=max_corpora, corpus_offset=corpus_offset)

    batch_started = time.time()
    batch_deadline = batch_started + max(1, wall_timeout_s) if wall_timeout_s > 0 else None
    batch_wall_timeout_hit = False
    reports = []
    aggregate_records: list[dict[str, Any]] = []
    static_cache = _global_static_cache(report_dir)
    for corpus in corpora:
        remaining_wall_s = None if batch_deadline is None else int(batch_deadline - time.time())
        if remaining_wall_s is not None and remaining_wall_s <= 0:
            batch_wall_timeout_hit = True
            break
        corpus_wall_timeout_s = wall_timeout_s if remaining_wall_s is None else max(1, min(wall_timeout_s, remaining_wall_s))
        stem = _slug(Path(corpus).stem)
        checkpoint = report_dir / f"{stem}.static_failure_checkpoint.jsonl"
        report_out = report_dir / f"{stem}.static_failure_report.json"
        report_md = report_dir / f"{stem}.static_failure_report.md"
        corpus_rows = _iter_rows(_read_json(corpus) or {})
        seed_report = _seed_checkpoint_from_cache(
            checkpoint=checkpoint,
            corpus_rows=corpus_rows,
            cache=static_cache,
            run_id=run_id,
        )
        rep = miner.build_report(argparse.Namespace(
            row_context=corpus,
            spec_dir=args.spec_dir,
            checkpoint=str(checkpoint),
            out=str(report_out),
            md=str(report_md),
            run_id=run_id,
            run_root=str(Path(args.run_root) / stem),
            limit=limit_per_corpus,
            max_new_rows=max_new_rows_per_corpus,
            max_tool_calls=max_tool_calls,
            per_candidate_timeout_s=per_candidate_timeout_s,
            wall_timeout_s=corpus_wall_timeout_s,
            min_signature_hits=min_signature_hits,
            report_limit=80,
            skip_any_checkpoint_row=False,
            no_run=bool(args.no_run),
            lease_ttl_s=static_miner_lease_ttl_s,
        ))
        reports.append({
            "corpus": corpus,
            "checkpoint": str(checkpoint),
            "report": str(report_out),
            "md": str(report_md),
            "new_rows_run": rep.get("new_rows_run"),
            "seeded_cached_static_results": seed_report.get("seeded_cached_static_results"),
            "counts": rep.get("counts"),
            "supply_candidate_count": rep.get("supply_candidate_count"),
            "wall_timeout_hit": rep.get("wall_timeout_hit"),
            "corpus_wall_timeout_s": corpus_wall_timeout_s,
        })
        if batch_deadline is not None and time.time() >= batch_deadline:
            batch_wall_timeout_hit = True
            break
        checkpoint_records = _read_jsonl(checkpoint)
        aggregate_records.extend(checkpoint_records)
        for rec in checkpoint_records:
            if str(rec.get("arm") or "") == "public_tool_static" and str(rec.get("row_id") or ""):
                static_cache[str(rec.get("row_id"))] = _better_static_record(static_cache.get(str(rec.get("row_id"))), rec)
    _write_jsonl(args.aggregate_checkpoint, aggregate_records)

    supply_scope_records = aggregate_records if selection_run_id == "" else [rec for rec in aggregate_records if str(rec.get("run_id") or "") == run_id]
    supply_records_for_scope = [rec for rec in supply_scope_records if bool(rec.get("supply_candidate"))]
    supply_ids = {str(rec.get("row_id") or "") for rec in supply_records_for_scope if str(rec.get("row_id") or "")}
    raw_supply_candidate_count = len(supply_records_for_scope)
    duplicate_supply_candidate_count = max(0, raw_supply_candidate_count - len(supply_ids))
    aggregate_rows = _merge_rows(corpora, selected_ids=None)
    Path(args.aggregate_row_context).parent.mkdir(parents=True, exist_ok=True)
    Path(args.aggregate_row_context).write_text(json.dumps({
        "schema": "leanmill-c-supply-batch-row-context-v1",
        "run_id": run_id,
        "source_corpora": corpora,
        "raw_supply_candidate_count": raw_supply_candidate_count,
        "unique_supply_candidate_row_count": len(supply_ids),
        "duplicate_supply_candidate_count": duplicate_supply_candidate_count,
        "supply_candidate_row_ids_from_static_miner": sorted(supply_ids),
        "rows": aggregate_rows,
    }, indent=2, sort_keys=True) + "\n")
    prep_stub = report_dir / "aggregate_prep_order.json"
    prep_stub.write_text(json.dumps({"selected_rows_order": [_row_id(row) for row in aggregate_rows if _row_id(row)]}, indent=2) + "\n")

    selection = c_prep.build(argparse.Namespace(
        checkpoint=args.aggregate_checkpoint,
        run_id=selection_run_id,
        row_context=args.aggregate_row_context,
        prep=str(prep_stub),
        spec_dir=args.spec_dir,
        registry=args.registry,
        out=args.selection_out,
        md=args.selection_md,
        row_context_out=args.selected_row_context_out,
        min_rows=min_freeze_rows,
        limit=args.selection_limit,
        min_rows_per_family=args.min_rows_per_family,
        allow_not_ready=True,
    ))
    freeze_result: dict[str, Any] | None = None
    freeze_marker_reason = "selection_not_ready_or_under_min"
    if selection.get("status") == "ready" and int(selection.get("selected_count") or 0) >= min_freeze_rows:
        freeze_result = freezer.freeze(argparse.Namespace(
            selection=args.selection_out,
            row_context=args.selected_row_context_out,
            out=args.freeze_out,
            label=args.freeze_label or run_id,
            min_rows=min_freeze_rows,
            allow_under_min=False,
            allow_not_ready=False,
        ))
    elif bool(args.freeze_under_min_for_pilot) and int(selection.get("selected_count") or 0) > 0 and selection.get("status") == "ready":
        freeze_result = freezer.freeze(argparse.Namespace(
            selection=args.selection_out,
            row_context=args.selected_row_context_out,
            out=args.freeze_out,
            label=args.freeze_label or f"{run_id}_pilot_under_min",
            min_rows=min_freeze_rows,
            allow_under_min=True,
            allow_not_ready=False,
        ))
    else:
        # Do not leave a stale frozen slice around after stricter eligibility
        # recomputes drop below threshold. Consumers can inspect this marker,
        # but cannot mistake it for a creditable freeze.
        if bool(args.freeze_under_min_for_pilot) and int(selection.get("selected_count") or 0) > 0:
            freeze_marker_reason = "pilot_under_min_selection_not_ready"
        freeze_path = Path(args.freeze_out)
        freeze_path.parent.mkdir(parents=True, exist_ok=True)
        freeze_path.write_text(json.dumps({
            "schema": "leanmill-c-discriminating-slice-frozen-v1",
            "status": "not_frozen",
            "reason": freeze_marker_reason,
            "run_id": run_id,
            "selection_path": args.selection_out,
            "selection_status": selection.get("status"),
            "selected_count": selection.get("selected_count"),
            "eligible_count": selection.get("eligible_count"),
            "min_rows": min_freeze_rows,
            "blockers_by_reason": selection.get("blockers_by_reason"),
            "non_laundering_assertions": {
                "stale_freeze_invalidated": True,
                "creditable_freeze_requires_status_frozen": True,
                "pilot_under_min_requires_ready_selection": True,
            },
        }, indent=2, sort_keys=True) + "\n")
    result = {
        "schema": "leanmill-c-supply-batch-v1",
        "status": "frozen" if freeze_result else "mined_not_frozen",
        "run_id": run_id,
        "selection_run_id_filter": selection_run_id,
        "reuse_static_results_across_runs": reuse_static_results,
        "corpus_globs": corpus_globs,
        "budget_profile": budget_profile or "default",
        "source_demand_routing": {
            "enabled": bool(args.source_demand_only),
            "selection": source_demand_selection if bool(args.source_demand_only) else None,
            "family_count": len(source_demand_families),
            "families": source_demand_families,
            "fallback_to_policy_globs": bool(args.source_demand_only and not source_demand_corpus_globs and not args.corpus_glob),
        },
        "corpus_count": len(corpora),
        "processed_corpus_count": len(reports),
        "batch_wall_timeout_hit": batch_wall_timeout_hit,
        "elapsed_s": round(time.time() - batch_started, 3),
        "corpus_offset": corpus_offset,
        "corpora": corpora,
        "reports": reports,
        "aggregate_checkpoint": args.aggregate_checkpoint,
        "aggregate_row_context": args.aggregate_row_context,
        "isolated_default_selection_outputs": isolated_default_selection_outputs,
        "candidate_accounting": {
            "raw_supply_candidate_count": raw_supply_candidate_count,
            "unique_supply_candidate_row_count": len(supply_ids),
            "duplicate_supply_candidate_count": duplicate_supply_candidate_count,
            "selection_scope": "all_accumulated_static_records" if selection_run_id == "" else "current_run_only",
            "rule": "C-slice threshold counts selection.selected_count after strict gate checks. Raw miner hits are per-corpus hints and may duplicate the same row_id many times.",
        },
        "selection": {
            "out": args.selection_out,
            "md": args.selection_md,
            "status": selection.get("status"),
            "eligible_count": selection.get("eligible_count"),
            "selected_count": selection.get("selected_count"),
            "blockers_by_reason": selection.get("blockers_by_reason"),
            "source_demand_count": len(selection.get("source_demand_requests") or []),
            "static_conflict_row_count": selection.get("static_conflict_row_count"),
            "static_conflict_policy": selection.get("static_conflict_policy"),
        },
        "freeze": None if not freeze_result else {
            "out": args.freeze_out,
            "row_count": freeze_result.get("row_count"),
            "freeze_sha256": freeze_result.get("freeze_sha256"),
        },
        "params": {
            "max_corpora": max_corpora,
            "corpus_offset": corpus_offset,
            "max_new_rows_per_corpus": max_new_rows_per_corpus,
            "limit_per_corpus": limit_per_corpus,
            "min_signature_hits": min_signature_hits,
            "min_freeze_rows": min_freeze_rows,
            "max_tool_calls": max_tool_calls,
            "per_candidate_timeout_s": per_candidate_timeout_s,
            "static_miner_lease_ttl_s": static_miner_lease_ttl_s,
            "batch_wall_timeout_s": wall_timeout_s,
            "wall_timeout_s": wall_timeout_s,
            "no_run": bool(args.no_run),
            "reuse_static_results_across_runs": reuse_static_results,
        },
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.md:
        _write_md(args.md, result)
    _record_batch_artifact_refs(args, result)
    return result


def build(args: argparse.Namespace) -> dict[str, Any]:
    with _shared_output_lock(args):
        return _build_unlocked(args)


def _write_md(path: str | Path, result: dict[str, Any]) -> None:
    lines = [
        "# LeanMill C-Supply Batch",
        "",
        f"- status: `{result['status']}`",
        f"- run_id: `{result['run_id']}`",
        f"- corpus_count: `{result['corpus_count']}`",
        f"- candidate_accounting: `{result.get('candidate_accounting', {})}`",
        f"- selection: `{result['selection']}`",
        f"- freeze: `{result['freeze']}`",
        "",
        "## Reports",
        "",
    ]
    for rep in result["reports"]:
        lines.append(f"- `{Path(rep['corpus']).name}` new_rows=`{rep['new_rows_run']}` supply=`{rep['supply_candidate_count']}` counts=`{rep['counts']}`")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_c_supply_batch_") as td:
        root = Path(td)
        spec = root / "specs"
        spec.mkdir()
        (spec / "fam.yaml").write_text("""
family: fam
status: candidate_family
residual_match:
  head_patterns: [AlphaToken, BetaToken]
templates:
  - id: pos
    row_id: r1
    test_kind: positive
    body_lines: [trivial]
  - id: neg
    row_id: r1
    test_kind: negative_control
    body_lines: [exact False.elim]
""")
        corpus = root / "probe_corpus_family_spec_fam.json"
        corpus.write_text(json.dumps({"rows": [{"row_id": "r1", "source_file": str(root / "r1.lean"), "goal": "AlphaToken BetaToken", "target_resolution_status": "pass"}]}) + "\n")
        (root / "r1.lean").write_text("theorem r1 : True := by\n  trivial\n-- AlphaToken BetaToken\n")
        report_dir = root / "reports"
        ck = report_dir / "probe_corpus_family_spec_fam.static_failure_checkpoint.jsonl"
        report_dir.mkdir()
        ck.write_text(json.dumps({"run_id": "batch", "row_id": "r1", "arm": "public_tool_static", "learning_exit": "tested_no_positive_signal", "attempt_count": 2, "supply_candidate": True}) + "\n")
        result = build(argparse.Namespace(
            factory_policy=str(root / "missing_policy.json"),
            budget_profile="",
            corpus_glob=[str(corpus)],
            max_corpora=1,
            corpus_offset=0,
            source_demand_only=False,
            source_demand_selection="",
            max_new_rows_per_corpus=0,
            limit_per_corpus=10,
            min_signature_hits=2,
            min_freeze_rows=1,
            max_tool_calls=3,
            per_candidate_timeout_s=5,
            wall_timeout_s=20,
            spec_dir=str(spec),
            registry=str(root / "registry.json"),
            aggregate_checkpoint=str(root / "agg.jsonl"),
            aggregate_row_context=str(root / "agg_rows.json"),
            selection_out=str(root / "sel.json"),
            selection_md=str(root / "sel.md"),
            selected_row_context_out=str(root / "sel_rows.json"),
            freeze_out=str(root / "freeze.json"),
            freeze_label="test",
            report_dir=str(report_dir),
            run_root=str(root / "run"),
            run_id="batch",
            selection_limit=20,
            min_rows_per_family=1,
            freeze_under_min_for_pilot=False,
            no_run=True,
            reuse_static_results_across_runs=True,
            out=None,
            md=None,
            shared_output_lock=str(root / "lock"),
        ))
        assert result["status"] == "mined_not_frozen", result
        assert result["selection"]["selected_count"] == 1, result
        assert result["selection"]["status"] == "blocked_pending_probe_or_static_sweep", result
        pilot_result = build(argparse.Namespace(
            factory_policy=str(root / "missing_policy.json"),
            budget_profile="",
            corpus_glob=[str(corpus)],
            max_corpora=1,
            corpus_offset=0,
            source_demand_only=False,
            source_demand_selection="",
            max_new_rows_per_corpus=0,
            limit_per_corpus=10,
            min_signature_hits=2,
            min_freeze_rows=2,
            max_tool_calls=3,
            per_candidate_timeout_s=5,
            wall_timeout_s=20,
            spec_dir=str(spec),
            registry=str(root / "registry.json"),
            aggregate_checkpoint=str(root / "agg_pilot.jsonl"),
            aggregate_row_context=str(root / "agg_pilot_rows.json"),
            selection_out=str(root / "sel_pilot.json"),
            selection_md=str(root / "sel_pilot.md"),
            selected_row_context_out=str(root / "sel_pilot_rows.json"),
            freeze_out=str(root / "freeze_pilot.json"),
            freeze_label="test_pilot",
            report_dir=str(report_dir),
            run_root=str(root / "run_pilot"),
            run_id="batch_pilot",
            selection_limit=20,
            min_rows_per_family=1,
            freeze_under_min_for_pilot=True,
            no_run=True,
            reuse_static_results_across_runs=True,
            out=None,
            md=None,
            shared_output_lock=str(root / "lock"),
        ))
        assert pilot_result["status"] == "mined_not_frozen", pilot_result
        pilot_freeze = _read_json(root / "freeze_pilot.json")
        assert pilot_freeze["status"] == "not_frozen", pilot_freeze
        assert pilot_freeze["reason"] == "pilot_under_min_selection_not_ready", pilot_freeze
        demand_sel = root / "demand_selection.json"
        demand_sel.write_text(json.dumps({"source_demand_requests": [{"family": "fam", "recommended_action": "source_similar_static_fail_rows"}]}) + "\n")
        assert _source_demand_families(demand_sel) == ["fam"]
        assert _source_demand_corpus_globs(demand_sel)[0].endswith("probe_corpus_family_spec_fam_*.json")
        resolved_rows = _merge_rows([str(corpus)])
        assert resolved_rows and resolved_rows[0]["target_resolution_status"] == "pass", resolved_rows
        missing_resolved = _with_target_resolution({"row_id": "missing", "source_file": str(root / "missing.lean")})
        assert missing_resolved["target_resolution_status"] == "missing_source_file", missing_resolved
        assert _is_reusable_static_cache_record({"learning_exit": "tested_no_positive_signal"}) is True
        assert _is_reusable_static_cache_record({"learning_exit": "harness_candidate_build_failure"}) is False
        cache_seed = root / "cache_seed.jsonl"
        cache_seed.write_text(json.dumps({"run_id": "old", "row_id": "r1", "arm": "public_tool_static", "learning_exit": "harness_candidate_build_failure"}) + "\n")
        skipped_seed = _seed_checkpoint_from_cache(checkpoint=root / "cache_target.jsonl", corpus_rows=[{"row_id": "r1"}], cache={"r1": {"run_id": "old", "row_id": "r1", "arm": "public_tool_static", "learning_exit": "harness_candidate_build_failure"}}, run_id="new")
        assert skipped_seed["seeded_cached_static_results"] == 0, skipped_seed
        conflict_out = root / "conflict.jsonl"
        _write_jsonl(conflict_out, [
            {"run_id": "r", "row_id": "x", "arm": "public_tool_static", "learning_exit": "tested_no_positive_signal"},
            {"run_id": "r", "row_id": "x", "arm": "public_tool_static", "learning_exit": "raw_closure_candidate"},
        ])
        written = _read_jsonl(conflict_out)
        assert len(written) == 1 and written[0]["learning_exit"] == "raw_closure_candidate", written
        shared_args = argparse.Namespace(
            out=DEFAULT_OUT,
            aggregate_checkpoint=str(root / "custom.jsonl"),
            aggregate_row_context=str(root / "custom_rows.json"),
            selection_out=str(root / "custom_sel.json"),
            selection_md=str(root / "custom_sel.md"),
            selected_row_context_out=str(root / "custom_sel_rows.json"),
            freeze_out=str(root / "custom_freeze.json"),
        )
        assert _uses_shared_dashboard_outputs(shared_args) is True
        try:
            _forbid_self_correction_shared_outputs(shared_args, run_id="self_correct_c_supply_test")
        except SystemExit as exc:
            assert "refusing self-correction" in str(exc)
        else:
            raise AssertionError("self-correction shared output guard did not fire")
        isolated_args = argparse.Namespace(
            out=str(root / "custom_status.json"),
            aggregate_checkpoint=str(root / "custom.jsonl"),
            aggregate_row_context=str(root / "custom_rows.json"),
            selection_out=str(root / "custom_sel.json"),
            selection_md=str(root / "custom_sel.md"),
            selected_row_context_out=str(root / "custom_sel_rows.json"),
            freeze_out=str(root / "custom_freeze.json"),
        )
        assert _uses_shared_dashboard_outputs(isolated_args) is False
        custom_status_args = argparse.Namespace(**vars(isolated_args))
        custom_status_args.out = str(root / "diagnostic_status.json")
        changed = _isolate_default_selection_outputs_for_custom_status(custom_status_args)
        assert changed == {}, changed
        default_selection_args = argparse.Namespace(
            out=str(root / "diagnostic_status.json"),
            aggregate_checkpoint=DEFAULT_AGG_CHECKPOINT,
            aggregate_row_context=DEFAULT_AGG_ROW_CONTEXT,
            selection_out=DEFAULT_SELECTION,
            selection_md=DEFAULT_SELECTION_MD,
            selected_row_context_out=DEFAULT_SELECTED_ROW_CONTEXT,
            freeze_out=DEFAULT_FREEZE,
        )
        changed = _isolate_default_selection_outputs_for_custom_status(default_selection_args)
        assert changed["selection_out"].endswith("diagnostic_status_c_discriminating_slice.json"), changed
        assert default_selection_args.selection_out != DEFAULT_SELECTION
    print("leanmill_c_supply_batch self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--budget-profile", default="")
    ap.add_argument("--corpus-glob", action="append", default=[])
    ap.add_argument("--max-corpora", type=int, default=None)
    ap.add_argument("--corpus-offset", type=int, default=None)
    ap.add_argument("--source-demand-only", action="store_true")
    ap.add_argument("--source-demand-selection", default=DEFAULT_SELECTION)
    ap.add_argument("--max-new-rows-per-corpus", type=int, default=None)
    ap.add_argument("--limit-per-corpus", type=int, default=None)
    ap.add_argument("--min-signature-hits", type=int, default=None)
    ap.add_argument("--min-freeze-rows", type=int, default=None)
    ap.add_argument("--max-tool-calls", type=int, default=None)
    ap.add_argument("--per-candidate-timeout-s", type=int, default=None)
    ap.add_argument("--wall-timeout-s", type=int, default=None)
    ap.add_argument("--spec-dir", default=miner.DEFAULT_SPEC_DIR)
    ap.add_argument("--registry", default=c_prep.REPAIR_FAMILY_REGISTRY)
    ap.add_argument("--aggregate-checkpoint", default=DEFAULT_AGG_CHECKPOINT)
    ap.add_argument("--aggregate-row-context", default=DEFAULT_AGG_ROW_CONTEXT)
    ap.add_argument("--selection-out", default=DEFAULT_SELECTION)
    ap.add_argument("--selection-md", default=DEFAULT_SELECTION_MD)
    ap.add_argument("--selected-row-context-out", default=DEFAULT_SELECTED_ROW_CONTEXT)
    ap.add_argument("--freeze-out", default=DEFAULT_FREEZE)
    ap.add_argument("--freeze-label", default="")
    ap.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    ap.add_argument("--run-root", default="/tmp/rung1/leanmill_c_supply_batch")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--selection-limit", type=int, default=50)
    ap.add_argument("--min-rows-per-family", type=int, default=3)
    ap.add_argument("--freeze-under-min-for-pilot", action="store_true")
    ap.add_argument("--shared-output-lock", default=DEFAULT_SHARED_OUTPUT_LOCK)
    ap.add_argument("--reuse-static-results-across-runs", action=argparse.BooleanOptionalAction, default=None)
    ap.add_argument("--no-run", action="store_true")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = build(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "status": result["status"],
        "run_id": result["run_id"],
        "corpus_count": result["corpus_count"],
        "selection": result["selection"],
        "freeze": result["freeze"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
