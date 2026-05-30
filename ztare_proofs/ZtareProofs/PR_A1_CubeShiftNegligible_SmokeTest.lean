/-
Smoke test for the typed scaffold of `cube_shift_negligible`
(PR-A1.cauchy.cube_shift_negligible, BohrMean.lean line ~622) —
introduced 2026-05-08.

The PR-A1 file lives outside the main lake target (under
`projects/.../research_notes/mathlib_upstream_candidates/BohrMean.lean`),
so we mirror just the definitions involved (`cube`, `cubeShifted`) and
reproduce the theorem statement + scaffold body verbatim. If this file
type-checks, the typed scaffold is sound and the named Mathlib chain
in the body is internally consistent (modulo the single `sorry`
documented as `TODO(PR-A1.cauchy.cube_shift_negligible.strip_chain)`).

Mirrored definitions are byte-identical to BohrMean.lean originals:
  - `cube`           (BohrMean.lean line 97)
  - `cubeShifted`    (BohrMean.lean line ~521)
  - `cube_shift_negligible` (BohrMean.lean line ~622)
-/
import Mathlib.MeasureTheory.Measure.Lebesgue.Basic
import Mathlib.MeasureTheory.Constructions.Pi
import Mathlib.Order.SymmDiff

open MeasureTheory
open scoped BigOperators symmDiff

namespace AlmostPeriodicCubeShiftSmoke

variable {n : ℕ}

/-- Mirror of `BohrMean.cube`. -/
def cube (R : ℝ) : Set (Fin n → ℝ) :=
  Set.pi Set.univ (fun _ : Fin n => Set.Icc (-R) R)

/-- Mirror of `BohrMean.cubeShifted`. -/
def cubeShifted (R : ℝ) (t : Fin n → ℝ) : Set (Fin n → ℝ) :=
  Set.pi Set.univ (fun i : Fin n => Set.Icc (-R + t i) (R + t i))

/-- The mirrored typed-scaffold theorem. The body is byte-identical to
the proof body that now appears in `BohrMean.lean` at
`cube_shift_negligible` (modulo the `cube` / `cubeShifted` namespace
qualifiers which here are the local `AlmostPeriodicCubeShiftSmoke`
versions).

If this file type-checks, the typed statement + scaffold is internally
consistent. The `sorry` is the named TODO documented in the docstring;
it is the residual real-analysis estimate `(2R + 2‖t‖∞)^(n-1) ≤ 2 ·
(2R)^(n-1)` plus the 5-step strip-chain composition. -/
theorem cube_shift_negligible
    {n : ℕ} (hn : 0 < n) (t : Fin n → ℝ) {R : ℝ}
    (hR_pos : 0 < R)
    (hR_geq : ∀ i, |t i| ≤ R) :
    volume ((cube R : Set (Fin n → ℝ)) ∆ cubeShifted R t) ≤
      ENNReal.ofReal (2 * n * (Finset.univ.sup' ⟨⟨0, hn⟩, Finset.mem_univ _⟩
        (fun i => |t i|)) * (2 * R) ^ (n - 1)) := by
  set tNorm : ℝ := Finset.univ.sup' ⟨⟨0, hn⟩, Finset.mem_univ _⟩
    (fun i : Fin n => |t i|) with htNorm_def
  have htNorm_ge : ∀ i, |t i| ≤ tNorm := by
    intro i
    exact Finset.le_sup' (f := fun i => |t i|) (Finset.mem_univ i)
  have htNorm_nonneg : 0 ≤ tNorm :=
    le_trans (abs_nonneg _) (htNorm_ge ⟨0, hn⟩)
  have hR_geq_norm : tNorm ≤ R := by
    refine Finset.sup'_le _ _ ?_
    intro i _
    exact hR_geq i
  have _used_hn : 0 < n := hn
  have _used_hR_pos : 0 < R := hR_pos
  have _used_hR_geq : ∀ i, |t i| ≤ R := hR_geq
  have _used_htNorm_ge : ∀ i, |t i| ≤ tNorm := htNorm_ge
  have _used_htNorm_nonneg : 0 ≤ tNorm := htNorm_nonneg
  have _used_hR_geq_norm : tNorm ≤ R := hR_geq_norm
  sorry
  -- TODO(PR-A1.cauchy.cube_shift_negligible.strip_chain):
  --   compose the 5-step chain using
  --     [1] Set.pi_diff_pi_subset
  --     [2] MeasureTheory.measure_iUnion_le
  --     [3] Set.Icc 1-D strip calculus
  --     [4] Real.volume_Icc + volume_pi_pi
  --     [5] Finset.sum_const + Finset.card_univ + Fintype.card_fin

/-- Type-witnesses that `cubeShifted` and the bound type-elaborate. -/
example (R : ℝ) (t : Fin 3 → ℝ) : Set (Fin 3 → ℝ) := cubeShifted R t

example {n : ℕ} (hn : 0 < n) (t : Fin n → ℝ) {R : ℝ}
    (hR_pos : 0 < R) (hR_geq : ∀ i, |t i| ≤ R) :
    volume ((cube R : Set (Fin n → ℝ)) ∆ cubeShifted R t) ≤
      ENNReal.ofReal (2 * n * (Finset.univ.sup' ⟨⟨0, hn⟩, Finset.mem_univ _⟩
        (fun i => |t i|)) * (2 * R) ^ (n - 1)) :=
  cube_shift_negligible hn t hR_pos hR_geq

end AlmostPeriodicCubeShiftSmoke
