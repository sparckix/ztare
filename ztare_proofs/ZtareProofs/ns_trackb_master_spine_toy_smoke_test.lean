/-
# Master spine smoke test — composes `GalerkinTypedCompanionBundle` for a zero toy

ARCHITECTURAL "Hello World" for the typed-companion master spine in
`ns_trackb_leray_hopf_master_spine.lean`.  We instantiate the bundle on
the simplest possible substrate (zero everywhere) and then APPLY
`leray_hopf_solution_from_galerkin_typed_companions` to produce a
concrete `AbstractLerayHopfWitness` term.

The point is COMPOSITION:
- All five typed-companion structures are inhabited.
- The five clause bridges in the master spine actually compose against
  this concrete bundle.
- No hidden type-class / universe issue blocks instantiation.

The analytical content is trivially zero on every clause.  This is the
correct calibration: the smoke test only checks the typed-companion
PLUMBING.  It does not pretend to be a Navier-Stokes proof.

We use a fully-zero `LeraySelfTaxProfilePriceStream` paired with a
matching zero `LeraySelfTaxMeasureValuedOutputLimitSource` so that the
constant-zero observable on the comap-atTop filter trivially has
liminf 0 (matching every relaxed output price).  All velocity-field
proxies are identically zero.

Producing the witness via the master theorem at the end of this file
proves that the FIVE clause bridges compose end-to-end against this
concrete bundle.
-/

import Mathlib.Tactic
import ZtareProofs.ns_trackb_leray_hopf_master_spine
import ZtareProofs.ns_trackb_toy_substrate_instance

namespace ZtareProofs.NS

noncomputable section

/-! ## Zero defect source / output-limit source / liminf bound data

We reuse the stream-level zero stream `zeroLeraySelfTaxProfilePriceStream`
from `ns_profile_lsc_self_tax_obligation.lean` and instantiate the
matching measure-valued output-limit source with all relaxed prices `= 0`. -/

/-- Zero defect source over the zero stream. -/
def smokeZeroDefectSource :
    LeraySelfTaxMeasureValuedDefectSource zeroLeraySelfTaxProfilePriceStream where
  defectState := Bool
  reynoldsDefect := false
  concentrationDefect := true
  defectPrice := fun _ _ => 0
  defect_carrier_declared_before_payoff := trivial
  reynolds_defect_reified_in_relaxed_limit_price := True
  reynolds_defect_reified_receipt := trivial
  concentration_measure_reified_in_relaxed_limit_price := True
  concentration_measure_reified_receipt := trivial
  defect_price_nonnegative := fun _ _ => le_refl 0

/-- Zero output-limit source: every relaxed price is `0`, every
prefix-le-relaxed inequality is `0 ≤ 0`. -/
def smokeZeroOutputLimitSource :
    LeraySelfTaxMeasureValuedOutputLimitSource zeroLeraySelfTaxProfilePriceStream where
  measure_defect_source := smokeZeroDefectSource
  component_stream_fixed_before_payoff := trivial
  prefix_components_declared_before_payoff := trivial
  limit_components_declared_before_payoff := trivial
  no_smooth_limit_price_substitution := trivial
  leray_projection_l2_bounded := True
  leray_projection_l2_bounded_receipt := trivial
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology := True
  nonlinear_output_converges_weakly_l2_or_strong_graph_topology_receipt := trivial
  strong_l4_w14_or_hs_source_topology_declared := True
  strong_l4_w14_or_hs_source_topology_declared_receipt := trivial
  cross_and_coherence_outputs_use_same_topology := True
  cross_and_coherence_outputs_use_same_topology_receipt := trivial
  selfTaxRelaxedOutputPrice := 0
  crossDefectRelaxedOutputPrice := 0
  coherenceRelaxedOutputPrice := 0
  self_tax_relaxed_output_includes_measure_defects := by
    show selfTaxDefectFloor _ ≤ (0 : Real)
    unfold selfTaxDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    simp [smokeZeroDefectSource]
  cross_defect_relaxed_output_includes_measure_defects := by
    show crossDefectFloor _ ≤ (0 : Real)
    unfold crossDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    simp [smokeZeroDefectSource]
  coherence_relaxed_output_includes_measure_defects := by
    show coherenceDefectFloor _ ≤ (0 : Real)
    unfold coherenceDefectFloor relaxed_output_defect_ledger_of_measure_valued_source
    simp [smokeZeroDefectSource]
  prefix_self_tax_le_relaxed_output := fun _ => le_refl 0
  prefix_cross_defect_le_relaxed_output := fun _ => le_refl 0
  prefix_coherence_le_relaxed_output := fun _ => le_refl 0
  self_tax_relaxed_output_le_limit := le_refl 0
  cross_defect_relaxed_output_le_limit := le_refl 0
  coherence_relaxed_output_le_limit := le_refl 0

