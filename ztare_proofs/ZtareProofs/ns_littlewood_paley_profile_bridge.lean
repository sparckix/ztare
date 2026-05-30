import Mathlib.Tactic
import ZtareProofs.ns_trackb_profile_decomposition_spine

/-!
# Littlewood-Paley shell bridge for Track B

This file is one layer more concrete than the abstract profile-decomposition
spine.  It still does **not** prove Navier-Stokes regularity.  It states the
next non-tautological bridge in dyadic shell language:

* the shell stream is fixed before payoff is scored;
* each finite shell prefix is charged by the same Leray pricing ledger;
* shell-cross residual payoff is charged as residual price;
* limiting payoff is approximated by finite prefixes;
* limiting price is lower semicontinuous against finite prefixes.

If those analytic hypotheses are supplied by a real Littlewood-Paley/profile
decomposition theorem, then no above-wall Track B survivor can appear only at
the infinite-shell limit.
-/

namespace ZtareProofs.NS

/-- A shell index is dyadic in the intended application.  Keeping this as `ℕ`
prevents this file from choosing a topology or frequency lattice after seeing
the profitable route. -/
abbrev LPShellIndex := ℕ

/-- A fixed Littlewood-Paley shell stream with separately declared limit values.

`shellProfile j` is the priced profile on dyadic shell `j`.  `crossPrice j`
and `crossPayoff j` are the declared residual/cross ledger terms exposed when
the first `j` shell interactions are admitted.  `coherencePrice j` and
`coherencePayoff j` are the explicit beat/backscatter or inner-product
coherence terms exposed by Phase 5IH/5II.  The concrete PDE theorem must
define these from the fixed Leray decomposition, not from an observed surplus.
-/
structure LPShellPricingStream where
  shellProfile : LPShellIndex → PricingProfile
  crossPrice : LPShellIndex → Real
  crossPayoff : LPShellIndex → Real
  coherencePrice : LPShellIndex → Real
  coherencePayoff : LPShellIndex → Real
  priceLimit : Real
  payoffLimit : Real

/-- Sum the first `n` terms of a shell-indexed real sequence. -/
def shellPrefixSum (a : LPShellIndex → Real) (n : ℕ) : Real :=
  ((List.range n).map a).sum

/-- Finite Littlewood-Paley shell prefix as a pricing profile family, including
the cross-shell residual ledger exposed up to the prefix. -/
def lpPrefixProfileFamily (S : LPShellPricingStream) (n : ℕ) :
    PricingProfileFamily where
  profiles := (List.range n).map S.shellProfile
  residualPrice := shellPrefixSum S.crossPrice n + shellPrefixSum S.coherencePrice n
  residualPayoff := shellPrefixSum S.crossPayoff n + shellPrefixSum S.coherencePayoff n

/-- A positive finite LP shell prefix has at least one declared profile.

This is the concrete LP source-side witness needed by scalar-alignment routes:
the nonemptiness comes from the fixed shell prefix itself, not from a later
payoff-dependent profile choice. -/
theorem lpPrefixProfileFamily_profiles_ne_nil_of_pos
    (S : LPShellPricingStream) {n : ℕ} (hn : 0 < n) :
    (lpPrefixProfileFamily S n).profiles ≠ [] := by
  cases n with
  | zero => exact (Nat.not_lt_zero 0 hn).elim
  | succ n =>
      intro hnil
      have hmem :
          S.shellProfile 0 ∈ (lpPrefixProfileFamily S (n + 1)).profiles := by
        change S.shellProfile 0 ∈ (List.range (n + 1)).map S.shellProfile
        exact List.mem_map.mpr ⟨0, by simp, rfl⟩
      rw [hnil] at hmem
      simp at hmem

/-- A positive finite LP shell prefix supplies the profile-membership witness
used by residual-only anti-tautology guards. -/
theorem lpPrefixProfileFamily_profile_mem_of_pos
    (S : LPShellPricingStream) {n : ℕ} (hn : 0 < n) :
    ∃ P : PricingProfile, P ∈ (lpPrefixProfileFamily S n).profiles := by
  cases n with
  | zero => exact (Nat.not_lt_zero 0 hn).elim
  | succ n =>
      refine ⟨S.shellProfile 0, ?_⟩
      change S.shellProfile 0 ∈ (List.range (n + 1)).map S.shellProfile
      exact List.mem_map.mpr ⟨0, by simp, rfl⟩

/-- Price of a finite LP shell prefix. -/
def lpPrefixPrice (S : LPShellPricingStream) (n : ℕ) : Real :=
  familyPrice (lpPrefixProfileFamily S n)

