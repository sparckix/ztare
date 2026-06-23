"""L3A concentration-branch workmap for NS Track-B triage.

The general NS graph/miner stack is useful, but its global ranking is dominated
by older high-use Track-B pricing-kernel declarations. This module extracts the
new L3A concentration/flux branch into its own ranked workmap so RD ticks can
see the next proof targets directly.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from ztare.motion.set_distance import jaccard_distance
from ztare.research_director.primitive_tick_surface import build_primitive_tick_surface


REPO = Path(__file__).resolve().parents[3]
DECL_INDEX = REPO / "analytics" / "public" / "queries" / "lean" / "lean_decl_index.json"
ARTIFACT_GRAPH = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "ns_trackb_artifact_graph.json"
)
OUT_PATH = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "ns_l3a_concentration_workmap.json"
)

L3A_FILE = "ns_L3_multiscale_YM_rescaled_increments"

ROUTE_ANCHORS = [
    "EventizedParabolicBetaCarlesonQuantStratSplitWitness",
    "BadCenterEventNonadaptiveWeightedSquareDomination",
    "SameTreeNonadaptiveEventIncidenceCarleson",
    "SameTreeEventIncidenceIndependentBudgetSplitWitness",
    "IndependentSameTreeEventBudgetWitness",
    "DuhamelSameTreeIndependentEventBudgetCandidate",
    "FreshFrequencyEventSameTreeLock",
    "FreshFrequencyPrefixDominationFromSubprimitives",
    "NonflatBadNodeFreshPacketDichotomy",
    "FreshPacketGainPaysNonflatBeta",
    "FreshFrequencyBoundedFanoutNoLogReuse",
    "DuhamelBernsteinFreshFrequencyEvent",
    "FreshFrequencyPressureDuhamelSameCarrierLock",
    "FreshFrequencyFlatBadCenterSkeletonLock",
    "BadNormalizedExcessDoesNotAutomaticallyCreateFreshFrequencyEvent",
    "FreshFrequencyEventRouteAvoidsEventPerNodeTautology",
    "SameTreeDuhamelBudgetRemainingObligations",
    "PriceDropDuhamelSourceDoesNotFillSameTreeObligations",
    "DuhamelReserveCanBeShellOnlyNotBadCenterBudget",
    "DuhamelReserveReuseCanMissBadCenterMultiplicity",
    "PressureDuhamelLeakageBlocksSameTreeBudget",
    "EventPerBadNodeConstructionIsTautological",
    "PressureDuhamelSameCarrierLock",
    "FlatBadCenterSkeletonLengthControl",
    "BadCenterQuantitativeDifferentiationPackage",
    "InheritedBadTreeCoronaNoNeckSkeleton",
    "FiniteLengthBadSkeletonDensityNoNeckStrong",
    "ExcessDropChargesBadCylinderRadiusSplitWitness",
    "RadiusChargingBadScaleMeasure",
    "NormalizedCKNExcessSublevelCarlesonPacking",
    "SignedToAbsoluteCubicFluxNoNeck",
]

NATIVE_PRIMITIVE_QUERY_TERMS = [
    "jaccard",
    "motion",
    "bic",
    "fit_primitive",
    "graph",
    "basin",
    "navier",
    "pde",
    "score",
    "critical_increment",
]

EXTERNAL_REFERENCE_SURFACE = [
    {
        "id": "lei_ren_2022_quantitative_partial_regularity_ns",
        "url": "https://arxiv.org/abs/2210.01783",
        "kind": "pde_reference",
        "why_relevant": (
            "Navier-Stokes quantitative partial regularity; useful as a sanity "
            "check for any claim that CKN data can be upgraded by a logarithmic "
            "or pigeonhole mechanism."
        ),
        "local_mapping": [
            "NormalizedCKNExcessSublevelCarlesonPacking",
            "CKNExcessCarlesonPacking",
            "RadiusChargingBadScaleMeasure",
        ],
    },
    {
        "id": "naber_valtorta_2017_rectifiable_reifenberg",
        "url": "https://annals.math.princeton.edu/2017/185-1/p03",
        "kind": "pde_geometry_reference",
        "why_relevant": (
            "Quantitative stratification plus beta/Reifenberg estimates turn "
            "symmetry defects into Minkowski/rectifiability control; this is "
            "the closest external template for the bad-center beta route."
        ),
        "local_mapping": [
            "BadCenterQuantitativeDifferentiationPackage",
            "BadCenterBetaSquareCarlesonDrop",
            "EventizedParabolicBetaCarlesonQuantStratConstructiveData",
            "SameTreeNonadaptiveEventIncidenceCarleson",
            "SameTreeEventIncidenceIndependentBudgetSplitWitness",
            "IndependentSameTreeEventBudgetWitness",
            "DuhamelSameTreeIndependentEventBudgetCandidate",
            "FreshFrequencyEventSameTreeLock",
            "FlatBadCenterSkeletonLengthControl",
        ],
    },
    {
        "id": "holden_korovin_2023_graph_sequence_premise_selection",
        "url": "https://arxiv.org/abs/2303.15642",
        "kind": "graph_algorithm_reference",
        "why_relevant": (
            "Graph sequence learning treats proof search as selecting an ordered "
            "premise sequence; relevant for turning Lean declaration graphs into "
            "candidate proof-route packets, not for PDE truth."
        ),
        "local_mapping": [
            "BadCenterEventNonadaptiveWeightedSquareDomination",
            "EventizedParabolicBetaCarlesonQuantStratConstructiveData",
            "SameTreeNonadaptiveEventIncidenceCarleson",
            "SameTreeEventIncidenceIndependentBudgetSplitWitness",
            "IndependentSameTreeEventBudgetWitness",
            "DuhamelSameTreeIndependentEventBudgetCandidate",
        ],
    },
    {
        "id": "buehler_2024_scientific_kg_reasoning",
        "url": "https://arxiv.org/abs/2403.11996",
        "kind": "knowledge_graph_reference",
        "why_relevant": (
            "Scientific knowledge graph exploration via communities, centrality, "
            "embeddings, and path sampling; relevant only as a route-discovery "
            "instrumentation analogue."
        ),
        "local_mapping": [
            "NS-GRAPH-TICK-PRECHECK",
            "NS-L3A-CONCENTRATION-WORKMAP",
        ],
    },
]

KEYWORD_WEIGHTS = {
    "CubicVectorMeasureCompactness": 120,
    "CubicVectorRadonMeasure": 110,
    "SignedWeakStarFluxConvergence": 110,
    "UniformIntegrabilityKillsFlux": 105,
    "ConcentrationFluxRepresentation": 60,
    "GeneralizedCubicYoungMeasure": 95,
    "RescaledIncrementStrongL2Vanishes": 90,
    "OrdinaryOscillationCollapse": 85,
    "CriticalIncrementBound": 80,
    "CriticalIncrementL3Bound": 75,
    "CriticalIncrementNoCollapsePacking": 90,
    "CriticalIncrementNoCollapseNotMerelySupport": 88,
    "CriticalIncrementNoNeckTheorem": 86,
    "SignedToAbsoluteCubicFluxNoNeck": 91,
    "SequenceBoundConcentrationFluxRepresentation": 40,
    "selectedDuchonRobertFluxMeasureSeq": 86,
    "SignedToAbsoluteNoNeckRequiresConcentrationFluxRepresentation": 40,
    "SignedFluxTestsDoNotImplyCriticalIncrementBoundBridge": 90,
    "SignedDRFluxBridgeDoesNotProduceCKNExcessCarlesonPacking": 156,
    "signedDRFluxBridgeDoesNotProduceCKNExcessCarlesonPacking_of_signedBridge": 141,
    "signedToAbsoluteCubicFluxNoNeck_of_bridge": 83,
    "sequenceBoundConcentrationFluxRepresentation_of_collapse": 86,
    "signedToAbsoluteNoNeck_requires_concentrationFluxRepresentation": 84,
    "signedFluxTestsDoNotImplyCriticalIncrementBoundBridge": 83,
    "DefectSurgeryDoesNotImproveCriticalIncrementBound": 84,
    "CubicConcentrationBubbleTangentProblem": 82,
    "regularityScaleLayerCakeBridge_of_codimFourPacking": 93,
    "oneScaleEnstrophyCriticalIncrementBound_of_enstrophyPacking_and_layerCakeBridge": 87,
    "QualitativeCKNDimOneDoesNotGiveRegularityScaleLayerCakeBridge": 90,
    "no_regularityScaleLayerCakeBridge_of_dimOneOnly": 90,
    "SuitableWeakToCriticalIncrementNoCollapsePackingTarget": 92,
    "SuitableWeakToRegularityScalePresentationTarget": 96,
    "EnstrophyCKNExcessToRegularityScalePresentationTarget": 94,
    "CKNExcessRegularityScaleConstructionWitness": 98,
    "CKNExcessRegularityScaleSplitWitness": 118,
    "RhoFromNormalizedCKNExcess": 99,
    "PointwiseScaleBoundsFromEpsilonRegularity": 97,
    "CodimFourSublevelVolumeFromExcess": 195,
    "NormalizedCKNExcessSublevelCarlesonPacking": 230,
    "CKNExcessCarlesonPacking": 226,
    "NormalizedExcessSublevelCarlesonMeasure": 224,
    "BadScaleMultiplicityControl": 222,
    "RadiusChargingBadScaleMeasure": 246,
    "ExcessDropChargesBadCylinderRadius": 242,
    "ExcessDropPotentialCandidate": 238,
    "ExcessDropTreeSuperadditivity": 240,
    "BadNodeRadiusDrop": 244,
    "ExcessDropTelescopesToRadiusCharging": 241,
    "ExcessDropChargesBadCylinderRadiusSplitWitness": 248,
    "RadiusChargingBadScaleMeasure.ofExcessDropSplitWitness": 213,
    "LocalExcessDecayWithoutTelescopingDoesNotChargeRadius": 236,
    "ClassicalMassChargeDoesNotDefineExcessDropPotential": 237,
    "ExcessDropRadiusChargeRequiresPointwiseBadCylinderDrop": 239,
    "MassRenormalizationCannotTelescopeAndPayRadius": 249,
    "NormalizedCKNExcessNotTreeSuperadditive": 247,
    "UnnormalizedMassTelescopesOnlyRadiusSquared": 248,
    "SignedFluxDoesNotDefineRadiusDropPotential": 233,
    "FreshEnstrophyRadiusDropForBadNormalizedExcess": 236,
    "FiniteLengthBadSkeletonDensityNoNeck": 244,
    "FreshEnstrophyDropFailsByChildConcentration": 256,
    "CKNBadnessToEnstrophyOnlyR2WithoutScaleInvariantEnergy": 255,
    "ResidualFreshExcessForcesFreshEnstrophy": 260,
    "ChildConcentrationNoLogPileupOrSkeletonCharge": 258,
    "BadNodeResidualOrInheritedDichotomy": 278,
    "PressureTailEscapeBlocksFreshEnstrophyDrop": 254,
    "FiniteLengthBadSkeletonDensityNoNeckStrong": 270,
    "InheritedBadnessNoChildRadiiContractionFromCKNMass": 282,
    "LogPileupInheritedBadTreeModel": 276,
    "ResidualBranchConditionalFreshEnstrophy": 264,
    "PressureInheritanceBlocksChildContraction": 260,
    "InheritedBadTreeCoronaNoNeckSkeleton": 292,
    "DimensionOneSupportDoesNotGiveRadiusCharging": 257,
    "ParabolicBadCenterBetaCarleson": 288,
    "NormalizedExcessBadCenterSelection": 289,
    "BadCenterNonadaptiveConstructionGuard": 292,
    "ParabolicBadCenterBetaNumberControl": 298,
    "BadCenterLowerDensityForSelectedNodes": 291,
    "NonadaptiveBadCenterCarrierFromNormalizedExcess": 300,
    "BadCenterParabolicBetaData": 299,
    "BadCenterBetaSquareCarlesonDrop": 306,
    "BadCenterMonotoneFrequencyDrop": 307,
    "BadCenterQuantitativeDifferentiationPackage": 309,
    "BadCenterMonotoneFrequencyDrop.ofQuantitativeDifferentiation": 223,
    "NormalizedMassCannotBeBadCenterFrequencyDrop": 292,
    "EnstrophyFrequencyDropNeedsNSOnlyMonotonicity": 296,
    "SignedFluxCannotBeBadCenterFrequencyDrop": 290,
    "PressureRecoveryDoesNotGiveBadCenterFrequencyDrop": 291,
    "QualitativeDimensionDoesNotGiveBadCenterFrequencyDrop": 289,
    "BadCenterEventRecurrenceLedgerBridge": 305,
    "BadCenterEventNodeIdentification": 306,
    "BadCenterEventWeightedSquareIdentification": 307,
    "badCenterEventBetaSquarePrefix": 227,
    "BadCenterEventPointwiseBetaSquareIdentity": 311,
    "eventWeightedGainPricePrefix_eq_badCenterEventBetaSquarePrefix": 228,
    "BadCenterEventPriceDropIdentification": 308,
    "BadCenterEventPriceDropDuhamelIncidenceSource": 310,
    "BadCenterEventPriceDropDuhamelIncidenceSource.eventCertificate": 225,
    "BadCenterEventPriceDropDuhamelIncidenceSource.weightedEventPricePrefix_le_budget": 226,
    "badCenterEventBetaSquarePrefix_le_eventBudget_ofDuhamelIncidenceSource": 229,
    "BadCenterBetaSquareCarlesonDrop.ofEventBudgetedPrefixData": 238,
    "BadCenterBetaSquareCarlesonDrop.ofSameTreeEventBudgetedPrefixData": 242,
    "BadCenterEventBudgetedBetaSquarePrefixBridge.ofPointwiseDuhamelCoverageNonCircular": 237,
    "event_weighted_gain_price_prefix_le_budget": 224,
    "BadCenterEventNonadaptiveWeightedSquareDomination": 312,
    "SameTreeNonadaptiveEventIncidenceCarleson": 360,
    "BadCenterEventNonadaptiveWeightedSquareDomination.ofSameTreeIncidence": 243,
    "SameTreeEventIncidenceIndependentBudgetSplitWitness": 386,
    "IndependentSameTreeEventBudgetWitness": 382,
    "DuhamelSameTreeIndependentEventBudgetCandidate": 384,
    "FreshFrequencyEventSameTreeLock": 760,
    "FreshFrequencyPrefixDominationFromSubprimitives": 755,
    "NonflatBadNodeFreshPacketDichotomy": 728,
    "FreshPacketGainPaysNonflatBeta": 724,
    "FreshFrequencyBoundedFanoutNoLogReuse": 726,
    "DuhamelBernsteinFreshFrequencyEvent": 372,
    "FreshFrequencyPressureDuhamelSameCarrierLock": 410,
    "FreshFrequencyFlatBadCenterSkeletonLock": 404,
    "BadNormalizedExcessDoesNotAutomaticallyCreateFreshFrequencyEvent": 414,
    "FreshFrequencyEventRouteAvoidsEventPerNodeTautology": 412,
    "SameTreePrefixDominationPrimitive.ofFreshFrequencyEventSameTreeLock": 244,
    "SameTreeDuhamelBudgetRemainingObligations": 390,
    "SameTreePrefixDominationPrimitive": 402,
    "SameTreeSelectedTreeControlPrimitive": 398,
    "sameTreePrefixDominationProp_ofPrimitive": 231,
    "sameTreeSelectedTreeControlProp_ofPrimitive": 231,
    "SameTreeDuhamelBudgetRemainingObligations.toSameTreeIncidence": 236,
    "PriceDropDuhamelSourceDoesNotFillSameTreeObligations": 388,
    "BadCenterEventIncidenceGeometry.ofPointwiseSingletonIncidence": 239,
    "SameTreeDuhamelBudgetRemainingObligations.ofPointwiseSingletonIncidence": 240,
    "SameTreeNonadaptiveEventIncidenceCarleson.ofPointwiseSingletonDuhamelSource": 241,
    "DuhamelSameTreeIndependentEventBudgetCandidate.ofPriceDropDuhamelIncidenceSource": 232,
    "SameTreeEventIncidenceIndependentBudgetSplitWitness.ofDuhamelSameTreeBudget": 230,
    "SameTreeNonadaptiveEventIncidenceCarleson.ofPriceDropDuhamelIncidenceSource": 234,
    "DuhamelReserveCanBeShellOnlyNotBadCenterBudget": 378,
    "DuhamelReserveReuseCanMissBadCenterMultiplicity": 376,
    "PressureDuhamelLeakageBlocksSameTreeBudget": 374,
    "EventPerBadNodeConstructionIsTautological": 370,
    "PressureDuhamelSameCarrierLock": 354,
    "FlatBadCenterSkeletonLengthControl": 350,
    "ChainwiseBetaDropDoesNotGiveGlobalBetaCarleson": 352,
    "EventizedParabolicBetaCarlesonQuantStratConstructiveData.ofSameTreeIncidence": 236,
    "BadCenterScaleTruncationPresentation": 314,
    "BadCenterEventIncidenceGeometry": 315,
    "BadCenterEventizedMonotoneBetaCarrier": 316,
    "BadCenterEventizedMonotoneBetaCarrier.ofQuantitativeDifferentiation": 233,
    "QuantitativeDifferentiationDoesNotSupplyEventIncidence": 327,
    "EventizedParabolicBetaCarlesonQuantitativeStratification": 318,
    "EventizedParabolicBetaCarlesonQuantStratSplitWitness": 319,
    "EventizedParabolicBetaCarlesonQuantStratConstructiveData": 321,
    "BadCenterEventNonadaptiveWeightedSquareDomination.ofEventizedConstructiveData": 234,
    "EventizedParabolicBetaCarlesonQuantitativeStratification.ofConstructiveData": 235,
    "EventizedParabolicBetaCarlesonQuantitativeStratification.ofSplitWitness": 232,
    "BadCenterEventNonadaptiveWeightedSquareDomination.ofEventizedQuantStrat": 231,
    "EventizedQuantStratNotSuppliedByEventAlgebraAlone": 323,
    "ScaleTruncationCofinalityNotSuppliedByEventPrefixAlone": 324,
    "SectionIncidenceDoesNotGiveBadCenterIncidenceGeometry": 325,
    "MonotoneBetaCarrierNotSuppliedByCKNMassOrEventAlgebra": 326,
    "BadCenterEventBudgetedBetaSquarePrefixBridge": 313,
    "BadCenterEventBudgetedBetaSquarePrefixBridge.ofPointwiseDuhamelCoverage": 230,
    "EventPrefixBudgetDoesNotImplyBadCenterBetaCarleson": 297,
    "PostHocEventBadNodeMatchingIsCircular": 298,
    "EventBadNodeUnboundedMultiplicityObstruction": 299,
    "BadCenterEventPriceDropIdentification.ofDuhamelIncidenceSource": 226,
    "BadCenterEventRecurrenceBridgeSplitWitness": 309,
    "BadCenterEventRecurrenceLedgerBridge.ofSplitWitness": 224,
    "BadCenterMonotoneFrequencyDrop.ofEventRecurrenceLedgerBridge": 223,
    "EventLedgerWithoutBadCenterIdentificationDoesNotCloseFrequencyDrop": 294,
    "EventPrecertificateWithoutBadCenterCarrierDoesNotClosePriceDrop": 296,
    "BadCenterBetaSquareCarlesonDrop.ofMonotoneFrequencyDrop": 222,
    "BadCenterBetaSquareCarlesonDrop.ofEventRecurrenceLedgerBridge": 224,
    "NSBadCenterBetaCarlesonSplitWitness": 304,
    "NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier": 218,
    "BadCenterNonadaptiveConstructionGuard.ofNonadaptiveCarrier": 218,
    "BadCenterLowerDensityForSelectedNodes.ofNonadaptiveCarrier": 218,
    "ParabolicBadCenterBetaNumberControl.ofBetaSquareDrop": 219,
    "ParabolicBadCenterBetaCarleson.ofSubwitnesses": 220,
    "ParabolicRectifiableReifenbergForBadCenters": 286,
    "BadCenterRectifiableBridgeWitness": 287,
    "NSBadCenterBetaCarlesonEstimate": 296,
    "QuantitativeStratificationSkeletonPackage": 294,
    "AdaptiveSkeletonChoiceWouldSmuggleRadiusCharge": 276,
    "CKNSupportDoesNotGiveBadCenterBetaCarleson": 284,
    "LogPileupBadCentersEvadeCarlesonWithoutBetaControl": 287,
    "ExcessDropChargesBadCylinderRadiusSplitWitness.ofFreshEnstrophyRadiusDrop": 216,
    "RadiusChargingBadScaleMeasure.ofFiniteLengthBadSkeletonDensityNoNeck": 211,
    "RadiusChargingBadScaleMeasure.ofFiniteLengthBadSkeletonDensityNoNeckStrong": 212,
    "RadiusChargingBadScaleMeasure.ofInheritedBadTreeCoronaNoNeckSkeleton": 213,
    "InheritedBadTreeCoronaNoNeckSkeleton.ofQuantitativeStratification": 214,
    "FiniteLengthBadSkeletonDensityNoNeckStrong.ofBadCenterBetaCarleson": 214,
    "ParabolicBadCenterBetaCarleson.ofNSBadCenterBetaCarlesonEstimate": 214,
    "NSBadCenterBetaCarlesonEstimate.ofSplitWitness": 220,
    "FiniteLengthBadSkeletonCharge": 214,
    "DyadicBadScaleCover": 188,
    "DyadicBadScaleSeparatedPacking": 190,
    "FiniteDyadicCarlesonPacking": 210,
    "BadScaleMultiplicityControl.ofFiniteDyadicCarlesonPacking": 184,
    "finite_badScaleCover_of_compact": 176,
    "CKNRestrictedDeGiorgiPositiveGain": 232,
    "CKNRestrictedDeGiorgiGainRulesOutLogPileup": 238,
    "PureLerayDeGiorgiProductionBoundDoesNotGivePositiveGain": 228,
    "pureLerayDeGiorgiProductionBound_doesNotGive_positiveGain": 194,
    "CKNRestrictionOnlyNoDerivedDeGiorgiGain": 235,
    "cknRestrictionOnly_doesNotDerive_deGiorgiPositiveGain": 205,
    "LocalizedProductionLevelSetGain": 168,
    "ProductionReverseHolderAboveThreshold": 154,
    "WeakBilinearDeGiorgiProductionNorm": 108,
    "EnergyDivFreeDeGiorgiGainIsTaoVulnerable": 150,
    "energyDivFreeDeGiorgiGain_isTaoVulnerable": 204,
    "DeGiorgiProductionCoefficientThreshold": 142,
    "WeakBilinearDeGiorgiProductionNorm_NotDerivedFromEnergy": 112,
    "weakBilinearDeGiorgiProductionNorm_notDerivedFromEnergy": 207,
    "TransportGainDoesNotControlStretchingProduction": 150,
    "TaoAveragedNSSieveForProductionGain": 156,
    "PositiveDeGiorgiGainDoesNotTelescopeBadScales": 166,
    "LocalizedProductionLevelSetGain.ofWeakBilinearProductionNorm": 128,
    "LocalizedProductionLevelSetGain.ofReverseHolderAboveThreshold": 130,
    "DeGiorgiGainRequiresNoLogPileupForRadiusCharge": 184,
    "WeakBilinearGainRequiresNoLogPileupForRadiusCharge": 132,
    "WeakBilinearGainRequiresNoLogPileupForRadiusCharge.ofWeakBilinear": 202,
    "RadiusChargingBadScaleMeasure.ofCKNRestrictedDeGiorgiGain": 206,
    "ExcessDecayTreeCodimFourPacking": 218,
    "CriticalIncrementNoNeckPacking": 216,
    "CKNExcessCarlesonPacking.ofBadScaleMultiplicityControl": 190,
    "CKNExcessCarlesonPacking.ofRadiusChargingBadScaleMeasure": 208,
    "CKNExcessCarlesonPacking.ofExcessDecayTree": 186,
    "CKNExcessCarlesonPacking.ofCriticalIncrementNoNeckPacking": 184,
    "RadiusChargingBadScaleMeasure.ofExcessDropChargesBadCylinderRadius": 210,
    "RadiusChargingBadScaleMeasure.ofFiniteLengthBadSkeletonCharge": 198,
    "RhoAndPointwiseBoundsDoNotGiveCodimFourSublevelVolume": 150,
    "rhoAndPointwiseBounds_doNotGiveCodimFourSublevelVolume": 135,
    "CodimFourSublevelVolumeFromExcess.ofCarlesonPacking": 155,
    "CodimFourSublevelVolumeFromExcess.ofCarlesonMeasure": 154,
    "CKNExcessRegularityScaleSplitWitness.ofCarlesonPacking": 145,
    "enstrophyCKNExcessToRegularityScalePresentation_of_carlesonPacking": 150,
    "CKNExcessRegularityScaleConstructionWitness.ofSplitWitness": 94,
    "EnstrophyRegularityScalePresentation.ofCKNExcessConstructionWitness": 86,
    "enstrophyCKNExcessToRegularityScalePresentation_of_constructionWitness": 94,
    "enstrophyCKNExcessToRegularityScalePresentation_of_splitWitness": 99,
    "EnstrophyCKNExcessLocalSmallnessDoesNotProduceCodimFourPacking": 92,
    "enstrophyCKNExcessLocalSmallness_doesNotProduceCodimFourPacking": 88,
    "EnstrophyCKNExcessLocalSmallnessDoesNotProduceRegularityScalePresentation": 121,
    "enstrophyCKNExcessLocalSmallness_doesNotProduceRegularityScalePresentation": 111,
    "QualitativeCKNDimOneDoesNotGiveCodimFourPacking": 89,
    "LogMinkowskiBadSetModel": 150,
    "LogMinkowskiMultiplicityModel": 152,
    "qualitativeCKNDimOne_doesNot_imply_CodimFourSublevelVolume": 142,
    "logMinkowskiMultiplicity_not_excluded_by_CKNMass": 144,
    "ClassicalCKNBadPackingDoesNotGiveExcessCarlesonPacking": 160,
    "ClassicalCKNBadCylinderCostOnlyCodimThree": 158,
    "classicalCKNBadCylinderCostOnlyCodimThree_of_CKNPacking": 144,
    "classicalCKNBadPacking_doesNotGive_excessCarlesonPacking": 145,
    "ReverseHolderThresholdFeedsExcessCarlesonPacking": 170,
    "NormalizedCKNExcessSublevelCarlesonPacking.ofReverseHolderThreshold": 150,
    "SubcriticalReverseHolderDoesNotFeedExcessCarlesonPacking": 155,
    "subcriticalReverseHolder_doesNotFeed_excessCarlesonPacking": 140,
    "QualitativeOrAsymptoticBadSetDoesNotProduceRegularityScalePresentation": 91,
    "FluxRadonMeasure": 70,
    "ContinuousFluxTestFunction": 65,
    "CubicIncrementFunctional": 60,
    "DuchonRobertFlux": 55,
    "DuchonRobertFlux.toSkeletonMollifiedFlux": 72,
    "DuchonRobertFlux.toSkeletonMollifiedFlux_eq": 78,
    "rescaledIncrementOf": 50,
}

NEXT_ACTIONS = {
    "CubicVectorMeasureCompactness": "Prove the vector-measure compactness theorem for V |V|^2 dγ under the L3 bound.",
    "SignedWeakStarFluxConvergence": "Specialize signed weak-* convergence to continuous test functions C(K, R).",
    "UniformIntegrabilityKillsFlux": "Formalize Vitali/equiintegrability corollary: concentration vanishes and flux tends to zero.",
    "ConcentrationFluxRepresentation": "Connect generalized-YM concentration data to signed flux pushforward.",
    "GeneralizedCubicYoungMeasure": "Keep as rich representation target after vector-measure flux theorem.",
    "RescaledIncrementStrongL2Vanishes": "Prove from local Leray-Hopf L2_t H1_x translation estimate.",
    "CriticalIncrementBound": "Do not assume silently; this is the PDE bridge/CKN frontier.",
    "CriticalIncrementNoCollapsePacking": "Treat as the honest Perelman no-collapse analog: codimension-four regularity-scale packing.",
    "CriticalIncrementNoCollapseNotMerelySupport": "Use as the no-go guard: support localization plus CKN codim-three packing is not enough.",
    "CriticalIncrementNoNeckTheorem": "Only pursue if a bubble/no-neck package can prove critical mass control below the packing target.",
    "SignedToAbsoluteCubicFluxNoNeck": "Positive signed-to-absolute interface, now sequence-bound: add absolute p=3 total-variation and no-neck control for the selected DR flux sequence.",
    "SequenceBoundConcentrationFluxRepresentation": "Bind signed flux convergence to the actual selected DR flux sequence and concentration pushforward, not arbitrary signed measures.",
    "selectedDuchonRobertFluxMeasureSeq": "Use as the source-bound DR flux-measure sequence selected by n_j and ell_j.",
    "SignedToAbsoluteNoNeckRequiresConcentrationFluxRepresentation": "Guard signed-to-absolute claims: signed tests alone cannot form no-neck without the sequence-bound concentration flux representation.",
    "SignedFluxTestsDoNotImplyCriticalIncrementBoundBridge": "No-go guard: signed weak-* DR flux tests do not by themselves pay critical-increment mass.",
    "SignedDRFluxBridgeDoesNotProduceCKNExcessCarlesonPacking": "Cross-lane guard: Track-B signed DR flux identity still does not pay normalized-excess Carleson packing.",
    "signedDRFluxBridgeDoesNotProduceCKNExcessCarlesonPacking_of_signedBridge": "Constructor for the signed-DR-to-Carleson no-go; use when a cross-lane answer confuses signed tests with bad-scale packing.",
    "signedToAbsoluteCubicFluxNoNeck_of_bridge": "Constructor only; keep below the PDE theorem that supplies absolute total variation and no-neck control.",
    "sequenceBoundConcentrationFluxRepresentation_of_collapse": "Constructor for the sequence-bound flux representation from critical bound, ordinary collapse, concentration representation, and selected DR convergence.",
    "signedToAbsoluteNoNeck_requires_concentrationFluxRepresentation": "Constructor for the guard that arbitrary signed convergence is not enough for no-neck.",
    "signedFluxTestsDoNotImplyCriticalIncrementBoundBridge": "Constructor for the cancellation guard; use it to block signed-flux laundering.",
    "DefectSurgeryDoesNotImproveCriticalIncrementBound": "Keep as surgery/localization no-go unless no-neck or quantization is added.",
    "CubicConcentrationBubbleTangentProblem": "Clarify whether increment concentration has a closed PDE tangent class before attempting classification.",
    "regularityScaleLayerCakeBridge_of_codimFourPacking": "Use as the exact positive implication: codim-four packing pays the deterministic layer-cake bridge.",
    "oneScaleEnstrophyCriticalIncrementBound_of_enstrophyPacking_and_layerCakeBridge": "Use as the honest factorization of the enstrophy fork through packing plus layer-cake, not a direct endpoint jump.",
    "QualitativeCKNDimOneDoesNotGiveRegularityScaleLayerCakeBridge": "Use as the direct no-go from qualitative CKN dimension data to the layer-cake bridge.",
    "no_regularityScaleLayerCakeBridge_of_dimOneOnly": "Use as the theorem-name kill on dimension-only CKN shortcuts.",
    "SuitableWeakToCriticalIncrementNoCollapsePackingTarget": "Main positive L3A target: derive codim-four no-collapse packing from suitable-weak/CKN data.",
    "SuitableWeakToRegularityScalePresentationTarget": "First exact positive bridge: turn suitable-weak local-smallness data into RegularityScalePresentation plus codim-four packing.",
    "EnstrophyCKNExcessToRegularityScalePresentationTarget": "Concrete PDE fork: test whether enstrophy plus Galilean-invariant CKN excess can produce the quantitative scale presentation.",
    "CKNExcessRegularityScaleConstructionWitness": "Split positive target: construct rho, prove pointwise scale bounds, and prove codim-four sublevel-volume control from normalized CKN-excess data.",
    "CKNExcessRegularityScaleSplitWitness": "Preferred positive surface: prove the rho, pointwise-bounds, and codim-four volume witnesses separately.",
    "RhoFromNormalizedCKNExcess": "First CKN-excess subproblem: construct the regularity scale rho from normalized excess data with fixed cylinder normalization.",
    "PointwiseScaleBoundsFromEpsilonRegularity": "Second CKN-excess subproblem: turn rho plus epsilon regularity into pointwise velocity/gradient scale bounds.",
    "CodimFourSublevelVolumeFromExcess": "Hardest CKN-excess subproblem: prove codimension-four sublevel-volume control for rho.",
    "NormalizedCKNExcessSublevelCarlesonPacking": "Smallest positive PDE primitive now exposed: prove bad-scale Carleson packing at the codimension-four exponent.",
    "CKNExcessCarlesonPacking": "Alias for the same top target in cylinder-packing language; use in prompts that discuss bad CKN-excess cylinders.",
    "NormalizedExcessSublevelCarlesonMeasure": "Scale-space measure wording of the same Carleson primitive; useful for dyadic/no-neck formulations.",
    "BadScaleMultiplicityControl": "Next smaller candidate: prove bad-scale multiplicity cannot accumulate logarithmically along the CKN skeleton.",
    "RadiusChargingBadScaleMeasure": "New sharp subprimitive: find a finite budget charging each bad cylinder by radius r_Q, not classical r_Q^2 mass.",
    "ExcessDropChargesBadCylinderRadius": "Entropy/drop version of radius charging; the excess drop must pay r_Q along bad tree nodes.",
    "ExcessDropPotentialCandidate": "First split field below excess-drop: name a finite nonnegative scale potential on the normalized-excess tree.",
    "ExcessDropTreeSuperadditivity": "Second split field: parent-child potential inequality strong enough to telescope.",
    "BadNodeRadiusDrop": "Hard split field: each bad normalized-excess node consumes radius r_Q from the potential drop.",
    "ExcessDropTelescopesToRadiusCharging": "Accounting split field: finite/infinite bad-tree telescoping plus bounded overlap gives radius charging.",
    "ExcessDropChargesBadCylinderRadiusSplitWitness": "Preferred next proof surface: potential, tree inequality, bad-node radius drop, and telescoping separated.",
    "RadiusChargingBadScaleMeasure.ofExcessDropSplitWitness": "Adapter from the split excess-drop witness to the radius-charging primitive.",
    "LocalExcessDecayWithoutTelescopingDoesNotChargeRadius": "Guard: local decay estimates do not charge radius unless they telescope over nested bad scales.",
    "ClassicalMassChargeDoesNotDefineExcessDropPotential": "Guard: classical r_Q^2 CKN mass charge cannot be renamed as an r_Q excess-drop potential.",
    "ExcessDropRadiusChargeRequiresPointwiseBadCylinderDrop": "Guard: signed flux or defect data must assign each bad cylinder to a pointwise radius-paying drop.",
    "MassRenormalizationCannotTelescopeAndPayRadius": "Core algebraic no-go: renormalized mass cannot both telescope and upgrade r_Q^2 to r_Q.",
    "NormalizedCKNExcessNotTreeSuperadditive": "Guard: normalized CKN excess detects badness but fails parent-child superadditivity.",
    "UnnormalizedMassTelescopesOnlyRadiusSquared": "Guard: unnormalized CKN/enstrophy/defect mass may telescope but only pays the classical r_Q^2 cost.",
    "SignedFluxDoesNotDefineRadiusDropPotential": "Guard: signed DR/pressure/Mobius flux lacks nonnegative absolute radius budget without no-cancellation.",
    "FreshEnstrophyRadiusDropForBadNormalizedExcess": "Conditional enstrophy primitive: only viable after residual fresh excess and no-inheritance hypotheses are supplied.",
    "FiniteLengthBadSkeletonDensityNoNeck": "Alternative geometric primitive: finite-length bad skeleton with fresh density/no-neck in every bad node.",
    "FreshEnstrophyDropFailsByChildConcentration": "Guard: parent badness can be inherited by child concentration, leaving no fresh enstrophy outside selected children.",
    "CKNBadnessToEnstrophyOnlyR2WithoutScaleInvariantEnergy": "Guard: without scale-invariant local energy, CKN badness yields only r_Q^2 enstrophy, not r_Q.",
    "ResidualFreshExcessForcesFreshEnstrophy": "Residual branch: fresh velocity excess plus scale-invariant energy, pressure localization, and Poincare geometry pays fresh enstrophy.",
    "ChildConcentrationNoLogPileupOrSkeletonCharge": "Inherited branch: child concentration must not repeat logarithmically; otherwise use skeleton/no-neck charge.",
    "BadNodeResidualOrInheritedDichotomy": "Next theorem surface: bad node has residual fresh excess or inherited child concentration with no-log/skeleton charge.",
    "PressureTailEscapeBlocksFreshEnstrophyDrop": "Guard: pressure excess can be inherited or harmonic, so it need not charge fresh velocity-gradient enstrophy.",
    "FiniteLengthBadSkeletonDensityNoNeckStrong": "Strong skeleton route: selected bad nodes cover bad sublevels and pay fresh finite length with bounded overlap.",
    "InheritedBadnessNoChildRadiiContractionFromCKNMass": "No-go: inherited CKN badness controls square cost, not child-radii contraction.",
    "LogPileupInheritedBadTreeModel": "Model obstruction: k*2^k inherited bad nodes have finite r_Q^2 charge but divergent radius length.",
    "ResidualBranchConditionalFreshEnstrophy": "Keep residual branch as a conditional local theorem with fresh excess, energy, pressure localization, and Poincare hypotheses.",
    "PressureInheritanceBlocksChildContraction": "Guard: parent pressure badness may be inherited from child sources or harmonic tails.",
    "InheritedBadTreeCoronaNoNeckSkeleton": "Next skeleton theorem: residual nodes pay enstrophy, inherited nodes pay fresh finite skeleton length with bounded overlap.",
    "DimensionOneSupportDoesNotGiveRadiusCharging": "Guard: qualitative CKN dimension-one support is weaker than finite length and fresh density.",
    "ParabolicBadCenterBetaCarleson": "Geometric carrier below skeleton/no-neck: bad-center beta numbers with Carleson control and lower density.",
    "NormalizedExcessBadCenterSelection": "First beta-Carleson sub-witness: choose bad centers nonadaptively from the normalized-excess tree.",
    "BadCenterNonadaptiveConstructionGuard": "Guard the beta route from adaptive skeleton selection: centers must come from solution/excess data before radius accounting.",
    "ParabolicBadCenterBetaNumberControl": "Hardest beta-Carleson sub-witness: prove parabolic beta-square Carleson control for bad centers.",
    "BadCenterLowerDensityForSelectedNodes": "Density sub-witness: selected bad nodes contain fresh bad-center density for skeleton accounting.",
    "NonadaptiveBadCenterCarrierFromNormalizedExcess": "Concrete carrier split: selected bad nodes, centers, radii, raw-source agreement, coverage, and lower density come from the normalized-excess tree before accounting.",
    "BadCenterParabolicBetaData": "Beta-data interface for the nonadaptive bad-center carrier: parabolic beta numbers against one-dimensional comparison lines.",
    "BadCenterBetaSquareCarlesonDrop": "Hard exposed PDE field: finite NS budget must pay beta-square radius charge over bad centers, not classical r_Q^2 mass.",
    "BadCenterMonotoneFrequencyDrop": "Smallest local proof shape below beta-square Carleson: monotone scale/frequency drop pays beta-square radius and telescopes over selected bad centers.",
    "BadCenterQuantitativeDifferentiationPackage": "Concrete viable source for monotone frequency drop: quantitative differentiation/cone-splitting makes non-flat beta consume a finite scale drop.",
    "BadCenterMonotoneFrequencyDrop.ofQuantitativeDifferentiation": "Adapter from quantitative differentiation/cone-splitting to monotone bad-center frequency drop.",
    "NormalizedMassCannotBeBadCenterFrequencyDrop": "Guard: normalized CKN mass detects badness but is not tree-monotone and only pays the classical radius-squared charge.",
    "EnstrophyFrequencyDropNeedsNSOnlyMonotonicity": "Guard/candidate boundary: enstrophy has finite budget, but scale-normalized enstrophy needs an NS-only monotonicity theorem to become frequency drop.",
    "SignedFluxCannotBeBadCenterFrequencyDrop": "Guard: signed DR/raw Mobius flux is not a nonnegative monotone frequency and can miss beta-length by cancellation.",
    "PressureRecoveryDoesNotGiveBadCenterFrequencyDrop": "Guard: pressure recovery gives upper estimates and nonlocal tails, not a monotone bad-center scale drop.",
    "QualitativeDimensionDoesNotGiveBadCenterFrequencyDrop": "Guard: dimension-one support gives no finite scale-frequency budget, beta-square drop, or same-carrier monotonicity.",
    "BadCenterEventRecurrenceLedgerBridge": "Candidate reuse bridge: event-recurrence weighted-square price could pay beta-square radius if events are identified with bad nodes nonadaptively.",
    "BadCenterEventNodeIdentification": "Event bridge sub-witness: events are generated from and cover the normalized-excess bad-center carrier without post-hoc radius accounting.",
    "BadCenterEventWeightedSquareIdentification": "Event bridge sub-witness: event gain is beta, event weight is node radius, and weighted event price is beta-square radius.",
    "badCenterEventBetaSquarePrefix": "Finite event-ordered bad-center beta-square prefix induced by eventToBadNode.",
    "BadCenterEventPointwiseBetaSquareIdentity": "Concrete pointwise identification: event gain is beta number and event weight is node radius along eventToBadNode.",
    "eventWeightedGainPricePrefix_eq_badCenterEventBetaSquarePrefix": "Closed algebra theorem: pointwise event/bad-center identity makes the event weighted prefix equal the beta-square bad-center event prefix.",
    "BadCenterEventPriceDropIdentification": "Event bridge sub-witness: event raw/recurrence price is a finite same-carrier NS scale drop with event multiplicity counted.",
    "BadCenterEventPriceDropDuhamelIncidenceSource": "Concrete source for the event price-drop field: Duhamel/Bernstein source plus fixed section incidence, identified with selected bad-center sections and same-carrier scale drop.",
    "BadCenterEventPriceDropDuhamelIncidenceSource.eventCertificate": "Adapter producing the existing event recurrence-price certificate from the Duhamel/source plus section-incidence source.",
    "BadCenterEventPriceDropDuhamelIncidenceSource.weightedEventPricePrefix_le_budget": "Closed event-side algebra: the concrete source bounds every weighted-square event prefix by the declared event price budget.",
    "badCenterEventBetaSquarePrefix_le_eventBudget_ofDuhamelIncidenceSource": "Closed finite-prefix bridge: pointwise radius/beta identity plus Duhamel/incidence source bounds the bad-center beta-square event prefix by the event budget.",
    "BadCenterBetaSquareCarlesonDrop.ofEventBudgetedPrefixData": "Non-circular adapter: finite event prefix budget plus domination and coverage fields produce the beta-square Carleson drop.",
    "BadCenterBetaSquareCarlesonDrop.ofSameTreeEventBudgetedPrefixData": "Same-tree specialization: same-tree incidence supplies weighted-square domination for the non-circular beta-drop adapter.",
    "BadCenterEventBudgetedBetaSquarePrefixBridge.ofPointwiseDuhamelCoverageNonCircular": "Non-circular bridge constructor: builds the beta-square drop from prefix data instead of taking it as an input.",
    "event_weighted_gain_price_prefix_le_budget": "Closed event certificate theorem: weighted event-gain price prefixes are bounded by the event price budget.",
    "BadCenterEventNonadaptiveWeightedSquareDomination": "Smallest remaining event bridge: fixed incidence must make weighted-square event prefixes dominate selected bad-center beta-square sums with bounded multiplicity.",
    "SameTreeNonadaptiveEventIncidenceCarleson": "New sharp 100x primitive: construct same-tree nonadaptive event incidence with finite event budget, cofinal scale prefixes, and bounded fanout for beta-square radius.",
    "BadCenterEventNonadaptiveWeightedSquareDomination.ofSameTreeIncidence": "Adapter: same-tree event incidence directly supplies the weighted-square domination interface.",
    "SameTreeEventIncidenceIndependentBudgetSplitWitness": "Preferred 100x split witness: same-tree incidence plus an independent finite NS budget, preventing event-price-as-target-sum tautology.",
    "IndependentSameTreeEventBudgetWitness": "Hard budget primitive: event prices must be bounded by a finite Navier-Stokes carrier before identifying them with beta-square radius mass.",
    "DuhamelSameTreeIndependentEventBudgetCandidate": "Concrete 100x source candidate: Duhamel/Bernstein reserve on the same bad-center stopping tree pays event weighted-gain prices before beta accounting.",
    "FreshFrequencyEventSameTreeLock": "Best current 100x bridge candidate: nonflat bad-center beta is paid by fresh scale-r^-1 Duhamel/Bernstein packets on the same stopping tree, with inherited/flat cases explicitly routed away.",
    "FreshFrequencyPrefixDominationFromSubprimitives": "Exact choke-point below the lock: assemble finite-prefix domination from fresh-packet dichotomy, beta payment, bounded fanout, pressure same-carrier, and flat skeleton controls.",
    "NonflatBadNodeFreshPacketDichotomy": "First hard subprimitive: a nonflat bad node must be inherited, flat, or have a fresh comparable-frequency packet chosen before radius accounting.",
    "FreshPacketGainPaysNonflatBeta": "Second hard subprimitive: the selected fresh packet gain must pay nonflat beta without pressure leakage or inherited packet reuse.",
    "FreshFrequencyBoundedFanoutNoLogReuse": "Third hard subprimitive: one fresh event cannot be reused across logarithmic descendants or same-scale bad-center multiplicity.",
    "DuhamelBernsteinFreshFrequencyEvent": "Concrete event datum for the fresh-frequency route; its price must be localized enstrophy/Duhamel square budget, not the target beta-radius sum.",
    "FreshFrequencyPressureDuhamelSameCarrierLock": "Companion lock forcing pressure tails and Duhamel errors onto the same fresh-frequency event carrier.",
    "FreshFrequencyFlatBadCenterSkeletonLock": "Companion lock routing low-beta flat bad centers to finite skeleton length instead of pretending beta-square pays radius.",
    "BadNormalizedExcessDoesNotAutomaticallyCreateFreshFrequencyEvent": "Guard: normalized-excess badness may be inherited or flat; fresh frequency events need a theorem, not vocabulary.",
    "FreshFrequencyEventRouteAvoidsEventPerNodeTautology": "Anti-smuggling guard: the route is noncircular only when events are generated by fresh packets and budgeted by independent PDE reserves.",
    "SameTreePrefixDominationPrimitive.ofFreshFrequencyEventSameTreeLock": "Adapter: fresh-frequency same-tree lock supplies the finite-prefix domination primitive.",
    "SameTreeDuhamelBudgetRemainingObligations": "Current narrow PDE packet: scale truncations, bad-center incidence geometry, same-reserve pressure, scale-limit persistence, cofinality, and prefix domination.",
    "SameTreePrefixDominationPrimitive": "Current exact theory-building target: finite scale-truncation beta-radius sums must be dominated by same-tree event prefixes before the endpoint Carleson limit is taken.",
    "SameTreeSelectedTreeControlPrimitive": "Post-prefix control target: use the scale presentation and finite-prefix domination to control the selected bad tree without restating endpoint beta-Carleson.",
    "sameTreePrefixDominationProp_ofPrimitive": "Adapter only: projects the explicit finite-prefix primitive to the raw Prop consumed by same-tree constructors.",
    "sameTreeSelectedTreeControlProp_ofPrimitive": "Adapter only: projects selected-tree control to the raw tree-control Prop; do not count this as PDE content.",
    "SameTreeDuhamelBudgetRemainingObligations.toSameTreeIncidence": "Constructor: the remaining Duhamel same-tree obligation packet yields the same-tree incidence primitive.",
    "PriceDropDuhamelSourceDoesNotFillSameTreeObligations": "Guard: the existing price-drop Duhamel source closes event prefixes but does not supply the remaining bad-center scale, incidence, pressure, and prefix-domination fields.",
    "BadCenterEventIncidenceGeometry.ofPointwiseSingletonIncidence": "Positive local constructor: eventToBadNode singleton incidence plus pointwise beta/radius identity supplies the incidence-geometry witness without asserting prefix domination.",
    "SameTreeDuhamelBudgetRemainingObligations.ofPointwiseSingletonIncidence": "Positive assembly: pointwise singleton incidence fills the same-tree obligation packet once scale, pressure, overlap, cofinality, and prefix domination are supplied.",
    "SameTreeNonadaptiveEventIncidenceCarleson.ofPointwiseSingletonDuhamelSource": "Direct route: pointwise identity plus Duhamel source builds same-tree incidence while leaving scale/pressure/prefix fields explicit.",
    "DuhamelSameTreeIndependentEventBudgetCandidate.ofPriceDropDuhamelIncidenceSource": "Constructor: existing Duhamel/incidence source gives the concrete same-tree budget candidate once pressure and scale-limit compatibility are supplied.",
    "SameTreeEventIncidenceIndependentBudgetSplitWitness.ofDuhamelSameTreeBudget": "Constructor: Duhamel same-tree budget plus scale truncations and incidence geometry builds the independent-budget split witness.",
    "SameTreeNonadaptiveEventIncidenceCarleson.ofPriceDropDuhamelIncidenceSource": "Direct positive assembly: existing Duhamel/incidence source plus scale truncation, incidence geometry, pressure-reserve, and scale-limit fields gives same-tree incidence.",
    "DuhamelReserveCanBeShellOnlyNotBadCenterBudget": "Guard: a finite Duhamel reserve can remain shell/process accounting unless its sections are identified with the normalized-excess bad-center tree.",
    "DuhamelReserveReuseCanMissBadCenterMultiplicity": "Guard: a finite reserve can be reused across many bad centers without bounded fanout/multiplicity on bad-center incidence.",
    "PressureDuhamelLeakageBlocksSameTreeBudget": "Guard: pressure tails and Duhamel residuals must stay on the same carrier or the reserve cannot telescope over selected bad centers.",
    "EventPerBadNodeConstructionIsTautological": "Guard: event-per-bad-node accounting is circular unless the event budget is independently finite before the bad-center Carleson target is introduced.",
    "PressureDuhamelSameCarrierLock": "Required compatibility primitive: pressure and Duhamel errors must be assigned to the same bad-center event stream, not matched afterward.",
    "FlatBadCenterSkeletonLengthControl": "Low-beta alternative: flat bad-center nodes need finite skeleton length control so beta-square estimates can imply radius packing.",
    "ChainwiseBetaDropDoesNotGiveGlobalBetaCarleson": "Guard: chain-wise quantitative differentiation can miss same-scale logarithmic bad-center multiplicity.",
    "EventizedParabolicBetaCarlesonQuantStratConstructiveData.ofSameTreeIncidence": "Adapter from same-tree incidence, same-carrier pressure/Duhamel lock, monotone beta carrier, and flat-node control to eventized constructive data.",
    "BadCenterScaleTruncationPresentation": "Subwitness for eventized quant strat: finite bad-center scale truncations whose beta-square partial sums recover the full Carleson sum.",
    "BadCenterEventIncidenceGeometry": "Subwitness for eventized quant strat: fixed event-to-bad-node incidence with radius/gain comparability and bounded fanout.",
    "BadCenterEventizedMonotoneBetaCarrier": "Subwitness for eventized quant strat: finite monotone beta carrier whose drops absorb pressure/Duhamel errors and block log pileup.",
    "BadCenterEventizedMonotoneBetaCarrier.ofQuantitativeDifferentiation": "Adapter: quantitative differentiation supplies the monotone beta carrier part of the eventized route, after Duhamel same-carrier compatibility.",
    "QuantitativeDifferentiationDoesNotSupplyEventIncidence": "Guard: quantitative differentiation can supply beta drops but not event prefixes, scale cofinality, or bounded event/bad-node incidence.",
    "EventizedParabolicBetaCarlesonQuantitativeStratification": "10x candidate theorem surface: construct event sections from the bad-center quantitative-stratification tree so event prices become beta-Carleson control.",
    "EventizedParabolicBetaCarlesonQuantStratSplitWitness": "Split witness for the 10x candidate: scale truncations + incidence geometry + monotone beta carrier imply eventized quant strat.",
    "EventizedParabolicBetaCarlesonQuantStratConstructiveData": "Non-circular assembly data for the 10x candidate: scale truncations, incidence geometry, monotone beta carrier, and explicit domination fields without storing the endpoint theorem.",
    "BadCenterEventNonadaptiveWeightedSquareDomination.ofEventizedConstructiveData": "Constructor from non-circular eventized quant-strat data to the weighted-square domination primitive.",
    "EventizedParabolicBetaCarlesonQuantitativeStratification.ofConstructiveData": "Constructor from non-circular assembly data to the named eventized beta-Carleson quantitative-stratification target.",
    "EventizedParabolicBetaCarlesonQuantitativeStratification.ofSplitWitness": "Adapter from the split witness to eventized parabolic beta-Carleson quantitative stratification.",
    "BadCenterEventNonadaptiveWeightedSquareDomination.ofEventizedQuantStrat": "Adapter from eventized parabolic quantitative stratification to the nonadaptive weighted-square domination primitive.",
    "EventizedQuantStratNotSuppliedByEventAlgebraAlone": "Guard: event prefix algebra and section incidence do not construct the bad-center quantitative-stratification carrier.",
    "ScaleTruncationCofinalityNotSuppliedByEventPrefixAlone": "Guard: finite event prefixes need not be cofinal with scale truncations of the selected normalized-excess bad-center tree.",
    "SectionIncidenceDoesNotGiveBadCenterIncidenceGeometry": "Guard: fixed recurrence section incidence is not automatically physical bad-center incidence geometry with radius/gain comparability and bounded fanout.",
    "MonotoneBetaCarrierNotSuppliedByCKNMassOrEventAlgebra": "Guard: classical CKN mass and event prefix algebra do not construct the monotone beta carrier needed to price non-flat bad-center geometry.",
    "BadCenterEventBudgetedBetaSquarePrefixBridge": "Budgeted event-prefix bridge: finite prefix algebra plus coverage/multiplicity witnesses produces the beta-square Carleson drop.",
    "BadCenterEventBudgetedBetaSquarePrefixBridge.ofPointwiseDuhamelCoverage": "Constructor from pointwise identity, Duhamel source, coverage, domination, and tree-control witnesses to the budgeted event-prefix bridge.",
    "EventPrefixBudgetDoesNotImplyBadCenterBetaCarleson": "Guard: finite event-prefix budget alone does not imply bad-center beta-Carleson without carrier coverage and bounded event fanout.",
    "PostHocEventBadNodeMatchingIsCircular": "Guard: matching events to bad nodes after radius accounting is circular and cannot supply nonadaptive weighted-square domination.",
    "EventBadNodeUnboundedMultiplicityObstruction": "Guard: one bounded event cannot be reused to pay arbitrarily many selected bad nodes without bounded incidence multiplicity.",
    "BadCenterEventPriceDropIdentification.ofDuhamelIncidenceSource": "Adapter from the concrete Duhamel/incidence source to the bad-center event price-drop witness.",
    "BadCenterEventRecurrenceBridgeSplitWitness": "Split witness for reusing event-recurrence weighted-square accounting as a bad-center monotone frequency drop.",
    "BadCenterEventRecurrenceLedgerBridge.ofSplitWitness": "Adapter packing event-node, weighted-square, and same-carrier price-drop witnesses into the event ledger bridge.",
    "BadCenterMonotoneFrequencyDrop.ofEventRecurrenceLedgerBridge": "Adapter from the event-recurrence ledger bridge to bad-center monotone frequency drop.",
    "EventLedgerWithoutBadCenterIdentificationDoesNotCloseFrequencyDrop": "Guard: event ledger algebra alone does not identify eventGain with beta, eventWeight with radius, or event price with same-carrier drop.",
    "EventPrecertificateWithoutBadCenterCarrierDoesNotClosePriceDrop": "Guard: event pre-certificate plus incidence is still insufficient unless tied to selected bad-center sections and same-carrier NS scale drop.",
    "BadCenterBetaSquareCarlesonDrop.ofMonotoneFrequencyDrop": "Adapter from a monotone frequency/scale drop to the beta-square Carleson drop.",
    "BadCenterBetaSquareCarlesonDrop.ofEventRecurrenceLedgerBridge": "Direct adapter from event-recurrence bad-center identification to beta-square Carleson drop.",
    "NSBadCenterBetaCarlesonSplitWitness": "Concrete split witness packaging the nonadaptive carrier, beta data, beta-square drop, and geometric beta-Carleson carrier.",
    "NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier": "Adapter from the concrete nonadaptive carrier to the existing selected bad-center interface.",
    "BadCenterNonadaptiveConstructionGuard.ofNonadaptiveCarrier": "Adapter exposing the carrier as the nonadaptive construction guard.",
    "BadCenterLowerDensityForSelectedNodes.ofNonadaptiveCarrier": "Adapter exposing carrier lower density as the selected-node density witness.",
    "ParabolicBadCenterBetaNumberControl.ofBetaSquareDrop": "Adapter from beta data plus beta-square drop to beta-number control.",
    "ParabolicBadCenterBetaCarleson.ofSubwitnesses": "Adapter packing selection, nonadaptive guard, beta control, and lower density into the geometric beta-Carleson carrier.",
    "ParabolicRectifiableReifenbergForBadCenters": "Accounting bridge: beta-Carleson plus density gives finite length, fresh density, and bounded corona overlap.",
    "BadCenterRectifiableBridgeWitness": "Expose the rectifiable/Reifenberg bridge as its own target between beta-Carleson estimates and finite-length skeleton accounting.",
    "NSBadCenterBetaCarlesonEstimate": "Hard PDE primitive: derive bad-center beta-Carleson from NS structure, not from adaptive skeleton choice.",
    "QuantitativeStratificationSkeletonPackage": "Candidate solve path: NS beta-Carleson plus rectifiable-Reifenberg bridge yields inherited bad-tree skeleton/no-neck.",
    "AdaptiveSkeletonChoiceWouldSmuggleRadiusCharge": "Guard: choosing a skeleton after seeing the bad tree merely encodes the desired radius charge.",
    "CKNSupportDoesNotGiveBadCenterBetaCarleson": "Guard: support localization and qualitative dimension do not give beta-square Carleson or selected-node density.",
    "LogPileupBadCentersEvadeCarlesonWithoutBetaControl": "Guard: log-pileup bad centers survive finite CKN mass unless beta-Carleson/flatness blocks them.",
    "ExcessDropChargesBadCylinderRadiusSplitWitness.ofFreshEnstrophyRadiusDrop": "Adapter from fresh enstrophy radius drop to the split excess-drop witness.",
    "RadiusChargingBadScaleMeasure.ofFiniteLengthBadSkeletonDensityNoNeck": "Adapter from finite-length skeleton density/no-neck to radius charging.",
    "RadiusChargingBadScaleMeasure.ofFiniteLengthBadSkeletonDensityNoNeckStrong": "Adapter from the strong skeleton density/no-neck route to radius charging.",
    "RadiusChargingBadScaleMeasure.ofInheritedBadTreeCoronaNoNeckSkeleton": "Adapter from inherited bad-tree corona/no-neck skeleton to radius charging.",
    "InheritedBadTreeCoronaNoNeckSkeleton.ofQuantitativeStratification": "Adapter from quantitative stratification skeleton package to inherited bad-tree corona/no-neck.",
    "FiniteLengthBadSkeletonDensityNoNeckStrong.ofBadCenterBetaCarleson": "Adapter from beta-Carleson plus rectifiable bridge to strong finite-length skeleton.",
    "ParabolicBadCenterBetaCarleson.ofNSBadCenterBetaCarlesonEstimate": "Projection from the NS beta-Carleson estimate to its geometric bad-center carrier.",
    "NSBadCenterBetaCarlesonEstimate.ofSplitWitness": "Constructor from the concrete carrier/beta-data/beta-square-drop split to the NS beta-Carleson estimate.",
    "FiniteLengthBadSkeletonCharge": "Geometric version of radius charging; stronger than dimension one because it requires finite parabolic length charge.",
    "DyadicBadScaleCover": "Mathlib-backed finite-cover substrate for bad sets at dyadic scales.",
    "DyadicBadScaleSeparatedPacking": "Mathlib-backed separated-packing substrate using packingNumber; counting layer only.",
    "FiniteDyadicCarlesonPacking": "Finite dyadic package combining cover/packing substrate with the PDE Carleson sum field.",
    "BadScaleMultiplicityControl.ofFiniteDyadicCarlesonPacking": "Adapter from finite dyadic Carleson package to bad-scale multiplicity control.",
    "finite_badScaleCover_of_compact": "Proved mathlib wrapper: compact bad sets admit finite metric covers at positive radius.",
    "CKNRestrictedDeGiorgiPositiveGain": "Candidate analytic source of radius charging from older Vasseur/De Giorgi notes: locate beta > 0 under CKN restriction.",
    "CKNRestrictedDeGiorgiGainRulesOutLogPileup": "Only promote the De Giorgi gain if it also excludes logarithmic bad-scale pileup.",
    "PureLerayDeGiorgiProductionBoundDoesNotGivePositiveGain": "Guard: pure Leray bounds make production finite but do not give the beta > 0 superlinear measure recursion or radius charge.",
    "pureLerayDeGiorgiProductionBound_doesNotGive_positiveGain": "Constructor for the beta<=0 De Giorgi no-go from pure Leray production control.",
    "CKNRestrictionOnlyNoDerivedDeGiorgiGain": "New no-go from GPT-5.5: CKN restriction plus normalized excess does not derive beta>0 or radius charge.",
    "cknRestrictionOnly_doesNotDerive_deGiorgiPositiveGain": "Constructor for the CKN-restriction-only De Giorgi no-go.",
    "LocalizedProductionLevelSetGain": "Actual analytic input needed by the De Giorgi fork: production on high-level sets gains a positive measure/energy power.",
    "ProductionReverseHolderAboveThreshold": "Concrete sufficient route: production coefficient reverse Holder strictly above q=5/2, giving beta=2/3-5/(3q)>0.",
    "WeakBilinearDeGiorgiProductionNorm": "Possible Vasseur-style intermediate: truncation-pairing norm weaker than global L9/4 but still supplying positive De Giorgi gain.",
    "EnergyDivFreeDeGiorgiGainIsTaoVulnerable": "Tao averaged-NS guard: energy + div-free transport cancellation + interpolation cannot be the unrestricted production-gain mechanism.",
    "energyDivFreeDeGiorgiGain_isTaoVulnerable": "Constructor for the Tao-vulnerable De Giorgi gain guard.",
    "DeGiorgiProductionCoefficientThreshold": "Exponent ledger for the honest production term: beta>0 requires coefficient integrability strictly above q=5/2.",
    "WeakBilinearDeGiorgiProductionNorm_NotDerivedFromEnergy": "No-go guard: weak bilinear positive production gain is not derived from energy, CKN restriction, or transport cancellation alone.",
    "weakBilinearDeGiorgiProductionNorm_notDerivedFromEnergy": "Constructor for the weak-bilinear-not-derived production no-go.",
    "TransportGainDoesNotControlStretchingProduction": "Guard: transport/cutoff De Giorgi gain cannot be transferred to the honest stretching production term.",
    "TaoAveragedNSSieveForProductionGain": "Tao averaged-NS sieve guard for production-gain claims based only on energy cancellation and upper bounds.",
    "PositiveDeGiorgiGainDoesNotTelescopeBadScales": "Guard: even a true positive De Giorgi recursion still needs an excess-drop/no-log finite radius budget.",
    "LocalizedProductionLevelSetGain.ofWeakBilinearProductionNorm": "Adapter from an explicit weak-bilinear beta>0 truncation norm to localized production level-set gain.",
    "LocalizedProductionLevelSetGain.ofReverseHolderAboveThreshold": "Adapter from above-threshold production reverse Holder to localized production level-set gain.",
    "DeGiorgiGainRequiresNoLogPileupForRadiusCharge": "Guard: even positive De Giorgi gain needs a no-log-pileup/excess-drop bridge before radius charging.",
    "WeakBilinearGainRequiresNoLogPileupForRadiusCharge": "Guard: weak-bilinear positive gain still needs no-log-pileup/excess-drop before radius charging.",
    "WeakBilinearGainRequiresNoLogPileupForRadiusCharge.ofWeakBilinear": "Constructor for the weak-bilinear gain plus no-log-pileup/excess-drop bridge guard.",
    "RadiusChargingBadScaleMeasure.ofCKNRestrictedDeGiorgiGain": "Adapter from CKN-restricted De Giorgi gain plus no-log-pileup to radius charging.",
    "ExcessDecayTreeCodimFourPacking": "Concrete CKN/excess route: build a decay tree and prove Carleson length for bad nodes.",
    "CriticalIncrementNoNeckPacking": "Perelman-style route made explicit: no-neck is useful only if it outputs the Carleson packing field.",
    "CKNExcessCarlesonPacking.ofBadScaleMultiplicityControl": "Adapter from dyadic multiplicity control to the normalized-excess Carleson primitive.",
    "CKNExcessCarlesonPacking.ofRadiusChargingBadScaleMeasure": "Direct adapter from the radius-charging theorem to normalized-excess Carleson packing.",
    "CKNExcessCarlesonPacking.ofExcessDecayTree": "Adapter from an excess-decay tree theorem to the normalized-excess Carleson primitive.",
    "CKNExcessCarlesonPacking.ofCriticalIncrementNoNeckPacking": "Adapter from a no-neck packing theorem to the normalized-excess Carleson primitive.",
    "RadiusChargingBadScaleMeasure.ofExcessDropChargesBadCylinderRadius": "Adapter from entropy/excess-drop radius charging to the radius-charging measure primitive.",
    "RadiusChargingBadScaleMeasure.ofFiniteLengthBadSkeletonCharge": "Adapter from finite-length skeleton charge to radius charging.",
    "RhoAndPointwiseBoundsDoNotGiveCodimFourSublevelVolume": "Guard: rho construction plus pointwise epsilon-regularity still lacks the bad-scale packing theorem.",
    "rhoAndPointwiseBounds_doNotGiveCodimFourSublevelVolume": "Constructor for the rho/pointwise-to-volume no-go guard.",
    "CodimFourSublevelVolumeFromExcess.ofCarlesonPacking": "Adapter from the Carleson packing primitive to the codimension-four sublevel-volume field.",
    "CodimFourSublevelVolumeFromExcess.ofCarlesonMeasure": "Same adapter under scale-space measure wording.",
    "CKNExcessRegularityScaleSplitWitness.ofCarlesonPacking": "Pack rho, pointwise bounds, and Carleson packing into the split regularity-scale witness.",
    "enstrophyCKNExcessToRegularityScalePresentation_of_carlesonPacking": "Direct Lean route: Carleson packing plus rho and pointwise bounds closes the enstrophy/CKN-excess target.",
    "CKNExcessRegularityScaleConstructionWitness.ofSplitWitness": "Pack the three split PDE witnesses into the existing regularity-scale construction record.",
    "EnstrophyRegularityScalePresentation.ofCKNExcessConstructionWitness": "Adapter from the split construction witness to the enstrophy regularity-scale presentation.",
    "enstrophyCKNExcessToRegularityScalePresentation_of_constructionWitness": "Positive constructor once the split rho/bounds/packing witness is supplied; swarm the fields, not the wrapper.",
    "enstrophyCKNExcessToRegularityScalePresentation_of_splitWitness": "Best constructor target after proving the split witnesses.",
    "EnstrophyCKNExcessLocalSmallnessDoesNotProduceCodimFourPacking": "Guard the enstrophy/excess lane: local-smallness data alone still lacks rho, pointwise scale bounds, and codim-four sublevel-volume control.",
    "enstrophyCKNExcessLocalSmallness_doesNotProduceCodimFourPacking": "Constructor for the local-smallness-to-packing guard; keep it between the excess bridge and the scale-presentation target.",
    "EnstrophyCKNExcessLocalSmallnessDoesNotProduceRegularityScalePresentation": "Stronger guard: the local-smallness shell does not construct the full quantitative RegularityScalePresentation.",
    "enstrophyCKNExcessLocalSmallness_doesNotProduceRegularityScalePresentation": "Constructor for the local-smallness-to-regularity-scale-presentation guard.",
    "QualitativeCKNDimOneDoesNotGiveCodimFourPacking": "Keep as the log-Minkowski obstruction separating support localization from critical packing.",
    "LogMinkowskiBadSetModel": "Countermodel shape: dimension-one CKN bad set with r^4 log(1/r) neighborhoods kills uniform codim-four volume.",
    "LogMinkowskiMultiplicityModel": "Dyadic obstruction: classical r^2 costs can be summable while Carleson length diverges logarithmically.",
    "qualitativeCKNDimOne_doesNot_imply_CodimFourSublevelVolume": "Constructor for the log-Minkowski obstruction model.",
    "logMinkowskiMultiplicity_not_excluded_by_CKNMass": "Constructor for the dyadic log-multiplicity obstruction.",
    "ClassicalCKNBadPackingDoesNotGiveExcessCarlesonPacking": "Guard the new Carleson primitive from being paid by classical CKN codim-three bad-cylinder packing.",
    "ClassicalCKNBadCylinderCostOnlyCodimThree": "Exponent guard: classical CKN pays r^2 per bad cylinder; the target needs an r-cost Carleson law.",
    "classicalCKNBadCylinderCostOnlyCodimThree_of_CKNPacking": "Constructor for the r^2-versus-r no-go surface.",
    "classicalCKNBadPacking_doesNotGive_excessCarlesonPacking": "Constructor for the classical CKN packing versus normalized-excess Carleson no-go.",
    "ReverseHolderThresholdFeedsExcessCarlesonPacking": "Candidate Gehring/reverse-Holder route into the Carleson primitive; requires threshold exponent and same-rho sublevel binding.",
    "NormalizedCKNExcessSublevelCarlesonPacking.ofReverseHolderThreshold": "Adapter from a fully specified reverse-Holder threshold mechanism to normalized-excess Carleson packing.",
    "SubcriticalReverseHolderDoesNotFeedExcessCarlesonPacking": "Guard: reverse Holder below q=5/2 does not pay codimension-four Carleson packing.",
    "subcriticalReverseHolder_doesNotFeed_excessCarlesonPacking": "Constructor for the subcritical reverse-Holder-to-Carleson guard.",
    "QualitativeOrAsymptoticBadSetDoesNotProduceRegularityScalePresentation": "Use as the shortcut guard: asymptotic/qualitative bad-set control is not the quantitative regularity-scale presentation.",
    "DuchonRobertFlux.toSkeletonMollifiedFlux": "Use as the adapter from the L3A DR carrier to the defect-calculus skeleton flux primitive.",
    "DuchonRobertFlux.toSkeletonMollifiedFlux_eq": "Keep as the theorem-wise guard that L3A DR flux is the skeleton mollifiedFlux, not an unrelated opaque placeholder.",
}


@dataclass
class L3AWorkmapItem:
    name: str
    score: int
    status: str
    kind: str
    file: str
    line: int | None
    reason: str
    next_action: str


def _load_json(path: Path) -> object:
    return json.loads(path.read_text())


def _decl_rows() -> list[dict]:
    idx = _load_json(DECL_INDEX)
    graph_rows = _artifact_status_by_name()
    if not isinstance(idx, dict):
        return [dict(row, name=name) for name, row in graph_rows.items()]
    decls = idx.get("decls", {})
    rows: list[dict] = []
    if isinstance(decls, dict):
        for name, entries in decls.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                file_name = str(entry.get("file", ""))
                if L3A_FILE in file_name:
                    row = dict(entry)
                    row["name"] = name
                    rows.append(row)
    elif isinstance(decls, list):
        for entry in decls:
            if isinstance(entry, dict) and L3A_FILE in str(entry):
                rows.append(entry)
    seen = {str(row.get("name", "")) for row in rows}
    for name, graph_row in graph_rows.items():
        if name not in seen:
            row = dict(graph_row)
            row["name"] = name
            rows.append(row)
    return rows


def _artifact_status_by_name() -> dict[str, dict]:
    if not ARTIFACT_GRAPH.exists():
        return {}
    graph = _load_json(ARTIFACT_GRAPH)
    if not isinstance(graph, dict):
        return {}
    out: dict[str, dict] = {}
    for node in graph.get("@graph", []):
        if not isinstance(node, dict):
            continue
        if L3A_FILE not in str(node.get("path", "")):
            continue
        name = str(node.get("name", ""))
        if name:
            out[name] = node
    return out


def _keyword_score(name: str) -> tuple[int, list[str]]:
    score = 0
    hits: list[str] = []
    exact_hits = {key for key in KEYWORD_WEIGHTS if key == name}
    for key, weight in KEYWORD_WEIGHTS.items():
        if exact_hits and key not in exact_hits and any(key in hit for hit in exact_hits):
            continue
        if key == name or key in name:
            score += weight
            hits.append(key)
    return score, hits


def _status_score(status: str) -> int:
    return {
        "open_obligation": 45,
        "receipt_interface": 35,
        "declaration": 25,
        "unclosed_proof_gap": 25,
        "closed_theorem": 15,
    }.get(status, 10)


def _name_tokens(name: str) -> set[str]:
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name.replace(".", " ")).split()
    out: set[str] = set()
    stop = {
        "of",
        "the",
        "and",
        "or",
        "to",
        "from",
        "not",
        "does",
        "give",
        "supplied",
        "by",
    }
    for part in parts:
        token = re.sub(r"[^A-Za-z0-9]+", "", part).lower()
        if len(token) >= 3 and token not in stop:
            out.add(token)
    return out


def _jaccard(left: set[str], right: set[str]) -> float:
    return 1.0 - jaccard_distance(left, right)


def build_basin_diagnostics(items: list[L3AWorkmapItem], *, top_n: int = 80) -> dict:
    """Route-selection diagnostics only; not mathematical evidence."""
    front = items[:top_n]
    by_name = {item.name: item for item in items}
    token_by_name = {item.name: _name_tokens(item.name) for item in items}

    neighborhoods: dict[str, list[dict]] = {}
    for anchor in ROUTE_ANCHORS:
        anchor_tokens = token_by_name.get(anchor) or _name_tokens(anchor)
        rows: list[dict] = []
        for item in front:
            sim = _jaccard(anchor_tokens, token_by_name[item.name])
            if item.name == anchor or sim >= 0.18:
                rows.append({
                    "name": item.name,
                    "score": item.score,
                    "token_jaccard": round(sim, 4),
                })
        rows.sort(key=lambda row: (-row["token_jaccard"], -row["score"], row["name"]))
        neighborhoods[anchor] = rows[:18]

    anchor_overlaps: list[dict] = []
    for i, left in enumerate(ROUTE_ANCHORS):
        left_names = {row["name"] for row in neighborhoods.get(left, [])}
        for right in ROUTE_ANCHORS[i + 1:]:
            right_names = {row["name"] for row in neighborhoods.get(right, [])}
            overlap = _jaccard(left_names, right_names)
            if overlap:
                anchor_overlaps.append({
                    "left": left,
                    "right": right,
                    "neighborhood_jaccard": round(overlap, 4),
                    "shared": sorted(left_names & right_names)[:12],
                })
    anchor_overlaps.sort(key=lambda row: -row["neighborhood_jaccard"])

    target_mass = sum(max(item.score, 0) for item in front) or 1
    n_obs = max(int(target_mass), 2)
    route_model_penalties: list[dict] = []
    for anchor in ROUTE_ANCHORS:
        rows = neighborhoods.get(anchor, [])
        names = {row["name"] for row in rows}
        covered_mass = sum(max(by_name[name].score, 0) for name in names if name in by_name)
        uncovered_ratio = max((target_mass - covered_mass) / target_mass, 1e-9)
        k_params = max(len(rows), 1)
        # BIC-shaped route penalty: lower is better, but this is a graph
        # selection heuristic, not a likelihood claim. Use weighted score
        # mass as the effective observation count so tiny underfit routes do
        # not win just because their parameter count is small.
        bic_like = n_obs * math.log(uncovered_ratio) + k_params * math.log(n_obs)
        route_model_penalties.append({
            "anchor": anchor,
            "covered_mass": covered_mass,
            "coverage_ratio": round(covered_mass / target_mass, 4),
            "complexity": k_params,
            "bic_like_penalty": round(bic_like, 4),
            "underfit_warning": covered_mass / target_mass < 0.05,
            "top_neighbors": [row["name"] for row in rows[:8]],
        })
    route_model_penalties.sort(key=lambda row: row["bic_like_penalty"])

    return {
        "method": (
            "Jaccard token neighborhoods plus BIC-shaped coverage/complexity "
            "penalty for route selection only; effective N is weighted score "
            "mass, not theorem evidence."
        ),
        "route_anchors": ROUTE_ANCHORS,
        "neighborhoods": neighborhoods,
        "anchor_overlaps": anchor_overlaps[:24],
        "route_model_penalties": route_model_penalties,
    }


def build_native_primitive_surface() -> dict:
    """Small pointer to repo-native primitives relevant to this workmap."""
    surface = build_primitive_tick_surface(
        query_terms=NATIVE_PRIMITIVE_QUERY_TERMS,
        top_n=12,
        per_bucket=4,
    )
    return {
        "source": "src.ztare.research_director.primitive_tick_surface",
        "query_terms": surface.query_terms,
        "ok": surface.ok,
        "warnings": surface.warnings,
        "top_hits": [asdict(hit) for hit in surface.top_hits],
        "bucket_hits": {
            name: [asdict(hit) for hit in hits]
            for name, hits in surface.buckets.items()
            if hits
        },
    }


def build_external_reference_surface(items: list[L3AWorkmapItem]) -> dict:
    """Map external papers/algorithms to local PDE route basins.

    This is deliberately a routing instrument. A paper match can make a local
    target more worth reading or cold-shotting, but it cannot validate the PDE
    implication.
    """
    by_name = {item.name: item for item in items}
    ranks = {item.name: rank + 1 for rank, item in enumerate(items)}
    mapped: list[dict] = []
    for ref in EXTERNAL_REFERENCE_SURFACE:
        local_rows: list[dict] = []
        for name in ref["local_mapping"]:
            item = by_name.get(name)
            local_rows.append({
                "name": name,
                "present": item is not None,
                "rank": ranks.get(name),
                "score": item.score if item else None,
                "next_action": item.next_action if item else None,
            })
        present_scores = [row["score"] for row in local_rows if row["score"] is not None]
        mapped.append({
            **ref,
            "local_rows": local_rows,
            "mapped_present_count": sum(1 for row in local_rows if row["present"]),
            "best_local_score": max(present_scores) if present_scores else None,
            "best_local_rank": min(
                (row["rank"] for row in local_rows if row["rank"] is not None),
                default=None,
            ),
        })
    mapped.sort(key=lambda row: (
        row["best_local_rank"] is None,
        row["best_local_rank"] or 10**9,
        -(row["best_local_score"] or 0),
        row["id"],
    ))
    return {
        "method": (
            "Externally sourced reference tags mapped onto local Lean basins. "
            "Use for literature/PDE route selection and prompt construction; "
            "do not treat as proof evidence."
        ),
        "references": mapped,
    }


def build_l3a_workmap() -> list[L3AWorkmapItem]:
    graph_rows = _artifact_status_by_name()
    items: list[L3AWorkmapItem] = []
    seen: set[str] = set()
    for row in _decl_rows():
        name = str(row.get("name", ""))
        if not name or name in seen:
            continue
        seen.add(name)
        graph = graph_rows.get(name, {})
        status = str(graph.get("status") or row.get("status") or "declaration")
        kind = str(row.get("kind") or graph.get("type") or "decl")
        line = row.get("line") or graph.get("line")
        try:
            line_int = int(line) if line is not None else None
        except Exception:
            line_int = None
        kscore, hits = _keyword_score(name)
        if not kscore:
            # Keep supporting declarations visible, but below proof targets.
            kscore = 5
        score = kscore + _status_score(status)
        if ".of" in name:
            # Namespaced `.of...` declarations are useful adapters, but the
            # workmap's top rows should remain hard PDE obligations rather than
            # constructor plumbing after namespaced declaration indexing.
            score = min(score - 120, 330)
        elif "." in name:
            score = min(score - 55, 330)
        if name.endswith("_nonempty"):
            score -= 70
        if status == "closed_theorem":
            # Closed algebra facts are useful evidence, but should not outrank
            # open PDE primitives in the local workmap.
            score -= 100
        reason = "keyword hits: " + ", ".join(hits) if hits else "supporting L3A declaration"
        if ".of" in name:
            reason += "; adapter constructor"
        elif "." in name:
            reason += "; namespaced declaration"
        if name.endswith("_nonempty"):
            reason += "; nonempty witness"
        if status == "closed_theorem":
            reason += "; closed theorem"
        items.append(
            L3AWorkmapItem(
                name=name,
                score=score,
                status=status,
                kind=kind,
                file=f"ztare_proofs/ZtareProofs/{L3A_FILE}.lean",
                line=line_int,
                reason=reason,
                next_action=NEXT_ACTIONS.get(name, "Supporting carrier; keep below PDE bridge targets."),
            )
        )
    items.sort(key=lambda x: (-x.score, x.line or 10**9, x.name))
    return items


def write_l3a_workmap(path: Path = OUT_PATH) -> list[L3AWorkmapItem]:
    items = build_l3a_workmap()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_by": "src.ztare.research_director.ns_l3a_workmap",
        "source_file": f"ztare_proofs/ZtareProofs/{L3A_FILE}.lean",
        "items": [asdict(item) for item in items],
        "top_targets": [asdict(item) for item in items[:12]],
        "basin_diagnostics": build_basin_diagnostics(items),
        "native_primitive_surface": build_native_primitive_surface(),
        "external_reference_surface": build_external_reference_surface(items),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return items


def render_summary(items: list[L3AWorkmapItem], *, n: int = 8) -> str:
    lines = [f"L3A concentration workmap targets: {len(items)}"]
    for item in items[:n]:
        loc = f"{item.file}:{item.line}" if item.line else item.file
        lines.append(f"  - {item.name} score={item.score} status={item.status} [{loc}]")
        lines.append(f"    next: {item.next_action}")
    return "\n".join(lines)
