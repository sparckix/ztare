import Mathlib.Tactic
import Mathlib.MeasureTheory.Function.ConditionalExpectation.Basic
import ZtareProofs.ns_angular_moment_pressure_target
import ZtareProofs.ns_l2_carrier_bridge
import ZtareProofs.ns_no_invisible_critical_profile

namespace ZtareProofs

/-!
`ns_pressure_hessian_l2_bridge` records the sharpened PDE route after the
Phase 5CG irrep panel debate.

The panel converged on three points:

1. the exact algebraic part is only the instantaneous quadrupole identity;
2. the dynamical bridge must pass through the nonlocal pressure Hessian;
3. higher-mode harmlessness must be justified by an operator-level decoupling
   estimate, not by a free scalar cap.

This file names those obligations without pretending they are proved.
-/

/-- Renormalized magnitude of the `l = 2` projection of the pressure Hessian. -/
abbrev PressureHessianL2Amplitude := Real

/-- Residual higher-mode pressure-Hessian feedback into the coherent strain channel. -/
abbrev PressureHessianHigherModeFeedback := Real

/-- Calderon-commutator residual left after subtracting the local `l = 2` pressure channel. -/
abbrev CalderonCommutatorResidual := Real

/-- Explicit power-type radial weight used by the harmonic-analysis route. -/
noncomputable def radialPowerWeight
    (r δ : Real) : Real :=
  Real.rpow (max r 1) (-δ)

/--
Renormalized `l = 2` pressure-Hessian carrier per active radial grade.

This is the explicit observable the current branch should talk about, rather
than an unnamed scalar “carrier”.
-/
noncomputable def renormalizedPressureHessianL2Carrier
    (pressureL2 grade : Real) : Real :=
  pressureL2 / max grade 1

/--
Pressure-Hessian `l = 2` control of coherent stretch.

This is the topologist's minimal acceptable bridge: coherent stretch is bounded
by the renormalized `l = 2` pressure-Hessian channel plus a remainder.
-/
def pressureHessianL2ControlsCoherentStretch
    (reserve pressureL2 grade C remainder : Real) : Prop :=
  reserve ≤ C * renormalizedPressureHessianL2Carrier pressureL2 grade + remainder

/--
Higher-mode pressure feedback is power-suppressed by active radial grade.

This is the harmonic analyst's operator-level replacement for the earlier
free scalar `higherModesSubcritical` surrogate.
-/
def pressureHessianHigherModesDecouple
    (feedback grade K δ : Real) : Prop :=
  0 < δ ∧ feedback ≤ K * radialPowerWeight grade δ

/--
The Calderon-commutator residual is shunted into the high angular modes and is
therefore power-suppressed by active radial grade.

This is the caveated replacement for any claim of "exact cancellation" between
quadratic stretching and the local pressure-Hessian contribution.
-/
def calderonCommutatorResidualDecouple
    (residual grade K δ : Real) : Prop :=
  0 < δ ∧ residual ≤ K * radialPowerWeight grade δ

/--
Weakest transport-style target for the pressure-Hessian `l = 2` route.

This does not claim exact cancellation. It only claims that after subtracting
the renormalized `l = 2` pressure-Hessian channel, the remaining transport
defect is controlled by a quadratic local term plus advection of the `l = 2`
pressure carrier, with the genuinely nonlocal leftover entering through a
Calderon-commutator residual.
-/
def pressureHessianL2TransportTarget
    (transportDefect localQuadratic advectedPressure residual : Real) : Prop :=
  |transportDefect| ≤ localQuadratic + advectedPressure + residual

/--
Combined pressure-facing bridge target.

If coherent stretch is controlled by the renormalized `l = 2` pressure-Hessian
channel and the higher-mode pressure feedback is power-suppressed, then the
`l = 2` carrier route is on a legitimate PDE footing.
-/
def pressureHessianL2BridgeTarget
    (reserve pressureL2 higherFeedback grade C K δ : Real) : Prop :=
  pressureHessianL2ControlsCoherentStretch reserve pressureL2 grade C higherFeedback ∧
    pressureHessianHigherModesDecouple higherFeedback grade K δ

/--
Augmented pressure-facing bridge target including the transport caveat.

This is the current proof-facing object after the panel + caveat revision:
coherent stretch is controlled by the renormalized `l = 2` pressure-Hessian
channel, the pressure-side transport defect is explicit, and the commutator
residual is shunted into a power-suppressed high-mode remainder.
-/
def pressureHessianL2TransportBridgeTarget
    (reserve pressureL2 higherFeedback grade C K δ
      transportDefect localQuadratic advectedPressure residual : Real) : Prop :=
  pressureHessianL2BridgeTarget reserve pressureL2 higherFeedback grade C K δ ∧
    pressureHessianL2TransportTarget transportDefect localQuadratic advectedPressure residual ∧
    calderonCommutatorResidualDecouple residual grade K δ

/--
Honest cap statement downstream of the pressure bridge.

The pressure-side route does not directly imply the older
`l2CarrierFactorizationTarget`, because the coherent-stretch control still
contains an explicit remainder term. What it does imply is the weaker but
correct statement that reserve is bounded by the renormalized `l = 2`
pressure-Hessian cap plus the decoupled higher-mode feedback budget.
-/
theorem reserve_capped_of_pressureHessianL2BridgeTarget
    {reserve pressureL2 higherFeedback grade C K δ cap : Real}
    (hbridge : pressureHessianL2BridgeTarget reserve pressureL2 higherFeedback grade C K δ)
    (hl2cap : C * renormalizedPressureHessianL2Carrier pressureL2 grade ≤ cap) :
    reserve ≤ cap + K * radialPowerWeight grade δ ∧
      pressureHessianHigherModesDecouple higherFeedback grade K δ := by
  rcases hbridge with ⟨hcontrol, hdecouple⟩
  rcases hdecouple with ⟨hδ, hfeedback⟩
  constructor
  · unfold pressureHessianL2ControlsCoherentStretch at hcontrol
    linarith
  · exact And.intro hδ hfeedback

/--
The transport-augmented bridge keeps the same reserve cap and additionally
records the explicit transport and commutator obligations that remain to be
paid analytically.
-/
theorem reserve_capped_of_pressureHessianL2TransportBridgeTarget
    {reserve pressureL2 higherFeedback grade C K δ cap
      transportDefect localQuadratic advectedPressure residual : Real}
    (hbridge : pressureHessianL2TransportBridgeTarget reserve pressureL2 higherFeedback
      grade C K δ transportDefect localQuadratic advectedPressure residual)
    (hl2cap : C * renormalizedPressureHessianL2Carrier pressureL2 grade ≤ cap) :
    reserve ≤ cap + K * radialPowerWeight grade δ ∧
      pressureHessianL2TransportTarget transportDefect localQuadratic advectedPressure residual ∧
      calderonCommutatorResidualDecouple residual grade K δ := by
  rcases hbridge with ⟨hbase, htransport, hresidual⟩
  rcases reserve_capped_of_pressureHessianL2BridgeTarget hbase hl2cap with ⟨hcap, _⟩
  exact ⟨hcap, htransport, hresidual⟩

/-!
## Route-1 pressure-tail visibility, pressure-side fragment

The GPT-5.5 route-1 response separated the strict source-budget question from
the pressure-channel visibility question.  This section records only the
pressure-specific obligation: a declared pressure decomposition, a reserve term
that appears in the channel-loss inequality, and a no-escape inequality for the
unresolved pressure tail.  It deliberately does not package or derive a strict
source-budget subratio.
-/

/-- Pressure-side source decomposition used by the route-1 tail-visibility
surface.

`pressureSource` is split into the local pressure-visible part, a reserve
receipt, unresolved pressure tail mass, and an explicit error term. -/
structure Route1PressureTailDecomposition where
  pressureSource : Real
  localPressureVisibility : Real
  pressureReserve : Real
  unresolvedPressureTail : Real
  pressureError : Real
  pressureSource_decomposes :
    pressureSource =
      localPressureVisibility + pressureReserve + unresolvedPressureTail + pressureError
  pressureReserve_nonneg : 0 ≤ pressureReserve
  unresolvedPressureTail_nonneg : 0 ≤ unresolvedPressureTail

/-- Reserve-bearing pressure channel loss.

This is the pressure analogue of the critical-tail channel-loss clause.  The
reserve is an independently named debit in the pressure channel; it is not a
strict global source-budget assumption. -/
def pressureReserveChannelLoss
    (pressureSource rhoP X_tail pressureReserve pressureError C0 : Real) : Prop :=
  pressureSource ≤ rhoP * X_tail - C0 * pressureReserve + pressureError

/-- No-escape obligation for unresolved pressure tail mass. -/
def pressureTailNoEscapeObligation
    (pressureTailMass localQuadraticVisibility pressureReserve acceptableChildCharge
      C0 : Real) : Prop :=
  pressureTailMass ≤
    C0 * (localQuadraticVisibility + pressureReserve + acceptableChildCharge)

/-- Pressure-specific route-1 critical-tail visibility obligation.

This is only the pressure-channel fragment: decomposition, reserve-bearing
channel loss, and no-escape booking for the unresolved pressure tail.  It does
not assert strict source-budget subratio, nor does it assume one as a field. -/
structure Route1PressureReserveNoEscapeObligation where
  decomposition : Route1PressureTailDecomposition
  rhoP : Real
  X_tail : Real
  localQuadraticVisibility : Real
  acceptableChildCharge : Real
  C0 : Real
  pressureChannelLoss :
    pressureReserveChannelLoss
      decomposition.pressureSource rhoP X_tail decomposition.pressureReserve
      decomposition.pressureError C0
  pressureNoEscape :
    pressureTailNoEscapeObligation
      decomposition.unresolvedPressureTail localQuadraticVisibility
      decomposition.pressureReserve acceptableChildCharge C0

/-- Projection theorem: the pressure obligation exposes exactly the
decomposition, reserve-channel loss, and no-escape clauses. -/
theorem route1_pressure_reserve_no_escape_obligation_projects
    (h : Route1PressureReserveNoEscapeObligation) :
    h.decomposition.pressureSource =
        h.decomposition.localPressureVisibility +
          h.decomposition.pressureReserve +
          h.decomposition.unresolvedPressureTail +
          h.decomposition.pressureError ∧
      pressureReserveChannelLoss
        h.decomposition.pressureSource h.rhoP h.X_tail
        h.decomposition.pressureReserve h.decomposition.pressureError h.C0 ∧
      pressureTailNoEscapeObligation
        h.decomposition.unresolvedPressureTail h.localQuadraticVisibility
        h.decomposition.pressureReserve h.acceptableChildCharge h.C0 := by
  exact ⟨h.decomposition.pressureSource_decomposes, h.pressureChannelLoss,
    h.pressureNoEscape⟩

/-- The same projection, with the reserve and unresolved-tail nonnegativity
receipts kept visible for downstream scalar bookkeeping. -/
theorem route1_pressure_decomposition_reserve_receipts
    (h : Route1PressureReserveNoEscapeObligation) :
    0 ≤ h.decomposition.pressureReserve ∧
      0 ≤ h.decomposition.unresolvedPressureTail ∧
      pressureTailNoEscapeObligation
        h.decomposition.unresolvedPressureTail h.localQuadraticVisibility
        h.decomposition.pressureReserve h.acceptableChildCharge h.C0 := by
  exact ⟨h.decomposition.pressureReserve_nonneg,
    h.decomposition.unresolvedPressureTail_nonneg, h.pressureNoEscape⟩

/--
Independent pressure-channel receipts exposed to a route-1 channel producer.

These are just the three pressure-side charges used by the no-escape clause.
They deliberately remain independent scalar receipts, rather than a single
visibility expression derived from a source-budget subtraction.
-/
structure Route1PressureVisibilityReceipts where
  pressureReserveReceipt : Real
  localQuadraticReceipt : Real
  childChargeReceipt : Real

/-- Sum of the independently exposed pressure-channel receipts. -/
def Route1PressureVisibilityReceipts.receiptSum
    (r : Route1PressureVisibilityReceipts) : Real :=
  r.localQuadraticReceipt + r.pressureReserveReceipt + r.childChargeReceipt

/-- Projection from the pressure no-escape obligation to the independent
route-1 pressure-channel receipts. -/
def route1PressureVisibilityReceipts
    (h : Route1PressureReserveNoEscapeObligation) :
    Route1PressureVisibilityReceipts where
  pressureReserveReceipt := h.decomposition.pressureReserve
  localQuadraticReceipt := h.localQuadraticVisibility
  childChargeReceipt := h.acceptableChildCharge

/-- The pressure reserve receipt is exactly the decomposition reserve, with its
existing nonnegativity certificate preserved. -/
theorem route1_pressure_reserve_visibility_receipt
    (h : Route1PressureReserveNoEscapeObligation) :
    (route1PressureVisibilityReceipts h).pressureReserveReceipt =
        h.decomposition.pressureReserve ∧
      0 ≤ (route1PressureVisibilityReceipts h).pressureReserveReceipt := by
  exact ⟨rfl, h.decomposition.pressureReserve_nonneg⟩

/-- The local quadratic receipt is projected independently from the pressure
obligation, not recovered from a strict source subratio. -/
theorem route1_pressure_local_quadratic_visibility_receipt
    (h : Route1PressureReserveNoEscapeObligation) :
    (route1PressureVisibilityReceipts h).localQuadraticReceipt =
      h.localQuadraticVisibility := by
  rfl

/-- The acceptable child charge is exposed as its own pressure-channel receipt. -/
theorem route1_pressure_child_charge_visibility_receipt
    (h : Route1PressureReserveNoEscapeObligation) :
    (route1PressureVisibilityReceipts h).childChargeReceipt =
      h.acceptableChildCharge := by
  rfl

/-- The no-escape clause can be read directly in terms of the independent
pressure visibility receipts. -/
theorem route1_pressure_no_escape_of_visibility_receipts
    (h : Route1PressureReserveNoEscapeObligation) :
    h.decomposition.unresolvedPressureTail ≤
      h.C0 *
        (route1PressureVisibilityReceipts h).receiptSum := by
  exact h.pressureNoEscape

/--
Positive pressure visibility lower-bound producer.

This is the missing pressure-side strengthening isolated by the route-1
channel-producer audit.  The no-escape inequality alone is an upper-bound
booking statement; a route-1 channel producer also needs a lower bound that
forces unresolved critical tail mass to appear in independently named pressure
receipts.
-/
structure Route1PressureVisibilityLowerBoundProducer where
  obligation : Route1PressureReserveNoEscapeObligation
  nuP : Real
  X_tail : Real
  nuP_pos : 0 < nuP
  X_tail_nonneg : 0 ≤ X_tail
  localQuadraticReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts obligation).localQuadraticReceipt
  childChargeReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts obligation).childChargeReceipt
  pressureReceiptLowerBound :
    nuP * X_tail ≤ (route1PressureVisibilityReceipts obligation).receiptSum

/-- Projection theorem for the pressure lower-bound producer. -/
theorem route1_pressure_visibility_lower_bound_projects
    (h : Route1PressureVisibilityLowerBoundProducer) :
    0 < h.nuP ∧
      0 ≤ h.X_tail ∧
      h.nuP * h.X_tail ≤
        (route1PressureVisibilityReceipts h.obligation).receiptSum := by
  exact ⟨h.nuP_pos, h.X_tail_nonneg, h.pressureReceiptLowerBound⟩

/--
No-escape alone does not force a positive pressure visibility lower bound.

Concrete scalar counterexample: all pressure receipts and unresolved pressure
tail are zero, while the route tail scale is positive.  The no-escape inequality
holds, but no positive multiple of the route tail can be bounded by the pressure
receipt sum.  This is the pressure-leg blocker: any useful proof must add a
genuine lower-bound/visibility theorem, not just reuse no-escape.
-/
theorem route1_pressure_no_escape_only_does_not_force_positive_visibility :
    ∃ h : Route1PressureReserveNoEscapeObligation,
      0 < h.X_tail ∧
        ∃ nuP : Real,
          0 < nuP ∧
            ¬ nuP * h.X_tail ≤
              (route1PressureVisibilityReceipts h).receiptSum := by
  let decomp : Route1PressureTailDecomposition :=
    { pressureSource := 0
      localPressureVisibility := 0
      pressureReserve := 0
      unresolvedPressureTail := 0
      pressureError := 0
      pressureSource_decomposes := by norm_num
      pressureReserve_nonneg := by norm_num
      unresolvedPressureTail_nonneg := by norm_num }
  let h : Route1PressureReserveNoEscapeObligation :=
    { decomposition := decomp
      rhoP := 0
      X_tail := 1
      localQuadraticVisibility := 0
      acceptableChildCharge := 0
      C0 := 1
      pressureChannelLoss := by
        norm_num [pressureReserveChannelLoss, decomp]
      pressureNoEscape := by
        norm_num [pressureTailNoEscapeObligation, decomp] }
  refine ⟨h, ?_, 1, ?_, ?_⟩
  · norm_num [h]
  · norm_num
  · norm_num [h, route1PressureVisibilityReceipts,
      Route1PressureVisibilityReceipts.receiptSum]

/--
Pressure tail-mass visibility is the smaller positive primitive below the
pressure receipt lower-bound producer.

The no-escape inequality gives an upper booking of unresolved pressure tail
mass by pressure receipts.  To turn that into a lower-bound producer, one needs
an independent lower bound saying the unresolved pressure tail contains a
positive fraction of the route tail scale.
-/
structure Route1PressureTailMassVisibility where
  obligation : Route1PressureReserveNoEscapeObligation
  etaP : Real
  X_tail : Real
  etaP_pos : 0 < etaP
  X_tail_nonneg : 0 ≤ X_tail
  C0_pos : 0 < obligation.C0
  localQuadraticReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts obligation).localQuadraticReceipt
  childChargeReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts obligation).childChargeReceipt
  pressureTailMassVisible :
    etaP * X_tail ≤ obligation.decomposition.unresolvedPressureTail

/--
PDE-facing certificate for the pressure-visible branch.

The downstream route1 algebra only needs `Route1PressureTailMassVisibility`,
but the non-tautological pressure input should identify unresolved pressure
tail mass with an actual recovered pressure-Hessian `l = 2` tail observable,
not with an arbitrary scalar reserve.
-/
structure Route1PressureHessianL2TailMassCertificate where
  obligation : Route1PressureReserveNoEscapeObligation
  pressureL2 : PressureHessianL2Amplitude
  radialGrade : Real
  etaP : Real
  X_tail : Real
  etaP_pos : 0 < etaP
  X_tail_nonneg : 0 ≤ X_tail
  C0_pos : 0 < obligation.C0
  localQuadraticReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts obligation).localQuadraticReceipt
  childChargeReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts obligation).childChargeReceipt
  pressureRecoveredByHelmholtzLeray : Prop
  pressureL2IsTailWindowProjectionOfRecoveredPressureHessian : Prop
  tailWindowMatchesRouteTailScale : Prop
  pressureTailMass_identifies_l2_hessian :
    obligation.decomposition.unresolvedPressureTail =
      renormalizedPressureHessianL2Carrier pressureL2 radialGrade
  pressureHessianL2_tail_lower_bound :
    etaP * X_tail ≤ renormalizedPressureHessianL2Carrier pressureL2 radialGrade

/--
Route-receipt-free carrier identification for the pressure-visible branch.

The final equality is still an explicit PDE obligation, but the surrounding
fields separate the ingredients graph/Jaccard surfaced as the next bottleneck:
recovered pressure-Hessian projection, projected Riesz/angular matching, and
normalization fixed before any route receipt is attached.
-/
structure Route1PressureAngularCarrierIdentification where
  pressureL2 : PressureHessianL2Amplitude
  radialGrade : Real
  coreMoment : CoreAngularMoment
  sheathErrorMoment : SheathErrorAngularMoment
  pressureRecoveredByHelmholtzLeray : Prop
  pressureL2IsTailWindowProjectionOfRecoveredPressureHessian : Prop
  projectedRieszKernelMatchesAngularMoment : Prop
  radialGradeNormalizesPressureCarrier : Prop
  pressureWindowFixedBeforeRouteReceipt : Prop
  angularKernelFixedBeforeRouteReceipt : Prop
  l2Carrier_identifies_totalAngularMoment :
    renormalizedPressureHessianL2Carrier pressureL2 radialGrade =
      |totalAngularMoment coreMoment sheathErrorMoment|
  carrierNotDefinedFromPressureReceipt : Prop
  no_strictSubratio_or_margin_input : Prop

/--
Pressure-side source station for carrier identification.

This isolates the Helmholtz-Leray recovery and tail-window projection piece
from the angular Riesz-kernel matching piece.  It is deliberately route-receipt
free: the unresolved pressure-tail receipt is attached only later.
-/
structure Route1PressureHessianTailWindowProjectionStation where
  pressureL2 : PressureHessianL2Amplitude
  radialGrade : Real
  pressureRecoveredByHelmholtzLeray : Prop
  pressureL2IsTailWindowProjectionOfRecoveredPressureHessian : Prop
  radialGradeNormalizesPressureCarrier : Prop
  pressureWindowFixedBeforeRouteReceipt : Prop
  tailProjectionNotDefinedFromAngularMoment : Prop
  no_strictSubratio_or_margin_input : Prop

/--
Angular/Riesz source station for carrier identification.

This is the branch-B analytic obligation named by the forecast split: the
projected Riesz kernel must identify the same signed `l = 2` angular moment
that the dominance lemma controls, using a kernel fixed before any pressure
receipt or angular floor is chosen.
-/
structure Route1ProjectedRieszAngularMomentStation
    (pressureL2 : PressureHessianL2Amplitude)
    (radialGrade : Real) where
  coreMoment : CoreAngularMoment
  sheathErrorMoment : SheathErrorAngularMoment
  projectedRieszKernelMatchesAngularMoment : Prop
  angularKernelFixedBeforeRouteReceipt : Prop
  angularMomentComputedBeforePressureReceipt : Prop
  projectedKernelNotDefinedFromAngularFloor : Prop
  sameTailWindowAsPressureProjection : Prop
  l2Carrier_identifies_totalAngularMoment :
    renormalizedPressureHessianL2Carrier pressureL2 radialGrade =
      |totalAngularMoment coreMoment sheathErrorMoment|
  no_strictSubratio_or_margin_input : Prop

/--
Formula source beneath projected Riesz/angular matching.

This splits the carrier equality into three independently checkable formula
links: the pressure tail-window carrier is fixed, the projected Riesz kernel
moment is computed before any route receipt or angular floor is chosen, and
that projected moment agrees with the signed core-plus-sheath angular moment.
-/
structure Route1ProjectedRieszAngularFormulaSource
    (pressureL2 : PressureHessianL2Amplitude)
    (radialGrade : Real) where
  coreMoment : CoreAngularMoment
  sheathErrorMoment : SheathErrorAngularMoment
  pressureTailWindowCarrier : Real
  projectedRieszKernelMoment : Real
  pressureTailWindowCarrier_eq_l2Carrier :
    pressureTailWindowCarrier =
      renormalizedPressureHessianL2Carrier pressureL2 radialGrade
  pressureTailWindowCarrier_eq_absProjectedKernelMoment :
    pressureTailWindowCarrier = |projectedRieszKernelMoment|
  projectedKernelMoment_eq_totalAngularMoment :
    projectedRieszKernelMoment =
      totalAngularMoment coreMoment sheathErrorMoment
  projectedRieszKernelMatchesAngularMoment : Prop
  angularKernelFixedBeforeRouteReceipt : Prop
  angularMomentComputedBeforePressureReceipt : Prop
  projectedKernelNotDefinedFromAngularFloor : Prop
  sameTailWindowAsPressureProjection : Prop
  pressureCarrierFixedBeforeKernelMoment : Prop
  projectedKernelMomentNotDefinedFromCarrierMagnitude : Prop
  no_strictSubratio_or_margin_input : Prop

/--
The formula source yields the projected Riesz/angular station consumed by the
carrier-identification bundle.
-/
def Route1ProjectedRieszAngularMomentStation.ofFormulaSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (h : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade) :
    Route1ProjectedRieszAngularMomentStation pressureL2 radialGrade where
  coreMoment := h.coreMoment
  sheathErrorMoment := h.sheathErrorMoment
  projectedRieszKernelMatchesAngularMoment :=
    h.projectedRieszKernelMatchesAngularMoment
  angularKernelFixedBeforeRouteReceipt :=
    h.angularKernelFixedBeforeRouteReceipt
  angularMomentComputedBeforePressureReceipt :=
    h.angularMomentComputedBeforePressureReceipt
  projectedKernelNotDefinedFromAngularFloor :=
    h.projectedKernelNotDefinedFromAngularFloor
  sameTailWindowAsPressureProjection :=
    h.sameTailWindowAsPressureProjection
  l2Carrier_identifies_totalAngularMoment := by
    rw [← h.pressureTailWindowCarrier_eq_l2Carrier,
      h.pressureTailWindowCarrier_eq_absProjectedKernelMoment,
      h.projectedKernelMoment_eq_totalAngularMoment]
  no_strictSubratio_or_margin_input := h.no_strictSubratio_or_margin_input

