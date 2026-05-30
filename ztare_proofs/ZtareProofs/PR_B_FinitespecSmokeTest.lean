/-
Smoke test for the closure of `bohrPlancherel_finiteSpec`
(PR-B sorry, BohrPlancherel.lean line ~598, tagged `TODO(PR-B.plancherel)`)
— closed 2026-05-08.

This is the **load-bearing T9-gating Bessel-direction theorem**: T9
step 3's hoisted axiom `T9.bohrAmp_le_Linfty` cites `bohrPlancherel_finiteSpec`
transitively for the upper bound `M[|f|²] ≤ ‖f‖∞²` direction.

The PR-B file lives outside the main lake target, so we cannot import it
directly. Instead, we mirror the minimal scaffolding (stubbed
`HasBohrMean`, `forwardChar`, `IsTrigPolyVelocity`, the closed primitives
`forwardChar_mul_conj`, `forwardChar_zero`, `normSq_trigPoly_expand`,
`bohrMean_character_pair_off_diag`, plus the hoisted transitive axioms)
and reproduce the proof body of `bohrPlancherel_finiteSpec` *verbatim*.

If this file type-checks, the proof body in `BohrPlancherel.lean` is
algebraically sound (modulo the same hoisted transitive axioms, all of
which are bookkeeping-equivalent to PR-A1's open `volume_cube_eq` /
narrowed `n ≥ 1` sorries).

Mathlib chain consumed by the proof:
  - `Complex.mul_conj`
  - `Finset.mem_filter`, `Finset.sum_congr`
  - `funext`, `neg_ne_zero`, `Ne.symm`
  - `forwardChar_mul_conj` (closed in BohrPlancherel.lean)
  - `forwardChar_zero` (closed in BohrPlancherel.lean)
  - `normSq_trigPoly_expand` (closed in BohrPlancherel.lean)
  - `bohrMean_character_pair_off_diag` (closed in BohrPlancherel.lean,
    transitively via `hasBohrMean_bohrCharacter_of_ne_zero`)

