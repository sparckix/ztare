import Mathlib.Tactic

/-!
The substrate-independent arithmetic and leading-field certificate behind the
filtered degree law for the normalized Jacobian-counterexample deformation.

The family-specific symbolic replay supplies the target-relative velocity
`W_s = sum s^q A_q` with degree gains `10`, `12`, and at most `14` for
`q = 1`, `q = 2`, and `q >= 3`, respectively. The parameter costs are
`q + 1`. This file certifies the resulting degree envelope and the exact
commuting leading fields. Degree here means quotient total degree in the fixed
linear coordinates `(v,t)` (equivalently `(v,2t-3v)`) and in the declared
target gauge. The large family formula and gauge minimum remain external.
-/

namespace AxiomPackJacobianFilteredFlow

def invariantR (v t : ℚ) : ℚ := v * (2 * t - 3 * v)

def leadingW1V (v t : ℚ) : ℚ :=
  -(3 / 64 : ℚ) * v^7 * (2 * t - 3 * v)^4

def leadingW1T (v t : ℚ) : ℚ :=
  (3 / 64 : ℚ) * v^6 * (t - 3 * v) * (2 * t - 3 * v)^4

def leadingW2V (v t : ℚ) : ℚ :=
  -(7 / 12 : ℚ) * invariantR v t * leadingW1V v t

def leadingW2T (v t : ℚ) : ℚ :=
  -(7 / 12 : ℚ) * invariantR v t * leadingW1T v t

/-- The leading velocity preserves the polynomial `r=v(2t-3v)`. -/
theorem leading_w1_preserves_r (v t : ℚ) :
    leadingW1V v t * (2 * t - 6 * v) +
      leadingW1T v t * (2 * v) = 0 := by
  simp [leadingW1V, leadingW1T]
  ring

/-- The next leading velocity is an invariant scalar multiple of the first. -/
theorem leading_w2_is_invariant_multiple (v t : ℚ) :
    leadingW2V v t = -(7 / 12 : ℚ) * invariantR v t * leadingW1V v t ∧
    leadingW2T v t = -(7 / 12 : ℚ) * invariantR v t * leadingW1T v t := by
  exact ⟨rfl, rfl⟩

/-- The leading field is nonzero, so its flow coefficients cannot all vanish. -/
theorem leading_w1_nonzero : leadingW1V 1 2 ≠ 0 := by
  norm_num [leadingW1V]

section InverseBranch

def inverseDiscriminant (P Q : ℚ) : ℚ :=
  -4 * P^3 + P^2 + 18 * P * Q - 27 * Q^2 - 4 * Q

/-- Eliminating the selected root from the seed inverse cubic gives a cubic
for its derivative coordinate. -/
theorem inverse_branch_discriminant_identity
    (P Q W : ℚ) (hroot : W ^ 3 - W ^ 2 + P * W - Q = 0) :
    let g := 3 * W^2 - 2 * W + P
    g^3 + (3 * P - 1) * g^2 + inverseDiscriminant P Q = 0 := by
  dsimp [inverseDiscriminant]
  linear_combination
    (27 * P * W - 18 * P + 27 * Q + 27 * W^3 - 27 * W^2 + 4) * hroot

/-- The root is rationally recovered from the derivative coordinate away
from the displayed linear denominator. -/
theorem inverse_branch_root_recovery_identity
    (P Q W : ℚ) (hroot : W ^ 3 - W ^ 2 + P * W - Q = 0) :
    let g := 3 * W^2 - 2 * W + P
    W * (3 * g + 6 * P - 2) = g + 9 * Q - P := by
  dsimp
  linear_combination 9 * hroot

/-- Terminal aggregation of the two exact inverse-branch elimination
identities used by the independent Newton-face proof. -/
theorem inverse_branch_coordinate_certificate
    (P Q W : ℚ) (hroot : W ^ 3 - W ^ 2 + P * W - Q = 0) :
    let g := 3 * W^2 - 2 * W + P
    g^3 + (3 * P - 1) * g^2 + inverseDiscriminant P Q = 0 ∧
      W * (3 * g + 6 * P - 2) = g + 9 * Q - P := by
  dsimp
  exact ⟨inverse_branch_discriminant_identity P Q W hroot,
    inverse_branch_root_recovery_identity P Q W hroot⟩

