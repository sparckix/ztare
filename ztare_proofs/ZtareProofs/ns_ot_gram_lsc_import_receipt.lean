import Mathlib.Tactic
import ZtareProofs.ns_all_output_positive_coherence_lsc

/-!
# OT/Benamou-Brenier import receipt for all-output Gram LSC

Verdict encoded by this file:

* Benamou-Brenier action lower-semicontinuity is not, by itself, the Track B
  all-output Gram/coherence LSC obligation.  It lives on an OT action topology.
* It can instantiate the existing all-output obligation only after a
  predeclared calibration proves that the OT limit action dominates the
  declared Gram target and every OT prefix action is charged by the fixed
  all-output Gram price.
* Those calibration fields are the non-tautological analytic burden.  Without
  them, a tail-recurring Gram price gap is still an exact falsifier, even if the
  OT action itself is lower-semicontinuous.

This is a proof-facing receipt shape, not a Navier-Stokes theorem and not an
OT theorem.  Constants, topology, and atom maps are intentionally fields.
-/

namespace ZtareProofs.NS

noncomputable section

universe u v

/-- Abstract topology/action surface for a Benamou-Brenier style action.

The concrete PDE/OT development must provide the actual state space,
convergence notion, continuity-equation closure, and constants before payoff is
scored. -/
structure OTActionTopology where
  OTState : Type v
  ConvergesTo : (ℕ → OTState) → OTState → Prop
  continuityEquationClosed : Prop
  metricAndConstantsDeclaredBeforePayoff : Prop

/-- Prefix OT action stream attached to one fixed OT topology. -/
structure OTActionStream (ω : OTActionTopology.{v}) where
  prefixState : ℕ → ω.OTState
  limitState : ω.OTState
  prefixAction : ℕ → Real
  limitAction : Real

/-- The OT stream uses one fixed topology and declared action geometry. -/
def OTActionUsesFixedTopology
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω) : Prop :=
  ω.continuityEquationClosed ∧
    ω.metricAndConstantsDeclaredBeforePayoff ∧
      ω.ConvergesTo A.prefixState A.limitState

/-- Lower-semicontinuity direction for the OT action.

This is the Benamou-Brenier inspiration in abstract epsilon/eventual form:
`limitAction <= liminf prefixAction`. -/
def OTActionLowerSemicontinuous
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω) : Prop :=
  OTActionUsesFixedTopology A →
    ∀ ε : Real, 0 < ε → ∃ N : ℕ, ∀ n : ℕ,
      N ≤ n →
        A.limitAction ≤ A.prefixAction n + ε

/-- Non-tautological calibration needed before OT LSC can price the all-output
Gram/coherence obligation.

The two scalar inequalities are the load-bearing bridge:

* `declared_gram_target_le_ot_limit_action`
* `prefix_ot_action_le_all_output_gram_price`

They say the OT action is neither a hidden source-coordinate substitute nor a
post-hoc moving observable.  Proving these from the fixed LP/Bony output atom
system is the real analytic import problem. -/
structure OTGramImportCalibration
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω) where
  fixed_lp_topology : ContinuumLPUsesFixedTopology S
  fixed_atoms : FixedAllOutputLPBonyAtoms S
  fixed_ot_topology : OTActionUsesFixedTopology A
  ot_observable_declared_before_payoff : Prop
  ot_observable_declared_before_payoff_paid :
    ot_observable_declared_before_payoff
  output_atom_to_ot_state_map_declared : Prop
  output_atom_to_ot_state_map_declared_paid :
    output_atom_to_ot_state_map_declared
  gram_kernel_pushes_forward_to_ot_metric : Prop
  gram_kernel_pushes_forward_to_ot_metric_paid :
    gram_kernel_pushes_forward_to_ot_metric
  constants_declared_before_payoff : Prop
  constants_declared_before_payoff_paid :
    constants_declared_before_payoff
  no_hidden_source_l2_or_moving_atoms : Prop
  no_hidden_source_l2_or_moving_atoms_paid :
    no_hidden_source_l2_or_moving_atoms
  prefix_ot_action_le_all_output_gram_price :
    ∀ n : ℕ, A.prefixAction n ≤ continuumLPPrefixPrice S n
  declared_gram_target_le_ot_limit_action :
    continuumGlobalSelfTaxTarget S ≤ A.limitAction

/-- Which OT-to-Gram calibration guard was left unpaid. -/
inductive OTGramImportCalibrationGuardBranch where
  | otObservableDeclared
  | outputAtomMapDeclared
  | gramKernelPushforward
  | constantsDeclared
  | noHiddenSourceL2OrMovingAtoms
