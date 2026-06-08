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

Auto-spec pipeline (added 2026-04-16, exercised on GP-074):

- ``--auto-spec``: on seam-phase convergence, LLM-drafts a spec,
  inserts a phase marker, and continues with spec-review debate on
  the same seam file.  All steps idempotent on crash.
- On spec-phase convergence, a single post-convergence LLM pass
  revises the spec to incorporate accepted changes from the debate.
  Idempotent via ``<!-- SPEC_REVISED_FROM_DEBATE ... -->`` marker.
  Revision logged in the seam under ``## Spec Revision Log``.
- Per-phase ``HARD_TURN_CAP``: the cap is scoped to the active phase
  (seam or spec), not total turns across both phases.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import date as _date, datetime, timezone
from enum import Enum
from pathlib import Path

from anthropic import Anthropic
from google import genai

from src.ztare.common.paths import REPO_ROOT
from src.ztare.findings.findings_context import (
    DEFAULT_TOKEN_BUDGET,
    build_findings_context,
    format_context_tiers,
)
from src.ztare.supervisor.supervisor_findings_debate import (
    DebatePhase,
    DebateState,
    DebateStatus,
    HARD_TURN_CAP,
    _detect_phase,
    append_turn,
    read_debate_state,
)
from src.ztare.supervisor.supervisor_state import TurnUsageTelemetry
from src.ztare.supervisor.supervisor_usage import estimate_cost_usd


DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
"""Default Anthropic model for Claude turns. Matches the existing
``supervisor/agent_wrappers.json`` setting for the ``claude`` actor so
the runner stays consistent with the rest of the supervisor stack
without re-parsing that config file."""

DEFAULT_GEMINI_MODEL = "gemini-3.1-pro-preview"
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


class AgentMode(str, Enum):
    """GP-036 Deliverable 7 — which seat lineup the runner uses.

    ``claude_gemini`` is the existing behavior: Claude + Gemini via
    separate providers. ``single_claude`` (added 2026-04-15) routes
    both seats to the Anthropic API with different system prompts —
    author seat uses the baseline debate instructions, skeptic seat
    uses the ``feedback_automated_skeptic_persona.md`` persona so the
    adversarial seat has structurally different priming. Provider
    independence is given up; persona isolation is the mitigation."""

    CLAUDE_GEMINI = "claude_gemini"
    SINGLE_CLAUDE = "single_claude"


DEFAULT_AGENT_MODE = AgentMode.CLAUDE_GEMINI


DEFAULT_SKEPTIC_PERSONA_PATH = (
    Path.home()
    / ".claude"
    / "projects"
    / "-[repo]-"
    / "memory"
    / "feedback_automated_skeptic_persona.md"
)
"""Default path to the automated-skeptic persona file used in
``single_claude`` mode. Built from ``Path.home()`` rather than a hard
absolute so the runner works for any operator who has the Claude Code
memory directory in the conventional location. Override with
``--skeptic-persona-path`` if the persona lives elsewhere."""


_REVIEWER_DOMAINS_DIR = REPO_ROOT / "config" / "prompts"
"""Directory containing ``reviewer_domain_*.md`` lens files."""

_GROUNDING_AGENTS_PATH = REPO_ROOT / "AGENTS.md"
_GROUNDING_THREE_LEGS_PATH = (
    REPO_ROOT / "research_areas" / "private" / "philosophy" / "three_legs_of_ztare.md"
)
_GROUNDING_MUNGER_PATH = (
    Path.home()
    / ".claude"
    / "projects"
    / "-[repo]-"
    / "memory"
    / "project_munger_philosophy.md"
)
"""Paths to the project-epistemics grounding files injected into both
single_claude seats. AGENTS.md holds the standing agent rules; the
three-legs doc holds the invert/compress/adversarial philosophy; the
Munger philosophy memo holds eigenquestion/inversion/WWYHTB discipline.
The skeptic-persona file (12 overreach patterns) is also loaded and
included in the shared bundle so Author and Skeptic share the same
adversarial vocabulary."""


def load_shared_grounding(
    *,
    skeptic_persona_path: Path | None = None,
    include_agents: bool = True,
    include_three_legs: bool = True,
    include_munger: bool = True,
    include_skeptic_checklist: bool = True,
) -> str:
    """Load the shared project-epistemics grounding for single_claude seats.

    Returns a single text bundle containing the project's standing
    rules and epistemic discipline (AGENTS, three-legs, Munger) plus
    the 12-pattern skeptic checklist. Both Author and Skeptic seats
    load this bundle so the two seats share vocabulary and differ only
    by role framing (see ``_AUTHOR_ROLE_HEADER`` / ``_SKEPTIC_ROLE_HEADER``).

    Any missing file is skipped (not raised) so the runner stays usable
    if operator-specific memory files are absent — except the skeptic
    checklist, which is required for single_claude mode by the same
    contract as ``load_skeptic_persona``.
    """

    chunks: list[str] = []

    def _try_load(label: str, path: Path) -> None:
        if path.exists():
            chunks.append(f"=== {label} ===\n{path.read_text(encoding='utf-8').strip()}")

    if include_agents:
        _try_load("PROJECT_STANDING_RULES (AGENTS.md)", _GROUNDING_AGENTS_PATH)
    if include_three_legs:
        _try_load("ZTARE_PHILOSOPHY (three legs)", _GROUNDING_THREE_LEGS_PATH)
    if include_munger:
        _try_load("MUNGER_DISCIPLINE (inversion, eigenquestion, WWYHTB, checklist)", _GROUNDING_MUNGER_PATH)
    if include_skeptic_checklist:
        target = skeptic_persona_path if skeptic_persona_path is not None else DEFAULT_SKEPTIC_PERSONA_PATH
        if not target.exists():
            raise FileNotFoundError(
                f"skeptic persona file (required for single_claude grounding) not found: {target}"
            )
        chunks.append(
            "=== ADVERSARIAL_CHECKLIST (12 overreach patterns) ===\n"
            + target.read_text(encoding="utf-8").strip()
        )

    return "\n\n".join(chunks)