/-- Payoff of a finite LP shell prefix. -/
def lpPrefixPayoff (S : LPShellPricingStream) (n : ℕ) : Real :=
  familyPayoff (lpPrefixProfileFamily S n)

/-- Definitional bridge from a finite LP profile family to its named prefix
price.  This keeps later source constructors from unfolding the LP prefix by
hand. -/
theorem familyPrice_lpPrefixProfileFamily_eq_lpPrefixPrice
    (S : LPShellPricingStream) (n : ℕ) :
    familyPrice (lpPrefixProfileFamily S n) = lpPrefixPrice S n := rfl

/-- Definitional bridge from a finite LP profile family to its named prefix
payoff. -/
theorem familyPayoff_lpPrefixProfileFamily_eq_lpPrefixPayoff
    (S : LPShellPricingStream) (n : ℕ) :
    familyPayoff (lpPrefixProfileFamily S n) = lpPrefixPayoff S n := rfl

/-- Source object for the stronger claim that one positive finite LP prefix is
not merely approximating the declared limit ledger, but is exactly the selected
limit ledger.  A plain `LPShellLimitCertificate` does not provide this. -/
structure LPPrefixLimitIdentificationSource
    (S : LPShellPricingStream) (n : ℕ) where
  prefix_pos : 0 < n
  payoff_matches_limit : lpPrefixPayoff S n = S.payoffLimit
  price_matches_limit : lpPrefixPrice S n = S.priceLimit

theorem familyPayoff_lpPrefixProfileFamily_eq_limit_of_identification
    {S : LPShellPricingStream} {n : ℕ}
    (h : LPPrefixLimitIdentificationSource S n) :
    familyPayoff (lpPrefixProfileFamily S n) = S.payoffLimit := by
  rw [familyPayoff_lpPrefixProfileFamily_eq_lpPrefixPayoff,
    h.payoff_matches_limit]

theorem familyPrice_lpPrefixProfileFamily_eq_limit_of_identification
    {S : LPShellPricingStream} {n : ℕ}
    (h : LPPrefixLimitIdentificationSource S n) :
    familyPrice (lpPrefixProfileFamily S n) = S.priceLimit := by
  rw [familyPrice_lpPrefixProfileFamily_eq_lpPrefixPrice,
    h.price_matches_limit]

/-- Domain-indexed source object for exact endpoint identification of a finite
LP prefix.  This is intentionally not Track-B-specific: callers choose the
domain predicate and endpoint functions.  The object says the selected positive
prefix was fixed before payoff scoring and its finite prefix ledgers identify
the desired endpoint values exactly. -/
structure LPPrefixEndpointIdentificationSource
    {α : Type} (Domain : α → Prop)
    (lp_stream_of : α → LPShellPricingStream)
    (prefix_len_of : α → ℕ)
    (payoffEndpoint priceEndpoint : α → Real) where
  prefix_declared_before_payoff :
    ∀ a : α, Domain a → Prop
  prefix_declared_before_payoff_paid :
    ∀ a : α, (h : Domain a) → prefix_declared_before_payoff a h
  prefix_pos :
    ∀ a : α, Domain a → 0 < prefix_len_of a
  payoff_identifies :
    ∀ a : α, (h : Domain a) →
      lpPrefixPayoff (lp_stream_of a) (prefix_len_of a) =
        payoffEndpoint a
  price_identifies :
    ∀ a : α, (h : Domain a) →
      lpPrefixPrice (lp_stream_of a) (prefix_len_of a) =
        priceEndpoint a

