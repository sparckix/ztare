from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any

from ztare.common.control_state_machine import (
    ControlStateChart,
    ControlTransition,
    render_control_state_chart_surface,
)
from ztare.validator.core.mutation_contract import MutationDeclaration


class RunnerR1State(str, Enum):
    AWAIT_DECLARATION = "await_declaration"
    AWAIT_PAYLOAD = "await_payload"
    PAYLOAD_RETRY = "payload_retry"
    READY_FOR_VALIDATION = "ready_for_validation"
    EXHAUSTED = "exhausted"


RUNNER_R1_CHART = ControlStateChart(
    schema="ztare-runner-r1-lifecycle-v1",
    transitions=(
        ControlTransition(
            state=RunnerR1State.AWAIT_DECLARATION.value,
            event="commit_declaration",
            next=RunnerR1State.AWAIT_PAYLOAD.value,
            invariant="declaration becomes immutable control state",
        ),
        ControlTransition(
            state=RunnerR1State.AWAIT_PAYLOAD.value,
            event="payload_generated",
            next=RunnerR1State.READY_FOR_VALIDATION.value,
            invariant="payload is interpreted under committed declaration",
        ),
        ControlTransition(
            state=RunnerR1State.READY_FOR_VALIDATION.value,
            event="r1_reject",
            next=RunnerR1State.PAYLOAD_RETRY.value,
            invariant="retry edits payload, not declaration",
        ),
        ControlTransition(
            state=RunnerR1State.PAYLOAD_RETRY.value,
            event="payload_retry_generated",
            next=RunnerR1State.READY_FOR_VALIDATION.value,
            invariant="committed declaration is reattached by the kernel",
        ),
        ControlTransition(
            state=RunnerR1State.PAYLOAD_RETRY.value,
            event="retry_budget_exhausted",
            next=RunnerR1State.EXHAUSTED.value,
            invariant="iteration may be consumed only after payload retries fail",
        ),
    ),
)
RUNNER_R1_TRANSITIONS = RUNNER_R1_CHART.transition_table()


_FENCED_JSON_OBJECT_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
_DECLARATION_KEYS = {
    "scope_delta",
    "claim_delta_type",
    "thesis_control_mode",
    "primitive_invoked",
    "touched_artifacts",
}


def mutation_declaration_payload(declaration: MutationDeclaration) -> dict[str, Any]:
    return {
        "scope_delta": declaration.scope_delta.value,
        "claim_delta_type": declaration.claim_delta_type.value,
        "thesis_control_mode": declaration.thesis_control_mode.value,
        "primitive_invoked": declaration.primitive_invoked,
        "touched_artifacts": [item.value for item in declaration.touched_artifacts],
    }


def mutation_declaration_json(declaration: MutationDeclaration) -> str:
    return json.dumps(mutation_declaration_payload(declaration), indent=2)


def render_committed_declaration_block(declaration: MutationDeclaration) -> str:
    return f"```json\n{mutation_declaration_json(declaration)}\n```"


def ensure_committed_runner_r1_declaration(
    text: str,
    declaration: MutationDeclaration,
) -> str:
    """Attach the immutable R1 declaration to a payload retry.

    Same-iteration retries are payload edits. If a worker repeats or changes a
    declaration block, remove that attempted reopen and carry the committed
    declaration instead.
    """
    body = _strip_mutation_declaration_block(text or "").strip()
    if body:
        return f"{render_committed_declaration_block(declaration)}\n\n{body}"
    return render_committed_declaration_block(declaration)


def render_runner_r1_lifecycle_surface(
    *,
    state: RunnerR1State,
    declaration: MutationDeclaration,
    last_error: str = "",
) -> str:
    return render_control_state_chart_surface(
        chart=RUNNER_R1_CHART,
        state=state.value,
        context={"committed_declaration": mutation_declaration_payload(declaration)},
        admissible_events=["payload_retry_generated"],
        heading="RUNNER R1 LIFECYCLE",
        last_error=last_error,
        boundary_rule=(
            "repair the candidate payload under the committed declaration; "
            "the kernel will reattach the declaration before validation"
        ),
    )


def runner_r1_lifecycle_spec_markdown() -> str:
    """Render the lifecycle as a compact spec artifact for workbench/proposals."""
    rows = [
        "| state | event | next | invariant |",
        "|---|---|---|---|",
    ]
    for row in RUNNER_R1_CHART.transitions:
        rows.append(
            f"| `{row.state}` | `{row.event}` | `{row.next}` | {row.invariant} |"
        )
    return "\n".join(
        [
            "# Runner R1 Lifecycle",
            "",
            "Schema: `ztare-runner-r1-lifecycle-v1`",
            "",
            *rows,
            "",
            "Mutable proposal surface: agents may propose lifecycle-chart changes, "
            "but adoption requires the same parser/regression gates as code changes.",
            "",
        ]
    )


def _strip_mutation_declaration_block(text: str) -> str:
    remaining = text
    while True:
        match = _first_mutation_declaration_match(remaining)
        if match is None:
            return remaining.strip()
        remaining = (remaining[: match.start()] + remaining[match.end() :]).strip()


def _first_mutation_declaration_match(text: str):
    for match in _FENCED_JSON_OBJECT_RE.finditer(text or ""):
        try:
            payload = json.loads(match.group(1), strict=False)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and _DECLARATION_KEYS.issubset(payload.keys()):
            return match
    return None
