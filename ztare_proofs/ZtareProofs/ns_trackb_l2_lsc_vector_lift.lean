/-
# L² LSC under weak limits — vector-valued lift to `EuclideanSpace ℝ (Fin d)`

This file lifts the scalar primitive

  `ZtareProofs.l2_norm_squared_lsc_under_weak_limit`

(from `ns_trackb_l2_lsc_primitive.lean`) to vector-valued L²-functions
with codomain `EuclideanSpace ℝ (Fin d)`.

## Theorem (informal)

Given `f_n, f_∞ : α → EuclideanSpace ℝ (Fin d)` and a measure `μ`, if
`f_n ⇀ f_∞` weakly in L²(μ; EuclideanSpace ℝ (Fin d)) and the sequence
is uniformly L²-bounded, then

    ∫ ‖f_∞ x‖² ∂μ  ≤  liminf_n  ∫ ‖f_n x‖² ∂μ.

## Strategy

`EuclideanSpace ℝ (Fin d)` carries the L² norm pointwise:

    ‖v‖² = ∑_{i : Fin d} (v i)².            (`EuclideanSpace.real_norm_sq_eq`)

Integrating against `μ`,

    ∫ ‖f x‖² ∂μ = ∑_{i : Fin d} ∫ (f x i)² ∂μ
                                          (`MeasureTheory.integral_finset_sum`).

So the vector primitive reduces to:
  1. apply the scalar primitive coordinatewise (one scalar
     `L2WeakLSCData` per `i : Fin d`), yielding `d`-many scalar
     inequalities `A_i ≤ liminf_n B_i n`;
  2. sum the `d` inequalities, then push the sum inside `liminf` via
     `le_liminf_add` (binary form, applied `d - 1` times by induction
     on `Finset (Fin d)`).

Like the scalar primitive, this file decouples the algebraic core from
concrete integral identities: the integral-vs-coordinate-sum
identifications are exposed as named hypotheses (see
`L2VectorWeakLSCData.Hypotheses.{limitVecL2_eq_sum, seqVecL2_eq_sum}`).
-/

import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.Analysis.InnerProductSpace.PiL2
import Mathlib.Topology.Algebra.Order.LiminfLimsup
import Mathlib.Order.LiminfLimsup
import ZtareProofs.ns_trackb_l2_lsc_primitive

open MeasureTheory Filter Topology
open scoped ENNReal NNReal BigOperators

namespace ZtareProofs

/-! ### Auxiliary 1: a `Finset`-sum is bounded above/below if each summand is. -/

private lemma isBoundedUnder_le_finset_sum
    {ι κ : Type*} {l : Filter ι}
    (s : Finset κ) (u : κ → ι → ℝ)
    (h : ∀ k ∈ s, l.IsBoundedUnder (· ≤ ·) (u k)) :
    l.IsBoundedUnder (· ≤ ·) (fun n => ∑ k ∈ s, u k n) := by
  classical
  induction s using Finset.induction_on with
  | empty =>
      refine ⟨0, ?_⟩
      rw [Filter.eventually_map]
      exact Filter.Eventually.of_forall fun _ => by simp
  | insert j t hj ih =>
      have hj_bd := h j (Finset.mem_insert_self _ _)
      have ih' := ih (fun q hq => h q (Finset.mem_insert_of_mem hq))
      have hadd := isBoundedUnder_le_add hj_bd ih'
      rcases hadd with ⟨B, hB⟩
      refine ⟨B, ?_⟩
      rw [Filter.eventually_map] at hB ⊢
      filter_upwards [hB] with n hn
      have hrw : ∑ k ∈ insert j t, u k n = u j n + ∑ k ∈ t, u k n :=
        Finset.sum_insert hj
      rw [hrw]
      exact hn

private lemma isBoundedUnder_ge_finset_sum
    {ι κ : Type*} {l : Filter ι}
    (s : Finset κ) (u : κ → ι → ℝ)
    (h : ∀ k ∈ s, l.IsBoundedUnder (· ≥ ·) (u k)) :
    l.IsBoundedUnder (· ≥ ·) (fun n => ∑ k ∈ s, u k n) := by
  classical
  induction s using Finset.induction_on with
  | empty =>
      refine ⟨0, ?_⟩
      rw [Filter.eventually_map]
      exact Filter.Eventually.of_forall fun _ => by simp
  | insert j t hj ih =>
      have hj_bd := h j (Finset.mem_insert_self _ _)
      have ih' := ih (fun q hq => h q (Finset.mem_insert_of_mem hq))
      have hadd := isBoundedUnder_ge_add hj_bd ih'
      rcases hadd with ⟨B, hB⟩
      refine ⟨B, ?_⟩
      rw [Filter.eventually_map] at hB ⊢
      filter_upwards [hB] with n hn
      have hrw : ∑ k ∈ insert j t, u k n = u j n + ∑ k ∈ t, u k n :=
        Finset.sum_insert hj
      rw [hrw]
      exact hn

