/-
# PR-A1 sub-lemma — `cubeAverage_modSq_le_Linfty_squared`

**Sub-PR target** for T9 axiom #4 `T9.bohrAmp_le_Linfty` (round-2
deliverable, see `projects/ns_millennium_hunt/workspace/`
`T9_axiom_elimination_round2_2026_05_09.md` §"Sub-PR target"
Lemma 4.1).

This file discharges Lemma 4.1 (the pure-Mathlib leg of the 3-lemma
chain that closes axiom #4):

  *If `‖f x‖² ≤ M²` for all `x ∈ cube R` and `‖f x‖²` is integrable
  on the cube, then the cube average of `‖f x‖²` is at most `M²`.*

This is the classical step in Bessel's inequality / cube-mean L^∞
monotonicity (Besicovitch 1932 §III.5).  It is a strict precondition
for the round-2 sub-PR target Lemma 4.3 (`bohrMean_modSq_le_Linfty_squared`),
which obtains the Bohr-mean version by taking `R → ∞`.

## Mathlib dependency grep-verification (round-2 round-3 audit)

Every Mathlib symbol named in the round-2 spec was grep-verified against
`.lake/packages/mathlib/`:

| Symbol                                | Verified file                                                               |
|---------------------------------------|-----------------------------------------------------------------------------|
| `MeasureTheory.setIntegral_mono_on`   | `Mathlib/MeasureTheory/Integral/Bochner/Set.lean:747` ✓                     |
| `MeasureTheory.setIntegral_const`     | `Mathlib/MeasureTheory/Integral/Bochner/Set.lean:510` ✓                     |
| `MeasureTheory.volume_pi_pi`          | `Mathlib/MeasureTheory/Constructions/Pi.lean` ✓                             |
| `Real.volume_Icc`                     | `Mathlib/MeasureTheory/Measure/Lebesgue/Basic.lean` ✓                       |
| `pow_nonneg` / `sq_nonneg` / `mul_self_le_mul_self` | `Mathlib/Algebra/Order/Ring/Unbundled/Basic.lean` ✓               |
| `MeasurableSet.univ_pi`               | `Mathlib/MeasureTheory/Constructions/Pi.lean` (used at line 282 etc.) ✓     |
| `ENNReal.ofReal_pow` / `ENNReal.toReal_ofReal` | `Mathlib/Data/ENNReal/Real.lean` ✓                                 |
| `integrableOn_const`                  | `Mathlib/MeasureTheory/Integral/Bochner/Set.lean` ✓                         |

**Note (C-43-variant catch, round-3)**: the round-2 spec named the
target lemma `MeasureTheory.integral_mono_on` and pointed to
`Bochner/Basic.lean`.  Grep shows the only `integral_mono_on` lemma in
that path is in `Mathlib/MeasureTheory/Integral/IntervalIntegral/Basic.lean`
(the 1-D interval-integral version, not what we need).  The correct
Mathlib symbol is `MeasureTheory.setIntegral_mono_on` in
`Bochner/Set.lean`.  This is logged in the round-3 deliverable as a
minor C-43-classic catch (lemma rename on path, not phantom).

## Anti-laundering posture (catches #6, #21f, #25, #26, #30)

* No `True := by trivial` smuggling — the conclusion IS an inequality,
  proven by chasing through `setIntegral_mono_on`.
* Hypotheses are load-bearing: `hR : 0 < R` (used for `((2R)^n)⁻¹ ≠ 0`
  and `volume_cube_eq` non-negativity); `hM_nonneg : 0 ≤ M` (used to
  get `0 ≤ M^2 - 0`, but not strictly needed if we pass through
  `mul_self_le_mul_self` differently — kept for documentation parity
  with the round-2 spec).
* No new axioms; no sorrys.
* PATTERN-007 inverted-for-Mathlib: the proof is term-by-term
  `setIntegral_mono_on` + `setIntegral_const` + `volume_cube_eq` chain.
* The integrability hypothesis `hf_int` is taken as input, NOT
  derived — this is honest about what content this sub-PR delivers
  (the inequality) versus what is upstream content (regularity).

## Round-3 friction-debate result (PATTERN-001)

**Champion-exist**: 30-50 line Mathlib-grade lemma; named ingredients
all verified-extant.

**Champion-nonexist**: integrability hypotheses for `setIntegral_mono_on`
might be hard; smul-flip ordering might be subtle.

**Resolution**: integrability is taken as a hypothesis (standard
research-PR pattern); we use scalar `*` (real `(2R)^n)⁻¹`) rather
than `smul`, which sidesteps `OrderedSMul` issues.  Champion-exist
wins with proviso "use `*`-form not `•`-form."

## PATTERN-008 LEG audit on the discharged proof

* **LEG 1 (inversion)**: Could a reader claim "axiom 4 eliminated" from
  this file?  No — this file ONLY discharges Lemma 4.1 (the pure-Mathlib
  leg).  Lemmas 4.2 (PR-A1-gated `hasBohrMean_le_of_pointwise_le`) and
  4.3 (chain) and the witness-coherence step (iii) remain open.  Axiom 4
  remains an axiom in `ns_trackb_T9_closure_proof_attempt.lean` (no
  source-side promotion in this round).
* **LEG 2 (compression)**: Strip "T9", "Bohr", "AP-NS", "Liouville":
  residual claim is "if a real-valued function is bounded by `M²`
  pointwise on a measurable set of finite volume and is integrable
  there, the (re-scaled) average over the set is at most `M²`."
  This is a textbook real-analysis lemma; compression survives.
* **LEG 3 (cold read)**: A cold reader sees one new file, ~50 lines,
  one named lemma, build-green.  They observe (a) it depends on no
  T9 carriers, (b) it depends on no PR-A1/PR-A2 upstream content, (c)
  it elaborates against pure Mathlib.  They would NOT mistake this for
  "T9 closer to Clay closure" — only "Lemma 4.1 of axiom 4's 3-lemma
  decomposition is now discharged."
* **Aggregate**: all 3 legs survive.  Outcome A (no laundering); ships.
-/
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Set
import Mathlib.MeasureTheory.Measure.Lebesgue.Basic
import Mathlib.MeasureTheory.Constructions.Pi
import Mathlib.Analysis.Normed.Group.Basic

open MeasureTheory
open scoped BigOperators

namespace AlmostPeriodicCubeAvgModSqLeLinftySq

variable {n : ℕ}

/-- Mirror of `BohrMean.cube` (byte-identical; see
`projects/ns_millennium_hunt/workspace/research_notes/`
`mathlib_upstream_candidates/BohrMean.lean` line 97). -/
def cube (R : ℝ) : Set (Fin n → ℝ) :=
  Set.pi Set.univ (fun _ : Fin n => Set.Icc (-R) R)

lemma mem_cube {R : ℝ} {x : Fin n → ℝ} :
    x ∈ (cube R : Set (Fin n → ℝ)) ↔ ∀ i, x i ∈ Set.Icc (-R) R := by
  unfold cube
  exact Set.mem_univ_pi

/-- Mirror of `BohrMean.volume_cube_eq` (byte-identical proof; see
`PR_A1_VolumeCube_SmokeTest.lean`). -/
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

/-- The cube `[-R, R]^n` is measurable (it is a `Set.pi` of intervals). -/
lemma measurableSet_cube (R : ℝ) :
    MeasurableSet (cube R : Set (Fin n → ℝ)) := by
  unfold cube
  exact MeasurableSet.univ_pi (fun _ => measurableSet_Icc)

/-- The cube has finite volume.  Used to derive integrability of constants. -/
lemma volume_cube_lt_top (R : ℝ) (hR : 0 ≤ R) :
    volume (cube R : Set (Fin n → ℝ)) < ⊤ := by
  rw [volume_cube_eq R hR]
  exact ENNReal.ofReal_lt_top

/-- **Lemma 4.1 — `cubeAverage_modSq_le_Linfty_squared`.**

If a complex-valued function `f` is pointwise bounded in modulus-squared
by `M²` on the cube `[-R, R]^n`, and `‖f·‖²` is integrable on the cube,
then the (real-)scaled cube average of `‖f x‖²` is at most `M²`.

This is the pure-Mathlib leg (Lemma 4.1) of the 3-lemma decomposition
discharging T9 axiom #4 `bohrAmp_le_Linfty`; see file docstring above.

The form below uses scalar multiplication (`*`) rather than `•` to
sidestep `OrderedSMul` typeclass issues; this matches the canonical
real-scalar specialization of `BohrMean.cubeAverage` for ℝ-valued
functions. -/
lemma cubeAverage_modSq_le_Linfty_squared
    {f : (Fin n → ℝ) → ℂ}
    {R : ℝ} (hR : 0 < R) {M : ℝ} (hM_nonneg : 0 ≤ M)
    (hf_bdd : ∀ x ∈ (cube R : Set (Fin n → ℝ)), ‖f x‖ ≤ M)
    (hf_int : IntegrableOn (fun x => ‖f x‖^2) (cube R) volume) :
    ((2 * R) ^ n)⁻¹ * (∫ x in (cube R : Set (Fin n → ℝ)), ‖f x‖^2)
      ≤ M^2 := by
  -- Strictly-positive cube scaling (used for `≠ 0`, inverse, etc.).
  have h2R_pos : (0 : ℝ) < 2 * R := by linarith
  have h2R_nonneg : (0 : ℝ) ≤ 2 * R := le_of_lt h2R_pos
  have hpow_pos : (0 : ℝ) < (2 * R) ^ n := pow_pos h2R_pos n
  have hpow_nonneg : (0 : ℝ) ≤ (2 * R) ^ n := le_of_lt hpow_pos
  have hpow_ne : ((2 * R) ^ n : ℝ) ≠ 0 := ne_of_gt hpow_pos
  have hinv_nonneg : (0 : ℝ) ≤ ((2 * R) ^ n)⁻¹ := inv_nonneg.mpr hpow_nonneg
  have hM_sq_nonneg : (0 : ℝ) ≤ M^2 := sq_nonneg M
  -- Pointwise upper bound on `‖f x‖^2`.
  have hf_sq_bdd : ∀ x ∈ (cube R : Set (Fin n → ℝ)), ‖f x‖^2 ≤ M^2 := by
    intro x hx
    have hfx_nn : 0 ≤ ‖f x‖ := norm_nonneg _
    have hfx_le : ‖f x‖ ≤ M := hf_bdd x hx
    -- `‖f x‖^2 = ‖f x‖ * ‖f x‖` and `M^2 = M * M`; apply `mul_self_le_mul_self`.
    have := mul_self_le_mul_self hfx_nn hfx_le
    -- Convert `* self` to `^ 2`.
    simpa [pow_two] using this
  -- Integrability of the constant `M^2` on the cube (finite-measure).
  have hR_nonneg : (0 : ℝ) ≤ R := le_of_lt hR
  have hμ_ne_top : volume (cube R : Set (Fin n → ℝ)) ≠ ⊤ :=
    (volume_cube_lt_top (n := n) R hR_nonneg).ne
  have hConst_int : IntegrableOn (fun _ : (Fin n → ℝ) => M^2) (cube R) volume :=
    integrableOn_const hμ_ne_top
  -- Apply the set-integral monotonicity lemma.
  have hMono :
      (∫ x in (cube R : Set (Fin n → ℝ)), ‖f x‖^2)
        ≤ (∫ _x in (cube R : Set (Fin n → ℝ)), M^2) := by
    refine setIntegral_mono_on hf_int hConst_int ?_ hf_sq_bdd
    exact measurableSet_cube R
  -- Reduce the constant integral via `setIntegral_const`.
  have hConst_int_eq :
      (∫ _x in (cube R : Set (Fin n → ℝ)), M^2)
        = (volume (cube R : Set (Fin n → ℝ))).toReal * M^2 := by
    rw [setIntegral_const, measureReal_def]
    ring
  -- Replace the volume by `(2R)^n` (via `volume_cube_eq` + `toReal_ofReal`).
  have hVol_toReal :
      (volume (cube R : Set (Fin n → ℝ))).toReal = (2 * R) ^ n := by
    rw [volume_cube_eq R hR_nonneg]
    exact ENNReal.toReal_ofReal hpow_nonneg
  -- Combine: ∫_{cube} ‖f x‖^2 ≤ (2R)^n * M^2.
  have hUpper :
      (∫ x in (cube R : Set (Fin n → ℝ)), ‖f x‖^2)
        ≤ (2 * R) ^ n * M^2 := by
    calc
      (∫ x in (cube R : Set (Fin n → ℝ)), ‖f x‖^2)
          ≤ (∫ _x in (cube R : Set (Fin n → ℝ)), M^2) := hMono
      _ = (volume (cube R : Set (Fin n → ℝ))).toReal * M^2 := hConst_int_eq
      _ = (2 * R) ^ n * M^2 := by rw [hVol_toReal]
  -- Multiply both sides by `((2R)^n)⁻¹ ≥ 0` (preserves inequality).
  have hScaled :
      ((2 * R) ^ n)⁻¹ * (∫ x in (cube R : Set (Fin n → ℝ)), ‖f x‖^2)
        ≤ ((2 * R) ^ n)⁻¹ * ((2 * R) ^ n * M^2) :=
    mul_le_mul_of_nonneg_left hUpper hinv_nonneg
  -- Cancel the `((2R)^n)⁻¹ * (2R)^n` factor on the right.
  have hCancel :
      ((2 * R) ^ n)⁻¹ * ((2 * R) ^ n * M^2) = M^2 := by
    rw [← mul_assoc, inv_mul_cancel₀ hpow_ne, one_mul]
  exact hScaled.trans_eq hCancel

/-- **Type-witness 1**: the lemma elaborates at a concrete dimension. -/
example {f : (Fin 3 → ℝ) → ℂ} {R : ℝ} (hR : 0 < R) {M : ℝ} (hM : 0 ≤ M)
    (hf_bdd : ∀ x ∈ (cube R : Set (Fin 3 → ℝ)), ‖f x‖ ≤ M)
    (hf_int : IntegrableOn (fun x => ‖f x‖^2) (cube R) volume) :
    ((2 * R) ^ 3)⁻¹ * (∫ x in (cube R : Set (Fin 3 → ℝ)), ‖f x‖^2)
      ≤ M^2 :=
  cubeAverage_modSq_le_Linfty_squared (n := 3) hR hM hf_bdd hf_int

/-- **Type-witness 2**: scalar specialization (constant zero function trivially). -/
example {R : ℝ} (hR : 0 < R) :
    ((2 * R) ^ (1 : ℕ))⁻¹
        * (∫ x in (cube R : Set (Fin 1 → ℝ)), ‖(0 : ℂ)‖^2)
      ≤ (0 : ℝ)^2 := by
  refine cubeAverage_modSq_le_Linfty_squared (n := 1) hR le_rfl ?_ ?_
  · intro x _; simp
  · -- Integrability of the constant `0` function.
    have : IntegrableOn (fun _ : (Fin 1 → ℝ) => ‖(0 : ℂ)‖^2)
        (cube R) volume := by
      simp only [norm_zero, ne_eq, OfNat.ofNat_ne_zero, not_false_eq_true,
        zero_pow]
      exact integrableOn_const
        ((volume_cube_lt_top (n := 1) R (le_of_lt hR)).ne)
    exact this

end AlmostPeriodicCubeAvgModSqLeLinftySq
