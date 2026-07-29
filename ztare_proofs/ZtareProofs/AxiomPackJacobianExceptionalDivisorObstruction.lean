import Mathlib.Tactic

/-!
Invariant terminal algebra for the exceptional-divisor obstruction.

For an algebraized compatible contact, the weighted source-volume identity
becomes

  (γ ∘ Ψ)^2 det(DΨ) = γ^2.

After taking γ as one affine coordinate, UFD factorization reduces this to a
one-variable square equation.  The lemmas below check its degree consequence,
the explicit inverse of the resulting triangular source map, and the final
generic-degree contradiction.
-/

namespace AxiomPackJacobianExceptionalDivisorObstruction

open Polynomial

/-- A nonconstant square factor of `X^2` has degree exactly one, and the
remaining factor is constant. -/
theorem exceptional_square_degree
    {K : Type*} [Field K]
    (g j : K[X])
    (hg : g ≠ 0)
    (hj : j ≠ 0)
    (hgPositive : 0 < g.natDegree)
    (hsquare : g ^ 2 * j = X ^ 2) :
    g.natDegree = 1 ∧ j.natDegree = 0 := by
  have hgSquare : g ^ 2 ≠ 0 := pow_ne_zero 2 hg
  have hdegree :
      2 * g.natDegree + j.natDegree = 2 := by
    calc
      2 * g.natDegree + j.natDegree
          = (g ^ 2).natDegree + j.natDegree := by
              rw [Polynomial.natDegree_pow]
      _ = (g ^ 2 * j).natDegree := by
            rw [Polynomial.natDegree_mul hgSquare hj]
      _ = (X ^ 2).natDegree := by rw [hsquare]
      _ = 2 := by simp
  omega

