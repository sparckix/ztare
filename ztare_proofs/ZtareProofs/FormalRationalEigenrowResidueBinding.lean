import Mathlib.Tactic
import ZtareProofs.FormalRationalFunctionDerivationLocalOrder
import ZtareProofs.FormalRationalLogDerivativeResidueComparison

/-!
# Binding a rational scalar eigenrow to a finite-pole residue equation

Two nonzero rational functions satisfying a cross-multiplied scalar
eigenrow have a nonzero rational quotient.  The formal quotient derivation,
canonical numerator and denominator, and their automatically constructed
local zero/pole factors reduce the eigenrow to equality between an integral
local order and the connection residue.
-/

namespace FormalRationalEigenrowResidueBinding

open Polynomial

open FormalRationalFunctionDerivationLocalOrder
open FormalRationalLogDerivativeResidueComparison

variable {K : Type*} [Field K]

noncomputable local instance ratFuncCanonicalIntAlgebra :
    Algebra ℤ (RatFunc K) :=
  Ring.toIntAlgebra (RatFunc K)

/-- A scalar cross row gives the logarithmic differential equation for the
quotient. -/
theorem quotient_eigenrow_of_cross
    (weight : K) (connection first second : RatFunc K)
    (hsecond : second ≠ 0)
    (hcross :
      second * ratFuncDerivation first -
          first * ratFuncDerivation second =
        RatFunc.C weight * connection * first * second) :
    ratFuncDerivation (first / second) =
      RatFunc.C weight * connection * (first / second) := by
  rw [Derivation.leibniz_div]
  simp only [smul_eq_mul]
  rw [hcross]
  field_simp [hsecond]

/-- A rational eigenrow, expressed through the canonical numerator and
denominator of its quotient, clears to the polynomial row consumed by the
local residue kernel. -/
theorem canonical_polynomial_cross_of_rational_eigenrow
    (point weight : K)
    (connectionNumerator reducedDenominator : K[X])
    (connection first second : RatFunc K)
    (hsecond : second ≠ 0)
    (hreducedDenominator : reducedDenominator ≠ 0)
    (hconnection :
      connection =
        algebraMap K[X] (RatFunc K) connectionNumerator /
          algebraMap K[X] (RatFunc K)
            ((X - C point) * reducedDenominator))
    (hcross :
      second * ratFuncDerivation first -
          first * ratFuncDerivation second =
        RatFunc.C weight * connection * first * second) :
    let ratio := first / second
    ((X - C point) * reducedDenominator) *
          (ratio.num.derivative * ratio.denom -
            ratio.num * ratio.denom.derivative) =
      C weight * connectionNumerator * ratio.num * ratio.denom := by
  dsimp only
  let ratio : RatFunc K := first / second
  have hquotient := quotient_eigenrow_of_cross
    weight connection first second hsecond hcross
  have hcanonical :
      quotientDerivative ratio.num ratio.denom =
        RatFunc.C weight * connection *
          (algebraMap K[X] (RatFunc K) ratio.num /
            algebraMap K[X] (RatFunc K) ratio.denom) := by
    calc
      quotientDerivative ratio.num ratio.denom =
          ratFuncDerivation
            (algebraMap K[X] (RatFunc K) ratio.num /
              algebraMap K[X] (RatFunc K) ratio.denom) :=
        (ratFuncDerivation_div ratio.num ratio.denom).symm
      _ = ratFuncDerivation ratio := by
        rw [RatFunc.num_div_denom]
      _ = RatFunc.C weight * connection * ratio := hquotient
      _ = RatFunc.C weight * connection *
            (algebraMap K[X] (RatFunc K) ratio.num /
              algebraMap K[X] (RatFunc K) ratio.denom) := by
        rw [RatFunc.num_div_denom]
  rw [hconnection] at hcanonical
  rw [quotientDerivative] at hcanonical
  rw [← RatFunc.algebraMap_C] at hcanonical
  have hconnectionDenominator :
      (X - C point) * reducedDenominator ≠ 0 :=
    mul_ne_zero (X_sub_C_ne_zero point) hreducedDenominator
  have hratioDenominator : ratio.denom ≠ 0 := ratio.denom_ne_zero
  have hconnectionDenominatorMap :
      algebraMap K[X] (RatFunc K)
          ((X - C point) * reducedDenominator) ≠ 0 :=
    RatFunc.algebraMap_ne_zero hconnectionDenominator
  have hratioDenominatorMap :
      algebraMap K[X] (RatFunc K) ratio.denom ≠ 0 :=
    RatFunc.algebraMap_ne_zero hratioDenominator
  field_simp [hconnectionDenominatorMap, hratioDenominatorMap] at hcanonical
  change
    ((X - C point) * reducedDenominator) *
          (ratio.num.derivative * ratio.denom -
            ratio.num * ratio.denom.derivative) =
      C weight * connectionNumerator * ratio.num * ratio.denom
  apply RatFunc.algebraMap_injective K
  simp only [map_mul, map_sub] at hcanonical ⊢
  convert hcanonical using 1 <;> ring

/-- Every nonzero rational scalar cross row forces equality between the
canonical zero-minus-pole order of the quotient and the weighted residue. -/
theorem local_order_eq_weight_mul_residue_of_rational_cross
    (point weight residue : K)
    (connectionNumerator reducedDenominator : K[X])
    (connection first second : RatFunc K)
    (hfirst : first ≠ 0) (hsecond : second ≠ 0)
    (hreducedAtPoint : reducedDenominator.eval point ≠ 0)
    (hresidue :
      connectionNumerator.eval point =
        residue * reducedDenominator.eval point)
    (hconnection :
      connection =
        algebraMap K[X] (RatFunc K) connectionNumerator /
          algebraMap K[X] (RatFunc K)
            ((X - C point) * reducedDenominator))
    (hcross :
      second * ratFuncDerivation first -
          first * ratFuncDerivation second =
        RatFunc.C weight * connection * first * second) :
    let ratio := first / second
    (ratio.num.rootMultiplicity point : K) -
        (ratio.denom.rootMultiplicity point : K) =
      weight * residue := by
  dsimp only
  let ratio : RatFunc K := first / second
  have hratio : ratio ≠ 0 := div_ne_zero hfirst hsecond
  let numeratorUnit :=
    ratio.num /ₘ
      (X - C point) ^ ratio.num.rootMultiplicity point
  let denominatorUnit :=
    ratio.denom /ₘ
      (X - C point) ^ ratio.denom.rootMultiplicity point
  have hnormal := rationalFunctionLocalNormalForm ratio point hratio
  dsimp only at hnormal
  have hraw := canonical_polynomial_cross_of_rational_eigenrow
    point weight connectionNumerator reducedDenominator
      connection first second hsecond
      (fun hzero => hreducedAtPoint (by rw [hzero]; simp))
      hconnection hcross
  dsimp only at hraw
  have hrawFactored := hraw
  rw [hnormal.1, hnormal.2.1] at hrawFactored
  have hnormalized := normalized_cross_of_local_factorizations
    point weight (ratio.num.rootMultiplicity point)
      (ratio.denom.rootMultiplicity point) numeratorUnit denominatorUnit
      connectionNumerator reducedDenominator (by
        exact hrawFactored)
  exact local_order_eq_weight_mul_residue
    point weight residue (ratio.num.rootMultiplicity point)
      (ratio.denom.rootMultiplicity point) numeratorUnit denominatorUnit
      connectionNumerator reducedDenominator
      hnormal.2.2.1 hnormal.2.2.2 hreducedAtPoint hresidue hnormalized

end FormalRationalEigenrowResidueBinding
