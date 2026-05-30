import Mathlib.Tactic
import ZtareProofs.ns_endogenous_orientation_instability
import ZtareProofs.ns_topological_gridlock

namespace ZtareProofs

/-!
`ns_knife_edge_gridlock_closure` is the post-5AL NS handoff.

The gp163d/AQUAL ladder did not prove a gravitational theorem. Its useful
payload is the proof architecture: the profitable orientation is a knife-edge,
so any endogenous orientation escape discounts gain while the exported debt
column remains live. In the NS spine, the candidate endogenous escape driver is
the `-Ω²` strain-frame rotation channel already isolated in
`ns_centrifugal_transversality`.

This file does not prove Navier-Stokes supplies the hard PDE premises. It
composes the formal consequences once those premises are supplied:

1. angular gain decays away from perfect alignment;
2. endogenous escape forces a nonzero angle floor;
3. the discounted gain is beaten by reused-frame / halo debt;
4. reset loss includes that debt;
5. the recurrence map is contractive above the threshold.
-/

/--
The "knife-edge" premise: the perfectly aligned gain envelope loses efficiency
once the state has escaped by an angle `θ E`.

This is an alias of the existing quadratic angular-decay law, kept here to name
the Phase 5AL handoff explicitly.
-/
def knifeEdgeGainDecay
    (GAligned GRealized θ : Real → Real) (c EStar : Real) : Prop :=
  quadraticAngularGainDecay GAligned GRealized θ c EStar

/--
The debt margin required after the knife-edge discount:
the gridlock/halo debt beats the discounted aligned gain.
-/
def discountedGainBeatenByGridlockDebt
    (GAligned DebtTax : cycleGain) (discount EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → discount * GAligned E < DebtTax E

/--
The core closure theorem:

If orientation escape turns the aligned gain into a discounted realized gain,
and the gridlock debt beats that discounted gain, then reset loss dominates the
realized recurrence. This is the formal version of:

`knife-edge profit -> forced misalignment -> dirty-frame debt -> contractive cycle`.
-/
theorem contractive_recurrence_of_knife_edge_gridlock
    {GAligned GRealized L DebtTax θ : cycleGain}
    {c EStar θStar : Real}
    (hknife : knifeEdgeGainDecay GAligned GRealized θ c EStar)
    (hescape : angularEscapeLowerBound θ EStar θStar)
    (hGAligned_nonneg : ∀ ⦃E : Real⦄, EStar ≤ E → 0 ≤ GAligned E)
    (hc : 0 ≤ c)
    (hθStar_nonneg : 0 ≤ θStar)
    (hdebt :
      discountedGainBeatenByGridlockDebt
        GAligned DebtTax (angularDiscount c θStar) EStar)
    (hinclude : resetLossIncludesGridlockDebt L DebtTax EStar) :
    contractiveAbove (recurrenceFromGainLoss GRealized L) EStar := by
  have hsupp :
      angularGainSuppressed GAligned GRealized (angularDiscount c θStar) EStar :=
    angular_gain_suppressed_of_quadratic_escape
      hknife hescape hGAligned_nonneg hc hθStar_nonneg
  apply contractive_recurrence_of_topological_gridlock
    (Grelay := GRealized) (L := L) (DebtTax := DebtTax) (EStar := EStar)
  · intro E hE
    exact lt_of_le_of_lt (hsupp hE) (hdebt hE)
  · exact hinclude

/--
Marginal-tax form of the same closure:
under the knife-edge gridlock premises, the realized marginal tax rate
eventually exceeds one, provided realized gain stays positive.
-/
theorem eventual_tax_dominance_of_knife_edge_gridlock
    {GAligned GRealized L DebtTax θ : cycleGain}
    {c EStar θStar : Real}
    (hGRealized_pos : ∀ ⦃E : Real⦄, EStar ≤ E → 0 < GRealized E)
    (hknife : knifeEdgeGainDecay GAligned GRealized θ c EStar)
    (hescape : angularEscapeLowerBound θ EStar θStar)
    (hGAligned_nonneg : ∀ ⦃E : Real⦄, EStar ≤ E → 0 ≤ GAligned E)
    (hc : 0 ≤ c)
    (hθStar_nonneg : 0 ≤ θStar)
    (hdebt :
      discountedGainBeatenByGridlockDebt
        GAligned DebtTax (angularDiscount c θStar) EStar)
    (hinclude : resetLossIncludesGridlockDebt L DebtTax EStar) :
    eventualTaxDominance GRealized L EStar := by
  intro E hE
  have hcontract :
      contractiveAbove (recurrenceFromGainLoss GRealized L) EStar :=
    contractive_recurrence_of_knife_edge_gridlock
      hknife hescape hGAligned_nonneg hc hθStar_nonneg hdebt hinclude
  unfold recurrenceFromGainLoss contractiveAbove at hcontract
  have hloss : GRealized E < L E := by
    have hstep := hcontract hE
    linarith
  unfold marginalTaxRate
  exact (one_lt_div (hGRealized_pos hE)).2 hloss

/--
The exact remaining PDE obligations.

This is not used as an axiom; it is a named checklist object for the next Lean
work. To turn the closure theorem into a Navier-Stokes theorem, the PDE side
must supply these premises from the equations rather than from empirical trace
data.
-/
structure KnifeEdgeGridlockPDEObligations
    (GAligned GRealized L DebtTax θ : cycleGain)
    (c EStar θStar : Real) : Prop where
  knife : knifeEdgeGainDecay GAligned GRealized θ c EStar
  escape : angularEscapeLowerBound θ EStar θStar
  alignedGainNonneg : ∀ ⦃E : Real⦄, EStar ≤ E → 0 ≤ GAligned E
  curvatureNonneg : 0 ≤ c
  angleFloorNonneg : 0 ≤ θStar
  debtBeatsDiscount :
    discountedGainBeatenByGridlockDebt
      GAligned DebtTax (angularDiscount c θStar) EStar
  resetIncludesDebt : resetLossIncludesGridlockDebt L DebtTax EStar

/--
Compressed theorem from the obligation record.
-/
theorem contractive_recurrence_of_pde_obligations
    {GAligned GRealized L DebtTax θ : cycleGain}
    {c EStar θStar : Real}
    (h :
      KnifeEdgeGridlockPDEObligations
        GAligned GRealized L DebtTax θ c EStar θStar) :
    contractiveAbove (recurrenceFromGainLoss GRealized L) EStar := by
  exact contractive_recurrence_of_knife_edge_gridlock
    h.knife h.escape h.alignedGainNonneg h.curvatureNonneg
    h.angleFloorNonneg h.debtBeatsDiscount h.resetIncludesDebt

end ZtareProofs