def load_reviewer_domains(domains: list[str]) -> str:
    """Load domain-lens prompt files and return as a labeled bundle.

    Each ``domain`` is a short name (e.g. ``philosophy_of_science``)
    that maps to a persona in the registry (category="domain").
    Missing domains raise ``KeyError`` so the operator gets a clear error
    rather than a silent no-op.

    Thin adapter over :mod:`src.ztare.personas.registry`.
    """
    if not domains:
        return ""

    from src.ztare.personas.registry import load_personas, format_many_for_injection

    personas = load_personas(domains, category="domain")
    return format_many_for_injection(personas, include_focus=False)


_AUTHOR_ROLE_HEADER = """\
=== YOUR ROLE THIS TURN: AUTHOR ===

You are the Author seat in a structured findings-debate. Your job is
to propose or sharpen load-bearing architectural claims in the seam
under debate. Run the project principles above as a GENERATIVE
checklist:

- Eigenquestion-first ordering: identify the single question whose
  answer reshapes the most downstream choices, and write your turn
  around it.
- Invert, always invert: before proposing a fix, ask how the seam
  could fail, and address the failure mode first.
- "What would you have to believe" (WWYHTB): for each load-bearing
  claim you accept or propose, state the beliefs it rests on — if any
  belief is unstated, surface it.
- Principle vs instantiation strip: state any general claim so the
  specific nouns can be stripped; if the claim collapses without its
  nouns, it was an instantiation, not a principle.
- Radical honesty about uncertainty: do not paper over gaps with
  confident-sounding language. Name the unknowns.
- Circle of competence: if a claim requires expertise the seam does
  not evidence, flag it and name what would be needed.

Write one rigorous debate turn in plain markdown. Do NOT include a
``### Turn N`` header — the runner adds it. Do NOT include the
``<!-- FINDINGS_DEBATE -->`` sentinel — the runner appends it from
your ``SENTINEL_DECISION`` line.
"""


_SKEPTIC_ROLE_HEADER = """\
=== YOUR ROLE THIS TURN: SKEPTIC ===

You are the Skeptic seat in a structured findings-debate. Your job is
to attack load-bearing claims in the seam and in the most recent
Author turn. Run the project principles above as an ADVERSARIAL
checklist:

- Apply the 12-pattern adversarial checklist (loaded above) to the
  seam and to every Author claim. Flag every match inline in prose —
  do NOT use the standalone ``## Critique of <draft>`` format from the
  persona file.
- Invert the Author's framing: what would have to be true for the
  Author to be wrong? If that condition is plausible, it is a live
  flag.
- Principle vs instantiation strip: if an Author claim reads as a
  principle but collapses once its proper nouns are stripped, flag it.
- Closure-language audit: if the Author says "last," "final," "only
  remaining," "clearly," "obviously" — check whether open tracks on
  the same object justify that language.
- Scope and overfitting: does the Author's fix generalize, or does it
  overfit the motivating case? Imagine one OOD case per claim.
- Do not manufacture disagreement. If every flag you find is already
  addressed, raise the sentinel and say so.

Write one rigorous debate turn in plain markdown. Enumerate flags
inline. Do NOT include a ``### Turn N`` header — the runner adds it.
Do NOT include the ``<!-- FINDINGS_DEBATE -->`` sentinel — the runner
appends it from your ``SENTINEL_DECISION`` line.
"""


def build_single_claude_system_prompt(
    *,
    role: str,
    shared_grounding: str,
    reviewer_domains_text: str = "",
) -> str:
    """Assemble the single_claude system prompt for one seat.

    ``role`` must be ``'author'`` or ``'skeptic'``. The system prompt
    is always: shared grounding (AGENTS + philosophy + Munger +
    adversarial checklist), then the role header, then the format
    reconciliation note shared with the rest of the runner.

    When ``reviewer_domains_text`` is non-empty, it is injected into
    the skeptic prompt between the role header and the format note,
    giving the skeptic domain-specific mental models for the review.
    Ignored for the author seat.
    """

    if role == "author":
        header = _AUTHOR_ROLE_HEADER
    elif role == "skeptic":
        header = _SKEPTIC_ROLE_HEADER
    else:
        raise ValueError(f"unknown single_claude role: {role}")

    parts = [shared_grounding, "---", header]

    if role == "skeptic" and reviewer_domains_text:
        parts.append("---")
        parts.append(
            "=== DOMAIN LENSES (apply these mental models to every claim) ===\n\n"
            + reviewer_domains_text
        )

    parts.append("---")
    parts.append(_DEFAULT_CLAUDE_SYSTEM_PROMPT)

    return "\n\n".join(parts)


ALLOWED_FINDINGS_DIRS: tuple[str, ...] = (
    "research_areas/seams/",
    "[internal-ref]",
)
"""Directories the runner is permitted to append turns into. Enforced
by ``validate_findings_write_scope`` (GP-036 Deliverable 2). A path
outside this set raises ``RunnerWriteScopeError`` before any API call
is issued."""


class RunnerWriteScopeError(Exception):
    """Raised when the runner is asked to write outside the allowed
    findings directories (GP-036 Deliverable 2)."""


def validate_findings_write_scope(seam_path: Path, repo_root: Path = REPO_ROOT) -> None:
    """Reject any seam path outside the allowed findings directories."""

    resolved = seam_path.resolve()
    try:
        rel = resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RunnerWriteScopeError(
            f"seam path {seam_path} is outside the repo root {repo_root}"
        ) from exc
    rel_str = str(rel).replace("\\", "/")
    if not any(rel_str.startswith(prefix) for prefix in ALLOWED_FINDINGS_DIRS):
        raise RunnerWriteScopeError(
            f"seam path {rel_str} is outside allowed findings dirs {ALLOWED_FINDINGS_DIRS}"
        )


