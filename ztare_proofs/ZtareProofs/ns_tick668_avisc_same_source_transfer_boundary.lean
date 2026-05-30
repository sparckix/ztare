import ZtareProofs.ns_route1_fresh_frequency_coercivity_adapter
import ZtareProofs.ns_trackb_de_giorgi_vorticity_attack

namespace ZtareProofs

open NSL3MultiscaleYM
open ZtareProofs.NS.DeGiorgiVorticityAttack

namespace Route1FreshFrequencyCoercivity

/-!
TICK668 boundary for the strongest old-observable route.

`LocalizedViscousAlignmentSurplusLevelSetGain` is the most plausible old
non-scalar geometry candidate, but it lives on a Track-B weak-solution /
vorticity-stretching window.  The C7 consumer needs morphology of the exact
invoice-fiber separated fresh-annular source attached to the projected indexed
carrier.  This file states the missing bridge without adding another owner
bridge or accepting vocabulary transfer.
-/

section AViscSameSourceBinding

variable {seq : LerayHopfSequence} {K : CompactSubCylinder}
variable {hRho : RhoFromNormalizedCKNExcess seq K}
variable {hCarrier : NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
variable {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
variable {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
variable {L : NS.EventRecurrencePriceLedger}
variable {hScale : BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta}
variable {hInc : BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L}
variable {hElig :
  ResidualFreshExcessAuditEligibilityData
    (seq := seq) (K := K) (hRho := hRho) (hCarrier := hCarrier)
    (hBeta := hBeta) (hEvents := hEvents) (L := L)}
variable {hGeom : LerayHeatFreshFrequencyEventTentGeometry seq K hRho hCarrier hEvents L}
variable {hPressure : FreshFrequencyPressureTailEventAssignment seq K hRho hCarrier hEvents L}
variable {hDuhamel : FreshFrequencyDuhamelErrorEventAssignment seq K hRho hCarrier hEvents L}
variable {hLock : FreshFrequencyEventSameTreeLock seq K hRho hCarrier hBeta hEvents L hScale hInc}
variable {h : CoronaDuhamelProductionSingleSpendCarrier hElig hGeom hPressure hDuhamel hLock}
variable {routeActiveTail : Nat → Real}
variable {hId :
  C7RouteActiveTailEventBetaSquareIdentification
    (hBeta := hBeta) (hEvents := hEvents) (L := L) routeActiveTail}
variable {hComplete : CoronaDuhamelC7SourceCompletion h hId}
variable {hTransfer :
  C7ScaledOwnerPreimageCarrierTransfer
    (C7SameCarrierPackingNoReuseReceipt.ofCoronaDuhamelC7SourceCompletion
      hComplete)}
variable {nse : NavierStokes.NavierStokesEquations 3}
variable {sol : NavierStokes.WeakSolution nse}

/--
Smaller A_visc theorem target.

This receipt pays only the old-observable source-bound part of the transfer:
the Track-B A_visc level-set window has been bound to the exact C7 projected
carrier, with no proxy substitution.  It deliberately does not include the
total fresh-annular carrier morphology fields.
-/
structure C7AViscSameSourcePushforwardBoundReceipt
    (hTransfer :
      C7ScaledOwnerPreimageCarrierTransfer
        (C7SameCarrierPackingNoReuseReceipt.ofCoronaDuhamelC7SourceCompletion
          hComplete)) where
  avisc : LocalizedViscousAlignmentSurplusLevelSetGain sol
  separatedSource :
    FreshAnnularChargeSeparatedSourceFromIndexedCarrier
      hComplete.scheduleCompletion.projectedCarrier
  route1Route2AnchorToC7Sequence : Prop
  route1Route2AnchorToC7Sequence_proof :
    route1Route2AnchorToC7Sequence
  c7SequenceRepresentsWeakSolutionWindow : Prop
  c7SequenceRepresentsWeakSolutionWindow_proof :
    c7SequenceRepresentsWeakSolutionWindow
  aviscWindowEqualsProjectedCarrier : Prop
  aviscWindowEqualsProjectedCarrier_proof :
    aviscWindowEqualsProjectedCarrier
  levelSetsRestrictedToInvoiceFiberSource : Prop
  levelSetsRestrictedToInvoiceFiberSource_proof :
    levelSetsRestrictedToInvoiceFiberSource
  noProxyCarrierSubstitution : Prop
  noProxyCarrierSubstitution_proof :
    noProxyCarrierSubstitution

/--
Exact source-binding receipt needed before an `A_visc` level-set gain can be
used as fresh-annular non-disguise morphology.

The receipt deliberately separates four jobs:

* relate the Track-B weak-solution window to the Route1/C7 sequence;
* identify the `A_visc` level-set window with the projected indexed carrier;
* rule out proxy-carrier substitution;
* prove morphology of the total fresh-annular separated source.
-/
structure C7AViscLevelSetSameSourceBindingReceipt
    (hTransfer :
      C7ScaledOwnerPreimageCarrierTransfer
        (C7SameCarrierPackingNoReuseReceipt.ofCoronaDuhamelC7SourceCompletion
          hComplete)) where
  avisc :
    LocalizedViscousAlignmentSurplusLevelSetGain sol
  separatedSource :
    FreshAnnularChargeSeparatedSourceFromIndexedCarrier
      hComplete.scheduleCompletion.projectedCarrier
  route1Route2AnchorToC7Sequence : Prop
  route1Route2AnchorToC7Sequence_proof :
    route1Route2AnchorToC7Sequence
  c7SequenceRepresentsWeakSolutionWindow : Prop
  c7SequenceRepresentsWeakSolutionWindow_proof :
    c7SequenceRepresentsWeakSolutionWindow
  aviscWindowEqualsProjectedCarrier : Prop
  aviscWindowEqualsProjectedCarrier_proof :
    aviscWindowEqualsProjectedCarrier
  levelSetsRestrictedToInvoiceFiberSource : Prop
  levelSetsRestrictedToInvoiceFiberSource_proof :
    levelSetsRestrictedToInvoiceFiberSource
  noProxyCarrierSubstitution : Prop
  noProxyCarrierSubstitution_proof :
    noProxyCarrierSubstitution
  totalFreshAnnularCarrierMorphologyProof : Prop
  totalFreshAnnularCarrierMorphologyProof_proof :
    totalFreshAnnularCarrierMorphologyProof
  notMonotoneTailCarrier : Prop
  notMonotoneTailCarrier_proof :
    notMonotoneTailCarrier
  notScalarMeasureCarrier : Prop
  notScalarMeasureCarrier_proof :
    notScalarMeasureCarrier
  notUniformEnstrophyBudgetDisguise : Prop
  notUniformEnstrophyBudgetDisguise_proof :
    notUniformEnstrophyBudgetDisguise

/--
The full A_visc binding receipt has the smaller source-bound theorem as a
projection, but not conversely.
-/
def C7AViscSameSourcePushforwardBoundReceipt.ofAViscLevelSetSameSourceBinding
    (hBind :
      C7AViscLevelSetSameSourceBindingReceipt
        (nse := nse) (sol := sol)
        (hTransfer := hTransfer)) :
    C7AViscSameSourcePushforwardBoundReceipt
      (nse := nse) (sol := sol)
      hTransfer where
  avisc := hBind.avisc
  separatedSource := hBind.separatedSource
  route1Route2AnchorToC7Sequence :=
    hBind.route1Route2AnchorToC7Sequence
  route1Route2AnchorToC7Sequence_proof :=
    hBind.route1Route2AnchorToC7Sequence_proof
  c7SequenceRepresentsWeakSolutionWindow :=
    hBind.c7SequenceRepresentsWeakSolutionWindow
  c7SequenceRepresentsWeakSolutionWindow_proof :=
    hBind.c7SequenceRepresentsWeakSolutionWindow_proof
  aviscWindowEqualsProjectedCarrier :=
    hBind.aviscWindowEqualsProjectedCarrier
  aviscWindowEqualsProjectedCarrier_proof :=
    hBind.aviscWindowEqualsProjectedCarrier_proof
  levelSetsRestrictedToInvoiceFiberSource :=
    hBind.levelSetsRestrictedToInvoiceFiberSource
  levelSetsRestrictedToInvoiceFiberSource_proof :=
    hBind.levelSetsRestrictedToInvoiceFiberSource_proof
  noProxyCarrierSubstitution :=
    hBind.noProxyCarrierSubstitution
  noProxyCarrierSubstitution_proof :=
    hBind.noProxyCarrierSubstitution_proof

/--
Candidate route for turning an A_visc source-bound into actual same-source
morphology.

The intended invariant is a tensor/orientation moment on the exact separated
source that survives the positive-part pushforward.  Without this extra
moment, the scalar A_visc masses can be realized by a monotone scalar tail.
-/
structure C7AViscTensorMomentSameSourceMorphologyReceipt
    (hTransfer :
      C7ScaledOwnerPreimageCarrierTransfer
        (C7SameCarrierPackingNoReuseReceipt.ofCoronaDuhamelC7SourceCompletion
          hComplete)) where
  pushforwardBound :
    C7AViscSameSourcePushforwardBoundReceipt
      (nse := nse) (sol := sol)
      hTransfer
  orientationTensorMomentBoundToTotalCarrier : Prop
  orientationTensorMomentBoundToTotalCarrier_proof :
    orientationTensorMomentBoundToTotalCarrier
  tensorMomentSurvivesPositivePartPushforward : Prop
  tensorMomentSurvivesPositivePartPushforward_proof :
    tensorMomentSurvivesPositivePartPushforward
  tensorMomentForcesTotalFreshAnnularCarrierMorphology : Prop
  tensorMomentForcesTotalFreshAnnularCarrierMorphology_proof :
    tensorMomentForcesTotalFreshAnnularCarrierMorphology
  notMonotoneTailCarrier : Prop
  notMonotoneTailCarrier_proof :
    notMonotoneTailCarrier
  notScalarMeasureCarrier : Prop
  notScalarMeasureCarrier_proof :
    notScalarMeasureCarrier
  notUniformEnstrophyBudgetDisguise : Prop
  notUniformEnstrophyBudgetDisguise_proof :
    notUniformEnstrophyBudgetDisguise

/--
Sharper pre-scalarization repair target.

This receipt carries a marked source law or variance lower bound on the exact
invoice fiber before collapsing to scalar masses.  It is the kind of extra
object needed to defeat the non-injectivity of
`integral (A_visc)_+ |omega|^2`.
-/
structure C7AViscMarkedSourceVarianceReceipt
    (hTransfer :
      C7ScaledOwnerPreimageCarrierTransfer
        (C7SameCarrierPackingNoReuseReceipt.ofCoronaDuhamelC7SourceCompletion
          hComplete)) where
  pushforwardBound :
    C7AViscSameSourcePushforwardBoundReceipt
      (nse := nse) (sol := sol)
      hTransfer
  markedSourceLawOnInvoiceFiber : Prop
  markedSourceLawOnInvoiceFiber_proof :
    markedSourceLawOnInvoiceFiber
  varianceLowerBoundBeforeScalarization : Prop
  varianceLowerBoundBeforeScalarization_proof :
    varianceLowerBoundBeforeScalarization
  markedLawBoundToTotalFreshAnnularCarrier : Prop
  markedLawBoundToTotalFreshAnnularCarrier_proof :
    markedLawBoundToTotalFreshAnnularCarrier
  scalarPushforwardNoninjectivityExcluded : Prop
  scalarPushforwardNoninjectivityExcluded_proof :
    scalarPushforwardNoninjectivityExcluded
  tracelessTensorLawOnInvoiceFiber : Prop
  tracelessTensorLawOnInvoiceFiber_proof :
    tracelessTensorLawOnInvoiceFiber
  tracelessTensorNonCancellation : Prop
  tracelessTensorNonCancellation_proof :
    tracelessTensorNonCancellation
  isotropicOrientationMixtureExcluded : Prop
  isotropicOrientationMixtureExcluded_proof :
    isotropicOrientationMixtureExcluded
  tracelessTensorForcesTotalCarrierMorphology : Prop
  tracelessTensorForcesTotalCarrierMorphology_proof :
    tracelessTensorForcesTotalCarrierMorphology

/--
The marked-source/variance receipt is the admissible way to pay the
tensor-moment morphology receipt only when it also pays a traceless tensor
non-cancellation law.  Scalar marked variance alone is not enough: an
isotropic orientation mixture can preserve the scalar A_visc pushforward while
canceling the tensor moment.
-/
def C7AViscTensorMomentSameSourceMorphologyReceipt.ofMarkedSourceVariance
    (hMarked :
      C7AViscMarkedSourceVarianceReceipt
        (nse := nse) (sol := sol)
        hTransfer)
    (notMonotoneTailCarrier : Prop)
    (notMonotoneTailCarrier_proof : notMonotoneTailCarrier)
    (notScalarMeasureCarrier : Prop)
    (notScalarMeasureCarrier_proof : notScalarMeasureCarrier)
    (notUniformEnstrophyBudgetDisguise : Prop)
    (notUniformEnstrophyBudgetDisguise_proof :
      notUniformEnstrophyBudgetDisguise) :
    C7AViscTensorMomentSameSourceMorphologyReceipt
      (nse := nse) (sol := sol)
      hTransfer where
  pushforwardBound := hMarked.pushforwardBound
  orientationTensorMomentBoundToTotalCarrier :=
    hMarked.tracelessTensorLawOnInvoiceFiber
  orientationTensorMomentBoundToTotalCarrier_proof :=
    hMarked.tracelessTensorLawOnInvoiceFiber_proof
  tensorMomentSurvivesPositivePartPushforward :=
    hMarked.isotropicOrientationMixtureExcluded
  tensorMomentSurvivesPositivePartPushforward_proof :=
    hMarked.isotropicOrientationMixtureExcluded_proof
  tensorMomentForcesTotalFreshAnnularCarrierMorphology :=
    hMarked.tracelessTensorForcesTotalCarrierMorphology
  tensorMomentForcesTotalFreshAnnularCarrierMorphology_proof :=
    hMarked.tracelessTensorForcesTotalCarrierMorphology_proof
  notMonotoneTailCarrier := notMonotoneTailCarrier
  notMonotoneTailCarrier_proof := notMonotoneTailCarrier_proof
  notScalarMeasureCarrier := notScalarMeasureCarrier
  notScalarMeasureCarrier_proof := notScalarMeasureCarrier_proof
  notUniformEnstrophyBudgetDisguise :=
    notUniformEnstrophyBudgetDisguise
  notUniformEnstrophyBudgetDisguise_proof :=
    notUniformEnstrophyBudgetDisguise_proof

/--
A paid tensor-moment morphology theorem upgrades the smaller A_visc
pushforward bound to the full same-source binding receipt.
-/
def C7AViscLevelSetSameSourceBindingReceipt.ofPushforwardAndTensorMoment
    (hTensor :
      C7AViscTensorMomentSameSourceMorphologyReceipt
        (nse := nse) (sol := sol)
        hTransfer) :
    C7AViscLevelSetSameSourceBindingReceipt
      (nse := nse) (sol := sol)
      (hTransfer := hTransfer) where
  avisc := hTensor.pushforwardBound.avisc
  separatedSource := hTensor.pushforwardBound.separatedSource
  route1Route2AnchorToC7Sequence :=
    hTensor.pushforwardBound.route1Route2AnchorToC7Sequence
  route1Route2AnchorToC7Sequence_proof :=
    hTensor.pushforwardBound.route1Route2AnchorToC7Sequence_proof
  c7SequenceRepresentsWeakSolutionWindow :=
    hTensor.pushforwardBound.c7SequenceRepresentsWeakSolutionWindow
  c7SequenceRepresentsWeakSolutionWindow_proof :=
    hTensor.pushforwardBound.c7SequenceRepresentsWeakSolutionWindow_proof
  aviscWindowEqualsProjectedCarrier :=
    hTensor.pushforwardBound.aviscWindowEqualsProjectedCarrier
  aviscWindowEqualsProjectedCarrier_proof :=
    hTensor.pushforwardBound.aviscWindowEqualsProjectedCarrier_proof
  levelSetsRestrictedToInvoiceFiberSource :=
    hTensor.pushforwardBound.levelSetsRestrictedToInvoiceFiberSource
  levelSetsRestrictedToInvoiceFiberSource_proof :=
    hTensor.pushforwardBound.levelSetsRestrictedToInvoiceFiberSource_proof
  noProxyCarrierSubstitution :=
    hTensor.pushforwardBound.noProxyCarrierSubstitution
  noProxyCarrierSubstitution_proof :=
    hTensor.pushforwardBound.noProxyCarrierSubstitution_proof
  totalFreshAnnularCarrierMorphologyProof :=
    hTensor.tensorMomentForcesTotalFreshAnnularCarrierMorphology
  totalFreshAnnularCarrierMorphologyProof_proof :=
    hTensor.tensorMomentForcesTotalFreshAnnularCarrierMorphology_proof
  notMonotoneTailCarrier := hTensor.notMonotoneTailCarrier
  notMonotoneTailCarrier_proof :=
    hTensor.notMonotoneTailCarrier_proof
  notScalarMeasureCarrier := hTensor.notScalarMeasureCarrier
  notScalarMeasureCarrier_proof :=
    hTensor.notScalarMeasureCarrier_proof
  notUniformEnstrophyBudgetDisguise :=
    hTensor.notUniformEnstrophyBudgetDisguise
  notUniformEnstrophyBudgetDisguise_proof :=
    hTensor.notUniformEnstrophyBudgetDisguise_proof

/--
If the `A_visc` binding receipt is actually paid, it is consumed by the
existing same-source morphology transfer surface.
-/
def C7FreshAnnularSameSourceMorphologyTransferReceipt.ofAViscLevelSetSameSourceBinding
    (hBind :
      C7AViscLevelSetSameSourceBindingReceipt
        (nse := nse) (sol := sol)
        (hTransfer := hTransfer)) :
    C7FreshAnnularSameSourceMorphologyTransferReceipt hTransfer where
  separatedSource := hBind.separatedSource
  oldObservableBoundOnThisSeparatedSource :=
    hBind.levelSetsRestrictedToInvoiceFiberSource
  oldObservableBoundOnThisSeparatedSource_proof :=
    hBind.levelSetsRestrictedToInvoiceFiberSource_proof
  observableCarrierIsSeparatedSource :=
    hBind.aviscWindowEqualsProjectedCarrier
  observableCarrierIsSeparatedSource_proof :=
    hBind.aviscWindowEqualsProjectedCarrier_proof
  noProxyCarrierChange :=
    hBind.noProxyCarrierSubstitution
  noProxyCarrierChange_proof :=
    hBind.noProxyCarrierSubstitution_proof
  totalFreshAnnularCarrierMorphologyProof :=
    hBind.totalFreshAnnularCarrierMorphologyProof
  totalFreshAnnularCarrierMorphologyProof_proof :=
    hBind.totalFreshAnnularCarrierMorphologyProof_proof
  notMonotoneTailCarrier := hBind.notMonotoneTailCarrier
  notMonotoneTailCarrier_proof :=
    hBind.notMonotoneTailCarrier_proof
  notScalarMeasureCarrier := hBind.notScalarMeasureCarrier
  notScalarMeasureCarrier_proof :=
    hBind.notScalarMeasureCarrier_proof
  notUniformEnstrophyBudgetDisguise :=
    hBind.notUniformEnstrophyBudgetDisguise
  notUniformEnstrophyBudgetDisguise_proof :=
    hBind.notUniformEnstrophyBudgetDisguise_proof

/--
Confuser for the fake `A_visc` transfer: the Track-B observable and a
Route1/Route2 association exist, but the observable window is not identified
with the C7 projected carrier and no total-carrier morphology proof is paid.
-/
structure C7AViscCarrierBindingMissingConfuser
    (hTransfer :
      C7ScaledOwnerPreimageCarrierTransfer
        (C7SameCarrierPackingNoReuseReceipt.ofCoronaDuhamelC7SourceCompletion
          hComplete)) where
  avisc :
    LocalizedViscousAlignmentSurplusLevelSetGain sol
  separatedSource :
    FreshAnnularChargeSeparatedSourceFromIndexedCarrier
      hComplete.scheduleCompletion.projectedCarrier
  route1Route2AnchorOnly : Prop
  route1Route2AnchorOnly_proof :
    route1Route2AnchorOnly
  c7SequenceRepresentsWeakSolutionWindowOnly : Prop
  c7SequenceRepresentsWeakSolutionWindowOnly_proof :
    c7SequenceRepresentsWeakSolutionWindowOnly
  aviscCarrierMayBeDifferentFromProjectedCarrier : Prop
  aviscCarrierMayBeDifferentFromProjectedCarrier_proof :
    aviscCarrierMayBeDifferentFromProjectedCarrier
  missingTotalFreshAnnularCarrierMorphologyProof : Prop
  missingTotalFreshAnnularCarrierMorphologyProof_proof :
    missingTotalFreshAnnularCarrierMorphologyProof
  noSameSourceAViscBinding :
    ¬ ∃ hBind :
        C7AViscLevelSetSameSourceBindingReceipt
          (nse := nse) (sol := sol)
          (hTransfer := hTransfer),
        hBind.separatedSource = separatedSource
  noSameSourceAViscPushforwardBound :
    ¬ ∃ hBound :
        C7AViscSameSourcePushforwardBoundReceipt
          (nse := nse) (sol := sol)
          hTransfer,
        hBound.separatedSource = separatedSource

/--
Hostile packet for the tensor-moment repair.

Even when the scalar A_visc pushforward is bound to the exact source, an
isotropic orientation mixture can keep the same scalar masses while the
orientation/tensor moment vanishes.  The tensor-moment theorem must exclude
this packet directly.
-/
structure C7AViscTensorMomentIsotropicCancellationConfuser
    (hTransfer :
      C7ScaledOwnerPreimageCarrierTransfer
        (C7SameCarrierPackingNoReuseReceipt.ofCoronaDuhamelC7SourceCompletion
          hComplete)) where
  pushforwardBound :
    C7AViscSameSourcePushforwardBoundReceipt
      (nse := nse) (sol := sol)
      hTransfer
  scalarAViscMassesPreserved : Prop
  scalarAViscMassesPreserved_proof :
    scalarAViscMassesPreserved
  orientationTensorMomentMayVanish : Prop
  orientationTensorMomentMayVanish_proof :
    orientationTensorMomentMayVanish
  totalCarrierMayStillBeScalarMeasure : Prop
  totalCarrierMayStillBeScalarMeasure_proof :
    totalCarrierMayStillBeScalarMeasure
  noSameSourceTensorMomentMorphology :
    ¬ ∃ hTensor :
        C7AViscTensorMomentSameSourceMorphologyReceipt
          (nse := nse) (sol := sol)
          hTransfer,
        hTensor.pushforwardBound.separatedSource =
          pushforwardBound.separatedSource
  noMarkedSourceVariance :
    ¬ ∃ hMarked :
        C7AViscMarkedSourceVarianceReceipt
          (nse := nse) (sol := sol)
          hTransfer,
        hMarked.pushforwardBound.separatedSource =
          pushforwardBound.separatedSource

/--
The fake `A_visc` transfer is blocked at the source-binding receipt itself.
-/
theorem no_C7AViscLevelSetSameSourceBindingReceipt_of_carrierBindingMissingConfuser
    (hConfuser :
      C7AViscCarrierBindingMissingConfuser
        (nse := nse) (sol := sol)
        (hTransfer := hTransfer))
    (hBind :
      C7AViscLevelSetSameSourceBindingReceipt
        (nse := nse) (sol := sol)
        (hTransfer := hTransfer))
    (hSameSource : hBind.separatedSource = hConfuser.separatedSource) :
    False :=
  hConfuser.noSameSourceAViscBinding ⟨hBind, hSameSource⟩

/--
The same carrier-binding confuser also blocks the smaller source-bound theorem.
-/
theorem no_C7AViscSameSourcePushforwardBoundReceipt_of_carrierBindingMissingConfuser
    (hConfuser :
      C7AViscCarrierBindingMissingConfuser
        (nse := nse) (sol := sol)
        (hTransfer := hTransfer))
    (hBound :
      C7AViscSameSourcePushforwardBoundReceipt
        (nse := nse) (sol := sol)
        hTransfer)
    (hSameSource : hBound.separatedSource = hConfuser.separatedSource) :
    False :=
  hConfuser.noSameSourceAViscPushforwardBound ⟨hBound, hSameSource⟩

/--
Scalar A_visc source binding does not imply the tensor-moment morphology
route when the same scalar masses admit isotropic cancellation.
-/
theorem no_C7AViscTensorMomentSameSourceMorphologyReceipt_of_isotropicCancellation
    (hConfuser :
      C7AViscTensorMomentIsotropicCancellationConfuser
        (nse := nse) (sol := sol)
        hTransfer)
    (hTensor :
      C7AViscTensorMomentSameSourceMorphologyReceipt
        (nse := nse) (sol := sol)
        hTransfer)
    (hSameSource :
      hTensor.pushforwardBound.separatedSource =
        hConfuser.pushforwardBound.separatedSource) :
    False :=
  hConfuser.noSameSourceTensorMomentMorphology
    ⟨hTensor, hSameSource⟩

/--
The isotropic-cancellation packet also blocks the sharper marked-source repair.
-/
theorem no_C7AViscMarkedSourceVarianceReceipt_of_isotropicCancellation
    (hConfuser :
      C7AViscTensorMomentIsotropicCancellationConfuser
        (nse := nse) (sol := sol)
        hTransfer)
    (hMarked :
      C7AViscMarkedSourceVarianceReceipt
        (nse := nse) (sol := sol)
        hTransfer)
    (hSameSource :
      hMarked.pushforwardBound.separatedSource =
        hConfuser.pushforwardBound.separatedSource) :
    False :=
  hConfuser.noMarkedSourceVariance ⟨hMarked, hSameSource⟩

end AViscSameSourceBinding

end Route1FreshFrequencyCoercivity
end ZtareProofs
