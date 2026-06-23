"""Fixture regression for the GP-031 findings-debate runner.

Covers only the pure functions: ``parse_sentinel_decision``,
``choose_next_agent``, and ``build_turn_prompt``. The API dispatch
functions (``call_claude``, ``call_gemini``) and the full
``run_findings_debate`` loop are exercised by live runs against real
seams; mocking the SDKs would not catch the kinds of bugs that matter
for this primitive (prompt structure, sentinel parsing, agent
alternation).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from ztare.supervisor.supervisor_findings_debate import (
    SENTINEL_NO_NEW_CLAIM,
    DebateState,
    DebateStatus,
    DebateTurn,
    append_turn,
    parse_debate_log,
    read_debate_state,
)
from ztare.supervisor.supervisor_findings_runner import (
    AgentMode,
    RunnerStopReason,
    RunnerWriteScopeError,
    SINGLE_CLAUDE_AUTHOR,
    SINGLE_CLAUDE_SKEPTIC,
    build_turn_prompt,
    choose_next_agent,
    emit_gate_escalation,
    parse_sentinel_decision,
    validate_findings_write_scope,
)
from ztare.findings.findings_context import (
    DEFAULT_TOKEN_BUDGET,
    build_findings_context,
    format_context_tiers,
)


def _state_with_turns(turns: tuple[DebateTurn, ...]) -> DebateState:
    return DebateState(seam_path=Path("/dev/null"), turns=turns, status=DebateStatus.PENDING)


def test_parse_sentinel_raise_clean_body() -> None:
    raw = "Body line one.\n\nBody line two.\n\nSENTINEL_DECISION: raise\n"
    body, raised = parse_sentinel_decision(raw)
    assert raised is True, "raise should set flag"
    assert "SENTINEL_DECISION" not in body, "decision line must be stripped from body"
    assert "Body line one." in body
    assert "Body line two." in body


def test_parse_sentinel_hold() -> None:
    raw = "Some content.\nSENTINEL_DECISION: hold"
    body, raised = parse_sentinel_decision(raw)
    assert raised is False
    assert "SENTINEL_DECISION" not in body


def test_parse_sentinel_missing_defaults_to_hold() -> None:
    raw = "Body without a decision line."
    body, raised = parse_sentinel_decision(raw)
    assert raised is False, "missing decision must default to hold (do not auto-converge)"
    assert "Body without a decision line." in body


def test_parse_sentinel_uses_last_match_when_repeated() -> None:
    raw = "First mention SENTINEL_DECISION: hold\nSecond mention\nSENTINEL_DECISION: raise"
    body, raised = parse_sentinel_decision(raw)
    assert raised is True, "the trailing decision is authoritative"


def test_parse_sentinel_case_insensitive() -> None:
    raw = "Content.\nsentinel_decision: RAISE"
    body, raised = parse_sentinel_decision(raw)
    assert raised is True


def test_parse_sentinel_inline_at_end_of_sentence() -> None:
    # Regression: GP-031 Turn 5 (Codex/o4-mini) emitted the marker
    # inline at the end of its closing paragraph instead of on its own
    # line. The earlier own-line-only regex missed it and the runner
    # appended the turn without the convergence marker. The lenient
    # parser must catch this shape.
    raw = (
        "I have addressed every prior concern and have nothing further "
        "to add. With that guardrail in place, I see no outstanding "
        "decision-critical architectural claims. SENTINEL_DECISION: raise"
    )
    body, raised = parse_sentinel_decision(raw)
    assert raised is True
    assert "SENTINEL_DECISION" not in body
    assert "decision-critical architectural claims." in body


def test_parse_sentinel_inline_in_middle_does_not_lock_in_early() -> None:
    # An agent that quotes the instructions early ("the SENTINEL_DECISION
    # contract requires...") and then makes its real decision at the end
    # should have the LAST occurrence honored, not the first.
    raw = (
        "Per the SENTINEL_DECISION: hold contract I will only raise when "
        "I have nothing new to add.\n\nI have nothing new to add.\n\n"
        "SENTINEL_DECISION: raise"
    )
    body, raised = parse_sentinel_decision(raw)
    assert raised is True


def test_choose_next_agent_empty_seam_starts_with_claude() -> None:
    state = _state_with_turns(())
    assert choose_next_agent(state) == "Claude"


def test_choose_next_agent_alternates_after_claude() -> None:
    turns = (DebateTurn(index=1, agent="Claude", body="x", no_new_load_bearing=False),)
    assert choose_next_agent(_state_with_turns(turns)) == "Gemini"


def test_choose_next_agent_alternates_after_gemini() -> None:
    turns = (
        DebateTurn(index=1, agent="Claude", body="x", no_new_load_bearing=False),
        DebateTurn(index=2, agent="Gemini", body="y", no_new_load_bearing=False),
    )
    assert choose_next_agent(_state_with_turns(turns)) == "Claude"


def test_choose_next_agent_legacy_codex_routes_to_claude() -> None:
    # Pre-swap seams may already contain Codex turns. The runner must
    # treat Codex as the "non-Claude" voice for routing so the
    # alternation invariant survives the swap from OpenAI→Gemini.
    turns = (
        DebateTurn(index=1, agent="Claude", body="x", no_new_load_bearing=False),
        DebateTurn(index=2, agent="Codex", body="y", no_new_load_bearing=False),
    )
    assert choose_next_agent(_state_with_turns(turns)) == "Claude"


def test_choose_next_agent_handles_double_claude_turn() -> None:
    # Turn 4 in GP-031 right now: Claude wrote two turns in a row.
    # The runner should still pick Gemini because Claude was the most
    # recent debate-side voice.
    turns = (
        DebateTurn(index=1, agent="Gemini", body="y", no_new_load_bearing=True),
        DebateTurn(index=2, agent="Claude", body="x", no_new_load_bearing=True),
        DebateTurn(index=3, agent="Claude", body="x2", no_new_load_bearing=True),
    )
    assert choose_next_agent(_state_with_turns(turns)) == "Gemini"


def test_choose_next_agent_returns_none_when_only_operator() -> None:
    # When the seam has only non-debate turns (e.g., a stray Operator
    # turn before either Claude or Codex weighed in), the runner should
    # refuse to guess and return None so the dispatcher reports
    # ``NO_AGENT`` and the operator can inspect.
    turns = (DebateTurn(index=1, agent="Operator", body="o", no_new_load_bearing=False),)
    assert choose_next_agent(_state_with_turns(turns)) is None


def test_build_turn_prompt_contains_seam_text_and_agent() -> None:
    seam_text = "## Hello\nThis is the seam body."
    state = _state_with_turns(())
    prompt = build_turn_prompt(seam_text=seam_text, agent="Claude", debate_state=state)
    assert "--- BEGIN SEAM ---" in prompt
    assert "--- END SEAM ---" in prompt
    assert seam_text in prompt
    assert "**Claude**" in prompt
    assert "0 prior turns" in prompt
    assert "SENTINEL_DECISION:" in prompt
    # No seam_path argument → no context block
    assert "--- BEGIN CONTEXT ---" not in prompt


def test_build_turn_prompt_reports_correct_turn_count() -> None:
    turns = (
        DebateTurn(index=1, agent="Claude", body="x", no_new_load_bearing=False),
        DebateTurn(index=2, agent="Codex", body="y", no_new_load_bearing=False),
    )
    prompt = build_turn_prompt(seam_text="seam", agent="Claude", debate_state=_state_with_turns(turns))
    assert "2 prior turns" in prompt


def test_runner_sees_real_seam_state() -> None:
    """End-to-end pure-side test against a real seam file in a tempdir.

    Writes a minimal seam with a Debate Log header and two turns from
    different agents, asks ``read_debate_state`` for the parsed state,
    and confirms ``choose_next_agent`` routes the next turn to the
    expected agent.
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        seam = Path(tmpdir) / "demo_seam.md"
        seam.write_text(
            "# Demo seam\n\n"
            "## Debate Log\n\n"
            "### Turn 1 — Claude (2026-04-11) — opening\n\n"
            f"Opening claim.\n\n{SENTINEL_NO_NEW_CLAIM}\n"
            "### Turn 2 — Gemini (2026-04-11) — sharpening\n\n"
            "Sharpening response.\n",
            encoding="utf-8",
        )
        state = read_debate_state(seam)
        assert state.turn_count == 2
        # Gemini went last → next is Claude
        assert choose_next_agent(state) == "Claude"
        # Gemini's last turn does NOT carry the sentinel → still pending
        assert state.status == DebateStatus.PENDING


