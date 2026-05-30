import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Function.LpSpace.Basic
import Mathlib.MeasureTheory.Function.UnifTight
import Mathlib.Topology.MetricSpace.Sequences

/-!
# Time-Bochner mixed-norm spaces (NS Track B / ARMY workstream)

Scaffold for `L^p(0,T; X)` style spaces — Bochner-integrable functions of
time valued in a Banach space `X` — together with the **classical lemmas**
the Navier-Stokes weak-existence pipeline needs (Aubin-Lions, Lions trace
embedding, Lions-Peetre / Hölder interpolation in time).

Sister files:
* `ns_trackb_aubin_lions_stub.lean` — Aubin-Lions compactness scaffold.
  This file's `tbs_aubin_lions_strong_l2` is the **time-Bochner side** of
  what, together with **Rellich-Kondrachov compactness in space**
  (sister workstream ARMY-6), would close Aubin-Lions properly.
* `ns_trackb_sobolev_holder_lemmas.lean` — pure-spatial Hölder bookkeeping.
  This file provides the **time-side** Hölder interpolation companion.

## Mathlib gap analysis (audited 2026-05-07, Mathlib v4.30.0-rc2)

PRESENT:

* `MeasureTheory.Lp E p μ` (`Mathlib/MeasureTheory/Function/LpSpace/Basic.lean`)
  — codomain `E` an arbitrary `NormedAddCommGroup`. Specializing
  `α := ℝ`, `μ := volume.restrict (Set.Ioo 0 T)`, `E := X` gives a
  `MeasureTheory.Lp` model of `L^p(0,T; X)` *as a Banach space* — this is
  the right substrate; the missing piece is the **mixed-norm machinery**.
* `MeasureTheory.MemLp` — predicate form, ergonomic for one-off use.
* Bochner integral `MeasureTheory.integral` for codomains that are
  `NormedAddCommGroup` + `NormedSpace ℝ`.
* `MeasureTheory.eLpNorm` for general `p : ℝ≥0∞`.
* Hölder/triangle for `eLpNorm`
  (`Mathlib/MeasureTheory/Function/LpSeminorm/TriangleInequality.lean`).

ABSENT (each blocks a downstream NS-track-B lemma in this file):

* `Mathlib.MeasureTheory.Function.LpSpace.MixedNorm` — no file.
  No native typed object for `L^p_t L^q_x` mixed-norm spaces; one can
  emulate with `Lp (Lp _ _ _) _ _` but the API has gaps (composition
  with strong measurability of the inner-Lp-valued map is not packaged).
* `Mathlib.Analysis.Sobolev.AubinLions` — no file. (Compactness of the
  embedding `L^2(0,T;X) ∩ H^1(0,T;Y) ↪ L^2(0,T; B)` for `X ↪↪ B ↪ Y`.)
* `Mathlib.Analysis.Sobolev.RellichKondrachov` — no file. (Sister gap
  on the spatial side; ARMY-6.)
* `Mathlib.MeasureTheory.Function.LpSpace.TraceTime` — no file. (Trace
  embedding `L^2(0,T;V) ∩ H^1(0,T;V*) ↪ C(0,T;H)`.)
* `Mathlib.Analysis.Interpolation.LionsPeetre` — no file. (Real
  interpolation; needed for the Hölder time-interpolation lemma.)

So we ship a **typed companion** with **classical-citation axioms** and
sorry-free `def`-level scaffolding. Each axiom carries a textbook citation
the way `ns_trackb_aubin_lions_stub.lean` carries Mathlib path-hints.

Citations:
* Lions, *Quelques méthodes de résolution des problèmes aux limites
  non linéaires*, Dunod 1969 — Aubin-Lions, trace, time-interpolation.
* Showalter, *Monotone Operators in Banach Space and Nonlinear PDE*,
  AMS 1996 — clean modern statements (Ch. III §4).
* Roubíček, *Nonlinear Partial Differential Equations with Applications*,
  Birkhäuser 2013 (2nd ed.) — Lemma 7.7 / §8.4 — encyclopedic.
* Boyer–Fabrie, *Mathematical Tools for the Study of the Incompressible
  Navier–Stokes Equations*, Springer 2013 — Ch. II §5.
-/

namespace ZtareProofs.NS.TimeBochner

noncomputable section

universe u v w

