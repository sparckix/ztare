import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Set
import Mathlib.MeasureTheory.Function.L1Space.HasFiniteIntegral
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.lean_dojo_ns_torus.MillenniumRDomain
import ZtareProofs.lean_dojo_ns_torus.MillenniumBoundedDomain
import ZtareProofs.ns_trackb_lean_dojo_concrete_bridge
import ZtareProofs.ns_trackb_lean_dojo_concrete_bridge_clauses

/-!
# Concrete bridge: typed-companion → lean-dojo periodic NS (`𝕋³`, Fefferman B + D)

This file is the PERIODIC-DOMAIN counterpart of
`ns_trackb_lean_dojo_concrete_bridge.lean` /
`ns_trackb_lean_dojo_concrete_bridge_clauses.lean`. It wires the
abstract typed-companion bridges to the periodic-domain Clay statement
in `ZtareProofs.lean_dojo_ns_torus.MillenniumBoundedDomain` (Fefferman
parts B and D from the Clay PDF, conditions (8)–(11)).

## Architecture-transfer claim

The existing five abstract bridges
(`energy_inequality`, `weak_initial_condition`, `velocity_regularity`,
`weak_incompressible`, `weak_momentum_equation`) work UNCHANGED on the
periodic domain. The reason:

* `NavierStokes.WeakSolution` and `NavierStokes.LerayHopfSolution` in
  `lean_dojo_ns/Navierstokes.lean` are DOMAIN-AGNOSTIC at the type
  level: they fix `VelocityField n = Euc ℝ (n+1) → Euc ℝ n` and
  `PressureField n = Euc ℝ (n+1) → ℝ` and define each clause as a
  Bochner integral over `Euc ℝ n` against compactly-supported smooth
  test functions.
* `MillenniumNS_BoundedDomain.FeffermanB` (resp. `FeffermanD`) reuses
  exactly the same `nseR3` / `GlobalSmoothSolution` machinery as the
  R³ statement (`MillenniumNSRDomain.FeffermanA` / `FeffermanC`); the
  ONLY periodic-specific structural addition is the conclusion
  `FeffermanCond10` (spatial periodicity of `sol.u` and `sol.p`) and
  the hypothesis `FeffermanCond8_initial` / `FeffermanCond8_force` on
  the initial data and force.
* `Torus3` is implemented as `Euc ℝ 3` (the lightweight torus model in
  `lean_dojo_ns_torus/Torus.lean`), so functions on the torus are
  literally `Euc ℝ 3 → ·` with periodicity carried as a side Prop.

In particular, the test-function space stays `ContDiff ℝ ⊤ ∧
compactly supported` in the lean-dojo formulation — there is NO
switch to "torus-periodic test functions" required, because the
underlying domain in lean-dojo's `WeakSolution` definition is still
`Euc ℝ n` (i.e. `ℝ³`), and periodicity is a side condition imposed by
`FeffermanCond10` on the SOLUTION.

This means the five abstract bridges import-and-reuse cleanly. The
ONLY new content this file ships is:

* `lerayHopf_periodicity_from_concrete_galerkin` — discharges
  `FeffermanCond10` for the limit `(uInf, pInf)` from per-`n`
  periodicity of the Galerkin sequence + pointwise convergence,
  exactly the analogue of "limit of zeros is zero" used for the
  weak-incompressibility clause.
* Convenience re-exports `lerayHopf_*_torus` of the five concrete
  bridges, namespaced under `ZtareProofs.NS.ConcreteBridge.Torus`,
  with documentation pointing at the Fefferman-B clause they
  discharge.

## What this file does NOT do

* It does NOT prove `FeffermanB` (existence of a smooth periodic
  solution) — that is the open Clay problem.
* It does NOT modify `NavierStokes.LerayHopfSolution` or any
  vendored definition.
* It does NOT introduce a new test-function space; the lean-dojo
  shape is the same on both domains.
-/

namespace ZtareProofs.NS.ConcreteBridge.Torus

noncomputable section

open MeasureTheory NavierStokes
open MillenniumNS_BoundedDomain
open scoped ENNReal

/-! ## Re-exports of the five clause bridges (unchanged on `𝕋³`)

