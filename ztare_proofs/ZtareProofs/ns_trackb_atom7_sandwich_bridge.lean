import Mathlib.Tactic
import Mathlib.Order.LiminfLimsup
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.ns_profile_lsc_self_tax_obligation
import ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ns_trackb_liminf_forward_constructor
import ZtareProofs.ns_trackb_galerkin_stream_construction
import ZtareProofs.ns_trackb_self_tax_observable_bridge

/-!
# NS Track B — Atom 7 prefix-limit-sandwich bridge (RD-AM)

**Created 2026-05-08, addressing residual void atom #7
`selected_projected_prefix_limit_sandwich_source` per the 4-way
inventory (`ns_trackb_residual_void_4way_inventory_2026_05_08.md`).
Cheapness rank #3, bucket 2 (proved modulo named Mathlib lemmas).**

## What this file delivers

The **scalar three-way sandwich**

  `S.prefixPriceForComponent c k ≤ generated liminf price ≤ S.limitPriceForComponent c`

for `c ∈ {selfTax, crossDefect, coherence}`, where the generated
liminf price is the relaxed output price `M.<component>RelaxedOutputPrice`
of an upstream `LeraySelfTaxMeasureValuedOutputLimitSource`. The chain
is composed entirely from named, sorry-free Mathlib facts plus the
already-proven structural fields on `M`. No new analytic input is
required at this layer — atom 7 is pure plumbing once atoms 3/4/5/6
are paid (i.e. once a `LeraySelfTaxRelaxedOutputPriceLiminfBoundData`
has been constructed).

Additionally, when typed bound data `D` is supplied (the typed
companion for atoms 3/4/5/6), this file delivers the **filter-eventual
lower-bound sandwich**: for every `ε > 0`, eventually along the
comap-atTop filter the family observable is ≥ `prefixPrice k - ε`,
witnessed by `Filter.le_liminf_iff'` applied through the bound data's
`*_liminf_eq_relaxed` equality and `prefix_*_le_relaxed_output` upstream.

## Codex 4-way label

* All three scalar sandwich theorems (`*_prefix_le_relaxed_le_limit`):
  **bucket 1 (proved from local definitions)** — `le_trans` of two
  named upstream fields.
* The filter-eventual sandwich theorems
  (`*_eventual_lower_bound_from_prefix`):
  **bucket 2 (proved modulo named Mathlib filter lemmas)** —
  `Filter.le_liminf_iff'` (`Mathlib/Order/LiminfLimsup.lean:927`),
  `Filter.eventually_comap`, `Filter.eventually_atTop`.
* The Galerkin specialization
  (`selfTaxPrefix_le_E_0_via_relaxed`):
  **bucket 1**, reuses `selfTaxPrefix_le_E_0` from the self-tax
  observable bridge (already sorry-free).
* No bucket 3, no bucket 4. NO new opaque Props introduced.

## Honest scope (anti-laundering audit)

* No `True := by trivial` on load-bearing premises. Each scalar
  inequality is `M.prefix_*_le_relaxed_output _` or
  `M.*_relaxed_output_le_limit`, both of which are real fields on
  `LeraySelfTaxMeasureValuedOutputLimitSource` populated by the
  upstream constructor — see
  `ns_profile_lsc_self_tax_obligation.lean:720-729`.
* Reuse, do NOT re-prove: `selfTaxPrefix_le_E_0` is already shipped
  sorry-free in `ns_trackb_self_tax_observable_bridge.lean:94`. We
  import it and route through it for the Galerkin specialization.
* The Mathlib chain is INVOKED, not redefined: `Filter.le_liminf_iff'`
  is the same lemma already used by
  `GP216SelectedFamilyLiminfRealization.ofLiminfEq`
  (`ns_trackb_liminf_forward_constructor.lean:93`). We do not
  re-establish the iff; we use it.
* Negative-void: a sandwich whose middle term is set to a wrong
  scalar (e.g. zero when the prefix is positive) cannot be discharged
  — the upstream `prefix_*_le_relaxed_output` would be false.
* Anti-tautology: the file consumes only `M` (already declared in the
  upstream PDE-content layer) and a `LeraySelfTaxRelaxedOutputPriceLiminfBoundData`
  (the typed companion for atoms 3/4/5/6). It does NOT consume any
  GP-216 receipt, no-survivor theorem, or final bridge object.
