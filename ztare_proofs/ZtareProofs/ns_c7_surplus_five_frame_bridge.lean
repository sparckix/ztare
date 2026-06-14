import ZtareProofs.ns_tick668_pressure_cutoff_carrier_identity

namespace ZtareProofs

open NSL3MultiscaleYM

namespace Route1FreshFrequencyCoercivity

/--
If the five-frame/route-tail exchange receipt is ever supplied, any surplus
source certificate for that route-tail stream pays the five-frame prefixes.

This does not construct the exchange receipt; it records the exact downstream
consumer so the route cannot spend a route-tail budget on five-frame absolute
trace-free pay without the Tick668 exchange theorem.
-/
theorem FiveFrameRouteTailExchangeReceipt.fiveFramePrefix_le_surplusProjectedBudget
    (hExchange : FiveFrameRouteTailExchangeReceipt)
    (hSource :
      SurplusLiftProjectionSourceCertificate hExchange.routeTailPayment)
    (N : Nat) :
    nsTick668FinitePrefixSum hExchange.fiveFrameAngularEventPay N ≤
      hExchange.C * (hSource.C_proj * hSource.ambientBudget) := by
  have hRoutePrefix :
      nsTick668FinitePrefixSum hExchange.routeTailPayment N ≤
        hSource.C_proj * hSource.ambientBudget := by
    rw [nsTick668FinitePrefixSum_eq_nsPrefixSum hExchange.routeTailPayment N]
    exact hSource.targetPrefix_le_budget N
  exact
    le_trans (hExchange.fiveFramePrefix_le_routeTailPrefix_all N)
      (mul_le_mul_of_nonneg_left hRoutePrefix hExchange.C_nonnegative)

/--
The five-frame trace-free source already carries the exact stream identity
needed by a surplus certificate: event-radius payment and trace-free valuation
pay are pointwise equal.  This bridge exposes that downstream consumer without
constructing the source theorem or its owner-prefix budget.
-/
theorem FiveFrameTracefreeValuationSource.tracefreePrefix_le_surplusProjectedBudget
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hSurplus :
      SurplusLiftProjectionSourceCertificate hSource.eventRadiusPayment)
    (N : Nat) :
    nsTick668FinitePrefixSum hSource.tracefreeValuationPay N ≤
      hSurplus.C_proj * hSurplus.ambientBudget := by
  have hStream :
      hSource.tracefreeValuationPay = hSource.eventRadiusPayment :=
    funext fun n => (hSource.eventRadiusPayment_eq_tracefreeValuationPay n).symm
  rw [hStream]
  rw [nsTick668FinitePrefixSum_eq_nsPrefixSum hSource.eventRadiusPayment N]
  exact hSurplus.targetPrefix_le_budget N

/--
The surplus-paid five-frame consumer cannot be used to hide the diagonal Dini
five-shadow overflow packet.  If the trace-free valuation stream is the
packet's replay-invariant shadow-TV stream, the consumer bridge gives a finite
prefix bound, contradicting the overflow certificate.
-/
theorem no_surplusPaidFiveFrameTracefreeSource_of_diagonalDiniOverflow
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hPacket : FiveShadowDiagonalDiniValuationOverflowConfuser)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hSurplus :
      SurplusLiftProjectionSourceCertificate hSource.eventRadiusPayment)
    (hSameStream :
      hSource.tracefreeValuationPay =
        hPacket.replayInvariantShadowTVPay) :
    False := by
  rcases hPacket.replayInvariantShadowTVPrefixesOverflow
      (hSurplus.C_proj * hSurplus.ambientBudget) with ⟨N, hExceeds⟩
  have hBound :
      nsTick668FinitePrefixSum hPacket.replayInvariantShadowTVPay N ≤
        hSurplus.C_proj * hSurplus.ambientBudget := by
    simpa [hSameStream]
      using hSource.tracefreePrefix_le_surplusProjectedBudget hSurplus N
  exact not_lt_of_ge hBound hExceeds

