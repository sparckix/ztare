/-
Smoke test for the closure of `bohrMean_character_pair_off_diag`
(PR-B sorry, BohrPlancherel.lean line ~303, tagged `TODO(PR-B.ortho)`)
— closed 2026-05-08.

The PR-B file lives outside the main lake target (under
`projects/.../research_notes/mathlib_upstream_candidates/BohrPlancherel.lean`),
so we cannot import it directly. Instead, we mirror the minimal scaffolding
(stubbed `bohrCharacter`, `forwardChar`, `HasBohrMean`, the two closed
primitives, and the transitive axiom hoisted per catch #21f) and reproduce
the proof body of `bohrMean_character_pair_off_diag` *verbatim*.

If this file type-checks, the proof body in `BohrPlancherel.lean` is
algebraically sound (modulo the same transitive axiom, which is
bookkeeping-equivalent to the narrowed `n ≥ 1` sorry inside PR-A1's
`bohrCoefficient_exp_ne`).

Mathlib chain:
  - `sub_ne_zero.mpr`        (Mathlib `sub_ne_zero` iff)
  - `neg_ne_zero.mpr`        (Mathlib group lemma)
  - `funext`                 (core)
  - `Finset.sum_neg_distrib` (Mathlib `Finset.sum_neg_distrib`)
  - `Finset.sum_sub_distrib` (Mathlib `Finset.sum_sub_distrib`)
  - `Pi.neg_apply`, `Pi.sub_apply`, `neg_mul`, `sub_mul`
  - `← Complex.exp_add`, `← Complex.exp_conj`, `Complex.conj_I`,
    `Complex.conj_ofReal`, `map_sum`, `map_mul`, `ring`

Anti-laundering:
  - The proof body is verbatim — no shortcuts via `True := by trivial`.
  - The transitive axiom `hasBohrMean_bohrCharacter_of_ne_zero` is the
    *same* axiom hoisted in `BohrPlancherel.lean`; it mirrors the
    narrowed `n ≥ 1` sorry inside `BohrMean.lean:480` (TODO PR-A1.exp.n_pos.compose).
  - Bucket-3 (transitive via PR-A1's narrowed sorry).
-/
import Mathlib.Analysis.SpecialFunctions.Complex.Circle
import Mathlib.Analysis.Complex.Exponential

open Complex
open scoped BigOperators ComplexConjugate

namespace AlmostPeriodicSmokeBOrtho

variable {n : ℕ}

/-- Mirror of `BohrMean.bohrCharacter`. -/
noncomputable def bohrCharacter (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp (-(2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

/-- Mirror of `BohrPlancherel.forwardChar`. -/
noncomputable def forwardChar (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp ((2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

/-- Stubbed `HasBohrMean` predicate: opaque — the orthogonality kill
chain is invariant under the precise definition of `HasBohrMean`. The
real predicate is `Tendsto (cubeAverage f) atTop (𝓝 m)`. -/
opaque HasBohrMean : ((Fin n → ℝ) → ℂ) → ℂ → Prop

/-- Mirror of the closed primitive `forwardChar_eq_bohrCharacter_neg`
(BohrPlancherel.lean:191, closed 2026-05-08). Verbatim proof body. -/
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

/-- Mirror of the closed primitive `forwardChar_mul_conj`
(BohrPlancherel.lean:218, closed 2026-05-08). Verbatim proof body. -/
lemma forwardChar_mul_conj (ξ ζ : Fin n → ℝ) (x : Fin n → ℝ) :
    forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x)
      = forwardChar (ξ - ζ) x := by
  unfold forwardChar
  rw [show ((starRingEnd ℂ) (Complex.exp ((2 * Real.pi) * Complex.I
              * (∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ)))))
        = Complex.exp (-((2 * Real.pi) * Complex.I
              * (∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ)))) from ?_]
  · rw [← Complex.exp_add]
    congr 1
    have hsub :
        (∑ i, (((ξ - ζ) i : ℝ) : ℂ) * ((x i : ℝ) : ℂ))
          = (∑ i, ((ξ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ))
            - (∑ i, ((ζ i : ℝ) : ℂ) * ((x i : ℝ) : ℂ)) := by
      rw [← Finset.sum_sub_distrib]
      refine Finset.sum_congr rfl ?_
      intro i _
      simp [Pi.sub_apply, sub_mul]
    rw [hsub]
    ring
  · rw [← Complex.exp_conj]
    congr 1
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

/-- Diagonal character lock: multiplying a packet by its conjugate collapses
    to the zero-frequency character.  This is the diagonal counterpart to the
    off-diagonal orthogonality theorem below, named separately so repair
    routing can distinguish same-frequency simplification from off-diagonal
    Bohr-mean cancellation. -/
lemma forwardChar_mul_conj_self (ξ : Fin n → ℝ) (x : Fin n → ℝ) :
    forwardChar ξ x * (starRingEnd ℂ) (forwardChar ξ x)
      = forwardChar (0 : Fin n → ℝ) x := by
  simpa using forwardChar_mul_conj ξ ξ x

/-- The zero-frequency character is the constant `1` packet. -/
@[simp] lemma forwardChar_zero (x : Fin n → ℝ) :
    forwardChar (0 : Fin n → ℝ) x = 1 := by
  unfold forwardChar
  simp

/-- Diagonal packet simplification in constant form. -/
lemma forwardChar_mul_conj_self_eq_one (ξ : Fin n → ℝ) (x : Fin n → ℝ) :
    forwardChar ξ x * (starRingEnd ℂ) (forwardChar ξ x) = 1 := by
  rw [forwardChar_mul_conj_self, forwardChar_zero]

/-- Mirror of the transitive axiom hoisted in `BohrPlancherel.lean`
(per catch #21f, bucket-3 transitive via PR-A1's narrowed `n ≥ 1` sorry). -/
axiom hasBohrMean_bohrCharacter_of_ne_zero
    {ζ : Fin n → ℝ} (hζ : ζ ≠ 0) :
    HasBohrMean (bohrCharacter ζ) (0 : ℂ)

/-- The closure under test — verbatim proof body of
`bohrMean_character_pair_off_diag` from `BohrPlancherel.lean`. -/
theorem bohrMean_character_pair_off_diag
    {ξ ζ : Fin n → ℝ} (hξζ : ξ ≠ ζ) :
    HasBohrMean
      (fun x : Fin n → ℝ =>
        forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x))
      (0 : ℂ) := by
  have hsub : ξ - ζ ≠ 0 := sub_ne_zero.mpr hξζ
  have hneg : -(ξ - ζ) ≠ 0 := neg_ne_zero.mpr hsub
  have hchar : HasBohrMean (bohrCharacter (-(ξ - ζ))) (0 : ℂ) :=
    hasBohrMean_bohrCharacter_of_ne_zero hneg
  have hpt : (fun x : Fin n → ℝ =>
                forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x))
              = (fun x : Fin n → ℝ => bohrCharacter (-(ξ - ζ)) x) := by
    funext x
    rw [forwardChar_mul_conj ξ ζ x, forwardChar_eq_bohrCharacter_neg]
  rw [hpt]
  exact hchar

/-- **Falsifiability check.** The hypothesis `ξ ≠ ζ` is load-bearing.
If we drop it (replace `hξζ` with the vacuous `True`), the integrand
collapses to `forwardChar 0 = 1` whose Bohr mean is `1`, not `0`, so the
conclusion would be `HasBohrMean (fun _ => 1) 0`, contradicting
`hasBohrMean_const`. We do *not* prove that contradiction here (would
need the real `HasBohrMean`), but the statement-level falsifier is the
non-removability of `hξζ` — exhibited by the explicit
`sub_ne_zero.mpr hξζ` step in the proof body. -/
example {ξ ζ : Fin n → ℝ} (hξζ : ξ ≠ ζ) :
    ξ - ζ ≠ 0 := sub_ne_zero.mpr hξζ

end AlmostPeriodicSmokeBOrtho
