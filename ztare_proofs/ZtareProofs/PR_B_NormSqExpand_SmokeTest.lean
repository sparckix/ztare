/-
Smoke test for the closure of `normSq_trigPoly_expand`
(PR-B sorry, BohrPlancherel.lean) — closed 2026-05-08.

The PR-B file lives outside the main lake target (under
`projects/.../research_notes/mathlib_upstream_candidates/BohrPlancherel.lean`),
so we cannot import it directly. Instead, we mirror the relevant
definitions (`forwardChar`, `IsTrigPolyVelocity`) and the supporting
lemmas (`forwardChar_zero`, `forwardChar_mul_conj`) — which are already
closed upstream — and then reproduce the `normSq_trigPoly_expand` proof
verbatim. If this file type-checks, the proof body is sound.

Mathlib chain consumed by the proof:
  - `Complex.mul_conj`             (Mathlib/Data/Complex/Basic.lean:564)
  - `map_add`, `map_sum`, `map_mul` (Mathlib `RingHom`/`AddMonoidHom` API)
  - `Finset.sum_mul_sum`           (Mathlib/Algebra/BigOperators/Ring/Finset.lean:59)
  - `Finset.sum_add_distrib`       (Mathlib/Algebra/BigOperators/Group/Finset/*)
  - `Finset.add_sum_erase`         (Mathlib/Algebra/BigOperators/Group/Finset/Basic.lean:741)
  - `Finset.filter_ne'`            (Mathlib/Data/Finset/Basic.lean:420)
  - `forwardChar_zero`, `forwardChar_mul_conj`  (this file's mirrors)

T9 chain impact: this advances `bohrPlancherel_finiteSpec` (the Bessel
direction T9 depends on).
-/
import Mathlib.Analysis.SpecialFunctions.Complex.Circle
import Mathlib.Analysis.Complex.Exponential

open Complex
open scoped BigOperators ComplexConjugate

namespace AlmostPeriodicSmokeBNormSq

variable {n : ℕ}

/-- Mirror of `BohrPlancherel.forwardChar`. -/
noncomputable def forwardChar (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp ((2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

@[simp] lemma forwardChar_zero (x : Fin n → ℝ) :
    forwardChar (0 : Fin n → ℝ) x = 1 := by
  simp [forwardChar]

/-- Mirror of `BohrPlancherel.forwardChar_mul_conj` — already closed in
the upstream file, repeated here verbatim for self-containment. -/
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

/-- Carrier-lock helper: a forward character times its conjugate has unit
    modulus.  This isolates the same-carrier character/conjugation step used
    inside the norm-square expansion. -/
lemma forwardChar_mul_conj_self (ξ : Fin n → ℝ) (x : Fin n → ℝ) :
    forwardChar ξ x * (starRingEnd ℂ) (forwardChar ξ x) = (1 : ℂ) := by
  rw [forwardChar_mul_conj, sub_self, forwardChar_zero]

/-- Mirror of `BohrPlancherel.IsTrigPolyVelocity` (with `Σ` renamed to
`Spec` because `Σ` is reserved syntax for sigma types in pure Lean —
the upstream file uses `Σ` only because Mathlib re-opens / shadows that
token in its internals; here we play it safe). -/
structure IsTrigPolyVelocity
    (Spec : Finset (Fin n → ℝ)) (a : (Fin n → ℝ) → ℂ)
    (f : (Fin n → ℝ) → ℂ) : Prop where
  zero_not_mem : (0 : Fin n → ℝ) ∉ Spec
  expand : ∀ x : Fin n → ℝ,
    f x = a 0 + ∑ ζ ∈ Spec, a ζ * forwardChar ζ x

/-- Incidence/budget adapter: multiplying the nonzero-frequency packet by its
    conjugate splits into the diagonal norm-square budget and the off-diagonal
    incidence sum.  This is the finite-sum core of the norm-square expansion,
    isolated from the endpoint lemma so a workstation has to route through
    support incidence, diagonal budget, and character-lock facts. -/
lemma trigPoly_packet_mul_conj_split
    (Spec : Finset (Fin n → ℝ)) (a : (Fin n → ℝ) → ℂ) (x : Fin n → ℝ) :
    (∑ ξ ∈ Spec, a ξ * forwardChar ξ x)
      * (∑ ζ ∈ Spec, (starRingEnd ℂ) (a ζ) * (starRingEnd ℂ) (forwardChar ζ x))
      = (∑ ζ ∈ Spec, (Complex.normSq (a ζ) : ℂ))
        + ∑ ξ ∈ Spec, ∑ ζ ∈ Spec with ζ ≠ ξ,
            a ξ * (starRingEnd ℂ) (a ζ)
              * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ζ x)) := by
  classical
  rw [Finset.sum_mul_sum]
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
      forwardChar ξ x * (starRingEnd ℂ) (forwardChar ξ x) = (1 : ℂ) :=
    forwardChar_mul_conj_self ξ x
  have hdiagξ :
      a ξ * (starRingEnd ℂ) (a ξ)
            * (forwardChar ξ x * (starRingEnd ℂ) (forwardChar ξ x))
        = (Complex.normSq (a ξ) : ℂ) := by
    rw [hcharSelf, mul_one]
    exact Complex.mul_conj (a ξ)
  rw [← Finset.add_sum_erase _ _ hξ, hdiagξ]
  congr 1
  rw [← Finset.filter_ne' Spec ξ]

/-- The closed lemma — verbatim copy of the proof body that now
appears in `BohrPlancherel.lean` at `normSq_trigPoly_expand`. -/
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
    rw [hTdef, hSdef]
    exact trigPoly_packet_mul_conj_split Spec a x
  have hexpand :
      (a 0 + T) * ((starRingEnd ℂ) (a 0) + Sconj)
        = a 0 * (starRingEnd ℂ) (a 0) + a 0 * Sconj
            + (starRingEnd ℂ) (a 0) * T + T * Sconj := by
    ring
  rw [hexpand, hdiag0, hTS]
  ring

end AlmostPeriodicSmokeBNormSq