/--
C7 same-carrier packing plus a genuine five-frame exchange receipt gives a
five-frame prefix budget.  The theorem deliberately assumes the exchange
receipt separately: the missing hard edge remains the same-prefix comparison
between `routeActiveTail` and five-frame absolute trace-free event pay.
-/
theorem fiveFramePrefix_le_C7PackingBudget_of_exchange
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : NS.EventRecurrencePriceLedger}
    {hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta}
    {hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L}
    {hElig :
      ResidualFreshExcessAuditEligibilityData
        (seq := seq) (K := K) (hRho := hRho) (hCarrier := hCarrier)
        (hBeta := hBeta) (hEvents := hEvents) (L := L)}
    {hGeom :
      LerayHeatFreshFrequencyEventTentGeometry
        seq K hRho hCarrier hEvents L}
    {hPressure :
      FreshFrequencyPressureTailEventAssignment
        seq K hRho hCarrier hEvents L}
    {hDuhamel :
      FreshFrequencyDuhamelErrorEventAssignment
        seq K hRho hCarrier hEvents L}
    {hLock :
      FreshFrequencyEventSameTreeLock
        seq K hRho hCarrier hBeta hEvents L hScale hInc}
    {hIndexed :
      ResidualFreshAuditIndexedSingleSpendCarrier
        hElig hGeom hPressure hDuhamel hLock}
    {routeActiveTail : Nat → Real}
    {hId :
      C7RouteActiveTailEventBetaSquareIdentification
        (hBeta := hBeta) (hEvents := hEvents) (L := L)
        routeActiveTail}
    (hPack : C7SameCarrierPackingNoReuseReceipt hIndexed hId)
    (hExchange : FiveFrameRouteTailExchangeReceipt)
    (hSameRoute : hExchange.routeTailPayment = routeActiveTail)
    (N : Nat) :
    nsTick668FinitePrefixSum hExchange.fiveFrameAngularEventPay N ≤
      hExchange.C * (hPack.rootBudget / hPack.c) := by
  have hRouteBudgetNS :
      NS.nsPrefixSum routeActiveTail N ≤ hPack.rootBudget / hPack.c :=
    le_trans
      (sameCarrierPacking_scaledRoutePrefix_le_scaledFreshPrefix hPack N)
      (sameCarrierPacking_scaledFreshPrefix_le_scaledRootBudget hPack N)
  have hRouteBudgetTick :
      nsTick668FinitePrefixSum hExchange.routeTailPayment N ≤
        hPack.rootBudget / hPack.c := by
    rw [hSameRoute]
    rw [nsTick668FinitePrefixSum_eq_nsPrefixSum routeActiveTail N]
    exact hRouteBudgetNS
  exact
    le_trans (hExchange.fiveFramePrefix_le_routeTailPrefix_all N)
      (mul_le_mul_of_nonneg_left hRouteBudgetTick hExchange.C_nonnegative)

/--
If the route active tail in the same-carrier C7 packing receipt is exactly the
event-radius stream of a five-frame trace-free source, then the packing budget
pays every trace-free valuation prefix.  The statement consumes the source
receipt; it does not manufacture the five-frame source or the PDE owner-budget
theorem behind it.
-/
theorem tracefreeValuationPrefix_le_C7PackingBudget_of_fiveFrameSource
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : NS.EventRecurrencePriceLedger}
    {hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta}
    {hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L}
    {hElig :
      ResidualFreshExcessAuditEligibilityData
        (seq := seq) (K := K) (hRho := hRho) (hCarrier := hCarrier)
        (hBeta := hBeta) (hEvents := hEvents) (L := L)}
    {hGeom :
      LerayHeatFreshFrequencyEventTentGeometry
        seq K hRho hCarrier hEvents L}
    {hPressure :
      FreshFrequencyPressureTailEventAssignment
        seq K hRho hCarrier hEvents L}
    {hDuhamel :
      FreshFrequencyDuhamelErrorEventAssignment
        seq K hRho hCarrier hEvents L}
    {hLock :
      FreshFrequencyEventSameTreeLock
        seq K hRho hCarrier hBeta hEvents L hScale hInc}
    {hIndexed :
      ResidualFreshAuditIndexedSingleSpendCarrier
        hElig hGeom hPressure hDuhamel hLock}
    {routeActiveTail : Nat → Real}
    {hId :
      C7RouteActiveTailEventBetaSquareIdentification
        (hBeta := hBeta) (hEvents := hEvents) (L := L)
        routeActiveTail}
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hPack : C7SameCarrierPackingNoReuseReceipt hIndexed hId)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hSameRoute : hSource.eventRadiusPayment = routeActiveTail)
    (N : Nat) :
    nsTick668FinitePrefixSum hSource.tracefreeValuationPay N ≤
      hPack.rootBudget / hPack.c := by
  have hRouteBudgetNS :
      NS.nsPrefixSum routeActiveTail N ≤ hPack.rootBudget / hPack.c :=
    le_trans
      (sameCarrierPacking_scaledRoutePrefix_le_scaledFreshPrefix hPack N)
      (sameCarrierPacking_scaledFreshPrefix_le_scaledRootBudget hPack N)
  have hSourceStream :
      hSource.tracefreeValuationPay = hSource.eventRadiusPayment :=
    funext fun n => (hSource.eventRadiusPayment_eq_tracefreeValuationPay n).symm
  have hStream : hSource.tracefreeValuationPay = routeActiveTail :=
    hSourceStream.trans hSameRoute
  rw [hStream]
  rw [nsTick668FinitePrefixSum_eq_nsPrefixSum routeActiveTail N]
  exact hRouteBudgetNS

