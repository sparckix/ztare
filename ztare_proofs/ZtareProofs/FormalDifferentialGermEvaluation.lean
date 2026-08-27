import Mathlib.Tactic
import ZtareProofs.FormalBivariateDerivationSwap
import ZtareProofs.FormalDerivativePrefixEvaluation
import ZtareProofs.FormalLocalizedDerivativeDarbouxDichotomy

/-!
# Differential evaluation of nested polynomial flows

Evaluation at a moving point intertwines a polynomial total derivation with
the target derivation when the coefficient map and the point velocity
intertwine.  Applying this once to the visible variable and once to the
hidden variable transports the stored bivariate derivation, all of its
iterates, and every finite derivative-prefix ideal into an arbitrary
differential target ring.

The kernel is algebraic.  It assumes no analytic realization and no
vanishing of a positive derivative iterate.
-/

namespace FormalDifferentialGermEvaluation

open Ideal Polynomial
open FormalBivariateDerivationSwap
open FormalDerivativePrefixEvaluation
open FormalDifferentialPolynomialInvariantSpecialization
open FormalFiniteDerivativeDarbouxAlternative
open FormalLocalizedDerivativeDarbouxDichotomy

noncomputable section

variable {K S : Type*} [CommRing K] [CommRing S]

/-- Evaluation of a nested polynomial first at the visible point in its
coefficient polynomial and then at the hidden point. -/
def nestedEvalRingHom
    (coefficientMap : K →+* S) (visible hidden : S) :
    K[X][X] →+* S :=
  eval₂RingHom (eval₂RingHom coefficientMap visible) hidden

/-- Moving-point chain rule for the total polynomial derivation.  Agreement
on constants and the polynomial variable generates agreement on every
polynomial. -/
theorem eval₂_polynomialTotalDerivation
    (dK : Derivation ℤ K K) (dS : Derivation ℤ S S)
    (coefficientMap : K →+* S) (velocity : K[X]) (point : S)
    (hcoefficients : ∀ coefficient : K,
      coefficientMap (dK coefficient) =
        dS (coefficientMap coefficient))
    (hpoint : dS point = velocity.eval₂ coefficientMap point) :
    ∀ polynomial : K[X],
      (polynomialTotalDerivation dK velocity polynomial).eval₂
          coefficientMap point =
        dS (polynomial.eval₂ coefficientMap point) := by
  let evaluation : K[X] →+* S := eval₂RingHom coefficientMap point
  have hconstant : ∀ coefficient : K,
      evaluation (polynomialTotalDerivation dK velocity (C coefficient)) =
        dS (evaluation (C coefficient)) := by
    intro coefficient
    simp [evaluation, hcoefficients]
  have hvariable :
      evaluation (polynomialTotalDerivation dK velocity X) =
        dS (evaluation X) := by
    simpa [evaluation] using hpoint.symm
  intro polynomial
  change evaluation (polynomialTotalDerivation dK velocity polynomial) =
    dS (evaluation polynomial)
  induction polynomial using Polynomial.induction_on' with
  | add left right hleft hright =>
      simpa only [map_add] using congrArg₂ (· + ·) hleft hright
  | monomial degree coefficient =>
      have hpower :
          evaluation
              (polynomialTotalDerivation dK velocity (X ^ degree)) =
            dS (evaluation (X ^ degree)) := by
        induction degree with
        | zero => simp
        | succ degree inductionHypothesis =>
            rw [pow_succ]
            calc
              evaluation (polynomialTotalDerivation dK velocity
                    (X ^ degree * X)) =
                  evaluation
                    (X ^ degree • polynomialTotalDerivation dK velocity X +
                      X • polynomialTotalDerivation dK velocity
                        (X ^ degree)) := by
                    rw [(polynomialTotalDerivation dK velocity).leibniz]
              _ = evaluation (X ^ degree) *
                    evaluation (polynomialTotalDerivation dK velocity X) +
                  evaluation X * evaluation
                    (polynomialTotalDerivation dK velocity
                      (X ^ degree)) := by
                    simp only [smul_eq_mul, map_add, map_mul]
              _ = evaluation (X ^ degree) * dS (evaluation X) +
                  evaluation X * dS (evaluation (X ^ degree)) := by
                    rw [hvariable, inductionHypothesis]
              _ = dS (evaluation (X ^ degree) * evaluation X) := by
                    symm
                    simpa only [smul_eq_mul] using
                      dS.leibniz (evaluation (X ^ degree)) (evaluation X)
              _ = dS (evaluation (X ^ degree * X)) := by
                    exact congrArg dS
                      (map_mul evaluation (X ^ degree) X).symm
      rw [← C_mul_X_pow_eq_monomial]
      calc
        evaluation (polynomialTotalDerivation dK velocity
              (C coefficient * X ^ degree)) =
            evaluation
              (C coefficient • polynomialTotalDerivation dK velocity
                  (X ^ degree) +
                X ^ degree • polynomialTotalDerivation dK velocity
                  (C coefficient)) := by
              rw [(polynomialTotalDerivation dK velocity).leibniz]
        _ = evaluation (C coefficient) *
              evaluation (polynomialTotalDerivation dK velocity
                (X ^ degree)) +
            evaluation (X ^ degree) *
              evaluation (polynomialTotalDerivation dK velocity
                (C coefficient)) := by
              simp only [smul_eq_mul, map_add, map_mul]
        _ = evaluation (C coefficient) *
              dS (evaluation (X ^ degree)) +
            evaluation (X ^ degree) * dS (evaluation (C coefficient)) := by
              rw [hpower, hconstant]
        _ = dS (evaluation (C coefficient) * evaluation (X ^ degree)) := by
              symm
              simpa only [smul_eq_mul] using
                dS.leibniz (evaluation (C coefficient))
                  (evaluation (X ^ degree))
        _ = dS (evaluation (C coefficient * X ^ degree)) := by
              exact congrArg dS
                (map_mul evaluation (C coefficient) (X ^ degree)).symm

