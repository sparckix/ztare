import Mathlib.Tactic
import ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ns_trackb_liminf_forward_constructor

/-!
# Toy substrate end-to-end instantiation — NS Track B numeric-liminf path

EXPLICIT TOY substrate where the typed-companion forward constructors
compose. NOT a Navier-Stokes proof. Sanity check that the typed-companion
architecture is internally consistent and produces the bundled
`GP216SelectedProjectedNumericCompactnessLiminfSource` for at least one
concrete non-trivial example.

Toy specification:
- `prefixSelfTaxPrice n := 1 - 1/(n+1) = n/(n+1)` (monotone increasing,
  bounded above by 1, supremum = 1).
- `selfTaxRelaxedOutputPrice := 1` (the supremum / monotone limit).
- approximation family := ℕ, idx := id (cofinal in itself trivially).
- defect state := Bool, defect prices := constant 0.

Goal: instantiate `LeraySelfTaxRelaxedOutputPriceLiminfBoundData` via
`fromMonotonePrefixSequence` and produce the bundled source via the
forward constructors.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Toy partial-sum function: `S n := 1 - 1/(n+1) = n/(n+1)`.

Monotone increasing in n, bounded above by 1, supremum = 1.
Avoids series-bounding proof obligations. -/
def toyPrefixSeq (n : ℕ) : Real := 1 - 1 / ((n + 1 : ℕ) : Real)

/-- 0 ≤ toyPrefixSeq n for every n. -/
theorem toyPrefixSeq_nonneg (n : ℕ) : 0 ≤ toyPrefixSeq n := by
  unfold toyPrefixSeq
  have h : (1 : Real) / ((n + 1 : ℕ) : Real) ≤ 1 := by
    have hpos : (0 : Real) < ((n + 1 : ℕ) : Real) := by exact_mod_cast Nat.succ_pos n
    rw [div_le_one hpos]
    exact_mod_cast Nat.succ_pos n
  linarith

/-- toyPrefixSeq n ≤ 1 for every n. -/
theorem toyPrefixSeq_le_one (n : ℕ) : toyPrefixSeq n ≤ 1 := by
  unfold toyPrefixSeq
  have hpos : (0 : Real) < ((n + 1 : ℕ) : Real) := by exact_mod_cast Nat.succ_pos n
  have hge : (0 : Real) ≤ 1 / ((n + 1 : ℕ) : Real) := by positivity
  linarith

/-- toyPrefixSeq is monotone in n. -/
theorem toyPrefixSeq_monotone : Monotone toyPrefixSeq := by
  intro m n hmn
  unfold toyPrefixSeq
  have hm : (0 : Real) < ((m + 1 : ℕ) : Real) := by exact_mod_cast Nat.succ_pos m
  have hn : (0 : Real) < ((n + 1 : ℕ) : Real) := by exact_mod_cast Nat.succ_pos n
  have hmn_real : ((m + 1 : ℕ) : Real) ≤ ((n + 1 : ℕ) : Real) := by exact_mod_cast Nat.add_le_add_right hmn 1
  have h_div : 1 / ((n + 1 : ℕ) : Real) ≤ 1 / ((m + 1 : ℕ) : Real) :=
    one_div_le_one_div_of_le hm hmn_real
  linarith

/-- Toy `LeraySelfTaxProfilePriceStream` with monotone-bounded prefix. -/
def toyMonotoneStream : LeraySelfTaxProfilePriceStream where
  prefixPayoff := fun _ => 0
  prefixSelfTaxPrice := toyPrefixSeq
  prefixCrossDefectPrice := toyPrefixSeq
  prefixCoherencePrice := toyPrefixSeq
  payoffLimit := 0
  selfTaxLimitPrice := 1
  crossDefectLimitPrice := 1
  coherenceLimitPrice := 1
  profileTopologyDeclaredBeforePayoff := True
  profileStreamDeclaredBeforePayoff := True
  prefixComponentPricesDeclaredBeforePayoff := True
  limitComponentPricesDeclaredBeforePayoff := True
  noPosthocPayoffDependentStreamChoice := True