These are the same theorems as in the R³ bridge; we re-state their
types here for documentation under the torus namespace. The bodies
delegate verbatim to the R³ bridges, demonstrating that the
typed-companion architecture is substrate-agnostic with respect to
domain topology (whole-space vs periodic). -/

/-- Energy-inequality clause for a periodic-domain Leray–Hopf limit.

Identical to the R³ bridge: lean-dojo's `LerayHopfSolution` carries
the energy inequality with the SAME `kineticEnergy` /
`enstrophy` Bochner integrands on `Euc ℝ 3`, and the Galerkin LSC +
per-`n` estimate witnesses are domain-agnostic. -/
theorem lerayHopf_energy_inequality_at_T_torus
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    [_hNeBot : (Filter.comap (id : ℕ → ℕ) Filter.atTop).NeBot]
    (boundData :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData M (id : ℕ → ℕ)
        (fun a => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax a)
        (fun a => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.crossDefect a)
        (fun a => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.coherence a))
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3)
    (nu T : ℝ)
    (nu_nonneg : 0 ≤ nu)
    (interp :
      ZtareProofs.NS.ConcreteBridge.ConcreteGalerkinInterpretation
        S galerkinSeq nu T)
    (lscKE :
      ZtareProofs.NS.ConcreteBridge.ConcreteKineticEnergyLSC
        galerkinSeq uInf T)
    (lscDiss :
      ZtareProofs.NS.ConcreteBridge.ConcreteCumulativeEnstrophyLSC
        galerkinSeq uInf T)
    (per_n_estimate :
      ∀ n, kineticEnergy (galerkinSeq n) T
            + 2 * nu *
              ZtareProofs.NS.ConcreteBridge.cumulativeEnstrophy
                (galerkinSeq n) T
          ≤ kineticEnergy (galerkinSeq n) 0)
    (combined_liminf_le :
      Filter.liminf
        (fun n => kineticEnergy (galerkinSeq n) T
          + 2 * nu *
              ZtareProofs.NS.ConcreteBridge.cumulativeEnstrophy
                (galerkinSeq n) T)
        Filter.atTop
      ≤ kineticEnergy uInf 0)
    (sum_le_combined_liminf :
      kineticEnergy uInf T
        + 2 * nu *
            Filter.liminf
              (fun n =>
                ZtareProofs.NS.ConcreteBridge.cumulativeEnstrophy
                  (galerkinSeq n) T)
              Filter.atTop
        ≤ Filter.liminf
            (fun n => kineticEnergy (galerkinSeq n) T
              + 2 * nu *
                  ZtareProofs.NS.ConcreteBridge.cumulativeEnstrophy
                    (galerkinSeq n) T)
            Filter.atTop) :
    kineticEnergy uInf T
        + 2 * nu *
            ZtareProofs.NS.ConcreteBridge.cumulativeEnstrophy uInf T
      ≤ kineticEnergy uInf 0 :=
  ZtareProofs.NS.ConcreteBridge.lerayHopf_energy_inequality_at_T_from_typed_companion
    boundData galerkinSeq uInf nu T nu_nonneg
    interp lscKE lscDiss per_n_estimate combined_liminf_le
    sum_le_combined_liminf

