import Mathlib.RingTheory.PowerSeries.Inverse
import Mathlib.RingTheory.PowerSeries.Substitution
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialFlowAtInfinity

/-!
# Cubic exclusion for order-two ramified infinity collisions

Exact finite orders multiply under substitution of one formal power series
into another.  When a polynomial infinity branch also satisfies the critical
balance `r * (d - 1) = 2`, the complete nonproportional collision range
`2 <= e < d` collapses to `r = 1`, `d = 3`, `e = 2`, and collision order
three.  A critical source/target pair with vanishing linear and cubic jets is
therefore incompatible with the pulled-back collision identity.

The result is substrate-neutral.  A caller must derive the collision identity
from its two Julia/Abel coordinates; the identity is not inferred here.
-/

namespace FormalRamifiedCubicCollisionExclusion

open PowerSeries
open FormalPolynomialFlowAtInfinity

variable {𝕜 : Type*} [Field 𝕜]

private theorem order_eq_zero_of_constantCoeff_ne_zero
    (series : 𝕜⟦X⟧)
    (hconstant : PowerSeries.constantCoeff series ≠ 0) :
    PowerSeries.order series = ((0 : ℕ) : ℕ∞) := by
  apply (PowerSeries.order_eq_nat).2
  constructor
  · simpa [PowerSeries.coeff_zero_eq_constantCoeff]
  · intro i hi
    omega

/-- Over a field, substitution multiplies two finite formal-series orders.
Mathlib's general semiring theorem gives only the lower bound; the nonzero
leading coefficient follows by dividing the outer series by its exact power
of `X` and observing that its unit remains a unit after substitution. -/
theorem order_subst_of_finite_orders
    (inner outer : 𝕜⟦X⟧) (innerOrder outerOrder : ℕ)
    (hinnerConstant : PowerSeries.constantCoeff inner = 0)
    (hinnerOrder : PowerSeries.order inner = innerOrder)
    (houterOrder : PowerSeries.order outer = outerOrder) :
    PowerSeries.order (outer.subst inner) =
      ((innerOrder * outerOrder : ℕ) : ℕ∞) := by
  have hinnerNonzero : inner ≠ 0 := by
    intro hzero
    rw [hzero, PowerSeries.order_zero] at hinnerOrder
    exact (ENat.top_ne_coe innerOrder) hinnerOrder
  have houterNonzero : outer ≠ 0 := by
    intro hzero
    rw [hzero, PowerSeries.order_zero] at houterOrder
    exact (ENat.top_ne_coe outerOrder) houterOrder
  have hhas : PowerSeries.HasSubst inner :=
    PowerSeries.HasSubst.of_constantCoeff_zero' hinnerConstant
  have hinnerToNat : (PowerSeries.order inner).toNat = innerOrder := by
    simp [hinnerOrder]
  have houterToNat : (PowerSeries.order outer).toNat = outerOrder := by
    simp [houterOrder]
  let unit := PowerSeries.divXPowOrder outer
  have hunitConstant : PowerSeries.constantCoeff unit ≠ 0 := by
    simpa only [unit, PowerSeries.constantCoeff_divXPowOrder] using
      PowerSeries.coeff_order houterNonzero
  have hunitSubstConstant :
      PowerSeries.constantCoeff (unit.subst inner) ≠ 0 := by
    rw [constantCoeff_subst_of_inner_constantCoeff_zero
      inner unit hinnerConstant]
    exact hunitConstant
  have hunitSubstOrder :
      PowerSeries.order (unit.subst inner) = ((0 : ℕ) : ℕ∞) :=
    order_eq_zero_of_constantCoeff_ne_zero _ hunitSubstConstant
  have hfactor : PowerSeries.X ^ outerOrder * unit = outer := by
    simpa only [unit, houterToNat] using
      (PowerSeries.X_pow_order_mul_divXPowOrder (f := outer))
  rw [← hfactor, PowerSeries.subst_mul hhas,
    PowerSeries.subst_pow hhas, PowerSeries.subst_X hhas,
    PowerSeries.order_mul, PowerSeries.order_pow,
    hinnerOrder, hunitSubstOrder]
  simpa [nsmul_eq_mul] using
    (mul_comm ((outerOrder : ℕ∞)) (innerOrder : ℕ∞))