/-- The toy stream's `prefixPriceForComponent` is monotone in n. -/
theorem toyMonotoneStream_prefixPriceForComponent_monotone
    (component : LeraySelfTaxPriceComponent) :
    Monotone
      (fun n : ℕ => toyMonotoneStream.prefixPriceForComponent component n) := by
  cases component <;>
    · intro m n hmn
      simp [toyMonotoneStream, LeraySelfTaxProfilePriceStream.prefixPriceForComponent]
      exact toyPrefixSeq_monotone hmn

/-- Toy defect source: defectState = Bool, all defect prices zero. -/
def toyDefectSource :
    LeraySelfTaxMeasureValuedDefectSource toyMonotoneStream where
  defectState := Bool
  reynoldsDefect := false
  concentrationDefect := true
  defectPrice := fun _ _ => 0
  defect_carrier_declared_before_payoff := trivial
  reynolds_defect_reified_in_relaxed_limit_price := True
  reynolds_defect_reified_receipt := trivial
  concentration_measure_reified_in_relaxed_limit_price := True
  concentration_measure_reified_receipt := trivial
  defect_price_nonnegative := fun _ _ => le_refl 0

/-- Toy output-limit source: relaxed prices = 1 = supremum of toyPrefixSeq. -/
def toyOutputLimitSource :
    LeraySelfTaxMeasureValuedOutputLimitSource toyMonotoneStream where
  measure_defect_source := toyDefectSource
  component_stream_fixed_before_payoff := trivial
  prefix_components_declared_before_payoff := trivial
  limit_components_declared_before_payoff := trivial
  no_smooth_limit_price_substitution := trivial
  leray_projection_l2_bounded := True
  leray_projection_l2_bounded_receipt := trivial
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology := True
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology_receipt := trivial
  strong_l4_w14_or_hs_source_topology_declared := True
  strong_l4_w14_or_hs_source_topology_declared_receipt := trivial
  cross_and_coherence_outputs_use_same_topology := True
  cross_and_coherence_outputs_use_same_topology_receipt := trivial
  selfTaxRelaxedOutputPrice := 1
  crossDefectRelaxedOutputPrice := 1
  coherenceRelaxedOutputPrice := 1
  self_tax_relaxed_output_includes_measure_defects := by
    show selfTaxDefectFloor _ ≤ (1 : Real)
    unfold selfTaxDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    simp [toyDefectSource]
  cross_defect_relaxed_output_includes_measure_defects := by
    show crossDefectFloor _ ≤ (1 : Real)
    unfold crossDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    simp [toyDefectSource]
  coherence_relaxed_output_includes_measure_defects := by
    show coherenceDefectFloor _ ≤ (1 : Real)
    unfold coherenceDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    simp [toyDefectSource]
  prefix_self_tax_le_relaxed_output := by
    intro n
    show toyPrefixSeq n ≤ 1
    exact toyPrefixSeq_le_one n
  prefix_cross_defect_le_relaxed_output := by
    intro n
    show toyPrefixSeq n ≤ 1
    exact toyPrefixSeq_le_one n
  prefix_coherence_le_relaxed_output := by
    intro n
    show toyPrefixSeq n ≤ 1
    exact toyPrefixSeq_le_one n
  self_tax_relaxed_output_le_limit := le_refl 1
  cross_defect_relaxed_output_le_limit := le_refl 1
  coherence_relaxed_output_le_limit := le_refl 1

