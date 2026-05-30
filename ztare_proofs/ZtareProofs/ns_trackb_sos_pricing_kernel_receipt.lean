import Mathlib.Tactic
import ZtareProofs.ns_universal_state_pricing_split

/-!
# Track B SOS pricing-kernel receipt

The universal state-pricing split is still an analytic/PDE obligation.  This
file adds the verifier interface for a future PSD/SOS certificate: Lean does
not search for the certificate, but if an exact receipt writes the threshold
defect gap as nonnegative slack plus squares, Lean routes it into the Track B
state-pricing split.

This prevents a common failure mode: an LLM saying "there is a PSD kernel"
without providing an exact object that prices the quartic root ledger.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Square notation for Track B pricing receipts. -/
def pricingCertSq (x : ℝ) : ℝ :=
  x * x

/-- Finite sum-of-squares payload for an exact pricing receipt. -/
def pricingSumSquares : List ℝ → ℝ
  | [] => 0
  | x :: xs => pricingCertSq x + pricingSumSquares xs

lemma pricingCertSq_nonneg (x : ℝ) : 0 ≤ pricingCertSq x := by
  unfold pricingCertSq
  exact mul_self_nonneg x

lemma pricingSumSquares_nonneg : ∀ xs : List ℝ, 0 ≤ pricingSumSquares xs
  | [] => by
      unfold pricingSumSquares
      norm_num
  | x :: xs => by
      unfold pricingSumSquares
      exact add_nonneg (pricingCertSq_nonneg x) (pricingSumSquares_nonneg xs)

/-- Exact gap at the Track B threshold root. -/
def thresholdDefectGapAtRoot (B : FullLedgerBlock) : ℝ :=
  survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) - 1

/-- A lossless PSD/SOS receipt for one above-wall interacting block. -/
structure SOSThresholdReceipt (B : FullLedgerBlock) where
  slack : ℝ
  terms : List ℝ
  slack_nonnegative : 0 ≤ slack
  exact_identity :
    thresholdDefectGapAtRoot B = slack + pricingSumSquares terms

theorem threshold_gap_nonnegative_of_sos_receipt
    {B : FullLedgerBlock}
    (R : SOSThresholdReceipt B) :
    0 ≤ thresholdDefectGapAtRoot B := by
  rw [R.exact_identity]
  exact add_nonneg R.slack_nonnegative (pricingSumSquares_nonneg R.terms)

/-- Trivial exact receipt from a nonnegative threshold-root gap.

This is intentionally exposed because it states the real scalar burden: after
the observable class and block are fixed, a negative threshold gap is the
falsifier; a nonnegative gap can be represented as nonnegative slack.  Structural
SOS/PSD work is needed to prove this nonnegativity uniformly, not to change the
ledger after scoring. -/
def sos_receipt_of_nonnegative_threshold_gap
    (B : FullLedgerBlock)
    (hgap : 0 ≤ thresholdDefectGapAtRoot B) :
    SOSThresholdReceipt B where
  slack := thresholdDefectGapAtRoot B
  terms := []
  slack_nonnegative := hgap
  exact_identity := by
    simp [pricingSumSquares]

/-- A negative threshold-root gap is an exact obstruction to any SOS receipt in
this verifier interface. -/
theorem no_sos_receipt_of_negative_threshold_gap
    (B : FullLedgerBlock)
    (hgap : thresholdDefectGapAtRoot B < 0) :
    SOSThresholdReceipt B → False := by
  intro R
  have hnonneg : 0 ≤ thresholdDefectGapAtRoot B :=
    threshold_gap_nonnegative_of_sos_receipt R
  linarith

/-- A threshold-root SOS receipt is enough to pay the interacting branch of the
universal state-pricing split. -/
theorem root_coercivity_of_sos_receipt
    (B : FullLedgerBlock)
    (R : SOSThresholdReceipt B) :
    RootCoercivityAtThreshold B := by
  intro _hgt
  have hgap : 0 ≤ thresholdDefectGapAtRoot B :=
    threshold_gap_nonnegative_of_sos_receipt R
  unfold thresholdDefectGapAtRoot at hgap
  linarith

