import Mathlib.Tactic
import ZtareProofs.ns_trackb_sos_pricing_kernel_receipt

/-!
# Matrix-block SOS boss-fight adapter

Boss Fight 1 asks for a concrete receipt boundary: a matrix block is priced
only when the observable is already in the charged admissible matrix class and
the block supplies an exact threshold-root SOS/PSD receipt.

This file is deliberately an adapter, not a new analytic theorem.  It connects
the existing matrix admissibility gate to the existing SOS pricing receipt and
records the anti-tautology: a block-only SOS identity does not make an
uncharged matrix observable admissible.
-/

namespace ZtareProofs.NS

noncomputable section

/-- A priced matrix-block branch for Boss Fight 1.

The branch carries both sides of the receipt:

* the observable is a predeclared admissible matrix block, hence has the full
  matrix ledger charges;
* the associated full-ledger block has an exact threshold-root SOS receipt for
  the interacting branch.
-/
structure MatrixBlockSOSBranchReceipt where
  block : FullLedgerBlock
  observable : SignedObservable
  global : IsGlobalTrackBBlock block
  matrix_kind : observable.kind = ObservableKind.matrixBlock
  admissible : IsAdmissibleObservable observable
  positive_self_tax : 0 < block.selfTax
  sos_receipt : SOSThresholdReceipt block

/-- The observable side of a matrix-block SOS branch really paid the matrix
ledger charges; the SOS identity alone is not the whole receipt. -/
theorem matrix_block_sos_branch_has_full_charges
    (R : MatrixBlockSOSBranchReceipt) :
    MatrixBlockFullyCharged R.observable :=
  matrix_block_admissible_has_full_charges R.matrix_kind R.admissible

/-- A matrix SOS branch exposes a genuinely usable global signed observable.

This is the positive observable bridge: the matrix-kind admissibility gate
provides the matrix-specific PSD ballast, while the legacy admissibility
receipt provides the non-oracle and predeclaration guards. -/
theorem matrix_block_sos_branch_observable_fully_charged
    (R : MatrixBlockSOSBranchReceipt) :
    GlobalSignedObservableFullyCharged R.observable :=
  fully_charged_observable_of_admissible_matrix
    R.matrix_kind
    R.admissible

/-- The SOS side of a priced matrix branch pays the above-wall root
coercivity obligation. -/
theorem matrix_block_root_coercivity_of_sos_branch
    (R : MatrixBlockSOSBranchReceipt) :
    RootCoercivityAtThreshold R.block :=
  root_coercivity_of_sos_receipt R.block R.sos_receipt

/-- A priced matrix branch supplies threshold-defect convexity for its
full-ledger block. -/
theorem matrix_block_threshold_defect_of_sos_branch
    (R : MatrixBlockSOSBranchReceipt) :
    ThresholdDefectConvexity R.block :=
  threshold_defect_of_root_coercivity R.block
    (matrix_block_root_coercivity_of_sos_branch R)

/-- The existing charged-matrix resolution object can be built from the exact
matrix SOS branch receipt. -/
def charged_matrix_resolution_of_sos_branch
    (R : MatrixBlockSOSBranchReceipt) :
    ChargedMatrixBlockResolution where
  block := R.block
  observable := R.observable
  global := R.global
  matrix_kind := R.matrix_kind
  admissible := R.admissible
  threshold_defect := matrix_block_threshold_defect_of_sos_branch R

/-- Boss Fight 1 positive adapter: once the matrix branch supplies the exact
threshold-root SOS receipt, the existing quartic theorem prices it. -/
theorem charged_matrix_block_no_survivor_of_sos_branch
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (R : MatrixBlockSOSBranchReceipt) :
    FullLedgerNoSurvivor R.block :=
  charged_matrix_block_no_survivor hquartic
    (charged_matrix_resolution_of_sos_branch R)

/-- Projection-typed Boss Fight 1 adapter.

