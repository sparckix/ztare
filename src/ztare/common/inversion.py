"""The shared INVERSION contract — the Popper "invert" leg, made explicit so BOTH substrates instantiate
ONE interface instead of two ad-hoc connectors (2026-06-06).

Why this exists: `validator/inverter_agent.py` (autoresearch champion-thesis falsifier) and the leanmill
FALSIFY move are the SAME move on different substrates — the Popper inversion:

    invert(claim)      Mode-1 / Munger : construct the counter-hypothesis (¬G / the opposite frame).
    specify(counter)   Mode-2 / Popper : a CONCRETE, EXECUTABLE test with pre-committed pass/fail.
    adjudicate(test)   an EXOGENOUS arbiter decides — NEVER narrative.

The inverter_agent's own creed is "a doubt without a test is narrative skepticism (harmful); a test
without a doubt is busywork." That discipline is enforced HERE, once, in `run_inversion`, so every
substrate inherits it. The substrate differences live in the implementations, not the contract:

  * Lean (LeanFalsifier, leanmill): the counter-hypothesis is ¬G; the test is a candidate ¬G proof; the
    arbiter is the KERNEL (compile + #print axioms + the anti-laundering organs). Adjudication is
    SYNCHRONOUS — the kernel decides instantly, and `falsified` is a hard bool.
  * Autoresearch (ThesisInverter, validator/inverter_agent): the counter-hypothesis is a Munger
    inversion of a champion thesis; the test is a Popper experiment with pass/fail criteria; the arbiter
    is the empirical test harness, which runs LATER. Adjudication is DEFERRED — `run_inversion` returns a
    Verdict with `deferred=True` and the queued tests, and the harness fills in `falsified` when it runs.

This module has NO substrate imports (no leanmill, no validator) so both sides can depend on it without a
cycle. It is the algorithm-level realization of the cognitive-gym Invert leg (common/cognitive_gym.py),
which already registers substrate connectors; an Inverter is what a producer connector dispatches to.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass
class CounterHypothesis:
    """Mode-1 (Munger): the constructed opposite of the claim. For Lean, `statement` is the closed
    Prop ¬G; for a thesis, a one-sentence inversion ("the metric goes DOWN under config X")."""
    statement: str
    rationale: str = ""


@dataclass
class FalsificationTest:
    """Mode-2 (Popper): a CONCRETE, EXECUTABLE test of the counter-hypothesis, with pre-committed
    pass/fail. `candidate` is the executable artifact (a candidate ¬G proof; or a test procedure).
    A FalsificationTest with an empty `candidate` is NOT a test — it is narrative skepticism, and
    `run_inversion` refuses it (no doubt without a test)."""
    counter: CounterHypothesis
    candidate: str = ""
    pass_when: str = ""     # if this holds, the original claim STANDS (the counter-hypothesis failed)
    fail_when: str = ""     # if this holds, the original claim is KILLED (the counter-hypothesis won)
    meta: dict = field(default_factory=dict)

    @property
    def is_executable(self) -> bool:
        return bool((self.candidate or "").strip())


@dataclass
class Verdict:
    """The adjudication outcome. `falsified`:
        True   — the claim was KILLED (an exogenous arbiter confirmed the counter-hypothesis).
        False  — the claim STANDS / the inversion did not refute it.
        None   — UNDECIDED: either the test is deferred (`deferred=True`, runs later) or the proposal was
                 narrative-only (no executable test) — never read None as "stands" (calibration discipline:
                 a null is inadmissible without the arbiter actually firing)."""
    falsified: Optional[bool]
    arbiter: str = ""        # what decided: "lean_kernel" | "test_harness" | "none"
    witness: str = ""        # the kernel-checked ¬G proof, or the failing measurement
    detail: str = ""
    deferred: bool = False   # the arbiter has not run yet (async substrate); `falsified` will be filled later
    meta: dict = field(default_factory=dict)


@runtime_checkable
class Inverter(Protocol):
    """The Popper inversion contract. A substrate implements these three; `run_inversion` sequences them
    and enforces the shared discipline. Each is a PROPOSER step except `adjudicate`, which is the only
    place a verdict is minted — and it must defer to an exogenous arbiter (kernel / test harness),
    never self-certify."""

    def invert(self, claim: str, context: dict) -> CounterHypothesis: ...

    def specify(self, counter: CounterHypothesis, context: dict) -> FalsificationTest: ...

    def adjudicate(self, test: FalsificationTest, context: dict) -> Verdict: ...


def run_inversion(inverter: "Inverter", claim: str, context: Optional[dict] = None) -> Verdict:
    """The shared Popper pipeline: invert → specify → adjudicate, with the discipline enforced ONCE.

      1. invert      — construct the counter-hypothesis.
      2. specify     — turn it into an EXECUTABLE test. If the test is not executable (empty candidate),
                       this is narrative skepticism: STOP and return an undecided Verdict (the harmful
                       "doubt without a test" the inverter_agent creed forbids — refused for everyone).
      3. adjudicate  — let the exogenous arbiter decide. The Verdict is whatever the arbiter returns
                       (synchronous bool for Lean; deferred=None for a queued empirical test).

    The proposer never self-credits: `falsified=True` can only come from `adjudicate`'s arbiter."""
    ctx = context or {}
    counter = inverter.invert(claim, ctx)
    test = inverter.specify(counter, ctx)
    if not test.is_executable:
        return Verdict(falsified=None, arbiter="none",
                       detail="narrative-only inversion (no executable test) — refused per the "
                              "'no doubt without a test' discipline", meta={"counter": counter.statement})
    return inverter.adjudicate(test, ctx)


def _selftest() -> int:
    """Deterministic contract checks (no substrate)."""
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    class _NarrativeOnly:
        """An inverter that DOUBTS but proposes no executable test — must be refused."""
        def invert(self, claim, ctx):
            return CounterHypothesis(statement=f"¬({claim})", rationale="doubt")

        def specify(self, counter, ctx):
            return FalsificationTest(counter=counter, candidate="")  # no test ⇒ narrative

        def adjudicate(self, test, ctx):  # must NEVER be reached
            return Verdict(falsified=True, arbiter="should_not_run")

    class _Sync:
        """A synchronous arbiter (Lean-shaped): the test executes and the verdict is a hard bool."""
        def __init__(self, kill):
            self.kill = kill

        def invert(self, claim, ctx):
            return CounterHypothesis(statement=f"¬({claim})")

        def specify(self, counter, ctx):
            return FalsificationTest(counter=counter, candidate="proof_of_not_G")

        def adjudicate(self, test, ctx):
            return Verdict(falsified=self.kill, arbiter="lean_kernel",
                           witness=test.candidate if self.kill else "")

    v_narr = run_inversion(_NarrativeOnly(), "G")
    ok("narrative-only inversion is refused (undecided, arbiter=none)",
       v_narr.falsified is None and v_narr.arbiter == "none")
    v_kill = run_inversion(_Sync(kill=True), "G")
    ok("synchronous arbiter can KILL (falsified=True, witness carried)",
       v_kill.falsified is True and v_kill.arbiter == "lean_kernel" and v_kill.witness == "proof_of_not_G")
    v_stand = run_inversion(_Sync(kill=False), "G")
    ok("synchronous arbiter can let it STAND (falsified=False, no witness)",
       v_stand.falsified is False and not v_stand.witness)
    ok("isinstance(Inverter) structural check", isinstance(_Sync(False), Inverter))

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
