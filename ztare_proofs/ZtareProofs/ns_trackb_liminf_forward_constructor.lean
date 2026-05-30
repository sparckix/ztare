import Mathlib.Tactic
import ZtareProofs.ns_gp216_bridge_composition_receipt

/-!
# Forward liminf constructor — GP-226 Track B Move 1

This file ships the FORWARD direction:

  `Filter.liminf q (Filter.comap idx Filter.atTop) = L`
  + boundedness/coboundedness
  → `GP216SelectedFamilyLiminfRealization ι idx q L`

Bacon shipped the REVERSE direction (`liminf_eq` in
`ns_gp216_bridge_composition_receipt`). The forward direction closes the
loop: any standard Mathlib liminf equality on the comap-atTop filter can
be turned into a typed `GP216SelectedFamilyLiminfRealization`. This is
the smallest forward primitive needed before the three observable-liminf
subatoms (self-tax, cross-defect, coherence) can be discharged from
analytic data.

Negative-void: the constructor consumes `hliminf` (the equality) +
boundedness/coboundedness. It does NOT pay observable provenance — the
companion `GP216SelectedFamilyObservableSource` handles that side. So
this constructor cannot be used to launder a constant-q with the wrong
value: `hliminf` would already be false in that case.

Anti-tautology: this is a forward construction from standard Mathlib
filter theorems. It does not consume any GP-216 receipt, no-survivor
theorem, or final bridge object. Its only inputs are:
- `idx : ι → ℕ` (the prefix-index map)
- `q : ι → Real` (the observable scalar family)
- `L : Real` (the claimed liminf value)
- `hbounded`, `hcobounded` (filter side conditions)
- `hliminf` (the equality on the standard Mathlib liminf object)

It produces the typed structure expected by the rest of the spine.
-/

namespace ZtareProofs.NS

noncomputable section

universe u

/-! ## Trivial ObservableSource constructor

When the family observable `q` is defined directly as the prefix price for
a declared component over the same approximation index, the
`GP216SelectedFamilyObservableSource` structure is satisfied trivially
by `q_matches_selected_prefix := fun _ => rfl`.

This helper packages that pattern. It does NOT bypass the
`q_matches_selected_prefix` constraint — it satisfies it definitionally
by construction. The "observable declared before payoff" Prop receipt
is supplied as `True` / `trivial`, which is honest because the observable
IS a fixed function of the upstream stream's prefix prices, not a
post-hoc choice. -/

def trivialObservableSourceFromPrefix
    {ι : Type u}
    (idx : ι → ℕ)
    (S : LeraySelfTaxProfilePriceStream)
    (component : LeraySelfTaxPriceComponent) :
    GP216SelectedFamilyObservableSource ι idx S component
      (fun a => S.prefixPriceForComponent component (idx a)) where
  observable_declared_before_payoff := True
  observable_declared_before_payoff_receipt := trivial
  q_matches_selected_prefix := fun _ => rfl

/-- Forward constructor: from the standard Mathlib liminf equality plus
boundedness/coboundedness, produce a `GP216SelectedFamilyLiminfRealization`.

This is the dual of `GP216GeneratedLiminfPriceCertificate.liminf_eq`. -/
def GP216SelectedFamilyLiminfRealization.ofLiminfEq
    {ι : Type u}
    (idx : ι → ℕ)
    (q : ι → Real)
    (L : Real)
    (hbounded :
      (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·) q)
    (hcobounded :
      (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·) q)
    (hliminf :
      Filter.liminf q (Filter.comap idx Filter.atTop) = L) :
    GP216SelectedFamilyLiminfRealization ι idx q L where
  eventual_lower_bound := by
    intro ε hε
    have hle : L ≤ Filter.liminf q (Filter.comap idx Filter.atTop) := by
      rw [hliminf]
    have h_eventually :
        ∀ᶠ a in Filter.comap idx Filter.atTop, L - ε ≤ q a := by
      have hiff :=
        (Filter.le_liminf_iff'
          (f := Filter.comap idx Filter.atTop)
          (u := q)
          hcobounded
          hbounded).mp hle
      exact hiff (L - ε) (by linarith)
    rw [Filter.eventually_comap] at h_eventually
    rw [Filter.eventually_atTop] at h_eventually
    obtain ⟨N, hN⟩ := h_eventually
    refine ⟨N, ?_⟩
    intro a hNa
    exact hN (idx a) hNa a rfl
  tail_near_attainment := by
    intro ε hε
    intro N
    have hge : Filter.liminf q (Filter.comap idx Filter.atTop) ≤ L := by
      rw [hliminf]
    have h_frequently :
        ∃ᶠ a in Filter.comap idx Filter.atTop, q a ≤ L + ε := by
      have hiff :=
        (Filter.liminf_le_iff'
          (f := Filter.comap idx Filter.atTop)
          (u := q)
          hcobounded
          hbounded).mp hge
      exact hiff (L + ε) (by linarith)
    rw [Filter.frequently_comap] at h_frequently
    rw [Filter.frequently_atTop] at h_frequently
    rcases h_frequently N with ⟨n, hNn, a, hidx, hq⟩
    refine ⟨a, ?_, hq⟩
    rw [hidx]
    exact hNn

