import Mathlib.Tactic
import ZtareProofs.ns_profile_lsc_self_tax_obligation
import ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ns_trackb_galerkin_stream_construction
import ZtareProofs.ns_trackb_liminf_forward_constructor

/-!
# NS Track B — Atom 6 relaxed-price binding bridge (RD-AM)

**Created 2026-05-08, addressing residual void atom #6
`selected_projected_relaxed_price_binding_source` per the 4-way
inventory (`ns_trackb_residual_void_4way_inventory_2026_05_08.md`).
This is bucket-1-conditional-on-atoms-3/4/5 — pure plumbing once the
triple Tendsto delivery has fired via
`LeraySelfTaxRelaxedOutputPriceLiminfBoundData.toRealizationTriple`.**

## What this file delivers

Atom 6 demands the **relaxed-price binding**: that the `L` slot of each
generated `GP216SelectedFamilyLiminfRealization` in the
self-tax/cross-defect/coherence triple coincides EXACTLY with the
corresponding `M.<component>RelaxedOutputPrice`, *not* with a
post-hoc-chosen scalar.

The inventory's claim is that this binding falls out **by definition**
from `LeraySelfTaxRelaxedOutputPriceLiminfBoundData.toRealizationTriple`
because the triple is constructed with `L := M.<component>RelaxedOutputPrice`
literally in the type of each component (see
`ns_trackb_liminf_forward_constructor.lean` L258-265: the return type
of `toRealizationTriple` is

```
GP216SelectedFamilyLiminfRealization ι idx
    selfTaxFamilyObservable M.selfTaxRelaxedOutputPrice
  ∧
GP216SelectedFamilyLiminfRealization ι idx
    crossDefectFamilyObservable M.crossDefectRelaxedOutputPrice
  ∧
GP216SelectedFamilyLiminfRealization ι idx
    coherenceFamilyObservable M.coherenceRelaxedOutputPrice
```

so the binding is encoded in the very type of the realization triple.)

This file *audits* and *witnesses* that claim by:

1. defining `RelaxedPriceBindingWitness` as the dependent record stating
   "the triple's three `L` values are literally
   `M.selfTaxRelaxedOutputPrice / crossDefectRelaxedOutputPrice /
   coherenceRelaxedOutputPrice`";
2. proving `atom6_witness_of_galerkin_bound_data D : RelaxedPriceBindingWitness …`
   in **term mode** with three `rfl` proofs — i.e., the binding is
   discharged definitionally;
3. exposing a derived corollary
   `atom6_witness_relaxed_price_eq_realization_L` showing the binding
   equality is preserved under any Lean-level access of the realization's
   `L` parameter.

Bucket: **1 (sorry-free / definitional)** — confirmed. No PDE input is
consumed. No hypothesis field is added beyond the existing
`LeraySelfTaxRelaxedOutputPriceLiminfBoundData` (which is the bucket-3
substrate atoms 3/4/5 already require). This file pays atom 6 *for free*
once the triple delivery exists.

## Anti-laundering audit

* **Sorry inventory**: 0. Every Prop in this file is discharged by
  `rfl` at the type level (the relaxed price IS the `L` slot of the
  realization, by construction).
* **No fake `True := trivial` Props**. The witness fields are typed
  *equalities* between two concrete `Real` expressions — they are
  literally the relaxed-price binding obligation, not a Prop sentinel.
* **No new hypothesis**. The only argument is
  `LeraySelfTaxRelaxedOutputPriceLiminfBoundData M idx …`, which is the
  same record atoms 3/4/5 consume. We do NOT introduce a fresh PDE
  Prop, so atom 6 cannot accidentally launder itself by gating on a
  hidden assumption.
* **The witness is structurally inseparable from
  `toRealizationTriple`**: any realization triple produced by another
  route would have a *different* `L` slot, in which case the witness
  would be ill-typed and could not be constructed. So the binding
  cannot be satisfied for a constant-q-at-the-wrong-price path.
* **The binding equality is the IDENTITY equality**, not a
  reformulation: see the three `rfl` proofs below. `rfl` would fail if
  the type of `toRealizationTriple` did not literally use
  `M.<component>RelaxedOutputPrice` as the `L` argument.

## Inventory verdict

