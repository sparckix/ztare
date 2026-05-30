import Mathlib.Tactic
import ZtareProofs.ns_littlewood_paley_paraproduct_bridge

/-!
# Beat/backscatter coherence charge obligation

Phase 5IH/5II/5IK exposed a specific Track B gap: ordinary cross terms and
positive beat/backscatter coherence cannot be bundled into an unnamed residual
after a profitable route is scored.

This file stays abstract.  It proves only scalar accounting facts:

* positive coherence can be priced by Cauchy/Young once the two price channels
  are declared in advance;
* a finite prefix ledger with separately charged ordinary-cross and
  beat/backscatter coherence terms is no-arbitrage;
* a countable LP limit is no-arbitrage if the same uniform charge survives
  prefix-to-limit passage.

The actual PDE theorem is the final obligation: construct the fixed
Littlewood-Paley/Leray charge stream for every global admissible field, with
beat/backscatter prices declared before payoff scoring.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Positive part of a signed payoff.  Negative coherence helps the ledger and
does not need to be charged as positive profit. -/
def positivePart (x : Real) : Real := max x 0

lemma positivePart_nonnegative (x : Real) : 0 ≤ positivePart x := by
  unfold positivePart
  exact le_max_right x 0

lemma positivePart_sq_le_of_sq_le
    {x leftPrice rightPrice : Real}
    (hleft : 0 ≤ leftPrice)
    (hright : 0 ≤ rightPrice)
    (hcauchy : x ^ (2 : Nat) ≤ leftPrice * rightPrice) :
    positivePart x ^ (2 : Nat) ≤ leftPrice * rightPrice := by
  have hprod_nonneg : 0 ≤ leftPrice * rightPrice :=
    mul_nonneg hleft hright
  by_cases hx : x ≤ 0
  · have hmax : positivePart x = 0 := by
      unfold positivePart
      exact max_eq_right hx
    rw [hmax]
    simpa using hprod_nonneg
  · have hx_nonneg : 0 ≤ x := le_of_lt (lt_of_not_ge hx)
    have hmax : positivePart x = x := by
      unfold positivePart
      exact max_eq_left hx_nonneg
    simpa [hmax] using hcauchy

/-- Cauchy plus AM-GM prices the positive part of a signed coherence term. -/
theorem positive_coherence_le_dual_average_of_cauchy
    {coherence leftPrice rightPrice : Real}
    (hleft : 0 ≤ leftPrice)
    (hright : 0 ≤ rightPrice)
    (hcauchy : coherence ^ (2 : Nat) ≤ leftPrice * rightPrice) :
    positivePart coherence ≤ (leftPrice + rightPrice) / 2 := by
  exact vorticity_production_le_dual_average
    hleft hright
    (positivePart_sq_le_of_sq_le hleft hright hcauchy)

/-- Young absorption form for a positive coherence term. -/
theorem positive_coherence_minus_viscous_le_tax_over_four_nu
    {coherence viscousPrice taxPrice nu : Real}
    (hnu : 0 < nu)
    (hvisc : 0 ≤ viscousPrice)
    (htax : 0 ≤ taxPrice)
    (hcauchy : coherence ^ (2 : Nat) ≤ viscousPrice * taxPrice) :
    positivePart coherence - nu * viscousPrice ≤ taxPrice / (4 * nu) := by
  exact production_minus_viscosity_le_self_tax_over_four_nu
    hnu
    (positivePart_nonnegative coherence)
    hvisc
    htax
    (positivePart_sq_le_of_sq_le hvisc htax hcauchy)

/-- A scalar Cauchy receipt for the two positive coherence channels exposed by
the beat/backscatter audits.  The left/right channels are abstract stand-ins
for the concrete LP/Leray norms that a real PDE theorem must supply. -/
structure BeatBackscatterCauchyReceipt where
  beatPayoff : Real
  backscatterPayoff : Real
  beatLeftPrice : Real
  beatRightPrice : Real
  backscatterLeftPrice : Real
  backscatterRightPrice : Real
  beat_left_nonnegative : 0 ≤ beatLeftPrice
  beat_right_nonnegative : 0 ≤ beatRightPrice
  backscatter_left_nonnegative : 0 ≤ backscatterLeftPrice
  backscatter_right_nonnegative : 0 ≤ backscatterRightPrice
  beat_cauchy :
    beatPayoff ^ (2 : Nat) ≤ beatLeftPrice * beatRightPrice
  backscatter_cauchy :
    backscatterPayoff ^ (2 : Nat) ≤
      backscatterLeftPrice * backscatterRightPrice

