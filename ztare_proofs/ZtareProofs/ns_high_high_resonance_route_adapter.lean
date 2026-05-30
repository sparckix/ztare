import Mathlib.Tactic
import ZtareProofs.ns_high_high_self_tax_charging_obligation
import ZtareProofs.ns_mixed_self_resonance_partition

/-!
# High-high resonance route adapter

The high-high branch split is now precise enough to state as a receipt:

* nonresonant mixed/self output supports have zero cross term and only need the
  fixed root self-tax floor;
* resonant supports may carry negative cross and must pay the stronger
  cross-aware allowance.

This is deliberately an adapter.  It does not assert the PDE estimate that
supplies the floors; it records exactly what such an estimate must pay before
the branch can be scored.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Nonresonant high-high receipt.

The support equality is part of the receipt so the cross term is not defined
after seeing the payoff.  Once the fixed supports are nonresonant, Lean derives
`block.cross = 0` from the support partition. -/
structure HighHighNonresonantRootFloorReceipt where
  highSupport : List Int
  lowSupport : List Int
  mixedResidual : Int → Real
  selfResidual : Int → Real
  block : FullLedgerBlock
  positive_gamma : 0 < block.gamma
  above_wall : sharpTarget < block.gamma
  no_resonance : NoMixedSelfResonance highSupport lowSupport
  cross_eq_support_cross :
    block.cross =
      supportCrossSum
        (pairSumSupport highSupport lowSupport)
        (pairSumSupport highSupport highSupport)
        mixedResidual selfResidual
  self_tax_floor :
    let x : Real := Real.sqrt (sharpTarget / block.gamma)
    (1 - x ^ (2 : Nat)) / x ^ (4 : Nat) ≤ block.selfTax

/-- The nonresonant receipt really forces zero mixed/self cross. -/
theorem high_high_cross_zero_of_nonresonant_receipt
    (R : HighHighNonresonantRootFloorReceipt) :
    R.block.cross = 0 := by
  rw [R.cross_eq_support_cross]
  exact mixed_self_cross_zero_of_no_resonance
    R.highSupport R.lowSupport R.mixedResidual R.selfResidual R.no_resonance

/-- Nonresonant high-high branches are paid once the fixed self-tax floor is
available. -/
theorem threshold_defect_of_nonresonant_root_floor_receipt
    (R : HighHighNonresonantRootFloorReceipt) :
    ThresholdDefectConvexity R.block :=
  threshold_defect_convexity_of_cross_zero_root_floor
    R.block R.positive_gamma R.above_wall
    (high_high_cross_zero_of_nonresonant_receipt R)
    R.self_tax_floor

/-- Nonresonant receipt falsifier: if the exact root self-tax floor is short,
the claimed nonresonant receipt is impossible. -/
theorem no_nonresonant_root_floor_receipt_of_shortfall
    (R : HighHighNonresonantRootFloorReceipt)
    (hshort :
      R.block.selfTax <
        let x : Real := Real.sqrt (sharpTarget / R.block.gamma)
        (1 - x ^ (2 : Nat)) / x ^ (4 : Nat)) :
    False := by
  exact not_lt_of_ge R.self_tax_floor hshort

/-- Resonant high-high receipt.

Resonance is not forbidden by support algebra; the receipt therefore requires
the exact cross-aware allowance at the Track B root. -/
structure HighHighResonantRootChargeReceipt where
  block : FullLedgerBlock
  positive_gamma : 0 < block.gamma
  above_wall : sharpTarget < block.gamma
  cross_aware_allowance :
    let x : Real := Real.sqrt (sharpTarget / block.gamma)
    (1 - x ^ (2 : Nat) - 2 * block.cross * x ^ (3 : Nat)) /
        x ^ (4 : Nat) ≤ block.selfTax

/-- Resonant high-high branches are paid by the stronger cross-aware receipt. -/
theorem threshold_defect_of_resonant_root_charge_receipt
    (R : HighHighResonantRootChargeReceipt) :
    ThresholdDefectConvexity R.block :=
  threshold_defect_convexity_of_cross_aware_root_allowance
    R.block R.positive_gamma R.above_wall R.cross_aware_allowance

