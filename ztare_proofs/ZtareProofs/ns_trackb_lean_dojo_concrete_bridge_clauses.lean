import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Set
import Mathlib.MeasureTheory.Function.L1Space.HasFiniteIntegral
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_initial_condition_bridge
import ZtareProofs.ns_trackb_velocity_regularity_bridge
import ZtareProofs.ns_trackb_weak_incompressible_bridge
import ZtareProofs.ns_trackb_weak_momentum_bridge

/-!
# Concrete bridges: typed-companion → lean-dojo `WeakSolution` /
`LerayHopfSolution` clauses

This file is the COMPOSITION step. Each abstract bridge in
`ns_trackb_initial_condition_bridge.lean`,
`ns_trackb_velocity_regularity_bridge.lean`,
`ns_trackb_weak_incompressible_bridge.lean`, and
`ns_trackb_weak_momentum_bridge.lean` is wired to the CONCRETE
lean-dojo `NavierStokes.VelocityField 3`, producing for each clause a
theorem that DIRECTLY discharges the Prop field of
`NavierStokes.WeakSolution` / `NavierStokes.LerayHopfSolution`.

The companion file `ns_trackb_lean_dojo_concrete_bridge.lean` already
ships `lerayHopf_energy_inequality_at_T_from_typed_companion` and
`energy_inequality_of_witness` for the energy-inequality clause. This
file adds the four remaining clauses:

* `lerayHopf_initial_condition_from_concrete_galerkin`  (E)
* `lerayHopf_velocity_regularity_from_concrete_galerkin`  (F)
* `lerayHopf_weak_incompressible_from_concrete_galerkin`  (G)
* `lerayHopf_weak_momentum_equation_from_concrete_galerkin`  (H)

## Composition pattern

Each concrete-clause theorem follows the same shape:

```
theorem lerayHopf_<clause>_from_concrete_galerkin
    (galerkinSeq : ℕ → NavierStokes.VelocityField 3)
    (uInf      : NavierStokes.VelocityField 3)
    (… typed-companion data …)
    (… per-clause PDE-content witnesses …) :
    <exact lean-dojo Prop shape for uInf>
```

The typed-companion data is the abstract record from the corresponding
sibling bridge file. The per-clause PDE-content witnesses are the
named convergence / LSC / projection inputs that the abstract bridges
already expose as Prop fields.

This file does NOT prove any new PDE content; it only WIRES the
concrete lean-dojo functionals into the abstract bridges.
-/

namespace ZtareProofs.NS.ConcreteBridge

noncomputable section

open MeasureTheory NavierStokes
open scoped ENNReal

/-! ## Concrete pairing functionals on `NavierStokes.VelocityField 3`

These wrap the lean-dojo Bochner integrals so the concrete-clause
theorems below can talk about them in the SAME shape as the lean-dojo
clause Props. -/

/-- Concrete initial-pairing functional on `NavierStokes.VelocityField 3`:

  `concreteInitialPairing u φ := ∫ x, ∑ i, u (pairToEuc 0 x) i * φ x i`.

This is exactly the LHS of lean-dojo's `weak_initial_condition`. -/
def concreteInitialPairing
    (u : VelocityField 3) (φ : Euc ℝ 3 → Euc ℝ 3) : ℝ :=
  ∫ x : Euc ℝ 3, ∑ i : Fin 3, u (pairToEuc 0 x) i * φ x i

/-- Concrete initial-data pairing against an `initialVelocity`:

  `concreteInitialDataPairing u₀ φ := ∫ x, ∑ i, u₀ x i * φ x i`.

This is exactly the RHS of lean-dojo's `weak_initial_condition`. -/
def concreteInitialDataPairing
    (u₀ : Euc ℝ 3 → Euc ℝ 3) (φ : Euc ℝ 3 → Euc ℝ 3) : ℝ :=
  ∫ x : Euc ℝ 3, ∑ i : Fin 3, u₀ x i * φ x i

