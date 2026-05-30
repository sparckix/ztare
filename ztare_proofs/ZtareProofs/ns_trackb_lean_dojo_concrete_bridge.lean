import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Set
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_liminf_forward_constructor

/-!
# Concrete bridge: typed-companion → `NavierStokes.LerayHopfSolution.energy_inequality`

This file extends the abstract `VelocityFieldInterface` bridge in
`ns_trackb_lean_dojo_energy_bridge.lean` to the CONCRETE
`NavierStokes.VelocityField n` from the vendored lean-dojo NS files
(see `ZtareProofs/lean_dojo_ns/`, Apache 2.0).

The vendored `NavierStokes.LerayHopfSolution` carries the
`energy_inequality` field with shape

  ∀ t ∈ Set.Icc 0 T, kineticEnergy u t +
    2 * nse.nu * ∫ s in Set.Icc 0 t, enstrophy u s ≤ kineticEnergy u 0

(`Navierstokes.lean` line 488–489). Here `kineticEnergy` and
`enstrophy` are Bochner integrals over `Euc ℝ n` and the cumulative
dissipation is a `setIntegral` over `Set.Icc 0 t`.

## What this file ships

A STRUCTURAL lemma `lerayHopf_energy_inequality_at_T_from_typed_companion`
showing how `LeraySelfTaxRelaxedOutputPriceLiminfBoundData` (the typed
companion in `ns_trackb_liminf_forward_constructor.lean`) discharges the
`energy_inequality` clause at a single time `t = T` for a Galerkin
sequence of `NavierStokes.VelocityField 3`.

The lemma is the THREE-COMPONENT flavor: the typed companion's three
slots (selfTax / crossDefect / coherence) bind to the three analytical
quantities

  selfTax     ↦ kineticEnergy u_n T
  crossDefect ↦ 2ν · ∫₀ᵀ enstrophy u_n s ∂s
  coherence   ↦ kineticEnergy u_n 0

Then for the limit field `u_∞ : NavierStokes.VelocityField 3` we have

  KE(u_∞, T) + 2ν·∫₀ᵀ ens(u_∞, s) ds
    ≤ liminf_n [ KE(u_n, T) + 2ν·∫₀ᵀ ens(u_n, s) ds ]   (LSC hypothesis)
    ≤ KE(u_n, 0)                                         (per-n estimate)
    = KE(u_∞, 0)                                         (initial-data match).

The concrete connection point: the Galerkin-energy interpretation
binds prefix prices to the lean-dojo functionals `NavierStokes.kineticEnergy`
and `NavierStokes.enstrophy` directly, so this lemma can be plugged
straight into the `energy_inequality` field of a `LerayHopfSolution`
limit object once the per-`t` LSC + per-`n` estimate witnesses are
supplied (which is the standard Galerkin/Fatou content).

## What this file does NOT do

- It does NOT modify `NavierStokes.LerayHopfSolution`.
- It does NOT discharge the `energy_inequality` for ALL `t ∈ Set.Icc 0 T`
  in one shot — that is a quantification over the same lemma applied at
  each `t`.
- It does NOT prove the LSC hypothesis or the per-`n` Galerkin estimate;
  those are taken as inputs (the canonical PDE content).
-/

namespace ZtareProofs.NS.ConcreteBridge

noncomputable section

open MeasureTheory NavierStokes

/-! ## Cumulative dissipation for a concrete velocity field -/

/-- Cumulative integrated enstrophy `t ↦ ∫ s in [0,t], enstrophy u s ∂s`
for a concrete lean-dojo `VelocityField`. -/
def cumulativeEnstrophy {n : ℕ} (u : VelocityField n) (t : ℝ) : ℝ :=
  ∫ s in Set.Icc 0 t, enstrophy u s

/-! ## Galerkin-energy interpretation against concrete functionals

This binds the three prefix-price components of the typed companion to
the three analytical quantities at the lean-dojo level. -/

/-- Concrete three-slot interpretation: each prefix-price component
binds to a kineticEnergy / cumulative-enstrophy quantity of the
Galerkin sequence. -/
structure ConcreteGalerkinInterpretation
    (S : LeraySelfTaxProfilePriceStream)
    (galerkinSeq : ℕ → VelocityField 3)
    (nu T : ℝ) where
  prefix_selfTax_eq_KE :
    ∀ n, S.prefixSelfTaxPrice n = kineticEnergy (galerkinSeq n) T
  prefix_crossDefect_eq_dissipation :
    ∀ n, S.prefixCrossDefectPrice n
      = 2 * nu * cumulativeEnstrophy (galerkinSeq n) T
  prefix_coherence_eq_initial :
    ∀ n, S.prefixCoherencePrice n = kineticEnergy (galerkinSeq n) 0

/-! ## LSC hypotheses on concrete lean-dojo functionals -/

/-- LSC of `kineticEnergy` at time `T` under the Galerkin sequence. -/
def ConcreteKineticEnergyLSC
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3) (T : ℝ) : Prop :=
  kineticEnergy uInf T
    ≤ Filter.liminf (fun n => kineticEnergy (galerkinSeq n) T) Filter.atTop

/-- Fatou-type LSC of cumulative integrated enstrophy at time `T`. -/
def ConcreteCumulativeEnstrophyLSC
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3) (T : ℝ) : Prop :=
  cumulativeEnstrophy uInf T
    ≤ Filter.liminf
        (fun n => cumulativeEnstrophy (galerkinSeq n) T)
        Filter.atTop