def beatBackscatterCauchyPrice (R : BeatBackscatterCauchyReceipt) : Real :=
  (R.beatLeftPrice + R.beatRightPrice) / 2 +
    (R.backscatterLeftPrice + R.backscatterRightPrice) / 2

def beatBackscatterPositivePayoff
    (R : BeatBackscatterCauchyReceipt) : Real :=
  positivePart R.beatPayoff + positivePart R.backscatterPayoff

/-- Cauchy/AM-GM charges the two positive coherence channels once their price
channels are fixed. -/
theorem beat_backscatter_positive_payoff_le_cauchy_price
    (R : BeatBackscatterCauchyReceipt) :
    beatBackscatterPositivePayoff R ≤ beatBackscatterCauchyPrice R := by
  unfold beatBackscatterPositivePayoff beatBackscatterCauchyPrice
  have hbeat :
      positivePart R.beatPayoff ≤
        (R.beatLeftPrice + R.beatRightPrice) / 2 :=
    positive_coherence_le_dual_average_of_cauchy
      R.beat_left_nonnegative
      R.beat_right_nonnegative
      R.beat_cauchy
  have hback :
      positivePart R.backscatterPayoff ≤
        (R.backscatterLeftPrice + R.backscatterRightPrice) / 2 :=
    positive_coherence_le_dual_average_of_cauchy
      R.backscatter_left_nonnegative
      R.backscatter_right_nonnegative
      R.backscatter_cauchy
  exact add_le_add hbeat hback

/-- Finite LP prefix ledger with ordinary cross terms separated from
beat/backscatter coherence terms.

`beatBackscatterPayoff` is the extra mixed coherence term between the two
mechanisms.  It is priced by its positive part, just like the individual beat
and backscatter channels. -/
structure BeatBackscatterPrefixChargeReceipt where
  basePayoff : Real
  basePrice : Real
  ordinaryCrossPayoff : Real
  ordinaryCrossPrice : Real
  beatPayoff : Real
  beatPrice : Real
  backscatterPayoff : Real
  backscatterPrice : Real
  beatBackscatterPayoff : Real
  beatBackscatterPrice : Real
  totalPayoff : Real
  totalPrice : Real
  lp_prefix_fixed_before_payoff : Prop
  ordinary_cross_price_declared_before_payoff : Prop
  beat_price_declared_before_payoff : Prop
  backscatter_price_declared_before_payoff : Prop
  beat_backscatter_price_declared_before_payoff : Prop
  no_backward_pricing_from_surplus : Prop
  base_charged : basePayoff ≤ basePrice
  ordinary_cross_charged : ordinaryCrossPayoff ≤ ordinaryCrossPrice
  beat_positive_charged : positivePart beatPayoff ≤ beatPrice
  backscatter_positive_charged :
    positivePart backscatterPayoff ≤ backscatterPrice
  beat_backscatter_positive_charged :
    positivePart beatBackscatterPayoff ≤ beatBackscatterPrice
  total_payoff_split :
    totalPayoff =
      basePayoff + ordinaryCrossPayoff +
        positivePart beatPayoff +
          positivePart backscatterPayoff +
            positivePart beatBackscatterPayoff
  total_price_split :
    totalPrice =
      basePrice + ordinaryCrossPrice +
        beatPrice + backscatterPrice + beatBackscatterPrice

/-- A finite prefix whose base, ordinary-cross, and beat/backscatter coherence
channels are separately charged is no-arbitrage. -/
theorem beat_backscatter_prefix_no_arbitrage_of_receipt
    (R : BeatBackscatterPrefixChargeReceipt) :
    R.totalPayoff ≤ R.totalPrice := by
  rw [R.total_payoff_split, R.total_price_split]
  nlinarith [R.base_charged,
    R.ordinary_cross_charged,
    R.beat_positive_charged,
    R.backscatter_positive_charged,
    R.beat_backscatter_positive_charged]