deriving DecidableEq, Repr

/-- Falsifier for an OT import calibration that records a guard as prose but
does not pay it as a proof field. -/
structure OTGramImportCalibrationGuardFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω)
    (C : OTGramImportCalibration S A) where
  branch : OTGramImportCalibrationGuardBranch
  missing :
    match branch with
    | OTGramImportCalibrationGuardBranch.otObservableDeclared =>
        ¬ C.ot_observable_declared_before_payoff
    | OTGramImportCalibrationGuardBranch.outputAtomMapDeclared =>
        ¬ C.output_atom_to_ot_state_map_declared
    | OTGramImportCalibrationGuardBranch.gramKernelPushforward =>
        ¬ C.gram_kernel_pushes_forward_to_ot_metric
    | OTGramImportCalibrationGuardBranch.constantsDeclared =>
        ¬ C.constants_declared_before_payoff
    | OTGramImportCalibrationGuardBranch.noHiddenSourceL2OrMovingAtoms =>
        ¬ C.no_hidden_source_l2_or_moving_atoms

/-- A paid OT-to-Gram calibration excludes each guard-failure branch. -/
theorem no_ot_gram_import_calibration_guard_falsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω)
    (C : OTGramImportCalibration S A)
    (F : OTGramImportCalibrationGuardFalsifier S A C) :
    False := by
  rcases F with ⟨branch, hmissing⟩
  cases branch with
  | otObservableDeclared =>
      exact hmissing C.ot_observable_declared_before_payoff_paid
  | outputAtomMapDeclared =>
      exact hmissing C.output_atom_to_ot_state_map_declared_paid
  | gramKernelPushforward =>
      exact hmissing C.gram_kernel_pushes_forward_to_ot_metric_paid
  | constantsDeclared =>
      exact hmissing C.constants_declared_before_payoff_paid
  | noHiddenSourceL2OrMovingAtoms =>
      exact hmissing C.no_hidden_source_l2_or_moving_atoms_paid

/-- The declared all-output Gram target is dominated by the OT limit action
only through the paid calibration object. -/
theorem continuum_global_target_le_ot_limit_action_of_calibration
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω)
    (C : OTGramImportCalibration S A) :
    continuumGlobalSelfTaxTarget S ≤ A.limitAction :=
  C.declared_gram_target_le_ot_limit_action

/-- Each OT prefix action is charged by the fixed all-output Gram prefix price
only through the same paid calibration object. -/
theorem ot_prefix_action_le_all_output_gram_price_of_calibration
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω)
    (C : OTGramImportCalibration S A)
    (n : ℕ) :
    A.prefixAction n ≤ continuumLPPrefixPrice S n :=
  C.prefix_ot_action_le_all_output_gram_price n

/-- Minimal OT import receipt for the all-output Gram LSC field. -/
structure OTGramLSCImportReceipt
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω) where
  ot_action_lower_semicontinuous : OTActionLowerSemicontinuous A
  calibration : OTGramImportCalibration S A

/-- OT action LSC plus the explicit calibration gives the existing continuum
LP/profile price LSC obligation.

This theorem is the only valid import route: OT LSC supplies the middle
inequality, while the calibration fields translate it into the all-output Gram
price topology. -/
theorem continuum_price_lsc_of_ot_gram_import_receipt
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω)
    (R : OTGramLSCImportReceipt S A) :
    ContinuumLPPriceLowerSemicontinuous S := by
  intro _hfixed ε hε
  obtain ⟨N, hN⟩ :=
    R.ot_action_lower_semicontinuous
      R.calibration.fixed_ot_topology
      ε
      hε
  refine ⟨N, ?_⟩
  intro n hn
  have hot_lsc : A.limitAction ≤ A.prefixAction n + ε := hN n hn
  have htarget :
      continuumGlobalSelfTaxTarget S ≤ A.limitAction :=
    R.calibration.declared_gram_target_le_ot_limit_action
  have hprefix :
      A.prefixAction n ≤ continuumLPPrefixPrice S n :=
    R.calibration.prefix_ot_action_le_all_output_gram_price n
  linarith

/-- Full all-output receipt with the OT route used only for the LSC field.

The finite prefix charges, liminf price bound, and smooth budget bridge remain
explicit because OT action LSC alone does not provide them. -/
structure AllOutputOTGramLSCImportReceipt
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω) where
  ot_import : OTGramLSCImportReceipt S A
  prefix_charge : ∀ N : ℕ, PrefixAllOutputCoherenceCharge S N
  liminf_price_bound : ContinuumLPLiminfPriceBound S
  smooth_budget_bridge : ContinuumLPSmoothBudgetBridge S
  declared_target_not_backfit_after_payoff : Prop
  declared_target_not_backfit_after_payoff_paid :
    declared_target_not_backfit_after_payoff

