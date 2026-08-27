import Mathlib.Analysis.Calculus.IteratedDeriv.ConvergenceOnBall
import Mathlib.Analysis.Calculus.IteratedDeriv.Lemmas
import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.RingTheory.PowerSeries.Derivative
import ZtareProofs.FormalAnalyticTaylorTransport
import ZtareProofs.FormalPowerSeriesLinearODE

/-!
# Canonical Taylor algebra for scalar analytic germs

The coefficient carrier is Mathlib's iterated-derivative Taylor series.  The
results below connect its analytic representation to the algebra and
derivative on `PowerSeries`, so scalar analytic ODEs can be transported to
formal ODEs without assuming a target coefficient identity.
-/

namespace FormalAnalyticTaylorAlgebra

open PowerSeries
open FormalAnalyticTaylorTransport
open FormalPowerSeriesLinearODE

variable {𝕜 : Type*} [RCLike 𝕜]

/-- The canonical scalar Taylor series of `f` at `center`. -/
noncomputable def taylorPowerSeries (f : 𝕜 → 𝕜) (center : 𝕜) : 𝕜⟦X⟧ :=
  PowerSeries.mk fun n => iteratedDeriv n f center / (n.factorial : 𝕜)

@[simp]
theorem coeff_taylorPowerSeries (f : 𝕜 → 𝕜) (center : 𝕜) (n : ℕ) :
    coeff n (taylorPowerSeries f center) =
      iteratedDeriv n f center / (n.factorial : 𝕜) := by
  simp [taylorPowerSeries]

/-- Analyticity supplies the canonical Taylor representation used by the
formal transport layer. -/
theorem hasFPowerSeriesAt_taylorPowerSeries
    {f : 𝕜 → 𝕜} {center : 𝕜} (hf : AnalyticAt 𝕜 f center) :
    HasFPowerSeriesAt f
      (asFormalMultilinearSeries (taylorPowerSeries f center)) center := by
  simpa [asFormalMultilinearSeries, taylorPowerSeries] using
    hf.hasFPowerSeriesAt

@[simp]
theorem constantCoeff_taylorPowerSeries (f : 𝕜 → 𝕜) (center : 𝕜) :
    constantCoeff (taylorPowerSeries f center) = f center := by
  rw [← coeff_zero_eq_constantCoeff]
  simp [taylorPowerSeries]

@[simp]
theorem taylorPowerSeries_const (value center : 𝕜) :
    taylorPowerSeries (fun _ => value) center = C value := by
  ext n
  by_cases hn : n = 0
  · subst n
    simp [taylorPowerSeries]
  · simp [taylorPowerSeries, iteratedDeriv_const, coeff_C, hn]

@[simp]
theorem taylorPowerSeries_id_zero :
    taylorPowerSeries (fun z : 𝕜 => z) 0 = X := by
  ext n
  rcases n with _ | _ | n <;>
    simp [taylorPowerSeries, iteratedDeriv_fun_id, coeff_X]

/-- Taylor transport preserves addition of analytic germs. -/
theorem taylorPowerSeries_add
    {f g : 𝕜 → 𝕜} {center : 𝕜}
    (hf : AnalyticAt 𝕜 f center) (hg : AnalyticAt 𝕜 g center) :
    taylorPowerSeries (f + g) center =
      taylorPowerSeries f center + taylorPowerSeries g center := by
  ext n
  rw [coeff_taylorPowerSeries,
    iteratedDeriv_add hf.contDiffAt hg.contDiffAt]
  simp only [map_add, coeff_taylorPowerSeries]
  ring

/-- Taylor transport preserves negation. -/
theorem taylorPowerSeries_neg (f : 𝕜 → 𝕜) (center : 𝕜) :
    taylorPowerSeries (-f) center = -taylorPowerSeries f center := by
  ext n
  simp [coeff_taylorPowerSeries]
  ring

/-- Taylor transport preserves subtraction of analytic germs. -/
theorem taylorPowerSeries_sub
    {f g : 𝕜 → 𝕜} {center : 𝕜}
    (hf : AnalyticAt 𝕜 f center) (hg : AnalyticAt 𝕜 g center) :
    taylorPowerSeries (f - g) center =
      taylorPowerSeries f center - taylorPowerSeries g center := by
  ext n
  rw [coeff_taylorPowerSeries,
    iteratedDeriv_sub hf.contDiffAt hg.contDiffAt]
  simp only [map_sub, coeff_taylorPowerSeries]
  ring

