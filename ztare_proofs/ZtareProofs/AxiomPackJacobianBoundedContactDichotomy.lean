import Mathlib.Tactic

/-!
Arithmetic terminal step for the bounded-contact reduction.

The geometric artifact supplies a commutative square of dominant quotient
maps.  Its horizontal generic degrees are four and three; uniformly bounded
formal source and target coefficients algebraize the vertical maps over
`Q((s))`, with positive generic degrees `h` and `m`.  Multiplicativity gives
`4*h = 3*m`.  This file checks that the target degree is then nontrivial and
at least three, so a determinant-one target map would be a plane Keller
counterexample.
-/

namespace AxiomPackJacobianBoundedContactDichotomy

theorem contact_degree_equation_forces_target_multiple
    (h m : ℕ) (hdegree : 4 * h = 3 * m) :
    ∃ r : ℕ, h = 3 * r ∧ m = 4 * r := by
  have hdivProduct : 3 ∣ 4 * h := ⟨m, hdegree⟩
  have hcoprime : Nat.Coprime 3 4 := by norm_num
  have hdiv : 3 ∣ h := hcoprime.dvd_of_dvd_mul_left hdivProduct
  obtain ⟨r, hr⟩ := hdiv
  refine ⟨r, hr, ?_⟩
  omega

theorem positive_contact_target_degree_at_least_three
    (h m : ℕ) (hpositive : 0 < h) (hdegree : 4 * h = 3 * m) :
    3 ≤ h := by
  obtain ⟨r, hr, _⟩ :=
    contact_degree_equation_forces_target_multiple h m hdegree
  omega

/-- Terminal numerical certificate used after algebraizing one uniformly
bounded compatible contact. -/
theorem bounded_contact_jc2_degree_certificate
    (h m : ℕ) (hpositive : 0 < h) (hdegree : 4 * h = 3 * m) :
    h ≠ 1 ∧ 3 ≤ h := by
  have hthree :=
    positive_contact_target_degree_at_least_three h m hpositive hdegree
  omega

end AxiomPackJacobianBoundedContactDichotomy
