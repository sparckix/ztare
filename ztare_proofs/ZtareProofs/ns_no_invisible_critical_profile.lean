import Mathlib.Tactic

namespace ZtareProofs.NS

/-!
`ns_no_invisible_critical_profile` isolates the compactness/rigidity leg used
by route-1 critical-tail visibility.

This file deliberately avoids the later profile-price, GP216, and Phase 5FB
tail in `ns_profile_lsc_self_tax_obligation.lean`, so route1 can import the
no-invisible-profile surface without inheriting that downstream build debt.
-/

/-- Reduced positive lane: the route only survives in a scale-critical
topology with genuine tail smallness already visible to the price/payoff. -/
structure CriticalProfileTailSmallness where
  criticalTopologyFixedBeforePayoff : Prop
  tailSmallnessVisibleToPrice : Prop
  profileStabilityAvailable : Prop

/-- Explicit tail-visibility gauge for the reduced critical-topology route.
This isolates the exact place where the price/payoff must see the profile tail,
instead of letting that requirement hide inside a generic `tailSmallness`
label. -/
structure CriticalProfileTailGauge where
  tailGaugeDeclaredBeforePayoff : Prop
  tailGaugeTendsToZeroAlongProfileTail : Prop
  payoffTailControlledByGauge : Prop

/-- The 2026-05-09 super-mega route reduction sharpened the surviving
critical-profile lane one level earlier: the route needs a genuine
Navier-Stokes critical topology with actual stability and common time windows,
not merely a symbolic tail gauge. -/
structure CriticalNSProfileTopology where
  chosenCriticalTopologyFixedBeforePayoff : Prop
  topologyIsScaleCriticalForNavierStokes : Prop
  perturbativeStabilityAvailableInTopology : Prop
  commonProfileLifespanWindowAvailable : Prop

/-- Bind the critical tail gauge to an actual nonlinear critical profile
decomposition, rather than letting the gauge float free as a label. -/
structure NSCriticalProfileDecomposition where
  topology : CriticalNSProfileTopology
  profileFamilyAdmitsActualNonlinearNSProfiles : Prop
  amplitudesAreSquareSummable : Prop
  profileParametersAreOrthogonal : Prop
  criticalTailGauge : CriticalProfileTailGauge

/-- No-invisible-critical-profile compactness obligation.

This is the compactness-side surface extracted from the GPT-5.5 tail response:
a strict failure of the no-invisible-critical-profile principle must produce a
genuine nonzero critical profile; if that profile has zero tail visibility, the
rigidity theorem forces it to be zero; those two outputs contradict.  This
object deliberately does not assume a strict source-budget or scalar subratio.
-/
structure NoInvisibleCriticalProfileCompactnessObligation where
  decomposition : NSCriticalProfileDecomposition
  strictNoInvisibleCriticalProfileFailure : Prop
  zeroCriticalTailVisibility : Prop
  compactnessExtractsCriticalProfile : Prop
  extractedCriticalProfileNonzero : Prop
  extractedCriticalProfileRigid : Prop
  extractedCriticalProfileZero : Prop
  strict_failure_extracts_compact_profile :
    strictNoInvisibleCriticalProfileFailure →
      compactnessExtractsCriticalProfile
  strict_failure_extracts_nonzero_critical_profile :
    strictNoInvisibleCriticalProfileFailure →
      extractedCriticalProfileNonzero
  zero_visibility_forces_rigidity :
    zeroCriticalTailVisibility →
      extractedCriticalProfileRigid
  rigidity_forces_zero_profile :
    extractedCriticalProfileRigid →
      extractedCriticalProfileZero
  nonzero_profile_contradicts_zero_profile :
    extractedCriticalProfileNonzero →
      extractedCriticalProfileZero →
        False

/-- Projection edge: strict failure is not allowed to remain a scalar gap; it
must extract a compact critical profile witness. -/
theorem critical_profile_compactness_extraction_of_strict_failure
    (h : NoInvisibleCriticalProfileCompactnessObligation)
    (hFail : h.strictNoInvisibleCriticalProfileFailure) :
    h.compactnessExtractsCriticalProfile :=
  h.strict_failure_extracts_compact_profile hFail

