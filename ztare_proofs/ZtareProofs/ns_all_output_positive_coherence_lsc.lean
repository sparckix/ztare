import Mathlib.Tactic
import ZtareProofs.ns_gp216_limit_lsc_obligation
import ZtareProofs.ns_profile_limit_lsc_bossfight
import ZtareProofs.ns_beat_backscatter_coherence_charge
import ZtareProofs.ns_gp216_positive_coherence_kernel
import ZtareProofs.ns_low_beat_weighted_l1_receipt

/-!
# All-output positive-coherence/L1 LSC adapter

This module is proof-facing glue for the continuum all-output
positive-coherence/L1 lower-semicontinuity obligation.

It does not prove Navier-Stokes regularity.  The analytic content remains in
explicit receipt fields:

* the LP/profile topology and all output atoms are fixed before payoff scoring;
* finite prefixes charge the all-output L1/coherence price;
* the declared continuum price is lower-semicontinuous in the epsilon/eventual
  sense used by `ContinuumLPPriceLowerSemicontinuous`;
* hidden source-coordinate L2 pricing is recorded as insufficient by a scalar
  anti-tautology witness.
-/

namespace ZtareProofs.NS

noncomputable section

universe u

/-- View a continuum all-output/coherence stream through the older profile
limit interface.

The payoff is constant across prefixes because the continuum stream has one
declared smooth-candidate payoff.  The prefix prices are the all-output
LP/profile prefix prices, and the limit price is the declared global self-tax
target. -/
def profileLimitStreamOfAllOutputPositiveCoherence
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) :
    ProfileLimitStream where
  prefixPayoff := fun _ => S.smoothCandidatePayoff
  prefixPrice := fun n => continuumLPPrefixPrice S n
  payoffLimit := S.smoothCandidatePayoff
  priceLimit := continuumGlobalSelfTaxTarget S

/-- Extra direction needed to reuse the older `ProfileLimitLSCCertificate`.

The GP-216 continuum receipt uses the `target <= prefix + eps eventually`
lower-semicontinuity direction plus a liminf upper bound and budget bridge.
The older boss-fight certificate instead asks every finite prefix price to be
below the limit price.  When an analytic instantiation proves this stronger
prefix-dominated envelope, the same all-output receipt can be viewed as an
ordinary profile-limit LSC certificate. -/
def AllOutputPrefixPriceDominatedByLimit
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) : Prop :=
  ∀ n : ℕ,
    continuumLPPrefixPrice S n ≤ continuumGlobalSelfTaxTarget S

/-- Monotone prefix-price convergence supplies the stronger
prefix-dominated-by-limit envelope used by the older profile-limit LSC
interface. -/
theorem all_output_prefix_price_dominated_by_limit_of_monotone_tendsto
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (hmono :
      Monotone (fun n : ℕ => continuumLPPrefixPrice S n))
    (htendsto :
      Filter.Tendsto
        (fun n : ℕ => continuumLPPrefixPrice S n)
        Filter.atTop
        (nhds (continuumGlobalSelfTaxTarget S))) :
    AllOutputPrefixPriceDominatedByLimit S := by
  intro n
  exact hmono.ge_of_tendsto htendsto n

/-- Source-consuming scalar edge from the positive-coherence kernel into the
declared all-output prefix price. -/
theorem all_output_prefix_payoff_le_price_of_positive_coherence_kernel
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (N : ℕ)
    (K : PositiveCoherenceKernelStream)
    (hpayoff_to_kernel :
      S.smoothCandidatePayoff ≤ positiveCoherencePrefixTax K N)
    (hkernel_to_prefix :
      positiveCoherencePrefixPrice K N ≤ continuumLPPrefixPrice S N) :
    S.smoothCandidatePayoff ≤ continuumLPPrefixPrice S N :=
  hpayoff_to_kernel.trans
    ((positive_coherence_prefix_tax_le_price K N).trans
      hkernel_to_prefix)

/-- Build one all-output prefix charge from the positive-coherence kernel.

