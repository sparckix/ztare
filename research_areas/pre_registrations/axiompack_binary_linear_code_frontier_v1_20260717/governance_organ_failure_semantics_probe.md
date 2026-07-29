---
description: "Pre-registered crash-control probe for required LeanMill governance organs."
status: closed_pass
date: 2026-07-17
---

# Governance-organ failure semantics probe

## Identity boundary

An organ may report a mathematical or policy rejection only from its defined
check. A crash, missing runtime dependency, or timeout has a different
identity: verifier unavailability. Both outcomes withhold closure credit, but
their receipts must remain distinguishable.

## Hypothesis

The common anti-laundering aggregator currently catches required-organ errors
without changing `passed`, and the outer proof gate treats an aggregator
exception as `anti_laundering_passed=True`. A deterministic injected crash will
therefore demonstrate an authority fail-open. Recording required-organ errors
as typed unavailability and setting `passed=False` will close the route without
changing any normal accepted or rejected control.

## Discriminating test

1. Replace one pure detector with a function that raises a fixed exception.
2. Run the common kernel on a nonvacuous selected theorem.
3. Require `available=false`, `passed=false`, the exact unavailable organ name,
   and no fabricated confirmed-laundering class.
4. Inject an exception at the outer kernel call and require the proof gate to
   withhold `gate_passed` with an unavailable flag.
5. Replay normal target-scope, ratification, and closed-artifact controls.

## Success criterion

- both injected crash controls withhold credit;
- unavailability is explicit and separate from `confirmed` findings;
- all normal focused controls preserve their prior verdicts;
- no adapter or domain-specific branch is added.

## Kill conditions

- the change classifies runtime faults as mathematical counterevidence;
- existing normal controls change verdict;
- callers cannot represent unavailability without changing the frozen closure
  record identity.

If killed, raise a typed exception at the common boundary and require every
caller to translate it to an open/unavailable receipt. Never restore a
fail-open closure path.

## Result

Passed. A required-organ exception now yields `available=false`,
`passed=false`, the exact unavailable organ name, and an empty `confirmed`
list. An exception around the outer proof-gate kernel sets
`anti_laundering_passed=false` and withholds `gate_passed`. Canonical
re-elaboration failure and failure of both Cage and direct-kernel routes use
the same typed unavailable state.

Executable controls are in
`tests/test_lean_proof_gate_target_scope.py`, including
`test_required_organ_crash_is_typed_unavailable`,
`test_outer_kernel_crash_withholds_gate_credit`, and the canonical/Cage
unavailability probes. Normal accepted and rejected target controls retain
their prior dispositions.
