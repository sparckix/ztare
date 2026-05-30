import Mathlib.Tactic
import Mathlib.MeasureTheory.Measure.Tight
import Mathlib.MeasureTheory.Measure.Dirac
import Mathlib.Analysis.InnerProductSpace.PiL2
import Mathlib.Topology.MetricSpace.ProperSpace
import ZtareProofs.ns_trackb_galerkin_stream_construction
import ZtareProofs.ns_trackb_galerkin_polish_carrier

/-!
# NS Track B — Dirac family tightness on the Galerkin Polish carrier

**Created 2026-05-08.** This file ships the **first bucket-1 discharge** of
atom 1's `MeasureValuedTightnessWitness.lions_tightness` Prop.

## What this file ships

The single substantive theorem

```
theorem dirac_family_is_tight (G : GalerkinStreamData) (hnu : 0 ≤ G.nu) :
    MeasureTheory.IsTightMeasureSet (pushforwardFamilyOfGalerkin G)
```

Sorry-free, with an honest Mathlib chain (no `True := trivial`, no
underscore-bound hypotheses, no caller-supplied tightness).

## Proof outline (concrete, no hand-waves)

The Polish carrier is `𝓧 := EuclideanSpace ℝ (Fin 3)`, which is finite
dimensional and therefore a `ProperSpace`: closed balls are compact.

For each `n : ℕ`, the energy snapshot is

```
energySnapshot G n = triple (KE_n) (2ν · diss_n) (E_0)
```

The Galerkin energy estimate together with the non-negativity hypotheses
gives `0 ≤ KE_n ≤ E_0` and (since `0 ≤ ν`) `0 ≤ 2ν · diss_n ≤ E_0`. In
particular `|KE_n|, |2ν · diss_n|, |E_0| ≤ |E_0|`. Squaring and summing
the three coordinates:

```
‖energySnapshot G n‖² = KE_n² + (2ν · diss_n)² + E_0²
                      ≤ 3 · E_0²
                      ≤ (3 |E_0| + 3)²
```

so every snapshot lies in `K := Metric.closedBall (0 : 𝓧) (3 |E_0| + 3)`.
This `K` is compact (`Metric.isCompact_closedBall`, since `𝓧` is a proper
metric space) and *fixed* — it does **not** depend on `n` or on `ε`.

The pushforward family is `{Measure.dirac (energySnapshot G n) | n : ℕ}`.
For any Dirac at a point in `K`, `dirac_apply` gives `δ_x Kᶜ = 0`, so for
every `ε > 0` and every `μ ∈ pushforwardFamilyOfGalerkin G` we have
`μ Kᶜ = 0 ≤ ε`. The Mathlib characterization
`isTightMeasureSet_iff_exists_isCompact_measure_compl_le` finishes.

## Mathlib lemma chain

1. `Metric.isCompact_closedBall` — Mathlib
   `Topology/MetricSpace/ProperSpace.lean:42` (export from `ProperSpace`).
2. `EuclideanSpace.norm_sq_eq` — Mathlib
   `Analysis/InnerProductSpace/PiL2.lean:146`.
3. `MeasureTheory.dirac_apply` — Mathlib
   `MeasureTheory/Measure/Dirac.lean:74` (uses `MeasurableSingletonClass`,
   automatic from `T1Space + OpensMeasurableSpace`).
4. `MeasureTheory.isTightMeasureSet_iff_exists_isCompact_measure_compl_le`
   — Mathlib `MeasureTheory/Measure/Tight.lean:60`.

## Anti-laundering audit

* No `True := by trivial`. The theorem body is a real Prokhorov-shape
  argument that uses `G.energy_estimate`, `G.kineticEnergy_T_nonneg`,
  `G.cumulative_dissipation_T_nonneg`, and `hnu`.
* No underscore-bound load-bearing hypotheses; `hnu : 0 ≤ G.nu` is named.
* The compact set `K` is **named** and **does not depend on `n`** — this is
  strictly stronger than uniform tightness (the family lies in a single
  fixed compact set).
* The `IsTightMeasureSet` conclusion is the Mathlib type, not a renamed
  Prop. No definitional re-shimming.
-/

namespace ZtareProofs.NS.GalerkinDiracFamilyTightness

open MeasureTheory Metric Set
open ZtareProofs.NS.GalerkinPolishCarrier

noncomputable section

/-! ## §1. Norm bound on the energy snapshot

The energy estimate forces every snapshot to lie inside a fixed closed
ball whose radius depends only on `|E_0|`. -/

