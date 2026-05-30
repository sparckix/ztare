# GP-061 Sandbox 11 (Threshold-Activation Recovery) — Public Claim Summary

> Public-evidence surface for the sealed piecewise-threshold recovery.
> Working directory private; cited by `docs/public_claim_register.md`
> under *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*.

## Claim

Presented with a two-variable response `V(t, R)` under cold variable
names, the engine recovered the **piecewise non-differentiable
threshold model**
`V = max(baseline, slope · (t − t_c(R)))` with a control-delayed
Heaviside activation: zero leakage in `∂V/∂t` until the threshold
`t_c(R)` is crossed, instantaneous transition to the active slope
thereafter. The named discriminator is the *Zero-Leakage Structural
Break*: a hyperbolic / softplus rival enforces acausal symmetric
rounding at the hinge (predicting early upward leakage); the
piecewise thesis strictly requires `∂V/∂t = 0` until `t_c`.
Apparatus-internal champion score: **95 / 100**. Holdout passes; the
farther-tail asymptotic gate also holds.

## What this calibrates

A *piecewise non-differentiable* recovery — a target class the
apparatus's smooth-mutator priors do not naturally reach for. The
Zero-Leakage Structural-Break discriminator is a reusable primitive
for piecewise-vs-smooth threshold discrimination.

## Retest tag

*Original-run only (n=1); piecewise-threshold calibration.*

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
  (`gp061_sandbox_11_01`).
- Working directory (private): `projects/gp061_sandbox_11_01/`.
