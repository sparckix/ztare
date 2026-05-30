import Mathlib.Tactic
import ZtareProofs.ns_profile_lipschitz_clay_bridge
import ZtareProofs.ns_self_tax_continuation_bkm_bridge

/-!
# Track B continuation handoff receipt

This file is a guard for the Track B continuation handoff.  It does not add a
new continuation taxonomy.  It records the exact data needed to let the
profile/no-survivor/Lipschitz route and the finite self-tax/enstrophy route
talk about the same evolution.

The load-bearing identity is `critical_iff_enstrophy_control`: the current
self-tax budget pays bounded H1/enstrophy, so a handoff may use generic
`NSEvolution.criticalControl` only after it has been identified with the
enstrophy continuation quantity for the same PDE solution.  The concrete
handoff now carries a same-PDE-solution provenance receipt; continuation or
global-regularity facts may be consequences, not sources, of the identity.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Non-circular source for the observable identities used by a Track B
continuation handoff.

The proposition `same_pde_solution` is the abstract analytic identity that the
two records come from the same PDE solution.  The observable iff fields must be
derived from that identity.  In particular, `globalRegular` and continuation
control may not be used as the source of the handoff identity. -/
structure TrackBContinuationSamePDESolutionIdentity
    (U : NSEvolution)
    (V : SelfTaxNSEvolution) where
  identity_source : SamePDESolutionObservableIdentitySource
  same_pde_solution : Prop
  same_pde_solution_proved : same_pde_solution
  smooth_iff_of_same_pde_solution :
    same_pde_solution →
      (U.smoothOnLocalInterval ↔ V.smoothOnLocalInterval)
  energy_iff_of_same_pde_solution :
    same_pde_solution →
      (U.finiteEnergyInequality ↔ V.finiteEnergyInequality)
  global_regular_iff_of_same_pde_solution :
    same_pde_solution →
      (U.globalRegular ↔ V.globalRegular)
  critical_iff_enstrophy_control_of_same_pde_solution :
    same_pde_solution →
      (U.criticalControl ↔
        V.continuationControl StandardContinuationQuantity.enstrophyBound)

/-- Constructor for the same-PDE-solution identity using the canonical
non-circular provenance source.

The hard analytic work is still explicit: callers must supply the
same-solution proposition, a proof of it, and the induced observable
equivalences.  This constructor only removes the otherwise repetitive source
receipt and makes it impossible to source the identity from continuation or
global regularity. -/
def trackB_continuation_same_pde_solution_identity_of_observable_equivalences
    (U : NSEvolution)
    (V : SelfTaxNSEvolution)
    (same_pde_solution : Prop)
    (same_pde_solution_proved : same_pde_solution)
    (smooth_iff_of_same_pde_solution :
      same_pde_solution →
        (U.smoothOnLocalInterval ↔ V.smoothOnLocalInterval))
    (energy_iff_of_same_pde_solution :
      same_pde_solution →
        (U.finiteEnergyInequality ↔ V.finiteEnergyInequality))
    (global_regular_iff_of_same_pde_solution :
      same_pde_solution →
        (U.globalRegular ↔ V.globalRegular))
    (critical_iff_enstrophy_control_of_same_pde_solution :
      same_pde_solution →
        (U.criticalControl ↔
          V.continuationControl StandardContinuationQuantity.enstrophyBound)) :
    TrackBContinuationSamePDESolutionIdentity U V where
  identity_source := samePDESolutionObservableIdentitySource
  same_pde_solution := same_pde_solution
  same_pde_solution_proved := same_pde_solution_proved
  smooth_iff_of_same_pde_solution := smooth_iff_of_same_pde_solution
  energy_iff_of_same_pde_solution := energy_iff_of_same_pde_solution
  global_regular_iff_of_same_pde_solution :=
    global_regular_iff_of_same_pde_solution
  critical_iff_enstrophy_control_of_same_pde_solution :=
    critical_iff_enstrophy_control_of_same_pde_solution

/-- Shared observable interface between the profile/Lipschitz NSE evolution
and the self-tax continuation evolution.

