import Mathlib.Tactic
import ZtareProofs.FormalAnalyticCrossJuliaMeromorphic
import ZtareProofs.FormalMeromorphicInfinityChart

/-!
# Pole chart forced by a nonremovable analytic cross-Julia branch

Cross-Julia elimination makes the hidden endpoint meromorphic.  If that
puncture has no finite analytic extension, its meromorphic order is a
strictly negative integer.  This file extracts the positive pole order and
the analytic reciprocal chart required by ramified valuation balance.
-/

namespace FormalAnalyticCrossJuliaPoleChart

open FormalAnalyticCrossJuliaMeromorphic
open FormalAnalyticPuncturedExtension
open FormalMeromorphicInfinityChart

/-- A nonremovable cross-Julia hidden endpoint has a positive finite pole
order and an analytic reciprocal coordinate. -/
theorem AnalyticCrossJuliaCarrier.exists_poleOrder_reciprocalChart
    (carrier : AnalyticCrossJuliaCarrier)
    (hnoExtension :
      ¬HasFiniteAnalyticExtension carrier.hiddenEndpoint carrier.center) :
    ∃ poleOrder : ℕ,
      0 < poleOrder ∧
      meromorphicOrderAt carrier.hiddenEndpoint carrier.center =
        ((-(poleOrder : ℤ) : ℤ) : WithTop ℤ) ∧
      HasAnalyticReciprocalChart carrier.hiddenEndpoint carrier.center := by
  have hmeromorphic := carrier.hiddenEndpoint_meromorphicAt
  obtain ⟨hnegative, _hcobounded, hreciprocal⟩ :=
    meromorphic_infinity_chart_terminal_certificate
      carrier.hiddenEndpoint carrier.center hmeromorphic hnoExtension
  have hfinite :
      meromorphicOrderAt carrier.hiddenEndpoint carrier.center ≠ ⊤ :=
    ne_top_of_lt hnegative
  let orderInt : ℤ :=
    (meromorphicOrderAt carrier.hiddenEndpoint carrier.center).untop₀
  have horderInt :
      meromorphicOrderAt carrier.hiddenEndpoint carrier.center =
        (orderInt : WithTop ℤ) :=
    (WithTop.coe_untop₀_of_ne_top hfinite).symm
  have horderIntNegative : orderInt < 0 := by
    rw [horderInt] at hnegative
    exact_mod_cast hnegative
  let poleOrder : ℕ := orderInt.natAbs
  have hpolePositive : 0 < poleOrder := by
    exact Int.natAbs_pos.mpr (ne_of_lt horderIntNegative)
  have horderPole :
      meromorphicOrderAt carrier.hiddenEndpoint carrier.center =
        ((-(poleOrder : ℤ) : ℤ) : WithTop ℤ) := by
    rw [horderInt]
    congr 1
    dsimp [poleOrder]
    rw [Int.ofNat_natAbs_of_nonpos horderIntNegative.le]
    simp
  exact ⟨poleOrder, hpolePositive, horderPole, hreciprocal⟩

/-- Aggregated nonremovable cross-Julia pole-chart surface. -/
theorem analytic_cross_julia_pole_chart_terminal_certificate :
    ∀ (carrier : AnalyticCrossJuliaCarrier),
      (¬HasFiniteAnalyticExtension carrier.hiddenEndpoint carrier.center) →
      ∃ poleOrder : ℕ,
        0 < poleOrder ∧
        meromorphicOrderAt carrier.hiddenEndpoint carrier.center =
          ((-(poleOrder : ℤ) : ℤ) : WithTop ℤ) ∧
        HasAnalyticReciprocalChart carrier.hiddenEndpoint carrier.center := by
  intro carrier hnoExtension
  exact AnalyticCrossJuliaCarrier.exists_poleOrder_reciprocalChart
    carrier hnoExtension

end FormalAnalyticCrossJuliaPoleChart
