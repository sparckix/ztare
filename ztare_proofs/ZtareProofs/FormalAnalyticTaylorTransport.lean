import Mathlib.Analysis.Analytic.OfScalars
import Mathlib.Analysis.Analytic.Uniqueness
import Mathlib.RingTheory.PowerSeries.Basic

/-!
# From analytic-germ equality to formal power-series equality

`HasFPowerSeriesAt` uses one-dimensional formal multilinear series, whereas
the algebraic obstruction kernels use `PowerSeries`.  This file gives the
content-preserving bridge through Mathlib's `FormalMultilinearSeries.ofScalars`.
-/

namespace FormalAnalyticTaylorTransport

open Filter PowerSeries Set
open scoped Topology

variable {𝕜 : Type*} [NontriviallyNormedField 𝕜]

/-- Regard a scalar `PowerSeries` as a one-dimensional formal multilinear
series with the same coefficients. -/
noncomputable def asFormalMultilinearSeries (series : PowerSeries 𝕜) :
    FormalMultilinearSeries 𝕜 𝕜 𝕜 :=
  FormalMultilinearSeries.ofScalars 𝕜 fun n => coeff n series

theorem asFormalMultilinearSeries_injective :
    Function.Injective (asFormalMultilinearSeries (𝕜 := 𝕜)) := by
  intro left right heq
  apply PowerSeries.ext
  have hcoefficients :=
    FormalMultilinearSeries.ofScalars_series_injective 𝕜 𝕜 heq
  exact congrFun hcoefficients

/-- Equal analytic germs have equal scalar power series whenever the two
series are their supplied local representations. -/
theorem powerSeries_eq_of_eventuallyEq
    {f g : 𝕜 → 𝕜} {center : 𝕜}
    {left right : PowerSeries 𝕜}
    (hleft : HasFPowerSeriesAt f (asFormalMultilinearSeries left) center)
    (hright : HasFPowerSeriesAt g (asFormalMultilinearSeries right) center)
    (heq : f =ᶠ[𝓝 center] g) :
    left = right := by
  apply asFormalMultilinearSeries_injective
  exact hleft.eq_formalMultilinearSeries_of_eventually hright heq

/-- Equality on an open chart yields equality of its two represented Taylor
series at any point of that chart. -/
theorem powerSeries_eq_of_eqOn_open
    {f g : 𝕜 → 𝕜} {center : 𝕜} {domain : Set 𝕜}
    {left right : PowerSeries 𝕜}
    (hopen : IsOpen domain) (hcenter : center ∈ domain)
    (hleft : HasFPowerSeriesAt f (asFormalMultilinearSeries left) center)
    (hright : HasFPowerSeriesAt g (asFormalMultilinearSeries right) center)
    (heq : EqOn f g domain) :
    left = right := by
  apply powerSeries_eq_of_eventuallyEq hleft hright
  filter_upwards [hopen.mem_nhds hcenter] with z hz
  exact heq hz

/-- Aggregated formal endpoint for analytic-to-formal Taylor transport. -/
theorem analytic_germ_to_powerSeries_terminal_certificate :
    ∀ {f g : 𝕜 → 𝕜} {center : 𝕜} {domain : Set 𝕜}
      {left right : PowerSeries 𝕜},
      IsOpen domain →
      center ∈ domain →
      HasFPowerSeriesAt f (asFormalMultilinearSeries left) center →
      HasFPowerSeriesAt g (asFormalMultilinearSeries right) center →
      EqOn f g domain →
      left = right := by
  intro f g center domain left right hopen hcenter hleft hright heq
  exact powerSeries_eq_of_eqOn_open hopen hcenter hleft hright heq

end FormalAnalyticTaylorTransport
