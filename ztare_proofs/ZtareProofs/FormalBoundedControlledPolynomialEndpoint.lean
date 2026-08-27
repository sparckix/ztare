import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Tactic
import ZtareProofs.FormalBoundedDerivativeEndpointLimit

/-!
# Endpoint compactness for bounded controlled-polynomial trajectories

Uniform bounds on the driver and state of a complex trajectory satisfying
`y' = driver * p(y)` construct an explicit speed bound.  The generic
bounded-derivative endpoint theorem then constructs a finite one-sided limit.
-/

namespace FormalBoundedControlledPolynomialEndpoint

open Filter FormalBoundedDerivativeEndpointLimit Polynomial Set
open scoped BigOperators NNReal Topology

/-- Explicit coefficient bound for polynomial evaluation on a norm ball. -/
noncomputable def polynomialNNNormBound (p : ℂ[X])
    (radius : ℝ≥0) : ℝ≥0 :=
  ∑ i ∈ p.support, ‖p.coeff i‖₊ * radius ^ i

/-- The explicit coefficient sum bounds polynomial evaluation on the stated
norm ball. -/
theorem eval_nnnorm_le_polynomialNNNormBound
    (p : ℂ[X]) (z : ℂ) (radius : ℝ≥0)
    (hz : ‖z‖₊ ≤ radius) :
    ‖p.eval z‖₊ ≤ polynomialNNNormBound p radius := by
  rw [p.eval_eq_sum]
  calc
    ‖p.sum fun i coefficient ↦ coefficient * z ^ i‖₊
        ≤ ∑ i ∈ p.support, ‖p.coeff i * z ^ i‖₊ := by
          exact nnnorm_sum_le _ _
    _ = ∑ i ∈ p.support, ‖p.coeff i‖₊ * ‖z‖₊ ^ i := by
      apply Finset.sum_congr rfl
      intro i hi
      simp only [nnnorm_mul, nnnorm_pow]
    _ ≤ ∑ i ∈ p.support, ‖p.coeff i‖₊ * radius ^ i := by
      apply Finset.sum_le_sum
      intro i hi
      simpa [mul_comm] using
        mul_le_mul_right (pow_le_pow_left' hz i) ‖p.coeff i‖₊

/-- A controlled-polynomial trajectory with bounded driver and state.  No
speed bound or endpoint limit is stored. -/
structure BoundedControlledPolynomialCarrier (p : ℂ[X]) where
  left : ℝ
  endpoint : ℝ
  driver : ℝ → ℂ
  trajectory : ℝ → ℂ
  driverBound : ℝ≥0
  stateBound : ℝ≥0
  left_lt_endpoint : left < endpoint
  trajectory_ode : ∀ t ∈ Ioo left endpoint,
    HasDerivAt trajectory (driver t * p.eval (trajectory t)) t
  driver_bound : ∀ t ∈ Ioo left endpoint,
    ‖driver t‖₊ ≤ driverBound
  state_bound : ∀ t ∈ Ioo left endpoint,
    ‖trajectory t‖₊ ≤ stateBound

/-- Exact derived-speed and endpoint-limit output. -/
def BoundedControlledPolynomialOutcome {p : ℂ[X]}
    (carrier : BoundedControlledPolynomialCarrier p) : Prop :=
  (∀ t ∈ Ioo carrier.left carrier.endpoint,
      ‖deriv carrier.trajectory t‖₊ ≤
        carrier.driverBound * polynomialNNNormBound p carrier.stateBound) ∧
    ∃ state : ℂ,
      Tendsto carrier.trajectory (𝓝[<] carrier.endpoint) (𝓝 state)

/-- Bounded controlled-polynomial motion has explicitly bounded speed and a
finite one-sided endpoint limit. -/
theorem BoundedControlledPolynomialCarrier.boundedControlledPolynomialOutcome
    {p : ℂ[X]} (carrier : BoundedControlledPolynomialCarrier p) :
    BoundedControlledPolynomialOutcome carrier := by
  have hspeed : ∀ t ∈ Ioo carrier.left carrier.endpoint,
      ‖deriv carrier.trajectory t‖₊ ≤
        carrier.driverBound * polynomialNNNormBound p carrier.stateBound := by
    intro t ht
    have hODE := carrier.trajectory_ode t ht
    rw [hODE.deriv, nnnorm_mul]
    exact mul_le_mul'
      (carrier.driver_bound t ht)
      (eval_nnnorm_le_polynomialNNNormBound
        p (carrier.trajectory t) carrier.stateBound
        (carrier.state_bound t ht))
  let boundedCarrier : BoundedDerivativeEndpointCarrier ℂ :=
    {
      left := carrier.left
      endpoint := carrier.endpoint
      trajectory := carrier.trajectory
      speedBound :=
        carrier.driverBound * polynomialNNNormBound p carrier.stateBound
      left_lt_endpoint := carrier.left_lt_endpoint
      differentiable := fun t ht ↦
        (carrier.trajectory_ode t ht).differentiableAt
      derivative_bound := hspeed
    }
  have hlimit := boundedCarrier.boundedDerivativeEndpointOutcome
  refine ⟨hspeed, ?_⟩
  simpa [
    BoundedDerivativeEndpointOutcome,
    boundedCarrier,
  ] using hlimit

/-- Aggregated bounded controlled-polynomial endpoint terminal. -/
theorem bounded_controlled_polynomial_endpoint_terminal_certificate :
    ∀ (p : ℂ[X]) (carrier : BoundedControlledPolynomialCarrier p),
      BoundedControlledPolynomialOutcome carrier := by
  intro p carrier
  exact carrier.boundedControlledPolynomialOutcome

end FormalBoundedControlledPolynomialEndpoint
