import Mathlib.Analysis.SpecialFunctions.Exp
import Mathlib.Tactic
import ZtareProofs.ns_abstract_eviction_implication

namespace ZtareProofs

/--
Abstract angle-eviction lemma:
if the alignment angle grows at least linearly in time while the system stays
inside a danger cone `θ ≤ θc`, then the contiguous dwell time inside that cone
is bounded by `θc / κ`.
-/
theorem danger_dwell_le_of_angle_growth
    {θ0 θc κ dwell : Real}
    (hκ : 0 < κ)
    (hθ0 : 0 ≤ θ0)
    (hθ0_le : θ0 ≤ θc)
    (hcone : θ0 + κ * dwell ≤ θc) :
    dwell ≤ (θc - θ0) / κ := by
  have hmul : κ * dwell ≤ θc - θ0 := by
    linarith
  exact (le_div_iff₀ hκ).2 (by simpa [mul_comm] using hmul)

/--
If the danger-state production is bounded above by `χmax` and the angle-growth
law forces `dwell ≤ (θc - θ0)/κ`, then a single visit is capped by the
corresponding exponential budget.
-/
theorem visit_cap_of_angle_eviction
    {ω_enter ω_exit χmax θ0 θc κ dwell : Real}
    (hω_nonneg : 0 ≤ ω_enter)
    (hgrowth : ω_exit ≤ ω_enter * Real.exp (χmax * dwell))
    (hχmax : 0 ≤ χmax)
    (hκ : 0 < κ)
    (hθ0 : 0 ≤ θ0)
    (hθ0_le : θ0 ≤ θc)
    (hcone : θ0 + κ * dwell ≤ θc)
    (hbudget_cap : χmax * ((θc - θ0) / κ) ≤ (1 : Real) / 100) :
    ω_exit ≤ ω_enter * Real.exp ((1 : Real) / 100) := by
  have hdwell : dwell ≤ (θc - θ0) / κ := by
    exact danger_dwell_le_of_angle_growth hκ hθ0 hθ0_le hcone
  have hχbound : χmax * dwell ≤ χmax * ((θc - θ0) / κ) := by
    exact mul_le_mul_of_nonneg_left hdwell hχmax
  have hbudget : χmax * dwell ≤ (1 : Real) / 100 := by
    exact le_trans hχbound hbudget_cap
  exact visit_multiplier_cap hω_nonneg hgrowth hbudget

/--
NS-specific premise-lift target shape:
to turn the empirical stall law into a structural one, it would be enough to
 prove an angle-growth lower bound strong enough that

   χmax * ((θc - θ0) / κ) ≤ 1/100

for every danger-state visit.

This theorem is intentionally abstract: it names the exact missing premise
without pretending the current numerics prove it.
-/
theorem premise_lift_target_shape
    {χmax θ0 θc κ : Real}
    (_hκ : 0 < κ)
    (hsmall : χmax * ((θc - θ0) / κ) ≤ (1 : Real) / 100) :
    χmax * ((θc - θ0) / κ) ≤ (1 : Real) / 100 := by
  exact hsmall

end ZtareProofs
