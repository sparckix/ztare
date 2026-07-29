import ZtareProofs.AxiomPackJacobianMinimumSectionLieConeArithmetic

/-!
Arithmetic carrier for eventual two-direction target symbols in the
minimum-section cusp cone.

At cusp weight `w`, a cone monomial has exponent pair `(a,b)` with

`2*a + 3*b = w`, `1 ≤ b`, and `a ≤ 2*b`.

Two adjacent solutions differ by `(3,-2)`.  Their Hamiltonian symbol
determinant on the cusp is one sixth of their exponent determinant, namely
`-w/6`.  This file proves that two such cone solutions exist at every
weight `w ≥ 17`.

The identification of exponent determinants with Hamiltonian symbol rank,
and the triangular lifting of symbol surjectivity to a moving formal contact,
remain in the pencil argument.
-/

namespace AxiomPackJacobianConeSymbolSurjectivityArithmetic

open AxiomPackJacobianMovingPoissonSectionArithmetic
open AxiomPackJacobianMinimumSectionLieConeArithmetic

/-- The adjacent fixed-weight exponent pair. -/
def adjacentPair (a b : ℕ) : ExponentPair :=
  ⟨a + 3, b - 2⟩

theorem adjacent_weight
    (a b : ℕ) (hb : 2 ≤ b) :
    weight (adjacentPair a b) = weight ⟨a, b⟩ := by
  simp [adjacentPair, weight]
  omega

theorem adjacent_bracket_numerator
    (a b : ℕ) (hb : 2 ≤ b) :
    bracketNumerator ⟨a, b⟩ (adjacentPair a b) =
      -((weight ⟨a, b⟩ : ℕ) : ℤ) := by
  simp [adjacentPair, bracketNumerator, weight, Nat.cast_sub hb]
  ring

theorem adjacent_bracket_nonzero
    (a b : ℕ) (hb : 2 ≤ b) (hw : 0 < weight ⟨a, b⟩) :
    BracketNonzero ⟨a, b⟩ (adjacentPair a b) := by
  rw [bracketNonzero_iff_numerator_ne_zero,
    adjacent_bracket_numerator a b hb]
  exact neg_ne_zero.mpr (by exact_mod_cast (Nat.ne_of_gt hw))

theorem two_cone_symbols_of_adjacent
    (w a b : ℕ)
    (hw : weight ⟨a, b⟩ = w)
    (hb : 3 ≤ b)
    (ha : a ≤ 2 * b)
    (hadj : a + 3 ≤ 2 * (b - 2)) :
    ∃ e f : ExponentPair,
      InMinimumLieCone e ∧
      InMinimumLieCone f ∧
      weight e = w ∧
      weight f = w ∧
      BracketNonzero e f := by
  have he : InMinimumLieCone ⟨a, b⟩ := by
    exact ⟨le_trans (by norm_num) hb, ha⟩
  have hf : InMinimumLieCone (adjacentPair a b) := by
    constructor
    · change 1 ≤ b - 2
      apply Nat.le_sub_of_add_le
      simpa using hb
    · simpa [adjacentPair] using hadj
  have hfw : weight (adjacentPair a b) = w := by
    rw [adjacent_weight a b (le_trans (by norm_num) hb), hw]
  have hpositive : 0 < weight ⟨a, b⟩ := by
    simp [weight]
    omega
  exact ⟨⟨a, b⟩, adjacentPair a b, he, hf, hw, hfw,
    adjacent_bracket_nonzero a b (le_trans (by norm_num) hb) hpositive⟩

theorem residue_zero_two_symbols
    (k : ℕ) (hk : 2 ≤ k) :
    ∃ e f : ExponentPair,
      InMinimumLieCone e ∧ InMinimumLieCone f ∧
      weight e = 6 * k ∧ weight f = 6 * k ∧
      BracketNonzero e f := by
  apply two_cone_symbols_of_adjacent (6 * k) 0 (2 * k)
  · simp [weight]
    omega
  · omega
  · omega
  · omega

theorem residue_one_two_symbols
    (k : ℕ) (hk : 3 ≤ k) :
    ∃ e f : ExponentPair,
      InMinimumLieCone e ∧ InMinimumLieCone f ∧
      weight e = 6 * k + 1 ∧ weight f = 6 * k + 1 ∧
      BracketNonzero e f := by
  apply two_cone_symbols_of_adjacent (6 * k + 1) 2 (2 * k - 1)
  · simp [weight]
    omega
  · omega
  · omega
  · omega

