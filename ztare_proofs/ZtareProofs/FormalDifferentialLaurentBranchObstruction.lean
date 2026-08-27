import Mathlib.RingTheory.LaurentSeries
import Mathlib.RingTheory.PowerSeries.Derivative
import Mathlib.Tactic
import ZtareProofs.FormalDifferentialGermEvaluation
import ZtareProofs.FormalLocalizationDerivationExtension

/-!
# Differential Laurent branch obstruction

A derivation of the coefficient field is extended coefficientwise to formal
power series and combined with the visible linear connection `D X = L X`.
The resulting derivation is then extended canonically to Laurent series.

One initial nested relation on a hidden formal branch transports through every
stored derivative iterate.  Consequently a nonzero polynomial in the visible
variable cannot lie in the derivative-prefix ideal: evaluation would make its
canonical image vanish in Laurent series, contradicting injectivity.
-/

namespace FormalDifferentialLaurentBranchObstruction

open Ideal Polynomial PowerSeries
open FormalBivariateDerivationSwap
open FormalDerivativePrefixEvaluation
open FormalDifferentialGermEvaluation
open FormalFiniteDerivativeDarbouxAlternative
open FormalLocalizationDerivationExtension
open scoped LaurentSeries

noncomputable section

variable {K : Type*} [Field K]

noncomputable local instance powerSeriesCanonicalIntAlgebra :
    Algebra ℤ K⟦X⟧ :=
  Ring.toIntAlgebra K⟦X⟧

noncomputable local instance laurentSeriesCanonicalIntAlgebra :
    Algebra ℤ K⸨X⸩ :=
  Ring.toIntAlgebra K⸨X⸩

/-- Apply a coefficient derivation independently to every coefficient of a
formal power series. -/
def coefficientwisePowerSeriesAddHom (dK : Derivation ℤ K K) :
    K⟦X⟧ →+ K⟦X⟧ where
  toFun series := PowerSeries.mk fun degree => dK (coeff degree series)
  map_zero' := by
    ext degree
    simp
  map_add' := by
    intro first second
    ext degree
    simp

@[simp]
theorem coefficientwisePowerSeriesAddHom_apply
    (dK : Derivation ℤ K K) (series : K⟦X⟧) :
    coefficientwisePowerSeriesAddHom dK series =
      PowerSeries.mk fun degree => dK (coeff degree series) := by
  rfl

/-- Coefficientwise extension of a coefficient-ring derivation to formal
power series. -/
def coefficientwisePowerSeriesDerivation (dK : Derivation ℤ K K) :
    Derivation ℤ K⟦X⟧ K⟦X⟧ :=
  Derivation.mk'
    (coefficientwisePowerSeriesAddHom dK).toIntLinearMap
    (by
      intro first second
      ext degree
      change
        coeff degree
            (coefficientwisePowerSeriesAddHom dK (first * second)) =
          coeff degree
            (first * coefficientwisePowerSeriesAddHom dK second +
              second * coefficientwisePowerSeriesAddHom dK first)
      simp only [coefficientwisePowerSeriesAddHom_apply, coeff_mk,
        PowerSeries.coeff_mul, map_sum, dK.leibniz, smul_eq_mul,
        map_add, Finset.sum_add_distrib]
      have hswap :
          (∑ pair ∈ Finset.antidiagonal degree,
              coeff pair.2 second * dK (coeff pair.1 first)) =
            ∑ pair ∈ Finset.antidiagonal degree,
              coeff pair.1 second * dK (coeff pair.2 first) := by
        simpa only [Prod.swap_prod_mk] using
          (Finset.Nat.sum_antidiagonal_swap
            (n := degree)
            (f := fun pair =>
              coeff pair.1 second * dK (coeff pair.2 first)))
      rw [hswap])

@[simp]
theorem coefficientwisePowerSeriesDerivation_coeff
    (dK : Derivation ℤ K K) (series : K⟦X⟧) (degree : ℕ) :
    coeff degree (coefficientwisePowerSeriesDerivation dK series) =
      dK (coeff degree series) := by
  change
    coeff degree (coefficientwisePowerSeriesAddHom dK series) =
      dK (coeff degree series)
  simp [coefficientwisePowerSeriesAddHom]

@[simp]
theorem coefficientwisePowerSeriesDerivation_C
    (dK : Derivation ℤ K K) (coefficient : K) :
    coefficientwisePowerSeriesDerivation dK (PowerSeries.C coefficient) =
      PowerSeries.C (dK coefficient) := by
  ext degree
  by_cases hdegree : degree = 0
  · subst degree
    simp
  · simp [PowerSeries.coeff_C, hdegree]

@[simp]
theorem coefficientwisePowerSeriesDerivation_X
    (dK : Derivation ℤ K K) :
    coefficientwisePowerSeriesDerivation dK (PowerSeries.X : K⟦X⟧) = 0 := by
  ext degree
  by_cases hdegree : degree = 1
  · subst degree
    simp [PowerSeries.coeff_X]
  · simp [PowerSeries.coeff_X, hdegree]

/-- The total formal connection: differentiate coefficients and add the
visible Euler term `(L X) d/dX`. -/
def powerSeriesTotalConnection
    (dK : Derivation ℤ K K) (logarithmicWeight : K) :
    Derivation ℤ K⟦X⟧ K⟦X⟧ :=
  coefficientwisePowerSeriesDerivation dK +
    (PowerSeries.C logarithmicWeight * PowerSeries.X) •
      powerSeriesIntDerivation K

