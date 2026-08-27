"""Capability-adaptive execution under a stable verification contract.

The producer of an answer is replaceable.  The task identity, evidence bytes,
output schema, verifier, tolerance, authority ceiling, and settlement receipt
are stable.  This module lets several execution modes compete without turning
an old benchmark result into a permanent architecture boundary.

Routing is deliberately non-scalar while evidence is sparse.  Unknown lanes
run as bounded shadow probes beside a declared baseline.  A lane becomes
eligible for primary routing only after enough independently verified receipts
for the same task family and capability epoch.  Eligible lanes are compared on
the cost/latency Pareto frontier; consequence and authority remain task-owned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from statistics import median
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256


EXECUTION_MODES = frozenset(
    {
        "deterministic_program",
        "direct_agent",
        "agent_authored_program",
        "verified_hybrid",
    }
)


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    return text


def _sha(value: Any, label: str) -> str:
    digest = _text(value, label).lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"{label} must be a SHA-256 digest")
    return digest


@dataclass(frozen=True, slots=True)
class ExecutionTask:
    """One frozen unit of work whose producers share an answer contract."""

    task_id: str
    task_family: str
    task_version: str
    input_payload: Mapping[str, Any]
    evidence_sha256s: tuple[str, ...]
    output_schema: str
    verifier_id: str
    verifier_version: str
    verifier_kind: str
    tolerance: float
    consequence_class: str
    authority_ceiling: str
    max_wallclock_s: int
    task_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for name in (
            "task_id",
            "task_family",
            "task_version",
            "output_schema",
            "verifier_id",
            "verifier_version",
            "verifier_kind",
            "consequence_class",
            "authority_ceiling",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), f"task.{name}"))
        evidence = tuple(sorted({_sha(row, "task evidence digest") for row in self.evidence_sha256s}))
        if not evidence:
            raise ValueError("execution task requires evidence identities")
        if not isinstance(self.input_payload, Mapping) or not self.input_payload:
            raise ValueError("execution task input_payload must be a nonempty object")
        tolerance = float(self.tolerance)
        if not 0 <= tolerance < 1:
            raise ValueError("execution task tolerance must be in [0, 1)")
        if type(self.max_wallclock_s) is not int or self.max_wallclock_s < 1:
            raise ValueError("execution task max_wallclock_s must be positive")
        object.__setattr__(self, "input_payload", dict(self.input_payload))
        object.__setattr__(self, "evidence_sha256s", evidence)
        object.__setattr__(self, "tolerance", tolerance)
        object.__setattr__(self, "task_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "ztare-execution-task-v1",
            "task_id": self.task_id,
            "task_family": self.task_family,
            "task_version": self.task_version,
            "input_payload": dict(self.input_payload),
            "evidence_sha256s": list(self.evidence_sha256s),
            "output_schema": self.output_schema,
            "verifier_id": self.verifier_id,
            "verifier_version": self.verifier_version,
            "verifier_kind": self.verifier_kind,
            "tolerance": self.tolerance,
            "consequence_class": self.consequence_class,
            "authority_ceiling": self.authority_ceiling,
            "max_wallclock_s": self.max_wallclock_s,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "task_sha256": self.task_sha256}


@dataclass(frozen=True, slots=True)
class ExecutorIdentity:
    """One versioned producer configuration, including its capability epoch."""

    executor_id: str
    mode: str
    implementation_id: str
    implementation_sha256: str
    runtime: str
    model: str
    reasoning_effort: str
    capability_epoch: str
    baseline: bool = False
    estimated_marginal_cost: float = 0.0
    executor_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for name in (
            "executor_id",
            "implementation_id",
            "runtime",
            "model",
            "reasoning_effort",
            "capability_epoch",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), f"executor.{name}"))
        mode = _text(self.mode, "executor.mode")
        if mode not in EXECUTION_MODES:
            raise ValueError(f"unsupported execution mode: {mode}")
        cost = float(self.estimated_marginal_cost)
        if cost < 0:
            raise ValueError("executor estimated_marginal_cost cannot be negative")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "implementation_sha256", _sha(
            self.implementation_sha256, "executor implementation digest"
        ))
        object.__setattr__(self, "estimated_marginal_cost", cost)
        object.__setattr__(self, "executor_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "ztare-executor-identity-v1",
            "executor_id": self.executor_id,
            "mode": self.mode,
            "implementation_id": self.implementation_id,
            "implementation_sha256": self.implementation_sha256,
            "runtime": self.runtime,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "capability_epoch": self.capability_epoch,
            "baseline": bool(self.baseline),
            "estimated_marginal_cost": self.estimated_marginal_cost,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "executor_sha256": self.executor_sha256}


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    """Settled result of one producer under one independent task verifier."""

    task_sha256: str
    task_family: str
    executor: ExecutorIdentity
    attempted_at: str
    wallclock_s: float
    marginal_cost: float
    carrier_live: bool
    output_sha256: str
    verifier_id: str
    verifier_version: str
    verifier_independent: bool
    verification_passed: bool
    residual: float | None
    reason_codes: tuple[str, ...]
    authority_granted: str
    receipt_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_sha256", _sha(self.task_sha256, "receipt task digest"))
        for name in (
            "task_family",
            "attempted_at",
            "verifier_id",
            "verifier_version",
            "authority_granted",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), f"receipt.{name}"))
        wallclock = float(self.wallclock_s)
        cost = float(self.marginal_cost)
        if wallclock < 0 or cost < 0:
            raise ValueError("execution receipt cost and wallclock cannot be negative")
        output_sha = str(self.output_sha256 or "").strip().lower()
        if self.carrier_live:
            output_sha = _sha(output_sha, "receipt output digest")
        elif output_sha:
            output_sha = _sha(output_sha, "receipt output digest")
        residual = None if self.residual is None else float(self.residual)
        if residual is not None and residual < 0:
            raise ValueError("verification residual cannot be negative")
        reasons = tuple(sorted({_text(row, "receipt reason code") for row in self.reason_codes}))
        if not reasons:
            reasons = ("verified" if self.verification_passed else "verification_failed",)
        object.__setattr__(self, "wallclock_s", wallclock)
        object.__setattr__(self, "marginal_cost", cost)
        object.__setattr__(self, "output_sha256", output_sha)
        object.__setattr__(self, "residual", residual)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "receipt_sha256", stable_sha256(self._payload()))

    @property
    def admissible_label(self) -> bool:
        return bool(self.carrier_live and self.verifier_independent)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "ztare-execution-receipt-v1",
            "task_sha256": self.task_sha256,
            "task_family": self.task_family,
            "executor": self.executor.to_dict(),
            "attempted_at": self.attempted_at,
            "wallclock_s": self.wallclock_s,
            "marginal_cost": self.marginal_cost,
            "carrier_live": bool(self.carrier_live),
            "output_sha256": self.output_sha256,
            "verifier_id": self.verifier_id,
            "verifier_version": self.verifier_version,
            "verifier_independent": bool(self.verifier_independent),
            "verification_passed": bool(self.verification_passed),
            "residual": self.residual,
            "reason_codes": list(self.reason_codes),
            "authority_granted": self.authority_granted,
            "admissible_label": self.admissible_label,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "receipt_sha256": self.receipt_sha256}


def _wilson_lower(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    denominator = 1 + z * z / total
    centre = p + z * z / (2 * total)
    radius = z * sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return max(0.0, (centre - radius) / denominator)


def capability_snapshot(
    executor: ExecutorIdentity,
    receipts: Iterable[ExecutionReceipt],
    *,
    task_family: str,
    min_verified_attempts: int,
    min_distinct_tasks: int,
    minimum_pass_rate: float,
) -> dict[str, Any]:
    """Project same-family, same-epoch evidence for one executor identity."""

    rows = [
        row for row in receipts
        if row.task_family == task_family
        and row.executor.executor_sha256 == executor.executor_sha256
        and row.admissible_label
    ]
    successes = sum(row.verification_passed for row in rows)
    distinct_tasks = len({row.task_sha256 for row in rows})
    lower = _wilson_lower(successes, len(rows))
    observed = successes / len(rows) if rows else None
    eligible = (
        len(rows) >= min_verified_attempts
        and distinct_tasks >= min_distinct_tasks
        and observed is not None
        and observed >= minimum_pass_rate
    )
    return {
        "schema": "ztare-capability-snapshot-v1",
        "task_family": task_family,
        "executor": executor.to_dict(),
        "admissible_attempt_count": len(rows),
        "verified_success_count": successes,
        "distinct_task_count": distinct_tasks,
        "observed_pass_rate": observed,
        "pass_rate_wilson_lower_95": lower if rows else None,
        "median_wallclock_s": median(row.wallclock_s for row in rows) if rows else None,
        "median_marginal_cost": median(row.marginal_cost for row in rows) if rows else None,
        "promotion_min_attempts": min_verified_attempts,
        "promotion_min_distinct_tasks": min_distinct_tasks,
        "promotion_minimum_pass_rate": minimum_pass_rate,
        "primary_route_eligible": eligible,
        "status": "eligible" if eligible else "shadow_evidence",
    }


def _pareto_ids(snapshots: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    eligible = [row for row in snapshots if row.get("primary_route_eligible")]
    frontier: list[str] = []
    for row in eligible:
        cost = float(row.get("median_marginal_cost") or 0.0)
        latency = float(row.get("median_wallclock_s") or 0.0)
        dominated = any(
            other is not row
            and float(other.get("median_marginal_cost") or 0.0) <= cost
            and float(other.get("median_wallclock_s") or 0.0) <= latency
            and (
                float(other.get("median_marginal_cost") or 0.0) < cost
                or float(other.get("median_wallclock_s") or 0.0) < latency
            )
            for other in eligible
        )
        if not dominated:
            frontier.append(str((row.get("executor") or {}).get("executor_id") or ""))
    return tuple(sorted(row for row in frontier if row))


def plan_execution_market(
    task: ExecutionTask,
    executors: Iterable[ExecutorIdentity],
    receipts: Iterable[ExecutionReceipt] = (),
    *,
    min_verified_attempts: int = 20,
    min_distinct_tasks: int = 5,
    minimum_pass_rate: float = 0.98,
    max_shadow_executors: int = 2,
) -> dict[str, Any]:
    """Return an inspectable route plan without an uncalibrated scalar score."""

    if min_verified_attempts < 1 or min_distinct_tasks < 1:
        raise ValueError("execution market promotion minima must be positive")
    if not 0 < minimum_pass_rate <= 1:
        raise ValueError("execution market minimum_pass_rate must be in (0, 1]")
    offers = tuple(executors)
    if not offers:
        raise ValueError("execution market requires at least one executor")
    if len({row.executor_sha256 for row in offers}) != len(offers):
        raise ValueError("execution market executor identities must be unique")
    baselines = tuple(row for row in offers if row.baseline)
    if len(baselines) != 1:
        raise ValueError("execution market requires exactly one declared baseline")
    rows = tuple(receipts)
    snapshots = tuple(
        capability_snapshot(
            offer,
            rows,
            task_family=task.task_family,
            min_verified_attempts=min_verified_attempts,
            min_distinct_tasks=min_distinct_tasks,
            minimum_pass_rate=minimum_pass_rate,
        )
        for offer in offers
    )
    pareto = _pareto_ids(snapshots)
    eligible_by_id = {
        str((row.get("executor") or {}).get("executor_id")): row
        for row in snapshots if row.get("primary_route_eligible")
    }
    if pareto:
        # A transparent lexicographic operating choice inside the Pareto set;
        # the full frontier remains visible to the caller.
        primary = min(
            pareto,
            key=lambda executor_id: (
                float(eligible_by_id[executor_id].get("median_marginal_cost") or 0.0),
                float(eligible_by_id[executor_id].get("median_wallclock_s") or 0.0),
                executor_id,
            ),
        )
        mode = "active_verified_route"
    else:
        primary = baselines[0].executor_id
        mode = "baseline_with_shadow_probes"
    unproven = [
        offer.executor_id for offer, snapshot in zip(offers, snapshots)
        if offer.executor_id != primary and not snapshot["primary_route_eligible"]
    ]
    shadow = tuple(unproven[: max(0, int(max_shadow_executors))])
    body = {
        "schema": "ztare-execution-market-plan-v1",
        "task_sha256": task.task_sha256,
        "task_family": task.task_family,
        "routing_mode": mode,
        "primary_executor_id": primary,
        "shadow_executor_ids": list(shadow),
        "eligible_pareto_executor_ids": list(pareto),
        "capability_snapshots": list(snapshots),
        "route_change_authority": "verified_task_family_receipts_only",
        "answer_authority_ceiling": task.authority_ceiling,
        "capital_authority": False,
    }
    return {**body, "plan_sha256": stable_sha256(body)}


__all__ = [
    "EXECUTION_MODES",
    "ExecutionReceipt",
    "ExecutionTask",
    "ExecutorIdentity",
    "capability_snapshot",
    "plan_execution_market",
]
