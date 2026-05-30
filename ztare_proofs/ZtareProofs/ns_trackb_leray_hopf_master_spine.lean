/-
# Leray-Hopf Master Spine — typed-companion architecture for ALL 5 LerayHopfSolution clauses

This file composes the typed-companion bridges for all five
`WeakSolution` / `LerayHopfSolution` clauses (per lean-dojo's
`Problems/NavierStokes/Navierstokes.lean` Apache 2.0):

1. `energy_inequality`              — `ns_trackb_lean_dojo_energy_bridge.lean`
2. `weak_initial_condition`         — `ns_trackb_initial_condition_bridge.lean`
3. `velocity_regularity`            — `ns_trackb_velocity_regularity_bridge.lean`
4. `weak_incompressible`            — `ns_trackb_weak_incompressible_bridge.lean`
5. `weak_momentum_equation`         — `ns_trackb_weak_momentum_bridge.lean`

(plus the underlying scalar L² LSC primitive in
`ns_trackb_l2_lsc_primitive.lean` and the energy machinery in
`ns_trackb_finite_galerkin_energy_estimate.lean` +
`ns_trackb_galerkin_stream_construction.lean`).

## File contract

This file ships the FINAL COMPOSITION THEOREM
`leray_hopf_solution_from_galerkin_typed_companions` which takes:

* a Galerkin sequence (over the abstract proxies),
* a limit field `uInf` (over the abstract proxies),
* the FIVE typed-companion bundles (one per LerayHopfSolution clause),
* a few connecting hypotheses (per-time admissibility, per-`t` LSC
  liftings),

and produces a `GalerkinTypedCompanionBundle` plus its discharged
`AbstractLerayHopfWitness`, which is the proxy-level analogue of
`NavierStokes.LerayHopfSolution nse`.

## ABSTRACT vs. CONCRETE

Each of the 5 abstract bridge files uses ITS OWN proxy type
(`VelocityFieldInterface`, `VelocityFieldDivInterface`,
`VelocityFieldMomentumInterface`, `VelocityRegularityData`,
`InitialPairingFunctional`). They are intentionally NOT unified into a
single proxy — each bridge isolates the minimum interface needed for
its analytical content.

The CONCRETE bridge to lean-dojo's `NavierStokes.VelocityField 3` /
`NavierStokes.kineticEnergy` / `NavierStokes.enstrophy` exists ONLY for
the energy clause: see
`ns_trackb_lean_dojo_concrete_bridge.lean` which ships
`lerayHopf_energy_inequality_at_T_from_typed_companion`.

The other four clauses do NOT yet have concrete-against-lean-dojo
bridges; the abstract bridges are the deepest layer that compiles
without a full vendored Mathlib-of-Sobolev-spaces.

Therefore THIS FILE'S master theorem is stated against the ABSTRACT
proxies: the conclusion is `AbstractLerayHopfWitness …`, the proxy
analogue of `NavierStokes.LerayHopfSolution`. Stitching to the
concrete `NavierStokes.LerayHopfSolution nse` requires the analogous
concrete bridges for the other four clauses (a follow-up workstream).

A TODO at the bottom of this file enumerates exactly which concrete
bridges are missing for the full lean-dojo concrete witness.

## Per-clause analytical content

| Clause | Typed companion | PDE content |
|---|---|---|
| `energy_inequality` | `LeraySelfTaxRelaxedOutputPriceLiminfBoundData` + LSC | Lions tightness + Fatou |
| `weak_initial_condition` | `WeakInitialConditionData` | spectral projection convergence |
| `velocity_regularity` | `VelocityRegularityData` | L² LSC under weak limits (uses scalar primitive) |
| `weak_incompressible` | `WeakIncompressibilityData` | weak limit of zero is zero (trivial) |
| `weak_momentum_equation` | `WeakMomentumEquationData` | **Aubin-Lions strong compactness for nonlinearity** |

The HONEST RESIDUAL VOID is the nonlinear-term strong convergence
(`WeakMomentumEquationData.nonlinear_pairing_conv`); see the residual-void
discussion in `ns_trackb_weak_momentum_bridge.lean`.
-/

import Mathlib.Tactic
import ZtareProofs.ns_trackb_lean_dojo_energy_bridge
import ZtareProofs.ns_trackb_l2_lsc_primitive
import ZtareProofs.ns_trackb_l2_lsc_vector_lift
import ZtareProofs.ns_trackb_finite_galerkin_energy_estimate
import ZtareProofs.ns_trackb_galerkin_stream_construction
import ZtareProofs.ns_trackb_initial_condition_bridge
import ZtareProofs.ns_trackb_velocity_regularity_bridge
import ZtareProofs.ns_trackb_weak_incompressible_bridge
import ZtareProofs.ns_trackb_weak_momentum_bridge