/-- A proposed zero beat/backscatter price is falsified by any positive
coherence surplus in a prefix that is otherwise fixed. -/
theorem no_zero_beat_backscatter_price_with_positive_coherence
    (R : BeatBackscatterPrefixChargeReceipt)
    (hbeatZero : R.beatPrice = 0)
    (hbackZero : R.backscatterPrice = 0)
    (hbbZero : R.beatBackscatterPrice = 0)
    (hpositive :
      0 <
        positivePart R.beatPayoff +
          positivePart R.backscatterPayoff +
            positivePart R.beatBackscatterPayoff) :
    False := by
  have hbeat :
      positivePart R.beatPayoff ≤ 0 := by
    simpa [hbeatZero] using R.beat_positive_charged
  have hback :
      positivePart R.backscatterPayoff ≤ 0 := by
    simpa [hbackZero] using R.backscatter_positive_charged
  have hbb :
      positivePart R.beatBackscatterPayoff ≤ 0 := by
    simpa [hbbZero] using R.beat_backscatter_positive_charged
  nlinarith [positivePart_nonnegative R.beatPayoff,
    positivePart_nonnegative R.backscatterPayoff,
    positivePart_nonnegative R.beatBackscatterPayoff]

/-- Countable LP charge stream for the beat/backscatter obligation.  The
stream must be fixed by the decomposition; it cannot be selected after seeing
which coherence channel produces surplus. -/
structure LPBeatBackscatterChargeStream where
  prefixReceipt : ℕ → BeatBackscatterPrefixChargeReceipt
  payoffLimit : Real
  priceLimit : Real

/-- Named source for a countable beat/backscatter charge stream.

The stream is still scalar data.  This source receipt records that the scalar
prefixes and limiting price come from a predeclared LP/Leray construction, with
the per-prefix anti-backward-pricing guards actually paid rather than merely
listed as proposition-valued metadata. -/
structure LPBeatBackscatterChargeStreamSource where
  stream : LPBeatBackscatterChargeStream
  lp_leray_source_declared_before_payoff : Prop
  lp_leray_source_declared_before_payoff_paid :
    lp_leray_source_declared_before_payoff
  limit_price_declared_before_payoff : Prop
  limit_price_declared_before_payoff_paid :
    limit_price_declared_before_payoff
  no_posthoc_coherence_stream_substitution : Prop
  no_posthoc_coherence_stream_substitution_paid :
    no_posthoc_coherence_stream_substitution
  prefix_lp_fixed_before_payoff_paid :
    ∀ n, (stream.prefixReceipt n).lp_prefix_fixed_before_payoff
  prefix_ordinary_cross_price_declared_paid :
    ∀ n,
      (stream.prefixReceipt n).ordinary_cross_price_declared_before_payoff
  prefix_beat_price_declared_paid :
    ∀ n, (stream.prefixReceipt n).beat_price_declared_before_payoff
  prefix_backscatter_price_declared_paid :
    ∀ n, (stream.prefixReceipt n).backscatter_price_declared_before_payoff
  prefix_beat_backscatter_price_declared_paid :
    ∀ n,
      (stream.prefixReceipt n).beat_backscatter_price_declared_before_payoff
  prefix_no_backward_pricing_paid :
    ∀ n, (stream.prefixReceipt n).no_backward_pricing_from_surplus

/-- Receipt that a target scalar stream is exactly the stream carried by a
named LP/Leray beat/backscatter source. -/
structure LPBeatBackscatterDerivedStreamReceipt
    (source : LPBeatBackscatterChargeStreamSource)
    (S : LPBeatBackscatterChargeStream) where
  prefix_receipt_eq_source :
    ∀ n, S.prefixReceipt n = source.stream.prefixReceipt n
  payoff_limit_eq_source :
    S.payoffLimit = source.stream.payoffLimit
  price_limit_eq_source :
    S.priceLimit = source.stream.priceLimit
  lp_leray_source_declared_from_source :
    source.lp_leray_source_declared_before_payoff
  limit_price_declared_from_source :
    source.limit_price_declared_before_payoff
  no_posthoc_stream_substitution_from_source :
    source.no_posthoc_coherence_stream_substitution
  prefix_lp_fixed_from_source :
    ∀ n, (S.prefixReceipt n).lp_prefix_fixed_before_payoff
  prefix_ordinary_cross_price_declared_from_source :
    ∀ n, (S.prefixReceipt n).ordinary_cross_price_declared_before_payoff
  prefix_beat_price_declared_from_source :
    ∀ n, (S.prefixReceipt n).beat_price_declared_before_payoff
  prefix_backscatter_price_declared_from_source :
    ∀ n, (S.prefixReceipt n).backscatter_price_declared_before_payoff
  prefix_beat_backscatter_price_declared_from_source :
    ∀ n, (S.prefixReceipt n).beat_backscatter_price_declared_before_payoff
  prefix_no_backward_pricing_from_source :
    ∀ n, (S.prefixReceipt n).no_backward_pricing_from_surplus

