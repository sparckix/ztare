import Mathlib.Tactic
import ZtareProofs.ns_pricing_kernel_limit_passage

/-!
# Dichotomy and cross-profile recombination branches for Track B

This file makes explicit the two profile-fragmentation branches that were
previously only routed through the general pricing-kernel limit-passage file:

* dichotomy / price subadditivity;
* cross-profile recombination charging.

It does **not** prove the PDE profile decomposition theorem.  It proves that
once independently declared fragments are pointwise priced and the cross
residual is charged, recombination cannot create a free trade.
-/

namespace ZtareProofs.NS

/-- A priced-fragment certificate: every declared profile is already
no-arbitrage under the fixed pricing kernel. -/
structure PricedFragmentCertificate (F : PricingProfileFamily) where
  profile_no_arbitrage : ∀ P ∈ F.profiles, ProfileNoArbitrage P

/-- A cross-profile recombination certificate: residual/cross payoff is charged
by residual/cross price. -/
structure CrossProfileRecombinationCertificate (F : PricingProfileFamily) where
  residual_price_nonnegative : 0 ≤ F.residualPrice
  cross_payoff_charged : CrossProfileCancellationCharged F

/-- Young/Cauchy cross-profile charge receipt.

This is the algebraic target for the recombination branch.  The PDE/profile
work must prove the product bound from fixed profile orthogonality or a
declared defect measure:

`crossPayoffMagnitude^2 <= leftProfilePrice * rightProfilePrice`.

Once that is available, AM-GM charges the cross payoff by the predeclared
residual price. -/
structure CrossProfileYoungChargeReceipt (F : PricingProfileFamily) where
  crossPayoffMagnitude : Real
  leftProfilePrice : Real
  rightProfilePrice : Real
  cross_magnitude_nonnegative : 0 ≤ crossPayoffMagnitude
  left_price_nonnegative : 0 ≤ leftProfilePrice
  right_price_nonnegative : 0 ≤ rightProfilePrice
  residual_payoff_le_cross_magnitude :
    F.residualPayoff ≤ crossPayoffMagnitude
  residual_price_eq_young_average :
    F.residualPrice = (leftProfilePrice + rightProfilePrice) / 2
  cross_sq_le_price_product :
    crossPayoffMagnitude ^ 2 ≤ leftProfilePrice * rightProfilePrice

/-- AM-GM charge for a bilinear cross-profile term. -/
lemma cross_magnitude_le_young_average
    {cross leftPrice rightPrice : Real}
    (hleft_nonneg : 0 ≤ leftPrice)
    (hright_nonneg : 0 ≤ rightPrice)
    (hprod : cross ^ 2 ≤ leftPrice * rightPrice) :
    cross ≤ (leftPrice + rightPrice) / 2 := by
  nlinarith [sq_nonneg (leftPrice - rightPrice),
    sq_nonneg (2 * cross - (leftPrice + rightPrice)),
    hleft_nonneg, hright_nonneg, hprod]

/-- A Young/Cauchy receipt supplies the cross-profile charging predicate. -/
theorem cross_profile_charged_of_young_receipt
    (F : PricingProfileFamily)
    (h : CrossProfileYoungChargeReceipt F) :
    CrossProfileCancellationCharged F := by
  unfold CrossProfileCancellationCharged
  have hyoung :
      h.crossPayoffMagnitude ≤
        (h.leftProfilePrice + h.rightProfilePrice) / 2 :=
    cross_magnitude_le_young_average
      h.left_price_nonnegative
      h.right_price_nonnegative
      h.cross_sq_le_price_product
  rw [h.residual_price_eq_young_average]
  exact h.residual_payoff_le_cross_magnitude.trans hyoung

/-- A Young/Cauchy receipt plus nonnegative residual price supplies the
existing cross-profile recombination certificate interface. -/
def cross_profile_recombination_certificate_of_young_receipt
    (F : PricingProfileFamily)
    (h : CrossProfileYoungChargeReceipt F)
    (hresidual_nonnegative : 0 ≤ F.residualPrice) :
    CrossProfileRecombinationCertificate F where
  residual_price_nonnegative := hresidual_nonnegative
  cross_payoff_charged := cross_profile_charged_of_young_receipt F h

/-- A Young/Cauchy cross-profile receipt is impossible when the residual payoff
exceeds the declared residual price. -/
theorem no_cross_profile_young_receipt_of_residual_arbitrage
    (F : PricingProfileFamily)
    (harb : F.residualPrice < F.residualPayoff)
    (h : CrossProfileYoungChargeReceipt F) :
    False := by
  have hcharged : CrossProfileCancellationCharged F :=
    cross_profile_charged_of_young_receipt F h
  unfold CrossProfileCancellationCharged at hcharged
  exact not_lt_of_ge hcharged harb

/-- Fragment pricing plus cross-profile charging closes a fixed profile
family. -/
theorem family_no_arbitrage_of_cross_profile_charging
    (F : PricingProfileFamily)
    (hpriced : PricedFragmentCertificate F)
    (hcross : CrossProfileRecombinationCertificate F) :
    familyPayoff F ≤ familyPrice F := by
  unfold familyPayoff familyPrice
  have hprofiles :
      (F.profiles.map (fun P => P.payoff)).sum ≤
      (F.profiles.map (fun P => P.price)).sum :=
    sum_payoff_le_sum_price_of_profiles hpriced.profile_no_arbitrage
  exact add_le_add hprofiles hcross.cross_payoff_charged

/-- Priced fragments plus charged cross-profile recombination are impossible
when the declared family payoff exceeds the declared family price. -/
theorem no_cross_profile_certificates_of_family_arbitrage
    (F : PricingProfileFamily)
    (harb : familyPrice F < familyPayoff F) :
    ¬ (PricedFragmentCertificate F ∧
        CrossProfileRecombinationCertificate F) := by
  intro h
  have hnoarb : familyPayoff F ≤ familyPrice F :=
    family_no_arbitrage_of_cross_profile_charging F h.1 h.2
  exact not_lt_of_ge hnoarb harb

/-- A dichotomy/cross-profile bridge for global Track B blocks. -/
structure DichotomyCrossProfileBridge where
  profile_family_of_block : FullLedgerBlock → PricingProfileFamily
  priced_fragments :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        PricedFragmentCertificate (profile_family_of_block B)
  cross_profile_charged :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        CrossProfileRecombinationCertificate (profile_family_of_block B)
  threshold_defect_of_family_no_arbitrage :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        familyPayoff (profile_family_of_block B) ≤
          familyPrice (profile_family_of_block B) →
            ThresholdDefectConvexity B

/-- Dichotomy/cross-profile bridge theorem: once the PDE supplies a fixed
fragment decomposition and charges the cross residual, the existing Track B
no-survivor theorem applies. -/
theorem no_global_survivor_of_dichotomy_cross_profile_bridge
    (bridge : DichotomyCrossProfileBridge)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hfamily :
      familyPayoff (bridge.profile_family_of_block B) ≤
        familyPrice (bridge.profile_family_of_block B) :=
    family_no_arbitrage_of_cross_profile_charging
      (bridge.profile_family_of_block B)
      (bridge.priced_fragments B hglobal)
      (bridge.cross_profile_charged B hglobal)
  exact hquartic B
    (bridge.threshold_defect_of_family_no_arbitrage B hglobal hfamily)

end ZtareProofs.NS