This is the compiler-checked form of the graph-surfaced three-profile
expansion: the scalar kernel may be used only in the orientation where the
assembled tax is below the positive-coherence price, and that price is then
embedded into the declared continuum prefix price. -/
def prefix_all_output_coherence_charge_of_positive_coherence_kernel
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (N : ℕ)
    (K : PositiveCoherenceKernelStream)
    (hbranch_self_tax_charged : Prop)
    (hbranch_self_tax_charged_paid :
      hbranch_self_tax_charged)
    (hcross_profile_defect_charged : Prop)
    (hcross_profile_defect_charged_paid :
      hcross_profile_defect_charged)
    (hpositive_coherence_charged : Prop)
    (hpositive_coherence_charged_paid :
      hpositive_coherence_charged)
    (hall_output_l1_price_charged : Prop)
    (hall_output_l1_price_charged_paid :
      hall_output_l1_price_charged)
    (hphysical_reserve_charged : Prop)
    (hphysical_reserve_charged_paid :
      hphysical_reserve_charged)
    (hresidual_terms_charged : Prop)
    (hresidual_terms_charged_paid :
      hresidual_terms_charged)
    (hpayoff_to_kernel :
      S.smoothCandidatePayoff ≤ positiveCoherencePrefixTax K N)
    (hkernel_to_prefix :
      positiveCoherencePrefixPrice K N ≤ continuumLPPrefixPrice S N) :
    PrefixAllOutputCoherenceCharge S N where
  branch_self_tax_charged := hbranch_self_tax_charged
  branch_self_tax_charged_paid := hbranch_self_tax_charged_paid
  cross_profile_defect_charged := hcross_profile_defect_charged
  cross_profile_defect_charged_paid := hcross_profile_defect_charged_paid
  positive_coherence_charged := hpositive_coherence_charged
  positive_coherence_charged_paid := hpositive_coherence_charged_paid
  all_output_l1_price_charged := hall_output_l1_price_charged
  all_output_l1_price_charged_paid := hall_output_l1_price_charged_paid
  physical_reserve_charged := hphysical_reserve_charged
  physical_reserve_charged_paid := hphysical_reserve_charged_paid
  residual_terms_charged := hresidual_terms_charged
  residual_terms_charged_paid := hresidual_terms_charged_paid
  prefix_payoff_le_price :=
    all_output_prefix_payoff_le_price_of_positive_coherence_kernel
      S N K hpayoff_to_kernel hkernel_to_prefix

/-- All-output positive-coherence/L1 receipt as a `ProfileLimitLSCCertificate`,
under the stronger prefix-price-dominated-by-limit envelope required by that
older interface. -/
def profile_lsc_certificate_of_all_output_positive_coherence
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (R : AllOutputPositiveCoherenceLSCReceipt S)
    (hprefix :
      AllOutputPrefixPriceDominatedByLimit S) :
    ProfileLimitLSCCertificate
      (profileLimitStreamOfAllOutputPositiveCoherence S) where
  finite_prefix_no_survivor := by
    intro n
    exact (R.prefix_charge n).prefix_payoff_le_price
  payoff_approximated_by_prefix := by
    intro ε hε
    refine ⟨0, ?_⟩
    dsimp [profileLimitStreamOfAllOutputPositiveCoherence]
    linarith
  prefix_price_lsc := by
    intro n
    exact hprefix n

/-- Existing profile-limit boss-fight conclusion obtained from the all-output
receipt plus the stronger prefix-price envelope. -/
theorem all_output_positive_coherence_payoff_le_global_target_via_profile_lsc
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (R : AllOutputPositiveCoherenceLSCReceipt S)
    (hprefix :
      AllOutputPrefixPriceDominatedByLimit S) :
    S.smoothCandidatePayoff ≤ continuumGlobalSelfTaxTarget S := by
  exact
    profile_limit_no_survivor_of_lsc_certificate
      (profileLimitStreamOfAllOutputPositiveCoherence S)
      (profile_lsc_certificate_of_all_output_positive_coherence
        S R hprefix)

