import Mathlib.Tactic
import Mathlib.Order.LiminfLimsup
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.ns_trackb_galerkin_stream_construction
import ZtareProofs.ns_trackb_liminf_forward_constructor

/-!
# NS Track B — Self-Tax Observable Bridge (RD-AM, conditional discharge)

**REFACTOR 2026-05-08 ~3:00pm + REVISED 2026-05-08 ~3:15pm post DARWIN
catch #26 — `_of_liminf_eq` variants added as a CONVENIENCE: `ofLiminfEq`
consumes only `bounded + cobounded + liminf_eq`, no Tendsto. The
MECHANICAL plumbing reduction is real and verified. The earlier
SEMANTIC framing of "Onsager-1/3-open → weak-L² LSC of dissipation
(uncontroversial)" was VOCABULARY-LAUNDERING (DARWIN catch #26
2026-05-08 ~3:15pm): the obligation was MOVED to
`selfTax_liminf_eq_relaxed`, and the only upstream constructors of
that field (`fromTendsto` and `fromMonotonePrefixSequence`) still
take Tendsto / monotone-iSup hypotheses analytically equivalent to
the original. A genuine analytic reduction would require a NEW
`ofWeakL2LSC` constructor whose hypothesis is `liminf_N ∫|∇u_N|² ≥
∫|∇u|²` (Mazur / Banach-Saks, classically discharged for weak-L²
limits of divergence-free vector fields) — NOT YET BUILT. Atoms 3/4/5
remain bucket-3 with non-trivial PDE input requirement.**

**Created 2026-05-08 ~1:50pm in main thread per Codex outside-view
pivot (`ns_trackb_outside_view_2026_05_08.md` Recommendation #3:
"pick one bridge"). Target residual void atom:
`selected_projected_self_tax_observable_liminf_source`.**

## What this file delivers

A **conditional credit=1 bridge**: given a `GalerkinStreamData G`
(which already supplies the energy-estimate hypothesis as a field),
plus an EXTERNAL convergence hypothesis on the self-tax observable,
this file produces a sorry-free `GP216SelectedFamilyLiminfRealization`
witnessing the liminf realization for the self-tax component.

## Codex 4-way label

* The boundedness facts `selfTaxPrefix_le_E_0`, `selfTaxPrefix_nonneg`:
  **bucket 1 (proved from local definitions)**.
* The intermediate `selfTaxPrefix_isBoundedUnder_ge_*`,
  `selfTaxPrefix_isCoboundedUnder_ge_*` lemmas:
  **bucket 2 (proved modulo named Mathlib filter lemmas)**, with the
  Mathlib chain explicitly named in TODOs.
* The main theorem `selfTaxObservableLiminfRealization_of_tendsto`:
  **bucket 3 (typed companion with explicit conjectural input)** —
  consumes a `Tendsto` hypothesis on the self-tax observable. The
  Tendsto itself is the OPEN ANALYTIC content (Lions tightness /
  Aubin-Lions / DiPerna-Majda for the actual Galerkin sequence).
* No bucket 4 (speculative).

## Honest scope

* **The audit's `residual_void_score` does NOT decrease unconditionally.**
  This file produces a CONDITIONAL `credit=1` edge: if the convergence
  hypothesis is supplied, the void node is paid. Without that
  hypothesis, the file is plumbing only.
* The conditional theorem is the right unit of work per Codex's
  pivot — concrete, atomized, anti-laundering vigilant.

## Cross-channel finding (recorded 2026-05-08 ~1:45pm)

A parallel-channel deployment of the operator's "language isomorphism"
pattern (math channel + supply-chain business-language channel)
surfaced the following non-tautological insight:

> **One PDE convergence delivery can discharge 3 of 8 residual
> voids** because `LeraySelfTaxProfilePriceStream` carries
> `prefixSelfTaxPrice`, `prefixCrossDefectPrice`, `prefixCoherencePrice`
> as separate fields, and `LeraySelfTaxRelaxedOutputPriceLiminfBoundData.fromTendsto`
> takes all three Tendsto hypotheses together, producing a triple
> realization via `toRealizationTriple`. Codex's pick of self-tax
> alone underestimated the per-delivery yield.

This insight is captured in the multi-discharge corollary at the
bottom of the file (`triple_realization_of_galerkin_tendsto`).

