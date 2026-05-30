import Mathlib.Tactic
import ZtareProofs.ns_pricing_kernel_limit_passage

/-!
# Null-profile cap branch for Track B

This file isolates one of the seven branch-killer obligations from the Track B
pricing-kernel program.  It does **not** prove the Navier-Stokes nullspace
gain lemma.  It proves the abstract branch logic:

if null profiles are capped, non-null profiles are priced by the interacting
branch, and residual payoff is charged by residual price, then the profile
family is no-arbitrage.

The analytic burden left outside this file is the real PDE theorem:

`P.isNull -> P.payoff <= P.price`

for actual Leray/Sobolev null profiles under the declared observable class.
-/

namespace ZtareProofs.NS

/-- Non-null profiles are priced by another branch of the Track B program. -/
def NonNullProfilePriced (P : PricingProfile) : Prop :=
  ¬ P.isNull → ProfileNoArbitrage P

/-- Branch-local certificate for the null-profile cap split. -/
structure NullProfileCapBranchCertificate (F : PricingProfileFamily) where
  residual_price_nonnegative : 0 ≤ F.residualPrice
  residual_charged : F.residualPayoff ≤ F.residualPrice
  null_cap : ∀ P ∈ F.profiles, NullProfileCapped P
  nonnull_priced : ∀ P ∈ F.profiles, NonNullProfilePriced P

/-- The null/non-null split supplies the profilewise no-arbitrage predicate
needed by dichotomy. -/
lemma profile_no_arbitrage_of_null_split
    {F : PricingProfileFamily}
    (h : NullProfileCapBranchCertificate F) :
    ∀ P ∈ F.profiles, ProfileNoArbitrage P := by
  intro P hP
  by_cases hnull : P.isNull
  · exact h.null_cap P hP hnull
  · exact h.nonnull_priced P hP hnull

/-- Null-profile branch closure for one finite profile family. -/
theorem family_no_arbitrage_of_null_profile_cap_branch
    (F : PricingProfileFamily)
    (h : NullProfileCapBranchCertificate F) :
    familyPayoff F ≤ familyPrice F := by
  apply family_no_arbitrage_of_dichotomy
  unfold DichotomyPriceSubadditive
  exact ⟨h.residual_price_nonnegative, h.residual_charged,
    profile_no_arbitrage_of_null_split h⟩

/-- One declared null arbitrage profile falsifies the null-profile cap branch
certificate for the family containing it. -/
theorem no_null_profile_cap_branch_certificate_of_null_arbitrage
    (F : PricingProfileFamily)
    (P : PricingProfile)
    (hP : P ∈ F.profiles)
    (hnull : P.isNull)
    (harb : P.price < P.payoff) :
    ¬ NullProfileCapBranchCertificate F := by
  intro h
  have hcap : P.payoff ≤ P.price :=
    h.null_cap P hP hnull
  exact not_lt_of_ge hcap harb

/-- Global branch bridge: if every global Track B block has a profile family
with the null-profile branch certificate and that family no-arbitrage implies
threshold-defect convexity, then the existing no-survivor theorem applies. -/
structure NullProfileCapBranchBridge where
  profile_family_of_block : FullLedgerBlock → PricingProfileFamily
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        NullProfileCapBranchCertificate (profile_family_of_block B)
  threshold_defect_of_family_no_arbitrage :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        familyPayoff (profile_family_of_block B) ≤
          familyPrice (profile_family_of_block B) →
            ThresholdDefectConvexity B

/-- Projection theorem for the null-profile branch. -/
theorem no_global_survivor_of_null_profile_cap_branch
    (bridge : NullProfileCapBranchBridge)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hfamily :
      familyPayoff (bridge.profile_family_of_block B) ≤
        familyPrice (bridge.profile_family_of_block B) :=
    family_no_arbitrage_of_null_profile_cap_branch
      (bridge.profile_family_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact hquartic B
    (bridge.threshold_defect_of_family_no_arbitrage B hglobal hfamily)

end ZtareProofs.NS
