"""Apparatus-vs-math failure classifier — the convergent-eigenquestion primitive (gemini API + codex
subscription independently surfaced it, 2026-06-05): tag EVERY solver non-closure as

  APPARATUS  — the failure is a resource / gating / toolchain artifact (budget exhausted, a capability
               gated off, a lake/scope/toolchain error). It says NOTHING about the mathematics; the
               correct response is re-run with the gate on / more budget, NOT "this is math-hard".
  MATH       — a genuine kernel-verified dead-end (unsolved goals / tactic failed / type mismatch):
               the leaf could not close it on the merits.

This MECHANIZES the standing discipline that I keep dropping by hand ("a negative is inadmissible
without calibration"; "don't launder an apparatus limit into a math-negative"). It REUSES the existing
solver error parser `proof_state.proof_state_signal` (no new parser) + the apparatus/genuine-gap
signature classes that `residual_to_lever` already encodes — it does not duplicate either."""
from __future__ import annotations

from ztare.leanmill.solver.proof_state import proof_state_signal

# proof_state.error_class → apparatus vs math. Toolchain/scope/transient = apparatus; the goal-level
# failures = a genuine math dead-end. (Mirrors residual_to_lever._APPARATUS_SIG / _GENUINE_GAP_SIG.)
_APPARATUS_CLASSES = frozenset({"unknown_identifier", "timeout", "other_error"})
_MATH_CLASSES = frozenset({"unsolved_goals", "tactic_failed", "type_mismatch"})
# Search-controller stop reasons that are APPARATUS (the run was cut off, not refuted).
_APPARATUS_STOP_CUES = (
    "move_budget_units_exhausted", "max_moves", "wallclock", "budget", "timed out", "timeout",
    "lake not on path", "lake env lean timed out", "exhausted",
)


def classify_failure(*, error_tail: str = "", returncode: "int | None" = None,
                     stop_reason: str = "", conjecture_enabled: "bool | None" = None,
                     iso_route_enabled: "bool | None" = None,
                     governance_rejections: int = 0) -> dict:
    """Returns {class: 'apparatus'|'math'|'unknown'|'cheat_caught', error_class, reason}. Order matters: a
    budget/timeout stop, or a gap with NO decompose path enabled at all, is apparatus REGARDLESS of the error
    text (the run never got the chance to fail on the merits). `governance_rejections` = this run's
    close-attempts governance did NOT ratify; when >0 it is the DOMINANT story (the leaf kept trying to launder,
    governance kept refusing) — surfacing it stops the generic `other_error`/budget summary from OBSCURING the
    anti-laundering gate."""
    import os as _os
    sl = proof_state_signal(returncode, error_tail or "")
    ec = sl.get("error_class", "other_error")
    sr = (stop_reason or "").lower()
    # CORRECTED 2026-06-12: "recursion never ran" requires NO decompose path. The agent-planner
    # `route_and_solve` (ZTARE_LEANMILL_ISO_ROUTE, DEFAULT-ON) recurses + composite-ratifies REGARDLESS of the
    # legacy `governed_dag_search` MOVE_CONJECTURE (ZTARE_CONJECTURE_DECOMPOSE, default-off). The old branch
    # branded EVERY gap apparatus whenever CONJECTURE_DECOMPOSE was off — false once route_and_solve went
    # default-on (it WAS recursing). Infer iso_route from the env when the caller does not pass it.
    if iso_route_enabled is None:
        iso_route_enabled = _os.environ.get("ZTARE_LEANMILL_ISO_ROUTE", "1") != "0"
    if governance_rejections > 0:
        # the anti-laundering gate FIRED (possibly several times) during the search; even if the run then hit budget, the
        # headline is "governance blocked N laundered/non-assembling closures", NOT "toolchain/other_error".
        return {"class": "cheat_caught", "error_class": "governance_blocked_closes",
                "reason": f"governance did NOT ratify {governance_rejections} close-attempt(s) this run "
                          f"(governance refused laundered/non-assembling closures); the non-closure is HONEST, "
                          f"not a toolchain error"}
    if any(c in sr for c in _APPARATUS_STOP_CUES):
        return {"class": "apparatus", "error_class": ec,
                "reason": f"controller stop = {stop_reason!r} (budget/timeout cut-off, not a math refutation)"}
    if conjecture_enabled is False and iso_route_enabled is False:
        return {"class": "apparatus", "error_class": ec,
                "reason": "NO decompose path enabled (ISO_ROUTE off AND CONJECTURE_DECOMPOSE off) — recursion "
                          "never ran; the gap is apparatus, not a math dead-end"}
    if ec == "parse_error":
        # the leaf produced syntactically invalid Lean: NOT a toolchain artifact (apparatus would launder
        # it as "re-run with more budget/gate") and NOT a confirmed math dead-end (math would over-claim
        # the target is hard). It is a leaf-output-quality miss → re-prompt; honestly `unknown`.
        return {"class": "unknown", "error_class": ec,
                "reason": "leaf produced syntactically invalid Lean (re-prompt; not toolchain, not a math dead-end)"}
    if ec in _APPARATUS_CLASSES:
        return {"class": "apparatus", "error_class": ec, "reason": f"toolchain/scope/transient error ({ec})"}
    if ec in _MATH_CLASSES:
        return {"class": "math", "error_class": ec, "reason": f"genuine kernel dead-end ({ec})"}
    return {"class": "unknown", "error_class": ec, "reason": "unclassified failure"}