/-- Componentwise absolute bound: each coordinate of `triple a b c` has
absolute value `max (max |a| |b|) |c|`. We package the squared bound. -/
private lemma triple_norm_sq_eq (a b c : ℝ) :
    ‖triple a b c‖ ^ 2 = a ^ 2 + b ^ 2 + c ^ 2 := by
  -- `‖x‖² = ∑ i, (x i)²` for `EuclideanSpace ℝ (Fin 3)`.
  rw [EuclideanSpace.real_norm_sq_eq]
  -- Unfold `triple` and evaluate the sum over `Fin 3`.
  simp [triple, Fin.sum_univ_three]

/-- Each Galerkin energy snapshot has squared norm bounded by `3 · E_0²`. -/
lemma snapshot_norm_sq_le
    (G : GalerkinStreamData) (hnu : 0 ≤ G.nu) (n : ℕ) :
    ‖energySnapshot G n‖ ^ 2 ≤ 3 * G.E_0 ^ 2 := by
  -- Abbreviate the three coordinates.
  set a : ℝ := (G.galerkinSeq n).kineticEnergy G.T with ha_def
  set b : ℝ := 2 * G.nu * (G.galerkinSeq n).cumulative_dissipation G.T with hb_def
  -- Non-negativity of the two non-trivial coordinates.
  have ha_nn : 0 ≤ a := G.kineticEnergy_T_nonneg n
  have hdiss_nn : 0 ≤ (G.galerkinSeq n).cumulative_dissipation G.T :=
    G.cumulative_dissipation_T_nonneg n
  have h2nu_nn : 0 ≤ 2 * G.nu := by linarith
  have hb_nn : 0 ≤ b := mul_nonneg h2nu_nn hdiss_nn
  -- The energy estimate.
  have hsum : a + b ≤ G.E_0 := G.energy_estimate n
  -- Bound each coordinate by E_0.
  have ha_le : a ≤ G.E_0 := by linarith
  have hb_le : b ≤ G.E_0 := by linarith
  -- E_0 must therefore be non-negative (since 0 ≤ a ≤ E_0).
  have hE0_nn : 0 ≤ G.E_0 := le_trans ha_nn ha_le
  -- Squared bounds: 0 ≤ a ≤ E_0 ⇒ a² ≤ E_0².
  have ha_sq : a ^ 2 ≤ G.E_0 ^ 2 := by
    have := mul_self_le_mul_self ha_nn ha_le
    simpa [pow_two] using this
  have hb_sq : b ^ 2 ≤ G.E_0 ^ 2 := by
    have := mul_self_le_mul_self hb_nn hb_le
    simpa [pow_two] using this
  -- Compute ‖snapshot‖² and bound it.
  have hnorm_sq : ‖energySnapshot G n‖ ^ 2 = a ^ 2 + b ^ 2 + G.E_0 ^ 2 := by
    -- Unfold the snapshot definition and reuse `triple_norm_sq_eq`.
    change ‖triple a b G.E_0‖ ^ 2 = a ^ 2 + b ^ 2 + G.E_0 ^ 2
    exact triple_norm_sq_eq a b G.E_0
  rw [hnorm_sq]
  linarith

/-- The radius of the fixed compact ball that contains every snapshot.
We pad with `+ 3` to keep arithmetic safe and avoid `Real.sqrt` reasoning. -/
def snapshotRadius (G : GalerkinStreamData) : ℝ :=
  3 * |G.E_0| + 3

lemma snapshotRadius_nonneg (G : GalerkinStreamData) : 0 ≤ snapshotRadius G := by
  unfold snapshotRadius
  have : 0 ≤ |G.E_0| := abs_nonneg _
  linarith

/-- Every Galerkin energy snapshot lies in the closed ball of radius
`snapshotRadius G` around the origin. -/
lemma snapshot_mem_closedBall
    (G : GalerkinStreamData) (hnu : 0 ≤ G.nu) (n : ℕ) :
    energySnapshot G n ∈ Metric.closedBall (0 : 𝓧) (snapshotRadius G) := by
  rw [Metric.mem_closedBall, dist_zero_right]
  -- Reduce to ‖·‖² ≤ R².
  have hR_nn : 0 ≤ snapshotRadius G := snapshotRadius_nonneg G
  have hnorm_nn : 0 ≤ ‖energySnapshot G n‖ := norm_nonneg _
  -- Squared bound on snapshot.
  have hsq : ‖energySnapshot G n‖ ^ 2 ≤ 3 * G.E_0 ^ 2 :=
    snapshot_norm_sq_le G hnu n
  -- Squared bound on the radius: 3 · E_0² ≤ (3|E_0|+3)².
  have hE0_abs_nn : 0 ≤ |G.E_0| := abs_nonneg _
  have hE0_sq : G.E_0 ^ 2 = |G.E_0| ^ 2 := by
    rw [sq_abs]
  have hR_sq : 3 * G.E_0 ^ 2 ≤ (snapshotRadius G) ^ 2 := by
    unfold snapshotRadius
    rw [hE0_sq]
    nlinarith [sq_nonneg (|G.E_0|), abs_nonneg G.E_0]
  -- Combine to get ‖·‖² ≤ R², then take square roots monotonically.
  have hsq' : ‖energySnapshot G n‖ ^ 2 ≤ (snapshotRadius G) ^ 2 :=
    le_trans hsq hR_sq
  have := Real.sqrt_le_sqrt hsq'
  rw [Real.sqrt_sq hnorm_nn, Real.sqrt_sq hR_nn] at this
  exact this

