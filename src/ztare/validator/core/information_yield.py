from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LoopControlAction(str, Enum):
    CONTINUE = "CONTINUE"
    REFRESH_SPECIALISTS = "REFRESH_SPECIALISTS"
    PIVOT_REQUIRED = "PIVOT_REQUIRED"
    UNDERIDENTIFIED = "UNDERIDENTIFIED"


class ThesisControlMode(str, Enum):
    EXPLOIT_CURRENT_THESIS = "EXPLOIT_CURRENT_THESIS"
    TRANSFER_MECHANISM = "TRANSFER_MECHANISM"
    ROTATE_ORTHOGONAL_THESIS = "ROTATE_ORTHOGONAL_THESIS"
    INVERT_OR_KILL_THESIS = "INVERT_OR_KILL_THESIS"
    NARROW_EVIDENCE_BOUNDARY = "NARROW_EVIDENCE_BOUNDARY"


@dataclass(frozen=True)
class IterationSignal:
    iteration_index: int
    score: int
    weakest_point: str
    score_improved: bool = False
    runtime_failure: bool = False
    catastrophic_failure: bool = False
    novel_attack_ids: tuple[str, ...] = field(default_factory=tuple)
    novel_hinge_ids: tuple[str, ...] = field(default_factory=tuple)
    novel_primitive_ids: tuple[str, ...] = field(default_factory=tuple)
    verified_axioms_added: int = 0
    falsification_mode: str = ""
    # R4: runner-contract signals consumed by yield evaluation
    mutation_r1_mismatch: bool = False          # True when R1 declaration validation failed
    claim_delta_type: str = ""                  # "NARROWING" | "WIDENING" | "REFRAMING" | ""
    committee_digest: str = ""                  # digest of this iteration's committee instantiation
    prior_committee_digest: str = ""            # digest of the previous iteration's committee
    # Task 12 / Gemini Inversion #3: weakest-link class label (runtime regex).
    # Used by evaluate_information_yield when class_novelty_mode=True to treat
    # a class-not-seen-before-in-session as novelty (champion persistence profile:
    # 28 iters / 10 distinct classes is the high-score signature).
    weakest_class: str = ""

    def has_novelty(self) -> bool:
        # GP-004: catastrophic failures should not reset stagnation just because
        # they emitted new residue; they are still dead-end iterations.
        if self.catastrophic_failure:
            return False
        return bool(
            self.novel_attack_ids
            or self.novel_hinge_ids
            or self.novel_primitive_ids
            or self.verified_axioms_added > 0
            or self._is_reframing_with_new_committee()
        )

    def _is_reframing_with_new_committee(self) -> bool:
        """A genuine reframing that also changed the committee topology is structural novelty.

        Note: this is a necessary but not sufficient condition for resetting stagnation.
        evaluate_information_yield throttles the credit so it fires at most once between
        score improvements — preventing dynamic-mode committee rotation from suppressing
        stagnation indefinitely. Science/math runs (--dynamic not set) always return False
        because committee_digest is "" in non-dynamic mode.
        """
        return (
            self.claim_delta_type == "REFRAMING"
            and bool(self.committee_digest)
            and bool(self.prior_committee_digest)
            and self.committee_digest != self.prior_committee_digest
        )

    def is_r1_failure(self) -> bool:
        """R1 declaration mismatch is treated as a non-informative iteration, like a runtime failure."""
        return self.mutation_r1_mismatch


@dataclass(frozen=True)
class InformationYieldDecision:
    action: LoopControlAction
    stagnant_window: int
    rationale: str


def select_thesis_control_mode(
    *,
    pending_action: LoopControlAction | str,
    rationale: str | None = None,
) -> ThesisControlMode:
    """Map the loop-control decision to the mutation posture owed next."""
    action = (
        pending_action.value
        if isinstance(pending_action, LoopControlAction)
        else str(pending_action or "").strip()
    )
    reason = (rationale or "").lower()
    if action == LoopControlAction.REFRESH_SPECIALISTS.value:
        return ThesisControlMode.TRANSFER_MECHANISM
    if action == LoopControlAction.UNDERIDENTIFIED.value:
        return ThesisControlMode.NARROW_EVIDENCE_BOUNDARY
    if action == LoopControlAction.PIVOT_REQUIRED.value:
        if any(term in reason for term in ("crash", "r1", "declaration", "runtime")):
            return ThesisControlMode.INVERT_OR_KILL_THESIS
        return ThesisControlMode.ROTATE_ORTHOGONAL_THESIS
    return ThesisControlMode.EXPLOIT_CURRENT_THESIS


