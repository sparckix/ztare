"""Findings-debate state primitive for GP-031.

First-slice implementation of the debate-converge loop described in
``research_areas/seams/GP-031_findings_birth_bridge_seam.md``.

This module is intentionally *not* a new SeedPipelineType and does not
enter the seed registry. Per Codex Turn 2, findings-debate is pre-seed
work: the object under debate is a seam file, not a program seed.
Promotion from seam → seed is a separate explicit edge handled in
``supervisor_findings_promotion.py``.

What this module provides:

- a parser that reads a markdown seam file and returns a structured
  view of its debate log (turns per agent, turn ordering, the sentinel
  that marks a turn as adding no new load-bearing claim)
- a convergence rule that is deliberately minimal and fails open to the
  operator (min 2 turns per agent, both agents' most-recent turn carries
  the sentinel, else pending; at hard turn cap the state escalates to
  the operator rather than auto-converging)
- an append helper that writes a new turn to the seam file without
  touching the prior content, preserving append-only debate-log shape

What this module explicitly does not provide:

- LLM dispatch to Claude or Codex (that integration is a later slice
  and lives in the wrapper layer, not here)
- promotion into ``seed_registry.json`` (see
  ``supervisor_findings_promotion.py``)
- finding detection from runtime output (explicit last-slice item per
  the GP-031 recommendation, deferred)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


SENTINEL_NO_NEW_CLAIM = "<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->"
"""Marker an agent includes anywhere in a turn body to signal that the
turn adds no new load-bearing architectural claim the other agent has
not already addressed. This is the explicit-flag exit channel Codex
Turn 2 required; it is not an LLM judge."""

PHASE_SPEC_PATTERN = re.compile(
    r"<!--\s*FINDINGS_DEBATE_PHASE:\s*spec\s*(?:path=([^\s]+))?\s*-->",
)

HARD_TURN_CAP = 12

MIN_TURNS_PER_AGENT = 2
"""Both agents must produce at least this many turns before the
convergence rule can fire. Prevents a drive-by single-turn "no new
claim" from closing the debate prematurely."""

# Matches: "### Turn 3 — Claude (2026-04-11) — Optional title"
# Also matches compound agent names used in single_claude mode, e.g.
# "### Turn 4 — Claude-Author (2026-04-15) — Autonomous runner turn"
# (the hyphen in ``Claude-Author`` / ``Claude-Skeptic`` must be in the
# character class, or single_claude turns silently fail to parse and the
# runner burns budget re-appending Turn 1 each cycle).
# Agent name is captured loosely; we normalize downstream.
_TURN_HEADER = re.compile(
    r"^###\s+Turn\s+(\d+)\s*[—\-]\s*([A-Za-z][A-Za-z0-9 _\-]*?)\s*(?:\(|—|$)",
    re.MULTILINE,
)


class DebatePhase(str, Enum):
    """Which phase of the seam-to-spec debate cycle we are in."""

    SEAM = "seam"
    """Debating the seam itself. Convergence here triggers spec draft."""

    SPEC = "spec"
    """Debating the spec (on the same seam file). Convergence here is terminal."""


class DebateStatus(str, Enum):
    """Outcome of the convergence check on a findings-debate seam."""

    PENDING = "pending"
    """The rule has not fired yet. Either there are fewer than
    ``MIN_TURNS_PER_AGENT`` turns from at least one agent, or the most
    recent turn from one or both agents does not carry the sentinel."""

    CONVERGED = "converged"
    """Both agents have at least ``MIN_TURNS_PER_AGENT`` turns and each
    agent's most recent turn carries the sentinel. The operator can seal
    the seam and (optionally) route it to the promotion edge."""

    ESCALATED_CAP = "escalated_cap"
    """The debate crossed ``HARD_TURN_CAP`` turns without the rule
    firing. The operator must decide whether the seam is actually
    converged, still alive, or stuck and should be demoted."""


@dataclass(frozen=True)
class DebateTurn:
    """A single parsed turn from a findings-debate seam file."""

    index: int
    agent: str
    body: str
    no_new_load_bearing: bool


@dataclass(frozen=True)
class DebateState:
    """Structured view of a findings-debate seam's debate log."""

    seam_path: Path
    turns: tuple[DebateTurn, ...]
    status: DebateStatus
    phase: DebatePhase = DebatePhase.SEAM
    spec_path: str | None = None

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    def turns_by_agent(self) -> dict[str, tuple[DebateTurn, ...]]:
        grouped: dict[str, list[DebateTurn]] = {}
        for turn in self.turns:
            grouped.setdefault(turn.agent, []).append(turn)
        return {agent: tuple(items) for agent, items in grouped.items()}