/-! ### Auxiliary 2: `liminf` of a finite sum dominates the sum of `liminf`s.

Binary base case is `le_liminf_add` (Mathlib
`Topology/Algebra/Order/LiminfLimsup.lean:68`); we lift it to `Finset`
by induction. -/

private lemma sum_liminf_le_liminf_sum_finset
    {ι κ : Type*} {l : Filter ι} [l.NeBot]
    (s : Finset κ) (u : κ → ι → ℝ)
    (h_bdd_below : ∀ k ∈ s, l.IsBoundedUnder (· ≥ ·) (u k))
    (h_bdd_above : ∀ k ∈ s, l.IsBoundedUnder (· ≤ ·) (u k)) :
    (∑ k ∈ s, Filter.liminf (u k) l)
      ≤ Filter.liminf (fun n => ∑ k ∈ s, u k n) l := by
  classical
  induction s using Finset.induction_on with
  | empty =>
      simp only [Finset.sum_empty]
      have h0 : Filter.liminf (fun _ : ι => (0 : ℝ)) l = 0 :=
        (tendsto_const_nhds : Tendsto (fun _ : ι => (0 : ℝ)) l (𝓝 0)).liminf_eq
      exact h0.ge
  | insert k s hks ih =>
      have h_bdd_below_k : l.IsBoundedUnder (· ≥ ·) (u k) :=
        h_bdd_below k (Finset.mem_insert_self _ _)
      have h_bdd_above_k : l.IsBoundedUnder (· ≤ ·) (u k) :=
        h_bdd_above k (Finset.mem_insert_self _ _)
      have h_bdd_below_s : ∀ j ∈ s, l.IsBoundedUnder (· ≥ ·) (u j) :=
        fun j hj => h_bdd_below j (Finset.mem_insert_of_mem hj)
      have h_bdd_above_s : ∀ j ∈ s, l.IsBoundedUnder (· ≤ ·) (u j) :=
        fun j hj => h_bdd_above j (Finset.mem_insert_of_mem hj)
      -- Bounds on the partial sum `S n := ∑ j ∈ s, u j n`.
      have h_bdd_below_S :
          l.IsBoundedUnder (· ≥ ·) (fun n => ∑ j ∈ s, u j n) :=
        isBoundedUnder_ge_finset_sum s u h_bdd_below_s
      have h_bdd_above_S :
          l.IsBoundedUnder (· ≤ ·) (fun n => ∑ j ∈ s, u j n) :=
        isBoundedUnder_le_finset_sum s u h_bdd_above_s
      have h_S_cobdd :
          l.IsCoboundedUnder (· ≥ ·) (fun n => ∑ j ∈ s, u j n) :=
        h_bdd_above_S.isCoboundedUnder_ge
      -- IH on `s`.
      have ih_s := ih h_bdd_below_s h_bdd_above_s
      -- Binary `le_liminf_add` on `(u k, ∑ j ∈ s, u j ·)`.
      have h_add :
          (Filter.liminf (u k) l) + Filter.liminf (fun n => ∑ j ∈ s, u j n) l
            ≤ Filter.liminf
                (fun n => u k n + ∑ j ∈ s, u j n) l := by
        have := le_liminf_add (f := l) (u := u k)
                  (v := fun n => ∑ j ∈ s, u j n)
                  h_bdd_below_k h_bdd_above_k h_bdd_below_S h_S_cobdd
        simpa [Pi.add_apply] using this
      -- Final assembly.
      rw [Finset.sum_insert hks]
      have hsum_eq :
          (fun n => u k n + ∑ j ∈ s, u j n)
            = (fun n => ∑ j ∈ insert k s, u j n) := by
        funext n; rw [Finset.sum_insert hks]
      calc Filter.liminf (u k) l + ∑ j ∈ s, Filter.liminf (u j) l
          ≤ Filter.liminf (u k) l
              + Filter.liminf (fun n => ∑ j ∈ s, u j n) l :=
            add_le_add (le_refl _) ih_s
        _ ≤ Filter.liminf (fun n => u k n + ∑ j ∈ s, u j n) l := h_add
        _ = Filter.liminf (fun n => ∑ j ∈ insert k s, u j n) l := by
            rw [hsum_eq]

/-! ### Vector primitive structures -/

/-- Inputs to the vector-valued L² LSC primitive.