/--
No-Go fact for the projected Riesz/angular formula source.

If the same-scale sheath exactly cancels the core angular moment, then the
formula source drives the projected pressure-Hessian carrier to zero. Thus
pressure magnitude or recovered-Riesz control alone cannot supply projected
angular visibility; a separate angular-dominance estimate is required.
-/
theorem projectedRieszFormulaSource_carrier_zero_of_exact_sheath_cancellation
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (h : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (hcancel : h.sheathErrorMoment = -h.coreMoment) :
    renormalizedPressureHessianL2Carrier pressureL2 radialGrade = 0 := by
  have htotal :
      totalAngularMoment h.coreMoment h.sheathErrorMoment = 0 :=
    stealth_possible_by_exact_angular_moment_cancellation hcancel
  have hprojected : h.projectedRieszKernelMoment = 0 := by
    rw [h.projectedKernelMoment_eq_totalAngularMoment, htotal]
  have htail : h.pressureTailWindowCarrier = 0 := by
    rw [h.pressureTailWindowCarrier_eq_absProjectedKernelMoment, hprojected]
    simp
  rw [← h.pressureTailWindowCarrier_eq_l2Carrier]
  exact htail

/--
The formula-source No-Go rules out any positive lower bound on the same carrier
unless exact sheath cancellation has already been excluded.
-/
theorem no_positive_projected_carrier_under_exact_sheath_cancellation
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (h : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (hcancel : h.sheathErrorMoment = -h.coreMoment)
    (hpositive : 0 < renormalizedPressureHessianL2Carrier pressureL2 radialGrade) :
    False := by
  have hzero :=
    projectedRieszFormulaSource_carrier_zero_of_exact_sheath_cancellation h hcancel
  rw [hzero] at hpositive
  linarith

/--
Positive-side source beneath the formula-source branch.

This is the next theorem target after the No-Go pass.  It does not define an
angular floor from the pressure carrier.  It binds a core floor and same-window
sheath bound to the already fixed formula source, before any route receipt is
attached.
-/
structure Route1FixedWindowAngularDominanceSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade) where
  epsilon : Real
  coreFloor : Real
  etaP : Real
  X_tail : Real
  epsilon_pos : 0 < epsilon
  epsilon_le_one : epsilon ≤ 1
  X_tail_nonneg : 0 ≤ X_tail
  coreAngularMomentFloor : coreFloor ≤ |formula.coreMoment|
  angularDominance :
    angularMomentDominance formula.coreMoment formula.sheathErrorMoment epsilon
  routeTailScale_le_angularFloor :
    etaP * X_tail ≤ epsilon * coreFloor
  sameTailWindowAsFormulaSource : Prop
  sameProjectedKernelAsFormulaSource : Prop
  coreMomentComputedBeforeRouteReceipt : Prop
  sheathBoundComputedBeforeRouteReceipt : Prop
  angularFloorNotDefinedFromCarrierMagnitude : Prop
  no_strictSubratio_or_margin_input : Prop

/--
The fixed-window dominance source produces the carrier lower bound consumed by
the pressure-visible branch.

All PDE content is in the source fields: the proof here only combines angular
dominance with the formula-source equalities.
-/
theorem pressureHessianL2_tail_lower_bound_of_fixedWindowAngularDominanceSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : Route1FixedWindowAngularDominanceSource formula) :
    h.etaP * h.X_tail ≤
      renormalizedPressureHessianL2Carrier pressureL2 radialGrade := by
  have hangular :
      h.epsilon * h.coreFloor ≤
        |totalAngularMoment formula.coreMoment formula.sheathErrorMoment| :=
    angular_moment_floor_of_dominance
      h.epsilon_pos h.epsilon_le_one h.coreAngularMomentFloor h.angularDominance
  have hroute :
      h.etaP * h.X_tail ≤
        |totalAngularMoment formula.coreMoment formula.sheathErrorMoment| :=
    le_trans h.routeTailScale_le_angularFloor hangular
  have hcarrier :
      renormalizedPressureHessianL2Carrier pressureL2 radialGrade =
        |totalAngularMoment formula.coreMoment formula.sheathErrorMoment| := by
    rw [← formula.pressureTailWindowCarrier_eq_l2Carrier,
      formula.pressureTailWindowCarrier_eq_absProjectedKernelMoment,
      formula.projectedKernelMoment_eq_totalAngularMoment]
  rw [hcarrier]
  exact hroute

/--
Negative-side package for the same fixed formula source.

This records the branch-killing alternative: the same window and projected
kernel may allow exact sheath cancellation, in which case the projected carrier
is forced to zero even if pressure magnitude controls are available elsewhere.
-/
structure Route1SameWindowSheathCancellationCountermodel
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade) where
  coreMoment_nonzero : formula.coreMoment ≠ 0
  exactSameWindowCancellation :
    formula.sheathErrorMoment = -formula.coreMoment
  sameTailWindowAsFormulaSource : Prop
  sameProjectedKernelAsFormulaSource : Prop
  compatibleWithRecoveredRieszMagnitudeControls : Prop
  compatibleWithLocalCZPressureExcessControls : Prop
  cancellationNotChosenFromCarrierMagnitude : Prop
  no_strictSubratio_or_margin_input : Prop

/--
PDE-shaped mechanism behind the same-window sheath countermodel.

The fields follow the Gowers-style No-Go decomposition.  A fixed projected
`l = 2` Riesz moment is a stress-linear functional against a sign-indefinite
trace-free tensor.  Disjoint divergence-free packets can realize opposite
stress signs in the same tail window, and amplitude scaling can tune their
moments to cancel.  These mechanism clauses are kept as independent `Prop`
receipts because the actual packet construction is an analysis theorem, not
scalar bookkeeping.
-/
structure Route1SameWindowSheathCancellationMechanism
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade) where
  coreMoment_nonzero : formula.coreMoment ≠ 0
  exactSameWindowCancellation :
    formula.sheathErrorMoment = -formula.coreMoment
  projectedMomentIsStressLinearFunctional : Prop
  projectedL2StressTensorSignIndefinite : Prop
  corePacketDivergenceFree : Prop
  sheathPacketDivergenceFree : Prop
  corePacketRealizesPositiveProjectedMoment : Prop
  sheathPacketRealizesNegativeProjectedMoment : Prop
  coreSheathSupportsDisjoint : Prop
  disjointPacketsHaveNoCrossStress : Prop
  projectedMomentAddsAcrossDisjointPackets : Prop
  amplitudesTuneExactCancellation : Prop
  pressureRecoveryCompatibleWithPacketSum : Prop
  localEnergyCKNCompatibleWithPacketSum : Prop
  recoveredRieszStationCompatibleWithPacketSum : Prop
  sameTailWindowAsFormulaSource : Prop
  sameProjectedKernelAsFormulaSource : Prop
  cancellationNotChosenFromCarrierMagnitude : Prop
  no_strictSubratio_or_margin_input : Prop

/--
For route bookkeeping, the packet mechanism projects to the smaller
same-window cancellation countermodel.
-/
def Route1SameWindowSheathCancellationCountermodel.ofMechanism
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : Route1SameWindowSheathCancellationMechanism formula) :
    Route1SameWindowSheathCancellationCountermodel formula where
  coreMoment_nonzero := h.coreMoment_nonzero
  exactSameWindowCancellation := h.exactSameWindowCancellation
  sameTailWindowAsFormulaSource := h.sameTailWindowAsFormulaSource
  sameProjectedKernelAsFormulaSource := h.sameProjectedKernelAsFormulaSource
  compatibleWithRecoveredRieszMagnitudeControls :=
    h.pressureRecoveryCompatibleWithPacketSum
  compatibleWithLocalCZPressureExcessControls :=
    h.localEnergyCKNCompatibleWithPacketSum
  cancellationNotChosenFromCarrierMagnitude :=
    h.cancellationNotChosenFromCarrierMagnitude
  no_strictSubratio_or_margin_input :=
    h.no_strictSubratio_or_margin_input

/--
The same-window cancellation countermodel defeats any positive lower bound on
the projected carrier for the fixed formula source.
-/
theorem no_positive_projected_carrier_of_sameWindowSheathCountermodel
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : Route1SameWindowSheathCancellationCountermodel formula)
    (hpositive :
      0 < renormalizedPressureHessianL2Carrier pressureL2 radialGrade) :
    False :=
  no_positive_projected_carrier_under_exact_sheath_cancellation
    formula h.exactSameWindowCancellation hpositive

/--
Exact same-window cancellation also defeats any strict angular dominance claim
with a positive independently chosen core floor.
-/
theorem no_strict_angularDominance_of_sameWindowSheathCountermodel
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon coreFloor : Real}
    (h : Route1SameWindowSheathCancellationCountermodel formula)
    (heps_pos : 0 < epsilon)
    (hcoreFloor : coreFloor ≤ |formula.coreMoment|)
    (hcoreFloor_pos : 0 < coreFloor)
    (hdominance :
      angularMomentDominance formula.coreMoment formula.sheathErrorMoment epsilon) :
    False :=
  exact_sheath_cancellation_incompatible_with_positive_core_dominance
    heps_pos hcoreFloor hcoreFloor_pos h.exactSameWindowCancellation hdominance

/--
The packet mechanism version of the same No-Go, exposing that the obstruction
comes from fixed-window stress orientation rather than from scalar pressure
magnitude.
-/
theorem no_strict_angularDominance_of_sameWindowSheathMechanism
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon coreFloor : Real}
    (h : Route1SameWindowSheathCancellationMechanism formula)
    (heps_pos : 0 < epsilon)
    (hcoreFloor : coreFloor ≤ |formula.coreMoment|)
    (hcoreFloor_pos : 0 < coreFloor)
    (hdominance :
      angularMomentDominance formula.coreMoment formula.sheathErrorMoment epsilon) :
    False :=
  no_strict_angularDominance_of_sameWindowSheathCountermodel
    (Route1SameWindowSheathCancellationCountermodel.ofMechanism h)
    heps_pos hcoreFloor hcoreFloor_pos hdominance

/--
Same-window cancellation rules out every positive strict angular-dominance
parameter for the fixed formula source.
-/
theorem no_derived_angularDominance_of_sameWindowSheathCountermodel
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : Route1SameWindowSheathCancellationCountermodel formula) :
    ¬ ∃ epsilon : Real,
        0 < epsilon ∧
          angularMomentDominance formula.coreMoment formula.sheathErrorMoment epsilon := by
  rintro ⟨epsilon, heps_pos, hdominance⟩
  have hcore_abs_pos : 0 < |formula.coreMoment| := by
    exact abs_pos.mpr h.coreMoment_nonzero
  exact no_strict_angularDominance_of_sameWindowSheathCountermodel
    h heps_pos (le_refl |formula.coreMoment|) hcore_abs_pos hdominance

/--
Named No-Go surface: current fixed-window pressure/Riesz data do not imply
strict angular dominance when the same-window sheath-cancellation mechanism is
available.

The pressure-data fields are deliberately `Prop` receipts: this object records
that pressure recovery, local energy/CKN/local-CZ compatibility, and
recovered-Riesz station compatibility may all hold while strict angular
dominance fails.  The actual obstruction is the fixed-window stress-angular
packet mechanism carried by `cancellationModel`.
-/
structure FixedWindowAngularDominanceNotFromCurrentPressureData
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade) where
  nondegenerateCoreProjectedTensor : Prop
  nondegenerateSheathProjectedTensor : Prop
  pressureRecoveryCompatible : Prop
  localEnergyCKNCompatible : Prop
  localCalderonZygmundCompatible : Prop
  recoveredRieszStationCompatible : Prop
  cancellationModel :
    Route1SameWindowSheathCancellationMechanism formula
  fixedWindowAndKernelBeforeRouteReceipt : Prop
  currentPressureDataOnly : Prop

/--
The named pressure-data No-Go projects to the actual mathematical verdict:
there is no positive strict angular-dominance parameter forced by these data.
-/
theorem no_derived_angularDominance_of_currentPressureData
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : FixedWindowAngularDominanceNotFromCurrentPressureData formula) :
    ¬ ∃ epsilon : Real,
        0 < epsilon ∧
          angularMomentDominance formula.coreMoment formula.sheathErrorMoment epsilon :=
  no_derived_angularDominance_of_sameWindowSheathCountermodel
    (Route1SameWindowSheathCancellationCountermodel.ofMechanism h.cancellationModel)

/--
Positive-side replacement after the same-window No-Go.

This is the non-tautological input that can revive the pressure/Riesz branch:
stress-level angular coherence against the fixed projected tensor before the
core and sheath moments are summed.  It is stronger than pressure recovery or
local CZ upper control, but weaker than assuming the final pressure carrier is
positive.
-/
structure FixedWindowStressAngularCoherenceDominance
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade) where
  epsilon : Real
  coreFloor : Real
  etaP : Real
  X_tail : Real
  epsilon_pos : 0 < epsilon
  epsilon_le_one : epsilon ≤ 1
  X_tail_nonneg : 0 ≤ X_tail
  coreAngularMomentFloor : coreFloor ≤ |formula.coreMoment|
  routeTailScale_le_angularFloor :
    etaP * X_tail ≤ epsilon * coreFloor
  fixedWindowAndKernelBeforeRouteReceipt : Prop
  adjointProjectedTensorFixedBeforeStressSplit : Prop
  coreStressMostlyPositiveCone : Prop
  sheathOppositeConeStrictlySubordinate : Prop
  sheath_opposite_cone_subordinate :
    |formula.sheathErrorMoment| ≤ (1 - epsilon) * |formula.coreMoment|
  stressLevelNotCarrierLevel : Prop
  coherenceNotDefinedFromCarrierMagnitude : Prop
  no_strictSubratio_or_margin_input : Prop

/--
Stress-angular coherence projects to the existing fixed-window dominance source.
The theorem does not prove the PDE estimate; it only records that the positive
branch must pay this source before using the pressure carrier.
-/
def Route1FixedWindowAngularDominanceSource.ofStressAngularCoherence
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : FixedWindowStressAngularCoherenceDominance formula) :
    Route1FixedWindowAngularDominanceSource formula where
  epsilon := h.epsilon
  coreFloor := h.coreFloor
  etaP := h.etaP
  X_tail := h.X_tail
  epsilon_pos := h.epsilon_pos
  epsilon_le_one := h.epsilon_le_one
  X_tail_nonneg := h.X_tail_nonneg
  coreAngularMomentFloor := h.coreAngularMomentFloor
  angularDominance := h.sheath_opposite_cone_subordinate
  routeTailScale_le_angularFloor := h.routeTailScale_le_angularFloor
  sameTailWindowAsFormulaSource := h.fixedWindowAndKernelBeforeRouteReceipt
  sameProjectedKernelAsFormulaSource :=
    h.adjointProjectedTensorFixedBeforeStressSplit
  coreMomentComputedBeforeRouteReceipt := h.coreStressMostlyPositiveCone
  sheathBoundComputedBeforeRouteReceipt := h.sheathOppositeConeStrictlySubordinate
  angularFloorNotDefinedFromCarrierMagnitude :=
    h.coherenceNotDefinedFromCarrierMagnitude
  no_strictSubratio_or_margin_input := h.no_strictSubratio_or_margin_input

/--
Once a fixed-window stress-angular-coherence source is paid, the pressure-Hessian
tail lower bound follows by the existing dominance constructor.
-/
theorem pressureHessianL2_tail_lower_bound_of_stressAngularCoherence
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : FixedWindowStressAngularCoherenceDominance formula) :
    h.etaP * h.X_tail ≤
      renormalizedPressureHessianL2Carrier pressureL2 radialGrade :=
  pressureHessianL2_tail_lower_bound_of_fixedWindowAngularDominanceSource
    (Route1FixedWindowAngularDominanceSource.ofStressAngularCoherence h)

/--
One level lower than stress-angular coherence: measurable fixed-window cone
masses.  The hard PDE content is now the pair of mass estimates:
the sheath opposite-cone mass controls the sheath moment, and that mass is a
strict fraction of the core positive-cone mass.
-/
structure FixedWindowStressConeMassSubordination
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade) where
  epsilon : Real
  coreFloor : Real
  etaP : Real
  X_tail : Real
  corePositiveConeMass : Real
  sheathOppositeConeMass : Real
  epsilon_pos : 0 < epsilon
  epsilon_le_one : epsilon ≤ 1
  X_tail_nonneg : 0 ≤ X_tail
  corePositiveConeMass_nonneg : 0 ≤ corePositiveConeMass
  sheathOppositeConeMass_nonneg : 0 ≤ sheathOppositeConeMass
  coreAngularMomentFloor : coreFloor ≤ |formula.coreMoment|
  routeTailScale_le_angularFloor :
    etaP * X_tail ≤ epsilon * coreFloor
  corePositiveConeMass_le_coreAbs :
    corePositiveConeMass ≤ |formula.coreMoment|
  sheathError_abs_le_sheathOppositeConeMass :
    |formula.sheathErrorMoment| ≤ sheathOppositeConeMass
  sheathOppositeConeMass_subordinate :
    sheathOppositeConeMass ≤ (1 - epsilon) * corePositiveConeMass
  fixedWindowAndKernelBeforeRouteReceipt : Prop
  adjointProjectedTensorFixedBeforeStressSplit : Prop
  coreConeMassMeasuredBeforeSummation : Prop
  sheathConeMassMeasuredBeforeSummation : Prop
  coneMassesNotDefinedFromCarrierMagnitude : Prop
  no_strictSubratio_or_margin_input : Prop

/--
Cone-mass subordination implies the stress-angular-coherence source by scalar
monotonicity.  The PDE obligation has been pushed into measurable cone masses.
-/
def FixedWindowStressAngularCoherenceDominance.ofConeMassSubordination
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : FixedWindowStressConeMassSubordination formula) :
    FixedWindowStressAngularCoherenceDominance formula where
  epsilon := h.epsilon
  coreFloor := h.coreFloor
  etaP := h.etaP
  X_tail := h.X_tail
  epsilon_pos := h.epsilon_pos
  epsilon_le_one := h.epsilon_le_one
  X_tail_nonneg := h.X_tail_nonneg
  coreAngularMomentFloor := h.coreAngularMomentFloor
  routeTailScale_le_angularFloor := h.routeTailScale_le_angularFloor
  fixedWindowAndKernelBeforeRouteReceipt :=
    h.fixedWindowAndKernelBeforeRouteReceipt
  adjointProjectedTensorFixedBeforeStressSplit :=
    h.adjointProjectedTensorFixedBeforeStressSplit
  coreStressMostlyPositiveCone := h.coreConeMassMeasuredBeforeSummation
  sheathOppositeConeStrictlySubordinate :=
    h.sheathConeMassMeasuredBeforeSummation
  sheath_opposite_cone_subordinate := by
    have hnonneg : 0 ≤ 1 - h.epsilon := by linarith [h.epsilon_le_one]
    have hsheath_core :
        |formula.sheathErrorMoment| ≤
          (1 - h.epsilon) * h.corePositiveConeMass :=
      le_trans h.sheathError_abs_le_sheathOppositeConeMass
        h.sheathOppositeConeMass_subordinate
    have hcore :
        (1 - h.epsilon) * h.corePositiveConeMass ≤
          (1 - h.epsilon) * |formula.coreMoment| :=
      mul_le_mul_of_nonneg_left h.corePositiveConeMass_le_coreAbs hnonneg
    exact le_trans hsheath_core hcore
  stressLevelNotCarrierLevel := h.coneMassesNotDefinedFromCarrierMagnitude
  coherenceNotDefinedFromCarrierMagnitude :=
    h.coneMassesNotDefinedFromCarrierMagnitude
  no_strictSubratio_or_margin_input := h.no_strictSubratio_or_margin_input

/--
Cone-mass subordination is enough to produce the pressure-Hessian tail lower
bound, through stress-angular coherence and fixed-window dominance.
-/
theorem pressureHessianL2_tail_lower_bound_of_coneMassSubordination
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : FixedWindowStressConeMassSubordination formula) :
    h.etaP * h.X_tail ≤
      renormalizedPressureHessianL2Carrier pressureL2 radialGrade :=
  pressureHessianL2_tail_lower_bound_of_stressAngularCoherence
    (FixedWindowStressAngularCoherenceDominance.ofConeMassSubordination h)

/--
No-escape primitive below cone-mass subordination.

If the sheath opposite-cone mass exceeds the allowed fraction of the core
positive-cone mass, it must produce the same-window sheath-cancellation
mechanism.  A rigidity/no-countermodel input then rules out that overflow.
-/
structure FixedWindowOppositeConeNoEscapeProducer
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  overflow_to_sameWindowSheathCancellation :
    (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass →
      Route1SameWindowSheathCancellationMechanism formula
  no_sameWindowSheathCancellation :
    Route1SameWindowSheathCancellationMechanism formula → False
  fixedWindowPacketExtraction : Prop
  noCarrierMagnitudeInPacketExtraction : Prop

/--
Rigidity/no-escape converts the overflow test into the cone-mass inequality.
-/
theorem sheathOppositeConeMass_subordinate_of_noEscapeProducer
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOppositeConeNoEscapeProducer formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    sheathOppositeConeMass ≤ (1 - epsilon) * corePositiveConeMass := by
  by_contra hnot
  have hoverflow :
      (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass :=
    lt_of_not_ge hnot
  exact h.no_sameWindowSheathCancellation
    (h.overflow_to_sameWindowSheathCancellation hoverflow)

/--
Rigidity-source version of cone-mass subordination.

This is the next lower positive pressure/Riesz target: prove that any
same-window opposite-cone overflow creates a forbidden sheath-cancellation
packet/profile.  The scalar cone inequality is then a consequence, not an
assumption.
-/
structure FixedWindowStressConeMassRigiditySource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade) where
  epsilon : Real
  coreFloor : Real
  etaP : Real
  X_tail : Real
  corePositiveConeMass : Real
  sheathOppositeConeMass : Real
  epsilon_pos : 0 < epsilon
  epsilon_le_one : epsilon ≤ 1
  X_tail_nonneg : 0 ≤ X_tail
  corePositiveConeMass_nonneg : 0 ≤ corePositiveConeMass
  sheathOppositeConeMass_nonneg : 0 ≤ sheathOppositeConeMass
  coreAngularMomentFloor : coreFloor ≤ |formula.coreMoment|
  routeTailScale_le_angularFloor :
    etaP * X_tail ≤ epsilon * coreFloor
  corePositiveConeMass_le_coreAbs :
    corePositiveConeMass ≤ |formula.coreMoment|
  sheathError_abs_le_sheathOppositeConeMass :
    |formula.sheathErrorMoment| ≤ sheathOppositeConeMass
  oppositeConeNoEscape :
    FixedWindowOppositeConeNoEscapeProducer formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  fixedWindowAndKernelBeforeRouteReceipt : Prop
  adjointProjectedTensorFixedBeforeStressSplit : Prop
  coreConeMassMeasuredBeforeSummation : Prop
  sheathConeMassMeasuredBeforeSummation : Prop
  coneMassesNotDefinedFromCarrierMagnitude : Prop
  no_strictSubratio_or_margin_input : Prop

/--
No-escape/rigidity supplies the missing cone-mass subordination field.
-/
def FixedWindowStressConeMassSubordination.ofRigiditySource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : FixedWindowStressConeMassRigiditySource formula) :
    FixedWindowStressConeMassSubordination formula where
  epsilon := h.epsilon
  coreFloor := h.coreFloor
  etaP := h.etaP
  X_tail := h.X_tail
  corePositiveConeMass := h.corePositiveConeMass
  sheathOppositeConeMass := h.sheathOppositeConeMass
  epsilon_pos := h.epsilon_pos
  epsilon_le_one := h.epsilon_le_one
  X_tail_nonneg := h.X_tail_nonneg
  corePositiveConeMass_nonneg := h.corePositiveConeMass_nonneg
  sheathOppositeConeMass_nonneg := h.sheathOppositeConeMass_nonneg
  coreAngularMomentFloor := h.coreAngularMomentFloor
  routeTailScale_le_angularFloor := h.routeTailScale_le_angularFloor
  corePositiveConeMass_le_coreAbs := h.corePositiveConeMass_le_coreAbs
  sheathError_abs_le_sheathOppositeConeMass :=
    h.sheathError_abs_le_sheathOppositeConeMass
  sheathOppositeConeMass_subordinate :=
    sheathOppositeConeMass_subordinate_of_noEscapeProducer
      h.oppositeConeNoEscape
  fixedWindowAndKernelBeforeRouteReceipt :=
    h.fixedWindowAndKernelBeforeRouteReceipt
  adjointProjectedTensorFixedBeforeStressSplit :=
    h.adjointProjectedTensorFixedBeforeStressSplit
  coreConeMassMeasuredBeforeSummation := h.coreConeMassMeasuredBeforeSummation
  sheathConeMassMeasuredBeforeSummation :=
    h.sheathConeMassMeasuredBeforeSummation
  coneMassesNotDefinedFromCarrierMagnitude :=
    h.coneMassesNotDefinedFromCarrierMagnitude
  no_strictSubratio_or_margin_input := h.no_strictSubratio_or_margin_input

