import Mathlib.Tactic
import ZtareProofs.ns_knife_edge_gridlock_closure
import ZtareProofs.ns_landfill_dilemma
import ZtareProofs.ns_calderon_zygmund_stealth_obstruction

namespace ZtareProofs

/-!
`ns_final_gridlock_closure` is the current compressed NS proof spine.

It does not assert that the Navier-Stokes PDE obligations are solved. It states
the strongest honest endpoint now available in the Lean stack:

* knife-edge orientation escape makes the realized recurrence contractive once
  gridlock debt beats the discounted gain;
* projected pressure-Hessian footprint makes each large handoff nonzero-polluting;
* finite orientation capacity plus finite landfill capacity kills the clean
  Zeno relay.

The remaining mathematical work is exactly the PDE derivation of the obligation
record supplied to this file.
-/

/--
The final obligation record for the current gridlock route.

The first block is the recurrence/tax block. The second block is the
projected pressure-footprint / no-free-landfill block.
-/
structure FinalGridlockPDEObligations
    (GAligned GRealized L DebtTax θ : cycleGain)
    (c EStar θStar : Real)
    (Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real)
    (Vlandfill densityCap cleaned : Real)
    (Pproj : ProjectedPressureRotation) (κ pFloor : Real) : Prop where
  knifeGridlock :
    KnifeEdgeGridlockPDEObligations
      GAligned GRealized L DebtTax θ c EStar θStar
  realizedGainPositive :
    ∀ ⦃E : Real⦄, EStar ≤ E → 0 < GRealized E
  projectedPressureFootprint : projectedPressureCreatesPollution Pproj pollutedPerJump κ
  pressureCoeffPositive : 0 < κ
  projectedPressureFloorPositive : 0 < pFloor
  projectedPressureNonNull : pFloor ≤ |Pproj|
  capacityOrLandfillOverflow :
    Vtotal <
        unresolvedPollution jumpCount pollutedPerJump cleanupRate elapsedTime ∨
      (densityCap * Vlandfill + cleaned) / pollutedPerJump < jumpCount

/--
The recurrence consequence of the final obligation record.
-/
theorem contractive_recurrence_of_final_gridlock_obligations
    {GAligned GRealized L DebtTax θ : cycleGain}
    {c EStar θStar : Real}
    {Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    {Vlandfill densityCap cleaned : Real}
    {Pproj : ProjectedPressureRotation} {κ pFloor : Real}
    (h :
      FinalGridlockPDEObligations
        GAligned GRealized L DebtTax θ c EStar θStar
        Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime
        Vlandfill densityCap cleaned Pproj κ pFloor) :
    contractiveAbove (recurrenceFromGainLoss GRealized L) EStar := by
  exact contractive_recurrence_of_pde_obligations h.knifeGridlock

/--
The marginal-tax consequence of the final obligation record.
-/
theorem eventual_tax_dominance_of_final_gridlock_obligations
    {GAligned GRealized L DebtTax θ : cycleGain}
    {c EStar θStar : Real}
    {Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    {Vlandfill densityCap cleaned : Real}
    {Pproj : ProjectedPressureRotation} {κ pFloor : Real}
    (h :
      FinalGridlockPDEObligations
        GAligned GRealized L DebtTax θ c EStar θStar
        Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime
        Vlandfill densityCap cleaned Pproj κ pFloor) :
    eventualTaxDominance GRealized L EStar := by
  exact eventual_tax_dominance_of_knife_edge_gridlock
    h.realizedGainPositive
    h.knifeGridlock.knife
    h.knifeGridlock.escape
    h.knifeGridlock.alignedGainNonneg
    h.knifeGridlock.curvatureNonneg
    h.knifeGridlock.angleFloorNonneg
    h.knifeGridlock.debtBeatsDiscount
    h.knifeGridlock.resetIncludesDebt

/--
The no-free-landfill consequence of the final obligation record.

Either the projected pressure-Hessian footprint exhausts clean orientation
capacity, or the rival's attempt to aim all debt into a dirty quadrant
overflows that finite landfill.
-/
theorem no_free_landfill_of_final_gridlock_obligations
    {GAligned GRealized L DebtTax θ : cycleGain}
    {c EStar θStar : Real}
    {Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    {Vlandfill densityCap cleaned : Real}
    {Pproj : ProjectedPressureRotation} {κ pFloor : Real}
    (h :
      FinalGridlockPDEObligations
        GAligned GRealized L DebtTax θ c EStar θStar
        Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime
        Vlandfill densityCap cleaned Pproj κ pFloor) :
    orientationCapacityExceeded
        Vtotal
        (jumpCount * pollutedPerJump)
        (cleanupRate * elapsedTime) ∨
      ¬ landfillCanAbsorb jumpCount pollutedPerJump Vlandfill densityCap cleaned := by
  have hpollute : 0 < pollutedPerJump :=
    positive_pollution_of_projected_pressure_footprint
      h.pressureCoeffPositive
      h.projectedPressureFloorPositive
      h.projectedPressureNonNull
      h.projectedPressureFootprint
  exact no_free_landfill_dilemma hpollute h.capacityOrLandfillOverflow

/--
One-line final spine:
under the full obligation record, the recurrence is contractive, the marginal
tax rate eventually exceeds one, and the clean Zeno relay has no free landfill.
-/
theorem final_gridlock_spine
    {GAligned GRealized L DebtTax θ : cycleGain}
    {c EStar θStar : Real}
    {Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    {Vlandfill densityCap cleaned : Real}
    {Pproj : ProjectedPressureRotation} {κ pFloor : Real}
    (h :
      FinalGridlockPDEObligations
        GAligned GRealized L DebtTax θ c EStar θStar
        Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime
        Vlandfill densityCap cleaned Pproj κ pFloor) :
    contractiveAbove (recurrenceFromGainLoss GRealized L) EStar ∧
      eventualTaxDominance GRealized L EStar ∧
      (orientationCapacityExceeded
          Vtotal
          (jumpCount * pollutedPerJump)
          (cleanupRate * elapsedTime) ∨
        ¬ landfillCanAbsorb jumpCount pollutedPerJump Vlandfill densityCap cleaned) := by
  constructor
  · exact contractive_recurrence_of_final_gridlock_obligations h
  · constructor
    · exact eventual_tax_dominance_of_final_gridlock_obligations h
    · exact no_free_landfill_of_final_gridlock_obligations h

end ZtareProofs
