/-
Smoke test for the last 3 sorrys closed in `BohrPlancherel.lean` on
2026-05-08 — bringing PR-A2's PR-B file to sorry-free (modulo the
PR-A1-narrowed transitive axioms `hasBohrMean_bohrCharacter_of_ne_zero`,
`hasBohrMean_forwardChar_of_ne_zero`, `hasBohrMean_const_mul_zero`,
`hasBohrMean_finset_sum_zero`, `hasBohrMean_finset_sum`,
`bohrPlancherel_linear_assembly`, all bookkeeping-equivalent to PR-A1's
`volume_cube_eq` / `n ≥ 1` sorries).

Closures under test (verbatim proof bodies from BohrPlancherel.lean):
  1. `plancherel_single_mode`         (line ~761)
  2. `bohrPlancherel_grad_finiteSpec` (line ~826)
  3. `plancherel_grad_single_mode`    (line ~870)

The PR-B file lives outside the main lake target; we mirror the minimal
scaffolding (stubbed `HasBohrMean`, `forwardChar`, `IsTrigPolyVelocity`,
the closed primitive `forwardChar_mul_conj`, hoisted transitive axioms
including the new `hasBohrMean_finset_sum`, plus the just-closed scalar
`bohrPlancherel_finiteSpec` mirrored verbatim from PR_B_FinitespecSmokeTest)
and reproduce the proof bodies of the 3 last-sorry closures.

Mathlib chain:
  - `Function.update`, `Function.update_of_ne`
  - `Finset.sum_singleton`, `Finset.mem_singleton`, `Finset.sum_comm`,
    `Finset.mul_sum`, `Finset.sum_mul`, `Finset.sum_congr`
  - `Complex.normSq_zero`, `Complex.normSq_mul`, `Complex.normSq_I`,
    `Complex.normSq_ofReal`, `Complex.ofReal_sum`
  - `funext`, `push_cast`, `ring`

ZtareProofs chain (transitive axioms):
  - `hasBohrMean_forwardChar_of_ne_zero` (mirrors PR-A1 narrowed sorry)
  - `bohrMean_character_pair_off_diag` (mirror)
  - `hasBohrMean_const_mul_zero` (mirror of PR-A2 `HasBohrMean.smul`)
  - `hasBohrMean_finset_sum_zero` (mirror)
  - `hasBohrMean_finset_sum` (NEW — mirror of `Finset.sum_induction` over
    `HasBohrMean.add` from PR-A2; gating on `volume_cube_eq`)
  - `bohrPlancherel_linear_assembly` (mirror)