This is the required anti-overclaim bridge.  A candidate handoff must show that
local smoothness, energy admissibility, global regularity, and the continuation
control are the same observable facts for the two records.  The control clause
is deliberately enstrophy-specific; finite self-tax does not by itself buy a
generic BKM/Serrin/critical-norm route. -/
structure TrackBContinuationSharedEvolution
    (U : NSEvolution)
    (V : SelfTaxNSEvolution) where
  smooth_iff :
    U.smoothOnLocalInterval ↔ V.smoothOnLocalInterval
  energy_iff :
    U.finiteEnergyInequality ↔ V.finiteEnergyInequality
  global_regular_iff :
    U.globalRegular ↔ V.globalRegular
  critical_iff_enstrophy_control :
    U.criticalControl ↔
      V.continuationControl StandardContinuationQuantity.enstrophyBound

/-- Build the same-evolution interface only from a same-PDE-solution identity
receipt. -/
def TrackBContinuationSharedEvolution.of_same_pde_solution_identity
    {U : NSEvolution}
    {V : SelfTaxNSEvolution}
    (I : TrackBContinuationSamePDESolutionIdentity U V) :
    TrackBContinuationSharedEvolution U V where
  smooth_iff :=
    I.smooth_iff_of_same_pde_solution I.same_pde_solution_proved
  energy_iff :=
    I.energy_iff_of_same_pde_solution I.same_pde_solution_proved
  global_regular_iff :=
    I.global_regular_iff_of_same_pde_solution I.same_pde_solution_proved
  critical_iff_enstrophy_control :=
    I.critical_iff_enstrophy_control_of_same_pde_solution
      I.same_pde_solution_proved

/-- Concrete handoff receipt for one initial datum.

The profile/Lipschitz side supplies no-survivor blocks and a Lipschitz reserve.
The self-tax side supplies the branch-local enstrophy continuation criterion.
They can compose only through a same-PDE-solution identity receipt. -/
structure TrackBContinuationHandoffReceipt where
  profile_lipschitz : TrackBProfileLipschitzControlObligation
  self_tax_enstrophy : SelfTaxContinuationEnstrophyBridge
  initialData : SmoothNSInitialData
  same_solution_identity :
    TrackBContinuationSamePDESolutionIdentity
      (profile_lipschitz.evolution_of_initial_data initialData)
      self_tax_enstrophy.evolution

/-- Source-facing constructor for a Track B continuation handoff.

The generated profile/Lipschitz evolution and the self-tax/enstrophy evolution
are connected only through a same-PDE-solution identity.  This constructor
keeps that identity explicit while filling the canonical non-circular
provenance source automatically. -/
def trackB_continuation_handoff_receipt_of_same_pde_solution
    (profile_lipschitz : TrackBProfileLipschitzControlObligation)
    (self_tax_enstrophy : SelfTaxContinuationEnstrophyBridge)
    (initialData : SmoothNSInitialData)
    (same_pde_solution : Prop)
    (same_pde_solution_proved : same_pde_solution)
    (smooth_iff_of_same_pde_solution :
      same_pde_solution →
        ((profile_lipschitz.evolution_of_initial_data
          initialData).smoothOnLocalInterval ↔
            self_tax_enstrophy.evolution.smoothOnLocalInterval))
    (energy_iff_of_same_pde_solution :
      same_pde_solution →
        ((profile_lipschitz.evolution_of_initial_data
          initialData).finiteEnergyInequality ↔
            self_tax_enstrophy.evolution.finiteEnergyInequality))
    (global_regular_iff_of_same_pde_solution :
      same_pde_solution →
        ((profile_lipschitz.evolution_of_initial_data
          initialData).globalRegular ↔
            self_tax_enstrophy.evolution.globalRegular))
    (critical_iff_enstrophy_control_of_same_pde_solution :
      same_pde_solution →
        ((profile_lipschitz.evolution_of_initial_data
          initialData).criticalControl ↔
            self_tax_enstrophy.evolution.continuationControl
              StandardContinuationQuantity.enstrophyBound)) :
    TrackBContinuationHandoffReceipt where
  profile_lipschitz := profile_lipschitz
  self_tax_enstrophy := self_tax_enstrophy
  initialData := initialData
  same_solution_identity :=
    trackB_continuation_same_pde_solution_identity_of_observable_equivalences
      (profile_lipschitz.evolution_of_initial_data initialData)
      self_tax_enstrophy.evolution
      same_pde_solution
      same_pde_solution_proved
      smooth_iff_of_same_pde_solution
      energy_iff_of_same_pde_solution
      global_regular_iff_of_same_pde_solution
      critical_iff_enstrophy_control_of_same_pde_solution

