import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Set
import ZtareProofs.ns_profile_lsc_self_tax_obligation
import ZtareProofs.ns_gp216_bridge_composition_receipt
import ZtareProofs.ns_trackb_lean_dojo_energy_bridge

/-!
# Track B — concrete Galerkin → typed-companion stream construction

This file provides the missing concrete glue between a PDE-side Galerkin
sequence `u_n : ℕ → VelocityFieldInterface 3` and the abstract typed-companion
`LeraySelfTaxProfilePriceStream` from `ns_profile_lsc_self_tax_obligation.lean`.

The earlier file `ns_trackb_lean_dojo_energy_bridge.lean` only EXPOSED the
interpretation as a `GalerkinEnergyInterpretation` *hypothesis* — it never
built the stream. This file builds it, picking the natural definitions:

```
prefixSelfTaxPrice n := (u_n).kineticEnergy T
                          + 2 * nu * (u_n).cumulative_dissipation T
selfTaxLimitPrice    := E_0      -- given initial-energy bound
```

Conceptually, `(u_n).cumulative_dissipation T` is the time integral

  `∫ s in Set.Icc 0 T, enstrophy(u_n, s)`

which matches the lean-dojo `setIntegral` shape. The current
`VelocityFieldInterface` proxy carries `cumulative_dissipation : ℝ → ℝ` as a
ready-built scalar field; if/when this file is composed against the actual
lean-dojo definitions, the convention `cumulative_dissipation T :=
∫ s in Set.Icc 0 T, enstrophy u s` is the substitution to make. We document
that convention explicitly here so downstream files can rely on it.

The cross-defect and coherence prefix prices are taken as zero placeholders
by default, i.e. this construction targets the energy-only single-component
Leray-Hopf inequality. Callers who need non-trivial cross-defect/coherence
ledgers can use the `ofGalerkinSequenceWithObservables` variant which takes
auxiliary Galerkin observables.

## Hypotheses

This file does NOT prove convergence (that's the LSC obligation handled by
the GalerkinEnergyLSC hypothesis in `ns_trackb_lean_dojo_energy_bridge.lean`).
It only sets up the substrate. The hypotheses we record at the construction
site are:

* `energyEstimate : ∀ n, KE(u_n,T) + 2ν * cum_diss(u_n,T) ≤ E_0`
  — the finite-Galerkin energy estimate (workstream 2 deliverable).
* `KE_nonneg : ∀ n, 0 ≤ KE(u_n,T)`
* `cumDiss_nonneg : ∀ n, 0 ≤ cum_diss(u_n,T)`

These are recorded as `Prop` fields on the bundling structure
`GalerkinStreamData`; the construction itself does not depend on them, but
the structural lemmas do.
-/

namespace ZtareProofs.NS

noncomputable section

universe u

/-! ## Galerkin observable bundle for the concrete stream

We bundle the Galerkin sequence, fixed final time, viscosity, initial-energy
bound, and standard non-negativity / energy-estimate hypotheses into one
structure so downstream constructors can take a single argument. -/

/-- Concrete Galerkin-side data for building a `LeraySelfTaxProfilePriceStream`.

`galerkinSeq n` is the n-th Galerkin truncation as a
`VelocityFieldInterface 3`; it carries `kineticEnergy` and
`cumulative_dissipation` (where the convention is
`cumulative_dissipation T = ∫ s in Set.Icc 0 T, enstrophyIntegral u_n s`).

`E_0` is the declared initial-energy bound; in the canonical instantiation
it is `(galerkinSeq 0).kineticEnergy 0` (or any uniform bound). -/
structure GalerkinStreamData where
  galerkinSeq : ℕ → VelocityFieldInterface 3
  T : ℝ
  nu : ℝ
  E_0 : ℝ
  energy_estimate :
    ∀ n,
      (galerkinSeq n).kineticEnergy T
        + 2 * nu * (galerkinSeq n).cumulative_dissipation T
        ≤ E_0
  kineticEnergy_T_nonneg :
    ∀ n, 0 ≤ (galerkinSeq n).kineticEnergy T
  cumulative_dissipation_T_nonneg :
    ∀ n, 0 ≤ (galerkinSeq n).cumulative_dissipation T

/-! ## The concrete stream construction (energy-only, zero placeholders)

We pick the cross-defect and coherence prefix prices to be identically zero
and the corresponding limit prices to be zero. The construction is therefore
focused on the self-tax / energy axis, which is the only axis used by
`energy_inequality_at_T_from_typed_companion`. -/