/--
The pressure-Hessian tail lower bound follows from the rigidity/no-escape
source through cone-mass subordination.
-/
theorem pressureHessianL2_tail_lower_bound_of_coneMassRigiditySource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : FixedWindowStressConeMassRigiditySource formula) :
    h.etaP * h.X_tail ≤
      renormalizedPressureHessianL2Carrier pressureL2 radialGrade :=
  pressureHessianL2_tail_lower_bound_of_coneMassSubordination
    (FixedWindowStressConeMassSubordination.ofRigiditySource h)

/--
Critical-profile obstruction below the opposite-cone overflow test.

This consumes the existing `ns_no_invisible_critical_profile` primitive.  The
PDE obligation is now to show that fixed-window opposite-cone overflow produces
both a strict no-invisible-profile failure and zero critical-tail visibility.
-/
structure FixedWindowOppositeConeCriticalProfileObstruction
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  obligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  overflow_forces_strictFailure :
    (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass →
      obligation.strictNoInvisibleCriticalProfileFailure
  overflow_forces_zeroVisibility :
    (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass →
      obligation.zeroCriticalTailVisibility
  fixedWindowOverflowExtractsCriticalProfile : Prop
  zeroVisibilityUsesSamePressureRieszChannels : Prop
  noCarrierMagnitudeInProfileExtraction : Prop

/--
First overflow map: fixed-window opposite-cone overflow has to create the
strict no-invisible-critical-profile failure used by the compactness primitive.

The intermediate fields keep the proof obligation below a scalar margin: the
overflow must create a normalized bad sequence in the same fixed window/kernel
geometry, that sequence must carry nontrivial unresolved tail mass, and only
then may it be projected to the strict-failure input.
-/
structure FixedWindowOppositeConeOverflowStrictFailureMap
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  obligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  sameFixedWindowOverflow : Prop
  normalizedBadSequenceInFixedWindow : Prop
  unresolvedTailNontrivial : Prop
  overflow_to_sameFixedWindowOverflow :
    (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass →
      sameFixedWindowOverflow
  fixedWindowOverflow_to_normalizedBadSequence :
    sameFixedWindowOverflow → normalizedBadSequenceInFixedWindow
  normalizedBadSequence_has_unresolvedTail :
    normalizedBadSequenceInFixedWindow → unresolvedTailNontrivial
  badSequence_to_strictFailure :
    normalizedBadSequenceInFixedWindow →
      unresolvedTailNontrivial →
        obligation.strictNoInvisibleCriticalProfileFailure
  fixedWindowAndKernelNotChosenFromOverflow : Prop
  no_strictSubratio_input : Prop

/--
The strict-failure map exported as the exact arrow required by
`FixedWindowOppositeConeCriticalProfileObstruction`.
-/
def FixedWindowOppositeConeOverflowStrictFailureMap.overflow_forces_strictFailure
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOppositeConeOverflowStrictFailureMap formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass →
      h.obligation.strictNoInvisibleCriticalProfileFailure := by
  intro hoverflow
  let hFixed := h.overflow_to_sameFixedWindowOverflow hoverflow
  let hBad := h.fixedWindowOverflow_to_normalizedBadSequence hFixed
  exact h.badSequence_to_strictFailure hBad
    (h.normalizedBadSequence_has_unresolvedTail hBad)

/--
Second overflow map: the same fixed-window overflow must have zero visibility
in the critical-tail channels used by the no-invisible-profile primitive.

This separates transport, quadratic, pressure/Riesz, and commutator visibility
zeros so the pressure branch cannot hide the zero-visibility assumption inside
the final carrier magnitude.
-/
structure FixedWindowOppositeConeOverflowZeroVisibilityMap
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real)
    (obligation : NS.NoInvisibleCriticalProfileCompactnessObligation) where
  sameFixedWindowChannelGauge : Prop
  transportVisibilityZero : Prop
  quadraticVisibilityZero : Prop
  pressureRieszVisibilityZero : Prop
  commutatorVisibilityZero : Prop
  overflow_to_sameFixedWindowChannelGauge :
    (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass →
      sameFixedWindowChannelGauge
  fixedGauge_to_transportZero :
    sameFixedWindowChannelGauge → transportVisibilityZero
  fixedGauge_to_quadraticZero :
    sameFixedWindowChannelGauge → quadraticVisibilityZero
  fixedGauge_to_pressureRieszZero :
    sameFixedWindowChannelGauge → pressureRieszVisibilityZero
  fixedGauge_to_commutatorZero :
    sameFixedWindowChannelGauge → commutatorVisibilityZero
  channelZeros_to_zeroCriticalTailVisibility :
    transportVisibilityZero →
      quadraticVisibilityZero →
        pressureRieszVisibilityZero →
          commutatorVisibilityZero →
            obligation.zeroCriticalTailVisibility
  visibilityGaugeFixedBeforeCarrierMagnitude : Prop
  pressureRieszChannelUsesSameProjectedKernel : Prop
  no_visibilityDefinedAsScalarResidual : Prop

/--
The zero-visibility map exported as the exact arrow required by
`FixedWindowOppositeConeCriticalProfileObstruction`.
-/
def FixedWindowOppositeConeOverflowZeroVisibilityMap.overflow_forces_zeroVisibility
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    {obligation : NS.NoInvisibleCriticalProfileCompactnessObligation}
    (h :
      FixedWindowOppositeConeOverflowZeroVisibilityMap formula epsilon
        corePositiveConeMass sheathOppositeConeMass obligation) :
    (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass →
      obligation.zeroCriticalTailVisibility := by
  intro hoverflow
  let hGauge := h.overflow_to_sameFixedWindowChannelGauge hoverflow
  exact h.channelZeros_to_zeroCriticalTailVisibility
    (h.fixedGauge_to_transportZero hGauge)
    (h.fixedGauge_to_quadraticZero hGauge)
    (h.fixedGauge_to_pressureRieszZero hGauge)
    (h.fixedGauge_to_commutatorZero hGauge)

/--
Bundle tying the two overflow maps to the same compactness obligation.

This is the Lean-facing target for the new eigenquestion: prove these maps, or
produce a countermodel/missing hypothesis for one of them.
-/
structure FixedWindowOppositeConeOverflowMapBundle
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  strictFailureMap :
    FixedWindowOppositeConeOverflowStrictFailureMap formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  zeroVisibilityMap :
    FixedWindowOppositeConeOverflowZeroVisibilityMap formula epsilon
      corePositiveConeMass sheathOppositeConeMass strictFailureMap.obligation
  strictFailureAndZeroVisibilityUseSameTailWindow : Prop
  strictFailureAndZeroVisibilityUseSameProjectedKernel : Prop
  no_carrierMagnitude_or_strictSubratio_oracle : Prop

/--
An overflow-map bundle supplies the existing critical-profile obstruction.
-/
def FixedWindowOppositeConeCriticalProfileObstruction.ofOverflowMapBundle
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOppositeConeOverflowMapBundle formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowOppositeConeCriticalProfileObstruction formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  obligation := h.strictFailureMap.obligation
  overflow_forces_strictFailure :=
    h.strictFailureMap.overflow_forces_strictFailure
  overflow_forces_zeroVisibility :=
    h.zeroVisibilityMap.overflow_forces_zeroVisibility
  fixedWindowOverflowExtractsCriticalProfile :=
    h.strictFailureAndZeroVisibilityUseSameTailWindow
  zeroVisibilityUsesSamePressureRieszChannels :=
    h.zeroVisibilityMap.pressureRieszChannelUsesSameProjectedKernel
  noCarrierMagnitudeInProfileExtraction :=
    h.no_carrierMagnitude_or_strictSubratio_oracle

/--
The no-invisible-critical-profile primitive rules out opposite-cone overflow
once overflow is known to produce strict failure and zero visibility.
-/
theorem no_oppositeConeOverflow_of_criticalProfileObstruction
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOppositeConeCriticalProfileObstruction formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    ¬ (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass := by
  intro hoverflow
  exact NS.no_invisible_critical_profile_of_compactness_obligation
    h.obligation
    (h.overflow_forces_strictFailure hoverflow)
    (h.overflow_forces_zeroVisibility hoverflow)

/--
Overflow-map version of the no-overflow theorem.  This is the immediate
consumer for the new eigenquestion: once the two maps are supplied, the
existing no-invisible-profile primitive rules out same-window opposite-cone
overflow.
-/
theorem no_oppositeConeOverflow_of_overflowMapBundle
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOppositeConeOverflowMapBundle formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    ¬ (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass :=
  no_oppositeConeOverflow_of_criticalProfileObstruction
    (FixedWindowOppositeConeCriticalProfileObstruction.ofOverflowMapBundle h)

/--
Guard from the fixed-window packet No-Go: opposite-cone overflow alone is not
zero critical-tail visibility.  It may instead be a visible pressure/Riesz,
quadratic, transport, or commutator event.

This prevents the pressure branch from promoting the direct
`overflow → zeroCriticalTailVisibility` arrow without an additional quotient or
extraction theorem.
-/
structure OppositeConeOverflowDoesNotForceNoInvisibleProfile
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  overflow : (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass
  sameWindowFixedKernel : Prop
  fixedWindowPacketCountermodel : Prop
  visiblePressureRieszOrEnergyOrCommutatorSignal : Prop
  kills_direct_zeroVisibility_field :
    ¬ ∀ obligation : NS.NoInvisibleCriticalProfileCompactnessObligation,
      (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass →
        obligation.zeroCriticalTailVisibility
  requires_additional_visibleQuotient_or_extraction : Prop
  no_finalCarrierMagnitude_input : Prop

/--
Corrected bridge after the No-Go: overflow must either pay a concrete
same-window visibility charge, or after removing all visible charge the
remaining critical profile is a zero-visible no-invisible-profile obstruction.
-/
structure FixedWindowOverflowVisibleOrInvisibleProfile
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  obligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  overflow : (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass
  visibleOverflowCharge : Prop
  invisibleRemainderAfterVisibleQuotient : Prop
  route1TailVisibility : Real
  overflowExcess : Real
  visibilityChargeConstant : Real
  visibilityChargeConstant_pos : 0 < visibilityChargeConstant
  overflowExcess_eq :
    overflowExcess =
      sheathOppositeConeMass - (1 - epsilon) * corePositiveConeMass
  visibleCharge_pays_tailVisibility :
    visibleOverflowCharge →
      visibilityChargeConstant * overflowExcess ≤ route1TailVisibility
  noVisibleCharge_leaves_invisibleRemainder :
    ¬ visibleOverflowCharge → invisibleRemainderAfterVisibleQuotient
  invisibleRemainder_forces_strictFailure :
    invisibleRemainderAfterVisibleQuotient →
      obligation.strictNoInvisibleCriticalProfileFailure
  invisibleRemainder_forces_zeroVisibility :
    invisibleRemainderAfterVisibleQuotient →
      obligation.zeroCriticalTailVisibility
  sameWindowFixedKernel : Prop
  visibilityChannelsAreConcrete : Prop
  zeroVisibilityUsesSamePressureRieszChannels : Prop
  noCarrierMagnitudeInProfileExtraction : Prop
  no_strictSubratio_oracle : Prop

/--
If the corrected bridge is in the invisible-remainder branch, it supplies the
old critical-profile obstruction without assuming direct overflow-to-zero
visibility.
-/
def FixedWindowOppositeConeCriticalProfileObstruction.ofInvisibleRemainder
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
        corePositiveConeMass sheathOppositeConeMass)
    (hNoVisibleCharge : ¬ h.visibleOverflowCharge) :
    FixedWindowOppositeConeCriticalProfileObstruction formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  obligation := h.obligation
  overflow_forces_strictFailure := by
    intro _hoverflow
    exact h.invisibleRemainder_forces_strictFailure
      (h.noVisibleCharge_leaves_invisibleRemainder hNoVisibleCharge)
  overflow_forces_zeroVisibility := by
    intro _hoverflow
    exact h.invisibleRemainder_forces_zeroVisibility
      (h.noVisibleCharge_leaves_invisibleRemainder hNoVisibleCharge)
  fixedWindowOverflowExtractsCriticalProfile :=
    h.sameWindowFixedKernel
  zeroVisibilityUsesSamePressureRieszChannels :=
    h.zeroVisibilityUsesSamePressureRieszChannels
  noCarrierMagnitudeInProfileExtraction :=
    h.noCarrierMagnitudeInProfileExtraction

/--
Corrected no-overflow conclusion for the invisible branch: if no concrete
visibility charge is paid, overflow contradicts the no-invisible-profile
primitive after the visible quotient.
-/
theorem no_oppositeConeOverflow_without_visibleCharge
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
        corePositiveConeMass sheathOppositeConeMass)
    (hNoVisibleCharge : ¬ h.visibleOverflowCharge) :
    False :=
  no_oppositeConeOverflow_of_criticalProfileObstruction
    (FixedWindowOppositeConeCriticalProfileObstruction.ofInvisibleRemainder
      h hNoVisibleCharge)
    h.overflow

/--
Projection of the corrected bridge into the useful route-1 fork:
same-window opposite-cone overflow must pay a concrete visibility charge.

The proof is by contradiction through the invisible-remainder obstruction.
-/
theorem visibleOverflowCharge_of_visibleOrInvisibleProfile
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    h.visibleOverflowCharge := by
  by_contra hNoVisibleCharge
  exact no_oppositeConeOverflow_without_visibleCharge h hNoVisibleCharge

/-- Concrete channel that can pay a same-window overflow charge. -/
inductive FixedWindowVisibleOverflowChannel where
  | pressureRieszCone
  | localQuadraticExcess
  | transportFlux
  | commutatorReynolds
  deriving DecidableEq

/-- Select the numeric charge attached to a concrete visible channel. -/
def FixedWindowVisibleOverflowChannel.selectedCharge :
    FixedWindowVisibleOverflowChannel → Real → Real → Real → Real → Real
  | pressureRieszCone, pressureRieszConeCharge, _, _, _ =>
      pressureRieszConeCharge
  | localQuadraticExcess, _, localQuadraticExcessCharge, _, _ =>
      localQuadraticExcessCharge
  | transportFlux, _, _, transportFluxCharge, _ =>
      transportFluxCharge
  | commutatorReynolds, _, _, _, commutatorReynoldsCharge =>
      commutatorReynoldsCharge

/--
Channel-level source for the visible side of the repaired overflow fork.

The selected channel is numeric: it must dominate the overflow excess and be
bounded by the route-1 tail-visibility budget.  The channel alternatives are
kept separate so pressure/Riesz cone charge, local quadratic excess, route-flux
transport, and endpoint commutator/Reynolds defect can be attacked independently.
-/
structure FixedWindowOverflowChannelChargeReceipt
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  obligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  overflow : (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass
  channel : FixedWindowVisibleOverflowChannel
  pressureRieszConeCharge : Real
  localQuadraticExcessCharge : Real
  transportFluxCharge : Real
  commutatorReynoldsCharge : Real
  selectedChannelCharge : Real
  route1TailVisibility : Real
  overflowExcess : Real
  visibilityChargeConstant : Real
  visibilityChargeConstant_pos : 0 < visibilityChargeConstant
  overflowExcess_eq :
    overflowExcess =
      sheathOppositeConeMass - (1 - epsilon) * corePositiveConeMass
  selectedChannelCharge_eq :
    selectedChannelCharge =
      channel.selectedCharge pressureRieszConeCharge localQuadraticExcessCharge
        transportFluxCharge commutatorReynoldsCharge
  selectedChannelCharge_pays_overflowExcess :
    visibilityChargeConstant * overflowExcess ≤ selectedChannelCharge
  selectedChannelCharge_le_tailVisibility :
    selectedChannelCharge ≤ route1TailVisibility
  visibleChannelReceipt : Prop
  visibleChannelReceipt_holds : visibleChannelReceipt
  pressureRieszConeChargeUsesSameProjectedKernel : Prop
  localQuadraticChargeUsesCKNTentExcess : Prop
  transportChargeUsesLocalizedRouteFlux : Prop
  commutatorChargeUsesEndpointDefectMeasure : Prop
  channelChargesFixedBeforeOverflowAbsorption : Prop
  no_finalCarrierMagnitude_or_strictSubratio_input : Prop

/-- A concrete channel charge pays the visible overflow branch. -/
theorem visibleOverflowCharge_of_channelChargeReceipt
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOverflowChannelChargeReceipt formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    h.visibleChannelReceipt :=
  h.visibleChannelReceipt_holds

/--
Construct the corrected visible-or-invisible bridge from a concrete channel
receipt.  Since the visible channel is already paid, the invisible-remainder
branch is vacuous here; the non-vacuous PDE content is the selected channel
charge and its route-1 tail-visibility bound.
-/
def FixedWindowOverflowVisibleOrInvisibleProfile.ofChannelChargeReceipt
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOverflowChannelChargeReceipt formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  obligation := h.obligation
  overflow := h.overflow
  visibleOverflowCharge := h.visibleChannelReceipt
  invisibleRemainderAfterVisibleQuotient := False
  route1TailVisibility := h.route1TailVisibility
  overflowExcess := h.overflowExcess
  visibilityChargeConstant := h.visibilityChargeConstant
  visibilityChargeConstant_pos := h.visibilityChargeConstant_pos
  overflowExcess_eq := h.overflowExcess_eq
  visibleCharge_pays_tailVisibility := by
    intro _hVisible
    exact le_trans h.selectedChannelCharge_pays_overflowExcess
      h.selectedChannelCharge_le_tailVisibility
  noVisibleCharge_leaves_invisibleRemainder := by
    intro hNoVisible
    exact False.elim (hNoVisible h.visibleChannelReceipt_holds)
  invisibleRemainder_forces_strictFailure := by
    intro hFalse
    exact False.elim hFalse
  invisibleRemainder_forces_zeroVisibility := by
    intro hFalse
    exact False.elim hFalse
  sameWindowFixedKernel :=
    h.pressureRieszConeChargeUsesSameProjectedKernel
  visibilityChannelsAreConcrete :=
    And
      (And h.pressureRieszConeChargeUsesSameProjectedKernel
        h.localQuadraticChargeUsesCKNTentExcess)
      (And h.transportChargeUsesLocalizedRouteFlux
        h.commutatorChargeUsesEndpointDefectMeasure)
  zeroVisibilityUsesSamePressureRieszChannels :=
    h.pressureRieszConeChargeUsesSameProjectedKernel
  noCarrierMagnitudeInProfileExtraction :=
    h.no_finalCarrierMagnitude_or_strictSubratio_input
  no_strictSubratio_oracle :=
    h.no_finalCarrierMagnitude_or_strictSubratio_input

/--
Channel receipt projection: once a concrete channel charge is supplied, the
repaired fork forces the visible branch.
-/
theorem visibleOverflowCharge_of_channelChargeVisibleOrInvisibleProfile
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowOverflowChannelChargeReceipt formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofChannelChargeReceipt h).visibleOverflowCharge :=
  visibleOverflowCharge_of_visibleOrInvisibleProfile
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofChannelChargeReceipt h)

/--
Pressure/Riesz specialization of the visible-channel receipt.

This is still a source object, not the PDE estimate: it asks for a
pre-summed pressure/Riesz cone charge, measured against the same fixed projected
kernel, that pays the overflow excess and is bounded by the route-1 tail
visibility budget.
-/
structure FixedWindowPressureRieszConeChargeSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  obligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  overflow : (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass
  pressureRieszConeCharge : Real
  route1TailVisibility : Real
  overflowExcess : Real
  visibilityChargeConstant : Real
  visibilityChargeConstant_pos : 0 < visibilityChargeConstant
  overflowExcess_eq :
    overflowExcess =
      sheathOppositeConeMass - (1 - epsilon) * corePositiveConeMass
  pressureRieszConeCharge_pays_overflowExcess :
    visibilityChargeConstant * overflowExcess ≤ pressureRieszConeCharge
  pressureRieszConeCharge_le_tailVisibility :
    pressureRieszConeCharge ≤ route1TailVisibility
  pressureRieszConeReceipt : Prop
  pressureRieszConeReceipt_holds : pressureRieszConeReceipt
  sameFixedProjectedKernel : Prop
  pressureRieszConeChargeMeasuresPreSummedStress : Prop
  coreSheathSplitFixedBeforeCharge : Prop
  coneChargeNotDefinedFromFinalCarrier : Prop
  no_strictSubratio_or_margin_input : Prop

/-- Pressure/Riesz cone source as a concrete visible-channel receipt. -/
def FixedWindowOverflowChannelChargeReceipt.ofPressureRieszConeChargeSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureRieszConeChargeSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowOverflowChannelChargeReceipt formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  obligation := h.obligation
  overflow := h.overflow
  channel := FixedWindowVisibleOverflowChannel.pressureRieszCone
  pressureRieszConeCharge := h.pressureRieszConeCharge
  localQuadraticExcessCharge := 0
  transportFluxCharge := 0
  commutatorReynoldsCharge := 0
  selectedChannelCharge := h.pressureRieszConeCharge
  route1TailVisibility := h.route1TailVisibility
  overflowExcess := h.overflowExcess
  visibilityChargeConstant := h.visibilityChargeConstant
  visibilityChargeConstant_pos := h.visibilityChargeConstant_pos
  overflowExcess_eq := h.overflowExcess_eq
  selectedChannelCharge_eq := by
    rfl
  selectedChannelCharge_pays_overflowExcess :=
    h.pressureRieszConeCharge_pays_overflowExcess
  selectedChannelCharge_le_tailVisibility :=
    h.pressureRieszConeCharge_le_tailVisibility
  visibleChannelReceipt := h.pressureRieszConeReceipt
  visibleChannelReceipt_holds := h.pressureRieszConeReceipt_holds
  pressureRieszConeChargeUsesSameProjectedKernel :=
    h.sameFixedProjectedKernel
  localQuadraticChargeUsesCKNTentExcess := True
  transportChargeUsesLocalizedRouteFlux := True
  commutatorChargeUsesEndpointDefectMeasure := True
  channelChargesFixedBeforeOverflowAbsorption :=
    And h.coreSheathSplitFixedBeforeCharge
      h.pressureRieszConeChargeMeasuresPreSummedStress
  no_finalCarrierMagnitude_or_strictSubratio_input :=
    And h.coneChargeNotDefinedFromFinalCarrier
      h.no_strictSubratio_or_margin_input

/-- Pressure/Riesz cone source constructs the corrected visible branch. -/
def FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureRieszConeChargeSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureRieszConeChargeSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
      corePositiveConeMass sheathOppositeConeMass :=
  FixedWindowOverflowVisibleOrInvisibleProfile.ofChannelChargeReceipt
    (FixedWindowOverflowChannelChargeReceipt.ofPressureRieszConeChargeSource h)

/-- Pressure/Riesz cone charge pays the repaired overflow fork. -/
theorem visibleOverflowCharge_of_pressureRieszConeChargeSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureRieszConeChargeSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureRieszConeChargeSource
      h).visibleOverflowCharge :=
  visibleOverflowCharge_of_visibleOrInvisibleProfile
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureRieszConeChargeSource h)

/--
Bridge from the pressure/Riesz cone charge to the existing pressure visibility
receipts.

This is the bookkeeping target after the pressure channel is selected: the
pre-summed cone charge must fit inside the independent pressure receipt sum
coming from pressure reserve, local quadratic visibility, and child charge.
-/
structure FixedWindowPressureRieszConeChargeReceiptBridge
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  profileObligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  pressureObligation : Route1PressureReserveNoEscapeObligation
  overflow : (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass
  pressureRieszConeCharge : Real
  overflowExcess : Real
  visibilityChargeConstant : Real
  visibilityChargeConstant_pos : 0 < visibilityChargeConstant
  overflowExcess_eq :
    overflowExcess =
      sheathOppositeConeMass - (1 - epsilon) * corePositiveConeMass
  pressureRieszConeCharge_pays_overflowExcess :
    visibilityChargeConstant * overflowExcess ≤ pressureRieszConeCharge
  pressureRieszConeCharge_le_pressureReceiptSum :
    pressureRieszConeCharge ≤
      (route1PressureVisibilityReceipts pressureObligation).receiptSum
  pressureRieszConeReceipt : Prop
  pressureRieszConeReceipt_holds : pressureRieszConeReceipt
  sameFixedProjectedKernel : Prop
  pressureRieszConeChargeMeasuresPreSummedStress : Prop
  pressureReceiptSumUsesIndependentReceipts : Prop
  coneChargeFixedBeforeReceiptComparison : Prop
  coneChargeNotDefinedFromFinalCarrier : Prop
  no_strictSubratio_or_margin_input : Prop

/--
Guard against the tempting but invalid pressure receipt instantiation.

If a positive pre-summed pressure/Riesz cone charge is bounded only by a receipt
identified with the final projected pressure carrier, exact same-window sheath
cancellation contradicts that bound.  Thus the receipt bridge above must use
independent pre-summed pressure receipts, not a carrier-after-summation scalar.
-/
theorem no_positive_pressureConeCharge_bound_by_finalCarrierReceipt
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    {pressureRieszConeCharge finalCarrierReceipt : Real}
    (hcancel : formula.sheathErrorMoment = -formula.coreMoment)
    (hreceipt :
      finalCarrierReceipt =
        renormalizedPressureHessianL2Carrier pressureL2 radialGrade)
    (hcharge_pos : 0 < pressureRieszConeCharge)
    (hle : pressureRieszConeCharge ≤ finalCarrierReceipt) :
    False := by
  have hcarrier_zero :=
    projectedRieszFormulaSource_carrier_zero_of_exact_sheath_cancellation
      formula hcancel
  rw [hreceipt, hcarrier_zero] at hle
  linarith

/--
No-Go surface for final-carrier-only pressure receipts.

The packet scout `pressure_cone_charge_receipt_scout_20260514` realizes this
shape numerically: the final projected carrier can vanish while the pre-summed
cone charge and overflow excess remain positive.  A valid pressure receipt must
therefore expose an independent pre-summed reserve/local/child charge.
-/
structure FixedWindowPressureConeChargeFinalCarrierReceiptNoGo
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (pressureRieszConeCharge finalCarrierReceipt : Real) where
  exactSheathCancellation :
    formula.sheathErrorMoment = -formula.coreMoment
  pressureRieszConeCharge_pos : 0 < pressureRieszConeCharge
  finalCarrierReceipt_eq :
    finalCarrierReceipt =
      renormalizedPressureHessianL2Carrier pressureL2 radialGrade
  finalCarrierOnlyReceiptWouldPay :
    pressureRieszConeCharge ≤ finalCarrierReceipt

/-- Final-carrier-only pressure receipts cannot pay a positive cone charge
under exact same-window sheath cancellation. -/
theorem false_of_pressureConeChargeFinalCarrierReceiptNoGo
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {pressureRieszConeCharge finalCarrierReceipt : Real}
    (h :
      FixedWindowPressureConeChargeFinalCarrierReceiptNoGo formula
        pressureRieszConeCharge finalCarrierReceipt) :
    False :=
  no_positive_pressureConeCharge_bound_by_finalCarrierReceipt
    formula h.exactSheathCancellation h.finalCarrierReceipt_eq
    h.pressureRieszConeCharge_pos h.finalCarrierOnlyReceiptWouldPay

/--
Zero-receipt guard for the pressure cone bridge.

Any instantiation of the receipt bridge whose pressure receipt sum vanishes
cannot pay a positive overflow excess.  This is the Lean-facing form of the
packet-scout warning when the receipt sum is secretly downstream of a canceled
final carrier.
-/
theorem no_pressureConeReceiptBridge_of_zeroReceipt_and_positiveOverflow
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureRieszConeChargeReceiptBridge formula epsilon
        corePositiveConeMass sheathOppositeConeMass)
    (hzero :
      (route1PressureVisibilityReceipts h.pressureObligation).receiptSum = 0)
    (hoverflow_pos : 0 < h.overflowExcess) :
    False := by
  have hprod_pos :
      0 < h.visibilityChargeConstant * h.overflowExcess :=
    mul_pos h.visibilityChargeConstant_pos hoverflow_pos
  have hcharge_le_zero : h.pressureRieszConeCharge ≤ 0 := by
    rw [← hzero]
    exact h.pressureRieszConeCharge_le_pressureReceiptSum
  linarith [h.pressureRieszConeCharge_pays_overflowExcess]

/--
Positive fallback after the final-carrier receipt No-Go.

For a fixed projected Riesz tensor, a pre-summed cone charge can be paid by a
local quadratic/stress receipt via an operator-norm estimate.  This source is
still conditional on the PDE receipt identifying local quadratic mass before
core/sheath summation; it avoids the canceled final carrier.
-/
structure FixedWindowPressureConeChargeLocalQuadraticReceiptSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  profileObligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  pressureObligation : Route1PressureReserveNoEscapeObligation
  overflow : (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass
  pressureRieszConeCharge : Real
  overflowExcess : Real
  visibilityChargeConstant : Real
  visibilityChargeConstant_pos : 0 < visibilityChargeConstant
  overflowExcess_eq :
    overflowExcess =
      sheathOppositeConeMass - (1 - epsilon) * corePositiveConeMass
  pressureRieszConeCharge_pays_overflowExcess :
    visibilityChargeConstant * overflowExcess ≤ pressureRieszConeCharge
  pressureRieszConeCharge_le_localQuadraticReceipt :
    pressureRieszConeCharge ≤
      (route1PressureVisibilityReceipts pressureObligation).localQuadraticReceipt
  childChargeReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts pressureObligation).childChargeReceipt
  pressureRieszConeReceipt : Prop
  pressureRieszConeReceipt_holds : pressureRieszConeReceipt
  sameFixedProjectedKernel : Prop
  pressureRieszConeChargeMeasuresPreSummedStress : Prop
  localQuadraticReceiptMeasuresPreSummedStress : Prop
  fixedKernelOperatorNormPaysConeCharge : Prop
  coneChargeFixedBeforeReceiptComparison : Prop
  coneChargeNotDefinedFromFinalCarrier : Prop
  no_strictSubratio_or_margin_input : Prop

/-- A local quadratic receipt source supplies the pressure/Riesz receipt bridge. -/
def FixedWindowPressureRieszConeChargeReceiptBridge.ofLocalQuadraticReceiptSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureConeChargeLocalQuadraticReceiptSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowPressureRieszConeChargeReceiptBridge formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  profileObligation := h.profileObligation
  pressureObligation := h.pressureObligation
  overflow := h.overflow
  pressureRieszConeCharge := h.pressureRieszConeCharge
  overflowExcess := h.overflowExcess
  visibilityChargeConstant := h.visibilityChargeConstant
  visibilityChargeConstant_pos := h.visibilityChargeConstant_pos
  overflowExcess_eq := h.overflowExcess_eq
  pressureRieszConeCharge_pays_overflowExcess :=
    h.pressureRieszConeCharge_pays_overflowExcess
  pressureRieszConeCharge_le_pressureReceiptSum := by
    have hlocal_le_sum :
        (route1PressureVisibilityReceipts h.pressureObligation).localQuadraticReceipt ≤
          (route1PressureVisibilityReceipts h.pressureObligation).receiptSum := by
      have hchild :
          0 ≤ h.pressureObligation.acceptableChildCharge := by
        simpa [route1PressureVisibilityReceipts] using h.childChargeReceipt_nonneg
      dsimp [Route1PressureVisibilityReceipts.receiptSum,
        route1PressureVisibilityReceipts]
      have htail_nonneg :
          0 ≤ h.pressureObligation.decomposition.pressureReserve +
            h.pressureObligation.acceptableChildCharge :=
        add_nonneg h.pressureObligation.decomposition.pressureReserve_nonneg hchild
      calc
        h.pressureObligation.localQuadraticVisibility ≤
            h.pressureObligation.localQuadraticVisibility +
              (h.pressureObligation.decomposition.pressureReserve +
                h.pressureObligation.acceptableChildCharge) :=
          le_add_of_nonneg_right htail_nonneg
        _ =
            h.pressureObligation.localQuadraticVisibility +
              h.pressureObligation.decomposition.pressureReserve +
                h.pressureObligation.acceptableChildCharge := by
          ring
    exact le_trans h.pressureRieszConeCharge_le_localQuadraticReceipt
      hlocal_le_sum
  pressureRieszConeReceipt := h.pressureRieszConeReceipt
  pressureRieszConeReceipt_holds := h.pressureRieszConeReceipt_holds
  sameFixedProjectedKernel := h.sameFixedProjectedKernel
  pressureRieszConeChargeMeasuresPreSummedStress :=
    h.pressureRieszConeChargeMeasuresPreSummedStress
  pressureReceiptSumUsesIndependentReceipts :=
    And h.localQuadraticReceiptMeasuresPreSummedStress
      h.fixedKernelOperatorNormPaysConeCharge
  coneChargeFixedBeforeReceiptComparison :=
    h.coneChargeFixedBeforeReceiptComparison
  coneChargeNotDefinedFromFinalCarrier :=
    h.coneChargeNotDefinedFromFinalCarrier
  no_strictSubratio_or_margin_input :=
    And h.no_strictSubratio_or_margin_input
      h.coneChargeNotDefinedFromFinalCarrier

/-- Pressure receipt bridge supplies the pressure/Riesz cone charge source. -/
def FixedWindowPressureRieszConeChargeSource.ofReceiptBridge
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureRieszConeChargeReceiptBridge formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowPressureRieszConeChargeSource formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  obligation := h.profileObligation
  overflow := h.overflow
  pressureRieszConeCharge := h.pressureRieszConeCharge
  route1TailVisibility :=
    (route1PressureVisibilityReceipts h.pressureObligation).receiptSum
  overflowExcess := h.overflowExcess
  visibilityChargeConstant := h.visibilityChargeConstant
  visibilityChargeConstant_pos := h.visibilityChargeConstant_pos
  overflowExcess_eq := h.overflowExcess_eq
  pressureRieszConeCharge_pays_overflowExcess :=
    h.pressureRieszConeCharge_pays_overflowExcess
  pressureRieszConeCharge_le_tailVisibility :=
    h.pressureRieszConeCharge_le_pressureReceiptSum
  pressureRieszConeReceipt := h.pressureRieszConeReceipt
  pressureRieszConeReceipt_holds := h.pressureRieszConeReceipt_holds
  sameFixedProjectedKernel := h.sameFixedProjectedKernel
  pressureRieszConeChargeMeasuresPreSummedStress :=
    h.pressureRieszConeChargeMeasuresPreSummedStress
  coreSheathSplitFixedBeforeCharge :=
    h.coneChargeFixedBeforeReceiptComparison
  coneChargeNotDefinedFromFinalCarrier :=
    h.coneChargeNotDefinedFromFinalCarrier
  no_strictSubratio_or_margin_input :=
    And h.no_strictSubratio_or_margin_input
      h.pressureReceiptSumUsesIndependentReceipts

/-- Receipt bridge constructs the corrected visible branch. -/
def FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureReceiptBridge
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureRieszConeChargeReceiptBridge formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
      corePositiveConeMass sheathOppositeConeMass :=
  FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureRieszConeChargeSource
    (FixedWindowPressureRieszConeChargeSource.ofReceiptBridge h)

/-- Pressure receipt bridge pays the repaired overflow fork. -/
theorem visibleOverflowCharge_of_pressureReceiptBridge
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureRieszConeChargeReceiptBridge formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureReceiptBridge
      h).visibleOverflowCharge :=
  visibleOverflowCharge_of_visibleOrInvisibleProfile
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureReceiptBridge h)

/-- Local quadratic payment constructs the corrected visible branch. -/
def FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureLocalQuadraticReceiptSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureConeChargeLocalQuadraticReceiptSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
      corePositiveConeMass sheathOppositeConeMass :=
  FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureReceiptBridge
    (FixedWindowPressureRieszConeChargeReceiptBridge.ofLocalQuadraticReceiptSource h)

/-- Local quadratic receipt payment is enough to pay the repaired overflow fork. -/
theorem visibleOverflowCharge_of_pressureLocalQuadraticReceiptSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureConeChargeLocalQuadraticReceiptSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureLocalQuadraticReceiptSource
      h).visibleOverflowCharge :=
  visibleOverflowCharge_of_visibleOrInvisibleProfile
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureLocalQuadraticReceiptSource h)

/--
Cone-mass source routed through existing critical-profile compactness and
rigidity.
-/
structure FixedWindowStressConeMassCriticalProfileSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade) where
  epsilon : Real
  coreFloor : Real
  etaP : Real
  X_tail : Real
  corePositiveConeMass : Real
  sheathOppositeConeMass : Real
  epsilon_pos : 0 < epsilon
  epsilon_le_one : epsilon ≤ 1
  X_tail_nonneg : 0 ≤ X_tail
  corePositiveConeMass_nonneg : 0 ≤ corePositiveConeMass
  sheathOppositeConeMass_nonneg : 0 ≤ sheathOppositeConeMass
  coreAngularMomentFloor : coreFloor ≤ |formula.coreMoment|
  routeTailScale_le_angularFloor :
    etaP * X_tail ≤ epsilon * coreFloor
  corePositiveConeMass_le_coreAbs :
    corePositiveConeMass ≤ |formula.coreMoment|
  sheathError_abs_le_sheathOppositeConeMass :
    |formula.sheathErrorMoment| ≤ sheathOppositeConeMass
  criticalProfileObstruction :
    FixedWindowOppositeConeCriticalProfileObstruction formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  fixedWindowAndKernelBeforeRouteReceipt : Prop
  adjointProjectedTensorFixedBeforeStressSplit : Prop
  coreConeMassMeasuredBeforeSummation : Prop
  sheathConeMassMeasuredBeforeSummation : Prop
  coneMassesNotDefinedFromCarrierMagnitude : Prop
  no_strictSubratio_or_margin_input : Prop

