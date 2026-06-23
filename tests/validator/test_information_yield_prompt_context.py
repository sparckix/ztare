from ztare.validator.core.information_yield import (
    LoopControlAction,
    ThesisControlMode,
    render_loop_control_prompt_context,
    select_thesis_control_mode,
)


def test_loop_control_prompt_context_is_empty_for_continue() -> None:
    assert (
        render_loop_control_prompt_context(
            pending_action=LoopControlAction.CONTINUE,
            rationale="Latest iteration improved score.",
            stagnant_window=0,
        )
        == ""
    )


def test_loop_control_prompt_context_surfaces_pivot_reason() -> None:
    rendered = render_loop_control_prompt_context(
        pending_action=LoopControlAction.PIVOT_REQUIRED,
        rationale="No new evidence across the pivot window; the same weakest point keeps repeating.",
        stagnant_window=3,
    )

    assert "LOOP CONTROL SIGNAL" in rendered
    assert "pending_action: PIVOT_REQUIRED" in rendered
    assert "thesis_control_mode: ROTATE_ORTHOGONAL_THESIS" in rendered
    assert "stagnant_window: 3" in rendered
    assert "same weakest point keeps repeating" in rendered
    assert "name the new mechanism class" in rendered


def test_loop_control_prompt_context_surfaces_underidentified_boundary() -> None:
    rendered = render_loop_control_prompt_context(
        pending_action=LoopControlAction.UNDERIDENTIFIED,
        rationale="Bounded-discriminator run has produced a catastrophic streak.",
        stagnant_window=5,
    )

    assert "evidence-boundary result" in rendered
    assert "thesis_control_mode: NARROW_EVIDENCE_BOUNDARY" in rendered
    assert "what measurement would make it decidable" in rendered


def test_thesis_control_mode_maps_refresh_to_transfer() -> None:
    assert (
        select_thesis_control_mode(
            pending_action=LoopControlAction.REFRESH_SPECIALISTS,
            rationale="Information yield is low; refresh specialists before continuing.",
        )
        == ThesisControlMode.TRANSFER_MECHANISM
    )


def test_thesis_control_mode_maps_crash_pivot_to_invert_or_kill() -> None:
    assert (
        select_thesis_control_mode(
            pending_action=LoopControlAction.PIVOT_REQUIRED,
            rationale="Recent iterations are crash-only or R1 failures with no new evidence.",
        )
        == ThesisControlMode.INVERT_OR_KILL_THESIS
    )
