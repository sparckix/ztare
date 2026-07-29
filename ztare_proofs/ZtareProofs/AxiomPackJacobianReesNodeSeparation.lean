import Mathlib.Tactic

/-!
Arithmetic endpoint for the diagonal Rees-boundary obstruction in the
normalized Jacobian campaign.

After `s = τ ε²` and the source/target dilations, the boundary family is

  pτ(r) = τ r³ - 3 r²,
  qτ(r) = 3 τ r⁴ / 4 - 2 r³.

The deterministic bridge proves that any Hamiltonian normal velocity,
modulo an arbitrary source-tangent term, must restrict to

  hτ(r) = -r⁶ / 4 + 3 τ r⁷ / 28.

This file checks the two cusp factors, the double point after scaling
`x = τ r`, its nonzero Hamiltonian separation, and the elementary Rees
degree inequalities.  The completion/evaluation argument remains in the
mathematical artifact.
-/

namespace AxiomPackJacobianReesNodeSeparation

noncomputable section

def boundaryP (τ r : ℝ) : ℝ := τ * r ^ 3 - 3 * r ^ 2

def boundaryQ (τ r : ℝ) : ℝ := 3 * τ * r ^ 4 / 4 - 2 * r ^ 3

def boundaryPPrime (τ r : ℝ) : ℝ := 3 * r * (τ * r - 2)

def boundaryQPrime (τ r : ℝ) : ℝ := 3 * r ^ 2 * (τ * r - 2)

def boundaryPSecond (τ r : ℝ) : ℝ := 6 * τ * r - 6

def boundaryQSecond (τ r : ℝ) : ℝ := 9 * τ * r ^ 2 - 12 * r

def boundaryPThird (τ : ℝ) : ℝ := 6 * τ

def boundaryQThird (τ r : ℝ) : ℝ := 18 * τ * r - 12

def cuspWronskian (τ r : ℝ) : ℝ :=
  boundaryPSecond τ r * boundaryQThird τ r -
    boundaryQSecond τ r * boundaryPThird τ

def scaledBoundaryP (x : ℝ) : ℝ := x ^ 3 - 3 * x ^ 2

def scaledBoundaryQ (x : ℝ) : ℝ := 3 * x ^ 4 / 4 - 2 * x ^ 3

def scaledNodeHamiltonian (x : ℝ) : ℝ :=
  -x ^ 6 / 4 + 3 * x ^ 7 / 28

theorem boundary_derivative_factorization (τ r : ℝ) :
    boundaryQPrime τ r = r * boundaryPPrime τ r := by
  simp [boundaryPPrime, boundaryQPrime]
  ring

theorem cuspWronskian_formula (τ r : ℝ) :
    cuspWronskian τ r =
      18 * (3 * r ^ 2 * τ ^ 2 - 6 * r * τ + 4) := by
  simp [cuspWronskian, boundaryPSecond, boundaryQSecond,
    boundaryPThird, boundaryQThird]
  ring

theorem first_cusp_wronskian (τ : ℝ) :
    cuspWronskian τ 0 = 72 := by
  rw [cuspWronskian_formula]
  norm_num

theorem second_cusp_wronskian (τ : ℝ) (hτ : τ ≠ 0) :
    cuspWronskian τ (2 / τ) = 72 := by
  rw [cuspWronskian_formula]
  field_simp [hτ]
  ring

theorem scaled_node_image
    (x : ℝ)
    (hx : x ^ 2 = 2 * x + 2) :
    scaledBoundaryP x = -2 ∧ scaledBoundaryQ x = 1 := by
  constructor
  · dsimp [scaledBoundaryP]
    linear_combination (x - 1) * (hx)
  · dsimp [scaledBoundaryQ]
    linear_combination (3 * x ^ 2 / 4 - x / 2 + 1 / 2) * (hx)

