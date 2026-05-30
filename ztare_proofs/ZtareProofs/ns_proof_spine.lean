import Mathlib.Tactic
import ZtareProofs.ns_centrifugal_transversality
import ZtareProofs.ns_endogenous_orientation_instability
import ZtareProofs.ns_eigenframe_poincare_section
import ZtareProofs.ns_section_budget_bounds
import ZtareProofs.ns_section_dichotomy
import ZtareProofs.ns_time_rate_pincer
import ZtareProofs.ns_viscous_exhaust_horizon
import ZtareProofs.ns_fractal_recurrence_target

namespace ZtareProofs

/-!
`ns_proof_spine` is the assembled theorem architecture of the current NS branch.

It does not solve Navier-Stokes. It makes explicit that the branch has been
compressed to one proof spine with one rival:

* main route: local centrifugal escape -> section return object ->
  section-level gain/loss bounds -> eventual loss dominance
* rival route: profitable shrinking recurrence
-/

/--
Top-level anti-blowup route on the eigenframe section.
-/
def antiBlowupRoute
    (S : EigenframeSection) (EStar Cgain Closs : Real) (α β : Nat) : Prop :=
  eventualDangerGainUpperBound S EStar Cgain α ∧
    eventualResetLossLowerBound S EStar Closs β ∧
    (∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
      Cgain * C.entry.peak ^ α ≤ Closs * C.entry.peak ^ β)

/--
Top-level rival route: a profitable shrinking subsequence survives.
-/
def rivalFractalRoute (Seq : CycleSeq) : Prop :=
  profitableShrinkingSubsequence Seq

/--
Proof-spine dichotomy.
-/
def proofSpineDichotomy
    (S : EigenframeSection) (EStar Cgain Closs : Real) (α β : Nat) (Seq : CycleSeq) : Prop :=
  antiBlowupRoute S EStar Cgain Closs α β ∨ rivalFractalRoute Seq

/--
If the anti-blowup route is paid for, the section dichotomy resolves on the
loss-dominant side.
-/
theorem section_dichotomy_of_proof_spine_antiblowup
    {S : EigenframeSection} {EStar Cgain Closs : Real} {α β : Nat} {Seq : CycleSeq}
    (h :
      antiBlowupRoute S EStar Cgain Closs α β) :
    sectionDichotomy S EStar Seq := by
  rcases h with ⟨hgain, hloss, hdom⟩
  exact section_dichotomy_of_section_budget_bounds hgain hloss hdom

/--
If the rival route is paid for, the section dichotomy resolves on the fractal
side.
-/
theorem section_dichotomy_of_proof_spine_rival
    {S : EigenframeSection} {EStar _Cgain _Closs : Real} {_α _β : Nat} {Seq : CycleSeq}
    (h : rivalFractalRoute Seq) :
    sectionDichotomy S EStar Seq := by
  exact Or.inr h

/--
Time-rate route into the recurrence spine.

This is the current "temporal liquidation" compression: if the reset loss
dominates gain through the stretch-rate cost `mu * r^2 / T(E)`, then the
gain/loss recurrence map is strictly contractive above the same threshold.

The theorem deliberately does not prove Navier-Stokes supplies the strict
margin. It isolates that margin as the remaining PDE bridge.
-/
theorem contractive_recurrence_of_time_rate_route
    {G L : cycleGain} {mu r EStar : Real} {T : Real → Real}
    (hGpos : ∀ ⦃E : Real⦄, EStar ≤ E → 0 < G E)
    (hmargin : strictStretchCostMargin G L mu r T EStar) :
    contractiveAbove (recurrenceFromGainLoss G L) EStar := by
  exact contractive_of_exhaustHorizon
    (exhaust_horizon_of_time_rate_pincer hGpos hmargin)

/--
Weak time-rate route into the recurrence spine.

If gain and loss meet at the same stretch-rate cost scale, the induced
recurrence is non-expanding. This is weaker than strict bankruptcy, but it is
still enough to rule out a profitable recurrence above the threshold.
-/
theorem nonexpanding_recurrence_of_weak_time_rate_route
    {G L : cycleGain} {mu r EStar : Real} {T : Real → Real}
    (hGain : gainBoundedByStretchCost G mu r T EStar)
    (hLoss : lossLowerBoundedByStretchCost L mu r T EStar) :
    nonexpandingAbove (recurrenceFromGainLoss G L) EStar := by
  apply nonexpanding_of_weakExhaustHorizon
  intro E hE
  exact le_trans (hGain hE) (hLoss hE)

/--
Orientation-instability route into the recurrence spine.

If endogenous frame escape suppresses the realized danger gain below the
aligned gain by a fixed angular discount, and reset loss beats that discounted
aligned gain, then the realized gain/loss recurrence is contractive.
-/
theorem contractive_recurrence_of_orientation_instability_route
    {G0 Gθ L : cycleGain} {discount EStar : Real}
    (hsupp : angularGainSuppressed G0 Gθ discount EStar)
    (hdiscounted :
      ∀ ⦃E : Real⦄, EStar ≤ E → discount * G0 E < L E) :
    contractiveAbove (recurrenceFromGainLoss Gθ L) EStar := by
  exact contractive_recurrence_of_angular_suppression hsupp hdiscounted

/--
Final assembled target shape for the current NS branch.

This is the exact state of the proof attempt after all compressions:
either the anti-blowup route is paid for by section-level gain/loss bounds,
or a profitable shrinking-return rival remains live.
-/
theorem proof_spine_target_shape
    {S : EigenframeSection} {EStar Cgain Closs : Real} {α β : Nat} {Seq : CycleSeq}
    (h :
      proofSpineDichotomy S EStar Cgain Closs α β Seq) :
    proofSpineDichotomy S EStar Cgain Closs α β Seq := by
  exact h

end ZtareProofs