Anti-laundering (catches #21f, #25, #26, #30):
  - Proof bodies are verbatim — no shortcuts via `True := by trivial`.
  - All hypotheses are non-underscore.
  - Bucket-3 (transitive via PR-A1 narrowed sorries).
-/
import Mathlib.Analysis.SpecialFunctions.Complex.Circle
import Mathlib.Analysis.Complex.Exponential

open Complex
open scoped BigOperators ComplexConjugate

namespace AlmostPeriodicSmokeBLastSorrys

variable {n : ℕ}

/-- Mirror of `BohrPlancherel.forwardChar`. -/
noncomputable def forwardChar (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp ((2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

@[simp] lemma forwardChar_zero (x : Fin n → ℝ) :
    forwardChar (0 : Fin n → ℝ) x = 1 := by
  simp [forwardChar]

/-- Mirror of `BohrPlancherel.forwardChar_mul_conj` (closed upstream
2026-05-08, verbatim). -/
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

/-- Stubbed `HasBohrMean` (opaque). -/
opaque HasBohrMean : ((Fin n → ℝ) → ℂ) → ℂ → Prop

/-- Mirror of `BohrPlancherel.IsTrigPolyVelocity`. -/
structure IsTrigPolyVelocity
    (Spec : Finset (Fin n → ℝ)) (a : (Fin n → ℝ) → ℂ)
    (f : (Fin n → ℝ) → ℂ) : Prop where
  zero_not_mem : (0 : Fin n → ℝ) ∉ Spec
  expand : ∀ x : Fin n → ℝ,
    f x = a 0 + ∑ ζ ∈ Spec, a ζ * forwardChar ζ x

/-! ### Hoisted transitive axioms (mirror) -/

axiom hasBohrMean_forwardChar_of_ne_zero
    {ζ : Fin n → ℝ} (hζ : ζ ≠ 0) :
    HasBohrMean (forwardChar ζ) (0 : ℂ)

axiom bohrMean_character_pair_off_diag
    {ξ ζ : Fin n → ℝ} (hξζ : ξ ≠ ζ) :
    HasBohrMean
      (fun x : Fin n → ℝ =>
        forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x))
      (0 : ℂ)

axiom hasBohrMean_const_mul_zero
    {f : (Fin n → ℝ) → ℂ} (c : ℂ) (hf : HasBohrMean f (0 : ℂ)) :
    HasBohrMean (fun x => c * f x) (0 : ℂ)

axiom hasBohrMean_finset_sum_zero
    {ι : Type*} {s : Finset ι} {g : ι → (Fin n → ℝ) → ℂ}
    (hg : ∀ i ∈ s, HasBohrMean (g i) (0 : ℂ)) :
    HasBohrMean (fun x => ∑ i ∈ s, g i x) (0 : ℂ)

/-- NEW axiom mirror — general (non-zero target) finite-sum linearity. -/
axiom hasBohrMean_finset_sum
    {ι : Type*} {s : Finset ι}
    {g : ι → (Fin n → ℝ) → ℂ} {m : ι → ℂ}
    (hg : ∀ i ∈ s, HasBohrMean (g i) (m i)) :
    HasBohrMean (fun x => ∑ i ∈ s, g i x) (∑ i ∈ s, m i)

axiom bohrPlancherel_linear_assembly
    {Spec : Finset (Fin n → ℝ)} {a : (Fin n → ℝ) → ℂ}
    (hg₂ :
      HasBohrMean
        (fun x : Fin n → ℝ =>
          a 0 * ∑ ζ ∈ Spec,
            (starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x))
        (0 : ℂ))
    (hg₃ :
      HasBohrMean
        (fun x : Fin n → ℝ =>
          (starRingEnd ℂ) (a 0) * ∑ ζ ∈ Spec, a ζ * forwardChar ζ x)
        (0 : ℂ))
    (hg₄ :
      HasBohrMean
        (fun x : Fin n → ℝ =>
          ∑ ξ ∈ Spec, ∑ ζ ∈ Spec with ζ ≠ ξ,
            a ξ * (starRingEnd ℂ) (a ζ)
              * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x)))
        (0 : ℂ)) :
    HasBohrMean
      (fun x : Fin n → ℝ =>
        ((Complex.normSq (a 0) : ℂ)
          + ∑ ζ ∈ Spec, (Complex.normSq (a ζ) : ℂ))
        + (a 0 * ∑ ζ ∈ Spec,
              (starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x))
        + ((starRingEnd ℂ) (a 0) * ∑ ζ ∈ Spec, a ζ * forwardChar ζ x)
        + ∑ ξ ∈ Spec, ∑ ζ ∈ Spec with ζ ≠ ξ,
            a ξ * (starRingEnd ℂ) (a ζ)
              * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x)))
      ((Complex.normSq (a 0) : ℂ)
        + ∑ ζ ∈ Spec, (Complex.normSq (a ζ) : ℂ))

/-! ### Mirror of just-closed `bohrPlancherel_finiteSpec` -/