/-- Reflexive provenance receipt for the stream carried by a named
beat/backscatter LP/Leray source. -/
def lpBeatBackscatterDerivedStreamReceiptRefl
    (source : LPBeatBackscatterChargeStreamSource) :
    LPBeatBackscatterDerivedStreamReceipt source source.stream where
  prefix_receipt_eq_source := fun _ => rfl
  payoff_limit_eq_source := rfl
  price_limit_eq_source := rfl
  lp_leray_source_declared_from_source :=
    source.lp_leray_source_declared_before_payoff_paid
  limit_price_declared_from_source :=
    source.limit_price_declared_before_payoff_paid
  no_posthoc_stream_substitution_from_source :=
    source.no_posthoc_coherence_stream_substitution_paid
  prefix_lp_fixed_from_source :=
    source.prefix_lp_fixed_before_payoff_paid
  prefix_ordinary_cross_price_declared_from_source :=
    source.prefix_ordinary_cross_price_declared_paid
  prefix_beat_price_declared_from_source :=
    source.prefix_beat_price_declared_paid
  prefix_backscatter_price_declared_from_source :=
    source.prefix_backscatter_price_declared_paid
  prefix_beat_backscatter_price_declared_from_source :=
    source.prefix_beat_backscatter_price_declared_paid
  prefix_no_backward_pricing_from_source :=
    source.prefix_no_backward_pricing_paid

/-- Concrete ways a target beat/backscatter stream can fail to be the stream
carried by its named LP/Leray source. -/
inductive LPBeatBackscatterSourceSubstitutionFalsifier
    (source : LPBeatBackscatterChargeStreamSource)
    (S : LPBeatBackscatterChargeStream)
    (Rprov : LPBeatBackscatterDerivedStreamReceipt source S) : Prop where
  | prefixReceipt (n : ℕ) :
      S.prefixReceipt n ≠ source.stream.prefixReceipt n →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | payoffLimit :
      S.payoffLimit ≠ source.stream.payoffLimit →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | priceLimit :
      S.priceLimit ≠ source.stream.priceLimit →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | missingLPLeraySource :
      ¬ source.lp_leray_source_declared_before_payoff →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | missingLimitPriceSource :
      ¬ source.limit_price_declared_before_payoff →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | posthocStreamSubstitution :
      ¬ source.no_posthoc_coherence_stream_substitution →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | prefixLPNotFixed (n : ℕ) :
      ¬ (S.prefixReceipt n).lp_prefix_fixed_before_payoff →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | prefixOrdinaryCrossNotDeclared (n : ℕ) :
      ¬ (S.prefixReceipt n).ordinary_cross_price_declared_before_payoff →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | prefixBeatNotDeclared (n : ℕ) :
      ¬ (S.prefixReceipt n).beat_price_declared_before_payoff →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | prefixBackscatterNotDeclared (n : ℕ) :
      ¬ (S.prefixReceipt n).backscatter_price_declared_before_payoff →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | prefixBeatBackscatterNotDeclared (n : ℕ) :
      ¬ (S.prefixReceipt n).beat_backscatter_price_declared_before_payoff →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov
  | prefixBackwardPricing (n : ℕ) :
      ¬ (S.prefixReceipt n).no_backward_pricing_from_surplus →
        LPBeatBackscatterSourceSubstitutionFalsifier source S Rprov