/-- Initial-condition clause for a periodic-domain limit. Identical to
the R³ bridge: lean-dojo's `weak_initial_condition` integrates against
compactly-supported smooth test functions on `Euc ℝ 3`. -/
theorem lerayHopf_initial_condition_torus
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3)
    (u₀ : Euc ℝ 3 → Euc ℝ 3)
    (h_to_data :
      ∀ φ : Euc ℝ 3 → Euc ℝ 3, ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        Filter.Tendsto
          (fun n =>
            ZtareProofs.NS.ConcreteBridge.concreteInitialPairing
              (galerkinSeq n) φ)
          Filter.atTop
          (nhds
            (ZtareProofs.NS.ConcreteBridge.concreteInitialDataPairing
              u₀ φ)))
    (h_to_limit :
      ∀ φ : Euc ℝ 3 → Euc ℝ 3, ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        Filter.Tendsto
          (fun n =>
            ZtareProofs.NS.ConcreteBridge.concreteInitialPairing
              (galerkinSeq n) φ)
          Filter.atTop
          (nhds
            (ZtareProofs.NS.ConcreteBridge.concreteInitialPairing
              uInf φ))) :
    ∀ φ : Euc ℝ 3 → Euc ℝ 3,
      ContDiff ℝ ⊤ φ →
      (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        ∫ x : Euc ℝ 3, (∑ i : Fin 3, uInf (pairToEuc 0 x) i * φ x i) =
          ∫ x : Euc ℝ 3, (∑ i : Fin 3, u₀ x i * φ x i) :=
  ZtareProofs.NS.ConcreteBridge.lerayHopf_initial_condition_from_concrete_galerkin_unfolded
    galerkinSeq uInf u₀ h_to_data h_to_limit

/-- Velocity-regularity clause for a periodic-domain limit. The L²/H¹
shape is unchanged because `velocity_regularity` is stated as
`HasFiniteIntegral` against Lebesgue measure on `Euc ℝ 3` in
lean-dojo. -/
theorem lerayHopf_velocity_regularity_torus
    (uInf : VelocityField 3)
    (T M_kin M_ens : ℝ)
    (T_pos : 0 < T)
    (M_kin_finite : (ENNReal.ofReal M_kin) ≠ ∞)
    (M_ens_finite : (ENNReal.ofReal M_ens) ≠ ∞)
    (lintegral_velocity_le :
      ∀ t ∈ Set.Icc (0 : ℝ) T,
        (∫⁻ x,
            ENNReal.ofReal
              (ZtareProofs.NS.ConcreteBridge.concreteSquaredVelocity
                uInf t x)
            ∂(MeasureTheory.volume : Measure (Euc ℝ 3)))
          ≤ ENNReal.ofReal M_kin)
    (lintegral_gradient_le :
      ∀ t ∈ Set.Icc (0 : ℝ) T,
        (∫⁻ x,
            ENNReal.ofReal
              (ZtareProofs.NS.ConcreteBridge.concreteSquaredGradient
                uInf t x)
            ∂(MeasureTheory.volume : Measure (Euc ℝ 3)))
          ≤ ENNReal.ofReal M_ens) :
    ∀ t ∈ Set.Icc (0 : ℝ) T,
      HasFiniteIntegral
        (fun x : Euc ℝ 3 => ∑ i : Fin 3, (uInf (pairToEuc t x) i) ^ 2)
        (MeasureTheory.volume : Measure (Euc ℝ 3)) ∧
      HasFiniteIntegral
        (fun x : Euc ℝ 3 => ∑ i : Fin 3, ∑ j : Fin 3,
          (partialDeriv (j.succ) (fun y => uInf y i) (pairToEuc t x))
            ^ 2)
        (MeasureTheory.volume : Measure (Euc ℝ 3)) :=
  ZtareProofs.NS.ConcreteBridge.lerayHopf_velocity_regularity_from_concrete_galerkin
    uInf T M_kin M_ens T_pos M_kin_finite M_ens_finite
    lintegral_velocity_le lintegral_gradient_le

/-- Weak-incompressibility clause for a periodic-domain limit.
Identical to the R³ bridge. -/
theorem lerayHopf_weak_incompressible_torus
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3)
    (T : ℝ)
    (per_n_divergence_free :
      ∀ (n : ℕ) (t : ℝ) (ψ : Euc ℝ 3 → ℝ),
        ContDiff ℝ ⊤ ψ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, ψ x = 0) →
        ZtareProofs.NS.ConcreteBridge.concreteDivergenceTest
          (galerkinSeq n) t ψ = 0)
    (weak_convergence :
      ∀ (t : ℝ) (ψ : Euc ℝ 3 → ℝ),
        ContDiff ℝ ⊤ ψ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, ψ x = 0) →
        Filter.Tendsto
          (fun n =>
            ZtareProofs.NS.ConcreteBridge.concreteDivergenceTest
              (galerkinSeq n) t ψ)
          Filter.atTop
          (nhds
            (ZtareProofs.NS.ConcreteBridge.concreteDivergenceTest
              uInf t ψ))) :
    ∀ t ∈ Set.Icc (0 : ℝ) T, ∀ ψ : Euc ℝ 3 → ℝ,
      ContDiff ℝ ⊤ ψ →
      (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, ψ x = 0) →
        ∫ x : Euc ℝ 3,
          (∑ i : Fin 3,
            partialDeriv i (fun y => uInf (pairToEuc t y) i) x * ψ x)
          = 0 :=
  ZtareProofs.NS.ConcreteBridge.lerayHopf_weak_incompressible_from_concrete_galerkin
    galerkinSeq uInf T per_n_divergence_free weak_convergence