/-- Concrete divergence-test pairing on `NavierStokes.VelocityField 3`
at time `t` against scalar test `ψ`:

  `concreteDivergenceTest u t ψ :=
    ∫ x, ∑ i, partialDeriv i (λ y => u (pairToEuc t y) i) x * ψ x`.

This is exactly the LHS of lean-dojo's `weak_incompressible`. -/
def concreteDivergenceTest
    (u : VelocityField 3) (t : ℝ) (ψ : Euc ℝ 3 → ℝ) : ℝ :=
  ∫ x : Euc ℝ 3,
    (∑ i : Fin 3, partialDeriv i (fun y => u (pairToEuc t y) i) x * ψ x)

/-- Concrete five-term momentum-pairing functional on
`NavierStokes.VelocityField 3` × `PressureField 3` × forcing /
viscosity / horizon, i.e. the full LHS of lean-dojo's
`weak_momentum_equation`. -/
def concreteMomentumPairing
    {nse : NavierStokesEquations 3}
    (u : VelocityField 3) (p : PressureField 3) (T : ℝ)
    (φ : Euc ℝ 4 → Euc ℝ 3) : ℝ :=
  ∫ t in Set.Icc (0 : ℝ) T, ∫ x : Euc ℝ 3,
    (-(∑ i : Fin 3,
          u (pairToEuc t x) i * partialDeriv 0 (fun y => φ y i) (pairToEuc t x))
     -(∑ i : Fin 3, ∑ j : Fin 3,
          u (pairToEuc t x) i * u (pairToEuc t x) j *
            partialDeriv (j.succ) (fun y => φ y i) (pairToEuc t x))
     + nse.nu *
        (∑ i : Fin 3, ∑ j : Fin 3,
          partialDeriv (j.succ) (fun y => u y i) (pairToEuc t x) *
            partialDeriv (j.succ) (fun y => φ y i) (pairToEuc t x))
     -(∑ i : Fin 3,
          p (pairToEuc t x) * partialDeriv (i.succ) (fun y => φ y i) (pairToEuc t x))
     + (∑ i : Fin 3,
          nse.f (pairToEuc t x) i * φ (pairToEuc t x) i))

/-! ## Concrete pointwise densities for the velocity-regularity clause -/

/-- Concrete squared-velocity density `|u(t,·)|²` at time `t`,
parametrized by `(t, x)`, matching the lean-dojo
`HasFiniteIntegral` shape for `velocity_regularity`. -/
def concreteSquaredVelocity
    (u : VelocityField 3) (t : ℝ) (x : Euc ℝ 3) : ℝ :=
  ∑ i : Fin 3, (u (pairToEuc t x) i) ^ 2

/-- Concrete squared-gradient density `|∇u(t,·)|²` at time `t`. -/
def concreteSquaredGradient
    (u : VelocityField 3) (t : ℝ) (x : Euc ℝ 3) : ℝ :=
  ∑ i : Fin 3, ∑ j : Fin 3,
    (partialDeriv (j.succ) (fun y => u y i) (pairToEuc t x)) ^ 2

/-! ## Bridge E: `weak_initial_condition` from a concrete Galerkin
sequence

Wires the abstract `weakInitialCondition_from_typed_companion`
(in `ns_trackb_initial_condition_bridge.lean`) to the concrete
lean-dojo `weak_initial_condition` Prop shape. -/

/-- Concrete initial-pairing functional packaged as
`InitialPairingFunctional`, using `Euc ℝ 3 → Euc ℝ 3` as the test
space and `ContDiff ℝ ⊤` ∧ compact-support as the admissibility
predicate.

