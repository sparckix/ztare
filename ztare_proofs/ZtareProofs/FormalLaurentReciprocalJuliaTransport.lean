import Mathlib.Tactic
import ZtareProofs.FormalAnalyticTaylorAlgebra
import ZtareProofs.FormalAnalyticTwoJuliaAbelCollision
import ZtareProofs.FormalLaurentInversePolynomialNonvanishing
import ZtareProofs.FormalRatFuncLaurentTangentCarrier

/-!
# Reciprocal Julia identities in a Laurent chart

A Julia identity whose hidden endpoint has a pole cannot be Taylor-expanded
before clearing denominators.  This module clears the identity with the
analytic reciprocal germ, extends it across the puncture, and then transports
the exact equality to power and Laurent series.
-/

namespace FormalLaurentReciprocalJuliaTransport

open Filter Polynomial PowerSeries
open scoped LaurentSeries Topology

open FormalAnalyticTaylorAlgebra
open FormalAnalyticTwoJuliaAbelCollision
open FormalPolynomialTimeSeparation
open FormalRatFuncLaurentTangentCarrier

noncomputable section

abbrev PS := PowerSeries ℂ
abbrev LS := LaurentSeries ℂ

/-- Clearing a pointwise Julia row by the analytic reciprocal converts the
hidden polynomial evaluation to a reversed-polynomial evaluation. -/
theorem cleared_julia_identity
    (generator : ℂ[X]) (degree : ℕ)
    (hdegree : generator.natDegree = degree) (htwo : 2 ≤ degree)
    {reciprocal hidden source reciprocalDerivative hiddenDerivative
      sourceDerivative : ℂ}
    (hreciprocalDerivative :
      reciprocalDerivative = -hiddenDerivative / hidden ^ 2)
    (hreciprocal : reciprocal = hidden⁻¹)
    (hjulia :
      hiddenDerivative * generator.eval source =
        sourceDerivative * generator.eval hidden)
    (hhidden : hidden ≠ 0) :
    -reciprocalDerivative * reciprocal ^ (degree - 2) *
        generator.eval source =
      sourceDerivative * generator.reverse.eval reciprocal := by
  have hreverse := reverse_eval_inv_mul_pow generator hhidden
  rw [hdegree] at hreverse
  rw [hreciprocalDerivative, hreciprocal,
    inv_pow_sub₀ hhidden htwo]
  field_simp [hhidden] at hreverse ⊢
  nlinarith [hjulia, hreverse]

private theorem TwoJuliaAbelCarrier.cleared_julia_nhdsNE
    (carrier : TwoJuliaAbelCarrier)
    (generator : ℂ[X]) (degree : ℕ)
    (base baseDerivative : ℂ → ℂ)
    (hdegree : generator.natDegree = degree)
    (htwo : 2 ≤ degree)
    (hbaseDerivative : ∀ t ∈ carrier.domain,
      HasDerivAt base (baseDerivative t) t)
    (hjulia : ∀ t ∈ carrier.domain,
      carrier.hiddenDerivative t * generator.eval (base t) =
        baseDerivative t * generator.eval (carrier.hidden t)) :
    (fun t =>
      -deriv carrier.reciprocal t *
          carrier.reciprocal t ^ (degree - 2) * generator.eval (base t))
      =ᶠ[𝒩[0] carrier.center]
    fun t => deriv base t * generator.reverse.eval (carrier.reciprocal t) := by
  filter_upwards [carrier.punctured_mem] with t ht
  have hreciprocalDerivative := carrier.reciprocal_derivative t ht
  have hbaseDerivativeAt := hbaseDerivative t ht
  rw [hreciprocalDerivative.deriv, hbaseDerivativeAt.deriv]
  exact cleared_julia_identity generator degree hdegree htwo
    (carrier.reciprocal_derivative_eq t ht)
    (carrier.reciprocal_eq_inverse t ht) (hjulia t ht)
    (carrier.hidden_nonzero t ht)

