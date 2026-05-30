import Mathlib.Tactic
import ZtareProofs.ns_eulerian_dissipation_bridge
import ZtareProofs.ns_fractal_recurrence_target
import ZtareProofs.ns_marginal_tax_rate

namespace ZtareProofs

/-!
`ns_time_rate_pincer` captures the 10k-foot cold shot after the
Eulerian-dissipation bridge.

The hidden variable is no longer just thickness. It is the time-rate tradeoff:

* dissipation lower bounds grow like `r^2 / T`,
* fractal/Zeno recurrence also needs `T` to shrink.

So the same shrinking return time that keeps the rival alive can raise the
reset tax, provided the gain does not outrun the stretch-rate cost.
-/

/-- Gain upper bound by a stretch-rate cost scale. -/
def gainBoundedByStretchCost
    (G : cycleGain) (mu r : Real) (T : Real → Real) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → G E ≤ stretchRateCost mu r (T E)

/-- Reset loss lower bound by a stretch-rate cost scale. -/
def lossLowerBoundedByStretchCost
    (L : cycleLoss) (mu r : Real) (T : Real → Real) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → stretchRateCost mu r (T E) ≤ L E

/--
If reset loss is lower-bounded by the stretch-rate cost and gain is
upper-bounded by the same cost, then the marginal tax rate is eventually at
least one, provided gain is positive.
-/
theorem weak_tax_dominance_of_stretch_cost_pincer
    {G L : cycleGain} {mu r EStar : Real} {T : Real → Real}
    (hGpos : ∀ ⦃E : Real⦄, EStar ≤ E → 0 < G E)
    (hGain : gainBoundedByStretchCost G mu r T EStar)
    (hLoss : lossLowerBoundedByStretchCost L mu r T EStar) :
    ∀ ⦃E : Real⦄, EStar ≤ E → 1 ≤ marginalTaxRate G L E := by
  intro E hE
  unfold marginalTaxRate
  have hGL : G E ≤ L E := le_trans (hGain hE) (hLoss hE)
  have hG : 0 < G E := hGpos hE
  exact (one_le_div hG).2 hGL

/--
Strict version: if the reset loss exceeds the stretch-rate cost by a positive
margin over the gain bound, the tax rate is eventually strictly greater than
one.
-/
def strictStretchCostMargin
    (G L : cycleGain) (mu r : Real) (T : Real → Real) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → G E < stretchRateCost mu r (T E) ∧
    stretchRateCost mu r (T E) ≤ L E

/--
Strict stretch-rate margin implies eventual tax dominance.
-/
theorem tax_dominance_of_strict_stretch_cost_margin
    {G L : cycleGain} {mu r EStar : Real} {T : Real → Real}
    (hGpos : ∀ ⦃E : Real⦄, EStar ≤ E → 0 < G E)
    (hmargin : strictStretchCostMargin G L mu r T EStar) :
    eventualTaxDominance G L EStar := by
  intro E hE
  unfold marginalTaxRate
  have hparts := hmargin hE
  have hGL : G E < L E := lt_of_lt_of_le hparts.1 hparts.2
  have hG : 0 < G E := hGpos hE
  exact (one_lt_div hG).2 hGL

/--
Time-rate pincer target:
the same shrinking cycle time required by the fractal rival can support the
exhaust route if it makes the stretch-rate cost dominate gain.
-/
theorem time_rate_pincer_target_shape
    {G L : cycleGain} {mu r EStar : Real} {T : Real → Real}
    (hGpos : ∀ ⦃E : Real⦄, EStar ≤ E → 0 < G E)
    (hmargin : strictStretchCostMargin G L mu r T EStar) :
    eventualTaxDominance G L EStar := by
  exact tax_dominance_of_strict_stretch_cost_margin hGpos hmargin

/--
Once the time-rate margin gives eventual tax dominance, the recurrence-map
exhaust horizon follows.
-/
theorem exhaust_horizon_of_time_rate_pincer
    {G L : cycleGain} {mu r EStar : Real} {T : Real → Real}
    (hGpos : ∀ ⦃E : Real⦄, EStar ≤ E → 0 < G E)
    (hmargin : strictStretchCostMargin G L mu r T EStar) :
    exhaustHorizon G L EStar := by
  exact exhaust_horizon_of_eventual_tax_dominance hGpos
    (tax_dominance_of_strict_stretch_cost_margin hGpos hmargin)

end ZtareProofs
