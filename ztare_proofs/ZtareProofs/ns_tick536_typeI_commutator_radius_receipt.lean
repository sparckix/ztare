import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import ZtareProofs.ns_route1_fresh_frequency_coercivity_adapter

/-!
# Tick536 — Type-I commutator-only radius receipt (PDE inequality surface)

## Origin

GPT-5.5 Pro response to v2 eigenq bundle reframed NS Clay flat-radius
cascade closure (narrow Track-B route-1 sense):

> Four-channel pincer (route ∨ pressure ∨ β ∨ α_I) does NOT close
> non-tautologically. Simultaneous countermodel survives: a single
> Leray-Hopf packet with pressure-cancellation + tangential route
> flux + flat β-support + α_I = 0 + Type-I amplitude. Surviving branch
> is commutator-only: `α_A = α_C` on the fresh region. Honest
> closure: add α_C as a fifth visibility channel **with its own
> finite/fresh accounting** — radius-receipt `c · r_Q ≤ α_C(freshRegion Q)`.

## Amnesia reconciliation

The five-channel ALGEBRA already exists in
`ZtareProofs/ns_route1_constructive_frontier.lean:472-515`:
`Route1FiveChannelVisibilityProducer` with channels `V_T, V_Q, V_P,
V_C, V_Aperp` and the strict-subratio theorem
`exists_strict_source_subratio_of_Route1FiveChannelVisibilityProducer`.
GPT-5.5's "α_C as 5th visibility channel" corresponds to the
frontier's `V_C` (4th in that producer) — the algebra is in place.

What is NOT in place is a PDE-side **inhabitation** of `V_C` for the
Type-I commutator-only branch: a producer that takes Type-I /
CKN-bad / signed-identity pencil data and delivers a radius-scale
lower bound on the substrate's `alphaC` measure.

This tick provides the typed-companion surface for that inhabitation.
It does NOT bridge `Set Ω → Real` substrate measures into the
frontier's scalar `Real` channels — that bridge is a separate
substrate-frontier-adapter scope, deliberately out of this tick.

## Self-Meta-Darwin discipline (per feedback_be_meta_darwin_to_self)

- **Zero unbound `: Prop` decoration**: every field is either a
  `Set Ω → Real` carrier, a `Real` constant, an explicit inequality,
  or a substrate adapter premise. No "this design intent" Prop
  placeholders that risk V3 signature-decoration laundering.
- **The hard PDE obligation is named explicitly**: `typeIDensityLower`
  carries the unproven analytical content (`c · r_Q ≤ α_A(freshRegion Q)`).
  CKN alone gives only `r²`; Type-I amplitude gives `r` under uniform
  density — adversarial intermittency residual flagged as
  `CommutatorOnlyTypeIIntermittentCascade` (not encoded here; named
  for downstream Meta-Darwin attack).
- **Composition is mechanical**: `radius_receipt_on_alphaC` is a
  3-line `linarith` from `sameCarrierEquality + typeIDensityLower`.
  Lean adds no PDE content; pencil owns the hypothesis.

## ANTI-PATTERN-012 explicit (6-point)

- form ✓ `SuitableLocalEnergyDefectMeasureSource Ω` carrier
- direction ✓ `(α_A = α_C) ∧ (c·r ≤ α_A) ⇒ c·r ≤ α_C`
- quantifier ✓ `∀ Q : Set Ω`
- domain ✓ fresh regions on K
- dimension ✓ measure-valued α + scalar radius
- inclusion ✓ substrate's `alphaA`, `alphaC` carriers explicitly referenced

## Universal-language ops applied (catalog tokens by name)

- **Problem Reformulation** — recast GPT-5.5's commutator-only branch
  as a substrate-engaged radius-receipt typed companion.
- **Auxiliary Comparison Object Construction** — the same-carrier
  equality `α_A = α_C` is the auxiliary identity letting the density
  lower bound migrate from active to commutator measure.
- **Characterization by Obstruction** — `CommutatorOnlyTypeI` branch
  is the surviving worst-case; its obstruction is `typeIDensityLower`
  intermittency residual.
