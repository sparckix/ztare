import Mathlib.Algebra.Polynomial.Div

/-!
# One-weight irreducible contraction over the coefficient ring

An irreducible polynomial over a domain that consists only of its leading
monomial is either constant or associated to `X`.  The proof stays over the
coefficient ring; in particular, it does not transport irreducibility to a
fraction field.
-/

namespace ZtareProofs.FormalOneWeightIrreducibleContraction

open Polynomial

/-- A one-weight irreducible polynomial over a domain is constant or
associated to the polynomial variable. -/
theorem natDegree_eq_zero_or_associated_X
    {A : Type*} [CommRing A] [IsDomain A]
    (h : A[X]) (hirr : Irreducible h)
    (honeWeight : h = monomial h.natDegree h.leadingCoeff) :
    h.natDegree = 0 ∨ Associated h X := by
  by_cases hdegreeZero : h.natDegree = 0
  · exact Or.inl hdegreeZero
  · right
    have hdegreePositive : 0 < h.natDegree := Nat.pos_of_ne_zero hdegreeZero
    have hroot : h.IsRoot 0 := by
      rw [honeWeight, ← C_mul_X_pow_eq_monomial]
      simp [IsRoot, hdegreePositive.ne']
    have hdegreeOne : h.natDegree = 1 := by
      by_contra hdegreeNotOne
      exact hirr.not_isRoot_of_natDegree_ne_one hdegreeNotOne hroot
    have hfactor : h = C h.leadingCoeff * X := by
      calc
        h = monomial 1 h.leadingCoeff := by simpa [hdegreeOne] using honeWeight
        _ = C h.leadingCoeff * X := C_mul_X_eq_monomial.symm
    have hconstantUnit : IsUnit (C h.leadingCoeff) :=
      (hirr.isUnit_or_isUnit hfactor).resolve_right not_isUnit_X
    rw [hfactor]
    exact associated_unit_mul_left X (C h.leadingCoeff) hconstantUnit

end ZtareProofs.FormalOneWeightIrreducibleContraction
