"""Deterministic pre-spend plan preview for autoresearch entry."""
from __future__ import annotations

import shlex
from typing import Any


def _split_command(command: str | None) -> list[str]:
    if not command:
        return []
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _flag_present(command: str | None, flag: str) -> bool:
    tokens = _split_command(command)
    return flag in tokens or any(token.startswith(f"{flag}=") for token in tokens)


def _flag_value(command: str | None, flag: str) -> str | None:
    tokens = _split_command(command)
    for idx, token in enumerate(tokens):
        if token == flag and idx + 1 < len(tokens):
            return tokens[idx + 1]
        if token.startswith(f"{flag}="):
            return token.split("=", 1)[1]
    return None


def quote_arg(value: Any) -> str:
    return shlex.quote(str(value))


def route_command_for_task(
    *,
    task: str,
    project: str = "",
    rubric: str = "",
    intake: str = "",
) -> str | None:
    if not str(task or "").strip():
        return None
    parts = ["ztare", "autoresearch", "route", "--task", quote_arg(task)]
    if project:
        parts.extend(["--project", quote_arg(project)])
    if rubric:
        parts.extend(["--rubric", quote_arg(rubric)])
    if intake:
        parts.extend(["--intake", quote_arg(intake)])
    return " ".join(parts)


def run_command_for_project(
    *,
    project: str,
    rubric: str,
    intake: str = "",
    preflight_only: bool = False,
) -> str | None:
    if not project or not rubric:
        return None
    parts = [
        "ztare",
        "autoresearch",
        "run",
        "--project",
        quote_arg(project),
        "--rubric",
        quote_arg(rubric),
    ]
    if intake:
        parts.extend(["--intake", quote_arg(intake)])
    if preflight_only:
        parts.append("--preflight-only")
    return " ".join(parts)


