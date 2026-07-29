import Mathlib

/-!
Combinatorial carrier for the graded rank-one Poisson-section theorem in the
Jacobian contact campaign.

A monomial `X^p * Y^q` is represented only by its exponent pair `(p, q)`.
Its cusp weight is `2 * p + 3 * q`.  When

`p * d - q * c ≠ 0`,

the Poisson bracket of exponent pairs `(p, q)` and `(c, d)` has exponent
pair `(p + c - 1, q + d - 1)`.  A graded rank-one section is required to
select this bracket exponent at weight `m + n - 5`.

This file certifies the resulting discrete classification and its
half-slope degree arithmetic.  Three preceding reductions remain in the
pencil argument: monomialization by the simple spectrum of `ad (P * Q)`,
restriction from polynomials to exponent pairs, and promotion from arbitrary
filtered or higher-rank sections to a graded rank-one section.
-/

namespace AxiomPackJacobianMovingPoissonSectionArithmetic

/-- Exponents of a monomial `X^p * Y^q`. -/
@[ext]
structure ExponentPair where
  p : ℕ
  q : ℕ
deriving DecidableEq, Repr

/-- Cusp weight for `wt(X) = 2`, `wt(Y) = 3`. -/
def weight (e : ExponentPair) : ℕ :=
  2 * e.p + 3 * e.q

/-- Ordinary polynomial degree. -/
def ordinaryDegree (e : ExponentPair) : ℕ :=
  e.p + e.q

/-- The numerator of the monomial Poisson-bracket coefficient. -/
def bracketNumerator (e f : ExponentPair) : ℤ :=
  (e.p : ℤ) * f.q - (e.q : ℤ) * f.p

/-- The normalized Poisson-bracket scalar `(p*d - q*c) / 6`. -/
def bracketScalar (e f : ExponentPair) : ℚ :=
  (bracketNumerator e f : ℚ) / 6

/-- A nonzero monomial bracket, stated without integer casts. -/
def BracketNonzero (e f : ExponentPair) : Prop :=
  e.p * f.q ≠ e.q * f.p

theorem bracketNonzero_iff_numerator_ne_zero
    (e f : ExponentPair) :
    BracketNonzero e f ↔ bracketNumerator e f ≠ 0 := by
  rw [BracketNonzero, bracketNumerator, sub_ne_zero]
  norm_cast

theorem bracketNonzero_iff_scalar_ne_zero
    (e f : ExponentPair) :
    BracketNonzero e f ↔ bracketScalar e f ≠ 0 := by
  rw [bracketNonzero_iff_numerator_ne_zero]
  simp [bracketScalar]

/-- Exponent pair of a nonzero monomial bracket. -/
def bracketExponent (e f : ExponentPair) : ExponentPair :=
  ⟨e.p + f.p - 1, e.q + f.q - 1⟩

/-- A graded rank-one monomial section closed under every nonzero bracket. -/
structure GradedMonomialSection where
  term : ℕ → ExponentPair
  graded : ∀ m : ℕ, 5 ≤ m → weight (term m) = m
  closed :
    ∀ m n : ℕ, 5 ≤ m → 5 ≤ n →
      BracketNonzero (term m) (term n) →
        term (m + n - 5) = bracketExponent (term m) (term n)

theorem weight_five_unique
    (e : ExponentPair) (h : weight e = 5) :
    e = ⟨1, 1⟩ := by
  ext <;> simp_all [weight] <;> omega

theorem weight_seven_unique
    (e : ExponentPair) (h : weight e = 7) :
    e = ⟨2, 1⟩ := by
  ext <;> simp_all [weight] <;> omega

theorem weight_six_cases
    (e : ExponentPair) (h : weight e = 6) :
    e = ⟨3, 0⟩ ∨ e = ⟨0, 2⟩ := by
  rcases e with ⟨p, q⟩
  simp only [weight] at h
  simp only [ExponentPair.mk.injEq]
  omega

theorem term_five (s : GradedMonomialSection) :
    s.term 5 = ⟨1, 1⟩ :=
  weight_five_unique _ (s.graded 5 (by norm_num))

theorem term_seven (s : GradedMonomialSection) :
    s.term 7 = ⟨2, 1⟩ :=
  weight_seven_unique _ (s.graded 7 (by norm_num))