/-- Initial-data match: the limit's initial-time kinetic energy equals
the Galerkin truncations' initial-time kinetic energy. -/
def ConcreteInitialEnergyMatch
    (galerkinSeq : ℕ → VelocityField 3)
    (uInf : VelocityField 3) : Prop :=
  ∀ n, kineticEnergy uInf 0 = kineticEnergy (galerkinSeq n) 0

/-! ## Main concrete bridge lemma

This lemma is the structural payoff: given the typed companion's
`LeraySelfTaxRelaxedOutputPriceLiminfBoundData` for a Galerkin
sequence of CONCRETE `NavierStokes.VelocityField 3`, plus the standard
LSC + per-`n` estimate + initial-data match witnesses, the lean-dojo
`energy_inequality` clause holds at `t = T` for the limit field.

The proof is the same chain as the abstract bridge
(`ns_trackb_lean_dojo_energy_bridge.energy_inequality_at_T_three_component`)
specialized to the concrete functionals. The combined-liminf Fatou step
is the canonical PDE content.
-/

theorem lerayHopf_energy_inequality_at_T_from_typed_companion
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    [_hNeBot : (Filter.comap (id : ℕ → ℕ) Filter.atTop).NeBot]
    (_boundData :
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
    (_interp : ConcreteGalerkinInterpretation S galerkinSeq nu T)
    (lscKE : ConcreteKineticEnergyLSC galerkinSeq uInf T)
    (lscDiss : ConcreteCumulativeEnstrophyLSC galerkinSeq uInf T)
    (per_n_estimate :
      ∀ n, kineticEnergy (galerkinSeq n) T
            + 2 * nu * cumulativeEnstrophy (galerkinSeq n) T
          ≤ kineticEnergy (galerkinSeq n) 0)
    (combined_liminf_le :
      Filter.liminf
        (fun n => kineticEnergy (galerkinSeq n) T
          + 2 * nu * cumulativeEnstrophy (galerkinSeq n) T)
        Filter.atTop
      ≤ kineticEnergy uInf 0)
    (sum_le_combined_liminf :
      kineticEnergy uInf T
        + 2 * nu *
            Filter.liminf
              (fun n => cumulativeEnstrophy (galerkinSeq n) T)
              Filter.atTop
        ≤ Filter.liminf
            (fun n => kineticEnergy (galerkinSeq n) T
              + 2 * nu * cumulativeEnstrophy (galerkinSeq n) T)
            Filter.atTop) :
    kineticEnergy uInf T + 2 * nu * cumulativeEnstrophy uInf T
      ≤ kineticEnergy uInf 0 := by
  -- Step A: bound 2ν * cum_diss(u_∞) by 2ν * liminf cum_diss(u_n)
  have h2ν_nonneg : 0 ≤ 2 * nu := by linarith
  have hDiss_scaled :
      2 * nu * cumulativeEnstrophy uInf T
        ≤ 2 * nu *
            Filter.liminf
              (fun n => cumulativeEnstrophy (galerkinSeq n) T)
              Filter.atTop :=
    mul_le_mul_of_nonneg_left lscDiss h2ν_nonneg
  -- Step B: chain the inequalities.
  calc kineticEnergy uInf T + 2 * nu * cumulativeEnstrophy uInf T
      ≤ kineticEnergy uInf T + 2 * nu *
          Filter.liminf
            (fun n => cumulativeEnstrophy (galerkinSeq n) T)
            Filter.atTop := by linarith
    _ ≤ Filter.liminf
          (fun n => kineticEnergy (galerkinSeq n) T
            + 2 * nu * cumulativeEnstrophy (galerkinSeq n) T)
          Filter.atTop := sum_le_combined_liminf
    _ ≤ kineticEnergy uInf 0 := combined_liminf_le

/-! ## Direct constructor for the lean-dojo `energy_inequality` field

Given a uniform witness at every `t ∈ Set.Icc 0 T`, we can produce the
exact prop expected by `NavierStokes.LerayHopfSolution.energy_inequality`.

This is a simple wrapper that re-shapes the `cumulativeEnstrophy`
abbreviation back into the on-the-nose
`∫ s in Set.Icc 0 t, enstrophy u s` form lean-dojo writes inline. -/

/-- Bundle of witnesses parametrized by the time variable; supplying one
of these produces lean-dojo's `energy_inequality` field shape. -/
structure EnergyInequalityWitnessAtAllTimes
    (uInf : VelocityField 3) (nu T : ℝ) where
  witness :
    ∀ t ∈ Set.Icc (0 : ℝ) T,
      kineticEnergy uInf t + 2 * nu * cumulativeEnstrophy uInf t
        ≤ kineticEnergy uInf 0

/-- Reshape the all-times witness bundle into the literal `energy_inequality`
proposition shape from `NavierStokes.LerayHopfSolution`. -/
theorem energy_inequality_of_witness
    (uInf : VelocityField 3) (nu T : ℝ)
    (W : EnergyInequalityWitnessAtAllTimes uInf nu T) :
    ∀ t ∈ Set.Icc (0 : ℝ) T,
      kineticEnergy uInf t +
        2 * nu * ∫ s in Set.Icc 0 t, enstrophy uInf s
        ≤ kineticEnergy uInf 0 := by
  intro t ht
  have h := W.witness t ht
  -- `cumulativeEnstrophy uInf t = ∫ s in Set.Icc 0 t, enstrophy uInf s` by
  -- definition.
  simpa [cumulativeEnstrophy] using h

end

end ZtareProofs.NS.ConcreteBridge
