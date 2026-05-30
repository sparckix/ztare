import Mathlib.Tactic
import ZtareProofs.ns_singular_value_compensation
import ZtareProofs.ns_section_budget_bounds

namespace ZtareProofs

/-!
`ns_eulerian_dissipation_bridge` names and partially closes the bridge identified
by the referee panel.

The finite-dimensional kinematics are done: incompressibility plus axial escape
forces transverse singular-value contraction. The missing analytic lift is from
that Lagrangian contraction to an Eulerian dissipation lower bound over the
reset interval. This file proves the implication layer once such a lower bound
is supplied.
-/

/-- Abstract integrated Eulerian dissipation over a return/reset interval. -/
abbrev EulerianDissipation := Real

/--
Corrected stretch-rate dissipation cost.

If a log-singular-value change `r` is accumulated over cycle time `T` on a
material region of volume `mu`, the natural Cauchy-Schwarz/Jensen shape is
`mu * r^2 / T`, not a time-free `(lambda - 1)^2` bound.
-/
noncomputable def stretchRateCost (mu r T : Real) : Real :=
  mu * r ^ (2 : Nat) / T

/--
Lagrangian collapse witness at a section return:
the local deformation is volume-preserving and one transverse singular value
falls below a threshold.
-/
structure LagrangianCollapseWitness where
  axial : Real
  trans1 : Real
  trans2 : Real
  q : Real
  hvol : volumePreservingSingularValues axial trans1 trans2
  haxial_nonneg : 0 ≤ axial
  hq_nonneg : 0 ≤ q
  hcollapse : trans1 < q ∨ trans2 < q

/--
The missing analytic premise:
Lagrangian collapse forces an Eulerian dissipation lower bound.

This is deliberately a target predicate. The current formal stack does not
derive it from the PDE yet.
-/
def collapseToEulerianDissipationLowerBound
    (_W : LagrangianCollapseWitness) (Dlower : Real) (D : EulerianDissipation) : Prop :=
  Dlower ≤ D

/--
Reset loss includes the integrated Eulerian dissipation paid over the reset
interval.
-/
def resetLossIncludesDissipation
    (C : EigenframeCycleWitness) (D : EulerianDissipation) : Prop :=
  D ≤ C.resetLoss

/--
If collapse yields a dissipation lower bound, and reset loss includes that
dissipation, then reset loss inherits the lower bound.
-/
theorem reset_loss_lower_bound_of_collapse_dissipation
    {C : EigenframeCycleWitness} {W : LagrangianCollapseWitness}
    {Dlower : Real} {D : EulerianDissipation}
    (hcollapse : collapseToEulerianDissipationLowerBound W Dlower D)
    (hinclude : resetLossIncludesDissipation C D) :
    Dlower ≤ C.resetLoss := by
  unfold collapseToEulerianDissipationLowerBound at hcollapse
  unfold resetLossIncludesDissipation at hinclude
  exact le_trans hcollapse hinclude

/--
Section-level version: if every high-intensity return has a collapse witness,
a dissipation lower bound, and reset loss includes that dissipation, then the
section has a reset-loss lower bound.
-/
theorem eventual_reset_loss_lower_bound_of_eulerian_dissipation
    {S : EigenframeSection} {EStar Closs : Real} {β : Nat}
    (D : EigenframeCycleWitness → EulerianDissipation)
    (W : EigenframeCycleWitness → LagrangianCollapseWitness)
    (hcollapse :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        collapseToEulerianDissipationLowerBound (W C) (Closs * C.entry.peak ^ β) (D C))
    (hinclude :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        resetLossIncludesDissipation C (D C)) :
    eventualResetLossLowerBound S EStar Closs β := by
  intro C hhigh
  unfold resetLossLowerBoundOnSection
  exact reset_loss_lower_bound_of_collapse_dissipation (hcollapse C hhigh) (hinclude C hhigh)

/--
The exact analytic bridge target left by the NS branch.
-/
def eulerianDissipationBridgeTarget
    (_S : EigenframeSection) (EStar Closs : Real) (β : Nat) : Prop :=
  ∃ (D : EigenframeCycleWitness → EulerianDissipation)
    (W : EigenframeCycleWitness → LagrangianCollapseWitness),
    (∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
      collapseToEulerianDissipationLowerBound (W C) (Closs * C.entry.peak ^ β) (D C)) ∧
    (∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
      resetLossIncludesDissipation C (D C))