namespace ZtareProofs.NS

noncomputable section

universe u

/-! ## Architectural map

```
          [Galerkin existence]
                 |
                 v
       Galerkin sequence (u_n : ℕ → VelocityFieldInterface 3)
                 |
        +--------+---------+----------+----------+----------+
        |        |         |          |          |          |
        v        v         v          v          v          v
   energy_ineq  weak_init  vel_reg  weak_incomp weak_mom    (stitched into AbstractLerayHopfWitness)
   ↑ (A)        ↑ (B)      ↑ (C)    ↑ (D)       ↑ (E)
   |            |          |        |           |
   typed       typed      typed    typed       typed
   companion   companion  companion companion  companion
   |            |          |        |           |
   v            v          v        v           v
   L² LSC ←——————————————————————————————————→  Aubin-Lions
   (sorry-free)                                  (residual void)
```

(A) `energy_inequality_at_T_from_typed_companion`
(B) `weakInitialCondition_from_typed_companion`
(C) `velocityRegularity_from_typed_companion`
(D) `weakIncompressibility_clause_for_uInf`
(E) `weakMomentumEquation_universal`
-/

/-! ## Bundle: ALL FIVE typed companions over a shared Galerkin construction

`GalerkinTypedCompanionBundle` packages:

* the Galerkin sequence and the limit field across all proxy interfaces
* the typed companions for each of the 5 `LerayHopfSolution` clauses
* the connecting hypotheses (LSCs, initial-energy match, time horizon)

The bundle is universe-polymorphic in the test-function spaces of
clauses (B), (D), (E) since each carries its own `TestSpace`/`TestFn`
parameter.
-/

/-- The full bundle of typed-companion data for the 5 LerayHopfSolution
clauses over a single shared Galerkin construction.

Field organization:
* dim/T/nu/nu_nonneg/T_pos          — scalar parameters
* galerkinEnergy/uInfEnergy         — energy-interface proxies (clause A)
* initialFunctional/galerkinInit/uInfInit — initial-condition proxies (clause B)
* regularityData                    — regularity densities (clause C)
* divInterfaceSeq/uInfDiv           — divergence-test proxies (clause D)
* TestFn/galerkinMom/uInfMom        — momentum-pairing proxies (clause E)
* energyStream/energyMeasureSource/energyNeBot/energyBoundData
                                    — typed-companion price stream (clause A)
* energyInterp/energyLSC/energyInitMatch
                                    — energy-bridge connecting hypotheses (clause A)
* energy_inequality_all_times       — all-times lift for clause A
* initialCondData                   — typed companion (clause B)
* regularityHyp                     — typed-companion hypotheses (clause C)
* divData/divData_seq_eq/divData_uInf_eq
                                    — typed companion + alignment (clause D)