/-- The toy prefix sequence converges to 1. This is the analytical content
of the toy: a real Mathlib-level convergence statement. -/
theorem toyPrefixSeq_tendsto_one :
    Filter.Tendsto toyPrefixSeq Filter.atTop (nhds 1) := by
  have h_one_div :
      Filter.Tendsto (fun n : ℕ => (1 : Real) / ((n : Real) + 1))
        Filter.atTop (nhds 0) := tendsto_one_div_add_atTop_nhds_zero_nat
  have h_sub :
      Filter.Tendsto (fun n : ℕ => (1 : Real) - 1 / ((n : Real) + 1))
        Filter.atTop (nhds (1 - 0)) :=
    Filter.Tendsto.sub tendsto_const_nhds h_one_div
  have h_eq : (fun n : ℕ => (1 : Real) - 1 / ((n : Real) + 1)) = toyPrefixSeq := by
    funext n
    unfold toyPrefixSeq
    push_cast
    ring
  rw [h_eq] at h_sub
  simpa using h_sub

/-- Toy compactness provenance: all PDE Props supplied as `True`.

NOT a real PDE proof; a structural witness that the provenance type
is inhabited for at least one substrate. The Lions/DiPerna-Majda/Tartar/
Duchon-Robert Props are placeholder True. -/
def toyCompactnessProvenance :
    LeraySelfTaxMeasureValuedOutputCompactnessProvenance
      toyMonotoneStream toyOutputLimitSource where
  approximation_family := ℕ
  approximation_index_to_prefix := id
  approximation_family_declared_before_payoff := True
  approximation_family_declared_before_payoff_receipt := trivial
  approximation_family_cofinal_in_prefixes := True
  approximation_family_cofinal_in_prefixes_receipt := trivial
  defect_carrier_generated_from_approximation_family := True
  defect_carrier_generated_from_approximation_family_receipt := trivial
  lions_tightness_excludes_vanishing_or_dichotomy_escape := True
  lions_tightness_excludes_vanishing_or_dichotomy_escape_receipt := trivial
  reynolds_defect_is_weak_limit_of_output_residuals := True
  reynolds_defect_is_weak_limit_of_output_residuals_receipt := trivial
  concentration_measure_is_tight_limit_of_output_defects := True
  concentration_measure_is_tight_limit_of_output_defects_receipt := trivial
  diperna_majda_oscillation_concentration_pair_accounted := True
  diperna_majda_oscillation_concentration_pair_accounted_receipt := trivial
  tartar_microlocal_defect_direction_accounted := True
  tartar_microlocal_defect_direction_accounted_receipt := trivial
  multiscale_or_correlation_defect_accounted := True
  multiscale_or_correlation_defect_accounted_receipt := trivial
  duchon_robert_local_energy_defect_accounted := True
  duchon_robert_local_energy_defect_accounted_receipt := trivial
  relaxed_output_prices_are_liminf_bounds := True
  relaxed_output_prices_are_liminf_bounds_receipt := trivial
  not_zero_defect_component_lsc_repackaging := True
  not_zero_defect_component_lsc_repackaging_receipt := trivial

/-- Bundled compactness-provenance + output-limit source for the toy. -/
def toyCompactnessProvenanceMeasureValuedOutputLimitSource :
    LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource
      toyMonotoneStream where
  measure_valued_output_limit := toyOutputLimitSource
  compactness_provenance := toyCompactnessProvenance

/-! ## Apply forward constructors to toy

These three Tendsto facts feed `fromTendsto` to produce the typed
liminf bound data, which then yields three typed `LeraySelfTaxRelaxedOutputPriceLiminfBoundData`
+ realization triples. -/

/-- The toy stream's `prefixPriceForComponent SelfTax` tends to 1
along `comap id atTop`. -/
theorem toy_selfTax_prefix_tendsto :
    Filter.Tendsto
      (fun a : ℕ => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax (id a))
      (Filter.comap (id : ℕ → ℕ) Filter.atTop)
      (nhds toyOutputLimitSource.selfTaxRelaxedOutputPrice) := by
  show Filter.Tendsto (fun a : ℕ => toyPrefixSeq a)
    (Filter.comap (id : ℕ → ℕ) Filter.atTop) (nhds 1)
  rw [show Filter.comap (id : ℕ → ℕ) Filter.atTop = Filter.atTop
        from Filter.comap_id]
  exact toyPrefixSeq_tendsto_one

