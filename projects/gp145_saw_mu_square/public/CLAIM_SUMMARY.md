# GP-145 SAW μ_sq Rigorous Null — Public Claim Summary

> Public-evidence surface for an apparatus-internal hardening project.
> Working directory private; the public artifact is this summary, cited
> by `docs/public_claim_register.md` under *Apparatus Self-Audits*.

## Claim

PSLQ search for an integer relation among the self-avoiding-walk
connective constant `μ_sq` and the 20-constant dictionary `Δ₁` returns
**no relation** under bounded conditions: dimension `d ≤ 5`, integer
coefficient height `H ≤ 10⁸`, 2-norm condition number
`κ̂ < 10¹²`. The Bailey-Ferguson 1992 explicit-error-constant theorem
guarantees deterministic recovery when working precision
`p ≥ T := ⌈log₂ H + log₂ κ̂ + d · log₂|Δ₁| + 64⌉`; six independent
seeded runs at `p ≥ T` simultaneously missing an existing relation has
probability bounded by ~2⁻³⁸⁴. The null is rigorous within the search
envelope.

## Score and what it caps at

Apparatus-internal champion score: **56 / 100**. The cap (a real,
methodologically interesting ceiling) is the *premise rigor on `κ̂`* —
the condition-number bound is empirical from the recorded runs, not
proven a priori for the full `Δ₁`. The G2 PSLQ falsity gate held
across all runs (no false positive).

## Retest tag

*Methodology / framework claim with explicit premise caveat.* The
result is a **rigorous null within scope**, not a "no closed form
exists" statement; it is a closed-form null *inside the named
(d ≤ 5, H ≤ 10⁸, Δ₁) search envelope* under the recorded `κ̂` bound.

## Honest framing

This is a methodology claim, not a discovery. It is the canonical
INS-053 instance of "null-result discipline" — the framework
distinguishes a *protocol-bounded* null from an *existence* null and
records the gap (`κ̂` bound is empirical, not provable in current
scope) as the durable next-step.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Apparatus Self-Audits* (`gp145_saw_mu_square`).
- Working directory (private): `projects/gp145_saw_mu_square/`.
- Sibling: a narrower-scope follow-up
  [`projects/gp145b_saw_narrow_null/public/CLAIM_SUMMARY.md`](../../gp145b_saw_narrow_null/public/CLAIM_SUMMARY.md)
  with a *provable* `κ̂` bound on a smaller dictionary.
- Next falsifier: prove `κ̂` analytically on the full `Δ₁`, OR
  enlarge the dictionary and re-search.