/-- The GP-216 receipt also packages directly into the existing no-smooth-escape
theorem, without strengthening it to the older prefix-dominated profile-limit
shape. -/
theorem no_smooth_escape_of_all_output_positive_coherence_lsc_receipt
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (R : AllOutputPositiveCoherenceLSCReceipt S) :
    ¬ ContinuumLPSmoothEscapeCandidate S :=
  no_smooth_escape_candidate_of_all_output_positive_coherence_lsc S R

/-- Concrete falsifier for the output/coherence price lower-semicontinuity
field.

It says that, in the fixed all-output topology and fixed atom system, there is
a positive price gap that reappears arbitrarily far out in the prefix stream:
the declared global target is still strictly above the charged all-output
prefix price plus that gap. -/
structure AllOutputCoherencePriceLSCFailureFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) where
  fixed_topology : ContinuumLPUsesFixedTopology S
  fixed_atoms : FixedAllOutputLPBonyAtoms S
  gap : Real
  gap_pos : 0 < gap
  arbitrarily_late_underpriced_output_coherence :
    ∀ N : ℕ, ∃ n : ℕ,
      N ≤ n ∧
        continuumLPPrefixPrice S n + gap <
          continuumGlobalSelfTaxTarget S

/-- The falsifier is exactly incompatible with the epsilon/eventual LSC
obligation used by the continuum receipt. -/
theorem no_continuum_lp_price_lsc_of_all_output_coherence_falsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (F : AllOutputCoherencePriceLSCFailureFalsifier S) :
    ¬ ContinuumLPPriceLowerSemicontinuous S := by
  intro hlsc
  have hhalf : 0 < F.gap / 2 := by
    nlinarith [F.gap_pos]
  obtain ⟨N, hN⟩ := hlsc F.fixed_topology (F.gap / 2) hhalf
  obtain ⟨n, hn_tail, hn_underpriced⟩ :=
    F.arbitrarily_late_underpriced_output_coherence N
  have hn_lsc :
      continuumGlobalSelfTaxTarget S ≤
        continuumLPPrefixPrice S n + F.gap / 2 :=
    hN n hn_tail
  linarith

/-- Therefore a single tail-recurring output/coherence price-drop falsifier
rules out an alleged all-output positive-coherence/L1 LSC receipt. -/
theorem no_all_output_positive_coherence_lsc_receipt_of_falsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (F : AllOutputCoherencePriceLSCFailureFalsifier S) :
    AllOutputPositiveCoherenceLSCReceipt S → False := by
  intro R
  exact
    no_continuum_lp_price_lsc_of_all_output_coherence_falsifier
      S F R.price_lower_semicontinuous

/-- Bounded finite-prefix audit receipt for the all-output/coherence topology.

This records the status of a deterministic finite Fourier falsifier search
without promoting it to a continuum theorem.  The fields separate three facts:
the searched finite panel produced no all-output LSC falsifier, the hidden
source-L2 negative control stayed dangerous, and the surviving finite payoffs
were already priced by the declared output/coherence ledger. -/
structure AllOutputFinitePrefixAuditReceipt where
  atomsBuilt : ℕ
  symbolGroups : ℕ
  searchRows : ℕ
  falsifierCount : ℕ
  falsifier_count_zero : falsifierCount = 0
  boundedPricedSurvivalRows : ℕ
  maxSourceL2NormalizedGain : Real
  source_l2_negative_control_exceeds_unit :
    1 < maxSourceL2NormalizedGain
  maxSearchPayoffOverDeclaredFull : Real
  search_payoff_ratio_charged :
    maxSearchPayoffOverDeclaredFull ≤ 1
  bounded_priced_survivors_are_priced_by_declared_full_ledger : Prop
  no_continuum_theorem_claimed_from_bounded_search : Prop

/-- Deterministic asymptotic tail-escape panel receipt.