private theorem TwoJuliaAbelCarrier.cleared_julia_nhds
    (carrier : TwoJuliaAbelCarrier)
    (generator : ℂ[X]) (degree : ℕ)
    (base baseDerivative : ℂ → ℂ)
    (hdegree : generator.natDegree = degree)
    (htwo : 2 ≤ degree)
    (hbaseAnalytic : AnalyticAt ℂ base carrier.center)
    (hbaseDerivative : ∀ t ∈ carrier.domain,
      HasDerivAt base (baseDerivative t) t)
    (hjulia : ∀ t ∈ carrier.domain,
      carrier.hiddenDerivative t * generator.eval (base t) =
        baseDerivative t * generator.eval (carrier.hidden t)) :
    (fun t =>
      -deriv carrier.reciprocal t *
          carrier.reciprocal t ^ (degree - 2) * generator.eval (base t))
      =ᶠ[nhds carrier.center]
    fun t => deriv base t * generator.reverse.eval (carrier.reciprocal t) := by
  have hleft : AnalyticAt ℂ
      (fun t =>
        -deriv carrier.reciprocal t *
          carrier.reciprocal t ^ (degree - 2) * generator.eval (base t))
      carrier.center := by
    exact ((carrier.reciprocal_analytic.deriv.neg.mul
      (carrier.reciprocal_analytic.pow (degree - 2))).mul
      (hbaseAnalytic.aeval_polynomial generator))
  have hright : AnalyticAt ℂ
      (fun t => deriv base t *
        generator.reverse.eval (carrier.reciprocal t)) carrier.center := by
    exact hbaseAnalytic.deriv.mul
      (carrier.reciprocal_analytic.aeval_polynomial generator.reverse)
  apply (ContinuousAt.eventuallyEq_nhds_iff_eventuallyEq_nhdsNE
    hleft.continuousAt hright.continuousAt).mp
  exact carrier.cleared_julia_nhdsNE generator degree base baseDerivative
    hdegree htwo hbaseDerivative hjulia

/-- Exact Taylor identity obtained after clearing one reciprocal Julia row. -/
theorem TwoJuliaAbelCarrier.cleared_julia_taylor
    (carrier : TwoJuliaAbelCarrier)
    (generator : ℂ[X]) (degree : ℕ)
    (base baseDerivative : ℂ → ℂ)
    (hdegree : generator.natDegree = degree)
    (htwo : 2 ≤ degree)
    (hbaseAnalytic : AnalyticAt ℂ base carrier.center)
    (hbaseDerivative : ∀ t ∈ carrier.domain,
      HasDerivAt base (baseDerivative t) t)
    (hjulia : ∀ t ∈ carrier.domain,
      carrier.hiddenDerivative t * generator.eval (base t) =
        baseDerivative t * generator.eval (carrier.hidden t)) :
    -(d⁄dX ℂ (taylorPowerSeries carrier.reciprocal carrier.center)) *
          taylorPowerSeries carrier.reciprocal carrier.center ^ (degree - 2) *
          Polynomial.aeval (taylorPowerSeries base carrier.center) generator =
      d⁄dX ℂ (taylorPowerSeries base carrier.center) *
        Polynomial.aeval
          (taylorPowerSeries carrier.reciprocal carrier.center)
          generator.reverse := by
  have hleft : AnalyticAt ℂ
      (fun t =>
        -deriv carrier.reciprocal t *
          carrier.reciprocal t ^ (degree - 2) * generator.eval (base t))
      carrier.center := by
    exact ((carrier.reciprocal_analytic.deriv.neg.mul
      (carrier.reciprocal_analytic.pow (degree - 2))).mul
      (hbaseAnalytic.aeval_polynomial generator))
  have hright : AnalyticAt ℂ
      (fun t => deriv base t *
        generator.reverse.eval (carrier.reciprocal t)) carrier.center := by
    exact hbaseAnalytic.deriv.mul
      (carrier.reciprocal_analytic.aeval_polynomial generator.reverse)
  have hseries := taylorPowerSeries_eq_of_eventuallyEq hleft hright
    (carrier.cleared_julia_nhds generator degree base baseDerivative
      hdegree htwo hbaseAnalytic hbaseDerivative hjulia)
  change taylorPowerSeries
      (((fun t => -deriv carrier.reciprocal t) *
          fun t => carrier.reciprocal t ^ (degree - 2)) *
        fun t => generator.eval (base t)) carrier.center = _ at hseries
  rw [taylorPowerSeries_mul
        (carrier.reciprocal_analytic.deriv.neg.mul
          (carrier.reciprocal_analytic.pow (degree - 2)))
        (hbaseAnalytic.aeval_polynomial generator),
      taylorPowerSeries_mul carrier.reciprocal_analytic.deriv.neg
        (carrier.reciprocal_analytic.pow (degree - 2)),
      taylorPowerSeries_neg, taylorPowerSeries_deriv,
      taylorPowerSeries_pow carrier.reciprocal_analytic,
      taylorPowerSeries_aeval_polynomial hbaseAnalytic] at hseries
  change taylorPowerSeries
      ((fun t => deriv base t) *
        fun t => generator.reverse.eval (carrier.reciprocal t))
      carrier.center = _ at hseries
  rw [taylorPowerSeries_mul hbaseAnalytic.deriv
        (carrier.reciprocal_analytic.aeval_polynomial generator.reverse),
      taylorPowerSeries_deriv,
      taylorPowerSeries_aeval_polynomial carrier.reciprocal_analytic]
    at hseries
  exact hseries