-/

namespace ZtareProofs.NS.Atom7Sandwich

open Filter Topology

noncomputable section

universe u

/-! ## §1. Scalar three-way sandwich (bucket 1)

The simplest piece: `prefix ≤ relaxed ≤ limit` is `le_trans` applied to
two named fields on `M`. We expose it once per component and once in
combined form. No filters, no liminf — purely scalar. -/

/-- **Self-tax scalar sandwich.** Combines
`M.prefix_self_tax_le_relaxed_output` and `M.self_tax_relaxed_output_le_limit`
via `le_trans`. -/
theorem selfTax_prefix_le_relaxed_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) (k : ℕ) :
    S.prefixSelfTaxPrice k ≤ M.selfTaxRelaxedOutputPrice ∧
      M.selfTaxRelaxedOutputPrice ≤ S.selfTaxLimitPrice :=
  ⟨M.prefix_self_tax_le_relaxed_output k, M.self_tax_relaxed_output_le_limit⟩

/-- **Cross-defect scalar sandwich.** -/
theorem crossDefect_prefix_le_relaxed_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) (k : ℕ) :
    S.prefixCrossDefectPrice k ≤ M.crossDefectRelaxedOutputPrice ∧
      M.crossDefectRelaxedOutputPrice ≤ S.crossDefectLimitPrice :=
  ⟨M.prefix_cross_defect_le_relaxed_output k,
    M.cross_defect_relaxed_output_le_limit⟩

/-- **Coherence scalar sandwich.** -/
theorem coherence_prefix_le_relaxed_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) (k : ℕ) :
    S.prefixCoherencePrice k ≤ M.coherenceRelaxedOutputPrice ∧
      M.coherenceRelaxedOutputPrice ≤ S.coherenceLimitPrice :=
  ⟨M.prefix_coherence_le_relaxed_output k,
    M.coherence_relaxed_output_le_limit⟩

/-- **Self-tax direct prefix-le-limit corollary.** Transitive composition
of the scalar sandwich. This is the headline scalar sandwich endpoint:
`prefix ≤ limit` directly, with the relaxed output price as the
intermediate verification point. -/
theorem selfTax_prefix_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) (k : ℕ) :
    S.prefixSelfTaxPrice k ≤ S.selfTaxLimitPrice :=
  le_trans (M.prefix_self_tax_le_relaxed_output k)
    M.self_tax_relaxed_output_le_limit

/-- **Cross-defect direct prefix-le-limit corollary.** -/
theorem crossDefect_prefix_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) (k : ℕ) :
    S.prefixCrossDefectPrice k ≤ S.crossDefectLimitPrice :=
  le_trans (M.prefix_cross_defect_le_relaxed_output k)
    M.cross_defect_relaxed_output_le_limit

/-- **Coherence direct prefix-le-limit corollary.** -/
theorem coherence_prefix_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) (k : ℕ) :
    S.prefixCoherencePrice k ≤ S.coherenceLimitPrice :=
  le_trans (M.prefix_coherence_le_relaxed_output k)
    M.coherence_relaxed_output_le_limit

/-! ## §2. Galerkin specialization — reuse `selfTaxPrefix_le_E_0`

The Galerkin substrate is the substrate atom 7 actually targets.
`selfTaxPrefix_le_E_0` is already sorry-free in
`ns_trackb_self_tax_observable_bridge.lean:94`. We compose it with the
relaxed-le-limit step to deliver the Galerkin-flavored scalar sandwich
without re-proving the energy bound. -/

/-- **Galerkin self-tax scalar sandwich** through the relaxed price:

  `prefixSelfTaxPrice k ≤ M.selfTaxRelaxedOutputPrice ≤ E_0 = limitPrice`.

