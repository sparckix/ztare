"""Findings-debate autonomous runner for GP-031 (Option B first slice).

This module is the wrapper-layer dispatch that turns the operator-typed
"ur turn on GP-031" loop into a runner that asks Claude and Gemini to
contribute their own debate turns against a seam file. It is the second
real packet on the GP-031 findings-birth bridge, sequenced after the
debate primitive (``supervisor_findings_debate``) and the promotion edge
(``supervisor_findings_promotion``) per the Codex Turn 2 order
inversion.

Design boundaries (load-bearing, see GP-031 Turn 4 avenue analysis):

- Findings-debate is *not* a SeedPipelineType. The runner does not
  consult ``supervisor_pipeline.actor_for_pipeline_state`` and does not
  read or write ``HandoffStatus``. Per Codex Turn 2, the seam-vs-seed
  boundary is preserved: the runner operates on a seam file, not on a
  supervisor program seed.
- The runner does not invent its own convergence rule. It calls
  ``supervisor_findings_debate.read_debate_state`` after every appended
  turn and exits when that primitive reports ``CONVERGED`` or
  ``ESCALATED_CAP``.
- The runner uses the Anthropic and Google GenAI SDKs directly with
  simple text prompts. It deliberately does not reuse the supervisor
  wrapper API transport functions (``_call_anthropic_research_b_api``
  etc.) because those are bound to the supervisor's tool-use schemas
  and HandoffStatus, both of which are seed-side concepts. OpenAI is
  intentionally NOT a participant: only Codex (the CLI) is operator-
  trusted, and the CLI path was rejected upstream because findings
  debates blow past the input-token wall that drove the original
  supervisor debate to API mode.
- Cost is tracked per seam in a sidecar JSONL ledger and capped on a
  per-run dollar budget. The hard turn cap (12) lives in the debate
  primitive; this runner adds a per-run cycle cap on top of it.

What this slice does *not* do:

- It does not detect findings from runtime output. That is the third
  GP-031 primitive and is deferred until the runner has been exercised
  on a real seam.
- It does not create a fresh seam file. The seam must already exist
  with a ``## Debate Log`` header — the runner is a continuation
  primitive, not a seam-birth primitive.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import date as _date
from enum import Enum
from pathlib import Path

from anthropic import Anthropic
from google import genai

from src.ztare.validator.supervisor_findings_debate import (
    DebateState,
    DebateStatus,
    HARD_TURN_CAP,
    append_turn,
    read_debate_state,
)
from src.ztare.validator.supervisor_state import TurnUsageTelemetry
from src.ztare.validator.supervisor_usage import estimate_cost_usd


DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
"""Default Anthropic model for Claude turns. Matches the existing
``supervisor/agent_wrappers.json`` setting for the ``claude`` actor so
the runner stays consistent with the rest of the supervisor stack
without re-parsing that config file."""

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
"""Default Google GenAI model for Gemini turns. Matches the default
gemini model used elsewhere in the repo (``llm_runtime`` /
mutator+judge defaults). Gemini takes the second debate seat in place
of OpenAI: only Codex (the CLI) is operator-trusted on the OpenAI side
and the CLI path was rejected for input-token-wall reasons, so the
runner uses Gemini for the non-Claude voice."""

DEFAULT_MAX_CYCLES = 6
"""Per-run cap on appended turns. Stacks below ``HARD_TURN_CAP``: the
debate primitive's hard cap (12) is the absolute ceiling for a seam's
total debate length; ``--max-cycles`` is the per-invocation budget so
the operator can run "do at most N more turns this session" without
having to count what is already in the seam."""

DEFAULT_MAX_COST_USD = 0.50
"""Default per-run dollar budget. The runner aborts before issuing the
next API call if the cumulative ``estimated_cost_usd`` of this run's
turns would exceed this budget. The check is pre-call so the limit is
never breached by an expensive single response."""


_SENTINEL_LINE = re.compile(r"SENTINEL_DECISION:\s*(raise|hold)\b", re.IGNORECASE)
"""Match the agent's decision marker. ``raise`` = the agent has no new
load-bearing claim and the
``FINDINGS_DEBATE: no_new_load_bearing_claim`` sentinel should be
appended to the turn. ``hold`` = the agent is still introducing or
rebutting a load-bearing claim and the debate must continue.

