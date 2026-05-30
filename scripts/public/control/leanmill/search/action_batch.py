#!/usr/bin/env python3
"""Batch runner for LeanSearch action smokes.

This is a thin checkpointed wrapper over `leansearch_action_smoke.py`.
It keeps each row's full JSON artifact separate, appends a JSONL summary
after every row, and resumes by skipping completed row ids. It deliberately
runs rows serially inside one process; cross-machine parallelism is handled
by launching one local batch and one VPS batch.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import leansearch_action_smoke as smoke


REPO = Path(__file__).resolve().parents[5]
DEFAULT_FILTER = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json"
DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_OUT_DIR = "/tmp/rung1/leansearch_action_batch"


LEVER_BY_RESIDUAL = {
    "no_candidate_action_generated": "source_acquisition_or_lane_mismatch",
    "type_mismatch": "typed_transport_or_specialization_template",
    "tactic_failed": "proof_planning_or_direction_template",
    "unsolved_goals": "mine_subgoals_for_next_template",
    "missing_instance": "instantiate_implicits_or_typeclass_context",
    "unknown_identifier": "target_context_source_filter_or_import_gap",
    "repl_step_context_gap": "retry_same_file_or_local_repair_templates_in_file_backend",
    "timeout": "decompose_or_reduce_search_breadth",
    "lean_error": "inspect_lean_error_tail",
    "mixed": "cluster_errors_before_next_lane",
    "syntax_or_template_bug": "fix_action_template_before_more_lean_spend",
    "internal_exception": "isolate_repl_or_kernel_bug_then_retry_minimal_driver",
    "directional_iff_gap": "split_iff_directions_and_emit_exact_gap_for_hard_side",
    "source_action_mismatch": "rerank_candidates_by_goal_delta_or_source_shape",
    "missing_sorried_file": "sync_source_files_or_run_on_machine_that_built_corpus",
    "no_positive_source_action": "source_action_rerank_or_requires_multistep_repair",
}


def _filter_rows(path: Path) -> list[str]:
    obj = json.loads(path.read_text(errors="ignore"))
    out: list[str] = []
    for row in obj.get("rows") or []:
        if int(row.get("row_context_resolved_count") or 0) > 0:
            out.append(str(row["row_id"]))
    return out


def _done_rows(checkpoint: Path) -> set[str]:
    done: set[str] = set()
    if not checkpoint.exists():
        return done
    for line in checkpoint.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("status") == "done" and rec.get("row_id"):
            done.add(str(rec["row_id"]))
    return done


def _append_jsonl(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()


def _append_telemetry(args: argparse.Namespace, rec: dict[str, Any], iteration_index: int) -> None:
    path_s = getattr(args, "factory_telemetry_path", "")
    if not path_s:
        return
    n_ratified = int(rec.get("n_ratified") or 0)
    n_closed = int(rec.get("n_closed") or 0)
    if n_ratified:
        action = "ratified_closure"
        pending = "DONE"
    elif n_closed:
        action = "compile_closed_needs_governance"
        pending = "GOVERN"
    elif rec.get("status") == "error":
        action = "row_error"
        pending = "RETRY_OR_INSPECT"
    else:
        action = "path_c_residual"
        pending = "PATH_C"
    payload = {
        "record_type": "iteration",
        "schema": "leansearch-factory-telemetry-v1",
        "run_id": getattr(args, "factory_run_id", ""),
        "iteration_index": iteration_index,
        "iteration_start_utc": rec.get("row_started_at"),
        "iteration_end_utc": rec.get("row_finished_at"),
        "wall_clock_seconds": float(rec.get("elapsed_s") or 0.0),
        "lead_time_seconds": rec.get("lead_s"),
        "lane": args.lane,
        "row_id": rec.get("row_id"),
        "loop_control_action": action,
        "score": n_ratified,
        "score_improved": bool(n_ratified),
        "champion_promoted": bool(n_ratified),
        "stagnation_count": 0 if n_ratified or n_closed else 1,
        "gate_engagement": bool(getattr(args, "govern_winners", False)),
        "gate_failure_count": 0 if n_ratified else int(n_closed > 0 and not n_ratified),
        "failed_gate_ids": [] if n_ratified or not n_closed else ["needs_path_b_governance"],
        "escalation_flags": {"self_reference": False, "semantic_escalation": False},
        "falsification_mode": "leansearch_repair_factory",
        "mutator_model_id": "deterministic_lean_action_templates",
        "judge_model_id": "path_b_governance" if getattr(args, "govern_winners", False) else "none",
        "mutator_usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0},
        "judge_usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0},
        "estimated_cost_usd": 0.0,
        "pending_loop_action": pending,
    }
    _append_jsonl(Path(path_s), payload)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _dominant_error(obj: dict[str, Any]) -> tuple[str, dict[str, int], str]:
    if obj.get("status") == "error" and obj.get("error"):
        err = str(obj.get("error") or "")
        if "FileNotFoundError" in err or "No such file or directory" in err:
            return "missing_sorried_file", {"missing_sorried_file": 1}, err[-800:]
        return "internal_exception", {"internal_exception": 1}, err[-800:]
    if obj.get("no_positive_source_action") and obj.get("source_action_scores"):
        scores = list(obj.get("source_action_scores") or [])
        score_counts: dict[str, int] = {}
        sample_bits: list[str] = []
        for s in scores:
            cls = str(s.get("error_class") or "unknown")
            score_counts[cls] = score_counts.get(cls, 0) + 1
            if len(sample_bits) < 3:
                sample_bits.append(f"{s.get('candidate')}: {s.get('message_tail')}")
        sample = "\n".join(sample_bits)[-800:]
        if score_counts and set(score_counts) <= {"unknown_identifier"}:
            return "repl_step_context_gap", score_counts, sample
        if score_counts:
            return "no_positive_source_action", score_counts, sample
    counts: dict[str, int] = {}
    sample = ""
    for r in obj.get("results") or []:
        cls = str(r.get("error_class") or "unknown")
        counts[cls] = counts.get(cls, 0) + 1
        if not sample:
            sample = str((r.get("stdout_tail") or "") + "\n" + (r.get("stderr_tail") or ""))[-800:]
    if not counts:
        return "no_candidate_action_generated", counts, sample
    normalized = _normal_form_error(obj, counts, sample)
    if normalized:
        return normalized, counts, sample
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    if len(counts) > 1 and counts[top] < sum(counts.values()):
        return top if counts[top] >= 2 else "mixed", counts, sample
    return top, counts, sample


def _normal_form_error(obj: dict[str, Any], counts: dict[str, int], sample: str) -> str | None:
    text = sample.lower()
    families = {str(r.get("action_family") or "") for r in obj.get("results") or []}
    row_id = str(obj.get("row_id") or "").lower()
    if any(r.get("repl_step_file_fallback_used") for r in obj.get("results") or []):
        if counts.get("unknown_identifier", 0):
            return "repl_step_context_gap"
    if "unexpected token" in text or "unexpected end of input" in text:
        return "syntax_or_template_bug"
    if "internal exception" in text:
        return "internal_exception"
    if ("iff" in row_id or "↔" in text or "constructor_apply_easy" in families) and counts.get("lean_error", 0):
        return "directional_iff_gap"
    if "could not unify" in text or "application type mismatch" in text or "type mismatch" in text:
        return "source_action_mismatch"
    return None


def _publish_event(args: argparse.Namespace, rec: dict[str, Any], row_obj: dict[str, Any] | None) -> None:
    if not args.event_dir:
        return
    lead_s = None
    started = getattr(args, "factory_started_monotonic", None)
    if started is not None:
        lead_s = round(time.monotonic() - float(started), 3)
    rec["lead_s"] = lead_s
    event_dir = Path(args.event_dir)
    base = {
        "schema": "leansearch-factory-event-v1",
        "created_at": _now_iso(),
        "run_id": getattr(args, "factory_run_id", ""),
        "lane": args.lane,
        "row_id": rec.get("row_id"),
        "row_out": rec.get("out"),
        "status": rec.get("status"),
        "cycle_s": rec.get("elapsed_s"),
        "lead_s": lead_s,
    }
    if rec.get("n_ratified"):
        _append_jsonl(event_dir / "closed.jsonl", {
            **base,
            "event": "ratified_closure",
            "ratified_candidates": rec.get("ratified_candidates", []),
        })
    elif rec.get("n_closed"):
        _append_jsonl(event_dir / "to_govern.jsonl", {
            **base,
            "event": "compile_closed_needs_governance",
            "closed_candidates": rec.get("closed_candidates", []),
        })
    else:
        residual, counts, sample = _dominant_error(row_obj or {})
        _append_jsonl(event_dir / "path_c_residuals.jsonl", {
            **base,
            "event": "path_c_residual",
            "residual_class": residual,
            "error_counts": counts,
            "next_lever": LEVER_BY_RESIDUAL.get(residual, "inspect_residual"),
            "sample_tail": sample,
        })


def run_batch(args: argparse.Namespace) -> dict[str, Any]:
    row_ids = list(args.row_id or _filter_rows(Path(args.static_filter)))
    if args.shard_count > 1:
        row_ids = [rid for i, rid in enumerate(row_ids) if i % args.shard_count == args.shard_index]
    if args.limit is not None:
        row_ids = row_ids[: args.limit]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = Path(args.checkpoint) if args.checkpoint else out_dir / "checkpoint.jsonl"
    done = _done_rows(checkpoint) if args.resume else set()

    completed = 0
    skipped = 0
    closed = 0
    ratified = 0
    rows_out: list[dict[str, Any]] = []
    for rid in row_ids:
        if rid in done:
            skipped += 1
            continue
        t0 = time.monotonic()
        row_started_at = _now_iso()
        row_out = out_dir / f"{rid}.json"
        try:
            obj = smoke.run(
                rid,
                Path(args.corpus),
                Path(args.static_filter),
                row_out,
                args.timeout,
                args.max_candidates,
                args.max_actions,
                Path(args.save_dir) if args.save_dir else None,
                args.govern_winners,
                [],
                args.action_family,
                args.candidate_name,
                args.backend,
                bool(getattr(args, "score_candidates", False)),
                bool(getattr(args, "require_positive_source_action", False)),
            )
            row_obj = obj
            rec = {
                "status": "done",
                "row_id": rid,
                "out": str(row_out),
                "elapsed_s": round(time.monotonic() - t0, 3),
                "row_started_at": row_started_at,
                "row_finished_at": _now_iso(),
                "n_results": len(obj.get("results") or []),
                "n_closed": obj.get("n_closed", 0),
                "n_ratified": obj.get("n_ratified", 0),
                "closed_candidates": obj.get("closed_candidates", []),
                "ratified_candidates": obj.get("ratified_candidates", []),
            }
        except Exception as exc:  # fail-row, keep batch resumable
            row_obj = None
            rec = {
                "status": "error",
                "row_id": rid,
                "out": str(row_out),
                "elapsed_s": round(time.monotonic() - t0, 3),
                "row_started_at": row_started_at,
                "row_finished_at": _now_iso(),
                "error": f"{type(exc).__name__}: {exc}",
            }
        with checkpoint.open("a") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
        _publish_event(args, rec, row_obj)
        offset = int(getattr(args, "factory_iteration_offset", 0) or 0)
        _append_telemetry(args, rec, offset + len(rows_out))
        rows_out.append(rec)
        completed += int(rec["status"] == "done")
        closed += int(rec.get("n_closed") or 0)
        ratified += int(rec.get("n_ratified") or 0)

    payload = {
        "schema": "leansearch-action-batch-v1",
        "lane": args.lane,
        "row_count_requested": len(row_ids),
        "completed": completed,
        "skipped": skipped,
        "closed_total": closed,
        "ratified_total": ratified,
        "checkpoint": str(checkpoint),
        "out_dir": str(out_dir),
        "rows": rows_out,
    }
    if args.summary:
        Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    rows = _filter_rows(REPO / DEFAULT_FILTER)
    assert "MCB_039_inner_le_Lp_mul_Lq_of_nonneg" in rows
    residual, counts, _ = _dominant_error({"results": [{"error_class": "type_mismatch"}]})
    assert residual == "type_mismatch" and counts["type_mismatch"] == 1
    residual, _, _ = _dominant_error({
        "row_id": "x_iff_y",
        "results": [{"error_class": "lean_error", "action_family": "constructor_apply_easy", "stderr_tail": "Lean error"}],
    })
    assert residual == "directional_iff_gap"
    residual, _, _ = _dominant_error({"results": [{"error_class": "lean_error", "stderr_tail": "unexpected token '·'"}]})
    assert residual == "syntax_or_template_bug"
    residual, _, _ = _dominant_error({
        "results": [{"error_class": "unknown_identifier", "repl_step_file_fallback_used": True, "stderr_tail": "Unknown identifier X"}],
    })
    assert residual == "repl_step_context_gap"
    residual, counts, _ = _dominant_error({"status": "error", "error": "FileNotFoundError: missing"})
    assert residual == "missing_sorried_file" and counts["missing_sorried_file"] == 1
    class A:
        lane = "x"
        factory_telemetry_path = ""
        factory_run_id = "r"
        govern_winners = False
    _append_telemetry(A(), {"n_closed": 1, "n_ratified": 0, "status": "done"}, 0)
    print("leansearch_action_batch self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row-id", action="append", default=[])
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--static-filter", default=DEFAULT_FILTER)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--checkpoint")
    ap.add_argument("--summary")
    ap.add_argument("--lane", default="adhoc")
    ap.add_argument("--event-dir", default="")
    ap.add_argument("--timeout", type=int, default=75)
    ap.add_argument("--max-candidates", type=int, default=4)
    ap.add_argument("--max-actions", type=int, default=1)
    ap.add_argument("--action-family", action="append", default=[])
    ap.add_argument("--candidate-name", action="append", default=[])
    ap.add_argument("--backend", choices=["subprocess", "repl", "repl_step", "repl_file"], default="subprocess")
    ap.add_argument("--govern-winners", action="store_true")
    ap.add_argument("--save-dir", default="")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--shard-count", type=int, default=1)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = run_batch(args)
    print(json.dumps({
        "completed": obj["completed"],
        "skipped": obj["skipped"],
        "closed_total": obj["closed_total"],
        "ratified_total": obj["ratified_total"],
        "checkpoint": obj["checkpoint"],
        "summary": args.summary,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