theorem term_six_not_y_sq (s : GradedMonomialSection) :
    s.term 6 ≠ ⟨0, 2⟩ := by
  intro h6
  have h7 := term_seven s
  have h8 : s.term 8 = ⟨1, 2⟩ := by
    have hn : BracketNonzero (s.term 6) (s.term 7) := by
      rw [h6, h7]
      norm_num [BracketNonzero]
    have hc := s.closed 6 7 (by norm_num) (by norm_num) hn
    simpa [h6, h7, bracketExponent] using hc
  have h9 : s.term 9 = ⟨0, 3⟩ := by
    have hn : BracketNonzero (s.term 6) (s.term 8) := by
      rw [h6, h8]
      norm_num [BracketNonzero]
    have hc := s.closed 6 8 (by norm_num) (by norm_num) hn
    simpa [h6, h8, bracketExponent] using hc
  have h10 : s.term 10 = ⟨2, 2⟩ := by
    have hn : BracketNonzero (s.term 7) (s.term 8) := by
      rw [h7, h8]
      norm_num [BracketNonzero]
    have hc := s.closed 7 8 (by norm_num) (by norm_num) hn
    simpa [h7, h8, bracketExponent] using hc
  have h12a : s.term 12 = ⟨3, 2⟩ := by
    have hn : BracketNonzero (s.term 7) (s.term 10) := by
      rw [h7, h10]
      norm_num [BracketNonzero]
    have hc := s.closed 7 10 (by norm_num) (by norm_num) hn
    simpa [h7, h10, bracketExponent] using hc
  have h12b : s.term 12 = ⟨0, 4⟩ := by
    have hn : BracketNonzero (s.term 8) (s.term 9) := by
      rw [h8, h9]
      norm_num [BracketNonzero]
    have hc := s.closed 8 9 (by norm_num) (by norm_num) hn
    simpa [h8, h9, bracketExponent] using hc
  rw [h12a] at h12b
  norm_num at h12b

theorem term_six (s : GradedMonomialSection) :
    s.term 6 = ⟨3, 0⟩ := by
  rcases weight_six_cases _ (s.graded 6 (by norm_num)) with h | h
  · exact h
  · exact (term_six_not_y_sq s h).elim

theorem even_term_succ
    (s : GradedMonomialSection) (a : ℕ) (ha : 3 ≤ a)
    (hterm : s.term (2 * a) = ⟨a, 0⟩) :
    s.term (2 * (a + 1)) = ⟨a + 1, 0⟩ := by
  have h7 := term_seven s
  have hn : BracketNonzero (s.term (2 * a)) (s.term 7) := by
    rw [hterm, h7]
    simp only [BracketNonzero]
    omega
  have hc :=
    s.closed (2 * a) 7 (by omega) (by norm_num) hn
  have hw : 2 * a + 7 - 5 = 2 * (a + 1) := by omega
  have he :
      bracketExponent (s.term (2 * a)) (s.term 7) =
        ⟨a + 1, 0⟩ := by
    rw [hterm, h7]
    ext <;> simp [bracketExponent]
  rw [hw, he] at hc
  exact hc

theorem even_term
    (s : GradedMonomialSection) (a : ℕ) (ha : 3 ≤ a) :
    s.term (2 * a) = ⟨a, 0⟩ := by
  induction a, ha using Nat.le_induction with
  | base =>
      simpa using term_six s
  | succ a ha ih =>
      exact even_term_succ s a ha ih

theorem odd_term
    (s : GradedMonomialSection) (a : ℕ) (ha : 2 ≤ a) :
    s.term (2 * a + 1) = ⟨a - 1, 1⟩ := by
  have hw := s.graded (2 * a + 1) (by omega)
  have hq : 0 < (s.term (2 * a + 1)).q := by
    by_contra h
    have hzero : (s.term (2 * a + 1)).q = 0 :=
      Nat.eq_zero_of_not_pos h
    simp only [weight, hzero, mul_zero, add_zero] at hw
    omega
  have h6 := term_six s
  have hn :
      BracketNonzero (s.term 6) (s.term (2 * a + 1)) := by
    rw [h6]
    simp only [BracketNonzero]
    omega
  have hc :=
    s.closed 6 (2 * a + 1) (by norm_num) (by omega) hn
  have htarget : 6 + (2 * a + 1) - 5 = 2 * (a + 1) := by omega
  have heven := even_term s (a + 1) (by omega)
  rw [htarget, heven, h6] at hc
  apply ExponentPair.ext
  · have hp := congrArg ExponentPair.p hc
    change a + 1 =
      3 + (s.term (2 * a + 1)).p - 1 at hp
    change (s.term (2 * a + 1)).p = a - 1
    omega
  · have hq' := congrArg ExponentPair.q hc
    change 0 =
      0 + (s.term (2 * a + 1)).q - 1 at hq'
    change (s.term (2 * a + 1)).q = 1
    omega