The pattern is deliberately lenient: it matches the marker anywhere in
the response body (not just on its own line) because models will
sometimes inline the decision at the end of a paragraph rather than
breaking it onto its own line. ``parse_sentinel_decision`` then takes
the LAST occurrence as authoritative, so an agent can reference the
marker earlier in their reasoning without accidentally locking in the
opposite decision."""


class RunnerStopReason(str, Enum):
    """Why the runner exited a debate loop."""

    CONVERGED = "converged"
    """The debate primitive reports ``CONVERGED`` after the most recent
    appended turn. Promotion is now safe per the GP-031 contract."""

    ESCALATED_CAP = "escalated_cap"
    """The debate crossed ``HARD_TURN_CAP`` without converging. The
    operator must inspect and decide whether to demote, override, or
    promote with ``allow_unconverged=True``."""

    MAX_CYCLES = "max_cycles"
    """The per-invocation cycle cap was reached. The seam itself is
    still in ``PENDING`` and the operator can rerun the runner."""

    COST_BUDGET = "cost_budget"
    """The cumulative ``estimated_cost_usd`` would exceed
    ``--max-cost-usd`` on the next call. No further turns appended."""

    NO_AGENT = "no_agent"
    """The runner could not determine which actor should take the next
    turn (e.g., the seam already has only ``Operator`` turns). This is
    a degenerate case that requires operator inspection."""


@dataclass(frozen=True)
class RunnerCycleResult:
    """One appended turn during a runner invocation."""

    cycle_index: int
    agent: str
    turn_index: int
    sentinel_raised: bool
    debate_status_after: str
    turn_usage: TurnUsageTelemetry


@dataclass(frozen=True)
class RunnerOutcome:
    """Aggregate result of a runner invocation."""

    seam_path: Path
    stop_reason: RunnerStopReason
    final_debate_status: str
    cycles: tuple[RunnerCycleResult, ...] = ()
    total_cost_usd: float = 0.0
    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


_TURN_INSTRUCTIONS = """\
You are participating in a structured findings-debate over a seam file.

Your job in one debate turn:

1. Read the seam file in full. It is included verbatim below between
   `--- BEGIN SEAM ---` and `--- END SEAM ---`.
2. Identify any **load-bearing architectural claim** the OTHER agent
   has made in the existing debate that you have not yet addressed. A
   load-bearing claim is one whose acceptance or rejection changes the
   shape of the proposed fix.
3. Write a single debate turn body in plain markdown. Do NOT include a
   `### Turn N — Agent` header — the runner will add it. Do NOT
   include the sentinel marker `<!-- FINDINGS_DEBATE: ... -->` in your
   body — the runner will append it based on your decision line.
4. End your response with EXACTLY ONE of these two lines, on its own
   line, as the very last line of your output:

       SENTINEL_DECISION: raise
       SENTINEL_DECISION: hold

   - `raise` = you have NO new load-bearing claim and you accept the
     debate as ready to converge from your side. Use this when the
     other agent's most recent turn has fully addressed your prior
     concerns and you have nothing new to add.
   - `hold` = you ARE introducing a new load-bearing claim, or you are
     rejecting a load-bearing claim from the other agent that has not
     yet been resolved. Use this when the debate is not yet done from
     your side.

Convergence requires BOTH agents' most recent turn to carry the
sentinel. A `raise` from you is not enough on its own; the other
agent must also raise on their next turn for the seam to converge.
Be honest: do not raise just to end the debate quickly, and do not
hold just to prolong it.

The seam file follows.

--- BEGIN SEAM ---
{seam_text}
--- END SEAM ---

You are the agent: **{agent}**. The current debate has {turn_count} prior turns.
Write your turn now and end with your `SENTINEL_DECISION:` line.
"""


def build_turn_prompt(*, seam_text: str, agent: str, debate_state: DebateState) -> str:
    """Render the prompt for a single agent's debate turn."""

    return _TURN_INSTRUCTIONS.format(
        seam_text=seam_text,
        agent=agent,
        turn_count=debate_state.turn_count,
    )


# ---------------------------------------------------------------------------
# Sentinel parsing
# ---------------------------------------------------------------------------


