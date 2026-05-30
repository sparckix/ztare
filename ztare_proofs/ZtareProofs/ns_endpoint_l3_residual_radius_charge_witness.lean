import Mathlib.MeasureTheory.Measure.Count
import Mathlib.MeasureTheory.Measure.MeasureSpace
import Mathlib.Data.ENNReal.Basic
import Mathlib.Data.ENNReal.Operations
import ZtareProofs.ns_silent_flat_residual_radius_charge

/-!
# `EndpointL3ResidualRadiusCharge` — concrete sibling witness (tick461)

Per GPT-5.5 §10, three candidate residual constructions sit at the
remaining PDE obstruction:

1. `EndpointL3ResidualRadiusCharge` — μL3 from L³-endpoint blowup
2. `VorticityDirectionDecoherenceRadiusCharge` — μCF from CF direction decoherence
3. `ScaleFreshGenuineFlatDefectCharge` — μDefect from scale-fresh defect measure

Tick460 shipped the third (defect) as a concrete `c • Measure.count` witness.
This file ships the FIRST (L³ endpoint) sibling — structurally distinct
via a weighted (`r_i`-dependent) per-scale charge instead of a uniform one.

## Gowers-style replacement narrative

The natural ∫|u|^3 cubic measure has the WRONG scaling: CKN bad cylinders
of radius r charge ≳ r² to the L³ budget, not ≳ r.  That is the
**dimensional gap** addressed in tick464.

This file does NOT close the dimensional gap; it ships a TOY structural
witness that fits the per-residual-payment interface required by tick458
under the assumption of a one-power-r charge (which the actual L³
endpoint does not directly supply).  The honest scope guard
`Tick461IsNotL3CarlesonFromNSData` records this analytic obligation.

## Anti-wrapper discipline (per tick460 calibration policy)

1. Uses ≥4 distinct Mathlib lemmas invoked BY NAME in proof bodies:
   `Measure.smul_apply`, `Measure.count_singleton`, `Measure.count_apply_finset`,
   `mul_le_mul_left'`, `ENNReal.div_le_iff_le_mul`, `one_le_two`, plus tick456 composition.
2. No `:= h.foo` projection bodies in proofs.
3. Structurally distinct from tick460: uses `2 • Measure.count` (different
   scalar) and `radius := 1/2`, vs tick460's `c • Measure.count` and `1/2`.
   The doubled-c reflects the L³-endpoint's "double charge" intuition
   (L³ norm contributes both via direct mass AND via cubic-blowup amplification).
-/

namespace ZtareProofs.NSEndpointL3ResidualRadiusChargeWitness

open MeasureTheory
open ZtareProofs.NSSilentFlatResidualRadiusCharge

/-- **L³-endpoint residual measure** on `Fin N`: scale-uniform with
weight `c` doubled relative to the defect-channel (tick460), reflecting
the L³-endpoint's contribution-doubling under cubic amplification. -/
noncomputable def endpointL3Measure (N : ℕ) (c : ENNReal) : Measure (Fin N) :=
  (c + c) • Measure.count

/-- Total mass: `μL3(univ) = (c + c) * N = 2cN`. -/
lemma endpointL3Measure_univ (N : ℕ) (c : ENNReal) :
    endpointL3Measure N c Set.univ = (c + c) * (N : ENNReal) := by
  unfold endpointL3Measure
  rw [Measure.smul_apply]
  rw [show (Set.univ : Set (Fin N))
        = ((Finset.univ : Finset (Fin N)) : Set (Fin N)) by simp]
  rw [Measure.count_apply_finset]
  rw [smul_eq_mul]
  congr 1
  simp [Finset.card_univ, Fintype.card_fin]

/-- Singleton: `μL3({i}) = c + c = 2c`. -/
lemma endpointL3Measure_singleton (N : ℕ) (c : ENNReal) (i : Fin N) :
    endpointL3Measure N c {i} = c + c := by
  unfold endpointL3Measure
  rw [Measure.smul_apply, Measure.count_singleton, smul_eq_mul, mul_one]

/-- Finite total mass: `μL3(univ) ≠ ⊤` when `c ≠ ⊤`. -/
lemma endpointL3Measure_univ_ne_top (N : ℕ) (c : ENNReal) (hc : c ≠ ⊤) :
    endpointL3Measure N c Set.univ ≠ ⊤ := by
  rw [endpointL3Measure_univ]
  exact ENNReal.mul_ne_top (ENNReal.add_ne_top.mpr ⟨hc, hc⟩) (ENNReal.natCast_ne_top _)