def render_loop_control_prompt_context(
    *,
    pending_action: LoopControlAction | str,
    rationale: str | None,
    stagnant_window: int | None = None,
) -> str:
    """Render the previous iteration's loop-control decision for the mutator.

    The evaluator already records this decision in telemetry. The mutator also
    needs the reason when the next proposal is being written; otherwise a pivot
    or specialist refresh can look like generic prompt flavor instead of a
    measured response to a specific low-yield pattern.
    """
    action = (
        pending_action.value
        if isinstance(pending_action, LoopControlAction)
        else str(pending_action or "").strip()
    )
    reason = (rationale or "").strip()
    if not action or action == LoopControlAction.CONTINUE.value:
        return ""

    thesis_control_mode = select_thesis_control_mode(
        pending_action=pending_action,
        rationale=rationale,
    )
    lines = [
        "### LOOP CONTROL SIGNAL (from the previous iteration)",
        f"- pending_action: {action}",
        f"- thesis_control_mode: {thesis_control_mode.value}",
    ]
    if stagnant_window is not None:
        lines.append(f"- stagnant_window: {int(stagnant_window)}")
    if reason:
        lines.append(f"- reason: {reason}")
    lines.extend([
        "",
        "Required response:",
        "- Declare the same thesis_control_mode in the R1 mutation declaration when that contract is active.",
        "- Address this reason directly in the next thesis.",
        "- Change the mechanism, evidence boundary, or evaluator-facing discriminator; do not only rephrase the prior proposal.",
    ])
    if action == LoopControlAction.REFRESH_SPECIALISTS.value:
        lines.append(
            "- Treat this as low-yield search: use a different review angle or primitive family before continuing."
        )
    elif action == LoopControlAction.PIVOT_REQUIRED.value:
        lines.append(
            "- Treat this as a pivot requirement: leave the repeated local basin and name the new mechanism class."
        )
    elif action == LoopControlAction.UNDERIDENTIFIED.value:
        lines.append(
            "- Treat this as an evidence-boundary result: narrow the claim or specify what measurement would make it decidable."
        )
    return "\n".join(lines) + "\n"


def apply_latent_motion_veto(
    decision: InformationYieldDecision,
    *,
    records_considered: int,
    mean_max_set_distance: float | None,
    threshold: float,
    min_records: int = 3,
) -> InformationYieldDecision:
    """Block REFRESH_SPECIALISTS when recent latent motion is still high.

    GP-034 is intentionally asymmetric in slice 1: latent motion is a
    veto on disruptive refresh, not a replacement for the scalar yield
    channel and not a veto on pivot / underidentification.
    """

    if decision.action != LoopControlAction.REFRESH_SPECIALISTS:
        return decision
    if mean_max_set_distance is None or records_considered < min_records:
        return decision
    if mean_max_set_distance < threshold:
        return decision
    return InformationYieldDecision(
        action=LoopControlAction.CONTINUE,
        stagnant_window=decision.stagnant_window,
        rationale=(
            f"{decision.rationale} GP-034 veto: recent latent-distance window "
            f"still shows structural movement "
            f"(mean_max_set_distance={mean_max_set_distance:.3f} >= {threshold:.3f})."
        ),
    )