/-- Resonant receipt falsifier: if the cross-aware allowance at the Track B
root is short, the claimed resonant receipt is impossible. -/
theorem no_resonant_root_charge_receipt_of_shortfall
    (R : HighHighResonantRootChargeReceipt)
    (hshort :
      R.block.selfTax <
        let x : Real := Real.sqrt (sharpTarget / R.block.gamma)
        (1 - x ^ (2 : Nat) - 2 * R.block.cross * x ^ (3 : Nat)) /
          x ^ (4 : Nat)) :
    False := by
  exact not_lt_of_ge R.cross_aware_allowance hshort

/-- A concrete additive-overlap witness negates the nonresonant branch. -/
theorem not_no_resonance_of_resonance_witness
    {highSupport lowSupport : List Int}
    (hwitness :
      ∃ h ∈ highSupport, ∃ l ∈ lowSupport,
        ∃ h₁ ∈ highSupport, ∃ h₂ ∈ highSupport, h + l = h₁ + h₂) :
    ¬ NoMixedSelfResonance highSupport lowSupport := by
  intro hno
  rcases hwitness with ⟨h, hh, l, hl, h₁, hh₁, h₂, hh₂, heq⟩
  exact hno h hh l hl h₁ hh₁ h₂ hh₂ heq

/-- Any strict above-wall branch that reaches the Track B threshold root has
already paid the cross-aware self-tax allowance.

This is the converse algebraic receipt to
`threshold_defect_convexity_of_cross_aware_root_allowance`: the allowance is
not an optional sufficient condition.  It is forced by threshold-root escape. -/
theorem cross_aware_allowance_of_threshold_root_escape
    (B : FullLedgerBlock)
    (hgamma : 0 < B.gamma)
    (_hgt : sharpTarget < B.gamma)
    (hdefect :
      1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma))) :
    let x : Real := Real.sqrt (sharpTarget / B.gamma)
    (1 - x ^ (2 : Nat) - 2 * B.cross * x ^ (3 : Nat)) /
        x ^ (4 : Nat) ≤ B.selfTax := by
  let x : Real := Real.sqrt (sharpTarget / B.gamma)
  have htarget_pos : 0 < sharpTarget := by
    norm_num [sharpTarget]
  have hratio_pos : 0 < sharpTarget / B.gamma :=
    div_pos htarget_pos hgamma
  have hx : 0 < x := by
    dsimp [x]
    exact Real.sqrt_pos.2 hratio_pos
  have hx4 : 0 < x ^ (4 : Nat) := pow_pos hx 4
  have hraw :
      1 ≤ x ^ (2 : Nat) + 2 * B.cross * x ^ (3 : Nat) +
        B.selfTax * x ^ (4 : Nat) := by
    simpa [x, survivalDefect] using hdefect
  have hnum :
      1 - x ^ (2 : Nat) - 2 * B.cross * x ^ (3 : Nat) ≤
        B.selfTax * x ^ (4 : Nat) := by
    nlinarith
  exact (div_le_iff₀ hx4).2 hnum

/-- Strict resonant escape attempt.

This is a falsifier-facing object, not a successful route certificate.  It
requires actual additive support overlap, an above-wall block, the fixed
support interpretation of the mixed/self cross term, and threshold-root
escape.  Lean then derives the cross-aware allowance; a shortfall breaks the
attempt. -/
structure HighHighResonantStrictEscapeAttempt where
  highSupport : List Int
  lowSupport : List Int
  mixedResidual : Int → Real
  selfResidual : Int → Real
  block : FullLedgerBlock
  positive_gamma : 0 < block.gamma
  above_wall : sharpTarget < block.gamma
  resonance_witness :
    ∃ h ∈ highSupport, ∃ l ∈ lowSupport,
      ∃ h₁ ∈ highSupport, ∃ h₂ ∈ highSupport, h + l = h₁ + h₂
  cross_eq_support_cross :
    block.cross =
      supportCrossSum
        (pairSumSupport highSupport lowSupport)
        (pairSumSupport highSupport highSupport)
        mixedResidual selfResidual
  threshold_escape :
    1 ≤ survivalDefect block (Real.sqrt (sharpTarget / block.gamma))

