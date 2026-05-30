import Mathlib.Tactic
import ZtareProofs.ns_littlewood_paley_profile_bridge
import ZtareProofs.ns_littlewood_paley_paraproduct_bridge

/-!
# Profile-limit lower-semicontinuity boss fight

This file isolates the small proof object behind the current Track B
profile-limit passage:

* finite prefixes are already no-survivor/no-arbitrage;
* the limiting payoff is seen by finite prefixes;
* the limiting price is lower-semicontinuous against those prefixes.

It also proves a tiny anti-tautology witness: finite-prefix no-survivor plus
payoff approximation still does not imply limit no-survivor if the limiting
price is allowed to drop below the prefix prices.
-/

namespace ZtareProofs.NS

/-- Minimal stream interface for the Boss Fight 3 limit passage.  It deliberately
does not choose a PDE topology; the analytic proof must instantiate the four
real-valued fields from a fixed profile/Littlewood-Paley decomposition. -/
structure ProfileLimitStream where
  prefixPayoff : ℕ → Real
  prefixPrice : ℕ → Real
  payoffLimit : Real
  priceLimit : Real

/-- Every finite prefix is already below the declared finite-prefix price. -/
def ProfileFinitePrefixNoSurvivor (S : ProfileLimitStream) : Prop :=
  ∀ n, S.prefixPayoff n ≤ S.prefixPrice n

/-- The limiting payoff cannot hide from all finite prefixes. -/
def ProfilePayoffApproximatedByPrefixes (S : ProfileLimitStream) : Prop :=
  ∀ ε : Real, 0 < ε → ∃ n, S.payoffLimit ≤ S.prefixPayoff n + ε

/-- Lower-semicontinuity in the pricing direction needed by Track B: the limit
price cannot be cheaper than any finite prefix admitted by the fixed
decomposition. -/
def ProfilePrefixPriceLowerSemicontinuous (S : ProfileLimitStream) : Prop :=
  ∀ n, S.prefixPrice n ≤ S.priceLimit

/-- The assembled lower-semicontinuity certificate. -/
structure ProfileLimitLSCCertificate (S : ProfileLimitStream) where
  finite_prefix_no_survivor : ProfileFinitePrefixNoSurvivor S
  payoff_approximated_by_prefix :
    ProfilePayoffApproximatedByPrefixes S
  prefix_price_lsc : ProfilePrefixPriceLowerSemicontinuous S

/-- Boss Fight 3 adapter: finite-prefix no-survivor plus payoff approximation
and price lower-semicontinuity rules out a survivor born only at the profile
limit. -/
theorem profile_limit_no_survivor_of_lsc_certificate
    (S : ProfileLimitStream)
    (h : ProfileLimitLSCCertificate S) :
    S.payoffLimit ≤ S.priceLimit := by
  refine le_of_forall_pos_le_add ?_
  intro ε hε
  obtain ⟨n, hn⟩ := h.payoff_approximated_by_prefix ε hε
  have hprefix : S.prefixPayoff n ≤ S.prefixPrice n :=
    h.finite_prefix_no_survivor n
  have hlsc : S.prefixPrice n ≤ S.priceLimit :=
    h.prefix_price_lsc n
  calc
    S.payoffLimit ≤ S.prefixPayoff n + ε := hn
    _ ≤ S.prefixPrice n + ε := by linarith
    _ ≤ S.priceLimit + ε := by linarith

/-- Anti-tautology witness: even if every finite prefix is no-survivor and the
payoff is exactly approximated by finite prefixes, the limit can be a survivor
when the price-lower-semicontinuity field is absent. -/
theorem finite_prefix_no_survivor_and_payoff_approx_not_enough_without_lsc :
    ∃ S : ProfileLimitStream,
      ProfileFinitePrefixNoSurvivor S ∧
        ProfilePayoffApproximatedByPrefixes S ∧
          S.priceLimit < S.payoffLimit := by
  refine ⟨
    { prefixPayoff := fun _ => 1
      prefixPrice := fun _ => 1
      payoffLimit := 1
      priceLimit := 0 },
    ?_⟩
  refine ⟨?_, ?_, ?_⟩
  · intro n
    norm_num
  · intro ε hε
    refine ⟨0, ?_⟩
    linarith
  · norm_num

/-- A single underpriced finite prefix falsifies an alleged profile-limit LSC
certificate.

This is the finite diagnostic form of Boss Fight 3: if the fixed topology lets
one charged finite prefix cost more than the declared limiting price, then the
limit-passage certificate cannot be the claimed one. -/
theorem no_profile_lsc_certificate_of_prefix_price_drop
    (S : ProfileLimitStream)
    (n : ℕ)
    (hdrop : S.priceLimit < S.prefixPrice n) :
    ¬ ProfileLimitLSCCertificate S := by
  intro h
  exact not_lt_of_ge (h.prefix_price_lsc n) hdrop

/-- View an existing countable pricing stream through the Boss Fight 3
lower-semicontinuity interface. -/
def profileLimitStreamOfCountable (S : CountablePricingStream) :
    ProfileLimitStream where
  prefixPayoff := prefixPayoff S.profiles
  prefixPrice := prefixPrice S.profiles
  payoffLimit := S.payoffLimit
  priceLimit := S.priceLimit