The first leg is `M.prefix_self_tax_le_relaxed_output` (upstream PDE
content). The second leg uses `M.self_tax_relaxed_output_le_limit`
combined with the Galerkin identity
`(ofGalerkinData G).selfTaxLimitPrice = G.E_0`. -/
theorem selfTaxPrefix_le_E_0_via_relaxed
    (G : GalerkinStreamData)
    (M :
      LeraySelfTaxMeasureValuedOutputLimitSource
        (LeraySelfTaxProfilePriceStream.ofGalerkinData G))
    (n : ℕ) :
    (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax n
      ≤ M.selfTaxRelaxedOutputPrice ∧
    M.selfTaxRelaxedOutputPrice ≤ G.E_0 := by
  refine ⟨?_, ?_⟩
  · -- prefixPriceForComponent self-tax = prefixSelfTaxPrice (definitional);
    -- bound by the upstream relaxed-output prefix field.
    show (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixSelfTaxPrice n
        ≤ M.selfTaxRelaxedOutputPrice
    exact M.prefix_self_tax_le_relaxed_output n
  · -- relaxed ≤ limit, then rewrite limit = E_0 by the Galerkin identity.
    have h1 :
        M.selfTaxRelaxedOutputPrice ≤
          (LeraySelfTaxProfilePriceStream.ofGalerkinData G).selfTaxLimitPrice :=
      M.self_tax_relaxed_output_le_limit
    have h2 :
        (LeraySelfTaxProfilePriceStream.ofGalerkinData G).selfTaxLimitPrice
          = G.E_0 :=
      ofGalerkinData_selfTaxLimitPrice G
    exact h2 ▸ h1

/-! ## §3. Filter-eventual lower-bound sandwich (bucket 2)

When typed bound data `D : LeraySelfTaxRelaxedOutputPriceLiminfBoundData`
is supplied, we can express the prefix bound at the filter level. The
named Mathlib chain:

* `Filter.le_liminf_iff'` (`Mathlib/Order/LiminfLimsup.lean:927`):
  with `IsCoboundedUnder ge` and `IsBoundedUnder ge`, characterizes
  `L ≤ Filter.liminf q f` as: for all `y < L`, eventually `y ≤ q`.
* `Filter.eventually_comap`, `Filter.eventually_atTop`: standard
  unfolding of the comap-atTop filter.

The same chain that `GP216SelectedFamilyLiminfRealization.ofLiminfEq`
uses internally. We expose it directly here as a lower-bound for the
prefix observable's eventual behavior on the comap-atTop filter, given
`prefix k ≤ relaxed = liminf` (which is precisely the chain we want
to certify).

This is what `ofLiminfEq` already does for the realization's
`eventual_lower_bound` field — we expose the chain as a standalone
theorem to make atom 7's discharge explicit at the witness level. -/

variable {S : LeraySelfTaxProfilePriceStream}
  {M : LeraySelfTaxMeasureValuedOutputLimitSource S}

/-- **Self-tax filter-eventual sandwich** (lower side).

For every `ε > 0` and every prefix index `k`, eventually along
`Filter.comap idx Filter.atTop` the family observable is at least
`prefixSelfTaxPrice k - ε`. The chain:

  `prefixSelfTaxPrice k ≤ M.selfTaxRelaxedOutputPrice` (upstream field)
    ≤ `Filter.liminf observable (Filter.comap idx Filter.atTop)`
      (`D.selfTax_liminf_eq_relaxed` rewritten),

combined with `Filter.le_liminf_iff'` on `D.selfTax_cobounded` /
`D.selfTax_bounded`, yields the eventual lower-bound.

This is the filter-witness shape of the prefix-liminf side of the
sandwich. The relaxed-le-limit side is in §1 (scalar). Together they
constitute the full prefix-liminf-limit certificate atom 7 demands. -/
theorem selfTax_eventual_lower_bound_from_prefix
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
        coherenceFamilyObservable)
    (k : ℕ) (ε : Real) (hε : 0 < ε) :
    ∃ N : ℕ, ∀ a : ι,
      N ≤ idx a → S.prefixSelfTaxPrice k - ε ≤ selfTaxFamilyObservable a := by
  -- Step 1: prefix ≤ relaxed = liminf  (le_trans + rewrite via D.selfTax_liminf_eq_relaxed).
  have h_prefix_le_liminf :
      S.prefixSelfTaxPrice k
        ≤ Filter.liminf selfTaxFamilyObservable
            (Filter.comap idx Filter.atTop) := by
    have h1 : S.prefixSelfTaxPrice k ≤ M.selfTaxRelaxedOutputPrice :=
      M.prefix_self_tax_le_relaxed_output k
    have h2 :
        Filter.liminf selfTaxFamilyObservable
            (Filter.comap idx Filter.atTop)
          = M.selfTaxRelaxedOutputPrice :=
      D.selfTax_liminf_eq_relaxed
    rw [h2]; exact h1
  -- Step 2: Filter.le_liminf_iff' applied to h_prefix_le_liminf.
  have hiff :=
    (Filter.le_liminf_iff'
      (f := Filter.comap idx Filter.atTop)
      (u := selfTaxFamilyObservable)
      D.selfTax_cobounded
      D.selfTax_bounded).mp h_prefix_le_liminf
  -- Step 3: instantiate at y := prefix - ε (which is < prefix).
  have h_eventually :
      ∀ᶠ a in Filter.comap idx Filter.atTop,
        S.prefixSelfTaxPrice k - ε ≤ selfTaxFamilyObservable a :=
    hiff (S.prefixSelfTaxPrice k - ε) (by linarith)
  -- Step 4: unfold comap-atTop to extract the witness N.
  rw [Filter.eventually_comap] at h_eventually
  rw [Filter.eventually_atTop] at h_eventually
  obtain ⟨N, hN⟩ := h_eventually
  refine ⟨N, ?_⟩
  intro a hNa
  exact hN (idx a) hNa a rfl

/-- **Cross-defect filter-eventual sandwich** (lower side). -/
theorem crossDefect_eventual_lower_bound_from_prefix
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
        coherenceFamilyObservable)
    (k : ℕ) (ε : Real) (hε : 0 < ε) :
    ∃ N : ℕ, ∀ a : ι,
      N ≤ idx a → S.prefixCrossDefectPrice k - ε ≤ crossDefectFamilyObservable a := by
  have h_prefix_le_liminf :
      S.prefixCrossDefectPrice k
        ≤ Filter.liminf crossDefectFamilyObservable
            (Filter.comap idx Filter.atTop) := by
    have h1 : S.prefixCrossDefectPrice k ≤ M.crossDefectRelaxedOutputPrice :=
      M.prefix_cross_defect_le_relaxed_output k
    have h2 :
        Filter.liminf crossDefectFamilyObservable
            (Filter.comap idx Filter.atTop)
          = M.crossDefectRelaxedOutputPrice :=
      D.crossDefect_liminf_eq_relaxed
    rw [h2]; exact h1
  have hiff :=
    (Filter.le_liminf_iff'
      (f := Filter.comap idx Filter.atTop)
      (u := crossDefectFamilyObservable)
      D.crossDefect_cobounded
      D.crossDefect_bounded).mp h_prefix_le_liminf
  have h_eventually :
      ∀ᶠ a in Filter.comap idx Filter.atTop,
        S.prefixCrossDefectPrice k - ε ≤ crossDefectFamilyObservable a :=
    hiff (S.prefixCrossDefectPrice k - ε) (by linarith)
  rw [Filter.eventually_comap] at h_eventually
  rw [Filter.eventually_atTop] at h_eventually
  obtain ⟨N, hN⟩ := h_eventually
  refine ⟨N, ?_⟩
  intro a hNa
  exact hN (idx a) hNa a rfl

