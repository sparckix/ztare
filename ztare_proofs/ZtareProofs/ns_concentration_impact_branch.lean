import Mathlib.Tactic
import ZtareProofs.ns_pricing_kernel_limit_passage

/-!
# Concentration-impact branch for Track B

This file isolates the "market impact" branch of the Track B pricing-kernel
program.  It is deliberately abstract: no Sobolev or Navier-Stokes regularity
claim is proved here.  The theorem says that if a fixed profile decomposition
supplies the required concentration-impact certificate, then concentration
cannot create a new above-price payoff.

The missing PDE obligation is exactly the hard part: instantiate
`ConcentrationImpactProfileCertificate` for actual Leray/Sobolev profiles
under a predeclared topology.
-/

namespace ZtareProofs.NS

/-- A profile-level concentration-impact certificate.

If the profile concentrates (`0 < concentrationScale`), payoff is dominated by
self-tax and self-tax is charged in the price.  If the profile vanishes at the
declared scale, payoff is non-positive.  The price is non-negative. -/
structure ConcentrationImpactProfileCertificate (P : PricingProfile) where
  scale_nonnegative : 0 ≤ P.concentrationScale
  price_nonnegative : 0 ≤ P.price
  impact_coercive : ConcentrationImpactCoercive P
  vanishing_no_payoff : VanishingHasNoPayoff P

/-- Dual-price concentration receipt.

This is the algebraic core exposed by Phase 5HY.  In a concentrating profile,
the cubic stretching scale is not expected to be dominated by one price channel
in every amplitude regime.  Instead, a viscous small-scale price and a
nonlinear self-tax price form a dual certificate:

`production^2 <= viscousPrice * selfTaxPrice`.

AM-GM then charges production by the average of the two prices.  The PDE work
is to instantiate `production_sq_le_dual_product` from the fixed
Leray/Sobolev/profile topology. -/
structure DualPriceConcentrationReceipt (P : PricingProfile) where
  production : Real
  viscousPrice : Real
  selfTaxPrice : Real
  production_nonnegative : 0 ≤ production
  viscous_price_nonnegative : 0 ≤ viscousPrice
  self_tax_price_nonnegative : 0 ≤ selfTaxPrice
  payoff_le_production : P.payoff ≤ production
  price_eq_dual_average :
    P.price = (viscousPrice + selfTaxPrice) / 2
  production_sq_le_dual_product :
    production ^ 2 ≤ viscousPrice * selfTaxPrice

/-- AM-GM form of the dual-price concentration receipt. -/
lemma production_le_dual_price_average
    {production viscousPrice selfTaxPrice : Real}
    (hvisc_nonneg : 0 ≤ viscousPrice)
    (hself_nonneg : 0 ≤ selfTaxPrice)
    (hprod :
      production ^ 2 ≤ viscousPrice * selfTaxPrice) :
    production ≤ (viscousPrice + selfTaxPrice) / 2 := by
  nlinarith [sq_nonneg (viscousPrice - selfTaxPrice),
    sq_nonneg (2 * production - (viscousPrice + selfTaxPrice)),
    hvisc_nonneg, hself_nonneg, hprod]

/-- A dual viscous/self-tax price receipt prices one concentrating profile. -/
theorem profile_no_arbitrage_of_dual_price_concentration
    (P : PricingProfile)
    (h : DualPriceConcentrationReceipt P) :
    ProfileNoArbitrage P := by
  unfold ProfileNoArbitrage
  have hproduction :
      h.production ≤ (h.viscousPrice + h.selfTaxPrice) / 2 :=
    production_le_dual_price_average
      h.viscous_price_nonnegative
      h.self_tax_price_nonnegative
      h.production_sq_le_dual_product
  rw [h.price_eq_dual_average]
  exact h.payoff_le_production.trans hproduction

/-- A dual-price concentration receipt is impossible for a profile whose payoff
exceeds the declared dual average price. -/
theorem no_dual_price_concentration_receipt_of_arbitrage
    (P : PricingProfile)
    (harb : P.price < P.payoff)
    (h : DualPriceConcentrationReceipt P) :
    False := by
  have hnoarb : ProfileNoArbitrage P :=
    profile_no_arbitrage_of_dual_price_concentration P h
  unfold ProfileNoArbitrage at hnoarb
  exact not_lt_of_ge hnoarb harb

/-- Family-level concentration certificate built from per-profile dual prices
plus charged residual leakage. -/
structure DualPriceConcentrationFamilyCertificate
    (F : PricingProfileFamily) where
  residual_price_nonnegative : 0 ≤ F.residualPrice
  residual_payoff_charged : F.residualPayoff ≤ F.residualPrice
  profile_dual_receipts :
    ∀ P ∈ F.profiles, DualPriceConcentrationReceipt P

/-- Per-profile dual-price receipts close a fixed concentration family. -/
theorem family_no_arbitrage_of_dual_price_concentration
    (F : PricingProfileFamily)
    (h : DualPriceConcentrationFamilyCertificate F) :
    familyPayoff F ≤ familyPrice F := by
  unfold familyPayoff familyPrice
  have hprofiles :
      (F.profiles.map (fun P => P.payoff)).sum ≤
        (F.profiles.map (fun P => P.price)).sum := by
    apply sum_payoff_le_sum_price_of_profiles
    intro P hP
    exact profile_no_arbitrage_of_dual_price_concentration P
      (h.profile_dual_receipts P hP)
  exact add_le_add hprofiles h.residual_payoff_charged