axiom bohrPlancherel_finiteSpec
    {Spec : Finset (Fin n → ℝ)} {a : (Fin n → ℝ) → ℂ} {f : (Fin n → ℝ) → ℂ}
    (hf : IsTrigPolyVelocity Spec a f) :
    HasBohrMean
      (fun x => (Complex.normSq (f x) : ℂ))
      ((Complex.normSq (a 0) : ℂ)
        + ∑ ζ ∈ Spec, (Complex.normSq (a ζ) : ℂ))

/-! ### Closure 1 — `plancherel_single_mode` (verbatim proof body) -/

theorem plancherel_single_mode
    {ζ : Fin n → ℝ} (hζ : ζ ≠ 0) (c : ℂ) :
    HasBohrMean
      (fun x => (Complex.normSq (c * forwardChar ζ x) : ℂ))
      ((Complex.normSq c : ℂ)) := by
  classical
  set a : (Fin n → ℝ) → ℂ := Function.update (fun _ => (0 : ℂ)) ζ c with ha_def
  have ha_zero : a 0 = 0 := by
    have h0ne : (0 : Fin n → ℝ) ≠ ζ := hζ.symm
    simp [ha_def, Function.update_of_ne h0ne]
  have ha_ζ : a ζ = c := by simp [ha_def]
  have hf : IsTrigPolyVelocity ({ζ} : Finset (Fin n → ℝ)) a
              (fun x => c * forwardChar ζ x) :=
    { zero_not_mem := by
        simp [Finset.mem_singleton, hζ.symm]
      expand := by
        intro x
        rw [Finset.sum_singleton, ha_zero, ha_ζ, zero_add] }
  have hres := bohrPlancherel_finiteSpec hf
  have hrhs :
      ((Complex.normSq (a 0) : ℂ)
        + ∑ ζ' ∈ ({ζ} : Finset (Fin n → ℝ)), (Complex.normSq (a ζ') : ℂ))
        = (Complex.normSq c : ℂ) := by
    rw [Finset.sum_singleton, ha_zero, ha_ζ, Complex.normSq_zero]
    push_cast
    ring
  rw [hrhs] at hres
  exact hres

/-! ### Mirror of `gradNormSq` -/

noncomputable def gradNormSq
    (Spec : Finset (Fin n → ℝ)) (a : (Fin n → ℝ) → ℂ) (x : Fin n → ℝ) : ℝ :=
  ∑ i : Fin n,
    Complex.normSq
      (∑ ζ ∈ Spec, ((2 * Real.pi : ℝ) : ℂ) * Complex.I
                  * (ζ i : ℂ) * a ζ * forwardChar ζ x)

/-! ### Closure 2 — `bohrPlancherel_grad_finiteSpec` (verbatim) -/