def load_skeptic_persona(path: Path | None = None) -> str:
    """Load the automated-skeptic persona file.

    Raises ``FileNotFoundError`` if the file is missing — ``single_claude``
    mode requires the persona, and silent fallback to the author prompt
    would collapse the two-voice invariant."""

    target = path if path is not None else DEFAULT_SKEPTIC_PERSONA_PATH
    if not target.exists():
        raise FileNotFoundError(
            f"skeptic persona file not found: {target}. "
            "single_claude mode requires this file — do not fall back silently."
        )
    return target.read_text(encoding="utf-8")


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

    SEAM_CONVERGED_SPEC_DRAFTED = "seam_converged_spec_drafted"
    """Seam debate converged and spec was auto-drafted. The runner
    transitions to spec-review phase and continues debating."""

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
{context_block}
You are the agent: **{agent}**. The current debate has {turn_count} prior turns.
Write your turn now and end with your `SENTINEL_DECISION:` line.
"""


def build_turn_prompt(
    *,
    seam_text: str,
    agent: str,
    debate_state: DebateState,
    seam_path: Path | None = None,
    token_budget: int | None = None,
) -> str:
    """Render the prompt for a single agent's debate turn.

    When ``seam_path`` is supplied, the builder calls
    ``build_findings_context`` (GP-036 Deliverable 5) and injects the
    tiered context block after the seam text. Absent ``seam_path`` the
    builder skips context injection, which is the path taken by the
    pure-function fixture regression tests and by any caller that
    doesn't want to touch the filesystem."""

    context_block = ""
    if seam_path is not None:
        tiers = build_findings_context(
            seam_path=seam_path,
            seam_text=seam_text,
            token_budget=token_budget if token_budget is not None else DEFAULT_TOKEN_BUDGET,
        )
        if tiers:
            rendered = format_context_tiers(tiers)
            context_block = (
                "\n--- BEGIN CONTEXT ---\n"
                f"{rendered}"
                "--- END CONTEXT ---\n"
            )

    spec_block = ""
    if debate_state.phase == DebatePhase.SPEC:
        if not debate_state.spec_path:
            print(
                "[findings-runner] WARNING: in spec-review phase but no spec_path "
                "found in phase marker — agents will not see spec content",
                flush=True,
            )
        else:
            spec_file = REPO_ROOT / debate_state.spec_path
            if not spec_file.exists():
                print(
                    f"[findings-runner] WARNING: spec file not found at {spec_file}",
                    flush=True,
                )
    if debate_state.phase == DebatePhase.SPEC and debate_state.spec_path:
        spec_file = REPO_ROOT / debate_state.spec_path
        if spec_file.exists():
            spec_block = (
                "\n--- BEGIN SPEC UNDER REVIEW ---\n"
                f"{spec_file.read_text(encoding='utf-8')}"
                "\n--- END SPEC UNDER REVIEW ---\n\n"
                "You are now in the SPEC REVIEW phase. The seam debate above "
                "has already converged. Your job is to review the spec for: "
                "implementation correctness, missing constraints, integration "
                "gaps, and faithfulness to the converged seam position. "
                "Do NOT re-debate the seam — only review the spec.\n"
            )

    return _TURN_INSTRUCTIONS.format(
        seam_text=seam_text,
        agent=agent,
        turn_count=debate_state.turn_count,
        context_block=context_block + spec_block,
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


_DEFAULT_CLAUDE_SYSTEM_PROMPT = (
    "You are participating in a structured findings-debate. "
    "Read the seam, contribute one rigorous turn, and end with "
    "your SENTINEL_DECISION line. Do not preface your turn with "
    "filler. Do not include any header line — the runner adds it."
)


_SKEPTIC_RECONCILIATION_NOTE = (
    "\n\n---\n\n"
    "FORMAT RECONCILIATION FOR THE FINDINGS-DEBATE RUNNER: You are acting "
    "as the `Claude-Skeptic` seat in a structured findings-debate, not as "
    "a standalone bounded critique. Apply the 12 overreach-pattern "
    "checklist above to the seam under debate, but write your turn body "
    "as a markdown debate turn (not as the standalone `## Critique of "
    "<draft>` format from the persona file). Enumerate any flags inline "
    "in prose. End your turn with `SENTINEL_DECISION: raise` if every "
    "flag you found is already addressed in the seam, or "
    "`SENTINEL_DECISION: hold` if any flag remains unresolved. The "
    "persona's `Verdict:` line is subsumed by the SENTINEL_DECISION "
    "line — do not output both."
)


def call_claude(
    *,
    prompt_text: str,
    model_name: str,
    max_tokens: int = 2000,
    system_prompt: str | None = None,
) -> tuple[str, TurnUsageTelemetry]:
    """Issue one Anthropic call and return the response body + usage.

    Uses the Messages API with no tool-use shape — findings-debate
    output is plain markdown plus a trailing decision line, not a
    structured tool payload, so the supervisor's tool-use transports
    are not appropriate here.

    ``system_prompt`` overrides the default author-seat system prompt.
    The runner uses this in ``single_claude`` mode to pass the
    automated-skeptic persona when the Claude-Skeptic seat is up.
    """

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        system=system_prompt if system_prompt is not None else _DEFAULT_CLAUDE_SYSTEM_PROMPT,
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
    thinking_tokens = (
        int(getattr(usage_metadata, "thoughts_token_count", 0) or 0)
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
        thinking_tokens=thinking_tokens,
        estimated_cost_usd=estimate_cost_usd(
            model_name=resolved_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=cached_tokens,
            thinking_tokens=thinking_tokens,
        ),
        telemetry_captured=True,
    )
    return body, telemetry


# ---------------------------------------------------------------------------
# Turn routing
# ---------------------------------------------------------------------------


_DEBATE_AGENTS: tuple[str, ...] = ("Claude", "Gemini")

SINGLE_CLAUDE_AUTHOR = "Claude-Author"
SINGLE_CLAUDE_SKEPTIC = "Claude-Skeptic"


def choose_next_agent(
    state: DebateState,
    *,
    agent_mode: AgentMode = DEFAULT_AGENT_MODE,
) -> str | None:
    """Pick the next debate agent.

    In ``claude_gemini`` mode (default) the routing is the legacy
    Claude/Gemini alternation. In ``single_claude`` mode the runner
    alternates ``Claude-Author`` and ``Claude-Skeptic`` — same provider,
    different system prompts — so the convergence and audit rules still
    see two distinct voices."""

    if agent_mode == AgentMode.SINGLE_CLAUDE:
        return _choose_next_single_claude(state)
    return _choose_next_claude_gemini(state)


def _choose_next_single_claude(state: DebateState) -> str | None:
    """Agent routing for ``single_claude`` mode.

    Starts with Author on an empty seam. Alternates Author/Skeptic
    strictly. Treats any legacy ``Claude``/``Gemini``/``Codex`` turn as
    a non-single-claude voice — on a mixed seam the runner picks
    whichever single-claude seat has fewer turns, defaulting to Author
    on ties. This preserves the operator's ability to switch a seam
    from ``claude_gemini`` to ``single_claude`` mid-debate."""

    if state.turn_count == 0:
        return SINGLE_CLAUDE_AUTHOR

    most_recent = max(state.turns, key=lambda t: t.index)
    if most_recent.agent == SINGLE_CLAUDE_AUTHOR:
        return SINGLE_CLAUDE_SKEPTIC
    if most_recent.agent == SINGLE_CLAUDE_SKEPTIC:
        return SINGLE_CLAUDE_AUTHOR

    # Mixed seam: count single-claude seats specifically
    grouped = state.turns_by_agent()
    author_count = len(grouped.get(SINGLE_CLAUDE_AUTHOR, ()))
    skeptic_count = len(grouped.get(SINGLE_CLAUDE_SKEPTIC, ()))
    if author_count <= skeptic_count:
        return SINGLE_CLAUDE_AUTHOR
    return SINGLE_CLAUDE_SKEPTIC


def _choose_next_claude_gemini(state: DebateState) -> str | None:
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


SUPERVISOR_USAGE_LEDGER_DIR = (
    REPO_ROOT / "ztare_workspace" / "supervisor" / "findings_debate" / "usage_ledger"
)
"""Home for the GP-036 runner's per-seam cost ledger.

Keeps observation data out of ``[internal-ref]`` where
the seams themselves live as hand-curated primary artifacts. The split
mirrors the existing ``ztare_workspace/gates/pending/`` pattern:
machine-emitted supervisor telemetry lives under
``ztare_workspace/supervisor/<category>/``, while human-edited research
artifacts stay in ``research_areas/``."""


def usage_ledger_path_for_seam(seam_path: Path) -> Path:
    """Return the per-seam usage-ledger path under the supervisor workspace.

    The ledger is keyed by the seam's file stem so the reporter can
    cross-walk ledger → seam without parsing the seam body. The parent
    directory is auto-created by ``append_usage_ledger`` on first write."""

    return SUPERVISOR_USAGE_LEDGER_DIR / f"{seam_path.stem}.jsonl"


# ---------------------------------------------------------------------------
# Executive-inbox escalation adapter (GP-036 Deliverable 4)
# ---------------------------------------------------------------------------


GATE_PENDING_DIR = REPO_ROOT / "ztare_workspace" / "gates" / "pending"
"""Directory where the runner drops typed escalation records when it
exits on a cap. Operator-pulled: the runner never auto-routes these.
Per the GP-036 seam Turn 4 constraint, the adapter is advisory only in
Slice A — it emits an inspectable JSON file and returns control."""


_ESCALATION_STOP_REASONS: frozenset[RunnerStopReason] = frozenset(
    {RunnerStopReason.ESCALATED_CAP, RunnerStopReason.COST_BUDGET}
)
"""Stop reasons that require an executive-inbox file drop. CONVERGED
and MAX_CYCLES are normal terminations and do not escalate. NO_AGENT
is a degenerate runner-routing failure and would not benefit from an
escalation record (the runner cannot describe what it wanted to do)."""


def _rough_gate_reason_name(stop: RunnerStopReason) -> str:
    """Map a runner-local stop reason to the HumanGateReason label it
    would be translated to if the operator chose to route it through
    supervisor gate resolution. Per the GP-036 seam the runner does
    NOT internally merge enums — this is just a hint for the operator
    reading the adapter record."""

    if stop == RunnerStopReason.ESCALATED_CAP:
        return "SPEC_REFINEMENT_CAP_REACHED"
    if stop == RunnerStopReason.COST_BUDGET:
        return "SPEC_REFINEMENT_BUDGET_REACHED"
    return ""


def emit_gate_escalation(
    *,
    seam_path: Path,
    stop_reason: RunnerStopReason,
    cycles: tuple[RunnerCycleResult, ...],
    total_cost_usd: float,
    notes: tuple[str, ...],
    gate_dir: Path = GATE_PENDING_DIR,
) -> Path:
    """Write a typed escalation record for the executive-inbox to pick up.

    Returns the path of the written JSON file. Never raises on
    pre-existing records of the same name — it overwrites, on the
    assumption that a later run's escalation supersedes an earlier
    one for the same seam. The operator reading the inbox should
    trust the most recent file timestamp."""

    gate_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "seam_path": str(seam_path),
        "escalation_reason": stop_reason.value,
        "equivalent_gate_reason": _rough_gate_reason_name(stop_reason),
        "cycle_count": len(cycles),
        "total_cost_usd": total_cost_usd,
        "notes": list(notes),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "advisory": True,
    }
    gate_file = gate_dir / f"gate_{seam_path.stem}.json"
    gate_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return gate_file


