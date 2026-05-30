import Mathlib.Tactic

/-!
# Phase latency control-Gramian receipt

This is an abstract receipt for the Phase 5JL-5JO latency facts, not a
Navier-Stokes theorem.

Scientific verdict recorded in Lean terms:

* A controllability/minimum-time receipt can instantiate the Track B
  phase-alignment latency theorem only if the Gramian is a fixed
  pre-payoff map from a macroscopic vorticity/Lipschitz control budget to
  phase reach on a parabolic window.
* Under the Phase 5JO low-high scaling, the fixed-topology parabolic-window
  reach has size `O(1 / |k|)` per unit macroscopic budget.  If
  `theta_j >= c / j`, then the required budget is `Omega(|k_j| / j)`.
* The pure L2 minimum-energy Gramian is not enough: with
  `Delta t_j ~= |k_j|^-2` and required low Lipschitz `~= |k_j| / j`, the
  action-only term can be `~ 1 / j^2`.  A proof-facing theorem therefore
  needs an explicit conversion from the Gramian control to the BKM /
  macroscopic vorticity reserve or positive-Gram catalyst ledger.

The assumptions below are deliberately explicit.  The hard PDE obligation is
to instantiate `parabolic_low_high_capacity` from a fixed LP/Bony/Leray
symbol estimate and to identify `controlBudget` with a genuine BKM or
macroscopic-vorticity reserve, not with an after-the-fact fitted control.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Abstract fixed-topology phase-reach receipt.

`reach j` is the scalar phase reach per unit control budget on block `j`.
The key non-tautological analytic input is
`reach j * kNorm j <= gramianConstant`: on a parabolic window
`Delta t_j ~= |k_j|^-2`, a fixed low-high topology gives only `O(1 / |k_j|)`
phase reach per unit macroscopic control budget.

No field below asserts Navier-Stokes regularity or existence of a smooth NSE
trajectory. -/
structure PhaseLatencyControlGramianReceipt where
  theta : ℕ → Real
  kNorm : ℕ → Real
  harmonicIndex : ℕ → Real
  controlBudget : ℕ → Real
  reach : ℕ → Real
  angleConstant : Real
  gramianConstant : Real
  theta_nonnegative : ∀ j : ℕ, 0 ≤ theta j
  k_nonnegative : ∀ j : ℕ, 0 ≤ kNorm j
  harmonic_nonnegative : ∀ j : ℕ, 0 ≤ harmonicIndex j
  budget_nonnegative : ∀ j : ℕ, 0 ≤ controlBudget j
  reach_nonnegative : ∀ j : ℕ, 0 ≤ reach j
  angle_constant_nonnegative : 0 ≤ angleConstant
  gramian_constant_nonnegative : 0 ≤ gramianConstant
  /-- Phase delivered by a block cannot exceed budget times fixed reach. -/
  phase_reach_bound :
    ∀ j : ℕ, theta j ≤ controlBudget j * reach j
  /-- Fixed-topology parabolic-window Gramian/symbol capacity. -/
  parabolic_low_high_capacity :
    ∀ j : ℕ, reach j * kNorm j ≤ gramianConstant
  /-- Phase 5JL-5JO harmonic-angle requirement: `theta_j >= c / j`. -/
  harmonic_angle_lower :
    ∀ j : ℕ, angleConstant ≤ theta j * harmonicIndex j

/-- Control budget lower bound forced by a fixed parabolic Gramian capacity.

Read as: if `harmonicIndex j` is comparable to `j` and `kNorm j = |k_j|`,
then a harmonic phase angle on a parabolic window requires control budget
`>= const * |k_j| / j`.  This is the proof-facing rate-reserve receipt.
-/
theorem control_budget_rate_reserve_lower_bound
    (R : PhaseLatencyControlGramianReceipt)
    (j : ℕ) :
    R.angleConstant * R.kNorm j ≤
      (R.controlBudget j * R.gramianConstant) * R.harmonicIndex j := by
  have hphase_scaled :
      R.theta j * R.kNorm j ≤
        (R.controlBudget j * R.reach j) * R.kNorm j := by
    exact mul_le_mul_of_nonneg_right
      (R.phase_reach_bound j)
      (R.k_nonnegative j)
  have hphase_budget :
      R.theta j * R.kNorm j ≤
        R.controlBudget j * R.gramianConstant := by
    have hcap_budget :
        R.controlBudget j * (R.reach j * R.kNorm j) ≤
          R.controlBudget j * R.gramianConstant := by
      exact mul_le_mul_of_nonneg_left
        (R.parabolic_low_high_capacity j)
        (R.budget_nonnegative j)
    nlinarith [hphase_scaled, hcap_budget]
  have hphase_budget_harmonic :
      (R.theta j * R.kNorm j) * R.harmonicIndex j ≤
        (R.controlBudget j * R.gramianConstant) *
          R.harmonicIndex j := by
    exact mul_le_mul_of_nonneg_right
      hphase_budget
      (R.harmonic_nonnegative j)
  have hangle_scaled :
      R.angleConstant * R.kNorm j ≤
        (R.theta j * R.harmonicIndex j) * R.kNorm j := by
    exact mul_le_mul_of_nonneg_right
      (R.harmonic_angle_lower j)
      (R.k_nonnegative j)
  nlinarith