def parse_debate_log(seam_path: Path) -> tuple[DebateTurn, ...]:
    """Parse a seam file's ``## Debate Log`` section into ordered turns.

    The parser is deliberately tolerant. It walks the file, finds turn
    headers of the form ``### Turn N — Agent (date) — Title``, and slices
    the body between consecutive headers. A turn body includes everything
    up to (but not including) the next header or end-of-file. The
    sentinel check is a plain substring test on the body.
    """

    text = seam_path.read_text(encoding="utf-8")
    headers = list(_TURN_HEADER.finditer(text))
    if not headers:
        return ()

    turns: list[DebateTurn] = []
    for idx, match in enumerate(headers):
        start = match.end()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(text)
        body = text[start:end]
        turn_index = int(match.group(1))
        agent = _normalize_agent(match.group(2))
        turns.append(
            DebateTurn(
                index=turn_index,
                agent=agent,
                body=body,
                no_new_load_bearing=SENTINEL_NO_NEW_CLAIM in body,
            )
        )

    turns.sort(key=lambda t: t.index)
    return tuple(turns)


def check_convergence(
    turns: tuple[DebateTurn, ...],
    *,
    spec_review: bool = False,
) -> DebateStatus:
    """Apply the minimal convergence rule from GP-031 Turn 2.

    Rule (explicit, rule-based, no LLM call):
    1. If the debate has crossed ``HARD_TURN_CAP``, return
       ``ESCALATED_CAP`` — operator must decide.
    2. Group turns by agent. Require at least
       ``MIN_TURNS_PER_AGENT`` turns from each of the known debate
       agents present. If fewer, return ``PENDING``.
    3. For each agent with any turns, check the most recent turn. If
       every present agent's most recent turn carries the sentinel,
       return ``CONVERGED``. Otherwise ``PENDING``.

    An agent that has never contributed does not block convergence; the
    rule only applies to agents that have actually produced turns. This
    keeps the rule useful on bilateral (Claude/Codex) debates and
    doesn't require upfront declaration of participants.

    When ``spec_review=True``, an additional convergence shortcut
    applies: if any agent has raised the sentinel on its last 2
    consecutive turns, converge. In spec-review, the spec artifact is
    frozen during debate, so the Skeptic will keep finding flags on
    unchanged text while the Author accepts them. Two consecutive
    Author sentinels means "substance is settled, only transcription
    remains" — the post-convergence revision pass handles the update.
    """

    if len(turns) > HARD_TURN_CAP:
        return DebateStatus.ESCALATED_CAP

    grouped: dict[str, list[DebateTurn]] = {}
    for turn in turns:
        grouped.setdefault(turn.agent, []).append(turn)

    if len(grouped) < 2:
        return DebateStatus.PENDING

    for agent_turns in grouped.values():
        if len(agent_turns) < MIN_TURNS_PER_AGENT:
            return DebateStatus.PENDING

    # Standard rule: both agents' most recent turns carry sentinel.
    all_recent_sentinel = all(
        max(agent_turns, key=lambda t: t.index).no_new_load_bearing
        for agent_turns in grouped.values()
    )
    if all_recent_sentinel:
        return DebateStatus.CONVERGED

    # Spec-review shortcut: any agent's last 2 turns both carry sentinel.
    if spec_review:
        for agent_turns in grouped.values():
            sorted_turns = sorted(agent_turns, key=lambda t: t.index)
            if len(sorted_turns) >= 2:
                if sorted_turns[-1].no_new_load_bearing and sorted_turns[-2].no_new_load_bearing:
                    return DebateStatus.CONVERGED

    return DebateStatus.PENDING


def _detect_phase(seam_path: Path) -> tuple[DebatePhase, str | None, int | None]:
    """Detect debate phase from the seam file.

    Returns (phase, spec_path_or_none, phase_marker_turn_index_or_none).
    The turn index is the last turn BEFORE the phase marker — turns after
    it belong to the spec-review phase.
    """
    text = seam_path.read_text(encoding="utf-8")
    m = PHASE_SPEC_PATTERN.search(text)
    if not m:
        return DebatePhase.SEAM, None, None
    spec_path = m.group(1) if m.group(1) else None
    marker_pos = m.start()
    headers = list(_TURN_HEADER.finditer(text))
    last_seam_turn_idx: int | None = None
    for h in headers:
        if h.start() < marker_pos:
            last_seam_turn_idx = int(h.group(1))
    return DebatePhase.SPEC, spec_path, last_seam_turn_idx