def _maybe_escalate(
    *,
    seam_path: Path,
    stop_reason: RunnerStopReason,
    cycles: tuple[RunnerCycleResult, ...],
    total_cost_usd: float,
    notes: tuple[str, ...],
) -> tuple[str, ...]:
    """Emit a gate file if the stop reason warrants one, returning
    notes extended with the gate-file path. Used by the run loop just
    before returning RunnerOutcome so the caller does not have to
    remember to invoke the adapter."""

    if stop_reason not in _ESCALATION_STOP_REASONS:
        return notes
    gate_file = emit_gate_escalation(
        seam_path=seam_path,
        stop_reason=stop_reason,
        cycles=cycles,
        total_cost_usd=total_cost_usd,
        notes=notes,
    )
    try:
        gate_rel = str(gate_file.relative_to(REPO_ROOT))
    except ValueError:
        gate_rel = str(gate_file)
    return notes + (f"executive-inbox gate record written: {gate_rel}",)


# ---------------------------------------------------------------------------
# Spec auto-drafting on seam convergence
# ---------------------------------------------------------------------------

_SPECS_DIR = REPO_ROOT / "research_areas" / "private" / "specs" / "active"


def _extract_seam_id(seam_path: Path) -> str:
    """Extract GP-NNN from seam filename."""
    m = re.search(r"(GP-\d+)", seam_path.name)
    return m.group(1) if m else "GP-XXX"