/-- Falsifier surface for exact LP-prefix endpoint identification.  This names
the four ways an apparent finite-prefix endpoint match can be illicit without
assuming any Navier-Stokes-specific type. -/
inductive LPPrefixEndpointIdentificationFalsifier
    {α : Type} (Domain : α → Prop)
    (lp_stream_of : α → LPShellPricingStream)
    (prefix_len_of : α → ℕ)
    (payoffEndpoint priceEndpoint : α → Real)
    (prefix_declared_before_payoff :
      ∀ a : α, Domain a → Prop) : Prop
  | prefix_not_declared_before_payoff :
      (∃ a : α, ∃ h : Domain a,
        ¬ prefix_declared_before_payoff a h) →
        LPPrefixEndpointIdentificationFalsifier
          Domain lp_stream_of prefix_len_of payoffEndpoint priceEndpoint
          prefix_declared_before_payoff
  | nonpositive_prefix :
      (∃ a : α, ∃ _ : Domain a, ¬ 0 < prefix_len_of a) →
        LPPrefixEndpointIdentificationFalsifier
          Domain lp_stream_of prefix_len_of payoffEndpoint priceEndpoint
          prefix_declared_before_payoff
  | payoff_mismatch :
      (∃ a : α, ∃ _ : Domain a,
        lpPrefixPayoff (lp_stream_of a) (prefix_len_of a) ≠
          payoffEndpoint a) →
        LPPrefixEndpointIdentificationFalsifier
          Domain lp_stream_of prefix_len_of payoffEndpoint priceEndpoint
          prefix_declared_before_payoff
  | price_mismatch :
      (∃ a : α, ∃ _ : Domain a,
        lpPrefixPrice (lp_stream_of a) (prefix_len_of a) ≠
          priceEndpoint a) →
        LPPrefixEndpointIdentificationFalsifier
          Domain lp_stream_of prefix_len_of payoffEndpoint priceEndpoint
          prefix_declared_before_payoff

theorem no_lp_prefix_endpoint_identification_falsifier_of_source
    {α : Type} {Domain : α → Prop}
    {lp_stream_of : α → LPShellPricingStream}
    {prefix_len_of : α → ℕ}
    {payoffEndpoint priceEndpoint : α → Real}
    (source :
      LPPrefixEndpointIdentificationSource Domain lp_stream_of prefix_len_of
        payoffEndpoint priceEndpoint) :
    ¬ LPPrefixEndpointIdentificationFalsifier
        Domain lp_stream_of prefix_len_of payoffEndpoint priceEndpoint
        source.prefix_declared_before_payoff := by
  intro hbad
  cases hbad with
  | prefix_not_declared_before_payoff h =>
      rcases h with ⟨a, hdomain, hmissing⟩
      exact hmissing (source.prefix_declared_before_payoff_paid a hdomain)
  | nonpositive_prefix h =>
      rcases h with ⟨a, hdomain, hnonpos⟩
      exact hnonpos (source.prefix_pos a hdomain)
  | payoff_mismatch h =>
      rcases h with ⟨a, hdomain, hmismatch⟩
      exact hmismatch (source.payoff_identifies a hdomain)
  | price_mismatch h =>
      rcases h with ⟨a, hdomain, hmismatch⟩
      exact hmismatch (source.price_identifies a hdomain)

theorem familyPayoff_lpPrefixProfileFamily_eq_endpoint_of_endpoint_identification
    {α : Type} {Domain : α → Prop}
    {lp_stream_of : α → LPShellPricingStream}
    {prefix_len_of : α → ℕ}
    {payoffEndpoint priceEndpoint : α → Real}
    (source :
      LPPrefixEndpointIdentificationSource Domain lp_stream_of prefix_len_of
        payoffEndpoint priceEndpoint)
    {a : α} (hdomain : Domain a) :
    familyPayoff (lpPrefixProfileFamily
        (lp_stream_of a) (prefix_len_of a)) =
      payoffEndpoint a := by
  rw [familyPayoff_lpPrefixProfileFamily_eq_lpPrefixPayoff,
    source.payoff_identifies a hdomain]

theorem familyPrice_lpPrefixProfileFamily_eq_endpoint_of_endpoint_identification
    {α : Type} {Domain : α → Prop}
    {lp_stream_of : α → LPShellPricingStream}
    {prefix_len_of : α → ℕ}
    {payoffEndpoint priceEndpoint : α → Real}
    (source :
      LPPrefixEndpointIdentificationSource Domain lp_stream_of prefix_len_of
        payoffEndpoint priceEndpoint)
    {a : α} (hdomain : Domain a) :
    familyPrice (lpPrefixProfileFamily
        (lp_stream_of a) (prefix_len_of a)) =
      priceEndpoint a := by
  rw [familyPrice_lpPrefixProfileFamily_eq_lpPrefixPrice,
    source.price_identifies a hdomain]

/-- Prefix-local shell certificate: each declared shell is priced and the
cross-shell residual/coherence payoff is charged for this prefix. -/
structure LPPrefixLedgerCertificate (S : LPShellPricingStream) (n : ℕ) where
  residual_price_nonnegative :
    0 ≤ (lpPrefixProfileFamily S n).residualPrice
  shell_no_arbitrage :
    ∀ P ∈ (lpPrefixProfileFamily S n).profiles, ProfileNoArbitrage P
  residual_payoff_charged :
    (lpPrefixProfileFamily S n).residualPayoff ≤
      (lpPrefixProfileFamily S n).residualPrice