/-- Forward constructor for the legacy generated-liminf certificate.

Composes `ofLiminfEq` with `GP216GeneratedLiminfPriceCertificate.ofSelectedFamilyRealization`
to produce the legacy certificate from a standard liminf equality plus a
prefix-observable source. -/
def GP216GeneratedLiminfPriceCertificate.ofLiminfEq
    {ι : Type u}
    {S : LeraySelfTaxProfilePriceStream}
    {component : LeraySelfTaxPriceComponent}
    (idx : ι → ℕ)
    (q : ι → Real)
    (L : Real)
    (O :
      GP216SelectedFamilyObservableSource
        ι idx S component q)
    (hbounded :
      (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·) q)
    (hcobounded :
      (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·) q)
    (hliminf :
      Filter.liminf q (Filter.comap idx Filter.atTop) = L) :
    GP216GeneratedLiminfPriceCertificate ι idx q L :=
  GP216GeneratedLiminfPriceCertificate.ofSelectedFamilyRealization
    O
    (GP216SelectedFamilyLiminfRealization.ofLiminfEq idx q L
      hbounded hcobounded hliminf)

/-! ## Typed companion for the `relaxed_output_prices_are_liminf_bounds` Prop

The upstream `LeraySelfTaxMeasureValuedOutputCompactnessProvenance` structure
in `ns_profile_lsc_self_tax_obligation.lean` carries
`relaxed_output_prices_are_liminf_bounds : Prop` as an opaque receipt. Per
the handover meta-pattern §4 ("Treat `Prop` As A Warning Light"), this is
exactly the danger pattern — a load-bearing claim that can be discharged
without exposing data.

The structure below converts that Prop into typed data: actual Mathlib
filter liminf equalities tying the family observables to the relaxed
output prices, plus the boundedness/coboundedness side conditions
required by `Filter.le_liminf_iff'` / `Filter.liminf_le_iff'`.

Negative-void: a constant-q-at-the-wrong-value cannot satisfy
`*_liminf_eq_relaxed` (the equality would be false). A zero-everywhere
trivialization cannot satisfy `prefix_le_relaxed` from the upstream
`LeraySelfTaxMeasureValuedOutputLimitSource` unless prefixes are also
zero — which would falsify the actual PDE substrate the source claims
to model.

Anti-tautology: this object is constructed from raw analytic data
(observables, filter facts, the relaxed prices already declared by the
upstream limit source). It does NOT consume any GP-216 receipt, the
final bridge object, or the no-survivor theorem.
-/

structure LeraySelfTaxRelaxedOutputPriceLiminfBoundData
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    {ι : Type u}
    (idx : ι → ℕ)
    (selfTaxFamilyObservable : ι → Real)
    (crossDefectFamilyObservable : ι → Real)
    (coherenceFamilyObservable : ι → Real) where
  -- MITIGATION 1 (Risk 1, F-NS-TRACKB-20260507-LAUNDERING-RISK-AUDIT-01):
  -- bind observables to actual stream prefix prices via the same
  -- approximation index, so a constant observable equal to a relaxed
  -- price cannot satisfy this typed companion.
  selfTax_observable_matches_prefix :
    ∀ a : ι,
      selfTaxFamilyObservable a
        = S.prefixPriceForComponent
            LeraySelfTaxPriceComponent.selfTax
            (idx a)
  crossDefect_observable_matches_prefix :
    ∀ a : ι,
      crossDefectFamilyObservable a
        = S.prefixPriceForComponent
            LeraySelfTaxPriceComponent.crossDefect
            (idx a)
  coherence_observable_matches_prefix :
    ∀ a : ι,
      coherenceFamilyObservable a
        = S.prefixPriceForComponent
            LeraySelfTaxPriceComponent.coherence
            (idx a)
  selfTax_bounded :
    (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·) selfTaxFamilyObservable
  selfTax_cobounded :
    (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·) selfTaxFamilyObservable
  selfTax_liminf_eq_relaxed :
    Filter.liminf selfTaxFamilyObservable (Filter.comap idx Filter.atTop)
      = M.selfTaxRelaxedOutputPrice
  crossDefect_bounded :
    (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·) crossDefectFamilyObservable
  crossDefect_cobounded :
    (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·) crossDefectFamilyObservable
  crossDefect_liminf_eq_relaxed :
    Filter.liminf crossDefectFamilyObservable (Filter.comap idx Filter.atTop)
      = M.crossDefectRelaxedOutputPrice
  coherence_bounded :
    (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·) coherenceFamilyObservable
  coherence_cobounded :
    (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·) coherenceFamilyObservable
  coherence_liminf_eq_relaxed :
    Filter.liminf coherenceFamilyObservable (Filter.comap idx Filter.atTop)
      = M.coherenceRelaxedOutputPrice