def read_debate_state(seam_path: Path) -> DebateState:
    """Read a seam file, parse its debate log, and return a full state.

    Phase-aware: if the seam contains a spec-phase marker, only turns
    after the marker count toward convergence. This makes the runner
    idempotent — re-entry after a crash during spec debate resumes
    from the spec phase, not the seam phase."""

    all_turns = parse_debate_log(seam_path)
    phase, spec_path, last_seam_turn_idx = _detect_phase(seam_path)

    if phase == DebatePhase.SPEC and last_seam_turn_idx is not None:
        spec_turns = tuple(t for t in all_turns if t.index > last_seam_turn_idx)
        if len(spec_turns) > HARD_TURN_CAP:
            status = DebateStatus.ESCALATED_CAP
        else:
            status = check_convergence(spec_turns, spec_review=True)
    elif len(all_turns) > HARD_TURN_CAP:
        status = DebateStatus.ESCALATED_CAP
    else:
        status = check_convergence(all_turns)

    return DebateState(
        seam_path=seam_path,
        turns=all_turns,
        status=status,
        phase=phase,
        spec_path=spec_path,
    )


def append_turn(
    seam_path: Path,
    agent: str,
    date: str,
    title: str,
    body: str,
    no_new_load_bearing: bool,
) -> DebateTurn:
    """Append a new turn to a seam file's debate log.

    The caller is responsible for the LLM invocation that produced the
    body. This function is a dumb writer: it computes the next turn
    index, injects the sentinel if requested, and appends the formatted
    turn to the seam file without touching prior content.

    Raises ``FileNotFoundError`` if the seam file does not exist and
    ``ValueError`` if the seam file has no ``## Debate Log`` header — the
    debate module refuses to invent one, so seams are always created by
    hand (as they are today) and only appended to mechanically.
    """

    if not seam_path.exists():
        raise FileNotFoundError(f"seam file not found: {seam_path}")

    existing_text = seam_path.read_text(encoding="utf-8")
    if "## Debate Log" not in existing_text:
        raise ValueError(
            f"seam file has no '## Debate Log' section: {seam_path}"
        )

    existing_turns = parse_debate_log(seam_path)
    next_index = (existing_turns[-1].index + 1) if existing_turns else 1
    normalized_agent = _normalize_agent(agent)

    sentinel_line = f"\n\n{SENTINEL_NO_NEW_CLAIM}" if no_new_load_bearing else ""
    header = f"\n### Turn {next_index} — {normalized_agent} ({date}) — {title}\n\n"
    formatted = f"{header}{body.rstrip()}{sentinel_line}\n"

    if not existing_text.endswith("\n"):
        formatted = "\n" + formatted

    with seam_path.open("a", encoding="utf-8") as handle:
        handle.write(formatted)

    # Round-trip safety: re-parse the seam and confirm the just-written
    # turn is recoverable. If not, the regex, the agent name, or the body
    # has broken re-parsing and the runner would otherwise burn budget
    # appending the same turn index on every cycle. Rollback by
    # truncating the file to its prior length and raise.
    rechecked = parse_debate_log(seam_path)
    recovered = any(
        t.index == next_index and t.agent == normalized_agent for t in rechecked
    )
    if not recovered:
        seam_path.write_text(existing_text, encoding="utf-8")
        raise ValueError(
            f"append_turn wrote Turn {next_index} — {normalized_agent} but "
            f"parse_debate_log could not recover it; file rolled back. "
            f"Likely cause: turn header regex does not accept the agent "
            f"name, or body contains a ##-level header that terminates "
            f"the ## Debate Log section."
        )

    return DebateTurn(
        index=next_index,
        agent=normalized_agent,
        body=f"{body.rstrip()}{sentinel_line}\n",
        no_new_load_bearing=no_new_load_bearing,
    )


def _normalize_agent(raw: str) -> str:
    """Normalize agent names so 'Claude', 'claude', 'Claude ' all match.

    Claude, Codex, Gemini, Operator, and Principal are recognized.
    Any other agent string is preserved verbatim (after strip) so
    custom-named turns still parse, but they participate in the
    convergence rule as additional present agents — which is acceptable:
    any turn in a findings debate counts as a turn that must carry the
    sentinel to converge, matching the explicit fail-open contract.

    Principal is the human owner of the repo.  An Operator turn is an
    agent-written administrative turn; a Principal turn carries human
    authority and can close debates by directive (the convergence rule
    still requires the sentinel, but the runner respects Principal
    turns for display and audit purposes).
    """

    stripped = raw.strip()
    lowered = stripped.lower()
    if lowered == "claude":
        return "Claude"
    if lowered.startswith("claude-"):
        suffix = stripped[len("claude-"):]
        return f"Claude-{suffix[0].upper()}{suffix[1:]}"
    if lowered == "codex":
        return "Codex"
    if lowered == "gemini":
        return "Gemini"
    if lowered == "operator":
        return "Operator"
    if lowered == "principal":
        return "Principal"
    return stripped