def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # budget/timeout stop ⇒ apparatus (even with a math-looking error)
    ok("budget stop → apparatus",
       classify_failure(error_tail="unsolved goals\n⊢ P", stop_reason="move_budget_units_exhausted")["class"] == "apparatus")
    # NO decompose path (BOTH off) ⇒ apparatus (recursion never ran)
    ok("both decompose paths off → apparatus",
       classify_failure(error_tail="unsolved goals", conjecture_enabled=False, iso_route_enabled=False)["class"] == "apparatus")
    # conjecture off BUT iso_route ON (the default) ⇒ recursion DID run ⇒ classify on the merits (math), NOT apparatus
    ok("conjecture off + iso_route on → classified on merits (math), not no-recursion apparatus",
       classify_failure(error_tail="unsolved goals", conjecture_enabled=False, iso_route_enabled=True)["class"] == "math")
    # toolchain/scope error ⇒ apparatus
    ok("unknown identifier → apparatus",
       classify_failure(error_tail="error: unknown identifier 'foo'")["class"] == "apparatus")
    # genuine math dead-end ⇒ math
    ok("unsolved goals → math",
       classify_failure(error_tail="unsolved goals\n⊢ x = y")["class"] == "math")
    ok("tactic failed → math",
       classify_failure(error_tail="error: linarith failed to find a contradiction")["class"] in ("math", "apparatus")
       and classify_failure(error_tail="error: linarith failed to find a contradiction")["error_class"] == "tactic_failed")
    # a real budget message takes precedence over the math error text
    ok("budget cue beats math text",
       classify_failure(error_tail="unsolved goals", stop_reason="lake env lean timed out")["class"] == "apparatus")
    # parse error (malformed leaf Lean) ⇒ unknown (re-prompt), NOT apparatus — the P1-RCA fix.
    _pe = classify_failure(error_tail="Probe.lean:6:0: error: unexpected identifier; expected command")
    ok("parse error → unknown (not apparatus)", _pe["class"] == "unknown" and _pe["error_class"] == "parse_error")
    # benign 'has local changes' warning must NOT mask a real unsolved-goals classification.
    ok("benign warning does not mask unsolved_goals",
       classify_failure(error_tail="warning: mathlib: repository '/x' has local changes\nunsolved goals\n⊢ x=y")["class"] == "math")
    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