theorem odd_term_of_weight
    (s : GradedMonomialSection) (m : ℕ)
    (hm : 5 ≤ m) (hodd : Odd m) :
    s.term m = ⟨(m - 3) / 2, 1⟩ := by
  rcases hodd with ⟨a, rfl⟩
  have ha : 2 ≤ a := by omega
  rw [odd_term s a ha]
  congr 1
  omega

theorem ordinary_degree_eq_half
    (s : GradedMonomialSection) (m : ℕ) (hm : 5 ≤ m) :
    ordinaryDegree (s.term m) = m / 2 := by
  rcases Nat.even_or_odd' m with ⟨a, h | h⟩
  · subst m
    have ha : 3 ≤ a := by omega
    rw [even_term s a ha]
    simp [ordinaryDegree]
  · subst m
    have ha : 2 ≤ a := by omega
    rw [odd_term s a ha]
    simp [ordinaryDegree]
    omega

/-- Exponent pair of the half-slope section at an even weight. -/
def evenPair (a : ℕ) : ExponentPair :=
  ⟨a, 0⟩

/-- Exponent pair of the half-slope section at an odd weight `2a + 1`. -/
def oddPair (a : ℕ) : ExponentPair :=
  ⟨a - 1, 1⟩

theorem evenPair_weight (a : ℕ) :
    weight (evenPair a) = 2 * a := by
  simp [weight, evenPair]

theorem oddPair_weight (a : ℕ) (ha : 1 ≤ a) :
    weight (oddPair a) = 2 * a + 1 := by
  simp [weight, oddPair]
  omega

theorem evenPair_degree (a : ℕ) :
    ordinaryDegree (evenPair a) = a := by
  simp [ordinaryDegree, evenPair]

theorem oddPair_degree (a : ℕ) (ha : 1 ≤ a) :
    ordinaryDegree (oddPair a) = a := by
  simp [ordinaryDegree, oddPair]
  omega

theorem even_odd_bracket_exponent
    (a b : ℕ) (ha : 1 ≤ a) (hb : 1 ≤ b) :
    bracketExponent (evenPair a) (oddPair b) =
      evenPair (a + b - 2) := by
  apply ExponentPair.ext
  · simp [bracketExponent, evenPair, oddPair]
    omega
  · simp [bracketExponent, evenPair, oddPair]

theorem odd_odd_bracket_exponent
    (a b : ℕ) (ha : 2 ≤ a) (hb : 2 ≤ b) :
    bracketExponent (oddPair a) (oddPair b) =
      oddPair (a + b - 2) := by
  apply ExponentPair.ext
  · simp [bracketExponent, oddPair]
    omega
  · simp [bracketExponent, oddPair]

theorem odd_even_bracket_exponent
    (a b : ℕ) (ha : 1 ≤ a) (hb : 1 ≤ b) :
    bracketExponent (oddPair a) (evenPair b) =
      evenPair (a + b - 2) := by
  apply ExponentPair.ext
  · simp [bracketExponent, evenPair, oddPair]
    omega
  · simp [bracketExponent, evenPair, oddPair]

theorem even_even_bracket_numerator (a b : ℕ) :
    bracketNumerator (evenPair a) (evenPair b) = 0 := by
  simp [bracketNumerator, evenPair]

theorem even_odd_bracket_numerator
    (a b : ℕ) :
    bracketNumerator (evenPair a) (oddPair b) = a := by
  simp [bracketNumerator, evenPair, oddPair]

theorem odd_even_bracket_numerator
    (a b : ℕ) :
    bracketNumerator (oddPair a) (evenPair b) = -(b : ℤ) := by
  simp [bracketNumerator, evenPair, oddPair]

theorem odd_odd_bracket_numerator
    (a b : ℕ) (ha : 1 ≤ a) (hb : 1 ≤ b) :
    bracketNumerator (oddPair a) (oddPair b) =
      (a : ℤ) - b := by
  simp [bracketNumerator, oddPair, Nat.cast_sub ha, Nat.cast_sub hb]

theorem even_even_bracket_scalar (a b : ℕ) :
    bracketScalar (evenPair a) (evenPair b) = 0 := by
  simp [bracketScalar, even_even_bracket_numerator]

theorem even_odd_bracket_scalar (a b : ℕ) :
    bracketScalar (evenPair a) (oddPair b) = (a : ℚ) / 6 := by
  simp [bracketScalar, even_odd_bracket_numerator]