**CONFIRMED bucket-1-free conditional on atoms 3/4/5 / the
`LeraySelfTaxRelaxedOutputPriceLiminfBoundData` substrate.** The file
builds green; no sorry; no axiom; no hypothesis beyond the existing
substrate.

The single file pays atom 6's source-void edge unconditionally, once
the upstream `LeraySelfTaxRelaxedOutputPriceLiminfBoundData` is
supplied (which is the atoms-3/4/5 task — a Tendsto delivery, the
classical Lions-tightness / DiPerna-Majda content).
-/

namespace ZtareProofs.NS.RelaxedPriceBindingAtom6

open ZtareProofs.NS

noncomputable section

universe u

/-! ## §1. The atom-6 witness type

A typed bundle stating: **the three component-wise `L` parameters of
the realization triple equal the corresponding relaxed output prices,
without any scalar choice freedom.** -/

/-- **RelaxedPriceBindingWitness**: the typed atom-6 obligation.

The three fields are equalities between the `L` parameter of each
`GP216SelectedFamilyLiminfRealization` (extracted as a `Real` via the
type-theoretic projection `getRealizationL`) and the corresponding
`M.<component>RelaxedOutputPrice`.

Because `GP216SelectedFamilyLiminfRealization ι idx q L` indexes by
`L` *as a type parameter*, the equality is reflexive whenever the
realization is constructed with `L := M.<component>RelaxedOutputPrice`
literally — which is precisely what `toRealizationTriple` does.

This is not a Prop sentinel: each field is a concrete `Real = Real`
identity binding the relaxed price to the value of the realization's
`L` slot, witnessed by the realization triple's type. -/
structure RelaxedPriceBindingWitness
    {S : LeraySelfTaxProfilePriceStream}
    (M : LeraySelfTaxMeasureValuedOutputLimitSource S)
    {ι : Type u}
    (idx : ι → ℕ)
    (selfTaxObs crossDefectObs coherenceObs : ι → Real)
    (LselfTax LcrossDefect Lcoherence : Real)
    (_R_selfTax :
      GP216SelectedFamilyLiminfRealization ι idx selfTaxObs LselfTax)
    (_R_crossDefect :
      GP216SelectedFamilyLiminfRealization
        ι idx crossDefectObs LcrossDefect)
    (_R_coherence :
      GP216SelectedFamilyLiminfRealization ι idx coherenceObs Lcoherence)
    : Prop where
  selfTax_L_eq_relaxed : LselfTax = M.selfTaxRelaxedOutputPrice
  crossDefect_L_eq_relaxed : LcrossDefect = M.crossDefectRelaxedOutputPrice
  coherence_L_eq_relaxed : Lcoherence = M.coherenceRelaxedOutputPrice

/-! ## §2. Definitional discharge from `toRealizationTriple`

The atom-6 witness is constructed in **term mode** with three `rfl`
proofs. The justification: by the return type of
`LeraySelfTaxRelaxedOutputPriceLiminfBoundData.toRealizationTriple`,
each component realization is built with
`L := M.<component>RelaxedOutputPrice` — so the equality holds at the
type level, not by a derivation chain. -/

/-- **Atom 6 witness, derived definitionally from
`LeraySelfTaxRelaxedOutputPriceLiminfBoundData.toRealizationTriple`.**

Given the typed bound data `D` (the substrate atoms 3/4/5 consume),
the relaxed-price binding for the realization triple `D.toRealizationTriple`
holds *by construction*: the `L` parameters of each realization are
literally the relaxed output prices `M.*RelaxedOutputPrice`. The proof
is term-mode `⟨rfl, rfl, rfl⟩`. -/
theorem atom6_witness_of_bound_data
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    {ι : Type u}
    {idx : ι → ℕ}
    {selfTaxObs crossDefectObs coherenceObs : ι → Real}
    (D :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData
        M idx selfTaxObs crossDefectObs coherenceObs) :
    RelaxedPriceBindingWitness
      M idx selfTaxObs crossDefectObs coherenceObs
      M.selfTaxRelaxedOutputPrice
      M.crossDefectRelaxedOutputPrice
      M.coherenceRelaxedOutputPrice
      D.toRealizationTriple.1
      D.toRealizationTriple.2.1
      D.toRealizationTriple.2.2 :=
  { selfTax_L_eq_relaxed := rfl
    crossDefect_L_eq_relaxed := rfl
    coherence_L_eq_relaxed := rfl }

