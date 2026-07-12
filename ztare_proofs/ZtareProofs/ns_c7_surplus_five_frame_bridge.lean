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
The C7 owner-preimage receipt pays the full trace-free cofinal owner-prefix
budget for a five-frame source whose event-radius stream is the same
route-active tail.  This upgrades the earlier prefix-only consumer: the
all-prefix inequalities come from `OwnerPreimagePackingReceipt`, while the
invoice/source and anti-laundering fields are projected from the typed C7 owner
receipt and the five-frame source.
-/
def TraceFreeVariationC7CofinalOwnerPrefixBudget.ofC7PackingOwnerPreimageAndFiveFrameSource
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
    {hPack : C7SameCarrierPackingNoReuseReceipt hIndexed hId}
    (hOwner : C7PackingOwnerPreimageReceipt hPack)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hSameRoute : hSource.eventRadiusPayment = routeActiveTail) :
    TraceFreeVariationC7CofinalOwnerPrefixBudget where
  selectedPrefixLength := 0
  activeAtomBound := hOwner.activeOwnerAtomBound
  owner := hOwner.ownerOfEvent
  angularEventPay := hSource.tracefreeValuationPay
  angularSampleMagnitude := hSource.tracefreeValuationPay
  atomCharge := hOwner.atomCharge
  targetCharge := hSource.tracefreeValuationPay
  angularTracefreeSpend := 0
  ownerTVBudget := hOwner.atomBudget
  C := hOwner.multiplicityBound
  angularEventPay_nonneg := by
    intro e
    have hSourceStream :
        hSource.tracefreeValuationPay = hSource.eventRadiusPayment :=
      funext fun n => (hSource.eventRadiusPayment_eq_tracefreeValuationPay n).symm
    have hStream : hSource.tracefreeValuationPay = routeActiveTail :=
      hSourceStream.trans hSameRoute
    simpa [hStream] using hOwner.ownerPreimage.eventPay_nonnegative e
  angularSampleMagnitude_nonneg := by
    intro e
    have hSourceStream :
        hSource.tracefreeValuationPay = hSource.eventRadiusPayment :=
      funext fun n => (hSource.eventRadiusPayment_eq_tracefreeValuationPay n).symm
    have hStream : hSource.tracefreeValuationPay = routeActiveTail :=
      hSourceStream.trans hSameRoute
    simpa [hStream] using hOwner.ownerPreimage.eventPay_nonnegative e
  atomCharge_nonneg := hOwner.atomCharge_nonnegative
  angularTracefreeSpend_nonneg := by norm_num
  ownerTVBudget_nonneg := hOwner.atomBudget_nonnegative
  C_nonneg := hOwner.multiplicityBound_nonnegative
  angularEventPrefixSpend_nonneg_selected := by
    simp [nsTick668FinitePrefixSum]
  ownerChargePrefixBudget_nonneg_selected := by
    rw [nsTick668FinitePrefixSum_eq_nsPrefixSum]
    exact
      NS.ns_prefix_sum_nonnegative_of_pointwise
        hOwner.atomCharge hOwner.atomCharge_nonnegative
        (hOwner.activeOwnerAtomBound 0)
  eventPay_eq_angularSampleMagnitude := by
    intro e _he
    rfl
  targetCharge_eq_angularEventPay := by
    intro e
    rfl
  angularTracefreeSpend_le_selectedEventPrefix := by
    simp [nsTick668FinitePrefixSum]
  pointwiseAngularEventPay_le_ownerCharge_all := by
    intro e
    have hSourceStream :
        hSource.tracefreeValuationPay = hSource.eventRadiusPayment :=
      funext fun n => (hSource.eventRadiusPayment_eq_tracefreeValuationPay n).symm
    have hStream : hSource.tracefreeValuationPay = routeActiveTail :=
      hSourceStream.trans hSameRoute
    simpa [hStream] using hOwner.ownerPreimage.pointwiseOwnedAtomPaysEvent e
  angularEventPrefixSpend_le_ownerChargePrefix_all := by
    intro N
    have hSourceStream :
        hSource.tracefreeValuationPay = hSource.eventRadiusPayment :=
      funext fun n => (hSource.eventRadiusPayment_eq_tracefreeValuationPay n).symm
    have hStream : hSource.tracefreeValuationPay = routeActiveTail :=
      hSourceStream.trans hSameRoute
    rw [hStream]
    rw [nsTick668FinitePrefixSum_eq_nsPrefixSum routeActiveTail N]
    rw [nsTick668FinitePrefixSum_eq_nsPrefixSum
      hOwner.atomCharge (hOwner.activeOwnerAtomBound N)]
    exact hOwner.ownerPreimage.ownerPreimagePackingPrefix N
  ownerChargePrefixBudget_le_ownerTVBudget_all := by
    intro N
    rw [nsTick668FinitePrefixSum_eq_nsPrefixSum
      hOwner.atomCharge (hOwner.activeOwnerAtomBound N)]
    exact hOwner.ownerPreimage.activeAtomPrefixBudget N
  angularEventPrefixSpend_le_ownerTVBudget_all := by
    intro N
    have hSourceStream :
        hSource.tracefreeValuationPay = hSource.eventRadiusPayment :=
      funext fun n => (hSource.eventRadiusPayment_eq_tracefreeValuationPay n).symm
    have hStream : hSource.tracefreeValuationPay = routeActiveTail :=
      hSourceStream.trans hSameRoute
    rw [hStream]
    rw [nsTick668FinitePrefixSum_eq_nsPrefixSum routeActiveTail N]
    exact OwnerPreimagePackingReceipt.eventPrefix_le_ownerBudget
      hOwner.ownerPreimage N
  targetPrefix_le_ownerTVBudget_all := by
    intro N
    have hSourceStream :
        hSource.tracefreeValuationPay = hSource.eventRadiusPayment :=
      funext fun n => (hSource.eventRadiusPayment_eq_tracefreeValuationPay n).symm
    have hStream : hSource.tracefreeValuationPay = routeActiveTail :=
      hSourceStream.trans hSameRoute
    rw [hStream]
    rw [nsTick668FinitePrefixSum_eq_nsPrefixSum routeActiveTail N]
    exact OwnerPreimagePackingReceipt.eventPrefix_le_ownerBudget
      hOwner.ownerPreimage N
  ownerIsTraceFreeVariationDisintegrationSection :=
    hOwner.ownerChosenByStoppingRuleBeforePayoff ∧
      hOwner.ownerLivesInSameAnnularPhaseSpaceTent
  ownerIsTraceFreeVariationDisintegrationSection_proof :=
    ⟨hOwner.ownerChosenByStoppingRuleBeforePayoff_proof,
      hOwner.ownerLivesInSameAnnularPhaseSpaceTent_proof⟩
  angularEventsAreVariationAtomsOnExactInvoiceFiber :=
    hSource.fiveShadowMeasuresOnExactSameSource ∧
      hSource.sourceSigmaAlgebraMatchesSelectedAnnularOwnerFibers
  angularEventsAreVariationAtomsOnExactInvoiceFiber_proof :=
    ⟨hSource.fiveShadowMeasuresOnExactSameSource_proof,
      hSource.sourceSigmaAlgebraMatchesSelectedAnnularOwnerFibers_proof⟩
  c7PrefixReadsVariationDisintegrationPrefix :=
    hOwner.ownerPreimage.globalSelectedTreePreimageBound
  c7PrefixReadsVariationDisintegrationPrefix_proof :=
    hOwner.ownerPreimage.globalSelectedTreePreimageBound_proof
  ownerChargeIsNoncircularTraceFreeVariationMeasure :=
    hOwner.atomChargeNormalizesPackingCurrency ∧
      hOwner.atomBudgetNormalizesPackingCurrency
  ownerChargeIsNoncircularTraceFreeVariationMeasure_proof :=
    ⟨hOwner.atomChargeNormalizesPackingCurrency_proof,
      hOwner.atomBudgetNormalizesPackingCurrency_proof⟩
  totalVariationBudgetIndependentOfTargetSpend :=
    hOwner.productionSourceFixedBeforeOwnerMap ∧
      hOwner.ownerChosenByStoppingRuleBeforePayoff
  totalVariationBudgetIndependentOfTargetSpend_proof :=
    ⟨hOwner.productionSourceFixedBeforeOwnerMap_proof,
      hOwner.ownerChosenByStoppingRuleBeforePayoff_proof⟩
  traceFreeVariationBudgetNotProductL2OrGlobalL4Disguise :=
    hSource.notBesovBVProductL2OrCFImport ∧
      hOwner.notUniformEnstrophyBudgetDisguise
  traceFreeVariationBudgetNotProductL2OrGlobalL4Disguise_proof :=
    ⟨hSource.notBesovBVProductL2OrCFImport_proof,
      hOwner.notUniformEnstrophyBudgetDisguise_proof⟩
  sparseHighHighGhostAccountedOrExcludedForVariationBudget :=
    hOwner.pressureReserveSeparatedFromOwnerBudget ∧
      hOwner.selectedEventInheritedOrRenewedByAnnularOwner
  sparseHighHighGhostAccountedOrExcludedForVariationBudget_proof :=
    ⟨hOwner.pressureReserveSeparatedFromOwnerBudget_proof,
      hOwner.selectedEventInheritedOrRenewedByAnnularOwner_proof⟩
  noSignedMomentOrPositivePartBudget :=
    hSource.notSignedMomentOrPositivePartScalarization
  noSignedMomentOrPositivePartBudget_proof :=
    hSource.notSignedMomentOrPositivePartScalarization_proof
  exactInvoiceFiber :=
    hSource.sourceSigmaAlgebraMatchesSelectedAnnularOwnerFibers ∧
      hOwner.ownerBudgetIsSameCoronaDuhamelCarrier
  exactInvoiceFiber_proof :=
    ⟨hSource.sourceSigmaAlgebraMatchesSelectedAnnularOwnerFibers_proof,
      hOwner.ownerBudgetIsSameCoronaDuhamelCarrier_proof⟩
  sameInputCarrier :=
    hOwner.ownerBudgetIsSameCoronaDuhamelCarrier ∧
      hSource.fiveShadowMeasuresOnExactSameSource
  sameInputCarrier_proof :=
    ⟨hOwner.ownerBudgetIsSameCoronaDuhamelCarrier_proof,
      hSource.fiveShadowMeasuresOnExactSameSource_proof⟩
  selectedPacketPartitionFixedBeforePayoff :=
    hOwner.partitionFixedBeforeOwnerPreimage
  selectedPacketPartitionFixedBeforePayoff_proof :=
    hOwner.partitionFixedBeforeOwnerPreimage_proof
  noDescendantRebillingForAngularEvents :=
    hOwner.noReuseSeparatedFromOwnerBudget
  noDescendantRebillingForAngularEvents_proof :=
    hOwner.noReuseSeparatedFromOwnerBudget_proof
  carrierIsPreSummedNotFinalAngularSamples :=
    hSource.shadowMeasureTotalVariationChargedBeforeFinalSummation
  carrierIsPreSummedNotFinalAngularSamples_proof :=
    hSource.shadowMeasureTotalVariationChargedBeforeFinalSummation_proof
  noCFOrOtherClayEquivalentInputUsed :=
    hSource.notBesovBVProductL2OrCFImport ∧
      hOwner.notMonotoneTailCarrier ∧ hOwner.notScalarMeasureCarrier
  noCFOrOtherClayEquivalentInputUsed_proof :=
    ⟨hSource.notBesovBVProductL2OrCFImport_proof,
      hOwner.notMonotoneTailCarrier_proof,
      hOwner.notScalarMeasureCarrier_proof⟩

