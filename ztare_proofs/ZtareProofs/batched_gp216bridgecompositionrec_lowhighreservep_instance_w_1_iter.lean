import ZtareProofs.ns_gp216_bridge_composition_receipt

namespace ZtareProofs.NS

noncomputable def gp216_bridge_composition_receipt_instance_2
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate : LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource : GP216ContinuumAllOutputSourceBundle selfTaxOutputSource.stream eventRecurrenceSource.ledger)
    (coordinateReformulation : TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branch_is_global : IsGlobalTrackBBlock (GP216GeneratedProfileLipschitzBranch continuationSource.handoff.profile_lipschitz continuationSource.handoff.initialData profileLipschitzBranchIndex))
    (lowHighReservePDESource : GP216LowHighReservePDESourceBundle continuationSource.handoff)
    : GP216BridgeCompositionReceipt := by
  exact gp216_bridge_composition_receipt_of_generated_branch
    declaredScope
    highHighSelfTaxPDESource
    selfTaxOutputSource
    coherenceSource
    coherenceCertificate
    lowBeatEnvelopeSource
    eventRecurrenceSource
    continuumSource
    coordinateReformulation
    continuationSource
    profileLipschitzBranchIndex
    branch_is_global
    lowHighReservePDESource

end ZtareProofs.NS