To keep the "scalar primitive applied coordinatewise" plumbing
free of dependent-type/HEq dances, we *fix* the underlying index type
`ι` and filter `l` at the vector level and require each per-coordinate
scalar primitive to be over those same `ι, l` (this is the realistic
case anyway: every Galerkin index sequence shares one filter).
-/
structure L2VectorWeakLSCData where
  /-- Index sequence (e.g. `ℕ`). -/
  ι : Type*
  /-- Filter on `ι`. -/
  l : Filter ι
  /-- Vector dimension. -/
  d : ℕ
  /-- For each coordinate `i : Fin d`:
      `crossCoord i n = ∫ (f_n x i) · (f_∞ x i) ∂μ`. -/
  crossCoord : Fin d → ι → ℝ
  /-- For each coordinate `i : Fin d`:
      `limitL2Coord i = ∫ (f_∞ x i)² ∂μ`. -/
  limitL2Coord : Fin d → ℝ
  /-- For each coordinate `i : Fin d`:
      `seqL2Coord i n = ∫ (f_n x i)² ∂μ`. -/
  seqL2Coord : Fin d → ι → ℝ
  /-- Vector L² norm² of the limit:  `limitVecL2 = ∫ ‖f_∞ x‖² ∂μ`. -/
  limitVecL2 : ℝ
  /-- Vector L² norm² of the sequence:  `seqVecL2 n = ∫ ‖f_n x‖² ∂μ`. -/
  seqVecL2 : ι → ℝ

namespace L2VectorWeakLSCData

/-- Bundle one coordinate as a `L2WeakLSCData` for direct application of
the scalar primitive. -/
def coordData (D : L2VectorWeakLSCData) (i : Fin D.d) : L2WeakLSCData where
  ι := D.ι
  l := D.l
  cross := D.crossCoord i
  limitL2 := D.limitL2Coord i
  seqL2 := D.seqL2Coord i

@[simp] lemma coordData_ι (D : L2VectorWeakLSCData) (i : Fin D.d) :
    (D.coordData i).ι = D.ι := rfl
@[simp] lemma coordData_l (D : L2VectorWeakLSCData) (i : Fin D.d) :
    (D.coordData i).l = D.l := rfl
@[simp] lemma coordData_seqL2 (D : L2VectorWeakLSCData) (i : Fin D.d) :
    (D.coordData i).seqL2 = D.seqL2Coord i := rfl
@[simp] lemma coordData_limitL2 (D : L2VectorWeakLSCData) (i : Fin D.d) :
    (D.coordData i).limitL2 = D.limitL2Coord i := rfl

/-- Hypotheses of the vector primitive.

* `coord_H i` packages the scalar primitive's hypotheses on coordinate
  `i`, ready for direct application.
* `coord_seqL2_bdd_above`, `coord_seqL2_bdd_below` are the per-coordinate
  uniform bounds used to push the sum inside `liminf`.
* `limitVecL2_eq_sum`, `seqVecL2_eq_sum` are the integral-linearity
  identifications:

      ∫ ‖f_∞ x‖² ∂μ = ∑_{i : Fin d} ∫ (f_∞ x i)² ∂μ
      ∫ ‖f_n x‖² ∂μ = ∑_{i : Fin d} ∫ (f_n x i)² ∂μ          (each `n`).

  Both follow from `EuclideanSpace.real_norm_sq_eq` together with
  `MeasureTheory.integral_finset_sum`.
-/
structure Hypotheses (D : L2VectorWeakLSCData) : Prop where
  countablyGenerated : IsCountablyGenerated D.l
  neBot : D.l.NeBot
  /-- Scalar primitive hypotheses, coordinatewise. -/
  coord_H : ∀ i : Fin D.d, (D.coordData i).Hypotheses
  /-- Each coordinate's `seqL2` is bounded above on `D.l`. -/
  coord_seqL2_bdd_above :
    ∀ i : Fin D.d, D.l.IsBoundedUnder (· ≤ ·) (D.seqL2Coord i)
  /-- Each coordinate's `seqL2` is bounded below on `D.l`. -/
  coord_seqL2_bdd_below :
    ∀ i : Fin D.d, D.l.IsBoundedUnder (· ≥ ·) (D.seqL2Coord i)
  /-- `∫ ‖f_∞‖² = ∑ ∫ (f_∞ i)²`.  Discharge with
  `EuclideanSpace.real_norm_sq_eq` + `MeasureTheory.integral_finset_sum`. -/
  limitVecL2_eq_sum :
    D.limitVecL2 = ∑ i : Fin D.d, D.limitL2Coord i
  /-- `∫ ‖f_n‖² = ∑ ∫ (f_n i)²` (pointwise in `n`). -/
  seqVecL2_eq_sum :
    ∀ n : D.ι, D.seqVecL2 n = ∑ i : Fin D.d, D.seqL2Coord i n

end L2VectorWeakLSCData

open L2VectorWeakLSCData

/-- **Vector L² LSC under weak limits** (codomain `EuclideanSpace ℝ (Fin d)`).