def evaluate_information_yield(
    history: list[IterationSignal],
    *,
    refresh_after: int = 2,
    pivot_after: int = 3,
    underidentified_after: int | None = None,
    class_novelty_mode: bool = False,
) -> InformationYieldDecision:
    """Evaluate information yield and return the next loop control action.

    underidentified_after: minimum catastrophic-streak length before the
    UNDERIDENTIFIED exit fires in bounded_discriminator mode. Defaults to
    pivot_after (preserving legacy behavior). Set higher (e.g. 50 or 100)
    for pre-registered experiments that require sustained starvation before
    the UNDERIDENTIFIED conclusion is valid — otherwise the exit fires before
    the pivot has had any chance to produce structural moves.

    class_novelty_mode (Task 12 / Gemini Inversion #3): when True, treat an
    iteration whose weakest_class has never been seen before in the session
    as novelty (resets stagnation). Mining data (GP-148 champion persistence
    profile) shows high-score groups traverse ~10 distinct weakest-link
    classes over ~28 iters; score-only stagnation prematurely kills the
    class-cycling behavior that produces champions. Default False preserves
    legacy behavior.
    """
    if underidentified_after is None:
        underidentified_after = pivot_after
    if not history:
        return InformationYieldDecision(
            action=LoopControlAction.CONTINUE,
            stagnant_window=0,
            rationale="No iteration history yet.",
        )

    latest = history[-1]

    # Runner/interface failures are outside the scientific version space.
    # They cannot accumulate search stagnation or authorize semantic pivots.
    if latest.is_r1_failure() or latest.runtime_failure:
        kind = "R1 declaration" if latest.is_r1_failure() else "runtime"
        return InformationYieldDecision(
            action=LoopControlAction.CONTINUE,
            stagnant_window=0,
            rationale=(
                f"Latest iteration had a {kind} failure; excluded from "
                "search-control evidence and routed to interface diagnostics."
            ),
        )

    if latest.score_improved:
        return InformationYieldDecision(
            action=LoopControlAction.CONTINUE,
            stagnant_window=0,
            rationale="Latest iteration improved score, so search should continue.",
        )
    if class_novelty_mode and latest.weakest_class:
        prior_classes = {
            item.weakest_class
            for item in history[:-1]
            if item.weakest_class and not item.runtime_failure and not item.is_r1_failure()
        }
        if latest.weakest_class not in prior_classes:
            return InformationYieldDecision(
                action=LoopControlAction.CONTINUE,
                stagnant_window=0,
                rationale=(
                    f"Class-novelty mode: weakest_class='{latest.weakest_class}' is new "
                    f"this session ({len(prior_classes)} classes seen prior). "
                    "Champion-profile persistence preserved."
                ),
            )
    if latest.has_novelty():
        # Throttle committee-rotation credit: grant at most once between score
        # improvements. If the only novelty is a REFRAMING+new-committee AND the
        # prior non-improving iteration was also committee-only, this is dynamic-mode
        # rotation noise — fall through to flat-tail stagnation accumulation instead.
        _only_committee_novelty = (
            latest._is_reframing_with_new_committee()
            and not latest.novel_attack_ids
            and not latest.novel_hinge_ids
            and not latest.novel_primitive_ids
            and latest.verified_axioms_added == 0
        )
        if _only_committee_novelty and len(history) >= 2:
            _prior = history[-2]
            _prior_is_committee_noise = (
                _prior._is_reframing_with_new_committee()
                and not _prior.score_improved
                and not _prior.novel_attack_ids
                and not _prior.novel_hinge_ids
                and not _prior.novel_primitive_ids
                and _prior.verified_axioms_added == 0
            )
            if not _prior_is_committee_noise:
                return InformationYieldDecision(
                    action=LoopControlAction.CONTINUE,
                    stagnant_window=0,
                    rationale="Latest iteration produced structural reframing with new committee topology.",
                )
            # else: prior was also committee-only without improvement — fall through
        else:
            novelty_reason = (
                "structural reframing with new committee topology"
                if latest._is_reframing_with_new_committee()
                else "new attack, hinge, primitive, or axiom evidence"
            )
            return InformationYieldDecision(
                action=LoopControlAction.CONTINUE,
                stagnant_window=0,
                rationale=f"Latest iteration produced {novelty_reason}.",
            )

    flat_tail = _collect_flat_tail(history, class_novelty_mode=class_novelty_mode)
    stagnant_window = len(flat_tail)

    latest_falsification_mode = (latest.falsification_mode or "numerical_proof").strip().lower()
    if (
        latest_falsification_mode == "bounded_discriminator"
        and stagnant_window >= underidentified_after
        and len(flat_tail) >= underidentified_after
        and all(
            item.catastrophic_failure
            and not item.runtime_failure
            and not item.is_r1_failure()
            for item in flat_tail[-underidentified_after:]
        )
    ):
        return InformationYieldDecision(
            action=LoopControlAction.UNDERIDENTIFIED,
            stagnant_window=stagnant_window,
            rationale=(
                "Bounded-discriminator run has produced a catastrophic streak. Possible causes: "
                "(1) evidence boundary is insufficient for any discriminative claim now or in future, "
                "(2) thesis relies on latent variables with no measurement protocol (GP-006 gap), "
                "(3) thesis makes valid forward predictions but current evidence cannot yet resolve them "
                "— in which case this is a legitimate research outcome, not a runner failure. "
                "Operator must distinguish between these before deciding next action."
            ),
        )

    weakest_points = {item.weakest_point for item in flat_tail}
    if stagnant_window >= pivot_after and len(weakest_points) == 1:
        return InformationYieldDecision(
            action=LoopControlAction.PIVOT_REQUIRED,
            stagnant_window=stagnant_window,
            rationale="No new evidence across the pivot window; the same weakest point keeps repeating.",
        )

    if stagnant_window >= refresh_after:
        return InformationYieldDecision(
            action=LoopControlAction.REFRESH_SPECIALISTS,
            stagnant_window=stagnant_window,
            rationale="Information yield is low; refresh specialists before attempting a broader pivot.",
        )

    return InformationYieldDecision(
        action=LoopControlAction.CONTINUE,
        stagnant_window=stagnant_window,
        rationale="Low-yield window is still below intervention thresholds.",
    )