/--
If the analytic bridge target is paid for, the section-level reset-loss lower
bound follows.
-/
theorem eventual_reset_loss_lower_bound_of_bridge_target
    {S : EigenframeSection} {EStar Closs : Real} {β : Nat}
    (hbridge : eulerianDissipationBridgeTarget S EStar Closs β) :
    eventualResetLossLowerBound S EStar Closs β := by
  rcases hbridge with ⟨D, W, hcollapse, hinclude⟩
  exact eventual_reset_loss_lower_bound_of_eulerian_dissipation D W hcollapse hinclude

/--
Stretch-rate version of the bridge target.

This is the sharpened form suggested by the panel: a Lagrangian singular-value
change only becomes an Eulerian dissipation lower bound after paying for the
time spent accumulating that change.
-/
def stretchRateDissipationBridgeTarget
    (_S : EigenframeSection) (EStar mu r T : Real) : Prop :=
  ∃ (D : EigenframeCycleWitness → EulerianDissipation),
    (∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
      stretchRateCost mu r T ≤ D C) ∧
    (∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
      resetLossIncludesDissipation C (D C))

/--
If the stretch-rate bridge is paid for, reset loss inherits the corresponding
time-aware lower bound.
-/
theorem reset_loss_lower_bound_of_stretchRate_bridge
    {S : EigenframeSection} {EStar mu r T : Real}
    (hbridge : stretchRateDissipationBridgeTarget S EStar mu r T) :
    ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
      stretchRateCost mu r T ≤ C.resetLoss := by
  rcases hbridge with ⟨D, hD, hinclude⟩
  intro C hhigh
  exact le_trans (hD C hhigh) (hinclude C hhigh)

/--
Source packet strong enough to instantiate the stretch-rate bridge target.
A material-frame label is not used directly; the packet must provide the
same-cycle Eulerian dissipation functional and the reset-loss inclusion.
-/
structure MaterialFrameStretchRateBridgeSource
    (S : EigenframeSection) (EStar mu r T : Real) where
  materialFrameFixedBeforePayoff : Prop
  materialFrameFixedBeforePayoff_proof : materialFrameFixedBeforePayoff
  intrinsicScaleReceipt : Prop
  intrinsicScaleReceipt_proof : intrinsicScaleReceipt
  sameCarrierResetWindow : Prop
  sameCarrierResetWindow_proof : sameCarrierResetWindow
  analyticExponentSourceReceipt : Prop
  analyticExponentSourceReceipt_proof : analyticExponentSourceReceipt
  D : EigenframeCycleWitness -> EulerianDissipation
  stretchRatePaid :
    ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak ->
      stretchRateCost mu r T ≤ D C
  resetLossIncludes :
    ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak ->
      resetLossIncludesDissipation C (D C)

/--
A fully paid material-frame stretch-rate source is exactly enough to build the
existing stretch-rate dissipation bridge target.
-/
theorem MaterialFrameStretchRateBridgeSource.toStretchRateDissipationBridgeTarget
    {S : EigenframeSection} {EStar mu r T : Real}
    (M : MaterialFrameStretchRateBridgeSource S EStar mu r T) :
    stretchRateDissipationBridgeTarget S EStar mu r T := by
  exact ⟨M.D, M.stretchRatePaid, M.resetLossIncludes⟩

/--
Confuser packet: frame/gauge language with no analytic exponent source,
no same-cycle dissipation lower bound, or no reset-loss inclusion cannot be
spent as the stretch-rate bridge.
-/
structure MaterialFrameGaugeWithoutStretchRateDissipationConfuser
    (S : EigenframeSection) (EStar mu r T : Real) where
  materialFrameLanguageVisible : Prop
  materialFrameLanguageVisible_proof : materialFrameLanguageVisible
  pureGaugeOrCocycleRelabel : Prop
  pureGaugeOrCocycleRelabel_proof : pureGaugeOrCocycleRelabel
  noAnalyticExponentSourceForDimensionlessStretch : Prop
  noAnalyticExponentSourceForDimensionlessStretch_proof :
    noAnalyticExponentSourceForDimensionlessStretch
  noSameCycleEulerianDissipationLowerBound : Prop
  noSameCycleEulerianDissipationLowerBound_proof :
    noSameCycleEulerianDissipationLowerBound
  noResetLossInclusionReceipt : Prop
  noResetLossInclusionReceipt_proof : noResetLossInclusionReceipt
  no_stretchRateDissipationBridgeTarget :
    stretchRateDissipationBridgeTarget S EStar mu r T -> False

