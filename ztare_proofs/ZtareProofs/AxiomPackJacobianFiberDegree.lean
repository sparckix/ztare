import Mathlib

/-!
Kernel-checkable algebraic certificate for the inverse-fiber mechanism of the
public dimension-three Keller counterexample and its cubic weighted-lift
line.

In the canonical multivariate presentation, variables `0,1,2` are
respectively `Q,P,w`.  Viewing `Q` as the outer variable makes the fiber
polynomial monic linear and hence irreducible.  Viewing `w` as the outer
variable exposes the degree drop from four to three at `s = 0`.
-/

namespace AxiomPackJacobianFiberDegree

open MvPolynomial

noncomputable section

@[simp] private theorem finCasesPolynomial_one :
    Fin.cases (Polynomial.X : Polynomial (MvPolynomial (Fin 2) ℚ))
      (fun k : Fin 2 => Polynomial.C (MvPolynomial.X k)) (1 : Fin 3) =
        Polynomial.C (MvPolynomial.X 0) := rfl

@[simp] private theorem finCasesPolynomial_two :
    Fin.cases (Polynomial.X : Polynomial (MvPolynomial (Fin 2) ℚ))
      (fun k : Fin 2 => Polynomial.C (MvPolynomial.X k)) (2 : Fin 3) =
        Polynomial.C (MvPolynomial.X 1) := rfl

/-- The inverse-fiber equation `R_s(w) - wP + Q`. -/
def fiberMv (s : ℚ) : MvPolynomial (Fin 3) ℚ :=
  X 0 - X 1 * X 2 + MvPolynomial.C (s / 4) * X 2 ^ 4
    - MvPolynomial.C (1 + s / 2) * X 2 ^ 3
    + MvPolynomial.C (1 + s / 4) * X 2 ^ 2

/-- Put `Q` outside, leaving inner variables `(P,w)`. -/
def fiberAsQ (s : ℚ) : Polynomial (MvPolynomial (Fin 2) ℚ) :=
  MvPolynomial.finSuccEquiv ℚ 2 (fiberMv s)

/-- The coefficient independent of the outer `Q` variable. -/
def qRemainder (s : ℚ) : MvPolynomial (Fin 2) ℚ :=
  -(X 0 * X 1) + MvPolynomial.C (s / 4) * X 1 ^ 4
    - MvPolynomial.C (1 + s / 2) * X 1 ^ 3
    + MvPolynomial.C (1 + s / 4) * X 1 ^ 2

theorem fiberAsQ_eq (s : ℚ) :
    fiberAsQ s = Polynomial.X + Polynomial.C (qRemainder s) := by
  simp [fiberAsQ, fiberMv, qRemainder,
    MvPolynomial.finSuccEquiv_apply]
  ring

/-- The coefficient-one dependence on the independent target variable `Q`
prevents a nontrivial factorization over `ℚ[P,w,Q]`. -/
theorem fiberAsQ_irreducible (s : ℚ) : Irreducible (fiberAsQ s) := by
  rw [fiberAsQ_eq]
  simpa [sub_eq_add_neg] using
    (Polynomial.irreducible_X_sub_C (-(qRemainder s)))

/-- Canonical multivariate form of the same irreducibility certificate. -/
theorem fiberMv_irreducible (s : ℚ) : Irreducible (fiberMv s) := by
  exact (MulEquiv.irreducible_iff
    (MvPolynomial.finSuccEquiv ℚ 2).toMulEquiv).mp
      (fiberAsQ_irreducible s)

/-- Put `w` outside, leaving inner variables `(P,Q)`. -/
def wPresentationEquiv :
    MvPolynomial (Fin 3) ℚ ≃ₐ[ℚ] Polynomial (MvPolynomial (Fin 2) ℚ) :=
  (MvPolynomial.renameEquiv ℚ Fin.revPerm).trans
    (MvPolynomial.finSuccEquiv ℚ 2)

def fiberAsW (s : ℚ) : Polynomial (MvPolynomial (Fin 2) ℚ) :=
  Polynomial.monomial 4 (MvPolynomial.C (s / 4))
    + Polynomial.monomial 3 (-MvPolynomial.C (1 + s / 2))
    + Polynomial.monomial 2 (MvPolynomial.C (1 + s / 4))
    + Polynomial.monomial 1 (-MvPolynomial.X 0)
    + Polynomial.monomial 0 (MvPolynomial.X 1)

theorem wPresentation_eq (s : ℚ) :
    wPresentationEquiv (fiberMv s) = fiberAsW s := by
  simp [wPresentationEquiv, fiberMv, fiberAsW,
    MvPolynomial.renameEquiv_apply, MvPolynomial.finSuccEquiv_apply,
    ← Polynomial.C_mul_X_pow_eq_monomial]
  ring