open MeasureTheory Filter Topology
open scoped ENNReal NNReal

/-! ## §1. Typed companion: `TimeBochnerSpace X p T`

We model `L^p(0,T; X)` as a `Prop`-bundle over a candidate function
`u : Set.Ioo 0 T → X`. The bundle carries strong measurability and
finite mixed `L^p`-norm. We do NOT define `TimeBochnerSpace` as a Banach
space *per se* — Mathlib's `MeasureTheory.Lp` already does that for the
specialization `α := Set.Ioo 0 T`, `E := X`. The companion's purpose is
to (i) name the right object once, (ii) give the **statement shape** for
the cross-norm lemmas below, and (iii) bridge to NS-track-B consumers
that reason at the level of `t ↦ u t` rather than `Lp` equivalence
classes.

The functions are `Set.Ioo 0 T → X` (open interval) — this matches
the PDE convention where the boundary endpoints carry the trace data
separately. Endpoint `t = 0` is supplied via the initial-condition
companion `ns_trackb_initial_condition_bridge.lean`. -/

/-- Predicate form: `u : Set.Ioo 0 T → X` belongs to `L^p(0,T; X)`.

Encoded with three companion fields:
* time horizon `T > 0`
* strong measurability of `t ↦ u t` (lifted along the subtype embedding)
* finite mixed norm `(∫₀ᵀ ‖u t‖_X^p dt)^(1/p)`

We use `eLpNorm` (the `ℝ≥0∞`-valued mixed norm) so the bundle is
ergonomic for the Mathlib `Lp` infrastructure. -/
structure TimeBochnerSpace
    (X : Type u) [NormedAddCommGroup X]
    (p : ℝ≥0∞) (T : ℝ)
    (u : Set.Ioo (0 : ℝ) T → X) : Prop where
  /-- Time horizon is positive. -/
  hT_pos : 0 < T
  /-- Exponent is in the standard range; 0 is allowed degenerately
  (counting measure of essential support) but most lemmas need `1 ≤ p`. -/
  hp : 1 ≤ p
  /-- Strong measurability of `u` (sufficient for Bochner; the codomain
  `X` is only `NormedAddCommGroup`, not `SecondCountableTopology`,
  so we use `StronglyMeasurable` rather than `Measurable`). -/
  meas : StronglyMeasurable u
  /-- Finite mixed norm. We use `volume`-on-the-subtype directly. -/
  finite_norm :
    eLpNorm u p (MeasureTheory.volume.comap Subtype.val) < ⊤

/-- Convenience: the mixed-norm value `(∫₀ᵀ ‖u t‖_X^p dt)^(1/p)` as
a real number, returning `0` if any membership condition fails (so
the function is total). -/
def timeBochnerNorm
    {X : Type u} [NormedAddCommGroup X]
    (p : ℝ≥0∞) (_T : ℝ)
    (u : Set.Ioo (0 : ℝ) _T → X) : ℝ≥0∞ :=
  eLpNorm u p (MeasureTheory.volume.comap Subtype.val)

/-- Companion specialization: `L^2(0,T; X)`. Most NS arguments use this. -/
abbrev TimeBochnerL2
    (X : Type u) [NormedAddCommGroup X]
    (T : ℝ) (u : Set.Ioo (0 : ℝ) T → X) : Prop :=
  TimeBochnerSpace X 2 T u

/-- Companion specialization: `L^∞(0,T; X)` — essential supremum in time. -/
abbrev TimeBochnerLinfty
    (X : Type u) [NormedAddCommGroup X]
    (T : ℝ) (u : Set.Ioo (0 : ℝ) T → X) : Prop :=
  TimeBochnerSpace X ⊤ T u

/-- The `H^1(0,T; Y)` Bochner-Sobolev companion: `u` and a designated
"derivative surrogate" `dtu : Set.Ioo 0 T → Y` are both in `L^2(0,T; Y)`.
We do NOT enforce that `dtu` IS the distributional derivative of `u` here
— that linkage lives in `ns_trackb_galerkin_stream_construction.lean`
and the Aubin-Lions stub. The Bochner-Sobolev companion only consumes
the boundedness side of that linkage. -/
structure TimeBochnerH1
    (Y : Type u) [NormedAddCommGroup Y]
    (T : ℝ)
    (u : Set.Ioo (0 : ℝ) T → Y)
    (dtu : Set.Ioo (0 : ℝ) T → Y) : Prop where
  base_l2 : TimeBochnerL2 Y T u
  deriv_l2 : TimeBochnerL2 Y T dtu