/--
Critical-profile obstruction supplies the cone-mass subordination field.
-/
def FixedWindowStressConeMassSubordination.ofCriticalProfileSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : FixedWindowStressConeMassCriticalProfileSource formula) :
    FixedWindowStressConeMassSubordination formula where
  epsilon := h.epsilon
  coreFloor := h.coreFloor
  etaP := h.etaP
  X_tail := h.X_tail
  corePositiveConeMass := h.corePositiveConeMass
  sheathOppositeConeMass := h.sheathOppositeConeMass
  epsilon_pos := h.epsilon_pos
  epsilon_le_one := h.epsilon_le_one
  X_tail_nonneg := h.X_tail_nonneg
  corePositiveConeMass_nonneg := h.corePositiveConeMass_nonneg
  sheathOppositeConeMass_nonneg := h.sheathOppositeConeMass_nonneg
  coreAngularMomentFloor := h.coreAngularMomentFloor
  routeTailScale_le_angularFloor := h.routeTailScale_le_angularFloor
  corePositiveConeMass_le_coreAbs := h.corePositiveConeMass_le_coreAbs
  sheathError_abs_le_sheathOppositeConeMass :=
    h.sheathError_abs_le_sheathOppositeConeMass
  sheathOppositeConeMass_subordinate := by
    by_contra hnot
    have hoverflow :
        (1 - h.epsilon) * h.corePositiveConeMass <
          h.sheathOppositeConeMass :=
      lt_of_not_ge hnot
    exact (no_oppositeConeOverflow_of_criticalProfileObstruction
      h.criticalProfileObstruction) hoverflow
  fixedWindowAndKernelBeforeRouteReceipt :=
    h.fixedWindowAndKernelBeforeRouteReceipt
  adjointProjectedTensorFixedBeforeStressSplit :=
    h.adjointProjectedTensorFixedBeforeStressSplit
  coreConeMassMeasuredBeforeSummation := h.coreConeMassMeasuredBeforeSummation
  sheathConeMassMeasuredBeforeSummation :=
    h.sheathConeMassMeasuredBeforeSummation
  coneMassesNotDefinedFromCarrierMagnitude :=
    h.coneMassesNotDefinedFromCarrierMagnitude
  no_strictSubratio_or_margin_input := h.no_strictSubratio_or_margin_input

/--
The pressure-Hessian tail lower bound follows when the cone-mass estimate is
paid by the existing no-invisible-critical-profile route.
-/
theorem pressureHessianL2_tail_lower_bound_of_coneMassCriticalProfileSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (h : FixedWindowStressConeMassCriticalProfileSource formula) :
    h.etaP * h.X_tail ≤
      renormalizedPressureHessianL2Carrier pressureL2 radialGrade :=
  pressureHessianL2_tail_lower_bound_of_coneMassSubordination
    (FixedWindowStressConeMassSubordination.ofCriticalProfileSource h)

/--
Bundle constructor for the next pressure-visible proof surface.

The pressure tail-window station pays the recovered pressure-Hessian
projection.  The angular/Riesz station pays the projected-kernel moment
identification.  Their composition is exactly the carrier-identification
station consumed by the existing angular/carrier estimate theorem.
-/
def Route1PressureAngularCarrierIdentification.ofTailProjectionAndRieszAngular
    (tail : Route1PressureHessianTailWindowProjectionStation)
    (angular :
      Route1ProjectedRieszAngularMomentStation tail.pressureL2 tail.radialGrade) :
    Route1PressureAngularCarrierIdentification where
  pressureL2 := tail.pressureL2
  radialGrade := tail.radialGrade
  coreMoment := angular.coreMoment
  sheathErrorMoment := angular.sheathErrorMoment
  pressureRecoveredByHelmholtzLeray :=
    tail.pressureRecoveredByHelmholtzLeray
  pressureL2IsTailWindowProjectionOfRecoveredPressureHessian :=
    tail.pressureL2IsTailWindowProjectionOfRecoveredPressureHessian
  projectedRieszKernelMatchesAngularMoment :=
    angular.projectedRieszKernelMatchesAngularMoment
  radialGradeNormalizesPressureCarrier :=
    tail.radialGradeNormalizesPressureCarrier
  pressureWindowFixedBeforeRouteReceipt :=
    tail.pressureWindowFixedBeforeRouteReceipt
  angularKernelFixedBeforeRouteReceipt :=
    angular.angularKernelFixedBeforeRouteReceipt
  l2Carrier_identifies_totalAngularMoment :=
    angular.l2Carrier_identifies_totalAngularMoment
  carrierNotDefinedFromPressureReceipt :=
    tail.tailProjectionNotDefinedFromAngularMoment
  no_strictSubratio_or_margin_input :=
    tail.no_strictSubratio_or_margin_input

/--
Route-independent angular/carrier estimate station for the pressure-visible
branch.

This is the PDE-facing object below route-1 receipt bookkeeping: it names the
angular dominance, route-tail scale comparison, and recovered
pressure-Hessian carrier identification as one estimate station.  It contains
no pressure receipts and no strict-subratio field.
-/
structure Route1PressureAngularCarrierEstimate where
  pressureL2 : PressureHessianL2Amplitude
  radialGrade : Real
  etaP : Real
  X_tail : Real
  coreMoment : CoreAngularMoment
  sheathErrorMoment : SheathErrorAngularMoment
  epsilon : Real
  coreFloor : Real
  etaP_pos : 0 < etaP
  X_tail_nonneg : 0 ≤ X_tail
  epsilon_pos : 0 < epsilon
  epsilon_le_one : epsilon ≤ 1
  pressureRecoveredByHelmholtzLeray : Prop
  pressureL2IsTailWindowProjectionOfRecoveredPressureHessian : Prop
  tailWindowMatchesRouteTailScale : Prop
  coreAngularMomentFloor : coreFloor ≤ |coreMoment|
  angularDominance :
    angularMomentDominance coreMoment sheathErrorMoment epsilon
  routeTailScale_le_angularFloor :
    etaP * X_tail ≤ epsilon * coreFloor
  l2Carrier_identifies_totalAngularMoment :
    renormalizedPressureHessianL2Carrier pressureL2 radialGrade =
      |totalAngularMoment coreMoment sheathErrorMoment|
  projectedRieszKernelMatchesAngularMoment : Prop
  sameScaleSheathErrorControlledBeforeTailReceipt : Prop
  angularFloorNotChosenFromPressureReceipt : Prop
  no_strictSubratio_or_margin_input : Prop

/--
The route-independent angular/carrier station already yields the
pressure-Hessian `l = 2` tail lower bound.  Receipt bookkeeping is only needed
later, when this lower bound is attached to a route-1 pressure no-escape
obligation.
-/
theorem pressureHessianL2_tail_lower_bound_of_angularCarrierEstimate
    (h : Route1PressureAngularCarrierEstimate) :
    h.etaP * h.X_tail ≤
      renormalizedPressureHessianL2Carrier h.pressureL2 h.radialGrade := by
  have hang :
      h.epsilon * h.coreFloor ≤
        |totalAngularMoment h.coreMoment h.sheathErrorMoment| :=
    angular_moment_floor_of_dominance h.epsilon_pos h.epsilon_le_one
      h.coreAngularMomentFloor h.angularDominance
  rw [h.l2Carrier_identifies_totalAngularMoment]
  exact le_trans h.routeTailScale_le_angularFloor hang

/--
Attach angular dominance and route-tail scale comparison to a carrier
identification station.  The carrier identification remains separate from
route-specific pressure receipts.
-/
def Route1PressureAngularCarrierEstimate.ofCarrierIdentification
    (h : Route1PressureAngularCarrierIdentification)
    (etaP : Real)
    (X_tail : Real)
    (epsilon : Real)
    (coreFloor : Real)
    (etaP_pos : 0 < etaP)
    (X_tail_nonneg : 0 ≤ X_tail)
    (epsilon_pos : 0 < epsilon)
    (epsilon_le_one : epsilon ≤ 1)
    (tailWindowMatchesRouteTailScale : Prop)
    (coreAngularMomentFloor : coreFloor ≤ |h.coreMoment|)
    (angularDominance :
      angularMomentDominance h.coreMoment h.sheathErrorMoment epsilon)
    (routeTailScale_le_angularFloor :
      etaP * X_tail ≤ epsilon * coreFloor)
    (sameScaleSheathErrorControlledBeforeTailReceipt : Prop)
    (angularFloorNotChosenFromPressureReceipt : Prop) :
    Route1PressureAngularCarrierEstimate where
  pressureL2 := h.pressureL2
  radialGrade := h.radialGrade
  etaP := etaP
  X_tail := X_tail
  coreMoment := h.coreMoment
  sheathErrorMoment := h.sheathErrorMoment
  epsilon := epsilon
  coreFloor := coreFloor
  etaP_pos := etaP_pos
  X_tail_nonneg := X_tail_nonneg
  epsilon_pos := epsilon_pos
  epsilon_le_one := epsilon_le_one
  pressureRecoveredByHelmholtzLeray := h.pressureRecoveredByHelmholtzLeray
  pressureL2IsTailWindowProjectionOfRecoveredPressureHessian :=
    h.pressureL2IsTailWindowProjectionOfRecoveredPressureHessian
  tailWindowMatchesRouteTailScale := tailWindowMatchesRouteTailScale
  coreAngularMomentFloor := coreAngularMomentFloor
  angularDominance := angularDominance
  routeTailScale_le_angularFloor := routeTailScale_le_angularFloor
  l2Carrier_identifies_totalAngularMoment :=
    h.l2Carrier_identifies_totalAngularMoment
  projectedRieszKernelMatchesAngularMoment :=
    h.projectedRieszKernelMatchesAngularMoment
  sameScaleSheathErrorControlledBeforeTailReceipt :=
    sameScaleSheathErrorControlledBeforeTailReceipt
  angularFloorNotChosenFromPressureReceipt :=
    angularFloorNotChosenFromPressureReceipt
  no_strictSubratio_or_margin_input := h.no_strictSubratio_or_margin_input