def _extract_seam_title(seam_path: Path) -> str:
    """Extract the title from the seam's first H1 line."""
    for line in seam_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            raw = line.lstrip("# ").strip()
            raw = re.sub(r"^GP-\d+\s*[—\-]\s*", "", raw)
            return re.sub(r"\s*[Ss]eam\s*$", "", raw).strip()
    return seam_path.stem


def _draft_spec_from_seam(
    seam_path: Path,
    *,
    claude_model: str,
    ledger_path: Path | None = None,
) -> Path:
    """Auto-draft a spec file from a converged seam using an LLM call.

    Idempotent: if the spec file already exists (e.g., from a prior
    crashed run), returns the existing path without overwriting.
    """
    seam_id = _extract_seam_id(seam_path)
    seam_title = _extract_seam_title(seam_path)
    seam_text = seam_path.read_text(encoding="utf-8")

    stem = seam_path.stem
    slug = stem.removesuffix("_seam") if stem.endswith("_seam") else stem
    spec_filename = f"{slug}_spec.md"
    spec_path = _SPECS_DIR / spec_filename

    if spec_path.exists():
        print(
            f"[findings-runner] spec already exists at {spec_path} — "
            f"skipping draft (idempotent recovery)",
            flush=True,
        )
        return spec_path

    try:
        seam_rel = str(seam_path.relative_to(REPO_ROOT))
    except ValueError:
        seam_rel = str(seam_path)

    spec_system = (
        "You are a technical architect drafting a spec from a converged seam debate. "
        "The spec is a clean blueprint — no debate log, no investigation narrative. "
        "Follow this exact structure:\n\n"
        "# <Title>\n\n"
        "## Status\n\nActive\n\n"
        f"## Seam\n\n{seam_rel}\n\n"
        "## Scope\n\n- ...\n\n"
        "## Decision\n\n<one paragraph>\n\n"
        "## Problem\n\n## Why It Matters\n\n## Constraints\n\n"
        "## Options\n\n<table with Pros/Cons/Verdict per option>\n\n"
        "## Recommendation\n\n## Implementation Sketch\n\n## Open Questions\n\n"
        "Extract all content from the seam debate. Do not invent new claims. "
        "The spec must faithfully represent the converged position from the debate."
    )

    prompt = (
        f"Draft a spec for: {seam_id} — {seam_title}\n\n"
        f"Converged seam content:\n\n{seam_text}"
    )

    client = Anthropic()
    response = client.messages.create(
        model=claude_model,
        max_tokens=4096,
        system=spec_system,
        messages=[{"role": "user", "content": prompt}],
    )
    if not response.content or not hasattr(response.content[0], "text"):
        raise RuntimeError(
            f"spec draft LLM call returned empty or non-text content: {response.content}"
        )
    spec_content = response.content[0].text

    if ledger_path is not None:
        usage = response.usage
        telemetry = TurnUsageTelemetry(
            model_name=claude_model,
            input_tokens=int(getattr(usage, "input_tokens", 0)),
            output_tokens=int(getattr(usage, "output_tokens", 0)),
            cache_creation_input_tokens=int(getattr(usage, "cache_creation_input_tokens", 0)),
            cache_read_input_tokens=int(getattr(usage, "cache_read_input_tokens", 0)),
            estimated_cost_usd=estimate_cost_usd(
                model_name=claude_model,
                input_tokens=int(getattr(usage, "input_tokens", 0)),
                output_tokens=int(getattr(usage, "output_tokens", 0)),
                cache_creation_input_tokens=int(getattr(usage, "cache_creation_input_tokens", 0)),
                cache_read_input_tokens=int(getattr(usage, "cache_read_input_tokens", 0)),
            ),
            telemetry_captured=True,
        )
        append_usage_ledger(
            ledger_path=ledger_path,
            telemetry=telemetry,
            agent="spec_draft",
            cycle_index=0,
        )

    _SPECS_DIR.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(spec_content, encoding="utf-8")
    return spec_path


def _insert_phase_marker_and_recommendation(
    seam_path: Path,
    spec_path: Path,
    today: str,
) -> None:
    """Append a Recommendation section and spec-phase marker to the seam."""
    seam_text = seam_path.read_text(encoding="utf-8")
    try:
        spec_rel = str(spec_path.relative_to(REPO_ROOT))
    except ValueError:
        spec_rel = str(spec_path)

    phase_block = (
        f"\n\n## Recommendation\n\n"
        f"See spec: `{spec_rel}` (auto-drafted {today} from converged seam debate).\n\n"
        f"<!-- FINDINGS_DEBATE_PHASE: spec path={spec_rel} -->\n\n"
        f"### Spec Review Phase\n\n"
        f"The spec has been auto-drafted from the converged seam debate above. "
        f"The following turns review the spec for implementation correctness, "
        f"missing constraints, and integration gaps.\n\n"
    )

    seam_path.write_text(seam_text + phase_block, encoding="utf-8")