theorem fiberAsW_irreducible (s : ℚ) : Irreducible (fiberAsW s) := by
  rw [← wPresentation_eq]
  exact (MulEquiv.irreducible_iff wPresentationEquiv.toMulEquiv).mpr
    (fiberMv_irreducible s)

theorem fiberAsW_coeff_four (s : ℚ) :
    (fiberAsW s).coeff 4 = MvPolynomial.C (s / 4) := by
  simp [fiberAsW, Polynomial.coeff_monomial]

theorem fiberAsW_coeff_three_at_zero :
    (fiberAsW 0).coeff 3 = -1 := by
  simp [fiberAsW, Polynomial.coeff_monomial]

theorem fiberAsW_natDegree_le_four (s : ℚ) :
    (fiberAsW s).natDegree ≤ 4 := by
  rw [Polynomial.natDegree_le_iff_coeff_eq_zero]
  intro n hn
  have h0 : n ≠ 0 := by omega
  have h1' : 1 ≠ n := by omega
  have h2' : 2 ≠ n := by omega
  have h3' : 3 ≠ n := by omega
  have h4' : 4 ≠ n := by omega
  simp [fiberAsW, Polynomial.coeff_monomial, Polynomial.coeff_C,
    h0, h1', h2', h3', h4']

/-- Every nonzero parameter has generic inverse degree four. -/
theorem fiberAsW_natDegree_of_ne_zero (s : ℚ) (hs : s ≠ 0) :
    (fiberAsW s).natDegree = 4 := by
  apply Polynomial.natDegree_eq_of_le_of_coeff_ne_zero
  · exact fiberAsW_natDegree_le_four s
  · rw [fiberAsW_coeff_four]
    simp [hs]

/-- The public seed loses its quartic term but retains a cubic term. -/
theorem fiberAsW_natDegree_zero : (fiberAsW 0).natDegree = 3 := by
  apply Polynomial.natDegree_eq_of_le_of_coeff_ne_zero
  · simp [fiberAsW]
    compute_degree
  · rw [fiberAsW_coeff_three_at_zero]
    norm_num

/-- Exact evaluation of the displayed inverse equation. -/
theorem fiberAsW_eval (s P Q w : ℚ) :
    Polynomial.eval w
      ((fiberAsW s).map (MvPolynomial.eval ![P, Q])) =
      -P * w + Q + s * w ^ 4 / 4 - (1 + s / 2) * w ^ 3
        + (1 + s / 4) * w ^ 2 := by
  simp [fiberAsW]
  ring

/-- The coefficient ring for the two independent target variables. -/
abbrev TargetRing := MvPolynomial (Fin 2) ℚ

/-- Rational-function-field presentation of the inverse equation. -/
def fiberOverTargetField (s : ℚ) : Polynomial (FractionRing TargetRing) :=
  (fiberAsW s).map (algebraMap TargetRing (FractionRing TargetRing))

/-- The inverse polynomial stays irreducible after passing from
`ℚ[P,Q]` to its fraction field `ℚ(P,Q)`. -/
theorem fiberOverTargetField_irreducible (s : ℚ) :
    Irreducible (fiberOverTargetField s) := by
  have hi : Irreducible (fiberAsW s) := fiberAsW_irreducible s
  have hdegree : (fiberAsW s).natDegree ≠ 0 := by
    by_cases hs : s = 0
    · subst s
      rw [fiberAsW_natDegree_zero]
      norm_num
    · rw [fiberAsW_natDegree_of_ne_zero s hs]
      norm_num
  exact (hi.isPrimitive hdegree).irreducible_iff_irreducible_map_fraction_map.mp hi

/-- Canonical combined certificate: the target-function-field fiber is
irreducible throughout the line, cubic at the public seed, and quartic at
every nonzero parameter. -/
theorem inverse_fiber_degree_certificate :
    Irreducible (fiberOverTargetField 0) ∧
      (fiberOverTargetField 0).natDegree = 3 ∧
      ∀ s : ℚ, s ≠ 0 →
        Irreducible (fiberOverTargetField s) ∧
          (fiberOverTargetField s).natDegree = 4 := by
  refine ⟨fiberOverTargetField_irreducible 0, ?_, ?_⟩
  · rw [fiberOverTargetField,
      Polynomial.natDegree_map_eq_of_injective
        (IsFractionRing.injective TargetRing (FractionRing TargetRing))]
    exact fiberAsW_natDegree_zero
  · intro s hs
    refine ⟨fiberOverTargetField_irreducible s, ?_⟩
    rw [fiberOverTargetField,
      Polynomial.natDegree_map_eq_of_injective
        (IsFractionRing.injective TargetRing (FractionRing TargetRing))]
    exact fiberAsW_natDegree_of_ne_zero s hs

end

end AxiomPackJacobianFiberDegree
