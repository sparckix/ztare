import ZtareProofs.AxiomPackJacobianCriticalPuiseuxUniformization
import ZtareProofs.FormalAnalyticLinearODEContinuation

/-!
# Constructed three-disk continuation of the regularized critical holonomy

The uniformizing coefficient is holomorphic on three exact overlapping
disks.  Local exponential solutions are normalized successively at the two
overlap points; analytic linear-ODE uniqueness then derives their overlap
compatibility.
-/

namespace AxiomPackJacobianCriticalPuiseuxContinuation

open Metric Set
open AxiomPackJacobianCriticalPuiseuxUniformization
open FormalAnalyticLinearODEContinuation

/-- The selected regularized holonomy continued from `q = 1` to `q = 3`. -/
structure SelectedRegularizedContinuation where
  left : ℂ → ℂ
  middle : ℂ → ℂ
  right : ℂ → ℂ
  analytic_left :
    AnalyticOnNhd ℂ left (ball (5 / 4) (1 / 3))
  analytic_middle :
    AnalyticOnNhd ℂ middle (ball 2 (3 / 5))
  analytic_right :
    AnalyticOnNhd ℂ right (ball (11 / 4) (1 / 3))
  left_initial : left 1 = -3
  left_ode : ∀ q ∈ ball (5 / 4) (1 / 3),
    HasDerivAt left (regularizedLogDerivative q * left q) q
  middle_ode : ∀ q ∈ ball 2 (3 / 5),
    HasDerivAt middle (regularizedLogDerivative q * middle q) q
  right_ode : ∀ q ∈ ball (11 / 4) (1 / 3),
    HasDerivAt right (regularizedLogDerivative q * right q) q
  left_middle_compatible : EqOn left middle
    (ball (5 / 4) (1 / 3) ∩ ball 2 (3 / 5))
  middle_right_compatible : EqOn middle right
    (ball 2 (3 / 5) ∩ ball (11 / 4) (1 / 3))
  left_nonzero : ∀ q ∈ ball (5 / 4) (1 / 3), left q ≠ 0
  middle_nonzero : ∀ q ∈ ball 2 (3 / 5), middle q ≠ 0
  right_nonzero : ∀ q ∈ ball (11 / 4) (1 / 3), right q ≠ 0

/-- Exact construction of the selected three-disk continuation. -/
theorem exists_selectedRegularizedContinuation :
    ∃ continuation : SelectedRegularizedContinuation,
      continuation.right 3 ≠ 0 := by
  rcases selected_disk_chain_overlaps with
    ⟨hone, honeHalf, htwoHalf, hthree⟩
  obtain ⟨left, hleftAnalytic, hleftInitial, hleftODE, hleftNonzero⟩ :=
    exists_solution_on_ball (by norm_num) hone
      regularizedLogDerivative_analyticOnNhd_left (-3)
  have hleftAtOverlap : left (3 / 2) ≠ 0 :=
    hleftNonzero (by norm_num) (3 / 2) honeHalf.1
  obtain ⟨middle, hmiddleAnalytic, hmiddleInitial, hmiddleODE,
      hmiddleNonzeroFromInitial⟩ :=
    exists_solution_on_ball (by norm_num) honeHalf.2
      regularizedLogDerivative_analyticOnNhd_middle (left (3 / 2))
  have hmiddleNonzero : ∀ q ∈ ball 2 (3 / 5), middle q ≠ 0 :=
    hmiddleNonzeroFromInitial hleftAtOverlap
  have hmiddleAtOverlap : middle (5 / 2) ≠ 0 :=
    hmiddleNonzero (5 / 2) htwoHalf.1
  obtain ⟨right, hrightAnalytic, hrightInitial, hrightODE,
      hrightNonzeroFromInitial⟩ :=
    exists_solution_on_ball (by norm_num) htwoHalf.2
      regularizedLogDerivative_analyticOnNhd_right (middle (5 / 2))
  have hrightNonzero :
      ∀ q ∈ ball (11 / 4) (1 / 3), right q ≠ 0 :=
    hrightNonzeroFromInitial hmiddleAtOverlap
  have hleftMiddle : EqOn left middle
      (ball (5 / 4) (1 / 3) ∩ ball 2 (3 / 5)) := by
    apply solution_eqOn_ball_inter_ball honeHalf
    · exact regularizedLogDerivative_analyticOnNhd_left.mono inter_subset_left
    · exact hleftAnalytic.mono inter_subset_left
    · exact hmiddleAnalytic.mono inter_subset_right
    · intro q hq
      exact hleftODE q hq.1
    · intro q hq
      exact hmiddleODE q hq.2
    · exact hmiddleInitial.symm
  have hmiddleRight : EqOn middle right
      (ball 2 (3 / 5) ∩ ball (11 / 4) (1 / 3)) := by
    apply solution_eqOn_ball_inter_ball htwoHalf
    · exact regularizedLogDerivative_analyticOnNhd_middle.mono inter_subset_left
    · exact hmiddleAnalytic.mono inter_subset_left
    · exact hrightAnalytic.mono inter_subset_right
    · intro q hq
      exact hmiddleODE q hq.1
    · intro q hq
      exact hrightODE q hq.2
    · exact hrightInitial.symm
  let continuation : SelectedRegularizedContinuation :=
    { left := left
      middle := middle
      right := right
      analytic_left := hleftAnalytic
      analytic_middle := hmiddleAnalytic
      analytic_right := hrightAnalytic
      left_initial := hleftInitial
      left_ode := hleftODE
      middle_ode := hmiddleODE
      right_ode := hrightODE
      left_middle_compatible := hleftMiddle
      middle_right_compatible := hmiddleRight
      left_nonzero := hleftNonzero (by norm_num)
      middle_nonzero := hmiddleNonzero
      right_nonzero := hrightNonzero }
  exact ⟨continuation, hrightNonzero 3 hthree⟩

/-- Aggregated constructed continuation certificate. -/
theorem selected_regularized_continuation_terminal_certificate :
    ∃ continuation : SelectedRegularizedContinuation,
      continuation.left 1 = -3 ∧
      continuation.right 3 ≠ 0 ∧
      EqOn continuation.left continuation.middle
        (ball (5 / 4) (1 / 3) ∩ ball 2 (3 / 5)) ∧
      EqOn continuation.middle continuation.right
        (ball 2 (3 / 5) ∩ ball (11 / 4) (1 / 3)) := by
  obtain ⟨continuation, hterminal⟩ :=
    exists_selectedRegularizedContinuation
  exact ⟨continuation, continuation.left_initial, hterminal,
    continuation.left_middle_compatible,
    continuation.middle_right_compatible⟩

end AxiomPackJacobianCriticalPuiseuxContinuation