/-- Divided rate-reserve form of the parabolic phase-latency obstruction.

This is the explicit `|k_j| / j`-style lower-bound surface: whenever the
Gramian denominator is strictly positive, the macroscopic control budget must
dominate the required angle-frequency product divided by that denominator. -/
theorem control_budget_divided_rate_reserve_lower_bound
    (R : PhaseLatencyControlGramianReceipt)
    (j : ℕ)
    (hden : 0 < R.gramianConstant * R.harmonicIndex j) :
    (R.angleConstant * R.kNorm j) /
        (R.gramianConstant * R.harmonicIndex j) ≤
      R.controlBudget j := by
  have h :=
    control_budget_rate_reserve_lower_bound R j
  have hrewrite :
      (R.controlBudget j * R.gramianConstant) *
          R.harmonicIndex j =
        R.controlBudget j *
          (R.gramianConstant * R.harmonicIndex j) := by
    ring
  rw [hrewrite] at h
  exact (div_le_iff₀ hden).2 h

/-- Bounded macroscopic control cannot support a shell whose required
`|k| / j` lower bound already exceeds the available reserve.

This is the finite-shell falsifier form: a candidate Track B latency escape
must either violate one receipt assumption, enlarge the macroscopic control
budget, or abandon the harmonic-angle/parabolic-window target.
-/
theorem no_bounded_control_budget_fast_alignment_at_shell
    (R : PhaseLatencyControlGramianReceipt)
    (j : ℕ)
    {B : Real}
    (hbudget : R.controlBudget j ≤ B)
    (hviol :
      (B * R.gramianConstant) * R.harmonicIndex j <
        R.angleConstant * R.kNorm j) :
    False := by
  have hreserve :
      R.angleConstant * R.kNorm j ≤
        (R.controlBudget j * R.gramianConstant) *
          R.harmonicIndex j :=
    control_budget_rate_reserve_lower_bound R j
  have hbudget_scaled :
      (R.controlBudget j * R.gramianConstant) *
          R.harmonicIndex j ≤
        (B * R.gramianConstant) * R.harmonicIndex j := by
    have h1 :
        R.controlBudget j * R.gramianConstant ≤
          B * R.gramianConstant := by
      exact mul_le_mul_of_nonneg_right
        hbudget
        R.gramian_constant_nonnegative
    exact mul_le_mul_of_nonneg_right
      h1
      (R.harmonic_nonnegative j)
  exact not_lt_of_ge (hreserve.trans hbudget_scaled) hviol

/-- Uniform-budget cascade exclusion.

If a proposed dyadic/harmonic schedule has shells where
`angleConstant * |k_j|` eventually exceeds every fixed macroscopic budget times
the parabolic reach denominator `gramianConstant * harmonicIndex j`, then no
single finite budget can realize the whole schedule.  This is the countable
version of the Phase 5JO obstruction. -/
theorem no_uniform_control_budget_for_unbounded_phase_latency_schedule
    (R : PhaseLatencyControlGramianReceipt)
    {B : Real}
    (hbudget : ∀ j : ℕ, R.controlBudget j ≤ B)
    (hunbounded_requirement :
      ∀ C : Real, ∃ j : ℕ,
        (C * R.gramianConstant) * R.harmonicIndex j <
          R.angleConstant * R.kNorm j) :
    False := by
  obtain ⟨j, hj⟩ := hunbounded_requirement B
  exact
    no_bounded_control_budget_fast_alignment_at_shell
      R j (hbudget j) hj

/-- Separate marker for the Phase 5JO action-only lane.

This object is intentionally not enough to build
`PhaseLatencyControlGramianReceipt`.  It records the discovered failure mode:
an L2/action minimum-energy lower bound may be finite while the pointwise
macroscopic catalyst/vorticity amplitude needed to realize the parabolic
phase rotation is unbounded.
-/
structure EnergyOnlyGramianLane where
  actionEnergy : ℕ → Real
  macroscopicBudget : ℕ → Real
  action_nonnegative : ∀ j : ℕ, 0 ≤ actionEnergy j
  macroscopic_budget_nonnegative : ∀ j : ℕ, 0 ≤ macroscopicBudget j
  action_prefix_finite_receipt : Prop
  lacks_action_to_macroscopic_budget_conversion : Prop

/-- The action-only Gramian lane is not a rate-reserve receipt unless an
extra theorem converts action energy into the macroscopic BKM/vorticity
budget priced by `PhaseLatencyControlGramianReceipt`. -/
def energy_only_lane_not_control_budget_receipt
    (E : EnergyOnlyGramianLane) : Prop :=
  E.lacks_action_to_macroscopic_budget_conversion

end

end ZtareProofs.NS