/-- The countable certificate from the earlier file is exactly an LSC
certificate once finite-prefix no-survivor has been derived from pointwise
profile no-arbitrage. -/
def profile_lsc_certificate_of_countable_limit
    (S : CountablePricingStream)
    (h : CountableLimitCertificate S) :
    ProfileLimitLSCCertificate (profileLimitStreamOfCountable S) where
  finite_prefix_no_survivor := by
    intro n
    exact prefix_no_arbitrage_of_pointwise S.profiles h.pointwise_no_arbitrage n
  payoff_approximated_by_prefix := h.payoff_approximated_by_prefix
  prefix_price_lsc := h.prefix_price_le_limit

/-- The old countable limit theorem factors through the Boss Fight 3 LSC
adapter. -/
theorem countable_no_arbitrage_via_profile_lsc
    (S : CountablePricingStream)
    (h : CountableLimitCertificate S) :
    S.payoffLimit ≤ S.priceLimit :=
  profile_limit_no_survivor_of_lsc_certificate
    (profileLimitStreamOfCountable S)
    (profile_lsc_certificate_of_countable_limit S h)

/-- View the Littlewood-Paley shell stream through the same abstract interface. -/
def profileLimitStreamOfLPShell (S : LPShellPricingStream) :
    ProfileLimitStream where
  prefixPayoff := lpPrefixPayoff S
  prefixPrice := lpPrefixPrice S
  payoffLimit := S.payoffLimit
  priceLimit := S.priceLimit

/-- LP shell limit certificates also instantiate the same lower-semicontinuity
adapter.  This keeps Boss Fight 3 targeted at the analytic LSC/payoff fields
instead of another finite-prefix theorem. -/
def profile_lsc_certificate_of_lp_shell_limit
    (S : LPShellPricingStream)
    (h : LPShellLimitCertificate S) :
    ProfileLimitLSCCertificate (profileLimitStreamOfLPShell S) where
  finite_prefix_no_survivor := by
    intro n
    exact lp_prefix_no_arbitrage_of_certificate S n (h.prefix_certificate n)
  payoff_approximated_by_prefix := h.payoff_approximated_by_prefix
  prefix_price_lsc := h.prefix_price_le_limit

/-- The LP shell limit passage factors through the Boss Fight 3 LSC adapter. -/
theorem lp_shell_no_arbitrage_via_profile_lsc
    (S : LPShellPricingStream)
    (h : LPShellLimitCertificate S) :
    S.payoffLimit ≤ S.priceLimit :=
  profile_limit_no_survivor_of_lsc_certificate
    (profileLimitStreamOfLPShell S)
    (profile_lsc_certificate_of_lp_shell_limit S h)

/-- View the LP/Bony paraproduct stream through the same Boss Fight 3 LSC
interface.  This removes one more abstraction gap: the branch receipts for
low-high, high-high, same-shell, and remainder terms must all survive the same
prefix-price lower-semicontinuity passage. -/
def profileLimitStreamOfLPParaproduct
    (S : LPParaproductPricingStream) :
    ProfileLimitStream where
  prefixPayoff := fun n => interactionFamilyPayoff (S.prefixFamily n)
  prefixPrice := fun n => interactionFamilyPrice (S.prefixFamily n)
  payoffLimit := S.payoffLimit
  priceLimit := S.priceLimit

/-- LP/Bony paraproduct limit certificates instantiate the Boss Fight 3 LSC
certificate directly. -/
def profile_lsc_certificate_of_lp_paraproduct_limit
    (S : LPParaproductPricingStream)
    (h : LPParaproductLimitCertificate S) :
    ProfileLimitLSCCertificate (profileLimitStreamOfLPParaproduct S) where
  finite_prefix_no_survivor := by
    intro n
    exact interaction_family_no_arbitrage_of_certificate
      (S.prefixFamily n) (h.prefix_certificate n)
  payoff_approximated_by_prefix := h.payoff_approximated_by_prefix
  prefix_price_lsc := h.prefix_price_le_limit

/-- The LP/Bony paraproduct countable limit factors through the Boss Fight 3
LSC adapter. -/
theorem lp_paraproduct_no_arbitrage_via_profile_lsc
    (S : LPParaproductPricingStream)
    (h : LPParaproductLimitCertificate S) :
    S.payoffLimit ≤ S.priceLimit :=
  profile_limit_no_survivor_of_lsc_certificate
    (profileLimitStreamOfLPParaproduct S)
    (profile_lsc_certificate_of_lp_paraproduct_limit S h)

/-- Minimal finite-prefix family for the paraproduct LSC anti-tautology
witness.  Every prefix is exactly no-arbitrage, but this says nothing about
the limiting price field. -/
def paraproductSafePrefixFamily : LPInteractionFamily where
  terms :=
    [{ interactionClass := LPParaproductClass.highHigh
       price := 1
       payoff := 1 }]
  residualPrice := 0
  residualPayoff := 0