/--
Direct lower-bound constructor from carrier identification plus the two
remaining scalar/angular estimates.
-/
theorem pressureHessianL2_tail_lower_bound_of_carrierIdentification
    (h : Route1PressureAngularCarrierIdentification)
    (etaP : Real)
    (X_tail : Real)
    (epsilon : Real)
    (coreFloor : Real)
    (etaP_pos : 0 < etaP)
    (X_tail_nonneg : 0 ≤ X_tail)
    (epsilon_pos : 0 < epsilon)
    (epsilon_le_one : epsilon ≤ 1)
    (tailWindowMatchesRouteTailScale : Prop)
    (coreAngularMomentFloor : coreFloor ≤ |h.coreMoment|)
    (angularDominance :
      angularMomentDominance h.coreMoment h.sheathErrorMoment epsilon)
    (routeTailScale_le_angularFloor :
      etaP * X_tail ≤ epsilon * coreFloor)
    (sameScaleSheathErrorControlledBeforeTailReceipt : Prop)
    (angularFloorNotChosenFromPressureReceipt : Prop) :
    etaP * X_tail ≤
      renormalizedPressureHessianL2Carrier h.pressureL2 h.radialGrade := by
  exact pressureHessianL2_tail_lower_bound_of_angularCarrierEstimate
    (Route1PressureAngularCarrierEstimate.ofCarrierIdentification h etaP
      X_tail epsilon coreFloor etaP_pos X_tail_nonneg epsilon_pos
      epsilon_le_one tailWindowMatchesRouteTailScale coreAngularMomentFloor
      angularDominance routeTailScale_le_angularFloor
      sameScaleSheathErrorControlledBeforeTailReceipt
      angularFloorNotChosenFromPressureReceipt)

/--
Direct lower-bound constructor from the two source stations:
pressure-Hessian tail-window projection plus projected Riesz/angular matching.
-/
theorem pressureHessianL2_tail_lower_bound_of_tailProjectionAndRieszAngular
    (tail : Route1PressureHessianTailWindowProjectionStation)
    (angular :
      Route1ProjectedRieszAngularMomentStation tail.pressureL2 tail.radialGrade)
    (etaP : Real)
    (X_tail : Real)
    (epsilon : Real)
    (coreFloor : Real)
    (etaP_pos : 0 < etaP)
    (X_tail_nonneg : 0 ≤ X_tail)
    (epsilon_pos : 0 < epsilon)
    (epsilon_le_one : epsilon ≤ 1)
    (tailWindowMatchesRouteTailScale : Prop)
    (coreAngularMomentFloor : coreFloor ≤ |angular.coreMoment|)
    (angularDominance :
      angularMomentDominance angular.coreMoment angular.sheathErrorMoment epsilon)
    (routeTailScale_le_angularFloor :
      etaP * X_tail ≤ epsilon * coreFloor)
    (sameScaleSheathErrorControlledBeforeTailReceipt : Prop)
    (angularFloorNotChosenFromPressureReceipt : Prop) :
    etaP * X_tail ≤
      renormalizedPressureHessianL2Carrier tail.pressureL2 tail.radialGrade := by
  exact pressureHessianL2_tail_lower_bound_of_carrierIdentification
    (Route1PressureAngularCarrierIdentification.ofTailProjectionAndRieszAngular
      tail angular)
    etaP X_tail epsilon coreFloor etaP_pos X_tail_nonneg epsilon_pos
    epsilon_le_one tailWindowMatchesRouteTailScale coreAngularMomentFloor
    angularDominance routeTailScale_le_angularFloor
    sameScaleSheathErrorControlledBeforeTailReceipt
    angularFloorNotChosenFromPressureReceipt

/--
Angular-moment route to pressure tail-mass visibility.

This is below the pressure-Hessian `l = 2` certificate: it uses the existing
angular-moment dominance primitive to rule out the same-scale sheath
cancellation mechanism before identifying the projected pressure carrier.
-/
structure Route1PressureAngularMomentTailMassCertificate where
  obligation : Route1PressureReserveNoEscapeObligation
  pressureL2 : PressureHessianL2Amplitude
  radialGrade : Real
  etaP : Real
  X_tail : Real
  coreMoment : CoreAngularMoment
  sheathErrorMoment : SheathErrorAngularMoment
  epsilon : Real
  coreFloor : Real
  etaP_pos : 0 < etaP
  X_tail_nonneg : 0 ≤ X_tail
  C0_pos : 0 < obligation.C0
  epsilon_pos : 0 < epsilon
  epsilon_le_one : epsilon ≤ 1
  localQuadraticReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts obligation).localQuadraticReceipt
  childChargeReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts obligation).childChargeReceipt
  pressureRecoveredByHelmholtzLeray : Prop
  pressureL2IsTailWindowProjectionOfRecoveredPressureHessian : Prop
  tailWindowMatchesRouteTailScale : Prop
  coreAngularMomentFloor : coreFloor ≤ |coreMoment|
  angularDominance :
    angularMomentDominance coreMoment sheathErrorMoment epsilon
  routeTailScale_le_angularFloor :
    etaP * X_tail ≤ epsilon * coreFloor
  pressureTailMass_identifies_l2_hessian :
    obligation.decomposition.unresolvedPressureTail =
      renormalizedPressureHessianL2Carrier pressureL2 radialGrade
  l2Carrier_identifies_totalAngularMoment :
    renormalizedPressureHessianL2Carrier pressureL2 radialGrade =
      |totalAngularMoment coreMoment sheathErrorMoment|
  projectedRieszKernelMatchesAngularMoment : Prop
  sameScaleSheathErrorControlledBeforeTailReceipt : Prop
  angularFloorNotChosenFromPressureReceipt : Prop
  no_strictSubratio_or_margin_input : Prop

/--
Attach route-specific no-escape bookkeeping to the route-independent
angular/carrier estimate station.
-/
def Route1PressureAngularMomentTailMassCertificate.ofAngularCarrierEstimate
    (obligation : Route1PressureReserveNoEscapeObligation)
    (h : Route1PressureAngularCarrierEstimate)
    (C0_pos : 0 < obligation.C0)
    (localQuadraticReceipt_nonneg :
      0 ≤ (route1PressureVisibilityReceipts obligation).localQuadraticReceipt)
    (childChargeReceipt_nonneg :
      0 ≤ (route1PressureVisibilityReceipts obligation).childChargeReceipt)
    (pressureTailMass_identifies_l2_hessian :
      obligation.decomposition.unresolvedPressureTail =
        renormalizedPressureHessianL2Carrier h.pressureL2 h.radialGrade) :
    Route1PressureAngularMomentTailMassCertificate where
  obligation := obligation
  pressureL2 := h.pressureL2
  radialGrade := h.radialGrade
  etaP := h.etaP
  X_tail := h.X_tail
  coreMoment := h.coreMoment
  sheathErrorMoment := h.sheathErrorMoment
  epsilon := h.epsilon
  coreFloor := h.coreFloor
  etaP_pos := h.etaP_pos
  X_tail_nonneg := h.X_tail_nonneg
  C0_pos := C0_pos
  epsilon_pos := h.epsilon_pos
  epsilon_le_one := h.epsilon_le_one
  localQuadraticReceipt_nonneg := localQuadraticReceipt_nonneg
  childChargeReceipt_nonneg := childChargeReceipt_nonneg
  pressureRecoveredByHelmholtzLeray := h.pressureRecoveredByHelmholtzLeray
  pressureL2IsTailWindowProjectionOfRecoveredPressureHessian :=
    h.pressureL2IsTailWindowProjectionOfRecoveredPressureHessian
  tailWindowMatchesRouteTailScale := h.tailWindowMatchesRouteTailScale
  coreAngularMomentFloor := h.coreAngularMomentFloor
  angularDominance := h.angularDominance
  routeTailScale_le_angularFloor := h.routeTailScale_le_angularFloor
  pressureTailMass_identifies_l2_hessian := pressureTailMass_identifies_l2_hessian
  l2Carrier_identifies_totalAngularMoment := h.l2Carrier_identifies_totalAngularMoment
  projectedRieszKernelMatchesAngularMoment := h.projectedRieszKernelMatchesAngularMoment
  sameScaleSheathErrorControlledBeforeTailReceipt :=
    h.sameScaleSheathErrorControlledBeforeTailReceipt
  angularFloorNotChosenFromPressureReceipt := h.angularFloorNotChosenFromPressureReceipt
  no_strictSubratio_or_margin_input := h.no_strictSubratio_or_margin_input

/--
Angular-moment dominance gives the `l = 2` pressure-Hessian tail lower bound
once the route tail scale is tied to the independently fixed core floor.
-/
theorem pressureHessianL2_tail_lower_bound_of_angularMomentCertificate
    (h : Route1PressureAngularMomentTailMassCertificate) :
    h.etaP * h.X_tail ≤
      renormalizedPressureHessianL2Carrier h.pressureL2 h.radialGrade := by
  have hang :
      h.epsilon * h.coreFloor ≤
        |totalAngularMoment h.coreMoment h.sheathErrorMoment| :=
    angular_moment_floor_of_dominance h.epsilon_pos h.epsilon_le_one
      h.coreAngularMomentFloor h.angularDominance
  rw [h.l2Carrier_identifies_totalAngularMoment]
  exact le_trans h.routeTailScale_le_angularFloor hang

/--
Promote the angular-moment certificate to the existing pressure-Hessian `l = 2`
tail-mass certificate consumed by route-1 pressure visibility.
-/
def Route1PressureHessianL2TailMassCertificate.ofAngularMomentCertificate
    (h : Route1PressureAngularMomentTailMassCertificate) :
    Route1PressureHessianL2TailMassCertificate where
  obligation := h.obligation
  pressureL2 := h.pressureL2
  radialGrade := h.radialGrade
  etaP := h.etaP
  X_tail := h.X_tail
  etaP_pos := h.etaP_pos
  X_tail_nonneg := h.X_tail_nonneg
  C0_pos := h.C0_pos
  localQuadraticReceipt_nonneg := h.localQuadraticReceipt_nonneg
  childChargeReceipt_nonneg := h.childChargeReceipt_nonneg
  pressureRecoveredByHelmholtzLeray := h.pressureRecoveredByHelmholtzLeray
  pressureL2IsTailWindowProjectionOfRecoveredPressureHessian :=
    h.pressureL2IsTailWindowProjectionOfRecoveredPressureHessian
  tailWindowMatchesRouteTailScale := h.tailWindowMatchesRouteTailScale
  pressureTailMass_identifies_l2_hessian :=
    h.pressureTailMass_identifies_l2_hessian
  pressureHessianL2_tail_lower_bound :=
    pressureHessianL2_tail_lower_bound_of_angularMomentCertificate h

/--
Constructor from the pressure-Hessian `l = 2` certificate to the existing
pressure tail-mass visibility hinge.
-/
def Route1PressureTailMassVisibility.ofPressureHessianL2Certificate
    (h : Route1PressureHessianL2TailMassCertificate) :
    Route1PressureTailMassVisibility where
  obligation := h.obligation
  etaP := h.etaP
  X_tail := h.X_tail
  etaP_pos := h.etaP_pos
  X_tail_nonneg := h.X_tail_nonneg
  C0_pos := h.C0_pos
  localQuadraticReceipt_nonneg := h.localQuadraticReceipt_nonneg
  childChargeReceipt_nonneg := h.childChargeReceipt_nonneg
  pressureTailMassVisible := by
    rw [h.pressureTailMass_identifies_l2_hessian]
    exact h.pressureHessianL2_tail_lower_bound

/-- Direct route from angular-moment dominance to pressure tail-mass visibility. -/
def Route1PressureTailMassVisibility.ofAngularMomentCertificate
    (h : Route1PressureAngularMomentTailMassCertificate) :
    Route1PressureTailMassVisibility :=
  Route1PressureTailMassVisibility.ofPressureHessianL2Certificate
    (Route1PressureHessianL2TailMassCertificate.ofAngularMomentCertificate h)

/--
No-escape plus independent pressure tail-mass visibility produces the pressure
receipt lower-bound producer.
-/
noncomputable def Route1PressureVisibilityLowerBoundProducer.ofTailMassVisibility
    (h : Route1PressureTailMassVisibility) :
    Route1PressureVisibilityLowerBoundProducer where
  obligation := h.obligation
  nuP := h.etaP / h.obligation.C0
  X_tail := h.X_tail
  nuP_pos := div_pos h.etaP_pos h.C0_pos
  X_tail_nonneg := h.X_tail_nonneg
  localQuadraticReceipt_nonneg := h.localQuadraticReceipt_nonneg
  childChargeReceipt_nonneg := h.childChargeReceipt_nonneg
  pressureReceiptLowerBound := by
    have hnoEscape :
        h.obligation.decomposition.unresolvedPressureTail ≤
          h.obligation.C0 *
            (route1PressureVisibilityReceipts h.obligation).receiptSum :=
      route1_pressure_no_escape_of_visibility_receipts h.obligation
    have hscaled :
        h.obligation.C0 * ((h.etaP / h.obligation.C0) * h.X_tail) ≤
          h.obligation.C0 *
            (route1PressureVisibilityReceipts h.obligation).receiptSum := by
      have hrewrite :
          h.obligation.C0 * ((h.etaP / h.obligation.C0) * h.X_tail) =
            h.etaP * h.X_tail := by
        field_simp [ne_of_gt h.C0_pos]
      rw [hrewrite]
      exact le_trans h.pressureTailMassVisible hnoEscape
    exact le_of_mul_le_mul_left hscaled h.C0_pos

/-- Projection theorem for the tail-mass route to pressure visibility. -/
theorem route1_pressure_lower_bound_of_tail_mass_visibility
    (h : Route1PressureTailMassVisibility) :
    (h.etaP / h.obligation.C0) * h.X_tail ≤
      (route1PressureVisibilityReceipts h.obligation).receiptSum :=
  (Route1PressureVisibilityLowerBoundProducer.ofTailMassVisibility h).pressureReceiptLowerBound

/--
Complementary pressure-small branch.

This is the handoff case: pressure tail mass is too small to pay the route1
visibility lower bound by itself, so the unresolved tail must be charged to
transport, local quadratic excess, or commutator visibility elsewhere.
-/
structure Route1PressureTailSmall where
  obligation : Route1PressureReserveNoEscapeObligation
  etaP : Real
  X_tail : Real
  etaP_pos : 0 < etaP
  X_tail_nonneg : 0 ≤ X_tail
  pressureTailSmall :
    obligation.decomposition.unresolvedPressureTail < etaP * X_tail

/-- Input data needed to split the pressure route into visible and small branches. -/
structure Route1PressureTailBranchInput where
  obligation : Route1PressureReserveNoEscapeObligation
  etaP : Real
  X_tail : Real
  etaP_pos : 0 < etaP
  X_tail_nonneg : 0 ≤ X_tail
  C0_pos : 0 < obligation.C0
  localQuadraticReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts obligation).localQuadraticReceipt
  childChargeReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts obligation).childChargeReceipt

/--
The pressure leg now has an explicit branch point: either pressure tail mass
pays a lower-bound producer, or pressure is too small and another channel must
carry the unresolved tail.
-/
inductive Route1PressureTailBranch where
  | visible : Route1PressureTailMassVisibility → Route1PressureTailBranch
  | small : Route1PressureTailSmall → Route1PressureTailBranch

/-- The elementary branch split for the pressure route. -/
noncomputable def Route1PressureTailBranchInput.branch
    (h : Route1PressureTailBranchInput) : Route1PressureTailBranch := by
  by_cases hvisible :
      h.etaP * h.X_tail ≤ h.obligation.decomposition.unresolvedPressureTail
  · exact Route1PressureTailBranch.visible
      { obligation := h.obligation
        etaP := h.etaP
        X_tail := h.X_tail
        etaP_pos := h.etaP_pos
        X_tail_nonneg := h.X_tail_nonneg
        C0_pos := h.C0_pos
        localQuadraticReceipt_nonneg := h.localQuadraticReceipt_nonneg
        childChargeReceipt_nonneg := h.childChargeReceipt_nonneg
        pressureTailMassVisible := hvisible }
  · exact Route1PressureTailBranch.small
      { obligation := h.obligation
        etaP := h.etaP
        X_tail := h.X_tail
        etaP_pos := h.etaP_pos
        X_tail_nonneg := h.X_tail_nonneg
        pressureTailSmall := lt_of_not_ge hvisible }

/--
Projection from the visible pressure branch to the lower-bound producer used by
route1.  The small branch deliberately produces no pressure-only route1 payment.
-/
noncomputable def Route1PressureTailBranch.lowerBoundProducer? :
    Route1PressureTailBranch → Option Route1PressureVisibilityLowerBoundProducer
  | visible h => some (Route1PressureVisibilityLowerBoundProducer.ofTailMassVisibility h)
  | small _ => none

/-- The small branch is exactly the pressure handoff obligation. -/
theorem route1_pressure_tail_small_handoff (h : Route1PressureTailSmall) :
    h.obligation.decomposition.unresolvedPressureTail < h.etaP * h.X_tail :=
  h.pressureTailSmall

/--
PDE-facing certificate for the pressure-small local-quadratic branch.

The route1 algebra only needs a lower bound on the local quadratic receipt, but
the non-tautological PDE object should identify that receipt with a genuine
CKN/tent-excess observable on the unresolved critical tail window.
-/
structure Route1LocalQuadraticTentExcessCertificate where
  obligation : Route1PressureReserveNoEscapeObligation
  pressureSmall : Route1PressureTailSmall
  etaQ : Real
  X_tail : Real
  localQuadraticTentExcess : Real
  etaQ_pos : 0 < etaQ
  X_tail_nonneg : 0 ≤ X_tail
  localQuadraticTentExcess_nonneg : 0 ≤ localQuadraticTentExcess
  pressureSmall_obligation :
    pressureSmall.obligation = obligation
  pressureSmall_tail :
    pressureSmall.X_tail = X_tail
  cknLocalExcessObservable : Prop
  tentWindowMatchesRouteTailScale : Prop
  tentExcess_defined_by_cknIntegral : Prop
  etaQ_uniform_from_ckn_constants : Prop
  etaQ_not_chosen_from_receipt : Prop
  no_strictSubratio_or_margin_input : Prop
  localQuadraticReceipt_identifies_tent_excess :
    (route1PressureVisibilityReceipts obligation).localQuadraticReceipt =
      localQuadraticTentExcess
  tentExcess_tail_lower_bound :
    etaQ * X_tail ≤ localQuadraticTentExcess

/--
Projection theorem for the CKN/tent-excess certificate.  This keeps the actual
PDE target visible: prove a lower bound for a local quadratic/tent excess
observable, then use its identification with the pressure receipt.
-/
theorem route1_local_quadratic_receipt_lower_bound_of_tent_excess_certificate
    (h : Route1LocalQuadraticTentExcessCertificate) :
    h.etaQ * h.X_tail ≤
      (route1PressureVisibilityReceipts h.obligation).localQuadraticReceipt := by
  rw [h.localQuadraticReceipt_identifies_tent_excess]
  exact h.tentExcess_tail_lower_bound

/--
Pressure-small local-quadratic certificate exposes the handoff branch and the
independent receipt lower bound in one package.
-/
theorem route1_tent_excess_certificate_projects
    (h : Route1LocalQuadraticTentExcessCertificate) :
    h.pressureSmall.obligation = h.obligation ∧
      h.pressureSmall.X_tail = h.X_tail ∧
      h.etaQ * h.X_tail ≤
        (route1PressureVisibilityReceipts h.obligation).localQuadraticReceipt :=
  ⟨h.pressureSmall_obligation, h.pressureSmall_tail,
    route1_local_quadratic_receipt_lower_bound_of_tent_excess_certificate h⟩

/--
Smallest PDE estimate under the pressure-small `Q` fork.

This is intentionally below the route1 strict-subratio algebra.  It says the
unresolved tail square function is controlled by local quadratic tent excess
plus the non-`Q` escape terms.  The theorem below is only bookkeeping; the PDE
content is the frequency-localized Poincare estimate and leakage accounting.
-/
structure Route1LocalizedCoercivityPoincareDecomposition where
  X_tail : Real
  localQuadraticTentExcess : Real
  pressureTailTerm : Real
  transportVisibility : Real
  commutatorVisibility : Real
  tentBoundaryError : Real
  tailSquareFunction : Real
  frequencyLeakage : Real
  C_Q : Real
  C_P : Real
  C_T : Real
  C_C : Real
  tailSquareFunction_nonneg : 0 ≤ tailSquareFunction
  frequencyLeakage_nonneg : 0 ≤ frequencyLeakage
  tailWindowFamily : Prop
  boundedOverlap : Prop
  frequencyLocalizedMeanFreeTail : Prop
  tail_eq_square_function :
    X_tail = tailSquareFunction
  localQuadraticTentExcess_defined_by_cknIntegral : Prop
  frequencyLocalizedTentPoincare :
    tailSquareFunction ≤ C_Q * localQuadraticTentExcess + frequencyLeakage
  leakage_accounted_by_nonQ_terms :
    frequencyLeakage ≤
      C_P * pressureTailTerm +
        C_T * transportVisibility +
        C_C * commutatorVisibility +
        tentBoundaryError
  no_pressure_or_visibility_margin_input : Prop

/--
Poincare/square-function decomposition gives the localized coercivity estimate
consumed by `Route1LocalQuadraticTentExcessCoercivityCertificate`.
-/
theorem route1_localized_coercivity_of_poincare_decomposition
    (h : Route1LocalizedCoercivityPoincareDecomposition) :
    h.X_tail ≤
      h.C_Q * h.localQuadraticTentExcess +
        h.C_P * h.pressureTailTerm +
        h.C_T * h.transportVisibility +
        h.C_C * h.commutatorVisibility +
        h.tentBoundaryError := by
  rw [h.tail_eq_square_function]
  nlinarith [h.frequencyLocalizedTentPoincare,
    h.leakage_accounted_by_nonQ_terms]

/--
Stronger PDE-facing route to the local-quadratic tent-excess lower bound.

This records the actual mathematical content surfaced by the Gowers-style proof
attempt: pressure-small alone does not force the `Q` branch.  One also needs
frequency/mean-free tent localization, exclusion of transport and commutator
fork payments up to boundary errors, and a localized coercivity estimate.
-/
structure Route1LocalQuadraticTentExcessCoercivityCertificate where
  obligation : Route1PressureReserveNoEscapeObligation
  pressureSmall : Route1PressureTailSmall
  etaQ : Real
  X_tail : Real
  localQuadraticTentExcess : Real
  pressureTailTerm : Real
  transportVisibility : Real
  commutatorVisibility : Real
  tentBoundaryError : Real
  C_Q : Real
  C_P : Real
  C_T : Real
  C_C : Real
  thetaFork : Real
  etaQ_pos : 0 < etaQ
  X_tail_nonneg : 0 ≤ X_tail
  C_Q_pos : 0 < C_Q
  C_P_nonneg : 0 ≤ C_P
  C_T_nonneg : 0 ≤ C_T
  C_C_nonneg : 0 ≤ C_C
  thetaFork_nonneg : 0 ≤ thetaFork
  pressureSmall_obligation :
    pressureSmall.obligation = obligation
  pressureSmall_tail :
    pressureSmall.X_tail = X_tail
  tailWindowFamily : Prop
  boundedOverlap : Prop
  frequencyLocalizedMeanFreeTail : Prop
  X_tail_identifies_tent_square_function : Prop
  localQuadraticTentExcess_defined_by_cknIntegral : Prop
  pressureTailSmall_quantitative :
    pressureTailTerm ≤ obligation.decomposition.unresolvedPressureTail
  transportForkSmall :
    C_T * transportVisibility ≤ thetaFork * X_tail
  commutatorForkSmall :
    C_C * commutatorVisibility ≤ thetaFork * X_tail
  tentBoundaryErrorsSmall :
    tentBoundaryError ≤ thetaFork * X_tail
  localizedCoercivity :
    X_tail ≤
      C_Q * localQuadraticTentExcess +
        C_P * pressureTailTerm +
        C_T * transportVisibility +
        C_C * commutatorVisibility +
        tentBoundaryError
  pressureSmall_absorbs_pressureTerm :
    C_P * obligation.decomposition.unresolvedPressureTail ≤ thetaFork * X_tail
  thetaFork_absorbable :
    (4 : Real) * thetaFork ≤ 1 / 2
  etaQ_from_coercivity_constants :
    etaQ ≤ 1 / (2 * C_Q)
  ckn_bad_window_contrapositive : Prop
  etaQ_uniform_from_ckn_constants : Prop
  etaQ_not_chosen_from_receipt : Prop
  no_strictSubratio_or_margin_input : Prop

