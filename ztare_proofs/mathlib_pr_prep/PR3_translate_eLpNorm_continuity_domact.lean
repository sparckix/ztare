import Mathlib.MeasureTheory.Function.LpSpace.DomAct.Continuous
import Mathlib.MeasureTheory.Function.LpSpace.Complete
import Mathlib.MeasureTheory.Group.Measure

/-!
# Translation continuity in `eLpNorm`

This draft records the short Mathlib-facing proof of translation continuity in
`eLpNorm`, derived from the existing continuity of the `DomAddAct` action on
`Lp`.
-/

open Filter
open scoped ENNReal Topology

namespace MeasureTheory

variable {G E : Type*} [NormedAddCommGroup G] [MeasurableSpace G] [BorelSpace G]
  [R1Space G] [SecondCountableTopology G] [LocallyCompactSpace G]
variable [NormedAddCommGroup E]
variable {μ : Measure G} [μ.IsAddHaarMeasure] {p : ℝ≥0∞}

/-- Translation is continuous in `eLpNorm` for functions in `Lᵖ` on a
second-countable locally compact abelian group with Haar measure. -/
theorem tendsto_translate_eLpNorm_zero [Fact (1 ≤ p)] [Fact (p ≠ ∞)]
    {f : G → E} (hf : MemLp f p μ) :
    Tendsto (fun h : G => eLpNorm (fun x => f (x + h) - f x) p μ) (𝓝 0) (𝓝 0) := by
  have hLp :
      Tendsto (fun h : G => DomAddAct.mk h +ᵥ hf.toLp f) (𝓝 0) (𝓝 (hf.toLp f)) := by
    have hcont : Continuous fun q : Gᵈᵃᵃ × Lp E p μ => q.1 +ᵥ q.2 :=
      continuous_vadd
    have hpair :
        Tendsto (fun h : G => (DomAddAct.mk h, hf.toLp f)) (𝓝 0)
          (𝓝 (DomAddAct.mk (0 : G), hf.toLp f)) :=
      (DomAddAct.continuous_mk.tendsto 0).prodMk_nhds tendsto_const_nhds
    change Tendsto (((fun q : Gᵈᵃᵃ × Lp E p μ => q.1 +ᵥ q.2) ∘
        fun h : G => (DomAddAct.mk h, hf.toLp f))) (𝓝 0) (𝓝 (hf.toLp f))
    simpa using (hcont.tendsto _).comp hpair
  rw [Lp.tendsto_Lp_iff_tendsto_eLpNorm'] at hLp
  refine hLp.congr' ?_
  filter_upwards with h
  apply eLpNorm_congr_ae
  have htrans : MemLp (fun x : G => f (h + x)) p μ :=
    hf.comp_measurePreserving (measurePreserving_add_left μ h)
  have hleft :
      ↑↑(DomAddAct.mk h +ᵥ hf.toLp f) =ᵐ[μ] fun x : G => f (h + x) := by
    rw [DomAddAct.mk_vadd_toLp]
    exact htrans.coeFn_toLp
  filter_upwards [hleft, hf.coeFn_toLp] with x hx_left hx_right
  rw [Pi.sub_apply, hx_left, hx_right, add_comm]

end MeasureTheory
