---
description: "Pre-registered solver-consumer probe for governance unavailability."
status: closed_pass
date: 2026-07-17
---

# Solver governance-unavailability probe

## Identity boundary

The solver may produce and compile a candidate proof. Only the common
governance result can make that candidate credit-ready. A governance runtime
fault or diagnostic disablement preserves the candidate for retry but cannot
be translated into approval or successful falsification.

## Hypothesis

Two solver consumers initialize the governance result as passing and retain
that value after exceptions or `ZTARE_KERNEL_AUTHORITATIVE=0`. An injected
kernel exception can therefore award closure credit, while an exception in the
falsification audit can return success. Replacing the Boolean default with a
three-way pass/reject/unavailable result will withhold credit and preserve the
failure identity.

## Discriminating test

1. Inject a common-kernel exception in the preverified-proof validation path.
2. Require the resulting contract receipt to report governance unavailable and
   `credit_ready=false`.
3. Disable the authoritative kernel through the existing diagnostic setting
   and require the same no-credit outcome.
4. Inject a governance exception in the falsification path and require an
   inconclusive/unavailable result rather than `True`.
5. Replay existing ratification, closed-artifact, and solver-boundary controls.

## Success criterion

- only an explicit `passed is True` governance result can contribute credit;
- exceptions and diagnostic disablement are typed unavailable;
- candidate proof/source bytes remain available for retry;
- existing pass and rejection controls preserve their verdicts.

## Kill conditions

- the repair discards a compiled candidate rather than preserving it for
  retry;
- unavailability is mislabeled as theorem rejection or counterevidence;
- the common kernel is duplicated inside the solver.

If killed, raise a typed governance-unavailable exception and force the
closed-artifact finalizer to retain an open receipt. Do not map the exception
to a passing Boolean.

## Result

Passed. Solver credit now requires `available is true` and `passed is true`
from the common target-governance kernel. Kernel exceptions and diagnostic
disablement retain the compiled candidate but return
`governance_unavailable` with `credit_ready=false`. Falsifier governance
exceptions return an inconclusive typed outcome and cannot count as a
successful refutation.

The discriminators are
`test_governance_unavailability_never_awards_solver_credit`,
`test_falsifier_governance_unavailability_is_inconclusive`, and the explicit
positive falsifier control in `tests/test_ratification_route.py`.