theorem toy_crossDefect_prefix_tendsto :
    Filter.Tendsto
      (fun a : ℕ => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.crossDefect (id a))
      (Filter.comap (id : ℕ → ℕ) Filter.atTop)
      (nhds toyOutputLimitSource.crossDefectRelaxedOutputPrice) := by
  show Filter.Tendsto (fun a : ℕ => toyPrefixSeq a)
    (Filter.comap (id : ℕ → ℕ) Filter.atTop) (nhds 1)
  rw [show Filter.comap (id : ℕ → ℕ) Filter.atTop = Filter.atTop
        from Filter.comap_id]
  exact toyPrefixSeq_tendsto_one

theorem toy_coherence_prefix_tendsto :
    Filter.Tendsto
      (fun a : ℕ => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.coherence (id a))
      (Filter.comap (id : ℕ → ℕ) Filter.atTop)
      (nhds toyOutputLimitSource.coherenceRelaxedOutputPrice) := by
  show Filter.Tendsto (fun a : ℕ => toyPrefixSeq a)
    (Filter.comap (id : ℕ → ℕ) Filter.atTop) (nhds 1)
  rw [show Filter.comap (id : ℕ → ℕ) Filter.atTop = Filter.atTop
        from Filter.comap_id]
  exact toyPrefixSeq_tendsto_one

/-- NeBot instance for the toy approximation filter. -/
instance : (Filter.comap (id : ℕ → ℕ) Filter.atTop).NeBot := by
  rw [show Filter.comap (id : ℕ → ℕ) Filter.atTop = Filter.atTop
        from Filter.comap_id]
  infer_instance

/-- The typed liminf bound data for the toy, produced via `fromTendsto`. -/
def toyLiminfBoundData :
    LeraySelfTaxRelaxedOutputPriceLiminfBoundData
      toyOutputLimitSource (id : ℕ → ℕ)
      (fun a => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax a)
      (fun a => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.crossDefect a)
      (fun a => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.coherence a) :=
  LeraySelfTaxRelaxedOutputPriceLiminfBoundData.fromTendsto
    toyOutputLimitSource id
    toy_selfTax_prefix_tendsto
    toy_crossDefect_prefix_tendsto
    toy_coherence_prefix_tendsto

/-- Three typed `GP216SelectedFamilyLiminfRealization`s for the toy.

This is the load-bearing structural witness: the typed-companion architecture
yields three `GP216`-shaped liminf realizations from a concrete monotone-bounded
substrate via the analytical bridge. -/
def toyLiminfRealizationTriple :
    GP216SelectedFamilyLiminfRealization ℕ id
        (fun a => toyMonotoneStream.prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax a)
        toyOutputLimitSource.selfTaxRelaxedOutputPrice
      ∧
    GP216SelectedFamilyLiminfRealization ℕ id
        (fun a => toyMonotoneStream.prefixPriceForComponent
          LeraySelfTaxPriceComponent.crossDefect a)
        toyOutputLimitSource.crossDefectRelaxedOutputPrice
      ∧
    GP216SelectedFamilyLiminfRealization ℕ id
        (fun a => toyMonotoneStream.prefixPriceForComponent
          LeraySelfTaxPriceComponent.coherence a)
        toyOutputLimitSource.coherenceRelaxedOutputPrice :=
  toyLiminfBoundData.toRealizationTriple