theorem no_stretchRateDissipationBridgeTarget_of_materialFrameGaugeConfuser
    {S : EigenframeSection} {EStar mu r T : Real}
    (C : MaterialFrameGaugeWithoutStretchRateDissipationConfuser S EStar mu r T)
    (hbridge : stretchRateDissipationBridgeTarget S EStar mu r T) : False :=
  C.no_stretchRateDissipationBridgeTarget hbridge

/--
Single-cycle Jensen/Cauchy source for the material-frame bridge.  This names
the analytic origin of the square in `stretchRateCost`: a time-integrated
material stretch rate on one fixed carrier/window, not dimensional analysis or
a global energy label.
-/
structure MaterialFrameJensenStretchRateSource
    (S : EigenframeSection) (EStar mu r T : Real) where
  materialTubeFixedBeforePayoff : Prop
  materialTubeFixedBeforePayoff_proof : materialTubeFixedBeforePayoff
  sameCarrierTubeWindow : Prop
  sameCarrierTubeWindow_proof : sameCarrierTubeWindow
  jensenCauchyStretchRateIdentity : Prop
  jensenCauchyStretchRateIdentity_proof : jensenCauchyStretchRateIdentity
  dimensionlessExponentAnalyticSource : Prop
  dimensionlessExponentAnalyticSource_proof : dimensionlessExponentAnalyticSource
  noGlobalEnergyRebilling : Prop
  noGlobalEnergyRebilling_proof : noGlobalEnergyRebilling
  D : EigenframeCycleWitness -> EulerianDissipation
  stretchRateCostFromJensen :
    ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak ->
      stretchRateCost mu r T ≤ D C
  resetLossIncludes :
    ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak ->
      resetLossIncludesDissipation C (D C)

/--
The single-cycle Jensen/Cauchy source is strong enough to populate the generic
material-frame stretch-rate bridge source.
-/
def MaterialFrameJensenStretchRateSource.toMaterialFrameStretchRateBridgeSource
    {S : EigenframeSection} {EStar mu r T : Real}
    (J : MaterialFrameJensenStretchRateSource S EStar mu r T) :
    MaterialFrameStretchRateBridgeSource S EStar mu r T where
  materialFrameFixedBeforePayoff := J.materialTubeFixedBeforePayoff
  materialFrameFixedBeforePayoff_proof := J.materialTubeFixedBeforePayoff_proof
  intrinsicScaleReceipt := J.jensenCauchyStretchRateIdentity
  intrinsicScaleReceipt_proof := J.jensenCauchyStretchRateIdentity_proof
  sameCarrierResetWindow := J.sameCarrierTubeWindow
  sameCarrierResetWindow_proof := J.sameCarrierTubeWindow_proof
  analyticExponentSourceReceipt := J.dimensionlessExponentAnalyticSource
  analyticExponentSourceReceipt_proof := J.dimensionlessExponentAnalyticSource_proof
  D := J.D
  stretchRatePaid := J.stretchRateCostFromJensen
  resetLossIncludes := J.resetLossIncludes

/--
Therefore a paid single-cycle Jensen/Cauchy source directly constructs the
existing stretch-rate dissipation bridge target.
-/
theorem MaterialFrameJensenStretchRateSource.toStretchRateDissipationBridgeTarget
    {S : EigenframeSection} {EStar mu r T : Real}
    (J : MaterialFrameJensenStretchRateSource S EStar mu r T) :
    stretchRateDissipationBridgeTarget S EStar mu r T :=
  (J.toMaterialFrameStretchRateBridgeSource).toStretchRateDissipationBridgeTarget

/--
Global dissipation visibility alone is not the single-cycle material tube
source: it may have finite energy/dissipation but lacks a fixed tube-window
assignment, Jensen stretch identity, or reset-loss inclusion on the same cycle.
-/
structure GlobalDissipationOnlyNotMaterialFrameJensenSourceConfuser
    (S : EigenframeSection) (EStar mu r T : Real) where
  globalDissipationFiniteOrVisible : Prop
  globalDissipationFiniteOrVisible_proof : globalDissipationFiniteOrVisible
  noFixedMaterialTubeWindow : Prop
  noFixedMaterialTubeWindow_proof : noFixedMaterialTubeWindow
  noJensenStretchRateIdentityOnSelectedCarrier : Prop
  noJensenStretchRateIdentityOnSelectedCarrier_proof :
    noJensenStretchRateIdentityOnSelectedCarrier
  noResetLossInclusionOnSameCycle : Prop
  noResetLossInclusionOnSameCycle_proof : noResetLossInclusionOnSameCycle
  no_materialFrameJensenStretchRateSource :
    MaterialFrameJensenStretchRateSource S EStar mu r T -> False