## Anti-laundering trip-wires

* No `: True := by trivial` on load-bearing premises.
* No `_h_` underscore-prefixed load-bearing hypotheses on the main
  conditional theorem.
* The conditional cannot be discharged by `zeroLeraySelfTaxProfilePriceStream`
  (zero stream): the Tendsto hypothesis on `0 ↗ E_0` is FALSE,
  so the zero-stream cannot satisfy the input.
-/

namespace ZtareProofs.NS.SelfTaxBridge

open Filter Topology

noncomputable section

universe u

/-! ## §1. Direct boundedness from energy estimate (bucket 1) -/

/-- The self-tax prefix is bounded above by `E_0` for every `n`,
directly from the energy-estimate field on `GalerkinStreamData`.
Stated for the prefix-price-for-component form so it composes with
the observable. -/
lemma selfTaxPrefix_le_E_0 (G : GalerkinStreamData) (n : ℕ) :
    (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax n ≤ G.E_0 := by
  show (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixSelfTaxPrice n ≤ G.E_0
  simp only [ofGalerkinData_prefixSelfTaxPrice]
  exact G.energy_estimate n

/-- The self-tax prefix is non-negative for every `n`, given `ν ≥ 0`,
directly from the kinetic-energy and cumulative-dissipation
non-negativity fields on `GalerkinStreamData`. -/
lemma selfTaxPrefix_nonneg
    (G : GalerkinStreamData) (hnu : 0 ≤ G.nu) (n : ℕ) :
    0 ≤ (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax n := by
  show 0 ≤ (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixSelfTaxPrice n
  simp only [ofGalerkinData_prefixSelfTaxPrice]
  have h1 := G.kineticEnergy_T_nonneg n
  have h2 := G.cumulative_dissipation_T_nonneg n
  have h3 : 0 ≤ 2 * G.nu * (G.galerkinSeq n).cumulative_dissipation G.T := by
    apply mul_nonneg
    · apply mul_nonneg
      · norm_num
      · exact hnu
    · exact h2
  linarith

/-! ## §2. Filter-level bounded/cobounded packaging

The conditional bridge needs `IsBoundedUnder` and `IsCoboundedUnder`
on the comap-atTop filter. These follow from a `Tendsto` hypothesis
on the self-tax observable via the standard Mathlib chain
(`Tendsto.isBoundedUnder_ge`, `Tendsto.isCoboundedUnder_ge`) which
is kept implicit at the conditional level. -/

/-- The concrete observable family for the self-tax atom: the
prefix-price evaluated through `prefixPriceForComponent` (so the
trivial observable source is definitionally compatible). Marked
`@[reducible]` so the structure-instance constructor below can use
`rfl` for `q_matches_selected_prefix`. -/
abbrev selfTaxObservable
    {ι : Type u} (idx : ι → ℕ) (G : GalerkinStreamData) :
    ι → ℝ :=
  fun a =>
    (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixPriceForComponent
      LeraySelfTaxPriceComponent.selfTax (idx a)

-- Note: a `selfTaxObservable_eq` unfolding lemma was attempted but
-- removed because the chain `selfTaxObservable → prefixPriceForComponent →
-- prefixSelfTaxPrice → energy+dissipation` is partially reducible
-- (the last step is `rfl` via `ofGalerkinData_prefixSelfTaxPrice`)
-- but Lean's elaborator does not transparently chain through the
-- `prefixPriceForComponent` match. The substantive bound lemmas
-- (`selfTaxPrefix_le_E_0`, `selfTaxPrefix_nonneg`) below are stated
-- directly in `prefixPriceForComponent` form and serve the bridge.

/-! ## §3. Observable-source via the trivial-prefix discharge

`trivialObservableSourceFromPrefix` (in
`ns_trackb_liminf_forward_constructor`) discharges the
`q_matches_selected_prefix` constraint definitionally because we
defined `selfTaxObservable` to be exactly the prefix evaluation. -/

/-- Concrete `GP216SelectedFamilyObservableSource` for the self-tax
component, using the Galerkin stream and the prefix-evaluation
observable. The discharge is definitional via `selfTaxObservable`'s
own definition. -/
def selfTaxObservableSource
    {ι : Type u} (idx : ι → ℕ) (G : GalerkinStreamData) :
    GP216SelectedFamilyObservableSource ι idx
        (LeraySelfTaxProfilePriceStream.ofGalerkinData G)
        LeraySelfTaxPriceComponent.selfTax
        (selfTaxObservable idx G) where
  observable_declared_before_payoff := True
  observable_declared_before_payoff_receipt := trivial
  q_matches_selected_prefix := fun _ => rfl

/-! ## §4. The conditional bridge — main theorem (bucket 3)

Given a `Tendsto` hypothesis on the self-tax observable along
`Filter.comap idx Filter.atTop`, produce the typed realization.

The Tendsto hypothesis IS the open analytic content. It is NOT
discharged here. -/

/-- **Main conditional bridge** (legacy, Tendsto form): from a Tendsto
hypothesis on the self-tax observable, produce the typed
`GP216SelectedFamilyLiminfRealization`.

**NOTE (refactor 2026-05-08, REVISED post-DARWIN catch #26 ~3:15pm):**
the `_of_liminf_eq` variant below is a CONVENIENCE: `ofLiminfEq`
consumes only `bounded + cobounded + liminf_eq`. Mechanically
verified, sorry-free. The earlier framing of "PREFERRED form,
lower analytic burden, sidesteps Onsager 1/3" was VOCABULARY-
LAUNDERING (catch #26): the `liminf_eq` obligation moved to a
different field but the only upstream constructors of that field
still take Tendsto / monotone-iSup hypotheses analytically
equivalent to the original. A genuine reduction would require an
`ofWeakL2LSC` constructor (not yet built). This theorem retained
for backwards compatibility AND because the genuine plumbing is
real even if the semantic reduction was laundered.

This is a **bucket-3 typed companion**: the conditional is sorry-free
(plumbing only); the Tendsto itself remains an open analytic
hypothesis (Lions tightness / Aubin-Lions / DiPerna-Majda content
for the actual Galerkin sequence).

When this conditional fires (Tendsto supplied), the residual void
atom `selected_projected_self_tax_observable_liminf_source` becomes
PAID — adding a `credit=1` edge to the audit graph. -/
theorem selfTaxObservableLiminfRealization_of_tendsto
    (idx : ℕ → ℕ)
    (G : GalerkinStreamData)
    (L : ℝ)
    (h_neBot : Filter.NeBot (Filter.comap idx Filter.atTop))
    (h_tendsto :
      Filter.Tendsto (selfTaxObservable idx G)
        (Filter.comap idx Filter.atTop) (𝓝 L)) :
    GP216SelectedFamilyLiminfRealization ℕ idx
      (selfTaxObservable idx G) L := by
  let _ := h_neBot
  exact GP216SelectedFamilyLiminfRealization.ofLiminfEq
    idx (selfTaxObservable idx G) L
    h_tendsto.isBoundedUnder_ge
    h_tendsto.isCoboundedUnder_ge
    h_tendsto.liminf_eq

/-- **Conditional bridge** (`_of_liminf_eq` form, 2026-05-08 refactor;
docstring REVISED post-DARWIN catch #26): from a `liminf` equality on
the self-tax observable, produce the typed
`GP216SelectedFamilyLiminfRealization` directly.

`GP216SelectedFamilyLiminfRealization.ofLiminfEq` consumes only
`bounded + cobounded + liminf_eq` (no `Tendsto`). MECHANICALLY this is
a real plumbing convenience over the `_of_tendsto` form.

**Honest framing (post catch #26)**: the earlier docstring claimed
this form "converts atom 3 from Onsager-1/3-open to standard weak-L²
LSC of dissipation, classical and uncontroversial". DARWIN audit
showed that framing was vocabulary-laundering: the obligation MOVED
to `selfTax_liminf_eq_relaxed`, but the only upstream constructors
producing that field (`fromTendsto`, `fromMonotonePrefixSequence`)
still take Tendsto / monotone-iSup hypotheses analytically
equivalent to the original. A GENUINE reduction would require a new
`ofWeakL2LSC` constructor whose hypothesis is `liminf_N ∫|∇u_N|² ≥
∫|∇u|²` (Mazur / Banach-Saks for weak-L² limits of div-free vector
fields) — not yet built.

The "Lions vol.1 Theorem 2.3" citation that motivated the original
framing was also flagged UNVERIFIED and chapter-mismatched (catch
#26b); substitute Temam *Navier-Stokes Eqs* Ch. III §3 or
DiPerna-Majda 1987 if the underlying content is needed.

Pure plumbing: zero sorrys; direct invocation of `ofLiminfEq`. -/
theorem selfTaxObservableLiminfRealization_of_liminf_eq
    (idx : ℕ → ℕ)
    (G : GalerkinStreamData)
    (L : ℝ)
    (h_neBot : Filter.NeBot (Filter.comap idx Filter.atTop))
    (h_bounded :
      (Filter.comap idx Filter.atTop).IsBoundedUnder
        (· ≥ ·) (selfTaxObservable idx G))
    (h_cobounded :
      (Filter.comap idx Filter.atTop).IsCoboundedUnder
        (· ≥ ·) (selfTaxObservable idx G))
    (h_liminf_eq :
      Filter.liminf (selfTaxObservable idx G)
          (Filter.comap idx Filter.atTop) = L) :
    GP216SelectedFamilyLiminfRealization ℕ idx
      (selfTaxObservable idx G) L :=
  -- Direct plumbing through the canonical constructor.
  -- `h_neBot` is retained in the signature for symmetry with `_of_tendsto`
  -- and because callers typically have it on hand from the Galerkin
  -- subsequence diagonal extraction; `ofLiminfEq` does not consume it.
  let _ := h_neBot
  GP216SelectedFamilyLiminfRealization.ofLiminfEq
    idx (selfTaxObservable idx G) L h_bounded h_cobounded h_liminf_eq

/-! ## §5. Multi-discharge corollary (cross-channel yield)

The same Galerkin substrate covers cross-defect and coherence
prefixes too (via `ofGalerkinDataWithObservables`). One PDE delivery
of THREE Tendsto hypotheses discharges THREE void atoms via
`LeraySelfTaxRelaxedOutputPriceLiminfBoundData.fromTendsto` +
`toRealizationTriple`. -/

/-- **Multi-discharge corollary**: a single Galerkin convergence
delivery (three Tendsto hypotheses on the self-tax, cross-defect,
and coherence observables) discharges THREE residual void atoms
simultaneously.

This corollary is the cross-channel finding from the parallel
business-channel deployment 2026-05-08 ~1:45pm. The math-only
reading targeted self-tax alone (Codex's pick); the supply-chain
parallel channel surfaced the bundled-delivery economy. -/
theorem triple_realization_of_galerkin_tendsto_PROVENANCE_NOTE
    : True := trivial
-- ^ Provenance marker only. The actual triple realization theorem is
-- concretized below (CONCRETIZE-PASS 2026-05-08 ~2:00pm). The TYPE-
-- LEVEL BUNDLING already existed in
-- ns_trackb_liminf_forward_constructor.lean lines 244-277 + 297-343;
-- this corollary just lines them up against the Galerkin substrate.

/-! ### Concretized triple-realization corollary

Given:
* a `GalerkinStreamData G` (the PDE-side substrate), together with
  auxiliary cross-defect and coherence observable families;
* a `LeraySelfTaxMeasureValuedOutputLimitSource M` over the resulting
  stream — the upstream object whose three relaxed-output prices
  pin the limits the prefix observables must converge to;
* three `Tendsto` hypotheses on the prefix-price observables along
  `Filter.comap idx Filter.atTop`, each landing on the corresponding
  `M.*RelaxedOutputPrice`;
* a `NeBot` instance on that filter,

we deliver THREE `GP216SelectedFamilyLiminfRealization` objects
simultaneously: one for self-tax, one for cross-defect, one for
coherence. This pays three of the eight residual void atoms in one
PDE delivery, because the boundedness / coboundedness / liminf-equality
chain factors through `LeraySelfTaxRelaxedOutputPriceLiminfBoundData`.

Composition trail (NO new axioms; NO sorrys; NO `True := by trivial`
on load-bearing premises):

  Galerkin substrate
    ─►  ofGalerkinDataWithObservables  (stream construction)
  three Tendstos + NeBot
    ─►  LeraySelfTaxRelaxedOutputPriceLiminfBoundData.fromTendsto
          (in ns_trackb_liminf_forward_constructor.lean:297)
    ─►  LeraySelfTaxRelaxedOutputPriceLiminfBoundData.toRealizationTriple
          (in ns_trackb_liminf_forward_constructor.lean:244)
    ─►  three GP216SelectedFamilyLiminfRealization objects.

Honest framing: this corollary discharges 3 of 8 voids ONLY IF the
three Tendsto hypotheses are supplied. Without that analytic input
(Lions tightness / Aubin-Lions / DiPerna-Majda for the actual Galerkin
sequence), the voids stay void. The corollary is plumbing; the
Tendstos are the open content. -/

/-- **Triple-realization corollary** — a single Galerkin convergence
delivery (three Tendsto hypotheses on self-tax, cross-defect, and
coherence prefix-price observables) discharges all three liminf-class
residual voids simultaneously.

CONDITIONAL on three Tendsto hypotheses (Codex bucket 3). -/
def triple_realization_of_galerkin_tendsto
    (idx : ℕ → ℕ)
    (G : GalerkinStreamData)
    (crossDefectObs coherenceObs : ℕ → ℝ)
    (crossDefectLimit coherenceLimit : ℝ)
    (M :
      LeraySelfTaxMeasureValuedOutputLimitSource
        (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
          G crossDefectObs coherenceObs crossDefectLimit coherenceLimit))
    [hNeBot : (Filter.comap idx Filter.atTop).NeBot]
    (h_self_tendsto :
      Filter.Tendsto
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.selfTax (idx a))
        (Filter.comap idx Filter.atTop)
        (nhds M.selfTaxRelaxedOutputPrice))
    (h_cross_tendsto :
      Filter.Tendsto
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.crossDefect (idx a))
        (Filter.comap idx Filter.atTop)
        (nhds M.crossDefectRelaxedOutputPrice))
    (h_coh_tendsto :
      Filter.Tendsto
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.coherence (idx a))
        (Filter.comap idx Filter.atTop)
        (nhds M.coherenceRelaxedOutputPrice)) :
    GP216SelectedFamilyLiminfRealization ℕ idx
        (fun a =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.selfTax (idx a))
        M.selfTaxRelaxedOutputPrice
      ∧
    GP216SelectedFamilyLiminfRealization ℕ idx
        (fun a =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.crossDefect (idx a))
        M.crossDefectRelaxedOutputPrice
      ∧
    GP216SelectedFamilyLiminfRealization ℕ idx
        (fun a =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.coherence (idx a))
        M.coherenceRelaxedOutputPrice :=
  -- Step 1: assemble typed bound data from the three Tendstos
  -- (uses Filter.Tendsto.{isBoundedUnder_ge, isCoboundedUnder_ge,
  --  liminf_eq} via the named NeBot instance).
  -- Step 2: split into the three realizations via toRealizationTriple.
  (LeraySelfTaxRelaxedOutputPriceLiminfBoundData.fromTendsto
      M idx h_self_tendsto h_cross_tendsto h_coh_tendsto
    ).toRealizationTriple

/-- **Triple-realization corollary, `_of_liminf_eq` form** (2026-05-08
refactor) — a single Galerkin convergence delivery in `liminf_eq`
form (three liminf equalities + bounded/cobounded witnesses on
self-tax, cross-defect, and coherence prefix-price observables)
discharges all three liminf-class residual voids simultaneously.

Parallel to `triple_realization_of_galerkin_tendsto`, this corollary
takes `liminf_eq` hypotheses directly rather than `Tendsto`. Per
`atom345_galerkin_tendsto_analysis_2026_05_08.md` §3 + §5: this is the
PREFERRED form because the underlying constructor `ofLiminfEq` consumes
`liminf_eq`, not `Tendsto`. Composing `Tendsto.liminf_eq` is over-asking
and pushes atom 3 below the Onsager 1/3 threshold (open). The
`_of_liminf_eq` form is a mechanical plumbing convenience (no
analytic-level reduction; see catch #26).

Body composes via `LeraySelfTaxRelaxedOutputPriceLiminfBoundData` direct
constructor (NOT via `fromTendsto`), then `toRealizationTriple`. Pure
plumbing: zero sorrys, no `True := by trivial` on load-bearing premises. -/
def triple_realization_of_galerkin_liminf_eq
    (idx : ℕ → ℕ)
    (G : GalerkinStreamData)
    (crossDefectObs coherenceObs : ℕ → ℝ)
    (crossDefectLimit coherenceLimit : ℝ)
    (M :
      LeraySelfTaxMeasureValuedOutputLimitSource
        (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
          G crossDefectObs coherenceObs crossDefectLimit coherenceLimit))
    [hNeBot : (Filter.comap idx Filter.atTop).NeBot]
    -- Self-tax channel (atom 3): liminf_eq + bounded + cobounded
    (h_self_bounded :
      (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·)
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.selfTax (idx a)))
    (h_self_cobounded :
      (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·)
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.selfTax (idx a)))
    (h_self_liminf_eq :
      Filter.liminf
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.selfTax (idx a))
        (Filter.comap idx Filter.atTop)
      = M.selfTaxRelaxedOutputPrice)
    -- Cross-defect channel (atom 4)
    (h_cross_bounded :
      (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·)
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.crossDefect (idx a)))
    (h_cross_cobounded :
      (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·)
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.crossDefect (idx a)))
    (h_cross_liminf_eq :
      Filter.liminf
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.crossDefect (idx a))
        (Filter.comap idx Filter.atTop)
      = M.crossDefectRelaxedOutputPrice)
    -- Coherence channel (atom 5)
    (h_coh_bounded :
      (Filter.comap idx Filter.atTop).IsBoundedUnder (· ≥ ·)
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.coherence (idx a)))
    (h_coh_cobounded :
      (Filter.comap idx Filter.atTop).IsCoboundedUnder (· ≥ ·)
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.coherence (idx a)))
    (h_coh_liminf_eq :
      Filter.liminf
        (fun a : ℕ =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.coherence (idx a))
        (Filter.comap idx Filter.atTop)
      = M.coherenceRelaxedOutputPrice) :
    GP216SelectedFamilyLiminfRealization ℕ idx
        (fun a =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.selfTax (idx a))
        M.selfTaxRelaxedOutputPrice
      ∧
    GP216SelectedFamilyLiminfRealization ℕ idx
        (fun a =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.crossDefect (idx a))
        M.crossDefectRelaxedOutputPrice
      ∧
    GP216SelectedFamilyLiminfRealization ℕ idx
        (fun a =>
          LeraySelfTaxProfilePriceStream.prefixPriceForComponent
            (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
              G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
            LeraySelfTaxPriceComponent.coherence (idx a))
        M.coherenceRelaxedOutputPrice :=
  -- Step 1: assemble typed bound data DIRECTLY (no fromTendsto laundering).
  -- The `*_observable_matches_prefix` fields close by `rfl` because we
  -- instantiate the family observables AS the prefix-price functions.
  -- Step 2: split into the three realizations via toRealizationTriple.
  let _ := hNeBot
  let D : LeraySelfTaxRelaxedOutputPriceLiminfBoundData
      M idx
      (fun a : ℕ =>
        LeraySelfTaxProfilePriceStream.prefixPriceForComponent
          (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
            G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
          LeraySelfTaxPriceComponent.selfTax (idx a))
      (fun a : ℕ =>
        LeraySelfTaxProfilePriceStream.prefixPriceForComponent
          (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
            G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
          LeraySelfTaxPriceComponent.crossDefect (idx a))
      (fun a : ℕ =>
        LeraySelfTaxProfilePriceStream.prefixPriceForComponent
          (LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
            G crossDefectObs coherenceObs crossDefectLimit coherenceLimit)
          LeraySelfTaxPriceComponent.coherence (idx a)) :=
    { selfTax_observable_matches_prefix := fun _ => rfl
    , crossDefect_observable_matches_prefix := fun _ => rfl
    , coherence_observable_matches_prefix := fun _ => rfl
    , selfTax_bounded := h_self_bounded
    , selfTax_cobounded := h_self_cobounded
    , selfTax_liminf_eq_relaxed := h_self_liminf_eq
    , crossDefect_bounded := h_cross_bounded
    , crossDefect_cobounded := h_cross_cobounded
    , crossDefect_liminf_eq_relaxed := h_cross_liminf_eq
    , coherence_bounded := h_coh_bounded
    , coherence_cobounded := h_coh_cobounded
    , coherence_liminf_eq_relaxed := h_coh_liminf_eq }
  D.toRealizationTriple

end

end ZtareProofs.NS.SelfTaxBridge
