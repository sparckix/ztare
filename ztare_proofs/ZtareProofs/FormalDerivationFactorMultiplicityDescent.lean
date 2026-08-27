import Mathlib.RingTheory.Derivation.Basic
import Mathlib.Tactic

/-!
# One-step multiplicity descent under a derivation

If `H = h^m u` with positive `m`, Leibniz factors `D H` by `h^(m-1)`.
The residual bracket is `m (D h) u + h (D u)`.  Thus a non-Darboux prime
factor loses one unit of multiplicity whenever its derivative and cofactor
remain nonzero modulo that factor.

The exact identity is independent of unique factorization.  Prime-factor
nonvanishing and finite descent are downstream consumers.
-/

namespace FormalDerivationFactorMultiplicityDescent

variable {R : Type*} [CommRing R]

/-- Exact factorization of the derivative of a positive power times a
cofactor. -/
theorem derivation_pow_mul_factorization
    (D : Derivation ℤ R R) (h u : R) (multiplicity : ℕ)
    (hpositive : 0 < multiplicity) :
    D (h ^ multiplicity * u) =
      h ^ (multiplicity - 1) *
        (multiplicity • (D h * u) + h * D u) := by
  rw [Derivation.leibniz, Derivation.leibniz_pow]
  have hpower : h ^ multiplicity = h ^ (multiplicity - 1) * h := by
    have hmultiplicity : multiplicity = (multiplicity - 1) + 1 := by omega
    calc
      h ^ multiplicity = h ^ ((multiplicity - 1) + 1) := by
        exact congrArg (fun exponent : ℕ ↦ h ^ exponent) hmultiplicity
      _ = h ^ (multiplicity - 1) * h := pow_succ _ _
  rw [hpower]
  simp only [nsmul_eq_mul]
  ring

/-- The factorization displayed as a one-step descent witness. -/
theorem exists_derivation_factor_descent_witness
    (D : Derivation ℤ R R) (h u : R) (multiplicity : ℕ)
    (hpositive : 0 < multiplicity) :
    ∃ residual,
      D (h ^ multiplicity * u) =
        h ^ (multiplicity - 1) * residual ∧
      residual = multiplicity • (D h * u) + h * D u := by
  refine ⟨multiplicity • (D h * u) + h * D u, ?_, rfl⟩
  exact derivation_pow_mul_factorization D h u multiplicity hpositive

/-- A prime factor whose own derivative and cofactor are nonzero modulo that
factor loses one unit of multiplicity after one derivation.  The natural
scalar is kept as an explicit nondivisibility premise; over a polynomial ring
in characteristic zero it is a nonzero unit. -/
theorem prime_pow_not_dvd_derivation_pow_mul
    [IsDomain R]
    (D : Derivation ℤ R R) (h u : R) (multiplicity : ℕ)
    (hpositive : 0 < multiplicity)
    (hprime : Prime h)
    (hscalar : ¬h ∣ (multiplicity : R))
    (hderivative : ¬h ∣ D h)
    (hcofactor : ¬h ∣ u) :
    ¬h ^ multiplicity ∣ D (h ^ multiplicity * u) := by
  intro hdvd
  rcases hdvd with ⟨quotient, hquotient⟩
  have hpower : h ^ multiplicity = h ^ (multiplicity - 1) * h := by
    have hmultiplicity : multiplicity = (multiplicity - 1) + 1 := by omega
    calc
      h ^ multiplicity = h ^ ((multiplicity - 1) + 1) :=
        congrArg (fun exponent : ℕ ↦ h ^ exponent) hmultiplicity
      _ = h ^ (multiplicity - 1) * h := pow_succ _ _
  let residual := multiplicity • (D h * u) + h * D u
  have hfactorization :
      D (h ^ multiplicity * u) = h ^ (multiplicity - 1) * residual := by
    exact derivation_pow_mul_factorization D h u multiplicity hpositive
  have hpowerNonzero : h ^ (multiplicity - 1) ≠ 0 :=
    pow_ne_zero _ hprime.ne_zero
  have hresidual : residual = h * quotient := by
    apply mul_left_cancel₀ hpowerNonzero
    calc
      h ^ (multiplicity - 1) * residual =
          D (h ^ multiplicity * u) := hfactorization.symm
      _ = h ^ multiplicity * quotient := hquotient
      _ = h ^ (multiplicity - 1) * (h * quotient) := by
        rw [hpower]
        ring
  have hmain : h ∣ multiplicity • (D h * u) := by
    refine ⟨quotient - D u, ?_⟩
    calc
      multiplicity • (D h * u) =
          residual - h * D u := by
        dsimp [residual]
        abel
      _ = h * quotient - h * D u := by rw [hresidual]
      _ = h * (quotient - D u) := by ring
  have hmain' : h ∣ (multiplicity : R) * (D h * u) := by
    simpa only [nsmul_eq_mul] using hmain
  rcases hprime.dvd_mul.mp hmain' with hscalarDvd | hderivativeCofactor
  · exact hscalar hscalarDvd
  · rcases hprime.dvd_mul.mp hderivativeCofactor with
      hderivativeDvd | hcofactorDvd
    · exact hderivative hderivativeDvd
    · exact hcofactor hcofactorDvd

