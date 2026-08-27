import Mathlib.Analysis.Calculus.Deriv.Polynomial
import Mathlib.Analysis.ODE.PicardLindelof
import Mathlib.Tactic
import ZtareProofs.FormalBoundedControlledPolynomialEndpoint

/-!
# Uniform bounded-state restart for controlled polynomial trajectories

A continuous globally bounded complex driver and a complex polynomial define
a time-dependent vector field on `Complex`.  On every bounded state ball,
one positive time radius works for every real restart center and every initial
state in that ball.  The radius, Lipschitz constant, Picard rectangle, and
local solution are constructed in the proof.
-/

namespace FormalControlledPolynomialUniformRestart

open Metric Polynomial Set
open scoped NNReal

open FormalBoundedControlledPolynomialEndpoint

/-- The only input data are the driver, its continuity, and its global norm
bound.  No restart or local-solution data are stored. -/
structure ControlledPolynomialDriverCarrier where
  driver : ℝ → ℂ
  driverBound : ℝ≥0
  driver_continuous : Continuous driver
  driver_bound : ∀ t, ‖driver t‖₊ ≤ driverBound

/-- One time radius works for every restart center and every initial state in
the declared norm ball. -/
def ControlledPolynomialUniformRestartOutcome
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier) : Prop :=
  ∀ radius : ℝ≥0,
    ∃ epsilon : ℝ, 0 < epsilon ∧
      ∀ restartTime : ℝ, ∀ state : ℂ, ‖state‖₊ ≤ radius →
        ∃ solution : ℝ → ℂ,
          solution restartTime = state ∧
          ∀ t ∈ Ioo (restartTime - epsilon) (restartTime + epsilon),
            HasDerivAt solution
              (carrier.driver t * p.eval (solution t)) t

/-- Continuous bounded controlled-polynomial fields admit uniform restarts on
every bounded state ball. -/
theorem ControlledPolynomialDriverCarrier.uniformRestartOutcome
    (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier) :
    ControlledPolynomialUniformRestartOutcome p carrier := by
  intro radius
  let stateRadius : ℝ≥0 := radius + 1
  let polynomialLipschitz : ℝ≥0 :=
    polynomialNNNormBound p.derivative stateRadius
  have hpolynomialLipschitz : LipschitzOnWith polynomialLipschitz
      (fun z : ℂ ↦ p.eval z) (closedBall 0 (stateRadius : ℝ)) := by
    apply (convex_closedBall (0 : ℂ) (stateRadius : ℝ)).lipschitzOnWith_of_nnnorm_deriv_le
    · intro z hz
      exact (p.hasDerivAt z).differentiableAt
    · intro z hz
      rw [(p.hasDerivAt z).deriv]
      exact eval_nnnorm_le_polynomialNNNormBound
        p.derivative z stateRadius
        (by exact_mod_cast (mem_closedBall_zero_iff.mp hz))
  let fieldBound : ℝ≥0 :=
    carrier.driverBound * polynomialNNNormBound p stateRadius
  let epsilon : ℝ := ((fieldBound : ℝ) + 1)⁻¹ / 2
  have hepsilon : 0 < epsilon := by
    dsimp [epsilon]
    positivity
  refine ⟨epsilon, hepsilon, ?_⟩
  intro restartTime state hstate
  have hrestartTime :
      restartTime ∈ Icc (restartTime - epsilon)
        (restartTime + epsilon) := by
    constructor <;> linarith
  let restartCenter : Icc (restartTime - epsilon)
      (restartTime + epsilon) := ⟨restartTime, hrestartTime⟩
  have hpicard : IsPicardLindelof
      (fun t : ℝ ↦ fun z : ℂ ↦ carrier.driver t * p.eval z)
      restartCenter (0 : ℂ) stateRadius radius fieldBound
      (carrier.driverBound * polynomialLipschitz) := by
    refine
      { lipschitzOnWith := ?_
        continuousOn := ?_
        norm_le := ?_
        mul_max_le := ?_ }
    · intro t ht
      have hscaled := (lipschitzWith_smul (carrier.driver t)).comp_lipschitzOnWith
        hpolynomialLipschitz
      have hconstant :
          ‖carrier.driver t‖₊ * polynomialLipschitz ≤
            carrier.driverBound * polynomialLipschitz :=
        mul_le_mul_right' (carrier.driver_bound t) polynomialLipschitz
      simpa only [Function.comp_apply, smul_eq_mul] using
        hscaled.weaken hconstant
    · intro state hstate
      exact (carrier.driver_continuous.mul continuous_const).continuousOn
    · intro t ht state hstate
      have hpolynomial :
          ‖p.eval state‖₊ ≤ polynomialNNNormBound p stateRadius :=
        eval_nnnorm_le_polynomialNNNormBound p state stateRadius
          (by
            exact_mod_cast (mem_closedBall_zero_iff.mp hstate))
      rw [norm_mul, ← coe_nnnorm, ← coe_nnnorm]
      change
        (↑(‖carrier.driver t‖₊ * ‖p.eval state‖₊) : ℝ) ≤
          ↑(carrier.driverBound * polynomialNNNormBound p stateRadius)
      exact_mod_cast (mul_le_mul' (carrier.driver_bound t) hpolynomial)
    · have hfieldRatio :
          (fieldBound : ℝ) / ((fieldBound : ℝ) + 1) ≤ 1 := by
        rw [div_le_one (by positivity : (0 : ℝ) < (fieldBound : ℝ) + 1)]
        linarith
      dsimp [restartCenter]
      simp only [add_sub_cancel_left, sub_sub_cancel, max_self]
      dsimp [epsilon, stateRadius]
      norm_num
      calc
        (fieldBound : ℝ) * (((fieldBound : ℝ) + 1)⁻¹ / 2) =
            ((fieldBound : ℝ) / ((fieldBound : ℝ) + 1)) / 2 := by
              simp only [div_eq_mul_inv, mul_assoc]
        _ ≤ 1 := by linarith
  have hstateClosedBall : state ∈ closedBall (0 : ℂ) (radius : ℝ) := by
    rw [mem_closedBall_zero_iff, ← coe_nnnorm, NNReal.coe_le_coe]
    exact hstate
  obtain ⟨solution, hsolutionInitial, hsolutionODE⟩ :=
    hpicard.exists_eq_forall_mem_Icc_hasDerivWithinAt hstateClosedBall
  refine ⟨solution, hsolutionInitial, ?_⟩
  intro t ht
  exact (hsolutionODE t (Ioo_subset_Icc_self ht)).hasDerivAt
    (Icc_mem_nhds ht.1 ht.2)

/-- Aggregated uniform controlled-polynomial restart terminal. -/
theorem controlled_polynomial_uniform_restart_terminal_certificate :
    ∀ (p : ℂ[X]) (carrier : ControlledPolynomialDriverCarrier),
      ControlledPolynomialUniformRestartOutcome p carrier := by
  intro p carrier
  exact carrier.uniformRestartOutcome p

end FormalControlledPolynomialUniformRestart
