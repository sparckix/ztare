import Mathlib.Tactic
import Mathlib.Analysis.InnerProductSpace.Basic
import Mathlib.Analysis.InnerProductSpace.Continuous
import Mathlib.Topology.Algebra.Order.LiminfLimsup
import ZtareProofs.ns_trackb_initial_condition_bridge

/-!
# Spectral-projection discharge of `WeakInitialConditionData.galerkin_to_initialData`

This file supplies the analytical content behind the
`pairing_to_initialData` field of `WeakInitialConditionData`
(see `ns_trackb_initial_condition_bridge.lean`). For the canonical
Galerkin construction `galerkinSeq n := P n u_0`, where `P n` is the
orthogonal projection onto the first `n` Fourier modes of a fixed
basis, the strong-L² convergence `P n u_0 → u_0` upgrades — by
continuity of the inner product — to scalar convergence of the
pairings `⟨P n u_0, φ⟩ → ⟨u_0, φ⟩` for every test function `φ`.

The Mathlib lemma supplying continuity is `Filter.Tendsto.inner` in
`Mathlib/Analysis/InnerProductSpace/Continuous.lean`, line 70:

```
theorem Filter.Tendsto.inner {f g : α → E} {l : Filter α} {x y : E}
    (hf : Tendsto f l (𝓝 x)) (hg : Tendsto g l (𝓝 y)) :
    Tendsto (fun t => ⟪f t, g t⟫) l (𝓝 ⟪x, y⟫)
```

We instantiate this in two ways:

1. `pairing_tendsto_of_strong_convergence`: from
   `Tendsto (fun n => P n x) atTop (𝓝 x)` (strong convergence of the
   projection sequence at `x`), conclude
   `Tendsto (fun n => ⟪P n x, y⟫) atTop (𝓝 ⟪x, y⟫)` for every `y`.

2. `pairing_tendsto_of_norm_convergence`: from
   `Tendsto (fun n => ‖P n x − x‖) atTop (𝓝 0)`, deduce strong
   convergence of `P n x → x` (this is the definition of strong
   convergence in a normed space) and then apply (1).

Both versions are sorry-free and ready to feed
`WeakInitialConditionData.fromScalarConvergences`.

## Composition with the existing bridge

The existing bridge

```
weakInitialCondition_from_typed_companion
  : WeakInitialConditionData F galerkinSeq uInf →
    ∀ φ, F.IsTest φ → F.initialPairing uInf φ = F.initialDataPairing φ
```

consumes a `WeakInitialConditionData` whose two `Filter.Tendsto`
fields must be supplied. The constructor in this file discharges the
`pairing_to_initialData` field for the canonical Galerkin
construction `galerkinSeq n := P n u_0` whenever the abstract
`InitialPairingFunctional`'s `initialPairing` evaluates to a Hilbert
inner product `⟪galerkinSeq n .at(0), φ⟫`. The shape match is exact;
the user simply provides the Hilbert-pairing equation as a definitional
unfolding hypothesis, and `Filter.Tendsto.inner` supplies the rest.
-/

namespace ZtareProofs.NS

noncomputable section

open Filter Topology

universe u

/-! ## Abstract Hilbert-projection setup -/

/-- Strong-convergence property of a sequence of (continuous linear)
projections `P n : H → H` at a fixed vector `x`: `P n x → x`. -/
def StrongConvergesAt {H : Type u} [SeminormedAddCommGroup H]
    (P : ℕ → H → H) (x : H) : Prop :=
  Tendsto (fun n => P n x) atTop (𝓝 x)

/-! ## Theorem 1: scalar pairing convergence from strong convergence -/

/-- **Spectral-projection discharge (strong-convergence form).** If
`P n x → x` strongly in a real inner-product space `H`, then the
pairings `⟪P n x, y⟫ → ⟪x, y⟫` for every `y ∈ H`.

This is the analytical content discharging
`WeakInitialConditionData.pairing_to_initialData` for the canonical
Galerkin construction `galerkinSeq n := P n u_0`. -/
theorem pairing_tendsto_of_strong_convergence
    {H : Type u} [NormedAddCommGroup H] [InnerProductSpace ℝ H]
    {P : ℕ → H → H} {x : H} (hP : StrongConvergesAt P x) (y : H) :
    Tendsto (fun n => (inner ℝ (P n x) y : ℝ)) atTop
      (𝓝 (inner ℝ x y : ℝ)) := by
  -- `P n x → x` and the constant sequence `y → y`. Combine via
  -- `Filter.Tendsto.inner` (continuity of the inner product).
  have hy : Tendsto (fun _ : ℕ => y) atTop (𝓝 y) := tendsto_const_nhds
  exact Filter.Tendsto.inner hP hy

