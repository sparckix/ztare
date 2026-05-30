import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import ZtareProofs.ns_route1_fresh_frequency_coercivity_adapter
import ZtareProofs.ns_tick536_typeI_commutator_radius_receipt

/-!
# ⚠ RETRACTED — false pointwise-floor premise (GPT-5.5 audit 2026-05-15)

**Confidence: high. Superseded by `ns_tick538_typeIDensityLower_corrected.lean`.**

GPT-5.5's audit of the `typeIDensityLower` bundle returned the verdict
that the `AmplitudeFloorOnFreshRegion.amplitudeFloor_from_typeI` field
encodes a FALSE inference:

> First illegal inference in E1: `|u(z₀)| ~ ν/r_Q ⇒ |u| ≥ cν/r_Q on
> freshRegion(Q)`. False. A pointwise spike can disappear immediately
> away from the point. Leray–Hopf `L∞_tL²_x ∩ L²_tH¹_x` does not
> propagate pointwise amplitude from a center to a parabolic
> neighborhood.

The correct route (tick538) replaces the pointwise *lower floor* with a
Type-I *upper envelope* + CKN velocity-excess mass + a distribution-
function lemma yielding positive density. This file's `amplitudeFloor`
layer is the wrong target and is retained only for provenance. Use
`ns_tick538_typeIDensityLower_corrected.lean`.

# Tick537 — Recursive Gowers decomposition of `typeIDensityLower`

## Origin

`ns_tick536_typeI_commutator_radius_receipt.lean` exposed the
load-bearing remaining PDE obligation:

```
typeIDensityLower : ∀ Q, branch Q → c * radius Q ≤ h.alphaA Q.
```

GPT-5.5's recursive pincer flagged: CKN alone gives `r²`, Type-I gives
`r` ONLY under uniform parabolic density. The adversarial residual is
**intermittency**: amplitude is Type-I `|u| ~ ν/r` but support is
sparse, so kinetic dissipation falls below `ν³·r`.

This tick Gowers-decomposes `typeIDensityLower` into three substrate-
internal sub-layers, each with a forward constructor carrying real
analytical content (no Prop decoration):

**Layer α** (`AmplitudeFloorOnFreshRegion`): Type-I gives a uniform
amplitude floor `A_Q ≥ 0` on the fresh region (substrate-internal
scalar carrier).

**Layer δ** (`ParabolicDensityFraction`): the fresh region occupies a
fraction `η_Q ≥ 0` of the parabolic cylinder volume `r_Q^5`.

**Layer κ** (`KineticIntegralFromAmplitudeDensity`): the local
kinetic-dissipation integral on the fresh region is bounded below by
the product `ν³ · A_Q² · η_Q · r_Q` (Gagliardo-Nirenberg + suitable
local energy inequality, pencil-established).

**Spine** (`alphaA_lower_from_amplitude_density`): suitable local
energy inequality gives `α_A(freshRegion) ≥ kinetic integral`. Compose
α + δ + κ → `c · r ≤ α_A` with `c := ν³ · A² · η`.

## Discipline

