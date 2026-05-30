import Mathlib.Tactic
import ZtareProofs.ns_leray_gain_tax_trackb_obligation
import ZtareProofs.ns_translation_covariant_matrix_exclusion

/-!
# Matrix-block ledger charging obligation

Phase 5DX found exact Leray-aware matrix intertwiners, so scalar
pressure-blind leakage arguments cannot be promoted to a full Track B theorem.
Phase 5ET/5EX then charged the cheapest matrix classes locally and found no
same-ledger survivor.

This file records the non-tautological logical split that remains:

* W-independent off-diagonal linear matrix blocks are excluded by translation
  covariance when the Fourier characters differ;
* any matrix block kept in the global observable class must be predeclared and
  charged by PSD ballast, damping, independent normalization, and the cross
  term;
* an uncharged matrix block is not an admissible Track B observable;
* a charged global matrix block still needs the same threshold-defect theorem
  as every other global block.

The file does **not** prove the PDE coercivity theorem.  It prevents the
matrix-intertwiner loophole from being silently dropped or converted into a
finite-audit overclaim.
-/

namespace ZtareProofs.NS

noncomputable section

/-- The concrete charge package required before a matrix observable can be
used in a global Track B statement. -/
def MatrixBlockFullyCharged (C : SignedObservable) : Prop :=
  C.psdBallastCharged ∧ C.dampingCharged ∧
    C.independentNormalized ∧ C.crossTermCharged

/-- Matrix-block admissibility forces every full-ledger charge. -/
theorem matrix_block_admissible_has_full_charges
    {C : SignedObservable}
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hC : IsAdmissibleObservable C) :
    MatrixBlockFullyCharged C := by
  exact hC.2.2 hkind

/-- If any full-ledger charge is missing, a matrix block is not an admissible
Track B observable. -/
theorem matrix_block_not_admissible_without_full_charges
    {C : SignedObservable}
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hmissing : ¬ MatrixBlockFullyCharged C) :
    ¬ IsAdmissibleObservable C := by
  intro hC
  exact hmissing (matrix_block_admissible_has_full_charges hkind hC)

/-- Restatement of the W-independent off-diagonal exclusion in matrix-block
language: translation covariance and character separation force the block to
be zero.  Background-covariant W-coupled blocks are deliberately not covered by
this lemma. -/
theorem w_independent_offdiagonal_matrix_block_zero
    {F : Type*} [Field F] {χk χl C : F}
    (hcov : χk * C = C * χl) (hsep : χk ≠ χl) : C = 0 :=
  translationCovariantBlock_zero_of_character_separation hcov hsep

/-- Positive matrix-branch resolution: the block is global, the observable is a
charged predeclared matrix block, and the exact threshold-defect theorem has
been paid. -/
structure ChargedMatrixBlockResolution where
  block : FullLedgerBlock
  observable : SignedObservable
  global : IsGlobalTrackBBlock block
  matrix_kind : observable.kind = ObservableKind.matrixBlock
  admissible : IsAdmissibleObservable observable
  threshold_defect : ThresholdDefectConvexity block

/-- Charged matrix blocks are priced by the same quartic no-survivor theorem as
the rest of Track B. -/
theorem charged_matrix_block_no_survivor
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (R : ChargedMatrixBlockResolution) :
    FullLedgerNoSurvivor R.block :=
  hquartic R.block R.threshold_defect

/-- Projection-typed matrix branch pricing.

Closure-facing matrix/SOS routes should use this form so the matrix branch
cannot be closed by a detached threshold-defect kernel. -/
theorem charged_matrix_block_no_survivor_with_projection
    (R : ChargedMatrixBlockResolution)
    (hprojection : QuarticSurvivalProjectionReceipt R.block) :
    FullLedgerNoSurvivor R.block :=
  full_ledger_no_survivor_of_quartic_survival_projection
    R.block
    hprojection
    R.threshold_defect

/-- The matrix branch cannot be settled by finite evidence alone.  It is closed
only by an admissibility split plus a global threshold-defect theorem for the
charged matrix class. -/
structure MatrixBlockLedgerChargingObligation where
  offdiagonal_translation_exclusion :
    ∀ {F : Type*} [Field F] {χk χl C : F},
      χk * C = C * χl → χk ≠ χl → C = 0
  charged_matrix_threshold_defect :
    ∀ (B : FullLedgerBlock) (C : SignedObservable),
      IsGlobalTrackBBlock B →
        IsAdmissibleObservable C →
          C.kind = ObservableKind.matrixBlock →
            ThresholdDefectConvexity B
  null_matrix_cap :
    ∀ (B : FullLedgerBlock) (C : SignedObservable),
      IsGlobalTrackBBlock B →
        IsAdmissibleObservable C →
          C.kind = ObservableKind.matrixBlock →
            B.selfTax = 0 →
              B.gamma ≤ sharpTarget

/-- A supplied matrix-block charging obligation feeds the existing
no-survivor theorem for every admissible global matrix block. -/
theorem no_matrix_block_survivor_of_charging_obligation
    (O : MatrixBlockLedgerChargingObligation)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock) :
    FullLedgerNoSurvivor B := by
  exact hquartic B (O.charged_matrix_threshold_defect B C hglobal hC hkind)

/-- Projection-typed variant of the matrix-block charging obligation.

This is the preferred adapter for global closures: matrix admissibility and
threshold-defect charging are still supplied by `O`, while survival-profit
exclusion must pass through the same-ledger quartic projection receipt. -/
theorem no_matrix_block_survivor_of_charging_obligation_with_projection
    (O : MatrixBlockLedgerChargingObligation)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock) :
    FullLedgerNoSurvivor B := by
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (O.charged_matrix_threshold_defect B C hglobal hC hkind)

/-- Null/self-tax-free matrix rows are not a separate escape once the matrix
null cap is paid; they enter the left side of threshold-defect convexity. -/
theorem threshold_defect_of_matrix_null_cap
    (O : MatrixBlockLedgerChargingObligation)
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock)
    (hself : B.selfTax = 0) :
    ThresholdDefectConvexity B := by
  exact Or.inl (O.null_matrix_cap B C hglobal hC hkind hself)

/-- Canonical proof packet: the W-independent translation exclusion is already
available, while the charged W-coupled/global branch is the remaining analytic
obligation. -/
structure MatrixBlockClosureFrontier where
  local_finite_audits_no_survivor : Prop
  translation_exclusion_available :
    ∀ {F : Type*} [Field F] {χk χl C : F},
      χk * C = C * χl → χk ≠ χl → C = 0
  global_charged_matrix_branch_open : Prop
  null_matrix_cap_open : Prop
  not_a_clay_proof_without_global_charging : Prop

def matrix_block_frontier_packet :
    MatrixBlockClosureFrontier := by
  refine ⟨True, ?_, True, True, True⟩
  intro F _ χk χl C hcov hsep
  exact w_independent_offdiagonal_matrix_block_zero hcov hsep

end

end ZtareProofs.NS