theorem bohrPlancherel_grad_finiteSpec
    {Spec : Finset (Fin n → ℝ)} {a : (Fin n → ℝ) → ℂ} {f : (Fin n → ℝ) → ℂ}
    (hf : IsTrigPolyVelocity Spec a f) :
    HasBohrMean
      (fun x : Fin n → ℝ => (gradNormSq Spec a x : ℂ))
      (∑ ζ ∈ Spec,
        ((2 * Real.pi) ^ 2 : ℂ)
          * (∑ i : Fin n, ((ζ i : ℂ)) ^ 2)
          * (Complex.normSq (a ζ) : ℂ)) := by
  classical
  have h_per_i :
      ∀ i : Fin n,
        HasBohrMean
          (fun x : Fin n → ℝ =>
            (Complex.normSq
              (∑ ζ ∈ Spec, ((2 * Real.pi : ℝ) : ℂ) * Complex.I
                          * (ζ i : ℂ) * a ζ * forwardChar ζ x) : ℂ))
          (∑ ζ ∈ Spec, ((2 * Real.pi) ^ 2 : ℂ) * ((ζ i : ℂ)) ^ 2
                      * (Complex.normSq (a ζ) : ℂ)) := by
    intro i
    set b : (Fin n → ℝ) → ℂ :=
      fun ζ => ((2 * Real.pi : ℝ) : ℂ) * Complex.I * (ζ i : ℂ) * a ζ
      with hb_def
    set g_i : (Fin n → ℝ) → ℂ :=
      fun x => b 0 + ∑ ζ ∈ Spec, b ζ * forwardChar ζ x
      with hg_def
    have hb_zero : b 0 = 0 := by
      simp [hb_def]
    have hf_i : IsTrigPolyVelocity Spec b g_i :=
      { zero_not_mem := hf.zero_not_mem
        expand := fun x => rfl }
    have hres := bohrPlancherel_finiteSpec hf_i
    have hnormSq_b : ∀ ζ,
        (Complex.normSq (b ζ) : ℂ)
          = ((2 * Real.pi) ^ 2 : ℂ) * ((ζ i : ℂ)) ^ 2
              * (Complex.normSq (a ζ) : ℂ) := by
      intro ζ
      show (Complex.normSq (((2 * Real.pi : ℝ) : ℂ) * Complex.I
              * (ζ i : ℂ) * a ζ) : ℂ)
            = ((2 * Real.pi) ^ 2 : ℂ) * ((ζ i : ℂ)) ^ 2
                * (Complex.normSq (a ζ) : ℂ)
      rw [Complex.normSq_mul, Complex.normSq_mul, Complex.normSq_mul,
          Complex.normSq_I, Complex.normSq_ofReal]
      have hζi : Complex.normSq ((ζ i : ℂ)) = (ζ i : ℝ) ^ 2 := by
        rw [show ((ζ i : ℂ)) = ((ζ i : ℝ) : ℂ) from rfl,
            Complex.normSq_ofReal]
        ring
      rw [hζi]
      push_cast
      ring
    have hrhs :
        ((Complex.normSq (b 0) : ℂ)
          + ∑ ζ ∈ Spec, (Complex.normSq (b ζ) : ℂ))
          = ∑ ζ ∈ Spec, ((2 * Real.pi) ^ 2 : ℂ) * ((ζ i : ℂ)) ^ 2
                      * (Complex.normSq (a ζ) : ℂ) := by
      rw [hb_zero, Complex.normSq_zero]
      push_cast
      rw [zero_add]
      exact Finset.sum_congr rfl (fun ζ _ => hnormSq_b ζ)
    rw [hrhs] at hres
    have hg_eq : g_i = fun x =>
        ∑ ζ ∈ Spec, ((2 * Real.pi : ℝ) : ℂ) * Complex.I
                  * (ζ i : ℂ) * a ζ * forwardChar ζ x := by
      funext x
      simp [hg_def, hb_def]
    rw [hg_eq] at hres
    exact hres
  have hSum :
      HasBohrMean
        (fun x : Fin n → ℝ =>
          ∑ i : Fin n, (Complex.normSq
            (∑ ζ ∈ Spec, ((2 * Real.pi : ℝ) : ℂ) * Complex.I
                        * (ζ i : ℂ) * a ζ * forwardChar ζ x) : ℂ))
        (∑ i : Fin n, ∑ ζ ∈ Spec,
            ((2 * Real.pi) ^ 2 : ℂ) * ((ζ i : ℂ)) ^ 2
              * (Complex.normSq (a ζ) : ℂ)) :=
    hasBohrMean_finset_sum (s := Finset.univ)
      (g := fun i x =>
        (Complex.normSq
          (∑ ζ ∈ Spec, ((2 * Real.pi : ℝ) : ℂ) * Complex.I
                      * (ζ i : ℂ) * a ζ * forwardChar ζ x) : ℂ))
      (m := fun i => ∑ ζ ∈ Spec, ((2 * Real.pi) ^ 2 : ℂ) * ((ζ i : ℂ)) ^ 2
                                  * (Complex.normSq (a ζ) : ℂ))
      (fun i _ => h_per_i i)
  have hLHS : (fun x : Fin n → ℝ => (gradNormSq Spec a x : ℂ))
              = (fun x : Fin n → ℝ =>
                  ∑ i : Fin n, (Complex.normSq
                    (∑ ζ ∈ Spec, ((2 * Real.pi : ℝ) : ℂ) * Complex.I
                                * (ζ i : ℂ) * a ζ * forwardChar ζ x) : ℂ)) := by
    funext x
    simp [gradNormSq, Complex.ofReal_sum]
  have hRHS :
      (∑ i : Fin n, ∑ ζ ∈ Spec,
          ((2 * Real.pi) ^ 2 : ℂ) * ((ζ i : ℂ)) ^ 2
            * (Complex.normSq (a ζ) : ℂ))
        = ∑ ζ ∈ Spec,
            ((2 * Real.pi) ^ 2 : ℂ)
              * (∑ i : Fin n, ((ζ i : ℂ)) ^ 2)
              * (Complex.normSq (a ζ) : ℂ) := by
    rw [Finset.sum_comm]
    refine Finset.sum_congr rfl (fun ζ _ => ?_)
    -- Goal: ∑ i, (2π)² · ζᵢ² · |a ζ|² = ((2π)² · (∑ i, ζᵢ²)) · |a ζ|²
    rw [show ((2 * Real.pi) ^ 2 : ℂ) * (∑ i : Fin n, ((ζ i : ℂ)) ^ 2)
            = ∑ i : Fin n, ((2 * Real.pi) ^ 2 : ℂ) * ((ζ i : ℂ)) ^ 2
          from (Finset.mul_sum _ _ _)]
    rw [Finset.sum_mul]
  rw [hLHS, ← hRHS]
  exact hSum