/--
Common-constructor Carleson receipt for the five-frame C7 owner-preimage route.

This is the Gowers-style coordinate change for TICK669: the active Carleson
budget is not selected by matching the visible Nat-indexed payment stream.
It is the same complete owner-prefix budget record constructed from the same
`C7PackingOwnerPreimageReceipt`, five-frame source, and route binding.
-/
def TraceFreeVariationSameCarrierFreshNoReuseCarlesonReceipt.ofC7PackingOwnerPreimageAndFiveFrameSource
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
    {hPack : C7SameCarrierPackingNoReuseReceipt hIndexed hId}
    (hOwner : C7PackingOwnerPreimageReceipt hPack)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hSameRoute : hSource.eventRadiusPayment = routeActiveTail) :
    TraceFreeVariationSameCarrierFreshNoReuseCarlesonReceipt where
  budget :=
    TraceFreeVariationC7CofinalOwnerPrefixBudget.ofC7PackingOwnerPreimageAndFiveFrameSource
      hOwner hSource hSameRoute
  traceFreeCarlesonBudgetIndependentOfAngularSpend :=
    hOwner.productionSourceFixedBeforeOwnerMap ∧
      hSource.shadowMeasureTotalVariationChargedBeforeFinalSummation
  traceFreeCarlesonBudgetIndependentOfAngularSpend_proof :=
    ⟨hOwner.productionSourceFixedBeforeOwnerMap_proof,
      hSource.shadowMeasureTotalVariationChargedBeforeFinalSummation_proof⟩
  sameCarrierFreshNoReuseForTraceFreeAtoms :=
    hOwner.ownerBudgetIsSameCoronaDuhamelCarrier ∧
      hOwner.noReuseSeparatedFromOwnerBudget ∧
        hSource.fiveShadowMeasuresOnExactSameSource
  sameCarrierFreshNoReuseForTraceFreeAtoms_proof :=
    ⟨hOwner.ownerBudgetIsSameCoronaDuhamelCarrier_proof,
      hOwner.noReuseSeparatedFromOwnerBudget_proof,
      hSource.fiveShadowMeasuresOnExactSameSource_proof⟩
  selectedC7TraceFreePrefixCofinalMap :=
    hOwner.ownerPreimage.globalSelectedTreePreimageBound
  selectedC7TraceFreePrefixCofinalMap_proof :=
    hOwner.ownerPreimage.globalSelectedTreePreimageBound_proof
  ownerAtomChargeNotBesovBVProxy :=
    hSource.notBesovBVProductL2OrCFImport ∧
      hOwner.notUniformEnstrophyBudgetDisguise
  ownerAtomChargeNotBesovBVProxy_proof :=
    ⟨hSource.notBesovBVProductL2OrCFImport_proof,
      hOwner.notUniformEnstrophyBudgetDisguise_proof⟩
  ownerAtomChargeNotProductL2OrGlobalL4Proxy :=
    hSource.notBesovBVProductL2OrCFImport ∧
      hOwner.notUniformEnstrophyBudgetDisguise
  ownerAtomChargeNotProductL2OrGlobalL4Proxy_proof :=
    ⟨hSource.notBesovBVProductL2OrCFImport_proof,
      hOwner.notUniformEnstrophyBudgetDisguise_proof⟩
  sparseHighHighTraceFreePrefixOverflowExcludedByMechanism :=
    hOwner.pressureReserveSeparatedFromOwnerBudget ∧
      hOwner.selectedEventInheritedOrRenewedByAnnularOwner
  sparseHighHighTraceFreePrefixOverflowExcludedByMechanism_proof :=
    ⟨hOwner.pressureReserveSeparatedFromOwnerBudget_proof,
      hOwner.selectedEventInheritedOrRenewedByAnnularOwner_proof⟩
  boundedMultiplicityDoesNotDefineBudget :=
    hOwner.boundedOwnerMultiplicityOnLineage ∧
      hOwner.ownerPreimage.globalSelectedTreePreimageBound
  boundedMultiplicityDoesNotDefineBudget_proof :=
    ⟨hOwner.boundedOwnerMultiplicityOnLineage_proof,
      hOwner.ownerPreimage.globalSelectedTreePreimageBound_proof⟩
  identityOwnerSummableVariationReceipt :=
    ∀ N : Nat,
      NS.nsPrefixSum hOwner.atomCharge (hOwner.activeOwnerAtomBound N) ≤
        hOwner.atomBudget
  identityOwnerSummableVariationReceipt_proof :=
    hOwner.ownerPreimage.activeAtomPrefixBudget
  noCFCoherenceOrStrictMarginImported :=
    hSource.notBesovBVProductL2OrCFImport ∧
      hOwner.notUniformEnstrophyBudgetDisguise
  noCFCoherenceOrStrictMarginImported_proof :=
    ⟨hSource.notBesovBVProductL2OrCFImport_proof,
      hOwner.notUniformEnstrophyBudgetDisguise_proof⟩

