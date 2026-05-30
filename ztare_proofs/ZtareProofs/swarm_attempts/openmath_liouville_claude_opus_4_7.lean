import Mathlib.Analysis.InnerProductSpace.Basic
import Mathlib.MeasureTheory.Integral.Bochner
import Mathlib.Analysis.SpecialFunctions.Gaussian


namespace ZtareProofs.SwarmAttempts.OpenMath.Oclaudeopus47

open MeasureTheory Filter

/--
**Sub-lemma (deterministic core of Lemma C):**
Let `u : ℝ³ → ℝ³` be bounded, divergence-free, and suppose
`u` is an ancient NS velocity field at some fixed time.
Then its convolution with the heat kernel `Gₜ` satisfies
`‖Gₜ * u‖_{L^∞} → 0` as `t → ∞`,
*provided* `u ∈ L^p(ℝ³)` for some `p < ∞`.

This is the deterministic avatar of the statement that
`𝔼[u(A^{s,t}(x), s)] → 0` as `s → -∞`,
since the law of `A^{s,t}(x)` has a density comparable to `G_{c(t-s)}`.
-/
theorem heat_kernel_average_decay_of_Lp_velocity
    {u : EuclideanSpace ℝ (Fin 3) → EuclideanSpace ℝ (Fin 3)}
    (hu_bdd : ∃ M : ℝ, ∀ x, ‖u x‖ ≤ M)
    (hu_Lp : ∃ p : ℝ, 1 ≤ p ∧ p < ⊤ ∧ Memℒp u (ENNReal.ofReal p) volume)
    -- Note: divergence-free is not needed for this decay statement
    : Tendsto (fun t : ℝ => ‖gaussianKernel t ⋆ u‖_∞) atTop (nhds 0) := by
  sorry -- Young's convolution inequality: ‖G_t * u‖_∞ ≤ ‖G_t‖_{p'} ‖u‖_p
         -- and ‖G_t‖_{p'} = C t^{-3/(2p)} → 0 as t → ∞ for p < ∞.

end ZtareProofs.SwarmAttempts.OpenMath.Oclaudeopus47
