import Mathlib.Tactic
import ZtareProofs.ns_leray_gain_tax_trackb_obligation

/-!
# Track B coordinate reformulation guard

Candidate G is useful only when it is a genuine representation change of the
same Track B object: the formal system, topology, observable class, and pricing
ledger are fixed before payoff is scored.  This file records the bookkeeping
guard.  It does not create a new PDE estimate; it prevents a moving-coordinate
argument from being counted as a survivor after the no-survivor ledger has
already priced the original block.
-/

namespace ZtareProofs.NS

/-- A coordinate/reformulation receipt for the same Track B block.

The concrete PDE proof may use survival-root variables, event clocks,
phase-latency coordinates, or Fourier/LP/Bony recasts.  Such a move is
Candidate G only if the fields below are fixed before payoff and the exact
ledger coordinates are preserved. -/
structure TrackBCoordinateReformulationReceipt where
  source : FullLedgerBlock
  target : FullLedgerBlock
  source_global : IsGlobalTrackBBlock source
  target_global : IsGlobalTrackBBlock target
  formal_system_preserved : Prop
  topology_preserved_before_payoff : Prop
  observable_class_preserved_before_payoff : Prop
  pricing_ledger_preserved_before_payoff : Prop
  gamma_preserved : target.gamma = source.gamma
  cross_preserved : target.cross = source.cross
  self_tax_preserved : target.selfTax = source.selfTax
  survival_profit_preserved : target.survivalProfit = source.survivalProfit

/-- A moving-coordinate escape is the claim that the reformulated block becomes
a survivor above the sharp target after the source block has already been
priced. -/
def CoordinateReformulationSurvivor
    (R : TrackBCoordinateReformulationReceipt) : Prop :=
  sharpTarget < R.target.survivalProfit

/-- A valid coordinate reformulation preserves no-survivor status. -/
theorem target_no_survivor_of_coordinate_reformulation
    (R : TrackBCoordinateReformulationReceipt)
    (hsource : FullLedgerNoSurvivor R.source) :
    FullLedgerNoSurvivor R.target := by
  unfold FullLedgerNoSurvivor at hsource ⊢
  rw [R.survival_profit_preserved]
  exact hsource

/-- A valid coordinate reformulation cannot manufacture a survivor. -/
theorem no_coordinate_reformulation_survivor_of_source_no_survivor
    (R : TrackBCoordinateReformulationReceipt)
    (hsource : FullLedgerNoSurvivor R.source) :
    ¬ CoordinateReformulationSurvivor R := by
  intro htarget
  have hno : FullLedgerNoSurvivor R.target :=
    target_no_survivor_of_coordinate_reformulation R hsource
  unfold CoordinateReformulationSurvivor at htarget
  unfold FullLedgerNoSurvivor at hno
  exact not_lt_of_ge hno htarget

/-- Threshold-defect convexity also survives a pure coordinate reformulation.

This is useful when a proof changes variables before applying the universal
pricing theorem.  The theorem is intentionally exact: if a coordinate change
only preserves degrees or asymptotic scaling, it does not satisfy this guard. -/
theorem target_threshold_defect_of_coordinate_reformulation
    (R : TrackBCoordinateReformulationReceipt)
    (hsource : ThresholdDefectConvexity R.source) :
    ThresholdDefectConvexity R.target := by
  unfold ThresholdDefectConvexity at hsource ⊢
  rcases hsource with hle | hsuper
  · left
    rw [R.gamma_preserved]
    exact hle
  · right
    rcases hsuper with ⟨hgt, hdefect⟩
    constructor
    · rw [R.gamma_preserved]
      exact hgt
    · have hdefect_eq :
          survivalDefect R.target
              (Real.sqrt (sharpTarget / R.target.gamma)) =
            survivalDefect R.source
              (Real.sqrt (sharpTarget / R.source.gamma)) := by
        unfold survivalDefect
        rw [R.gamma_preserved, R.cross_preserved, R.self_tax_preserved]
      rw [hdefect_eq]
      exact hdefect

end ZtareProofs.NS
