import Mathlib.Tactic
import ZtareProofs.ns_pricing_kernel_limit_passage

/-!
# Vanishing branch for Track B

This file isolates the no-deployed-payoff branch of the pricing-kernel
program.  It proves only the abstract routing theorem: if a profile family is
vanishing in the declared topology, each profile's payoff is non-positive, and
residual payoff is charged, then the family cannot produce arbitrage.

The real PDE obligation remains open: instantiate the vanishing certificate
for actual Leray/Sobolev profile decompositions under a fixed topology.
-/

namespace ZtareProofs.NS

/-- A profile certificate for the vanishing branch. -/
structure VanishingProfileCertificate (P : PricingProfile) where
  vanished : P.concentrationScale = 0
  price_nonnegative : 0 ≤ P.price
  no_deployed_payoff : VanishingHasNoPayoff P

/-- Vanishing profiles are priced because their payoff is non-positive. -/
theorem profile_no_arbitrage_of_vanishing
    (P : PricingProfile)
    (h : VanishingProfileCertificate P) :
    ProfileNoArbitrage P := by
  unfold ProfileNoArbitrage
  have hpay : P.payoff ≤ 0 := h.no_deployed_payoff h.vanished
  exact hpay.trans h.price_nonnegative

/-- A vanishing profile certificate is impossible for a profile whose declared
payoff exceeds declared price. -/
theorem no_vanishing_profile_certificate_of_arbitrage
    (P : PricingProfile)
    (harb : P.price < P.payoff) :
    ¬ VanishingProfileCertificate P := by
  intro h
  have hnoarb : ProfileNoArbitrage P :=
    profile_no_arbitrage_of_vanishing P h
  unfold ProfileNoArbitrage at hnoarb
  exact not_lt_of_ge hnoarb harb

/-- Family-level certificate for the vanishing branch. -/
structure VanishingFamilyCertificate (F : PricingProfileFamily) where
  residual_price_nonnegative : 0 ≤ F.residualPrice
  residual_payoff_charged : F.residualPayoff ≤ F.residualPrice
  profile_certificates :
    ∀ P ∈ F.profiles, VanishingProfileCertificate P

/-- Vanishing closes a fixed profile family. -/
theorem family_no_arbitrage_of_vanishing
    (F : PricingProfileFamily)
    (h : VanishingFamilyCertificate F) :
    familyPayoff F ≤ familyPrice F := by
  unfold familyPayoff familyPrice
  have hprofiles :
      (F.profiles.map (fun P => P.payoff)).sum ≤
        (F.profiles.map (fun P => P.price)).sum := by
    apply sum_payoff_le_sum_price_of_profiles
    intro P hP
    exact profile_no_arbitrage_of_vanishing P
      (h.profile_certificates P hP)
  exact add_le_add hprofiles h.residual_payoff_charged

/-- A family-level vanishing certificate is impossible if the declared family
payoff exceeds declared family price. -/
theorem no_vanishing_family_certificate_of_arbitrage
    (F : PricingProfileFamily)
    (harb : familyPrice F < familyPayoff F) :
    ¬ VanishingFamilyCertificate F := by
  intro h
  have hnoarb : familyPayoff F ≤ familyPrice F :=
    family_no_arbitrage_of_vanishing F h
  exact not_lt_of_ge hnoarb harb

/-- Track B bridge specialized to the vanishing branch. -/
structure VanishingPricingBridge where
  profile_family_of_block : FullLedgerBlock → PricingProfileFamily
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        VanishingFamilyCertificate (profile_family_of_block B)
  threshold_defect_of_family_no_arbitrage :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        familyPayoff (profile_family_of_block B) ≤
          familyPrice (profile_family_of_block B) →
            ThresholdDefectConvexity B

/-- Vanishing bridge theorem: once the PDE supplies the fixed no-deployed-payoff
certificate, the existing Track B no-survivor theorem applies. -/
theorem no_global_survivor_of_vanishing_bridge
    (bridge : VanishingPricingBridge)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hfamily :
      familyPayoff (bridge.profile_family_of_block B) ≤
        familyPrice (bridge.profile_family_of_block B) :=
    family_no_arbitrage_of_vanishing
      (bridge.profile_family_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact hquartic B
    (bridge.threshold_defect_of_family_no_arbitrage B hglobal hfamily)

end ZtareProofs.NS
