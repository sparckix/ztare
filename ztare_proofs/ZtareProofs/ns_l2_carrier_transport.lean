import Mathlib.Tactic
import ZtareProofs.ns_pressure_hessian_l2_bridge

namespace ZtareProofs

/-!
`ns_l2_carrier_transport` isolates the exact live frontier after the
Phase 5CG pressure-Hessian rewrite.

This file does not claim the NS branch is complete. It records the remaining
transport-style obligation in the narrowest honest form:

* the exact algebraic layer is already separate (`ns_quadrupole_identity`);
* coherent stretch is controlled through the renormalized `l = 2`
  pressure-Hessian channel plus a remainder;
* the remaining dynamic gap is the transport inequality for that difference,
  with a Calderon-commutator residual routed into the high modes.
-/

/-- Renormalized coherent-stretch observable, e.g. axial singular-value proxy. -/
abbrev CoherentStretchObservable := Real

/-- Material derivative of the coherent-stretch / pressure-carrier defect. -/
abbrev CarrierTransportDefect := Real

/-- Local quadratic transport contribution, e.g. `|∇u|^2`. -/
abbrev LocalQuadraticTerm := Real

/-- Advection term acting on the renormalized pressure-Hessian `l = 2` carrier. -/
abbrev AdvectedPressureCarrierTerm := Real

/-- Active radial grade used by the current pressure-facing route. -/
abbrev ActiveRadialGrade := Real

/-- Fixed reference enstrophy floor preventing fake singular denominators. -/
abbrev ReferenceEnstrophyFloor := Real

/-- Leading-order candidate for the material derivative of coherent stretch. -/
abbrev LeadingOrderStretchTransport := Real

/--
Repo-native scalar pressure-`l = 2` carrier used by the live frontier.

This is the exact object the transport defect is measured against. It keeps the
branch anchored to the pressure-Hessian route rather than to a free scalar
proxy.
-/
noncomputable def pressureL2CarrierObservable
    (pressureL2 vorticitySq radialGrade Λ0 : Real) : Real :=
  pressureL2 * vorticitySq / max radialGrade Λ0

/--
Observable `C` is only a leading-order candidate until the PDE derivation is paid.

This records the sharpest honest midpoint between "pure empirical fit" and
"already a theorem": under the pressure-Hessian `l = 2` route, the live scalar
is the candidate principal term in the transport of coherent stretch, up to an
explicit residual budget.
-/
def pressureL2CarrierLeadingOrderCandidate
    (leadingOrder pressureL2 vorticitySq radialGrade Λ0 residual : Real) : Prop :=
  let p2 := pressureL2CarrierObservable pressureL2 vorticitySq radialGrade Λ0
  leadingOrder = p2 + residual

/--
Power-suppressed commutator residual hypothesis.

This is recorded explicitly rather than hidden inside prose. It is still an
obligation, not a proved estimate.
-/
def commutatorResidualPowerSuppressed
    (commutatorResidual radialGrade carrier K δ : Real) : Prop :=
  0 < δ ∧ commutatorResidual ≤ K * radialPowerWeight radialGrade δ * |carrier|

/--
Weaker honest version of the same residual hypothesis.

No fixed positive decay exponent is inserted by hand. The branch only records
that some radial-grade-dependent decay profile exists and is attached to the
commutator residual. This is closer to the true unpaid analytic work.
-/
def commutatorResidualProfileSuppressed
    (commutatorResidual carrier decayProfile : Real) : Prop :=
  0 ≤ decayProfile ∧ commutatorResidual ≤ decayProfile * |carrier|

/--
Exact remaining transport inequality target.

This is the weakest theorem-shaped statement still missing in the current
proof-facing route. It deliberately does not claim exact cancellation.
-/
def l2CarrierTransportInequality
    (transportDefect localQuadratic advectedPressure residual : Real) : Prop :=
  pressureHessianL2TransportTarget transportDefect localQuadratic advectedPressure residual

/--
Unpaid derivation target for observable `C`.

This is the exact fork the branch now sits on: either the current observable is
forced as the leading-order pressure-side transport scalar up to an explicit
residual, or the branch is still dressing an empirical proxy in PDE language.
-/
def observableC_PDE_derivation_obligation
    (leadingOrder pressureL2 vorticitySq radialGrade Λ0 residual
      transportDefect localQuadratic advectedPressure commutatorResidual
      decayProfile : Real) : Prop :=
  pressureL2CarrierLeadingOrderCandidate
      leadingOrder pressureL2 vorticitySq radialGrade Λ0 residual ∧
    l2CarrierTransportInequality
      transportDefect localQuadratic advectedPressure commutatorResidual ∧
    commutatorResidualProfileSuppressed commutatorResidual
      (pressureL2CarrierObservable pressureL2 vorticitySq radialGrade Λ0)
      decayProfile