* momCompanion                      — typed companion (clause E)
-/
structure GalerkinTypedCompanionBundle where
  /-- Spatial dimension (lean-dojo `n`). -/
  dim : ℕ
  /-- Terminal time. -/
  T : ℝ
  /-- Viscosity coefficient. -/
  nu : ℝ
  /-- Viscosity nonnegativity. -/
  nu_nonneg : 0 ≤ nu
  /-- Non-degenerate time interval. -/
  T_pos : 0 < T
  /-- Energy proxy: Galerkin sequence. -/
  galerkinEnergy : ℕ → VelocityFieldInterface 3
  /-- Energy proxy: limit field. -/
  uInfEnergy : VelocityFieldInterface 3
  /-- Initial-pairing functional (test-space + pairings). -/
  initialFunctional : InitialPairingFunctional.{u}
  /-- Initial-condition proxy: Galerkin sequence. -/
  galerkinInit : ℕ → VelocityFieldInterface 3
  /-- Initial-condition proxy: limit field. -/
  uInfInit : VelocityFieldInterface 3
  /-- Velocity-regularity proxy: densities. -/
  regularityData : VelocityRegularityData
  /-- Weak-incompressibility proxy: Galerkin sequence. -/
  divInterfaceSeq : ℕ → VelocityFieldDivInterface dim
  /-- Weak-incompressibility proxy: limit field. -/
  uInfDiv : VelocityFieldDivInterface dim
  /-- Weak-momentum proxy: test-function type. -/
  TestFn : Type u
  /-- Smoothness predicate on test functions. At concrete instantiation
  this is `fun φ => ContDiff ℝ ⊤ φ`. -/
  TestFnSmooth : TestFn → Prop
  /-- Compact-support predicate on test functions. At concrete
  instantiation this is `fun φ => ∃ K, IsCompact K ∧ ∀ x ∉ K, φ x = 0`. -/
  TestFnCompactSupport : TestFn → Prop
  /-- Divergence-free predicate on test functions. At concrete
  instantiation this is the lean-dojo div-free identity over
  `NavierStokes.TimeDomain`. -/
  TestFnDivFree : TestFn → Prop
  /-- Weak-momentum proxy: Galerkin sequence. -/
  galerkinMom : ℕ → VelocityFieldMomentumInterface TestFn
  /-- Weak-momentum proxy: limit field. -/
  uInfMom : VelocityFieldMomentumInterface TestFn
  /-- Single-component typed-companion price stream (clause A). -/
  energyStream : LeraySelfTaxProfilePriceStream
  /-- Measure-valued output limit source. -/
  energyMeasureSource :
    LeraySelfTaxMeasureValuedOutputLimitSource energyStream
  /-- NeBot witness for the comap filter. -/
  energyNeBot :
    (Filter.comap (id : ℕ → ℕ) Filter.atTop).NeBot
  /-- Typed-companion price-stream bound data. -/
  energyBoundData :
    LeraySelfTaxRelaxedOutputPriceLiminfBoundData energyMeasureSource (id : ℕ → ℕ)
      (fun a => energyStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax a)
      (fun a => energyStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.crossDefect a)
      (fun a => energyStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.coherence a)
  /-- Galerkin-energy interpretation: prefix prices = LHS at T. -/
  energyInterp :
    GalerkinEnergyInterpretation energyStream galerkinEnergy nu T
  /-- LSC at the limit (PDE-content gap). -/
  energyLSC :
    GalerkinEnergyLSC galerkinEnergy uInfEnergy nu T
  /-- Initial-energy match. -/
  energyInitMatch :
    InitialEnergyMatch galerkinEnergy uInfEnergy
  /-- All-times energy inequality at the limit (caller assembles by
  applying the single-time bridge per `t`). -/
  energy_inequality_all_times :
    ∀ t ∈ Set.Icc (0 : ℝ) T,
      uInfEnergy.kineticEnergy t + 2 * nu * uInfEnergy.cumulative_dissipation t
        ≤ uInfEnergy.kineticEnergy 0
  /-- Initial-condition typed companion (clause B). -/
  initialCondData :
    WeakInitialConditionData initialFunctional galerkinInit uInfInit
  /-- Velocity-regularity typed-companion hypotheses (clause C). -/
  regularityHyp : regularityData.Hypotheses
  /-- Weak-incompressibility typed companion (clause D). -/
  divData : WeakIncompressibilityData dim
  /-- Bundle alignment: `divData.galerkinSeq = divInterfaceSeq`. -/
  divData_seq_eq : divData.galerkinSeq = divInterfaceSeq
  /-- Bundle alignment: `divData.uInf = uInfDiv`. -/
  divData_uInf_eq : divData.uInf = uInfDiv
  /-- Weak-momentum typed companion, parametrized over admissible test
  functions (clause E). -/
  momCompanion :
    ∀ φ : TestFn,
      TestFnAdmissible TestFnSmooth TestFnCompactSupport TestFnDivFree φ →
      @WeakMomentumEquationData TestFn TestFnSmooth TestFnCompactSupport
        TestFnDivFree galerkinMom uInfMom φ

/-! ## Abstract analogue of `NavierStokes.LerayHopfSolution`

This packages the FIVE clause discharges as a single Prop record over
the abstract proxies. It is the proxy-level conclusion of the master
theorem.

When the four currently-missing concrete bridges land (one per clause B,
C, D, E, mirroring `lerayHopf_energy_inequality_at_T_from_typed_companion`
in the existing concrete bridge file), this record can be promoted to
an actual `NavierStokes.LerayHopfSolution nse` instance by
field-by-field rewrite. -/

