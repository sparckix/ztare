import Mathlib.Analysis.Calculus.MeanValue
import Mathlib.Topology.UniformSpace.Cauchy
import Mathlib.Tactic

/-!
# Finite endpoint limits from bounded derivative

A trajectory on a finite half-open real interval whose derivative is
uniformly bounded is Lipschitz there.  The left-endpoint filter is Cauchy, so
completeness of the codomain constructs a finite endpoint limit.
-/

namespace FormalBoundedDerivativeEndpointLimit

open Filter Set
open scoped NNReal Topology

/-- Data for a trajectory with uniformly bounded speed on a finite half-open
interval.  No endpoint value, compactness witness, or limit is stored. -/
structure BoundedDerivativeEndpointCarrier
    (E : Type*) [NormedAddCommGroup E] [NormedSpace ℝ E] where
  left : ℝ
  endpoint : ℝ
  trajectory : ℝ → E
  speedBound : ℝ≥0
  left_lt_endpoint : left < endpoint
  differentiable : ∀ t ∈ Ioo left endpoint,
    DifferentiableAt ℝ trajectory t
  derivative_bound : ∀ t ∈ Ioo left endpoint,
    ‖deriv trajectory t‖₊ ≤ speedBound

/-- Exact endpoint-compactness output. -/
def BoundedDerivativeEndpointOutcome
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (carrier : BoundedDerivativeEndpointCarrier E) : Prop :=
  ∃ state : E,
    Tendsto carrier.trajectory (𝓝[<] carrier.endpoint) (𝓝 state)

/-- Uniformly bounded speed on a finite half-open interval forces a finite
one-sided endpoint limit in every complete normed codomain. -/
theorem BoundedDerivativeEndpointCarrier.boundedDerivativeEndpointOutcome
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    [CompleteSpace E]
    (carrier : BoundedDerivativeEndpointCarrier E) :
    BoundedDerivativeEndpointOutcome carrier := by
  have hLipschitz :
      LipschitzOnWith carrier.speedBound carrier.trajectory
        (Ioo carrier.left carrier.endpoint) :=
    Convex.lipschitzOnWith_of_nnnorm_deriv_le
      carrier.differentiable carrier.derivative_bound
        (convex_Ioo carrier.left carrier.endpoint)
  have hEndpointCauchy : Cauchy (𝓝[<] carrier.endpoint) :=
    cauchy_nhds.mono nhdsWithin_le_nhds
  have hInterval :
      𝓝[<] carrier.endpoint ≤ 𝓟 (Ioo carrier.left carrier.endpoint) := by
    exact le_principal_iff.mpr
      (Ioo_mem_nhdsLT carrier.left_lt_endpoint)
  have hTrajectoryCauchy :
      Cauchy (map carrier.trajectory (𝓝[<] carrier.endpoint)) :=
    hEndpointCauchy.map_of_le hLipschitz.uniformContinuousOn hInterval
  exact cauchy_map_iff_exists_tendsto.mp hTrajectoryCauchy

/-- Aggregated bounded-derivative endpoint terminal. -/
theorem bounded_derivative_endpoint_limit_terminal_certificate :
    ∀ (E : Type*) (_ : NormedAddCommGroup E) (_ : NormedSpace ℝ E)
      (_ : CompleteSpace E)
      (carrier : BoundedDerivativeEndpointCarrier E),
      BoundedDerivativeEndpointOutcome carrier := by
  intro E _ _ _ carrier
  exact carrier.boundedDerivativeEndpointOutcome

end FormalBoundedDerivativeEndpointLimit