end InverseBranch

section DegreeEnvelope

/-- Aggregate degree envelope for a time-ordered word. `a` counts the
cost-two/gain-ten atom, `b` the cost-three/gain-twelve atom, and `lateAtoms`
the remaining atoms. Each late atom costs at least four and gains at most
fourteen. -/
theorem word_degree_envelope
    (a b lateAtoms lateCost lateGain n gain : ℕ)
    (hn : n = 2 * a + 3 * b + lateCost)
    (hgain : gain = 10 * a + 12 * b + lateGain)
    (hcost : 4 * lateAtoms ≤ lateCost)
    (hlate : lateGain ≤ 14 * lateAtoms) :
    gain ≤ 5 * n := by
  omega

/-- At odd parameter order, at least three units of the degree budget are
lost. The bound is attained only by introducing the cost-three atom. -/
theorem odd_word_degree_envelope
    (a b lateAtoms lateCost lateGain n gain : ℕ)
    (hn : n = 2 * a + 3 * b + lateCost)
    (hgain : gain = 10 * a + 12 * b + lateGain)
    (hcost : 4 * lateAtoms ≤ lateCost)
    (hlate : lateGain ≤ 14 * lateAtoms)
    (hzero : lateAtoms = 0 → lateCost = 0)
    (hodd : Odd n) :
    gain + 3 ≤ 5 * n := by
  rcases hodd with ⟨k, hk⟩
  omega

/-- Equality in the global envelope excludes both the cost-three atom and all
later atoms. -/
theorem envelope_equality_forces_only_first_atom
    (a b lateAtoms lateCost lateGain n gain : ℕ)
    (hn : n = 2 * a + 3 * b + lateCost)
    (hgain : gain = 10 * a + 12 * b + lateGain)
    (hcost : 4 * lateAtoms ≤ lateCost)
    (hlate : lateGain ≤ 14 * lateAtoms)
    (heq : gain = 5 * n) :
    b = 0 ∧ lateAtoms = 0 := by
  omega

/-- Equality in the odd envelope forces exactly one cost-three atom and no
later atom. Different placements of that atom are handled by the commuting
leading-field identities above. -/
theorem odd_envelope_equality_forces_one_second_atom
    (a b lateAtoms lateCost lateGain n gain : ℕ)
    (hn : n = 2 * a + 3 * b + lateCost)
    (hgain : gain = 10 * a + 12 * b + lateGain)
    (hcost : 4 * lateAtoms ≤ lateCost)
    (hlate : lateGain ≤ 14 * lateAtoms)
    (heq : gain + 3 = 5 * n) :
    b = 1 ∧ lateAtoms = 0 := by
  omega

end DegreeEnvelope

/-- Terminal aggregation of the leading-field and degree-envelope checks. -/
theorem filtered_flow_certificate
    (v t : ℚ)
    (a b lateAtoms lateCost lateGain n gain : ℕ)
    (hn : n = 2 * a + 3 * b + lateCost)
    (hgain : gain = 10 * a + 12 * b + lateGain)
    (hcost : 4 * lateAtoms ≤ lateCost)
    (hlate : lateGain ≤ 14 * lateAtoms)
    (hzero : lateAtoms = 0 → lateCost = 0) :
    leadingW1V v t * (2 * t - 6 * v) +
          leadingW1T v t * (2 * v) = 0 ∧
      leadingW2V v t = -(7 / 12 : ℚ) * invariantR v t * leadingW1V v t ∧
      leadingW2T v t = -(7 / 12 : ℚ) * invariantR v t * leadingW1T v t ∧
      gain ≤ 5 * n ∧
      (Odd n → gain + 3 ≤ 5 * n) := by
  refine ⟨leading_w1_preserves_r v t, rfl, rfl, ?_, ?_⟩
  · exact word_degree_envelope a b lateAtoms lateCost lateGain n gain
      hn hgain hcost hlate
  · intro hodd
    exact odd_word_degree_envelope a b lateAtoms lateCost lateGain n gain
      hn hgain hcost hlate hzero hodd

end AxiomPackJacobianFilteredFlow
