/-
Smoke test for the catch #21f-refined decomposition of
`IsAlmostPeriodic.bohrCharacter_isAP`
(BohrMean.lean line ~1153 after the 2026-05-08 root-sorry pass) —
introduced 2026-05-08 (sister-agent line-734 hoist closure).

The PR-A1 file lives outside the main lake target (under
`projects/.../research_notes/mathlib_upstream_candidates/BohrMean.lean`),
so we mirror the relevant definitions and the structural composition.

This smoke test verifies that:

  * `bohrCharacter_add` (algebraic translation formula) is sorry-free.
  * `norm_bohrCharacter_translate_diff` (uniform-in-x reduction) is
    sorry-free.
  * `bohrCharacter_isAP` body is sorry-free GIVEN the named root
    sub-lemma `dirichlet_kronecker_relatively_dense`.
  * The chain dirichlet_kronecker → bohrCharacter_isAP →
    mul_unimodular_of_joint_density compresses to a SINGLE root sorry.

Mirrored items:

  * `bohrCharacter`                              (BohrMean.lean ~248)
  * `IsAlmostPeriodic`                           (IsAlmostPeriodic.lean ~57)
  * `norm_bohrCharacter`                         (BohrMean.lean ~833)
  * `bohrCharacter_add`                          (BohrMean.lean ~914)
  * `norm_bohrCharacter_translate_diff`          (BohrMean.lean ~945)
  * `dirichlet_kronecker_relatively_dense`       (BohrMean.lean ~989) — axiom here
  * `IsAlmostPeriodic.bohrCharacter_isAP`        (BohrMean.lean ~1153)