/-- Build a `LeraySelfTaxProfilePriceStream` from concrete Galerkin data,
using zero placeholders for the cross-defect and coherence ledgers.

This is the canonical bridge from a PDE-side Galerkin sequence to the
typed-companion abstract stream. -/
def LeraySelfTaxProfilePriceStream.ofGalerkinData
    (G : GalerkinStreamData) : LeraySelfTaxProfilePriceStream where
  prefixPayoff := fun _ => 0
  prefixSelfTaxPrice := fun n =>
    (G.galerkinSeq n).kineticEnergy G.T
      + 2 * G.nu * (G.galerkinSeq n).cumulative_dissipation G.T
  prefixCrossDefectPrice := fun _ => 0
  prefixCoherencePrice := fun _ => 0
  payoffLimit := 0
  selfTaxLimitPrice := G.E_0
  crossDefectLimitPrice := 0
  coherenceLimitPrice := 0
  profileTopologyDeclaredBeforePayoff := True
  profileStreamDeclaredBeforePayoff := True
  prefixComponentPricesDeclaredBeforePayoff := True
  limitComponentPricesDeclaredBeforePayoff := True
  noPosthocPayoffDependentStreamChoice := True

/-! ### Variant: nonzero auxiliary cross-defect / coherence observables

When the caller has actual Galerkin-side cross-defect and coherence
observables (e.g. anti-symmetric trilinear remainders, projected coherence
inner products), we offer a richer variant. The cross/coherence ledgers are
taken to be those auxiliary observables with limit prices supplied by the
caller. -/

/-- Build a `LeraySelfTaxProfilePriceStream` from Galerkin data PLUS
auxiliary cross-defect and coherence observable families. -/
def LeraySelfTaxProfilePriceStream.ofGalerkinDataWithObservables
    (G : GalerkinStreamData)
    (crossDefectObs coherenceObs : ℕ → ℝ)
    (crossDefectLimit coherenceLimit : ℝ) :
    LeraySelfTaxProfilePriceStream where
  prefixPayoff := fun _ => 0
  prefixSelfTaxPrice := fun n =>
    (G.galerkinSeq n).kineticEnergy G.T
      + 2 * G.nu * (G.galerkinSeq n).cumulative_dissipation G.T
  prefixCrossDefectPrice := crossDefectObs
  prefixCoherencePrice := coherenceObs
  payoffLimit := 0
  selfTaxLimitPrice := G.E_0
  crossDefectLimitPrice := crossDefectLimit
  coherenceLimitPrice := coherenceLimit
  profileTopologyDeclaredBeforePayoff := True
  profileStreamDeclaredBeforePayoff := True
  prefixComponentPricesDeclaredBeforePayoff := True
  limitComponentPricesDeclaredBeforePayoff := True
  noPosthocPayoffDependentStreamChoice := True

/-! ## Definitional unfolding lemmas

These are `rfl`-level identities exposed for downstream use; in particular
they let us discharge the `prefix_eq_galerkin_lhs` field of the
`GalerkinEnergyInterpretation` record. -/

