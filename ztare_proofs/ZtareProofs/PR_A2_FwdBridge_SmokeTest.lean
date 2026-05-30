/-
Smoke test for the closure of `forwardChar_eq_bohrCharacter_neg`
(PR-A2 sorry #1, BohrPlancherel.lean line ~191) — closed 2026-05-08.

The PR-A2 file lives outside the main lake target (under
`projects/.../research_notes/mathlib_upstream_candidates/BohrPlancherel.lean`),
so we cannot import it directly. Instead, we mirror just the two
definitions involved (`forwardChar` and `bohrCharacter`) and reproduce
the proof verbatim. If this file type-checks, the proof body is sound.

The mirrored definitions are byte-identical to the originals:
  - `bohrCharacter` from BohrMean.lean line 248
  - `forwardChar` from BohrPlancherel.lean line 181
  - `forwardChar_eq_bohrCharacter_neg` from BohrPlancherel.lean line 191
-/
import Mathlib.Analysis.SpecialFunctions.Complex.Circle

open Complex
open scoped BigOperators

namespace AlmostPeriodicSmoke

variable {n : ℕ}

/-- Mirror of `BohrMean.bohrCharacter`. -/
noncomputable def bohrCharacter (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp (-(2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

/-- Mirror of `BohrPlancherel.forwardChar`. -/
noncomputable def forwardChar (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp ((2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

/-- The closed lemma — verbatim copy of the proof body that now
appears in `BohrPlancherel.lean` at `forwardChar_eq_bohrCharacter_neg`. -/
lemma forwardChar_eq_bohrCharacter_neg (ζ x : Fin n → ℝ) :
    forwardChar ζ x = bohrCharacter (-ζ) x := by
  unfold forwardChar bohrCharacter
  congr 1
  have hsum :
      (∑ i, (((-ζ) i : ℝ) : ℂ) * ((x i : ℝ) : ℂ))
        = -(∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ)) := by
    rw [← Finset.sum_neg_distrib]
    refine Finset.sum_congr rfl ?_
    intro i _
    simp [Pi.neg_apply, neg_mul]
  rw [hsum]
  ring

end AlmostPeriodicSmoke
