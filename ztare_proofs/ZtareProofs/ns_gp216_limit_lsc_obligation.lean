import Mathlib.Tactic

/-!
# GP-216 continuum LP/profile LSC obligation

This file records the continuum LP/profile lower-semicontinuity gap as an
abstract interface.  It does not prove any Navier-Stokes regularity statement:
the topology, convergence assertion, prefix prices, liminf bound, and budget
bridge are all explicit hypotheses.

The small theorem at the end says only that a smooth escape candidate cannot
beat the declared global self-tax target once the liminf price bound and budget
bridge are supplied for the same fixed LP/profile stream.
-/

namespace ZtareProofs.NS

noncomputable section

universe u

/-- Fixed continuum LP/profile topology data.

`ConvergesTo` is intentionally abstract.  A PDE instantiation must provide the
actual topology and prove that the chosen prefix profiles converge to the
declared limit profile in this fixed topology. -/
structure ContinuumLPProfileTopology where
  Profile : Type u
  ConvergesTo : (ℕ → Profile) → Profile → Prop
  SmoothLimit : Profile → Prop
  fixedDecompositionDeclared : Prop

/-- Prefix price stream for one fixed continuum LP/profile decomposition.

The three prefix price fields are scalar ledgers for the self-tax, cross/profile
defect, and residual/coherence components.  `globalSelfTaxTarget` is the
declared continuum target price that a smooth escape would have to beat. -/
structure ContinuumLPPrefixPriceStream
    (τ : ContinuumLPProfileTopology.{u}) where
  prefixProfile : ℕ → τ.Profile
  limitProfile : τ.Profile
  prefixSelfTaxPrice : ℕ → Real
  prefixCrossProfilePrice : ℕ → Real
  prefixResidualPrice : ℕ → Real
  smoothCandidatePayoff : Real
  globalSelfTaxTarget : Real

/-- Total finite-prefix price charged by the declared LP/profile ledger. -/
def continuumLPPrefixPrice
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) (n : ℕ) : Real :=
  S.prefixSelfTaxPrice n +
    S.prefixCrossProfilePrice n +
      S.prefixResidualPrice n

/-- The global self-tax target associated with the stream. -/
def continuumGlobalSelfTaxTarget
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) : Real :=
  S.globalSelfTaxTarget

/-- The stream uses the one fixed LP/profile topology and decomposition. -/
def ContinuumLPUsesFixedTopology
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) : Prop :=
  τ.fixedDecompositionDeclared ∧
    τ.ConvergesTo S.prefixProfile S.limitProfile

/-- Lower-semicontinuity direction for the declared global self-tax target.

This is the analytic obligation `target <= liminf prefixPrice`, expressed in
epsilon/eventual form to keep the interface independent of a particular
`Filter.liminf` formalization. -/
def ContinuumLPPriceLowerSemicontinuous
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) : Prop :=
  ContinuumLPUsesFixedTopology S →
    ∀ ε : Real, 0 < ε → ∃ N : ℕ, ∀ n : ℕ,
      N ≤ n →
        continuumGlobalSelfTaxTarget S ≤
          continuumLPPrefixPrice S n + ε

/-- A Mathlib `liminf` lower bound supplies the epsilon/eventual
lower-semicontinuity field used by the Track B continuum LP receipt.