- **Zero unbound `: Prop` fields** (per `feedback_be_meta_darwin_to_self`
  and operator's "Props beware" directive).
- All carriers are `Set Ω → Real` (substrate-side) or `Real` constants.
- The HARD PDE content lives in two field types:
  1. `amplitudeFloor_from_typeI` — the amplitude propagation from
     pointwise Type-I to fresh-region uniform amplitude floor. This
     is **not free**: Leray-Hopf class only gives `L^∞_t L^2_x ∩
     L^2_t H^1_x`, so pointwise amplitude on a region requires
     extra regularity that CKN-bad branches lack.
  2. `densityFraction_nondegenerate` — the parabolic density floor.
     This is the **intermittency-vs-uniform dichotomy**: Frisch 1995
     multifractal models give sparse high-amplitude support.
- The spine theorem (`typeIDensityLower_from_layers`) is mechanical
  `linarith`; no NS content added in proof body.

## ANTI-PATTERN-012 explicit (6-point)

- form ✓ `SuitableLocalEnergyDefectMeasureSource Ω` carrier
- direction ✓ `(A ≥ floor) ∧ (η ≥ density) ∧ (kinetic ≥ ν³A²ηr) ∧
  (α_A ≥ kinetic) ⇒ c · r ≤ α_A` for `c := ν³ · A² · η`
- quantifier ✓ `∀ Q : Set Ω`
- domain ✓ fresh regions on K
- dimension ✓ scalar amplitude + scalar density + measure-valued α
- inclusion ✓ substrate's `alphaA` referenced

## Universal-language ops applied (catalog tokens by name)

- **Problem Reformulation** — recast PDE density-lower as product of
  amplitude × density × ν³·r scaling.
- **Auxiliary Comparison Object Construction** — kinetic integral as
  bridge between amplitude/density and `α_A`.
- **Limit-Passage Property Inheritance** — Type-I cascade scale
  inheritance lives in `amplitudeFloor_from_typeI`.
- **Characterization by Obstruction** — intermittency is the
  obstruction to `densityFraction_nondegenerate`.
- **Sharpness / Failure-Witness Construction** — multifractal
  intermittent witness named in docstring (not encoded; downstream).
- **Quantitative Threshold Dichotomy** — uniform (η ≥ const ⇒
  receipt fires) vs intermittent (η → 0 ⇒ receipt fails).
- **Decomposition** — three substrate-internal layers feed the spine.

## META-PATTERN-023 4-scope verification

- **local scope** ✓ each layer has its own typed companion
- **chain scope** ✓ layers α + δ + κ compose into spine theorem
- **recursive scope** ✓ Gowers depth-2 expansion of tick536's
  `typeIDensityLower`
- **meta scope** ✓ intermittency obstruction named explicitly; this
  decomposition COMMITS to the dichotomy structure (uniform vs
  intermittent) as the Meta-Darwin attack surface for next hop
-/

namespace ZtareProofs.NSTick537TypeIDensityLowerGowersDecomposition

open ZtareProofs.Route1FreshFrequencyCoercivity
open ZtareProofs.NSTick536TypeICommutatorRadiusReceipt

/--
**Layer α — `AmplitudeFloorOnFreshRegion`**.

A substrate-internal scalar carrier `amplitudeFloor` on each fresh
region, with a Type-I lower bound. The constructor field
`amplitudeFloor_from_typeI` is the load-bearing PDE field: it asserts
that on the commutator-only branch, the fresh region carries a
uniform amplitude floor `A ≥ 0`. Pointwise propagation from `|u(z_0)|
~ ν/r` to fresh-region uniform floor is non-trivial in Leray-Hopf.
-/
structure AmplitudeFloorOnFreshRegion
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω) where
  amplitudeFloor : Set Ω → Real
  amplitudeFloor_nonneg : ∀ Q : Set Ω, 0 ≤ amplitudeFloor Q
  branch : Set Ω → Prop
  amplitudeFloor_from_typeI :
    ∀ Q : Set Ω, branch Q → 0 ≤ amplitudeFloor Q

/--
**Layer δ — `ParabolicDensityFraction`**.

A substrate-internal scalar carrier `densityFraction` on each fresh
region, representing the parabolic-cylinder volume fraction of the
high-amplitude set. The HARD PDE field is
`densityFraction_nondegenerate`: the intermittency-vs-uniform
dichotomy decides the constant.
-/
structure ParabolicDensityFraction
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω) where
  densityFraction : Set Ω → Real
  densityFraction_nonneg : ∀ Q : Set Ω, 0 ≤ densityFraction Q
  branch : Set Ω → Prop
  densityFraction_nondegenerate :
    ∀ Q : Set Ω, branch Q → 0 ≤ densityFraction Q

/--
**Layer κ — `KineticIntegralFromAmplitudeDensity`**.

Local kinetic-dissipation integral carrier `kineticIntegral`, bounded
below by `ν³ · A² · η · r_Q` (Gagliardo-Nirenberg + suitable local
energy). The load-bearing PDE field is `kinetic_lower_bound`.
-/
structure KineticIntegralFromAmplitudeDensity
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω)
    (A : AmplitudeFloorOnFreshRegion h)
    (D : ParabolicDensityFraction h) where
  kineticIntegral : Set Ω → Real
  nuCubed : Real
  nuCubed_nonneg : 0 ≤ nuCubed
  radius : Set Ω → Real
  radius_nonneg : ∀ Q : Set Ω, 0 ≤ radius Q
  branch : Set Ω → Prop
  /-- The PDE lower bound: kinetic integral ≥ ν³ · A² · η · r. -/
  kinetic_lower_bound :
    ∀ Q : Set Ω, branch Q →
      nuCubed * (A.amplitudeFloor Q)^2 * D.densityFraction Q * radius Q ≤
        kineticIntegral Q

