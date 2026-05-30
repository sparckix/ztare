import Mathlib.Tactic
import ZtareProofs.ns_leray_gain_tax_trackb_obligation

/-!
# Pricing-kernel limit passage obligations for Track B

This file formalizes the current bridge target after the finite state-pricing
audits.  It does **not** prove Navier-Stokes regularity.  It names the exact
non-tautological limit-passage conditions needed to promote a finite or
scale-local Track B pricing kernel into a global Sobolev-class theorem.

The financial analogy is only a mnemonic:

* concentration = block execution / market-impact coercivity;
* dichotomy = fragmented execution / price subadditivity;
* cross-profile recombination = hedge leakage;
* vanishing = no deployed capital / no nonlinear payoff;
* null profiles = below-wall or non-rearming directions.

The mathematical object is the fixed, predeclared Leray ledger from
`ns_leray_gain_tax_trackb_obligation.lean`.
-/

namespace ZtareProofs.NS

/-- A profile in the concentration-compactness limit passage.  The fields are
abstract on purpose: the real PDE work is proving that actual Leray profiles
admit these ledgers under a fixed topology. -/
structure PricingProfile where
  price : Real
  payoff : Real
  selfTax : Real
  concentrationScale : Real
  isNull : Prop

/-- A finite profile family produced by a fixed decomposition theorem. -/
structure PricingProfileFamily where
  profiles : List PricingProfile
  residualPrice : Real
  residualPayoff : Real

/-- The local no-arbitrage condition for one priced profile. -/
def ProfileNoArbitrage (P : PricingProfile) : Prop :=
  P.payoff ≤ P.price

/-- Price of a profile family, including residual leakage. -/
def familyPrice (F : PricingProfileFamily) : Real :=
  (F.profiles.map (fun P => P.price)).sum + F.residualPrice

/-- Payoff of a profile family, including residual payoff. -/
def familyPayoff (F : PricingProfileFamily) : Real :=
  (F.profiles.map (fun P => P.payoff)).sum + F.residualPayoff

/-- The dichotomy branch: fragmentation cannot reduce total charged price below
the sum of the independently priced pieces. -/
def DichotomyPriceSubadditive (F : PricingProfileFamily) : Prop :=
  0 ≤ F.residualPrice ∧
    F.residualPayoff ≤ F.residualPrice ∧
      ∀ P ∈ F.profiles, ProfileNoArbitrage P

/-- The concentration branch: forcing mass into a shrinking scale is charged by
the self-tax/impact side of the ledger. -/
def ConcentrationImpactCoercive (P : PricingProfile) : Prop :=
  0 < P.concentrationScale → P.payoff ≤ P.selfTax ∧ P.selfTax ≤ P.price

/-- The vanishing branch: a profile with no deployed concentration has no
above-wall payoff. -/
def VanishingHasNoPayoff (P : PricingProfile) : Prop :=
  P.concentrationScale = 0 → P.payoff ≤ 0

/-- The null branch: self-tax-free/null profiles remain below the price wall. -/
def NullProfileCapped (P : PricingProfile) : Prop :=
  P.isNull → ProfileNoArbitrage P

/-- Cross-profile recombination cannot create a free hedge: any cancellation
benefit is charged in the residual ledger. -/
def CrossProfileCancellationCharged (F : PricingProfileFamily) : Prop :=
  F.residualPayoff ≤ F.residualPrice

/-- Branch-local limit-passage certificate for one profile family. -/
structure ProfileFamilyLimitCertificate (F : PricingProfileFamily) where
  dichotomy : DichotomyPriceSubadditive F
  concentration : ∀ P ∈ F.profiles, ConcentrationImpactCoercive P
  vanishing : ∀ P ∈ F.profiles, VanishingHasNoPayoff P
  null_profiles : ∀ P ∈ F.profiles, NullProfileCapped P
  cross_recombination : CrossProfileCancellationCharged F

lemma sum_payoff_le_sum_price_of_profiles
    {ps : List PricingProfile}
    (h : ∀ P ∈ ps, ProfileNoArbitrage P) :
    (ps.map (fun P => P.payoff)).sum ≤
      (ps.map (fun P => P.price)).sum := by
  induction ps with
  | nil =>
      simp
  | cons P ps ih =>
      have hP : P.payoff ≤ P.price := h P (by simp)
      have hps : ∀ Q ∈ ps, ProfileNoArbitrage Q := by
        intro Q hQ
        exact h Q (by simp [hQ])
      simp [hP, ih hps, add_le_add]

/-- Price subadditivity closes the dichotomy branch for a fixed family. -/
theorem family_no_arbitrage_of_dichotomy
    (F : PricingProfileFamily)
    (h : DichotomyPriceSubadditive F) :
    familyPayoff F ≤ familyPrice F := by
  unfold familyPayoff familyPrice
  exact add_le_add (sum_payoff_le_sum_price_of_profiles h.2.2) h.2.1

/-- The full profile-family certificate implies no family-level arbitrage. -/
theorem family_no_arbitrage_of_limit_certificate
    (F : PricingProfileFamily)
    (h : ProfileFamilyLimitCertificate F) :
    familyPayoff F ≤ familyPrice F :=
  family_no_arbitrage_of_dichotomy F h.dichotomy

/-- Limit-passage bridge: if every global Track B block has a fixed profile
family whose family no-arbitrage implies threshold-defect convexity, then the
existing scalar Track B projection theorem applies. -/
structure PricingKernelProfileLimitBridge where
  profile_family_of_block : FullLedgerBlock → PricingProfileFamily
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        ProfileFamilyLimitCertificate (profile_family_of_block B)
  threshold_defect_of_family_no_arbitrage :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        familyPayoff (profile_family_of_block B) ≤
          familyPrice (profile_family_of_block B) →
            ThresholdDefectConvexity B

/-- The precise bridge theorem: pay the profile limit-passage obligation, and
the already isolated Track B no-survivor theorem follows. -/
theorem no_global_survivor_of_profile_limit_bridge
    (bridge : PricingKernelProfileLimitBridge)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hfamily :
      familyPayoff (bridge.profile_family_of_block B) ≤
        familyPrice (bridge.profile_family_of_block B) :=
    family_no_arbitrage_of_limit_certificate
      (bridge.profile_family_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact hquartic B (bridge.threshold_defect_of_family_no_arbitrage B hglobal hfamily)

/-- Projection-typed variant of the profile limit-passage bridge for one
promoted block. -/
theorem no_global_survivor_of_profile_limit_bridge_with_projection_at_block
    (bridge : PricingKernelProfileLimitBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hprojection : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  have hfamily :
      familyPayoff (bridge.profile_family_of_block B) ≤
        familyPrice (bridge.profile_family_of_block B) :=
    family_no_arbitrage_of_limit_certificate
      (bridge.profile_family_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (bridge.threshold_defect_of_family_no_arbitrage B hglobal hfamily)

/-- Legacy family adapter for older callers. -/
theorem no_global_survivor_of_profile_limit_bridge_with_projection
    (bridge : PricingKernelProfileLimitBridge)
    (hprojection :
      ∀ B : FullLedgerBlock, QuarticSurvivalProjectionReceipt B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B :=
  no_global_survivor_of_profile_limit_bridge_with_projection_at_block
    bridge B hglobal (hprojection B)

end ZtareProofs.NS
