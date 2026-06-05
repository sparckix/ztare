"""Apparatus certificate — never conflate an apparatus bug with a science outcome.

Every false signal this project has chased was an APPARATUS negative read as a SCIENCE "no":
dead REPL (toolchain), dead API key, dead embedder, prompt-not-delivered, crippled agent
(no Bash), env-blind proofState, under-budget timeout, path-doubling verify. A negative has
TWO possible causes — the apparatus is broken/under-powered, OR the science genuinely says no
— and defaulting to the second without ruling out the first is the recurring mistake.

A positive (liveness) control is NECESSARY but NOT SUFFICIENT. The failures fall in three
sub-classes, and a negative is a SCIENCE outcome only if ALL THREE controls pass on that run,
through the same code path:

  • LIVENESS   — a known-TRUE trivial input must succeed (instrument is alive).
  • ADEQUACY   — a known-SOLVABLE, DIFFICULTY-MATCHED case must succeed AT THE SAME BUDGET
                 (instrument is powered enough for this difficulty class). A liveness control
                 can pass while the run is still under-budgeted; only a difficulty-matched
                 control at the same budget rules out "budget-suspect".
  • SOUNDNESS  — a known-FALSE input must be REJECTED (instrument is not false-accepting; the
                 measurement actually exercises the real artifact, not a no-op).

The verdict is therefore THREE-way, never binary:
  POSITIVE             — apparatus certified + result positive.
  ADMISSIBLE_NEGATIVE  — apparatus certified (live+adequate+sound) AND result negative ⇒ a
                         real science "no" / frontier; safe to record + reason from.
  INADMISSIBLE         — apparatus NOT certified ⇒ QUARANTINE; re-test; NEVER record as a
                         science finding. (dead | under-budget | mis-wired)

Substrate-neutral: callers pass control callables for their instrument (Lean, embedder,
grader, retrieval, …). Generalizes substrate_liveness / embedder_liveness into one stamp.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Callable, Optional


class Verdict(str, Enum):
    POSITIVE = "positive"
    ADMISSIBLE_NEGATIVE = "admissible_negative"   # real science no / frontier
    INADMISSIBLE = "inadmissible"                 # apparatus bug — quarantine, re-test


@dataclass
class Certificate:
    live: bool
    adequate: bool
    sound: bool
    live_why: str = ""
    adequate_why: str = ""
    sound_why: str = ""

    @property
    def certified(self) -> bool:
        return self.live and self.adequate and self.sound

    def verdict(self, result_positive: bool) -> Verdict:
        if not self.certified:
            return Verdict.INADMISSIBLE
        return Verdict.POSITIVE if result_positive else Verdict.ADMISSIBLE_NEGATIVE

    def banner(self) -> str:
        if self.certified:
            return "[apparatus] CERTIFIED (live+adequate+sound) — negatives are admissible"
        fails = []
        if not self.live: fails.append(f"NOT-LIVE({self.live_why})")
        if not self.adequate: fails.append(f"UNDER-POWERED({self.adequate_why})")
        if not self.sound: fails.append(f"UNSOUND/MIS-WIRED({self.sound_why})")
        return ("[apparatus] ⚠️ UNCERTIFIED — a negative here is INADMISSIBLE (apparatus bug, "
                "not a science 'no'): " + "; ".join(fails))

    def to_dict(self) -> dict:
        d = asdict(self); d["certified"] = self.certified; return d


def certify(
    *,
    liveness: Callable[[], "tuple[bool, str]"],
    soundness: Callable[[], "tuple[bool, str]"],
    adequacy: Optional[Callable[[], "tuple[bool, str]"]] = None,
) -> Certificate:
    """Run the three controls (each returns (ok, why)). `adequacy` is optional only where a
    difficulty-matched solvable case genuinely cannot be constructed (e.g. an open frontier
    with no known-solvable peer); pass None there and treat the resulting open as
    'localized-open, not certified-wall', NOT as a clean negative. Controls must run through
    the SAME code path as the real measurement, or the certificate is theater."""
    lo, lw = _safe(liveness)
    so, sw = _safe(soundness)
    if adequacy is None:
        ao, aw = lo, "adequacy not asserted (no difficulty-matched peer) — open is 'localized', not a certified wall"
    else:
        ao, aw = _safe(adequacy)
    return Certificate(live=lo, adequate=ao, sound=so,
                       live_why=lw, adequate_why=aw, sound_why=sw)


def _safe(fn) -> "tuple[bool, str]":
    try:
        ok, why = fn()
        return bool(ok), str(why)
    except Exception as e:  # a control that crashes is a failed control (fail-closed)
        return False, f"control raised: {str(e)[:120]}"


def _self_test() -> int:
    fails = []
    c = Certificate(True, True, True)
    if not c.certified or c.verdict(False) != Verdict.ADMISSIBLE_NEGATIVE: fails.append("certified neg ⇒ admissible")
    if c.verdict(True) != Verdict.POSITIVE: fails.append("certified pos ⇒ positive")
    c = Certificate(True, False, True)  # under-powered
    if c.certified or c.verdict(False) != Verdict.INADMISSIBLE: fails.append("under-powered neg ⇒ inadmissible")
    c = certify(liveness=lambda: (True, "ok"), soundness=lambda: (True, "ok"),
                adequacy=lambda: (False, "budget too small"))
    if c.verdict(False) != Verdict.INADMISSIBLE: fails.append("adequacy fail ⇒ inadmissible")
    c = certify(liveness=lambda: (_ for _ in ()).throw(RuntimeError("x")).__next__(),
                soundness=lambda: (True, "ok"))  # liveness crashes
    if c.live: fails.append("crashing control must fail-closed")
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