ZtareProofs chain (transitive axioms hoisted in BohrPlancherel.lean,
mirrored here verbatim):
  - `hasBohrMean_forwardChar_of_ne_zero` (composes
    `hasBohrMean_bohrCharacter_of_ne_zero` with the closed bridge
    `forwardChar_eq_bohrCharacter_neg`)
  - `hasBohrMean_const_mul_zero` (bookkeeping for `HasBohrMean.smul`
    lifted to ℂ)
  - `hasBohrMean_finset_sum_zero` (bookkeeping for `Finset.sum_induction`
    over `HasBohrMean.add`, gated on integrability via PR-A1
    `volume_cube_eq`)
  - `bohrPlancherel_linear_assembly` (composite of the four
    `HasBohrMean.add` applications gated on PR-A1's `volume_cube_eq`)

Anti-laundering (catches #21f, #25, #26, #30):
  - The proof body is verbatim — no shortcuts via `True := by trivial`.
  - All hypotheses on every theorem are non-underscore.
  - The closure transitively depends on `bohrCoefficient_exp_ne` n ≥ 1
    sorry through `hasBohrMean_bohrCharacter_of_ne_zero`, hoisted as a
    named axiom per catch #21f bucket-3.
  - Bucket-3 (transitive via PR-A1's narrowed `n ≥ 1` sorry +
    `volume_cube_eq` sorry).

T9 unblock impact: with this closure, the Bessel-direction Plancherel
identity for finite-spec AP functions has a sorry-free proof body inside
`BohrPlancherel.lean`. The remaining transitive sorries are exactly the
PR-A1/PR-A2 ones already gating the entire PR-B file.
-/
import Mathlib.Analysis.SpecialFunctions.Complex.Circle
import Mathlib.Analysis.Complex.Exponential

open Complex
open scoped BigOperators ComplexConjugate

namespace AlmostPeriodicSmokeBFinitespec

variable {n : ℕ}

/-- Mirror of `BohrPlancherel.forwardChar`. -/
noncomputable def forwardChar (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp ((2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

@[simp] lemma forwardChar_zero (x : Fin n → ℝ) :
    forwardChar (0 : Fin n → ℝ) x = 1 := by
  simp [forwardChar]

/-- Mirror of `BohrPlancherel.forwardChar_mul_conj` — closed upstream
2026-05-08, verbatim. -/
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

/-- Stubbed `HasBohrMean` predicate: opaque — the assembly chain is
invariant under the precise definition of `HasBohrMean`. The real
predicate is `Tendsto (cubeAverage f) atTop (𝓝 m)`. -/
opaque HasBohrMean : ((Fin n → ℝ) → ℂ) → ℂ → Prop

/-- Mirror of `BohrPlancherel.IsTrigPolyVelocity` (with `Σ` renamed to
`Spec` for pure-Lean syntax safety). -/
structure IsTrigPolyVelocity
    (Spec : Finset (Fin n → ℝ)) (a : (Fin n → ℝ) → ℂ)
    (f : (Fin n → ℝ) → ℂ) : Prop where
  zero_not_mem : (0 : Fin n → ℝ) ∉ Spec
  expand : ∀ x : Fin n → ℝ,
    f x = a 0 + ∑ ζ ∈ Spec, a ζ * forwardChar ζ x

/-- Mirror of the closed `normSq_trigPoly_expand` (verbatim proof). -/
lemma normSq_trigPoly_expand
    {Spec : Finset (Fin n → ℝ)} {a : (Fin n → ℝ) → ℂ} {f : (Fin n → ℝ) → ℂ}
    (hf : IsTrigPolyVelocity Spec a f) (x : Fin n → ℝ) :
    (Complex.normSq (f x) : ℂ)
      = (Complex.normSq (a 0) : ℂ)
        + ∑ ζ ∈ Spec, (Complex.normSq (a ζ) : ℂ)
        + (a 0 * ∑ ζ ∈ Spec, (starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x))
        + ((starRingEnd ℂ) (a 0) * ∑ ζ ∈ Spec, a ζ * forwardChar ζ x)
        + ∑ ξ ∈ Spec, ∑ ζ ∈ Spec with ζ ≠ ξ,
            a ξ * (starRingEnd ℂ) (a ζ)
              * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x)) := by
  classical
  have hfx : (Complex.normSq (f x) : ℂ) = f x * (starRingEnd ℂ) (f x) :=
    (Complex.mul_conj (f x)).symm
  rw [hfx, hf.expand x]
  rw [map_add]
  have hconjSum :
      (starRingEnd ℂ) (∑ ζ ∈ Spec, a ζ * forwardChar ζ x)
        = ∑ ζ ∈ Spec,
            (starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x) := by
    rw [map_sum]
    refine Finset.sum_congr rfl (fun ζ _ => ?_)
    exact map_mul _ _ _
  rw [hconjSum]
  set T : ℂ := ∑ ζ ∈ Spec, a ζ * forwardChar ζ x with hTdef
  set Sconj : ℂ :=
      ∑ ζ ∈ Spec, (starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x)
    with hSdef
  have hdiag0 : a 0 * (starRingEnd ℂ) (a 0) = (Complex.normSq (a 0) : ℂ) :=
    Complex.mul_conj (a 0)
  have hTS :
      T * Sconj
        = (∑ ζ ∈ Spec, (Complex.normSq (a ζ) : ℂ))
          + ∑ ξ ∈ Spec, ∑ ζ ∈ Spec with ζ ≠ ξ,
              a ξ * (starRingEnd ℂ) (a ζ)
                * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x)) := by
    rw [hTdef, hSdef, Finset.sum_mul_sum]
    have hreorder :
        ∀ ξ ∈ Spec, ∀ ζ ∈ Spec,
          a ξ * forwardChar ξ x
              * ((starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x))
            = a ξ * (starRingEnd ℂ) (a ζ)
                * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x)) := by
      intro ξ _ ζ _; ring
    rw [Finset.sum_congr rfl
          (fun ξ hξ => Finset.sum_congr rfl (fun ζ hζ => hreorder ξ hξ ζ hζ))]
    rw [← Finset.sum_add_distrib]
    refine Finset.sum_congr rfl (fun ξ hξ => ?_)
    have hcharSelf :
        forwardChar ξ x * (starRingEnd ℂ) (forwardChar ξ x) = (1 : ℂ) := by
      rw [forwardChar_mul_conj, sub_self, forwardChar_zero]
    have hdiagξ :
        a ξ * (starRingEnd ℂ) (a ξ)
              * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ξ x))
          = (Complex.normSq (a ξ) : ℂ) := by
      rw [hcharSelf, mul_one]
      exact Complex.mul_conj (a ξ)
    rw [← Finset.add_sum_erase _ _ hξ, hdiagξ]
    congr 1
    rw [← Finset.filter_ne' Spec ξ]
  have hexpand :
      (a 0 + T) * ((starRingEnd ℂ) (a 0) + Sconj)
        = a 0 * (starRingEnd ℂ) (a 0) + a 0 * Sconj
            + (starRingEnd ℂ) (a 0) * T + T * Sconj := by
    ring
  rw [hexpand, hdiag0, hTS]
  ring

/-! ### Hoisted transitive axioms (catch #21f bucket-3) — mirrors of
those in `BohrPlancherel.lean`. -/

/-- Forward-character zero-Bohr-mean axiom (mirror). -/
axiom hasBohrMean_forwardChar_of_ne_zero
    {ζ : Fin n → ℝ} (hζ : ζ ≠ 0) :
    HasBohrMean (forwardChar ζ) (0 : ℂ)

/-- Off-diagonal kill (mirror of the closed
`bohrMean_character_pair_off_diag` from BohrPlancherel.lean, hoisted as
an axiom in this smoke file because the closed proof body relies on the
real `bohrCharacter` and the same transitive axiom). -/
axiom bohrMean_character_pair_off_diag
    {ξ ζ : Fin n → ℝ} (hξζ : ξ ≠ ζ) :
    HasBohrMean
      (fun x : Fin n → ℝ =>
        forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x))
      (0 : ℂ)