/-- Evaluating a polynomial lifted as coefficients of a second polynomial
recovers direct evaluation under the original coefficient map. -/
theorem eval₂_map_C
    (coefficientMap : K →+* S) (visible hidden : S)
    (polynomial : K[X]) :
    (polynomial.map C).eval₂ (eval₂RingHom coefficientMap visible) hidden =
      polynomial.eval₂ coefficientMap hidden := by
  rw [Polynomial.eval₂_map]
  congr 1
  ext coefficient
  simp

/-- The exact stored bivariate derivation becomes target differentiation
after nested evaluation when the visible and hidden germs satisfy their two
generator equations. -/
theorem nestedEval_storedBivariateDerivation
    (dK : Derivation ℤ K K) (dS : Derivation ℤ S S)
    (coefficientMap : K →+* S) (velocity : K[X])
    (logarithmicWeight : K) (visible hidden : S)
    (hcoefficients : ∀ coefficient : K,
      coefficientMap (dK coefficient) =
        dS (coefficientMap coefficient))
    (hvisible : dS visible = coefficientMap logarithmicWeight * visible)
    (hhidden : dS hidden = velocity.eval₂ coefficientMap hidden) :
    ∀ polynomial : K[X][X],
      nestedEvalRingHom coefficientMap visible hidden
          (storedBivariateDerivation
            dK velocity logarithmicWeight polynomial) =
        dS (nestedEvalRingHom coefficientMap visible hidden polynomial) := by
  have hvisibleVelocity :
      dS visible =
        (C logarithmicWeight * X).eval₂ coefficientMap visible := by
    simpa using hvisible
  have hvisibleIntertwines : ∀ coefficientPolynomial : K[X],
      (polynomialTotalDerivation dK (C logarithmicWeight * X)
          coefficientPolynomial).eval₂ coefficientMap visible =
        dS (coefficientPolynomial.eval₂ coefficientMap visible) :=
    eval₂_polynomialTotalDerivation dK dS coefficientMap
      (C logarithmicWeight * X) visible hcoefficients hvisibleVelocity
  have hhiddenVelocity :
      dS hidden =
        (velocity.map C).eval₂
          (eval₂RingHom coefficientMap visible) hidden := by
    rw [eval₂_map_C]
    exact hhidden
  exact eval₂_polynomialTotalDerivation
    (polynomialTotalDerivation dK (C logarithmicWeight * X))
    dS (eval₂RingHom coefficientMap visible) (velocity.map C) hidden
    hvisibleIntertwines hhiddenVelocity

/-- Nested evaluation transports every natural iterate of the stored
bivariate derivation. -/
theorem nestedEval_iterate_storedBivariateDerivation
    (dK : Derivation ℤ K K) (dS : Derivation ℤ S S)
    (coefficientMap : K →+* S) (velocity : K[X])
    (logarithmicWeight : K) (visible hidden : S)
    (hcoefficients : ∀ coefficient : K,
      coefficientMap (dK coefficient) =
        dS (coefficientMap coefficient))
    (hvisible : dS visible = coefficientMap logarithmicWeight * visible)
    (hhidden : dS hidden = velocity.eval₂ coefficientMap hidden) :
    ∀ order polynomial,
      nestedEvalRingHom coefficientMap visible hidden
          (((storedBivariateDerivation
            dK velocity logarithmicWeight : K[X][X] → K[X][X])^[order])
              polynomial) =
        ((dS : S → S)^[order])
          (nestedEvalRingHom coefficientMap visible hidden polynomial) := by
  exact map_iterate_of_intertwines
    (storedBivariateDerivation dK velocity logarithmicWeight) dS
    (nestedEvalRingHom coefficientMap visible hidden)
    (nestedEval_storedBivariateDerivation dK dS coefficientMap velocity
      logarithmicWeight visible hidden hcoefficients hvisible hhidden)