This records the Phase 5JC sequence/topology check: tail-recurring bounded
price escapes are allowed as negative controls only when a guard is invalid
(hidden source-L2, omitted positive coherence, or moving output atoms after
payoff).  A proof-facing falsifier must have valid fixed all-output topology
and still produce a recurring tail price gap. -/
structure AllOutputTailEscapePanelReceipt where
  scenariosChecked : ℕ
  validTailLSCFalsifierCount : ℕ
  invalidUnderchargedNegativeControls : ℕ
  chargedOrPricedPanels : ℕ
  valid_tail_lsc_falsifier_count_zero :
    validTailLSCFalsifierCount = 0
  negative_controls_exist :
    0 < invalidUnderchargedNegativeControls
  charged_panels_exist :
    0 < chargedOrPricedPanels
  all_valid_scope_panels_charge_tail_escape : Prop
  invalid_controls_fail_topology_or_coherence_guard : Prop
  no_continuum_theorem_claimed_from_sequence_panel : Prop

/-- Countable-prefix tail convergence for the declared all-output Gram price.

This is the concrete continuum-limit obligation exposed by Phase 5JC/5JF:
after the output atoms and Gram/coherence kernel are fixed, the finite-prefix
price must converge to the declared continuum target in that same topology.
It cannot be replaced by a hidden source-coordinate L2 budget or by moving the
output atoms after seeing payoff. -/
def AllOutputPrefixPriceTendsToDeclaredTarget
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) : Prop :=
  ∀ ε : Real, 0 < ε → ∃ N : ℕ, ∀ n : ℕ,
    N ≤ n →
      |continuumLPPrefixPrice S n -
        continuumGlobalSelfTaxTarget S| ≤ ε

/-- Cauchy version of the same tail obligation.

This is weaker than convergence to the declared target; it is useful as a
diagnostic because a Cauchy all-output Gram stream may still converge to the
wrong price if the global target was declared after payoff scoring. -/
def AllOutputPrefixPriceTailCauchy
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) : Prop :=
  ∀ ε : Real, 0 < ε → ∃ N : ℕ, ∀ m n : ℕ,
    N ≤ m →
      N ≤ n →
        |continuumLPPrefixPrice S m -
          continuumLPPrefixPrice S n| ≤ ε

/-- Metric Cauchy convergence of the prefix-price sequence supplies the
order-form tail Cauchy field used by all-output Gram control. -/
theorem all_output_prefix_price_tail_cauchy_of_cauchySeq
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (h :
      CauchySeq
        (fun n : ℕ => continuumLPPrefixPrice S n)) :
    AllOutputPrefixPriceTailCauchy S := by
  intro ε hε
  obtain ⟨N, hN⟩ := (Metric.cauchySeq_iff.mp h) ε hε
  refine ⟨N, ?_⟩
  intro m n hm hn
  have hdist :
      dist (continuumLPPrefixPrice S m)
        (continuumLPPrefixPrice S n) < ε :=
    hN m hm n hn
  rw [Real.dist_eq] at hdist
  exact le_of_lt hdist

/-- Metric convergence of the prefix prices to the predeclared continuum
target supplies the order-form target-convergence field used by the countable
all-output Gram receipt.

This is a small Mathlib-backed adapter, but it is load-bearing: analytic PDE
work often proves `Tendsto`, while the Track B proof spine consumes the
explicit eventually-`≤ ε` statement so the declared target cannot be swapped
after payoff scoring. -/
theorem all_output_prefix_price_tends_to_declared_target_of_tendsto
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (h :
      Filter.Tendsto
        (fun n : ℕ => continuumLPPrefixPrice S n)
        Filter.atTop
        (nhds (continuumGlobalSelfTaxTarget S))) :
    AllOutputPrefixPriceTendsToDeclaredTarget S := by
  intro ε hε
  obtain ⟨N, hN⟩ := (Metric.tendsto_atTop.mp h) ε hε
  refine ⟨N, ?_⟩
  intro n hn
  have hdist :
      dist (continuumLPPrefixPrice S n)
        (continuumGlobalSelfTaxTarget S) < ε :=
    hN n hn
  rw [Real.dist_eq] at hdist
  exact le_of_lt hdist

/-- Countable all-output Gram tail-control receipt.