/-- A priced LP prefix cannot create no-arbitrage failure. -/
theorem lp_prefix_no_arbitrage_of_certificate
    (S : LPShellPricingStream)
    (n : ℕ)
    (h : LPPrefixLedgerCertificate S n) :
    lpPrefixPayoff S n ≤ lpPrefixPrice S n := by
  unfold lpPrefixPayoff lpPrefixPrice
  apply family_no_arbitrage_of_dichotomy
  unfold DichotomyPriceSubadditive
  refine ⟨?_, ?_, h.shell_no_arbitrage⟩
  · exact h.residual_price_nonnegative
  · exact h.residual_payoff_charged

/-- Countable shell-limit certificate.  This is the LP analogue of execution
slippage / market impact: finite prefixes approximate payoff, while the limit
cannot become cheaper than every finite prefix under the fixed pricing kernel. -/
structure LPShellLimitCertificate (S : LPShellPricingStream) where
  prefix_certificate : ∀ n, LPPrefixLedgerCertificate S n
  payoff_approximated_by_prefix :
    ∀ ε : Real, 0 < ε → ∃ n, S.payoffLimit ≤ lpPrefixPayoff S n + ε
  prefix_price_le_limit :
    ∀ n, lpPrefixPrice S n ≤ S.priceLimit

/-- LP shell limit passage: no profitable trade can appear only after passing
from all finite dyadic prefixes to the countable shell limit. -/
theorem lp_shell_no_arbitrage_of_limit_certificate
    (S : LPShellPricingStream)
    (h : LPShellLimitCertificate S) :
    S.payoffLimit ≤ S.priceLimit := by
  refine le_of_forall_pos_le_add ?_
  intro ε hε
  obtain ⟨n, hn⟩ := h.payoff_approximated_by_prefix ε hε
  have hpref : lpPrefixPayoff S n ≤ lpPrefixPrice S n :=
    lp_prefix_no_arbitrage_of_certificate S n (h.prefix_certificate n)
  have hprice : lpPrefixPrice S n ≤ S.priceLimit :=
    h.prefix_price_le_limit n
  calc
    S.payoffLimit ≤ lpPrefixPayoff S n + ε := hn
    _ ≤ lpPrefixPrice S n + ε := by linarith
    _ ≤ S.priceLimit + ε := by linarith

/-- If LP prefix prices are unbounded, no finite-price shell limit certificate
can exist.  This is the countable-profile version of the market-impact
accumulation fork: either coherence/cross prices remain uniformly lower
semicontinuous into the declared limit price, or the attempted infinite route
has infinite cost. -/
theorem no_lp_shell_limit_certificate_of_unbounded_prefix_prices
    (S : LPShellPricingStream)
    (hunbounded : ∀ B : Real, ∃ n : ℕ, B < lpPrefixPrice S n) :
    ¬ LPShellLimitCertificate S := by
  intro h
  obtain ⟨n, hn⟩ := hunbounded S.priceLimit
  have hle : lpPrefixPrice S n ≤ S.priceLimit :=
    h.prefix_price_le_limit n
  exact not_lt_of_ge hle hn

/-- Zero-valued profile used only for LP-shell non-implication tests. -/
def lpZeroPricingProfile : PricingProfile where
  price := 0
  payoff := 0
  selfTax := 0
  concentrationScale := 0
  isNull := True

/-- A shell stream whose finite prefixes have price `0`, but whose declared
limit price is `1`.  It satisfies the limit certificate because that
certificate only requires prefix prices to lie below the limit price. -/
def lpLimitPriceMismatchCounterexampleStream : LPShellPricingStream where
  shellProfile := fun _ => lpZeroPricingProfile
  crossPrice := fun _ => 0
  crossPayoff := fun _ => 0
  coherencePrice := fun _ => 0
  coherencePayoff := fun _ => 0
  priceLimit := 1
  payoffLimit := 0

