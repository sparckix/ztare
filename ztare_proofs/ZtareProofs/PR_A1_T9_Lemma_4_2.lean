/-
# PR-A1 sub-lemma — `hasBohrMean_le_of_pointwise_le` (Lemma 4.2)

**Sub-PR target** for T9 axiom #4 `T9.bohrAmp_le_Linfty` (round-3
deliverable continuation, see
`projects/ns_millennium_hunt/workspace/T9_axiom4_sublemma_2026_05_09.md`).

This file discharges Lemma 4.2 (the `HasBohrMean`-monotonicity leg of
the 3-lemma chain that closes axiom #4):

  *If `f ≤ g` pointwise on `Fin n → ℝ`, both `f` and `g` are integrable
  on every cube `[-R, R]^n` (R > 0), and they have Bohr means
  `mf` and `mg` respectively, then `mf ≤ mg`.*

This is the predicate-level monotonicity step used to combine
Lemma 4.1 (`cubeAverage_modSq_le_Linfty_squared`, already discharged
sorry-free in `PR_A1_CubeAvgModSqLeLinftySq.lean`) with the constant-
function Bohr-mean fact (`hasBohrMean_const`) to obtain Lemma 4.3
(`bohrMean_modSq_le_Linfty_squared`, the consumer-facing axiom-#4
sub-target).

## Mathlib dependency grep-verification (round-3 audit, C-43)

Round-3 audit caught one phantom in the round-2 spec for THIS lemma
(`Filter.Tendsto.le_le`); see "Phantom-gap catches" docstring section
below.  Verified-extant Mathlib symbols actually used in the proof:

| Symbol                                | Verified file                                                                  |
|---------------------------------------|--------------------------------------------------------------------------------|
| `le_of_tendsto_of_tendsto'`           | `Mathlib/Topology/Order/OrderClosed.lean:477` ✓                                |
| `MeasureTheory.setIntegral_mono_on`   | `Mathlib/MeasureTheory/Integral/Bochner/Set.lean:747` ✓                        |
| `MeasureTheory.volume_pi_pi`          | `Mathlib/MeasureTheory/Constructions/Pi.lean` ✓                                |
| `MeasurableSet.univ_pi`               | `Mathlib/MeasureTheory/Constructions/Pi.lean` ✓                                |
| `smul_le_smul_of_nonneg_left`         | `Mathlib/Algebra/Order/Module/Defs.lean:324` ✓                                 |
| `inv_nonneg`, `pow_nonneg`, `pow_pos` | basic Mathlib ✓                                                                |
| `atTop_neBot` (instance)              | `Mathlib/Order/Filter/AtTopBot/Basic.lean:58` ✓                                |

**Note (C-43 phantom catch, round-3 #44b)**: round-2 spec at line 154
named `Filter.Tendsto.le_le` for this lemma.  Grep on the Mathlib
package (`grep -rn "Tendsto.le_le" .lake/packages/mathlib/Mathlib/`)
returns ZERO hits.  `Tendsto.le_le` is a phantom — it does not exist
under that name in Mathlib.  The correct primitive is
`le_of_tendsto_of_tendsto'` (top-level, in
`Mathlib/Topology/Order/OrderClosed.lean:477`), with signature
`(hf : Tendsto f b (𝓝 a₁)) (hg : Tendsto g b (𝓝 a₂)) (h : ∀ x, f x ≤ g x) : a₁ ≤ a₂`.
This catch is logged in the round-3 deliverable as a C-43-classic
catch (named lemma claimed in spec but not present in Mathlib);
mitigation applied below.

## Anti-laundering posture (catches #6, #21f, #25, #26, #30, #44b)

* No `True := by trivial` smuggling — the conclusion IS an inequality
  on Bohr means, proven by chasing pointwise integrability + scalar
  monotonicity + `le_of_tendsto_of_tendsto'`.
* Hypotheses are load-bearing:
  - `hf_int_pos` and `hg_int_pos` (integrability on every cube R > 0)
    are used to satisfy `setIntegral_mono_on`'s integrability
    requirements.  These are honest about the regularity content
    NOT delivered by `HasBohrMean` alone (HasBohrMean is a Tendsto
    statement; cube integrability is structurally separate).
  - `h_ptwise : ∀ x, f x ≤ g x` is used directly in
    `setIntegral_mono_on`.
  - `hf : HasBohrMean f mf` and `hg : HasBohrMean g mg` are unfolded
    to `Tendsto cubeAverage (atTop) (𝓝 m)` and supplied to
    `le_of_tendsto_of_tendsto'`.
* No new axioms; no sorrys.
* PATTERN-007-inverted-for-Mathlib: term-by-term Mathlib chase.
* PATTERN-008 LEG audit performed below.

## Mirror discipline

This file mirrors `cubeAverage` and `HasBohrMean` from the upstream
candidate `BohrMean.lean` (lines 140 and 145 respectively) BYTE-
IDENTICALLY, restricted to the case `E = ℝ`.  This matches the
mirror discipline used by `PR_A1_VolumeCube_SmokeTest.lean` and
`PR_A1_CubeAvgModSqLeLinftySq.lean` (the round-3 Lemma 4.1
deliverable).  When `BohrMean.lean` lands sorry-free upstream,
this file's `cubeAverage` / `HasBohrMean` definitions become
definitionally equal to the upstream ones, and the lemma's body
ports over verbatim.

## Round-3-continuation friction-debate result (PATTERN-001)

**Champion-exist**: 30-50 line Mathlib-grade lemma; named primitives
all verified-extant (after C-43 phantom catch); structural pattern
matches Lemma 4.1.

**Champion-nonexist**: integrability on cubes might fail to be
derivable from `HasBohrMean` alone (it's not — see (a) below);
`smul`-form `cubeAverage` might require `OrderedSMul` instances
that fail.

**Resolution**:
* (a) Integrability is taken as an explicit hypothesis (per
  research-PR pattern; HasBohrMean does not imply integrability,
  since the Bochner integral returns 0 for non-integrable
  functions and Tendsto can hold trivially in some pathological
  cases).
* (b) The `•` in `cubeAverage` is real-scalar on real-valued
  target (`E = ℝ`), so `smul_le_smul_of_nonneg_left` applies via
  the `OrderedSMul ℝ ℝ` instance (which is just `mul_le_mul_*`
  in disguise — verified by grep at `Algebra/Order/Module/Defs.lean:247`).

Champion-exist wins.  Estimated ~50 line proof.

## PATTERN-008 LEG audit on the discharged proof

* **LEG 1 (inversion)**: Could a reader claim "axiom 4 eliminated"
  from this file?  No — this file ONLY discharges Lemma 4.2.  Lemma
  4.3 (chain) and the witness-coherence step (iii) remain open.
  Axiom 4 remains an axiom in `ns_trackb_T9_closure_proof_attempt.lean`
  (no source-side promotion).
* **LEG 2 (compression)**: Strip "T9", "Bohr", "AP-NS", "Liouville":
  residual claim is "if `f ≤ g` pointwise and both are integrable
  on every centered cube, then their cube-average limits (when they
  exist) are also ordered."  This is a textbook real-analysis
  lemma; compression survives.
* **LEG 3 (cold read)**: A cold reader sees one new file, ~80 lines,
  one named lemma, build-green.  They observe (a) it depends on no
  T9 carriers, (b) it depends on no PR-A1/PR-A2 upstream content, (c)
  it elaborates against pure Mathlib + the round-3 mirror of `cube`
  / `cubeAverage` / `HasBohrMean`.  They would NOT mistake this for
  "T9 closer to Clay closure" — only "Lemma 4.2 of axiom 4's 3-lemma
  decomposition is now discharged."
* **Aggregate**: all 3 legs survive.  Outcome A (no laundering); ships.
-/
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Set
import Mathlib.MeasureTheory.Measure.Lebesgue.Basic
import Mathlib.MeasureTheory.Constructions.Pi
import Mathlib.Topology.Order.OrderClosed

open MeasureTheory Filter Topology
open scoped BigOperators

namespace AlmostPeriodicHasBohrMeanLeOfPointwiseLe

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

/-- The cube `[-R, R]^n` is measurable. -/
lemma measurableSet_cube (R : ℝ) :
    MeasurableSet (cube R : Set (Fin n → ℝ)) := by
  unfold cube
  exact MeasurableSet.univ_pi (fun _ => measurableSet_Icc)

/-- Mirror of `BohrMean.cubeAverage` specialised to `E = ℝ`
(byte-identical up to the target type). -/
noncomputable def cubeAverage (f : (Fin n → ℝ) → ℝ) (R : ℝ) : ℝ :=
  ((2 * R) ^ n)⁻¹ • ∫ x in (cube R : Set (Fin n → ℝ)), f x

/-- Mirror of `BohrMean.HasBohrMean` specialised to `E = ℝ`
(byte-identical). -/
def HasBohrMean (f : (Fin n → ℝ) → ℝ) (m : ℝ) : Prop :=
  Tendsto (cubeAverage f) atTop (𝓝 m)

/-- **Lemma 4.2 — `hasBohrMean_le_of_pointwise_le`.**

If `f ≤ g` pointwise on `Fin n → ℝ`, both `f` and `g` are integrable
on every centred cube `[-R, R]^n` for `R > 0`, and they admit Bohr
means `mf` and `mg` respectively, then `mf ≤ mg`.

This is the `HasBohrMean`-level monotonicity sub-lemma of axiom #4's
3-lemma decomposition (see file docstring). -/
lemma hasBohrMean_le_of_pointwise_le
    {f g : (Fin n → ℝ) → ℝ}
    {mf mg : ℝ}
    (hf : HasBohrMean f mf) (hg : HasBohrMean g mg)
    (hf_int_pos : ∀ R : ℝ, 0 < R → IntegrableOn f (cube R) volume)
    (hg_int_pos : ∀ R : ℝ, 0 < R → IntegrableOn g (cube R) volume)
    (h_ptwise : ∀ x, f x ≤ g x) :
    mf ≤ mg := by
  -- Step 1: pointwise on cube-averages, eventually for R > 0.
  -- For R > 0, both ∫_{cube R} f and ∫_{cube R} g exist (by integrability),
  -- and ∫_{cube R} f ≤ ∫_{cube R} g via setIntegral_mono_on.
  -- Since (2R)^n > 0, scaling preserves the inequality.
  have hCubeAvg_le_eventually :
      ∀ᶠ R in (atTop : Filter ℝ), cubeAverage f R ≤ cubeAverage g R := by
    -- Eventually for R ≥ 1, R > 0 holds; we can also just use R > 0 directly
    -- via `eventually_gt_atTop`.
    refine (eventually_gt_atTop (0 : ℝ)).mono ?_
    intro R hR_pos
    -- Compute the integral inequality on the cube.
    have hMono :
        (∫ x in (cube R : Set (Fin n → ℝ)), f x)
          ≤ (∫ x in (cube R : Set (Fin n → ℝ)), g x) :=
      setIntegral_mono_on
        (hf_int_pos R hR_pos) (hg_int_pos R hR_pos)
        (measurableSet_cube R) (fun x _ => h_ptwise x)
    -- Scale both sides by `((2R)^n)⁻¹ ≥ 0`.
    have h2R_pos : (0 : ℝ) < 2 * R := by linarith
    have hpow_pos : (0 : ℝ) < (2 * R) ^ n := pow_pos h2R_pos n
    have hpow_nonneg : (0 : ℝ) ≤ (2 * R) ^ n := le_of_lt hpow_pos
    have hinv_nonneg : (0 : ℝ) ≤ ((2 * R) ^ n)⁻¹ := inv_nonneg.mpr hpow_nonneg
    -- `cubeAverage` uses `•`; for ℝ-valued targets `•` is `*`, so
    -- `smul_le_smul_of_nonneg_left` applies.
    change ((2 * R) ^ n)⁻¹ • (∫ x in (cube R : Set (Fin n → ℝ)), f x)
      ≤ ((2 * R) ^ n)⁻¹ • (∫ x in (cube R : Set (Fin n → ℝ)), g x)
    exact smul_le_smul_of_nonneg_left hMono hinv_nonneg
  -- Step 2: `le_of_tendsto_of_tendsto'`-style closure.  We use the
  -- eventually-version `le_of_tendsto_of_tendsto` since our pointwise
  -- inequality holds only eventually (for R > 0).
  exact le_of_tendsto_of_tendsto hf hg hCubeAvg_le_eventually

/-- **Type-witness 1**: the lemma elaborates at a concrete dimension. -/
example
    {f g : (Fin 3 → ℝ) → ℝ} {mf mg : ℝ}
    (hf : HasBohrMean f mf) (hg : HasBohrMean g mg)
    (hf_int_pos : ∀ R : ℝ, 0 < R → IntegrableOn f (cube R) volume)
    (hg_int_pos : ∀ R : ℝ, 0 < R → IntegrableOn g (cube R) volume)
    (h_ptwise : ∀ x, f x ≤ g x) :
    mf ≤ mg :=
  hasBohrMean_le_of_pointwise_le (n := 3)
    hf hg hf_int_pos hg_int_pos h_ptwise

/-- The cube has finite volume.  Used for `IntegrableOn` of constants
(mirror of the same helper in `PR_A1_CubeAvgModSqLeLinftySq.lean`). -/
private lemma volume_cube_lt_top_aux (R : ℝ) (hR : 0 ≤ R) :
    volume (cube R : Set (Fin n → ℝ)) ≠ ⊤ := by
  have h2R : (0 : ℝ) ≤ 2 * R := by linarith
  unfold cube
  rw [volume_pi_pi]
  simp only [Real.volume_Icc]
  exact (ENNReal.prod_lt_top fun _ _ => ENNReal.ofReal_lt_top).ne

/-- **Type-witness 2**: the constant-zero specialisation
(both Bohr means are 0; pointwise 0 ≤ 0; trivial). -/
example {n : ℕ} {mf mg : ℝ}
    (hf : HasBohrMean (fun _ : Fin n → ℝ => (0 : ℝ)) mf)
    (hg : HasBohrMean (fun _ : Fin n → ℝ => (0 : ℝ)) mg) :
    mf ≤ mg := by
  refine hasBohrMean_le_of_pointwise_le (n := n) hf hg ?_ ?_ ?_
  · intro R hR
    exact integrableOn_const (volume_cube_lt_top_aux R (le_of_lt hR))
  · intro R hR
    exact integrableOn_const (volume_cube_lt_top_aux R (le_of_lt hR))
  · intro _; exact le_refl 0

end AlmostPeriodicHasBohrMeanLeOfPointwiseLe
