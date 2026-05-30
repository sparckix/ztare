import Mathlib.Tactic
import ZtareProofs.ns_leray_gain_tax_trackb_obligation

/-!
# Leray self-tax to continuation bridge target

This file is a receipt, not a Navier-Stokes regularity proof.

`ns_leray_gain_tax_trackb_obligation.lean` proves the sharp scalar absorption
step: after the viscous channel is paid, enstrophy growth is bounded by a
finite Leray self-tax integral.  The purpose of this file is to keep the next
Clay-level step honest:

* finite self-tax gives an abstract enstrophy bound;
* this branch's direct continuation quantity is bounded H1/enstrophy, not a
  generic BKM/Serrin/critical-norm placeholder;
* a Clay continuation conclusion still needs the separately declared standard
  bridge "bounded enstrophy implies no blowup" for strong 3D NSE;
* that standard bridge is not smuggled into the self-tax receipt.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Continuation quantities that may appear in nearby proof branches.

For the finite Leray self-tax branch, the paid quantity is
`enstrophyBound`.  The other tags are retained only to make overclaims
visible: this file does not derive BKM, Serrin, or a generic critical norm
from the projected-forcing budget. -/
inductive StandardContinuationQuantity where
  | enstrophyBound
  | bkmVorticityLinfTimeIntegral
  | criticalNormBound
deriving DecidableEq, Repr

/-- Provenance tag for an observable-identity handoff.

Continuation/global-regularity facts may be consequences of a handoff, but
they are not valid sources for identifying two continuation records.  A
non-circular handoff must source the identity from the same PDE solution. -/
inductive ContinuationObservableIdentitySource where
  | samePDESolution
  | continuationOrGlobalRegular
  | unspecified
deriving DecidableEq, Repr

/-- Receipt that an observable-identity handoff is sourced from a same-PDE
solution identity, rather than from continuation or global regularity. -/
structure SamePDESolutionObservableIdentitySource where
  source : ContinuationObservableIdentitySource
  source_is_same_pde_solution :
    source = ContinuationObservableIdentitySource.samePDESolution

/-- Canonical non-circular observable-identity provenance source.

Use this when the handoff is sourced from an actual same-PDE-solution identity.
It deliberately does not mention continuation or global regularity, so it
cannot be used to backfit an observable equivalence from the conclusion. -/
def samePDESolutionObservableIdentitySource :
    SamePDESolutionObservableIdentitySource where
  source := ContinuationObservableIdentitySource.samePDESolution
  source_is_same_pde_solution := rfl

/-- Falsifiers for the provenance of an observable-identity handoff. -/
inductive ContinuationObservableIdentitySourceFalsifier
    (S : SamePDESolutionObservableIdentitySource) : Type where
  | sourced_from_continuation_or_global_regular :
      S.source =
        ContinuationObservableIdentitySource.continuationOrGlobalRegular →
        ContinuationObservableIdentitySourceFalsifier S
  | source_unspecified :
      S.source = ContinuationObservableIdentitySource.unspecified →
        ContinuationObservableIdentitySourceFalsifier S

/-- A same-PDE-solution source receipt excludes the circular provenance
falsifiers. -/
theorem no_continuation_observable_identity_source_falsifier
    (S : SamePDESolutionObservableIdentitySource)
    (F : ContinuationObservableIdentitySourceFalsifier S) :
    False := by
  cases F with
  | sourced_from_continuation_or_global_regular hsource =>
      rw [S.source_is_same_pde_solution] at hsource
      cases hsource
  | source_unspecified hsource =>
      rw [S.source_is_same_pde_solution] at hsource
      cases hsource

/-- Abstract evolution state for the continuation receipt.

The propositions stand in for the analytic function-space construction.  The
receipt only composes already declared estimates and continuation theorems. -/
structure SelfTaxNSEvolution where
  smoothOnLocalInterval : Prop
  finiteEnergyInequality : Prop
  continuationControl : StandardContinuationQuantity → Prop
  globalRegular : Prop

/-- The bounded-enstrophy conclusion produced by finite Leray self-tax. -/
def HasEnstrophyBound
    (R : VorticityDualPriceTimeAbsorptionReceipt)
    (budget : Real) : Prop :=
  R.finalEnstrophy ≤ R.initialEnstrophy + budget

/-- The scalar layer only: finite self-tax controls enstrophy in the abstract
time-integrated receipt.  This is not yet a Clay continuation statement. -/
theorem finite_self_tax_controls_enstrophy
    (R : VorticityDualPriceTimeAbsorptionReceipt)
    {budget : Real}
    (hbudget : R.selfTaxCoeff * R.selfTaxIntegral ≤ budget) :
    HasEnstrophyBound R budget := by
  exact enstrophy_bound_of_self_tax_budget R hbudget

/-- The local-to-global version of the same scalar layer.