/-- The constant-zero sequence converges to zero on `comap id atTop`. -/
private theorem smoke_zero_tendsto :
    Filter.Tendsto (fun _ : ℕ => (0 : Real))
      (Filter.comap (id : ℕ → ℕ) Filter.atTop) (nhds 0) := by
  rw [show Filter.comap (id : ℕ → ℕ) Filter.atTop = Filter.atTop
        from Filter.comap_id]
  exact tendsto_const_nhds

/-- NeBot for the smoke filter (reused from the toy substrate file's
instance, but we restate explicitly here so that this file compiles even
if loaded standalone). -/
instance : (Filter.comap (id : ℕ → ℕ) Filter.atTop).NeBot := by
  rw [show Filter.comap (id : ℕ → ℕ) Filter.atTop = Filter.atTop
        from Filter.comap_id]
  infer_instance

/-- Zero liminf bound data, produced via `fromTendsto`. -/
def smokeZeroLiminfBoundData :
    LeraySelfTaxRelaxedOutputPriceLiminfBoundData
      smokeZeroOutputLimitSource (id : ℕ → ℕ)
      (fun a => zeroLeraySelfTaxProfilePriceStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.selfTax a)
      (fun a => zeroLeraySelfTaxProfilePriceStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.crossDefect a)
      (fun a => zeroLeraySelfTaxProfilePriceStream.prefixPriceForComponent
        LeraySelfTaxPriceComponent.coherence a) :=
  LeraySelfTaxRelaxedOutputPriceLiminfBoundData.fromTendsto
    smokeZeroOutputLimitSource id
    (by
      -- After unfolding `prefixPriceForComponent` on the zero stream the
      -- function inside the Tendsto is the constant-zero sequence and
      -- the relaxed price is `0`, so `simp` closes the goal directly.
      simp [LeraySelfTaxProfilePriceStream.prefixPriceForComponent,
            zeroLeraySelfTaxProfilePriceStream, smokeZeroOutputLimitSource])
    (by
      simp [LeraySelfTaxProfilePriceStream.prefixPriceForComponent,
            zeroLeraySelfTaxProfilePriceStream, smokeZeroOutputLimitSource])
    (by
      simp [LeraySelfTaxProfilePriceStream.prefixPriceForComponent,
            zeroLeraySelfTaxProfilePriceStream, smokeZeroOutputLimitSource])

/-! ## Trivial velocity-field interfaces -/

/-- Zero velocity-field proxy for the energy / divergence-test clauses. -/
def smokeZeroField3 : VelocityFieldInterface 3 where
  velocity := fun _ _ => 0
  enstrophy_density := fun _ _ => 0
  kineticEnergy := fun _ => 0
  enstrophyIntegral := fun _ => 0
  cumulative_dissipation := fun _ => 0

/-- Zero divergence-test proxy. -/
def smokeZeroDiv (n : ℕ) : VelocityFieldDivInterface n where
  divergenceTest := fun _ _ => 0