/--
Typed owner-preimage prefix payment for a five-frame trace-free source.

This is intentionally a receipt interface, not a constructor.  The workbench
requires the owner map, output-scale owner eligibility, finite multiplicity,
no-rebilling, and the numerical selected-prefix inequality before a source
theorem can spend owner-preimage currency on trace-free valuation pay.
-/
structure FiveFrameOwnerPreimagePrefixReceipt
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hSource : FiveFrameTracefreeValuationSource formula) where
  ownerPreimageBudget : Real
  ownerMapFixedBeforePayoff : Prop
  ownerMapFixedBeforePayoff_proof : ownerMapFixedBeforePayoff
  fullOutputScaleOwner : Prop
  fullOutputScaleOwner_proof : fullOutputScaleOwner
  finiteOwnerMultiplicity : Prop
  finiteOwnerMultiplicity_proof : finiteOwnerMultiplicity
  noOwnerPreimageRebilling : Prop
  noOwnerPreimageRebilling_proof : noOwnerPreimageRebilling
  tracefreePrefix_le_ownerPreimageBudget :
    ∀ N : Nat,
      nsTick668FinitePrefixSum hSource.tracefreeValuationPay N ≤
        ownerPreimageBudget

/--
A C7 owner-preimage receipt pays the five-frame owner-preimage receipt once
the five-frame source is identified with the same route-active-tail stream.

This is a conditional positive adapter, not a source theorem: the numerical
prefix inequality comes from `OwnerPreimagePackingReceipt`, and the qualitative
owner/timing/no-rebilling fields are projected from `C7PackingOwnerPreimageReceipt`
rather than filled by declaration-only labels.
-/
def FiveFrameOwnerPreimagePrefixReceipt.ofC7PackingOwnerPreimageReceipt
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : NS.EventRecurrencePriceLedger}
    {hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta}
    {hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L}
    {hElig :
      ResidualFreshExcessAuditEligibilityData
        (seq := seq) (K := K) (hRho := hRho) (hCarrier := hCarrier)
        (hBeta := hBeta) (hEvents := hEvents) (L := L)}
    {hGeom :
      LerayHeatFreshFrequencyEventTentGeometry
        seq K hRho hCarrier hEvents L}
    {hPressure :
      FreshFrequencyPressureTailEventAssignment
        seq K hRho hCarrier hEvents L}
    {hDuhamel :
      FreshFrequencyDuhamelErrorEventAssignment
        seq K hRho hCarrier hEvents L}
    {hLock :
      FreshFrequencyEventSameTreeLock
        seq K hRho hCarrier hBeta hEvents L hScale hInc}
    {hIndexed :
      ResidualFreshAuditIndexedSingleSpendCarrier
        hElig hGeom hPressure hDuhamel hLock}
    {routeActiveTail : Nat → Real}
    {hId :
      C7RouteActiveTailEventBetaSquareIdentification
        (hBeta := hBeta) (hEvents := hEvents) (L := L)
        routeActiveTail}
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hPack : C7SameCarrierPackingNoReuseReceipt hIndexed hId)
    (hOwner : C7PackingOwnerPreimageReceipt hPack)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hSameRoute : hSource.eventRadiusPayment = routeActiveTail) :
    FiveFrameOwnerPreimagePrefixReceipt hSource where
  ownerPreimageBudget := hOwner.multiplicityBound * hOwner.atomBudget
  ownerMapFixedBeforePayoff := hOwner.ownerChosenByStoppingRuleBeforePayoff
  ownerMapFixedBeforePayoff_proof :=
    hOwner.ownerChosenByStoppingRuleBeforePayoff_proof
  fullOutputScaleOwner := hOwner.ownerLivesInSameAnnularPhaseSpaceTent
  fullOutputScaleOwner_proof :=
    hOwner.ownerLivesInSameAnnularPhaseSpaceTent_proof
  finiteOwnerMultiplicity := hOwner.boundedOwnerMultiplicityOnLineage
  finiteOwnerMultiplicity_proof :=
    hOwner.boundedOwnerMultiplicityOnLineage_proof
  noOwnerPreimageRebilling := hOwner.noReuseSeparatedFromOwnerBudget
  noOwnerPreimageRebilling_proof :=
    hOwner.noReuseSeparatedFromOwnerBudget_proof
  tracefreePrefix_le_ownerPreimageBudget := by
    intro N
    have hSourceStream :
        hSource.tracefreeValuationPay = hSource.eventRadiusPayment :=
      funext fun n => (hSource.eventRadiusPayment_eq_tracefreeValuationPay n).symm
    have hStream : hSource.tracefreeValuationPay = routeActiveTail :=
      hSourceStream.trans hSameRoute
    rw [hStream]
    rw [nsTick668FinitePrefixSum_eq_nsPrefixSum routeActiveTail N]
    exact
      OwnerPreimagePackingReceipt.eventPrefix_le_ownerBudget
        hOwner.ownerPreimage N