def test_single_claude_mode_starts_with_author() -> None:
    state = _state_with_turns(())
    assert choose_next_agent(state, agent_mode=AgentMode.SINGLE_CLAUDE) == SINGLE_CLAUDE_AUTHOR


def test_single_claude_mode_alternates_author_skeptic() -> None:
    turns = (DebateTurn(index=1, agent=SINGLE_CLAUDE_AUTHOR, body="x", no_new_load_bearing=False),)
    assert choose_next_agent(_state_with_turns(turns), agent_mode=AgentMode.SINGLE_CLAUDE) == SINGLE_CLAUDE_SKEPTIC
    turns2 = turns + (DebateTurn(index=2, agent=SINGLE_CLAUDE_SKEPTIC, body="y", no_new_load_bearing=False),)
    assert choose_next_agent(_state_with_turns(turns2), agent_mode=AgentMode.SINGLE_CLAUDE) == SINGLE_CLAUDE_AUTHOR


def test_single_claude_mode_mixed_seam_defaults_to_author_on_tie() -> None:
    # Legacy Claude/Gemini turns on a seam that then switches to single_claude.
    # Routing picks whichever single_claude seat has fewer turns; tie → Author.
    turns = (
        DebateTurn(index=1, agent="Claude", body="x", no_new_load_bearing=False),
        DebateTurn(index=2, agent="Gemini", body="y", no_new_load_bearing=False),
    )
    assert choose_next_agent(_state_with_turns(turns), agent_mode=AgentMode.SINGLE_CLAUDE) == SINGLE_CLAUDE_AUTHOR