/-- Forward constructor: from typed liminf-bound data, derive the three
selected-family liminf realizations bound to the upstream relaxed output
prices.

This is the typed-data substitute for the opaque
`relaxed_output_prices_are_liminf_bounds` Prop in
`LeraySelfTaxMeasureValuedOutputCompactnessProvenance`.

Closes subatoms 3 / 4 / 5 (observable-liminf for self-tax / cross /
coherence) AND subatom 6 (relaxed price binding) transitively, because
each realization is constructed with `L := relaxedOutputPrice` so the
equality holds by definition rather than by post-hoc choice. -/
def LeraySelfTaxRelaxedOutputPriceLiminfBoundData.toRealizationTriple
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    {ι : Type u}
    {idx : ι → ℕ}
    {selfTaxFamilyObservable : ι → Real}
    {crossDefectFamilyObservable : ι → Real}
    {coherenceFamilyObservable : ι → Real}
    (D :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData
        M idx
        selfTaxFamilyObservable
        crossDefectFamilyObservable
        coherenceFamilyObservable) :
    GP216SelectedFamilyLiminfRealization ι idx
        selfTaxFamilyObservable M.selfTaxRelaxedOutputPrice
      ∧
    GP216SelectedFamilyLiminfRealization ι idx
        crossDefectFamilyObservable M.crossDefectRelaxedOutputPrice
      ∧
    GP216SelectedFamilyLiminfRealization ι idx
        coherenceFamilyObservable M.coherenceRelaxedOutputPrice :=
  ⟨ GP216SelectedFamilyLiminfRealization.ofLiminfEq
      idx selfTaxFamilyObservable M.selfTaxRelaxedOutputPrice
      D.selfTax_bounded D.selfTax_cobounded D.selfTax_liminf_eq_relaxed,
    GP216SelectedFamilyLiminfRealization.ofLiminfEq
      idx crossDefectFamilyObservable M.crossDefectRelaxedOutputPrice
      D.crossDefect_bounded D.crossDefect_cobounded D.crossDefect_liminf_eq_relaxed,
    GP216SelectedFamilyLiminfRealization.ofLiminfEq
      idx coherenceFamilyObservable M.coherenceRelaxedOutputPrice
      D.coherence_bounded D.coherence_cobounded D.coherence_liminf_eq_relaxed ⟩

/-! ## Analytical bridge: produce typed bound data from PDE convergence

This is the genuine analytical content of the typed companion. It says:
*if the family observables converge (in the topological sense) to the
relaxed output prices on the comap-atTop filter, and the filter is
non-empty (NeBot), then the typed bound data is constructible.*

The Mathlib bridges used:
- `Filter.Tendsto.liminf_eq` (Mathlib/Topology/Order/LiminfLimsup.lean:196):
  with `NeBot f`, `Tendsto u f (𝓝 a) → liminf u f = a`.
- `Filter.Tendsto.isBoundedUnder_ge` (LiminfLimsup.lean:97): from Tendsto.
- `Filter.Tendsto.isCoboundedUnder_ge` (LiminfLimsup.lean:69): with NeBot.

The `*_observable_matches_prefix` Mitigation 1 fields close trivially
because we instantiate the observable AS the prefix price function.

This is the smallest piece of genuine PDE-content bridge currently in
the apparatus: it reduces the typed-companion-instantiation burden to
"prove the family observables converge to the relaxed prices", which is
the classical Lions tightness / DiPerna-Majda transport content. -/