theorem residue_two_two_symbols
    (k : ℕ) (hk : 2 ≤ k) :
    ∃ e f : ExponentPair,
      InMinimumLieCone e ∧ InMinimumLieCone f ∧
      weight e = 6 * k + 2 ∧ weight f = 6 * k + 2 ∧
      BracketNonzero e f := by
  apply two_cone_symbols_of_adjacent (6 * k + 2) 1 (2 * k)
  · simp [weight]
    omega
  · omega
  · omega
  · omega

theorem residue_three_two_symbols
    (k : ℕ) (hk : 2 ≤ k) :
    ∃ e f : ExponentPair,
      InMinimumLieCone e ∧ InMinimumLieCone f ∧
      weight e = 6 * k + 3 ∧ weight f = 6 * k + 3 ∧
      BracketNonzero e f := by
  apply two_cone_symbols_of_adjacent (6 * k + 3) 0 (2 * k + 1)
  · simp [weight]
    omega
  · omega
  · omega
  · omega

theorem residue_four_two_symbols
    (k : ℕ) (hk : 3 ≤ k) :
    ∃ e f : ExponentPair,
      InMinimumLieCone e ∧ InMinimumLieCone f ∧
      weight e = 6 * k + 4 ∧ weight f = 6 * k + 4 ∧
      BracketNonzero e f := by
  apply two_cone_symbols_of_adjacent (6 * k + 4) 2 (2 * k)
  · simp [weight]
    omega
  · omega
  · omega
  · omega

theorem residue_five_two_symbols
    (k : ℕ) (hk : 2 ≤ k) :
    ∃ e f : ExponentPair,
      InMinimumLieCone e ∧ InMinimumLieCone f ∧
      weight e = 6 * k + 5 ∧ weight f = 6 * k + 5 ∧
      BracketNonzero e f := by
  apply two_cone_symbols_of_adjacent (6 * k + 5) 1 (2 * k + 1)
  · simp [weight]
    omega
  · omega
  · omega
  · omega

/-- Every cusp weight at least `17` has two cone monomials whose exponent
determinant, and hence Hamiltonian cusp-symbol determinant, is nonzero. -/
theorem eventual_two_cone_symbols
    (w : ℕ) (hw : 17 ≤ w) :
    ∃ e f : ExponentPair,
      InMinimumLieCone e ∧
      InMinimumLieCone f ∧
      weight e = w ∧
      weight f = w ∧
      BracketNonzero e f := by
  let k := w / 6
  have hdecomp : w = 6 * k + w % 6 := by
    dsimp [k]
    omega
  have hmod : w % 6 < 6 := Nat.mod_lt _ (by norm_num)
  interval_cases hr : w % 6
  · have hk : 2 ≤ k := by omega
    simpa [hdecomp, hr] using residue_zero_two_symbols k hk
  · have hk : 3 ≤ k := by omega
    simpa [hdecomp, hr] using residue_one_two_symbols k hk
  · have hk : 2 ≤ k := by omega
    simpa [hdecomp, hr] using residue_two_two_symbols k hk
  · have hk : 2 ≤ k := by omega
    simpa [hdecomp, hr] using residue_three_two_symbols k hk
  · have hk : 3 ≤ k := by omega
    simpa [hdecomp, hr] using residue_four_two_symbols k hk
  · have hk : 2 ≤ k := by omega
    simpa [hdecomp, hr] using residue_five_two_symbols k hk

/-- Terminal arithmetic certificate for eventual target-symbol rank two. -/
theorem cone_symbol_surjectivity_arithmetic_terminal_certificate :
    (∀ a b : ℕ, 2 ≤ b →
      weight (adjacentPair a b) = weight ⟨a, b⟩) ∧
    (∀ a b : ℕ, 2 ≤ b →
      bracketNumerator ⟨a, b⟩ (adjacentPair a b) =
        -((weight ⟨a, b⟩ : ℕ) : ℤ)) ∧
    (∀ w : ℕ, 17 ≤ w →
      ∃ e f : ExponentPair,
        InMinimumLieCone e ∧
        InMinimumLieCone f ∧
        weight e = w ∧
        weight f = w ∧
        BracketNonzero e f) := by
  exact ⟨adjacent_weight, adjacent_bracket_numerator,
    eventual_two_cone_symbols⟩

end AxiomPackJacobianConeSymbolSurjectivityArithmetic