The hard PDE input is the fixed-topology local-to-global self-tax receipt.
Once supplied, the conclusion is still only an enstrophy bound. -/
theorem local_to_global_self_tax_controls_enstrophy
    (R : VorticityDualPriceTimeAbsorptionReceipt)
    (G : SelfTaxIntegralLocalToGlobalReceipt)
    (hmatch : R.selfTaxIntegral = G.selfTaxIntegral) :
    HasEnstrophyBound R (R.selfTaxCoeff * G.totalBudget) := by
  exact enstrophy_bound_of_local_to_global_self_tax_budget R G hmatch

/-- A standard continuation criterion, kept separate from the self-tax bound.

`bound_to_control` is the analytic bridge from a bounded-enstrophy receipt to
the chosen standard continuation quantity.  For the self-tax branch, this
should be instantiated with `quantity = enstrophyBound`; using another tag is a
different proof route and must pay an additional conversion theorem. -/
structure SelfTaxStandardContinuationCriterion where
  quantity : StandardContinuationQuantity
  bound_to_control :
    ∀ (U : SelfTaxNSEvolution)
      (R : VorticityDualPriceTimeAbsorptionReceipt)
      (budget : Real),
      HasEnstrophyBound R budget →
        U.continuationControl quantity
  continues :
    ∀ U : SelfTaxNSEvolution,
      U.smoothOnLocalInterval →
        U.finiteEnergyInequality →
          U.continuationControl quantity →
            U.globalRegular

/-- The continuation criterion directly paid by finite projected self-tax.

This is the preferred final handoff for the current Track B spine: finite
`∫ ||P((u · ∇)u)||₂²` gives bounded enstrophy, and bounded enstrophy is the
standard strong-solution continuation control. -/
structure SelfTaxEnstrophyContinuationCriterion where
  bound_to_enstrophy_control :
    ∀ (U : SelfTaxNSEvolution)
      (R : VorticityDualPriceTimeAbsorptionReceipt)
      (budget : Real),
      HasEnstrophyBound R budget →
        U.continuationControl StandardContinuationQuantity.enstrophyBound
  continues_from_enstrophy :
    ∀ U : SelfTaxNSEvolution,
      U.smoothOnLocalInterval →
        U.finiteEnergyInequality →
          U.continuationControl StandardContinuationQuantity.enstrophyBound →
            U.globalRegular

/-- Full continuation bridge obligation.

The data explicitly separates the self-tax estimate from the standard
continuation theorem.  A candidate that supplies only `finite_self_tax_budget`
has proved an enstrophy bound, not Clay continuation. -/
structure SelfTaxContinuationBKMBridge where
  evolution : SelfTaxNSEvolution
  absorption : VorticityDualPriceTimeAbsorptionReceipt
  selfTaxBudget : Real
  finite_self_tax_budget :
    absorption.selfTaxCoeff * absorption.selfTaxIntegral ≤ selfTaxBudget
  standard_continuation : SelfTaxStandardContinuationCriterion

/-- Specialized self-tax continuation bridge using the direct enstrophy handoff.

Use this for Track B unless an additional theorem converts the self-tax budget
to a different standard continuation quantity. -/
structure SelfTaxContinuationEnstrophyBridge where
  evolution : SelfTaxNSEvolution
  absorption : VorticityDualPriceTimeAbsorptionReceipt
  selfTaxBudget : Real
  finite_self_tax_budget :
    absorption.selfTaxCoeff * absorption.selfTaxIntegral ≤ selfTaxBudget
  enstrophy_continuation : SelfTaxEnstrophyContinuationCriterion

/-- Finite self-tax gives the bridge's advertised enstrophy bound. -/
theorem enstrophy_bound_of_self_tax_continuation_bridge
    (B : SelfTaxContinuationBKMBridge) :
    HasEnstrophyBound B.absorption B.selfTaxBudget := by
  exact finite_self_tax_controls_enstrophy
    B.absorption
    B.finite_self_tax_budget

/-- Finite self-tax gives the specialized bridge's enstrophy bound. -/
theorem enstrophy_bound_of_self_tax_enstrophy_bridge
    (B : SelfTaxContinuationEnstrophyBridge) :
    HasEnstrophyBound B.absorption B.selfTaxBudget := by
  exact finite_self_tax_controls_enstrophy
    B.absorption
    B.finite_self_tax_budget

/-- Conditional continuation theorem.

This is the intended target receipt: finite Leray self-tax can be connected to
Clay continuation only after a standard continuation criterion is separately
declared and instantiated. -/
theorem global_regular_of_self_tax_and_standard_continuation
    (B : SelfTaxContinuationBKMBridge)
    (hsmooth : B.evolution.smoothOnLocalInterval)
    (henergy : B.evolution.finiteEnergyInequality) :
    B.evolution.globalRegular := by
  have hbound : HasEnstrophyBound B.absorption B.selfTaxBudget :=
    enstrophy_bound_of_self_tax_continuation_bridge B
  have hcontrol :
      B.evolution.continuationControl B.standard_continuation.quantity :=
    B.standard_continuation.bound_to_control
      B.evolution
      B.absorption
      B.selfTaxBudget
      hbound
  exact B.standard_continuation.continues
    B.evolution
    hsmooth
    henergy
    hcontrol

