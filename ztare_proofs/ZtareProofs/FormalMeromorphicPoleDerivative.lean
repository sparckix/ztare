import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Tactic

/-!
# Derivative order at a finite nonzero meromorphic order

This file proves the exact one-step order drop under differentiation whenever
the meromorphic order is a nonzero integer.  Mathlib supplies meromorphic
normal form and meromorphicity of the derivative; the nonzero leading
coefficient is checked explicitly.
-/

namespace FormalMeromorphicPoleDerivative

open Filter

/-- Differentiation decreases every finite nonzero meromorphic order by
exactly one. -/
theorem meromorphicOrderAt_deriv_of_nonzero_integer_order
    (f : ℂ → ℂ) (x : ℂ) (n : ℤ)
    (hf : MeromorphicAt f x) (hn : n ≠ 0)
    (horder : meromorphicOrderAt f x = (n : WithTop ℤ)) :
    meromorphicOrderAt (deriv f) x = ((n - 1 : ℤ) : WithTop ℤ) := by
  obtain ⟨unit, hunitAnalytic, hunitNonzero, hnormal⟩ :=
    (meromorphicOrderAt_eq_int_iff hf).1 horder
  let nextUnit : ℂ → ℂ := fun z ↦
    (n : ℂ) * unit z + (z - x) * deriv unit z
  have hnextAnalytic : AnalyticAt ℂ nextUnit x := by
    dsimp [nextUnit]
    fun_prop
  have hnextValue : nextUnit x = (n : ℂ) * unit x := by
    simp [nextUnit]
  have hnComplex : (n : ℂ) ≠ 0 := by
    exact_mod_cast hn
  have hnextNonzero : nextUnit x ≠ 0 := by
    rw [hnextValue]
    exact mul_ne_zero hnComplex hunitNonzero
  apply (meromorphicOrderAt_eq_int_iff hf.deriv).2
  refine ⟨nextUnit, hnextAnalytic, hnextNonzero, ?_⟩
  have hderivNormal := EventuallyEq.nhdsNE_deriv hnormal
  filter_upwards [hderivNormal,
      eventually_nhdsWithin_of_eventually_nhds
        hunitAnalytic.eventually_analyticAt,
      self_mem_nhdsWithin] with z hz hunitAt hxz
  rw [hz]
  have hx : z - x ≠ 0 := sub_ne_zero.mpr hxz
  have hunitDifferentiable : DifferentiableAt ℂ unit z :=
    hunitAt.differentiableAt
  change deriv (fun x_1 ↦ (x_1 - x) ^ n * unit x_1) z =
    (z - x) ^ (n - 1) * nextUnit z
  have hpower : HasDerivAt (fun w : ℂ ↦ (w - x) ^ n)
      ((n : ℂ) * (z - x) ^ (n - 1)) z := by
    convert (hasDerivAt_zpow n (z - x) (Or.inl hx)).comp z
      ((hasDerivAt_id z).sub_const x) using 1
    all_goals simp
  have hproduct := hpower.mul hunitDifferentiable.hasDerivAt
  have hderiv :
      deriv (fun w : ℂ ↦ (w - x) ^ n * unit w) z =
        ((n : ℂ) * (z - x) ^ (n - 1)) * unit z +
          (z - x) ^ n * deriv unit z := by
    exact hproduct.deriv
  rw [hderiv]
  dsimp [nextUnit]
  rw [show n = (n - 1) + 1 by omega]
  rw [zpow_add₀ hx, zpow_one]
  ring_nf

/-- A meromorphic pole of positive order `r` has derivative pole order
`r + 1`. -/
theorem meromorphicOrderAt_deriv_of_pole
    (f : ℂ → ℂ) (x : ℂ) (r : ℕ)
    (hf : MeromorphicAt f x) (hr : 0 < r)
    (horder :
      meromorphicOrderAt f x = ((-(r : ℤ) : ℤ) : WithTop ℤ)) :
    meromorphicOrderAt (deriv f) x =
      (((-(r : ℤ) - 1 : ℤ)) : WithTop ℤ) := by
  apply meromorphicOrderAt_deriv_of_nonzero_integer_order
    f x (-(r : ℤ)) hf
  · omega
  · exact horder

/-- An analytic or meromorphic zero of positive finite order `q` has
derivative order `q - 1`. -/
theorem meromorphicOrderAt_deriv_of_positive_order
    (f : ℂ → ℂ) (x : ℂ) (q : ℕ)
    (hf : MeromorphicAt f x) (hq : 0 < q)
    (horder : meromorphicOrderAt f x = ((q : ℤ) : WithTop ℤ)) :
    meromorphicOrderAt (deriv f) x =
      (((q : ℤ) - 1 : ℤ) : WithTop ℤ) := by
  apply meromorphicOrderAt_deriv_of_nonzero_integer_order f x (q : ℤ) hf
  · exact_mod_cast (Nat.ne_zero_of_lt hq)
  · exact horder

/-- Aggregated reusable terminal surface. -/
theorem meromorphic_pole_derivative_terminal_certificate :
    (∀ (f : ℂ → ℂ) (x : ℂ) (n : ℤ),
      MeromorphicAt f x → n ≠ 0 →
      meromorphicOrderAt f x = (n : WithTop ℤ) →
      meromorphicOrderAt (deriv f) x = ((n - 1 : ℤ) : WithTop ℤ)) ∧
    (∀ (f : ℂ → ℂ) (x : ℂ) (r : ℕ),
      MeromorphicAt f x → 0 < r →
      meromorphicOrderAt f x = ((-(r : ℤ) : ℤ) : WithTop ℤ) →
      meromorphicOrderAt (deriv f) x =
        (((-(r : ℤ) - 1 : ℤ)) : WithTop ℤ)) := by
  constructor
  · intro f x n hf hn horder
    exact meromorphicOrderAt_deriv_of_nonzero_integer_order
      f x n hf hn horder
  · intro f x r hf hr horder
    exact meromorphicOrderAt_deriv_of_pole f x r hf hr horder

end FormalMeromorphicPoleDerivative