/-- Zero momentum proxy with `TestFn := Unit`. -/
def smokeZeroMom : VelocityFieldMomentumInterface Unit where
  timePairing      := fun _ _ => 0
  nonlinearPairing := fun _ _ => 0
  viscousPairing   := fun _ _ => 0
  pressurePairing  := fun _ _ => 0
  forcingPairing   := fun _ _ => 0
  timeIntegrate    := fun _ => 0
  momentumPairing  := fun _ => 0

/-! ## Trivial initial-pairing functional and weak-IC typed companion -/

def smokeInitialFunctional : InitialPairingFunctional.{0} where
  TestSpace := Unit
  IsTest := fun _ => True
  initialPairing := fun _ _ => 0
  initialDataPairing := fun _ => 0

def smokeInitialCondData :
    WeakInitialConditionData smokeInitialFunctional
      (fun _ : ℕ => smokeZeroField3) smokeZeroField3 where
  pairing_to_initialData := by
    intro _ _
    -- both sides are constantly 0
    simp [smokeInitialFunctional]
  pairing_to_limit := by
    intro _ _
    simp [smokeInitialFunctional]

/-! ## Trivial velocity-regularity data -/

def smokeRegularityData : VelocityRegularityData where
  n := 3
  T := 1
  squaredVelocity := fun _ _ _ => 0
  squaredGradient := fun _ _ _ => 0
  limitSquaredVelocity := fun _ _ => 0
  limitSquaredGradient := fun _ _ => 0
  M_kin := 0
  M_ens := 0

def smokeRegularityHyp : smokeRegularityData.Hypotheses where
  T_pos := by show (0 : ℝ) < 1; norm_num
  limit_squaredVelocity_nonneg := by
    intro _ _
    exact MeasureTheory.ae_of_all _ (fun _ => le_refl 0)
  limit_squaredGradient_nonneg := by
    intro _ _
    exact MeasureTheory.ae_of_all _ (fun _ => le_refl 0)
  M_kin_finite := by
    show (ENNReal.ofReal (0 : ℝ)) ≠ ⊤
    simp
  M_ens_finite := by
    show (ENNReal.ofReal (0 : ℝ)) ≠ ⊤
    simp
  lintegral_limit_velocity_le := by
    intro _ _
    simp [smokeRegularityData]
  lintegral_limit_gradient_le := by
    intro _ _
    simp [smokeRegularityData]

/-! ## Trivial weak-incompressibility typed companion -/

def smokeDivData : WeakIncompressibilityData 3 where
  galerkinSeq := fun _ => smokeZeroDiv 3
  uInf := smokeZeroDiv 3
  per_n_divergence_free := by intro _ _ _; rfl
  weak_convergence := by
    intro _ _
    show Filter.Tendsto (fun _ : ℕ => (0 : ℝ)) Filter.atTop (nhds 0)
    exact tendsto_const_nhds

/-! ## Trivial weak-momentum-equation typed companion

The smoke test instantiates the three admissibility predicates with
the trivial `fun _ => True` choices.  This is an EXPLICIT, named
choice — it remains valid for the toy stand-in, but at the concrete
NS instantiation site the predicates are pinned to the lean-dojo
`ContDiff` / compact-support / divergence-free clauses. -/

/-- Toy smoothness predicate: `True` for any `Unit` test function. -/
def smokeTestFnSmooth : Unit → Prop := fun _ => True
/-- Toy compact-support predicate: `True` for any `Unit` test function. -/
def smokeTestFnCompactSupport : Unit → Prop := fun _ => True
/-- Toy divergence-free predicate: `True` for any `Unit` test function. -/
def smokeTestFnDivFree : Unit → Prop := fun _ => True