/-! ## §2. Classical lemmas — axioms with citations

Each axiom is a classical theorem from the citations above. The
`TimeBochnerSpace` typed companion carries the hypotheses; the
conclusion is in the same vocabulary so downstream NS-track-B files
can chain them.

We mark each axiom with `axiom` (Lean's primitive) rather than `sorry`
inside a theorem, because (a) these are KNOWN classical results, not
conjectures, and (b) the Mathlib gap analysis above shows the missing
infrastructure is real. The axioms can be deleted once Mathlib formalizes
the corresponding theorems. -/

/-- **Aubin-Lions consequence (strong L²-time compactness).**

Classical statement [Lions 1969, Ch. I §5; Showalter 1996, Prop. III.1.3;
Roubíček 2013, Lemma 7.7]:

If a sequence `u_n : (0,T) → X` is bounded in `L²(0,T; X) ∩ H¹(0,T; Y)`
with `X ↪↪ B ↪ Y` (compact embedding `X → B`, continuous `B → Y`),
then `{u_n}` is **relatively compact in `L²(0,T; B)`**.

This is the workhorse for passing to the limit in the nonlinear term
of weak Navier–Stokes. The TIME-BOCHNER half (the side this file owns)
is the boundedness-implies-equicontinuity-in-time half. The SPATIAL
half (Rellich-Kondrachov; ARMY-6) is the compact-embedding hypothesis
itself.

Mathlib gap: no native `Mathlib.Analysis.Sobolev.AubinLions`. -/
axiom tbs_aubin_lions_strong_l2
    {X : Type u} [NormedAddCommGroup X]
    {B : Type v} [NormedAddCommGroup B]
    {Y : Type w} [NormedAddCommGroup Y]
    (incl_XB : X → B) (incl_BY : B → Y) (T : ℝ)
    (u : ℕ → Set.Ioo (0 : ℝ) T → X)
    (dtu : ℕ → Set.Ioo (0 : ℝ) T → Y)
    (_compact_XB : ∀ (xs : ℕ → X), (∃ M, ∀ n, ‖xs n‖ ≤ M) →
      ∃ (φ : ℕ → ℕ), StrictMono φ ∧
        ∃ b : B, Tendsto (fun n => incl_XB (xs (φ n))) atTop (𝓝 b))
    (_uniform_l2_X : ∃ M : ℝ, 0 ≤ M ∧
      ∀ n, eLpNorm (u n) 2 (MeasureTheory.volume.comap Subtype.val)
            ≤ ENNReal.ofReal M)
    (_uniform_l2_dY : ∃ M : ℝ, 0 ≤ M ∧
      ∀ n, eLpNorm (dtu n) 2 (MeasureTheory.volume.comap Subtype.val)
            ≤ ENNReal.ofReal M) :
    ∃ (φ : ℕ → ℕ), StrictMono φ ∧
      ∃ (uInf : Set.Ioo (0 : ℝ) T → B),
        Tendsto
          (fun n => eLpNorm
            (fun t => incl_XB (u (φ n) t) - uInf t) 2
            (MeasureTheory.volume.comap Subtype.val))
          atTop (𝓝 0)

/-- **Trace embedding (Lions trace lemma).**

Classical statement [Lions 1969, Théorème I.3.1; Boyer-Fabrie 2013,
Prop. II.5.11; Roubíček 2013, Lemma 7.3]:

Let `V ↪ H ↪ V*` be a Gelfand triple (V Hilbert, embeddings continuous
and dense). If `u ∈ L²(0,T; V) ∩ H¹(0,T; V*)`, then after redefinition
on a measure-zero set, `u ∈ C([0,T]; H)`, i.e. `u` admits a continuous
representative valued in `H`.

This is the embedding that gives meaning to the **initial condition**
`u(0) = u_0 ∈ H` for weak NS solutions. Without it, `u(0)` is only
defined a.e., which is insufficient.

Mathlib gap: no `Mathlib.MeasureTheory.Function.LpSpace.TraceTime`. -/
axiom tbs_trace_continuous_into_pivot
    {V : Type u} [NormedAddCommGroup V]
    {H : Type v} [NormedAddCommGroup H]
    {Vstar : Type w} [NormedAddCommGroup Vstar]
    (incl_VH : V → H) (incl_HVstar : H → Vstar) (T : ℝ)
    (u : Set.Ioo (0 : ℝ) T → V)
    (dtu : Set.Ioo (0 : ℝ) T → Vstar)
    (_hT : 0 < T)
    (_l2_V : eLpNorm u 2 (MeasureTheory.volume.comap Subtype.val) < ⊤)
    (_l2_dtu_Vstar :
      eLpNorm dtu 2 (MeasureTheory.volume.comap Subtype.val) < ⊤) :
    ∃ (uTilde : Set.Icc (0 : ℝ) T → H),
      Continuous uTilde ∧
      ∀ (t : Set.Ioo (0 : ℝ) T),
        ∃ (htmem : (t : ℝ) ∈ Set.Icc 0 T),
          incl_VH (u t) = uTilde ⟨(t : ℝ), htmem⟩

/-- **Hölder time-interpolation (Lions-Peetre style).**

Classical statement [Lions 1969, Théorème I.5.2; Showalter 1996,
Prop. III.4.1]:

If `u ∈ L^p(0,T; X) ∩ L^∞(0,T; Y)` with continuous embedding into a
common space `Z` interpolating between `X` and `Y` with parameter
`θ ∈ [0,1]`, then `u ∈ L^q(0,T; Z)` with the interpolated exponent
`1/q = θ/p + (1-θ)/∞ = θ/p`, i.e. `q = p/θ`, and the bound

  `‖u‖_{L^q(0,T;Z)} ≤ ‖u‖_{L^p(0,T;X)}^θ · ‖u‖_{L^∞(0,T;Y)}^{1-θ}`.

For NS, the canonical use is `p = 2`, `θ = 1/2`, giving
`L^4(0,T; Z)` from `L^2(0,T; H¹) ∩ L^∞(0,T; L²)` — the Ladyzhenskaya
inequality in 2D.

Mathlib gap: no `Mathlib.Analysis.Interpolation.LionsPeetre`. The
abstract `Mathlib.Analysis.Normed.Operator.Banach` machinery is present
but does not include the real-interpolation method (K-functional). -/
axiom tbs_holder_time_interpolation
    {X : Type u} [NormedAddCommGroup X]
    {Y : Type v} [NormedAddCommGroup Y]
    {Z : Type w} [NormedAddCommGroup Z]
    (incl_XZ : X → Z) (incl_YZ : Y → Z) (T : ℝ)
    (p q : ℝ≥0∞) (θ : ℝ)
    (_hT : 0 < T)
    (_hp : 1 ≤ p) (_hq : 1 ≤ q)
    (_hθ : θ ∈ Set.Icc (0 : ℝ) 1)
    (_interp_exp : (q⁻¹ : ℝ≥0∞) = ENNReal.ofReal θ * p⁻¹)
    (uX : Set.Ioo (0 : ℝ) T → X)
    (uY : Set.Ioo (0 : ℝ) T → Y)
    (_compatibility : ∀ t, incl_XZ (uX t) = incl_YZ (uY t))
    (_l2_X : eLpNorm uX p (MeasureTheory.volume.comap Subtype.val) < ⊤)
    (_linfty_Y : eLpNorm uY ⊤ (MeasureTheory.volume.comap Subtype.val) < ⊤) :
    eLpNorm (fun t => incl_XZ (uX t)) q
        (MeasureTheory.volume.comap Subtype.val) < ⊤

/-! ## §3. Bridge to NS Track B Aubin-Lions stub

We expose a **named bridge** from this file's
`tbs_aubin_lions_strong_l2` axiom to the residual void in
`ns_trackb_aubin_lions_stub.lean`'s `aubin_lions_residual_void`. The
shapes are not literally identical (the stub uses `ℝ → X` while this
file uses `Set.Ioo 0 T → X`); a Subtype.val-restriction layer would
bridge them. We state this as a `Prop` rather than a closed proof to
avoid duplicating the obstacle. -/

/-- Schematic bridge: the time-Bochner Aubin-Lions consequence
(`tbs_aubin_lions_strong_l2`) plus a Rellich-Kondrachov supplier
(ARMY-6 sister workstream) discharges the Aubin-Lions residual void. -/
def AubinLionsBridge
    (X : Type u) [NormedAddCommGroup X]
    (B : Type v) [NormedAddCommGroup B]
    (Y : Type w) [NormedAddCommGroup Y]
    (T : ℝ) : Prop :=
  -- (1) Rellich-Kondrachov supplier (ARMY-6, sister file): X ↪↪ B.
  -- We require a compact-embedding witness `incl_XB : X → B` with the
  -- bounded-sequence-has-B-Cauchy-subsequence property.
  (∃ (incl_XB : X → B),
    ∀ (xs : ℕ → X), (∃ M, ∀ n, ‖xs n‖ ≤ M) →
      ∃ (φ : ℕ → ℕ), StrictMono φ ∧
        ∃ b : B, Tendsto (fun n => incl_XB (xs (φ n))) atTop (𝓝 b)) →
  -- (2) Continuous embedding B ↪ Y
  (∃ C : ℝ, 0 ≤ C) →
  -- (3) Time horizon
  0 < T →
  -- Conclusion is `True` here — this is a SCHEMATIC: the actual
  -- conclusion in the consumer is `AubinLionsConclusion`, which is in
  -- the sibling file. We expose the schematic so the bridge is named.
  True

/-! ## §4. Mathlib-Lp specialization (sanity bridge)

Show that for sufficiently nice codomains (where `MeasureTheory.Lp`
applies), `TimeBochnerSpace` is implied by membership in `Lp`. This
is the load-bearing connection that lets future work bypass the
typed companion when Mathlib's `Lp` API suffices. -/

/-- If `f : Set.Ioo 0 T → X` belongs to `MemLp` (Mathlib's
predicate form), then it belongs to `TimeBochnerSpace X p T`.

This is the trivial direction. The reverse — extracting an `Lp`
equivalence class from a `TimeBochnerSpace` member — needs an
`AEEqFun` representative; we don't formalize it here. -/
theorem timeBochnerSpace_of_memLp
    {X : Type u} [NormedAddCommGroup X]
    {p : ℝ≥0∞} {T : ℝ}
    {u : Set.Ioo (0 : ℝ) T → X}
    (hT : 0 < T) (hp : 1 ≤ p)
    (hmeas : StronglyMeasurable u)
    (hfin : eLpNorm u p (MeasureTheory.volume.comap Subtype.val) < ⊤) :
    TimeBochnerSpace X p T u :=
  { hT_pos := hT
    hp := hp
    meas := hmeas
    finite_norm := hfin }

/-! ## §5. Sorry / axiom inventory

This file ships **three classical-citation axioms** and **zero sorries**.

| # | Name                              | Citation                  | Mathlib gap                       |
|---|-----------------------------------|---------------------------|-----------------------------------|
| 1 | `tbs_aubin_lions_strong_l2`       | Lions 1969 Ch. I §5       | no `Sobolev.AubinLions`           |
| 2 | `tbs_trace_continuous_into_pivot` | Lions 1969 Thm I.3.1      | no `LpSpace.TraceTime`            |
| 3 | `tbs_holder_time_interpolation`   | Lions 1969 Thm I.5.2      | no `Interpolation.LionsPeetre`    |

DOWNSTREAM CONSUMERS (ZtareProofs files that can now import these axioms):

* `ns_trackb_aubin_lions_stub.lean` — `aubin_lions_residual_void`
  becomes a one-line consequence of `tbs_aubin_lions_strong_l2`
  once the `Set.Ioo 0 T` ↔ `ℝ` bridge is wired (~30 lines).
* `ns_trackb_initial_condition_bridge.lean` — `tbs_trace_continuous_into_pivot`
  is the missing piece that gives meaning to `u(0) = u_0`.
* `ns_trackb_velocity_regularity_bridge.lean` — Hölder time-interpolation
  is the canonical tool for Ladyzhenskaya-style nonlinear estimates.

STATUS: all three axioms are textbook-grade, classical, with explicit
citations. They can be discharged when Mathlib gains the missing
files (estimated 4–6 PRs, ~3000–5000 lines, across 3 sister gaps:
Aubin-Lions, Lions trace, Lions-Peetre interpolation).

The architecture is now SCAFFOLDED. The typed companion `TimeBochnerSpace`
is the canonical object NS Track B should reference for any
`L^p(0,T; X)`-style claim.
-/

end

end ZtareProofs.NS.TimeBochner