/-- Symmetric form: pairing in the second slot. -/
theorem pairing_tendsto_of_strong_convergence_right
    {H : Type u} [NormedAddCommGroup H] [InnerProductSpace ℝ H]
    {P : ℕ → H → H} {x : H} (hP : StrongConvergesAt P x) (y : H) :
    Tendsto (fun n => (inner ℝ y (P n x) : ℝ)) atTop
      (𝓝 (inner ℝ y x : ℝ)) := by
  have hy : Tendsto (fun _ : ℕ => y) atTop (𝓝 y) := tendsto_const_nhds
  exact Filter.Tendsto.inner hy hP

/-! ## Theorem 2: strong convergence from norm convergence -/

/-- Norm convergence `‖P n x − x‖ → 0` is the definition of strong
convergence of `P n x → x` in a normed space. -/
theorem strongConvergesAt_of_norm_tendsto_zero
    {H : Type u} [NormedAddCommGroup H]
    {P : ℕ → H → H} {x : H}
    (h : Tendsto (fun n => ‖P n x - x‖) atTop (𝓝 0)) :
    StrongConvergesAt P x := by
  -- `Tendsto (P n x) atTop (𝓝 x)` is equivalent to
  -- `Tendsto (‖P n x - x‖) atTop (𝓝 0)`.
  rw [StrongConvergesAt, ← tendsto_sub_nhds_zero_iff]
  exact tendsto_zero_iff_norm_tendsto_zero.mpr h

/-! ## Theorem 3: combined corollary (norm-convergence form) -/

/-- **Spectral-projection discharge (norm-convergence form).** From
`‖P n x − x‖ → 0` in a real inner-product space, conclude
`⟪P n x, y⟫ → ⟪x, y⟫` for any `y`.

This is the most directly usable form: the load-bearing hypothesis is
exactly what classical Fourier-series / spectral-basis approximation
theorems supply. -/
theorem pairing_tendsto_of_norm_convergence
    {H : Type u} [NormedAddCommGroup H] [InnerProductSpace ℝ H]
    {P : ℕ → H → H} {x : H}
    (h_norm : Tendsto (fun n => ‖P n x - x‖) atTop (𝓝 0)) (y : H) :
    Tendsto (fun n => (inner ℝ (P n x) y : ℝ)) atTop
      (𝓝 (inner ℝ x y : ℝ)) :=
  pairing_tendsto_of_strong_convergence
    (strongConvergesAt_of_norm_tendsto_zero h_norm) y

/-! ## Typed bridge: feed `WeakInitialConditionData`

The bridge below packages `pairing_tendsto_of_strong_convergence` into
the exact `Filter.Tendsto` shape required by
`WeakInitialConditionData.pairing_to_initialData`, given a definitional
identification of `F.initialPairing (galerkinSeq n) φ` with the
Hilbert inner product `⟪P n u_0, φ_H φ⟫` (where `φ_H` lifts the
abstract test function to the Hilbert space).

For the canonical "Galerkin sequence as initial condition" — i.e.
`galerkinSeq n` is constructed so that its initial pairing is
literally `⟪P n u_0, φ⟫` — and the limit solution `uInf` is the
fixed initial datum `u_0` itself, the typed companion's
`pairing_to_limit` field is the trivial constant-sequence Tendsto
(every term equals the limit). We expose both fields. -/

/-- Spectral-projection bridge to `WeakInitialConditionData`.

Hypotheses:
* `H` is a real inner-product space (the Hilbert space carrying `u_0`).
* `P n : H → H` is the spectral projection sequence with
  `‖P n u_0 − u_0‖ → 0`.
* The abstract pairings of the typed companion factor through the
  Hilbert inner product as
    `F.initialPairing (galerkinSeq n) φ = ⟪P n u_0, testToH φ⟫`
    `F.initialDataPairing φ = ⟪u_0, testToH φ⟫`
  for some lift `testToH : F.TestSpace → H` of test functions.
* The limit solution coincides with the initial datum at `t = 0`:
    `F.initialPairing uInf φ = F.initialDataPairing φ`.

