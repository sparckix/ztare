# GP-096 Sandbox 20 — Public Claim Summary

> **What this file is.** The public-evidence surface for a sealed blind
> curve-fit recovery whose full working directory is private. This summary
> is the canonical public artifact cited by the corresponding entry in
> [`docs/public_claim_register.md`](../../../docs/public_claim_register.md)
> under *Polymer Stress-Relaxation Blind Fit*.

## One-line claim

Presented with 22 visible points plus 4 hidden tail points of a monotonic
scalar dataset under cold variable names (no domain labels), the engine
recovered the form `G(t) = A · t^(−B) · exp(−C·t)` with
`A = 0.006598, B = 0.4328, C = 0.754`, passing the apparatus's gates and
falsifying the named structurally strongest rival. The dataset is the
stress-relaxation curve of a noncatenated polystyrene ring polymer melt
(molecular weight 198 kDa), and the recovered form is close to the
*a priori theoretical expectation* given by the source paper's Eqn. 1.

## What was tested

- Visible evidence: 22 monotonic `(t, G)` pairs spanning >5 decades in t
  and >3 decades in G.
- Hidden farther-tail: 4 additional points at high t.
- Cold variable names; the operator did not name the substrate or the
  source paper to the engine.

The pre-committed champion form was the three-parameter family
`G(t) = A · t^(−B) · exp(−C·t)` (each parameter mapping uniquely to a
distinct, resolvable observable data feature: B is the negative empirical
log-log slope at low t; C controls upward curvature in log(G) at large t;
A sets normalization at t₀).

The pre-committed structural rival was the log-quadratic exponential
`G_rival(t) = exp(−a·log(t/t₀) − b·[log(t/t₀)]²)` — the strongest
three-parameter monotonic form that can curve in log–log but lacks a
true exponential cutoff.

## Recovered form and parameters

```
G(t) = A · t^(-B) · exp(-C · t)
A = 0.006598027192503714
B = 0.43275741672097323
C = 0.7543912662524426
```

## Gate verdicts

From the working `fit_result.json`:

| Metric | Value |
|---|---|
| max absolute residual | 0.0251 |
| mean absolute residual | 0.0044 |
| RMSE | 0.0079 |
| residual diagnostic classification | outlier-dominated |
| concentration ratio (worst region: low t) | 0.642 |

The named discriminator at the tail point `t = 2.12` (observed G ≈ 0.001):
the champion stays within ±10%; the log-quadratic rival is off by more
than 50%. The asymptotic-wall gate holds.

## Honest framing — what this is, and what it is not

This is a **blind recovery of a known physical form on a single dataset,
with external validation by the source paper's a priori theory**. The
substrate label was withheld from the engine; the recovered three-parameter
form lines up with what the source paper derives from first principles
as the expected relaxation in this regime.

It is *not* a discovery of new polymer-melt physics. It is *not* an
adjudication between the source paper's theoretical derivation and rival
empirical fits. It is *not* a claim that the same engine recovers
ring-polymer forms in regimes outside the t-range tested. The reported
parameters are single-fit values; uncertainty quantification beyond the
gate thresholds was not reported.

## Retest tag and caveat

*Original-run only (n=1) under cold variable names.* The external
comparison to the source paper's Eqn. 1 is a theory-vs-fit agreement,
not an independent re-run of the engine. The engine has not been pointed
at additional stress-relaxation datasets (other molecular weights, other
ring-polymer melts, other relaxation regimes) under the same gates.

This work was developed in collaboration with an external scientist;
attribution is held pending source-paper context being released alongside.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`, section
  *Polymer Stress-Relaxation Blind Fit*.
- Working directory (private): `projects/gp096_sandbox_20/`.
- Next falsifier: either republish the dataset and the source paper's
  Eqn. 1 alongside the fit so a reader can verify the agreement directly,
  or run the same blind protocol on a second ring-polymer-melt dataset
  (different MW, different regime) and report the form recovered. Both
  are real falsifier moves; the first is cheaper.