/--
Valuation-specific owner budget from the C7 owner-preimage receipt.  This is
the direct consumer needed by the TICK669 A_visc five-frame route: once the
five-frame source is bound to the route-active tail and the typed C7
owner-preimage receipt exists, the valuation budget row follows with the same
cofinal trace-free owner budget.
-/
def TraceFreeL2ValuationC7CofinalOwnerBudget.ofC7PackingOwnerPreimageAndFiveFrameSource
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
    {hPack : C7SameCarrierPackingNoReuseReceipt hIndexed hId}
    (hOwner : C7PackingOwnerPreimageReceipt hPack)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hSameRoute : hSource.eventRadiusPayment = routeActiveTail) :
    TraceFreeL2ValuationC7CofinalOwnerBudget formula where
  source := hSource
  budget :=
    TraceFreeVariationC7CofinalOwnerPrefixBudget.ofC7PackingOwnerPreimageAndFiveFrameSource
      hOwner hSource hSameRoute
  valuationPay_eq_budgetAngularEventPay := rfl
  fiveShadowTVBudgetPaidBeforeScalarProjection :=
    hSource.shadowMeasureTotalVariationChargedBeforeFinalSummation
  fiveShadowTVBudgetPaidBeforeScalarProjection_proof :=
    hSource.shadowMeasureTotalVariationChargedBeforeFinalSummation_proof
  selectedValuationPrefixesCofinalWithC7ScaleTruncations :=
    hOwner.ownerPreimage.globalSelectedTreePreimageBound
  selectedValuationPrefixesCofinalWithC7ScaleTruncations_proof :=
    hOwner.ownerPreimage.globalSelectedTreePreimageBound_proof
  valuationBudgetNotFromEndpointCZOrSignedDiniOrProductL2 :=
    hSource.noCZEndpointMeasureLaundering ∧
      hSource.notSignedMomentOrPositivePartScalarization ∧
        hSource.notBesovBVProductL2OrCFImport
  valuationBudgetNotFromEndpointCZOrSignedDiniOrProductL2_proof :=
    ⟨hSource.noCZEndpointMeasureLaundering_proof,
      hSource.notSignedMomentOrPositivePartScalarization_proof,
      hSource.notBesovBVProductL2OrCFImport_proof⟩
  exactInvoiceFiberForFiveShadowValuation :=
    hSource.sourceSigmaAlgebraMatchesSelectedAnnularOwnerFibers ∧
      hOwner.ownerBudgetIsSameCoronaDuhamelCarrier
  exactInvoiceFiberForFiveShadowValuation_proof :=
    ⟨hSource.sourceSigmaAlgebraMatchesSelectedAnnularOwnerFibers_proof,
      hOwner.ownerBudgetIsSameCoronaDuhamelCarrier_proof⟩