/-- Global SOS receipt package: fixed objects plus exact receipts for every
interacting above-wall block.  Null routes still need their cap theorem. -/
structure UniversalStatePricingSOSReceipt where
  state_space_fixed_before_payoff : Prop
  observable_class_fixed_before_payoff : Prop
  price_terms_fixed_before_payoff : Prop
  self_tax_nonnegative :
    ∀ (B : FullLedgerBlock) (C : SignedObservable),
      IsGlobalTrackBBlock B →
        IsAdmissibleObservable C →
          0 ≤ B.selfTax
  null_route_cap :
    ∀ (B : FullLedgerBlock) (C : SignedObservable),
      IsGlobalTrackBBlock B →
        IsAdmissibleObservable C →
          B.selfTax = 0 →
            B.gamma ≤ sharpTarget
  interacting_sos_receipt :
    ∀ (B : FullLedgerBlock) (C : SignedObservable),
      IsGlobalTrackBBlock B →
        IsAdmissibleObservable C →
          0 < B.selfTax →
            SOSThresholdReceipt B

/-- Exact SOS receipts instantiate the universal state-pricing split. -/
def state_pricing_split_of_sos_receipt
    (R : UniversalStatePricingSOSReceipt) :
    StatePricingSplitCertificate where
  state_space_fixed_before_payoff := R.state_space_fixed_before_payoff
  observable_class_fixed_before_payoff := R.observable_class_fixed_before_payoff
  price_terms_fixed_before_payoff := R.price_terms_fixed_before_payoff
  self_tax_nonnegative := R.self_tax_nonnegative
  null_route_cap := R.null_route_cap
  interacting_root_charge := by
    intro B C hglobal hC hpos
    exact root_coercivity_of_sos_receipt B
      (R.interacting_sos_receipt B C hglobal hC hpos)

/-- Above-wall global blocks cannot be null-route blocks in a universal SOS
receipt.  This is the noncircular bridge from the null/interacting split to
the positive self-tax hypothesis required by the interacting SOS payload. -/
theorem positive_self_tax_of_universal_sos_receipt_above_wall
    (R : UniversalStatePricingSOSReceipt)
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (habove : sharpTarget < B.gamma) :
    0 < B.selfTax := by
  by_contra hnot
  have hle : B.selfTax ≤ 0 := le_of_not_gt hnot
  have hnonneg : 0 ≤ B.selfTax := R.self_tax_nonnegative B C hglobal hC
  have hzero : B.selfTax = 0 := le_antisymm hle hnonneg
  have hcap : B.gamma ≤ sharpTarget := R.null_route_cap B C hglobal hC hzero
  linarith

/-- Named handoff from an exact SOS pricing receipt to threshold-defect
convexity.

This is only receipt routing; the SOS/PDE construction is still an assumption
inside `UniversalStatePricingSOSReceipt`. -/
theorem threshold_defect_of_sos_pricing_receipt
    (R : UniversalStatePricingSOSReceipt)
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C) :
    ThresholdDefectConvexity B :=
  threshold_defect_of_state_pricing_split
    (state_pricing_split_of_sos_receipt R) B C hglobal hC

/-- A full universal-kernel obligation can be built from exact SOS receipts
plus the matrix-block admissibility gate.  Survival projection is intentionally
not part of this global object; it must be supplied for the promoted block. -/
def universal_kernel_obligation_of_sos_receipt
    (R : UniversalStatePricingSOSReceipt) :
    UniversalStatePricingKernelObligation where
  split := state_pricing_split_of_sos_receipt R
  matrix_gate_charges_admissible_observables :=
    fun _ hC hkind => matrix_block_admissible_has_full_charges hkind hC

/-- Projection theorem for exact PSD/SOS receipts. -/
theorem no_global_survivor_of_sos_pricing_receipt
    (R : UniversalStatePricingSOSReceipt)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C) :
    FullLedgerNoSurvivor B := by
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (threshold_defect_of_state_pricing_split
      (state_pricing_split_of_sos_receipt R) B C hglobal hC)

end

end ZtareProofs.NS
