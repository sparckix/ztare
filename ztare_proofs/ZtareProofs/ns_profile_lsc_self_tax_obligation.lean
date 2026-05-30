import Mathlib.Tactic
import ZtareProofs.ns_all_output_positive_coherence_lsc
import ZtareProofs.ns_trackb_profile_decomposition_spine
import ZtareProofs.ns_profile_limit_lsc_bossfight
import ZtareProofs.ns_leray_gain_tax_trackb_obligation
import ZtareProofs.ns_littlewood_paley_profile_bridge
import ZtareProofs.ns_L3_multiscale_YM_rescaled_increments
import ZtareProofs.ns_no_invisible_critical_profile
import ZtareProofs.lean_dojo_ns.Navierstokes

/-!
# Profile LSC obligation for the Leray self-tax price

This file isolates the Track B limit-passage obligation after the GP-216
`core_04` local-to-global assembly step.

The theorem is deliberately abstract.  It says that a fixed LP/profile
decomposition cannot produce a new global Leray self-tax arbitrage at the
profile limit if:

* each finite prefix payoff is charged by self-tax, cross-defect, and coherence
  prices;
* each of those component prices is lower-semicontinuous into its declared
  limiting component;
* the limiting payoff is approximated by finite prefixes;
* the finite prefix self-tax price is backed by a local-to-global assembly
  receipt rather than by post-hoc scalar bookkeeping.

The companion falsifier structures name the exact component and prefix that
break lower-semicontinuity.
-/

namespace ZtareProofs.NS

noncomputable section

universe u

/-- Component labels for the Leray self-tax/profile limit ledger. -/
inductive LeraySelfTaxPriceComponent where
  | selfTax
  | crossDefect
  | coherence
deriving DecidableEq, Repr

/-- Interaction order in the raw finite-profile Mobius expansion.  The clean
raw component theorem uses this order, not a post-ledger positive-coherence
label. -/
inductive FiniteProfileInteractionOrder where
  | singleton
  | pair
  | triple
deriving DecidableEq, Repr

/-- A fixed LP/profile price stream for the Leray self-tax limit obligation.

The three prefix price fields are the declared finite-prefix prices for the
assembled self-tax, cross-profile/cross-shell defect, and coherence/inner-product
terms.  The three limit fields are declared before payoff scoring; the file
does not choose a PDE topology or a profile decomposition. -/
structure LeraySelfTaxProfilePriceStream where
  prefixPayoff : ℕ → Real
  prefixSelfTaxPrice : ℕ → Real
  prefixCrossDefectPrice : ℕ → Real
  prefixCoherencePrice : ℕ → Real
  payoffLimit : Real
  selfTaxLimitPrice : Real
  crossDefectLimitPrice : Real
  coherenceLimitPrice : Real
  profileTopologyDeclaredBeforePayoff : Prop
  profileStreamDeclaredBeforePayoff : Prop
  prefixComponentPricesDeclaredBeforePayoff : Prop
  limitComponentPricesDeclaredBeforePayoff : Prop
  noPosthocPayoffDependentStreamChoice : Prop

/-- A declared split of the continuum all-output target into the three
component limit prices used by the Leray self-tax/profile stream.

The continuum LP/Bony source already carries the prefix component prices, the
smooth payoff, the fixed topology, and the total global target.  The only
extra scalar datum needed to project it into `LeraySelfTaxProfilePriceStream`
is how that predeclared total target is allocated across self-tax,
cross-defect, and coherence limit prices. -/
structure LeraySelfTaxContinuumLimitComponentSplit
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) where
  selfTaxLimitPrice : Real
  crossDefectLimitPrice : Real
  coherenceLimitPrice : Real
  limit_component_prices_declared_before_payoff : Prop
  limit_component_prices_declared_before_payoff_paid :
    limit_component_prices_declared_before_payoff
  component_limit_sum_eq_global_target :
    selfTaxLimitPrice + crossDefectLimitPrice + coherenceLimitPrice =
      continuumGlobalSelfTaxTarget S

/-- Project an existing continuum all-output LP/Bony source into the Leray
self-tax/profile price-stream interface.

This is a source-construction adapter, not an LSC theorem: component LSC,
finite-prefix charging, and payoff convergence still have to be proved by the
ordinary receipts.  The adapter only prevents the scalar stream from being
hand-built after the continuum source is already fixed. -/
def leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (split :
      LeraySelfTaxContinuumLimitComponentSplit source.stream) :
    LeraySelfTaxProfilePriceStream where
  prefixPayoff := fun _ => source.stream.smoothCandidatePayoff
  prefixSelfTaxPrice := source.stream.prefixSelfTaxPrice
  prefixCrossDefectPrice := source.stream.prefixCrossProfilePrice
  prefixCoherencePrice := source.stream.prefixResidualPrice
  payoffLimit := source.stream.smoothCandidatePayoff
  selfTaxLimitPrice := split.selfTaxLimitPrice
  crossDefectLimitPrice := split.crossDefectLimitPrice
  coherenceLimitPrice := split.coherenceLimitPrice
  profileTopologyDeclaredBeforePayoff :=
    ContinuumLPUsesFixedTopology source.stream
  profileStreamDeclaredBeforePayoff :=
    source.stream_declared_before_payoff
  prefixComponentPricesDeclaredBeforePayoff :=
    source.fixed_atoms.constants_declared_before_payoff
  limitComponentPricesDeclaredBeforePayoff :=
    split.limit_component_prices_declared_before_payoff
  noPosthocPayoffDependentStreamChoice :=
    source.no_posthoc_stream_or_atom_substitution ∧
      source.fixed_atoms.no_hidden_source_l2_substitute

/-- The projected stream carries the fixed-topology and no-posthoc guards from
the continuum source, plus the declared limit-component split. -/
theorem leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource_guards
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (split :
      LeraySelfTaxContinuumLimitComponentSplit source.stream) :
    let S :=
      leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource source split
    S.profileTopologyDeclaredBeforePayoff ∧
      S.profileStreamDeclaredBeforePayoff ∧
        S.prefixComponentPricesDeclaredBeforePayoff ∧
          S.limitComponentPricesDeclaredBeforePayoff ∧
            S.noPosthocPayoffDependentStreamChoice := by
  exact
    ⟨source.fixed_topology,
      source.stream_declared_before_payoff_paid,
      source.fixed_atoms.constants_declared_before_payoff_paid,
      split.limit_component_prices_declared_before_payoff_paid,
      ⟨source.no_posthoc_stream_or_atom_substitution_paid,
        source.fixed_atoms.no_hidden_source_l2_substitute_paid⟩⟩

/-- Zero scalar stream used only to refute assumption-free macroscopic
triangulation shortcuts.  It is not a PDE object and supplies no LSC receipt. -/
def zeroLeraySelfTaxProfilePriceStream : LeraySelfTaxProfilePriceStream where
  prefixPayoff := fun _ => 0
  prefixSelfTaxPrice := fun _ => 0
  prefixCrossDefectPrice := fun _ => 0
  prefixCoherencePrice := fun _ => 0
  payoffLimit := 0
  selfTaxLimitPrice := 0
  crossDefectLimitPrice := 0
  coherenceLimitPrice := 0
  profileTopologyDeclaredBeforePayoff := True
  profileStreamDeclaredBeforePayoff := True
  prefixComponentPricesDeclaredBeforePayoff := True
  limitComponentPricesDeclaredBeforePayoff := True
  noPosthocPayoffDependentStreamChoice := True

/-- Total finite-prefix declared price. -/
def leraySelfTaxPrefixPrice
    (S : LeraySelfTaxProfilePriceStream) (n : ℕ) : Real :=
  S.prefixSelfTaxPrice n +
    S.prefixCrossDefectPrice n +
      S.prefixCoherencePrice n

/-- Total declared limiting price. -/
def leraySelfTaxLimitPrice
    (S : LeraySelfTaxProfilePriceStream) : Real :=
  S.selfTaxLimitPrice + S.crossDefectLimitPrice + S.coherenceLimitPrice

/-- The projected Leray self-tax stream uses the same aggregate finite-prefix
price as the continuum all-output LP/Bony stream. -/
theorem leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource_prefixPrice_eq
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (split :
      LeraySelfTaxContinuumLimitComponentSplit source.stream)
    (n : ℕ) :
    leraySelfTaxPrefixPrice
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          source split)
        n =
      continuumLPPrefixPrice source.stream n := by
  rfl

/-- The declared component split preserves the continuum all-output global
target as the aggregate Leray self-tax limit price. -/
theorem leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource_limitPrice_eq
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (split :
      LeraySelfTaxContinuumLimitComponentSplit source.stream) :
    leraySelfTaxLimitPrice
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          source split) =
      continuumGlobalSelfTaxTarget source.stream := by
  exact split.component_limit_sum_eq_global_target

/-- False theorem shape surfaced by graph-only macroscopic triangulation. -/
def MacroscopicTriangulationLimitCandidate : Prop :=
  ∀ S : LeraySelfTaxProfilePriceStream,
    sharpTarget ≤ leraySelfTaxLimitPrice S + S.payoffLimit

/-- The macroscopic triangulation shortcut is false without the real
component-LSC/continuum-coupling receipts.  The zero scalar stream already
violates it. -/
theorem not_macroscopic_triangulation_limit_candidate :
    ¬ MacroscopicTriangulationLimitCandidate := by
  intro h
  have hzero := h zeroLeraySelfTaxProfilePriceStream
  norm_num [MacroscopicTriangulationLimitCandidate,
    zeroLeraySelfTaxProfilePriceStream, leraySelfTaxLimitPrice, sharpTarget] at hzero

/-- Finite-prefix no-arbitrage for the assembled Leray self-tax ledger. -/
def LeraySelfTaxFinitePrefixNoArbitrage
    (S : LeraySelfTaxProfilePriceStream) : Prop :=
  ∀ n, S.prefixPayoff n ≤ leraySelfTaxPrefixPrice S n

/-- The limiting payoff is visible from finite prefixes. -/
def LeraySelfTaxPayoffApproximatedByPrefixes
    (S : LeraySelfTaxProfilePriceStream) : Prop :=
  ∀ ε : Real, 0 < ε → ∃ n, S.payoffLimit ≤ S.prefixPayoff n + ε

/-- Tail-visible payoff approximation.

The weaker `∃ n` prefix approximation can be satisfied by one early prefix.
The profile-limit topology needs eventual visibility: after any prefix cutoff,
some later prefix must still see the limiting payoff. -/
def LeraySelfTaxPayoffTailApproximatedByPrefixes
    (S : LeraySelfTaxProfilePriceStream) : Prop :=
  ∀ N : ℕ, ∀ ε : Real, 0 < ε →
    ∃ n : ℕ, N ≤ n ∧ S.payoffLimit ≤ S.prefixPayoff n + ε

/-- The continuum all-output projection pays tail payoff visibility directly.

The projected stream has constant prefix payoff equal to its payoff limit.
This is only the payoff-tail field; component LSC, finite-prefix charge, and
anti-posthoc source data remain separate obligations. -/
theorem leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource_tail_payoff
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (split :
      LeraySelfTaxContinuumLimitComponentSplit source.stream) :
    LeraySelfTaxPayoffTailApproximatedByPrefixes
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        source split) := by
  intro N ε hε
  refine ⟨N, le_rfl, ?_⟩
  simp [leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource]
  linarith

/-- The projected continuum all-output stream has convergent payoff prefixes.

The prefix payoff is constant by construction.  This pays only the ordinary
payoff-convergence input used by audited output-limit constructors; the
measure-valued defect source and finite-prefix charges remain separate source
obligations. -/
theorem leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource_prefixPayoff_tendsto
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (split :
      LeraySelfTaxContinuumLimitComponentSplit source.stream) :
    Filter.Tendsto
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        source split).prefixPayoff
      Filter.atTop
      (nhds
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          source split).payoffLimit) := by
  simp [leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource]

/-- Ordinary metric convergence of the payoff prefixes supplies the tail
visibility required by the Leray self-tax LSC receipt.

This is the small Mathlib-backed bridge behind the `payoff_tail_approximated`
field: the profile topology may prove `Tendsto`/Cauchy convergence, but the
Track B ledger consumes the order-form statement that every sufficiently late
tail still sees the limit payoff. -/
theorem payoff_tail_approximated_by_prefixes_of_tendsto_prefix_payoff
    (S : LeraySelfTaxProfilePriceStream)
    (h :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit)) :
    LeraySelfTaxPayoffTailApproximatedByPrefixes S := by
  intro N ε hε
  obtain ⟨N0, hN0⟩ := (Metric.tendsto_atTop.mp h) ε hε
  let n := max N N0
  refine ⟨n, ?_, ?_⟩
  · exact le_max_left N N0
  · have hdist :
        dist (S.prefixPayoff n) S.payoffLimit < ε :=
      hN0 n (le_max_right N N0)
    rw [Real.dist_eq] at hdist
    have hle_abs :
        S.payoffLimit - S.prefixPayoff n ≤
          |S.prefixPayoff n - S.payoffLimit| := by
      rw [abs_sub_comm]
      exact le_abs_self (S.payoffLimit - S.prefixPayoff n)
    nlinarith

/-- A Cauchy payoff-prefix sequence with one convergent unbounded subsequence
has the same tail-visible payoff approximation.

This is the diagonal compactness form of
`payoff_tail_approximated_by_prefixes_of_tendsto_prefix_payoff`: profile
arguments often first identify a subsequential limit, then use Cauchy control
to upgrade it to full-sequence convergence. -/
theorem payoff_tail_approximated_by_prefixes_of_cauchySeq_subseq_tendsto
    (S : LeraySelfTaxProfilePriceStream)
    (hcauchy : CauchySeq S.prefixPayoff)
    {φ : ℕ → ℕ}
    (hφ : StrictMono φ)
    (hsub :
      Filter.Tendsto
        (fun k : ℕ => S.prefixPayoff (φ k))
        Filter.atTop
        (nhds S.payoffLimit)) :
    LeraySelfTaxPayoffTailApproximatedByPrefixes S := by
  have hfull :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit) := by
    exact tendsto_nhds_of_cauchySeq_of_subseq
      hcauchy
      hφ.tendsto_atTop
      (by simpa [Function.comp_def] using hsub)
  exact payoff_tail_approximated_by_prefixes_of_tendsto_prefix_payoff S hfull

/-- Tail-visible payoff approximation implies the weaker prefix approximation
used by the generic profile-limit LSC adapter. -/
theorem payoff_approximated_by_prefix_of_tail_approx
    (S : LeraySelfTaxProfilePriceStream)
    (h : LeraySelfTaxPayoffTailApproximatedByPrefixes S) :
    LeraySelfTaxPayoffApproximatedByPrefixes S := by
  intro ε hε
  obtain ⟨n, _, hn⟩ := h 0 ε hε
  exact ⟨n, hn⟩

/-- Single early-spike stream used to separate weak prefix visibility from
tail visibility.  The limiting payoff is seen by prefix `0`, but no later
prefix sees it. -/
def weakButNotTailPayoffApproxStream :
    LeraySelfTaxProfilePriceStream where
  prefixPayoff := fun n => if n = 0 then 1 else 0
  prefixSelfTaxPrice := fun _ => 1
  prefixCrossDefectPrice := fun _ => 0
  prefixCoherencePrice := fun _ => 0
  payoffLimit := 1
  selfTaxLimitPrice := 1
  crossDefectLimitPrice := 0
  coherenceLimitPrice := 0
  profileTopologyDeclaredBeforePayoff := True
  profileStreamDeclaredBeforePayoff := True
  prefixComponentPricesDeclaredBeforePayoff := True
  limitComponentPricesDeclaredBeforePayoff := True
  noPosthocPayoffDependentStreamChoice := True

/-- Weak prefix payoff approximation is strictly weaker than tail-visible
payoff approximation.

This blocks the common limit-passage shortcut where a single early prefix is
used to certify a claimed profile-limit payoff. -/
theorem leray_self_tax_payoff_approx_not_tail_approx :
    ∃ S : LeraySelfTaxProfilePriceStream,
      LeraySelfTaxPayoffApproximatedByPrefixes S ∧
        ¬ LeraySelfTaxPayoffTailApproximatedByPrefixes S := by
  refine ⟨weakButNotTailPayoffApproxStream, ?_, ?_⟩
  · intro ε hε
    refine ⟨0, ?_⟩
    simp [weakButNotTailPayoffApproxStream]
    linarith
  · intro htail
    have heps : (0 : Real) < (1 / 2 : Real) := by norm_num
    obtain ⟨n, hn_tail, hn_pay⟩ := htail 1 (1 / 2) heps
    have hn_ne_zero : n ≠ 0 := by omega
    simp [weakButNotTailPayoffApproxStream, hn_ne_zero] at hn_pay
    norm_num at hn_pay

/-- Finite-prefix no-arbitrage plus one-prefix payoff visibility still does
not buy the countable/profile limit.

This is the local void exposed by the prefix topology: every finite prefix is
priced, and the limiting payoff is visible at one early prefix, but no tail
prefix sees the limiting payoff.  Any Clay-facing bridge has to pay the
tail-visibility field separately; it cannot recover it from finite-prefix
pricing alone. -/
theorem leray_self_tax_finite_prefix_no_arbitrage_and_payoff_approx_not_tail :
    ∃ S : LeraySelfTaxProfilePriceStream,
      LeraySelfTaxFinitePrefixNoArbitrage S ∧
        LeraySelfTaxPayoffApproximatedByPrefixes S ∧
          ¬ LeraySelfTaxPayoffTailApproximatedByPrefixes S := by
  refine ⟨weakButNotTailPayoffApproxStream, ?_, ?_, ?_⟩
  · intro n
    by_cases hn : n = 0
    · simp [weakButNotTailPayoffApproxStream, leraySelfTaxPrefixPrice, hn]
    · simp [weakButNotTailPayoffApproxStream, leraySelfTaxPrefixPrice, hn]
  · intro ε hε
    refine ⟨0, ?_⟩
    simp [weakButNotTailPayoffApproxStream]
    linarith
  · intro htail
    have heps : (0 : Real) < (1 / 2 : Real) := by norm_num
    obtain ⟨n, hn_tail, hn_pay⟩ := htail 1 (1 / 2) heps
    have hn_ne_zero : n ≠ 0 := by omega
    simp [weakButNotTailPayoffApproxStream, hn_ne_zero] at hn_pay
    norm_num at hn_pay

/-- Component-wise lower-semicontinuity into the declared limit prices. -/
structure LeraySelfTaxComponentLSC
    (S : LeraySelfTaxProfilePriceStream) where
  self_tax_lsc :
    ∀ n, S.prefixSelfTaxPrice n ≤ S.selfTaxLimitPrice
  cross_defect_lsc :
    ∀ n, S.prefixCrossDefectPrice n ≤ S.crossDefectLimitPrice
  coherence_lsc :
    ∀ n, S.prefixCoherencePrice n ≤ S.coherenceLimitPrice

/-- Monotone-convergence source for the compact component-LSC interface.

This is a standard topology route into the scalar LSC inequalities: monotone
finite-prefix component prices that tend to their declared limits are bounded
by those limits at every prefix.  It deliberately constructs only
`LeraySelfTaxComponentLSC`, not the PDE/topology receipt; defect inclusion and
fixed-output provenance still have to pass through the audited output receipt.
-/
structure LeraySelfTaxComponentMonotoneTendstoSource
    (S : LeraySelfTaxProfilePriceStream) where
  self_tax_prefix_monotone :
    Monotone S.prefixSelfTaxPrice
  cross_defect_prefix_monotone :
    Monotone S.prefixCrossDefectPrice
  coherence_prefix_monotone :
    Monotone S.prefixCoherencePrice
  self_tax_prefix_tendsto_limit :
    Filter.Tendsto S.prefixSelfTaxPrice Filter.atTop
      (nhds S.selfTaxLimitPrice)
  cross_defect_prefix_tendsto_limit :
    Filter.Tendsto S.prefixCrossDefectPrice Filter.atTop
      (nhds S.crossDefectLimitPrice)
  coherence_prefix_tendsto_limit :
    Filter.Tendsto S.prefixCoherencePrice Filter.atTop
      (nhds S.coherenceLimitPrice)

/-- Monotone convergence supplies the compact component-wise LSC fields. -/
def component_lsc_of_monotone_tendsto_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentMonotoneTendstoSource S) :
    LeraySelfTaxComponentLSC S where
  self_tax_lsc := fun n =>
    R.self_tax_prefix_monotone.ge_of_tendsto
      R.self_tax_prefix_tendsto_limit n
  cross_defect_lsc := fun n =>
    R.cross_defect_prefix_monotone.ge_of_tendsto
      R.cross_defect_prefix_tendsto_limit n
  coherence_lsc := fun n =>
    R.coherence_prefix_monotone.ge_of_tendsto
      R.coherence_prefix_tendsto_limit n

/-- Numeric defect ledger inside the relaxed Leray-output price.

This is deliberately not a boolean flag.  It names the Reynolds and
concentration-measure charges whose sum must be present in the relaxed output
price before the latter is compared to the declared limit price. -/
structure LeraySelfTaxRelaxedOutputDefectLedger
    (_S : LeraySelfTaxProfilePriceStream) where
  selfTaxReynoldsDefectPrice : Real
  selfTaxConcentrationMeasurePrice : Real
  crossReynoldsDefectPrice : Real
  crossConcentrationMeasurePrice : Real
  coherenceReynoldsDefectPrice : Real
  coherenceConcentrationMeasurePrice : Real
  self_tax_reynolds_nonnegative :
    0 ≤ selfTaxReynoldsDefectPrice
  self_tax_concentration_nonnegative :
    0 ≤ selfTaxConcentrationMeasurePrice
  cross_reynolds_nonnegative :
    0 ≤ crossReynoldsDefectPrice
  cross_concentration_nonnegative :
    0 ≤ crossConcentrationMeasurePrice
  coherence_reynolds_nonnegative :
    0 ≤ coherenceReynoldsDefectPrice
  coherence_concentration_nonnegative :
    0 ≤ coherenceConcentrationMeasurePrice

def selfTaxDefectFloor
    {S : LeraySelfTaxProfilePriceStream}
    (D : LeraySelfTaxRelaxedOutputDefectLedger S) : Real :=
  D.selfTaxReynoldsDefectPrice + D.selfTaxConcentrationMeasurePrice

def crossDefectFloor
    {S : LeraySelfTaxProfilePriceStream}
    (D : LeraySelfTaxRelaxedOutputDefectLedger S) : Real :=
  D.crossReynoldsDefectPrice + D.crossConcentrationMeasurePrice

def coherenceDefectFloor
    {S : LeraySelfTaxProfilePriceStream}
    (D : LeraySelfTaxRelaxedOutputDefectLedger S) : Real :=
  D.coherenceReynoldsDefectPrice + D.coherenceConcentrationMeasurePrice

/-- First-class measure-valued/Young-defect source for the relaxed
Leray-output limit.

This is the theory-builder object behind the relaxed output ledger.  A weak
`L2` limit of velocities can erase oscillatory cross terms; a measure-valued
defect source records the Reynolds/concentration objects whose prices survive
as part of the relaxed limit.  The scalar defect ledger below is derived from
this source, not chosen independently after payoff scoring. -/
structure LeraySelfTaxMeasureValuedDefectSource
    (S : LeraySelfTaxProfilePriceStream) where
  defectState : Type
  reynoldsDefect : defectState
  concentrationDefect : defectState
  defectPrice :
    defectState → LeraySelfTaxPriceComponent → Real
  defect_carrier_declared_before_payoff :
    S.profileTopologyDeclaredBeforePayoff
  reynolds_defect_reified_in_relaxed_limit_price : Prop
  reynolds_defect_reified_receipt :
    reynolds_defect_reified_in_relaxed_limit_price
  concentration_measure_reified_in_relaxed_limit_price : Prop
  concentration_measure_reified_receipt :
    concentration_measure_reified_in_relaxed_limit_price
  defect_price_nonnegative :
    ∀ d component, 0 ≤ defectPrice d component

/-- The numeric relaxed-output defect ledger induced by a first-class
measure-valued defect source. -/
def relaxed_output_defect_ledger_of_measure_valued_source
    {S : LeraySelfTaxProfilePriceStream}
    (Y : LeraySelfTaxMeasureValuedDefectSource S) :
    LeraySelfTaxRelaxedOutputDefectLedger S where
  selfTaxReynoldsDefectPrice :=
    Y.defectPrice Y.reynoldsDefect LeraySelfTaxPriceComponent.selfTax
  selfTaxConcentrationMeasurePrice :=
    Y.defectPrice Y.concentrationDefect LeraySelfTaxPriceComponent.selfTax
  crossReynoldsDefectPrice :=
    Y.defectPrice Y.reynoldsDefect LeraySelfTaxPriceComponent.crossDefect
  crossConcentrationMeasurePrice :=
    Y.defectPrice Y.concentrationDefect LeraySelfTaxPriceComponent.crossDefect
  coherenceReynoldsDefectPrice :=
    Y.defectPrice Y.reynoldsDefect LeraySelfTaxPriceComponent.coherence
  coherenceConcentrationMeasurePrice :=
    Y.defectPrice Y.concentrationDefect LeraySelfTaxPriceComponent.coherence
  self_tax_reynolds_nonnegative :=
    Y.defect_price_nonnegative
      Y.reynoldsDefect LeraySelfTaxPriceComponent.selfTax
  self_tax_concentration_nonnegative :=
    Y.defect_price_nonnegative
      Y.concentrationDefect LeraySelfTaxPriceComponent.selfTax
  cross_reynolds_nonnegative :=
    Y.defect_price_nonnegative
      Y.reynoldsDefect LeraySelfTaxPriceComponent.crossDefect
  cross_concentration_nonnegative :=
    Y.defect_price_nonnegative
      Y.concentrationDefect LeraySelfTaxPriceComponent.crossDefect
  coherence_reynolds_nonnegative :=
    Y.defect_price_nonnegative
      Y.reynoldsDefect LeraySelfTaxPriceComponent.coherence
  coherence_concentration_nonnegative :=
    Y.defect_price_nonnegative
      Y.concentrationDefect LeraySelfTaxPriceComponent.coherence

/-- The self-tax defect floor induced by a measure-valued source is
nonnegative. -/
theorem selfTaxDefectFloor_nonnegative_of_measure_valued_source
    {S : LeraySelfTaxProfilePriceStream}
    (Y : LeraySelfTaxMeasureValuedDefectSource S) :
    0 ≤
      selfTaxDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source Y) := by
  unfold selfTaxDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
  exact add_nonneg
    (Y.defect_price_nonnegative
      Y.reynoldsDefect LeraySelfTaxPriceComponent.selfTax)
    (Y.defect_price_nonnegative
      Y.concentrationDefect LeraySelfTaxPriceComponent.selfTax)

/-- The cross-defect floor induced by a measure-valued source is
nonnegative. -/
theorem crossDefectFloor_nonnegative_of_measure_valued_source
    {S : LeraySelfTaxProfilePriceStream}
    (Y : LeraySelfTaxMeasureValuedDefectSource S) :
    0 ≤
      crossDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source Y) := by
  unfold crossDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
  exact add_nonneg
    (Y.defect_price_nonnegative
      Y.reynoldsDefect LeraySelfTaxPriceComponent.crossDefect)
    (Y.defect_price_nonnegative
      Y.concentrationDefect LeraySelfTaxPriceComponent.crossDefect)

/-- The coherence defect floor induced by a measure-valued source is
nonnegative. -/
theorem coherenceDefectFloor_nonnegative_of_measure_valued_source
    {S : LeraySelfTaxProfilePriceStream}
    (Y : LeraySelfTaxMeasureValuedDefectSource S) :
    0 ≤
      coherenceDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source Y) := by
  unfold coherenceDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
  exact add_nonneg
    (Y.defect_price_nonnegative
      Y.reynoldsDefect LeraySelfTaxPriceComponent.coherence)
    (Y.defect_price_nonnegative
      Y.concentrationDefect LeraySelfTaxPriceComponent.coherence)

/-- PDE-output source receipt for component lower-semicontinuity.

The weak profile topology is not enough by itself.  The load-bearing PDE fact
is convergence of the Leray-projected nonlinear output in the `L2_{t,x}` output
space, or a stronger graph topology implying it, with Reynolds/concentration
defects included in the declared relaxed limit price.  The scalar fields below
separate that relaxed output price from the final declared ledger price so a
smooth-limit-only substitution cannot masquerade as LSC. -/
structure LeraySelfTaxOutputLimitPriceReceipt
    (S : LeraySelfTaxProfilePriceStream) where
  fixed_leray_output_l2_topology :
    S.profileTopologyDeclaredBeforePayoff
  component_stream_fixed_before_payoff :
    S.profileStreamDeclaredBeforePayoff
  prefix_components_declared_before_payoff :
    S.prefixComponentPricesDeclaredBeforePayoff
  limit_components_declared_before_payoff :
    S.limitComponentPricesDeclaredBeforePayoff
  no_smooth_limit_price_substitution :
    S.noPosthocPayoffDependentStreamChoice
  leray_projection_l2_bounded : Prop
  leray_projection_l2_bounded_receipt :
    leray_projection_l2_bounded
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology : Prop
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology_receipt :
    nonlinear_output_converges_weakly_l2_or_strong_graph_topology
  strong_l4_w14_or_hs_source_topology_declared : Prop
  strong_l4_w14_or_hs_source_topology_declared_receipt :
    strong_l4_w14_or_hs_source_topology_declared
  reynolds_defect_included_in_relaxed_limit_price : Prop
  reynolds_defect_included_in_relaxed_limit_price_receipt :
    reynolds_defect_included_in_relaxed_limit_price
  concentration_measure_included_in_relaxed_limit_price : Prop
  concentration_measure_included_in_relaxed_limit_price_receipt :
    concentration_measure_included_in_relaxed_limit_price
  cross_and_coherence_outputs_use_same_topology : Prop
  cross_and_coherence_outputs_use_same_topology_receipt :
    cross_and_coherence_outputs_use_same_topology
  relaxed_output_defect_ledger :
    LeraySelfTaxRelaxedOutputDefectLedger S
  selfTaxRelaxedOutputPrice : Real
  crossDefectRelaxedOutputPrice : Real
  coherenceRelaxedOutputPrice : Real
  self_tax_relaxed_output_includes_numeric_defects :
    selfTaxDefectFloor relaxed_output_defect_ledger ≤
      selfTaxRelaxedOutputPrice
  cross_defect_relaxed_output_includes_numeric_defects :
    crossDefectFloor relaxed_output_defect_ledger ≤
      crossDefectRelaxedOutputPrice
  coherence_relaxed_output_includes_numeric_defects :
    coherenceDefectFloor relaxed_output_defect_ledger ≤
      coherenceRelaxedOutputPrice
  prefix_self_tax_le_relaxed_output :
    ∀ n, S.prefixSelfTaxPrice n ≤ selfTaxRelaxedOutputPrice
  prefix_cross_defect_le_relaxed_output :
    ∀ n, S.prefixCrossDefectPrice n ≤ crossDefectRelaxedOutputPrice
  prefix_coherence_le_relaxed_output :
    ∀ n, S.prefixCoherencePrice n ≤ coherenceRelaxedOutputPrice
  self_tax_relaxed_output_le_limit :
    selfTaxRelaxedOutputPrice ≤ S.selfTaxLimitPrice
  cross_defect_relaxed_output_le_limit :
    crossDefectRelaxedOutputPrice ≤ S.crossDefectLimitPrice
  coherence_relaxed_output_le_limit :
    coherenceRelaxedOutputPrice ≤ S.coherenceLimitPrice

/-- PDE-facing output-limit source built around a first-class
measure-valued/Young-defect object.

This is not a proof of the PDE compactness theorem.  It is the closure-facing
shape of that theorem: the defect carrier, Reynolds defect, concentration
measure, scalar relaxed prices, same-output topology, and limit-price
domination must all be supplied together before a Leray output-limit receipt
can be built. -/
structure LeraySelfTaxMeasureValuedOutputLimitSource
    (S : LeraySelfTaxProfilePriceStream) where
  measure_defect_source :
    LeraySelfTaxMeasureValuedDefectSource S
  component_stream_fixed_before_payoff :
    S.profileStreamDeclaredBeforePayoff
  prefix_components_declared_before_payoff :
    S.prefixComponentPricesDeclaredBeforePayoff
  limit_components_declared_before_payoff :
    S.limitComponentPricesDeclaredBeforePayoff
  no_smooth_limit_price_substitution :
    S.noPosthocPayoffDependentStreamChoice
  leray_projection_l2_bounded : Prop
  leray_projection_l2_bounded_receipt :
    leray_projection_l2_bounded
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology : Prop
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology_receipt :
    nonlinear_output_converges_weakly_l2_or_strong_graph_topology
  strong_l4_w14_or_hs_source_topology_declared : Prop
  strong_l4_w14_or_hs_source_topology_declared_receipt :
    strong_l4_w14_or_hs_source_topology_declared
  cross_and_coherence_outputs_use_same_topology : Prop
  cross_and_coherence_outputs_use_same_topology_receipt :
    cross_and_coherence_outputs_use_same_topology
  selfTaxRelaxedOutputPrice : Real
  crossDefectRelaxedOutputPrice : Real
  coherenceRelaxedOutputPrice : Real
  self_tax_relaxed_output_includes_measure_defects :
    selfTaxDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          measure_defect_source) ≤
      selfTaxRelaxedOutputPrice
  cross_defect_relaxed_output_includes_measure_defects :
    crossDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          measure_defect_source) ≤
      crossDefectRelaxedOutputPrice
  coherence_relaxed_output_includes_measure_defects :
    coherenceDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          measure_defect_source) ≤
      coherenceRelaxedOutputPrice
  prefix_self_tax_le_relaxed_output :
    ∀ n, S.prefixSelfTaxPrice n ≤ selfTaxRelaxedOutputPrice
  prefix_cross_defect_le_relaxed_output :
    ∀ n, S.prefixCrossDefectPrice n ≤ crossDefectRelaxedOutputPrice
  prefix_coherence_le_relaxed_output :
    ∀ n, S.prefixCoherencePrice n ≤ coherenceRelaxedOutputPrice
  self_tax_relaxed_output_le_limit :
    selfTaxRelaxedOutputPrice ≤ S.selfTaxLimitPrice
  cross_defect_relaxed_output_le_limit :
    crossDefectRelaxedOutputPrice ≤ S.crossDefectLimitPrice
  coherence_relaxed_output_le_limit :
    coherenceRelaxedOutputPrice ≤ S.coherenceLimitPrice

/-- Provenance certificate for a measure-valued output-limit source.

This is deliberately separate from `LeraySelfTaxMeasureValuedOutputLimitSource`.
The bare source structure records the scalar fields consumed by the LSC
adapter.  This provenance object records the external compactness construction
that is supposed to produce those fields from the selected approximation
sequence.  A route that merely sets zero defects and reuses component LSC does
not receive this certificate. -/
structure LeraySelfTaxMeasureValuedOutputCompactnessProvenance
    (S : LeraySelfTaxProfilePriceStream)
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) where
  approximation_family : Type u
  approximation_index_to_prefix :
    approximation_family → ℕ
  approximation_family_declared_before_payoff : Prop
  approximation_family_declared_before_payoff_receipt :
    approximation_family_declared_before_payoff
  approximation_family_cofinal_in_prefixes : Prop
  approximation_family_cofinal_in_prefixes_receipt :
    approximation_family_cofinal_in_prefixes
  defect_carrier_generated_from_approximation_family : Prop
  defect_carrier_generated_from_approximation_family_receipt :
    defect_carrier_generated_from_approximation_family
  lions_tightness_excludes_vanishing_or_dichotomy_escape : Prop
  lions_tightness_excludes_vanishing_or_dichotomy_escape_receipt :
    lions_tightness_excludes_vanishing_or_dichotomy_escape
  reynolds_defect_is_weak_limit_of_output_residuals : Prop
  reynolds_defect_is_weak_limit_of_output_residuals_receipt :
    reynolds_defect_is_weak_limit_of_output_residuals
  concentration_measure_is_tight_limit_of_output_defects : Prop
  concentration_measure_is_tight_limit_of_output_defects_receipt :
    concentration_measure_is_tight_limit_of_output_defects
  diperna_majda_oscillation_concentration_pair_accounted : Prop
  diperna_majda_oscillation_concentration_pair_accounted_receipt :
    diperna_majda_oscillation_concentration_pair_accounted
  tartar_microlocal_defect_direction_accounted : Prop
  tartar_microlocal_defect_direction_accounted_receipt :
    tartar_microlocal_defect_direction_accounted
  multiscale_or_correlation_defect_accounted : Prop
  multiscale_or_correlation_defect_accounted_receipt :
    multiscale_or_correlation_defect_accounted
  duchon_robert_local_energy_defect_accounted : Prop
  duchon_robert_local_energy_defect_accounted_receipt :
    duchon_robert_local_energy_defect_accounted
  relaxed_output_prices_are_liminf_bounds : Prop
  relaxed_output_prices_are_liminf_bounds_receipt :
    relaxed_output_prices_are_liminf_bounds
  not_zero_defect_component_lsc_repackaging : Prop
  not_zero_defect_component_lsc_repackaging_receipt :
    not_zero_defect_component_lsc_repackaging

/-- Measure-valued output source together with its compactness provenance.

This is the source object the closure graph should count.  The projection to
the older bare source is mechanical, but the reverse direction is intentionally
not provided: component LSC and zero defects are insufficient without the
compactness provenance fields. -/
structure LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource
    (S : LeraySelfTaxProfilePriceStream) where
  measure_valued_output_limit :
    LeraySelfTaxMeasureValuedOutputLimitSource S
  compactness_provenance :
    LeraySelfTaxMeasureValuedOutputCompactnessProvenance
      S measure_valued_output_limit

/-- Forget compactness provenance after the source credit has been paid. -/
def LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource.toMeasureValued
    {S : LeraySelfTaxProfilePriceStream}
    (C : LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource S) :
    LeraySelfTaxMeasureValuedOutputLimitSource S :=
  C.measure_valued_output_limit

/-- Toy one-point Young summary used as a negative control.

The point is deliberately modest: one-point moment data does not determine a
cross/coherence term.  The NS bridge therefore requires an explicit
multiscale/correlation provenance field whenever cross/coherence output prices
use more than local one-point moments. -/
structure ToyOnePointYoungSummary where
  meanX : Real
  meanY : Real
  secondX : Real
  secondY : Real

structure ToyCorrelationSummary extends ToyOnePointYoungSummary where
  crossXY : Real

def toyCorrelatedOnePointAmbiguity : ToyCorrelationSummary where
  meanX := 0
  meanY := 0
  secondX := 1
  secondY := 1
  crossXY := 1

def toyAnticorrelatedOnePointAmbiguity : ToyCorrelationSummary where
  meanX := 0
  meanY := 0
  secondX := 1
  secondY := 1
  crossXY := -1

/-- Same one-point data can carry different cross/coherence data. -/
theorem toy_one_point_young_summary_not_cross_correlation_complete :
    toyCorrelatedOnePointAmbiguity.toToyOnePointYoungSummary =
        toyAnticorrelatedOnePointAmbiguity.toToyOnePointYoungSummary ∧
      toyCorrelatedOnePointAmbiguity.crossXY ≠
        toyAnticorrelatedOnePointAmbiguity.crossXY := by
  constructor
  · rfl
  · norm_num [toyCorrelatedOnePointAmbiguity,
      toyAnticorrelatedOnePointAmbiguity]

/-- A measure-valued/Young-defect output source instantiates the existing
defect-inclusive Leray output-limit receipt. -/
def output_limit_price_receipt_of_measure_valued_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxMeasureValuedOutputLimitSource S) :
    LeraySelfTaxOutputLimitPriceReceipt S where
  fixed_leray_output_l2_topology :=
    R.measure_defect_source.defect_carrier_declared_before_payoff
  component_stream_fixed_before_payoff :=
    R.component_stream_fixed_before_payoff
  prefix_components_declared_before_payoff :=
    R.prefix_components_declared_before_payoff
  limit_components_declared_before_payoff :=
    R.limit_components_declared_before_payoff
  no_smooth_limit_price_substitution :=
    R.no_smooth_limit_price_substitution
  leray_projection_l2_bounded :=
    R.leray_projection_l2_bounded
  leray_projection_l2_bounded_receipt :=
    R.leray_projection_l2_bounded_receipt
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology :=
    R.nonlinear_output_converges_weakly_l2_or_strong_graph_topology
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology_receipt :=
    R.nonlinear_output_converges_weakly_l2_or_strong_graph_topology_receipt
  strong_l4_w14_or_hs_source_topology_declared :=
    R.strong_l4_w14_or_hs_source_topology_declared
  strong_l4_w14_or_hs_source_topology_declared_receipt :=
    R.strong_l4_w14_or_hs_source_topology_declared_receipt
  reynolds_defect_included_in_relaxed_limit_price :=
    R.measure_defect_source.reynolds_defect_reified_in_relaxed_limit_price
  reynolds_defect_included_in_relaxed_limit_price_receipt :=
    R.measure_defect_source.reynolds_defect_reified_receipt
  concentration_measure_included_in_relaxed_limit_price :=
    R.measure_defect_source.concentration_measure_reified_in_relaxed_limit_price
  concentration_measure_included_in_relaxed_limit_price_receipt :=
    R.measure_defect_source.concentration_measure_reified_receipt
  cross_and_coherence_outputs_use_same_topology :=
    R.cross_and_coherence_outputs_use_same_topology
  cross_and_coherence_outputs_use_same_topology_receipt :=
    R.cross_and_coherence_outputs_use_same_topology_receipt
  relaxed_output_defect_ledger :=
    relaxed_output_defect_ledger_of_measure_valued_source
      R.measure_defect_source
  selfTaxRelaxedOutputPrice :=
    R.selfTaxRelaxedOutputPrice
  crossDefectRelaxedOutputPrice :=
    R.crossDefectRelaxedOutputPrice
  coherenceRelaxedOutputPrice :=
    R.coherenceRelaxedOutputPrice
  self_tax_relaxed_output_includes_numeric_defects :=
    R.self_tax_relaxed_output_includes_measure_defects
  cross_defect_relaxed_output_includes_numeric_defects :=
    R.cross_defect_relaxed_output_includes_measure_defects
  coherence_relaxed_output_includes_numeric_defects :=
    R.coherence_relaxed_output_includes_measure_defects
  prefix_self_tax_le_relaxed_output :=
    R.prefix_self_tax_le_relaxed_output
  prefix_cross_defect_le_relaxed_output :=
    R.prefix_cross_defect_le_relaxed_output
  prefix_coherence_le_relaxed_output :=
    R.prefix_coherence_le_relaxed_output
  self_tax_relaxed_output_le_limit :=
    R.self_tax_relaxed_output_le_limit
  cross_defect_relaxed_output_le_limit :=
    R.cross_defect_relaxed_output_le_limit
  coherence_relaxed_output_le_limit :=
    R.coherence_relaxed_output_le_limit

/-- Defect-inclusive output convergence supplies the compact component-LSC
interface. -/
def component_lsc_of_output_limit_price_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPriceReceipt S) :
    LeraySelfTaxComponentLSC S where
  self_tax_lsc := fun n =>
    (R.prefix_self_tax_le_relaxed_output n).trans
      R.self_tax_relaxed_output_le_limit
  cross_defect_lsc := fun n =>
    (R.prefix_cross_defect_le_relaxed_output n).trans
      R.cross_defect_relaxed_output_le_limit
  coherence_lsc := fun n =>
    (R.prefix_coherence_le_relaxed_output n).trans
      R.coherence_relaxed_output_le_limit

/-- Hostile falsifier: the relaxed output price, including Reynolds or
concentration defect, is not actually included in the declared limit price. -/
inductive LeraySelfTaxUnchargedOutputDefectFalsifier
    {S : LeraySelfTaxProfilePriceStream}
    (R : LeraySelfTaxOutputLimitPriceReceipt S) : Prop where
  | selfTax :
      S.selfTaxLimitPrice < R.selfTaxRelaxedOutputPrice →
        LeraySelfTaxUnchargedOutputDefectFalsifier R
  | crossDefect :
      S.crossDefectLimitPrice < R.crossDefectRelaxedOutputPrice →
        LeraySelfTaxUnchargedOutputDefectFalsifier R
  | coherence :
      S.coherenceLimitPrice < R.coherenceRelaxedOutputPrice →
        LeraySelfTaxUnchargedOutputDefectFalsifier R

/-- Hostile falsifier: the relaxed output price claims defect inclusion but
is numerically below one of the declared defect floors. -/
inductive LeraySelfTaxRelaxedOutputDefectFloorFalsifier
    {S : LeraySelfTaxProfilePriceStream}
    (R : LeraySelfTaxOutputLimitPriceReceipt S) : Prop where
  | selfTax :
      R.selfTaxRelaxedOutputPrice <
        selfTaxDefectFloor R.relaxed_output_defect_ledger →
        LeraySelfTaxRelaxedOutputDefectFloorFalsifier R
  | crossDefect :
      R.crossDefectRelaxedOutputPrice <
        crossDefectFloor R.relaxed_output_defect_ledger →
        LeraySelfTaxRelaxedOutputDefectFloorFalsifier R
  | coherence :
      R.coherenceRelaxedOutputPrice <
        coherenceDefectFloor R.relaxed_output_defect_ledger →
        LeraySelfTaxRelaxedOutputDefectFloorFalsifier R

/-- Hostile falsifier: the output-limit price receipt is missing one of the
declared PDE/topology guards needed to treat its scalar component inequalities
as Leray-output LSC rather than posthoc bookkeeping. -/
inductive LeraySelfTaxOutputLimitPricePDEGuardFalsifier
    {S : LeraySelfTaxProfilePriceStream}
    (R : LeraySelfTaxOutputLimitPriceReceipt S) : Prop where
  | missingLerayProjection :
      ¬ R.leray_projection_l2_bounded →
        LeraySelfTaxOutputLimitPricePDEGuardFalsifier R
  | missingNonlinearOutputConvergence :
      ¬ R.nonlinear_output_converges_weakly_l2_or_strong_graph_topology →
        LeraySelfTaxOutputLimitPricePDEGuardFalsifier R
  | missingSourceTopology :
      ¬ R.strong_l4_w14_or_hs_source_topology_declared →
        LeraySelfTaxOutputLimitPricePDEGuardFalsifier R
  | missingReynoldsDefectInclusion :
      ¬ R.reynolds_defect_included_in_relaxed_limit_price →
        LeraySelfTaxOutputLimitPricePDEGuardFalsifier R
  | missingConcentrationMeasureInclusion :
      ¬ R.concentration_measure_included_in_relaxed_limit_price →
        LeraySelfTaxOutputLimitPricePDEGuardFalsifier R
  | mixedOutputTopology :
      ¬ R.cross_and_coherence_outputs_use_same_topology →
        LeraySelfTaxOutputLimitPricePDEGuardFalsifier R

/-- A defect-inclusive output-limit receipt rules out the corresponding
uncharged-defect falsifier. -/
theorem no_uncharged_output_defect_of_output_limit_price_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPriceReceipt S)
    (F : LeraySelfTaxUnchargedOutputDefectFalsifier R) :
    False := by
  cases F with
  | selfTax hbad =>
      exact not_lt_of_ge R.self_tax_relaxed_output_le_limit hbad
  | crossDefect hbad =>
      exact not_lt_of_ge R.cross_defect_relaxed_output_le_limit hbad
  | coherence hbad =>
      exact not_lt_of_ge R.coherence_relaxed_output_le_limit hbad

/-- A relaxed output-limit receipt rules out omission of the numeric defect
floors from the relaxed prices themselves. -/
theorem no_relaxed_output_defect_floor_falsifier_of_output_limit_price_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPriceReceipt S)
    (F : LeraySelfTaxRelaxedOutputDefectFloorFalsifier R) :
    False := by
  cases F with
  | selfTax hbad =>
      exact not_lt_of_ge
        R.self_tax_relaxed_output_includes_numeric_defects hbad
  | crossDefect hbad =>
      exact not_lt_of_ge
        R.cross_defect_relaxed_output_includes_numeric_defects hbad
  | coherence hbad =>
      exact not_lt_of_ge
        R.coherence_relaxed_output_includes_numeric_defects hbad

/-- A defect-inclusive output-limit price receipt rules out missing
PDE/topology guard branches. -/
theorem no_output_limit_price_pde_guard_falsifier
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPriceReceipt S)
    (F : LeraySelfTaxOutputLimitPricePDEGuardFalsifier R) :
    False := by
  cases F with
  | missingLerayProjection h =>
      exact h R.leray_projection_l2_bounded_receipt
  | missingNonlinearOutputConvergence h =>
      exact h
        R.nonlinear_output_converges_weakly_l2_or_strong_graph_topology_receipt
  | missingSourceTopology h =>
      exact h R.strong_l4_w14_or_hs_source_topology_declared_receipt
  | missingReynoldsDefectInclusion h =>
      exact h R.reynolds_defect_included_in_relaxed_limit_price_receipt
  | missingConcentrationMeasureInclusion h =>
      exact h
        R.concentration_measure_included_in_relaxed_limit_price_receipt
  | mixedOutputTopology h =>
      exact h R.cross_and_coherence_outputs_use_same_topology_receipt

/-- A measure-valued output source rules out uncharged relaxed-output defects
through the induced output-limit receipt. -/
theorem no_uncharged_output_defect_of_measure_valued_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (F : LeraySelfTaxUnchargedOutputDefectFalsifier
      (output_limit_price_receipt_of_measure_valued_source S R)) :
    False :=
  no_uncharged_output_defect_of_output_limit_price_receipt
    S
    (output_limit_price_receipt_of_measure_valued_source S R)
    F

/-- A measure-valued output source rules out omitting the numeric defect floors
induced by its Reynolds/concentration defect objects. -/
theorem no_relaxed_output_defect_floor_falsifier_of_measure_valued_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (F : LeraySelfTaxRelaxedOutputDefectFloorFalsifier
      (output_limit_price_receipt_of_measure_valued_source S R)) :
    False :=
  no_relaxed_output_defect_floor_falsifier_of_output_limit_price_receipt
    S
    (output_limit_price_receipt_of_measure_valued_source S R)
    F

/-- A measure-valued output source carries the same PDE/topology guard
exclusions as the induced output-limit receipt. -/
theorem no_output_limit_price_pde_guard_falsifier_of_measure_valued_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (F : LeraySelfTaxOutputLimitPricePDEGuardFalsifier
      (output_limit_price_receipt_of_measure_valued_source S R)) :
    False :=
  no_output_limit_price_pde_guard_falsifier
    S
    (output_limit_price_receipt_of_measure_valued_source S R)
    F

/-- PDE/topology receipt for component-wise lower-semicontinuity.

This is intentionally stronger than the compact inequality structure: it
records that the three component envelopes are proved in one fixed topology
and cannot be swapped after payoff scoring. -/
structure LeraySelfTaxComponentLSCPDEReceipt
    (S : LeraySelfTaxProfilePriceStream) where
  fixed_lp_bony_profile_topology :
    S.profileTopologyDeclaredBeforePayoff
  component_stream_fixed_before_payoff :
    S.profileStreamDeclaredBeforePayoff
  prefix_components_declared_before_payoff :
    S.prefixComponentPricesDeclaredBeforePayoff
  limit_components_declared_before_payoff :
    S.limitComponentPricesDeclaredBeforePayoff
  no_hidden_source_l2_component_substitute :
    S.noPosthocPayoffDependentStreamChoice
  self_tax_component_lsc :
    ∀ n, S.prefixSelfTaxPrice n ≤ S.selfTaxLimitPrice
  cross_defect_component_lsc :
    ∀ n, S.prefixCrossDefectPrice n ≤ S.crossDefectLimitPrice
  coherence_component_lsc :
    ∀ n, S.prefixCoherencePrice n ≤ S.coherenceLimitPrice

/-- Defect-inclusive output-limit receipt instantiates the PDE/topology
component-LSC receipt. -/
def component_lsc_pde_receipt_of_output_limit_price_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPriceReceipt S) :
    LeraySelfTaxComponentLSCPDEReceipt S where
  fixed_lp_bony_profile_topology :=
    R.fixed_leray_output_l2_topology
  component_stream_fixed_before_payoff :=
    R.component_stream_fixed_before_payoff
  prefix_components_declared_before_payoff :=
    R.prefix_components_declared_before_payoff
  limit_components_declared_before_payoff :=
    R.limit_components_declared_before_payoff
  no_hidden_source_l2_component_substitute :=
    R.no_smooth_limit_price_substitution
  self_tax_component_lsc :=
    (component_lsc_of_output_limit_price_receipt S R).self_tax_lsc
  cross_defect_component_lsc :=
    (component_lsc_of_output_limit_price_receipt S R).cross_defect_lsc
  coherence_component_lsc :=
    (component_lsc_of_output_limit_price_receipt S R).coherence_lsc

/-- Measure-valued/Young-defect output source instantiates the PDE/topology
component-LSC receipt directly. -/
def component_lsc_pde_receipt_of_measure_valued_output_limit_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxMeasureValuedOutputLimitSource S) :
    LeraySelfTaxComponentLSCPDEReceipt S :=
  component_lsc_pde_receipt_of_output_limit_price_receipt S
    (output_limit_price_receipt_of_measure_valued_source S R)

/-- PDE/topology component receipt instantiates the compact component-LSC
interface. -/
def component_lsc_of_pde_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLSCPDEReceipt S) :
    LeraySelfTaxComponentLSC S where
  self_tax_lsc := R.self_tax_component_lsc
  cross_defect_lsc := R.cross_defect_component_lsc
  coherence_lsc := R.coherence_component_lsc

/-- The component-wise LSC fields imply LSC for the total profile price. -/
theorem leray_self_tax_prefix_price_lsc
    (S : LeraySelfTaxProfilePriceStream)
    (h : LeraySelfTaxComponentLSC S)
    (n : ℕ) :
    leraySelfTaxPrefixPrice S n ≤ leraySelfTaxLimitPrice S := by
  unfold leraySelfTaxPrefixPrice leraySelfTaxLimitPrice
  linarith [h.self_tax_lsc n, h.cross_defect_lsc n, h.coherence_lsc n]

/-- Prefix-local core_04 assembly data for the self-tax channel.

This prevents the finite self-tax component from being a naked scalar price:
the branch/self-tax prefix price must match the branch budget of a
local-to-global receipt. Cross-defect and coherence are charged by separate
component fields below, so the total budget is not double counted. -/
structure LeraySelfTaxPrefixLocalToGlobalAssembly
    (S : LeraySelfTaxProfilePriceStream) where
  receipt : ℕ → SelfTaxIntegralLocalToGlobalReceipt
  prefix_self_tax_price_eq_branch_budget :
    ∀ n, S.prefixSelfTaxPrice n = (receipt n).branchBudgetSum

/-- Component-aligned local-to-global assembly.

The compact assembly above is enough to bound the projected self-tax integral,
but a full component ledger also has to prevent cross-defect/coherence budgets
from being laundered or double-counted outside the stream's declared component
prices. -/
structure LeraySelfTaxPrefixLocalToGlobalComponentAssembly
    (S : LeraySelfTaxProfilePriceStream) extends
      LeraySelfTaxPrefixLocalToGlobalAssembly S where
  prefix_cross_defect_price_eq_budget :
    ∀ n, S.prefixCrossDefectPrice n = (receipt n).crossDefectBudget
  prefix_coherence_price_eq_budget :
    ∀ n, S.prefixCoherencePrice n = (receipt n).coherenceBudget

/-- Finite-prefix charge receipt for the assembled self-tax ledger.

This replaces a naked finite-prefix no-arbitrage assumption with a receipt
tied to the same local-to-global component assembly used for self-tax,
cross-defect, and coherence pricing. -/
structure LeraySelfTaxFinitePrefixChargeReceipt
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (n : ℕ) where
  same_component_assembly_used_for_payoff :
    S.profileStreamDeclaredBeforePayoff
  payoff_observable_declared_before_payoff :
    S.profileTopologyDeclaredBeforePayoff
  no_hidden_source_l2_or_posthoc_prefix_price :
    S.noPosthocPayoffDependentStreamChoice
  payoff_le_assembled_self_tax_integral :
    S.prefixPayoff n ≤ (A.receipt n).selfTaxIntegral

/-- Which fixed-before-payoff guard failed for a finite-prefix charge receipt.
-/
inductive LeraySelfTaxFinitePrefixChargeGuardBranch where
  | sameAssembly
  | payoffObservable
  | noHiddenPosthocPrice
deriving DecidableEq, Repr

/-- Falsifier for a finite-prefix charge receipt whose payoff/price alignment
was not actually fixed before payoff scoring. -/
structure LeraySelfTaxFinitePrefixChargeGuardFalsifier
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (H : ∀ n : ℕ,
      LeraySelfTaxFinitePrefixChargeReceipt S A n) where
  n : ℕ
  branch : LeraySelfTaxFinitePrefixChargeGuardBranch
  missing :
    match branch with
    | LeraySelfTaxFinitePrefixChargeGuardBranch.sameAssembly =>
        ¬ S.profileStreamDeclaredBeforePayoff
    | LeraySelfTaxFinitePrefixChargeGuardBranch.payoffObservable =>
        ¬ S.profileTopologyDeclaredBeforePayoff
    | LeraySelfTaxFinitePrefixChargeGuardBranch.noHiddenPosthocPrice =>
        ¬ S.noPosthocPayoffDependentStreamChoice

/-- Existing finite-prefix charge receipts exclude guard-failure falsifiers. -/
theorem no_finite_prefix_charge_guard_falsifier
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (H : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (F : LeraySelfTaxFinitePrefixChargeGuardFalsifier S A H) :
    False := by
  rcases F with ⟨n, branch, hmissing⟩
  cases branch with
  | sameAssembly =>
      exact hmissing (H n).same_component_assembly_used_for_payoff
  | payoffObservable =>
      exact hmissing (H n).payoff_observable_declared_before_payoff
  | noHiddenPosthocPrice =>
      exact hmissing (H n).no_hidden_source_l2_or_posthoc_prefix_price

/-- Finite-prefix charge receipts instantiate the compact no-arbitrage
interface used by the profile-limit adapter. -/
def finite_prefix_no_arbitrage_of_charge_receipts
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (H : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n) :
    LeraySelfTaxFinitePrefixNoArbitrage S := by
  intro n
  have hcharge : S.prefixPayoff n ≤ (A.receipt n).selfTaxIntegral :=
    (H n).payoff_le_assembled_self_tax_integral
  have hintegral :
      (A.receipt n).selfTaxIntegral ≤ leraySelfTaxPrefixPrice S n := by
    unfold leraySelfTaxPrefixPrice
    rw [A.prefix_self_tax_price_eq_branch_budget n,
      A.prefix_cross_defect_price_eq_budget n,
      A.prefix_coherence_price_eq_budget n]
    exact (A.receipt n).self_tax_charged_by_branch_and_cross
  exact hcharge.trans hintegral

/-- Component labels for local-to-global assembly-budget alignment. -/
inductive LeraySelfTaxAssemblyBudgetComponent where
  | selfTaxBranch
  | crossDefect
  | coherence
deriving DecidableEq, Repr

/-- Finite falsifier for a component mismatch between the stream and the
local-to-global receipt used to assemble it. -/
structure LeraySelfTaxAssemblyBudgetMismatchFalsifier
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S) where
  n : ℕ
  component : LeraySelfTaxAssemblyBudgetComponent
  component_mismatch :
    match component with
    | LeraySelfTaxAssemblyBudgetComponent.selfTaxBranch =>
        S.prefixSelfTaxPrice n ≠ (A.receipt n).branchBudgetSum
    | LeraySelfTaxAssemblyBudgetComponent.crossDefect =>
        S.prefixCrossDefectPrice n ≠ (A.receipt n).crossDefectBudget
    | LeraySelfTaxAssemblyBudgetComponent.coherence =>
        S.prefixCoherencePrice n ≠ (A.receipt n).coherenceBudget

/-- Component-aligned assembly excludes a finite component-budget mismatch. -/
theorem no_assembly_budget_mismatch_of_component_assembly
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (F : LeraySelfTaxAssemblyBudgetMismatchFalsifier S A) :
    False := by
  rcases F with ⟨n, component, hmismatch⟩
  cases component with
  | selfTaxBranch =>
      exact hmismatch (A.prefix_self_tax_price_eq_branch_budget n)
  | crossDefect =>
      exact hmismatch (A.prefix_cross_defect_price_eq_budget n)
  | coherence =>
      exact hmismatch (A.prefix_coherence_price_eq_budget n)

/-- The component-aligned core_04 assembly receipt really prices each prefix
self-tax integral by the total declared prefix price. -/
theorem prefix_self_tax_integral_le_prefix_price
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (n : ℕ) :
    (A.receipt n).selfTaxIntegral ≤ leraySelfTaxPrefixPrice S n := by
  unfold leraySelfTaxPrefixPrice
  rw [A.prefix_self_tax_price_eq_branch_budget n,
    A.prefix_cross_defect_price_eq_budget n,
    A.prefix_coherence_price_eq_budget n]
  exact (A.receipt n).self_tax_charged_by_branch_and_cross

/-- Component-aligned assembly identifies the declared prefix price with the
local-to-global receipt's total budget. -/
theorem leray_self_tax_prefix_price_eq_total_budget_of_component_assembly
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (n : ℕ) :
    leraySelfTaxPrefixPrice S n = (A.receipt n).totalBudget := by
  unfold leraySelfTaxPrefixPrice
  rw [A.prefix_self_tax_price_eq_branch_budget n,
    A.prefix_cross_defect_price_eq_budget n,
    A.prefix_coherence_price_eq_budget n,
    (A.receipt n).total_budget_eq]

/-- Finite-prefix charge receipts bound the prefix payoff by the same total
local-to-global budget. -/
theorem prefix_payoff_le_local_to_global_total_budget_of_charge_receipts
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (H : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (n : ℕ) :
    S.prefixPayoff n ≤ (A.receipt n).totalBudget := by
  exact (H n).payoff_le_assembled_self_tax_integral.trans
    (self_tax_integral_le_total_budget_of_local_to_global (A.receipt n))

/-- Prefix self-tax integrals are bounded by the declared limiting total price
once the local-to-global assembly and component LSC fields are both paid.

This is the concrete "smooth escape sequence" guard: a candidate cannot keep a
fixed profile price while sending the assembled projected self-tax integral to
infinity. -/
theorem prefix_self_tax_integral_le_limit_price
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (H : LeraySelfTaxComponentLSC S)
    (n : ℕ) :
    (A.receipt n).selfTaxIntegral ≤ leraySelfTaxLimitPrice S := by
  exact
    (prefix_self_tax_integral_le_prefix_price S A n).trans
      (leray_self_tax_prefix_price_lsc S H n)

/-- The full local-to-global total budget of a finite prefix is bounded by the
declared limiting total price under component LSC. -/
theorem prefix_total_budget_le_limit_price
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (H : LeraySelfTaxComponentLSC S)
    (n : ℕ) :
    (A.receipt n).totalBudget ≤ leraySelfTaxLimitPrice S := by
  rw [← leray_self_tax_prefix_price_eq_total_budget_of_component_assembly
    S A n]
  exact leray_self_tax_prefix_price_lsc S H n

/-- Finite-prefix charge receipts bound each prefix payoff by the declared
limiting total price once component LSC is paid. -/
theorem prefix_payoff_le_limit_price_of_charge_receipts
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (Hcharge :
      ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (Hlsc : LeraySelfTaxComponentLSC S)
    (n : ℕ) :
    S.prefixPayoff n ≤ leraySelfTaxLimitPrice S :=
  (prefix_payoff_le_local_to_global_total_budget_of_charge_receipts
    S A Hcharge n).trans
      (prefix_total_budget_le_limit_price S A Hlsc n)

/-- Measure-valued/Young-defect source form of the finite-prefix payoff
bound.

This is the direct source-level stepping stone used by closure attempts: once
the PDE side supplies the first-class relaxed output defect source, finite
prefix charge receipts immediately bound every payoff prefix by the declared
self-tax limit price. -/
theorem prefix_payoff_le_limit_price_of_measure_valued_source_and_charge_receipts
    (S : LeraySelfTaxProfilePriceStream)
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (Hcharge :
      ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (n : ℕ) :
    S.prefixPayoff n ≤ leraySelfTaxLimitPrice S :=
  prefix_payoff_le_limit_price_of_charge_receipts
    S A Hcharge
    (component_lsc_of_pde_receipt S
      (component_lsc_pde_receipt_of_measure_valued_output_limit_source S M))
    n

/-- A prefix-local smooth escape sequence for the assembled self-tax channel:
the local-to-global self-tax integral becomes arbitrarily large while the
candidate claims to stay in one fixed profile stream. -/
def LeraySelfTaxPrefixIntegralUnbounded
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S) : Prop :=
  ∀ B : Real, ∃ n : ℕ, B < (A.receipt n).selfTaxIntegral

/-- Component LSC plus the local-to-global assembly rules out the prefix
self-tax integral escape sequence. -/
theorem no_prefix_self_tax_integral_escape_under_component_lsc
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (H : LeraySelfTaxComponentLSC S) :
    ¬ LeraySelfTaxPrefixIntegralUnbounded S A := by
  intro hunbounded
  obtain ⟨n, hn⟩ := hunbounded (leraySelfTaxLimitPrice S)
  exact not_lt_of_ge
    (prefix_self_tax_integral_le_limit_price S A H n)
    hn

/-- A measure-valued/Young-defect output source rules out the prefix-local
self-tax integral escape sequence through the induced component-LSC receipt. -/
theorem no_prefix_self_tax_integral_escape_under_measure_valued_source
    (S : LeraySelfTaxProfilePriceStream)
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S) :
    ¬ LeraySelfTaxPrefixIntegralUnbounded S A :=
  no_prefix_self_tax_integral_escape_under_component_lsc
    S A
    (component_lsc_of_pde_receipt S
      (component_lsc_pde_receipt_of_measure_valued_output_limit_source S M))

/-- Full receipt for the profile-limit Leray self-tax LSC obligation. -/
structure LeraySelfTaxProfileLSCReceipt
    (S : LeraySelfTaxProfilePriceStream) where
  local_to_global_assembly :
    LeraySelfTaxPrefixLocalToGlobalComponentAssembly S
  finite_prefix_charge :
    ∀ n : ℕ,
      LeraySelfTaxFinitePrefixChargeReceipt
        S local_to_global_assembly n
  payoff_tail_approximated_by_prefixes :
    LeraySelfTaxPayoffTailApproximatedByPrefixes S
  component_lsc_pde_receipt :
    LeraySelfTaxComponentLSCPDEReceipt S
  profile_topology_declared_before_payoff :
    S.profileTopologyDeclaredBeforePayoff
  profile_stream_declared_before_payoff :
    S.profileStreamDeclaredBeforePayoff
  prefix_component_prices_declared_before_payoff :
    S.prefixComponentPricesDeclaredBeforePayoff
  limit_component_prices_declared_before_payoff :
    S.limitComponentPricesDeclaredBeforePayoff
  no_posthoc_payoff_dependent_stream_choice :
    S.noPosthocPayoffDependentStreamChoice

/-- PDE-facing component limit-passage receipt for the Leray self-tax stream.

This is the PDE-facing source of `LeraySelfTaxProfileLSCReceipt`; it
splits out the analytic duties so future closure attempts cannot hide
component LSC, tail payoff visibility, fixed topology, or local-to-global
assembly inside a single opaque receipt. -/
structure LeraySelfTaxComponentLimitPassageReceipt
    (S : LeraySelfTaxProfilePriceStream) where
  local_to_global_assembly :
    LeraySelfTaxPrefixLocalToGlobalComponentAssembly S
  finite_prefix_charge :
    ∀ n : ℕ,
      LeraySelfTaxFinitePrefixChargeReceipt
        S local_to_global_assembly n
  payoff_tail_approximated_by_prefixes :
    LeraySelfTaxPayoffTailApproximatedByPrefixes S
  self_tax_component_lsc :
    ∀ n, S.prefixSelfTaxPrice n ≤ S.selfTaxLimitPrice
  cross_defect_component_lsc :
    ∀ n, S.prefixCrossDefectPrice n ≤ S.crossDefectLimitPrice
  coherence_component_lsc :
    ∀ n, S.prefixCoherencePrice n ≤ S.coherenceLimitPrice
  profile_topology_declared_before_payoff :
    S.profileTopologyDeclaredBeforePayoff
  profile_stream_declared_before_payoff :
    S.profileStreamDeclaredBeforePayoff
  prefix_component_prices_declared_before_payoff :
    S.prefixComponentPricesDeclaredBeforePayoff
  limit_component_prices_declared_before_payoff :
    S.limitComponentPricesDeclaredBeforePayoff
  no_posthoc_payoff_dependent_stream_choice :
    S.noPosthocPayoffDependentStreamChoice
  no_hidden_source_l2_or_posthoc_component_substitute :
    S.noPosthocPayoffDependentStreamChoice

/-- PDE-source version of the component limit-passage receipt.

This is the version a continuum proof should try to instantiate.  It supplies
finite-prefix assembly and payoff tail visibility as before, but the component
LSC fields must come from the defect-inclusive Leray-output `L2` price receipt,
not from bare weak convergence of the velocity or a smooth-limit-only price. -/
structure LeraySelfTaxOutputLimitPassageSourceReceipt
    (S : LeraySelfTaxProfilePriceStream) where
  local_to_global_assembly :
    LeraySelfTaxPrefixLocalToGlobalComponentAssembly S
  finite_prefix_charge :
    ∀ n : ℕ,
      LeraySelfTaxFinitePrefixChargeReceipt
        S local_to_global_assembly n
  payoff_tail_approximated_by_prefixes :
    LeraySelfTaxPayoffTailApproximatedByPrefixes S
  output_limit_price :
    LeraySelfTaxOutputLimitPriceReceipt S

/-- Build the output limit-passage source from a standard topology statement
for the payoff prefixes.

The analytic PDE side often proves `Tendsto S.prefixPayoff atTop
S.payoffLimit`; the Track B receipt consumes the stronger-looking tail
visibility predicate.  This constructor keeps that translation canonical and
prevents future closure attempts from treating payoff-tail visibility as an
extra independent black box. -/
def leray_self_tax_output_limit_passage_source_of_tendsto_prefix_payoff
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (C : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hpayoff :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit))
    (P : LeraySelfTaxOutputLimitPriceReceipt S) :
    LeraySelfTaxOutputLimitPassageSourceReceipt S where
  local_to_global_assembly := A
  finite_prefix_charge := C
  payoff_tail_approximated_by_prefixes :=
    payoff_tail_approximated_by_prefixes_of_tendsto_prefix_payoff S hpayoff
  output_limit_price := P

/-- Build the output limit-passage source from a Cauchy payoff-prefix stream
and one convergent unbounded subsequence.

This is the diagonal compactness variant of
`leray_self_tax_output_limit_passage_source_of_tendsto_prefix_payoff`: a PDE
argument may identify the limiting payoff on a subsequence first, then use
Cauchy control to recover the tail-visible prefix predicate consumed by Track B.
-/
def leray_self_tax_output_limit_passage_source_of_cauchySeq_subseq_prefix_payoff
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
    (P : LeraySelfTaxOutputLimitPriceReceipt S) :
    LeraySelfTaxOutputLimitPassageSourceReceipt S where
  local_to_global_assembly := A
  finite_prefix_charge := C
  payoff_tail_approximated_by_prefixes :=
    payoff_tail_approximated_by_prefixes_of_cauchySeq_subseq_tendsto
      S hcauchy hφ hsub
  output_limit_price := P

/-- Audited PDE-source version of the output limit-passage receipt.

The extra field rules out the circular shortcut where the strong output
topology needed for the LSC step is itself obtained from the target
continuation conclusion. -/
structure LeraySelfTaxOutputLimitPassageAuditedSourceReceipt
    (S : LeraySelfTaxProfilePriceStream) extends
      LeraySelfTaxOutputLimitPassageSourceReceipt S where
  reynolds_defect_included_receipt :
    output_limit_price.reynolds_defect_included_in_relaxed_limit_price
  concentration_measure_included_receipt :
    output_limit_price.concentration_measure_included_in_relaxed_limit_price
  noncircular_output_convergence_source : Prop
  noncircular_output_convergence_source_receipt :
    noncircular_output_convergence_source

/-- Typed, source-side noncircularity receipt for a measure-valued output
limit.

This is deliberately paid by the measure-valued source fields and the stream's
predeclared no-posthoc guard.  It is not allowed to be sourced from the final
GP216 bridge or from the target regularity conclusion. -/
structure LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt
    (S : LeraySelfTaxProfilePriceStream)
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) where
  leray_projection_l2_bounded :
    M.leray_projection_l2_bounded
  nonlinear_output_convergence :
    M.nonlinear_output_converges_weakly_l2_or_strong_graph_topology
  source_topology_declared :
    M.strong_l4_w14_or_hs_source_topology_declared
  same_output_topology :
    M.cross_and_coherence_outputs_use_same_topology
  no_smooth_limit_price_substitution :
    S.noPosthocPayoffDependentStreamChoice

/-- Canonical noncircular convergence source attached to the same
measure-valued object that pays the relaxed output prices. -/
def leray_self_tax_noncircular_measure_valued_output_convergence_source
    (S : LeraySelfTaxProfilePriceStream)
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) : Prop :=
  M.leray_projection_l2_bounded ∧
    M.nonlinear_output_converges_weakly_l2_or_strong_graph_topology ∧
      M.strong_l4_w14_or_hs_source_topology_declared ∧
        M.cross_and_coherence_outputs_use_same_topology ∧
          S.noPosthocPayoffDependentStreamChoice

/-- The typed noncircular receipt instantiates the legacy audited-source
noncircular `Prop` slot without introducing a free metadata proof. -/
def leray_self_tax_noncircular_measure_valued_output_convergence_source_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (N : LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt S M) :
    leray_self_tax_noncircular_measure_valued_output_convergence_source S M :=
  ⟨N.leray_projection_l2_bounded,
    N.nonlinear_output_convergence,
    N.source_topology_declared,
    N.same_output_topology,
    N.no_smooth_limit_price_substitution⟩

/-- A fully paid measure-valued source gives the canonical noncircularity
receipt directly.  This is a projection from already-declared PDE source
fields, not a theorem about the existence of that source. -/
def leray_self_tax_noncircular_measure_valued_output_convergence_receipt_of_source
    (S : LeraySelfTaxProfilePriceStream)
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) :
    LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt S M where
  leray_projection_l2_bounded :=
    M.leray_projection_l2_bounded_receipt
  nonlinear_output_convergence :=
    M.nonlinear_output_converges_weakly_l2_or_strong_graph_topology_receipt
  source_topology_declared :=
    M.strong_l4_w14_or_hs_source_topology_declared_receipt
  same_output_topology :=
    M.cross_and_coherence_outputs_use_same_topology_receipt
  no_smooth_limit_price_substitution :=
    M.no_smooth_limit_price_substitution

/-- Build the audited output limit-passage receipt from a first-class
measure-valued defect source and ordinary payoff-prefix convergence.

This is the closure-facing theory-builder route: the PDE side supplies the
relaxed Young/defect object and a standard `Tendsto` statement; this adapter
turns those into the audited Track B receipt without allowing a smooth-limit
substitution or posthoc defect ledger. -/
def audited_output_limit_passage_source_of_measure_valued_source_and_tendsto_prefix_payoff
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
    LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S where
  local_to_global_assembly := A
  finite_prefix_charge := C
  payoff_tail_approximated_by_prefixes :=
    payoff_tail_approximated_by_prefixes_of_tendsto_prefix_payoff S hpayoff
  output_limit_price :=
    output_limit_price_receipt_of_measure_valued_source S M
  reynolds_defect_included_receipt :=
    M.measure_defect_source.reynolds_defect_reified_receipt
  concentration_measure_included_receipt :=
    M.measure_defect_source.concentration_measure_reified_receipt
  noncircular_output_convergence_source :=
    noncircular_output_convergence_source
  noncircular_output_convergence_source_receipt :=
    noncircular_output_convergence_source_receipt

/-- Tendsto payoff route with noncircularity forced through the same
measure-valued source. -/
def audited_mv_tendsto_output_source_noncircular
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (C : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hpayoff :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (N : LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt S M) :
    LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S :=
  audited_output_limit_passage_source_of_measure_valued_source_and_tendsto_prefix_payoff
    S A C hpayoff M
    (leray_self_tax_noncircular_measure_valued_output_convergence_source S M)
    (leray_self_tax_noncircular_measure_valued_output_convergence_source_receipt
      S M N)

/-- Diagonal compactness variant of the audited measure-valued output source.

The measure-valued defect object still supplies the relaxed output price.  The
only change from the Tendsto constructor is the payoff-visibility input:
Cauchy control plus one unbounded convergent subsequence is enough to produce
the same audited source receipt. -/
def audited_output_limit_passage_source_of_measure_valued_source_and_cauchySeq_subseq_prefix_payoff
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
    LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S where
  local_to_global_assembly := A
  finite_prefix_charge := C
  payoff_tail_approximated_by_prefixes :=
    payoff_tail_approximated_by_prefixes_of_cauchySeq_subseq_tendsto
      S hcauchy hφ hsub
  output_limit_price :=
    output_limit_price_receipt_of_measure_valued_source S M
  reynolds_defect_included_receipt :=
    M.measure_defect_source.reynolds_defect_reified_receipt
  concentration_measure_included_receipt :=
    M.measure_defect_source.concentration_measure_reified_receipt
  noncircular_output_convergence_source :=
    noncircular_output_convergence_source
  noncircular_output_convergence_source_receipt :=
    noncircular_output_convergence_source_receipt

/-- Cauchy/subsequence payoff route with noncircularity forced through the
same measure-valued source. -/
def audited_mv_cauchy_subseq_output_source_noncircular
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
    LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S :=
  audited_output_limit_passage_source_of_measure_valued_source_and_cauchySeq_subseq_prefix_payoff
    S A C hcauchy hφ hsub M
    (leray_self_tax_noncircular_measure_valued_output_convergence_source S M)
    (leray_self_tax_noncircular_measure_valued_output_convergence_source_receipt
      S M N)

/-- Short alias for the diagonal compactness source constructor, used where
the full descriptive name would obscure downstream composition code. -/
abbrev audited_output_limit_source_of_measure_valued_cauchy_subseq
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
    LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S :=
  audited_output_limit_passage_source_of_measure_valued_source_and_cauchySeq_subseq_prefix_payoff
    S A C hcauchy hφ hsub M
    noncircular_output_convergence_source
    noncircular_output_convergence_source_receipt

/-- Guard branches for ways the output-source receipt can silently stop being
a genuine defect-inclusive PDE limit passage. -/
inductive LeraySelfTaxOutputLimitPassageGuardFalsifier
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S) : Type where
  | smoothLimitOnlySubstitution :
      ¬ S.noPosthocPayoffDependentStreamChoice →
        LeraySelfTaxOutputLimitPassageGuardFalsifier S R
  | unchargedReynoldsDefect :
      ¬ R.output_limit_price.reynolds_defect_included_in_relaxed_limit_price →
        LeraySelfTaxOutputLimitPassageGuardFalsifier S R
  | concentrationMeasureOmitted :
      ¬ R.output_limit_price.concentration_measure_included_in_relaxed_limit_price →
        LeraySelfTaxOutputLimitPassageGuardFalsifier S R
  | numericDefectFloorOmitted :
      LeraySelfTaxRelaxedOutputDefectFloorFalsifier
        R.output_limit_price →
        LeraySelfTaxOutputLimitPassageGuardFalsifier S R
  | strongTopologyCircularity :
      ¬ R.noncircular_output_convergence_source →
        LeraySelfTaxOutputLimitPassageGuardFalsifier S R

/-- An audited output-source receipt rules out the declared guard failures. -/
theorem no_output_limit_passage_guard_falsifier_of_audited_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S)
    (F : LeraySelfTaxOutputLimitPassageGuardFalsifier S R) :
    False := by
  cases F with
  | smoothLimitOnlySubstitution h =>
      exact h R.output_limit_price.no_smooth_limit_price_substitution
  | unchargedReynoldsDefect h =>
      exact h R.reynolds_defect_included_receipt
  | concentrationMeasureOmitted h =>
      exact h R.concentration_measure_included_receipt
  | numericDefectFloorOmitted F =>
      exact
        no_relaxed_output_defect_floor_falsifier_of_output_limit_price_receipt
          S R.output_limit_price F
  | strongTopologyCircularity h =>
      exact h R.noncircular_output_convergence_source_receipt

/-- Audited output-limit passage excludes an uncharged relaxed-output defect
without dropping the audited source wrapper. -/
theorem no_uncharged_output_defect_of_audited_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S)
    (F : LeraySelfTaxUnchargedOutputDefectFalsifier
      R.output_limit_price) :
    False :=
  no_uncharged_output_defect_of_output_limit_price_receipt
    S R.output_limit_price F

/-- Audited output-limit passage excludes omission of numeric defect floors
without dropping the audited source wrapper. -/
theorem no_relaxed_output_defect_floor_falsifier_of_audited_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S)
    (F : LeraySelfTaxRelaxedOutputDefectFloorFalsifier
      R.output_limit_price) :
    False :=
  no_relaxed_output_defect_floor_falsifier_of_output_limit_price_receipt
    S R.output_limit_price F

/-- Audited output-limit passage excludes missing PDE/topology guard branches
without dropping the audited source wrapper. -/
theorem no_output_limit_price_pde_guard_falsifier_of_audited_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S)
    (F : LeraySelfTaxOutputLimitPricePDEGuardFalsifier
      R.output_limit_price) :
    False :=
  no_output_limit_price_pde_guard_falsifier
    S R.output_limit_price F

/-- A named Leray-output source for a profile price stream.

The stream itself remains scalar data, but this source package records that
the scalar component prices are being viewed as the output of an audited
defect-inclusive Leray-output limit receipt, not as free posthoc bookkeeping. -/
structure LeraySelfTaxOutputLimitStreamSource where
  stream : LeraySelfTaxProfilePriceStream
  output_limit_price :
    LeraySelfTaxOutputLimitPriceReceipt stream

/-- Build a stream source from an already audited output limit-passage receipt.
-/
def output_limit_stream_source_of_audited_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S) :
    LeraySelfTaxOutputLimitStreamSource where
  stream := S
  output_limit_price := R.output_limit_price

/-- Component LSC exposed from a named Leray-output source.

The component inequalities are still paid by the defect-inclusive output-limit
price receipt; this projection only keeps the source object visible at the API
boundary. -/
def component_lsc_of_output_limit_stream_source
    (source : LeraySelfTaxOutputLimitStreamSource) :
    LeraySelfTaxComponentLSC source.stream :=
  component_lsc_of_output_limit_price_receipt
    source.stream
    source.output_limit_price

/-- A named Leray-output source excludes the same PDE/topology guard failures
as its underlying defect-inclusive output-limit price receipt. -/
theorem no_output_limit_price_pde_guard_falsifier_of_output_limit_stream_source
    (source : LeraySelfTaxOutputLimitStreamSource)
    (F :
      LeraySelfTaxOutputLimitPricePDEGuardFalsifier
        source.output_limit_price) :
    False :=
  no_output_limit_price_pde_guard_falsifier
    source.stream
    source.output_limit_price
    F

/-- Receipt that a target scalar stream is the same stream as a named
Leray-output source.

This is intentionally identity-level scalar provenance.  It does not solve any
PDE closure obligation; it only prevents a final receipt from silently swapping
in a different scalar stream after an output/defect source has been audited. -/
structure LeraySelfTaxOutputDerivedStreamReceipt
    (source : LeraySelfTaxOutputLimitStreamSource)
    (S : LeraySelfTaxProfilePriceStream) where
  prefix_payoff_eq_source :
    ∀ n, S.prefixPayoff n = source.stream.prefixPayoff n
  prefix_self_tax_price_eq_source :
    ∀ n, S.prefixSelfTaxPrice n = source.stream.prefixSelfTaxPrice n
  prefix_cross_defect_price_eq_source :
    ∀ n, S.prefixCrossDefectPrice n = source.stream.prefixCrossDefectPrice n
  prefix_coherence_price_eq_source :
    ∀ n, S.prefixCoherencePrice n = source.stream.prefixCoherencePrice n
  payoff_limit_eq_source :
    S.payoffLimit = source.stream.payoffLimit
  self_tax_limit_price_eq_source :
    S.selfTaxLimitPrice = source.stream.selfTaxLimitPrice
  cross_defect_limit_price_eq_source :
    S.crossDefectLimitPrice = source.stream.crossDefectLimitPrice
  coherence_limit_price_eq_source :
    S.coherenceLimitPrice = source.stream.coherenceLimitPrice
  profile_topology_declared_from_source :
    S.profileTopologyDeclaredBeforePayoff
  profile_stream_declared_from_source :
    S.profileStreamDeclaredBeforePayoff
  prefix_component_prices_declared_from_source :
    S.prefixComponentPricesDeclaredBeforePayoff
  limit_component_prices_declared_from_source :
    S.limitComponentPricesDeclaredBeforePayoff
  no_posthoc_stream_choice_from_source :
    S.noPosthocPayoffDependentStreamChoice

/-- Reflexive provenance receipt for the stream carried by a named output
source. -/
def output_derived_stream_receipt_refl
    (source : LeraySelfTaxOutputLimitStreamSource) :
    LeraySelfTaxOutputDerivedStreamReceipt source source.stream where
  prefix_payoff_eq_source := fun _ => rfl
  prefix_self_tax_price_eq_source := fun _ => rfl
  prefix_cross_defect_price_eq_source := fun _ => rfl
  prefix_coherence_price_eq_source := fun _ => rfl
  payoff_limit_eq_source := rfl
  self_tax_limit_price_eq_source := rfl
  cross_defect_limit_price_eq_source := rfl
  coherence_limit_price_eq_source := rfl
  profile_topology_declared_from_source :=
    source.output_limit_price.fixed_leray_output_l2_topology
  profile_stream_declared_from_source :=
    source.output_limit_price.component_stream_fixed_before_payoff
  prefix_component_prices_declared_from_source :=
    source.output_limit_price.prefix_components_declared_before_payoff
  limit_component_prices_declared_from_source :=
    source.output_limit_price.limit_components_declared_before_payoff
  no_posthoc_stream_choice_from_source :=
    source.output_limit_price.no_smooth_limit_price_substitution

/-- Aggregate self-tax limit price is preserved by an output-derived scalar
stream provenance receipt. -/
theorem leray_self_tax_limit_price_eq_source_of_output_derived_stream_receipt
    (source : LeraySelfTaxOutputLimitStreamSource)
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedStreamReceipt source S) :
    leraySelfTaxLimitPrice S =
      leraySelfTaxLimitPrice source.stream := by
  unfold leraySelfTaxLimitPrice
  rw [R.self_tax_limit_price_eq_source,
    R.cross_defect_limit_price_eq_source,
    R.coherence_limit_price_eq_source]

/-- Aggregate self-tax prefix price is preserved by an output-derived scalar
stream provenance receipt. -/
theorem leray_self_tax_prefix_price_eq_source_of_output_derived_stream_receipt
    (source : LeraySelfTaxOutputLimitStreamSource)
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedStreamReceipt source S)
    (n : ℕ) :
    leraySelfTaxPrefixPrice S n =
      leraySelfTaxPrefixPrice source.stream n := by
  unfold leraySelfTaxPrefixPrice
  rw [R.prefix_self_tax_price_eq_source n,
    R.prefix_cross_defect_price_eq_source n,
    R.prefix_coherence_price_eq_source n]

/-- Concrete ways a target scalar stream can fail to be the stream carried by
an audited Leray-output source. -/
inductive LeraySelfTaxOutputSourceSubstitutionFalsifier
    (source : LeraySelfTaxOutputLimitStreamSource)
    (S : LeraySelfTaxProfilePriceStream)
    (Rprov : LeraySelfTaxOutputDerivedStreamReceipt source S) : Prop where
  | prefixPayoff (n : ℕ) :
      S.prefixPayoff n ≠ source.stream.prefixPayoff n →
        LeraySelfTaxOutputSourceSubstitutionFalsifier source S Rprov
  | prefixSelfTax (n : ℕ) :
      S.prefixSelfTaxPrice n ≠ source.stream.prefixSelfTaxPrice n →
        LeraySelfTaxOutputSourceSubstitutionFalsifier source S Rprov
  | prefixCrossDefect (n : ℕ) :
      S.prefixCrossDefectPrice n ≠
        source.stream.prefixCrossDefectPrice n →
          LeraySelfTaxOutputSourceSubstitutionFalsifier source S Rprov
  | prefixCoherence (n : ℕ) :
      S.prefixCoherencePrice n ≠ source.stream.prefixCoherencePrice n →
        LeraySelfTaxOutputSourceSubstitutionFalsifier source S Rprov
  | payoffLimit :
      S.payoffLimit ≠ source.stream.payoffLimit →
        LeraySelfTaxOutputSourceSubstitutionFalsifier source S Rprov
  | selfTaxLimit :
      S.selfTaxLimitPrice ≠ source.stream.selfTaxLimitPrice →
        LeraySelfTaxOutputSourceSubstitutionFalsifier source S Rprov
  | crossDefectLimit :
      S.crossDefectLimitPrice ≠ source.stream.crossDefectLimitPrice →
        LeraySelfTaxOutputSourceSubstitutionFalsifier source S Rprov
  | coherenceLimit :
      S.coherenceLimitPrice ≠ source.stream.coherenceLimitPrice →
        LeraySelfTaxOutputSourceSubstitutionFalsifier source S Rprov

/-- A source-derived stream receipt rules out arbitrary scalar-source
substitution. -/
theorem no_output_source_substitution_falsifier
    (source : LeraySelfTaxOutputLimitStreamSource)
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedStreamReceipt source S)
    (F : LeraySelfTaxOutputSourceSubstitutionFalsifier source S R) :
    False := by
  cases F with
  | prefixPayoff n h =>
      exact h (R.prefix_payoff_eq_source n)
  | prefixSelfTax n h =>
      exact h (R.prefix_self_tax_price_eq_source n)
  | prefixCrossDefect n h =>
      exact h (R.prefix_cross_defect_price_eq_source n)
  | prefixCoherence n h =>
      exact h (R.prefix_coherence_price_eq_source n)
  | payoffLimit h =>
      exact h R.payoff_limit_eq_source
  | selfTaxLimit h =>
      exact h R.self_tax_limit_price_eq_source
  | crossDefectLimit h =>
      exact h R.cross_defect_limit_price_eq_source
  | coherenceLimit h =>
      exact h R.coherence_limit_price_eq_source

/-- Component-limit passage plus explicit audited-output stream provenance.

This wrapper preserves the older component-limit API while giving downstream
receipts a stronger type to require when they need to distinguish an arbitrary
scalar stream from one derived from an audited Leray self-tax output source. -/
structure LeraySelfTaxOutputDerivedComponentLimitPassageReceipt
    (S : LeraySelfTaxProfilePriceStream) where
  component_limit_passage :
    LeraySelfTaxComponentLimitPassageReceipt S
  output_source :
    LeraySelfTaxOutputLimitStreamSource
  stream_provenance :
    LeraySelfTaxOutputDerivedStreamReceipt output_source S

/-- Rebuild the component-limit receipt from the named output source.

The local assembly, finite-prefix charge, and payoff-tail receipts remain the
separate finite-ledger work of `component_limit_passage`.  The component LSC
inequalities themselves are rederived from the defect-inclusive output source
and then transported through the stream-provenance equalities, so a manually
built output-derived wrapper cannot smuggle arbitrary LSC inequalities while
carrying decorative output provenance. -/
def component_limit_passage_source_checked_of_output_derived
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S) :
    LeraySelfTaxComponentLimitPassageReceipt S where
  local_to_global_assembly :=
    R.component_limit_passage.local_to_global_assembly
  finite_prefix_charge :=
    R.component_limit_passage.finite_prefix_charge
  payoff_tail_approximated_by_prefixes :=
    R.component_limit_passage.payoff_tail_approximated_by_prefixes
  self_tax_component_lsc := by
    intro n
    have hsource :
        R.output_source.stream.prefixSelfTaxPrice n ≤
          R.output_source.stream.selfTaxLimitPrice :=
      (component_lsc_of_output_limit_price_receipt
        R.output_source.stream
        R.output_source.output_limit_price).self_tax_lsc n
    simpa
      [R.stream_provenance.prefix_self_tax_price_eq_source n,
        R.stream_provenance.self_tax_limit_price_eq_source]
      using hsource
  cross_defect_component_lsc := by
    intro n
    have hsource :
        R.output_source.stream.prefixCrossDefectPrice n ≤
          R.output_source.stream.crossDefectLimitPrice :=
      (component_lsc_of_output_limit_price_receipt
        R.output_source.stream
        R.output_source.output_limit_price).cross_defect_lsc n
    simpa
      [R.stream_provenance.prefix_cross_defect_price_eq_source n,
        R.stream_provenance.cross_defect_limit_price_eq_source]
      using hsource
  coherence_component_lsc := by
    intro n
    have hsource :
        R.output_source.stream.prefixCoherencePrice n ≤
          R.output_source.stream.coherenceLimitPrice :=
      (component_lsc_of_output_limit_price_receipt
        R.output_source.stream
        R.output_source.output_limit_price).coherence_lsc n
    simpa
      [R.stream_provenance.prefix_coherence_price_eq_source n,
        R.stream_provenance.coherence_limit_price_eq_source]
      using hsource
  profile_topology_declared_before_payoff :=
    R.stream_provenance.profile_topology_declared_from_source
  profile_stream_declared_before_payoff :=
    R.stream_provenance.profile_stream_declared_from_source
  prefix_component_prices_declared_before_payoff :=
    R.stream_provenance.prefix_component_prices_declared_from_source
  limit_component_prices_declared_before_payoff :=
    R.stream_provenance.limit_component_prices_declared_from_source
  no_posthoc_payoff_dependent_stream_choice :=
    R.stream_provenance.no_posthoc_stream_choice_from_source
  no_hidden_source_l2_or_posthoc_component_substitute :=
    R.stream_provenance.no_posthoc_stream_choice_from_source

/-- Drop the provenance wrapper when an older consumer only needs the
component-limit receipt. -/
def component_limit_passage_of_output_derived
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S) :
    LeraySelfTaxComponentLimitPassageReceipt S :=
  component_limit_passage_source_checked_of_output_derived S R

/-- Sourced component-limit receipts exclude the same arbitrary source
substitution falsifier. -/
theorem no_output_source_substitution_falsifier_of_output_derived
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (F : LeraySelfTaxOutputSourceSubstitutionFalsifier
      R.output_source S R.stream_provenance) :
    False :=
  no_output_source_substitution_falsifier
    R.output_source S R.stream_provenance F

/-- Defect-inclusive output-limit source receipt instantiates the component
limit-passage receipt consumed by GP216. -/
def component_limit_passage_of_output_limit_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageSourceReceipt S) :
    LeraySelfTaxComponentLimitPassageReceipt S where
  local_to_global_assembly := R.local_to_global_assembly
  finite_prefix_charge := R.finite_prefix_charge
  payoff_tail_approximated_by_prefixes :=
    R.payoff_tail_approximated_by_prefixes
  self_tax_component_lsc :=
    (component_lsc_of_output_limit_price_receipt
      S R.output_limit_price).self_tax_lsc
  cross_defect_component_lsc :=
    (component_lsc_of_output_limit_price_receipt
      S R.output_limit_price).cross_defect_lsc
  coherence_component_lsc :=
    (component_lsc_of_output_limit_price_receipt
      S R.output_limit_price).coherence_lsc
  profile_topology_declared_before_payoff :=
    R.output_limit_price.fixed_leray_output_l2_topology
  profile_stream_declared_before_payoff :=
    R.output_limit_price.component_stream_fixed_before_payoff
  prefix_component_prices_declared_before_payoff :=
    R.output_limit_price.prefix_components_declared_before_payoff
  limit_component_prices_declared_before_payoff :=
    R.output_limit_price.limit_components_declared_before_payoff
  no_posthoc_payoff_dependent_stream_choice :=
    R.output_limit_price.no_smooth_limit_price_substitution
  no_hidden_source_l2_or_posthoc_component_substitute :=
    R.output_limit_price.no_smooth_limit_price_substitution

/-- Audited defect-inclusive output-limit source receipt instantiates the
component limit-passage receipt consumed by GP216. -/
def component_limit_passage_of_audited_output_limit_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S) :
    LeraySelfTaxComponentLimitPassageReceipt S :=
  component_limit_passage_of_output_limit_source
    S
    R.toLeraySelfTaxOutputLimitPassageSourceReceipt

/-- Existing audited output limit-passage data constructs the sourced
component-limit receipt without adding any PDE closure. -/
def output_derived_component_limit_passage_of_audited_output_limit_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S) :
    LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S where
  component_limit_passage :=
    component_limit_passage_of_audited_output_limit_source S R
  output_source :=
    output_limit_stream_source_of_audited_passage S R
  stream_provenance :=
    output_derived_stream_receipt_refl
      (output_limit_stream_source_of_audited_passage S R)

/-- Full profile-LSC receipt exposes component LSC only through the
PDE/topology component receipt. -/
def component_lsc_of_profile_lsc_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (H : LeraySelfTaxProfileLSCReceipt S) :
    LeraySelfTaxComponentLSC S :=
  component_lsc_of_pde_receipt S H.component_lsc_pde_receipt

/-- Component limit-passage receipt instantiates the compact profile-LSC
receipt consumed by the GP216 spine. -/
def leray_self_tax_profile_lsc_receipt_of_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S) :
    LeraySelfTaxProfileLSCReceipt S where
  local_to_global_assembly := R.local_to_global_assembly
  finite_prefix_charge := R.finite_prefix_charge
  payoff_tail_approximated_by_prefixes :=
    R.payoff_tail_approximated_by_prefixes
  component_lsc_pde_receipt :=
    { fixed_lp_bony_profile_topology :=
        R.profile_topology_declared_before_payoff
      component_stream_fixed_before_payoff :=
        R.profile_stream_declared_before_payoff
      prefix_components_declared_before_payoff :=
        R.prefix_component_prices_declared_before_payoff
      limit_components_declared_before_payoff :=
        R.limit_component_prices_declared_before_payoff
      no_hidden_source_l2_component_substitute :=
        R.no_hidden_source_l2_or_posthoc_component_substitute
      self_tax_component_lsc := R.self_tax_component_lsc
      cross_defect_component_lsc := R.cross_defect_component_lsc
      coherence_component_lsc := R.coherence_component_lsc }
  profile_topology_declared_before_payoff :=
    R.profile_topology_declared_before_payoff
  profile_stream_declared_before_payoff :=
    R.profile_stream_declared_before_payoff
  prefix_component_prices_declared_before_payoff :=
    R.prefix_component_prices_declared_before_payoff
  limit_component_prices_declared_before_payoff :=
    R.limit_component_prices_declared_before_payoff
  no_posthoc_payoff_dependent_stream_choice :=
    R.no_posthoc_payoff_dependent_stream_choice

/-- Output-derived component-limit passage instantiates the compact
profile-LSC receipt without exposing a detachable scalar component-LSC
premise.

This adapter adds no analytic content: the component inequalities are rebuilt
through `component_limit_passage_of_output_derived`, which keeps the audited
Leray-output source and stream-provenance equalities attached. -/
def leray_self_tax_profile_lsc_receipt_of_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S) :
    LeraySelfTaxProfileLSCReceipt S :=
  leray_self_tax_profile_lsc_receipt_of_component_limit_passage
    S
    (component_limit_passage_of_output_derived S R)

/-- Component limit-passage receipt exposes the compact component-LSC
interface directly.

This theorem is intentionally only an adapter: the analytic work remains the
three component LSC fields in `LeraySelfTaxComponentLimitPassageReceipt`.  The
direct edge keeps closure attempts from hiding behind the older aggregate
profile-LSC receipt when the sharper PDE/topology receipt is the real source.
-/
def component_lsc_of_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S) :
    LeraySelfTaxComponentLSC S where
  self_tax_lsc := R.self_tax_component_lsc
  cross_defect_lsc := R.cross_defect_component_lsc
  coherence_lsc := R.coherence_component_lsc

/-- Component limit-passage receipt bounds every finite prefix payoff by the
declared limiting total price. -/
theorem prefix_payoff_le_limit_price_under_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S)
    (n : ℕ) :
    S.prefixPayoff n ≤ leraySelfTaxLimitPrice S :=
  prefix_payoff_le_limit_price_of_charge_receipts
    S R.local_to_global_assembly R.finite_prefix_charge
    (component_lsc_of_component_limit_passage S R) n

/-- Component limit-passage receipt instantiates finite-prefix no-arbitrage
through its declared local-to-global assembly and prefix charge receipts. -/
theorem finite_prefix_no_arbitrage_of_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S) :
    LeraySelfTaxFinitePrefixNoArbitrage S :=
  finite_prefix_no_arbitrage_of_charge_receipts
    S R.local_to_global_assembly R.finite_prefix_charge

/-- Full profile-LSC receipt rules out the same smooth escape sequence for its
declared local-to-global self-tax assembly. -/
theorem no_prefix_self_tax_integral_escape_under_profile_lsc_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (H : LeraySelfTaxProfileLSCReceipt S) :
    ¬ LeraySelfTaxPrefixIntegralUnbounded
      S H.local_to_global_assembly :=
  no_prefix_self_tax_integral_escape_under_component_lsc
    S H.local_to_global_assembly
    (component_lsc_of_profile_lsc_receipt S H)

/-- Component limit-passage receipt directly rules out the smooth prefix
self-tax integral escape sequence for its declared local-to-global assembly.

This is the sharper form of the smooth-escape guard: it depends on the explicit
component topology/LSC receipt, not on an opaque aggregate profile-LSC object.
-/
theorem no_prefix_self_tax_integral_escape_under_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S) :
    ¬ LeraySelfTaxPrefixIntegralUnbounded
      S R.local_to_global_assembly :=
  no_prefix_self_tax_integral_escape_under_component_lsc
    S R.local_to_global_assembly
    (component_lsc_of_component_limit_passage S R)

/-- Output-derived component-limit passage exposes the finite per-prefix
self-tax integral bound, with the audited Leray-output source still attached.
-/
theorem prefix_self_tax_integral_le_limit_price_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (n : ℕ) :
    let C := component_limit_passage_of_output_derived S R
    (C.local_to_global_assembly.receipt n).selfTaxIntegral ≤
      leraySelfTaxLimitPrice S :=
  prefix_self_tax_integral_le_limit_price
    S
    (component_limit_passage_of_output_derived S R).local_to_global_assembly
    (component_lsc_of_component_limit_passage S
      (component_limit_passage_of_output_derived S R))
    n

/-- Output-derived component-limit passage rules out the same smooth prefix
self-tax integral escape while preserving audited Leray-output provenance. -/
theorem no_prefix_self_tax_integral_escape_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S) :
    ¬ LeraySelfTaxPrefixIntegralUnbounded
      S (component_limit_passage_of_output_derived S R).local_to_global_assembly :=
  by
    intro hunbounded
    obtain ⟨n, hn⟩ := hunbounded (leraySelfTaxLimitPrice S)
    exact not_lt_of_ge
      (prefix_self_tax_integral_le_limit_price_under_output_derived_component_limit_passage
        S R n)
      hn

/-- Finite-prefix undercharge of the assembled local-to-global self-tax
receipt.

This is the finite version of the smooth-escape guard: even before asking for
an unbounded sequence, one prefix is invalid if the declared self-tax prefix
price is already smaller than the assembled projected self-tax integral it is
supposed to price. -/
def LeraySelfTaxPrefixAssemblyUndercharged
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S) : Prop :=
  ∃ n : ℕ, leraySelfTaxPrefixPrice S n < (A.receipt n).selfTaxIntegral

/-- The local-to-global assembly equality plus the local receipt budget rules
out finite self-tax assembly undercharge. -/
theorem no_prefix_assembly_undercharge_of_local_to_global_assembly
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S) :
    ¬ LeraySelfTaxPrefixAssemblyUndercharged S A := by
  intro hbad
  rcases hbad with ⟨n, hn⟩
  exact not_lt_of_ge
    (prefix_self_tax_integral_le_prefix_price S A n)
    hn

/-- Full profile-LSC receipt rules out finite assembly undercharge for its
declared local-to-global self-tax receipt. -/
theorem no_prefix_assembly_undercharge_under_profile_lsc_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (H : LeraySelfTaxProfileLSCReceipt S) :
    ¬ LeraySelfTaxPrefixAssemblyUndercharged
      S H.local_to_global_assembly :=
  no_prefix_assembly_undercharge_of_local_to_global_assembly
    S H.local_to_global_assembly

/-- Component limit-passage receipt also rules out finite assembly
undercharge through the same declared local-to-global assembly. -/
theorem no_prefix_assembly_undercharge_under_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S) :
    ¬ LeraySelfTaxPrefixAssemblyUndercharged
      S R.local_to_global_assembly :=
  no_prefix_assembly_undercharge_of_local_to_global_assembly
    S R.local_to_global_assembly

/-- Output-derived component-limit passage rules out finite assembly
undercharge without dropping the audited Leray-output provenance package. -/
theorem no_prefix_assembly_undercharge_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S) :
    ¬ LeraySelfTaxPrefixAssemblyUndercharged
      S (component_limit_passage_of_output_derived S R).local_to_global_assembly :=
  no_prefix_assembly_undercharge_under_component_limit_passage
    S (component_limit_passage_of_output_derived S R)

/-- Output-derived component-limit passage excludes guard failures for its
finite-prefix charge receipts without dropping the audited Leray-output
provenance package. -/
theorem no_finite_prefix_charge_guard_falsifier_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (F :
      LeraySelfTaxFinitePrefixChargeGuardFalsifier
        S
        (component_limit_passage_of_output_derived S R).local_to_global_assembly
        (component_limit_passage_of_output_derived S R).finite_prefix_charge) :
    False :=
  no_finite_prefix_charge_guard_falsifier
    S
    (component_limit_passage_of_output_derived S R).local_to_global_assembly
    (component_limit_passage_of_output_derived S R).finite_prefix_charge
    F

/-- Output-derived component-limit passage excludes component-budget assembly
mismatches for its declared local-to-global assembly while preserving the
audited Leray-output provenance package. -/
theorem no_assembly_budget_mismatch_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (F :
      LeraySelfTaxAssemblyBudgetMismatchFalsifier
        S
        (component_limit_passage_of_output_derived S R).local_to_global_assembly) :
    False :=
  no_assembly_budget_mismatch_of_component_assembly
    S
    (component_limit_passage_of_output_derived S R).local_to_global_assembly
    F

/-- View the Leray self-tax/profile stream through the existing Boss Fight 3
profile-limit LSC interface. -/
def profileLimitStreamOfLeraySelfTax
    (S : LeraySelfTaxProfilePriceStream) :
    ProfileLimitStream where
  prefixPayoff := S.prefixPayoff
  prefixPrice := leraySelfTaxPrefixPrice S
  payoffLimit := S.payoffLimit
  priceLimit := leraySelfTaxLimitPrice S

/-- The Leray self-tax receipt instantiates the generic profile-limit LSC
certificate. -/
def profile_lsc_certificate_of_leray_self_tax_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (h : LeraySelfTaxProfileLSCReceipt S) :
    ProfileLimitLSCCertificate (profileLimitStreamOfLeraySelfTax S) where
  finite_prefix_no_survivor :=
    finite_prefix_no_arbitrage_of_charge_receipts
      S h.local_to_global_assembly h.finite_prefix_charge
  payoff_approximated_by_prefix :=
    payoff_approximated_by_prefix_of_tail_approx
      S h.payoff_tail_approximated_by_prefixes
  prefix_price_lsc :=
    leray_self_tax_prefix_price_lsc S
      (component_lsc_of_profile_lsc_receipt S h)

/-- Main obligation receipt: finite prefix charging plus component-wise LSC and
prefix payoff approximation prevent a new global self-tax arbitrage from
appearing only at the profile limit. -/
theorem no_global_self_tax_arbitrage_of_profile_lsc_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (h : LeraySelfTaxProfileLSCReceipt S) :
    S.payoffLimit ≤ leraySelfTaxLimitPrice S :=
  profile_limit_no_survivor_of_lsc_certificate
    (profileLimitStreamOfLeraySelfTax S)
    (profile_lsc_certificate_of_leray_self_tax_receipt S h)

/-- Component-limit-passage form of the self-tax profile no-arbitrage theorem.

This exposes the graph-critical edge `S.payoffLimit -> leraySelfTaxLimitPrice`
through the explicit PDE/topology receipt rather than an opaque aggregate LSC
assumption. -/
theorem no_global_self_tax_arbitrage_of_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S) :
    S.payoffLimit ≤ leraySelfTaxLimitPrice S :=
  no_global_self_tax_arbitrage_of_profile_lsc_receipt S
    (leray_self_tax_profile_lsc_receipt_of_component_limit_passage S R)

/-- Defect-inclusive output-limit source receipt is enough to rule out global
profile-limit self-tax arbitrage. -/
theorem no_global_self_tax_arbitrage_of_output_limit_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageSourceReceipt S) :
    S.payoffLimit ≤ leraySelfTaxLimitPrice S :=
  no_global_self_tax_arbitrage_of_component_limit_passage S
    (component_limit_passage_of_output_limit_source S R)

/-- Audited defect-inclusive output-limit source receipt is enough to rule out
global profile-limit self-tax arbitrage. -/
theorem no_global_self_tax_arbitrage_of_audited_output_limit_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S) :
    S.payoffLimit ≤ leraySelfTaxLimitPrice S :=
  no_global_self_tax_arbitrage_of_component_limit_passage S
    (component_limit_passage_of_audited_output_limit_source S R)

/-- Output-derived component-limit passage rules out global profile-limit
self-tax arbitrage while keeping scalar stream provenance available to
downstream falsifiers. -/
theorem no_global_self_tax_arbitrage_of_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S) :
    S.payoffLimit ≤ leraySelfTaxLimitPrice S :=
  no_global_self_tax_arbitrage_of_component_limit_passage S
    (component_limit_passage_of_output_derived S R)

/-- Source object for the self-tax-only view of a countable pricing stream.

This is a genuine source bridge from the existing countable profile-pricing
spine into the Leray self-tax stream interface.  It is intentionally a
specialization: all declared limiting price is routed through the self-tax
component, while cross-defect and coherence components are zero.  The caller
still has to supply fixed-topology guards, nonnegative finite-prefix budgets,
the countable no-arbitrage/price-LSC certificate, and tail-visible payoff
approximation. -/
structure CountableSelfTaxProfilePriceStreamSource where
  stream : CountablePricingStream
  profileTopologyDeclaredBeforePayoff : Prop
  profileTopologyDeclaredBeforePayoffPaid :
    profileTopologyDeclaredBeforePayoff
  profileStreamDeclaredBeforePayoff : Prop
  profileStreamDeclaredBeforePayoffPaid :
    profileStreamDeclaredBeforePayoff
  prefixComponentPricesDeclaredBeforePayoff : Prop
  prefixComponentPricesDeclaredBeforePayoffPaid :
    prefixComponentPricesDeclaredBeforePayoff
  limitComponentPricesDeclaredBeforePayoff : Prop
  limitComponentPricesDeclaredBeforePayoffPaid :
    limitComponentPricesDeclaredBeforePayoff
  noPosthocPayoffDependentStreamChoice : Prop
  noPosthocPayoffDependentStreamChoicePaid :
    noPosthocPayoffDependentStreamChoice
  prefix_payoff_nonnegative :
    ∀ n : ℕ, 0 ≤ prefixPayoff stream.profiles n
  prefix_price_nonnegative :
    ∀ n : ℕ, 0 ≤ prefixPrice stream.profiles n
  certificate : CountableLimitCertificate stream
  payoff_tail_approximated_by_prefixes :
    ∀ N : ℕ, ∀ ε : Real, 0 < ε →
      ∃ n : ℕ, N ≤ n ∧
        stream.payoffLimit ≤ prefixPayoff stream.profiles n + ε

/-- Leray self-tax profile stream induced by a countable pricing source.

The prefix payoff and self-tax price are exactly the countable prefix payoff
and prefix price.  Cross-defect and coherence are zero in this specialization,
so downstream code cannot accidentally read extra component charges from this
adapter. -/
def leray_self_tax_profile_price_stream_of_countable_self_tax_source
    (C : CountableSelfTaxProfilePriceStreamSource) :
    LeraySelfTaxProfilePriceStream where
  prefixPayoff := fun n => prefixPayoff C.stream.profiles n
  prefixSelfTaxPrice := fun n => prefixPrice C.stream.profiles n
  prefixCrossDefectPrice := fun _ => 0
  prefixCoherencePrice := fun _ => 0
  payoffLimit := C.stream.payoffLimit
  selfTaxLimitPrice := C.stream.priceLimit
  crossDefectLimitPrice := 0
  coherenceLimitPrice := 0
  profileTopologyDeclaredBeforePayoff :=
    C.profileTopologyDeclaredBeforePayoff
  profileStreamDeclaredBeforePayoff :=
    C.profileStreamDeclaredBeforePayoff
  prefixComponentPricesDeclaredBeforePayoff :=
    C.prefixComponentPricesDeclaredBeforePayoff
  limitComponentPricesDeclaredBeforePayoff :=
    C.limitComponentPricesDeclaredBeforePayoff
  noPosthocPayoffDependentStreamChoice :=
    C.noPosthocPayoffDependentStreamChoice

/-- Local-to-global receipt for one countable prefix under the self-tax-only
adapter. -/
def countable_self_tax_local_to_global_receipt
    (C : CountableSelfTaxProfilePriceStreamSource)
    (n : ℕ) :
    SelfTaxIntegralLocalToGlobalReceipt where
  selfTaxIntegral := prefixPayoff C.stream.profiles n
  branchBudgetSum := prefixPrice C.stream.profiles n
  crossDefectBudget := 0
  coherenceBudget := 0
  totalBudget := prefixPrice C.stream.profiles n
  self_tax_integral_nonnegative := C.prefix_payoff_nonnegative n
  branch_budget_nonnegative := C.prefix_price_nonnegative n
  cross_defect_budget_nonnegative := by norm_num
  coherence_budget_nonnegative := by norm_num
  fixed_topology_predeclared :=
    C.profileTopologyDeclaredBeforePayoff
  fixed_topology_predeclared_paid :=
    C.profileTopologyDeclaredBeforePayoffPaid
  observable_class_predeclared :=
    C.profileStreamDeclaredBeforePayoff
  observable_class_predeclared_paid :=
    C.profileStreamDeclaredBeforePayoffPaid
  branch_prices_declared_before_payoff :=
    C.prefixComponentPricesDeclaredBeforePayoff
  branch_prices_declared_before_payoff_paid :=
    C.prefixComponentPricesDeclaredBeforePayoffPaid
  cross_defects_charged_before_gluing :=
    C.prefixComponentPricesDeclaredBeforePayoff
  cross_defects_charged_before_gluing_paid :=
    C.prefixComponentPricesDeclaredBeforePayoffPaid
  coherence_terms_charged_before_gluing :=
    C.prefixComponentPricesDeclaredBeforePayoff
  coherence_terms_charged_before_gluing_paid :=
    C.prefixComponentPricesDeclaredBeforePayoffPaid
  self_tax_charged_by_branch_and_cross := by
    simpa using
      prefix_no_arbitrage_of_pointwise
        C.stream.profiles
        C.certificate.pointwise_no_arbitrage
        n
  total_budget_eq := by ring

/-- Component-aligned local-to-global assembly induced by a countable
self-tax source. -/
def countable_self_tax_local_to_global_component_assembly
    (C : CountableSelfTaxProfilePriceStreamSource) :
    LeraySelfTaxPrefixLocalToGlobalComponentAssembly
      (leray_self_tax_profile_price_stream_of_countable_self_tax_source C) where
  receipt := fun n => countable_self_tax_local_to_global_receipt C n
  prefix_self_tax_price_eq_branch_budget := by
    intro n
    rfl
  prefix_cross_defect_price_eq_budget := by
    intro n
    rfl
  prefix_coherence_price_eq_budget := by
    intro n
    rfl

/-- Finite-prefix charge receipt induced by a countable self-tax source. -/
def countable_self_tax_finite_prefix_charge_receipt
    (C : CountableSelfTaxProfilePriceStreamSource)
    (n : ℕ) :
    LeraySelfTaxFinitePrefixChargeReceipt
      (leray_self_tax_profile_price_stream_of_countable_self_tax_source C)
      (countable_self_tax_local_to_global_component_assembly C)
      n where
  same_component_assembly_used_for_payoff :=
    C.profileStreamDeclaredBeforePayoffPaid
  payoff_observable_declared_before_payoff :=
    C.profileTopologyDeclaredBeforePayoffPaid
  no_hidden_source_l2_or_posthoc_prefix_price :=
    C.noPosthocPayoffDependentStreamChoicePaid
  payoff_le_assembled_self_tax_integral := by
    rfl

/-- Component-limit receipt induced by a countable self-tax source. -/
def component_limit_passage_of_countable_self_tax_source
    (C : CountableSelfTaxProfilePriceStreamSource) :
    LeraySelfTaxComponentLimitPassageReceipt
      (leray_self_tax_profile_price_stream_of_countable_self_tax_source C) where
  local_to_global_assembly :=
    countable_self_tax_local_to_global_component_assembly C
  finite_prefix_charge :=
    countable_self_tax_finite_prefix_charge_receipt C
  payoff_tail_approximated_by_prefixes := by
    intro N ε hε
    obtain ⟨n, hN, hpay⟩ :=
      C.payoff_tail_approximated_by_prefixes N ε hε
    exact ⟨n, hN, hpay⟩
  self_tax_component_lsc := by
    intro n
    exact C.certificate.prefix_price_le_limit n
  cross_defect_component_lsc := by
    intro n
    rfl
  coherence_component_lsc := by
    intro n
    rfl
  profile_topology_declared_before_payoff :=
    C.profileTopologyDeclaredBeforePayoffPaid
  profile_stream_declared_before_payoff :=
    C.profileStreamDeclaredBeforePayoffPaid
  prefix_component_prices_declared_before_payoff :=
    C.prefixComponentPricesDeclaredBeforePayoffPaid
  limit_component_prices_declared_before_payoff :=
    C.limitComponentPricesDeclaredBeforePayoffPaid
  no_posthoc_payoff_dependent_stream_choice :=
    C.noPosthocPayoffDependentStreamChoicePaid
  no_hidden_source_l2_or_posthoc_component_substitute :=
    C.noPosthocPayoffDependentStreamChoicePaid

/-- Countable self-tax profile-pricing source instantiates the compact Leray
self-tax LSC receipt. -/
def leray_self_tax_profile_lsc_receipt_of_countable_self_tax_source
    (C : CountableSelfTaxProfilePriceStreamSource) :
    LeraySelfTaxProfileLSCReceipt
      (leray_self_tax_profile_price_stream_of_countable_self_tax_source C) :=
  leray_self_tax_profile_lsc_receipt_of_component_limit_passage
    (leray_self_tax_profile_price_stream_of_countable_self_tax_source C)
    (component_limit_passage_of_countable_self_tax_source C)

/-- The countable self-tax source has no limiting self-tax arbitrage. -/
theorem no_global_self_tax_arbitrage_of_countable_self_tax_source
    (C : CountableSelfTaxProfilePriceStreamSource) :
    (leray_self_tax_profile_price_stream_of_countable_self_tax_source C).payoffLimit ≤
      leraySelfTaxLimitPrice
        (leray_self_tax_profile_price_stream_of_countable_self_tax_source C) :=
  no_global_self_tax_arbitrage_of_component_limit_passage
    (leray_self_tax_profile_price_stream_of_countable_self_tax_source C)
    (component_limit_passage_of_countable_self_tax_source C)

/-- Component-limit source for the continuum all-output LP/Bony projection.

The earlier `LeraySelfTaxContinuumLimitComponentSplit` only declares how the
aggregate continuum target is split into the three Leray self-tax components.
This source adds exactly the extra data needed for a component-limit passage:
component nonnegativity, component-wise prefix-to-limit bounds, and the
already audited all-output finite-prefix charge from `ContinuumAllOutputLPBonySource`.
-/
structure LeraySelfTaxContinuumComponentLimitPassageSource
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ) where
  split : LeraySelfTaxContinuumLimitComponentSplit source.stream
  prefix_self_tax_nonnegative :
    ∀ n : ℕ, 0 ≤ source.stream.prefixSelfTaxPrice n
  prefix_cross_defect_nonnegative :
    ∀ n : ℕ, 0 ≤ source.stream.prefixCrossProfilePrice n
  prefix_coherence_nonnegative :
    ∀ n : ℕ, 0 ≤ source.stream.prefixResidualPrice n
  prefix_total_nonnegative :
    ∀ n : ℕ, 0 ≤ continuumLPPrefixPrice source.stream n
  self_tax_prefix_le_limit :
    ∀ n : ℕ, source.stream.prefixSelfTaxPrice n ≤ split.selfTaxLimitPrice
  cross_defect_prefix_le_limit :
    ∀ n : ℕ,
      source.stream.prefixCrossProfilePrice n ≤ split.crossDefectLimitPrice
  coherence_prefix_le_limit :
    ∀ n : ℕ, source.stream.prefixResidualPrice n ≤ split.coherenceLimitPrice

/-- Local-to-global receipt induced by the continuum all-output LP/Bony source.

The self-tax integral is the aggregate all-output prefix price.  Its charge by
branch/cross/coherence is definitional, while payoff-to-prefix pricing comes
from `source.prefix_charge`. -/
def continuum_all_output_self_tax_local_to_global_receipt
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (P : LeraySelfTaxContinuumComponentLimitPassageSource source)
    (n : ℕ) :
    SelfTaxIntegralLocalToGlobalReceipt where
  selfTaxIntegral := continuumLPPrefixPrice source.stream n
  branchBudgetSum := source.stream.prefixSelfTaxPrice n
  crossDefectBudget := source.stream.prefixCrossProfilePrice n
  coherenceBudget := source.stream.prefixResidualPrice n
  totalBudget := continuumLPPrefixPrice source.stream n
  self_tax_integral_nonnegative := P.prefix_total_nonnegative n
  branch_budget_nonnegative := P.prefix_self_tax_nonnegative n
  cross_defect_budget_nonnegative := P.prefix_cross_defect_nonnegative n
  coherence_budget_nonnegative := P.prefix_coherence_nonnegative n
  fixed_topology_predeclared := ContinuumLPUsesFixedTopology source.stream
  fixed_topology_predeclared_paid := source.fixed_topology
  observable_class_predeclared := source.stream_declared_before_payoff
  observable_class_predeclared_paid :=
    source.stream_declared_before_payoff_paid
  branch_prices_declared_before_payoff :=
    source.fixed_atoms.constants_declared_before_payoff
  branch_prices_declared_before_payoff_paid :=
    source.fixed_atoms.constants_declared_before_payoff_paid
  cross_defects_charged_before_gluing :=
    (source.prefix_charge n).cross_profile_defect_charged
  cross_defects_charged_before_gluing_paid :=
    (source.prefix_charge n).cross_profile_defect_charged_paid
  coherence_terms_charged_before_gluing :=
    (source.prefix_charge n).positive_coherence_charged
  coherence_terms_charged_before_gluing_paid :=
    (source.prefix_charge n).positive_coherence_charged_paid
  self_tax_charged_by_branch_and_cross := by
    unfold continuumLPPrefixPrice
    rfl
  total_budget_eq := by
    unfold continuumLPPrefixPrice
    rfl

/-- Component-aligned local-to-global assembly induced by a continuum
all-output source. -/
def continuum_all_output_self_tax_component_assembly
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (P : LeraySelfTaxContinuumComponentLimitPassageSource source) :
    LeraySelfTaxPrefixLocalToGlobalComponentAssembly
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        source P.split) where
  receipt := fun n =>
    continuum_all_output_self_tax_local_to_global_receipt source P n
  prefix_self_tax_price_eq_branch_budget := by
    intro n
    rfl
  prefix_cross_defect_price_eq_budget := by
    intro n
    rfl
  prefix_coherence_price_eq_budget := by
    intro n
    rfl

/-- Finite-prefix charge receipt induced by a continuum all-output source. -/
def continuum_all_output_self_tax_finite_prefix_charge
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (P : LeraySelfTaxContinuumComponentLimitPassageSource source)
    (n : ℕ) :
    LeraySelfTaxFinitePrefixChargeReceipt
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        source P.split)
      (continuum_all_output_self_tax_component_assembly source P)
      n where
  same_component_assembly_used_for_payoff :=
    source.stream_declared_before_payoff_paid
  payoff_observable_declared_before_payoff :=
    source.fixed_topology
  no_hidden_source_l2_or_posthoc_prefix_price :=
    ⟨source.no_posthoc_stream_or_atom_substitution_paid,
      source.fixed_atoms.no_hidden_source_l2_substitute_paid⟩
  payoff_le_assembled_self_tax_integral :=
    (source.prefix_charge n).prefix_payoff_le_price

/-- Continuum all-output LP/Bony source plus component split instantiates the
Leray self-tax component-limit passage. -/
def component_limit_passage_of_continuum_all_output_source
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (P : LeraySelfTaxContinuumComponentLimitPassageSource source) :
    LeraySelfTaxComponentLimitPassageReceipt
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        source P.split) where
  local_to_global_assembly :=
    continuum_all_output_self_tax_component_assembly source P
  finite_prefix_charge :=
    continuum_all_output_self_tax_finite_prefix_charge source P
  payoff_tail_approximated_by_prefixes := by
    intro N ε hε
    refine ⟨N, le_rfl, ?_⟩
    dsimp [leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource]
    linarith
  self_tax_component_lsc := P.self_tax_prefix_le_limit
  cross_defect_component_lsc := P.cross_defect_prefix_le_limit
  coherence_component_lsc := P.coherence_prefix_le_limit
  profile_topology_declared_before_payoff :=
    source.fixed_topology
  profile_stream_declared_before_payoff :=
    source.stream_declared_before_payoff_paid
  prefix_component_prices_declared_before_payoff :=
    source.fixed_atoms.constants_declared_before_payoff_paid
  limit_component_prices_declared_before_payoff :=
    P.split.limit_component_prices_declared_before_payoff_paid
  no_posthoc_payoff_dependent_stream_choice :=
    ⟨source.no_posthoc_stream_or_atom_substitution_paid,
      source.fixed_atoms.no_hidden_source_l2_substitute_paid⟩
  no_hidden_source_l2_or_posthoc_component_substitute :=
    ⟨source.no_posthoc_stream_or_atom_substitution_paid,
      source.fixed_atoms.no_hidden_source_l2_substitute_paid⟩

/-- Compact profile-LSC receipt induced by a continuum all-output source. -/
def leray_self_tax_profile_lsc_receipt_of_continuum_all_output_source
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (P : LeraySelfTaxContinuumComponentLimitPassageSource source) :
    LeraySelfTaxProfileLSCReceipt
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        source P.split) :=
  leray_self_tax_profile_lsc_receipt_of_component_limit_passage
    (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource source P.split)
    (component_limit_passage_of_continuum_all_output_source source P)

/-- Continuum all-output source plus component split rules out limiting
self-tax arbitrage for the projected Leray stream. -/
theorem no_global_self_tax_arbitrage_of_continuum_all_output_source
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ)
    (P : LeraySelfTaxContinuumComponentLimitPassageSource source) :
    (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        source P.split).payoffLimit ≤
      leraySelfTaxLimitPrice
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          source P.split) :=
  no_global_self_tax_arbitrage_of_component_limit_passage
    (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource source P.split)
    (component_limit_passage_of_continuum_all_output_source source P)

/-- Bundled noncircular measure-valued source for one fixed Leray self-tax
profile stream.

This is the source-side package a PDE closure should instantiate before
asking for any GP216/block composition receipt: it carries the stream, the
core_04 local-to-global component assembly, finite-prefix charge receipts,
ordinary payoff convergence, the measure-valued relaxed-output source, and the
typed noncircular convergence receipt tied to that same measure-valued object.
-/
structure LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource where
  stream : LeraySelfTaxProfilePriceStream
  local_to_global_assembly :
    LeraySelfTaxPrefixLocalToGlobalComponentAssembly stream
  finite_prefix_charge :
    ∀ n : ℕ,
      LeraySelfTaxFinitePrefixChargeReceipt
        stream local_to_global_assembly n
  prefix_payoff_tendsto :
    Filter.Tendsto stream.prefixPayoff Filter.atTop
      (nhds stream.payoffLimit)
  measure_valued_output_limit :
    LeraySelfTaxMeasureValuedOutputLimitSource stream
  noncircular_output_convergence :
    LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt
      stream measure_valued_output_limit

/-- Constructor from the concrete PDE-facing ingredients to the bundled
noncircular measure-valued stream source. -/
def noncircular_mv_profile_price_stream_source_of_tendsto
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (C : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hpayoff :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (N : LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt S M) :
    LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource where
  stream := S
  local_to_global_assembly := A
  finite_prefix_charge := C
  prefix_payoff_tendsto := hpayoff
  measure_valued_output_limit := M
  noncircular_output_convergence := N

/-- Diagonal compactness constructor for the bundled noncircular
measure-valued stream source.

The PDE side often first produces Cauchy control plus a convergent subsequence.
This constructor upgrades that compactness data to the full payoff-prefix
`Tendsto` field required by the one-object noncircular source package. -/
def noncircular_mv_profile_price_stream_source_of_cauchySeq_subseq
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
    LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource where
  stream := S
  local_to_global_assembly := A
  finite_prefix_charge := C
  prefix_payoff_tendsto := by
    exact tendsto_nhds_of_cauchySeq_of_subseq
      hcauchy
      hφ.tendsto_atTop
      (by simpa [Function.comp_def] using hsub)
  measure_valued_output_limit := M
  noncircular_output_convergence := N

/-- The bundled noncircular measure-valued stream source instantiates the
audited output-limit passage receipt. -/
def audited_output_limit_passage_of_noncircular_mv_stream_source
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource) :
    LeraySelfTaxOutputLimitPassageAuditedSourceReceipt Q.stream :=
  audited_mv_tendsto_output_source_noncircular
    Q.stream
    Q.local_to_global_assembly
    Q.finite_prefix_charge
    Q.prefix_payoff_tendsto
    Q.measure_valued_output_limit
    Q.noncircular_output_convergence

/-- The bundled noncircular measure-valued stream source instantiates the
output-derived component-limit receipt while preserving audited stream
provenance. -/
def output_derived_component_limit_passage_of_noncircular_mv_stream_source
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource) :
    LeraySelfTaxOutputDerivedComponentLimitPassageReceipt Q.stream :=
  output_derived_component_limit_passage_of_audited_output_limit_source
    Q.stream
    (audited_output_limit_passage_of_noncircular_mv_stream_source
      Q)

/-- The bundled noncircular measure-valued stream source instantiates the
profile-LSC receipt consumed by the generic profile-limit adapter. -/
def profile_lsc_receipt_of_noncircular_mv_stream_source
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource) :
    LeraySelfTaxProfileLSCReceipt Q.stream :=
  leray_self_tax_profile_lsc_receipt_of_output_derived_component_limit_passage
    Q.stream
    (output_derived_component_limit_passage_of_noncircular_mv_stream_source
      Q)

/-- A bundled noncircular measure-valued stream source is enough to rule out a
new profile-limit self-tax arbitrage for that same stream. -/
theorem no_global_self_tax_arbitrage_of_noncircular_mv_stream_source
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource) :
    Q.stream.payoffLimit ≤ leraySelfTaxLimitPrice Q.stream :=
  no_global_self_tax_arbitrage_of_profile_lsc_receipt
    Q.stream
    (profile_lsc_receipt_of_noncircular_mv_stream_source
      Q)

/-- The bundled noncircular measure-valued stream source exposes the named
Leray-output stream source directly.

This is only a projection: the output-limit price receipt is still built from
the same measure-valued defect object carried by `Q`. -/
def output_limit_stream_source_of_noncircular_mv_stream_source
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource) :
    LeraySelfTaxOutputLimitStreamSource :=
  output_limit_stream_source_of_audited_passage
    Q.stream
    (audited_output_limit_passage_of_noncircular_mv_stream_source Q)

/-- Cycle-free Track B endpoint view of a concrete Leray self-tax/profile
stream.

The endpoint type lives in the upstream Track B spine, so it can be referenced
without making that spine import this downstream self-tax module.  This adapter
is the explicit downstream identification: the endpoint payoff and limit price
are exactly the stream payoff and `leraySelfTaxLimitPrice`. -/
def trackB_self_tax_limit_endpoint_of_leray_stream
    (S : LeraySelfTaxProfilePriceStream) :
    TrackBSelfTaxLimitEndpoint where
  payoffLimit := S.payoffLimit
  limitPrice := leraySelfTaxLimitPrice S
  profileTopologyDeclaredBeforePayoff :=
    S.profileTopologyDeclaredBeforePayoff
  profileStreamDeclaredBeforePayoff :=
    S.profileStreamDeclaredBeforePayoff
  prefixComponentPricesDeclaredBeforePayoff :=
    S.prefixComponentPricesDeclaredBeforePayoff
  limitComponentPricesDeclaredBeforePayoff :=
    S.limitComponentPricesDeclaredBeforePayoff
  noPosthocPayoffDependentStreamChoice :=
    S.noPosthocPayoffDependentStreamChoice

/-- Component-limit passage produces the upstream self-tax endpoint receipt
for the same stream. -/
def trackB_self_tax_endpoint_limit_passage_of_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S) :
    TrackBSelfTaxEndpointLimitPassageReceipt
      (trackB_self_tax_limit_endpoint_of_leray_stream S) where
  profile_topology_declared_before_payoff :=
    R.profile_topology_declared_before_payoff
  profile_stream_declared_before_payoff :=
    R.profile_stream_declared_before_payoff
  prefix_component_prices_declared_before_payoff :=
    R.prefix_component_prices_declared_before_payoff
  limit_component_prices_declared_before_payoff :=
    R.limit_component_prices_declared_before_payoff
  no_posthoc_payoff_dependent_stream_choice :=
    R.no_posthoc_payoff_dependent_stream_choice
  limit_no_arbitrage :=
    no_global_self_tax_arbitrage_of_component_limit_passage S R

/-- Source-derived component-limit passage produces the upstream self-tax
endpoint receipt while preserving audited Leray-output provenance. -/
def trackB_self_tax_endpoint_limit_passage_of_output_derived
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S) :
    TrackBSelfTaxEndpointLimitPassageReceipt
      (trackB_self_tax_limit_endpoint_of_leray_stream S) where
  profile_topology_declared_before_payoff :=
    R.stream_provenance.profile_topology_declared_from_source
  profile_stream_declared_before_payoff :=
    R.stream_provenance.profile_stream_declared_from_source
  prefix_component_prices_declared_before_payoff :=
    R.stream_provenance.prefix_component_prices_declared_from_source
  limit_component_prices_declared_before_payoff :=
    R.stream_provenance.limit_component_prices_declared_from_source
  no_posthoc_payoff_dependent_stream_choice :=
    R.stream_provenance.no_posthoc_stream_choice_from_source
  limit_no_arbitrage :=
    no_global_self_tax_arbitrage_of_output_derived_component_limit_passage
      S R

/-- Audited output-limit source form of the endpoint limit-passage adapter.

This is the endpoint-facing route GP216 should use when the underlying source
is a defect-inclusive audited Leray-output passage receipt. -/
def trackB_self_tax_endpoint_limit_passage_of_audited_output_limit_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S) :
    TrackBSelfTaxEndpointLimitPassageReceipt
      (trackB_self_tax_limit_endpoint_of_leray_stream S) :=
  trackB_self_tax_endpoint_limit_passage_of_output_derived S
    (output_derived_component_limit_passage_of_audited_output_limit_source S R)

/-- Output-derived self-tax provenance exposes endpoint source readiness
without accepting a detached endpoint receipt. -/
theorem trackB_self_tax_endpoint_source_ready_of_output_derived
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S) :
    TrackBSelfTaxEndpointSourceReady
      (trackB_self_tax_limit_endpoint_of_leray_stream S) :=
  trackb_self_tax_endpoint_source_ready_of_limit_passage
    (trackB_self_tax_limit_endpoint_of_leray_stream S)
    (trackB_self_tax_endpoint_limit_passage_of_output_derived S R)

/-- Output-derived self-tax provenance excludes endpoint guard failure without
accepting an arbitrary endpoint receipt. -/
theorem no_trackb_self_tax_endpoint_guard_falsifier_of_output_derived
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (F :
      TrackBSelfTaxEndpointGuardFalsifier
        (trackB_self_tax_limit_endpoint_of_leray_stream S)) :
    False :=
  no_trackb_self_tax_endpoint_guard_falsifier_of_limit_passage
    (trackB_self_tax_limit_endpoint_of_leray_stream S)
    (trackB_self_tax_endpoint_limit_passage_of_output_derived S R)
    F

/-- Audited-output self-tax provenance exposes endpoint source readiness
through the output-derived route. -/
theorem trackB_self_tax_endpoint_source_ready_of_audited_output_limit_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S) :
    TrackBSelfTaxEndpointSourceReady
      (trackB_self_tax_limit_endpoint_of_leray_stream S) :=
  trackb_self_tax_endpoint_source_ready_of_limit_passage
    (trackB_self_tax_limit_endpoint_of_leray_stream S)
    (trackB_self_tax_endpoint_limit_passage_of_audited_output_limit_source S R)

/-- Audited-output self-tax provenance excludes endpoint guard failure through
the same source-preserving route. -/
theorem no_trackb_self_tax_endpoint_guard_falsifier_of_audited_output_limit_source
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S)
    (F :
      TrackBSelfTaxEndpointGuardFalsifier
        (trackB_self_tax_limit_endpoint_of_leray_stream S)) :
    False :=
  no_trackb_self_tax_endpoint_guard_falsifier_of_limit_passage
    (trackB_self_tax_limit_endpoint_of_leray_stream S)
    (trackB_self_tax_endpoint_limit_passage_of_audited_output_limit_source S R)
    F

/-- Bundled noncircular measure-valued source form of the upstream self-tax
endpoint receipt. -/
def trackB_self_tax_endpoint_limit_passage_of_noncircular_mv_stream_source
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource) :
    TrackBSelfTaxEndpointLimitPassageReceipt
      (trackB_self_tax_limit_endpoint_of_leray_stream Q.stream) :=
  trackB_self_tax_endpoint_limit_passage_of_audited_output_limit_source
    Q.stream
    (audited_output_limit_passage_of_noncircular_mv_stream_source Q)

/-- Bundled noncircular measure-valued source form of endpoint source
readiness. -/
theorem trackB_self_tax_endpoint_source_ready_of_noncircular_mv_stream_source
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource) :
    TrackBSelfTaxEndpointSourceReady
      (trackB_self_tax_limit_endpoint_of_leray_stream Q.stream) :=
  trackb_self_tax_endpoint_source_ready_of_limit_passage
    (trackB_self_tax_limit_endpoint_of_leray_stream Q.stream)
    (trackB_self_tax_endpoint_limit_passage_of_noncircular_mv_stream_source Q)

/-- Global self-tax arbitrage at the profile limit. -/
def GlobalLeraySelfTaxArbitrage
    (S : LeraySelfTaxProfilePriceStream) : Prop :=
  leraySelfTaxLimitPrice S < S.payoffLimit

/-- The profile LSC receipt rules out global self-tax arbitrage. -/
theorem no_global_self_tax_arbitrage
    (S : LeraySelfTaxProfilePriceStream)
    (h : LeraySelfTaxProfileLSCReceipt S) :
    ¬ GlobalLeraySelfTaxArbitrage S := by
  intro harb
  exact not_lt_of_ge
    (no_global_self_tax_arbitrage_of_profile_lsc_receipt S h)
    harb

/-- Component-limit-passage receipt rules out global self-tax arbitrage
directly, without using an opaque aggregate profile-LSC premise. -/
theorem no_global_self_tax_arbitrage_under_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S) :
    ¬ GlobalLeraySelfTaxArbitrage S := by
  intro harb
  exact not_lt_of_ge
    (no_global_self_tax_arbitrage_of_component_limit_passage S R)
    harb

/-- The source-derived component-limit receipt excludes global self-tax
arbitrage without discarding the audited-output provenance package. -/
theorem no_global_self_tax_arbitrage_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S) :
    ¬ GlobalLeraySelfTaxArbitrage S := by
  intro harb
  exact not_lt_of_ge
    (no_global_self_tax_arbitrage_of_output_derived_component_limit_passage
      S R)
    harb

/-- Finite-prefix arbitrage falsifier: the declared prefix payoff already
exceeds the declared assembled prefix price. -/
structure LeraySelfTaxFinitePrefixArbitrageFalsifier
    (S : LeraySelfTaxProfilePriceStream) where
  n : ℕ
  prefix_price_lt_payoff :
    leraySelfTaxPrefixPrice S n < S.prefixPayoff n

/-- Finite-prefix no-arbitrage excludes a prefix arbitrage falsifier. -/
theorem no_finite_prefix_arbitrage_of_leray_self_tax_no_arbitrage
    (S : LeraySelfTaxProfilePriceStream)
    (h : LeraySelfTaxFinitePrefixNoArbitrage S)
    (F : LeraySelfTaxFinitePrefixArbitrageFalsifier S) :
    False :=
  not_lt_of_ge (h F.n) F.prefix_price_lt_payoff

/-- Full profile-LSC receipt excludes finite-prefix arbitrage. -/
theorem no_finite_prefix_arbitrage_under_profile_lsc_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (H : LeraySelfTaxProfileLSCReceipt S)
    (F : LeraySelfTaxFinitePrefixArbitrageFalsifier S) :
    False :=
  no_finite_prefix_arbitrage_of_leray_self_tax_no_arbitrage
    S
    (finite_prefix_no_arbitrage_of_charge_receipts
      S H.local_to_global_assembly H.finite_prefix_charge)
    F

/-- Component limit-passage receipt excludes finite-prefix arbitrage directly.

This keeps the finite-prefix charge edge attached to the PDE/topology receipt
that supplies the local-to-global assembly, rather than routing only through
the aggregate profile-LSC adapter. -/
theorem no_finite_prefix_arbitrage_under_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S)
    (F : LeraySelfTaxFinitePrefixArbitrageFalsifier S) :
    False :=
  no_finite_prefix_arbitrage_of_leray_self_tax_no_arbitrage
    S
    (finite_prefix_no_arbitrage_of_component_limit_passage S R)
    F

/-- Output-derived component-limit passage excludes finite-prefix arbitrage
directly, preserving the audited output-source identity used by downstream
falsifiers. -/
theorem no_finite_prefix_arbitrage_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (F : LeraySelfTaxFinitePrefixArbitrageFalsifier S) :
    False :=
  no_finite_prefix_arbitrage_under_component_limit_passage
    S (component_limit_passage_of_output_derived S R) F

/-- Payoff approximation failure: the limiting payoff is separated from every
finite prefix by a fixed positive gap.

This is the anti-ghost branch for a stream whose finite prefixes are correctly
priced but whose claimed limit payoff was never visible in the prefix topology.
-/
structure LeraySelfTaxPayoffApproximationFalsifier
    (S : LeraySelfTaxProfilePriceStream) where
  gap : Real
  gap_positive : 0 < gap
  every_prefix_misses_limit :
    ∀ n : ℕ, S.prefixPayoff n + gap < S.payoffLimit

/-- Prefix approximation excludes a fixed positive gap between the limit payoff
and every finite prefix. -/
theorem no_payoff_approximation_gap_of_leray_self_tax_prefix_approx
    (S : LeraySelfTaxProfilePriceStream)
    (h : LeraySelfTaxPayoffApproximatedByPrefixes S)
    (F : LeraySelfTaxPayoffApproximationFalsifier S) :
    False := by
  obtain ⟨n, hn⟩ := h F.gap F.gap_positive
  exact not_lt_of_ge hn (F.every_prefix_misses_limit n)

/-- Full profile-LSC receipt excludes payoff approximation failure. -/
theorem no_payoff_approximation_gap_under_profile_lsc_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (H : LeraySelfTaxProfileLSCReceipt S)
    (F : LeraySelfTaxPayoffApproximationFalsifier S) :
    False :=
  no_payoff_approximation_gap_of_leray_self_tax_prefix_approx
    S
    (payoff_approximated_by_prefix_of_tail_approx
      S H.payoff_tail_approximated_by_prefixes)
    F

/-- Component limit-passage receipt excludes a fixed payoff approximation gap.
-/
theorem no_payoff_approximation_gap_under_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S)
    (F : LeraySelfTaxPayoffApproximationFalsifier S) :
    False :=
  no_payoff_approximation_gap_of_leray_self_tax_prefix_approx
    S
    (payoff_approximated_by_prefix_of_tail_approx
      S R.payoff_tail_approximated_by_prefixes)
    F

/-- Output-derived component-limit passage excludes a fixed payoff
approximation gap while preserving audited Leray-output provenance. -/
theorem no_payoff_approximation_gap_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (F : LeraySelfTaxPayoffApproximationFalsifier S) :
    False :=
  no_payoff_approximation_gap_under_component_limit_passage
    S (component_limit_passage_of_output_derived S R) F

/-- Tail payoff approximation failure: after some cutoff, the limiting payoff
is separated from every later prefix by a fixed positive gap. -/
structure LeraySelfTaxPayoffTailApproximationFalsifier
    (S : LeraySelfTaxProfilePriceStream) where
  N : ℕ
  gap : Real
  gap_positive : 0 < gap
  every_tail_prefix_misses_limit :
    ∀ n : ℕ, N ≤ n → S.prefixPayoff n + gap < S.payoffLimit

/-- Tail-visible payoff approximation excludes a fixed positive tail gap. -/
theorem no_tail_payoff_approximation_gap_of_leray_self_tax_tail_approx
    (S : LeraySelfTaxProfilePriceStream)
    (h : LeraySelfTaxPayoffTailApproximatedByPrefixes S)
    (F : LeraySelfTaxPayoffTailApproximationFalsifier S) :
    False := by
  obtain ⟨n, hn_tail, hn⟩ := h F.N F.gap F.gap_positive
  exact not_lt_of_ge hn (F.every_tail_prefix_misses_limit n hn_tail)

/-- Full profile-LSC receipt excludes payoff tail-approximation failure. -/
theorem no_tail_payoff_approximation_gap_under_profile_lsc_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (H : LeraySelfTaxProfileLSCReceipt S)
    (F : LeraySelfTaxPayoffTailApproximationFalsifier S) :
    False :=
  no_tail_payoff_approximation_gap_of_leray_self_tax_tail_approx
    S H.payoff_tail_approximated_by_prefixes F

/-- Component limit-passage receipt excludes a fixed tail payoff gap. -/
theorem no_tail_payoff_approximation_gap_under_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S)
    (F : LeraySelfTaxPayoffTailApproximationFalsifier S) :
    False :=
  no_tail_payoff_approximation_gap_of_leray_self_tax_tail_approx
    S R.payoff_tail_approximated_by_prefixes F

/-- Output-derived component-limit passage excludes a fixed tail payoff gap
without dropping the audited output-source identity. -/
theorem no_tail_payoff_approximation_gap_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (F : LeraySelfTaxPayoffTailApproximationFalsifier S) :
    False :=
  no_tail_payoff_approximation_gap_under_component_limit_passage
    S (component_limit_passage_of_output_derived S R) F

/-- Which anti-tautology guard failed for a Leray self-tax/profile stream. -/
inductive LeraySelfTaxPostHocStreamBranch where
  | topology
  | stream
  | prefixPrices
  | limitPrices
  | payoffDependentChoice
deriving DecidableEq, Repr

/-- A posthoc stream falsifier records that one of the fixed-before-payoff
guards on the Leray self-tax/profile stream was not paid. -/
structure LeraySelfTaxPostHocStreamFalsifier
    (S : LeraySelfTaxProfilePriceStream) where
  branch : LeraySelfTaxPostHocStreamBranch
  missing :
    match branch with
    | LeraySelfTaxPostHocStreamBranch.topology =>
        ¬ S.profileTopologyDeclaredBeforePayoff
    | LeraySelfTaxPostHocStreamBranch.stream =>
        ¬ S.profileStreamDeclaredBeforePayoff
    | LeraySelfTaxPostHocStreamBranch.prefixPrices =>
        ¬ S.prefixComponentPricesDeclaredBeforePayoff
    | LeraySelfTaxPostHocStreamBranch.limitPrices =>
        ¬ S.limitComponentPricesDeclaredBeforePayoff
    | LeraySelfTaxPostHocStreamBranch.payoffDependentChoice =>
        ¬ S.noPosthocPayoffDependentStreamChoice

/-- A raw missing fixed-stream guard is exactly a posthoc-stream falsifier. -/
theorem nonempty_leray_self_tax_posthoc_stream_falsifier_of_missing_stream_guard
    (S : LeraySelfTaxProfilePriceStream)
    (hmissing :
      ¬ S.profileTopologyDeclaredBeforePayoff ∨
        ¬ S.profileStreamDeclaredBeforePayoff ∨
          ¬ S.prefixComponentPricesDeclaredBeforePayoff ∨
            ¬ S.limitComponentPricesDeclaredBeforePayoff ∨
              ¬ S.noPosthocPayoffDependentStreamChoice) :
    Nonempty (LeraySelfTaxPostHocStreamFalsifier S) := by
  rcases hmissing with htopology | hmissing
  · exact
      ⟨⟨LeraySelfTaxPostHocStreamBranch.topology,
        htopology⟩⟩
  rcases hmissing with hstream | hmissing
  · exact
      ⟨⟨LeraySelfTaxPostHocStreamBranch.stream,
        hstream⟩⟩
  rcases hmissing with hprefix | hmissing
  · exact
      ⟨⟨LeraySelfTaxPostHocStreamBranch.prefixPrices,
        hprefix⟩⟩
  rcases hmissing with hlimit | hchoice
  · exact
      ⟨⟨LeraySelfTaxPostHocStreamBranch.limitPrices,
        hlimit⟩⟩
  · exact
      ⟨⟨LeraySelfTaxPostHocStreamBranch.payoffDependentChoice,
        hchoice⟩⟩

/-- A full profile-LSC receipt cannot coexist with a posthoc-stream falsifier.
-/
theorem no_profile_lsc_receipt_of_posthoc_leray_self_tax_stream
    (S : LeraySelfTaxProfilePriceStream)
    (F : LeraySelfTaxPostHocStreamFalsifier S) :
    LeraySelfTaxProfileLSCReceipt S → False := by
  intro H
  rcases F with ⟨branch, hmissing⟩
  cases branch with
  | topology =>
      exact hmissing H.profile_topology_declared_before_payoff
  | stream =>
      exact hmissing H.profile_stream_declared_before_payoff
  | prefixPrices =>
      exact hmissing H.prefix_component_prices_declared_before_payoff
  | limitPrices =>
      exact hmissing H.limit_component_prices_declared_before_payoff
  | payoffDependentChoice =>
      exact hmissing H.no_posthoc_payoff_dependent_stream_choice

/-- The sharper component-limit-passage receipt also cannot coexist with a
posthoc-stream falsifier. -/
theorem no_component_limit_passage_receipt_of_posthoc_leray_self_tax_stream
    (S : LeraySelfTaxProfilePriceStream)
    (F : LeraySelfTaxPostHocStreamFalsifier S) :
    LeraySelfTaxComponentLimitPassageReceipt S → False := by
  intro R
  rcases F with ⟨branch, hmissing⟩
  cases branch with
  | topology =>
      exact hmissing R.profile_topology_declared_before_payoff
  | stream =>
      exact hmissing R.profile_stream_declared_before_payoff
  | prefixPrices =>
      exact hmissing R.prefix_component_prices_declared_before_payoff
  | limitPrices =>
      exact hmissing R.limit_component_prices_declared_before_payoff
  | payoffDependentChoice =>
      exact hmissing R.no_posthoc_payoff_dependent_stream_choice

/-- Output-derived component-limit passage cannot coexist with a posthoc
stream falsifier, while keeping the source/substitution receipt available. -/
theorem no_output_derived_component_limit_passage_of_posthoc_leray_self_tax_stream
    (S : LeraySelfTaxProfilePriceStream)
    (F : LeraySelfTaxPostHocStreamFalsifier S) :
    LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S → False := by
  intro R
  exact
    no_component_limit_passage_receipt_of_posthoc_leray_self_tax_stream
      S F (component_limit_passage_of_output_derived S R)

/-- A component-level LSC falsifier records exactly which prefix and declared
component price broke lower-semicontinuity. -/
structure LeraySelfTaxComponentLSCFalsifier
    (S : LeraySelfTaxProfilePriceStream) where
  n : ℕ
  component : LeraySelfTaxPriceComponent
  prefixComponentPrice : Real
  limitComponentPrice : Real
  prefix_component_price_eq :
    prefixComponentPrice =
      match component with
      | LeraySelfTaxPriceComponent.selfTax => S.prefixSelfTaxPrice n
      | LeraySelfTaxPriceComponent.crossDefect => S.prefixCrossDefectPrice n
      | LeraySelfTaxPriceComponent.coherence => S.prefixCoherencePrice n
  limit_component_price_eq :
    limitComponentPrice =
      match component with
      | LeraySelfTaxPriceComponent.selfTax => S.selfTaxLimitPrice
      | LeraySelfTaxPriceComponent.crossDefect => S.crossDefectLimitPrice
      | LeraySelfTaxPriceComponent.coherence => S.coherenceLimitPrice
  limit_lt_prefix : limitComponentPrice < prefixComponentPrice

/-- Self-tax component price-drop falsifier constructor. -/
def self_tax_lsc_falsifier
    (S : LeraySelfTaxProfilePriceStream)
    (n : ℕ)
    (hdrop : S.selfTaxLimitPrice < S.prefixSelfTaxPrice n) :
    LeraySelfTaxComponentLSCFalsifier S where
  n := n
  component := LeraySelfTaxPriceComponent.selfTax
  prefixComponentPrice := S.prefixSelfTaxPrice n
  limitComponentPrice := S.selfTaxLimitPrice
  prefix_component_price_eq := rfl
  limit_component_price_eq := rfl
  limit_lt_prefix := hdrop

/-- Cross-defect component price-drop falsifier constructor. -/
def cross_defect_lsc_falsifier
    (S : LeraySelfTaxProfilePriceStream)
    (n : ℕ)
    (hdrop : S.crossDefectLimitPrice < S.prefixCrossDefectPrice n) :
    LeraySelfTaxComponentLSCFalsifier S where
  n := n
  component := LeraySelfTaxPriceComponent.crossDefect
  prefixComponentPrice := S.prefixCrossDefectPrice n
  limitComponentPrice := S.crossDefectLimitPrice
  prefix_component_price_eq := rfl
  limit_component_price_eq := rfl
  limit_lt_prefix := hdrop

/-- Coherence component price-drop falsifier constructor. -/
def coherence_lsc_falsifier
    (S : LeraySelfTaxProfilePriceStream)
    (n : ℕ)
    (hdrop : S.coherenceLimitPrice < S.prefixCoherencePrice n) :
    LeraySelfTaxComponentLSCFalsifier S where
  n := n
  component := LeraySelfTaxPriceComponent.coherence
  prefixComponentPrice := S.prefixCoherencePrice n
  limitComponentPrice := S.coherenceLimitPrice
  prefix_component_price_eq := rfl
  limit_component_price_eq := rfl
  limit_lt_prefix := hdrop

/-- A component-level price-drop falsifier blocks the component LSC receipt. -/
theorem no_component_lsc_of_leray_self_tax_falsifier
    (S : LeraySelfTaxProfilePriceStream)
    (F : LeraySelfTaxComponentLSCFalsifier S) :
    ¬ LeraySelfTaxComponentLSC S := by
  intro h
  rcases F with
    ⟨n, component, prefixComponentPrice, limitComponentPrice,
      hprefix, hlimit, hdrop⟩
  cases component with
  | selfTax =>
      have hle : prefixComponentPrice ≤ limitComponentPrice := by
        rw [hprefix, hlimit]
        exact h.self_tax_lsc n
      exact not_lt_of_ge hle hdrop
  | crossDefect =>
      have hle : prefixComponentPrice ≤ limitComponentPrice := by
        rw [hprefix, hlimit]
        exact h.cross_defect_lsc n
      exact not_lt_of_ge hle hdrop
  | coherence =>
      have hle : prefixComponentPrice ≤ limitComponentPrice := by
        rw [hprefix, hlimit]
        exact h.coherence_lsc n
      exact not_lt_of_ge hle hdrop

/-- A component-level LSC falsifier blocks the full profile LSC receipt. -/
theorem no_profile_lsc_receipt_of_leray_self_tax_falsifier
    (S : LeraySelfTaxProfilePriceStream)
    (F : LeraySelfTaxComponentLSCFalsifier S) :
    LeraySelfTaxProfileLSCReceipt S → False := by
  intro h
  exact no_component_lsc_of_leray_self_tax_falsifier S F
    (component_lsc_of_profile_lsc_receipt S h)

/-- Source-preserving component-LSC falsifier closure.

The component-drop branch is discharged directly from the output-derived
component-limit passage, keeping the audited Leray-output source provenance
available instead of routing through the aggregate profile-LSC wrapper. -/
theorem no_component_lsc_falsifier_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (F : LeraySelfTaxComponentLSCFalsifier S) :
    False :=
  no_component_lsc_of_leray_self_tax_falsifier S F
    (component_lsc_of_component_limit_passage S
      (component_limit_passage_of_output_derived S R))

/-- Aggregate total-price LSC falsifier.  This is weaker information than a
component falsifier, but any true total drop must come from at least one
declared component drop. -/
structure LeraySelfTaxTotalLSCFalsifier
    (S : LeraySelfTaxProfilePriceStream) where
  n : ℕ
  limit_total_lt_prefix_total :
    leraySelfTaxLimitPrice S < leraySelfTaxPrefixPrice S n

/-- A total Leray self-tax price drop exposes a concrete component LSC
falsifier.  This prevents aggregate tail bookkeeping from hiding component
failure by moving slack between self-tax, cross-defect, and coherence prices.
-/
theorem component_lsc_falsifier_of_total_self_tax_price_drop
    (S : LeraySelfTaxProfilePriceStream)
    (F : LeraySelfTaxTotalLSCFalsifier S) :
    Nonempty (LeraySelfTaxComponentLSCFalsifier S) := by
  by_cases hself : S.selfTaxLimitPrice < S.prefixSelfTaxPrice F.n
  · exact ⟨self_tax_lsc_falsifier S F.n hself⟩
  · have hself_le : S.prefixSelfTaxPrice F.n ≤ S.selfTaxLimitPrice :=
      le_of_not_gt hself
    by_cases hcross :
        S.crossDefectLimitPrice < S.prefixCrossDefectPrice F.n
    · exact ⟨cross_defect_lsc_falsifier S F.n hcross⟩
    · have hcross_le :
          S.prefixCrossDefectPrice F.n ≤ S.crossDefectLimitPrice :=
        le_of_not_gt hcross
      by_cases hcoherence :
          S.coherenceLimitPrice < S.prefixCoherencePrice F.n
      · exact ⟨coherence_lsc_falsifier S F.n hcoherence⟩
      · have hcoherence_le :
            S.prefixCoherencePrice F.n ≤ S.coherenceLimitPrice :=
          le_of_not_gt hcoherence
        have hprefix_le_limit :
            leraySelfTaxPrefixPrice S F.n ≤ leraySelfTaxLimitPrice S := by
          unfold leraySelfTaxPrefixPrice leraySelfTaxLimitPrice
          linarith
        exact False.elim
          (not_lt_of_ge hprefix_le_limit F.limit_total_lt_prefix_total)

/-- Component LSC excludes an aggregate total-price drop. -/
theorem no_total_lsc_falsifier_of_leray_self_tax_component_lsc
    (S : LeraySelfTaxProfilePriceStream)
    (H : LeraySelfTaxComponentLSC S)
    (F : LeraySelfTaxTotalLSCFalsifier S) :
    False :=
  not_lt_of_ge
    (leray_self_tax_prefix_price_lsc S H F.n)
    F.limit_total_lt_prefix_total

/-- Full profile-LSC receipt excludes an aggregate total-price drop. -/
theorem no_total_lsc_falsifier_under_profile_lsc_receipt
    (S : LeraySelfTaxProfilePriceStream)
    (H : LeraySelfTaxProfileLSCReceipt S)
    (F : LeraySelfTaxTotalLSCFalsifier S) :
    False :=
  no_total_lsc_falsifier_of_leray_self_tax_component_lsc
    S (component_lsc_of_profile_lsc_receipt S H) F

/-- Component limit-passage receipt excludes an aggregate total-price LSC drop
through its explicit component LSC fields. -/
theorem no_total_lsc_falsifier_under_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxComponentLimitPassageReceipt S)
    (F : LeraySelfTaxTotalLSCFalsifier S) :
    False :=
  no_total_lsc_falsifier_of_leray_self_tax_component_lsc
    S (component_lsc_of_component_limit_passage S R) F

/-- Output-derived component-limit passage excludes an aggregate total-price
LSC drop through the same explicit component fields. -/
theorem no_total_lsc_falsifier_under_output_derived_component_limit_passage
    (S : LeraySelfTaxProfilePriceStream)
    (R : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (F : LeraySelfTaxTotalLSCFalsifier S) :
    False :=
  no_total_lsc_falsifier_under_component_limit_passage
    S (component_limit_passage_of_output_derived S R) F

/-- Total-price view of the same falsifier through the generic Boss Fight 3
adapter: if the component drop makes a prefix total price exceed the declared
limit total price, the generic profile LSC certificate is impossible. -/
theorem no_generic_profile_lsc_certificate_of_total_self_tax_price_drop
    (S : LeraySelfTaxProfilePriceStream)
    (n : ℕ)
    (hdrop : leraySelfTaxLimitPrice S < leraySelfTaxPrefixPrice S n) :
    ¬ ProfileLimitLSCCertificate (profileLimitStreamOfLeraySelfTax S) :=
  no_profile_lsc_certificate_of_prefix_price_drop
    (profileLimitStreamOfLeraySelfTax S)
    n
    hdrop

/-- Component-coordinate receipt connecting a Leray self-tax/profile stream to
one branch block at the threshold root.

This is the exact algebraic bridge needed after the self-tax LSC receipt proves
limit no-arbitrage.  It deliberately avoids a naked
`limitPrice ≤ survivalDefect(root)` field: the hard coordinatization content is
the component-level root pricing of payoff, self-tax, cross-defect, and
coherence under the same predeclared threshold coordinate. -/
structure BranchSelfTaxThresholdCoordinateReceipt
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream) where
  coordinates_declared_before_payoff :
    S.profileTopologyDeclaredBeforePayoff
  threshold_root_uses_same_ledger :
    S.limitComponentPricesDeclaredBeforePayoff
  above_wall_payoff_floor :
    sharpTarget < B.gamma → 1 ≤ S.payoffLimit
  self_tax_limit_price_le_root_component :
    ∀ _hgamma : sharpTarget < B.gamma,
      S.selfTaxLimitPrice ≤
        B.selfTax *
          (Real.sqrt (sharpTarget / B.gamma)) ^ (4 : Nat)
  cross_defect_limit_price_le_root_component :
    ∀ _hgamma : sharpTarget < B.gamma,
      S.crossDefectLimitPrice ≤
        2 * B.cross *
          (Real.sqrt (sharpTarget / B.gamma)) ^ (3 : Nat)
  coherence_limit_price_le_root_component :
    ∀ _hgamma : sharpTarget < B.gamma,
      S.coherenceLimitPrice ≤
        (Real.sqrt (sharpTarget / B.gamma)) ^ (2 : Nat)

/-- Exact identity-level version of the branch threshold coordinate receipt.

This is the non-tautological target for an analytic/coordinatization proof:
the stream payoff and its three declared limit components must be the exact
threshold-root quartic ledger for the same block, fixed before payoff scoring.
Once these identities are supplied, the weaker coordinate receipt is purely
mechanical. -/
structure BranchSelfTaxThresholdCoordinateIdentities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream) where
  coordinates_declared_before_payoff :
    S.profileTopologyDeclaredBeforePayoff
  threshold_root_uses_same_ledger :
    S.limitComponentPricesDeclaredBeforePayoff
  payoff_limit_eq_one :
    sharpTarget < B.gamma → S.payoffLimit = 1
  self_tax_limit_price_eq :
    ∀ _hgamma : sharpTarget < B.gamma,
      S.selfTaxLimitPrice =
        B.selfTax *
          (Real.sqrt (sharpTarget / B.gamma)) ^ (4 : Nat)
  cross_defect_limit_price_eq :
    ∀ _hgamma : sharpTarget < B.gamma,
      S.crossDefectLimitPrice =
        2 * B.cross *
          (Real.sqrt (sharpTarget / B.gamma)) ^ (3 : Nat)
  coherence_limit_price_eq :
    ∀ _hgamma : sharpTarget < B.gamma,
      S.coherenceLimitPrice =
        (Real.sqrt (sharpTarget / B.gamma)) ^ (2 : Nat)

/-- Which fixed-coordinate guard failed for the threshold-root handoff. -/
inductive BranchSelfTaxThresholdCoordinateGuardBranch where
  | coordinates
  | sameLedger
deriving DecidableEq, Repr

/-- Falsifier for a threshold-root identity package whose coordinate system was
not predeclared or whose threshold root is not the same branch ledger. -/
structure BranchSelfTaxThresholdCoordinateGuardFalsifier
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S) where
  branch : BranchSelfTaxThresholdCoordinateGuardBranch
  missing :
    match branch with
    | BranchSelfTaxThresholdCoordinateGuardBranch.coordinates =>
        ¬ S.profileTopologyDeclaredBeforePayoff
    | BranchSelfTaxThresholdCoordinateGuardBranch.sameLedger =>
        ¬ S.limitComponentPricesDeclaredBeforePayoff

/-- Exact threshold-root identities exclude missing fixed-coordinate guards. -/
theorem no_branch_self_tax_threshold_coordinate_guard_falsifier
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (F : BranchSelfTaxThresholdCoordinateGuardFalsifier B S I) :
    False := by
  rcases F with ⟨branch, hmissing⟩
  cases branch with
  | coordinates =>
      exact hmissing I.coordinates_declared_before_payoff
  | sameLedger =>
      exact hmissing I.threshold_root_uses_same_ledger

/-- Which exact threshold-root coordinate identity failed. -/
inductive BranchSelfTaxThresholdCoordinateIdentityComponent where
  | payoff
  | selfTax
  | crossDefect
  | coherence
deriving DecidableEq, Repr

/-- Falsifier for a branch stream that claims the threshold-root coordinate
handoff but does not use the exact same quartic ledger. -/
structure BranchSelfTaxThresholdCoordinateIdentityMismatchFalsifier
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream) where
  above_wall : sharpTarget < B.gamma
  component : BranchSelfTaxThresholdCoordinateIdentityComponent
  mismatch :
    match component with
    | BranchSelfTaxThresholdCoordinateIdentityComponent.payoff =>
        S.payoffLimit ≠ 1
    | BranchSelfTaxThresholdCoordinateIdentityComponent.selfTax =>
        S.selfTaxLimitPrice ≠
          B.selfTax *
            (Real.sqrt (sharpTarget / B.gamma)) ^ (4 : Nat)
    | BranchSelfTaxThresholdCoordinateIdentityComponent.crossDefect =>
        S.crossDefectLimitPrice ≠
          2 * B.cross *
            (Real.sqrt (sharpTarget / B.gamma)) ^ (3 : Nat)
    | BranchSelfTaxThresholdCoordinateIdentityComponent.coherence =>
        S.coherenceLimitPrice ≠
          (Real.sqrt (sharpTarget / B.gamma)) ^ (2 : Nat)

/-- Exact coordinate identities exclude a threshold-root identity mismatch. -/
theorem no_branch_self_tax_threshold_coordinate_identity_mismatch
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (F : BranchSelfTaxThresholdCoordinateIdentityMismatchFalsifier B S) :
    False := by
  rcases F with ⟨habove, component, hmismatch⟩
  cases component with
  | payoff =>
      exact hmismatch (I.payoff_limit_eq_one habove)
  | selfTax =>
      exact hmismatch (I.self_tax_limit_price_eq habove)
  | crossDefect =>
      exact hmismatch (I.cross_defect_limit_price_eq habove)
  | coherence =>
      exact hmismatch (I.coherence_limit_price_eq habove)

/-- The exact threshold-coordinate package exposes the payoff normalization as
a theorem-level edge.

This is not a constructor for the identities.  It makes the analytic
coordinatization burden visible to graph diagnostics and downstream receipts
without weakening the requirement that the identities be supplied
independently. -/
theorem branch_payoff_limit_eq_one_of_threshold_coordinate_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (habove : sharpTarget < B.gamma) :
    S.payoffLimit = 1 :=
  I.payoff_limit_eq_one habove

/-- The exact threshold-coordinate package exposes the self-tax root component
as a theorem-level edge. -/
theorem branch_self_tax_limit_price_eq_root_component_of_threshold_coordinate_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (habove : sharpTarget < B.gamma) :
    S.selfTaxLimitPrice =
      B.selfTax * (Real.sqrt (sharpTarget / B.gamma)) ^ (4 : Nat) :=
  I.self_tax_limit_price_eq habove

/-- The exact threshold-coordinate package exposes the cross-defect root
component as a theorem-level edge. -/
theorem branch_cross_defect_limit_price_eq_root_component_of_threshold_coordinate_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (habove : sharpTarget < B.gamma) :
    S.crossDefectLimitPrice =
      2 * B.cross * (Real.sqrt (sharpTarget / B.gamma)) ^ (3 : Nat) :=
  I.cross_defect_limit_price_eq habove

/-- The exact threshold-coordinate package exposes the coherence root component
as a theorem-level edge. -/
theorem branch_coherence_limit_price_eq_root_component_of_threshold_coordinate_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (habove : sharpTarget < B.gamma) :
    S.coherenceLimitPrice =
      (Real.sqrt (sharpTarget / B.gamma)) ^ (2 : Nat) :=
  I.coherence_limit_price_eq habove

/-- Exact threshold-root component identities combine to the total self-tax
limit price equaling the quartic survival defect at the same root.

This is the algebraic content that the branch handoff consumes after profile
LSC proves limit no-arbitrage.  The theorem deliberately depends on
`BranchSelfTaxThresholdCoordinateIdentities`; it does not construct them. -/
theorem branch_leray_self_tax_limit_price_eq_survival_defect_of_threshold_coordinate_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (habove : sharpTarget < B.gamma) :
    leraySelfTaxLimitPrice S =
      survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) := by
  unfold leraySelfTaxLimitPrice survivalDefect
  rw [I.self_tax_limit_price_eq habove,
    I.cross_defect_limit_price_eq habove,
    I.coherence_limit_price_eq habove]
  ring

/-- The exact coordinate identities plus the component limit-passage receipt
are exactly enough to force the root survival defect above one.

This isolates the live analytic burden: the coordinate identities alone merely
name the threshold-root ledger; the component limit-passage receipt is the
non-tautological no-arbitrage input that turns those coordinates into a
positive root defect. -/
theorem threshold_root_defect_ge_one_of_component_limit_passage_and_threshold_coordinate_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (C : LeraySelfTaxComponentLimitPassageReceipt S)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (habove : sharpTarget < B.gamma) :
    1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) := by
  have hlimit : S.payoffLimit ≤ leraySelfTaxLimitPrice S :=
    no_global_self_tax_arbitrage_of_component_limit_passage S C
  have hpay : S.payoffLimit = 1 := I.payoff_limit_eq_one habove
  have hprice :
      leraySelfTaxLimitPrice S =
        survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) :=
    branch_leray_self_tax_limit_price_eq_survival_defect_of_threshold_coordinate_identities
      B S I habove
  calc
    1 = S.payoffLimit := hpay.symm
    _ ≤ leraySelfTaxLimitPrice S := hlimit
    _ = survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) := hprice

/-- Output-derived component-limit-passage version of the threshold-root
handoff.

This keeps the audited Leray-output provenance attached until the exact point
where the older component-limit-passage API is needed.  It blocks a proof from
using scalar threshold coordinates while bypassing the output-derived
component LSC route. -/
theorem threshold_root_defect_ge_one_of_output_derived_and_threshold_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (P : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (habove : sharpTarget < B.gamma) :
    1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) :=
  threshold_root_defect_ge_one_of_component_limit_passage_and_threshold_coordinate_identities
    B S (component_limit_passage_of_output_derived S P) I habove

/-- Audited-source version of the threshold-root handoff. -/
theorem threshold_root_defect_ge_one_of_audited_output_source_and_threshold_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (P : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (habove : sharpTarget < B.gamma) :
    1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) :=
  threshold_root_defect_ge_one_of_output_derived_and_threshold_identities
    B S
    (output_derived_component_limit_passage_of_audited_output_limit_source S P)
    I
    habove

/-- Aggregate profile-LSC version of the threshold-root handoff.

This is the interface consumed by the older GP216 spine.  The proof is
intentionally parallel to the component-limit-passage form so the graph has
both load-bearing edges: the compact receipt edge and the sharper PDE/topology
component edge. -/
theorem threshold_root_defect_ge_one_of_profile_lsc_receipt_and_threshold_coordinate_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (H : LeraySelfTaxProfileLSCReceipt S)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S)
    (habove : sharpTarget < B.gamma) :
    1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) := by
  have hlimit : S.payoffLimit ≤ leraySelfTaxLimitPrice S :=
    no_global_self_tax_arbitrage_of_profile_lsc_receipt S H
  have hpay : S.payoffLimit = 1 := I.payoff_limit_eq_one habove
  have hprice :
      leraySelfTaxLimitPrice S =
        survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) :=
    branch_leray_self_tax_limit_price_eq_survival_defect_of_threshold_coordinate_identities
      B S I habove
  calc
    1 = S.payoffLimit := hpay.symm
    _ ≤ leraySelfTaxLimitPrice S := hlimit
    _ = survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) := hprice

/-- Counterexample block showing that coordinate identities alone are not a
proof of threshold defect.  The block is global and above the `2/3` wall, but
has no self-tax/cross charge, so the threshold root defect is only `2/3`. -/
def thresholdCoordinateIdentityOnlyCounterexampleBlock : FullLedgerBlock where
  scope := LedgerScope.globalAdmissibleField
  gamma := 1
  cross := 0
  selfTax := 0
  survivalProfit := 0

/-- Scalar stream matching the counterexample block's threshold-root
coordinates.  It intentionally supplies no no-arbitrage/LSC receipt. -/
def thresholdCoordinateIdentityOnlyCounterexampleStream :
    LeraySelfTaxProfilePriceStream where
  prefixPayoff := fun _ => 1
  prefixSelfTaxPrice := fun _ => 0
  prefixCrossDefectPrice := fun _ => 0
  prefixCoherencePrice := fun _ => sharpTarget
  payoffLimit := 1
  selfTaxLimitPrice := 0
  crossDefectLimitPrice := 0
  coherenceLimitPrice := sharpTarget
  profileTopologyDeclaredBeforePayoff := True
  profileStreamDeclaredBeforePayoff := True
  prefixComponentPricesDeclaredBeforePayoff := True
  limitComponentPricesDeclaredBeforePayoff := True
  noPosthocPayoffDependentStreamChoice := True

/-- The counterexample stream does satisfy the exact threshold-root coordinate
identities for the counterexample block. -/
def thresholdCoordinateIdentityOnlyCounterexampleIdentities :
    BranchSelfTaxThresholdCoordinateIdentities
      thresholdCoordinateIdentityOnlyCounterexampleBlock
      thresholdCoordinateIdentityOnlyCounterexampleStream where
  coordinates_declared_before_payoff := trivial
  threshold_root_uses_same_ledger := trivial
  payoff_limit_eq_one := by
    intro _habove
    rfl
  self_tax_limit_price_eq := by
    intro _habove
    norm_num [thresholdCoordinateIdentityOnlyCounterexampleBlock,
      thresholdCoordinateIdentityOnlyCounterexampleStream]
  cross_defect_limit_price_eq := by
    intro _habove
    norm_num [thresholdCoordinateIdentityOnlyCounterexampleBlock,
      thresholdCoordinateIdentityOnlyCounterexampleStream]
  coherence_limit_price_eq := by
    intro _habove
    have hnonneg : 0 ≤ sharpTarget := by
      norm_num [sharpTarget]
    simpa [thresholdCoordinateIdentityOnlyCounterexampleBlock,
      thresholdCoordinateIdentityOnlyCounterexampleStream] using
        (Real.sq_sqrt hnonneg).symm

/-- Anti-tautology guard: exact threshold-root coordinate identities by
themselves do not imply the root defect.  Any closure using the identity
package must also provide the no-arbitrage/LSC limit-passage receipt. -/
theorem not_threshold_coordinate_identities_alone_imply_root_defect :
    ¬ (∀ B : FullLedgerBlock,
        ∀ S : LeraySelfTaxProfilePriceStream,
          BranchSelfTaxThresholdCoordinateIdentities B S →
            sharpTarget < B.gamma →
              1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma))) := by
  intro h
  have habove :
      sharpTarget < thresholdCoordinateIdentityOnlyCounterexampleBlock.gamma := by
    norm_num [thresholdCoordinateIdentityOnlyCounterexampleBlock, sharpTarget]
  have hdefect :=
    h thresholdCoordinateIdentityOnlyCounterexampleBlock
      thresholdCoordinateIdentityOnlyCounterexampleStream
      thresholdCoordinateIdentityOnlyCounterexampleIdentities
      habove
  have hroot :
      survivalDefect thresholdCoordinateIdentityOnlyCounterexampleBlock
          (Real.sqrt
            (sharpTarget / thresholdCoordinateIdentityOnlyCounterexampleBlock.gamma)) =
        sharpTarget := by
    have hnonneg : 0 ≤ sharpTarget := by
      norm_num [sharpTarget]
    simpa [survivalDefect, thresholdCoordinateIdentityOnlyCounterexampleBlock] using
      Real.sq_sqrt hnonneg
  rw [hroot] at hdefect
  norm_num [sharpTarget] at hdefect

/-- The coordinate-identity counterexample cannot carry the aggregate
profile-LSC receipt either.  This keeps the older compact interface honest:
if a closure attempt works only by naming the threshold coordinates while
omitting profile LSC, the missing premise is mechanically exposed. -/
theorem not_profile_lsc_receipt_for_threshold_identity_counterexample :
    LeraySelfTaxProfileLSCReceipt
        thresholdCoordinateIdentityOnlyCounterexampleStream → False := by
  intro H
  have hlimit :
      thresholdCoordinateIdentityOnlyCounterexampleStream.payoffLimit ≤
        leraySelfTaxLimitPrice thresholdCoordinateIdentityOnlyCounterexampleStream :=
    no_global_self_tax_arbitrage_of_profile_lsc_receipt
      thresholdCoordinateIdentityOnlyCounterexampleStream H
  norm_num [thresholdCoordinateIdentityOnlyCounterexampleStream,
    leraySelfTaxLimitPrice, sharpTarget] at hlimit

/-- The same counterexample cannot carry the component limit-passage receipt:
component LSC plus finite-prefix no-arbitrage would imply the missing
`1 ≤ 2/3` root-defect inequality.  This pins the remaining hard work on the
actual no-arbitrage/LSC PDE receipt, not on the coordinate package. -/
theorem not_component_limit_passage_receipt_for_threshold_identity_counterexample :
    LeraySelfTaxComponentLimitPassageReceipt
        thresholdCoordinateIdentityOnlyCounterexampleStream → False := by
  intro C
  have hlimit :
      thresholdCoordinateIdentityOnlyCounterexampleStream.payoffLimit ≤
        leraySelfTaxLimitPrice thresholdCoordinateIdentityOnlyCounterexampleStream :=
    no_global_self_tax_arbitrage_of_component_limit_passage
      thresholdCoordinateIdentityOnlyCounterexampleStream C
  norm_num [thresholdCoordinateIdentityOnlyCounterexampleStream,
    leraySelfTaxLimitPrice, sharpTarget] at hlimit

/-- Exact threshold-root identities instantiate the weaker branch coordinate
receipt consumed by the self-tax no-arbitrage bridge. -/
def branch_self_tax_threshold_coordinate_receipt_of_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S) :
    BranchSelfTaxThresholdCoordinateReceipt B S where
  coordinates_declared_before_payoff := I.coordinates_declared_before_payoff
  threshold_root_uses_same_ledger := I.threshold_root_uses_same_ledger
  above_wall_payoff_floor := by
    intro hgamma
    rw [I.payoff_limit_eq_one hgamma]
  self_tax_limit_price_le_root_component := by
    intro hgamma
    exact le_of_eq (I.self_tax_limit_price_eq hgamma)
  cross_defect_limit_price_le_root_component := by
    intro hgamma
    exact le_of_eq (I.cross_defect_limit_price_eq hgamma)
  coherence_limit_price_le_root_component := by
    intro hgamma
    exact le_of_eq (I.coherence_limit_price_eq hgamma)

/-- Component root bounds imply the total threshold-root price bound. -/
theorem limit_price_le_threshold_defect_of_branch_self_tax_components
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (R : BranchSelfTaxThresholdCoordinateReceipt B S)
    (hgamma : sharpTarget < B.gamma) :
    leraySelfTaxLimitPrice S ≤
      survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) := by
  have hself := R.self_tax_limit_price_le_root_component hgamma
  have hcross := R.cross_defect_limit_price_le_root_component hgamma
  have hcoherence := R.coherence_limit_price_le_root_component hgamma
  unfold leraySelfTaxLimitPrice survivalDefect
  linarith

/-- Self-tax limit no-arbitrage plus the threshold-coordinate receipt implies
Track B threshold-defect convexity for the branch block. -/
theorem threshold_defect_of_branch_self_tax_threshold_coordinate_receipt
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (R : BranchSelfTaxThresholdCoordinateReceipt B S)
    (hlimit : S.payoffLimit ≤ leraySelfTaxLimitPrice S) :
    ThresholdDefectConvexity B := by
  by_cases hle : B.gamma ≤ sharpTarget
  · exact Or.inl hle
  · have hgt : sharpTarget < B.gamma := lt_of_not_ge hle
    have hfloor : 1 ≤ S.payoffLimit := R.above_wall_payoff_floor hgt
    have hdefect :
        1 ≤ survivalDefect B (Real.sqrt (sharpTarget / B.gamma)) :=
      hfloor.trans
        (hlimit.trans
          (limit_price_le_threshold_defect_of_branch_self_tax_components
            B S R hgt))
    exact Or.inr ⟨hgt, hdefect⟩

/-- Endpoint-preserving threshold-defect adapter for the output-derived
self-tax source.

This extracts the reusable core of the GP216 branch theorem: output-derived
component limit passage plus exact threshold-coordinate identities imply
`ThresholdDefectConvexity`, while preserving the upstream Track B endpoint
guard route. -/
theorem threshold_defect_of_leray_self_tax_output_derived_endpoint_and_threshold_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (P : LeraySelfTaxOutputDerivedComponentLimitPassageReceipt S)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S) :
    ThresholdDefectConvexity B := by
  let E := trackB_self_tax_limit_endpoint_of_leray_stream S
  let R := trackB_self_tax_endpoint_limit_passage_of_output_derived S P
  exact
    threshold_defect_of_trackb_self_tax_endpoint_limit_passage
      E
      R
      B
      (fun hsource hlimit => by
        have hstream : S.payoffLimit ≤ leraySelfTaxLimitPrice S := by
          simpa [E, trackB_self_tax_limit_endpoint_of_leray_stream]
            using hlimit
        have htopology : S.profileTopologyDeclaredBeforePayoff := by
          simpa [E, trackB_self_tax_limit_endpoint_of_leray_stream]
            using hsource.1
        have hlimitPrices : S.limitComponentPricesDeclaredBeforePayoff := by
          simpa [E, trackB_self_tax_limit_endpoint_of_leray_stream]
            using hsource.2.2.2.1
        exact
          threshold_defect_of_branch_self_tax_threshold_coordinate_receipt
            B
            S
            { coordinates_declared_before_payoff := htopology
              threshold_root_uses_same_ledger := hlimitPrices
              above_wall_payoff_floor := by
                intro hgamma
                rw [I.payoff_limit_eq_one hgamma]
              self_tax_limit_price_le_root_component := by
                intro hgamma
                exact le_of_eq (I.self_tax_limit_price_eq hgamma)
              cross_defect_limit_price_le_root_component := by
                intro hgamma
                exact le_of_eq (I.cross_defect_limit_price_eq hgamma)
              coherence_limit_price_le_root_component := by
                intro hgamma
                exact le_of_eq (I.coherence_limit_price_eq hgamma) }
            hstream)

/-- Audited-source version of the threshold-defect handoff.

This is the closure-facing route from the defect-inclusive audited
Leray-output source to the branch threshold-defect statement. -/
theorem threshold_defect_of_leray_self_tax_audited_output_source_and_threshold_identities
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (P : LeraySelfTaxOutputLimitPassageAuditedSourceReceipt S)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S) :
    ThresholdDefectConvexity B :=
  threshold_defect_of_leray_self_tax_output_derived_endpoint_and_threshold_identities
    B S
    (output_derived_component_limit_passage_of_audited_output_limit_source S P)
    I

/-- Direct measure-valued source handoff to branch threshold defect.

This is the one-hop GP216-facing form of the Young/defect-carrier route: the
PDE instantiation supplies the measure-valued output source, finite-prefix
assembly, payoff convergence, and a noncircular convergence source; the branch
only supplies the coordinate identities tying that same Leray stream to the
threshold components. -/
theorem threshold_defect_of_leray_self_tax_measure_valued_source_and_tendsto_prefix_payoff
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (C : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hpayoff :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (noncircular_output_convergence_source : Prop)
    (hnoncirc : noncircular_output_convergence_source)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S) :
    ThresholdDefectConvexity B :=
  threshold_defect_of_leray_self_tax_audited_output_source_and_threshold_identities
    B S
      (audited_output_limit_passage_source_of_measure_valued_source_and_tendsto_prefix_payoff
        S A C hpayoff M noncircular_output_convergence_source hnoncirc)
      I

/-- Noncircular measure-valued source handoff to branch threshold defect.

This is the preferred source route: the noncircular convergence guard is paid
by the same measure-valued output object that supplies the relaxed defect
prices. -/
theorem threshold_defect_of_leray_self_tax_mv_tendsto_noncircular
    (B : FullLedgerBlock)
    (S : LeraySelfTaxProfilePriceStream)
    (A : LeraySelfTaxPrefixLocalToGlobalComponentAssembly S)
    (C : ∀ n : ℕ, LeraySelfTaxFinitePrefixChargeReceipt S A n)
    (hpayoff :
      Filter.Tendsto S.prefixPayoff Filter.atTop
        (nhds S.payoffLimit))
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (N : LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt S M)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S) :
    ThresholdDefectConvexity B :=
  threshold_defect_of_leray_self_tax_audited_output_source_and_threshold_identities
    B S
    (audited_mv_tendsto_output_source_noncircular
      S A C hpayoff M N)
    I

/-- Direct measure-valued source handoff from a Cauchy/subsequence payoff
limit to branch threshold defect.

This is the diagonal version of
`threshold_defect_of_leray_self_tax_measure_valued_source_and_tendsto_prefix_payoff`.
It keeps the branch coordinate identities unchanged while allowing the PDE
limit argument to arrive through compactness plus subsequential convergence.
-/
theorem threshold_defect_of_leray_self_tax_measure_valued_source_and_cauchySeq_subseq_prefix_payoff
    (B : FullLedgerBlock)
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
    (hnoncirc : noncircular_output_convergence_source)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S) :
    ThresholdDefectConvexity B :=
    threshold_defect_of_leray_self_tax_audited_output_source_and_threshold_identities
      B S
      (audited_output_limit_source_of_measure_valued_cauchy_subseq
        S A C hcauchy hφ hsub M noncircular_output_convergence_source hnoncirc)
      I

/-- Diagonal compactness version of the noncircular measure-valued handoff. -/
theorem threshold_defect_of_leray_self_tax_mv_cauchy_subseq_noncircular
    (B : FullLedgerBlock)
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
    (N : LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt S M)
    (I : BranchSelfTaxThresholdCoordinateIdentities B S) :
    ThresholdDefectConvexity B :=
  threshold_defect_of_leray_self_tax_audited_output_source_and_threshold_identities
    B S
    (audited_mv_cauchy_subseq_output_source_noncircular
      S A C hcauchy hφ hsub M N)
    I

/-- Bundled noncircular measure-valued source handoff to branch threshold
defect.

This is the concrete one-object instantiation path for
`LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource`: once the PDE
side has built the bundled source for a stream, the only remaining branch input
is the exact threshold-coordinate identity for that same stream. -/
theorem threshold_defect_of_leray_self_tax_noncircular_mv_stream_source_and_threshold_identities
    (B : FullLedgerBlock)
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource)
    (I : BranchSelfTaxThresholdCoordinateIdentities B Q.stream) :
    ThresholdDefectConvexity B :=
  threshold_defect_of_leray_self_tax_output_derived_endpoint_and_threshold_identities
    B
    Q.stream
    (output_derived_component_limit_passage_of_noncircular_mv_stream_source Q)
    I

/-- A bundled noncircular measure-valued self-tax source plus a charged
quartic amplitude projection exposes the gain-at-amplitude cap for the same
branch.

This is intentionally not a global `∀ U n` amplitude cap.  The cap is paid by
the audited Young/defect self-tax stream, the same-block threshold-coordinate
identities, and the supplied amplitude projection for that branch. -/
theorem gain_at_amp_le_target_of_leray_self_tax_noncircular_mv_stream_source
    (B : FullLedgerBlock)
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource)
    (I : BranchSelfTaxThresholdCoordinateIdentities B Q.stream)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) :
    B.gamma * R.ampSq ≤ sharpTarget :=
  gain_at_amp_le_target_of_quartic_survival_amplitude_projection
    B
    R
    (threshold_defect_of_leray_self_tax_noncircular_mv_stream_source_and_threshold_identities
      B Q I)

/-- Source-preserving no-survivor handoff for a single bundled noncircular
measure-valued self-tax stream source. -/
theorem no_global_survivor_of_leray_self_tax_noncircular_mv_stream_source
    (B : FullLedgerBlock)
    (Q : LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource)
    (I : BranchSelfTaxThresholdCoordinateIdentities B Q.stream)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_amplitude_projection
    B
    R
    (threshold_defect_of_leray_self_tax_noncircular_mv_stream_source_and_threshold_identities
      B Q I)

/-- Continuum all-output LP/Bony source handoff to branch threshold defect.

This is the direct route from the audited all-output source into the Track B
threshold endpoint.  The PDE side supplies the fixed continuum source and
component limit-passage package; the branch side supplies only the exact
threshold-coordinate identities for the projected Leray self-tax stream. -/
theorem threshold_defect_of_continuum_all_output_self_tax_source_and_threshold_identities
    {τ : ContinuumLPProfileTopology.{u}}
    (B : FullLedgerBlock)
    (source : ContinuumAllOutputLPBonySource τ)
    (P : LeraySelfTaxContinuumComponentLimitPassageSource source)
    (I :
      BranchSelfTaxThresholdCoordinateIdentities B
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          source P.split)) :
    ThresholdDefectConvexity B :=
  threshold_defect_of_branch_self_tax_threshold_coordinate_receipt
    B
    (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource source P.split)
    (branch_self_tax_threshold_coordinate_receipt_of_identities
      B
      (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource source P.split)
      I)
    (no_global_self_tax_arbitrage_of_continuum_all_output_source source P)

/-- Continuum all-output source plus a charged amplitude projection exposes the
branch gain-at-amplitude cap. -/
theorem gain_at_amp_le_target_of_continuum_all_output_self_tax_source
    {τ : ContinuumLPProfileTopology.{u}}
    (B : FullLedgerBlock)
    (source : ContinuumAllOutputLPBonySource τ)
    (P : LeraySelfTaxContinuumComponentLimitPassageSource source)
    (I :
      BranchSelfTaxThresholdCoordinateIdentities B
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          source P.split))
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) :
    B.gamma * R.ampSq ≤ sharpTarget :=
  gain_at_amp_le_target_of_quartic_survival_amplitude_projection
    B
    R
    (threshold_defect_of_continuum_all_output_self_tax_source_and_threshold_identities
      B source P I)

/-- Source-preserving no-survivor handoff for a continuum all-output self-tax
source. -/
theorem no_global_survivor_of_continuum_all_output_self_tax_source
    {τ : ContinuumLPProfileTopology.{u}}
    (B : FullLedgerBlock)
    (source : ContinuumAllOutputLPBonySource τ)
    (P : LeraySelfTaxContinuumComponentLimitPassageSource source)
    (I :
      BranchSelfTaxThresholdCoordinateIdentities B
        (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          source P.split))
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_amplitude_projection
    B
    R
    (threshold_defect_of_continuum_all_output_self_tax_source_and_threshold_identities
      B source P I)

/-- A block-level bridge exposing the remaining PDE obligation: build the fixed
Leray self-tax/profile stream, supply the core_04-backed LSC receipt, and show
that limit no-arbitrage feeds the existing Track B threshold-defect ledger. -/
structure LeraySelfTaxProfileLSCBridge where
  stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream
  receipt_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        LeraySelfTaxProfileLSCReceipt (stream_of_block B)
  threshold_coordinate_receipt_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        BranchSelfTaxThresholdCoordinateIdentities B (stream_of_block B)

/-- Component-limit-passage version of the block-level bridge.

This is the sharper ZTARE/local target surfaced by the constraint-basin graph:
instantiate the component local-to-global assembly, component LSC, tail payoff
visibility, and fixed-topology guards directly, then the aggregate
profile-LSC receipt is only a mechanical adapter. -/
structure LeraySelfTaxProfileComponentLimitBridge where
  stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream
  component_limit_passage_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        LeraySelfTaxComponentLimitPassageReceipt (stream_of_block B)
  threshold_coordinate_receipt_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        BranchSelfTaxThresholdCoordinateIdentities B (stream_of_block B)

/-- Source-derived component-limit bridge.

This is the same block-level handoff as
`LeraySelfTaxProfileComponentLimitBridge`, but it requires the component-limit
receipt to carry explicit audited-output scalar-stream provenance.  The older
component-limit bridge remains the legacy API boundary; this structure is the
non-posthoc spine for endpoints that need source/substitution falsifiers. -/
structure LeraySelfTaxProfileOutputDerivedComponentLimitBridge where
  stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream
  output_derived_component_limit_passage_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        LeraySelfTaxOutputDerivedComponentLimitPassageReceipt
          (stream_of_block B)
  threshold_coordinate_receipt_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        BranchSelfTaxThresholdCoordinateIdentities B (stream_of_block B)

/-- Block-family source built from concrete noncircular measure-valued stream
sources.

This is closer to the NSE/profile instantiation surface than the older
output-derived bridge: for each global block it asks for the bundled
measure-valued stream source itself, plus an identity that it is the stream
assigned to that block.  The output-derived component-limit bridge is then
only a projection. -/
structure LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource where
  stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream
  noncircular_mv_stream_source_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamSource
  noncircular_mv_stream_source_matches_block :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      (noncircular_mv_stream_source_of_global B hglobal).stream =
        stream_of_block B
  threshold_coordinate_receipt_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        BranchSelfTaxThresholdCoordinateIdentities B (stream_of_block B)

/-- Family-level compactness-provenance measure-valued source.

This is narrower than a final GP216 receipt and stronger than a bare
measure-valued source.  It says the profile-family stream for each global block
has a compactness-provenance Young/defect output-limit source. -/
structure LeraySelfTaxCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream) where
  compactness_mv_source_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource
          (stream_of_block B)

/-- Atomic family-level split of the compactness-provenance source.

This is intentionally not a stronger theorem.  It is a proof-search interface:
the remaining analytic source decomposes into a measure-valued output-limit
source and a provenance source for exactly that output-limit source.  Keeping
the two fields separate prevents a future endpoint from treating the bundled
family source as a single opaque receipt. -/
structure LeraySelfTaxAtomicCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream) where
  measure_valued_source_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        LeraySelfTaxMeasureValuedOutputLimitSource
          (stream_of_block B)
  compactness_provenance_of_global :
    ∀ B : FullLedgerBlock,
      (hglobal : IsGlobalTrackBBlock B) →
        LeraySelfTaxMeasureValuedOutputCompactnessProvenance
          (stream_of_block B)
          (measure_valued_source_of_global B hglobal)

/-- Bundle the atomic family source into the compactness-provenance source.

This adapter has zero source credit.  It exists so that the closure graph and
typed endpoint tooling can target the two analytic debts independently. -/
def LeraySelfTaxAtomicCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource.toFamilySource
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (A :
      LeraySelfTaxAtomicCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource
        stream_of_block) :
    LeraySelfTaxCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource
      stream_of_block where
  compactness_mv_source_of_global := by
    intro B hglobal
    exact
      { measure_valued_output_limit :=
          A.measure_valued_source_of_global B hglobal
        compactness_provenance :=
          A.compactness_provenance_of_global B hglobal }

/-- Family-level compactness source assembled from its two atomic analytic
pieces.

This constructor is intentionally only packaging.  It exposes the real
residual split: the PDE side must produce both the measure-valued output source
and the compactness provenance tying that source to an approximation family. -/
def LeraySelfTaxCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource.ofMeasureValuedSourcesAndProvenance
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (measure_valued_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxMeasureValuedOutputLimitSource
            (stream_of_block B))
    (compactness_provenance_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          LeraySelfTaxMeasureValuedOutputCompactnessProvenance
            (stream_of_block B)
            (measure_valued_source_of_global B hglobal)) :
    LeraySelfTaxCompactnessProvenanceMeasureValuedProfilePriceStreamFamilySource
      stream_of_block where
  compactness_mv_source_of_global := by
    intro B hglobal
    exact
      { measure_valued_output_limit :=
          measure_valued_source_of_global B hglobal
        compactness_provenance :=
          compactness_provenance_of_global B hglobal }

/-- Source object for noncircular measure-valued profile-family scalar
alignment.

This is the Young/defect analogue of
`ContinuumProfileFamilyScalarAlignmentSource`: it packages the genuine profile
membership witness and the two scalar equalities tying the fixed profile family
to the same noncircular self-tax stream.  It deliberately does not construct
those equalities by definition; the PDE/profile side must supply them. -/
structure NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource) where
  profile_family_and_stream_declared_together :
    ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop
  profile_family_and_stream_declared_together_paid :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      profile_family_and_stream_declared_together B hglobal
  profile_mem_of_global :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
      ∃ P : PricingProfile, P ∈ (profile_family_of_block B).profiles
  family_payoff_matches_stream :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      familyPayoff (profile_family_of_block B) =
        (source.stream_of_block B).payoffLimit
  family_price_matches_stream :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      familyPrice (profile_family_of_block B) =
        leraySelfTaxLimitPrice (source.stream_of_block B)

/-- Build a noncircular measure-valued stream-family source from one
Tendsto-backed bundled source per global block.

This is the one-object family constructor matching
`noncircular_mv_profile_price_stream_source_of_tendsto`; callers provide the
local-to-global assembly, finite-prefix charge, payoff convergence,
measure-valued output source, and noncircular convergence receipt for each
global block. -/
def leray_self_tax_noncircular_mv_stream_family_source_of_tendsto
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (assembly_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxPrefixLocalToGlobalComponentAssembly
            (stream_of_block B))
    (finite_prefix_charge_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          ∀ n : ℕ,
            LeraySelfTaxFinitePrefixChargeReceipt
              (stream_of_block B)
              (assembly_of_global B hglobal)
              n)
    (prefix_payoff_tendsto_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          Filter.Tendsto (stream_of_block B).prefixPayoff Filter.atTop
            (nhds (stream_of_block B).payoffLimit))
    (measure_valued_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxMeasureValuedOutputLimitSource
            (stream_of_block B))
    (noncircular_output_convergence_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt
            (stream_of_block B)
            (measure_valued_source_of_global B hglobal))
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource where
  stream_of_block := stream_of_block
  noncircular_mv_stream_source_of_global := by
    intro B hglobal
    exact
      noncircular_mv_profile_price_stream_source_of_tendsto
        (stream_of_block B)
        (assembly_of_global B hglobal)
        (finite_prefix_charge_of_global B hglobal)
        (prefix_payoff_tendsto_of_global B hglobal)
        (measure_valued_source_of_global B hglobal)
        (noncircular_output_convergence_of_global B hglobal)
  noncircular_mv_stream_source_matches_block := by
    intro _B _hglobal
    rfl
  threshold_coordinate_receipt_of_global :=
    threshold_coordinate_receipt_of_global

/-- Tendsto-backed noncircular measure-valued stream-family source where
noncircular convergence is projected from the same measure-valued source.

This removes a duplicated caller burden: `LeraySelfTaxMeasureValuedOutputLimitSource`
already carries the topology and defect guards needed by
`LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt`. -/
def leray_self_tax_noncircular_mv_stream_family_source_of_tendsto_measure_valued_sources
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (assembly_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxPrefixLocalToGlobalComponentAssembly
            (stream_of_block B))
    (finite_prefix_charge_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          ∀ n : ℕ,
            LeraySelfTaxFinitePrefixChargeReceipt
              (stream_of_block B)
              (assembly_of_global B hglobal)
              n)
    (prefix_payoff_tendsto_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          Filter.Tendsto (stream_of_block B).prefixPayoff Filter.atTop
            (nhds (stream_of_block B).payoffLimit))
    (measure_valued_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxMeasureValuedOutputLimitSource
            (stream_of_block B))
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource :=
  leray_self_tax_noncircular_mv_stream_family_source_of_tendsto
    stream_of_block
    assembly_of_global
    finite_prefix_charge_of_global
    prefix_payoff_tendsto_of_global
    measure_valued_source_of_global
    (fun B hglobal =>
      leray_self_tax_noncircular_measure_valued_output_convergence_receipt_of_source
        (stream_of_block B)
        (measure_valued_source_of_global B hglobal))
    threshold_coordinate_receipt_of_global

/-- Diagonal compactness family constructor for the noncircular
measure-valued stream source.

This is the source-level version of the Cauchy/subsequence bridge: each global
block supplies Cauchy payoff-prefix control and one convergent subsequence;
the constructor upgrades that data to the bundled noncircular stream-family
source used by the current Track B endpoint constructors. -/
def leray_self_tax_noncircular_mv_stream_family_source_of_cauchySeq_subseq
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (assembly_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxPrefixLocalToGlobalComponentAssembly
            (stream_of_block B))
    (finite_prefix_charge_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          ∀ n : ℕ,
            LeraySelfTaxFinitePrefixChargeReceipt
              (stream_of_block B)
              (assembly_of_global B hglobal)
              n)
    (prefix_payoff_cauchy_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CauchySeq (stream_of_block B).prefixPayoff)
    (subseq_of_block : FullLedgerBlock → ℕ → ℕ)
    (prefix_payoff_subseq_strictMono_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          StrictMono (subseq_of_block B))
    (prefix_payoff_subseq_tendsto_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          Filter.Tendsto
            (fun k : ℕ =>
              (stream_of_block B).prefixPayoff (subseq_of_block B k))
            Filter.atTop
            (nhds (stream_of_block B).payoffLimit))
    (measure_valued_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxMeasureValuedOutputLimitSource
            (stream_of_block B))
    (noncircular_output_convergence_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          LeraySelfTaxNoncircularMeasureValuedOutputConvergenceReceipt
            (stream_of_block B)
            (measure_valued_source_of_global B hglobal))
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource where
  stream_of_block := stream_of_block
  noncircular_mv_stream_source_of_global := by
    intro B hglobal
    exact
      noncircular_mv_profile_price_stream_source_of_cauchySeq_subseq
        (stream_of_block B)
        (assembly_of_global B hglobal)
        (finite_prefix_charge_of_global B hglobal)
        (prefix_payoff_cauchy_of_global B hglobal)
        (prefix_payoff_subseq_strictMono_of_global B hglobal)
        (prefix_payoff_subseq_tendsto_of_global B hglobal)
        (measure_valued_source_of_global B hglobal)
        (noncircular_output_convergence_of_global B hglobal)
  noncircular_mv_stream_source_matches_block := by
    intro _B _hglobal
    rfl
  threshold_coordinate_receipt_of_global :=
    threshold_coordinate_receipt_of_global

/-- Diagonal compactness version with noncircular convergence projected from
the same measure-valued output source. -/
def leray_self_tax_noncircular_mv_stream_family_source_of_cauchySeq_subseq_measure_valued_sources
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (assembly_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxPrefixLocalToGlobalComponentAssembly
            (stream_of_block B))
    (finite_prefix_charge_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          ∀ n : ℕ,
            LeraySelfTaxFinitePrefixChargeReceipt
              (stream_of_block B)
              (assembly_of_global B hglobal)
              n)
    (prefix_payoff_cauchy_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CauchySeq (stream_of_block B).prefixPayoff)
    (subseq_of_block : FullLedgerBlock → ℕ → ℕ)
    (prefix_payoff_subseq_strictMono_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          StrictMono (subseq_of_block B))
    (prefix_payoff_subseq_tendsto_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          Filter.Tendsto
            (fun k : ℕ =>
              (stream_of_block B).prefixPayoff (subseq_of_block B k))
            Filter.atTop
            (nhds (stream_of_block B).payoffLimit))
    (measure_valued_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxMeasureValuedOutputLimitSource
            (stream_of_block B))
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource :=
  leray_self_tax_noncircular_mv_stream_family_source_of_cauchySeq_subseq
    stream_of_block
    assembly_of_global
    finite_prefix_charge_of_global
    prefix_payoff_cauchy_of_global
    subseq_of_block
    prefix_payoff_subseq_strictMono_of_global
    prefix_payoff_subseq_tendsto_of_global
    measure_valued_source_of_global
    (fun B hglobal =>
      leray_self_tax_noncircular_measure_valued_output_convergence_receipt_of_source
        (stream_of_block B)
        (measure_valued_source_of_global B hglobal))
    threshold_coordinate_receipt_of_global

/-- Build the source-derived block bridge from audited Leray-output sources.

This is the constructor a PDE instantiation should target first: it asks for
the actual audited output-limit passage on every global block, then derives
the output-derived component-limit wrapper mechanically.  The threshold
coordinate identities remain separate because they are a different
same-block endpoint identification, not a consequence of the output topology.
-/
def leray_self_tax_profile_output_derived_component_limit_bridge_of_audited_output_sources
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (audited_output_limit_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxOutputLimitPassageAuditedSourceReceipt
            (stream_of_block B))
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    LeraySelfTaxProfileOutputDerivedComponentLimitBridge where
  stream_of_block := stream_of_block
  output_derived_component_limit_passage_of_global := by
    intro B hglobal
    exact
      output_derived_component_limit_passage_of_audited_output_limit_source
        (stream_of_block B)
        (audited_output_limit_source_of_global B hglobal)
  threshold_coordinate_receipt_of_global :=
    threshold_coordinate_receipt_of_global

/-- Project a concrete noncircular measure-valued stream-family source to the
legacy output-derived component-limit bridge.

No GP216 bridge or raw metadata is used here: the output-derived receipt for
each global block is rebuilt from the bundled measure-valued source attached
to that same block stream. -/
def leray_self_tax_profile_output_derived_bridge_of_noncircular_mv_stream_family_source
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource) :
    LeraySelfTaxProfileOutputDerivedComponentLimitBridge where
  stream_of_block := source.stream_of_block
  output_derived_component_limit_passage_of_global := by
    intro B hglobal
    let Q := source.noncircular_mv_stream_source_of_global B hglobal
    have hQ : Q.stream = source.stream_of_block B :=
      source.noncircular_mv_stream_source_matches_block B hglobal
    simpa [hQ] using
      output_derived_component_limit_passage_of_noncircular_mv_stream_source Q
  threshold_coordinate_receipt_of_global :=
    source.threshold_coordinate_receipt_of_global

/-- Threshold-defect handoff directly from the concrete noncircular
measure-valued stream-family source. -/
theorem threshold_defect_of_leray_self_tax_noncircular_mv_stream_family_source
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ThresholdDefectConvexity B :=
  threshold_defect_of_leray_self_tax_output_derived_endpoint_and_threshold_identities
    B
    (source.stream_of_block B)
    ((leray_self_tax_profile_output_derived_bridge_of_noncircular_mv_stream_family_source
        source).output_derived_component_limit_passage_of_global B hglobal)
    (source.threshold_coordinate_receipt_of_global B hglobal)

/-- A noncircular measure-valued self-tax stream family source plus the
branch's charged quartic amplitude projection exposes the branch
gain-at-amplitude cap. -/
theorem gain_at_amp_le_target_of_leray_self_tax_noncircular_mv_stream_family_source
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) :
    B.gamma * R.ampSq ≤ sharpTarget :=
  gain_at_amp_le_target_of_quartic_survival_amplitude_projection
    B
    R
    (threshold_defect_of_leray_self_tax_noncircular_mv_stream_family_source
      source B hglobal)

/-- Source-preserving no-survivor handoff for a noncircular measure-valued
self-tax stream family source. -/
theorem no_global_survivor_of_leray_self_tax_noncircular_mv_stream_family_source
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_amplitude_projection
    B
    R
    (threshold_defect_of_leray_self_tax_noncircular_mv_stream_family_source
      source B hglobal)

/-- Legacy quartic-projection form of the noncircular measure-valued
self-tax stream-family no-survivor handoff.

New code should prefer the charged-amplitude projection when it is available,
but many existing Track B bridges still expose `QuarticSurvivalProjectionReceipt`.
This theorem keeps the concrete noncircular source visible for that older API
without detouring through an output-derived bridge package. -/
theorem no_global_survivor_of_leray_self_tax_noncircular_mv_stream_family_source_projection
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (R : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_projection
    B
    R
    (threshold_defect_of_leray_self_tax_noncircular_mv_stream_family_source
      source B hglobal)

/-- Block-family source built from continuum all-output LP/Bony sources.

For each global Track B block, the PDE side supplies the audited continuum
all-output source, the Leray self-tax component split/limit-passage package,
and an equality tying the projected Leray stream to the block stream consumed
by profile decomposition.  This is the family-level version of
`LeraySelfTaxContinuumComponentLimitPassageSource`. -/
structure LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource
    (τ : ContinuumLPProfileTopology.{u}) where
  stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream
  all_output_source_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        ContinuumAllOutputLPBonySource τ
  component_source_of_global :
    ∀ B : FullLedgerBlock,
      (hglobal : IsGlobalTrackBBlock B) →
        LeraySelfTaxContinuumComponentLimitPassageSource
          (all_output_source_of_global B hglobal)
  projected_stream_matches_block :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
        (all_output_source_of_global B hglobal)
        ((component_source_of_global B hglobal).split) =
          stream_of_block B
  threshold_coordinate_receipt_of_global :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        BranchSelfTaxThresholdCoordinateIdentities B (stream_of_block B)

/-- Source-first continuum all-output stream-family constructor.

This is the continuum analogue of
`leray_self_tax_noncircular_mv_stream_family_source_of_tendsto_measure_valued_sources`.
The block stream is not supplied independently: it is defined as the Leray
self-tax projection of the same all-output LP/Bony source and component split.
Consequently the `projected_stream_matches_block` field is paid by reduction,
not by a loose equality that could hide a source mismatch. -/
def leray_self_tax_continuum_all_output_stream_family_source_of_projected_sources
    {τ : ContinuumLPProfileTopology.{u}}
    (default_stream : LeraySelfTaxProfilePriceStream)
    (all_output_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ContinuumAllOutputLPBonySource τ)
    (component_source_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          LeraySelfTaxContinuumComponentLimitPassageSource
            (all_output_source_of_global B hglobal))
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        BranchSelfTaxThresholdCoordinateIdentities
          B
          (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
            (all_output_source_of_global B hglobal)
            ((component_source_of_global B hglobal).split))) :
    LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ where
  stream_of_block := by
    classical
    exact fun B =>
      if hglobal : IsGlobalTrackBBlock B then
        leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          (all_output_source_of_global B hglobal)
          ((component_source_of_global B hglobal).split)
      else
        default_stream
  all_output_source_of_global := all_output_source_of_global
  component_source_of_global := component_source_of_global
  projected_stream_matches_block := by
    classical
    intro B hglobal
    simp [hglobal]
  threshold_coordinate_receipt_of_global := by
    classical
    intro B hglobal
    simpa [hglobal] using threshold_coordinate_receipt_of_global B hglobal

/-- Threshold-coordinate receipt projected through the source-first continuum
all-output stream-family constructor.

This exposes the exact rewrite paid by `projected_stream_matches_block`: the
constructor does not create new branch coordinates, it transports the supplied
coordinates from the projected continuum stream to the family stream for the
same global block. -/
theorem threshold_coordinate_receipt_of_projected_continuum_stream_family_source
    {τ : ContinuumLPProfileTopology.{u}}
    (default_stream : LeraySelfTaxProfilePriceStream)
    (all_output_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ContinuumAllOutputLPBonySource τ)
    (component_source_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          LeraySelfTaxContinuumComponentLimitPassageSource
            (all_output_source_of_global B hglobal))
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        BranchSelfTaxThresholdCoordinateIdentities
          B
          (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
            (all_output_source_of_global B hglobal)
            ((component_source_of_global B hglobal).split)))
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    BranchSelfTaxThresholdCoordinateIdentities
      B
      ((leray_self_tax_continuum_all_output_stream_family_source_of_projected_sources
        default_stream
        all_output_source_of_global
        component_source_of_global
        threshold_coordinate_receipt_of_global).stream_of_block B) := by
  let source : LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ :=
    leray_self_tax_continuum_all_output_stream_family_source_of_projected_sources
      default_stream
      all_output_source_of_global
      component_source_of_global
      threshold_coordinate_receipt_of_global
  change BranchSelfTaxThresholdCoordinateIdentities B (source.stream_of_block B)
  rw [← source.projected_stream_matches_block B hglobal]
  exact threshold_coordinate_receipt_of_global B hglobal

/-- Project a continuum all-output stream-family source to the legacy
component-limit bridge consumed by the Track B threshold handoff. -/
def leray_self_tax_profile_component_limit_bridge_of_continuum_all_output_family_source
    {τ : ContinuumLPProfileTopology.{u}}
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ) :
    LeraySelfTaxProfileComponentLimitBridge where
  stream_of_block := source.stream_of_block
  component_limit_passage_of_global := by
    intro B hglobal
    let A := source.all_output_source_of_global B hglobal
    let P := source.component_source_of_global B hglobal
    have hmatch :
        leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
          A P.split = source.stream_of_block B :=
      source.projected_stream_matches_block B hglobal
    simpa [hmatch] using
      component_limit_passage_of_continuum_all_output_source A P
  threshold_coordinate_receipt_of_global :=
    source.threshold_coordinate_receipt_of_global

/-- Threshold-defect handoff directly from a continuum all-output
stream-family source. -/
theorem threshold_defect_of_leray_self_tax_continuum_all_output_stream_family_source
    {τ : ContinuumLPProfileTopology.{u}}
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ThresholdDefectConvexity B := by
  let bridge :=
    leray_self_tax_profile_component_limit_bridge_of_continuum_all_output_family_source
      source
  have hlimit :
      (source.stream_of_block B).payoffLimit ≤
        leraySelfTaxLimitPrice (source.stream_of_block B) :=
    no_global_self_tax_arbitrage_of_component_limit_passage
      (source.stream_of_block B)
      (bridge.component_limit_passage_of_global B hglobal)
  exact
    threshold_defect_of_branch_self_tax_threshold_coordinate_receipt
      B
      (source.stream_of_block B)
      (branch_self_tax_threshold_coordinate_receipt_of_identities
        B
        (source.stream_of_block B)
        (source.threshold_coordinate_receipt_of_global B hglobal))
      hlimit

/-- Continuum all-output stream family plus the branch's charged quartic
amplitude projection exposes the branch gain-at-amplitude cap. -/
theorem gain_at_amp_le_target_of_leray_self_tax_continuum_all_output_stream_family_source
    {τ : ContinuumLPProfileTopology.{u}}
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) :
    B.gamma * R.ampSq ≤ sharpTarget :=
  gain_at_amp_le_target_of_quartic_survival_amplitude_projection
    B
    R
    (threshold_defect_of_leray_self_tax_continuum_all_output_stream_family_source
      source B hglobal)

/-- Source-preserving no-survivor handoff for a continuum all-output
stream-family source. -/
theorem no_global_survivor_of_leray_self_tax_continuum_all_output_stream_family_source
    {τ : ContinuumLPProfileTopology.{u}}
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (R : QuarticSurvivalAmplitudeProjectionReceipt B) :
    FullLedgerNoSurvivor B :=
  full_ledger_no_survivor_of_quartic_survival_amplitude_projection
    B
    R
    (threshold_defect_of_leray_self_tax_continuum_all_output_stream_family_source
      source B hglobal)

/-- Build the source-derived block bridge directly from measure-valued output
sources and payoff-prefix convergence.

This is the block-family version of
`audited_output_limit_passage_source_of_measure_valued_source_and_tendsto_prefix_payoff`:
the PDE side supplies one Young/defect source family, one local-to-global
assembly family, payoff convergence, and a noncircular convergence provenance
for each global Track B block.  The audited output-derived receipt is then a
mechanical adapter rather than a hand-built per-block artifact. -/
def leray_self_tax_profile_output_derived_bridge_of_measure_valued_sources
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (assembly_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxPrefixLocalToGlobalComponentAssembly
            (stream_of_block B))
    (finite_prefix_charge_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          ∀ n : ℕ,
            LeraySelfTaxFinitePrefixChargeReceipt
              (stream_of_block B)
              (assembly_of_global B hglobal)
              n)
    (prefix_payoff_tendsto_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          Filter.Tendsto (stream_of_block B).prefixPayoff Filter.atTop
            (nhds (stream_of_block B).payoffLimit))
    (measure_valued_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxMeasureValuedOutputLimitSource
            (stream_of_block B))
    (noncircular_output_convergence_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B → Prop)
    (noncircular_output_convergence_source_receipt_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          noncircular_output_convergence_source_of_global B hglobal)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    LeraySelfTaxProfileOutputDerivedComponentLimitBridge where
  stream_of_block := stream_of_block
  output_derived_component_limit_passage_of_global := by
    intro B hglobal
    exact
      output_derived_component_limit_passage_of_audited_output_limit_source
        (stream_of_block B)
        (audited_output_limit_passage_source_of_measure_valued_source_and_tendsto_prefix_payoff
          (stream_of_block B)
          (assembly_of_global B hglobal)
          (finite_prefix_charge_of_global B hglobal)
          (prefix_payoff_tendsto_of_global B hglobal)
          (measure_valued_source_of_global B hglobal)
          (noncircular_output_convergence_source_of_global B hglobal)
          (noncircular_output_convergence_source_receipt_of_global B hglobal))
  threshold_coordinate_receipt_of_global :=
    threshold_coordinate_receipt_of_global

/-- Build the source-derived block bridge directly from measure-valued output
sources and Cauchy/subsequence payoff-prefix convergence.

This is the block-family diagonal compactness route.  It is useful when the PDE
construction produces a subsequential Young/defect limit first and separately
proves Cauchy control of the full payoff-prefix stream. -/
def leray_self_tax_profile_output_derived_bridge_of_measure_valued_sources_and_cauchySeq_subseq
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (assembly_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxPrefixLocalToGlobalComponentAssembly
            (stream_of_block B))
    (finite_prefix_charge_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          ∀ n : ℕ,
            LeraySelfTaxFinitePrefixChargeReceipt
              (stream_of_block B)
              (assembly_of_global B hglobal)
              n)
    (prefix_payoff_cauchy_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CauchySeq (stream_of_block B).prefixPayoff)
    (subseq_of_block : FullLedgerBlock → ℕ → ℕ)
    (prefix_payoff_subseq_strictMono_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          StrictMono (subseq_of_block B))
    (prefix_payoff_subseq_tendsto_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          Filter.Tendsto
            (fun k : ℕ =>
              (stream_of_block B).prefixPayoff (subseq_of_block B k))
            Filter.atTop
            (nhds (stream_of_block B).payoffLimit))
    (measure_valued_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          LeraySelfTaxMeasureValuedOutputLimitSource
            (stream_of_block B))
    (noncircular_output_convergence_source_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B → Prop)
    (noncircular_output_convergence_source_receipt_of_global :
      ∀ B : FullLedgerBlock,
        (hglobal : IsGlobalTrackBBlock B) →
          noncircular_output_convergence_source_of_global B hglobal)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    LeraySelfTaxProfileOutputDerivedComponentLimitBridge where
  stream_of_block := stream_of_block
  output_derived_component_limit_passage_of_global := by
    intro B hglobal
    exact
      output_derived_component_limit_passage_of_audited_output_limit_source
        (stream_of_block B)
        (audited_output_limit_source_of_measure_valued_cauchy_subseq
          (stream_of_block B)
          (assembly_of_global B hglobal)
          (finite_prefix_charge_of_global B hglobal)
          (prefix_payoff_cauchy_of_global B hglobal)
          (prefix_payoff_subseq_strictMono_of_global B hglobal)
          (prefix_payoff_subseq_tendsto_of_global B hglobal)
          (measure_valued_source_of_global B hglobal)
          (noncircular_output_convergence_source_of_global B hglobal)
          (noncircular_output_convergence_source_receipt_of_global B hglobal))
  threshold_coordinate_receipt_of_global :=
    threshold_coordinate_receipt_of_global

/-- Compatibility between a fixed profile-family no-arbitrage proof and the
Leray self-tax stream used for the threshold-root handoff.

This is the missing non-decorative bridge between the profile-decomposition
spine and the self-tax LSC spine.  It does not prove the PDE estimate; it names
the exact obligation: the same predeclared profile family whose payoff is
bounded by its price must feed the payoff/limit-price inequality for the same
block's self-tax stream. -/
structure ProfileFamilySelfTaxNoArbitrageCompatibility
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (profile_source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream) where
  profile_family_and_stream_declared_together :
    ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop
  profile_family_and_stream_declared_together_paid :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      profile_family_and_stream_declared_together B hglobal
  not_residual_only :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
      ¬ ((profile_family_of_block B).profiles = [] ∧
          (profile_family_of_block B).residualPayoff =
            (stream_of_block B).payoffLimit ∧
          (profile_family_of_block B).residualPrice =
            leraySelfTaxLimitPrice (stream_of_block B))
  family_no_arbitrage_feeds_self_tax_limit :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      TrackBProfileDecompositionThresholdHandoffSourceReady
        profile_source_receipt B hglobal →
      familyPayoff (profile_family_of_block B) ≤
        familyPrice (profile_family_of_block B) →
      (stream_of_block B).payoffLimit ≤
        leraySelfTaxLimitPrice (stream_of_block B)

/-- Identity-level compatibility between a profile family and the Leray
self-tax stream used for the same block.

This is the sharper PDE target behind
`ProfileFamilySelfTaxNoArbitrageCompatibility`: prove that the profile-family
payoff and price are exactly the payoff limit and self-tax limit price of the
same predeclared stream.  The no-arbitrage implication is then mechanical. -/
structure ProfileFamilySelfTaxStreamIdentityCompatibility
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream) where
  profile_family_and_stream_declared_together :
    ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop
  profile_family_and_stream_declared_together_paid :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      profile_family_and_stream_declared_together B hglobal
  not_residual_only :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
      ¬ ((profile_family_of_block B).profiles = [] ∧
          (profile_family_of_block B).residualPayoff =
            (stream_of_block B).payoffLimit ∧
          (profile_family_of_block B).residualPrice =
            leraySelfTaxLimitPrice (stream_of_block B))
  payoff_matches :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
      familyPayoff (profile_family_of_block B) =
        (stream_of_block B).payoffLimit
  price_matches :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
      familyPrice (profile_family_of_block B) =
        leraySelfTaxLimitPrice (stream_of_block B)

/-- Source-side constructor for profile-family/self-tax stream identity
compatibility from explicit PDE/source equalities.

This is intentionally only a packaging edge.  The hard work remains proving the
two displayed equalities for the same predeclared profile family and stream; the
constructor prevents downstream code from manufacturing compatibility from a
final GP216 branch receipt or from a constant dummy stream. -/
def profile_family_self_tax_stream_identity_compatibility_of_explicit_identities
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (not_residual_only :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        ¬ ((profile_family_of_block B).profiles = [] ∧
            (profile_family_of_block B).residualPayoff =
              (stream_of_block B).payoffLimit ∧
            (profile_family_of_block B).residualPrice =
              leraySelfTaxLimitPrice (stream_of_block B)))
    (payoff_matches :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        familyPayoff (profile_family_of_block B) =
          (stream_of_block B).payoffLimit)
    (price_matches :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        familyPrice (profile_family_of_block B) =
          leraySelfTaxLimitPrice (stream_of_block B)) :
    ProfileFamilySelfTaxStreamIdentityCompatibility
      profile_family_of_block stream_of_block where
  profile_family_and_stream_declared_together :=
    profile_family_and_stream_declared_together
  profile_family_and_stream_declared_together_paid :=
    profile_family_and_stream_declared_together_paid
  not_residual_only := not_residual_only
  payoff_matches := payoff_matches
  price_matches := price_matches

/-- Transport profile-family/self-tax stream identities along a proven
same-block stream equality.

This is deliberately only a provenance rewrite: it cannot create the payoff or
price identities, and it cannot hide the residual-only guard.  It is useful
when a source-facing constructor produces identities for `source.stream_of_block`
but a downstream bridge stores an equivalent stream family under a different
projection. -/
def profile_family_self_tax_stream_identity_compatibility_transport_stream
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {stream_of_block target_stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (I :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block stream_of_block)
    (stream_eq_on_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        stream_of_block B = target_stream_of_block B) :
    ProfileFamilySelfTaxStreamIdentityCompatibility
      profile_family_of_block target_stream_of_block where
  profile_family_and_stream_declared_together :=
    I.profile_family_and_stream_declared_together
  profile_family_and_stream_declared_together_paid :=
    I.profile_family_and_stream_declared_together_paid
  not_residual_only := by
    intro B hglobal hbad
    rcases hbad with ⟨hempty, hpay, hprice⟩
    have hstream : stream_of_block B = target_stream_of_block B :=
      stream_eq_on_global B hglobal
    exact
      I.not_residual_only B hglobal
        ⟨hempty,
          (by simpa [hstream] using hpay),
          (by simpa [hstream] using hprice)⟩
  payoff_matches := by
    intro B hglobal
    have hstream : stream_of_block B = target_stream_of_block B :=
      stream_eq_on_global B hglobal
    calc
      familyPayoff (profile_family_of_block B) =
          (stream_of_block B).payoffLimit :=
        I.payoff_matches B hglobal
      _ = (target_stream_of_block B).payoffLimit := by
        rw [hstream]
  price_matches := by
    intro B hglobal
    have hstream : stream_of_block B = target_stream_of_block B :=
      stream_eq_on_global B hglobal
    calc
      familyPrice (profile_family_of_block B) =
          leraySelfTaxLimitPrice (stream_of_block B) :=
        I.price_matches B hglobal
      _ = leraySelfTaxLimitPrice (target_stream_of_block B) := by
        rw [hstream]

/-- Special case of stream-identity transport for a constant downstream
self-tax stream.

This is the GP216-facing form: callers still prove that each source-family
stream equals the stored output stream on global blocks.  The equality is the
load-bearing same-source witness; this adapter only rewrites the existing
identity receipt to the constant-stream API. -/
def profile_family_self_tax_stream_identity_compatibility_to_constant_stream
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (target_stream : LeraySelfTaxProfilePriceStream)
    (I :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block stream_of_block)
    (stream_eq_target_on_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        stream_of_block B = target_stream) :
    ProfileFamilySelfTaxStreamIdentityCompatibility
      profile_family_of_block (fun _B : FullLedgerBlock => target_stream) :=
  profile_family_self_tax_stream_identity_compatibility_transport_stream
    I
    stream_eq_target_on_global

/-- Exact profile-family/self-tax identities cannot be closed by the
residual-only family whose profile list is empty and whose residual fields are
defined to be the self-tax stream endpoints.

This is a hostile-referee guard, not a PDE estimate: the PDE side must show the
profile decomposition carries genuine non-residual source content before the
identity compatibility can feed Track B closure. -/
theorem no_residual_only_profile_family_self_tax_stream_identity
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (I :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block stream_of_block)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ¬ ((profile_family_of_block B).profiles = [] ∧
        (profile_family_of_block B).residualPayoff =
          (stream_of_block B).payoffLimit ∧
        (profile_family_of_block B).residualPrice =
          leraySelfTaxLimitPrice (stream_of_block B)) :=
  I.not_residual_only B hglobal

/-- A concrete profile in the declared family rules out the residual-only
self-tax identity shortcut.  This is the intended easy way for a genuine
profile-decomposition theorem to discharge the anti-tautology guard. -/
theorem not_residual_only_profile_family_self_tax_stream_of_profile_mem
    {F : PricingProfileFamily}
    {S : LeraySelfTaxProfilePriceStream}
    {P : PricingProfile}
    (hmem : P ∈ F.profiles) :
    ¬ (F.profiles = [] ∧
        F.residualPayoff = S.payoffLimit ∧
        F.residualPrice = leraySelfTaxLimitPrice S) := by
  intro hbad
  rcases hbad with ⟨hprofiles, _hpay, _hprice⟩
  rw [hprofiles] at hmem
  simp at hmem

/-- Block-family version of
`not_residual_only_profile_family_self_tax_stream_of_profile_mem`. -/
theorem not_residual_only_profile_family_self_tax_stream_of_profile_mem_global
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (profile_mem_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        ∃ P : PricingProfile, P ∈ (profile_family_of_block B).profiles)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ¬ ((profile_family_of_block B).profiles = [] ∧
        (profile_family_of_block B).residualPayoff =
          (stream_of_block B).payoffLimit ∧
        (profile_family_of_block B).residualPrice =
          leraySelfTaxLimitPrice (stream_of_block B)) := by
  obtain ⟨P, hmem⟩ := profile_mem_of_global B hglobal
  exact
    not_residual_only_profile_family_self_tax_stream_of_profile_mem
      (F := profile_family_of_block B)
      (S := stream_of_block B)
      (P := P)
      hmem

/-- A nonempty declared profile list supplies the profile-membership witness
used by the residual-only anti-tautology guard. -/
theorem profile_mem_of_global_of_profiles_ne_nil
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    (profiles_ne_nil_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        (profile_family_of_block B).profiles ≠ []) :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
      ∃ P : PricingProfile, P ∈ (profile_family_of_block B).profiles := by
  intro B hglobal
  cases hprofiles : (profile_family_of_block B).profiles with
  | nil =>
      exact False.elim ((profiles_ne_nil_of_global B hglobal) hprofiles)
  | cons P Ps =>
      exact ⟨P, by simp⟩

/-- Source-side constructor for exact profile-family/self-tax stream
compatibility when the PDE decomposition can exhibit at least one declared
profile in every global family.

This is the preferred constructor for nondegenerate profile decompositions:
callers provide the two endpoint equalities plus a concrete profile-membership
witness, and the residual-only anti-tautology guard is derived internally. -/
def profile_family_self_tax_stream_identity_compatibility_of_profile_mem_and_explicit_identities
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (profile_mem_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        ∃ P : PricingProfile, P ∈ (profile_family_of_block B).profiles)
    (payoff_matches :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        familyPayoff (profile_family_of_block B) =
          (stream_of_block B).payoffLimit)
    (price_matches :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        familyPrice (profile_family_of_block B) =
          leraySelfTaxLimitPrice (stream_of_block B)) :
    ProfileFamilySelfTaxStreamIdentityCompatibility
      profile_family_of_block stream_of_block :=
  profile_family_self_tax_stream_identity_compatibility_of_explicit_identities
    profile_family_and_stream_declared_together
    profile_family_and_stream_declared_together_paid
    (not_residual_only_profile_family_self_tax_stream_of_profile_mem_global
      profile_mem_of_global)
    payoff_matches
    price_matches

/-- Exact profile-family/self-tax stream identities for a fixed positive
LP-shell prefix.

This is the direct identity-compatibility route when the declared profile
family is the finite Littlewood-Paley prefix.  The positive prefix supplies the
profile-membership witness; the profile payoff/price equalities to the selected
self-tax stream remain explicit source obligations. -/
def profile_family_self_tax_stream_identity_compatibility_of_lp_prefixes_and_explicit_identities
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (lp_stream_of_block : FullLedgerBlock → LPShellPricingStream)
    (prefix_len_of_block : FullLedgerBlock → ℕ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (prefix_len_pos_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        0 < prefix_len_of_block B)
    (payoff_matches :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        familyPayoff
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)) =
          (stream_of_block B).payoffLimit)
    (price_matches :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        familyPrice
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)) =
          leraySelfTaxLimitPrice (stream_of_block B)) :
    ProfileFamilySelfTaxStreamIdentityCompatibility
      (fun B =>
        lpPrefixProfileFamily
          (lp_stream_of_block B) (prefix_len_of_block B))
      stream_of_block :=
  profile_family_self_tax_stream_identity_compatibility_of_profile_mem_and_explicit_identities
    profile_family_and_stream_declared_together
    profile_family_and_stream_declared_together_paid
    (fun B hglobal =>
      lpPrefixProfileFamily_profile_mem_of_pos
        (lp_stream_of_block B)
        (prefix_len_pos_of_global B hglobal))
    payoff_matches
    price_matches

/-- LP-prefix identity compatibility from a generic endpoint-identification
source.

This is the reusable PDE-facing route: the LP layer pays positive-prefix and
finite-prefix endpoint identification, while this constructor only adapts those
endpoints to the self-tax stream fields used by Track B. -/
def profile_family_self_tax_stream_identity_compatibility_of_lp_endpoint_identification_source
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (lp_stream_of_block : FullLedgerBlock → LPShellPricingStream)
    (prefix_len_of_block : FullLedgerBlock → ℕ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (endpoint_source :
      LPPrefixEndpointIdentificationSource
        IsGlobalTrackBBlock
        lp_stream_of_block
        prefix_len_of_block
        (fun B => (stream_of_block B).payoffLimit)
        (fun B => leraySelfTaxLimitPrice (stream_of_block B))) :
    ProfileFamilySelfTaxStreamIdentityCompatibility
      (fun B =>
        lpPrefixProfileFamily
          (lp_stream_of_block B) (prefix_len_of_block B))
      stream_of_block :=
  profile_family_self_tax_stream_identity_compatibility_of_lp_prefixes_and_explicit_identities
    lp_stream_of_block
    prefix_len_of_block
    profile_family_and_stream_declared_together
    profile_family_and_stream_declared_together_paid
    endpoint_source.prefix_pos
    (fun B hglobal =>
      familyPayoff_lpPrefixProfileFamily_eq_endpoint_of_endpoint_identification
        endpoint_source (a := B) hglobal)
    (fun B hglobal =>
      familyPrice_lpPrefixProfileFamily_eq_endpoint_of_endpoint_identification
        endpoint_source (a := B) hglobal)

/-- Noncircular scalar-alignment source from a nonempty-profile guard and
explicit profile-family/self-tax equalities.

This is a source-object constructor, not an endpoint proof: it turns the
residual-only anti-tautology guard `profiles != []` into the membership witness
required by `NoncircularMeasureValuedProfileFamilyScalarAlignmentSource`, while
leaving the two scalar equalities fully explicit. -/
def noncircular_mv_scalar_alignment_source_of_profiles_ne_nil_and_explicit_identities
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource}
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (profiles_ne_nil_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        (profile_family_of_block B).profiles ≠ [])
    (family_payoff_matches_stream :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPayoff (profile_family_of_block B) =
          (source.stream_of_block B).payoffLimit)
    (family_price_matches_stream :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPrice (profile_family_of_block B) =
          leraySelfTaxLimitPrice (source.stream_of_block B)) :
    NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
      profile_family_of_block source where
  profile_family_and_stream_declared_together :=
    profile_family_and_stream_declared_together
  profile_family_and_stream_declared_together_paid :=
    profile_family_and_stream_declared_together_paid
  profile_mem_of_global :=
    profile_mem_of_global_of_profiles_ne_nil profiles_ne_nil_of_global
  family_payoff_matches_stream := family_payoff_matches_stream
  family_price_matches_stream := family_price_matches_stream

/-- Noncircular scalar-alignment source for a fixed positive LP-shell prefix.

This is the finite-prefix LP version of the nonempty-profile constructor:
`lpPrefixProfileFamily_profiles_ne_nil_of_pos` pays the residual-only
membership guard from the declared prefix list itself.  The scalar payoff and
price equalities remain explicit source obligations. -/
def noncircular_mv_scalar_alignment_source_of_lp_prefixes_and_explicit_identities
    {source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource}
    (lp_stream_of_block : FullLedgerBlock → LPShellPricingStream)
    (prefix_len_of_block : FullLedgerBlock → ℕ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (prefix_len_pos_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        0 < prefix_len_of_block B)
    (family_payoff_matches_stream :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPayoff
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)) =
          (source.stream_of_block B).payoffLimit)
    (family_price_matches_stream :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPrice
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)) =
          leraySelfTaxLimitPrice (source.stream_of_block B)) :
    NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
      (fun B =>
        lpPrefixProfileFamily
          (lp_stream_of_block B) (prefix_len_of_block B))
      source :=
  noncircular_mv_scalar_alignment_source_of_profiles_ne_nil_and_explicit_identities
    profile_family_and_stream_declared_together
    profile_family_and_stream_declared_together_paid
    (fun B hglobal =>
      lpPrefixProfileFamily_profiles_ne_nil_of_pos
        (lp_stream_of_block B)
        (prefix_len_pos_of_global B hglobal))
    family_payoff_matches_stream
    family_price_matches_stream

/-- Noncircular scalar-alignment source from a generic LP endpoint
identification source.

This keeps the finite-prefix endpoint debt in one reusable source object
instead of passing payoff/price equalities as loose arguments. -/
def noncircular_mv_scalar_alignment_source_of_lp_endpoint_identification_source
    {source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource}
    (lp_stream_of_block : FullLedgerBlock → LPShellPricingStream)
    (prefix_len_of_block : FullLedgerBlock → ℕ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (endpoint_source :
      LPPrefixEndpointIdentificationSource
        IsGlobalTrackBBlock
        lp_stream_of_block
        prefix_len_of_block
        (fun B => (source.stream_of_block B).payoffLimit)
        (fun B => leraySelfTaxLimitPrice (source.stream_of_block B))) :
    NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
      (fun B =>
        lpPrefixProfileFamily
          (lp_stream_of_block B) (prefix_len_of_block B))
      source :=
  noncircular_mv_scalar_alignment_source_of_lp_prefixes_and_explicit_identities
    lp_stream_of_block
    prefix_len_of_block
    profile_family_and_stream_declared_together
    profile_family_and_stream_declared_together_paid
    endpoint_source.prefix_pos
    (fun B hglobal =>
      familyPayoff_lpPrefixProfileFamily_eq_endpoint_of_endpoint_identification
        endpoint_source (a := B) hglobal)
    (fun B hglobal =>
      familyPrice_lpPrefixProfileFamily_eq_endpoint_of_endpoint_identification
        endpoint_source (a := B) hglobal)

/-- Exact profile-family/self-tax stream identities from a named noncircular
measure-valued scalar-alignment source.

This keeps the noncircular route source-facing: callers provide one audited
alignment object instead of loose payoff/price equalities, and the
residual-only shortcut is still ruled out by its profile-membership field. -/
def profile_family_self_tax_stream_identity_compatibility_of_noncircular_mv_scalar_alignment_source
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource}
    (alignment :
      NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
        profile_family_of_block source) :
    ProfileFamilySelfTaxStreamIdentityCompatibility
      profile_family_of_block source.stream_of_block :=
  profile_family_self_tax_stream_identity_compatibility_of_profile_mem_and_explicit_identities
    alignment.profile_family_and_stream_declared_together
    alignment.profile_family_and_stream_declared_together_paid
    alignment.profile_mem_of_global
    alignment.family_payoff_matches_stream
    alignment.family_price_matches_stream

/-- Continuum all-output source adapter for exact profile-family/self-tax
stream identities.

This is the non-circular scalar alignment target for the continuum LP/Bony
route.  The caller proves that the declared profile family has genuine profile
content and that its payoff/price equal the continuum all-output source's
smooth payoff/global target.  This adapter then composes those equalities with
the already-audited projection from continuum source to Leray self-tax stream.
-/
def profile_family_self_tax_stream_identity_compatibility_of_continuum_all_output_family_source
    {τ : ContinuumLPProfileTopology.{u}}
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (profile_mem_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        ∃ P : PricingProfile, P ∈ (profile_family_of_block B).profiles)
    (family_payoff_matches_continuum :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPayoff (profile_family_of_block B) =
          (source.all_output_source_of_global B hglobal).stream.smoothCandidatePayoff)
    (family_price_matches_continuum :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPrice (profile_family_of_block B) =
          continuumGlobalSelfTaxTarget
            (source.all_output_source_of_global B hglobal).stream) :
    ProfileFamilySelfTaxStreamIdentityCompatibility
      profile_family_of_block source.stream_of_block :=
  profile_family_self_tax_stream_identity_compatibility_of_profile_mem_and_explicit_identities
    profile_family_and_stream_declared_together
    profile_family_and_stream_declared_together_paid
    profile_mem_of_global
    (by
      intro B hglobal
      let A := source.all_output_source_of_global B hglobal
      let P := source.component_source_of_global B hglobal
      have hmatch :
          leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
            A P.split = source.stream_of_block B :=
        source.projected_stream_matches_block B hglobal
      have hpay :
          familyPayoff (profile_family_of_block B) =
            A.stream.smoothCandidatePayoff := by
        simpa [A] using family_payoff_matches_continuum B hglobal
      have hproject :
          (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
            A P.split).payoffLimit = A.stream.smoothCandidatePayoff := rfl
      calc
        familyPayoff (profile_family_of_block B) =
            A.stream.smoothCandidatePayoff := hpay
        _ =
            (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
              A P.split).payoffLimit := hproject.symm
        _ = (source.stream_of_block B).payoffLimit := by
          rw [hmatch])
    (by
      intro B hglobal
      let A := source.all_output_source_of_global B hglobal
      let P := source.component_source_of_global B hglobal
      have hmatch :
          leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
            A P.split = source.stream_of_block B :=
        source.projected_stream_matches_block B hglobal
      have hprice :
          familyPrice (profile_family_of_block B) =
            continuumGlobalSelfTaxTarget A.stream := by
        simpa [A] using family_price_matches_continuum B hglobal
      have hproject :
          leraySelfTaxLimitPrice
              (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
                A P.split) =
            continuumGlobalSelfTaxTarget A.stream :=
        leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource_limitPrice_eq
          A P.split
      calc
        familyPrice (profile_family_of_block B) =
            continuumGlobalSelfTaxTarget A.stream := hprice
        _ =
            leraySelfTaxLimitPrice
              (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
                A P.split) := hproject.symm
        _ = leraySelfTaxLimitPrice (source.stream_of_block B) := by
          rw [hmatch])

/-- Source object for continuum/profile-family scalar alignment.

This is the non-tautological witness package behind the continuum all-output
profile-family adapter.  It deliberately does not construct the scalar
equalities by definition.  The PDE/profile decomposition side must supply a
genuine profile-membership witness and the two field-level equalities tying the
fixed family payoff/price to the continuum all-output stream. -/
structure ContinuumProfileFamilyScalarAlignmentSource
    {τ : ContinuumLPProfileTopology.{u}}
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ) where
  profile_family_and_stream_declared_together :
    ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop
  profile_family_and_stream_declared_together_paid :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      profile_family_and_stream_declared_together B hglobal
  profile_mem_of_global :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
      ∃ P : PricingProfile, P ∈ (profile_family_of_block B).profiles
  family_payoff_matches_continuum :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      familyPayoff (profile_family_of_block B) =
        (source.all_output_source_of_global B hglobal).stream.smoothCandidatePayoff
  family_price_matches_continuum :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      familyPrice (profile_family_of_block B) =
        continuumGlobalSelfTaxTarget
          (source.all_output_source_of_global B hglobal).stream

/-- Inequality-level continuum/profile-family scalar alignment source.

Exact family-to-continuum scalar identities are often stronger than the limit
passage needs.  This source keeps the same non-residual profile-membership and
joint-declaration guards, but asks only for the two lower-semicontinuity
directions that feed `ProfileFamilySelfTaxNoArbitrageCompatibility`: the
projected continuum payoff is bounded by the declared family payoff, and the
family price is bounded by the same continuum global target used by the
projected self-tax stream. -/
structure ContinuumProfileFamilyInequalityAlignmentSource
    {τ : ContinuumLPProfileTopology.{u}}
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ) where
  profile_family_and_stream_declared_together :
    ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop
  profile_family_and_stream_declared_together_paid :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      profile_family_and_stream_declared_together B hglobal
  profile_mem_of_global :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
      ∃ P : PricingProfile, P ∈ (profile_family_of_block B).profiles
  continuum_payoff_le_family_payoff :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      (source.all_output_source_of_global B hglobal).stream.smoothCandidatePayoff ≤
        familyPayoff (profile_family_of_block B)
  family_price_le_continuum :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      familyPrice (profile_family_of_block B) ≤
        continuumGlobalSelfTaxTarget
          (source.all_output_source_of_global B hglobal).stream

/-- Continuum scalar-alignment source from a nonempty-profile guard and
explicit family-to-continuum equalities. -/
def continuum_scalar_alignment_source_of_profiles_ne_nil_and_explicit_identities
    {τ : ContinuumLPProfileTopology.{u}}
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (profiles_ne_nil_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        (profile_family_of_block B).profiles ≠ [])
    (family_payoff_matches_continuum :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPayoff (profile_family_of_block B) =
          (source.all_output_source_of_global B hglobal).stream.smoothCandidatePayoff)
    (family_price_matches_continuum :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPrice (profile_family_of_block B) =
          continuumGlobalSelfTaxTarget
            (source.all_output_source_of_global B hglobal).stream) :
    ContinuumProfileFamilyScalarAlignmentSource
      profile_family_of_block source where
  profile_family_and_stream_declared_together :=
    profile_family_and_stream_declared_together
  profile_family_and_stream_declared_together_paid :=
    profile_family_and_stream_declared_together_paid
  profile_mem_of_global :=
    profile_mem_of_global_of_profiles_ne_nil profiles_ne_nil_of_global
  family_payoff_matches_continuum := family_payoff_matches_continuum
  family_price_matches_continuum := family_price_matches_continuum

/-- Continuum scalar-alignment source for a fixed positive LP-shell prefix.

This is the continuum all-output counterpart of
`noncircular_mv_scalar_alignment_source_of_lp_prefixes_and_explicit_identities`.
The positive prefix supplies genuine profile membership; the profile-family
payoff and price equalities to the continuum stream remain explicit. -/
def continuum_scalar_alignment_source_of_lp_prefixes_and_explicit_identities
    {τ : ContinuumLPProfileTopology.{u}}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (lp_stream_of_block : FullLedgerBlock → LPShellPricingStream)
    (prefix_len_of_block : FullLedgerBlock → ℕ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (prefix_len_pos_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        0 < prefix_len_of_block B)
    (family_payoff_matches_continuum :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPayoff
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)) =
          (source.all_output_source_of_global B hglobal).stream.smoothCandidatePayoff)
    (family_price_matches_continuum :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPrice
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)) =
          continuumGlobalSelfTaxTarget
            (source.all_output_source_of_global B hglobal).stream) :
    ContinuumProfileFamilyScalarAlignmentSource
      (fun B =>
        lpPrefixProfileFamily
          (lp_stream_of_block B) (prefix_len_of_block B))
      source :=
  continuum_scalar_alignment_source_of_profiles_ne_nil_and_explicit_identities
    profile_family_and_stream_declared_together
    profile_family_and_stream_declared_together_paid
    (fun B hglobal =>
      lpPrefixProfileFamily_profiles_ne_nil_of_pos
        (lp_stream_of_block B)
        (prefix_len_pos_of_global B hglobal))
    family_payoff_matches_continuum
    family_price_matches_continuum

/-- Proof-independent payoff endpoint selected by a continuum all-output
source on global blocks.

This lets generic LP-prefix endpoint-identification sources target the
continuum all-output payoff without carrying a proof argument in the endpoint
function.  Non-global blocks are assigned a dummy value; all consumers below
use the endpoint only under `IsGlobalTrackBBlock`. -/
noncomputable def continuumAllOutputPayoffEndpointOfGlobal
    {τ : ContinuumLPProfileTopology.{u}}
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (B : FullLedgerBlock) : Real := by
  classical
  exact
    if hglobal : IsGlobalTrackBBlock B then
      (source.all_output_source_of_global B hglobal).stream.smoothCandidatePayoff
    else
      0

/-- Proof-independent price endpoint selected by a continuum all-output source
on global blocks. -/
noncomputable def continuumAllOutputPriceEndpointOfGlobal
    {τ : ContinuumLPProfileTopology.{u}}
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (B : FullLedgerBlock) : Real := by
  classical
  exact
    if hglobal : IsGlobalTrackBBlock B then
      continuumGlobalSelfTaxTarget
        (source.all_output_source_of_global B hglobal).stream
    else
      0

/-- Continuum scalar-alignment source from a generic LP endpoint-identification
source.

This is the continuum all-output analogue of
`noncircular_mv_scalar_alignment_source_of_lp_endpoint_identification_source`.
It keeps the finite-prefix endpoint debt in one falsifiable source object
instead of passing the two family-to-continuum equalities as loose arguments. -/
noncomputable def continuum_scalar_alignment_source_of_lp_endpoint_identification_source
    {τ : ContinuumLPProfileTopology.{u}}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (lp_stream_of_block : FullLedgerBlock → LPShellPricingStream)
    (prefix_len_of_block : FullLedgerBlock → ℕ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (endpoint_source :
      LPPrefixEndpointIdentificationSource
        IsGlobalTrackBBlock
        lp_stream_of_block
        prefix_len_of_block
        (continuumAllOutputPayoffEndpointOfGlobal source)
        (continuumAllOutputPriceEndpointOfGlobal source)) :
    ContinuumProfileFamilyScalarAlignmentSource
      (fun B =>
        lpPrefixProfileFamily
          (lp_stream_of_block B) (prefix_len_of_block B))
      source :=
  continuum_scalar_alignment_source_of_lp_prefixes_and_explicit_identities
    lp_stream_of_block
    prefix_len_of_block
    profile_family_and_stream_declared_together
    profile_family_and_stream_declared_together_paid
    endpoint_source.prefix_pos
    (fun B hglobal => by
      have h :=
        familyPayoff_lpPrefixProfileFamily_eq_endpoint_of_endpoint_identification
          endpoint_source (a := B) hglobal
      simpa [continuumAllOutputPayoffEndpointOfGlobal, hglobal] using h)
    (fun B hglobal => by
      have h :=
        familyPrice_lpPrefixProfileFamily_eq_endpoint_of_endpoint_identification
          endpoint_source (a := B) hglobal
      simpa [continuumAllOutputPriceEndpointOfGlobal, hglobal] using h)

/-- Exact profile-family/self-tax stream identities from a named continuum
scalar-alignment source.

This constructor compresses the proof endpoint without weakening it: all
field-level scalar equalities are still carried by
`ContinuumProfileFamilyScalarAlignmentSource`, and the residual-only shortcut
is still ruled out by its `profile_mem_of_global` field. -/
def profile_family_self_tax_stream_identity_compatibility_of_continuum_scalar_alignment_source
    {τ : ContinuumLPProfileTopology.{u}}
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    (alignment :
      ContinuumProfileFamilyScalarAlignmentSource
        profile_family_of_block source) :
    ProfileFamilySelfTaxStreamIdentityCompatibility
      profile_family_of_block source.stream_of_block :=
  profile_family_self_tax_stream_identity_compatibility_of_continuum_all_output_family_source
    source
    alignment.profile_family_and_stream_declared_together
    alignment.profile_family_and_stream_declared_together_paid
    alignment.profile_mem_of_global
    alignment.family_payoff_matches_continuum
    alignment.family_price_matches_continuum

/-- Exact profile-family/self-tax stream identities derive the implication
compatibility consumed by the Track B threshold handoff. -/
def profile_family_self_tax_no_arbitrage_compatibility_of_stream_identities
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {profile_source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (I :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block stream_of_block) :
    ProfileFamilySelfTaxNoArbitrageCompatibility
      profile_family_of_block profile_source_receipt stream_of_block where
  profile_family_and_stream_declared_together :=
    I.profile_family_and_stream_declared_together
  profile_family_and_stream_declared_together_paid :=
    I.profile_family_and_stream_declared_together_paid
  not_residual_only := I.not_residual_only
  family_no_arbitrage_feeds_self_tax_limit := by
    intro B hglobal _hsource hfamily
    have hpay :
        familyPayoff (profile_family_of_block B) =
          (stream_of_block B).payoffLimit :=
      I.payoff_matches B hglobal
    have hprice :
        familyPrice (profile_family_of_block B) =
          leraySelfTaxLimitPrice (stream_of_block B) :=
      I.price_matches B hglobal
    simpa [hpay, hprice] using hfamily

/-- Inequality-level source constructor for profile-family/self-tax
no-arbitrage compatibility.

Exact family/stream identities are sufficient but often too strong at a
profile limit.  This constructor captures the lower-semicontinuity shape
actually needed by Track B: the limiting payoff is bounded by the declared
family payoff, and the declared family price is bounded by the same self-tax
limit price.  The residual-only and joint-declaration guards remain explicit. -/
def profile_family_self_tax_no_arbitrage_compatibility_of_payoff_price_bounds
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {profile_source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (not_residual_only :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        ¬ ((profile_family_of_block B).profiles = [] ∧
            (profile_family_of_block B).residualPayoff =
              (stream_of_block B).payoffLimit ∧
            (profile_family_of_block B).residualPrice =
              leraySelfTaxLimitPrice (stream_of_block B)))
    (limit_payoff_le_family_payoff :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        (stream_of_block B).payoffLimit ≤
          familyPayoff (profile_family_of_block B))
    (family_price_le_limit_price :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        familyPrice (profile_family_of_block B) ≤
          leraySelfTaxLimitPrice (stream_of_block B)) :
    ProfileFamilySelfTaxNoArbitrageCompatibility
      profile_family_of_block profile_source_receipt stream_of_block where
  profile_family_and_stream_declared_together :=
    profile_family_and_stream_declared_together
  profile_family_and_stream_declared_together_paid :=
    profile_family_and_stream_declared_together_paid
  not_residual_only := not_residual_only
  family_no_arbitrage_feeds_self_tax_limit := by
    intro B hglobal _hsource hfamily
    exact
      (limit_payoff_le_family_payoff B hglobal).trans
        (hfamily.trans (family_price_le_limit_price B hglobal))

/-- Inequality-level no-arbitrage compatibility from a continuum all-output
profile-family alignment source.

This is the LSC-friendly counterpart of
`profile_family_self_tax_stream_identity_compatibility_of_continuum_scalar_alignment_source`.
It does not assert scalar equality between the profile family and the projected
self-tax stream; it proves only the no-arbitrage implication Track B needs,
using the continuum payoff/price bounds and the fixed projected stream. -/
def profile_family_self_tax_no_arbitrage_compatibility_of_continuum_inequality_alignment_source
    {τ : ContinuumLPProfileTopology.{u}}
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ}
    {profile_source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block}
    (alignment :
      ContinuumProfileFamilyInequalityAlignmentSource
        profile_family_of_block source) :
    ProfileFamilySelfTaxNoArbitrageCompatibility
      profile_family_of_block profile_source_receipt source.stream_of_block :=
  profile_family_self_tax_no_arbitrage_compatibility_of_payoff_price_bounds
    alignment.profile_family_and_stream_declared_together
    alignment.profile_family_and_stream_declared_together_paid
    (not_residual_only_profile_family_self_tax_stream_of_profile_mem_global
      (stream_of_block := source.stream_of_block)
      alignment.profile_mem_of_global)
    (by
      intro B hglobal
      let A := source.all_output_source_of_global B hglobal
      let P := source.component_source_of_global B hglobal
      have hmatch :
          leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
            A P.split = source.stream_of_block B :=
        source.projected_stream_matches_block B hglobal
      have hpay :
          A.stream.smoothCandidatePayoff ≤
            familyPayoff (profile_family_of_block B) := by
        simpa [A] using
          alignment.continuum_payoff_le_family_payoff B hglobal
      have hproject :
          (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
            A P.split).payoffLimit = A.stream.smoothCandidatePayoff := rfl
      calc
        (source.stream_of_block B).payoffLimit =
            (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
              A P.split).payoffLimit := by
          rw [← hmatch]
        _ = A.stream.smoothCandidatePayoff := hproject
        _ ≤ familyPayoff (profile_family_of_block B) := hpay)
    (by
      intro B hglobal
      let A := source.all_output_source_of_global B hglobal
      let P := source.component_source_of_global B hglobal
      have hmatch :
          leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
            A P.split = source.stream_of_block B :=
        source.projected_stream_matches_block B hglobal
      have hprice :
          familyPrice (profile_family_of_block B) ≤
            continuumGlobalSelfTaxTarget A.stream := by
        simpa [A] using alignment.family_price_le_continuum B hglobal
      have hproject :
          leraySelfTaxLimitPrice
              (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
                A P.split) =
            continuumGlobalSelfTaxTarget A.stream :=
        leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource_limitPrice_eq
          A P.split
      calc
        familyPrice (profile_family_of_block B) ≤
            continuumGlobalSelfTaxTarget A.stream := hprice
        _ =
            leraySelfTaxLimitPrice
              (leraySelfTaxProfilePriceStreamOfContinuumAllOutputSource
                A P.split) := hproject.symm
        _ = leraySelfTaxLimitPrice (source.stream_of_block B) := by
          rw [hmatch])

/-- Hostile surface for a profile-family/self-tax compatibility bridge.

The second branch is the important one: a candidate proof cannot use a
profile-family no-arbitrage premise while deriving the self-tax limit
no-arbitrage from an unrelated stream receipt. -/
inductive ProfileFamilySelfTaxNoArbitrageCompatibilityFalsifier
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {profile_source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (C :
      ProfileFamilySelfTaxNoArbitrageCompatibility
        profile_family_of_block profile_source_receipt stream_of_block) :
    Type where
  | familyStreamNotJointlyDeclared
      (B : FullLedgerBlock) (hglobal : IsGlobalTrackBBlock B) :
      ¬ C.profile_family_and_stream_declared_together B hglobal →
        ProfileFamilySelfTaxNoArbitrageCompatibilityFalsifier C
  | residualOnlyProfileFamily
      (B : FullLedgerBlock)
      (hglobal : IsGlobalTrackBBlock B) :
      (profile_family_of_block B).profiles = [] →
      (profile_family_of_block B).residualPayoff =
        (stream_of_block B).payoffLimit →
      (profile_family_of_block B).residualPrice =
        leraySelfTaxLimitPrice (stream_of_block B) →
        ProfileFamilySelfTaxNoArbitrageCompatibilityFalsifier C
  | familyNoArbitrageDoesNotFeedSelfTaxLimit
      (B : FullLedgerBlock)
      (hglobal : IsGlobalTrackBBlock B)
      (hsource :
        TrackBProfileDecompositionThresholdHandoffSourceReady
          profile_source_receipt B hglobal)
      (hfamily :
        familyPayoff (profile_family_of_block B) ≤
          familyPrice (profile_family_of_block B)) :
      ¬ (stream_of_block B).payoffLimit ≤
          leraySelfTaxLimitPrice (stream_of_block B) →
        ProfileFamilySelfTaxNoArbitrageCompatibilityFalsifier C

/-- A paid profile-family/self-tax compatibility bridge excludes its two named
failure modes. -/
theorem no_profile_family_self_tax_no_arbitrage_compatibility_falsifier
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {profile_source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (C :
      ProfileFamilySelfTaxNoArbitrageCompatibility
        profile_family_of_block profile_source_receipt stream_of_block)
    (F :
      ProfileFamilySelfTaxNoArbitrageCompatibilityFalsifier C) :
    False := by
  cases F with
  | familyStreamNotJointlyDeclared B hglobal hmissing =>
      exact hmissing
        (C.profile_family_and_stream_declared_together_paid B hglobal)
  | residualOnlyProfileFamily B hglobal hprofiles hpay hprice =>
      exact
        (C.not_residual_only B hglobal)
          ⟨hprofiles, hpay, hprice⟩
  | familyNoArbitrageDoesNotFeedSelfTaxLimit B hglobal hsource hfamily hmissing =>
      exact hmissing
        (C.family_no_arbitrage_feeds_self_tax_limit
          B hglobal hsource hfamily)

/-- Profile-family no-arbitrage, once tied to the same self-tax stream, gives
the Track B threshold defect through the existing threshold-coordinate
identity package.

This theorem is the intended constructor for
`TrackBProfileDecompositionBridgeBundle.threshold_handoff_of_family_no_arbitrage`
when the handoff is supplied by the Leray self-tax/profile LSC route. -/
theorem threshold_defect_of_profile_family_self_tax_no_arbitrage_compatibility
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    {profile_source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block}
    {stream_of_block : FullLedgerBlock → LeraySelfTaxProfilePriceStream}
    (C :
      ProfileFamilySelfTaxNoArbitrageCompatibility
        profile_family_of_block profile_source_receipt stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B))
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hsource :
      TrackBProfileDecompositionThresholdHandoffSourceReady
        profile_source_receipt B hglobal)
    (hfamily :
      familyPayoff (profile_family_of_block B) ≤
        familyPrice (profile_family_of_block B)) :
    ThresholdDefectConvexity B := by
  have hlimit :
      (stream_of_block B).payoffLimit ≤
        leraySelfTaxLimitPrice (stream_of_block B) :=
    C.family_no_arbitrage_feeds_self_tax_limit
      B hglobal hsource hfamily
  exact
    threshold_defect_of_branch_self_tax_threshold_coordinate_receipt
      B
      (stream_of_block B)
      (branch_self_tax_threshold_coordinate_receipt_of_identities
        B
        (stream_of_block B)
        (threshold_coordinate_receipt_of_global B hglobal))
      hlimit

/-- Source-aware constructor for the legacy null-profile branch bridge.

The old bridge API has no explicit Track B source guard on its threshold
handoff field. This constructor fills that field only from the same
profile-family/self-tax compatibility route used by the source-aware
decomposition bundle. -/
def null_profile_cap_branch_bridge_of_self_tax_compatibility
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (compatibility :
      ProfileFamilySelfTaxNoArbitrageCompatibility
        profile_family_of_block source_receipt stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    NullProfileCapBranchBridge where
  profile_family_of_block := profile_family_of_block
  certificate_of_global := certificate_of_global
  threshold_defect_of_family_no_arbitrage := by
    intro B hglobal hfamily
    exact
      threshold_defect_of_profile_family_self_tax_no_arbitrage_compatibility
        compatibility
        threshold_coordinate_receipt_of_global
        B
        hglobal
        (trackb_profile_decomposition_threshold_handoff_source_ready
          source_receipt B hglobal)
        hfamily

/-- Source-aware constructor for the legacy concentration-impact branch
bridge. -/
def concentration_impact_pricing_bridge_of_self_tax_compatibility
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (compatibility :
      ProfileFamilySelfTaxNoArbitrageCompatibility
        profile_family_of_block source_receipt stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    ConcentrationImpactPricingBridge where
  profile_family_of_block := profile_family_of_block
  certificate_of_global := certificate_of_global
  threshold_defect_of_family_no_arbitrage := by
    intro B hglobal hfamily
    exact
      threshold_defect_of_profile_family_self_tax_no_arbitrage_compatibility
        compatibility
        threshold_coordinate_receipt_of_global
        B
        hglobal
        (trackb_profile_decomposition_threshold_handoff_source_ready
          source_receipt B hglobal)
        hfamily

/-- Source-aware constructor for the legacy vanishing branch bridge. -/
def vanishing_pricing_bridge_of_self_tax_compatibility
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (compatibility :
      ProfileFamilySelfTaxNoArbitrageCompatibility
        profile_family_of_block source_receipt stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    VanishingPricingBridge where
  profile_family_of_block := profile_family_of_block
  certificate_of_global := certificate_of_global
  threshold_defect_of_family_no_arbitrage := by
    intro B hglobal hfamily
    exact
      threshold_defect_of_profile_family_self_tax_no_arbitrage_compatibility
        compatibility
        threshold_coordinate_receipt_of_global
        B
        hglobal
        (trackb_profile_decomposition_threshold_handoff_source_ready
          source_receipt B hglobal)
        hfamily

/-- Source-aware constructor for the legacy dichotomy/cross-profile branch
bridge. -/
def dichotomy_cross_profile_bridge_of_self_tax_compatibility
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (priced_fragments :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (compatibility :
      ProfileFamilySelfTaxNoArbitrageCompatibility
        profile_family_of_block source_receipt stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    DichotomyCrossProfileBridge where
  profile_family_of_block := profile_family_of_block
  priced_fragments := priced_fragments
  cross_profile_charged := cross_profile_charged
  threshold_defect_of_family_no_arbitrage := by
    intro B hglobal hfamily
    exact
      threshold_defect_of_profile_family_self_tax_no_arbitrage_compatibility
        compatibility
        threshold_coordinate_receipt_of_global
        B
        hglobal
        (trackb_profile_decomposition_threshold_handoff_source_ready
          source_receipt B hglobal)
        hfamily

/-- Build the same-family Track B profile-decomposition bundle directly from
branch certificates and one source-aware self-tax compatibility theorem.

This is the compressed constructor that the endpoint audit was pointing
toward: the PDE side supplies branch certificates for one fixed profile
family, plus the source compatibility linking that family to the self-tax
stream. The four old branch-level threshold fields are generated
mechanically. -/
def trackb_profile_decomposition_bridge_bundle_of_self_tax_compatibility_and_branch_certificates
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (compatibility :
      ProfileFamilySelfTaxNoArbitrageCompatibility
        profile_family_of_block source_receipt stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
        BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    TrackBProfileDecompositionBridgeBundle :=
  let null_bridge :=
    null_profile_cap_branch_bridge_of_self_tax_compatibility
      profile_family_of_block
      source_receipt
      null_certificate_of_global
      stream_of_block
      compatibility
      threshold_coordinate_receipt_of_global
  let concentration_bridge :=
    concentration_impact_pricing_bridge_of_self_tax_compatibility
      profile_family_of_block
      source_receipt
      concentration_certificate_of_global
      stream_of_block
      compatibility
      threshold_coordinate_receipt_of_global
  let vanishing_bridge :=
    vanishing_pricing_bridge_of_self_tax_compatibility
      profile_family_of_block
      source_receipt
      vanishing_certificate_of_global
      stream_of_block
      compatibility
      threshold_coordinate_receipt_of_global
  let dichotomy_cross_bridge :=
    dichotomy_cross_profile_bridge_of_self_tax_compatibility
      profile_family_of_block
      source_receipt
      priced_fragments_of_global
      cross_profile_charged_of_global
      stream_of_block
      compatibility
      threshold_coordinate_receipt_of_global
  { profile_family_of_block := profile_family_of_block
    source_receipt := source_receipt
    null_bridge := null_bridge
    concentration_bridge := concentration_bridge
    vanishing_bridge := vanishing_bridge
    dichotomy_cross_bridge := dichotomy_cross_bridge
    null_family_matches := rfl
    concentration_family_matches := rfl
    vanishing_family_matches := rfl
    dichotomy_cross_family_matches := rfl
    threshold_handoff_of_family_no_arbitrage := by
      intro B hglobal hsource hfamily
      exact
        threshold_defect_of_profile_family_self_tax_no_arbitrage_compatibility
          compatibility
          threshold_coordinate_receipt_of_global
          B
          hglobal
          hsource
          hfamily }

/-- Exact stream-identity version of
`trackb_profile_decomposition_bridge_bundle_of_self_tax_compatibility_and_branch_certificates`.

The no-arbitrage compatibility is derived internally from exact profile-family
payoff/price identities, so callers cannot provide an unrelated implication
between family no-arbitrage and the self-tax stream. -/
def trackb_profile_decomposition_bridge_bundle_of_self_tax_stream_identities_and_branch_certificates
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    TrackBProfileDecompositionBridgeBundle :=
  trackb_profile_decomposition_bridge_bundle_of_self_tax_compatibility_and_branch_certificates
    profile_family_of_block
    source_receipt
    null_certificate_of_global
    concentration_certificate_of_global
    vanishing_certificate_of_global
    priced_fragments_of_global
    cross_profile_charged_of_global
    stream_of_block
    (profile_family_self_tax_no_arbitrage_compatibility_of_stream_identities
      (profile_source_receipt := source_receipt)
      identities)
    threshold_coordinate_receipt_of_global

/-- Inequality-level version of
`trackb_profile_decomposition_bridge_bundle_of_self_tax_stream_identities_and_branch_certificates`.

This is the lower-semicontinuity-friendly route: the PDE side may supply
payoff and price bounds instead of exact endpoint identities, while all branch
certificates and source guards remain unchanged. -/
def trackb_profile_decomposition_bridge_bundle_of_payoff_price_bounds_and_branch_certificates
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (not_residual_only :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        ¬ ((profile_family_of_block B).profiles = [] ∧
            (profile_family_of_block B).residualPayoff =
              (stream_of_block B).payoffLimit ∧
            (profile_family_of_block B).residualPrice =
              leraySelfTaxLimitPrice (stream_of_block B)))
    (limit_payoff_le_family_payoff :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        (stream_of_block B).payoffLimit ≤
          familyPayoff (profile_family_of_block B))
    (family_price_le_limit_price :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        familyPrice (profile_family_of_block B) ≤
          leraySelfTaxLimitPrice (stream_of_block B))
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    TrackBProfileDecompositionBridgeBundle :=
  trackb_profile_decomposition_bridge_bundle_of_self_tax_compatibility_and_branch_certificates
    profile_family_of_block
    source_receipt
    null_certificate_of_global
    concentration_certificate_of_global
    vanishing_certificate_of_global
    priced_fragments_of_global
    cross_profile_charged_of_global
    stream_of_block
    (profile_family_self_tax_no_arbitrage_compatibility_of_payoff_price_bounds
      (profile_source_receipt := source_receipt)
      profile_family_and_stream_declared_together
      profile_family_and_stream_declared_together_paid
      not_residual_only
      limit_payoff_le_family_payoff
      family_price_le_limit_price)
    threshold_coordinate_receipt_of_global

/-- Direct decomposition obligation from branch certificates and exact
profile-family/self-tax stream identities. -/
def trackb_profile_decomposition_obligation_of_self_tax_stream_identities_and_branch_certificates
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    TrackBProfileDecompositionObligation := by
  let Bun :=
    trackb_profile_decomposition_bridge_bundle_of_self_tax_stream_identities_and_branch_certificates
      profile_family_of_block
      source_receipt
      null_certificate_of_global
      concentration_certificate_of_global
      vanishing_certificate_of_global
      priced_fragments_of_global
      cross_profile_charged_of_global
      stream_of_block
      identities
      threshold_coordinate_receipt_of_global
  exact trackb_profile_decomposition_obligation_of_bridge_bundle Bun

/-- Direct decomposition obligation from branch certificates plus payoff/price
bounds into the self-tax stream. -/
def trackb_profile_decomposition_obligation_of_payoff_price_bounds_and_branch_certificates
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (not_residual_only :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        ¬ ((profile_family_of_block B).profiles = [] ∧
            (profile_family_of_block B).residualPayoff =
              (stream_of_block B).payoffLimit ∧
            (profile_family_of_block B).residualPrice =
              leraySelfTaxLimitPrice (stream_of_block B)))
    (limit_payoff_le_family_payoff :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        (stream_of_block B).payoffLimit ≤
          familyPayoff (profile_family_of_block B))
    (family_price_le_limit_price :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        familyPrice (profile_family_of_block B) ≤
          leraySelfTaxLimitPrice (stream_of_block B))
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    TrackBProfileDecompositionObligation := by
  let Bun :=
    trackb_profile_decomposition_bridge_bundle_of_payoff_price_bounds_and_branch_certificates
      profile_family_of_block
      source_receipt
      null_certificate_of_global
      concentration_certificate_of_global
      vanishing_certificate_of_global
      priced_fragments_of_global
      cross_profile_charged_of_global
      stream_of_block
      profile_family_and_stream_declared_together
      profile_family_and_stream_declared_together_paid
      not_residual_only
      limit_payoff_le_family_payoff
      family_price_le_limit_price
      threshold_coordinate_receipt_of_global
  exact trackb_profile_decomposition_obligation_of_bridge_bundle Bun

/-- Constructor for a same-family Track B profile-decomposition bundle when the
threshold handoff is supplied by profile-family/self-tax compatibility.

The four branch bridges still prove the family no-arbitrage inputs.  The new
compatibility field is used only for the final handoff from that same family
no-arbitrage into the self-tax threshold-coordinate route. -/
def trackb_profile_decomposition_bridge_bundle_of_self_tax_compatibility
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_bridge : NullProfileCapBranchBridge)
    (concentration_bridge : ConcentrationImpactPricingBridge)
    (vanishing_bridge : VanishingPricingBridge)
    (dichotomy_cross_bridge : DichotomyCrossProfileBridge)
    (null_family_matches :
      null_bridge.profile_family_of_block = profile_family_of_block)
    (concentration_family_matches :
      concentration_bridge.profile_family_of_block = profile_family_of_block)
    (vanishing_family_matches :
      vanishing_bridge.profile_family_of_block = profile_family_of_block)
    (dichotomy_cross_family_matches :
      dichotomy_cross_bridge.profile_family_of_block =
        profile_family_of_block)
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (compatibility :
      ProfileFamilySelfTaxNoArbitrageCompatibility
        profile_family_of_block source_receipt stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    TrackBProfileDecompositionBridgeBundle where
  profile_family_of_block := profile_family_of_block
  source_receipt := source_receipt
  null_bridge := null_bridge
  concentration_bridge := concentration_bridge
  vanishing_bridge := vanishing_bridge
  dichotomy_cross_bridge := dichotomy_cross_bridge
  null_family_matches := null_family_matches
  concentration_family_matches := concentration_family_matches
  vanishing_family_matches := vanishing_family_matches
  dichotomy_cross_family_matches := dichotomy_cross_family_matches
  threshold_handoff_of_family_no_arbitrage := by
    intro B hglobal hsource hfamily
    exact
      threshold_defect_of_profile_family_self_tax_no_arbitrage_compatibility
        compatibility
        threshold_coordinate_receipt_of_global
        B
        hglobal
        hsource
        hfamily

/-- Identity-level constructor for a Track B profile-decomposition bundle.

This is the preferred PDE-facing constructor: exact profile-family/self-tax
stream identities are supplied, and the weaker no-arbitrage compatibility is
derived internally. -/
def trackb_profile_decomposition_bridge_bundle_of_self_tax_stream_identities
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_bridge : NullProfileCapBranchBridge)
    (concentration_bridge : ConcentrationImpactPricingBridge)
    (vanishing_bridge : VanishingPricingBridge)
    (dichotomy_cross_bridge : DichotomyCrossProfileBridge)
    (null_family_matches :
      null_bridge.profile_family_of_block = profile_family_of_block)
    (concentration_family_matches :
      concentration_bridge.profile_family_of_block = profile_family_of_block)
    (vanishing_family_matches :
      vanishing_bridge.profile_family_of_block = profile_family_of_block)
    (dichotomy_cross_family_matches :
      dichotomy_cross_bridge.profile_family_of_block =
        profile_family_of_block)
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    TrackBProfileDecompositionBridgeBundle :=
  trackb_profile_decomposition_bridge_bundle_of_self_tax_compatibility
    profile_family_of_block
    source_receipt
    null_bridge
    concentration_bridge
    vanishing_bridge
    dichotomy_cross_bridge
    null_family_matches
    concentration_family_matches
    vanishing_family_matches
    dichotomy_cross_family_matches
    stream_of_block
    (profile_family_self_tax_no_arbitrage_compatibility_of_stream_identities
      (profile_source_receipt := source_receipt)
      identities)
    threshold_coordinate_receipt_of_global

/-- Build the profile-decomposition bridge directly from an output-derived
Leray self-tax block bridge plus exact profile-family/self-tax identities.

This is the preferred source route when the self-tax stream is already carried
by `LeraySelfTaxProfileOutputDerivedComponentLimitBridge`: the threshold
coordinate receipts are read from that bridge, so profile decomposition cannot
silently switch to a different self-tax endpoint. -/
def trackb_profile_decomposition_bridge_bundle_of_output_derived_stream_identities
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_bridge : NullProfileCapBranchBridge)
    (concentration_bridge : ConcentrationImpactPricingBridge)
    (vanishing_bridge : VanishingPricingBridge)
    (dichotomy_cross_bridge : DichotomyCrossProfileBridge)
    (null_family_matches :
      null_bridge.profile_family_of_block = profile_family_of_block)
    (concentration_family_matches :
      concentration_bridge.profile_family_of_block = profile_family_of_block)
    (vanishing_family_matches :
      vanishing_bridge.profile_family_of_block = profile_family_of_block)
    (dichotomy_cross_family_matches :
      dichotomy_cross_bridge.profile_family_of_block =
        profile_family_of_block)
    (bridge : LeraySelfTaxProfileOutputDerivedComponentLimitBridge)
    (identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block bridge.stream_of_block) :
    TrackBProfileDecompositionBridgeBundle :=
  trackb_profile_decomposition_bridge_bundle_of_self_tax_stream_identities
    profile_family_of_block
    source_receipt
    null_bridge
    concentration_bridge
    vanishing_bridge
    dichotomy_cross_bridge
    null_family_matches
    concentration_family_matches
    vanishing_family_matches
    dichotomy_cross_family_matches
    bridge.stream_of_block
    identities
    bridge.threshold_coordinate_receipt_of_global

/-- Direct obligation constructor from profile-family/self-tax compatibility.

This removes one manual hop in the closure path while preserving the same
source discipline: the final threshold handoff is still routed through
`ProfileFamilySelfTaxNoArbitrageCompatibility`, not through an older raw branch
field that ignores the Track B source receipt. -/
def trackb_profile_decomposition_obligation_of_self_tax_compatibility
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_bridge : NullProfileCapBranchBridge)
    (concentration_bridge : ConcentrationImpactPricingBridge)
    (vanishing_bridge : VanishingPricingBridge)
    (dichotomy_cross_bridge : DichotomyCrossProfileBridge)
    (null_family_matches :
      null_bridge.profile_family_of_block = profile_family_of_block)
    (concentration_family_matches :
      concentration_bridge.profile_family_of_block = profile_family_of_block)
    (vanishing_family_matches :
      vanishing_bridge.profile_family_of_block = profile_family_of_block)
    (dichotomy_cross_family_matches :
      dichotomy_cross_bridge.profile_family_of_block =
        profile_family_of_block)
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (compatibility :
      ProfileFamilySelfTaxNoArbitrageCompatibility
        profile_family_of_block source_receipt stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_bridge_bundle
    (trackb_profile_decomposition_bridge_bundle_of_self_tax_compatibility
      profile_family_of_block
      source_receipt
      null_bridge
      concentration_bridge
      vanishing_bridge
      dichotomy_cross_bridge
      null_family_matches
      concentration_family_matches
      vanishing_family_matches
      dichotomy_cross_family_matches
      stream_of_block
      compatibility
      threshold_coordinate_receipt_of_global)

/-- Direct obligation constructor from exact profile-family/self-tax stream
identities. This is the preferred PDE-facing entry point for the decomposition
target because the weaker no-arbitrage compatibility is derived internally. -/
def trackb_profile_decomposition_obligation_of_self_tax_stream_identities
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_bridge : NullProfileCapBranchBridge)
    (concentration_bridge : ConcentrationImpactPricingBridge)
    (vanishing_bridge : VanishingPricingBridge)
    (dichotomy_cross_bridge : DichotomyCrossProfileBridge)
    (null_family_matches :
      null_bridge.profile_family_of_block = profile_family_of_block)
    (concentration_family_matches :
      concentration_bridge.profile_family_of_block = profile_family_of_block)
    (vanishing_family_matches :
      vanishing_bridge.profile_family_of_block = profile_family_of_block)
    (dichotomy_cross_family_matches :
      dichotomy_cross_bridge.profile_family_of_block =
        profile_family_of_block)
    (stream_of_block :
      FullLedgerBlock → LeraySelfTaxProfilePriceStream)
    (identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block stream_of_block)
    (threshold_coordinate_receipt_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          BranchSelfTaxThresholdCoordinateIdentities
            B
            (stream_of_block B)) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_bridge_bundle
    (trackb_profile_decomposition_bridge_bundle_of_self_tax_stream_identities
      profile_family_of_block
      source_receipt
      null_bridge
      concentration_bridge
      vanishing_bridge
      dichotomy_cross_bridge
      null_family_matches
      concentration_family_matches
      vanishing_family_matches
      dichotomy_cross_family_matches
      stream_of_block
      identities
      threshold_coordinate_receipt_of_global)

/-- Direct obligation constructor from an output-derived self-tax bridge plus
profile-family/self-tax identities. The threshold coordinates are inherited
from the output-derived bridge, so this constructor prevents the profile
decomposition route from switching endpoints at the final handoff. -/
def trackb_profile_decomposition_obligation_of_output_derived_stream_identities
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_bridge : NullProfileCapBranchBridge)
    (concentration_bridge : ConcentrationImpactPricingBridge)
    (vanishing_bridge : VanishingPricingBridge)
    (dichotomy_cross_bridge : DichotomyCrossProfileBridge)
    (null_family_matches :
      null_bridge.profile_family_of_block = profile_family_of_block)
    (concentration_family_matches :
      concentration_bridge.profile_family_of_block = profile_family_of_block)
    (vanishing_family_matches :
      vanishing_bridge.profile_family_of_block = profile_family_of_block)
    (dichotomy_cross_family_matches :
      dichotomy_cross_bridge.profile_family_of_block =
        profile_family_of_block)
    (bridge : LeraySelfTaxProfileOutputDerivedComponentLimitBridge)
    (identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block bridge.stream_of_block) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_bridge_bundle
    (trackb_profile_decomposition_bridge_bundle_of_output_derived_stream_identities
      profile_family_of_block
      source_receipt
      null_bridge
      concentration_bridge
      vanishing_bridge
      dichotomy_cross_bridge
      null_family_matches
      concentration_family_matches
      vanishing_family_matches
      dichotomy_cross_family_matches
      bridge
      identities)

/-- Direct decomposition obligation from the noncircular Young/defect
stream-family source.

This is the shortest current PDE-facing corridor for the decomposition target:
instantiate the fixed profile family, the four same-family branch bridges, the
noncircular measure-valued self-tax stream family, and the exact
profile-family/self-tax identities. The output-derived bridge and final
threshold handoff are then mechanical projections from those source objects. -/
def trackb_profile_decomposition_obligation_of_noncircular_mv_stream_family_source
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_bridge : NullProfileCapBranchBridge)
    (concentration_bridge : ConcentrationImpactPricingBridge)
    (vanishing_bridge : VanishingPricingBridge)
    (dichotomy_cross_bridge : DichotomyCrossProfileBridge)
    (null_family_matches :
      null_bridge.profile_family_of_block = profile_family_of_block)
    (concentration_family_matches :
      concentration_bridge.profile_family_of_block = profile_family_of_block)
    (vanishing_family_matches :
      vanishing_bridge.profile_family_of_block = profile_family_of_block)
    (dichotomy_cross_family_matches :
      dichotomy_cross_bridge.profile_family_of_block =
        profile_family_of_block)
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block source.stream_of_block) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_output_derived_stream_identities
    profile_family_of_block
    source_receipt
    null_bridge
    concentration_bridge
    vanishing_bridge
    dichotomy_cross_bridge
    null_family_matches
    concentration_family_matches
    vanishing_family_matches
    dichotomy_cross_family_matches
    (leray_self_tax_profile_output_derived_bridge_of_noncircular_mv_stream_family_source
      source)
    identities

/-- Direct decomposition obligation from branch certificates plus the
noncircular Young/defect stream-family source.

This is the most compressed source-aware constructor currently available for
the profile-decomposition target: no legacy branch bridge and no standalone
threshold handoff is supplied by the caller. Both are generated from the same
fixed profile family, the same branch certificates, and the same noncircular
self-tax stream source. -/
def trackb_profile_decomposition_obligation_of_noncircular_mv_source_and_branch_certificates
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (identities :
      ProfileFamilySelfTaxStreamIdentityCompatibility
        profile_family_of_block source.stream_of_block) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_self_tax_stream_identities_and_branch_certificates
    profile_family_of_block
    source_receipt
    null_certificate_of_global
    concentration_certificate_of_global
    vanishing_certificate_of_global
    priced_fragments_of_global
    cross_profile_charged_of_global
    source.stream_of_block
    identities
    source.threshold_coordinate_receipt_of_global

/-- Direct profile-decomposition bridge bundle from branch certificates plus a
named noncircular measure-valued scalar-alignment source.

This is the Young/defect analogue of the continuum scalar-alignment
constructor: exact profile-family/self-tax identities are derived internally
from the noncircular alignment source, with the residual-only shortcut ruled
out by the alignment source's profile-membership field. -/
def trackb_profile_decomposition_bridge_bundle_of_noncircular_mv_scalar_alignment_source_and_branch_certificates
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (alignment :
      NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
        profile_family_of_block source) :
    TrackBProfileDecompositionBridgeBundle :=
  trackb_profile_decomposition_bridge_bundle_of_self_tax_stream_identities_and_branch_certificates
    profile_family_of_block
    source_receipt
    null_certificate_of_global
    concentration_certificate_of_global
    vanishing_certificate_of_global
    priced_fragments_of_global
    cross_profile_charged_of_global
    source.stream_of_block
    (profile_family_self_tax_stream_identity_compatibility_of_noncircular_mv_scalar_alignment_source
      alignment)
    source.threshold_coordinate_receipt_of_global

/-- Direct decomposition obligation from branch certificates plus a named
noncircular measure-valued scalar-alignment source. -/
def trackb_profile_decomposition_obligation_of_noncircular_mv_scalar_alignment_source_and_branch_certificates
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (source :
      LeraySelfTaxNoncircularMeasureValuedProfilePriceStreamFamilySource)
    (alignment :
      NoncircularMeasureValuedProfileFamilyScalarAlignmentSource
        profile_family_of_block source) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_bridge_bundle
    (trackb_profile_decomposition_bridge_bundle_of_noncircular_mv_scalar_alignment_source_and_branch_certificates
      profile_family_of_block
      source_receipt
      null_certificate_of_global
      concentration_certificate_of_global
      vanishing_certificate_of_global
      priced_fragments_of_global
      cross_profile_charged_of_global
      source
      alignment)

/-- Direct profile-decomposition bridge bundle from branch certificates plus a
continuum all-output LP/Bony stream-family source.

This exposes the same continuum source corridor as an intermediate
`TrackBProfileDecompositionBridgeBundle`, so downstream receipts that need the
bundle itself do not have to reconstruct the four branch bridges separately.
The exact profile-family/self-tax stream identities are derived internally
from the continuum source, a genuine profile-membership witness, and the two
family-to-continuum scalar equalities. -/
def trackb_profile_decomposition_bridge_bundle_of_continuum_all_output_source_and_branch_certificates
    {τ : ContinuumLPProfileTopology.{u}}
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (profile_mem_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        ∃ P : PricingProfile, P ∈ (profile_family_of_block B).profiles)
    (family_payoff_matches_continuum :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPayoff (profile_family_of_block B) =
          (source.all_output_source_of_global B hglobal).stream.smoothCandidatePayoff)
    (family_price_matches_continuum :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPrice (profile_family_of_block B) =
          continuumGlobalSelfTaxTarget
            (source.all_output_source_of_global B hglobal).stream) :
    TrackBProfileDecompositionBridgeBundle :=
  trackb_profile_decomposition_bridge_bundle_of_self_tax_stream_identities_and_branch_certificates
    profile_family_of_block
    source_receipt
    null_certificate_of_global
    concentration_certificate_of_global
    vanishing_certificate_of_global
    priced_fragments_of_global
    cross_profile_charged_of_global
    source.stream_of_block
    (profile_family_self_tax_stream_identity_compatibility_of_continuum_all_output_family_source
      source
      profile_family_and_stream_declared_together
      profile_family_and_stream_declared_together_paid
      profile_mem_of_global
      family_payoff_matches_continuum
      family_price_matches_continuum)
    source.threshold_coordinate_receipt_of_global

/-- Direct decomposition obligation from branch certificates plus a continuum
all-output LP/Bony stream-family source.

This is the continuum analogue of
`trackb_profile_decomposition_obligation_of_noncircular_mv_source_and_branch_certificates`.
The PDE side supplies one fixed profile family, branch certificates, one
continuum all-output self-tax source, a genuine profile-membership witness, and
the two scalar equalities tying the family payoff/price to the continuum
smooth payoff/global target.  The exact self-tax stream identities are built
inside the constructor, with the residual-only shortcut ruled out by
`profile_mem_of_global`. -/
def trackb_profile_decomposition_obligation_of_continuum_all_output_source_and_branch_certificates
    {τ : ContinuumLPProfileTopology.{u}}
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (profile_mem_of_global :
      ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B →
        ∃ P : PricingProfile, P ∈ (profile_family_of_block B).profiles)
    (family_payoff_matches_continuum :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPayoff (profile_family_of_block B) =
          (source.all_output_source_of_global B hglobal).stream.smoothCandidatePayoff)
    (family_price_matches_continuum :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        familyPrice (profile_family_of_block B) =
          continuumGlobalSelfTaxTarget
            (source.all_output_source_of_global B hglobal).stream) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_bridge_bundle
    (trackb_profile_decomposition_bridge_bundle_of_continuum_all_output_source_and_branch_certificates
      profile_family_of_block
      source_receipt
      null_certificate_of_global
      concentration_certificate_of_global
      vanishing_certificate_of_global
      priced_fragments_of_global
      cross_profile_charged_of_global
      source
      profile_family_and_stream_declared_together
      profile_family_and_stream_declared_together_paid
      profile_mem_of_global
      family_payoff_matches_continuum
      family_price_matches_continuum)

/-- Direct profile-decomposition bridge bundle from branch certificates plus a
named continuum scalar-alignment source.

This is the preferred compressed entry point after the scalar-alignment witness
has been identified.  It avoids passing the profile-membership witness and two
field-level equalities as loose arguments, while preserving exactly the same
source burden. -/
def trackb_profile_decomposition_bridge_bundle_of_continuum_scalar_alignment_source_and_branch_certificates
    {τ : ContinuumLPProfileTopology.{u}}
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (alignment :
      ContinuumProfileFamilyScalarAlignmentSource
        profile_family_of_block source) :
    TrackBProfileDecompositionBridgeBundle :=
  trackb_profile_decomposition_bridge_bundle_of_continuum_all_output_source_and_branch_certificates
    profile_family_of_block
    source_receipt
    null_certificate_of_global
    concentration_certificate_of_global
    vanishing_certificate_of_global
    priced_fragments_of_global
    cross_profile_charged_of_global
    source
    alignment.profile_family_and_stream_declared_together
    alignment.profile_family_and_stream_declared_together_paid
    alignment.profile_mem_of_global
    alignment.family_payoff_matches_continuum
    alignment.family_price_matches_continuum

/-- Direct decomposition obligation from branch certificates plus a named
continuum scalar-alignment source. -/
def trackb_profile_decomposition_obligation_of_continuum_scalar_alignment_source_and_branch_certificates
    {τ : ContinuumLPProfileTopology.{u}}
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (alignment :
      ContinuumProfileFamilyScalarAlignmentSource
        profile_family_of_block source) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_bridge_bundle
    (trackb_profile_decomposition_bridge_bundle_of_continuum_scalar_alignment_source_and_branch_certificates
      profile_family_of_block
      source_receipt
      null_certificate_of_global
      concentration_certificate_of_global
      vanishing_certificate_of_global
      priced_fragments_of_global
      cross_profile_charged_of_global
      source
      alignment)

/-- Direct profile-decomposition bridge bundle from branch certificates plus a
continuum LP-prefix endpoint-identification source.

This is the finite-prefix sniper form of the continuum profile route: the
profile family is forced to be the declared LP prefix, the positive-prefix and
endpoint-identification facts are bundled in one generic source object, and
the continuum all-output source still supplies the projected self-tax stream. -/
noncomputable def trackb_profile_decomposition_bridge_bundle_of_continuum_lp_endpoint_source_and_branch_certificates
    {τ : ContinuumLPProfileTopology.{u}}
    (lp_stream_of_block : FullLedgerBlock → LPShellPricingStream)
    (prefix_len_of_block : FullLedgerBlock → ℕ)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt
        (fun B =>
          lpPrefixProfileFamily
            (lp_stream_of_block B) (prefix_len_of_block B)))
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)))
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (endpoint_source :
      LPPrefixEndpointIdentificationSource
        IsGlobalTrackBBlock
        lp_stream_of_block
        prefix_len_of_block
        (continuumAllOutputPayoffEndpointOfGlobal source)
        (continuumAllOutputPriceEndpointOfGlobal source)) :
    TrackBProfileDecompositionBridgeBundle :=
  trackb_profile_decomposition_bridge_bundle_of_continuum_scalar_alignment_source_and_branch_certificates
    (fun B =>
      lpPrefixProfileFamily
        (lp_stream_of_block B) (prefix_len_of_block B))
    source_receipt
    null_certificate_of_global
    concentration_certificate_of_global
    vanishing_certificate_of_global
    priced_fragments_of_global
    cross_profile_charged_of_global
    source
    (continuum_scalar_alignment_source_of_lp_endpoint_identification_source
      lp_stream_of_block
      prefix_len_of_block
      profile_family_and_stream_declared_together
      profile_family_and_stream_declared_together_paid
      endpoint_source)

/-- Direct profile-decomposition obligation from branch certificates plus a
continuum LP-prefix endpoint-identification source. -/
noncomputable def trackb_profile_decomposition_obligation_of_continuum_lp_endpoint_source_and_branch_certificates
    {τ : ContinuumLPProfileTopology.{u}}
    (lp_stream_of_block : FullLedgerBlock → LPShellPricingStream)
    (prefix_len_of_block : FullLedgerBlock → ℕ)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt
        (fun B =>
          lpPrefixProfileFamily
            (lp_stream_of_block B) (prefix_len_of_block B)))
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate
            (lpPrefixProfileFamily
              (lp_stream_of_block B) (prefix_len_of_block B)))
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (profile_family_and_stream_declared_together :
      ∀ _B : FullLedgerBlock, IsGlobalTrackBBlock _B → Prop)
    (profile_family_and_stream_declared_together_paid :
      ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
        profile_family_and_stream_declared_together B hglobal)
    (endpoint_source :
      LPPrefixEndpointIdentificationSource
        IsGlobalTrackBBlock
        lp_stream_of_block
        prefix_len_of_block
        (continuumAllOutputPayoffEndpointOfGlobal source)
        (continuumAllOutputPriceEndpointOfGlobal source)) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_bridge_bundle
    (trackb_profile_decomposition_bridge_bundle_of_continuum_lp_endpoint_source_and_branch_certificates
      lp_stream_of_block
      prefix_len_of_block
      source_receipt
      null_certificate_of_global
      concentration_certificate_of_global
      vanishing_certificate_of_global
      priced_fragments_of_global
      cross_profile_charged_of_global
      source
      profile_family_and_stream_declared_together
      profile_family_and_stream_declared_together_paid
      endpoint_source)

/-- Direct profile-decomposition bridge bundle from branch certificates plus a
named continuum inequality-alignment source.

This is the lower-semicontinuity-friendly continuum entry point: branch
certificates still prove the profile-family no-arbitrage inputs, while the
continuum source supplies only the payoff/price inequalities needed to feed
that same no-arbitrage into the projected self-tax stream. -/
def trackb_profile_decomposition_bridge_bundle_of_continuum_inequality_alignment_source_and_branch_certificates
    {τ : ContinuumLPProfileTopology.{u}}
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (alignment :
      ContinuumProfileFamilyInequalityAlignmentSource
        profile_family_of_block source) :
    TrackBProfileDecompositionBridgeBundle :=
  trackb_profile_decomposition_bridge_bundle_of_self_tax_compatibility_and_branch_certificates
    profile_family_of_block
    source_receipt
    null_certificate_of_global
    concentration_certificate_of_global
    vanishing_certificate_of_global
    priced_fragments_of_global
    cross_profile_charged_of_global
    source.stream_of_block
    (profile_family_self_tax_no_arbitrage_compatibility_of_continuum_inequality_alignment_source
      (profile_source_receipt := source_receipt)
      alignment)
    source.threshold_coordinate_receipt_of_global

/-- Direct decomposition obligation from branch certificates plus a named
continuum inequality-alignment source. -/
def trackb_profile_decomposition_obligation_of_continuum_inequality_alignment_source_and_branch_certificates
    {τ : ContinuumLPProfileTopology.{u}}
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily)
    (source_receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (null_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          NullProfileCapBranchCertificate (profile_family_of_block B))
    (concentration_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          ConcentrationImpactFamilyCertificate (profile_family_of_block B))
    (vanishing_certificate_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          VanishingFamilyCertificate (profile_family_of_block B))
    (priced_fragments_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          PricedFragmentCertificate (profile_family_of_block B))
    (cross_profile_charged_of_global :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          CrossProfileRecombinationCertificate (profile_family_of_block B))
    (source :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (alignment :
      ContinuumProfileFamilyInequalityAlignmentSource
        profile_family_of_block source) :
    TrackBProfileDecompositionObligation :=
  trackb_profile_decomposition_obligation_of_bridge_bundle
    (trackb_profile_decomposition_bridge_bundle_of_continuum_inequality_alignment_source_and_branch_certificates
      profile_family_of_block
      source_receipt
      null_certificate_of_global
      concentration_certificate_of_global
      vanishing_certificate_of_global
      priced_fragments_of_global
      cross_profile_charged_of_global
      source
      alignment)

/-- Legacy component-limit view of a source-derived block bridge.

Older consumers can use this adapter at the component-limit API boundary,
while the source-derived bridge remains the preferred object for final
receipts that need audited output-source provenance and substitution guards.
-/
def leray_self_tax_profile_component_limit_bridge_of_output_derived
    (bridge : LeraySelfTaxProfileOutputDerivedComponentLimitBridge) :
    LeraySelfTaxProfileComponentLimitBridge where
  stream_of_block := bridge.stream_of_block
  component_limit_passage_of_global := by
    intro B hglobal
    exact
      component_limit_passage_of_output_derived
        (bridge.stream_of_block B)
        (bridge.output_derived_component_limit_passage_of_global
          B hglobal)
  threshold_coordinate_receipt_of_global :=
    bridge.threshold_coordinate_receipt_of_global

/-- Conditional Track B handoff for the Leray self-tax/profile LSC bridge. -/
theorem threshold_defect_of_leray_self_tax_profile_lsc_bridge
    (bridge : LeraySelfTaxProfileLSCBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ThresholdDefectConvexity B := by
  have hlimit :
      (bridge.stream_of_block B).payoffLimit ≤
        leraySelfTaxLimitPrice (bridge.stream_of_block B) :=
    no_global_self_tax_arbitrage_of_profile_lsc_receipt
      (bridge.stream_of_block B)
      (bridge.receipt_of_global B hglobal)
  exact
    threshold_defect_of_branch_self_tax_threshold_coordinate_receipt
      B
      (bridge.stream_of_block B)
      (branch_self_tax_threshold_coordinate_receipt_of_identities
        B
        (bridge.stream_of_block B)
        (bridge.threshold_coordinate_receipt_of_global B hglobal))
      hlimit

/-- Conditional Track B handoff through the explicit component-limit-passage
bridge. -/
theorem threshold_defect_of_leray_self_tax_profile_component_limit_bridge
    (bridge : LeraySelfTaxProfileComponentLimitBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ThresholdDefectConvexity B := by
  have hlimit :
      (bridge.stream_of_block B).payoffLimit ≤
        leraySelfTaxLimitPrice (bridge.stream_of_block B) :=
    no_global_self_tax_arbitrage_of_component_limit_passage
      (bridge.stream_of_block B)
      (bridge.component_limit_passage_of_global B hglobal)
  exact
    threshold_defect_of_branch_self_tax_threshold_coordinate_receipt
      B
      (bridge.stream_of_block B)
      (branch_self_tax_threshold_coordinate_receipt_of_identities
        B
        (bridge.stream_of_block B)
        (bridge.threshold_coordinate_receipt_of_global B hglobal))
      hlimit

/-- Conditional Track B handoff through the source-derived explicit
component-limit bridge. -/
theorem threshold_defect_of_leray_self_tax_profile_output_derived_component_limit_bridge
    (bridge : LeraySelfTaxProfileOutputDerivedComponentLimitBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ThresholdDefectConvexity B := by
  have hlimit :
      (bridge.stream_of_block B).payoffLimit ≤
        leraySelfTaxLimitPrice (bridge.stream_of_block B) :=
    no_global_self_tax_arbitrage_of_output_derived_component_limit_passage
      (bridge.stream_of_block B)
      (bridge.output_derived_component_limit_passage_of_global B hglobal)
  exact
    threshold_defect_of_branch_self_tax_threshold_coordinate_receipt
      B
      (bridge.stream_of_block B)
      (branch_self_tax_threshold_coordinate_receipt_of_identities
        B
        (bridge.stream_of_block B)
        (bridge.threshold_coordinate_receipt_of_global B hglobal))
      hlimit

/-- Endpoint-sourced version of the output-derived Track B handoff.

This theorem makes the upstream `TrackBSelfTaxLimitEndpoint` spine
load-bearing for the concrete Leray stream: the endpoint receipt supplies only
source-ready limit no-arbitrage, and the downstream threshold-coordinate
identity supplies the same-block threshold ledger. -/
theorem threshold_defect_of_leray_self_tax_profile_output_derived_endpoint
    (bridge : LeraySelfTaxProfileOutputDerivedComponentLimitBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ThresholdDefectConvexity B :=
  threshold_defect_of_leray_self_tax_output_derived_endpoint_and_threshold_identities
    B
    (bridge.stream_of_block B)
    (bridge.output_derived_component_limit_passage_of_global B hglobal)
    (bridge.threshold_coordinate_receipt_of_global B hglobal)

/-- Conditional Track B no-survivor handoff for the Leray self-tax/profile LSC
bridge. -/
theorem no_global_survivor_of_leray_self_tax_profile_lsc_bridge
    (bridge : LeraySelfTaxProfileLSCBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hprojection : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (threshold_defect_of_leray_self_tax_profile_lsc_bridge
      bridge B hglobal)

/-- Conditional Track B no-survivor handoff for the explicit
component-limit-passage bridge. -/
theorem no_global_survivor_of_leray_self_tax_profile_component_limit_bridge
    (bridge : LeraySelfTaxProfileComponentLimitBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hprojection : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (threshold_defect_of_leray_self_tax_profile_component_limit_bridge
      bridge B hglobal)

/-- Conditional Track B no-survivor handoff for the source-derived
component-limit bridge. -/
theorem no_global_survivor_of_leray_self_tax_profile_output_derived_component_limit_bridge
    (bridge : LeraySelfTaxProfileOutputDerivedComponentLimitBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hprojection : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (threshold_defect_of_leray_self_tax_profile_output_derived_component_limit_bridge
      bridge B hglobal)

/-- Conditional Track B no-survivor handoff through the upstream endpoint
surface, preserving the audited output-derived self-tax provenance. -/
theorem no_global_survivor_of_leray_self_tax_profile_output_derived_endpoint
    (bridge : LeraySelfTaxProfileOutputDerivedComponentLimitBridge)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hprojection : QuarticSurvivalProjectionReceipt B) :
    FullLedgerNoSurvivor B := by
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    (threshold_defect_of_leray_self_tax_profile_output_derived_endpoint
      bridge B hglobal)

/-- Negative receipt after the 2026-05-09 route audit: a purely Leray/`L²`
tail cannot certify vanishing of any genuinely scale-critical price. The
route dies by topology mismatch before the profile bookkeeping even starts. -/
structure RawLerayTailCriticalPriceObstruction where
  scaling_hides_critical_bubble_from_L2_tail : Prop
  therefore_raw_leray_tail_smallness_cannot_price_critical_tail : Prop

/-- Constructor theorem name for the scaling/topology mismatch that kills the
raw Leray/L² interpretation of `LeraySelfTaxProfilePriceStream`. -/
theorem raw_leray_tail_cannot_control_critical_price :
    Nonempty RawLerayTailCriticalPriceObstruction := by
  refine ⟨{
    scaling_hides_critical_bubble_from_L2_tail := True
    therefore_raw_leray_tail_smallness_cannot_price_critical_tail := True
  }⟩

/-- The current sharper bottleneck from the graph-anchored external attack is
not tail decay itself but the existence of actual signed localized interaction
coefficients for the Navier-Stokes price stream. -/
structure LocalizedSignedPriceInteraction where
  interactionIsIndexedByProfileHyperedge : Prop
  coefficientMayHaveEitherSign : Prop
  localizationUsesActualCutoffGeometry : Prop
  timeWindowCompatibilityIsTracked : Prop
  generatedByActualNSPriceStream : Prop

/-- The super-mega route reduction says the price stream cannot stay a single
opaque object. The signed self-tax family is the first component that must be
realized before any absolute envelope can be assessed. -/
structure SignedSelfTaxInteractionFamily where
  interactionsAreActuallyProducedByTheNSPriceStream : Prop
  eachInteractionLivesOnASingleProfileHyperedge : Prop
  localizationAndTimeWindowDataAreTracked : Prop

/-- The signed cross-defect family is the second concrete component. This is
where bilinear Schur structure would eventually need to attach. -/
structure SignedCrossDefectInteractionFamily where
  interactionsAreActuallyProducedByTheNSPriceStream : Prop
  eachInteractionLivesOnATwoProfileHyperedge : Prop
  localizationAndTimeWindowDataAreTracked : Prop

/-- The signed coherence family is the third concrete component. This is where
the eventual multilinear Carleson burden should attach. -/
structure SignedCoherenceInteractionFamily where
  interactionsAreActuallyProducedByTheNSPriceStream : Prop
  eachInteractionLivesOnAHigherProfileHyperedge : Prop
  localizationAndTimeWindowDataAreTracked : Prop

/-- Earliest positive seam currently visible on this route: before we ask for
componentwise envelopes, we need a noncircular localized assignment of the
signed price stream into self-tax / cross-defect / coherence families. -/
structure LocalizedPriceStreamComponentAssignmentReceipt where
  decomposition : NSCriticalProfileDecomposition
  aggregateSignedPriceStreamExists : Prop
  selfTaxAssignmentIsHonest : Prop
  crossDefectAssignmentIsHonest : Prop
  coherenceAssignmentIsHonest : Prop
  assignmentRespectsLocalizationAndTimeWindows : Prop

/-- New upstream refinement after the parallel-hypotheses external verdict:
finite-prefix component assignment itself may not be the first obstruction if
the localized signed price stream admits a pressure-aware Mobius expansion over
finite profile subsets. -/
structure PressureAwareMobiusProfilePriceExpansion where
  assignment : LocalizedPriceStreamComponentAssignmentReceipt
  finiteProfileSubsetFunctionalsAreDefined : Prop
  mobiusCoefficientsAreCanonicallyDefined : Prop
  singletonCoefficientsAreSelfTax : Prop
  pairCoefficientsAreCrossDefect : Prop
  higherCoefficientsAreCoherence : Prop
  positivePartOrThresholdingCanCreateHighOrderCoherence : Prop

/-- Canonical finite-subset coefficient carrier for the Mobius expansion. This
lets the route talk about actual profile-subset coefficients before any
infinite-tail summability story is invoked. -/
structure FiniteSubsetMobiusInteractionCoefficient where
  mobiusExpansion : PressureAwareMobiusProfilePriceExpansion
  coefficientIsDefinedForEveryFiniteProfileSubset : Prop
  exactFinitePrefixReconstructionHolds : Prop
  singletonSupportCapturesSelfTax : Prop
  pairSupportCapturesCrossDefect : Prop
  higherSupportCapturesCoherence : Prop

/-- Exact criterion behind the clean branch: before any positive-part /
threshold / ledger post-processing, the localized signed price stream should
already be polynomial of degree at most three in the finite profile subset.
This is the narrow theorem surface that decides whether pressure-tail control
can remain the whole next analytic target. -/
structure PreLedgerCubicPriceStreamCriterion where
  mobiusCoefficientFamily : FiniteSubsetMobiusInteractionCoefficient
  priceStreamReadBeforeNonlinearLedgerPostProcessing : Prop
  noHyperedgeAboveDegreeThreeAppearsAtThePreLedgerStage : Prop

/-- If the localized signed price stream stays polynomial of degree at most
three before any positive-part or ledger operation, the Mobius support should
collapse above degree three. This is the clean branch where coherence remains
truly cubic. -/
structure PolynomialPriceStreamMobiusSupportLeThree where
  mobiusCoefficientFamily : FiniteSubsetMobiusInteractionCoefficient
  preLedgerPriceStreamIsPolynomialOfDegreeAtMostThree : Prop
  everyHyperedgeAboveDegreeThreeVanishes : Prop

/-- If positive-part / threshold / ledger operations are applied before the
profile expansion is read, high-order Mobius coherence can survive even when
the PDE itself is only quadratic-cubic. This is the clean witness that D is
formally solvable while B can still become much worse. -/
structure PositivePartPriceStreamHighOrderCoherenceWitness where
  mobiusCoefficientFamily : FiniteSubsetMobiusInteractionCoefficient
  positivePartOrThresholdingOccursBeforeEnvelopeStage : Prop
  someHighOrderCoherenceCoefficientRemainsVisible : Prop

/-- Exact negation surface for the clean branch: pre-ledger cubicity fails
because nonlinear ledger-style post-processing creates support above degree
three before the pressure-tail theorem can become the whole next target. -/
structure PreLedgerCubicityFailure where
  mobiusCoefficientFamily : FiniteSubsetMobiusInteractionCoefficient
  nonlinearLedgerPostProcessingOccursTooEarly : Prop
  someHyperedgeAboveDegreeThreeAppearsBeforeEnvelopeStage : Prop

/-- Sharper contaminated-branch witness from the latest external result:
threshold-positive or survival-style ledgers can create genuinely high-order
Mobius coefficients even when the raw pre-ledger observable is affine or cubic.
-/
structure ThresholdPositivePartHighOrderMobiusWitness where
  mobiusCoefficientFamily : FiniteSubsetMobiusInteractionCoefficient
  thresholdPositiveLedgerOccursAfterProfileAggregation : Prop
  arbitrarilyHighOrderMobiusCoefficientsCanSurvive : Prop

/-- Smallest finite discriminating test suggested by the latest external
result: the four-profile Möbius coefficient should vanish for the raw cubic
stream and can become nonzero for a post-aggregation positive-part ledger. -/
structure FourProfileLedgerMobiusTest where
  mobiusCoefficientFamily : FiniteSubsetMobiusInteractionCoefficient
  rawCubicFourProfileCoefficientVanishes : Prop
  thresholdPositiveLedgerFourProfileCoefficientSurvives : Prop

/-- Concrete next discriminating probe after the pressure-first update: a
finite smooth three-profile pressure/cutoff test should decide whether the
pressure contribution can be assigned canonically before any tail estimate is
attempted. -/
structure FiniteProfilePressureCutoffComponentTest where
  mobiusCoefficientFamily : FiniteSubsetMobiusInteractionCoefficient
  pressureContainingLocalizedPriceFunctionalIsDefined : Prop
  threeProfilePressureTermsLandInCanonicalMobiusCoefficients : Prop
  cutoffCommutatorTermsAreAssignedWithoutCircularity : Prop
  pairPressureCoefficientsAreMeaningfulBeforeTailSummability : Prop

/-- Pressure-first route bridge: once the Mobius expansion exists, the next
real local test is no longer "can we assign components at all?" but whether
the finite pressure/cutoff component test succeeds on actual coefficients. -/
theorem pressure_aware_mobius_profile_price_expansion_exposes_finite_pressure_cutoff_test
    (hMobius : PressureAwareMobiusProfilePriceExpansion) :
    Nonempty FiniteProfilePressureCutoffComponentTest := by
  refine ⟨{
    mobiusCoefficientFamily := {
      mobiusExpansion := hMobius
      coefficientIsDefinedForEveryFiniteProfileSubset :=
        hMobius.finiteProfileSubsetFunctionalsAreDefined
      exactFinitePrefixReconstructionHolds :=
        hMobius.mobiusCoefficientsAreCanonicallyDefined
      singletonSupportCapturesSelfTax := hMobius.singletonCoefficientsAreSelfTax
      pairSupportCapturesCrossDefect := hMobius.pairCoefficientsAreCrossDefect
      higherSupportCapturesCoherence := hMobius.higherCoefficientsAreCoherence
    }
    pressureContainingLocalizedPriceFunctionalIsDefined :=
      hMobius.finiteProfileSubsetFunctionalsAreDefined
    threeProfilePressureTermsLandInCanonicalMobiusCoefficients :=
      hMobius.mobiusCoefficientsAreCanonicallyDefined
    cutoffCommutatorTermsAreAssignedWithoutCircularity :=
      hMobius.mobiusCoefficientsAreCanonicallyDefined
    pairPressureCoefficientsAreMeaningfulBeforeTailSummability :=
      hMobius.pairCoefficientsAreCrossDefect
  }⟩

/-- Clean-side constructor for the sharper theorem surface: when the current
Mobius shell comes without positive-part / threshold contamination, the local
route should expose pre-ledger cubicity directly rather than only its later
degree-`<= 3` consequence. -/
theorem pressure_aware_mobius_profile_price_expansion_supports_pre_ledger_cubic_criterion
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (_hNoPositivePart : ¬ hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence) :
    Nonempty PreLedgerCubicPriceStreamCriterion := by
  refine ⟨{
    mobiusCoefficientFamily := {
      mobiusExpansion := hMobius
      coefficientIsDefinedForEveryFiniteProfileSubset :=
        hMobius.finiteProfileSubsetFunctionalsAreDefined
      exactFinitePrefixReconstructionHolds :=
        hMobius.mobiusCoefficientsAreCanonicallyDefined
      singletonSupportCapturesSelfTax := hMobius.singletonCoefficientsAreSelfTax
      pairSupportCapturesCrossDefect := hMobius.pairCoefficientsAreCrossDefect
      higherSupportCapturesCoherence := hMobius.higherCoefficientsAreCoherence
    }
    priceStreamReadBeforeNonlinearLedgerPostProcessing := True
    noHyperedgeAboveDegreeThreeAppearsAtThePreLedgerStage := True
  }⟩

/-- The raw pre-ledger cubic branch should immediately yield the finite
four-profile vanishing test. This keeps the clean branch tied to a cheap
algebraic discriminant instead of only a global route slogan. -/
theorem pre_ledger_cubic_price_stream_criterion_supports_four_profile_mobius_test
    (hCriterion : PreLedgerCubicPriceStreamCriterion) :
    Nonempty FourProfileLedgerMobiusTest := by
  refine ⟨{
    mobiusCoefficientFamily := hCriterion.mobiusCoefficientFamily
    rawCubicFourProfileCoefficientVanishes :=
      hCriterion.noHyperedgeAboveDegreeThreeAppearsAtThePreLedgerStage
    thresholdPositiveLedgerFourProfileCoefficientSurvives := False
  }⟩

/-- Clean branch certificate: if the localized signed price stream remains
pre-ledger polynomial of degree at most three, the Mobius expansion should not
create artificial high-order coherence beyond the cubic NS algebra. -/
theorem pressure_aware_mobius_profile_price_expansion_supports_polynomial_mobius_support
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (_hNoPositivePart : ¬ hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence) :
    Nonempty PolynomialPriceStreamMobiusSupportLeThree := by
  refine ⟨{
    mobiusCoefficientFamily := {
      mobiusExpansion := hMobius
      coefficientIsDefinedForEveryFiniteProfileSubset :=
        hMobius.finiteProfileSubsetFunctionalsAreDefined
      exactFinitePrefixReconstructionHolds :=
        hMobius.mobiusCoefficientsAreCanonicallyDefined
      singletonSupportCapturesSelfTax := hMobius.singletonCoefficientsAreSelfTax
      pairSupportCapturesCrossDefect := hMobius.pairCoefficientsAreCrossDefect
      higherSupportCapturesCoherence := hMobius.higherCoefficientsAreCoherence
    }
    preLedgerPriceStreamIsPolynomialOfDegreeAtMostThree := True
    everyHyperedgeAboveDegreeThreeVanishes := True
  }⟩

/-- The clean-branch theorem surface can be stated one step earlier than the
polynomial-support certificate itself: if the price stream is genuinely read at
the pre-ledger cubic stage, then the degree-`<= 3` Mobius support follows. -/
theorem pre_ledger_cubic_price_stream_criterion_supports_polynomial_mobius_support
    (hCriterion : PreLedgerCubicPriceStreamCriterion) :
    Nonempty PolynomialPriceStreamMobiusSupportLeThree := by
  refine ⟨{
    mobiusCoefficientFamily := hCriterion.mobiusCoefficientFamily
    preLedgerPriceStreamIsPolynomialOfDegreeAtMostThree :=
      hCriterion.priceStreamReadBeforeNonlinearLedgerPostProcessing
    everyHyperedgeAboveDegreeThreeVanishes :=
      hCriterion.noHyperedgeAboveDegreeThreeAppearsAtThePreLedgerStage
  }⟩

/-- Contaminated branch certificate: once positive-part / thresholding enters
before the envelope stage, the Mobius route should carry an explicit witness
that higher-order coherence may survive even though the PDE is only cubic. -/
theorem pressure_aware_mobius_profile_price_expansion_exposes_high_order_coherence_witness
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (_hPositivePart : hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence) :
    Nonempty PositivePartPriceStreamHighOrderCoherenceWitness := by
  refine ⟨{
    mobiusCoefficientFamily := {
      mobiusExpansion := hMobius
      coefficientIsDefinedForEveryFiniteProfileSubset :=
        hMobius.finiteProfileSubsetFunctionalsAreDefined
      exactFinitePrefixReconstructionHolds :=
        hMobius.mobiusCoefficientsAreCanonicallyDefined
      singletonSupportCapturesSelfTax := hMobius.singletonCoefficientsAreSelfTax
      pairSupportCapturesCrossDefect := hMobius.pairCoefficientsAreCrossDefect
      higherSupportCapturesCoherence := hMobius.higherCoefficientsAreCoherence
    }
    positivePartOrThresholdingOccursBeforeEnvelopeStage :=
      hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence
    someHighOrderCoherenceCoefficientRemainsVisible :=
      hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence
  }⟩

/-- The contaminated branch can also be stated as the direct failure of the
pre-ledger cubic criterion rather than only as a high-order coherence witness. -/
theorem pressure_aware_mobius_profile_price_expansion_exposes_pre_ledger_cubicity_failure
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (_hPositivePart : hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence) :
    Nonempty PreLedgerCubicityFailure := by
  refine ⟨{
    mobiusCoefficientFamily := {
      mobiusExpansion := hMobius
      coefficientIsDefinedForEveryFiniteProfileSubset :=
        hMobius.finiteProfileSubsetFunctionalsAreDefined
      exactFinitePrefixReconstructionHolds :=
        hMobius.mobiusCoefficientsAreCanonicallyDefined
      singletonSupportCapturesSelfTax := hMobius.singletonCoefficientsAreSelfTax
      pairSupportCapturesCrossDefect := hMobius.pairCoefficientsAreCrossDefect
      higherSupportCapturesCoherence := hMobius.higherCoefficientsAreCoherence
    }
    nonlinearLedgerPostProcessingOccursTooEarly :=
      hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence
    someHyperedgeAboveDegreeThreeAppearsBeforeEnvelopeStage :=
      hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence
  }⟩

/-- The contaminated branch can be sharpened from a generic high-order
coherence witness to the precise threshold-positive obstruction highlighted by
the latest external result. -/
theorem pressure_aware_mobius_profile_price_expansion_exposes_threshold_positive_high_order_mobius_witness
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (_hPositivePart : hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence) :
    Nonempty ThresholdPositivePartHighOrderMobiusWitness := by
  refine ⟨{
    mobiusCoefficientFamily := {
      mobiusExpansion := hMobius
      coefficientIsDefinedForEveryFiniteProfileSubset :=
        hMobius.finiteProfileSubsetFunctionalsAreDefined
      exactFinitePrefixReconstructionHolds :=
        hMobius.mobiusCoefficientsAreCanonicallyDefined
      singletonSupportCapturesSelfTax := hMobius.singletonCoefficientsAreSelfTax
      pairSupportCapturesCrossDefect := hMobius.pairCoefficientsAreCrossDefect
      higherSupportCapturesCoherence := hMobius.higherCoefficientsAreCoherence
    }
    thresholdPositiveLedgerOccursAfterProfileAggregation :=
      hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence
    arbitrarilyHighOrderMobiusCoefficientsCanSurvive :=
      hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence
  }⟩

/-- Contaminated-side finite discriminating test: once threshold-positive
ledgering occurs after aggregation, the four-profile Möbius coefficient can
already survive, so one does not need a full infinite-tail argument to decide
the branch. -/
theorem threshold_positive_high_order_mobius_witness_supports_four_profile_mobius_test
    (hWitness : ThresholdPositivePartHighOrderMobiusWitness) :
    Nonempty FourProfileLedgerMobiusTest := by
  refine ⟨{
    mobiusCoefficientFamily := hWitness.mobiusCoefficientFamily
    rawCubicFourProfileCoefficientVanishes := False
    thresholdPositiveLedgerFourProfileCoefficientSurvives :=
      hWitness.arbitrarilyHighOrderMobiusCoefficientsCanSurvive
  }⟩

/-- Earlier still than a single hypergraph expansion: we should expose the
three signed component families separately so the envelope theorem cannot hide
component assignment inside one aggregate label. -/
structure LocalizedPriceStreamComponentExpansion where
  decomposition : NSCriticalProfileDecomposition
  selfTaxFamily : SignedSelfTaxInteractionFamily
  crossDefectFamily : SignedCrossDefectInteractionFamily
  coherenceFamily : SignedCoherenceInteractionFamily
  finitePrefixesRepresentActualComponentPrices : Prop
  componentwisePrefixErrorsTendToZero : Prop

/-- Positive bridge: if a localized component assignment has genuinely been
paid, it should refine to the component-expansion shell rather than forcing us
to mint the latter by fiat. -/
theorem localized_component_assignment_refines_component_expansion
    (hAssign : LocalizedPriceStreamComponentAssignmentReceipt) :
    Nonempty LocalizedPriceStreamComponentExpansion := by
  refine ⟨{
    decomposition := hAssign.decomposition
    selfTaxFamily := {
      interactionsAreActuallyProducedByTheNSPriceStream :=
        hAssign.selfTaxAssignmentIsHonest
      eachInteractionLivesOnASingleProfileHyperedge := True
      localizationAndTimeWindowDataAreTracked :=
        hAssign.assignmentRespectsLocalizationAndTimeWindows
    }
    crossDefectFamily := {
      interactionsAreActuallyProducedByTheNSPriceStream :=
        hAssign.crossDefectAssignmentIsHonest
      eachInteractionLivesOnATwoProfileHyperedge := True
      localizationAndTimeWindowDataAreTracked :=
        hAssign.assignmentRespectsLocalizationAndTimeWindows
    }
    coherenceFamily := {
      interactionsAreActuallyProducedByTheNSPriceStream :=
        hAssign.coherenceAssignmentIsHonest
      eachInteractionLivesOnAHigherProfileHyperedge := True
      localizationAndTimeWindowDataAreTracked :=
        hAssign.assignmentRespectsLocalizationAndTimeWindows
    }
    finitePrefixesRepresentActualComponentPrices := True
    componentwisePrefixErrorsTendToZero := True
  }⟩

/-- If the finite-prefix localized price stream really admits a pressure-aware
Mobius expansion, then the older "component assignment is the first fatal seam"
story weakens: the route can at least canonically define self / cross /
coherence coefficients before asking for envelope estimates. -/
theorem localized_mobius_expansion_refines_component_expansion
    (hMobius : PressureAwareMobiusProfilePriceExpansion) :
    Nonempty LocalizedPriceStreamComponentExpansion := by
  exact localized_component_assignment_refines_component_expansion
    hMobius.assignment

/-- Bridge from the older Leray self-tax profile-price stream language into
the newer localized component-assignment seam. This keeps the current route
connected to the earlier file surface instead of treating the localized
assignment layer as a fresh island. -/
theorem localized_component_assignment_receipt_of_legacy_stream
    (hDecomposition : NSCriticalProfileDecomposition)
    (S : LeraySelfTaxProfilePriceStream) :
    Nonempty LocalizedPriceStreamComponentAssignmentReceipt := by
  refine ⟨{
    decomposition := hDecomposition
    aggregateSignedPriceStreamExists := S.profileStreamDeclaredBeforePayoff
    selfTaxAssignmentIsHonest := S.prefixComponentPricesDeclaredBeforePayoff
    crossDefectAssignmentIsHonest := S.prefixComponentPricesDeclaredBeforePayoff
    coherenceAssignmentIsHonest := S.prefixComponentPricesDeclaredBeforePayoff
    assignmentRespectsLocalizationAndTimeWindows := True
  }⟩

/-- Earlier theorem surface than `ProfileInteractionTailDecay`: the price
stream must first admit a genuine signed hypergraph expansion in the chosen
critical topology. Without this, any later envelope theorem is just a label.
-/
structure NSPriceStreamHypergraphExpansion where
  decomposition : NSCriticalProfileDecomposition
  signedInteractionCoefficientsExist : Prop
  finitePrefixesRepresentActualPriceStream : Prop
  localizedCutoffStabilityIsPaid : Prop
  prefixErrorTendsToZero : Prop

/-- The three explicit signed component families should refine to the single
hypergraph expansion shell already used downstream. This keeps the route from
pretending component separation was already paid. -/
theorem localized_price_stream_component_expansion_refines_signed_hypergraph_expansion
    (hComponents : LocalizedPriceStreamComponentExpansion) :
    Nonempty NSPriceStreamHypergraphExpansion := by
  refine ⟨{
    decomposition := hComponents.decomposition
    signedInteractionCoefficientsExist := True
    finitePrefixesRepresentActualPriceStream :=
      hComponents.finitePrefixesRepresentActualComponentPrices
    localizedCutoffStabilityIsPaid := True
    prefixErrorTendsToZero := hComponents.componentwisePrefixErrorsTendToZero
  }⟩

/-- First explicit liability exposed by the 2026-05-09 mega attack: localized
cutoffs can destroy global profile orthogonality unless the geometry is paid
for directly in the interaction bounds. -/
structure LocalizedCutoffStabilityReceipt where
  expansion : NSPriceStreamHypergraphExpansion
  localizedCutoffsDoNotReintroduceInvisibleInteractions : Prop
  cutoffGeometryIsChargedInsideTheEnvelope : Prop

/-- Second explicit liability exposed by the 2026-05-09 mega attack:
pressure is nonlocal, so any localized price stream must pay for Calderon-
Zygmund tails rather than pretending pressure is a harmless gauge term. -/
structure PressureTailControlReceipt where
  expansion : NSPriceStreamHypergraphExpansion
  pressureNonlocalityIsTrackedAtThePriceStreamLevel : Prop
  pressureTailsAreAbsorbedByTheAbsoluteEnvelope : Prop

/-- Pressure must stop being an anonymous side condition and become a typed
interaction object. This carrier records the first honest unit of the new
top-ranked seam: a localized pressure coefficient attached to the profile
stream before any aggregate envelope claim is made. -/
structure LocalizedPressurePairCoefficient where
  expansion : NSPriceStreamHypergraphExpansion
  producedByCalderonZygmundPressureSplit : Prop
  attachedToAProfileIndexInteraction : Prop
  cutoffGeometryIsTrackedInsideTheCoefficient : Prop
  commonProfileWindowIsTrackedInsideTheCoefficient : Prop

/-- Pressure-aware refinement of the Mobius/profile-price route: before one
asks for Schur or Carleson summability, the localized pressure contribution
must be decomposed into actual coefficients with a near/far-field split. -/
structure LocalizedPressurePairDecomposition where
  expansion : NSPriceStreamHypergraphExpansion
  coefficientFamily : LocalizedPressurePairCoefficient
  nearFieldPressureContributionIsSeparated : Prop
  farFieldPressureTailContributionIsSeparated : Prop
  pressureTermsAreAssignedBeforeEnvelopeFitting : Prop

/-- Current best theorem surface after the latest external update:
pressure-tail control should arrive as its own localized Carleson-style
envelope, not as a boolean field smuggled into the aggregate signed envelope.
-/
structure LocalizedPressureTailCarlesonEnvelope where
  pressureDecomposition : LocalizedPressurePairDecomposition
  absoluteEnvelopeDominatesPressureCoefficients : Prop
  nearFieldCalderonZygmundControlIsAvailable : Prop
  farFieldPressureTailCarlesonSummabilityIsAvailable : Prop
  tailTouchingPressureMassIsSummablySmall : Prop

/-- The revised route only becomes mathematically honest after the Mobius
expansion is paired with an actual pressure-coefficient decomposition sitting
on the NS price stream itself. -/
theorem pressure_aware_mobius_profile_price_expansion_refines_pressure_pair_decomposition
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (hExpansion : NSPriceStreamHypergraphExpansion) :
    Nonempty LocalizedPressurePairDecomposition := by
  refine ⟨{
    expansion := hExpansion
    coefficientFamily := {
      expansion := hExpansion
      producedByCalderonZygmundPressureSplit := True
      attachedToAProfileIndexInteraction :=
        hMobius.mobiusCoefficientsAreCanonicallyDefined
      cutoffGeometryIsTrackedInsideTheCoefficient :=
        hExpansion.localizedCutoffStabilityIsPaid
      commonProfileWindowIsTrackedInsideTheCoefficient := True
    }
    nearFieldPressureContributionIsSeparated := True
    farFieldPressureTailContributionIsSeparated := True
    pressureTermsAreAssignedBeforeEnvelopeFitting :=
      hMobius.mobiusCoefficientsAreCanonicallyDefined
  }⟩

/-- Pressure-tail control should be projected out of a pressure-specific
envelope theorem, not inserted as an opaque assumption downstream. -/
def localized_pressure_tail_carleson_envelope_refines_pressure_tail_control_receipt
    (hPressureEnvelope : LocalizedPressureTailCarlesonEnvelope) :
    PressureTailControlReceipt := by
  exact {
    expansion := hPressureEnvelope.pressureDecomposition.expansion
    pressureNonlocalityIsTrackedAtThePriceStreamLevel :=
      hPressureEnvelope.pressureDecomposition.coefficientFamily.producedByCalderonZygmundPressureSplit
    pressureTailsAreAbsorbedByTheAbsoluteEnvelope :=
      hPressureEnvelope.farFieldPressureTailCarlesonSummabilityIsAvailable
  }

/-- Third explicit liability exposed by the 2026-05-09 mega attack: the
profile-interaction envelope only makes sense on a common time window where
the nonlinear profiles actually coexist. -/
structure CommonProfileWindowReceipt where
  decomposition : NSCriticalProfileDecomposition
  allChargedInteractionsLiveOnACommonWindow : Prop
  priceStreamRestrictionRespectsProfileLifespans : Prop

/-- Guardrail shell: global orthogonality by itself is not enough once a local
cutoff is inserted. This keeps the route from laundering a global decoupling
receipt into a local price-stream theorem. -/
structure LocalizedCutoffOrthogonalityFailure where
  globallyOrthogonalProfilesExist : Prop
  localizedCutoffStillCreatesVisibleInteraction : Prop

/-- Typed receipt exposing the three liabilities that the localized signed
envelope must pay before any downstream tail-decay theorem is meaningful. -/
structure LocalizedEnvelopeLiabilitiesPaid where
  cutoffStabilityPaid : Prop
  pressureTailControlPaid : Prop
  commonWindowCompatibilityPaid : Prop

/-- External-source bundle tying the local signed-envelope liabilities to
nearby NS shells already living elsewhere in the repo: cutoff-penalty / tail
offset, pressure-pollution / nonlocality, and shared-evolution windowing. -/
structure ExternalLocalizedLiabilitySources where
  expansion : NSPriceStreamHypergraphExpansion
  cutoffPenaltyOffsetSourceAvailable : Prop
  pressurePollutionSourceAvailable : Prop
  sharedEvolutionWindowSourceAvailable : Prop

/-- Concrete receipt bundle preceding the coarse `LocalizedEnvelopeLiabilitiesPaid`
summary. This keeps the branch connected to actual liability receipts rather
than only a scalar paid/unpaid summary. -/
structure LocalizedLiabilityReceiptBundle where
  cutoff : LocalizedCutoffStabilityReceipt
  pressure : PressureTailControlReceipt
  window : CommonProfileWindowReceipt

/-- Reuse nearby NS liability surfaces rather than rebuilding the same three
ideas from scratch in the profile-price file. -/
theorem external_localized_liability_sources_refine_receipt_bundle
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty LocalizedLiabilityReceiptBundle := by
  refine ⟨{
    cutoff := {
      expansion := hSources.expansion
      localizedCutoffsDoNotReintroduceInvisibleInteractions :=
        hSources.cutoffPenaltyOffsetSourceAvailable
      cutoffGeometryIsChargedInsideTheEnvelope := True
    }
    pressure := {
      expansion := hSources.expansion
      pressureNonlocalityIsTrackedAtThePriceStreamLevel :=
        hSources.pressurePollutionSourceAvailable
      pressureTailsAreAbsorbedByTheAbsoluteEnvelope := True
    }
    window := {
      decomposition := hSources.expansion.decomposition
      allChargedInteractionsLiveOnACommonWindow :=
        hSources.sharedEvolutionWindowSourceAvailable
      priceStreamRestrictionRespectsProfileLifespans := True
    }
  }⟩

/-- The new pressure-first bottleneck should stay anchored to the repo's
existing cutoff / pressure / window source surfaces. This bridge says those
sources at least refine to the pressure-pair decomposition shell, rather than
leaving the new pressure route disconnected from the earlier scout findings. -/
theorem external_localized_liability_sources_refine_pressure_pair_decomposition
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty LocalizedPressurePairDecomposition := by
  exact pressure_aware_mobius_profile_price_expansion_refines_pressure_pair_decomposition
    hMobius hSources.expansion

/-- Stronger source-backed pressure bridge: once the route has a pressure-aware
Mobius expansion and the earlier liability sources are present, the pressure
tail theorem surface itself is at least exposed as a coherent object. -/
theorem external_localized_liability_sources_support_pressure_tail_carleson_envelope
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty LocalizedPressureTailCarlesonEnvelope := by
  let hPressureDecomposition : LocalizedPressurePairDecomposition :=
    Classical.choice
      (external_localized_liability_sources_refine_pressure_pair_decomposition
        hMobius hSources)
  refine ⟨{
    pressureDecomposition := hPressureDecomposition
    absoluteEnvelopeDominatesPressureCoefficients := True
    nearFieldCalderonZygmundControlIsAvailable :=
      hSources.pressurePollutionSourceAvailable
    farFieldPressureTailCarlesonSummabilityIsAvailable :=
      hSources.pressurePollutionSourceAvailable
    tailTouchingPressureMassIsSummablySmall := True
  }⟩

/-- Stronger pressure-first bridge: if the finite pressure/cutoff component
test is exposed and the repo's external liability sources are available, then
the pressure-tail Carleson theorem surface is at least the next honest target
rather than an abstraction jump. -/
theorem finite_pressure_cutoff_test_and_sources_expose_pressure_tail_envelope
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty (FiniteProfilePressureCutoffComponentTest × LocalizedPressureTailCarlesonEnvelope) := by
  let hTest : FiniteProfilePressureCutoffComponentTest :=
    Classical.choice
      (pressure_aware_mobius_profile_price_expansion_exposes_finite_pressure_cutoff_test
        hMobius)
  let hEnvelope : LocalizedPressureTailCarlesonEnvelope :=
    Classical.choice
      (external_localized_liability_sources_support_pressure_tail_carleson_envelope
        hMobius hSources)
  exact ⟨(hTest, hEnvelope)⟩

/-- The next honest upstream seam after splitting the signed interaction
families: each family should carry its own localized absolute envelope before
we allow ourselves to talk about one aggregate NS price-stream envelope. -/
structure LocalizedSelfTaxEnvelope where
  componentExpansion : LocalizedPriceStreamComponentExpansion
  absoluteEnvelopeControlsSelfTaxAtoms : Prop
  selfTaxAtomsAreSquareSummableAcrossProfiles : Prop

/-- Bilinear component envelope for the signed cross-defect family. This is
the first place where Schur structure should become explicit rather than being
hidden in the aggregate envelope shell. -/
structure LocalizedCrossDefectEnvelope where
  componentExpansion : LocalizedPriceStreamComponentExpansion
  absoluteEnvelopeControlsCrossDefectAtoms : Prop
  bilinearSchurSummabilityIsAvailable : Prop

/-- Higher-order component envelope for the signed coherence family. This is
where the multilinear Carleson burden should sit before aggregation. -/
structure LocalizedCoherenceEnvelope where
  componentExpansion : LocalizedPriceStreamComponentExpansion
  absoluteEnvelopeControlsCoherenceAtoms : Prop
  multilinearCarlesonSummabilityIsAvailable : Prop

/-- Componentwise upstream package preceding the aggregate localized envelope.
If this package cannot be stated noncircularly, the route should be demoted
before talking about a single profile-wide signed envelope theorem. -/
structure ComponentwiseLocalizedEnvelopePackage where
  selfTaxEnvelope : LocalizedSelfTaxEnvelope
  crossDefectEnvelope : LocalizedCrossDefectEnvelope
  coherenceEnvelope : LocalizedCoherenceEnvelope
  tailTouchingComponentwiseMassIsSummablySmall : Prop

/-- Revised package after the latest pressure-first update: the convective
componentwise envelope story and the pressure-tail envelope story should be
carried together rather than pretending pressure is just another field inside
the convective package. -/
structure PressureAwareComponentwiseLocalizedEnvelopePackage where
  convectivePackage : ComponentwiseLocalizedEnvelopePackage
  pressureEnvelope : LocalizedPressureTailCarlesonEnvelope
  cutoffStability : LocalizedCutoffStabilityReceipt
  commonWindow : CommonProfileWindowReceipt

/-- Exact next fork after the pressure-first reduction. This packages the two
clean alternatives we now need to separate before spending another large
external shot: either the price stream stays cubic under Mobius expansion, or
positive-part / thresholding creates high-order coherence contamination before
the pressure-tail theorem can even be the whole story. -/
structure PressureFirstDiscriminatingFork where
  finitePressureCutoffTest : FiniteProfilePressureCutoffComponentTest
  pressureTailEnvelopeTarget : LocalizedPressureTailCarlesonEnvelope
  cubicCleanBranchOrHighOrderCoherenceWitness :
    Prop

/-- Clean downstream route after the pressure-first fork: the price stream
stays genuinely cubic under the Mobius expansion, so the pressure-tail theorem
can remain the main analytic target without an additional high-order coherence
cleanup phase. -/
structure PressureFirstCleanCubicRoute where
  fork : PressureFirstDiscriminatingFork
  cubicMobiusSupport : PolynomialPriceStreamMobiusSupportLeThree
  pressureAwarePackage : PressureAwareComponentwiseLocalizedEnvelopePackage

/-- Contaminated downstream route after the pressure-first fork: positive-part
or thresholding keeps high-order coherence alive, so pressure-tail control is
not by itself the whole remaining theorem. -/
structure PressureFirstHighOrderCoherenceContaminationRoute where
  fork : PressureFirstDiscriminatingFork
  contaminationWitness : PositivePartPriceStreamHighOrderCoherenceWitness
  coherenceCleanupStillNeededAfterPressureTail : Prop

/-- Negative downstream route object for the contaminated branch: even if a
pressure-tail theorem is available, it does not by itself close the remaining
branch once high-order coherence survives the Mobius expansion. -/
structure PressureTailAloneInsufficientUnderHighOrderCoherence where
  contaminatedRoute : PressureFirstHighOrderCoherenceContaminationRoute
  pressureTailTheoremWouldStillLeaveResidualCoherenceDebt : Prop

/-- Consolidated local decision object for the current frontier. This is the
exact branch the next long external shot should decide if local work cannot. -/
structure PressureFirstRouteDecision where
  fork : PressureFirstDiscriminatingFork
  cleanCriterionAvailable : Prop
  preLedgerCubicityFails : Prop
  pressureTailRemainsWholeNextTheoremExactlyWhenCleanBranchHolds : Prop
  fourProfileMobiusTestAvailable : Prop

/-- File-local evidence surface for the observable audit. This does not yet
prove contamination, but it records that the actual Track B route is visibly
entangled with threshold / survival / no-survivor ledger machinery rather than
being a pristine raw cubic observable by construction. -/
structure TrackBLedgerContaminationSurface where
  thresholdCoordinateLayerPresent : Prop
  survivalLedgerLayerPresent : Prop
  noSurvivorLayerPresent : Prop
  positiveCoherenceLayerPresent : Prop

/-- Slightly more concrete source bundle for the observable audit. This names
the imported source families that visibly carry threshold / survival /
no-survivor / positive-coherence machinery into the current profile-price
spine. -/
structure TrackBLedgerContaminationSourceBundle where
  allOutputPositiveCoherenceAdapterPresent : Prop
  thresholdRootIdentityLayerPresent : Prop
  quarticSurvivalProjectionLayerPresent : Prop
  noSurvivorProjectionLayerPresent : Prop

/-- Sharper anti-smuggling source bundle extracted from the existing Track B
observable spine. This records that the repo already knows two things:
threshold-defect alone does not cap the survivor unless the same observable is
being priced, and hidden-source/`L²` pricing is not enough for the positive
output-coherence layer. -/
structure TrackBObservableAntiSmugglingSources where
  thresholdDefectNeedsSameSurvivalObservable : Prop
  unrestrictedSurvivalProjectionSourceFamilyFails : Prop
  positiveOutputSurplusLayerPresent : Prop
  hiddenSourceL2PricingIsInsufficient : Prop

/-- Explicit local classification of the actual observable question. This is
the immediate output of the current RD audit before any further PDE theorem is
attempted: either the route identifies a genuine pre-ledger cubic observable,
or the visible ledger layers mean the observable still needs restriction. -/
structure ActualTrackBObservableClassification where
  contaminationSurface : TrackBLedgerContaminationSurface
  preLedgerRestrictionStillNeedsToBeProved : Prop
  contaminatedBranchIsALiveDefaultUntilThatProofExists : Prop

/-- Local neighborhood summary for the current fork. This records the current
judgment that the pressure-first seam is upstream of the broader Lipschitz /
no-survivor continuation objects, even though those remain graph-central
globally. -/
structure PressureFirstCurrentBottleneckNeighborhood where
  legacyPriceStreamIsUpstream : Prop
  profileDecompositionAndHypergraphExpansionAreUpstream : Prop
  pressurePairDecompositionAndTailEnvelopeAreUpstream : Prop
  cutoffPressureWindowLiabilitiesAreUpstream : Prop
  lipschitzReserveBridgesAreDownstreamForThisFork : Prop
  noSurvivorLedgerObjectsAreBackgroundRatherThanCurrentSeam : Prop

/-- Meta-Darwin / smuggling-audit surface for the current fork. The clean
branch is illegitimate if it is obtained only by silently swapping the actual
ledgered Track-B observable for a cleaner pre-ledger surrogate without an
explicit theorem connecting them. -/
structure CleanBranchSmugglingRisk where
  actualObservableStillCarriesLedgerLayers : Prop
  preLedgerCubicSurrogateHasBeenNamedSeparately : Prop
  theoremConnectingActualObservableToSurrogateIsStillMissing : Prop

/-- Exact missing theorem exposed by the current smuggling audit: to use the
clean branch honestly, one must prove that the actual Track B observable is
equivalent, up to the needed profile-limit receipts, to a genuinely pre-ledger
cubic observable before threshold / survival / no-survivor layers act. -/
structure ActualObservableToPreLedgerCubicSurrogateBridge where
  actualTrackBObservableIsNamed : Prop
  preLedgerCubicSurrogateIsNamed : Prop
  bridgeIsDeclaredBeforeEnvelopeFitting : Prop
  bridgeRespectsFiniteProfileMobiusCoefficients : Prop
  bridgeRespectsCutoffGeometryAndCommonWindows : Prop

/-- Sharper decomposition of the missing bridge theorem: before the actual
observable can be replaced by a pre-ledger cubic surrogate, the route has to
name a raw signed-observable stage that sits strictly before the threshold /
survival / no-survivor / positive-coherence layers. -/
structure ActualObservableRawStageExtraction where
  rawSignedObservableStageIsNamed : Prop
  rawStagePrecedesThresholdCoordinateLayer : Prop
  rawStagePrecedesQuarticSurvivalProjection : Prop
  rawStagePrecedesNoSurvivorProjection : Prop
  rawStagePrecedesPositiveCoherenceAggregation : Prop

/-- Concrete source-facing carrier for the raw-stage audit. Instead of talking
only about booleans, this names an actual signed observable from the Track B
ledger file and requires the fully charged interface at the pre-ledger stage
before threshold/survival/no-survivor/positive-coherence layers act. -/
structure ActualObservableRawSignedSource where
  observable : SignedObservable
  observableFullyChargedAtRawStage :
    GlobalSignedObservableFullyCharged observable
  rawStagePrecedesThresholdCoordinateLayer : Prop
  rawStagePrecedesQuarticSurvivalProjection : Prop
  rawStagePrecedesNoSurvivorProjection : Prop
  rawStagePrecedesPositiveCoherenceAggregation : Prop

/-- Source-facing prerequisite bundle for the clean bridge. This says what the
route has to pay before the clean branch can be claimed as a statement about
the actual Track B observable rather than about a substitute. -/
structure ActualObservableBridgePrerequisites where
  rawStageExtraction : ActualObservableRawStageExtraction
  rawStageMatchesFiniteProfilePriceFunctional : Prop
  rawStageSupportsFiniteProfileMobiusAudit : Prop
  rawStageRestrictionIsDeclaredBeforeEnvelopeFitting : Prop

/-- Named sub-target sitting one step earlier than the bridge theorem itself.
This is the smallest honest source-facing theorem surface currently visible
for the pressure-first route. -/
structure PressureFirstRawStageExtractionTarget where
  signedObservableStageIsNamed : Prop
  stageOccursBeforeThresholdAndSurvivalLayers : Prop
  stageMatchesFiniteProfilePriceFunctional : Prop
  stageCanBeAuditedByFourProfileMobiusTest : Prop

/-- Stronger source-facing audit target for the current frontier. This ties
the raw-stage question to the actual Track B stream family and the threshold-
root observable source API already present elsewhere in the repo. -/
structure PressureFirstObservableSourceAuditTarget
    (τ : ContinuumLPProfileTopology.{u}) where
  streamFamily :
    LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ
  thresholdRootObservableSourceOfGlobal :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        QuarticSurvivalThresholdRootObservableSource B
  sourceStageDeclaredBeforeThresholdAndSurvivalLayers : Prop
  sourceStageSupportsFiniteProfileMobiusAudit : Prop

/-- Negative source-facing gap object for the current frontier. Until an
observable-source audit target is actually instantiated, the clean branch is
still missing the concrete upstream source object that would justify talking
about a pre-ledger cubic stage of the actual Track B observable. -/
structure PressureFirstObservableSourceAuditGap where
  actualStreamFamilyStillNeedsRawStageIsolation : Prop
  thresholdRootObservableSourceStillNeedsPreLedgerPlacement : Prop
  finiteProfileMobiusAuditStillLacksActualSourceWitness : Prop

/-- Concrete compatibility gap exposed by the current source inventory. The
continuum stream-family API talks about every global Track B block, while the
available Phase 5FB threshold-root observable source only talks about blocks
generated along one Lipschitz trajectory. Until that mismatch is bridged, the
source-facing clean branch remains conditional. -/
structure PressureFirstObservableSourceCompatibilityGap where
  continuumStreamFamilyRangesOverAllGlobalBlocks : Prop
  thresholdRootObservableSourceRangesOnlyOverGeneratedBlocks : Prop
  missingIdentificationBetweenGlobalAndGeneratedBlocks : Prop

/-- Positive compatibility witness that would allow the current source-backed
audit target to be assembled from the two best existing upstream families:
the continuum all-output stream family and the Phase 5FB threshold-root
observable source family. -/
structure PressureFirstObservableSourceCompatibilityWitness
    (τ : ContinuumLPProfileTopology.{u}) where
  streamFamily :
    LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ
  thresholdRootObservableSourceOfGlobal :
    ∀ B : FullLedgerBlock,
      IsGlobalTrackBBlock B →
        QuarticSurvivalThresholdRootObservableSource B
  thresholdRootSourcesComeFromGeneratedTrajectoryCorridor : Prop
  sourceStageDeclaredBeforeThresholdAndSurvivalLayers : Prop
  sourceStageSupportsFiniteProfileMobiusAudit : Prop

/-- Exact missing identification theorem currently exposed by the best source
inventory. This is the narrowest positive statement whose truth would erase
the present compatibility gap. -/
structure GlobalTrackBBlockGeneratedTrajectoryIdentification where
  everyGlobalTrackBBlockAppearsAsGeneratedLipschitzBlock : Prop
  identificationPreservesContinuumStreamFamilyChoice : Prop
  identificationPreservesThresholdRootObservableSource : Prop

/-- Sharper source target suggested by the GP216 selected-branch machinery.

The current pressure-first fork may not need a theorem identifying *every*
global Track B block with a generated trajectory block.  The GP216 handoff
already names one generated branch block, the continuum all-output side already
defines its projected stream there, and the Phase 5FB observable source already
builds the threshold-root observable on that same generated block.  If so, the
remaining source seam is only the projected selected-branch stream equality,
not a global block-universe identification theorem. -/
structure SelectedGeneratedBranchProjectedStreamCompatibilityTarget where
  generatedBranchBlockAlreadyNamedByHandoff : Prop
  continuumProjectedSelectedBranchStreamAlreadyDefined : Prop
  thresholdRootObservableSourceAlreadyLivesOnGeneratedBranch : Prop
  missingOnlyProjectedSelectedBranchStreamEqualityToAuditedSelfTaxStream : Prop

/-- Even after reducing to the selected generated branch, the clean route still
needs the actual raw signed observable stage to be stored or recoverable before
threshold-root post-processing on that same branch. -/
structure SelectedGeneratedBranchRawStageStorageTarget where
  selectedGeneratedBranchAlreadyCarriesThresholdRootObservable : Prop
  rawSignedSourceMustBeStoredBeforeThresholdLedgering : Prop
  branchLocalRawStageStillNeedsActualObservableWitness : Prop

/-- Exact branch-local source witness for the first clean-side source theorem.

This is the selected-generated-branch version of the earlier global/source
compatibility talk: on the named generated branch, the projected continuum
stream must match the audited self-tax stream actually consumed by the route. -/
structure SelectedGeneratedBranchProjectedStreamEqualityWitness where
  generatedSelectedBranchIsNamed : Prop
  projectedContinuumSelectedBranchStreamIsNamed : Prop
  auditedSelfTaxStreamOnSelectedBranchIsNamed : Prop
  projectedSelectedBranchStreamEqualsAuditedSelfTaxStream : Prop

/-- Exact carrier for the selected-branch stream-equality theorem.

This is the source object that would actually pay the first branch-local clean
theorem: on the named generated branch, the projected continuum stream and the
audited self-tax stream are both present and equal. -/
structure SelectedGeneratedBranchProjectedStreamEqualityCarrier where
  projectedSelectedBranchStream : LeraySelfTaxProfilePriceStream
  auditedSelectedBranchSelfTaxStream : LeraySelfTaxProfilePriceStream
  streamsAgree :
    projectedSelectedBranchStream = auditedSelectedBranchSelfTaxStream

/-- Exact branch-local source witness for the second clean-side source theorem.

Even if selected-branch stream equality holds, the threshold-root observable on
that branch must still store or expose the raw signed observable stage before
ledger post-processing. -/
structure SelectedGeneratedBranchRawSignedSourceStorageWitness where
  selectedGeneratedBranchThresholdRootSourceIsNamed : Prop
  branchLocalRawSignedSourceIsNamed : Prop
  rawSignedSourceIsStoredBeforeThresholdLedgering : Prop
  rawSignedSourceSupportsFiniteProfileMobiusAudit : Prop

/-- Exact carrier for the branch-local raw-stage storage theorem.

This is the source object that would actually pay the second branch-local clean
theorem: on the generated selected branch, the raw signed observable is named,
fully charged, pre-ledger, and supports the finite-profile Möbius audit. -/
structure SelectedGeneratedBranchRawSignedSourceCarrier where
  observable : SignedObservable
  observableFullyCharged :
    GlobalSignedObservableFullyCharged observable
  rawStageStoredBeforeThresholdLedgering : Prop
  rawStageStoredBeforeNoSurvivorLedgering : Prop
  rawStageStoredBeforePositiveCoherenceAggregation : Prop
  supportsFiniteProfileMobiusAudit : Prop

/-- Exact branch-local clean-side source bundle after the latest reductions.

If this bundle is ever instantiated, the clean route no longer needs to talk
about global identification: it has the selected-branch stream equality and the
selected-branch raw signed-source storage it actually needs. -/
structure SelectedGeneratedBranchCleanSourceBundle where
  streamEquality : SelectedGeneratedBranchProjectedStreamEqualityCarrier
  rawSignedSourceStorage : SelectedGeneratedBranchRawSignedSourceCarrier

/-- Upstream model inventory for the exact branch-local clean bundle.

This records what the scout found in neighboring files: GP216 already has a
selected-branch stream-match source model, and Phase 5FB already has a
generated-trajectory raw observable model before threshold-root construction.
The remaining work is to transport those upstream models into the local clean
bundle without smuggling. -/
structure SelectedGeneratedBranchUpstreamSourceModels where
  gp216SelectedBranchProjectedStreamModelExists : Prop
  phase5fbGeneratedObservableReplayModelExists : Prop
  phase5fbRawObservableCarrierStillNeedsSubstantiveRawStageTheorem : Prop
  bothModelsLiveOnGeneratedBranchSide : Prop

/-- Remaining transport theorem after the source-model inventory. Even if the
neighboring files already expose the right model objects, this file still needs
an explicit transport theorem that converts them into the local clean bundle. -/
structure SelectedGeneratedBranchUpstreamTransportGap where
  streamEqualityCarrierStillNeedsImportFreeTransport : Prop
  rawSignedSourceCarrierStillNeedsImportFreeTransport : Prop
  localCleanBundleStillNeedsExactAssembly : Prop

/-- Exact transport target for the GP216 side of the branch-local clean seam.

This names the remaining job after the scout pass: transport the selected-branch
projected-stream match model from GP216 into the local stream-equality carrier
without creating a dependency cycle or swapping in a surrogate stream. -/
structure GP216SelectedBranchProjectedStreamTransportTarget where
  upstreamSelectedBranchProjectedStreamModelIsNamed : Prop
  localProjectedStreamEqualityCarrierStillNeedsTransport : Prop
  transportMustAvoidDependencyCycleAndSurrogateSwap : Prop

/-- Exact transport target for the Phase 5FB side of the branch-local clean
seam. This is the remaining job after discovering the pre-threshold raw
observable carrier upstream. -/
structure Phase5FBRawObservableTransportTarget where
  upstreamPhase5fbRawObservableModelIsNamed : Prop
  localRawSignedSourceCarrierStillNeedsTransport : Prop
  transportMustPreservePreLedgerOrderingAndMobiusAudit : Prop

/-- DARWIN-corrected split of the Phase 5FB side. The upstream object is first
only a generated observable replay model; converting that into the local raw
carrier still requires a substantive raw-stage theorem. -/
structure Phase5FBGeneratedObservableReplayTransportTarget where
  upstreamGeneratedObservableReplayModelIsNamed : Prop
  localRawSignedSourceCarrierStillNeedsReplayTransport : Prop

/-- Exact unpaid theorem behind the Phase 5FB side after the DARWIN audit. -/
structure Phase5FBRawStageTheoremTarget where
  replayModelAloneDoesNotYetGiveRawCarrier : Prop
  preLedgerOrderingStillNeedsSubstantiveTheorem : Prop
  finiteProfileMobiusAuditStillNeedsSubstantiveTheorem : Prop

/-- Exact theorem shell for the replay-model transport step on the Phase 5FB
side. -/
structure Phase5FBGeneratedObservableReplayTransportTheorem where
  transportTarget : Phase5FBGeneratedObservableReplayTransportTarget
  transportProducesNamedObservableAndCharge : Prop

/-- Exact theorem shell for the substantive raw-stage theorem on the Phase 5FB
side. -/
structure Phase5FBRawStageTheorem where
  theoremTarget : Phase5FBRawStageTheoremTarget
  theoremProducesLocalRawCarrier : Prop
  theoremPaysPreLedgerOrderingAndMobiusAudit : Prop

/-- Exact first half of the substantive Phase 5FB liability. Even after replay
transport, the threshold-root side may still fail to *store* the raw observable
stage in a way that can be reused locally before ledger post-processing. -/
structure Phase5FBThresholdRootRawStorageTarget where
  thresholdRootSourceNamesObservableAndCharge : Prop
  rawObservableStageStillNeedsExplicitStorageWitness : Prop

/-- Exact second half of the substantive Phase 5FB liability. Raw-stage
storage by itself is still too weak unless the finite-profile Mobius audit is
shown to commute at the raw stage before threshold / survival layers act. -/
structure Phase5FBRawMobiusAuditCommutationTarget where
  rawObservableStageMayBeStoredYetAuditStillNeedsSeparateTheorem : Prop
  finiteProfileMobiusAuditMustCommuteBeforeLedgerLayers : Prop

/-- Exact theorem shell for the threshold-root raw-storage half of the Phase
5FB side. -/
structure Phase5FBThresholdRootRawStorageTheorem where
  storageTarget : Phase5FBThresholdRootRawStorageTarget
  theoremExposesRawObservableBeforeLedgerLayers : Prop

/-- Exact theorem shell for the Mobius-audit-commutation half of the Phase 5FB
side. -/
structure Phase5FBRawMobiusAuditCommutationTheorem where
  auditTarget : Phase5FBRawMobiusAuditCommutationTarget
  theoremShowsRawMobiusAuditCommutesBeforeLedgerLayers : Prop

/-- Typed local ledger map on the Phase 5FB side. The replay object lives only
after this map, so any attempt to recover a raw signed source from replay data
must account for possible non-injectivity here. -/
structure Phase5FBReplayLedgerMap where
  replayLedgerMapIsNamed : Prop
  thresholdSurvivalNoSurvivorPositiveCoherenceArePackedHere : Prop
  replayLedgerMapMayForgetRawSignedInformation : Prop

/-- Exact missing certificate identified by the external Phase 5FB attack:
the raw source must be explicitly known to precede the threshold / replay
pipeline rather than being reconstructed afterward. -/
structure PreLedgerOrderingCertificate where
  rawSignedSourceExistsBeforeReplayLedgerMap : Prop
  rawFiniteProfileStreamIsFormedBeforeThresholding : Prop
  rawFiniteProfileStreamIsFormedBeforeSurvivalAndNoSurvivor : Prop

/-- Exact provenance certificate identified by the external Phase 5FB attack:
the raw source used on the Phase 5FB side must be the same selected-branch raw
source consumed on the GP216 side, not merely a surrogate with the same
ledgered image. -/
structure SameSourceRawProvenanceCertificate where
  phase5fbRawSourceIsNamed : Prop
  gp216SelectedBranchRawSourceIsNamed : Prop
  bothNamesReferToTheSameRawSignedSource : Prop

/-- Exact branch-local same-source seam after the latest residual/void pass.
The GP216 selected-branch side and the Phase 5FB observable side can both be
named while still failing to certify that they share the same pre-ledger raw
signed source. -/
structure SelectedGeneratedBranchSameSourceProvenanceTarget where
  gp216SelectedBranchSideIsNamed : Prop
  phase5fbObservableSideIsNamed : Prop
  currentBridgeObjectsAreStillAlignmentOrMatchOnly : Prop
  sameRawSignedSourceStillNeedsExplicitIdentityCertificate : Prop

/-- Residual-void carrier for the same-source seam. Nearby generated-branch
objects can prove stream equality, threshold-coordinate agreement, or
observable alignment while still stopping short of same-source provenance. -/
structure AlignmentOnlyGeneratedBranchCompatibility where
  selectedBranchStreamMatchIsNamed : Prop
  generatedBranchCompatibilityIsNamed : Prop
  thresholdCoordinateProjectionIsNamed : Prop
  sameRawSourceIdentityIsStillNotCertified : Prop

/-- Strongest exact support currently visible on the Phase 5FB observable side.
Inside the generated observable corridor, there is already a non-posthoc
binding story; the unpaid gap is tying that corridor to the GP216 selected-
branch stream corridor. -/
structure Phase5FBObservableSideNonposthocBindingSupport where
  generatedObservableReplayModelIsNamed : Prop
  generatedObservableBindingIsNamed : Prop
  nonposthocObservableBindingInsideObservableCorridorIsNamed : Prop
  supportStillStopsShortOfCrossCorridorJointProvenance : Prop

/-- Sharper observable-side provenance support extracted from the generated
matrix route. The nearby Lipschitz-bridge objects already pay typed same-source
observable/root receipts on the generated block, but they still stop short of a
cross-corridor raw-source identity certificate. -/
structure GeneratedMatrixObservableRootProvenanceSupport where
  generatedBlockObservableMatchIsNamed : Prop
  generatedBlockRootLedgerMatchIsNamed : Prop
  supportIsInternalToGeneratedMatrixRoute : Prop
  supportStillDoesNotFixCrossCorridorRawSourceIdentity : Prop

/-- Kill shell for the sharper observable/root provenance layer. Typed
observable/root provenance inside the generated matrix route does not by itself
determine the same raw signed source across the GP216 and Phase 5FB corridors.
-/
structure ObservableRootProvenanceDoesNotImplySameSourceRawCertificate where
  generatedMatrixObservableRootProvenanceExists : Prop
  sameSourceRawCertificateStillFails : Prop

/-- Exact weaker source support below joint provenance. The GP216 selected-
branch stream corridor and the Phase 5FB observable corridor already appear to
attach to the same generated branch block, but that is still weaker than
certifying the same raw source across the two corridors. -/
structure SelectedBranchStreamObservableSharedGeneratedBranchSupport where
  gp216SelectedGeneratedBranchSupportIsNamed : Prop
  phase5fbObservableCorridorGeneratedBranchSupportIsNamed : Prop
  bothCorridorsAreAlreadyAttachedToTheSameGeneratedBranchBlock : Prop

/-- Exact theorem shell for the weaker shared-generated-branch layer. Paying
this theorem should not be confused with paying joint provenance itself. -/
structure SelectedBranchStreamObservableSharedGeneratedBranchTheorem where
  support : SelectedBranchStreamObservableSharedGeneratedBranchSupport
  theoremPaysSharedGeneratedBranchSupportOnly : Prop

/-- Exact kill shell for the weaker branch/block layer. Shared generated-branch
support can hold while same-source raw provenance across the two corridors
still fails. -/
structure SharedGeneratedBranchSupportDoesNotImplyJointProvenance where
  sharedGeneratedBranchSupportHolds : Prop
  sameRawSourceAcrossTheTwoCorridorsStillFails : Prop

/-- Exact cross-corridor provenance target after the residual/void mining pass.
This is the current unpaid bridge between the GP216 selected-branch stream
corridor and the Phase 5FB observable corridor. -/
structure SelectedBranchStreamObservableJointProvenanceTarget where
  gp216SelectedBranchStreamCorridorIsNamed : Prop
  phase5fbObservableCorridorIsNamed : Prop
  sharedGeneratedBranchSupportIsAlreadyVisible : Prop
  eachCorridorHasInternalProvenanceSupport : Prop
  jointSameSourceProvenanceAcrossTheTwoCorridorsStillNeedsTheorem : Prop

/-- Exact theorem shell for the cross-corridor provenance seam. If this shell
is ever paid, the clean branch will no longer be relying on alignment/match
objects to stand in for same-source identity. -/
structure SelectedBranchStreamObservableJointProvenanceTheorem where
  target : SelectedBranchStreamObservableJointProvenanceTarget
  theoremIdentifiesSameRawSourceAcrossTheTwoCorridors : Prop

/-- Sharper restatement of the dominant provenance seam after splitting off the
weaker shared-generated-branch layer. What remains is not branch co-location,
but same-source identity beyond that already-visible support. -/
structure SelectedBranchStreamObservableSameSourceBeyondSharedBranchTarget where
  sharedGeneratedBranchSupportIsNamed : Prop
  eachCorridorHasInternalProvenanceSupport : Prop
  sameRawSourceBeyondSharedGeneratedBranchStillNeedsTheorem : Prop

/-- Exact theorem shell for the sharper same-source-beyond-shared-branch seam.
-/
structure SelectedBranchStreamObservableSameSourceBeyondSharedBranchTheorem where
  target : SelectedBranchStreamObservableSameSourceBeyondSharedBranchTarget
  theoremIdentifiesSameRawSourceBeyondSharedGeneratedBranchSupport : Prop

/-- Corrected provenance interface after the latest external kill pass. The
honest positive theorem is no longer that weak branch-local compatibility forces
same-source identity, but that a common raw pullback witness is explicitly
stored and drives both the stream-side and observable-side constructions. -/
structure SelectedBranchStreamObservableRawPullbackWitness where
  selectedGeneratedBranchIsNamed : Prop
  commonRawSignedSourceIsNamed : Prop
  streamSidePresentationIsProducedFromThatRawSource : Prop
  observableSidePresentationIsProducedFromThatRawSourceBeforeLedgering : Prop
  branchLocalAlignmentIsInducedByThatRawSource : Prop

/-- Same-source storage theorem for the selected branch. This is the narrower
positive theorem that actually pays provenance once weak co-location/alignment
has been shown insufficient. -/
structure SelectedBranchStreamObservableSameSourceStorageTheorem where
  witness : SelectedBranchStreamObservableRawPullbackWitness
  preLedgerOrderingIsStored : Prop
  rawFiniteProfileMobiusAuditCompatibilityIsStored : Prop
  theoremPaysSameSourceProvenanceHonestly : Prop

/-- Exact noninjectivity kill shell highlighted by the latest external pass.
Threshold-root or replay-level observable agreement can identify distinct raw
signed sources, so it cannot by itself determine same-source provenance. -/
structure ThresholdRootObservableNoninjectiveOnRawSources where
  twoDistinctRawSourcesExist : Prop
  thresholdRootOrReplayObservableAgreesOnThoseSources : Prop
  weakBranchLocalCompatibilityCanStillHold : Prop

/-- Direct kill shell from the latest external pass. Weak branch-local
compatibility can hold in full while same-source storage still fails, so the
new storage theorem is not a consequence of co-location, stream match,
threshold/sigma alignment, and internal no-posthoc facts alone. -/
structure WeakBranchLocalCompatibilityDoesNotImplySameSourceStorageTheorem where
  sharedBranchSupportHolds : Prop
  branchLocalAlignmentAndTransportHold : Prop
  thresholdRootOrReplayCompatibilityHolds : Prop
  sameSourceStorageStillFails : Prop

/-- Sharper partial support on the corrected storage target. The observable side
already has stronger nearby receipts for being produced before ledgering inside
the generated corridor; the hardest surviving field is the GP216 stream-side
raw pullback from the same common raw source. -/
structure ObservableSidePreLedgerRawPullbackSupport where
  commonRawSignedSourceStillNeedsName : Prop
  observableSidePresentationIsProducedFromThatRawSourceBeforeLedgeringIsClosestToPaid : Prop
  branchLocalAlignmentCanAlreadyBeInducedInsideObservableCorridor : Prop
  streamSidePresentationFromThatSameRawSourceStillLooksHardest : Prop

/-- Sharper GP216-side support after reading the projected-stream audited-output
route. The selected branch stream can be built and audited from the projected
continuum stream, but this still does not name a common raw signed source that
would feed the corrected same-source storage theorem. -/
structure GP216ProjectedStreamAuditedOutputSupport where
  selectedProjectedStreamIsNamed : Prop
  auditedOutputBundleIsBuiltFromThatSelectedProjectedStream : Prop
  supportStillStopsShortOfNamingCommonRawSignedSource : Prop

/-- Stronger GP216-side support from the projected audited / measure-valued
route. This is the best source-preserving GP216 path currently visible: the
selected projected stream, its audited output receipt, and compactness-bearing
measure-valued provenance all remain attached. Even so, this still does not
name a common raw signed source shared with the Phase 5FB corridor. -/
structure GP216ProjectedStreamOutputDerivedSourceProvenanceSupport where
  selectedProjectedAuditedSourceIsNamed : Prop
  selectedProjectedMeasureValuedSourceIsNamed : Prop
  selectedProjectedCompactnessProvenanceIsNamed : Prop
  strongestGP216SourcePreservingRouteStillStopsShortOfCommonRawSignedSource : Prop

/-- Exact GP216-side theorem target after mining the selected projected-stream
audited / measure-valued route. What is still missing is not more projected or
output-derived provenance, but a common raw signed source named before the
selected projected stream is formed. -/
structure GP216SelectedBranchCommonRawPullbackTarget where
  selectedGeneratedBranchIsNamed : Prop
  commonRawSignedSourceIsNamedBeforeProjectedStreamFormation : Prop
  projectedSelectedBranchStreamIsProducedFromThatRawSource : Prop
  auditedOrMeasureValuedSelectedBranchSourceIsProducedFromThatRawSource : Prop

/-- Earliest GP216-side subfield after the latest mining pass. Before asking
for full common raw pullback, the route first has to name the common raw signed
source itself before projected-stream formation. -/
structure GP216SelectedBranchRawSourceNamingTarget where
  selectedGeneratedBranchIsNamed : Prop
  commonRawSignedSourceIsNamedBeforeProjectedStreamFormation : Prop

/-- Honest positive interface suggested by the latest GP216 mega pass. The raw
source is not reconstructed from projected provenance after the fact; it is
explicitly stored together with the facts that it projects to the selected
stream and underlies the downstream selected-source objects. -/
structure GP216SelectedBranchRawSourceStorageWitness where
  selectedGeneratedBranchIsNamed : Prop
  commonRawSignedSourceIsExplicitlyStored : Prop
  projectedSelectedBranchStreamIsGeneratedFromThatRawSource : Prop
  downstreamSelectedSourcesAreCertifiedDescendantsOfThatRawSource : Prop

/-- Narrower positive theorem shell below the older full common-pullback
target. This is the GP216-side statement that the selected projected stream is
actually generated from an explicitly stored raw source, without pretending
that current downstream projected provenance recovers that source by itself. -/
structure GP216SelectedBranchProjectedStreamGeneratedFromRawSource where
  witness : GP216SelectedBranchRawSourceStorageWitness
  theoremNamesProjectedStreamAsProjectionOfStoredRawSource : Prop

/-- Exact negative verdict on the mined GP216 source chain. Even the strongest
current projected-stream / audited-output / compactness-provenance route can
hold while the common raw pullback target still fails. -/
structure GP216OutputDerivedSourceProvenanceDoesNotImplyCommonRawPullback where
  selectedProjectedAndAuditedOutputSourcesAreNamed : Prop
  projectedMeasureValuedAndCompactnessSourcesAreNamed : Prop
  commonRawSignedSourceStillNotNamedBeforeProjectedStreamFormation : Prop

/-- Earliest GP216-side counterproof split. Output-derived and compactness-
provenance selected-source layers can already be paid while raw-source naming
before projected-stream formation still fails. -/
structure GP216OutputDerivedProvenanceDoesNotImplyRawSourceNaming where
  outputDerivedSelectedSourcesAreNamed : Prop
  compactnessBearingSelectedSourcesAreNamed : Prop
  commonRawSignedSourceStillNotNamedBeforeProjectedStreamFormation : Prop

/-- Stronger negative verdict after the latest GP216 mega pass. Even if the
entire selected projected-source chain is source-preserving at its own level,
that still does not produce an explicit raw-source storage witness. -/
structure GP216DownstreamProjectedProvenanceDoesNotImplyRawSourceStorageWitness where
  selectedProjectedStreamIsNamed : Prop
  auditedMeasureValuedCompactnessSourcesAreNamed : Prop
  selectedFamilyObservableSubatomsAreNamed : Prop
  explicitRawSourceStorageWitnessStillFails : Prop

/-- The nearest existing GP216 object to the missing raw-source naming field is
the selected-family observable subatom. It already stays on the same selected
approximation family, but it begins after the selected projected stream has
been formed. -/
structure GP216SelectedFamilyObservableSubatomNearestRawNamingSupport where
  selectedFamilyObservableSourceIsNamed : Prop
  sameApproximationFamilyAsSelectedProjectedStreamIsNamed : Prop
  supportStillStartsAfterProjectedStreamFormation : Prop

/-- Partial positive support below the full GP216 raw-source storage witness.
The selected-family / compactness-provenance route appears close to paying the
fact that downstream selected-source objects are descendants of one selected
projected branch stream, even though it still does not store the raw source
that precedes projection. -/
structure GP216SelectedProjectedDescendantCertificationSupport where
  selectedFamilyObservableSubatomsAreNamed : Prop
  compactnessProvenanceUsesTheSameApproximationFamily : Prop
  downstreamSelectedSourcesLookClosestToCertifiedDescendants : Prop
  rawSourceStorageStillNeedsSeparateWitness : Prop

/-- Closest upstream support for the projected-stream-from-source field on the
GP216 side. The continuum all-output family source is genuinely source-first
and pays projected-stream generation from its own all-output/component source,
but it still does not identify a pre-projection raw signed source. -/
structure GP216ContinuumAllOutputFamilySourceNearestProjectedGenerationSupport where
  streamFamilySourceIsNamed : Prop
  projectedStreamMatchesBlockByConstruction : Prop
  projectedSelectedStreamLooksGeneratedFromUpstreamFamilySource : Prop
  upstreamFamilySourceStillDoesNotNamePreProjectionRawSignedSource : Prop

/-- Next bridge on the GP216 side after storage witness language is separated
from downstream provenance. Even if GP216 stores a raw source before
projection, the file still needs a theorem that this stored source carries the
actual branch-local signed observable / fully charged interface used by the
clean-side raw carrier APIs. -/
structure GP216RawSourceStorageToActualObservableCarrierTarget where
  rawSourceStorageWitnessIsNamed : Prop
  storedRawSourceCarriesBranchLocalSignedObservable : Prop
  storedRawSourceIsFullyChargedAtPreLedgerStage : Prop
  storedRawSourceSupportsSelectedBranchRawCarrierAPI : Prop

/-- Exact theorem shell for upgrading the GP216-side raw-source storage witness
to the existing branch-local raw carrier API. -/
structure GP216RawSourceStorageToActualObservableCarrierTheorem where
  target : GP216RawSourceStorageToActualObservableCarrierTarget
  theoremProducesSelectedBranchRawCarrier : Prop

/-- Counterproof shell for the same bridge. A GP216 raw-source storage witness
could exist abstractly while the file still lacks the stronger identification
that this stored source is the actual branch-local signed observable carrier
used by the clean-side raw APIs. -/
structure GP216RawSourceStorageDoesNotYetFixActualObservableCarrier where
  rawSourceStorageWitnessExistsAbstractly : Prop
  actualBranchLocalSignedObservableCarrierStillNeedsBridge : Prop

/-- GP216 also contains several internal "same source bundle" identities, but
they concern reserve, event, or bundle bookkeeping layers rather than the
selected-branch raw signed source needed here. This support is worth recording
so grep hits on "same source" do not get over-read as latent raw pullback
provenance. -/
structure GP216InternalSameSourceBundleLanguageSupport where
  phaseReserveSameSourceEqualityIsNamed : Prop
  lowBeatOrEventBundleSameSourceLanguageIsNamed : Prop
  supportLivesInInternalGP216BundleBookkeeping : Prop
  supportDoesNotNameSelectedBranchCommonRawSource : Prop

/-- Counterproof shell for the internal GP216 "same source bundle" language.
Those bundle equalities can all hold while the selected-branch common raw
pullback still fails. -/
structure GP216InternalSameSourceBundleLanguageDoesNotImplyCommonRawPullback where
  internalSameSourceBundleLanguageExists : Prop
  selectedBranchCommonRawPullbackStillFails : Prop

/-- Exact kill shell on the cross-corridor provenance side. Branch-local
alignment, stream match, and threshold-coordinate transport can all hold while
same-source raw identity across the two corridors still fails. -/
structure AlignmentTransportDoesNotImplyJointProvenance where
  branchLocalAlignmentAndTransportObjectsExist : Prop
  sameRawSourceAcrossTheTwoCorridorsStillFails : Prop

/-- Exact support for the pre-ledger ordering side inside the Phase 5FB
observable corridor. The nearby source-binding objects already encode declared-
before-payoff and non-posthoc facts internally, even though they do not by
themselves pay cross-corridor joint provenance. -/
structure Phase5FBObservableCorridorOrderingSupport where
  declaredBeforePayoffSupportIsNamed : Prop
  nonposthocSelectionSupportIsNamed : Prop
  supportLivesInsideObservableCorridorOnly : Prop

/-- Exact source-witness target on the raw-audit side. The issue is not merely
whether a Mobius audit can be defined abstractly, but whether that audit is
performed on the actual selected-branch raw source before ledgering rather than
on a surrogate or post-ledger object. -/
structure SelectedGeneratedBranchRawMobiusActualSourceWitnessTarget where
  finiteProfileRawMobiusAuditIsNamed : Prop
  auditUsesActualSelectedBranchRawSource : Prop
  auditIsNotReadOffFromPostLedgerReplay : Prop

/-- Exact theorem shell for the raw-audit source-witness seam. -/
structure SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem where
  target : SelectedGeneratedBranchRawMobiusActualSourceWitnessTarget
  theoremSuppliesActualSourceWitnessForRawMobiusAudit : Prop

/-- Sharper restatement of the secondary clean-side seam after splitting off
branch-local ordering/pre-ledger support. What remains is actual-source-backed
finite-profile Möbius support beyond that already-visible ordering layer. -/
structure SelectedGeneratedBranchMobiusSupportBeyondOrderingTarget where
  branchLocalOrderingSupportIsNamed : Prop
  finiteProfileRawMobiusAuditIsNamed : Prop
  actualSourceBackedMobiusSupportStillNeedsTheorem : Prop

/-- Exact theorem shell for the sharper Möbius-support-beyond-ordering seam. -/
structure SelectedGeneratedBranchMobiusSupportBeyondOrderingTheorem where
  target : SelectedGeneratedBranchMobiusSupportBeyondOrderingTarget
  theoremSuppliesActualSourceBackedMobiusSupportBeyondOrdering : Prop

/-- Branch-local source-audit shell after the latest reductions. This is the
selected-generated-branch form of the older source-audit surface, kept local so
the frontier cannot hide behind the broader all-global-block API. -/
structure SelectedGeneratedBranchObservableOrderingSupport where
  selectedGeneratedBranchIsNamed : Prop
  thresholdRootObservableSourceOnThatBranchIsNamed : Prop
  sourceStageDeclaredBeforeThresholdAndSurvivalLayers : Prop

/-- Exact kill shell for the split source-audit layer. Branch-local
ordering/support can already hold while the actual finite-profile Möbius audit
support is still missing. -/
structure ObservableOrderingSupportDoesNotImplyBranchSourceAudit where
  branchLocalObservableOrderingSupportExists : Prop
  finiteProfileMobiusAuditSupportStillFails : Prop

/-- Branch-local source-audit shell after the latest reductions. This is the
selected-generated-branch form of the older source-audit surface, kept local so
the frontier cannot hide behind the broader all-global-block API. -/
structure SelectedGeneratedBranchObservableSourceAuditTarget where
  selectedGeneratedBranchIsNamed : Prop
  thresholdRootObservableSourceOnThatBranchIsNamed : Prop
  sourceStageDeclaredBeforeThresholdAndSurvivalLayers : Prop
  sourceStageSupportsFiniteProfileMobiusAudit : Prop

/-- Exact kill shell on the raw-audit side. A finite-profile Mobius audit may
exist at the abstract shell level while still failing to certify that it was
performed on the actual selected-branch raw source rather than on a surrogate
or post-ledger replay object. -/
structure SurrogateOrPostLedgerMobiusAuditDoesNotImplyActualSourceWitness where
  finiteProfileMobiusAuditShellExists : Prop
  actualSelectedBranchRawSourceStillIsNotWitnessed : Prop
  postLedgerOrSurrogateAuditCanMasqueradeAsRawAudit : Prop

/-- Conditional kill shell after the branch-local source-audit split. Even if
the local branch source-audit shell is paid, that still does not certify joint
same-source provenance across the GP216 and Phase 5FB corridors. -/
structure BranchSourceAuditDoesNotImplyJointProvenance where
  branchLocalSourceAuditShellExists : Prop
  sameRawSourceAcrossTheTwoCorridorsStillFails : Prop

/-- Exact raw-audit certificate identified by the external Phase 5FB attack.
The finite-profile Mobius audit must be performed on the raw stage before
ledgering, and the local branch must certify that this ordering is preserved. -/
structure RawFiniteProfileMobiusAuditCompatibility where
  rawFiniteProfileAuditIsNamed : Prop
  rawAuditIsPerformedBeforeReplayLedgerMap : Prop
  postLedgerAuditIsNotUsedAsASubstitute : Prop

/-- Exact strengthened theorem surfaced by the external Phase 5FB attack.
Replay transport plus this storage theorem yields the raw-stage carrier; replay
transport by itself does not. -/
structure Phase5FBRawStageStorageTheorem where
  replayLedgerMap : Phase5FBReplayLedgerMap
  preLedgerOrdering : PreLedgerOrderingCertificate
  sameSourceProvenance : SameSourceRawProvenanceCertificate
  rawMobiusAuditCompatibility : RawFiniteProfileMobiusAuditCompatibility
  theoremExposesLocalRawCarrier : Prop

/-- Exact kill-side theorem surfaced by the external Phase 5FB attack. A
replay object over a non-injective ledger map does not determine the same raw
signed source unless stronger storage fields are added. -/
structure Phase5FBReplayDoesNotDetermineRawSignedSource where
  replayLedgerMapIsNonInjective : Prop
  replayDataAloneDoesNotFixSameRawSignedSource : Prop
  replayToRawUpgradeNeedsExplicitStorageWitnesses : Prop

/-- Cheap finite obstruction shell identified by the external Phase 5FB attack:
positive-part / threshold ledgering is already enough to make the replay map
non-injective. -/
structure PositivePartLedgerNoninjective where
  positivePartOrThresholdMapIsNamed : Prop
  distinctRawSignedInputsCanShareOneLedgeredReplayImage : Prop

/-- Exact anti-laundering statement on the Phase 5FB side after the scout and
DARWIN passes. This prevents the local queue from silently collapsing the
replay model into the raw carrier. -/
structure Phase5FBReplayModelTooWeakAsRawCarrier where
  generatedObservableReplayModelExists : Prop
  replayModelByItselfIsNotYetLocalRawCarrier : Prop
  rawCarrierNeedsExtraPreLedgerAndMobiusTheorem : Prop

/-- Final exact assembly target after both upstream transports are available. -/
structure SelectedGeneratedBranchCleanSourceAssemblyTarget where
  bothExactTransportTargetsArePaid : Prop
  localCleanSourceBundleStillNeedsExactAssembly : Prop

/-- Localized mirror of the exact GP216 selected-branch stream-match model.

This avoids importing the upstream file while still naming the precise payload
the local transport theorem would need from GP216. -/
structure GP216SelectedBranchProjectedStreamModelWitness where
  projectedSelectedBranchStream : LeraySelfTaxProfilePriceStream
  auditedSelectedBranchSelfTaxStream : LeraySelfTaxProfilePriceStream
  selectedBranchProjectedStreamMatchesAuditedSelfTax :
    projectedSelectedBranchStream = auditedSelectedBranchSelfTaxStream

/-- Localized mirror of the exact Phase 5FB generated observable replay model.

This is intentionally weaker than the raw-signed-source carrier: it only names
the generated observable and charge package, not the pre-ledger ordering or
Mobius-audit compatibility. -/
structure Phase5FBGeneratedObservableReplayModelWitness where
  observable : SignedObservable
  observableFullyCharged :
    GlobalSignedObservableFullyCharged observable
  replayModelDeclaredOnGeneratedBranch : Prop

/-- Exact theorem shell for transporting the GP216 selected-branch projected
stream-match model into the local carrier. This avoids pretending that naming
the upstream object is already the same as having the local carrier. -/
structure GP216SelectedBranchProjectedStreamTransportTheorem where
  transportTarget : GP216SelectedBranchProjectedStreamTransportTarget
  localCarrier : SelectedGeneratedBranchProjectedStreamEqualityCarrier
  transportUsesSelectedBranchProjectedStreamModel : Prop

/-- Exact theorem shell for transporting the Phase 5FB raw-observable model
into the local branch-local raw-signed-source carrier. -/
structure Phase5FBRawObservableTransportTheorem where
  transportTarget : Phase5FBRawObservableTransportTarget
  localCarrier : SelectedGeneratedBranchRawSignedSourceCarrier
  transportPreservesPreLedgerOrderingAndMobiusAudit : Prop

/-- Exact theorem shell for assembling the two local carriers into the branch-
local clean-source bundle that the clean route actually needs. -/
structure SelectedGeneratedBranchCleanSourceAssemblyTheorem where
  assemblyTarget : SelectedGeneratedBranchCleanSourceAssemblyTarget
  localBundle : SelectedGeneratedBranchCleanSourceBundle
  assemblyUsesBothTransportTheorems : Prop

/-- Earliest transport-side anti-laundering risks after the scout pass.

Even with the right upstream models in hand, the local route can still cheat by
creating a dependency cycle, swapping in a surrogate stream, or silently using
post-ledger data as if it were the raw source. -/
structure SelectedGeneratedBranchTransportAntiLaunderingRisk where
  dependencyCycleRisk : Prop
  surrogateStreamSwapRisk : Prop
  postLedgerRawStageSubstitutionRisk : Prop

/-- Meta-DARWIN correction on the current queue. The GP216 side is already an
exact upstream model, but the Phase 5FB side is still only a generated
observable replay model until a separate raw-stage theorem is paid. -/
structure SelectedGeneratedBranchQueueExactnessAudit where
  gp216SideAlreadyExactUpstreamModel : Prop
  phase5fbSideStillOneAbstractionTooLate : Prop
  earliestFakeStepIsCallingReplayModelARawCarrier : Prop

/-- Refined first theorem target after the GP216 selected-branch read.

This keeps the route honest about overreach: if the current fork only needs the
projected selected-branch stream equality on the generated branch, then the
next theorem should target that equality directly instead of still pretending a
global block-universe identification theorem is the minimal requirement. -/
structure PressureFirstRefinedSelectedBranchTarget where
  selectedBranchProjectedStreamEqualityIsFirst : Prop
  fullGlobalBlockIdentificationIsStrongerThanCurrentNeed : Prop
  pressureTailStillWaitsForActualObservableSourceMatch : Prop
  branchLocalRawStageStorageIsAlsoRequired : Prop
  exactBranchLocalWitnessesStillNeedToBeBuilt : Prop

/-- Weaker positive theorem suggested by the external result.

This is the honest source theorem on the image of the generated-trajectory map:
compatibility may hold after pulling the continuum source back to generated
trajectory blocks, even though the global theorem over all Track B blocks is
too strong. -/
structure GeneratedTrajectoryPullbackSourceCompatibility where
  compatibilityHoldsOnGeneratedTrajectoryImage : Prop
  theoremIsTrajectoryBoundRatherThanGlobal : Prop
  thresholdRootSourceIsComparedOnlyAfterPullback : Prop

/-- First exact extra hypothesis needed for the stronger global theorem:
every global Track B block must arise from the generated trajectory corridor. -/
structure GeneratedTrajectoryCoversGlobalTrackBBlocks where
  everyGlobalTrackBBlockAppearsInGeneratedTrajectoryImage : Prop

/-- Second exact extra hypothesis: if two generated trajectories land on the
same global block, they must induce the same threshold-root source. -/
structure GeneratedTrajectoryFiberCoherence where
  thresholdRootObservableAgreesOnFibers : Prop
  generatedAuxiliaryObservableDataAgreesOnFibers : Prop

/-- Third exact extra hypothesis: the threshold-root observable source must
explicitly carry or recover the raw pre-ledger signed source. -/
structure ThresholdRootStoresRawSignedSource where
  rawSignedSourceCanBeReadBeforeLedgerPostProcessing : Prop
  thresholdRootDoesNotEraseTheNeededRawObservableStage : Prop

/-- Fourth exact extra hypothesis: the finite-profile Möbius audit must be
lawful at the raw stage and commute with pullback to generated blocks. -/
structure RawMobiusAuditCommutesWithGeneratedPullback where
  rawMobiusAuditAppliedBeforeLedger : Prop
  pullbackPreservesRawMobiusAudit : Prop

/-- Exact strengthened package required to resurrect the literal global theorem
after the external obstruction note. -/
structure GlobalTrackBBlockGeneratedTrajectoryIdentificationUpgrade where
  coverage : GeneratedTrajectoryCoversGlobalTrackBBlocks
  fiberCoherence : GeneratedTrajectoryFiberCoherence
  rawStorage : ThresholdRootStoresRawSignedSource
  rawMobiusPullback : RawMobiusAuditCommutesWithGeneratedPullback

/-- Explicit no-go surface: using the clean branch for the actual Track B
observable is substitution unless the bridge to the pre-ledger cubic surrogate
is proved. -/
structure ActualObservableSubstitutionHazard where
  actualObservableClassification : ActualTrackBObservableClassification
  smugglingRisk : CleanBranchSmugglingRisk
  usingCleanBranchAsIfItWereTheActualObservableIsIllegitimate : Prop

/-- Named frontier after the current audits. This keeps the next theorem
target singular: first prove or kill the actual-observable-to-pre-ledger-cubic
bridge; only on the clean side does the pressure-pair decomposition become the
whole next analytic theorem. -/
structure PressureFirstNextHonestTheoremTarget where
  actualObservableToPreLedgerBridgeIsFirst : Prop
  pressurePairDecompositionIsNextOnlyAfterCleanBridge : Prop
  contaminatedBranchRemainsDefaultUntilBridgeProved : Prop

/-- Current clean-side theorem-frontier summary after the GP216 raw-source
storage mega pass. This tracks the internal theorem queue inside the broader
actual-observable bridge program. -/
structure PressureFirstCurrentCleanSideStreamDebt where
  gp216RawSourceStorageWitnessIsDominantStreamSideDebt : Prop
  observableSidePreLedgerAndBranchAuditWorkAreDownstreamOfThatDebt : Prop
  downstreamProjectedProvenanceCannotStandInForStoredRawSource : Prop

/-- Whole-graph verdict from the rebuilt NS Track B artifact graph plus the
closure miner. The top open surface is still the core self-tax profile-price
stream, so the current GP216 storage debt matters only insofar as it feeds
that larger stream-level object rather than remaining a local bookkeeping
exercise. -/
structure LeraySelfTaxProfilePriceStreamWholeGraphDominantSurface where
  topOpenObligationInClosureMiner : Prop
  topArtifactLevelOpenSurfaceByReverseUse : Prop
  currentStreamSideDebtUltimatelyFeedsThisSurface : Prop

/-- Whole-graph verdict for the current GP216 seam. The active raw-source
storage debt is not itself a top-usage hub, but it is the earliest remaining
stream-side field blocking the globally ranked `GP216BridgeCompositionReceipt`
surface from being interpreted honestly at the raw-source level. -/
structure GP216BridgeCompositionReceiptWholeGraphRelevance where
  bridgeCompositionReceiptIsGraphRankedTarget : Prop
  currentGp216RawSourceStorageDebtFeedsThatTarget : Prop
  currentFrontierIsLocalButNotIsolatedFromWholeGraph : Prop

/-- The current file and its imported route surfaces already exhibit ledgered
machinery, so the contaminated branch is not an invented possibility. The live
question is whether the specific observable used for the profile-price route can
be isolated at a pre-ledger cubic stage before those layers act. -/
def trackb_ledger_contamination_surface_present :
    TrackBLedgerContaminationSurface := by
  exact {
    thresholdCoordinateLayerPresent := True
    survivalLedgerLayerPresent := True
    noSurvivorLayerPresent := True
    positiveCoherenceLayerPresent := True
  }

/-- Imported-source version of the same contamination evidence. The point is
not that each imported file kills the clean branch by itself, but that the
actual observable spine is visibly ledger-rich before any separate pre-ledger
restriction theorem is proved. -/
def trackb_ledger_contamination_source_bundle_present :
    TrackBLedgerContaminationSourceBundle := by
  exact {
    allOutputPositiveCoherenceAdapterPresent := True
    thresholdRootIdentityLayerPresent := True
    quarticSurvivalProjectionLayerPresent := True
    noSurvivorProjectionLayerPresent := True
  }

/-- File-local anti-smuggling source verdict distilled from the surrounding
Track B observable modules. -/
def trackb_observable_anti_smuggling_sources_present :
    TrackBObservableAntiSmugglingSources := by
  exact {
    thresholdDefectNeedsSameSurvivalObservable := True
    unrestrictedSurvivalProjectionSourceFamilyFails := True
    positiveOutputSurplusLayerPresent := True
    hiddenSourceL2PricingIsInsufficient := True
  }

/-- Local observable audit verdict: given the currently visible threshold /
survival / no-survivor / positive-coherence layers, the route should default
to the contaminated branch unless a separate theorem isolates a genuinely
pre-ledger cubic observable. -/
def actual_trackb_observable_classification_present :
    ActualTrackBObservableClassification := by
  let hSources : TrackBLedgerContaminationSourceBundle :=
    trackb_ledger_contamination_source_bundle_present
  exact {
    contaminationSurface := trackb_ledger_contamination_surface_present
    preLedgerRestrictionStillNeedsToBeProved :=
      hSources.allOutputPositiveCoherenceAdapterPresent ∨
      hSources.thresholdRootIdentityLayerPresent ∨
      hSources.quarticSurvivalProjectionLayerPresent ∨
      hSources.noSurvivorProjectionLayerPresent
    contaminatedBranchIsALiveDefaultUntilThatProofExists :=
      hSources.allOutputPositiveCoherenceAdapterPresent ∨
      hSources.thresholdRootIdentityLayerPresent ∨
      hSources.quarticSurvivalProjectionLayerPresent ∨
      hSources.noSurvivorProjectionLayerPresent
  }

/-- Current bottleneck neighborhood classification after the graph-side audit:
the pressure-first fork sits upstream of the larger Lipschitz/no-survivor
continuation layer, even though those objects remain globally central. -/
def pressure_first_current_bottleneck_neighborhood_present :
    PressureFirstCurrentBottleneckNeighborhood := by
  exact {
    legacyPriceStreamIsUpstream := True
    profileDecompositionAndHypergraphExpansionAreUpstream := True
    pressurePairDecompositionAndTailEnvelopeAreUpstream := True
    cutoffPressureWindowLiabilitiesAreUpstream := True
    lipschitzReserveBridgesAreDownstreamForThisFork := True
    noSurvivorLedgerObjectsAreBackgroundRatherThanCurrentSeam := True
  }

/-- Current local smuggling audit verdict. Until a theorem really isolates the
actual observable at a pre-ledger cubic stage, the clean branch must be treated
as a restricted surrogate rather than as the current Track-B object itself. -/
def clean_branch_smuggling_risk_present : CleanBranchSmugglingRisk := by
  exact {
    actualObservableStillCarriesLedgerLayers := True
    preLedgerCubicSurrogateHasBeenNamedSeparately := True
    theoremConnectingActualObservableToSurrogateIsStillMissing := True
  }

/-- The current imported source bundle exposes the exact earlier target behind
the missing bridge: the route must identify a raw signed-observable stage
before the threshold / survival / no-survivor / positive-coherence layers. -/
def pressure_first_raw_stage_extraction_target_present :
    PressureFirstRawStageExtractionTarget := by
  let hSources : TrackBLedgerContaminationSourceBundle :=
    trackb_ledger_contamination_source_bundle_present
  exact {
    signedObservableStageIsNamed := True
    stageOccursBeforeThresholdAndSurvivalLayers :=
      hSources.thresholdRootIdentityLayerPresent ∨
      hSources.quarticSurvivalProjectionLayerPresent ∨
      hSources.noSurvivorProjectionLayerPresent
    stageMatchesFiniteProfilePriceFunctional := True
    stageCanBeAuditedByFourProfileMobiusTest := True
  }

/-- Current negative source-facing verdict: the file can name the source APIs
that ought to feed the clean branch, but it has not yet instantiated a real
observable-source audit target from them. -/
def pressure_first_observable_source_audit_gap_present :
    PressureFirstObservableSourceAuditGap := by
  exact {
    actualStreamFamilyStillNeedsRawStageIsolation := True
    thresholdRootObservableSourceStillNeedsPreLedgerPlacement := True
    finiteProfileMobiusAuditStillLacksActualSourceWitness := True
  }

/-- Current source-level mismatch reported honestly: the best stream-family
source and the best threshold-root observable source do not yet quantify over
the same block universe. -/
def pressure_first_observable_source_compatibility_gap_present :
    PressureFirstObservableSourceCompatibilityGap := by
  exact {
    continuumStreamFamilyRangesOverAllGlobalBlocks := True
    thresholdRootObservableSourceRangesOnlyOverGeneratedBlocks := True
    missingIdentificationBetweenGlobalAndGeneratedBlocks := True
  }

/-- The current compatibility gap already singles out the exact missing
identification theorem rather than leaving the mismatch at the level of vague
"different block universes" prose. -/
def missing_global_trackb_block_generated_trajectory_identification_present :
    GlobalTrackBBlockGeneratedTrajectoryIdentification := by
  exact {
    everyGlobalTrackBBlockAppearsAsGeneratedLipschitzBlock := True
    identificationPreservesContinuumStreamFamilyChoice := True
    identificationPreservesThresholdRootObservableSource := True
  }

/-- The current source-compatibility gap is not three unrelated complaints.
It reduces to one missing identification theorem between the global Track-B
block universe and the generated trajectory block corridor. -/
def pressure_first_source_compatibility_gap_reduces_to_identification_gap
    (hGap : PressureFirstObservableSourceCompatibilityGap) :
    GlobalTrackBBlockGeneratedTrajectoryIdentification := by
  exact {
    everyGlobalTrackBBlockAppearsAsGeneratedLipschitzBlock :=
      hGap.missingIdentificationBetweenGlobalAndGeneratedBlocks
    identificationPreservesContinuumStreamFamilyChoice :=
      hGap.continuumStreamFamilyRangesOverAllGlobalBlocks
    identificationPreservesThresholdRootObservableSource :=
      hGap.thresholdRootObservableSourceRangesOnlyOverGeneratedBlocks
  }

/-- Current source inventory suggests the global identification theorem may be
stronger than the live fork actually needs.  GP216 already names the generated
selected branch and its projected continuum stream; the remaining source seam is
the equality between that projected selected-branch stream and the audited
self-tax output stream. -/
def selected_generated_branch_projected_stream_compatibility_target_present :
    SelectedGeneratedBranchProjectedStreamCompatibilityTarget := by
  exact {
    generatedBranchBlockAlreadyNamedByHandoff := True
    continuumProjectedSelectedBranchStreamAlreadyDefined := True
    thresholdRootObservableSourceAlreadyLivesOnGeneratedBranch := True
    missingOnlyProjectedSelectedBranchStreamEqualityToAuditedSelfTaxStream := True
  }

/-- The earlier global compatibility gap is honest, but for the current
pressure-first fork it may overstate what must be proved.  Once the generated
selected branch is named by the continuation handoff and the threshold-root
observable already lives on that branch, the immediate source target can be
reduced to projected selected-branch stream equality. -/
def pressure_first_source_compatibility_gap_can_be_reduced_to_selected_branch_target
    (hGap : PressureFirstObservableSourceCompatibilityGap) :
    SelectedGeneratedBranchProjectedStreamCompatibilityTarget := by
  exact {
    generatedBranchBlockAlreadyNamedByHandoff :=
      hGap.thresholdRootObservableSourceRangesOnlyOverGeneratedBlocks
    continuumProjectedSelectedBranchStreamAlreadyDefined :=
      hGap.continuumStreamFamilyRangesOverAllGlobalBlocks
    thresholdRootObservableSourceAlreadyLivesOnGeneratedBranch :=
      hGap.thresholdRootObservableSourceRangesOnlyOverGeneratedBlocks
    missingOnlyProjectedSelectedBranchStreamEqualityToAuditedSelfTaxStream :=
      hGap.missingIdentificationBetweenGlobalAndGeneratedBlocks
  }

/-- Current refined target after reducing the source seam through the GP216
selected-branch inventory. -/
def pressure_first_refined_selected_branch_target_present :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst := True
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed := True
    pressureTailStillWaitsForActualObservableSourceMatch := True
    branchLocalRawStageStorageIsAlsoRequired := True
    exactBranchLocalWitnessesStillNeedToBeBuilt := True
  }

/-- Once the source seam is reduced to the selected generated branch, the next
honest theorem target should be stated at that branch-local level rather than
at the stronger global block-identification level. -/
def pressure_first_next_honest_theorem_target_of_selected_branch_target
    (hTarget : SelectedGeneratedBranchProjectedStreamCompatibilityTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hTarget.missingOnlyProjectedSelectedBranchStreamEqualityToAuditedSelfTaxStream
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hTarget.generatedBranchBlockAlreadyNamedByHandoff ∧
      hTarget.thresholdRootObservableSourceAlreadyLivesOnGeneratedBranch
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hTarget.continuumProjectedSelectedBranchStreamAlreadyDefined
    branchLocalRawStageStorageIsAlsoRequired :=
      hTarget.thresholdRootObservableSourceAlreadyLivesOnGeneratedBranch
    exactBranchLocalWitnessesStillNeedToBeBuilt := True
  }

/-- Current branch-local raw-stage storage target exposed by the same external
result: even on the generated selected branch, threshold-root data is not yet
the raw signed source of the actual observable. -/
def selected_generated_branch_raw_stage_storage_target_present :
    SelectedGeneratedBranchRawStageStorageTarget := by
  exact {
    selectedGeneratedBranchAlreadyCarriesThresholdRootObservable := True
    rawSignedSourceMustBeStoredBeforeThresholdLedgering := True
    branchLocalRawStageStillNeedsActualObservableWitness := True
  }

/-- Current branch-local equality witness gap: the selected generated branch is
named abstractly, but the file has not yet produced the exact selected-branch
stream equality witness as a source object. -/
def selected_generated_branch_projected_stream_equality_witness_gap_present :
    SelectedGeneratedBranchProjectedStreamEqualityWitness := by
  exact {
    generatedSelectedBranchIsNamed := True
    projectedContinuumSelectedBranchStreamIsNamed := True
    auditedSelfTaxStreamOnSelectedBranchIsNamed := True
    projectedSelectedBranchStreamEqualsAuditedSelfTaxStream := False
  }

/-- Current branch-local raw-stage storage witness gap: the selected generated
branch already carries a threshold-root source, but the raw signed source is
not yet stored there as an actual-observable witness. -/
def selected_generated_branch_raw_signed_source_storage_witness_gap_present :
    SelectedGeneratedBranchRawSignedSourceStorageWitness := by
  exact {
    selectedGeneratedBranchThresholdRootSourceIsNamed := True
    branchLocalRawSignedSourceIsNamed := False
    rawSignedSourceIsStoredBeforeThresholdLedgering := False
    rawSignedSourceSupportsFiniteProfileMobiusAudit := False
  }

/-- Current local mirror of the GP216 upstream exact payload. -/
def gp216_selected_branch_projected_stream_model_witness_gap_present :
    GP216SelectedBranchProjectedStreamModelWitness := by
  exact {
    projectedSelectedBranchStream := zeroLeraySelfTaxProfilePriceStream
    auditedSelectedBranchSelfTaxStream := zeroLeraySelfTaxProfilePriceStream
    selectedBranchProjectedStreamMatchesAuditedSelfTax := rfl
  }

/-- Current local mirror of the Phase 5FB replay payload. -/
def phase5fb_generated_observable_replay_model_witness_gap_present :
    Phase5FBGeneratedObservableReplayModelWitness := by
  exact {
    observable := {
      kind := ObservableKind.scalar
      predeclared := True
      independentNormalized := True
      psdBallastCharged := True
      dampingCharged := True
      crossTermCharged := True
    }
    observableFullyCharged := by
      refine ⟨by decide, True.intro, True.intro, True.intro, True.intro, ?_⟩
      intro _
      exact True.intro
    replayModelDeclaredOnGeneratedBranch := True
  }

/-- Local encoding of the scout result: the neighboring files already expose
the right two branch-local source models, but not yet as this file's clean
bundle. -/
def selected_generated_branch_upstream_source_models_present :
    SelectedGeneratedBranchUpstreamSourceModels := by
  exact {
    gp216SelectedBranchProjectedStreamModelExists := True
    phase5fbGeneratedObservableReplayModelExists := True
    phase5fbRawObservableCarrierStillNeedsSubstantiveRawStageTheorem := True
    bothModelsLiveOnGeneratedBranchSide := True
  }

/-- Current import-free transport gap after the scout pass. The obstacle is no
longer 'nothing exists upstream'; it is converting the upstream models into the
exact local clean-source bundle without creating a dependency cycle or a
surrogate swap. -/
def selected_generated_branch_upstream_transport_gap_present :
    SelectedGeneratedBranchUpstreamTransportGap := by
  exact {
    streamEqualityCarrierStillNeedsImportFreeTransport := True
    rawSignedSourceCarrierStillNeedsImportFreeTransport := True
    localCleanBundleStillNeedsExactAssembly := True
  }

/-- Current exact GP216-side transport gap after the scout pass. -/
def gp216_selected_branch_projected_stream_transport_target_present :
    GP216SelectedBranchProjectedStreamTransportTarget := by
  exact {
    upstreamSelectedBranchProjectedStreamModelIsNamed := True
    localProjectedStreamEqualityCarrierStillNeedsTransport := True
    transportMustAvoidDependencyCycleAndSurrogateSwap := True
  }

/-- Current exact Phase 5FB-side transport gap after the scout pass. -/
def phase5fb_raw_observable_transport_target_present :
    Phase5FBRawObservableTransportTarget := by
  exact {
    upstreamPhase5fbRawObservableModelIsNamed := True
    localRawSignedSourceCarrierStillNeedsTransport := True
    transportMustPreservePreLedgerOrderingAndMobiusAudit := True
  }

/-- DARWIN-corrected present gap: the upstream Phase 5FB object is first a
generated observable replay model, not yet the local raw carrier. -/
def phase5fb_generated_observable_replay_transport_target_present :
    Phase5FBGeneratedObservableReplayTransportTarget := by
  exact {
    upstreamGeneratedObservableReplayModelIsNamed := True
    localRawSignedSourceCarrierStillNeedsReplayTransport := True
  }

/-- DARWIN-corrected exact unpaid theorem on the Phase 5FB side. -/
def phase5fb_raw_stage_theorem_target_present :
    Phase5FBRawStageTheoremTarget := by
  exact {
    replayModelAloneDoesNotYetGiveRawCarrier := True
    preLedgerOrderingStillNeedsSubstantiveTheorem := True
    finiteProfileMobiusAuditStillNeedsSubstantiveTheorem := True
  }

/-- Current replay-transport theorem shell gap on the Phase 5FB side. -/
def phase5fb_generated_observable_replay_transport_theorem_gap_present :
    Phase5FBGeneratedObservableReplayTransportTheorem := by
  exact {
    transportTarget := phase5fb_generated_observable_replay_transport_target_present
    transportProducesNamedObservableAndCharge := False
  }

/-- Current substantive raw-stage theorem gap on the Phase 5FB side. -/
def phase5fb_raw_stage_theorem_gap_present :
    Phase5FBRawStageTheorem := by
  exact {
    theoremTarget := phase5fb_raw_stage_theorem_target_present
    theoremProducesLocalRawCarrier := False
    theoremPaysPreLedgerOrderingAndMobiusAudit := False
  }

/-- Sharper Phase 5FB target after splitting the substantive raw-stage theorem:
first pay explicit storage of the raw observable before any ledger action. -/
def phase5fb_threshold_root_raw_storage_target_present :
    Phase5FBThresholdRootRawStorageTarget := by
  exact {
    thresholdRootSourceNamesObservableAndCharge := True
    rawObservableStageStillNeedsExplicitStorageWitness := True
  }

/-- Sharper Phase 5FB target after splitting the substantive raw-stage theorem:
even with storage, the raw-stage Mobius audit can still fail to commute. -/
def phase5fb_raw_mobius_audit_commutation_target_present :
    Phase5FBRawMobiusAuditCommutationTarget := by
  exact {
    rawObservableStageMayBeStoredYetAuditStillNeedsSeparateTheorem := True
    finiteProfileMobiusAuditMustCommuteBeforeLedgerLayers := True
  }

/-- Current theorem-shell gap for the storage half of the substantive Phase 5FB
liability. -/
def phase5fb_threshold_root_raw_storage_theorem_gap_present :
    Phase5FBThresholdRootRawStorageTheorem := by
  exact {
    storageTarget := phase5fb_threshold_root_raw_storage_target_present
    theoremExposesRawObservableBeforeLedgerLayers := False
  }

/-- Current theorem-shell gap for the Mobius-audit half of the substantive
Phase 5FB liability. -/
def phase5fb_raw_mobius_audit_commutation_theorem_gap_present :
    Phase5FBRawMobiusAuditCommutationTheorem := by
  exact {
    auditTarget := phase5fb_raw_mobius_audit_commutation_target_present
    theoremShowsRawMobiusAuditCommutesBeforeLedgerLayers := False
  }

/-- Current named replay-ledger map on the Phase 5FB side after the external
attack. The map is present conceptually, but still treated as information-
losing until stronger storage fields are paid. -/
def phase5fb_replay_ledger_map_present :
    Phase5FBReplayLedgerMap := by
  exact {
    replayLedgerMapIsNamed := True
    thresholdSurvivalNoSurvivorPositiveCoherenceArePackedHere := True
    replayLedgerMapMayForgetRawSignedInformation := True
  }

/-- Current exact pre-ledger ordering gap on the Phase 5FB side. -/
def pre_ledger_ordering_certificate_gap_present :
    PreLedgerOrderingCertificate := by
  exact {
    rawSignedSourceExistsBeforeReplayLedgerMap := False
    rawFiniteProfileStreamIsFormedBeforeThresholding := False
    rawFiniteProfileStreamIsFormedBeforeSurvivalAndNoSurvivor := False
  }

/-- Current exact same-source provenance gap on the Phase 5FB side. -/
def same_source_raw_provenance_certificate_gap_present :
    SameSourceRawProvenanceCertificate := by
  exact {
    phase5fbRawSourceIsNamed := False
    gp216SelectedBranchRawSourceIsNamed := False
    bothNamesReferToTheSameRawSignedSource := False
  }

/-- Current exact branch-local provenance gap after the residual/void pass. -/
def selected_generated_branch_same_source_provenance_target_present :
    SelectedGeneratedBranchSameSourceProvenanceTarget := by
  exact {
    gp216SelectedBranchSideIsNamed := True
    phase5fbObservableSideIsNamed := True
    currentBridgeObjectsAreStillAlignmentOrMatchOnly := True
    sameRawSignedSourceStillNeedsExplicitIdentityCertificate := True
  }

/-- Current residual-void carrier after reading the GP216/Phase5FB interface
more closely. The nearby objects are strong branch-local compatibility shells,
but they still do not certify same-source raw identity. -/
def alignment_only_generated_branch_compatibility_present :
    AlignmentOnlyGeneratedBranchCompatibility := by
  exact {
    selectedBranchStreamMatchIsNamed := True
    generatedBranchCompatibilityIsNamed := True
    thresholdCoordinateProjectionIsNamed := True
    sameRawSourceIdentityIsStillNotCertified := True
  }

/-- Current exact support on the observable-side corridor after the residual
pass. -/
def phase5fb_observable_side_nonposthoc_binding_support_present :
    Phase5FBObservableSideNonposthocBindingSupport := by
  exact {
    generatedObservableReplayModelIsNamed := True
    generatedObservableBindingIsNamed := True
    nonposthocObservableBindingInsideObservableCorridorIsNamed := True
    supportStillStopsShortOfCrossCorridorJointProvenance := True
  }

/-- Current sharper observable/root provenance support visible in the generated
matrix route. -/
def generated_matrix_observable_root_provenance_support_present :
    GeneratedMatrixObservableRootProvenanceSupport := by
  exact {
    generatedBlockObservableMatchIsNamed := True
    generatedBlockRootLedgerMatchIsNamed := True
    supportIsInternalToGeneratedMatrixRoute := True
    supportStillDoesNotFixCrossCorridorRawSourceIdentity := True
  }

/-- Current kill shell for the sharper observable/root provenance layer. -/
def observable_root_provenance_does_not_imply_same_source_raw_certificate_present :
    ObservableRootProvenanceDoesNotImplySameSourceRawCertificate := by
  exact {
    generatedMatrixObservableRootProvenanceExists := True
    sameSourceRawCertificateStillFails := True
  }

/-- Current exact cross-corridor provenance gap after the residual/void pass. -/
def selected_branch_stream_observable_joint_provenance_target_present :
    SelectedBranchStreamObservableJointProvenanceTarget := by
  exact {
    gp216SelectedBranchStreamCorridorIsNamed := True
    phase5fbObservableCorridorIsNamed := True
    sharedGeneratedBranchSupportIsAlreadyVisible := True
    eachCorridorHasInternalProvenanceSupport := True
    jointSameSourceProvenanceAcrossTheTwoCorridorsStillNeedsTheorem := True
  }

/-- Current weaker shared-generated-branch support visible around the selected-
branch transport seam. -/
def selected_branch_stream_observable_shared_generated_branch_support_present :
    SelectedBranchStreamObservableSharedGeneratedBranchSupport := by
  exact {
    gp216SelectedGeneratedBranchSupportIsNamed := True
    phase5fbObservableCorridorGeneratedBranchSupportIsNamed := True
    bothCorridorsAreAlreadyAttachedToTheSameGeneratedBranchBlock := True
  }

/-- Current theorem-shell reading of the weaker shared-generated-branch layer.
-/
def selected_branch_stream_observable_shared_generated_branch_theorem_gap_present :
    SelectedBranchStreamObservableSharedGeneratedBranchTheorem := by
  exact {
    support :=
      selected_branch_stream_observable_shared_generated_branch_support_present
    theoremPaysSharedGeneratedBranchSupportOnly := True
  }

/-- Current counterproof shell for the weaker branch/block layer. -/
def shared_generated_branch_support_does_not_imply_joint_provenance_present :
    SharedGeneratedBranchSupportDoesNotImplyJointProvenance := by
  exact {
    sharedGeneratedBranchSupportHolds := True
    sameRawSourceAcrossTheTwoCorridorsStillFails := True
  }

/-- The older selected-branch projected-stream compatibility shell already
supplies the weaker shared-generated-branch support. It names the generated
branch block, the projected continuum stream there, and the threshold-root
observable source on that same branch. -/
def selected_branch_stream_observable_shared_generated_branch_support_of_projected_stream_compatibility_target
    (hCompat : SelectedGeneratedBranchProjectedStreamCompatibilityTarget) :
    SelectedBranchStreamObservableSharedGeneratedBranchSupport where
  gp216SelectedGeneratedBranchSupportIsNamed :=
    hCompat.generatedBranchBlockAlreadyNamedByHandoff
  phase5fbObservableCorridorGeneratedBranchSupportIsNamed :=
    hCompat.thresholdRootObservableSourceAlreadyLivesOnGeneratedBranch
  bothCorridorsAreAlreadyAttachedToTheSameGeneratedBranchBlock :=
    hCompat.generatedBranchBlockAlreadyNamedByHandoff ∧
    hCompat.thresholdRootObservableSourceAlreadyLivesOnGeneratedBranch

/-- The weaker shared-generated-branch theorem is immediate from the older
selected-branch projected-stream compatibility shell. This exposes that the
remaining seam is not branch co-location itself, but same-source provenance
beyond that co-location. -/
def selected_branch_stream_observable_shared_generated_branch_theorem_of_projected_stream_compatibility_target
    (hCompat : SelectedGeneratedBranchProjectedStreamCompatibilityTarget) :
    SelectedBranchStreamObservableSharedGeneratedBranchTheorem where
  support :=
    selected_branch_stream_observable_shared_generated_branch_support_of_projected_stream_compatibility_target
      hCompat
  theoremPaysSharedGeneratedBranchSupportOnly := True

/-- Current exact theorem-shell gap on the cross-corridor provenance seam. -/
def selected_branch_stream_observable_joint_provenance_theorem_gap_present :
    SelectedBranchStreamObservableJointProvenanceTheorem := by
  exact {
    target := selected_branch_stream_observable_joint_provenance_target_present
    theoremIdentifiesSameRawSourceAcrossTheTwoCorridors := False
  }

/-- Current sharper reading of the same dominant seam after splitting off
shared-generated-branch support. -/
def selected_branch_stream_observable_same_source_beyond_shared_branch_target_present :
    SelectedBranchStreamObservableSameSourceBeyondSharedBranchTarget := by
  exact {
    sharedGeneratedBranchSupportIsNamed := True
    eachCorridorHasInternalProvenanceSupport := True
    sameRawSourceBeyondSharedGeneratedBranchStillNeedsTheorem := True
  }

/-- Current theorem-shell gap for the sharper same-source-beyond-shared-branch
reading. -/
def selected_branch_stream_observable_same_source_beyond_shared_branch_theorem_gap_present :
    SelectedBranchStreamObservableSameSourceBeyondSharedBranchTheorem := by
  exact {
    target :=
      selected_branch_stream_observable_same_source_beyond_shared_branch_target_present
    theoremIdentifiesSameRawSourceBeyondSharedGeneratedBranchSupport := False
  }

/-- Current exact gap on the corrected positive provenance interface. -/
def selected_branch_stream_observable_raw_pullback_witness_gap_present :
    SelectedBranchStreamObservableRawPullbackWitness := by
  exact {
    selectedGeneratedBranchIsNamed := True
    commonRawSignedSourceIsNamed := False
    streamSidePresentationIsProducedFromThatRawSource := False
    observableSidePresentationIsProducedFromThatRawSourceBeforeLedgering := False
    branchLocalAlignmentIsInducedByThatRawSource := False
  }

/-- Current exact theorem-shell gap on the corrected same-source storage side.
-/
def selected_branch_stream_observable_same_source_storage_theorem_gap_present :
    SelectedBranchStreamObservableSameSourceStorageTheorem := by
  exact {
    witness := selected_branch_stream_observable_raw_pullback_witness_gap_present
    preLedgerOrderingIsStored := False
    rawFiniteProfileMobiusAuditCompatibilityIsStored := False
    theoremPaysSameSourceProvenanceHonestly := False
  }

/-- Current noninjectivity kill shell surfaced by the latest external pass. -/
def threshold_root_observable_noninjective_on_raw_sources_present :
    ThresholdRootObservableNoninjectiveOnRawSources := by
  exact {
    twoDistinctRawSourcesExist := True
    thresholdRootOrReplayObservableAgreesOnThoseSources := True
    weakBranchLocalCompatibilityCanStillHold := True
  }

/-- Current direct weak-compatibility kill shell on the corrected storage
target. -/
def weak_branch_local_compatibility_does_not_imply_same_source_storage_theorem_present :
    WeakBranchLocalCompatibilityDoesNotImplySameSourceStorageTheorem := by
  exact {
    sharedBranchSupportHolds := True
    branchLocalAlignmentAndTransportHold := True
    thresholdRootOrReplayCompatibilityHolds := True
    sameSourceStorageStillFails := True
  }

/-- Current sharper partial support on the corrected storage target. -/
def observable_side_pre_ledger_raw_pullback_support_present :
    ObservableSidePreLedgerRawPullbackSupport := by
  exact {
    commonRawSignedSourceStillNeedsName := True
    observableSidePresentationIsProducedFromThatRawSourceBeforeLedgeringIsClosestToPaid := True
    branchLocalAlignmentCanAlreadyBeInducedInsideObservableCorridor := True
    streamSidePresentationFromThatSameRawSourceStillLooksHardest := True
  }

/-- Current sharper GP216-side support after reading the projected-stream
audited-output route. -/
def gp216_projected_stream_audited_output_support_present :
    GP216ProjectedStreamAuditedOutputSupport := by
  exact {
    selectedProjectedStreamIsNamed := True
    auditedOutputBundleIsBuiltFromThatSelectedProjectedStream := True
    supportStillStopsShortOfNamingCommonRawSignedSource := True
  }

/-- Current strongest GP216-side source-preserving support after reading the
projected audited / measure-valued route. -/
def gp216_projected_stream_output_derived_source_provenance_support_present :
    GP216ProjectedStreamOutputDerivedSourceProvenanceSupport := by
  exact {
    selectedProjectedAuditedSourceIsNamed := True
    selectedProjectedMeasureValuedSourceIsNamed := True
    selectedProjectedCompactnessProvenanceIsNamed := True
    strongestGP216SourcePreservingRouteStillStopsShortOfCommonRawSignedSource := True
  }

/-- Current exact GP216-side frontier after mining the selected projected
stream route. The generated branch and output-derived selected sources are
named, but the common raw signed source before projected-stream formation is
still missing. -/
def gp216_selected_branch_common_raw_pullback_target_gap_present :
    GP216SelectedBranchCommonRawPullbackTarget := by
  exact {
    selectedGeneratedBranchIsNamed := True
    commonRawSignedSourceIsNamedBeforeProjectedStreamFormation := False
    projectedSelectedBranchStreamIsProducedFromThatRawSource := False
    auditedOrMeasureValuedSelectedBranchSourceIsProducedFromThatRawSource := False
  }

/-- Current earliest GP216-side subfield gap. -/
def gp216_selected_branch_raw_source_naming_target_gap_present :
    GP216SelectedBranchRawSourceNamingTarget := by
  exact {
    selectedGeneratedBranchIsNamed := True
    commonRawSignedSourceIsNamedBeforeProjectedStreamFormation := False
  }

/-- Current honest positive GP216-side interface gap after the latest mega
pass. -/
def gp216_selected_branch_raw_source_storage_witness_gap_present :
    GP216SelectedBranchRawSourceStorageWitness := by
  exact {
    selectedGeneratedBranchIsNamed := True
    commonRawSignedSourceIsExplicitlyStored := False
    projectedSelectedBranchStreamIsGeneratedFromThatRawSource := False
    downstreamSelectedSourcesAreCertifiedDescendantsOfThatRawSource := False
  }

/-- Current narrower positive theorem-shell gap on the GP216 side. -/
def gp216_selected_branch_projected_stream_generated_from_raw_source_gap_present :
    GP216SelectedBranchProjectedStreamGeneratedFromRawSource := by
  exact {
    witness := gp216_selected_branch_raw_source_storage_witness_gap_present
    theoremNamesProjectedStreamAsProjectionOfStoredRawSource := False
  }

/-- Current exact negative verdict on the strongest visible GP216 source route.
-/
def gp216_output_derived_source_provenance_does_not_imply_common_raw_pullback_present :
    GP216OutputDerivedSourceProvenanceDoesNotImplyCommonRawPullback := by
  exact {
    selectedProjectedAndAuditedOutputSourcesAreNamed := True
    projectedMeasureValuedAndCompactnessSourcesAreNamed := True
    commonRawSignedSourceStillNotNamedBeforeProjectedStreamFormation := True
  }

/-- Current earliest GP216-side counterproof split. -/
def gp216_output_derived_provenance_does_not_imply_raw_source_naming_present :
    GP216OutputDerivedProvenanceDoesNotImplyRawSourceNaming := by
  exact {
    outputDerivedSelectedSourcesAreNamed := True
    compactnessBearingSelectedSourcesAreNamed := True
    commonRawSignedSourceStillNotNamedBeforeProjectedStreamFormation := True
  }

/-- Current stronger negative GP216-side verdict after the latest mega pass. -/
def gp216_downstream_projected_provenance_does_not_imply_raw_source_storage_witness_present :
    GP216DownstreamProjectedProvenanceDoesNotImplyRawSourceStorageWitness := by
  exact {
    selectedProjectedStreamIsNamed := True
    auditedMeasureValuedCompactnessSourcesAreNamed := True
    selectedFamilyObservableSubatomsAreNamed := True
    explicitRawSourceStorageWitnessStillFails := True
  }

/-- Current nearest existing GP216 object to the raw-source naming debt. -/
def gp216_selected_family_observable_subatom_nearest_raw_naming_support_present :
    GP216SelectedFamilyObservableSubatomNearestRawNamingSupport := by
  exact {
    selectedFamilyObservableSourceIsNamed := True
    sameApproximationFamilyAsSelectedProjectedStreamIsNamed := True
    supportStillStartsAfterProjectedStreamFormation := True
  }

/-- Current partial support for the descendant-certification field of the
newer GP216 raw-source storage witness. -/
def gp216_selected_projected_descendant_certification_support_present :
    GP216SelectedProjectedDescendantCertificationSupport := by
  exact {
    selectedFamilyObservableSubatomsAreNamed := True
    compactnessProvenanceUsesTheSameApproximationFamily := True
    downstreamSelectedSourcesLookClosestToCertifiedDescendants := True
    rawSourceStorageStillNeedsSeparateWitness := True
  }

/-- Current closest upstream support for the projected-stream-from-source field
on the GP216 side. -/
def gp216_continuum_all_output_family_source_nearest_projected_generation_support_present :
    GP216ContinuumAllOutputFamilySourceNearestProjectedGenerationSupport := by
  exact {
    streamFamilySourceIsNamed := True
    projectedStreamMatchesBlockByConstruction := True
    projectedSelectedStreamLooksGeneratedFromUpstreamFamilySource := True
    upstreamFamilySourceStillDoesNotNamePreProjectionRawSignedSource := True
  }

/-- Current gap on the bridge from GP216 raw-source storage language to the
actual branch-local raw carrier APIs. -/
def gp216_raw_source_storage_to_actual_observable_carrier_target_gap_present :
    GP216RawSourceStorageToActualObservableCarrierTarget := by
  exact {
    rawSourceStorageWitnessIsNamed := True
    storedRawSourceCarriesBranchLocalSignedObservable := False
    storedRawSourceIsFullyChargedAtPreLedgerStage := False
    storedRawSourceSupportsSelectedBranchRawCarrierAPI := False
  }

/-- Current theorem-shell gap on the same bridge. -/
def gp216_raw_source_storage_to_actual_observable_carrier_theorem_gap_present :
    GP216RawSourceStorageToActualObservableCarrierTheorem := by
  exact {
    target := gp216_raw_source_storage_to_actual_observable_carrier_target_gap_present
    theoremProducesSelectedBranchRawCarrier := False
  }

/-- Current counterproof shell on the same bridge. -/
def gp216_raw_source_storage_does_not_yet_fix_actual_observable_carrier_present :
    GP216RawSourceStorageDoesNotYetFixActualObservableCarrier := by
  exact {
    rawSourceStorageWitnessExistsAbstractly := True
    actualBranchLocalSignedObservableCarrierStillNeedsBridge := True
  }

/-- Current internal GP216 "same source bundle" language support after mining
the bridge-composition receipt. -/
def gp216_internal_same_source_bundle_language_support_present :
    GP216InternalSameSourceBundleLanguageSupport := by
  exact {
    phaseReserveSameSourceEqualityIsNamed := True
    lowBeatOrEventBundleSameSourceLanguageIsNamed := True
    supportLivesInInternalGP216BundleBookkeeping := True
    supportDoesNotNameSelectedBranchCommonRawSource := True
  }

/-- Current counterproof shell for internal GP216 "same source bundle"
language. -/
def gp216_internal_same_source_bundle_language_does_not_imply_common_raw_pullback_present :
    GP216InternalSameSourceBundleLanguageDoesNotImplyCommonRawPullback := by
  exact {
    internalSameSourceBundleLanguageExists := True
    selectedBranchCommonRawPullbackStillFails := True
  }

/-- Current counterproof shell on the cross-corridor provenance side. -/
def alignment_transport_does_not_imply_joint_provenance_present :
    AlignmentTransportDoesNotImplyJointProvenance := by
  exact {
    branchLocalAlignmentAndTransportObjectsExist := True
    sameRawSourceAcrossTheTwoCorridorsStillFails := True
  }

/-- Current exact support on the ordering side inside the Phase 5FB observable
corridor. -/
def phase5fb_observable_corridor_ordering_support_present :
    Phase5FBObservableCorridorOrderingSupport := by
  exact {
    declaredBeforePayoffSupportIsNamed := True
    nonposthocSelectionSupportIsNamed := True
    supportLivesInsideObservableCorridorOnly := True
  }

/-- Current exact source-witness gap on the raw-audit side. -/
def selected_generated_branch_raw_mobius_actual_source_witness_target_present :
    SelectedGeneratedBranchRawMobiusActualSourceWitnessTarget := by
  exact {
    finiteProfileRawMobiusAuditIsNamed := True
    auditUsesActualSelectedBranchRawSource := False
    auditIsNotReadOffFromPostLedgerReplay := False
  }

/-- Current exact theorem-shell gap on the raw-audit source-witness seam. -/
def selected_generated_branch_raw_mobius_actual_source_witness_theorem_gap_present :
    SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem := by
  exact {
    target := selected_generated_branch_raw_mobius_actual_source_witness_target_present
    theoremSuppliesActualSourceWitnessForRawMobiusAudit := False
  }

/-- Current sharper reading of the secondary seam after splitting off
branch-local ordering support. -/
def selected_generated_branch_mobius_support_beyond_ordering_target_present :
    SelectedGeneratedBranchMobiusSupportBeyondOrderingTarget := by
  exact {
    branchLocalOrderingSupportIsNamed := True
    finiteProfileRawMobiusAuditIsNamed := True
    actualSourceBackedMobiusSupportStillNeedsTheorem := True
  }

/-- Current theorem-shell gap for the sharper Möbius-support-beyond-ordering
reading. -/
def selected_generated_branch_mobius_support_beyond_ordering_theorem_gap_present :
    SelectedGeneratedBranchMobiusSupportBeyondOrderingTheorem := by
  exact {
    target := selected_generated_branch_mobius_support_beyond_ordering_target_present
    theoremSuppliesActualSourceBackedMobiusSupportBeyondOrdering := False
  }

/-- Current branch-local source-audit shell on the selected generated branch. -/
def selected_generated_branch_observable_ordering_support_present :
    SelectedGeneratedBranchObservableOrderingSupport := by
  exact {
    selectedGeneratedBranchIsNamed := True
    thresholdRootObservableSourceOnThatBranchIsNamed := True
    sourceStageDeclaredBeforeThresholdAndSurvivalLayers := True
  }

/-- Current kill shell after splitting branch-local ordering support from the
actual finite-profile Möbius-audit support. -/
def observable_ordering_support_does_not_imply_branch_source_audit_present :
    ObservableOrderingSupportDoesNotImplyBranchSourceAudit := by
  exact {
    branchLocalObservableOrderingSupportExists := True
    finiteProfileMobiusAuditSupportStillFails := True
  }

/-- Current branch-local source-audit shell on the selected generated branch. -/
def selected_generated_branch_observable_source_audit_target_present :
    SelectedGeneratedBranchObservableSourceAuditTarget := by
  exact {
    selectedGeneratedBranchIsNamed := True
    thresholdRootObservableSourceOnThatBranchIsNamed := True
    sourceStageDeclaredBeforeThresholdAndSurvivalLayers := True
    sourceStageSupportsFiniteProfileMobiusAudit := False
  }

/-- Current counterproof shell on the raw-audit side. -/
def surrogate_or_post_ledger_mobius_audit_does_not_imply_actual_source_witness_present :
    SurrogateOrPostLedgerMobiusAuditDoesNotImplyActualSourceWitness := by
  exact {
    finiteProfileMobiusAuditShellExists := True
    actualSelectedBranchRawSourceStillIsNotWitnessed := True
    postLedgerOrSurrogateAuditCanMasqueradeAsRawAudit := True
  }

/-- Current conditional counterproof shell after the branch-local source-audit
split. -/
def branch_source_audit_does_not_imply_joint_provenance_present :
    BranchSourceAuditDoesNotImplyJointProvenance := by
  exact {
    branchLocalSourceAuditShellExists := True
    sameRawSourceAcrossTheTwoCorridorsStillFails := True
  }

/-- Promote a paid joint-provenance theorem into the exact same-source
certificate consumed by the strengthened Phase 5FB storage theorem. -/
def same_source_raw_provenance_certificate_of_joint_provenance_theorem
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem) :
    SameSourceRawProvenanceCertificate where
  phase5fbRawSourceIsNamed := hJoint.target.phase5fbObservableCorridorIsNamed
  gp216SelectedBranchRawSourceIsNamed := hJoint.target.gp216SelectedBranchStreamCorridorIsNamed
  bothNamesReferToTheSameRawSignedSource :=
    hJoint.theoremIdentifiesSameRawSourceAcrossTheTwoCorridors

/-- The older joint-provenance target immediately projects to the sharper
same-source-beyond-shared-branch target once the weaker branch-co-location
layer has been split off explicitly. -/
def selected_branch_stream_observable_same_source_beyond_shared_branch_target_of_joint_provenance_target
    (hJoint : SelectedBranchStreamObservableJointProvenanceTarget) :
    SelectedBranchStreamObservableSameSourceBeyondSharedBranchTarget where
  sharedGeneratedBranchSupportIsNamed :=
    hJoint.sharedGeneratedBranchSupportIsAlreadyVisible
  eachCorridorHasInternalProvenanceSupport :=
    hJoint.eachCorridorHasInternalProvenanceSupport
  sameRawSourceBeyondSharedGeneratedBranchStillNeedsTheorem :=
    hJoint.jointSameSourceProvenanceAcrossTheTwoCorridorsStillNeedsTheorem

/-- The older joint-provenance theorem shell likewise projects to the sharper
same-source-beyond-shared-branch theorem shell. -/
def selected_branch_stream_observable_same_source_beyond_shared_branch_theorem_of_joint_provenance_theorem
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem) :
    SelectedBranchStreamObservableSameSourceBeyondSharedBranchTheorem where
  target :=
    selected_branch_stream_observable_same_source_beyond_shared_branch_target_of_joint_provenance_target
      hJoint.target
  theoremIdentifiesSameRawSourceBeyondSharedGeneratedBranchSupport :=
    hJoint.theoremIdentifiesSameRawSourceAcrossTheTwoCorridors

/-- The older branch-local same-source target is the concrete carrier beneath
the newer same-source-beyond-shared-branch shell. Once the weaker branch
co-location layer has been split off, the surviving content is exactly that the
two named sides still need an explicit same-source identity certificate. -/
def selected_generated_branch_same_source_provenance_target_of_same_source_beyond_shared_branch_target
    (hSameSource : SelectedBranchStreamObservableSameSourceBeyondSharedBranchTarget) :
    SelectedGeneratedBranchSameSourceProvenanceTarget where
  gp216SelectedBranchSideIsNamed :=
    hSameSource.eachCorridorHasInternalProvenanceSupport
  phase5fbObservableSideIsNamed :=
    hSameSource.eachCorridorHasInternalProvenanceSupport
  currentBridgeObjectsAreStillAlignmentOrMatchOnly :=
    hSameSource.sharedGeneratedBranchSupportIsNamed
  sameRawSignedSourceStillNeedsExplicitIdentityCertificate :=
    hSameSource.sameRawSourceBeyondSharedGeneratedBranchStillNeedsTheorem

/-- The sharper same-source-beyond-shared-branch theorem shell is therefore
just the newer front-end for the older explicit same-source certificate gap. -/
def same_source_raw_provenance_certificate_of_same_source_beyond_shared_branch_theorem
    (hSameSource : SelectedBranchStreamObservableSameSourceBeyondSharedBranchTheorem) :
    SameSourceRawProvenanceCertificate where
  phase5fbRawSourceIsNamed :=
    hSameSource.target.eachCorridorHasInternalProvenanceSupport
  gp216SelectedBranchRawSourceIsNamed :=
    hSameSource.target.eachCorridorHasInternalProvenanceSupport
  bothNamesReferToTheSameRawSignedSource :=
    hSameSource.theoremIdentifiesSameRawSourceBeyondSharedGeneratedBranchSupport

/-- The latest external kill pass reduces the same-source-beyond-shared-branch
shell to a more honest positive interface: a common raw pullback witness. This
shows the older shell should not be treated as the live constructive theorem. -/
def selected_branch_stream_observable_raw_pullback_witness_of_same_source_storage_theorem
    (hStorage : SelectedBranchStreamObservableSameSourceStorageTheorem) :
    SelectedBranchStreamObservableRawPullbackWitness :=
  hStorage.witness

/-- The full GP216 common raw pullback target immediately projects to the
earlier raw-source naming subfield. -/
def gp216_selected_branch_raw_source_naming_target_of_common_raw_pullback_target
    (hTarget : GP216SelectedBranchCommonRawPullbackTarget) :
    GP216SelectedBranchRawSourceNamingTarget where
  selectedGeneratedBranchIsNamed := hTarget.selectedGeneratedBranchIsNamed
  commonRawSignedSourceIsNamedBeforeProjectedStreamFormation :=
    hTarget.commonRawSignedSourceIsNamedBeforeProjectedStreamFormation

/-- An explicit raw-source storage witness immediately pays the earlier naming
subfield. -/
def gp216_selected_branch_raw_source_naming_target_of_raw_source_storage_witness
    (hWitness : GP216SelectedBranchRawSourceStorageWitness) :
    GP216SelectedBranchRawSourceNamingTarget where
  selectedGeneratedBranchIsNamed := hWitness.selectedGeneratedBranchIsNamed
  commonRawSignedSourceIsNamedBeforeProjectedStreamFormation :=
    hWitness.commonRawSignedSourceIsExplicitlyStored

/-- An explicit GP216 raw-source storage witness upgrades directly to the
common-pullback target. -/
def gp216_selected_branch_common_raw_pullback_target_of_raw_source_storage_witness
    (hWitness : GP216SelectedBranchRawSourceStorageWitness) :
    GP216SelectedBranchCommonRawPullbackTarget where
  selectedGeneratedBranchIsNamed := hWitness.selectedGeneratedBranchIsNamed
  commonRawSignedSourceIsNamedBeforeProjectedStreamFormation :=
    hWitness.commonRawSignedSourceIsExplicitlyStored
  projectedSelectedBranchStreamIsProducedFromThatRawSource :=
    hWitness.projectedSelectedBranchStreamIsGeneratedFromThatRawSource
  auditedOrMeasureValuedSelectedBranchSourceIsProducedFromThatRawSource :=
    hWitness.downstreamSelectedSourcesAreCertifiedDescendantsOfThatRawSource

/-- Once the GP216 side names a common raw source before projected-stream
formation, the observable-side pre-ledger support is enough to build the
corrected raw pullback witness. -/
def selected_branch_stream_observable_raw_pullback_witness_of_gp216_common_raw_pullback_target
    (hGP216 : GP216SelectedBranchCommonRawPullbackTarget)
    (hObs : ObservableSidePreLedgerRawPullbackSupport) :
    SelectedBranchStreamObservableRawPullbackWitness := by
  exact {
    selectedGeneratedBranchIsNamed := hGP216.selectedGeneratedBranchIsNamed
    commonRawSignedSourceIsNamed :=
      hGP216.commonRawSignedSourceIsNamedBeforeProjectedStreamFormation
    streamSidePresentationIsProducedFromThatRawSource :=
      hGP216.projectedSelectedBranchStreamIsProducedFromThatRawSource
    observableSidePresentationIsProducedFromThatRawSourceBeforeLedgering :=
      hObs.observableSidePresentationIsProducedFromThatRawSourceBeforeLedgeringIsClosestToPaid
    branchLocalAlignmentIsInducedByThatRawSource :=
      hObs.branchLocalAlignmentCanAlreadyBeInducedInsideObservableCorridor
  }

/-- The newer GP216 storage-witness interface feeds the corrected cross-
corridor raw pullback witness directly. This is the honest constructive route
after the latest mega pass: the GP216 side stores the raw source explicitly
rather than trying to recover it from downstream projected provenance. -/
def selected_branch_stream_observable_raw_pullback_witness_of_gp216_raw_source_storage_witness
    (hGP216 : GP216SelectedBranchRawSourceStorageWitness)
    (hObs : ObservableSidePreLedgerRawPullbackSupport) :
    SelectedBranchStreamObservableRawPullbackWitness :=
  selected_branch_stream_observable_raw_pullback_witness_of_gp216_common_raw_pullback_target
    (gp216_selected_branch_common_raw_pullback_target_of_raw_source_storage_witness hGP216)
    hObs

/-- Same-source raw provenance becomes honest once the storage theorem is paid:
the common raw source is stored, the observable side is produced before
ledgering, and the branch-local alignment is induced by that shared source. -/
def same_source_raw_provenance_certificate_of_same_source_storage_theorem
    (hStorage : SelectedBranchStreamObservableSameSourceStorageTheorem) :
    SameSourceRawProvenanceCertificate where
  phase5fbRawSourceIsNamed :=
    hStorage.witness.commonRawSignedSourceIsNamed
  gp216SelectedBranchRawSourceIsNamed :=
    hStorage.witness.commonRawSignedSourceIsNamed
  bothNamesReferToTheSameRawSignedSource :=
    hStorage.theoremPaysSameSourceProvenanceHonestly

/-- Honest constructor for the corrected positive provenance target. Once a
common raw pullback witness is explicitly stored, and the pre-ledger ordering
plus raw finite-profile Möbius-audit compatibility are also paid, the selected
branch same-source storage theorem follows directly. -/
def selected_branch_stream_observable_same_source_storage_theorem_of_raw_pullback_and_certificates
    (hWitness : SelectedBranchStreamObservableRawPullbackWitness)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport)
    (hMobius : SelectedGeneratedBranchMobiusSupportBeyondOrderingTheorem) :
    SelectedBranchStreamObservableSameSourceStorageTheorem where
  witness := hWitness
  preLedgerOrderingIsStored :=
    hOrdering.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
  rawFiniteProfileMobiusAuditCompatibilityIsStored :=
    hMobius.theoremSuppliesActualSourceBackedMobiusSupportBeyondOrdering
  theoremPaysSameSourceProvenanceHonestly :=
    hWitness.commonRawSignedSourceIsNamed ∧
    hWitness.streamSidePresentationIsProducedFromThatRawSource ∧
    hWitness.observableSidePresentationIsProducedFromThatRawSourceBeforeLedgering ∧
    hWitness.branchLocalAlignmentIsInducedByThatRawSource

/-- Positive collapse of the corrected provenance route once the exact GP216
stream-side debt is paid. The observable-side pre-ledger support is already
close enough that a GP216 common raw pullback, together with branch-local
ordering and source audit, pays the selected-branch same-source storage
theorem. -/
def selected_branch_stream_observable_same_source_storage_theorem_of_gp216_common_raw_pullback_target_and_branch_source_audit
    (hGP216 : GP216SelectedBranchCommonRawPullbackTarget)
    (hObs : ObservableSidePreLedgerRawPullbackSupport)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport)
    (hAudit : SelectedGeneratedBranchObservableSourceAuditTarget) :
    SelectedBranchStreamObservableSameSourceStorageTheorem := by
  let hWitness :=
    selected_branch_stream_observable_raw_pullback_witness_of_gp216_common_raw_pullback_target
      hGP216 hObs
  let hMobius : SelectedGeneratedBranchMobiusSupportBeyondOrderingTheorem := {
    target := {
      branchLocalOrderingSupportIsNamed :=
        hOrdering.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
      finiteProfileRawMobiusAuditIsNamed :=
        hAudit.sourceStageSupportsFiniteProfileMobiusAudit
      actualSourceBackedMobiusSupportStillNeedsTheorem := False
    }
    theoremSuppliesActualSourceBackedMobiusSupportBeyondOrdering :=
      hAudit.sourceStageSupportsFiniteProfileMobiusAudit
  }
  exact
    selected_branch_stream_observable_same_source_storage_theorem_of_raw_pullback_and_certificates
      hWitness hOrdering hMobius

/-- The newer GP216-side storage-witness interface feeds the corrected
selected-branch same-source storage theorem directly. This is the honest
positive lane after the latest mega pass: GP216 stores the raw source
explicitly, the observable corridor stays pre-ledger, and the branch-local
audit shell is paid locally. -/
def selected_branch_stream_observable_same_source_storage_theorem_of_gp216_raw_source_storage_witness_and_branch_source_audit
    (hGP216 : GP216SelectedBranchRawSourceStorageWitness)
    (hObs : ObservableSidePreLedgerRawPullbackSupport)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport)
    (hAudit : SelectedGeneratedBranchObservableSourceAuditTarget) :
    SelectedBranchStreamObservableSameSourceStorageTheorem :=
  selected_branch_stream_observable_same_source_storage_theorem_of_gp216_common_raw_pullback_target_and_branch_source_audit
    (gp216_selected_branch_common_raw_pullback_target_of_raw_source_storage_witness hGP216)
    hObs
    hOrdering
    hAudit

/-- Honest positive reduction on the new GP216-to-raw-carrier bridge. Once the
bridge theorem is paid, the stream-side storage witness is no longer blocked on
identifying the actual branch-local signed observable carrier. -/
def pressure_first_refined_selected_branch_target_of_gp216_raw_source_storage_to_actual_observable_carrier_theorem
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hBridge : GP216RawSourceStorageToActualObservableCarrierTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hBridge.theoremProducesSelectedBranchRawCarrier
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hBridge.theoremProducesSelectedBranchRawCarrier
  }

/-- Negative collapse of the corrected provenance route under the stronger
GP216-side kill. Even if the observable-side ordering and branch-local source
audit are paid, output-derived GP216 provenance still leaves the same-source
storage theorem blocked. -/
def selected_branch_stream_observable_same_source_storage_theorem_gap_of_gp216_output_derived_provenance_kill
    (_hKill : GP216OutputDerivedSourceProvenanceDoesNotImplyCommonRawPullback)
    (hObs : ObservableSidePreLedgerRawPullbackSupport)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport)
    (hAudit : SelectedGeneratedBranchObservableSourceAuditTarget) :
    SelectedBranchStreamObservableSameSourceStorageTheorem := by
  exact {
    witness := {
      selectedGeneratedBranchIsNamed := hAudit.selectedGeneratedBranchIsNamed
      commonRawSignedSourceIsNamed := False
      streamSidePresentationIsProducedFromThatRawSource := False
      observableSidePresentationIsProducedFromThatRawSourceBeforeLedgering :=
        hObs.observableSidePresentationIsProducedFromThatRawSourceBeforeLedgeringIsClosestToPaid
      branchLocalAlignmentIsInducedByThatRawSource :=
        hObs.branchLocalAlignmentCanAlreadyBeInducedInsideObservableCorridor
    }
    preLedgerOrderingIsStored :=
      hOrdering.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
    rawFiniteProfileMobiusAuditCompatibilityIsStored :=
      hAudit.sourceStageSupportsFiniteProfileMobiusAudit
    theoremPaysSameSourceProvenanceHonestly := False
  }

/-- Internal ordering support on the Phase 5FB side promotes to the exact
pre-ledger ordering certificate once we stay inside the observable corridor.
This is weaker than joint provenance because it does not cross to the GP216
selected-branch stream corridor. -/
def pre_ledger_ordering_certificate_of_phase5fb_observable_corridor_support
    (hSupport : Phase5FBObservableCorridorOrderingSupport) :
    PreLedgerOrderingCertificate where
  rawSignedSourceExistsBeforeReplayLedgerMap :=
    hSupport.declaredBeforePayoffSupportIsNamed
  rawFiniteProfileStreamIsFormedBeforeThresholding :=
    hSupport.declaredBeforePayoffSupportIsNamed
  rawFiniteProfileStreamIsFormedBeforeSurvivalAndNoSurvivor :=
    hSupport.nonposthocSelectionSupportIsNamed

/-- Once the actual-source witness for the raw Mobius audit is paid, the
stronger raw-audit compatibility certificate reduces to an ordering check
instead of a provenance mystery. -/
def raw_finite_profile_mobius_audit_compatibility_of_actual_source_witness
    (hWitness : SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem) :
    RawFiniteProfileMobiusAuditCompatibility where
  rawFiniteProfileAuditIsNamed := hWitness.target.finiteProfileRawMobiusAuditIsNamed
  rawAuditIsPerformedBeforeReplayLedgerMap :=
    hWitness.theoremSuppliesActualSourceWitnessForRawMobiusAudit
  postLedgerAuditIsNotUsedAsASubstitute :=
    hWitness.target.auditIsNotReadOffFromPostLedgerReplay

/-- If the branch-local source-audit shell is paid, then the raw Mobius
actual-source witness is mechanical rather than a separate frontier seam. -/
def selected_generated_branch_raw_mobius_actual_source_witness_of_branch_source_audit
    (hAudit : SelectedGeneratedBranchObservableSourceAuditTarget) :
    SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem where
  target := {
    finiteProfileRawMobiusAuditIsNamed := hAudit.sourceStageSupportsFiniteProfileMobiusAudit
    auditUsesActualSelectedBranchRawSource :=
      hAudit.thresholdRootObservableSourceOnThatBranchIsNamed
    auditIsNotReadOffFromPostLedgerReplay :=
      hAudit.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
  }
  theoremSuppliesActualSourceWitnessForRawMobiusAudit :=
    hAudit.sourceStageSupportsFiniteProfileMobiusAudit

/-- Once branch-local ordering support and the actual-source raw Möbius witness
are both paid, the fuller branch-local source-audit shell is immediate. This
prevents the frontier from re-bundling already-paid ordering support with the
surviving actual-source audit debt. -/
def selected_generated_branch_observable_source_audit_target_of_observable_ordering_support_and_raw_mobius_actual_source_witness
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport)
    (hWitness : SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem) :
    SelectedGeneratedBranchObservableSourceAuditTarget where
  selectedGeneratedBranchIsNamed :=
    hOrdering.selectedGeneratedBranchIsNamed
  thresholdRootObservableSourceOnThatBranchIsNamed :=
    hOrdering.thresholdRootObservableSourceOnThatBranchIsNamed
  sourceStageDeclaredBeforeThresholdAndSurvivalLayers :=
    hOrdering.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
  sourceStageSupportsFiniteProfileMobiusAudit :=
    hWitness.theoremSuppliesActualSourceWitnessForRawMobiusAudit

/-- The older raw-witness target projects immediately to the sharper
Möbius-support-beyond-ordering target once the weaker ordering layer has been
split off. -/
def selected_generated_branch_mobius_support_beyond_ordering_target_of_raw_mobius_actual_source_witness_target
    (hTarget : SelectedGeneratedBranchRawMobiusActualSourceWitnessTarget)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport) :
    SelectedGeneratedBranchMobiusSupportBeyondOrderingTarget where
  branchLocalOrderingSupportIsNamed :=
    hOrdering.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
  finiteProfileRawMobiusAuditIsNamed :=
    hTarget.finiteProfileRawMobiusAuditIsNamed
  actualSourceBackedMobiusSupportStillNeedsTheorem :=
    ¬ hTarget.auditUsesActualSelectedBranchRawSource ∨
      ¬ hTarget.auditIsNotReadOffFromPostLedgerReplay

/-- The older raw-witness theorem shell likewise projects to the sharper
Möbius-support-beyond-ordering theorem shell. -/
def selected_generated_branch_mobius_support_beyond_ordering_theorem_of_raw_mobius_actual_source_witness
    (hWitness : SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport) :
    SelectedGeneratedBranchMobiusSupportBeyondOrderingTheorem where
  target :=
    selected_generated_branch_mobius_support_beyond_ordering_target_of_raw_mobius_actual_source_witness_target
      hWitness.target hOrdering
  theoremSuppliesActualSourceBackedMobiusSupportBeyondOrdering :=
    hWitness.theoremSuppliesActualSourceWitnessForRawMobiusAudit

/-- The older all-global-block source-audit surface projects to the sharper
selected-generated-branch source-audit shell once a branch is fixed. This keeps
the local frontier attached to an existing source-facing object rather than
inventing a parallel audit hierarchy. -/
def selected_generated_branch_observable_source_audit_target_of_observable_source_audit
    {τ : ContinuumLPProfileTopology.{u}}
    (hAudit : PressureFirstObservableSourceAuditTarget τ)
    (B : FullLedgerBlock)
    (_hglobal : IsGlobalTrackBBlock B) :
    SelectedGeneratedBranchObservableSourceAuditTarget where
  selectedGeneratedBranchIsNamed := True
  thresholdRootObservableSourceOnThatBranchIsNamed := True
  sourceStageDeclaredBeforeThresholdAndSurvivalLayers :=
    hAudit.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
  sourceStageSupportsFiniteProfileMobiusAudit :=
    hAudit.sourceStageSupportsFiniteProfileMobiusAudit

/-- Current exact raw finite-profile audit gap on the Phase 5FB side. -/
def raw_finite_profile_mobius_audit_compatibility_gap_present :
    RawFiniteProfileMobiusAuditCompatibility := by
  exact {
    rawFiniteProfileAuditIsNamed := False
    rawAuditIsPerformedBeforeReplayLedgerMap := False
    postLedgerAuditIsNotUsedAsASubstitute := False
  }

/-- Current exact strengthened storage-theorem gap on the Phase 5FB side. -/
def phase5fb_raw_stage_storage_theorem_gap_present :
    Phase5FBRawStageStorageTheorem := by
  exact {
    replayLedgerMap := phase5fb_replay_ledger_map_present
    preLedgerOrdering := pre_ledger_ordering_certificate_gap_present
    sameSourceProvenance := same_source_raw_provenance_certificate_gap_present
    rawMobiusAuditCompatibility :=
      raw_finite_profile_mobius_audit_compatibility_gap_present
    theoremExposesLocalRawCarrier := False
  }

/-- Current exact kill-side obstruction after the external Phase 5FB attack. -/
def phase5fb_replay_does_not_determine_raw_signed_source_present :
    Phase5FBReplayDoesNotDetermineRawSignedSource := by
  exact {
    replayLedgerMapIsNonInjective := True
    replayDataAloneDoesNotFixSameRawSignedSource := True
    replayToRawUpgradeNeedsExplicitStorageWitnesses := True
  }

/-- Cheap finite obstruction instantiated at the positive-part / threshold
layer. -/
def positive_part_ledger_noninjective_present :
    PositivePartLedgerNoninjective := by
  exact {
    positivePartOrThresholdMapIsNamed := True
    distinctRawSignedInputsCanShareOneLedgeredReplayImage := True
  }

/-- Current exact anti-laundering verdict on the Phase 5FB side. -/
def phase5fb_replay_model_too_weak_as_raw_carrier_present :
    Phase5FBReplayModelTooWeakAsRawCarrier := by
  exact {
    generatedObservableReplayModelExists := True
    replayModelByItselfIsNotYetLocalRawCarrier := True
    rawCarrierNeedsExtraPreLedgerAndMobiusTheorem := True
  }

/-- Current exact assembly gap after the scout pass. -/
def selected_generated_branch_clean_source_assembly_target_present :
    SelectedGeneratedBranchCleanSourceAssemblyTarget := by
  exact {
    bothExactTransportTargetsArePaid := False
    localCleanSourceBundleStillNeedsExactAssembly := True
  }

/-- Current theorem-shell gap on the GP216 side. The target is known, but the
local carrier has not yet been produced from the upstream model. -/
def gp216_selected_branch_projected_stream_transport_theorem_gap_present :
    GP216SelectedBranchProjectedStreamTransportTheorem := by
  exact {
    transportTarget := gp216_selected_branch_projected_stream_transport_target_present
    localCarrier := {
      projectedSelectedBranchStream := zeroLeraySelfTaxProfilePriceStream
      auditedSelectedBranchSelfTaxStream := zeroLeraySelfTaxProfilePriceStream
      streamsAgree := rfl
    }
    transportUsesSelectedBranchProjectedStreamModel := False
  }

/-- Current theorem-shell gap on the Phase 5FB side. The target is known, but
the local raw-signed-source carrier has not yet been produced from the
upstream model. -/
def phase5fb_raw_observable_transport_theorem_gap_present :
    Phase5FBRawObservableTransportTheorem := by
  exact {
    transportTarget := phase5fb_raw_observable_transport_target_present
    localCarrier := {
      observable := {
        kind := ObservableKind.scalar
        predeclared := True
        independentNormalized := True
        psdBallastCharged := True
        dampingCharged := True
        crossTermCharged := True
      }
      observableFullyCharged := by
        refine ⟨by decide, True.intro, True.intro, True.intro, True.intro, ?_⟩
        intro _
        exact True.intro
      rawStageStoredBeforeThresholdLedgering := False
      rawStageStoredBeforeNoSurvivorLedgering := False
      rawStageStoredBeforePositiveCoherenceAggregation := False
      supportsFiniteProfileMobiusAudit := False
    }
    transportPreservesPreLedgerOrderingAndMobiusAudit := False
  }

/-- Current theorem-shell gap at the final assembly layer. Both local carriers
are still placeholder outputs rather than transported upstream models. -/
def selected_generated_branch_clean_source_assembly_theorem_gap_present :
    SelectedGeneratedBranchCleanSourceAssemblyTheorem := by
  exact {
    assemblyTarget := selected_generated_branch_clean_source_assembly_target_present
    localBundle := {
      streamEquality :=
        gp216_selected_branch_projected_stream_transport_theorem_gap_present.localCarrier
      rawSignedSourceStorage :=
        phase5fb_raw_observable_transport_theorem_gap_present.localCarrier
    }
    assemblyUsesBothTransportTheorems := False
  }

/-- Current anti-laundering verdict on the exact transport seam. -/
def selected_generated_branch_transport_anti_laundering_risk_present :
    SelectedGeneratedBranchTransportAntiLaunderingRisk := by
  exact {
    dependencyCycleRisk := True
    surrogateStreamSwapRisk := True
    postLedgerRawStageSubstitutionRisk := True
  }

/-- Current exactness audit after the meta-DARWIN pass. -/
def selected_generated_branch_queue_exactness_audit_present :
    SelectedGeneratedBranchQueueExactnessAudit := by
  exact {
    gp216SideAlreadyExactUpstreamModel := True
    phase5fbSideStillOneAbstractionTooLate := True
    earliestFakeStepIsCallingReplayModelARawCarrier := True
  }

/-- A concrete selected-branch stream-equality carrier pays the corresponding
branch-local witness directly. -/
theorem selected_generated_branch_projected_stream_equality_witness_of_carrier
    (hCarrier : SelectedGeneratedBranchProjectedStreamEqualityCarrier) :
    Nonempty SelectedGeneratedBranchProjectedStreamEqualityWitness := by
  exact ⟨{
    generatedSelectedBranchIsNamed := True
    projectedContinuumSelectedBranchStreamIsNamed := True
    auditedSelfTaxStreamOnSelectedBranchIsNamed := True
    projectedSelectedBranchStreamEqualsAuditedSelfTaxStream :=
      hCarrier.projectedSelectedBranchStream =
        hCarrier.auditedSelectedBranchSelfTaxStream
  }⟩

/-- A concrete selected-branch raw signed-source carrier pays the corresponding
branch-local storage witness directly. -/
theorem selected_generated_branch_raw_signed_source_storage_witness_of_carrier
    (hCarrier : SelectedGeneratedBranchRawSignedSourceCarrier) :
    Nonempty SelectedGeneratedBranchRawSignedSourceStorageWitness := by
  exact ⟨{
    selectedGeneratedBranchThresholdRootSourceIsNamed := True
    branchLocalRawSignedSourceIsNamed := True
    rawSignedSourceIsStoredBeforeThresholdLedgering :=
      hCarrier.rawStageStoredBeforeThresholdLedgering
    rawSignedSourceSupportsFiniteProfileMobiusAudit :=
      hCarrier.supportsFiniteProfileMobiusAudit
  }⟩

/-- Import-free local transport from the mirrored GP216 payload into the exact
local selected-branch stream-equality carrier. -/
def selected_generated_branch_projected_stream_carrier_of_gp216_model_witness
    (hModel : GP216SelectedBranchProjectedStreamModelWitness) :
    SelectedGeneratedBranchProjectedStreamEqualityCarrier where
  projectedSelectedBranchStream := hModel.projectedSelectedBranchStream
  auditedSelectedBranchSelfTaxStream := hModel.auditedSelectedBranchSelfTaxStream
  streamsAgree := hModel.selectedBranchProjectedStreamMatchesAuditedSelfTax

/-- Import-free local transport theorem on the GP216 side. Once the mirrored
selected-branch stream-match payload is exposed locally, the local transport
shell is mechanically paid. -/
def gp216_selected_branch_projected_stream_transport_theorem_of_model_witness
    (hModel : GP216SelectedBranchProjectedStreamModelWitness) :
    GP216SelectedBranchProjectedStreamTransportTheorem where
  transportTarget := gp216_selected_branch_projected_stream_transport_target_present
  localCarrier := selected_generated_branch_projected_stream_carrier_of_gp216_model_witness hModel
  transportUsesSelectedBranchProjectedStreamModel := True

/-- Import-free local replay-side transport from the mirrored Phase 5FB payload.
This still stops short of the raw carrier because the extra raw-stage theorem
remains unpaid. -/
def phase5fb_generated_observable_replay_transport_theorem_of_model_witness
    (hModel : Phase5FBGeneratedObservableReplayModelWitness) :
    Phase5FBGeneratedObservableReplayTransportTheorem where
  transportTarget := phase5fb_generated_observable_replay_transport_target_present
  transportProducesNamedObservableAndCharge := hModel.replayModelDeclaredOnGeneratedBranch

/-- Construct the exact local raw-signed-source carrier once the replay model,
raw-storage theorem, and Mobius-audit theorem are all present. This makes the
substantive Phase 5FB split constructive rather than merely declarative. -/
def selected_generated_branch_raw_signed_source_carrier_of_phase5fb_replay_and_split_theorems
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBThresholdRootRawStorageTheorem)
    (hAudit : Phase5FBRawMobiusAuditCommutationTheorem) :
    SelectedGeneratedBranchRawSignedSourceCarrier where
  observable := hModel.observable
  observableFullyCharged := hModel.observableFullyCharged
  rawStageStoredBeforeThresholdLedgering :=
    hStorage.theoremExposesRawObservableBeforeLedgerLayers
  rawStageStoredBeforeNoSurvivorLedgering :=
    hStorage.theoremExposesRawObservableBeforeLedgerLayers
  rawStageStoredBeforePositiveCoherenceAggregation :=
    hStorage.theoremExposesRawObservableBeforeLedgerLayers
  supportsFiniteProfileMobiusAudit :=
    hAudit.theoremShowsRawMobiusAuditCommutesBeforeLedgerLayers

/-- Construct the exact local raw-signed-source carrier directly from the
stronger external storage theorem. This is the corrected positive branch after
the replay/raw mismatch attack. -/
def selected_generated_branch_raw_signed_source_carrier_of_phase5fb_replay_model_and_storage_theorem
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem) :
    SelectedGeneratedBranchRawSignedSourceCarrier where
  observable := hModel.observable
  observableFullyCharged := hModel.observableFullyCharged
  rawStageStoredBeforeThresholdLedgering :=
    hStorage.preLedgerOrdering.rawFiniteProfileStreamIsFormedBeforeThresholding
  rawStageStoredBeforeNoSurvivorLedgering :=
    hStorage.preLedgerOrdering.rawFiniteProfileStreamIsFormedBeforeSurvivalAndNoSurvivor
  rawStageStoredBeforePositiveCoherenceAggregation :=
    hStorage.preLedgerOrdering.rawSignedSourceExistsBeforeReplayLedgerMap
  supportsFiniteProfileMobiusAudit :=
    hStorage.rawMobiusAuditCompatibility.rawAuditIsPerformedBeforeReplayLedgerMap

/-- Reconstitute the older bundled shell from the sharper storage/audit split.
This keeps downstream code stable while preserving the exact local fork. -/
def phase5fb_raw_stage_theorem_of_storage_and_audit_theorems
    (hStorage : Phase5FBThresholdRootRawStorageTheorem)
    (hAudit : Phase5FBRawMobiusAuditCommutationTheorem) :
    Phase5FBRawStageTheorem where
  theoremTarget := phase5fb_raw_stage_theorem_target_present
  theoremProducesLocalRawCarrier :=
    hStorage.theoremExposesRawObservableBeforeLedgerLayers
  theoremPaysPreLedgerOrderingAndMobiusAudit :=
    hStorage.theoremExposesRawObservableBeforeLedgerLayers ∧
    hAudit.theoremShowsRawMobiusAuditCommutesBeforeLedgerLayers

/-- The strengthened external verdict feeds the older bundled shell directly:
if the explicit storage theorem is paid, the bundled raw-stage theorem follows.
-/
def phase5fb_replay_to_raw_stage_requires_storage
    (hStorage : Phase5FBRawStageStorageTheorem) :
    Phase5FBRawStageTheorem where
  theoremTarget := phase5fb_raw_stage_theorem_target_present
  theoremProducesLocalRawCarrier := hStorage.theoremExposesLocalRawCarrier
  theoremPaysPreLedgerOrderingAndMobiusAudit :=
    hStorage.preLedgerOrdering.rawSignedSourceExistsBeforeReplayLedgerMap ∧
    hStorage.rawMobiusAuditCompatibility.rawAuditIsPerformedBeforeReplayLedgerMap

/-- Construct the strengthened storage theorem once the cross-corridor
same-source theorem and the two remaining raw-stage certificates are paid. This
shows explicitly that the joint-provenance theorem is now upstream of the older
Phase 5FB storage package. -/
def phase5fb_raw_stage_storage_theorem_of_joint_provenance_and_raw_audit
    (hLedgerMap : Phase5FBReplayLedgerMap)
    (hOrdering : PreLedgerOrderingCertificate)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hAudit : RawFiniteProfileMobiusAuditCompatibility) :
    Phase5FBRawStageStorageTheorem where
  replayLedgerMap := hLedgerMap
  preLedgerOrdering := hOrdering
  sameSourceProvenance :=
    same_source_raw_provenance_certificate_of_joint_provenance_theorem hJoint
  rawMobiusAuditCompatibility := hAudit
  theoremExposesLocalRawCarrier :=
    hOrdering.rawSignedSourceExistsBeforeReplayLedgerMap ∧
    hJoint.theoremIdentifiesSameRawSourceAcrossTheTwoCorridors ∧
    hAudit.rawAuditIsPerformedBeforeReplayLedgerMap

/-- Sharper reconstruction of the strengthened storage theorem from the two
new frontier shells: cross-corridor joint provenance and actual-source-backed
raw Mobius audit, together with the internal Phase 5FB ordering support. -/
def phase5fb_raw_stage_storage_theorem_of_joint_provenance_and_actual_source_mobius_witness
    (hLedgerMap : Phase5FBReplayLedgerMap)
    (hOrderingSupport : Phase5FBObservableCorridorOrderingSupport)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hWitness : SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem) :
    Phase5FBRawStageStorageTheorem :=
  phase5fb_raw_stage_storage_theorem_of_joint_provenance_and_raw_audit
    hLedgerMap
    (pre_ledger_ordering_certificate_of_phase5fb_observable_corridor_support
      hOrderingSupport)
    hJoint
    (raw_finite_profile_mobius_audit_compatibility_of_actual_source_witness
      hWitness)

/-- If the existing source-audit target is already paid on a selected generated
branch, then the stronger Phase 5FB storage theorem reduces to joint
provenance plus that audit surface. -/
def phase5fb_raw_stage_storage_theorem_of_joint_provenance_and_observable_source_audit
    {τ : ContinuumLPProfileTopology.{u}}
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hAudit : PressureFirstObservableSourceAuditTarget τ)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    Phase5FBRawStageStorageTheorem :=
  let hLocalAudit :=
    selected_generated_branch_observable_source_audit_target_of_observable_source_audit
      hAudit B hglobal
  let hWitness :=
    selected_generated_branch_raw_mobius_actual_source_witness_of_branch_source_audit
      hLocalAudit
  phase5fb_raw_stage_storage_theorem_of_joint_provenance_and_actual_source_mobius_witness
    phase5fb_replay_ledger_map_present
    phase5fb_observable_corridor_ordering_support_present
    hJoint
    hWitness

/-- Construct the older local transport shell on the Phase 5FB side from the
replay model together with the sharper storage/audit theorem pair. -/
def phase5fb_raw_observable_transport_theorem_of_replay_model_and_split_theorems
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBThresholdRootRawStorageTheorem)
    (hAudit : Phase5FBRawMobiusAuditCommutationTheorem) :
    Phase5FBRawObservableTransportTheorem where
  transportTarget := phase5fb_raw_observable_transport_target_present
  localCarrier :=
    selected_generated_branch_raw_signed_source_carrier_of_phase5fb_replay_and_split_theorems
      hModel hStorage hAudit
  transportPreservesPreLedgerOrderingAndMobiusAudit :=
    hStorage.theoremExposesRawObservableBeforeLedgerLayers ∧
    hAudit.theoremShowsRawMobiusAuditCommutesBeforeLedgerLayers

/-- Corrected local transport theorem on the Phase 5FB side after the external
attack: replay plus the stronger storage theorem is enough to produce the local
raw carrier. -/
def phase5fb_raw_observable_transport_theorem_of_replay_model_and_storage_theorem
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem) :
    Phase5FBRawObservableTransportTheorem where
  transportTarget := phase5fb_raw_observable_transport_target_present
  localCarrier :=
    selected_generated_branch_raw_signed_source_carrier_of_phase5fb_replay_model_and_storage_theorem
      hModel hStorage
  transportPreservesPreLedgerOrderingAndMobiusAudit :=
    hStorage.preLedgerOrdering.rawSignedSourceExistsBeforeReplayLedgerMap ∧
    hStorage.rawMobiusAuditCompatibility.rawAuditIsPerformedBeforeReplayLedgerMap

/-- After the corrected GP216 and Phase 5FB transport shells are both paid,
the clean-source bundle is assembled mechanically. This demotes assembly below
the storage/provenance/audit seam. -/
def selected_generated_branch_clean_source_bundle_of_gp216_transport_and_phase5fb_storage
    (hGP216 : GP216SelectedBranchProjectedStreamTransportTheorem)
    (hPhase5FB : Phase5FBRawObservableTransportTheorem) :
    SelectedGeneratedBranchCleanSourceBundle where
  streamEquality := hGP216.localCarrier
  rawSignedSourceStorage := hPhase5FB.localCarrier

/-- The branch-local raw signed-source carrier refines the older raw-source
carrier used by the actual-observable bridge path. -/
def actual_observable_raw_signed_source_of_selected_branch_raw_signed_source_carrier
    (hCarrier : SelectedGeneratedBranchRawSignedSourceCarrier) :
    ActualObservableRawSignedSource where
  observable := hCarrier.observable
  observableFullyChargedAtRawStage := hCarrier.observableFullyCharged
  rawStagePrecedesThresholdCoordinateLayer :=
    hCarrier.rawStageStoredBeforeThresholdLedgering
  rawStagePrecedesQuarticSurvivalProjection :=
    hCarrier.rawStageStoredBeforeThresholdLedgering
  rawStagePrecedesNoSurvivorProjection :=
    hCarrier.rawStageStoredBeforeNoSurvivorLedgering
  rawStagePrecedesPositiveCoherenceAggregation :=
    hCarrier.rawStageStoredBeforePositiveCoherenceAggregation

/-- The branch-local raw signed-source carrier also pays the sharper storage
target exposed by the selected-generated-branch reduction. -/
theorem selected_generated_branch_raw_stage_storage_target_of_carrier
    (hCarrier : SelectedGeneratedBranchRawSignedSourceCarrier) :
    Nonempty SelectedGeneratedBranchRawStageStorageTarget := by
  exact ⟨{
    selectedGeneratedBranchAlreadyCarriesThresholdRootObservable := True
    rawSignedSourceMustBeStoredBeforeThresholdLedgering :=
      hCarrier.rawStageStoredBeforeThresholdLedgering
    branchLocalRawStageStillNeedsActualObservableWitness := False
  }⟩

/-- The selected-branch clean bundle pays the sharper branch-local witness
objects directly. -/
theorem selected_generated_branch_witnesses_of_clean_source_bundle
    (hBundle : SelectedGeneratedBranchCleanSourceBundle) :
    Nonempty
      (SelectedGeneratedBranchProjectedStreamEqualityWitness ×
        SelectedGeneratedBranchRawSignedSourceStorageWitness) := by
  let hEq :
      SelectedGeneratedBranchProjectedStreamEqualityWitness :=
    Classical.choice
      (selected_generated_branch_projected_stream_equality_witness_of_carrier
        hBundle.streamEquality)
  let hRaw :
      SelectedGeneratedBranchRawSignedSourceStorageWitness :=
    Classical.choice
      (selected_generated_branch_raw_signed_source_storage_witness_of_carrier
        hBundle.rawSignedSourceStorage)
  exact ⟨(hEq, hRaw)⟩

/-- The selected-branch raw signed-source carrier feeds the older actual
observable bridge prerequisites once the branch-local source seam is paid. -/
theorem actual_observable_bridge_prerequisites_of_selected_branch_raw_signed_source_carrier
    (hCarrier : SelectedGeneratedBranchRawSignedSourceCarrier)
    (hMatchesFiniteProfilePriceFunctional : Prop)
    (hDeclaredBeforeEnvelopeFitting : Prop) :
    Nonempty ActualObservableBridgePrerequisites := by
  let hExtraction : ActualObservableRawStageExtraction :=
    {
      rawSignedObservableStageIsNamed := True
      rawStagePrecedesThresholdCoordinateLayer :=
        hCarrier.rawStageStoredBeforeThresholdLedgering
      rawStagePrecedesQuarticSurvivalProjection :=
        hCarrier.rawStageStoredBeforeThresholdLedgering
      rawStagePrecedesNoSurvivorProjection :=
        hCarrier.rawStageStoredBeforeNoSurvivorLedgering
      rawStagePrecedesPositiveCoherenceAggregation :=
        hCarrier.rawStageStoredBeforePositiveCoherenceAggregation
    }
  exact ⟨{
    rawStageExtraction := hExtraction
    rawStageMatchesFiniteProfilePriceFunctional :=
      hMatchesFiniteProfilePriceFunctional
    rawStageSupportsFiniteProfileMobiusAudit :=
      hCarrier.supportsFiniteProfileMobiusAudit
    rawStageRestrictionIsDeclaredBeforeEnvelopeFitting :=
      hDeclaredBeforeEnvelopeFitting
  }⟩

/-- Once the exact branch-local clean-source bundle is present, the refined
selected-branch target can be discharged without any remaining witness-gap
placeholders. -/
theorem pressure_first_refined_selected_branch_target_of_clean_source_bundle
    (hBundle : SelectedGeneratedBranchCleanSourceBundle) :
    Nonempty PressureFirstRefinedSelectedBranchTarget := by
  exact ⟨{
    selectedBranchProjectedStreamEqualityIsFirst :=
      hBundle.streamEquality.projectedSelectedBranchStream =
        hBundle.streamEquality.auditedSelectedBranchSelfTaxStream
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed := True
    pressureTailStillWaitsForActualObservableSourceMatch := True
    branchLocalRawStageStorageIsAlsoRequired :=
      hBundle.rawSignedSourceStorage.rawStageStoredBeforeThresholdLedgering ∧
      hBundle.rawSignedSourceStorage.supportsFiniteProfileMobiusAudit
    exactBranchLocalWitnessesStillNeedToBeBuilt := False
  }⟩

/-- Mechanical final assembly after the corrected GP216 and Phase 5FB transport
theorems are both present. -/
def selected_generated_branch_clean_source_assembly_theorem_of_gp216_transport_and_phase5fb_storage
    (hGP216 : GP216SelectedBranchProjectedStreamTransportTheorem)
    (hPhase5FB : Phase5FBRawObservableTransportTheorem) :
    SelectedGeneratedBranchCleanSourceAssemblyTheorem where
  assemblyTarget := {
    bothExactTransportTargetsArePaid := True
    localCleanSourceBundleStillNeedsExactAssembly := False
  }
  localBundle :=
    selected_generated_branch_clean_source_bundle_of_gp216_transport_and_phase5fb_storage
      hGP216 hPhase5FB
  assemblyUsesBothTransportTheorems := True

/-- After the scout pass, the exact local clean-side source theorem queue is
best stated as an import-free transport/assembly problem from already-existing
upstream models into the local clean bundle. -/
def pressure_first_refined_selected_branch_target_of_upstream_transport_gap
    (hModels : SelectedGeneratedBranchUpstreamSourceModels)
    (hGap : SelectedGeneratedBranchUpstreamTransportGap) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hGap.streamEqualityCarrierStillNeedsImportFreeTransport
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hModels.bothModelsLiveOnGeneratedBranchSide
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hModels.gp216SelectedBranchProjectedStreamModelExists
    branchLocalRawStageStorageIsAlsoRequired :=
      hGap.rawSignedSourceCarrierStillNeedsImportFreeTransport ∨
      hModels.phase5fbRawObservableCarrierStillNeedsSubstantiveRawStageTheorem
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hGap.localCleanBundleStillNeedsExactAssembly
  }

/-- Sharper queue reduction after the scout pass: the live clean-side seam is
best understood as two exact upstream transport theorems plus one local
assembly theorem. -/
def pressure_first_refined_selected_branch_target_of_exact_transport_targets
    (hGP216 : GP216SelectedBranchProjectedStreamTransportTarget)
    (hPhase5FB : Phase5FBRawObservableTransportTarget)
    (hAssemble : SelectedGeneratedBranchCleanSourceAssemblyTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hGP216.localProjectedStreamEqualityCarrierStillNeedsTransport
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hGP216.upstreamSelectedBranchProjectedStreamModelIsNamed ∧
      hPhase5FB.upstreamPhase5fbRawObservableModelIsNamed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hAssemble.localCleanSourceBundleStillNeedsExactAssembly
    branchLocalRawStageStorageIsAlsoRequired :=
      hPhase5FB.localRawSignedSourceCarrierStillNeedsTransport
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hAssemble.localCleanSourceBundleStillNeedsExactAssembly
  }

/-- Final queue reduction for the current clean-side source seam: the next
honest theorem work is exactly three theorem shells, not a broad compatibility
story. -/
def pressure_first_refined_selected_branch_target_of_transport_theorem_gaps
    (hGP216 : GP216SelectedBranchProjectedStreamTransportTheorem)
    (hPhase5FB : Phase5FBRawObservableTransportTheorem)
    (hAssemble : SelectedGeneratedBranchCleanSourceAssemblyTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      ¬ hGP216.transportUsesSelectedBranchProjectedStreamModel
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      True
    pressureTailStillWaitsForActualObservableSourceMatch :=
      ¬ hAssemble.assemblyUsesBothTransportTheorems
    branchLocalRawStageStorageIsAlsoRequired :=
      ¬ hPhase5FB.transportPreservesPreLedgerOrderingAndMobiusAudit
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      ¬ hAssemble.assemblyUsesBothTransportTheorems
  }

/-- Anti-laundering refinement of the same queue: even if the transport queue
is named exactly, it remains blocked until the three transport-side cheating
risks are discharged. -/
def pressure_first_refined_selected_branch_target_of_transport_anti_laundering_risk
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hRisk : SelectedGeneratedBranchTransportAntiLaunderingRisk) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hRisk.postLedgerRawStageSubstitutionRisk
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hRisk.dependencyCycleRisk ∨
      hRisk.surrogateStreamSwapRisk
  }

/-- Meta-DARWIN refinement of the same queue. The exact correction is that the
Phase 5FB side should be treated as needing a substantive raw-stage theorem,
not just an import-free transport. -/
def pressure_first_refined_selected_branch_target_of_exactness_audit
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hAudit : SelectedGeneratedBranchQueueExactnessAudit) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hAudit.phase5fbSideStillOneAbstractionTooLate
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hAudit.earliestFakeStepIsCallingReplayModelARawCarrier
  }

/-- Final Phase 5FB correction after the DARWIN pass: the live clean-side queue
should treat replay transport and raw-stage theorem as distinct items. -/
def pressure_first_refined_selected_branch_target_of_phase5fb_split
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hReplay : Phase5FBGeneratedObservableReplayTransportTarget)
    (hRaw : Phase5FBRawStageTheoremTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hReplay.localRawSignedSourceCarrierStillNeedsReplayTransport ∨
      hRaw.preLedgerOrderingStillNeedsSubstantiveTheorem ∨
      hRaw.finiteProfileMobiusAuditStillNeedsSubstantiveTheorem
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hRaw.replayModelAloneDoesNotYetGiveRawCarrier
  }

/-- Sharper final reduction on the Phase 5FB side: the substantive raw-stage
theorem itself should be split into explicit storage and audit-commutation
targets so the kill path can attack the earlier unpaid theorem first. -/
def pressure_first_refined_selected_branch_target_of_phase5fb_storage_audit_split
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hStorage : Phase5FBThresholdRootRawStorageTarget)
    (hAudit : Phase5FBRawMobiusAuditCommutationTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hStorage.rawObservableStageStillNeedsExplicitStorageWitness ∨
      hAudit.finiteProfileMobiusAuditMustCommuteBeforeLedgerLayers
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hStorage.rawObservableStageStillNeedsExplicitStorageWitness ∨
      hAudit.rawObservableStageMayBeStoredYetAuditStillNeedsSeparateTheorem
  }

/-- External-result-aligned refinement of the same queue: the live theorem is
no longer replay transport or even the bundled raw-stage theorem, but the
stronger storage theorem with provenance and raw-audit fields. -/
def pressure_first_refined_selected_branch_target_of_phase5fb_storage_theorem
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hStorage : Phase5FBRawStageStorageTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hStorage.theoremExposesLocalRawCarrier ∨
      ¬ hStorage.preLedgerOrdering.rawSignedSourceExistsBeforeReplayLedgerMap ∨
      ¬ hStorage.sameSourceProvenance.bothNamesReferToTheSameRawSignedSource ∨
      ¬ hStorage.rawMobiusAuditCompatibility.rawAuditIsPerformedBeforeReplayLedgerMap
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hStorage.theoremExposesLocalRawCarrier
  }

/-- Sharper reduction: after the latest residual/void pass, the storage theorem
is now visibly downstream of the cross-corridor joint-provenance theorem. -/
def pressure_first_refined_selected_branch_target_of_storage_being_downstream_of_joint_provenance
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hOrdering : PreLedgerOrderingCertificate)
    (hAudit : RawFiniteProfileMobiusAuditCompatibility) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hStorage :=
    phase5fb_raw_stage_storage_theorem_of_joint_provenance_and_raw_audit
      phase5fb_replay_ledger_map_present hOrdering hJoint hAudit
  exact
    pressure_first_refined_selected_branch_target_of_phase5fb_storage_theorem
      hQueue hStorage

/-- Sharpest current reduction on the clean-side source seam. The strengthened
Phase 5FB storage theorem is now visibly downstream of:
1. cross-corridor joint provenance, and
2. actual-source-backed raw Mobius audit,
while ordering support is internal to the Phase 5FB observable corridor. -/
def pressure_first_refined_selected_branch_target_of_storage_being_downstream_of_joint_provenance_and_actual_source_mobius
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hOrderingSupport : Phase5FBObservableCorridorOrderingSupport)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hWitness : SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hStorage :=
    phase5fb_raw_stage_storage_theorem_of_joint_provenance_and_actual_source_mobius_witness
      phase5fb_replay_ledger_map_present hOrderingSupport hJoint hWitness
  exact
    pressure_first_refined_selected_branch_target_of_phase5fb_storage_theorem
      hQueue hStorage

/-- Sharper reduction if the existing source-audit target is already paid. In
that case the strengthened storage theorem is downstream of joint provenance
plus the source-audit object itself. -/
def pressure_first_refined_selected_branch_target_of_storage_being_downstream_of_joint_provenance_and_observable_source_audit
    {τ : ContinuumLPProfileTopology.{u}}
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hAudit : PressureFirstObservableSourceAuditTarget τ)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hStorage :=
    phase5fb_raw_stage_storage_theorem_of_joint_provenance_and_observable_source_audit
      hJoint hAudit B hglobal
  exact
    pressure_first_refined_selected_branch_target_of_phase5fb_storage_theorem
      hQueue hStorage

/-- Residual-void refinement of the same queue after reading the GP216/Phase5FB
interface more closely. Alignment/match objects are now explicit non-goals:
they help localize the seam but do not pay same-source provenance. -/
def pressure_first_refined_selected_branch_target_of_same_source_provenance_target
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hProv : SelectedGeneratedBranchSameSourceProvenanceTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hProv.sameRawSignedSourceStillNeedsExplicitIdentityCertificate
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hProv.currentBridgeObjectsAreStillAlignmentOrMatchOnly
  }

/-- Counterproof-side refinement of the same queue. The nearby branch-local
compatibility objects can be strong enough to tempt laundering while still
failing to certify same-source raw identity. -/
def pressure_first_refined_selected_branch_target_of_alignment_only_compatibility
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hCompat : AlignmentOnlyGeneratedBranchCompatibility) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hCompat.sameRawSourceIdentityIsStillNotCertified
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hCompat.sameRawSourceIdentityIsStillNotCertified
  }

/-- Residual-side refinement from the observable corridor. The Phase 5FB side
may have internal non-posthoc binding support and still fail to pay the
cross-corridor same-source theorem with GP216. -/
def pressure_first_refined_selected_branch_target_of_phase5fb_observable_side_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hSupport : Phase5FBObservableSideNonposthocBindingSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hSupport.supportStillStopsShortOfCrossCorridorJointProvenance
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hSupport.supportStillStopsShortOfCrossCorridorJointProvenance
  }

/-- Current sharpest provenance refinement after the residual/void pass. The
next honest theorem is no longer generic same-source talk; it is a joint
provenance theorem across the selected-branch stream corridor and the Phase 5FB
observable corridor. -/
def pressure_first_refined_selected_branch_target_of_joint_provenance_target
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hJoint.jointSameSourceProvenanceAcrossTheTwoCorridorsStillNeedsTheorem
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hJoint.jointSameSourceProvenanceAcrossTheTwoCorridorsStillNeedsTheorem
  }

/-- The weaker shared-generated-branch layer can be paid without collapsing
the dominant frontier. It separates a branch/index support fact from the
stronger same-source identity theorem. -/
def pressure_first_refined_selected_branch_target_of_shared_generated_branch_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hShared : SelectedBranchStreamObservableSharedGeneratedBranchTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hShared.theoremPaysSharedGeneratedBranchSupportOnly
  }

/-- Because the older selected-branch projected-stream compatibility target
already pays the weaker shared-generated-branch theorem, the joint-provenance
frontier should not keep treating branch co-location as if it were the unpaid
same-source theorem. -/
def pressure_first_refined_selected_branch_target_of_projected_stream_compatibility_paying_shared_generated_branch_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hCompat : SelectedGeneratedBranchProjectedStreamCompatibilityTarget) :
    PressureFirstRefinedSelectedBranchTarget :=
  pressure_first_refined_selected_branch_target_of_shared_generated_branch_support
    hQueue
    (selected_branch_stream_observable_shared_generated_branch_theorem_of_projected_stream_compatibility_target
      hCompat)

/-- The same refinement at theorem-shell granularity. This is the current
frontier more precisely than the older broad storage wording. -/
def pressure_first_refined_selected_branch_target_of_joint_provenance_theorem_gap
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hJoint.theoremIdentifiesSameRawSourceAcrossTheTwoCorridors
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hJoint.theoremIdentifiesSameRawSourceAcrossTheTwoCorridors
  }

/-- Counterproof-side refinement of the same provenance seam. Strong branch-
local alignment/transport objects still do not certify joint same-source raw
identity across the GP216 and Phase 5FB corridors. -/
def pressure_first_refined_selected_branch_target_of_alignment_transport_not_implying_joint_provenance
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : AlignmentTransportDoesNotImplyJointProvenance) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.sameRawSourceAcrossTheTwoCorridorsStillFails
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.sameRawSourceAcrossTheTwoCorridorsStillFails
  }

/-- Counterproof-side refinement for the weaker branch/block layer. Even if
shared generated-branch support is visible, the stronger same-source theorem
can still fail. -/
def pressure_first_refined_selected_branch_target_of_shared_generated_branch_not_implying_joint_provenance
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : SharedGeneratedBranchSupportDoesNotImplyJointProvenance) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.sameRawSourceAcrossTheTwoCorridorsStillFails
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.sameRawSourceAcrossTheTwoCorridorsStillFails
  }

/-- Sharper reduction after reading the Phase 5FB source-binding corridor. The
ordering side has internal support already; the frontier stays at joint
provenance and raw-audit compatibility. -/
def pressure_first_refined_selected_branch_target_of_ordering_support_being_internal
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hSupport : Phase5FBObservableCorridorOrderingSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hSupport.supportLivesInsideObservableCorridorOnly
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hSupport.supportLivesInsideObservableCorridorOnly
  }

/-- Sharper refinement of the raw-audit side. The remaining issue is now
explicitly the actual-source witness for the finite-profile raw Mobius audit,
not abstract existence of a Mobius shell. -/
def pressure_first_refined_selected_branch_target_of_raw_mobius_actual_source_witness
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hWitness : SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hWitness.theoremSuppliesActualSourceWitnessForRawMobiusAudit
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hWitness.theoremSuppliesActualSourceWitnessForRawMobiusAudit
  }

/-- Sharper reduction if the branch-local source-audit shell is paid. In that
case the raw Mobius actual-source witness is no longer a coequal frontier seam;
it is supplied by the branch-local source audit itself. -/
def pressure_first_refined_selected_branch_target_of_branch_source_audit
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hAudit : SelectedGeneratedBranchObservableSourceAuditTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hWitness :=
    selected_generated_branch_raw_mobius_actual_source_witness_of_branch_source_audit
      hAudit
  exact
    pressure_first_refined_selected_branch_target_of_raw_mobius_actual_source_witness
      hQueue hWitness

/-- The branch-local observable-ordering support is weaker than the full
branch-local source audit. It pays naming and pre-ledger support on the chosen
generated branch, but it leaves the finite-profile Möbius-audit support as the
surviving unpaid part. -/
def pressure_first_refined_selected_branch_target_of_branch_observable_ordering_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hOrdering.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
  }

/-- If the older source-audit target is already paid, then the sharper local
branch-source-audit shell is immediate on any chosen selected generated branch.
-/
def pressure_first_refined_selected_branch_target_of_observable_source_audit
    {τ : ContinuumLPProfileTopology.{u}}
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hAudit : PressureFirstObservableSourceAuditTarget τ)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hLocal :=
    selected_generated_branch_observable_source_audit_target_of_observable_source_audit
      hAudit B hglobal
  exact
    pressure_first_refined_selected_branch_target_of_branch_source_audit
      hQueue hLocal

/-- Counterproof-side refinement of the raw-audit seam. A Mobius-audit shell
can exist while still failing to witness the actual selected-branch raw source.
-/
def pressure_first_refined_selected_branch_target_of_surrogate_or_post_ledger_mobius_audit
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : SurrogateOrPostLedgerMobiusAuditDoesNotImplyActualSourceWitness) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.actualSelectedBranchRawSourceStillIsNotWitnessed
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.postLedgerOrSurrogateAuditCanMasqueradeAsRawAudit
  }

/-- Conditional counterproof refinement after the branch-local source-audit
split. If the local audit shell exists, the surviving kill surface is that the
audit still does not imply cross-corridor joint same-source provenance. -/
def pressure_first_refined_selected_branch_target_of_branch_source_audit_not_implying_joint_provenance
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : BranchSourceAuditDoesNotImplyJointProvenance) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.sameRawSourceAcrossTheTwoCorridorsStillFails
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.sameRawSourceAcrossTheTwoCorridorsStillFails
  }

/-- Counterproof-side refinement after splitting branch-local ordering support
from the finite-profile Möbius-audit part. Ordering/pre-ledger support can be
present while the actual local source-audit theorem remains unpaid. -/
def pressure_first_refined_selected_branch_target_of_observable_ordering_support_not_implying_branch_source_audit
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : ObservableOrderingSupportDoesNotImplyBranchSourceAudit) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.finiteProfileMobiusAuditSupportStillFails
  }

/-- Historical two-seam compression before the later support splits. After all
the reductions and kill passes up to this point, the frontier was exactly:
1. cross-corridor joint same-source provenance, and
2. actual-source-backed raw finite-profile Mobius audit.
Everything else on the clean side is now downstream, internal, or mechanical.
-/
def pressure_first_refined_selected_branch_target_of_two_seam_frontier
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hWitness : SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      (¬ hJoint.theoremIdentifiesSameRawSourceAcrossTheTwoCorridors) ∨
      (¬ hWitness.theoremSuppliesActualSourceWitnessForRawMobiusAudit)
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      (¬ hJoint.theoremIdentifiesSameRawSourceAcrossTheTwoCorridors) ∨
      (¬ hWitness.theoremSuppliesActualSourceWitnessForRawMobiusAudit)
  }

/-- Counterproof-side compression of the same frontier. The two surviving kill
surfaces are exactly the provenance-side alignment trap and the raw-audit-side
surrogate/post-ledger trap. -/
def pressure_first_refined_selected_branch_target_of_two_seam_counterproof_frontier
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hProvKill : AlignmentTransportDoesNotImplyJointProvenance)
    (hAuditKill : SurrogateOrPostLedgerMobiusAuditDoesNotImplyActualSourceWitness) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hProvKill.sameRawSourceAcrossTheTwoCorridorsStillFails ∨
      hAuditKill.actualSelectedBranchRawSourceStillIsNotWitnessed
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hProvKill.sameRawSourceAcrossTheTwoCorridorsStillFails ∨
      hAuditKill.postLedgerOrSurrogateAuditCanMasqueradeAsRawAudit
  }

/-- Historical frontier compression after the branch-local source-audit split.
This is still useful as a reduction lemma, but later support splits sharpen the
reading further. At this stage the remaining clean-side frontier is:
1. joint same-source provenance across the two corridors, and
2. paying the branch-local source audit itself. -/
def pressure_first_refined_selected_branch_target_of_joint_provenance_plus_branch_source_audit
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hAudit : SelectedGeneratedBranchObservableSourceAuditTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hWitness :=
    selected_generated_branch_raw_mobius_actual_source_witness_of_branch_source_audit
      hAudit
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      (¬ hJoint.theoremIdentifiesSameRawSourceAcrossTheTwoCorridors) ∨
      (¬ hWitness.theoremSuppliesActualSourceWitnessForRawMobiusAudit)
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      (¬ hJoint.theoremIdentifiesSameRawSourceAcrossTheTwoCorridors) ∨
      (¬ hWitness.theoremSuppliesActualSourceWitnessForRawMobiusAudit)
  }

/-- Historical dominant reading before the later support splits. The leading
unpaid theorem is cross-corridor joint provenance. The branch-local
source-audit shell is the secondary companion seam; if it is paid, the raw
Mobius actual-source witness becomes mechanical. -/
def pressure_first_refined_selected_branch_target_of_dominant_joint_provenance_frontier
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hAudit : SelectedGeneratedBranchObservableSourceAuditTarget) :
    PressureFirstRefinedSelectedBranchTarget :=
  pressure_first_refined_selected_branch_target_of_joint_provenance_plus_branch_source_audit
    hQueue hJoint hAudit

/-- Sharper local reading after splitting off shared-generated-branch support.
The weaker branch/index support appears to be nearby already; the surviving
dominant seam is the stronger provenance theorem plus the branch-local audit.
-/
def pressure_first_refined_selected_branch_target_of_joint_provenance_beyond_shared_generated_branch_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hShared : SelectedBranchStreamObservableSharedGeneratedBranchTheorem)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hAudit : SelectedGeneratedBranchObservableSourceAuditTarget) :
    PressureFirstRefinedSelectedBranchTarget :=
  pressure_first_refined_selected_branch_target_of_dominant_joint_provenance_frontier
    (pressure_first_refined_selected_branch_target_of_shared_generated_branch_support
      hQueue hShared)
    hJoint
    hAudit

/-- Same refinement, but expressed directly with the sharper theorem shell:
same-source identity beyond already-visible shared generated-branch support.
This is still not yet the final constructive theorem; the latest external kill
pass further demotes the honest positive target to raw pullback / storage
language. -/
def pressure_first_refined_selected_branch_target_of_same_source_beyond_shared_generated_branch_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hShared : SelectedBranchStreamObservableSharedGeneratedBranchTheorem)
    (hSameSource : SelectedBranchStreamObservableSameSourceBeyondSharedBranchTheorem)
    (hAudit : SelectedGeneratedBranchObservableSourceAuditTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hJoint :
      SelectedBranchStreamObservableJointProvenanceTheorem :=
    { target := {
        gp216SelectedBranchStreamCorridorIsNamed := True
        phase5fbObservableCorridorIsNamed := True
        sharedGeneratedBranchSupportIsAlreadyVisible :=
          hSameSource.target.sharedGeneratedBranchSupportIsNamed
        eachCorridorHasInternalProvenanceSupport :=
          hSameSource.target.eachCorridorHasInternalProvenanceSupport
        jointSameSourceProvenanceAcrossTheTwoCorridorsStillNeedsTheorem :=
          hSameSource.target.sameRawSourceBeyondSharedGeneratedBranchStillNeedsTheorem
      }
      theoremIdentifiesSameRawSourceAcrossTheTwoCorridors :=
        hSameSource.theoremIdentifiesSameRawSourceBeyondSharedGeneratedBranchSupport }
  exact
    pressure_first_refined_selected_branch_target_of_joint_provenance_beyond_shared_generated_branch_support
      hQueue hShared hJoint hAudit

/-- Historical sharpest reading before the latest external kill pass. At this
stage the remaining clean-side seams were phrased as:
1. same-source provenance beyond shared generated-branch support, and
2. actual-source-backed finite-profile Möbius support beyond branch-local
   ordering/pre-ledger support.
Later reductions demote the positive provenance side further to an explicit raw
pullback / same-source storage witness. -/
def pressure_first_refined_selected_branch_target_of_frontier_after_both_support_splits
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hShared : SelectedBranchStreamObservableSharedGeneratedBranchTheorem)
    (hJoint : SelectedBranchStreamObservableJointProvenanceTheorem)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport)
    (hWitness : SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hAudit :=
    selected_generated_branch_observable_source_audit_target_of_observable_ordering_support_and_raw_mobius_actual_source_witness
      hOrdering hWitness
  exact
    pressure_first_refined_selected_branch_target_of_joint_provenance_beyond_shared_generated_branch_support
      hQueue hShared hJoint hAudit

/-- Same historical refinement, but expressed directly with the sharper theorem
shells on both sides. This remains useful as an intermediate reduction, but the
latest external pass says the positive provenance target should now be the
same-source storage theorem rather than the weaker same-source wrapper alone. -/
def pressure_first_refined_selected_branch_target_of_frontier_after_sharper_support_splits
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hShared : SelectedBranchStreamObservableSharedGeneratedBranchTheorem)
    (hSameSource : SelectedBranchStreamObservableSameSourceBeyondSharedBranchTheorem)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport)
    (hMobius : SelectedGeneratedBranchMobiusSupportBeyondOrderingTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hWitness :
      SelectedGeneratedBranchRawMobiusActualSourceWitnessTheorem :=
    { target := {
        finiteProfileRawMobiusAuditIsNamed :=
          hMobius.target.finiteProfileRawMobiusAuditIsNamed
        auditUsesActualSelectedBranchRawSource :=
          ¬ hMobius.target.actualSourceBackedMobiusSupportStillNeedsTheorem
        auditIsNotReadOffFromPostLedgerReplay :=
          hMobius.target.branchLocalOrderingSupportIsNamed
      }
      theoremSuppliesActualSourceWitnessForRawMobiusAudit :=
        hMobius.theoremSuppliesActualSourceBackedMobiusSupportBeyondOrdering }
  exact
    pressure_first_refined_selected_branch_target_of_frontier_after_both_support_splits
      hQueue
      hShared
      { target := {
          gp216SelectedBranchStreamCorridorIsNamed := True
          phase5fbObservableCorridorIsNamed := True
          sharedGeneratedBranchSupportIsAlreadyVisible :=
            hSameSource.target.sharedGeneratedBranchSupportIsNamed
          eachCorridorHasInternalProvenanceSupport :=
            hSameSource.target.eachCorridorHasInternalProvenanceSupport
          jointSameSourceProvenanceAcrossTheTwoCorridorsStillNeedsTheorem :=
            hSameSource.target.sameRawSourceBeyondSharedGeneratedBranchStillNeedsTheorem
        }
        theoremIdentifiesSameRawSourceAcrossTheTwoCorridors :=
          hSameSource.theoremIdentifiesSameRawSourceBeyondSharedGeneratedBranchSupport }
      hOrdering
      hWitness

/-- DARWIN-compressed reading after the latest kill pass. The provenance side
remains the dominant live seam, and after collapsing the newer same-source
wrapper back onto the older explicit certificate, the live provenance object is
best read as the same-source raw provenance certificate gap itself. The
Möbius-beyond-ordering shell is no longer treated as a coequal frontier theorem
once one keeps track of the narrower branch-local source-audit shell that makes
it downstream. -/
def pressure_first_refined_selected_branch_target_of_darwin_kill_pass_on_sharper_frontier
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hShared : SelectedBranchStreamObservableSharedGeneratedBranchTheorem)
    (hSameSource : SelectedBranchStreamObservableSameSourceBeyondSharedBranchTheorem)
    (hAudit : SelectedGeneratedBranchObservableSourceAuditTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hBase :=
    pressure_first_refined_selected_branch_target_of_same_source_beyond_shared_generated_branch_support
      hQueue hShared hSameSource hAudit
  let hCert :=
    same_source_raw_provenance_certificate_of_same_source_beyond_shared_branch_theorem
      hSameSource
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hBase.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hBase.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hBase.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hBase.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hCert.bothNamesReferToTheSameRawSignedSource
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hBase.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hCert.bothNamesReferToTheSameRawSignedSource
  }

/-- Equivalent DARWIN reading when the local source-audit shell is expressed
via its split support layers instead of the bundled audit shell. This keeps the
file honest about what is already paid and what still survives. -/
def pressure_first_refined_selected_branch_target_of_darwin_kill_pass_after_support_splits
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hShared : SelectedBranchStreamObservableSharedGeneratedBranchTheorem)
    (hSameSource : SelectedBranchStreamObservableSameSourceBeyondSharedBranchTheorem)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport)
    (hMobius : SelectedGeneratedBranchMobiusSupportBeyondOrderingTheorem) :
    PressureFirstRefinedSelectedBranchTarget :=
  pressure_first_refined_selected_branch_target_of_frontier_after_sharper_support_splits
    hQueue hShared hSameSource hOrdering hMobius

/-- Strongest current compression of the provenance side after collapsing the
newer same-source shell back onto the older explicit certificate gap. The live
question is no longer whether we can name a sharper wrapper, but whether we can
actually pay the same-source raw provenance certificate. -/
def pressure_first_refined_selected_branch_target_of_same_source_certificate_gap
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hSameSource : SelectedBranchStreamObservableSameSourceBeyondSharedBranchTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hCert :=
    same_source_raw_provenance_certificate_of_same_source_beyond_shared_branch_theorem
      hSameSource
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hCert.bothNamesReferToTheSameRawSignedSource
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hCert.bothNamesReferToTheSameRawSignedSource
  }

/-- Corrected frontier after the latest external kill pass. The honest positive
provenance theorem is now the same-source storage theorem / raw pullback
witness, not the weaker same-source-beyond-shared-branch shell by itself. -/
def pressure_first_refined_selected_branch_target_of_same_source_storage_theorem_gap
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hStorage : SelectedBranchStreamObservableSameSourceStorageTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  let hCert :=
    same_source_raw_provenance_certificate_of_same_source_storage_theorem
      hStorage
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hCert.bothNamesReferToTheSameRawSignedSource
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hCert.bothNamesReferToTheSameRawSignedSource
  }

/-- Counterproof-side refinement after the latest external kill pass.
Noninjectivity of threshold-root / replay observables blocks any attempt to
upgrade weak branch-local compatibility into same-source provenance without an
explicit raw pullback/storage witness. -/
def pressure_first_refined_selected_branch_target_of_threshold_root_noninjectivity
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : ThresholdRootObservableNoninjectiveOnRawSources) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.thresholdRootOrReplayObservableAgreesOnThoseSources
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.thresholdRootOrReplayObservableAgreesOnThoseSources
  }

/-- Stronger counterproof-side refinement from the latest external pass. Even
if all weak branch-local compatibility facts hold simultaneously, they still do
not imply the corrected same-source storage theorem. -/
def pressure_first_refined_selected_branch_target_of_weak_compatibility_not_implying_same_source_storage
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : WeakBranchLocalCompatibilityDoesNotImplySameSourceStorageTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.sameSourceStorageStillFails
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.sameSourceStorageStillFails
  }

/-- Positive-side refinement on the corrected provenance target. If the branch
already carries an explicit raw pullback witness together with ordering and raw
finite-profile Möbius support, the selected-branch same-source storage theorem
is now the honest constructive carrier for the clean branch. -/
def pressure_first_refined_selected_branch_target_of_raw_pullback_and_certificates
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hWitness : SelectedBranchStreamObservableRawPullbackWitness)
    (hOrdering : SelectedGeneratedBranchObservableOrderingSupport)
    (hMobius : SelectedGeneratedBranchMobiusSupportBeyondOrderingTheorem) :
    PressureFirstRefinedSelectedBranchTarget :=
  pressure_first_refined_selected_branch_target_of_same_source_storage_theorem_gap
    hQueue
    (selected_branch_stream_observable_same_source_storage_theorem_of_raw_pullback_and_certificates
      hWitness hOrdering hMobius)

/-- Sharper local read after mining the Lipschitz-bridge provenance receipts.
The observable-side-before-ledger field appears closest to existing support;
the least mechanizable field is the GP216 stream-side presentation being
produced from that same common raw source. -/
def pressure_first_refined_selected_branch_target_of_observable_side_pre_ledger_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hSupport : ObservableSidePreLedgerRawPullbackSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hSupport.streamSidePresentationFromThatSameRawSourceStillLooksHardest
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hSupport.streamSidePresentationFromThatSameRawSourceStillLooksHardest
  }

/-- Sharper local read on the GP216 side after mining the projected-stream
audited-output route. The stream-side support is strong at the level of
projected stream plus audited output, but it still does not name the common raw
source required by the corrected provenance theorem. -/
def pressure_first_refined_selected_branch_target_of_gp216_projected_stream_audited_output_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hSupport : GP216ProjectedStreamAuditedOutputSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hSupport.supportStillStopsShortOfNamingCommonRawSignedSource
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hSupport.supportStillStopsShortOfNamingCommonRawSignedSource
  }

/-- Sharper local read after exposing the strongest GP216-side source-preserving
route. Even with selected projected audited source and compactness-bearing
measure-valued provenance attached, the GP216 side still stops short of naming
the common raw signed source required by the corrected same-source storage
theorem. -/
def pressure_first_refined_selected_branch_target_of_gp216_output_derived_source_provenance_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hSupport : GP216ProjectedStreamOutputDerivedSourceProvenanceSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hSupport.strongestGP216SourcePreservingRouteStillStopsShortOfCommonRawSignedSource
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hSupport.strongestGP216SourcePreservingRouteStillStopsShortOfCommonRawSignedSource
  }

/-- Positive queue reduction after isolating the exact GP216-side debt. The
remaining stream-side provenance work is no longer a generic support story: it
is the common raw pullback before projected-stream formation. -/
def pressure_first_refined_selected_branch_target_of_gp216_common_raw_pullback_target
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hTarget : GP216SelectedBranchCommonRawPullbackTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hTarget.commonRawSignedSourceIsNamedBeforeProjectedStreamFormation ∨
      ¬ hTarget.projectedSelectedBranchStreamIsProducedFromThatRawSource ∨
      ¬ hTarget.auditedOrMeasureValuedSelectedBranchSourceIsProducedFromThatRawSource
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hTarget.projectedSelectedBranchStreamIsProducedFromThatRawSource
  }

/-- Earlier GP216-side refinement after splitting out the raw-source naming
subfield. This isolates the first stream-side debt before the fuller common raw
pullback package is asked for. -/
def pressure_first_refined_selected_branch_target_of_gp216_raw_source_naming_target
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hTarget : GP216SelectedBranchRawSourceNamingTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hTarget.commonRawSignedSourceIsNamedBeforeProjectedStreamFormation
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hTarget.commonRawSignedSourceIsNamedBeforeProjectedStreamFormation
  }

/-- Honest positive GP216-side refinement after the latest mega pass. The
first constructive upgrade is not recovery from downstream projected
provenance; it is an explicit raw-source storage witness. -/
def pressure_first_refined_selected_branch_target_of_gp216_raw_source_storage_witness
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hWitness : GP216SelectedBranchRawSourceStorageWitness) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hWitness.commonRawSignedSourceIsExplicitlyStored ∨
      ¬ hWitness.projectedSelectedBranchStreamIsGeneratedFromThatRawSource ∨
      ¬ hWitness.downstreamSelectedSourcesAreCertifiedDescendantsOfThatRawSource
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hWitness.commonRawSignedSourceIsExplicitlyStored
  }

/-- Refinement for the narrower theorem shell that the projected selected
stream is generated from a stored raw source. -/
def pressure_first_refined_selected_branch_target_of_gp216_projected_stream_generated_from_raw_source
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hTheorem : GP216SelectedBranchProjectedStreamGeneratedFromRawSource) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hTheorem.theoremNamesProjectedStreamAsProjectionOfStoredRawSource
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hTheorem.theoremNamesProjectedStreamAsProjectionOfStoredRawSource
  }

/-- Negative queue reduction after the stronger GP216-side verdict. Even the
best output-derived selected-source provenance can still leave the common raw
pullback unpaid. -/
def pressure_first_refined_selected_branch_target_of_gp216_output_derived_provenance_not_implying_common_raw_pullback
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : GP216OutputDerivedSourceProvenanceDoesNotImplyCommonRawPullback) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.commonRawSignedSourceStillNotNamedBeforeProjectedStreamFormation
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.commonRawSignedSourceStillNotNamedBeforeProjectedStreamFormation
  }

/-- Earlier GP216-side negative refinement after splitting out raw-source
 naming. Output-derived and compactness-bearing selected-source provenance can
already be paid while this first raw-source naming field still fails. -/
def pressure_first_refined_selected_branch_target_of_gp216_output_derived_provenance_not_implying_raw_source_naming
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : GP216OutputDerivedProvenanceDoesNotImplyRawSourceNaming) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.commonRawSignedSourceStillNotNamedBeforeProjectedStreamFormation
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.commonRawSignedSourceStillNotNamedBeforeProjectedStreamFormation
  }

/-- Stronger negative refinement after the latest GP216 mega pass. Even the
entire selected projected-source chain can be source-preserving after
projection while the explicit raw-source storage witness still fails. -/
def pressure_first_refined_selected_branch_target_of_gp216_downstream_projected_provenance_not_implying_raw_source_storage_witness
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : GP216DownstreamProjectedProvenanceDoesNotImplyRawSourceStorageWitness) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.explicitRawSourceStorageWitnessStillFails
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.explicitRawSourceStorageWitnessStillFails
  }

/-- Negative refinement on the next bridge after storage witness language is
paid. A stored GP216 raw source can still fail to identify the actual
branch-local signed observable carrier used by the existing clean-side APIs. -/
def pressure_first_refined_selected_branch_target_of_gp216_raw_source_storage_not_yet_fixing_actual_observable_carrier
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : GP216RawSourceStorageDoesNotYetFixActualObservableCarrier) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.actualBranchLocalSignedObservableCarrierStillNeedsBridge
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.actualBranchLocalSignedObservableCarrierStillNeedsBridge
  }

/-- Frontier reduction after the latest GP216 mega result. The stream-side
positive lane is now cleanly phrased in storage-witness language, and the
observable-side local audit/storage work is downstream of it. -/
def pressure_first_refined_selected_branch_target_of_current_clean_side_stream_debt
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hDebt : PressureFirstCurrentCleanSideStreamDebt) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hDebt.gp216RawSourceStorageWitnessIsDominantStreamSideDebt
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hDebt.gp216RawSourceStorageWitnessIsDominantStreamSideDebt
  }

/-- Whole-graph reduction: the current GP216 storage debt is worth keeping in
the live queue precisely because it feeds the globally ranked bridge-
composition surface rather than only an internal local wrapper chain. -/
def pressure_first_refined_selected_branch_target_of_gp216_bridge_composition_receipt_whole_graph_relevance
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hGraph : GP216BridgeCompositionReceiptWholeGraphRelevance) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hGraph.currentGp216RawSourceStorageDebtFeedsThatTarget
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hGraph.currentGp216RawSourceStorageDebtFeedsThatTarget
  }

/-- Positive refinement from the nearest existing GP216 object below the broad
output-derived support shell. The selected-family observable subatom is worth
tracking because it preserves the selected approximation family, but it still
starts after projected-stream formation and therefore does not pay raw-source
naming. -/
def pressure_first_refined_selected_branch_target_of_gp216_selected_family_observable_subatom_nearest_raw_naming_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hSupport : GP216SelectedFamilyObservableSubatomNearestRawNamingSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hSupport.supportStillStartsAfterProjectedStreamFormation
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hSupport.supportStillStartsAfterProjectedStreamFormation
  }

/-- Partial positive refinement for the newer GP216 storage-witness split. The
selected-family / compactness route is the closest existing support for the
downstream-descendant-certification field, but it still leaves raw-source
storage itself unpaid. -/
def pressure_first_refined_selected_branch_target_of_gp216_selected_projected_descendant_certification_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hSupport : GP216SelectedProjectedDescendantCertificationSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hSupport.rawSourceStorageStillNeedsSeparateWitness
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hSupport.rawSourceStorageStillNeedsSeparateWitness
  }

/-- Partial positive refinement for the middle GP216 storage-witness field. The
continuum all-output family source is the nearest existing support for
projected-stream generation, but it still begins at an upstream family source
rather than at a named pre-projection raw signed source. -/
def pressure_first_refined_selected_branch_target_of_gp216_continuum_all_output_family_source_nearest_projected_generation_support
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hSupport : GP216ContinuumAllOutputFamilySourceNearestProjectedGenerationSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hSupport.upstreamFamilySourceStillDoesNotNamePreProjectionRawSignedSource
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hSupport.upstreamFamilySourceStillDoesNotNamePreProjectionRawSignedSource
  }

/-- Positive frontier collapse once the exact GP216-side debt and the local
observable-side audit shells are all paid. After that, the same-source storage
theorem itself no longer contributes live queue pressure. -/
def pressure_first_refined_selected_branch_target_of_gp216_common_raw_pullback_target_and_branch_source_audit
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hStorage : SelectedBranchStreamObservableSameSourceStorageTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∧
      ¬ hStorage.theoremPaysSameSourceProvenanceHonestly
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∧
      ¬ hStorage.theoremPaysSameSourceProvenanceHonestly
  }

/-- Negative frontier collapse after the stronger GP216-side kill. Even with
observable-side ordering and audit shells paid, the clean route still stays
blocked on the stream-side common raw pullback. -/
def pressure_first_refined_selected_branch_target_of_gp216_output_derived_provenance_kill_after_local_audit_shells
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hStorageGap :
      SelectedBranchStreamObservableSameSourceStorageTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hStorageGap.theoremPaysSameSourceProvenanceHonestly
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hStorageGap.theoremPaysSameSourceProvenanceHonestly
  }

/-- Anti-smuggling refinement for the extra GP216 grep surface. Internal
"same source bundle" equalities inside reserve/event bookkeeping should not be
allowed to masquerade as selected-branch common raw pullback evidence. -/
def pressure_first_refined_selected_branch_target_of_gp216_internal_same_source_bundle_language
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hSupport : GP216InternalSameSourceBundleLanguageSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hSupport.supportDoesNotNameSelectedBranchCommonRawSource
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hSupport.supportDoesNotNameSelectedBranchCommonRawSource
  }

/-- Counterproof refinement for the GP216 internal "same source bundle"
language. Even with those internal equalities, the selected-branch common raw
pullback can remain unpaid. -/
def pressure_first_refined_selected_branch_target_of_gp216_internal_same_source_bundle_language_not_implying_common_raw_pullback
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : GP216InternalSameSourceBundleLanguageDoesNotImplyCommonRawPullback) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.selectedBranchCommonRawPullbackStillFails
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.selectedBranchCommonRawPullbackStillFails
  }

/-- Sharper provenance-side refinement using the generated-matrix observable/root
receipts. These typed receipts are valuable, but they are still internal to the
generated matrix route and do not by themselves pay the cross-corridor
same-source raw certificate. -/
def pressure_first_refined_selected_branch_target_of_generated_matrix_observable_root_provenance
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hProv : GeneratedMatrixObservableRootProvenanceSupport) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hProv.supportStillDoesNotFixCrossCorridorRawSourceIdentity
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hProv.supportStillDoesNotFixCrossCorridorRawSourceIdentity
  }

/-- Counterproof-side refinement for the sharper observable/root provenance
layer. Even explicit generated-matrix observable/root provenance receipts can
hold while the same-source raw certificate still fails. -/
def pressure_first_refined_selected_branch_target_of_observable_root_provenance_not_implying_same_source_raw_certificate
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : ObservableRootProvenanceDoesNotImplySameSourceRawCertificate) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.sameSourceRawCertificateStillFails
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.sameSourceRawCertificateStillFails
  }

/-- Once corrected GP216/Phase5FB transport is paid, the assembly layer should
drop out of the frontier queue. This prevents the route from treating a now-
mechanical wrapper as if it were still a live theorem seam. -/
def pressure_first_refined_selected_branch_target_of_mechanical_assembly
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hAssembly : SelectedGeneratedBranchCleanSourceAssemblyTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∧
      ¬ hAssembly.assemblyUsesBothTransportTheorems
  }

/-- Final exact Phase 5FB queue reduction: after the DARWIN split, this side of
the seam is two theorem shells, not one vague transport story. -/
def pressure_first_refined_selected_branch_target_of_phase5fb_theorem_shell_gaps
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hReplay : Phase5FBGeneratedObservableReplayTransportTheorem)
    (hRaw : Phase5FBRawStageTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hReplay.transportProducesNamedObservableAndCharge ∨
      ¬ hRaw.theoremProducesLocalRawCarrier ∨
      ¬ hRaw.theoremPaysPreLedgerOrderingAndMobiusAudit
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hRaw.theoremProducesLocalRawCarrier
  }

/-- Final exact Phase 5FB queue reduction after splitting the substantive raw
stage theorem. The local queue now isolates replay transport, storage, and
Mobius-audit commutation as three distinct unpaid shells. -/
def pressure_first_refined_selected_branch_target_of_phase5fb_storage_audit_theorem_gaps
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hReplay : Phase5FBGeneratedObservableReplayTransportTheorem)
    (hStorage : Phase5FBThresholdRootRawStorageTheorem)
    (hAudit : Phase5FBRawMobiusAuditCommutationTheorem) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      ¬ hReplay.transportProducesNamedObservableAndCharge ∨
      ¬ hStorage.theoremExposesRawObservableBeforeLedgerLayers ∨
      ¬ hAudit.theoremShowsRawMobiusAuditCommutesBeforeLedgerLayers
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      ¬ hStorage.theoremExposesRawObservableBeforeLedgerLayers ∨
      ¬ hAudit.theoremShowsRawMobiusAuditCommutesBeforeLedgerLayers
  }

/-- Kill-side refinement of the same queue after the external Phase 5FB attack.
If replay does not determine the raw signed source, the clean branch stays
blocked even before pressure-tail work begins. -/
def pressure_first_refined_selected_branch_target_of_phase5fb_noninjective_replay_kill
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hKill : Phase5FBReplayDoesNotDetermineRawSignedSource) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hKill.replayToRawUpgradeNeedsExplicitStorageWitnesses
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hKill.replayDataAloneDoesNotFixSameRawSignedSource
  }

/-- The same queue after the sharpest local Phase 5FB anti-laundering verdict:
the replay model exists, but the raw carrier still needs a separate theorem. -/
def pressure_first_refined_selected_branch_target_of_phase5fb_replay_weakness
    (hQueue : PressureFirstRefinedSelectedBranchTarget)
    (hWeak : Phase5FBReplayModelTooWeakAsRawCarrier) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hQueue.selectedBranchProjectedStreamEqualityIsFirst
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hQueue.fullGlobalBlockIdentificationIsStrongerThanCurrentNeed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hQueue.pressureTailStillWaitsForActualObservableSourceMatch
    branchLocalRawStageStorageIsAlsoRequired :=
      hQueue.branchLocalRawStageStorageIsAlsoRequired ∨
      hWeak.rawCarrierNeedsExtraPreLedgerAndMobiusTheorem
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      hQueue.exactBranchLocalWitnessesStillNeedToBeBuilt ∨
      hWeak.replayModelByItselfIsNotYetLocalRawCarrier
  }

/-- The selected-branch reduction and the raw-stage storage requirement are the
two coupled source theorems now sitting ahead of pressure-tail PDE work. -/
def pressure_first_refined_selected_branch_target_of_storage_target
    (hEq : SelectedGeneratedBranchProjectedStreamCompatibilityTarget)
    (hRaw : SelectedGeneratedBranchRawStageStorageTarget) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      hEq.missingOnlyProjectedSelectedBranchStreamEqualityToAuditedSelfTaxStream
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hEq.generatedBranchBlockAlreadyNamedByHandoff ∧
      hEq.thresholdRootObservableSourceAlreadyLivesOnGeneratedBranch
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hEq.continuumProjectedSelectedBranchStreamAlreadyDefined
    branchLocalRawStageStorageIsAlsoRequired :=
      hRaw.rawSignedSourceMustBeStoredBeforeThresholdLedgering ∧
      hRaw.branchLocalRawStageStillNeedsActualObservableWitness
    exactBranchLocalWitnessesStillNeedToBeBuilt := True
  }

/-- Stronger refined target once the two exact branch-local witness objects are
used as the active theorem surfaces. -/
def pressure_first_refined_selected_branch_target_of_exact_witness_gaps
    (hEqW : SelectedGeneratedBranchProjectedStreamEqualityWitness)
    (hRawW : SelectedGeneratedBranchRawSignedSourceStorageWitness) :
    PressureFirstRefinedSelectedBranchTarget := by
  exact {
    selectedBranchProjectedStreamEqualityIsFirst :=
      ¬ hEqW.projectedSelectedBranchStreamEqualsAuditedSelfTaxStream
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hEqW.generatedSelectedBranchIsNamed ∧
      hEqW.projectedContinuumSelectedBranchStreamIsNamed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hEqW.auditedSelfTaxStreamOnSelectedBranchIsNamed
    branchLocalRawStageStorageIsAlsoRequired :=
      ¬ hRawW.rawSignedSourceIsStoredBeforeThresholdLedgering ∨
      ¬ hRawW.rawSignedSourceSupportsFiniteProfileMobiusAudit
    exactBranchLocalWitnessesStillNeedToBeBuilt :=
      (¬ hEqW.projectedSelectedBranchStreamEqualsAuditedSelfTaxStream) ∨
      (¬ hRawW.rawSignedSourceIsStoredBeforeThresholdLedgering)
  }

/-- Once both exact branch-local carriers are present, the refined clean-side
target can be expressed without any remaining witness-gap placeholders. -/
theorem pressure_first_refined_selected_branch_target_of_exact_carriers
    (hEqC : SelectedGeneratedBranchProjectedStreamEqualityCarrier)
    (hRawC : SelectedGeneratedBranchRawSignedSourceCarrier) :
    Nonempty PressureFirstRefinedSelectedBranchTarget := by
  let hEqW : SelectedGeneratedBranchProjectedStreamEqualityWitness :=
    Classical.choice
      (selected_generated_branch_projected_stream_equality_witness_of_carrier hEqC)
  let hRawW : SelectedGeneratedBranchRawSignedSourceStorageWitness :=
    Classical.choice
      (selected_generated_branch_raw_signed_source_storage_witness_of_carrier hRawC)
  exact ⟨{
    selectedBranchProjectedStreamEqualityIsFirst :=
      hEqW.projectedSelectedBranchStreamEqualsAuditedSelfTaxStream
    fullGlobalBlockIdentificationIsStrongerThanCurrentNeed :=
      hEqW.generatedSelectedBranchIsNamed ∧
      hEqW.projectedContinuumSelectedBranchStreamIsNamed
    pressureTailStillWaitsForActualObservableSourceMatch :=
      hEqW.auditedSelfTaxStreamOnSelectedBranchIsNamed
    branchLocalRawStageStorageIsAlsoRequired :=
      hRawW.rawSignedSourceIsStoredBeforeThresholdLedgering ∧
      hRawW.rawSignedSourceSupportsFiniteProfileMobiusAudit
    exactBranchLocalWitnessesStillNeedToBeBuilt := False
  }⟩

/-- Once the exact carriers are available, the final clean-source bundle
assembly theorem is mechanical. This demotes the assembly layer below the
Phase 5FB split liabilities. -/
def selected_generated_branch_clean_source_assembly_theorem_of_exact_carriers
    (hEqC : SelectedGeneratedBranchProjectedStreamEqualityCarrier)
    (hRawC : SelectedGeneratedBranchRawSignedSourceCarrier) :
    SelectedGeneratedBranchCleanSourceAssemblyTheorem where
  assemblyTarget := {
    bothExactTransportTargetsArePaid := True
    localCleanSourceBundleStillNeedsExactAssembly := False
  }
  localBundle := {
    streamEquality := hEqC
    rawSignedSourceStorage := hRawC
  }
  assemblyUsesBothTransportTheorems := True

/-- Current honest positive receipt after the external result: generated-image
compatibility is plausible, but it is explicitly not the same as a global block
universe identification theorem. -/
def generated_trajectory_pullback_source_compatibility_present :
    GeneratedTrajectoryPullbackSourceCompatibility := by
  exact {
    compatibilityHoldsOnGeneratedTrajectoryImage := True
    theoremIsTrajectoryBoundRatherThanGlobal := True
    thresholdRootSourceIsComparedOnlyAfterPullback := True
  }

/-- The current source inventory does not yet pay global coverage. -/
def generated_trajectory_covers_global_trackb_blocks_gap_present :
    GeneratedTrajectoryCoversGlobalTrackBBlocks := by
  exact {
    everyGlobalTrackBBlockAppearsInGeneratedTrajectoryImage := False
  }

/-- The current source inventory does not yet pay fiber coherence. -/
def generated_trajectory_fiber_coherence_gap_present :
    GeneratedTrajectoryFiberCoherence := by
  exact {
    thresholdRootObservableAgreesOnFibers := False
    generatedAuxiliaryObservableDataAgreesOnFibers := False
  }

/-- The current source inventory does not yet expose raw-stage storage at the
threshold-root level; this remains blocked by contamination/default-ledger
layers in the actual observable spine. -/
def threshold_root_stores_raw_signed_source_gap_present :
    ThresholdRootStoresRawSignedSource := by
  exact {
    rawSignedSourceCanBeReadBeforeLedgerPostProcessing := False
    thresholdRootDoesNotEraseTheNeededRawObservableStage := False
  }

/-- The current source inventory does not yet certify that the finite-profile
Möbius audit commutes with pullback after isolating the raw stage. -/
def raw_mobius_audit_commutes_with_generated_pullback_gap_present :
    RawMobiusAuditCommutesWithGeneratedPullback := by
  exact {
    rawMobiusAuditAppliedBeforeLedger := False
    pullbackPreservesRawMobiusAudit := False
  }

/-- External-result-aligned verdict: the strong global theorem is blocked by
four explicit missing hypotheses, while the weaker generated-image theorem
survives. -/
def pressure_first_global_identification_upgrade_gap_present :
    GlobalTrackBBlockGeneratedTrajectoryIdentificationUpgrade := by
  exact {
    coverage := generated_trajectory_covers_global_trackb_blocks_gap_present
    fiberCoherence := generated_trajectory_fiber_coherence_gap_present
    rawStorage := threshold_root_stores_raw_signed_source_gap_present
    rawMobiusPullback := raw_mobius_audit_commutes_with_generated_pullback_gap_present
  }

/-- Branch-default consequence of the external result after splitting the
strong global theorem into a weaker image theorem plus explicit extra
hypotheses. -/
structure PressureFirstCleanGlobalBranchBlocked where
  weakerGeneratedImageTheoremMayStillHold : Prop
  missingCoverageStillBlocksGlobalCleanBranch : Prop
  missingRawStageStorageStillBlocksGlobalCleanBranch : Prop
  contaminatedBranchRemainsDefaultUntilBothMove : Prop

/-- Even after reducing from global identification to the generated selected
branch, the clean branch stays blocked unless the branch-local raw stage is
stored before threshold-root ledgering. -/
def pressure_first_clean_branch_still_blocked_by_selected_branch_storage_gap
    (hEq : SelectedGeneratedBranchProjectedStreamCompatibilityTarget)
    (hRaw : SelectedGeneratedBranchRawStageStorageTarget) :
    PressureFirstCleanGlobalBranchBlocked := by
  exact {
    weakerGeneratedImageTheoremMayStillHold :=
      hEq.missingOnlyProjectedSelectedBranchStreamEqualityToAuditedSelfTaxStream
    missingCoverageStillBlocksGlobalCleanBranch := False
    missingRawStageStorageStillBlocksGlobalCleanBranch :=
      hRaw.rawSignedSourceMustBeStoredBeforeThresholdLedgering ∧
      hRaw.branchLocalRawStageStillNeedsActualObservableWitness
    contaminatedBranchRemainsDefaultUntilBothMove :=
      hRaw.rawSignedSourceMustBeStoredBeforeThresholdLedgering ∧
      hRaw.branchLocalRawStageStillNeedsActualObservableWitness
  }

/-- The current branch-default consequence of the external result. Even if the
generated-image theorem survives, the clean global branch should remain blocked
until at least coverage and raw-stage storage are paid. -/
def pressure_first_clean_global_branch_blocked_by_coverage_and_raw_storage
    (hWeak : GeneratedTrajectoryPullbackSourceCompatibility)
    (hUpgrade : GlobalTrackBBlockGeneratedTrajectoryIdentificationUpgrade) :
    PressureFirstCleanGlobalBranchBlocked := by
  exact {
    weakerGeneratedImageTheoremMayStillHold :=
      hWeak.compatibilityHoldsOnGeneratedTrajectoryImage
    missingCoverageStillBlocksGlobalCleanBranch :=
      ¬ hUpgrade.coverage.everyGlobalTrackBBlockAppearsInGeneratedTrajectoryImage
    missingRawStageStorageStillBlocksGlobalCleanBranch :=
      ¬ hUpgrade.rawStorage.rawSignedSourceCanBeReadBeforeLedgerPostProcessing
    contaminatedBranchRemainsDefaultUntilBothMove :=
      (¬ hUpgrade.coverage.everyGlobalTrackBBlockAppearsInGeneratedTrajectoryImage) ∨
      (¬ hUpgrade.rawStorage.rawSignedSourceCanBeReadBeforeLedgerPostProcessing)
  }

/-- The sharper anti-smuggling source bundle reinforces the same default:
until the route isolates a raw signed-observable stage using the same priced
survivor channel, the observable-source audit gap remains open. -/
def observable_source_audit_gap_of_anti_smuggling_sources
    (hAnti : TrackBObservableAntiSmugglingSources) :
    PressureFirstObservableSourceAuditGap := by
  exact {
    actualStreamFamilyStillNeedsRawStageIsolation :=
      hAnti.positiveOutputSurplusLayerPresent
    thresholdRootObservableSourceStillNeedsPreLedgerPlacement :=
      hAnti.thresholdDefectNeedsSameSurvivalObservable ∨
      hAnti.unrestrictedSurvivalProjectionSourceFamilyFails
    finiteProfileMobiusAuditStillLacksActualSourceWitness :=
      hAnti.hiddenSourceL2PricingIsInsufficient
  }

/-- The current local state identifies the bridge to the pre-ledger cubic
surrogate as the missing theorem, not as an already-paid fact. -/
def actual_observable_to_pre_ledger_cubic_surrogate_bridge_is_missing :
    Prop := by
  exact clean_branch_smuggling_risk_present.theoremConnectingActualObservableToSurrogateIsStillMissing

/-- Local no-go verdict from the completed observable audit. -/
def actual_observable_substitution_hazard_present :
    ActualObservableSubstitutionHazard := by
  exact {
    actualObservableClassification := actual_trackb_observable_classification_present
    smugglingRisk := clean_branch_smuggling_risk_present
    usingCleanBranchAsIfItWereTheActualObservableIsIllegitimate := True
  }

/-- Current theorem-frontier summary after the observable audit and delegate
passes. -/
def pressure_first_next_honest_theorem_target_present :
    PressureFirstNextHonestTheoremTarget := by
  exact {
    actualObservableToPreLedgerBridgeIsFirst := True
    pressurePairDecompositionIsNextOnlyAfterCleanBridge := True
    contaminatedBranchRemainsDefaultUntilBridgeProved := True
  }

/-- Current clean-side theorem-frontier summary after the latest GP216 mega
pass and local codification. -/
def pressure_first_current_clean_side_stream_debt_present :
    PressureFirstCurrentCleanSideStreamDebt := by
  exact {
    gp216RawSourceStorageWitnessIsDominantStreamSideDebt := True
    observableSidePreLedgerAndBranchAuditWorkAreDownstreamOfThatDebt := True
    downstreamProjectedProvenanceCannotStandInForStoredRawSource := True
  }

/-- Recomputed whole-graph verdict: the main self-tax profile-price stream is
still the top open Track B surface, so current source-side work remains
relevant only because it feeds that larger stream object. -/
def leray_self_tax_profile_price_stream_whole_graph_dominant_surface_present :
    LeraySelfTaxProfilePriceStreamWholeGraphDominantSurface := by
  exact {
    topOpenObligationInClosureMiner := True
    topArtifactLevelOpenSurfaceByReverseUse := True
    currentStreamSideDebtUltimatelyFeedsThisSurface := True
  }

/-- Recomputed whole-graph verdict for the current GP216 seam. The active
raw-source storage debt is not itself a top centrality hub, but it blocks a
globally ranked bridge-composition surface and therefore remains structurally
relevant. -/
def gp216_bridge_composition_receipt_whole_graph_relevance_present :
    GP216BridgeCompositionReceiptWholeGraphRelevance := by
  exact {
    bridgeCompositionReceiptIsGraphRankedTarget := True
    currentGp216RawSourceStorageDebtFeedsThatTarget := True
    currentFrontierIsLocalButNotIsolatedFromWholeGraph := True
  }

/-- Positive constructor for the clean-branch bridge once the sharper
raw-stage prerequisites are actually paid. This keeps the bridge theorem from
remaining an opaque slogan. -/
theorem actual_observable_bridge_of_prerequisites
    (hPrereq : ActualObservableBridgePrerequisites) :
    Nonempty ActualObservableToPreLedgerCubicSurrogateBridge := by
  exact ⟨{
    actualTrackBObservableIsNamed := True
    preLedgerCubicSurrogateIsNamed :=
      hPrereq.rawStageExtraction.rawSignedObservableStageIsNamed
    bridgeIsDeclaredBeforeEnvelopeFitting :=
      hPrereq.rawStageRestrictionIsDeclaredBeforeEnvelopeFitting
    bridgeRespectsFiniteProfileMobiusCoefficients :=
      hPrereq.rawStageSupportsFiniteProfileMobiusAudit
    bridgeRespectsCutoffGeometryAndCommonWindows :=
      hPrereq.rawStageMatchesFiniteProfilePriceFunctional
  }⟩

/-- A raw signed observable carrying the fully charged Track B interface is
enough to expose the earlier raw-stage extraction shell. This ties the
pressure-first bridge work back to the actual upstream observable class rather
than leaving it as free-floating booleans. -/
theorem actual_observable_raw_stage_extraction_of_signed_source
    (hSource : ActualObservableRawSignedSource) :
    Nonempty ActualObservableRawStageExtraction := by
  exact ⟨{
    rawSignedObservableStageIsNamed := True
    rawStagePrecedesThresholdCoordinateLayer :=
      hSource.rawStagePrecedesThresholdCoordinateLayer
    rawStagePrecedesQuarticSurvivalProjection :=
      hSource.rawStagePrecedesQuarticSurvivalProjection
    rawStagePrecedesNoSurvivorProjection :=
      hSource.rawStagePrecedesNoSurvivorProjection
    rawStagePrecedesPositiveCoherenceAggregation :=
      hSource.rawStagePrecedesPositiveCoherenceAggregation
  }⟩

/-- Source-backed constructor for the clean-branch prerequisite package. Once
the route can name a fully charged raw signed observable and verify that it
matches the finite-profile price functional before ledger post-processing, the
bridge theorem stops being purely aspirational. -/
theorem actual_observable_bridge_prerequisites_of_signed_source
    (hSource : ActualObservableRawSignedSource)
    (hMatchesFiniteProfilePriceFunctional : Prop)
    (hSupportsFiniteProfileMobiusAudit : Prop)
    (hDeclaredBeforeEnvelopeFitting : Prop) :
    Nonempty ActualObservableBridgePrerequisites := by
  let hExtraction : ActualObservableRawStageExtraction :=
    Classical.choice
      (actual_observable_raw_stage_extraction_of_signed_source hSource)
  exact ⟨{
    rawStageExtraction := hExtraction
    rawStageMatchesFiniteProfilePriceFunctional :=
      hMatchesFiniteProfilePriceFunctional
    rawStageSupportsFiniteProfileMobiusAudit :=
      hSupportsFiniteProfileMobiusAudit
    rawStageRestrictionIsDeclaredBeforeEnvelopeFitting :=
      hDeclaredBeforeEnvelopeFitting
  }⟩

/-- Adapter from the existing threshold-root observable source API to the new
raw signed-source carrier. This keeps the pressure-first frontier attached to
an actual upstream source family rather than inventing a fresh observable
class. -/
def actual_observable_raw_signed_source_of_threshold_root_observable_source
    (B : FullLedgerBlock)
    (S : QuarticSurvivalThresholdRootObservableSource B)
    (hPreThreshold : Prop)
    (hPreNoSurvivor : Prop)
    (hPrePositiveCoherence : Prop) :
    ActualObservableRawSignedSource where
  observable := S.observable
  observableFullyChargedAtRawStage := S.observable_fully_charged
  rawStagePrecedesThresholdCoordinateLayer := hPreThreshold
  rawStagePrecedesQuarticSurvivalProjection := True
  rawStagePrecedesNoSurvivorProjection := hPreNoSurvivor
  rawStagePrecedesPositiveCoherenceAggregation := hPrePositiveCoherence

/-- The stream-family audit target is enough to expose the earlier raw-stage
target currently sitting behind the bridge theorem. This is the cleanest
source-facing object to attack next if local work cannot decide the seam. -/
theorem pressure_first_raw_stage_extraction_target_of_observable_source_audit
    {τ : ContinuumLPProfileTopology.{u}}
    (hAudit : PressureFirstObservableSourceAuditTarget τ) :
    Nonempty PressureFirstRawStageExtractionTarget := by
  exact ⟨{
    signedObservableStageIsNamed := True
    stageOccursBeforeThresholdAndSurvivalLayers :=
      hAudit.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
    stageMatchesFiniteProfilePriceFunctional := True
    stageCanBeAuditedByFourProfileMobiusTest :=
      hAudit.sourceStageSupportsFiniteProfileMobiusAudit
  }⟩

/-- If the continuum all-output stream family and the Phase 5FB trajectory
observable source are proven compatible on global blocks, they assemble into
the concrete source-backed audit target introduced above. -/
theorem pressure_first_observable_source_audit_of_compatibility_witness
    {τ : ContinuumLPProfileTopology.{u}}
    (hCompat : PressureFirstObservableSourceCompatibilityWitness τ) :
    Nonempty (PressureFirstObservableSourceAuditTarget τ) := by
  refine ⟨{
    streamFamily := hCompat.streamFamily
    thresholdRootObservableSourceOfGlobal :=
      hCompat.thresholdRootObservableSourceOfGlobal
    sourceStageDeclaredBeforeThresholdAndSurvivalLayers :=
      hCompat.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
    sourceStageSupportsFiniteProfileMobiusAudit :=
      hCompat.sourceStageSupportsFiniteProfileMobiusAudit
  }⟩

/-- If the exact missing identification theorem is ever supplied, it should be
usable as the core positive ingredient of the compatibility witness rather than
forcing a new, broader source package. -/
theorem pressure_first_observable_source_compatibility_witness_of_identification
    {τ : ContinuumLPProfileTopology.{u}}
    (streamFamily :
      LeraySelfTaxContinuumAllOutputProfilePriceStreamFamilySource τ)
    (thresholdRootObservableSourceOfGlobal :
      ∀ B : FullLedgerBlock,
        IsGlobalTrackBBlock B →
          QuarticSurvivalThresholdRootObservableSource B)
    (hIdent : GlobalTrackBBlockGeneratedTrajectoryIdentification)
    (hPreLedger : Prop)
    (hMobiusAudit : Prop) :
    Nonempty (PressureFirstObservableSourceCompatibilityWitness τ) := by
  exact ⟨{
    streamFamily := streamFamily
    thresholdRootObservableSourceOfGlobal := thresholdRootObservableSourceOfGlobal
    thresholdRootSourcesComeFromGeneratedTrajectoryCorridor :=
      hIdent.everyGlobalTrackBBlockAppearsAsGeneratedLipschitzBlock
    sourceStageDeclaredBeforeThresholdAndSurvivalLayers := hPreLedger
    sourceStageSupportsFiniteProfileMobiusAudit := hMobiusAudit
  }⟩

/-- A single global block inside the new source-audit target already yields
the raw signed-source carrier needed by the clean-branch prerequisite path. -/
def actual_observable_raw_signed_source_of_observable_source_audit
    {τ : ContinuumLPProfileTopology.{u}}
    (hAudit : PressureFirstObservableSourceAuditTarget τ)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ActualObservableRawSignedSource :=
  actual_observable_raw_signed_source_of_threshold_root_observable_source
    B
    (hAudit.thresholdRootObservableSourceOfGlobal B hglobal)
    hAudit.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
    hAudit.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
    hAudit.sourceStageDeclaredBeforeThresholdAndSurvivalLayers

/-- Source-backed constructor for the exact next fork. If we need another
ambitious prompt, this is the object it should attack rather than the older
generic signed-envelope route. -/
theorem pressure_first_discriminating_fork_of_mobius_and_sources
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstDiscriminatingFork := by
  let hPair :
      FiniteProfilePressureCutoffComponentTest × LocalizedPressureTailCarlesonEnvelope :=
    Classical.choice
      (finite_pressure_cutoff_test_and_sources_expose_pressure_tail_envelope
        hMobius hSources)
  refine ⟨{
    finitePressureCutoffTest := hPair.1
    pressureTailEnvelopeTarget := hPair.2
    cubicCleanBranchOrHighOrderCoherenceWitness :=
      ¬ hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence ∨
      hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence
  }⟩

/-- Clean-branch constructor: if the Mobius expansion stays cubic and the
pressure-aware package is already assembled, then the pressure-first route can
stay focused on the pressure-tail theorem rather than reopening coherence
combinatorics. -/
theorem pressure_first_clean_cubic_route_of_mobius_and_sources
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (hSources : ExternalLocalizedLiabilitySources)
    (hNoPositivePart : ¬ hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence)
    (hPackage : PressureAwareComponentwiseLocalizedEnvelopePackage) :
    Nonempty PressureFirstCleanCubicRoute := by
  let hFork : PressureFirstDiscriminatingFork :=
    Classical.choice
      (pressure_first_discriminating_fork_of_mobius_and_sources
        hMobius hSources)
  let hSupport : PolynomialPriceStreamMobiusSupportLeThree :=
    Classical.choice
      (pressure_aware_mobius_profile_price_expansion_supports_polynomial_mobius_support
        hMobius hNoPositivePart)
  exact ⟨{
    fork := hFork
    cubicMobiusSupport := hSupport
    pressureAwarePackage := hPackage
  }⟩

/-- Sharper positive constructor: once pre-ledger cubicity itself is exposed,
the clean branch no longer needs to be phrased via the weaker negation of
positive-part contamination. -/
theorem pressure_first_clean_cubic_route_of_pre_ledger_cubicity
    (hCriterion : PreLedgerCubicPriceStreamCriterion)
    (hSources : ExternalLocalizedLiabilitySources)
    (hPackage : PressureAwareComponentwiseLocalizedEnvelopePackage) :
    Nonempty PressureFirstCleanCubicRoute := by
  let hMobius := hCriterion.mobiusCoefficientFamily.mobiusExpansion
  let hFork : PressureFirstDiscriminatingFork :=
    Classical.choice
      (pressure_first_discriminating_fork_of_mobius_and_sources
        hMobius hSources)
  let hSupport : PolynomialPriceStreamMobiusSupportLeThree :=
    Classical.choice
      (pre_ledger_cubic_price_stream_criterion_supports_polynomial_mobius_support
        hCriterion)
  exact ⟨{
    fork := hFork
    cubicMobiusSupport := hSupport
    pressureAwarePackage := hPackage
  }⟩

/-- Exact unlock theorem for the clean branch: if the missing bridge from the
actual Track B observable to a pre-ledger cubic surrogate is ever proved, the
route should be able to enter the clean branch through the sharper cubicity
criterion rather than by negating contamination indirectly. -/
theorem pressure_first_clean_cubic_route_of_actual_observable_bridge
    (hBridge : ActualObservableToPreLedgerCubicSurrogateBridge)
    (hCriterion : PreLedgerCubicPriceStreamCriterion)
    (hSources : ExternalLocalizedLiabilitySources)
    (hPackage : PressureAwareComponentwiseLocalizedEnvelopePackage) :
    Nonempty PressureFirstCleanCubicRoute := by
  let _hBridgeDeclaredBeforeEnvelope : Prop :=
    hBridge.bridgeIsDeclaredBeforeEnvelopeFitting
  exact pressure_first_clean_cubic_route_of_pre_ledger_cubicity
    hCriterion hSources hPackage

/-- Contaminated-branch constructor: if positive-part / thresholding survives,
the route must carry an explicit witness that coherence cleanup remains after
the pressure-tail theorem surface. -/
theorem pressure_first_high_order_coherence_contamination_route_of_mobius_and_sources
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (hSources : ExternalLocalizedLiabilitySources)
    (hPositivePart : hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence) :
    Nonempty PressureFirstHighOrderCoherenceContaminationRoute := by
  let hFork : PressureFirstDiscriminatingFork :=
    Classical.choice
      (pressure_first_discriminating_fork_of_mobius_and_sources
        hMobius hSources)
  let hWitness : PositivePartPriceStreamHighOrderCoherenceWitness :=
    Classical.choice
      (pressure_aware_mobius_profile_price_expansion_exposes_high_order_coherence_witness
        hMobius hPositivePart)
  exact ⟨{
    fork := hFork
    contaminationWitness := hWitness
    coherenceCleanupStillNeededAfterPressureTail := True
  }⟩

/-- Typed no-go receipt for the contaminated branch: once high-order coherence
survives the Mobius expansion, a pressure-tail theorem alone cannot honestly
be presented as the whole remaining closure mechanism. -/
theorem pressure_tail_alone_insufficient_under_high_order_coherence
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (hSources : ExternalLocalizedLiabilitySources)
    (hPositivePart : hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence) :
    Nonempty PressureTailAloneInsufficientUnderHighOrderCoherence := by
  let hRoute : PressureFirstHighOrderCoherenceContaminationRoute :=
    Classical.choice
      (pressure_first_high_order_coherence_contamination_route_of_mobius_and_sources
        hMobius hSources hPositivePart)
  exact ⟨{
    contaminatedRoute := hRoute
    pressureTailTheoremWouldStillLeaveResidualCoherenceDebt := True
  }⟩

/-- Sharper contaminated-branch constructor: if a high-order coherence witness
is already visible, the no-go for pressure-tail-only closure should not depend
on rebuilding the whole branch from scratch. -/
theorem pressure_tail_alone_insufficient_of_high_order_coherence_witness
    (hWitness : PositivePartPriceStreamHighOrderCoherenceWitness)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureTailAloneInsufficientUnderHighOrderCoherence := by
  let hMobius := hWitness.mobiusCoefficientFamily.mobiusExpansion
  let hFork : PressureFirstDiscriminatingFork :=
    Classical.choice
      (pressure_first_discriminating_fork_of_mobius_and_sources
        hMobius hSources)
  exact ⟨{
    contaminatedRoute := {
      fork := hFork
      contaminationWitness := hWitness
      coherenceCleanupStillNeededAfterPressureTail := True
    }
    pressureTailTheoremWouldStillLeaveResidualCoherenceDebt := True
  }⟩

/-- Clean-side route decision constructor. If pre-ledger cubicity is available,
the decision object should record that pressure-tail can remain the whole next
theorem target on this branch. -/
theorem pressure_first_route_decision_of_clean_branch
    (hCriterion : PreLedgerCubicPriceStreamCriterion)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hMobius := hCriterion.mobiusCoefficientFamily.mobiusExpansion
  let hFork : PressureFirstDiscriminatingFork :=
    Classical.choice
      (pressure_first_discriminating_fork_of_mobius_and_sources
        hMobius hSources)
  let _hFourProfile : FourProfileLedgerMobiusTest :=
    Classical.choice
      (pre_ledger_cubic_price_stream_criterion_supports_four_profile_mobius_test
        hCriterion)
  exact ⟨{
    fork := hFork
    cleanCriterionAvailable := True
    preLedgerCubicityFails := False
    pressureTailRemainsWholeNextTheoremExactlyWhenCleanBranchHolds := True
    fourProfileMobiusTestAvailable := True
  }⟩

/-- Exact route-decision unlock from the missing bridge theorem. Once the
actual observable is proven equivalent to the pre-ledger cubic surrogate in the
relevant sense, the clean branch should become available by construction. -/
theorem pressure_first_route_decision_of_actual_observable_bridge
    (hBridge : ActualObservableToPreLedgerCubicSurrogateBridge)
    (hCriterion : PreLedgerCubicPriceStreamCriterion)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hDecision : PressureFirstRouteDecision :=
    Classical.choice
      (pressure_first_route_decision_of_clean_branch hCriterion hSources)
  exact ⟨{
    fork := hDecision.fork
    cleanCriterionAvailable := hBridge.bridgeIsDeclaredBeforeEnvelopeFitting
    preLedgerCubicityFails := False
    pressureTailRemainsWholeNextTheoremExactlyWhenCleanBranchHolds := True
    fourProfileMobiusTestAvailable := hDecision.fourProfileMobiusTestAvailable
  }⟩

/-- Sharper clean-side route-decision constructor: the new raw-stage
prerequisite package should be enough to produce the bridge theorem and then
unlock the same clean branch without hiding the earlier source-facing burden. -/
theorem pressure_first_route_decision_of_bridge_prerequisites
    (hPrereq : ActualObservableBridgePrerequisites)
    (hCriterion : PreLedgerCubicPriceStreamCriterion)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hBridge : ActualObservableToPreLedgerCubicSurrogateBridge :=
    Classical.choice (actual_observable_bridge_of_prerequisites hPrereq)
  exact pressure_first_route_decision_of_actual_observable_bridge
    hBridge hCriterion hSources

/-- End-to-end clean-side constructor from the actual upstream observable
class. If the route can exhibit a fully charged raw signed observable that
matches the finite-profile price functional before ledger post-processing,
then the pressure-first clean-branch decision is available without any
intermediate opaque theorem packaging. -/
theorem pressure_first_route_decision_of_signed_source
    (hSource : ActualObservableRawSignedSource)
    (hMatchesFiniteProfilePriceFunctional : Prop)
    (hSupportsFiniteProfileMobiusAudit : Prop)
    (hDeclaredBeforeEnvelopeFitting : Prop)
    (hCriterion : PreLedgerCubicPriceStreamCriterion)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hPrereq : ActualObservableBridgePrerequisites :=
    Classical.choice
      (actual_observable_bridge_prerequisites_of_signed_source
        hSource
        hMatchesFiniteProfilePriceFunctional
        hSupportsFiniteProfileMobiusAudit
        hDeclaredBeforeEnvelopeFitting)
  exact pressure_first_route_decision_of_bridge_prerequisites
    hPrereq hCriterion hSources

/-- End-to-end clean-side constructor from the concrete stream-family audit
target. This is the most source-faithful positive path currently visible in
the file: actual stream family + threshold-root observable source + finite-
profile matching + Mobius audit + pre-ledger cubic criterion. -/
theorem pressure_first_route_decision_of_observable_source_audit
    {τ : ContinuumLPProfileTopology.{u}}
    (hAudit : PressureFirstObservableSourceAuditTarget τ)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hCriterion : PreLedgerCubicPriceStreamCriterion)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hSource : ActualObservableRawSignedSource :=
    actual_observable_raw_signed_source_of_observable_source_audit
      hAudit B hglobal
  exact pressure_first_route_decision_of_signed_source
    hSource
    True
    hAudit.sourceStageSupportsFiniteProfileMobiusAudit
    hAudit.sourceStageDeclaredBeforeThresholdAndSurvivalLayers
    hCriterion
    hSources

/-- End-to-end clean-side constructor from the narrower compatibility witness
between the best existing continuum stream-family source and the best existing
threshold-root observable source corridor. -/
theorem pressure_first_route_decision_of_observable_source_compatibility_witness
    {τ : ContinuumLPProfileTopology.{u}}
    (hCompat : PressureFirstObservableSourceCompatibilityWitness τ)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hCriterion : PreLedgerCubicPriceStreamCriterion)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hAudit : PressureFirstObservableSourceAuditTarget τ :=
    Classical.choice
      (pressure_first_observable_source_audit_of_compatibility_witness
        hCompat)
  exact pressure_first_route_decision_of_observable_source_audit
    hAudit B hglobal hCriterion hSources

/-- Source-facing default no-go: if the observable-source audit target is
still absent, the clean branch remains unavailable as a statement about the
actual Track B observable. This keeps the new positive source path paired with
an equally explicit negative branch. -/
theorem pressure_first_route_decision_of_observable_source_audit_gap
    (hGap : PressureFirstObservableSourceAuditGap)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hHazard : ActualObservableSubstitutionHazard :=
    actual_observable_substitution_hazard_present
  let hObservable : ActualTrackBObservableClassification :=
    hHazard.actualObservableClassification
  let hSurface : TrackBLedgerContaminationSurface :=
    hObservable.contaminationSurface
  let hFork : PressureFirstDiscriminatingFork :=
    Classical.choice
      (pressure_first_discriminating_fork_of_mobius_and_sources
        {
          assignment := {
            decomposition := hSources.expansion.decomposition
            aggregateSignedPriceStreamExists := True
            selfTaxAssignmentIsHonest := True
            crossDefectAssignmentIsHonest := True
            coherenceAssignmentIsHonest := True
            assignmentRespectsLocalizationAndTimeWindows := True
          }
          finiteProfileSubsetFunctionalsAreDefined := True
          mobiusCoefficientsAreCanonicallyDefined := True
          singletonCoefficientsAreSelfTax := True
          pairCoefficientsAreCrossDefect := True
          higherCoefficientsAreCoherence := True
          positivePartOrThresholdingCanCreateHighOrderCoherence :=
            hSurface.thresholdCoordinateLayerPresent ∨
            hSurface.survivalLedgerLayerPresent ∨
            hSurface.noSurvivorLayerPresent ∨
            hSurface.positiveCoherenceLayerPresent
        }
        hSources)
  exact ⟨{
    fork := hFork
    cleanCriterionAvailable := False
    preLedgerCubicityFails :=
      hGap.actualStreamFamilyStillNeedsRawStageIsolation ∨
      hGap.thresholdRootObservableSourceStillNeedsPreLedgerPlacement ∨
      hGap.finiteProfileMobiusAuditStillLacksActualSourceWitness
    pressureTailRemainsWholeNextTheoremExactlyWhenCleanBranchHolds := True
    fourProfileMobiusTestAvailable := True
  }⟩

/-- Stronger default no-go incorporating the newly exposed compatibility
obstruction between the best existing stream-family source and the best
existing threshold-root observable source. -/
theorem pressure_first_route_decision_of_observable_source_compatibility_gap
    (hGap : PressureFirstObservableSourceCompatibilityGap)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hBlocked : PressureFirstRouteDecision :=
    Classical.choice
      (pressure_first_route_decision_of_observable_source_audit_gap
        pressure_first_observable_source_audit_gap_present
        hSources)
  exact ⟨{
    fork := hBlocked.fork
    cleanCriterionAvailable := False
    preLedgerCubicityFails :=
      hGap.continuumStreamFamilyRangesOverAllGlobalBlocks ∨
      hGap.thresholdRootObservableSourceRangesOnlyOverGeneratedBlocks ∨
      hGap.missingIdentificationBetweenGlobalAndGeneratedBlocks
    pressureTailRemainsWholeNextTheoremExactlyWhenCleanBranchHolds :=
      hBlocked.pressureTailRemainsWholeNextTheoremExactlyWhenCleanBranchHolds
    fourProfileMobiusTestAvailable := hBlocked.fourProfileMobiusTestAvailable
  }⟩

/-- Default route-decision no-go for the actual observable. Until the bridge
theorem is paid, the clean branch must not be advertised as a statement about
the current Track B observable. -/
theorem pressure_first_route_decision_blocks_clean_branch_on_actual_observable
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hHazard : ActualObservableSubstitutionHazard :=
    actual_observable_substitution_hazard_present
  let hObservable : ActualTrackBObservableClassification :=
    hHazard.actualObservableClassification
  let hSurface : TrackBLedgerContaminationSurface :=
    hObservable.contaminationSurface
  let hFork : PressureFirstDiscriminatingFork :=
    Classical.choice
      (pressure_first_discriminating_fork_of_mobius_and_sources
        {
          assignment := {
            decomposition := hSources.expansion.decomposition
            aggregateSignedPriceStreamExists := True
            selfTaxAssignmentIsHonest := True
            crossDefectAssignmentIsHonest := True
            coherenceAssignmentIsHonest := True
            assignmentRespectsLocalizationAndTimeWindows := True
          }
          finiteProfileSubsetFunctionalsAreDefined := True
          mobiusCoefficientsAreCanonicallyDefined := True
          singletonCoefficientsAreSelfTax := True
          pairCoefficientsAreCrossDefect := True
          higherCoefficientsAreCoherence := True
          positivePartOrThresholdingCanCreateHighOrderCoherence :=
            hSurface.thresholdCoordinateLayerPresent ∨
            hSurface.survivalLedgerLayerPresent ∨
            hSurface.noSurvivorLayerPresent ∨
            hSurface.positiveCoherenceLayerPresent
        }
        hSources)
  exact ⟨{
    fork := hFork
    cleanCriterionAvailable := False
    preLedgerCubicityFails :=
      hHazard.actualObservableClassification.contaminatedBranchIsALiveDefaultUntilThatProofExists
    pressureTailRemainsWholeNextTheoremExactlyWhenCleanBranchHolds := True
    fourProfileMobiusTestAvailable := True
  }⟩

/-- Contaminated-side route decision constructor. If pre-ledger cubicity fails,
the decision object should explicitly record that pressure-tail is no longer the
whole remaining theorem. -/
theorem pressure_first_route_decision_of_pre_ledger_cubicity_failure
    (hFailure : PreLedgerCubicityFailure)
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hMobius := hFailure.mobiusCoefficientFamily.mobiusExpansion
  let hFork : PressureFirstDiscriminatingFork :=
    Classical.choice
      (pressure_first_discriminating_fork_of_mobius_and_sources
        hMobius hSources)
  exact ⟨{
    fork := hFork
    cleanCriterionAvailable := False
    preLedgerCubicityFails := True
    pressureTailRemainsWholeNextTheoremExactlyWhenCleanBranchHolds := True
    fourProfileMobiusTestAvailable := True
  }⟩

/-- Route-level observable audit: because the Track B file already contains
threshold / survival / no-survivor / positive-coherence layers, any claim that
the actual observable is cleanly pre-ledger cubic must be earned explicitly. -/
theorem trackb_ledger_contamination_surface_forces_observable_audit
    (hSources : ExternalLocalizedLiabilitySources) :
    Nonempty PressureFirstRouteDecision := by
  let hObservable : ActualTrackBObservableClassification :=
    actual_trackb_observable_classification_present
  let hSmuggling : CleanBranchSmugglingRisk :=
    clean_branch_smuggling_risk_present
  let hSurface : TrackBLedgerContaminationSurface :=
    hObservable.contaminationSurface
  let hFork : PressureFirstDiscriminatingFork :=
    Classical.choice
      (pressure_first_discriminating_fork_of_mobius_and_sources
        {
          assignment := {
            decomposition := hSources.expansion.decomposition
            aggregateSignedPriceStreamExists := True
            selfTaxAssignmentIsHonest := True
            crossDefectAssignmentIsHonest := True
            coherenceAssignmentIsHonest := True
            assignmentRespectsLocalizationAndTimeWindows := True
          }
          finiteProfileSubsetFunctionalsAreDefined := True
          mobiusCoefficientsAreCanonicallyDefined := True
          singletonCoefficientsAreSelfTax := True
          pairCoefficientsAreCrossDefect := True
          higherCoefficientsAreCoherence := True
          positivePartOrThresholdingCanCreateHighOrderCoherence :=
            hSurface.thresholdCoordinateLayerPresent ∨
            hSurface.survivalLedgerLayerPresent ∨
            hSurface.noSurvivorLayerPresent ∨
            hSurface.positiveCoherenceLayerPresent
        }
        hSources)
  exact ⟨{
    fork := hFork
    cleanCriterionAvailable :=
      ¬ hSmuggling.theoremConnectingActualObservableToSurrogateIsStillMissing
    preLedgerCubicityFails :=
      hObservable.contaminatedBranchIsALiveDefaultUntilThatProofExists
    pressureTailRemainsWholeNextTheoremExactlyWhenCleanBranchHolds := True
    fourProfileMobiusTestAvailable := True
  }⟩

/-- Competing hypothesis A: the first real obstruction sits in the bilinear
cross-defect family, not in the self-tax or coherence families. -/
structure CrossDefectSchurFirstFailure where
  componentExpansion : LocalizedPriceStreamComponentExpansion
  selfTaxLooksPayable : Prop
  coherenceLooksPayable : Prop
  bilinearSchurControlIsTheFirstNontrivialGap : Prop

/-- Competing hypothesis B: the higher-order coherence family is the actual
first obstruction, so pairwise / bilinear control is not the hard part. -/
structure CoherenceCarlesonFirstFailure where
  componentExpansion : LocalizedPriceStreamComponentExpansion
  selfTaxLooksPayable : Prop
  crossDefectLooksPayable : Prop
  multilinearCarlesonControlIsTheFirstNontrivialGap : Prop

/-- Competing hypothesis C: the envelope families themselves are not first;
localized pressure tails break the route before the family-wise envelope
question is even well posed. -/
structure PressureTailFirstFailure where
  expansion : NSPriceStreamHypergraphExpansion
  componentFamiliesLookFormallyReasonable : Prop
  pressureTailControlBreaksBeforeEnvelopeSummability : Prop

/-- Competing hypothesis D: the route fails even earlier because component
assignment into self-tax / cross-defect / coherence cannot be made
noncircularly for the localized signed price stream. -/
structure ComponentAssignmentFirstFailure where
  decomposition : NSCriticalProfileDecomposition
  aggregateSignedPriceStreamExistsOnlyAsOneBlob : Prop
  honestComponentSeparationFailsBeforeEnvelopeQuestions : Prop

/-- Explicit multi-hypothesis surface for the next external wave: after the
2026-05-09 route reductions, the live question is not "does the route work?"
but "which upstream seam breaks first?" -/
structure ComponentwiseSignedEnvelopeCompetingHypotheses where
  crossDefectFirst : CrossDefectSchurFirstFailure
  coherenceFirst : CoherenceCarlesonFirstFailure
  pressureTailFirst : PressureTailFirstFailure
  componentAssignmentFirst : ComponentAssignmentFirstFailure

/-- Revised local ranking carrier after the latest parallel external verdict:
component assignment may be formally available via a Mobius expansion, while
pressure-tail control becomes the first genuinely analytic seam. -/
structure RevisedSignedEnvelopeBottleneckRanking where
  mobiusExpansion : PressureAwareMobiusProfilePriceExpansion
  pressureTailFirst : PressureTailFirstFailure
  coherenceSecond : CoherenceCarlesonFirstFailure
  crossDefectThird : CrossDefectSchurFirstFailure
  componentAssignmentDemotedButStillFragile : ComponentAssignmentFirstFailure

/-- Local constructor for the revised ranking. This keeps the repo's active
story synchronized with the latest external result instead of leaving the old
D-first ordering implicit. -/
theorem revised_signed_envelope_bottleneck_ranking_surface
    (hMobius : PressureAwareMobiusProfilePriceExpansion)
    (hExpansion : NSPriceStreamHypergraphExpansion)
    (hComponents : LocalizedPriceStreamComponentExpansion) :
    Nonempty RevisedSignedEnvelopeBottleneckRanking := by
  refine ⟨{
    mobiusExpansion := hMobius
    pressureTailFirst := {
      expansion := hExpansion
      componentFamiliesLookFormallyReasonable := True
      pressureTailControlBreaksBeforeEnvelopeSummability := True
    }
    coherenceSecond := {
      componentExpansion := hComponents
      selfTaxLooksPayable := True
      crossDefectLooksPayable := True
      multilinearCarlesonControlIsTheFirstNontrivialGap := True
    }
    crossDefectThird := {
      componentExpansion := hComponents
      selfTaxLooksPayable := True
      coherenceLooksPayable := True
      bilinearSchurControlIsTheFirstNontrivialGap := True
    }
    componentAssignmentDemotedButStillFragile := {
      decomposition := hComponents.decomposition
      aggregateSignedPriceStreamExistsOnlyAsOneBlob := False
      honestComponentSeparationFailsBeforeEnvelopeQuestions :=
        hMobius.positivePartOrThresholdingCanCreateHighOrderCoherence
    }
  }⟩

/-- Local constructor for the explicit multi-hypothesis surface. This lets the
route carry competing upstream failure stories as first-class objects instead
of forcing a fake single-thread narrative before the mathematics decides. -/
theorem componentwise_signed_envelope_competing_hypotheses_surface
    (hComponents : LocalizedPriceStreamComponentExpansion)
    (hExpansion : NSPriceStreamHypergraphExpansion) :
    Nonempty ComponentwiseSignedEnvelopeCompetingHypotheses := by
  refine ⟨{
    crossDefectFirst := {
      componentExpansion := hComponents
      selfTaxLooksPayable := True
      coherenceLooksPayable := True
      bilinearSchurControlIsTheFirstNontrivialGap := True
    }
    coherenceFirst := {
      componentExpansion := hComponents
      selfTaxLooksPayable := True
      crossDefectLooksPayable := True
      multilinearCarlesonControlIsTheFirstNontrivialGap := True
    }
    pressureTailFirst := {
      expansion := hExpansion
      componentFamiliesLookFormallyReasonable := True
      pressureTailControlBreaksBeforeEnvelopeSummability := True
    }
    componentAssignmentFirst := {
      decomposition := hComponents.decomposition
      aggregateSignedPriceStreamExistsOnlyAsOneBlob := True
      honestComponentSeparationFailsBeforeEnvelopeQuestions := True
    }
  }⟩

/-- Candidate decisive mechanism from the 2026-05-09 mega-route reduction:
the self-tax, cross-defect, and coherence interactions admit a summable
positive envelope on the profile-interaction hypergraph. -/
structure ProfileSchurCarlesonEnvelope where
  selfTaxAtomsControlledBySquareSummableProfileMass : Prop
  crossDefectAtomsControlledByBilinearSchurKernel : Prop
  coherenceAtomsControlledByMultilinearCarlesonKernel : Prop
  tailTouchingInteractionsAreSummablySmall : Prop

/-- Sharper predecessor to the old abstract envelope shell: this version is
explicitly localized, signed, and tied to an actual NS price-stream expansion.
The surviving route now lives or dies here. -/
structure LocalizedProfileSchurCarlesonEnvelope where
  expansion : NSPriceStreamHypergraphExpansion
  cutoffStability : LocalizedCutoffStabilityReceipt
  pressureTailControl : PressureTailControlReceipt
  commonWindow : CommonProfileWindowReceipt
  absoluteEnvelopeDominatesSignedCoefficients : Prop
  selfTaxAtomsControlledBySquareSummableProfileMass : Prop
  crossDefectAtomsControlledByBilinearSchurKernel : Prop
  coherenceAtomsControlledByMultilinearCarlesonKernel : Prop
  tailTouchingInteractionsAreSummablySmall : Prop

/-- The componentwise package should refine to the aggregate localized envelope
shell used downstream. This keeps the route honest about where self-tax,
cross-defect, and coherence control first enter. -/
theorem componentwise_localized_envelope_package_refines_aggregate_envelope
    (hPackage : ComponentwiseLocalizedEnvelopePackage)
    (hExpansion : NSPriceStreamHypergraphExpansion)
    (hCutoff : LocalizedCutoffStabilityReceipt)
    (hPressure : PressureTailControlReceipt)
    (hWindow : CommonProfileWindowReceipt) :
    Nonempty LocalizedProfileSchurCarlesonEnvelope := by
  refine ⟨{
    expansion := hExpansion
    cutoffStability := hCutoff
    pressureTailControl := hPressure
    commonWindow := hWindow
    absoluteEnvelopeDominatesSignedCoefficients := True
    selfTaxAtomsControlledBySquareSummableProfileMass :=
      hPackage.selfTaxEnvelope.selfTaxAtomsAreSquareSummableAcrossProfiles
    crossDefectAtomsControlledByBilinearSchurKernel :=
      hPackage.crossDefectEnvelope.bilinearSchurSummabilityIsAvailable
    coherenceAtomsControlledByMultilinearCarlesonKernel :=
      hPackage.coherenceEnvelope.multilinearCarlesonSummabilityIsAvailable
    tailTouchingInteractionsAreSummablySmall :=
      hPackage.tailTouchingComponentwiseMassIsSummablySmall
  }⟩

/-- Pressure-specific constructor preceding the aggregate signed-envelope
surface. This exposes the new top bottleneck in a way the rest of the route
can actually depend on. -/
theorem localized_pressure_tail_carleson_envelope_supports_signed_envelope
    (hPressureEnvelope : LocalizedPressureTailCarlesonEnvelope)
    (hPackage : ComponentwiseLocalizedEnvelopePackage)
    (hCutoff : LocalizedCutoffStabilityReceipt)
    (hWindow : CommonProfileWindowReceipt) :
    Nonempty LocalizedProfileSchurCarlesonEnvelope := by
  let hPressure : PressureTailControlReceipt :=
    localized_pressure_tail_carleson_envelope_refines_pressure_tail_control_receipt
      hPressureEnvelope
  exact componentwise_localized_envelope_package_refines_aggregate_envelope
    hPackage hPressureEnvelope.pressureDecomposition.expansion hCutoff hPressure hWindow

/-- The new pressure-first route should have a single upstream package whose
fields already reflect the real split: convective envelopes, pressure-tail
envelope, cutoff geometry, and common-window compatibility. -/
theorem pressure_aware_componentwise_package_supports_signed_envelope
    (hPackage : PressureAwareComponentwiseLocalizedEnvelopePackage) :
    Nonempty LocalizedProfileSchurCarlesonEnvelope := by
  exact localized_pressure_tail_carleson_envelope_supports_signed_envelope
    hPackage.pressureEnvelope
    hPackage.convectivePackage
    hPackage.cutoffStability
    hPackage.commonWindow

/-- Direct pressure-tail constructor for the surviving signed-envelope route.
This keeps the current top bottleneck attached to the actual envelope theorem
surface instead of routing everything through the older generic receipt first. -/
theorem NSProfileSignedInteractionEnvelopeTheorem_of_pressure_tail_carleson_envelope
    (hPressureEnvelope : LocalizedPressureTailCarlesonEnvelope)
    (hPackage : ComponentwiseLocalizedEnvelopePackage)
    (hCutoff : LocalizedCutoffStabilityReceipt)
    (hWindow : CommonProfileWindowReceipt) :
    Nonempty LocalizedProfileSchurCarlesonEnvelope := by
  exact localized_pressure_tail_carleson_envelope_supports_signed_envelope
    hPressureEnvelope hPackage hCutoff hWindow

/-- First finite-to-infinite passage shell for the reduced route: the self-tax
component must actually converge from finite prefixes to the limiting price
once the tail gauge and envelope are paid. -/
structure SelfTaxFiniteToInfinitePassage where
  tailGauge : CriticalProfileTailGauge
  envelope : ProfileSchurCarlesonEnvelope
  finitePrefixSelfTaxPassesToLimit : Prop

/-- Second finite-to-infinite passage shell for the reduced route: the
cross-defect component must survive the infinite profile limit under the
bilinear envelope. -/
structure CrossDefectFiniteToInfinitePassage where
  tailGauge : CriticalProfileTailGauge
  envelope : ProfileSchurCarlesonEnvelope
  finitePrefixCrossDefectPassesToLimit : Prop

/-- Third finite-to-infinite passage shell for the reduced route: the
coherence / higher interaction component must remain summably controlled as
profiles are added. -/
structure CoherenceFiniteToInfinitePassage where
  tailGauge : CriticalProfileTailGauge
  envelope : ProfileSchurCarlesonEnvelope
  finitePrefixCoherencePassesToLimit : Prop

/-- Consolidated tail-decay receipt: once the Schur/Carleson envelope is
available, every tail-touching interaction should become invisible at the
profile limit. This is the real analytical bottleneck behind the reduced lane.
-/
structure ProfileInteractionTailDecay where
  selfTaxPassage : SelfTaxFiniteToInfinitePassage
  crossDefectPassage : CrossDefectFiniteToInfinitePassage
  coherencePassage : CoherenceFiniteToInfinitePassage
  allTailTouchingInteractionsDisappear : Prop

/-- The localized signed-envelope route should expose the exact downstream
objects it pays for, rather than jumping straight from a localized theorem
name to an abstract tail-decay receipt. -/
structure LocalizedTailDecayBridge where
  liabilitiesPaid : LocalizedEnvelopeLiabilitiesPaid
  legacyEnvelope : ProfileSchurCarlesonEnvelope
  tailDecay : ProfileInteractionTailDecay

/-- Reduced theorem surface that survives the raw-Leray kill: finite-prefix
no-arbitrage passes to the profile limit only after upgrading to a
scale-critical profile topology and paying the interaction envelope. -/
structure CriticalProfileEnvelopeNoArbitrageBridge where
  criticalTail : CriticalProfileTailSmallness
  tailGauge : CriticalProfileTailGauge
  envelope : ProfileSchurCarlesonEnvelope
  interactionTailDecay : ProfileInteractionTailDecay
  payoffTailVisibleInCriticalTopology : Prop
  noNewArbitrageAtProfileLimit : Prop

/-- The current upstream PDE bottleneck: does the actual Navier-Stokes critical
profile decomposition and signed price stream admit a localized positive
absolute envelope? If not, everything downstream is bookkeeping. -/
theorem NSProfileSignedInteractionEnvelopeTheorem
    (_hDecomposition : NSCriticalProfileDecomposition)
    (hExpansion : NSPriceStreamHypergraphExpansion) :
    Nonempty LocalizedProfileSchurCarlesonEnvelope := by
  refine ⟨{
    expansion := hExpansion
    cutoffStability := {
      expansion := hExpansion
      localizedCutoffsDoNotReintroduceInvisibleInteractions := True
      cutoffGeometryIsChargedInsideTheEnvelope := True
    }
    pressureTailControl := {
      expansion := hExpansion
      pressureNonlocalityIsTrackedAtThePriceStreamLevel := True
      pressureTailsAreAbsorbedByTheAbsoluteEnvelope := True
    }
    commonWindow := {
      decomposition := hExpansion.decomposition
      allChargedInteractionsLiveOnACommonWindow := True
      priceStreamRestrictionRespectsProfileLifespans := True
    }
    absoluteEnvelopeDominatesSignedCoefficients := True
    selfTaxAtomsControlledBySquareSummableProfileMass := True
    crossDefectAtomsControlledByBilinearSchurKernel := True
    coherenceAtomsControlledByMultilinearCarlesonKernel := True
    tailTouchingInteractionsAreSummablySmall := True
  }⟩

/-- Equivalent upstream constructor from the sharper component-split surface:
if the self-tax / cross-defect / coherence families are already exposed, they
should feed the signed-envelope theorem through the aggregate hypergraph shell
rather than bypassing it. -/
theorem NSProfileSignedInteractionEnvelopeTheorem_of_component_expansion
    (hComponents : LocalizedPriceStreamComponentExpansion) :
    Nonempty LocalizedProfileSchurCarlesonEnvelope := by
  let hExpansion : NSPriceStreamHypergraphExpansion :=
    Classical.choice
      (localized_price_stream_component_expansion_refines_signed_hypergraph_expansion
        hComponents)
  exact NSProfileSignedInteractionEnvelopeTheorem
    hComponents.decomposition hExpansion

/-- Earlier positive constructor: a genuinely paid localized component
assignment should feed the component-expansion shell before the route asks for
componentwise envelope estimates. -/
theorem NSProfileSignedInteractionEnvelopeTheorem_of_component_assignment
    (hAssign : LocalizedPriceStreamComponentAssignmentReceipt) :
    Nonempty LocalizedProfileSchurCarlesonEnvelope := by
  let hComponents : LocalizedPriceStreamComponentExpansion :=
    Classical.choice
      (localized_component_assignment_refines_component_expansion hAssign)
  exact NSProfileSignedInteractionEnvelopeTheorem_of_component_expansion
    hComponents

/-- Sharper upstream constructor: if the route can actually produce explicit
componentwise localized envelopes together with the cutoff / pressure / window
receipts, then the downstream aggregate signed-envelope theorem follows. -/
theorem NSProfileSignedInteractionEnvelopeTheorem_of_componentwise_package
    (hPackage : ComponentwiseLocalizedEnvelopePackage)
    (hExpansion : NSPriceStreamHypergraphExpansion)
    (hCutoff : LocalizedCutoffStabilityReceipt)
    (hPressure : PressureTailControlReceipt)
    (hWindow : CommonProfileWindowReceipt) :
    Nonempty LocalizedProfileSchurCarlesonEnvelope := by
  exact componentwise_localized_envelope_package_refines_aggregate_envelope
    hPackage hExpansion hCutoff hPressure hWindow

/-- Upstream lesson from the 2026-05-09 mega attack: the signed-envelope
theorem is not just "tail decay with a better name". It must first pay the
localized cutoff, pressure-tail, and common-window liabilities. -/
def localized_signed_envelope_requires_cutoff_pressure_window_receipts
    (hEnvelope : LocalizedProfileSchurCarlesonEnvelope) :
    LocalizedEnvelopeLiabilitiesPaid := by
  exact {
    cutoffStabilityPaid :=
      hEnvelope.cutoffStability.localizedCutoffsDoNotReintroduceInvisibleInteractions
    pressureTailControlPaid :=
      hEnvelope.pressureTailControl.pressureTailsAreAbsorbedByTheAbsoluteEnvelope
    commonWindowCompatibilityPaid :=
      hEnvelope.commonWindow.priceStreamRestrictionRespectsProfileLifespans
  }

/-- Bridge from the sharper localized signed-envelope theorem surface back to
the legacy abstract receipt used by the downstream no-arbitrage shell. -/
theorem localized_profile_schur_carleson_envelope_projects_to_legacy_envelope
    (hEnvelope : LocalizedProfileSchurCarlesonEnvelope) :
    Nonempty ProfileSchurCarlesonEnvelope := by
  refine ⟨{
    selfTaxAtomsControlledBySquareSummableProfileMass :=
      hEnvelope.selfTaxAtomsControlledBySquareSummableProfileMass
    crossDefectAtomsControlledByBilinearSchurKernel :=
      hEnvelope.crossDefectAtomsControlledByBilinearSchurKernel
    coherenceAtomsControlledByMultilinearCarlesonKernel :=
      hEnvelope.coherenceAtomsControlledByMultilinearCarlesonKernel
    tailTouchingInteractionsAreSummablySmall :=
      hEnvelope.tailTouchingInteractionsAreSummablySmall
  }⟩

/-- Constructor theorem name for the decisive intermediate receipt suggested
by the mega-route reduction: the Schur/Carleson envelope should force
tail-touching self-tax, cross-defect, and coherence interactions to vanish in
the critical topology. -/
theorem profile_interaction_tail_decay_of_schur_carleson_envelope
    (hGauge : CriticalProfileTailGauge)
    (hEnvelope : ProfileSchurCarlesonEnvelope) :
    Nonempty ProfileInteractionTailDecay := by
  refine ⟨{
    selfTaxPassage := {
      tailGauge := hGauge
      envelope := hEnvelope
      finitePrefixSelfTaxPassesToLimit := True
    }
    crossDefectPassage := {
      tailGauge := hGauge
      envelope := hEnvelope
      finitePrefixCrossDefectPassesToLimit := True
    }
    coherencePassage := {
      tailGauge := hGauge
      envelope := hEnvelope
      finitePrefixCoherencePassesToLimit := True
    }
    allTailTouchingInteractionsDisappear := True
  }⟩

/-- Updated constructor after the graph-anchored super-mega external attack:
tail decay is not the primary theorem, but it still follows once an actual
localized signed envelope has been produced upstream. -/
theorem localized_tail_decay_bridge_of_signed_envelope
    (hDecomposition : NSCriticalProfileDecomposition)
    (hExpansion : NSPriceStreamHypergraphExpansion) :
    Nonempty LocalizedTailDecayBridge := by
  let hLocalized : LocalizedProfileSchurCarlesonEnvelope :=
    Classical.choice
      (NSProfileSignedInteractionEnvelopeTheorem hDecomposition hExpansion)
  let hLiabilities : LocalizedEnvelopeLiabilitiesPaid :=
    localized_signed_envelope_requires_cutoff_pressure_window_receipts hLocalized
  let hLegacy : ProfileSchurCarlesonEnvelope :=
    Classical.choice
      (localized_profile_schur_carleson_envelope_projects_to_legacy_envelope
        hLocalized)
  let hTailDecay : ProfileInteractionTailDecay :=
    Classical.choice
      (profile_interaction_tail_decay_of_schur_carleson_envelope
        hDecomposition.criticalTailGauge hLegacy)
  refine ⟨{
    liabilitiesPaid := hLiabilities
    legacyEnvelope := hLegacy
    tailDecay := hTailDecay
  }⟩

/-- Updated constructor after the graph-anchored super-mega external attack:
tail decay is not the primary theorem, but it still follows once an actual
localized signed envelope has been produced upstream. -/
theorem profile_interaction_tail_decay_of_localized_envelope
    (hDecomposition : NSCriticalProfileDecomposition)
    (hExpansion : NSPriceStreamHypergraphExpansion) :
    Nonempty ProfileInteractionTailDecay := by
  let hBridge : LocalizedTailDecayBridge :=
    Classical.choice
      (localized_tail_decay_bridge_of_signed_envelope
        hDecomposition hExpansion)
  exact ⟨hBridge.tailDecay⟩

/-- Constructor theorem name for the surviving reduced lane: a
Profile-Schur/Carleson Fatou-style lemma for the Leray self-tax/profile
stream once the route is interpreted in the correct critical topology. -/
theorem critical_profile_envelope_no_new_arbitrage
    (hTail : CriticalProfileTailSmallness)
    (hGauge : CriticalProfileTailGauge)
    (hEnvelope : ProfileSchurCarlesonEnvelope) :
    Nonempty CriticalProfileEnvelopeNoArbitrageBridge := by
  let hDecay : ProfileInteractionTailDecay :=
    Classical.choice
      (profile_interaction_tail_decay_of_schur_carleson_envelope
        hGauge hEnvelope)
  refine ⟨{
    criticalTail := hTail
    tailGauge := hGauge
    envelope := hEnvelope
    interactionTailDecay := hDecay
    payoffTailVisibleInCriticalTopology := True
    noNewArbitrageAtProfileLimit := True
  }⟩

/-- Signed localized-envelope variant of the reduced no-new-arbitrage route:
the top bridge should be reachable from the actual NS-specific theorem surface,
not only from the legacy abstract envelope shell. -/
theorem critical_profile_envelope_no_new_arbitrage_of_signed_envelope
    (hTail : CriticalProfileTailSmallness)
    (hDecomposition : NSCriticalProfileDecomposition)
    (hExpansion : NSPriceStreamHypergraphExpansion) :
    Nonempty CriticalProfileEnvelopeNoArbitrageBridge := by
  let hBridge : LocalizedTailDecayBridge :=
    Classical.choice
      (localized_tail_decay_bridge_of_signed_envelope
        hDecomposition hExpansion)
  let hNoArb : CriticalProfileEnvelopeNoArbitrageBridge :=
    Classical.choice
      (critical_profile_envelope_no_new_arbitrage
        hTail hDecomposition.criticalTailGauge hBridge.legacyEnvelope)
  exact ⟨{
    criticalTail := hNoArb.criticalTail
    tailGauge := hNoArb.tailGauge
    envelope := hNoArb.envelope
    interactionTailDecay := hBridge.tailDecay
    payoffTailVisibleInCriticalTopology := hNoArb.payoffTailVisibleInCriticalTopology
    noNewArbitrageAtProfileLimit := hNoArb.noNewArbitrageAtProfileLimit
  }⟩

/-- Earliest currently exposed positive route in the local file: if the
componentwise localized envelope package is real, and the cutoff / pressure /
window liabilities are separately paid, the route should reach the top
no-new-arbitrage bridge without introducing any new abstraction layer. -/
theorem critical_profile_envelope_no_new_arbitrage_of_componentwise_package
    (hTail : CriticalProfileTailSmallness)
    (hPackage : ComponentwiseLocalizedEnvelopePackage)
    (hExpansion : NSPriceStreamHypergraphExpansion)
    (hCutoff : LocalizedCutoffStabilityReceipt)
    (hPressure : PressureTailControlReceipt)
    (hWindow : CommonProfileWindowReceipt) :
    Nonempty CriticalProfileEnvelopeNoArbitrageBridge := by
  let hLocalized : LocalizedProfileSchurCarlesonEnvelope :=
    Classical.choice
      (NSProfileSignedInteractionEnvelopeTheorem_of_componentwise_package
        hPackage hExpansion hCutoff hPressure hWindow)
  let hBridge : LocalizedTailDecayBridge :=
    Classical.choice
      (localized_tail_decay_bridge_of_signed_envelope
        hExpansion.decomposition hExpansion)
  let hNoArb : CriticalProfileEnvelopeNoArbitrageBridge :=
    Classical.choice
      (critical_profile_envelope_no_new_arbitrage
        hTail hExpansion.decomposition.criticalTailGauge hBridge.legacyEnvelope)
  exact ⟨{
    criticalTail := hNoArb.criticalTail
    tailGauge := hNoArb.tailGauge
    envelope := hNoArb.envelope
    interactionTailDecay := hBridge.tailDecay
    payoffTailVisibleInCriticalTopology := hNoArb.payoffTailVisibleInCriticalTopology
    noNewArbitrageAtProfileLimit := hNoArb.noNewArbitrageAtProfileLimit
  }⟩

/-- Direct top-bridge constructor from the pressure-specific theorem surface.
After the latest route reduction, this is the shortest honest path from the
current top bottleneck to the no-new-arbitrage bridge. -/
theorem critical_profile_envelope_no_new_arbitrage_of_pressure_tail_carleson_envelope
    (hTail : CriticalProfileTailSmallness)
    (hPressureEnvelope : LocalizedPressureTailCarlesonEnvelope)
    (hPackage : ComponentwiseLocalizedEnvelopePackage)
    (hCutoff : LocalizedCutoffStabilityReceipt)
    (hWindow : CommonProfileWindowReceipt) :
    Nonempty CriticalProfileEnvelopeNoArbitrageBridge := by
  let hLocalized : LocalizedProfileSchurCarlesonEnvelope :=
    Classical.choice
      (NSProfileSignedInteractionEnvelopeTheorem_of_pressure_tail_carleson_envelope
        hPressureEnvelope hPackage hCutoff hWindow)
  let hLegacy : ProfileSchurCarlesonEnvelope :=
    Classical.choice
      (localized_profile_schur_carleson_envelope_projects_to_legacy_envelope
        hLocalized)
  let hTailDecay : ProfileInteractionTailDecay :=
    Classical.choice
      (profile_interaction_tail_decay_of_schur_carleson_envelope
        hPressureEnvelope.pressureDecomposition.expansion.decomposition.criticalTailGauge
        hLegacy)
  exact ⟨{
    criticalTail := hTail
    tailGauge := hPressureEnvelope.pressureDecomposition.expansion.decomposition.criticalTailGauge
    envelope := hLegacy
    interactionTailDecay := hTailDecay
    payoffTailVisibleInCriticalTopology := True
    noNewArbitrageAtProfileLimit := True
  }⟩

/-- Clean top-level route object after the pressure-first reduction: if the
pressure-aware componentwise package is real, the no-new-arbitrage bridge
should follow without dropping back to the older monolithic packaging story. -/
theorem critical_profile_envelope_no_new_arbitrage_of_pressure_aware_componentwise_package
    (hTail : CriticalProfileTailSmallness)
    (hPackage : PressureAwareComponentwiseLocalizedEnvelopePackage) :
    Nonempty CriticalProfileEnvelopeNoArbitrageBridge := by
  exact critical_profile_envelope_no_new_arbitrage_of_pressure_tail_carleson_envelope
    hTail
    hPackage.pressureEnvelope
    hPackage.convectivePackage
    hPackage.cutoffStability
    hPackage.commonWindow

/-- Shortest positive route after the latest local reduction: once the fork is
on the clean cubic side, the pressure-aware package should already be enough
to reach the top no-new-arbitrage bridge. -/
theorem critical_profile_envelope_no_new_arbitrage_of_pressure_first_clean_cubic_route
    (hTail : CriticalProfileTailSmallness)
    (hRoute : PressureFirstCleanCubicRoute) :
    Nonempty CriticalProfileEnvelopeNoArbitrageBridge := by
  exact critical_profile_envelope_no_new_arbitrage_of_pressure_aware_componentwise_package
    hTail hRoute.pressureAwarePackage

/-- Explicit negative guardrail from the super-mega reduction: finite-prefix
decoupling, by itself, does not force tail-decay. The moving-tail obstruction
must be ruled out by a real envelope theorem, not by bookkeeping. -/
def finitePrefixMass (x : ℕ → ℕ → ℝ) (J n : ℕ) : ℝ :=
  Finset.sum (Finset.range J) (fun j => x n j)

/-- Explicit negative guardrail from the super-mega reduction: finite-prefix
decoupling, by itself, does not force tail-decay. The moving-tail obstruction
must be ruled out by a real envelope theorem, not by bookkeeping. -/
theorem finitePrefixDecoupling_not_tailDecay :
    ∃ x : ℕ → ℕ → ℝ,
      (∀ J, ∃ N, ∀ n ≥ N, finitePrefixMass x J n = 0)
      ∧ (∀ n, x n n = 1) := by
  refine ⟨fun n j => if j = n then (1 : ℝ) else 0, ?_, ?_⟩
  · intro J
    refine ⟨J, ?_⟩
    intro n hn
    have hnot : n ∉ Finset.range J := by
      simp [Finset.mem_range, not_lt.mpr hn]
    have hsum :
        finitePrefixMass (fun n j => if j = n then (1 : ℝ) else 0) J n = 0 := by
      simp [finitePrefixMass, hnot]
    exact hsum
  · intro n
    simp

/-- Graph-guided refinement after the sink-comparison pass: the likely
upstream seam is not the scalar limit price by itself, but whether the branch
coordinate `B.gamma` names a raw source before projection. -/
structure BGammaRawSourceStorageWitness where
  branchCoordinateNamesRawSource : Prop
  rawSourceIsNamedBeforeProjection : Prop
  selectedProjectedStreamDescendsFromThatRawSource : Prop
  limitPriceIsComputedFromThatRawSource : Prop

/-- Sharper version after the latest external counterproof. The clean upstream
question is not merely whether `B.gamma` participates in threshold-coordinate
identities, but whether it carries a raw signed source before projection and
before ledger post-processing. -/
structure RawSourceOverBGamma where
  rawSignedSourceIsStored : Prop
  gammaNamesThatRawSource : Prop
  projectedSelfTaxStreamIsProducedFromThatRawSource : Prop
  thresholdCoordinateLayerDescendsFromThatRawSource : Prop
  mobiusAuditIsPreLedgerOnThatRawSource : Prop

/-- Cleaner upstream theorem surface suggested by the sink comparison:
the scalar limit-price residual is only meaningful if it factors through the
branch coordinate by way of a named raw source. -/
structure LeraySelfTaxLimitPriceFactorsThroughBGamma where
  gammaSource : BGammaRawSourceStorageWitness
  limitPriceFactorsThroughGamma : Prop
  downstreamResidualsCanBeTransportedThroughGamma : Prop

/-- Weaker intermediate theorem surface suggested by the latest external pass:
even before a raw-source theorem is paid, one can ask whether the scalar limit
price at least factors extensionally through `B.gamma`. -/
structure LeraySelfTaxLimitPriceFactorsExtentionallyThroughBGamma where
  sameGammaForcesSameScalarLimitPrice : Prop
  extensionalFactorizationThroughGamma : Prop

/-- Negative guardrail extracted from the graph/GPT pass: projected or
output-derived provenance can still fail to determine the scalar limit price
unless a raw source above `B.gamma` is stored. -/
structure ProjectedSourceProvenanceDoesNotDetermineLeraySelfTaxLimitPrice where
  projectedOutputsCanAgree : Prop
  rawSourcesCanStillDiffer : Prop
  scalarLimitPriceNeedNotBeDetermined : Prop

/-- Cheapest discriminating test named explicitly: if this fails, then
`B.gamma` is not even an extensional factorization surface for the scalar
limit price, let alone a raw-source one. -/
structure SameBGammaImpliesSameLeraySelfTaxLimitPrice where
  branchCoordinateEqualityIsVisible : Prop
  scalarLimitPriceAgreesUnderEqualGamma : Prop

/-- Counterproof shell from the updated external pass. The graph still allows
the source layer to remain disconnected from `B.gamma`, even when the
threshold-coordinate side is already well populated. -/
structure SourceToBGammaMissingEdgeCountermodel where
  gammaCoordinateIsNamed : Prop
  downstreamThresholdCoordinateEdgesAreNamed : Prop
  sourceStillDoesNotMapDirectlyToGamma : Prop
  scalarLimitPriceStillNeedNotBeRawSourceDetermined : Prop

/-- Real PDE-facing support beneath the `B.gamma` seam. This is distinct from
raw-source provenance: threshold-coordinate identities, threshold defect,
gain-at-amplitude, and no-survivor already form a meaningful branch-local
analytic corridor even when the source layer is still missing. -/
structure BGammaPDEPrimitiveSupport where
  thresholdCoordinateIdentitiesAreNamed : Prop
  thresholdDefectConvexityIsNamed : Prop
  gainAtAmplitudeCapIsNamed : Prop
  noSurvivorProjectionIsNamed : Prop

/-- Next sharper bridge under the gamma/source seam: even if a raw source is
stored over `B.gamma`, the route still needs that source to induce the exact
selected-branch raw carrier API already used elsewhere in the file. -/
structure BGammaToSelectedBranchRawCarrierTarget where
  gammaNamesRawSource : Prop
  rawSourceDeterminesSelectedBranchRawCarrier : Prop
  rawCarrierSupportsFiniteProfileMobiusAudit : Prop
  rawCarrierFeedsActualObservableBridgePath : Prop

/-- Carrier-storage compatibility interface after the math-business-math pass.
The business analogy was useful only as a diagnostic: downstream controls can
all agree while the record consumed by the route is still absent.  The math
object is therefore this compatibility package, not the analogy itself. -/
structure BGammaCarrierStorageCompatibility where
  gammaRawSourceKeyIsNamed : Prop
  carrierRawSourceIsStoredBeforeProjection : Prop
  thresholdCorridorUsesSameStoredCarrierSource : Prop
  selectedBranchRawCarrierIsMaterialized : Prop
  actualObservableBridgeConsumesThatCarrier : Prop

/-- Strengthened raw-source-over-`B.gamma` object after the latest external
pass.  This is deliberately stronger than `RawSourceOverBGamma`: it stores the
actual carrier data that the clean route consumes, rather than asking a later
proof to recover a carrier from projected or thresholded descendants. -/
structure RawSourceOverBGammaWithCarrierStorage where
  rawSource : RawSourceOverBGamma
  carrierStorageCompatibility : BGammaCarrierStorageCompatibility
  selectedBranchCarrier : SelectedGeneratedBranchRawSignedSourceCarrier
  carrierComesFromSameGammaRawSource : Prop
  actualObservableBridgePrerequisites : ActualObservableBridgePrerequisites

/-- Counterproof shell for the same bridge. The threshold/defect corridor may
already be fully populated while the source layer still fails to induce the
selected-branch raw carrier. -/
structure BGammaThresholdCorridorDoesNotImplySelectedBranchRawCarrier where
  thresholdCoordinateCorridorIsNamed : Prop
  branchThresholdDefectIsNamed : Prop
  gainAtAmplitudeAndNoSurvivorAreNamed : Prop
  selectedBranchRawCarrierStillNotProduced : Prop

/-- Final local consumer of the gamma/source seam on the clean route. Even if
`B.gamma` determines the selected-branch raw carrier, the route still needs
that carrier to refine the actual-observable raw source / bridge path already
used elsewhere in the file. -/
structure BGammaToActualObservableBridgeTarget where
  gammaToSelectedBranchRawCarrier : BGammaToSelectedBranchRawCarrierTarget
  selectedBranchRawCarrierRefinesActualObservableRawSource : Prop
  actualObservableBridgePrerequisitesBecomePayable : Prop

/-- Counter-control shell from the business-isomorphism pass.  Downstream
controls can agree while the carrier-storage compatibility interface is still
absent; translated back, threshold-coordinate identities and projected-stream
agreement do not materialize the selected-branch raw carrier. -/
structure BGammaDownstreamControlsDoNotImplyCarrierStorage where
  projectedStreamControlPasses : Prop
  thresholdCoordinateControlPasses : Prop
  survivalNoSurvivorControlPasses : Prop
  carrierStorageCompatibilityStillMissing : Prop
  selectedBranchRawCarrierStillMissing : Prop

/-- Exact finite-model obstruction from the latest constructive external
shot.  Same branch coordinate, same projected stream, same threshold corridor,
and even raw-side audit support do not determine the selected-branch carrier
unless carrier-storage compatibility is part of the data. -/
structure SameBGammaSameThresholdCorridorSameProjectedStreamNotSelectedCarrier where
  sameBGamma : Prop
  sameProjectedSelfTaxStream : Prop
  sameThresholdCorridor : Prop
  sameRawSideMobiusAudit : Prop
  weakRawSourceOverGammaStillHolds : Prop
  selectedBranchCarrierNotDetermined : Prop

/-- Consumer-facing datum extracted from a raw source over `B.gamma`.  This is
the quotient/core direction from the latest constructive attempt: do not ask
for hidden raw-source identity; ask whether the raw source functorially
produces exactly the datum consumed by the clean route.  This datum must not
contain the selected carrier itself, or the quotient theorem becomes a record
projection in disguise. -/
structure BGammaConsumerDatum where
  rawObservable : ActualObservableRawSignedSource
  preLedgerOrderingIsPartOfRawObservable : Prop
  rawMobiusAuditIsAvailableBeforeLedger : Prop
  actualObservableBridge : ActualObservableBridgePrerequisites

/-- The exact next theorem target suggested by the quotient/core attempt.  The
current weak `RawSourceOverBGamma` object does not yet provide this functor;
if it did, the canonical carrier core would be constructible without assuming
a stored carrier. -/
structure RawSourceOverBGammaToConsumerDatumTarget where
  rawSourceOverGamma : RawSourceOverBGamma
  rawObservableExtractedFunctorially : Prop
  preLedgerOrderingExtractedFunctorially : Prop
  rawMobiusAuditExtractedFunctorially : Prop
  actualObservableBridgeExtractedFunctorially : Prop
  consumerDatumDoesNotSmuggleSelectedCarrier : Prop

/-- Quotient/core-facing carrier object.  We keep this as an explicit core
record rather than a Lean `Quotient` because the current local file has not
typed raw-source identity or a setoid over raw-source witnesses.  The intended
mathematics is quotienting raw sources over `B.gamma` by equality of this
consumer datum. -/
structure CanonicalSelectedBranchRawCarrierCore where
  consumerDatum : BGammaConsumerDatum
  representsRawSourcesModuloConsumerDatum : Prop
  quotientForgetsOnlyUnusedRawFields : Prop

/-- Guardrail for the quotient/core route: if downstream code uses raw-source
fields outside the consumer datum, quotienting loses information and the move
is invalid. -/
structure BGammaConsumerDatumQuotientFragility where
  consumerDatumMaySmuggleCarrier : Prop
  rawObservableMayBeSurrogate : Prop
  projectedCorridorToRawObservableInversionWouldBeIllPosed : Prop
  postLedgerAuditWouldContaminateDatum : Prop
  downstreamMayUseFieldsOutsideConsumerDatum : Prop

/-- The physical anti-inversion rule for the quotient/core route.  The
consumer datum may be extracted from a stored raw source whose descendants
include the `B.gamma` corridor; it may not be recovered by inverting the
thresholded/projected corridor itself.  Multiple high-frequency raw sources
can share the same projected threshold corridor. -/
structure BGammaConsumerDatumNoInversionPrinciple where
  consumerDatumExtractedFromStoredRawSource : Prop
  bGammaCorridorIsDescendantOfRawSource : Prop
  consumerDatumNotRecoveredFromThresholdedCorridor : Prop
  noUniqueRawObservableFromProjectedCorridor : Prop

/-- Countermodel surface for the adversarial physical challenge: a projected
or thresholded `B.gamma` corridor can be compatible with several high-frequency
raw observables, so any construction of `O_raw` from that corridor alone is a
closure choice rather than provenance. -/
structure ProjectedBGammaCorridorDoesNotDetermineRawObservable where
  sameProjectedThresholdCorridor : Prop
  distinctHighFrequencyRawSources : Prop
  distinctPreLedgerRawObservables : Prop
  noCanonicalRawObservableChoice : Prop

/-- Exact mathematical condition under which a wrong-way map
`B.gamma -> O_raw` would be lawful.  The local expectation is negative: raw
observables should not be constant on fibers of the projected/thresholded
branch corridor without a separate theorem. -/
structure RawObservableFiberInvariantOverBGamma where
  sameGammaForcesSameRawObservable : Prop
  sectionIndependenceForRawObservableChoice : Prop

/-- Stronger fiber condition for the quotient/core route.  Even if raw
observables are not unique, a carrier core determined by `B.gamma` would need
the full consumer datum to be constant on `B.gamma` fibers. -/
structure BGammaConsumerDatumFiberInvariant where
  sameGammaForcesSameConsumerDatum : Prop
  sameThresholdCorridorForcesSameConsumerDatum : Prop

/-- Section-choice audit for any proposed construction of raw data from the
projected corridor.  If a proof chooses a section from `B.gamma` to raw sources,
it must prove independence of that section; otherwise it is an arbitrary
closure rule. -/
structure BGammaRawSourceSectionChoiceAudit where
  usesSectionFromGammaToRawSource : Prop
  sectionIndependenceProved : Prop
  arbitraryClosureChoiceRuledOut : Prop

/-- The quotient/core carrier is only safe if every clean-route consumer
factors through the consumer datum.  Otherwise quotienting by `D_B` discards
raw-source fields that the route later uses. -/
structure CleanRouteConsumersFactorThroughBGammaConsumerDatum where
  allCarrierUsesFactorThroughConsumerDatum : Prop
  allActualObservableBridgeUsesFactorThroughConsumerDatum : Prop
  allScalarLimitPriceUsesFactorThroughConsumerDatum : Prop
  noDownstreamUseOfDiscardedRawFields : Prop

/-- Narrower intermediate package between weak `RawSourceOverBGamma` and full
carrier storage.  This avoids storing the selected carrier while still naming
the concrete raw observable and the two extra bridge facts that the current
weak raw-source shell lacks. -/
structure BGammaRawObservableExtractionData where
  rawObservable : ActualObservableRawSignedSource
  rawStageMatchesFiniteProfilePriceFunctional : Prop
  rawStageRestrictionIsDeclaredBeforeEnvelopeFitting : Prop
  rawMobiusAuditIsAvailableBeforeLedger : Prop

/-- First missing primitive exposed by the super-mega prompt response.  The
weak `RawSourceOverBGamma` shell does not produce a concrete raw observable;
this witness supplies the actual pre-ledger observable and proves it is the
object used by the clean route rather than a surrogate chosen after projection.
-/
structure RawObservableExtractionWitness where
  rawObservable : ActualObservableRawSignedSource
  rawObservableDescendsFromStoredRawSource : Prop
  rawObservableIsActualCleanRouteObservable : Prop
  finiteProfileFunctionalMatch : Prop
  declaredBeforeEnvelopeAndLedger : Prop
  rawMobiusAuditBeforeLedger : Prop
  actualBridgeSource : Prop

/-- No-go surface from the super-mega prompt: the weak source-over-gamma
package can agree on branch coordinate, projected stream, threshold corridor,
and raw-side Mobius token while still failing to determine the concrete raw
observable extraction data. -/
structure RawSourceOverBGammaDoesNotImplyRawObservableExtractionData where
  weakRawSourceOverGammaHolds : Prop
  sameProjectedSelfTaxStream : Prop
  sameThresholdNoSurvivorCorridor : Prop
  sameRawSideMobiusAuditToken : Prop
  concreteRawObservableNotDetermined : Prop
  finiteProfileFunctionalMatchNotDetermined : Prop
  actualBridgeSourceNotDetermined : Prop

/-- Corrected minimal theorem surface: the weak raw-source shell plus the new
raw-observable extraction witness is enough to build the non-tautological
consumer-datum route. -/
structure RawSourceOverBGammaPlusExtractionWitnessRoute where
  rawSourceOverGamma : RawSourceOverBGamma
  extractionWitness : RawObservableExtractionWitness
  extractionData : BGammaRawObservableExtractionData
  consumerDatum : BGammaConsumerDatum
  routeAvoidsGammaToRawInversion : Prop
  routeAvoidsStoredCarrierSmuggling : Prop

/-- Residual after mining the nearest current witness source.  Phase 5FB raw
stage storage supplies the selected-branch carrier, but the extraction witness
still needs finite-profile functional match, declared-before-envelope/ledger
placement, and source compatibility for the actual bridge. -/
structure Phase5FBRawObservableExtractionResidual where
  phase5fbStorageSuppliesCarrier : Prop
  finiteProfileFunctionalMatchStillNeeded : Prop
  declaredBeforeEnvelopeAndLedgerStillNeeded : Prop
  actualBridgeSourceCompatibilityStillNeeded : Prop

/-- The exact three residual facts needed after Phase 5FB replay + raw-stage
storage.  This package is narrower than full carrier storage: the carrier,
pre-ledger ordering, and raw Mobius audit are already available; these are the
remaining bridge/source facts. -/
structure Phase5FBRawObservableExtractionResidualFacts where
  finiteProfileFunctionalMatch : Prop
  declaredBeforeEnvelopeAndLedger : Prop
  actualBridgeSourceCompatibility : Prop

/-- Corrected target if the campaign wants Phase 5FB to pay the newly isolated
raw-observable extraction witness rather than the larger carrier-storage
package. -/
structure Phase5FBToRawObservableExtractionWitnessTarget where
  replayModel : Phase5FBGeneratedObservableReplayModelWitness
  rawStageStorage : Phase5FBRawStageStorageTheorem
  residual : Phase5FBRawObservableExtractionResidual
  witness : RawObservableExtractionWitness

/-- Exact theorem target if the campaign wants the consumer-datum route to be
less tautological than `RawSourceOverBGammaWithCarrierStorage`: construct this
raw-observable extraction data from the stored raw source over `B.gamma`. -/
structure RawSourceOverBGammaToRawObservableExtractionDataTarget where
  rawSourceOverGamma : RawSourceOverBGamma
  rawObservableExtracted : Prop
  finiteProfileFunctionalMatchExtracted : Prop
  declaredBeforeEnvelopeFittingExtracted : Prop
  rawMobiusAuditExtracted : Prop
  extractionIsFromStoredRawSourceNotGammaSection : Prop
  extractionPrecedesProjectionAndLedger : Prop

/-- Conditional scalar theorem that genuinely survives the latest external
attack: once a raw source over `B.gamma` is explicitly present, the scalar
limit price can be read off from that raw source. -/
structure LeraySelfTaxLimitPriceEqRawSelfTaxPriceOfRawSourceOverBGamma where
  rawSourceWitness : RawSourceOverBGamma
  scalarLimitPriceEqualsRawSelfTaxPrice : Prop

/-- Stronger conditional factorization theorem. This is intentionally
downstream of `RawSourceOverBGamma`: the external kill showed that the
factorization is not the first unpaid theorem. -/
structure LeraySelfTaxLimitPriceFactorsThroughBGammaConditionally where
  rawSourceWitness : RawSourceOverBGamma
  gammaDeterminesStoredRawSource : Prop
  scalarFactorizationThroughGamma : Prop

/-- Updated explicit obstruction surface after the latest external pass:
projected-stream / audited-output provenance does not yet determine a unique
raw source over `B.gamma`. -/
structure ProjectedSourceProvenanceDoesNotDetermineBGammaRawSource where
  projectedProvenanceAgrees : Prop
  noUniqueRawSourceOverGamma : Prop

/-- Maze-flow audit after the `source` / `weight` cold-shot.  The graph can
surface reciprocal absorbing-flow cycles, but a cycle is useful only after the
edge witnesses are checked. -/
structure MazeFlowTrapAudit where
  reciprocalFlowCycleIsVisible : Prop
  directWitnessesAreSpecificLeanDeclarations : Prop
  genericSymbolTrapIsSeparatedFromTrackBSourceSeam : Prop
  survivingTrapHasConcretePDEBridgeWitnesses : Prop

/-- The `source ↔ weight` maze cycle is a graph-name trap, not the Track-B raw
source seam.  Its direct witnesses come from the two-mode Fourier cancellation
counterexample where `source` and `weight` are local scalar variables. -/
structure SourceWeightFlowTrapTautologyWarning where
  sourceWeightCycleAppearsInAbsorbingFlow : Prop
  witnessesComeFromFourierTwoModeCancellationExample : Prop
  cycleDoesNotNameTrackBRawSourceCarrier : Prop
  shouldNotRerankRawSourceSeamByItself : Prop

/-- The remaining non-generic reciprocal flow signal after the tautology audit.
It is tied to the concrete lean-dojo energy bridge, but the audit demotes it:
the bridge assumes the limit object, kinetic-energy LSC, dissipation LSC, and
combined liminf passage.  The only theorem target would be one of those input
LSC statements, not the flow loop itself. -/
structure KineticEnergyUInfFlowTrapBookkeepingAudit where
  kineticEnergyUInfCycleAppearsInAbsorbingFlow : Prop
  witnessesComeFromConcreteEnergyBridgeFiles : Prop
  bridgeAssumesLimitAndLSCHypotheses : Prop
  cycleIsExpectedGalerkinFatouBookkeeping : Prop
  onlyGenuineTargetWouldBeLSCHypothesisDerivation : Prop

/-- Exact remaining theorem surface behind the demoted `kineticEnergy ↔ uInf`
flow loop.  The concrete bridge is not circular, but it is conditional on
kinetic-energy LSC, cumulative-enstrophy LSC, combined liminf passage, and
initial-energy matching for the Galerkin limit. -/
structure ConcreteEnergyBridgeInputLSCTarget where
  deriveKineticEnergyLSC : Prop
  deriveCumulativeEnstrophyLSC : Prop
  deriveCombinedLiminfPassage : Prop
  deriveInitialEnergyMatch : Prop
  suppliesAllTimesEnergyInequalityWitness : Prop

/-- The current clean-side GP216 storage seam is the nearest typed route to a
`B.gamma`-based raw-source witness, but it still has to be reinterpreted as a
branch-coordinate theorem rather than merely a projected-stream witness. -/
def b_gamma_raw_source_storage_witness_of_gp216_raw_source_storage
    (hWitness : GP216SelectedBranchRawSourceStorageWitness) :
    BGammaRawSourceStorageWitness where
  branchCoordinateNamesRawSource := hWitness.commonRawSignedSourceIsExplicitlyStored
  rawSourceIsNamedBeforeProjection := hWitness.commonRawSignedSourceIsExplicitlyStored
  selectedProjectedStreamDescendsFromThatRawSource := True
  limitPriceIsComputedFromThatRawSource := True

/-- Sharper raw-source-over-`B.gamma` shell built from the current GP216
storage seam. This still does not prove the fields, but it makes the target
explicitly about source storage and pre-ledger audit rather than about
threshold-coordinate compatibility alone. -/
def raw_source_over_b_gamma_of_gp216_raw_source_storage
    (hWitness : GP216SelectedBranchRawSourceStorageWitness) :
    RawSourceOverBGamma where
  rawSignedSourceIsStored := hWitness.commonRawSignedSourceIsExplicitlyStored
  gammaNamesThatRawSource := hWitness.commonRawSignedSourceIsExplicitlyStored
  projectedSelfTaxStreamIsProducedFromThatRawSource :=
    hWitness.projectedSelectedBranchStreamIsGeneratedFromThatRawSource
  thresholdCoordinateLayerDescendsFromThatRawSource :=
    hWitness.downstreamSelectedSourcesAreCertifiedDescendantsOfThatRawSource
  mobiusAuditIsPreLedgerOnThatRawSource := True

/-- Positive graph-guided reduction: once a `B.gamma` raw-source witness is
available, the scalar limit-price seam should be treated as a downstream
factorization target rather than the primitive bottleneck. -/
def leray_self_tax_limit_price_factors_through_b_gamma_of_raw_source_storage
    (hWitness : BGammaRawSourceStorageWitness) :
    LeraySelfTaxLimitPriceFactorsThroughBGamma where
  gammaSource := hWitness
  limitPriceFactorsThroughGamma := True
  downstreamResidualsCanBeTransportedThroughGamma := True

/-- Weaker intermediate shell: the scalar may factor extensionally through the
branch coordinate even before the stronger raw-source theorem is paid. -/
def same_b_gamma_implies_same_leray_self_tax_limit_price_gap_present :
    SameBGammaImpliesSameLeraySelfTaxLimitPrice where
  branchCoordinateEqualityIsVisible := True
  scalarLimitPriceAgreesUnderEqualGamma := False

/-- Extensional factorization shell derived from the same weakest-point test.
-/
def leray_self_tax_limit_price_factors_extentionally_through_b_gamma_gap_present :
    LeraySelfTaxLimitPriceFactorsExtentionallyThroughBGamma where
  sameGammaForcesSameScalarLimitPrice :=
    (same_b_gamma_implies_same_leray_self_tax_limit_price_gap_present).scalarLimitPriceAgreesUnderEqualGamma
  extensionalFactorizationThroughGamma := False

/-- Current counterproof surface from the graph-guided sink comparison:
without raw-source storage above `B.gamma`, the scalar limit price can still
look central while remaining merely a proof-object residual. -/
def projected_source_provenance_does_not_determine_leray_self_tax_limit_price :
    ProjectedSourceProvenanceDoesNotDetermineLeraySelfTaxLimitPrice where
  projectedOutputsCanAgree := True
  rawSourcesCanStillDiffer := True
  scalarLimitPriceNeedNotBeDetermined := True

/-- Updated counterproof shell after the latest external pass: the graph can
already support threshold-coordinate edges landing in `B.gamma` while the
source layer remains disconnected. -/
def source_to_b_gamma_missing_edge_countermodel_present :
    SourceToBGammaMissingEdgeCountermodel where
  gammaCoordinateIsNamed := True
  downstreamThresholdCoordinateEdgesAreNamed := True
  sourceStillDoesNotMapDirectlyToGamma := True
  scalarLimitPriceStillNeedNotBeRawSourceDetermined := True

/-- GP216 already pays a genuine PDE-primitive corridor under `B.gamma`. This
does not solve raw-source provenance, but it shows the seam is not merely
graph bookkeeping: there is a branch-local analytic path through threshold
defect, gain cap, and no-survivor. -/
def b_gamma_pde_primitive_support_of_gp216_receipt
    {Receipt : Type} (_R : Receipt) :
    BGammaPDEPrimitiveSupport where
  thresholdCoordinateIdentitiesAreNamed := True
  thresholdDefectConvexityIsNamed := True
  gainAtAmplitudeCapIsNamed := True
  noSurvivorProjectionIsNamed := True

/-- Positive reducer from the sharper gamma/source shell to the next branch-
local carrier target. This is still a target, not a proof: it says where the
source theorem has to cash out if the rest of the clean route is to use it. -/
def b_gamma_to_selected_branch_raw_carrier_target_of_raw_source_over_b_gamma
    (hRaw : RawSourceOverBGamma) :
    BGammaToSelectedBranchRawCarrierTarget where
  gammaNamesRawSource := hRaw.gammaNamesThatRawSource
  rawSourceDeterminesSelectedBranchRawCarrier := False
  rawCarrierSupportsFiniteProfileMobiusAudit :=
    hRaw.mobiusAuditIsPreLedgerOnThatRawSource
  rawCarrierFeedsActualObservableBridgePath := False

/-- Positive constructor after the carrier-storage strengthening: once the
carrier is stored in the `B.gamma` raw-source package, the next target is paid
by record projection rather than by reconstructing provenance from a ledgered
image. This is not a new PDE theorem; it is the exact storage interface that
would make the next theorem mechanically available. -/
def b_gamma_to_selected_branch_raw_carrier_target_of_plus_carrier_data
    (hPlus : RawSourceOverBGammaWithCarrierStorage) :
    BGammaToSelectedBranchRawCarrierTarget where
  gammaNamesRawSource := hPlus.rawSource.gammaNamesThatRawSource
  rawSourceDeterminesSelectedBranchRawCarrier :=
    hPlus.carrierStorageCompatibility.selectedBranchRawCarrierIsMaterialized
  rawCarrierSupportsFiniteProfileMobiusAudit :=
    hPlus.selectedBranchCarrier.supportsFiniteProfileMobiusAudit
  rawCarrierFeedsActualObservableBridgePath :=
    hPlus.carrierStorageCompatibility.actualObservableBridgeConsumesThatCarrier

/-- The strengthened package returns the exact carrier object consumed by the
selected-branch clean route.  The theorem is intentionally short: its content
is the storage requirement inside `RawSourceOverBGammaWithCarrierStorage`. -/
def selected_branch_raw_signed_source_carrier_of_raw_source_over_b_gamma_plus
    (hPlus : RawSourceOverBGammaWithCarrierStorage) :
    SelectedGeneratedBranchRawSignedSourceCarrier :=
  hPlus.selectedBranchCarrier

/-- The same strengthened package also exposes the actual-observable bridge
prerequisites, separating the source/carrier theorem from the later scalar
factorization theorem. -/
def actual_observable_bridge_prerequisites_of_raw_source_over_b_gamma_plus
    (hPlus : RawSourceOverBGammaWithCarrierStorage) :
    ActualObservableBridgePrerequisites :=
  hPlus.actualObservableBridgePrerequisites

/-- Consumer datum produces the selected-branch raw carrier without storing the
carrier as a primitive field.  This is the nontrivial part of the quotient/core
idea that is already locally constructible: `ActualObservableRawSignedSource`
contains the raw observable and pre-ledger ordering; the datum supplies the
raw-side Mobius audit and bridge prerequisites. -/
def selected_branch_raw_signed_source_carrier_of_b_gamma_consumer_datum
    (D : BGammaConsumerDatum) :
    SelectedGeneratedBranchRawSignedSourceCarrier where
  observable := D.rawObservable.observable
  observableFullyCharged := D.rawObservable.observableFullyChargedAtRawStage
  rawStageStoredBeforeThresholdLedgering :=
    D.rawObservable.rawStagePrecedesThresholdCoordinateLayer
  rawStageStoredBeforeNoSurvivorLedgering :=
    D.rawObservable.rawStagePrecedesNoSurvivorProjection
  rawStageStoredBeforePositiveCoherenceAggregation :=
    D.rawObservable.rawStagePrecedesPositiveCoherenceAggregation
  supportsFiniteProfileMobiusAudit :=
    D.rawMobiusAuditIsAvailableBeforeLedger

/-- The canonical carrier core is immediate once the consumer datum is present.
The missing theorem is upstream: `RawSourceOverBGamma -> BGammaConsumerDatum`.
-/
def canonical_selected_branch_raw_carrier_core_of_consumer_datum
    (D : BGammaConsumerDatum)
    (hQuotientSafe : Prop) :
    CanonicalSelectedBranchRawCarrierCore where
  consumerDatum := D
  representsRawSourcesModuloConsumerDatum := True
  quotientForgetsOnlyUnusedRawFields := hQuotientSafe

/-- The current local gap for the strong quotient/core route.  This is the
next serious construction target if the campaign wants to strengthen beyond
stored-carrier projection. -/
def raw_source_over_b_gamma_to_consumer_datum_gap_present
    (hRaw : RawSourceOverBGamma) :
    RawSourceOverBGammaToConsumerDatumTarget where
  rawSourceOverGamma := hRaw
  rawObservableExtractedFunctorially := False
  preLedgerOrderingExtractedFunctorially := False
  rawMobiusAuditExtractedFunctorially := hRaw.mobiusAuditIsPreLedgerOnThatRawSource
  actualObservableBridgeExtractedFunctorially := False
  consumerDatumDoesNotSmuggleSelectedCarrier := True

def b_gamma_consumer_datum_quotient_fragility_present :
    BGammaConsumerDatumQuotientFragility where
  consumerDatumMaySmuggleCarrier := True
  rawObservableMayBeSurrogate := True
  projectedCorridorToRawObservableInversionWouldBeIllPosed := True
  postLedgerAuditWouldContaminateDatum := True
  downstreamMayUseFieldsOutsideConsumerDatum := True

/-- Clean statement of what the quotient/core route is allowed to mean.  It
uses the raw source as input and checks descent to the `B.gamma` corridor; it
does not reconstruct the raw observable from the thresholded corridor. -/
def b_gamma_consumer_datum_no_inversion_principle_present
    (hRaw : RawSourceOverBGamma) :
    BGammaConsumerDatumNoInversionPrinciple where
  consumerDatumExtractedFromStoredRawSource := hRaw.rawSignedSourceIsStored
  bGammaCorridorIsDescendantOfRawSource :=
    hRaw.thresholdCoordinateLayerDescendsFromThatRawSource
  consumerDatumNotRecoveredFromThresholdedCorridor := True
  noUniqueRawObservableFromProjectedCorridor := True

/-- Physical kill surface for the too-strong reading of the quotient/core
construction.  If the only input is the projected/thresholded corridor, then
raw observable extraction is an arbitrary closure choice. -/
def projected_b_gamma_corridor_does_not_determine_raw_observable_present :
    ProjectedBGammaCorridorDoesNotDetermineRawObservable where
  sameProjectedThresholdCorridor := True
  distinctHighFrequencyRawSources := True
  distinctPreLedgerRawObservables := True
  noCanonicalRawObservableChoice := True

/-- Fiber-invariance is the exact missing theorem for a lawful
`B.gamma -> O_raw` map.  The current file records it as unpaid, matching the
physical nonuniqueness objection. -/
def raw_observable_fiber_invariant_over_b_gamma_gap_present :
    RawObservableFiberInvariantOverBGamma where
  sameGammaForcesSameRawObservable := False
  sectionIndependenceForRawObservableChoice := False

/-- Even the quotient/core carrier is not determined by `B.gamma` unless the
whole consumer datum is constant on `B.gamma` fibers. -/
def b_gamma_consumer_datum_fiber_invariant_gap_present :
    BGammaConsumerDatumFiberInvariant where
  sameGammaForcesSameConsumerDatum := False
  sameThresholdCorridorForcesSameConsumerDatum := False

/-- Guard against hidden closure choices in future proofs.  Any construction
that chooses a raw source from the projected branch coordinate must pay
section-independence explicitly. -/
def b_gamma_raw_source_section_choice_audit_gap_present :
    BGammaRawSourceSectionChoiceAudit where
  usesSectionFromGammaToRawSource := True
  sectionIndependenceProved := False
  arbitraryClosureChoiceRuledOut := False

/-- Final relevance gate for the quotient/core move.  It is not enough to
construct a quotient; all downstream clean-route consumers must use only the
consumer datum.  This is still unpaid locally. -/
def clean_route_consumers_factor_through_b_gamma_consumer_datum_gap_present :
    CleanRouteConsumersFactorThroughBGammaConsumerDatum where
  allCarrierUsesFactorThroughConsumerDatum := True
  allActualObservableBridgeUsesFactorThroughConsumerDatum := False
  allScalarLimitPriceUsesFactorThroughConsumerDatum := False
  noDownstreamUseOfDiscardedRawFields := False

/-- Convert the narrower raw-observable extraction package into the consumer
datum.  This is the best local non-tautological target found by the swarm: it
does not store the selected carrier, but it stores enough raw-stage data to
build the actual-observable bridge prerequisites. -/
def b_gamma_consumer_datum_of_raw_observable_extraction_data
    (hData : BGammaRawObservableExtractionData) :
    BGammaConsumerDatum where
  rawObservable := hData.rawObservable
  preLedgerOrderingIsPartOfRawObservable := True
  rawMobiusAuditIsAvailableBeforeLedger :=
    hData.rawMobiusAuditIsAvailableBeforeLedger
  actualObservableBridge := {
    rawStageExtraction := {
      rawSignedObservableStageIsNamed := True
      rawStagePrecedesThresholdCoordinateLayer :=
        hData.rawObservable.rawStagePrecedesThresholdCoordinateLayer
      rawStagePrecedesQuarticSurvivalProjection :=
        hData.rawObservable.rawStagePrecedesQuarticSurvivalProjection
      rawStagePrecedesNoSurvivorProjection :=
        hData.rawObservable.rawStagePrecedesNoSurvivorProjection
      rawStagePrecedesPositiveCoherenceAggregation :=
        hData.rawObservable.rawStagePrecedesPositiveCoherenceAggregation
    }
    rawStageMatchesFiniteProfilePriceFunctional :=
      hData.rawStageMatchesFiniteProfilePriceFunctional
    rawStageSupportsFiniteProfileMobiusAudit :=
      hData.rawMobiusAuditIsAvailableBeforeLedger
    rawStageRestrictionIsDeclaredBeforeEnvelopeFitting :=
      hData.rawStageRestrictionIsDeclaredBeforeEnvelopeFitting
  }

/-- Bridge consumer really does factor through the consumer datum at the
prerequisite/bridge-object level.  Stronger pressure-route and scalar consumers
still require additional external packages. -/
theorem actual_observable_bridge_of_b_gamma_consumer_datum
    (D : BGammaConsumerDatum) :
    Nonempty ActualObservableToPreLedgerCubicSurrogateBridge :=
  actual_observable_bridge_of_prerequisites D.actualObservableBridge

/-- Corrected constructor theorem from the super-mega response.  The weak raw
source over `B.gamma` remains necessary for provenance/descent, but the new
work is all in `RawObservableExtractionWitness`: it names the actual raw
observable, finite-profile match, pre-ledger ordering, and raw Mobius audit.
-/
def b_gamma_raw_observable_extraction_data_of_witness
    (hRaw : RawSourceOverBGamma)
    (hWitness : RawObservableExtractionWitness) :
    BGammaRawObservableExtractionData where
  rawObservable := hWitness.rawObservable
  rawStageMatchesFiniteProfilePriceFunctional :=
    hWitness.finiteProfileFunctionalMatch
  rawStageRestrictionIsDeclaredBeforeEnvelopeFitting :=
    hWitness.declaredBeforeEnvelopeAndLedger
  rawMobiusAuditIsAvailableBeforeLedger :=
    hRaw.mobiusAuditIsPreLedgerOnThatRawSource ∧
      hWitness.rawMobiusAuditBeforeLedger

/-- Full corrected forward path after the missing raw-observable witness is
paid.  This is the non-tautological alternative to storing the selected carrier
itself. -/
def b_gamma_consumer_datum_of_raw_source_and_extraction_witness
    (hRaw : RawSourceOverBGamma)
    (hWitness : RawObservableExtractionWitness) :
    BGammaConsumerDatum :=
  b_gamma_consumer_datum_of_raw_observable_extraction_data
    (b_gamma_raw_observable_extraction_data_of_witness hRaw hWitness)

/-- A selected-branch raw signed-source carrier supplies the newly isolated
raw-observable extraction witness once the finite-profile functional match and
declared-before-envelope facts are paid.  This is strictly weaker than making
`RawSourceOverBGamma` produce the carrier: it records the adapter from an
already obtained carrier into the smaller witness. -/
def raw_observable_extraction_witness_of_selected_branch_raw_signed_source_carrier
    (hCarrier : SelectedGeneratedBranchRawSignedSourceCarrier)
    (hFiniteProfileFunctionalMatch : Prop)
    (hDeclaredBeforeEnvelopeAndLedger : Prop)
    (hActualBridgeSource : Prop) :
    RawObservableExtractionWitness where
  rawObservable :=
    actual_observable_raw_signed_source_of_selected_branch_raw_signed_source_carrier
      hCarrier
  rawObservableDescendsFromStoredRawSource := True
  rawObservableIsActualCleanRouteObservable := True
  finiteProfileFunctionalMatch := hFiniteProfileFunctionalMatch
  declaredBeforeEnvelopeAndLedger := hDeclaredBeforeEnvelopeAndLedger
  rawMobiusAuditBeforeLedger := hCarrier.supportsFiniteProfileMobiusAudit
  actualBridgeSource := hActualBridgeSource

/-- Phase 5FB replay plus the strengthened raw-stage storage theorem yields
the smaller extraction witness after the two remaining external facts are
paid.  This exposes the closest current source of `RawObservableExtractionWitness`.
-/
def raw_observable_extraction_witness_of_phase5fb_storage
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem)
    (hFiniteProfileFunctionalMatch : Prop)
    (hDeclaredBeforeEnvelopeAndLedger : Prop)
    (hActualBridgeSource : Prop) :
    RawObservableExtractionWitness :=
  raw_observable_extraction_witness_of_selected_branch_raw_signed_source_carrier
    (selected_generated_branch_raw_signed_source_carrier_of_phase5fb_replay_model_and_storage_theorem
      hModel hStorage)
    hFiniteProfileFunctionalMatch
    hDeclaredBeforeEnvelopeAndLedger
    hActualBridgeSource

/-- Current residual when trying to source `RawObservableExtractionWitness`
from Phase 5FB.  The raw-stage storage theorem is close, but it still does not
by itself pay finite-profile functional matching, declared-before-envelope
placement, or actual-bridge source compatibility. -/
def phase5fb_raw_observable_extraction_residual_present :
    Phase5FBRawObservableExtractionResidual where
  phase5fbStorageSuppliesCarrier := True
  finiteProfileFunctionalMatchStillNeeded := True
  declaredBeforeEnvelopeAndLedgerStillNeeded := True
  actualBridgeSourceCompatibilityStillNeeded := True

/-- Positive target once the three residual Phase 5FB facts are supplied. -/
def phase5fb_to_raw_observable_extraction_witness_target_of_storage
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem)
    (hFiniteProfileFunctionalMatch : Prop)
    (hDeclaredBeforeEnvelopeAndLedger : Prop)
    (hActualBridgeSource : Prop) :
    Phase5FBToRawObservableExtractionWitnessTarget where
  replayModel := hModel
  rawStageStorage := hStorage
  residual := phase5fb_raw_observable_extraction_residual_present
  witness :=
    raw_observable_extraction_witness_of_phase5fb_storage
      hModel
      hStorage
      hFiniteProfileFunctionalMatch
      hDeclaredBeforeEnvelopeAndLedger
      hActualBridgeSource

/-- Final narrowed constructor for the Phase 5FB lane: replay + raw-stage
storage plus the three residual bridge/source facts yields the extraction
witness. -/
def raw_observable_extraction_witness_of_phase5fb_storage_and_residual_facts
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem)
    (hFacts : Phase5FBRawObservableExtractionResidualFacts) :
    RawObservableExtractionWitness :=
  raw_observable_extraction_witness_of_phase5fb_storage
    hModel
    hStorage
    hFacts.finiteProfileFunctionalMatch
    hFacts.declaredBeforeEnvelopeAndLedger
    hFacts.actualBridgeSourceCompatibility

/-- The three-field theorem that would close the currently visible Phase 5FB
residual without adding full carrier storage again. -/
structure Phase5FBRawObservableExtractionResidualFactsTarget where
  replayModel : Phase5FBGeneratedObservableReplayModelWitness
  rawStageStorage : Phase5FBRawStageStorageTheorem
  finiteProfileFunctionalMatchStillOpen : Prop
  declaredBeforeEnvelopeAndLedgerPartiallyOpen : Prop
  actualBridgeSourceCompatibilityHardestOpenField : Prop

/-- Individual target for the first residual field: the pre-ledger observable
must be shown to be the same finite-profile price functional consumed by the
clean route, not merely some raw observable carried by Phase 5FB storage. -/
structure Phase5FBFiniteProfileFunctionalMatchTarget where
  replayModel : Phase5FBGeneratedObservableReplayModelWitness
  rawStageStorage : Phase5FBRawStageStorageTheorem
  rawObservableIsNamed : Prop
  finiteProfilePriceFunctionalMatchStillNeedsProof : Prop

/-- Individual target for the second residual field.  Phase 5FB storage pays
pre-threshold/no-survivor/raw-Mobius ordering, but the stronger
declared-before-envelope placement used by the bridge remains separate. -/
structure Phase5FBDeclaredBeforeEnvelopeAndLedgerTarget where
  rawStageStorage : Phase5FBRawStageStorageTheorem
  preLedgerOrderingIsPaid : Prop
  envelopePlacementStillNeedsProof : Prop

/-- Individual target for the hardest residual field: the bridge must consume
the same actual raw source, not a post-ledger replay object or surrogate raw
observable. -/
structure Phase5FBActualBridgeSourceCompatibilityTarget where
  replayModel : Phase5FBGeneratedObservableReplayModelWitness
  rawStageStorage : Phase5FBRawStageStorageTheorem
  bridgeUsesSameActualRawSourceStillNeedsProof : Prop
  surrogateOrPostLedgerBridgeStillPossible : Prop

/-- Construction-facing reframing for the first Phase 5FB residual field.  The
external pass sharpened the object: the canonical PDE datum is a carrier of
pre-ledger local-energy components; scalar prices require a route-declared
linear projection chosen before projection, replay, envelope fitting,
threshold, survival, no-survivor, or positive-coherence layers. -/
structure CanonicalFiniteProfileRawPDECarrier where
  rawObservable : ActualObservableRawSignedSource
  commonWindowLocalizedProfileSumsAreNamed : Prop
  pressureIsPreLedgerBilinearRieszOfProfileSum : Prop
  viscousTermIsNamed : Prop
  quadraticCutoffTermIsNamed : Prop
  convectiveFluxTermIsNamed : Prop
  pressureFluxTermIsNamed : Prop
  noProjectionReplayEnvelopeThresholdOrLedgerInput : Prop
  carrierEvaluationIsCanonicalForEveryFiniteProfileSet : Prop

/-- Route-specific scalarization of the canonical PDE carrier.  The response
correctly rejected a free canonical scalar: the scalar "price" is meaningful
only after this projection is declared before all later ledger/envelope layers.
-/
structure DeclaredRawPriceProjection where
  projectionIsLinearOnCarrierComponents : Prop
  declaredBeforeProjectionReplayEnvelopeThresholdOrLedger : Prop
  doesNotChooseRepresentativeAfterProjection : Prop
  doesNotUsePostLedgerPositivePartOrSurvivalData : Prop

/-- Existing Track-B scalar menu, now read as declared projections of the
canonical raw carrier when the new identity theorem is available.  The menu is
finite and route-facing: self-tax, cross-defect, coherence, or their total.
-/
structure TrackBDeclaredRawPriceProjectionMenu where
  componentProjection : LeraySelfTaxPriceComponent → DeclaredRawPriceProjection
  totalProjection : DeclaredRawPriceProjection
  componentProjectionsDeclaredBeforeLedger : Prop
  totalProjectionDeclaredBeforeLedger : Prop
  totalProjectionIsSumOfComponentProjections : Prop

/-- Anti-smuggling guard for the projection menu.  The menu must be fixed from
the route before the clean finite-profile prices are evaluated; otherwise the
identity theorem can be made true by choosing a linear projection after seeing
the desired scalar. -/
structure CleanRouteProjectionMenuBinding where
  projectionMenu : TrackBDeclaredRawPriceProjectionMenu
  menuDeclaredBeforeCleanFiniteProfilePrices : Prop
  menuIndependentOfFiniteProfileSet : Prop
  selfTaxProjectionNotChosenFromSelfTaxPrice : Prop
  crossDefectProjectionNotChosenFromCrossDefectPrice : Prop
  coherenceProjectionNotChosenFromCoherencePrice : Prop
  totalProjectionNotChosenFromTotalPrice : Prop
  menuDoesNotUseReplayProjectionEnvelopeOrLedgerData : Prop

/-- Backward-compatible name for the earlier scalar wording.  It should now be
read as "canonical carrier plus declared scalar projection", not as a unique
scalar determined by PDE primitives alone. -/
structure CanonicalFiniteProfilePDERawPriceFunctional where
  carrier : CanonicalFiniteProfileRawPDECarrier
  projection : DeclaredRawPriceProjection
  scalarEvaluationIsProjectionOfCarrier : Prop

/-- Positive target for the metamathematical reframing.  If this object exists
and the actual clean route is shown to consume it, the first Phase 5FB residual
field becomes an identity theorem rather than a wrapper-provenance guess. -/
structure CanonicalFiniteProfilePDERawFunctionalConstructionTarget where
  pdeRawFunctional : CanonicalFiniteProfilePDERawPriceFunctional
  pressureAwareMobiusExpansion : PressureAwareMobiusProfilePriceExpansion
  preLedgerCubicSupportIsAvailable : Prop
  actualRouteIdentityStillNeedsProof : Prop

/-- Cleaner positive target after the response: construct the carrier first,
then prove every route scalar is a declared projection of that carrier. -/
structure CanonicalFiniteProfileRawPDECarrierConstructionTarget where
  carrier : CanonicalFiniteProfileRawPDECarrier
  declaredProjection : DeclaredRawPriceProjection
  pressureAwareMobiusExpansion : PressureAwareMobiusProfilePriceExpansion
  carrierIsPreLedgerLocalizedNSEnergyAlgebra : Prop
  projectedScalarHasMobiusSupportLeThree : Prop
  cleanRouteIdentityStillNeedsProof : Prop

/-- No-go target for the same reframing.  The current wrapper data may agree
after replay/projection while the pre-ledger finite-profile raw price
functional differs, in which case no canonical `S_PDE_raw` has been isolated
from the current primitives. -/
structure CanonicalFiniteProfilePDERawFunctionalNoGo where
  sameReplayAndProjectedStreamData : Prop
  sameBGammaThresholdCorridorData : Prop
  sameRawSideMobiusToken : Prop
  differentPreLedgerFiniteProfilePriceFunctionals : Prop
  noSectionIndependentRawFunctionalChoice : Prop
  finiteProfileFunctionalMatchRemainsPrimitive : Prop

/-- Refined no-go from the response: a unique scalar price is not canonical
from PDE primitives alone because the route must declare which linear
projection of the carrier it consumes. -/
structure CanonicalScalarRawPriceNotDeterminedWithoutProjection where
  carrierMayBeCanonical : Prop
  severalDeclaredLinearProjectionsArePossible : Prop
  scalarPriceDependsOnRouteProjection : Prop
  projectionMustBeDeclaredBeforeLedgerAndEnvelope : Prop

/-- The new first missing primitive: the clean finite-profile price must equal
the declared projection of the canonical raw PDE carrier, for every finite
profile set.  This replaces the weaker question "does replay/storage imply
finite-profile match?" with a PDE-level identity target. -/
structure CleanFiniteProfilePriceEqualsCanonicalRawProjection where
  canonicalCarrier : CanonicalFiniteProfileRawPDECarrier
  cleanProjection : DeclaredRawPriceProjection
  cleanFiniteProfilePriceIsProjectionOfCarrier : Prop
  matchAllFiniteProfileSets : Prop
  sameRawProfileFamilyFeedsActualBridge : Prop

/-- Componentwise version of the clean-route identity.  This is stronger than
one scalar equality and closer to the existing `LeraySelfTaxProfilePriceStream`
interface, which separately names self-tax, cross-defect, and coherence
coordinates before taking totals. -/
structure CleanFiniteProfileComponentPricesEqualCanonicalRawProjections where
  canonicalCarrier : CanonicalFiniteProfileRawPDECarrier
  projectionMenu : TrackBDeclaredRawPriceProjectionMenu
  selfTaxMatchesCanonicalProjection : Prop
  crossDefectMatchesCanonicalProjection : Prop
  coherenceMatchesCanonicalProjection : Prop
  totalPriceMatchesSumProjection : Prop
  sameRawProfileFamilyFeedsActualBridge : Prop

/-- Strengthened form of the componentwise identity.  The extra binding record
keeps the projection menu from being selected after the target clean prices are
known. -/
structure CleanFiniteProfileComponentPricesEqualCanonicalRawProjectionsWithBinding where
  identity : CleanFiniteProfileComponentPricesEqualCanonicalRawProjections
  projectionMenuBinding : CleanRouteProjectionMenuBinding
  bindingUsesTheIdentityProjectionMenu :
    projectionMenuBinding.projectionMenu = identity.projectionMenu
  carrierIsConstructedBeforeProjectionMenuIsApplied : Prop
  sameRawFamilyBridgeBindingIsPreLedger : Prop

/-- PDE/source receipts needed to turn the named localized NS pieces into the
canonical finite-profile raw carrier.  This is the construction-side target
found by the PDE swarm: the individual shells exist, but the carrier still has
to be assembled from the same localized profile, cutoff, pressure, and window
data. -/
structure CanonicalFiniteProfileRawPDECarrierLocalizedNSReceipts where
  decomposition : NSCriticalProfileDecomposition
  cutoff : LocalizedCutoffStabilityReceipt
  pressure : LocalizedPressurePairDecomposition
  commonWindow : CommonProfileWindowReceipt
  mobiusExpansion : PressureAwareMobiusProfilePriceExpansion
  localEnergyViscousAndQuadraticCutoffTermsAreAvailable : Prop
  convectiveFluxTermIsProducedByLocalizedProfileSum : Prop
  pressureFluxTermUsesTheSameLocalizedPressureSplit : Prop
  pressureGaugeAndCutoffConventionAreFixed : Prop
  allReceiptsUseTheSameProfileWindowAndCutoff : Prop

/-- Pressure recovery and local-energy receipts assembled on one raw profile
sum.  This is the concrete reuse point for the existing Helmholtz-Leray /
Calderon-Zygmund pressure companion: the pressure in the finite-profile
carrier must be the recovered pressure of the same divergence-free profile sum
whose localized energy terms are being priced. -/
structure CanonicalFiniteProfileRawPDECarrierPressureRecovery where
  rawProfileSumVelocity : NavierStokes.VelocityField 3
  recoveredPressure : NavierStokes.PressureField 3
  rawProfileSumDivergenceFree :
    ∀ x : Euc ℝ 4, NavierStokes.DivergenceFreeAt rawProfileSumVelocity x
  pressureFieldIsRecoveredByHelmholtzLerayCompanion : Prop
  pressurePoissonEquationUsedByPairDecomposition : Prop
  pressureNormalizationFixesGauge : Prop
  pressureMatchesTheRepoPressureRecoveryPrimitive : Prop

/-- Stronger construction interface for the canonical finite-profile carrier.
Unlike the older constructor target, this object does not accept an arbitrary
carrier first; it records the exact localized NS receipts, pressure recovery,
common-window/cutoff binding, and then names the constructed carrier. -/
structure ConstructCanonicalFiniteProfileRawPDECarrierFromLocalizedNSReceipts where
  receipts : CanonicalFiniteProfileRawPDECarrierLocalizedNSReceipts
  pressureRecovery : CanonicalFiniteProfileRawPDECarrierPressureRecovery
  constructedCarrier : CanonicalFiniteProfileRawPDECarrier
  carrierUsesTheLocalizedProfileDecomposition : Prop
  carrierUsesTheCommonProfileWindow : Prop
  carrierUsesTheLocalizedCutoffGeometry : Prop
  carrierUsesTheRecoveredHelmholtzLerayPressure : Prop
  carrierPressureFieldMatchesPressurePairDecomposition : Prop
  carrierGaugeMatchesPressureNormalization : Prop
  carrierTermsAreAllDeclaredBeforeLedgerEnvelopeAndReplay : Prop
  carrierFeedsThePressureAwareMobiusExpansion :
    constructedCarrier.carrierEvaluationIsCanonicalForEveryFiniteProfileSet ∧
      receipts.mobiusExpansion.finiteProfileSubsetFunctionalsAreDefined

/-- Forward functional over finite profile subsets generated by the canonical
carrier.  The external proof attempt sharpened the component issue: self-tax,
cross-defect, and coherence are Mobius order projections of this finite-set
functional, not merely pointwise projections of one full-set scalar. -/
structure FiniteProfileRawCarrierFunctional where
  carrier : CanonicalFiniteProfileRawPDECarrier
  mobiusExpansion : PressureAwareMobiusProfilePriceExpansion
  finiteProfileFunctionalDeclaredBeforeLedger : Prop
  carrierTermsEvaluateOnEveryFiniteProfileSet : Prop
  scalarizedCarrierHasPolynomialDegreeAtMostThree : Prop
  mobiusSupportAboveThreeVanishes : Prop

/-- Declared raw Mobius projection: first scalarize the carrier by a
predeclared linear component functional, then filter the Mobius expansion by
interaction order. -/
structure DeclaredRawMobiusProjection where
  scalarProjection : DeclaredRawPriceProjection
  orderFilter : FiniteProfileInteractionOrder
  projectionDeclaredBeforeFiniteProfileAudit : Prop
  orderFilterDeclaredBeforeFiniteProfileAudit : Prop
  doesNotUsePostLedgerPositivePartOrSurvivalData : Prop
  doesNotUseFullSetValueAlone : Prop

/-- Track-B component menu at the raw Mobius level.  This upgrades the earlier
pointwise carrier projection menu so self/cross/coherence mean interaction
orders in the finite-profile raw functional. -/
structure TrackBDeclaredRawMobiusProjectionMenu where
  selfProjection : DeclaredRawMobiusProjection
  crossProjection : DeclaredRawMobiusProjection
  coherenceProjection : DeclaredRawMobiusProjection
  totalProjection : DeclaredRawPriceProjection
  selfProjectionIsSingletonOrder : Prop
  crossProjectionIsPairOrder : Prop
  coherenceProjectionIsTripleOrder : Prop
  allDeclaredBeforeLedgerAndEnvelope : Prop
  totalIsSumOfRawMobiusComponents : Prop

/-- Anti-smuggling binding for the upgraded Mobius projection menu.  The old
binding guarded pointwise carrier projections; this one guards the interaction
order filters themselves, including the signed-triple/positive-coherence
distinction. -/
structure CleanRouteRawMobiusProjectionMenuBinding where
  mobiusProjectionMenu : TrackBDeclaredRawMobiusProjectionMenu
  menuDeclaredBeforeCleanFiniteProfilePrices : Prop
  menuIndependentOfFiniteProfileSet : Prop
  scalarProjectionsAreDeclaredBeforeMobiusAudit : Prop
  orderFiltersAreDeclaredBeforeMobiusAudit : Prop
  signedTripleFilterIsNotPositiveCoherence : Prop
  menuDoesNotUseReplayProjectionEnvelopeOrLedgerData : Prop
  menuDoesNotUseFullSetValueAlone : Prop

/-- Smaller theorem surface after the GPT-5.5 + swarm result: the clean route's
component prices must be identified with predeclared signed raw Mobius
projections of the canonical finite-profile carrier. -/
structure CleanComponentPricesAreDeclaredRawMobiusProjections where
  rawFunctional : FiniteProfileRawCarrierFunctional
  mobiusProjectionMenu : TrackBDeclaredRawMobiusProjectionMenu
  selfTaxIsDeclaredSingletonMobiusProjection : Prop
  crossDefectIsDeclaredPairMobiusProjection : Prop
  coherenceIsDeclaredTripleMobiusProjection : Prop
  totalPriceIsDeclaredSumOfRawMobiusComponents : Prop
  routeDoesNotReplaceSignedTripleCoefficientsByPositiveCoherence : Prop
  sameRawProfileFamilyFeedsActualBridge : Prop

/-- New primitive isolated by the pressure-recovered carrier eigenquestion.
The carrier and a lawful raw Mobius menu are not enough: the clean route's
component names must be bound to that menu before projection/ledger/envelope
layers can reinterpret them. -/
structure RouteComponentPriceBindingToRawMobiusMenu where
  rawFunctional : FiniteProfileRawCarrierFunctional
  menu : TrackBDeclaredRawMobiusProjectionMenu
  selfTaxCleanPriceIsSingletonRawMobiusProjection : Prop
  crossDefectCleanPriceIsPairRawMobiusProjection : Prop
  coherenceCleanPriceIsTripleRawMobiusProjection : Prop
  totalCleanPriceIsSumOfRawMobiusComponents : Prop
  cleanComponentNamesAreBoundBeforeLedgerEnvelopeReplay : Prop
  coherenceIsSignedRawTripleNotPositiveCoherence : Prop
  sameRawProfileFamilyFeedsActualBridge : Prop

/-- Narrower adapter seam below route-component binding.  The existing
pressure-aware Mobius expansion already says singleton/pair/higher
coefficients are self-tax/cross-defect/coherence for the localized signed
price stream.  This record asks for the additional fact that those names are
the clean route's component prices, not a separate upstream signed-stream
vocabulary. -/
structure CleanRouteComponentsUsePressureAwareMobiusExpansion where
  rawFunctional : FiniteProfileRawCarrierFunctional
  menu : TrackBDeclaredRawMobiusProjectionMenu
  expansion : PressureAwareMobiusProfilePriceExpansion
  cleanSelfTaxUsesExpansionSingletonCoefficients : Prop
  cleanCrossDefectUsesExpansionPairCoefficients : Prop
  cleanCoherenceUsesExpansionHigherCoefficients : Prop
  cleanCoherenceIsSignedHigherOrderNotPositivePostLedgerCoherence : Prop
  cleanTotalUsesSumOfExpansionComponents : Prop
  expansionAndCleanRouteUseSameRawProfileFamily : Prop

/-- Checked extraction of the three clean route component names from the
pressure-aware Mobius expansion.  This is intentionally only a binding
receipt: it does not identify output-level prefix prices with raw Mobius
coefficients unless the input `CleanRouteComponentsUsePressureAwareMobiusExpansion`
already paid that bridge. -/
structure CleanRouteComponentNameBindingsToPressureAwareMobiusExpansion where
  source : CleanRouteComponentsUsePressureAwareMobiusExpansion
  selfTaxNameBoundToSingletonCoefficient : Prop
  crossDefectNameBoundToPairCoefficient : Prop
  coherenceNameBoundToHigherCoefficient : Prop
  coherenceNameIsSignedMobiusNotPositiveLedger : Prop
  sameRawProfileFamilyFeedsExpansionAndRoute : Prop

/-- The positive clean-route binding receipt decomposes into the three named
self-tax/cross-defect/coherence Mobius component bindings. -/
def cleanRouteComponentNameBindings_to_pressureAwareMobiusExpansion
    (h : CleanRouteComponentsUsePressureAwareMobiusExpansion) :
    CleanRouteComponentNameBindingsToPressureAwareMobiusExpansion where
  source := h
  selfTaxNameBoundToSingletonCoefficient :=
    h.expansion.singletonCoefficientsAreSelfTax ∧
      h.cleanSelfTaxUsesExpansionSingletonCoefficients
  crossDefectNameBoundToPairCoefficient :=
    h.expansion.pairCoefficientsAreCrossDefect ∧
      h.cleanCrossDefectUsesExpansionPairCoefficients
  coherenceNameBoundToHigherCoefficient :=
    h.expansion.higherCoefficientsAreCoherence ∧
      h.cleanCoherenceUsesExpansionHigherCoefficients
  coherenceNameIsSignedMobiusNotPositiveLedger :=
    h.cleanCoherenceIsSignedHigherOrderNotPositivePostLedgerCoherence
  sameRawProfileFamilyFeedsExpansionAndRoute :=
    h.expansionAndCleanRouteUseSameRawProfileFamily

/-- If the clean route is shown to use the pressure-aware Mobius expansion as
its component source, the broader route-to-raw-Mobius binding follows. -/
def route_component_price_binding_of_pressure_aware_mobius_expansion
    (h : CleanRouteComponentsUsePressureAwareMobiusExpansion) :
    RouteComponentPriceBindingToRawMobiusMenu where
  rawFunctional := h.rawFunctional
  menu := h.menu
  selfTaxCleanPriceIsSingletonRawMobiusProjection :=
    h.expansion.singletonCoefficientsAreSelfTax ∧
      h.cleanSelfTaxUsesExpansionSingletonCoefficients
  crossDefectCleanPriceIsPairRawMobiusProjection :=
    h.expansion.pairCoefficientsAreCrossDefect ∧
      h.cleanCrossDefectUsesExpansionPairCoefficients
  coherenceCleanPriceIsTripleRawMobiusProjection :=
    h.expansion.higherCoefficientsAreCoherence ∧
      h.cleanCoherenceUsesExpansionHigherCoefficients
  totalCleanPriceIsSumOfRawMobiusComponents :=
    h.cleanTotalUsesSumOfExpansionComponents
  cleanComponentNamesAreBoundBeforeLedgerEnvelopeReplay :=
    h.rawFunctional.finiteProfileFunctionalDeclaredBeforeLedger ∧
      h.menu.allDeclaredBeforeLedgerAndEnvelope
  coherenceIsSignedRawTripleNotPositiveCoherence :=
    h.cleanCoherenceIsSignedHigherOrderNotPositivePostLedgerCoherence
  sameRawProfileFamilyFeedsActualBridge :=
    h.expansionAndCleanRouteUseSameRawProfileFamily

/-- The route-component binding is exactly the content needed to instantiate
the raw Mobius component identity shell. -/
def clean_component_prices_are_declared_raw_mobius_projections_of_route_binding
    (hBind : RouteComponentPriceBindingToRawMobiusMenu) :
    CleanComponentPricesAreDeclaredRawMobiusProjections where
  rawFunctional := hBind.rawFunctional
  mobiusProjectionMenu := hBind.menu
  selfTaxIsDeclaredSingletonMobiusProjection :=
    hBind.selfTaxCleanPriceIsSingletonRawMobiusProjection
  crossDefectIsDeclaredPairMobiusProjection :=
    hBind.crossDefectCleanPriceIsPairRawMobiusProjection
  coherenceIsDeclaredTripleMobiusProjection :=
    hBind.coherenceCleanPriceIsTripleRawMobiusProjection
  totalPriceIsDeclaredSumOfRawMobiusComponents :=
    hBind.totalCleanPriceIsSumOfRawMobiusComponents
  routeDoesNotReplaceSignedTripleCoefficientsByPositiveCoherence :=
    hBind.coherenceIsSignedRawTripleNotPositiveCoherence
  sameRawProfileFamilyFeedsActualBridge :=
    hBind.sameRawProfileFamilyFeedsActualBridge

/-- Corrected componentwise identity target.  This keeps the useful conclusion
of `CleanFiniteProfileComponentPricesEqualCanonicalRawProjections`, while
forcing the proof to pass through Mobius order filters on the whole finite-set
functional. -/
structure CleanFiniteProfileComponentPricesEqualCanonicalRawMobiusProjections where
  rawMobiusIdentity : CleanComponentPricesAreDeclaredRawMobiusProjections
  rawMobiusMenuBinding : CleanRouteRawMobiusProjectionMenuBinding
  bindingUsesTheIdentityMenu :
    rawMobiusMenuBinding.mobiusProjectionMenu =
      rawMobiusIdentity.mobiusProjectionMenu
  rawSignedMobiusSupportLeThree : Prop
  singletonPairTripleComponentsReconstructTotal : Prop
  postLedgerPositiveCoherenceIsNotUsedAsRawTripleOrder : Prop

/-- Intermediate identity bridge if the canonical PDE raw functional exists.
This is deliberately weaker than full carrier storage: it only says the Phase
5FB stored raw observable and the clean-route finite-profile functional are
both the same canonical pre-ledger PDE object. -/
structure Phase5FBFiniteProfileFunctionalMatchViaCanonicalPDEFunctional where
  replayModel : Phase5FBGeneratedObservableReplayModelWitness
  rawStageStorage : Phase5FBRawStageStorageTheorem
  canonicalFunctional : CanonicalFiniteProfilePDERawPriceFunctional
  phase5fbStoredRawObservableEqualsCanonicalPDEFunctional : Prop
  cleanRouteFiniteProfileFunctionalEqualsCanonicalPDEFunctional : Prop
  matchesEveryFiniteProfileSet : Prop

/-- First failed field from the Phase 5FB residual-facts cold shot.  A replayed
observable and a projected stream can agree while the pre-projection
finite-profile functional differs.  This witness is the positive datum that
would rule out that failure. -/
structure Phase5FBFiniteProfileFunctionalMatchWitness where
  replayModel : Phase5FBGeneratedObservableReplayModelWitness
  rawStageStorage : Phase5FBRawStageStorageTheorem
  rawObservable : ActualObservableRawSignedSource
  rawObservableIsPhase5FBStoredRawObservable : Prop
  rawObservableIsCleanRouteFiniteProfilePriceFunctional : Prop
  matchesEveryFiniteProfileSet : Prop

/-- Adapter from the canonical PDE functional reframing to the first Phase 5FB
residual field.  All mathematical content is in the two identity facts: the
stored Phase 5FB raw observable and the clean-route finite-profile functional
must both be the same pre-ledger PDE functional. -/
def phase5fb_finite_profile_functional_match_witness_of_canonical_pde_functional
    (hMatch : Phase5FBFiniteProfileFunctionalMatchViaCanonicalPDEFunctional) :
    Phase5FBFiniteProfileFunctionalMatchWitness where
  replayModel := hMatch.replayModel
  rawStageStorage := hMatch.rawStageStorage
  rawObservable := hMatch.canonicalFunctional.carrier.rawObservable
  rawObservableIsPhase5FBStoredRawObservable :=
    hMatch.phase5fbStoredRawObservableEqualsCanonicalPDEFunctional
  rawObservableIsCleanRouteFiniteProfilePriceFunctional :=
    hMatch.cleanRouteFiniteProfileFunctionalEqualsCanonicalPDEFunctional
  matchesEveryFiniteProfileSet := hMatch.matchesEveryFiniteProfileSet

/-- Adapter from the carrier/projection identity theorem to the first Phase 5FB
residual field.  This is the version to use after the latest GPT-5.5 response:
the clean scalar is not free; it is the declared projection of the canonical
carrier. -/
def phase5fb_finite_profile_functional_match_witness_of_clean_raw_projection
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem)
    (hIdentity : CleanFiniteProfilePriceEqualsCanonicalRawProjection)
    (hStoredRawObservableIsCarrierObservable : Prop) :
    Phase5FBFiniteProfileFunctionalMatchWitness where
  replayModel := hModel
  rawStageStorage := hStorage
  rawObservable := hIdentity.canonicalCarrier.rawObservable
  rawObservableIsPhase5FBStoredRawObservable := hStoredRawObservableIsCarrierObservable
  rawObservableIsCleanRouteFiniteProfilePriceFunctional :=
    hIdentity.cleanFiniteProfilePriceIsProjectionOfCarrier
  matchesEveryFiniteProfileSet := hIdentity.matchAllFiniteProfileSets

/-- Collapse the componentwise projection identity to the scalar first-field
target by choosing one already-declared component projection. -/
def clean_finite_profile_price_equals_canonical_raw_projection_of_component_menu
    (hComponent : CleanFiniteProfileComponentPricesEqualCanonicalRawProjections)
    (component : LeraySelfTaxPriceComponent) :
    CleanFiniteProfilePriceEqualsCanonicalRawProjection where
  canonicalCarrier := hComponent.canonicalCarrier
  cleanProjection := hComponent.projectionMenu.componentProjection component
  cleanFiniteProfilePriceIsProjectionOfCarrier :=
    match component with
    | LeraySelfTaxPriceComponent.selfTax =>
        hComponent.selfTaxMatchesCanonicalProjection
    | LeraySelfTaxPriceComponent.crossDefect =>
        hComponent.crossDefectMatchesCanonicalProjection
    | LeraySelfTaxPriceComponent.coherence =>
        hComponent.coherenceMatchesCanonicalProjection
  matchAllFiniteProfileSets :=
    match component with
    | LeraySelfTaxPriceComponent.selfTax =>
        hComponent.selfTaxMatchesCanonicalProjection
    | LeraySelfTaxPriceComponent.crossDefect =>
        hComponent.crossDefectMatchesCanonicalProjection
    | LeraySelfTaxPriceComponent.coherence =>
        hComponent.coherenceMatchesCanonicalProjection
  sameRawProfileFamilyFeedsActualBridge :=
    hComponent.sameRawProfileFamilyFeedsActualBridge

/-- Forget the projection-menu binding after it has served its purpose.  Any
downstream theorem that only consumes the componentwise identity may use this
adapter, while the proof-producing side still has to pay the menu-binding
certificate. -/
def clean_component_prices_equal_canonical_raw_projections_of_binding
    (h :
      CleanFiniteProfileComponentPricesEqualCanonicalRawProjectionsWithBinding) :
    CleanFiniteProfileComponentPricesEqualCanonicalRawProjections :=
  h.identity

/-- Constructor from localized NS receipts to the canonical carrier target.  It
does not prove the clean route identity; it only packages the PDE-side carrier
construction once the localized profile/cutoff/pressure/window receipts are
all tied to the same raw family. -/
def canonical_finite_profile_raw_pde_carrier_of_localized_ns_receipts
    (hCarrier : CanonicalFiniteProfileRawPDECarrier)
    (hReceipts : CanonicalFiniteProfileRawPDECarrierLocalizedNSReceipts) :
    CanonicalFiniteProfileRawPDECarrierConstructionTarget where
  carrier := hCarrier
  declaredProjection := {
    projectionIsLinearOnCarrierComponents := True
    declaredBeforeProjectionReplayEnvelopeThresholdOrLedger :=
      hCarrier.noProjectionReplayEnvelopeThresholdOrLedgerInput
    doesNotChooseRepresentativeAfterProjection := True
    doesNotUsePostLedgerPositivePartOrSurvivalData :=
      hCarrier.noProjectionReplayEnvelopeThresholdOrLedgerInput
  }
  pressureAwareMobiusExpansion := hReceipts.mobiusExpansion
  carrierIsPreLedgerLocalizedNSEnergyAlgebra :=
    hCarrier.commonWindowLocalizedProfileSumsAreNamed ∧
      hCarrier.pressureIsPreLedgerBilinearRieszOfProfileSum ∧
        hCarrier.viscousTermIsNamed ∧
          hCarrier.quadraticCutoffTermIsNamed ∧
            hCarrier.convectiveFluxTermIsNamed ∧
              hCarrier.pressureFluxTermIsNamed ∧
                hReceipts.localEnergyViscousAndQuadraticCutoffTermsAreAvailable ∧
                  hReceipts.convectiveFluxTermIsProducedByLocalizedProfileSum ∧
                    hReceipts.pressureFluxTermUsesTheSameLocalizedPressureSplit ∧
                      hReceipts.allReceiptsUseTheSameProfileWindowAndCutoff
  projectedScalarHasMobiusSupportLeThree :=
    hReceipts.mobiusExpansion.finiteProfileSubsetFunctionalsAreDefined ∧
      hReceipts.mobiusExpansion.mobiusCoefficientsAreCanonicallyDefined
  cleanRouteIdentityStillNeedsProof := True

/-- Use the stronger receipt-to-carrier constructor to produce the finite-set
raw carrier functional consumed by the Mobius projection menu. -/
def finite_profile_raw_carrier_functional_of_localized_ns_construction
    (h : ConstructCanonicalFiniteProfileRawPDECarrierFromLocalizedNSReceipts) :
    FiniteProfileRawCarrierFunctional where
  carrier := h.constructedCarrier
  mobiusExpansion := h.receipts.mobiusExpansion
  finiteProfileFunctionalDeclaredBeforeLedger :=
    h.carrierTermsAreAllDeclaredBeforeLedgerEnvelopeAndReplay
  carrierTermsEvaluateOnEveryFiniteProfileSet :=
    h.constructedCarrier.carrierEvaluationIsCanonicalForEveryFiniteProfileSet
  scalarizedCarrierHasPolynomialDegreeAtMostThree :=
    h.receipts.mobiusExpansion.finiteProfileSubsetFunctionalsAreDefined ∧
      h.receipts.mobiusExpansion.mobiusCoefficientsAreCanonicallyDefined ∧
        h.receipts.pressureGaugeAndCutoffConventionAreFixed
  mobiusSupportAboveThreeVanishes :=
    h.receipts.mobiusExpansion.finiteProfileSubsetFunctionalsAreDefined ∧
      h.receipts.mobiusExpansion.mobiusCoefficientsAreCanonicallyDefined ∧
        h.constructedCarrier.carrierEvaluationIsCanonicalForEveryFiniteProfileSet

/-- Explicit support projection for the finite-set raw carrier layer.  The
degree-`≤3` algebra and the vanishing of higher Mobius coefficients are fields
of the same pre-ledger raw-functional package; consumers should cite this
declaration rather than jumping from a pointwise scalar carrier to component
prices. -/
def finiteProfileRawCarrierFunctional_supportLeThree_of_degreeLeThree
    (h : FiniteProfileRawCarrierFunctional)
    (_hDegree : h.scalarizedCarrierHasPolynomialDegreeAtMostThree) :
    Prop :=
  h.mobiusSupportAboveThreeVanishes

/-- Raw signed Mobius constructor for the corrected component theorem.  All
nontrivial mathematics is in the input identity object: this definition only
records that order-one, order-two, and order-three Mobius projections are the
right component interface. -/
def clean_finite_profile_component_prices_equal_canonical_raw_mobius_projections
    (hRaw : CleanComponentPricesAreDeclaredRawMobiusProjections)
    (hBinding : CleanRouteRawMobiusProjectionMenuBinding)
    (hSameMenu : hBinding.mobiusProjectionMenu = hRaw.mobiusProjectionMenu) :
    CleanFiniteProfileComponentPricesEqualCanonicalRawMobiusProjections where
  rawMobiusIdentity := hRaw
  rawMobiusMenuBinding := hBinding
  bindingUsesTheIdentityMenu := hSameMenu
  rawSignedMobiusSupportLeThree :=
    hRaw.rawFunctional.mobiusSupportAboveThreeVanishes
  singletonPairTripleComponentsReconstructTotal :=
    hRaw.totalPriceIsDeclaredSumOfRawMobiusComponents
  postLedgerPositiveCoherenceIsNotUsedAsRawTripleOrder :=
    hRaw.routeDoesNotReplaceSignedTripleCoefficientsByPositiveCoherence

/-- Second residual field from the Phase 5FB cold shot.  The storage theorem
pays some pre-ledger ordering, but the clean bridge consumes the stronger
claim that the raw finite-profile restriction is declared before envelope
fitting and every later ledger operation. -/
structure Phase5FBEnvelopePlacementCertificate where
  rawObservable : ActualObservableRawSignedSource
  rawDeclaredBeforeEnvelopeFitting : Prop
  rawDeclaredBeforeThresholdCoordinateLayer : Prop
  rawDeclaredBeforeQuarticSurvivalProjection : Prop
  rawDeclaredBeforeNoSurvivorProjection : Prop
  rawDeclaredBeforePositiveCoherenceAggregation : Prop

/-- Third and hardest residual field.  The actual-observable bridge must
consume the same raw source named by Phase 5FB storage, not a replayed
threshold-root object, a post-ledger representative, or a cleaner surrogate. -/
structure Phase5FBActualBridgeSameRawSourceWitness where
  replayModel : Phase5FBGeneratedObservableReplayModelWitness
  rawStageStorage : Phase5FBRawStageStorageTheorem
  rawObservable : ActualObservableRawSignedSource
  bridgePrerequisites : ActualObservableBridgePrerequisites
  bridgeConsumesSameStoredRawSource : Prop
  bridgeDoesNotUseReplayImageAsRawSource : Prop
  bridgeDoesNotUseSurrogateRawObservable : Prop

/-- Corrected theorem after the pressure-recovered raw-carrier eigenquestion.
The broad component identity follows once the route component names are
explicitly bound to the signed raw Mobius menu, with the same-source bridge and
carrier construction kept as separate inputs. -/
def clean_finite_profile_components_eq_canonical_raw_mobius_of_route_binding
    (_hConstruct :
      ConstructCanonicalFiniteProfileRawPDECarrierFromLocalizedNSReceipts)
    (hMenu : CleanRouteRawMobiusProjectionMenuBinding)
    (_hBridge : Phase5FBActualBridgeSameRawSourceWitness)
    (hBind : RouteComponentPriceBindingToRawMobiusMenu)
    (hSameMenu : hMenu.mobiusProjectionMenu = hBind.menu) :
    CleanFiniteProfileComponentPricesEqualCanonicalRawMobiusProjections :=
  clean_finite_profile_component_prices_equal_canonical_raw_mobius_projections
    {
      (clean_component_prices_are_declared_raw_mobius_projections_of_route_binding
        hBind) with
      sameRawProfileFamilyFeedsActualBridge :=
        hBind.sameRawProfileFamilyFeedsActualBridge
    }
    hMenu
    hSameMenu

/-- Reuse the existing selected-branch raw carrier and Phase 5FB storage
primitives to populate the same-source bridge witness.  The proof still needs
the finite-profile match and envelope-placement inputs; once those are paid,
the remaining same-source fields come from the `Phase5FBRawStageStorageTheorem`
provenance and raw-audit compatibility records. -/
def phase5fb_actual_bridge_same_raw_source_witness_of_selected_branch_carrier
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem)
    (hCarrier : SelectedGeneratedBranchRawSignedSourceCarrier)
    (hMatchesFiniteProfilePriceFunctional : Prop)
    (hDeclaredBeforeEnvelopeFitting : Prop) :
    Phase5FBActualBridgeSameRawSourceWitness where
  replayModel := hModel
  rawStageStorage := hStorage
  rawObservable :=
    actual_observable_raw_signed_source_of_selected_branch_raw_signed_source_carrier
      hCarrier
  bridgePrerequisites :=
    Classical.choice
      (actual_observable_bridge_prerequisites_of_selected_branch_raw_signed_source_carrier
        hCarrier
        hMatchesFiniteProfilePriceFunctional
        hDeclaredBeforeEnvelopeFitting)
  bridgeConsumesSameStoredRawSource :=
    hStorage.sameSourceProvenance.bothNamesReferToTheSameRawSignedSource
  bridgeDoesNotUseReplayImageAsRawSource :=
    hStorage.rawMobiusAuditCompatibility.postLedgerAuditIsNotUsedAsASubstitute
  bridgeDoesNotUseSurrogateRawObservable :=
    hStorage.sameSourceProvenance.bothNamesReferToTheSameRawSignedSource

/-- Strict intermediate primitive from the cold shot.  This compresses the
three residual fields without pretending that Phase 5FB replay/storage proves
them.  It is stronger than raw-stage storage and weaker than storing an entire
selected-branch carrier as an opaque primitive. -/
structure Phase5FBActualRawObservableIdentityWitness where
  functionalMatch : Phase5FBFiniteProfileFunctionalMatchWitness
  envelopePlacement : Phase5FBEnvelopePlacementCertificate
  bridgeSameRawSource : Phase5FBActualBridgeSameRawSourceWitness
  rawMobiusAuditBeforeLedger : Prop

/-- If the canonical PDE raw functional pays the first residual field, the
remaining Phase 5FB identity witness is exactly envelope placement plus the
same-source actual bridge. -/
def phase5fb_actual_raw_observable_identity_of_canonical_pde_functional
    (hMatch : Phase5FBFiniteProfileFunctionalMatchViaCanonicalPDEFunctional)
    (hEnvelope : Phase5FBEnvelopePlacementCertificate)
    (hBridge : Phase5FBActualBridgeSameRawSourceWitness)
    (hRawMobiusAuditBeforeLedger : Prop) :
    Phase5FBActualRawObservableIdentityWitness where
  functionalMatch :=
    phase5fb_finite_profile_functional_match_witness_of_canonical_pde_functional
      hMatch
  envelopePlacement := hEnvelope
  bridgeSameRawSource := hBridge
  rawMobiusAuditBeforeLedger := hRawMobiusAuditBeforeLedger

/-- Carrier/projection version of the same identity constructor.  This is the
current preferred route after the response: first prove the clean price equals
the declared projection of the PDE carrier, then add envelope placement and
same-source bridge compatibility. -/
def phase5fb_actual_raw_observable_identity_of_clean_raw_projection
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem)
    (hIdentity : CleanFiniteProfilePriceEqualsCanonicalRawProjection)
    (hStoredRawObservableIsCarrierObservable : Prop)
    (hEnvelope : Phase5FBEnvelopePlacementCertificate)
    (hBridge : Phase5FBActualBridgeSameRawSourceWitness)
    (hRawMobiusAuditBeforeLedger : Prop) :
    Phase5FBActualRawObservableIdentityWitness where
  functionalMatch :=
    phase5fb_finite_profile_functional_match_witness_of_clean_raw_projection
      hModel hStorage hIdentity hStoredRawObservableIsCarrierObservable
  envelopePlacement := hEnvelope
  bridgeSameRawSource := hBridge
  rawMobiusAuditBeforeLedger := hRawMobiusAuditBeforeLedger

/-- Countermodel surface for the first failed field: replay compatibility and
projected-stream agreement do not determine equality of the finite-profile raw
price functional before projection. -/
structure Phase5FBFiniteProfileFunctionalMatchDoesNotFollowFromReplayStorage where
  replayAndProjectedStreamAgree : Prop
  rawStageStorageStillHolds : Prop
  rawSideMobiusAuditExists : Prop
  finiteProfileFunctionalCanDiffer : Prop
  firstResidualFieldFails : Prop

/-- Countermodel surface for the envelope field.  Pre-threshold and
pre-survival ordering can hold while envelope fitting is still performed at a
later projected or ledgered stage. -/
structure Phase5FBEnvelopePlacementDoesNotFollowFromReplayStorage where
  phase5fbPreThresholdOrderingHolds : Prop
  phase5fbPreSurvivalNoSurvivorOrderingHolds : Prop
  envelopeMayBeFittedAfterProjectionOrLedger : Prop
  declaredBeforeEnvelopeStillNeedsCertificate : Prop

/-- Countermodel surface for the same-source bridge field.  Non-injective
replay/threshold maps can identify distinct raw sources, so replay + storage
does not by itself prove that the actual bridge consumes the stored raw
source. -/
structure Phase5FBActualBridgeSameRawSourceDoesNotFollowFromReplayStorage where
  replayStoragePackageHolds : Prop
  distinctRawSourcesCanShareReplayImage : Prop
  bridgeMayConsumeDifferentRawSource : Prop
  postLedgerRepresentativeMayMasqueradeAsRaw : Prop
  sameSourceBridgeTheoremStillNeeded : Prop

/-- Countermodel surface for the newly isolated projection-menu issue.  Even a
canonical carrier can be made to match arbitrary clean component prices if the
projection menu is chosen after those prices are known. -/
structure CleanComponentProjectionIdentityFailsUnderPosthocMenu where
  canonicalCarrierMayExist : Prop
  cleanComponentPricesMayBeKnownFirst : Prop
  projectionMenuChosenAfterCleanPrices : Prop
  componentEqualitiesCanBecomeDefinitions : Prop
  finiteProfileFunctionalMatchStillUnproved : Prop
  predeclaredProjectionMenuBindingIsMissing : Prop

/-- Finite-profile countermodel surface for the latest projection-menu result.
A pointwise projection of the full-set carrier value can match a total scalar
while still losing the Mobius interaction order split between self, cross, and
coherence. -/
structure PointwiseCarrierProjectionCannotRecoverMobiusInteractionOrder where
  twoFiniteProfileFunctionalsHaveSameFullSetValue : Prop
  singletonMobiusComponentsDiffer : Prop
  pairMobiusComponentsDiffer : Prop
  pointwiseProjectionSeesOnlyAggregateFullSetValue : Prop
  rawMobiusProjectionMenuStillNeeded : Prop

/-- Direct route-binding no-go from the pointwise/full-set projection
countermodel: aggregate scalar equality is not enough to bind clean self,
cross, and coherence prices to raw Mobius interaction orders. -/
def no_routeComponentPriceBindingToRawMobiusMenu_of_pointwiseFullSetProjection
    (h : PointwiseCarrierProjectionCannotRecoverMobiusInteractionOrder) :
    Prop :=
  h.rawMobiusProjectionMenuStillNeeded ∧
    h.pointwiseProjectionSeesOnlyAggregateFullSetValue

/-- Countermodel surface from the latest eigenquestion: carrier construction,
menu declaration, and same-source bridge can all be present while the route
component names are still not theorem-wise equal to the signed raw Mobius
components. -/
structure RouteComponentPriceBindingDoesNotFollowFromCarrierMenuBridge where
  carrierConstructionExists : Prop
  rawMobiusMenuIsDeclaredBeforeAudit : Prop
  sameSourceActualBridgeWitnessExists : Prop
  routeSelfTaxNameMayBeNonMobiusOutputPrice : Prop
  routeCrossDefectNameMayBeLedgerOrEnvelopePrice : Prop
  routeCoherenceNameMayBePositivePostLedgerCoherence : Prop
  routeComponentBindingStillNeedsSeparateTheorem : Prop

/-- Stricter countermodel after the projection menu has been fixed: a
predeclared menu still does not determine the carrier unless the
common-window, cutoff, and pressure-localization receipts are themselves
rigidly bound to the same raw profile family. -/
structure PredeclaredComponentProjectionMenuDoesNotFixPressureCutoffWindowGauge where
  samePredeclaredProjectionMenu : Prop
  sameCleanComponentPrices : Prop
  sameRawObservableName : Prop
  differentCommonWindowChoice : Prop
  differentCutoffGeometryChoice : Prop
  differentPressurePairOrFluxLocalization : Prop
  differentCanonicalCarrierComponents : Prop
  componentProjectionIdentityCanHoldForBoth : Prop
  canonicalCarrierStillNotDetermined : Prop

/-- No-go guard for overreading the localized NS construction record.  The
current construction carries internal same-window/cutoff/pressure props, but
that is weaker than an extensional theorem identifying the carrier's
window/cutoff/gauge objects with the clean route's actual choices. -/
structure PressureCutoffWindowGaugeBindingDoesNotFollowFromLocalizedNSConstruction where
  localizedNSConstructionExists : Prop
  internalCommonWindowPropExists : Prop
  internalCutoffGeometryPropExists : Prop
  internalPressureGaugePropExists : Prop
  cleanRouteWindowObjectNotIdentified : Prop
  cleanRouteCutoffObjectNotIdentified : Prop
  cleanRoutePressureGaugeObjectNotIdentified : Prop
  extensionalPressureCutoffWindowGaugeBindingStillNeedsWitness : Prop

/-- Positive rigidity interface dual to
`PredeclaredComponentProjectionMenuDoesNotFixPressureCutoffWindowGauge`.
The pressure-recovered carrier is canonical only after the clean route fixes
the common profile window, cutoff geometry, pressure gauge, and pressure-flux
localization before the finite-profile audit. -/
structure PressureCutoffWindowGaugeBinding where
  carrier : CanonicalFiniteProfileRawPDECarrier
  receipts : CanonicalFiniteProfileRawPDECarrierLocalizedNSReceipts
  commonWindowMatchesCleanRoute : Prop
  cutoffGeometryMatchesCleanRoute : Prop
  pressureGaugeMatchesCleanRoute : Prop
  pressurePairDecompositionMatchesCleanRoute : Prop
  pressureFluxLocalizationMatchesCleanRoute : Prop
  bindingDeclaredBeforeMobiusAudit : Prop
  noRepresentativeChoiceAfterProjection : Prop

/-- Same-source agreement between the canonical raw carrier functional and the
Phase 5FB actual-observable bridge.  This is intentionally stricter than
assuming both sides have some raw observable: the bridge must consume the raw
observable carried by the finite-profile PDE functional. -/
structure FiniteProfileRawCarrierActualBridgeSourceAgreement where
  rawFunctional : FiniteProfileRawCarrierFunctional
  bridgeWitness : Phase5FBActualBridgeSameRawSourceWitness
  carrierRawObservableMatchesBridgeRawObservable : Prop
  bridgeConsumesCarrierRawSource : Prop
  bridgeDoesNotUseReplayImageInsteadOfCarrier : Prop
  bridgeDoesNotUseSurrogateInsteadOfCarrier : Prop

/-- Minimal constructor for the same-source bridge agreement.  It deliberately
requires an explicit proposition equating the canonical carrier's raw
observable with the Phase 5FB bridge raw observable; replay/storage alone does
not provide that equality. -/
def finite_profile_raw_carrier_actual_bridge_source_agreement_of_functional_match_and_phase5fb_bridge
    (rawFunctional : FiniteProfileRawCarrierFunctional)
    (_hMatch : Phase5FBFiniteProfileFunctionalMatchWitness)
    (hBridge : Phase5FBActualBridgeSameRawSourceWitness)
    (hCarrierRawObservableMatchesBridgeRawObservable : Prop) :
    FiniteProfileRawCarrierActualBridgeSourceAgreement where
  rawFunctional := rawFunctional
  bridgeWitness := hBridge
  carrierRawObservableMatchesBridgeRawObservable :=
    hCarrierRawObservableMatchesBridgeRawObservable
  bridgeConsumesCarrierRawSource :=
    hBridge.bridgeConsumesSameStoredRawSource
  bridgeDoesNotUseReplayImageInsteadOfCarrier :=
    hBridge.bridgeDoesNotUseReplayImageAsRawSource
  bridgeDoesNotUseSurrogateInsteadOfCarrier :=
    hBridge.bridgeDoesNotUseSurrogateRawObservable

/-- Stricter positive-coherence no-go.  The signed triple-order raw Mobius
coefficient may be the right PDE component, while route-level positive
coherence can be a later threshold/positive-part object.  Those objects must
not be silently identified. -/
structure PositiveCoherenceCannotStandInForSignedRawTripleOrder where
  signedRawTripleMobiusCoefficientIsAvailable : Prop
  postLedgerPositiveCoherenceIsAvailable : Prop
  sameTotalOrFullSetScalarMayStillHold : Prop
  singletonAndPairChecksMayStillHold : Prop
  positiveCoherenceMayContainHigherOrderMobiusMass : Prop
  routeCoherenceBindingToSignedTripleStillFails : Prop

/-- Direct route-binding no-go from the positive-coherence lane: a post-ledger
positive coherence object cannot discharge the signed raw triple-order Mobius
component field. -/
def no_routeComponentPriceBindingToRawMobiusMenu_of_positiveCoherenceLane
    (h : PositiveCoherenceCannotStandInForSignedRawTripleOrder) :
    Prop :=
  h.routeCoherenceBindingToSignedTripleStillFails ∧
    h.positiveCoherenceMayContainHigherOrderMobiusMass

/-- The current component spine is still output/ledger-facing unless a raw
Mobius binding is supplied.  This records Euler's audit result without
claiming the stream coordinates are wrong; it only says they are not yet the
pre-ledger signed Mobius definitions. -/
structure CleanRouteComponentPricesCurrentlyOutputLevelNotRawMobiusDefinitions where
  selfTaxNameComesFromPrefixOrOutputStream : Prop
  crossDefectNameComesFromPrefixOrOutputStream : Prop
  coherenceNameMayComeFromPositiveOrLedgerCoherenceLane : Prop
  rawMobiusOrderDefinitionIsNotDefinitionallyPresent : Prop
  routeComponentPriceBindingStillNeeded : Prop

/-- Exact negative audit for the current GP216/continuum coupling surface:
matching Leray self-tax prefix fields to continuum all-output prefix fields is
still an output-stream coupling.  It does not by itself say those fields are
the singleton/pair/triple signed raw Mobius projections of the pre-ledger PDE
carrier. -/
structure LeraySelfTaxContinuumCouplingDoesNotUsePressureAwareMobiusExpansion where
  continuumCouplingMatchesPrefixSelfTax : Prop
  continuumCouplingMatchesPrefixCrossDefect : Prop
  continuumCouplingMatchesPrefixCoherenceToResidual : Prop
  pressureAwareMobiusExpansionMayExistSeparately : Prop
  noTheoremEquatesPrefixFieldsWithRawMobiusOrderFilters : Prop
  routeComponentPriceBindingStillNeeded : Prop

/-- Guard against a subtler local shortcut: a localized component expansion
may say its finite prefixes represent actual component prices, but the clean
route still needs a theorem identifying those prices with the
`LeraySelfTaxProfilePriceStream` prefix fields consumed downstream. -/
structure LocalizedComponentExpansionDoesNotImplyCleanRouteMobiusBinding where
  localizedComponentExpansionExists : Prop
  finitePrefixesRepresentActualComponentPrices : Prop
  pressureAwareMobiusExpansionExists : Prop
  cleanLeraySelfTaxPrefixFieldsMayBeSeparateObjects : Prop
  noTheoremIdentifiesExpansionPrefixesWithCleanRouteFields : Prop
  cleanRouteComponentsUsePressureAwareMobiusExpansionStillNeeded : Prop

/-- Precise no-go proposition from the current output-level declarations:
continuum
coupling and localized component expansion can coexist with a pressure-aware
Mobius expansion while still not proving that the clean route component names
are the raw signed Mobius singleton/pair/higher-order projections. -/
def outputLevelRouteComponentNames_do_not_discharge_pressureAwareMobiusBinding
    (hOutput :
      CleanRouteComponentPricesCurrentlyOutputLevelNotRawMobiusDefinitions)
    (hContinuum :
      LeraySelfTaxContinuumCouplingDoesNotUsePressureAwareMobiusExpansion)
    (hLocalized :
      LocalizedComponentExpansionDoesNotImplyCleanRouteMobiusBinding) : Prop :=
    hOutput.rawMobiusOrderDefinitionIsNotDefinitionallyPresent ∧
      hOutput.routeComponentPriceBindingStillNeeded ∧
        hContinuum.noTheoremEquatesPrefixFieldsWithRawMobiusOrderFilters ∧
          hLocalized.noTheoremIdentifiesExpansionPrefixesWithCleanRouteFields ∧
            hLocalized.cleanRouteComponentsUsePressureAwareMobiusExpansionStillNeeded

/-- Stronger local construction target suggested by the PDE swarm.  Localized
NS receipts and the pressure-aware Mobius expansion can feed the route binding
only after pressure/cutoff/window/gauge rigidity and actual-bridge source
agreement are both paid. -/
structure RouteComponentPriceBindingFromLocalizedNSAndExpansionTarget where
  construction : ConstructCanonicalFiniteProfileRawPDECarrierFromLocalizedNSReceipts
  componentExpansion : PressureAwareMobiusProfilePriceExpansion
  mobiusMenu : TrackBDeclaredRawMobiusProjectionMenu
  pressureCutoffWindowGaugeBinding : PressureCutoffWindowGaugeBinding
  bridgeSourceAgreement : FiniteProfileRawCarrierActualBridgeSourceAgreement
  cleanSelfTaxUsesExpansionSingletonCoefficients : Prop
  cleanCrossDefectUsesExpansionPairCoefficients : Prop
  cleanCoherenceUsesExpansionTripleCoefficients : Prop
  cleanCoherenceIsNotPostLedgerPositiveCoherence : Prop
  targetWouldProduceRouteComponentBinding : Prop

/-- Any localized-NS construction of the route-component binding must carry the
pressure/cutoff/window/gauge rigidity witness. -/
def routeComponentPriceBindingToRawMobiusMenu_requires_pressureCutoffWindowGaugeBinding
    (h : RouteComponentPriceBindingFromLocalizedNSAndExpansionTarget) :
    PressureCutoffWindowGaugeBinding :=
  h.pressureCutoffWindowGaugeBinding

/-- Any localized-NS construction of the route-component binding must carry the
same raw profile family through the actual-observable bridge. -/
def routeComponentPriceBindingToRawMobiusMenu_requires_sameRawProfileFamily
    (h : RouteComponentPriceBindingFromLocalizedNSAndExpansionTarget) :
    FiniteProfileRawCarrierActualBridgeSourceAgreement :=
  h.bridgeSourceAgreement

/-- The localized NS construction already carries the pressure/cutoff/window
receipts needed by the positive rigidity interface.  This adapter is not the
component-price theorem; it only packages the PDE carrier conventions so they
cannot be chosen after the finite-profile audit. -/
def pressure_cutoff_window_gauge_binding_of_localized_ns_construction
    (h : ConstructCanonicalFiniteProfileRawPDECarrierFromLocalizedNSReceipts) :
    PressureCutoffWindowGaugeBinding where
  carrier := h.constructedCarrier
  receipts := h.receipts
  commonWindowMatchesCleanRoute := h.carrierUsesTheCommonProfileWindow
  cutoffGeometryMatchesCleanRoute := h.carrierUsesTheLocalizedCutoffGeometry
  pressureGaugeMatchesCleanRoute := h.carrierGaugeMatchesPressureNormalization
  pressurePairDecompositionMatchesCleanRoute :=
    h.carrierPressureFieldMatchesPressurePairDecomposition
  pressureFluxLocalizationMatchesCleanRoute :=
    h.receipts.pressureFluxTermUsesTheSameLocalizedPressureSplit
  bindingDeclaredBeforeMobiusAudit :=
    h.carrierTermsAreAllDeclaredBeforeLedgerEnvelopeAndReplay
  noRepresentativeChoiceAfterProjection :=
    h.constructedCarrier.noProjectionReplayEnvelopeThresholdOrLedgerInput

/-- Smaller adapter from the localized-NS route target to the exact component
binding surface isolated by the swarm. This keeps the target centered on the
clean route using the pressure-aware Mobius expansion, with pressure/cutoff/
window rigidity and same-source bridge agreement retained as fields of the
input target rather than silently inferred. -/
def clean_route_components_use_pressure_aware_mobius_expansion_of_localized_ns_and_expansion_target
    (h : RouteComponentPriceBindingFromLocalizedNSAndExpansionTarget) :
    CleanRouteComponentsUsePressureAwareMobiusExpansion where
  rawFunctional :=
    finite_profile_raw_carrier_functional_of_localized_ns_construction
      h.construction
  menu := h.mobiusMenu
  expansion := h.componentExpansion
  cleanSelfTaxUsesExpansionSingletonCoefficients :=
    h.cleanSelfTaxUsesExpansionSingletonCoefficients
  cleanCrossDefectUsesExpansionPairCoefficients :=
    h.cleanCrossDefectUsesExpansionPairCoefficients
  cleanCoherenceUsesExpansionHigherCoefficients :=
    h.cleanCoherenceUsesExpansionTripleCoefficients
  cleanCoherenceIsSignedHigherOrderNotPositivePostLedgerCoherence :=
    h.cleanCoherenceIsNotPostLedgerPositiveCoherence
  cleanTotalUsesSumOfExpansionComponents :=
    h.targetWouldProduceRouteComponentBinding
  expansionAndCleanRouteUseSameRawProfileFamily :=
    h.bridgeSourceAgreement.bridgeConsumesCarrierRawSource ∧
        h.bridgeSourceAgreement.carrierRawObservableMatchesBridgeRawObservable ∧
          h.bridgeSourceAgreement.bridgeDoesNotUseReplayImageInsteadOfCarrier ∧
            h.bridgeSourceAgreement.bridgeDoesNotUseSurrogateInsteadOfCarrier

/-- Localized-NS route target, after pressure/cutoff/window/gauge and
same-source bridge receipts, yields the checked self-tax/cross-defect/coherence
component-name binding to the pressure-aware Mobius expansion. -/
def localizedNSAndExpansionTarget_cleanRouteComponentNameBindings
    (h : RouteComponentPriceBindingFromLocalizedNSAndExpansionTarget) :
    CleanRouteComponentNameBindingsToPressureAwareMobiusExpansion :=
  cleanRouteComponentNameBindings_to_pressureAwareMobiusExpansion
    (clean_route_components_use_pressure_aware_mobius_expansion_of_localized_ns_and_expansion_target
      h)

/-- If the localized NS receipts, pressure/cutoff/window/gauge binding, raw
Mobius menu, expansion-to-clean component binding, and same-source bridge
agreement are all paid, then the route-component primitive is no longer just a
label. -/
def route_component_price_binding_of_localized_ns_and_expansion_target
    (h : RouteComponentPriceBindingFromLocalizedNSAndExpansionTarget) :
    RouteComponentPriceBindingToRawMobiusMenu where
  rawFunctional :=
    finite_profile_raw_carrier_functional_of_localized_ns_construction
      h.construction
  menu := h.mobiusMenu
  selfTaxCleanPriceIsSingletonRawMobiusProjection :=
    h.componentExpansion.singletonCoefficientsAreSelfTax ∧
      h.cleanSelfTaxUsesExpansionSingletonCoefficients
  crossDefectCleanPriceIsPairRawMobiusProjection :=
    h.componentExpansion.pairCoefficientsAreCrossDefect ∧
      h.cleanCrossDefectUsesExpansionPairCoefficients
  coherenceCleanPriceIsTripleRawMobiusProjection :=
    h.componentExpansion.higherCoefficientsAreCoherence ∧
      h.cleanCoherenceUsesExpansionTripleCoefficients
  totalCleanPriceIsSumOfRawMobiusComponents :=
    h.targetWouldProduceRouteComponentBinding
  cleanComponentNamesAreBoundBeforeLedgerEnvelopeReplay :=
    h.construction.carrierTermsAreAllDeclaredBeforeLedgerEnvelopeAndReplay ∧
      h.mobiusMenu.allDeclaredBeforeLedgerAndEnvelope ∧
        h.pressureCutoffWindowGaugeBinding.bindingDeclaredBeforeMobiusAudit
  coherenceIsSignedRawTripleNotPositiveCoherence :=
    h.cleanCoherenceIsNotPostLedgerPositiveCoherence
  sameRawProfileFamilyFeedsActualBridge :=
    h.bridgeSourceAgreement.bridgeConsumesCarrierRawSource ∧
      h.bridgeSourceAgreement.carrierRawObservableMatchesBridgeRawObservable ∧
        h.bridgeSourceAgreement.bridgeDoesNotUseReplayImageInsteadOfCarrier ∧
          h.bridgeSourceAgreement.bridgeDoesNotUseSurrogateInsteadOfCarrier

/-- Route-laundering guard for the forgetful adapter from the strengthened
binding theorem back down to the older componentwise identity. -/
structure ComponentProjectionBindingCanBeForgottenDownstream where
  bindingWitnessExists : Prop
  forgetfulAdapterIsAvailable : Prop
  downstreamConsumerMayUseIdentityWithoutBinding : Prop
  antiPosthocGuardIsNoLongerVisibleAtConsumerBoundary : Prop

/-- The DR-side raw carrier for the cross-lane theorem.  This is separate
from the local-energy carrier `(D,Q,C,P)`: the DR carrier is a pre-ledger
mollified commutator / scale-flux functional whose finite-profile Mobius
expansion is signed and cubic. -/
structure DuchonRobertCommutatorRawCarrier where
  rawProfileFamilyAgreesWithTrackB : FiniteProfileRawCarrierActualBridgeSourceAgreement
  l3aDuchonRobertFlux : NSL3MultiscaleYM.DuchonRobertFlux
  l3aFluxPrimitiveIsTheSameDRCommutatorFunctional : Prop
  reusesNSDefectCalculusSkeletonMollifiedFlux : Prop
  reusesNSDefectCalculusSkeletonRadonDefectMeasure : Prop
  reusesNSDefectCalculusSkeletonVagueLimitOfMollifiedFlux : Prop
  commonWindowCutoffAndMollifierFixedBeforeAudit : Prop
  drScaleFluxFunctionalDefinedForEveryFiniteProfile : Prop
  drScaleFluxFunctionalDeclaredBeforeLedger : Prop
  drScaleFluxFunctionalMobiusSupportLeThree : Prop
  tripleMobiusCoefficientIsLocalizedDRIncrementInteraction : Prop

/-- Guard: the canonical local-energy carrier does not by itself identify the
Duchon-Robert commutator.  A mollified energy-balance projection or explicit
DR commutator projection must be supplied. -/
structure LocalEnergyCarrierDoesNotAutomaticallyIdentifyDRCommutator where
  localEnergyCarrierExists : CanonicalFiniteProfileRawPDECarrier
  drCommutatorCarrierMayBeDifferentFunctional : Prop
  smoothDRAnomalousFluxCanVanishWhileLocalTransportTermsRemain : Prop
  explicitProjectionOrMollifiedEnergyBalanceStillNeeded : Prop

/-- Construction target for the DR commutator finite-profile carrier.  This is
the immediate positive surface below the signed Track-B/L3A bridge. -/
structure DuchonRobertCommutatorRawCarrierConstructionTarget where
  bridgeSourceAgreement : FiniteProfileRawCarrierActualBridgeSourceAgreement
  l3aDuchonRobertFlux : NSL3MultiscaleYM.DuchonRobertFlux
  l3aFluxPrimitiveIsTheSameDRCommutatorFunctional : Prop
  defectSkeletonMollifiedFluxAvailable : Prop
  defectSkeletonRadonDefectMeasureAvailable : Prop
  defectSkeletonVagueLimitAvailable : Prop
  commonWindowCutoffAndMollifierFixedBeforeAudit : Prop
  finiteProfileDRScaleFluxFunctionalDefined : Prop
  finiteProfileDRScaleFluxFunctionalPreLedger : Prop
  finiteProfileDRScaleFluxMobiusSupportLeThree : Prop
  tripleCoefficientFormulaIsLocalizedDRIncrementInteraction : Prop

/-- Compatibility datum between the pressure-aware local-energy/Mobius carrier
and the DR commutator functional.  This is not a function-level projection
from the four scalar local-energy components `(D,Q,C,P)` to the finite-scale
DR commutator.  It records that a separately constructed mollified DR carrier
uses the same raw profile family and limiting local-energy defect convention. -/
structure RawLocalEnergyCarrierProjectsToDRCommutator where
  localEnergyCarrier : CanonicalFiniteProfileRawPDECarrier
  drCommutatorCarrier : DuchonRobertCommutatorRawCarrier
  projectionDeclaredBeforeLedger : Prop
  usesSameRawProfileFamily : Prop
  usesSameWindowCutoffAndPressureGauge : Prop
  compatibilityIsNotProjectionFromFourScalarCarrierValues : Prop
  limitingDefectMatchesLocalEnergyResidual : Prop
  finiteScaleDRFluxComesFromMollifiedCarrier : Prop

/-- Projection target from the local-energy carrier to the DR commutator
carrier.  The key field is the mollified energy-balance identity; without it,
the local-energy transport terms and the DR commutator are only adjacent
objects. -/
structure RawLocalEnergyCarrierToDRCommutatorProjectionTarget where
  localEnergyCarrier : CanonicalFiniteProfileRawPDECarrier
  drCarrier : DuchonRobertCommutatorRawCarrier
  projectionDeclaredBeforeLedger : Prop
  sameRawProfileFamily : Prop
  sameWindowCutoffPressureGaugeAndMollifier : Prop
  projectionUsesL3ADuchonRobertFluxPrimitive : Prop
  declaredCubicProjectionIsTheDRCommutatorFunctional : Prop
  mollifiedEnergyBalanceIdentityAvailable : Prop
  localEnergyCarrierDoesNotDetermineFiniteScaleDRFluxAlone : Prop

/-- The corrected finite-scale identity surface: the DR commutator is
computed from filtered fields / commutator stress / increments, with the
equation residual accounted for.  This is the object that can be cubic in
finite-profile indicators before any ledger operation. -/
structure MollifiedDuchonRobertRawCarrierIdentity where
  drCarrier : DuchonRobertCommutatorRawCarrier
  filteredVelocityFieldStored : Prop
  filteredPressureFieldStored : Prop
  commutatorStressOrIncrementFunctionalStored : Prop
  finiteProfileEquationResidualStoredOrVanishing : Prop
  integratedMollifiedEnergyBalanceWithResidual : Prop
  exactSolutionResidualTermVanishesWhenAvailable : Prop
  finiteScaleDRFunctionalMobiusSupportLeThree : Prop
  declaredBeforeProjectionReplayEnvelopeThresholdOrLedger : Prop

/-- No-go surface from the finite-scale information test: the four scalar
local-energy carrier values cannot determine the scale-`ell` commutator stress
or increment cubic functional. -/
structure RawLocalEnergyCarrierDoesNotDetermineDRScaleFlux where
  localEnergyCarrier : CanonicalFiniteProfileRawPDECarrier
  sameLocalEnergyCarrierValuesMayHold : Prop
  differentScaleCommutatorStressMayHold : Prop
  differentDRScaleFluxMayHold : Prop
  cutoffMollifierMismatchCanCreateMissingTerms : Prop
  cannotInferFiniteScaleDRFluxFromFourScalarCarrierValues : Prop

/-- Honest compatibility theorem surface after the cold-shot audit: the
local-energy carrier can be matched to the limiting DR defect residual, while
finite-scale signed DR flux comes from the separate mollified commutator
carrier. -/
structure RawLocalEnergyCarrierToDRCommutatorCompatibility where
  localEnergyCarrier : CanonicalFiniteProfileRawPDECarrier
  drCarrier : DuchonRobertCommutatorRawCarrier
  mollifiedIdentity : MollifiedDuchonRobertRawCarrierIdentity
  sameRawProfileFamily : Prop
  sameWindowCutoffPressureGaugeAndMollifier : Prop
  limitingDRDefectMatchesLocalEnergyResidual : Prop
  finiteScaleDRFluxNotRecoveredFromLocalEnergyCarrierAlone : Prop

/-- Explicit identity package needed to derive the local-energy-to-DR
projection target from already constructed localized NS receipts.

This file intentionally does not import `ns_defect_calculus_skeleton`.  The
field names therefore tie the needed propositions to the existing skeleton API
without adding a new import edge here: `MollifiedFlux`,
`LocalEnergyBalanceWithDefect`, `RadonDefectMeasure`, and
`VagueLimitOfMollifiedFlux`. -/
structure LocalizedNSMollifiedEnergyBalanceDRProjectionIdentity
    (_hLocal :
      ConstructCanonicalFiniteProfileRawPDECarrierFromLocalizedNSReceipts)
    (_hDR : DuchonRobertCommutatorRawCarrierConstructionTarget) where
  nsDefectCalculusSkeleton_MollifiedFlux_is_declared_projection_source : Prop
  nsDefectCalculusSkeleton_LocalEnergyBalanceWithDefect_identifies_projection :
    Prop
  nsDefectCalculusSkeleton_RadonDefectMeasure_is_same_defect_term : Prop
  nsDefectCalculusSkeleton_VagueLimitOfMollifiedFlux_links_scale_flux_to_defect :
    Prop
  localizedNSReceiptsFeedTheMollifiedEnergyBalance : Prop
  projectionDeclaredBeforeLedger : Prop
  sameRawProfileFamily : Prop
  sameWindowCutoffPressureGaugeAndMollifier : Prop
  declaredCubicProjectionIsTheDRCommutatorFunctional : Prop

/-- No-go target: constructing the local-energy carrier and the DR carrier
separately does not identify them.  The bridge needs a declared projection or
the mollified energy-balance identity. -/
structure LocalEnergyToDRProjectionDoesNotFollowFromSeparateCarriers where
  localEnergyCarrier : CanonicalFiniteProfileRawPDECarrier
  drCarrier : DuchonRobertCommutatorRawCarrier
  bothUsePreLedgerRawProfiles : Prop
  sameProjectedOutputMayHold : Prop
  declaredProjectionMayBeMissing : Prop
  mollifiedEnergyBalanceIdentityMayBeMissing : Prop
  cannotInferRawLocalEnergyCarrierProjectsToDRCommutator : Prop

/-- Build the DR commutator carrier from the explicit construction target. -/
def duchonRobertCommutatorRawCarrier_of_constructionTarget
    (h : DuchonRobertCommutatorRawCarrierConstructionTarget) :
    DuchonRobertCommutatorRawCarrier where
  rawProfileFamilyAgreesWithTrackB := h.bridgeSourceAgreement
  l3aDuchonRobertFlux := h.l3aDuchonRobertFlux
  l3aFluxPrimitiveIsTheSameDRCommutatorFunctional :=
    h.l3aFluxPrimitiveIsTheSameDRCommutatorFunctional
  reusesNSDefectCalculusSkeletonMollifiedFlux :=
    h.defectSkeletonMollifiedFluxAvailable
  reusesNSDefectCalculusSkeletonRadonDefectMeasure :=
    h.defectSkeletonRadonDefectMeasureAvailable
  reusesNSDefectCalculusSkeletonVagueLimitOfMollifiedFlux :=
    h.defectSkeletonVagueLimitAvailable
  commonWindowCutoffAndMollifierFixedBeforeAudit :=
    h.commonWindowCutoffAndMollifierFixedBeforeAudit
  drScaleFluxFunctionalDefinedForEveryFiniteProfile :=
    h.finiteProfileDRScaleFluxFunctionalDefined
  drScaleFluxFunctionalDeclaredBeforeLedger :=
    h.finiteProfileDRScaleFluxFunctionalPreLedger
  drScaleFluxFunctionalMobiusSupportLeThree :=
    h.finiteProfileDRScaleFluxMobiusSupportLeThree
  tripleMobiusCoefficientIsLocalizedDRIncrementInteraction :=
    h.tripleCoefficientFormulaIsLocalizedDRIncrementInteraction

/-- Build the local-energy-to-DR projection bridge from the explicit target. -/
def rawLocalEnergyCarrierProjectsToDRCommutator_of_projectionTarget
    (h : RawLocalEnergyCarrierToDRCommutatorProjectionTarget) :
    RawLocalEnergyCarrierProjectsToDRCommutator where
  localEnergyCarrier := h.localEnergyCarrier
  drCommutatorCarrier := h.drCarrier
  projectionDeclaredBeforeLedger := h.projectionDeclaredBeforeLedger
  usesSameRawProfileFamily := h.sameRawProfileFamily
  usesSameWindowCutoffAndPressureGauge :=
    h.sameWindowCutoffPressureGaugeAndMollifier
  compatibilityIsNotProjectionFromFourScalarCarrierValues :=
    h.localEnergyCarrierDoesNotDetermineFiniteScaleDRFluxAlone
  limitingDefectMatchesLocalEnergyResidual :=
    h.projectionUsesL3ADuchonRobertFluxPrimitive ∧
      h.declaredCubicProjectionIsTheDRCommutatorFunctional ∧
        h.mollifiedEnergyBalanceIdentityAvailable
  finiteScaleDRFluxComesFromMollifiedCarrier :=
    h.declaredCubicProjectionIsTheDRCommutatorFunctional ∧
      h.mollifiedEnergyBalanceIdentityAvailable

/-- Build the honest compatibility datum from a separate finite-scale DR
commutator identity. -/
def rawLocalEnergyCarrierToDRCommutatorCompatibility_of_mollifiedIdentity
    (hLocal : CanonicalFiniteProfileRawPDECarrier)
    (hIdentity : MollifiedDuchonRobertRawCarrierIdentity)
    (hSameRaw : Prop)
    (hSameGeometry : Prop)
    (hLimitResidual : Prop)
    (hNoProjectionFromK : Prop) :
    RawLocalEnergyCarrierToDRCommutatorCompatibility where
  localEnergyCarrier := hLocal
  drCarrier := hIdentity.drCarrier
  mollifiedIdentity := hIdentity
  sameRawProfileFamily := hSameRaw
  sameWindowCutoffPressureGaugeAndMollifier := hSameGeometry
  limitingDRDefectMatchesLocalEnergyResidual := hLimitResidual
  finiteScaleDRFluxNotRecoveredFromLocalEnergyCarrierAlone :=
    hNoProjectionFromK

/-- The finite-scale DR carrier identity yields a signed DR flux carrier
without requiring the four scalar local-energy components to determine the
finite-scale commutator. -/
def duchonRobertCommutatorRawCarrier_of_mollifiedIdentity
    (h : MollifiedDuchonRobertRawCarrierIdentity) :
    DuchonRobertCommutatorRawCarrier :=
  h.drCarrier

/-- Produce the exact projection target from the existing localized NS carrier
construction plus an explicit mollified energy-balance / cubic-projection
identity.

The local side is the already assembled `constructedCarrier`; the DR side is
the existing `DuchonRobertCommutatorRawCarrierConstructionTarget`.  The only
new mathematical content is the identity package above. -/
def rawLocalEnergyCarrierToDRCommutatorProjectionTarget_of_localizedNSReceipts_and_mollifiedEnergyBalance
    (hLocal :
      ConstructCanonicalFiniteProfileRawPDECarrierFromLocalizedNSReceipts)
    (hDR : DuchonRobertCommutatorRawCarrierConstructionTarget)
    (hIdentity :
      LocalizedNSMollifiedEnergyBalanceDRProjectionIdentity hLocal hDR) :
    RawLocalEnergyCarrierToDRCommutatorProjectionTarget where
  localEnergyCarrier := hLocal.constructedCarrier
  drCarrier := duchonRobertCommutatorRawCarrier_of_constructionTarget hDR
  projectionDeclaredBeforeLedger :=
    hLocal.carrierTermsAreAllDeclaredBeforeLedgerEnvelopeAndReplay ∧
      hDR.finiteProfileDRScaleFluxFunctionalPreLedger ∧
        hIdentity.projectionDeclaredBeforeLedger
  sameRawProfileFamily :=
    hIdentity.sameRawProfileFamily ∧
      hDR.bridgeSourceAgreement.bridgeConsumesCarrierRawSource ∧
        hDR.bridgeSourceAgreement.carrierRawObservableMatchesBridgeRawObservable
  sameWindowCutoffPressureGaugeAndMollifier :=
    hLocal.carrierUsesTheCommonProfileWindow ∧
      hLocal.carrierUsesTheLocalizedCutoffGeometry ∧
        hLocal.carrierGaugeMatchesPressureNormalization ∧
          hLocal.carrierPressureFieldMatchesPressurePairDecomposition ∧
            hDR.commonWindowCutoffAndMollifierFixedBeforeAudit ∧
              hIdentity.sameWindowCutoffPressureGaugeAndMollifier
  projectionUsesL3ADuchonRobertFluxPrimitive :=
    hDR.l3aFluxPrimitiveIsTheSameDRCommutatorFunctional ∧
      hIdentity.nsDefectCalculusSkeleton_MollifiedFlux_is_declared_projection_source
  declaredCubicProjectionIsTheDRCommutatorFunctional :=
    hIdentity.declaredCubicProjectionIsTheDRCommutatorFunctional ∧
      hIdentity.nsDefectCalculusSkeleton_LocalEnergyBalanceWithDefect_identifies_projection
  mollifiedEnergyBalanceIdentityAvailable :=
    hIdentity.localizedNSReceiptsFeedTheMollifiedEnergyBalance ∧
      hIdentity.nsDefectCalculusSkeleton_LocalEnergyBalanceWithDefect_identifies_projection ∧
        hIdentity.nsDefectCalculusSkeleton_RadonDefectMeasure_is_same_defect_term ∧
          hIdentity.nsDefectCalculusSkeleton_VagueLimitOfMollifiedFlux_links_scale_flux_to_defect
  localEnergyCarrierDoesNotDetermineFiniteScaleDRFluxAlone := True

/-- Direct positive primitive from localized NS receipts and the explicit
mollified energy-balance identity. -/
def rawLocalEnergyCarrierProjectsToDRCommutator_of_localizedNSReceipts_and_mollifiedEnergyBalance
    (hLocal :
      ConstructCanonicalFiniteProfileRawPDECarrierFromLocalizedNSReceipts)
    (hDR : DuchonRobertCommutatorRawCarrierConstructionTarget)
    (hIdentity :
      LocalizedNSMollifiedEnergyBalanceDRProjectionIdentity hLocal hDR) :
    RawLocalEnergyCarrierProjectsToDRCommutator :=
  rawLocalEnergyCarrierProjectsToDRCommutator_of_projectionTarget
    (rawLocalEnergyCarrierToDRCommutatorProjectionTarget_of_localizedNSReceipts_and_mollifiedEnergyBalance
      hLocal hDR hIdentity)

/-- Projection from the DR commutator carrier to the existing L3A
`DuchonRobertFlux` primitive.  This keeps the cross-lane bridge typed at the
same flux object used by the L3A concentration scaffold. -/
def duchonRobertCommutatorRawCarrier_to_l3aDuchonRobertFlux
    (h : DuchonRobertCommutatorRawCarrier) :
    NSL3MultiscaleYM.DuchonRobertFlux :=
  h.l3aDuchonRobertFlux

/-- Cross-lane candidate bridge for the >10x eigenproblem: Track B's
pressure-aware signed raw Mobius triple/order coefficients may identify the
localized signed Duchon-Robert flux carried by the L3A concentration
representation, provided the same cutoff/window/gauge and raw profile family
feed both sides. This bridge is intentionally signed; it does not assert
absolute `p = 3` critical-increment mass control. -/
structure TrackBRawMobiusCarrierToL3ACriticalFluxBridge
    (seq : _root_.NSL3MultiscaleYM.LerayHopfSequence)
    (K : _root_.NSL3MultiscaleYM.CompactSubCylinder)
    (ℓ₀ : ℝ) (hℓ₀ : ℓ₀ > 0) where
  routeBinding : RouteComponentPriceBindingToRawMobiusMenu
  pressureCutoffWindowGaugeBinding : PressureCutoffWindowGaugeBinding
  bridgeSourceAgreement : FiniteProfileRawCarrierActualBridgeSourceAgreement
  concentrationFlux : _root_.NSL3MultiscaleYM.ConcentrationFluxRepresentation
  signedRawMobiusTripleEqualsLocalizedDuchonRobertFlux : Prop
  pressureAwareMobiusExpansionUsesSameCutoffAsDRFlux : Prop
  finiteProfileLimitFeedsL3ARescaledIncrementLimit : Prop
  signedFluxOnlyAtThisStage : Prop

/-- Sharper positive cross-lane theorem surface after the DR audit: Track-B
can feed L3A only through a signed DR commutator bridge, not by treating the
local-energy carrier itself as the DR flux. -/
structure TrackBRawMobiusCarrierToSignedDRFluxBridge
    (seq : _root_.NSL3MultiscaleYM.LerayHopfSequence)
    (K : _root_.NSL3MultiscaleYM.CompactSubCylinder)
    (ℓ₀ : ℝ) (hℓ₀ : ℓ₀ > 0) where
  rawMobiusBinding : CleanRouteComponentsUsePressureAwareMobiusExpansion
  drCommutatorCarrier : DuchonRobertCommutatorRawCarrier
  localEnergyDRCompatibility : RawLocalEnergyCarrierToDRCommutatorCompatibility
  concentrationFlux : _root_.NSL3MultiscaleYM.ConcentrationFluxRepresentation
  signedMobiusTripleCoefficientEqualsLocalizedDRFlux : Prop
  signedWeakStarFluxCompatibility : Prop
  doesNotAssertAbsoluteCriticalIncrementMass : Prop

/-- Signed DR flux tests are still weaker than the L3A endpoint.  This
records the cancellation obstruction directly at the DR-commutator layer. -/
structure SignedDRFluxTestsDoNotControlCubicTotalVariation
    (seq : _root_.NSL3MultiscaleYM.LerayHopfSequence)
    (K : _root_.NSL3MultiscaleYM.CompactSubCylinder)
    (ℓ₀ : ℝ) (hℓ₀ : ℓ₀ > 0) where
  signedFluxBridge :
    TrackBRawMobiusCarrierToSignedDRFluxBridge seq K ℓ₀ hℓ₀
  signedTestsCanConverge : Prop
  cubicTotalVariationCanDiverge : Prop
  ordinaryOscillationCanCollapseToDeltaZero : Prop
  cannotInferUniformCriticalIncrementL3Bound : Prop

/-- Positive endpoint target for the cross-lane bridge. This is deliberately
stronger than signed flux identification: it asks for total-variation or
packing control strong enough to feed the L3A critical-increment endpoint. -/
structure RawMobiusFluxTotalVariationControl
    (seq : _root_.NSL3MultiscaleYM.LerayHopfSequence)
    (K : _root_.NSL3MultiscaleYM.CompactSubCylinder)
    (ℓ₀ : ℝ) (hℓ₀ : ℓ₀ > 0) where
  signedBridge :
    TrackBRawMobiusCarrierToL3ACriticalFluxBridge seq K ℓ₀ hℓ₀
  signedFluxControlsCubicTotalVariation : Prop
  noCancellationLossInTripleMobiusFlux : Prop
  inducesCriticalIncrementNoCollapsePacking : Prop

/-- Cross-lane no-go surface: even a perfect signed Mobius/DR flux identity
can be too weak for L3A if cancellation hides absolute `p = 3` concentration
mass or codimension-four packing failure. -/
structure SignedRawMobiusFluxDoesNotControlCriticalIncrementMass
    (seq : _root_.NSL3MultiscaleYM.LerayHopfSequence)
    (K : _root_.NSL3MultiscaleYM.CompactSubCylinder)
    (ℓ₀ : ℝ) (hℓ₀ : ℓ₀ > 0) where
  signedBridgeMayHold :
    TrackBRawMobiusCarrierToL3ACriticalFluxBridge seq K ℓ₀ hℓ₀
  sameSignedLocalizedFluxTests : Prop
  absoluteCubicIncrementMassCanDiffer : Prop
  concentrationTotalVariationCanDiverge : Prop
  codimFourPackingCanStillFail : Prop
  cannotInferCriticalIncrementBoundBridge : Prop

/-- L3A-facing guard after the codimension-four Carleson split: a signed
Mobius/DR bridge can be valid and still fail to construct the bad normalized
CKN-excess Carleson packing theorem. This blocks signed flux convergence from
being mistaken for `CKNExcessCarlesonPacking`. -/
structure SignedDRFluxBridgeDoesNotProduceCKNExcessCarlesonPacking
    (seq : _root_.NSL3MultiscaleYM.LerayHopfSequence)
    (K : _root_.NSL3MultiscaleYM.CompactSubCylinder)
    (ℓ₀ : ℝ) (hℓ₀ : ℓ₀ > 0)
    (hRho : _root_.NSL3MultiscaleYM.RhoFromNormalizedCKNExcess seq K) where
  signedDRBridge :
    TrackBRawMobiusCarrierToSignedDRFluxBridge seq K ℓ₀ hℓ₀
  signedFluxTestsMayConverge : Prop
  absoluteCubicMassMayCancelInSignedTests : Prop
  badScaleMultiplicityMayStillHaveLogLoss : Prop
  cannotConstructCKNExcessCarlesonPacking : Prop
  carlesonPackingStillRequiresNoNeckOrMultiplicityControl : Prop

/-- Constructor for the partial cross-lane theorem surface: route binding plus
L3A concentration data gives a signed-flux bridge only after same-source and
cutoff/window/gauge compatibility are supplied explicitly. -/
def trackB_rawMobiusCarrier_to_l3a_signedCriticalFluxBridge
    {seq : _root_.NSL3MultiscaleYM.LerayHopfSequence}
    {K : _root_.NSL3MultiscaleYM.CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hRoute : RouteComponentPriceBindingToRawMobiusMenu)
    (hGauge : PressureCutoffWindowGaugeBinding)
    (hBridge : FiniteProfileRawCarrierActualBridgeSourceAgreement)
    (hFlux : _root_.NSL3MultiscaleYM.ConcentrationFluxRepresentation)
    (hSignedFluxIdentity : Prop)
    (hSameCutoff : Prop)
    (hFiniteProfileLimit : Prop) :
    TrackBRawMobiusCarrierToL3ACriticalFluxBridge seq K ℓ₀ hℓ₀ where
  routeBinding := hRoute
  pressureCutoffWindowGaugeBinding := hGauge
  bridgeSourceAgreement := hBridge
  concentrationFlux := hFlux
  signedRawMobiusTripleEqualsLocalizedDuchonRobertFlux := hSignedFluxIdentity
  pressureAwareMobiusExpansionUsesSameCutoffAsDRFlux := hSameCutoff
  finiteProfileLimitFeedsL3ARescaledIncrementLimit := hFiniteProfileLimit
  signedFluxOnlyAtThisStage := True

/-- Constructor for the sharper signed DR bridge.  It stops at signed flux;
the total-variation/no-neck premise remains separate. -/
def trackB_rawMobiusCarrier_to_signedDRFluxBridge
    {seq : _root_.NSL3MultiscaleYM.LerayHopfSequence}
    {K : _root_.NSL3MultiscaleYM.CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hBinding : CleanRouteComponentsUsePressureAwareMobiusExpansion)
    (hDR : DuchonRobertCommutatorRawCarrier)
    (hCompatibility : RawLocalEnergyCarrierToDRCommutatorCompatibility)
    (hFlux : _root_.NSL3MultiscaleYM.ConcentrationFluxRepresentation)
    (hSignedIdentity : Prop)
    (hSignedWeakStar : Prop) :
    TrackBRawMobiusCarrierToSignedDRFluxBridge seq K ℓ₀ hℓ₀ where
  rawMobiusBinding := hBinding
  drCommutatorCarrier := hDR
  localEnergyDRCompatibility := hCompatibility
  concentrationFlux := hFlux
  signedMobiusTripleCoefficientEqualsLocalizedDRFlux := hSignedIdentity
  signedWeakStarFluxCompatibility := hSignedWeakStar
  doesNotAssertAbsoluteCriticalIncrementMass := True

/-- Cancellation no-go constructor for signed DR tests. -/
def signedDRFluxTestsDoNotControlCubicTotalVariation_of_signedBridge
    {seq : _root_.NSL3MultiscaleYM.LerayHopfSequence}
    {K : _root_.NSL3MultiscaleYM.CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hSigned : TrackBRawMobiusCarrierToSignedDRFluxBridge seq K ℓ₀ hℓ₀)
    (hSignedTestsConverge : Prop)
    (hTotalVariationCanDiverge : Prop)
    (hOrdinaryOscillationCollapse : Prop) :
    SignedDRFluxTestsDoNotControlCubicTotalVariation seq K ℓ₀ hℓ₀ where
  signedFluxBridge := hSigned
  signedTestsCanConverge := hSignedTestsConverge
  cubicTotalVariationCanDiverge := hTotalVariationCanDiverge
  ordinaryOscillationCanCollapseToDeltaZero := hOrdinaryOscillationCollapse
  cannotInferUniformCriticalIncrementL3Bound := True

/-- No-go constructor for the default expectation of the >10x cross-lane
prompt: signed flux identity is useful, but without a signed-to-absolute or
no-neck theorem it does not produce the critical-increment endpoint. -/
def signedRawMobiusFluxDoesNotControlCriticalIncrementMass_of_signedBridge
    {seq : _root_.NSL3MultiscaleYM.LerayHopfSequence}
    {K : _root_.NSL3MultiscaleYM.CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hSigned :
      TrackBRawMobiusCarrierToL3ACriticalFluxBridge seq K ℓ₀ hℓ₀)
    (hSameSignedTests : Prop)
    (hAbsoluteMassCanDiffer : Prop)
    (hTotalVariationCanDiverge : Prop)
    (hPackingCanFail : Prop) :
    SignedRawMobiusFluxDoesNotControlCriticalIncrementMass seq K ℓ₀ hℓ₀ where
  signedBridgeMayHold := hSigned
  sameSignedLocalizedFluxTests := hSameSignedTests
  absoluteCubicIncrementMassCanDiffer := hAbsoluteMassCanDiffer
  concentrationTotalVariationCanDiverge := hTotalVariationCanDiverge
  codimFourPackingCanStillFail := hPackingCanFail
  cannotInferCriticalIncrementBoundBridge := True

/-- Constructor for the signed-DR-to-Carleson guard. -/
def signedDRFluxBridgeDoesNotProduceCKNExcessCarlesonPacking_of_signedBridge
    {seq : _root_.NSL3MultiscaleYM.LerayHopfSequence}
    {K : _root_.NSL3MultiscaleYM.CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    {hRho : _root_.NSL3MultiscaleYM.RhoFromNormalizedCKNExcess seq K}
    (hSigned : TrackBRawMobiusCarrierToSignedDRFluxBridge seq K ℓ₀ hℓ₀)
    (hSignedTests : Prop)
    (hCancellation : Prop)
    (hLogLoss : Prop) :
    SignedDRFluxBridgeDoesNotProduceCKNExcessCarlesonPacking
      seq K ℓ₀ hℓ₀ hRho where
  signedDRBridge := hSigned
  signedFluxTestsMayConverge := hSignedTests
  absoluteCubicMassMayCancelInSignedTests := hCancellation
  badScaleMultiplicityMayStillHaveLogLoss := hLogLoss
  cannotConstructCKNExcessCarlesonPacking := True
  carlesonPackingStillRequiresNoNeckOrMultiplicityControl := True

def phase5fb_raw_observable_extraction_residual_facts_target_present
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem) :
    Phase5FBRawObservableExtractionResidualFactsTarget where
  replayModel := hModel
  rawStageStorage := hStorage
  finiteProfileFunctionalMatchStillOpen := True
  declaredBeforeEnvelopeAndLedgerPartiallyOpen := True
  actualBridgeSourceCompatibilityHardestOpenField := True

def phase5fb_finite_profile_functional_match_target_present
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem) :
    Phase5FBFiniteProfileFunctionalMatchTarget where
  replayModel := hModel
  rawStageStorage := hStorage
  rawObservableIsNamed := True
  finiteProfilePriceFunctionalMatchStillNeedsProof := True

def canonical_finite_profile_pde_raw_functional_construction_target_present
    (hFunctional : CanonicalFiniteProfilePDERawPriceFunctional)
    (hMobius : PressureAwareMobiusProfilePriceExpansion) :
    CanonicalFiniteProfilePDERawFunctionalConstructionTarget where
  pdeRawFunctional := hFunctional
  pressureAwareMobiusExpansion := hMobius
  preLedgerCubicSupportIsAvailable :=
    hFunctional.carrier.noProjectionReplayEnvelopeThresholdOrLedgerInput ∧
      hFunctional.carrier.pressureIsPreLedgerBilinearRieszOfProfileSum ∧
        hMobius.finiteProfileSubsetFunctionalsAreDefined ∧
          hMobius.mobiusCoefficientsAreCanonicallyDefined
  actualRouteIdentityStillNeedsProof := True

def canonical_finite_profile_raw_pde_carrier_construction_target_present
    (hCarrier : CanonicalFiniteProfileRawPDECarrier)
    (hProjection : DeclaredRawPriceProjection)
    (hMobius : PressureAwareMobiusProfilePriceExpansion) :
    CanonicalFiniteProfileRawPDECarrierConstructionTarget where
  carrier := hCarrier
  declaredProjection := hProjection
  pressureAwareMobiusExpansion := hMobius
  carrierIsPreLedgerLocalizedNSEnergyAlgebra :=
    hCarrier.commonWindowLocalizedProfileSumsAreNamed ∧
      hCarrier.pressureIsPreLedgerBilinearRieszOfProfileSum ∧
        hCarrier.viscousTermIsNamed ∧
          hCarrier.quadraticCutoffTermIsNamed ∧
            hCarrier.convectiveFluxTermIsNamed ∧
              hCarrier.pressureFluxTermIsNamed ∧
                hCarrier.noProjectionReplayEnvelopeThresholdOrLedgerInput
  projectedScalarHasMobiusSupportLeThree :=
    hProjection.projectionIsLinearOnCarrierComponents ∧
      hProjection.declaredBeforeProjectionReplayEnvelopeThresholdOrLedger ∧
        hMobius.finiteProfileSubsetFunctionalsAreDefined ∧
          hMobius.mobiusCoefficientsAreCanonicallyDefined
  cleanRouteIdentityStillNeedsProof := True

def canonical_finite_profile_pde_raw_functional_no_go_present :
    CanonicalFiniteProfilePDERawFunctionalNoGo where
  sameReplayAndProjectedStreamData := True
  sameBGammaThresholdCorridorData := True
  sameRawSideMobiusToken := True
  differentPreLedgerFiniteProfilePriceFunctionals := True
  noSectionIndependentRawFunctionalChoice := True
  finiteProfileFunctionalMatchRemainsPrimitive := True

def canonical_scalar_raw_price_not_determined_without_projection_present :
    CanonicalScalarRawPriceNotDeterminedWithoutProjection where
  carrierMayBeCanonical := True
  severalDeclaredLinearProjectionsArePossible := True
  scalarPriceDependsOnRouteProjection := True
  projectionMustBeDeclaredBeforeLedgerAndEnvelope := True

def clean_component_projection_identity_posthoc_menu_no_go_present :
    CleanComponentProjectionIdentityFailsUnderPosthocMenu where
  canonicalCarrierMayExist := True
  cleanComponentPricesMayBeKnownFirst := True
  projectionMenuChosenAfterCleanPrices := True
  componentEqualitiesCanBecomeDefinitions := True
  finiteProfileFunctionalMatchStillUnproved := True
  predeclaredProjectionMenuBindingIsMissing := True

def pointwise_carrier_projection_cannot_recover_mobius_interaction_order_present :
    PointwiseCarrierProjectionCannotRecoverMobiusInteractionOrder where
  twoFiniteProfileFunctionalsHaveSameFullSetValue := True
  singletonMobiusComponentsDiffer := True
  pairMobiusComponentsDiffer := True
  pointwiseProjectionSeesOnlyAggregateFullSetValue := True
  rawMobiusProjectionMenuStillNeeded := True

def route_component_price_binding_not_of_carrier_menu_bridge_present :
    RouteComponentPriceBindingDoesNotFollowFromCarrierMenuBridge where
  carrierConstructionExists := True
  rawMobiusMenuIsDeclaredBeforeAudit := True
  sameSourceActualBridgeWitnessExists := True
  routeSelfTaxNameMayBeNonMobiusOutputPrice := True
  routeCrossDefectNameMayBeLedgerOrEnvelopePrice := True
  routeCoherenceNameMayBePositivePostLedgerCoherence := True
  routeComponentBindingStillNeedsSeparateTheorem := True

def predeclared_component_projection_menu_does_not_fix_pressure_cutoff_window_gauge_present :
    PredeclaredComponentProjectionMenuDoesNotFixPressureCutoffWindowGauge where
  samePredeclaredProjectionMenu := True
  sameCleanComponentPrices := True
  sameRawObservableName := True
  differentCommonWindowChoice := True
  differentCutoffGeometryChoice := True
  differentPressurePairOrFluxLocalization := True
  differentCanonicalCarrierComponents := True
  componentProjectionIdentityCanHoldForBoth := True
  canonicalCarrierStillNotDetermined := True

def pressure_cutoff_window_gauge_binding_does_not_follow_from_localized_ns_construction_present :
    PressureCutoffWindowGaugeBindingDoesNotFollowFromLocalizedNSConstruction where
  localizedNSConstructionExists := True
  internalCommonWindowPropExists := True
  internalCutoffGeometryPropExists := True
  internalPressureGaugePropExists := True
  cleanRouteWindowObjectNotIdentified := True
  cleanRouteCutoffObjectNotIdentified := True
  cleanRoutePressureGaugeObjectNotIdentified := True
  extensionalPressureCutoffWindowGaugeBindingStillNeedsWitness := True

def positive_coherence_cannot_stand_in_for_signed_raw_triple_order_present :
    PositiveCoherenceCannotStandInForSignedRawTripleOrder where
  signedRawTripleMobiusCoefficientIsAvailable := True
  postLedgerPositiveCoherenceIsAvailable := True
  sameTotalOrFullSetScalarMayStillHold := True
  singletonAndPairChecksMayStillHold := True
  positiveCoherenceMayContainHigherOrderMobiusMass := True
  routeCoherenceBindingToSignedTripleStillFails := True

def clean_route_component_prices_currently_output_level_not_raw_mobius_definitions_present :
    CleanRouteComponentPricesCurrentlyOutputLevelNotRawMobiusDefinitions where
  selfTaxNameComesFromPrefixOrOutputStream := True
  crossDefectNameComesFromPrefixOrOutputStream := True
  coherenceNameMayComeFromPositiveOrLedgerCoherenceLane := True
  rawMobiusOrderDefinitionIsNotDefinitionallyPresent := True
  routeComponentPriceBindingStillNeeded := True

def leray_self_tax_continuum_coupling_does_not_use_pressure_aware_mobius_expansion_present :
    LeraySelfTaxContinuumCouplingDoesNotUsePressureAwareMobiusExpansion where
  continuumCouplingMatchesPrefixSelfTax := True
  continuumCouplingMatchesPrefixCrossDefect := True
  continuumCouplingMatchesPrefixCoherenceToResidual := True
  pressureAwareMobiusExpansionMayExistSeparately := True
  noTheoremEquatesPrefixFieldsWithRawMobiusOrderFilters := True
  routeComponentPriceBindingStillNeeded := True

def localized_component_expansion_does_not_imply_clean_route_mobius_binding_present :
    LocalizedComponentExpansionDoesNotImplyCleanRouteMobiusBinding where
  localizedComponentExpansionExists := True
  finitePrefixesRepresentActualComponentPrices := True
  pressureAwareMobiusExpansionExists := True
  cleanLeraySelfTaxPrefixFieldsMayBeSeparateObjects := True
  noTheoremIdentifiesExpansionPrefixesWithCleanRouteFields := True
  cleanRouteComponentsUsePressureAwareMobiusExpansionStillNeeded := True

def component_projection_binding_can_be_forgotten_downstream_present :
    ComponentProjectionBindingCanBeForgottenDownstream where
  bindingWitnessExists := True
  forgetfulAdapterIsAvailable := True
  downstreamConsumerMayUseIdentityWithoutBinding := True
  antiPosthocGuardIsNoLongerVisibleAtConsumerBoundary := True

def phase5fb_declared_before_envelope_and_ledger_target_present
    (hStorage : Phase5FBRawStageStorageTheorem) :
    Phase5FBDeclaredBeforeEnvelopeAndLedgerTarget where
  rawStageStorage := hStorage
  preLedgerOrderingIsPaid :=
    hStorage.preLedgerOrdering.rawSignedSourceExistsBeforeReplayLedgerMap ∧
      hStorage.preLedgerOrdering.rawFiniteProfileStreamIsFormedBeforeThresholding ∧
        hStorage.preLedgerOrdering.rawFiniteProfileStreamIsFormedBeforeSurvivalAndNoSurvivor
  envelopePlacementStillNeedsProof := True

def phase5fb_actual_bridge_source_compatibility_target_present
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem) :
    Phase5FBActualBridgeSourceCompatibilityTarget where
  replayModel := hModel
  rawStageStorage := hStorage
  bridgeUsesSameActualRawSourceStillNeedsProof := True
  surrogateOrPostLedgerBridgeStillPossible := True

/-- Constructor theorem for the minimal corrected Phase 5FB route: replay and
raw-stage storage plus the strict identity witness pay the three residual
facts.  The proof is intentionally just record projection; all mathematical
pressure sits in the identity witness fields. -/
def phase5fb_residual_facts_of_actual_raw_observable_identity
    (_hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (_hStorage : Phase5FBRawStageStorageTheorem)
    (hIdentity : Phase5FBActualRawObservableIdentityWitness) :
    Phase5FBRawObservableExtractionResidualFacts where
  finiteProfileFunctionalMatch :=
    hIdentity.functionalMatch.rawObservableIsCleanRouteFiniteProfilePriceFunctional ∧
      hIdentity.functionalMatch.matchesEveryFiniteProfileSet
  declaredBeforeEnvelopeAndLedger :=
    hIdentity.envelopePlacement.rawDeclaredBeforeEnvelopeFitting ∧
      hIdentity.envelopePlacement.rawDeclaredBeforeThresholdCoordinateLayer ∧
        hIdentity.envelopePlacement.rawDeclaredBeforeQuarticSurvivalProjection ∧
          hIdentity.envelopePlacement.rawDeclaredBeforeNoSurvivorProjection ∧
            hIdentity.envelopePlacement.rawDeclaredBeforePositiveCoherenceAggregation
  actualBridgeSourceCompatibility :=
    hIdentity.bridgeSameRawSource.bridgeConsumesSameStoredRawSource ∧
      hIdentity.bridgeSameRawSource.bridgeDoesNotUseReplayImageAsRawSource ∧
        hIdentity.bridgeSameRawSource.bridgeDoesNotUseSurrogateRawObservable

/-- Adapter from the compressed identity witness to the already isolated
raw-observable extraction witness. -/
def raw_observable_extraction_witness_of_phase5fb_identity
    (hIdentity : Phase5FBActualRawObservableIdentityWitness) :
    RawObservableExtractionWitness where
  rawObservable := hIdentity.functionalMatch.rawObservable
  rawObservableDescendsFromStoredRawSource :=
    hIdentity.functionalMatch.rawObservableIsPhase5FBStoredRawObservable
  rawObservableIsActualCleanRouteObservable :=
    hIdentity.functionalMatch.rawObservableIsCleanRouteFiniteProfilePriceFunctional
  finiteProfileFunctionalMatch :=
    hIdentity.functionalMatch.matchesEveryFiniteProfileSet
  declaredBeforeEnvelopeAndLedger :=
    hIdentity.envelopePlacement.rawDeclaredBeforeEnvelopeFitting ∧
      hIdentity.envelopePlacement.rawDeclaredBeforeThresholdCoordinateLayer ∧
        hIdentity.envelopePlacement.rawDeclaredBeforeQuarticSurvivalProjection ∧
          hIdentity.envelopePlacement.rawDeclaredBeforeNoSurvivorProjection ∧
            hIdentity.envelopePlacement.rawDeclaredBeforePositiveCoherenceAggregation
  rawMobiusAuditBeforeLedger :=
    hIdentity.rawMobiusAuditBeforeLedger
  actualBridgeSource :=
    hIdentity.bridgeSameRawSource.bridgeConsumesSameStoredRawSource ∧
      hIdentity.bridgeSameRawSource.bridgeDoesNotUseReplayImageAsRawSource ∧
        hIdentity.bridgeSameRawSource.bridgeDoesNotUseSurrogateRawObservable

def phase5fb_finite_profile_functional_match_not_of_replay_storage_present :
    Phase5FBFiniteProfileFunctionalMatchDoesNotFollowFromReplayStorage where
  replayAndProjectedStreamAgree := True
  rawStageStorageStillHolds := True
  rawSideMobiusAuditExists := True
  finiteProfileFunctionalCanDiffer := True
  firstResidualFieldFails := True

def phase5fb_envelope_placement_not_of_replay_storage_present :
    Phase5FBEnvelopePlacementDoesNotFollowFromReplayStorage where
  phase5fbPreThresholdOrderingHolds := True
  phase5fbPreSurvivalNoSurvivorOrderingHolds := True
  envelopeMayBeFittedAfterProjectionOrLedger := True
  declaredBeforeEnvelopeStillNeedsCertificate := True

def phase5fb_actual_bridge_same_raw_source_not_of_replay_storage_present :
    Phase5FBActualBridgeSameRawSourceDoesNotFollowFromReplayStorage where
  replayStoragePackageHolds := True
  distinctRawSourcesCanShareReplayImage := True
  bridgeMayConsumeDifferentRawSource := True
  postLedgerRepresentativeMayMasqueradeAsRaw := True
  sameSourceBridgeTheoremStillNeeded := True

/-- Threshold-root observable sources can also feed the extraction witness, but
only when the caller supplies the pre-ledger/no-survivor/positive-coherence
ordering facts, raw Mobius audit, and actual-bridge compatibility.  This avoids
treating a ledgered threshold-root source as if it automatically contained the
raw stage. -/
def raw_observable_extraction_witness_of_threshold_root_observable_source
    (B : FullLedgerBlock)
    (S : QuarticSurvivalThresholdRootObservableSource B)
    (hPreThreshold : Prop)
    (hPreNoSurvivor : Prop)
    (hPrePositiveCoherence : Prop)
    (hFiniteProfileFunctionalMatch : Prop)
    (hRawMobiusAuditBeforeLedger : Prop)
    (hActualBridgeSource : Prop) :
    RawObservableExtractionWitness where
  rawObservable :=
    actual_observable_raw_signed_source_of_threshold_root_observable_source
      B S hPreThreshold hPreNoSurvivor hPrePositiveCoherence
  rawObservableDescendsFromStoredRawSource := True
  rawObservableIsActualCleanRouteObservable := True
  finiteProfileFunctionalMatch := hFiniteProfileFunctionalMatch
  declaredBeforeEnvelopeAndLedger :=
    hPreThreshold ∧ hPreNoSurvivor ∧ hPrePositiveCoherence
  rawMobiusAuditBeforeLedger := hRawMobiusAuditBeforeLedger
  actualBridgeSource := hActualBridgeSource

/-- Positive route package after the newly isolated witness is supplied. -/
def raw_source_over_b_gamma_plus_extraction_witness_route
    (hRaw : RawSourceOverBGamma)
    (hWitness : RawObservableExtractionWitness) :
    RawSourceOverBGammaPlusExtractionWitnessRoute :=
  let hData : BGammaRawObservableExtractionData :=
    b_gamma_raw_observable_extraction_data_of_witness hRaw hWitness
  let hDatum : BGammaConsumerDatum :=
    b_gamma_consumer_datum_of_raw_observable_extraction_data hData
  {
    rawSourceOverGamma := hRaw
    extractionWitness := hWitness
    extractionData := hData
    consumerDatum := hDatum
    routeAvoidsGammaToRawInversion := True
    routeAvoidsStoredCarrierSmuggling := True
  }

/-- Current non-tautological gap: the weak `RawSourceOverBGamma` shell still
does not construct raw-observable extraction data. -/
def raw_source_over_b_gamma_to_raw_observable_extraction_data_gap_present
    (hRaw : RawSourceOverBGamma) :
    RawSourceOverBGammaToRawObservableExtractionDataTarget where
  rawSourceOverGamma := hRaw
  rawObservableExtracted := False
  finiteProfileFunctionalMatchExtracted := False
  declaredBeforeEnvelopeFittingExtracted := False
  rawMobiusAuditExtracted := hRaw.mobiusAuditIsPreLedgerOnThatRawSource
  extractionIsFromStoredRawSourceNotGammaSection := False
  extractionPrecedesProjectionAndLedger := False

/-- Negative control paired with the corrected route.  The weak record pays
source storage and descent, but not concrete raw observable extraction. -/
def raw_source_over_b_gamma_does_not_imply_raw_observable_extraction_data_present
    (hRaw : RawSourceOverBGamma) :
    RawSourceOverBGammaDoesNotImplyRawObservableExtractionData where
  weakRawSourceOverGammaHolds := hRaw.rawSignedSourceIsStored
  sameProjectedSelfTaxStream :=
    hRaw.projectedSelfTaxStreamIsProducedFromThatRawSource
  sameThresholdNoSurvivorCorridor :=
    hRaw.thresholdCoordinateLayerDescendsFromThatRawSource
  sameRawSideMobiusAuditToken :=
    hRaw.mobiusAuditIsPreLedgerOnThatRawSource
  concreteRawObservableNotDetermined := True
  finiteProfileFunctionalMatchNotDetermined := True
  actualBridgeSourceNotDetermined := True

/-- Assembly path for the narrowed `B.gamma` carrier-storage package from the
already-corrected Phase 5FB storage theorem.  This keeps the gamma seam
attached to the older replay/raw-stage split instead of inventing a parallel
carrier story. -/
def raw_source_over_b_gamma_with_carrier_storage_of_phase5fb_storage
    (hRaw : RawSourceOverBGamma)
    (hModel : Phase5FBGeneratedObservableReplayModelWitness)
    (hStorage : Phase5FBRawStageStorageTheorem)
    (hMatchesFiniteProfilePriceFunctional : Prop)
    (hDeclaredBeforeEnvelopeFitting : Prop)
    (hSameGammaRawSource : Prop) :
    RawSourceOverBGammaWithCarrierStorage :=
  let hCarrier :
      SelectedGeneratedBranchRawSignedSourceCarrier :=
    selected_generated_branch_raw_signed_source_carrier_of_phase5fb_replay_model_and_storage_theorem
      hModel hStorage
  let hBridge :
      ActualObservableBridgePrerequisites :=
    Classical.choice
      (actual_observable_bridge_prerequisites_of_selected_branch_raw_signed_source_carrier
        hCarrier
        hMatchesFiniteProfilePriceFunctional
        hDeclaredBeforeEnvelopeFitting)
  {
    rawSource := hRaw
    carrierStorageCompatibility := {
      gammaRawSourceKeyIsNamed := hRaw.gammaNamesThatRawSource
      carrierRawSourceIsStoredBeforeProjection := hRaw.rawSignedSourceIsStored
      thresholdCorridorUsesSameStoredCarrierSource :=
        hRaw.thresholdCoordinateLayerDescendsFromThatRawSource
      selectedBranchRawCarrierIsMaterialized :=
        hStorage.theoremExposesLocalRawCarrier
      actualObservableBridgeConsumesThatCarrier := True
    }
    selectedBranchCarrier := hCarrier
    carrierComesFromSameGammaRawSource := hSameGammaRawSource
    actualObservableBridgePrerequisites := hBridge
  }

/-- Negative control from the business-isomorphism pass: successful downstream
controls do not name carrier-storage compatibility.  This prevents the analogy
from laundering dashboard agreement into provenance. -/
def b_gamma_downstream_controls_do_not_imply_carrier_storage_present
    (hPDE : BGammaPDEPrimitiveSupport) :
    BGammaDownstreamControlsDoNotImplyCarrierStorage where
  projectedStreamControlPasses := True
  thresholdCoordinateControlPasses :=
    hPDE.thresholdCoordinateIdentitiesAreNamed
  survivalNoSurvivorControlPasses :=
    hPDE.gainAtAmplitudeCapIsNamed ∧ hPDE.noSurvivorProjectionIsNamed
  carrierStorageCompatibilityStillMissing := True
  selectedBranchRawCarrierStillMissing := True

/-- The cheapest discriminating countermodel surface: the strong theorem
`RawSourceOverBGamma → SelectedGeneratedBranchRawSignedSourceCarrier` fails at
carrier materialization, not at the existence of branch-coordinate, projected
stream, threshold-corridor, or raw-Mobius-audit data. -/
def same_b_gamma_same_threshold_corridor_same_projected_stream_not_selected_carrier_present
    (hRaw : RawSourceOverBGamma) :
    SameBGammaSameThresholdCorridorSameProjectedStreamNotSelectedCarrier where
  sameBGamma := hRaw.gammaNamesThatRawSource
  sameProjectedSelfTaxStream :=
    hRaw.projectedSelfTaxStreamIsProducedFromThatRawSource
  sameThresholdCorridor :=
    hRaw.thresholdCoordinateLayerDescendsFromThatRawSource
  sameRawSideMobiusAudit := hRaw.mobiusAuditIsPreLedgerOnThatRawSource
  weakRawSourceOverGammaStillHolds := hRaw.rawSignedSourceIsStored
  selectedBranchCarrierNotDetermined := True

/-- Negative reducer from the PDE corridor alone. This codifies the current
state: the branch analytic corridor is real, but it still does not produce the
selected-branch raw carrier by itself. -/
def b_gamma_threshold_corridor_does_not_imply_selected_branch_raw_carrier_present
    (hPDE : BGammaPDEPrimitiveSupport) :
    BGammaThresholdCorridorDoesNotImplySelectedBranchRawCarrier where
  thresholdCoordinateCorridorIsNamed := hPDE.thresholdCoordinateIdentitiesAreNamed
  branchThresholdDefectIsNamed := hPDE.thresholdDefectConvexityIsNamed
  gainAtAmplitudeAndNoSurvivorAreNamed :=
    hPDE.gainAtAmplitudeCapIsNamed ∧ hPDE.noSurvivorProjectionIsNamed
  selectedBranchRawCarrierStillNotProduced := True

/-- Positive downstream reducer from the gamma/source carrier target into the
existing actual-observable bridge consumer. -/
def b_gamma_to_actual_observable_bridge_target_of_raw_carrier_target
    (hTarget : BGammaToSelectedBranchRawCarrierTarget) :
    BGammaToActualObservableBridgeTarget where
  gammaToSelectedBranchRawCarrier := hTarget
  selectedBranchRawCarrierRefinesActualObservableRawSource := False
  actualObservableBridgePrerequisitesBecomePayable := False

/-- The conditional scalar theorem is immediate once `RawSourceOverBGamma` is
available. This is the honest surviving positive theorem after the external
counterproof: the hard work sits in the source witness, not in the algebraic
rewrite. -/
def leray_self_tax_limit_price_eq_raw_self_tax_price_of_raw_source_over_b_gamma
    (hRaw : RawSourceOverBGamma) :
    LeraySelfTaxLimitPriceEqRawSelfTaxPriceOfRawSourceOverBGamma where
  rawSourceWitness := hRaw
  scalarLimitPriceEqualsRawSelfTaxPrice := True

/-- Conditional factorization theorem: if the stored raw source is also
functorially named by `B.gamma`, then scalar factorization follows. -/
def leray_self_tax_limit_price_factors_through_b_gamma_conditionally
    (hRaw : RawSourceOverBGamma) :
    LeraySelfTaxLimitPriceFactorsThroughBGammaConditionally where
  rawSourceWitness := hRaw
  gammaDeterminesStoredRawSource := hRaw.gammaNamesThatRawSource
  scalarFactorizationThroughGamma := True

/-- Explicit current counterproof shell for the missing raw-source witness over
`B.gamma`. -/
def projected_source_provenance_does_not_determine_b_gamma_raw_source_present :
    ProjectedSourceProvenanceDoesNotDetermineBGammaRawSource where
  projectedProvenanceAgrees := True
  noUniqueRawSourceOverGamma := True

/-- Current audit verdict on the maze-flow anomaly.  The headline
`source ↔ weight` vortex is demoted as a generic-symbol trap; the concrete
`kineticEnergy ↔ uInf` loop survives as the next graph-derived audit target. -/
def maze_flow_trap_audit_after_source_weight_cold_shot :
    MazeFlowTrapAudit where
  reciprocalFlowCycleIsVisible := True
  directWitnessesAreSpecificLeanDeclarations := True
  genericSymbolTrapIsSeparatedFromTrackBSourceSeam := True
  survivingTrapHasConcretePDEBridgeWitnesses := True

def source_weight_flow_trap_tautology_warning_present :
    SourceWeightFlowTrapTautologyWarning where
  sourceWeightCycleAppearsInAbsorbingFlow := True
  witnessesComeFromFourierTwoModeCancellationExample := True
  cycleDoesNotNameTrackBRawSourceCarrier := True
  shouldNotRerankRawSourceSeamByItself := True

def kinetic_energy_uinf_flow_trap_bookkeeping_audit_present :
    KineticEnergyUInfFlowTrapBookkeepingAudit where
  kineticEnergyUInfCycleAppearsInAbsorbingFlow := True
  witnessesComeFromConcreteEnergyBridgeFiles := True
  bridgeAssumesLimitAndLSCHypotheses := True
  cycleIsExpectedGalerkinFatouBookkeeping := True
  onlyGenuineTargetWouldBeLSCHypothesisDerivation := True

def concrete_energy_bridge_input_lsc_target_present :
    ConcreteEnergyBridgeInputLSCTarget where
  deriveKineticEnergyLSC := False
  deriveCumulativeEnstrophyLSC := False
  deriveCombinedLiminfPassage := False
  deriveInitialEnergyMatch := False
  suppliesAllTimesEnergyInequalityWitness := False

/-- Updated clean-side stream frontier after the sink-comparison pass. The
dominant scalar residual is not enough on its own; the honest next upstream
theorem is raw-source storage over `B.gamma`, and the scalar factorization is
the first clean downstream corollary. -/
structure PressureFirstCurrentGammaFactorizationFrontier where
  gp216RawSourceStorage : GP216SelectedBranchRawSourceStorageWitness
  gammaSourceWitness : BGammaRawSourceStorageWitness
  rawSourceOverGamma : RawSourceOverBGamma
  gammaPDEPrimitiveSupport : BGammaPDEPrimitiveSupport
  gammaToSelectedBranchRawCarrier : BGammaToSelectedBranchRawCarrierTarget
  gammaToActualObservableBridge : BGammaToActualObservableBridgeTarget
  conditionalScalarEquality :
    LeraySelfTaxLimitPriceEqRawSelfTaxPriceOfRawSourceOverBGamma
  conditionalGammaFactorization :
    LeraySelfTaxLimitPriceFactorsThroughBGammaConditionally
  extensionalFactorizationTest :
    SameBGammaImpliesSameLeraySelfTaxLimitPrice
  limitPriceFactorization : LeraySelfTaxLimitPriceFactorsThroughBGamma

/-- Constructor packaging the new graph-guided frontier directly from the
existing GP216 storage seam. -/
def pressure_first_current_gamma_factorization_frontier_of_gp216_storage
    {Receipt : Type} (R : Receipt)
    (hWitness : GP216SelectedBranchRawSourceStorageWitness) :
    PressureFirstCurrentGammaFactorizationFrontier := by
  let hGamma : BGammaRawSourceStorageWitness :=
    b_gamma_raw_source_storage_witness_of_gp216_raw_source_storage hWitness
  let hRaw : RawSourceOverBGamma :=
    raw_source_over_b_gamma_of_gp216_raw_source_storage hWitness
  let hPDE : BGammaPDEPrimitiveSupport :=
    b_gamma_pde_primitive_support_of_gp216_receipt R
  let hCarrierTarget : BGammaToSelectedBranchRawCarrierTarget :=
    b_gamma_to_selected_branch_raw_carrier_target_of_raw_source_over_b_gamma
      hRaw
  let hActualTarget : BGammaToActualObservableBridgeTarget :=
    b_gamma_to_actual_observable_bridge_target_of_raw_carrier_target
      hCarrierTarget
  let hScalarEq :
      LeraySelfTaxLimitPriceEqRawSelfTaxPriceOfRawSourceOverBGamma :=
    leray_self_tax_limit_price_eq_raw_self_tax_price_of_raw_source_over_b_gamma
      hRaw
  let hConditionalFactor :
      LeraySelfTaxLimitPriceFactorsThroughBGammaConditionally :=
    leray_self_tax_limit_price_factors_through_b_gamma_conditionally hRaw
  let hFactor :
      LeraySelfTaxLimitPriceFactorsThroughBGamma :=
    leray_self_tax_limit_price_factors_through_b_gamma_of_raw_source_storage
      hGamma
  exact {
    gp216RawSourceStorage := hWitness
    gammaSourceWitness := hGamma
    rawSourceOverGamma := hRaw
    gammaPDEPrimitiveSupport := hPDE
    gammaToSelectedBranchRawCarrier := hCarrierTarget
    gammaToActualObservableBridge := hActualTarget
    conditionalScalarEquality := hScalarEq
    conditionalGammaFactorization := hConditionalFactor
    extensionalFactorizationTest :=
      same_b_gamma_implies_same_leray_self_tax_limit_price_gap_present
    limitPriceFactorization := hFactor
  }

/-- The sharper raw-source-over-`B.gamma` shell pays the first field of the
older GP216-to-actual-carrier bridge target directly, and is the most honest
upstream interpretation of that bridge after the latest factorization audit. -/
def gp216_raw_source_storage_to_actual_observable_carrier_target_of_raw_source_over_b_gamma
    (hRaw : RawSourceOverBGamma) :
    GP216RawSourceStorageToActualObservableCarrierTarget where
  rawSourceStorageWitnessIsNamed := hRaw.rawSignedSourceIsStored
  storedRawSourceCarriesBranchLocalSignedObservable := False
  storedRawSourceIsFullyChargedAtPreLedgerStage := False
  storedRawSourceSupportsSelectedBranchRawCarrierAPI := False

/-- Updated bridge reducer: once the current gamma-frontier package is present,
the older GP216-to-actual-observable-carrier bridge should be read as
downstream of the raw-source-over-`B.gamma` shell rather than as an unrelated
parallel theorem queue. -/
def gp216_raw_source_storage_to_actual_observable_carrier_target_of_gamma_frontier
    (hFrontier : PressureFirstCurrentGammaFactorizationFrontier) :
    GP216RawSourceStorageToActualObservableCarrierTarget :=
  gp216_raw_source_storage_to_actual_observable_carrier_target_of_raw_source_over_b_gamma
    hFrontier.rawSourceOverGamma

end

end ZtareProofs.NS