def test_validate_findings_write_scope_accepts_private_seam() -> None:
    # Any file under [internal-ref] is allowed
    from ztare.common.paths import REPO_ROOT
    seam = REPO_ROOT / "research_areas" / "private" / "seams" / "GP-036_findings_runner_supervisor_convergence_seam.md"
    validate_findings_write_scope(seam)  # should not raise


def test_validate_findings_write_scope_rejects_outside() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        outside = Path(tmpdir) / "not_a_seam.md"
        outside.write_text("x")
        raised = False
        try:
            validate_findings_write_scope(outside)
        except RunnerWriteScopeError:
            raised = True
        assert raised, "seam path outside findings dirs must raise"


def test_validate_findings_write_scope_rejects_src_path() -> None:
    from ztare.common.paths import REPO_ROOT
    inside_repo_wrong_dir = REPO_ROOT / "src" / "ztare" / "validator" / "supervisor_findings_runner.py"
    raised = False
    try:
        validate_findings_write_scope(inside_repo_wrong_dir)
    except RunnerWriteScopeError:
        raised = True
    assert raised, "src/ paths are not findings dirs"


def test_build_findings_context_returns_empty_when_no_refs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        seam = Path(tmpdir) / "GP-999_synthetic_seam.md"
        seam.write_text("No references here, just prose.")
        tiers = build_findings_context(
            seam_path=seam,
            seam_text=seam.read_text(),
            token_budget=DEFAULT_TOKEN_BUDGET,
        )
        # GP-999 is not a real board row, and no seam/artifact refs exist.
        assert tiers == []


def test_build_findings_context_injects_related_seam() -> None:
    # A real seam from the repo referenced by path — the context builder
    # must emit a RELATED_SEAM_EXCERPT tier with the right provenance.
    from ztare.common.paths import REPO_ROOT
    real_related = "GP-031 (internal seam)"
    if not (REPO_ROOT / real_related).exists():
        return  # skip if the referenced file moved
    with tempfile.TemporaryDirectory() as tmpdir:
        seam = Path(tmpdir) / "GP-036_test_seam.md"
        seam_body = f"This seam references {real_related} inline."
        seam.write_text(seam_body)
        tiers = build_findings_context(
            seam_path=seam,
            seam_text=seam_body,
            token_budget=DEFAULT_TOKEN_BUDGET,
        )
        labels = [t.label for t in tiers]
        assert "RELATED_SEAM_EXCERPT" in labels
        related_tier = next(t for t in tiers if t.label == "RELATED_SEAM_EXCERPT")
        assert related_tier.source_path == real_related