theorem lp_limit_price_mismatch_counterexample_certificate :
    LPShellLimitCertificate lpLimitPriceMismatchCounterexampleStream := by
  refine
    { prefix_certificate := ?_,
      payoff_approximated_by_prefix := ?_,
      prefix_price_le_limit := ?_ }
  · intro n
    refine
      { residual_price_nonnegative := ?_,
        shell_no_arbitrage := ?_,
        residual_payoff_charged := ?_ }
    · simp [lpPrefixProfileFamily, lpLimitPriceMismatchCounterexampleStream,
        shellPrefixSum]
    · intro P hP
      have hPsimp : ¬ n = 0 ∧ P = lpZeroPricingProfile := by
        simpa [lpPrefixProfileFamily, lpLimitPriceMismatchCounterexampleStream]
          using hP
      rcases hPsimp with ⟨_, rfl⟩
      norm_num [ProfileNoArbitrage, lpZeroPricingProfile]
    · simp [lpPrefixProfileFamily, lpLimitPriceMismatchCounterexampleStream,
        shellPrefixSum]
  · intro ε hε
    refine ⟨0, ?_⟩
    simpa [lpPrefixPayoff, lpPrefixProfileFamily,
      lpLimitPriceMismatchCounterexampleStream, shellPrefixSum,
      familyPayoff] using le_of_lt hε
  · intro n
    simp [lpPrefixPrice, lpPrefixProfileFamily,
      lpLimitPriceMismatchCounterexampleStream, shellPrefixSum, familyPrice,
      lpZeroPricingProfile]

/-- A positive prefix plus an LP shell limit certificate does not imply exact
identity between the selected finite prefix price and the declared limit
price.  Exact finite-prefix identification is a separate source obligation. -/
theorem lp_shell_limit_certificate_does_not_imply_positive_prefix_price_identity :
    ∃ S : LPShellPricingStream,
      ∃ n : ℕ,
        LPShellLimitCertificate S ∧ 0 < n ∧ lpPrefixPrice S n ≠ S.priceLimit := by
  refine
    ⟨lpLimitPriceMismatchCounterexampleStream, 1,
      lp_limit_price_mismatch_counterexample_certificate, by norm_num, ?_⟩
  norm_num [lpPrefixPrice, lpPrefixProfileFamily,
    lpLimitPriceMismatchCounterexampleStream, shellPrefixSum, familyPrice,
    lpZeroPricingProfile]

/-- The concrete LP-shell bridge for global Track B blocks. -/
structure LittlewoodPaleyShellPricingBridge where
  stream_of_block : FullLedgerBlock → LPShellPricingStream
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        LPShellLimitCertificate (stream_of_block B)
  threshold_defect_of_shell_no_arbitrage :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        (stream_of_block B).payoffLimit ≤ (stream_of_block B).priceLimit →
          ThresholdDefectConvexity B

/-- If a real Littlewood-Paley decomposition supplies the fixed shell pricing
certificate, Track B reduces to the existing full-ledger no-survivor theorem. -/
theorem no_global_survivor_of_littlewood_paley_shell_bridge
    (bridge : LittlewoodPaleyShellPricingBridge)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hnoarb :
      (bridge.stream_of_block B).payoffLimit ≤
        (bridge.stream_of_block B).priceLimit :=
    lp_shell_no_arbitrage_of_limit_certificate
      (bridge.stream_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact hquartic B
    (bridge.threshold_defect_of_shell_no_arbitrage B hglobal hnoarb)

/-- Projection-typed variant of the Littlewood-Paley shell bridge for one
promoted block. -/
theorem no_global_survivor_of_littlewood_paley_shell_bridge_with_projection_at_block
    (bridge : LittlewoodPaleyShellPricingBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hprojection : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  have hnoarb :
      (bridge.stream_of_block B).payoffLimit ≤
        (bridge.stream_of_block B).priceLimit :=
    lp_shell_no_arbitrage_of_limit_certificate
      (bridge.stream_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (bridge.threshold_defect_of_shell_no_arbitrage B hglobal hnoarb)

/-- Legacy family adapter for older callers. -/
theorem no_global_survivor_of_littlewood_paley_shell_bridge_with_projection
    (bridge : LittlewoodPaleyShellPricingBridge)
    (hprojection :
      ∀ B : FullLedgerBlock, QuarticSurvivalProjectionReceipt B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B :=
  no_global_survivor_of_littlewood_paley_shell_bridge_with_projection_at_block
    bridge B hglobal (hprojection B)

/-- Anti-tautology payload for a usable LP-shell certificate.  This is metadata,
not a proof: a shell bridge that lacks these declarations has not fixed the
state-price kernel before scoring the route. -/
structure LPShellAntiTautologyRules where
  shell_decomposition_predeclared : Prop
  observable_class_predeclared : Prop
  cross_terms_charged_before_limit : Prop
  beat_backscatter_coherence_charged_before_limit : Prop
  no_backward_pricing_from_surplus : Prop
  matrix_intertwiners_charged_or_excluded : Prop

end ZtareProofs.NS