/--
Verbatim live frontier in repo-native symbols.

Interpretation:

* `σ` is represented by `stretch`,
* `p₂` is `pressureL2CarrierObservable pressureL2 enstrophyGrade`,
* the defect is `D_t (σ - C₀ p₂)`,
* the residual term is required separately to be power-suppressed by active
  radial grade.
* the quadratic stretching residual is not cancelled by fiat; it is part of
  the unpaid defect budget that this obligation must control.

This remains an obligation. Nothing in this file claims it is proved.
-/
def pressureL2TransportDefectObligation
    (stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual : Real) : Prop :=
  let p2 := pressureL2CarrierObservable pressureL2 vorticitySq radialGrade Λ0
  l2CarrierTransportInequality
      transportDefect
      (C0 * localQuadratic)
      (C0 * advectedPressure) 
      commutatorResidual ∧
    commutatorResidualProfileSuppressed commutatorResidual p2 decayProfile

/--
Backward-compatible alias while the workspace notes and dependent cages are
updated to the stricter defect-focused naming.
-/
abbrev pressureL2TransportObligation := pressureL2TransportDefectObligation

/--
Combined transport-and-cap target.

If the pressure-Hessian `l = 2` bridge is paid and the transport defect is
controlled with a power-suppressed commutator residual, then the coherent
stretch reserve is bounded by the renormalized pressure carrier budget.
-/
def l2CarrierTransportClosureTarget
    (reserve pressureL2 higherFeedback grade C K δ cap
      transportDefect localQuadratic advectedPressure residual : Real) : Prop :=
  pressureHessianL2TransportBridgeTarget reserve pressureL2 higherFeedback
    grade C K δ transportDefect localQuadratic advectedPressure residual ∧
    C * renormalizedPressureHessianL2Carrier pressureL2 grade ≤ cap

/--
What the live frontier already gives if the transport closure target is paid:
the reserve is capped by the renormalized pressure carrier budget plus the
power-suppressed residual scale.

This is intentionally weaker than "global regularity follows". It is the
maximal honest theorem shape supported by the current cage.
-/
theorem reserve_capped_of_l2CarrierTransportClosureTarget
    {reserve pressureL2 higherFeedback grade C K δ cap
      transportDefect localQuadratic advectedPressure residual : Real}
    (h :
      l2CarrierTransportClosureTarget reserve pressureL2 higherFeedback grade C K δ cap
        transportDefect localQuadratic advectedPressure residual) :
    reserve ≤ cap + K * radialPowerWeight grade δ ∧
      l2CarrierTransportInequality transportDefect localQuadratic advectedPressure residual ∧
      calderonCommutatorResidualDecouple residual grade K δ := by
  rcases h with ⟨hbridge, hl2cap⟩
  exact reserve_capped_of_pressureHessianL2TransportBridgeTarget hbridge hl2cap

/--
If the verbatim transport obligation is paid, then the carrier defect is under
the exact pressure-facing control currently required by the branch.
-/
theorem transport_defect_control_of_pressureL2TransportObligation
    {stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual : Real}
    (h :
      pressureL2TransportDefectObligation stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual) :
    l2CarrierTransportInequality
        transportDefect
        (C0 * localQuadratic)
        (C0 * advectedPressure)
        commutatorResidual ∧
      commutatorResidualProfileSuppressed
        commutatorResidual
        (pressureL2CarrierObservable pressureL2 vorticitySq radialGrade Λ0)
        decayProfile := by
  simpa [pressureL2TransportDefectObligation]
    using h

/--
What the branch would gain if observable `C` were genuinely PDE-derived:
the current pressure-side scalar would be justified as a leading-order term
rather than only as the best empirical closure on the Phase 5CG family.
-/
theorem leading_order_candidate_of_observableC_PDE_derivation_obligation
    {leadingOrder pressureL2 vorticitySq radialGrade Λ0 residual
      transportDefect localQuadratic advectedPressure commutatorResidual
      decayProfile : Real}
    (h :
      observableC_PDE_derivation_obligation
        leadingOrder pressureL2 vorticitySq radialGrade Λ0 residual
        transportDefect localQuadratic advectedPressure commutatorResidual
        decayProfile) :
    pressureL2CarrierLeadingOrderCandidate
        leadingOrder pressureL2 vorticitySq radialGrade Λ0 residual ∧
      l2CarrierTransportInequality
        transportDefect localQuadratic advectedPressure commutatorResidual := by
  rcases h with ⟨hlead, htransport, _⟩
  exact ⟨hlead, htransport⟩

end ZtareProofs