This is still an analytic receipt, not a proof of the PDE estimate.  It names
the exact limit-passage condition that would upgrade finite all-output Gram
charging to the continuum profile theorem. -/
structure AllOutputCountableGramTailControlReceipt
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) where
  fixed_topology : ContinuumLPUsesFixedTopology S
  fixed_atoms : FixedAllOutputLPBonyAtoms S
  prefix_charge : ∀ N : ℕ, PrefixAllOutputCoherenceCharge S N
  prefix_price_tail_cauchy : AllOutputPrefixPriceTailCauchy S
  prefix_price_tends_to_declared_target :
    AllOutputPrefixPriceTendsToDeclaredTarget S
  smooth_budget_bridge : ContinuumLPSmoothBudgetBridge S
  declared_target_not_backfit_after_payoff : Prop
  declared_target_not_backfit_after_payoff_paid :
    declared_target_not_backfit_after_payoff

/-- Convergence to the declared all-output target implies the Cauchy tail
property in the same fixed scalar topology.

This is a bookkeeping reduction for the countable-tail receipt: a closure
attempt should not have to instantiate a separate Cauchy proof once it has
already proved convergence to the predeclared continuum target. -/
theorem all_output_prefix_price_tail_cauchy_of_tends_to_declared_target
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (htends : AllOutputPrefixPriceTendsToDeclaredTarget S) :
    AllOutputPrefixPriceTailCauchy S := by
  intro ε hε
  have hhalf : 0 < ε / 2 := by
    linarith
  obtain ⟨N, hN⟩ := htends (ε / 2) hhalf
  refine ⟨N, ?_⟩
  intro m n hm hn
  let target := continuumGlobalSelfTaxTarget S
  let pm := continuumLPPrefixPrice S m
  let pn := continuumLPPrefixPrice S n
  have hmabs : |pm - target| ≤ ε / 2 := by
    simpa [pm, target] using hN m hm
  have hnabs : |pn - target| ≤ ε / 2 := by
    simpa [pn, target] using hN n hn
  have htri :
      |pm - pn| ≤ |pm - target| + |pn - target| := by
    have h0 := abs_sub (pm - target) (pn - target)
    have hrewrite : (pm - target) - (pn - target) = pm - pn := by
      ring
    simpa [hrewrite] using h0
  simpa [pm, pn] using
    (le_trans htri (by linarith [hmabs, hnabs] :
      |pm - target| + |pn - target| ≤ ε))

/-- Constructor for countable Gram tail control when target convergence has
already been proved.

The fixed topology, atom declarations, prefix charges, smooth-budget bridge,
and no-backfit guard remain explicit; only the redundant Cauchy field is
derived. -/
def all_output_countable_gram_tail_control_receipt_of_declared_target_convergence
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (fixed_topology : ContinuumLPUsesFixedTopology S)
    (fixed_atoms : FixedAllOutputLPBonyAtoms S)
    (prefix_charge : ∀ N : ℕ, PrefixAllOutputCoherenceCharge S N)
    (prefix_price_tends_to_declared_target :
      AllOutputPrefixPriceTendsToDeclaredTarget S)
    (smooth_budget_bridge : ContinuumLPSmoothBudgetBridge S)
    (declared_target_not_backfit_after_payoff : Prop)
    (declared_target_not_backfit_after_payoff_paid :
      declared_target_not_backfit_after_payoff) :
    AllOutputCountableGramTailControlReceipt S where
  fixed_topology := fixed_topology
  fixed_atoms := fixed_atoms
  prefix_charge := prefix_charge
  prefix_price_tail_cauchy :=
    all_output_prefix_price_tail_cauchy_of_tends_to_declared_target
      S prefix_price_tends_to_declared_target
  prefix_price_tends_to_declared_target :=
    prefix_price_tends_to_declared_target
  smooth_budget_bridge := smooth_budget_bridge
  declared_target_not_backfit_after_payoff :=
    declared_target_not_backfit_after_payoff
  declared_target_not_backfit_after_payoff_paid :=
    declared_target_not_backfit_after_payoff_paid

/-- Constructor for countable Gram tail control from standard metric
convergence of the prefix-price sequence.