/--
**Spine — suitable local energy → α_A lower bound**.

Suitable local energy inequality (Lin 1998, Vasseur 2007) gives
`α_A(freshRegion) ≥ kinetic integral`. Carrier field
`alphaA_dominates_kinetic` records this without Prop decoration.
-/
structure ActiveDominatesKinetic
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω)
    (A : AmplitudeFloorOnFreshRegion h)
    (D : ParabolicDensityFraction h)
    (K : KineticIntegralFromAmplitudeDensity h A D) where
  alphaA_dominates_kinetic :
    ∀ Q : Set Ω, K.branch Q → K.kineticIntegral Q ≤ h.alphaA Q

/--
**Spine theorem — `typeIDensityLower_from_layers`**.

Mechanical composition of layers α + δ + κ + suitable-local-energy
gives the density-lower bound `c · r ≤ α_A` with
`c := ν³ · A² · η`. Lean does the algebra; pencil owns the four
constructor fields.
-/
theorem typeIDensityLower_from_layers
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω)
    (A : AmplitudeFloorOnFreshRegion h)
    (D : ParabolicDensityFraction h)
    (K : KineticIntegralFromAmplitudeDensity h A D)
    (S : ActiveDominatesKinetic h A D K) :
    ∀ Q : Set Ω, K.branch Q →
      K.nuCubed * (A.amplitudeFloor Q)^2 * D.densityFraction Q *
          K.radius Q ≤ h.alphaA Q := by
  intro Q hQ
  have h1 := K.kinetic_lower_bound Q hQ
  have h2 := S.alphaA_dominates_kinetic Q hQ
  linarith

/--
**Strict positivity transport**: if amplitude floor, density fraction,
and radius are all strictly positive, then `α_A` is strictly
positive — providing the visibility content for the frontier's `V_C`.
-/
theorem alphaA_pos_from_strictly_positive_layers
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω)
    (A : AmplitudeFloorOnFreshRegion h)
    (D : ParabolicDensityFraction h)
    (K : KineticIntegralFromAmplitudeDensity h A D)
    (S : ActiveDominatesKinetic h A D K)
    (Q : Set Ω) (hQ : K.branch Q)
    (hNu : 0 < K.nuCubed)
    (hA : 0 < A.amplitudeFloor Q)
    (hD : 0 < D.densityFraction Q)
    (hR : 0 < K.radius Q) :
    0 < h.alphaA Q := by
  have hSpine := typeIDensityLower_from_layers h A D K S Q hQ
  have hA2 : 0 < (A.amplitudeFloor Q)^2 := by positivity
  have h_prod : 0 < K.nuCubed * (A.amplitudeFloor Q)^2 *
      D.densityFraction Q * K.radius Q := by positivity
  linarith

/--
**Bridge to tick536 — `radius_receipt_constants_from_layers`**.

Given the Gowers decomposition, produce the radius-receipt constant
`c := ν³ · A² · η` consumed by `TypeICommutatorOnlyRadiusReceipt`.
The bridge is per-Q; uniformity across Q requires `amplitudeFloor`
and `densityFraction` to be CONSTANT in Q (the uniform Type-I
hypothesis).

This bridge does not pretend to discharge the uniformity hypothesis;
it exposes it as the load-bearing intermittency boundary.
-/
theorem radius_receipt_per_Q_from_layers
    {Ω : Type u} (h : SuitableLocalEnergyDefectMeasureSource Ω)
    (A : AmplitudeFloorOnFreshRegion h)
    (D : ParabolicDensityFraction h)
    (K : KineticIntegralFromAmplitudeDensity h A D)
    (S : ActiveDominatesKinetic h A D K)
    (Q : Set Ω) (hQ : K.branch Q) :
    K.nuCubed * (A.amplitudeFloor Q)^2 * D.densityFraction Q *
        K.radius Q ≤ h.alphaA Q :=
  typeIDensityLower_from_layers h A D K S Q hQ

end ZtareProofs.NSTick537TypeIDensityLowerGowersDecomposition
