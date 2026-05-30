# GP-163d Unified Acceleration — Public Claim Summary (Internal Candidate, Hold-and-Flag)

> Public-evidence surface for an apparatus-internal scale-dependence
> candidate. Working directory private; cited by
> `docs/public_claim_register.md` under *Modified Gravity / AQUAL /
> RAR*. **This is not a promoted unified-acceleration claim** — the
> register's hold-and-flag posture is the operative framing.

## Claim (apparatus-internal only)

A six-parameter density-radius susceptibility form, pre-committed to
**Hypothesis S (scale-dependence)** with anti-patterns AP-1 (false
fit on absent data) and AP-2 (hidden universality) explicitly
forbidden by the project charter and respected by the form, passes
the apparatus's holdout (class A withheld, MRE 0.275) and farther-
tail (84 class-B + 12 class-C unseen rows, MRE 0.275 against a
threshold of 0.50) gates under an **apparatus-internal score of 100**.
Class B and C predictions are determined by smooth functions of
continuous features (`radius_log10`, `rho_local_log10`, NaN-safe
disk/gas terms on class A only) — *no* free class-conditional
parameter is introduced for the unseen classes.

## What is real here

The pre-commit discipline is real. The charter forbids both AP-1
(declaring a free parameter that has no visible-class rows to
constrain it) and AP-2 (hidden universality — a class-conditional
form whose unseen-class branches reduce to the visible-class branch
under default parameters), and the recovered form respects both. The
NaN-safe gating on class-A-only features is correct discipline. A
non-trivial farther-tail margin was cleared on unseen classes under
a smooth feature-conditioned form. The apparatus's own probability
DAG places the favorable outcome at **0.78**, not 1.0 — the score of
100 is the *rubric verdict*, not the probability the law is right.

## Why this is not promoted to a public unified-acceleration claim

- **MRE < 0.50 is a loose threshold for a physics-grade claim** —
  "agreement within a factor of 1.5" passes the gate, but it is not
  law-grade discrimination.
- **The unseen-class sample is small** (84 + 12 rows).
- **Six free parameters with sigmoid saturations** is flexible
  relative to the unseen evidence.
- **The disk/gas features that distinguish class A are NaN on B and
  C**, so the class-B/C prediction effectively rides on one
  continuous feature (`rho_local_log10`).
- **The judge layer is LLM-based**, not an external physicist. The
  apparatus's own probability DAG sits at 0.78.
- **The supporting Lagrangian derivability is sketched, not derived.**
- **The thesis's own self-flagged catastrophic mode** is precisely
  that an enriched future substrate could expose a class-separating
  cause the current features do not capture.

## Retest tag

*Apparatus-internal verdict only; original-run only (n=1); not
externally reviewed.*

## Next falsifier

An enriched v4 substrate that exposes one new candidate
class-separating feature (e.g., a cluster gas-mass-profile slope or
a wide-binary perihelion observable), independently chosen; **or**
an external physicist's re-evaluation against an alternative
phenomenological form with the same parameter count.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Modified Gravity / AQUAL / RAR*, sub-entry *Internal
  scale-dependence candidate*.
- Working directory (private): `projects/gp163d_unified_accel/`.
