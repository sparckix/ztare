import Mathlib.Tactic
import ZtareProofs.ns_pricing_kernel_limit_passage

/-!
# Countable pricing-kernel limit passage for Track B

This file isolates the next finite-to-infinite bridge after the market-impact
profile skeleton.  It does **not** prove Navier-Stokes regularity.  It proves a
small but useful abstract fact:

if every finite prefix of a predeclared countable profile stream is priced by
the same no-arbitrage kernel, the limiting payoff is approximated from finite
prefixes, and the limiting price dominates every finite prefix price, then no
new arbitrage appears at the countable limit.

The remaining PDE work is to instantiate these abstract hypotheses for an
actual Leray/Sobolev profile decomposition.
-/

namespace ZtareProofs.NS

/-- The finite prefix family of a countable stream of priced profiles. -/
def prefixProfileFamily (P : ℕ → PricingProfile) (n : ℕ) :
    PricingProfileFamily where
  profiles := (List.range n).map P
  residualPrice := 0
  residualPayoff := 0

/-- Price of a finite prefix. -/
def prefixPrice (P : ℕ → PricingProfile) (n : ℕ) : Real :=
  familyPrice (prefixProfileFamily P n)

/-- Payoff of a finite prefix. -/
def prefixPayoff (P : ℕ → PricingProfile) (n : ℕ) : Real :=
  familyPayoff (prefixProfileFamily P n)

/-- Pointwise no-arbitrage implies no-arbitrage on every finite prefix. -/
theorem prefix_no_arbitrage_of_pointwise
    (P : ℕ → PricingProfile)
    (h : ∀ i, ProfileNoArbitrage (P i))
    (n : ℕ) :
    prefixPayoff P n ≤ prefixPrice P n := by
  unfold prefixPayoff prefixPrice
  apply family_no_arbitrage_of_dichotomy
  unfold DichotomyPriceSubadditive
  refine ⟨?_, ?_, ?_⟩
  · dsimp [prefixProfileFamily]
    norm_num
  · dsimp [prefixProfileFamily]
    norm_num
  intro Q hQ
  dsimp [prefixProfileFamily] at hQ
  rcases List.mem_map.mp hQ with ⟨i, _hi, hQi⟩
  rw [← hQi]
  exact h i

/-- A countable priced stream with separately declared limiting price/payoff.
The limit values are abstract because the analytic topology is the missing PDE
obligation, not something this algebraic file should choose post hoc. -/
structure CountablePricingStream where
  profiles : ℕ → PricingProfile
  priceLimit : Real
  payoffLimit : Real

/-- Finite-prefix approximation hypotheses strong enough to pass no-arbitrage
to the countable limit.  These are the "execution slippage" requirements:
finite execution approximates payoff, while infinite execution cannot cost less
than any finite prefix under the fixed pricing kernel. -/
structure CountableLimitCertificate (S : CountablePricingStream) where
  pointwise_no_arbitrage : ∀ i, ProfileNoArbitrage (S.profiles i)
  payoff_approximated_by_prefix :
    ∀ ε : Real, 0 < ε → ∃ n, S.payoffLimit ≤ prefixPayoff S.profiles n + ε
  prefix_price_le_limit :
    ∀ n, prefixPrice S.profiles n ≤ S.priceLimit

/-- Countable limit passage: under finite-prefix approximation and price
lower-semicontinuity, no arbitrage can appear only at infinity. -/
theorem countable_no_arbitrage_of_limit_certificate
    (S : CountablePricingStream)
    (h : CountableLimitCertificate S) :
    S.payoffLimit ≤ S.priceLimit := by
  refine le_of_forall_pos_le_add ?_
  intro ε hε
  obtain ⟨n, hn⟩ := h.payoff_approximated_by_prefix ε hε
  have hpref :
      prefixPayoff S.profiles n ≤ prefixPrice S.profiles n :=
    prefix_no_arbitrage_of_pointwise S.profiles h.pointwise_no_arbitrage n
  have hprice : prefixPrice S.profiles n ≤ S.priceLimit :=
    h.prefix_price_le_limit n
  calc
    S.payoffLimit ≤ prefixPayoff S.profiles n + ε := hn
    _ ≤ prefixPrice S.profiles n + ε := by linarith
    _ ≤ S.priceLimit + ε := by linarith

/-- A countable limit certificate is impossible if the declared limiting payoff
exceeds the declared limiting price. -/
theorem no_countable_limit_certificate_of_limit_arbitrage
    (S : CountablePricingStream)
    (harb : S.priceLimit < S.payoffLimit) :
    ¬ CountableLimitCertificate S := by
  intro h
  have hnoarb : S.payoffLimit ≤ S.priceLimit :=
    countable_no_arbitrage_of_limit_certificate S h
  exact not_lt_of_ge hnoarb harb

/-- A nonnegative profile price is contained in the finite prefix ending at
that profile.  This is the elementary countable-limit "market impact cannot
smear away" fact used by the profile-limit bridge. -/
lemma profile_price_le_prefix_price_succ_of_nonnegative
    (P : ℕ → PricingProfile)
    (h : ∀ i : ℕ, 0 ≤ (P i).price)
    (n : ℕ) :
    (P n).price ≤ prefixPrice P (n + 1) := by
  unfold prefixPrice familyPrice prefixProfileFamily
  rw [List.range_succ]
  simp only [List.map_append, List.map_singleton, List.sum_append,
    List.sum_singleton]
  have hprefix :
      0 ≤ (List.map (fun x => (P x).price) (List.range n)).sum := by
    apply List.sum_nonneg
    intro x hx
    rcases List.mem_map.mp hx with ⟨i, _hi, hxi⟩
    rw [← hxi]
    exact h i
  simp [List.map_map, Function.comp_def]
  linarith