/-- Weak-momentum-equation clause for a periodic-domain limit.
Identical to the R³ bridge. -/
theorem lerayHopf_weak_momentum_equation_torus
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
            ∑ i : Fin 3,
              partialDeriv (i.succ) (fun y => φ y i) x = 0) →
        @ZtareProofs.NS.ConcreteBridge.concreteMomentumPairing nse
          (galerkinSeq n) (pSeq n) T φ = 0)
    (limit_momentum_pairing_convergence :
      ∀ (φ : Euc ℝ 4 → Euc ℝ 3),
        ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 4), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        (∀ x : Euc ℝ 4, x ∈ TimeDomain 3 T →
            ∑ i : Fin 3,
              partialDeriv (i.succ) (fun y => φ y i) x = 0) →
        Filter.Tendsto
          (fun n =>
            @ZtareProofs.NS.ConcreteBridge.concreteMomentumPairing nse
              (galerkinSeq n) (pSeq n) T φ)
          Filter.atTop
          (nhds
            (@ZtareProofs.NS.ConcreteBridge.concreteMomentumPairing
              nse uInf pInf T φ))) :
    ∀ φ : Euc ℝ 4 → Euc ℝ 3,
      ContDiff ℝ ⊤ φ →
      (∃ K : Set (Euc ℝ 4), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
      (∀ x : Euc ℝ 4, x ∈ TimeDomain 3 T →
          ∑ i : Fin 3,
            partialDeriv (i.succ) (fun y => φ y i) x = 0) →
      ∫ t in Set.Icc (0 : ℝ) T, ∫ x : Euc ℝ 3,
        (-(∑ i : Fin 3,
              uInf (pairToEuc t x) i *
                partialDeriv 0 (fun y => φ y i) (pairToEuc t x))
         -(∑ i : Fin 3, ∑ j : Fin 3,
              uInf (pairToEuc t x) i * uInf (pairToEuc t x) j *
                partialDeriv (j.succ) (fun y => φ y i)
                  (pairToEuc t x))
         + nse.nu *
            (∑ i : Fin 3, ∑ j : Fin 3,
              partialDeriv (j.succ) (fun y => uInf y i)
                  (pairToEuc t x) *
                partialDeriv (j.succ) (fun y => φ y i)
                  (pairToEuc t x))
         -(∑ i : Fin 3,
              pInf (pairToEuc t x) *
                partialDeriv (i.succ) (fun y => φ y i)
                  (pairToEuc t x))
         + (∑ i : Fin 3,
              nse.f (pairToEuc t x) i * φ (pairToEuc t x) i)) = 0 :=
  ZtareProofs.NS.ConcreteBridge.lerayHopf_weak_momentum_equation_from_concrete_galerkin
    galerkinSeq pSeq uInf pInf T
    per_n_weak_identity limit_momentum_pairing_convergence

/-! ## NEW periodic-domain clause: `FeffermanCond10`

This is the clause that has no analogue in the R³ statements — the
periodicity of the solution `(u, p)` in the spatial variables. We
discharge it by the same "limit of identical equalities is the same
equality" pattern used for `weak_incompressible`. -/

/-- Pointwise periodicity preservation for a velocity field.

Given a Galerkin sequence whose every member is spatially periodic,
plus pointwise convergence at every shifted location, the limit
field is spatially periodic. -/
theorem isPeriodic_velocity_from_pointwise_limit
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3)
    (t : ℝ)
    (per_n_periodic :
      ∀ n,
        IsPeriodic (fun x : Euc ℝ 3 => (galerkinSeq n) (pairToEuc t x)))
    (pointwise_limit :
      ∀ y : Euc ℝ 3,
        Filter.Tendsto
          (fun n => (galerkinSeq n) (pairToEuc t y))
          Filter.atTop
          (nhds (uInf (pairToEuc t y)))) :
    IsPeriodic (fun x : Euc ℝ 3 => uInf (pairToEuc t x)) := by
  intro x i k
  -- Goal: `uInf (pairToEuc t (x + k • standardBasis i))
  --        = uInf (pairToEuc t x)`.
  -- For each n: `(galerkinSeq n) (pairToEuc t (x + k • e_i))
  --            = (galerkinSeq n) (pairToEuc t x)` by `per_n_periodic`.
  have h_eq :
      (fun n => (galerkinSeq n)
                  (pairToEuc t
                    (x + k • (standardBasis (n := 3) i))))
        = fun n => (galerkinSeq n) (pairToEuc t x) := by
    funext n
    exact per_n_periodic n x i k
  -- Pointwise limit at the shifted point converges to
  -- `uInf (pairToEuc t (x + k • e_i))`; rewriting via h_eq gives
  -- convergence of the constant sequence to the unshifted limit.
  have h_shift :
      Filter.Tendsto
        (fun n => (galerkinSeq n)
                    (pairToEuc t
                      (x + k • (standardBasis (n := 3) i))))
        Filter.atTop
        (nhds
          (uInf
            (pairToEuc t (x + k • (standardBasis (n := 3) i))))) :=
    pointwise_limit (x + k • (standardBasis (n := 3) i))
  have h_unshift :
      Filter.Tendsto
        (fun n => (galerkinSeq n) (pairToEuc t x))
        Filter.atTop
        (nhds (uInf (pairToEuc t x))) :=
    pointwise_limit x
  rw [h_eq] at h_shift
  exact tendsto_nhds_unique h_shift h_unshift

