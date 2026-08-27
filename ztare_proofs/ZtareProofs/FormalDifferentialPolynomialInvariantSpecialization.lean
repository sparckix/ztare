import Mathlib.RingTheory.Derivation.MapCoeffs
import Mathlib.Tactic

/-!
# Polynomial total derivations and invariant specialization

A coefficient derivation and a polynomial velocity define the total
derivation `P ↦ d_coeff(P) + v P'`.  A coefficient homomorphism that
intertwines both coefficient derivations and velocities intertwines the total
derivations at every iterate.  Specialization of a visible variable along a
divisor preserved by its velocity is the main consumer.
-/

namespace FormalDifferentialPolynomialInvariantSpecialization

open Polynomial

/-- Apply a supplied coefficient derivation coefficientwise. -/
noncomputable def polynomialCoefficientDerivation
    {R : Type*} [CommRing R] (d : Derivation ℤ R R) :
    Derivation ℤ R[X] R[X] :=
  letI : Differential R := ⟨d⟩
  Differential.mapCoeffs

@[simp]
theorem coeff_polynomialCoefficientDerivation
    {R : Type*} [CommRing R] (d : Derivation ℤ R R)
    (polynomial : R[X]) (n : ℕ) :
    (polynomialCoefficientDerivation d polynomial).coeff n =
      d (polynomial.coeff n) := by
  rfl