/-- A finite-price countable LSC certificate cannot contain pointwise-unbounded
nonnegative profile prices.

This is the profile-limit analogue of the low-high prefix falsifier: if an
infinite cascade requires profiles whose declared prices diverge, then the
limit price cannot remain finite while dominating every finite prefix. -/
theorem no_countable_limit_certificate_of_pointwise_unbounded_prices
    (S : CountablePricingStream)
    (hprice_nonnegative :
      ∀ i : ℕ, 0 ≤ (S.profiles i).price)
    (hunbounded :
      ∀ B : Real, ∃ i : ℕ, B < (S.profiles i).price) :
    ¬ CountableLimitCertificate S := by
  intro h
  obtain ⟨i, hi⟩ := hunbounded S.priceLimit
  have hsingle :
      (S.profiles i).price ≤ prefixPrice S.profiles (i + 1) :=
    profile_price_le_prefix_price_succ_of_nonnegative
      S.profiles hprice_nonnegative i
  have hlimit :
      prefixPrice S.profiles (i + 1) ≤ S.priceLimit :=
    h.prefix_price_le_limit (i + 1)
  have hprice_le_limit :
      (S.profiles i).price ≤ S.priceLimit :=
    hsingle.trans hlimit
  exact not_lt_of_ge hprice_le_limit hi

/-- A finite-price countable LSC certificate also cannot contain pointwise
unbounded profile payoffs, provided profile prices are nonnegative.

Pointwise no-arbitrage converts each payoff spike into a price spike, and the
finite-prefix price lower-semicontinuity then forces that spike below the same
declared limit price.  This is the countable profile analogue of "harmonic
gain cannot smear through the weak limit for free." -/
theorem no_countable_limit_certificate_of_pointwise_unbounded_payoffs
    (S : CountablePricingStream)
    (hprice_nonnegative :
      ∀ i : ℕ, 0 ≤ (S.profiles i).price)
    (hunbounded :
      ∀ B : Real, ∃ i : ℕ, B < (S.profiles i).payoff) :
    ¬ CountableLimitCertificate S := by
  intro h
  obtain ⟨i, hi⟩ := hunbounded S.priceLimit
  have hpoint :
      (S.profiles i).payoff ≤ (S.profiles i).price :=
    h.pointwise_no_arbitrage i
  have hprice_spike :
      S.priceLimit < (S.profiles i).price :=
    lt_of_lt_of_le hi hpoint
  have hsingle :
      (S.profiles i).price ≤ prefixPrice S.profiles (i + 1) :=
    profile_price_le_prefix_price_succ_of_nonnegative
      S.profiles hprice_nonnegative i
  have hlimit :
      prefixPrice S.profiles (i + 1) ≤ S.priceLimit :=
    h.prefix_price_le_limit (i + 1)
  have hprice_le_limit :
      (S.profiles i).price ≤ S.priceLimit :=
    hsingle.trans hlimit
  exact not_lt_of_ge hprice_le_limit hprice_spike

/-- A countable pricing bridge for global Track B blocks. -/
structure CountablePricingKernelBridge where
  stream_of_block : FullLedgerBlock → CountablePricingStream
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        CountableLimitCertificate (stream_of_block B)
  threshold_defect_of_countable_no_arbitrage :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        (stream_of_block B).payoffLimit ≤ (stream_of_block B).priceLimit →
          ThresholdDefectConvexity B

/-- Countable bridge theorem: once the PDE supplies the fixed countable pricing
certificate, the existing Track B no-survivor theorem applies. -/
theorem no_global_survivor_of_countable_pricing_bridge
    (bridge : CountablePricingKernelBridge)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hnoarb :
      (bridge.stream_of_block B).payoffLimit ≤
        (bridge.stream_of_block B).priceLimit :=
    countable_no_arbitrage_of_limit_certificate
      (bridge.stream_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact hquartic B
    (bridge.threshold_defect_of_countable_no_arbitrage B hglobal hnoarb)

/-- Projection-typed variant of the countable pricing bridge for one promoted
block. -/
theorem no_global_survivor_of_countable_pricing_bridge_with_projection_at_block
    (bridge : CountablePricingKernelBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hprojection : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  have hnoarb :
      (bridge.stream_of_block B).payoffLimit ≤
        (bridge.stream_of_block B).priceLimit :=
    countable_no_arbitrage_of_limit_certificate
      (bridge.stream_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (bridge.threshold_defect_of_countable_no_arbitrage B hglobal hnoarb)

/-- Legacy family adapter for older callers. -/
theorem no_global_survivor_of_countable_pricing_bridge_with_projection
    (bridge : CountablePricingKernelBridge)
    (hprojection :
      ∀ B : FullLedgerBlock, QuarticSurvivalProjectionReceipt B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B :=
  no_global_survivor_of_countable_pricing_bridge_with_projection_at_block
    bridge B hglobal (hprojection B)

end ZtareProofs.NS