The boundedness hypotheses are exactly the side conditions required by
Mathlib's real-valued `Filter.le_liminf_iff'`; the fixed-topology proof remains
an explicit input to `ContinuumLPPriceLowerSemicontinuous`, but this scalar
adapter does not need to inspect it. -/
theorem continuum_price_lsc_of_liminf_ge_global_target
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (hcobounded :
      Filter.atTop.IsCoboundedUnder (· ≥ ·)
        (fun n : ℕ => continuumLPPrefixPrice S n))
    (hbounded :
      Filter.atTop.IsBoundedUnder (· ≥ ·)
        (fun n : ℕ => continuumLPPrefixPrice S n))
    (hliminf :
      continuumGlobalSelfTaxTarget S ≤
        Filter.liminf
          (fun n : ℕ => continuumLPPrefixPrice S n)
          Filter.atTop) :
    ContinuumLPPriceLowerSemicontinuous S := by
  intro _ ε hε
  have hlt :
      continuumGlobalSelfTaxTarget S - ε <
        continuumGlobalSelfTaxTarget S := by
    linarith
  have hev :
      ∀ᶠ n : ℕ in Filter.atTop,
        continuumGlobalSelfTaxTarget S - ε ≤
          continuumLPPrefixPrice S n :=
    ((Filter.le_liminf_iff'
      (f := Filter.atTop)
      (u := fun n : ℕ => continuumLPPrefixPrice S n)
      hcobounded
      hbounded).mp hliminf)
      (continuumGlobalSelfTaxTarget S - ε) hlt
  obtain ⟨N, hN⟩ := Filter.eventually_atTop.mp hev
  refine ⟨N, ?_⟩
  intro n hn
  have hn_lower :
      continuumGlobalSelfTaxTarget S - ε ≤
        continuumLPPrefixPrice S n :=
    hN n hn
  linarith

/-- Kinematic-action source for a continuum LP lower-semicontinuity receipt.

This is the proof-facing form of the optimal-transport/Benamou-Brenier
inspiration: the PDE side must provide a predeclared action functional whose
weak-limit lower bound already dominates the global target, and must prove
that each finite prefix price dominates that action.  The adapter below only
uses Mathlib's monotonicity of `liminf`; it does not declare the action bound
for free. -/
structure ContinuumLPKinematicActionLSCSource
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) where
  action : ℕ → Real
  action_declared_before_payoff : Prop
  action_declared_before_payoff_paid :
    action_declared_before_payoff
  target_le_liminf_action :
    continuumGlobalSelfTaxTarget S ≤
      Filter.liminf action Filter.atTop
  action_le_prefix_price :
    ∀ n : ℕ, action n ≤ continuumLPPrefixPrice S n
  action_bounded :
    Filter.atTop.IsBoundedUnder (· ≥ ·) action
  prefix_cobounded :
    Filter.atTop.IsCoboundedUnder (· ≥ ·)
      (fun n : ℕ => continuumLPPrefixPrice S n)
  prefix_bounded :
    Filter.atTop.IsBoundedUnder (· ≥ ·)
      (fun n : ℕ => continuumLPPrefixPrice S n)

/-- Hostile falsifier surface for a claimed kinematic-action LSC source.

The action source is invalid if the action was chosen after payoff scoring, if
the action does not carry the global-target liminf lower bound, or if some
finite prefix price undercharges the action it is supposed to dominate. -/
inductive ContinuumLPKinematicActionLSCFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (K : ContinuumLPKinematicActionLSCSource S) : Prop where
  | action_not_declared :
      ¬ K.action_declared_before_payoff →
        ContinuumLPKinematicActionLSCFalsifier S K
  | target_liminf_shortfall :
      ¬ continuumGlobalSelfTaxTarget S ≤
          Filter.liminf K.action Filter.atTop →
        ContinuumLPKinematicActionLSCFalsifier S K
  | prefix_undercharges_action :
      (n : ℕ) →
      continuumLPPrefixPrice S n < K.action n →
        ContinuumLPKinematicActionLSCFalsifier S K

/-- A kinematic-action LSC source rules out the exact guard failures for that
same source object. -/
theorem no_continuum_lp_kinematic_action_lsc_falsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (K : ContinuumLPKinematicActionLSCSource S)
    (F : ContinuumLPKinematicActionLSCFalsifier S K) :
    False := by
  cases F with
  | action_not_declared hbad =>
      exact hbad K.action_declared_before_payoff_paid
  | target_liminf_shortfall hbad =>
      exact hbad K.target_le_liminf_action
  | prefix_undercharges_action n hbad =>
      exact not_lt_of_ge (K.action_le_prefix_price n) hbad

/-- A kinematic-action lower bound inherits to the declared LP prefix price.

This is the non-tautological LSC bridge: once a genuine action source is
lower-semicontinuous and each finite LP prefix pays at least that action, the
existing continuum price LSC receipt follows by `Filter.liminf_le_liminf`.
-/
theorem continuum_price_lsc_of_kinematic_action_source
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (K : ContinuumLPKinematicActionLSCSource S) :
    ContinuumLPPriceLowerSemicontinuous S := by
  have hliminf_price :
      continuumGlobalSelfTaxTarget S ≤
        Filter.liminf
          (fun n : ℕ => continuumLPPrefixPrice S n)
          Filter.atTop := by
    exact K.target_le_liminf_action.trans
      (Filter.liminf_le_liminf
        (f := Filter.atTop)
        (u := K.action)
        (v := fun n : ℕ => continuumLPPrefixPrice S n)
        (Filter.Eventually.of_forall K.action_le_prefix_price)
        K.action_bounded
        K.prefix_cobounded)
  exact
    continuum_price_lsc_of_liminf_ge_global_target
      S
      K.prefix_cobounded
      K.prefix_bounded
      hliminf_price

/-- Liminf price upper bound for the prefix ledger.

This says the prefix stream has arbitrarily cheap prefixes up to the declared
global target.  Together with the budget bridge, it prevents a smooth escape
payoff from sitting strictly above the target. -/
def ContinuumLPLiminfPriceBound
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) : Prop :=
  ∀ ε : Real, 0 < ε → ∃ n : ℕ,
    continuumLPPrefixPrice S n ≤
      continuumGlobalSelfTaxTarget S + ε

/-- Budget bridge from low prefix prices to the smooth candidate payoff.

The bridge is deliberately abstract: if a prefix realizes the liminf target up
to `ε`, then the same prefix budget must also price the smooth candidate payoff
up to `ε`.  This is the continuum LP/profile gap that must be paid by analysis,
not by this Lean file. -/
def ContinuumLPSmoothBudgetBridge
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) : Prop :=
  ∀ ε : Real, 0 < ε → ∀ n : ℕ,
    continuumLPPrefixPrice S n ≤
      continuumGlobalSelfTaxTarget S + ε →
        S.smoothCandidatePayoff ≤
          continuumLPPrefixPrice S n + ε

/-- Full abstract receipt for the continuum LP/profile LSC obligation. -/
structure ContinuumLPLSCObligationReceipt
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) where
  fixed_topology : ContinuumLPUsesFixedTopology S
  price_lower_semicontinuous : ContinuumLPPriceLowerSemicontinuous S
  liminf_price_bound : ContinuumLPLiminfPriceBound S
  smooth_budget_bridge : ContinuumLPSmoothBudgetBridge S

/-- Fixed all-output LP/Bony atom declaration.

Phase 5IW showed that hidden source-coordinate L2 pricing is not a valid
replacement for output-side pricing: aggregate columns can add constructively.
The continuum theorem must therefore declare the output atoms, Gram/coherence
kernel, physical reserve order, and constants before payoff is scored. -/
structure FixedAllOutputLPBonyAtoms
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) where
  lp_projectors_declared_before_payoff : Prop
  lp_projectors_declared_before_payoff_paid :
    lp_projectors_declared_before_payoff
  bony_interaction_classes_declared : Prop
  bony_interaction_classes_declared_paid :
    bony_interaction_classes_declared
  leray_output_atoms_declared : Prop
  leray_output_atoms_declared_paid :
    leray_output_atoms_declared
  all_output_atom_topology_declared : Prop
  all_output_atom_topology_declared_paid :
    all_output_atom_topology_declared
  gram_coherence_kernel_declared : Prop
  gram_coherence_kernel_declared_paid :
    gram_coherence_kernel_declared
  physical_reserve_order_declared : Prop
  physical_reserve_order_declared_paid :
    physical_reserve_order_declared
  constants_declared_before_payoff : Prop
  constants_declared_before_payoff_paid :
    constants_declared_before_payoff
  no_hidden_source_l2_substitute : Prop
  no_hidden_source_l2_substitute_paid :
    no_hidden_source_l2_substitute

/-- Which fixed all-output LP/Bony atom guard was left unpaid. -/
inductive FixedAllOutputLPBonyAtomsGuardBranch where
  | lpProjectors
  | bonyInteractionClasses
  | lerayOutputAtoms
  | outputAtomTopology
  | gramCoherenceKernel
  | physicalReserveOrder
  | constants
  | noHiddenSourceL2
deriving DecidableEq, Repr

/-- Falsifier for an all-output atom system that records guard labels without
paid witnesses. -/
structure FixedAllOutputLPBonyAtomsGuardFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (A : FixedAllOutputLPBonyAtoms S) where
  branch : FixedAllOutputLPBonyAtomsGuardBranch
  missing :
    match branch with
    | FixedAllOutputLPBonyAtomsGuardBranch.lpProjectors =>
        ¬ A.lp_projectors_declared_before_payoff
    | FixedAllOutputLPBonyAtomsGuardBranch.bonyInteractionClasses =>
        ¬ A.bony_interaction_classes_declared
    | FixedAllOutputLPBonyAtomsGuardBranch.lerayOutputAtoms =>
        ¬ A.leray_output_atoms_declared
    | FixedAllOutputLPBonyAtomsGuardBranch.outputAtomTopology =>
        ¬ A.all_output_atom_topology_declared
    | FixedAllOutputLPBonyAtomsGuardBranch.gramCoherenceKernel =>
        ¬ A.gram_coherence_kernel_declared
    | FixedAllOutputLPBonyAtomsGuardBranch.physicalReserveOrder =>
        ¬ A.physical_reserve_order_declared
    | FixedAllOutputLPBonyAtomsGuardBranch.constants =>
        ¬ A.constants_declared_before_payoff
    | FixedAllOutputLPBonyAtomsGuardBranch.noHiddenSourceL2 =>
        ¬ A.no_hidden_source_l2_substitute

/-- A paid all-output atom declaration excludes every guard-failure branch. -/
theorem no_fixed_all_output_lp_bony_atoms_guard_falsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (A : FixedAllOutputLPBonyAtoms S)
    (F : FixedAllOutputLPBonyAtomsGuardFalsifier S A) :
    False := by
  rcases F with ⟨branch, hmissing⟩
  cases branch with
  | lpProjectors =>
      exact hmissing A.lp_projectors_declared_before_payoff_paid
  | bonyInteractionClasses =>
      exact hmissing A.bony_interaction_classes_declared_paid
  | lerayOutputAtoms =>
      exact hmissing A.leray_output_atoms_declared_paid
  | outputAtomTopology =>
      exact hmissing A.all_output_atom_topology_declared_paid
  | gramCoherenceKernel =>
      exact hmissing A.gram_coherence_kernel_declared_paid
  | physicalReserveOrder =>
      exact hmissing A.physical_reserve_order_declared_paid
  | constants =>
      exact hmissing A.constants_declared_before_payoff_paid
  | noHiddenSourceL2 =>
      exact hmissing A.no_hidden_source_l2_substitute_paid

/-- Finite-prefix all-output/coherence charge.

This is the concrete finite-prefix charge that the analytic theorem must
instantiate from the fixed LP/Bony decomposition.  It separates the
all-output L1/coherence price from branch and residual prices so a proof cannot
silently reuse the invalid source-L2 topology exposed by Phase 5IW. -/
structure PrefixAllOutputCoherenceCharge
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) (N : ℕ) where
  branch_self_tax_charged : Prop
  branch_self_tax_charged_paid :
    branch_self_tax_charged
  cross_profile_defect_charged : Prop
  cross_profile_defect_charged_paid :
    cross_profile_defect_charged
  positive_coherence_charged : Prop
  positive_coherence_charged_paid :
    positive_coherence_charged
  all_output_l1_price_charged : Prop
  all_output_l1_price_charged_paid :
    all_output_l1_price_charged
  physical_reserve_charged : Prop
  physical_reserve_charged_paid :
    physical_reserve_charged
  residual_terms_charged : Prop
  residual_terms_charged_paid :
    residual_terms_charged
  prefix_payoff_le_price :
    S.smoothCandidatePayoff ≤ continuumLPPrefixPrice S N

/-- Which finite-prefix all-output charge guard was left unpaid. -/
inductive PrefixAllOutputCoherenceChargeGuardBranch where
  | branchSelfTax
  | crossProfileDefect
  | positiveCoherence
  | allOutputL1
  | physicalReserve
  | residualTerms
deriving DecidableEq, Repr

/-- Falsifier for a prefix charge that records charged components as labels
without paying those labels. -/
structure PrefixAllOutputCoherenceChargeGuardFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (N : ℕ)
    (C : PrefixAllOutputCoherenceCharge S N) where
  branch : PrefixAllOutputCoherenceChargeGuardBranch
  missing :
    match branch with
    | PrefixAllOutputCoherenceChargeGuardBranch.branchSelfTax =>
        ¬ C.branch_self_tax_charged
    | PrefixAllOutputCoherenceChargeGuardBranch.crossProfileDefect =>
        ¬ C.cross_profile_defect_charged
    | PrefixAllOutputCoherenceChargeGuardBranch.positiveCoherence =>
        ¬ C.positive_coherence_charged
    | PrefixAllOutputCoherenceChargeGuardBranch.allOutputL1 =>
        ¬ C.all_output_l1_price_charged
    | PrefixAllOutputCoherenceChargeGuardBranch.physicalReserve =>
        ¬ C.physical_reserve_charged
    | PrefixAllOutputCoherenceChargeGuardBranch.residualTerms =>
        ¬ C.residual_terms_charged

/-- A paid prefix charge excludes every finite-prefix guard-failure branch. -/
theorem no_prefix_all_output_coherence_charge_guard_falsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (N : ℕ)
    (C : PrefixAllOutputCoherenceCharge S N)
    (F : PrefixAllOutputCoherenceChargeGuardFalsifier S N C) :
    False := by
  rcases F with ⟨branch, hmissing⟩
  cases branch with
  | branchSelfTax =>
      exact hmissing C.branch_self_tax_charged_paid
  | crossProfileDefect =>
      exact hmissing C.cross_profile_defect_charged_paid
  | positiveCoherence =>
      exact hmissing C.positive_coherence_charged_paid
  | allOutputL1 =>
      exact hmissing C.all_output_l1_price_charged_paid
  | physicalReserve =>
      exact hmissing C.physical_reserve_charged_paid
  | residualTerms =>
      exact hmissing C.residual_terms_charged_paid

/-- Proof-facing all-output positive-coherence/L1 LSC receipt.

The fields are still analytic obligations, but they now name the exact
topology that has to be proved lower-semicontinuous. -/
structure AllOutputPositiveCoherenceLSCReceipt
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) where
  fixed_topology : ContinuumLPUsesFixedTopology S
  fixed_atoms : FixedAllOutputLPBonyAtoms S
  prefix_charge : ∀ N : ℕ, PrefixAllOutputCoherenceCharge S N
  price_lower_semicontinuous : ContinuumLPPriceLowerSemicontinuous S
  liminf_price_bound : ContinuumLPLiminfPriceBound S
  smooth_budget_bridge : ContinuumLPSmoothBudgetBridge S

/-- Source bundle for deriving a continuum all-output LP/Bony receipt.

The stream, atoms, charges, and scalar limit-passage duties are carried as one
object so downstream bridges cannot silently switch LP atoms or target prices
after payoff scoring. -/
structure ContinuumAllOutputLPBonySource
    (τ : ContinuumLPProfileTopology.{u}) where
  stream : ContinuumLPPrefixPriceStream τ
  fixed_topology : ContinuumLPUsesFixedTopology stream
  fixed_atoms : FixedAllOutputLPBonyAtoms stream
  prefix_charge : ∀ N : ℕ, PrefixAllOutputCoherenceCharge stream N
  price_lower_semicontinuous :
    ContinuumLPPriceLowerSemicontinuous stream
  liminf_price_bound : ContinuumLPLiminfPriceBound stream
  smooth_budget_bridge : ContinuumLPSmoothBudgetBridge stream
  stream_declared_before_payoff : Prop
  stream_declared_before_payoff_paid :
    stream_declared_before_payoff
  no_posthoc_stream_or_atom_substitution : Prop
  no_posthoc_stream_or_atom_substitution_paid :
    no_posthoc_stream_or_atom_substitution

/-- Build an all-output LP/Bony source from a predeclared kinematic-action
lower-semicontinuity source.

The action source pays only the `price_lower_semicontinuous` field.  Fixed
topology, fixed atoms, finite-prefix charges, liminf upper bound, smooth-budget
bridge, and anti-posthoc guards remain separate source obligations.  This keeps
the optimal-transport/Galerkin action pivot from becoming a tautological
replacement for the full continuum LP/Bony receipt. -/
def continuum_all_output_lp_bony_source_of_kinematic_action_lsc
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (fixed_topology : ContinuumLPUsesFixedTopology S)
    (fixed_atoms : FixedAllOutputLPBonyAtoms S)
    (prefix_charge : ∀ N : ℕ, PrefixAllOutputCoherenceCharge S N)
    (kinematic_action : ContinuumLPKinematicActionLSCSource S)
    (liminf_price_bound : ContinuumLPLiminfPriceBound S)
    (smooth_budget_bridge : ContinuumLPSmoothBudgetBridge S)
    (stream_declared_before_payoff : Prop)
    (stream_declared_before_payoff_paid :
      stream_declared_before_payoff)
    (no_posthoc_stream_or_atom_substitution : Prop)
    (no_posthoc_stream_or_atom_substitution_paid :
      no_posthoc_stream_or_atom_substitution) :
    ContinuumAllOutputLPBonySource τ where
  stream := S
  fixed_topology := fixed_topology
  fixed_atoms := fixed_atoms
  prefix_charge := prefix_charge
  price_lower_semicontinuous :=
    continuum_price_lsc_of_kinematic_action_source S kinematic_action
  liminf_price_bound := liminf_price_bound
  smooth_budget_bridge := smooth_budget_bridge
  stream_declared_before_payoff := stream_declared_before_payoff
  stream_declared_before_payoff_paid := stream_declared_before_payoff_paid
  no_posthoc_stream_or_atom_substitution :=
    no_posthoc_stream_or_atom_substitution
  no_posthoc_stream_or_atom_substitution_paid :=
    no_posthoc_stream_or_atom_substitution_paid

/-- A derived stream receipt records that the downstream stream is exactly the
one supplied by the all-output LP/Bony source. -/
structure ContinuumAllOutputLPBonyDerivedStreamReceipt
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (S : ContinuumLPPrefixPriceStream τ) where
  stream_eq_source : S = source.stream
  stream_declared_from_source :
    source.stream_declared_before_payoff
  no_posthoc_substitution_from_source :
    source.no_posthoc_stream_or_atom_substitution

/-- The source bundle instantiates the all-output positive-coherence receipt
for any downstream stream proved equal to the source stream. -/
def all_output_positive_coherence_lsc_receipt_of_all_output_source
    {τ : ContinuumLPProfileTopology.{u}}
    {source : ContinuumAllOutputLPBonySource τ}
    {S : ContinuumLPPrefixPriceStream τ}
    (R : ContinuumAllOutputLPBonyDerivedStreamReceipt source S) :
    AllOutputPositiveCoherenceLSCReceipt S := by
  cases R.stream_eq_source
  exact
    { fixed_topology := source.fixed_topology
      fixed_atoms := source.fixed_atoms
      prefix_charge := source.prefix_charge
      price_lower_semicontinuous := source.price_lower_semicontinuous
      liminf_price_bound := source.liminf_price_bound
      smooth_budget_bridge := source.smooth_budget_bridge }

/-- All-output positive-coherence/L1 receipt instantiates the generic
continuum LP/profile LSC obligation. -/
def continuum_lsc_receipt_of_all_output_positive_coherence
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (R : AllOutputPositiveCoherenceLSCReceipt S) :
    ContinuumLPLSCObligationReceipt S where
  fixed_topology := R.fixed_topology
  price_lower_semicontinuous := R.price_lower_semicontinuous
  liminf_price_bound := R.liminf_price_bound
  smooth_budget_bridge := R.smooth_budget_bridge

/-- A smooth escape candidate is a smooth limit profile whose payoff beats the
declared global self-tax target in the same fixed topology. -/
structure ContinuumLPSmoothEscapeCandidate
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) where
  fixed_topology : ContinuumLPUsesFixedTopology S
  smooth_limit : τ.SmoothLimit S.limitProfile
  beats_global_self_tax_target :
    continuumGlobalSelfTaxTarget S < S.smoothCandidatePayoff

/-- Liminf price control plus the budget bridge bounds the smooth candidate
payoff by the declared global self-tax target. -/
theorem smooth_candidate_payoff_le_global_self_tax_target
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (hliminf : ContinuumLPLiminfPriceBound S)
    (hbridge : ContinuumLPSmoothBudgetBridge S) :
    S.smoothCandidatePayoff ≤ continuumGlobalSelfTaxTarget S := by
  refine le_of_forall_pos_le_add ?_
  intro ε hε
  have hhalf : 0 < ε / 2 := by linarith
  obtain ⟨n, hprice⟩ := hliminf (ε / 2) hhalf
  have hbudget :
      S.smoothCandidatePayoff ≤
        continuumLPPrefixPrice S n + ε / 2 :=
    hbridge (ε / 2) hhalf n hprice
  calc
    S.smoothCandidatePayoff
        ≤ continuumLPPrefixPrice S n + ε / 2 := hbudget
    _ ≤ (continuumGlobalSelfTaxTarget S + ε / 2) + ε / 2 := by
      linarith
    _ = continuumGlobalSelfTaxTarget S + ε := by
      ring

/-- Main obstruction theorem: once the liminf price bound and budget bridge are
paid, no smooth limit profile can escape above the global self-tax target. -/
theorem no_smooth_escape_candidate_of_liminf_price_bound_and_budget_bridge
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (hliminf : ContinuumLPLiminfPriceBound S)
    (hbridge : ContinuumLPSmoothBudgetBridge S) :
    ¬ ContinuumLPSmoothEscapeCandidate S := by
  intro hescape
  exact not_lt_of_ge
    (smooth_candidate_payoff_le_global_self_tax_target S hliminf hbridge)
    hescape.beats_global_self_tax_target

/-- Receipt-level wrapper including the fixed-topology and LSC fields.  The LSC
field is retained as an explicit obligation even though the final scalar
contradiction only needs the liminf upper bound plus budget bridge. -/
theorem no_smooth_escape_candidate_of_lsc_obligation_receipt
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (R : ContinuumLPLSCObligationReceipt S) :
    ¬ ContinuumLPSmoothEscapeCandidate S :=
  no_smooth_escape_candidate_of_liminf_price_bound_and_budget_bridge
    S
    R.liminf_price_bound
    R.smooth_budget_bridge

/-- Specialized wrapper for the Phase 5IW-correct topology: once the
all-output positive-coherence/L1 LSC receipt is paid, no smooth escape can be
born only at the continuum profile limit. -/
theorem no_smooth_escape_candidate_of_all_output_positive_coherence_lsc
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (R : AllOutputPositiveCoherenceLSCReceipt S) :
    ¬ ContinuumLPSmoothEscapeCandidate S :=
  no_smooth_escape_candidate_of_lsc_obligation_receipt
    S
    (continuum_lsc_receipt_of_all_output_positive_coherence R)

end

end ZtareProofs.NS
