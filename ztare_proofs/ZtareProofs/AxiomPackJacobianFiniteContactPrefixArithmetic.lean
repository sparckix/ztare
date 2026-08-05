import Mathlib.Tactic

/-!
Arithmetic carrier for the finite positive-contact prefix obstruction.

In the radial-normal chart, the seed pullback of the cusp polynomial has
normal order two.  A positive contact monomial `P^a Q^b D^d C^m` has stable
odd-transfer numerator

`6*a + 9*b + 15*d + 4*m`,

while the twelve boundary classes at positive discriminant depth have
numerator

`21*a + 57*d + 35*m + 9*ell`.

The remaining five exceptional boundary states have a corrected even Magnus
orbit with radial offsets `(2,1,1,1,2)`.  Its bracket multiplier is positive
at every natural adjoint depth, and the corrected cancellation transition
cannot return to an exceptional state at discriminant depth zero.

The contact-valuation identification, completeness of the current solve,
and derivation of the displayed transfer and transition formulas remain in
the deterministic symbolic artifacts.  This file checks the exact seed
identity and the arithmetic terminal used by the finite-prefix argument.
-/

namespace AxiomPackJacobianFiniteContactPrefixArithmetic

/-- First seed component in the radial-normal chart. -/
def seedP (r z : ℚ) : ℚ :=
  -3 / 4 * r ^ 2 + r + z / 2

/-- Second seed component in the radial-normal chart. -/
def seedQ (r z : ℚ) : ℚ :=
  -1 / 4 * r ^ 3 + 1 / 4 * r ^ 2 + r * z / 4

/-- The target cusp polynomial. -/
def cuspC (p q : ℚ) : ℚ :=
  4 * p ^ 3 - p ^ 2 - 18 * p * q + 27 * q ^ 2 + 4 * q

/-- Exact order-two cusp pullback used by the contact valuation argument. -/
theorem seed_cusp_pullback (r z : ℚ) :
    cuspC (seedP r z) (seedQ r z) =
      z ^ 2 * (-9 * r ^ 2 + 12 * r + 8 * z - 4) / 16 := by
  unfold cuspC seedP seedQ
  ring

/-- Stable odd-transfer numerator for `P^a Q^b D^d C^m`. -/
def stableTransferNumerator (a b d m : ℕ) : ℕ :=
  6 * a + 9 * b + 15 * d + 4 * m

theorem stable_transfer_numerator_positive
    (a b d m : ℕ) (hm : 0 < m) :
    0 < stableTransferNumerator a b d m := by
  simp [stableTransferNumerator]
  omega

/-- Positive-discriminant boundary numerator. -/
def boundaryTransferNumerator (a d m ell : ℕ) : ℕ :=
  21 * a + 57 * d + 35 * m + 9 * ell

theorem boundary_transfer_numerator_positive
    (a d m ell : ℕ) (hm : 0 < m) :
    0 < boundaryTransferNumerator a d m ell := by
  simp [boundaryTransferNumerator]
  omega

/-- Twice the limiting source-Hamiltonian rate on a positive-contact
`(a,d,m,ell)` class. -/
def positiveContactTwiceRate (a d m ell : ℕ) : ℕ :=
  7 * a + 19 * d + 15 * m + 3 * ell - 4

/-- Every positive-contact terminal ray has limiting Hamiltonian rate at
least `11/2`, hence strictly above two. -/
theorem positive_contact_rate_above_two
    (a d m ell : ℕ) (hm : 0 < m) :
    11 ≤ positiveContactTwiceRate a d m ell := by
  simp only [positiveContactTwiceRate]
  omega

/-- The exceptional `d=0` boundary states. -/
def ExceptionalState (a ell : ℕ) : Prop :=
  (a = 0 ∧ ell ≤ 3) ∨ (a = 1 ∧ ell = 0)

/-- Corrected maximum-radial offset on the exceptional state set. -/
def exceptionalRadialOffset (ell : ℕ) : ℕ :=
  if ell = 0 then 2 else 1

/-- Positive numerators of the five normalized exceptional amplitudes. -/
def exceptionalAmplitude00Numerator (m : ℕ) : ℕ :=
  m * (81 * m - 46)

def exceptionalAmplitude01Numerator (m : ℕ) : ℕ :=
  (3 * m + 1) * (153 * m ^ 2 + 114 * m + 73)

def exceptionalAmplitude02Numerator (m : ℕ) : ℕ :=
  (3 * m + 2) * (153 * m ^ 2 + 192 * m + 112)

def exceptionalAmplitude03Numerator (m : ℕ) : ℕ :=
  3 * (m + 1) * (153 * m ^ 2 + 270 * m + 169)

def exceptionalAmplitude10AbsNumerator (m : ℕ) : ℕ :=
  (m + 1) * (81 * m + 127)

theorem exceptional_amplitude_numerators_positive
    (m : ℕ) (hm : 0 < m) :
    0 < exceptionalAmplitude00Numerator m ∧
    0 < exceptionalAmplitude01Numerator m ∧
    0 < exceptionalAmplitude02Numerator m ∧
    0 < exceptionalAmplitude03Numerator m ∧
    0 < exceptionalAmplitude10AbsNumerator m := by
  have h00 : 0 < 81 * m - 46 := by omega
  exact ⟨
    Nat.mul_pos hm h00,
    Nat.mul_pos (by omega) (by omega),
    Nat.mul_pos (by omega) (by omega),
    Nat.mul_pos (Nat.mul_pos (by omega) (by omega)) (by omega),
    Nat.mul_pos (by omega) (by omega)⟩