This is the topology-facing version a PDE proof should prefer when it has
proved ordinary convergence of the fixed all-output Gram prefix prices.  The
no-backfit and same-atom guards remain explicit; only the conversion from
`Tendsto` to the Track B order-form convergence field is automated. -/
def all_output_countable_gram_tail_control_receipt_of_tendsto_declared_target
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (fixed_topology : ContinuumLPUsesFixedTopology S)
    (fixed_atoms : FixedAllOutputLPBonyAtoms S)
    (prefix_charge : ∀ N : ℕ, PrefixAllOutputCoherenceCharge S N)
    (htendsto :
      Filter.Tendsto
        (fun n : ℕ => continuumLPPrefixPrice S n)
        Filter.atTop
        (nhds (continuumGlobalSelfTaxTarget S)))
    (smooth_budget_bridge : ContinuumLPSmoothBudgetBridge S)
    (declared_target_not_backfit_after_payoff : Prop)
    (declared_target_not_backfit_after_payoff_paid :
      declared_target_not_backfit_after_payoff) :
    AllOutputCountableGramTailControlReceipt S :=
  all_output_countable_gram_tail_control_receipt_of_declared_target_convergence
    fixed_topology
    fixed_atoms
    prefix_charge
    (all_output_prefix_price_tends_to_declared_target_of_tendsto S htendsto)
    smooth_budget_bridge
    declared_target_not_backfit_after_payoff
    declared_target_not_backfit_after_payoff_paid

/-- Source-level countable Gram tail-control duty for a declared all-output
LP/Bony source. -/
structure AllOutputCountableGramTailControlSource
    {τ : ContinuumLPProfileTopology.{u}}
    (source : ContinuumAllOutputLPBonySource τ) where
  prefix_price_tends_to_declared_target :
    AllOutputPrefixPriceTendsToDeclaredTarget source.stream
  declared_target_not_backfit_after_payoff : Prop
  declared_target_not_backfit_after_payoff_paid :
    declared_target_not_backfit_after_payoff

/-- A source-level tail-control duty instantiates the countable Gram tail
receipt for the same declared LP/Bony stream. -/
def all_output_countable_gram_tail_control_receipt_of_source
    {τ : ContinuumLPProfileTopology.{u}}
    {source : ContinuumAllOutputLPBonySource τ}
    (R : AllOutputCountableGramTailControlSource source) :
    AllOutputCountableGramTailControlReceipt source.stream :=
  all_output_countable_gram_tail_control_receipt_of_declared_target_convergence
    source.fixed_topology
    source.fixed_atoms
    source.prefix_charge
    R.prefix_price_tends_to_declared_target
    source.smooth_budget_bridge
    R.declared_target_not_backfit_after_payoff
    R.declared_target_not_backfit_after_payoff_paid

/-- Falsifier for a countable all-output tail-control receipt whose continuum
target was allowed to be backfit after payoff scoring. -/
structure AllOutputDeclaredTargetBackfitFalsifier
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (R : AllOutputCountableGramTailControlReceipt S) where
  missing_no_backfit :
    ¬ R.declared_target_not_backfit_after_payoff

/-- A countable all-output tail-control receipt excludes its own declared-target
backfit falsifier. -/
theorem no_all_output_declared_target_backfit_falsifier_of_countable_gram_tail_control
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (R : AllOutputCountableGramTailControlReceipt S)
    (F : AllOutputDeclaredTargetBackfitFalsifier S R) :
    False :=
  F.missing_no_backfit R.declared_target_not_backfit_after_payoff_paid

/-- Convergence of finite all-output prefix prices to the declared target gives
the lower-semicontinuity direction required by the continuum receipt. -/
theorem continuum_price_lsc_of_all_output_prefix_price_tends_to_declared_target
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (htends : AllOutputPrefixPriceTendsToDeclaredTarget S) :
    ContinuumLPPriceLowerSemicontinuous S := by
  intro _ ε hε
  obtain ⟨N, hN⟩ := htends ε hε
  refine ⟨N, ?_⟩
  intro n hn
  have habs :
      |continuumLPPrefixPrice S n -
        continuumGlobalSelfTaxTarget S| ≤ ε :=
    hN n hn
  have hlower :
      -ε ≤
        continuumLPPrefixPrice S n -
          continuumGlobalSelfTaxTarget S :=
    (abs_le.mp habs).1
  linarith

