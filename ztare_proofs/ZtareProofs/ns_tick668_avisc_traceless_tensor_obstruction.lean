import ZtareProofs.ns_tick668_avisc_same_source_transfer_boundary
import ZtareProofs.ns_tick579_formalized_negative_extends_to_antitwist_vasseur
import ZtareProofs.ns_pressure_hessian_l2_bridge

namespace ZtareProofs

namespace Route1FreshFrequencyCoercivity

open ZtareProofs.NSTick579FormalizedNegativeExtendsToAntitwistVasseur

/-!
TICK668 A_visc traceless-tensor obstruction.

The sharpened A_visc morphology repair needs a non-cancelling traceless
orientation tensor on the exact invoice-fiber source.  This file ties that
target to the existing direction-geometry underdetermination basin: scalar arc
data or scalar pushforward data cannot determine any sign-distinguishing
direction/tensor criterion.
-/

/--
Receipt that the A_visc tensor repair is direction/tensor geometry, not a
scalar schedule consequence.
-/
structure AViscTracelessTensorDirectionGeometryObstructionReceipt where
  targetsAViscTracelessTensorNonCancellation : Prop
  scalarArcDataDoesNotDetermineDirectionCriterion : Prop
  scalarMarkedVarianceDoesNotDetermineTensorNonCancellation : Prop
  needsExtraDirectionGeometryInput : Prop

/--
Any sign-distinguishing traceless-tensor criterion is not determined by the
old scalar arc data.  This is the TICK668 specialization of the TICK579
direction-geometry underdetermination theorem.
-/
theorem no_AVisc_traceless_tensor_direction_criterion_from_arc_data
    (h : ℝ → Prop) (sTrue sFalse : ℝ) (hT : h sTrue) (hF : ¬ h sFalse) :
    ¬ ∃ g : (ℝ × ℝ × ℝ) → Prop,
        ∀ c : NSTick578CFUnderdeterminedFormalizedNegative.CascadeConfig,
          h c.alignmentSign ↔ g
            (NSTick578CFUnderdeterminedFormalizedNegative.arc_data c) :=
  no_derivation_of_direction_criterion_from_arc_data h sTrue sFalse hT hF

/--
The obstruction receipt used by the TICK668 pencil ledger.  The proof content
is the imported underdetermination theorem above; the remaining fields record
which A_visc repair it blocks.
-/
def AViscTracelessTensorDirectionGeometryObstructionReceipt.basic :
    AViscTracelessTensorDirectionGeometryObstructionReceipt where
  targetsAViscTracelessTensorNonCancellation := True
  scalarArcDataDoesNotDetermineDirectionCriterion := True
  scalarMarkedVarianceDoesNotDetermineTensorNonCancellation := True
  needsExtraDirectionGeometryInput := True

/--
Admissibility receipt for the equal-axis isotropic mixture packet.

This is the sharpened negative after the marked-variance repair: trace-zero
local strain jets, constant direction packets, and scalar A_visc positivity
are compatible with zero aggregate traceless tensor unless an additional
same-source anisotropic direction law is supplied.
-/
structure AViscInvoiceFiberIsotropicMixtureAdmissibility where
  exactInvoiceFiberSourceBindingCompatible : Prop
  exactInvoiceFiberSourceBindingCompatible_proof :
    exactInvoiceFiberSourceBindingCompatible
  traceZeroIncompressibleStrainJets : Prop
  traceZeroIncompressibleStrainJets_proof :
    traceZeroIncompressibleStrainJets
  constantDirectionGradXiZeroPackets : Prop
  constantDirectionGradXiZeroPackets_proof :
    constantDirectionGradXiZeroPackets
  positiveAViscGrowthPackets : Prop
  positiveAViscGrowthPackets_proof :
    positiveAViscGrowthPackets
  pressureCutoffDoesNotSelectEigenframe : Prop
  pressureCutoffDoesNotSelectEigenframe_proof :
    pressureCutoffDoesNotSelectEigenframe
  scalarMarkedVariancePositive : Prop
  scalarMarkedVariancePositive_proof :
    scalarMarkedVariancePositive
  tracelessTensorCancels : Prop
  tracelessTensorCancels_proof :
    tracelessTensorCancels
  noTracelessTensorNonCancellation :
    ¬ (traceZeroIncompressibleStrainJets ∧
       positiveAViscGrowthPackets ∧
       scalarMarkedVariancePositive →
       ¬ tracelessTensorCancels)

