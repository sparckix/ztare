import Mathlib.Tactic
import ZtareProofs.ns_littlewood_paley_profile_bridge

/-!
# Littlewood-Paley paraproduct bridge for Track B

This file refines the shell bridge by naming the Bony/Littlewood-Paley
interaction classes that an actual PDE proof must charge:

* low-high catalyst terms;
* high-low transport terms;
* high-high cascade terms;
* same-shell/remainder terms.

The theorem is still abstract and does **not** prove Navier-Stokes regularity.
It says that if a fixed paraproduct decomposition prices every declared
interaction term and charges residual payoff, then no above-wall Track B trade
can appear in the finite-prefix or countable-limit passage.
-/

namespace ZtareProofs.NS

/-- Paraproduct class of a shell interaction. -/
inductive LPParaproductClass where
  | lowHigh
  | highLow
  | highHigh
  | sameShell
  | remainder
deriving DecidableEq, Repr

/-- A single priced paraproduct interaction. -/
structure LPInteractionLedger where
  interactionClass : LPParaproductClass
  price : Real
  payoff : Real

/-- One interaction is priced when payoff does not exceed its declared price. -/
def InteractionNoArbitrage (T : LPInteractionLedger) : Prop :=
  T.payoff ≤ T.price

/-- A finite family of paraproduct interactions plus residual terms. -/
structure LPInteractionFamily where
  terms : List LPInteractionLedger
  residualPrice : Real
  residualPayoff : Real

def interactionFamilyPrice (F : LPInteractionFamily) : Real :=
  (F.terms.map (fun T => T.price)).sum + F.residualPrice

def interactionFamilyPayoff (F : LPInteractionFamily) : Real :=
  (F.terms.map (fun T => T.payoff)).sum + F.residualPayoff

lemma sum_interaction_payoff_le_sum_price
    {ts : List LPInteractionLedger}
    (h : ∀ T ∈ ts, InteractionNoArbitrage T) :
    (ts.map (fun T => T.payoff)).sum ≤
      (ts.map (fun T => T.price)).sum := by
  induction ts with
  | nil =>
      simp
  | cons T ts ih =>
      have hT : T.payoff ≤ T.price := h T (by simp)
      have hts : ∀ U ∈ ts, InteractionNoArbitrage U := by
        intro U hU
        exact h U (by simp [hU])
      simp [hT, ih hts, add_le_add]

/-- Finite paraproduct-family certificate. -/
structure LPInteractionFamilyCertificate (F : LPInteractionFamily) where
  residual_price_nonnegative : 0 ≤ F.residualPrice
  residual_payoff_charged : F.residualPayoff ≤ F.residualPrice
  interaction_no_arbitrage : ∀ T ∈ F.terms, InteractionNoArbitrage T

/-- A fixed finite paraproduct decomposition is no-arbitrage once every term and
the residual are charged. -/
theorem interaction_family_no_arbitrage_of_certificate
    (F : LPInteractionFamily)
    (h : LPInteractionFamilyCertificate F) :
    interactionFamilyPayoff F ≤ interactionFamilyPrice F := by
  unfold interactionFamilyPayoff interactionFamilyPrice
  exact add_le_add
    (sum_interaction_payoff_le_sum_price h.interaction_no_arbitrage)
    h.residual_payoff_charged

/-- Countable paraproduct-prefix stream.  The actual PDE proof must define
`prefixFamily n` from a fixed LP/Bony decomposition, not from the observed
profitable route. -/
structure LPParaproductPricingStream where
  prefixFamily : ℕ → LPInteractionFamily
  priceLimit : Real
  payoffLimit : Real

/-- Limit certificate for the paraproduct stream. -/
structure LPParaproductLimitCertificate (S : LPParaproductPricingStream) where
  prefix_certificate : ∀ n, LPInteractionFamilyCertificate (S.prefixFamily n)
  payoff_approximated_by_prefix :
    ∀ ε : Real, 0 < ε →
      ∃ n, S.payoffLimit ≤ interactionFamilyPayoff (S.prefixFamily n) + ε
  prefix_price_le_limit :
    ∀ n, interactionFamilyPrice (S.prefixFamily n) ≤ S.priceLimit