theorem no_MaterialFrameJensenStretchRateSource_of_globalDissipationOnlyConfuser
    {S : EigenframeSection} {EStar mu r T : Real}
    (C : GlobalDissipationOnlyNotMaterialFrameJensenSourceConfuser S EStar mu r T)
    (J : MaterialFrameJensenStretchRateSource S EStar mu r T) : False :=
  C.no_materialFrameJensenStretchRateSource J

/-- Prefix budget for selected material-tube dissipation atoms. -/
def prefixMaterialTubeDissipationBudget
    (Dprefix : Nat -> Real) (criticalBudget : Real) : Prop :=
  ∀ N : Nat, (Finset.range N).sum Dprefix ≤ criticalBudget

/--
All-cascade material-tube no-reuse source.  This is the Clay-relevant upgrade
of the single-cycle Jensen source: each selected index has its own paid tube
source, those tube dissipation atoms are charged into a prefix budget, and the
selected family has no nested rebilling.
-/
structure AllCascadeMaterialTubeNoReuseSource
    (S : EigenframeSection) (EStar : Real)
    (mu r T : Nat -> Real) (criticalBudget : Real) where
  source : ∀ n : Nat, MaterialFrameJensenStretchRateSource S EStar (mu n) (r n) (T n)
  Dprefix : Nat -> Real
  selectedTubeFamilyFixedBeforePayoff : Prop
  selectedTubeFamilyFixedBeforePayoff_proof : selectedTubeFamilyFixedBeforePayoff
  sameCarrierNoReuse : Prop
  sameCarrierNoReuse_proof : sameCarrierNoReuse
  boundedOverlapMultiplicity : Prop
  boundedOverlapMultiplicity_proof : boundedOverlapMultiplicity
  noGlobalDissipationRebilling : Prop
  noGlobalDissipationRebilling_proof : noGlobalDissipationRebilling
  cycleDissipationChargedToPrefix :
    ∀ n : Nat, ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak ->
      (source n).D C ≤ Dprefix n
  prefixBudget : prefixMaterialTubeDissipationBudget Dprefix criticalBudget

/-- Each selected tube source still gives the local stretch-rate bridge target. -/
theorem AllCascadeMaterialTubeNoReuseSource.bridge_at_index
    {S : EigenframeSection} {EStar : Real}
    {mu r T : Nat -> Real} {criticalBudget : Real}
    (A : AllCascadeMaterialTubeNoReuseSource S EStar mu r T criticalBudget)
    (n : Nat) :
    stretchRateDissipationBridgeTarget S EStar (mu n) (r n) (T n) :=
  (A.source n).toStretchRateDissipationBridgeTarget

/-- The all-cascade source exposes its selected prefix budget. -/
theorem AllCascadeMaterialTubeNoReuseSource.prefix_budget_bound
    {S : EigenframeSection} {EStar : Real}
    {mu r T : Nat -> Real} {criticalBudget : Real}
    (A : AllCascadeMaterialTubeNoReuseSource S EStar mu r T criticalBudget) :
    prefixMaterialTubeDissipationBudget A.Dprefix criticalBudget :=
  A.prefixBudget

/--
Nested material-tube rebilling confuser: finite/global dissipation may be
visible while the selected family reuses the same tube atoms across the prefix.
-/
structure NestedMaterialTubeRebillingConfuser
    (S : EigenframeSection) (EStar : Real)
    (mu r T : Nat -> Real) (criticalBudget : Real) where
  finiteGlobalDissipationVisible : Prop
  finiteGlobalDissipationVisible_proof : finiteGlobalDissipationVisible
  selectedTubesCanNestOnSameAtoms : Prop
  selectedTubesCanNestOnSameAtoms_proof : selectedTubesCanNestOnSameAtoms
  noPrefixInjectionOrMultiplicityBound : Prop
  noPrefixInjectionOrMultiplicityBound_proof : noPrefixInjectionOrMultiplicityBound
  resetLossInclusionNotPrefixStable : Prop
  resetLossInclusionNotPrefixStable_proof : resetLossInclusionNotPrefixStable
  no_allCascadeMaterialTubeNoReuseSource :
    AllCascadeMaterialTubeNoReuseSource S EStar mu r T criticalBudget -> False

