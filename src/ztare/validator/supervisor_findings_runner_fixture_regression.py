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

from src.ztare.validator.supervisor_findings_debate import (
    SENTINEL_NO_NEW_CLAIM,
    DebateState,
    DebateStatus,
    DebateTurn,
    read_debate_state,
)
from src.ztare.validator.supervisor_findings_runner import (
    build_turn_prompt,
    choose_next_agent,
    parse_sentinel_decision,
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
        "load-bearing architectural claims. SENTINEL_DECISION: raise"
    )
    body, raised = parse_sentinel_decision(raw)
    assert raised is True
    assert "SENTINEL_DECISION" not in body
    assert "load-bearing architectural claims." in body


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


_TESTS = (
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
