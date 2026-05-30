import Mathlib.Tactic

namespace ZtareProofs

/-!
Scalar bookkeeping for the Phase 5EL gain/tax tether.

This is not a Navier-Stokes theorem.  It records the exact algebraic
obligation exposed by the local Fourier audits.  With normalized mixed defect
one, the full residual polynomial has the form

  D(t) = t^2 + 2 b t^3 + c t^4

and signed profit has the form `gamma * t^2`.  To beat a target `T`, the
amplitude must have `t^2 > T / gamma`; at the threshold amplitude `x`, self-tax
above the cross-aware allowance already makes the defect reach one.
-/

/-- If the amplitude square is below the target/gain threshold, the signed
profit cannot exceed the target. -/
theorem gain_times_amp_sq_le_target_of_amp_sq_le
    {gamma target ampSq : Real}
    (hgamma : 0 < gamma)
    (hamp : ampSq ≤ target / gamma) :
    gamma * ampSq ≤ target := by
  have hmul : gamma * ampSq ≤ gamma * (target / gamma) :=
    mul_le_mul_of_nonneg_left hamp (le_of_lt hgamma)
  have hsimpl : gamma * (target / gamma) = target := by
    field_simp [hgamma.ne']
  simpa [hsimpl] using hmul

/-- Reverse form of the gain/amplitude threshold.

This is the algebraic bridge used by source-facing PDE receipts: it is often
more natural to prove the gain action cap `gamma * ampSq <= target`, then let
Lean convert it into the threshold amplitude-square bound. -/
theorem amp_sq_le_of_gain_times_amp_sq_le_target
    {gamma target ampSq : Real}
    (hgamma : 0 < gamma)
    (hcap : gamma * ampSq ≤ target) :
    ampSq ≤ target / gamma := by
  have hmul : gamma * ampSq / gamma ≤ target / gamma :=
    div_le_div_of_nonneg_right hcap (le_of_lt hgamma)
  have hcancel : gamma * ampSq / gamma = ampSq := by
    field_simp [hgamma.ne']
  simpa [hcancel] using hmul

/-- Square-root threshold form of a gain action cap. -/
theorem amp_sq_le_sqrt_sq_of_gain_times_amp_sq_le_target
    {gamma target ampSq : Real}
    (hgamma : 0 < gamma)
    (htarget : 0 ≤ target)
    (hcap : gamma * ampSq ≤ target) :
    ampSq ≤ (Real.sqrt (target / gamma)) ^ (2 : Nat) := by
  have hdiv : ampSq ≤ target / gamma :=
    amp_sq_le_of_gain_times_amp_sq_le_target hgamma hcap
  have hratio_nonnegative : 0 ≤ target / gamma :=
    div_nonneg htarget (le_of_lt hgamma)
  have hroot :
      (Real.sqrt (target / gamma)) ^ (2 : Nat) = target / gamma := by
    simpa using Real.sq_sqrt hratio_nonnegative
  simpa [hroot] using hdiv

/-- Cross-aware self-tax allowance.

At a threshold amplitude `x>0`, if

  c >= (1 - x^2 - 2*b*x^3) / x^4,

then the normalized full residual defect has already reached at least one:

  1 <= x^2 + 2*b*x^3 + c*x^4.

This is the algebra behind the Phase 5EL margin column. -/
theorem defect_ge_one_of_self_tax_ge_cross_aware_allowance
    {x b c : Real}
    (hx : 0 < x)
    (hc : (1 - x ^ (2 : Nat) - 2 * b * x ^ (3 : Nat)) / x ^ (4 : Nat) ≤ c) :
    1 ≤ x ^ (2 : Nat) + 2 * b * x ^ (3 : Nat) + c * x ^ (4 : Nat) := by
  have hx4_pos : 0 < x ^ (4 : Nat) := pow_pos hx 4
  have hmul :
      ((1 - x ^ (2 : Nat) - 2 * b * x ^ (3 : Nat)) / x ^ (4 : Nat))
          * x ^ (4 : Nat) ≤ c * x ^ (4 : Nat) :=
    mul_le_mul_of_nonneg_right hc (le_of_lt hx4_pos)
  have hleft :
      ((1 - x ^ (2 : Nat) - 2 * b * x ^ (3 : Nat)) / x ^ (4 : Nat))
          * x ^ (4 : Nat)
        = 1 - x ^ (2 : Nat) - 2 * b * x ^ (3 : Nat) := by
    field_simp [ne_of_gt hx4_pos]
  nlinarith

end ZtareProofs