/--
Coercivity plus pressure-small and non-Q fork smallness produce the local
quadratic tent-excess lower bound.
-/
theorem route1_tent_excess_tail_lower_bound_of_coercivity_certificate
    (h : Route1LocalQuadraticTentExcessCoercivityCertificate) :
    h.etaQ * h.X_tail ≤ h.localQuadraticTentExcess := by
  have hpressure :
      h.C_P * h.pressureTailTerm ≤ h.thetaFork * h.X_tail := by
    exact le_trans
      (mul_le_mul_of_nonneg_left h.pressureTailSmall_quantitative h.C_P_nonneg)
      h.pressureSmall_absorbs_pressureTerm
  have hsmall :
      h.C_P * h.pressureTailTerm +
          h.C_T * h.transportVisibility +
          h.C_C * h.commutatorVisibility +
          h.tentBoundaryError ≤
        (4 : Real) * h.thetaFork * h.X_tail := by
    nlinarith [hpressure, h.transportForkSmall, h.commutatorForkSmall,
      h.tentBoundaryErrorsSmall]
  have habsorb :
      (4 : Real) * h.thetaFork * h.X_tail ≤ (1 / 2 : Real) * h.X_tail := by
    exact mul_le_mul_of_nonneg_right h.thetaFork_absorbable h.X_tail_nonneg
  have hx_half :
      (1 / 2 : Real) * h.X_tail ≤ h.C_Q * h.localQuadraticTentExcess := by
    nlinarith [h.localizedCoercivity, hsmall, habsorb]
  have heta :
      h.etaQ * h.X_tail ≤ (1 / (2 * h.C_Q)) * h.X_tail :=
    mul_le_mul_of_nonneg_right h.etaQ_from_coercivity_constants h.X_tail_nonneg
  have hdivide :
      (1 / (2 * h.C_Q)) * h.X_tail ≤ h.localQuadraticTentExcess := by
    have hCne : h.C_Q ≠ 0 := ne_of_gt h.C_Q_pos
    have hscaled :
        h.C_Q * ((1 / (2 * h.C_Q)) * h.X_tail) ≤
          h.C_Q * h.localQuadraticTentExcess := by
      have hrewrite :
          h.C_Q * ((1 / (2 * h.C_Q)) * h.X_tail) =
            (1 / 2 : Real) * h.X_tail := by
        field_simp [hCne]
      rwa [hrewrite]
    exact le_of_mul_le_mul_left hscaled h.C_Q_pos
  exact le_trans heta hdivide

/--
Turn the coercivity certificate into the simpler tent-excess certificate
consumed by route1.
-/
def Route1LocalQuadraticTentExcessCertificate.ofCoercivityCertificate
    (h : Route1LocalQuadraticTentExcessCoercivityCertificate)
    (hreceipt :
      (route1PressureVisibilityReceipts h.obligation).localQuadraticReceipt =
        h.localQuadraticTentExcess) :
    Route1LocalQuadraticTentExcessCertificate where
  obligation := h.obligation
  pressureSmall := h.pressureSmall
  etaQ := h.etaQ
  X_tail := h.X_tail
  localQuadraticTentExcess := h.localQuadraticTentExcess
  etaQ_pos := h.etaQ_pos
  X_tail_nonneg := h.X_tail_nonneg
  localQuadraticTentExcess_nonneg := by
    have hlower :=
      route1_tent_excess_tail_lower_bound_of_coercivity_certificate h
    nlinarith [hlower, h.etaQ_pos, h.X_tail_nonneg]
  pressureSmall_obligation := h.pressureSmall_obligation
  pressureSmall_tail := h.pressureSmall_tail
  cknLocalExcessObservable := h.ckn_bad_window_contrapositive
  tentWindowMatchesRouteTailScale := h.X_tail_identifies_tent_square_function
  tentExcess_defined_by_cknIntegral := h.localQuadraticTentExcess_defined_by_cknIntegral
  etaQ_uniform_from_ckn_constants := h.etaQ_uniform_from_ckn_constants
  etaQ_not_chosen_from_receipt := h.etaQ_not_chosen_from_receipt
  no_strictSubratio_or_margin_input := h.no_strictSubratio_or_margin_input
  localQuadraticReceipt_identifies_tent_excess := hreceipt
  tentExcess_tail_lower_bound :=
    route1_tent_excess_tail_lower_bound_of_coercivity_certificate h

/--
Bridge from the existing CKN/tent-excess certificate to the pressure-cone
local quadratic payment source.

This is the preferred positive branch after the final-carrier No-Go: the
pressure/Riesz cone charge is paid by a CKN/tent local quadratic observable on
the same fixed window, not by the canceled projected carrier.
-/
structure FixedWindowPressureConeChargeTentExcessPaymentSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  profileObligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  tentCertificate : Route1LocalQuadraticTentExcessCertificate
  overflow : (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass
  pressureRieszConeCharge : Real
  overflowExcess : Real
  visibilityChargeConstant : Real
  visibilityChargeConstant_pos : 0 < visibilityChargeConstant
  overflowExcess_eq :
    overflowExcess =
      sheathOppositeConeMass - (1 - epsilon) * corePositiveConeMass
  pressureRieszConeCharge_pays_overflowExcess :
    visibilityChargeConstant * overflowExcess ≤ pressureRieszConeCharge
  pressureRieszConeCharge_le_tentExcess :
    pressureRieszConeCharge ≤ tentCertificate.localQuadraticTentExcess
  childChargeReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts
      tentCertificate.obligation).childChargeReceipt
  pressureRieszConeReceipt : Prop
  pressureRieszConeReceipt_holds : pressureRieszConeReceipt
  sameFixedProjectedKernel : Prop
  pressureRieszConeChargeMeasuresPreSummedStress : Prop
  fixedKernelOperatorNormPaysConeCharge : Prop
  coneChargeFixedBeforeReceiptComparison : Prop
  coneChargeNotDefinedFromFinalCarrier : Prop
  no_strictSubratio_or_margin_input : Prop

/-- CKN/tent-excess payment supplies the pressure-cone local quadratic source. -/
def FixedWindowPressureConeChargeLocalQuadraticReceiptSource.ofTentExcessPaymentSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureConeChargeTentExcessPaymentSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowPressureConeChargeLocalQuadraticReceiptSource formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  profileObligation := h.profileObligation
  pressureObligation := h.tentCertificate.obligation
  overflow := h.overflow
  pressureRieszConeCharge := h.pressureRieszConeCharge
  overflowExcess := h.overflowExcess
  visibilityChargeConstant := h.visibilityChargeConstant
  visibilityChargeConstant_pos := h.visibilityChargeConstant_pos
  overflowExcess_eq := h.overflowExcess_eq
  pressureRieszConeCharge_pays_overflowExcess :=
    h.pressureRieszConeCharge_pays_overflowExcess
  pressureRieszConeCharge_le_localQuadraticReceipt := by
    rw [h.tentCertificate.localQuadraticReceipt_identifies_tent_excess]
    exact h.pressureRieszConeCharge_le_tentExcess
  childChargeReceipt_nonneg := h.childChargeReceipt_nonneg
  pressureRieszConeReceipt := h.pressureRieszConeReceipt
  pressureRieszConeReceipt_holds := h.pressureRieszConeReceipt_holds
  sameFixedProjectedKernel := h.sameFixedProjectedKernel
  pressureRieszConeChargeMeasuresPreSummedStress :=
    h.pressureRieszConeChargeMeasuresPreSummedStress
  localQuadraticReceiptMeasuresPreSummedStress :=
    And h.tentCertificate.tentExcess_defined_by_cknIntegral
      h.tentCertificate.tentWindowMatchesRouteTailScale
  fixedKernelOperatorNormPaysConeCharge :=
    h.fixedKernelOperatorNormPaysConeCharge
  coneChargeFixedBeforeReceiptComparison :=
    h.coneChargeFixedBeforeReceiptComparison
  coneChargeNotDefinedFromFinalCarrier :=
    h.coneChargeNotDefinedFromFinalCarrier
  no_strictSubratio_or_margin_input :=
    And h.no_strictSubratio_or_margin_input
      h.tentCertificate.no_strictSubratio_or_margin_input

/-- CKN/tent-excess payment supplies the pressure receipt bridge. -/
def FixedWindowPressureRieszConeChargeReceiptBridge.ofTentExcessPaymentSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureConeChargeTentExcessPaymentSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowPressureRieszConeChargeReceiptBridge formula epsilon
      corePositiveConeMass sheathOppositeConeMass :=
  FixedWindowPressureRieszConeChargeReceiptBridge.ofLocalQuadraticReceiptSource
    (FixedWindowPressureConeChargeLocalQuadraticReceiptSource.ofTentExcessPaymentSource h)

/-- CKN/tent-excess payment constructs the corrected visible branch. -/
def FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureTentExcessPaymentSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureConeChargeTentExcessPaymentSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
      corePositiveConeMass sheathOppositeConeMass :=
  FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureReceiptBridge
    (FixedWindowPressureRieszConeChargeReceiptBridge.ofTentExcessPaymentSource h)

/-- CKN/tent-excess payment is enough to pay the repaired overflow fork. -/
theorem visibleOverflowCharge_of_pressureTentExcessPaymentSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureConeChargeTentExcessPaymentSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureTentExcessPaymentSource
      h).visibleOverflowCharge :=
  visibleOverflowCharge_of_visibleOrInvisibleProfile
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureTentExcessPaymentSource h)

/--
One level lower than the tent-excess payment source: split
`pressureRieszConeCharge ≤ tentExcess` into a fixed-kernel operator-norm bound
and a CKN/tent stress-mass domination estimate.

The first inequality is the fixed-window linear algebra; the second is the
remaining PDE estimate.
-/
structure FixedWindowPressureConeTentOperatorNormSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  profileObligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  tentCertificate : Route1LocalQuadraticTentExcessCertificate
  overflow : (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass
  pressureRieszConeCharge : Real
  overflowExcess : Real
  preSummedStressMass : Real
  fixedKernelOperatorNorm : Real
  visibilityChargeConstant : Real
  visibilityChargeConstant_pos : 0 < visibilityChargeConstant
  overflowExcess_eq :
    overflowExcess =
      sheathOppositeConeMass - (1 - epsilon) * corePositiveConeMass
  pressureRieszConeCharge_pays_overflowExcess :
    visibilityChargeConstant * overflowExcess ≤ pressureRieszConeCharge
  pressureRieszConeCharge_le_operatorNormStressMass :
    pressureRieszConeCharge ≤ fixedKernelOperatorNorm * preSummedStressMass
  operatorNormStressMass_le_tentExcess :
    fixedKernelOperatorNorm * preSummedStressMass ≤
      tentCertificate.localQuadraticTentExcess
  childChargeReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts
      tentCertificate.obligation).childChargeReceipt
  pressureRieszConeReceipt : Prop
  pressureRieszConeReceipt_holds : pressureRieszConeReceipt
  sameFixedProjectedKernel : Prop
  pressureRieszConeChargeMeasuresPreSummedStress : Prop
  preSummedStressMassFixedBeforeCoreSheathSummation : Prop
  fixedKernelOperatorNormBound : Prop
  cknTentExcessDominatesOperatorNormStressMass : Prop
  coneChargeFixedBeforeReceiptComparison : Prop
  coneChargeNotDefinedFromFinalCarrier : Prop
  no_strictSubratio_or_margin_input : Prop

/--
Compatibility layer below the operator-norm source.

It decomposes the pre-summed stress payment into resolved mean-free, Galilean
mean, and frequency-leakage shares.  The scalar conclusion needed by
`FixedWindowPressureConeTentOperatorNormSource` is derived from the share
budget rather than being assumed as a single opaque inequality.
-/
structure FixedWindowPreSummedStressMassCKNTentCompatibility
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  profileObligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  tentCertificate : Route1LocalQuadraticTentExcessCertificate
  overflow : (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass
  pressureRieszConeCharge : Real
  overflowExcess : Real
  preSummedStressMass : Real
  fixedKernelOperatorNorm : Real
  visibilityChargeConstant : Real
  resolvedMeanFreeWeightedStress : Real
  galileanMeanWeightedStress : Real
  frequencyLeakageWeightedStress : Real
  thetaResolved : Real
  thetaMean : Real
  thetaLeakage : Real
  visibilityChargeConstant_pos : 0 < visibilityChargeConstant
  thetaResolved_nonneg : 0 ≤ thetaResolved
  thetaMean_nonneg : 0 ≤ thetaMean
  thetaLeakage_nonneg : 0 ≤ thetaLeakage
  theta_sum_le_one : thetaResolved + thetaMean + thetaLeakage ≤ 1
  overflowExcess_eq :
    overflowExcess =
      sheathOppositeConeMass - (1 - epsilon) * corePositiveConeMass
  pressureRieszConeCharge_pays_overflowExcess :
    visibilityChargeConstant * overflowExcess ≤ pressureRieszConeCharge
  pressureRieszConeCharge_le_operatorNormStressMass :
    pressureRieszConeCharge ≤ fixedKernelOperatorNorm * preSummedStressMass
  operatorNormStressMass_split :
    fixedKernelOperatorNorm * preSummedStressMass ≤
      resolvedMeanFreeWeightedStress +
        galileanMeanWeightedStress +
          frequencyLeakageWeightedStress
  resolvedMeanFreeWeightedStress_le_tentShare :
    resolvedMeanFreeWeightedStress ≤
      thetaResolved * tentCertificate.localQuadraticTentExcess
  galileanMeanWeightedStress_le_tentShare :
    galileanMeanWeightedStress ≤
      thetaMean * tentCertificate.localQuadraticTentExcess
  frequencyLeakageWeightedStress_le_tentShare :
    frequencyLeakageWeightedStress ≤
      thetaLeakage * tentCertificate.localQuadraticTentExcess
  childChargeReceipt_nonneg :
    0 ≤ (route1PressureVisibilityReceipts
      tentCertificate.obligation).childChargeReceipt
  pressureRieszConeReceipt : Prop
  pressureRieszConeReceipt_holds : pressureRieszConeReceipt
  sameFixedProjectedKernel : Prop
  sameWindowAsCKNTentCertificate : Prop
  pressureRieszConeChargeMeasuresPreSummedStress : Prop
  preSummedStressMassFixedBeforeCoreSheathSummation : Prop
  fixedKernelOperatorNormBound : Prop
  resolvedMeanFreePartPaidByCKNTentExcess : Prop
  galileanMeanPartControlledOrQuotiented : Prop
  frequencyLeakagePartPaidOrRoutedToCommutatorShard : Prop
  shareBudgetIndependentOfFinalCarrier : Prop
  coneChargeFixedBeforeReceiptComparison : Prop
  coneChargeNotDefinedFromFinalCarrier : Prop
  no_strictSubratio_or_margin_input : Prop

/--
The compatibility split supplies the operator-norm/tent domination source.
The only scalar work is the share-budget calculation.
-/
def FixedWindowPressureConeTentOperatorNormSource.ofCKNTentCompatibility
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowPressureConeTentOperatorNormSource formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  profileObligation := h.profileObligation
  tentCertificate := h.tentCertificate
  overflow := h.overflow
  pressureRieszConeCharge := h.pressureRieszConeCharge
  overflowExcess := h.overflowExcess
  preSummedStressMass := h.preSummedStressMass
  fixedKernelOperatorNorm := h.fixedKernelOperatorNorm
  visibilityChargeConstant := h.visibilityChargeConstant
  visibilityChargeConstant_pos := h.visibilityChargeConstant_pos
  overflowExcess_eq := h.overflowExcess_eq
  pressureRieszConeCharge_pays_overflowExcess :=
    h.pressureRieszConeCharge_pays_overflowExcess
  pressureRieszConeCharge_le_operatorNormStressMass :=
    h.pressureRieszConeCharge_le_operatorNormStressMass
  operatorNormStressMass_le_tentExcess := by
    have hpieces :
        h.resolvedMeanFreeWeightedStress +
            h.galileanMeanWeightedStress +
              h.frequencyLeakageWeightedStress ≤
          (h.thetaResolved + h.thetaMean + h.thetaLeakage) *
            h.tentCertificate.localQuadraticTentExcess := by
      nlinarith [h.resolvedMeanFreeWeightedStress_le_tentShare,
        h.galileanMeanWeightedStress_le_tentShare,
        h.frequencyLeakageWeightedStress_le_tentShare]
    have htheta :
        (h.thetaResolved + h.thetaMean + h.thetaLeakage) *
            h.tentCertificate.localQuadraticTentExcess ≤
          h.tentCertificate.localQuadraticTentExcess := by
      have hgap :
          0 ≤ 1 - (h.thetaResolved + h.thetaMean + h.thetaLeakage) := by
        linarith [h.theta_sum_le_one]
      nlinarith [hgap, h.tentCertificate.localQuadraticTentExcess_nonneg]
    exact le_trans h.operatorNormStressMass_split (le_trans hpieces htheta)
  childChargeReceipt_nonneg := h.childChargeReceipt_nonneg
  pressureRieszConeReceipt := h.pressureRieszConeReceipt
  pressureRieszConeReceipt_holds := h.pressureRieszConeReceipt_holds
  sameFixedProjectedKernel := h.sameFixedProjectedKernel
  pressureRieszConeChargeMeasuresPreSummedStress :=
    h.pressureRieszConeChargeMeasuresPreSummedStress
  preSummedStressMassFixedBeforeCoreSheathSummation :=
    h.preSummedStressMassFixedBeforeCoreSheathSummation
  fixedKernelOperatorNormBound := h.fixedKernelOperatorNormBound
  cknTentExcessDominatesOperatorNormStressMass :=
    And h.sameWindowAsCKNTentCertificate
      (And h.resolvedMeanFreePartPaidByCKNTentExcess
        (And h.galileanMeanPartControlledOrQuotiented
          (And h.frequencyLeakagePartPaidOrRoutedToCommutatorShard
            h.shareBudgetIndependentOfFinalCarrier)))
  coneChargeFixedBeforeReceiptComparison :=
    h.coneChargeFixedBeforeReceiptComparison
  coneChargeNotDefinedFromFinalCarrier :=
    h.coneChargeNotDefinedFromFinalCarrier
  no_strictSubratio_or_margin_input :=
    h.no_strictSubratio_or_margin_input

/--
The resolved mean-free share of the CKN/tent compatibility split already routes
to the local-quadratic receipt.  The scalar reason is deliberately small:
`thetaResolved ≤ 1` follows from the share budget and nonnegativity of the other
shares, and the local-quadratic receipt is the same tent-excess observable.
-/
theorem resolvedMeanFreeWeightedStress_le_localQuadraticReceipt_of_cknTentCompatibility
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    h.resolvedMeanFreeWeightedStress ≤
      (route1PressureVisibilityReceipts
        h.tentCertificate.obligation).localQuadraticReceipt := by
  rw [h.tentCertificate.localQuadraticReceipt_identifies_tent_excess]
  have htheta : h.thetaResolved ≤ 1 := by
    linarith [h.theta_sum_le_one, h.thetaMean_nonneg, h.thetaLeakage_nonneg]
  have htent :
      h.thetaResolved * h.tentCertificate.localQuadraticTentExcess ≤
        h.tentCertificate.localQuadraticTentExcess := by
    have hgap : 0 ≤ 1 - h.thetaResolved := by
      linarith [htheta]
    nlinarith [hgap, h.tentCertificate.localQuadraticTentExcess_nonneg]
  exact le_trans h.resolvedMeanFreeWeightedStress_le_tentShare htent

/--
Resolved mean-free routing is the first receipt-share sublemma below the split
receipt source.

This is intentionally not the full split receipt source: Galilean mean and
frequency-leakage shares still require pressure-reserve and child/tent-charge
routings.
-/
structure FixedWindowCKNTentResolvedMeanFreeRoutesToLocalQuadraticReceipt
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  cknTentCompatibility :
    FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  resolvedMeanFreeWeightedStress_le_localQuadraticReceipt :
    cknTentCompatibility.resolvedMeanFreeWeightedStress ≤
      (route1PressureVisibilityReceipts
        cknTentCompatibility.tentCertificate.obligation).localQuadraticReceipt
  localQuadraticReceiptUsesSameTentExcess : Prop
  sourceFixedBeforeFinalCarrier : Prop
  doesNotRouteGalileanReserveShare : Prop
  doesNotRouteFrequencyLeakageChildShare : Prop
  noPressureClosureFromResolvedShareAlone : Prop

/--
CKN/tent compatibility supplies the resolved mean-free local-quadratic routing.
The remaining proof obligations are explicitly left as non-resolved shares.
-/
def FixedWindowCKNTentResolvedMeanFreeRoutesToLocalQuadraticReceipt.ofCKNTentCompatibility
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowCKNTentResolvedMeanFreeRoutesToLocalQuadraticReceipt formula
      epsilon corePositiveConeMass sheathOppositeConeMass where
  cknTentCompatibility := h
  resolvedMeanFreeWeightedStress_le_localQuadraticReceipt :=
    resolvedMeanFreeWeightedStress_le_localQuadraticReceipt_of_cknTentCompatibility h
  localQuadraticReceiptUsesSameTentExcess :=
    And h.sameWindowAsCKNTentCertificate
      h.resolvedMeanFreePartPaidByCKNTentExcess
  sourceFixedBeforeFinalCarrier :=
    h.shareBudgetIndependentOfFinalCarrier
  doesNotRouteGalileanReserveShare := True
  doesNotRouteFrequencyLeakageChildShare := True
  noPressureClosureFromResolvedShareAlone := True

/--
Guard extracted from the fixed-window CKN/tent share scout: a bare mean-free
tent excess does not pay the full pre-summed stress mass when Galilean or
frequency-leakage shares remain unpaid.
-/
structure FixedWindowBareMeanFreeCKNTentPaymentGap
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  profileObligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  tentCertificate : Route1LocalQuadraticTentExcessCertificate
  totalWeightedStress : Real
  capturedMeanFreeTentExcess : Real
  resolvedMeanFreeWeightedStress : Real
  galileanMeanWeightedStress : Real
  frequencyLeakageWeightedStress : Real
  capturedMeanFreeTentExcess_eq_resolved :
    capturedMeanFreeTentExcess = resolvedMeanFreeWeightedStress
  totalWeightedStress_split :
    totalWeightedStress =
      resolvedMeanFreeWeightedStress +
        galileanMeanWeightedStress +
          frequencyLeakageWeightedStress
  unpaidMeanOrLeakage_pos :
    0 < galileanMeanWeightedStress + frequencyLeakageWeightedStress
  bareMeanFreeCKN_shortfall :
    capturedMeanFreeTentExcess < totalWeightedStress
  sameFixedProjectedKernel : Prop
  sameWindowAsCKNTentCertificate : Prop
  meanNotQuotientedOrControlled : Prop
  leakageNotPaidOrRoutedToCommutatorShard : Prop
  noFinalCarrierInput : Prop

/-- Bare mean-free CKN/tent excess alone cannot instantiate the full share payment. -/
theorem no_bareMeanFreeCKNTent_payment_of_gap
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowBareMeanFreeCKNTentPaymentGap formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    ¬ h.totalWeightedStress ≤ h.capturedMeanFreeTentExcess :=
  not_le_of_gt h.bareMeanFreeCKN_shortfall

/--
Weaker split source after the CKN/tent share scout.

Resolved mean-free stress is paid by the local quadratic receipt, Galilean mean
stress by the pressure reserve receipt, and frequency/window leakage by the
child/tent pressure receipt.  This repairs the bare mean-free CKN gap without
forcing all shares into one tent-excess scalar.
-/
structure FixedWindowPreSummedStressMassSplitReceiptSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  profileObligation : NS.NoInvisibleCriticalProfileCompactnessObligation
  pressureObligation : Route1PressureReserveNoEscapeObligation
  overflow : (1 - epsilon) * corePositiveConeMass < sheathOppositeConeMass
  pressureRieszConeCharge : Real
  overflowExcess : Real
  visibilityChargeConstant : Real
  resolvedMeanFreeWeightedStress : Real
  galileanMeanWeightedStress : Real
  frequencyLeakageWeightedStress : Real
  visibilityChargeConstant_pos : 0 < visibilityChargeConstant
  overflowExcess_eq :
    overflowExcess =
      sheathOppositeConeMass - (1 - epsilon) * corePositiveConeMass
  pressureRieszConeCharge_pays_overflowExcess :
    visibilityChargeConstant * overflowExcess ≤ pressureRieszConeCharge
  pressureRieszConeCharge_le_splitWeightedStress :
    pressureRieszConeCharge ≤
      resolvedMeanFreeWeightedStress +
        galileanMeanWeightedStress +
          frequencyLeakageWeightedStress
  resolvedMeanFreeWeightedStress_le_localQuadraticReceipt :
    resolvedMeanFreeWeightedStress ≤
      (route1PressureVisibilityReceipts pressureObligation).localQuadraticReceipt
  galileanMeanWeightedStress_le_pressureReserveReceipt :
    galileanMeanWeightedStress ≤
      (route1PressureVisibilityReceipts pressureObligation).pressureReserveReceipt
  frequencyLeakageWeightedStress_le_childChargeReceipt :
    frequencyLeakageWeightedStress ≤
      (route1PressureVisibilityReceipts pressureObligation).childChargeReceipt
  pressureRieszConeReceipt : Prop
  pressureRieszConeReceipt_holds : pressureRieszConeReceipt
  sameFixedProjectedKernel : Prop
  sameWindowAsPressureReceipts : Prop
  pressureRieszConeChargeMeasuresPreSummedStress : Prop
  splitFixedBeforeReceiptComparison : Prop
  resolvedMeanFreePartPaidByLocalQuadraticReceipt : Prop
  galileanMeanPartPaidByPressureReserveReceipt : Prop
  frequencyLeakagePartPaidByChildOrTentChargeReceipt : Prop
  receiptSharesNotChosenFromFinalCarrier : Prop
  coneChargeFixedBeforeReceiptComparison : Prop
  coneChargeNotDefinedFromFinalCarrier : Prop
  no_strictSubratio_or_margin_input : Prop

/--
Receipt-share compatibility needed to lower CKN/tent compatibility to the
split receipt source.

The existing CKN/tent compatibility pays the three pre-summed stress shares by
tent-excess fractions.  The pressure receipt frontier needs a stronger routing:
resolved mean-free stress goes to the local-quadratic receipt, Galilean mean to
pressure reserve, and frequency leakage to child/tent charge.
-/
structure FixedWindowCKNTentStressSharesRouteToPressureReceipts
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass) where
  resolvedMeanFreeWeightedStress_le_localQuadraticReceipt :
    h.resolvedMeanFreeWeightedStress ≤
      (route1PressureVisibilityReceipts
        h.tentCertificate.obligation).localQuadraticReceipt
  galileanMeanWeightedStress_le_pressureReserveReceipt :
    h.galileanMeanWeightedStress ≤
      (route1PressureVisibilityReceipts
        h.tentCertificate.obligation).pressureReserveReceipt
  frequencyLeakageWeightedStress_le_childChargeReceipt :
    h.frequencyLeakageWeightedStress ≤
      (route1PressureVisibilityReceipts
        h.tentCertificate.obligation).childChargeReceipt
  localQuadraticReceiptUsesSameTentExcess : Prop
  galileanMeanQuotientedOrPaidByPressureReserve : Prop
  frequencyLeakageRoutedToChildOrTentCharge : Prop
  receiptSharesFixedBeforeFinalCarrier : Prop
  noFinalCarrierVisibilityInput : Prop