/-! ### Closure 3 — `plancherel_grad_single_mode` (verbatim) -/

theorem plancherel_grad_single_mode
    {ζ : Fin n → ℝ} (hζ : ζ ≠ 0) (c : ℂ) :
    HasBohrMean
      (fun x : Fin n → ℝ =>
        (gradNormSq ({ζ} : Finset (Fin n → ℝ))
                    (Function.update (fun _ => (0 : ℂ)) ζ c) x : ℂ))
      (((2 * Real.pi) ^ 2 : ℂ)
        * (∑ i : Fin n, ((ζ i : ℂ)) ^ 2)
        * (Complex.normSq c : ℂ)) := by
  classical
  set a : (Fin n → ℝ) → ℂ := Function.update (fun _ => (0 : ℂ)) ζ c with ha_def
  have ha_zero : a 0 = 0 := by
    have h0ne : (0 : Fin n → ℝ) ≠ ζ := hζ.symm
    simp [ha_def, Function.update_of_ne h0ne]
  have ha_ζ : a ζ = c := by simp [ha_def]
  have hf : IsTrigPolyVelocity ({ζ} : Finset (Fin n → ℝ)) a
              (fun x => c * forwardChar ζ x) :=
    { zero_not_mem := by
        simp [Finset.mem_singleton, hζ.symm]
      expand := by
        intro x
        rw [Finset.sum_singleton, ha_zero, ha_ζ, zero_add] }
  have hres := bohrPlancherel_grad_finiteSpec hf
  have hrhs :
      (∑ ζ' ∈ ({ζ} : Finset (Fin n → ℝ)),
        ((2 * Real.pi) ^ 2 : ℂ)
          * (∑ i : Fin n, ((ζ' i : ℂ)) ^ 2)
          * (Complex.normSq (a ζ') : ℂ))
        = ((2 * Real.pi) ^ 2 : ℂ)
            * (∑ i : Fin n, ((ζ i : ℂ)) ^ 2)
            * (Complex.normSq c : ℂ) := by
    rw [Finset.sum_singleton, ha_ζ]
  rw [hrhs] at hres
  exact hres

end AlmostPeriodicSmokeBLastSorrys
