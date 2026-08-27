import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialTimeSeparation

/-!
# Exact polynomial substitution orders on ramified meromorphic germs

Two local rules are proved from polynomial factorizations:

* at a finite center, root multiplicity multiplies the order of the source
  displacement;
* at a pole, polynomial degree multiplies the pole order.

The second rule uses an explicitly supplied analytic reciprocal extension and
the polynomial-reversal identity.  No asymptotic evaluation at infinity is
assumed.
-/

namespace FormalPolynomialMeromorphicOrder

open Filter Polynomial
open scoped Topology
open FormalPolynomialTimeSeparation

noncomputable def shiftedPolynomial
    (p : ℂ[X]) (center : ℂ) : ℂ[X] :=
  p.comp (Polynomial.X + Polynomial.C center)

noncomputable def shiftedRootUnit
    (p : ℂ[X]) (center : ℂ) : ℂ[X] :=
  (p /ₘ (Polynomial.X - Polynomial.C center) ^
      p.rootMultiplicity center).comp
    (Polynomial.X + Polynomial.C center)

theorem shiftedPolynomial_eq_rootPower_mul_unit
    (p : ℂ[X]) (center : ℂ) :
    shiftedPolynomial p center =
      Polynomial.X ^ p.rootMultiplicity center *
        shiftedRootUnit p center := by
  have h := p.pow_mul_divByMonic_rootMultiplicity_eq center
  have hc := congrArg (fun q : ℂ[X] ↦
    q.comp (Polynomial.X + Polynomial.C center)) h
  simpa [shiftedPolynomial, shiftedRootUnit, Polynomial.mul_comp,
    Polynomial.pow_comp, Polynomial.sub_comp] using hc.symm

theorem shiftedRootUnit_constantCoeff_ne_zero
    {p : ℂ[X]} (hp : p ≠ 0) (center : ℂ) :
    (shiftedRootUnit p center).coeff 0 ≠ 0 := by
  rw [Polynomial.coeff_zero_eq_eval_zero, shiftedRootUnit,
    Polynomial.eval_comp, Polynomial.eval_add, Polynomial.eval_X,
    Polynomial.eval_C, zero_add]
  exact Polynomial.eval_divByMonic_pow_rootMultiplicity_ne_zero center hp

/-- Polynomial evaluation preserves meromorphicity of a scalar germ. -/
theorem meromorphicAt_eval_polynomial
    {f : ℂ → ℂ} {x : ℂ} (hf : MeromorphicAt f x)
    (p : ℂ[X]) : MeromorphicAt (fun t ↦ p.eval (f t)) x := by
  induction p using Polynomial.induction_on' with
  | add p q hp hq =>
      simpa only [Polynomial.eval_add, Pi.add_apply] using hp.add hq
  | monomial n a =>
      simpa only [Polynomial.eval_monomial, Pi.mul_apply,
        Pi.pow_apply] using (MeromorphicAt.const a x).mul (hf.pow n)

private theorem shifted_eval_factorization
    (p : ℂ[X]) (center value : ℂ) :
    p.eval (center + value) =
      value ^ p.rootMultiplicity center *
        (shiftedRootUnit p center).eval value := by
  have hfactor := shiftedPolynomial_eq_rootPower_mul_unit p center
  have heval := congrArg (Polynomial.eval value) hfactor
  simpa [shiftedPolynomial, Polynomial.eval_comp, add_comm,
    add_left_comm, add_assoc] using heval

/-- At a finite center, substitution multiplies polynomial root multiplicity
by the positive order of the analytic displacement. -/
theorem meromorphicOrderAt_polynomial_eval_at_finite_center
    (p : ℂ[X]) (hp : p ≠ 0) (center : ℂ)
    (source : ℂ → ℂ) (x : ℂ) (q : ℕ)
    (hsourceAnalytic : AnalyticAt ℂ source x)
    (hsourceZero : source x = 0)
    (hsourceOrder :
      meromorphicOrderAt source x = ((q : ℤ) : WithTop ℤ)) :
    meromorphicOrderAt (fun t ↦ p.eval (center + source t)) x =
      (((q * p.rootMultiplicity center : ℕ) : ℤ) : WithTop ℤ) := by
  let unit : ℂ → ℂ := fun t ↦
    (shiftedRootUnit p center).eval (source t)
  have hunitAnalytic : AnalyticAt ℂ unit x := by
    simpa [unit, Polynomial.aeval_def] using
      hsourceAnalytic.aeval_polynomial (shiftedRootUnit p center)
  have hunitNonzero : unit x ≠ 0 := by
    simpa [unit, hsourceZero, ← Polynomial.coeff_zero_eq_eval_zero] using
      shiftedRootUnit_constantCoeff_ne_zero hp center
  have hunitOrder : meromorphicOrderAt unit x = 0 := by
    rw [hunitAnalytic.meromorphicOrderAt_eq,
      hunitAnalytic.analyticOrderAt_eq_zero.mpr hunitNonzero]
    simp
  have hfactor :
      (fun t ↦ p.eval (center + source t)) =
        source ^ p.rootMultiplicity center * unit := by
    funext t
    exact shifted_eval_factorization p center (source t)
  rw [hfactor, meromorphicOrderAt_mul
      (hsourceAnalytic.meromorphicAt.pow _) hunitAnalytic.meromorphicAt,
    meromorphicOrderAt_pow hsourceAnalytic.meromorphicAt,
    hsourceOrder, hunitOrder]
  norm_cast
  simp [mul_comm]