/-- Three typed `GP216SelectedFamilyObservableSource`s for the toy
(each observable is the prefix price for its declared component). -/
def toyObservableSources :
    GP216SelectedFamilyObservableSource ℕ id toyMonotoneStream
        LeraySelfTaxPriceComponent.selfTax
        (fun a => toyMonotoneStream.prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax (id a))
      ×
    GP216SelectedFamilyObservableSource ℕ id toyMonotoneStream
        LeraySelfTaxPriceComponent.crossDefect
        (fun a => toyMonotoneStream.prefixPriceForComponent
          LeraySelfTaxPriceComponent.crossDefect (id a))
      ×
    GP216SelectedFamilyObservableSource ℕ id toyMonotoneStream
        LeraySelfTaxPriceComponent.coherence
        (fun a => toyMonotoneStream.prefixPriceForComponent
          LeraySelfTaxPriceComponent.coherence (id a)) :=
  ⟨ trivialObservableSourceFromPrefix id toyMonotoneStream
      LeraySelfTaxPriceComponent.selfTax,
    trivialObservableSourceFromPrefix id toyMonotoneStream
      LeraySelfTaxPriceComponent.crossDefect,
    trivialObservableSourceFromPrefix id toyMonotoneStream
      LeraySelfTaxPriceComponent.coherence ⟩

/-! ## Defect-bearing toy variant — closes subatoms 8a/8b/8c

The zero-defect toy above CORRECTLY cannot close
`GP216SameFamilyDefectCarrierSubatom` /
`GP216CorrelationDefectSubatom` / `GP216LocalEnergyDefectSubatom`
because their forward constructors require strict positivity of
defect prices/floors. This is the negative-void design.

Below: a toy variant with positive defect prices that DOES close
those three subatoms via `fromTypedDefectGeneration`,
`fromTypedCompanions` (correlation), and `fromTypedCompanions`
(local energy).

The substrate is identical to `toyMonotoneStream` modulo defect
data — same prefix sequence, same monotonicity, same convergence,
but defect prices are constant `0.1` instead of zero, and relaxed
output prices are `1` (still ≥ defect floor `0.2`). -/

/-- Defect-bearing defect source: defectState = Bool, defectPrice = 0.1 constant. -/
def toyDefectSourcePos :
    LeraySelfTaxMeasureValuedDefectSource toyMonotoneStream where
  defectState := Bool
  reynoldsDefect := false
  concentrationDefect := true
  defectPrice := fun _ _ => (1 / 10 : Real)
  defect_carrier_declared_before_payoff := trivial
  reynolds_defect_reified_in_relaxed_limit_price := True
  reynolds_defect_reified_receipt := trivial
  concentration_measure_reified_in_relaxed_limit_price := True
  concentration_measure_reified_receipt := trivial
  defect_price_nonnegative := fun _ _ => by norm_num

/-- Defect-bearing output-limit source. Relaxed prices = 1 (≥ defect floor 0.2). -/
def toyOutputLimitSourcePos :
    LeraySelfTaxMeasureValuedOutputLimitSource toyMonotoneStream where
  measure_defect_source := toyDefectSourcePos
  component_stream_fixed_before_payoff := trivial
  prefix_components_declared_before_payoff := trivial
  limit_components_declared_before_payoff := trivial
  no_smooth_limit_price_substitution := trivial
  leray_projection_l2_bounded := True
  leray_projection_l2_bounded_receipt := trivial
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology := True
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology_receipt := trivial
  strong_l4_w14_or_hs_source_topology_declared := True
  strong_l4_w14_or_hs_source_topology_declared_receipt := trivial
  cross_and_coherence_outputs_use_same_topology := True
  cross_and_coherence_outputs_use_same_topology_receipt := trivial
  selfTaxRelaxedOutputPrice := 1
  crossDefectRelaxedOutputPrice := 1
  coherenceRelaxedOutputPrice := 1
  self_tax_relaxed_output_includes_measure_defects := by
    show selfTaxDefectFloor _ ≤ (1 : Real)
    unfold selfTaxDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    simp [toyDefectSourcePos]
    norm_num
  cross_defect_relaxed_output_includes_measure_defects := by
    show crossDefectFloor _ ≤ (1 : Real)
    unfold crossDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    simp [toyDefectSourcePos]
    norm_num
  coherence_relaxed_output_includes_measure_defects := by
    show coherenceDefectFloor _ ≤ (1 : Real)
    unfold coherenceDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    simp [toyDefectSourcePos]
    norm_num
  prefix_self_tax_le_relaxed_output := fun n => toyPrefixSeq_le_one n
  prefix_cross_defect_le_relaxed_output := fun n => toyPrefixSeq_le_one n
  prefix_coherence_le_relaxed_output := fun n => toyPrefixSeq_le_one n
  self_tax_relaxed_output_le_limit := le_refl 1
  cross_defect_relaxed_output_le_limit := le_refl 1
  coherence_relaxed_output_le_limit := le_refl 1