/-- A strict resonant escape attempt is genuinely outside the nonresonant
support branch. -/
theorem not_no_resonance_of_resonant_strict_escape_attempt
    (A : HighHighResonantStrictEscapeAttempt) :
    ¬ NoMixedSelfResonance A.highSupport A.lowSupport :=
  not_no_resonance_of_resonance_witness A.resonance_witness

/-- The mandatory cross-aware payment extracted from a strict resonant escape
attempt. -/
theorem cross_aware_allowance_of_resonant_strict_escape_attempt
    (A : HighHighResonantStrictEscapeAttempt) :
    let x : Real := Real.sqrt (sharpTarget / A.block.gamma)
    (1 - x ^ (2 : Nat) - 2 * A.block.cross * x ^ (3 : Nat)) /
        x ^ (4 : Nat) ≤ A.block.selfTax :=
  cross_aware_allowance_of_threshold_root_escape
    A.block A.positive_gamma A.above_wall A.threshold_escape

/-- A strict resonant escape attempt automatically provides the resonant root
charge receipt; the only remaining PDE burden is producing the fixed
threshold-root escape object itself. -/
def resonant_root_charge_receipt_of_strict_escape_attempt
    (A : HighHighResonantStrictEscapeAttempt) :
    HighHighResonantRootChargeReceipt where
  block := A.block
  positive_gamma := A.positive_gamma
  above_wall := A.above_wall
  cross_aware_allowance :=
    cross_aware_allowance_of_resonant_strict_escape_attempt A

/-- Falsifier interface for the remaining high-high resonant gap: an actual
resonant above-wall threshold escape whose self-tax is still below the
cross-aware allowance. -/
structure HighHighResonantStrictEscapeShortfallFalsifier where
  attempt : HighHighResonantStrictEscapeAttempt
  self_tax_shortfall :
    attempt.block.selfTax <
      let x : Real := Real.sqrt (sharpTarget / attempt.block.gamma)
      (1 - x ^ (2 : Nat) - 2 * attempt.block.cross * x ^ (3 : Nat)) /
        x ^ (4 : Nat)

/-- No strict above-wall resonant escape can both reach the threshold root and
underpay the cross-aware self-tax allowance. -/
theorem no_resonant_strict_escape_shortfall_falsifier
    (F : HighHighResonantStrictEscapeShortfallFalsifier) :
    False := by
  exact not_lt_of_ge
    (cross_aware_allowance_of_resonant_strict_escape_attempt F.attempt)
    F.self_tax_shortfall

/-- Complete high-high route certificate at the current proof frontier.

The certificate keeps the anti-tautology split explicit: a branch is either
below the `2/3` wall, nonresonant with a predeclared self-tax floor, or
resonant with a predeclared cross-aware allowance. -/
inductive HighHighResonanceRoute : FullLedgerBlock → Prop
  | wall_or_below (B : FullLedgerBlock) :
      B.gamma ≤ sharpTarget → HighHighResonanceRoute B
  | nonresonant (R : HighHighNonresonantRootFloorReceipt) :
      HighHighResonanceRoute R.block
  | resonant (R : HighHighResonantRootChargeReceipt) :
      HighHighResonanceRoute R.block

/-- The resonance route split supplies threshold-defect convexity. -/
theorem threshold_defect_of_high_high_resonance_route
    (B : FullLedgerBlock)
    (R : HighHighResonanceRoute B) :
    ThresholdDefectConvexity B := by
  cases R with
  | wall_or_below _ hbelow =>
      exact Or.inl hbelow
  | nonresonant H =>
      exact threshold_defect_of_nonresonant_root_floor_receipt H
  | resonant H =>
      exact threshold_defect_of_resonant_root_charge_receipt H

/-- If the global quartic theorem is available, the explicit high-high
resonance route certificate prices the branch. -/
theorem high_high_no_survivor_of_resonance_route
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (R : HighHighResonanceRoute B) :
    FullLedgerNoSurvivor B :=
  hquartic B (threshold_defect_of_high_high_resonance_route B R)

/-- Projection-typed high-high route adapter.

This is the closure-facing form: the resonance split may supply the threshold
defect, but survival-profit exclusion must pass through the same-ledger
quartic survival projection. -/
theorem high_high_no_survivor_of_resonance_route_with_projection
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (R : HighHighResonanceRoute B) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (threshold_defect_of_high_high_resonance_route B R)

end

end ZtareProofs.NS
