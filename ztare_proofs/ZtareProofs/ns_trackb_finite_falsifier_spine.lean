import Mathlib.Tactic
import ZtareProofs.ns_low_high_catalyst_charging_obligation
import ZtareProofs.ns_low_high_kinematic_dichotomy
import ZtareProofs.ns_low_high_lipschitz_reserve_adapter
import ZtareProofs.ns_high_low_transport_charging_obligation
import ZtareProofs.ns_high_high_resonance_route_adapter
import ZtareProofs.ns_same_shell_remainder_charging_obligation
import ZtareProofs.ns_concentration_impact_branch
import ZtareProofs.ns_vanishing_branch
import ZtareProofs.ns_dichotomy_cross_profile_branch
import ZtareProofs.ns_pricing_kernel_countable_limit
import ZtareProofs.ns_low_frequency_lipschitz_control_bridge
import ZtareProofs.ns_null_profile_cap_branch
import ZtareProofs.ns_profile_limit_lsc_bossfight
import ZtareProofs.ns_matrix_block_sos_bossfight

/-!
# Track B finite falsifier spine

This module is a map, not a Navier-Stokes proof.

It collects the current finite negative-arm tests for the Track B proof
surface.  The point is anti-tautology: every branch must either supply its
predeclared analytic receipt, or it can be broken by a concrete finite witness
of the corresponding shape.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Compact catalogue of the current finite falsifier interfaces for Track B.