/-- Lift a coefficient derivation to a polynomial total derivation with the
declared velocity of the polynomial variable. -/
noncomputable def polynomialTotalDerivation
    {R : Type*} [CommRing R]
    (d : Derivation ℤ R R) (velocity : R[X]) :
    Derivation ℤ R[X] R[X] :=
  polynomialCoefficientDerivation d +
    velocity • (Polynomial.derivative'.restrictScalars ℤ)

theorem polynomialTotalDerivation_apply
    {R : Type*} [CommRing R]
    (d : Derivation ℤ R R) (velocity polynomial : R[X]) :
    polynomialTotalDerivation d velocity polynomial =
      polynomialCoefficientDerivation d polynomial +
        velocity * polynomial.derivative := by
  rfl

@[simp]
theorem polynomialTotalDerivation_C
    {R : Type*} [CommRing R]
    (d : Derivation ℤ R R) (velocity : R[X]) (a : R) :
    polynomialTotalDerivation d velocity (C a) = C (d a) := by
  ext n
  rw [polynomialTotalDerivation_apply, coeff_add, coeff_mul]
  by_cases hn : n = 0
  · subst n
    simp
  · simp [coeff_C, hn]

@[simp]
theorem polynomialTotalDerivation_X
    {R : Type*} [CommRing R]
    (d : Derivation ℤ R R) (velocity : R[X]) :
    polynomialTotalDerivation d velocity X = velocity := by
  rw [polynomialTotalDerivation_apply]
  ext n
  rw [coeff_add]
  have hcoefficient :
      (polynomialCoefficientDerivation d X).coeff n = 0 := by
    rw [coeff_polynomialCoefficientDerivation]
    by_cases hn : n = 1
    · subst n
      simp
    · have hne : 1 ≠ n := Ne.symm hn
      simp [coeff_X, hne]
  rw [hcoefficient, zero_add]
  simp

theorem map_polynomialCoefficientDerivation
    {R S : Type*} [CommRing R] [CommRing S]
    (dR : Derivation ℤ R R) (dS : Derivation ℤ S S)
    (phi : R →+* S)
    (hcoeff : ∀ a : R, phi (dR a) = dS (phi a))
    (polynomial : R[X]) :
    (polynomialCoefficientDerivation dR polynomial).map phi =
      polynomialCoefficientDerivation dS (polynomial.map phi) := by
  ext n
  simp [hcoeff]

/-- Polynomial mapping commutes with total derivations when it commutes with
the coefficient derivations and maps one velocity to the other. -/
theorem map_polynomialTotalDerivation
    {R S : Type*} [CommRing R] [CommRing S]
    (dR : Derivation ℤ R R) (dS : Derivation ℤ S S)
    (phi : R →+* S) (velocityR : R[X]) (velocityS : S[X])
    (hcoeff : ∀ a : R, phi (dR a) = dS (phi a))
    (hvelocity : velocityR.map phi = velocityS) :
    ∀ polynomial : R[X],
      (polynomialTotalDerivation dR velocityR polynomial).map phi =
        polynomialTotalDerivation dS velocityS (polynomial.map phi) := by
  intro polynomial
  rw [polynomialTotalDerivation_apply, polynomialTotalDerivation_apply,
    Polynomial.map_add, Polynomial.map_mul,
    map_polynomialCoefficientDerivation dR dS phi hcoeff,
    derivative_map, hvelocity]

/-- Intertwining of total derivations persists through every natural
iterate. -/
theorem map_iterate_polynomialTotalDerivation
    {R S : Type*} [CommRing R] [CommRing S]
    (dR : Derivation ℤ R R) (dS : Derivation ℤ S S)
    (phi : R →+* S) (velocityR : R[X]) (velocityS : S[X])
    (hcoeff : ∀ a : R, phi (dR a) = dS (phi a))
    (hvelocity : velocityR.map phi = velocityS) :
    ∀ n polynomial,
      (((polynomialTotalDerivation dR velocityR)^[n]) polynomial).map phi =
        ((polynomialTotalDerivation dS velocityS)^[n])
          (polynomial.map phi) := by
  intro n
  induction n with
  | zero =>
      intro polynomial
      rfl
  | succ n inductionHypothesis =>
      intro polynomial
      rw [Function.iterate_succ_apply', Function.iterate_succ_apply',
        map_polynomialTotalDerivation dR dS phi velocityR velocityS
          hcoeff hvelocity,
        inductionHypothesis]

/-- Evaluation at zero intertwines a polynomial total derivation with its
coefficient derivation whenever the variable velocity vanishes at zero. -/
theorem eval_zero_polynomialTotalDerivation
    {R : Type*} [CommRing R]
    (d : Derivation ℤ R R) (velocity : R[X])
    (hvelocity : velocity.eval 0 = 0) :
    ∀ polynomial : R[X],
      (polynomialTotalDerivation d velocity polynomial).eval 0 =
        d (polynomial.eval 0) := by
  intro polynomial
  rw [polynomialTotalDerivation_apply, eval_add, eval_mul, hvelocity,
    zero_mul, add_zero]
  rw [← coeff_zero_eq_eval_zero,
    coeff_polynomialCoefficientDerivation]
  exact congrArg d (coeff_zero_eq_eval_zero polynomial)

/-- Specializing a visible polynomial variable at zero commutes with the
hidden total derivation whenever the visible velocity preserves that
divisor. -/
theorem map_eval_zero_hiddenTotalDerivation
    {R : Type*} [CommRing R]
    (d : Derivation ℤ R R) (visibleVelocity p : R[X])
    (hvisible : visibleVelocity.eval 0 = 0) :
    ∀ hiddenPolynomial : R[X][X],
      (polynomialTotalDerivation
          (polynomialTotalDerivation d visibleVelocity)
          (p.map C) hiddenPolynomial).map (evalRingHom 0) =
        polynomialTotalDerivation d p
          (hiddenPolynomial.map (evalRingHom 0)) := by
  have hmap : (p.map C).map (evalRingHom 0) = p := by
    ext n
    simp
  exact map_polynomialTotalDerivation
    (polynomialTotalDerivation d visibleVelocity) d (evalRingHom 0)
      (p.map C) p
      (eval_zero_polynomialTotalDerivation d visibleVelocity hvisible)
      hmap

/-- The invariant-divisor specialization commutes with the complete hidden
prolongation tower, not only its first member. -/
theorem map_eval_zero_iterate_hiddenTotalDerivation
    {R : Type*} [CommRing R]
    (d : Derivation ℤ R R) (visibleVelocity p : R[X])
    (hvisible : visibleVelocity.eval 0 = 0) :
    ∀ n hiddenPolynomial,
      (((polynomialTotalDerivation
          (polynomialTotalDerivation d visibleVelocity)
          (p.map C))^[n]) hiddenPolynomial).map (evalRingHom 0) =
        ((polynomialTotalDerivation d p)^[n])
          (hiddenPolynomial.map (evalRingHom 0)) := by
  have hmap : (p.map C).map (evalRingHom 0) = p := by
    ext n
    simp
  exact map_iterate_polynomialTotalDerivation
    (polynomialTotalDerivation d visibleVelocity) d (evalRingHom 0)
      (p.map C) p
      (eval_zero_polynomialTotalDerivation d visibleVelocity hvisible)
      hmap

/-- Aggregated invariant-specialization kernel. -/
theorem differential_polynomial_invariant_specialization_terminal_certificate :
    ∀ {R : Type*} [CommRing R]
      (d : Derivation ℤ R R) (visibleVelocity p : R[X]),
      visibleVelocity.eval 0 = 0 →
      (∀ hiddenPolynomial : R[X][X],
        (polynomialTotalDerivation
            (polynomialTotalDerivation d visibleVelocity)
            (p.map C) hiddenPolynomial).map (evalRingHom 0) =
          polynomialTotalDerivation d p
            (hiddenPolynomial.map (evalRingHom 0))) ∧
      (∀ n hiddenPolynomial,
        (((polynomialTotalDerivation
            (polynomialTotalDerivation d visibleVelocity)
            (p.map C))^[n]) hiddenPolynomial).map (evalRingHom 0) =
          ((polynomialTotalDerivation d p)^[n])
            (hiddenPolynomial.map (evalRingHom 0))) := by
  intro R _ d visibleVelocity p hvisible
  exact ⟨map_eval_zero_hiddenTotalDerivation d visibleVelocity p hvisible,
    map_eval_zero_iterate_hiddenTotalDerivation d visibleVelocity p hvisible⟩

end FormalDifferentialPolynomialInvariantSpecialization
