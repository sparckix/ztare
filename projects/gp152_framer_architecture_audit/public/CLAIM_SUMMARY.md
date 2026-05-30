# GP-152 Framer Architecture Audit — Public Claim Summary

> Public-evidence surface for a Framer-language audit project. Working
> directory private; cited by `docs/public_claim_register.md` under
> *Apparatus Self-Audits*.

## Claim

A bounded, symmetry-filtered, MDL-driven pre-solver phase (the
"Framer") reduces the description length — and therefore the search
burden — of any invariant that is concise only after a coordinate
change. The conditional claim: if the solver stack is preceded by a
Framer that (1) prunes the transformation space with symmetry and
dimensional filters, (2) explores the residual search tree with an
`O(M log M)` per-axis MDL-greedy walk, and (3) hands the best-MDL
coordinate pair to the existing solvers, then the apparatus on average
reaches `≥ 85` score in `≤ 10` iterations for invariants that are
first-order expressible in the transformation basis
`Σ = {shift, scale, power, log, exp, reciprocal}`. Scope:
single-curve fits and multi-dataset universality collapses with `≤ 4`
non-universal scalings per dataset. Apparatus-internal champion score:
**91 / 100**.

## What this validates

The audit verifies that the framing-apparatus layer produces
well-formed action-principle candidates (INS-032) and integrates
cleanly with the gate stack downstream. The rival framing — "reactive-
only" post-hoc framers (INVERT, COMPRESS, CATEGORY_SWITCH) — is shown
to fire often enough to make the proactive Framer's marginal value the
central test, not a tautology.

## Retest tag

*Original-run only (n=1); apparatus / framework claim.* The cap at 91
reflects the bounded scope (`≤ 4` non-universal scalings per dataset);
broader claims need an enlarged benchmark set.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Apparatus Self-Audits* (`gp152_framer_architecture_audit`).
- Working directory (private): `projects/gp152_framer_architecture_audit/`.
- Companion critique:
  [`projects/gp153_framer_spec_critique/public/CLAIM_SUMMARY.md`](../../gp153_framer_spec_critique/public/CLAIM_SUMMARY.md).
