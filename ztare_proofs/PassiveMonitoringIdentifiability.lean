import Mathlib

namespace StrategicReporting

/-- Two states are observationally equivalent for a deterministic report channel
exactly when the channel emits the same complete report for each of them. -/
def ObservationallyEquivalent
    {State Report : Type*} (report : State → Report) (x0 x1 : State) : Prop :=
  report x0 = report x1

-- @denotation-anchor: anchor=anchor_observationallyEquivalent_iff; target=ObservationallyEquivalent; kind=definitional; external=Lean.Init.Prelude.Eq
theorem anchor_observationallyEquivalent_iff
    {State Report : Type*} (report : State → Report) (x0 x1 : State) :
    ObservationallyEquivalent report x0 x1 ↔ Eq (report x0) (report x1) := Iff.rfl

/-- Observational equivalence is reflexive on every complete report channel. -/
theorem observationallyEquivalent_refl
    {State Report : Type*} (report : State → Report) (x : State) :
    ObservationallyEquivalent report x x := rfl

/-- A deterministic report-only estimator has equal outputs on observationally
equivalent states. -/
theorem ObservationallyEquivalent.estimate_eq
    {State Report : Type*} {report : State → Report} {x0 x1 : State}
    (hobs : ObservationallyEquivalent report x0 x1) (estimate : Report → Real) :
    estimate (report x0) = estimate (report x1) := by
  exact congrArg estimate hobs

/-- The absolute loss of a deterministic report-only estimator at a latent state. -/
def passiveAbsoluteError
    {State Report : Type*} (report : State → Report) (target : State → Real)
    (estimate : Report → Real) (x : State) : Real :=
  |estimate (report x) - target x|

-- @denotation-anchor: anchor=anchor_passiveAbsoluteError_eq_abs_sub; target=passiveAbsoluteError; kind=definitional; external=abs
theorem anchor_passiveAbsoluteError_eq_abs_sub
    {State Report : Type*} (report : State → Report) (target : State → Real)
    (estimate : Report → Real) (x : State) :
    passiveAbsoluteError report target estimate x = |estimate (report x) - target x| := rfl

/-- The direct absolute-loss definition gives zero error for a zero target and
zero estimator. -/
theorem passiveAbsoluteError_zero_estimator_zero_target
    {State Report : Type*} (report : State → Report) (x : State) :
    passiveAbsoluteError report (fun _ => 0) (fun _ => 0) x = 0 := by
  simp [passiveAbsoluteError]

/-- If two latent states generate the same complete passive report, no
deterministic estimator using only that report can have absolute error smaller
than half their target separation at both states. -/
theorem observationalEquivalence_passiveLowerBound
    {State Report : Type*}
    (report : State → Report)
    (target : State → Real)
    (estimate : Report → Real)
    (x0 x1 : State)
    (hobs : report x0 = report x1) :
    |target x0 - target x1| / 2 <=
      max |estimate (report x0) - target x0|
          |estimate (report x1) - target x1| := by
  let a := estimate (report x0)
  have hestimate : a = estimate (report x1) := by
    dsimp [a]
    exact congrArg estimate hobs
  have htriangle :
      |target x0 - target x1| ≤ |a - target x0| + |a - target x1| := by
    calc
      |target x0 - target x1| = |(target x0 - a) + (a - target x1)| := by
        congr 1
        ring
      _ ≤ |target x0 - a| + |a - target x1| := abs_add_le _ _
      _ = |a - target x0| + |a - target x1| := by
        rw [abs_sub_comm]
  have hleft :
      |a - target x0| ≤
        max |estimate (report x0) - target x0|
            |estimate (report x1) - target x1| := by
    change |estimate (report x0) - target x0| ≤ _
    exact le_max_left _ _
  have hright :
      |a - target x1| ≤
        max |estimate (report x0) - target x0|
            |estimate (report x1) - target x1| := by
    rw [hestimate]
    exact le_max_right _ _
  linarith

/-- The same lower bound stated through the reusable absolute-error API. -/
theorem observationalEquivalence_passiveLowerBound_error
    {State Report : Type*}
    (report : State → Report)
    (target : State → Real)
    (estimate : Report → Real)
    (x0 x1 : State)
    (hobs : ObservationallyEquivalent report x0 x1) :
    |target x0 - target x1| / 2 ≤
      max (passiveAbsoluteError report target estimate x0)
          (passiveAbsoluteError report target estimate x1) := by
  simpa [passiveAbsoluteError] using
    observationalEquivalence_passiveLowerBound report target estimate x0 x1 hobs

end StrategicReporting