/-- Defect-bearing compactness provenance. -/
def toyCompactnessProvenancePos :
    LeraySelfTaxMeasureValuedOutputCompactnessProvenance
      toyMonotoneStream toyOutputLimitSourcePos where
  approximation_family := ℕ
  approximation_index_to_prefix := id
  approximation_family_declared_before_payoff := True
  approximation_family_declared_before_payoff_receipt := trivial
  approximation_family_cofinal_in_prefixes := True
  approximation_family_cofinal_in_prefixes_receipt := trivial
  defect_carrier_generated_from_approximation_family := True
  defect_carrier_generated_from_approximation_family_receipt := trivial
  lions_tightness_excludes_vanishing_or_dichotomy_escape := True
  lions_tightness_excludes_vanishing_or_dichotomy_escape_receipt := trivial
  reynolds_defect_is_weak_limit_of_output_residuals := True
  reynolds_defect_is_weak_limit_of_output_residuals_receipt := trivial
  concentration_measure_is_tight_limit_of_output_defects := True
  concentration_measure_is_tight_limit_of_output_defects_receipt := trivial
  diperna_majda_oscillation_concentration_pair_accounted := True
  diperna_majda_oscillation_concentration_pair_accounted_receipt := trivial
  tartar_microlocal_defect_direction_accounted := True
  tartar_microlocal_defect_direction_accounted_receipt := trivial
  multiscale_or_correlation_defect_accounted := True
  multiscale_or_correlation_defect_accounted_receipt := trivial
  duchon_robert_local_energy_defect_accounted := True
  duchon_robert_local_energy_defect_accounted_receipt := trivial
  relaxed_output_prices_are_liminf_bounds := True
  relaxed_output_prices_are_liminf_bounds_receipt := trivial
  not_zero_defect_component_lsc_repackaging := True
  not_zero_defect_component_lsc_repackaging_receipt := trivial

/-- Bundled defect-bearing source. -/
def toyCompactnessProvenanceMeasureValuedOutputLimitSourcePos :
    LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource
      toyMonotoneStream where
  measure_valued_output_limit := toyOutputLimitSourcePos
  compactness_provenance := toyCompactnessProvenancePos

/-- Typed defect-generation companion: 0 → reynolds (false), nonzero → concentration (true). -/
def toyTypedDefectGeneration :
    LeraySelfTaxApproximationFamilyDefectGenerationTypedData
      toyCompactnessProvenancePos toyDefectSourcePos where
  generatedDefect := (fun a : ℕ =>
    match a with
    | 0 => false
    | _ => true : ℕ → Bool)
  reynolds_witness := ⟨(0 : ℕ), rfl⟩
  concentration_witness := ⟨(1 : ℕ), rfl⟩
  positive_defect_witness :=
    ⟨(0 : ℕ), LeraySelfTaxPriceComponent.selfTax, by
      show (0 : Real) < (1 / 10 : Real)
      norm_num⟩

/-- Closes subatom 8a (defect carrier) for the toy via typed companion. -/
def toyDefectCarrierSubatom :
    GP216SameFamilyDefectCarrierSubatom
      toyCompactnessProvenancePos.approximation_family
      toyCompactnessProvenancePos.approximation_index_to_prefix
      toyCompactnessProvenanceMeasureValuedOutputLimitSourcePos :=
  GP216SameFamilyDefectCarrierSubatom.fromTypedDefectGeneration
    toyCompactnessProvenanceMeasureValuedOutputLimitSourcePos
    toyTypedDefectGeneration