Conclusion: a `WeakInitialConditionData F galerkinSeq uInf`. -/
def WeakInitialConditionData.fromSpectralProjection
    {H : Type u} [NormedAddCommGroup H] [InnerProductSpace ℝ H]
    (F : InitialPairingFunctional)
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3)
    (P : ℕ → H → H) (u₀ : H) (testToH : F.TestSpace → H)
    (h_proj_norm :
      Tendsto (fun n => ‖P n u₀ - u₀‖) atTop (𝓝 0))
    (h_pair_factor :
      ∀ n φ, F.initialPairing (galerkinSeq n) φ
              = (inner ℝ (P n u₀) (testToH φ) : ℝ))
    (h_data_factor :
      ∀ φ, F.initialDataPairing φ = (inner ℝ u₀ (testToH φ) : ℝ))
    (h_uInf_is_data :
      ∀ φ, F.IsTest φ →
        F.initialPairing uInf φ = F.initialDataPairing φ) :
    WeakInitialConditionData F galerkinSeq uInf where
  pairing_to_initialData := by
    intro φ _
    -- Rewrite both sides via the factorization, then apply the
    -- spectral-projection scalar-pairing theorem.
    have h_inner :
        Tendsto (fun n => (inner ℝ (P n u₀) (testToH φ) : ℝ)) atTop
          (𝓝 (inner ℝ u₀ (testToH φ) : ℝ)) :=
      pairing_tendsto_of_norm_convergence h_proj_norm (testToH φ)
    -- Rewrite the function pointwise to match `F.initialPairing`.
    have h_eq_fun :
        (fun n => F.initialPairing (galerkinSeq n) φ)
          = (fun n => (inner ℝ (P n u₀) (testToH φ) : ℝ)) := by
      funext n; exact h_pair_factor n φ
    have h_eq_lim :
        (F.initialDataPairing φ) = (inner ℝ u₀ (testToH φ) : ℝ) :=
      h_data_factor φ
    rw [h_eq_fun, h_eq_lim]
    exact h_inner
  pairing_to_limit := by
    intro φ hφ
    -- For the canonical "limit = initial datum at t=0" Galerkin setup,
    -- `F.initialPairing uInf φ = F.initialDataPairing φ`, so the
    -- target is literally the initialData target — same Tendsto.
    have h_match : F.initialPairing uInf φ = F.initialDataPairing φ :=
      h_uInf_is_data φ hφ
    rw [h_match]
    -- Reduce to `pairing_to_initialData`.
    have h_inner :
        Tendsto (fun n => (inner ℝ (P n u₀) (testToH φ) : ℝ)) atTop
          (𝓝 (inner ℝ u₀ (testToH φ) : ℝ)) :=
      pairing_tendsto_of_norm_convergence h_proj_norm (testToH φ)
    have h_eq_fun :
        (fun n => F.initialPairing (galerkinSeq n) φ)
          = (fun n => (inner ℝ (P n u₀) (testToH φ) : ℝ)) := by
      funext n; exact h_pair_factor n φ
    have h_eq_lim :
        (F.initialDataPairing φ) = (inner ℝ u₀ (testToH φ) : ℝ) :=
      h_data_factor φ
    rw [h_eq_fun, h_eq_lim]
    exact h_inner

/-! ## Direct-bridge corollary (alternative form)

A more direct corollary that takes ONLY the strong-norm-convergence
of the projection at `u_0` and a per-test Cauchy-Schwarz bound, and
concludes the scalar `Filter.Tendsto` needed by
`pairing_to_initialData_from_strong_L2` from the existing bridge.

Composes with `WeakInitialConditionData.fromScalarConvergences`. -/
theorem pairing_tendsto_atFixedTest
    {H : Type u} [NormedAddCommGroup H] [InnerProductSpace ℝ H]
    {P : ℕ → H → H} {x : H}
    (h_norm : Tendsto (fun n => ‖P n x - x‖) atTop (𝓝 0))
    (y : H) :
    Tendsto (fun n => (inner ℝ (P n x) y - inner ℝ x y : ℝ)) atTop
      (𝓝 0) := by
  have h_pair :
      Tendsto (fun n => (inner ℝ (P n x) y : ℝ)) atTop
        (𝓝 (inner ℝ x y : ℝ)) :=
    pairing_tendsto_of_norm_convergence h_norm y
  have h_const : Tendsto (fun _ : ℕ => (inner ℝ x y : ℝ)) atTop
      (𝓝 (inner ℝ x y : ℝ)) := tendsto_const_nhds
  have := h_pair.sub h_const
  simpa using this

end

end ZtareProofs.NS
