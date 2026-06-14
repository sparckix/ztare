"""The substrate-agnostic VERIFICATION-VERDICT contract shared by every checker binding.

This is the small, genuinely-shared core of "checker-agnostic governance": not a forced unified `verify`
(a Lean proof-compile checker and an SMT equivalence checker do DIFFERENT operations — coercing them under
one signature is the "two engines, one coat" trap), but the THREE things every checker really shares —
the verdict TYPE (`CheckResult`), the strict-pass RULE (`is_ok`), and an audit NAME. The operations
(compile a proof, check ∀-equivalence, decide labelled instances) stay per-checker; the GOVERNANCE that
consumes their verdicts does not need to know which substrate produced them.

Earns its place in `common/` by ≥2 real consumers (the adversary's own promotion condition):
  - `ztare.leanmill.solver.solver_core.LeanLakeChecker` — Lean/lake proof-compile binding.
  - `ztare.common.smt_checker.SmtPolicyChecker` — z3 equivalence-leg binding (with counterexamples).
NO substrate imports here (no Lean, no z3) — the exact discipline of `common/kernel_hardener.py` and
`common/inversion.py`, so both engines can depend on it without a cycle or a heavy dep.

  python -m ztare.common.governed_verification --selftest
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class CheckResult:
    """A checker's verdict, substrate-neutral: `ok` (did it ratify), `diagnostics` (human-readable — a
    Lean error tail, an SMT counterexample, a failing instance), and `name` (WHICH checker ratified, so a
    closure/audit record is traceable to its verification substrate)."""
    ok: bool
    diagnostics: str = ""
    name: str = ""


def is_ok(result) -> bool:
    """STRICT pass: True only for canonical `True` or a `CheckResult` with `ok is True`. A verdict string,
    a non-zero return code, `None`, or any non-True value is INCONCLUSIVE ⇒ NOT a pass — because a false
    ACCEPT is a fabricated success (the opposite bias from a prover gate). The single place the statement
    side and every checker binding agree on "what counts as ratified"."""
    if isinstance(result, CheckResult):
        return result.ok is True
    return result is True


@runtime_checkable
class Checker(Protocol):
    """The marker every checker binding satisfies: an audit `name`. The verification OPERATION is
    deliberately NOT fixed here (proof-compile / equivalence / instance-battery are different jobs);
    what is shared is that each produces a `CheckResult` and is identifiable in the audit trail. A
    consumer that holds a `Checker` should call its operation-specific method (`verify`, `equivalence`,
    `decide_instances`) and pass the verdict through `is_ok`."""
    name: str


def _selftest() -> int:
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    ok("checkresult_fields", CheckResult(True, "d", "n").ok is True and CheckResult(False).name == "")
    ok("is_ok_true", is_ok(True) and is_ok(CheckResult(True)))
    ok("is_ok_strict_rejects_coercibles",
       not is_ok(1) and not is_ok("YES") and not is_ok(None) and not is_ok(CheckResult(False)))

    class _Mock:
        name = "mock"

        def verify(self, x):
            return CheckResult("good" in x, "", self.name)

    m = _Mock()
    ok("mock_is_checker", isinstance(m, Checker))           # satisfies the marker (has .name)
    ok("mock_verdict_through_is_ok", is_ok(m.verify("good")) and not is_ok(m.verify("bad")))
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