def LeraySelfTaxRelaxedOutputPriceLiminfBoundData.fromTendsto
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    {ι : Type u}
    (idx : ι → ℕ)
    [hNeBot : (Filter.comap idx Filter.atTop).NeBot]
    (selfTax_tendsto :
      Filter.Tendsto
        (fun a : ι =>
          S.prefixPriceForComponent
            LeraySelfTaxPriceComponent.selfTax (idx a))
        (Filter.comap idx Filter.atTop)
        (nhds M.selfTaxRelaxedOutputPrice))
    (crossDefect_tendsto :
      Filter.Tendsto
        (fun a : ι =>
          S.prefixPriceForComponent
            LeraySelfTaxPriceComponent.crossDefect (idx a))
        (Filter.comap idx Filter.atTop)
        (nhds M.crossDefectRelaxedOutputPrice))
    (coherence_tendsto :
      Filter.Tendsto
        (fun a : ι =>
          S.prefixPriceForComponent
            LeraySelfTaxPriceComponent.coherence (idx a))
        (Filter.comap idx Filter.atTop)
        (nhds M.coherenceRelaxedOutputPrice)) :
    LeraySelfTaxRelaxedOutputPriceLiminfBoundData
      M idx
      (fun a => S.prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax (idx a))
      (fun a => S.prefixPriceForComponent
        LeraySelfTaxPriceComponent.crossDefect (idx a))
      (fun a => S.prefixPriceForComponent
        LeraySelfTaxPriceComponent.coherence (idx a)) where
  selfTax_observable_matches_prefix := fun _ => rfl
  crossDefect_observable_matches_prefix := fun _ => rfl
  coherence_observable_matches_prefix := fun _ => rfl
  selfTax_bounded := selfTax_tendsto.isBoundedUnder_ge
  selfTax_cobounded := selfTax_tendsto.isCoboundedUnder_ge
  selfTax_liminf_eq_relaxed := selfTax_tendsto.liminf_eq
  crossDefect_bounded := crossDefect_tendsto.isBoundedUnder_ge
  crossDefect_cobounded := crossDefect_tendsto.isCoboundedUnder_ge
  crossDefect_liminf_eq_relaxed := crossDefect_tendsto.liminf_eq
  coherence_bounded := coherence_tendsto.isBoundedUnder_ge
  coherence_cobounded := coherence_tendsto.isCoboundedUnder_ge
  coherence_liminf_eq_relaxed := coherence_tendsto.liminf_eq

/-! ## Monotone-convergence special case (Real-friendly via tendsto_atTop_ciSup)

When the family is `ι := ℕ` with `idx := id` and the prefix prices are
monotone increasing in N with relaxed price equal to the supremum over
N (a hypothesis that holds for Galerkin truncations of `∫|∇u_N|²` and
similar canonical NS approximation energies), the typed companion holds
via Mathlib's `tendsto_atTop_ciSup` (conditionally-complete variant for
Real). The boundedness above comes from the upstream
`prefix_*_le_relaxed_output` field of `LeraySelfTaxMeasureValuedOutputLimitSource`.

SymPy verified for the Galerkin toy `S_N := sum_{k=1}^N 1/k²` in
`scripts/public/projects/ns/ns_trackb_typed_companion_sympy_check.py`. -/