The SOS receipt supplies the threshold-root defect, but the final survivor
exclusion still has to use the same-ledger quartic survival projection. -/
theorem charged_matrix_block_no_survivor_of_sos_branch_with_projection
    (R : MatrixBlockSOSBranchReceipt)
    (hprojection : QuarticSurvivalProjectionReceipt R.block) :
    FullLedgerNoSurvivor R.block :=
  charged_matrix_block_no_survivor_with_projection
    (charged_matrix_resolution_of_sos_branch R)
    hprojection

/-- Specialize a universal SOS pricing receipt to a positive-self-tax matrix
block.  This is the direct bridge from the global receipt interface to the
matrix branch of Boss Fight 1. -/
def matrix_sos_branch_of_universal_sos_receipt
    (R : UniversalStatePricingSOSReceipt)
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hpos : 0 < B.selfTax) :
    MatrixBlockSOSBranchReceipt where
  block := B
  observable := C
  global := hglobal
  matrix_kind := hkind
  admissible := hC
  positive_self_tax := hpos
  sos_receipt := R.interacting_sos_receipt B C hglobal hC hpos

/-- Specialize a universal SOS pricing receipt to an above-wall matrix block.

The positive self-tax hypothesis is derived from the null/interacting split:
if a global block above `sharpTarget` had zero self-tax, `null_route_cap`
would force it back below the wall. -/
def matrix_sos_branch_of_universal_sos_receipt_above_wall
    (R : UniversalStatePricingSOSReceipt)
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (habove : sharpTarget < B.gamma) :
    MatrixBlockSOSBranchReceipt :=
  matrix_sos_branch_of_universal_sos_receipt
    R B C hglobal hC hkind
    (positive_self_tax_of_universal_sos_receipt_above_wall
      R B C hglobal hC habove)

/-- Build the matrix SOS branch receipt once the fixed block has paid a
nonnegative threshold-root gap.  This is the exact finite-audit handoff: the
matrix observable still must be admissible and charged before the scalar gap
can be used. -/
def matrix_sos_branch_of_nonnegative_threshold_gap
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hpos : 0 < B.selfTax)
    (hgap : 0 ≤ thresholdDefectGapAtRoot B) :
    MatrixBlockSOSBranchReceipt where
  block := B
  observable := C
  global := hglobal
  matrix_kind := hkind
  admissible := hC
  positive_self_tax := hpos
  sos_receipt := sos_receipt_of_nonnegative_threshold_gap B hgap

/-- Finite Euclidean pairing used by the operator/PSD audit adapter. -/
def finiteRealDot {n : ℕ} (x y : Fin n → ℝ) : ℝ :=
  ∑ i, x i * y i

/-- A finite self-adjoint operator candidate on audit coordinates.

This is intentionally an operator-facing object rather than a ledger restatement:
future SDP/SOS output must identify the coordinates, the operator action, and
the symmetry/linearity checks before claiming a PSD receipt. -/
structure FiniteSelfAdjointOperator (n : ℕ) where
  op : (Fin n → ℝ) → (Fin n → ℝ)
  op_add :
    ∀ x y i, op (fun j => x j + y j) i = op x i + op y i
  op_smul :
    ∀ a x i, op (fun j => a * x j) i = a * op x i
  symmetric :
    ∀ x y, finiteRealDot x (op y) = finiteRealDot (op x) y

/-- Quadratic form of a finite operator candidate. -/
def finiteOperatorQuadratic {n : ℕ}
    (A : FiniteSelfAdjointOperator n) (x : Fin n → ℝ) : ℝ :=
  finiteRealDot x (A.op x)

/-- A finite self-adjoint operator whose quadratic form has actually passed the
PSD reality check. -/
structure FinitePSDOperator (n : ℕ) where
  carrier : FiniteSelfAdjointOperator n
  quadratic_nonnegative :
    ∀ x : Fin n → ℝ, 0 ≤ finiteOperatorQuadratic carrier x