/-- One initial relation equality forces every generator of every finite
derivative prefix to vanish after evaluation. -/
theorem derivativePrefix_generators_vanish_of_initial
    (dK : Derivation ℤ K K) (dS : Derivation ℤ S S)
    (coefficientMap : K →+* S) (velocity : K[X])
    (logarithmicWeight : K) (visible hidden : S)
    (hcoefficients : ∀ coefficient : K,
      coefficientMap (dK coefficient) =
        dS (coefficientMap coefficient))
    (hvisible : dS visible = coefficientMap logarithmicWeight * visible)
    (hhidden : dS hidden = velocity.eval₂ coefficientMap hidden)
    (initial : K[X][X])
    (hinitial : nestedEvalRingHom coefficientMap visible hidden initial = 0)
    (bound : ℕ) :
    ∀ index : Fin (bound + 1),
      nestedEvalRingHom coefficientMap visible hidden
          (((storedBivariateDerivation
            dK velocity logarithmicWeight : K[X][X] → K[X][X])^[index.1])
              initial) = 0 := by
  intro index
  rw [nestedEval_iterate_storedBivariateDerivation dK dS coefficientMap
    velocity logarithmicWeight visible hidden hcoefficients hvisible hhidden,
    hinitial]
  induction index.1 with
  | zero => rfl
  | succ order inductionHypothesis =>
      rw [Function.iterate_succ_apply', inductionHypothesis, map_zero]

/-- Every member of the finite derivative-prefix ideal vanishes along the
differentially compatible nested germ. -/
theorem nestedEval_eq_zero_of_mem_derivativePrefixIdeal
    (dK : Derivation ℤ K K) (dS : Derivation ℤ S S)
    (coefficientMap : K →+* S) (velocity : K[X])
    (logarithmicWeight : K) (visible hidden : S)
    (hcoefficients : ∀ coefficient : K,
      coefficientMap (dK coefficient) =
        dS (coefficientMap coefficient))
    (hvisible : dS visible = coefficientMap logarithmicWeight * visible)
    (hhidden : dS hidden = velocity.eval₂ coefficientMap hidden)
    (initial : K[X][X])
    (hinitial : nestedEvalRingHom coefficientMap visible hidden initial = 0)
    (bound : ℕ) (member : K[X][X])
    (hmember : member ∈ derivativePrefixIdeal
      (storedBivariateDerivation dK velocity logarithmicWeight)
      initial bound) :
    nestedEvalRingHom coefficientMap visible hidden member = 0 := by
  exact map_eq_zero_of_mem_derivativePrefixIdeal
    (storedBivariateDerivation dK velocity logarithmicWeight)
    initial bound (nestedEvalRingHom coefficientMap visible hidden)
    (derivativePrefix_generators_vanish_of_initial dK dS coefficientMap
      velocity logarithmicWeight visible hidden hcoefficients hvisible
      hhidden initial hinitial bound)
    member hmember

/-- Aggregated differential-germ evaluation certificate. -/
theorem differential_germ_evaluation_terminal_certificate :
    ∀ (dK : Derivation ℤ K K) (dS : Derivation ℤ S S)
      (coefficientMap : K →+* S) (velocity : K[X])
      (logarithmicWeight : K) (visible hidden : S),
      (∀ coefficient : K,
        coefficientMap (dK coefficient) =
          dS (coefficientMap coefficient)) →
      dS visible = coefficientMap logarithmicWeight * visible →
      dS hidden = velocity.eval₂ coefficientMap hidden →
      ∀ initial : K[X][X],
        nestedEvalRingHom coefficientMap visible hidden initial = 0 →
        (∀ order,
          nestedEvalRingHom coefficientMap visible hidden
              (((storedBivariateDerivation
                dK velocity logarithmicWeight : K[X][X] → K[X][X])^[order])
                  initial) = 0) ∧
        ∀ bound member,
          member ∈ derivativePrefixIdeal
            (storedBivariateDerivation dK velocity logarithmicWeight)
            initial bound →
          nestedEvalRingHom coefficientMap visible hidden member = 0 := by
  intro dK dS coefficientMap velocity logarithmicWeight visible hidden
    hcoefficients hvisible hhidden initial hinitial
  constructor
  · intro order
    exact derivativePrefix_generators_vanish_of_initial
      dK dS coefficientMap velocity logarithmicWeight visible hidden
      hcoefficients hvisible hhidden initial hinitial order ⟨order, by omega⟩
  · intro bound member hmember
    exact nestedEval_eq_zero_of_mem_derivativePrefixIdeal
      dK dS coefficientMap velocity logarithmicWeight visible hidden
      hcoefficients hvisible hhidden initial hinitial bound member hmember

end

end FormalDifferentialGermEvaluation
