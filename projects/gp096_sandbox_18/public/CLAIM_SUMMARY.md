# GP-096 Sandbox 18 — Topology-Induction Gap (DFDO) — Public Claim Summary

> Public-evidence surface for the topology-induction-gap diagnosis on
> a two-regime Duffing-plus-power-law substrate. Working directory
> private; cited by `docs/public_claim_register.md` under
> *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*.

## Claim

Presented with `v(u)` data exhibiting segmented smooth decay through
at least two distinct regimes (initial steep decay over `u ∈ [4, 80]`,
followed by a slower decay regime) under cold variable names, the
apparatus identified a **functional surrogate** —
"rational-sum-of-exponentials with inverse-`u` modifiers" — that
passes the hard gates at apparatus-internal score **95 / 100** but
is *in the wrong structural class*. The true ground truth is a
two-regime Duffing-plus-power-law form `v(u) ~ C · (1 + c·u)^{−3.70}`;
the apparatus's recovered form is a different topology that happens
to match the data within the gate margins.

## What this catalogues — topology-induction gap (GP-103)

The diagnosis: the apparatus's hard-gate pass-rate is *not* a
sufficient condition for structural-class correctness. The
recovered form has `score 95` (passes holdout, passes farther-tail
within thresholds) but the minimum gate-passing form the apparatus
*should* have proposed — a two-regime additive composite
`a · exp(−b · u^p) + C · (1 + d · u)^{−3.70}` — was never proposed.
The H-GP103 trigger-guard bug was identified during the post-mortem:
the compositional-hypothesis-generator's trigger checked only the
visible-window gate, not the full gate battery, so the trigger fired
late or not at all on this substrate. The fix is the topology-
induction guard at GP-103.

## Retest tag

*Diagnostic finding (no recovery to retest in the structural sense).*
The functional-surrogate champion is a real artifact; the diagnosis
that the apparatus identified the wrong structural class is the
durable finding. The companion sealed run
`gp096_sandbox_18_gagorder` reproduces the same score and verdict
under an order-parameter variant, confirming the structural mismatch
is not seed-dependent.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Sealed Apparatus Calibrations and Curve-Fit Sandboxes*
  (`gp096_sandbox_18` / `gp096_sandbox_18_gagorder`).
- Working directory (private): `projects/gp096_sandbox_18/` and
  `projects/gp096_sandbox_18_gagorder/`.
