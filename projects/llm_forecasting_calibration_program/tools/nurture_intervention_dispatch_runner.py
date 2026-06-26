#!/usr/bin/env python3
"""Run forecast-nurture dispatch rows and write DB-compatible receipts."""
from __future__ import annotations

import argparse
import json
import os
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
DEFAULT_QUEUE = WORKSPACE / "n1_nurture_intervention_smoke_queue.jsonl"
DEFAULT_CALLS = WORKSPACE / "n1_nurture_intervention_calls.jsonl"
DEFAULT_FAILURES = WORKSPACE / "n1_nurture_intervention_failed_calls.jsonl"
DEFAULT_TRACE_DIR = WORKSPACE / "traces/n1_nurture_intervention_v1"
PILOT_ID = "n1_nurture_intervention_v1"
SUBSCRIPTION_RUNTIME_ROUTES = {
    "claude_subscription": "claude",
    "codex_subscription": "codex",
}
GEMINI_RUNTIME_ROUTE = "gemini_api_or_manual"
DEEPSEEK_RUNTIME_ROUTE = "deepseek_api_or_manual"
RETRYABLE_FAILURE_CLASSES = {"blocked_runtime", "blocked_auth", "schema_recovered_by_current_validator"}

REQUIRED_BY_CONDITION = {
    "baseline": {"p_success"},
    "diagnostic_only": {"p_success", "worry", "bid_ask_low", "bid_ask_high", "self_predicted_brier"},
    "reference_class_numeric": {
        "p_success_before_reference",
        "reference_class_yes_rate_used",
        "p_success",
        "revision_delta",
    },
    "contrastive_numeric_revision": {
        "p_success_initial",
        "contrast_relative_likelihood",
        "p_success",
        "revision_delta",
    },
    "probability_repair": {
        "p_success_before_repair",
        "base_rate_used",
        "p_success",
        "revision_delta",
        "repair_rationale_short",
    },
    "selection_aware_probability_repair": {
        "p_success_before_repair",
        "raw_event_base_rate",
        "market_selected_base_rate",
        "chosen_reference_class",
        "chosen_base_rate",
        "p_success",
        "revision_delta",
        "repair_rationale_short",
    },
    "guarded_selection_aware_probability_repair": {
        "baseline_anchor_p",
        "p_success_before_repair",
        "raw_event_base_rate",
        "market_selected_base_rate",
        "selection_premium",
        "guard_decision",
        "p_success",
        "revision_delta_vs_anchor",
        "repair_rationale_short",
    },
    "selective_action": {
        "p_success",
        "worry",
        "selected_action",
        "expected_utility",
        "action_rationale_short",
    },
    "free_prose_forecast": {
        "p_success",
        "rationale_short",
        "failure_modes_short",
    },
    "typed_carrier_forecast": {
        "source_facts",
        "residual_evidence_carrier",
        "nearest_confuser",
        "action_program",
        "deterministic_check",
        "p_success",
    },
    "carrier_to_action_execution": {
        "source_facts",
        "residual_evidence_carrier",
        "nearest_confuser",
        "action_program",
        "deterministic_check",
        "p_success",
        "selected_action",
        "expected_utility",
        "action_rationale_short",
    },
    "bare_forecast": {"p_success"},
    "length_matched_placebo": {"format_check", "p_success"},
    "expert_training_prompt": {"base_rate", "update_reason", "main_uncertainty", "p_success"},
    "audit_informed_prompt": {
        "source_visibility_check",
        "label_vintage_check",
        "base_rate",
        "overconfidence_check",
        "p_success",
    },
    "failure_mode_specific_prompt": {"likely_error", "revision_reason", "p_success"},
}
ACTION_VALUES = {
    "forecast",
    "forecast_yes",
    "forecast_no",
    "yes",
    "no",
    "abstain",
    "reroute_or_judge",
    "reroute",
    "judge",
}
FORECAST_ACTION_ALIASES = {"forecast", "forecast_yes", "forecast_no", "yes", "no"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


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


def carrier_schema_ok(condition: str, parsed: dict[str, Any], p_success: float | None) -> bool:
    required = REQUIRED_BY_CONDITION.get(condition)
    if not required or p_success is None:
        return False
    if any(key not in parsed for key in required):
        return False
    if condition == "probability_repair":
        before = numeric_probability(parsed.get("p_success_before_repair"))
        base_rate = numeric_probability(parsed.get("base_rate_used"))
        if before is None or base_rate is None:
            return False
    if condition == "selection_aware_probability_repair":
        before = numeric_probability(parsed.get("p_success_before_repair"))
        raw_base = numeric_probability(parsed.get("raw_event_base_rate"))
        selected_base = numeric_probability(parsed.get("market_selected_base_rate"))
        chosen_base = numeric_probability(parsed.get("chosen_base_rate"))
        reference_class = str(parsed.get("chosen_reference_class") or "").strip()
        if before is None or raw_base is None or selected_base is None or chosen_base is None:
            return False
        if not reference_class:
            return False
    if condition == "guarded_selection_aware_probability_repair":
        anchor = numeric_probability(parsed.get("baseline_anchor_p"))
        before = numeric_probability(parsed.get("p_success_before_repair"))
        raw_base = numeric_probability(parsed.get("raw_event_base_rate"))
        selected_base = numeric_probability(parsed.get("market_selected_base_rate"))
        premium = parsed.get("selection_premium")
        try:
            premium_float = float(premium)
        except (TypeError, ValueError):
            premium_float = None
        guard_decision = str(parsed.get("guard_decision") or "").strip()
        if anchor is None or before is None or raw_base is None or selected_base is None:
            return False
        if premium_float is None or not guard_decision:
            return False
    if condition == "selective_action":
        action = normalize_action(parsed.get("selected_action"))
        if action not in ACTION_VALUES:
            return False
        parsed["selected_action_normalized"] = "forecast" if action in FORECAST_ACTION_ALIASES else action
    if condition == "free_prose_forecast":
        if not str(parsed.get("rationale_short") or "").strip():
            return False
        if not str(parsed.get("failure_modes_short") or "").strip():
            return False
    if condition == "typed_carrier_forecast":
        source_facts = parsed.get("source_facts")
        action_program = parsed.get("action_program")
        if not isinstance(source_facts, list) or not (2 <= len(source_facts) <= 5):
            return False
        if not isinstance(action_program, list) or not (2 <= len(action_program) <= 4):
            return False
        for key in ("residual_evidence_carrier", "nearest_confuser", "deterministic_check"):
            if not str(parsed.get(key) or "").strip():
                return False
    if condition == "carrier_to_action_execution":
        source_facts = parsed.get("source_facts")
        action_program = parsed.get("action_program")
        action = normalize_action(parsed.get("selected_action"))
        if not isinstance(source_facts, list) or not (2 <= len(source_facts) <= 5):
            return False
        if not isinstance(action_program, list) or not (2 <= len(action_program) <= 4):
            return False
        for key in ("residual_evidence_carrier", "nearest_confuser", "deterministic_check", "action_rationale_short"):
            if not str(parsed.get(key) or "").strip():
                return False
        if action not in ACTION_VALUES:
            return False
        parsed["selected_action_normalized"] = "forecast" if action in FORECAST_ACTION_ALIASES else action
    if condition in {
        "length_matched_placebo",
        "expert_training_prompt",
        "audit_informed_prompt",
        "failure_mode_specific_prompt",
    }:
        for key in REQUIRED_BY_CONDITION[condition] - {"p_success"}:
            if not str(parsed.get(key) or "").strip():
                return False
    if condition in {"expert_training_prompt", "audit_informed_prompt"}:
        if numeric_probability(parsed.get("base_rate")) is None:
            return False
    return True


def normalize_action(value: Any) -> str:
    action = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if action in {"forecasting", "make_forecast"}:
        return "forecast"
    if action in {"forecast_yes", "yes", "predict_yes", "forecast_y"}:
        return "forecast_yes"
    if action in {"forecast_no", "no", "predict_no", "forecast_n"}:
        return "forecast_no"
    if action in {"reroute", "judge", "reroute_or_judge", "reroute/judge"}:
        return "reroute_or_judge" if action == "reroute/judge" else action
    return action


def receipt_current_schema_ok(row: dict[str, Any]) -> bool:
    condition = str(row.get("condition") or "")
    parsed = row.get("parsed") if isinstance(row.get("parsed"), dict) else {}
    p_success = numeric_probability(row.get("p_success"))
    if p_success is None:
        p_success = numeric_probability(parsed.get("p_success"))
    return bool(row.get("returncode") == 0 and carrier_schema_ok(condition, parsed, p_success))


def classify_failure(receipt: dict[str, Any]) -> str | None:
    """Classify non-scientific failures so they do not consume dispatch rows."""
    if receipt.get("schema_ok"):
        return None
    raw = str(receipt.get("raw_response") or "")
    stderr = str(receipt.get("stderr_tail") or "")
    error = str(receipt.get("error") or "")
    combined = "\n".join([raw, stderr, error]).lower()
    if "not logged in" in combined or "please run /login" in combined:
        return "blocked_auth"
    if "failed to initialize in-process app-server client" in combined:
        return "blocked_runtime"
    if "session limit" in combined and "resets" in combined:
        return "blocked_runtime"
    if "operation not permitted" in combined and str(receipt.get("runtime")) == "codex":
        return "blocked_runtime"
    if "nodename nor servname provided" in combined or "temporary failure in name resolution" in combined:
        return "blocked_runtime"
    if "api key" in combined or "permission denied" in combined or "unauthorized" in combined:
        return "blocked_auth"
    if "unsupported_runtime_route" in combined:
        return "unsupported_runtime"
    if receipt_current_schema_ok(receipt):
        return "schema_recovered_by_current_validator"
    if receipt.get("returncode") not in (0, None) and not raw.strip():
        return "runtime_error"
    return "schema_or_parse_failure"


def completed_dispatch_ids(calls: Path) -> set[str]:
    done: set[str] = set()
    for row in load_jsonl(calls):
        if row.get("schema_ok") and numeric_probability(row.get("p_success")) is not None:
            done.add(str(row.get("dispatch_id")))
    return done


def attempted_dispatch_ids(path: Path) -> set[str]:
    done: set[str] = set()
    for row in load_jsonl(path):
        dispatch_id = row.get("dispatch_id")
        if not dispatch_id:
            continue
        failure_class = str(classify_failure(row) or row.get("failure_class") or "")
        if failure_class in RETRYABLE_FAILURE_CLASSES:
            continue
        if failure_class == "schema_or_parse_failure" and receipt_current_schema_ok(row):
            continue
        done.add(str(dispatch_id))
    return done


def failure_counts(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in load_jsonl(path):
        failure_class = str(classify_failure(row) or row.get("failure_class") or "unknown")
        counts[failure_class] = counts.get(failure_class, 0) + 1
    return counts


def trace_path(trace_dir: Path, dispatch_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.=-]+", "__", dispatch_id)
    return trace_dir / f"{safe}.json"


def build_prompt(row: dict[str, Any]) -> str:
    prompt_contract = row.get("prompt_contract") if isinstance(row.get("prompt_contract"), dict) else {}
    required_fields = prompt_contract.get("required_output_fields") or ["p_success"]
    carrier = {
        key: prompt_contract[key]
        for key in (
            "reference_class",
            "contrast_case",
            "utility_regime",
            "repair_contract",
            "diagnostic_slice",
            "correction_allowed",
            "carrier_contract",
        )
        if key in prompt_contract
    }
    schema = {field: "number_or_string_as_appropriate" for field in required_fields}
    if row.get("condition") == "probability_repair":
        schema.update(
            {
                "p_success_before_repair": "number in [0,1]",
                "base_rate_used": "number in [0,1]",
                "p_success": "number in [0,1]",
                "revision_delta": "number; p_success - p_success_before_repair",
                "repair_rationale_short": "string",
            }
        )
    if row.get("condition") == "selection_aware_probability_repair":
        schema.update(
            {
                "p_success_before_repair": "number in [0,1]",
                "raw_event_base_rate": "number in [0,1]",
                "market_selected_base_rate": "number in [0,1]",
                "chosen_reference_class": "string naming the reference class used for the final probability",
                "chosen_base_rate": "number in [0,1]",
                "p_success": "number in [0,1]",
                "revision_delta": "number; p_success - p_success_before_repair",
                "repair_rationale_short": "string",
            }
        )
    if row.get("condition") == "guarded_selection_aware_probability_repair":
        schema.update(
            {
                "baseline_anchor_p": "number in [0,1]; must echo the provided baseline anchor",
                "p_success_before_repair": "number in [0,1]",
                "raw_event_base_rate": "number in [0,1]",
                "market_selected_base_rate": "number in [0,1]",
                "selection_premium": "number; market_selected_base_rate - raw_event_base_rate",
                "guard_decision": "string; one of revise, hold_anchor, cap_revision",
                "p_success": "number in [0,1]",
                "revision_delta_vs_anchor": "number; p_success - baseline_anchor_p",
                "repair_rationale_short": "string",
            }
        )
    if row.get("condition") == "free_prose_forecast":
        schema.update(
            {
                "p_success": "number in [0,1]",
                "rationale_short": "string up to 220 chars",
                "failure_modes_short": "string up to 220 chars",
            }
        )
    if row.get("condition") == "typed_carrier_forecast":
        schema.update(
            {
                "source_facts": "array of 2 to 5 short strings copied or inferred from the question/source only",
                "residual_evidence_carrier": "short string naming the uncertainty-bearing carrier field",
                "nearest_confuser": "short string naming the most plausible wrong contract class",
                "action_program": "array of 2 to 4 short imperative strings for how the probability was set",
                "deterministic_check": "short string describing the check used before emitting p_success",
                "p_success": "number in [0,1]",
            }
        )
    if row.get("condition") == "carrier_to_action_execution":
        schema.update(
            {
                "source_facts": "array of 2 to 5 short strings copied or inferred from the question/source only",
                "residual_evidence_carrier": "short string naming the uncertainty-bearing carrier field",
                "nearest_confuser": "short string naming the most plausible wrong contract class",
                "action_program": "array of 2 to 4 short imperative strings for how the probability and action were set",
                "deterministic_check": "short string describing the check used before emitting p_success and selected_action",
                "p_success": "number in [0,1]",
                "selected_action": "string; one of forecast, forecast_yes, forecast_no, abstain, reroute_or_judge",
                "expected_utility": "number under the provided utility regime",
                "action_rationale_short": "string up to 180 chars",
            }
        )
    if row.get("condition") == "length_matched_placebo":
        schema.update(
            {
                "format_check": "short string confirming that only neutral formatting was applied",
                "p_success": "number in [0,1]",
            }
        )
    if row.get("condition") == "expert_training_prompt":
        schema.update(
            {
                "base_rate": "number in [0,1]",
                "update_reason": "short string",
                "main_uncertainty": "short string",
                "p_success": "number in [0,1]",
            }
        )
    if row.get("condition") == "audit_informed_prompt":
        schema.update(
            {
                "source_visibility_check": "short string",
                "label_vintage_check": "short string",
                "base_rate": "number in [0,1]",
                "overconfidence_check": "short string",
                "p_success": "number in [0,1]",
            }
        )
    if row.get("condition") == "failure_mode_specific_prompt":
        schema.update(
            {
                "likely_error": "short string",
                "revision_reason": "short string",
                "p_success": "number in [0,1]",
            }
        )
    schema.update(
        {
            "dispatch_id": row.get("dispatch_id"),
            "contract_id": row.get("contract_id"),
            "condition": row.get("condition"),
        }
    )
    return (
        "You are making a tool-free forecast on a resolved historical forecasting contract. "
        "The true outcome is intentionally hidden. Do not browse or use tools.\n\n"
        f"Question:\n{row.get('question')}\n\n"
        f"Source: {row.get('source')} / {row.get('source_corpus')}\n"
        f"Condition: {row.get('condition')}\n"
        f"Instruction: {prompt_contract.get('instruction')}\n\n"
        f"Condition carrier:\n{json.dumps(carrier, indent=2, sort_keys=True)}\n\n"
        "Return exactly one JSON object and no markdown. "
        "All probabilities must be numbers in [0,1]. "
        f"Required JSON fields:\n{json.dumps(schema, indent=2, sort_keys=True)}\n"
    )


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
    condition = str(row.get("condition") or "")
    schema_ok = (
        returncode == 0
        and carrier_schema_ok(condition, parsed, p_success)
        and str(parsed.get("contract_id")) == str(row.get("contract_id"))
        and str(parsed.get("condition")) == condition
    )
    if schema_ok and condition == "guarded_selection_aware_probability_repair":
        parsed_anchor = numeric_probability(parsed.get("baseline_anchor_p"))
        row_anchor = numeric_probability(row.get("baseline_anchor_p"))
        schema_ok = parsed_anchor is not None and row_anchor is not None and abs(parsed_anchor - row_anchor) < 1e-9
    return {
        "schema": "gp245-n1-nurture-call-receipt-v1",
        "pilot_id": row.get("pilot_id") or PILOT_ID,
        "dispatch_id": row.get("dispatch_id"),
        "contract_id": row.get("contract_id"),
        "agent_id": row.get("agent_id") or row.get("family"),
        "family": row.get("family"),
        "runtime": runtime,
        "runtime_route": row.get("runtime_route"),
        "condition": condition,
        "primitive": row.get("primitive"),
        "source": row.get("source"),
        "source_corpus": row.get("source_corpus"),
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
    families: set[str] | None,
    routes: set[str] | None,
    conditions: set[str] | None,
    dispatch_ids: set[str] | None,
    contract_ids: set[str] | None,
    pilot_id: str,
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
        if conditions and str(row.get("condition")) not in conditions:
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
    timeout_seconds: int,
    codex_model: str,
    gemini_model: str,
    deepseek_model: str,
    trace_dir: Path,
) -> dict[str, Any]:
    route = str(row.get("runtime_route") or "")
    runtime = SUBSCRIPTION_RUNTIME_ROUTES.get(route)
    fired_at = now_iso()
    prompt = build_prompt(row)
    if runtime is None and route not in {GEMINI_RUNTIME_ROUTE, DEEPSEEK_RUNTIME_ROUTE}:
        receipt = {
            "schema": "gp245-n1-nurture-call-receipt-v1",
            "pilot_id": row.get("pilot_id") or PILOT_ID,
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
        receipt["failure_class"] = classify_failure(receipt)
        return receipt
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
                max_tokens=700,
                retries=2,
                timeout_seconds=timeout_seconds,
                request_label=f"nurture::{row.get('dispatch_id')}",
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
        previous_full_auto = os.environ.get("ZTARE_LEANMILL_AGENT_FULL_AUTO")
        if os.environ.get("ZTARE_FORECAST_AGENT_FULL_AUTO") != "1":
            os.environ["ZTARE_LEANMILL_AGENT_FULL_AUTO"] = "0"
        try:
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
        finally:
            if previous_full_auto is None:
                os.environ.pop("ZTARE_LEANMILL_AGENT_FULL_AUTO", None)
            else:
                os.environ["ZTARE_LEANMILL_AGENT_FULL_AUTO"] = previous_full_auto
        command_preview = redact_prompt_command(run.final_command, f"<prompt:{row.get('dispatch_id')}>")
        receipt = receipt_from_run(
            row=row,
            runtime=runtime or route,
            raw_response=run.result.stdout or "",
            stderr=run.result.stderr or "",
            returncode=int(run.result.returncode),
            command_preview=command_preview,
            recovery_note=run.recovery_note,
            fired_at=fired_at,
        )
        run_stdout = run.result.stdout or ""
        run_stderr = run.result.stderr or ""

    if not receipt.get("schema_ok"):
        receipt["failure_class"] = classify_failure(receipt)
    trace = {
        "schema": "gp245-n1-nurture-call-trace-v1",
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
    receipt["trace_path"] = repo_relative(path)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--failures", type=Path, default=DEFAULT_FAILURES)
    parser.add_argument("--trace-dir", type=Path, default=DEFAULT_TRACE_DIR)
    parser.add_argument("--family", action="append")
    parser.add_argument("--runtime-route", action="append")
    parser.add_argument("--condition", action="append")
    parser.add_argument("--dispatch-id", action="append")
    parser.add_argument("--contract-id", action="append")
    parser.add_argument("--pilot-id", default=PILOT_ID)
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
    done.update(attempted_dispatch_ids(args.failures))
    selected = select_rows(
        rows,
        families=set(args.family or []) or None,
        routes=set(args.runtime_route or []) or None,
        conditions=set(args.condition or []) or None,
        dispatch_ids=set(args.dispatch_id or []) or None,
        contract_ids=set(args.contract_id or []) or None,
        pilot_id=args.pilot_id,
        include_completed=args.include_completed,
        done=done,
    )
    if args.max_calls >= 0:
        selected = selected[: args.max_calls]
    summary = {
        "schema": "gp245-nurture-dispatch-runner-v2",
        "mode": args.mode,
        "queue": str(args.queue),
        "calls": str(args.calls),
        "failures": str(args.failures),
        "trace_dir": str(args.trace_dir),
        "selected_rows": len(selected),
        "already_completed": len(done),
        "failure_counts": failure_counts(args.failures),
        "retryable_failure_classes": sorted(RETRYABLE_FAILURE_CLASSES),
        "families": sorted(set(str(row.get("family")) for row in selected)),
        "conditions": sorted(set(str(row.get("condition")) for row in selected)),
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
            deepseek_model=args.deepseek_model,
            trace_dir=args.trace_dir,
        )
        append_jsonl(args.calls if receipt.get("schema_ok") else args.failures, receipt)
        receipts.append(receipt)
        print(
            json.dumps(
                {
                    "dispatch_id": receipt.get("dispatch_id"),
                    "condition": receipt.get("condition"),
                    "schema_ok": receipt.get("schema_ok"),
                    "failure_class": receipt.get("failure_class"),
                    "p_success": receipt.get("p_success"),
                },
                sort_keys=True,
            )
        )
    summary["written_rows"] = len(receipts)
    summary["schema_ok"] = sum(1 for row in receipts if row.get("schema_ok"))
    summary["failed_rows"] = [row.get("dispatch_id") for row in receipts if not row.get("schema_ok")]
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["schema_ok"] == len(receipts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