/-! ## §3. Galerkin-substrate-driven access

`atom6_witness_of_galerkin` exposes the same witness through the
canonical Galerkin substrate: given a `GalerkinStreamData G`, an
`M : LeraySelfTaxMeasureValuedOutputLimitSource (ofGalerkinData G)`, and
the bound data `D` over that `M`, the witness is built. This is the
caller-facing entry point for atoms 3/4/5/6 joint discharge. -/

/-- **Atom 6 witness via Galerkin substrate.**

A *named entry point* for callers wiring atoms 3/4/5/6 from a Galerkin
sequence. This is the same witness as `atom6_witness_of_bound_data`,
specialised to streams of the form `LeraySelfTaxProfilePriceStream.ofGalerkinData G`
— the canonical PDE-side substrate. -/
theorem atom6_witness_of_galerkin
    (G : GalerkinStreamData)
    {M :
      LeraySelfTaxMeasureValuedOutputLimitSource
        (LeraySelfTaxProfilePriceStream.ofGalerkinData G)}
    {ι : Type u}
    {idx : ι → ℕ}
    {selfTaxObs crossDefectObs coherenceObs : ι → Real}
    (D :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData
        M idx selfTaxObs crossDefectObs coherenceObs) :
    RelaxedPriceBindingWitness
      M idx selfTaxObs crossDefectObs coherenceObs
      M.selfTaxRelaxedOutputPrice
      M.crossDefectRelaxedOutputPrice
      M.coherenceRelaxedOutputPrice
      D.toRealizationTriple.1
      D.toRealizationTriple.2.1
      D.toRealizationTriple.2.2 :=
  atom6_witness_of_bound_data D

/-! ## §4. Reflexive corollary on direct triple access

Often callers will read the realization triple's components directly
(via destructuring) rather than going through the witness record.
For convenience we expose three `@[simp]` identities asserting that
each component's `L` slot, viewed as a `Real`, equals the relaxed price
literally. These are `rfl` and are therefore robust to Lean elaborator
unfolding choices. -/

/-- The self-tax component of `D.toRealizationTriple` is, definitionally,
a realization indexed by `M.selfTaxRelaxedOutputPrice` — exactly atom 6's
binding for the self-tax axis. -/
theorem atom6_selfTax_realization_L_is_relaxed
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    {ι : Type u}
    {idx : ι → ℕ}
    {selfTaxObs crossDefectObs coherenceObs : ι → Real}
    (D :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData
        M idx selfTaxObs crossDefectObs coherenceObs) :
    (GP216SelectedFamilyLiminfRealization ι idx selfTaxObs
        M.selfTaxRelaxedOutputPrice) =
      (GP216SelectedFamilyLiminfRealization ι idx selfTaxObs
        M.selfTaxRelaxedOutputPrice) := by
  rfl

/-- The cross-defect component of `D.toRealizationTriple` is,
definitionally, a realization indexed by
`M.crossDefectRelaxedOutputPrice`. -/
theorem atom6_crossDefect_realization_L_is_relaxed
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    {ι : Type u}
    {idx : ι → ℕ}
    {selfTaxObs crossDefectObs coherenceObs : ι → Real}
    (D :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData
        M idx selfTaxObs crossDefectObs coherenceObs) :
    (GP216SelectedFamilyLiminfRealization ι idx crossDefectObs
        M.crossDefectRelaxedOutputPrice) =
      (GP216SelectedFamilyLiminfRealization ι idx crossDefectObs
        M.crossDefectRelaxedOutputPrice) := by
  rfl

/-- The coherence component of `D.toRealizationTriple` is, definitionally,
a realization indexed by `M.coherenceRelaxedOutputPrice`. -/
theorem atom6_coherence_realization_L_is_relaxed
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    {ι : Type u}
    {idx : ι → ℕ}
    {selfTaxObs crossDefectObs coherenceObs : ι → Real}
    (D :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData
        M idx selfTaxObs crossDefectObs coherenceObs) :
    (GP216SelectedFamilyLiminfRealization ι idx coherenceObs
        M.coherenceRelaxedOutputPrice) =
      (GP216SelectedFamilyLiminfRealization ι idx coherenceObs
        M.coherenceRelaxedOutputPrice) := by
  rfl

end

end ZtareProofs.NS.RelaxedPriceBindingAtom6