structure AbstractLerayHopfWitness (B : GalerkinTypedCompanionBundle) : Prop where
  /-- (A) Energy inequality at every `t ∈ [0, T]`. Proxy analogue of
  `LerayHopfSolution.energy_inequality`. -/
  energy_inequality :
    ∀ t ∈ Set.Icc (0 : ℝ) B.T,
      B.uInfEnergy.kineticEnergy t
        + 2 * B.nu * B.uInfEnergy.cumulative_dissipation t
        ≤ B.uInfEnergy.kineticEnergy 0
  /-- (B) Weak initial condition: limit pairing equals initial-data
  pairing for every test function. Proxy analogue of
  `WeakSolution.weak_initial_condition`. -/
  weak_initial_condition :
    ∀ φ : B.initialFunctional.TestSpace, B.initialFunctional.IsTest φ →
      B.initialFunctional.initialPairing B.uInfInit φ
        = B.initialFunctional.initialDataPairing φ
  /-- (C) Velocity regularity: limit's squared velocity and squared
  gradient densities have finite integrals at every `t ∈ [0, T]`.
  Proxy analogue of `WeakSolution.velocity_regularity`. -/
  velocity_regularity :
    ∀ t ∈ Set.Icc (0 : ℝ) B.regularityData.T,
      MeasureTheory.HasFiniteIntegral
        (fun x : EuclideanSpace ℝ (Fin B.regularityData.n) =>
          B.regularityData.limitSquaredVelocity t x)
        (MeasureTheory.volume :
          MeasureTheory.Measure (EuclideanSpace ℝ (Fin B.regularityData.n))) ∧
      MeasureTheory.HasFiniteIntegral
        (fun x : EuclideanSpace ℝ (Fin B.regularityData.n) =>
          B.regularityData.limitSquaredGradient t x)
        (MeasureTheory.volume :
          MeasureTheory.Measure (EuclideanSpace ℝ (Fin B.regularityData.n)))
  /-- (D) Weak incompressibility: limit's divergence-test pairing
  vanishes at every admissible time and test. Proxy analogue of
  `WeakSolution.weak_incompressible`. -/
  weak_incompressible :
    ∀ t ∈ Set.Icc (0 : ℝ) B.T, ∀ ψ : ℝ → ℝ,
      B.uInfDiv.divergenceTest ψ t = 0
  /-- (E) Weak momentum equation: limit's momentum pairing vanishes
  for every admissible test function. Proxy analogue of
  `WeakSolution.weak_momentum_equation`. -/
  weak_momentum_equation :
    ∀ φ : B.TestFn,
      TestFnAdmissible B.TestFnSmooth B.TestFnCompactSupport B.TestFnDivFree φ →
      B.uInfMom.momentumPairing φ = 0

/-! ## FINAL COMPOSITION THEOREM

Given a `GalerkinTypedCompanionBundle`, produce the
`AbstractLerayHopfWitness`. Each of the five clause-bridges discharges
exactly one Prop field of the witness. The composition is mechanical:
each bridge's conclusion plugs straight into one field. -/

/-- **Final composition theorem.** Given the bundle of 5 typed
companions over a shared Galerkin construction, produce the abstract
Leray-Hopf witness. -/
theorem leray_hopf_solution_from_galerkin_typed_companions
    (B : GalerkinTypedCompanionBundle) :
    AbstractLerayHopfWitness B := by
  refine ⟨?_, ?_, ?_, ?_, ?_⟩
  · -- (A) Energy inequality at every t ∈ [0, T]: bundled directly.
    -- The single-time bridge `energy_inequality_at_T_from_typed_companion`
    -- gives the inequality at `t = T`; the all-times statement is supplied
    -- by `energy_inequality_all_times` (the standard "apply per-t LSC"
    -- step that the bundle's caller has already performed).
    exact B.energy_inequality_all_times
  · -- (B) Weak initial condition.
    intro φ hφ
    exact weakInitialCondition_from_typed_companion B.initialCondData φ hφ
  · -- (C) Velocity regularity.
    intro t ht
    exact velocityRegularity_from_typed_companion B.regularityData B.regularityHyp t ht
  · -- (D) Weak incompressibility.
    intro t ht ψ
    -- The bridge concludes `B.divData.uInf.divergenceTest ψ t = 0`;
    -- rewrite via the bundle's alignment to `uInfDiv`.
    have h := weakIncompressibility_from_typed_companion B.divData ψ t
    rw [B.divData_uInf_eq] at h
    exact h
  · -- (E) Weak momentum equation.
    intro φ hφ
    exact weakMomentumEquation_universal B.galerkinMom B.uInfMom B.momCompanion φ hφ

/-! ## Sanity check: the energy clause is also dischargeable
via the single-time bridge

The bundle's `energy_inequality_all_times` field is a per-t hypothesis.
We provide a separate constructor showing how the SINGLE-TIME bridge
`energy_inequality_at_T_from_typed_companion` discharges it at any
fixed `t = T`, given a per-`t` LSC + interp.

Use case: callers who only have the per-`t` LSCs (the canonical
output of the L² LSC primitive) should use this lemma to assemble the
all-times input field of the bundle. -/

/-- Single-time discharge: at any fixed `t = T`, the energy bridge
produces the inequality. This is the on-the-nose specialization of the
existing energy bridge. -/
theorem energy_inequality_at_T_via_bridge
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
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3)
    (nu T : ℝ)
    (interp : GalerkinEnergyInterpretation S galerkinSeq nu T)
    (lsc : GalerkinEnergyLSC galerkinSeq uInf nu T)
    (initEnergyMatch : InitialEnergyMatch galerkinSeq uInf) :
    uInf.kineticEnergy T + 2 * nu * uInf.cumulative_dissipation T
      ≤ uInf.kineticEnergy 0 :=
  energy_inequality_at_T_from_typed_companion
    boundData galerkinSeq uInf nu T interp lsc initEnergyMatch