def parse_sentinel_decision(response_text: str) -> tuple[str, bool]:
    """Strip the ``SENTINEL_DECISION:`` marker and return body+flag.

    Returns ``(body_without_decision_marker, no_new_load_bearing_flag)``.
    If no marker is present, the body is returned unchanged and the
    flag defaults to ``False`` (treated as ``hold``) so an agent that
    fails to follow the format does not accidentally close the debate.

    The LAST occurrence of the marker is authoritative — earlier
    references (e.g., the agent quoting the instructions) do not lock
    in a decision. The marker is removed from the body in-place; if
    the surrounding sentence becomes awkward, that is the agent's
    problem to avoid by putting the marker on its own line, but the
    runner will not refuse to parse a turn over it.
    """

    matches = list(_SENTINEL_LINE.finditer(response_text))
    if not matches:
        return response_text.rstrip() + "\n", False
    last = matches[-1]
    decision = last.group(1).strip().lower()
    body = (response_text[: last.start()] + response_text[last.end():]).rstrip() + "\n"
    return body, decision == "raise"


# ---------------------------------------------------------------------------
# Agent dispatch
# ---------------------------------------------------------------------------


def call_claude(*, prompt_text: str, model_name: str, max_tokens: int = 2000) -> tuple[str, TurnUsageTelemetry]:
    """Issue one Anthropic call and return the response body + usage.

    Uses the Messages API with no tool-use shape — findings-debate
    output is plain markdown plus a trailing decision line, not a
    structured tool payload, so the supervisor's tool-use transports
    are not appropriate here.
    """

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        system=(
            "You are participating in a structured findings-debate. "
            "Read the seam, contribute one rigorous turn, and end with "
            "your SENTINEL_DECISION line. Do not preface your turn with "
            "filler. Do not include any header line — the runner adds it."
        ),
        messages=[{"role": "user", "content": prompt_text}],
        temperature=0,
    )
    text_blocks = [
        getattr(block, "text", "")
        for block in response.content
        if getattr(block, "type", None) == "text"
    ]
    body = "".join(text_blocks)
    usage = response.usage
    input_tokens = int(getattr(usage, "input_tokens", 0))
    output_tokens = int(getattr(usage, "output_tokens", 0))
    resolved_model = getattr(response, "model", None) or model_name
    telemetry = TurnUsageTelemetry(
        model_name=resolved_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        estimated_cost_usd=estimate_cost_usd(
            model_name=resolved_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
        telemetry_captured=True,
    )
    return body, telemetry


def call_gemini(*, prompt_text: str, model_name: str) -> tuple[str, TurnUsageTelemetry]:
    """Issue one Google GenAI call and return the response body + usage.

    Mirrors the call shape used in ``src/ztare/common/llm_runtime.py``:
    ``client.models.generate_content(model=..., contents=...)`` with
    no explicit config (defaults are fine for plain-text debate
    turns), then pulls token counts off ``response.usage_metadata``.
    """

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=model_name,
        contents=prompt_text,
    )
    body = getattr(response, "text", "") or ""
    usage_metadata = getattr(response, "usage_metadata", None)
    input_tokens = (
        int(getattr(usage_metadata, "prompt_token_count", 0) or 0)
        if usage_metadata is not None
        else 0
    )
    output_tokens = (
        int(getattr(usage_metadata, "candidates_token_count", 0) or 0)
        if usage_metadata is not None
        else 0
    )
    cached_tokens = (
        int(getattr(usage_metadata, "cached_content_token_count", 0) or 0)
        if usage_metadata is not None
        else 0
    )
    resolved_model = getattr(response, "model", None) or model_name
    telemetry = TurnUsageTelemetry(
        model_name=resolved_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=cached_tokens,
        estimated_cost_usd=estimate_cost_usd(
            model_name=resolved_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=cached_tokens,
        ),
        telemetry_captured=True,
    )
    return body, telemetry


# ---------------------------------------------------------------------------
# Turn routing
# ---------------------------------------------------------------------------


_DEBATE_AGENTS: tuple[str, ...] = ("Claude", "Gemini")