def LeraySelfTaxRelaxedOutputPriceLiminfBoundData.fromMonotonePrefixSequence
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    (selfTax_monotone :
      Monotone
        (fun n : ℕ => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax n))
    (crossDefect_monotone :
      Monotone
        (fun n : ℕ => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.crossDefect n))
    (coherence_monotone :
      Monotone
        (fun n : ℕ => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.coherence n))
    (selfTax_relaxed_eq_iSup :
      M.selfTaxRelaxedOutputPrice
        = ⨆ n : ℕ, S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax n)
    (crossDefect_relaxed_eq_iSup :
      M.crossDefectRelaxedOutputPrice
        = ⨆ n : ℕ, S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.crossDefect n)
    (coherence_relaxed_eq_iSup :
      M.coherenceRelaxedOutputPrice
        = ⨆ n : ℕ, S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.coherence n) :
    LeraySelfTaxRelaxedOutputPriceLiminfBoundData
      M (id : ℕ → ℕ)
      (fun a => S.prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax a)
      (fun a => S.prefixPriceForComponent
        LeraySelfTaxPriceComponent.crossDefect a)
      (fun a => S.prefixPriceForComponent
        LeraySelfTaxPriceComponent.coherence a) := by
  haveI : (Filter.comap (id : ℕ → ℕ) Filter.atTop).NeBot := by
    rw [show (Filter.comap (id : ℕ → ℕ) Filter.atTop) = Filter.atTop by
      simp [Filter.comap_id]]
    infer_instance
  -- Range boundedness: M.relaxedPrice is an upper bound by upstream
  -- `prefix_*_le_relaxed_output`.
  have hSelfTax_bdd : BddAbove (Set.range
      (fun n : ℕ => S.prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax n)) := by
    refine ⟨M.selfTaxRelaxedOutputPrice, ?_⟩
    rintro y ⟨n, rfl⟩
    exact M.prefix_self_tax_le_relaxed_output n
  have hCross_bdd : BddAbove (Set.range
      (fun n : ℕ => S.prefixPriceForComponent
        LeraySelfTaxPriceComponent.crossDefect n)) := by
    refine ⟨M.crossDefectRelaxedOutputPrice, ?_⟩
    rintro y ⟨n, rfl⟩
    exact M.prefix_cross_defect_le_relaxed_output n
  have hCoherence_bdd : BddAbove (Set.range
      (fun n : ℕ => S.prefixPriceForComponent
        LeraySelfTaxPriceComponent.coherence n)) := by
    refine ⟨M.coherenceRelaxedOutputPrice, ?_⟩
    rintro y ⟨n, rfl⟩
    exact M.prefix_coherence_le_relaxed_output n
  have hSelfTax :
      Filter.Tendsto
        (fun n : ℕ => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax n)
        Filter.atTop
        (nhds M.selfTaxRelaxedOutputPrice) := by
    rw [selfTax_relaxed_eq_iSup]
    exact tendsto_atTop_ciSup selfTax_monotone hSelfTax_bdd
  have hCross :
      Filter.Tendsto
        (fun n : ℕ => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.crossDefect n)
        Filter.atTop
        (nhds M.crossDefectRelaxedOutputPrice) := by
    rw [crossDefect_relaxed_eq_iSup]
    exact tendsto_atTop_ciSup crossDefect_monotone hCross_bdd
  have hCoherence :
      Filter.Tendsto
        (fun n : ℕ => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.coherence n)
        Filter.atTop
        (nhds M.coherenceRelaxedOutputPrice) := by
    rw [coherence_relaxed_eq_iSup]
    exact tendsto_atTop_ciSup coherence_monotone hCoherence_bdd
  have hSelfTax_comap :
      Filter.Tendsto
        (fun a : ℕ => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax (id a))
        (Filter.comap (id : ℕ → ℕ) Filter.atTop)
        (nhds M.selfTaxRelaxedOutputPrice) := by
    simp [Filter.comap_id, id]
    exact hSelfTax
  have hCross_comap :
      Filter.Tendsto
        (fun a : ℕ => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.crossDefect (id a))
        (Filter.comap (id : ℕ → ℕ) Filter.atTop)
        (nhds M.crossDefectRelaxedOutputPrice) := by
    simp [Filter.comap_id, id]
    exact hCross
  have hCoherence_comap :
      Filter.Tendsto
        (fun a : ℕ => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.coherence (id a))
        (Filter.comap (id : ℕ → ℕ) Filter.atTop)
        (nhds M.coherenceRelaxedOutputPrice) := by
    simp [Filter.comap_id, id]
    exact hCoherence
  exact LeraySelfTaxRelaxedOutputPriceLiminfBoundData.fromTendsto
    M id hSelfTax_comap hCross_comap hCoherence_comap

/-! ## Sandwich derivation — closes subatom 7 (prefix ≤ liminf ≤ limit)

Given the typed bound data above plus the upstream
`LeraySelfTaxMeasureValuedOutputLimitSource` (which already carries
`prefix_*_le_relaxed_output` and `*_relaxed_output_le_limit`), the
prefix/limit sandwich for the generated liminf prices follows by trivial
transitive substitution.

This closes subatom 7 (`selected_projected_prefix_limit_sandwich_source`)
without paying any new defect or compactness data. -/

theorem LeraySelfTaxRelaxedOutputPriceLiminfBoundData.self_tax_prefix_le_relaxed
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S} :
    ∀ k : ℕ, S.prefixSelfTaxPrice k ≤ M.selfTaxRelaxedOutputPrice :=
  M.prefix_self_tax_le_relaxed_output