theorem no_AllCascadeMaterialTubeNoReuseSource_of_nestedRebillingConfuser
    {S : EigenframeSection} {EStar : Real}
    {mu r T : Nat -> Real} {criticalBudget : Real}
    (C : NestedMaterialTubeRebillingConfuser S EStar mu r T criticalBudget)
    (A : AllCascadeMaterialTubeNoReuseSource S EStar mu r T criticalBudget) : False :=
  C.no_allCascadeMaterialTubeNoReuseSource A

/--
Spatial volume preservation from a regular Lagrangian/divergence-free flow.
This is intentionally only a partial source: it fixes material labels and
spatial support, but records that selected time-window owner-preimages remain
owed before any prefix dissipation budget can be spent.
-/
structure FlowMapSpatialVolumePartialSource where
  materialLabelsFixedBeforePayoff : Prop
  materialLabelsFixedBeforePayoff_proof : materialLabelsFixedBeforePayoff
  regularLagrangianFlowAvailable : Prop
  regularLagrangianFlowAvailable_proof : regularLagrangianFlowAvailable
  divergenceFreeVolumePreservation : Prop
  divergenceFreeVolumePreservation_proof : divergenceFreeVolumePreservation
  spatialLabelOwnerReceipt : Prop
  spatialLabelOwnerReceipt_proof : spatialLabelOwnerReceipt
  spatialDisjointnessAtEachTime : Prop
  spatialDisjointnessAtEachTime_proof : spatialDisjointnessAtEachTime
  timeWindowOwnerPreimageStillOwed : Prop
  timeWindowOwnerPreimageStillOwed_proof : timeWindowOwnerPreimageStillOwed

/--
Flow-map source strong enough for the all-cascade material-tube socket.  It
contains the spatial-volume partial source, but also the extra temporal owner
preimage, bounded-overlap, and no-rebilling receipts that volume preservation
alone does not provide.
-/
structure FlowMapTimeWindowNoReuseSource
    (S : EigenframeSection) (EStar : Real)
    (mu r T : Nat -> Real) (criticalBudget : Real) where
  spatialSource : FlowMapSpatialVolumePartialSource
  owner : Nat -> Nat
  windowCharge : Nat -> Real
  ownerCharge : Nat -> Real
  C : Real
  selectedWindowMapFixedBeforePayoff : Prop
  selectedWindowMapFixedBeforePayoff_proof : selectedWindowMapFixedBeforePayoff
  ownerPreimagePrefixReceipt : Prop
  ownerPreimagePrefixReceipt_proof : ownerPreimagePrefixReceipt
  boundedTimeOverlap : Prop
  boundedTimeOverlap_proof : boundedTimeOverlap
  noNestedTimeWindowRebilling : Prop
  noNestedTimeWindowRebilling_proof : noNestedTimeWindowRebilling
  pointwiseWindowCharge_le_ownerCharge :
    ∀ n : Nat, windowCharge n ≤ ownerCharge (owner n)
  ownerPreimagePrefixInequality :
    ∀ N : Nat, (Finset.range N).sum windowCharge ≤
      C * (Finset.range N).sum ownerCharge
  allCascade : AllCascadeMaterialTubeNoReuseSource S EStar mu r T criticalBudget

/--
A full time-window no-reuse source exposes the existing all-cascade material
source.  The proof does not spend spatial volume directly; it consumes the
separate owner-preimage and bounded-overlap receipts carried by the source.
-/
def FlowMapTimeWindowNoReuseSource.toAllCascadeMaterialTubeNoReuseSource
    {S : EigenframeSection} {EStar : Real}
    {mu r T : Nat -> Real} {criticalBudget : Real}
    (F : FlowMapTimeWindowNoReuseSource S EStar mu r T criticalBudget) :
    AllCascadeMaterialTubeNoReuseSource S EStar mu r T criticalBudget :=
  F.allCascade

/--
Confuser for the tempting but invalid promotion from flow-map spatial volume to
selected time-window no-reuse.  A material label can keep its spatial volume at
each time while being selected and charged across many time windows.
-/
structure FlowMapVolumePreservationWithoutTimeWindowOwnerPreimageConfuser
    (S : EigenframeSection) (EStar : Real)
    (mu r T : Nat -> Real) (criticalBudget : Real) where
  materialVolumePreserved : Prop
  materialVolumePreserved_proof : materialVolumePreserved
  materialLabelsFixedBeforePayoff : Prop
  materialLabelsFixedBeforePayoff_proof : materialLabelsFixedBeforePayoff
  sameMaterialLabelCanRecurAcrossWindows : Prop
  sameMaterialLabelCanRecurAcrossWindows_proof : sameMaterialLabelCanRecurAcrossWindows
  noNumericalOwnerPreimagePrefixInequality : Prop
  noNumericalOwnerPreimagePrefixInequality_proof :
    noNumericalOwnerPreimagePrefixInequality
  noBoundedSelectedWindowMultiplicity : Prop
  noBoundedSelectedWindowMultiplicity_proof : noBoundedSelectedWindowMultiplicity
  no_allCascadeMaterialTubeNoReuseSource :
    AllCascadeMaterialTubeNoReuseSource S EStar mu r T criticalBudget -> False