/-- Convergence of finite all-output prefix prices to the declared target gives
the liminf upper-bound direction used by the no-escape theorem. -/
theorem continuum_liminf_bound_of_all_output_prefix_price_tends_to_declared_target
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (htends : AllOutputPrefixPriceTendsToDeclaredTarget S) :
    ContinuumLPLiminfPriceBound S := by
  intro ε hε
  obtain ⟨N, hN⟩ := htends ε hε
  refine ⟨N, ?_⟩
  have habs :
      |continuumLPPrefixPrice S N -
        continuumGlobalSelfTaxTarget S| ≤ ε :=
    hN N (le_refl N)
  have hupper :
      continuumLPPrefixPrice S N -
        continuumGlobalSelfTaxTarget S ≤ ε :=
    (abs_le.mp habs).2
  linarith

/-- Countable all-output Gram tail control instantiates the positive-coherence
LSC receipt. -/
def all_output_positive_coherence_lsc_receipt_of_countable_gram_tail_control
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (R : AllOutputCountableGramTailControlReceipt S) :
    AllOutputPositiveCoherenceLSCReceipt S where
  fixed_topology := R.fixed_topology
  fixed_atoms := R.fixed_atoms
  prefix_charge := R.prefix_charge
  price_lower_semicontinuous :=
    continuum_price_lsc_of_all_output_prefix_price_tends_to_declared_target
      S R.prefix_price_tends_to_declared_target
  liminf_price_bound :=
    continuum_liminf_bound_of_all_output_prefix_price_tends_to_declared_target
      S R.prefix_price_tends_to_declared_target
  smooth_budget_bridge := R.smooth_budget_bridge

/-- Countable all-output Gram tail control also exposes the generic continuum
LSC obligation receipt, preserving the same fixed stream and atom provenance.
-/
def continuum_lsc_obligation_receipt_of_countable_all_output_gram_tail_control
    {τ : ContinuumLPProfileTopology.{u}}
    {S : ContinuumLPPrefixPriceStream τ}
    (R : AllOutputCountableGramTailControlReceipt S) :
    ContinuumLPLSCObligationReceipt S :=
  continuum_lsc_receipt_of_all_output_positive_coherence
    (all_output_positive_coherence_lsc_receipt_of_countable_gram_tail_control R)

/-- Positive Gram tail source tied to the fixed all-output prefix stream.

The tail price is required to be the difference of two prefix prices, and the
tail payoff is charged by that positive Gram tail price.  This names the exact
countable-tail edge the PDE instantiation must supply. -/
structure AllOutputPositiveGramTailSource
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ) where
  tailPositiveGramPrice : ℕ → ℕ → Real
  tailOutputPayoff : ℕ → ℕ → Real
  tail_price_eq_prefix_increment :
    ∀ J K : ℕ, J ≤ K →
      tailPositiveGramPrice J K =
        continuumLPPrefixPrice S K - continuumLPPrefixPrice S J
  tail_payoff_le_tail_price :
    ∀ J K : ℕ, J ≤ K →
      tailOutputPayoff J K ≤ tailPositiveGramPrice J K
  same_fixed_output_atoms : Prop
  same_fixed_output_atoms_paid : same_fixed_output_atoms
  no_hidden_source_l2_or_moving_atoms : Prop
  no_hidden_source_l2_or_moving_atoms_paid :
    no_hidden_source_l2_or_moving_atoms