/-- A family-level dual concentration receipt is impossible if declared family
payoff exceeds declared family price. -/
theorem no_dual_price_concentration_family_certificate_of_arbitrage
    (F : PricingProfileFamily)
    (harb : familyPrice F < familyPayoff F)
    (h : DualPriceConcentrationFamilyCertificate F) :
    False := by
  have hnoarb : familyPayoff F ≤ familyPrice F :=
    family_no_arbitrage_of_dual_price_concentration F h
  exact not_lt_of_ge hnoarb harb

/-- Track B bridge specialized to the dual-price concentration branch. -/
structure DualPriceConcentrationPricingBridge where
  profile_family_of_block : FullLedgerBlock → PricingProfileFamily
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        DualPriceConcentrationFamilyCertificate (profile_family_of_block B)
  threshold_defect_of_family_no_arbitrage :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        familyPayoff (profile_family_of_block B) ≤
          familyPrice (profile_family_of_block B) →
            ThresholdDefectConvexity B

/-- Dual-price concentration bridge theorem: once the PDE supplies the fixed
dual viscous/self-tax product receipt, the existing Track B no-survivor theorem
applies. -/
theorem no_global_survivor_of_dual_price_concentration_bridge
    (bridge : DualPriceConcentrationPricingBridge)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hfamily :
      familyPayoff (bridge.profile_family_of_block B) ≤
        familyPrice (bridge.profile_family_of_block B) :=
    family_no_arbitrage_of_dual_price_concentration
      (bridge.profile_family_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact hquartic B
    (bridge.threshold_defect_of_family_no_arbitrage B hglobal hfamily)

/-- A concentration-impact certificate prices one profile. -/
theorem profile_no_arbitrage_of_concentration_impact
    (P : PricingProfile)
    (h : ConcentrationImpactProfileCertificate P) :
    ProfileNoArbitrage P := by
  unfold ProfileNoArbitrage
  rcases lt_or_eq_of_le h.scale_nonnegative with hpos | hzero
  · exact (h.impact_coercive hpos).1.trans (h.impact_coercive hpos).2
  · have hz : P.concentrationScale = 0 := by linarith
    have hpay : P.payoff ≤ 0 := h.vanishing_no_payoff hz
    exact hpay.trans h.price_nonnegative

/-- A concentration-impact profile certificate is impossible for a profile
whose declared payoff exceeds its declared price. -/
theorem no_concentration_impact_profile_certificate_of_arbitrage
    (P : PricingProfile)
    (harb : P.price < P.payoff) :
    ¬ ConcentrationImpactProfileCertificate P := by
  intro h
  have hnoarb : ProfileNoArbitrage P :=
    profile_no_arbitrage_of_concentration_impact P h
  unfold ProfileNoArbitrage at hnoarb
  exact not_lt_of_ge hnoarb harb

/-- Family-level concentration-impact certificate, including charged residual
leakage. -/
structure ConcentrationImpactFamilyCertificate (F : PricingProfileFamily) where
  residual_price_nonnegative : 0 ≤ F.residualPrice
  residual_payoff_charged : F.residualPayoff ≤ F.residualPrice
  profile_certificates :
    ∀ P ∈ F.profiles, ConcentrationImpactProfileCertificate P

/-- Concentration impact closes a fixed finite profile family. -/
theorem family_no_arbitrage_of_concentration_impact
    (F : PricingProfileFamily)
    (h : ConcentrationImpactFamilyCertificate F) :
    familyPayoff F ≤ familyPrice F := by
  unfold familyPayoff familyPrice
  have hprofiles :
      (F.profiles.map (fun P => P.payoff)).sum ≤
        (F.profiles.map (fun P => P.price)).sum := by
    apply sum_payoff_le_sum_price_of_profiles
    intro P hP
    exact profile_no_arbitrage_of_concentration_impact P
      (h.profile_certificates P hP)
  exact add_le_add hprofiles h.residual_payoff_charged

/-- A family-level concentration-impact certificate is impossible if the
declared family payoff exceeds declared family price. -/
theorem no_concentration_impact_family_certificate_of_arbitrage
    (F : PricingProfileFamily)
    (harb : familyPrice F < familyPayoff F) :
    ¬ ConcentrationImpactFamilyCertificate F := by
  intro h
  have hnoarb : familyPayoff F ≤ familyPrice F :=
    family_no_arbitrage_of_concentration_impact F h
  exact not_lt_of_ge hnoarb harb

/-- Track B bridge specialized to the concentration-impact branch. -/
structure ConcentrationImpactPricingBridge where
  profile_family_of_block : FullLedgerBlock → PricingProfileFamily
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        ConcentrationImpactFamilyCertificate (profile_family_of_block B)
  threshold_defect_of_family_no_arbitrage :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        familyPayoff (profile_family_of_block B) ≤
          familyPrice (profile_family_of_block B) →
            ThresholdDefectConvexity B

/-- Concentration-impact bridge theorem: once the PDE supplies the fixed
profile certificate, the existing Track B no-survivor theorem applies. -/
theorem no_global_survivor_of_concentration_impact_bridge
    (bridge : ConcentrationImpactPricingBridge)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hfamily :
      familyPayoff (bridge.profile_family_of_block B) ≤
        familyPrice (bridge.profile_family_of_block B) :=
    family_no_arbitrage_of_concentration_impact
      (bridge.profile_family_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact hquartic B
    (bridge.threshold_defect_of_family_no_arbitrage B hglobal hfamily)

end ZtareProofs.NS
