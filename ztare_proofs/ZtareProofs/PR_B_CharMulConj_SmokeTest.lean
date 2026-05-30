/-
Smoke test for the closure of `forwardChar_mul_conj`
(PR-B sorry, BohrPlancherel.lean line ~218) — closed 2026-05-08.

The PR-B file lives outside the main lake target (under
`projects/.../research_notes/mathlib_upstream_candidates/BohrPlancherel.lean`),
so we cannot import it directly. Instead, we mirror just the
definition involved (`forwardChar`) and reproduce the proof verbatim.
If this file type-checks, the proof body is sound.

The mirrored definition is byte-identical to the original:
  - `forwardChar` from BohrPlancherel.lean line 181
  - `forwardChar_mul_conj` from BohrPlancherel.lean line ~218

Mathlib chain:
  - `Complex.exp_conj` (Mathlib/Analysis/Complex/Exponential.lean:173)
  - `Complex.exp_add`  (Mathlib/Analysis/Complex/Exponential.lean:107)
  - `Complex.conj_I`   (Mathlib/Data/Complex/Basic.lean — conj I = -I)
  - `Finset.sum_sub_distrib`
  - `Pi.sub_apply`
-/
import Mathlib.Analysis.SpecialFunctions.Complex.Circle
import Mathlib.Analysis.Complex.Exponential

open Complex
open scoped BigOperators ComplexConjugate

namespace AlmostPeriodicSmokeB

variable {n : ℕ}

/-- Mirror of `BohrPlancherel.forwardChar`. -/
noncomputable def forwardChar (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp ((2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

/-- Real-vector subtraction transports through the forward-character dot sum. -/
lemma forwardChar_sum_sub (ξ ζ : Fin n → ℝ) (x : Fin n → ℝ) :
    (∑ i, (((ξ - ζ) i : ℝ) : ℂ) * ((x i : ℝ) : ℂ))
      = (∑ i, ((ξ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ))
        - (∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ)) := by
  rw [← Finset.sum_sub_distrib]
  refine Finset.sum_congr rfl ?_
  intro i _
  simp [Pi.sub_apply, sub_mul]

/-- The forward-character exponent is purely imaginary, so conjugation
negates the exponent. -/
lemma star_exp_forwardChar_exponent (ζ : Fin n → ℝ) (x : Fin n → ℝ) :
    (starRingEnd ℂ) (Complex.exp ((2 * Real.pi) * Complex.I
        * (∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ))))
      = Complex.exp (-((2 * Real.pi) * Complex.I
        * (∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ)))) := by
  rw [← Complex.exp_conj]
  congr 1
  -- Push conj through the product. Each ζ i and x i casts from ℝ, so
  -- conj acts as identity on the sum; conj(2π) = 2π; conj(I) = -I.
  have hS :
      (starRingEnd ℂ) (∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ))
        = ∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ) := by
    rw [map_sum]
    refine Finset.sum_congr rfl ?_
    intro i _
    simp
  rw [map_mul, map_mul, hS, Complex.conj_I]
  simp only [Complex.conj_ofReal, map_ofNat, map_mul]
  ring

/-- The closed lemma — verbatim copy of the proof body that now
appears in `BohrPlancherel.lean` at `forwardChar_mul_conj`. -/
lemma forwardChar_mul_conj (ξ ζ : Fin n → ℝ) (x : Fin n → ℝ) :
    forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x)
      = forwardChar (ξ - ζ) x := by
  unfold forwardChar
  rw [show ((starRingEnd ℂ) (Complex.exp ((2 * Real.pi) * Complex.I
              * (∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ)))))
        = Complex.exp (-((2 * Real.pi) * Complex.I
              * (∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ)))) from
        star_exp_forwardChar_exponent ζ x]
  · rw [← Complex.exp_add]
    congr 1
    have hsub := forwardChar_sum_sub ξ ζ x
    rw [hsub]
    ring

end AlmostPeriodicSmokeB