@[simp]
lemma ofGalerkinData_prefixSelfTaxPrice (G : GalerkinStreamData) (n : ℕ) :
    (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixSelfTaxPrice n
      = (G.galerkinSeq n).kineticEnergy G.T
          + 2 * G.nu * (G.galerkinSeq n).cumulative_dissipation G.T := rfl

@[simp]
lemma ofGalerkinData_selfTaxLimitPrice (G : GalerkinStreamData) :
    (LeraySelfTaxProfilePriceStream.ofGalerkinData G).selfTaxLimitPrice
      = G.E_0 := rfl

@[simp]
lemma ofGalerkinData_prefixCrossDefectPrice
    (G : GalerkinStreamData) (n : ℕ) :
    (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixCrossDefectPrice n
      = 0 := rfl

@[simp]
lemma ofGalerkinData_prefixCoherencePrice
    (G : GalerkinStreamData) (n : ℕ) :
    (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixCoherencePrice n
      = 0 := rfl

/-! ## Per-prefix energy bound

The energy estimate field of `GalerkinStreamData` directly gives the
prefix-vs-limit bound `∀ n, prefixSelfTaxPrice n ≤ selfTaxLimitPrice` that
the typed companion's relaxed-output ledger consumes. -/

theorem ofGalerkinData_prefix_le_limit (G : GalerkinStreamData) (n : ℕ) :
    (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixSelfTaxPrice n
      ≤ (LeraySelfTaxProfilePriceStream.ofGalerkinData G).selfTaxLimitPrice := by
  simp only [ofGalerkinData_prefixSelfTaxPrice, ofGalerkinData_selfTaxLimitPrice]
  exact G.energy_estimate n

/-- The prefix self-tax price is non-negative for every `n`. -/
theorem ofGalerkinData_prefixSelfTaxPrice_nonneg
    (G : GalerkinStreamData) (hnu : 0 ≤ G.nu) (n : ℕ) :
    0 ≤ (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixSelfTaxPrice n := by
  simp only [ofGalerkinData_prefixSelfTaxPrice]
  have h1 : 0 ≤ (G.galerkinSeq n).kineticEnergy G.T := G.kineticEnergy_T_nonneg n
  have h2 : 0 ≤ (G.galerkinSeq n).cumulative_dissipation G.T :=
    G.cumulative_dissipation_T_nonneg n
  have h3 : 0 ≤ 2 * G.nu * (G.galerkinSeq n).cumulative_dissipation G.T := by
    have h2nu : 0 ≤ 2 * G.nu := by linarith
    exact mul_nonneg h2nu h2
  linarith

/-! ## Wiring into `GalerkinEnergyInterpretation`

The energy bridge in `ns_trackb_lean_dojo_energy_bridge.lean` consumes a
`GalerkinEnergyInterpretation` record. The concrete stream we just built
satisfies the `prefix_eq_galerkin_lhs` field by construction. The
`limit_eq_initial_energy` field, however, asserts that for every `n` the
stream's limit price equals `(galerkinSeq n).kineticEnergy 0`. For our
construction, the stream's limit price is `G.E_0`, so this only holds when
`E_0` is taken to be a per-`n` invariant of the form
`(galerkinSeq n).kineticEnergy 0` (which is the canonical case where the
initial data is fixed across truncations).

We therefore expose the interpretation builder as taking that final
hypothesis explicitly. -/

/-- Build the `GalerkinEnergyInterpretation` record connecting the stream
produced by `ofGalerkinData` to the original Galerkin sequence.

The caller must supply the `initial_energy_match` hypothesis
`∀ n, G.E_0 = (G.galerkinSeq n).kineticEnergy 0`, which is the standard
"all truncations share the same initial data" assumption from the Galerkin
construction. -/
def galerkinEnergyInterpretation
    (G : GalerkinStreamData)
    (initial_energy_match :
      ∀ n, G.E_0 = (G.galerkinSeq n).kineticEnergy 0) :
    GalerkinEnergyInterpretation
      (LeraySelfTaxProfilePriceStream.ofGalerkinData G)
      G.galerkinSeq G.nu G.T where
  prefix_eq_galerkin_lhs := fun n => by
    simp [ofGalerkinData_prefixSelfTaxPrice]
  limit_eq_initial_energy := fun n => by
    simp [ofGalerkinData_selfTaxLimitPrice]
    exact initial_energy_match n

/-! ## Smoke check

A trivial example: zero velocity field, T = 1, nu = 0, E_0 = 0.
This verifies that the construction is non-vacuous and definitionally
unfolds correctly. -/

/-- The trivial zero `VelocityFieldInterface` for sanity-checking. -/
def zeroVelocityField : VelocityFieldInterface 3 where
  velocity := fun _ _ => 0
  enstrophy_density := fun _ _ => 0
  kineticEnergy := fun _ => 0
  enstrophyIntegral := fun _ => 0
  cumulative_dissipation := fun _ => 0

/-- A trivial Galerkin data instance: every truncation is the zero field. -/
def trivialGalerkinData : GalerkinStreamData where
  galerkinSeq := fun _ => zeroVelocityField
  T := 1
  nu := 0
  E_0 := 0
  energy_estimate := fun _ => by simp [zeroVelocityField]
  kineticEnergy_T_nonneg := fun _ => by simp [zeroVelocityField]
  cumulative_dissipation_T_nonneg := fun _ => by simp [zeroVelocityField]

example :
    (LeraySelfTaxProfilePriceStream.ofGalerkinData trivialGalerkinData).selfTaxLimitPrice = 0 := rfl

example (n : ℕ) :
    (LeraySelfTaxProfilePriceStream.ofGalerkinData trivialGalerkinData).prefixSelfTaxPrice n = 0 := by
  simp [ofGalerkinData_prefixSelfTaxPrice, trivialGalerkinData, zeroVelocityField]

end

end ZtareProofs.NS