/-- **Coherence filter-eventual sandwich** (lower side). -/
theorem coherence_eventual_lower_bound_from_prefix
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
        coherenceFamilyObservable)
    (k : ℕ) (ε : Real) (hε : 0 < ε) :
    ∃ N : ℕ, ∀ a : ι,
      N ≤ idx a → S.prefixCoherencePrice k - ε ≤ coherenceFamilyObservable a := by
  have h_prefix_le_liminf :
      S.prefixCoherencePrice k
        ≤ Filter.liminf coherenceFamilyObservable
            (Filter.comap idx Filter.atTop) := by
    have h1 : S.prefixCoherencePrice k ≤ M.coherenceRelaxedOutputPrice :=
      M.prefix_coherence_le_relaxed_output k
    have h2 :
        Filter.liminf coherenceFamilyObservable
            (Filter.comap idx Filter.atTop)
          = M.coherenceRelaxedOutputPrice :=
      D.coherence_liminf_eq_relaxed
    rw [h2]; exact h1
  have hiff :=
    (Filter.le_liminf_iff'
      (f := Filter.comap idx Filter.atTop)
      (u := coherenceFamilyObservable)
      D.coherence_cobounded
      D.coherence_bounded).mp h_prefix_le_liminf
  have h_eventually :
      ∀ᶠ a in Filter.comap idx Filter.atTop,
        S.prefixCoherencePrice k - ε ≤ coherenceFamilyObservable a :=
    hiff (S.prefixCoherencePrice k - ε) (by linarith)
  rw [Filter.eventually_comap] at h_eventually
  rw [Filter.eventually_atTop] at h_eventually
  obtain ⟨N, hN⟩ := h_eventually
  refine ⟨N, ?_⟩
  intro a hNa
  exact hN (idx a) hNa a rfl