/-- Const-times-zero-mean preserves zero (mirror). -/
axiom hasBohrMean_const_mul_zero
    {f : (Fin n → ℝ) → ℂ} (c : ℂ) (hf : HasBohrMean f (0 : ℂ)) :
    HasBohrMean (fun x => c * f x) (0 : ℂ)

/-- Finite sum of zero-mean is zero-mean (mirror). -/
axiom hasBohrMean_finset_sum_zero
    {ι : Type*} {s : Finset ι} {g : ι → (Fin n → ℝ) → ℂ}
    (hg : ∀ i ∈ s, HasBohrMean (g i) (0 : ℂ)) :
    HasBohrMean (fun x => ∑ i ∈ s, g i x) (0 : ℂ)

/-- Linear-assembly axiom (mirror). -/
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

/-! ### The closure under test — verbatim proof body of
`bohrPlancherel_finiteSpec` from `BohrPlancherel.lean`. -/

theorem bohrPlancherel_finiteSpec
    {Spec : Finset (Fin n → ℝ)} {a : (Fin n → ℝ) → ℂ} {f : (Fin n → ℝ) → ℂ}
    (hf : IsTrigPolyVelocity Spec a f) :
    HasBohrMean
      (fun x => (Complex.normSq (f x) : ℂ))
      ((Complex.normSq (a 0) : ℂ)
        + ∑ ζ ∈ Spec, (Complex.normSq (a ζ) : ℂ)) := by
  classical
  have hζne : ∀ ζ ∈ Spec, ζ ≠ 0 := by
    intro ζ hζmem hζ0
    exact hf.zero_not_mem (hζ0 ▸ hζmem)
  have hconj_char_zero : ∀ ζ ∈ Spec,
      HasBohrMean (fun x : Fin n → ℝ => (starRingEnd ℂ) (forwardChar ζ x))
                  (0 : ℂ) := by
    intro ζ hζ
    have hζn : ζ ≠ 0 := hζne ζ hζ
    have hnegζ : -ζ ≠ 0 := neg_ne_zero.mpr hζn
    have hpt : (fun x : Fin n → ℝ => (starRingEnd ℂ) (forwardChar ζ x))
                = (fun x : Fin n → ℝ => forwardChar (-ζ) x) := by
      funext x
      have := forwardChar_mul_conj 0 ζ x
      simp [forwardChar_zero, zero_sub] at this
      exact this
    rw [hpt]
    exact hasBohrMean_forwardChar_of_ne_zero hnegζ
  have hg₂ :
      HasBohrMean
        (fun x : Fin n → ℝ =>
          a 0 * ∑ ζ ∈ Spec,
            (starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x))
        (0 : ℂ) := by
    have hsum :
        HasBohrMean
          (fun x : Fin n → ℝ =>
            ∑ ζ ∈ Spec,
              (starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x))
          (0 : ℂ) := by
      refine hasBohrMean_finset_sum_zero (s := Spec)
        (g := fun ζ x =>
          (starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x)) ?_
      intro ζ hζ
      exact hasBohrMean_const_mul_zero ((starRingEnd ℂ) (a ζ))
        (hconj_char_zero ζ hζ)
    exact hasBohrMean_const_mul_zero (a 0) hsum
  have hg₃ :
      HasBohrMean
        (fun x : Fin n → ℝ =>
          (starRingEnd ℂ) (a 0) * ∑ ζ ∈ Spec, a ζ * forwardChar ζ x)
        (0 : ℂ) := by
    have hsum :
        HasBohrMean
          (fun x : Fin n → ℝ => ∑ ζ ∈ Spec, a ζ * forwardChar ζ x)
          (0 : ℂ) := by
      refine hasBohrMean_finset_sum_zero (s := Spec)
        (g := fun ζ x => a ζ * forwardChar ζ x) ?_
      intro ζ hζ
      exact hasBohrMean_const_mul_zero (a ζ)
        (hasBohrMean_forwardChar_of_ne_zero (hζne ζ hζ))
    exact hasBohrMean_const_mul_zero ((starRingEnd ℂ) (a 0)) hsum
  have hg₄ :
      HasBohrMean
        (fun x : Fin n → ℝ =>
          ∑ ξ ∈ Spec, ∑ ζ ∈ Spec with ζ ≠ ξ,
            a ξ * (starRingEnd ℂ) (a ζ)
              * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x)))
        (0 : ℂ) := by
    refine hasBohrMean_finset_sum_zero (s := Spec)
      (g := fun ξ x =>
        ∑ ζ ∈ Spec with ζ ≠ ξ,
          a ξ * (starRingEnd ℂ) (a ζ)
            * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x))) ?_
    intro ξ _hξ
    refine hasBohrMean_finset_sum_zero (s := Spec.filter (fun ζ => ζ ≠ ξ))
      (g := fun ζ x =>
        a ξ * (starRingEnd ℂ) (a ζ)
          * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x))) ?_
    intro ζ hζmem
    rw [Finset.mem_filter] at hζmem
    obtain ⟨_hζSpec, hζneξ⟩ := hζmem
    have hξne : ξ ≠ ζ := (Ne.symm hζneξ)
    have hchar :
        HasBohrMean
          (fun x : Fin n → ℝ =>
            forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x))
          (0 : ℂ) :=
      bohrMean_character_pair_off_diag hξne
    exact hasBohrMean_const_mul_zero (a ξ * (starRingEnd ℂ) (a ζ)) hchar
  have hAssembled :
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
          + ∑ ζ ∈ Spec, (Complex.normSq (a ζ) : ℂ)) :=
    bohrPlancherel_linear_assembly (Spec := Spec) (a := a) hg₂ hg₃ hg₄
  have hpt : (fun x : Fin n → ℝ => (Complex.normSq (f x) : ℂ))
              = (fun x : Fin n → ℝ =>
                  ((Complex.normSq (a 0) : ℂ)
                    + ∑ ζ ∈ Spec, (Complex.normSq (a ζ) : ℂ))
                  + (a 0 * ∑ ζ ∈ Spec,
                        (starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x))
                  + ((starRingEnd ℂ) (a 0) * ∑ ζ ∈ Spec, a ζ * forwardChar ζ x)
                  + ∑ ξ ∈ Spec, ∑ ζ ∈ Spec with ζ ≠ ξ,
                      a ξ * (starRingEnd ℂ) (a ζ)
                        * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x))) := by
    funext x
    exact normSq_trigPoly_expand hf x
  rw [hpt]
  exact hAssembled

end AlmostPeriodicSmokeBFinitespec
