import Mathlib.Tactic
import ZtareProofs.ns_matrix_block_ledger_charging_obligation

/-!
# Universal state-pricing split

This file records the current Track B proof target in the operator's
state-pricing language without turning the analogy into a tautology.

The finite audits suggest a no-arbitrage split:

* cheap/null/self-tax-free routes are capped at the sharp `2/3` wall;
* genuinely interacting routes must pay the exact quartic defect at the
  threshold root;
* matrix-block observables enter only after the admissibility gate in
  `ns_matrix_block_ledger_charging_obligation.lean`.

The hard PDE theorem is the construction of a global certificate satisfying
this split for actual Leray/Sobolev states.  The Lean results below are only
the algebraic routing: if such a certificate exists, it implies the existing
Track B no-survivor statement.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Exact root coercivity: once the mixed gain is above the sharp wall, the
declared same-ledger defect at the threshold root is already at least one. -/
def RootCoercivityAtThreshold (B : FullLedgerBlock) : Prop :=
  sharpTarget < B.gamma →
    1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma))

/-- Root coercivity is exactly the right branch of threshold-defect convexity,
with the below-wall branch handled separately. -/
theorem threshold_defect_of_root_coercivity
    (B : FullLedgerBlock)
    (hroot : RootCoercivityAtThreshold B) :
    ThresholdDefectConvexity B := by
  by_cases hle : B.gamma ≤ sharpTarget
  · exact Or.inl hle
  · have hgt : sharpTarget < B.gamma := lt_of_not_ge hle
    exact Or.inr ⟨hgt, hroot hgt⟩

/-- The non-tautological state-pricing split.

All maps/classes must be fixed before payoff is scored.  `self_tax_nonnegative`
is part of the ledger semantics; `null_route_cap` is the cheap-route theorem;
`interacting_root_charge` is the true quartic/PSD/coercivity theorem.
-/
structure StatePricingSplitCertificate where
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
  interacting_root_charge :
    ∀ (B : FullLedgerBlock) (C : SignedObservable),
      IsGlobalTrackBBlock B →
        IsAdmissibleObservable C →
          0 < B.selfTax →
            RootCoercivityAtThreshold B

/-- The state-pricing split implies Track B threshold-defect convexity. -/
theorem threshold_defect_of_state_pricing_split
    (K : StatePricingSplitCertificate)
    (B : FullLedgerBlock)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C) :
    ThresholdDefectConvexity B := by
  have hnonneg : 0 ≤ B.selfTax :=
    K.self_tax_nonnegative B C hglobal hC
  rcases lt_or_eq_of_le hnonneg with hpos | hzero
  · exact threshold_defect_of_root_coercivity B
      (K.interacting_root_charge B C hglobal hC hpos)
  · exact Or.inl (K.null_route_cap B C hglobal hC hzero.symm)

/-- Once the state-pricing split is paid, the existing quartic no-survivor
projection theorem gives the Track B no-survivor result. -/
theorem no_global_survivor_of_state_pricing_split
    (K : StatePricingSplitCertificate)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C) :
    FullLedgerNoSurvivor B := by
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (threshold_defect_of_state_pricing_split K B C hglobal hC)

/-- Strong-observable version of the state-pricing projection.

This is the receipt future Track B closures should prefer: the signed
observable is fully charged before it enters the legacy admissibility interface.
It prevents a scalar or diagonal observable from bypassing normalization,
damping, or cross-term charges just because it is not a matrix block. -/
theorem no_global_survivor_of_state_pricing_split_fully_charged
    (K : StatePricingSplitCertificate)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : GlobalSignedObservableFullyCharged C) :
    FullLedgerNoSurvivor B :=
  no_global_survivor_of_state_pricing_split
    K B hprojection C hglobal
    (admissible_observable_of_fully_charged hC)

/-- The full universal pricing kernel obligation: state-pricing split plus the
matrix-block admissibility gate.  This is the current honest closure target,
not a theorem already proved for Navier-Stokes. -/
structure UniversalStatePricingKernelObligation where
  split : StatePricingSplitCertificate
  matrix_gate_charges_admissible_observables :
    ∀ C : SignedObservable,
      IsAdmissibleObservable C →
        C.kind = ObservableKind.matrixBlock →
          MatrixBlockFullyCharged C

/-- Global no-survivor conclusion from the universal kernel obligation. -/
theorem no_global_survivor_of_universal_state_pricing_kernel
    (O : UniversalStatePricingKernelObligation)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (threshold_defect_of_state_pricing_split O.split B C hglobal hC)

/-- Global no-survivor conclusion from the universal kernel using the stronger
fully charged observable receipt. -/
theorem no_global_survivor_of_universal_state_pricing_kernel_fully_charged
    (O : UniversalStatePricingKernelObligation)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : GlobalSignedObservableFullyCharged C) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (threshold_defect_of_state_pricing_split O.split B C hglobal
      (admissible_observable_of_fully_charged hC))

/-- Matrix-block specialization: a charged admissible matrix block is not a
separate route around the universal kernel; it is priced by the same split. -/
theorem no_matrix_survivor_of_universal_state_pricing_kernel
    (O : UniversalStatePricingKernelObligation)
    (B : FullLedgerBlock)
    (hprojection : QuarticSurvivalProjectionReceipt B)
    (C : SignedObservable)
    (hglobal : IsGlobalTrackBBlock B)
    (hC : IsAdmissibleObservable C)
    (hkind : C.kind = ObservableKind.matrixBlock) :
    FullLedgerNoSurvivor B := by
  have _hcharges : MatrixBlockFullyCharged C :=
    O.matrix_gate_charges_admissible_observables C hC hkind
  exact no_global_survivor_of_universal_state_pricing_kernel
    O B hprojection C hglobal hC

/-- Open-frontier packet for the research director: the split is the exact next
theorem target.  A candidate that only restates these fields has not proved the
kernel. -/
structure UniversalStatePricingOpenFrontier where
  null_route_cap_open : Prop
  interacting_root_charge_open : Prop
  matrix_gate_formalized : Prop
  profile_limit_passage_open : Prop
  low_frequency_lipschitz_reserve_open : Prop
  not_proved_by_finite_certificates_alone : Prop

def universal_state_pricing_open_frontier :
    UniversalStatePricingOpenFrontier :=
  ⟨True, True, True, True, True, True⟩

end

end ZtareProofs.NS