/--
Separated-source owner geometry is enough to pay the TICK669 five-frame
valuation budget.

The proof is a consumer-facing composition: the separated-source bridge first
pays the residual-after-transfer receipt, then the owner-geometry core and
canonical separation receipt, then the C7 owner-preimage receipt consumed by
the five-frame valuation adapter above.  Thus the remaining mathematical input
is not scalar `A_visc` mass, but the same-source owner-lineage plus
anti-laundering bridge on the separated fresh-annular source.
-/
noncomputable def TraceFreeL2ValuationC7CofinalOwnerBudget.ofC7SeparatedSourceOwnerGeometryBridgeAndFiveFrameSource
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
    {h :
      CoronaDuhamelProductionSingleSpendCarrier
        hElig hGeom hPressure hDuhamel hLock}
    {routeActiveTail : Nat → Real}
    {hId :
      C7RouteActiveTailEventBetaSquareIdentification
        (hBeta := hBeta) (hEvents := hEvents) (L := L)
        routeActiveTail}
    {hComplete :
      CoronaDuhamelC7SourceCompletion h hId}
    {hTransfer :
      C7ScaledOwnerPreimageCarrierTransfer
        (C7SameCarrierPackingNoReuseReceipt.ofCoronaDuhamelC7SourceCompletion
          hComplete)}
    {pressureL2 : PressureHessianL2Amplitude}
    {radialGrade : Real}
    {formula : Route1ProjectedRieszAngularFormulaSource pressureL2 radialGrade}
    (hBridge :
      C7OwnerGeometryResidualBridgeFromFreshAnnularChargeSeparatedSource
        hTransfer)
    (hSource : FiveFrameTracefreeValuationSource formula)
    (hSameRoute : hSource.eventRadiusPayment = routeActiveTail) :
    TraceFreeL2ValuationC7CofinalOwnerBudget formula :=
  let hResidual :
      C7OwnerGeometryResidualAfterScaledTransfer hTransfer :=
    C7OwnerGeometryResidualAfterScaledTransfer.ofFreshAnnularChargeSeparatedBridge
      hBridge
  let hCore : C7OwnerPreimageGeometryCoreReceipt hComplete :=
    C7OwnerPreimageGeometryCoreReceipt.ofScaledCarrierTransferResidual
      hResidual
  let hSep :
      C7CarrierRadiusCanonicalOwnerSeparationReceipt hComplete :=
    C7CarrierRadiusCanonicalOwnerSeparationReceipt.ofOwnerPreimageGeometryCore
      hCore
  TraceFreeL2ValuationC7CofinalOwnerBudget.ofC7PackingOwnerPreimageAndFiveFrameSource
    (C7PackingOwnerPreimageReceipt.ofScaledCarrierTransferCanonicalCurrency
      hTransfer
      hSep.productionSourceFixedBeforeOwnerMap
      hSep.productionSourceFixedBeforeOwnerMap_proof
      hSep.pressureReserveSeparatedFromOwnerBudget
      hSep.pressureReserveSeparatedFromOwnerBudget_proof
      hSep.partitionFixedBeforeOwnerPreimage
      hSep.partitionFixedBeforeOwnerPreimage_proof
      hSep.sectionIdentityFixedBeforeOwnerPreimage
      hSep.sectionIdentityFixedBeforeOwnerPreimage_proof
      hSep.noReuseSeparatedFromOwnerBudget
      hSep.noReuseSeparatedFromOwnerBudget_proof
      hSep.selectedEventInheritedOrRenewedByAnnularOwner
      hSep.selectedEventInheritedOrRenewedByAnnularOwner_proof
      hSep.boundedOwnerMultiplicityOnLineage
      hSep.boundedOwnerMultiplicityOnLineage_proof
      hSep.ownerBudgetIsSameCoronaDuhamelCarrier
      hSep.ownerBudgetIsSameCoronaDuhamelCarrier_proof
      hSep.notMonotoneTailCarrier
      hSep.notMonotoneTailCarrier_proof
      hSep.notScalarMeasureCarrier
      hSep.notScalarMeasureCarrier_proof
      hSep.notUniformEnstrophyBudgetDisguise
      hSep.notUniformEnstrophyBudgetDisguise_proof
      hSep.sourceSelectionNotDeclarationOnly)
    hSource
    hSameRoute

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