def choose_next_agent(state: DebateState) -> str | None:
    """Pick the next debate agent.

    Rule: alternate Claude/Gemini. If the seam has no turns, start with
    Claude. Legacy seams may already contain ``Codex`` turns from the
    pre-swap runner; for routing purposes those count as the
    "non-Claude" voice and the runner returns ``Claude`` next so the
    alternation invariant is preserved across the swap. If the most
    recent turn is from a non-debate actor (e.g., ``Operator``), fall
    back to whichever current debate agent has fewer turns; if tied,
    default to Claude. Returns ``None`` if the seam has only non-debate
    turns and the runner cannot make a clean choice.
    """

    if state.turn_count == 0:
        return "Claude"

    most_recent = max(state.turns, key=lambda t: t.index)
    if most_recent.agent == "Claude":
        return "Gemini"
    if most_recent.agent in ("Gemini", "Codex"):
        return "Claude"

    grouped = state.turns_by_agent()
    claude_count = len(grouped.get("Claude", ()))
    gemini_count = len(grouped.get("Gemini", ()))
    if claude_count == 0 and gemini_count == 0:
        return None
    if claude_count <= gemini_count:
        return "Claude"
    return "Gemini"


# ---------------------------------------------------------------------------
# Cost ledger
# ---------------------------------------------------------------------------


