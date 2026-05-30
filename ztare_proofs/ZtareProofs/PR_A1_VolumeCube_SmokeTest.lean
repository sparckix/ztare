/-
Smoke test for `volume_cube_eq` (PR-A1).

Mirrors the closed proof from
`projects/ns_millennium_hunt/workspace/research_notes/mathlib_upstream_candidates/BohrMean.lean`
(line ~111).  The original file imports `«IsAlmostPeriodic»`, a sibling
research-notes module, and is not part of the main lake target — so we
mirror the `cube` definition byte-identically and reproduce the proof
here.  If this file type-checks against Mathlib, the upstream lemma's
proof body is sound (no hidden sorry, no `True := by trivial`
laundering, no axiom dependence beyond Mathlib's own `volume_pi_pi`,
`Real.volume_Icc`, `Finset.prod_const`, `ENNReal.ofReal_pow`).

Anti-laundering posture:
- Body is term-by-term identical to BohrMean.lean line ~111.
- Hypothesis `hR : 0 ≤ R` is load-bearing (used twice for
  `ENNReal.ofReal_pow` non-negativity).
- No underscores on real hypotheses.
-/
import Mathlib.MeasureTheory.Measure.Lebesgue.Basic
import Mathlib.MeasureTheory.Constructions.Pi

open MeasureTheory
open scoped BigOperators

namespace AlmostPeriodicVolumeCubeSmoke

variable {n : ℕ}

/-- Mirror of `BohrMean.cube`. -/
def cube (R : ℝ) : Set (Fin n → ℝ) :=
  Set.pi Set.univ (fun _ : Fin n => Set.Icc (-R) R)

/-- Mirror of `BohrMean.volume_cube_eq` (closed; sorry-free). -/
lemma volume_cube_eq (R : ℝ) (hR : 0 ≤ R) :
    volume (cube R : Set (Fin n → ℝ)) = ENNReal.ofReal ((2 * R) ^ n) := by
  have h2R : (0 : ℝ) ≤ 2 * R := by linarith
  unfold cube
  rw [volume_pi_pi]
  simp only [Real.volume_Icc]
  rw [Finset.prod_const, Finset.card_univ, Fintype.card_fin]
  rw [← ENNReal.ofReal_pow (by linarith : (0 : ℝ) ≤ R - -R) n]
  congr 1
  ring

/-- Type-witness: the lemma elaborates at a concrete `n` and `R`. -/
example : volume (cube (1 : ℝ) : Set (Fin 3 → ℝ)) = ENNReal.ofReal ((2 * 1) ^ 3) :=
  volume_cube_eq 1 (by norm_num)

/-- Type-witness: the conclusion has the expected shape under generic `R`. -/
example {n : ℕ} (R : ℝ) (hR : 0 ≤ R) :
    volume (cube R : Set (Fin n → ℝ)) = ENNReal.ofReal ((2 * R) ^ n) :=
  volume_cube_eq R hR

end AlmostPeriodicVolumeCubeSmoke