/-- The successive cofactors left after peeling one copy of `h` at each
derivative.  The ambient multiplicity is fixed; at step `j` the scalar is
`multiplicity - j`. -/
def descentCofactor
    (D : Derivation ℤ R R) (h : R) (multiplicity : ℕ) (u : R) :
    ℕ → R
  | 0 => u
  | step + 1 =>
      (multiplicity - step) •
          (D h * descentCofactor D h multiplicity u step) +
        h * D (descentCofactor D h multiplicity u step)

/-- Iterating the one-step identity through the initial multiplicity gives
the exact remaining power and recursive cofactor. -/
theorem iterate_derivation_pow_mul_factorization
    (D : Derivation ℤ R R) (h u : R) (multiplicity : ℕ) :
    ∀ step ≤ multiplicity,
      (D : R → R)^[step] (h ^ multiplicity * u) =
        h ^ (multiplicity - step) *
          descentCofactor D h multiplicity u step := by
  intro step hstep
  induction step with
  | zero =>
      simp [descentCofactor]
  | succ step inductionHypothesis =>
      have hstepWeak : step ≤ multiplicity :=
        le_trans (Nat.le_succ step) hstep
      have hstepStrict : step < multiplicity :=
        Nat.lt_of_succ_le hstep
      have hpositive : 0 < multiplicity - step :=
        Nat.sub_pos_of_lt hstepStrict
      rw [Function.iterate_succ_apply']
      rw [inductionHypothesis hstepWeak]
      rw [derivation_pow_mul_factorization D h
        (descentCofactor D h multiplicity u step)
        (multiplicity - step) hpositive]
      simp only [descentCofactor]
      congr 1

/-- Under the prime, non-Darboux, and characteristic-scalar hypotheses, no
recursive cofactor regains a copy of `h`. -/
theorem prime_not_dvd_descentCofactor
    [IsDomain R]
    (D : Derivation ℤ R R) (h u : R) (multiplicity : ℕ)
    (hprime : Prime h)
    (hscalars : ∀ scalar : ℕ, 0 < scalar → scalar ≤ multiplicity →
      ¬h ∣ (scalar : R))
    (hderivative : ¬h ∣ D h)
    (hcofactor : ¬h ∣ u) :
    ∀ step ≤ multiplicity,
      ¬h ∣ descentCofactor D h multiplicity u step := by
  intro step hstep
  induction step with
  | zero =>
      simpa [descentCofactor] using hcofactor
  | succ step inductionHypothesis =>
      have hstepWeak : step ≤ multiplicity :=
        le_trans (Nat.le_succ step) hstep
      have hstepStrict : step < multiplicity :=
        Nat.lt_of_succ_le hstep
      have hscalarPositive : 0 < multiplicity - step :=
        Nat.sub_pos_of_lt hstepStrict
      have hscalarBound : multiplicity - step ≤ multiplicity :=
        Nat.sub_le _ _
      intro hdvd
      have hmain :
          h ∣ (multiplicity - step) •
            (D h * descentCofactor D h multiplicity u step) := by
        rcases hdvd with ⟨quotient, hquotient⟩
        refine ⟨quotient - D (descentCofactor D h multiplicity u step), ?_⟩
        simp only [descentCofactor] at hquotient ⊢
        calc
          (multiplicity - step) •
                (D h * descentCofactor D h multiplicity u step) =
              ((multiplicity - step) •
                  (D h * descentCofactor D h multiplicity u step) +
                h * D (descentCofactor D h multiplicity u step)) -
                  h * D (descentCofactor D h multiplicity u step) := by
            abel
          _ = h * quotient -
                h * D (descentCofactor D h multiplicity u step) := by
            rw [hquotient]
          _ = h *
                (quotient - D
                  (descentCofactor D h multiplicity u step)) := by ring
      have hmain' :
          h ∣ ((multiplicity - step : ℕ) : R) *
            (D h * descentCofactor D h multiplicity u step) := by
        simpa only [nsmul_eq_mul] using hmain
      rcases hprime.dvd_mul.mp hmain' with hscalarDvd | hrestDvd
      · exact (hscalars (multiplicity - step) hscalarPositive
          hscalarBound) hscalarDvd
      · rcases hprime.dvd_mul.mp hrestDvd with
          hderivativeDvd | hcofactorDvd
        · exact hderivative hderivativeDvd
        · exact (inductionHypothesis hstepWeak) hcofactorDvd

/-- A non-Darboux prime disappears by the derivative indexed by its exact
initial multiplicity. -/
theorem prime_not_dvd_iterate_at_multiplicity
    [IsDomain R]
    (D : Derivation ℤ R R) (h u : R) (multiplicity : ℕ)
    (hprime : Prime h)
    (hscalars : ∀ scalar : ℕ, 0 < scalar → scalar ≤ multiplicity →
      ¬h ∣ (scalar : R))
    (hderivative : ¬h ∣ D h)
    (hcofactor : ¬h ∣ u) :
    ¬h ∣ (D : R → R)^[multiplicity] (h ^ multiplicity * u) := by
  rw [iterate_derivation_pow_mul_factorization D h u multiplicity
    multiplicity le_rfl, Nat.sub_self, pow_zero, one_mul]
  exact prime_not_dvd_descentCofactor D h u multiplicity hprime
    hscalars hderivative hcofactor multiplicity le_rfl

/-- Contrapositive finite Darboux alternative: persistence through the exact
initial multiplicity forces a prime to divide its own derivative. -/
theorem prime_dvd_derivative_of_persists_to_multiplicity
    [IsDomain R]
    (D : Derivation ℤ R R) (h u : R) (multiplicity : ℕ)
    (hprime : Prime h)
    (hscalars : ∀ scalar : ℕ, 0 < scalar → scalar ≤ multiplicity →
      ¬h ∣ (scalar : R))
    (hcofactor : ¬h ∣ u)
    (hpersistent :
      h ∣ (D : R → R)^[multiplicity] (h ^ multiplicity * u)) :
    h ∣ D h := by
  by_contra hderivative
  exact (prime_not_dvd_iterate_at_multiplicity D h u multiplicity
    hprime hscalars hderivative hcofactor) hpersistent

/-- Aggregated factor-multiplicity descent certificate. -/
theorem derivation_factor_multiplicity_descent_terminal_certificate :
    ∀ (D : Derivation ℤ R R) (h u : R) (multiplicity : ℕ),
      0 < multiplicity →
      D (h ^ multiplicity * u) =
        h ^ (multiplicity - 1) *
          (multiplicity • (D h * u) + h * D u) ∧
      ∃ residual,
        D (h ^ multiplicity * u) =
          h ^ (multiplicity - 1) * residual ∧
        residual = multiplicity • (D h * u) + h * D u := by
  intro D h u multiplicity hpositive
  exact ⟨derivation_pow_mul_factorization D h u multiplicity hpositive,
    exists_derivation_factor_descent_witness
      D h u multiplicity hpositive⟩

/-- Aggregated prime-factor nondivisibility branch. -/
theorem derivation_prime_factor_multiplicity_drop_terminal_certificate
    [IsDomain R] :
    ∀ (D : Derivation ℤ R R) (h u : R) (multiplicity : ℕ),
      0 < multiplicity →
      Prime h →
      (¬h ∣ (multiplicity : R)) →
      (¬h ∣ D h) →
      (¬h ∣ u) →
      ¬h ^ multiplicity ∣ D (h ^ multiplicity * u) := by
  intro D h u multiplicity hpositive hprime hscalar hderivative hcofactor
  exact prime_pow_not_dvd_derivation_pow_mul D h u multiplicity hpositive
    hprime hscalar hderivative hcofactor

/-- Aggregated finite persistent-prime/Darboux alternative. -/
theorem derivation_persistent_prime_darboux_terminal_certificate
    [IsDomain R] :
    ∀ (D : Derivation ℤ R R) (h u : R) (multiplicity : ℕ),
      Prime h →
      (∀ scalar : ℕ, 0 < scalar → scalar ≤ multiplicity →
        ¬h ∣ (scalar : R)) →
      (¬h ∣ u) →
      h ∣ (D : R → R)^[multiplicity] (h ^ multiplicity * u) →
      h ∣ D h := by
  intro D h u multiplicity hprime hscalars hcofactor hpersistent
  exact prime_dvd_derivative_of_persists_to_multiplicity
    D h u multiplicity hprime hscalars hcofactor hpersistent

end FormalDerivationFactorMultiplicityDescent
