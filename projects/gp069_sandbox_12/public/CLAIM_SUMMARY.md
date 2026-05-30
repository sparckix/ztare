# GP-069 Sandbox 12 — Modular Quadratic Congruence Recovery — Public Claim Summary

> Public-evidence surface for a sealed modular-arithmetic recovery.
> Working directory private; cited by `docs/public_claim_register.md`
> under *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*.

## Claim

Presented with a deterministic discrete-input-to-output mapping
`y = f(x)` over integer inputs under cold variable names, the engine
recovered the closed-form quadratic congruence
`y = (3x² + 5x + 7) mod 13`. The operative field `m = 13` was
identified from periodic repeating intervals in the input space. The
named discriminator is the **second discrete derivative modulo 13**:
a linear rival `y = (Ax + B) mod 13` requires the second difference
to be `0`; the quadratic thesis requires it to be `2a (mod 13) = 6`.
Apparatus-internal champion score: **83 / 100**.

## What this calibrates

A *vocabulary-boundary* check (INS-012). Discrete modular arithmetic
is a category the apparatus's continuous-grammar mutators do not
naturally reach for; the recovery demonstrates that the apparatus's
discrete-arithmetic search surface can identify a closed-finite-field
mapping when the substrate carries the periodicity signal. The
secondary contribution is the *modulo-difference discriminator* as a
reusable primitive for distinguishing linear-modular from
quadratic-modular targets.

## Retest tag

*Original-run only (n=1); vocabulary-boundary calibration.*

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
  (`gp069_sandbox_12`).
- Working directory (private): `projects/gp069_sandbox_12/`.
