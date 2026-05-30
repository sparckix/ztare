# GP-072 Sandbox 14 — Chirp-Signal Recovery — Public Claim Summary

> Public-evidence surface for a sealed chirp-signal recovery. Working
> directory private; cited by `docs/public_claim_register.md` under
> *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*.

## Claim

Presented with continuous oscillatory data under cold variable names,
the engine recovered `f(x) = A · sin(B · x²)` with `A = 50, B = 0.01`,
distinguishing the chirp form from two named rivals: a polynomial of
even degree (predicts absolute divergence to infinity outside the
window) and a standard harmonic oscillator `sin(kx)` (predicts a
constant wavelength across all domains). The named discriminator is
the **spatial-frequency compression of zero-crossings**: chirp
predicts monotonically increasing spatial frequency as `|x|` grows;
the harmonic rival predicts constant wavelength. Apparatus-internal
champion score: **94 / 100**.

## What this calibrates

The recovery demonstrates the apparatus's identification of a *bounded
oscillatory* form on a substrate where the simplest naive rival
(harmonic) fits visible data well in any short window but is
falsified by the global zero-crossing structure. The discriminator
(zero-crossing-interval monotonicity) is a reusable primitive for
chirp-vs-harmonic discrimination on bounded oscillatory data.

## Retest tag

*Original-run only (n=1); bounded-oscillation calibration.*

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
  (`gp072_sandbox_14`).
- Working directory (private): `projects/gp072_sandbox_14/`.