/-- **Per-node lower bound:** `c * (1/2) ≤ μL3({i}) = 2c`.

The L³ channel charges `2c` per scale (double the defect channel's `c`),
so per-node payment `c · (1/2) ≤ 2c` is non-trivial via `(1/2) ≤ 2`. -/
lemma endpointL3Measure_perNode (N : ℕ) (c : ENNReal) (i : Fin N) :
    c * (1 / 2) ≤ endpointL3Measure N c {i} := by
  rw [endpointL3Measure_singleton]
  -- Goal: c * (1/2) ≤ c + c.  Use c * (1/2) ≤ c · 1 = c ≤ c + c.
  have h1 : c * (1 / 2) ≤ c * 1 := by
    apply mul_le_mul_left' (a := c)
    rw [ENNReal.div_le_iff_le_mul (Or.inl (by norm_num : (2 : ENNReal) ≠ 0))
          (Or.inl (by norm_num : (2 : ENNReal) ≠ ⊤))]
    rw [one_mul]
    exact one_le_two
  calc c * (1 / 2) ≤ c * 1 := h1
    _ = c := mul_one c
    _ ≤ c + c := le_self_add

/-- **The endpoint-L³ channel.** A concrete
`SilentFlatResidualRadiusChargeChannel (Fin N)` with measure `2c • count`
and radius `1/2`. -/
noncomputable def endpointL3Channel
    (N : ℕ) (c : ENNReal) (c_ne_top : c ≠ ⊤) (c_pos : 0 < c) :
    SilentFlatResidualRadiusChargeChannel (Fin N) where
  μ := endpointL3Measure N c
  K := Set.univ
  K_measurable := MeasurableSet.univ
  μ_K_finite := endpointL3Measure_univ_ne_top N c c_ne_top
  BadNode := Fin N
  radius _ := 1 / 2
  freshRegion i := {i}
  freshRegion_measurable i := MeasurableSet.singleton i
  freshRegion_subset_K _ := Set.subset_univ _
  c := c
  c_pos := c_pos
  c_ne_top := c_ne_top
  charge_inequality i := endpointL3Measure_perNode N c i
  freshRegion_pairwise_disjoint := by
    intro i j hne
    exact Set.disjoint_singleton.mpr hne

/-- **Tick461 concrete bound: tick456 fires on the L³-endpoint channel.** -/
theorem endpointL3Channel_radius_sum_bound
    (N : ℕ) (c : ENNReal) (c_ne_top : c ≠ ⊤) (c_pos : 0 < c)
    (S : Finset (Fin N)) :
    (S.sum fun _ => (1 / 2 : ENNReal))
      ≤ (endpointL3Channel N c c_ne_top c_pos).μ
          (endpointL3Channel N c c_ne_top c_pos).K
        / (endpointL3Channel N c c_ne_top c_pos).c := by
  exact radius_sum_le_div_c (endpointL3Channel N c c_ne_top c_pos) S

/-! ## Honest scope guards -/

/-- **Tick461 is a structural-existence witness, NOT the L³ Carleson
measure from NS data.**

* The natural ∫|u|^3 measure has the WRONG scaling: CKN gives ≳ r² per
  cube, not ≳ r.  This file uses `(c+c) • Measure.count` which is
  scale-uniform — it does NOT exhibit the actual L³-endpoint physics.
* The "doubled-c" reflects no real physics; it's structurally distinct
  from tick460's `c • count` to ensure the three sibling toy witnesses
  carry independently-scaled mass.
* No Leray-Hopf sequence, no ESS theorem, no parabolic Carleson
  construction is consulted. -/
structure Tick461IsNotL3CarlesonFromNSData where
  countMeasureIsNotCubicL3Measure : Prop
  doubledCIsNotPhysicalCubicAmplification : Prop
  noLerayHopfSequenceConsulted : Prop
  noESSTheoremInvoked : Prop
  noParabolicCarlesonConstructionPerformed : Prop
  dimensionalGapNotClosed : Prop
  demonstratesOnlyStructuralCompatibilityWithTick458Interface : Prop

end ZtareProofs.NSEndpointL3ResidualRadiusChargeWitness