/-- Conditional continuation theorem through the direct H1/enstrophy route.

This is the branch-local theorem to cite when the only paid analytic budget is
finite projected self-tax. -/
theorem global_regular_of_self_tax_and_enstrophy_continuation
    (B : SelfTaxContinuationEnstrophyBridge)
    (hsmooth : B.evolution.smoothOnLocalInterval)
    (henergy : B.evolution.finiteEnergyInequality) :
    B.evolution.globalRegular := by
  have hbound : HasEnstrophyBound B.absorption B.selfTaxBudget :=
    enstrophy_bound_of_self_tax_enstrophy_bridge B
  have hcontrol :
      B.evolution.continuationControl
        StandardContinuationQuantity.enstrophyBound :=
    B.enstrophy_continuation.bound_to_enstrophy_control
      B.evolution
      B.absorption
      B.selfTaxBudget
      hbound
  exact B.enstrophy_continuation.continues_from_enstrophy
    B.evolution
    hsmooth
    henergy
    hcontrol

/-- Local-to-global variant of the bridge, using a fixed topology self-tax
gluing receipt before invoking the standard continuation theorem. -/
structure LocalToGlobalSelfTaxContinuationBKMBridge where
  evolution : SelfTaxNSEvolution
  absorption : VorticityDualPriceTimeAbsorptionReceipt
  local_to_global : SelfTaxIntegralLocalToGlobalReceipt
  self_tax_matches :
    absorption.selfTaxIntegral = local_to_global.selfTaxIntegral
  standard_continuation : SelfTaxStandardContinuationCriterion

/-- Local-to-global variant with the direct H1/enstrophy continuation handoff. -/
structure LocalToGlobalSelfTaxContinuationEnstrophyBridge where
  evolution : SelfTaxNSEvolution
  absorption : VorticityDualPriceTimeAbsorptionReceipt
  local_to_global : SelfTaxIntegralLocalToGlobalReceipt
  self_tax_matches :
    absorption.selfTaxIntegral = local_to_global.selfTaxIntegral
  enstrophy_continuation : SelfTaxEnstrophyContinuationCriterion

/-- Local-to-global self-tax control plus a separately declared continuation
criterion yields the abstract global-regularity conclusion. -/
theorem global_regular_of_local_to_global_self_tax_and_standard_continuation
    (B : LocalToGlobalSelfTaxContinuationBKMBridge)
    (hsmooth : B.evolution.smoothOnLocalInterval)
    (henergy : B.evolution.finiteEnergyInequality) :
    B.evolution.globalRegular := by
  let budget := B.absorption.selfTaxCoeff * B.local_to_global.totalBudget
  have hbound : HasEnstrophyBound B.absorption budget :=
    local_to_global_self_tax_controls_enstrophy
      B.absorption
      B.local_to_global
      B.self_tax_matches
  have hcontrol :
      B.evolution.continuationControl B.standard_continuation.quantity :=
    B.standard_continuation.bound_to_control
      B.evolution
      B.absorption
      budget
      hbound
  exact B.standard_continuation.continues
    B.evolution
    hsmooth
    henergy
    hcontrol

/-- Local-to-global self-tax control plus the direct H1/enstrophy continuation
criterion yields the abstract global-regularity conclusion. -/
theorem global_regular_of_local_to_global_self_tax_and_enstrophy_continuation
    (B : LocalToGlobalSelfTaxContinuationEnstrophyBridge)
    (hsmooth : B.evolution.smoothOnLocalInterval)
    (henergy : B.evolution.finiteEnergyInequality) :
    B.evolution.globalRegular := by
  let budget := B.absorption.selfTaxCoeff * B.local_to_global.totalBudget
  have hbound : HasEnstrophyBound B.absorption budget :=
    local_to_global_self_tax_controls_enstrophy
      B.absorption
      B.local_to_global
      B.self_tax_matches
  have hcontrol :
      B.evolution.continuationControl
        StandardContinuationQuantity.enstrophyBound :=
    B.enstrophy_continuation.bound_to_enstrophy_control
      B.evolution
      B.absorption
      budget
      hbound
  exact B.enstrophy_continuation.continues_from_enstrophy
    B.evolution
    hsmooth
    henergy
    hcontrol

/-- Anti-overclaim checklist for the continuation target. -/
structure SelfTaxContinuationOpenObligations where
  finite_leray_self_tax_integral : Prop
  fixed_topology_self_tax_gluing : Prop
  enstrophy_bound_extracted : Prop
  h1_enstrophy_continuation_criterion_instantiated : Prop
  no_blowup_conclusion_uses_standard_criterion : Prop

end

end ZtareProofs.NS