/-- Diagonal finite self-adjoint operator.  This is the Lean-side target for
finite PSD/SOS exports whose slack matrix has already been diagonalized or
rationalized into a diagonal certificate. -/
def finiteDiagonalSelfAdjointOperator {n : ℕ}
    (d : Fin n → ℝ) :
    FiniteSelfAdjointOperator n where
  op := fun x i => d i * x i
  op_add := by
    intro x y i
    ring
  op_smul := by
    intro a x i
    ring
  symmetric := by
    intro x y
    unfold finiteRealDot
    apply Finset.sum_congr rfl
    intro i _hi
    ring

/-- A diagonal finite operator with nonnegative diagonal is PSD. -/
def finiteDiagonalPSDOperator {n : ℕ}
    (d : Fin n → ℝ)
    (hd : ∀ i : Fin n, 0 ≤ d i) :
    FinitePSDOperator n where
  carrier := finiteDiagonalSelfAdjointOperator d
  quadratic_nonnegative := by
    intro x
    unfold finiteOperatorQuadratic finiteRealDot finiteDiagonalSelfAdjointOperator
    change 0 ≤ ∑ i, x i * (d i * x i)
    refine Finset.sum_nonneg ?_
    intro i _hi
    have hsq : 0 ≤ x i * x i := mul_self_nonneg (x i)
    have hdiag : 0 ≤ d i := hd i
    have hrewrite : x i * (d i * x i) = d i * (x i * x i) := by
      ring
    rw [hrewrite]
    exact mul_nonneg hdiag hsq

/-- Operator/PSD receipt for a matrix-block threshold gap.

The exact identity says the Track B threshold-root gap is the audited operator
quadratic form at the declared coordinates, plus ordinary residual SOS terms.
This is the finite-dimensional handoff expected from an external PSD/SOS
search. -/
structure MatrixBlockOperatorPSDReceipt (B : FullLedgerBlock) where
  n : ℕ
  operator : FinitePSDOperator n
  coordinates : Fin n → ℝ
  residual_terms : List ℝ
  exact_threshold_identity :
    thresholdDefectGapAtRoot B =
      finiteOperatorQuadratic operator.carrier coordinates +
        pricingSumSquares residual_terms

/-- Convert a finite operator/PSD audit receipt into the scalar SOS receipt
understood by the existing Track B pricing kernel. -/
def sos_receipt_of_matrix_operator_psd_receipt
    (B : FullLedgerBlock)
    (R : MatrixBlockOperatorPSDReceipt B) :
    SOSThresholdReceipt B where
  slack := finiteOperatorQuadratic R.operator.carrier R.coordinates
  terms := R.residual_terms
  slack_nonnegative := R.operator.quadratic_nonnegative R.coordinates
  exact_identity := R.exact_threshold_identity

/-- A uniform operator/PSD receipt family instantiates the universal SOS
pricing interface.

This is the source-facing handoff from SDP/operator search into the Track B
state-pricing split.  The constructor does not prove PSD or null-route pricing:
those remain explicit inputs.  It only converts each operator identity into the
`SOSThresholdReceipt` shape consumed by `UniversalStatePricingSOSReceipt`. -/
def universal_sos_receipt_of_operator_psd_receipts
    (state_space_fixed_before_payoff : Prop)
    (observable_class_fixed_before_payoff : Prop)
    (price_terms_fixed_before_payoff : Prop)
    (self_tax_nonnegative :
      ∀ (B : FullLedgerBlock) (C : SignedObservable),
        IsGlobalTrackBBlock B →
          IsAdmissibleObservable C →
            0 ≤ B.selfTax)
    (null_route_cap :
      ∀ (B : FullLedgerBlock) (C : SignedObservable),
        IsGlobalTrackBBlock B →
          IsAdmissibleObservable C →
            B.selfTax = 0 →
              B.gamma ≤ sharpTarget)
    (operator_psd_receipt :
      ∀ (B : FullLedgerBlock) (C : SignedObservable),
        IsGlobalTrackBBlock B →
          IsAdmissibleObservable C →
            0 < B.selfTax →
              MatrixBlockOperatorPSDReceipt B) :
    UniversalStatePricingSOSReceipt where
  state_space_fixed_before_payoff := state_space_fixed_before_payoff
  observable_class_fixed_before_payoff := observable_class_fixed_before_payoff
  price_terms_fixed_before_payoff := price_terms_fixed_before_payoff
  self_tax_nonnegative := self_tax_nonnegative
  null_route_cap := null_route_cap
  interacting_sos_receipt := by
    intro B C hglobal hC hpos
    exact
      sos_receipt_of_matrix_operator_psd_receipt B
        (operator_psd_receipt B C hglobal hC hpos)