def _normal_string_list(values: list[Any] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        item = str(value or "").strip()
        if item and item not in out:
            out.append(item)
    return out


def _workspace_prefix(project: str) -> str:
    return f"projects/{project}/workspace" if project else "project workspace"


def _budget_summary(run_command: str | None) -> dict[str, Any]:
    fallback_enabled = _flag_present(run_command, "--allow-model-fallback")
    return {
        "iteration_budget": _flag_value(run_command, "--iters") or "caller_selected",
        "llm_timeout_seconds": _flag_value(run_command, "--llm-timeout-seconds")
        or "runtime_default",
        "llm_retries": _flag_value(run_command, "--llm-retries") or "runtime_default",
        "model_fallback_policy": (
            "explicitly_enabled" if fallback_enabled else "disabled_by_default"
        ),
        "provider_spend_starts_at": (
            "bounded_loop_run" if run_command else "not_planned_until_surface_ready"
        ),
    }


def build_autoresearch_plan_preview(
    *,
    decision: str | None = None,
    project: str = "",
    rubric: str = "",
    route_command: str | None = None,
    preflight_command: str | None = None,
    run_command: str | None = None,
    can_run_now: bool = False,
    preflight_admitted: bool = False,
    missing: list[Any] | None = None,
    blocking_missing: list[Any] | None = None,
    source: str | None = None,
    worker_transport: str = "",
    provider_failure_observed: bool = False,
) -> dict[str, Any]:
    """Return a no-model-call preview of the proposed autoresearch execution."""
    missing_items = _normal_string_list(missing)
    blocking_items = _normal_string_list(blocking_missing)
    available = bool(decision or route_command or preflight_command or run_command)
    can_launch_loop = bool(can_run_now and run_command and not blocking_items)
    if not available:
        status = "unavailable"
    elif blocking_items:
        status = "blocked_before_kernel_entry"
    elif missing_items and not can_run_now:
        status = "surface_preparation_required"
    elif can_launch_loop:
        status = "ready_for_bounded_run" if preflight_admitted else "ready_for_preflight"
    elif can_run_now:
        status = "ready_decision_without_run_command"
    else:
        status = "routing_only"

    if can_launch_loop and preflight_admitted and run_command:
        recommended_first_command = run_command
    elif can_launch_loop and preflight_command:
        recommended_first_command = preflight_command
    else:
        recommended_first_command = route_command or preflight_command or run_command

    route_step_is_declared_run = bool(route_command and route_command == run_command)
    route_step_command = None if route_step_is_declared_run else route_command
    dependency_order: list[dict[str, Any]] = [
        {
            "id": "intake_declared_run" if route_step_is_declared_run else "route_decision",
            "description": (
                "the project intake already declares the bounded run command"
                if route_step_is_declared_run
                else "check whether the task belongs in the in-loop kernel"
            ),
            "model_calls": False,
            "command": route_step_command,
        }
    ]
    if blocking_items or (missing_items and not can_run_now):
        dependency_order.append(
            {
                "id": "repair_surfaces",
                "description": "prepare the missing claim, rubric, evaluator, source, or artifact surface",
                "model_calls": False,
                "missing": blocking_items or missing_items,
            }
        )
    if preflight_command:
        dependency_order.append(
            {
                "id": "preflight_only",
                "description": "run launch checks without mutator or judge model calls",
                "model_calls": False,
                "command": preflight_command,
                "status": "completed" if preflight_admitted else "pending",
            }
        )
    if run_command:
        dependency_order.append(
            {
                "id": "bounded_loop_run",
                "description": "run the in-loop mutator/evaluator cycle after preflight",
                "model_calls": True,
                "command": run_command,
            }
        )
    dependency_order.append(
        {
            "id": "trace_health_review",
            "description": "inspect trace and health output before treating a run as evidence",
            "model_calls": False,
        }
    )

    workers: list[dict[str, Any]] = [
        {
            "role": "route_readiness_check",
            "work_mode": "deterministic",
            "model_calls": False,
        }
    ]
    if blocking_items or (missing_items and not can_run_now):
        workers.append(
            {
                "role": "surface_preparation",
                "work_mode": "out_of_loop_prep",
                "model_calls": False,
            }
        )
    if preflight_command:
        workers.append(
            {
                "role": "launch_preflight",
                "work_mode": "deterministic",
                "model_calls": False,
            }
        )
    if run_command:
        transport = worker_transport or "configured_provider"
        workers.extend(
            [
                {
                    "role": "mutator",
                    "work_mode": "in_loop_autoresearch",
                    "transport": transport,
                    "model_calls": True,
                },
                {
                    "role": "judge_or_gate",
                    "work_mode": "in_loop_autoresearch",
                    "transport": transport,
                    "model_calls": True,
                },
            ]
        )

    if provider_failure_observed:
        risk = "provider_runtime_failure_misread_as_research_signal"
        risk_reason = (
            "recent telemetry shows charged input with no model output; retry or inspect "
            "the provider path before interpreting loop failure scientifically"
        )
    elif blocking_items:
        risk = "blocked_kernel_entry"
        risk_reason = "blocking readiness debt must clear before the in-loop kernel is meaningful"
    elif missing_items and not can_run_now:
        risk = "underspecified_surface"
        risk_reason = "the task still needs a bounded claim, evaluator, rubric, or artifact surface"
    elif run_command and not preflight_command:
        risk = "paid_run_without_preflight_command"
        risk_reason = "a run command is available but no model-free preflight command is surfaced"
    else:
        risk = "candidate_evidence_or_metric_gaming"
        risk_reason = (
            "the first paid loop can still produce a plausible artifact that only passes a weak "
            "rubric; inspect the trace before promotion"
        )

    workspace = _workspace_prefix(project)
    expected_outputs = (
        [
            f"{workspace}/eval_history.jsonl",
            f"{workspace}/iteration_telemetry.jsonl",
            f"{workspace}/latest_eval.json or equivalent score artifact",
            "ztare autoresearch trace/health JSON",
        ]
        if can_run_now or run_command
        else [
            "bounded claim/eigenquestion artifact",
            "rubric or deterministic evaluator surface",
            "source/evidence refs tied to the project intake",
        ]
    )

    return {
        "schema": "ztare-autoresearch-plan-preview-v1",
        "available": available,
        "status": status,
        "source": source,
        "project": project or None,
        "rubric": rubric or None,
        "model_calls_before_confirmation": False,
        "recommended_first_command": recommended_first_command,
        "dependency_order": dependency_order,
        "worker_count": len(workers),
        "workers": workers,
        "budget": _budget_summary(run_command),
        "expected_outputs": expected_outputs,
        "largest_quality_drop_risk": risk,
        "risk_reason": risk_reason,
    }