/-- Tendsto facts for the defect-bearing toy (same as zero-defect since
relaxed output prices are still 1 = limit of toyPrefixSeq). -/
theorem toy_selfTax_prefix_tendsto_pos :
    Filter.Tendsto
      (fun a : ℕ => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax (id a))
      (Filter.comap (id : ℕ → ℕ) Filter.atTop)
      (nhds toyOutputLimitSourcePos.selfTaxRelaxedOutputPrice) := by
  show Filter.Tendsto (fun a : ℕ => toyPrefixSeq a)
    (Filter.comap (id : ℕ → ℕ) Filter.atTop) (nhds 1)
  rw [show Filter.comap (id : ℕ → ℕ) Filter.atTop = Filter.atTop
        from Filter.comap_id]
  exact toyPrefixSeq_tendsto_one

theorem toy_crossDefect_prefix_tendsto_pos :
    Filter.Tendsto
      (fun a : ℕ => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.crossDefect (id a))
      (Filter.comap (id : ℕ → ℕ) Filter.atTop)
      (nhds toyOutputLimitSourcePos.crossDefectRelaxedOutputPrice) := by
  show Filter.Tendsto (fun a : ℕ => toyPrefixSeq a)
    (Filter.comap (id : ℕ → ℕ) Filter.atTop) (nhds 1)
  rw [show Filter.comap (id : ℕ → ℕ) Filter.atTop = Filter.atTop
        from Filter.comap_id]
  exact toyPrefixSeq_tendsto_one

theorem toy_coherence_prefix_tendsto_pos :
    Filter.Tendsto
      (fun a : ℕ => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.coherence (id a))
      (Filter.comap (id : ℕ → ℕ) Filter.atTop)
      (nhds toyOutputLimitSourcePos.coherenceRelaxedOutputPrice) := by
  show Filter.Tendsto (fun a : ℕ => toyPrefixSeq a)
    (Filter.comap (id : ℕ → ℕ) Filter.atTop) (nhds 1)
  rw [show Filter.comap (id : ℕ → ℕ) Filter.atTop = Filter.atTop
        from Filter.comap_id]
  exact toyPrefixSeq_tendsto_one

/-- Defect-bearing typed bound data via fromTendsto. -/
def toyLiminfBoundDataPos :
    LeraySelfTaxRelaxedOutputPriceLiminfBoundData
      toyOutputLimitSourcePos (id : ℕ → ℕ)
      (fun a => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax a)
      (fun a => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.crossDefect a)
      (fun a => toyMonotoneStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.coherence a) :=
  LeraySelfTaxRelaxedOutputPriceLiminfBoundData.fromTendsto
    toyOutputLimitSourcePos id
    toy_selfTax_prefix_tendsto_pos
    toy_crossDefect_prefix_tendsto_pos
    toy_coherence_prefix_tendsto_pos

/-- Local-energy defect floor witness for defect-bearing toy. -/
def toyLocalEnergyDefectFloor :
    LeraySelfTaxLocalEnergyDefectFloorTypedData toyOutputLimitSourcePos where
  positive_local_energy_defect_floor := by
    unfold selfTaxDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    show (0 : Real) < (1/10 : Real) + 1/10
    norm_num

/-- Correlation defect floor witness for defect-bearing toy. -/
def toyCorrelationDefectFloor :
    LeraySelfTaxCorrelationDefectFloorTypedData toyOutputLimitSourcePos where
  positive_cross_or_coherence_defect_floor := by
    left
    unfold crossDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    show (0 : Real) < (1/10 : Real) + 1/10
    norm_num

/-- Closes subatom 8b (correlation defect) for the toy. -/
def toyCorrelationDefectSubatom :
    GP216CorrelationDefectSubatom ℕ id
      toyCompactnessProvenanceMeasureValuedOutputLimitSourcePos
      toyOutputLimitSourcePos.crossDefectRelaxedOutputPrice
      toyOutputLimitSourcePos.coherenceRelaxedOutputPrice :=
  GP216CorrelationDefectSubatom.fromTypedCompanions
    toyCompactnessProvenanceMeasureValuedOutputLimitSourcePos
    toyLiminfBoundDataPos
    toyCorrelationDefectFloor