/-- Both rows of a two-Julia carrier admit exact cleared Taylor identities. -/
theorem TwoJuliaAbelCarrier.cleared_taylor_rows
    (carrier : TwoJuliaAbelCarrier) :
    -(d⁄dX ℂ (taylorPowerSeries carrier.reciprocal carrier.center)) *
          taylorPowerSeries carrier.reciprocal carrier.center ^
            (carrier.firstDegree - 2) *
          Polynomial.aeval
            (taylorPowerSeries carrier.source carrier.center)
            carrier.firstGenerator =
        d⁄dX ℂ (taylorPowerSeries carrier.source carrier.center) *
          Polynomial.aeval
            (taylorPowerSeries carrier.reciprocal carrier.center)
            carrier.firstGenerator.reverse ∧
      -(d⁄dX ℂ (taylorPowerSeries carrier.reciprocal carrier.center)) *
          taylorPowerSeries carrier.reciprocal carrier.center ^
            (carrier.secondDegree - 2) *
          Polynomial.aeval
            (taylorPowerSeries carrier.target carrier.center)
            carrier.secondGenerator =
        d⁄dX ℂ (taylorPowerSeries carrier.target carrier.center) *
          Polynomial.aeval
            (taylorPowerSeries carrier.reciprocal carrier.center)
            carrier.secondGenerator.reverse := by
  constructor
  · exact carrier.cleared_julia_taylor carrier.firstGenerator
      carrier.firstDegree carrier.source carrier.sourceDerivative
      carrier.first_degree carrier.first_degree_at_least_two
      carrier.source_analytic carrier.source_derivative carrier.inner_julia
  · exact carrier.cleared_julia_taylor carrier.secondGenerator
      carrier.secondDegree carrier.target carrier.targetDerivative
      carrier.second_degree carrier.second_degree_at_least_two
      carrier.target_analytic carrier.target_derivative carrier.outer_julia