def smokeMomCompanion (φ : Unit)
    (_ : TestFnAdmissible smokeTestFnSmooth smokeTestFnCompactSupport
            smokeTestFnDivFree φ) :
    @WeakMomentumEquationData Unit smokeTestFnSmooth
      smokeTestFnCompactSupport smokeTestFnDivFree
      (fun _ : ℕ => smokeZeroMom) smokeZeroMom φ where
  test_admissible := ⟨trivial, trivial, trivial⟩
  galerkin_weak_identity := by intro _; rfl
  galerkin_decomposes := by
    intro _
    show (0 : ℝ) = 0
    rfl
  limit_decomposes := by
    show (0 : ℝ) = 0
    rfl
  limit_timeIntegrate_linear := by
    intros _ _ _ _ _
    show (0 : ℝ) = -0 - 0 + 0 - 0 + 0
    ring
  seq_timeIntegrate_linear := by
    intros _ _ _ _ _ _
    show (0 : ℝ) = -0 - 0 + 0 - 0 + 0
    ring
  time_pairing_conv := by
    show Filter.Tendsto (fun _ : ℕ => (0 : ℝ)) Filter.atTop (nhds 0)
    exact tendsto_const_nhds
  nonlinear_pairing_conv := by
    show Filter.Tendsto (fun _ : ℕ => (0 : ℝ)) Filter.atTop (nhds 0)
    exact tendsto_const_nhds
  viscous_pairing_conv := by
    show Filter.Tendsto (fun _ : ℕ => (0 : ℝ)) Filter.atTop (nhds 0)
    exact tendsto_const_nhds
  pressure_pairing_conv := by
    show Filter.Tendsto (fun _ : ℕ => (0 : ℝ)) Filter.atTop (nhds 0)
    exact tendsto_const_nhds
  forcing_pairing_conv := by
    show Filter.Tendsto (fun _ : ℕ => (0 : ℝ)) Filter.atTop (nhds 0)
    exact tendsto_const_nhds

/-! ## Galerkin-energy interpretation, LSC, initial-energy match

All identities collapse to `0 = 0` because both the stream and the
field are zero. -/

def smokeEnergyInterp :
    GalerkinEnergyInterpretation zeroLeraySelfTaxProfilePriceStream
      (fun _ : ℕ => smokeZeroField3) 0 1 where
  prefix_eq_galerkin_lhs := by
    intro _
    show (0 : ℝ) = 0 + 2 * 0 * 0
    ring
  limit_eq_initial_energy := by
    intro _
    show (0 : ℝ) = 0
    rfl

def smokeEnergyLSC :
    GalerkinEnergyLSC (fun _ : ℕ => smokeZeroField3) smokeZeroField3 0 1 := by
  -- Goal: KE(uInf, T) + 2ν * cum_diss(uInf, T) ≤ liminf [KE(u_n, T) + 2ν * cum_diss(u_n, T)]
  -- Both sides reduce to 0 ≤ liminf (fun _ => 0) = 0.
  show (0 : ℝ) + 2 * 0 * 0 ≤
    Filter.liminf (fun _ : ℕ => (0 : ℝ) + 2 * 0 * 0) Filter.atTop
  have h : Filter.liminf (fun _ : ℕ => (0 : ℝ) + 2 * 0 * 0) Filter.atTop = 0 := by
    have : (fun _ : ℕ => (0 : ℝ) + 2 * 0 * 0) = fun _ => (0 : ℝ) := by
      funext _; ring
    rw [this, Filter.liminf_const]
  rw [h]
  norm_num

def smokeInitEnergyMatch :
    InitialEnergyMatch (fun _ : ℕ => smokeZeroField3) smokeZeroField3 := by
  intro _
  show (0 : ℝ) = 0
  rfl

/-! ## All-times energy inequality (direct)

The bundle accepts a per-`t` energy inequality at the limit.  Since both
fields are zero, every clause reduces to `0 + 0 ≤ 0`. -/

theorem smoke_energy_inequality_all_times :
    ∀ t ∈ Set.Icc (0 : ℝ) 1,
      smokeZeroField3.kineticEnergy t
        + 2 * (0 : ℝ) * smokeZeroField3.cumulative_dissipation t
        ≤ smokeZeroField3.kineticEnergy 0 := by
  intro _ _
  show (0 : ℝ) + 2 * 0 * 0 ≤ 0
  norm_num

/-! ## Assemble the bundle -/

