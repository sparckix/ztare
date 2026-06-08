#!/usr/bin/env python3
"""Run GP-245 anti-bias-collapse dispatch rows through subscription CLIs.

This is the execution surface for the Law 1 minimal smoke. It reads the
validated dispatch queue, runs selected rows through subscription-backed
Claude/Codex CLIs, and appends DB-compatible call receipts. Gemini rows remain
manual/API TODO unless an operator supplies a compatible runtime later.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.ztare.common.subscription_agent_runtime import (  # noqa: E402
    redact_prompt_command,
    run_subscription_agent_with_recovery,
)


WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/anti_bias_collapse_v1/workspace"
DEFAULT_QUEUE = WORKSPACE / "anti_bias_collapse_dispatch_queue.jsonl"
DEFAULT_CALLS = WORKSPACE / "anti_bias_collapse_v1_calls.jsonl"
DEFAULT_FAILURES = WORKSPACE / "anti_bias_collapse_v1_failed_calls.jsonl"
DEFAULT_TRACE_DIR = WORKSPACE / "traces/anti_bias_collapse_v1"
PILOT_ID = "anti_bias_collapse_v1"
SUBSCRIPTION_RUNTIME_ROUTES = {
    "claude_subscription": "claude",
    "codex_subscription": "codex",
}
GEMINI_RUNTIME_ROUTE = "gemini_api_or_manual"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{line_no}: expected JSON object")
        rows.append(row)
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
        fh.flush()


def completed_dispatch_ids(calls: Path) -> set[str]:
    done: set[str] = set()
    for row in load_jsonl(calls):
        if not row.get("schema_ok"):
            continue
        if numeric_probability(row.get("p_success")) is None:
            continue
        dispatch_id = row.get("dispatch_id")
        if dispatch_id:
            done.add(str(dispatch_id))
    return done


def extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    candidates = [text]
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S | re.I)
    candidates.extend(fenced)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def numeric_probability(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        out = float(value)
        if 0.0 <= out <= 1.0:
            return out
    return None


def receipt_from_run(
    *,
    row: dict[str, Any],
    runtime: str,
    raw_response: str,
    stderr: str,
    returncode: int,
    command_preview: list[str],
    recovery_note: str | None,
    fired_at: str,
) -> dict[str, Any]:
    parsed = extract_json_object(raw_response) or {}
    p_success = numeric_probability(parsed.get("p_success"))
    schema_ok = (
        returncode == 0
        and p_success is not None
        and parsed.get("bias_id") == row.get("bias_id")
        and parsed.get("event_id") == row.get("event_id")
        and parsed.get("frame") == row.get("frame")
        and parsed.get("prompt_arm") == row.get("prompt_arm")
    )
    return {
        "schema": "gp245-anti-bias-collapse-call-receipt-v1",
        "pilot_id": PILOT_ID,
        "dispatch_id": row.get("dispatch_id"),
        "family": row.get("family"),
        "agent_id": row.get("agent_id"),
        "runtime": runtime,
        "runtime_route": row.get("runtime_route"),
        "db_contract_id": row.get("db_contract_id"),
        "contract_id": row.get("db_contract_id"),
        "bias_id": row.get("bias_id"),
        "bias_class_preregistered": row.get("bias_class_preregistered"),
        "event_id": row.get("event_id"),
        "event_core": row.get("event_core"),
        "frame": row.get("frame"),
        "prompt_arm": row.get("prompt_arm"),
        "g0": row.get("g0"),
        "normative_gap_direction": row.get("normative_gap_direction"),
        "predicted_cell": row.get("predicted_cell"),
        "source_finding_ids": row.get("source_finding_ids"),
        "p_success": p_success,
        "schema_ok": schema_ok,
        "parsed": parsed,
        "raw_response": raw_response,
        "stderr_tail": stderr[-4000:],
        "returncode": returncode,
        "command_preview": command_preview,
        "recovery_note": recovery_note,
        "fired_at": fired_at,
    }


def trace_path(trace_dir: Path, dispatch_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.=-]+", "__", dispatch_id)
    return trace_dir / f"{safe}.json"


def build_prompt(row: dict[str, Any]) -> str:
    return (
        f"{row['prompt']}\n\n"
        "Exact metadata to echo in the JSON:\n"
        f"- bias_id: {row['bias_id']}\n"
        f"- event_id: {row['event_id']}\n"
        f"- frame: {row['frame']}\n"
        f"- prompt_arm: {row['prompt_arm']}\n\n"
        "Do not include markdown fences. Do not explain outside the JSON. "
        "Use the exact bias_id, event_id, frame, and prompt_arm values from the requested schema."
    )


def select_rows(
    rows: list[dict[str, Any]],
    *,
    families: set[str] | None,
    routes: set[str] | None,
    include_completed: bool,
    done: set[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        if row.get("pilot_id") != PILOT_ID:
            continue
        if families and str(row.get("family")) not in families:
            continue
        if routes and str(row.get("runtime_route")) not in routes:
            continue
        if not include_completed and row.get("dispatch_id") in done:
            continue
        selected.append(row)
    return selected


def run_row(
    row: dict[str, Any],
    *,
    timeout_seconds: int,
    codex_model: str,
    gemini_model: str,
    trace_dir: Path,
) -> dict[str, Any]:
    route = str(row.get("runtime_route") or "")
    runtime = SUBSCRIPTION_RUNTIME_ROUTES.get(route)
    if runtime is None and route != GEMINI_RUNTIME_ROUTE:
        return {
            "schema": "gp245-anti-bias-collapse-call-receipt-v1",
            "pilot_id": PILOT_ID,
            "dispatch_id": row.get("dispatch_id"),
            "family": row.get("family"),
            "agent_id": row.get("agent_id"),
            "runtime_route": route,
            "schema_ok": False,
            "p_success": None,
            "parsed": {},
            "raw_response": "",
            "returncode": None,
            "error": f"unsupported_runtime_route:{route}",
            "fired_at": now_iso(),
        }
    fired_at = now_iso()
    prompt = build_prompt(row)
    if route == GEMINI_RUNTIME_ROUTE:
        from src.ztare.common.llm_runtime import LLMRuntime  # lazy import for optional deps

        command_preview = ["LLMRuntime.call_text", f"model={gemini_model}", f"<prompt:{row.get('dispatch_id')}>"]
        try:
            response = LLMRuntime().call_text(
                prompt,
                model_id=gemini_model,
                fallback_model_ids=(),
                config={"temperature": 0.0},
                max_tokens=512,
                retries=2,
                timeout_seconds=timeout_seconds,
                request_label=f"anti_bias_collapse::{row.get('dispatch_id')}",
            )
            raw_response = response.text or ""
            stderr = ""
            returncode = 0
            error = None
        except Exception as exc:
            raw_response = ""
            stderr = repr(exc)
            returncode = 1
            error = str(exc)
        receipt = receipt_from_run(
            row=row,
            runtime="gemini",
            raw_response=raw_response,
            stderr=stderr,
            returncode=returncode,
            command_preview=command_preview,
            recovery_note=None,
            fired_at=fired_at,
        )
        if error:
            receipt["error"] = error
        trace = {
            "schema": "gp245-anti-bias-collapse-call-trace-v1",
            "dispatch_row": row,
            "prompt": prompt,
            "receipt": {k: v for k, v in receipt.items() if k not in {"raw_response"}},
            "raw_response": raw_response,
            "stderr": stderr,
            "command_preview": command_preview,
        }
        path = trace_path(trace_dir, str(row.get("dispatch_id")))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt["trace_path"] = str(path.relative_to(REPO))
        return receipt

    run = run_subscription_agent_with_recovery(
        runtime=runtime,
        prompt=prompt,
        agent_id=str(row.get("agent_id") or row.get("family") or runtime),
        repo=REPO,
        session_state=None,
        timeout_seconds=timeout_seconds,
        default_codex_model=codex_model,
        codex_sandbox="read-only",
        claude_disallowed_tools=(
            "Bash",
            "Read",
            "Glob",
            "Grep",
            "Edit",
            "Write",
            "WebFetch",
            "WebSearch",
        ),
    )
    command_preview = redact_prompt_command(run.final_command, f"<prompt:{row.get('dispatch_id')}>")
    receipt = receipt_from_run(
        row=row,
        runtime=runtime,
        raw_response=run.result.stdout or "",
        stderr=run.result.stderr or "",
        returncode=int(run.result.returncode),
        command_preview=command_preview,
        recovery_note=run.recovery_note,
        fired_at=fired_at,
    )
    trace = {
        "schema": "gp245-anti-bias-collapse-call-trace-v1",
        "dispatch_row": row,
        "prompt": prompt,
        "receipt": {k: v for k, v in receipt.items() if k not in {"raw_response"}},
        "raw_response": run.result.stdout or "",
        "stderr": run.result.stderr or "",
        "command_preview": command_preview,
    }
    path = trace_path(trace_dir, str(row.get("dispatch_id")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt["trace_path"] = str(path.relative_to(REPO))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES)
    parser.add_argument("--trace-dir", type=Path, default=DEFAULT_TRACE_DIR)
    parser.add_argument("--family", action="append", help="Filter to a family; repeatable.")
    parser.add_argument("--runtime-route", action="append", help="Filter to a runtime route; repeatable.")
    parser.add_argument("--max-calls", type=int, default=1)
    parser.add_argument("--mode", choices=["preview", "live"], default="preview")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--codex-model", default="gpt-5.4-mini")
    parser.add_argument("--gemini-model", default="gemini-2.5-flash")
    parser.add_argument("--include-completed", action="store_true")
    args = parser.parse_args()

    rows = load_jsonl(args.queue)
    done = completed_dispatch_ids(args.calls)
    selected = select_rows(
        rows,
        families=set(args.family or []) or None,
        routes=set(args.runtime_route or []) or None,
        include_completed=args.include_completed,
        done=done,
    )
    if args.max_calls >= 0:
        selected = selected[: args.max_calls]
    summary = {
        "schema": "gp245-anti-bias-collapse-dispatch-runner-v1",
        "mode": args.mode,
        "queue": str(args.queue),
        "calls": str(args.calls),
        "failures": str(args.failures),
        "trace_dir": str(args.trace_dir),
        "selected_rows": len(selected),
        "already_completed": len(done),
        "families": sorted(set(str(row.get("family")) for row in selected)),
        "runtime_routes": sorted(set(str(row.get("runtime_route")) for row in selected)),
    }
    if args.mode == "preview":
        summary["dispatch_ids"] = [row.get("dispatch_id") for row in selected[:20]]
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    receipts: list[dict[str, Any]] = []
    for row in selected:
        receipt = run_row(
            row,
            timeout_seconds=args.timeout_seconds,
            codex_model=args.codex_model,
            gemini_model=args.gemini_model,
            trace_dir=args.trace_dir,
        )
        if receipt.get("schema_ok"):
            append_jsonl(args.calls, receipt)
        else:
            append_jsonl(args.failures, receipt)
        receipts.append(receipt)
        print(json.dumps({"dispatch_id": receipt.get("dispatch_id"), "schema_ok": receipt.get("schema_ok"), "p_success": receipt.get("p_success")}, sort_keys=True))
    summary["written_rows"] = len(receipts)
    summary["schema_ok"] = sum(1 for row in receipts if row.get("schema_ok"))
    summary["failed_rows"] = [row.get("dispatch_id") for row in receipts if not row.get("schema_ok")]
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["schema_ok"] == len(receipts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