/-- Projection edge: strict failure produces a nonzero critical profile. -/
theorem nonzero_critical_profile_of_strict_failure
    (h : NoInvisibleCriticalProfileCompactnessObligation)
    (hFail : h.strictNoInvisibleCriticalProfileFailure) :
    h.extractedCriticalProfileNonzero :=
  h.strict_failure_extracts_nonzero_critical_profile hFail

/-- Projection edge: zero visibility routes through rigidity before producing
the zero-profile conclusion. -/
theorem zero_profile_of_zero_visibility
    (h : NoInvisibleCriticalProfileCompactnessObligation)
    (hZeroVisibility : h.zeroCriticalTailVisibility) :
    h.extractedCriticalProfileZero :=
  h.rigidity_forces_zero_profile
    (h.zero_visibility_forces_rigidity hZeroVisibility)

/-- The no-invisible-critical-profile contradiction.

Once strict failure has extracted a nonzero critical profile, zero visibility
cannot also hold under the rigidity receipt. -/
theorem no_invisible_critical_profile_of_compactness_obligation
    (h : NoInvisibleCriticalProfileCompactnessObligation)
    (hFail : h.strictNoInvisibleCriticalProfileFailure)
    (hZeroVisibility : h.zeroCriticalTailVisibility) :
    False :=
  h.nonzero_profile_contradicts_zero_profile
    (nonzero_critical_profile_of_strict_failure h hFail)
    (zero_profile_of_zero_visibility h hZeroVisibility)

/-- Compact projection surface for the no-invisible-critical-profile leg.

The surface keeps the three relevant channels separate: strict failure projects
to an extracted compact profile, the extracted profile is nonzero, and zero
critical-tail visibility projects through rigidity.  It intentionally avoids
any source-subratio hypothesis or any definition of visibility as a scalar
residual. -/
structure NoInvisibleCriticalProfileCompactProjectionSurface where
  obligation : NoInvisibleCriticalProfileCompactnessObligation
  strictFailureWitness :
    obligation.strictNoInvisibleCriticalProfileFailure
  zeroChannelVisibilityWitness :
    obligation.zeroCriticalTailVisibility
  compactProjectionWitness :
    obligation.compactnessExtractsCriticalProfile
  nonzeroExtractedProfileWitness :
    obligation.extractedCriticalProfileNonzero
  zeroVisibilityRigidityWitness :
    obligation.extractedCriticalProfileRigid

/-- Strict failure and zero channel visibility canonically project to the
compact contradiction surface. -/
def noInvisibleCriticalProfileCompactProjectionSurface
    (h : NoInvisibleCriticalProfileCompactnessObligation)
    (hFail : h.strictNoInvisibleCriticalProfileFailure)
    (hZeroVisibility : h.zeroCriticalTailVisibility) :
    NoInvisibleCriticalProfileCompactProjectionSurface where
  obligation := h
  strictFailureWitness := hFail
  zeroChannelVisibilityWitness := hZeroVisibility
  compactProjectionWitness :=
    critical_profile_compactness_extraction_of_strict_failure h hFail
  nonzeroExtractedProfileWitness :=
    nonzero_critical_profile_of_strict_failure h hFail
  zeroVisibilityRigidityWitness :=
    h.zero_visibility_forces_rigidity hZeroVisibility

/-- Contradiction edge for the compact projection surface: strict failure gives
a nonzero extracted profile, while zero channel visibility routes through
rigidity to the zero profile. -/
theorem no_invisible_critical_profile_contradiction_of_compact_projection_surface
    (h : NoInvisibleCriticalProfileCompactProjectionSurface) :
    False :=
  h.obligation.nonzero_profile_contradicts_zero_profile
    h.nonzeroExtractedProfileWitness
    (h.obligation.rigidity_forces_zero_profile
      h.zeroVisibilityRigidityWitness)

/-- Alias with the surface exposed explicitly: strict no-invisible failure plus
zero critical-tail channel visibility is inconsistent with the nonzero compact
profile extracted by compactness and rigidity. -/
theorem no_invisible_critical_profile_of_compact_projection_surface
    (h : NoInvisibleCriticalProfileCompactnessObligation)
    (hFail : h.strictNoInvisibleCriticalProfileFailure)
    (hZeroVisibility : h.zeroCriticalTailVisibility) :
    False :=
  no_invisible_critical_profile_contradiction_of_compact_projection_surface
    (noInvisibleCriticalProfileCompactProjectionSurface h hFail hZeroVisibility)

end ZtareProofs.NS