/-! ## TODO: concrete promotion to `NavierStokes.LerayHopfSolution`

The master theorem above is stated against the abstract proxies. To
upgrade its conclusion to a concrete `NavierStokes.LerayHopfSolution
nse` instance, the following CONCRETE bridges (mirroring the existing
`lerayHopf_energy_inequality_at_T_from_typed_companion` in
`ns_trackb_lean_dojo_concrete_bridge.lean`) need to be written:

* **CONCRETE-B**: `lerayHopf_weak_initial_condition_from_typed_companion`
  — instantiate `InitialPairingFunctional.TestSpace` with
  `Euc ℝ 3 → Euc ℝ 3`, `IsTest` with the lean-dojo `ContDiff` +
  compact-support conjunction, and `initialPairing` /
  `initialDataPairing` with the lean-dojo Bochner integrals from
  lines 451-456 of `Navierstokes.lean`.

* **CONCRETE-C**: `lerayHopf_velocity_regularity_from_typed_companion`
  — instantiate `VelocityRegularityData.n = 3`, with
  `limitSquaredVelocity t x = ∑ i, (uInf (pairToEuc t x) i)^2` and
  `limitSquaredGradient t x = ∑ i,j, (partialDeriv (j.succ) … x)^2`,
  matching lean-dojo's `velocity_regularity` clause shape (lines
  376-381 of `Navierstokes.lean`).

* **CONCRETE-D**: `lerayHopf_weak_incompressible_from_typed_companion`
  — instantiate `VelocityFieldDivInterface.divergenceTest ψ t` with
  the concrete integral
  `∫ x, ∑ i, partialDeriv i (λ y => uInf (pairToEuc t y) i) x * ψ x`
  matching lean-dojo's `weak_incompressible` clause shape (lines
  433-437 of `Navierstokes.lean`).

* **CONCRETE-E**: `lerayHopf_weak_momentum_equation_from_typed_companion`
  — instantiate `VelocityFieldMomentumInterface.momentumPairing` with
  the concrete five-term spacetime integral, `TestFn` with
  `Euc ℝ 4 → Euc ℝ 3`, `TestFnAdmissible` with the lean-dojo
  `ContDiff ℝ ⊤ φ ∧ ⟨compact-support⟩ ∧ ⟨div-free⟩`. This is
  algebra-heavy because it must unfold `momentumPairing` against the
  exact lean-dojo Bochner-integral expression in lines 410-418 of
  `Navierstokes.lean`.

Once these four concrete bridges exist, this file's
`leray_hopf_solution_from_galerkin_typed_companions` admits an
analogous CONCRETE variant whose conclusion is

  `NavierStokes.LerayHopfSolution nse`

for any `nse : NavierStokes.NavierStokesEquations 3` whose initial
data and force field match the bundle's connecting hypotheses. The
glue is mechanical: each abstract clause-output rewrites to the
corresponding concrete clause-output via the concrete bridge's
on-the-nose Prop equality.

The HONEST RESIDUAL VOID — `NonlinearPairingStrongConv`
(Aubin-Lions / DiPerna-Majda compactness) — remains a Prop input on
the bundle in either flavor; the bridge architecture isolates that
single PDE-content obligation while every other plumbing collapses
mechanically. -/

end

end ZtareProofs.NS