@[simp]
theorem powerSeriesTotalConnection_C
    (dK : Derivation ℤ K K) (logarithmicWeight coefficient : K) :
    powerSeriesTotalConnection dK logarithmicWeight
        (PowerSeries.C coefficient) =
      PowerSeries.C (dK coefficient) := by
  simp [powerSeriesTotalConnection]

@[simp]
theorem powerSeriesTotalConnection_X
    (dK : Derivation ℤ K K) (logarithmicWeight : K) :
    powerSeriesTotalConnection dK logarithmicWeight
        (PowerSeries.X : K⟦X⟧) =
      PowerSeries.C logarithmicWeight * PowerSeries.X := by
  simp [powerSeriesTotalConnection]

/-- Localization of the total connection to Laurent series. -/
def laurentSeriesTotalConnection
    (dK : Derivation ℤ K K) (logarithmicWeight : K) :
    Derivation ℤ K⸨X⸩ K⸨X⸩ :=
  localizationDerivation
    (Submonoid.powers (PowerSeries.X : K⟦X⟧))
    (powerSeriesTotalConnection dK logarithmicWeight)

@[simp]
theorem laurentSeriesTotalConnection_algebraMap
    (dK : Derivation ℤ K K) (logarithmicWeight : K)
    (series : K⟦X⟧) :
    laurentSeriesTotalConnection dK logarithmicWeight
        (algebraMap K⟦X⟧ K⸨X⸩ series) =
      algebraMap K⟦X⟧ K⸨X⸩
        (powerSeriesTotalConnection dK logarithmicWeight series) := by
  exact localizationDerivation_algebraMap
    (A := K⟦X⟧) (S := K⸨X⸩)
    (Submonoid.powers (PowerSeries.X : K⟦X⟧))
    (powerSeriesTotalConnection dK logarithmicWeight) series

/-- A selected formal branch satisfying the exact hidden ODE excludes every
nonzero visible polynomial from every finite derivative-prefix ideal.

The target, its derivation, its coefficient binding, its visible equation,
and visible-variable injectivity are all canonical constructions.  The only
geometric inputs are the hidden branch ODE and the single initial relation
equality. -/
theorem no_nonzero_visible_prefix_eliminant_on_powerSeries_branch
    (dK : Derivation ℤ K K) (velocity : K[X])
    (logarithmicWeight : K) (hidden : K⟦X⟧)
    (initial : K[X][X]) (bound : ℕ) (eliminant : K[X])
    (hhidden :
      powerSeriesTotalConnection dK logarithmicWeight hidden =
        velocity.eval₂ PowerSeries.C hidden)
    (hinitial :
      nestedEvalRingHom PowerSeries.C PowerSeries.X hidden initial = 0)
    (hmember :
      Polynomial.C eliminant ∈ derivativePrefixIdeal
        (storedBivariateDerivation dK velocity logarithmicWeight)
        initial bound)
    (heliminant : eliminant ≠ 0) : False := by
  have hevaluated :
      nestedEvalRingHom PowerSeries.C PowerSeries.X hidden
          (Polynomial.C eliminant) = 0 := by
    exact nestedEval_eq_zero_of_mem_derivativePrefixIdeal
      dK (powerSeriesTotalConnection dK logarithmicWeight)
      PowerSeries.C velocity logarithmicWeight PowerSeries.X hidden
      (by
        intro coefficient
        simp)
      (by simp)
      hhidden initial hinitial bound (Polynomial.C eliminant) hmember
  have hpowerSeries : (eliminant : K⟦X⟧) = 0 := by
    simpa [nestedEvalRingHom, Polynomial.eval₂_C_X_eq_coe] using hevaluated
  exact heliminant (Polynomial.coe_injective K hpowerSeries)

/-- Aggregated certificate for the constructed formal connection and its
finite-prefix obstruction. -/
theorem differential_laurent_branch_obstruction_terminal_certificate
    (dK : Derivation ℤ K K) (velocity : K[X])
    (logarithmicWeight : K) (hidden : K⟦X⟧)
    (initial : K[X][X]) (bound : ℕ) (eliminant : K[X])
    (hhidden :
      powerSeriesTotalConnection dK logarithmicWeight hidden =
        velocity.eval₂ PowerSeries.C hidden)
    (hinitial :
      nestedEvalRingHom PowerSeries.C PowerSeries.X hidden initial = 0)
    (hmember :
      Polynomial.C eliminant ∈ derivativePrefixIdeal
        (storedBivariateDerivation dK velocity logarithmicWeight)
        initial bound)
    (heliminant : eliminant ≠ 0) :
    (∀ coefficient : K,
      powerSeriesTotalConnection dK logarithmicWeight
          (PowerSeries.C coefficient) =
        PowerSeries.C (dK coefficient)) ∧
    powerSeriesTotalConnection dK logarithmicWeight PowerSeries.X =
      PowerSeries.C logarithmicWeight * PowerSeries.X ∧
    False := by
  refine ⟨powerSeriesTotalConnection_C dK logarithmicWeight, ?_, ?_⟩
  · exact powerSeriesTotalConnection_X dK logarithmicWeight
  · exact no_nonzero_visible_prefix_eliminant_on_powerSeries_branch
      dK velocity logarithmicWeight hidden initial bound eliminant
      hhidden hinitial hmember heliminant

end

end FormalDifferentialLaurentBranchObstruction