/--
Weak owner-preimage labels for a five-frame trace-free source.

These are deliberately the fields the workbench rejected as weak substitutes:
pointwise ownership/payment labels, finite atom budget labels, local fanout
labels, and qualitative same-carrier/no-reuse labels.  There is no numerical
selected-prefix owner-preimage inequality here.
-/
structure FiveFrameWeakOwnerPreimageLabels
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hSource : FiveFrameTracefreeValuationSource formula) where
  ownerMapDeclaredBeforePayoff : Prop
  ownerMapDeclaredBeforePayoff_proof : ownerMapDeclaredBeforePayoff
  pointwiseOwnerPaymentLabel : Prop
  pointwiseOwnerPaymentLabel_proof : pointwiseOwnerPaymentLabel
  finiteAtomBudgetLabel : Prop
  finiteAtomBudgetLabel_proof : finiteAtomBudgetLabel
  boundedLocalFanoutLabel : Prop
  boundedLocalFanoutLabel_proof : boundedLocalFanoutLabel
  sameCarrierNoReuseLabel : Prop
  sameCarrierNoReuseLabel_proof : sameCarrierNoReuseLabel

def weakOwnerPreimageLabels_of_diagonalDiniOverflow
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hPacket : FiveShadowDiagonalDiniValuationOverflowConfuser)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (_hSameStream :
      hSource.tracefreeValuationPay =
        hPacket.replayInvariantShadowTVPay) :
    FiveFrameWeakOwnerPreimageLabels hSource := by
  exact
    { ownerMapDeclaredBeforePayoff := True
      ownerMapDeclaredBeforePayoff_proof := trivial
      pointwiseOwnerPaymentLabel := True
      pointwiseOwnerPaymentLabel_proof := trivial
      finiteAtomBudgetLabel := True
      finiteAtomBudgetLabel_proof := trivial
      boundedLocalFanoutLabel := True
      boundedLocalFanoutLabel_proof := trivial
      sameCarrierNoReuseLabel := True
      sameCarrierNoReuseLabel_proof := trivial }

/--
Weak owner labels alone are compatible with the diagonal Dini replay-invariant
stream at the receipt-interface level.  The construction uses only label
fields; it does not provide `fullOutputScaleOwner`, finite multiplicity, no
rebilling, or a selected-prefix inequality.
-/
theorem weakOwnerPreimageLabels_compatible_with_diagonalDiniOverflow
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hPacket : FiveShadowDiagonalDiniValuationOverflowConfuser)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hSameStream :
      hSource.tracefreeValuationPay =
        hPacket.replayInvariantShadowTVPay) :
    Nonempty (FiveFrameWeakOwnerPreimageLabels hSource) :=
  ⟨weakOwnerPreimageLabels_of_diagonalDiniOverflow
    hPacket hSource hSameStream⟩

