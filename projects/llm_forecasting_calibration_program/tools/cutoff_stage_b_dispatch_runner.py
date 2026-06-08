#!/usr/bin/env python3
"""Run the frozen GP-245 Law 3 cutoff Stage-B dispatch slate.

This runner is resumable and writes append-only receipts. It does not ingest
into the DB; use ``ztare forecast cutoff-panel-ingest`` after calls land.
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


WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace"
DEFAULT_QUEUE = WORKSPACE / "cutoff_stage_b_dispatch_slate.jsonl"
DEFAULT_CALLS = WORKSPACE / "cutoff_stage_b_panel_v1_calls.jsonl"
DEFAULT_FAILURES = WORKSPACE / "cutoff_stage_b_panel_v1_failed_calls.jsonl"
DEFAULT_TRACE_DIR = WORKSPACE / "traces/cutoff_stage_b_panel_v1"
PILOT_ID = "cutoff_stage_b_panel_v1"
SUBSCRIPTION_RUNTIME_ROUTES = {
    "claude_subscription": "claude",
    "codex_subscription": "codex",
}
GEMINI_RUNTIME_ROUTE = "gemini_api_or_manual"
DEEPSEEK_RUNTIME_ROUTE = "deepseek_api_or_manual"


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
        fh.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")
        fh.flush()


def numeric_probability(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        p = float(value)
        if 0.0 <= p <= 1.0:
            return p
    return None


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


def completed_dispatch_ids(calls: Path) -> set[str]:
    done: set[str] = set()
    for row in load_jsonl(calls):
        if row.get("schema_ok") and numeric_probability(row.get("p_success")) is not None:
            done.add(str(row.get("dispatch_id")))
    return done


def trace_path(trace_dir: Path, dispatch_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.=-]+", "__", dispatch_id)
    return trace_dir / f"{safe}.json"


def receipt_from_run(
    *,
    row: dict[str, Any],
    pilot_id: str,
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
    require_cutoff_echo = bool(row.get("require_cutoff_echo", True))
    cutoff_ok = True if not require_cutoff_echo else parsed.get("cutoff_relation") == row.get("cutoff_relation")
    schema_ok = (
        returncode == 0
        and p_success is not None
        and cutoff_ok
        and parsed.get("source") == row.get("source")
        and parsed.get("topic") == row.get("topic")
    )
    return {
        "schema": "gp245-cutoff-stage-b-call-receipt-v1",
        "pilot_id": pilot_id,
        "dispatch_id": row.get("dispatch_id"),
        "contract_id": row.get("contract_id"),
        "agent_id": row.get("family"),
        "family": row.get("family"),
        "runtime": runtime,
        "runtime_route": row.get("runtime_route"),
        "condition": row.get("condition"),
        "primitive": row.get("primitive"),
        "cutoff_relation": row.get("cutoff_relation"),
        "source": row.get("source"),
        "topic": row.get("topic"),
        "base_rate_band": row.get("base_rate_band"),
        "question_length_bucket": row.get("question_length_bucket"),
        "resolve_date": row.get("resolve_date"),
        "panel_cutoff_date": row.get("panel_cutoff_date"),
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


def select_rows(
    rows: list[dict[str, Any]],
    *,
    pilot_id: str,
    families: set[str] | None,
    routes: set[str] | None,
    cutoff_relations: set[str] | None,
    dispatch_ids: set[str] | None,
    contract_ids: set[str] | None,
    include_completed: bool,
    done: set[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        if row.get("pilot_id") != pilot_id:
            continue
        if families and str(row.get("family")) not in families:
            continue
        if routes and str(row.get("runtime_route")) not in routes:
            continue
        if cutoff_relations and str(row.get("cutoff_relation")) not in cutoff_relations:
            continue
        if dispatch_ids and str(row.get("dispatch_id")) not in dispatch_ids:
            continue
        if contract_ids and str(row.get("contract_id")) not in contract_ids:
            continue
        if not include_completed and str(row.get("dispatch_id")) in done:
            continue
        selected.append(row)
    return selected


def run_row(
    row: dict[str, Any],
    *,
    pilot_id: str,
    timeout_seconds: int,
    codex_model: str,
    gemini_model: str,
    deepseek_model: str,
    trace_dir: Path,
) -> dict[str, Any]:
    route = str(row.get("runtime_route") or "")
    runtime = SUBSCRIPTION_RUNTIME_ROUTES.get(route)
    fired_at = now_iso()
    prompt = str(row.get("prompt") or "")
    if runtime is None and route not in {GEMINI_RUNTIME_ROUTE, DEEPSEEK_RUNTIME_ROUTE}:
        return {
            "schema": "gp245-cutoff-stage-b-call-receipt-v1",
            "pilot_id": pilot_id,
            "dispatch_id": row.get("dispatch_id"),
            "contract_id": row.get("contract_id"),
            "family": row.get("family"),
            "runtime_route": route,
            "schema_ok": False,
            "p_success": None,
            "parsed": {},
            "raw_response": "",
            "returncode": None,
            "error": f"unsupported_runtime_route:{route}",
            "fired_at": fired_at,
        }
    if route in {GEMINI_RUNTIME_ROUTE, DEEPSEEK_RUNTIME_ROUTE}:
        from src.ztare.common.llm_runtime import LLMRuntime  # lazy optional dependency

        model_id = gemini_model if route == GEMINI_RUNTIME_ROUTE else deepseek_model
        runtime_label = "gemini" if route == GEMINI_RUNTIME_ROUTE else "deepseek"
        command_preview = ["LLMRuntime.call_text", f"model={model_id}", f"<prompt:{row.get('dispatch_id')}>"]
        try:
            response = LLMRuntime().call_text(
                prompt,
                model_id=model_id,
                fallback_model_ids=(),
                config={"temperature": 0.0},
                max_tokens=512,
                retries=2,
                timeout_seconds=timeout_seconds,
                request_label=f"cutoff_stage_b::{row.get('dispatch_id')}",
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
            pilot_id=pilot_id,
            runtime=runtime_label,
            raw_response=raw_response,
            stderr=stderr,
            returncode=returncode,
            command_preview=command_preview,
            recovery_note=None,
            fired_at=fired_at,
        )
        if error:
            receipt["error"] = error
        run_stdout = raw_response
        run_stderr = stderr
    else:
        run = run_subscription_agent_with_recovery(
            runtime=runtime,
            prompt=prompt,
            agent_id=str(row.get("family") or runtime),
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
            pilot_id=pilot_id,
            runtime=runtime,
            raw_response=run.result.stdout or "",
            stderr=run.result.stderr or "",
            returncode=int(run.result.returncode),
            command_preview=command_preview,
            recovery_note=run.recovery_note,
            fired_at=fired_at,
        )
        run_stdout = run.result.stdout or ""
        run_stderr = run.result.stderr or ""

    trace = {
        "schema": "gp245-cutoff-stage-b-call-trace-v1",
        "dispatch_row": row,
        "prompt": prompt,
        "receipt": {k: v for k, v in receipt.items() if k != "raw_response"},
        "raw_response": run_stdout,
        "stderr": run_stderr,
        "command_preview": command_preview,
    }
    path = trace_path(trace_dir, str(row.get("dispatch_id")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        receipt["trace_path"] = str(path.resolve().relative_to(REPO))
    except ValueError:
        receipt["trace_path"] = str(path)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES)
    parser.add_argument("--trace-dir", type=Path, default=DEFAULT_TRACE_DIR)
    parser.add_argument("--pilot-id", default=PILOT_ID)
    parser.add_argument("--family", action="append")
    parser.add_argument("--runtime-route", action="append")
    parser.add_argument("--cutoff-relation", action="append")
    parser.add_argument("--dispatch-id", action="append")
    parser.add_argument("--contract-id", action="append")
    parser.add_argument("--max-calls", type=int, default=1)
    parser.add_argument("--mode", choices=["preview", "live"], default="preview")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--codex-model", default="gpt-5.4-mini")
    parser.add_argument("--gemini-model", default="gemini-2.5-flash")
    parser.add_argument("--deepseek-model", default="deepseek-chat")
    parser.add_argument("--include-completed", action="store_true")
    args = parser.parse_args()

    rows = load_jsonl(args.queue)
    done = completed_dispatch_ids(args.calls)
    selected = select_rows(
        rows,
        pilot_id=args.pilot_id,
        families=set(args.family or []) or None,
        routes=set(args.runtime_route or []) or None,
        cutoff_relations=set(args.cutoff_relation or []) or None,
        dispatch_ids=set(args.dispatch_id or []) or None,
        contract_ids=set(args.contract_id or []) or None,
        include_completed=args.include_completed,
        done=done,
    )
    if args.max_calls >= 0:
        selected = selected[: args.max_calls]
    summary = {
        "schema": "gp245-cutoff-stage-b-dispatch-runner-v1",
        "mode": args.mode,
        "pilot_id": args.pilot_id,
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
            pilot_id=args.pilot_id,
            timeout_seconds=args.timeout_seconds,
            codex_model=args.codex_model,
            gemini_model=args.gemini_model,
            deepseek_model=args.deepseek_model,
            trace_dir=args.trace_dir,
        )
        append_jsonl(args.calls if receipt.get("schema_ok") else args.failures, receipt)
        receipts.append(receipt)
        print(json.dumps({"dispatch_id": receipt.get("dispatch_id"), "schema_ok": receipt.get("schema_ok"), "p_success": receipt.get("p_success")}, sort_keys=True))
    summary["written_rows"] = len(receipts)
    summary["schema_ok"] = sum(1 for row in receipts if row.get("schema_ok"))
    summary["failed_rows"] = [row.get("dispatch_id") for row in receipts if not row.get("schema_ok")]
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["schema_ok"] == len(receipts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
