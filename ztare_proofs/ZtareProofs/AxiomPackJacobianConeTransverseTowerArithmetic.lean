import ZtareProofs.AxiomPackJacobianConeSymbolSurjectivityArithmetic

/-!
Arithmetic and seed-line carrier for the transverse-tower obstruction to a
universal cone normal form.

In adapted source coordinates `(V,G)`, the line `V = -1` maps under the seed
to `(P,Q) = (G+1,0)`.  The normal derivative of `Q` is `(G+1)^2`, while its
tangent derivative vanishes.  A cone Hamiltonian has zero second component
on `Q=0`; its first component has `P`-degree at most two.

For the transverse Hamiltonian tower `C^k`, the second component has degree
`3*k-1` on this line.  A source field of component degree at most `B` reaches
degree at most `B+2`, hence matching the tower forces `B ≥ 3*k-3`.

The identification of the displayed formulas with Hamiltonian derivatives
and polynomial degrees remains in the pencil argument.  This file checks the
seed restriction, its two derivative formulas, the cone exponent cap, and
the resulting unbounded arithmetic lower-bound spine.
-/

namespace AxiomPackJacobianConeTransverseTowerArithmetic

/-- The seed's first component in adapted source coordinates. -/
def seedP (V G : ℚ) : ℚ :=
  -(G + 1) *
    (3 * G * V ^ 2 + 6 * G * V + 3 * G + 3 * V ^ 2 + 4 * V)

/-- A factored inner polynomial for the seed's second component. -/
def seedQInner (V G : ℚ) : ℚ :=
  2 * G * V ^ 2 + 4 * G * V + 2 * G + 2 * V ^ 2 + 3 * V

/-- The seed's second component in adapted source coordinates. -/
def seedQ (V G : ℚ) : ℚ :=
  -(G + 1) ^ 2 * (V + 1) * seedQInner V G

/-- Formal `V` derivative of `seedQ`. -/
def seedQdV (V G : ℚ) : ℚ :=
  -(G + 1) ^ 2 *
    (seedQInner V G +
      (V + 1) * (4 * G * V + 4 * G + 4 * V + 3))

/-- Formal `G` derivative of `seedQ`. -/
def seedQdG (V G : ℚ) : ℚ :=
  -2 * (G + 1) * (V + 1) * seedQInner V G -
    (G + 1) ^ 2 * (V + 1) * (2 * V ^ 2 + 4 * V + 2)

theorem seed_transverse_line (G : ℚ) :
    seedP (-1) G = G + 1 ∧
    seedQ (-1) G = 0 := by
  constructor
  · simp [seedP]
    ring
  · simp [seedQ]

theorem seed_q_derivatives_on_transverse_line (G : ℚ) :
    seedQdV (-1) G = (G + 1) ^ 2 ∧
    seedQdG (-1) G = 0 := by
  constructor
  · simp [seedQdV, seedQInner]
    ring
  · simp [seedQdG]

/-- On the cone face `b=1`, the inequality `a ≤ 2*b` caps `a` at two. -/
theorem cone_line_exponent_cap
    (a b : ℕ) (hb : b = 1) (hcone : a ≤ 2 * b) :
    a ≤ 2 := by
  omega

/-- Matching a degree `3*k-1` transverse target by a degree-`B` source
response multiplied by the quadratic seed derivative forces
`B ≥ 3*k-3`. -/
theorem transverse_tower_source_degree_bound
    (k B : ℕ)
    (hdegree : 3 * k - 1 ≤ B + 2) :
    3 * k - 3 ≤ B := by
  omega

/-- No fixed source-degree cap can absorb the complete transverse tower. -/
theorem transverse_tower_escapes_every_fixed_cap
    (B : ℕ) :
    ∃ k : ℕ, 2 ≤ k ∧ B < 3 * k - 3 := by
  exact ⟨B + 2, by omega, by omega⟩

/-- Terminal carrier for the seed-line and unbounded-degree obstruction. -/
theorem cone_transverse_tower_arithmetic_terminal_certificate :
    (∀ G : ℚ,
      seedP (-1) G = G + 1 ∧
      seedQ (-1) G = 0) ∧
    (∀ G : ℚ,
      seedQdV (-1) G = (G + 1) ^ 2 ∧
      seedQdG (-1) G = 0) ∧
    (∀ a b : ℕ, b = 1 → a ≤ 2 * b → a ≤ 2) ∧
    (∀ k B : ℕ, 3 * k - 1 ≤ B + 2 → 3 * k - 3 ≤ B) ∧
    (∀ B : ℕ, ∃ k : ℕ, 2 ≤ k ∧ B < 3 * k - 3) := by
  exact ⟨seed_transverse_line,
    seed_q_derivatives_on_transverse_line,
    cone_line_exponent_cap,
    transverse_tower_source_degree_bound,
    transverse_tower_escapes_every_fixed_cap⟩

end AxiomPackJacobianConeTransverseTowerArithmetic