/-- Paraproduct limit passage: charged finite paraproduct prefixes cannot
generate a new no-arbitrage failure only at the infinite-shell limit. -/
theorem paraproduct_no_arbitrage_of_limit_certificate
    (S : LPParaproductPricingStream)
    (h : LPParaproductLimitCertificate S) :
    S.payoffLimit ≤ S.priceLimit := by
  refine le_of_forall_pos_le_add ?_
  intro ε hε
  obtain ⟨n, hn⟩ := h.payoff_approximated_by_prefix ε hε
  have hpref :
      interactionFamilyPayoff (S.prefixFamily n) ≤
        interactionFamilyPrice (S.prefixFamily n) :=
    interaction_family_no_arbitrage_of_certificate
      (S.prefixFamily n)
      (h.prefix_certificate n)
  have hprice :
      interactionFamilyPrice (S.prefixFamily n) ≤ S.priceLimit :=
    h.prefix_price_le_limit n
  calc
    S.payoffLimit ≤ interactionFamilyPayoff (S.prefixFamily n) + ε := hn
    _ ≤ interactionFamilyPrice (S.prefixFamily n) + ε := by linarith
    _ ≤ S.priceLimit + ε := by linarith

/-- Prefix payoff escape for a fixed LP/Bony paraproduct stream. -/
def LPParaproductPrefixPayoffUnbounded
    (S : LPParaproductPricingStream) : Prop :=
  ∀ B : Real, ∃ n : ℕ, B < interactionFamilyPayoff (S.prefixFamily n)

/-- A valid LP/Bony paraproduct limit certificate rules out a smooth-prefix
escape with unbounded payoff in the same fixed decomposition. -/
theorem no_unbounded_paraproduct_prefix_payoff_under_limit_certificate
    (S : LPParaproductPricingStream)
    (h : LPParaproductLimitCertificate S) :
    ¬ LPParaproductPrefixPayoffUnbounded S := by
  intro hunbounded
  obtain ⟨n, hn⟩ := hunbounded S.priceLimit
  have hpref :
      interactionFamilyPayoff (S.prefixFamily n) ≤
        interactionFamilyPrice (S.prefixFamily n) :=
    interaction_family_no_arbitrage_of_certificate
      (S.prefixFamily n)
      (h.prefix_certificate n)
  have hprice :
      interactionFamilyPrice (S.prefixFamily n) ≤ S.priceLimit :=
    h.prefix_price_le_limit n
  exact not_lt_of_ge (hpref.trans hprice) hn

/-- Track B bridge specialized to the LP paraproduct decomposition. -/
structure LPParaproductPricingBridge where
  stream_of_block : FullLedgerBlock → LPParaproductPricingStream
  certificate_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        LPParaproductLimitCertificate (stream_of_block B)
  threshold_defect_of_paraproduct_no_arbitrage :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        (stream_of_block B).payoffLimit ≤ (stream_of_block B).priceLimit →
          ThresholdDefectConvexity B

/-- If the PDE supplies a fixed charged LP paraproduct certificate, then Track B
has no global full-ledger survivor. -/
theorem no_global_survivor_of_lp_paraproduct_bridge
    (bridge : LPParaproductPricingBridge)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hnoarb :
      (bridge.stream_of_block B).payoffLimit ≤
        (bridge.stream_of_block B).priceLimit :=
    paraproduct_no_arbitrage_of_limit_certificate
      (bridge.stream_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact hquartic B
    (bridge.threshold_defect_of_paraproduct_no_arbitrage B hglobal hnoarb)

/-- Projection-typed variant of the LP/Bony paraproduct bridge for one promoted
block.  This is the non-vacuous closure-facing form: the survival projection is
required only for the same block whose paraproduct stream is being priced. -/
theorem no_global_survivor_of_lp_paraproduct_bridge_with_projection_at_block
    (bridge : LPParaproductPricingBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hprojection : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  have hnoarb :
      (bridge.stream_of_block B).payoffLimit ≤
        (bridge.stream_of_block B).priceLimit :=
    paraproduct_no_arbitrage_of_limit_certificate
      (bridge.stream_of_block B)
      (bridge.certificate_of_global B hglobal)
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (bridge.threshold_defect_of_paraproduct_no_arbitrage B hglobal hnoarb)

/-- Legacy family adapter for older callers.  New closure code should use
`no_global_survivor_of_lp_paraproduct_bridge_with_projection_at_block`. -/
theorem no_global_survivor_of_lp_paraproduct_bridge_with_projection
    (bridge : LPParaproductPricingBridge)
    (hprojection :
      ∀ B : FullLedgerBlock, QuarticSurvivalProjectionReceipt B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B :=
  no_global_survivor_of_lp_paraproduct_bridge_with_projection_at_block
    bridge B hglobal (hprojection B)

/-- Anti-tautology payload for the paraproduct theorem. -/
structure LPParaproductAntiTautologyRules where
  paraproduct_partition_predeclared : Prop
  interaction_classes_exhaustive : Prop
  low_high_catalyst_charged : Prop
  high_high_self_tax_charged : Prop
  residual_terms_charged_before_limit : Prop
  no_phase_choice_after_profit_scoring : Prop

end ZtareProofs.NS