theorem odd_even_bracket_scalar (a b : ℕ) :
    bracketScalar (oddPair a) (evenPair b) = -(b : ℚ) / 6 := by
  simp [bracketScalar, odd_even_bracket_numerator]

theorem odd_odd_bracket_scalar
    (a b : ℕ) (ha : 1 ≤ a) (hb : 1 ≤ b) :
    bracketScalar (oddPair a) (oddPair b) =
      ((a : ℚ) - b) / 6 := by
  rw [bracketScalar, odd_odd_bracket_numerator a b ha hb]
  push_cast
  rfl

/-- The parity representative at every weight.  Only weights at least five
are used by the graded section. -/
def halfSlopeTerm (m : ℕ) : ExponentPair :=
  if m % 2 = 0 then evenPair (m / 2) else oddPair (m / 2)

@[simp]
theorem halfSlopeTerm_even (a : ℕ) :
    halfSlopeTerm (2 * a) = evenPair a := by
  simp [halfSlopeTerm]

@[simp]
theorem halfSlopeTerm_odd (a : ℕ) :
    halfSlopeTerm (2 * a + 1) = oddPair a := by
  simp [halfSlopeTerm]
  congr 1
  omega

/-- The parity representatives form a graded rank-one monomial section. -/
def halfSlopeSection : GradedMonomialSection where
  term := halfSlopeTerm
  graded := by
    intro m hm
    rcases Nat.even_or_odd' m with ⟨a, h | h⟩
    · subst m
      simpa using evenPair_weight a
    · subst m
      have ha : 2 ≤ a := by omega
      simpa using oddPair_weight a (by omega)
  closed := by
    intro m n hm hn hnonzero
    rcases Nat.even_or_odd' m with ⟨a, ha | ha⟩
    · rcases Nat.even_or_odd' n with ⟨b, hb | hb⟩
      · subst m
        subst n
        simp [halfSlopeTerm, BracketNonzero, evenPair] at hnonzero
      · subst m
        subst n
        have ha' : 3 ≤ a := by omega
        have hb' : 2 ≤ b := by omega
        have htarget :
            2 * a + (2 * b + 1) - 5 = 2 * (a + b - 2) := by
          omega
        rw [htarget, halfSlopeTerm_even, halfSlopeTerm_even,
          halfSlopeTerm_odd]
        exact (even_odd_bracket_exponent a b (by omega) (by omega)).symm
    · rcases Nat.even_or_odd' n with ⟨b, hb | hb⟩
      · subst m
        subst n
        have ha' : 2 ≤ a := by omega
        have hb' : 3 ≤ b := by omega
        have htarget :
            (2 * a + 1) + 2 * b - 5 = 2 * (a + b - 2) := by
          omega
        rw [htarget, halfSlopeTerm_even, halfSlopeTerm_odd,
          halfSlopeTerm_even]
        exact (odd_even_bracket_exponent a b (by omega) (by omega)).symm
      · subst m
        subst n
        have ha' : 2 ≤ a := by omega
        have hb' : 2 ≤ b := by omega
        have htarget :
            (2 * a + 1) + (2 * b + 1) - 5 =
              2 * (a + b - 2) + 1 := by
          omega
        rw [htarget, halfSlopeTerm_odd, halfSlopeTerm_odd,
          halfSlopeTerm_odd]
        exact (odd_odd_bracket_exponent a b ha' hb').symm

theorem halfSlopeSection_exists :
    Nonempty GradedMonomialSection :=
  ⟨halfSlopeSection⟩

/-- Terminal combinatorial certificate for the unique half-slope graded
rank-one section. -/
theorem moving_poisson_section_arithmetic_terminal_certificate
    (s : GradedMonomialSection) :
    s.term 5 = ⟨1, 1⟩ ∧
      s.term 6 = ⟨3, 0⟩ ∧
      s.term 7 = ⟨2, 1⟩ ∧
      (∀ a : ℕ, 3 ≤ a → s.term (2 * a) = ⟨a, 0⟩) ∧
      (∀ a : ℕ, 2 ≤ a →
        s.term (2 * a + 1) = ⟨a - 1, 1⟩) ∧
      (∀ m : ℕ, 5 ≤ m →
        ordinaryDegree (s.term m) = m / 2) := by
  exact ⟨term_five s, term_six s, term_seven s,
    even_term s, odd_term s, ordinary_degree_eq_half s⟩

end AxiomPackJacobianMovingPoissonSectionArithmetic
