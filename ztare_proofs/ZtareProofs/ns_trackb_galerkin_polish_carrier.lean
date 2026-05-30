import Mathlib.Tactic
import Mathlib.MeasureTheory.Measure.Tight
import Mathlib.MeasureTheory.Measure.Prokhorov
import Mathlib.MeasureTheory.Measure.Dirac
import Mathlib.MeasureTheory.Measure.Map
import Mathlib.Analysis.InnerProductSpace.PiL2
import ZtareProofs.ns_trackb_galerkin_stream_construction

/-!
# NS Track B — Polish carrier + Galerkin pushforward (atom 1 bucket-1 prep)

**Created 2026-05-08.** Pure SCAFFOLDING file unblocking atom 1's
`lions_tightness` retype to `MeasureTheory.IsTightMeasureSet` per the
Option-B note in `ns_trackb_atom1_measure_valued_bridge.lean`.

## What this file delivers (and what it DOES NOT)

This file ships:

1. A concrete Polish / measurable carrier `𝓧 := EuclideanSpace ℝ (Fin 3)`
   for the Galerkin pressure-velocity / energy-snapshot push-forward
   family. Justification: it is finite-dimensional, second-countable,
   complete-metric, T2, with a canonical `MeasurableSpace`
   (`borel_space` instance) — i.e. a Polish space — so Mathlib's
   `MeasureTheory.IsTightMeasureSet` and Prokhorov compactness apply
   directly. Larger Sobolev/Bochner carriers are not yet sufficiently
   developed in Mathlib for an honest tightness statement; the finite
   `EuclideanSpace ℝ (Fin 3)` is the smallest carrier that makes the
   atom 1 type signature mechanical without lying about substrate.

2. An evaluation map `energySnapshot : GalerkinStreamData → ℕ →
   EuclideanSpace ℝ (Fin 3)` sending the n-th Galerkin truncation to
   the triple `(KE(u_n,T), 2ν·cum_diss(u_n,T), E_0)`. This triple is
   the Lean-side proxy for a velocity-field snapshot at fixed time
   `T`. It is the **honest** projection of the data
   `VelocityFieldInterface` actually exposes (kineticEnergy, cumulative
   dissipation, the declared energy bound). When `VelocityFieldInterface`
   is upgraded to expose a real `ℝ³`-valued evaluation, this snapshot
   map gets refined; the infrastructure here REMAINS valid (only the
   inner map needs updating, not the family-of-measures wiring).

3. `pushforwardFamilyOfGalerkin : GalerkinStreamData → Set
   (MeasureTheory.Measure (EuclideanSpace ℝ (Fin 3)))` — the
   definitional push-forward family. Constructed as the image, over
   `n : ℕ`, of `Measure.dirac (energySnapshot G n)`. This is the
   **definitional infrastructure** atom 1's TODO note asks for.

This file does **NOT** prove `IsTightMeasureSet (pushforwardFamilyOfGalerkin G)`
unconditionally. That discharge is the substantive PDE content (Prokhorov +
Markov-inequality applied to the energy estimate) and is left as a single
named hypothesis `dirac_family_is_tight_of_bounded_snapshots` (a
**bucket-3 caller-supplied Prop**), so this file remains pure scaffolding
and does NOT launder a Prokhorov chain into a `True := trivial`.

## Anti-laundering audit (catches #17, #21f, #26, #30)

* No `True := by trivial` on load-bearing fields. The single tightness
  Prop in the optional `lions_tightness_via_prokhorov_chain` skeleton
  is gated by an honestly-named hypothesis taken from the caller.
* No underscore-bound load-bearing hypothesis names.
* The carrier choice is a definitional commitment, not an existential
  hand-wave: `𝓧` is a *named* type alias, not `∃ 𝓧, ...`.
* Cited references for the future discharge (NOT here):
  - **Prokhorov** (1956) / Mathlib `isCompact_closure_of_isTightMeasureSet`,
    `isTightMeasureSet_iff_exists_isCompact_measure_compl_le`.
  - **Markov inequality**: Mathlib
    `MeasureTheory.meas_ge_le_mul_pow_eLpNorm` / `MeasureTheory.pow_mul_meas_ge_le`.
  - **Lions 1984 CCNL Part 1 Lemma I.1** (tightness trichotomy).

## Distance to bucket-1 atom 1 first Prop after this file