- **Sharpness / Failure-Witness Construction** — adversarial residual
  `CommutatorOnlyTypeIIntermittentCascade` named for downstream
  Meta-Darwin attack.
- **Quantitative Threshold Dichotomy** — `r²` (CKN alone) vs `r`
  (Type-I uniform density) is the threshold the radius receipt
  depends on.

## META-PATTERN-023 4-scope verification

- **local scope** ✓ single typed companion + single composition theorem
- **chain scope** ✓ feeds frontier's `V_C` inhabitation (separate
  substrate-frontier bridge scope, not in this tick)
- **recursive scope** ✓ closes the GPT-5.5 recursive pincer's
  load-bearing remaining piece (the radius-receipt)
- **meta scope** ✓ amnesia-reconciled (frontier file's existing
  5-channel algebra acknowledged, not reinvented); zero unbound Props
  by design (Self-Meta-Darwin discipline)
-/

namespace ZtareProofs.NSTick536TypeICommutatorRadiusReceipt

open ZtareProofs.Route1FreshFrequencyCoercivity

/--
**Type-I commutator-only radius receipt** — the typed companion that
GPT-5.5's recursive pincer identified as the load-bearing remaining
obligation.

Fields:
- `typeICommutatorOnlyBranch` is a predicate selecting fresh regions
  where the active term is carried entirely by the commutator
  (`α_A = α_C`).
- `c` and `radius` are honest scalars; `c_pos` is a real positivity
  constraint.
- `sameCarrierEquality` is the substrate-measure equality on the
  branch (algebraic).
- `typeIDensityLower` is the PDE-side inequality: under Type-I
  uniform amplitude density over a parabolic cylinder, the active
  term on the fresh region is bounded below by `c · r_Q`. This is the
  HARD field; CKN alone gives only `r²`.

No `Prop` decoration fields. No closure claims. No vocabulary-laundered
"visibility predicate" placeholder.
-/
structure TypeICommutatorOnlyRadiusReceipt
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω) where
  typeICommutatorOnlyBranch : Set Ω → Prop
  c : Real
  c_pos : 0 < c
  radius : Set Ω → Real
  sameCarrierEquality :
    ∀ Q : Set Ω, typeICommutatorOnlyBranch Q → h.alphaA Q = h.alphaC Q
  typeIDensityLower :
    ∀ Q : Set Ω, typeICommutatorOnlyBranch Q → c * radius Q ≤ h.alphaA Q

/--
**Radius receipt on α_C** (mechanical composition).

Given the typed companion's two hypotheses (same-carrier equality +
density lower bound on the active term), the commutator measure pays
radius-scale fresh-region mass.

Lean owns the algebra; pencil owns `typeIDensityLower`.
-/
theorem radius_receipt_on_alphaC
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω)
    (R : TypeICommutatorOnlyRadiusReceipt h) :
    ∀ Q : Set Ω, R.typeICommutatorOnlyBranch Q →
      R.c * R.radius Q ≤ h.alphaC Q := by
  intro Q hQ
  have hSame := R.sameCarrierEquality Q hQ
  have hLower := R.typeIDensityLower Q hQ
  linarith

/--
**Strict positivity transport**: if the radius is strictly positive
on the branch, the commutator measure is strictly positive.

This is the Lean-side anti-trivial witness: `alphaC > 0` on
selected commutator-only fresh regions, providing the visibility
content for the frontier's `V_C` channel.
-/
theorem alphaC_pos_on_branch_of_radius_pos
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω)
    (R : TypeICommutatorOnlyRadiusReceipt h)
    (Q : Set Ω) (hQ : R.typeICommutatorOnlyBranch Q)
    (hr : 0 < R.radius Q) :
    0 < h.alphaC Q := by
  have hcr : 0 < R.c * R.radius Q := mul_pos R.c_pos hr
  have hReceipt := radius_receipt_on_alphaC h R Q hQ
  linarith

end ZtareProofs.NSTick536TypeICommutatorRadiusReceipt