/-- Derived same-evolution interface for existing downstream dot-notation.

The interface is no longer a raw field: it is computed from
`same_solution_identity`, so future instantiations must provide same-PDE-solution
provenance before they can use the observable iff facts. -/
def TrackBContinuationHandoffReceipt.same_evolution
    (H : TrackBContinuationHandoffReceipt) :
    TrackBContinuationSharedEvolution
      (H.profile_lipschitz.evolution_of_initial_data H.initialData)
      H.self_tax_enstrophy.evolution :=
  TrackBContinuationSharedEvolution.of_same_pde_solution_identity
    H.same_solution_identity

/-- Falsifiers for the same-PDE-solution provenance of the handoff identity. -/
inductive TrackBContinuationSamePDEIdentityFalsifier
    {U : NSEvolution}
    {V : SelfTaxNSEvolution}
    (I : TrackBContinuationSamePDESolutionIdentity U V) : Type where
  | missing_same_pde_solution :
      ¬ I.same_pde_solution →
        TrackBContinuationSamePDEIdentityFalsifier I
  | circular_or_unspecified_source :
      ContinuationObservableIdentitySourceFalsifier I.identity_source →
        TrackBContinuationSamePDEIdentityFalsifier I

/-- The same-PDE-solution identity receipt excludes both missing-identity and
circular-source falsifiers. -/
theorem no_trackB_continuation_same_pde_identity_falsifier
    {U : NSEvolution}
    {V : SelfTaxNSEvolution}
    (I : TrackBContinuationSamePDESolutionIdentity U V)
    (F : TrackBContinuationSamePDEIdentityFalsifier I) :
    False := by
  cases F with
  | missing_same_pde_solution hmissing =>
      exact hmissing I.same_pde_solution_proved
  | circular_or_unspecified_source hsource =>
      exact no_continuation_observable_identity_source_falsifier
        I.identity_source
        hsource

/-- Receipt-level provenance falsifier for the concrete handoff object. -/
abbrev TrackBContinuationReceiptIdentityFalsifier
    (H : TrackBContinuationHandoffReceipt) : Type :=
  TrackBContinuationSamePDEIdentityFalsifier H.same_solution_identity

/-- A concrete handoff receipt excludes a circular or missing source for its
observable identity. -/
theorem no_trackB_continuation_receipt_identity_falsifier
    (H : TrackBContinuationHandoffReceipt)
    (F : TrackBContinuationReceiptIdentityFalsifier H) :
    False :=
  no_trackB_continuation_same_pde_identity_falsifier
    H.same_solution_identity
    F

/-- Precise falsifiers for the claim that the profile/Lipschitz evolution and
the self-tax evolution are the same continuation object. -/
inductive TrackBContinuationHandoffFalsifier
    (U : NSEvolution)
    (V : SelfTaxNSEvolution) : Type where
  | profile_smooth_missing_self_tax :
      U.smoothOnLocalInterval →
        ¬ V.smoothOnLocalInterval →
          TrackBContinuationHandoffFalsifier U V
  | self_tax_smooth_missing_profile :
      V.smoothOnLocalInterval →
        ¬ U.smoothOnLocalInterval →
          TrackBContinuationHandoffFalsifier U V
  | profile_energy_missing_self_tax :
      U.finiteEnergyInequality →
        ¬ V.finiteEnergyInequality →
          TrackBContinuationHandoffFalsifier U V
  | self_tax_energy_missing_profile :
      V.finiteEnergyInequality →
        ¬ U.finiteEnergyInequality →
          TrackBContinuationHandoffFalsifier U V
  | profile_regular_missing_self_tax :
      U.globalRegular →
        ¬ V.globalRegular →
          TrackBContinuationHandoffFalsifier U V
  | self_tax_regular_missing_profile :
      V.globalRegular →
        ¬ U.globalRegular →
          TrackBContinuationHandoffFalsifier U V
  | profile_critical_missing_self_tax_enstrophy :
      U.criticalControl →
        ¬ V.continuationControl StandardContinuationQuantity.enstrophyBound →
          TrackBContinuationHandoffFalsifier U V
  | self_tax_enstrophy_missing_profile_critical :
      V.continuationControl StandardContinuationQuantity.enstrophyBound →
        ¬ U.criticalControl →
          TrackBContinuationHandoffFalsifier U V

