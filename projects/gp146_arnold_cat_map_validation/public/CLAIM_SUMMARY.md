# GP-146 Arnold Cat Map Self-Validation — Public Claim Summary

> Public-evidence surface for an apparatus self-validation run on a
> known dynamical-systems target. Working directory private; cited by
> `docs/public_claim_register.md` under *Apparatus Self-Audits*.

## Claim

The apparatus was pointed at the maximum Lyapunov exponent of Arnold's
cat map under cold variable names, and the discovery + Lean-verification
loop closed against the **known analytic ground truth**
`λ₁ = log((3 + √5)/2) = 2 · log((1 + √5)/2)` under the
G1–G8 + G-CIRC + G-FALSIFY gate battery. Apparatus-internal champion
score: **92 / 100**.

## What this validates

This is the canonical INS-047 instance of *self-validation discipline*:
the apparatus's discovery loop is pointed at a target whose answer is
mathematically established, and the loop is graded on whether it closes
on that answer. It demonstrates that the gate stack does *not* falsely
discriminate against a correct analytic answer when one is reachable in
the grammar.

## Retest tag

*Original-run only (n=1); methodology / framework claim for the
self-validation discipline.* The validation is on a single chaotic-
system target; broader generalization (other dynamical systems, other
analytic invariants) is not claimed.

## Honest framing

This is *not* a discovery of the Lyapunov exponent — the result is
known. It is a *calibration* of the apparatus against a known answer,
recorded so the loop's claim that it closes on correct targets has
sealed evidence behind it.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Apparatus Self-Audits* (`gp146_arnold_cat_map_validation`).
- Working directory (private): `projects/gp146_arnold_cat_map_validation/`.