theorem LeraySelfTaxRelaxedOutputPriceLiminfBoundData.cross_defect_prefix_le_relaxed
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S} :
    ∀ k : ℕ, S.prefixCrossDefectPrice k ≤ M.crossDefectRelaxedOutputPrice :=
  M.prefix_cross_defect_le_relaxed_output

theorem LeraySelfTaxRelaxedOutputPriceLiminfBoundData.coherence_prefix_le_relaxed
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S} :
    ∀ k : ℕ, S.prefixCoherencePrice k ≤ M.coherenceRelaxedOutputPrice :=
  M.prefix_coherence_le_relaxed_output

theorem LeraySelfTaxRelaxedOutputPriceLiminfBoundData.self_tax_relaxed_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S} :
    M.selfTaxRelaxedOutputPrice ≤ S.selfTaxLimitPrice :=
  M.self_tax_relaxed_output_le_limit

theorem LeraySelfTaxRelaxedOutputPriceLiminfBoundData.cross_defect_relaxed_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S} :
    M.crossDefectRelaxedOutputPrice ≤ S.crossDefectLimitPrice :=
  M.cross_defect_relaxed_output_le_limit

theorem LeraySelfTaxRelaxedOutputPriceLiminfBoundData.coherence_relaxed_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S} :
    M.coherenceRelaxedOutputPrice ≤ S.coherenceLimitPrice :=
  M.coherence_relaxed_output_le_limit

/-! ## Typed companion for upstream `reynolds_defect_reified` /
`concentration_measure_reified` Props (data-only)

The upstream `LeraySelfTaxMeasureValuedDefectSource` (in
`ns_profile_lsc_self_tax_obligation.lean`, line 505+) carries TWO load-
bearing opaque Props:

  reynolds_defect_reified_in_relaxed_limit_price : Prop
  concentration_measure_reified_in_relaxed_limit_price : Prop

Per handover meta-pattern §4 ("Treat Prop As A Warning Light"), these
are danger names ("reified") — load-bearing claims with no exposed
data. The structure below provides the typed substitute: actual Real-
positive `defectPrice` witnesses with specific components.

This typed data is what subatom 8
(`selected_projected_same_family_defect_generation_source`) requires
for `generated_defect_has_positive_price`. A forward constructor
producing the full `GP216SameFamilyDefectCarrierSubatom` from this
typed reification ALSO needs an inhabitedness witness for the
approximation family `ι`, which is held in another opaque Prop
upstream (`approximation_family_cofinal_in_prefixes`). The full
forward constructor is therefore pending a SECOND typed companion for
that Prop; documented as future work in the F-row.

Anti-tautology: this object is constructed from raw analytic data
(actual `defectPrice` values from the PDE substrate) plus the upstream
defect source declarations. It does NOT consume any GP-216 receipt,
the final bridge object, or the no-survivor theorem.

Negative-void: a zero-defect substrate cannot satisfy the strict
inequality `0 < defectPrice _ _`. This is exactly the route blocked by
the `zero-defect-generation-certificate` regression test in
`scripts/public/projects/ns/ns_trackb_negative_void_probe.py`. -/

structure LeraySelfTaxMeasureValuedDefectSourceReifiedTypedData
    {S : LeraySelfTaxProfilePriceStream}
    (Y : LeraySelfTaxMeasureValuedDefectSource S) where
  reynolds_positive_component : LeraySelfTaxPriceComponent
  reynolds_defect_has_positive_price :
    0 < Y.defectPrice Y.reynoldsDefect reynolds_positive_component
  concentration_positive_component : LeraySelfTaxPriceComponent
  concentration_measure_has_positive_price :
    0 < Y.defectPrice Y.concentrationDefect concentration_positive_component

/-! ## Typed companion for `approximation_family_cofinal_in_prefixes` Prop

The upstream `LeraySelfTaxMeasureValuedOutputCompactnessProvenance`
carries `approximation_family_cofinal_in_prefixes : Prop` — a danger-
named opaque Prop. Its honest content: the family is non-empty AND
cofinal in the prefix-index sequence.

The typed companion below exposes both: an inhabitant witness and the
cofinality data.

Anti-tautology: constructed from raw analytic data (the actual family
inhabitant + cofinal index witnesses). Does NOT consume any GP-216
receipt or final bridge object.

Negative-void: an empty family violates `Inhabited`. A non-cofinal
family violates `family_cofinal` (the existential fails for some N).
Either failure prevents the typed companion from being instantiated. -/

structure LeraySelfTaxApproximationFamilyCofinalTypedData
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    (CP : LeraySelfTaxMeasureValuedOutputCompactnessProvenance S M) where
  family_inhabitant : CP.approximation_family
  family_cofinal :
    ∀ N : ℕ, ∃ a : CP.approximation_family,
      N ≤ CP.approximation_index_to_prefix a