_SPEC_REVISION_MARKER = "<!-- SPEC_REVISED_FROM_DEBATE"


def _revise_spec_from_debate(
    seam_path: Path,
    spec_path: Path,
    *,
    claude_model: str,
    today: str,
    ledger_path: Path | None = None,
) -> bool:
    """Revise a spec based on converged spec-review debate turns.

    Idempotent: if the spec already contains the revision marker, returns
    False without touching the file.  On success, writes the revised spec
    and appends a revision note to the seam, then returns True.
    """
    spec_text = spec_path.read_text(encoding="utf-8")
    if _SPEC_REVISION_MARKER in spec_text:
        print(
            "[findings-runner] spec already revised (marker found) — skipping",
            flush=True,
        )
        return False

    state = read_debate_state(seam_path)
    phase, _, last_seam_turn_idx = _detect_phase(seam_path)
    if phase != DebatePhase.SPEC or last_seam_turn_idx is None:
        return False

    spec_turns = [t for t in state.turns if t.index > last_seam_turn_idx]
    if not spec_turns:
        return False

    debate_summary = "\n\n".join(
        f"### Turn {t.index} — {t.agent}\n{t.body.strip()}"
        for t in spec_turns
    )

    system = (
        "You are revising a spec based on a converged spec-review debate. "
        "Apply all accepted changes from the debate turns to the spec. "
        "Do NOT add new claims that were not in the debate. "
        "Do NOT remove sections — only modify content within existing sections. "
        "Preserve the exact markdown structure (headings, tables, lists). "
        "At the very end of the file, append this marker on its own line:\n"
        f"{_SPEC_REVISION_MARKER} {today} -->\n"
    )

    prompt = (
        f"## Current spec\n\n{spec_text}\n\n"
        f"## Spec-review debate turns (converged)\n\n{debate_summary}\n\n"
        "Produce the complete revised spec with all accepted changes applied."
    )

    client = Anthropic()
    response = client.messages.create(
        model=claude_model,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if not response.content or not hasattr(response.content[0], "text"):
        raise RuntimeError(
            f"spec revision LLM call returned empty content: {response.content}"
        )

    if ledger_path is not None:
        usage = response.usage
        telemetry = TurnUsageTelemetry(
            model_name=claude_model,
            input_tokens=int(getattr(usage, "input_tokens", 0)),
            output_tokens=int(getattr(usage, "output_tokens", 0)),
            cache_creation_input_tokens=int(getattr(usage, "cache_creation_input_tokens", 0)),
            cache_read_input_tokens=int(getattr(usage, "cache_read_input_tokens", 0)),
            estimated_cost_usd=estimate_cost_usd(
                model_name=claude_model,
                input_tokens=int(getattr(usage, "input_tokens", 0)),
                output_tokens=int(getattr(usage, "output_tokens", 0)),
                cache_creation_input_tokens=int(getattr(usage, "cache_creation_input_tokens", 0)),
                cache_read_input_tokens=int(getattr(usage, "cache_read_input_tokens", 0)),
            ),
            telemetry_captured=True,
        )
        append_usage_ledger(
            ledger_path=ledger_path,
            telemetry=telemetry,
            agent="spec_revision",
            cycle_index=0,
        )

    revised = response.content[0].text
    if _SPEC_REVISION_MARKER not in revised:
        revised = revised.rstrip() + f"\n\n{_SPEC_REVISION_MARKER} {today} -->\n"

    spec_path.write_text(revised, encoding="utf-8")
    print(f"[findings-runner] spec revised at {spec_path}", flush=True)

    try:
        spec_rel = str(spec_path.relative_to(REPO_ROOT))
    except ValueError:
        spec_rel = str(spec_path)
    seam_text = seam_path.read_text(encoding="utf-8")
    revision_note = (
        f"\n\n## Spec Revision Log\n\n"
        f"- **{today}:** Spec at `{spec_rel}` revised automatically from "
        f"converged spec-review debate ({len(spec_turns)} turns). "
        f"Changes applied by LLM post-convergence pass.\n"
    )
    seam_path.write_text(seam_text + revision_note, encoding="utf-8")

    return True


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
    agent_mode: AgentMode = DEFAULT_AGENT_MODE,
    context_token_budget: int = 30_000,
    skeptic_persona_path: Path | None = None,
    auto_spec: bool = False,
    reviewer_domains: list[str] | None = None,
    workspace_dir: Path | None = None,
) -> RunnerOutcome:
    """Drive a findings-debate to convergence or escalation.

    The loop is: read state → exit if terminal → choose agent → cost
    pre-check → call agent → parse decision → append turn → re-read
    state. ``execute=False`` performs all the planning steps (state
    reads, agent selection, prompt construction) without issuing API
    calls or appending turns; this is the dry-run mode used to verify
    the runner against a seam before spending tokens.

    When ``auto_spec=True``, seam-phase convergence triggers automatic
    spec drafting and a transition to spec-review phase. The runner
    is idempotent: re-entry after a crash detects the phase from the
    seam file and resumes accordingly.

    When ``reviewer_domains`` is non-empty, the named domain-lens
    files are loaded from ``config/prompts/`` and injected into the
    skeptic's system prompt (single_claude mode only).
    """

    if not seam_path.exists():
        raise FileNotFoundError(f"seam file not found: {seam_path}")

    validate_findings_write_scope(seam_path)

    shared_grounding_text: str | None = None
    author_system_prompt: str | None = None
    skeptic_system_prompt: str | None = None
    # GP-079: LLM-driven persona routing with dynamic generation fallback.
    # When no explicit --reviewer-domains are passed, the LLM router selects
    # from the static catalog and optionally generates a dynamic persona.
    # Explicit domains bypass the router entirely (backward-compatible).
    reviewer_domains_text = ""
    _route_result = None  # track for potential promotion after debate

    if reviewer_domains is not None:
        # Explicit domains — load directly from static catalog
        reviewer_domains_text = load_reviewer_domains(reviewer_domains)
        print(
            f"[findings-runner] loaded {len(reviewer_domains)} explicit reviewer domain(s): "
            f"{', '.join(reviewer_domains)} ({len(reviewer_domains_text):,} chars)",
            flush=True,
        )
    elif workspace_dir is not None:
        from src.ztare.personas.routing import auto_select_from_workspace
        _route_result = auto_select_from_workspace(workspace_dir)
        if not _route_result.is_empty:
            reviewer_domains_text = _route_result.format_for_injection()
            method_tag = f"[{_route_result.routing_method}]"
            names = _route_result.all_names
            dynamic_count = len(_route_result.dynamic_personas)
            print(
                f"[findings-runner] {method_tag} auto-routed {len(names)} persona(s) "
                f"from failure families: {', '.join(names)}"
                + (f" ({dynamic_count} dynamic)" if dynamic_count else ""),
                flush=True,
            )
    if agent_mode == AgentMode.SINGLE_CLAUDE:
        shared_grounding_text = load_shared_grounding(skeptic_persona_path=skeptic_persona_path)
        author_system_prompt = build_single_claude_system_prompt(
            role="author", shared_grounding=shared_grounding_text
        )
        skeptic_system_prompt = build_single_claude_system_prompt(
            role="skeptic",
            shared_grounding=shared_grounding_text,
            reviewer_domains_text=reviewer_domains_text,
        )
        print(
            f"[findings-runner] single_claude grounding loaded "
            f"({len(shared_grounding_text):,} chars; "
            f"author_prompt={len(author_system_prompt):,} chars; "
            f"skeptic_prompt={len(skeptic_system_prompt):,} chars)",
            flush=True,
        )

    cycles: list[RunnerCycleResult] = []
    notes: list[str] = []
    ledger_path = usage_ledger_path_for_seam(seam_path)
    today_str = today or _date.today().isoformat()

    state = read_debate_state(seam_path)

    if state.status == DebateStatus.CONVERGED:
        if auto_spec and state.phase == DebatePhase.SEAM and execute:
            print(
                "[findings-runner] seam debate converged — auto-drafting spec...",
                flush=True,
            )
            spec_path = _draft_spec_from_seam(
                seam_path, claude_model=claude_model,
                ledger_path=ledger_path,
            )
            _insert_phase_marker_and_recommendation(
                seam_path, spec_path, today_str,
            )
            print(
                f"[findings-runner] spec drafted at {spec_path} — "
                f"transitioning to spec-review phase",
                flush=True,
            )
            state = read_debate_state(seam_path)
        elif auto_spec and not execute:
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.CONVERGED,
                final_debate_status=state.status.value,
                cycles=(),
                total_cost_usd=0.0,
                notes=(
                    "seam debate converged but --auto-spec requires --execute to draft spec. "
                    "Re-run with --execute to trigger spec drafting.",
                ),
            )
        else:
            entry_revision_notes: list[str] = [
                "debate was already fully converged on entry — no turns appended",
            ]
            if auto_spec and execute and state.phase == DebatePhase.SPEC and state.spec_path:
                spec_file = REPO_ROOT / state.spec_path
                if spec_file.exists():
                    revised = _revise_spec_from_debate(
                        seam_path, spec_file,
                        claude_model=claude_model, today=today_str,
                        ledger_path=ledger_path,
                    )
                    if revised:
                        entry_revision_notes.append(
                            f"spec revised from converged debate at {spec_file}"
                        )
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.CONVERGED,
                final_debate_status=state.status.value,
                cycles=(),
                total_cost_usd=0.0,
                notes=tuple(entry_revision_notes),
            )
    if state.status == DebateStatus.ESCALATED_CAP:
        entry_notes: tuple[str, ...] = (
            f"seam was already at hard turn cap ({HARD_TURN_CAP}) on entry",
        )
        entry_notes = _maybe_escalate(
            seam_path=seam_path,
            stop_reason=RunnerStopReason.ESCALATED_CAP,
            cycles=(),
            total_cost_usd=0.0,
            notes=entry_notes,
        )
        return RunnerOutcome(
            seam_path=seam_path,
            stop_reason=RunnerStopReason.ESCALATED_CAP,
            final_debate_status=state.status.value,
            cycles=(),
            total_cost_usd=0.0,
            notes=entry_notes,
        )

    cumulative_cost = 0.0

    for cycle_index in range(1, max_cycles + 1):
        print(
            f"[findings-runner] cycle {cycle_index}/{max_cycles} starting "
            f"(status={state.status.value} cost={cumulative_cost:.6f})",
            flush=True,
        )
        agent = choose_next_agent(state, agent_mode=agent_mode)
        if agent is None:
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.NO_AGENT,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=("seam has only non-debate turns; runner cannot route",),
            )

        print(f"[findings-runner]   routed to agent={agent}", flush=True)
        seam_text = seam_path.read_text(encoding="utf-8")
        prompt_text = build_turn_prompt(
            seam_text=seam_text,
            agent=agent,
            debate_state=state,
            seam_path=seam_path,
            token_budget=context_token_budget,
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
            escalated_notes = _maybe_escalate(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.COST_BUDGET,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=tuple(notes),
            )
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.COST_BUDGET,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=escalated_notes,
            )

        print(
            f"[findings-runner]   dispatching {agent} call "
            f"(prompt_chars={len(prompt_text)})",
            flush=True,
        )
        if agent == "Claude":
            response_text, telemetry = call_claude(
                prompt_text=prompt_text,
                model_name=claude_model,
            )
        elif agent == SINGLE_CLAUDE_AUTHOR:
            assert author_system_prompt is not None, (
                "single_claude mode reached author seat without grounding loaded"
            )
            response_text, telemetry = call_claude(
                prompt_text=prompt_text,
                model_name=claude_model,
                system_prompt=author_system_prompt,
            )
        elif agent == SINGLE_CLAUDE_SKEPTIC:
            assert skeptic_system_prompt is not None, (
                "single_claude mode reached skeptic seat without grounding loaded"
            )
            response_text, telemetry = call_claude(
                prompt_text=prompt_text,
                model_name=claude_model,
                system_prompt=skeptic_system_prompt,
            )
        elif agent == "Gemini":
            gemini_prompt = prompt_text
            if reviewer_domains_text:
                gemini_prompt = (
                    "## Reviewer Domain Lenses\n\n"
                    "Apply the following domain lenses when evaluating this seam. "
                    "These are your epistemic constraints for this turn — "
                    "they define the frame from which you critique.\n\n"
                    + reviewer_domains_text
                    + "\n\n---\n\n"
                    + prompt_text
                )
            response_text, telemetry = call_gemini(
                prompt_text=gemini_prompt,
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

        print(
            f"[findings-runner]   {agent} returned "
            f"(response_chars={len(response_text)} "
            f"cost_delta={telemetry.estimated_cost_usd:.6f})",
            flush=True,
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
        print(
            f"[findings-runner]   turn appended idx={appended_turn.index} "
            f"sentinel={sentinel_raised} status_after={state.status.value} "
            f"cum_cost={cumulative_cost:.6f}",
            flush=True,
        )
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

        if state.status == DebateStatus.CONVERGED and auto_spec and state.phase == DebatePhase.SEAM:
            print(
                "[findings-runner] seam debate converged mid-loop — auto-drafting spec...",
                flush=True,
            )
            spec_path = _draft_spec_from_seam(
                seam_path, claude_model=claude_model,
                ledger_path=ledger_path,
            )
            _insert_phase_marker_and_recommendation(
                seam_path, spec_path, today_str,
            )
            notes.append(f"spec auto-drafted at {spec_path}")
            print(
                f"[findings-runner] spec drafted at {spec_path} — "
                f"continuing to spec-review phase",
                flush=True,
            )
            state = read_debate_state(seam_path)
            continue
        if state.status == DebateStatus.CONVERGED:
            if auto_spec and execute and state.phase == DebatePhase.SPEC and state.spec_path:
                spec_file = REPO_ROOT / state.spec_path
                if spec_file.exists():
                    revised = _revise_spec_from_debate(
                        seam_path, spec_file,
                        claude_model=claude_model, today=today_str,
                        ledger_path=ledger_path,
                    )
                    if revised:
                        notes.append(f"spec revised from converged debate at {spec_file}")
            # GP-079: promote dynamic personas on successful convergence
            if _route_result and _route_result.dynamic_personas:
                from src.ztare.personas.routing import promote_dynamic_persona
                for dp in _route_result.dynamic_personas:
                    promoted_path = promote_dynamic_persona(dp)
                    notes.append(f"promoted dynamic persona '{dp.name}' to {promoted_path.name}")
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.CONVERGED,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=tuple(notes),
            )
        if state.status == DebateStatus.ESCALATED_CAP:
            escalated_notes = _maybe_escalate(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.ESCALATED_CAP,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=tuple(notes),
            )
            return RunnerOutcome(
                seam_path=seam_path,
                stop_reason=RunnerStopReason.ESCALATED_CAP,
                final_debate_status=state.status.value,
                cycles=tuple(cycles),
                total_cost_usd=cumulative_cost,
                notes=escalated_notes,
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
    domains = (
        [d.strip() for d in args.reviewer_domains.split(",") if d.strip()]
        if args.reviewer_domains
        else None
    )
    outcome = run_findings_debate(
        seam_path=args.seam_path,
        max_cycles=args.max_cycles,
        max_cost_usd=args.max_cost_usd,
        claude_model=args.claude_model,
        gemini_model=args.gemini_model,
        execute=args.execute,
        today=args.today,
        agent_mode=AgentMode(args.agent_mode),
        context_token_budget=args.context_token_budget,
        skeptic_persona_path=args.skeptic_persona_path,
        auto_spec=args.auto_spec,
        reviewer_domains=domains,
        workspace_dir=args.workspace_dir,
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
    parser.add_argument(
        "--agent-mode",
        type=str,
        choices=[m.value for m in AgentMode],
        default=DEFAULT_AGENT_MODE.value,
        help=(
            "Seat lineup. 'claude_gemini' (default) alternates Claude and "
            "Gemini across providers. 'single_claude' alternates "
            "Claude-Author and Claude-Skeptic on the Anthropic API with "
            "different system prompts (skeptic seat loads the automated "
            "skeptic persona file)."
        ),
    )
    parser.add_argument(
        "--context-token-budget",
        type=int,
        default=30_000,
        help="Token budget for the GP-036 context builder (tiers 1-3).",
    )
    parser.add_argument(
        "--skeptic-persona-path",
        type=Path,
        default=None,
        help=(
            "Override path to the automated skeptic persona file used by "
            "single_claude mode. Defaults to the operator's Claude Code "
            "memory directory."
        ),
    )
    parser.add_argument(
        "--auto-spec",
        action="store_true",
        help=(
            "On seam-debate convergence, auto-draft a spec and continue "
            "with spec-review debate. Idempotent: re-entry detects the "
            "phase from the seam file and resumes."
        ),
    )
    parser.add_argument(
        "--reviewer-domains",
        type=str,
        default=None,
        help=(
            "Comma-separated list of domain lenses to inject into the "
            "skeptic prompt (single_claude mode). Each name maps to "
            "config/prompts/reviewer_domain_{name}.md. Example: "
            "philosophy_of_science,systems_ml,symbolic_regression,"
            "munger_multidisciplinary. If omitted and --workspace-dir is "
            "provided, domains are auto-routed from failure families "
            "(GP-079 Option 3)."
        ),
    )
    parser.add_argument(
        "--workspace-dir",
        type=Path,
        default=None,
        help=(
            "Path to the project workspace directory containing "
            "latent_distance.jsonl. Used for GP-079 Option 3 auto-routing "
            "when --reviewer-domains is not explicitly set. "
            "Example: projects/gp080_01/workspace"
        ),
    )
    parser.set_defaults(func=cmd_run_findings_debate)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
