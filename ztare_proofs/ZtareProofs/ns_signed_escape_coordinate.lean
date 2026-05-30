import Mathlib.Analysis.SpecialFunctions.Exp
import Mathlib.Tactic
import ZtareProofs.ns_abstract_eviction_implication

namespace ZtareProofs

/--
Generic signed escape-coordinate implication:
if a danger-state visit starts at escape coordinate `a0`, stays inside the
danger tube `a ≤ Δ`, and the coordinate increases at speed at least `γ`,
then the visit length is bounded by `(Δ - a0) / γ`.
-/
theorem danger_dwell_le_of_signed_escape
    {a0 Δ γ dwell : Real}
    (hγ : 0 < γ)
    (_ha0 : 0 ≤ a0)
    (_ha0_le : a0 ≤ Δ)
    (hband : a0 + γ * dwell ≤ Δ) :
    dwell ≤ (Δ - a0) / γ := by
  have hmul : γ * dwell ≤ Δ - a0 := by
    linarith
  exact (le_div_iff₀ hγ).2 (by simpa [mul_comm] using hmul)

/--
If a danger-state visit obeys a signed escape-coordinate law and the local
production is bounded above by `χmax`, then the single-visit amplification is
capped by the corresponding exponential budget.
-/
theorem visit_cap_of_signed_escape
    {ω_enter ω_exit χmax a0 Δ γ dwell : Real}
    (hω_nonneg : 0 ≤ ω_enter)
    (hgrowth : ω_exit ≤ ω_enter * Real.exp (χmax * dwell))
    (hχmax : 0 ≤ χmax)
    (hγ : 0 < γ)
    (ha0 : 0 ≤ a0)
    (ha0_le : a0 ≤ Δ)
    (hband : a0 + γ * dwell ≤ Δ)
    (hbudget_cap : χmax * ((Δ - a0) / γ) ≤ (1 : Real) / 100) :
    ω_exit ≤ ω_enter * Real.exp ((1 : Real) / 100) := by
  have hdwell : dwell ≤ (Δ - a0) / γ := by
    exact danger_dwell_le_of_signed_escape hγ ha0 ha0_le hband
  have hχbound : χmax * dwell ≤ χmax * ((Δ - a0) / γ) := by
    exact mul_le_mul_of_nonneg_left hdwell hχmax
  have hbudget : χmax * dwell ≤ (1 : Real) / 100 := by
    exact le_trans hχbound hbudget_cap
  exact visit_multiplier_cap hω_nonneg hgrowth hbudget

/--
NS-specific target shape for the current proof seam:
to lift the empirical trace to a structural anti-consolidation mechanism, it
would be enough to prove a signed escape coordinate with speed lower bound `γ`
strong enough that `χmax * ((Δ - a0) / γ) ≤ 1/100` on every danger-state visit.
-/
theorem signed_escape_target_shape
    {χmax a0 Δ γ : Real}
    (_hγ : 0 < γ)
    (hsmall : χmax * ((Δ - a0) / γ) ≤ (1 : Real) / 100) :
    χmax * ((Δ - a0) / γ) ≤ (1 : Real) / 100 := by
  exact hsmall

end ZtareProofs