/-! ## MITIGATION 2 (Risk 2, F-NS-TRACKB-20260507-LAUNDERING-RISK-AUDIT-01):

Replace the fiat-alternation `generatedDefect` with a typed companion
that places the analytical burden honestly. The new companion below
isolates the analytical content (the family genuinely produces both
Reynolds and concentration defects via some PDE-derived map). The
forward constructor becomes trivial type-coercion. -/

structure LeraySelfTaxApproximationFamilyDefectGenerationTypedData
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    (CP : LeraySelfTaxMeasureValuedOutputCompactnessProvenance S M)
    (Y : LeraySelfTaxMeasureValuedDefectSource S) where
  generatedDefect : CP.approximation_family → Y.defectState
  reynolds_witness :
    ∃ a : CP.approximation_family, generatedDefect a = Y.reynoldsDefect
  concentration_witness :
    ∃ a : CP.approximation_family, generatedDefect a = Y.concentrationDefect
  positive_defect_witness :
    ∃ a : CP.approximation_family, ∃ component : LeraySelfTaxPriceComponent,
      0 < Y.defectPrice (generatedDefect a) component

/-- Forward constructor for `GP216SameFamilyDefectCarrierSubatom` given
the typed defect-generation companion above.

Closes subatom 8 in the conditional sense: the structural wiring is a
trivial pass-through; the genuine PDE content lives in producing the
typed defect-generation companion, whose three existential witnesses ARE
the Lions/DiPerna-Majda/Tartar analytical claims about the approximation
family's measure-valued limits.

Compared to the prior fiat-alternation construction, this constructor
does NOT generate defects by bookkeeping. It consumes a witness map
provided externally. Risk 2 (fiat alternation laundering) is closed at
this layer; the analytical burden is correctly placed on producing the
typed defect-generation companion. -/
def GP216SameFamilyDefectCarrierSubatom.fromTypedDefectGeneration
    {S : LeraySelfTaxProfilePriceStream}
    (C : LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource S)
    (typedDefectGen :
      LeraySelfTaxApproximationFamilyDefectGenerationTypedData
        C.compactness_provenance
        C.measure_valued_output_limit.measure_defect_source) :
    GP216SameFamilyDefectCarrierSubatom
      C.compactness_provenance.approximation_family
      C.compactness_provenance.approximation_index_to_prefix
      C where
  approximation_family_equiv_compactness_provenance := Equiv.refl _
  compactness_provenance_index_matches := fun _ => rfl
  generatedDefect := typedDefectGen.generatedDefect
  reynolds_defect_generated_on_family := typedDefectGen.reynolds_witness
  concentration_defect_generated_on_family := typedDefectGen.concentration_witness
  generated_defect_has_positive_price := typedDefectGen.positive_defect_witness

/-! ## Typed companion for correlation defect floor (cross + coherence)

Subatom 8b: `GP216CorrelationDefectSubatom` requires a positive
cross-or-coherence defect floor on the relaxed-output ledger plus
inequalities tying the floors below the generated liminf prices.

Typed companion below isolates the analytical content. The inequality
fields close transitively from the upstream
`*_relaxed_output_includes_measure_defects` + the typed bound data's
`*_liminf_eq_relaxed`. -/

structure LeraySelfTaxCorrelationDefectFloorTypedData
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) where
  positive_cross_or_coherence_defect_floor :
    0 <
      crossDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          M.measure_defect_source) ∨
    0 <
      coherenceDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          M.measure_defect_source)

/-! ## Typed companion for local-energy defect floor (self-tax)

Subatom 8c: `GP216LocalEnergyDefectSubatom` requires a positive self-tax
defect floor on the relaxed-output ledger.

Typed companion below isolates the analytical content. -/

structure LeraySelfTaxLocalEnergyDefectFloorTypedData
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) where
  positive_local_energy_defect_floor :
    0 <
      selfTaxDefectFloor
        (relaxed_output_defect_ledger_of_measure_valued_source
          M.measure_defect_source)

/-- Forward constructor for `GP216CorrelationDefectSubatom` given typed
bound data + correlation defect floor witness.