/-- The operator/PSD receipt is enough to make the threshold-root gap
nonnegative, without assuming the ledger conclusion directly. -/
theorem threshold_gap_nonnegative_of_matrix_operator_psd_receipt
    {B : FullLedgerBlock}
    (R : MatrixBlockOperatorPSDReceipt B) :
    0 ≤ thresholdDefectGapAtRoot B :=
  threshold_gap_nonnegative_of_sos_receipt
    (sos_receipt_of_matrix_operator_psd_receipt B R)

/-- Build the Boss Fight 1 matrix branch from an operator-level PSD receipt.
This is the preferred positive handoff: admissibility and ledger charges remain
separate from the finite PSD/SOS certificate. -/
def matrix_sos_branch_of_operator_psd_receipt
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hpos : 0 < B.selfTax)
    (R : MatrixBlockOperatorPSDReceipt B) :
    MatrixBlockSOSBranchReceipt where
  block := B
  observable := C
  global := hglobal
  matrix_kind := hkind
  admissible := hC
  positive_self_tax := hpos
  sos_receipt := sos_receipt_of_matrix_operator_psd_receipt B R

/-- Operator/PSD receipts expose a fully charged observable once they are
paired with the predeclared admissible matrix observable.

The PSD receipt alone has no observable field; this theorem records the exact
noncircular handoff through `matrix_sos_branch_of_operator_psd_receipt`. -/
theorem matrix_operator_psd_receipt_observable_fully_charged
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hpos : 0 < B.selfTax)
    (R : MatrixBlockOperatorPSDReceipt B) :
    GlobalSignedObservableFullyCharged C :=
  matrix_block_sos_branch_observable_fully_charged
    (matrix_sos_branch_of_operator_psd_receipt
      B C hglobal hC hkind hpos R)

/-- Once a charged matrix branch supplies an operator/PSD receipt, the existing
quartic no-survivor theorem prices it. -/
theorem charged_matrix_block_no_survivor_of_operator_psd_receipt
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hpos : 0 < B.selfTax)
    (R : MatrixBlockOperatorPSDReceipt B) :
    FullLedgerNoSurvivor B :=
  charged_matrix_block_no_survivor_of_sos_branch hquartic
    (matrix_sos_branch_of_operator_psd_receipt
      B C hglobal hC hkind hpos R)

/-- Projection-typed operator/PSD handoff for a charged matrix branch. -/
theorem charged_matrix_block_no_survivor_of_operator_psd_receipt_with_projection
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hpos : 0 < B.selfTax)
    (R : MatrixBlockOperatorPSDReceipt B) :
    FullLedgerNoSurvivor B :=
  charged_matrix_block_no_survivor_of_sos_branch_with_projection
    (matrix_sos_branch_of_operator_psd_receipt
      B C hglobal hC hkind hpos R)
    hprojection

/-- Operator-level falsifier: a single negative quadratic witness blocks any
PSD upgrade of the same finite self-adjoint operator. -/
theorem finite_operator_psd_upgrade_falsified_by_negative_quadratic
    {n : ℕ}
    (A : FiniteSelfAdjointOperator n)
    (x : Fin n → ℝ)
    (hneg : finiteOperatorQuadratic A x < 0) :
    ¬ ∃ P : FinitePSDOperator n, P.carrier = A := by
  intro h
  rcases h with ⟨P, hPA⟩
  have hnonneg : 0 ≤ finiteOperatorQuadratic P.carrier x :=
    P.quadratic_nonnegative x
  rw [hPA] at hnonneg
  linarith