/-- A cleared Taylor Julia identity recovers the raw Julia identity in the
Laurent field after inverting the reciprocal germ. -/
theorem laurent_julia_of_cleared_taylor
    (coordinate reciprocal source : PS)
    (generator : ℂ[X]) (degree : ℕ)
    (hdegree : generator.natDegree = degree) (htwo : 2 ≤ degree)
    (hreciprocal : reciprocal ≠ 0)
    (hcleared :
      -(d⁄dX ℂ reciprocal) * reciprocal ^ (degree - 2) *
          Polynomial.aeval source generator =
        d⁄dX ℂ source *
          Polynomial.aeval reciprocal generator.reverse) :
    coordinateDerivation coordinate
          ((algebraMap PS LS reciprocal)⁻¹) *
        Polynomial.aeval (algebraMap PS LS source) generator =
      coordinateDerivation coordinate (algebraMap PS LS source) *
        Polynomial.aeval ((algebraMap PS LS reciprocal)⁻¹)
          generator := by
  let reciprocalLaurent : LS := algebraMap PS LS reciprocal
  let sourceLaurent : LS := algebraMap PS LS source
  let hidden : LS := reciprocalLaurent⁻¹
  have hreciprocalLaurent : reciprocalLaurent ≠ 0 := by
    simpa only [reciprocalLaurent, map_zero] using
      (FaithfulSMul.algebraMap_injective PS LS).ne hreciprocal
  have hhidden : hidden ≠ 0 := inv_ne_zero hreciprocalLaurent
  letI : Invertible hidden := invertibleOfNonzero hhidden
  have hinverseHidden : ⅟hidden = reciprocalLaurent := by
    rw [invOf_eq_inv]
    simp [hidden, reciprocalLaurent, hreciprocalLaurent]
  have hreverse := Polynomial.eval₂_reverse_mul_pow
    (algebraMap ℂ LS) hidden generator
  rw [hinverseHidden, hdegree] at hreverse
  have hpower :
      reciprocalLaurent ^ (degree - 2) * hidden ^ degree = hidden ^ 2 := by
    have hdecomposition : degree - 2 + 2 = degree :=
      Nat.sub_add_cancel htwo
    have hcancel : reciprocalLaurent * hidden = 1 := by
      simp [hidden, hreciprocalLaurent]
    calc
      reciprocalLaurent ^ (degree - 2) * hidden ^ degree =
          reciprocalLaurent ^ (degree - 2) *
            (hidden ^ (degree - 2) * hidden ^ 2) := by
              rw [← pow_add, hdecomposition]
      _ = (reciprocalLaurent ^ (degree - 2) *
            hidden ^ (degree - 2)) * hidden ^ 2 := by ring
      _ = (reciprocalLaurent * hidden) ^ (degree - 2) *
            hidden ^ 2 := by rw [mul_pow]
      _ = hidden ^ 2 := by rw [hcancel]; simp
  have hclearedLaurent :
      -(algebraMap PS LS (d⁄dX ℂ reciprocal)) *
            reciprocalLaurent ^ (degree - 2) *
            Polynomial.aeval sourceLaurent generator =
        algebraMap PS LS (d⁄dX ℂ source) *
          Polynomial.aeval reciprocalLaurent generator.reverse := by
    have hmapped := congrArg (algebraMap PS LS) hcleared
    simpa only [map_neg, map_mul, map_pow, reciprocalLaurent,
      sourceLaurent, Polynomial.aeval_def] using hmapped
  have hraw :
      -hidden ^ 2 * algebraMap PS LS (d⁄dX ℂ reciprocal) *
            Polynomial.aeval sourceLaurent generator =
        algebraMap PS LS (d⁄dX ℂ source) *
          Polynomial.aeval hidden generator := by
    calc
      -hidden ^ 2 * algebraMap PS LS (d⁄dX ℂ reciprocal) *
            Polynomial.aeval sourceLaurent generator =
          (-(algebraMap PS LS (d⁄dX ℂ reciprocal)) *
              reciprocalLaurent ^ (degree - 2) *
              Polynomial.aeval sourceLaurent generator) *
            hidden ^ degree := by rw [hpower]; ring
      _ = (algebraMap PS LS (d⁄dX ℂ source) *
              Polynomial.aeval reciprocalLaurent generator.reverse) *
            hidden ^ degree := by rw [hclearedLaurent]
      _ = algebraMap PS LS (d⁄dX ℂ source) *
            (Polynomial.aeval reciprocalLaurent generator.reverse *
              hidden ^ degree) := by ring
      _ = algebraMap PS LS (d⁄dX ℂ source) *
            Polynomial.aeval hidden generator := by
              simpa only [Polynomial.aeval_def] using
                congrArg
                  (fun value : LS =>
                    algebraMap PS LS (d⁄dX ℂ source) * value)
                  hreverse
  rw [show (algebraMap PS LS reciprocal)⁻¹ = hidden by rfl,
    show algebraMap PS LS source = sourceLaurent by rfl]
  rw [(coordinateDerivation coordinate).leibniz_inv,
    coordinateDerivation_algebraMap,
    coordinateDerivation_algebraMap]
  simp only [smul_eq_mul]
  calc
    (-hidden ^ 2 *
          ((algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
            algebraMap PS LS (d⁄dX ℂ reciprocal))) *
          Polynomial.aeval sourceLaurent generator =
        (algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          (-hidden ^ 2 *
            algebraMap PS LS (d⁄dX ℂ reciprocal) *
            Polynomial.aeval sourceLaurent generator) := by ring
    _ = (algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          (algebraMap PS LS (d⁄dX ℂ source) *
            Polynomial.aeval hidden generator) := by rw [hraw]
    _ = ((algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          algebraMap PS LS (d⁄dX ℂ source)) *
            Polynomial.aeval hidden generator := by ring

/-- Both cleared Taylor rows of a two-Julia carrier become raw Julia rows
for its Laurent hidden endpoint. -/
theorem TwoJuliaAbelCarrier.laurent_julia_rows
    (carrier : TwoJuliaAbelCarrier) (coordinate : PS)
    (hreciprocal :
      taylorPowerSeries carrier.reciprocal carrier.center ≠ 0) :
    let reciprocal :=
      taylorPowerSeries carrier.reciprocal carrier.center
    let source := taylorPowerSeries carrier.source carrier.center
    let target := taylorPowerSeries carrier.target carrier.center
    let hidden : LS := (algebraMap PS LS reciprocal)⁻¹
    coordinateDerivation coordinate hidden *
          Polynomial.aeval (algebraMap PS LS source)
            carrier.firstGenerator =
        coordinateDerivation coordinate (algebraMap PS LS source) *
          Polynomial.aeval hidden carrier.firstGenerator ∧
      coordinateDerivation coordinate hidden *
          Polynomial.aeval (algebraMap PS LS target)
            carrier.secondGenerator =
        coordinateDerivation coordinate (algebraMap PS LS target) *
          Polynomial.aeval hidden carrier.secondGenerator := by
  dsimp only
  obtain ⟨hfirst, hsecond⟩ := carrier.cleared_taylor_rows
  constructor
  · exact laurent_julia_of_cleared_taylor coordinate
      (taylorPowerSeries carrier.reciprocal carrier.center)
      (taylorPowerSeries carrier.source carrier.center)
      carrier.firstGenerator carrier.firstDegree carrier.first_degree
      carrier.first_degree_at_least_two hreciprocal hfirst
  · exact laurent_julia_of_cleared_taylor coordinate
      (taylorPowerSeries carrier.reciprocal carrier.center)
      (taylorPowerSeries carrier.target carrier.center)
      carrier.secondGenerator carrier.secondDegree carrier.second_degree
      carrier.second_degree_at_least_two hreciprocal hsecond

end

end FormalLaurentReciprocalJuliaTransport