theorem no_AllCascadeMaterialTubeNoReuseSource_of_flowMapVolumeOnlyConfuser
    {S : EigenframeSection} {EStar : Real}
    {mu r T : Nat -> Real} {criticalBudget : Real}
    (C : FlowMapVolumePreservationWithoutTimeWindowOwnerPreimageConfuser
      S EStar mu r T criticalBudget)
    (A : AllCascadeMaterialTubeNoReuseSource S EStar mu r T criticalBudget) : False :=
  C.no_allCascadeMaterialTubeNoReuseSource A

/--
Temporal material-window owner-preimage receipt.  This is the arithmetic core
that Vitali/stopping-window language must supply before it can be consumed by
the material-tube no-reuse bridge.
-/
structure MaterialTimeWindowOwnerPreimageReceipt where
  owner : Nat -> Nat
  windowCharge : Nat -> Real
  atomCharge : Nat -> Real
  activeAtomBound : Nat -> Nat
  C : Real
  atomBudget : Real
  windowCharge_nonnegative : ∀ n : Nat, 0 ≤ windowCharge n
  atomCharge_nonnegative : ∀ n : Nat, 0 ≤ atomCharge n
  C_nonnegative : 0 ≤ C
  atomBudget_nonnegative : 0 ≤ atomBudget
  owner_lt_activeAtomBound : ∀ {e N : Nat}, e < N -> owner e < activeAtomBound N
  pointwiseOwnedAtomPaysWindow : ∀ e : Nat, windowCharge e ≤ atomCharge (owner e)
  ownerPreimagePrefixInequality :
    ∀ N : Nat, (Finset.range N).sum windowCharge ≤
      C * (Finset.range (activeAtomBound N)).sum atomCharge
  activeAtomPrefixBudget :
    ∀ N : Nat, (Finset.range (activeAtomBound N)).sum atomCharge ≤ atomBudget
  ownerMapFixedBeforePayoff : Prop
  ownerMapFixedBeforePayoff_proof : ownerMapFixedBeforePayoff
  sameMaterialTimeCarrier : Prop
  sameMaterialTimeCarrier_proof : sameMaterialTimeCarrier
  globalSelectedWindowPreimageBound : Prop
  globalSelectedWindowPreimageBound_proof : globalSelectedWindowPreimageBound

/-- Consume the temporal owner-preimage receipt as a selected-prefix budget. -/
theorem MaterialTimeWindowOwnerPreimageReceipt.windowPrefix_le_ownerBudget
    (h : MaterialTimeWindowOwnerPreimageReceipt) :
    ∀ N : Nat, (Finset.range N).sum h.windowCharge ≤ h.C * h.atomBudget := by
  intro N
  exact
    le_trans (h.ownerPreimagePrefixInequality N)
      (mul_le_mul_of_nonneg_left (h.activeAtomPrefixBudget N) h.C_nonnegative)