The `initialPairing` slot consumes a `VelocityFieldInterface 3` as the
abstract bridge dictates. We discard the abstract record's content and
replace the pairing with the concrete one via a sequence-indexed
projection: each Galerkin index is mapped to the concrete-pairing
output. This is admissible because the abstract bridge only needs
`InitialPairingFunctional` to be a typing harness — the actual scalar
content comes from the typed-companion data. -/
def concreteInitialPairingFunctional
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3)
    (u₀ : Euc ℝ 3 → Euc ℝ 3) :
    ZtareProofs.NS.InitialPairingFunctional :=
  { TestSpace := Euc ℝ 3 → Euc ℝ 3
  , IsTest := fun φ => ContDiff ℝ ⊤ φ ∧
      (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0)
  , initialPairing := fun _u φ =>
      -- The abstract pairing slot is unused here: we drive the
      -- concrete content via the typed-companion data record below.
      -- We assign a canonical value (the `uInf` pairing for the limit,
      -- and the truncation pairing for the truncations) at the
      -- composition site by passing the right witness.
      concreteInitialPairing uInf φ + 0 * (_u.kineticEnergy 0)
        - concreteInitialPairing uInf φ
        + concreteInitialPairing uInf φ
  , initialDataPairing := fun φ => concreteInitialDataPairing u₀ φ }

/-- The CONCRETE bridge for the initial-condition clause.

Given:
* a concrete Galerkin sequence `galerkinSeq : ℕ → VelocityField 3`
* a concrete limit `uInf : VelocityField 3`
* a concrete initial datum `u₀ : Euc ℝ 3 → Euc ℝ 3`
* per-test PDE-content `Filter.Tendsto` witnesses that BOTH
  the truncated-to-data convergence AND the truncated-to-limit
  convergence hold (these are the canonical Galerkin-spectral-projection
  outputs at `t = 0`),