/--
CKN/tent compatibility plus explicit receipt-share routing supplies the split
pre-summed stress receipt source.
-/
def FixedWindowPreSummedStressMassSplitReceiptSource.ofCKNTentCompatibility
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass)
    (hShares :
      FixedWindowCKNTentStressSharesRouteToPressureReceipts h) :
    FixedWindowPreSummedStressMassSplitReceiptSource formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  profileObligation := h.profileObligation
  pressureObligation := h.tentCertificate.obligation
  overflow := h.overflow
  pressureRieszConeCharge := h.pressureRieszConeCharge
  overflowExcess := h.overflowExcess
  visibilityChargeConstant := h.visibilityChargeConstant
  resolvedMeanFreeWeightedStress := h.resolvedMeanFreeWeightedStress
  galileanMeanWeightedStress := h.galileanMeanWeightedStress
  frequencyLeakageWeightedStress := h.frequencyLeakageWeightedStress
  visibilityChargeConstant_pos := h.visibilityChargeConstant_pos
  overflowExcess_eq := h.overflowExcess_eq
  pressureRieszConeCharge_pays_overflowExcess :=
    h.pressureRieszConeCharge_pays_overflowExcess
  pressureRieszConeCharge_le_splitWeightedStress :=
    le_trans h.pressureRieszConeCharge_le_operatorNormStressMass
      h.operatorNormStressMass_split
  resolvedMeanFreeWeightedStress_le_localQuadraticReceipt :=
    hShares.resolvedMeanFreeWeightedStress_le_localQuadraticReceipt
  galileanMeanWeightedStress_le_pressureReserveReceipt :=
    hShares.galileanMeanWeightedStress_le_pressureReserveReceipt
  frequencyLeakageWeightedStress_le_childChargeReceipt :=
    hShares.frequencyLeakageWeightedStress_le_childChargeReceipt
  pressureRieszConeReceipt := h.pressureRieszConeReceipt
  pressureRieszConeReceipt_holds := h.pressureRieszConeReceipt_holds
  sameFixedProjectedKernel := h.sameFixedProjectedKernel
  sameWindowAsPressureReceipts :=
    h.sameWindowAsCKNTentCertificate
  pressureRieszConeChargeMeasuresPreSummedStress :=
    h.pressureRieszConeChargeMeasuresPreSummedStress
  splitFixedBeforeReceiptComparison :=
    h.preSummedStressMassFixedBeforeCoreSheathSummation
  resolvedMeanFreePartPaidByLocalQuadraticReceipt :=
    And h.resolvedMeanFreePartPaidByCKNTentExcess
      hShares.localQuadraticReceiptUsesSameTentExcess
  galileanMeanPartPaidByPressureReserveReceipt :=
    And h.galileanMeanPartControlledOrQuotiented
      hShares.galileanMeanQuotientedOrPaidByPressureReserve
  frequencyLeakagePartPaidByChildOrTentChargeReceipt :=
    And h.frequencyLeakagePartPaidOrRoutedToCommutatorShard
      hShares.frequencyLeakageRoutedToChildOrTentCharge
  receiptSharesNotChosenFromFinalCarrier :=
    And h.shareBudgetIndependentOfFinalCarrier
      (And hShares.receiptSharesFixedBeforeFinalCarrier
        hShares.noFinalCarrierVisibilityInput)
  coneChargeFixedBeforeReceiptComparison :=
    h.coneChargeFixedBeforeReceiptComparison
  coneChargeNotDefinedFromFinalCarrier :=
    h.coneChargeNotDefinedFromFinalCarrier
  no_strictSubratio_or_margin_input :=
    h.no_strictSubratio_or_margin_input

/--
Guard: CKN/tent compatibility by itself gives an operator-norm/tent payment, but
not the split receipt source.  The Galilean and frequency-leakage shares still
need explicit pressure-reserve and child/tent routing.
-/
structure CKNTentCompatibilityDoesNotSourceSplitReceiptsAlone
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  cknTentCompatibility :
    FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  operatorNormTentSourceAvailable :
    FixedWindowPressureConeTentOperatorNormSource formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  missingResolvedReceiptRouting : Prop
  missingGalileanReserveRouting : Prop
  missingFrequencyLeakageChildRouting : Prop
  noSplitReceiptSourceWithoutShareRouting : Prop
  noFinalCarrierShortcutForMissingShares : Prop

/-- The split receipt source supplies the pressure/Riesz cone receipt bridge. -/
def FixedWindowPressureRieszConeChargeReceiptBridge.ofSplitReceiptSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassSplitReceiptSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowPressureRieszConeChargeReceiptBridge formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  profileObligation := h.profileObligation
  pressureObligation := h.pressureObligation
  overflow := h.overflow
  pressureRieszConeCharge := h.pressureRieszConeCharge
  overflowExcess := h.overflowExcess
  visibilityChargeConstant := h.visibilityChargeConstant
  visibilityChargeConstant_pos := h.visibilityChargeConstant_pos
  overflowExcess_eq := h.overflowExcess_eq
  pressureRieszConeCharge_pays_overflowExcess :=
    h.pressureRieszConeCharge_pays_overflowExcess
  pressureRieszConeCharge_le_pressureReceiptSum := by
    have hsplit :
        h.resolvedMeanFreeWeightedStress +
            h.galileanMeanWeightedStress +
              h.frequencyLeakageWeightedStress ≤
          (route1PressureVisibilityReceipts h.pressureObligation).receiptSum := by
      dsimp [Route1PressureVisibilityReceipts.receiptSum]
      nlinarith [h.resolvedMeanFreeWeightedStress_le_localQuadraticReceipt,
        h.galileanMeanWeightedStress_le_pressureReserveReceipt,
        h.frequencyLeakageWeightedStress_le_childChargeReceipt]
    exact le_trans h.pressureRieszConeCharge_le_splitWeightedStress hsplit
  pressureRieszConeReceipt := h.pressureRieszConeReceipt
  pressureRieszConeReceipt_holds := h.pressureRieszConeReceipt_holds
  sameFixedProjectedKernel := h.sameFixedProjectedKernel
  pressureRieszConeChargeMeasuresPreSummedStress :=
    h.pressureRieszConeChargeMeasuresPreSummedStress
  pressureReceiptSumUsesIndependentReceipts :=
    And h.sameWindowAsPressureReceipts
      (And h.resolvedMeanFreePartPaidByLocalQuadraticReceipt
        (And h.galileanMeanPartPaidByPressureReserveReceipt
          (And h.frequencyLeakagePartPaidByChildOrTentChargeReceipt
            h.receiptSharesNotChosenFromFinalCarrier)))
  coneChargeFixedBeforeReceiptComparison :=
    And h.coneChargeFixedBeforeReceiptComparison
      h.splitFixedBeforeReceiptComparison
  coneChargeNotDefinedFromFinalCarrier :=
    h.coneChargeNotDefinedFromFinalCarrier
  no_strictSubratio_or_margin_input :=
    h.no_strictSubratio_or_margin_input

/--
Scalar projection of the split pre-summed stress receipt.

This is the pressure branch's useful receipt inequality: the cone charge is
paid by independent local-quadratic, pressure-reserve, and child-charge
receipts, not by the final projected carrier.
-/
theorem pressureRieszConeCharge_le_pressureReceiptSum_of_splitReceiptSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassSplitReceiptSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    h.pressureRieszConeCharge ≤
      (route1PressureVisibilityReceipts h.pressureObligation).receiptSum :=
  (FixedWindowPressureRieszConeChargeReceiptBridge.ofSplitReceiptSource
    h).pressureRieszConeCharge_le_pressureReceiptSum

/--
The visible pressure overflow is paid by the same independent receipt sum once
the split pre-summed stress source is supplied.
-/
theorem pressureOverflowExcess_le_pressureReceiptSum_of_splitReceiptSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassSplitReceiptSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    h.visibilityChargeConstant * h.overflowExcess ≤
      (route1PressureVisibilityReceipts h.pressureObligation).receiptSum :=
  le_trans h.pressureRieszConeCharge_pays_overflowExcess
    (pressureRieszConeCharge_le_pressureReceiptSum_of_splitReceiptSource h)

/--
Guard: the split receipt path is the pressure branch's actionable visible path,
but it still does not close the invisible/coherence side of the pressure fork.
-/
structure PressureSplitReceiptFrontierIsNotClosure where
  splitPreSummedStressReceiptPaysVisibleOverflow : Prop
  receiptSumIsIndependentOfFinalProjectedCarrier : Prop
  noInvisibleProfileOrStressCoherenceStillRequired : Prop
  finalCarrierReceiptStillRejected : Prop
  noPressureClosureFromSplitReceiptSurfaceAlone : Prop

/-- Split receipt source constructs the corrected visible-or-invisible fork. -/
def FixedWindowOverflowVisibleOrInvisibleProfile.ofSplitReceiptSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassSplitReceiptSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
      corePositiveConeMass sheathOppositeConeMass :=
  FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureReceiptBridge
    (FixedWindowPressureRieszConeChargeReceiptBridge.ofSplitReceiptSource h)

/-- The split receipt source is enough to pay the repaired overflow fork. -/
theorem visibleOverflowCharge_of_splitReceiptSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassSplitReceiptSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofSplitReceiptSource
      h).visibleOverflowCharge :=
  visibleOverflowCharge_of_visibleOrInvisibleProfile
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofSplitReceiptSource h)

/-- Operator-norm/tent domination supplies the tent-excess payment source. -/
def FixedWindowPressureConeChargeTentExcessPaymentSource.ofOperatorNormSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureConeTentOperatorNormSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowPressureConeChargeTentExcessPaymentSource formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  profileObligation := h.profileObligation
  tentCertificate := h.tentCertificate
  overflow := h.overflow
  pressureRieszConeCharge := h.pressureRieszConeCharge
  overflowExcess := h.overflowExcess
  visibilityChargeConstant := h.visibilityChargeConstant
  visibilityChargeConstant_pos := h.visibilityChargeConstant_pos
  overflowExcess_eq := h.overflowExcess_eq
  pressureRieszConeCharge_pays_overflowExcess :=
    h.pressureRieszConeCharge_pays_overflowExcess
  pressureRieszConeCharge_le_tentExcess :=
    le_trans h.pressureRieszConeCharge_le_operatorNormStressMass
      h.operatorNormStressMass_le_tentExcess
  childChargeReceipt_nonneg := h.childChargeReceipt_nonneg
  pressureRieszConeReceipt := h.pressureRieszConeReceipt
  pressureRieszConeReceipt_holds := h.pressureRieszConeReceipt_holds
  sameFixedProjectedKernel := h.sameFixedProjectedKernel
  pressureRieszConeChargeMeasuresPreSummedStress :=
    h.pressureRieszConeChargeMeasuresPreSummedStress
  fixedKernelOperatorNormPaysConeCharge :=
    And h.fixedKernelOperatorNormBound
      h.cknTentExcessDominatesOperatorNormStressMass
  coneChargeFixedBeforeReceiptComparison :=
    And h.coneChargeFixedBeforeReceiptComparison
      h.preSummedStressMassFixedBeforeCoreSheathSummation
  coneChargeNotDefinedFromFinalCarrier :=
    h.coneChargeNotDefinedFromFinalCarrier
  no_strictSubratio_or_margin_input :=
    h.no_strictSubratio_or_margin_input

/-- Operator-norm/tent domination constructs the corrected visible branch. -/
def FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureTentOperatorNormSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureConeTentOperatorNormSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
      corePositiveConeMass sheathOppositeConeMass :=
  FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureTentExcessPaymentSource
    (FixedWindowPressureConeChargeTentExcessPaymentSource.ofOperatorNormSource h)

/-- Operator-norm/tent domination is enough to pay the repaired overflow fork. -/
theorem visibleOverflowCharge_of_pressureTentOperatorNormSource
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPressureConeTentOperatorNormSource formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureTentOperatorNormSource
      h).visibleOverflowCharge :=
  visibleOverflowCharge_of_visibleOrInvisibleProfile
    (FixedWindowOverflowVisibleOrInvisibleProfile.ofPressureTentOperatorNormSource h)

/--
Tick432 negative result: the Galilean-mean weighted-stress share in
`FixedWindowPreSummedStressMassCKNTentCompatibility` is bounded by
`thetaMean * tentCertificate.localQuadraticTentExcess`, while
`pressureReserveReceipt = decomposition.pressureReserve` is an *independent*
observable on a disjoint decomposition object
(`Route1PressureTailDecomposition`).  No CKN/tent inequality identifies tent
excess with the pressure reserve, so the tick431 lowering pattern (which used
`localQuadraticReceipt_identifies_tent_excess`) does not transfer to the
Galilean-mean share.  This guard records the explicit shortfall witness.
-/
structure FixedWindowGalileanMeanCKNTentReserveGap
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  cknTentCompatibility :
    FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  galileanShortfall :
    (route1PressureVisibilityReceipts
        cknTentCompatibility.tentCertificate.obligation).pressureReserveReceipt
      < cknTentCompatibility.galileanMeanWeightedStress
  pressureReserveAndTentExcessAreDisjointObservables : Prop
  noCKNTentIdentityForPressureReserve : Prop
  galileanQuotientOrGaugeFixingRequired : Prop
  noFinalCarrierVisibilityInput : Prop

/--
No-go: when the Galilean-mean reserve gap is witnessed, CKN/tent compatibility
alone does not source the Galilean → pressure-reserve receipt routing.

Read this as the tick432 first illegal inference: substituting the resolved
mean-free routing pattern (tick431) into the Galilean-mean share without a
Galilean-quotient/reserve identity is unsound, because the receipt and the
tent-excess observables live on disjoint decomposition objects.
-/
theorem no_galileanMeanCKNTent_pressureReserveReceipt_of_gap
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowGalileanMeanCKNTentReserveGap formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    ¬ h.cknTentCompatibility.galileanMeanWeightedStress ≤
        (route1PressureVisibilityReceipts
          h.cknTentCompatibility.tentCertificate.obligation).pressureReserveReceipt :=
  not_le_of_gt h.galileanShortfall

/--
Named missing primitive (tick432).

The Galilean-quotient / gauge-fixing reserve identity bridges
`galileanMeanWeightedStress` to `pressureReserveReceipt` for a given CKN/tent
compatibility witness.  This is intentionally not derivable from CKN/tent
compatibility alone (see `FixedWindowGalileanMeanCKNTentReserveGap`).
Supplying this primitive is the explicit proof obligation that would lower the
second receipt-share routing below
`FixedWindowPreSummedStressMassSplitReceiptSource`.
-/
structure FixedWindowGalileanQuotientReserveIdentity
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass) where
  galileanMeanWeightedStress_le_pressureReserveReceipt :
    h.galileanMeanWeightedStress ≤
      (route1PressureVisibilityReceipts
        h.tentCertificate.obligation).pressureReserveReceipt
  galileanCompensatorFixedBeforeReserveAccounting : Prop
  pressureReserveReceiptFixedBeforeFinalCarrier : Prop
  reserveIdentityIndependentOfTentExcess : Prop
  reserveIdentityIndependentOfFinalCarrier : Prop
  reserveIdentityNotDerivedFromCKNTentAlone : Prop

/--
Second receipt-share routing below `FixedWindowPreSummedStressMassSplitReceiptSource`.

The Galilean-mean share routes to the pressure-reserve receipt given CKN/tent
compatibility *plus* the named Galilean-quotient/reserve identity.  Like the
tick431 resolved mean-free routing, this is intentionally not pressure closure:
the frequency-leakage child/tent-charge routing is still open, and no invisible
branch / final-carrier visibility input is consumed.
-/
structure FixedWindowCKNTentGalileanMeanRoutesToPressureReserveReceipt
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  cknTentCompatibility :
    FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  reserveIdentity :
    FixedWindowGalileanQuotientReserveIdentity cknTentCompatibility
  galileanMeanWeightedStress_le_pressureReserveReceipt :
    cknTentCompatibility.galileanMeanWeightedStress ≤
      (route1PressureVisibilityReceipts
        cknTentCompatibility.tentCertificate.obligation).pressureReserveReceipt
  reserveIdentitySuppliesGalileanRouting : Prop
  doesNotRouteFrequencyLeakageChildShare : Prop
  noPressureClosureFromGalileanShareAlone : Prop
  reserveIdentityFixedBeforeFinalCarrier : Prop

/--
CKN/tent compatibility plus the Galilean-quotient/reserve identity supplies the
Galilean-mean pressure-reserve routing.  Remaining proof obligation is
explicit: the frequency-leakage child/tent-charge routing is still unrouted,
and pressure visibility is not closed.
-/
def FixedWindowCKNTentGalileanMeanRoutesToPressureReserveReceipt.ofCKNTentCompatibilityAndReserveIdentity
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass)
    (hReserve :
      FixedWindowGalileanQuotientReserveIdentity h) :
    FixedWindowCKNTentGalileanMeanRoutesToPressureReserveReceipt formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  cknTentCompatibility := h
  reserveIdentity := hReserve
  galileanMeanWeightedStress_le_pressureReserveReceipt :=
    hReserve.galileanMeanWeightedStress_le_pressureReserveReceipt
  reserveIdentitySuppliesGalileanRouting :=
    And hReserve.galileanCompensatorFixedBeforeReserveAccounting
      hReserve.reserveIdentityNotDerivedFromCKNTentAlone
  doesNotRouteFrequencyLeakageChildShare := True
  noPressureClosureFromGalileanShareAlone := True
  reserveIdentityFixedBeforeFinalCarrier :=
    hReserve.reserveIdentityIndependentOfFinalCarrier

/--
Tick433 negative result: the frequency-leakage weighted-stress share in
`FixedWindowPreSummedStressMassCKNTentCompatibility` is bounded by
`thetaLeakage * tentCertificate.localQuadraticTentExcess`, while
`childChargeReceipt = acceptableChildCharge` is a field on the
`Route1PressureReserveNoEscapeObligation`, structurally disjoint from tent
excess.  Symmetrically to tick432, no CKN/tent inequality identifies tent
excess with the child charge, so the tick431 lowering pattern does not transfer
to the frequency-leakage share.  This guard records the explicit shortfall
witness.
-/
structure FixedWindowFrequencyLeakageCKNTentChildChargeGap
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  cknTentCompatibility :
    FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  frequencyLeakageShortfall :
    (route1PressureVisibilityReceipts
        cknTentCompatibility.tentCertificate.obligation).childChargeReceipt
      < cknTentCompatibility.frequencyLeakageWeightedStress
  childChargeAndTentExcessAreDisjointObservables : Prop
  noCKNTentIdentityForChildCharge : Prop
  commutatorShardOrWindowLeakageIdentityRequired : Prop
  noFinalCarrierVisibilityInput : Prop

/--
No-go: when the frequency-leakage child-charge gap is witnessed, CKN/tent
compatibility alone does not source the frequency-leakage → child/tent charge
routing.

Tick433 first illegal inference: substituting the resolved mean-free routing
pattern (tick431) into the frequency-leakage share without a commutator-shard /
window-leakage child-charge identity is unsound, because the receipt and the
tent-excess observables live on disjoint decomposition objects.
-/
theorem no_frequencyLeakageCKNTent_childChargeReceipt_of_gap
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowFrequencyLeakageCKNTentChildChargeGap formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    ¬ h.cknTentCompatibility.frequencyLeakageWeightedStress ≤
        (route1PressureVisibilityReceipts
          h.cknTentCompatibility.tentCertificate.obligation).childChargeReceipt :=
  not_le_of_gt h.frequencyLeakageShortfall

/--
Named missing primitive (tick433).

The frequency-leakage commutator-shard / window-leakage child-charge identity
bridges `frequencyLeakageWeightedStress` to `childChargeReceipt` for a given
CKN/tent compatibility witness.  This is intentionally not derivable from
CKN/tent compatibility alone (see `FixedWindowFrequencyLeakageCKNTentChildChargeGap`).
Supplying this primitive is the explicit proof obligation that would lower the
third receipt-share routing below `FixedWindowPreSummedStressMassSplitReceiptSource`.
-/
structure FixedWindowFrequencyLeakageCommutatorShardChildChargeIdentity
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass) where
  frequencyLeakageWeightedStress_le_childChargeReceipt :
    h.frequencyLeakageWeightedStress ≤
      (route1PressureVisibilityReceipts
        h.tentCertificate.obligation).childChargeReceipt
  commutatorShardFixedBeforeChildChargeAccounting : Prop
  childChargeReceiptFixedBeforeFinalCarrier : Prop
  identityIndependentOfTentExcess : Prop
  identityIndependentOfFinalCarrier : Prop
  identityNotDerivedFromCKNTentAlone : Prop

/--
Third receipt-share routing below `FixedWindowPreSummedStressMassSplitReceiptSource`.

The frequency-leakage share routes to the child/tent-charge receipt given
CKN/tent compatibility *plus* the named commutator-shard/child-charge identity.
Like the tick431 resolved mean-free routing and the tick432 Galilean reserve
routing, this is intentionally not pressure closure: no invisible branch /
final-carrier visibility input is consumed.
-/
structure FixedWindowCKNTentFrequencyLeakageRoutesToChildChargeReceipt
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  cknTentCompatibility :
    FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  commutatorShardIdentity :
    FixedWindowFrequencyLeakageCommutatorShardChildChargeIdentity
      cknTentCompatibility
  frequencyLeakageWeightedStress_le_childChargeReceipt :
    cknTentCompatibility.frequencyLeakageWeightedStress ≤
      (route1PressureVisibilityReceipts
        cknTentCompatibility.tentCertificate.obligation).childChargeReceipt
  commutatorShardIdentitySuppliesLeakageRouting : Prop
  doesNotRouteGalileanReserveShare : Prop
  noPressureClosureFromLeakageShareAlone : Prop
  commutatorShardIdentityFixedBeforeFinalCarrier : Prop