Every field is already proved in a branch module.  This structure simply keeps
the frontier from drifting back into prose such as "charge the tax" or "the
limit should be okay." -/
structure TrackBFiniteFalsifierSurface where
  low_high_reserve_shortfall :
    ∀ (H : LowHighCatalystLeakageBridge),
      LowHighCatalystReserveShortfallFalsifier H → False
  low_high_negative_member :
    ∀ (P : ClosedLowHighCatalystPositive)
      (N : ClosedLowHighCatalystNegative),
        P.Class N.interaction → False
  low_high_bilinear_constant_shortfall :
    ∀ L : LowHighKinematicDichotomyLedger,
      LowHighBilinearConstantWitness L →
        LowHighBilinearChargeFalsifier L →
          False
  low_high_lp_bony_receipt_shortfall :
    ∀ L : LowHighKinematicDichotomyLedger,
      LowHighLPBonyEstimateReceipt L →
        LowHighBilinearChargeFalsifier L →
          False
  low_high_lipschitz_reserve_link_shortfall :
    ∀ (L : LowHighKinematicDichotomyLedger)
      (R : LowHighLPBonyUnpaidEstimateReceipt L)
      (G : LowFrequencyLipschitzLedger)
      (_C : LowFrequencyLipschitzControlCertificate G)
      (n : ℕ),
        LowHighLipschitzReserveLink L R G n →
          FullLedgerNoSurvivor (G.block n) →
            LowHighBilinearChargeFalsifier L →
              False
  low_high_shell_prefix_overbudget :
    ∀ (G : LowFrequencyLipschitzLedger)
      (_C : LowFrequencyLipschitzControlCertificate G)
      (S : LowHighShellReserveClosure G)
      (_ : ∀ n : ℕ, FullLedgerNoSurvivor (G.block n)),
        LowHighShellPrefixReserveFalsifier G S → False
  high_low_reserve_shortfall :
    ∀ (H : HighLowTransportLeakageBridge),
      HighLowTransportReserveShortfallFalsifier H → False
  high_low_negative_member :
    ∀ (P : ClosedHighLowTransportPositive)
      (N : ClosedHighLowTransportNegative),
        P.Class N.interaction → False
  high_high_nonresonant_shortfall :
    ∀ R : HighHighNonresonantRootFloorReceipt,
      R.block.selfTax < (
        let x : Real := Real.sqrt (sharpTarget / R.block.gamma)
        (1 - x ^ (2 : Nat)) / x ^ (4 : Nat)) →
          False
  high_high_resonant_shortfall :
    ∀ R : HighHighResonantRootChargeReceipt,
      R.block.selfTax < (
        let x : Real := Real.sqrt (sharpTarget / R.block.gamma)
        (1 - x ^ (2 : Nat) - 2 * R.block.cross * x ^ (3 : Nat)) /
          x ^ (4 : Nat)) →
          False
  residual_charge_shortfall :
    ResidualChargeFalsifier → False
  concentration_profile_arbitrage :
    ∀ P : PricingProfile,
      P.price < P.payoff →
        ¬ ConcentrationImpactProfileCertificate P
  concentration_family_arbitrage :
    ∀ F : PricingProfileFamily,
      familyPrice F < familyPayoff F →
        ¬ ConcentrationImpactFamilyCertificate F
  vanishing_profile_arbitrage :
    ∀ P : PricingProfile,
      P.price < P.payoff →
        ¬ VanishingProfileCertificate P
  vanishing_family_arbitrage :
    ∀ F : PricingProfileFamily,
      familyPrice F < familyPayoff F →
        ¬ VanishingFamilyCertificate F
  cross_profile_family_arbitrage :
    ∀ F : PricingProfileFamily,
      familyPrice F < familyPayoff F →
        ¬ (PricedFragmentCertificate F ∧
          CrossProfileRecombinationCertificate F)
  countable_limit_arbitrage :
    ∀ S : CountablePricingStream,
      S.priceLimit < S.payoffLimit →
        ¬ CountableLimitCertificate S
  low_frequency_entry_underpriced :
    ∀ (L : LowFrequencyLipschitzLedger)
      (_ : LowFrequencyLipschitzControlCertificate L)
      (_ : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
      (marketImpactCost : ℕ → Real),
        (∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n) →
          ∀ n : ℕ, L.reservePrice n < marketImpactCost n → False
  low_frequency_unbounded_market_impact :
    ∀ (L : LowFrequencyLipschitzLedger)
      (_ : LowFrequencyLipschitzControlCertificate L)
      (_ : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
      (marketImpactCost : ℕ → Real),
        (∀ n : ℕ, 0 ≤ marketImpactCost n) →
          (∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n) →
            (∀ B : Real, ∃ n : ℕ, B < marketImpactCost n) →
              False
  low_frequency_linear_shell_market_impact :
    ∀ (L : LowFrequencyLipschitzLedger)
      (_ : LowFrequencyLipschitzControlCertificate L)
      (_ : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
      (shellLabel marketImpactCost : ℕ → Real)
      (a : Real),
        0 < a →
          (∀ n : ℕ, 0 ≤ marketImpactCost n) →
            (∀ n : ℕ, a * shellLabel n ≤ marketImpactCost n) →
              (∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n) →
                (∀ B : Real, ∃ n : ℕ, B < shellLabel n) →
                  False
  null_profile_arbitrage :
    ∀ (F : PricingProfileFamily) (P : PricingProfile),
      P ∈ F.profiles →
        P.isNull →
          P.price < P.payoff →
            ¬ NullProfileCapBranchCertificate F
  countable_unbounded_profile_prices :
    ∀ S : CountablePricingStream,
      (∀ i : ℕ, 0 ≤ (S.profiles i).price) →
        (∀ B : Real, ∃ i : ℕ, B < (S.profiles i).price) →
          ¬ CountableLimitCertificate S
  profile_prefix_price_drop :
    ∀ (S : ProfileLimitStream) (n : ℕ),
      S.priceLimit < S.prefixPrice n →
        ¬ ProfileLimitLSCCertificate S
  lp_paraproduct_prefix_price_drop :
    ∀ (S : LPParaproductPricingStream) (n : ℕ),
      S.priceLimit < interactionFamilyPrice (S.prefixFamily n) →
        ¬ LPParaproductLimitCertificate S
  matrix_negative_gap :
    ∀ B : FullLedgerBlock,
      thresholdDefectGapAtRoot B < 0 →
        ¬ ∃ R : MatrixBlockSOSBranchReceipt, R.block = B

/-- The current branch modules instantiate the finite falsifier spine. -/
def trackBFiniteFalsifierSurface : TrackBFiniteFalsifierSurface where
  low_high_reserve_shortfall :=
    no_low_high_catalyst_reserve_shortfall_with_leakage_absorption
  low_high_negative_member :=
    no_low_high_negative_member_of_closed_positive
  low_high_bilinear_constant_shortfall :=
    no_low_high_bilinear_falsifier_with_constant_witness
  low_high_lp_bony_receipt_shortfall :=
    no_low_high_bilinear_falsifier_with_lp_bony_receipt
  low_high_lipschitz_reserve_link_shortfall :=
    no_low_high_lipschitz_reserve_link_with_bilinear_falsifier
  low_high_shell_prefix_overbudget :=
    no_low_high_shell_reserve_closure_with_prefix_falsifier
  high_low_reserve_shortfall :=
    no_high_low_transport_reserve_shortfall_with_leakage_absorption
  high_low_negative_member :=
    no_high_low_negative_member_of_closed_positive
  high_high_nonresonant_shortfall :=
    no_nonresonant_root_floor_receipt_of_shortfall
  high_high_resonant_shortfall :=
    no_resonant_root_charge_receipt_of_shortfall
  residual_charge_shortfall :=
    no_residual_falsifier_with_charge_witness
  concentration_profile_arbitrage :=
    no_concentration_impact_profile_certificate_of_arbitrage
  concentration_family_arbitrage :=
    no_concentration_impact_family_certificate_of_arbitrage
  vanishing_profile_arbitrage :=
    no_vanishing_profile_certificate_of_arbitrage
  vanishing_family_arbitrage :=
    no_vanishing_family_certificate_of_arbitrage
  cross_profile_family_arbitrage :=
    no_cross_profile_certificates_of_family_arbitrage
  countable_limit_arbitrage :=
    no_countable_limit_certificate_of_limit_arbitrage
  low_frequency_entry_underpriced :=
    by
      intro L C hnosurvivor marketImpactCost hmarket n hunderpriced
      exact no_underpriced_market_impact_entry_under_no_survivor
        L C hnosurvivor marketImpactCost hmarket n hunderpriced
  low_frequency_unbounded_market_impact :=
    no_pointwise_unbounded_market_impact_under_no_survivor
  low_frequency_linear_shell_market_impact :=
    no_linear_shell_market_impact_under_no_survivor
  null_profile_arbitrage :=
    no_null_profile_cap_branch_certificate_of_null_arbitrage
  countable_unbounded_profile_prices :=
    no_countable_limit_certificate_of_pointwise_unbounded_prices
  profile_prefix_price_drop :=
    no_profile_lsc_certificate_of_prefix_price_drop
  lp_paraproduct_prefix_price_drop :=
    no_lp_paraproduct_lsc_certificate_of_prefix_price_drop
  matrix_negative_gap :=
    no_matrix_sos_branch_of_negative_threshold_gap

end

end ZtareProofs.NS
