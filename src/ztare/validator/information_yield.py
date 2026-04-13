from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LoopControlAction(str, Enum):
    CONTINUE = "CONTINUE"
    REFRESH_SPECIALISTS = "REFRESH_SPECIALISTS"
    PIVOT_REQUIRED = "PIVOT_REQUIRED"
    UNDERIDENTIFIED = "UNDERIDENTIFIED"


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
        """A genuine reframing that also changed the committee topology is structural novelty."""
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
) -> InformationYieldDecision:
    """Evaluate information yield and return the next loop control action.

    underidentified_after: minimum catastrophic-streak length before the
    UNDERIDENTIFIED exit fires in bounded_discriminator mode. Defaults to
    pivot_after (preserving legacy behavior). Set higher (e.g. 50 or 100)
    for pre-registered experiments that require sustained starvation before
    the UNDERIDENTIFIED conclusion is valid — otherwise the exit fires before
    the pivot has had any chance to produce structural moves.
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

    # R4: R1 mismatch is non-informative — treat identically to runtime_failure
    if latest.is_r1_failure():
        flat_tail = _collect_flat_tail(history)
        stagnant_window = len(flat_tail)
        if stagnant_window >= 2 and all(
            (item.runtime_failure or item.is_r1_failure()) for item in flat_tail[-2:]
        ):
            return InformationYieldDecision(
                action=LoopControlAction.PIVOT_REQUIRED,
                stagnant_window=stagnant_window,
                rationale="Recent iterations are R1 declaration failures or crashes with no new evidence.",
            )
        return InformationYieldDecision(
            action=LoopControlAction.REFRESH_SPECIALISTS,
            stagnant_window=stagnant_window,
            rationale="Latest iteration failed R1 declaration validation; refresh before continuing.",
        )

    if latest.score_improved:
        return InformationYieldDecision(
            action=LoopControlAction.CONTINUE,
            stagnant_window=0,
            rationale="Latest iteration improved score, so search should continue.",
        )
    if latest.has_novelty():
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

    flat_tail = _collect_flat_tail(history)
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

    if stagnant_window >= 2 and all(
        (item.runtime_failure or item.is_r1_failure()) for item in flat_tail[-2:]
    ):
        return InformationYieldDecision(
            action=LoopControlAction.PIVOT_REQUIRED,
            stagnant_window=stagnant_window,
            rationale="Recent iterations are crash-only or R1 failures with no new evidence.",
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


def _collect_flat_tail(history: list[IterationSignal]) -> list[IterationSignal]:
    tail: list[IterationSignal] = []
    for item in reversed(history):
        if item.score_improved or item.has_novelty():
            break
        tail.append(item)
    tail.reverse()
    return tail