/-- Pointwise periodicity preservation for a pressure field. -/
theorem isPeriodic_pressure_from_pointwise_limit
    (pSeq : ℕ → PressureField 3)
    (pInf : PressureField 3)
    (t : ℝ)
    (per_n_periodic :
      ∀ n,
        IsPeriodic (fun x : Euc ℝ 3 => (pSeq n) (pairToEuc t x)))
    (pointwise_limit :
      ∀ y : Euc ℝ 3,
        Filter.Tendsto
          (fun n => (pSeq n) (pairToEuc t y))
          Filter.atTop
          (nhds (pInf (pairToEuc t y)))) :
    IsPeriodic (fun x : Euc ℝ 3 => pInf (pairToEuc t x)) := by
  intro x i k
  have h_eq :
      (fun n => (pSeq n)
                  (pairToEuc t
                    (x + k • (standardBasis (n := 3) i))))
        = fun n => (pSeq n) (pairToEuc t x) := by
    funext n
    exact per_n_periodic n x i k
  have h_shift :
      Filter.Tendsto
        (fun n => (pSeq n)
                    (pairToEuc t
                      (x + k • (standardBasis (n := 3) i))))
        Filter.atTop
        (nhds
          (pInf
            (pairToEuc t (x + k • (standardBasis (n := 3) i))))) :=
    pointwise_limit (x + k • (standardBasis (n := 3) i))
  have h_unshift :
      Filter.Tendsto
        (fun n => (pSeq n) (pairToEuc t x))
        Filter.atTop
        (nhds (pInf (pairToEuc t x))) :=
    pointwise_limit x
  rw [h_eq] at h_shift
  exact tendsto_nhds_unique h_shift h_unshift

/-- The CONCRETE bridge for the periodic-conclusion clause
`FeffermanCond10`.

Given:
* a concrete Galerkin sequence `(galerkinSeq, pSeq)` whose every
  member is spatially periodic at every nonneg time `t`,
* pointwise convergence to `(uInf, pInf)` at every nonneg time `t`,

we conclude `FeffermanCond10 uInf pInf` (i.e. the limit `(u, p)` is
spatially periodic at every nonneg time `t`).