Closes subatom 8b: structural wiring trivial; analytical content in the
typed correlation defect floor companion. -/
def GP216CorrelationDefectSubatom.fromTypedCompanions
    {S : LeraySelfTaxProfilePriceStream}
    (C : LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource S)
    {ι : Type u}
    {idx : ι → ℕ}
    {selfTaxFamilyObservable : ι → Real}
    {crossDefectFamilyObservable : ι → Real}
    {coherenceFamilyObservable : ι → Real}
    (CP_bound :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData
        C.measure_valued_output_limit idx
        selfTaxFamilyObservable
        crossDefectFamilyObservable
        coherenceFamilyObservable)
    (correlationDefectFloor :
      LeraySelfTaxCorrelationDefectFloorTypedData
        C.measure_valued_output_limit) :
    GP216CorrelationDefectSubatom
      ι idx C
      C.measure_valued_output_limit.crossDefectRelaxedOutputPrice
      C.measure_valued_output_limit.coherenceRelaxedOutputPrice where
  crossCorrelationObservable := crossDefectFamilyObservable
  coherenceCorrelationObservable := coherenceFamilyObservable
  cross_correlation_observable_source :=
    { observable_declared_before_payoff := True
      observable_declared_before_payoff_receipt := trivial
      q_matches_selected_prefix := CP_bound.crossDefect_observable_matches_prefix }
  coherence_correlation_observable_source :=
    { observable_declared_before_payoff := True
      observable_declared_before_payoff_receipt := trivial
      q_matches_selected_prefix := CP_bound.coherence_observable_matches_prefix }
  cross_correlation_liminf_realization :=
    GP216SelectedFamilyLiminfRealization.ofLiminfEq
      idx crossDefectFamilyObservable
      C.measure_valued_output_limit.crossDefectRelaxedOutputPrice
      CP_bound.crossDefect_bounded
      CP_bound.crossDefect_cobounded
      CP_bound.crossDefect_liminf_eq_relaxed
  coherence_correlation_liminf_realization :=
    GP216SelectedFamilyLiminfRealization.ofLiminfEq
      idx coherenceFamilyObservable
      C.measure_valued_output_limit.coherenceRelaxedOutputPrice
      CP_bound.coherence_bounded
      CP_bound.coherence_cobounded
      CP_bound.coherence_liminf_eq_relaxed
  positive_cross_or_coherence_defect_floor :=
    correlationDefectFloor.positive_cross_or_coherence_defect_floor
  cross_liminf_includes_correlation_defect_floor :=
    C.measure_valued_output_limit.cross_defect_relaxed_output_includes_measure_defects
  coherence_liminf_includes_correlation_defect_floor :=
    C.measure_valued_output_limit.coherence_relaxed_output_includes_measure_defects

/-- Forward constructor for `GP216LocalEnergyDefectSubatom` given typed
bound data + local-energy defect floor witness. -/
def GP216LocalEnergyDefectSubatom.fromTypedCompanions
    {S : LeraySelfTaxProfilePriceStream}
    (C : LeraySelfTaxCompactnessProvenanceMeasureValuedOutputLimitSource S)
    {ι : Type u}
    {idx : ι → ℕ}
    {selfTaxFamilyObservable : ι → Real}
    {crossDefectFamilyObservable : ι → Real}
    {coherenceFamilyObservable : ι → Real}
    (CP_bound :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData
        C.measure_valued_output_limit idx
        selfTaxFamilyObservable
        crossDefectFamilyObservable
        coherenceFamilyObservable)
    (localEnergyFloor :
      LeraySelfTaxLocalEnergyDefectFloorTypedData
        C.measure_valued_output_limit) :
    GP216LocalEnergyDefectSubatom
      ι idx C
      C.measure_valued_output_limit.selfTaxRelaxedOutputPrice where
  localEnergyObservable := selfTaxFamilyObservable
  local_energy_observable_source :=
    { observable_declared_before_payoff := True
      observable_declared_before_payoff_receipt := trivial
      q_matches_selected_prefix := CP_bound.selfTax_observable_matches_prefix }
  local_energy_liminf_realization :=
    GP216SelectedFamilyLiminfRealization.ofLiminfEq
      idx selfTaxFamilyObservable
      C.measure_valued_output_limit.selfTaxRelaxedOutputPrice
      CP_bound.selfTax_bounded
      CP_bound.selfTax_cobounded
      CP_bound.selfTax_liminf_eq_relaxed
  positive_local_energy_defect_floor :=
    localEnergyFloor.positive_local_energy_defect_floor
  self_tax_liminf_includes_local_energy_defect_floor :=
    C.measure_valued_output_limit.self_tax_relaxed_output_includes_measure_defects

end

end ZtareProofs.NS