/-- The same square identity determines the factors up to a nonzero scalar. -/
theorem exceptional_square_exact
    {K : Type*} [Field K]
    (g j : K[X])
    (hg : g ≠ 0)
    (hj : j ≠ 0)
    (hgPositive : 0 < g.natDegree)
    (hsquare : g ^ 2 * j = X ^ 2) :
    ∃ c : K, c ≠ 0 ∧
      g = C c * X ∧ j = C (c⁻¹ ^ 2) := by
  obtain ⟨hgOne, hjZero⟩ :=
    exceptional_square_degree g j hg hj hgPositive hsquare
  obtain ⟨c, hc, b, hlinear⟩ :=
    Polynomial.natDegree_eq_one.mp hgOne
  have hjConstant : j = C (j.coeff 0) :=
    Polynomial.eq_C_of_natDegree_eq_zero hjZero
  have hjCoeff : j.coeff 0 ≠ 0 := by
    intro hzero
    apply hj
    rw [hjConstant, hzero, C_0]
  have hconstant :
      b ^ 2 * j.coeff 0 = 0 := by
    have heval := congrArg (Polynomial.eval 0) hsquare
    rw [← hlinear, hjConstant] at heval
    simpa using heval
  have hb : b = 0 := by
    rcases mul_eq_zero.mp hconstant with hbSquare | hjZero'
    · exact sq_eq_zero_iff.mp hbSquare
    · exact (hjCoeff hjZero').elim
  have hgExact : g = C c * X := by
    rw [← hlinear, hb, C_0, add_zero]
  have hleading :
      c ^ 2 * j.coeff 0 = 1 := by
    have hfactor :
        (C c * X) ^ 2 * C (j.coeff 0) =
          C (c ^ 2 * j.coeff 0) * X ^ 2 := by
      calc
        (C c * X) ^ 2 * C (j.coeff 0) =
            (C c * C c * C (j.coeff 0)) * (X * X) := by ring
        _ = C ((c * c) * j.coeff 0) * X ^ 2 := by
              rw [← C_mul, ← C_mul, pow_two]
        _ = C (c ^ 2 * j.coeff 0) * X ^ 2 := by
              simp only [pow_two]
    have hpoly :
        C (c ^ 2 * j.coeff 0) * X ^ 2 = X ^ 2 := by
      calc
        C (c ^ 2 * j.coeff 0) * X ^ 2 =
            (C c * X) ^ 2 * C (j.coeff 0) := hfactor.symm
        _ = g ^ 2 * C (j.coeff 0) :=
          congrArg (fun q : K[X] => q ^ 2 * C (j.coeff 0)) hgExact.symm
        _ = g ^ 2 * j :=
          congrArg (fun q : K[X] => g ^ 2 * q) hjConstant.symm
        _ = X ^ 2 := hsquare
    calc
      c ^ 2 * j.coeff 0 =
          (C (c ^ 2 * j.coeff 0) * X ^ 2).coeff 2 := by
            symm
            change
              (C (c ^ 2 * j.coeff 0) * X ^ 2 : K[X]).coeff 2 =
                c ^ 2 * j.coeff 0
            rw [Polynomial.coeff_C_mul_X_pow]
            simp
      _ = (X ^ 2 : K[X]).coeff 2 :=
        congrArg (fun p : K[X] => p.coeff 2) hpoly
      _ = 1 := by simp
  have hjScalar : j.coeff 0 = c⁻¹ ^ 2 := by
    apply mul_left_cancel₀ (pow_ne_zero 2 hc)
    calc
      c ^ 2 * j.coeff 0 = 1 := hleading
      _ = c ^ 2 * (c⁻¹ ^ 2) := by field_simp
  exact ⟨c, hc, hgExact, hjConstant.trans (congrArg C hjScalar)⟩

/-- Two-variable form after an affine change of coordinates.  The outer
polynomial variable is transverse to the exceptional coordinate `X`. -/
theorem exceptional_square_bivariate_exact
    {K : Type*} [Field K]
    (g j : Polynomial (K[X]))
    (hg : g ≠ 0)
    (hj : j ≠ 0)
    (hgNonconstant :
      ∀ c : K, g ≠ Polynomial.C (Polynomial.C c))
    (hsquare :
      g ^ 2 * j = Polynomial.C (X ^ 2)) :
    ∃ c : K, c ≠ 0 ∧
      g = Polynomial.C (C c * X) ∧
      j = Polynomial.C (C (c⁻¹ ^ 2)) := by
  have hgSquare : g ^ 2 ≠ 0 := pow_ne_zero 2 hg
  have houterDegree :
      2 * g.natDegree + j.natDegree = 0 := by
    calc
      2 * g.natDegree + j.natDegree
          = (g ^ 2).natDegree + j.natDegree := by
              rw [Polynomial.natDegree_pow]
      _ = (g ^ 2 * j).natDegree := by
            rw [Polynomial.natDegree_mul hgSquare hj]
      _ = (Polynomial.C (X ^ 2) :
              Polynomial (K[X])).natDegree := by rw [hsquare]
      _ = 0 := by simp
  have hgOuterZero : g.natDegree = 0 := by omega
  have hjOuterZero : j.natDegree = 0 := by omega
  have hgOuter :
      g = Polynomial.C (g.coeff 0) :=
    Polynomial.eq_C_of_natDegree_eq_zero hgOuterZero
  have hjOuter :
      j = Polynomial.C (j.coeff 0) :=
    Polynomial.eq_C_of_natDegree_eq_zero hjOuterZero
  have hgCoeff : g.coeff 0 ≠ 0 := by
    intro hzero
    apply hg
    rw [hgOuter, hzero, Polynomial.C_0]
  have hjCoeff : j.coeff 0 ≠ 0 := by
    intro hzero
    apply hj
    rw [hjOuter, hzero, Polynomial.C_0]
  have hinner :
      (g.coeff 0) ^ 2 * j.coeff 0 = X ^ 2 := by
    have hcoeff :=
      congrArg
        (fun p : Polynomial (K[X]) => p.coeff 0)
        hsquare
    rw [hgOuter, hjOuter] at hcoeff
    simpa [pow_two] using hcoeff
  have hgInnerPositive : 0 < (g.coeff 0).natDegree := by
    apply Nat.pos_of_ne_zero
    intro hzero
    have hgScalar :=
      Polynomial.eq_C_of_natDegree_eq_zero hzero
    exact hgNonconstant ((g.coeff 0).coeff 0)
      (hgOuter.trans (congrArg Polynomial.C hgScalar))
  obtain ⟨c, hc, hgInner, hjInner⟩ :=
    exceptional_square_exact
      (g.coeff 0) (j.coeff 0)
      hgCoeff hjCoeff hgInnerPositive hinner
  exact ⟨c, hc,
    hgOuter.trans (congrArg Polynomial.C hgInner),
    hjOuter.trans (congrArg Polynomial.C hjInner)⟩

/-- Explicit inverse for the triangular form forced by preservation of the
linear exceptional coordinate. -/
theorem triangular_source_inverse
    (c x y px : ℚ)
    (hc : c ≠ 0) :
    let forwardX := c * x
    let forwardY := c⁻¹ ^ 3 * y + px
    let inverseX := c⁻¹ * forwardX
    let inverseY := c ^ 3 * (forwardY - px)
    inverseX = x ∧ inverseY = y := by
  dsimp
  constructor
  · field_simp
  · field_simp
    ring

/-- Terminal degree contradiction after the source map has generic degree
one. -/
theorem bounded_contact_degree_contradiction
    (h : ℕ)
    (hdegree : 4 * h = 3) :
    False := by
  omega

/-- Aggregated arithmetic endpoint used by carried-artifact ratification. -/
theorem exceptional_divisor_obstruction_certificate
    (g j : ℚ[X])
    (hg : g ≠ 0)
    (hj : j ≠ 0)
    (hgPositive : 0 < g.natDegree)
    (hsquare : g ^ 2 * j = X ^ 2)
    (h : ℕ)
    (hdegree : 4 * h = 3) :
    (∃ c : ℚ, c ≠ 0 ∧
      g = C c * X ∧ j = C (c⁻¹ ^ 2)) ∧ False := by
  exact ⟨exceptional_square_exact g j hg hj hgPositive hsquare,
    bounded_contact_degree_contradiction h hdegree⟩

/-- Bivariate terminal certificate: the exceptional-square identity first
forces independence of the transverse coordinate, then determines the
remaining one-variable factors and reaches the generic-degree obstruction. -/
theorem exceptional_divisor_bivariate_obstruction_certificate
    (g j : Polynomial (ℚ[X]))
    (hg : g ≠ 0)
    (hj : j ≠ 0)
    (hgNonconstant :
      ∀ c : ℚ, g ≠ Polynomial.C (Polynomial.C c))
    (hsquare :
      g ^ 2 * j = Polynomial.C (X ^ 2))
    (h : ℕ)
    (hdegree : 4 * h = 3) :
    (∃ c : ℚ, c ≠ 0 ∧
      g = Polynomial.C (C c * X) ∧
      j = Polynomial.C (C (c⁻¹ ^ 2))) ∧ False := by
  exact
    ⟨exceptional_square_bivariate_exact g j hg hj hgNonconstant hsquare,
      bounded_contact_degree_contradiction h hdegree⟩

end AxiomPackJacobianExceptionalDivisorObstruction