/-- The algebraic resonance equation has no natural adjoint depth.  Here
`R` is the positive radial contribution before the `C^m` factor. -/
theorem odd_orbit_has_no_integral_resonance
    (R m k : ℕ) (hR : 0 < R) :
    2 * (R + m) * k ≠ R + 2 * m := by
  intro hresonance
  cases k with
  | zero =>
      simp at hresonance
      omega
  | succ k =>
      simp only [Nat.mul_succ] at hresonance
      omega

/-- Corrected exceptional even-orbit bracket multiplier. -/
def correctedEvenOrbitMultiplier
    (R m delta k : ℕ) : ℕ :=
  2 * m * delta + 2 * k * (R + m)

theorem corrected_even_orbit_multiplier_positive
    (R m delta k : ℕ) (hm : 0 < m) (hdelta : 0 < delta) :
    0 < correctedEvenOrbitMultiplier R m delta k := by
  have hbase : 0 < 2 * m * delta := by positivity
  simp only [correctedEvenOrbitMultiplier]
  omega

/-- A positive adjoint depth from contact depth at least two exceeds the
maximum contact depth of a finite prefix. -/
theorem positive_orbit_exceeds_contact_maximum
    (M k : ℕ) (hM : 2 ≤ M) (hk : 0 < k) :
    M < M + (M - 1) * k := by
  have hpred : 0 < M - 1 := by omega
  have hproduct : 0 < (M - 1) * k := Nat.mul_pos hpred hk
  omega

/-- The exact direct-cancellation transition has no edge from the five
exceptional depth-zero states back into that same state set. -/
theorem exceptional_transition_exits
    (a ell a' d' ell' k : ℕ)
    (hsource : ExceptionalState a ell)
    (htransition :
      7 * a' + 19 * d' + 3 * ell' =
        7 * a + 3 * ell + 2 * exceptionalRadialOffset ell +
          k * (7 * a + 3 * ell + 11)) :
    0 < d' ∨ ¬ ExceptionalState a' ell' := by
  by_cases hd : 0 < d'
  · exact Or.inl hd
  · right
    intro htarget
    have hdZero : d' = 0 := by omega
    subst d'
    rcases hsource with ⟨ha, hell⟩ | ⟨ha, hell⟩
    · subst a
      rcases htarget with ⟨ha', hell'⟩ | ⟨ha', hell'⟩
      · subst a'
        interval_cases ell <;>
          interval_cases ell' <;>
          simp [exceptionalRadialOffset] at htransition <;>
          omega
      · subst a'
        subst ell'
        interval_cases ell <;>
          simp [exceptionalRadialOffset] at htransition <;>
          omega
    · subst a
      subst ell
      rcases htarget with ⟨ha', hell'⟩ | ⟨ha', hell'⟩
      · subst a'
        interval_cases ell' <;>
          simp [exceptionalRadialOffset] at htransition <;>
          omega
      · subst a'
        subst ell'
        simp [exceptionalRadialOffset] at htransition
        omega

/-- Aggregated arithmetic endpoint for the finite-contact prefix argument. -/
theorem finite_contact_prefix_arithmetic_terminal_certificate :
    (∀ r z : ℚ,
      cuspC (seedP r z) (seedQ r z) =
        z ^ 2 * (-9 * r ^ 2 + 12 * r + 8 * z - 4) / 16) ∧
    (∀ a b d m : ℕ, 0 < m →
      0 < stableTransferNumerator a b d m) ∧
    (∀ a d m ell : ℕ, 0 < m →
      0 < boundaryTransferNumerator a d m ell) ∧
    (∀ a d m ell : ℕ, 0 < m →
      11 ≤ positiveContactTwiceRate a d m ell) ∧
    (∀ R m k : ℕ, 0 < R →
      2 * (R + m) * k ≠ R + 2 * m) ∧
    (∀ m : ℕ, 0 < m →
      0 < exceptionalAmplitude00Numerator m ∧
      0 < exceptionalAmplitude01Numerator m ∧
      0 < exceptionalAmplitude02Numerator m ∧
      0 < exceptionalAmplitude03Numerator m ∧
      0 < exceptionalAmplitude10AbsNumerator m) ∧
    (∀ R m delta k : ℕ, 0 < m → 0 < delta →
      0 < correctedEvenOrbitMultiplier R m delta k) ∧
    (∀ M k : ℕ, 2 ≤ M → 0 < k →
      M < M + (M - 1) * k) ∧
    (∀ a ell a' d' ell' k : ℕ,
      ExceptionalState a ell →
      7 * a' + 19 * d' + 3 * ell' =
        7 * a + 3 * ell + 2 * exceptionalRadialOffset ell +
          k * (7 * a + 3 * ell + 11) →
      0 < d' ∨ ¬ ExceptionalState a' ell') := by
  exact ⟨seed_cusp_pullback,
    stable_transfer_numerator_positive,
    boundary_transfer_numerator_positive,
    positive_contact_rate_above_two,
    odd_orbit_has_no_integral_resonance,
    exceptional_amplitude_numerators_positive,
    corrected_even_orbit_multiplier_positive,
    positive_orbit_exceeds_contact_maximum,
    exceptional_transition_exits⟩

end AxiomPackJacobianFiniteContactPrefixArithmetic