/-- A valid shared-evolution handoff rules out every declared mismatch. -/
theorem no_trackB_continuation_handoff_falsifier_of_shared_evolution
    {U : NSEvolution}
    {V : SelfTaxNSEvolution}
    (S : TrackBContinuationSharedEvolution U V)
    (F : TrackBContinuationHandoffFalsifier U V) :
    False := by
  cases F with
  | profile_smooth_missing_self_tax hprofile hself =>
      exact hself (S.smooth_iff.mp hprofile)
  | self_tax_smooth_missing_profile hself hprofile =>
      exact hprofile (S.smooth_iff.mpr hself)
  | profile_energy_missing_self_tax hprofile hself =>
      exact hself (S.energy_iff.mp hprofile)
  | self_tax_energy_missing_profile hself hprofile =>
      exact hprofile (S.energy_iff.mpr hself)
  | profile_regular_missing_self_tax hprofile hself =>
      exact hself (S.global_regular_iff.mp hprofile)
  | self_tax_regular_missing_profile hself hprofile =>
      exact hprofile (S.global_regular_iff.mpr hself)
  | profile_critical_missing_self_tax_enstrophy hprofile hself =>
      exact hself (S.critical_iff_enstrophy_control.mp hprofile)
  | self_tax_enstrophy_missing_profile_critical hself hprofile =>
      exact hprofile (S.critical_iff_enstrophy_control.mpr hself)

/-- Receipt-level mismatch falsifier for the concrete handoff object. -/
abbrev TrackBContinuationReceiptFalsifier
    (H : TrackBContinuationHandoffReceipt) : Type :=
  TrackBContinuationHandoffFalsifier
    (H.profile_lipschitz.evolution_of_initial_data H.initialData)
    H.self_tax_enstrophy.evolution

/-- A concrete handoff receipt excludes a concrete mismatch between its two
evolution records. -/
theorem no_trackB_continuation_receipt_falsifier
    (H : TrackBContinuationHandoffReceipt)
    (F : TrackBContinuationReceiptFalsifier H) :
    False :=
  no_trackB_continuation_handoff_falsifier_of_shared_evolution
    H.same_evolution
    F

/-- Finite self-tax pays enstrophy control, and a valid handoff converts that
specific enstrophy control into the profile/Lipschitz evolution's declared
continuation control. -/
theorem profile_critical_control_of_self_tax_enstrophy_handoff
    (H : TrackBContinuationHandoffReceipt) :
    (H.profile_lipschitz.evolution_of_initial_data H.initialData).criticalControl := by
  have hbound :
      HasEnstrophyBound
        H.self_tax_enstrophy.absorption
        H.self_tax_enstrophy.selfTaxBudget :=
    enstrophy_bound_of_self_tax_enstrophy_bridge
      H.self_tax_enstrophy
  have hcontrol :
      H.self_tax_enstrophy.evolution.continuationControl
        StandardContinuationQuantity.enstrophyBound :=
    H.self_tax_enstrophy.enstrophy_continuation.bound_to_enstrophy_control
      H.self_tax_enstrophy.evolution
      H.self_tax_enstrophy.absorption
      H.self_tax_enstrophy.selfTaxBudget
      hbound
  exact H.same_evolution.critical_iff_enstrophy_control.mpr hcontrol

/-- Profile decomposition plus Lipschitz reserve pays the same enstrophy
continuation control on the self-tax evolution, provided the two sides share
the evolution through the handoff receipt. -/
theorem self_tax_enstrophy_control_of_profile_lipschitz_handoff
    (H : TrackBContinuationHandoffReceipt) :
    H.self_tax_enstrophy.evolution.continuationControl
      StandardContinuationQuantity.enstrophyBound := by
  let O := H.profile_lipschitz
  let U := O.evolution_of_initial_data H.initialData
  have hcritical : U.criticalControl :=
    critical_control_of_trackB_profile_lipschitz_closure
      O H.initialData
  exact H.same_evolution.critical_iff_enstrophy_control.mp hcritical

