#!/usr/bin/env python3
"""Mine candidate new LeanMill repair families from ex-post static failures.

This is a planning lane only by default. It reads completed static-tool failures,
clusters rows not well-covered by existing repair-family signatures, and emits
family-birth candidates with explicit no-credit boundaries. It does not run Lean,
write repair-family YAML, or enqueue agents unless --enqueue is passed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from ztare.leanmill.contracts import source_family_match
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
    from ztare.leanmill.contracts import source_family_match

import leanmill_static_failure_miner as static_miner
import leanmill_family_specs as family_specs
import leanmill_work_queue as work_queue
import leanmill_runtime_router as runtime_router
import leanmill_operator_contracts as operator_contracts
from leanmill_factory_config import FACTORY_POLICY, priority_value
from leanmill_paths import DATA_DIR

DEFAULT_SELECTION = f"{DATA_DIR}/c_supply_batch_c_discriminating_slice.json"
DEFAULT_CHECKPOINT = f"{DATA_DIR}/c_supply_batch_checkpoint.jsonl"
DEFAULT_ROW_CONTEXT = f"{DATA_DIR}/c_supply_batch_row_context.json"
DEFAULT_SPEC_DIR = family_specs.DEFAULT_SPEC_DIR
DEFAULT_OUT = f"{DATA_DIR}/family_birth_candidates.json"
DEFAULT_MD = f"{DATA_DIR}/family_birth_candidates.md"
DEFAULT_FACTORY_INTELLIGENCE = f"{DATA_DIR}/leanmill_factory_intelligence.json"
FAMILY_BIRTH_CONTRACT_REVISION = "family_birth_schema_feedback_v3"
STRICT_NO_SIGNAL = {"tested_no_positive_signal"}
POSITIVE_EXITS = static_miner.POSITIVE_EXITS
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_']+")
EXTRA_GENERIC_TOKENS = {
    "lean", "mathlib", "theorem", "lemma", "proof", "true", "false", "type", "sort",
    "copyright", "authors", "author", "apache", "license", "released", "rights", "reserved",
    "analysis", "algebra", "public", "module", "import", "dedup", "complete", "after",
    "mcb", "candidate", "source", "file", "target", "unknown", "row", "by", "have",
    "show", "exact", "using", "simpa", "simp", "rw", "intro", "apply", "fun", "let",
    "def", "import", "namespace", "section", "variable", "variables", "class", "instance",
    "described", "this", "that", "with", "from", "then", "where", "main", "basic",
    "expose", "exposes", "inst", "spaces", "comm", "group", "noncomputable",
    "scoped", "symm", "only", "local", "notation", "sorry", "normed", "space",
    "convert", "refine", "calc", "cases", "cast", "ring",
}


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
    out: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _priority_base(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", FACTORY_POLICY),
        namespace="formula_bases",
        key=key,
        fallback=fallback,
    )


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value)).strip("_") or "item"


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("target_id") or "")


def _iter_rows(obj: Any) -> list[dict[str, Any]]:
    return static_miner._iter_rows(obj)


def _strip_lean_noise(text: str) -> str:
    text = re.sub(r"/-.*?-\/", " ", text, flags=re.S)
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--") or stripped.startswith("import ") or stripped.startswith("public import "):
            continue
        cut = line.find("--")
        if cut >= 0:
            line = line[:cut]
        kept.append(line)
    return "\n".join(kept)


def _declaration_names(text: str) -> list[str]:
    clean = _strip_lean_noise(text)
    names: list[str] = []
    for match in re.finditer(r"\b(?:theorem|lemma|def|abbrev|structure|class|instance)\s+([A-Za-z0-9_'.]+)", clean):
        names.append(match.group(1))
    return names


def _row_haystack(row: dict[str, Any]) -> str:
    parts = [str(row.get(k) or "") for k in (
        "row_id",
        "target_theorem_name",
        "theorem_name",
        "goal",
        "source_hinge",
        "statement",
        "formal_statement",
    )]
    source_file = str(row.get("source_file") or row.get("sorried_file") or "")
    if source_file:
        path = Path(source_file)
        if path.exists() and path.is_file():
            try:
                parts.append(_strip_lean_noise(path.read_text(errors="ignore"))[:4000])
            except OSError:
                pass
    return "\n".join(parts)


def _split_identifier(token: str) -> list[str]:
    token = token.replace("'", "")
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", token).replace("_", " ").split()
    return [p.lower() for p in parts if p]


def _distinctive_tokens(text: str) -> set[str]:
    generic = set(static_miner.GENERIC_SIGNATURE_TOKENS).union(EXTRA_GENERIC_TOKENS)
    out: set[str] = set()
    for raw in TOKEN_RE.findall(text):
        for tok in _split_identifier(raw):
            if tok in generic or len(tok) < 4 or tok.isdigit():
                continue
            if tok.startswith("mcb"):
                continue
            out.add(tok)
    return out


def _existing_family_patterns(spec_dir: str | Path, *, allowed_statuses: set[str] | None = None) -> set[str]:
    tokens: set[str] = set()
    for spec in family_specs.load_specs(spec_dir):
        if allowed_statuses is not None and str(spec.get("status") or "") not in allowed_statuses:
            continue
        residual = spec.get("residual_match") if isinstance(spec.get("residual_match"), dict) else {}
        for pat in residual.get("head_patterns") or []:
            tokens.update(_distinctive_tokens(str(pat)))
    return tokens


def _selection_selected_rows(selection: dict[str, Any]) -> set[str]:
    out = {str(x) for x in selection.get("selected_rows_order") or [] if str(x)}
    for key in ("rows", "selected_rows"):
        for row in selection.get(key) or []:
            if isinstance(row, dict) and row.get("eligible") is True and str(row.get("row_id") or ""):
                out.add(str(row.get("row_id") or ""))
    return out


def _selection_birth_pressure_rows(selection: dict[str, Any]) -> dict[str, list[str]]:
    pressure_reasons = {"no_positive_family_template", "family_template_not_top_static_match"}
    out: dict[str, list[str]] = {}
    for row in selection.get("rows") or []:
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("row_id") or "")
        reasons = [str(r) for r in (row.get("rejection_reasons") or []) if str(r)]
        matched = sorted(set(reasons).intersection(pressure_reasons))
        if row_id and matched:
            out[row_id] = matched
    return out


def _best_existing_match(rec: dict[str, Any]) -> dict[str, Any] | None:
    matches = [m for m in rec.get("family_matches") or [] if isinstance(m, dict) and str(m.get("family") or "")]
    if not matches:
        return None
    matches.sort(key=lambda m: (-float(m.get("confidence") or 0.0), -int(m.get("hit_count") or 0), str(m.get("family") or "")))
    return matches[0]


def _static_positive_rows(records: list[dict[str, Any]]) -> set[str]:
    return {str(r.get("row_id") or "") for r in records if str(r.get("arm") or "") == "public_tool_static" and str(r.get("learning_exit") or "") in POSITIVE_EXITS}


def _factory_intelligence_context(path: str | Path = DEFAULT_FACTORY_INTELLIGENCE) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return {
            "schema": "leanmill-upstream-factory-intelligence-context-v1",
            "available": False,
            "path": str(path),
        }
    credit = payload.get("c_supply_credit_ready_read_model") if isinstance(payload.get("c_supply_credit_ready_read_model"), dict) else {}
    gate = payload.get("family_spec_gate") if isinstance(payload.get("family_spec_gate"), dict) else {}
    target = payload.get("target_resolution_read_model") if isinstance(payload.get("target_resolution_read_model"), dict) else {}
    lifecycle = payload.get("family_supply_lifecycle") if isinstance(payload.get("family_supply_lifecycle"), dict) else {}
    recommendations = payload.get("recommendations") if isinstance(payload.get("recommendations"), list) else []
    return {
        "schema": "leanmill-upstream-factory-intelligence-context-v1",
        "available": True,
        "path": str(path),
        "credit_ready_count": int(credit.get("credit_ready_count") or 0),
        "remaining_to_target": int(credit.get("remaining_to_target") or 0),
        "credit_ready_family_counts": credit.get("credit_ready_family_counts") or {},
        "blockers_by_reason": credit.get("blockers_by_reason") or {},
        "family_spec_gate_status": gate.get("status"),
        "family_spec_gate_failure_count": int(gate.get("failure_count") or 0),
        "target_resolution_open_missing_count": int(target.get("open_missing_target_metadata_count") or 0),
        "target_resolution_risk_classes": target.get("risk_classes") or [],
        "open_family_birth_count": int(lifecycle.get("open_family_birth_count") or 0),
        "open_family_generalize_count": int(lifecycle.get("open_family_generalize_count") or 0),
        "top_recommendation_classes": [
            str(item.get("class") or "")
            for item in recommendations[:6]
            if isinstance(item, dict) and str(item.get("class") or "")
        ],
        "routing_rule": (
            "Prefer reusable new-family breadth from strict static-no-signal rows that can produce "
            "positive plus matched negative-control templates; this context is routing evidence, not proof credit."
        ),
        "avoid": [
            "duplicating an existing family signature",
            "static-positive rows for C-discriminating supply",
            "rows without concrete target binding",
            "single-row families unless the task is explicitly retired or seed_only",
            "unmatched negatives or syntax-only negative controls",
        ],
    }


def _candidate_records(args: argparse.Namespace, rows_by_id: dict[str, dict[str, Any]], selected_rows: set[str], birth_pressure_rows: dict[str, list[str]]) -> list[dict[str, Any]]:
    records = _read_jsonl(args.checkpoint)
    positive_rows = _static_positive_rows(records)
    latest_by_row: dict[str, dict[str, Any]] = {}
    for rec in records:
        if str(rec.get("arm") or "") != "public_tool_static":
            continue
        if str(rec.get("learning_exit") or "") not in STRICT_NO_SIGNAL:
            continue
        row_id = str(rec.get("row_id") or "")
        if not row_id or row_id in selected_rows or row_id in positive_rows:
            continue
        if row_id not in rows_by_id:
            continue
        best = _best_existing_match(rec)
        pressure_reasons = birth_pressure_rows.get(row_id) or []
        covered_by_existing = bool(best and float(best.get("confidence") or 0.0) >= float(args.existing_family_confidence_floor) and int(best.get("hit_count") or 0) >= int(args.existing_family_hit_floor))
        if covered_by_existing and not pressure_reasons and not bool(args.include_covered_static_failures):
            continue
        rec = dict(rec)
        rec["family_birth_pressure_reasons"] = pressure_reasons
        rec["best_existing_family_match"] = best
        prev = latest_by_row.get(row_id)
        if prev is None or int(rec.get("attempt_count") or 0) >= int(prev.get("attempt_count") or 0):
            latest_by_row[row_id] = rec
    return list(latest_by_row.values())


def _cluster_candidates(args: argparse.Namespace, candidates: list[dict[str, Any]], rows_by_id: dict[str, dict[str, Any]], existing_tokens: set[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    row_tokens: dict[str, set[str]] = {}
    raw_row_tokens: dict[str, set[str]] = {}
    for rec in candidates:
        row_id = str(rec.get("row_id") or "")
        raw_tokens = _distinctive_tokens(_row_haystack(rows_by_id[row_id]))
        raw_row_tokens[row_id] = raw_tokens
        row_tokens[row_id] = raw_tokens.difference(existing_tokens if bool(args.exclude_existing_family_tokens) else set())
    token_to_rows: dict[str, set[str]] = defaultdict(set)
    for row_id, toks in row_tokens.items():
        for tok in toks:
            token_to_rows[tok].add(row_id)
    seed_tokens = [tok for tok, rows in token_to_rows.items() if len(rows) >= int(args.min_rows)]
    diagnostic = {
        "schema": "leanmill-family-birth-cluster-diagnostics-v1",
        "candidate_count": len(candidates),
        "rows_with_raw_tokens": sum(1 for toks in raw_row_tokens.values() if toks),
        "rows_with_tokens_after_existing_filter": sum(1 for toks in row_tokens.values() if toks),
        "existing_family_token_count": len(existing_tokens),
        "token_row_counts_top": [
            {"token": tok, "row_count": len(rows)}
            for tok, rows in sorted(token_to_rows.items(), key=lambda item: (-len(item[1]), item[0]))[:20]
        ],
        "min_rows": int(args.min_rows),
        "min_shared_tokens": int(args.min_shared_tokens),
        "exclude_existing_family_tokens": bool(args.exclude_existing_family_tokens),
    }
    clusters_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    for seed in seed_tokens:
        rows = set(token_to_rows[seed])
        shared = {seed}
        for tok, tok_rows in token_to_rows.items():
            if tok == seed:
                continue
            if len(rows.intersection(tok_rows)) >= int(args.min_rows):
                shared.add(tok)
        rows = {rid for rid in rows if len(row_tokens.get(rid, set()).intersection(shared)) >= int(args.min_shared_tokens)}
        if len(rows) < int(args.min_rows) or len(shared) < int(args.min_shared_tokens):
            continue
        key_tokens = tuple(sorted(shared, key=lambda t: (-len(token_to_rows[t].intersection(rows)), t))[: max(2, int(args.max_signature_tokens))])
        if key_tokens in clusters_by_key:
            clusters_by_key[key_tokens]["row_ids"] = sorted(set(clusters_by_key[key_tokens]["row_ids"]).union(rows))
            continue
        proposed_family = _slug("_".join(key_tokens[:3]) + "_planner")
        clusters_by_key[key_tokens] = {
            "proposed_family": proposed_family,
            "signature_tokens": list(key_tokens),
            "row_ids": sorted(rows),
            "birth_status": "candidate_only_no_credit",
            "evidence_rule": "static public tools produced tested_no_positive_signal; existing family match below threshold; rows share distinctive tokens",
        }
    clusters = []
    for cluster in clusters_by_key.values():
        rows = cluster["row_ids"]
        cluster["row_count"] = len(rows)
        cluster["rows"] = [
            {
                "row_id": rid,
                "source_file": rows_by_id[rid].get("source_file") or rows_by_id[rid].get("sorried_file"),
                "target_theorem_name": rows_by_id[rid].get("target_theorem_name"),
                "token_hits": sorted(row_tokens.get(rid, set()).intersection(set(cluster["signature_tokens"]))),
            }
            for rid in rows[: int(args.max_rows_per_cluster)]
        ]
        cluster["required_birth_receipt"] = {
            "min_rows": int(args.min_rows),
            "min_shared_tokens": int(args.min_shared_tokens),
            "requires_positive_template_per_row": True,
            "requires_matched_negative_control_per_row": True,
            "requires_no_static_public_positive": True,
            "requires_heldout_or_sibling_before_benchmark_credit": True,
        }
        clusters.append(cluster)
    clusters.sort(key=lambda c: (-int(c.get("row_count") or 0), -len(c.get("signature_tokens") or []), str(c.get("proposed_family") or "")))
    clusters = clusters[: max(0, int(args.max_clusters))]
    diagnostic["cluster_count"] = len(clusters)
    return clusters, diagnostic


def _existing_family_birth_work(cx: Any, *, family: str, row_ids: list[str], cooldown_s: int, contract_revision: str) -> dict[str, Any] | None:
    now = int(time.time())
    row_set = set(row_ids)
    for work_id, status, updated_at, payload_json in cx.execute(
        "SELECT work_id, status, updated_at, payload_json FROM work_items WHERE kind='agent_repair_task'"
    ).fetchall():
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("family_spec_patch_mode") or "") != "family_birth_candidate":
            continue
        if str(payload.get("family") or "") != family:
            continue
        existing_rows = set(str(x) for x in (payload.get("family_birth_candidate_rows") or []) if str(x))
        same_cluster = bool(row_set) and existing_rows == row_set
        existing_revision = str(payload.get("family_birth_contract_revision") or "")
        if status in {"queued", "claimed", "running"}:
            return {"work_id": work_id, "status": status, "reason": "open_family_birth_exists"}
        if same_cluster and status in {"done", "retired"}:
            return {"work_id": work_id, "status": status, "reason": "terminal_same_cluster_family_birth_exists"}
        if same_cluster and status == "failed" and existing_revision == contract_revision:
            return {"work_id": work_id, "status": status, "reason": "failed_same_cluster_current_contract_exists"}
        if cooldown_s > 0 and now - int(updated_at or 0) < cooldown_s and existing_revision == contract_revision:
            return {"work_id": work_id, "status": status, "reason": "family_birth_cooldown_active"}
    return None


def _enqueue_jobs(args: argparse.Namespace, clusters: list[dict[str, Any]], run_id: str, factory_context: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not args.enqueue:
        return [], []
    cx = work_queue.connect(args.queue_db)
    planned_runtime_counts: dict[str, int] = {}
    enqueued: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for cluster in clusters[: max(0, int(args.max_enqueued))]:
        family = str(cluster.get("proposed_family") or "")
        target_path = str(Path(args.spec_dir) / f"{_slug(family)}.yaml")
        cluster_rows = [row for row in (cluster.get("rows") or []) if isinstance(row, dict)]
        row_ids = [str(row.get("row_id") or "") for row in cluster_rows if str(row.get("row_id") or "")]
        if Path(target_path).exists():
            skipped.append({"family": family, "target_path": target_path, "reason": "target_family_yaml_already_exists"})
            continue
        existing = _existing_family_birth_work(cx, family=family, row_ids=row_ids, cooldown_s=int(args.cooldown_s), contract_revision=FAMILY_BIRTH_CONTRACT_REVISION)
        if existing:
            skipped.append({"family": family, "row_ids": row_ids, **existing})
            continue
        routing = runtime_router.select_runtime(
            requested_runtime=args.agent_runtime,
            queue_db=args.queue_db,
            policy_path=args.factory_policy,
            policy_profile=args.policy_profile,
            route_key=f"family_birth:{family}:{','.join(cluster.get('row_ids') or [])}",
            planned_counts=planned_runtime_counts,
            events_path=args.events,
        )
        runtime = str(routing.get("selected_runtime") or args.agent_runtime)
        planned_runtime_counts[runtime] = planned_runtime_counts.get(runtime, 0) + 1
        cluster_signature = hashlib.sha256((family + "|" + "|".join(sorted(row_ids))).encode("utf-8")).hexdigest()[:16]
        work_id = f"family_birth_candidate:{family}:{cluster_signature}"
        operator_contract = operator_contracts.family_birth_candidate_contract(
            family=family,
            cluster_rows=cluster_rows,
            target_path=target_path,
            cluster=cluster,
            contract_id=f"family_birth_candidate:{family}:{run_id}",
        )
        task = (
            "Create a new LeanMill repair-family YAML candidate only if the cluster supports a reusable family. "
            "Follow the operator_contract action program exactly. The family must be data-only, source/clean-solver credit false, and candidate_family or seed_only. "
            "For each included row add one positive template and one substantively matched negative_control template. "
            "Do not claim proof value, do not edit scoreboards or registries, and do not edit outside the target YAML. "
            "Use factory_intelligence_context only for routing and prioritization; it is not proof evidence and must not be cited as credit. "
            "If the cluster is too weak or overfit, do not edit; emit terminal JSON with exit_kind operator_required or retired. "
            f"Target YAML: {target_path}. Factory intelligence context: {json.dumps(factory_context, sort_keys=True)}. "
            f"Cluster: {json.dumps(cluster, sort_keys=True)}"
        )
        payload = {
            "work_id": work_id,
            "runtime": runtime,
            "agent_id": f"leanmill_{runtime}_family_birth_candidate",
            "runtime_routing_receipt": routing,
            "family_birth_contract_revision": FAMILY_BIRTH_CONTRACT_REVISION,
            "station": "repair_registry",
            "family": family,
            "task": task,
            "expected_exit": "family_spec_patch",
            "allowed_paths": [target_path, "/tmp/rung1"],
            "allowed_write_paths": [target_path],
            "requires_negative_control": True,
            "negative_control": "Every born-family row must include a matched negative_control template that should fail when the proposed family-specific bridge/direction/source ingredient is removed or reversed.",
            "proof_affecting": False,
            "max_iterations": args.agent_max_iterations,
            "max_wall_time_s": args.agent_max_wall_time_s,
            "max_family_spec_feedback_retries": 1,
            "family_spec_patch_target": target_path,
            "family_spec_patch_mode": "family_birth_candidate",
            "family_birth_cluster": cluster,
            "family_birth_activation_row_context": str(args.row_context),
            "family_birth_candidate_rows": [str(row.get("row_id") or "") for row in cluster_rows if str(row.get("row_id") or "")],
            "family_birth_candidates": cluster_rows,
            "factory_intelligence_context": factory_context,
            "operator_contract": operator_contract,
            "replenish_group": f"family_birth_candidate:{family}",
        }
        work_queue.enqueue(
            cx,
            kind="agent_repair_task",
            priority=_priority_base(args, "family_birth_candidate", 225) + int(cluster.get("row_count") or 0),
            payload=payload,
            max_attempts=2,
        )
        work_queue.append_event(args.events, {"event_type": "family_birth_candidate_enqueued", "work_id": work_id, "payload": {"family": family, "row_ids": cluster.get("row_ids")}})
        enqueued.append({"work_id": work_id, "family": family, "runtime": runtime, "target_path": target_path, "row_ids": cluster.get("row_ids")})
    return enqueued, skipped


def build(args: argparse.Namespace) -> dict[str, Any]:
    selection = _read_json(args.selection) or {}
    rows_by_id = {_row_id(row): row for row in _iter_rows(_read_json(args.row_context) or {}) if _row_id(row)}
    selected_rows = _selection_selected_rows(selection)
    birth_pressure_rows = _selection_birth_pressure_rows(selection)
    family_match_policy = source_family_match.policy_from_factory_policy(
        _read_json(getattr(args, "factory_policy", FACTORY_POLICY)) or {},
        profile=str(getattr(args, "policy_profile", "") or ""),
    )
    existing_tokens = _existing_family_patterns(args.spec_dir, allowed_statuses=set(family_match_policy.allowed_statuses))
    factory_context = _factory_intelligence_context()
    candidates = _candidate_records(args, rows_by_id, selected_rows, birth_pressure_rows)
    clusters, cluster_diagnostics = _cluster_candidates(args, candidates, rows_by_id, existing_tokens)
    run_id = args.run_id or str(int(time.time()))
    enqueued, skipped = _enqueue_jobs(args, clusters, run_id, factory_context)
    result = {
        "schema": "leanmill-family-birth-miner-v1",
        "run_id": run_id,
        "dry_run": not args.enqueue,
        "selection": args.selection,
        "checkpoint": args.checkpoint,
        "row_context": args.row_context,
        "spec_dir": args.spec_dir,
        "candidate_static_fail_row_count": len(candidates),
        "birth_pressure_row_count": len(birth_pressure_rows),
        "cluster_count": len(clusters),
        "cluster_diagnostics": cluster_diagnostics,
        "existing_family_token_policy": {
            "source_family_match_policy": family_match_policy.as_receipt(),
            "rule": "Family-birth token suppression uses only candidate_family-or-stronger existing family statuses. Seed-only families no longer erase birth evidence because they are not conversion-eligible downstream.",
        },
        "clusters": clusters,
        "enqueued": len(enqueued),
        "enqueued_jobs": enqueued,
        "factory_intelligence_context": factory_context,
        "thresholds": {
            "existing_family_confidence_floor": float(args.existing_family_confidence_floor),
            "existing_family_hit_floor": int(args.existing_family_hit_floor),
            "min_rows": int(args.min_rows),
            "min_shared_tokens": int(args.min_shared_tokens),
        },
        "credit_boundary": "family birth candidates create no proof credit and no benchmark credit until YAML gate, positive/negative pairs, static-fail evidence, and heldout/sibling checks pass",
    }
    if args.out:
        _write_json(args.out, result)
    if args.md:
        _write_md(args.md, result)
    return result


def _write_md(path: str | Path, result: dict[str, Any]) -> None:
    lines = [
        "# LeanMill Family Birth Candidates",
        "",
        f"- run_id: `{result['run_id']}`",
        f"- dry_run: `{result['dry_run']}`",
        f"- candidate_static_fail_row_count: `{result['candidate_static_fail_row_count']}`",
        f"- birth_pressure_row_count: `{result.get('birth_pressure_row_count')}`",
        f"- cluster_count: `{result['cluster_count']}`",
        "",
        "| proposed family | rows | signature tokens | status |",
        "|---|---:|---|---|",
    ]
    for cluster in result.get("clusters") or []:
        lines.append("| " + " | ".join([
            str(cluster.get("proposed_family")),
            str(cluster.get("row_count")),
            ",".join(cluster.get("signature_tokens") or []),
            str(cluster.get("birth_status")),
        ]) + " |")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_family_birth_") as td:
        root = Path(td)
        src = root / "rows.lean"
        src.write_text("""
