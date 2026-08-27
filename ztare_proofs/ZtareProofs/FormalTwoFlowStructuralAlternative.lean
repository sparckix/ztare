import ZtareProofs.FormalAnalyticFiniteRoute
import ZtareProofs.FormalPolynomialFlowAtInfinity
import ZtareProofs.FormalProportionalFlowReduction

/-!
# Route-indexed structural alternative for two polynomial flows

This file assembles the finite-chart, infinity-chart, and proportional-flow
mechanisms. The route is represented by typed evidence. In particular, the
theorem does not claim that every analytic continuation of an arbitrary
factorization supplies one of these constructors; that global realization is
a separate proposition.
-/

namespace FormalTwoFlowStructuralAlternative

open Polynomial PowerSeries
open FormalAnalyticFiniteRoute
open FormalPolynomialFlowAtInfinity
open FormalProportionalFlowReduction
open FormalSubstitutionFlow

universe u

/-- The two representations used by the structural assembly. Analytic
factor germs own finite-chart continuation, while formal endpoints own the
substitution orientation in the proportional branch. -/
structure TwoFlowFrame (𝕜 : Type u) where
  basepoint : ℂ
  inner : ℂ → ℂ
  outer : ℂ → ℂ
  firstEndpoint : 𝕜⟦X⟧
  secondEndpoint : 𝕜⟦X⟧

/-- Exact endpoint data needed after normalized generators have been proved
equal. This is the output of the separate proportional-trajectory
identification theorem, not a route tag. -/
structure ProportionalEndpointIdentification
    {𝕜 : Type u} [Field 𝕜] (frame : TwoFlowFrame 𝕜) where
  flow : SubstitutionFlow 𝕜
  scale : 𝕜
  first_eq : frame.firstEndpoint = flow.endpoint 1
  second_eq : frame.secondEndpoint = flow.endpoint scale

/-- Inspectable route evidence consumed by the assembly.

The infinity constructor contains only the normalized polynomial and
time-coordinate data from which equal degree and the coefficient-collision
alternative are derived. Endpoint identification may be used only after
the normalized generators are proved equal. -/
inductive TwoFlowRouteEvidence
    {𝕜 : Type u} [Field 𝕜] [CharZero 𝕜]
    (frame : TwoFlowFrame 𝕜) : Type (u + 1)
  | finite
      (inner_analytic : AnalyticAt ℂ frame.inner frame.basepoint)
      (outer_analytic :
        AnalyticAt ℂ frame.outer (frame.inner frame.basepoint))
  | infinity
      (firstGenerator secondGenerator : 𝕜[X])
      (firstDegree secondDegree : ℕ)
      (transition : 𝕜⟦X⟧)
      (first_degree_at_least_two : 2 ≤ firstDegree)
      (second_degree_at_least_two : 2 ≤ secondDegree)
      (first_monic :
        Polynomial.IsMonicOfDegree firstGenerator firstDegree)
      (second_monic :
        Polynomial.IsMonicOfDegree secondGenerator secondDegree)
      (first_constant_zero : firstGenerator.coeff 0 = 0)
      (second_constant_zero : secondGenerator.coeff 0 = 0)
      (first_linear_zero : firstGenerator.coeff 1 = 0)
      (second_linear_zero : secondGenerator.coeff 1 = 0)
      (transition_constant_zero : constantCoeff transition = 0)
      (transition_linear_nonzero : coeff 1 transition ≠ 0)
      (time_coordinate_transition :
        normalizedTimeCoordinate secondDegree
            (reciprocalDenominator secondDegree secondGenerator) =
          transition.subst
            (normalizedTimeCoordinate firstDegree
              (reciprocalDenominator firstDegree firstGenerator)))
      (proportional_endpoint_identification :
        firstGenerator = secondGenerator →
          ProportionalEndpointIdentification frame)