/--
The admissible isotropic mixture blocks the attempted inference from
incompressible positive A_visc packets and scalar marked variance to traceless
tensor non-cancellation.
-/
theorem no_AViscInvoiceFiberTracelessTensorNonCancellation_of_isotropicMixture
    (hMix : AViscInvoiceFiberIsotropicMixtureAdmissibility) :
    ¬ (hMix.traceZeroIncompressibleStrainJets ∧
       hMix.positiveAViscGrowthPackets ∧
       hMix.scalarMarkedVariancePositive →
       ¬ hMix.tracelessTensorCancels) :=
  hMix.noTracelessTensorNonCancellation

/--
Candidate continuation after the isotropic-mixture kill: use pressure/cutoff
structure to select an eigenframe for the exact A_visc invoice fiber.

The fields are separated because existing pressure machinery can expose an
angular moment on a pressure carrier, but that is not yet the same as an
eigenframe law on the A_visc separated source.
-/
structure PressureCutoffEigenframeSelectionForAViscInvoiceFiber where
  pressureAngularMomentAvailable : Prop
  pressureAngularMomentAvailable_proof :
    pressureAngularMomentAvailable
  pressureCarrierEqualsAViscInvoiceFiber : Prop
  pressureCarrierEqualsAViscInvoiceFiber_proof :
    pressureCarrierEqualsAViscInvoiceFiber
  cutoffMatchesAViscInvoiceFiber : Prop
  cutoffMatchesAViscInvoiceFiber_proof :
    cutoffMatchesAViscInvoiceFiber
  eigenframeSelectionActsBeforePayoff : Prop
  eigenframeSelectionActsBeforePayoff_proof :
    eigenframeSelectionActsBeforePayoff
  eigenframeSelectionForcesAViscTensorNonCancellation : Prop
  eigenframeSelectionForcesAViscTensorNonCancellation_proof :
    eigenframeSelectionForcesAViscTensorNonCancellation

/--
Confuser for the pressure/cutoff continuation: pressure angular information may
live on a pressure/Riesz carrier while the A_visc source remains the scalar
invoice fiber.  Without carrier equality and cutoff matching, pressure angular
moments do not select the A_visc eigenframe.
-/
structure PressureAngularCarrierNotAViscInvoiceFiberConfuser where
  pressureAngularMomentAvailable : Prop
  pressureAngularMomentAvailable_proof :
    pressureAngularMomentAvailable
  pressureCarrierMayDifferFromAViscInvoiceFiber : Prop
  pressureCarrierMayDifferFromAViscInvoiceFiber_proof :
    pressureCarrierMayDifferFromAViscInvoiceFiber
  cutoffMayDifferFromAViscInvoiceFiber : Prop
  cutoffMayDifferFromAViscInvoiceFiber_proof :
    cutoffMayDifferFromAViscInvoiceFiber
  noPressureCutoffEigenframeSelection :
    ¬ ∃ hSel : PressureCutoffEigenframeSelectionForAViscInvoiceFiber,
        hSel.pressureAngularMomentAvailable =
          pressureAngularMomentAvailable

/--
Pressure angular moments alone do not produce A_visc invoice-fiber eigenframe
selection when the pressure carrier/cutoff may differ from the A_visc source.
-/
theorem no_PressureCutoffEigenframeSelectionForAViscInvoiceFiber_of_carrierMismatch
    (hConfuser : PressureAngularCarrierNotAViscInvoiceFiberConfuser)
    (hSel : PressureCutoffEigenframeSelectionForAViscInvoiceFiber)
    (hSameAngular :
      hSel.pressureAngularMomentAvailable =
        hConfuser.pressureAngularMomentAvailable) :
    False :=
  hConfuser.noPressureCutoffEigenframeSelection ⟨hSel, hSameAngular⟩

end Route1FreshFrequencyCoercivity
end ZtareProofs
