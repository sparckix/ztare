# GP-150 Epistemic-Boundary Audit — Public Claim Summary

> Public-evidence surface for an apparatus-scope audit project.
> Working directory private; cited by `docs/public_claim_register.md`
> under *Apparatus Self-Audits*.

## Claim

The apparatus's *continuous-mixture* implementation of a subordinated
Brownian semigroup `u(x,t) = ∫₀^∞ G(x,s) ν_t(ds)` represents the
subordinator measure `ρ_t = ν_t/s` by a **finite table** of weights
`{w_j}` at variances `{s_j}` — i.e., not a continuous mixture in
practice. The Fourier symbol identity
`σ(k) = −log 𝔼[e^{ikB_{S_t}}] = ∫₀^∞ (1 − e^{-sk²}) ρ_t(ds)` constrains
how the finite-table approximation can replace the continuous law.
The audit characterizes the truncation error envelope and the
admissibility boundary of the implementation. Apparatus-internal
champion score: **71 / 100**.

## What this audits

The project is an *epistemic-boundary* audit: it identifies *where the
apparatus's knowledge-state actually lies*. The implementation
advertises a continuous mixture; the audit records the finite-table
truncation as the real epistemic surface, and bounds the discrepancy.
Recorded as INS-024.

## Retest tag

*Original-run only (n=1).* Score caps at 71 because the analytic
truncation bound is partial; a tighter bound (or a continuous-mixture
implementation) would lift the score.

## Honest framing

The contribution is the *recognition* of an epistemic-scope mismatch
(continuous-mixture advertised, finite-table implemented) and the
*bounding* of the implementation's true admissibility surface. It is
not a fix to the apparatus; it is a sealed audit that names what the
fix would need to deliver.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Apparatus Self-Audits* (`gp150_epistemic_boundary_audit`).
- Working directory (private): `projects/gp150_epistemic_boundary_audit/`.
