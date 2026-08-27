import ZtareProofs.FormalAnalyticRamifiedFiberProduct
import ZtareProofs.FormalPolynomialFiniteTimeCoordinate
import ZtareProofs.FormalPolynomialInfinityTimeCoordinate

/-!
# Regular finite-to-infinity fiber products for polynomial flows

For an exact degree-`d` polynomial with `d ≥ 2`, the reciprocal infinity
time coordinate has order `d - 1`.  At a regular finite point, the normalized
finite Abel coordinate has order one.  Their analytic fiber product therefore
constructs a finite `(d - 1)`-fold source parameterization whose reciprocal
lift has a simple pole.
-/

namespace FormalPolynomialRegularInfinityFiberProduct

open Filter Polynomial
open scoped Topology

open FormalAnalyticRamifiedFiberProduct
open FormalPolynomialFiniteTimeCoordinate
open FormalPolynomialInfinityTimeCoordinate

/-- The constructed local finite-to-infinity correspondence at a regular
finite point of a polynomial vector field. -/
structure PolynomialRegularInfinityFiberProduct
    (p : ℂ[X]) (degree : ℕ) (center : ℂ) where
  infinityTime : ℂ → ℂ
  finiteTime : ℂ → ℂ
  infinityTime_analytic : AnalyticAt ℂ infinityTime 0
  infinityTime_zero : infinityTime 0 = 0
  infinityTime_derivative :
    ∀ᶠ z in nhds 0,
      HasDerivAt infinityTime (reciprocalTimeIntegrand p degree z) z
  infinityTime_order :
    analyticOrderAt infinityTime 0 = (degree - 1 : ℕ)
  finiteTime_analytic : AnalyticAt ℂ finiteTime center
  finiteTime_zero : finiteTime center = 0
  finiteTime_derivative :
    ∀ᶠ x in nhds center,
      HasDerivAt finiteTime (finiteTimeIntegrand p x) x
  finiteTime_derivative_center :
    deriv finiteTime center = (p.eval center)⁻¹
  finiteTime_order : analyticOrderAt finiteTime center = (1 : ℕ)
  fiberProduct :
    AnalyticRamifiedFiberProduct infinityTime finiteTime
      0 center (degree - 1) 1
  inverse_lifted_reciprocal_order :
    meromorphicOrderAt
        ((fun w ↦ fiberProduct.liftedTarget w - 0)⁻¹) 0 =
      ((-1 : ℤ) : WithTop ℤ)

/-- Exact-degree polynomial infinity time and a regular finite Abel time
coordinate construct a finite ramified fiber product with a simple pole. -/
theorem polynomial_regular_infinity_fiber_product_terminal_certificate :
    ∀ (p : ℂ[X]) (degree : ℕ) (center : ℂ),
      p.natDegree = degree →
      2 ≤ degree →
      p.eval center ≠ 0 →
      Nonempty (PolynomialRegularInfinityFiberProduct p degree center) := by
  intro p degree center hdegree htwo hregular
  obtain ⟨infinityTime, hinfinityAnalytic, hinfinityZero,
      hinfinityDerivative, hinfinityOrder, hinfinityPositive⟩ :=
    polynomial_infinity_time_coordinate_terminal_certificate
      p degree hdegree htwo
  obtain ⟨finiteTime, hfiniteAnalytic, hfiniteZero,
      hfiniteDerivative, hfiniteDerivativeCenter, hfiniteOrder⟩ :=
    polynomial_finite_time_coordinate_terminal_certificate p center hregular
  obtain ⟨fiberProduct⟩ :=
    analytic_ramified_fiber_product_terminal_certificate
      infinityTime finiteTime 0 center (degree - 1) 1
      hinfinityAnalytic hinfinityOrder hinfinityPositive
      hfiniteAnalytic hfiniteOrder (by simp)
  have hinverseOrder :
      meromorphicOrderAt
          ((fun w ↦ fiberProduct.liftedTarget w - 0)⁻¹) 0 =
        ((-1 : ℤ) : WithTop ℤ) := by
    simpa using fiberProduct.inverse_displacement_order
  exact ⟨{
    infinityTime := infinityTime
    finiteTime := finiteTime
    infinityTime_analytic := hinfinityAnalytic
    infinityTime_zero := hinfinityZero
    infinityTime_derivative := hinfinityDerivative
    infinityTime_order := hinfinityOrder
    finiteTime_analytic := hfiniteAnalytic
    finiteTime_zero := hfiniteZero
    finiteTime_derivative := hfiniteDerivative
    finiteTime_derivative_center := hfiniteDerivativeCenter
    finiteTime_order := hfiniteOrder
    fiberProduct := fiberProduct
    inverse_lifted_reciprocal_order := hinverseOrder
  }⟩

end FormalPolynomialRegularInfinityFiberProduct