/-- The concrete handoff identifies profile-side and self-tax-side global
regularity as the same PDE observable.

This named endpoint keeps final Clay/GP216 composition from reusing
continuation as the source of the identity: the equivalence is projected from
`same_solution_identity` through `same_evolution`. -/
theorem profile_global_regular_iff_self_tax_global_regular_of_handoff
    (H : TrackBContinuationHandoffReceipt) :
    (H.profile_lipschitz.evolution_of_initial_data
      H.initialData).globalRegular ↔
        H.self_tax_enstrophy.evolution.globalRegular :=
  H.same_evolution.global_regular_iff

/-- The concrete handoff identifies profile-side critical control with the
enstrophy continuation control actually paid by the self-tax branch. -/
theorem profile_critical_iff_self_tax_enstrophy_control_of_handoff
    (H : TrackBContinuationHandoffReceipt) :
    (H.profile_lipschitz.evolution_of_initial_data
      H.initialData).criticalControl ↔
        H.self_tax_enstrophy.evolution.continuationControl
          StandardContinuationQuantity.enstrophyBound :=
  H.same_evolution.critical_iff_enstrophy_control

/-- No-survivor/profile + Lipschitz control can close through the self-tax
branch only when the handoff identifies the generated evolution with the
enstrophy continuation evolution. -/
theorem global_regular_of_profile_lipschitz_handoff_to_self_tax_enstrophy
    (H : TrackBContinuationHandoffReceipt)
    (hsmooth :
      (H.profile_lipschitz.evolution_of_initial_data
        H.initialData).smoothOnLocalInterval)
    (henergy :
      (H.profile_lipschitz.evolution_of_initial_data
        H.initialData).finiteEnergyInequality) :
    H.self_tax_enstrophy.evolution.globalRegular := by
  have hcontrol :
      H.self_tax_enstrophy.evolution.continuationControl
        StandardContinuationQuantity.enstrophyBound :=
    self_tax_enstrophy_control_of_profile_lipschitz_handoff H
  exact
    H.self_tax_enstrophy.enstrophy_continuation.continues_from_enstrophy
      H.self_tax_enstrophy.evolution
      (H.same_evolution.smooth_iff.mp hsmooth)
      (H.same_evolution.energy_iff.mp henergy)
      hcontrol

/-- Profile-side global regularity obtained through the enstrophy handoff, not
through an uninstantiated generic continuation placeholder. -/
theorem global_regular_of_profile_lipschitz_enstrophy_handoff
    (H : TrackBContinuationHandoffReceipt)
    (hsmooth :
      (H.profile_lipschitz.evolution_of_initial_data
        H.initialData).smoothOnLocalInterval)
    (henergy :
      (H.profile_lipschitz.evolution_of_initial_data
        H.initialData).finiteEnergyInequality) :
    (H.profile_lipschitz.evolution_of_initial_data H.initialData).globalRegular := by
  have hself :
      H.self_tax_enstrophy.evolution.globalRegular :=
    global_regular_of_profile_lipschitz_handoff_to_self_tax_enstrophy
      H
      hsmooth
      henergy
  exact H.same_evolution.global_regular_iff.mpr hself

/-- Self-tax/enstrophy continuation transfers back to the profile/Lipschitz
evolution only through the declared same-evolution handoff. -/
theorem global_regular_of_self_tax_enstrophy_handoff_to_profile_lipschitz
    (H : TrackBContinuationHandoffReceipt)
    (hsmooth : H.self_tax_enstrophy.evolution.smoothOnLocalInterval)
    (henergy : H.self_tax_enstrophy.evolution.finiteEnergyInequality) :
    (H.profile_lipschitz.evolution_of_initial_data H.initialData).globalRegular := by
  have hself :
      H.self_tax_enstrophy.evolution.globalRegular :=
    global_regular_of_self_tax_and_enstrophy_continuation
      H.self_tax_enstrophy
      hsmooth
      henergy
  exact H.same_evolution.global_regular_iff.mpr hself

end

end ZtareProofs.NS