/-- Negative threshold-root gap is a hard falsifier for the matrix SOS branch,
even if the matrix observable is otherwise admissible. -/
theorem no_matrix_sos_branch_of_negative_threshold_gap
    (B : FullLedgerBlock)
    (hgap : thresholdDefectGapAtRoot B < 0) :
    ¬ ∃ R : MatrixBlockSOSBranchReceipt, R.block = B := by
  intro h
  rcases h with ⟨R, hRB⟩
  exact no_sos_receipt_of_negative_threshold_gap B hgap
    (hRB ▸ R.sos_receipt)

/-- Universal exact SOS pricing receipts price every admissible positive-tax
matrix block. -/
theorem no_matrix_survivor_of_universal_sos_receipt
    (R : UniversalStatePricingSOSReceipt)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hpos : 0 < B.selfTax) :
    FullLedgerNoSurvivor B :=
  charged_matrix_block_no_survivor_of_sos_branch hquartic
    (matrix_sos_branch_of_universal_sos_receipt
      R B C hglobal hC hkind hpos)

/-- Projection-typed universal SOS pricing receipt for admissible
positive-tax matrix blocks. -/
theorem no_matrix_survivor_of_universal_sos_receipt_with_projection
    (R : UniversalStatePricingSOSReceipt)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hpos : 0 < B.selfTax) :
    FullLedgerNoSurvivor B :=
  charged_matrix_block_no_survivor_of_sos_branch_with_projection
    (matrix_sos_branch_of_universal_sos_receipt
      R B C hglobal hC hkind hpos)
    hprojection

/-- Universal exact SOS pricing receipts price every admissible above-wall
matrix block, with positive self-tax derived from the null-route cap. -/
theorem no_matrix_survivor_of_universal_sos_receipt_above_wall
    (R : UniversalStatePricingSOSReceipt)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (habove : sharpTarget < B.gamma) :
    FullLedgerNoSurvivor B :=
  charged_matrix_block_no_survivor_of_sos_branch hquartic
    (matrix_sos_branch_of_universal_sos_receipt_above_wall
      R B C hglobal hC hkind habove)

/-- Projection-typed universal SOS pricing receipt for above-wall matrix
blocks, with positivity derived instead of assumed. -/
theorem no_matrix_survivor_of_universal_sos_receipt_above_wall_with_projection
    (R : UniversalStatePricingSOSReceipt)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (habove : sharpTarget < B.gamma) :
    FullLedgerNoSurvivor B :=
  charged_matrix_block_no_survivor_of_sos_branch_with_projection
    (matrix_sos_branch_of_universal_sos_receipt_above_wall
      R B C hglobal hC hkind habove)
    hprojection

/-- A fake matrix receipt: it supplies an exact block-level SOS identity, but
the matrix observable is missing at least one required ledger charge. -/
structure BlockOnlyMatrixSOSReceipt where
  block : FullLedgerBlock
  observable : SignedObservable
  matrix_kind : observable.kind = ObservableKind.matrixBlock
  missing_full_charges : ¬ MatrixBlockFullyCharged observable
  sos_receipt : SOSThresholdReceipt block

/-- Anti-tautology theorem: an exact block-level SOS identity does not admit an
uncharged matrix observable.  The receipt must include the matrix ledger gate,
not just the scalar threshold-root identity. -/
theorem block_only_matrix_sos_receipt_not_admissible
    (F : BlockOnlyMatrixSOSReceipt) :
    ¬ IsAdmissibleObservable F.observable :=
  matrix_block_not_admissible_without_full_charges
    F.matrix_kind F.missing_full_charges

/-- Consequently, a block-only fake receipt cannot be upgraded to the positive
Boss Fight 1 matrix-branch receipt for the same observable. -/
theorem no_matrix_sos_branch_from_block_only_fake
    (F : BlockOnlyMatrixSOSReceipt) :
    ¬ ∃ R : MatrixBlockSOSBranchReceipt,
      R.block = F.block ∧ R.observable = F.observable := by
  intro h
  rcases h with ⟨R, _hblock, hobs⟩
  exact block_only_matrix_sos_receipt_not_admissible F
    (hobs ▸ R.admissible)

end

end ZtareProofs.NS
