# GP-145b SAW μ_sq Narrow-Scope Null — Public Claim Summary

> Public-evidence surface for the narrower-scope follow-up to GP-145.
> Working directory private; cited by `docs/public_claim_register.md`
> under *Apparatus Self-Audits*.

## Claim

The PSLQ null on `μ_sq` against a small dictionary `Δ₀_small` survives
under a *provable* working-precision margin. Operating at 450 bits of
precision against the 333-bit-padded Clisby uncertainty interval for
`μ_sq` with `Δ₀_small` (3-vector `(μ_sq, k₁, k₂)`), the
Ferguson-Bailey-Arno theorem 2 guarantees that any undetected integer
relation must have `max(|c_i|) > 10⁸`. The retired axiom is the
"bidirectional FBA guarantee" — the theorem grants forward recovery,
not a symmetric residual lower bound; the project re-derives the
correct one-sided guarantee with explicit precision arithmetic.

## Score and what it caps at

Apparatus-internal champion score: **48 / 100**. The cap is the same
methodological ceiling as GP-145 — the analytic precision-margin
argument tightens the *bound* on undetected relations but does not
turn the null into an existence claim.

## Retest tag

*Cross-scope confirmed* relative to GP-145: the narrower-dictionary
null persists with an *analytically* provable `κ̂` envelope, closing
the empirical-`κ̂` gap of the parent project within `Δ₀_small`. The
broader-`Δ₁` envelope's `κ̂` remains empirical.

## Honest framing

This is the analytically tighter sibling of GP-145. It strengthens the
*lower-bound* on any undetected SAW relation under a small dictionary
to `max(|c_i|) > 10⁸`. It does not promote the null to an existence
claim; PSLQ-bounded nulls inside named search envelopes are not
existence proofs.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Apparatus Self-Audits* (`gp145b_saw_narrow_null`).
- Working directory (private): `projects/gp145b_saw_narrow_null/`.
- Parent project (broader scope, empirical `κ̂`):
  [`projects/gp145_saw_mu_square/public/CLAIM_SUMMARY.md`](../../gp145_saw_mu_square/public/CLAIM_SUMMARY.md).