/--
Any complete owner-preimage prefix receipt for a five-frame trace-free source
must already exclude the diagonal Dini replay-invariant shadow-TV packet.  This
is the source-boundary guard surfaced by the PDE workbench: pointwise owner
labels are not enough, but a real selected-prefix owner-preimage inequality
would contradict the unbounded Dini prefixes.
-/
theorem no_ownerPreimagePrefixPaidFiveFrameTracefreeSource_of_diagonalDiniOverflow
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hPacket : FiveShadowDiagonalDiniValuationOverflowConfuser)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hReceipt : FiveFrameOwnerPreimagePrefixReceipt hSource)
    (hSameStream :
      hSource.tracefreeValuationPay =
        hPacket.replayInvariantShadowTVPay) :
    False := by
  rcases hPacket.replayInvariantShadowTVPrefixesOverflow
      hReceipt.ownerPreimageBudget with ⟨N, hExceeds⟩
  have hBound :
      nsTick668FinitePrefixSum hPacket.replayInvariantShadowTVPay N ≤
        hReceipt.ownerPreimageBudget := by
    simpa [hSameStream]
      using hReceipt.tracefreePrefix_le_ownerPreimageBudget N
  exact not_lt_of_ge hBound hExceeds

/--
Adding weak owner labels to the diagonal Dini packet does not change the
source-boundary obstruction.  The contradiction still requires the real
`FiveFrameOwnerPreimagePrefixReceipt`; the weak label packet is intentionally
unused except as a visible guard against label laundering.
-/
theorem no_weakOwnerLabelsPlusReceiptPaidFiveFrameTracefreeSource_of_diagonalDiniOverflow
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hPacket : FiveShadowDiagonalDiniValuationOverflowConfuser)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (_hWeak : FiveFrameWeakOwnerPreimageLabels hSource)
    (hReceipt : FiveFrameOwnerPreimagePrefixReceipt hSource)
    (hSameStream :
      hSource.tracefreeValuationPay =
        hPacket.replayInvariantShadowTVPay) :
    False :=
  no_ownerPreimagePrefixPaidFiveFrameTracefreeSource_of_diagonalDiniOverflow
    hPacket hSource hReceipt hSameStream

/--
The C7 same-carrier packing consumer also cannot hide the diagonal Dini
five-shadow overflow packet.  This is the C7-specific version of the surplus
guard above: if the trace-free valuation stream is the replay-invariant
shadow-TV stream, the C7 prefix budget contradicts the overflow certificate.
-/
theorem no_C7PackingPaidFiveFrameTracefreeSource_of_diagonalDiniOverflow
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : NS.EventRecurrencePriceLedger}
    {hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta}
    {hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L}
    {hElig :
      ResidualFreshExcessAuditEligibilityData
        (seq := seq) (K := K) (hRho := hRho) (hCarrier := hCarrier)
        (hBeta := hBeta) (hEvents := hEvents) (L := L)}
    {hGeom :
      LerayHeatFreshFrequencyEventTentGeometry
        seq K hRho hCarrier hEvents L}
    {hPressure :
      FreshFrequencyPressureTailEventAssignment
        seq K hRho hCarrier hEvents L}
    {hDuhamel :
      FreshFrequencyDuhamelErrorEventAssignment
        seq K hRho hCarrier hEvents L}
    {hLock :
      FreshFrequencyEventSameTreeLock
        seq K hRho hCarrier hBeta hEvents L hScale hInc}
    {hIndexed :
      ResidualFreshAuditIndexedSingleSpendCarrier
        hElig hGeom hPressure hDuhamel hLock}
    {routeActiveTail : Nat → Real}
    {hId :
      C7RouteActiveTailEventBetaSquareIdentification
        (hBeta := hBeta) (hEvents := hEvents) (L := L)
        routeActiveTail}
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hPacket : FiveShadowDiagonalDiniValuationOverflowConfuser)
    (hPack : C7SameCarrierPackingNoReuseReceipt hIndexed hId)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hSameRoute : hSource.eventRadiusPayment = routeActiveTail)
    (hSameStream :
      hSource.tracefreeValuationPay =
        hPacket.replayInvariantShadowTVPay) :
    False := by
  rcases hPacket.replayInvariantShadowTVPrefixesOverflow
      (hPack.rootBudget / hPack.c) with ⟨N, hExceeds⟩
  have hBound :
      nsTick668FinitePrefixSum hPacket.replayInvariantShadowTVPay N ≤
        hPack.rootBudget / hPack.c := by
    simpa [hSameStream]
      using
        tracefreeValuationPrefix_le_C7PackingBudget_of_fiveFrameSource
          hPack hSource hSameRoute N
  exact not_lt_of_ge hBound hExceeds

end Route1FreshFrequencyCoercivity
end ZtareProofs