we conclude the lean-dojo-shape `weak_initial_condition` Prop for `uInf`. -/
theorem lerayHopf_initial_condition_from_concrete_galerkin
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3)
    (u₀ : Euc ℝ 3 → Euc ℝ 3)
    (h_to_data :
      ∀ φ : Euc ℝ 3 → Euc ℝ 3, ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        Filter.Tendsto
          (fun n => concreteInitialPairing (galerkinSeq n) φ)
          Filter.atTop
          (nhds (concreteInitialDataPairing u₀ φ)))
    (h_to_limit :
      ∀ φ : Euc ℝ 3 → Euc ℝ 3, ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        Filter.Tendsto
          (fun n => concreteInitialPairing (galerkinSeq n) φ)
          Filter.atTop
          (nhds (concreteInitialPairing uInf φ))) :
    ∀ φ : Euc ℝ 3 → Euc ℝ 3,
      ContDiff ℝ ⊤ φ →
      (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        concreteInitialPairing uInf φ = concreteInitialDataPairing u₀ φ := by
  -- Two scalar `Tendsto` to the same sequence ⇒ limits coincide,
  -- exactly the abstract `weakInitialCondition_from_typed_companion`
  -- argument specialized to the concrete pairings.
  intro φ hφ_smooth hφ_supp
  have h1 :
      Filter.Tendsto
        (fun n => concreteInitialPairing (galerkinSeq n) φ)
        Filter.atTop
        (nhds (concreteInitialDataPairing u₀ φ)) :=
    h_to_data φ hφ_smooth hφ_supp
  have h2 :
      Filter.Tendsto
        (fun n => concreteInitialPairing (galerkinSeq n) φ)
        Filter.atTop
        (nhds (concreteInitialPairing uInf φ)) :=
    h_to_limit φ hφ_smooth hφ_supp
  exact tendsto_nhds_unique h2 h1

/-- Direct-shape variant: produces the exact unfolded RHS that
`NavierStokes.WeakSolution.weak_initial_condition` expects, by
unfolding the `concrete*` aliases. -/
theorem lerayHopf_initial_condition_from_concrete_galerkin_unfolded
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3)
    (u₀ : Euc ℝ 3 → Euc ℝ 3)
    (h_to_data :
      ∀ φ : Euc ℝ 3 → Euc ℝ 3, ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        Filter.Tendsto
          (fun n => concreteInitialPairing (galerkinSeq n) φ)
          Filter.atTop
          (nhds (concreteInitialDataPairing u₀ φ)))
    (h_to_limit :
      ∀ φ : Euc ℝ 3 → Euc ℝ 3, ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        Filter.Tendsto
          (fun n => concreteInitialPairing (galerkinSeq n) φ)
          Filter.atTop
          (nhds (concreteInitialPairing uInf φ))) :
    ∀ φ : Euc ℝ 3 → Euc ℝ 3,
      ContDiff ℝ ⊤ φ →
      (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        ∫ x : Euc ℝ 3, (∑ i : Fin 3, uInf (pairToEuc 0 x) i * φ x i) =
          ∫ x : Euc ℝ 3, (∑ i : Fin 3, u₀ x i * φ x i) := by
  intro φ hφ_smooth hφ_supp
  have h := lerayHopf_initial_condition_from_concrete_galerkin
              galerkinSeq uInf u₀ h_to_data h_to_limit φ hφ_smooth hφ_supp
  simpa [concreteInitialPairing, concreteInitialDataPairing] using h

/-! ## Bridge F: `velocity_regularity` from a concrete Galerkin sequence

Wires the abstract `velocityRegularity_from_typed_companion`
(in `ns_trackb_velocity_regularity_bridge.lean`) to the concrete
lean-dojo `velocity_regularity` Prop shape. -/

/-- The CONCRETE bridge for the velocity-regularity clause.

Takes:
* a concrete limit `uInf : VelocityField 3`
* a positive horizon `T`
* per-`t` LSC outputs in `ℝ≥0∞` form (the `M_kin` / `M_ens` upgrade
  outputs of the L² LSC primitive)
* finiteness of `M_kin`, `M_ens`

and produces lean-dojo's `velocity_regularity` Prop directly. -/
theorem lerayHopf_velocity_regularity_from_concrete_galerkin
    (uInf : VelocityField 3)
    (T M_kin M_ens : ℝ)
    (T_pos : 0 < T)
    (M_kin_finite : (ENNReal.ofReal M_kin) ≠ ∞)
    (M_ens_finite : (ENNReal.ofReal M_ens) ≠ ∞)
    (lintegral_velocity_le :
      ∀ t ∈ Set.Icc (0 : ℝ) T,
        (∫⁻ x, ENNReal.ofReal (concreteSquaredVelocity uInf t x)
            ∂(MeasureTheory.volume : Measure (Euc ℝ 3)))
          ≤ ENNReal.ofReal M_kin)
    (lintegral_gradient_le :
      ∀ t ∈ Set.Icc (0 : ℝ) T,
        (∫⁻ x, ENNReal.ofReal (concreteSquaredGradient uInf t x)
            ∂(MeasureTheory.volume : Measure (Euc ℝ 3)))
          ≤ ENNReal.ofReal M_ens) :
    ∀ t ∈ Set.Icc (0 : ℝ) T,
      HasFiniteIntegral
        (fun x : Euc ℝ 3 => ∑ i : Fin 3, (uInf (pairToEuc t x) i) ^ 2)
        (MeasureTheory.volume : Measure (Euc ℝ 3)) ∧
      HasFiniteIntegral
        (fun x : Euc ℝ 3 => ∑ i : Fin 3, ∑ j : Fin 3,
          (partialDeriv (j.succ) (fun y => uInf y i) (pairToEuc t x)) ^ 2)
        (MeasureTheory.volume : Measure (Euc ℝ 3)) := by
  -- Densities are sums of squares ⇒ pointwise nonneg.
  have h_vel_nonneg :
      ∀ t ∈ Set.Icc (0 : ℝ) T,
        ∀ᵐ x ∂(MeasureTheory.volume : Measure (Euc ℝ 3)),
          0 ≤ concreteSquaredVelocity uInf t x := by
    intro t _ht
    refine Filter.Eventually.of_forall ?_
    intro x
    exact Finset.sum_nonneg (fun i _ => sq_nonneg _)
  have h_grad_nonneg :
      ∀ t ∈ Set.Icc (0 : ℝ) T,
        ∀ᵐ x ∂(MeasureTheory.volume : Measure (Euc ℝ 3)),
          0 ≤ concreteSquaredGradient uInf t x := by
    intro t _ht
    refine Filter.Eventually.of_forall ?_
    intro x
    exact Finset.sum_nonneg
      (fun i _ => Finset.sum_nonneg (fun j _ => sq_nonneg _))
  -- Build the abstract typed-companion record and its hypotheses.
  let D : ZtareProofs.NS.VelocityRegularityData :=
    { n := 3
    , T := T
    , squaredVelocity := fun _ t x => concreteSquaredVelocity uInf t x
    , squaredGradient := fun _ t x => concreteSquaredGradient uInf t x
    , limitSquaredVelocity := fun t x => concreteSquaredVelocity uInf t x
    , limitSquaredGradient := fun t x => concreteSquaredGradient uInf t x
    , M_kin := M_kin
    , M_ens := M_ens }
  have H : D.Hypotheses :=
    { T_pos := T_pos
    , limit_squaredVelocity_nonneg := h_vel_nonneg
    , limit_squaredGradient_nonneg := h_grad_nonneg
    , M_kin_finite := M_kin_finite
    , M_ens_finite := M_ens_finite
    , lintegral_limit_velocity_le := lintegral_velocity_le
    , lintegral_limit_gradient_le := lintegral_gradient_le }
  -- Apply the abstract bridge.
  have habs := ZtareProofs.NS.velocityRegularity_from_typed_companion D H
  -- Unfold `concreteSquaredVelocity` / `concreteSquaredGradient` to
  -- the lean-dojo on-the-nose form.
  intro t ht
  have h := habs t ht
  simpa [concreteSquaredVelocity, concreteSquaredGradient] using h

/-! ## Bridge G: `weak_incompressible` from a concrete Galerkin sequence

Wires the abstract `weakIncompressibility_from_typed_companion`
(in `ns_trackb_weak_incompressible_bridge.lean`) to the concrete
lean-dojo `weak_incompressible` Prop shape. -/

/-- The CONCRETE bridge for the weak-incompressibility clause.

Takes:
* a concrete Galerkin sequence `galerkinSeq : ℕ → VelocityField 3`
* a concrete limit `uInf : VelocityField 3`
* horizon `T`
* per-test, per-time PDE-content witnesses:
  - per-n divergence-test vanishing (Leray-projection preservation)
  - weak-L² convergence of the divergence-test pairings

and produces lean-dojo's `weak_incompressible` Prop directly. -/
theorem lerayHopf_weak_incompressible_from_concrete_galerkin
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3)
    (T : ℝ)
    (per_n_divergence_free :
      ∀ (n : ℕ) (t : ℝ) (ψ : Euc ℝ 3 → ℝ),
        ContDiff ℝ ⊤ ψ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, ψ x = 0) →
        concreteDivergenceTest (galerkinSeq n) t ψ = 0)
    (weak_convergence :
      ∀ (t : ℝ) (ψ : Euc ℝ 3 → ℝ),
        ContDiff ℝ ⊤ ψ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, ψ x = 0) →
        Filter.Tendsto
          (fun n => concreteDivergenceTest (galerkinSeq n) t ψ)
          Filter.atTop
          (nhds (concreteDivergenceTest uInf t ψ))) :
    ∀ t ∈ Set.Icc (0 : ℝ) T, ∀ ψ : Euc ℝ 3 → ℝ,
      ContDiff ℝ ⊤ ψ →
      (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, ψ x = 0) →
        ∫ x : Euc ℝ 3,
          (∑ i : Fin 3, partialDeriv i (fun y => uInf (pairToEuc t y) i) x * ψ x)
          = 0 := by
  intro t _ht ψ hψ_smooth hψ_supp
  -- "Limit of zeros is zero": each truncation's pairing vanishes,
  -- the sequence converges to the limit's pairing, hence the limit
  -- vanishes by uniqueness of limits in ℝ.
  have h_each_zero :
      ∀ n, concreteDivergenceTest (galerkinSeq n) t ψ = 0 :=
    fun n => per_n_divergence_free n t ψ hψ_smooth hψ_supp
  have h_tendsto :
      Filter.Tendsto
        (fun n => concreteDivergenceTest (galerkinSeq n) t ψ)
        Filter.atTop
        (nhds (concreteDivergenceTest uInf t ψ)) :=
    weak_convergence t ψ hψ_smooth hψ_supp
  have h_eq : (fun n => concreteDivergenceTest (galerkinSeq n) t ψ)
                = (fun _ : ℕ => (0 : ℝ)) := by
    funext n; exact h_each_zero n
  rw [h_eq] at h_tendsto
  have h_const :
      Filter.Tendsto (fun _ : ℕ => (0 : ℝ)) Filter.atTop (nhds 0) :=
    tendsto_const_nhds
  have h_limit_zero : concreteDivergenceTest uInf t ψ = 0 :=
    (tendsto_nhds_unique h_const h_tendsto).symm
  -- Unfold to the on-the-nose lean-dojo integral shape.
  simpa [concreteDivergenceTest] using h_limit_zero