/-- A source-derived beat/backscatter stream receipt excludes arbitrary scalar
stream substitution and missing declaration guards. -/
theorem no_lp_beat_backscatter_source_substitution_falsifier
    (source : LPBeatBackscatterChargeStreamSource)
    (S : LPBeatBackscatterChargeStream)
    (R : LPBeatBackscatterDerivedStreamReceipt source S)
    (F : LPBeatBackscatterSourceSubstitutionFalsifier source S R) :
    False := by
  cases F with
  | prefixReceipt n h =>
      exact h (R.prefix_receipt_eq_source n)
  | payoffLimit h =>
      exact h R.payoff_limit_eq_source
  | priceLimit h =>
      exact h R.price_limit_eq_source
  | missingLPLeraySource h =>
      exact h R.lp_leray_source_declared_from_source
  | missingLimitPriceSource h =>
      exact h R.limit_price_declared_from_source
  | posthocStreamSubstitution h =>
      exact h R.no_posthoc_stream_substitution_from_source
  | prefixLPNotFixed n h =>
      exact h (R.prefix_lp_fixed_from_source n)
  | prefixOrdinaryCrossNotDeclared n h =>
      exact h (R.prefix_ordinary_cross_price_declared_from_source n)
  | prefixBeatNotDeclared n h =>
      exact h (R.prefix_beat_price_declared_from_source n)
  | prefixBackscatterNotDeclared n h =>
      exact h (R.prefix_backscatter_price_declared_from_source n)
  | prefixBeatBackscatterNotDeclared n h =>
      exact h (R.prefix_beat_backscatter_price_declared_from_source n)
  | prefixBackwardPricing n h =>
      exact h (R.prefix_no_backward_pricing_from_source n)

/-- Source-level positive-coherence payment package.

This is provenance-only: it exposes that the named LP/Leray source already
carries fixed prefixes, declared beat/backscatter prices, no backward pricing,
and per-prefix positive-part charges. -/
def LPBeatBackscatterSourceUniformPositiveCoherencePaid
    (source : LPBeatBackscatterChargeStreamSource) : Prop :=
  source.lp_leray_source_declared_before_payoff ∧
    source.limit_price_declared_before_payoff ∧
      source.no_posthoc_coherence_stream_substitution ∧
        (∀ n : ℕ,
          (source.stream.prefixReceipt n).lp_prefix_fixed_before_payoff ∧
            (source.stream.prefixReceipt n).ordinary_cross_price_declared_before_payoff ∧
              (source.stream.prefixReceipt n).beat_price_declared_before_payoff ∧
                (source.stream.prefixReceipt n).backscatter_price_declared_before_payoff ∧
                  (source.stream.prefixReceipt n).beat_backscatter_price_declared_before_payoff ∧
                    (source.stream.prefixReceipt n).no_backward_pricing_from_surplus ∧
                      positivePart (source.stream.prefixReceipt n).beatPayoff ≤
                        (source.stream.prefixReceipt n).beatPrice ∧
                      positivePart (source.stream.prefixReceipt n).backscatterPayoff ≤
                        (source.stream.prefixReceipt n).backscatterPrice ∧
                      positivePart (source.stream.prefixReceipt n).beatBackscatterPayoff ≤
                        (source.stream.prefixReceipt n).beatBackscatterPrice)

/-- A named beat/backscatter source pays the uniform positive-coherence
package directly from its source and prefix receipts. -/
theorem lp_beat_backscatter_source_uniform_positive_coherence_paid
    (source : LPBeatBackscatterChargeStreamSource) :
    LPBeatBackscatterSourceUniformPositiveCoherencePaid source := by
  refine
    ⟨source.lp_leray_source_declared_before_payoff_paid,
      source.limit_price_declared_before_payoff_paid,
      source.no_posthoc_coherence_stream_substitution_paid, ?_⟩
  intro n
  exact
    ⟨source.prefix_lp_fixed_before_payoff_paid n,
      source.prefix_ordinary_cross_price_declared_paid n,
      source.prefix_beat_price_declared_paid n,
      source.prefix_backscatter_price_declared_paid n,
      source.prefix_beat_backscatter_price_declared_paid n,
      source.prefix_no_backward_pricing_paid n,
      (source.stream.prefixReceipt n).beat_positive_charged,
      (source.stream.prefixReceipt n).backscatter_positive_charged,
      (source.stream.prefixReceipt n).beat_backscatter_positive_charged⟩

/-- Limit certificate for uniform LP beat/backscatter charging. -/
structure LPBeatBackscatterLimitCertificate
    (S : LPBeatBackscatterChargeStream) where
  payoff_approximated_by_prefix :
    ∀ ε : Real, 0 < ε →
      ∃ n, S.payoffLimit ≤ (S.prefixReceipt n).totalPayoff + ε
  prefix_price_le_limit :
    ∀ n, (S.prefixReceipt n).totalPrice ≤ S.priceLimit