/-- The OT import receipt routes to the existing all-output
positive-coherence/L1 LSC receipt, provided the non-OT fields are also paid. -/
def all_output_positive_coherence_lsc_receipt_of_ot_gram_import
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    {ω : OTActionTopology.{v}}
    {A : OTActionStream ω}
    (R : AllOutputOTGramLSCImportReceipt S A) :
    AllOutputPositiveCoherenceLSCReceipt S where
  fixed_topology := R.ot_import.calibration.fixed_lp_topology
  fixed_atoms := R.ot_import.calibration.fixed_atoms
  prefix_charge := R.prefix_charge
  price_lower_semicontinuous :=
    continuum_price_lsc_of_ot_gram_import_receipt S A R.ot_import
  liminf_price_bound := R.liminf_price_bound
  smooth_budget_bridge := R.smooth_budget_bridge

/-- Existing no-smooth-escape conclusion obtained through the OT import route.
-/
theorem no_smooth_escape_of_ot_gram_lsc_import
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω)
    (R : AllOutputOTGramLSCImportReceipt S A) :
    ¬ ContinuumLPSmoothEscapeCandidate S :=
  no_smooth_escape_candidate_of_all_output_positive_coherence_lsc
    S
    (all_output_positive_coherence_lsc_receipt_of_ot_gram_import R)

/-- Falsifier for an OT-import route whose all-output target was allowed to be
backfit after payoff scoring.

The OT action LSC may still hold in this case; what fails is the admissibility
of importing that action as the fixed all-output Gram target. -/
structure AllOutputOTGramDeclaredTargetBackfitFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    {A : OTActionStream ω}
    (R : AllOutputOTGramLSCImportReceipt S A) where
  missing_no_backfit :
    ¬ R.declared_target_not_backfit_after_payoff

/-- An OT Gram import receipt excludes its own declared-target backfit
falsifier.  This keeps the no-backfit guard load-bearing even though the base
`AllOutputPositiveCoherenceLSCReceipt` does not carry that guard field. -/
theorem no_all_output_ot_gram_declared_target_backfit_falsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    {A : OTActionStream ω}
    (R : AllOutputOTGramLSCImportReceipt S A)
    (F : AllOutputOTGramDeclaredTargetBackfitFalsifier S R) :
    False :=
  F.missing_no_backfit R.declared_target_not_backfit_after_payoff_paid

/-- Exact obstruction to treating OT action LSC as automatically sufficient.

This witness says: the OT action may be lower-semicontinuous in its own fixed
topology, but the all-output Gram price still has a tail-recurring gap in the
LP/Bony topology.  Such a witness is compatible with OT LSC until the
calibration inequalities are proved. -/
structure OTActionLSCButGramGapFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω) where
  ot_action_lower_semicontinuous : OTActionLowerSemicontinuous A
  fixed_lp_topology : ContinuumLPUsesFixedTopology S
  fixed_atoms : FixedAllOutputLPBonyAtoms S
  gap : Real
  gap_pos : 0 < gap
  arbitrarily_late_underpriced_output_gram :
    ∀ N : ℕ, ∃ n : ℕ,
      N ≤ n ∧
        continuumLPPrefixPrice S n + gap <
          continuumGlobalSelfTaxTarget S

/-- A tail-recurring all-output Gram gap rules out any OT import receipt.

The proof deliberately reuses the existing all-output LSC falsifier.  OT LSC is
not contradicted; the missing object is the calibration from OT action to the
fixed all-output Gram ledger. -/
theorem no_ot_gram_lsc_import_receipt_of_gram_gap
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    {ω : OTActionTopology.{v}}
    (A : OTActionStream ω)
    (F : OTActionLSCButGramGapFalsifier S A) :
    OTGramLSCImportReceipt S A → False := by
  intro R
  have hprice_lsc :
      ContinuumLPPriceLowerSemicontinuous S :=
    continuum_price_lsc_of_ot_gram_import_receipt S A R
  let G : AllOutputCoherencePriceLSCFailureFalsifier S :=
    { fixed_topology := F.fixed_lp_topology
      fixed_atoms := F.fixed_atoms
      gap := F.gap
      gap_pos := F.gap_pos
      arbitrarily_late_underpriced_output_coherence :=
        F.arbitrarily_late_underpriced_output_gram }
  exact
    no_continuum_lp_price_lsc_of_all_output_coherence_falsifier
      S G hprice_lsc

end

end ZtareProofs.NS