theorem scaledNodeHamiltonian_reduced
    (x : ℝ)
    (hx : x ^ 2 = 2 * x + 2) :
    scaledNodeHamiltonian x = (36 * x + 26) / 7 := by
  have hx3 : x ^ 3 = 6 * x + 4 := by
    calc
      x ^ 3 = x * x ^ 2 := by ring
      _ = x * (2 * x + 2) := by rw [hx]
      _ = 6 * x + 4 := by nlinarith [hx]
  have hx4 : x ^ 4 = 16 * x + 12 := by
    calc
      x ^ 4 = x * x ^ 3 := by ring
      _ = x * (6 * x + 4) := by rw [hx3]
      _ = 16 * x + 12 := by nlinarith [hx]
  have hx5 : x ^ 5 = 44 * x + 32 := by
    calc
      x ^ 5 = x * x ^ 4 := by ring
      _ = x * (16 * x + 12) := by rw [hx4]
      _ = 44 * x + 32 := by nlinarith [hx]
  have hx6 : x ^ 6 = 120 * x + 88 := by
    calc
      x ^ 6 = x * x ^ 5 := by ring
      _ = x * (44 * x + 32) := by rw [hx5]
      _ = 120 * x + 88 := by nlinarith [hx]
  have hx7 : x ^ 7 = 328 * x + 240 := by
    calc
      x ^ 7 = x * x ^ 6 := by ring
      _ = x * (120 * x + 88) := by rw [hx6]
      _ = 328 * x + 240 := by nlinarith [hx]
  rw [scaledNodeHamiltonian, hx6, hx7]
  ring

theorem explicit_node_pair :
    let d : ℝ := Real.sqrt 3
    let x : ℝ := 1 + d
    let y : ℝ := 1 - d
    (scaledBoundaryP x = -2 ∧ scaledBoundaryQ x = 1) ∧
    (scaledBoundaryP y = -2 ∧ scaledBoundaryQ y = 1) ∧
    scaledNodeHamiltonian x - scaledNodeHamiltonian y =
      72 * d / 7 ∧
    scaledNodeHamiltonian x - scaledNodeHamiltonian y ≠ 0 := by
  dsimp
  have hd2 : (Real.sqrt 3) ^ 2 = 3 := by
    norm_num
  have hdpos : 0 < Real.sqrt 3 := Real.sqrt_pos.2 (by norm_num)
  have hx : (1 + Real.sqrt 3 : ℝ) ^ 2 =
      2 * (1 + Real.sqrt 3) + 2 := by
    nlinarith
  have hy : (1 - Real.sqrt 3 : ℝ) ^ 2 =
      2 * (1 - Real.sqrt 3) + 2 := by
    nlinarith
  have hxImage := scaled_node_image (1 + Real.sqrt 3) hx
  have hyImage := scaled_node_image (1 - Real.sqrt 3) hy
  have hxHamiltonian :=
    scaledNodeHamiltonian_reduced (1 + Real.sqrt 3) hx
  have hyHamiltonian :=
    scaledNodeHamiltonian_reduced (1 - Real.sqrt 3) hy
  refine ⟨hxImage, hyImage, ?_, ?_⟩
  · rw [hxHamiltonian, hyHamiltonian]
    ring
  · rw [hxHamiltonian, hyHamiltonian]
    nlinarith

/-- Strictly subcritical `(4,6)` support has node valuation tending upward.
This is the scalar inequality used in the local-finiteness argument. -/
theorem subcritical_node_valuation_bound
    (n i j δ C : ℚ)
    (h : 4 * i + 6 * j ≤ (2 - δ) * n + C) :
    δ * n / 2 - C / 2 ≤ n - 2 * i - 3 * j := by
  linarith

/-- Node weight at least `n` forces ordinary target degree at least `n/3`. -/
theorem node_weight_forces_ordinary_degree
    (n i j : ℚ)
    (hi : 0 ≤ i)
    (hweight : n ≤ 2 * i + 3 * j) :
    n / 3 ≤ i + j := by
  linarith

theorem rees_node_separation_arithmetic_terminal_certificate :
    (let d : ℝ := Real.sqrt 3
     let x : ℝ := 1 + d
     let y : ℝ := 1 - d
     (scaledBoundaryP x = -2 ∧ scaledBoundaryQ x = 1) ∧
     (scaledBoundaryP y = -2 ∧ scaledBoundaryQ y = 1) ∧
     scaledNodeHamiltonian x - scaledNodeHamiltonian y =
       72 * d / 7 ∧
     scaledNodeHamiltonian x - scaledNodeHamiltonian y ≠ 0) ∧
    (∀ n i j δ C : ℚ,
      4 * i + 6 * j ≤ (2 - δ) * n + C →
      δ * n / 2 - C / 2 ≤ n - 2 * i - 3 * j) ∧
    (∀ n i j : ℚ,
      0 ≤ i → n ≤ 2 * i + 3 * j →
      n / 3 ≤ i + j) := by
  exact ⟨explicit_node_pair, subcritical_node_valuation_bound,
    node_weight_forces_ordinary_degree⟩

end

end AxiomPackJacobianReesNodeSeparation