/-- Uniform LP limit passage: charged finite prefixes cannot create a new
beat/backscatter surplus at the countable LP limit. -/
theorem lp_beat_backscatter_no_arbitrage_of_limit_certificate
    (S : LPBeatBackscatterChargeStream)
    (h : LPBeatBackscatterLimitCertificate S) :
    S.payoffLimit ≤ S.priceLimit := by
  refine le_of_forall_pos_le_add ?_
  intro ε hε
  obtain ⟨n, hn⟩ := h.payoff_approximated_by_prefix ε hε
  have hpref :
      (S.prefixReceipt n).totalPayoff ≤
        (S.prefixReceipt n).totalPrice :=
    beat_backscatter_prefix_no_arbitrage_of_receipt
      (S.prefixReceipt n)
  have hprice :
      (S.prefixReceipt n).totalPrice ≤ S.priceLimit :=
    h.prefix_price_le_limit n
  calc
    S.payoffLimit ≤ (S.prefixReceipt n).totalPayoff + ε := hn
    _ ≤ (S.prefixReceipt n).totalPrice + ε := by linarith
    _ ≤ S.priceLimit + ε := by linarith

/-- Prefix-level positive-coherence escape: finite prefixes of the declared
beat/backscatter stream carry arbitrarily large charged payoff while the
candidate still claims one finite limiting price. -/
def LPBeatBackscatterPrefixPayoffUnbounded
    (S : LPBeatBackscatterChargeStream) : Prop :=
  ∀ B : Real, ∃ n : ℕ, B < (S.prefixReceipt n).totalPayoff

/-- A valid uniform beat/backscatter limit certificate rules out prefix payoff
escape in the same fixed stream.  This is the direct finite-prefix diagnostic
for the "charge positive coherence uniformly" obligation. -/
theorem no_unbounded_beat_backscatter_prefix_payoff_under_limit_certificate
    (S : LPBeatBackscatterChargeStream)
    (h : LPBeatBackscatterLimitCertificate S) :
    ¬ LPBeatBackscatterPrefixPayoffUnbounded S := by
  intro hunbounded
  obtain ⟨n, hn⟩ := hunbounded S.priceLimit
  have hpref :
      (S.prefixReceipt n).totalPayoff ≤
        (S.prefixReceipt n).totalPrice :=
    beat_backscatter_prefix_no_arbitrage_of_receipt
      (S.prefixReceipt n)
  have hprice :
      (S.prefixReceipt n).totalPrice ≤ S.priceLimit :=
    h.prefix_price_le_limit n
  exact not_lt_of_ge (hpref.trans hprice) hn

/-- Source-provenance adapter: if a limit certificate is proved for a stream
derived from a named LP/Leray beat/backscatter source, then the same source
stream cannot have unbounded charged payoff prefixes. -/
theorem no_unbounded_source_beat_backscatter_prefix_payoff_of_derived_limit_certificate
    (source : LPBeatBackscatterChargeStreamSource)
    (S : LPBeatBackscatterChargeStream)
    (R : LPBeatBackscatterDerivedStreamReceipt source S)
    (h : LPBeatBackscatterLimitCertificate S) :
    ¬ LPBeatBackscatterPrefixPayoffUnbounded source.stream := by
  have hsource : LPBeatBackscatterLimitCertificate source.stream := by
    refine ⟨?_, ?_⟩
    · intro ε hε
      obtain ⟨n, hn⟩ := h.payoff_approximated_by_prefix ε hε
      refine ⟨n, ?_⟩
      calc
        source.stream.payoffLimit = S.payoffLimit := R.payoff_limit_eq_source.symm
        _ ≤ (S.prefixReceipt n).totalPayoff + ε := hn
        _ = (source.stream.prefixReceipt n).totalPayoff + ε := by
          rw [R.prefix_receipt_eq_source n]
    · intro n
      calc
        (source.stream.prefixReceipt n).totalPrice =
            (S.prefixReceipt n).totalPrice := by
          rw [(R.prefix_receipt_eq_source n).symm]
        _ ≤ S.priceLimit := h.prefix_price_le_limit n
        _ = source.stream.priceLimit := R.price_limit_eq_source
  exact no_unbounded_beat_backscatter_prefix_payoff_under_limit_certificate
    source.stream hsource

/-- Source-provenance adapter for beat/backscatter no-arbitrage.

