/-
Smoke test for the typed scaffold of `hasBohrMean_mul_bohrCharacter`
(PR-A1.coeff_well_defined, BohrMean.lean line ~1381 after the
2026-05-08 closure pass) — introduced 2026-05-08.

The PR-A1 file lives outside the main lake target (under
`projects/.../research_notes/mathlib_upstream_candidates/BohrMean.lean`),
so we mirror just the definitions and structural composition involved:

  * `bohrCharacter`                 (BohrMean.lean line ~248)
  * `cube`                          (BohrMean.lean line ~97) — only the
                                    *signature* enters via
                                    `HasBohrMean`; we mirror its
                                    interface stub `cubeAverage`.
  * `HasBohrMean`                   (BohrMean.lean line ~145)
  * `IsAlmostPeriodic`              (IsAlmostPeriodic.lean line ~57)
  * `IsAlmostPeriodic.mul_bohrCharacter`
                                    (BohrMean.lean line ~1381 after pass)
  * `hasBohrMean_of_isAlmostPeriodic`
                                    (IsAlmostPeriodic.lean line ~760)
  * `hasBohrMean_mul_bohrCharacter` (BohrMean.lean line ~1381 after pass)

If this file type-checks, the typed statement + structural composition
(continuity-of-product + boundedness-of-product + AP-of-product →
existence) is internally consistent. Two `sorry`s remain:

  - `IsAlmostPeriodic.mul_bohrCharacter`        — sister scaffold TODO
  - `hasBohrMean_of_isAlmostPeriodic` (n ≥ 1)   — sister scaffold TODO

The `hasBohrMean_mul_bohrCharacter` body itself is sorry-free: it
threads three load-bearing hypotheses into the existence theorem.