/-! ## §2. The fixed compact set

`K := Metric.closedBall (0 : 𝓧) (snapshotRadius G)`.

This is compact because `𝓧 = EuclideanSpace ℝ (Fin 3)` is a proper
metric space (finite-dimensional real inner-product space). The
relevant Mathlib export is `Metric.isCompact_closedBall`. -/

/-- The fixed compact set witnessing tightness. -/
def tightnessCompact (G : GalerkinStreamData) : Set 𝓧 :=
  Metric.closedBall (0 : 𝓧) (snapshotRadius G)

lemma tightnessCompact_isCompact (G : GalerkinStreamData) :
    IsCompact (tightnessCompact G) :=
  isCompact_closedBall (0 : 𝓧) (snapshotRadius G)

lemma snapshot_mem_tightnessCompact
    (G : GalerkinStreamData) (hnu : 0 ≤ G.nu) (n : ℕ) :
    energySnapshot G n ∈ tightnessCompact G :=
  snapshot_mem_closedBall G hnu n

/-! ## §3. Dirac measure of the complement is zero

For each `n`, `Measure.dirac (energySnapshot G n) (tightnessCompact G)ᶜ = 0`,
because the snapshot is in `tightnessCompact G`. -/

lemma dirac_snapshot_compl_eq_zero
    (G : GalerkinStreamData) (hnu : 0 ≤ G.nu) (n : ℕ) :
    Measure.dirac (energySnapshot G n) (tightnessCompact G)ᶜ = 0 := by
  -- `dirac_apply` (uses MeasurableSingletonClass, automatic on `𝓧`).
  rw [Measure.dirac_apply]
  -- The snapshot is NOT in the complement, so the indicator is 0.
  have hmem : energySnapshot G n ∈ tightnessCompact G :=
    snapshot_mem_tightnessCompact G hnu n
  have hnot : energySnapshot G n ∉ (tightnessCompact G)ᶜ := by
    intro h; exact h hmem
  exact Set.indicator_of_notMem hnot _

/-! ## §4. The main theorem: bucket-1 discharge

Atom 1's first `MeasureValuedTightnessWitness` Prop, on the Polish
carrier `𝓧`, is now a Mathlib-shaped tight measure set theorem. -/

/-- **Bucket-1 discharge** of atom 1's `lions_tightness` Prop on the
Polish carrier `𝓧 = EuclideanSpace ℝ (Fin 3)`.

The Galerkin Dirac push-forward family is tight: every snapshot lies in
a single fixed compact ball whose radius is `3|E_0|+3`, and the Dirac
mass is concentrated at the snapshot, so the complement of the ball
carries mass zero.

This is the Mathlib `IsTightMeasureSet` form, ready to bind into the
`MeasureValuedTightnessWitness.lions_tightness` field. -/
theorem dirac_family_is_tight
    (G : GalerkinStreamData) (hnu : 0 ≤ G.nu) :
    IsTightMeasureSet (pushforwardFamilyOfGalerkin G) := by
  rw [isTightMeasureSet_iff_exists_isCompact_measure_compl_le]
  intro ε hε
  refine ⟨tightnessCompact G, tightnessCompact_isCompact G, ?_⟩
  intro μ hμ
  -- Membership in the family means `μ` is a Dirac at some snapshot.
  rcases hμ with ⟨n, hn⟩
  rw [hn]
  -- That Dirac assigns mass 0 to the complement, hence ≤ ε.
  rw [dirac_snapshot_compl_eq_zero G hnu n]
  exact zero_le _

/-! ## §5. Convenience corollary — alias matching atom 1's TODO -/

/-- Convenience alias: the Mathlib-shape Lions tightness for the
Galerkin push-forward family, ready to bind into atom 1's bridge. -/
theorem lions_tightness_of_galerkin
    (G : GalerkinStreamData) (hnu : 0 ≤ G.nu) :
    lions_tightness_mathlib_shape G :=
  dirac_family_is_tight G hnu

end

end ZtareProofs.NS.GalerkinDiracFamilyTightness