This is the SAME architectural pattern as
`lerayHopf_weak_incompressible_from_concrete_galerkin`: the clause is
preserved under pointwise limits because it is a CLOSED equality
condition. -/
theorem lerayHopf_periodicity_from_concrete_galerkin
    (galerkinSeq : ℕ → VelocityField 3)
    (pSeq : ℕ → PressureField 3)
    (uInf : VelocityField 3)
    (pInf : PressureField 3)
    (per_n_velocity_periodic :
      ∀ (n : ℕ) (t : ℝ), 0 ≤ t →
        IsPeriodic (fun x : Euc ℝ 3 => (galerkinSeq n) (pairToEuc t x)))
    (per_n_pressure_periodic :
      ∀ (n : ℕ) (t : ℝ), 0 ≤ t →
        IsPeriodic (fun x : Euc ℝ 3 => (pSeq n) (pairToEuc t x)))
    (velocity_pointwise :
      ∀ (t : ℝ), 0 ≤ t → ∀ y : Euc ℝ 3,
        Filter.Tendsto
          (fun n => (galerkinSeq n) (pairToEuc t y))
          Filter.atTop
          (nhds (uInf (pairToEuc t y))))
    (pressure_pointwise :
      ∀ (t : ℝ), 0 ≤ t → ∀ y : Euc ℝ 3,
        Filter.Tendsto
          (fun n => (pSeq n) (pairToEuc t y))
          Filter.atTop
          (nhds (pInf (pairToEuc t y)))) :
    FeffermanCond10 uInf pInf := by
  refine ⟨?_, ?_⟩
  · intro t ht
    exact
      isPeriodic_velocity_from_pointwise_limit galerkinSeq uInf t
        (fun n => per_n_velocity_periodic n t ht)
        (velocity_pointwise t ht)
  · intro t ht
    exact
      isPeriodic_pressure_from_pointwise_limit pSeq pInf t
        (fun n => per_n_pressure_periodic n t ht)
        (pressure_pointwise t ht)

/-! ## Composition receipt (periodic / Fefferman B + D)

Together with the four R³ clause bridges (re-exported above as
`lerayHopf_*_torus`) and the energy-inequality clause
`lerayHopf_energy_inequality_at_T_torus`, the new lemma
`lerayHopf_periodicity_from_concrete_galerkin` covers the
periodic-domain Clay statement structure:

| Clay periodic-domain field      | concrete bridge theorem                                   |
|---------------------------------|-----------------------------------------------------------|
| `energy_inequality`             | `lerayHopf_energy_inequality_at_T_torus`                  |
| `velocity_regularity`           | `lerayHopf_velocity_regularity_torus`                     |
| `weak_momentum_equation`        | `lerayHopf_weak_momentum_equation_torus`                  |
| `weak_incompressible`           | `lerayHopf_weak_incompressible_torus`                     |
| `weak_initial_condition`        | `lerayHopf_initial_condition_torus`                       |
| `FeffermanCond10` (NEW on 𝕋³)   | `lerayHopf_periodicity_from_concrete_galerkin`            |

## Architecture-transfer assessment

The architecture transfers VERY CLEANLY from `ℝ³` to `𝕋³`:

1. **No type changes**: `VelocityField 3`, `PressureField 3`,
   `pairToEuc`, `partialDeriv`, `kineticEnergy`, `enstrophy`,
   `TimeDomain` all work unchanged.
2. **No test-function-space change**: lean-dojo formulates `WeakSolution`
   weak clauses against compactly-supported smooth test functions on
   `Euc ℝ 3`, NOT against torus-periodic test functions; the periodic
   conclusion is carried by `FeffermanCond10` as a side property.
3. **No bridge modification**: all five abstract bridges
   (energy_inequality, weak_initial_condition, velocity_regularity,
   weak_incompressible, weak_momentum_equation) discharge their
   periodic-domain clauses verbatim.
4. **One additional bridge needed**: `FeffermanCond10` (periodicity
   preservation). The proof is structurally the SAME as
   `weak_incompressible` (both are "limit of pointwise equalities").

The substrate-agnosticism of the typed-companion architecture is
witnessed by the fact that the full periodic bridge file consists
ALMOST ENTIRELY of re-export wrappers; the only new mathematical
content is the periodicity-preservation lemma, which is a 10-line
`tendsto_nhds_unique` argument.
-/

end

end ZtareProofs.NS.ConcreteBridge.Torus