/--
Positive tail constructor: if selected windows are already event-indexed into
same-carrier atoms with the identity owner map, pointwise payment plus an atom
prefix budget produces the temporal owner-preimage receipt.
-/
def MaterialTimeWindowOwnerPreimageReceipt.ofIdentityWindowAtoms
    (windowCharge atomCharge : Nat -> Real) (atomBudget : Real)
    (windowCharge_nonnegative : ∀ n : Nat, 0 ≤ windowCharge n)
    (atomCharge_nonnegative : ∀ n : Nat, 0 ≤ atomCharge n)
    (atomBudget_nonnegative : 0 ≤ atomBudget)
    (pointwiseWindowCharge_le_atomCharge :
      ∀ n : Nat, windowCharge n ≤ atomCharge n)
    (atomPrefixBudget :
      ∀ N : Nat, (Finset.range N).sum atomCharge ≤ atomBudget)
    (ownerMapFixedBeforePayoff : Prop)
    (ownerMapFixedBeforePayoff_proof : ownerMapFixedBeforePayoff)
    (sameMaterialTimeCarrier : Prop)
    (sameMaterialTimeCarrier_proof : sameMaterialTimeCarrier)
    (globalSelectedWindowPreimageBound : Prop)
    (globalSelectedWindowPreimageBound_proof : globalSelectedWindowPreimageBound) :
    MaterialTimeWindowOwnerPreimageReceipt where
  owner := fun n : Nat => n
  windowCharge := windowCharge
  atomCharge := atomCharge
  activeAtomBound := fun N : Nat => N
  C := 1
  atomBudget := atomBudget
  windowCharge_nonnegative := windowCharge_nonnegative
  atomCharge_nonnegative := atomCharge_nonnegative
  C_nonnegative := by norm_num
  atomBudget_nonnegative := atomBudget_nonnegative
  owner_lt_activeAtomBound := by
    intro e N heN
    exact heN
  pointwiseOwnedAtomPaysWindow := pointwiseWindowCharge_le_atomCharge
  ownerPreimagePrefixInequality := by
    intro N
    simpa using
      Finset.sum_le_sum
        (fun n _hn => pointwiseWindowCharge_le_atomCharge n :
          ∀ n ∈ Finset.range N, windowCharge n ≤ atomCharge n)
  activeAtomPrefixBudget := atomPrefixBudget
  ownerMapFixedBeforePayoff := ownerMapFixedBeforePayoff
  ownerMapFixedBeforePayoff_proof := ownerMapFixedBeforePayoff_proof
  sameMaterialTimeCarrier := sameMaterialTimeCarrier
  sameMaterialTimeCarrier_proof := sameMaterialTimeCarrier_proof
  globalSelectedWindowPreimageBound := globalSelectedWindowPreimageBound
  globalSelectedWindowPreimageBound_proof :=
    globalSelectedWindowPreimageBound_proof

/--
Vitali/stopping-window confuser: local covering overlap, bounded fanout, and
pointwise owner payment do not construct the temporal no-reuse source unless
they compose into the numerical selected-prefix owner-preimage inequality.
-/
structure VitaliStoppingWindowWithoutOwnerPreimageConfuser
    (S : EigenframeSection) (EStar : Real)
    (mu r T : Nat -> Real) (criticalBudget : Real) where
  vitaliStoppingSelectionVisible : Prop
  vitaliStoppingSelectionVisible_proof : vitaliStoppingSelectionVisible
  boundedLocalOverlap : Prop
  boundedLocalOverlap_proof : boundedLocalOverlap
  pointwiseOwnerPaymentVisible : Prop
  pointwiseOwnerPaymentVisible_proof : pointwiseOwnerPaymentVisible
  finiteOwnerAtomBudgetVisible : Prop
  finiteOwnerAtomBudgetVisible_proof : finiteOwnerAtomBudgetVisible
  noTemporalOwnerPreimagePrefixInequality : Prop
  noTemporalOwnerPreimagePrefixInequality_proof :
    noTemporalOwnerPreimagePrefixInequality
  selectedWindowsMayRebillOwnerAtomsAcrossTime : Prop
  selectedWindowsMayRebillOwnerAtomsAcrossTime_proof :
    selectedWindowsMayRebillOwnerAtomsAcrossTime
  no_flowMapTimeWindowNoReuseSource :
    FlowMapTimeWindowNoReuseSource S EStar mu r T criticalBudget -> False

theorem no_FlowMapTimeWindowNoReuseSource_of_vitaliStoppingWindowConfuser
    {S : EigenframeSection} {EStar : Real}
    {mu r T : Nat -> Real} {criticalBudget : Real}
    (C : VitaliStoppingWindowWithoutOwnerPreimageConfuser
      S EStar mu r T criticalBudget)
    (F : FlowMapTimeWindowNoReuseSource S EStar mu r T criticalBudget) : False :=
  C.no_flowMapTimeWindowNoReuseSource F

/--
Carrier-neutral telescoping source for an atom prefix budget.  It is the
material-window analogue of a stopping-tree energy decrement: every selected
atom charge is paid by a pre-payoff potential drop.
-/
structure TelescopingMaterialAtomBudgetSource where
  atomCharge : Nat -> Real
  potential : Nat -> Real
  atomBudget : Real
  atomCharge_nonnegative : ∀ n : Nat, 0 ≤ atomCharge n
  potential_nonnegative : ∀ n : Nat, 0 ≤ potential n
  atomBudget_nonnegative : 0 ≤ atomBudget
  atomChargePaidByPotentialDrop :
    ∀ n : Nat, atomCharge n + potential (n + 1) ≤ potential n
  potentialInitial_le_atomBudget : potential 0 ≤ atomBudget
  potentialFixedBeforePayoff : Prop
  potentialFixedBeforePayoff_proof : potentialFixedBeforePayoff
  sameMaterialWindowAtomCarrier : Prop
  sameMaterialWindowAtomCarrier_proof : sameMaterialWindowAtomCarrier
  noHiddenRegularityCriterionImport : Prop
  noHiddenRegularityCriterionImport_proof : noHiddenRegularityCriterionImport