theorem r1 : True := by
  -- FrobnicateBridge OrbitalLift
  trivial
theorem r2 : True := by
  -- FrobnicateBridge OrbitalLift
  trivial
theorem r3 : True := by
  -- FrobnicateBridge OrbitalLift
  trivial
""")
        row_context = root / "rows.json"
        row_context.write_text(json.dumps({"rows": [
            {"row_id": "FrobnicateBridge_OrbitalLift_r1", "goal": "FrobnicateBridge OrbitalLift", "source_file": str(src)},
            {"row_id": "FrobnicateBridge_OrbitalLift_r2", "goal": "FrobnicateBridge OrbitalLift", "source_file": str(src)},
            {"row_id": "FrobnicateBridge_OrbitalLift_r3", "goal": "FrobnicateBridge OrbitalLift", "source_file": str(src)},
        ]}) + "\n")
        checkpoint = root / "ck.jsonl"
        checkpoint.write_text("".join(json.dumps({"arm": "public_tool_static", "row_id": rid, "learning_exit": "tested_no_positive_signal", "attempt_count": 3, "family_matches": []}) + "\n" for rid in ("FrobnicateBridge_OrbitalLift_r1", "FrobnicateBridge_OrbitalLift_r2", "FrobnicateBridge_OrbitalLift_r3")))
        selection = root / "selection.json"
        selection.write_text(json.dumps({"selected_rows_order": []}) + "\n")
        spec_dir = root / "specs"
        spec_dir.mkdir()
        (spec_dir / "old.yaml").write_text("family: old\nversion: 1\nstatus: seed_only\nresidual_match:\n  head_patterns: [UnrelatedToken]\ntemplates: []\n")
        result = build(argparse.Namespace(selection=str(selection), checkpoint=str(checkpoint), row_context=str(row_context), spec_dir=str(spec_dir), out=None, md=None, run_id="x", existing_family_confidence_floor=0.75, existing_family_hit_floor=3, include_covered_static_failures=False, exclude_existing_family_tokens=True, min_rows=3, min_shared_tokens=2, max_signature_tokens=4, max_rows_per_cluster=10, max_clusters=5, enqueue=False, queue_db=str(root / "q.sqlite"), events=str(root / "events.jsonl"), max_enqueued=1, agent_runtime="balanced", factory_policy=str(root / "missing_policy.json"), policy_profile="", agent_max_iterations=3, agent_max_wall_time_s=1200))
        assert result["cluster_count"] >= 1, result
        assert result["clusters"][0]["row_count"] == 3, result
        assert result["factory_intelligence_context"]["schema"] == "leanmill-upstream-factory-intelligence-context-v1", result
        checkpoint.write_text(json.dumps({"arm": "public_tool_static", "row_id": "r1", "learning_exit": "tested_no_positive_signal", "attempt_count": 3, "family_matches": [{"family": "old", "confidence": 0.95, "hit_count": 5, "has_negative_controls": True}]}) + "\n")
        blocked = build(argparse.Namespace(selection=str(selection), checkpoint=str(checkpoint), row_context=str(row_context), spec_dir=str(spec_dir), out=None, md=None, run_id="x", existing_family_confidence_floor=0.75, existing_family_hit_floor=3, include_covered_static_failures=False, exclude_existing_family_tokens=True, min_rows=1, min_shared_tokens=1, max_signature_tokens=4, max_rows_per_cluster=10, max_clusters=5, enqueue=False, queue_db=str(root / "q.sqlite"), events=str(root / "events.jsonl"), max_enqueued=1, agent_runtime="balanced", factory_policy=str(root / "missing_policy.json"), policy_profile="", agent_max_iterations=3, agent_max_wall_time_s=1200))
        assert blocked["candidate_static_fail_row_count"] == 0, blocked
    print("leanmill_family_birth_miner self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", default=DEFAULT_SELECTION)
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--existing-family-confidence-floor", type=float, default=0.75)
    ap.add_argument("--existing-family-hit-floor", type=int, default=3)
    ap.add_argument("--include-covered-static-failures", action=argparse.BooleanOptionalAction, default=False)
    ap.add_argument("--exclude-existing-family-tokens", action=argparse.BooleanOptionalAction, default=False)
    ap.add_argument("--min-rows", type=int, default=3)
    ap.add_argument("--min-shared-tokens", type=int, default=1)
    ap.add_argument("--max-signature-tokens", type=int, default=8)
    ap.add_argument("--max-rows-per-cluster", type=int, default=12)
    ap.add_argument("--max-clusters", type=int, default=20)
    ap.add_argument("--enqueue", action="store_true")
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--max-enqueued", type=int, default=0)
    ap.add_argument("--cooldown-s", type=int, default=86400)
    ap.add_argument("--agent-runtime", choices=["balanced", "codex", "claude"], default="balanced")
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--agent-max-iterations", type=int, default=3)
    ap.add_argument("--agent-max-wall-time-s", type=int, default=1200)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = build(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "dry_run": result["dry_run"],
        "candidate_static_fail_row_count": result["candidate_static_fail_row_count"],
        "birth_pressure_row_count": result.get("birth_pressure_row_count"),
        "cluster_count": result["cluster_count"],
        "enqueued": result["enqueued"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