/-- The three mechanism-level outcomes. The infinity-collision constructor
retains the exact all-order series order, not only its interval consequence. -/
inductive TwoFlowStructuralOutcome
    {𝕜 : Type u} [Field 𝕜] (frame : TwoFlowFrame 𝕜) : Prop
  | finite
      (composition_analytic :
        AnalyticAt ℂ (frame.outer ∘ frame.inner) frame.basepoint)
  | infinityCollision
      (firstGenerator secondGenerator : 𝕜[X])
      (degree collisionDegree : ℕ)
      (degree_at_least_two : 2 ≤ degree)
      (first_monic : Polynomial.IsMonicOfDegree firstGenerator degree)
      (second_monic : Polynomial.IsMonicOfDegree secondGenerator degree)
      (collision_degree_at_least_two : 2 ≤ collisionDegree)
      (collision_degree_lt : collisionDegree < degree)
      (time_coordinate_collision_order :
        order
            (normalizedTimeCoordinate degree
                (reciprocalDenominator degree firstGenerator) -
              normalizedTimeCoordinate degree
                (reciprocalDenominator degree secondGenerator)) =
          ((2 * degree - collisionDegree - 1 : ℕ) : ℕ∞))
      (transition_exponent_interval :
        1 <
            ((2 * degree - collisionDegree - 1 : ℕ) : ℚ) /
              ((degree - 1 : ℕ) : ℚ) ∧
          ((2 * degree - collisionDegree - 1 : ℕ) : ℚ) /
              ((degree - 1 : ℕ) : ℚ) < 2)
  | proportional
      (flow : SubstitutionFlow 𝕜)
      (scale : 𝕜)
      (composition_eq_reparameterized_time_one :
        frame.firstEndpoint.subst frame.secondEndpoint =
          (flow.reparam (1 + scale)).endpoint 1)

/-- Assemble the exact route mechanisms. Equal degree is proved from the
time-coordinate transition; proportionality is decided only by the complete
normalized coefficient alternative. -/
theorem structuralOutcome_of_routeEvidence
    {𝕜 : Type u} [Field 𝕜] [CharZero 𝕜]
    (frame : TwoFlowFrame 𝕜)
    (route : TwoFlowRouteEvidence frame) :
    TwoFlowStructuralOutcome frame := by
  cases route with
  | finite hinner houter =>
      exact .finite
        (analyticAt_comp_of_finite_factor_germs hinner houter)
  | infinity p q d e transition hd he hp hq hp0 hq0 hp1 hq1
      htransition0 htransition1 htransition hproportional =>
      have hdegrees : d = e :=
        nonzero_linear_transition_forces_equal_degree hd he hp hq
          transition htransition0 htransition1 htransition
      subst e
      rcases monic_tangent_time_coordinate_alternative
          hd hp hq hp0 hq0 hp1 hq1 with hpq | hcollision
      · obtain ⟨flow, scale, hfirst, hsecond⟩ := hproportional hpq
        exact .proportional flow scale
          (identified_endpoints_reduce_to_reparameterized_time_one
            flow scale frame.firstEndpoint frame.secondEndpoint
            hfirst hsecond)
      · obtain ⟨collisionDegree, hcollisionTwo, hcollisionLt,
          hcollisionOrder⟩ := hcollision
        exact .infinityCollision p q d collisionDegree hd hp hq
          hcollisionTwo hcollisionLt hcollisionOrder
          (time_coordinate_collision_exponent_interval
            hd hcollisionTwo hcollisionLt)

/-- Aggregated theorem identity for governed coverage. -/
theorem two_flow_structural_alternative_terminal_certificate :
    ∀ (𝕜 : Type u) [Field 𝕜] [CharZero 𝕜]
      (frame : TwoFlowFrame 𝕜),
      TwoFlowRouteEvidence frame → TwoFlowStructuralOutcome frame := by
  intro 𝕜 _ _ frame
  exact structuralOutcome_of_routeEvidence frame

end FormalTwoFlowStructuralAlternative
