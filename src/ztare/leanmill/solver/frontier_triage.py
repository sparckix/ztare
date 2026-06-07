"""Frontier-type triage — pre-attempt classifier: formalization-bound vs discovery-bound.

The solver should spend its (expensive) agentic budget on goals where the MATHEMATICS is known
and only the LEAN ENCODING is missing (formalization-bound). It should NOT burn budget on goals
where the math itself is open (discovery-bound) — those belong to the Research Director, not the
prover. `cube_fubini` showed the human-supplied formalization/discovery tag is unreliable, so this
classifies from the GOAL STRUCTURE itself (reproducible), reusing the two existing classifiers
rather than inventing a taxonomy:
  - `obligation_router.classify` — universal obligation class (Construct/Transfer/Bound/Decompose)
    read off the goal's head connective.
  - `gap_typing.heuristic_gap_type` — PDE/analysis lexical gap-type (AUXILIARY = needs a tailored
    test-object construction; the strongest discovery-bound signal).

NON-IATROGENIC FLOOR (mirrors the calibration floor): the classifier DEFAULTS to ATTEMPT
(formalization_bound) and only emits `discovery_bound` on STRONG, conjunctive evidence — so it can
never wrongly defer a target the solver could have closed. The advisory verdict is always recorded;
the DEFER action is opt-in (the worker only skips on a discovery_bound verdict when
ZTARE_FRONTIER_TRIAGE_DEFER=1), so the default path is parity by construction.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass


@dataclass
class TriageVerdict:
    triage_class: str       # "formalization_bound" | "discovery_bound" | "unknown"
    confidence: str         # "low" | "medium" | "high"
    attempt: bool           # the recommendation (True = run the solver on it)
    obligation: str         # the obligation class (from obligation_router)
    gap_type: str           # the gap-type (from gap_typing)
    rationale: str
    target_strength: str = "unknown"  # M4: "strong_missing" | "elementary" | "unknown" — does the FULL
    #   target likely need machinery ABSENT from Mathlib (steer toward SPECIALIZE-or-retire) vs elementary
    #   lemmas? The generalization of REACH_INVENT (missing-IDENTIFIER) to missing-axiom-STRENGTH. ADVISORY:
    #   default "unknown" (never steers) — the action is opt-in under ZTARE_LEANMILL_TARGET_STRENGTH.

    def to_dict(self) -> dict:
        return asdict(self)


# Advanced-machinery gap-types: when a goal owes one of these AND carries an explicit discovery marker AND
# a construction/bound obligation, the FULL target likely needs structure ABSENT from the proof library
# (an advanced-theory shape) — prefer an honest SPECIALIZE rung over doomed direct escalation.
_STRONG_GAP_TYPES = ("AUXILIARY", "COMMUTATOR", "PROPAGATION", "LIMIT_PASSAGE")


def _target_strength(obligation: str, gap_type: str, has_marker: bool) -> str:
    """STRUCTURAL strength estimate (NON-IATROGENIC: defaults to 'unknown' so it never steers unless the
    conjunctive evidence is STRONG). strong_missing only on {marker AND construction/bound obligation AND
    an advanced-machinery gap-type}; elementary on a recognized obligation over a known lemma family."""
    if has_marker and obligation in ("Construct", "Bound") and gap_type in _STRONG_GAP_TYPES:
        return "strong_missing"
    if not has_marker and (obligation == "Transfer" or (obligation == "Bound"
                                                        and gap_type in ("UNKNOWN", "SOBOLEV", "HOLDER"))):
        return "elementary"
    return "unknown"


# Lexical markers that a goal needs a NEW idea, not just an encoding. Conservative: these only
# tip the verdict to discovery_bound in CONJUNCTION with a construction-shaped obligation.
_DISCOVERY_MARKERS = (
    "conjecture", "open problem", "it is not known", "unknown whether",
    "sharp constant", "optimal constant", "best constant", "extremal",
    "new inequality", "novel bound",
)


def triage(goal_text: str, *, source_hint: str = "") -> TriageVerdict:
    """Classify a goal as formalization-bound (attempt) or discovery-bound (defer).

    `source_hint` may carry the row's free-text description; it is used ONLY to look for explicit
    discovery markers (never to force a class — the human tag is untrusted per cube_fubini)."""
    try:
        from ztare.leanmill.solver.obligation_router import classify
        ob = classify(goal_text or "")
        obligation, gap_type = ob.obligation, ob.gap_type
    except Exception:
        obligation, gap_type = "Transfer", "UNKNOWN"

    hay = f"{goal_text} {source_hint}".lower()
    has_marker = any(m in hay for m in _DISCOVERY_MARKERS)
    ts = _target_strength(obligation, gap_type, has_marker)  # M4 advisory tag (stamped on every verdict)

    # CONSERVATIVE FLOOR (cold-review 2026-06-03): a lexical AUXILIARY/Construct signal ALONE is
    # NOT enough to defer — `∃ carrier, carrier = {0}` is Construct+AUXILIARY by lexical cue yet
    # closes in one line. So EVERY defer now requires an EXPLICIT discovery marker (open-problem /
    # sharp-constant / extremal language). This guarantees we never defer a goal whose only
    # discovery signal is incidental vocabulary.
    # Strong discovery-bound: explicit marker AND a construction obligation with AUXILIARY gap-type
    # (the math object itself must be invented, not just encoded).
    if has_marker and obligation == "Construct" and gap_type == "AUXILIARY":
        return TriageVerdict(
            "discovery_bound", "high", False, obligation, gap_type,
            "explicit open-problem language AND a construction obligation with AUXILIARY gap-type — "
            "owes a tailored test-object construction; defer to the RD.",
            target_strength=ts,
        )
    # Medium discovery-bound: explicit discovery markers in the text AND a non-routine obligation.
    if has_marker and obligation in ("Construct", "Bound"):
        return TriageVerdict(
            "discovery_bound", "medium", False, obligation, gap_type,
            "explicit open-problem / sharp-constant / extremal language alongside a "
            "construction-or-bound obligation — likely discovery-bound; defer.",
            target_strength=ts,
        )
    # AUXILIARY alone (without a construction obligation) is ambiguous — attempt, but flag it.
    if gap_type == "AUXILIARY":
        return TriageVerdict(
            "formalization_bound", "low", True, obligation, gap_type,
            "AUXILIARY gap-type but no construction obligation — likely an encodable lemma "
            "around a test object; attempt, but the gap-type warrants a watchful eye.",
            target_strength=ts,
        )
    # Default: formalization-bound (attempt). A recognized obligation over a known lemma family is
    # exactly what the agentic leaf + premise shelf are for.
    return TriageVerdict(
        "formalization_bound", "medium" if gap_type != "UNKNOWN" else "low", True,
        obligation, gap_type,
        f"{obligation} obligation"
        + (f" / {gap_type} gap-type" if gap_type != "UNKNOWN" else "")
        + " — known-math shape; attempt with the standard pipeline.",
        target_strength=ts,
    )


def defer_enabled() -> bool:
    """The DEFER action is opt-in; default-off → the worker attempts everything (parity)."""
    return os.environ.get("ZTARE_FRONTIER_TRIAGE_DEFER") == "1"


def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # A plain equality/transfer goal → formalization-bound, attempt.
    v = triage("∀ x : ℝ, x + 0 = x")
    ok("transfer_eq_is_formalization_bound", v.triage_class == "formalization_bound" and v.attempt)

    # REGRESSION (cold-review counterexample): a Construct+AUXILIARY goal by LEXICAL cue alone, with
    # NO discovery marker, is trivially closable → MUST attempt (never defer on incidental vocab).
    v = triage("∃ carrier : Set Nat, carrier = {0}")
    ok("construct_auxiliary_no_marker_attempts", v.attempt and v.triage_class == "formalization_bound")
    # WITH an explicit discovery marker, the same Construct+AUXILIARY shape → high-confidence defer.
    v = triage("∃ w, IsBarrier w ∧ carrier w = region",
               source_hint="constructing this barrier is an open problem")
    ok("construct_auxiliary_with_marker_defers", v.triage_class == "discovery_bound"
       and not v.attempt and v.confidence == "high")

    # Explicit open-problem language on a bound → discovery-bound (medium).
    v = triage("‖f‖ ≤ C * ‖f‖", source_hint="the sharp constant here is an open problem")
    ok("open_problem_marker_defers", v.triage_class == "discovery_bound" and not v.attempt)

    # An inequality with a known family (no markers) → formalization-bound, attempt.
    v = triage("∀ x y : ℝ, x * y ≤ (x^2 + y^2) / 2")
    ok("plain_bound_is_formalization_bound", v.attempt)

    # NON-IATROGENIC FLOOR: when classification fails / is empty, default to ATTEMPT (never defer).
    v = triage("")
    ok("empty_goal_defaults_to_attempt", v.attempt)

    # M4 target_strength (advisory steer): the strong-missing conjunction (marker + Construct + AUXILIARY)
    # tags strong_missing; a plain transfer goal does NOT; the non-iatrogenic default is 'unknown'.
    v = triage("∃ w, IsBarrier w ∧ carrier w = region",
               source_hint="constructing this barrier is an open problem")
    ok("target_strength_strong_missing_on_conjunction", v.target_strength == "strong_missing")
    ok("target_strength_not_strong_on_plain_eq", triage("∀ x : ℝ, x + 0 = x").target_strength != "strong_missing")
    # Non-iatrogenic safety: an empty/unclassifiable goal must NEVER tag strong_missing (the only tag that
    # steers); it may be elementary/unknown (both = no steer, attempt normally).
    ok("target_strength_empty_never_strong_missing", triage("").target_strength != "strong_missing")

    # defer is opt-in / default-off → parity.
    import os as _os
    saved = _os.environ.pop("ZTARE_FRONTIER_TRIAGE_DEFER", None)
    ok("defer_default_off", defer_enabled() is False)
    _os.environ["ZTARE_FRONTIER_TRIAGE_DEFER"] = "1"
    ok("defer_opt_in", defer_enabled() is True)
    if saved is None:
        _os.environ.pop("ZTARE_FRONTIER_TRIAGE_DEFER", None)
    else:
        _os.environ["ZTARE_FRONTIER_TRIAGE_DEFER"] = saved

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
