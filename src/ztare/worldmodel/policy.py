"""Action selection as inversion, priced as composite information yield (GP-250).

The next action is an experiment against the surviving committee, and its value
is a composite — mirroring the loop's information-yield discipline, where no
single scalar carries the verdict:

- identification bits (EIG): entropy of the partition the action induces over
  the committee's predicted next states. Query-by-committee, named plainly.
- compression gain: expected description-length mass eliminated. Killing a
  structurally large survivor buys more than separating same-size variants.
  This is the action-level expectation of the trajectory-level signal in
  `ztare.validator.core.compression_progress`, computed on the same
  `program_size` the synthesizer ranks by.
- context coverage: probing an unwitnessed guard context `(action, step%2,
  step%3)` has value even when the current committee agrees, because the
  synthesizer's hypothesis language distinguishes exactly those contexts. The
  policy explores what the grammar can express, no more.

Weights are pre-registered (identification primary, the other two secondary)
and recorded on the GP-250 seam; changing them is a seam amendment, not a
tuning knob. Typed statuses are unchanged: "probe", "identified",
"underidentified" — pressure stays finite (proportionality), and a live
committee with no reachable signal exits typed instead of grinding.

Known boundary, recorded from the P0' runs: this is 1-step pricing. Laws whose
discriminating context arrives on a future step residue can still be probed
prematurely; the information-ratio (multi-step) objective is the named upgrade
path if BC-1'' shows the composite is not enough.
"""

from __future__ import annotations

from dataclasses import dataclass

from ztare.research_signals import price_experiment
from ztare.worldmodel.grid_dsl import Grid, Program, evaluate, program_size

# Pre-registered composite weights (GP-250 seam, 2026-07-02). Not a tuning knob.
W_EIG = 1.0
W_COMPRESSION = 0.5
W_COVERAGE = 0.5


@dataclass(frozen=True)
class PolicyDecision:
    """status: "probe" (take `action`), "identified", "underidentified"."""
    status: str
    action: "int | None" = None
    score: float = 0.0
    reason: str = ""


def context_key(action: int, step: int) -> tuple:
    """The guard-context signature the seed grammar can distinguish."""
    return (action, step % 2, step % 3)


def select_action(committee: "tuple[Program, ...]", grid: Grid, step: int,
                  action_arity: int, remaining_budget: int,
                  witnessed_contexts: "set[tuple] | None" = None,
                  tried_counts: "dict[int, int] | None" = None) -> PolicyDecision:
    """Choose the next experiment by composite yield over legal actions."""
    if remaining_budget <= 0:
        return PolicyDecision(status="underidentified",
                              reason="budget exhausted with a live committee")
    if len(committee) == 0:
        # No hypothesis yet (empty log or no synthesis run): bootstrap with the
        # least-tried action. An empty committee is not identification.
        tried0 = tried_counts or {}
        a0 = min(range(action_arity), key=lambda a: (tried0.get(a, 0), a))
        return PolicyDecision(status="probe", action=a0, score=0.0,
                              reason="bootstrap: no committee yet")
    if len(committee) == 1:
        return PolicyDecision(status="identified", reason="committee is singleton")

    witnessed = witnessed_contexts or set()

    best_action, best_score, best_parts = None, -1.0, ""
    for a in range(action_arity):
        parts = price_experiment(
            committee,
            predict=lambda prog, _a=a: evaluate(prog, grid, _a, step),
            size_fn=program_size,
            novel_context=context_key(a, step) not in witnessed,
        )
        score = parts.score(W_EIG, W_COMPRESSION, W_COVERAGE)
        if score > best_score:
            best_action, best_score = a, score
            best_parts = (f"eig={parts.identification:.2f} "
                          f"compression={parts.compression_gain:.2f} "
                          f"coverage={parts.novelty:.0f}")

    if best_score > 0.0:
        return PolicyDecision(status="probe", action=best_action, score=best_score,
                              reason=f"composite yield: {best_parts}")

    # No identification signal and no unwitnessed context: reachable agreement
    # is still not equivalence, so exercise the least-tried action a bounded
    # number of times before declaring the frontier closed.
    tried = tried_counts or {}
    least_tried = min(range(action_arity), key=lambda a: (tried.get(a, 0), a))
    if tried.get(least_tried, 0) < max(3, remaining_budget // action_arity):
        return PolicyDecision(status="probe", action=least_tried, score=0.0,
                              reason="frontier fallback: flat yield with live committee")
    return PolicyDecision(status="underidentified",
                          reason="no discriminating action reachable within budget")
