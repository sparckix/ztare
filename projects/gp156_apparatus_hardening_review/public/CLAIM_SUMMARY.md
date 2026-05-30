# GP-156 Apparatus Hardening Review — Public Claim Summary

> Public-evidence surface for the foundational apparatus-hardening
> review. Working directory private; cited by
> `docs/public_claim_register.md` under *Apparatus Self-Audits*.

## Claim

Catalogues a class of *fail-open* apparatus failure modes and a
cross-layer fractal-Goodhart pattern. The driving instance: when a
mutator introduces a **misspelled feature key** in `PARAMETRIC_FORM`
(e.g., `features['intrnsc_dim_d']` instead of `features['intrinsic_dim_d']`),
the fit-primitive path swallows the resulting `KeyError` silently and
returns a flat objective value (typically `1e9`) for every
optimization attempt. `scipy.optimize.minimize` interprets a uniform
flat surface as "every region is equally bad," converges to arbitrary
parameters, writes a *valid-looking* `fit_features_result.json`, and
the candidate proceeds — even though no information was learned. This
is a fail-open execution-path denial-of-optimization not caught by
existing smoke tests.

The review extends the pattern to five layers: pre-commit verifier,
gate harness, judge isolation, rubric calibration, and fit-primitive
contract. Recorded as the foundational **INS-001 through INS-006**
findings on fractal Goodhart at every apparatus layer.
Apparatus-internal champion score: **97 / 100**.

## What this hardens

This is the *foundational* apparatus-hardening artifact for the
repository. The five-layer audit underwrites the
"Goodhart-at-every-layer" framing used in the public documentation
([`goodhart_at_every_layer.md`](../../../docs/concepts/goodhart_at_every_layer.md)).
Every gate that survives the review carries a documented failure-mode
the gate was designed against.

## Retest tag

*Methodology / framework claim* — the review is the central
artifact, and the apparatus hardening it catalogues has been replayed
across the five named layers. The cap at 97 reflects the fact that
new layers may yet be identified; the catalogue is open.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Apparatus Self-Audits* (`gp156_apparatus_hardening_review`).
- Working directory (private): `projects/gp156_apparatus_hardening_review/`.
- Public docs underwritten by this review:
  [`docs/concepts/goodhart_at_every_layer.md`](../../../docs/concepts/goodhart_at_every_layer.md),
  [`docs/concepts/anti_pattern_catalog.md`](../../../docs/concepts/anti_pattern_catalog.md).
