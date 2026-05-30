#!/usr/bin/env python3
"""Build a Path-C residual curriculum queue from existing proof logs.

This is deliberately non-heavy: it only reads governed residual/source
artifacts and emits ranked next-lever rows. The goal is to turn old
failures into a concrete queue for cheap candidate/static-check work.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_QUEUE = "analytics/public/leanmill/results/v2061_public_union_next_source_discovery_queue.json"
DEFAULT_CONTEXT_DISCOVERY = "analytics/public/leanmill/results/v2019_context_theorem_source_discovery.json"
DEFAULT_RESIDUAL_LEDGER = "analytics/public/ledgers/residual_to_lever/RUNG1_RESIDUAL_LEDGER.jsonl"
DEFAULT_TYPED_LABEL = "analytics/public/leanmill/results/v2108_typed_label_readiness_with_witness_equality_and_hard_negatives.json"
DEFAULT_TYPED_LABEL_RESULT = "analytics/public/leanmill/results/v2109_typed_label_cpu_logistic_diagnostic.json"
DEFAULT_CONSUMPTION_MANIFEST = "analytics/public/leanmill/_archive/LATEST_META_SOLVER_CONSUMPTION_MANIFEST.json"
DEFAULT_REPLAY_GATE = "analytics/public/leanmill/results/v2063_public_union_source_candidate_replay_market_gate.json"
DEFAULT_OUT = "analytics/public/leanmill/path_curricula/PATH_C_CURRICULUM_QUEUE.json"
DEFAULT_MD = "analytics/public/leanmill/path_curricula/PATH_C_CURRICULUM_QUEUE.md"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(errors="ignore"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _base_row(kind: str, row_id: str, priority: int, next_lever: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "row_id": row_id,
        "priority": priority,
        "next_lever": next_lever,
        "budget_gate": "static_check_or_one_row_smoke_before_batch",
        "path_b_gate": "ratified_only_no_manual_edits_false_ratify_zero",
    }


def _replay_blockers(obj: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for rec in obj.get("replay_blocked_candidates") or []:
        row_id = str(rec.get("row_id") or "")
        if not row_id:
            continue
        blocker = str(rec.get("replay_blocker") or "blocked")
        out.setdefault(row_id, [])
        if blocker not in out[row_id]:
            out[row_id].append(blocker)
    return out


def _unblocked_rows(obj: dict[str, Any]) -> set[str]:
    return {str(rec.get("row_id")) for rec in obj.get("unblocked_canary_candidates") or []
            if rec.get("row_id")}


def _source_queue_rows(obj: dict[str, Any], replay_gate: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    replay_gate = replay_gate or {}
    blockers = _replay_blockers(replay_gate)
    unblocked = _unblocked_rows(replay_gate)
    out: list[dict[str, Any]] = []
    for i, rec in enumerate(obj.get("source_discovery_queue") or [], start=1):
        row_id = str(rec.get("row_id") or f"source_queue_{i}")
        row_blockers = blockers.get(row_id) or []
        replay_ready = row_id in unblocked and not row_blockers
        priority = 100 - i
        next_lever = "generate_source_safe_candidate_packet_then_static_check"
        if replay_ready:
            next_lever = "bounded_replay_smoke_of_static_passed_candidate"
            priority += 10
        elif row_blockers:
            next_lever = "resolve_replay_blocker_before_replay_smoke"
            priority -= 35
        row = _base_row(
            "source_safe_candidate_generation",
            row_id,
            priority,
            next_lever,
        )
        row.update({
            "source_file": rec.get("source_file"),
            "source_hinge": rec.get("source_hinge"),
            "action_family": rec.get("non_timeout_candidate_family"),
            "available_source_names": rec.get("available_source_names") or [],
            "guardrails": rec.get("guardrails") or [],
            "reason": rec.get("priority_reason") or rec.get("next_action"),
            "replay_ready": replay_ready,
            "replay_blockers": row_blockers,
            "source_artifact": DEFAULT_SOURCE_QUEUE,
        })
        out.append(row)
    return out


def _context_rows(obj: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, rec in enumerate(obj.get("discoveries") or [], start=1):
        row_id = str(rec.get("row_id") or f"context_discovery_{i}")
        action = str(rec.get("next_source_safe_action_family") or "hydrate_context_then_static_check")
        row = _base_row("context_hydration_repair", row_id, 80 - i, action)
        row.update({
            "source_file": rec.get("source_file"),
            "source_status": rec.get("source_status"),
            "action_family": action,
            "context_hydration_needed": rec.get("context_hydration_needed") or [],
            "guardrails": rec.get("guardrails") or [],
            "primary_sources": rec.get("primary_sources") or [],
            "quarantined_sources": rec.get("quarantined_sources") or [],
            "source_artifact": DEFAULT_CONTEXT_DISCOVERY,
        })
        out.append(row)
    return out


def _residual_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(r.get("residual_class") or "unknown") for r in records)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for rec in records:
        row_id = str(rec.get("row") or rec.get("row_id") or "")
        residual = str(rec.get("residual_class") or "unknown")
        lever = str(rec.get("next_lever") or "classify_residual")
        key = (row_id, residual, lever)
        if not row_id or key in seen:
            continue
        seen.add(key)
        priority = 65
        kind = "governed_residual_to_lever"
        if residual in {"gate_contract_not_crisp", "target_kind_mismatch"}:
            priority = 55
        if residual == "gate_contract_not_crisp" and rec.get("certified_proof_exists"):
            kind = "historical_contract_cleanup"
            priority = 15
            lever = "official_contract_restatement_or_retire_not_path_c_canary"
        if residual in {"missing_library_premise", "theorem_or_pde_gap"}:
            priority = 75
        row = _base_row(kind, row_id, priority, lever)
        row.update({
            "residual_class": residual,
            "next_target": rec.get("next_target"),
            "certified_proof_exists": rec.get("certified_proof_exists"),
            "scoreboard": rec.get("scoreboard"),
            "class_frequency": counts[residual],
            "source_artifact": DEFAULT_RESIDUAL_LEDGER,
        })
        out.append(row)
    return out


def _typed_label_rows(obj: dict[str, Any], result_obj: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    result_obj = result_obj or {}
    result_status = str(result_obj.get("status") or "")
    result_decision = result_obj.get("decision") or {}
    if result_status.startswith("typed_label_cpu_diagnostic_complete"):
        row = _base_row(
            "typed_label_diagnostic_completed",
            "typed_label_next",
            18,
            str(result_decision.get("next_artifact") or "acquire_larger_typed_label_eval_before_model_claim"),
        )
        row.update({
            "reason": result_decision.get("block_reason") or "typed-label diagnostic consumed; model claim remains blocked",
            "claim_model_delta_now": result_decision.get("claim_model_delta_now"),
            "allow_gpu_or_full_gnn_training_now": result_decision.get("allow_gpu_or_full_gnn_training_now"),
            "source_artifact": DEFAULT_TYPED_LABEL_RESULT,
        })
        rows.append(row)
        return rows
    decision = obj.get("decision") or {}
    preferred = decision.get("preferred_next_artifact")
    if preferred:
        row = _base_row(
            "typed_label_contrast_acquisition",
            "typed_label_next",
            70,
            str(preferred),
        )
        row.update({
            "reason": decision.get("rationale"),
            "next_artifact_options": decision.get("next_artifact_options") or [],
            "source_artifact": DEFAULT_TYPED_LABEL,
        })
        rows.append(row)
    return rows


def _error_class(rec: dict[str, Any]) -> str:
    text = "\n".join(str(rec.get(k) or "") for k in ("stdout_tail", "stderr_tail"))
    low = text.lower()
    if rec.get("timed_out"):
        return "timeout"
    if "type mismatch" in low or "application type mismatch" in low:
        return "type_mismatch"
    if "unsolved goals" in low:
        return "unsolved_goals"
    if "unknown identifier" in low:
        return "unknown_identifier"
    if "unexpected end of input" in low:
        return "syntax_incomplete"
    if "`simp` made no progress" in low or "made no progress" in low:
        return "no_progress"
    if rec.get("returncode") not in (0, None):
        return "lean_error"
    return "none"


def _canary_rows(objs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    rows: list[dict[str, Any]] = []
    ratified: set[str] = set()
    compile_ready: set[str] = set()
    for obj in objs:
        row_id = str(obj.get("row_id") or "")
        if not row_id:
            continue
        candidates = obj.get("rows") or []
        closed = [r for r in candidates if r.get("closed")]
        governed = [r for r in closed if (r.get("governance") or {}).get("verdict") == "closure"]
        failed_labels = sorted({
            _error_class(r) for r in candidates
            if not r.get("closed") and _error_class(r) != "none"
        })
        if governed:
            ratified.add(row_id)
            row = _base_row(
                "path_c_ratified_candidate",
                row_id,
                20,
                "retire_or_export_to_consumption_manifest",
            )
            row.update({
                "closed_candidates": [str(r.get("candidate")) for r in closed],
                "ratified_candidates": [str(r.get("candidate")) for r in governed],
                "failed_error_classes": failed_labels,
                "source_artifact": "canary_result",
                "reason": "canary replay produced official governance closure",
            })
            rows.append(row)
        elif closed:
            compile_ready.add(row_id)
            row = _base_row(
                "path_c_candidate_ready_for_governance",
                row_id,
                95,
                "govern_static_winners_only",
            )
            row.update({
                "closed_candidates": [str(r.get("candidate")) for r in closed],
                "failed_error_classes": failed_labels,
                "source_artifact": "canary_result",
                "reason": "canary replay compiled candidates but no ratified governance result supplied",
            })
            rows.append(row)
        elif failed_labels:
            row = _base_row(
                "path_c_failed_candidate_labels",
                row_id,
                45,
                "mine_failed_candidate_errors_for_repair_policy",
            )
            row.update({
                "failed_error_classes": failed_labels,
                "source_artifact": "canary_result",
                "reason": "canary replay produced repair-policy failure labels",
            })
            rows.append(row)
    return rows, ratified, compile_ready


def _consumed_rows(obj: dict[str, Any]) -> set[str]:
    rows: set[str] = set()
    for key in ("primary_strict_row_ids", "solver_closure_row_ids"):
        vals = obj.get(key) or []
        rows.update(str(v) for v in vals)
    # Some artifacts store this inventory under a nested manifest-like object.
    for val in obj.values():
        if isinstance(val, dict):
            rows.update(_consumed_rows(val))
    return rows


def build_queue(source_queue: Path, context_discovery: Path, residual_ledger: Path,
                typed_label: Path, typed_label_result: Path | None = None,
                consumption_manifest: Path | None = None,
                replay_gate: Path | None = None,
                canary_results: list[Path] | None = None) -> dict[str, Any]:
    canary_objs = [_read_json(p) for p in (canary_results or [])]
    canary_result_rows, ratified_canary_rows, compile_ready_canary_rows = _canary_rows(canary_objs)

    rows: list[dict[str, Any]] = []
    rows.extend(_source_queue_rows(_read_json(source_queue), _read_json(replay_gate) if replay_gate else None))
    rows.extend(_context_rows(_read_json(context_discovery)))
    rows.extend(_residual_rows(_read_jsonl(residual_ledger)))
    rows.extend(_typed_label_rows(_read_json(typed_label), _read_json(typed_label_result) if typed_label_result else None))
    rows.extend(canary_result_rows)

    consumed = _consumed_rows(_read_json(consumption_manifest)) if consumption_manifest else set()
    active_canary_rows = ratified_canary_rows | compile_ready_canary_rows
    before_consumed_exclusion = len(rows)
    rows = [
        r for r in rows
        if str(r.get("row_id")) not in consumed
        or str(r.get("kind")).startswith("path_c_")
    ]
    excluded_consumed_count = before_consumed_exclusion - len(rows)
    before_canary_suppression = len(rows)
    rows = [
        r for r in rows
        if (
            str(r.get("row_id")) not in active_canary_rows
            or str(r.get("kind")).startswith("path_c_")
        )
    ]
    suppressed_canary_duplicate_count = before_canary_suppression - len(rows)

    rows = sorted(rows, key=lambda r: (-int(r.get("priority", 0)), str(r.get("row_id"))))
    for i, row in enumerate(rows, start=1):
        row["queue_rank"] = i
    kind_counts = Counter(str(r.get("kind")) for r in rows)
    return {
        "schema": "path-c-curriculum-queue-v1",
        "generated_by": "scripts/public/control/path_c_curriculum_queue.py",
        "inputs": {
            "source_queue": str(source_queue),
            "context_discovery": str(context_discovery),
            "residual_ledger": str(residual_ledger),
            "typed_label": str(typed_label),
            "typed_label_result": str(typed_label_result) if typed_label_result else None,
            "consumption_manifest": str(consumption_manifest) if consumption_manifest else None,
            "replay_gate": str(replay_gate) if replay_gate else None,
            "canary_results": [str(p) for p in (canary_results or [])],
        },
        "canary_ratified_rows": sorted(ratified_canary_rows),
        "canary_compile_ready_rows": sorted(compile_ready_canary_rows),
        "excluded_consumed_rows": sorted(consumed),
        "excluded_consumed_count": excluded_consumed_count,
        "suppressed_canary_duplicate_count": suppressed_canary_duplicate_count,
        "n_rows": len(rows),
        "kind_counts": dict(sorted(kind_counts.items())),
        "rows": rows,
    }


def write_markdown(obj: dict[str, Any], path: Path) -> None:
    lines = [
        "# Path C Curriculum Queue",
        "",
        f"Rows: `{obj['n_rows']}`",
        "",
        "| Rank | Kind | Row | Next Lever | Reason |",
        "|---:|---|---|---|---|",
    ]
    for row in obj["rows"][:25]:
        reason = str(row.get("reason") or row.get("source_hinge") or row.get("residual_class") or "")
        reason = reason.replace("|", "/")
        lines.append(
            f"| {row['queue_rank']} | {row.get('kind')} | `{row.get('row_id')}` | "
            f"`{row.get('next_lever')}` | {reason[:180]} |"
        )
    path.write_text("\n".join(lines) + "\n")


def _self_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / "source.json"
        context = root / "context.json"
        residual = root / "residual.jsonl"
        typed = root / "typed.json"
        typed_result = root / "typed_result.json"
        manifest = root / "manifest.json"
        replay = root / "replay.json"
        canary = root / "canary.json"
        source.write_text(json.dumps({
            "source_discovery_queue": [{
                "row_id": "r1",
                "source_file": "A.lean",
                "source_hinge": "lemma_a",
                "non_timeout_candidate_family": "rewrite",
                "available_source_names": ["lemma_a"],
                "next_action": "static check",
            }]
        }))
        context.write_text(json.dumps({
            "discoveries": [{
                "row_id": "r2",
                "next_source_safe_action_family": "hydrate_then_induction",
                "source_file": "B.lean",
            }]
        }))
        residual.write_text(json.dumps({
            "row": "r3",
            "residual_class": "missing_library_premise",
            "next_lever": "retrieve_context",
        }) + "\n")
        typed.write_text(json.dumps({"decision": {"preferred_next_artifact": "make_hard_negative"}}))
        typed_result.write_text(json.dumps({
            "status": "typed_label_cpu_diagnostic_complete_model_claim_blocked",
            "decision": {
                "next_artifact": "acquire_rank1_negative_or_larger_typed_label_eval_before_any_model_claim",
                "block_reason": "small diagnostic did not beat baseline",
                "claim_model_delta_now": False,
                "allow_gpu_or_full_gnn_training_now": False,
            },
        }))
        manifest.write_text(json.dumps({"primary_strict_row_ids": ["r1"]}))
        replay.write_text(json.dumps({
            "replay_blocked_candidates": [{"row_id": "r2", "replay_blocker": "needs_context"}],
            "unblocked_canary_candidates": [{"row_id": "r1"}],
        }))
        canary.write_text(json.dumps({
            "row_id": "r2",
            "rows": [
                {"candidate": "good", "closed": True,
                 "governance": {"verdict": "closure"}},
                {"candidate": "bad", "closed": False,
                 "stderr_tail": "error: Type mismatch\nunsolved goals"},
            ],
        }))
        obj = build_queue(source, context, residual, typed, typed_result, manifest, replay, [canary])
        assert obj["n_rows"] == 3, obj
        assert obj["excluded_consumed_count"] == 1, obj
        assert obj["canary_ratified_rows"] == ["r2"], obj
        assert any(r["kind"] == "path_c_ratified_candidate" for r in obj["rows"]), obj["rows"]
        assert any(r["kind"] == "typed_label_diagnostic_completed" for r in obj["rows"]), obj["rows"]
        assert all(r["row_id"] != "r1" for r in obj["rows"]), obj["rows"]
    print("path_c_curriculum_queue self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-queue", default=DEFAULT_SOURCE_QUEUE)
    ap.add_argument("--context-discovery", default=DEFAULT_CONTEXT_DISCOVERY)
    ap.add_argument("--residual-ledger", default=DEFAULT_RESIDUAL_LEDGER)
    ap.add_argument("--typed-label", default=DEFAULT_TYPED_LABEL)
    ap.add_argument("--typed-label-result", default=DEFAULT_TYPED_LABEL_RESULT)
    ap.add_argument("--consumption-manifest", default=DEFAULT_CONSUMPTION_MANIFEST)
    ap.add_argument("--replay-gate", default=DEFAULT_REPLAY_GATE)
    ap.add_argument("--canary-result", action="append", default=[])
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--markdown", default=DEFAULT_MD)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        _self_test()
        return
    obj = build_queue(Path(args.source_queue), Path(args.context_discovery),
                      Path(args.residual_ledger), Path(args.typed_label),
                      Path(args.typed_label_result) if args.typed_label_result else None,
                      Path(args.consumption_manifest) if args.consumption_manifest else None,
                      Path(args.replay_gate) if args.replay_gate else None,
                      [Path(p) for p in args.canary_result])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    md = Path(args.markdown)
    md.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(obj, md)
    print(json.dumps({"out": str(out), "markdown": str(md), "n_rows": obj["n_rows"],
                      "kind_counts": obj["kind_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