/-! ## §4. Full atom-7 witness bundle

This structure packages all three components' three-way sandwiches
(scalar prefix ≤ relaxed ≤ limit) plus the filter-eventual lower-bound
versions. It is the atom-7-flavor witness consumed downstream by the
GP-216 bridge composition layer when the residual void
`selected_projected_prefix_limit_sandwich_source` is paid. -/

structure GP216PrefixLimitSandwichWitness
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) where
  /-- Self-tax: prefix ≤ relaxed output for every `k`. -/
  selfTax_prefix_le_relaxed :
    ∀ k : ℕ, S.prefixSelfTaxPrice k ≤ M.selfTaxRelaxedOutputPrice
  /-- Self-tax: relaxed output ≤ limit price. -/
  selfTax_relaxed_le_limit :
    M.selfTaxRelaxedOutputPrice ≤ S.selfTaxLimitPrice
  /-- Cross-defect: prefix ≤ relaxed output for every `k`. -/
  crossDefect_prefix_le_relaxed :
    ∀ k : ℕ, S.prefixCrossDefectPrice k ≤ M.crossDefectRelaxedOutputPrice
  /-- Cross-defect: relaxed output ≤ limit price. -/
  crossDefect_relaxed_le_limit :
    M.crossDefectRelaxedOutputPrice ≤ S.crossDefectLimitPrice
  /-- Coherence: prefix ≤ relaxed output for every `k`. -/
  coherence_prefix_le_relaxed :
    ∀ k : ℕ, S.prefixCoherencePrice k ≤ M.coherenceRelaxedOutputPrice
  /-- Coherence: relaxed output ≤ limit price. -/
  coherence_relaxed_le_limit :
    M.coherenceRelaxedOutputPrice ≤ S.coherenceLimitPrice

/-- **Forward constructor**: every
`LeraySelfTaxMeasureValuedOutputLimitSource` already carries the six
load-bearing inequalities we need; the witness is just a rebundling
of those fields. No analytic input required. -/
def GP216PrefixLimitSandwichWitness.fromOutputLimitSource
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S) :
    GP216PrefixLimitSandwichWitness M where
  selfTax_prefix_le_relaxed := M.prefix_self_tax_le_relaxed_output
  selfTax_relaxed_le_limit := M.self_tax_relaxed_output_le_limit
  crossDefect_prefix_le_relaxed := M.prefix_cross_defect_le_relaxed_output
  crossDefect_relaxed_le_limit := M.cross_defect_relaxed_output_le_limit
  coherence_prefix_le_relaxed := M.prefix_coherence_le_relaxed_output
  coherence_relaxed_le_limit := M.coherence_relaxed_output_le_limit

/-- **Direct prefix-le-limit projection** from the witness. The
transitive composition of the two stored fields delivers the headline
sandwich endpoint without re-traversing the relaxed price. -/
theorem GP216PrefixLimitSandwichWitness.selfTax_prefix_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    (W : GP216PrefixLimitSandwichWitness M) (k : ℕ) :
    S.prefixSelfTaxPrice k ≤ S.selfTaxLimitPrice :=
  le_trans (W.selfTax_prefix_le_relaxed k) W.selfTax_relaxed_le_limit

theorem GP216PrefixLimitSandwichWitness.crossDefect_prefix_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    (W : GP216PrefixLimitSandwichWitness M) (k : ℕ) :
    S.prefixCrossDefectPrice k ≤ S.crossDefectLimitPrice :=
  le_trans (W.crossDefect_prefix_le_relaxed k) W.crossDefect_relaxed_le_limit

theorem GP216PrefixLimitSandwichWitness.coherence_prefix_le_limit
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    (W : GP216PrefixLimitSandwichWitness M) (k : ℕ) :
    S.prefixCoherencePrice k ≤ S.coherenceLimitPrice :=
  le_trans (W.coherence_prefix_le_relaxed k) W.coherence_relaxed_le_limit

end

end ZtareProofs.NS.Atom7Sandwich