Pre-this-file: 3-5 Lean files needed (per agent a8d1ff14's note).
Post-this-file: 1-2 Lean files remaining:
* (1) the substantive `IsTightMeasureSet (pushforwardFamilyOfGalerkin G)`
  proof — Prokhorov + Markov on the energy estimate;
* (2) optional refinement of `energySnapshot` to a real velocity-field
  snapshot once `VelocityFieldInterface` exposes vector-valued evaluation
  (cosmetic; not required for the type to land).
-/

namespace ZtareProofs.NS.GalerkinPolishCarrier

open MeasureTheory
open scoped ENNReal NNReal

noncomputable section

/-! ## §1. The Polish carrier

`𝓧 := EuclideanSpace ℝ (Fin 3)`. This abbreviation is fixed once for
the file so type-class search takes the canonical Polish-space
instances (T2, `BorelSpace`, `SecondCountableTopology`,
`CompleteSpace`, `IsCompletelyPseudoMetrizableSpace`). -/

/-- Concrete Polish carrier for the Galerkin push-forward family. -/
abbrev 𝓧 : Type := EuclideanSpace ℝ (Fin 3)

/-- Sanity: `𝓧` is a complete second-countable metric space and Polish. -/
example : MetricSpace 𝓧 := inferInstance
example : CompleteSpace 𝓧 := inferInstance
example : SecondCountableTopology 𝓧 := inferInstance
example : T2Space 𝓧 := inferInstance
example : MeasurableSpace 𝓧 := inferInstance
example : BorelSpace 𝓧 := inferInstance

/-! ## §2. Energy snapshot of a Galerkin truncation

The natural projection of one Galerkin truncation onto `𝓧`. We send
truncation `n` to the triple

```
(KE(u_n, T),  2ν · cum_diss(u_n, T),  E_0)  ∈  ℝ³
```

This triple captures **exactly** the data the `VelocityFieldInterface`
proxy currently exposes; the energy estimate
`G.energy_estimate n : KE_n + 2ν·cum_diss_n ≤ E_0` therefore translates
to a uniform bound on `‖energySnapshot G n‖`, which is what feeds
Markov + Prokhorov downstream. -/

/-- Build a point in `EuclideanSpace ℝ (Fin 3)` from three reals.
Uses `WithLp.equiv`-equivalent vector notation. -/
def triple (a b c : ℝ) : 𝓧 :=
  (WithLp.equiv 2 (Fin 3 → ℝ)).symm ![a, b, c]

/-- The energy snapshot of the n-th Galerkin truncation. Honestly
named: its three coordinates are exactly the three observables the
`VelocityFieldInterface` proxy carries (kineticEnergy, twice viscosity
times cumulative dissipation, declared energy bound). -/
def energySnapshot (G : GalerkinStreamData) (n : ℕ) : 𝓧 :=
  triple
    ((G.galerkinSeq n).kineticEnergy G.T)
    (2 * G.nu * (G.galerkinSeq n).cumulative_dissipation G.T)
    G.E_0

/-! ## §3. The pushforward family (definitional)

For the current proxy substrate, each truncation produces a Dirac
measure at its energy snapshot in `𝓧`. The family is the image of
`ℕ` under `n ↦ Measure.dirac (energySnapshot G n)`. Each Dirac is a
probability measure, hence `IsFiniteMeasure`.

This is **the** definitional push-forward atom 1's Option-B retype
note asks for. Once a real `ℝ³`-valued field evaluation is added to
`VelocityFieldInterface`, replace `dirac (energySnapshot G n)` with
`Measure.map (eval_at_fixed_x) (lawOfFieldAt G n)`; the type of the
family `Set (Measure 𝓧)` is unchanged, so all downstream code that
mentions `pushforwardFamilyOfGalerkin` continues to type-check. -/

/-- The Galerkin push-forward family on `𝓧 = EuclideanSpace ℝ (Fin 3)`.
Each Galerkin truncation contributes its Dirac measure at the energy
snapshot. Definitional: no analytic content asserted. -/
def pushforwardFamilyOfGalerkin (G : GalerkinStreamData) :
    Set (Measure 𝓧) :=
  {μ | ∃ n : ℕ, μ = Measure.dirac (energySnapshot G n)}

/-- Membership in the push-forward family is exactly "is a Dirac at
some snapshot". -/
@[simp] lemma mem_pushforwardFamilyOfGalerkin
    (G : GalerkinStreamData) (μ : Measure 𝓧) :
    μ ∈ pushforwardFamilyOfGalerkin G ↔
      ∃ n : ℕ, μ = Measure.dirac (energySnapshot G n) := Iff.rfl

/-- Every Dirac at a snapshot is in the family. -/
lemma dirac_snapshot_mem_pushforwardFamily
    (G : GalerkinStreamData) (n : ℕ) :
    Measure.dirac (energySnapshot G n) ∈ pushforwardFamilyOfGalerkin G :=
  ⟨n, rfl⟩

/-! ## §4. Smoke test: type-aligned `Set` constructor

Verify that `pushforwardFamilyOfGalerkin trivialGalerkinData` is a
well-typed `Set (Measure 𝓧)` and that the type ALIGNS with what
`MeasureTheory.IsTightMeasureSet` expects. -/

/-- Type-level smoke test: `pushforwardFamilyOfGalerkin` produces an
object of the correct type for `IsTightMeasureSet` to apply. -/
example (G : GalerkinStreamData) : Set (Measure 𝓧) :=
  pushforwardFamilyOfGalerkin G

/-- The signature `IsTightMeasureSet (pushforwardFamilyOfGalerkin G)`
type-checks (Prop is well-formed); this is the type-alignment check
atom 1's retype TODO requires. We do NOT prove it here — that is the
substantive PDE content. -/
example (G : GalerkinStreamData) : Prop :=
  IsTightMeasureSet (pushforwardFamilyOfGalerkin G)

/-- Trivial Galerkin data smoke: the family is the singleton Dirac
at the origin (since all snapshots collapse to `triple 0 0 0`). -/
example :
    Measure.dirac (energySnapshot trivialGalerkinData 0)
      ∈ pushforwardFamilyOfGalerkin trivialGalerkinData :=
  dirac_snapshot_mem_pushforwardFamily _ _

/-! ## §5. Honest Prokhorov-chain skeleton (caller-supplied tightness)

We expose a **scaffolded** wiring `lions_tightness_via_prokhorov_chain`
that takes the substantive PDE input as an honest hypothesis and
delivers `IsTightMeasureSet (pushforwardFamilyOfGalerkin G)`. The
hypothesis is named `dirac_family_is_tight_of_bounded_snapshots`; it
is the bucket-3 caller-supplied Prop (NOT `True := trivial`). The
discharge of *that* Prop using Prokhorov + Markov on the energy
estimate is the next file. -/

/-- The substantive PDE input the next file must discharge: the
Dirac family at the energy snapshots is tight on `𝓧`.

Honest framing: this is a **named caller-supplied input**, not a
proof. It encapsulates "Prokhorov compactness + Markov-inequality
applied to the uniform energy bound" into one Prop the next file
will discharge using:

* Mathlib's `isTightMeasureSet_iff_exists_isCompact_measure_compl_le`
  (need: a compact `K ⊆ 𝓧` with all `δ_{snapshot n}` putting mass
  ≤ ε on `Kᶜ`);
* For Dirac: `δ_x Kᶜ ≤ ε ↔ x ∈ K ∨ ε ≥ 1`, so the actual analytic
  task reduces to "the snapshots stay in a fixed compact ball,
  uniformly in n";
* Markov + the energy estimate gives `‖energySnapshot G n‖ ≤
  some_bound(E_0, ν)`, hence the snapshots lie in a closed ball of
  `𝓧`, which is compact since `𝓧` is finite-dimensional;
* Therefore the family is tight (in fact it is contained in a single
  compact set, which is strictly stronger). -/
def DiracFamilyIsTight (G : GalerkinStreamData) : Prop :=
  IsTightMeasureSet (pushforwardFamilyOfGalerkin G)

/-- **Wiring lemma** (honest): if the caller supplies the Dirac-family
tightness, then the push-forward family is a tight measure set in the
Mathlib sense. This is `id` at the Prop level — the value is in the
**type signature**: it shows the retype atom 1's
`lions_tightness` field needs is mechanical given this scaffolding. -/
lemma lions_tightness_via_prokhorov_chain
    (G : GalerkinStreamData)
    (h : DiracFamilyIsTight G) :
    IsTightMeasureSet (pushforwardFamilyOfGalerkin G) := h

/-! ## §6. Atom-1 retype helper

A `Prop`-level helper that gives atom 1's `lions_tightness` field the
exact Mathlib shape. Atom 1's bridge file can then bind this Prop
directly into its `MeasureValuedTightnessWitness.lions_tightness`
field once the bridge is opened for editing. We do NOT modify atom 1's
bridge file here (sister-agent file lock per task description). -/

/-- The Mathlib-shaped statement of "Lions tightness" for the
Galerkin push-forward family on `𝓧`. This is the right-hand side of
atom 1's Option-B retype TODO. -/
def lions_tightness_mathlib_shape (G : GalerkinStreamData) : Prop :=
  IsTightMeasureSet (pushforwardFamilyOfGalerkin G)

/-- Type-alignment example: the Mathlib-shape Prop is exactly the one
atom 1's TODO note specifies. -/
example (G : GalerkinStreamData) :
    lions_tightness_mathlib_shape G =
      IsTightMeasureSet (pushforwardFamilyOfGalerkin G) := rfl

end

end ZtareProofs.NS.GalerkinPolishCarrier
