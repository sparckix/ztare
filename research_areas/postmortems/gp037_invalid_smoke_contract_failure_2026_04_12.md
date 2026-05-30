# GP-037 Invalid Smoke — Contract Failure Post-Mortem

**Timestamp:** 2026-04-12 11:25:42 EDT
**Project:** `gp037_substrate_swap_01`
**Classification:** construction-time contract failure
**Author:** Codex

## Summary

The first GP-037 3b smoke attempt was invalid, not because the model scored `0`, but because the verifier layer that was supposed to make the run scientifically meaningful never engaged.

The sandbox charter described deterministic gates in a human-readable way, but not in the exact machine-readable format the GP-030 parser accepts. The run therefore proceeded with:

- `deterministic_charter_gates.declared = []`
- `harness_invoked = false`

So the smoke run exercised:

- the mutator
- the fitter
- the bounded-discriminator pivot

but **not** the intended GP-030 verifier surface.

## Root Cause

The failure came from a split between:

1. **Human contract**
   - the charter clearly described gates in prose / table form
2. **Machine contract**
   - the parser only accepts:
     - exact heading `## Deterministic Gates`
     - fenced block
     - `deterministic_gates:` list in the expected YAML-ish shape

The human contract looked valid.
The machine contract was not satisfied.

## Meta Lesson

**A sealed experiment is not actually sealed unless the machine path that enforces the contract has been validated end-to-end.**

For verifier sandboxes, seal-time validation must check all three layers:

1. **Parser layer**
   - the charter parser returns non-empty declared gates
2. **Harness layer**
   - the harness emits a payload covering those gates
3. **Score-contract layer**
   - a real evaluation artifact shows `declared != []` and `harness_invoked = true`

Without that, a run can look sealed while the critical enforcement surface is silently inert.

## Why This Matters Beyond GP-037

This is not just a one-off sandbox mistake. It is a general ZTARE lesson:

- human-readable truth is not executable truth
- prose that “obviously means the right thing” is irrelevant if the narrow parser disagrees
- seal discipline has to validate the narrowest machine interface, not the broadest human interpretation

This is the same family of problem ZTARE is built to expose elsewhere:

- the system does not run on what we mean
- it runs on what the executable contract actually binds

## Required Standing Rule

Before any verifier experiment is treated as sealed:

1. dry-run the actual parser path
2. dry-run the actual harness path
3. inspect a real evaluation artifact, not just a smoke script output

If any of those are missing, the run is not sealed.