The scalar limit charge is first transported back to the named LP/Leray source
stream, so downstream closure code cannot use a detached target stream for the
payoff inequality while checking source provenance in a separate side branch. -/
theorem lp_beat_backscatter_no_arbitrage_of_derived_limit_certificate
    (source : LPBeatBackscatterChargeStreamSource)
    (S : LPBeatBackscatterChargeStream)
    (R : LPBeatBackscatterDerivedStreamReceipt source S)
    (h : LPBeatBackscatterLimitCertificate S) :
    source.stream.payoffLimit ≤ source.stream.priceLimit := by
  have hsource : LPBeatBackscatterLimitCertificate source.stream := by
    refine ⟨?_, ?_⟩
    · intro ε hε
      obtain ⟨n, hn⟩ := h.payoff_approximated_by_prefix ε hε
      refine ⟨n, ?_⟩
      calc
        source.stream.payoffLimit = S.payoffLimit := R.payoff_limit_eq_source.symm
        _ ≤ (S.prefixReceipt n).totalPayoff + ε := hn
        _ = (source.stream.prefixReceipt n).totalPayoff + ε := by
          rw [R.prefix_receipt_eq_source n]
    · intro n
      calc
        (source.stream.prefixReceipt n).totalPrice =
            (S.prefixReceipt n).totalPrice := by
          rw [(R.prefix_receipt_eq_source n).symm]
        _ ≤ S.priceLimit := h.prefix_price_le_limit n
        _ = source.stream.priceLimit := R.price_limit_eq_source
  exact lp_beat_backscatter_no_arbitrage_of_limit_certificate
    source.stream hsource

/-- Anti-tautology payload for the PDE theorem.  These are metadata/obligation
bits, not analytic proofs. -/
structure BeatBackscatterAntiTautologyRules where
  lp_decomposition_predeclared : Prop
  ordinary_cross_class_separated : Prop
  beat_class_separated : Prop
  backscatter_class_separated : Prop
  beat_backscatter_class_separated : Prop
  coherence_prices_declared_before_payoff : Prop
  uniform_charge_not_fit_to_surplus : Prop
  pressure_leray_projection_fixed : Prop

/-- The real PDE obligation: construct a fixed LP/Leray stream whose ordinary
cross and beat/backscatter coherence prices are uniform through the countable
LP limit, and show that this no-arbitrage statement implies the Track B
threshold defect. -/
structure UniformLPBeatBackscatterChargeObligation where
  stream_of_block : FullLedgerBlock → LPBeatBackscatterChargeStream
  anti_tautology_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        BeatBackscatterAntiTautologyRules
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        LPBeatBackscatterLimitCertificate (stream_of_block B)
  threshold_defect_of_uniform_lp_charge :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        BeatBackscatterAntiTautologyRules →
        (stream_of_block B).payoffLimit ≤
          (stream_of_block B).priceLimit →
            ThresholdDefectConvexity B

/-- Projection theorem: if the uniform LP beat/backscatter charge theorem is
paid, Track B reduces back to the existing full-ledger no-survivor theorem. -/
theorem no_global_survivor_of_uniform_lp_beat_backscatter_charge
    (obligation : UniformLPBeatBackscatterChargeObligation)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hnoarb :
      (obligation.stream_of_block B).payoffLimit ≤
        (obligation.stream_of_block B).priceLimit :=
    lp_beat_backscatter_no_arbitrage_of_limit_certificate
      (obligation.stream_of_block B)
      (obligation.certificate_of_global B hglobal)
  have hsource : BeatBackscatterAntiTautologyRules :=
    obligation.anti_tautology_of_global B hglobal
  exact hquartic B
    (obligation.threshold_defect_of_uniform_lp_charge
      B hglobal hsource hnoarb)

/-- Projection-typed version of the uniform beat/backscatter charge theorem.

Closure-facing code should use this form so the same predeclared survival
observable is charged by the threshold-defect ledger. -/
theorem no_global_survivor_of_uniform_lp_beat_backscatter_charge_with_projection
    (obligation : UniformLPBeatBackscatterChargeObligation)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hprojection : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  have hnoarb :
      (obligation.stream_of_block B).payoffLimit ≤
        (obligation.stream_of_block B).priceLimit :=
    lp_beat_backscatter_no_arbitrage_of_limit_certificate
      (obligation.stream_of_block B)
      (obligation.certificate_of_global B hglobal)
  have hsource : BeatBackscatterAntiTautologyRules :=
    obligation.anti_tautology_of_global B hglobal
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (obligation.threshold_defect_of_uniform_lp_charge
      B hglobal hsource hnoarb)

end

end ZtareProofs.NS