/-- The fully-zero `GalerkinTypedCompanionBundle`.  Every analytical
quantity is `0`; every Tendsto is the constant-zero sequence; every
inequality is `0 ≤ 0` or `0 = 0`. -/
def smokeBundle : GalerkinTypedCompanionBundle where
  dim := 3
  T := 1
  nu := 0
  nu_nonneg := le_refl 0
  T_pos := by norm_num
  galerkinEnergy := fun _ => smokeZeroField3
  uInfEnergy := smokeZeroField3
  initialFunctional := smokeInitialFunctional
  galerkinInit := fun _ => smokeZeroField3
  uInfInit := smokeZeroField3
  regularityData := smokeRegularityData
  divInterfaceSeq := fun _ => smokeZeroDiv 3
  uInfDiv := smokeZeroDiv 3
  TestFn := Unit
  TestFnSmooth := smokeTestFnSmooth
  TestFnCompactSupport := smokeTestFnCompactSupport
  TestFnDivFree := smokeTestFnDivFree
  galerkinMom := fun _ => smokeZeroMom
  uInfMom := smokeZeroMom
  energyStream := zeroLeraySelfTaxProfilePriceStream
  energyMeasureSource := smokeZeroOutputLimitSource
  energyNeBot := inferInstance
  energyBoundData := smokeZeroLiminfBoundData
  energyInterp := smokeEnergyInterp
  energyLSC := smokeEnergyLSC
  energyInitMatch := smokeInitEnergyMatch
  energy_inequality_all_times := smoke_energy_inequality_all_times
  initialCondData := smokeInitialCondData
  regularityHyp := smokeRegularityHyp
  divData := smokeDivData
  divData_seq_eq := rfl
  divData_uInf_eq := rfl
  momCompanion := smokeMomCompanion

/-! ## Apply the master theorem

`leray_hopf_solution_from_galerkin_typed_companions smokeBundle` is the
end-to-end smoke-test artefact.  Its TYPE is `AbstractLerayHopfWitness
smokeBundle`, which is the proxy analogue of
`NavierStokes.LerayHopfSolution`. -/

/-- Concrete `AbstractLerayHopfWitness` produced by the master theorem. -/
def smokeWitness : AbstractLerayHopfWitness smokeBundle :=
  leray_hopf_solution_from_galerkin_typed_companions smokeBundle

/-! ## Non-triviality checks

We pull out each of the five witness fields to verify it has the
correct, NON-trivial Prop shape (i.e. is not `True`).  This is the
sanity check that the master spine's witness type really is the
five-clause record, not an opaque alias. -/

example :
    ∀ t ∈ Set.Icc (0 : ℝ) smokeBundle.T,
      smokeBundle.uInfEnergy.kineticEnergy t
        + 2 * smokeBundle.nu * smokeBundle.uInfEnergy.cumulative_dissipation t
        ≤ smokeBundle.uInfEnergy.kineticEnergy 0 :=
  smokeWitness.energy_inequality

example :
    ∀ φ : smokeBundle.initialFunctional.TestSpace,
      smokeBundle.initialFunctional.IsTest φ →
        smokeBundle.initialFunctional.initialPairing smokeBundle.uInfInit φ
          = smokeBundle.initialFunctional.initialDataPairing φ :=
  smokeWitness.weak_initial_condition

example :
    ∀ t ∈ Set.Icc (0 : ℝ) smokeBundle.regularityData.T, ∀ ψ : ℝ → ℝ,
      smokeBundle.uInfDiv.divergenceTest ψ t = 0 := by
  intro t ht ψ
  -- The master witness's weak_incompressible field uses `B.T`, not
  -- `B.regularityData.T`; both are 1 here so we just feed the same
  -- interval witness through.
  exact smokeWitness.weak_incompressible t (by simpa using ht) ψ

example :
    ∀ φ : smokeBundle.TestFn,
      TestFnAdmissible smokeBundle.TestFnSmooth smokeBundle.TestFnCompactSupport
        smokeBundle.TestFnDivFree φ →
      smokeBundle.uInfMom.momentumPairing φ = 0 :=
  smokeWitness.weak_momentum_equation

end

end ZtareProofs.NS