def test_build_findings_context_injects_related_spec() -> None:
    # A seam that cites a spec file under research_areas/(private/)?specs/active/
    # must auto-inject a SPEC_EXCERPT tier — this is what makes
    # "debate the spec inside the seam" work without the operator
    # pasting spec excerpts into turn bodies by hand.
    from ztare.common.paths import REPO_ROOT
    real_spec = "GP-036 (internal seam)"
    if not (REPO_ROOT / real_spec).exists():
        return  # skip if the referenced spec moved
    with tempfile.TemporaryDirectory() as tmpdir:
        seam = Path(tmpdir) / "GP-036_test_seam.md"
        seam_body = f"Turn N reopens scope, see {real_spec} for current contract."
        seam.write_text(seam_body)
        tiers = build_findings_context(
            seam_path=seam,
            seam_text=seam_body,
            token_budget=DEFAULT_TOKEN_BUDGET,
        )
        labels = [t.label for t in tiers]
        assert "SPEC_EXCERPT" in labels, f"expected SPEC_EXCERPT in {labels}"
        spec_tier = next(t for t in tiers if t.label == "SPEC_EXCERPT")
        assert spec_tier.source_path == real_spec


def test_format_context_tiers_includes_provenance_headers() -> None:
    from ztare.findings.findings_context import ContextTier
    tiers = [
        ContextTier(
            label="BOARD_ROW",
            source_path="[internal-ref]",
            content="| GP-036 | findings | ... |",
            token_estimate=10,
        )
    ]
    rendered = format_context_tiers(tiers)
    assert "--- BOARD_ROW (source: [internal-ref]) ---" in rendered
    assert "GP-036" in rendered


def test_build_turn_prompt_injects_context_when_seam_path_given() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        seam = Path(tmpdir) / "GP-036_dummy_seam.md"
        seam_body = "Seam body referencing GP-031 (internal seam)"
        seam.write_text(seam_body)
        state = _state_with_turns(())
        prompt = build_turn_prompt(
            seam_text=seam_body,
            agent=SINGLE_CLAUDE_AUTHOR,
            debate_state=state,
            seam_path=seam,
        )
        from ztare.common.paths import REPO_ROOT
        if (REPO_ROOT / "GP-031 (internal seam)").exists():
            assert "--- BEGIN CONTEXT ---" in prompt
            assert "--- END CONTEXT ---" in prompt
        assert f"**{SINGLE_CLAUDE_AUTHOR}**" in prompt


def test_emit_gate_escalation_writes_payload_to_disk() -> None:
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        gate_dir = Path(tmpdir) / "gates" / "pending"
        seam = Path(tmpdir) / "GP-036_dummy_seam.md"
        seam.write_text("dummy seam body")
        gate_file = emit_gate_escalation(
            seam_path=seam,
            stop_reason=RunnerStopReason.COST_BUDGET,
            cycles=(),
            total_cost_usd=1.234,
            notes=("cost budget reached before cycle 3",),
            gate_dir=gate_dir,
        )
        assert gate_file.exists(), "gate file must land on disk"
        assert gate_file.parent == gate_dir
        payload = json.loads(gate_file.read_text(encoding="utf-8"))
        for key in (
            "seam_path",
            "escalation_reason",
            "equivalent_gate_reason",
            "cycle_count",
            "total_cost_usd",
            "notes",
            "timestamp_utc",
            "advisory",
        ):
            assert key in payload, f"missing key: {key}"
        assert payload["escalation_reason"] == RunnerStopReason.COST_BUDGET.value
        assert payload["advisory"] is True
        assert payload["total_cost_usd"] == 1.234


def _seam_with_empty_debate_log(tmpdir: Path) -> Path:
    seam = tmpdir / "GP-000_roundtrip_test_seam.md"
    seam.write_text(
        "# Seam\n\n## Problem\n\nBody.\n\n## Debate Log\n",
        encoding="utf-8",
    )
    return seam


def test_append_turn_single_claude_author_round_trips() -> None:
    """Regression: the _TURN_HEADER regex must accept hyphenated agent
    names like ``Claude-Author`` and ``Claude-Skeptic``. Before the fix,
    the regex stopped at the hyphen, ``parse_debate_log`` returned zero
    turns after the write, and the runner silently re-appended Turn 1 on
    every cycle, burning budget without making progress."""

    with tempfile.TemporaryDirectory() as tmpdir:
        seam = _seam_with_empty_debate_log(Path(tmpdir))
        turn = append_turn(
            seam_path=seam,
            agent=SINGLE_CLAUDE_AUTHOR,
            date="2026-04-15",
            title="Autonomous runner turn",
            body="Author opening position.",
            no_new_load_bearing=False,
        )
        assert turn.index == 1
        assert turn.agent == SINGLE_CLAUDE_AUTHOR
        parsed = parse_debate_log(seam)
        assert len(parsed) == 1, f"expected 1 turn, got {len(parsed)}"
        assert parsed[0].agent == SINGLE_CLAUDE_AUTHOR
        assert parsed[0].index == 1


