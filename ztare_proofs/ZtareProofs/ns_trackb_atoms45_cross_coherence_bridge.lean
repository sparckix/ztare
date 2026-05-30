import Mathlib.Tactic
import Mathlib.Order.LiminfLimsup
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.ns_trackb_galerkin_stream_construction
import ZtareProofs.ns_trackb_liminf_forward_constructor

/-!
# NS Track B — Cross-Defect & Coherence Observable Bridges (atoms 4 & 5)

**Created 2026-05-08 ~3:30pm. Sister bridge to
`ns_trackb_self_tax_observable_bridge.lean` (atom 3). Targets residual void
atoms `selected_projected_cross_defect_observable_liminf_source` (#4) and
`selected_projected_coherence_observable_liminf_source` (#5).**

These two atoms share the same shape as atom 3 but for the cross-defect and
coherence observables on the Galerkin substrate. Per
`ns_trackb_residual_void_4way_inventory_2026_05_08.md`, they are bucket 3:
typed companions consuming a `liminf_eq` hypothesis as the open analytic
content.

## What this file delivers

A pair of **conditional credit=1 bridges**: given a `GalerkinStreamData G`
(plus auxiliary cross-defect and coherence observable families wired through
`ofGalerkinDataWithObservables`) and a `liminf_eq` hypothesis on the
corresponding observable, this file produces sorry-free
`GP216SelectedFamilyLiminfRealization` objects witnessing the liminf
realization for each component.

## Why `_of_liminf_eq` and NOT `_of_tendsto` (MECHANICAL ONLY — DARWIN catch #26)

Per atoms 3/4/5 analysis (`atom345_galerkin_tendsto_analysis_2026_05_08.md`)
AND the subsequent anti-laundering correction
(`anti_laundering_catch_26_vocabulary_relabel_refactor_2026_05_08.md`):

* **Mechanical plumbing reduction (real):**
  `GP216SelectedFamilyLiminfRealization.ofLiminfEq` consumes only
  `bounded + cobounded + liminf_eq` (no Tendsto, sorry-free). Routing
  through `Tendsto.liminf_eq` over-asks at the Lean-construction layer,
  so the `_of_liminf_eq` form is a strictly cheaper plumbing convenience.

* **Semantic analytic-level reduction (LAUNDERED — do NOT claim):**
  An earlier version of this docstring framed the `_of_liminf_eq` form as
  living at "standard weak-L² LSC of dissipation (uncontroversial)" and
  contrasted it with a "Tendsto form pushing below the Onsager 1/3
  threshold (open)". DARWIN catch #26 demoted that framing as
  vocabulary-laundering: the obligation `liminf q F = relaxed_output_price`
  was MOVED to the `crossDefect_liminf_eq_relaxed` /
  `coherence_liminf_eq_relaxed` field of the upstream relaxed-output-price
  liminf-bound data, and every existing forward constructor of that field
  (`fromTendsto`, `fromMonotonePrefixSequence`) STILL takes Tendsto or
  monotone-iSup hypotheses analytically equivalent to the original. The
  Onsager-1/3 question has not been moved to a more elementary level.
  A genuine analytic reduction would require a NEW upstream constructor
  (e.g. `ofWeakL2LSC` with hypothesis
  `liminf_N ∫|∇u_N|² ≥ ∫|∇u|²`); that constructor does NOT exist in this
  build.

## Codex 4-way label

* The two main theorems `crossDefectObservableLiminfRealization_of_liminf_eq`,
  `coherenceObservableLiminfRealization_of_liminf_eq`:
  **bucket 3 (typed companion with explicit conjectural input)** — consume a
  `liminf_eq` hypothesis. The `liminf_eq` itself remains the open analytic
  content. Per DARWIN catch #26, do NOT label this content as "weak-L² LSC
  of cross-defect / coherence functionals (uncontroversial)" — discharging
  it on the Galerkin substrate via the available upstream constructors
  still requires Tendsto / monotone-iSup hypotheses.
* The observable defs and source defs: **bucket 1** (definitional plumbing).

## Honest scope

* These conditionals do NOT decrease the audit's `residual_void_score`
  unconditionally. Each produces a CONDITIONAL `credit=1` edge: if the
  `liminf_eq` hypothesis is supplied, the corresponding void node is paid.
  Without that hypothesis, the file is plumbing only.
* The `liminf_eq` hypothesis is the precise open analytic content for each
  channel — identification of `Filter.liminf` value with the relaxed
  output price. Per DARWIN catch #26, this is NOT a free / "weak-L² LSC"
  obligation: every existing upstream constructor on the Galerkin
  substrate still requires Tendsto- or monotone-iSup-level input. The
  cost is comparable to atom 1's, NOT below it.

## Anti-laundering trip-wires

* `crossDefectObservable`, `coherenceObservable` are `abbrev` (not `def`) —
  same lesson as catch #25 from atom 3 (transparent elaboration).
* `LeraySelfTaxProfilePriceStream.prefixPriceForComponent stream component k`
  named form, NOT anonymous-projection (catch #25 lesson).
* No `: True := by trivial` on load-bearing premises.
* The conditionals cannot be discharged by a zero-stream when the
  `liminf_eq` value is non-zero: the `liminf_eq` hypothesis on `0` against a
  non-zero target is FALSE.

## Coordination

Sister agent is concurrently editing `ns_trackb_self_tax_observable_bridge.lean`
to add `_of_liminf_eq` variants for atom 3. This file is SEPARATE and does
NOT edit that file.
-/

namespace ZtareProofs.NS.CrossCoherenceBridge

open Filter Topology

noncomputable section

universe u

/-! ## §1. Cross-Defect & Coherence observable defs (bucket 1)

Both observables are defined on the `ofGalerkinDataWithObservables` stream,
which carries the auxiliary cross-defect and coherence observable families
the caller supplies. By construction, the stream's
`prefixCrossDefectPrice = crossDefectObs` and
`prefixCoherencePrice = coherenceObs` (cf.
`ns_trackb_galerkin_stream_construction.lean:144-145`), so
`prefixPriceForComponent` evaluated at `crossDefect` / `coherence` reduces
to the auxiliary observables. We expose these as `abbrev` so the structure
constructor below can discharge `q_matches_selected_prefix` by `rfl`. -/

/-- The concrete cross-defect observable family for atom 4: prefix-price
evaluated through `prefixPriceForComponent` at the `crossDefect` component.
`abbrev` for transparent elaboration (catch #25 lesson). -/
abbrev crossDefectObservable
    {ι : Type u} (idx : ι → ℕ)
    (G : GalerkinStreamData)
    (crossDefectObs coherenceObs : ℕ → ℝ)
    (crossDefectLimit coherenceLimit : ℝ) :
    ι → ℝ :=
  fun a =>
    LeraySelfTaxProfilePriceStream.prefixPriceForComponent
      (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
        G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
      LeraySelfTaxPriceComponent.crossDefect (idx a)

/-- The concrete coherence observable family for atom 5: prefix-price
evaluated through `prefixPriceForComponent` at the `coherence` component.
`abbrev` for transparent elaboration (catch #25 lesson). -/
abbrev coherenceObservable
    {ι : Type u} (idx : ι → ℕ)
    (G : GalerkinStreamData)
    (crossDefectObs coherenceObs : ℕ → ℝ)
    (crossDefectLimit coherenceLimit : ℝ) :
    ι → ℝ :=
  fun a =>
    LeraySelfTaxProfilePriceStream.prefixPriceForComponent
      (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
        G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
      LeraySelfTaxPriceComponent.coherence (idx a)

/-! ## §2. Observable-source defs via the trivial-prefix discharge

`trivialObservableSourceFromPrefix` (in
`ns_trackb_liminf_forward_constructor`) discharges the
`q_matches_selected_prefix` constraint definitionally because we defined the
observables to be exactly the `prefixPriceForComponent` evaluation. -/

/-- Concrete `GP216SelectedFamilyObservableSource` for the cross-defect
component. Discharge is definitional via `crossDefectObservable`'s own
definition. -/
def crossDefectObservableSource
    {ι : Type u} (idx : ι → ℕ)
    (G : GalerkinStreamData)
    (crossDefectObs coherenceObs : ℕ → ℝ)
    (crossDefectLimit coherenceLimit : ℝ) :
    GP216SelectedFamilyObservableSource ι idx
        (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
          G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
        LeraySelfTaxPriceComponent.crossDefect
        (crossDefectObservable idx G crossDefectObs coherenceObs
          crossDefectLimit coherenceLimit) where
  observable_declared_before_payoff := True
  observable_declared_before_payoff_receipt := trivial
  q_matches_selected_prefix := fun _ => rfl

/-- Concrete `GP216SelectedFamilyObservableSource` for the coherence
component. Discharge is definitional via `coherenceObservable`'s own
definition. -/
def coherenceObservableSource
    {ι : Type u} (idx : ι → ℕ)
    (G : GalerkinStreamData)
    (crossDefectObs coherenceObs : ℕ → ℝ)
    (crossDefectLimit coherenceLimit : ℝ) :
    GP216SelectedFamilyObservableSource ι idx
        (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
          G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
        LeraySelfTaxPriceComponent.coherence
        (coherenceObservable idx G crossDefectObs coherenceObs
          crossDefectLimit coherenceLimit) where
  observable_declared_before_payoff := True
  observable_declared_before_payoff_receipt := trivial
  q_matches_selected_prefix := fun _ => rfl

/-! ## §3. The conditional bridges — main theorems (bucket 3)

Given a `liminf_eq` hypothesis on the cross-defect (resp. coherence)
observable along `Filter.comap idx Filter.atTop`, plus bounded/cobounded
witnesses, produce the typed `GP216SelectedFamilyLiminfRealization`.

The `liminf_eq` hypothesis IS the open analytic content for each channel.
It is NOT discharged here. Specifically:

* For atom 4 (cross-defect): identification of `Filter.liminf` of the
  prefix cross-defect price with `M.crossDefectRelaxedOutputPrice`.
* For atom 5 (coherence): identification of `Filter.liminf` of the prefix
  coherence price with `M.coherenceRelaxedOutputPrice`.

**Anti-laundering note (DARWIN catch #26).** A previous version of this
docstring labelled atom 4 as "Aubin-Lions class" and atom 5 as
"DiPerna-Majda class" and asserted that, at the `liminf` level, both sit
"below the Onsager 1/3 threshold (uncontroversial weak-L² LSC)" while a
`Tendsto` form would be open. That contrast was vocabulary-laundering: it
renames the hypothesis (Tendsto → liminf_eq) without exhibiting any
constructor of the relevant relaxed-output-price liminf-bound field whose
discharge is classically easier than the Tendsto / monotone-iSup
hypotheses already required upstream. We retain the `_of_liminf_eq`
plumbing (mechanically real) and drop the strictly-weaker-analytic-level
claim. Cf.
`anti_laundering_catch_26_vocabulary_relabel_refactor_2026_05_08.md`. -/

/-- **Main conditional bridge for atom 4** (`_of_liminf_eq` form): from a
`liminf_eq` hypothesis on the cross-defect observable, produce the typed
`GP216SelectedFamilyLiminfRealization`.

Sorry-free plumbing: direct invocation of
`GP216SelectedFamilyLiminfRealization.ofLiminfEq`.

`h_neBot` is retained in the signature for symmetry with the Tendsto form
and because callers typically have it on hand from the Galerkin subsequence
diagonal extraction; `ofLiminfEq` does not consume it. -/
theorem crossDefectObservableLiminfRealization_of_liminf_eq
    (idx : ℕ → ℕ)
    (G : GalerkinStreamData)
    (crossDefectObs coherenceObs : ℕ → ℝ)
    (crossDefectLimit coherenceLimit : ℝ)
    (L : ℝ)
    (h_neBot : Filter.NeBot (Filter.comap idx Filter.atTop))
    (h_bounded :
      (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·)
        (crossDefectObservable idx G crossDefectObs coherenceObs
          crossDefectLimit coherenceLimit))
    (h_cobounded :
      (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·)
        (crossDefectObservable idx G crossDefectObs coherenceObs
          crossDefectLimit coherenceLimit))
    (h_liminf_eq :
      Filter.liminf
          (crossDefectObservable idx G crossDefectObs coherenceObs
            crossDefectLimit coherenceLimit)
          (Filter.comap idx Filter.atTop) = L) :
    GP216SelectedFamilyLiminfRealization ℕ idx
      (crossDefectObservable idx G crossDefectObs coherenceObs
        crossDefectLimit coherenceLimit) L :=
  let _ := h_neBot
  GP216SelectedFamilyLiminfRealization.ofLiminfEq
    idx
    (crossDefectObservable idx G crossDefectObs coherenceObs
      crossDefectLimit coherenceLimit)
    L h_bounded h_cobounded h_liminf_eq

/-- **Main conditional bridge for atom 5** (`_of_liminf_eq` form): from a
`liminf_eq` hypothesis on the coherence observable, produce the typed
`GP216SelectedFamilyLiminfRealization`.

Sorry-free plumbing: direct invocation of
`GP216SelectedFamilyLiminfRealization.ofLiminfEq`. -/
theorem coherenceObservableLiminfRealization_of_liminf_eq
    (idx : ℕ → ℕ)
    (G : GalerkinStreamData)
    (crossDefectObs coherenceObs : ℕ → ℝ)
    (crossDefectLimit coherenceLimit : ℝ)
    (L : ℝ)
    (h_neBot : Filter.NeBot (Filter.comap idx Filter.atTop))
    (h_bounded :
      (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·)
        (coherenceObservable idx G crossDefectObs coherenceObs
          crossDefectLimit coherenceLimit))
    (h_cobounded :
      (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·)
        (coherenceObservable idx G crossDefectObs coherenceObs
          crossDefectLimit coherenceLimit))
    (h_liminf_eq :
      Filter.liminf
          (coherenceObservable idx G crossDefectObs coherenceObs
            crossDefectLimit coherenceLimit)
          (Filter.comap idx Filter.atTop) = L) :
    GP216SelectedFamilyLiminfRealization ℕ idx
      (coherenceObservable idx G crossDefectObs coherenceObs
        crossDefectLimit coherenceLimit) L :=
  let _ := h_neBot
  GP216SelectedFamilyLiminfRealization.ofLiminfEq
    idx
    (coherenceObservable idx G crossDefectObs coherenceObs
      crossDefectLimit coherenceLimit)
    L h_bounded h_cobounded h_liminf_eq

end

end ZtareProofs.NS.CrossCoherenceBridge