If `f_n ⇀ f_∞` weakly in `L²(μ; EuclideanSpace ℝ (Fin d))` and the
sequence is uniformly L²-bounded — both encoded coordinatewise via the
scalar `L2WeakLSCData.Hypotheses` together with the integral-linearity
identifications `limitVecL2_eq_sum`, `seqVecL2_eq_sum` — then

  `∫ ‖f_∞ x‖² ∂μ ≤ liminf_n ∫ ‖f_n x‖² ∂μ`.

The proof applies the scalar primitive coordinatewise (`Fin d`-many
times) and sums via `le_liminf_add` (binary), lifted to `Finset` by
`sum_liminf_le_liminf_sum_finset`. -/
theorem l2_vector_norm_squared_lsc_under_weak_limit
    (D : L2VectorWeakLSCData) (H : D.Hypotheses) :
    D.limitVecL2 ≤ Filter.liminf D.seqVecL2 D.l := by
  haveI : D.l.NeBot := H.neBot
  haveI : IsCountablyGenerated D.l := H.countablyGenerated
  -- Step 1.  Apply the scalar primitive coordinatewise.
  have h_coord :
      ∀ i : Fin D.d,
        D.limitL2Coord i ≤ Filter.liminf (D.seqL2Coord i) D.l := by
    intro i
    have := ZtareProofs.l2_norm_squared_lsc_under_weak_limit
              (D.coordData i) (H.coord_H i)
    -- `coordData_*` `simp`-reduces the conclusion to the desired form.
    simpa using this
  -- Step 2.  Sum the `d` coordinate inequalities.
  have h_sum_coord :
      ∑ i : Fin D.d, D.limitL2Coord i
        ≤ ∑ i : Fin D.d, Filter.liminf (D.seqL2Coord i) D.l :=
    Finset.sum_le_sum (fun i _ => h_coord i)
  -- Step 3.  Push the finite sum inside `liminf`.
  have h_push :
      ∑ i : Fin D.d, Filter.liminf (D.seqL2Coord i) D.l
        ≤ Filter.liminf
            (fun n : D.ι => ∑ i : Fin D.d, D.seqL2Coord i n) D.l :=
    sum_liminf_le_liminf_sum_finset
      (Finset.univ : Finset (Fin D.d))
      (fun i n => D.seqL2Coord i n)
      (fun i _ => H.coord_seqL2_bdd_below i)
      (fun i _ => H.coord_seqL2_bdd_above i)
  -- Step 4.  Identify ∑ ∂coord with `seqVecL2`.
  have h_eq_seq :
      (fun n : D.ι => ∑ i : Fin D.d, D.seqL2Coord i n) = D.seqVecL2 := by
    funext n; exact (H.seqVecL2_eq_sum n).symm
  rw [h_eq_seq] at h_push
  -- Step 5.  Identify ∑ limit with `limitVecL2`.
  calc D.limitVecL2
      = ∑ i : Fin D.d, D.limitL2Coord i := H.limitVecL2_eq_sum
    _ ≤ ∑ i : Fin D.d, Filter.liminf (D.seqL2Coord i) D.l := h_sum_coord
    _ ≤ Filter.liminf D.seqVecL2 D.l := h_push

/-!
## Closure summary

`l2_vector_norm_squared_lsc_under_weak_limit` is sorry-free.  The
discharge plan for `L2VectorWeakLSCData.Hypotheses` at any concrete
call site is:

* `coord_H i`             — scalar primitive hypotheses applied to
                            coordinate `i` (see
                            `ns_trackb_l2_lsc_primitive.lean` for the
                            Mathlib companions of each scalar field).
* `coord_seqL2_bdd_above`,
  `coord_seqL2_bdd_below` — uniform bounds on each coordinate's `seqL2`
                            (consequence of the per-coordinate uniform
                             L² bound + integral nonnegativity).
* `limitVecL2_eq_sum`     — `EuclideanSpace.real_norm_sq_eq` +
                            `MeasureTheory.integral_finset_sum`.
* `seqVecL2_eq_sum`       — same identification, applied pointwise in
                            `n`.

The auxiliary lemmas

  * `isBoundedUnder_le_finset_sum`,
  * `isBoundedUnder_ge_finset_sum`,
  * `sum_liminf_le_liminf_sum_finset`

are sorry-free, built from `isBoundedUnder_le_add`, `isBoundedUnder_ge_add`,
and `le_liminf_add` respectively.  For the Clay-relevant case `d = 3`
the sum-side argument unfolds to two applications of `le_liminf_add`.

The vector lift is the bridge between the scalar L² primitive and the
NS Track-B `kineticEnergy`/`enstrophy` LSC obligations stated against
`VelocityField n = α → EuclideanSpace ℝ (Fin n)`.
-/

end ZtareProofs
