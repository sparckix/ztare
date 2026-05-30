# GP-161 MDL Anti-Goodhart — Public Claim Summary

> Public-evidence surface for the MDL-pressure Goodhart-immunity test.
> Working directory private; cited by `docs/public_claim_register.md`
> under *Apparatus Self-Audits*.

## Claim

Parsimony pressure (BIC / MDL) does not force the apparatus to select
a wrong-but-simple model when the ground truth is structurally
complex. The instance: an exponential envelope `exp(−b·x)` paired with
a log-chirp oscillatory phase was tested against the critique that
the envelope-phase pairing is *ad-hoc* (the envelope is mathematically
inconsistent with the non-linear oscillatory structure even though
it fits visible data with `max|residual| = 0.012`). Iteration 2
resolves the coupling by re-deriving an envelope that *is* consistent
with the log-chirp phase, rather than retreating to a simpler
parsimony-preferred form that fails the consistency check.
Apparatus-internal champion score: **81 / 100**.

## What this audits

Goodhart immunity at the selection layer (INS-028). A naive MDL/BIC
selection would prefer the simpler `exp(−b·x) · cos²` fit on visible
data (lower complexity, low residual); the apparatus correctly
discriminates the structurally inconsistent pairing under the panel's
critique and reaches for the mathematically consistent (more complex)
envelope. The audit is the demonstration that MDL pressure is *not*
a sufficient selection rule on its own — it needs the consistency
gate alongside.

## Retest tag

*Original-run only (n=1); methodology / framework claim for
selection-layer Goodhart immunity.* The instance is one pairing
(exponential envelope × log-chirp phase); broader generalization
needs more substrate variety.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Apparatus Self-Audits* (`gp161_mdl_anti_goodhart`).
- Working directory (private): `projects/gp161_mdl_anti_goodhart/`.
- Related: the foundational apparatus-hardening review
  [`projects/gp156_apparatus_hardening_review/public/CLAIM_SUMMARY.md`](../../gp156_apparatus_hardening_review/public/CLAIM_SUMMARY.md).