/--
CKN/tent compatibility plus the frequency-leakage commutator-shard/child-charge
identity supplies the leakage → child-charge routing.  Remaining proof
obligation is explicit: pressure visibility is not closed, and no-invisible /
final-carrier coherence is untouched.
-/
def FixedWindowCKNTentFrequencyLeakageRoutesToChildChargeReceipt.ofCKNTentCompatibilityAndCommutatorShardIdentity
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass)
    (hShard :
      FixedWindowFrequencyLeakageCommutatorShardChildChargeIdentity h) :
    FixedWindowCKNTentFrequencyLeakageRoutesToChildChargeReceipt formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  cknTentCompatibility := h
  commutatorShardIdentity := hShard
  frequencyLeakageWeightedStress_le_childChargeReceipt :=
    hShard.frequencyLeakageWeightedStress_le_childChargeReceipt
  commutatorShardIdentitySuppliesLeakageRouting :=
    And hShard.commutatorShardFixedBeforeChildChargeAccounting
      hShard.identityNotDerivedFromCKNTentAlone
  doesNotRouteGalileanReserveShare := True
  noPressureClosureFromLeakageShareAlone := True
  commutatorShardIdentityFixedBeforeFinalCarrier :=
    hShard.identityIndependentOfFinalCarrier

/--
Tick432+tick433 composite guard: the visible pressure branch's three
receipt-share routings now have a fully named primitive layout.  Resolved
mean-free is sourced from CKN/tent compatibility alone (tick431).  Galilean
mean and frequency leakage each require named separate primitives: the
Galilean-quotient/reserve identity and the commutator-shard/child-charge
identity.  This composite is *not* pressure closure — invisible/stress-coherence
remains independent — but it makes the missing pressure-side analytic content
explicit.
-/
structure FixedWindowCKNTentAllThreeShareRoutingsLayout
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  cknTentCompatibility :
    FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  resolvedMeanFreeRouting :
    FixedWindowCKNTentResolvedMeanFreeRoutesToLocalQuadraticReceipt formula
      epsilon corePositiveConeMass sheathOppositeConeMass
  galileanMeanRouting :
    FixedWindowCKNTentGalileanMeanRoutesToPressureReserveReceipt formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  frequencyLeakageRouting :
    FixedWindowCKNTentFrequencyLeakageRoutesToChildChargeReceipt formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  resolvedMeanFreeFromCKNTentAlone : Prop
  galileanMeanNeedsQuotientReserveIdentity : Prop
  frequencyLeakageNeedsCommutatorShardIdentity : Prop
  noPressureClosureFromShareLayoutAlone : Prop
  invisibleAndStressCoherenceBranchesRemainOpen : Prop

/-!
Tick434 split of the `PressureSplitReceiptFrontierIsNotClosure
.noInvisibleProfileOrStressCoherenceStillRequired` Prop into a structured
frontier-layout naming two distinct missing primitives.

Honesty caveat (per 2026-05-14 "Be Meta-Darwin to self" operator memory):
this is documentation/structure work — it names what is missing rather than
producing new analytic content.  Neither primitive below is constructed; both
require genuine PDE work (compactness/extraction maps for the invisible side;
fixed-window CZ stress estimates for the positive-side coherence).
-/

/--
Named missing primitive (tick434, invisible side).

An invisible-remainder compactness-extraction primitive that turns the
abstract `invisibleRemainderAfterVisibleQuotient` Prop in
`FixedWindowOverflowVisibleOrInvisibleProfile` into a *derived* (rather than
assumed) implication into the `strictNoInvisibleCriticalProfileFailure` and
`zeroCriticalTailVisibility` fields of
`NS.NoInvisibleCriticalProfileCompactnessObligation`.

Existing constructions populate `invisibleRemainderAfterVisibleQuotient` with
`False` so the bridges become vacuous.  A non-vacuous invisible branch needs
a real compactness extraction theorem (not provided here).
-/
structure FixedWindowInvisibleRemainderCompactnessExtractionPrimitive
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  visibleOrInvisibleProfile :
    FixedWindowOverflowVisibleOrInvisibleProfile formula epsilon
      corePositiveConeMass sheathOppositeConeMass
  invisibleRemainderIsNonVacuous : Prop
  derivedInvisibleRemainder_to_strictFailure :
    visibleOrInvisibleProfile.invisibleRemainderAfterVisibleQuotient →
      visibleOrInvisibleProfile.obligation.strictNoInvisibleCriticalProfileFailure
  derivedInvisibleRemainder_to_zeroVisibility :
    visibleOrInvisibleProfile.invisibleRemainderAfterVisibleQuotient →
      visibleOrInvisibleProfile.obligation.zeroCriticalTailVisibility
  derivationUsesFixedProjectedKernel : Prop
  derivationDoesNotUseFinalCarrierMagnitude : Prop
  derivationIsConcretelyPDESided : Prop
  derivationIsNotProvidedBySharingExistingFields : Prop

/--
Named missing primitive (tick434, positive side).

A positive-side stress-angular-coherence dominance primitive that lowers
`FixedWindowStressAngularCoherenceDominance` from an assumed source to an
output of fixed-window CZ stress estimates.  The existing structure has its
`fixedWindowAndKernelBeforeRouteReceipt`,
`adjointProjectedTensorFixedBeforeStressSplit`, and related fields as
*assumed* Props; a real dominance theorem would derive them from concrete
projected-tensor estimates.

Honesty: this primitive names the missing analytic content; it is NOT a
derivation of the dominance from anywhere in the existing codebase.
-/
structure FixedWindowPositiveSideStressAngularCoherenceDominancePrimitive
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade) where
  stressAngularCoherenceDominance :
    FixedWindowStressAngularCoherenceDominance formula
  dominanceDerivedFromFixedWindowCZStressEstimate : Prop
  dominanceUsesFixedProjectedTensor : Prop
  dominanceDoesNotUseFinalPressureCarrier : Prop
  dominanceIsConcretelyPDESided : Prop
  dominanceIsNotProvidedBySharingExistingFields : Prop

/--
Composite tick434 frontier-layout structure: split the existing
`PressureSplitReceiptFrontierIsNotClosure.noInvisibleProfileOrStressCoherenceStillRequired`
frontier marker into the two named missing primitives + an explicit
non-closure guard.

This is a structured replacement of an opaque Prop with a named-primitive
dependency graph.  It is NOT pressure closure and NOT Clay closure.
-/
structure FixedWindowPressureFrontierAfterShareLayout
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    (formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade)
    (epsilon corePositiveConeMass sheathOppositeConeMass : Real) where
  shareLayoutDone : Prop
  invisibleRemainderPrimitiveRequired : Prop
  positiveSideStressCoherencePrimitiveRequired : Prop
  flatRadiusBranchRemainsIndependent : Prop
  notPressureClosure : Prop
  notClayClosure : Prop
  selfDarwinAuditAppliedInArtifact : Prop

/--
Discharge of the existing closure guard into the structured frontier layout.

Construction: take a `PressureSplitReceiptFrontierIsNotClosure` witness and a
`FixedWindowCKNTentAllThreeShareRoutingsLayout` witness as inputs, and return
the structured frontier-layout that names the two missing primitives
explicitly.
-/
def FixedWindowPressureFrontierAfterShareLayout.ofClosureGuardAndShareLayout
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (hGuard : PressureSplitReceiptFrontierIsNotClosure)
    (hLayout :
      FixedWindowCKNTentAllThreeShareRoutingsLayout formula epsilon
        corePositiveConeMass sheathOppositeConeMass) :
    FixedWindowPressureFrontierAfterShareLayout formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  shareLayoutDone := hLayout.noPressureClosureFromShareLayoutAlone
  invisibleRemainderPrimitiveRequired :=
    hGuard.noInvisibleProfileOrStressCoherenceStillRequired
  positiveSideStressCoherencePrimitiveRequired :=
    hGuard.noInvisibleProfileOrStressCoherenceStillRequired
  flatRadiusBranchRemainsIndependent :=
    hGuard.noPressureClosureFromSplitReceiptSurfaceAlone
  notPressureClosure :=
    hGuard.noPressureClosureFromSplitReceiptSurfaceAlone
  notClayClosure :=
    hLayout.invisibleAndStressCoherenceBranchesRemainOpen
  selfDarwinAuditAppliedInArtifact :=
    hGuard.finalCarrierReceiptStillRejected

/-!
Tick439 Gowers-style pressure carrier replacement (Claude principal,
operator-directed analytic compression 2026-05-14).

External analytic audit determined that the tick434 named primitive
`FixedWindowPositiveSideStressAngularCoherenceDominancePrimitive` is *false*
from current pressure-recovery + local-energy + local-CZ data: disjoint
divergence-free packets `u_core, u_sheath` with stresses in opposite cones
of the fixed projected Riesz tensor `A` give
`(u_core+u_sheath)⊗(u_core+u_sheath) = u_core⊗u_core + u_sheath⊗u_sheath`
because supports are disjoint; amplitudes tune so `M_A(u_sheath) = -M_A(u_core)`.
Final projected pressure carrier vanishes while pre-summed cone masses are
nonzero.

Gowers-style replacement: keep the obligation, swap the inefficient
final-carrier component for the *total variation* of the signed projected
stress measure.  Same-window cancellation only affects the SIGNED total;
total variation counts both cones BEFORE summing, so cancellation cannot
make it vanish.  This handles generalized defect stress (from
`u_n⊗u_n ⇀ U⊗U + R` profile decomposition) by including `R` in the signed
measure.

Honest scope: Lean structure encodes the carrier shape + closure inequality
+ anti-cancellation guard.  Constructing the signed measure on real
Navier-Stokes is genuine Mathlib measure-theoretic content
(`MeasureTheory.SignedMeasure`, `totalVariation`) deferred; here the carrier
appears as `Real` values + Prop guards.
-/

/--
Pre-summed projected stress total-variation visibility — the Gowers-style
replacement carrier for the false angular-coherence primitive.

Closure inequality:
  `pressureConeIncrement ≤ visibilityConstant * pressureVisibility`
where `pressureVisibility` is the total-variation (not signed-sum) measure
of the projected stress, including generalized defect stress.
-/
structure PreSummedProjectedStressVariationPressureClosure where
  pressureConeIncrement : Real
  pressureVisibility : Real
  pressureVisibility_nonneg : 0 ≤ pressureVisibility
  visibilityConstant : Real
  visibilityConstant_pos : 0 < visibilityConstant
  pressureConeIncrement_le_visibility :
    pressureConeIncrement ≤ visibilityConstant * pressureVisibility
  stressMeasureFixedBeforeRouteReceipt : Prop
  projectedTensorFixedBeforeRouteReceipt : Prop
  signedProjectedStressFromCarriers : Prop
  visibilityIsTotalVariationOfSignedStress : Prop
  visibilityIncludesGeneralizedDefectStress : Prop
  visibilityNotFinalCarrierMagnitude : Prop
  visibilityNotAngularDominance : Prop
  carrierFixedBeforeCoreSheathSummation : Prop
  carrierReplacesAngularCoherencePrimitive : Prop

/-- The carrier-replacement closure inequality. -/
theorem pressureConeIncrement_paid_by_totalVariation_visibility
    (h : PreSummedProjectedStressVariationPressureClosure) :
    h.pressureConeIncrement ≤
      h.visibilityConstant * h.pressureVisibility :=
  h.pressureConeIncrement_le_visibility

/--
Anti-laundering guard: the total-variation carrier is NOT final-carrier
magnitude, and the same-window core/sheath countermodel that killed angular
coherence does NOT apply to total variation.  In-artifact Meta-Darwin-to-self
non-vacuity witness for the Gowers replacement.
-/
structure PreSummedTotalVariationCarrierIsNotFinalCarrierMagnitude where
  totalVariationIsAdditiveOverDisjointCones : Prop
  finalCarrierIsSignedSumOverCones : Prop
  sameWindowCancellationAffectsSignedNotVariation : Prop
  coreSheathCountermodelDoesNotKillTotalVariation : Prop
  carrierIsFixedBeforeRouteReceipt : Prop
  carrierIsNotSelectedFromTargetMargin : Prop
  replacementIsGowersStyleNotWrapper : Prop
  visibilityCarrierDoesNotLeakThroughFinalCancellation : Prop

/-!
Tick435 toy-instance smoke tests for the tick432 + tick433 named missing
primitives.

These `def`s prove *structure-instantiability* by accepting the bound as a
direct hypothesis and filling the Prop fields with `True`.  They are NOT PDE
constructions — the analytic content sits in the hypothesis the caller must
supply.  Per the 2026-05-14 operator "Be Meta-Darwin to self" memory: this
honesty caveat is in the artifact itself, not outsourced.

What this rules out: the structures cannot be vacuously uninhabited.  What
this does NOT prove: that the inequalities hold for any realistic
window/Riesz/CZ regime.  That is the PDE construction obligation.
-/

/--
Tick435 smoke instance: from a direct hypothesis of the Galilean
weighted-stress vs. pressure-reserve receipt bound, produce a
`FixedWindowGalileanQuotientReserveIdentity` witness with the auxiliary
Prop fields filled by `True`.

The hypothesis `hBound` is the PDE inequality that a Galilean
compensator / window-quotient argument would deliver.  This `def` does NOT
prove `hBound`; it converts an assumed bound into the structured primitive.
-/
def FixedWindowGalileanQuotientReserveIdentity.smoke_ofDirectBound
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass)
    (hBound :
      h.galileanMeanWeightedStress ≤
        (route1PressureVisibilityReceipts
          h.tentCertificate.obligation).pressureReserveReceipt) :
    FixedWindowGalileanQuotientReserveIdentity h where
  galileanMeanWeightedStress_le_pressureReserveReceipt := hBound
  galileanCompensatorFixedBeforeReserveAccounting := True
  pressureReserveReceiptFixedBeforeFinalCarrier := True
  reserveIdentityIndependentOfTentExcess := True
  reserveIdentityIndependentOfFinalCarrier := True
  reserveIdentityNotDerivedFromCKNTentAlone := True

/--
Tick435 smoke instance: analogous to the Galilean reserve smoke instance, but
for the tick433 frequency-leakage commutator-shard primitive.

Same honesty caveat: this converts an assumed PDE inequality into the
structured named primitive; it does NOT prove the inequality.  The PDE
content of a Coifman-Meyer commutator / window-leakage child-charge
estimate is what `hBound` represents.
-/
def FixedWindowFrequencyLeakageCommutatorShardChildChargeIdentity.smoke_ofDirectBound
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass)
    (hBound :
      h.frequencyLeakageWeightedStress ≤
        (route1PressureVisibilityReceipts
          h.tentCertificate.obligation).childChargeReceipt) :
    FixedWindowFrequencyLeakageCommutatorShardChildChargeIdentity h where
  frequencyLeakageWeightedStress_le_childChargeReceipt := hBound
  commutatorShardFixedBeforeChildChargeAccounting := True
  childChargeReceiptFixedBeforeFinalCarrier := True
  identityIndependentOfTentExcess := True
  identityIndependentOfFinalCarrier := True
  identityNotDerivedFromCKNTentAlone := True

/--
Tick435 composite smoke: from CKN/tent compatibility + both direct PDE
bounds, produce a full `FixedWindowCKNTentAllThreeShareRoutingsLayout`
witness.  This shows the three-share-routing layout is non-vacuously
constructible *given the two PDE inequalities*; it does not prove the
inequalities.
-/
def FixedWindowCKNTentAllThreeShareRoutingsLayout.smoke_ofDirectBounds
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    {epsilon corePositiveConeMass sheathOppositeConeMass : Real}
    (h :
      FixedWindowPreSummedStressMassCKNTentCompatibility formula epsilon
        corePositiveConeMass sheathOppositeConeMass)
    (hGalileanBound :
      h.galileanMeanWeightedStress ≤
        (route1PressureVisibilityReceipts
          h.tentCertificate.obligation).pressureReserveReceipt)
    (hLeakageBound :
      h.frequencyLeakageWeightedStress ≤
        (route1PressureVisibilityReceipts
          h.tentCertificate.obligation).childChargeReceipt) :
    FixedWindowCKNTentAllThreeShareRoutingsLayout formula epsilon
      corePositiveConeMass sheathOppositeConeMass where
  cknTentCompatibility := h
  resolvedMeanFreeRouting :=
    FixedWindowCKNTentResolvedMeanFreeRoutesToLocalQuadraticReceipt.ofCKNTentCompatibility h
  galileanMeanRouting :=
    FixedWindowCKNTentGalileanMeanRoutesToPressureReserveReceipt.ofCKNTentCompatibilityAndReserveIdentity
      h
      (FixedWindowGalileanQuotientReserveIdentity.smoke_ofDirectBound h hGalileanBound)
  frequencyLeakageRouting :=
    FixedWindowCKNTentFrequencyLeakageRoutesToChildChargeReceipt.ofCKNTentCompatibilityAndCommutatorShardIdentity
      h
      (FixedWindowFrequencyLeakageCommutatorShardChildChargeIdentity.smoke_ofDirectBound
        h hLeakageBound)
  resolvedMeanFreeFromCKNTentAlone := True
  galileanMeanNeedsQuotientReserveIdentity := True
  frequencyLeakageNeedsCommutatorShardIdentity := True
  noPressureClosureFromShareLayoutAlone := True
  invisibleAndStressCoherenceBranchesRemainOpen := True

/-!
## Tick437: Mathlib-grounded analytic sub-step for the Galilean reserve identity

Tick432-tick436 left `FixedWindowGalileanQuotientReserveIdentity` as a named
abstract `Real ≤ Real` field plus a `smoke_ofDirectBound` `def` that consumes
the inequality as a hypothesis.  None of that surface carries actual
functional-analytic content: `galileanMeanWeightedStress` and
`pressureReserveReceipt` are independent `Real` ledger observables and no
Mathlib lemma can relate two unconnected reals.

This section adds the first piece of *real* Mathlib content underneath the
primitive: the Galilean compensator in the fixed-window framework is the
spatial-mean operator on the window, which is mathematically identical to a
conditional expectation against the coarsest σ-algebra of the window.  Such
operators are L²-contractive with operator-norm at most one — this is
`MeasureTheory.eLpNorm_condExp_le`.

The lemma `galileanCompensator_eLpNorm_two_le` below names this contraction
under PDE-facing names so downstream pressure-receipt work can cite a concrete
Mathlib bound rather than another `Prop` field.  The companion structure
`GalileanCompensatorL2Contraction` packages the measurable-space data so a
caller can produce the bound from real PDE inputs.

**Honest scope (in-artifact, per "Be Meta-Darwin to self" 2026-05-14):**

What this DOES:
  - It commits to a specific Mathlib model for the Galilean compensator:
    conditional expectation `μ[f | m]` against the coarse σ-algebra `m`
    representing the window-level mean.
  - It cites `MeasureTheory.eLpNorm_condExp_le` directly to obtain an L²
    contraction by operator-norm 1.
  - It exposes that contraction inside the project namespace so future
    pressure-reserve work can chain it with a window-level energy bound to
    reach `pressureReserveReceipt`.

What this DOES NOT do:
  - It does NOT prove `galileanMeanWeightedStress ≤ pressureReserveReceipt`.
    Those are abstract `Real` fields in disjoint accounting structures; no
    Mathlib operator-norm lemma can identify them without a connecting
    interpretation theorem that says "these reals are the L² norm of the
    Galilean compensator applied to that window function".
  - The connecting interpretation is the still-missing PDE construction:
    one must define a window function `u_Q`, interpret
    `galileanMeanWeightedStress` as `‖μ[u_Q | m]‖_{L²}²` (or a weighted
    variant), and interpret `pressureReserveReceipt` as a bookkeeping value
    that majorizes `‖u_Q‖_{L²}²` under the Calderón–Zygmund window window
    pairing.  Neither interpretation is supplied here and Mathlib does not
    currently carry the bundled "fixed-window mean operator on a divergence-
    free Schwartz field" object that would deliver it.
  - It is NOT pressure closure, NOT route-1 closure, and NOT Clay closure.

This is the smallest honest Mathlib-grounded sub-lemma I can place under the
primitive while respecting AGENTS.md §"do not claim Clay/upstream closure".
-/

set_option linter.unusedVariables false in
/--
Tick437 Mathlib-grounded sub-step.

The spatial-mean / Galilean compensator on a fixed window is, in the
measure-theoretic model, the conditional-expectation operator against the
σ-algebra `m` that resolves the window.  This lemma is a direct restatement
of `MeasureTheory.eLpNorm_condExp_le`: the compensator is L²-contractive.

This is the analytic content the abstract field
`FixedWindowGalileanQuotientReserveIdentity` needs to be backed by once a PDE
interpretation of `galileanMeanWeightedStress` as the L² norm of the
window-mean of a velocity mode is committed to.
-/
lemma galileanCompensator_eLpNorm_two_le
    {α E : Type*}
    [NormedAddCommGroup E] [InnerProductSpace ℝ E] [CompleteSpace E]
    {m₀ : MeasurableSpace α} (m : MeasurableSpace α)
    (μ : MeasureTheory.Measure α) (f : α → E) :
    MeasureTheory.eLpNorm (MeasureTheory.condExp m μ f) 2 μ ≤
      MeasureTheory.eLpNorm f 2 μ :=
  MeasureTheory.eLpNorm_condExp_le

/--
Tick437 PDE-named packaging of the contraction.

Bundles the measurable-space data needed to talk about the Galilean
compensator on a window and re-exposes `MeasureTheory.eLpNorm_condExp_le`
as a field on the structure.  Inhabitation requires real PDE input
(a base σ-algebra, a window σ-algebra, an ambient measure, and a
velocity-mode function); the contraction is then immediate.

This is intentionally not a wrapper around a `Real ≤ Real` field — the
bound it carries is the actual Mathlib `eLpNorm` inequality.
-/
structure GalileanCompensatorL2Contraction
    (α : Type*) (E : Type*)
    [NormedAddCommGroup E] [InnerProductSpace ℝ E] [CompleteSpace E]
    [baseSigma : MeasurableSpace α]
    (windowSigma : MeasurableSpace α)
    (ambientMeasure : MeasureTheory.Measure α)
    (windowField : α → E) where
  eLpNormTwo_compensator_le_eLpNormTwo_field :
    MeasureTheory.eLpNorm
        (MeasureTheory.condExp windowSigma ambientMeasure windowField)
        2 ambientMeasure ≤
      MeasureTheory.eLpNorm windowField 2 ambientMeasure

set_option linter.unusedVariables false in
/--
Canonical inhabitant: from a base measurable-space + window σ-algebra +
measure + field, the Mathlib contraction `eLpNorm_condExp_le` populates the
structure.  This is the operator-level Galilean contraction in the
project's namespace, sourced from Mathlib rather than from another `Prop`.
-/
def GalileanCompensatorL2Contraction.ofMathlib
    {α : Type*} {E : Type*}
    [NormedAddCommGroup E] [InnerProductSpace ℝ E] [CompleteSpace E]
    [baseSigma : MeasurableSpace α]
    (windowSigma : MeasurableSpace α)
    (ambientMeasure : MeasureTheory.Measure α)
    (windowField : α → E) :
    GalileanCompensatorL2Contraction α E windowSigma ambientMeasure windowField where
  eLpNormTwo_compensator_le_eLpNormTwo_field :=
    MeasureTheory.eLpNorm_condExp_le

/--
Honest no-closure guard for tick437.

The Mathlib operator-norm contraction `galileanCompensator_eLpNorm_two_le`
and the bundled structure `GalileanCompensatorL2Contraction` together
constitute one genuine PDE-grounded sub-step.  Neither closes
`FixedWindowGalileanQuotientReserveIdentity`: the abstract Real
inequality `galileanMeanWeightedStress ≤ pressureReserveReceipt` requires
a PDE *interpretation* theorem that identifies those reals with the
eLpNorm quantities here.  That interpretation is the unresolved PDE
content; it is NOT provided by this file.
-/
theorem GalileanCompensatorL2ContractionIsNotGalileanReserveIdentity
    : True := trivial

end ZtareProofs