def append_usage_ledger(*, ledger_path: Path, telemetry: TurnUsageTelemetry, agent: str, cycle_index: int) -> None:
    """Append one turn's telemetry to a per-seam JSONL ledger."""

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "cycle_index": cycle_index,
        "agent": agent,
        **asdict(telemetry),
    }
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def usage_ledger_path_for_seam(seam_path: Path) -> Path:
    """Co-locate the cost ledger next to the seam file."""

    return seam_path.with_name(seam_path.stem + "_findings_debate_usage.jsonl")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run_findings_debate(
    *,
    seam_path: Path,
    max_cycles: int = DEFAULT_MAX_CYCLES,
    max_cost_usd: float = DEFAULT_MAX_COST_USD,
    claude_model: str = DEFAULT_CLAUDE_MODEL,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    execute: bool = False,
    today: str | None = None,
) -> RunnerOutcome:
    """Drive a findings-debate to convergence or escalation.

    The loop is: read state → exit if terminal → choose agent → cost
    pre-check → call agent → parse decision → append turn → re-read
    state. ``execute=False`` performs all the planning steps (state
    reads, agent selection, prompt construction) without issuing API
    calls or appending turns; this is the dry-run mode used to verify
    the runner against a seam before spending tokens.
    """

    if not seam_path.exists():
        raise FileNotFoundError(f"seam file not found: {seam_path}")

    cycles: list[RunnerCycleResult] = []
    notes: list[str] = []
    ledger_path = usage_ledger_path_for_seam(seam_path)
    today_str = today or _date.today().isoformat()

    state = read_debate_state(seam_path)

    if state.status == DebateStatus.CONVERGED:
        return RunnerOutcome(
            seam_path=seam_path,
            stop_reason=RunnerStopReason.CONVERGED,
            final_debate_status=state.status.value,
            cycles=(),
            total_cost_usd=0.0,
            notes=("seam was already converged on entry — no turns appended",),
        )
    if state.status == DebateStatus.ESCALATED_CAP:
        return RunnerOutcome(
            seam_path=seam_path,
            stop_reason=RunnerStopReason.ESCALATED_CAP,
            final_debate_status=state.status.value,
            cycles=(),
            total_cost_usd=0.0,
            notes=(f"seam was already at hard turn cap ({HARD_TURN_CAP}) on entry",),
        )

    cumulative_cost = 0.0

    for cycle_index in range(1, max_cycles + 1):
        agent = choose_next_agent(state)
        if agent is None:
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.NO_AGENT,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=("seam has only non-debate turns; runner cannot route",),
            )

        seam_text = seam_path.read_text(encoding="utf-8")
        prompt_text = build_turn_prompt(
            seam_text=seam_text,
            agent=agent,
            debate_state=state,
        )

        if not execute:
            notes.append(
                f"dry-run cycle {cycle_index}: would dispatch to {agent} "
                f"(prompt length={len(prompt_text)} chars)"
            )
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.MAX_CYCLES,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=tuple(notes),
            )

        if cumulative_cost >= max_cost_usd:
            notes.append(
                f"cost budget reached before cycle {cycle_index}: "
                f"{cumulative_cost:.6f} >= {max_cost_usd:.6f}"
            )
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.COST_BUDGET,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=tuple(notes),
            )

        if agent == "Claude":
            response_text, telemetry = call_claude(
                prompt_text=prompt_text,
                model_name=claude_model,
            )
        elif agent == "Gemini":
            response_text, telemetry = call_gemini(
                prompt_text=prompt_text,
                model_name=gemini_model,
            )
        else:
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.NO_AGENT,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=(f"unknown debate agent: {agent}",),
            )

        body, sentinel_raised = parse_sentinel_decision(response_text)
        if not body.strip():
            notes.append(
                f"cycle {cycle_index}: agent {agent} returned empty body — aborting before append"
            )
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.NO_AGENT,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost + telemetry.estimated_cost_usd,
                notes=tuple(notes),
            )

        appended_turn = append_turn(
            seam_path=seam_path,
            agent=agent,
            date=today_str,
            title="Autonomous runner turn",
            body=body,
            no_new_load_bearing=sentinel_raised,
        )
        cumulative_cost += telemetry.estimated_cost_usd
        append_usage_ledger(
            ledger_path=ledger_path,
            telemetry=telemetry,
            agent=agent,
            cycle_index=cycle_index,
        )

        state = read_debate_state(seam_path)
        cycles.append(
            RunnerCycleResult(
                cycle_index=cycle_index,
                agent=agent,
                turn_index=appended_turn.index,
                sentinel_raised=sentinel_raised,
                debate_status_after=state.status.value,
                turn_usage=telemetry,
            )
        )

        if state.status == DebateStatus.CONVERGED:
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.CONVERGED,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=tuple(notes),
            )
        if state.status == DebateStatus.ESCALATED_CAP:
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.ESCALATED_CAP,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=tuple(notes),
            )

    return RunnerOutcome(
        seam_path=seam_path,
        stop_reason=RunnerStopReason.MAX_CYCLES,
        final_debate_status=state.status.value,
        cycles=tuple(cycles),
        total_cost_usd=cumulative_cost,
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_run_findings_debate(args: argparse.Namespace) -> int:
    outcome = run_findings_debate(
        seam_path=args.seam_path,
        max_cycles=args.max_cycles,
        max_cost_usd=args.max_cost_usd,
        claude_model=args.claude_model,
        gemini_model=args.gemini_model,
        execute=args.execute,
        today=args.today,
    )
    print(f"[findings-runner] seam={outcome.seam_path}")
    print(f"[findings-runner] stop_reason={outcome.stop_reason.value}")
    print(f"[findings-runner] final_debate_status={outcome.final_debate_status}")
    print(f"[findings-runner] cycles={len(outcome.cycles)} total_cost_usd={outcome.total_cost_usd:.6f}")
    for cycle in outcome.cycles:
        print(
            f"[findings-runner]   cycle={cycle.cycle_index} agent={cycle.agent} "
            f"turn={cycle.turn_index} sentinel={cycle.sentinel_raised} "
            f"status_after={cycle.debate_status_after} cost={cycle.turn_usage.estimated_cost_usd:.6f}"
        )
    for note in outcome.notes:
        print(f"[findings-runner] note: {note}")
    return 0 if outcome.stop_reason in {RunnerStopReason.CONVERGED, RunnerStopReason.MAX_CYCLES} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GP-031 autonomous findings-debate runner. Drives a seam toward convergence."
    )
    parser.add_argument("--seam-path", type=Path, required=True)
    parser.add_argument("--max-cycles", type=int, default=DEFAULT_MAX_CYCLES)
    parser.add_argument("--max-cost-usd", type=float, default=DEFAULT_MAX_COST_USD)
    parser.add_argument("--claude-model", type=str, default=DEFAULT_CLAUDE_MODEL)
    parser.add_argument("--gemini-model", type=str, default=DEFAULT_GEMINI_MODEL)
    parser.add_argument("--execute", action="store_true", help="Issue real API calls and append turns. Without this flag the runner is dry-run only.")
    parser.add_argument("--today", type=str, default=None, help="Override today's date in ISO form (used for the appended turn header).")
    parser.set_defaults(func=cmd_run_findings_debate)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