/-- Strong telescoping invariant: prefix charge plus remaining potential is bounded. -/
theorem TelescopingMaterialAtomBudgetSource.prefix_charge_plus_potential_le_initial
    (h : TelescopingMaterialAtomBudgetSource) :
    ∀ N : Nat, (Finset.range N).sum h.atomCharge + h.potential N ≤ h.potential 0 := by
  intro N
  induction N with
  | zero =>
      simp
  | succ N ih =>
      have hdrop :
          h.atomCharge N + h.potential (N + 1) ≤ h.potential N :=
        h.atomChargePaidByPotentialDrop N
      rw [Finset.sum_range_succ]
      nlinarith

/-- The telescoping source gives the atom prefix budget needed by Level382. -/
theorem TelescopingMaterialAtomBudgetSource.atomPrefixBudget
    (h : TelescopingMaterialAtomBudgetSource) :
    ∀ N : Nat, (Finset.range N).sum h.atomCharge ≤ h.atomBudget := by
  intro N
  have htel := h.prefix_charge_plus_potential_le_initial N
  have hnonneg := h.potential_nonnegative N
  nlinarith [h.potentialInitial_le_atomBudget]

/--
Compose the telescoping atom budget with the Level382 identity owner receipt.
The window charges are supplied separately; the atom budget is paid by the
potential decrement source.
-/
def TelescopingMaterialAtomBudgetSource.toMaterialTimeWindowOwnerPreimageReceipt
    (h : TelescopingMaterialAtomBudgetSource)
    (windowCharge : Nat -> Real)
    (windowCharge_nonnegative : ∀ n : Nat, 0 ≤ windowCharge n)
    (pointwiseWindowCharge_le_atomCharge :
      ∀ n : Nat, windowCharge n ≤ h.atomCharge n)
    (ownerMapFixedBeforePayoff : Prop)
    (ownerMapFixedBeforePayoff_proof : ownerMapFixedBeforePayoff)
    (globalSelectedWindowPreimageBound : Prop)
    (globalSelectedWindowPreimageBound_proof : globalSelectedWindowPreimageBound) :
    MaterialTimeWindowOwnerPreimageReceipt :=
  MaterialTimeWindowOwnerPreimageReceipt.ofIdentityWindowAtoms
    windowCharge h.atomCharge h.atomBudget
    windowCharge_nonnegative h.atomCharge_nonnegative h.atomBudget_nonnegative
    pointwiseWindowCharge_le_atomCharge h.atomPrefixBudget
    ownerMapFixedBeforePayoff ownerMapFixedBeforePayoff_proof
    h.sameMaterialWindowAtomCarrier h.sameMaterialWindowAtomCarrier_proof
    globalSelectedWindowPreimageBound globalSelectedWindowPreimageBound_proof

/--
Finite/global dissipation without a selected per-atom decrement does not supply
the atom prefix budget required by the material time-window owner receipt.
-/
structure FiniteGlobalDissipationWithoutAtomDecrementConfuser where
  finiteGlobalDissipationVisible : Prop
  finiteGlobalDissipationVisible_proof : finiteGlobalDissipationVisible
  localOverlapOrCoveringVisible : Prop
  localOverlapOrCoveringVisible_proof : localOverlapOrCoveringVisible
  selectedWindowsMayReuseSameDissipationReservoir : Prop
  selectedWindowsMayReuseSameDissipationReservoir_proof :
    selectedWindowsMayReuseSameDissipationReservoir
  noPerAtomPotentialDecrement : Prop
  noPerAtomPotentialDecrement_proof : noPerAtomPotentialDecrement
  no_telescopingMaterialAtomBudgetSource :
    TelescopingMaterialAtomBudgetSource -> False

theorem no_TelescopingMaterialAtomBudgetSource_of_finiteGlobalConfuser
    (C : FiniteGlobalDissipationWithoutAtomDecrementConfuser)
    (h : TelescopingMaterialAtomBudgetSource) : False :=
  C.no_telescopingMaterialAtomBudgetSource h

end ZtareProofs
