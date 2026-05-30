"""Budget guard for out-of-loop LLM/script swarms.

This module is intentionally small and general-purpose.  It gives scripts a
shared way to:

* estimate cost before an LLM call,
* enforce a per-run cap and the role/day spend caps,
* record actual spend after telemetry is returned,
* optionally write an operator approval gate under ``org/gates/pending``.

It does not dispatch any LLM calls by itself.  Callers still choose the model
and execution policy; this guard only makes the money boundary explicit.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ztare.common.paths import REPO_ROOT
from src.ztare.supervisor.spend_tracker import check_budget_allows, record_spend
from src.ztare.supervisor.supervisor_usage import estimate_cost_usd


DEFAULT_TOKEN_CHARS = 3
DEFAULT_ROLE_ID = "research_director"


class LLMBudgetDenied(RuntimeError):
    """Raised when a paid LLM call is not authorized by the budget guard."""


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def estimate_tokens_from_text(text: str, *, chars_per_token: int = DEFAULT_TOKEN_CHARS) -> int:
    """Conservative text-to-token estimate.

    The runtime retry tracker also uses roughly ``len(prompt)//3`` for
    stealth-bill estimates.  Keeping the same convention errs on the side of
    overestimating spend, which is the correct failure direction.
    """
    return max(1, (len(text) + chars_per_token - 1) // chars_per_token)


@dataclass(frozen=True)
class LLMCallEstimate:
    model_name: str | None
    input_tokens: int
    output_tokens: int
    n_calls: int
    estimated_cost_usd: float
    label: str


def estimate_llm_call_cost(
    *,
    prompt: str,
    model_name: str | None,
    max_output_tokens: int,
    n_calls: int = 1,
    label: str = "llm_call",
) -> LLMCallEstimate:
    input_tokens = estimate_tokens_from_text(prompt)
    output_tokens = max(0, int(max_output_tokens))
    cost = estimate_cost_usd(
        model_name=model_name,
        input_tokens=input_tokens * n_calls,
        output_tokens=output_tokens * n_calls,
    )
    return LLMCallEstimate(
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        n_calls=n_calls,
        estimated_cost_usd=cost,
        label=label,
    )


def estimate_from_usage(usage: Any, *, fallback: LLMCallEstimate | None = None) -> float:
    """Compute cost from an ``LLMRuntime`` usage object, falling back to estimate."""
    if usage is None:
        return fallback.estimated_cost_usd if fallback else 0.0
    direct_cost = getattr(usage, "direct_cost_usd", None)
    if direct_cost is not None:
        return float(direct_cost)
    model_name = getattr(usage, "model_name", None)
    cost = estimate_cost_usd(
        model_name=model_name,
        input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        cache_creation_input_tokens=int(
            getattr(usage, "cache_creation_input_tokens", 0) or 0),
        cache_read_input_tokens=int(
            getattr(usage, "cache_read_input_tokens", 0) or 0),
        thinking_tokens=int(getattr(usage, "thinking_tokens", 0) or 0),
    )
    return cost or (fallback.estimated_cost_usd if fallback else 0.0)


@dataclass
class LLMBudgetSession:
    """Per-run guard for one script invocation."""

    allow_paid: bool = False
    max_total_cost_usd: float | None = None
    role_id: str | None = DEFAULT_ROLE_ID
    session_id: str | None = None
    action: str = "llm_swarm"
    record_actual_spend: bool = True

    reserved_estimated_cost_usd: float = 0.0
    actual_cost_usd: float = 0.0

    def preflight(
        self,
        *,
        prompt: str,
        model_name: str | None,
        max_output_tokens: int,
        label: str,
        n_calls: int = 1,
        reserve: bool = True,
    ) -> LLMCallEstimate:
        estimate = estimate_llm_call_cost(
            prompt=prompt,
            model_name=model_name,
            max_output_tokens=max_output_tokens,
            n_calls=n_calls,
            label=label,
        )
        if not self.allow_paid:
            raise LLMBudgetDenied(
                "paid LLM call blocked: rerun with --allow-paid after reviewing "
                f"estimate ${estimate.estimated_cost_usd:.4f}"
            )
        if self.max_total_cost_usd is not None:
            after = self.reserved_estimated_cost_usd + estimate.estimated_cost_usd
            if after > self.max_total_cost_usd:
                raise LLMBudgetDenied(
                    f"run cap exceeded: reserved ${after:.4f} > "
                    f"--max-total-cost-usd ${self.max_total_cost_usd:.4f}"
                )
        allowed, reason = check_budget_allows(
            estimated_cost_usd=estimate.estimated_cost_usd,
            action=f"{self.action}:{label}",
            session_id=self.session_id,
            role_id=self.role_id,
        )
        if not allowed:
            raise LLMBudgetDenied(reason)
        if reserve:
            self.reserved_estimated_cost_usd += estimate.estimated_cost_usd
        return estimate

    def record_response(
        self,
        *,
        usage: Any,
        fallback_estimate: LLMCallEstimate,
        label: str,
    ) -> float:
        cost = estimate_from_usage(usage, fallback=fallback_estimate)
        self.actual_cost_usd += cost
        if self.record_actual_spend and cost > 0:
            record_spend(
                cost_usd=cost,
                category="llm",
                action=f"{self.action}:{label}",
                model_name=getattr(usage, "model_name", None)
                    or fallback_estimate.model_name,
                session_id=self.session_id,
                notes=(
                    f"estimated_preflight_usd={fallback_estimate.estimated_cost_usd:.8f}",
                    f"input_tokens={getattr(usage, 'input_tokens', fallback_estimate.input_tokens)}",
                    f"output_tokens={getattr(usage, 'output_tokens', fallback_estimate.output_tokens)}",
                ),
            )
        return cost


def budget_report(estimate: LLMCallEstimate, *, max_total_cost_usd: float | None = None) -> dict[str, Any]:
    return {
        "label": estimate.label,
        "model_name": estimate.model_name,
        "input_tokens_est": estimate.input_tokens,
        "max_output_tokens": estimate.output_tokens,
        "n_calls": estimate.n_calls,
        "estimated_cost_usd": estimate.estimated_cost_usd,
        "max_total_cost_usd": max_total_cost_usd,
    }


def print_budget_report(estimate: LLMCallEstimate, *, max_total_cost_usd: float | None = None) -> None:
    cap = "" if max_total_cost_usd is None else f"  cap=${max_total_cost_usd:.4f}"
    print(
        f"  budget[{estimate.label}]: model={estimate.model_name} "
        f"input~{estimate.input_tokens} max_out={estimate.output_tokens} "
        f"calls={estimate.n_calls} est=${estimate.estimated_cost_usd:.4f}{cap}"
    )


def write_pending_operator_gate(
    *,
    estimate: LLMCallEstimate,
    action: str,
    reason: str,
    max_total_cost_usd: float | None,
    out_dir: Path | None = None,
) -> Path:
    """Write a pending org gate requesting approval for paid LLM spend."""
    out_root = out_dir or (REPO_ROOT / "org" / "gates" / "pending")
    out_root.mkdir(parents=True, exist_ok=True)
    safe_action = re.sub(r"[^A-Za-z0-9_.-]+", "_", action).strip("_")[:80]
    path = out_root / f"{utc_stamp()}_{safe_action or 'llm_budget'}.json"
    payload = {
        "gate_id": path.stem,
        "kind": "paid_llm_budget_approval",
        "status": "pending",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "reason": reason,
        "estimate": asdict(estimate),
        "max_total_cost_usd": max_total_cost_usd,
        "choices": [
            {
                "id": "approve",
                "consequence": "operator may rerun with --allow-paid and the stated cap",
            },
            {
                "id": "deny",
                "consequence": "do not execute the paid LLM call",
            },
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path