/-- Countable tail control makes the charged positive-Gram tail payoff vanish
uniformly over later tail intervals. -/
theorem all_output_positive_gram_tail_payoff_vanishes_of_countable_tail_control
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (R : AllOutputCountableGramTailControlReceipt S)
    (G : AllOutputPositiveGramTailSource S) :
    ∀ ε : Real, 0 < ε → ∃ J0 : ℕ, ∀ J K : ℕ,
      J0 ≤ J → J ≤ K → G.tailOutputPayoff J K ≤ ε := by
  intro ε hε
  obtain ⟨J0, hCauchy⟩ := R.prefix_price_tail_cauchy ε hε
  refine ⟨J0, ?_⟩
  intro J K hJ hJK
  have hK : J0 ≤ K := le_trans hJ hJK
  have hdiff :
      continuumLPPrefixPrice S K -
        continuumLPPrefixPrice S J ≤ ε := by
    exact (abs_le.mp (hCauchy K J hK hJ)).2
  have htail : G.tailPositiveGramPrice J K ≤ ε := by
    rw [G.tail_price_eq_prefix_increment J K hJK]
    exact hdiff
  exact le_trans (G.tail_payoff_le_tail_price J K hJK) htail

/-- Once countable all-output Gram tail control is paid in the fixed topology,
there is no smooth profile-limit escape above the declared self-tax target. -/
theorem no_smooth_escape_of_countable_all_output_gram_tail_control
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (R : AllOutputCountableGramTailControlReceipt S) :
    ¬ ContinuumLPSmoothEscapeCandidate S :=
  no_smooth_escape_candidate_of_all_output_positive_coherence_lsc
    S
    (all_output_positive_coherence_lsc_receipt_of_countable_gram_tail_control R)

/-- Countable all-output Gram tail control rules out the concrete
tail-recurring LSC failure falsifier.

This does not prove the PDE tail-control theorem; it only makes the already
paid countable-tail receipt discharge the already declared LSC falsifier. -/
theorem no_all_output_coherence_lsc_failure_of_countable_gram_tail_control
    {τ : ContinuumLPProfileTopology.{u}}
    (S : ContinuumLPPrefixPriceStream τ)
    (R : AllOutputCountableGramTailControlReceipt S) :
    ¬ Nonempty (AllOutputCoherencePriceLSCFailureFalsifier S) := by
  intro hF
  rcases hF with ⟨F⟩
  exact
    no_all_output_positive_coherence_lsc_receipt_of_falsifier
      S F
      (all_output_positive_coherence_lsc_receipt_of_countable_gram_tail_control R)

/-- Hidden source-coordinate L2 budgets alone do not bound the all-output
positive-coherence payoff channel.  This is the scalar anti-tautology witness
imported from the low-beat L1 receipt: the continuum theorem must charge an
output/coherence price, not merely a source-L2 budget. -/
theorem hidden_source_l2_pricing_insufficient_for_all_output_coherence :
    ∃ S : SourceL2OnlyLowBeatDiagnostic,
      (∀ n : ℕ, S.sourceL2Budget n ≤ 1) ∧
        (∀ B : Real, ∃ n : ℕ, B < S.outputPayoff n) :=
  source_l2_only_budget_does_not_cap_low_beat_payoff

/-- Stronger positive-part version of the same anti-tautology: even charging
only the positive output/coherence surplus cannot be bounded from a hidden
source-L2 budget alone. -/
theorem hidden_source_l2_pricing_does_not_bound_positive_output_surplus :
    ∃ S : SourceL2OnlyLowBeatDiagnostic,
      (∀ n : ℕ, S.sourceL2Budget n ≤ 1) ∧
        (∀ B : Real, ∃ n : ℕ, B < positivePart (S.outputPayoff n)) := by
  refine ⟨
    { sourceL2Budget := fun _ => 1
      outputPayoff := fun n => (n : Real) },
    ?_⟩
  constructor
  · intro n
    norm_num
  · intro B
    obtain ⟨n, hn⟩ := exists_nat_gt B
    refine ⟨n, ?_⟩
    have hn_nonneg : 0 ≤ (n : Real) := by
      exact_mod_cast Nat.zero_le n
    have hpos :
        positivePart ((n : Real)) = (n : Real) := by
      unfold positivePart
      exact max_eq_left hn_nonneg
    simpa [hpos] using hn

end

end ZtareProofs.NS
