#!/usr/bin/env python3
"""Publish a no-lift LeanMill evaluation result as an internal receipt.

This is intentionally a negative-result publisher. It records what the
benchmark showed and which claims are forbidden; it does not create proof
credit, benchmark lift, or public differentiation evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from leanmill_paths import DATA_DIR  # noqa: E402
import leanmill_work_queue as work_queue  # noqa: E402
from src.ztare.leanmill.common import (  # noqa: E402
    read_json,
    sha256_file,
    write_json_atomic,
    write_text_atomic,
)


DEFAULT_RUN = f"{DATA_DIR}/evaluation_harness_run.json"
DEFAULT_OUT = f"{DATA_DIR}/evaluation_harness_no_lift_report.json"
DEFAULT_MD = f"{DATA_DIR}/evaluation_harness_no_lift_report.md"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build(args: argparse.Namespace) -> dict[str, Any]:
    run = _dict(read_json(args.run, default={}))
    arm_metrics = _dict(run.get("arm_metrics"))
    comparison = _dict(arm_metrics.get("benchmark_lift_comparison"))
    credited_run_present = bool(run and not run.get("preflight_only") and int(run.get("record_count") or 0) > 0)
    has_lift = bool(comparison.get("meets_20pp_closure_lift") or comparison.get("meets_2x_attempt_efficiency_lift"))
    if not credited_run_present:
        status = "blocked_no_credited_run"
    elif not comparison:
        status = "blocked_missing_lift_comparison"
    elif has_lift:
        status = "blocked_run_has_lift"
    else:
        status = "published_no_lift_result"
    return {
        "schema": "leanmill-evaluation-no-lift-report-v1",
        "generated_at_epoch": int(time.time()),
        "status": status,
        "source_run": args.run,
        "source_run_sha256": sha256_file(args.run),
        "row_count": int(run.get("row_count") or 0),
        "selected_row_count": int(run.get("selected_row_count") or 0),
        "completed_row_count": int(run.get("completed_row_count") or run.get("row_count") or 0),
        "record_count": int(run.get("record_count") or 0),
        "baseline_arm": comparison.get("baseline_arm"),
        "residual_arm": comparison.get("residual_arm"),
        "closure_rate_delta": comparison.get("closure_rate_delta"),
        "attempt_efficiency_ratio_baseline_over_residual": comparison.get("attempt_efficiency_ratio_baseline_over_residual"),
        "meets_20pp_closure_lift": bool(comparison.get("meets_20pp_closure_lift")),
        "meets_2x_attempt_efficiency_lift": bool(comparison.get("meets_2x_attempt_efficiency_lift")),
        "allowed_internal_claim": (
            "On this credited natural-Mathlib slice, the residual curriculum did not beat the governed public/static baseline "
            "on closure-rate lift or attempt-efficiency lift."
            if status == "published_no_lift_result" else ""
        ),
        "forbidden_claims": [
            "competitive planner lift from this slice",
            "non-subsumed benchmark win from this slice",
            "proof credit from public/static closures",
            "exact-gap or family-template credit from a no-lift aggregate",
        ],
        "credit_boundary": "internal negative benchmark receipt only; no proof credit and no competitive-lift claim",
        "meta_reasoning_receipt": {
            "failure_mode": "positive-looking family/proposal mechanisms can be overclaimed when the benchmark shows no aggregate lift",
            "mechanized_prevention": "publish the no-lift receipt keyed to the run hash and suppress lift/differentiation recommendations for that run",
            "gaming_guard": "negative publication is not converted into proof value or benchmark success",
        },
        "next_action": (
            "prioritize C-discriminating rows where public/static tools fail, and keep this run as no-lift evidence"
            if status == "published_no_lift_result" else
            "repair or rerun the evaluation harness before publishing a no-lift receipt"
        ),
    }


def write_markdown(path: str | Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LeanMill Evaluation No-Lift Report",
        "",
        f"- generated_at_epoch: `{payload.get('generated_at_epoch')}`",
        f"- status: `{payload.get('status')}`",
        f"- source_run: `{payload.get('source_run')}`",
        f"- source_run_sha256: `{payload.get('source_run_sha256')}`",
        f"- selected_row_count: `{payload.get('selected_row_count')}`",
        f"- completed_row_count: `{payload.get('completed_row_count')}`",
        f"- baseline_arm: `{payload.get('baseline_arm')}`",
        f"- residual_arm: `{payload.get('residual_arm')}`",
        f"- closure_rate_delta: `{payload.get('closure_rate_delta')}`",
        f"- attempt_efficiency_ratio_baseline_over_residual: `{payload.get('attempt_efficiency_ratio_baseline_over_residual')}`",
        f"- meets_20pp_closure_lift: `{payload.get('meets_20pp_closure_lift')}`",
        f"- meets_2x_attempt_efficiency_lift: `{payload.get('meets_2x_attempt_efficiency_lift')}`",
        f"- allowed_internal_claim: {payload.get('allowed_internal_claim')}",
        f"- forbidden_claims: `{payload.get('forbidden_claims')}`",
        f"- credit_boundary: {payload.get('credit_boundary')}",
        f"- next_action: {payload.get('next_action')}",
    ]
    write_text_atomic(path, "\n".join(lines) + "\n")


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_eval_no_lift_") as td:
        root = Path(td)
        run = root / "run.json"
        run.write_text(json.dumps({
            "preflight_only": False,
            "row_count": 2,
            "selected_row_count": 2,
            "completed_row_count": 2,
            "record_count": 8,
            "arm_metrics": {
                "benchmark_lift_comparison": {
                    "baseline_arm": "baseline",
                    "residual_arm": "residual",
                    "closure_rate_delta": 0.0,
                    "attempt_efficiency_ratio_baseline_over_residual": 0.5,
                    "meets_20pp_closure_lift": False,
                    "meets_2x_attempt_efficiency_lift": False,
                }
            },
        }) + "\n")
        payload = build(argparse.Namespace(run=str(run)))
        assert payload["status"] == "published_no_lift_result", payload
        assert payload["source_run_sha256"] == sha256_file(run), payload
    print("leanmill_evaluation_no_lift_report self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=DEFAULT_RUN)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    write_json_atomic(args.out, payload)
    write_markdown(args.md, payload)
    if args.events:
        work_queue.append_event(args.events, {
            "event_type": "leanmill_evaluation_no_lift_published",
            "payload": {
                "status": payload.get("status"),
                "source_run": payload.get("source_run"),
                "source_run_sha256": payload.get("source_run_sha256"),
                "next_action": payload.get("next_action"),
            },
            "artifact_paths": [args.out, args.md],
        })
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "status": payload.get("status"),
        "source_run_sha256": payload.get("source_run_sha256"),
        "next_action": payload.get("next_action"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
