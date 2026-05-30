# OEIS A000959 Newton-Step Variant — Public Claim Summary (Negative Result)

> **What this file is.** The public-evidence surface for the
> Newton-step validation attempt on Lucky-number density. The working
> directory is private. This summary records a **durable negative
> result**: the Newton-step extrapolation path was falsified at
> apparatus-internal score 12 / 100. Recording the falsification is the
> point.

## One-line claim (a negative)

The Newton-step extrapolation hypothesis for the Lucky-number density
ratio — that the form
`a + b · log(n) + c/n + d/(n · log(n))` would extrapolate cleanly under
a Newton-mode validation harness — was tested and **failed**. The
durable evidence is the failure.

## What was tested

The mutator was given the density ratio `L(n)/n` under a Newton-step
validation protocol that required the candidate form to extrapolate
reliably across windows. The pre-committed form was
`a + b · log(n) + c/n + d/(n · log(n))` — log-leading with a
"compressed inverse-logarithmic" sub-leading term distinct from a
loglog correction.

## Result

Apparatus-internal score: **12 / 100**. The Newton-step extrapolation
did not validate. The structural hypothesis "the apparatus can recover
the Lucky-number density via Newton-step validation under this fit
form" is **falsified by this run**.

## Honest framing — durable negative

This is the kind of result the discipline of the apparatus is designed
to preserve: a falsified hypothesis recorded next to the original
claim, so future work cannot quietly re-propose the same path without
addressing the falsification.

The falsification does *not* generalize to "Lucky-number density is
not recoverable under any apparatus." It does cleanly say "the
Newton-step extrapolation under this fit form, at this scale, does
not pass the validation gates."

## Retest tag

*Negative result on retest.* The Newton-step path is demoted; the
demotion is durable evidence. Re-running this exact variant under the
same protocol would not promote the original claim — only a different
substrate, a different protocol, or a different fit family could move
the verdict.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Asymptotic-Law Sandbox Recoveries (Per-Substrate)*
  (A000959 family — Newton-step demotion).
- Working directory (private): `projects/oeis_a000959_newton/`.
- Stronger same-substrate variant (not Newton-step):
  [`projects/oeis_a000959_500k/public/CLAIM_SUMMARY.md`](../../oeis_a000959_500k/public/CLAIM_SUMMARY.md).
