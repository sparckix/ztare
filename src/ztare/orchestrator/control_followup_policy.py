"""Follow-up policy for in-loop autoresearch controls.

The loop has multiple escape controls: stagnation pivots and parallel blitzes
are the important ones here. A control firing is not evidence that the control
helped; the run needs follow-up iterations where score, champion state, or
stagnation can move. This module prevents consecutive non-emergency controls
from firing before that follow-up window has been observed.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONTROL_FOLLOWUP_WINDOW = 3
CONTROL_FOLLOWUP_SCHEMA = "ztare-control-followup-policy-v1"

_PIVOT_EVENT_TYPES = {
    "topological_pivot_profile_injected",
    "v4_bounded_mutation_override",
    "topological_pivot_emergency",
}
_EMERGENCY_CONTROL_KINDS = {
    "emergency_pivot",
    "topological_pivot_emergency",
    "v4_bounded_mutation_override",
}


@dataclass(frozen=True)
class ControlEventRef:
    iteration: int
    control_kind: str
    source_path: str


@dataclass(frozen=True)
class ControlFollowupDecision:
    schema_version: str
    candidate_control_kind: str
    allowed: bool
    decision: str
    reason: str
    followup_window: int
    prior_control_kind: str | None = None
    prior_control_iteration: int | None = None
    remaining_followup_iterations: int = 0
    prior_source_path: str | None = None


def control_followup_window(rubric_data: dict[str, Any] | None) -> int:
    """Return the number of follow-up iterations required after a control."""

    rubric = rubric_data or {}
    try:
        window = int(rubric.get("control_followup_window", DEFAULT_CONTROL_FOLLOWUP_WINDOW))
    except (TypeError, ValueError):
        window = DEFAULT_CONTROL_FOLLOWUP_WINDOW
    return max(0, window)


def _jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(row, dict):
                rows.append(row)
    except Exception:  # noqa: BLE001
        return []
    return rows


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def read_control_events(workspace_dir: str | Path) -> list[ControlEventRef]:
    """Read prior pivot/blitz controls from the existing workspace logs."""

    workspace = Path(workspace_dir)
    events: list[ControlEventRef] = []

    loop_events_path = workspace / "loop_events.jsonl"
    for row in _jsonl_rows(loop_events_path):
        event_type = str(row.get("event_type") or "")
        if event_type not in _PIVOT_EVENT_TYPES:
            continue
        iteration = _int_or_none(row.get("iteration_index") or row.get("iter"))
        if iteration is None:
            continue
        events.append(
            ControlEventRef(
                iteration=iteration,
                control_kind=event_type,
                source_path=str(loop_events_path),
            )
        )

    blitz_path = workspace / "parallel_blitz_log.jsonl"
    for row in _jsonl_rows(blitz_path):
        iteration = _int_or_none(row.get("iter") or row.get("iteration_index"))
        if iteration is None:
            continue
        events.append(
            ControlEventRef(
                iteration=iteration,
                control_kind="parallel_blitz",
                source_path=str(blitz_path),
            )
        )

    events.sort(key=lambda event: (event.iteration, event.control_kind))
    return events


def latest_prior_control(
    workspace_dir: str | Path,
    *,
    current_iteration: int,
) -> ControlEventRef | None:
    """Return the most recent control strictly before ``current_iteration``."""

    prior = [
        event for event in read_control_events(workspace_dir)
        if event.iteration < current_iteration
    ]
    if not prior:
        return None
    return max(prior, key=lambda event: event.iteration)


def evaluate_control_followup(
    workspace_dir: str | Path,
    *,
    current_iteration: int,
    rubric_data: dict[str, Any] | None,
    candidate_control_kind: str,
    emergency: bool = False,
) -> ControlFollowupDecision:
    """Decide whether a non-emergency control may fire on this iteration."""

    window = control_followup_window(rubric_data)
    if window <= 0:
        return ControlFollowupDecision(
            schema_version=CONTROL_FOLLOWUP_SCHEMA,
            candidate_control_kind=candidate_control_kind,
            allowed=True,
            decision="allow_disabled",
            reason="control_followup_window<=0",
            followup_window=window,
        )
    if emergency or candidate_control_kind in _EMERGENCY_CONTROL_KINDS:
        return ControlFollowupDecision(
            schema_version=CONTROL_FOLLOWUP_SCHEMA,
            candidate_control_kind=candidate_control_kind,
            allowed=True,
            decision="allow_emergency_or_bounded_override",
            reason=f"{candidate_control_kind} bypasses non-emergency follow-up cooldown",
            followup_window=window,
        )

    prior = latest_prior_control(workspace_dir, current_iteration=current_iteration)
    if prior is None:
        return ControlFollowupDecision(
            schema_version=CONTROL_FOLLOWUP_SCHEMA,
            candidate_control_kind=candidate_control_kind,
            allowed=True,
            decision="allow_no_prior_control",
            reason="no prior control event",
            followup_window=window,
        )

    distance = current_iteration - prior.iteration
    if distance > window:
        return ControlFollowupDecision(
            schema_version=CONTROL_FOLLOWUP_SCHEMA,
            candidate_control_kind=candidate_control_kind,
            allowed=True,
            decision="allow_followup_window_observed",
            reason=(
                f"{distance} iterations elapsed since prior {prior.control_kind}; "
                f"window={window}"
            ),
            followup_window=window,
            prior_control_kind=prior.control_kind,
            prior_control_iteration=prior.iteration,
            prior_source_path=prior.source_path,
        )

    remaining = max(1, window - distance + 1)
    return ControlFollowupDecision(
        schema_version=CONTROL_FOLLOWUP_SCHEMA,
        candidate_control_kind=candidate_control_kind,
        allowed=False,
        decision="observe_prior_control_followup",
        reason=(
            f"prior {prior.control_kind} fired at iteration {prior.iteration}; "
            f"observe {remaining} more follow-up iteration(s) before firing "
            f"{candidate_control_kind}"
        ),
        followup_window=window,
        prior_control_kind=prior.control_kind,
        prior_control_iteration=prior.iteration,
        remaining_followup_iterations=remaining,
        prior_source_path=prior.source_path,
    )


def record_control_followup_decision(
    workspace_dir: str | Path,
    decision: ControlFollowupDecision,
    *,
    run_id: str | None = None,
    project: str | None = None,
    iteration_index: int | None = None,
) -> None:
    """Append a follow-up policy decision for audit and later routing analysis."""

    workspace = Path(workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)
    payload = asdict(decision)
    payload.update(
        {
            "record_type": "control_followup_policy_decision",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "project": project,
            "iteration_index": iteration_index,
        }
    )
    with (workspace / "control_followup_policy.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")
