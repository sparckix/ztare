#!/usr/bin/env python3
"""Run N10 hard-prompt-break dispatch rows.

This runner exists because the hard-prompt-break condition is genuinely
two-stage: the first model call is forbidden to emit p_success; the second
model call executes from the frozen carrier.
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


WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace"
DEFAULT_QUEUE = WORKSPACE / "n10_hard_prompt_break_v1_dispatch_queue.jsonl"
DEFAULT_CALLS = WORKSPACE / "n10_hard_prompt_break_v1_calls.jsonl"
DEFAULT_FAILURES = WORKSPACE / "n10_hard_prompt_break_v1_failed_calls.jsonl"
DEFAULT_TRACE_DIR = WORKSPACE / "traces/n10_hard_prompt_break_v1"
PILOT_ID = "n10_hard_prompt_break_v1"
SUBSCRIPTION_RUNTIME_ROUTES = {
    "claude_subscription": "claude",
    "codex_subscription": "codex",
}

CARRIER_FIELDS = {
    "source_facts",
    "residual_evidence_carrier",
    "nearest_confuser",
    "action_program",
    "deterministic_check",
}

PROSE_STAGE_FIELDS = {
    "rationale_short",
    "failure_modes_short",
}


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


def carrier_fields_ok(parsed: dict[str, Any]) -> bool:
    if any(field not in parsed for field in CARRIER_FIELDS):
        return False
    if "p_success" in parsed or "final_probability" in parsed or "forecast_probability" in parsed:
        return False
    source_facts = parsed.get("source_facts")
    action_program = parsed.get("action_program")
    if not isinstance(source_facts, list) or not (2 <= len(source_facts) <= 5):
        return False
    if not isinstance(action_program, list) or not (2 <= len(action_program) <= 4):
        return False
    for key in ("residual_evidence_carrier", "nearest_confuser", "deterministic_check"):
        if not str(parsed.get(key) or "").strip():
            return False
    return True


def prose_stage_ok(parsed: dict[str, Any]) -> bool:
    if any(field not in parsed for field in PROSE_STAGE_FIELDS):
        return False
    if "p_success" in parsed or "final_probability" in parsed or "forecast_probability" in parsed:
        return False
    return all(str(parsed.get(key) or "").strip() for key in PROSE_STAGE_FIELDS)


def single_turn_schema_ok(condition: str, parsed: dict[str, Any], p_success: float | None) -> bool:
    if p_success is None:
        return False
    if condition == "baseline":
        return True
    if condition == "free_prose_forecast":
        return bool(str(parsed.get("rationale_short") or "").strip()) and bool(
            str(parsed.get("failure_modes_short") or "").strip()
        )
    if condition == "single_turn_typed_carrier_forecast":
        carrier_like = {key: parsed.get(key) for key in CARRIER_FIELDS}
        return carrier_fields_ok(carrier_like)
    return False


def trace_path(trace_dir: Path, dispatch_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.=-]+", "__", dispatch_id)
    return trace_dir.resolve() / f"{safe}.json"


def completed_dispatch_ids(calls: Path) -> set[str]:
    done: set[str] = set()
    for row in load_jsonl(calls):
        if row.get("schema_ok") and numeric_probability(row.get("p_success")) is not None:
            done.add(str(row.get("dispatch_id")))
    return done


def build_single_prompt(row: dict[str, Any]) -> str:
    condition = str(row.get("condition"))
    prompt_contract = row.get("prompt_contract") if isinstance(row.get("prompt_contract"), dict) else {}
    if condition == "baseline":
        schema = {"p_success": "number in [0,1]"}
    elif condition == "free_prose_forecast":
        schema = {
            "p_success": "number in [0,1]",
            "rationale_short": "string up to 220 chars",
            "failure_modes_short": "string up to 220 chars",
        }
    else:
        schema = {
            "source_facts": "array of 2 to 5 short strings copied or inferred from the question/source only",
            "residual_evidence_carrier": "short string naming the uncertainty-bearing carrier field",
            "nearest_confuser": "short string naming the most plausible wrong contract class",
            "action_program": "array of 2 to 4 short imperative strings for how the probability was set",
            "deterministic_check": "short string describing the check used before emitting p_success",
            "p_success": "number in [0,1]",
        }
    schema.update({"dispatch_id": row.get("dispatch_id"), "contract_id": row.get("contract_id"), "condition": condition})
    return (
        "You are making a tool-free forecast on a resolved historical forecasting contract. "
        "The true outcome is intentionally hidden. Do not browse or use tools.\n\n"
        f"Question:\n{row.get('question')}\n\n"
        f"Source: {row.get('source')} / {row.get('source_corpus')}\n"
        f"Condition: {condition}\n"
        f"Instruction: {prompt_contract.get('instruction')}\n\n"
        f"Condition carrier:\n{json.dumps(prompt_contract.get('carrier_contract', {}), indent=2, sort_keys=True)}\n\n"
        "Return exactly one JSON object and no markdown. "
        "All probabilities must be numbers in [0,1]. "
        f"Required JSON fields:\n{json.dumps(schema, indent=2, sort_keys=True)}\n"
    )


def build_stage1_prompt(row: dict[str, Any]) -> str:
    prompt_contract = row.get("prompt_contract") if isinstance(row.get("prompt_contract"), dict) else {}
    schema = {
        "source_facts": "array of 2 to 5 short strings copied or inferred from the question/source only",
        "residual_evidence_carrier": "short string naming the uncertainty-bearing carrier field",
        "nearest_confuser": "short string naming the most plausible wrong contract class",
        "action_program": "array of 2 to 4 short imperative strings for the later probability-setting procedure",
        "deterministic_check": "short string describing the check to run before emitting p_success later",
        "dispatch_id": row.get("dispatch_id"),
        "contract_id": row.get("contract_id"),
        "condition": row.get("condition"),
        "stage": "carrier_only",
    }
    return (
        "Stage 1 of a hard-prompt-break forecast. You must not emit a final probability, "
        "p_success, forecast_probability, or final answer. The true outcome is hidden. "
        "Do not browse or use tools.\n\n"
        f"Question:\n{row.get('question')}\n\n"
        f"Source: {row.get('source')} / {row.get('source_corpus')}\n"
        f"Carrier contract:\n{json.dumps(prompt_contract.get('carrier_contract', {}), indent=2, sort_keys=True)}\n\n"
        "Return exactly one JSON object and no markdown. "
        f"Required JSON fields:\n{json.dumps(schema, indent=2, sort_keys=True)}\n"
    )


def build_stage2_prompt(row: dict[str, Any], carrier: dict[str, Any]) -> str:
    schema = {
        "p_success": "number in [0,1]",
        "stage2_execution_check": "short string explaining how the frozen carrier was executed",
        "dispatch_id": row.get("dispatch_id"),
        "contract_id": row.get("contract_id"),
        "condition": row.get("condition"),
        "stage": "execute_frozen_carrier",
    }
    return (
        "Stage 2 of a hard-prompt-break forecast. Execute the frozen Stage-1 carrier. "
        "Do not revise the carrier fields; use them as the action program for setting p_success. "
        "The true outcome is hidden. Do not browse or use tools.\n\n"
        f"Question:\n{row.get('question')}\n\n"
        f"Source: {row.get('source')} / {row.get('source_corpus')}\n"
        f"Frozen Stage-1 carrier:\n{json.dumps(carrier, indent=2, sort_keys=True)}\n\n"
        "Return exactly one JSON object and no markdown. "
        "All probabilities must be numbers in [0,1]. "
        f"Required JSON fields:\n{json.dumps(schema, indent=2, sort_keys=True)}\n"
    )


def build_prose_stage1_prompt(row: dict[str, Any]) -> str:
    schema = {
        "rationale_short": "string up to 220 chars",
        "failure_modes_short": "string up to 220 chars",
        "dispatch_id": row.get("dispatch_id"),
        "contract_id": row.get("contract_id"),
        "condition": row.get("condition"),
        "stage": "prose_only",
    }
    return (
        "Stage 1 of a two-call prose placebo forecast. You must not emit a final "
        "probability, p_success, forecast_probability, or final answer. The true "
        "outcome is hidden. Do not browse or use tools.\n\n"
        f"Question:\n{row.get('question')}\n\n"
        f"Source: {row.get('source')} / {row.get('source_corpus')}\n\n"
        "Return exactly one JSON object and no markdown. "
        f"Required JSON fields:\n{json.dumps(schema, indent=2, sort_keys=True)}\n"
    )


def build_prose_stage2_prompt(row: dict[str, Any], frozen_prose: dict[str, Any]) -> str:
    schema = {
        "p_success": "number in [0,1]",
        "stage2_execution_check": "short string explaining how the frozen prose was used",
        "dispatch_id": row.get("dispatch_id"),
        "contract_id": row.get("contract_id"),
        "condition": row.get("condition"),
        "stage": "execute_frozen_prose",
    }
    return (
        "Stage 2 of a two-call prose placebo forecast. Use the frozen Stage-1 "
        "prose to set p_success. Do not add new evidence. The true outcome is "
        "hidden. Do not browse or use tools.\n\n"
        f"Question:\n{row.get('question')}\n\n"
        f"Source: {row.get('source')} / {row.get('source_corpus')}\n"
        f"Frozen Stage-1 prose:\n{json.dumps(frozen_prose, indent=2, sort_keys=True)}\n\n"
        "Return exactly one JSON object and no markdown. "
        "All probabilities must be numbers in [0,1]. "
        f"Required JSON fields:\n{json.dumps(schema, indent=2, sort_keys=True)}\n"
    )


def run_prompt(row: dict[str, Any], prompt: str, *, timeout_seconds: int, codex_model: str) -> dict[str, Any]:
    route = str(row.get("runtime_route") or "")
    runtime = SUBSCRIPTION_RUNTIME_ROUTES.get(route)
    if runtime is None:
        return {
            "runtime": None,
            "returncode": 1,
            "raw_response": "",
            "stderr_tail": f"unsupported_runtime_route={route}",
            "command_preview": [],
            "recovery_note": None,
        }
    result = run_subscription_agent_with_recovery(
        runtime=runtime,
        prompt=prompt,
        agent_id=str(row.get("agent_id") or row.get("family") or runtime),
        repo=REPO,
        session_state=None,
        timeout_seconds=timeout_seconds,
        default_codex_model=codex_model,
        codex_sandbox="read-only",
    )
    completed = result.result
    return {
        "runtime": runtime,
        "returncode": int(completed.returncode),
        "raw_response": completed.stdout,
        "stderr_tail": completed.stderr[-4000:],
        "command_preview": redact_prompt_command(result.final_command, f"<prompt:{row.get('dispatch_id')}>"),
        "recovery_note": result.recovery_note,
    }


def run_row(row: dict[str, Any], *, timeout_seconds: int, codex_model: str, trace_dir: Path) -> dict[str, Any]:
    fired_at = now_iso()
    condition = str(row.get("condition") or "")
    if condition not in {"hard_prompt_break_carrier_then_forecast", "two_stage_free_prose_then_forecast"}:
        prompt = build_single_prompt(row)
        result = run_prompt(row, prompt, timeout_seconds=timeout_seconds, codex_model=codex_model)
        parsed = extract_json_object(result["raw_response"]) or {}
        p_success = numeric_probability(parsed.get("p_success"))
        schema_ok = (
            result["returncode"] == 0
            and single_turn_schema_ok(condition, parsed, p_success)
            and str(parsed.get("contract_id")) == str(row.get("contract_id"))
            and str(parsed.get("condition")) == condition
        )
        receipt = {
            "schema": "gp245-n10-hard-prompt-break-call-receipt-v1",
            "pilot_id": row.get("pilot_id") or PILOT_ID,
            "dispatch_id": row.get("dispatch_id"),
            "contract_id": row.get("contract_id"),
            "agent_id": row.get("agent_id") or row.get("family"),
            "family": row.get("family"),
            "runtime": result["runtime"],
            "runtime_route": row.get("runtime_route"),
            "condition": condition,
            "primitive": row.get("primitive"),
            "source": row.get("source"),
            "source_corpus": row.get("source_corpus"),
            "p_success": p_success,
            "schema_ok": schema_ok,
            "parsed": parsed,
            "raw_response": result["raw_response"],
            "stderr_tail": result["stderr_tail"],
            "returncode": result["returncode"],
            "command_preview": result["command_preview"],
            "recovery_note": result["recovery_note"],
            "fired_at": fired_at,
        }
    elif condition == "hard_prompt_break_carrier_then_forecast":
        stage1_prompt = build_stage1_prompt(row)
        stage1 = run_prompt(row, stage1_prompt, timeout_seconds=timeout_seconds, codex_model=codex_model)
        carrier = extract_json_object(stage1["raw_response"]) or {}
        stage1_ok = (
            stage1["returncode"] == 0
            and carrier_fields_ok(carrier)
            and str(carrier.get("contract_id")) == str(row.get("contract_id"))
            and str(carrier.get("condition")) == condition
            and str(carrier.get("stage")) == "carrier_only"
        )
        if stage1_ok:
            stage2_prompt = build_stage2_prompt(row, carrier)
            stage2 = run_prompt(row, stage2_prompt, timeout_seconds=timeout_seconds, codex_model=codex_model)
            stage2_parsed = extract_json_object(stage2["raw_response"]) or {}
        else:
            stage2 = {
                "runtime": stage1["runtime"],
                "returncode": 1,
                "raw_response": "",
                "stderr_tail": "stage1_schema_failed",
                "command_preview": [],
                "recovery_note": None,
            }
            stage2_parsed = {}
        p_success = numeric_probability(stage2_parsed.get("p_success"))
        schema_ok = (
            stage1_ok
            and stage2["returncode"] == 0
            and p_success is not None
            and bool(str(stage2_parsed.get("stage2_execution_check") or "").strip())
            and str(stage2_parsed.get("contract_id")) == str(row.get("contract_id"))
            and str(stage2_parsed.get("condition")) == condition
            and str(stage2_parsed.get("stage")) == "execute_frozen_carrier"
        )
        parsed = {
            **{key: carrier.get(key) for key in CARRIER_FIELDS},
            "p_success": p_success,
            "stage2_execution_check": stage2_parsed.get("stage2_execution_check"),
            "stage1_forbade_p_success": "p_success" not in carrier,
            "stage1_schema_ok": stage1_ok,
            "stage2_schema_ok": schema_ok,
        }
        receipt = {
            "schema": "gp245-n10-hard-prompt-break-call-receipt-v1",
            "pilot_id": row.get("pilot_id") or PILOT_ID,
            "dispatch_id": row.get("dispatch_id"),
            "contract_id": row.get("contract_id"),
            "agent_id": row.get("agent_id") or row.get("family"),
            "family": row.get("family"),
            "runtime": stage1["runtime"],
            "runtime_route": row.get("runtime_route"),
            "condition": condition,
            "primitive": row.get("primitive"),
            "source": row.get("source"),
            "source_corpus": row.get("source_corpus"),
            "p_success": p_success,
            "schema_ok": schema_ok,
            "parsed": parsed,
            "raw_response": stage2["raw_response"],
            "stage1_raw_response": stage1["raw_response"],
            "stage1_stderr_tail": stage1["stderr_tail"],
            "stderr_tail": stage2["stderr_tail"],
            "returncode": stage2["returncode"],
            "command_preview": stage2["command_preview"],
            "stage1_command_preview": stage1["command_preview"],
            "recovery_note": stage2["recovery_note"],
            "stage1_recovery_note": stage1["recovery_note"],
            "fired_at": fired_at,
        }
    else:
        stage1_prompt = build_prose_stage1_prompt(row)
        stage1 = run_prompt(row, stage1_prompt, timeout_seconds=timeout_seconds, codex_model=codex_model)
        frozen_prose = extract_json_object(stage1["raw_response"]) or {}
        stage1_ok = (
            stage1["returncode"] == 0
            and prose_stage_ok(frozen_prose)
            and str(frozen_prose.get("contract_id")) == str(row.get("contract_id"))
            and str(frozen_prose.get("condition")) == condition
            and str(frozen_prose.get("stage")) == "prose_only"
        )
        if stage1_ok:
            stage2_prompt = build_prose_stage2_prompt(row, frozen_prose)
            stage2 = run_prompt(row, stage2_prompt, timeout_seconds=timeout_seconds, codex_model=codex_model)
            stage2_parsed = extract_json_object(stage2["raw_response"]) or {}
        else:
            stage2 = {
                "runtime": stage1["runtime"],
                "returncode": 1,
                "raw_response": "",
                "stderr_tail": "stage1_schema_failed",
                "command_preview": [],
                "recovery_note": None,
            }
            stage2_parsed = {}
        p_success = numeric_probability(stage2_parsed.get("p_success"))
        schema_ok = (
            stage1_ok
            and stage2["returncode"] == 0
            and p_success is not None
            and bool(str(stage2_parsed.get("stage2_execution_check") or "").strip())
            and str(stage2_parsed.get("contract_id")) == str(row.get("contract_id"))
            and str(stage2_parsed.get("condition")) == condition
            and str(stage2_parsed.get("stage")) == "execute_frozen_prose"
        )
        parsed = {
            "rationale_short": frozen_prose.get("rationale_short"),
            "failure_modes_short": frozen_prose.get("failure_modes_short"),
            "p_success": p_success,
            "stage2_execution_check": stage2_parsed.get("stage2_execution_check"),
            "stage1_forbade_p_success": "p_success" not in frozen_prose,
            "stage1_schema_ok": stage1_ok,
            "stage2_schema_ok": schema_ok,
        }
        receipt = {
            "schema": "gp245-n10-hard-prompt-break-call-receipt-v1",
            "pilot_id": row.get("pilot_id") or PILOT_ID,
            "dispatch_id": row.get("dispatch_id"),
            "contract_id": row.get("contract_id"),
            "agent_id": row.get("agent_id") or row.get("family"),
            "family": row.get("family"),
            "runtime": stage1["runtime"],
            "runtime_route": row.get("runtime_route"),
            "condition": condition,
            "primitive": row.get("primitive"),
            "source": row.get("source"),
            "source_corpus": row.get("source_corpus"),
            "p_success": p_success,
            "schema_ok": schema_ok,
            "parsed": parsed,
            "raw_response": stage2["raw_response"],
            "stage1_raw_response": stage1["raw_response"],
            "stage1_stderr_tail": stage1["stderr_tail"],
            "stderr_tail": stage2["stderr_tail"],
            "returncode": stage2["returncode"],
            "command_preview": stage2["command_preview"],
            "stage1_command_preview": stage1["command_preview"],
            "recovery_note": stage2["recovery_note"],
            "stage1_recovery_note": stage1["recovery_note"],
            "fired_at": fired_at,
        }
    path = trace_path(trace_dir, str(row.get("dispatch_id")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"dispatch": row, "receipt": receipt}, indent=2, sort_keys=True), encoding="utf-8")
    receipt["trace_path"] = str(path.relative_to(REPO))
    return receipt


def select_rows(
    rows: list[dict[str, Any]],
    *,
    pilot_id: str,
    conditions: set[str] | None,
    families: set[str] | None,
    max_rows: int | None,
    done: set[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        if row.get("pilot_id") != pilot_id:
            continue
        if conditions and str(row.get("condition")) not in conditions:
            continue
        if families and str(row.get("family")) not in families:
            continue
        if str(row.get("dispatch_id")) in done:
            continue
        selected.append(row)
        if max_rows is not None and len(selected) >= max_rows:
            break
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES)
    parser.add_argument("--trace-dir", type=Path, default=DEFAULT_TRACE_DIR)
    parser.add_argument("--pilot-id", default=PILOT_ID)
    parser.add_argument("--conditions", default="")
    parser.add_argument("--families", default="")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--codex-model", default="gpt-5.5")
    args = parser.parse_args()

    rows = load_jsonl(args.queue)
    done = completed_dispatch_ids(args.calls)
    conditions = {part.strip() for part in args.conditions.split(",") if part.strip()} or None
    families = {part.strip() for part in args.families.split(",") if part.strip()} or None
    selected = select_rows(
        rows,
        pilot_id=args.pilot_id,
        conditions=conditions,
        families=families,
        max_rows=args.max_rows,
        done=done,
    )
    print(f"selected {len(selected)} rows")
    for row in selected:
        receipt = run_row(row, timeout_seconds=args.timeout_seconds, codex_model=args.codex_model, trace_dir=args.trace_dir)
        target = args.calls if receipt.get("schema_ok") else args.failures
        append_jsonl(target, receipt)
        print(
            json.dumps(
                {
                    "dispatch_id": receipt.get("dispatch_id"),
                    "condition": receipt.get("condition"),
                    "schema_ok": receipt.get("schema_ok"),
                    "p_success": receipt.get("p_success"),
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