**Anti-laundering compliance** (catches #21f, #25, #26, #30):
- No `True := by trivial` rewrites.
- The single root sorry is hoisted into a separately-named axiom
  (`dirichlet_kronecker_relatively_dense`) which is grep-able.
- All other lemmas are closed sorry-free; failures would be visible
  as smoke-test compile errors.
-/
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Measure.Lebesgue.Basic
import Mathlib.MeasureTheory.Constructions.Pi
import Mathlib.Analysis.Complex.Trigonometric
import Mathlib.Analysis.Normed.Group.Bounded
import Mathlib.Order.Filter.AtTopBot.Basic

open scoped Topology BigOperators

namespace BohrCharIsAPSmoke

variable {n : ℕ}

/-! ### Mirrored definitions (byte-identical to BohrMean.lean / IsAlmostPeriodic.lean) -/

/-- Mirror of `BohrMean.bohrCharacter`. -/
noncomputable def bohrCharacter (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp (-(2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

/-- Mirror of `IsAlmostPeriodic`. -/
def IsAlmostPeriodic {α : Type*} [PseudoMetricSpace α]
    (f : (Fin n → ℝ) → α) : Prop :=
  ∀ ε : ℝ, 0 < ε → ∃ L : ℝ, 0 < L ∧
    ∀ x : Fin n → ℝ, ∃ t : Fin n → ℝ,
      (∀ i, |t i - x i| ≤ L) ∧
      (∀ y : Fin n → ℝ, dist (f (y + t)) (f y) < ε)

/-! ### Mirrored sorry-free helpers -/

/-- Mirror of `BohrMean.norm_bohrCharacter`. Sorry-free. -/
@[simp] lemma norm_bohrCharacter (ζ x : Fin n → ℝ) :
    ‖bohrCharacter ζ x‖ = 1 := by
  unfold bohrCharacter
  rw [Complex.norm_exp]
  have hre :
      (-(2 * Real.pi) * Complex.I *
          (∑ i, (ζ i : ℂ) * (x i : ℂ))).re = 0 := by
    have hSumIm :
        (∑ i, (ζ i : ℂ) * (x i : ℂ)).im = 0 := by
      have heq : (∑ i, (ζ i : ℂ) * (x i : ℂ)) =
          ((∑ i, ζ i * x i : ℝ) : ℂ) := by
        push_cast; rfl
      rw [heq]; simp
    simp [Complex.mul_re, Complex.mul_im, Complex.I_re, Complex.I_im,
          hSumIm]
  rw [hre, Real.exp_zero]

/-- Mirror of `BohrMean.bohrCharacter_add`. Sorry-free. -/
lemma bohrCharacter_add (ζ x τ : Fin n → ℝ) :
    bohrCharacter ζ (x + τ) = bohrCharacter ζ x * bohrCharacter ζ τ := by
  unfold bohrCharacter
  rw [← Complex.exp_add]
  congr 1
  have hsum :
      (∑ i, (ζ i : ℂ) * ((x + τ) i : ℂ))
        = (∑ i, (ζ i : ℂ) * (x i : ℂ))
          + (∑ i, (ζ i : ℂ) * (τ i : ℂ)) := by
    rw [← Finset.sum_add_distrib]
    refine Finset.sum_congr rfl (fun i _ => ?_)
    show (ζ i : ℂ) * (((x + τ) i : ℝ) : ℂ)
        = (ζ i : ℂ) * (x i : ℂ) + (ζ i : ℂ) * (τ i : ℂ)
    have hpt : (x + τ) i = x i + τ i := rfl
    rw [hpt]
    push_cast
    ring
  rw [hsum]
  ring

/-- Mirror of `BohrMean.norm_bohrCharacter_translate_diff`. Sorry-free. -/
lemma norm_bohrCharacter_translate_diff (ζ x τ : Fin n → ℝ) :
    ‖bohrCharacter ζ (x + τ) - bohrCharacter ζ x‖
      = ‖bohrCharacter ζ τ - 1‖ := by
  have hfactor :
      bohrCharacter ζ (x + τ) - bohrCharacter ζ x
        = bohrCharacter ζ x * (bohrCharacter ζ τ - 1) := by
    rw [bohrCharacter_add]; ring
  rw [hfactor, norm_mul, norm_bohrCharacter, one_mul]

/-! ### Mirrored ROOT sorry (held as axiom here so the structural
composition can be type-checked) -/

/-- Mirror of `BohrMean.dirichlet_kronecker_relatively_dense` —
**single root open obligation** for the entire `bohrCharacter` AP
chain. Held as an axiom in this smoke test. -/
axiom dirichlet_kronecker_relatively_dense (ζ : Fin n → ℝ) :
    ∀ ε : ℝ, 0 < ε → ∃ L : ℝ, 0 < L ∧
      ∀ x : Fin n → ℝ, ∃ τ : Fin n → ℝ,
        (∀ i, |τ i - x i| ≤ L) ∧
        ‖bohrCharacter ζ τ - 1‖ < ε

/-! ### The structural composition itself — sorry-free. -/

/-- Mirror of `BohrMean.IsAlmostPeriodic.bohrCharacter_isAP` —
sorry-free composition of `dirichlet_kronecker_relatively_dense` +
`norm_bohrCharacter_translate_diff`. -/
theorem bohrCharacter_isAP (ζ : Fin n → ℝ) :
    IsAlmostPeriodic (bohrCharacter ζ : (Fin n → ℝ) → ℂ) := by
  intro ε hε
  obtain ⟨L, hLpos, hL⟩ := dirichlet_kronecker_relatively_dense ζ ε hε
  refine ⟨L, hLpos, ?_⟩
  intro x
  obtain ⟨τ, hτ_close, hτ_small⟩ := hL x
  refine ⟨τ, hτ_close, ?_⟩
  intro y
  have hreduce :
      ‖bohrCharacter ζ (y + τ) - bohrCharacter ζ y‖
        = ‖bohrCharacter ζ τ - 1‖ :=
    norm_bohrCharacter_translate_diff ζ y τ
  have hbound :
      ‖bohrCharacter ζ (y + τ) - bohrCharacter ζ y‖ < ε := by
    rw [hreduce]; exact hτ_small
  simpa [Complex.dist_eq] using hbound

/-- Type-witness on real concrete data (`n = 3`). -/
example (ζ : Fin 3 → ℝ) :
    IsAlmostPeriodic (bohrCharacter ζ : (Fin 3 → ℝ) → ℂ) :=
  bohrCharacter_isAP ζ

/-- Type-witness that `bohrCharacter_add` is sorry-free. -/
example (ζ x τ : Fin 5 → ℝ) :
    bohrCharacter ζ (x + τ) = bohrCharacter ζ x * bohrCharacter ζ τ :=
  bohrCharacter_add ζ x τ

/-- Type-witness that `norm_bohrCharacter_translate_diff` is sorry-free. -/
example (ζ x τ : Fin 7 → ℝ) :
    ‖bohrCharacter ζ (x + τ) - bohrCharacter ζ x‖
      = ‖bohrCharacter ζ τ - 1‖ :=
  norm_bohrCharacter_translate_diff ζ x τ

end BohrCharIsAPSmoke
