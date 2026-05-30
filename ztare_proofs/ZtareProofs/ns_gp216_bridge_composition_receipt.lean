import Mathlib.Tactic
import ZtareProofs.ns_profile_lsc_self_tax_obligation
import ZtareProofs.ns_beat_backscatter_coherence_charge
import ZtareProofs.ns_low_beat_operator_norm_receipt
import ZtareProofs.ns_low_beat_weighted_l1_receipt
import ZtareProofs.ns_all_output_positive_coherence_lsc
import ZtareProofs.ns_event_recurrence_price_bridge
import ZtareProofs.ns_self_tax_continuation_bkm_bridge
import ZtareProofs.ns_phase_latency_clay_bridge
import ZtareProofs.ns_trackb_coordinate_reformulation_guard
import ZtareProofs.ns_low_high_profile_lipschitz_composition
import ZtareProofs.ns_trackb_continuation_handoff_receipt
import ZtareProofs.ns_flat_torus_killing_mode
import ZtareProofs.ns_high_high_self_tax_charging_obligation

/-!
# GP-216 bridge composition receipt

This file is a local composition receipt for the GP-216/5IQ critical gap C.
It does not target the exponential obstruction route.  It records the smallest
Lean-level bridge needed to say that the already declared branch, self-tax,
coherence, low-beat reserve, and continuation assumptions exclude a remaining
survivor/global-bridge candidate within the declared scope.
-/

namespace ZtareProofs.NS

noncomputable section

universe u

/-- Select one component price from a Leray self-tax/profile stream.

This is the small typed handle used by the numeric-liminf source: future
constructors must produce observables from the selected stream's component
prices, not from an arbitrary scalar family. -/
def LeraySelfTaxProfilePriceStream.prefixPriceForComponent
    (S : LeraySelfTaxProfilePriceStream)
    (component : LeraySelfTaxPriceComponent)
    (k : ℕ) : Real :=
  match component with
  | LeraySelfTaxPriceComponent.selfTax => S.prefixSelfTaxPrice k
  | LeraySelfTaxPriceComponent.crossDefect => S.prefixCrossDefectPrice k
  | LeraySelfTaxPriceComponent.coherence => S.prefixCoherencePrice k

/-- Select one limit component price from a Leray self-tax/profile stream. -/
def LeraySelfTaxProfilePriceStream.limitPriceForComponent
    (S : LeraySelfTaxProfilePriceStream)
    (component : LeraySelfTaxPriceComponent) : Real :=
  match component with
  | LeraySelfTaxPriceComponent.selfTax => S.selfTaxLimitPrice
  | LeraySelfTaxPriceComponent.crossDefect => S.crossDefectLimitPrice
  | LeraySelfTaxPriceComponent.coherence => S.coherenceLimitPrice

/-- Compatibility receipt tying the event-recurrence ledger to the same
all-output LP/Bony prefix stream used by the continuum LSC receipt.

This prevents the GP-216 composition from closing with an event certificate
whose recurrence prices live outside the declared all-output/coherence topology.
It is only a coupling receipt, not a PDE estimate. -/
structure AllOutputEventRecurrenceCouplingDeclarations
    {τ : ContinuumLPProfileTopology.{u}}
    (_S : ContinuumLPPrefixPriceStream τ)
    (_L : EventRecurrencePriceLedger) where
  event_decomposition_refines_all_output_atoms : Prop
  event_gain_declared_in_same_output_observable : Prop
  event_prices_declared_before_payoff : Prop

structure AllOutputEventRecurrenceCoupling
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (L : EventRecurrencePriceLedger) where
  fixed_topology : ContinuumLPUsesFixedTopology S
  fixed_atoms : FixedAllOutputLPBonyAtoms S
  fixed_atoms_lp_projectors_declared :
    fixed_atoms.lp_projectors_declared_before_payoff
  fixed_atoms_bony_classes_declared :
    fixed_atoms.bony_interaction_classes_declared
  fixed_atoms_leray_outputs_declared :
    fixed_atoms.leray_output_atoms_declared
  fixed_atoms_output_topology_declared :
    fixed_atoms.all_output_atom_topology_declared
  fixed_atoms_gram_kernel_declared :
    fixed_atoms.gram_coherence_kernel_declared
  fixed_atoms_physical_reserve_order_declared :
    fixed_atoms.physical_reserve_order_declared
  fixed_atoms_constants_declared :
    fixed_atoms.constants_declared_before_payoff
  fixed_atoms_no_hidden_source_l2 :
    fixed_atoms.no_hidden_source_l2_substitute
  declarations : AllOutputEventRecurrenceCouplingDeclarations S L
  event_decomposition_refines_all_output_atoms :
    declarations.event_decomposition_refines_all_output_atoms
  event_gain_declared_in_same_output_observable :
    declarations.event_gain_declared_in_same_output_observable
  event_prices_declared_before_payoff :
    declarations.event_prices_declared_before_payoff
  raw_recurrence_price_embeds_in_all_output_prefix :
    ∀ N : ℕ,
      eventRawRecurrencePricePrefix L N ≤ continuumLPPrefixPrice S N

/-- Finite-prefix falsifier for a fake composition: the event recurrence price
needed by the dynamic bridge exceeds the all-output prefix price allegedly
charging the same topology. -/
structure AllOutputEventRecurrencePriceMismatchFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (L : EventRecurrencePriceLedger)
    (C : AllOutputEventRecurrenceCoupling S L) where
  prefixLength : ℕ
  same_fixed_topology : ContinuumLPUsesFixedTopology S
  same_fixed_atoms : FixedAllOutputLPBonyAtoms S
  event_decomposition_claims_same_output_atoms :
    C.declarations.event_decomposition_refines_all_output_atoms
  event_prefix_price_not_charged_by_all_output_prefix :
    continuumLPPrefixPrice S prefixLength <
      eventRawRecurrencePricePrefix L prefixLength

/-- Which fixed-before-payoff guard failed for the event-recurrence /
all-output coupling. -/
inductive AllOutputEventRecurrenceCouplingGuardBranch where
  | fixedTopology
  | fixedAtoms
  | refinesAtoms
  | sameObservable
  | pricesDeclared
deriving DecidableEq, Repr

/-- Falsifier for a coupling that embeds event prices numerically but does not
pay the fixed-topology/output-atom/declared-price guards. -/
structure AllOutputEventRecurrenceCouplingGuardFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (L : EventRecurrencePriceLedger)
    (C : AllOutputEventRecurrenceCoupling S L) where
  branch : AllOutputEventRecurrenceCouplingGuardBranch
  missing :
    match branch with
    | AllOutputEventRecurrenceCouplingGuardBranch.fixedTopology =>
        ¬ ContinuumLPUsesFixedTopology S
    | AllOutputEventRecurrenceCouplingGuardBranch.fixedAtoms =>
        ¬ (C.fixed_atoms.lp_projectors_declared_before_payoff ∧
          C.fixed_atoms.bony_interaction_classes_declared ∧
          C.fixed_atoms.leray_output_atoms_declared ∧
          C.fixed_atoms.all_output_atom_topology_declared ∧
          C.fixed_atoms.gram_coherence_kernel_declared ∧
          C.fixed_atoms.physical_reserve_order_declared ∧
          C.fixed_atoms.constants_declared_before_payoff ∧
          C.fixed_atoms.no_hidden_source_l2_substitute)
    | AllOutputEventRecurrenceCouplingGuardBranch.refinesAtoms =>
        ¬ C.declarations.event_decomposition_refines_all_output_atoms
    | AllOutputEventRecurrenceCouplingGuardBranch.sameObservable =>
        ¬ C.declarations.event_gain_declared_in_same_output_observable
    | AllOutputEventRecurrenceCouplingGuardBranch.pricesDeclared =>
        ¬ C.declarations.event_prices_declared_before_payoff

/-- A valid event/all-output coupling excludes missing coupling guards. -/
theorem no_all_output_event_recurrence_coupling_guard_falsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (L : EventRecurrencePriceLedger)
    (C : AllOutputEventRecurrenceCoupling S L)
    (F : AllOutputEventRecurrenceCouplingGuardFalsifier S L C) :
    False := by
  rcases F with ⟨branch, hmissing⟩
  cases branch with
  | fixedTopology =>
      exact hmissing C.fixed_topology
  | fixedAtoms =>
      exact hmissing
        ⟨C.fixed_atoms_lp_projectors_declared,
          C.fixed_atoms_bony_classes_declared,
          C.fixed_atoms_leray_outputs_declared,
          C.fixed_atoms_output_topology_declared,
          C.fixed_atoms_gram_kernel_declared,
          C.fixed_atoms_physical_reserve_order_declared,
          C.fixed_atoms_constants_declared,
          C.fixed_atoms_no_hidden_source_l2⟩
  | refinesAtoms =>
      exact hmissing C.event_decomposition_refines_all_output_atoms
  | sameObservable =>
      exact hmissing C.event_gain_declared_in_same_output_observable
  | pricesDeclared =>
      exact hmissing C.event_prices_declared_before_payoff

/-- A valid all-output/event-recurrence coupling rules out the corresponding
same-topology prefix price mismatch. -/
theorem no_all_output_event_recurrence_coupling_of_price_mismatch
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (L : EventRecurrencePriceLedger)
    (C : AllOutputEventRecurrenceCoupling S L)
    (F : AllOutputEventRecurrencePriceMismatchFalsifier S L C) :
    False :=
  not_lt_of_ge
    (C.raw_recurrence_price_embeds_in_all_output_prefix F.prefixLength)
    F.event_prefix_price_not_charged_by_all_output_prefix

/-- Compatibility receipt tying the Leray self-tax/profile stream to the same
continuum all-output LP/Bony stream used by the positive-coherence LSC branch.

This is only a coupling receipt.  It does not prove component LSC; it prevents
the composite bridge from closing with a self-tax stream and an all-output
stream that price different prefixes, limits, or payoff objects. -/
structure LeraySelfTaxContinuumCoupling
    {τ : ContinuumLPProfileTopology.{u}}
    (L : LeraySelfTaxProfilePriceStream)
    (S : ContinuumLPPrefixPriceStream τ) where
  fixed_topology : ContinuumLPUsesFixedTopology S
  prefix_self_tax_price_matches :
    ∀ n : ℕ, L.prefixSelfTaxPrice n = S.prefixSelfTaxPrice n
  prefix_cross_defect_price_matches :
    ∀ n : ℕ, L.prefixCrossDefectPrice n = S.prefixCrossProfilePrice n
  prefix_coherence_price_matches :
    ∀ n : ℕ, L.prefixCoherencePrice n = S.prefixResidualPrice n
  payoff_limit_matches :
    L.payoffLimit = S.smoothCandidatePayoff
  total_limit_price_matches :
    leraySelfTaxLimitPrice L = continuumGlobalSelfTaxTarget S

/-- Which part of the Leray-self-tax / continuum-stream coupling failed. -/
inductive LeraySelfTaxContinuumCouplingComponent where
  | prefixSelfTax
  | prefixCrossDefect
  | prefixCoherence
  | payoffLimit
  | totalLimitPrice
deriving DecidableEq, Repr

/-- Finite falsifier for a mismatch between the Leray self-tax stream and the
continuum all-output stream used in the same GP216 receipt. -/
structure LeraySelfTaxContinuumCouplingMismatchFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (L : LeraySelfTaxProfilePriceStream)
    (S : ContinuumLPPrefixPriceStream τ) where
  n : ℕ
  component : LeraySelfTaxContinuumCouplingComponent
  mismatch :
    match component with
    | LeraySelfTaxContinuumCouplingComponent.prefixSelfTax =>
        L.prefixSelfTaxPrice n ≠ S.prefixSelfTaxPrice n
    | LeraySelfTaxContinuumCouplingComponent.prefixCrossDefect =>
        L.prefixCrossDefectPrice n ≠ S.prefixCrossProfilePrice n
    | LeraySelfTaxContinuumCouplingComponent.prefixCoherence =>
        L.prefixCoherencePrice n ≠ S.prefixResidualPrice n
    | LeraySelfTaxContinuumCouplingComponent.payoffLimit =>
        L.payoffLimit ≠ S.smoothCandidatePayoff
    | LeraySelfTaxContinuumCouplingComponent.totalLimitPrice =>
        leraySelfTaxLimitPrice L ≠ continuumGlobalSelfTaxTarget S

/-- A valid Leray-self-tax / continuum-stream coupling rules out the
corresponding mismatch falsifier. -/
theorem no_leray_self_tax_continuum_coupling_mismatch
    {τ : ContinuumLPProfileTopology.{u}}
    (L : LeraySelfTaxProfilePriceStream)
    (S : ContinuumLPPrefixPriceStream τ)
    (C : LeraySelfTaxContinuumCoupling L S)
    (F : LeraySelfTaxContinuumCouplingMismatchFalsifier L S) :
    False := by
  rcases F with ⟨n, component, hmismatch⟩
  cases component with
  | prefixSelfTax =>
      exact hmismatch (C.prefix_self_tax_price_matches n)
  | prefixCrossDefect =>
      exact hmismatch (C.prefix_cross_defect_price_matches n)
  | prefixCoherence =>
      exact hmismatch (C.prefix_coherence_price_matches n)
  | payoffLimit =>
      exact hmismatch C.payoff_limit_matches
  | totalLimitPrice =>
      exact hmismatch C.total_limit_price_matches

/-- The same-topology Leray self-tax / continuum coupling exposes the exact
total-price identity as a theorem-level edge.

The constraint-basin graph reads theorem signatures more reliably than
structure fields.  Keeping this edge explicit prevents the final GP216 receipt
from hiding the passage from the Leray self-tax limit price to the continuum
all-output target inside a record projection. -/
theorem leray_self_tax_limit_price_eq_continuum_global_target_of_coupling
    {τ : ContinuumLPProfileTopology.{u}}
    (L : LeraySelfTaxProfilePriceStream)
    (S : ContinuumLPPrefixPriceStream τ)
    (C : LeraySelfTaxContinuumCoupling L S) :
    leraySelfTaxLimitPrice L = continuumGlobalSelfTaxTarget S :=
  C.total_limit_price_matches

/-- The same-topology Leray self-tax / continuum coupling preserves aggregate
prefix prices as a named theorem-level edge. -/
theorem leray_self_tax_prefix_price_eq_continuum_prefix_price_of_coupling
    {τ : ContinuumLPProfileTopology.{u}}
    (L : LeraySelfTaxProfilePriceStream)
    (S : ContinuumLPPrefixPriceStream τ)
    (C : LeraySelfTaxContinuumCoupling L S)
    (n : ℕ) :
    leraySelfTaxPrefixPrice L n = continuumLPPrefixPrice S n := by
  unfold leraySelfTaxPrefixPrice continuumLPPrefixPrice
  rw [C.prefix_self_tax_price_matches n,
    C.prefix_cross_defect_price_matches n,
    C.prefix_coherence_price_matches n]

/-- Aggregate tail convergence for the total Leray self-tax/profile price.

This is intentionally weaker than component LSC.  It records only that the
assembled total prefix price tends to the declared total limit price. -/
def LeraySelfTaxPrefixPriceTendsToDeclaredLimit
    (L : LeraySelfTaxProfilePriceStream) : Prop :=
  ∀ ε : Real, 0 < ε → ∃ N : ℕ, ∀ n : ℕ, N ≤ n →
    |leraySelfTaxPrefixPrice L n - leraySelfTaxLimitPrice L| ≤ ε

/-- Falsifier for failed aggregate total-price tail convergence. -/
structure LeraySelfTaxTotalTailConvergenceFalsifier
    (L : LeraySelfTaxProfilePriceStream) where
  gap : Real
  gap_positive : 0 < gap
  arbitrarily_late_gap :
    ∀ N : ℕ, ∃ n : ℕ, N ≤ n ∧
      gap < |leraySelfTaxPrefixPrice L n - leraySelfTaxLimitPrice L|

/-- Aggregate total-price tail convergence excludes a fixed late-tail gap. -/
theorem no_leray_self_tax_total_tail_convergence_falsifier
    (L : LeraySelfTaxProfilePriceStream)
    (H : LeraySelfTaxPrefixPriceTendsToDeclaredLimit L)
    (F : LeraySelfTaxTotalTailConvergenceFalsifier L) :
    False := by
  obtain ⟨N, hN⟩ := H F.gap F.gap_positive
  obtain ⟨n, hn, hgap⟩ := F.arbitrarily_late_gap N
  exact not_lt_of_ge (hN n hn) hgap

/-- A stream with exact aggregate total-tail control but a component LSC drop.

The total prefix price is constantly equal to the declared total limit price,
but the self-tax component prefix exceeds its declared limit.  This is the
component-shift void: total all-output convergence does not by itself certify
component-wise Leray self-tax LSC. -/
def totalTailButSelfTaxComponentDropStream :
    LeraySelfTaxProfilePriceStream where
  prefixPayoff := fun _ => 0
  prefixSelfTaxPrice := fun _ => 2
  prefixCrossDefectPrice := fun _ => 0
  prefixCoherencePrice := fun _ => 0
  payoffLimit := 0
  selfTaxLimitPrice := 1
  crossDefectLimitPrice := 1
  coherenceLimitPrice := 0
  profileTopologyDeclaredBeforePayoff := True
  profileStreamDeclaredBeforePayoff := True
  prefixComponentPricesDeclaredBeforePayoff := True
  limitComponentPricesDeclaredBeforePayoff := True
  noPosthocPayoffDependentStreamChoice := True

/-- Aggregate total-tail convergence does not imply component LSC.

This theorem blocks a tempting GP216 shortcut: same-topology total all-output
tail control may transfer the aggregate price limit, but it cannot replace the
defect-inclusive component LSC receipt. -/
theorem leray_self_tax_total_tail_control_not_component_lsc :
    ∃ S : LeraySelfTaxProfilePriceStream,
      LeraySelfTaxPrefixPriceTendsToDeclaredLimit S ∧
        ¬ LeraySelfTaxComponentLSC S := by
  refine ⟨totalTailButSelfTaxComponentDropStream, ?_, ?_⟩
  · intro ε hε
    refine ⟨0, ?_⟩
    intro n _hn
    norm_num [totalTailButSelfTaxComponentDropStream,
      leraySelfTaxPrefixPrice, leraySelfTaxLimitPrice]
    exact le_of_lt hε
  · intro H
    have hdrop :
        (totalTailButSelfTaxComponentDropStream.selfTaxLimitPrice) <
          totalTailButSelfTaxComponentDropStream.prefixSelfTaxPrice 0 := by
      norm_num [totalTailButSelfTaxComponentDropStream]
    exact not_lt_of_ge (H.self_tax_lsc 0) hdrop

/-- A same-topology coupling transfers all-output countable tail control to
the aggregate Leray self-tax/profile total price.

This adapter does not prove `LeraySelfTaxComponentLSC`: total convergence can
hide component-level price drops unless the component LSC receipt is supplied
separately. -/
theorem leray_self_tax_total_tail_control_of_coupled_countable_gram_tail
    {τ : ContinuumLPProfileTopology.{u}}
    (L : LeraySelfTaxProfilePriceStream)
    (S : ContinuumLPPrefixPriceStream τ)
    (C : LeraySelfTaxContinuumCoupling L S)
    (R : AllOutputCountableGramTailControlReceipt S) :
    LeraySelfTaxPrefixPriceTendsToDeclaredLimit L := by
  intro ε hε
  obtain ⟨N, hN⟩ := R.prefix_price_tends_to_declared_target ε hε
  refine ⟨N, ?_⟩
  intro n hn
  have hprefix :
      leraySelfTaxPrefixPrice L n = continuumLPPrefixPrice S n := by
    exact
      leray_self_tax_prefix_price_eq_continuum_prefix_price_of_coupling
        L S C n
  have hlimit :
      leraySelfTaxLimitPrice L = continuumGlobalSelfTaxTarget S :=
    C.total_limit_price_matches
  rw [hprefix, hlimit]
  exact hN n hn

/-- Same-topology transfer from standard all-output prefix convergence to
aggregate Leray self-tax/profile total-price convergence.

This is the topology-facing version of
`leray_self_tax_total_tail_control_of_coupled_countable_gram_tail`: a PDE
argument can prove ordinary `Tendsto` on the all-output Gram prefix prices,
then use this adapter to obtain the Track B total-price tail field. Component
LSC remains a separate audited-output duty. -/
theorem leray_self_tax_total_tail_control_of_coupled_all_output_tendsto
    {τ : ContinuumLPProfileTopology.{u}}
    (L : LeraySelfTaxProfilePriceStream)
    (S : ContinuumLPPrefixPriceStream τ)
    (C : LeraySelfTaxContinuumCoupling L S)
    (h :
      Filter.Tendsto
        (fun n : ℕ => continuumLPPrefixPrice S n)
        Filter.atTop
        (nhds (continuumGlobalSelfTaxTarget S))) :
    LeraySelfTaxPrefixPriceTendsToDeclaredLimit L := by
  intro ε hε
  have htends : AllOutputPrefixPriceTendsToDeclaredTarget S :=
    all_output_prefix_price_tends_to_declared_target_of_tendsto S h
  obtain ⟨N, hN⟩ := htends ε hε
  refine ⟨N, ?_⟩
  intro n hn
  have hprefix :
      leraySelfTaxPrefixPrice L n = continuumLPPrefixPrice S n := by
    exact
      leray_self_tax_prefix_price_eq_continuum_prefix_price_of_coupling
        L S C n
  have hlimit :
      leraySelfTaxLimitPrice L = continuumGlobalSelfTaxTarget S :=
    C.total_limit_price_matches
  rw [hprefix, hlimit]
  exact hN n hn

/-- Stronger aggregate total envelope transfer when the all-output side has
already supplied the older prefix-dominated-by-limit hypothesis.

This remains a total-price statement, not component LSC. -/
theorem leray_self_tax_total_prefix_dominated_by_limit_of_coupling
    {τ : ContinuumLPProfileTopology.{u}}
    (L : LeraySelfTaxProfilePriceStream)
    (S : ContinuumLPPrefixPriceStream τ)
    (C : LeraySelfTaxContinuumCoupling L S)
    (hpdom : AllOutputPrefixPriceDominatedByLimit S) :
    ∀ n : ℕ, leraySelfTaxPrefixPrice L n ≤ leraySelfTaxLimitPrice L := by
  intro n
  have hprefix :
      leraySelfTaxPrefixPrice L n = continuumLPPrefixPrice S n := by
    exact
      leray_self_tax_prefix_price_eq_continuum_prefix_price_of_coupling
        L S C n
  have hlimit :
      leraySelfTaxLimitPrice L = continuumGlobalSelfTaxTarget S :=
    C.total_limit_price_matches
  rw [hprefix, hlimit]
  exact hpdom n

/-- GP216 self-tax source bundle.

The final bridge must not carry a scalar Leray self-tax stream separately from
the audited Leray-output source that proves its limit-passage guards.  This
bundle keeps the stream and the audited source receipt in one typed object, so
later projections cannot silently swap the scalar stream after the guard facts
have been checked. -/
structure GP216SelfTaxAuditedOutputSourceBundle where
  stream : LeraySelfTaxProfilePriceStream
  audited_source :
    LeraySelfTaxOutputLimitPassageAuditedSourceReceipt stream

/-- Package an already-audited Leray-output source as the GP216 self-tax
bundle.

This is only a provenance constructor: it does not manufacture the audited
source.  It gives PDE-side work a direct endpoint when the output-limit
passage receipt has already been constructed by another route. -/
def gp216_self_tax_audited_output_source_bundle_of_audited_source
    (S : LeraySelfTaxProfilePriceStream)
    (P : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S) :
    GP216SelfTaxAuditedOutputSourceBundle where
  stream := S
  audited_source := P

/-- Build the GP216 self-tax source bundle from a first-class
measure-valued/Young-defect output source.

This is the GP216 endpoint for the theory-builder route: the final bridge can
ask for an audited self-tax bundle while the PDE instantiation supplies the
relaxed defect object directly. -/
def gp216_self_tax_audited_output_source_bundle_of_measure_valued_source
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (C : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hpayoff :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (noncircular_output_convergence_source : Prop)
    (noncircular_output_convergence_source_receipt :
      noncircular_output_convergence_source) :
    GP216SelfTaxAuditedOutputSourceBundle where
  stream := S
  audited_source :=
    audited_output_limit_passage_source_of_measure_valued_source_and_tendsto_prefix_payoff
      S A C hpayoff M
      noncircular_output_convergence_source
      noncircular_output_convergence_source_receipt

/-- Measure-valued GP216 self-tax bundle with noncircularity sourced from the
same Young/defect object. -/
def gp216_self_tax_audited_output_source_bundle_of_measure_valued_source_noncircular
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (C : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hpayoff :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (N : LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt S M) :
    GP216SelfTaxAuditedOutputSourceBundle where
  stream := S
  audited_source :=
    audited_mv_tendsto_output_source_noncircular
      S A C hpayoff M N

/-- GP216 self-tax bundle projected from the bundled noncircular
measure-valued stream source.

This is the clean endpoint for the Young/defect route: the PDE side supplies
one first-class source object `Q`; GP216 consumes only the audited bundle
projection, not the raw ingredient list. -/
def gp216_self_tax_audited_output_source_bundle_of_noncircular_mv_stream_source
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource) :
    GP216SelfTaxAuditedOutputSourceBundle where
  stream := Q.stream
  audited_source :=
    audited_output_limit_passage_of_noncircular_mv_stream_source Q

/-- Diagonal compactness form of the GP216 self-tax source bundle.

This is the endpoint-facing version of the Cauchy/subsequence
Young-measure route: the PDE side may construct a measure-valued limit along a
subsequence and prove Cauchy control of the full payoff-prefix stream, without
first packaging that as a global `Tendsto` proof. -/
def gp216_self_tax_audited_output_source_bundle_of_measure_valued_cauchy_subseq
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (C : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hcauchy : CauchySeq S.prefixPayoff)
    {φ : ℕ → ℕ}
    (hφ : StrictMono φ)
    (hsub :
      Filter.Tendsto
        (fun k : ℕ => S.prefixPayoff (φ k))
        Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (noncircular_output_convergence_source : Prop)
    (noncircular_output_convergence_source_receipt :
      noncircular_output_convergence_source) :
    GP216SelfTaxAuditedOutputSourceBundle where
  stream := S
  audited_source :=
    audited_output_limit_source_of_measure_valued_cauchy_subseq
      S A C hcauchy hφ hsub M
      noncircular_output_convergence_source
      noncircular_output_convergence_source_receipt

/-- Diagonal compactness GP216 self-tax bundle with noncircularity sourced from
the same Young/defect object. -/
def gp216_self_tax_audited_output_source_bundle_of_measure_valued_cauchy_subseq_noncircular
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (C : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hcauchy : CauchySeq S.prefixPayoff)
    {φ : ℕ → ℕ}
    (hφ : StrictMono φ)
    (hsub :
      Filter.Tendsto
        (fun k : ℕ => S.prefixPayoff (φ k))
        Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (N : LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt S M) :
    GP216SelfTaxAuditedOutputSourceBundle where
  stream := S
  audited_source :=
    audited_mv_cauchy_subseq_output_source_noncircular
      S A C hcauchy hφ hsub M N

/-- Output-derived component-limit passage projected directly from the
audited self-tax source bundle. -/
def GP216SelfTaxAuditedOutputSourceBundle.outputDerivedComponentLimitPassage
    (B : GP216SelfTaxAuditedOutputSourceBundle) :
    LeraySelfTaxOutputDerivedComponentLimitPassageReceipt B.stream :=
  output_derived_component_limit_passage_of_audited_output_limit_source
    B.stream
    B.audited_source

/-- Named Leray-output stream source projected from the GP216 self-tax source
bundle. -/
def GP216SelfTaxAuditedOutputSourceBundle.outputLimitStreamSource
    (B : GP216SelfTaxAuditedOutputSourceBundle) :
    LeraySelfTaxOutputLimitStreamSource :=
  output_limit_stream_source_of_audited_passage
    B.stream
    B.audited_source

/-- Reflexive scalar-stream provenance projected from the same GP216 self-tax
source bundle. -/
def GP216SelfTaxAuditedOutputSourceBundle.outputDerivedStreamReceipt
    (B : GP216SelfTaxAuditedOutputSourceBundle) :
    LeraySelfTaxOutputDerivedStreamReceipt
      B.outputLimitStreamSource
      B.stream :=
  output_derived_stream_receipt_refl
    B.outputLimitStreamSource

/-- The GP216 self-tax bundle excludes scalar stream substitution before a
larger component-limit wrapper is projected. -/
theorem GP216SelfTaxAuditedOutputSourceBundle.noOutputSourceSubstitutionFalsifier
    (B : GP216SelfTaxAuditedOutputSourceBundle)
    (F :
      LeraySelfTaxOutputSourceSubstitutionFalsifier
        B.outputLimitStreamSource
        B.stream
        B.outputDerivedStreamReceipt) :
    False :=
  no_output_source_substitution_falsifier
    B.outputLimitStreamSource
    B.stream
    B.outputDerivedStreamReceipt
    F

/-- The audited GP216 self-tax source bundle pays the scalar payoff-to-limit
edge before any continuum target or final bridge is invoked. -/
theorem GP216SelfTaxAuditedOutputSourceBundle.payoff_le_limitPrice
    (B : GP216SelfTaxAuditedOutputSourceBundle) :
    B.stream.payoffLimit ≤ leraySelfTaxLimitPrice B.stream :=
  no_global_self_tax_arbitrage_of_audited_output_limit_source
    B.stream
    B.audited_source

/-- Bundle-level endpoint limit-passage projected from the same audited
Leray-output source.

This is useful for closure attempts that target the upstream endpoint API
without first constructing a whole GP216 composition receipt. -/
def GP216SelfTaxAuditedOutputSourceBundle.trackBEndpointLimitPassage
    (B : GP216SelfTaxAuditedOutputSourceBundle) :
    TrackBSelfTaxEndpointLimitPassageReceipt
      (trackB_self_tax_limit_endpoint_of_leray_stream B.stream) :=
  trackB_self_tax_endpoint_limit_passage_of_audited_output_limit_source
    B.stream
    B.audited_source

/-- GP216 low-beat finite-reserve bundle.

The finite-reserve obstruction needs the low-beat stream, the declared reserve
limit, and the prefix reserve bound to move together.  Bundling the three
prevents a final bridge from swapping the stream after the finite bound has
been checked. -/
structure GP216LowBeatFiniteReserveBundle where
  stream : LowBeatPrefixReserveStream
  reserveLimit : Real
  reserveBounded :
    ∀ n : ℕ, stream.prefixReservePrice n ≤ reserveLimit

/-- GP216 low-beat envelope source bundle.

The finite-reserve stream, fixed-prefix scalar envelope, and moving/all-output
tail envelope must be one declared low-beat source.  Otherwise the bridge can
prove the stream guard, then discharge fixed/moving scalar survivors using
envelope objects whose reserve budget or payoff source was selected
independently. -/
structure GP216LowBeatEnvelopeSourceBundle where
  finiteReserve : GP216LowBeatFiniteReserveBundle
  fixedPrefix : VanishingFixedPrefixLowBeatEnvelope
  movingAllOutput : MovingAllOutputLowBeatEnvelope
  fixed_reserve_matches_stream :
    ∀ n : ℕ,
      fixedPrefix.envelope.reserve n =
        finiteReserve.stream.prefixReservePrice n
  fixed_payoff_matches_stream :
    ∀ n : ℕ,
      fixedPrefix.envelope.payoff n =
        finiteReserve.stream.prefixBeatPayoff n
  fixed_budget_matches_limit :
    fixedPrefix.envelope.budget = finiteReserve.reserveLimit
  moving_budget_matches_limit :
    movingAllOutput.budget = finiteReserve.reserveLimit
  moving_output_topology_predeclared_paid :
    movingAllOutput.output_topology_predeclared
  moving_output_atoms_declared_before_payoff_paid :
    movingAllOutput.output_atoms_declared_before_payoff
  moving_gram_coherence_declared_before_payoff_paid :
    movingAllOutput.gram_coherence_declared_before_payoff
  moving_physical_reserve_declared_before_payoff_paid :
    movingAllOutput.physical_reserve_declared_before_payoff

/-- Falsifier surface for a low-beat envelope bundle whose scalar fixed or
moving envelope is not tied to the same declared finite-reserve source. -/
inductive GP216LowBeatEnvelopeSourceFalsifier
    (B : GP216LowBeatEnvelopeSourceBundle) : Type where
  | fixedReserveMismatch (n : ℕ) :
      B.fixedPrefix.envelope.reserve n ≠
        B.finiteReserve.stream.prefixReservePrice n →
        GP216LowBeatEnvelopeSourceFalsifier B
  | fixedPayoffMismatch (n : ℕ) :
      B.fixedPrefix.envelope.payoff n ≠
        B.finiteReserve.stream.prefixBeatPayoff n →
        GP216LowBeatEnvelopeSourceFalsifier B
  | fixedBudgetMismatch :
      B.fixedPrefix.envelope.budget ≠ B.finiteReserve.reserveLimit →
        GP216LowBeatEnvelopeSourceFalsifier B
  | movingBudgetMismatch :
      B.movingAllOutput.budget ≠ B.finiteReserve.reserveLimit →
        GP216LowBeatEnvelopeSourceFalsifier B
  | movingOutputTopologyUnpaid :
      ¬ B.movingAllOutput.output_topology_predeclared →
        GP216LowBeatEnvelopeSourceFalsifier B
  | movingOutputAtomsUnpaid :
      ¬ B.movingAllOutput.output_atoms_declared_before_payoff →
        GP216LowBeatEnvelopeSourceFalsifier B
  | movingGramCoherenceUnpaid :
      ¬ B.movingAllOutput.gram_coherence_declared_before_payoff →
        GP216LowBeatEnvelopeSourceFalsifier B
  | movingPhysicalReserveUnpaid :
      ¬ B.movingAllOutput.physical_reserve_declared_before_payoff →
        GP216LowBeatEnvelopeSourceFalsifier B

/-- A low-beat envelope source bundle excludes scalar-envelope substitution
and unpaid moving-output declaration branches. -/
theorem no_gp216_low_beat_envelope_source_falsifier
    (B : GP216LowBeatEnvelopeSourceBundle)
    (F : GP216LowBeatEnvelopeSourceFalsifier B) :
    False := by
  cases F with
  | fixedReserveMismatch n h =>
      exact h (B.fixed_reserve_matches_stream n)
  | fixedPayoffMismatch n h =>
      exact h (B.fixed_payoff_matches_stream n)
  | fixedBudgetMismatch h =>
      exact h B.fixed_budget_matches_limit
  | movingBudgetMismatch h =>
      exact h B.moving_budget_matches_limit
  | movingOutputTopologyUnpaid h =>
      exact h B.moving_output_topology_predeclared_paid
  | movingOutputAtomsUnpaid h =>
      exact h B.moving_output_atoms_declared_before_payoff_paid
  | movingGramCoherenceUnpaid h =>
      exact h B.moving_gram_coherence_declared_before_payoff_paid
  | movingPhysicalReserveUnpaid h =>
      exact h B.moving_physical_reserve_declared_before_payoff_paid

/-- GP216 event-recurrence auxiliary panel bundle.

These receipts are not independent global-bridge inputs; they are the hostile
search/audit panels for the event-recurrence PDE obligation.  Keeping them
under the event source prevents the final receipt from treating latency,
decoupling, and Fourier falsifier checks as decorative root-level baggage. -/
structure GP216EventRecurrenceAuxiliaryPanelBundle where
  lowerEnvelopeGeometryProbe :
    EventLowerEnvelopeGeometryProbeReceipt
  lowerEnvelopeSmoothFalsifier :
    EventLowerEnvelopeSmoothFalsifierReceipt
  fractionalLogGainAdversary :
    FractionalLogGainAdversaryReceipt
  reserveGainDecouplingSearch :
    ReserveGainDecouplingSearchReceipt
  matrixReserveGainDecouplingAudit :
    MatrixReserveGainDecouplingAuditReceipt
  setupLatencyExecutionCost :
    SetupLatencyExecutionCostReceipt
  dynamicLatencyCounterexampleSearch :
    DynamicLatencyCounterexampleSearchReceipt
  smoothLatencyPDEObligationFalsifier :
    SmoothLatencyPDEObligationFalsifierReceipt
  concreteFourierLatencyFalsifier :
    ConcreteFourierLatencyFalsifierReceipt

/-- Paid surface for all event-recurrence hostile-search panels. -/
def GP216EventRecurrenceAuxiliaryPanelBundle.Paid
    (B : GP216EventRecurrenceAuxiliaryPanelBundle) : Prop :=
  B.lowerEnvelopeGeometryProbe.Paid ∧
    B.lowerEnvelopeSmoothFalsifier.Paid ∧
      B.fractionalLogGainAdversary.Paid ∧
        B.reserveGainDecouplingSearch.Paid ∧
          B.matrixReserveGainDecouplingAudit.Paid ∧
            B.setupLatencyExecutionCost.Paid ∧
              B.dynamicLatencyCounterexampleSearch.Paid ∧
                B.smoothLatencyPDEObligationFalsifier.Paid ∧
                  B.concreteFourierLatencyFalsifier.Paid

/-- The auxiliary event-recurrence panel bundle is paid exactly when each
hostile-search receipt carries its own paid anti-tautology guards. -/
theorem GP216EventRecurrenceAuxiliaryPanelBundle.paid
    (B : GP216EventRecurrenceAuxiliaryPanelBundle) :
    B.Paid :=
  ⟨B.lowerEnvelopeGeometryProbe.paid,
    B.lowerEnvelopeSmoothFalsifier.paid,
    B.fractionalLogGainAdversary.paid,
    B.reserveGainDecouplingSearch.paid,
    B.matrixReserveGainDecouplingAudit.paid,
    B.setupLatencyExecutionCost.paid,
    B.dynamicLatencyCounterexampleSearch.paid,
    B.smoothLatencyPDEObligationFalsifier.paid,
    B.concreteFourierLatencyFalsifier.paid⟩

/-- Named ways an event-recurrence auxiliary panel bundle can fail to be paid.

This is only a typed projection of the existing panel receipts.  It does not
add a new analytic assumption; it prevents GP216 from treating the conjunction
`P.Paid` as an opaque failure mode. -/
inductive GP216EventRecurrenceAuxiliaryPanelFalsifier
    (B : GP216EventRecurrenceAuxiliaryPanelBundle) : Type where
  | lowerEnvelopeGeometryProbeUnpaid :
      ¬ B.lowerEnvelopeGeometryProbe.Paid →
        GP216EventRecurrenceAuxiliaryPanelFalsifier B
  | lowerEnvelopeSmoothFalsifierUnpaid :
      ¬ B.lowerEnvelopeSmoothFalsifier.Paid →
        GP216EventRecurrenceAuxiliaryPanelFalsifier B
  | fractionalLogGainAdversaryUnpaid :
      ¬ B.fractionalLogGainAdversary.Paid →
        GP216EventRecurrenceAuxiliaryPanelFalsifier B
  | reserveGainDecouplingSearchUnpaid :
      ¬ B.reserveGainDecouplingSearch.Paid →
        GP216EventRecurrenceAuxiliaryPanelFalsifier B
  | matrixReserveGainDecouplingAuditUnpaid :
      ¬ B.matrixReserveGainDecouplingAudit.Paid →
        GP216EventRecurrenceAuxiliaryPanelFalsifier B
  | setupLatencyExecutionCostUnpaid :
      ¬ B.setupLatencyExecutionCost.Paid →
        GP216EventRecurrenceAuxiliaryPanelFalsifier B
  | dynamicLatencyCounterexampleSearchUnpaid :
      ¬ B.dynamicLatencyCounterexampleSearch.Paid →
        GP216EventRecurrenceAuxiliaryPanelFalsifier B
  | smoothLatencyPDEObligationFalsifierUnpaid :
      ¬ B.smoothLatencyPDEObligationFalsifier.Paid →
        GP216EventRecurrenceAuxiliaryPanelFalsifier B
  | concreteFourierLatencyFalsifierUnpaid :
      ¬ B.concreteFourierLatencyFalsifier.Paid →
        GP216EventRecurrenceAuxiliaryPanelFalsifier B

/-- A bundle whose individual hostile-search panels are paid excludes every
panel-specific unpaid branch. -/
theorem no_gp216_event_recurrence_auxiliary_panel_falsifier
    (B : GP216EventRecurrenceAuxiliaryPanelBundle)
    (F : GP216EventRecurrenceAuxiliaryPanelFalsifier B) :
    False := by
  cases F with
  | lowerEnvelopeGeometryProbeUnpaid h =>
      exact h B.lowerEnvelopeGeometryProbe.paid
  | lowerEnvelopeSmoothFalsifierUnpaid h =>
      exact h B.lowerEnvelopeSmoothFalsifier.paid
  | fractionalLogGainAdversaryUnpaid h =>
      exact h B.fractionalLogGainAdversary.paid
  | reserveGainDecouplingSearchUnpaid h =>
      exact h B.reserveGainDecouplingSearch.paid
  | matrixReserveGainDecouplingAuditUnpaid h =>
      exact h B.matrixReserveGainDecouplingAudit.paid
  | setupLatencyExecutionCostUnpaid h =>
      exact h B.setupLatencyExecutionCost.paid
  | dynamicLatencyCounterexampleSearchUnpaid h =>
      exact h B.dynamicLatencyCounterexampleSearch.paid
  | smoothLatencyPDEObligationFalsifierUnpaid h =>
      exact h B.smoothLatencyPDEObligationFalsifier.paid
  | concreteFourierLatencyFalsifierUnpaid h =>
      exact h B.concreteFourierLatencyFalsifier.paid

/-- Handoff from paid event hostile-search panels into the corresponding
event-recurrence PDE duties.

The panels are not decorative diagnostics: a GP216 event source must explain
how paid decoupling/latency/Fourier panels discharge the matching PDE
obligation fields before the event bridge can use them. -/
structure GP216EventAuxiliaryPanelsPDEHandoff
    (P : GP216EventRecurrenceAuxiliaryPanelBundle)
    (O : EventRecurrencePricePDEObligation) where
  pde_duties_of_paid_panels :
    P.Paid →
      O.reserve_gain_decoupling_ruled_out_or_constructed ∧
        O.matrix_reserve_gain_decoupling_ruled_out_or_constructed ∧
          O.setup_latency_execution_cost_ruled_out_or_constructed ∧
            O.dynamic_latency_counterexample_ruled_out_or_constructed ∧
              O.smooth_latency_pde_obligation_ruled_out_or_constructed ∧
                O.concrete_fourier_latency_falsifier_ruled_out_or_constructed

/-- Handoff from the three lower-envelope adversary panels into the matching
event-recurrence PDE duties.

These panels sit between the raw Duhamel/Bony event ledger and the later
decoupling/latency audits.  Keeping them in their own handoff prevents the
GP216 source bundle from paying the raw-LP/Bony, super-sqrt/log-reserve, or
fractional harmonic adversary fields as detachable root propositions. -/
structure GP216EventLowerEnvelopePDEHandoff
    (P : GP216EventRecurrenceAuxiliaryPanelBundle)
    (O : EventRecurrencePricePDEObligation) where
  lower_envelope_obstruction_of_paid_panels :
    P.lowerEnvelopeGeometryProbe.Paid →
      P.lowerEnvelopeSmoothFalsifier.Paid →
        O.raw_lp_bony_underpricing_obstruction_addressed
  super_sqrt_or_log_reserve_of_paid_smooth_panel :
    P.lowerEnvelopeSmoothFalsifier.Paid →
      O.super_sqrt_gain_or_predeclared_log_reserve_proved
  fractional_log_adversary_of_paid_panel :
    P.fractionalLogGainAdversary.Paid →
      O.fractional_log_gain_adversary_decoupling_ruled_out_or_constructed

/-- Semantic handoff from the concrete event-price sources to the PDE
checklist.

The PDE obligation is not allowed to be paid by root-level slogans while the
same source bundle separately carries event incidence and a dynamic-price
precertificate.  This handoff makes the section-incidence and pre-certificate
objects load-bearing for the corresponding obligation fields. -/
structure GP216EventRecurrencePDEHandoff
    (O : EventRecurrencePricePDEObligation)
    (L : EventRecurrencePriceLedger)
    (P : EventDynamicRecurrencePricePrecertificate L)
    (I : EventSectionIncidenceReceipt L) where
  fixed_event_sections_paid :
    I.fixed_event_sections_before_payoff
  event_decomposition_of_section :
    I.fixed_event_sections_before_payoff →
      O.event_decomposition_fixed_before_payoff
  event_weights_of_precertificate :
    (∀ e : ℕ, 0 < L.eventWeight e) →
      O.event_weights_declared_before_payoff
  preparation_windows_paid :
    I.preparation_windows_declared_before_payoff
  preparation_windows_of_section :
    I.preparation_windows_declared_before_payoff →
      O.preparation_windows_declared_before_payoff
  resource_overlap_paid :
    I.resource_overlap_measured_before_payoff
  resource_overlap_of_section :
    I.resource_overlap_measured_before_payoff →
      O.resource_overlap_measured_before_payoff
  raw_price_declared_before_payoff_of_precertificate :
    P.event_prices_declared_before_payoff →
      P.event_prices_not_backfit_from_realized_gain_or_payoff →
        O.raw_price_declared_before_payoff
  recurrence_price_declared_before_payoff_of_precertificate :
    P.event_prices_declared_before_payoff →
      P.event_prices_not_backfit_from_realized_gain_or_payoff →
        O.recurrence_price_declared_before_payoff
  raw_recurrence_lower_envelope_of_precertificate :
    (∀ e : ℕ,
      L.eventWeight e * (L.eventGain e) ^ (2 : Nat) ≤
        L.rawPrice e + L.recurrencePrice e) →
      O.raw_recurrence_lower_envelope_proved
  reciprocal_budget_of_section :
    (∀ N : ℕ,
      eventReciprocalWeightPrefix L N ≤ I.eventReciprocalBudget) →
        O.reciprocal_budget_over_events_proved
  overlap_tax_paid :
    I.overlap_tax_charged_before_payoff
  overlap_adjusted_effective_multiplicity_of_section :
    I.overlap_tax_charged_before_payoff →
      O.overlap_adjusted_effective_multiplicity_proved
  finite_cauchy_duality_of_precertificate :
    EventFiniteCauchyDualityField L →
      O.finite_cauchy_duality_over_events_proved
  no_shell_only_budget_shortcut_paid :
    I.no_shell_only_budget_shortcut
  shell_multiplicity_lift_of_section :
    I.no_shell_only_budget_shortcut →
      O.shell_multiplicity_lift_proved_if_using_shell_weights

/-- Duhamel/Bernstein lower-envelope receipts discharge the raw-recurrence
lower-envelope field of the event PDE obligation through the explicit GP216
event handoff.

This theorem only names an existing algebraic route.  The PDE work remains
constructing `EventDuhamelBernsteinLowerEnvelopeReceipt`: same-event kernel
identification, positive-kernel comparison, and same-ledger reserve charging.
-/
theorem event_raw_recurrence_lower_envelope_pde_field_of_duhamel_handoff
    {O : EventRecurrencePricePDEObligation}
    {L : EventRecurrencePriceLedger}
    {P : EventDynamicRecurrencePricePrecertificate L}
    {I : EventSectionIncidenceReceipt L}
    (H : GP216EventRecurrencePDEHandoff O L P I)
    (R : EventDuhamelBernsteinLowerEnvelopeReceipt L) :
    O.raw_recurrence_lower_envelope_proved :=
  H.raw_recurrence_lower_envelope_of_precertificate
    (raw_recurrence_lower_envelope_of_event_duhamel_bernstein L R)

/-- Named ways the event-recurrence PDE handoff can lack the paid source data
it claims to transport from section incidence into the PDE checklist.

This is a provenance surface for the handoff object, not a new PDE estimate.
It exposes the existing paid fields that make event sections, preparation
windows, overlap accounting, and shell-multiplicity lifting load-bearing. -/
inductive GP216EventRecurrencePDEHandoffFalsifier
    {O : EventRecurrencePricePDEObligation}
    {L : EventRecurrencePriceLedger}
    {P : EventDynamicRecurrencePricePrecertificate L}
    {I : EventSectionIncidenceReceipt L}
    (H : GP216EventRecurrencePDEHandoff O L P I) : Type where
  | fixedEventSectionsUnpaid :
      ¬ I.fixed_event_sections_before_payoff →
        GP216EventRecurrencePDEHandoffFalsifier H
  | eventPricesDeclarationUnpaid :
      ¬ P.event_prices_declared_before_payoff →
        GP216EventRecurrencePDEHandoffFalsifier H
  | eventPricesBackfitGuardUnpaid :
      ¬ P.event_prices_not_backfit_from_realized_gain_or_payoff →
        GP216EventRecurrencePDEHandoffFalsifier H
  | preparationWindowsUnpaid :
      ¬ I.preparation_windows_declared_before_payoff →
        GP216EventRecurrencePDEHandoffFalsifier H
  | resourceOverlapUnpaid :
      ¬ I.resource_overlap_measured_before_payoff →
        GP216EventRecurrencePDEHandoffFalsifier H
  | overlapTaxUnpaid :
      ¬ I.overlap_tax_charged_before_payoff →
        GP216EventRecurrencePDEHandoffFalsifier H
  | shellMultiplicityShortcutUnpaid :
      ¬ I.no_shell_only_budget_shortcut →
        GP216EventRecurrencePDEHandoffFalsifier H

/-- A concrete event-recurrence PDE handoff excludes its missing-source
provenance falsifiers. -/
theorem no_gp216_event_recurrence_pde_handoff_falsifier
    {O : EventRecurrencePricePDEObligation}
    {L : EventRecurrencePriceLedger}
    {P : EventDynamicRecurrencePricePrecertificate L}
    {I : EventSectionIncidenceReceipt L}
    (H : GP216EventRecurrencePDEHandoff O L P I)
    (F : GP216EventRecurrencePDEHandoffFalsifier H) :
    False := by
  cases F with
  | fixedEventSectionsUnpaid h =>
      exact h H.fixed_event_sections_paid
  | eventPricesDeclarationUnpaid h =>
      exact h P.event_prices_declared_before_payoff_paid
  | eventPricesBackfitGuardUnpaid h =>
      exact h
        P.event_prices_not_backfit_from_realized_gain_or_payoff_paid
  | preparationWindowsUnpaid h =>
      exact h H.preparation_windows_paid
  | resourceOverlapUnpaid h =>
      exact h H.resource_overlap_paid
  | overlapTaxUnpaid h =>
      exact h H.overlap_tax_paid
  | shellMultiplicityShortcutUnpaid h =>
      exact h H.no_shell_only_budget_shortcut_paid

/-- GP216 event-recurrence source bundle.

The recurrence ledger is only usable in the final bridge together with its
PDE duty checklist, satisfaction receipt, auxiliary hostile-search panels,
section-incidence receipt, and dynamic-price precertificate.  The full
certificate is derived from the section-incidence multiplicity lift, preventing
a closure attempt from carrying a certified event ledger while swapping the
event-incidence source underneath it. -/
structure GP216EventRecurrenceSourceBundle where
  ledger : EventRecurrencePriceLedger
  pdeObligation : EventRecurrencePricePDEObligation
  auxiliaryPanels :
    GP216EventRecurrenceAuxiliaryPanelBundle
  auxiliaryPanelsPDEHandoff :
    GP216EventAuxiliaryPanelsPDEHandoff
      auxiliaryPanels
      pdeObligation
  lowerEnvelopePDEHandoff :
    GP216EventLowerEnvelopePDEHandoff
      auxiliaryPanels
      pdeObligation
  precertificate :
    EventDynamicRecurrencePricePrecertificate ledger
  duhamelLowerEnvelope :
    EventDuhamelBernsteinLowerEnvelopeReceipt ledger
  sectionIncidence :
    EventSectionIncidenceReceipt ledger
  reciprocalBudget_matches_sectionIncidence :
    ledger.reciprocalBudget = sectionIncidence.eventReciprocalBudget
  pdeHandoff :
    GP216EventRecurrencePDEHandoff
      pdeObligation
      ledger
      precertificate
      sectionIncidence

/-- GP216 event PDE satisfaction is derived from the explicit event-duty
fields carried by the source bundle, rather than stored as an opaque proof
beside the obligation. -/
def GP216EventRecurrenceSourceBundle.pdeSatisfied
    (B : GP216EventRecurrenceSourceBundle) :
    EventRecurrencePricePDEObligationSatisfied B.pdeObligation := by
  dsimp [EventRecurrencePricePDEObligationSatisfied]
  rcases B.auxiliaryPanelsPDEHandoff.pde_duties_of_paid_panels
      B.auxiliaryPanels.paid with
    ⟨hreserveGain, hmatrixReserveGain, hsetupLatency, hdynamicLatency,
      hsmoothLatency, hconcreteFourier⟩
  have hrawLpBony :
      B.pdeObligation.raw_lp_bony_underpricing_obstruction_addressed :=
    B.lowerEnvelopePDEHandoff.lower_envelope_obstruction_of_paid_panels
      B.auxiliaryPanels.lowerEnvelopeGeometryProbe.paid
      B.auxiliaryPanels.lowerEnvelopeSmoothFalsifier.paid
  have hsuperSqrt :
      B.pdeObligation.super_sqrt_gain_or_predeclared_log_reserve_proved :=
    B.lowerEnvelopePDEHandoff.super_sqrt_or_log_reserve_of_paid_smooth_panel
      B.auxiliaryPanels.lowerEnvelopeSmoothFalsifier.paid
  have hfractionalLog :
      B.pdeObligation.fractional_log_gain_adversary_decoupling_ruled_out_or_constructed :=
    B.lowerEnvelopePDEHandoff.fractional_log_adversary_of_paid_panel
      B.auxiliaryPanels.fractionalLogGainAdversary.paid
  exact
    ⟨B.pdeHandoff.event_decomposition_of_section
        B.pdeHandoff.fixed_event_sections_paid,
      B.pdeHandoff.event_weights_of_precertificate
        B.precertificate.event_weight_positive,
      B.pdeHandoff.preparation_windows_of_section
        B.pdeHandoff.preparation_windows_paid,
      B.pdeHandoff.resource_overlap_of_section
        B.pdeHandoff.resource_overlap_paid,
      B.pdeHandoff.raw_price_declared_before_payoff_of_precertificate
        B.precertificate.event_prices_declared_before_payoff_paid
        B.precertificate.event_prices_not_backfit_from_realized_gain_or_payoff_paid,
      B.pdeHandoff.recurrence_price_declared_before_payoff_of_precertificate
        B.precertificate.event_prices_declared_before_payoff_paid
        B.precertificate.event_prices_not_backfit_from_realized_gain_or_payoff_paid,
      event_raw_recurrence_lower_envelope_pde_field_of_duhamel_handoff
        B.pdeHandoff
        B.duhamelLowerEnvelope,
      B.pdeHandoff.reciprocal_budget_of_section
        B.sectionIncidence.event_reciprocal_prefix_le_effective_budget,
      B.pdeHandoff.overlap_adjusted_effective_multiplicity_of_section
        B.pdeHandoff.overlap_tax_paid,
      B.pdeHandoff.finite_cauchy_duality_of_precertificate
        B.precertificate.duality,
      B.pdeHandoff.shell_multiplicity_lift_of_section
        B.pdeHandoff.no_shell_only_budget_shortcut_paid,
      hrawLpBony,
      hsuperSqrt,
      hfractionalLog,
      hreserveGain,
      hmatrixReserveGain,
      hsetupLatency,
      hdynamicLatency,
      hsmoothLatency,
      hconcreteFourier⟩

/-- Event multiplicity lift projected from the section-incidence source. -/
def GP216EventRecurrenceSourceBundle.multiplicityLift
    (B : GP216EventRecurrenceSourceBundle) :
    EventMultiplicityAdjustedReciprocalLift B.ledger :=
  multiplicity_lift_of_event_section_incidence
    B.ledger
    B.sectionIncidence

/-- Event pre-certificate regenerated from the GP216 Duhamel/Bernstein lower
envelope source.

This prevents the final event certificate from relying on a detached raw
lower-envelope field when a Duhamel/Bernstein source has been declared. -/
def GP216EventRecurrenceSourceBundle.duhamelPrecertificate
    (B : GP216EventRecurrenceSourceBundle) :
    EventDynamicRecurrencePricePrecertificate B.ledger where
  event_weight_positive := B.precertificate.event_weight_positive
  event_prices_declared_before_payoff :=
    B.precertificate.event_prices_declared_before_payoff
  event_prices_declared_before_payoff_paid :=
    B.precertificate.event_prices_declared_before_payoff_paid
  event_prices_not_backfit_from_realized_gain_or_payoff :=
    B.precertificate.event_prices_not_backfit_from_realized_gain_or_payoff
  event_prices_not_backfit_from_realized_gain_or_payoff_paid :=
    B.precertificate.event_prices_not_backfit_from_realized_gain_or_payoff_paid
  price_budget_nonnegative := B.precertificate.price_budget_nonnegative
  raw_recurrence_lower_envelope :=
    raw_recurrence_lower_envelope_of_event_duhamel_bernstein
      B.ledger
      B.duhamelLowerEnvelope
  raw_recurrence_prefix_le_budget :=
    B.precertificate.raw_recurrence_prefix_le_budget
  duality := B.precertificate.duality

/-- Source-level dynamic recurrence precertificate for the GP216 event bundle.

The Duhamel/Bernstein lower envelope remains visible in this source object,
so downstream event-gain divergence proofs route through the same lower
envelope and section-incidence receipts carried by the bundle. -/
def GP216EventRecurrenceSourceBundle.duhamelPrecertificateSource
    (B : GP216EventRecurrenceSourceBundle) :
    EventDynamicRecurrencePricePrecertificateSource B.ledger where
  event_weight_positive := B.precertificate.event_weight_positive
  event_prices_declared_before_payoff :=
    B.precertificate.event_prices_declared_before_payoff
  event_prices_declared_before_payoff_paid :=
    B.precertificate.event_prices_declared_before_payoff_paid
  event_prices_not_backfit_from_realized_gain_or_payoff :=
    B.precertificate.event_prices_not_backfit_from_realized_gain_or_payoff
  event_prices_not_backfit_from_realized_gain_or_payoff_paid :=
    B.precertificate.event_prices_not_backfit_from_realized_gain_or_payoff_paid
  price_budget_nonnegative := B.precertificate.price_budget_nonnegative
  duhamel_lower_envelope := B.duhamelLowerEnvelope
  raw_recurrence_prefix_le_budget :=
    B.precertificate.raw_recurrence_prefix_le_budget
  duality := B.precertificate.duality

/-- Full event-recurrence certificate derived from the pre-certificate and the
section-incidence multiplicity lift. -/
def GP216EventRecurrenceSourceBundle.certificate
    (B : GP216EventRecurrenceSourceBundle) :
    EventDynamicRecurrencePriceCertificate B.ledger :=
  event_price_bridge_of_precertificate_and_multiplicity_lift
    B.ledger
    B.duhamelPrecertificate
    B.multiplicityLift
    B.reciprocalBudget_matches_sectionIncidence

/-- The GP216 event source bundle rules out divergent event-gain prefixes
through the Duhamel lower-envelope and section-incidence sources it carries. -/
theorem GP216EventRecurrenceSourceBundle.noDivergentEventGainPrefix
    (B : GP216EventRecurrenceSourceBundle) :
    ¬ EventGainPrefixDiverges B.ledger :=
  no_divergent_event_gain_prefix_of_duhamel_source_and_section_incidence
    B.ledger
    B.duhamelPrecertificateSource
    B.sectionIncidence
    B.reciprocalBudget_matches_sectionIncidence

/-- Falsifier for an event-recurrence source bundle whose ledger reciprocal
budget is not the one measured by the section-incidence receipt. -/
structure GP216EventRecurrenceSectionIncidenceMismatchFalsifier
    (B : GP216EventRecurrenceSourceBundle) where
  reciprocal_budget_mismatch :
    B.ledger.reciprocalBudget ≠
      B.sectionIncidence.eventReciprocalBudget

/-- The event-recurrence source bundle carries the reciprocal-budget identity
used by the multiplicity lift, so section-incidence mismatch cannot survive.
-/
theorem no_gp216_event_recurrence_section_incidence_mismatch_falsifier
    (B : GP216EventRecurrenceSourceBundle)
    (F : GP216EventRecurrenceSectionIncidenceMismatchFalsifier B) :
    False :=
  F.reciprocal_budget_mismatch
    B.reciprocalBudget_matches_sectionIncidence

/-- Source handoff from the flat-torus clock branch to the phase-capacity
inequality used by GP216.

The final capacity inequality is still an analytic/PDE field.  The surrounding
paid fields make the required source commitments explicit: fixed flat-torus
phase symbols, identification of phase reach with the low-high/Killing clock,
and charging of the macroscopic clock in the Track B reserve ledger. -/
structure GP216FlatTorusPhaseCapacityHandoff
    (P : PhaseLatencyLipschitzCapacitySource)
    (K : FlatTorusKillingModeConclusion)
    (O : FlatTorusLowHighKinematicPDEObligation) where
  fixed_flat_torus_phase_symbol_topology : Prop
  fixed_flat_torus_phase_symbol_topology_paid :
    fixed_flat_torus_phase_symbol_topology
  phase_reach_identified_with_killing_clock : Prop
  phase_reach_identified_with_killing_clock_paid :
    phase_reach_identified_with_killing_clock
  macroscopic_clock_budget_charged_in_trackb_reserve : Prop
  macroscopic_clock_budget_charged_in_trackb_reserve_paid :
    macroscopic_clock_budget_charged_in_trackb_reserve
  capacity_of_flat_torus_sources :
    fixed_flat_torus_phase_symbol_topology →
      phase_reach_identified_with_killing_clock →
        macroscopic_clock_budget_charged_in_trackb_reserve →
          K.shell_transfer_requires_nonzero_strain →
            O.nonconstant_shell_transfer_forces_positive_deformation →
              O.positive_deformation_charged_by_reserve_loss →
                O.reserve_loss_charged_in_trackb_price →
                  ∀ j : ℕ,
                    P.phase.reach j * P.phase.kNorm j ≤
                      P.phase.gramianConstant

/-- Falsifiers for a flat-torus phase-capacity handoff with missing source
provenance. -/
inductive GP216FlatTorusPhaseCapacityHandoffFalsifier
    {P : PhaseLatencyLipschitzCapacitySource}
    {K : FlatTorusKillingModeConclusion}
    {O : FlatTorusLowHighKinematicPDEObligation}
    (H : GP216FlatTorusPhaseCapacityHandoff P K O) : Type where
  | phase_symbol_topology_missing :
      ¬ H.fixed_flat_torus_phase_symbol_topology →
        GP216FlatTorusPhaseCapacityHandoffFalsifier H
  | phase_reach_not_identified_with_killing_clock :
      ¬ H.phase_reach_identified_with_killing_clock →
        GP216FlatTorusPhaseCapacityHandoffFalsifier H
  | macroscopic_clock_not_charged_in_reserve :
      ¬ H.macroscopic_clock_budget_charged_in_trackb_reserve →
        GP216FlatTorusPhaseCapacityHandoffFalsifier H

/-- A paid flat-torus phase-capacity handoff excludes missing-source
provenance falsifiers. -/
theorem no_gp216_flat_torus_phase_capacity_handoff_falsifier
    {P : PhaseLatencyLipschitzCapacitySource}
    {K : FlatTorusKillingModeConclusion}
    {O : FlatTorusLowHighKinematicPDEObligation}
    (H : GP216FlatTorusPhaseCapacityHandoff P K O)
    (F : GP216FlatTorusPhaseCapacityHandoffFalsifier H) :
    False := by
  cases F with
  | phase_symbol_topology_missing h =>
      exact h H.fixed_flat_torus_phase_symbol_topology_paid
  | phase_reach_not_identified_with_killing_clock h =>
      exact h H.phase_reach_identified_with_killing_clock_paid
  | macroscopic_clock_not_charged_in_reserve h =>
      exact h H.macroscopic_clock_budget_charged_in_trackb_reserve_paid

/-- Macroscopic flat-torus clock source for the phase-capacity handoff.

This is the theory-builder source object behind the flat-torus
symmetry-breaker: the Duhamel/Bernstein viscous shell guard, the Killing-mode
adapter, and the Track B reserve-budget charge are carried together before
the GP216 phase-capacity handoff is constructed.  The hard PDE content remains
the final `capacity_of_macroscopic_clock_sources` field; this object only
prevents that capacity from being supplied as a detached scalar inequality. -/
structure MacroscopicFlatTorusClockSource
    (P : PhaseLatencyLipschitzCapacitySource) where
  duhamelReceipt : LowHighDuhamelBernsteinReceipt
  viscousShellGuard :
    LowHighDuhamelViscousShellGuard duhamelReceipt
  killingMode : FlatTorusKillingModeConclusion
  lowHighPDE : FlatTorusLowHighKinematicPDEObligation
  adapter :
    FlatTorusKillingModePDEAdapter lowHighPDE killingMode
  fixed_flat_torus_phase_symbol_topology : Prop
  fixed_flat_torus_phase_symbol_topology_paid :
    fixed_flat_torus_phase_symbol_topology
  phase_reach_identified_with_viscous_killing_clock : Prop
  phase_reach_identified_with_viscous_killing_clock_paid :
    phase_reach_identified_with_viscous_killing_clock
  macroscopic_clock_budget_charged_in_trackb_reserve : Prop
  macroscopic_clock_budget_charged_in_trackb_reserve_paid :
    macroscopic_clock_budget_charged_in_trackb_reserve
  capacity_of_macroscopic_clock_sources :
    fixed_flat_torus_phase_symbol_topology →
      phase_reach_identified_with_viscous_killing_clock →
        macroscopic_clock_budget_charged_in_trackb_reserve →
          LowHighDuhamelViscousShellGuard duhamelReceipt →
            killingMode.shell_transfer_requires_nonzero_strain →
              lowHighPDE.nonconstant_shell_transfer_forces_positive_deformation →
                lowHighPDE.positive_deformation_charged_by_reserve_loss →
                  lowHighPDE.reserve_loss_charged_in_trackb_price →
                    ∀ j : ℕ,
                      P.phase.reach j * P.phase.kNorm j ≤
                        P.phase.gramianConstant

/-- A macroscopic clock source constructs the GP216 phase-capacity handoff.

This is intentionally one-way: downstream consumers see the existing handoff
interface, while upstream PDE work must instantiate the stronger source object
with the Duhamel/viscous-shell guard still attached. -/
def MacroscopicFlatTorusClockSource.toPhaseCapacityHandoff
    {P : PhaseLatencyLipschitzCapacitySource}
    (M : MacroscopicFlatTorusClockSource P) :
    GP216FlatTorusPhaseCapacityHandoff
      P M.killingMode M.lowHighPDE where
  fixed_flat_torus_phase_symbol_topology :=
    M.fixed_flat_torus_phase_symbol_topology
  fixed_flat_torus_phase_symbol_topology_paid :=
    M.fixed_flat_torus_phase_symbol_topology_paid
  phase_reach_identified_with_killing_clock :=
    M.phase_reach_identified_with_viscous_killing_clock
  phase_reach_identified_with_killing_clock_paid :=
    M.phase_reach_identified_with_viscous_killing_clock_paid
  macroscopic_clock_budget_charged_in_trackb_reserve :=
    M.macroscopic_clock_budget_charged_in_trackb_reserve
  macroscopic_clock_budget_charged_in_trackb_reserve_paid :=
    M.macroscopic_clock_budget_charged_in_trackb_reserve_paid
  capacity_of_flat_torus_sources := by
    intro htop hclock hbudget hshell hnonconstant hpositive hreserve j
    exact
      M.capacity_of_macroscopic_clock_sources
        htop
        hclock
        hbudget
        M.viscousShellGuard
        hshell
        hnonconstant
        hpositive
        hreserve
        j

/-- Falsifier surface for a macroscopic clock source whose PDE provenance is
missing before it constructs the GP216 phase-capacity handoff. -/
inductive MacroscopicFlatTorusClockSourceFalsifier
    {P : PhaseLatencyLipschitzCapacitySource}
    (M : MacroscopicFlatTorusClockSource P) : Type where
  | phase_symbol_topology_missing :
      ¬ M.fixed_flat_torus_phase_symbol_topology →
        MacroscopicFlatTorusClockSourceFalsifier M
  | phase_reach_not_identified_with_viscous_killing_clock :
      ¬ M.phase_reach_identified_with_viscous_killing_clock →
        MacroscopicFlatTorusClockSourceFalsifier M
  | macroscopic_clock_not_charged_in_reserve :
      ¬ M.macroscopic_clock_budget_charged_in_trackb_reserve →
        MacroscopicFlatTorusClockSourceFalsifier M

/-- A paid macroscopic flat-torus clock source excludes its own provenance
falsifiers. -/
theorem no_macroscopic_flat_torus_clock_source_falsifier
    {P : PhaseLatencyLipschitzCapacitySource}
    (M : MacroscopicFlatTorusClockSource P)
    (F : MacroscopicFlatTorusClockSourceFalsifier M) :
    False := by
  cases F with
  | phase_symbol_topology_missing h =>
      exact h M.fixed_flat_torus_phase_symbol_topology_paid
  | phase_reach_not_identified_with_viscous_killing_clock h =>
      exact h M.phase_reach_identified_with_viscous_killing_clock_paid
  | macroscopic_clock_not_charged_in_reserve h =>
      exact h M.macroscopic_clock_budget_charged_in_trackb_reserve_paid

/-- GP216 flat-torus clock / phase-capacity bundle.

This packages the finite flat-torus Killing obstruction with the continuum
low-high PDE obligation and the phase-capacity handoff it feeds.  The bundle is
the anti-parabolic-rescaling guard: a closure cannot use a phase-latency
capacity inequality while treating the torus symmetry-breaker as a detachable
side assumption. -/
structure GP216FlatTorusPhaseCapacitySourceBundle
    (P : PhaseLatencyLipschitzCapacitySource) where
  killingMode : FlatTorusKillingModeConclusion
  lowHighPDE : FlatTorusLowHighKinematicPDEObligation
  adapter :
    FlatTorusKillingModePDEAdapter lowHighPDE killingMode
  phaseCapacityHandoff :
    GP216FlatTorusPhaseCapacityHandoff P killingMode lowHighPDE

/-- Build the GP216 flat-torus phase-capacity source bundle from the stronger
macroscopic clock source. -/
def GP216FlatTorusPhaseCapacitySourceBundle.ofMacroscopicClockSource
    {P : PhaseLatencyLipschitzCapacitySource}
    (M : MacroscopicFlatTorusClockSource P) :
    GP216FlatTorusPhaseCapacitySourceBundle P where
  killingMode := M.killingMode
  lowHighPDE := M.lowHighPDE
  adapter := M.adapter
  phaseCapacityHandoff :=
    M.toPhaseCapacityHandoff

/-- Source facts paid by a macroscopic flat-torus clock source before the
GP216 bundle forgets the Duhamel/viscous-shell provenance.

This is a provenance bridge, not a new estimate: the existing
Killing/PDE adapter still supplies the source facts consumed by phase
capacity. -/
def MacroscopicFlatTorusClockSource.flatTorusPhaseCapacitySourcesPaid
    {P : PhaseLatencyLipschitzCapacitySource}
    (M : MacroscopicFlatTorusClockSource P) :
    M.killingMode.shell_transfer_requires_nonzero_strain ∧
      M.lowHighPDE.nonconstant_shell_transfer_forces_positive_deformation ∧
        M.lowHighPDE.positive_deformation_charged_by_reserve_loss ∧
          M.lowHighPDE.reserve_loss_charged_in_trackb_price :=
  flat_torus_phase_capacity_sources_of_killing_mode_adapter
    M.lowHighPDE
    M.killingMode
    M.adapter

/-- The macroscopic flat-torus clock source carries a paid satisfaction
receipt for its low-high PDE obligation; only the phase-capacity estimate
remains as the hard clock field. -/
def MacroscopicFlatTorusClockSource.flatTorusLowHighPDESatisfied
    {P : PhaseLatencyLipschitzCapacitySource}
    (M : MacroscopicFlatTorusClockSource P) :
    FlatTorusLowHighKinematicPDEObligationSatisfied M.lowHighPDE :=
  flat_torus_low_high_pde_satisfied_of_killing_mode_adapter
    M.lowHighPDE
    M.killingMode
    M.adapter

/-- Direct phase-capacity form for the macroscopic clock source.

This exposes the non-detached route: Duhamel/viscous shell provenance feeds the
flat-torus Killing/PDE adapter, which feeds the same phase-capacity handoff
used by GP216. -/
theorem phase_capacity_of_macroscopic_flat_torus_clock_source
    {P : PhaseLatencyLipschitzCapacitySource}
    (M : MacroscopicFlatTorusClockSource P) :
    ∀ j : ℕ,
      P.phase.reach j * P.phase.kNorm j ≤
        P.phase.gramianConstant := by
  rcases M.flatTorusPhaseCapacitySourcesPaid with
    ⟨hshell, hdeformation, hreserveLoss, htrackBPrice⟩
  exact
    M.toPhaseCapacityHandoff.capacity_of_flat_torus_sources
      M.toPhaseCapacityHandoff.fixed_flat_torus_phase_symbol_topology_paid
      M.toPhaseCapacityHandoff.phase_reach_identified_with_killing_clock_paid
      M.toPhaseCapacityHandoff.macroscopic_clock_budget_charged_in_trackb_reserve_paid
      hshell
      hdeformation
      hreserveLoss
      htrackBPrice

/-- Build the macroscopic flat-torus clock source from the typed audited
LP/Bony-Lipschitz reserve route.

This is the constructor GP216 closure attempts should target when the torus
symmetry-breaker is paid by a concrete low-high LP/Bony reserve link.  It
derives the flat-torus PDE obligation and Killing-mode adapter from the same
typed source.  The phase-capacity inequality itself is not requested a second
time here: it is exactly the `parabolic_low_high_capacity` field of the carried
fixed-topology `PhaseLatencyControlGramianReceipt`. -/
def macroscopic_flat_torus_clock_source_of_typed_audited_lipschitz_reserve_source
    {P : PhaseLatencyLipschitzCapacitySource}
    (duhamelReceipt : LowHighDuhamelBernsteinReceipt)
    (viscousShellGuard :
      LowHighDuhamelViscousShellGuard duhamelReceipt)
    (K : FlatTorusKillingModeConclusion)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (provenance : FlatTorusKillingModeProvenance K)
    (lp_bony_constant_declared_before_payoff_paid :
      R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      R.high_shell_energy_declared_before_payoff)
    (fixed_flat_torus_phase_symbol_topology : Prop)
    (fixed_flat_torus_phase_symbol_topology_paid :
      fixed_flat_torus_phase_symbol_topology)
    (phase_reach_identified_with_viscous_killing_clock : Prop)
    (phase_reach_identified_with_viscous_killing_clock_paid :
      phase_reach_identified_with_viscous_killing_clock)
    (macroscopic_clock_budget_charged_in_trackb_reserve : Prop)
    (macroscopic_clock_budget_charged_in_trackb_reserve_paid :
      macroscopic_clock_budget_charged_in_trackb_reserve) :
    MacroscopicFlatTorusClockSource P where
  duhamelReceipt := duhamelReceipt
  viscousShellGuard := viscousShellGuard
  killingMode := K
  lowHighPDE :=
    flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
      K L R
  adapter :=
    flat_torus_killing_pde_adapter_of_typed_audited_lipschitz_reserve_source
      K L R G Cert n link hnosurvivor provenance
      lp_bony_constant_declared_before_payoff_paid
      lipschitz_cost_declared_before_payoff_paid
      high_shell_energy_declared_before_payoff_paid
  fixed_flat_torus_phase_symbol_topology :=
    fixed_flat_torus_phase_symbol_topology
  fixed_flat_torus_phase_symbol_topology_paid :=
    fixed_flat_torus_phase_symbol_topology_paid
  phase_reach_identified_with_viscous_killing_clock :=
    phase_reach_identified_with_viscous_killing_clock
  phase_reach_identified_with_viscous_killing_clock_paid :=
    phase_reach_identified_with_viscous_killing_clock_paid
  macroscopic_clock_budget_charged_in_trackb_reserve :=
    macroscopic_clock_budget_charged_in_trackb_reserve
  macroscopic_clock_budget_charged_in_trackb_reserve_paid :=
    macroscopic_clock_budget_charged_in_trackb_reserve_paid
  capacity_of_macroscopic_clock_sources := by
    intro htop hclock hbudget hguard hshell hdeformation hreserve hprice j
    exact P.phase.parabolic_low_high_capacity j

/-- Source-first version of the macroscopic flat-torus clock constructor.

This is the preferred route when the flat-torus symmetry breaker has been paid
by a `FlatTorusSmoothKillingFourierSource`: the finite Fourier payload proves
the zero-strain rigidity edge, while the typed LP/Bony reserve source pays the
low-high deformation/reserve charging edges. -/
def macroscopic_flat_torus_clock_source_of_smooth_fourier_and_typed_audited_lipschitz_reserve
    {P : PhaseLatencyLipschitzCapacitySource}
    (duhamelReceipt : LowHighDuhamelBernsteinReceipt)
    (viscousShellGuard :
      LowHighDuhamelViscousShellGuard duhamelReceipt)
    (S : FlatTorusSmoothKillingFourierSource)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyUnpaidEstimateReceipt L)
    (G : LowFrequencyLipschitzLedger)
    (Cert : LowFrequencyLipschitzAuditedControlCertificate G)
    (n : ℕ)
    (link : LowHighLipschitzReserveLink L R G n)
    (hnosurvivor : FullLedgerNoSurvivor (G.block n))
    (lp_bony_constant_declared_before_payoff_paid :
      R.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      R.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      R.high_shell_energy_declared_before_payoff)
    (fixed_flat_torus_phase_symbol_topology : Prop)
    (fixed_flat_torus_phase_symbol_topology_paid :
      fixed_flat_torus_phase_symbol_topology)
    (phase_reach_identified_with_viscous_killing_clock : Prop)
    (phase_reach_identified_with_viscous_killing_clock_paid :
      phase_reach_identified_with_viscous_killing_clock)
    (macroscopic_clock_budget_charged_in_trackb_reserve : Prop)
    (macroscopic_clock_budget_charged_in_trackb_reserve_paid :
      macroscopic_clock_budget_charged_in_trackb_reserve) :
    MacroscopicFlatTorusClockSource P where
  duhamelReceipt := duhamelReceipt
  viscousShellGuard := viscousShellGuard
  killingMode := S.toConclusion
  lowHighPDE :=
    flat_torus_low_high_pde_obligation_of_lipschitz_reserve_source
      S.toConclusion L R
  adapter :=
    flat_torus_killing_pde_adapter_of_smooth_fourier_source_and_typed_audited_lipschitz_reserve
      S L R G Cert n link hnosurvivor
      lp_bony_constant_declared_before_payoff_paid
      lipschitz_cost_declared_before_payoff_paid
      high_shell_energy_declared_before_payoff_paid
  fixed_flat_torus_phase_symbol_topology :=
    fixed_flat_torus_phase_symbol_topology
  fixed_flat_torus_phase_symbol_topology_paid :=
    fixed_flat_torus_phase_symbol_topology_paid
  phase_reach_identified_with_viscous_killing_clock :=
    phase_reach_identified_with_viscous_killing_clock
  phase_reach_identified_with_viscous_killing_clock_paid :=
    phase_reach_identified_with_viscous_killing_clock_paid
  macroscopic_clock_budget_charged_in_trackb_reserve :=
    macroscopic_clock_budget_charged_in_trackb_reserve
  macroscopic_clock_budget_charged_in_trackb_reserve_paid :=
    macroscopic_clock_budget_charged_in_trackb_reserve_paid
  capacity_of_macroscopic_clock_sources := by
    intro htop hclock hbudget hguard hshell hdeformation hreserve hprice j
    exact P.phase.parabolic_low_high_capacity j

/-- GP216 continuation source bundle.

The continuation theorem needs the concrete Track B handoff together with the
smoothness and finite-energy hypotheses for the generated profile/Lipschitz
evolution.  The self-tax continuation prerequisites are then derived through
the same-PDE handoff, so a closure cannot start continuation from a detached
self-tax evolution. -/
structure GP216ContinuationSourceBundle where
  handoff : TrackBContinuationHandoffReceipt
  profile_smooth :
    (handoff.profile_lipschitz.evolution_of_initial_data
      handoff.initialData).smoothOnLocalInterval
  profile_energy :
    (handoff.profile_lipschitz.evolution_of_initial_data
      handoff.initialData).finiteEnergyInequality

/-- GP216 high-high self-tax PDE source bundle.

The high-high branch exposes a PDE/SOS duty checklist and a paid satisfaction
receipt.  They move together; otherwise the final bridge could swap the
obligation after proving its branch-wise guard facts. -/
structure GP216HighHighSelfTaxPDESourceBundle where
  obligation : HighHighSelfTaxPDEObligation
  fixed_high_high_lp_bony_topology :
    obligation.fixed_high_high_lp_bony_topology
  same_leray_output_ledger_declared_before_payoff :
    obligation.same_leray_output_ledger_declared_before_payoff
  self_tax_nonnegative_for_global_high_high_blocks :
    obligation.self_tax_nonnegative_for_global_high_high_blocks
  null_self_tax_above_wall_cap_proved :
    obligation.null_self_tax_above_wall_cap_proved
  cross_aware_root_allowance_or_sos_receipt_proved :
    obligation.cross_aware_root_allowance_or_sos_receipt_proved
  cauchy_saturating_bad_ledger_falsifier_addressed :
    obligation.cauchy_saturating_bad_ledger_falsifier_addressed
  resonant_wall_case_not_promoted_above_wall :
    obligation.resonant_wall_case_not_promoted_above_wall
  smooth_profile_limit_preserves_high_high_receipt :
    obligation.smooth_profile_limit_preserves_high_high_receipt
  no_posthoc_phase_shell_or_observable_choice :
    obligation.no_posthoc_phase_shell_or_observable_choice

/-- GP216 high-high PDE satisfaction is derived from the explicit high-high
PDE duty fields, while the two closed arithmetic boundary surfaces are filled
by the high-high module's proved scalar receipts. -/
def GP216HighHighSelfTaxPDESourceBundle.satisfied
    (B : GP216HighHighSelfTaxPDESourceBundle) :
    HighHighSelfTaxPDEObligationSatisfied B.obligation :=
  high_high_self_tax_pde_obligation_satisfied_of_pde_duties
    B.obligation
    B.fixed_high_high_lp_bony_topology
    B.same_leray_output_ledger_declared_before_payoff
    B.self_tax_nonnegative_for_global_high_high_blocks
    B.null_self_tax_above_wall_cap_proved
    B.cross_aware_root_allowance_or_sos_receipt_proved
    B.cauchy_saturating_bad_ledger_falsifier_addressed
    B.resonant_wall_case_not_promoted_above_wall
    B.smooth_profile_limit_preserves_high_high_receipt
    B.no_posthoc_phase_shell_or_observable_choice

/-- GP216 low-high Lipschitz reserve PDE source bundle.

The low-high PDE checklist and the generated energy-budget reserve closure are
both tied to the concrete continuation handoff.  This bundle keeps the
LP/Bony-duty satisfaction and generated shell-reserve closure on the same
profile/Lipschitz ledger. -/
structure GP216LowHighReservePDESourceBundle
    (H : TrackBContinuationHandoffReceipt) where
  obligation : LowHighLipschitzReservePDEObligation
  energyBudgetShellReserveClosure :
    LowHighEnergyBudgetShellReserveClosure
      (trackBGeneratedLowFrequencyLipschitzLedger
        H.profile_lipschitz
        H.initialData)
  energyBudgetPDEHandoff :
    LowHighEnergyBudgetShellReservePDEHandoff
      obligation
      (trackBGeneratedLowFrequencyLipschitzLedger
        H.profile_lipschitz
        H.initialData)
      energyBudgetShellReserveClosure

/-- Build the GP216 low-high reserve source bundle from the typed shell-reserve
PDE handoff.

This is only a source-shape adapter: the load-bearing PDE object remains
`LowHighEnergyBudgetShellReservePDEHandoff` for the generated
profile/Lipschitz ledger. -/
def GP216LowHighReservePDESourceBundle.ofEnergyBudgetShellPDEHandoff
    (H : TrackBContinuationHandoffReceipt)
    (obligation : LowHighLipschitzReservePDEObligation)
    (energyBudgetShellReserveClosure :
      LowHighEnergyBudgetShellReserveClosure
        (trackBGeneratedLowFrequencyLipschitzLedger
          H.profile_lipschitz
          H.initialData))
    (energyBudgetPDEHandoff :
      LowHighEnergyBudgetShellReservePDEHandoff
        obligation
        (trackBGeneratedLowFrequencyLipschitzLedger
          H.profile_lipschitz
          H.initialData)
        energyBudgetShellReserveClosure) :
    GP216LowHighReservePDESourceBundle H where
  obligation := obligation
  energyBudgetShellReserveClosure := energyBudgetShellReserveClosure
  energyBudgetPDEHandoff := energyBudgetPDEHandoff

/-- GP216 low-high PDE duties that are paid before importing generated-block
no-survivor pricing.

This projection is the source-first audit surface for the low-high reserve
bundle.  It deliberately stops short of
`LowHighLipschitzReservePDEObligationSatisfied`, because the latter also needs
the no-survivor-priced leakage/no-arbitrage fields. -/
def GP216LowHighReservePDESourceBundle.preNoSurvivorSatisfied
    {H : TrackBContinuationHandoffReceipt}
    (B : GP216LowHighReservePDESourceBundle H) :
    LowHighLipschitzReservePDEPreNoSurvivorSatisfied B.obligation :=
  low_high_lipschitz_reserve_pde_pre_no_survivor_satisfied_of_energy_budget_shell_closure
    B.obligation
    (trackBGeneratedLowFrequencyLipschitzLedger
      H.profile_lipschitz
      H.initialData)
    B.energyBudgetShellReserveClosure
    B.energyBudgetPDEHandoff

/-- GP216 low-high PDE satisfaction is derived from the shell-reserve closure
and its semantic handoff, not stored beside the closure as an independent
receipt. -/
def GP216LowHighReservePDESourceBundle.satisfied
    {H : TrackBContinuationHandoffReceipt}
    (B : GP216LowHighReservePDESourceBundle H) :
    LowHighLipschitzReservePDEObligationSatisfied B.obligation :=
  low_high_lipschitz_reserve_pde_obligation_satisfied_of_audited_energy_budget_shell_closure
    B.obligation
    (trackBGeneratedLowFrequencyLipschitzLedger
      H.profile_lipschitz
      H.initialData)
    (trackBGeneratedLowFrequencyLipschitzAuditedCertificate
      H.profile_lipschitz
      H.initialData)
    B.energyBudgetShellReserveClosure
    (generated_lipschitz_blocks_no_survivor_of_trackB_profile_closure
      H.profile_lipschitz
      H.initialData)
    B.energyBudgetPDEHandoff

/-- Typed no-backfit receipt for the declared continuum target.

This replaces the loose GP216 field pair
`declaredTargetNotBackfitAfterPayoff : Prop` /
`declaredTargetNotBackfitAfterPayoffPaid` with a source-shaped object tied to
the particular continuum stream whose target convergence is consumed. -/
structure GP216DeclaredContinuumTargetReceipt
    {τ : ContinuumLPProfileTopology.{v}}
    (stream : ContinuumLPPrefixPriceStream τ) where
  declaredTargetNotBackfitAfterPayoff : Prop
  declaredTargetNotBackfitAfterPayoffPaid :
    declaredTargetNotBackfitAfterPayoff

/-- Falsifier for a declared continuum target receipt whose no-backfit guard
is absent. -/
structure GP216DeclaredContinuumTargetReceiptFalsifier
    {τ : ContinuumLPProfileTopology.{v}}
    {stream : ContinuumLPPrefixPriceStream τ}
    (R : GP216DeclaredContinuumTargetReceipt stream) where
  targetBackfitAfterPayoff :
    ¬ R.declaredTargetNotBackfitAfterPayoff

/-- A typed declared-target receipt excludes the missing no-backfit branch. -/
theorem no_gp216_declared_continuum_target_receipt_falsifier
    {τ : ContinuumLPProfileTopology.{v}}
    {stream : ContinuumLPPrefixPriceStream τ}
    (R : GP216DeclaredContinuumTargetReceipt stream)
    (F : GP216DeclaredContinuumTargetReceiptFalsifier R) :
    False :=
  F.targetBackfitAfterPayoff R.declaredTargetNotBackfitAfterPayoffPaid

/-- GP216 continuum all-output source bundle.

The continuum LP/Bony topology, prefix stream, declared-target convergence,
and the self-tax/event recurrence couplings are one same-topology limit-passage
object.  The countable Cauchy tail receipt is derived from target convergence,
so the final bridge cannot prove tail control in one all-output topology while
transporting self-tax or event prices through a different stream. -/
structure GP216ContinuumAllOutputSourceBundle.{v}
    (S : LeraySelfTaxProfilePriceStream)
    (E : EventRecurrencePriceLedger) where
  topology : ContinuumLPProfileTopology.{v}
  stream : ContinuumLPPrefixPriceStream topology
  fixedTopology : ContinuumLPUsesFixedTopology stream
  fixedAtoms : FixedAllOutputLPBonyAtoms stream
  prefixCharge : ∀ N : ℕ, PrefixAllOutputCoherenceCharge stream N
  prefixPriceTendsToDeclaredTarget :
    AllOutputPrefixPriceTendsToDeclaredTarget stream
  smoothBudgetBridge : ContinuumLPSmoothBudgetBridge stream
  declaredTargetReceipt :
    GP216DeclaredContinuumTargetReceipt stream
  selfTaxCoupling :
    LeraySelfTaxContinuumCoupling S stream
  eventCoupling :
    AllOutputEventRecurrenceCoupling stream E
  eventCoupling_fixed_atoms_matches_countable_tail :
    eventCoupling.fixed_atoms = fixedAtoms

/-- The GP216 continuum countable-tail control receipt is assembled from the
same all-output source bundle, deriving the Cauchy tail from convergence to
the declared target. -/
def GP216ContinuumAllOutputSourceBundle.countableTailControl
    {S : LeraySelfTaxProfilePriceStream}
    {E : EventRecurrencePriceLedger}
    (B : GP216ContinuumAllOutputSourceBundle S E) :
    AllOutputCountableGramTailControlReceipt B.stream :=
  all_output_countable_gram_tail_control_receipt_of_declared_target_convergence
    B.fixedTopology
    B.fixedAtoms
    B.prefixCharge
    B.prefixPriceTendsToDeclaredTarget
    B.smoothBudgetBridge
    B.declaredTargetReceipt.declaredTargetNotBackfitAfterPayoff
    B.declaredTargetReceipt.declaredTargetNotBackfitAfterPayoffPaid

/-- Falsifier for a continuum source bundle whose event-recurrence coupling
uses different all-output atoms than the countable-tail/Gram control receipt.

The final bridge uses `fixedAtoms` for countable tail control and
`eventCoupling.fixed_atoms` for event price transport.  This surface makes
that identity load-bearing. -/
structure GP216ContinuumAllOutputFixedAtomsProvenanceFalsifier
    {S : LeraySelfTaxProfilePriceStream}
    {E : EventRecurrencePriceLedger}
    (B : GP216ContinuumAllOutputSourceBundle S E) where
  atom_source_mismatch :
    B.eventCoupling.fixed_atoms ≠ B.countableTailControl.fixed_atoms

/-- A continuum all-output source bundle excludes atom-source mismatch between
event recurrence transport and countable-tail control. -/
theorem no_gp216_continuum_all_output_fixed_atoms_provenance_falsifier
    {S : LeraySelfTaxProfilePriceStream}
    {E : EventRecurrencePriceLedger}
    (B : GP216ContinuumAllOutputSourceBundle S E)
    (F : GP216ContinuumAllOutputFixedAtomsProvenanceFalsifier B) :
    False :=
  F.atom_source_mismatch <| by
    simpa [GP216ContinuumAllOutputSourceBundle.countableTailControl]
      using B.eventCoupling_fixed_atoms_matches_countable_tail

/-- Composite receipt for the GP-216/5IQ local bridge stack.

The fields are deliberately existing receipts or abstract branch assumptions:
this file only checks that the interfaces compose.  In particular, the
low-beat branch is represented by the existing finite-reserve obstruction:
a candidate that needs unbounded low-beat payoff prefixes cannot coexist with
a finite declared reserve limit. -/
structure GP216BridgeCompositionReceipt where
  declaredScope : Prop
  branchBlock : FullLedgerBlock
  branch_is_global : IsGlobalTrackBBlock branchBlock
  highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle
  selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle
  branchSelfTaxThresholdCoordinateIdentities :
    BranchSelfTaxThresholdCoordinateIdentities
      branchBlock
      selfTaxOutputSource.stream
  highHigh_same_output_ledger_matches_self_tax_stream :
    highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
      selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff
  coherenceSource : LPBeatBackscatterChargeStreamSource
  coherenceCertificate :
    LPBeatBackscatterLimitCertificate coherenceSource.stream
  lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle
  eventRecurrenceSource : GP216EventRecurrenceSourceBundle
  continuumSource :
    GP216ContinuumAllOutputSourceBundle
      selfTaxOutputSource.stream
      eventRecurrenceSource.ledger
  coordinateReformulation :
    TrackBCoordinateReformulationReceipt
  coordinate_source_is_branch :
    coordinateReformulation.source = branchBlock
  continuationSource : GP216ContinuationSourceBundle
  profileLipschitzBranchIndex : ℕ
  branch_matches_profile_lipschitz_generated_block :
    branchBlock =
      (trackBGeneratedLowFrequencyLipschitzLedger
        continuationSource.handoff.profile_lipschitz
        continuationSource.handoff.initialData).block
        profileLipschitzBranchIndex
  branch_profile_family_self_tax_stream_declared_together : Prop
  branch_profile_family_self_tax_stream_declared_together_paid :
    branch_profile_family_self_tax_stream_declared_together
  branch_profile_family_payoff_matches_self_tax_stream :
    familyPayoff
      (continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
        branchBlock) =
        selfTaxOutputSource.stream.payoffLimit
  branch_profile_family_price_matches_self_tax_stream :
    familyPrice
      (continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
        branchBlock) =
        leraySelfTaxLimitPrice selfTaxOutputSource.stream
  lowHighReservePDESource :
    GP216LowHighReservePDESourceBundle
      continuationSource.handoff
  phaseLatencyProfileReserveSource :
    PhaseLatencyProfileLipschitzReserveSource
      continuationSource.handoff.profile_lipschitz
      continuationSource.handoff.initialData
  phaseLatencyConcreteFourierSymbol :
    ConcreteFourierLatencySymbolReceipt
      (trackBGeneratedLowFrequencyLipschitzLedger
        continuationSource.handoff.profile_lipschitz
        continuationSource.handoff.initialData)
  phaseLatencyControlBudget_matches_required_lipschitz :
    ∀ n : ℕ,
      phaseLatencyProfileReserveSource.phase.controlBudget n =
        phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n
  macroscopicFlatTorusClockSource :
    MacroscopicFlatTorusClockSource
      (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
        continuationSource.handoff.profile_lipschitz
        continuationSource.handoff.initialData
        phaseLatencyProfileReserveSource.phase
        phaseLatencyConcreteFourierSymbol
        phaseLatencyControlBudget_matches_required_lipschitz
      ).toPhaseLatencyCapacitySource

/-- The generated GP216 branch block determined by the continuation handoff and
its profile/Lipschitz branch index.

Keeping this as a named projection lets constructors expose the final branch as
generated-by-construction, rather than as a detached `FullLedgerBlock` plus a
late equality proof. -/
def GP216GeneratedProfileLipschitzBranchBlock
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ) : FullLedgerBlock :=
  (trackBGeneratedLowFrequencyLipschitzLedger
    H.profile_lipschitz
    H.initialData).block n

/-- The selected projected continuum self-tax stream.

Naming this projection keeps later compactness objects tied to the branch-local
stream that the GP216 bridge actually consumes, instead of hiding the target
inside a family-level source. -/
def GP216ContinuumProjectedSelectedBranchStream
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n)) :
    LeraySelfTaxProfilePriceStream :=
  leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
    (source.all_output_source_of_global
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      branch_is_global)
    ((source.component_source_of_global
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      branch_is_global).split)

/-- Source object for the exact selected-branch stream identity.

This is the remaining branch-local analytic primitive after the continuum,
noncircular, and Phase 5FB projection routes have been exposed.  It does not
construct threshold coordinates by itself; it only says that the source-family
stream at the selected generated branch is the audited GP216 self-tax stream.
-/
structure GP216SelectedBranchSelfTaxStreamMatchSource
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream) where
  branch_is_global :
    IsGlobalTrackBBlock
      (GP216GeneratedProfileLipschitzBranchBlock H n)
  selected_branch_stream_matches_self_tax_output :
    stream_of_block
      (GP216GeneratedProfileLipschitzBranchBlock H n) =
        selfTaxOutputSource.stream

/-- Hostile surface for the selected-branch stream-match source.

Any candidate route that pays only same-topology, event recurrence, component
LSC, or Phase 5FB replay still fails if this selected branch stream mismatch is
present. -/
inductive GP216SelectedBranchSelfTaxStreamMatchFalsifier
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (_S :
      GP216SelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource stream_of_block) :
    Type where
  | selectedBranchStreamMismatch :
      stream_of_block
          (GP216GeneratedProfileLipschitzBranchBlock H n) ≠
        selfTaxOutputSource.stream →
      GP216SelectedBranchSelfTaxStreamMatchFalsifier _S

/-- A selected-branch stream-match source rules out its named mismatch. -/
theorem no_GP216SelectedBranchSelfTaxStreamMatchFalsifier
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (S :
      GP216SelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource stream_of_block)
    (F : GP216SelectedBranchSelfTaxStreamMatchFalsifier S) :
    False := by
  cases F with
  | selectedBranchStreamMismatch hbad =>
      exact hbad S.selected_branch_stream_matches_self_tax_output

/-- Selected-branch stream match projected from a global same-stream source.

This is intentionally marked as a too-strong adapter: it is useful for old
routes that already have a global stream match, but the current bridge should
prefer a source that pays only the selected branch. -/
def GP216SelectedBranchSelfTaxStreamMatchSource.ofGlobalStreamMatch
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (stream_matches_self_tax_output :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        stream_of_block B = selfTaxOutputSource.stream) :
    GP216SelectedBranchSelfTaxStreamMatchSource
      H n selfTaxOutputSource stream_of_block where
  branch_is_global := branch_is_global
  selected_branch_stream_matches_self_tax_output :=
    stream_matches_self_tax_output
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      branch_is_global

/-- Selected-branch stream match from a branch-local equality source. -/
def GP216SelectedBranchSelfTaxStreamMatchSource.ofSelectedBranchEquality
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (selected_branch_stream_matches_self_tax_output :
      stream_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n) =
          selfTaxOutputSource.stream) :
    GP216SelectedBranchSelfTaxStreamMatchSource
      H n selfTaxOutputSource stream_of_block where
  branch_is_global := branch_is_global
  selected_branch_stream_matches_self_tax_output :=
    selected_branch_stream_matches_self_tax_output

/-- Continuum all-output selected-branch stream match from the projected
continuum stream equality at the generated branch.

The required equality is now exactly the PDE-side object: the Leray self-tax
projection of the branch's continuum all-output source, using its component
split, must equal the audited GP216 self-tax stream. -/
def GP216SelectedBranchSelfTaxStreamMatchSource.ofContinuumProjectedSelectedBranchEquality
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (projected_branch_stream_matches_self_tax_output :
      leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        (source.all_output_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global)
        ((source.component_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global).split) =
          selfTaxOutputSource.stream) :
    GP216SelectedBranchSelfTaxStreamMatchSource
      H n selfTaxOutputSource source.stream_of_block where
  branch_is_global := branch_is_global
  selected_branch_stream_matches_self_tax_output := by
    rw [← source.projected_stream_matches_block
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      branch_is_global]
    exact projected_branch_stream_matches_self_tax_output

/-- Source object for the projected continuum equality at the selected generated
branch.

This is the non-reflexive form of the remaining source obligation: the PDE-side
continuum projection for the selected branch must equal the audited GP216
self-tax output stream. -/
structure GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchSource
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ) where
  branch_is_global :
    IsGlobalTrackBBlock
      (GP216GeneratedProfileLipschitzBranchBlock H n)
  projected_branch_stream_matches_self_tax_output :
    leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
      (source.all_output_source_of_global
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global)
      ((source.component_source_of_global
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global).split) =
      selfTaxOutputSource.stream

/-- Source object that audits the selected projected continuum stream itself.

This is the non-tautological way to make the selected projected-stream equality
definitional: the GP216 self-tax bundle is built from the projected stream, not
chosen independently and later identified with it.  The remaining PDE content is
the audited output-limit receipt for that projected stream. -/
structure GP216ContinuumProjectedSelectedBranchAuditedOutputSource
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ) where
  branch_is_global :
    IsGlobalTrackBBlock
      (GP216GeneratedProfileLipschitzBranchBlock H n)
  projected_audited_source :
    LeraySelfTaxOutputLimitPassageAuditedSourceReceipt
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        (source.all_output_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global)
        ((source.component_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global).split))

/-- Source object that pays the selected projected audited output receipt
through a measure-valued defect source with compactness provenance.

The continuum all-output source supplies the selected projection, component
assembly, finite-prefix charges, and constant payoff-prefix convergence.  The
new PDE payload is the measure-valued output-limit source for that same
projected stream plus a provenance certificate.  The extra provenance field
blocks the zero-defect/component-LSC repackaging route. -/
structure GP216ContinuumProjectedSelectedBranchMeasureValuedAuditedOutputSource
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ) where
  branch_is_global :
    IsGlobalTrackBBlock
      (GP216GeneratedProfileLipschitzBranchBlock H n)
  projected_measure_valued_source :
    LeraySelfTaxMeasureValuedOutputLimitSource
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        (source.all_output_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global)
        ((source.component_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global).split))
  projected_measure_valued_compactness_provenance :
    LeraySelfTaxMeasureValuedOutputCompactnessProvenance
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        (source.all_output_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global)
        ((source.component_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global).split))
      projected_measure_valued_source

/-- Source object that pays the selected projected measure-valued route with
compactness provenance.

This is the non-laundered endpoint for the residual-void objective.  It asks
for a compactness/provenance-bearing measure-valued source for the selected
projection, not just a bare measure-valued record that could be filled by
zero defects and component LSC. -/
structure GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ) where
  branch_is_global :
    IsGlobalTrackBBlock
      (GP216GeneratedProfileLipschitzBranchBlock H n)
  projected_compactness_measure_valued_source :
    LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        (source.all_output_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global)
        ((source.component_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global).split))

/-- A selected-family observable extracted from one component of the selected
projected stream.

This is the first subatom of the numeric-liminf source.  It prevents the
constant-observable route from entering the selected source: `q` must be the
selected prefix price for a declared component over the same approximation
family. -/
structure GP216SelectedFamilyObservableSource
    (ι : Type u)
    (approximation_index_to_prefix : ι → ℕ)
    (S : LeraySelfTaxProfilePriceStream)
    (component : LeraySelfTaxPriceComponent)
    (q : ι → Real) where
  observable_declared_before_payoff : Prop
  observable_declared_before_payoff_receipt :
    observable_declared_before_payoff
  q_matches_selected_prefix :
    ∀ a : ι,
      q a =
        S.prefixPriceForComponent component
          (approximation_index_to_prefix a)

/-- A generated liminf realization over one selected approximation family.

This is the second subatom of the numeric-liminf source.  It is separated from
observable extraction so Mathlib/filter lemmas can attack the tail-realization
problem without also paying selected-stream provenance. -/
structure GP216SelectedFamilyLiminfRealization
    (ι : Type u)
    (approximation_index_to_prefix : ι → ℕ)
    (q : ι → Real)
    (L : Real) where
  eventual_lower_bound :
    ∀ ε : Real, 0 < ε →
      ∃ N : ℕ, ∀ a : ι,
        N ≤ approximation_index_to_prefix a → L - ε ≤ q a
  tail_near_attainment :
    ∀ ε : Real, 0 < ε →
      ∀ N : ℕ, ∃ a : ι,
        N ≤ approximation_index_to_prefix a ∧ q a ≤ L + ε

/-- A generated liminf price over one declared approximation family.

This is a source-side certificate, not a scalar adapter.  The observable `q`
is evaluated on the same approximation family that later feeds the compactness
provenance; the two tail clauses are the finite Lean-facing shape of a liminf
statement. -/
structure GP216GeneratedLiminfPriceCertificate
    (ι : Type u)
    (approximation_index_to_prefix : ι → ℕ)
    (q : ι → Real)
    (L : Real) where
  observable_declared_before_payoff : Prop
  observable_declared_before_payoff_receipt :
    observable_declared_before_payoff
  eventual_lower_bound :
    ∀ ε : Real, 0 < ε →
      ∃ N : ℕ, ∀ a : ι,
        N ≤ approximation_index_to_prefix a → L - ε ≤ q a
  tail_near_attainment :
    ∀ ε : Real, 0 < ε →
      ∀ N : ℕ, ∃ a : ι,
        N ≤ approximation_index_to_prefix a ∧ q a ≤ L + ε

/-- Package selected observable extraction plus liminf realization into the
legacy generated certificate shape. -/
def GP216GeneratedLiminfPriceCertificate.ofSelectedFamilyRealization
    {ι : Type u}
    {approximation_index_to_prefix : ι → ℕ}
    {S : LeraySelfTaxProfilePriceStream}
    {component : LeraySelfTaxPriceComponent}
    {q : ι → Real}
    {L : Real}
    (O :
      GP216SelectedFamilyObservableSource
        ι approximation_index_to_prefix S component q)
    (R :
      GP216SelectedFamilyLiminfRealization
        ι approximation_index_to_prefix q L) :
    GP216GeneratedLiminfPriceCertificate
      ι approximation_index_to_prefix q L where
  observable_declared_before_payoff := O.observable_declared_before_payoff
  observable_declared_before_payoff_receipt :=
    O.observable_declared_before_payoff_receipt
  eventual_lower_bound := R.eventual_lower_bound
  tail_near_attainment := R.tail_near_attainment

/-- The generated liminf certificate is exactly a Mathlib liminf over the
selected approximation-family filter.

This theorem turns the custom tail certificate into a standard filter object.
It does not enumerate the approximation family by `ℕ`; the relevant filter is
`Filter.comap approximation_index_to_prefix Filter.atTop`. -/
theorem GP216GeneratedLiminfPriceCertificate.liminf_eq
    {ι : Type u}
    (idx : ι → ℕ)
    (q : ι → Real)
    (L : Real)
    (C : GP216GeneratedLiminfPriceCertificate ι idx q L) :
    Filter.liminf q (Filter.comap idx Filter.atTop) = L := by
  have hbounded :
      (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·) q := by
    rcases C.eventual_lower_bound 1 zero_lt_one with ⟨N, hN⟩
    refine Filter.isBoundedUnder_of_eventually_ge (a := L - 1) ?_
    rw [Filter.eventually_comap]
    rw [Filter.eventually_atTop]
    refine ⟨N, ?_⟩
    intro n hn a ha
    exact hN a (by simpa [ha] using hn)
  have hcobounded :
      (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·) q := by
    refine Filter.IsCoboundedUnder.of_frequently_le (a := L + 1) ?_
    rw [Filter.frequently_comap]
    rw [Filter.frequently_atTop]
    intro N
    rcases C.tail_near_attainment 1 zero_lt_one N with ⟨a, hNa, hq⟩
    exact ⟨idx a, hNa, a, rfl, hq⟩
  apply le_antisymm
  · refine
      ((Filter.liminf_le_iff'
        (f := Filter.comap idx Filter.atTop)
        (u := q)
        hcobounded
        hbounded).mpr ?_)
    intro y hy
    have hε : 0 < y - L := sub_pos.mpr hy
    rcases C.tail_near_attainment (y - L) hε with htail
    rw [Filter.frequently_comap]
    rw [Filter.frequently_atTop]
    intro N
    rcases htail N with ⟨a, hNa, hq⟩
    refine ⟨idx a, hNa, a, rfl, ?_⟩
    linarith
  · refine
      ((Filter.le_liminf_iff'
        (f := Filter.comap idx Filter.atTop)
        (u := q)
        hcobounded
        hbounded).mpr ?_)
    intro y hy
    have hε : 0 < L - y := sub_pos.mpr hy
    rcases C.eventual_lower_bound (L - y) hε with ⟨N, hN⟩
    rw [Filter.eventually_comap]
    rw [Filter.eventually_atTop]
    refine ⟨N, ?_⟩
    intro n hn a ha
    have htail : L - (L - y) ≤ q a := hN a (by simpa [ha] using hn)
    linarith

/-- A selected defect-generation certificate must pay with a real
measure-valued defect price, not only with a named anti-laundering proposition.

This is intentionally a positive witness on the induced defect ledger.  A
zero-defect component-LSC adapter can still satisfy nonnegativity, but it
cannot prove this predicate. -/
def GP216MeasureValuedSourceHasPositiveGeneratedDefect
    {S : LeraySelfTaxProfilePriceStream}
    (Y : LeraySelfTaxMeasureValuedDefectSource S) : Prop :=
  0 <
      selfTaxDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source Y) ∨
    0 <
      crossDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source Y) ∨
    0 <
      coherenceDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source Y)

/-- Same-family defect carrier indexed by the selected approximation family.

The witness lives over `ι`, then proves that this family is the compactness
provenance family.  It blocks the old zero-defect route by requiring generated
defect states and a positive generated defect price. -/
structure GP216SameFamilyDefectCarrierSubatom
    {S : LeraySelfTaxProfilePriceStream}
    (ι : Type u)
    (approximation_index_to_prefix : ι → ℕ)
    (C : LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource S) where
  approximation_family_equiv_compactness_provenance :
    ι ≃ C.compactness_provenance.approximation_family
  compactness_provenance_index_matches :
    ∀ a : ι,
      C.compactness_provenance.approximation_index_to_prefix
          (approximation_family_equiv_compactness_provenance a) =
        approximation_index_to_prefix a
  generatedDefect :
    ι → C.measure_valued_output_limit.measure_defect_source.defectState
  reynolds_defect_generated_on_family :
    ∃ a : ι,
      generatedDefect a =
        C.measure_valued_output_limit.measure_defect_source.reynoldsDefect
  concentration_defect_generated_on_family :
    ∃ a : ι,
      generatedDefect a =
        C.measure_valued_output_limit.measure_defect_source.concentrationDefect
  generated_defect_has_positive_price :
    ∃ a : ι, ∃ component : LeraySelfTaxPriceComponent,
      0 <
        C.measure_valued_output_limit.measure_defect_source.defectPrice
          (generatedDefect a)
          component

/-- Cross/coherence defect prices generated by the selected family. -/
structure GP216CorrelationDefectSubatom
    {S : LeraySelfTaxProfilePriceStream}
    (ι : Type u)
    (approximation_index_to_prefix : ι → ℕ)
    (C : LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource S)
    (crossDefectGeneratedLiminfPrice : Real)
    (coherenceGeneratedLiminfPrice : Real) where
  crossCorrelationObservable : ι → Real
  coherenceCorrelationObservable : ι → Real
  cross_correlation_observable_source :
    GP216SelectedFamilyObservableSource
      ι approximation_index_to_prefix S
      LeraySelfTaxPriceComponent.crossDefect
      crossCorrelationObservable
  coherence_correlation_observable_source :
    GP216SelectedFamilyObservableSource
      ι approximation_index_to_prefix S
      LeraySelfTaxPriceComponent.coherence
      coherenceCorrelationObservable
  cross_correlation_liminf_realization :
    GP216SelectedFamilyLiminfRealization
      ι approximation_index_to_prefix
      crossCorrelationObservable
      crossDefectGeneratedLiminfPrice
  coherence_correlation_liminf_realization :
    GP216SelectedFamilyLiminfRealization
      ι approximation_index_to_prefix
      coherenceCorrelationObservable
      coherenceGeneratedLiminfPrice
  positive_cross_or_coherence_defect_floor :
    0 <
        crossDefectFloor
          (relaxed_output_defect_ledger_of_measure_valued_source
            C.measure_valued_output_limit.measure_defect_source) ∨
      0 <
        coherenceDefectFloor
          (relaxed_output_defect_ledger_of_measure_valued_source
            C.measure_valued_output_limit.measure_defect_source)
  cross_liminf_includes_correlation_defect_floor :
    crossDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          C.measure_valued_output_limit.measure_defect_source) ≤
      crossDefectGeneratedLiminfPrice
  coherence_liminf_includes_correlation_defect_floor :
    coherenceDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          C.measure_valued_output_limit.measure_defect_source) ≤
      coherenceGeneratedLiminfPrice

/-- Local-energy defect price generated by the selected family. -/
structure GP216LocalEnergyDefectSubatom
    {S : LeraySelfTaxProfilePriceStream}
    (ι : Type u)
    (approximation_index_to_prefix : ι → ℕ)
    (C : LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource S)
    (selfTaxGeneratedLiminfPrice : Real) where
  localEnergyObservable : ι → Real
  local_energy_observable_source :
    GP216SelectedFamilyObservableSource
      ι approximation_index_to_prefix S
      LeraySelfTaxPriceComponent.selfTax
      localEnergyObservable
  local_energy_liminf_realization :
    GP216SelectedFamilyLiminfRealization
      ι approximation_index_to_prefix
      localEnergyObservable
      selfTaxGeneratedLiminfPrice
  positive_local_energy_defect_floor :
    0 <
      selfTaxDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          C.measure_valued_output_limit.measure_defect_source)
  self_tax_liminf_includes_local_energy_defect_floor :
    selfTaxDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          C.measure_valued_output_limit.measure_defect_source) ≤
      selfTaxGeneratedLiminfPrice

/-- Typed same-family defect provenance for the selected numeric source.

The fields are pulled from the compactness provenance carried by the selected
measure-valued source, then tied to the same approximation family and to the
numeric liminf prices.  This blocks the weaker route where fresh `Prop`s are
declared locally after a zero-defect component-LSC adapter has already supplied
the scalar inequalities. -/
structure GP216SelectedDefectGenerationCertificate
    {S : LeraySelfTaxProfilePriceStream}
    (ι : Type u)
    (approximation_index_to_prefix : ι → ℕ)
    (C : LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource S)
    (selfTaxGeneratedLiminfPrice : Real)
    (crossDefectGeneratedLiminfPrice : Real)
    (coherenceGeneratedLiminfPrice : Real) where
  approximation_family_equiv_compactness_provenance :
    ι ≃ C.compactness_provenance.approximation_family
  compactness_provenance_index_matches :
    ∀ a : ι,
      C.compactness_provenance.approximation_index_to_prefix
          (approximation_family_equiv_compactness_provenance a) =
        approximation_index_to_prefix a
  same_family_defect_carrier :
    GP216SameFamilyDefectCarrierSubatom
      ι approximation_index_to_prefix C
  correlation_defect_prices :
    GP216CorrelationDefectSubatom
      ι approximation_index_to_prefix C
      crossDefectGeneratedLiminfPrice
      coherenceGeneratedLiminfPrice
  local_energy_defect_price :
    GP216LocalEnergyDefectSubatom
      ι approximation_index_to_prefix C
      selfTaxGeneratedLiminfPrice
  defect_carrier_generated_from_same_family :
    C.compactness_provenance.defect_carrier_generated_from_approximation_family
  lions_trichotomy_reduced_to_tight_selected_branch :
    C.compactness_provenance.lions_tightness_excludes_vanishing_or_dichotomy_escape
  oscillation_concentration_pair_generated :
    C.compactness_provenance.diperna_majda_oscillation_concentration_pair_accounted
  microlocal_defect_direction_generated :
    C.compactness_provenance.tartar_microlocal_defect_direction_accounted
  multiscale_or_correlation_defects_generate_cross_coherence_prices :
    C.compactness_provenance.multiscale_or_correlation_defect_accounted
  local_energy_defect_accounted_on_selected_branch :
    C.compactness_provenance.duchon_robert_local_energy_defect_accounted
  relaxed_prices_are_generated_liminf_bounds :
    C.compactness_provenance.relaxed_output_prices_are_liminf_bounds
  not_zero_defect_component_lsc_repackaging :
    C.compactness_provenance.not_zero_defect_component_lsc_repackaging
  positive_generated_measure_defect :
    GP216MeasureValuedSourceHasPositiveGeneratedDefect
      C.measure_valued_output_limit.measure_defect_source
  self_tax_liminf_includes_measure_defect_floor :
    selfTaxDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          C.measure_valued_output_limit.measure_defect_source) ≤
      selfTaxGeneratedLiminfPrice
  cross_defect_liminf_includes_measure_defect_floor :
    crossDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          C.measure_valued_output_limit.measure_defect_source) ≤
      crossDefectGeneratedLiminfPrice
  coherence_liminf_includes_measure_defect_floor :
    coherenceDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          C.measure_valued_output_limit.measure_defect_source) ≤
      coherenceGeneratedLiminfPrice

/-- Numeric compactness/liminf provenance for the selected projected branch.

This is the repaired residual-void objective after the concentration-
compactness review.  It is deliberately selected-branch local and numerically
tied to the relaxed prices inside the measure-valued source.  A Prop-only
statement that "compactness provenance holds" is not enough here: the same
cofinal approximation family must generate the relaxed self-tax, cross-defect,
and coherence prices consumed downstream. -/
structure GP216SelectedProjectedNumericCompactnessLiminfSource
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ) where
  selected_compactness_source :
    GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource
      H n source
  approximation_family : Type u
  approximation_index_to_prefix :
    approximation_family → ℕ
  selected_projected_stream_fixed_before_payoff : Prop
  selected_projected_stream_fixed_before_payoff_receipt :
    selected_projected_stream_fixed_before_payoff
  selfTaxGeneratedLiminfPrice : Real
  crossDefectGeneratedLiminfPrice : Real
  coherenceGeneratedLiminfPrice : Real
  selfTaxFamilyObservable :
    approximation_family → Real
  crossDefectFamilyObservable :
    approximation_family → Real
  coherenceFamilyObservable :
    approximation_family → Real
  self_tax_family_observable_source :
    GP216SelectedFamilyObservableSource
      approximation_family
      approximation_index_to_prefix
      (GP216ContinuumProjectedSelectedBranchStream
        H n source selected_compactness_source.branch_is_global)
      LeraySelfTaxPriceComponent.selfTax
      selfTaxFamilyObservable
  cross_defect_family_observable_source :
    GP216SelectedFamilyObservableSource
      approximation_family
      approximation_index_to_prefix
      (GP216ContinuumProjectedSelectedBranchStream
        H n source selected_compactness_source.branch_is_global)
      LeraySelfTaxPriceComponent.crossDefect
      crossDefectFamilyObservable
  coherence_family_observable_source :
    GP216SelectedFamilyObservableSource
      approximation_family
      approximation_index_to_prefix
      (GP216ContinuumProjectedSelectedBranchStream
        H n source selected_compactness_source.branch_is_global)
      LeraySelfTaxPriceComponent.coherence
      coherenceFamilyObservable
  self_tax_liminf_realization :
    GP216SelectedFamilyLiminfRealization
      approximation_family
      approximation_index_to_prefix
      selfTaxFamilyObservable
      selfTaxGeneratedLiminfPrice
  cross_defect_liminf_realization :
    GP216SelectedFamilyLiminfRealization
      approximation_family
      approximation_index_to_prefix
      crossDefectFamilyObservable
      crossDefectGeneratedLiminfPrice
  coherence_liminf_realization :
    GP216SelectedFamilyLiminfRealization
      approximation_family
      approximation_index_to_prefix
      coherenceFamilyObservable
      coherenceGeneratedLiminfPrice
  self_tax_generated_liminf_eq_relaxed_output :
    selfTaxGeneratedLiminfPrice =
      LeraySelfTaxMeasureValuedOutputLimitSource.selfTaxRelaxedOutputPrice
        (LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource.toMeasureValued
          selected_compactness_source.projected_compactness_measure_valued_source)
  cross_defect_generated_liminf_eq_relaxed_output :
    crossDefectGeneratedLiminfPrice =
      LeraySelfTaxMeasureValuedOutputLimitSource.crossDefectRelaxedOutputPrice
        (LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource.toMeasureValued
          selected_compactness_source.projected_compactness_measure_valued_source)
  coherence_generated_liminf_eq_relaxed_output :
    coherenceGeneratedLiminfPrice =
      LeraySelfTaxMeasureValuedOutputLimitSource.coherenceRelaxedOutputPrice
        (LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource.toMeasureValued
          selected_compactness_source.projected_compactness_measure_valued_source)
  self_tax_prefix_le_generated_liminf :
    ∀ k,
      (GP216ContinuumProjectedSelectedBranchStream
        H n source selected_compactness_source.branch_is_global).prefixSelfTaxPrice k ≤
        selfTaxGeneratedLiminfPrice
  cross_defect_prefix_le_generated_liminf :
    ∀ k,
      (GP216ContinuumProjectedSelectedBranchStream
        H n source selected_compactness_source.branch_is_global).prefixCrossDefectPrice k ≤
        crossDefectGeneratedLiminfPrice
  coherence_prefix_le_generated_liminf :
    ∀ k,
      (GP216ContinuumProjectedSelectedBranchStream
        H n source selected_compactness_source.branch_is_global).prefixCoherencePrice k ≤
        coherenceGeneratedLiminfPrice
  self_tax_generated_liminf_le_limit :
    selfTaxGeneratedLiminfPrice ≤
      (GP216ContinuumProjectedSelectedBranchStream
        H n source selected_compactness_source.branch_is_global).selfTaxLimitPrice
  cross_defect_generated_liminf_le_limit :
    crossDefectGeneratedLiminfPrice ≤
      (GP216ContinuumProjectedSelectedBranchStream
        H n source selected_compactness_source.branch_is_global).crossDefectLimitPrice
  coherence_generated_liminf_le_limit :
    coherenceGeneratedLiminfPrice ≤
      (GP216ContinuumProjectedSelectedBranchStream
        H n source selected_compactness_source.branch_is_global).coherenceLimitPrice
  selected_defect_generation_certificate :
    GP216SelectedDefectGenerationCertificate
      approximation_family
      approximation_index_to_prefix
      selected_compactness_source.projected_compactness_measure_valued_source
      selfTaxGeneratedLiminfPrice
      crossDefectGeneratedLiminfPrice
      coherenceGeneratedLiminfPrice

/-- Forget the numeric provenance only after it has paid the selected source.

This adapter is zero source credit.  It lets existing GP216 consumers keep using
the compactness-provenance selected source while the residual-void objective is
tightened to the numeric provenance structure above. -/
def GP216SelectedProjectedNumericCompactnessLiminfSource.toCompactnessSource
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S : GP216SelectedProjectedNumericCompactnessLiminfSource H n source) :
    GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource
      H n source :=
  S.selected_compactness_source

/-- Compactness-provenance selected projection forgets to the older
measure-valued source only after the provenance has been supplied. -/
def GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource.toMeasureValuedAuditedOutputSource
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource
        H n source) :
    GP216ContinuumProjectedSelectedBranchMeasureValuedAuditedOutputSource
      H n source where
  branch_is_global := S.branch_is_global
  projected_measure_valued_source :=
    S.projected_compactness_measure_valued_source.toMeasureValued
  projected_measure_valued_compactness_provenance :=
    S.projected_compactness_measure_valued_source.compactness_provenance

/-- Family-level compactness provenance pays the selected projected GP216
source through the already declared projected-stream equality.

This is not a final-receipt shortcut: the source credit sits in the
family-level compactness-provenance MV source for `source.stream_of_block`.
The selected continuum projection is only rewritten to that declared family
stream. -/
def GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource.ofFamilyCompactnessSource
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (family_compactness_source :
      LeraySelfTaxCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource
        source.stream_of_block)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n)) :
    GP216ContinuumProjectedSelectedBranchCompactnessMeasureValuedAuditedOutputSource
      H n source where
  branch_is_global := branch_is_global
  projected_compactness_measure_valued_source := by
    let B := GP216GeneratedProfileLipschitzBranchBlock H n
    rw [source.projected_stream_matches_block B branch_is_global]
    exact family_compactness_source.compactness_mv_source_of_global
      B branch_is_global

/-- A measure-valued selected projection instantiates the audited selected
projection without adding a separate stream-equality premise. -/
def GP216ContinuumProjectedSelectedBranchMeasureValuedAuditedOutputSource.toAuditedOutputSource
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchMeasureValuedAuditedOutputSource
        H n source) :
    GP216ContinuumProjectedSelectedBranchAuditedOutputSource H n source where
  branch_is_global := S.branch_is_global
  projected_audited_source := by
    let B := GP216GeneratedProfileLipschitzBranchBlock H n
    let A := source.all_output_source_of_global B S.branch_is_global
    let P := source.component_source_of_global B S.branch_is_global
    let stream :=
      leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource A P.split
    exact
      audited_mv_tendsto_output_source_noncircular
        stream
        (continuum_all_output_self_tax_component_assembly A P)
        (continuum_all_output_self_tax_finite_prefix_charge A P)
        (by
          simp [stream, leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource])
        S.projected_measure_valued_source
        (leray_self_tax_noncircular_measure_valued_output_convergence_receipt_of_source
          stream
          S.projected_measure_valued_source)

/-- The audited selected projection gives the GP216 self-tax bundle by
construction. -/
def GP216ContinuumProjectedSelectedBranchAuditedOutputSource.toSelfTaxBundle
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchAuditedOutputSource H n source) :
    GP216SelfTaxAuditedOutputSourceBundle :=
  gp216_self_tax_audited_output_source_bundle_of_audited_source
    (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
      (source.all_output_source_of_global
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        S.branch_is_global)
      ((source.component_source_of_global
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        S.branch_is_global).split))
    S.projected_audited_source

/-- Auditing the selected projected continuum stream pays the selected-branch
stream match against the GP216 bundle built from that same stream. -/
def GP216ContinuumProjectedSelectedBranchAuditedOutputSource.toStreamMatchSource
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchAuditedOutputSource H n source) :
    GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchSource
      H n S.toSelfTaxBundle source where
  branch_is_global := S.branch_is_global
  projected_branch_stream_matches_self_tax_output := rfl

/-- Hostile surface for the projected-continuum selected-branch equality. -/
inductive GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (_S :
      GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource source) :
    Type where
  | projectedBranchStreamMismatch :
      leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        (source.all_output_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          _S.branch_is_global)
        ((source.component_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          _S.branch_is_global).split) ≠
        selfTaxOutputSource.stream →
      GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchFalsifier _S

/-- A projected-continuum selected-branch source rules out its named mismatch. -/
theorem no_GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource source)
    (F :
      GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchFalsifier S) :
    False := by
  cases F with
  | projectedBranchStreamMismatch hbad =>
      exact hbad S.projected_branch_stream_matches_self_tax_output

/-- Convert the projected-continuum selected-branch equality into the generic
selected-branch stream-match source. -/
def GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchSource.toSelectedBranchStreamMatch
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource source) :
    GP216SelectedBranchSelfTaxStreamMatchSource
      H n selfTaxOutputSource source.stream_of_block :=
  GP216SelectedBranchSelfTaxStreamMatchSource.ofContinuumProjectedSelectedBranchEquality
    H
    n
    selfTaxOutputSource
    source
    S.branch_is_global
    S.projected_branch_stream_matches_self_tax_output

/-- Coordinate-level equivalence for the threshold-root handoff.

This is weaker than equality of `LeraySelfTaxProfilePriceStream` records.  It
contains only the two declaration guards and four scalar coordinates consumed by
`BranchSelfTaxThresholdCoordinateIdentities`. -/
structure LeraySelfTaxThresholdCoordinateEquivalence
    (source target : LeraySelfTaxProfilePriceStream) where
  target_profile_topology_declared_before_payoff :
    target.profileTopologyDeclaredBeforePayoff
  target_limit_component_prices_declared_before_payoff :
    target.limitComponentPricesDeclaredBeforePayoff
  payoff_limit_eq :
    target.payoffLimit = source.payoffLimit
  self_tax_limit_price_eq :
    target.selfTaxLimitPrice = source.selfTaxLimitPrice
  cross_defect_limit_price_eq :
    target.crossDefectLimitPrice = source.crossDefectLimitPrice
  coherence_limit_price_eq :
    target.coherenceLimitPrice = source.coherenceLimitPrice

/-- Transport exact branch threshold coordinates across coordinate-level
equivalence.

This avoids the over-strong whole-stream equality route.  The proof only rewrites
the scalar coordinates that the threshold package actually consumes. -/
def branch_threshold_coordinates_transport_of_coordinate_equivalence
    (B : FullLedgerBlock)
    (source target : LeraySelfTaxProfilePriceStream)
    (I : BranchSelfTaxThresholdCoordinateIdentities B source)
    (E : LeraySelfTaxThresholdCoordinateEquivalence source target) :
    BranchSelfTaxThresholdCoordinateIdentities B target where
  coordinates_declared_before_payoff :=
    E.target_profile_topology_declared_before_payoff
  threshold_root_uses_same_ledger :=
    E.target_limit_component_prices_declared_before_payoff
  payoff_limit_eq_one := by
    intro hgamma
    rw [E.payoff_limit_eq]
    exact I.payoff_limit_eq_one hgamma
  self_tax_limit_price_eq := by
    intro hgamma
    rw [E.self_tax_limit_price_eq]
    exact I.self_tax_limit_price_eq hgamma
  cross_defect_limit_price_eq := by
    intro hgamma
    rw [E.cross_defect_limit_price_eq]
    exact I.cross_defect_limit_price_eq hgamma
  coherence_limit_price_eq := by
    intro hgamma
    rw [E.coherence_limit_price_eq]
    exact I.coherence_limit_price_eq hgamma

/-- Source object for threshold-coordinate equivalence between the projected
continuum selected branch and the audited GP216 self-tax stream.

This is the de-anchored residual source: it does not ask the two streams to be
equal as records, only that the threshold coordinates consumed by the final
handoff agree. -/
structure GP216ContinuumProjectedSelectedBranchThresholdCoordinateMatchSource
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ) where
  branch_is_global :
    IsGlobalTrackBBlock
      (GP216GeneratedProfileLipschitzBranchBlock H n)
  projected_branch_threshold_coordinates_match_self_tax_output :
    LeraySelfTaxThresholdCoordinateEquivalence
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        (source.all_output_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global)
        ((source.component_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global).split))
      selfTaxOutputSource.stream

/-- Which threshold-coordinate equality failed between a projected continuum
branch stream and the audited GP216 self-tax output stream. -/
inductive GP216ProjectedSelectedBranchThresholdCoordinateMismatch where
  | payoffLimit
  | selfTaxLimit
  | crossDefectLimit
  | coherenceLimit
deriving DecidableEq, Repr

/-- Hostile surface for the coordinate-level selected-branch residual void. -/
structure GP216ContinuumProjectedSelectedBranchThresholdCoordinateMatchFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchThresholdCoordinateMatchSource
        H n selfTaxOutputSource source) where
  branch : GP216ProjectedSelectedBranchThresholdCoordinateMismatch
  mismatch :
    let projected :=
      leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        (source.all_output_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          S.branch_is_global)
        ((source.component_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          S.branch_is_global).split)
    match branch with
    | GP216ProjectedSelectedBranchThresholdCoordinateMismatch.payoffLimit =>
        selfTaxOutputSource.stream.payoffLimit ≠ projected.payoffLimit
    | GP216ProjectedSelectedBranchThresholdCoordinateMismatch.selfTaxLimit =>
        selfTaxOutputSource.stream.selfTaxLimitPrice ≠ projected.selfTaxLimitPrice
    | GP216ProjectedSelectedBranchThresholdCoordinateMismatch.crossDefectLimit =>
        selfTaxOutputSource.stream.crossDefectLimitPrice ≠
          projected.crossDefectLimitPrice
    | GP216ProjectedSelectedBranchThresholdCoordinateMismatch.coherenceLimit =>
        selfTaxOutputSource.stream.coherenceLimitPrice ≠
          projected.coherenceLimitPrice

/-- A coordinate-match source rules out its named scalar-coordinate mismatch. -/
theorem no_GP216ContinuumProjectedSelectedBranchThresholdCoordinateMatchFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchThresholdCoordinateMatchSource
        H n selfTaxOutputSource source)
    (F :
      GP216ContinuumProjectedSelectedBranchThresholdCoordinateMatchFalsifier S) :
    False := by
  rcases F with ⟨branch, mismatch⟩
  cases branch with
  | payoffLimit =>
      exact mismatch S.projected_branch_threshold_coordinates_match_self_tax_output.payoff_limit_eq
  | selfTaxLimit =>
      exact mismatch
        S.projected_branch_threshold_coordinates_match_self_tax_output.self_tax_limit_price_eq
  | crossDefectLimit =>
      exact mismatch
        S.projected_branch_threshold_coordinates_match_self_tax_output.cross_defect_limit_price_eq
  | coherenceLimit =>
      exact mismatch
        S.projected_branch_threshold_coordinates_match_self_tax_output.coherence_limit_price_eq

/-- Lower-level source for the projected selected-branch coordinate match.

The live PDE primitive is not whole-stream equality.  It is that the audited
GP216 self-tax stream has the same payoff and component-limit coordinates as
the continuum source and component split selected by the generated branch. -/
structure GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchSource
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ) where
  branch_is_global :
    IsGlobalTrackBBlock
      (GP216GeneratedProfileLipschitzBranchBlock H n)
  target_profile_topology_declared_before_payoff :
    selfTaxOutputSource.stream.profileTopologyDeclaredBeforePayoff
  target_limit_component_prices_declared_before_payoff :
    selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff
  payoff_limit_matches_projected :
    selfTaxOutputSource.stream.payoffLimit =
      (source.all_output_source_of_global
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global).stream.smoothCandidatePayoff
  self_tax_limit_matches_projected_split :
    selfTaxOutputSource.stream.selfTaxLimitPrice =
      ((source.component_source_of_global
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global).split).selfTaxLimitPrice
  cross_defect_limit_matches_projected_split :
    selfTaxOutputSource.stream.crossDefectLimitPrice =
      ((source.component_source_of_global
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global).split).crossDefectLimitPrice
  coherence_limit_matches_projected_split :
    selfTaxOutputSource.stream.coherenceLimitPrice =
      ((source.component_source_of_global
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global).split).coherenceLimitPrice

/-- Which selected-branch limit component failed to match the projected
continuum all-output source and component split. -/
inductive GP216ProjectedSelectedBranchLimitComponentSplitMismatch where
  | payoffLimit
  | selfTaxLimit
  | crossDefectLimit
  | coherenceLimit
deriving DecidableEq, Repr

/-- Hostile surface for a selected-branch split-match source whose audited
self-tax stream does not carry the projected continuum payoff/component
coordinates. -/
structure GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchSource
        H n selfTaxOutputSource source) where
  branch : GP216ProjectedSelectedBranchLimitComponentSplitMismatch
  mismatch :
    match branch with
    | GP216ProjectedSelectedBranchLimitComponentSplitMismatch.payoffLimit =>
        selfTaxOutputSource.stream.payoffLimit ≠
          (source.all_output_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            S.branch_is_global).stream.smoothCandidatePayoff
    | GP216ProjectedSelectedBranchLimitComponentSplitMismatch.selfTaxLimit =>
        selfTaxOutputSource.stream.selfTaxLimitPrice ≠
          ((source.component_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            S.branch_is_global).split).selfTaxLimitPrice
    | GP216ProjectedSelectedBranchLimitComponentSplitMismatch.crossDefectLimit =>
        selfTaxOutputSource.stream.crossDefectLimitPrice ≠
          ((source.component_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            S.branch_is_global).split).crossDefectLimitPrice
    | GP216ProjectedSelectedBranchLimitComponentSplitMismatch.coherenceLimit =>
        selfTaxOutputSource.stream.coherenceLimitPrice ≠
          ((source.component_source_of_global
            (GP216GeneratedProfileLipschitzBranchBlock H n)
            S.branch_is_global).split).coherenceLimitPrice

/-- A selected-branch split-match source rules out its named scalar mismatch. -/
theorem no_GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchSource
        H n selfTaxOutputSource source)
    (F :
      GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchFalsifier
        S) :
    False := by
  rcases F with ⟨branch, mismatch⟩
  cases branch with
  | payoffLimit =>
      exact mismatch S.payoff_limit_matches_projected
  | selfTaxLimit =>
      exact mismatch S.self_tax_limit_matches_projected_split
  | crossDefectLimit =>
      exact mismatch S.cross_defect_limit_matches_projected_split
  | coherenceLimit =>
      exact mismatch S.coherence_limit_matches_projected_split

/-- A selected projected-stream equality pays the split-coordinate source.

This is the residual-void algebraic constructor.  It does not use the final GP216
receipt or a threshold-coordinate source.  It says that once the audited GP216
self-tax stream is independently identified with the selected continuum
projection, the payoff and component-limit coordinates are only projections of
that stream equality. -/
def GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchSource.ofProjectedStreamEquality
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (projected_branch_stream_matches_self_tax_output :
      leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        (source.all_output_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global)
        ((source.component_source_of_global
          (GP216GeneratedProfileLipschitzBranchBlock H n)
          branch_is_global).split) =
      selfTaxOutputSource.stream) :
    GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchSource
      H n selfTaxOutputSource source where
  branch_is_global := branch_is_global
  target_profile_topology_declared_before_payoff := by
    let B := GP216GeneratedProfileLipschitzBranchBlock H n
    let A := source.all_output_source_of_global B branch_is_global
    rw [← projected_branch_stream_matches_self_tax_output]
    exact A.fixed_topology
  target_limit_component_prices_declared_before_payoff := by
    let B := GP216GeneratedProfileLipschitzBranchBlock H n
    let P := source.component_source_of_global B branch_is_global
    rw [← projected_branch_stream_matches_self_tax_output]
    exact P.split.limit_component_prices_declared_before_payoff_paid
  payoff_limit_matches_projected := by
    rw [← projected_branch_stream_matches_self_tax_output]
    rfl
  self_tax_limit_matches_projected_split := by
    rw [← projected_branch_stream_matches_self_tax_output]
    rfl
  cross_defect_limit_matches_projected_split := by
    rw [← projected_branch_stream_matches_self_tax_output]
    rfl
  coherence_limit_matches_projected_split := by
    rw [← projected_branch_stream_matches_self_tax_output]
    rfl

/-- The older projected-stream source is strong enough to pay the current
split-coordinate residual source. -/
def GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchSource.toLimitComponentSplitMatch
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource source) :
    GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchSource
      H n selfTaxOutputSource source :=
  GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchSource.ofProjectedStreamEquality
    H
    n
    selfTaxOutputSource
    source
    S.branch_is_global
    S.projected_branch_stream_matches_self_tax_output

/-- The selected-branch split-match source produces the coordinate equivalence
consumed by the residual-void bridge. -/
def GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchSource.toCoordinateMatch
    {τ : ContinuumLPProfileTopology.{u}}
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (S :
      GP216ContinuumProjectedSelectedBranchLimitComponentSplitMatchSource
        H n selfTaxOutputSource source) :
    GP216ContinuumProjectedSelectedBranchThresholdCoordinateMatchSource
      H n selfTaxOutputSource source where
  branch_is_global := S.branch_is_global
  projected_branch_threshold_coordinates_match_self_tax_output := by
    let B := GP216GeneratedProfileLipschitzBranchBlock H n
    let A := source.all_output_source_of_global B S.branch_is_global
    let P := source.component_source_of_global B S.branch_is_global
    exact
      { target_profile_topology_declared_before_payoff :=
          S.target_profile_topology_declared_before_payoff
        target_limit_component_prices_declared_before_payoff :=
          S.target_limit_component_prices_declared_before_payoff
        payoff_limit_eq := by
          exact S.payoff_limit_matches_projected
        self_tax_limit_price_eq := by
          exact S.self_tax_limit_matches_projected_split
        cross_defect_limit_price_eq := by
          exact S.cross_defect_limit_matches_projected_split
        coherence_limit_price_eq := by
          exact S.coherence_limit_matches_projected_split }

/-- Projected continuum coordinate-match source pays the selected-branch
threshold-coordinate identities for the audited GP216 self-tax stream. -/
theorem branch_threshold_coordinates_of_continuum_projected_selected_branch_coordinate_match
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (coordinate_match :
      GP216ContinuumProjectedSelectedBranchThresholdCoordinateMatchSource
        H n selfTaxOutputSource profile_stream_source) :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      selfTaxOutputSource.stream := by
  let B := GP216GeneratedProfileLipschitzBranchBlock H n
  let A := profile_stream_source.all_output_source_of_global
    B coordinate_match.branch_is_global
  let P := profile_stream_source.component_source_of_global
    B coordinate_match.branch_is_global
  have hproject :
      leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        A P.split =
      profile_stream_source.stream_of_block B :=
    profile_stream_source.projected_stream_matches_block
      B coordinate_match.branch_is_global
  have Iblock :
      BranchSelfTaxThresholdCoordinateIdentities
        B (profile_stream_source.stream_of_block B) :=
    profile_stream_source.threshold_coordinate_receipt_of_global
      B coordinate_match.branch_is_global
  have Iproject :
      BranchSelfTaxThresholdCoordinateIdentities
        B
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          A P.split) := by
    rw [hproject]
    exact Iblock
  exact
    branch_threshold_coordinates_transport_of_coordinate_equivalence
      B
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        A P.split)
      selfTaxOutputSource.stream
      Iproject
      coordinate_match.projected_branch_threshold_coordinates_match_self_tax_output

/-- Branch-scoped compatibility between the generated profile/Lipschitz block
and the audited Leray self-tax stream.

This is deliberately narrower than the global constant-stream adapters: it
ties only the selected generated branch to the GP216 self-tax output stream and
keeps the exact threshold-coordinate identity source as its own field.  If
that source cannot be constructed analytically, the same-topology/component-LSC
route stops here. -/
structure GP216GeneratedBranchSelfTaxLipschitzCompatibility
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle) where
  branch_is_global :
    IsGlobalTrackBBlock
      (GP216GeneratedProfileLipschitzBranchBlock H n)
  profile_family_self_tax_stream_declared_together : Prop
  profile_family_self_tax_stream_declared_together_paid :
    profile_family_self_tax_stream_declared_together
  profile_payoff_matches_self_tax_stream :
    familyPayoff
      (H.profile_lipschitz.profile_bundle.profile_family_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n)) =
        selfTaxOutputSource.stream.payoffLimit
  profile_price_matches_self_tax_stream :
    familyPrice
      (H.profile_lipschitz.profile_bundle.profile_family_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n)) =
        leraySelfTaxLimitPrice selfTaxOutputSource.stream
  threshold_coordinate_source :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      selfTaxOutputSource.stream

/-- The branch-scoped compatibility source plus the audited output-derived
component receipt pays the threshold-root defect for that same generated
branch. -/
theorem GP216GeneratedBranchSelfTaxLipschitzCompatibility.thresholdRootDefectGeOne
    {H : TrackBContinuationHandoffReceipt}
    {n : ℕ}
    {selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle}
    (C :
      GP216GeneratedBranchSelfTaxLipschitzCompatibility
        H n selfTaxOutputSource)
    (habove :
      sharpTarget <
        (GP216GeneratedProfileLipschitzBranchBlock H n).gamma) :
    1 ≤
      survivalDefect
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        (Real.sqrt
          (sharpTarget /
            (GP216GeneratedProfileLipschitzBranchBlock H n).gamma)) :=
  threshold_root_defect_ge_one_of_output_derived_and_threshold_identities
    (GP216GeneratedProfileLipschitzBranchBlock H n)
    selfTaxOutputSource.stream
    selfTaxOutputSource.outputDerivedComponentLimitPassage
    C.threshold_coordinate_source
    habove

/-- Branch-local constructor from a continuum scalar-alignment source.

Unlike the older GP216 scalar-alignment constructor, this needs the projected
continuum stream to match the audited GP216 self-tax stream only at the
selected generated branch.  The threshold-coordinate receipt is transported
from the continuum stream-family source at the same branch. -/
def GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofContinuumScalarAlignmentAtBranch
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (profile_stream_alignment :
      ContinuumProfileFamilyScalarAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (branch_stream_matches_self_tax_output :
      profile_stream_source.stream_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n) =
          selfTaxOutputSource.stream) :
    GP216GeneratedBranchSelfTaxLipschitzCompatibility
      H n selfTaxOutputSource where
  branch_is_global := branch_is_global
  profile_family_self_tax_stream_declared_together :=
    profile_stream_alignment.profile_family_and_stream_declared_together
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      branch_is_global
  profile_family_self_tax_stream_declared_together_paid :=
    profile_stream_alignment.profile_family_and_stream_declared_together_paid
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      branch_is_global
  profile_payoff_matches_self_tax_stream := by
    let I :=
      profile_family_self_tax_stream_identity_compatibility_of_continuum_scalar_alignment_source
        profile_stream_alignment
    have hpay :=
      I.payoff_matches
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global
    simpa [branch_stream_matches_self_tax_output] using hpay
  profile_price_matches_self_tax_stream := by
    let I :=
      profile_family_self_tax_stream_identity_compatibility_of_continuum_scalar_alignment_source
        profile_stream_alignment
    have hprice :=
      I.price_matches
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global
    simpa [branch_stream_matches_self_tax_output] using hprice
  threshold_coordinate_source := by
    have hthreshold :=
      profile_stream_source.threshold_coordinate_receipt_of_global
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global
    simpa [branch_stream_matches_self_tax_output] using hthreshold

/-- Branch-local constructor from a continuum scalar-alignment source and the
named selected-branch stream-match source. -/
def GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofContinuumScalarAlignmentAndSelectedBranchStreamMatch
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (profile_stream_alignment :
      ContinuumProfileFamilyScalarAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source)
    (stream_match :
      GP216SelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource profile_stream_source.stream_of_block) :
    GP216GeneratedBranchSelfTaxLipschitzCompatibility
      H n selfTaxOutputSource :=
  GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofContinuumScalarAlignmentAtBranch
    H
    n
    selfTaxOutputSource
    profile_stream_source
    profile_stream_alignment
    stream_match.branch_is_global
    stream_match.selected_branch_stream_matches_self_tax_output

/-- Branch-local constructor from continuum scalar alignment and the projected
continuum selected-branch stream source. -/
def GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofContinuumScalarAlignmentAndProjectedSelectedBranchStreamMatch
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (profile_stream_alignment :
      ContinuumProfileFamilyScalarAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source)
    (projected_stream_match :
      GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource profile_stream_source) :
    GP216GeneratedBranchSelfTaxLipschitzCompatibility
      H n selfTaxOutputSource :=
  GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofContinuumScalarAlignmentAndSelectedBranchStreamMatch
    H
    n
    selfTaxOutputSource
    profile_stream_source
    profile_stream_alignment
    projected_stream_match.toSelectedBranchStreamMatch

/-- Direct selected-branch threshold-coordinate source from a continuum
all-output scalar-alignment family. -/
theorem branch_threshold_coordinates_of_continuum_scalar_alignment_at_generated_branch
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (_profile_stream_alignment :
      ContinuumProfileFamilyScalarAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (branch_stream_matches_self_tax_output :
      profile_stream_source.stream_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n) =
          selfTaxOutputSource.stream) :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      selfTaxOutputSource.stream := by
  have hthreshold :=
    profile_stream_source.threshold_coordinate_receipt_of_global
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      branch_is_global
  simpa [branch_stream_matches_self_tax_output] using hthreshold

/-- Direct selected-branch threshold-coordinate source from a projected
continuum selected-branch stream source. -/
theorem branch_threshold_coordinates_of_continuum_projected_selected_branch_stream_match
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (_profile_stream_alignment :
      ContinuumProfileFamilyScalarAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source)
    (projected_stream_match :
      GP216ContinuumProjectedSelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource profile_stream_source) :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      selfTaxOutputSource.stream :=
  branch_threshold_coordinates_of_continuum_scalar_alignment_at_generated_branch
    H
    n
    selfTaxOutputSource
    profile_stream_source
    _profile_stream_alignment
    projected_stream_match.branch_is_global
    projected_stream_match.toSelectedBranchStreamMatch.selected_branch_stream_matches_self_tax_output

/-- Branch-local constructor from a noncircular measure-valued scalar-alignment
source.

This is the Young/defect analogue of
`ofContinuumScalarAlignmentAtBranch`: it avoids a global constant-stream
adapter by asking only that the selected generated branch's noncircular
measure-valued stream is the audited GP216 self-tax stream.  The exact
threshold-coordinate receipt is transported from the same source at that
branch. -/
def GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofNoncircularMVScalarAlignmentAtBranch
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (alignment :
      NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        source)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (branch_stream_matches_self_tax_output :
      source.stream_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n) =
          selfTaxOutputSource.stream) :
    GP216GeneratedBranchSelfTaxLipschitzCompatibility
      H n selfTaxOutputSource where
  branch_is_global := branch_is_global
  profile_family_self_tax_stream_declared_together :=
    alignment.profile_family_and_stream_declared_together
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      branch_is_global
  profile_family_self_tax_stream_declared_together_paid :=
    alignment.profile_family_and_stream_declared_together_paid
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      branch_is_global
  profile_payoff_matches_self_tax_stream := by
    let I :=
      profile_family_self_tax_stream_identity_compatibility_of_noncircular_mv_scalar_alignment_source
        alignment
    have hpay :=
      I.payoff_matches
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global
    simpa [branch_stream_matches_self_tax_output] using hpay
  profile_price_matches_self_tax_stream := by
    let I :=
      profile_family_self_tax_stream_identity_compatibility_of_noncircular_mv_scalar_alignment_source
        alignment
    have hprice :=
      I.price_matches
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global
    simpa [branch_stream_matches_self_tax_output] using hprice
  threshold_coordinate_source := by
    have hthreshold :=
      source.threshold_coordinate_receipt_of_global
        (GP216GeneratedProfileLipschitzBranchBlock H n)
        branch_is_global
    simpa [branch_stream_matches_self_tax_output] using hthreshold

/-- Branch-local constructor from a noncircular measure-valued scalar-alignment
source and the named selected-branch stream-match source. -/
def GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofNoncircularMVScalarAlignmentAndSelectedBranchStreamMatch
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (alignment :
      NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        source)
    (stream_match :
      GP216SelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource source.stream_of_block) :
    GP216GeneratedBranchSelfTaxLipschitzCompatibility
      H n selfTaxOutputSource :=
  GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofNoncircularMVScalarAlignmentAtBranch
    H
    n
    selfTaxOutputSource
    source
    alignment
    stream_match.branch_is_global
    stream_match.selected_branch_stream_matches_self_tax_output

/-- Direct selected-branch threshold-coordinate source from a noncircular
measure-valued scalar-alignment family. -/
theorem branch_threshold_coordinates_of_noncircular_mv_scalar_alignment_at_generated_branch
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (_alignment :
      NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        source)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (branch_stream_matches_self_tax_output :
      source.stream_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n) =
          selfTaxOutputSource.stream) :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      selfTaxOutputSource.stream := by
  have hthreshold :=
    source.threshold_coordinate_receipt_of_global
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      branch_is_global
  simpa [branch_stream_matches_self_tax_output] using hthreshold

/-- Branch-local constructor from a continuum Phase 5FB observable-alignment
source.

The Phase 5FB source pays the profile-family scalar alignment for the same
profile bundle and generated Lipschitz bridge.  It still does not pay the
selected-branch equality between the continuum stream and the audited GP216
self-tax stream; that equality remains an explicit analytic source. -/
def GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofContinuumPhase5FBSigmaObservableAlignmentAtBranch
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (phase5fb_alignment :
      ContinuumPhase5FBSigmaObservableAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source
        H.profile_lipschitz.lipschitz_bridge)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (branch_stream_matches_self_tax_output :
      profile_stream_source.stream_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n) =
          selfTaxOutputSource.stream) :
    GP216GeneratedBranchSelfTaxLipschitzCompatibility
      H n selfTaxOutputSource :=
  GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofContinuumScalarAlignmentAtBranch
    H
    n
    selfTaxOutputSource
    profile_stream_source
    phase5fb_alignment.alignment
    branch_is_global
    branch_stream_matches_self_tax_output

/-- Branch-local constructor from continuum Phase 5FB observable alignment and
the named selected-branch stream-match source. -/
def GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofContinuumPhase5FBSigmaObservableAlignmentAndSelectedBranchStreamMatch
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (phase5fb_alignment :
      ContinuumPhase5FBSigmaObservableAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source
        H.profile_lipschitz.lipschitz_bridge)
    (stream_match :
      GP216SelectedBranchSelfTaxStreamMatchSource
        H n selfTaxOutputSource profile_stream_source.stream_of_block) :
    GP216GeneratedBranchSelfTaxLipschitzCompatibility
      H n selfTaxOutputSource :=
  GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofContinuumPhase5FBSigmaObservableAlignmentAtBranch
    H
    n
    selfTaxOutputSource
    profile_stream_source
    phase5fb_alignment
    stream_match.branch_is_global
    stream_match.selected_branch_stream_matches_self_tax_output

/-- Direct threshold-coordinate projection from a continuum Phase 5FB
observable-alignment source at the selected generated branch.

This is the same selected-branch projection as the scalar-alignment route, with
Phase 5FB provenance attached to the profile-alignment source. -/
theorem branch_threshold_coordinates_of_continuum_phase5fb_sigma_observable_alignment_at_generated_branch
    {τ : ContinuumLPProfileTopology.{u}}
    (H : TrackBContinuationHandoffReceipt)
    (n : ℕ)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (_phase5fb_alignment :
      ContinuumPhase5FBSigmaObservableAlignmentSource
        H.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source
        H.profile_lipschitz.lipschitz_bridge)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock H n))
    (branch_stream_matches_self_tax_output :
      profile_stream_source.stream_of_block
        (GP216GeneratedProfileLipschitzBranchBlock H n) =
          selfTaxOutputSource.stream) :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock H n)
      selfTaxOutputSource.stream :=
  branch_threshold_coordinates_of_continuum_scalar_alignment_at_generated_branch
    H
    n
    selfTaxOutputSource
    profile_stream_source
    _phase5fb_alignment.alignment
    branch_is_global
    branch_stream_matches_self_tax_output

/-- Constructor for the final GP216 receipt from a generated profile/Lipschitz
branch.

This is the source-facing final assembly route.  It removes the detached-branch
failure mode by setting `branchBlock` definitionally to the generated
profile/Lipschitz block.  The constructor still requires all load-bearing
witnesses: branch globality, threshold/self-tax identities, profile/self-tax
payoff and price equalities, low-high reserve PDE handoff, concrete Fourier
phase source, and macroscopic flat-torus clock source. -/
def gp216_bridge_composition_receipt_of_generated_branch
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate :
      LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource :
      GP216ContinuumAllOutputSourceBundle
        selfTaxOutputSource.stream
        eventRecurrenceSource.ledger)
    (coordinateReformulation :
      TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex))
    (branchSelfTaxThresholdCoordinateIdentities :
      BranchSelfTaxThresholdCoordinateIdentities
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
        selfTaxOutputSource.stream)
    (highHigh_same_output_ledger_matches_self_tax_stream :
      highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
        selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff)
    (coordinate_source_is_branch :
      coordinateReformulation.source =
        GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
    (branch_profile_family_self_tax_stream_declared_together : Prop)
    (branch_profile_family_self_tax_stream_declared_together_paid :
      branch_profile_family_self_tax_stream_declared_together)
    (branch_profile_family_payoff_matches_self_tax_stream :
      familyPayoff
        (continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
          (GP216GeneratedProfileLipschitzBranchBlock
            continuationSource.handoff
            profileLipschitzBranchIndex)) =
        selfTaxOutputSource.stream.payoffLimit)
    (branch_profile_family_price_matches_self_tax_stream :
      familyPrice
        (continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
          (GP216GeneratedProfileLipschitzBranchBlock
            continuationSource.handoff
            profileLipschitzBranchIndex)) =
        leraySelfTaxLimitPrice selfTaxOutputSource.stream)
    (lowHighReservePDESource :
      GP216LowHighReservePDESourceBundle
        continuationSource.handoff)
    (phaseLatencyProfileReserveSource :
      PhaseLatencyProfileLipschitzReserveSource
        continuationSource.handoff.profile_lipschitz
        continuationSource.handoff.initialData)
    (phaseLatencyConcreteFourierSymbol :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData))
    (phaseLatencyControlBudget_matches_required_lipschitz :
      ∀ n : ℕ,
        phaseLatencyProfileReserveSource.phase.controlBudget n =
          phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n)
    (macroscopicFlatTorusClockSource :
      MacroscopicFlatTorusClockSource
        (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData
          phaseLatencyProfileReserveSource.phase
          phaseLatencyConcreteFourierSymbol
          phaseLatencyControlBudget_matches_required_lipschitz
        ).toPhaseLatencyCapacitySource) :
    GP216BridgeCompositionReceipt where
  declaredScope := declaredScope
  branchBlock :=
    GP216GeneratedProfileLipschitzBranchBlock
      continuationSource.handoff
      profileLipschitzBranchIndex
  branch_is_global := branch_is_global
  highHighSelfTaxPDESource := highHighSelfTaxPDESource
  selfTaxOutputSource := selfTaxOutputSource
  branchSelfTaxThresholdCoordinateIdentities :=
    branchSelfTaxThresholdCoordinateIdentities
  highHigh_same_output_ledger_matches_self_tax_stream :=
    highHigh_same_output_ledger_matches_self_tax_stream
  coherenceSource := coherenceSource
  coherenceCertificate := coherenceCertificate
  lowBeatEnvelopeSource := lowBeatEnvelopeSource
  eventRecurrenceSource := eventRecurrenceSource
  continuumSource := continuumSource
  coordinateReformulation := coordinateReformulation
  coordinate_source_is_branch := coordinate_source_is_branch
  continuationSource := continuationSource
  profileLipschitzBranchIndex := profileLipschitzBranchIndex
  branch_matches_profile_lipschitz_generated_block := rfl
  branch_profile_family_self_tax_stream_declared_together :=
    branch_profile_family_self_tax_stream_declared_together
  branch_profile_family_self_tax_stream_declared_together_paid :=
    branch_profile_family_self_tax_stream_declared_together_paid
  branch_profile_family_payoff_matches_self_tax_stream :=
    branch_profile_family_payoff_matches_self_tax_stream
  branch_profile_family_price_matches_self_tax_stream :=
    branch_profile_family_price_matches_self_tax_stream
  lowHighReservePDESource := lowHighReservePDESource
  phaseLatencyProfileReserveSource := phaseLatencyProfileReserveSource
  phaseLatencyConcreteFourierSymbol := phaseLatencyConcreteFourierSymbol
  phaseLatencyControlBudget_matches_required_lipschitz :=
    phaseLatencyControlBudget_matches_required_lipschitz
  macroscopicFlatTorusClockSource := macroscopicFlatTorusClockSource

/-- Generated-branch GP216 constructor using the branch-scoped self-tax /
Lipschitz compatibility source.

This is the preferred constructor when testing the same-topology/component-LSC
route: profile payoff/price identities and threshold coordinates are supplied
by one source object for the selected generated branch, not by separate global
constant-stream arguments. -/
def gp216_bridge_composition_receipt_of_generated_branch_and_branch_compatibility
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate :
      LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource :
      GP216ContinuumAllOutputSourceBundle
        selfTaxOutputSource.stream
        eventRecurrenceSource.ledger)
    (coordinateReformulation :
      TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branchCompatibility :
      GP216GeneratedBranchSelfTaxLipschitzCompatibility
        continuationSource.handoff
        profileLipschitzBranchIndex
        selfTaxOutputSource)
    (highHigh_same_output_ledger_matches_self_tax_stream :
      highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
        selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff)
    (coordinate_source_is_branch :
      coordinateReformulation.source =
        GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
    (lowHighReservePDESource :
      GP216LowHighReservePDESourceBundle
        continuationSource.handoff)
    (phaseLatencyProfileReserveSource :
      PhaseLatencyProfileLipschitzReserveSource
        continuationSource.handoff.profile_lipschitz
        continuationSource.handoff.initialData)
    (phaseLatencyConcreteFourierSymbol :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData))
    (phaseLatencyControlBudget_matches_required_lipschitz :
      ∀ n : ℕ,
        phaseLatencyProfileReserveSource.phase.controlBudget n =
          phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n)
    (macroscopicFlatTorusClockSource :
      MacroscopicFlatTorusClockSource
        (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData
          phaseLatencyProfileReserveSource.phase
          phaseLatencyConcreteFourierSymbol
          phaseLatencyControlBudget_matches_required_lipschitz
        ).toPhaseLatencyCapacitySource) :
    GP216BridgeCompositionReceipt :=
  gp216_bridge_composition_receipt_of_generated_branch
    declaredScope
    highHighSelfTaxPDESource
    selfTaxOutputSource
    coherenceSource
    coherenceCertificate
    lowBeatEnvelopeSource
    eventRecurrenceSource
    continuumSource
    coordinateReformulation
    continuationSource
    profileLipschitzBranchIndex
    branchCompatibility.branch_is_global
    branchCompatibility.threshold_coordinate_source
    highHigh_same_output_ledger_matches_self_tax_stream
    coordinate_source_is_branch
    branchCompatibility.profile_family_self_tax_stream_declared_together
    branchCompatibility.profile_family_self_tax_stream_declared_together_paid
    branchCompatibility.profile_payoff_matches_self_tax_stream
    branchCompatibility.profile_price_matches_self_tax_stream
    lowHighReservePDESource
    phaseLatencyProfileReserveSource
    phaseLatencyConcreteFourierSymbol
    phaseLatencyControlBudget_matches_required_lipschitz
    macroscopicFlatTorusClockSource

/-- Generated-branch GP216 constructor from branch-local continuum scalar
alignment.

This is the narrowed version of the continuum scalar-alignment route.  It does
not require the continuum stream family to equal the stored GP216 self-tax
stream for every global block; it requires that equality only at the selected
generated branch.  The threshold-coordinate identity is read from the
continuum stream-family source at that same branch. -/
def gp216_bridge_receipt_of_branch_local_continuum_scalar_alignment_and_concrete_fourier_phase
    {τ : ContinuumLPProfileTopology.{u}}
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate :
      LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource :
      GP216ContinuumAllOutputSourceBundle
        selfTaxOutputSource.stream
        eventRecurrenceSource.ledger)
    (coordinateReformulation :
      TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex))
    (highHigh_same_output_ledger_matches_self_tax_stream :
      highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
        selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff)
    (coordinate_source_is_branch :
      coordinateReformulation.source =
        GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (profile_stream_alignment :
      ContinuumProfileFamilyScalarAlignmentSource
        continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source)
    (branch_stream_matches_self_tax_output :
      profile_stream_source.stream_of_block
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex) =
        selfTaxOutputSource.stream)
    (lowHighReservePDESource :
      GP216LowHighReservePDESourceBundle
        continuationSource.handoff)
    (phaseLatencyProfileReserveSource :
      PhaseLatencyProfileLipschitzReserveSource
        continuationSource.handoff.profile_lipschitz
        continuationSource.handoff.initialData)
    (phaseLatencyConcreteFourierSymbol :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData))
    (phaseLatencyControlBudget_matches_required_lipschitz :
      ∀ n : ℕ,
        phaseLatencyProfileReserveSource.phase.controlBudget n =
          phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n)
    (macroscopicFlatTorusClockSource :
      MacroscopicFlatTorusClockSource
        (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData
          phaseLatencyProfileReserveSource.phase
          phaseLatencyConcreteFourierSymbol
          phaseLatencyControlBudget_matches_required_lipschitz
        ).toPhaseLatencyCapacitySource) :
    GP216BridgeCompositionReceipt :=
  gp216_bridge_composition_receipt_of_generated_branch_and_branch_compatibility
    declaredScope
    highHighSelfTaxPDESource
    selfTaxOutputSource
    coherenceSource
    coherenceCertificate
    lowBeatEnvelopeSource
    eventRecurrenceSource
    continuumSource
    coordinateReformulation
    continuationSource
    profileLipschitzBranchIndex
    (GP216GeneratedBranchSelfTaxLipschitzCompatibility.ofContinuumScalarAlignmentAtBranch
      continuationSource.handoff
      profileLipschitzBranchIndex
      selfTaxOutputSource
      profile_stream_source
      profile_stream_alignment
      branch_is_global
      branch_stream_matches_self_tax_output)
    highHigh_same_output_ledger_matches_self_tax_stream
    coordinate_source_is_branch
    lowHighReservePDESource
    phaseLatencyProfileReserveSource
    phaseLatencyConcreteFourierSymbol
    phaseLatencyControlBudget_matches_required_lipschitz
    macroscopicFlatTorusClockSource

/-- Generated-branch GP216 constructor with profile/self-tax stream
identities as the scalar source.

This removes the two loose branch profile-family payoff/price equalities from
the final constructor surface.  The caller supplies one identity-compatibility
object for the fixed profile family and the GP216 self-tax stream; the branch
fields are then projected at the generated branch block. -/
def gp216_bridge_composition_receipt_of_generated_branch_and_profile_stream_identities
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate :
      LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource :
      GP216ContinuumAllOutputSourceBundle
        selfTaxOutputSource.stream
        eventRecurrenceSource.ledger)
    (coordinateReformulation :
      TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex))
    (branchSelfTaxThresholdCoordinateIdentities :
      BranchSelfTaxThresholdCoordinateIdentities
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
        selfTaxOutputSource.stream)
    (highHigh_same_output_ledger_matches_self_tax_stream :
      highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
        selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff)
    (coordinate_source_is_branch :
      coordinateReformulation.source =
        GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
    (profile_stream_identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
        (fun _B : FullLedgerBlock => selfTaxOutputSource.stream))
    (lowHighReservePDESource :
      GP216LowHighReservePDESourceBundle
        continuationSource.handoff)
    (phaseLatencyProfileReserveSource :
      PhaseLatencyProfileLipschitzReserveSource
        continuationSource.handoff.profile_lipschitz
        continuationSource.handoff.initialData)
    (phaseLatencyConcreteFourierSymbol :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData))
    (phaseLatencyControlBudget_matches_required_lipschitz :
      ∀ n : ℕ,
        phaseLatencyProfileReserveSource.phase.controlBudget n =
          phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n)
    (macroscopicFlatTorusClockSource :
      MacroscopicFlatTorusClockSource
        (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData
          phaseLatencyProfileReserveSource.phase
          phaseLatencyConcreteFourierSymbol
          phaseLatencyControlBudget_matches_required_lipschitz
        ).toPhaseLatencyCapacitySource) :
    GP216BridgeCompositionReceipt :=
  gp216_bridge_composition_receipt_of_generated_branch
    declaredScope
    highHighSelfTaxPDESource
    selfTaxOutputSource
    coherenceSource
    coherenceCertificate
    lowBeatEnvelopeSource
    eventRecurrenceSource
    continuumSource
    coordinateReformulation
    continuationSource
    profileLipschitzBranchIndex
    branch_is_global
    branchSelfTaxThresholdCoordinateIdentities
    highHigh_same_output_ledger_matches_self_tax_stream
    coordinate_source_is_branch
    (profile_stream_identities.profile_family_and_stream_declared_together
      (GP216GeneratedProfileLipschitzBranchBlock
        continuationSource.handoff
        profileLipschitzBranchIndex)
      branch_is_global)
    (profile_stream_identities.profile_family_and_stream_declared_together_paid
      (GP216GeneratedProfileLipschitzBranchBlock
        continuationSource.handoff
        profileLipschitzBranchIndex)
      branch_is_global)
    (by
      simpa [GP216GeneratedProfileLipschitzBranchBlock]
        using
          profile_stream_identities.payoff_matches
            (GP216GeneratedProfileLipschitzBranchBlock
              continuationSource.handoff
              profileLipschitzBranchIndex)
            branch_is_global)
    (by
      simpa [GP216GeneratedProfileLipschitzBranchBlock]
        using
          profile_stream_identities.price_matches
            (GP216GeneratedProfileLipschitzBranchBlock
              continuationSource.handoff
              profileLipschitzBranchIndex)
            branch_is_global)
    lowHighReservePDESource
    phaseLatencyProfileReserveSource
    phaseLatencyConcreteFourierSymbol
    phaseLatencyControlBudget_matches_required_lipschitz
    macroscopicFlatTorusClockSource

/-- Constructor for the final GP216 receipt from a generated profile/Lipschitz
branch whose phase source is built directly from the concrete Fourier latency
symbol.

This is the preferred source-facing final assembly route for the phase side: the
caller supplies the phase control receipt, the concrete Fourier symbol receipt,
and their entrywise identification; the generated phase-reserve source is then
constructed internally.  That prevents a detached
`PhaseLatencyProfileLipschitzReserveSource` from being paired with an unrelated
Fourier-symbol receipt. -/
def gp216_bridge_composition_receipt_of_generated_branch_and_concrete_fourier_phase
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate :
      LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource :
      GP216ContinuumAllOutputSourceBundle
        selfTaxOutputSource.stream
        eventRecurrenceSource.ledger)
    (coordinateReformulation :
      TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex))
    (branchSelfTaxThresholdCoordinateIdentities :
      BranchSelfTaxThresholdCoordinateIdentities
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
        selfTaxOutputSource.stream)
    (highHigh_same_output_ledger_matches_self_tax_stream :
      highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
        selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff)
    (coordinate_source_is_branch :
      coordinateReformulation.source =
        GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
    (branch_profile_family_self_tax_stream_declared_together : Prop)
    (branch_profile_family_self_tax_stream_declared_together_paid :
      branch_profile_family_self_tax_stream_declared_together)
    (branch_profile_family_payoff_matches_self_tax_stream :
      familyPayoff
        (continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
          (GP216GeneratedProfileLipschitzBranchBlock
            continuationSource.handoff
            profileLipschitzBranchIndex)) =
        selfTaxOutputSource.stream.payoffLimit)
    (branch_profile_family_price_matches_self_tax_stream :
      familyPrice
        (continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
          (GP216GeneratedProfileLipschitzBranchBlock
            continuationSource.handoff
            profileLipschitzBranchIndex)) =
        leraySelfTaxLimitPrice selfTaxOutputSource.stream)
    (lowHighReservePDESource :
      GP216LowHighReservePDESourceBundle
        continuationSource.handoff)
    (phase : PhaseLatencyControlGramianReceipt)
    (phaseLatencyConcreteFourierSymbol :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData))
    (phaseLatencyControlBudget_matches_required_lipschitz :
      ∀ n : ℕ,
        phase.controlBudget n =
          phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n)
    (macroscopicFlatTorusClockSource :
      MacroscopicFlatTorusClockSource
        (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData
          phase
          phaseLatencyConcreteFourierSymbol
          phaseLatencyControlBudget_matches_required_lipschitz
        ).toPhaseLatencyCapacitySource) :
    GP216BridgeCompositionReceipt :=
  gp216_bridge_composition_receipt_of_generated_branch
    declaredScope
    highHighSelfTaxPDESource
    selfTaxOutputSource
    coherenceSource
    coherenceCertificate
    lowBeatEnvelopeSource
    eventRecurrenceSource
    continuumSource
    coordinateReformulation
    continuationSource
    profileLipschitzBranchIndex
    branch_is_global
    branchSelfTaxThresholdCoordinateIdentities
    highHigh_same_output_ledger_matches_self_tax_stream
    coordinate_source_is_branch
    branch_profile_family_self_tax_stream_declared_together
    branch_profile_family_self_tax_stream_declared_together_paid
    branch_profile_family_payoff_matches_self_tax_stream
    branch_profile_family_price_matches_self_tax_stream
    lowHighReservePDESource
    (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
      continuationSource.handoff.profile_lipschitz
      continuationSource.handoff.initialData
      phase
      phaseLatencyConcreteFourierSymbol
      phaseLatencyControlBudget_matches_required_lipschitz)
    phaseLatencyConcreteFourierSymbol
    phaseLatencyControlBudget_matches_required_lipschitz
    macroscopicFlatTorusClockSource

/-- Generated-branch GP216 constructor with both compressed source routes:
profile/self-tax stream identities and concrete-Fourier phase provenance.

This is the narrow final assembly surface for the current corridor.  It does
not prove either source object; it prevents the final receipt from accepting
loose payoff/price scalar equalities or a detached phase-reserve source once
the source-level identity and Fourier-symbol witnesses are available. -/
def gp216_bridge_composition_receipt_of_generated_branch_identities_and_concrete_fourier_phase
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate :
      LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource :
      GP216ContinuumAllOutputSourceBundle
        selfTaxOutputSource.stream
        eventRecurrenceSource.ledger)
    (coordinateReformulation :
      TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex))
    (branchSelfTaxThresholdCoordinateIdentities :
      BranchSelfTaxThresholdCoordinateIdentities
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
        selfTaxOutputSource.stream)
    (highHigh_same_output_ledger_matches_self_tax_stream :
      highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
        selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff)
    (coordinate_source_is_branch :
      coordinateReformulation.source =
        GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
    (profile_stream_identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
        (fun _B : FullLedgerBlock => selfTaxOutputSource.stream))
    (lowHighReservePDESource :
      GP216LowHighReservePDESourceBundle
        continuationSource.handoff)
    (phase : PhaseLatencyControlGramianReceipt)
    (phaseLatencyConcreteFourierSymbol :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData))
    (phaseLatencyControlBudget_matches_required_lipschitz :
      ∀ n : ℕ,
        phase.controlBudget n =
          phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n)
    (macroscopicFlatTorusClockSource :
      MacroscopicFlatTorusClockSource
        (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData
          phase
          phaseLatencyConcreteFourierSymbol
          phaseLatencyControlBudget_matches_required_lipschitz
        ).toPhaseLatencyCapacitySource) :
    GP216BridgeCompositionReceipt :=
  gp216_bridge_composition_receipt_of_generated_branch_and_profile_stream_identities
    declaredScope
    highHighSelfTaxPDESource
    selfTaxOutputSource
    coherenceSource
    coherenceCertificate
    lowBeatEnvelopeSource
    eventRecurrenceSource
    continuumSource
    coordinateReformulation
    continuationSource
    profileLipschitzBranchIndex
    branch_is_global
    branchSelfTaxThresholdCoordinateIdentities
    highHigh_same_output_ledger_matches_self_tax_stream
    coordinate_source_is_branch
    profile_stream_identities
    lowHighReservePDESource
    (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
      continuationSource.handoff.profile_lipschitz
      continuationSource.handoff.initialData
      phase
      phaseLatencyConcreteFourierSymbol
      phaseLatencyControlBudget_matches_required_lipschitz)
    phaseLatencyConcreteFourierSymbol
    phaseLatencyControlBudget_matches_required_lipschitz
    macroscopicFlatTorusClockSource

/-- Generated-branch GP216 constructor with source-family stream identities.

Many source-facing profile decompositions naturally produce identities for a
block-indexed stream family, while GP216 stores one audited output stream.  This
constructor keeps that mismatch honest: callers provide the identity receipt
for the source family and a same-global-block equality to the stored output
stream.  The equality is the load-bearing provenance bridge; this theorem only
transports the existing identity receipt to the constant-stream API. -/
def gp216_bridge_receipt_of_stream_family_identities_and_concrete_fourier_phase
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate :
      LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource :
      GP216ContinuumAllOutputSourceBundle
        selfTaxOutputSource.stream
        eventRecurrenceSource.ledger)
    (coordinateReformulation :
      TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex))
    (branchSelfTaxThresholdCoordinateIdentities :
      BranchSelfTaxThresholdCoordinateIdentities
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
        selfTaxOutputSource.stream)
    (highHigh_same_output_ledger_matches_self_tax_stream :
      highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
        selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff)
    (coordinate_source_is_branch :
      coordinateReformulation.source =
        GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (profile_stream_identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
        stream_of_block)
    (stream_matches_self_tax_output :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        stream_of_block B = selfTaxOutputSource.stream)
    (lowHighReservePDESource :
      GP216LowHighReservePDESourceBundle
        continuationSource.handoff)
    (phase : PhaseLatencyControlGramianReceipt)
    (phaseLatencyConcreteFourierSymbol :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData))
    (phaseLatencyControlBudget_matches_required_lipschitz :
      ∀ n : ℕ,
        phase.controlBudget n =
          phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n)
    (macroscopicFlatTorusClockSource :
      MacroscopicFlatTorusClockSource
        (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData
          phase
          phaseLatencyConcreteFourierSymbol
          phaseLatencyControlBudget_matches_required_lipschitz
        ).toPhaseLatencyCapacitySource) :
    GP216BridgeCompositionReceipt :=
  gp216_bridge_composition_receipt_of_generated_branch_identities_and_concrete_fourier_phase
    declaredScope
    highHighSelfTaxPDESource
    selfTaxOutputSource
    coherenceSource
    coherenceCertificate
    lowBeatEnvelopeSource
    eventRecurrenceSource
    continuumSource
    coordinateReformulation
    continuationSource
    profileLipschitzBranchIndex
    branch_is_global
    branchSelfTaxThresholdCoordinateIdentities
    highHigh_same_output_ledger_matches_self_tax_stream
    coordinate_source_is_branch
    (profile_family_self_tax_stream_identity_compatibility_to_constant_stream
      selfTaxOutputSource.stream
      profile_stream_identities
      stream_matches_self_tax_output)
    lowHighReservePDESource
    phase
    phaseLatencyConcreteFourierSymbol
    phaseLatencyControlBudget_matches_required_lipschitz
    macroscopicFlatTorusClockSource

/-- Generated-branch GP216 constructor from continuum all-output scalar
alignment.

This is the current shortest non-circular stream-identity lane: the continuum
source supplies the Leray self-tax stream family, the scalar-alignment source
pays the exact profile payoff/price identities, and a separate same-stream
bridge identifies those block streams with GP216's stored audited output
stream. -/
def gp216_bridge_receipt_of_continuum_scalar_alignment_and_concrete_fourier_phase
    {τ : ContinuumLPProfileTopology.{u}}
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate :
      LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource :
      GP216ContinuumAllOutputSourceBundle
        selfTaxOutputSource.stream
        eventRecurrenceSource.ledger)
    (coordinateReformulation :
      TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex))
    (branchSelfTaxThresholdCoordinateIdentities :
      BranchSelfTaxThresholdCoordinateIdentities
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
        selfTaxOutputSource.stream)
    (highHigh_same_output_ledger_matches_self_tax_stream :
      highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
        selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff)
    (coordinate_source_is_branch :
      coordinateReformulation.source =
        GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
    (profile_stream_source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (profile_stream_alignment :
      ContinuumProfileFamilyScalarAlignmentSource
        continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
        profile_stream_source)
    (stream_matches_self_tax_output :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        profile_stream_source.stream_of_block B = selfTaxOutputSource.stream)
    (lowHighReservePDESource :
      GP216LowHighReservePDESourceBundle
        continuationSource.handoff)
    (phase : PhaseLatencyControlGramianReceipt)
    (phaseLatencyConcreteFourierSymbol :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData))
    (phaseLatencyControlBudget_matches_required_lipschitz :
      ∀ n : ℕ,
        phase.controlBudget n =
          phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n)
    (macroscopicFlatTorusClockSource :
      MacroscopicFlatTorusClockSource
        (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData
          phase
          phaseLatencyConcreteFourierSymbol
          phaseLatencyControlBudget_matches_required_lipschitz
        ).toPhaseLatencyCapacitySource) :
    GP216BridgeCompositionReceipt :=
  gp216_bridge_receipt_of_stream_family_identities_and_concrete_fourier_phase
    declaredScope
    highHighSelfTaxPDESource
    selfTaxOutputSource
    coherenceSource
    coherenceCertificate
    lowBeatEnvelopeSource
    eventRecurrenceSource
    continuumSource
    coordinateReformulation
    continuationSource
    profileLipschitzBranchIndex
    branch_is_global
    branchSelfTaxThresholdCoordinateIdentities
    highHigh_same_output_ledger_matches_self_tax_stream
    coordinate_source_is_branch
    profile_stream_source.stream_of_block
    (profile_family_self_tax_stream_identity_compatibility_of_continuum_scalar_alignment_source
      profile_stream_alignment)
    stream_matches_self_tax_output
    lowHighReservePDESource
    phase
    phaseLatencyConcreteFourierSymbol
    phaseLatencyControlBudget_matches_required_lipschitz
    macroscopicFlatTorusClockSource

/-- Generated-branch GP216 constructor with all currently source-first
compression applied.

Compared with
`gp216_bridge_composition_receipt_of_generated_branch_identities_and_concrete_fourier_phase`,
this version does not accept a prebuilt macroscopic flat-torus clock source.
It builds that clock from the Fourier/Killing source, the typed LP/Bony
Lipschitz-reserve source, and the concrete Fourier phase receipt.  The hard
phase-capacity inequality still lives in `phase.parabolic_low_high_capacity`;
this constructor only prevents a detached clock source from being paired with
the final bridge. -/
def gp216_bridge_composition_receipt_of_generated_branch_source_first
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate :
      LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource :
      GP216ContinuumAllOutputSourceBundle
        selfTaxOutputSource.stream
        eventRecurrenceSource.ledger)
    (coordinateReformulation :
      TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex))
    (branchSelfTaxThresholdCoordinateIdentities :
      BranchSelfTaxThresholdCoordinateIdentities
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
        selfTaxOutputSource.stream)
    (highHigh_same_output_ledger_matches_self_tax_stream :
      highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
        selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff)
    (coordinate_source_is_branch :
      coordinateReformulation.source =
        GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
    (profile_stream_identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
        (fun _B : FullLedgerBlock => selfTaxOutputSource.stream))
    (lowHighReservePDESource :
      GP216LowHighReservePDESourceBundle
        continuationSource.handoff)
    (phase : PhaseLatencyControlGramianReceipt)
    (phaseLatencyConcreteFourierSymbol :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData))
    (phaseLatencyControlBudget_matches_required_lipschitz :
      ∀ n : ℕ,
        phase.controlBudget n =
          phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n)
    (duhamelReceipt : LowHighDuhamelBernsteinReceipt)
    (viscousShellGuard :
      LowHighDuhamelViscousShellGuard duhamelReceipt)
    (flatTorusFourierSource : FlatTorusSmoothKillingFourierSource)
    (lowHighLedger : LowHighKinematicDichotomyLedger)
    (lpBonyReserveSource :
      LowHighLPBonyUnpaidEstimateReceipt lowHighLedger)
    (lipschitzLedger : LowFrequencyLipschitzLedger)
    (lipschitzCert :
      LowFrequencyLipschitzAuditedControlCertificate lipschitzLedger)
    (flatTorusReserveIndex : ℕ)
    (lipschitzReserveLink :
      LowHighLipschitzReserveLink
        lowHighLedger
        lpBonyReserveSource
        lipschitzLedger
        flatTorusReserveIndex)
    (flatTorusBlockNoSurvivor :
      FullLedgerNoSurvivor (lipschitzLedger.block flatTorusReserveIndex))
    (lp_bony_constant_declared_before_payoff_paid :
      lpBonyReserveSource.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      lpBonyReserveSource.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      lpBonyReserveSource.high_shell_energy_declared_before_payoff)
    (fixed_flat_torus_phase_symbol_topology : Prop)
    (fixed_flat_torus_phase_symbol_topology_paid :
      fixed_flat_torus_phase_symbol_topology)
    (phase_reach_identified_with_viscous_killing_clock : Prop)
    (phase_reach_identified_with_viscous_killing_clock_paid :
      phase_reach_identified_with_viscous_killing_clock)
    (macroscopic_clock_budget_charged_in_trackb_reserve : Prop)
    (macroscopic_clock_budget_charged_in_trackb_reserve_paid :
      macroscopic_clock_budget_charged_in_trackb_reserve) :
    GP216BridgeCompositionReceipt :=
  gp216_bridge_composition_receipt_of_generated_branch_identities_and_concrete_fourier_phase
    declaredScope
    highHighSelfTaxPDESource
    selfTaxOutputSource
    coherenceSource
    coherenceCertificate
    lowBeatEnvelopeSource
    eventRecurrenceSource
    continuumSource
    coordinateReformulation
    continuationSource
    profileLipschitzBranchIndex
    branch_is_global
    branchSelfTaxThresholdCoordinateIdentities
    highHigh_same_output_ledger_matches_self_tax_stream
    coordinate_source_is_branch
    profile_stream_identities
    lowHighReservePDESource
    phase
    phaseLatencyConcreteFourierSymbol
    phaseLatencyControlBudget_matches_required_lipschitz
    (macroscopic_flat_torus_clock_source_of_smooth_fourier_and_typed_audited_lipschitz_reserve
      (P :=
        (phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData
          phase
          phaseLatencyConcreteFourierSymbol
          phaseLatencyControlBudget_matches_required_lipschitz
        ).toPhaseLatencyCapacitySource)
      duhamelReceipt
      viscousShellGuard
      flatTorusFourierSource
      lowHighLedger
      lpBonyReserveSource
      lipschitzLedger
      lipschitzCert
      flatTorusReserveIndex
      lipschitzReserveLink
      flatTorusBlockNoSurvivor
      lp_bony_constant_declared_before_payoff_paid
      lipschitz_cost_declared_before_payoff_paid
      high_shell_energy_declared_before_payoff_paid
      fixed_flat_torus_phase_symbol_topology
      fixed_flat_torus_phase_symbol_topology_paid
      phase_reach_identified_with_viscous_killing_clock
      phase_reach_identified_with_viscous_killing_clock_paid
      macroscopic_clock_budget_charged_in_trackb_reserve
      macroscopic_clock_budget_charged_in_trackb_reserve_paid)

/-- Fully source-facing GP216 assembly for the current corridor.

This combines the two non-tautological compressions above: profile/self-tax
identities may come from a source stream family that is merely proved equal to
the stored GP216 output stream on global blocks, and the macroscopic flat-torus
clock is built from Fourier/Killing plus typed LP/Bony reserve sources. -/
def gp216_bridge_receipt_of_stream_family_identities_source_first
    (declaredScope : Prop)
    (highHighSelfTaxPDESource : GP216HighHighSelfTaxPDESourceBundle)
    (selfTaxOutputSource : GP216SelfTaxAuditedOutputSourceBundle)
    (coherenceSource : LPBeatBackscatterChargeStreamSource)
    (coherenceCertificate :
      LPBeatBackscatterLimitCertificate coherenceSource.stream)
    (lowBeatEnvelopeSource : GP216LowBeatEnvelopeSourceBundle)
    (eventRecurrenceSource : GP216EventRecurrenceSourceBundle)
    (continuumSource :
      GP216ContinuumAllOutputSourceBundle
        selfTaxOutputSource.stream
        eventRecurrenceSource.ledger)
    (coordinateReformulation :
      TrackBCoordinateReformulationReceipt)
    (continuationSource : GP216ContinuationSourceBundle)
    (profileLipschitzBranchIndex : ℕ)
    (branch_is_global :
      IsGlobalTrackBBlock
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex))
    (branchSelfTaxThresholdCoordinateIdentities :
      BranchSelfTaxThresholdCoordinateIdentities
        (GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
        selfTaxOutputSource.stream)
    (highHigh_same_output_ledger_matches_self_tax_stream :
      highHighSelfTaxPDESource.obligation.same_leray_output_ledger_declared_before_payoff ↔
        selfTaxOutputSource.stream.limitComponentPricesDeclaredBeforePayoff)
    (coordinate_source_is_branch :
      coordinateReformulation.source =
        GP216GeneratedProfileLipschitzBranchBlock
          continuationSource.handoff
          profileLipschitzBranchIndex)
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (profile_stream_identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        continuationSource.handoff.profile_lipschitz.profile_bundle.profile_family_of_block
        stream_of_block)
    (stream_matches_self_tax_output :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        stream_of_block B = selfTaxOutputSource.stream)
    (lowHighReservePDESource :
      GP216LowHighReservePDESourceBundle
        continuationSource.handoff)
    (phase : PhaseLatencyControlGramianReceipt)
    (phaseLatencyConcreteFourierSymbol :
      ConcreteFourierLatencySymbolReceipt
        (trackBGeneratedLowFrequencyLipschitzLedger
          continuationSource.handoff.profile_lipschitz
          continuationSource.handoff.initialData))
    (phaseLatencyControlBudget_matches_required_lipschitz :
      ∀ n : ℕ,
        phase.controlBudget n =
          phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n)
    (duhamelReceipt : LowHighDuhamelBernsteinReceipt)
    (viscousShellGuard :
      LowHighDuhamelViscousShellGuard duhamelReceipt)
    (flatTorusFourierSource : FlatTorusSmoothKillingFourierSource)
    (lowHighLedger : LowHighKinematicDichotomyLedger)
    (lpBonyReserveSource :
      LowHighLPBonyUnpaidEstimateReceipt lowHighLedger)
    (lipschitzLedger : LowFrequencyLipschitzLedger)
    (lipschitzCert :
      LowFrequencyLipschitzAuditedControlCertificate lipschitzLedger)
    (flatTorusReserveIndex : ℕ)
    (lipschitzReserveLink :
      LowHighLipschitzReserveLink
        lowHighLedger
        lpBonyReserveSource
        lipschitzLedger
        flatTorusReserveIndex)
    (flatTorusBlockNoSurvivor :
      FullLedgerNoSurvivor (lipschitzLedger.block flatTorusReserveIndex))
    (lp_bony_constant_declared_before_payoff_paid :
      lpBonyReserveSource.lp_bony_constant_declared_before_payoff)
    (lipschitz_cost_declared_before_payoff_paid :
      lpBonyReserveSource.lipschitz_cost_declared_before_payoff)
    (high_shell_energy_declared_before_payoff_paid :
      lpBonyReserveSource.high_shell_energy_declared_before_payoff)
    (fixed_flat_torus_phase_symbol_topology : Prop)
    (fixed_flat_torus_phase_symbol_topology_paid :
      fixed_flat_torus_phase_symbol_topology)
    (phase_reach_identified_with_viscous_killing_clock : Prop)
    (phase_reach_identified_with_viscous_killing_clock_paid :
      phase_reach_identified_with_viscous_killing_clock)
    (macroscopic_clock_budget_charged_in_trackb_reserve : Prop)
    (macroscopic_clock_budget_charged_in_trackb_reserve_paid :
      macroscopic_clock_budget_charged_in_trackb_reserve) :
    GP216BridgeCompositionReceipt :=
  gp216_bridge_composition_receipt_of_generated_branch_source_first
    declaredScope
    highHighSelfTaxPDESource
    selfTaxOutputSource
    coherenceSource
    coherenceCertificate
    lowBeatEnvelopeSource
    eventRecurrenceSource
    continuumSource
    coordinateReformulation
    continuationSource
    profileLipschitzBranchIndex
    branch_is_global
    branchSelfTaxThresholdCoordinateIdentities
    highHigh_same_output_ledger_matches_self_tax_stream
    coordinate_source_is_branch
    (profile_family_self_tax_stream_identity_compatibility_to_constant_stream
      selfTaxOutputSource.stream
      profile_stream_identities
      stream_matches_self_tax_output)
    lowHighReservePDESource
    phase
    phaseLatencyConcreteFourierSymbol
    phaseLatencyControlBudget_matches_required_lipschitz
    duhamelReceipt
    viscousShellGuard
    flatTorusFourierSource
    lowHighLedger
    lpBonyReserveSource
    lipschitzLedger
    lipschitzCert
    flatTorusReserveIndex
    lipschitzReserveLink
    flatTorusBlockNoSurvivor
    lp_bony_constant_declared_before_payoff_paid
    lipschitz_cost_declared_before_payoff_paid
    high_shell_energy_declared_before_payoff_paid
    fixed_flat_torus_phase_symbol_topology
    fixed_flat_torus_phase_symbol_topology_paid
    phase_reach_identified_with_viscous_killing_clock
    phase_reach_identified_with_viscous_killing_clock_paid
    macroscopic_clock_budget_charged_in_trackb_reserve
    macroscopic_clock_budget_charged_in_trackb_reserve_paid

/-- The GP216 concrete-Fourier profile phase source is derived from the
generated phase source plus the same generated Fourier-symbol receipt. -/
def GP216BridgeCompositionReceipt.phaseLatencyConcreteFourierReserveSource
    (R : GP216BridgeCompositionReceipt) :
    PhaseLatencyProfileLipschitzReserveSource
      R.continuationSource.handoff.profile_lipschitz
      R.continuationSource.handoff.initialData :=
  phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol
    R.continuationSource.handoff.profile_lipschitz
    R.continuationSource.handoff.initialData
    R.phaseLatencyProfileReserveSource.phase
    R.phaseLatencyConcreteFourierSymbol
    R.phaseLatencyControlBudget_matches_required_lipschitz

/-- The stored GP216 phase-reserve source is the same source as the one
reconstructed from the concrete Fourier symbol receipt.

This prevents the final receipt from silently carrying two phase-reserve
objects with the same phase but different ledger provenance. -/
theorem GP216BridgeCompositionReceipt.phaseLatencyReserveSource_eq_concreteFourierSource
    (R : GP216BridgeCompositionReceipt) :
    R.phaseLatencyProfileReserveSource =
      R.phaseLatencyConcreteFourierReserveSource := by
  cases hS : R.phaseLatencyProfileReserveSource
  simp [GP216BridgeCompositionReceipt.phaseLatencyConcreteFourierReserveSource,
    phase_latency_profile_lipschitz_reserve_source_of_concrete_fourier_symbol,
    hS]

/-- The stored GP216 phase-control budget is exactly the concrete Fourier
symbol's required low-frequency Lipschitz schedule.

This is a named projection of a source equality already carried by
`GP216BridgeCompositionReceipt`; it is not a new estimate. -/
theorem GP216BridgeCompositionReceipt.phaseLatencyControlBudget_eq_requiredLowLipschitz
    (R : GP216BridgeCompositionReceipt)
    (n : ℕ) :
    R.phaseLatencyProfileReserveSource.phase.controlBudget n =
      R.phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n :=
  R.phaseLatencyControlBudget_matches_required_lipschitz n

/-- The concrete Fourier latency receipt embeds its required low-frequency
Lipschitz cost in the generated profile/Lipschitz ledger.

This is only a projection of the stored Fourier-symbol source; it exposes the
source edge so phase-latency consumers do not need to reconstruct the generated
ledger identity by hand. -/
theorem GP216BridgeCompositionReceipt.phaseLatencyRequiredLowLipschitz_le_lipschitzCost
    (R : GP216BridgeCompositionReceipt)
    (n : ℕ) :
    R.phaseLatencyConcreteFourierSymbol.requiredLowLipschitz n ≤
      (trackBGeneratedLowFrequencyLipschitzLedger
        R.continuationSource.handoff.profile_lipschitz
        R.continuationSource.handoff.initialData).lipschitzCost n :=
  R.phaseLatencyConcreteFourierSymbol.required_lipschitz_embeds_in_lipschitz_ledger n

/-- The stored GP216 phase control budget is priced by the generated
profile/Lipschitz ledger.

The proof routes through the mandatory concrete-Fourier/source equality rather
than assuming a detached phase reserve budget. -/
theorem GP216BridgeCompositionReceipt.phaseLatencyControlBudget_le_lipschitzCost
    (R : GP216BridgeCompositionReceipt)
    (n : ℕ) :
    R.phaseLatencyProfileReserveSource.phase.controlBudget n ≤
      (trackBGeneratedLowFrequencyLipschitzLedger
        R.continuationSource.handoff.profile_lipschitz
        R.continuationSource.handoff.initialData).lipschitzCost n :=
  R.phaseLatencyProfileReserveSource.phase_control_embeds_in_generated_lipschitz_ledger n

/-- The GP216 phase-latency Lipschitz reserve is derived from the generated
profile/Lipschitz phase source and the concrete Fourier-symbol receipt, not
stored as an arbitrary bridge. -/
def GP216BridgeCompositionReceipt.phaseLatencyLipschitzReserve
    (R : GP216BridgeCompositionReceipt) :
    PhaseLatencyLipschitzReserveBridge :=
  R.phaseLatencyConcreteFourierReserveSource.toPhaseLatencyLipschitzReserveBridge

/-- The GP216 phase-latency capacity source, before importing generated
no-survivor pricing. -/
def GP216BridgeCompositionReceipt.phaseLatencyCapacitySource
    (R : GP216BridgeCompositionReceipt) :
    PhaseLatencyLipschitzCapacitySource :=
  R.phaseLatencyConcreteFourierReserveSource.toPhaseLatencyCapacitySource

/-- GP216 flat-torus phase-capacity bundle projected from the mandatory
macroscopic clock source.

The composite receipt stores the stronger source object, so Duhamel/viscous
shell provenance is no longer optional at the final bridge boundary.  Older
downstream code can still consume the existing bundle interface through this
projection. -/
def GP216BridgeCompositionReceipt.flatTorusPhaseCapacitySource
    (R : GP216BridgeCompositionReceipt) :
    GP216FlatTorusPhaseCapacitySourceBundle
      R.phaseLatencyCapacitySource :=
  GP216FlatTorusPhaseCapacitySourceBundle.ofMacroscopicClockSource
    R.macroscopicFlatTorusClockSource

/-- The GP216 self-tax scalar stream is projected from the audited Leray-output
source bundle, not stored as a detachable field. -/
def GP216BridgeCompositionReceipt.selfTaxStream
    (R : GP216BridgeCompositionReceipt) :
    LeraySelfTaxProfilePriceStream :=
  R.selfTaxOutputSource.stream

/-- The GP216 audited Leray-output source receipt is projected from the same
bundle that provides the scalar stream. -/
def GP216BridgeCompositionReceipt.selfTaxOutputLimitSource
    (R : GP216BridgeCompositionReceipt) :
    LeraySelfTaxOutputLimitPassageAuditedSourceReceipt
      R.selfTaxStream :=
  R.selfTaxOutputSource.audited_source

/-- The self-tax payoff-to-limit charge is projected from the same audited
bundle that supplies the scalar stream to the GP216 receipt. -/
theorem GP216BridgeCompositionReceipt.selfTaxOutputSource_payoff_le_limitPrice
    (R : GP216BridgeCompositionReceipt) :
    R.selfTaxStream.payoffLimit ≤
      leraySelfTaxLimitPrice R.selfTaxStream :=
  R.selfTaxOutputSource.payoff_le_limitPrice

/-- The GP216 continuation handoff is projected from the bundle that also
carries its smoothness and finite-energy prerequisites. -/
def GP216BridgeCompositionReceipt.continuationHandoff
    (R : GP216BridgeCompositionReceipt) :
    TrackBContinuationHandoffReceipt :=
  R.continuationSource.handoff

/-- Smoothness prerequisite projected from the continuation source bundle. -/
def GP216BridgeCompositionReceipt.continuation_smooth
    (R : GP216BridgeCompositionReceipt) :
    R.continuationHandoff.self_tax_enstrophy.evolution.smoothOnLocalInterval :=
  R.continuationHandoff.same_evolution.smooth_iff.mp
    R.continuationSource.profile_smooth

/-- Finite-energy prerequisite projected from the continuation source bundle.
-/
def GP216BridgeCompositionReceipt.continuation_energy
    (R : GP216BridgeCompositionReceipt) :
    R.continuationHandoff.self_tax_enstrophy.evolution.finiteEnergyInequality :=
  R.continuationHandoff.same_evolution.energy_iff.mp
    R.continuationSource.profile_energy

/-- High-high PDE obligation projected from its paid source bundle. -/
def GP216BridgeCompositionReceipt.highHighSelfTaxPDEObligation
    (R : GP216BridgeCompositionReceipt) :
    HighHighSelfTaxPDEObligation :=
  R.highHighSelfTaxPDESource.obligation

/-- High-high PDE satisfaction projected from the same source bundle as the
obligation. -/
def GP216BridgeCompositionReceipt.highHighSelfTaxPDEObligationSatisfied
    (R : GP216BridgeCompositionReceipt) :
    HighHighSelfTaxPDEObligationSatisfied
      R.highHighSelfTaxPDEObligation :=
  R.highHighSelfTaxPDESource.satisfied

/-- The GP216 profile/Lipschitz obligation is the one carried by the concrete
continuation handoff, not a detached copy plus equality proof. -/
def GP216BridgeCompositionReceipt.profileLipschitzObligation
    (R : GP216BridgeCompositionReceipt) :
    TrackBProfileLipschitzControlObligation :=
  R.continuationHandoff.profile_lipschitz

/-- The GP216 initial datum is the one carried by the concrete continuation
handoff, not a detached copy plus equality proof. -/
def GP216BridgeCompositionReceipt.profileLipschitzInitialData
    (R : GP216BridgeCompositionReceipt) :
    SmoothNSInitialData :=
  R.continuationHandoff.initialData

/-- The profile family used by the GP216 branch is projected from the generated
profile/Lipschitz obligation, not supplied as a detached scalar family. -/
def GP216BridgeCompositionReceipt.branchProfileFamily
    (R : GP216BridgeCompositionReceipt) :
    PricingProfileFamily :=
  R.profileLipschitzObligation.profile_bundle.profile_family_of_block
    R.branchBlock

/-- Profile-side smoothness prerequisite projected from the continuation
source bundle. -/
def GP216BridgeCompositionReceipt.profile_lipschitz_smooth
    (R : GP216BridgeCompositionReceipt) :
    (R.profileLipschitzObligation.evolution_of_initial_data
      R.profileLipschitzInitialData).smoothOnLocalInterval :=
  R.continuationSource.profile_smooth

/-- Profile-side finite-energy prerequisite projected from the continuation
source bundle. -/
def GP216BridgeCompositionReceipt.profile_lipschitz_energy
    (R : GP216BridgeCompositionReceipt) :
    (R.profileLipschitzObligation.evolution_of_initial_data
      R.profileLipschitzInitialData).finiteEnergyInequality :=
  R.continuationSource.profile_energy

/-- Low-high Lipschitz reserve PDE obligation projected from its source
bundle. -/
def GP216BridgeCompositionReceipt.lowHighLipschitzReservePDEObligation
    (R : GP216BridgeCompositionReceipt) :
    LowHighLipschitzReservePDEObligation :=
  R.lowHighReservePDESource.obligation

/-- Low-high Lipschitz reserve PDE satisfaction projected from the same source
bundle as the obligation. -/
def GP216BridgeCompositionReceipt.lowHighLipschitzReservePDEObligationSatisfied
    (R : GP216BridgeCompositionReceipt) :
    LowHighLipschitzReservePDEObligationSatisfied
      R.lowHighLipschitzReservePDEObligation :=
  R.lowHighReservePDESource.satisfied

/-- The low-high smooth limit/reserve preservation duty is projected from the
same energy-budget PDE handoff that satisfies the GP216 low-high reserve
obligation. -/
theorem GP216BridgeCompositionReceipt.lowHighSmoothLimitPreservesCostAndReserve
    (R : GP216BridgeCompositionReceipt) :
    R.lowHighLipschitzReservePDEObligation.smooth_limit_preserves_cost_and_reserve :=
  smooth_limit_preserves_cost_and_reserve_of_energy_budget_shell_pde_handoff
    R.lowHighReservePDESource.energyBudgetPDEHandoff

/-- Generated low-high shell reserve closure projected from the same source
bundle as the low-high PDE checklist. -/
def GP216BridgeCompositionReceipt.lowHighEnergyBudgetShellReserveClosure
    (R : GP216BridgeCompositionReceipt) :
    LowHighEnergyBudgetShellReserveClosure
      (trackBGeneratedLowFrequencyLipschitzLedger
        R.profileLipschitzObligation
        R.profileLipschitzInitialData) :=
  R.lowHighReservePDESource.energyBudgetShellReserveClosure

/-- The GP216 coherence stream is the stream carried by the named LP/Leray
source.  It is derived rather than stored as a detached scalar stream. -/
def GP216BridgeCompositionReceipt.coherenceStream
    (R : GP216BridgeCompositionReceipt) :
    LPBeatBackscatterChargeStream :=
  R.coherenceSource.stream

/-- Reflexive source receipt for the derived GP216 coherence stream. -/
def GP216BridgeCompositionReceipt.coherenceSourceReceipt
    (R : GP216BridgeCompositionReceipt) :
    LPBeatBackscatterDerivedStreamReceipt
      R.coherenceSource
      R.coherenceStream :=
  lpBeatBackscatterDerivedStreamReceiptRefl R.coherenceSource

/-- GP216 consumes coherence through the named source package, not through a
detached scalar limit inequality. -/
def GP216PositiveCoherenceUniformlyPaid
    (R : GP216BridgeCompositionReceipt) : Prop :=
  LPBeatBackscatterSourceUniformPositiveCoherencePaid R.coherenceSource ∧
    R.coherenceSource.stream.payoffLimit ≤
      R.coherenceSource.stream.priceLimit ∧
    ¬ LPBeatBackscatterPrefixPayoffUnbounded R.coherenceSource.stream

/-- The GP216 low-beat stream is projected from the finite-reserve bundle that
also carries the reserve cap. -/
def GP216BridgeCompositionReceipt.lowBeatStream
    (R : GP216BridgeCompositionReceipt) :
    LowBeatPrefixReserveStream :=
  R.lowBeatEnvelopeSource.finiteReserve.stream

/-- The GP216 low-beat reserve limit is projected from the same bundle as the
stream it bounds. -/
def GP216BridgeCompositionReceipt.lowBeatReserveLimit
    (R : GP216BridgeCompositionReceipt) : Real :=
  R.lowBeatEnvelopeSource.finiteReserve.reserveLimit

/-- The GP216 low-beat reserve bound is projected from the finite-reserve
bundle, preventing detached stream/bound substitutions. -/
def GP216BridgeCompositionReceipt.lowBeatReserveBounded
    (R : GP216BridgeCompositionReceipt) :
    ∀ n : ℕ, R.lowBeatStream.prefixReservePrice n ≤
      R.lowBeatReserveLimit :=
  R.lowBeatEnvelopeSource.finiteReserve.reserveBounded

/-- The GP216 fixed-prefix low-beat envelope is projected from the same
low-beat source bundle as the finite reserve stream. -/
def GP216BridgeCompositionReceipt.fixedPrefixLowBeat
    (R : GP216BridgeCompositionReceipt) :
    VanishingFixedPrefixLowBeatEnvelope :=
  R.lowBeatEnvelopeSource.fixedPrefix

/-- The GP216 moving/all-output low-beat envelope is projected from the same
low-beat source bundle as the finite reserve stream. -/
def GP216BridgeCompositionReceipt.movingAllOutputLowBeat
    (R : GP216BridgeCompositionReceipt) :
    MovingAllOutputLowBeatEnvelope :=
  R.lowBeatEnvelopeSource.movingAllOutput

/-- The GP216 event recurrence ledger is projected from the source bundle that
also carries the recurrence PDE and certificate receipts. -/
def GP216BridgeCompositionReceipt.eventRecurrence
    (R : GP216BridgeCompositionReceipt) :
    EventRecurrencePriceLedger :=
  R.eventRecurrenceSource.ledger

/-- The GP216 event PDE obligation is projected from the same source bundle as
the recurrence ledger. -/
def GP216BridgeCompositionReceipt.eventRecurrencePDEObligation
    (R : GP216BridgeCompositionReceipt) :
    EventRecurrencePricePDEObligation :=
  R.eventRecurrenceSource.pdeObligation

/-- Paid event PDE duties projected from the event-recurrence source bundle. -/
def GP216BridgeCompositionReceipt.eventRecurrencePDEObligationSatisfied
    (R : GP216BridgeCompositionReceipt) :
    EventRecurrencePricePDEObligationSatisfied
      R.eventRecurrencePDEObligation :=
  R.eventRecurrenceSource.pdeSatisfied

/-- Auxiliary hostile-search panels projected from the event source bundle. -/
def GP216BridgeCompositionReceipt.eventRecurrenceAuxiliaryPanels
    (R : GP216BridgeCompositionReceipt) :
    GP216EventRecurrenceAuxiliaryPanelBundle :=
  R.eventRecurrenceSource.auxiliaryPanels

/-- Reserve/gain decoupling panel projected from the event source bundle. -/
def GP216BridgeCompositionReceipt.reserveGainDecouplingSearch
    (R : GP216BridgeCompositionReceipt) :
    ReserveGainDecouplingSearchReceipt :=
  R.eventRecurrenceAuxiliaryPanels.reserveGainDecouplingSearch

/-- Matrix reserve/gain decoupling audit projected from the event source
bundle. -/
def GP216BridgeCompositionReceipt.matrixReserveGainDecouplingAudit
    (R : GP216BridgeCompositionReceipt) :
    MatrixReserveGainDecouplingAuditReceipt :=
  R.eventRecurrenceAuxiliaryPanels.matrixReserveGainDecouplingAudit

/-- Setup-latency execution-cost panel projected from the event source bundle.
-/
def GP216BridgeCompositionReceipt.setupLatencyExecutionCost
    (R : GP216BridgeCompositionReceipt) :
    SetupLatencyExecutionCostReceipt :=
  R.eventRecurrenceAuxiliaryPanels.setupLatencyExecutionCost

/-- Dynamic latency counterexample-search panel projected from the event source
bundle. -/
def GP216BridgeCompositionReceipt.dynamicLatencyCounterexampleSearch
    (R : GP216BridgeCompositionReceipt) :
    DynamicLatencyCounterexampleSearchReceipt :=
  R.eventRecurrenceAuxiliaryPanels.dynamicLatencyCounterexampleSearch

/-- Smooth latency PDE-obligation falsifier panel projected from the event
source bundle. -/
def GP216BridgeCompositionReceipt.smoothLatencyPDEObligationFalsifier
    (R : GP216BridgeCompositionReceipt) :
    SmoothLatencyPDEObligationFalsifierReceipt :=
  R.eventRecurrenceAuxiliaryPanels.smoothLatencyPDEObligationFalsifier

/-- Concrete Fourier latency falsifier panel projected from the event source
bundle. -/
def GP216BridgeCompositionReceipt.concreteFourierLatencyFalsifier
    (R : GP216BridgeCompositionReceipt) :
    ConcreteFourierLatencyFalsifierReceipt :=
  R.eventRecurrenceAuxiliaryPanels.concreteFourierLatencyFalsifier

/-- Event-section incidence projected from the source bundle, keeping the same
ledger as the dynamic recurrence certificate. -/
def GP216BridgeCompositionReceipt.eventSectionIncidence
    (R : GP216BridgeCompositionReceipt) :
    EventSectionIncidenceReceipt R.eventRecurrence :=
  R.eventRecurrenceSource.sectionIncidence

/-- Dynamic event-recurrence price certificate projected from the source
bundle. -/
def GP216BridgeCompositionReceipt.eventRecurrenceCertificate
    (R : GP216BridgeCompositionReceipt) :
    EventDynamicRecurrencePriceCertificate R.eventRecurrence :=
  R.eventRecurrenceSource.certificate

/-- Budget-product bound for finite event-gain prefixes, projected at the
GP216 composition boundary.  This exposes the event-recurrence contribution
without using it as a branch threshold-coordinate constructor. -/
theorem GP216BridgeCompositionReceipt.eventGainPrefix_sq_le_budgetProduct
    (R : GP216BridgeCompositionReceipt)
    (N : ℕ) :
    (eventGainPrefix R.eventRecurrence N) ^ (2 : Nat) ≤
      R.eventRecurrence.priceBudget * R.eventRecurrence.reciprocalBudget :=
  event_gain_prefix_sq_le_budget_product
    R.eventRecurrence
    R.eventRecurrenceCertificate
    N

/-- The event source bundle rules out divergent event-gain prefixes at the
GP216 boundary through its Duhamel lower-envelope and section-incidence
receipts. -/
theorem GP216BridgeCompositionReceipt.noDivergentEventGainPrefix
    (R : GP216BridgeCompositionReceipt) :
    ¬ EventGainPrefixDiverges R.eventRecurrence :=
  R.eventRecurrenceSource.noDivergentEventGainPrefix

/-- Continuum topology projected from the same all-output source bundle as the
countable tail and coupling receipts. -/
def GP216BridgeCompositionReceipt.continuumTopology
    (R : GP216BridgeCompositionReceipt) :
    ContinuumLPProfileTopology :=
  R.continuumSource.topology

/-- Continuum LP/Bony stream projected from the all-output source bundle. -/
def GP216BridgeCompositionReceipt.continuumStream
    (R : GP216BridgeCompositionReceipt) :
    ContinuumLPPrefixPriceStream R.continuumSource.topology :=
  R.continuumSource.stream

/-- Countable all-output tail control projected from the same source as the
continuum stream. -/
def GP216BridgeCompositionReceipt.allOutputCountableTailControl
    (R : GP216BridgeCompositionReceipt) :
    AllOutputCountableGramTailControlReceipt R.continuumStream :=
  R.continuumSource.countableTailControl

/-- Generic continuum LSC receipt projected from the same countable
all-output tail-control source used by the final bridge. -/
def GP216BridgeCompositionReceipt.continuumLSCReceipt
    (R : GP216BridgeCompositionReceipt) :
    ContinuumLPLSCObligationReceipt R.continuumStream :=
  continuum_lsc_obligation_receipt_of_countable_all_output_gram_tail_control
    R.allOutputCountableTailControl

/-- Self-tax / continuum coupling projected from the all-output source bundle.
-/
def GP216BridgeCompositionReceipt.selfTaxContinuumCoupling
    (R : GP216BridgeCompositionReceipt) :
    LeraySelfTaxContinuumCoupling
      R.selfTaxStream
      R.continuumStream :=
  R.continuumSource.selfTaxCoupling

/-- The GP216 self-tax aggregate prefix price is the same prefix price as the
declared continuum all-output LP/Bony stream. -/
theorem GP216BridgeCompositionReceipt.selfTaxPrefixPrice_eq_continuumPrefixPrice
    (R : GP216BridgeCompositionReceipt)
    (n : ℕ) :
    leraySelfTaxPrefixPrice R.selfTaxStream n =
      continuumLPPrefixPrice R.continuumStream n :=
  leray_self_tax_prefix_price_eq_continuum_prefix_price_of_coupling
    R.selfTaxStream
    R.continuumStream
    R.selfTaxContinuumCoupling
    n

/-- The GP216 self-tax aggregate total price has countable-tail control from
the same all-output source bundle as the event-recurrence coupling.

This is not component LSC.  It only exposes the total-price tail edge already
paid by `continuumSource`; the component price bounds still come from the
audited self-tax output source. -/
theorem GP216BridgeCompositionReceipt.selfTaxTotalTailControl
    (R : GP216BridgeCompositionReceipt) :
    LeraySelfTaxPrefixPriceTendsToDeclaredLimit R.selfTaxStream :=
  leray_self_tax_total_tail_control_of_coupled_countable_gram_tail
    R.selfTaxStream
    R.continuumStream
    R.selfTaxContinuumCoupling
    R.allOutputCountableTailControl

/-- The GP216 same-topology tail receipt excludes an arbitrarily late
aggregate self-tax total-price gap. -/
theorem GP216BridgeCompositionReceipt.noSelfTaxTotalTailConvergenceFalsifier
    (R : GP216BridgeCompositionReceipt)
    (F : LeraySelfTaxTotalTailConvergenceFalsifier R.selfTaxStream) :
    False :=
  no_leray_self_tax_total_tail_convergence_falsifier
    R.selfTaxStream
    R.selfTaxTotalTailControl
    F

/-- Event-recurrence / all-output coupling projected from the same continuum
source bundle as the countable tail-control receipt. -/
def GP216BridgeCompositionReceipt.allOutputEventRecurrenceCoupling
    (R : GP216BridgeCompositionReceipt) :
    AllOutputEventRecurrenceCoupling
      R.continuumStream
      R.eventRecurrence :=
  R.continuumSource.eventCoupling

/-- The event-recurrence coupling and the countable-tail control are tied to
the same fixed all-output atoms at the GP216 composition boundary.

This is the direct projection of the provenance identity stored in the
continuum source bundle.  It prevents a final bridge from proving countable
tail control in one LP/Bony atomization while transporting event recurrence
prices through another. -/
theorem GP216BridgeCompositionReceipt.eventCoupling_fixedAtoms_eq_countableTail
    (R : GP216BridgeCompositionReceipt) :
    R.allOutputEventRecurrenceCoupling.fixed_atoms =
      R.allOutputCountableTailControl.fixed_atoms := by
  simpa [GP216BridgeCompositionReceipt.allOutputEventRecurrenceCoupling,
    GP216BridgeCompositionReceipt.allOutputCountableTailControl,
    GP216ContinuumAllOutputSourceBundle.countableTailControl]
    using R.continuumSource.eventCoupling_fixed_atoms_matches_countable_tail

/-- Event recurrence prices are embedded in the same continuum all-output
prefix stream used by GP216 tail control.  This is topology/price
bookkeeping, not a branch threshold-coordinate constructor. -/
theorem GP216BridgeCompositionReceipt.eventRawRecurrencePricePrefix_le_continuumPrefixPrice
    (R : GP216BridgeCompositionReceipt)
    (N : ℕ) :
    eventRawRecurrencePricePrefix R.eventRecurrence N ≤
      continuumLPPrefixPrice R.continuumStream N :=
  R.allOutputEventRecurrenceCoupling.raw_recurrence_price_embeds_in_all_output_prefix N

/-- Flat-torus Killing conclusion projected from the macroscopic clock source.
-/
def GP216BridgeCompositionReceipt.flatTorusKillingMode
    (R : GP216BridgeCompositionReceipt) :
    FlatTorusKillingModeConclusion :=
  R.macroscopicFlatTorusClockSource.killingMode

/-- Flat-torus low-high PDE obligation projected from the same macroscopic
clock source as the Killing obstruction and phase-capacity handoff. -/
def GP216BridgeCompositionReceipt.flatTorusLowHighPDE
    (R : GP216BridgeCompositionReceipt) :
    FlatTorusLowHighKinematicPDEObligation :=
  R.macroscopicFlatTorusClockSource.lowHighPDE

/-- Flat-torus Killing/PDE adapter projected from the macroscopic clock
source. -/
def GP216BridgeCompositionReceipt.flatTorusKillingPDEAdapter
    (R : GP216BridgeCompositionReceipt) :
    FlatTorusKillingModePDEAdapter
      R.flatTorusLowHighPDE
      R.flatTorusKillingMode :=
  R.macroscopicFlatTorusClockSource.adapter

/-- Phase-capacity handoff projected from the macroscopic clock source. -/
def GP216BridgeCompositionReceipt.flatTorusPhaseCapacityHandoff
    (R : GP216BridgeCompositionReceipt) :
    GP216FlatTorusPhaseCapacityHandoff
      R.phaseLatencyCapacitySource
      R.flatTorusKillingMode
      R.flatTorusLowHighPDE :=
  R.macroscopicFlatTorusClockSource.toPhaseCapacityHandoff

/-- Capacity theorem projected from the paid macroscopic flat-torus clock
source. -/
def GP216BridgeCompositionReceipt.flat_torus_pde_feeds_phase_capacity
    (R : GP216BridgeCompositionReceipt) :
    ∀ j : ℕ,
      R.phaseLatencyLipschitzReserve.phase.reach j *
          R.phaseLatencyLipschitzReserve.phase.kNorm j ≤
        R.phaseLatencyLipschitzReserve.phase.gramianConstant := by
  exact
    phase_capacity_of_macroscopic_flat_torus_clock_source
      R.macroscopicFlatTorusClockSource

/-- Flat-torus capacity stated directly on the stored profile-phase source.

This is the same macroscopic-clock source route as
`flat_torus_pde_feeds_phase_capacity`, but with the conclusion phrased on
`phaseLatencyProfileReserveSource.phase` so downstream code does not have to
walk through the derived legacy reserve bridge just to see the source phase. -/
theorem GP216BridgeCompositionReceipt.flat_torus_pde_feeds_profile_phase_capacity
    (R : GP216BridgeCompositionReceipt) :
    ∀ j : ℕ,
      R.phaseLatencyProfileReserveSource.phase.reach j *
          R.phaseLatencyProfileReserveSource.phase.kNorm j ≤
        R.phaseLatencyProfileReserveSource.phase.gramianConstant :=
  R.flat_torus_pde_feeds_phase_capacity

/-- GP216 derives the flat-torus Killing provenance from the concrete PDE
adapter instead of carrying a detached provenance field. -/
def GP216BridgeCompositionReceipt.flatTorusKillingModeProvenance
    (R : GP216BridgeCompositionReceipt) :
    FlatTorusKillingModeProvenance R.flatTorusKillingMode :=
  R.flatTorusKillingPDEAdapter.provenance

/-- GP216 derives the flat-torus low-high PDE satisfaction receipt through the
Killing-mode adapter, making the torus symmetry-breaker load-bearing before
phase capacity is consumed. -/
def GP216BridgeCompositionReceipt.flatTorusLowHighPDESatisfied
    (R : GP216BridgeCompositionReceipt) :
    FlatTorusLowHighKinematicPDEObligationSatisfied
      R.flatTorusLowHighPDE :=
  R.macroscopicFlatTorusClockSource.flatTorusLowHighPDESatisfied

/-- Derived handoff from finite flat-torus shell obstruction to the continuum
low-high positive-deformation duty. -/
def GP216BridgeCompositionReceipt.flat_torus_mode_supplies_pde_nonconstant_transfer
    (R : GP216BridgeCompositionReceipt) :
    R.flatTorusKillingMode.shell_transfer_requires_nonzero_strain →
      R.flatTorusLowHighPDE.nonconstant_shell_transfer_forces_positive_deformation :=
  R.flatTorusKillingPDEAdapter.shell_obstruction_positive_deformation_handoff

/-- The component-limit receipt used by the GP216 bridge is derived from the
defect-inclusive Leray-output source receipt with explicit scalar-stream
provenance, not carried as an opaque assumption. -/
def GP216BridgeCompositionReceipt.selfTaxOutputDerivedComponentLimitPassage
    (R : GP216BridgeCompositionReceipt) :
    LeraySelfTaxOutputDerivedComponentLimitPassageReceipt R.selfTaxStream :=
  R.selfTaxOutputSource.outputDerivedComponentLimitPassage

/-- The output-derived self-tax wrapper uses the same named output source as
the GP216 self-tax bundle.

This is definitional source provenance, not an additional analytic input. -/
theorem GP216BridgeCompositionReceipt.selfTaxOutputDerived_outputSource_eq_bundleSource
    (R : GP216BridgeCompositionReceipt) :
    R.selfTaxOutputDerivedComponentLimitPassage.output_source =
      R.selfTaxOutputSource.outputLimitStreamSource :=
  rfl

/-- The self-tax bundle source stream's declared limit price is the continuum
all-output target.

This transports through the audited self-tax bundle's direct stream provenance
before using the same-topology continuum coupling, so the final target edge is
not a raw scalar-stream shortcut. -/
theorem GP216BridgeCompositionReceipt.selfTaxBundleSourceLimitPrice_eq_continuumTarget
    (R : GP216BridgeCompositionReceipt) :
    leraySelfTaxLimitPrice
        R.selfTaxOutputSource.outputLimitStreamSource.stream =
      continuumGlobalSelfTaxTarget R.continuumStream := by
  have hsource :
      leraySelfTaxLimitPrice R.selfTaxOutputSource.outputLimitStreamSource.stream =
        leraySelfTaxLimitPrice R.selfTaxStream := by
    exact
      (leray_self_tax_limit_price_eq_source_of_output_derived_stream_receipt
        R.selfTaxOutputSource.outputLimitStreamSource
        R.selfTaxStream
        R.selfTaxOutputSource.outputDerivedStreamReceipt).symm
  exact hsource.trans
    (leray_self_tax_limit_price_eq_continuum_global_target_of_coupling
      R.selfTaxStream R.continuumStream R.selfTaxContinuumCoupling)

/-- Compatibility alias for older consumers that still project the
output-derived component-limit wrapper before reading the output source. -/
theorem GP216BridgeCompositionReceipt.selfTaxOutputSourceLimitPrice_eq_continuumTarget
    (R : GP216BridgeCompositionReceipt) :
    leraySelfTaxLimitPrice
        R.selfTaxOutputDerivedComponentLimitPassage.output_source.stream =
      continuumGlobalSelfTaxTarget R.continuumStream := by
  let P := R.selfTaxOutputDerivedComponentLimitPassage
  have hsource :
      leraySelfTaxLimitPrice P.output_source.stream =
        leraySelfTaxLimitPrice R.selfTaxStream := by
    exact
      (leray_self_tax_limit_price_eq_source_of_output_derived_stream_receipt
        P.output_source R.selfTaxStream P.stream_provenance).symm
  exact hsource.trans
    (leray_self_tax_limit_price_eq_continuum_global_target_of_coupling
      R.selfTaxStream R.continuumStream R.selfTaxContinuumCoupling)

/-- Drop the GP216 self-tax source wrapper only at the legacy component-limit
API boundary. -/
def GP216BridgeCompositionReceipt.selfTaxComponentLimitPassage
    (R : GP216BridgeCompositionReceipt) :
    LeraySelfTaxComponentLimitPassageReceipt R.selfTaxStream :=
  component_limit_passage_of_output_derived
    R.selfTaxStream
    R.selfTaxOutputDerivedComponentLimitPassage

/-- Component LSC projected directly at the GP216 boundary.

This is only a projection of the audited output-derived component-limit
receipt.  It is kept explicit so later bridge steps cannot replace component
LSC with aggregate total-tail convergence. -/
def GP216BridgeCompositionReceipt.selfTaxComponentLSC
    (R : GP216BridgeCompositionReceipt) :
    LeraySelfTaxComponentLSC R.selfTaxStream :=
  component_lsc_of_component_limit_passage
    R.selfTaxStream
    R.selfTaxComponentLimitPassage

/-- The GP216 output-derived component receipt excludes component-LSC
falsifiers directly at the composition boundary. -/
theorem GP216BridgeCompositionReceipt.noSelfTaxComponentLSCFalsifier
    (R : GP216BridgeCompositionReceipt)
    (F : LeraySelfTaxComponentLSCFalsifier R.selfTaxStream) :
    False :=
  no_component_lsc_of_leray_self_tax_falsifier
    R.selfTaxStream
    F
    R.selfTaxComponentLSC

/-- The local-to-global component assembly used by the GP216 self-tax branch,
kept at the output-derived component-limit layer rather than the aggregate
profile-LSC receipt layer. -/
def GP216BridgeCompositionReceipt.selfTaxOutputLocalToGlobalAssembly
    (R : GP216BridgeCompositionReceipt) :
    LeraySelfTaxPrefixLocalToGlobalComponentAssembly R.selfTaxStream :=
  R.selfTaxComponentLimitPassage.local_to_global_assembly

/-- The finite-prefix charge receipt paired with
`selfTaxOutputLocalToGlobalAssembly`. -/
def GP216BridgeCompositionReceipt.selfTaxOutputFinitePrefixCharge
    (R : GP216BridgeCompositionReceipt) :
    ∀ n : ℕ,
      LeraySelfTaxFinitePrefixChargeReceipt
        R.selfTaxStream
        R.selfTaxOutputLocalToGlobalAssembly n :=
  R.selfTaxComponentLimitPassage.finite_prefix_charge

/-- The GP216 self-tax receipt is derived at the output-derived layer, keeping
the defect-inclusive output source and stream provenance visible on the term
surface. -/
def GP216BridgeCompositionReceipt.selfTaxReceipt
    (R : GP216BridgeCompositionReceipt) :
    LeraySelfTaxProfileLSCReceipt R.selfTaxStream :=
  leray_self_tax_profile_lsc_receipt_of_output_derived_component_limit_passage
    R.selfTaxStream
    R.selfTaxOutputDerivedComponentLimitPassage

/-- The branch amplitude-level projection receipt is derived from the
generated profile/Lipschitz block family, not supplied as a free GP216 field.

This keeps the actual amplitude/gain constructor visible in the composite
receipt before it is lowered to the older quartic projection interface. -/
def GP216BridgeCompositionReceipt.branchQuarticSurvivalAmplitudeObservableSource
    (R : GP216BridgeCompositionReceipt) :
    QuarticSurvivalAmplitudeObservableSource R.branchBlock := by
  rw [R.branch_matches_profile_lipschitz_generated_block]
  exact R.profileLipschitzObligation.generated_amplitude_observable_source
    (R.profileLipschitzObligation.evolution_of_initial_data
      R.profileLipschitzInitialData)
    R.profileLipschitzBranchIndex

/-- The branch amplitude-level projection receipt is derived from the
generated profile/Lipschitz charged-observable source, not supplied as a free
GP216 field. -/
def GP216BridgeCompositionReceipt.branchQuarticSurvivalAmplitudeProjection
    (R : GP216BridgeCompositionReceipt) :
    QuarticSurvivalAmplitudeProjectionReceipt R.branchBlock :=
  quartic_survival_amplitude_projection_of_observable_source
    R.branchBlock
    R.branchQuarticSurvivalAmplitudeObservableSource

/-- The GP216 generated branch uses the audited self-tax stream in the
threshold-coordinate receipt.

This is the source-preserving projection of
`branchSelfTaxThresholdCoordinateIdentities`: downstream generated-branch
arguments can consume the exact generated profile/Lipschitz block and the
audited self-tax stream directly, instead of first accepting a detached
`branchBlock` and rewriting it later. -/
def GP216BridgeCompositionReceipt.generatedBranchSelfTaxThresholdCoordinateIdentities
    (R : GP216BridgeCompositionReceipt) :
    BranchSelfTaxThresholdCoordinateIdentities
      (GP216GeneratedProfileLipschitzBranchBlock
        R.continuationSource.handoff
        R.profileLipschitzBranchIndex)
      R.selfTaxStream := by
  rw [GP216GeneratedProfileLipschitzBranchBlock]
  rw [← R.branch_matches_profile_lipschitz_generated_block]
  exact R.branchSelfTaxThresholdCoordinateIdentities

/-- The generated GP216 branch is already charged by the audited output-derived
self-tax source at the threshold root.

This is the branch/generated-block form of the defect-measure guard: it uses
the audited self-tax stream and the generated-block threshold identities,
not a new scalar defect assertion. -/
theorem gp216_generated_branch_threshold_root_defect_of_output_derived_self_tax
    (R : GP216BridgeCompositionReceipt)
    (habove :
      sharpTarget <
        (GP216GeneratedProfileLipschitzBranchBlock
          R.continuationSource.handoff
          R.profileLipschitzBranchIndex).gamma) :
    1 ≤
      survivalDefect
        (GP216GeneratedProfileLipschitzBranchBlock
          R.continuationSource.handoff
          R.profileLipschitzBranchIndex)
        (Real.sqrt
          (sharpTarget /
            (GP216GeneratedProfileLipschitzBranchBlock
              R.continuationSource.handoff
              R.profileLipschitzBranchIndex).gamma)) :=
  threshold_root_defect_ge_one_of_audited_output_source_and_threshold_identities
    (GP216GeneratedProfileLipschitzBranchBlock
      R.continuationSource.handoff
      R.profileLipschitzBranchIndex)
    R.selfTaxStream
    R.selfTaxOutputLimitSource
    R.generatedBranchSelfTaxThresholdCoordinateIdentities
    habove

/-- The generated GP216 branch has the fixed threshold-root coordinate guards.

This is the falsifier-facing guard form for the generated branch and audited
self-tax stream. -/
theorem no_gp216_generated_branch_self_tax_threshold_guard_falsifier
    (R : GP216BridgeCompositionReceipt)
    (F :
      BranchSelfTaxThresholdCoordinateGuardFalsifier
        (GP216GeneratedProfileLipschitzBranchBlock
          R.continuationSource.handoff
          R.profileLipschitzBranchIndex)
        R.selfTaxStream
        R.generatedBranchSelfTaxThresholdCoordinateIdentities) :
    False :=
  no_branch_self_tax_threshold_coordinate_guard_falsifier
    (GP216GeneratedProfileLipschitzBranchBlock
      R.continuationSource.handoff
      R.profileLipschitzBranchIndex)
    R.selfTaxStream
    R.generatedBranchSelfTaxThresholdCoordinateIdentities
    F

/-- The generated GP216 branch normalizes the audited self-tax payoff limit at
the threshold root. -/
theorem gp216_generated_branch_payoff_limit_eq_one
    (R : GP216BridgeCompositionReceipt)
    (habove :
      sharpTarget <
        (GP216GeneratedProfileLipschitzBranchBlock
          R.continuationSource.handoff
          R.profileLipschitzBranchIndex).gamma) :
    R.selfTaxStream.payoffLimit = 1 :=
  branch_payoff_limit_eq_one_of_threshold_coordinate_identities
    (GP216GeneratedProfileLipschitzBranchBlock
      R.continuationSource.handoff
      R.profileLipschitzBranchIndex)
    R.selfTaxStream
    R.generatedBranchSelfTaxThresholdCoordinateIdentities
    habove

/-- The generated GP216 branch self-tax limit price is the exact quartic root
component of the same audited self-tax stream. -/
theorem gp216_generated_branch_self_tax_limit_price_eq_root_component
    (R : GP216BridgeCompositionReceipt)
    (habove :
      sharpTarget <
        (GP216GeneratedProfileLipschitzBranchBlock
          R.continuationSource.handoff
          R.profileLipschitzBranchIndex).gamma) :
    R.selfTaxStream.selfTaxLimitPrice =
      (GP216GeneratedProfileLipschitzBranchBlock
        R.continuationSource.handoff
        R.profileLipschitzBranchIndex).selfTax *
        (Real.sqrt
          (sharpTarget /
            (GP216GeneratedProfileLipschitzBranchBlock
              R.continuationSource.handoff
              R.profileLipschitzBranchIndex).gamma)) ^ (4 : Nat) :=
  branch_self_tax_limit_price_eq_root_component_of_threshold_coordinate_identities
    (GP216GeneratedProfileLipschitzBranchBlock
      R.continuationSource.handoff
      R.profileLipschitzBranchIndex)
    R.selfTaxStream
    R.generatedBranchSelfTaxThresholdCoordinateIdentities
    habove

/-- The branch projection receipt is derived from the generated
profile/Lipschitz amplitude receipt, not supplied as a free GP216 field. -/
def GP216BridgeCompositionReceipt.branchQuarticSurvivalProjection
    (R : GP216BridgeCompositionReceipt) :
    QuarticSurvivalProjectionReceipt R.branchBlock :=
  quartic_survival_projection_of_amplitude_receipt
    R.branchBlock
    R.branchQuarticSurvivalAmplitudeProjection

/-- The actual GP216 generated branch has the Lipschitz gain-at-amplitude cap.

This is deliberately generated-branch scoped: no global all-`NSEvolution` cap
is claimed.  The separate `branch_matches_profile_lipschitz_generated_block`
field ties this generated block to `branchBlock` at downstream branch uses. -/
theorem GP216BridgeCompositionReceipt.generatedBranchGainAtAmpLeTarget
    (R : GP216BridgeCompositionReceipt) :
    let U :=
      R.profileLipschitzObligation.evolution_of_initial_data
        R.profileLipschitzInitialData
    let B :=
      (R.profileLipschitzObligation.lipschitz_bridge.ledger_of_evolution U).block
        R.profileLipschitzBranchIndex
    B.gamma *
        (R.profileLipschitzObligation.generated_quartic_survival_amplitude_projection
          U R.profileLipschitzBranchIndex).ampSq ≤
      sharpTarget :=
  generated_lipschitz_gain_at_amp_le_target_of_profile_lipschitz_source
    R.profileLipschitzObligation
    R.profileLipschitzInitialData
    R.profileLipschitzBranchIndex

/-- The GP216 generated branch therefore exposes the exact threshold-root
amplitude bound. -/
theorem GP216BridgeCompositionReceipt.generatedBranchAmpSqLeThresholdRoot
    (R : GP216BridgeCompositionReceipt)
    (habove :
      let U :=
        R.profileLipschitzObligation.evolution_of_initial_data
          R.profileLipschitzInitialData
      let B :=
        (R.profileLipschitzObligation.lipschitz_bridge.ledger_of_evolution U).block
          R.profileLipschitzBranchIndex
      sharpTarget < B.gamma) :
    let U :=
      R.profileLipschitzObligation.evolution_of_initial_data
        R.profileLipschitzInitialData
    let B :=
      (R.profileLipschitzObligation.lipschitz_bridge.ledger_of_evolution U).block
        R.profileLipschitzBranchIndex
    (R.profileLipschitzObligation.generated_quartic_survival_amplitude_projection
        U R.profileLipschitzBranchIndex).ampSq ≤
      (Real.sqrt (sharpTarget / B.gamma)) ^ (2 : Nat) := by
  let U :=
    R.profileLipschitzObligation.evolution_of_initial_data
      R.profileLipschitzInitialData
  let B :=
    (trackBGeneratedLowFrequencyLipschitzLedger
      R.profileLipschitzObligation
      R.profileLipschitzInitialData).block
      R.profileLipschitzBranchIndex
  exact
    amp_sq_le_threshold_root_of_gain_action_cap
      B
      habove
      R.generatedBranchGainAtAmpLeTarget

/-- Falsifier for a GP216 branch that is not the generated profile/Lipschitz
block it later prices.

The equality `branch_matches_profile_lipschitz_generated_block` is used by
the projection theorems, so expose it as its own final-surface failure instead
of leaving it only as an internal rewrite. -/
structure GP216BranchGeneratedBlockIdentityFalsifier
    (R : GP216BridgeCompositionReceipt) where
  generated_block_mismatch :
    R.branchBlock ≠
      (trackBGeneratedLowFrequencyLipschitzLedger
        R.profileLipschitzObligation
        R.profileLipschitzInitialData).block
        R.profileLipschitzBranchIndex

/-- The GP216 branch is the generated profile/Lipschitz block carried by the
continuation source, so generated-block mismatch falsifiers cannot survive. -/
theorem no_gp216_branch_generated_block_identity_falsifier
    (R : GP216BridgeCompositionReceipt)
    (F : GP216BranchGeneratedBlockIdentityFalsifier R) :
    False := by
  exact F.generated_block_mismatch <| by
    simpa [GP216BridgeCompositionReceipt.profileLipschitzObligation,
      GP216BridgeCompositionReceipt.profileLipschitzInitialData]
      using R.branch_matches_profile_lipschitz_generated_block

/-- Falsifier for a coordinate reformulation whose source is not the GP216
branch block it is meant to recast. -/
structure GP216CoordinateReformulationSourceIdentityFalsifier
    (R : GP216BridgeCompositionReceipt) where
  coordinate_source_mismatch :
    R.coordinateReformulation.source ≠ R.branchBlock

/-- The GP216 coordinate reformulation is explicitly sourced at the branch
block, so source-identity mismatch falsifiers cannot survive. -/
theorem no_gp216_coordinate_reformulation_source_identity_falsifier
    (R : GP216BridgeCompositionReceipt)
    (F : GP216CoordinateReformulationSourceIdentityFalsifier R) :
    False :=
  F.coordinate_source_mismatch R.coordinate_source_is_branch

/-- Falsifier for a GP216 branch whose profile-family payoff/price is not the
same audited self-tax stream scored at the final bridge.

This names the min-cut surfaced by the constraint graph: profile-family
no-arbitrage is only relevant to the branch if its payoff and price are the
payoff limit and declared Leray self-tax limit price of the same audited
self-tax stream. -/
inductive GP216BranchProfileFamilySelfTaxStreamIdentityFalsifier
    (R : GP216BridgeCompositionReceipt) : Type where
  | familyStreamNotJointlyDeclared :
      ¬ R.branch_profile_family_self_tax_stream_declared_together →
        GP216BranchProfileFamilySelfTaxStreamIdentityFalsifier R
  | payoffMismatch :
      familyPayoff R.branchProfileFamily ≠
        R.selfTaxStream.payoffLimit →
        GP216BranchProfileFamilySelfTaxStreamIdentityFalsifier R
  | priceMismatch :
      familyPrice R.branchProfileFamily ≠
        leraySelfTaxLimitPrice R.selfTaxStream →
        GP216BranchProfileFamilySelfTaxStreamIdentityFalsifier R

/-- The GP216 receipt rules out branch profile-family/self-tax stream
identity failures because it carries the joint declaration and exact
payoff/price equalities at the final bridge boundary. -/
theorem no_gp216_branch_profile_family_self_tax_stream_identity_falsifier
    (R : GP216BridgeCompositionReceipt)
    (F : GP216BranchProfileFamilySelfTaxStreamIdentityFalsifier R) :
    False := by
  cases F with
  | familyStreamNotJointlyDeclared hbad =>
      exact hbad R.branch_profile_family_self_tax_stream_declared_together_paid
  | payoffMismatch hbad =>
      exact hbad <| by
        simpa [GP216BridgeCompositionReceipt.branchProfileFamily]
          using R.branch_profile_family_payoff_matches_self_tax_stream
  | priceMismatch hbad =>
      exact hbad <| by
        simpa [GP216BridgeCompositionReceipt.branchProfileFamily]
          using R.branch_profile_family_price_matches_self_tax_stream

/-- Branch profile-family no-arbitrage feeds the same audited self-tax stream
only through the explicit GP216 payoff/price identities. -/
theorem gp216_branch_profile_family_no_arbitrage_feeds_self_tax_limit
    (R : GP216BridgeCompositionReceipt)
    (hfamily :
      familyPayoff R.branchProfileFamily ≤
        familyPrice R.branchProfileFamily) :
    R.selfTaxStream.payoffLimit ≤
      leraySelfTaxLimitPrice R.selfTaxStream := by
  have hpay :
      familyPayoff R.branchProfileFamily =
        R.selfTaxStream.payoffLimit := by
    simpa [GP216BridgeCompositionReceipt.branchProfileFamily]
      using R.branch_profile_family_payoff_matches_self_tax_stream
  have hprice :
      familyPrice R.branchProfileFamily =
        leraySelfTaxLimitPrice R.selfTaxStream := by
    simpa [GP216BridgeCompositionReceipt.branchProfileFamily]
      using R.branch_profile_family_price_matches_self_tax_stream
  calc
    R.selfTaxStream.payoffLimit =
        familyPayoff R.branchProfileFamily := hpay.symm
    _ ≤ familyPrice R.branchProfileFamily := hfamily
    _ = leraySelfTaxLimitPrice R.selfTaxStream := hprice

/-- Branch profile-family price is the same continuum all-output self-tax
target carried by the GP216 source bundle.

This exposes the branch-profile pricing edge through the actual
`selfTaxOutputSource.stream` / `continuumSource.selfTaxCoupling` route, rather
than leaving downstream proofs to compose the two identities ad hoc. -/
theorem gp216_branch_profile_family_price_eq_continuum_global_target
    (R : GP216BridgeCompositionReceipt) :
    familyPrice R.branchProfileFamily =
      continuumGlobalSelfTaxTarget R.continuumStream := by
  have hprice :
      familyPrice R.branchProfileFamily =
        leraySelfTaxLimitPrice R.selfTaxStream := by
    simpa [GP216BridgeCompositionReceipt.branchProfileFamily]
      using R.branch_profile_family_price_matches_self_tax_stream
  exact hprice.trans
    (leray_self_tax_limit_price_eq_continuum_global_target_of_coupling
      R.selfTaxStream R.continuumStream R.selfTaxContinuumCoupling)

/-- GP216-facing self-tax no-arbitrage in the continuum all-output coordinates.

This is the graph-surfaced component bridge: the self-tax payoff is charged
through the output-derived component-limit wrapper, so scalar-stream provenance
is preserved before the result is transported through the same-topology
continuum coupling. -/
theorem gp216_self_tax_payoff_le_continuum_global_target
    (R : GP216BridgeCompositionReceipt) :
    R.selfTaxStream.payoffLimit ≤
      continuumGlobalSelfTaxTarget R.continuumStream := by
  have hlimit :
      R.selfTaxStream.payoffLimit ≤
        leraySelfTaxLimitPrice R.selfTaxStream :=
    no_global_self_tax_arbitrage_of_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
  have hlimit_source :
      R.selfTaxStream.payoffLimit ≤
        leraySelfTaxLimitPrice
          R.selfTaxOutputSource.outputLimitStreamSource.stream := by
    have hsource :
        leraySelfTaxLimitPrice
            R.selfTaxOutputSource.outputLimitStreamSource.stream =
          leraySelfTaxLimitPrice R.selfTaxStream := by
      exact
        (leray_self_tax_limit_price_eq_source_of_output_derived_stream_receipt
          R.selfTaxOutputSource.outputLimitStreamSource
          R.selfTaxStream
          R.selfTaxOutputSource.outputDerivedStreamReceipt).symm
    simpa [hsource] using hlimit
  exact hlimit_source.trans
    (le_of_eq R.selfTaxBundleSourceLimitPrice_eq_continuumTarget)

/-- Coupled component-limit-passage form of the self-tax payoff charge.

This is the typed version of the transitivity-closure candidate
`S.payoffLimit ≤ continuumGlobalSelfTaxTarget`: it is valid only when the
component LSC receipt and same-topology continuum coupling are both supplied. -/
theorem self_tax_payoff_le_continuum_global_target_of_component_lsc_coupling
    {τ : ContinuumLPProfileTopology.{u}}
    (S : LeraySelfTaxProfilePriceStream)
    (T : ContinuumLPPrefixPriceStream τ)
    (P : LeraySelfTaxComponentLimitPassageReceipt S)
    (C : LeraySelfTaxContinuumCoupling S T) :
    S.payoffLimit ≤ continuumGlobalSelfTaxTarget T := by
  have hlimit : S.payoffLimit ≤ leraySelfTaxLimitPrice S :=
    no_global_self_tax_arbitrage_of_component_limit_passage S P
  simpa [leray_self_tax_limit_price_eq_continuum_global_target_of_coupling
      S T C] using hlimit

/-- Coupled output-source form of the self-tax payoff charge.

This is the GP216-safe route: component LSC is not supplied as an opaque
assumption but derived from the audited, defect-inclusive Leray-output limit
source. -/
theorem self_tax_payoff_le_continuum_global_target_of_output_limit_source
    {τ : ContinuumLPProfileTopology.{u}}
    (S : LeraySelfTaxProfilePriceStream)
    (T : ContinuumLPPrefixPriceStream τ)
    (P : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S)
    (C : LeraySelfTaxContinuumCoupling S T) :
    S.payoffLimit ≤ continuumGlobalSelfTaxTarget T := by
  have hlimit : S.payoffLimit ≤ leraySelfTaxLimitPrice S :=
    no_global_self_tax_arbitrage_of_audited_output_limit_source S P
  simpa [leray_self_tax_limit_price_eq_continuum_global_target_of_coupling
      S T C] using hlimit

/-- Bundle-level continuum payoff charge.

This projects the GP216 self-tax bundle directly into the continuum
all-output target when the same-topology coupling is supplied, without using a
final `GP216BridgeCompositionReceipt`. -/
theorem GP216SelfTaxAuditedOutputSourceBundle.payoff_le_continuumGlobalTarget
    {τ : ContinuumLPProfileTopology.{u}}
    (B : GP216SelfTaxAuditedOutputSourceBundle)
    (T : ContinuumLPPrefixPriceStream τ)
    (C : LeraySelfTaxContinuumCoupling B.stream T) :
    B.stream.payoffLimit ≤ continuumGlobalSelfTaxTarget T :=
  self_tax_payoff_le_continuum_global_target_of_output_limit_source
    B.stream
    T
    B.audited_source
    C

/-- Measure-valued/Young-defect form of the coupled self-tax payoff charge.

This is a source-visible alias for the same audited output-limit route used by
GP216: the PDE side supplies the relaxed output defect source directly, and
the theorem immediately packages it as the audited source consumed by the
continuum coupling. -/
theorem self_tax_payoff_le_continuum_global_target_of_measure_valued_source
    {τ : ContinuumLPProfileTopology.{u}}
    (S : LeraySelfTaxProfilePriceStream)
    (T : ContinuumLPPrefixPriceStream τ)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (charges : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hpayoff :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (noncircular_output_convergence_source : Prop)
    (noncircular_output_convergence_source_receipt :
      noncircular_output_convergence_source)
    (C : LeraySelfTaxContinuumCoupling S T) :
    S.payoffLimit ≤ continuumGlobalSelfTaxTarget T :=
  self_tax_payoff_le_continuum_global_target_of_output_limit_source
    S T
    (audited_output_limit_passage_source_of_measure_valued_source_and_tendsto_prefix_payoff
      S A charges hpayoff M
      noncircular_output_convergence_source
      noncircular_output_convergence_source_receipt)
    C

/-- Noncircular measure-valued form of the coupled self-tax payoff charge. -/
theorem self_tax_payoff_le_continuum_global_target_of_mv_noncircular
    {τ : ContinuumLPProfileTopology.{u}}
    (S : LeraySelfTaxProfilePriceStream)
    (T : ContinuumLPPrefixPriceStream τ)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (charges : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hpayoff :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (N : LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt S M)
    (C : LeraySelfTaxContinuumCoupling S T) :
    S.payoffLimit ≤ continuumGlobalSelfTaxTarget T :=
  self_tax_payoff_le_continuum_global_target_of_output_limit_source
    S T
    (audited_mv_tendsto_output_source_noncircular
      S A charges hpayoff M N)
    C

/-- Cauchy/subsequence measure-valued form of the coupled self-tax payoff
charge.

This names the diagonal compactness route at the GP216 boundary. It keeps the
subsequence Young-measure source visible while still concluding through the
same audited output-limit theorem, so no detached scalar stream is introduced.
-/
theorem self_tax_payoff_le_continuum_global_target_of_measure_valued_cauchy_subseq
    {τ : ContinuumLPProfileTopology.{u}}
    (S : LeraySelfTaxProfilePriceStream)
    (T : ContinuumLPPrefixPriceStream τ)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (charges : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hcauchy : CauchySeq S.prefixPayoff)
    {φ : ℕ → ℕ}
    (hφ : StrictMono φ)
    (hsub :
      Filter.Tendsto
        (fun k : ℕ => S.prefixPayoff (φ k))
        Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (noncircular_output_convergence_source : Prop)
    (noncircular_output_convergence_source_receipt :
      noncircular_output_convergence_source)
    (C : LeraySelfTaxContinuumCoupling S T) :
    S.payoffLimit ≤ continuumGlobalSelfTaxTarget T :=
  self_tax_payoff_le_continuum_global_target_of_output_limit_source
    S T
    (audited_output_limit_source_of_measure_valued_cauchy_subseq
      S A charges hcauchy hφ hsub M
      noncircular_output_convergence_source
      noncircular_output_convergence_source_receipt)
    C

/-- Noncircular Cauchy/subsequence measure-valued form of the coupled self-tax
payoff charge. -/
theorem self_tax_payoff_le_continuum_global_target_of_mv_cauchy_noncircular
    {τ : ContinuumLPProfileTopology.{u}}
    (S : LeraySelfTaxProfilePriceStream)
    (T : ContinuumLPPrefixPriceStream τ)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (charges : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hcauchy : CauchySeq S.prefixPayoff)
    {φ : ℕ → ℕ}
    (hφ : StrictMono φ)
    (hsub :
      Filter.Tendsto
        (fun k : ℕ => S.prefixPayoff (φ k))
        Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (N : LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt S M)
    (C : LeraySelfTaxContinuumCoupling S T) :
    S.payoffLimit ≤ continuumGlobalSelfTaxTarget T :=
  self_tax_payoff_le_continuum_global_target_of_output_limit_source
    S T
    (audited_mv_cauchy_subseq_output_source_noncircular
      S A charges hcauchy hφ hsub M N)
    C

/-- Coupled output-derived form of the self-tax payoff charge.

This is the strongest source-provenance-preserving route: the component limit
receipt is carried together with its audited Leray-output source and scalar
stream provenance until the final same-topology continuum coupling. -/
theorem self_tax_payoff_le_continuum_global_target_of_output_derived_source
    {τ : ContinuumLPProfileTopology.{u}}
    (S : LeraySelfTaxProfilePriceStream)
    (T : ContinuumLPPrefixPriceStream τ)
    (P : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (C : LeraySelfTaxContinuumCoupling S T) :
    S.payoffLimit ≤ continuumGlobalSelfTaxTarget T := by
  have hlimit : S.payoffLimit ≤ leraySelfTaxLimitPrice S :=
    no_global_self_tax_arbitrage_of_output_derived_component_limit_passage
      S P
  simpa [leray_self_tax_limit_price_eq_continuum_global_target_of_coupling
      S T C] using hlimit

/-- Coupled prefix-envelope form of the self-tax price charge.

This is the typed version of the transitivity-closure candidate
`leraySelfTaxPrefixPrice ≤ continuumGlobalSelfTaxTarget`: it requires the
all-output prefix envelope before transporting the prefix through the same
continuum topology. -/
theorem self_tax_prefix_price_le_continuum_global_target_of_coupling
    {τ : ContinuumLPProfileTopology.{u}}
    (S : LeraySelfTaxProfilePriceStream)
    (T : ContinuumLPPrefixPriceStream τ)
    (C : LeraySelfTaxContinuumCoupling S T)
    (hpdom : AllOutputPrefixPriceDominatedByLimit T) :
    ∀ n : ℕ, leraySelfTaxPrefixPrice S n ≤ continuumGlobalSelfTaxTarget T := by
  intro n
  have hprefix :
      leraySelfTaxPrefixPrice S n ≤ leraySelfTaxLimitPrice S :=
    leray_self_tax_total_prefix_dominated_by_limit_of_coupling
      S T C hpdom n
  simpa [leray_self_tax_limit_price_eq_continuum_global_target_of_coupling
      S T C] using hprefix

/-- Named flat-torus symmetry-breaker predicate for the composite receipt.

Keeping this as a named node makes the proof-landscape graph show whether the
torus/Killing branch is actually load-bearing in the final bridge. -/
def GP216FlatTorusNonconstantTransferPaid
    (R : GP216BridgeCompositionReceipt) : Prop :=
  R.flatTorusLowHighPDE.nonconstant_shell_transfer_forces_positive_deformation

/-- Full flat-torus source package consumed by the phase-capacity handoff. -/
def GP216FlatTorusPhaseCapacitySourcesPaid
    (R : GP216BridgeCompositionReceipt) : Prop :=
  R.flatTorusKillingMode.shell_transfer_requires_nonzero_strain ∧
    R.flatTorusLowHighPDE.nonconstant_shell_transfer_forces_positive_deformation ∧
      R.flatTorusLowHighPDE.positive_deformation_charged_by_reserve_loss ∧
        R.flatTorusLowHighPDE.reserve_loss_charged_in_trackb_price

/-- Named phase-capacity mismatch branch for the composite receipt. -/
def GP216PhaseLatencyCapacityMismatch
    (R : GP216BridgeCompositionReceipt) : Prop :=
  ∃ j : ℕ,
    R.phaseLatencyLipschitzReserve.phase.gramianConstant <
      R.phaseLatencyLipschitzReserve.phase.reach j *
        R.phaseLatencyLipschitzReserve.phase.kNorm j

/-- Integrated phase-alignment control-energy escape inside the generated
profile/Lipschitz branch.

This is distinct from the pointwise harmonic phase-latency escape: here the
attempt must pay a full control-energy Gramian schedule and embed each entry in
the same generated low-frequency Lipschitz ledger before GP216 scores it. -/
def GP216PhaseAlignmentControlEnergyEscape
    (R : GP216BridgeCompositionReceipt) : Prop :=
  Nonempty
    (PhaseAlignmentProfileLipschitzEscapeAttempt
      R.profileLipschitzObligation
      R.profileLipschitzInitialData)

/-- Harmonic phase-latency escape inside the generated profile/Lipschitz
branch.

This is the profile-tied counterpart of
`HarmonicDyadicPhaseLatencyEscape R.phaseLatencyLipschitzReserve`; it prevents
the final bridge from proving latency pricing only for a detached reserve
ledger while the generated Track B Lipschitz ledger carries the actual escape.
-/
def GP216ProfileLipschitzPhaseLatencyEscape
    (R : GP216BridgeCompositionReceipt) : Prop :=
  Nonempty
    (PhaseLatencyProfileLipschitzEscapeAttempt
      R.profileLipschitzObligation
      R.profileLipschitzInitialData)

/-- Falsifier for a phase-latency reserve bridge detached from the generated
Track B profile/Lipschitz ledger used by the GP216 closure. -/
structure GP216PhaseLatencyReserveSourceFalsifier
    (R : GP216BridgeCompositionReceipt) where
  ledger_mismatch :
    R.phaseLatencyLipschitzReserve.ledger ≠
      trackBGeneratedLowFrequencyLipschitzLedger
        R.profileLipschitzObligation
        R.profileLipschitzInitialData

/-- The GP216 phase-latency bridge is tied to the generated
profile/Lipschitz ledger, so the harmonic latency branch cannot discharge
against a detached low-frequency reserve. -/
theorem no_gp216_phase_latency_reserve_source_falsifier
    (R : GP216BridgeCompositionReceipt)
    (F : GP216PhaseLatencyReserveSourceFalsifier R) :
    False := by
  exact F.ledger_mismatch rfl

/-- Falsifier for the stronger source-first profile/Lipschitz phase-reserve
object carried by GP216. -/
abbrev GP216PhaseLatencyProfileReserveSourceFalsifier
    (R : GP216BridgeCompositionReceipt) :=
  PhaseLatencyProfileLipschitzReserveSourceFalsifier
    R.phaseLatencyProfileReserveSource

/-- The GP216 phase-latency source excludes generated-ledger and phase-control
embedding failures before it is projected to the legacy reserve bridge. -/
theorem no_gp216_phase_latency_profile_reserve_source_falsifier
    (R : GP216BridgeCompositionReceipt)
    (F : GP216PhaseLatencyProfileReserveSourceFalsifier R) :
    False :=
  no_phase_latency_profile_lipschitz_reserve_source_falsifier
    R.phaseLatencyProfileReserveSource
    F

/-- The GP216 composite receipt excludes missing provenance on the stronger
macroscopic flat-torus clock source, not only on the derived phase-capacity
handoff. -/
theorem gp216_no_macroscopic_flat_torus_clock_source_falsifier
    (R : GP216BridgeCompositionReceipt) :
    ¬ Nonempty
      (MacroscopicFlatTorusClockSourceFalsifier
        R.macroscopicFlatTorusClockSource) := by
  intro hfalsifier
  rcases hfalsifier with ⟨hfalsifier⟩
  exact
    no_macroscopic_flat_torus_clock_source_falsifier
      R.macroscopicFlatTorusClockSource
      hfalsifier

/-- Named gap for event-recurrence PDE duties.

The event-level recurrence certificate is not allowed to close the GP-216
bridge unless the PDE-side event topology, multiplicity, latency, and
decoupling obligations have been satisfied as a single predeclared receipt. -/
def GP216EventRecurrencePDEObligationGap
    (R : GP216BridgeCompositionReceipt) : Prop :=
  ¬ EventRecurrencePricePDEObligationSatisfied
    R.eventRecurrencePDEObligation

/-- Named gap for the low-high Lipschitz reserve PDE duty.

The shell-family reserve closure is not allowed to close the low-high branch
unless the fixed LP/Bony topology, reserve embedding, same-ledger identity, and
smooth limit preservation duties are paid up front. -/
def GP216LowHighLipschitzReservePDEObligationGap
    (R : GP216BridgeCompositionReceipt) : Prop :=
  ¬ LowHighLipschitzReservePDEObligationSatisfied
    R.lowHighLipschitzReservePDEObligation

/-- Named concrete Fourier latency symbol escape.

This is the GP216-facing form of the low-high `|k_j| / j` latency obstruction:
if a fixed Fourier-symbol receipt embeds the required low-Lipschitz cost into
the generated Track B ledger, then an unbounded `shellOverIndex` schedule is a
candidate escape branch that the receipt must explicitly price. -/
def GP216ConcreteFourierLatencySymbolEscape
    (R : GP216BridgeCompositionReceipt) : Prop :=
  ∃ S :
    ConcreteFourierLatencySymbolReceipt
      (trackBGeneratedLowFrequencyLipschitzLedger
        R.profileLipschitzObligation
        R.profileLipschitzInitialData),
    ∀ B : Real, ∃ n : ℕ, B < S.shellOverIndex n

/-- The profile/Lipschitz evolution generated inside GP216. -/
def GP216ProfileLipschitzEvolution
    (R : GP216BridgeCompositionReceipt) : NSEvolution :=
  R.profileLipschitzObligation.evolution_of_initial_data
    R.profileLipschitzInitialData

/-- Falsifier for a circular or undeclared Lipschitz-prefix continuation source
inside the generated GP216 profile/Lipschitz bridge. -/
abbrev GP216LipschitzContinuationSourceFalsifier
    (R : GP216BridgeCompositionReceipt) : Type :=
  LowFrequencyLipschitzContinuationSourceFalsifier
    (R.profileLipschitzObligation.lipschitz_bridge.ledger_of_evolution
      (GP216ProfileLipschitzEvolution R))
    (R.profileLipschitzObligation.lipschitz_bridge.continuation_source_of_evolution
      (GP216ProfileLipschitzEvolution R))

/-- Falsifier for a scalar self-tax stream substituted after the audited
Leray-output source has been fixed. -/
abbrev GP216SelfTaxOutputSourceSubstitutionFalsifier
    (R : GP216BridgeCompositionReceipt) : Prop :=
  LeraySelfTaxOutputSourceSubstitutionFalsifier
    R.selfTaxOutputSource.outputLimitStreamSource
    R.selfTaxStream
    R.selfTaxOutputSource.outputDerivedStreamReceipt

/-- Falsifier for missing upstream endpoint provenance after the concrete
Leray self-tax stream is viewed through the cycle-free Track B endpoint. -/
abbrev GP216SelfTaxEndpointGuardFalsifier
    (R : GP216BridgeCompositionReceipt) : Type :=
  TrackBSelfTaxEndpointGuardFalsifier
    (trackB_self_tax_limit_endpoint_of_leray_stream R.selfTaxStream)

/-- Falsifier for a posthoc profile-decomposition source inside the GP216
profile/Lipschitz branch. -/
abbrev GP216ProfileDecompositionSourceFalsifier
    (R : GP216BridgeCompositionReceipt) : Prop :=
  TrackBProfileDecompositionSourceFalsifier
    R.profileLipschitzObligation.profile_obligation.source_receipt

/-- Falsifier for a profile-decomposition bridge bundle whose four branch
bridges do not share the same predeclared profile family. -/
abbrev GP216ProfileDecompositionBridgeBundleFalsifier
    (R : GP216BridgeCompositionReceipt) : Type :=
  TrackBProfileDecompositionBridgeBundleFalsifier
    R.profileLipschitzObligation.profile_bundle

/-- Falsifier for a generated profile/Lipschitz amplitude source that is not
backed by a fully charged signed observable. -/
abbrev GP216ProfileLipschitzAmplitudeSourceFalsifier
    (R : GP216BridgeCompositionReceipt) : Type :=
  TrackBProfileLipschitzGeneratedAmplitudeObservableSourceFalsifier
    R.profileLipschitzObligation

/-- Falsifier for a high-high PDE source whose "same Leray output ledger"
duty is not identified with the concrete GP216 self-tax output stream. -/
structure GP216HighHighSelfTaxPDEOutputLedgerProvenanceFalsifier
    (R : GP216BridgeCompositionReceipt) where
  same_output_ledger_mismatch :
    ¬ (R.highHighSelfTaxPDEObligation.same_leray_output_ledger_declared_before_payoff ↔
      R.selfTaxStream.limitComponentPricesDeclaredBeforePayoff)

/-- The GP216 high-high source excludes mismatch between the abstract
same-output-ledger duty and the concrete self-tax output stream used by the
branch threshold coordinates. -/
theorem no_gp216_high_high_self_tax_pde_output_ledger_provenance_falsifier
    (R : GP216BridgeCompositionReceipt)
    (F : GP216HighHighSelfTaxPDEOutputLedgerProvenanceFalsifier R) :
    False :=
  F.same_output_ledger_mismatch
    R.highHigh_same_output_ledger_matches_self_tax_stream

/-- Named gap for the high-high self-tax PDE/SOS duty.

The branch no-survivor route is not allowed to close with a naked
`ThresholdDefectConvexity` assumption.  It must carry the high-high topology,
same-output ledger, null-route cap, cross-aware/SOS receipt, and profile-limit
stability duties as a predeclared receipt. -/
def GP216HighHighSelfTaxPDEObligationGap
    (R : GP216BridgeCompositionReceipt) : Prop :=
  ¬ HighHighSelfTaxPDEObligationSatisfied
    R.highHighSelfTaxPDEObligation

/-- The disjunctive survivor/global-bridge candidate ruled out by the composite
receipt.

Each branch is one surviving gap class exposed by the imported receipts:
full-ledger branch survivor, profile-limit self-tax arbitrage, positive
beat/backscatter surplus, unbounded low-beat demand against a finite reserve,
harmonic phase-latency escape, or failure of the declared continuation bridge. -/
def GP216GlobalBridgeCandidateWithinDeclaredScope
    (R : GP216BridgeCompositionReceipt) : Prop :=
  R.declaredScope ∧
    (Nonempty
      (QuarticSurvivalProjectionGuardFalsifier
        R.branchBlock
        R.branchQuarticSurvivalProjection) ∨
      Nonempty
        (QuarticSurvivalAmplitudeProjectionFalsifier
          R.branchBlock
          R.branchQuarticSurvivalAmplitudeProjection) ∨
      Nonempty
        (QuarticSurvivalProjectionCapFalsifier
          R.branchBlock
          R.branchQuarticSurvivalProjection) ∨
      Nonempty
        (GP216BranchGeneratedBlockIdentityFalsifier
          R) ∨
      sharpTarget < R.branchBlock.survivalProfit ∨
      GlobalLeraySelfTaxArbitrage R.selfTaxStream ∨
        continuumGlobalSelfTaxTarget R.continuumStream <
          R.selfTaxStream.payoffLimit ∨
        LeraySelfTaxPrefixIntegralUnbounded
          R.selfTaxStream
          R.selfTaxOutputLocalToGlobalAssembly ∨
          LeraySelfTaxPrefixAssemblyUndercharged
            R.selfTaxStream
            R.selfTaxOutputLocalToGlobalAssembly ∨
          Nonempty
            (LeraySelfTaxFinitePrefixArbitrageFalsifier
              R.selfTaxStream) ∨
          Nonempty
            (LeraySelfTaxFinitePrefixChargeGuardFalsifier
              R.selfTaxStream
              R.selfTaxOutputLocalToGlobalAssembly
              R.selfTaxOutputFinitePrefixCharge) ∨
          Nonempty
            (LeraySelfTaxPayoffApproximationFalsifier
              R.selfTaxStream) ∨
          Nonempty
            (LeraySelfTaxPayoffTailApproximationFalsifier
              R.selfTaxStream) ∨
          Nonempty
            (LeraySelfTaxComponentLSCFalsifier
              R.selfTaxStream) ∨
          Nonempty
            (LeraySelfTaxTotalLSCFalsifier
              R.selfTaxStream) ∨
          Nonempty
            (LeraySelfTaxUnchargedOutputDefectFalsifier
              R.selfTaxOutputLimitSource.output_limit_price) ∨
          Nonempty
            (LeraySelfTaxRelaxedOutputDefectFloorFalsifier
              R.selfTaxOutputLimitSource.output_limit_price) ∨
          Nonempty
            (LeraySelfTaxOutputLimitPricePDEGuardFalsifier
              R.selfTaxOutputLimitSource.output_limit_price) ∨
          Nonempty
            (LeraySelfTaxOutputLimitPassageGuardFalsifier
              R.selfTaxStream
              R.selfTaxOutputLimitSource) ∨
          Nonempty
            (GP216SelfTaxOutputSourceSubstitutionFalsifier R) ∨
          Nonempty
            (GP216SelfTaxEndpointGuardFalsifier R) ∨
          Nonempty
            (LeraySelfTaxPostHocStreamFalsifier
              R.selfTaxStream) ∨
          Nonempty
            (LeraySelfTaxAssemblyBudgetMismatchFalsifier
              R.selfTaxStream R.selfTaxOutputLocalToGlobalAssembly) ∨
          Nonempty
            (LeraySelfTaxContinuumCouplingMismatchFalsifier
              R.selfTaxStream R.continuumStream) ∨
          Nonempty
            (BranchSelfTaxThresholdCoordinateIdentityMismatchFalsifier
              R.branchBlock R.selfTaxStream) ∨
          Nonempty
            (BranchSelfTaxThresholdCoordinateGuardFalsifier
              R.branchBlock
              R.selfTaxStream
              R.branchSelfTaxThresholdCoordinateIdentities) ∨
          Nonempty
            (GP216BranchProfileFamilySelfTaxStreamIdentityFalsifier
              R) ∨
          Nonempty
            (LPBeatBackscatterSourceSubstitutionFalsifier
              R.coherenceSource
              R.coherenceStream
              R.coherenceSourceReceipt) ∨
          ¬ GP216PositiveCoherenceUniformlyPaid R ∨
            Nonempty
              (LowBeatPrefixReserveGuardFalsifier R.lowBeatStream) ∨
            Nonempty
              (GP216LowBeatEnvelopeSourceFalsifier
                R.lowBeatEnvelopeSource) ∨
            (∀ B : Real, ∃ n : ℕ,
              B < R.lowBeatStream.prefixBeatPayoff n) ∨
              FixedPrefixLowBeatSurvivor R.fixedPrefixLowBeat ∨
                MovingAllOutputLowBeatSurvivor R.movingAllOutputLowBeat ∨
                  ContinuumLPSmoothEscapeCandidate R.continuumStream ∨
                    Nonempty
                      (AllOutputCoherencePriceLSCFailureFalsifier
                        R.continuumStream) ∨
                    Nonempty
                      (FixedAllOutputLPBonyAtomsGuardFalsifier
                        R.continuumStream
                        R.allOutputCountableTailControl.fixed_atoms) ∨
                    (∃ N : ℕ,
                      Nonempty
                        (PrefixAllOutputCoherenceChargeGuardFalsifier
                          R.continuumStream
                          N
                          (R.allOutputCountableTailControl.prefix_charge N))) ∨
                    Nonempty (AllOutputEventRecurrencePriceMismatchFalsifier
                      R.continuumStream
                      R.eventRecurrence
                      R.allOutputEventRecurrenceCoupling) ∨
                    Nonempty (AllOutputEventRecurrenceCouplingGuardFalsifier
                      R.continuumStream
                      R.eventRecurrence
                      R.allOutputEventRecurrenceCoupling) ∨
                    Nonempty
                      (GP216ContinuumAllOutputFixedAtomsProvenanceFalsifier
                        R.continuumSource) ∨
                        Nonempty
                          (AllOutputDeclaredTargetBackfitFalsifier
                            R.continuumStream
                            R.allOutputCountableTailControl) ∨
                    Nonempty
                      (GP216EventRecurrenceSectionIncidenceMismatchFalsifier
                        R.eventRecurrenceSource) ∨
                    ¬ R.eventRecurrenceAuxiliaryPanels.Paid ∨
                    Nonempty
                      (GP216EventRecurrenceAuxiliaryPanelFalsifier
                        R.eventRecurrenceAuxiliaryPanels) ∨
                    Nonempty
                      (GP216EventRecurrencePDEHandoffFalsifier
                        R.eventRecurrenceSource.pdeHandoff) ∨
                    Nonempty
                      (EventDuhamelBernsteinLowerEnvelopeFalsifier
                        R.eventRecurrenceSource.ledger
                        R.eventRecurrenceSource.duhamelLowerEnvelope) ∨
                    Nonempty
                      (GP216HighHighSelfTaxPDEOutputLedgerProvenanceFalsifier
                        R) ∨
                      GP216HighHighSelfTaxPDEObligationGap R ∨
                        Nonempty
                          (HighHighSelfTaxPDEObligationFalsifier
                            R.highHighSelfTaxPDEObligation) ∨
                        Nonempty
                          (EventRecurrencePricePDEObligationFalsifier
                            R.eventRecurrencePDEObligation) ∨
                          GP216EventRecurrencePDEObligationGap R ∨
                            EventGainPrefixDiverges R.eventRecurrence ∨
                          GP216LowHighLipschitzReservePDEObligationGap R ∨
                          Nonempty
                            (LowHighLipschitzReservePDEObligationFalsifier
                              R.lowHighLipschitzReservePDEObligation) ∨
                          Nonempty
                            (LowHighEnergyBudgetShellReservePDEHandoffFalsifier
                              R.lowHighReservePDESource.energyBudgetPDEHandoff) ∨
                          (∀ B : Real, ∃ N : ℕ,
                            B < nsPrefixSum
                              R.lowHighEnergyBudgetShellReserveClosure.shellBudgetCost N) ∨
                          GP216ConcreteFourierLatencySymbolEscape R ∨
                          Nonempty
                            (GP216CoordinateReformulationSourceIdentityFalsifier
                              R) ∨
                          CoordinateReformulationSurvivor
                            R.coordinateReformulation ∨
                            Nonempty
                              (FlatTorusKillingModeProvenanceFalsifier
                                R.flatTorusKillingMode
                                R.flatTorusKillingModeProvenance) ∨
                            Nonempty
                              (FlatTorusLowHighKinematicPDEObligationFalsifier
                              R.flatTorusLowHighPDE) ∨
                            ¬ GP216FlatTorusPhaseCapacitySourcesPaid R ∨
                            Nonempty
                              (MacroscopicFlatTorusClockSourceFalsifier
                                R.macroscopicFlatTorusClockSource) ∨
                            Nonempty
                              (GP216FlatTorusPhaseCapacityHandoffFalsifier
                                R.flatTorusPhaseCapacityHandoff) ∨
                            Nonempty
                              (GP216PhaseLatencyProfileReserveSourceFalsifier
                                R) ∨
                            Nonempty
                              (GP216PhaseLatencyReserveSourceFalsifier R) ∨
                              GP216PhaseLatencyCapacityMismatch R ∨
                                GP216PhaseAlignmentControlEnergyEscape R ∨
                                  GP216ProfileLipschitzPhaseLatencyEscape R ∨
                                HarmonicDyadicPhaseLatencyEscape
                                  R.phaseLatencyLipschitzReserve ∨
                                  Nonempty
                                    (GP216LipschitzContinuationSourceFalsifier
                                      R) ∨
                                  Nonempty
                                    (GP216ProfileDecompositionSourceFalsifier
                                      R) ∨
                                  Nonempty
                                    (GP216ProfileDecompositionBridgeBundleFalsifier
                                      R) ∨
                                  Nonempty
                                    (TrackBProfileLipschitzSourceCouplingFalsifier
                                      R.profileLipschitzObligation) ∨
                                  Nonempty
                                    (GP216ProfileLipschitzAmplitudeSourceFalsifier
                                      R) ∨
                                  Nonempty
                                    (TrackBContinuationReceiptIdentityFalsifier
                                      R.continuationHandoff) ∨
                                  Nonempty
                                    (TrackBContinuationReceiptFalsifier
                                      R.continuationHandoff) ∨
                                  ¬ (R.profileLipschitzObligation.evolution_of_initial_data
                                    R.profileLipschitzInitialData).criticalControl ∨
                                    ¬ (R.profileLipschitzObligation.evolution_of_initial_data
                                      R.profileLipschitzInitialData).globalRegular ∨
                  ¬ R.continuationHandoff.self_tax_enstrophy.evolution.globalRegular)

/-- Branch threshold-defect component of the composite receipt.

This legacy theorem name is kept for callers that refer to the self-tax LSC
branch, but the proof now routes through the output-derived component-limit
receipt so the aggregate profile-LSC adapter is not load-bearing. -/
theorem gp216_branch_threshold_defect_of_self_tax_lsc
    (R : GP216BridgeCompositionReceipt) :
    ThresholdDefectConvexity R.branchBlock :=
  threshold_defect_of_leray_self_tax_audited_output_source_and_threshold_identities
    R.branchBlock
    R.selfTaxStream
    R.selfTaxOutputLimitSource
    R.branchSelfTaxThresholdCoordinateIdentities

/-- Branch threshold-defect component through the output-derived component
limit receipt.

This is the non-posthoc GP216 route: the scalar self-tax stream remains tied to
the audited Leray-output source while the payoff limit is charged, then the
same stream is handed to the branch-threshold coordinate receipt. -/
theorem gp216_branch_threshold_defect_of_output_derived_self_tax
    (R : GP216BridgeCompositionReceipt) :
    ThresholdDefectConvexity R.branchBlock :=
  threshold_defect_of_leray_self_tax_audited_output_source_and_threshold_identities
    R.branchBlock
    R.selfTaxStream
    R.selfTaxOutputLimitSource
    R.branchSelfTaxThresholdCoordinateIdentities

/-- Above-wall GP216 threshold-root defect through the output-derived
self-tax source.

This is the concrete branch algebra behind
`gp216_branch_threshold_defect_of_output_derived_self_tax`: the audited
Leray-output component limit passage charges the same scalar self-tax stream
that the branch threshold-coordinate identities evaluate at the quartic root.
-/
theorem gp216_branch_threshold_root_defect_of_output_derived_self_tax
    (R : GP216BridgeCompositionReceipt)
    (habove : sharpTarget < R.branchBlock.gamma) :
    1 ≤
      survivalDefect
        R.branchBlock
        (Real.sqrt (sharpTarget / R.branchBlock.gamma)) :=
  threshold_root_defect_ge_one_of_audited_output_source_and_threshold_identities
    R.branchBlock
    R.selfTaxStream
    R.selfTaxOutputLimitSource
    R.branchSelfTaxThresholdCoordinateIdentities
    habove

/-- The GP216 branch exposes the direct gain-at-amplitude cap through the
audited self-tax threshold-defect source and the generated amplitude
projection.

This is branch-scoped: it does not assert a global cap for arbitrary
`NSEvolution` blocks. -/
theorem GP216BridgeCompositionReceipt.branchGainAtAmpLeTarget
    (R : GP216BridgeCompositionReceipt) :
    R.branchBlock.gamma *
        R.branchQuarticSurvivalAmplitudeProjection.ampSq ≤
      sharpTarget :=
  gain_at_amp_le_target_of_quartic_survival_amplitude_projection
    R.branchBlock
    R.branchQuarticSurvivalAmplitudeProjection
    (gp216_branch_threshold_defect_of_output_derived_self_tax R)

/-- Above the sharp wall, the GP216 branch amplitude is bounded by the exact
threshold-root square. -/
theorem GP216BridgeCompositionReceipt.branchAmpSqLeThresholdRoot
    (R : GP216BridgeCompositionReceipt)
    (habove : sharpTarget < R.branchBlock.gamma) :
    R.branchQuarticSurvivalAmplitudeProjection.ampSq ≤
      (Real.sqrt (sharpTarget / R.branchBlock.gamma)) ^ (2 : Nat) :=
  amp_sq_le_threshold_root_of_gain_action_cap
    R.branchBlock
    habove
    R.branchGainAtAmpLeTarget

/-- Branch component of the composite receipt: the global admissible block has
no full-ledger survivor once the output-derived self-tax source supplies
threshold defect. -/
theorem gp216_branch_no_survivor
    (R : GP216BridgeCompositionReceipt) :
    FullLedgerNoSurvivor R.branchBlock :=
  full_ledger_no_survivor_of_quartic_survival_amplitude_projection
    R.branchBlock
    R.branchQuarticSurvivalAmplitudeProjection
    (gp216_branch_threshold_defect_of_output_derived_self_tax R)

/-- GP216 branch no-survivor through the generated profile/Lipschitz block.

This binds `branchBlock` to the actual block family generated by the
profile/Lipschitz obligation before the no-survivor result is consumed. -/
theorem gp216_branch_no_survivor_of_profile_lipschitz_generated_block
    (R : GP216BridgeCompositionReceipt) :
    FullLedgerNoSurvivor R.branchBlock := by
  rw [R.branch_matches_profile_lipschitz_generated_block]
  exact generated_lipschitz_block_no_survivor_of_trackB_profile_closure
    R.profileLipschitzObligation
    R.profileLipschitzInitialData
    R.profileLipschitzBranchIndex

/-- Coherence component of the composite receipt: uniform beat/backscatter
charging prevents a new limit surplus.

Even this scalar convenience theorem is routed through the named LP/Leray
source receipt; callers that need to audit source identity should use
`gp216_source_coherence_payoff_le_price` directly. -/
theorem gp216_coherence_payoff_le_price
    (R : GP216BridgeCompositionReceipt) :
    R.coherenceStream.payoffLimit ≤ R.coherenceStream.priceLimit :=
  lp_beat_backscatter_no_arbitrage_of_derived_limit_certificate
    R.coherenceSource
    R.coherenceStream
    R.coherenceSourceReceipt
    R.coherenceCertificate

/-- Source-preserving coherence component of the composite receipt.

This is the GP216-safe route: the LP/Leray beat/backscatter source remains
attached while the limit certificate is used to charge payoff by price. -/
theorem gp216_source_coherence_payoff_le_price
    (R : GP216BridgeCompositionReceipt) :
    R.coherenceSource.stream.payoffLimit ≤
      R.coherenceSource.stream.priceLimit :=
  lp_beat_backscatter_no_arbitrage_of_derived_limit_certificate
    R.coherenceSource
    R.coherenceStream
    R.coherenceSourceReceipt
    R.coherenceCertificate

/-- Source-preserving prefix form of the coherence component. -/
theorem gp216_source_coherence_prefix_not_unbounded
    (R : GP216BridgeCompositionReceipt) :
    ¬ LPBeatBackscatterPrefixPayoffUnbounded R.coherenceSource.stream :=
  no_unbounded_source_beat_backscatter_prefix_payoff_of_derived_limit_certificate
    R.coherenceSource
    R.coherenceStream
    R.coherenceSourceReceipt
    R.coherenceCertificate

/-- GP216-facing source-level uniform positive-coherence package. -/
theorem gp216_positive_coherence_uniformly_paid
    (R : GP216BridgeCompositionReceipt) :
    GP216PositiveCoherenceUniformlyPaid R :=
  ⟨lp_beat_backscatter_source_uniform_positive_coherence_paid
      R.coherenceSource,
    gp216_source_coherence_payoff_le_price R,
    gp216_source_coherence_prefix_not_unbounded R⟩

/-- Target-stream prefix form, derived through the declared source equality. -/
theorem gp216_coherence_prefix_not_unbounded
    (R : GP216BridgeCompositionReceipt) :
    ¬ LPBeatBackscatterPrefixPayoffUnbounded R.coherenceStream := by
  intro htarget
  have hsource : LPBeatBackscatterPrefixPayoffUnbounded
      R.coherenceSource.stream := by
    intro B
    obtain ⟨n, hn⟩ := htarget B
    refine ⟨n, ?_⟩
    simpa [R.coherenceSourceReceipt.prefix_receipt_eq_source n] using hn
  exact gp216_source_coherence_prefix_not_unbounded R hsource

/-- Continuation component of the composite receipt: finite self-tax plus the
separately declared standard continuation criterion gives global regularity in
the abstract evolution interface. -/
theorem gp216_continuation_global_regular
    (R : GP216BridgeCompositionReceipt) :
    R.continuationHandoff.self_tax_enstrophy.evolution.globalRegular :=
  global_regular_of_self_tax_and_enstrophy_continuation
    R.continuationHandoff.self_tax_enstrophy
    R.continuation_smooth
    R.continuation_energy

/-- Clay-facing continuation component: the abstract self-tax continuation
conclusion transfers to the generated profile/Lipschitz NSE evolution only
through the declared same-evolution handoff.

This prevents the composite receipt from closing on a detached
`SelfTaxNSEvolution` while leaving the actual generated evolution unproved. -/
theorem gp216_profile_lipschitz_global_regular
    (R : GP216BridgeCompositionReceipt) :
    (R.profileLipschitzObligation.evolution_of_initial_data
      R.profileLipschitzInitialData).globalRegular := by
  simpa [
    GP216BridgeCompositionReceipt.profileLipschitzObligation,
    GP216BridgeCompositionReceipt.profileLipschitzInitialData,
    GP216BridgeCompositionReceipt.continuationHandoff
  ] using
    global_regular_of_self_tax_enstrophy_handoff_to_profile_lipschitz
      R.continuationHandoff
      R.continuation_smooth
      R.continuation_energy

/-- GP216-facing critical-control handoff from the generated profile/Lipschitz
closure.

This exposes the BKM/continuation control variable before the final
continuation theorem is applied.  The source is the audited low-frequency
Lipschitz ledger/no-survivor route; the self-tax/enstrophy handoff may consume
this control through the same-PDE identity, but it is not the source of the
GP216 critical-control payment. -/
theorem gp216_profile_lipschitz_critical_control
    (R : GP216BridgeCompositionReceipt) :
    (R.profileLipschitzObligation.evolution_of_initial_data
      R.profileLipschitzInitialData).criticalControl := by
  exact critical_control_of_trackB_profile_lipschitz_closure
    R.profileLipschitzObligation
    R.profileLipschitzInitialData

/-- Flat-torus symmetry-breaker component: the finite Fourier/Killing receipt
must feed the continuum low-high PDE obligation before the phase-latency branch
is allowed into the GP-216 composition.

This is the anti-scaling-symmetry guard: the bridge is not allowed to use a
detached parabolic latency receipt while the torus zero-strain/Killing branch
remains unused. -/
theorem gp216_flat_torus_nonconstant_shell_transfer_forces_positive_deformation
    (R : GP216BridgeCompositionReceipt) :
    R.flatTorusLowHighPDE.nonconstant_shell_transfer_forces_positive_deformation :=
  flat_torus_nonconstant_transfer_of_killing_mode_adapter
    R.flatTorusLowHighPDE
    R.flatTorusKillingMode
    R.flatTorusKillingPDEAdapter

/-- GP216-facing full flat-torus source package consumed by phase capacity. -/
theorem gp216_flat_torus_phase_capacity_sources_paid
    (R : GP216BridgeCompositionReceipt) :
    GP216FlatTorusPhaseCapacitySourcesPaid R :=
  flat_torus_phase_capacity_sources_of_killing_mode_adapter
    R.flatTorusLowHighPDE
    R.flatTorusKillingMode
    R.flatTorusKillingPDEAdapter

/-- Phase-capacity bound derived from an explicit paid flat-torus source
package.

This is the source-consuming form used by the final contradiction: the
capacity handoff is not allowed to recompute or bypass the flat-torus/Killing
source facts already exposed as `GP216FlatTorusPhaseCapacitySourcesPaid`. -/
theorem gp216_flat_torus_feeds_phase_latency_capacity_of_sources
    (R : GP216BridgeCompositionReceipt)
    (hsources : GP216FlatTorusPhaseCapacitySourcesPaid R) :
    ∀ j : ℕ,
      R.phaseLatencyLipschitzReserve.phase.reach j *
          R.phaseLatencyLipschitzReserve.phase.kNorm j ≤
        R.phaseLatencyLipschitzReserve.phase.gramianConstant := by
  rcases hsources with
    ⟨hshell, hdeformation, hreserveLoss, htrackBPrice⟩
  exact
    R.flatTorusPhaseCapacityHandoff.capacity_of_flat_torus_sources
      R.flatTorusPhaseCapacityHandoff.fixed_flat_torus_phase_symbol_topology_paid
      R.flatTorusPhaseCapacityHandoff.phase_reach_identified_with_killing_clock_paid
      R.flatTorusPhaseCapacityHandoff.macroscopic_clock_budget_charged_in_trackb_reserve_paid
      hshell
      hdeformation
      hreserveLoss
      htrackBPrice

/-- Phase-capacity bound projected directly from the mandatory macroscopic
flat-torus clock source. -/
theorem gp216_flat_torus_feeds_phase_latency_capacity_of_macroscopic_clock_source
    (R : GP216BridgeCompositionReceipt) :
    ∀ j : ℕ,
      R.phaseLatencyLipschitzReserve.phase.reach j *
          R.phaseLatencyLipschitzReserve.phase.kNorm j ≤
        R.phaseLatencyLipschitzReserve.phase.gramianConstant :=
  phase_capacity_of_macroscopic_flat_torus_clock_source
    R.macroscopicFlatTorusClockSource

/-- GP216-facing flat-torus mode obstruction derived through the explicit
zero-strain/Killing-field provenance chain. -/
theorem gp216_flat_torus_mode_shell_transfer_requires_nonzero_strain
    (R : GP216BridgeCompositionReceipt) :
    R.flatTorusKillingMode.shell_transfer_requires_nonzero_strain :=
  shell_transfer_requires_nonzero_strain_of_killing_mode_provenance
    R.flatTorusKillingMode
    R.flatTorusKillingModeProvenance

/-- The phase-latency parabolic capacity used by the bridge must be supplied
through the flat-torus low-high PDE branch, not by an unpriced microscopic
rescaling lane. -/
theorem gp216_flat_torus_feeds_phase_latency_capacity
    (R : GP216BridgeCompositionReceipt) :
    ∀ j : ℕ,
      R.phaseLatencyLipschitzReserve.phase.reach j *
          R.phaseLatencyLipschitzReserve.phase.kNorm j ≤
        R.phaseLatencyLipschitzReserve.phase.gramianConstant :=
  gp216_flat_torus_feeds_phase_latency_capacity_of_macroscopic_clock_source R

/-- The low-high Lipschitz reserve PDE checklist is an explicit paid component
of the GP216 receipt.

This theorem does not prove the LP/Bony estimate; it makes the already-carried
receipt field visible as a named proof-spine component before the global
candidate is discharged. -/
theorem gp216_low_high_lipschitz_reserve_pde_obligation_paid
    (R : GP216BridgeCompositionReceipt) :
    LowHighLipschitzReservePDEObligationSatisfied
      R.lowHighLipschitzReservePDEObligation :=
  R.lowHighLipschitzReservePDEObligationSatisfied

/-- The GP216 low-high reserve source excludes handoff-falsifier branches for
the exact energy-budget PDE handoff it carries. -/
theorem gp216_no_low_high_energy_budget_shell_reserve_pde_handoff_falsifier
    (R : GP216BridgeCompositionReceipt) :
    ¬ Nonempty
      (LowHighEnergyBudgetShellReservePDEHandoffFalsifier
        R.lowHighReservePDESource.energyBudgetPDEHandoff) := by
  intro hfalsifier
  rcases hfalsifier with ⟨hfalsifier⟩
  exact
    no_low_high_energy_budget_shell_reserve_pde_handoff_falsifier
      R.lowHighReservePDESource.energyBudgetPDEHandoff
      hfalsifier

/-- The generated low-high shell market-impact prefix cannot diverge inside a
valid GP216 receipt.

The proof routes through the generated profile/Lipschitz ledger and its
predeclared shell reserve closure; it does not introduce a new pressure or
continuation assumption. -/
theorem gp216_no_unbounded_low_high_market_impact_prefix
    (R : GP216BridgeCompositionReceipt) :
    ¬ (∀ B : Real, ∃ N : ℕ,
      B < nsPrefixSum
        R.lowHighEnergyBudgetShellReserveClosure.shellBudgetCost N) :=
  no_unbounded_low_high_energy_budget_market_impact_prefix_under_trackB_profile_closure
    R.profileLipschitzObligation
    R.profileLipschitzInitialData
    R.lowHighEnergyBudgetShellReserveClosure

/-- A concrete Fourier `|k_j| / j` latency-symbol escape cannot survive the
generated Track B profile/Lipschitz ledger. -/
theorem gp216_no_concrete_fourier_latency_symbol_escape
    (R : GP216BridgeCompositionReceipt) :
    ¬ GP216ConcreteFourierLatencySymbolEscape R := by
  intro hescape
  rcases hescape with ⟨S, hunbounded⟩
  exact no_concrete_fourier_latency_symbol_escape_under_trackB_profile_closure
    R.profileLipschitzObligation
    R.profileLipschitzInitialData
    S
    hunbounded

/-- The concrete Fourier symbol stored in GP216 cannot itself carry an
unbounded `|k_j| / j` schedule.

This is the source-visible form of
`gp216_no_concrete_fourier_latency_symbol_escape`: consumers that already have
the stored `phaseLatencyConcreteFourierSymbol` should use this edge directly
instead of rebuilding the existential escape package. -/
theorem GP216BridgeCompositionReceipt.no_stored_concrete_fourier_latency_symbol_unbounded
    (R : GP216BridgeCompositionReceipt)
    (hunbounded :
      ∀ B : Real, ∃ n : ℕ,
        B < R.phaseLatencyConcreteFourierSymbol.shellOverIndex n) :
    False :=
  no_concrete_fourier_latency_symbol_escape_under_trackB_profile_closure
    R.profileLipschitzObligation
    R.profileLipschitzInitialData
    R.phaseLatencyConcreteFourierSymbol
    hunbounded

/-- The integrated phase-alignment control-energy escape cannot survive inside
the generated GP216 profile/Lipschitz branch.

The discharge is source-preserving: every phase-alignment energy entry is
already required by `PhaseAlignmentProfileLipschitzEscapeAttempt` to embed in
the generated low-frequency Lipschitz ledger. -/
theorem gp216_no_phase_alignment_control_energy_escape
    (R : GP216BridgeCompositionReceipt) :
    ¬ GP216PhaseAlignmentControlEnergyEscape R := by
  intro hescape
  rcases hescape with ⟨A⟩
  exact
    no_phase_alignment_control_energy_escape_of_profile_lipschitz_closure
      R.profileLipschitzObligation
      R.profileLipschitzInitialData
      A

/-- The profile-tied harmonic phase-latency escape cannot survive inside the
generated GP216 profile/Lipschitz branch.

This is the non-detached version of the phase-latency branch: the existing
profile/Lipschitz phase-latency theorem consumes the generated Lipschitz
embedding and excludes the harmonic/dyadic escape inside that same ledger. -/
theorem gp216_no_profile_lipschitz_phase_latency_escape
    (R : GP216BridgeCompositionReceipt) :
    ¬ GP216ProfileLipschitzPhaseLatencyEscape R := by
  intro hescape
  rcases hescape with ⟨A⟩
  exact
    no_phase_latency_escape_of_profile_lipschitz_closure
      R.profileLipschitzObligation
      R.profileLipschitzInitialData
      A

/-- Main GP-216/5IQ bridge composition receipt.

Given the declared branch theorem, profile LSC self-tax receipt,
beat/backscatter coherence certificate, finite low-beat reserve, and standard
continuation bridge, there is no remaining survivor/global bridge candidate in
the declared scope. -/
theorem no_gp216_global_bridge_candidate_of_composition_receipt
    (R : GP216BridgeCompositionReceipt) :
    ¬ GP216GlobalBridgeCandidateWithinDeclaredScope R := by
  intro hcandidate
  rcases hcandidate with ⟨_, hbad⟩
  have hbranchThresholdDefect :
      ThresholdDefectConvexity R.branchBlock :=
    gp216_branch_threshold_defect_of_output_derived_self_tax R
  have hbranchGenerated :
      FullLedgerNoSurvivor R.branchBlock :=
    gp216_branch_no_survivor_of_profile_lipschitz_generated_block R
  have hquarticProjectionGuard :
      ¬ Nonempty
        (QuarticSurvivalProjectionGuardFalsifier
          R.branchBlock
          R.branchQuarticSurvivalProjection) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_quartic_survival_projection_guard_falsifier
      R.branchBlock
      R.branchQuarticSurvivalProjection
      hbad
  have hquarticAmplitudeProjection :
      ¬ Nonempty
        (QuarticSurvivalAmplitudeProjectionFalsifier
          R.branchBlock
          R.branchQuarticSurvivalAmplitudeProjection) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_quartic_survival_amplitude_projection_falsifier
      R.branchBlock
      R.branchQuarticSurvivalAmplitudeProjection
      hbad
  have hquarticProjectionCap :
      ¬ Nonempty
        (QuarticSurvivalProjectionCapFalsifier
          R.branchBlock
          R.branchQuarticSurvivalProjection) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_quartic_survival_projection_cap_falsifier
      R.branchBlock
      R.branchQuarticSurvivalProjection
      hbad
  have hbranchGeneratedBlockIdentity :
      ¬ Nonempty
        (GP216BranchGeneratedBlockIdentityFalsifier
          R) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact
      no_gp216_branch_generated_block_identity_falsifier
        R
        hbad
  have hself :
      ¬ GlobalLeraySelfTaxArbitrage R.selfTaxStream :=
    no_global_self_tax_arbitrage_under_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
  have hselfContinuumTarget :
      ¬ continuumGlobalSelfTaxTarget R.continuumStream <
        R.selfTaxStream.payoffLimit := by
    exact not_lt_of_ge
      (gp216_self_tax_payoff_le_continuum_global_target R)
  have hselfIntegral :
      ¬ LeraySelfTaxPrefixIntegralUnbounded
        R.selfTaxStream
        R.selfTaxOutputLocalToGlobalAssembly :=
    no_prefix_self_tax_integral_escape_under_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
  have hselfAssembly :
      ¬ LeraySelfTaxPrefixAssemblyUndercharged
        R.selfTaxStream
        R.selfTaxOutputLocalToGlobalAssembly :=
    no_prefix_assembly_undercharge_under_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
  have hselfFinitePrefix :
      ¬ Nonempty
        (LeraySelfTaxFinitePrefixArbitrageFalsifier
          R.selfTaxStream) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_finite_prefix_arbitrage_under_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
      hbad
  have hselfFinitePrefixChargeGuard :
      ¬ Nonempty
        (LeraySelfTaxFinitePrefixChargeGuardFalsifier
          R.selfTaxStream
          R.selfTaxOutputLocalToGlobalAssembly
          R.selfTaxOutputFinitePrefixCharge) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_finite_prefix_charge_guard_falsifier_under_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
      hbad
  have hselfPayoffApprox :
      ¬ Nonempty
        (LeraySelfTaxPayoffApproximationFalsifier
          R.selfTaxStream) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_payoff_approximation_gap_under_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
      hbad
  have hselfTailPayoffApprox :
      ¬ Nonempty
        (LeraySelfTaxPayoffTailApproximationFalsifier
          R.selfTaxStream) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_tail_payoff_approximation_gap_under_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
      hbad
  have hselfComponentLSC :
      ¬ Nonempty
        (LeraySelfTaxComponentLSCFalsifier
          R.selfTaxStream) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_component_lsc_falsifier_under_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
      hbad
  have hselfTotalLSC :
      ¬ Nonempty
        (LeraySelfTaxTotalLSCFalsifier
          R.selfTaxStream) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_total_lsc_falsifier_under_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
      hbad
  have hselfUnchargedOutputDefect :
      ¬ Nonempty
        (LeraySelfTaxUnchargedOutputDefectFalsifier
          R.selfTaxOutputLimitSource.output_limit_price) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_uncharged_output_defect_of_audited_source
      R.selfTaxStream
      R.selfTaxOutputLimitSource
      hbad
  have hselfRelaxedOutputDefectFloor :
      ¬ Nonempty
        (LeraySelfTaxRelaxedOutputDefectFloorFalsifier
          R.selfTaxOutputLimitSource.output_limit_price) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_relaxed_output_defect_floor_falsifier_of_audited_source
      R.selfTaxStream
      R.selfTaxOutputLimitSource
      hbad
  have hselfOutputLimitPricePDEGuard :
      ¬ Nonempty
        (LeraySelfTaxOutputLimitPricePDEGuardFalsifier
          R.selfTaxOutputLimitSource.output_limit_price) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_output_limit_price_pde_guard_falsifier_of_audited_source
      R.selfTaxStream
      R.selfTaxOutputLimitSource
      hbad
  have hselfOutputLimitGuard :
      ¬ Nonempty
        (LeraySelfTaxOutputLimitPassageGuardFalsifier
          R.selfTaxStream
          R.selfTaxOutputLimitSource) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_output_limit_passage_guard_falsifier_of_audited_source
      R.selfTaxStream
      R.selfTaxOutputLimitSource
      hbad
  have hselfOutputSourceSubstitution :
      ¬ Nonempty (GP216SelfTaxOutputSourceSubstitutionFalsifier R) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact GP216SelfTaxAuditedOutputSourceBundle.noOutputSourceSubstitutionFalsifier
      R.selfTaxOutputSource
      hbad
  have hselfEndpointGuard :
      ¬ Nonempty (GP216SelfTaxEndpointGuardFalsifier R) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_trackb_self_tax_endpoint_guard_falsifier_of_output_derived
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
      hbad
  have hselfPostHoc :
      ¬ Nonempty
        (LeraySelfTaxPostHocStreamFalsifier
          R.selfTaxStream) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_output_derived_component_limit_passage_of_posthoc_leray_self_tax_stream
      R.selfTaxStream
      hbad
      R.selfTaxOutputDerivedComponentLimitPassage
  have hselfAssemblyMismatch :
      ¬ Nonempty
        (LeraySelfTaxAssemblyBudgetMismatchFalsifier
          R.selfTaxStream R.selfTaxOutputLocalToGlobalAssembly) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_assembly_budget_mismatch_under_output_derived_component_limit_passage
      R.selfTaxStream
      R.selfTaxOutputDerivedComponentLimitPassage
      hbad
  have hselfContinuumMismatch :
      ¬ Nonempty
        (LeraySelfTaxContinuumCouplingMismatchFalsifier
          R.selfTaxStream R.continuumStream) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_leray_self_tax_continuum_coupling_mismatch
      R.selfTaxStream
      R.continuumStream
      R.selfTaxContinuumCoupling
      hbad
  have hbranchCoordinateMismatch :
      ¬ Nonempty
        (BranchSelfTaxThresholdCoordinateIdentityMismatchFalsifier
          R.branchBlock R.selfTaxStream) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_branch_self_tax_threshold_coordinate_identity_mismatch
      R.branchBlock
      R.selfTaxStream
      R.branchSelfTaxThresholdCoordinateIdentities
      hbad
  have hbranchCoordinateGuard :
      ¬ Nonempty
        (BranchSelfTaxThresholdCoordinateGuardFalsifier
          R.branchBlock
          R.selfTaxStream
          R.branchSelfTaxThresholdCoordinateIdentities) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_branch_self_tax_threshold_coordinate_guard_falsifier
      R.branchBlock
      R.selfTaxStream
      R.branchSelfTaxThresholdCoordinateIdentities
      hbad
  have hbranchProfileFamilySelfTaxIdentity :
      ¬ Nonempty
        (GP216BranchProfileFamilySelfTaxStreamIdentityFalsifier
          R) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact
      no_gp216_branch_profile_family_self_tax_stream_identity_falsifier
        R
        hbad
  have hcoherenceSource :
      ¬ Nonempty
        (LPBeatBackscatterSourceSubstitutionFalsifier
          R.coherenceSource
          R.coherenceStream
          R.coherenceSourceReceipt) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_lp_beat_backscatter_source_substitution_falsifier
      R.coherenceSource
      R.coherenceStream
      R.coherenceSourceReceipt
      hbad
  have hpositiveCoherenceUniform :
      GP216PositiveCoherenceUniformlyPaid R :=
    gp216_positive_coherence_uniformly_paid R
  have hlowBeatGuard :
      ¬ Nonempty (LowBeatPrefixReserveGuardFalsifier R.lowBeatStream) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_low_beat_prefix_reserve_guard_falsifier
      R.lowBeatStream
      hbad
  have hlowBeatEnvelopeSource :
      ¬ Nonempty
        (GP216LowBeatEnvelopeSourceFalsifier
          R.lowBeatEnvelopeSource) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact no_gp216_low_beat_envelope_source_falsifier
      R.lowBeatEnvelopeSource
      hbad
  have hcontinuation :
      R.continuationHandoff.self_tax_enstrophy.evolution.globalRegular :=
    gp216_continuation_global_regular R
  have hprofileRegular :
      (R.profileLipschitzObligation.evolution_of_initial_data
        R.profileLipschitzInitialData).globalRegular :=
    gp216_profile_lipschitz_global_regular R
  have hprofileCritical :
      (R.profileLipschitzObligation.evolution_of_initial_data
        R.profileLipschitzInitialData).criticalControl :=
    gp216_profile_lipschitz_critical_control R
  have hfixedPrefix :
      ¬ FixedPrefixLowBeatSurvivor R.fixedPrefixLowBeat :=
    no_fixed_prefix_low_beat_survivor R.fixedPrefixLowBeat
  have hmovingAllOutput :
      ¬ MovingAllOutputLowBeatSurvivor R.movingAllOutputLowBeat :=
    no_moving_all_output_low_beat_survivor R.movingAllOutputLowBeat
  have hcontinuum :
      ¬ ContinuumLPSmoothEscapeCandidate R.continuumStream :=
    no_smooth_escape_of_countable_all_output_gram_tail_control
      R.continuumStream
      R.allOutputCountableTailControl
  have hcontinuumLSCFailure :
      ¬ Nonempty (AllOutputCoherencePriceLSCFailureFalsifier
        R.continuumStream) :=
    no_all_output_coherence_lsc_failure_of_countable_gram_tail_control
      R.continuumStream
      R.allOutputCountableTailControl
  have hcontinuumFixedAtomsGuard :
      ¬ Nonempty
        (FixedAllOutputLPBonyAtomsGuardFalsifier
          R.continuumStream
          R.allOutputCountableTailControl.fixed_atoms) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact
      no_fixed_all_output_lp_bony_atoms_guard_falsifier
        R.continuumStream
        R.allOutputCountableTailControl.fixed_atoms
        hbad
  have hallOutputPrefixChargeGuard :
      ¬ (∃ N : ℕ,
        Nonempty
          (PrefixAllOutputCoherenceChargeGuardFalsifier
            R.continuumStream
            N
            (R.allOutputCountableTailControl.prefix_charge N))) := by
    intro hbad
    rcases hbad with ⟨N, hguard⟩
    rcases hguard with ⟨hguard⟩
    exact
      no_prefix_all_output_coherence_charge_guard_falsifier
        R.continuumStream
        N
        (R.allOutputCountableTailControl.prefix_charge N)
        hguard
  have hcouplingMismatch :
      ¬ Nonempty (AllOutputEventRecurrencePriceMismatchFalsifier
        R.continuumStream
        R.eventRecurrence
        R.allOutputEventRecurrenceCoupling) := by
    intro hmismatch
    rcases hmismatch with ⟨hmismatch⟩
    exact no_all_output_event_recurrence_coupling_of_price_mismatch
      R.continuumStream
      R.eventRecurrence
      R.allOutputEventRecurrenceCoupling
      hmismatch
  have hcouplingGuard :
      ¬ Nonempty (AllOutputEventRecurrenceCouplingGuardFalsifier
        R.continuumStream
        R.eventRecurrence
        R.allOutputEventRecurrenceCoupling) := by
    intro hguard
    rcases hguard with ⟨hguard⟩
    exact no_all_output_event_recurrence_coupling_guard_falsifier
      R.continuumStream
      R.eventRecurrence
      R.allOutputEventRecurrenceCoupling
      hguard
  have hcontinuumFixedAtomsProvenance :
      ¬ Nonempty
        (GP216ContinuumAllOutputFixedAtomsProvenanceFalsifier
          R.continuumSource) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_gp216_continuum_all_output_fixed_atoms_provenance_falsifier
      R.continuumSource
      hfalsifier
  have hallOutputBackfitGuard :
      ¬ Nonempty
        (AllOutputDeclaredTargetBackfitFalsifier
          R.continuumStream
          R.allOutputCountableTailControl) := by
    intro hguard
    rcases hguard with ⟨hguard⟩
    exact
      no_all_output_declared_target_backfit_falsifier_of_countable_gram_tail_control
        R.continuumStream
        R.allOutputCountableTailControl
        hguard
  have heventSectionIncidenceMismatch :
      ¬ Nonempty
        (GP216EventRecurrenceSectionIncidenceMismatchFalsifier
          R.eventRecurrenceSource) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact
      no_gp216_event_recurrence_section_incidence_mismatch_falsifier
        R.eventRecurrenceSource
        hfalsifier
  have heventAuxiliaryPanelsPaid :
      R.eventRecurrenceAuxiliaryPanels.Paid :=
    R.eventRecurrenceAuxiliaryPanels.paid
  have heventAuxiliaryPanelFalsifier :
      ¬ Nonempty
        (GP216EventRecurrenceAuxiliaryPanelFalsifier
          R.eventRecurrenceAuxiliaryPanels) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_gp216_event_recurrence_auxiliary_panel_falsifier
      R.eventRecurrenceAuxiliaryPanels
      hfalsifier
  have heventPDEHandoffFalsifier :
      ¬ Nonempty
        (GP216EventRecurrencePDEHandoffFalsifier
          R.eventRecurrenceSource.pdeHandoff) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_gp216_event_recurrence_pde_handoff_falsifier
      R.eventRecurrenceSource.pdeHandoff
      hfalsifier
  have heventDuhamelLowerEnvelopeFalsifier :
      ¬ Nonempty
        (EventDuhamelBernsteinLowerEnvelopeFalsifier
          R.eventRecurrenceSource.ledger
          R.eventRecurrenceSource.duhamelLowerEnvelope) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_event_duhamel_bernstein_lower_envelope_falsifier
      R.eventRecurrenceSource.ledger
      R.eventRecurrenceSource.duhamelLowerEnvelope
      hfalsifier
  have hhighHighOutputLedgerProvenance :
      ¬ Nonempty
        (GP216HighHighSelfTaxPDEOutputLedgerProvenanceFalsifier R) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact
      no_gp216_high_high_self_tax_pde_output_ledger_provenance_falsifier
        R
        hfalsifier
  have hhighHighPDEObligation :
      ¬ GP216HighHighSelfTaxPDEObligationGap R := by
    intro hgap
    exact hgap R.highHighSelfTaxPDEObligationSatisfied
  have hhighHighPDEObligationFalsifier :
      ¬ Nonempty
        (HighHighSelfTaxPDEObligationFalsifier
          R.highHighSelfTaxPDEObligation) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_high_high_self_tax_pde_obligation_falsifier
      R.highHighSelfTaxPDEObligation
      R.highHighSelfTaxPDEObligationSatisfied
      hfalsifier
  have heventPDEObligation :
      ¬ GP216EventRecurrencePDEObligationGap R := by
    intro hgap
    exact hgap R.eventRecurrencePDEObligationSatisfied
  have heventPDEObligationFalsifier :
      ¬ Nonempty
        (EventRecurrencePricePDEObligationFalsifier
          R.eventRecurrencePDEObligation) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_event_recurrence_price_pde_obligation_falsifier
      R.eventRecurrencePDEObligation
      R.eventRecurrencePDEObligationSatisfied
      hfalsifier
  have heventRecurrence :
      ¬ EventGainPrefixDiverges R.eventRecurrence :=
    no_divergent_event_gain_prefix_of_event_price_bridge
      R.eventRecurrence
      R.eventRecurrenceCertificate
  have hlowHighPDEObligation :
      ¬ GP216LowHighLipschitzReservePDEObligationGap R := by
    intro hgap
    exact hgap
      (gp216_low_high_lipschitz_reserve_pde_obligation_paid R)
  have hlowHighPDEObligationFalsifier :
      ¬ Nonempty
        (LowHighLipschitzReservePDEObligationFalsifier
          R.lowHighLipschitzReservePDEObligation) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_low_high_lipschitz_reserve_pde_obligation_falsifier
      R.lowHighLipschitzReservePDEObligation
      (gp216_low_high_lipschitz_reserve_pde_obligation_paid R)
      hfalsifier
  have hlowHighPDEHandoffFalsifier :
      ¬ Nonempty
        (LowHighEnergyBudgetShellReservePDEHandoffFalsifier
          R.lowHighReservePDESource.energyBudgetPDEHandoff) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact
      no_low_high_energy_budget_shell_reserve_pde_handoff_falsifier
        R.lowHighReservePDESource.energyBudgetPDEHandoff
        hfalsifier
  have hphaseLatency :
      ¬ HarmonicDyadicPhaseLatencyEscape
        R.phaseLatencyLipschitzReserve :=
    no_harmonic_dyadic_phase_latency_escape_under_lipschitz_reserve
      R.phaseLatencyLipschitzReserve
  have hprofileLipschitzContinuationSource :
      ¬ Nonempty (GP216LipschitzContinuationSourceFalsifier R) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact
      no_low_frequency_lipschitz_bridge_continuation_source_falsifier
        R.profileLipschitzObligation.lipschitz_bridge
        (GP216ProfileLipschitzEvolution R)
        hfalsifier
  have hprofileDecompositionSource :
      ¬ Nonempty (GP216ProfileDecompositionSourceFalsifier R) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_trackb_profile_decomposition_source_receipt_of_falsifier
      R.profileLipschitzObligation.profile_obligation.source_receipt
      hfalsifier
  have hprofileDecompositionBundle :
      ¬ Nonempty
        (GP216ProfileDecompositionBridgeBundleFalsifier R) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_trackb_profile_decomposition_bridge_bundle_falsifier
      R.profileLipschitzObligation.profile_bundle
      hfalsifier
  have hprofileLipschitzSourceCoupling :
      ¬ Nonempty
        (TrackBProfileLipschitzSourceCouplingFalsifier
          R.profileLipschitzObligation) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_trackB_profile_lipschitz_source_coupling_falsifier
      R.profileLipschitzObligation
      hfalsifier
  have hprofileLipschitzAmplitudeObservableSource :
      ¬ Nonempty
        (TrackBProfileLipschitzGeneratedAmplitudeObservableSourceFalsifier
          R.profileLipschitzObligation) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact
      no_trackB_profile_lipschitz_generated_amplitude_observable_source_falsifier
        R.profileLipschitzObligation
        hfalsifier
  have hlowHighPrefix :
      ¬ (∀ B : Real, ∃ N : ℕ,
        B < nsPrefixSum
          R.lowHighEnergyBudgetShellReserveClosure.shellBudgetCost N) :=
    gp216_no_unbounded_low_high_market_impact_prefix R
  have hconcreteFourierSymbol :
      ¬ GP216ConcreteFourierLatencySymbolEscape R :=
    gp216_no_concrete_fourier_latency_symbol_escape R
  have hcoordinateSourceIdentity :
      ¬ Nonempty
        (GP216CoordinateReformulationSourceIdentityFalsifier R) := by
    intro hbad
    rcases hbad with ⟨hbad⟩
    exact
      no_gp216_coordinate_reformulation_source_identity_falsifier
        R
        hbad
  have hflatTorusPhaseCapacitySources :
      GP216FlatTorusPhaseCapacitySourcesPaid R :=
    gp216_flat_torus_phase_capacity_sources_paid R
  have hflatTorusPhaseCapacityHandoff :
      ¬ Nonempty
        (GP216FlatTorusPhaseCapacityHandoffFalsifier
          R.flatTorusPhaseCapacityHandoff) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_gp216_flat_torus_phase_capacity_handoff_falsifier
      R.flatTorusPhaseCapacityHandoff
      hfalsifier
  have hmacroscopicFlatTorusClockSource :
      ¬ Nonempty
        (MacroscopicFlatTorusClockSourceFalsifier
          R.macroscopicFlatTorusClockSource) :=
    gp216_no_macroscopic_flat_torus_clock_source_falsifier R
  have hphaseLatencyProfileReserveSource :
      ¬ Nonempty
        (GP216PhaseLatencyProfileReserveSourceFalsifier R) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact
      no_gp216_phase_latency_profile_reserve_source_falsifier
        R
        hfalsifier
  have hphaseLatencyReserveSource :
      ¬ Nonempty (GP216PhaseLatencyReserveSourceFalsifier R) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_gp216_phase_latency_reserve_source_falsifier
      R
      hfalsifier
  have hphaseCapacity :
      ¬ GP216PhaseLatencyCapacityMismatch R := by
    intro hbadCapacity
    unfold GP216PhaseLatencyCapacityMismatch at hbadCapacity
    rcases hbadCapacity with ⟨j, hj⟩
    exact not_lt_of_ge
      (gp216_flat_torus_feeds_phase_latency_capacity R j)
      hj
  have hphaseAlignment :
      ¬ GP216PhaseAlignmentControlEnergyEscape R :=
    gp216_no_phase_alignment_control_energy_escape R
  have hprofilePhaseLatency :
      ¬ GP216ProfileLipschitzPhaseLatencyEscape R :=
    gp216_no_profile_lipschitz_phase_latency_escape R
  have hcoordinate :
      ¬ CoordinateReformulationSurvivor R.coordinateReformulation := by
    have hsource :
        FullLedgerNoSurvivor R.coordinateReformulation.source := by
      rw [R.coordinate_source_is_branch]
      exact hbranchGenerated
    exact
      no_coordinate_reformulation_survivor_of_source_no_survivor
        R.coordinateReformulation
        hsource
  have hflatTorusPDEObligation :
      ¬ Nonempty
        (FlatTorusLowHighKinematicPDEObligationFalsifier
          R.flatTorusLowHighPDE) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_flat_torus_low_high_kinematic_pde_obligation_falsifier
      R.flatTorusLowHighPDE
      R.flatTorusLowHighPDESatisfied
      hfalsifier
  have hflatTorusKillingModeProvenance :
      ¬ Nonempty
        (FlatTorusKillingModeProvenanceFalsifier
          R.flatTorusKillingMode
          R.flatTorusKillingModeProvenance) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_flat_torus_killing_mode_provenance_falsifier
      R.flatTorusKillingMode
      R.flatTorusKillingModeProvenance
      hfalsifier
  have hcontinuationHandoff :
      ¬ Nonempty (TrackBContinuationReceiptFalsifier R.continuationHandoff) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_trackB_continuation_receipt_falsifier
      R.continuationHandoff
      hfalsifier
  have hcontinuationIdentity :
      ¬ Nonempty
        (TrackBContinuationReceiptIdentityFalsifier
          R.continuationHandoff) := by
    intro hfalsifier
    rcases hfalsifier with ⟨hfalsifier⟩
    exact no_trackB_continuation_receipt_identity_falsifier
      R.continuationHandoff
      hfalsifier
  rcases hbad with hquarticProjectionGuardEscape | hbad
  · exact hquarticProjectionGuard hquarticProjectionGuardEscape
  rcases hbad with hquarticAmplitudeProjectionEscape | hbad
  · exact hquarticAmplitudeProjection hquarticAmplitudeProjectionEscape
  rcases hbad with hquarticProjectionCapEscape | hbad
  · exact hquarticProjectionCap hquarticProjectionCapEscape
  rcases hbad with hbranchGeneratedBlockIdentityEscape | hbad
  · exact hbranchGeneratedBlockIdentity
      hbranchGeneratedBlockIdentityEscape
  rcases hbad with hbranchSurvivor | hbad
  · exact hquarticProjectionCap
      (nonempty_quartic_survival_projection_cap_falsifier_of_threshold_defect_and_survivor
        R.branchBlock
        R.branchQuarticSurvivalProjection
        hbranchThresholdDefect
        hbranchSurvivor)
  rcases hbad with hselfArbitrage | hbad
  · exact hself hselfArbitrage
  rcases hbad with hselfContinuumTargetEscape | hbad
  · exact hselfContinuumTarget hselfContinuumTargetEscape
  rcases hbad with hselfIntegralEscape | hbad
  · exact hselfIntegral hselfIntegralEscape
  rcases hbad with hselfAssemblyEscape | hbad
  · exact hselfAssembly hselfAssemblyEscape
  rcases hbad with hselfFinitePrefixEscape | hbad
  · exact hselfFinitePrefix hselfFinitePrefixEscape
  rcases hbad with hselfFinitePrefixChargeGuardEscape | hbad
  · exact hselfFinitePrefixChargeGuard hselfFinitePrefixChargeGuardEscape
  rcases hbad with hselfPayoffApproxEscape | hbad
  · exact hselfPayoffApprox hselfPayoffApproxEscape
  rcases hbad with hselfTailPayoffApproxEscape | hbad
  · exact hselfTailPayoffApprox hselfTailPayoffApproxEscape
  rcases hbad with hselfComponentLSCEscape | hbad
  · exact hselfComponentLSC hselfComponentLSCEscape
  rcases hbad with hselfTotalLSCEscape | hbad
  · exact hselfTotalLSC hselfTotalLSCEscape
  rcases hbad with hselfUnchargedOutputDefectEscape | hbad
  · exact hselfUnchargedOutputDefect hselfUnchargedOutputDefectEscape
  rcases hbad with hselfRelaxedOutputDefectFloorEscape | hbad
  · exact hselfRelaxedOutputDefectFloor
      hselfRelaxedOutputDefectFloorEscape
  rcases hbad with hselfOutputLimitPricePDEGuardEscape | hbad
  · exact hselfOutputLimitPricePDEGuard
      hselfOutputLimitPricePDEGuardEscape
  rcases hbad with hselfOutputLimitGuardEscape | hbad
  · exact hselfOutputLimitGuard hselfOutputLimitGuardEscape
  rcases hbad with hselfOutputSourceSubstitutionEscape | hbad
  · exact hselfOutputSourceSubstitution
      hselfOutputSourceSubstitutionEscape
  rcases hbad with hselfEndpointGuardEscape | hbad
  · exact hselfEndpointGuard hselfEndpointGuardEscape
  rcases hbad with hselfPostHocEscape | hbad
  · exact hselfPostHoc hselfPostHocEscape
  rcases hbad with hselfAssemblyMismatchEscape | hbad
  · exact hselfAssemblyMismatch hselfAssemblyMismatchEscape
  rcases hbad with hselfContinuumMismatchEscape | hbad
  · exact hselfContinuumMismatch hselfContinuumMismatchEscape
  rcases hbad with hbranchCoordinateMismatchEscape | hbad
  · exact hbranchCoordinateMismatch hbranchCoordinateMismatchEscape
  rcases hbad with hbranchCoordinateGuardEscape | hbad
  · exact hbranchCoordinateGuard hbranchCoordinateGuardEscape
  rcases hbad with hbranchProfileFamilySelfTaxIdentityEscape | hbad
  · exact hbranchProfileFamilySelfTaxIdentity
      hbranchProfileFamilySelfTaxIdentityEscape
  rcases hbad with hcoherenceSourceEscape | hbad
  · exact hcoherenceSource hcoherenceSourceEscape
  rcases hbad with hcoherenceUniformEscape | hbad
  · exact hcoherenceUniformEscape hpositiveCoherenceUniform
  rcases hbad with hlowBeatGuardEscape | hbad
  · exact hlowBeatGuard hlowBeatGuardEscape
  rcases hbad with hlowBeatEnvelopeSourceEscape | hbad
  · exact hlowBeatEnvelopeSource hlowBeatEnvelopeSourceEscape
  rcases hbad with hlowBeatUnbounded | hcontinuationFailure
  · exact no_finite_low_beat_reserve_limit_of_unbounded_payoff
      R.lowBeatStream
      R.lowBeatReserveBounded
      hlowBeatUnbounded
  rcases hcontinuationFailure with hfixedPrefixSurvivor | hcontinuationFailure
  · exact hfixedPrefix hfixedPrefixSurvivor
  rcases hcontinuationFailure with hmovingAllOutputSurvivor | hcontinuationFailure
  · exact hmovingAllOutput hmovingAllOutputSurvivor
  rcases hcontinuationFailure with hcontinuumEscape | hcontinuationFailure
  · exact hcontinuum hcontinuumEscape
  rcases hcontinuationFailure with hcontinuumLSCEscape | hcontinuationFailure
  · exact hcontinuumLSCFailure hcontinuumLSCEscape
  rcases hcontinuationFailure with hcontinuumFixedAtomsGuardEscape |
      hcontinuationFailure
  · exact hcontinuumFixedAtomsGuard hcontinuumFixedAtomsGuardEscape
  rcases hcontinuationFailure with hallOutputPrefixChargeGuardEscape |
      hcontinuationFailure
  · exact hallOutputPrefixChargeGuard hallOutputPrefixChargeGuardEscape
  rcases hcontinuationFailure with hcouplingEscape | hcontinuationFailure
  · exact hcouplingMismatch hcouplingEscape
  rcases hcontinuationFailure with hcouplingGuardEscape | hcontinuationFailure
  · exact hcouplingGuard hcouplingGuardEscape
  rcases hcontinuationFailure with hcontinuumFixedAtomsEscape |
      hcontinuationFailure
  · exact hcontinuumFixedAtomsProvenance hcontinuumFixedAtomsEscape
  rcases hcontinuationFailure with hallOutputBackfitEscape |
      hcontinuationFailure
  · exact hallOutputBackfitGuard hallOutputBackfitEscape
  rcases hcontinuationFailure with heventSectionIncidenceMismatchEscape |
      hcontinuationFailure
  · exact heventSectionIncidenceMismatch
      heventSectionIncidenceMismatchEscape
  rcases hcontinuationFailure with heventAuxiliaryPanelsUnpaid |
      hcontinuationFailure
  · exact heventAuxiliaryPanelsUnpaid heventAuxiliaryPanelsPaid
  rcases hcontinuationFailure with heventAuxiliaryPanelFalsifierEscape |
      hcontinuationFailure
  · exact heventAuxiliaryPanelFalsifier
      heventAuxiliaryPanelFalsifierEscape
  rcases hcontinuationFailure with heventPDEHandoffEscape |
      hcontinuationFailure
  · exact heventPDEHandoffFalsifier heventPDEHandoffEscape
  rcases hcontinuationFailure with heventDuhamelLowerEnvelopeEscape |
      hcontinuationFailure
  · exact heventDuhamelLowerEnvelopeFalsifier
      heventDuhamelLowerEnvelopeEscape
  rcases hcontinuationFailure with hhighHighOutputLedgerProvenanceEscape |
      hcontinuationFailure
  · exact hhighHighOutputLedgerProvenance
      hhighHighOutputLedgerProvenanceEscape
  rcases hcontinuationFailure with hhighHighPDEGap | hcontinuationFailure
  · exact hhighHighPDEObligation hhighHighPDEGap
  rcases hcontinuationFailure with hhighHighPDEFalsifier |
      hcontinuationFailure
  · exact hhighHighPDEObligationFalsifier hhighHighPDEFalsifier
  rcases hcontinuationFailure with heventPDEFalsifier | hcontinuationFailure
  · exact heventPDEObligationFalsifier heventPDEFalsifier
  rcases hcontinuationFailure with heventPDEGap | hcontinuationFailure
  · exact heventPDEObligation heventPDEGap
  rcases hcontinuationFailure with heventEscape | hcontinuationFailure
  · exact heventRecurrence heventEscape
  rcases hcontinuationFailure with hlowHighPDEGap | hcontinuationFailure
  · exact hlowHighPDEObligation hlowHighPDEGap
  rcases hcontinuationFailure with hlowHighPDEFalsifier |
      hcontinuationFailure
  · exact hlowHighPDEObligationFalsifier hlowHighPDEFalsifier
  rcases hcontinuationFailure with hlowHighPDEHandoffEscape |
      hcontinuationFailure
  · exact hlowHighPDEHandoffFalsifier hlowHighPDEHandoffEscape
  rcases hcontinuationFailure with hlowHighEscape | hcontinuationFailure
  · exact hlowHighPrefix hlowHighEscape
  rcases hcontinuationFailure with hconcreteFourierSymbolEscape |
      hcontinuationFailure
  · exact hconcreteFourierSymbol hconcreteFourierSymbolEscape
  rcases hcontinuationFailure with hcoordinateSourceIdentityEscape |
      hcontinuationFailure
  · exact hcoordinateSourceIdentity hcoordinateSourceIdentityEscape
  rcases hcontinuationFailure with hcoordinateEscape | hcontinuationFailure
  · exact hcoordinate hcoordinateEscape
  rcases hcontinuationFailure with hflatTorusKillingModeProvenanceEscape |
      hcontinuationFailure
  · exact hflatTorusKillingModeProvenance
      hflatTorusKillingModeProvenanceEscape
  rcases hcontinuationFailure with hflatTorusPDEObligationEscape |
      hcontinuationFailure
  · exact hflatTorusPDEObligation hflatTorusPDEObligationEscape
  rcases hcontinuationFailure with hflatTorusSourceFailure | hcontinuationFailure
  · exact hflatTorusSourceFailure hflatTorusPhaseCapacitySources
  rcases hcontinuationFailure with hmacroscopicClockSourceEscape |
      hcontinuationFailure
  · exact hmacroscopicFlatTorusClockSource hmacroscopicClockSourceEscape
  rcases hcontinuationFailure with hflatTorusPhaseCapacityHandoffEscape |
      hcontinuationFailure
  · exact hflatTorusPhaseCapacityHandoff
      hflatTorusPhaseCapacityHandoffEscape
  rcases hcontinuationFailure with hphaseLatencyProfileReserveSourceEscape |
      hcontinuationFailure
  · exact hphaseLatencyProfileReserveSource
      hphaseLatencyProfileReserveSourceEscape
  rcases hcontinuationFailure with hphaseLatencyReserveSourceEscape |
      hcontinuationFailure
  · exact hphaseLatencyReserveSource hphaseLatencyReserveSourceEscape
  rcases hcontinuationFailure with hphaseCapacityFailure | hcontinuationFailure
  · exact hphaseCapacity hphaseCapacityFailure
  rcases hcontinuationFailure with hphaseAlignmentFailure |
      hcontinuationFailure
  · exact hphaseAlignment hphaseAlignmentFailure
  rcases hcontinuationFailure with hprofilePhaseLatencyFailure |
      hcontinuationFailure
  · exact hprofilePhaseLatency hprofilePhaseLatencyFailure
  rcases hcontinuationFailure with hphaseEscape | hcontinuationFailure
  · exact hphaseLatency hphaseEscape
  rcases hcontinuationFailure with hprofileLipschitzContinuationSourceEscape |
      hcontinuationFailure
  · exact hprofileLipschitzContinuationSource
      hprofileLipschitzContinuationSourceEscape
  rcases hcontinuationFailure with hprofileDecompositionSourceEscape |
      hcontinuationFailure
  · exact hprofileDecompositionSource hprofileDecompositionSourceEscape
  rcases hcontinuationFailure with hprofileDecompositionBundleEscape |
      hcontinuationFailure
  · exact hprofileDecompositionBundle hprofileDecompositionBundleEscape
  rcases hcontinuationFailure with hprofileLipschitzSourceCouplingEscape |
      hcontinuationFailure
  · exact hprofileLipschitzSourceCoupling
      hprofileLipschitzSourceCouplingEscape
  rcases hcontinuationFailure with hprofileLipschitzAmplitudeSourceEscape |
      hcontinuationFailure
  · exact hprofileLipschitzAmplitudeObservableSource
      hprofileLipschitzAmplitudeSourceEscape
  rcases hcontinuationFailure with hcontinuationIdentityEscape |
      hcontinuationFailure
  · exact hcontinuationIdentity hcontinuationIdentityEscape
  rcases hcontinuationFailure with hhandoffMismatch | hcontinuationFailure
  · exact hcontinuationHandoff hhandoffMismatch
  rcases hcontinuationFailure with hprofileCriticalFailure |
      hcontinuationFailure
  · exact hprofileCriticalFailure hprofileCritical
  rcases hcontinuationFailure with hprofileFailure | hcontinuationFailure
  · exact hprofileFailure hprofileRegular
  · exact hcontinuationFailure hcontinuation

/-- GP216 endpoint package: the composition receipt gives both the generated
profile/Lipschitz evolution's global regularity and exclusion of every
declared bridge-candidate escape.

This is the current Clay-facing endpoint of the formal spine.  The theorem is
conditional only on the fields of `GP216BridgeCompositionReceipt`; all
survivor, coherence, event-recurrence, low-high, flat-torus, self-tax, and
continuation branches are discharged by the receipt projections above. -/
theorem gp216_profile_regular_and_no_declared_bridge_candidate
    (R : GP216BridgeCompositionReceipt) :
    (R.profileLipschitzObligation.evolution_of_initial_data
      R.profileLipschitzInitialData).globalRegular ∧
      ¬ GP216GlobalBridgeCandidateWithinDeclaredScope R := by
  exact
    ⟨gp216_profile_lipschitz_global_regular R,
      no_gp216_global_bridge_candidate_of_composition_receipt R⟩

/-- Clay-shaped GP216 receipt family.

This is the exact remaining quantified endpoint: to turn the Track B/GP216
spine into a Clay regularity theorem, the PDE analysis must instantiate one
composition receipt for each smooth finite-energy initial datum, and the
receipt must be about that datum rather than a detached witness. -/
structure GP216ClayProblemReceipt where
  receipt_of_initial_data :
    SmoothNSInitialData → GP216BridgeCompositionReceipt
  receipt_initial_data_matches :
    ∀ u0 : SmoothNSInitialData,
      (receipt_of_initial_data u0).profileLipschitzInitialData = u0

/-- Conditional Clay theorem for the GP216 spine.

All proof-spine branches have been compressed into
`GP216BridgeCompositionReceipt`; this theorem exposes the only remaining
mathematical burden as constructing the receipt family above for actual
Navier-Stokes data. -/
theorem global_regular_of_gp216_clay_problem_receipt
    (P : GP216ClayProblemReceipt)
    (u0 : SmoothNSInitialData) :
    (((P.receipt_of_initial_data u0).profileLipschitzObligation)
      |>.evolution_of_initial_data u0).globalRegular := by
  let R := P.receipt_of_initial_data u0
  have hregular :
      (R.profileLipschitzObligation.evolution_of_initial_data
        R.profileLipschitzInitialData).globalRegular :=
    gp216_profile_lipschitz_global_regular R
  have hmatch : R.profileLipschitzInitialData = u0 := by
    simpa [R] using P.receipt_initial_data_matches u0
  simpa [R, hmatch] using hregular

end

end ZtareProofs.NS