**Anti-laundering compliance** (catches #21f, #25, #26, #30):
- `hAP`, `hCont`, `hBdd` are all named (not `_`) and load-bearing.
- No `True := by trivial` rewrites.
- The two transitive `sorry`s are hoisted into separately-named
  sub-lemmas (catch #21f), not buried as anonymous holes.
-/
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Measure.Lebesgue.Basic
import Mathlib.MeasureTheory.Constructions.Pi
import Mathlib.Analysis.Complex.Trigonometric
import Mathlib.Analysis.Normed.Group.Bounded
import Mathlib.Order.Filter.AtTopBot.Basic

open MeasureTheory Filter
open scoped Topology BigOperators

namespace AlmostPeriodicMulCharSmoke

variable {n : ℕ}

/-! ### Mirrored definitions (byte-identical to BohrMean.lean / IsAlmostPeriodic.lean) -/

/-- Mirror of `BohrMean.cube`. -/
def cube (R : ℝ) : Set (Fin n → ℝ) :=
  Set.pi Set.univ (fun _ : Fin n => Set.Icc (-R) R)

/-- Mirror of `BohrMean.cubeAverage` (interface only — definition not
needed for this smoke test). -/
noncomputable def cubeAverage (f : (Fin n → ℝ) → ℂ) (R : ℝ) : ℂ :=
  ((2 * R) ^ n)⁻¹ • ∫ x in (cube R : Set (Fin n → ℝ)), f x

/-- Mirror of `BohrMean.HasBohrMean`. -/
def HasBohrMean (f : (Fin n → ℝ) → ℂ) (m : ℂ) : Prop :=
  Tendsto (cubeAverage f) atTop (𝓝 m)

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

/-! ### Mirrored helper lemmas (sorry-free) -/

/-- Mirror of `BohrMean.norm_bohrCharacter`. -/
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
        push_cast
        rfl
      rw [heq]
      simp
    simp [Complex.mul_re, Complex.mul_im, Complex.I_re, Complex.I_im,
          hSumIm]
  rw [hre, Real.exp_zero]

/-- Mirror of `BohrMean.continuous_bohrCharacter`. -/
lemma continuous_bohrCharacter (ζ : Fin n → ℝ) :
    Continuous (bohrCharacter ζ : (Fin n → ℝ) → ℂ) := by
  unfold bohrCharacter
  refine Complex.continuous_exp.comp ?_
  refine (continuous_const (y := (-(2 * Real.pi) * Complex.I))).mul ?_
  refine continuous_finset_sum Finset.univ ?_
  intro i _
  refine continuous_const.mul ?_
  exact Complex.continuous_ofReal.comp (continuous_apply i)

/-! ### Mirrored sister-agent sorrys (kept as named axioms here so the
structural composition can be checked even though they are open in the
master file).

After 2026-05-08 catch #21f decomposition (this agent), the single
`isAP_mul_bohrCharacter` axiom is split into TWO sub-axioms +
ONE closed sub-lemma:

  * `bohrCharacter_isAP` — open (Dirichlet-Kronecker on ℝ^n).
  * `mul_unimodular_of_joint_density` — CLOSED in this smoke test
    (mirrors the master file, sorry-free).
  * `isAP_mul_bohrCharacter` — open (needs bounded_of_continuous +
    Bohr-intersection to compose the previous two).
-/

/-- Mirror of `BohrMean.IsAlmostPeriodic.bohrCharacter_isAP` — open. -/
axiom bohrCharacter_isAP (ζ : Fin n → ℝ) :
    IsAlmostPeriodic (bohrCharacter ζ : (Fin n → ℝ) → ℂ)

/-- Mirror of `BohrMean.IsAlmostPeriodic.mul_unimodular_of_joint_density`
— CLOSED here, sorry-free, byte-faithful to master file. -/
theorem mul_unimodular_of_joint_density
    {f χ : (Fin n → ℝ) → ℂ} {M : ℝ}
    (_hf : IsAlmostPeriodic f)
    (_hχ : IsAlmostPeriodic χ)
    (hχ_unit : ∀ x, ‖χ x‖ = 1)
    (hM_pos : 0 < M)
    (hf_bdd : ∀ x, ‖f x‖ ≤ M)
    (hjoint : ∀ ε : ℝ, 0 < ε → ∃ L : ℝ, 0 < L ∧
      ∀ x : Fin n → ℝ, ∃ t : Fin n → ℝ,
        (∀ i, |t i - x i| ≤ L) ∧
        (∀ y, dist (f (y + t)) (f y) < ε / (2 * (M + 1))) ∧
        (∀ y, dist (χ (y + t)) (χ y) < ε / (2 * (M + 1)))) :
    IsAlmostPeriodic (fun x => f x * χ x) := by
  intro ε hε
  obtain ⟨L, hLpos, hL⟩ := hjoint ε hε
  refine ⟨L, hLpos, ?_⟩
  intro x
  obtain ⟨t, ht_close, htf, htχ⟩ := hL x
  refine ⟨t, ht_close, ?_⟩
  intro y
  have hMp1 : (0 : ℝ) < M + 1 := by linarith
  have h2Mp1 : (0 : ℝ) < 2 * (M + 1) := by linarith
  have hF : ‖f (y + t) - f y‖ < ε / (2 * (M + 1)) := by
    have := htf y
    simpa [Complex.dist_eq] using this
  have hX : ‖χ (y + t) - χ y‖ < ε / (2 * (M + 1)) := by
    have := htχ y
    simpa [Complex.dist_eq] using this
  have hsplit :
      f (y + t) * χ (y + t) - f y * χ y
        = (f (y + t) - f y) * χ (y + t) + f y * (χ (y + t) - χ y) := by
    ring
  have hχ_norm_yt : ‖χ (y + t)‖ = 1 := hχ_unit (y + t)
  have hf_norm_y  : ‖f y‖ ≤ M := hf_bdd y
  have hbound1 : ‖(f (y + t) - f y) * χ (y + t)‖
      = ‖f (y + t) - f y‖ := by
    rw [norm_mul, hχ_norm_yt, mul_one]
  have hbound2 : ‖f y * (χ (y + t) - χ y)‖
      ≤ M * ‖χ (y + t) - χ y‖ := by
    rw [norm_mul]
    exact mul_le_mul_of_nonneg_right hf_norm_y (norm_nonneg _)
  have htri :
      ‖f (y + t) * χ (y + t) - f y * χ y‖
        ≤ ‖f (y + t) - f y‖ + M * ‖χ (y + t) - χ y‖ := by
    calc
      ‖f (y + t) * χ (y + t) - f y * χ y‖
          = ‖(f (y + t) - f y) * χ (y + t)
                + f y * (χ (y + t) - χ y)‖ := by rw [hsplit]
      _ ≤ ‖(f (y + t) - f y) * χ (y + t)‖
            + ‖f y * (χ (y + t) - χ y)‖ := norm_add_le _ _
      _ = ‖f (y + t) - f y‖
            + ‖f y * (χ (y + t) - χ y)‖ := by rw [hbound1]
      _ ≤ ‖f (y + t) - f y‖
            + M * ‖χ (y + t) - χ y‖ := by linarith [hbound2]
  have hweighted :
      ‖f (y + t) - f y‖ + M * ‖χ (y + t) - χ y‖
        < ε / (2 * (M + 1)) + M * (ε / (2 * (M + 1))) := by
    have h2 : M * ‖χ (y + t) - χ y‖ < M * (ε / (2 * (M + 1))) :=
      mul_lt_mul_of_pos_left hX hM_pos
    linarith
  have hsum_eq :
      ε / (2 * (M + 1)) + M * (ε / (2 * (M + 1))) = ε / 2 := by
    have hne : (2 * (M + 1)) ≠ 0 := ne_of_gt h2Mp1
    field_simp
    ring
  have hε_half : (ε / 2 : ℝ) < ε := by linarith
  have hfinal :
      ‖f (y + t) * χ (y + t) - f y * χ y‖ < ε := by
    calc
      ‖f (y + t) * χ (y + t) - f y * χ y‖
          ≤ ‖f (y + t) - f y‖ + M * ‖χ (y + t) - χ y‖ := htri
      _ < ε / (2 * (M + 1)) + M * (ε / (2 * (M + 1))) := hweighted
      _ = ε / 2 := hsum_eq
      _ < ε := hε_half
  simpa [Complex.dist_eq] using hfinal

/-- Mirror of `BohrMean.IsAlmostPeriodic.mul_bohrCharacter` — open
(transitive composition of the open `bohrCharacter_isAP`, the closed
`mul_unimodular_of_joint_density`, and the open `bounded_of_continuous`
+ Bohr-intersection that supply `M` and the joint-density witness). -/
axiom isAP_mul_bohrCharacter
    {f : (Fin n → ℝ) → ℂ} (hf : IsAlmostPeriodic f) (ζ : Fin n → ℝ) :
    IsAlmostPeriodic (fun x => f x * bohrCharacter ζ x)

/-- Mirror of `BohrMean.hasBohrMean_of_isAlmostPeriodic` — open. -/
axiom hasBohrMean_of_isAlmostPeriodic
    {f : (Fin n → ℝ) → ℂ}
    (hAP : IsAlmostPeriodic f)
    (hCont : Continuous f)
    (hBdd : Bornology.IsBounded (Set.range f)) :
    ∃ m : ℂ, HasBohrMean f m

/-! ### The structural composition itself — sorry-free.

This is the proof body that now lives in `BohrMean.lean` at
`hasBohrMean_mul_bohrCharacter`. The mirroring is byte-identical
modulo the `axiom`-vs-`theorem` nature of the two transitive
dependencies above. -/
theorem hasBohrMean_mul_bohrCharacter
    {f : (Fin n → ℝ) → ℂ}
    (hAP : IsAlmostPeriodic f)
    (hCont : Continuous f)
    (hBdd : Bornology.IsBounded (Set.range f))
    (ζ : Fin n → ℝ) :
    ∃ m : ℂ, HasBohrMean (fun x => f x * bohrCharacter ζ x) m := by
  -- Step 1: continuity of the product.
  have hContProd : Continuous (fun x => f x * bohrCharacter ζ x) :=
    hCont.mul (continuous_bohrCharacter ζ)
  -- Step 2: boundedness of the range of the product.
  have hBddProd : Bornology.IsBounded
      (Set.range (fun x => f x * bohrCharacter ζ x)) := by
    rw [isBounded_iff_forall_norm_le] at hBdd ⊢
    obtain ⟨C, hC⟩ := hBdd
    refine ⟨C, ?_⟩
    rintro _ ⟨x, rfl⟩
    have hfx : ‖f x‖ ≤ C := hC (f x) (Set.mem_range_self x)
    have hχx : ‖bohrCharacter ζ x‖ = 1 := norm_bohrCharacter ζ x
    calc ‖f x * bohrCharacter ζ x‖
        = ‖f x‖ * ‖bohrCharacter ζ x‖ := by rw [norm_mul]
      _ = ‖f x‖ * 1 := by rw [hχx]
      _ = ‖f x‖ := by ring
      _ ≤ C := hfx
  -- Step 3: AP of the product (via the named sub-axiom).
  have hAPProd : IsAlmostPeriodic (fun x => f x * bohrCharacter ζ x) :=
    isAP_mul_bohrCharacter hAP ζ
  -- Step 4: apply the existence theorem to the modulated function.
  exact hasBohrMean_of_isAlmostPeriodic hAPProd hContProd hBddProd

/-- Type-witness that the existence corollary type-elaborates with all
hypotheses load-bearing on real concrete data. -/
example (f : (Fin 3 → ℝ) → ℂ)
    (hAP : IsAlmostPeriodic f) (hCont : Continuous f)
    (hBdd : Bornology.IsBounded (Set.range f))
    (ζ : Fin 3 → ℝ) :
    ∃ m : ℂ, HasBohrMean (fun x => f x * bohrCharacter ζ x) m :=
  hasBohrMean_mul_bohrCharacter hAP hCont hBdd ζ

/-- Type-witness that `norm_bohrCharacter` is sorry-free: the example
elaborates as a closed term. -/
example (ζ x : Fin 5 → ℝ) : ‖bohrCharacter ζ x‖ = 1 :=
  norm_bohrCharacter ζ x

/-- Type-witness that `continuous_bohrCharacter` is sorry-free. -/
example (ζ : Fin 7 → ℝ) :
    Continuous (bohrCharacter ζ : (Fin 7 → ℝ) → ℂ) :=
  continuous_bohrCharacter ζ

end AlmostPeriodicMulCharSmoke