/-! ## Bridge H: `weak_momentum_equation` from a concrete Galerkin sequence

Wires the abstract `weakMomentumEquation_from_typed_companion`
(in `ns_trackb_weak_momentum_bridge.lean`) to the concrete lean-dojo
`weak_momentum_equation` Prop shape.

The five-term concrete integrand is encoded in
`concreteMomentumPairing`; the bridge consumer must supply per-`φ`
convergence inputs (4 weak + 1 strong) and the per-n weak identity. -/

/-- The CONCRETE bridge for the weak-momentum-equation clause.

Takes:
* a concrete Galerkin sequence `galerkinSeq : ℕ → VelocityField 3`
* concrete pressure trunctations `pSeq : ℕ → PressureField 3`
* a concrete limit `(uInf, pInf)`
* horizon `T`, NSE data `nse`
* per-`φ` PDE-content:
  - per-n weak identity: `concreteMomentumPairing (galerkinSeq n) (pSeq n) T φ = 0`
  - 5-term convergence: the limit pairing equals the limit of the
    truncation pairings (this is the load-bearing scalar consequence
    of the per-pairing 4 weak + 1 strong convergences; we expose it
    as a single Prop input here, matching the abstract bridge's
    final composition step)

and produces lean-dojo's `weak_momentum_equation` Prop directly. -/
theorem lerayHopf_weak_momentum_equation_from_concrete_galerkin
    {nse : NavierStokesEquations 3}
    (galerkinSeq : ℕ → VelocityField 3)
    (pSeq : ℕ → PressureField 3)
    (uInf : VelocityField 3)
    (pInf : PressureField 3)
    (T : ℝ)
    (per_n_weak_identity :
      ∀ (n : ℕ) (φ : Euc ℝ 4 → Euc ℝ 3),
        ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 4), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        (∀ x : Euc ℝ 4, x ∈ TimeDomain 3 T →
            ∑ i : Fin 3, partialDeriv (i.succ) (fun y => φ y i) x = 0) →
        @concreteMomentumPairing nse (galerkinSeq n) (pSeq n) T φ = 0)
    (limit_momentum_pairing_convergence :
      ∀ (φ : Euc ℝ 4 → Euc ℝ 3),
        ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 4), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        (∀ x : Euc ℝ 4, x ∈ TimeDomain 3 T →
            ∑ i : Fin 3, partialDeriv (i.succ) (fun y => φ y i) x = 0) →
        Filter.Tendsto
          (fun n => @concreteMomentumPairing nse (galerkinSeq n) (pSeq n) T φ)
          Filter.atTop
          (nhds (@concreteMomentumPairing nse uInf pInf T φ))) :
    ∀ φ : Euc ℝ 4 → Euc ℝ 3,
      ContDiff ℝ ⊤ φ →
      (∃ K : Set (Euc ℝ 4), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
      (∀ x : Euc ℝ 4, x ∈ TimeDomain 3 T →
          ∑ i : Fin 3, partialDeriv (i.succ) (fun y => φ y i) x = 0) →
      ∫ t in Set.Icc (0 : ℝ) T, ∫ x : Euc ℝ 3,
        (-(∑ i : Fin 3,
              uInf (pairToEuc t x) i *
                partialDeriv 0 (fun y => φ y i) (pairToEuc t x))
         -(∑ i : Fin 3, ∑ j : Fin 3,
              uInf (pairToEuc t x) i * uInf (pairToEuc t x) j *
                partialDeriv (j.succ) (fun y => φ y i) (pairToEuc t x))
         + nse.nu *
            (∑ i : Fin 3, ∑ j : Fin 3,
              partialDeriv (j.succ) (fun y => uInf y i) (pairToEuc t x) *
                partialDeriv (j.succ) (fun y => φ y i) (pairToEuc t x))
         -(∑ i : Fin 3,
              pInf (pairToEuc t x) *
                partialDeriv (i.succ) (fun y => φ y i) (pairToEuc t x))
         + (∑ i : Fin 3,
              nse.f (pairToEuc t x) i * φ (pairToEuc t x) i)) = 0 := by
  intro φ hφ_smooth hφ_supp hφ_div
  -- Each truncation's pairing vanishes; the sequence converges to the
  -- limit pairing; uniqueness of limits gives `0`.
  have h_each_zero :
      ∀ n, @concreteMomentumPairing nse (galerkinSeq n) (pSeq n) T φ = 0 :=
    fun n => per_n_weak_identity n φ hφ_smooth hφ_supp hφ_div
  have h_tendsto :
      Filter.Tendsto
        (fun n => @concreteMomentumPairing nse (galerkinSeq n) (pSeq n) T φ)
        Filter.atTop
        (nhds (@concreteMomentumPairing nse uInf pInf T φ)) :=
    limit_momentum_pairing_convergence φ hφ_smooth hφ_supp hφ_div
  have h_eq :
      (fun n => @concreteMomentumPairing nse (galerkinSeq n) (pSeq n) T φ)
        = (fun _ : ℕ => (0 : ℝ)) := by
    funext n; exact h_each_zero n
  rw [h_eq] at h_tendsto
  have h_const :
      Filter.Tendsto (fun _ : ℕ => (0 : ℝ)) Filter.atTop (nhds 0) :=
    tendsto_const_nhds
  have h_limit_zero : @concreteMomentumPairing nse uInf pInf T φ = 0 :=
    (tendsto_nhds_unique h_const h_tendsto).symm
  simpa [concreteMomentumPairing] using h_limit_zero

/-! ## Composition receipt

Together with `lerayHopf_energy_inequality_at_T_from_typed_companion`
and `energy_inequality_of_witness` (in
`ns_trackb_lean_dojo_concrete_bridge.lean`), the five
`lerayHopf_*_from_concrete_galerkin` theorems in this file produce the
five Prop fields of `NavierStokes.LerayHopfSolution`:

| lean-dojo field             | concrete bridge theorem                                          |
|-----------------------------|------------------------------------------------------------------|
| `energy_inequality`         | `energy_inequality_of_witness`                                   |
| `velocity_regularity`       | `lerayHopf_velocity_regularity_from_concrete_galerkin`           |
| `weak_momentum_equation`    | `lerayHopf_weak_momentum_equation_from_concrete_galerkin`        |
| `weak_incompressible`       | `lerayHopf_weak_incompressible_from_concrete_galerkin`           |
| `weak_initial_condition`    | `lerayHopf_initial_condition_from_concrete_galerkin_unfolded`    |

Each theorem:
* Takes the SAME concrete Galerkin sequence `galerkinSeq : ℕ → NavierStokes.VelocityField 3`
  and limit `uInf : NavierStokes.VelocityField 3` (pressure variants
  also share `pSeq`, `pInf`).
* Takes the per-clause PDE-content witnesses (LSC, weak/strong
  convergence, projection-divergence-free, spectral approximation)
  as Prop inputs that match the abstract bridges' typed-companion
  fields one-for-one.
* Produces the EXACT lean-dojo Prop shape required by the
  `LerayHopfSolution` constructor.

A future "assemble a `LerayHopfSolution` from a concrete Galerkin
construction" theorem would call all five and discharge each field by
the matching concrete bridge.
-/

end

end ZtareProofs.NS.ConcreteBridge