/-- At a meromorphic pole, polynomial degree multiplies the pole order.  The
analytic reciprocal extension is part of the normalized branch data. -/
theorem meromorphicOrderAt_polynomial_eval_at_pole
    (p : ℂ[X]) (hp : p ≠ 0) (degree : ℕ)
    (hdegree : p.natDegree = degree)
    (inner reciprocal : ℂ → ℂ) (x : ℂ) (r : ℕ)
    (hinner : MeromorphicAt inner x)
    (hinnerOrder :
      meromorphicOrderAt inner x = ((-(r : ℤ) : ℤ) : WithTop ℤ))
    (hreciprocalAnalytic : AnalyticAt ℂ reciprocal x)
    (hreciprocalZero : reciprocal x = 0)
    (hreciprocal :
      reciprocal =ᶠ[𝓝[≠] (x : ℂ)] (fun t ↦ (inner t)⁻¹)) :
    meromorphicOrderAt (fun t ↦ p.eval (inner t)) x =
      (((-(r : ℤ) * degree : ℤ)) : WithTop ℤ) := by
  let reverseUnit : ℂ → ℂ := fun t ↦ p.reverse.eval (reciprocal t)
  have hreverseAnalytic : AnalyticAt ℂ reverseUnit x := by
    simpa [reverseUnit, Polynomial.aeval_def] using
      hreciprocalAnalytic.aeval_polynomial p.reverse
  have hreverseAt : reverseUnit x = p.leadingCoeff := by
    simp [reverseUnit, hreciprocalZero, ← Polynomial.coeff_zero_eq_eval_zero,
      Polynomial.coeff_zero_reverse]
  have hreverseNonzero : reverseUnit x ≠ 0 := by
    rw [hreverseAt]
    exact Polynomial.leadingCoeff_ne_zero.mpr hp
  have hreverseOrder : meromorphicOrderAt reverseUnit x = 0 := by
    rw [hreverseAnalytic.meromorphicOrderAt_eq,
      hreverseAnalytic.analyticOrderAt_eq_zero.mpr hreverseNonzero]
    simp
  have hinnerNonzero : ∀ᶠ t in 𝓝[≠] x, inner t ≠ 0 := by
    have hnotTop : meromorphicOrderAt inner x ≠ ⊤ := by
      rw [hinnerOrder]
      simp
    exact (meromorphicOrderAt_ne_top_iff_eventually_ne_zero hinner).mp
      hnotTop
  have hfactor :
      (fun t ↦ p.eval (inner t)) =ᶠ[𝓝[≠] x]
        fun t ↦ inner t ^ degree * reverseUnit t := by
    filter_upwards [hreciprocal, hinnerNonzero] with t hrec hnonzero
    calc
      p.eval (inner t) =
          p.reverse.eval (inner t)⁻¹ * inner t ^ p.natDegree :=
        (reverse_eval_inv_mul_pow p hnonzero).symm
      _ = reverseUnit t * inner t ^ degree := by
        simp only [reverseUnit, hdegree, hrec]
      _ = inner t ^ degree * reverseUnit t := mul_comm _ _
  rw [meromorphicOrderAt_congr hfactor]
  change meromorphicOrderAt (inner ^ degree * reverseUnit) x =
    (((-(r : ℤ) * degree : ℤ)) : WithTop ℤ)
  rw [
    meromorphicOrderAt_mul (hinner.pow degree)
      hreverseAnalytic.meromorphicAt,
    meromorphicOrderAt_pow hinner, hinnerOrder, hreverseOrder]
  norm_cast
  ring

/-- Aggregated exact substitution-order surface. -/
theorem polynomial_meromorphic_order_terminal_certificate :
    (∀ (p : ℂ[X]), p ≠ 0 → ∀ (center : ℂ) (source : ℂ → ℂ)
      (x : ℂ) (q : ℕ),
      AnalyticAt ℂ source x → source x = 0 →
      meromorphicOrderAt source x = ((q : ℤ) : WithTop ℤ) →
      meromorphicOrderAt (fun t ↦ p.eval (center + source t)) x =
        (((q * p.rootMultiplicity center : ℕ) : ℤ) : WithTop ℤ)) ∧
    (∀ (p : ℂ[X]), p ≠ 0 → ∀ (degree : ℕ),
      p.natDegree = degree →
      ∀ (inner reciprocal : ℂ → ℂ) (x : ℂ) (r : ℕ),
      MeromorphicAt inner x →
      meromorphicOrderAt inner x =
        ((-(r : ℤ) : ℤ) : WithTop ℤ) →
      AnalyticAt ℂ reciprocal x → reciprocal x = 0 →
      reciprocal =ᶠ[𝓝[≠] (x : ℂ)] (fun t ↦ (inner t)⁻¹) →
      meromorphicOrderAt (fun t ↦ p.eval (inner t)) x =
        (((-(r : ℤ) * degree : ℤ)) : WithTop ℤ)) := by
  constructor
  · intro p hp center source x q hsource hzero horder
    exact meromorphicOrderAt_polynomial_eval_at_finite_center
      p hp center source x q hsource hzero horder
  · intro p hp degree hdegree inner reciprocal x r hinner horder
      hreciprocalAnalytic hreciprocalZero hreciprocal
    exact meromorphicOrderAt_polynomial_eval_at_pole
      p hp degree hdegree inner reciprocal x r hinner horder
      hreciprocalAnalytic hreciprocalZero hreciprocal

end FormalPolynomialMeromorphicOrder