/-- A pointed inner germ with no linear or cubic jet has no cubic jet after
substitution into any outer formal series. -/
theorem coeff_three_subst_of_zero_linear_cubic
    (inner outer : 𝕜⟦X⟧)
    (hconstant : PowerSeries.constantCoeff inner = 0)
    (hlinear : PowerSeries.coeff 1 inner = 0)
    (hcubic : PowerSeries.coeff 3 inner = 0) :
    PowerSeries.coeff 3 (outer.subst inner) = 0 := by
  have hhas : PowerSeries.HasSubst inner :=
    PowerSeries.HasSubst.of_constantCoeff_zero' hconstant
  rw [PowerSeries.coeff_subst' hhas]
  apply finsum_eq_zero_of_forall_eq_zero
  intro n
  rcases n with _ | _ | n
  · simp
  · simp [hcubic]
  · have hinnerOrder : ((2 : ℕ) : ℕ∞) ≤ PowerSeries.order inner := by
      apply PowerSeries.nat_le_order
      intro i hi
      interval_cases i <;>
        simp_all [PowerSeries.coeff_zero_eq_constantCoeff]
    have hpowOrder : ((4 : ℕ) : ℕ∞) ≤
        PowerSeries.order (inner ^ (n + 2)) := by
      have htwoLe : (2 : ℕ) ≤ n + 2 := by omega
      have htwoLeEnat : ((2 : ℕ) : ℕ∞) ≤ ((n + 2 : ℕ) : ℕ∞) := by
        exact_mod_cast htwoLe
      have hproduct :
          ((2 : ℕ) : ℕ∞) * ((2 : ℕ) : ℕ∞) ≤
            ((n + 2 : ℕ) : ℕ∞) * PowerSeries.order inner :=
        mul_le_mul htwoLeEnat hinnerOrder (by simp) (by simp)
      calc
        ((4 : ℕ) : ℕ∞) ≤
            (n + 2) • PowerSeries.order inner := by
          simpa [nsmul_eq_mul] using hproduct
        _ ≤ PowerSeries.order (inner ^ (n + 2)) :=
          PowerSeries.le_order_pow inner (n + 2)
    have hcoeff : PowerSeries.coeff 3 (inner ^ (n + 2)) = 0 := by
      apply PowerSeries.coeff_of_lt_order
      exact lt_of_lt_of_le (by norm_num) hpowOrder
    simp [hcoeff]

/-- The order-two ramification balance leaves one and only one
nonproportional collision: a cubic generator with a quadratic coefficient
collision, pulled back through an unramified reciprocal coordinate. -/
theorem critical_balance_nonproportional_collision_unique
    (ramification degree collisionDegree : ℕ)
    (hdegree : 2 ≤ degree)
    (hcollisionTwo : 2 ≤ collisionDegree)
    (hcollisionLt : collisionDegree < degree)
    (hbalance : ramification * (degree - 1) = 2) :
    ramification = 1 ∧ degree = 3 ∧ collisionDegree = 2 ∧
      2 * degree - collisionDegree - 1 = 3 := by
  have hramificationDvd : ramification ∣ 2 := by
    exact ⟨degree - 1, hbalance.symm⟩
  rcases (Nat.dvd_prime Nat.prime_two).mp hramificationDvd with
    hramificationOne | hramificationTwo
  · subst ramification
    omega
  · subst ramification
    omega

/-- A pulled-back nonproportional infinity collision cannot equal a
difference of two analytic coordinate substitutions whose source and target
displacements both have zero linear and cubic jets. -/
theorem ramified_cubic_collision_excluded
    (reciprocal collision sourceDisplacement targetDisplacement
      sourceCoordinate targetCoordinate : 𝕜⟦X⟧)
    (ramification degree collisionDegree : ℕ)
    (hreciprocalConstant :
      PowerSeries.constantCoeff reciprocal = 0)
    (hreciprocalOrder :
      PowerSeries.order reciprocal = ramification)
    (hcollisionOrder :
      PowerSeries.order collision =
        ((2 * degree - collisionDegree - 1 : ℕ) : ℕ∞))
    (hdegree : 2 ≤ degree)
    (hcollisionTwo : 2 ≤ collisionDegree)
    (hcollisionLt : collisionDegree < degree)
    (hbalance : ramification * (degree - 1) = 2)
    (hsourceConstant :
      PowerSeries.constantCoeff sourceDisplacement = 0)
    (hsourceLinear : PowerSeries.coeff 1 sourceDisplacement = 0)
    (hsourceCubic : PowerSeries.coeff 3 sourceDisplacement = 0)
    (htargetConstant :
      PowerSeries.constantCoeff targetDisplacement = 0)
    (htargetLinear : PowerSeries.coeff 1 targetDisplacement = 0)
    (htargetCubic : PowerSeries.coeff 3 targetDisplacement = 0)
    (habel :
      collision.subst reciprocal =
        targetCoordinate.subst targetDisplacement -
          sourceCoordinate.subst sourceDisplacement) : False := by
  obtain ⟨hramification, hdegreeThree, hcollisionDegree,
      hcollisionOrderNat⟩ :=
    critical_balance_nonproportional_collision_unique
      ramification degree collisionDegree hdegree hcollisionTwo
      hcollisionLt hbalance
  have hpullbackOrder := order_subst_of_finite_orders
    reciprocal collision ramification
      (2 * degree - collisionDegree - 1)
      hreciprocalConstant hreciprocalOrder hcollisionOrder
  rw [hramification, hcollisionOrderNat] at hpullbackOrder
  norm_num at hpullbackOrder
  have hpullbackCubic :
      PowerSeries.coeff 3 (collision.subst reciprocal) ≠ 0 :=
    (PowerSeries.order_eq_nat.mp hpullbackOrder).1
  have hsourceCoordinateCubic :=
    coeff_three_subst_of_zero_linear_cubic
      sourceDisplacement sourceCoordinate hsourceConstant
      hsourceLinear hsourceCubic
  have htargetCoordinateCubic :=
    coeff_three_subst_of_zero_linear_cubic
      targetDisplacement targetCoordinate htargetConstant
      htargetLinear htargetCubic
  apply hpullbackCubic
  rw [habel, map_sub, htargetCoordinateCubic,
    hsourceCoordinateCubic, sub_zero]

/-- Aggregated reusable terminal surface. -/
theorem ramified_cubic_collision_exclusion_terminal_certificate :
    (∀ (inner outer : 𝕜⟦X⟧) (innerOrder outerOrder : ℕ),
      PowerSeries.constantCoeff inner = 0 →
      PowerSeries.order inner = innerOrder →
      PowerSeries.order outer = outerOrder →
      PowerSeries.order (outer.subst inner) =
        ((innerOrder * outerOrder : ℕ) : ℕ∞)) ∧
    (∀ (inner outer : 𝕜⟦X⟧),
      PowerSeries.constantCoeff inner = 0 →
      PowerSeries.coeff 1 inner = 0 →
      PowerSeries.coeff 3 inner = 0 →
      PowerSeries.coeff 3 (outer.subst inner) = 0) ∧
    (∀ (reciprocal collision sourceDisplacement targetDisplacement
        sourceCoordinate targetCoordinate : 𝕜⟦X⟧)
      (ramification degree collisionDegree : ℕ),
      PowerSeries.constantCoeff reciprocal = 0 →
      PowerSeries.order reciprocal = ramification →
      PowerSeries.order collision =
        ((2 * degree - collisionDegree - 1 : ℕ) : ℕ∞) →
      2 ≤ degree → 2 ≤ collisionDegree → collisionDegree < degree →
      ramification * (degree - 1) = 2 →
      PowerSeries.constantCoeff sourceDisplacement = 0 →
      PowerSeries.coeff 1 sourceDisplacement = 0 →
      PowerSeries.coeff 3 sourceDisplacement = 0 →
      PowerSeries.constantCoeff targetDisplacement = 0 →
      PowerSeries.coeff 1 targetDisplacement = 0 →
      PowerSeries.coeff 3 targetDisplacement = 0 →
      collision.subst reciprocal =
        targetCoordinate.subst targetDisplacement -
          sourceCoordinate.subst sourceDisplacement → False) := by
  refine ⟨order_subst_of_finite_orders, ?_, ?_⟩
  · exact coeff_three_subst_of_zero_linear_cubic
  · exact ramified_cubic_collision_excluded

end FormalRamifiedCubicCollisionExclusion