/-- Eventually equal analytic germs have the same canonical Taylor series. -/
theorem taylorPowerSeries_eq_of_eventuallyEq
    {f g : 𝕜 → 𝕜} {center : 𝕜}
    (hf : AnalyticAt 𝕜 f center) (hg : AnalyticAt 𝕜 g center)
    (heq : f =ᶠ[nhds center] g) :
    taylorPowerSeries f center = taylorPowerSeries g center := by
  exact powerSeries_eq_of_eventuallyEq
    (hasFPowerSeriesAt_taylorPowerSeries hf)
    (hasFPowerSeriesAt_taylorPowerSeries hg) heq

/-- Taylor transport commutes with the scalar derivative. -/
theorem taylorPowerSeries_deriv (f : 𝕜 → 𝕜) (center : 𝕜) :
    taylorPowerSeries (deriv f) center =
      d⁄dX 𝕜 (taylorPowerSeries f center) := by
  ext n
  rw [coeff_derivative]
  simp only [coeff_taylorPowerSeries, ← iteratedDeriv_succ']
  rw [Nat.factorial_succ, Nat.cast_mul]
  have hn : ((n + 1 : ℕ) : 𝕜) ≠ 0 := by
    exact_mod_cast Nat.succ_ne_zero n
  field_simp
  simp only [Nat.cast_add, Nat.cast_one]

private theorem choose_mul_div_factorial
    (n i : ℕ) (hi : i ≤ n) (left right : 𝕜) :
    (n.choose i : 𝕜) * left * right / (n.factorial : 𝕜) =
      (left / (i.factorial : 𝕜)) *
        (right / ((n - i).factorial : 𝕜)) := by
  have hiFactorial : (i.factorial : 𝕜) ≠ 0 := by
    exact_mod_cast Nat.factorial_ne_zero i
  have hsubFactorial : ((n - i).factorial : 𝕜) ≠ 0 := by
    exact_mod_cast Nat.factorial_ne_zero (n - i)
  have hnFactorial : (n.factorial : 𝕜) ≠ 0 := by
    exact_mod_cast Nat.factorial_ne_zero n
  have hfactorial :
      (n.choose i : 𝕜) * (i.factorial : 𝕜) *
          ((n - i).factorial : 𝕜) = (n.factorial : 𝕜) := by
    exact_mod_cast Nat.choose_mul_factorial_mul_factorial hi
  field_simp
  rw [← hfactorial]
  ring

/-- Taylor transport preserves multiplication of scalar analytic germs. -/
theorem taylorPowerSeries_mul
    {f g : 𝕜 → 𝕜} {center : 𝕜}
    (hf : AnalyticAt 𝕜 f center) (hg : AnalyticAt 𝕜 g center) :
    taylorPowerSeries (f * g) center =
      taylorPowerSeries f center * taylorPowerSeries g center := by
  ext n
  rw [coeff_taylorPowerSeries,
    iteratedDeriv_mul hf.contDiffAt hg.contDiffAt,
    PowerSeries.coeff_mul,
    Finset.Nat.sum_antidiagonal_eq_sum_range_succ_mk,
    div_eq_mul_inv, Finset.sum_mul]
  apply Finset.sum_congr rfl
  intro i hi
  rw [coeff_taylorPowerSeries, coeff_taylorPowerSeries]
  have hin : i ≤ n := by
    exact Nat.le_of_lt_succ (Finset.mem_range.mp hi)
  simpa [div_eq_mul_inv] using
    choose_mul_div_factorial n i hin
      (iteratedDeriv i f center) (iteratedDeriv (n - i) g center)

/-- Taylor transport preserves natural powers of scalar analytic germs. -/
theorem taylorPowerSeries_pow
    {f : 𝕜 → 𝕜} {center : 𝕜} (hf : AnalyticAt 𝕜 f center)
    (n : ℕ) :
    taylorPowerSeries (fun z => f z ^ n) center =
      taylorPowerSeries f center ^ n := by
  induction n with
  | zero =>
      simpa using taylorPowerSeries_const (1 : 𝕜) center
  | succ n ih =>
      have hpow : AnalyticAt 𝕜 (fun z => f z ^ n) center := hf.pow n
      calc
        taylorPowerSeries (fun z => f z ^ (n + 1)) center =
            taylorPowerSeries (f * fun z => f z ^ n) center := by
          congr 1
          funext z
          simp only [Pi.mul_apply, pow_succ']
        _ = taylorPowerSeries f center *
              taylorPowerSeries (fun z => f z ^ n) center :=
          taylorPowerSeries_mul hf hpow
        _ = taylorPowerSeries f center ^ (n + 1) := by
          rw [ih, pow_succ']

/-- Taylor transport commutes with evaluation of a scalar polynomial. -/
theorem taylorPowerSeries_aeval_polynomial
    {f : 𝕜 → 𝕜} {center : 𝕜} (hf : AnalyticAt 𝕜 f center)
    (p : Polynomial 𝕜) :
    taylorPowerSeries (fun z => Polynomial.aeval (f z) p) center =
      Polynomial.aeval (taylorPowerSeries f center) p := by
  induction p using Polynomial.induction_on' with
  | add p q hp hq =>
      have hpAnalytic := hf.aeval_polynomial p
      have hqAnalytic := hf.aeval_polynomial q
      simp only [map_add]
      change taylorPowerSeries
          ((fun z => Polynomial.aeval (f z) p) +
            (fun z => Polynomial.aeval (f z) q)) center = _
      rw [taylorPowerSeries_add hpAnalytic hqAnalytic, hp, hq]
  | monomial n a =>
      simp only [Polynomial.aeval_def, Polynomial.eval₂_monomial]
      change taylorPowerSeries
          ((fun _ : 𝕜 => a) * (fun z => f z ^ n)) center = _
      calc
        taylorPowerSeries
              ((fun _ : 𝕜 => a) * (fun z => f z ^ n)) center =
            taylorPowerSeries (fun _ : 𝕜 => a) center *
              taylorPowerSeries (fun z => f z ^ n) center :=
          taylorPowerSeries_mul analyticAt_const (hf.pow n)
        _ = (algebraMap 𝕜 𝕜⟦X⟧) a *
              taylorPowerSeries f center ^ n := by
          rw [taylorPowerSeries_const, taylorPowerSeries_pow hf n]
          rfl

/-- An eventual analytic polynomial Julia identity transports to the exact
identity between the canonical Taylor series. -/
theorem taylorPowerSeries_polynomial_julia
    {base endpoint derivativeFactor : 𝕜 → 𝕜} {center : 𝕜}
    (hbase : AnalyticAt 𝕜 base center)
    (hendpoint : AnalyticAt 𝕜 endpoint center)
    (hderivativeFactor : AnalyticAt 𝕜 derivativeFactor center)
    (generator : Polynomial 𝕜)
    (hJulia :
      (fun z => Polynomial.aeval (endpoint z) generator) =ᶠ[nhds center]
        fun z => derivativeFactor z *
          Polynomial.aeval (base z) generator) :
    Polynomial.aeval (taylorPowerSeries endpoint center) generator =
      taylorPowerSeries derivativeFactor center *
        Polynomial.aeval (taylorPowerSeries base center) generator := by
  have hleft : AnalyticAt 𝕜
      (fun z => Polynomial.aeval (endpoint z) generator) center :=
    hendpoint.aeval_polynomial generator
  have hright : AnalyticAt 𝕜
      (fun z => derivativeFactor z *
        Polynomial.aeval (base z) generator) center :=
    hderivativeFactor.mul (hbase.aeval_polynomial generator)
  have hseries := taylorPowerSeries_eq_of_eventuallyEq
    hleft hright hJulia
  rw [taylorPowerSeries_aeval_polynomial hendpoint generator] at hseries
  calc
    Polynomial.aeval (taylorPowerSeries endpoint center) generator =
        taylorPowerSeries
          (fun z => derivativeFactor z *
            Polynomial.aeval (base z) generator) center := hseries
    _ = taylorPowerSeries derivativeFactor center *
          taylorPowerSeries
            (fun z => Polynomial.aeval (base z) generator) center := by
      simpa only [Pi.mul_apply] using
        taylorPowerSeries_mul hderivativeFactor
          (hbase.aeval_polynomial generator)
    _ = taylorPowerSeries derivativeFactor center *
          Polynomial.aeval (taylorPowerSeries base center) generator := by
      rw [taylorPowerSeries_aeval_polynomial hbase generator]

/-- Taylor transport preserves inversion of a nonvanishing analytic germ. -/
theorem taylorPowerSeries_inv
    {f : 𝕜 → 𝕜} {center : 𝕜}
    (hf : AnalyticAt 𝕜 f center) (hnonzero : f center ≠ 0) :
    taylorPowerSeries (fun z => (f z)⁻¹) center =
      (taylorPowerSeries f center)⁻¹ := by
  have hinv : AnalyticAt 𝕜 (fun z => (f z)⁻¹) center := hf.inv hnonzero
  have hproduct : AnalyticAt 𝕜
      (fun z => (f z)⁻¹ * f z) center := hinv.mul hf
  have hne : ∀ᶠ z in nhds center, f z ≠ 0 :=
    hf.continuousAt.eventually_ne hnonzero
  have heq : (fun z => (f z)⁻¹ * f z) =ᶠ[nhds center]
      (fun _ => (1 : 𝕜)) := by
    filter_upwards [hne] with z hz
    exact inv_mul_cancel₀ hz
  have hseries := taylorPowerSeries_eq_of_eventuallyEq
    hproduct analyticAt_const heq
  have hproductSeries :
      taylorPowerSeries (fun z => (f z)⁻¹ * f z) center =
        taylorPowerSeries (fun z => (f z)⁻¹) center *
          taylorPowerSeries f center := by
    simpa only [Pi.mul_apply] using taylorPowerSeries_mul hinv hf
  have honeSeries :
      taylorPowerSeries (fun _ : 𝕜 => (1 : 𝕜)) center = 1 := by
    simpa using taylorPowerSeries_const (1 : 𝕜) center
  have hmulOne :
      taylorPowerSeries (fun z => (f z)⁻¹) center *
        taylorPowerSeries f center = 1 := by
    rw [← hproductSeries, ← honeSeries]
    exact hseries
  apply (PowerSeries.eq_inv_iff_mul_eq_one ?_).mpr hmulOne
  simpa [constantCoeff_taylorPowerSeries] using hnonzero

/-- An analytic scalar linear ODE transports coefficient-for-coefficient to
the corresponding formal ODE. -/
theorem taylorPowerSeries_linearODE
    {coefficient endpoint : 𝕜 → 𝕜} {center : 𝕜}
    (hcoefficient : AnalyticAt 𝕜 coefficient center)
    (hendpoint : AnalyticAt 𝕜 endpoint center)
    (hODE : deriv endpoint =ᶠ[nhds center]
      fun z => coefficient z * endpoint z) :
    d⁄dX 𝕜 (taylorPowerSeries endpoint center) =
      taylorPowerSeries coefficient center *
        taylorPowerSeries endpoint center := by
  have hderiv : AnalyticAt 𝕜 (deriv endpoint) center := hendpoint.deriv
  have hproduct :
      AnalyticAt 𝕜 (fun z => coefficient z * endpoint z) center :=
    hcoefficient.mul hendpoint
  have hseries := powerSeries_eq_of_eventuallyEq
    (hasFPowerSeriesAt_taylorPowerSeries hderiv)
    (hasFPowerSeriesAt_taylorPowerSeries hproduct) hODE
  rw [taylorPowerSeries_deriv] at hseries
  calc
    d⁄dX 𝕜 (taylorPowerSeries endpoint center) =
        taylorPowerSeries (fun z => coefficient z * endpoint z) center :=
      hseries
    _ = taylorPowerSeries coefficient center *
          taylorPowerSeries endpoint center := by
      simpa only [Pi.mul_apply] using
        taylorPowerSeries_mul hcoefficient hendpoint

/-- The Taylor series of a normalized analytic solution is the constructed
normalized formal endpoint for the Taylor series of its coefficient. -/
theorem taylorPowerSeries_eq_normalizedEndpoint
    {coefficient endpoint : 𝕜 → 𝕜} {center : 𝕜}
    (hcoefficient : AnalyticAt 𝕜 coefficient center)
    (hendpoint : AnalyticAt 𝕜 endpoint center)
    (hvalue : endpoint center = 1)
    (hODE : deriv endpoint =ᶠ[nhds center]
      fun z => coefficient z * endpoint z) :
    taylorPowerSeries endpoint center =
      normalizedEndpoint (taylorPowerSeries coefficient center) := by
  apply linear_ode_solution_unique
  · rw [constantCoeff_taylorPowerSeries,
      normalizedEndpoint_constantCoeff, hvalue]
  · exact taylorPowerSeries_linearODE hcoefficient hendpoint hODE
  · exact normalizedEndpoint_derivative _

/-- Aggregated Taylor-to-formal linear-ODE transport certificate. -/
theorem analytic_taylor_linear_ode_terminal_certificate :
    ∀ {coefficient endpoint : 𝕜 → 𝕜} {center : 𝕜},
      AnalyticAt 𝕜 coefficient center →
      AnalyticAt 𝕜 endpoint center →
      endpoint center = 1 →
      deriv endpoint =ᶠ[nhds center]
        (fun z => coefficient z * endpoint z) →
      taylorPowerSeries endpoint center =
        normalizedEndpoint (taylorPowerSeries coefficient center) := by
  intro coefficient endpoint center hcoefficient hendpoint hvalue hODE
  exact taylorPowerSeries_eq_normalizedEndpoint
    hcoefficient hendpoint hvalue hODE

end FormalAnalyticTaylorAlgebra