theorem paraproduct_safe_prefix_family_certificate :
    LPInteractionFamilyCertificate paraproductSafePrefixFamily := by
  refine ⟨?_, ?_, ?_⟩
  · norm_num [paraproductSafePrefixFamily]
  · norm_num [paraproductSafePrefixFamily]
  · intro T hT
    have hT' :
        T =
          { interactionClass := LPParaproductClass.highHigh
            price := 1
            payoff := 1 } := by
      simpa [paraproductSafePrefixFamily] using hT
    rw [hT']
    unfold InteractionNoArbitrage
    norm_num

/-- Paraproduct-specific anti-tautology witness.

Even if every finite LP/Bony prefix is charged and the limiting payoff is
visible from finite prefixes, a survivor can appear if the limiting price is
allowed to drop.  Therefore Boss Fight 3 must prove the paraproduct
`prefix_price_le_limit` field; finite branch receipts alone are not enough. -/
theorem paraproduct_prefix_safe_and_payoff_approx_not_enough_without_lsc :
    ∃ S : LPParaproductPricingStream,
      (∀ n, LPInteractionFamilyCertificate (S.prefixFamily n)) ∧
        (∀ ε : Real, 0 < ε →
          ∃ n, S.payoffLimit ≤
            interactionFamilyPayoff (S.prefixFamily n) + ε) ∧
          S.priceLimit < S.payoffLimit := by
  refine ⟨
    { prefixFamily := fun _ => paraproductSafePrefixFamily
      priceLimit := 0
      payoffLimit := 1 },
    ?_⟩
  refine ⟨?_, ?_, ?_⟩
  · intro n
    exact paraproduct_safe_prefix_family_certificate
  · intro ε hε
    refine ⟨0, ?_⟩
    norm_num [interactionFamilyPayoff, paraproductSafePrefixFamily]
    exact le_of_lt hε
  · norm_num

/-- A single underpriced finite LP/Bony prefix falsifies the paraproduct
limit certificate. -/
theorem no_lp_paraproduct_lsc_certificate_of_prefix_price_drop
    (S : LPParaproductPricingStream)
    (n : ℕ)
    (hdrop :
      S.priceLimit < interactionFamilyPrice (S.prefixFamily n)) :
    ¬ LPParaproductLimitCertificate S := by
  intro h
  exact not_lt_of_ge (h.prefix_price_le_limit n) hdrop

/-- The same one-prefix price-drop falsifier after embedding the LP/Bony stream
into the abstract profile-limit interface. -/
theorem no_profile_lsc_certificate_of_lp_paraproduct_price_drop
    (S : LPParaproductPricingStream)
    (n : ℕ)
    (hdrop :
      S.priceLimit < interactionFamilyPrice (S.prefixFamily n)) :
    ¬ ProfileLimitLSCCertificate (profileLimitStreamOfLPParaproduct S) := by
  exact no_profile_lsc_certificate_of_prefix_price_drop
    (profileLimitStreamOfLPParaproduct S) n hdrop

/-- A block-level bridge that exposes the remaining PDE obligation in its
smallest form: construct a fixed profile-limit stream for each global block,
prove the LSC certificate, and show that limit no-survivor implies the existing
threshold-defect condition. -/
structure ProfileLimitLSCBridge where
  stream_of_block : FullLedgerBlock → ProfileLimitStream
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        ProfileLimitLSCCertificate (stream_of_block B)
  threshold_defect_of_limit_no_survivor :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        (stream_of_block B).payoffLimit ≤ (stream_of_block B).priceLimit →
          ThresholdDefectConvexity B

/-- Conditional global no-survivor theorem for the isolated LSC boss-fight
bridge. -/
theorem no_global_survivor_of_profile_limit_lsc_bridge
    (bridge : ProfileLimitLSCBridge)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hlimit :
      (bridge.stream_of_block B).payoffLimit ≤
        (bridge.stream_of_block B).priceLimit :=
    profile_limit_no_survivor_of_lsc_certificate
      (bridge.stream_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact hquartic B
    (bridge.threshold_defect_of_limit_no_survivor B hglobal hlimit)

/-- Projection-typed variant of the isolated profile-LSC boss-fight bridge for
one promoted block. -/
theorem no_global_survivor_of_profile_limit_lsc_bridge_with_projection_at_block
    (bridge : ProfileLimitLSCBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hprojection : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  have hlimit :
      (bridge.stream_of_block B).payoffLimit ≤
        (bridge.stream_of_block B).priceLimit :=
    profile_limit_no_survivor_of_lsc_certificate
      (bridge.stream_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (bridge.threshold_defect_of_limit_no_survivor B hglobal hlimit)

/-- Legacy family adapter for older callers. -/
theorem no_global_survivor_of_profile_limit_lsc_bridge_with_projection
    (bridge : ProfileLimitLSCBridge)
    (hprojection :
      ∀ B : FullLedgerBlock, QuarticSurvivalProjectionReceipt B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B :=
  no_global_survivor_of_profile_limit_lsc_bridge_with_projection_at_block
    bridge B hglobal (hprojection B)

end ZtareProofs.NS