def test_append_turn_single_claude_skeptic_round_trips() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        seam = _seam_with_empty_debate_log(Path(tmpdir))
        append_turn(
            seam_path=seam,
            agent=SINGLE_CLAUDE_AUTHOR,
            date="2026-04-15",
            title="Opening",
            body="Author body.",
            no_new_load_bearing=False,
        )
        turn2 = append_turn(
            seam_path=seam,
            agent=SINGLE_CLAUDE_SKEPTIC,
            date="2026-04-15",
            title="Counter",
            body="Skeptic body.",
            no_new_load_bearing=False,
        )
        assert turn2.index == 2
        parsed = parse_debate_log(seam)
        assert len(parsed) == 2
        assert parsed[0].agent == SINGLE_CLAUDE_AUTHOR
        assert parsed[1].agent == SINGLE_CLAUDE_SKEPTIC
        assert parsed[0].index == 1
        assert parsed[1].index == 2


def test_append_turn_rejects_unparseable_body_and_rolls_back() -> None:
    """Round-trip safety: if the body contains an h2 header that
    terminates the ## Debate Log section, append_turn must raise and
    leave the file unchanged."""

    with tempfile.TemporaryDirectory() as tmpdir:
        seam = _seam_with_empty_debate_log(Path(tmpdir))
        pre = seam.read_text(encoding="utf-8")
        # An h2 inside the body is not itself the failure; the failure is
        # any body that breaks round-trip. Simulate by patching the regex
        # via a poison agent name the regex can't match.
        try:
            append_turn(
                seam_path=seam,
                agent="Bad\nAgent",  # newline makes header span two lines
                date="2026-04-15",
                title="will fail to parse",
                body="body",
                no_new_load_bearing=False,
            )
        except ValueError:
            post = seam.read_text(encoding="utf-8")
            assert post == pre, "file must be rolled back on round-trip failure"
            return
        raise AssertionError("expected ValueError on unparseable turn")


_TESTS = (
    test_append_turn_single_claude_author_round_trips,
    test_append_turn_single_claude_skeptic_round_trips,
    test_append_turn_rejects_unparseable_body_and_rolls_back,
    test_parse_sentinel_raise_clean_body,
    test_parse_sentinel_hold,
    test_parse_sentinel_missing_defaults_to_hold,
    test_parse_sentinel_uses_last_match_when_repeated,
    test_parse_sentinel_case_insensitive,
    test_parse_sentinel_inline_at_end_of_sentence,
    test_parse_sentinel_inline_in_middle_does_not_lock_in_early,
    test_choose_next_agent_empty_seam_starts_with_claude,
    test_choose_next_agent_alternates_after_claude,
    test_choose_next_agent_alternates_after_gemini,
    test_choose_next_agent_legacy_codex_routes_to_claude,
    test_choose_next_agent_handles_double_claude_turn,
    test_choose_next_agent_returns_none_when_only_operator,
    test_build_turn_prompt_contains_seam_text_and_agent,
    test_build_turn_prompt_reports_correct_turn_count,
    test_runner_sees_real_seam_state,
    test_single_claude_mode_starts_with_author,
    test_single_claude_mode_alternates_author_skeptic,
    test_single_claude_mode_mixed_seam_defaults_to_author_on_tie,
    test_validate_findings_write_scope_accepts_private_seam,
    test_validate_findings_write_scope_rejects_outside,
    test_validate_findings_write_scope_rejects_src_path,
    test_build_findings_context_returns_empty_when_no_refs,
    test_build_findings_context_injects_related_seam,
    test_build_findings_context_injects_related_spec,
    test_format_context_tiers_includes_provenance_headers,
    test_build_turn_prompt_injects_context_when_seam_path_given,
    test_emit_gate_escalation_writes_payload_to_disk,
)


def main() -> int:
    failed = 0
    for test in _TESTS:
        try:
            test()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
        except Exception as exc:  # pragma: no cover - surfaced to operator
            failed += 1
            print(f"ERROR {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\n{len(_TESTS) - failed}/{len(_TESTS)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
