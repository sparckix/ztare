import Mathlib.MeasureTheory.Measure.Count
import Mathlib.MeasureTheory.Measure.MeasureSpace
import Mathlib.Data.ENNReal.Basic
import ZtareProofs.ns_silent_flat_residual_radius_charge

/-!
# Concrete `SilentFlatResidualRadiusChargeChannel` instantiation via `Measure.count` (tick457)

**Executable self-challenge for tick456.**

Per the codex_rd / meta_darwin_proxy GP-230 forecast (aggregate p ≈ 0.60),
the recommended clean design is `α := Fin N × Fin N` (finite), with
`μ := Measure.count`, `freshRegion Q := {Q}`.  This makes:

* pairwise disjointness automatic (singletons of distinct points are
  disjoint via `Set.disjoint_singleton`),
* finite mass `count(univ) = N²` automatic via `Measure.count_apply_finset`,
* per-node inequality `1 · 1 ≤ count{Q} = 1` automatic via
  `Measure.count_singleton`.

Then `tick456 (radius_sum_le_div_c)` gives a concrete numerical bound
`Σ 1 ≤ N²` on a `Finset` of bad nodes.

## Anti-wrapper discipline

1. Uses 4 named Mathlib lemmas: `Measure.count_singleton`,
   `Measure.count_apply_finset`, `Set.disjoint_singleton`,
   `ENNReal.natCast_ne_top`, plus tick456's `radius_sum_le_div_c`.
2. `μ` is a real `Mathlib.MeasureTheory.Measure`, not an opaque Prop.
3. Concrete bound `Σ 1 ≤ N²` is *derived* numerically.
4. No `:= h.foo` projection bodies — each carrier field has a Mathlib
   witness.

## Honest scope

This is a toy combinatorial witness on `Fin N × Fin N` with counting
measure.  It demonstrates tick456 fires; it is NOT a Navier-Stokes
construction.  A real NS construction would build μ as a parabolic
Carleson measure on a Leray-Hopf weak solution.
-/

namespace ZtareProofs.NSSilentFlatResidualRadiusChargeCountInstantiation

open MeasureTheory
open ZtareProofs.NSSilentFlatResidualRadiusCharge

/--
**The clean count-measure instantiation on `Fin N × Fin N`.**

All carrier fields populated by real Mathlib types/proofs:
* `μ := Measure.count` (canonical counting measure).
* `K := Set.univ` over the finite product `Fin N × Fin N` (finite mass).
* `BadNode := Fin N × Fin N`, `freshRegion Q := {Q}`.
* `radius _ := 1`, `c := 1` in `ENNReal`.
-/
noncomputable def countFinChannel (N : ℕ) :
    SilentFlatResidualRadiusChargeChannel (Fin N × Fin N) where
  μ := Measure.count
  K := Set.univ
  K_measurable := MeasurableSet.univ
  μ_K_finite := by
    rw [show (Set.univ : Set (Fin N × Fin N))
          = ((Finset.univ : Finset (Fin N × Fin N)) : Set (Fin N × Fin N)) by simp]
    rw [Measure.count_apply_finset]
    exact ENNReal.natCast_ne_top _
  BadNode := Fin N × Fin N
  radius _ := 1
  freshRegion Q := {Q}
  freshRegion_measurable Q := MeasurableSet.singleton Q
  freshRegion_subset_K _ := Set.subset_univ _
  c := 1
  c_pos := by simp
  c_ne_top := ENNReal.one_ne_top
  charge_inequality Q := by
    rw [Measure.count_singleton]
    simp
  freshRegion_pairwise_disjoint := by
    intro Q Q' hne
    exact Set.disjoint_singleton.mpr hne

/--
**Tick457 concrete bound: tick456 aggregation fires on the
finite count witness.**

For any finite `S` of bad nodes drawn from `Fin N × Fin N`, the sum of
radii is bounded by `count(univ) / 1 = N²`.

This is the executable demonstration that tick456's
`radius_sum_le_div_c` produces a real numerical bound on a concrete
Mathlib-typed witness.
-/
theorem countFinChannel_radius_sum_bound (N : ℕ)
    (S : Finset (Fin N × Fin N)) :
    (S.sum fun _ => (1 : ENNReal))
      ≤ (countFinChannel N).μ (countFinChannel N).K / (countFinChannel N).c := by
  exact radius_sum_le_div_c (countFinChannel N) S

/--
**Numerical specialization: `Σ 1 ≤ N²`.**

Specializes the abstract bound to the concrete value `count(univ) = N²`
on `Fin N × Fin N` and `c = 1`.
-/
theorem countFinChannel_radius_sum_le_N_sq (N : ℕ)
    (S : Finset (Fin N × Fin N)) :
    (S.sum fun _ => (1 : ENNReal)) ≤ ((N * N : ℕ) : ENNReal) := by
  have hbound : (S.sum fun _ => (1 : ENNReal))
      ≤ (countFinChannel N).μ (countFinChannel N).K / (countFinChannel N).c :=
    countFinChannel_radius_sum_bound N S
  have hμK : (countFinChannel N).μ (countFinChannel N).K = ((N * N : ℕ) : ENNReal) := by
    show (Measure.count : Measure (Fin N × Fin N)) Set.univ = ((N * N : ℕ) : ENNReal)
    rw [show (Set.univ : Set (Fin N × Fin N))
          = ((Finset.univ : Finset (Fin N × Fin N)) : Set (Fin N × Fin N)) by simp]
    rw [Measure.count_apply_finset]
    congr 1
    simp [Finset.card_univ, Fintype.card_prod, Fintype.card_fin]
  have hc : (countFinChannel N).c = 1 := rfl
  rw [hc, hμK] at hbound
  simpa using hbound

/-!
## Honest scope guards
-/

/--
**Tick457 is a Mathlib instantiation test, NOT an NS construction.**

The witness uses `Measure.count` on `Fin N × Fin N` — a toy
combinatorial setting.  No Leray-Hopf solution, no parabolic Carleson
measure, no CKN bad cylinders are involved.
-/
structure Tick457IsNotNSConstruction where
  countMeasureIsCombinatorial : Prop
  finNxFinNIsNotSpaceTime : Prop
  unitRadiusIsNotCKNRadius : Prop
  singletonFreshRegionIsNotCKNFreshTent : Prop
  noLerayHopfSequenceConsulted : Prop
  noParabolicCarlesonMeasureConstructed : Prop
  demonstratesOnlyThatTick456Fires : Prop

end ZtareProofs.NSSilentFlatResidualRadiusChargeCountInstantiation