/-- Closes subatom 8c (local-energy defect) for the toy. -/
def toyLocalEnergyDefectSubatom :
    GP216LocalEnergyDefectSubatom ℕ id
      toyCompactnessProvenanceMeasureValuedOutputLimitSourcePos
      toyOutputLimitSourcePos.selfTaxRelaxedOutputPrice :=
  GP216LocalEnergyDefectSubatom.fromTypedCompanions
    toyCompactnessProvenanceMeasureValuedOutputLimitSourcePos
    toyLiminfBoundDataPos
    toyLocalEnergyDefectFloor

/-- Equivalence between toy index ℕ and provenance approximation family ℕ (refl). -/
def toyApproximationEquiv : ℕ ≃ ℕ := Equiv.refl ℕ

/-- The full `GP216SelectedDefectGenerationCertificate` for the defect-bearing toy.

This closes the 7th major GP216 ingredient: defect generation packaging.
With this + the three subatoms above + the Prop receipts from the
compactness provenance, the toy can be promoted to a full
`GP216SelectedProjectedNumericCompactnessLiminfSource` modulo only the
upstream continuum-level handoff bureaucracy (which is orthogonal to
the measure-valued-output-limit substrate). -/
def toyDefectGenerationCertificate :
    GP216SelectedDefectGenerationCertificate ℕ id
      toyCompactnessProvenanceMeasureValuedOutputLimitSourcePos
      toyOutputLimitSourcePos.selfTaxRelaxedOutputPrice
      toyOutputLimitSourcePos.crossDefectRelaxedOutputPrice
      toyOutputLimitSourcePos.coherenceRelaxedOutputPrice where
  approximation_family_equiv_compactness_provenance := toyApproximationEquiv
  compactness_provenance_index_matches := fun a => rfl
  same_family_defect_carrier := toyDefectCarrierSubatom
  correlation_defect_prices := toyCorrelationDefectSubatom
  local_energy_defect_price := toyLocalEnergyDefectSubatom
  defect_carrier_generated_from_same_family :=
    toyCompactnessProvenancePos.defect_carrier_generated_from_approximation_family_receipt
  lions_trichotomy_reduced_to_tight_selected_branch :=
    toyCompactnessProvenancePos.lions_tightness_excludes_vanishing_or_dichotomy_escape_receipt
  oscillation_concentration_pair_generated :=
    toyCompactnessProvenancePos.diperna_majda_oscillation_concentration_pair_accounted_receipt
  microlocal_defect_direction_generated :=
    toyCompactnessProvenancePos.tartar_microlocal_defect_direction_accounted_receipt
  multiscale_or_correlation_defects_generate_cross_coherence_prices :=
    toyCompactnessProvenancePos.multiscale_or_correlation_defect_accounted_receipt
  local_energy_defect_accounted_on_selected_branch :=
    toyCompactnessProvenancePos.duchon_robert_local_energy_defect_accounted_receipt
  relaxed_prices_are_generated_liminf_bounds :=
    toyCompactnessProvenancePos.relaxed_output_prices_are_liminf_bounds_receipt
  not_zero_defect_component_lsc_repackaging :=
    toyCompactnessProvenancePos.not_zero_defect_component_lsc_repackaging_receipt
  positive_generated_measure_defect := by
    left
    exact toyLocalEnergyDefectFloor.positive_local_energy_defect_floor
  self_tax_liminf_includes_measure_defect_floor :=
    toyOutputLimitSourcePos.self_tax_relaxed_output_includes_measure_defects
  cross_defect_liminf_includes_measure_defect_floor :=
    toyOutputLimitSourcePos.cross_defect_relaxed_output_includes_measure_defects
  coherence_liminf_includes_measure_defect_floor :=
    toyOutputLimitSourcePos.coherence_relaxed_output_includes_measure_defects

end

end ZtareProofs.NS