def _collect_flat_tail(
    history: list[IterationSignal],
    *,
    class_novelty_mode: bool = False,
) -> list[IterationSignal]:
    """Collect consecutive non-improving, non-substantively-novel iterations.

    A REFRAMING+new-committee iteration acts as a grace boundary (stops collection)
    only when it was the FIRST such occurrence after a score improvement — i.e., when
    its preceding item was a score improvement or was not itself committee-only noise.
    All subsequent committee-rotation iterations (same pattern, no improvement)
    accumulate as stagnation. This prevents dynamic-mode committee rotation from
    suppressing stagnation indefinitely in qualitative projects.
    """
    tail: list[IterationSignal] = []
    for idx, item in enumerate(reversed(history)):
        hist_idx = len(history) - 1 - idx  # forward index in history

        if item.score_improved:
            break

        # Hard novelty: genuine new information always stops accumulation.
        # Catastrophic failures are excluded from novelty (per has_novelty logic).
        if not item.catastrophic_failure and (
            item.novel_attack_ids
            or item.novel_hinge_ids
            or item.novel_primitive_ids
            or item.verified_axioms_added > 0
        ):
            break

        # Class-novelty grace boundary: if class_novelty_mode is on and this item
        # introduces a weakest_class not seen in earlier history, treat as novelty
        # and stop flat-tail accumulation at this boundary. Use forward index so
        # "earlier" means strictly before this iteration's position in history.
        if (
            class_novelty_mode
            and not item.catastrophic_failure
            and item.weakest_class
        ):
            earlier_classes = {
                h.weakest_class
                for h in history[:hist_idx]
                if h.weakest_class and not h.runtime_failure and not h.is_r1_failure()
            }
            if item.weakest_class not in earlier_classes:
                break

        # Committee-only reframing: grace boundary only when the prior item was an
        # improvement or was not itself committee-only noise. If the prior was ALSO
        # committee-only non-improving, this iteration is stagnation — include it.
        if item._is_reframing_with_new_committee() and not item.catastrophic_failure:
            _prior = history[hist_idx - 1] if hist_idx > 0 else None
            _prior_is_committee_noise = (
                _prior is not None
                and _prior._is_reframing_with_new_committee()
                and not _prior.score_improved
                and not _prior.novel_attack_ids
                and not _prior.novel_hinge_ids
                and not _prior.novel_primitive_ids
                and _prior.verified_axioms_added == 0
            )
            if not _prior_is_committee_noise:
                break  # grace boundary — don't include this item in the tail

        tail.append(item)

    tail.reverse()
    return tail
