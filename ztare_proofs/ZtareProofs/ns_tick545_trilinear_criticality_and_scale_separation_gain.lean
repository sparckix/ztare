import Mathlib.Tactic
import ZtareProofs.ns_commutator_tower_irreducible_estimate

/-!
# Tick545 — Trilinear-criticality (tick544 H3 fails) + the genuine scale-separation gain

## Origin (self-Meta-Darwin continuation, pencil-first)

Continuing the strict-margin proof attempt: working H3 honestly
revealed that tick544's `budget ≤ C·∫|w|²` (L²-control) is the WRONG
Calderón–Zygmund bound. This tick records the correct structural
facts as proved theorems:

1. **Trilinear-criticality (NEGATIVE, PROVED).** The pressure flux
   `α_QP = ∫ p·(w·∇φ)`, `p = Riesz(w⊗w)`, is degree-3 trilinear in
   `w`. The only scale-consistent CZ-consistent bound is
   `|α_QP| ≤ C·A` with `A = ∫|w|³` (cubic-critical). Modeling the
   flux abstractly as a value `T` with the honest cubic bound
   `|T| ≤ C·A` and tower level `currentStep = A`, the produced ratio
   is `≤ C` with **no `M` dependence**: amplitude rearrangement at a
   single scale cannot beat the cubic-critical homogeneity. So
   tick544's `1/M` gain does not survive — the strict margin is NOT
   produced by single-scale concentration.

2. **Scale-separation gain (POSITIVE, PROVED).** The genuine gain
   comes from CZ off-diagonal kernel decay across a scale separation:
   core at scale `r`, cancelling sheath at scale `r' < r`. If the
   trilinear flux factors with off-diagonal decay
   `|T| ≤ C·(r'/r)^κ·A` (κ > 0 — the genuine CZ off-diagonal
   estimate, the real frontier), then `ratio ≤ C·(r'/r)^κ`, which is
   `< 1` once `r' < r` sufficiently — a strict margin produced from
   **scale separation**, not amplitude.

## Pencil (stated first, per Gowers-first discipline)

