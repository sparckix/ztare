/-
Smoke test for the partial closure of `bohrCoefficient_exp_ne` (PR-A1).

The full file at
  projects/ns_millennium_hunt/workspace/research_notes/mathlib_upstream_candidates/BohrMean.lean
is not part of the main lake target (it imports `«IsAlmostPeriodic»`, a
sibling research-notes module).  This smoke test extracts the *new* logic
introduced in the partial closure of `bohrCoefficient_exp_ne` — namely the
`n = 0` vacuous-case dispatch and the existence of an index `i₀` with
`ζ i₀ ≠ 0` — and shows it type-checks against Mathlib + core.

If a future agent fully closes (1)-(5) from the parent file's TODO chain,
they should mirror the structure here.
-/
import Mathlib.Analysis.Normed.Field.Basic
import Mathlib.Data.Real.Basic
import Mathlib.Logic.Function.Basic

namespace AlmostPeriodic.SmokeTest

/-- Smoke: in `Fin 0 → ℝ`, every function is `0`. -/
example (ζ : Fin 0 → ℝ) : ζ = 0 := Subsingleton.elim _ _

/-- Smoke: the `i₀`-existence step from the partial closure of
`bohrCoefficient_exp_ne` type-checks. -/
example {n : ℕ} {ζ : Fin n → ℝ} (hζ : ζ ≠ 0) : ∃ i, ζ i ≠ 0 := by
  classical
  by_contra hall
  push Not at hall
  apply hζ
  funext i
  simpa using hall i

/-- Smoke: full case-split from the partial closure (n=0 vacuous, n>0 picks
an index).  Mirrors the exact tactic shape used in `BohrMean.lean`. -/
example {n : ℕ} {ζ : Fin n → ℝ} (hζ : ζ ≠ 0) :
    n = 0 ∨ ∃ i : Fin n, ζ i ≠ 0 := by
  rcases Nat.eq_zero_or_pos n with hn0 | _hnpos
  · exact Or.inl hn0
  · refine Or.inr ?_
    classical
    by_contra hall
    push Not at hall
    apply hζ
    funext i
    simpa using hall i

end AlmostPeriodic.SmokeTest