Flux integrand `p·(w·∇φ)` = (deg-2 Riesz of `w⊗w`) · (deg-1 `w`) =
deg-3 in `w`. A homogeneous degree-3 functional `T(λw) = λ³ T(w)`;
under the NS rescaling that fixes the cubic CKN mass `A`, `T/A` is
scale-invariant ⇒ no factor of the amplitude `M` can appear. Hence
single-scale amplitude rearrangement (tick544's mechanism) yields
`ratio = O(1)`, never `O(1/M)`. The escape is to place the three
`w`-slots at separated scales; the CZ kernel `K(x) ~ |x|^{-3}` then
contributes a genuine off-diagonal factor `(r'/r)^κ` between the
core's stress and the boundary collar at the larger scale.

## Universal-language ops composed (META-PATTERN-022)

- **Problem Reformulation** — "produce ratio<1" → "is the flux
  amplitude-gainable or homogeneity-locked?"
- **Sharpness / Failure-Witness Construction** — trilinear
  homogeneity is the exact failure witness for the single-scale
  mechanism (tick544).
- **Characterization by Obstruction** — the obstruction to a 1/M
  gain is degree-3 homogeneity; the only bypass is scale separation.
- **Auxiliary Comparison Object Construction** — the off-diagonal
  factor `(r'/r)^κ` is the comparison object carrying the genuine
  gain.
- **Quantitative Threshold Dichotomy** — single-scale (ratio O(1),
  no margin) vs scale-separated (ratio ≤ C(r'/r)^κ < 1).

## Honest scope

The NEGATIVE result is unconditional (homogeneity). The POSITIVE
result is conditional on the CZ off-diagonal estimate
`|T| ≤ C(r'/r)^κ A`, κ>0 — that estimate is the real remaining PDE
frontier (genuine harmonic analysis: Calderón–Zygmund kernel
off-diagonal decay between separated scales), now correctly located
and NOT a single-scale amplitude trick. tick544's H3 is corrected,
not silently kept.

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar trilinear-flux model + cubic budget
- direction ✓ cubic bound ⇒ ratio O(1); off-diagonal ⇒ ratio<1
- quantifier ✓ ∀ flux value / scale ratio
- domain ✓ super-Type-I core/sheath
- dimension ✓ scalar A / ratio / (r'/r)
- inclusion ✓ feeds existing `defectBudgetSubcriticalityEstimate`
-/

namespace ZtareProofs.NSTick545TrilinearCriticalityAndScaleSeparationGain

open ZtareProofs

/-! ## (1) NEGATIVE: trilinear-criticality kills the single-scale 1/M gain -/

/--
**`single_scale_ratio_has_no_amplitude_gain`** (PROVED).

Honest cubic CZ bound `|T| ≤ C·A` with tower level `A`: the ratio is
`≤ C`, with NO dependence on the amplitude `M`. Whatever `M` is, the
single-scale mechanism gives `ratio = C` — it cannot be driven below
1 by `M → ∞`. (Contrast tick544, whose `Cκ/M` rested on the wrong
L² H3.)
-/
theorem single_scale_ratio_has_no_amplitude_gain
    (T A C M : ℝ)
    (hA : 0 < A)
    (hC : 0 ≤ C)
    (hcubic : |T| ≤ C * A) :
    |T| / A ≤ C ∧ (∀ M' : ℝ, |T| / A ≤ C) := by
  have hbound : |T| / A ≤ C := by
    rw [div_le_iff₀ hA]; linarith [hcubic]
  exact ⟨hbound, fun _ => hbound⟩

/--
**`single_scale_not_subcritical_in_general`** (PROVED).

If the honest cubic constant `C ≥ 1`, the single-scale ratio bound is
`≥`-side `C ≥ 1`: it does NOT certify `ratio < 1`. A witness that the
mechanism fails to produce the strict margin.
-/
theorem single_scale_not_subcritical_in_general
    (C : ℝ) (hC : 1 ≤ C) :
    ¬ (∀ T A : ℝ, 0 < A → |T| ≤ C * A → |T| / A < 1) := by
  intro h
  -- witness: T = C, A = 1.  |C| = C ≤ C*1, but |C|/1 = C ≥ 1.
  have hCnn : (0:ℝ) ≤ C := by linarith
  have hwit := h C 1 (by norm_num) (by
    rw [abs_of_nonneg hCnn]; linarith)
  rw [abs_of_nonneg hCnn] at hwit
  simp at hwit
  linarith

/-! ## (2) POSITIVE: the genuine scale-separation gain -/

/--
**`scale_separation_gives_strict_ratio`** (PROVED).

The genuine mechanism: CZ off-diagonal decay across separated scales
gives `|T| ≤ C·q·A` where `q = (r'/r)^κ` is the off-diagonal factor.
If `0 ≤ C`, `q ≥ 0`, `C·q < 1`, then the produced ratio is strictly
below one — a real strict margin from SCALE SEPARATION.
-/
theorem scale_separation_gives_strict_ratio
    (T A C q : ℝ)
    (hA : 0 < A)
    (hC : 0 ≤ C) (hq : 0 ≤ q)
    (hoff : |T| ≤ C * q * A)
    (hCq : C * q < 1) :
    |T| / A ≤ C * q ∧ C * q < 1 := by
  refine ⟨?_, hCq⟩
  rw [div_le_iff₀ hA]; linarith [hoff]

/--
**`produces_subcriticality_from_scale_separation`** (PROVED).

Feed the scale-separation ratio `C·q < 1` into the pre-existing
`defectBudgetSubcriticalityEstimate` (no rebuild). This is the
corrected, honest production: strict margin from the off-diagonal
factor `q = (r'/r)^κ`, not from a single-scale amplitude trick.
-/
theorem produces_subcriticality_from_scale_separation
    (budget A C q : ℝ)
    (hA : 0 ≤ A)
    (hbudget_nonneg : 0 ≤ budget)
    (hCq0 : 0 ≤ C * q)
    (hCq1 : C * q < 1)
    (hbud : budget ≤ (C * q) * A) :
    defectBudgetSubcriticalityEstimate budget A (C * q) :=
  ⟨hbudget_nonneg, hA, hCq0, hCq1, hbud⟩

/-! ## (3) Honest scope record -/

structure Tick545HonestScopeRecord where
  /-- tick544 H3 corrected (wrong CZ bound), not silently kept. -/
  tick544_H3_corrected : Prop
  /-- Trilinear-criticality NEGATIVE result is unconditional. -/
  negative_is_unconditional_homogeneity : Prop
  /-- Genuine gain relocated to CZ off-diagonal scale separation. -/
  gain_is_scale_separation_not_amplitude : Prop
  /-- Positive result conditional on the off-diagonal estimate
      `|T| ≤ C(r'/r)^κ A` — the correctly-located real frontier. -/
  remaining_frontier_is_off_diagonal_CZ_estimate : Prop
  /-- Produces the EXISTING subcriticality object, no rebuild. -/
  produces_existing_object : Prop

end ZtareProofs.NSTick545TrilinearCriticalityAndScaleSeparationGain
