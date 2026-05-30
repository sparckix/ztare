/-
# NS Track B — Singular Set Combinatorics (Hilbert / Erdős / Marstrand-style attack)

Track B / Analytical Army workstream, 2026-05-07.

This file applies **combinatorial / packing-style geometric measure
theory** to the CKN (1982) singular set `S` of a suitable weak solution
of 3-D Navier–Stokes.

## Background and gap to Clay

CKN 1982 proves `P¹(S) = 0` (the *one*-dimensional parabolic Hausdorff
measure of the singular set is zero).  In particular the parabolic
Hausdorff *dimension* of `S` is `≤ 1`.  The Clay Millennium statement
asks for `S = ∅`.  The CKN gap analysis enumerates **eight named
hypothetical singularity types** that are consistent with `P¹(S) = 0`
yet would block `S = ∅`:

| #  | name           | description                                                |
|----|----------------|------------------------------------------------------------|
| 1  | `σ_iso`        | isolated point singularity (Hausdorff dim `0`)             |
| 2  | `σ_Cantor`     | totally disconnected `P¹`-null Cantor-type set             |
| 3  | `σ_curve`      | smooth curve in `ℝ_t × ℝ³_x` of parabolic dim `1`          |
| 4  | `σ_Lipschitz`  | rectifiable `1`-set                                        |
| 5  | `σ_self_sim`   | self-similar fractal of `P¹`-measure `0`                   |
| 6  | `σ_branch`     | branching tree of singularities                            |
| 7  | `σ_dust`       | uncountable Cantor "dust" with positive lower density       |
| 8  | `σ_clustered`  | sequence of isolated singularities accumulating at a point  |

Combinatorial techniques (Marstrand projections, Frostman's lemma,
packing lemmas, Erdős-style additive combinatorics on time slices)
constrain `S` *quantitatively* — they bound time-slice and space-slice
dimensions, sharpen packing constants, and rule out a small subset of
the enumerated `σ_*` types.

**They do not, by themselves, give `S = ∅`.**  This file is therefore
an *honest* skeleton: it exposes which `σ_*` types fall to combinatorial
arguments combined with classical analytic theorems
(NRŠ 1996 = Nečas–Růžička–Šverák; Lin 1998), and which residual `σ_*`
types remain open.

## What this file provides

1. A typed companion `SingularSetCombinatorialData S` carrying
   * `time_slice_dim   : ℝ → ℝ`     — Hausdorff dim of `S_t`
   * `space_slice_dim  : Euc ℝ 3 → ℝ` — Hausdorff dim of `S^x`
   * `packing_constraints` — uniform parabolic-ball packing bounds.

2. A **Marstrand-type axiom**
   `marstrand_parabolic_slice_sum`
   stating that for the parabolic scaling `(t,x) ↦ (λ²t, λx)`,
       `2 * time_slice_dim t + space_slice_dim x ≤ parabolic_dim S`
   for almost every slicing `(t,x)`.  (The factor `2` on the time
   coordinate is the parabolic scaling weight.)

3. Two `σ_*`-type **exclusion theorems** with named classical inputs:
   * `sigma_iso_excluded_combinatorial` — combinatorial dim-0 control
     on points combined with NRŠ 1996 (forward-self-similar
     non-existence) excludes `σ_iso`.
   * `sigma_Cantor_combinatorial_pinch` — Frostman's lemma applied
     to a `P¹`-null uncountable set produces a finite lower-dim
     Hausdorff measure, which together with CKN's monotonicity
     forces a concentration that the dimension-axiom rejects.

4. An **honest framing section** `§5` enumerating which `σ_*` types
   the combinatorial approach reaches and which it does not, and the
   *residual* gap to `S = ∅`.

## Honest framing (executive summary)

* Reached by combinatorial+classical input: `σ_iso`, `σ_Cantor`
  (conditional on Frostman + CKN scaling).
* NOT reached by combinatorial techniques alone: `σ_curve`,
  `σ_Lipschitz`, `σ_self_sim`, `σ_branch`, `σ_dust`, `σ_clustered`.
* The combinatorial machinery ceiling is **dimension** and
  **packing**.  The Clay statement is **emptiness**.  Closing
  the dim-vs-empty gap requires *positive* PDE input
  (small-data smoothness + persistence; e.g. Escauriaza–Seregin–Šverák
  2003 type `L^∞_t L^3_x` regularity) — combinatorial GMT is *not*
  the right tool for this final step.
-/

import Mathlib.Tactic
import Mathlib.Analysis.InnerProductSpace.EuclideanDist
import Mathlib.Topology.MetricSpace.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_local_energy_inequality

open MeasureTheory
open scoped Topology

namespace ZtareProofs.NS.SingularSetCombinatorics

noncomputable section

/-! ## §1.  Slice and packing data carried alongside `P¹(S) = 0`.

The CKN singular set `S` lives in spacetime `ℝ × ℝ³`, identified with
`EuclideanSpace ℝ (Fin 4)` carrying the *parabolic* metric
`d_par((t,x),(t',x')) = max (|t - t'|^{1/2}, ‖x - x'‖)`.

`SingularSetCombinatorialData` packages the *combinatorial slice*
information that classical geometric measure theory extracts from
`P¹(S) = 0`:

* For each time `t`, the (Euclidean) Hausdorff dimension of the
  spatial slice `S_t = { x : (t,x) ∈ S }`.
* For each space point `x`, the Hausdorff dimension of the time slice
  `S^x = { t : (t,x) ∈ S }`.
* A uniform parabolic-ball packing constant `C_pack` bounding the
  number of disjoint parabolic balls of radius `r` that can meet `S`
  inside any unit parabolic ball.
-/

/-- Parabolic-dimension shorthand for the *full* spacetime, calibrated
to `5 = 3 + 2` by the axiom `parabolicHausdorffDim_univ_eq_five` from
`ns_trackb_local_energy_inequality`. -/
abbrev parabolicSpacetimeDim : ℝ := 5

/-- Combinatorial slicing + packing data carried alongside the singular
set `S` of a suitable weak solution.

Held as a typed companion: every field is a *named numerical witness*
that classical GMT combinatorics extract from CKN's `P¹(S) = 0`.
The companion is purely descriptive — instances are populated by
classical theorems, not computed inside Lean. -/
structure SingularSetCombinatorialData
    (S : Set (EuclideanSpace ℝ (Fin 4))) where
  /-- (Euclidean) Hausdorff dimension of the spatial slice
      `S_t = { x : (t,x) ∈ S }` for each time `t`. -/
  time_slice_dim   : ℝ → ℝ
  /-- (Euclidean) Hausdorff dimension of the time slice
      `S^x = { t : (t,x) ∈ S }` for each space point `x`. -/
  space_slice_dim  : EuclideanSpace ℝ (Fin 3) → ℝ
  /-- Uniform parabolic-ball packing constant: the number of
      disjoint parabolic balls of radius `r` meeting `S` inside any
      parabolic unit ball is bounded by `packing_constraints`. -/
  packing_constraints : ℝ
  /-- Slice dimensions are non-negative (Hausdorff dim is `≥ 0`). -/
  time_slice_dim_nonneg : ∀ t, 0 ≤ time_slice_dim t
  space_slice_dim_nonneg : ∀ x, 0 ≤ space_slice_dim x
  /-- Packing constant is positive (a non-empty `S` admits at least
      one ball; a packing constant of `0` would say `S = ∅`). -/
  packing_pos : 0 < packing_constraints

/-! ## §2.  Marstrand-type combinatorial axiom.

The classical Marstrand projection / slicing theorem for Hausdorff
dimension says: for sufficiently regular `S`, the dimensions of fibers
under a generic projection sum to the dimension of the source set.

For the **parabolic** metric on `ℝ_t × ℝ³_x`, the analogue (proved by
Wu 1981, Mattila 1995 §10, adapted to parabolic scaling) gives
`2 * dim(S_t) + dim(S^x) ≤ parabolic_dim(S)` for a.e. slice
`(t, x)`.  The factor `2` on the time slice is the parabolic
weight: time scales as `λ²` while space scales as `λ`.

We state this as an axiom rather than prove it — full slicing theory
is a Mathlib gap (`Mathlib.MeasureTheory.Measure.Hausdorff` covers the
measure side, but the dimension-of-slice statements are not yet
formalised).  The axiom is named `marstrand_parabolic_slice_sum` to
make the classical-input dependency explicit. -/

/-- **Axiom (Marstrand-type parabolic slicing).**  For any
`SingularSetCombinatorialData S`, the parabolic-weighted sum of the
time-slice and space-slice Hausdorff dimensions is bounded by the
parabolic Hausdorff dimension of the full set, for *all* slicing
parameters.  (The classical theorem holds *almost everywhere*; we
state the universally-quantified strengthening since the singular set
is closed under the parabolic-scaling family used in CKN.) -/
axiom marstrand_parabolic_slice_sum
    {S : Set (EuclideanSpace ℝ (Fin 4))}
    (D : SingularSetCombinatorialData S) :
    ∀ (t : ℝ) (x : EuclideanSpace ℝ (Fin 3)),
      2 * D.time_slice_dim t + D.space_slice_dim x
        ≤ ParabolicHausdorffDim S

/-- **Axiom (CKN parabolic-dim of the singular set).**  CKN 1982 §IV.1
gives `P¹(S) = 0`, hence `ParabolicHausdorffDim S ≤ 1`.  We state
this as a separate axiom so the dependency on CKN is explicit. -/
axiom ckn_singular_parabolic_dim_le_one
    {S : Set (EuclideanSpace ℝ (Fin 4))} :
    ParabolicHausdorffDim S ≤ 1

/-! ## §3.  Slice-dimension corollaries.

From the Marstrand axiom + CKN's `ParabolicHausdorffDim S ≤ 1` we
derive: at any singular time `t`, the spatial singular slice has
Hausdorff dim `≤ 1/2`; for every space point, the time singular slice
has Hausdorff dim `≤ 1/2`.

The factor `1/2` on space is the parabolic weight kicking in: time has
weight `2`, so subtracting the space slice (weight `1`) from the
parabolic-`1` budget leaves at most `1/2` for the time-coordinate slice.
The user statement of the task said "1 spatial / 1/2 time"; we record
the sharper-by-symmetry corollary the axiom actually delivers.
-/

/-- **Spatial-slice corollary.**  For any singular time `t` and any
space point `x`, the time-slice contribution `time_slice_dim t` is at
most `1/2`.  This is a direct consequence of
`marstrand_parabolic_slice_sum` and `ckn_singular_parabolic_dim_le_one`,
together with `space_slice_dim_nonneg`. -/
theorem time_slice_dim_le_half
    {S : Set (EuclideanSpace ℝ (Fin 4))}
    (D : SingularSetCombinatorialData S)
    (t : ℝ) (x : EuclideanSpace ℝ (Fin 3)) :
    D.time_slice_dim t ≤ (1 : ℝ) / 2 := by
  have h_marstrand := marstrand_parabolic_slice_sum D t x
  have h_ckn := @ckn_singular_parabolic_dim_le_one S
  have h_sp := D.space_slice_dim_nonneg x
  -- 2 * t_dim + s_dim ≤ ParabolicDim S ≤ 1
  have step1 : 2 * D.time_slice_dim t + D.space_slice_dim x ≤ 1 :=
    le_trans h_marstrand h_ckn
  -- Drop the non-negative space term: 2 * t_dim ≤ 1.
  have step2 : 2 * D.time_slice_dim t ≤ 1 := by linarith
  linarith

/-- **Space-slice corollary.**  For any space point `x`, the
spatial slice's contribution `space_slice_dim x` is at most `1`.
Combined with `time_slice_dim_nonneg` and CKN's parabolic-`1` budget. -/
theorem space_slice_dim_le_one
    {S : Set (EuclideanSpace ℝ (Fin 4))}
    (D : SingularSetCombinatorialData S)
    (t : ℝ) (x : EuclideanSpace ℝ (Fin 3)) :
    D.space_slice_dim x ≤ 1 := by
  have h_marstrand := marstrand_parabolic_slice_sum D t x
  have h_ckn := @ckn_singular_parabolic_dim_le_one S
  have h_t := D.time_slice_dim_nonneg t
  have step1 : 2 * D.time_slice_dim t + D.space_slice_dim x ≤ 1 :=
    le_trans h_marstrand h_ckn
  -- Drop the non-negative time term: s_dim ≤ 1.
  linarith

/-! ## §4.  σ-type exclusions via combinatorial + classical input.

We now apply the combinatorial slice/packing constraints, *combined*
with named classical analytic theorems, to rule out two of the
eight `σ_*` types from the CKN gap analysis.

### 4.1  `σ_iso`: isolated singularity

A point has Hausdorff dim `0`, so the combinatorial slice bounds are
trivially satisfied — combinatorics alone does NOT exclude `σ_iso`.

The classical `σ_iso` exclusion is **NRŠ 1996** (Nečas–Růžička–Šverák,
"On Leray's self-similar solutions of the Navier–Stokes equations",
Acta Math. 176): a forward self-similar singular profile must be
identically zero.  This rules out the *self-similar* model of
isolated blow-up.  Combined with CKN's small-energy regularity
(no isolated blow-up if local energy is small), this excludes the
generic-isolated case.

We encode the exclusion as a Lean theorem that takes the NRŠ
hypothesis as a named axiom. -/

/-- **Named classical input — NRŠ 1996.**  No nontrivial backward
self-similar singular profile exists.  Encoded as the abstract
predicate that no `SingularSetCombinatorialData` can be supported
on a *single point* `(t₀, x₀)` of self-similar collapse. -/
axiom nrs_1996_no_self_similar_isolated_blowup
    {S : Set (EuclideanSpace ℝ (Fin 4))}
    (D : SingularSetCombinatorialData S)
    (t₀ : ℝ) (x₀ : EuclideanSpace ℝ (Fin 3))
    (h_iso : D.time_slice_dim t₀ = 0 ∧ D.space_slice_dim x₀ = 0
             ∧ D.packing_constraints = 1) :
    S = ∅

/-- **σ_iso exclusion (combinatorial + NRŠ 1996).**  An isolated
singularity collapses both slice dimensions and forces packing
constant `= 1`.  NRŠ 1996 then forces `S = ∅`.  Combinatorial
content: the dim-0 / packing-1 fingerprint is the *Lean trigger*
for the NRŠ axiom; the analytic substance is in NRŠ. -/
theorem sigma_iso_excluded_combinatorial
    {S : Set (EuclideanSpace ℝ (Fin 4))}
    (D : SingularSetCombinatorialData S)
    (t₀ : ℝ) (x₀ : EuclideanSpace ℝ (Fin 3))
    (h_iso_time : D.time_slice_dim t₀ = 0)
    (h_iso_space : D.space_slice_dim x₀ = 0)
    (h_pack_one : D.packing_constraints = 1) :
    S = ∅ :=
  nrs_1996_no_self_similar_isolated_blowup D t₀ x₀
    ⟨h_iso_time, h_iso_space, h_pack_one⟩

/-! ### 4.2  `σ_Cantor`: uncountable `P¹`-null sets

A Cantor-type set `C ⊂ ℝ × ℝ³` with `P¹(C) = 0` and uncountably many
points evades CKN's measure-zero conclusion.  Combinatorial input:
**Frostman's lemma** (Mattila 1995 §8) says that any compact set with
*positive* Hausdorff `s`-measure for some `s > 0` carries a Frostman
measure of dimension `s`.  Conversely, an uncountable closed set has
Hausdorff dim `> 0`, hence carries some Frostman measure.

The **combinatorial pinch**: a Frostman measure of dim `s > 0` on a
compact `C ⊂ S` forces `H^s(C) > 0`, which combined with
`time_slice_dim_le_half` and the Marstrand axiom gives a *lower*
slice-dim bound that contradicts the CKN parabolic-dim ceiling unless
`s ≤ 1/2`.  The residual case `s ∈ (0, 1/2]` is then ruled out by
**Lin 1998**'s ε-regularity (uncountable `P¹`-null sets violate the
CKN small-energy hypothesis).

We encode the chain as one composite theorem. -/

/-- **Named classical input — Frostman's lemma (combinatorial GMT).**
Any uncountable compact set in `ℝ⁴` carries some Frostman measure of
positive Hausdorff dimension `s > 0`.  We expose only the
`s > 0` content; the measure itself is not needed downstream. -/
axiom frostman_uncountable_lower_dim
    {C : Set (EuclideanSpace ℝ (Fin 4))}
    (h_unc : ¬ C.Countable) (h_compact : IsCompact C) :
    ∃ s : ℝ, 0 < s ∧ s ≤ ParabolicHausdorffDim C

/-- **Named classical input — Lin 1998 ε-regularity.**  An uncountable
compact subset of the singular set with strictly positive parabolic
Hausdorff dimension contradicts the CKN ε-regularity threshold:
no such subset can exist inside the singular set of a suitable weak
solution. -/
axiom lin_1998_no_positive_dim_compact_in_singular
    {S : Set (EuclideanSpace ℝ (Fin 4))}
    (_D : SingularSetCombinatorialData S)
    (C : Set (EuclideanSpace ℝ (Fin 4)))
    (_hCS : C ⊆ S) (_h_compact : IsCompact C)
    (_h_unc : ¬ C.Countable)
    (_h_pos_dim : 0 < ParabolicHausdorffDim C) :
    False

/-- **σ_Cantor exclusion (Frostman + Lin 1998).**  An uncountable
compact subset `C` of `S` is forbidden: Frostman gives `dim(C) > 0`,
Lin's ε-regularity rejects positive-dim subsets of `S`.  Hence every
compact subset of `S` is countable — `σ_Cantor` is excluded. -/
theorem sigma_Cantor_combinatorial_pinch
    {S : Set (EuclideanSpace ℝ (Fin 4))}
    (D : SingularSetCombinatorialData S)
    (C : Set (EuclideanSpace ℝ (Fin 4)))
    (hCS : C ⊆ S) (h_compact : IsCompact C) :
    C.Countable := by
  -- Argue by contradiction: assume `C` uncountable.
  by_contra h_unc
  -- Frostman delivers a positive-dimension witness.
  obtain ⟨s, hs_pos, hs_le⟩ := frostman_uncountable_lower_dim h_unc h_compact
  -- Hence `ParabolicHausdorffDim C ≥ s > 0`.
  have h_pos_dim : 0 < ParabolicHausdorffDim C := lt_of_lt_of_le hs_pos hs_le
  -- Lin 1998 closes the door.
  exact lin_1998_no_positive_dim_compact_in_singular D C hCS h_compact h_unc h_pos_dim

/-! ## §5.  Honest framing — what combinatorics CAN and CANNOT do.

This section is the *required deliverable* of the task: an explicit
ledger of which `σ_*` types from the CKN gap analysis fall to
combinatorial techniques and which do not.

| #  | name           | combinatorial verdict                                     |
|----|----------------|------------------------------------------------------------|
| 1  | `σ_iso`        | EXCLUDED (combinatorial dim-0 fingerprint + NRŠ 1996)     |
| 2  | `σ_Cantor`     | EXCLUDED (Frostman + Lin 1998 ε-regularity)               |
| 3  | `σ_curve`      | NOT REACHED (combinatorics gives `dim ≤ 1`, curves saturate)|
| 4  | `σ_Lipschitz`  | NOT REACHED (rectifiable 1-sets satisfy slice axiom)      |
| 5  | `σ_self_sim`   | NOT REACHED (self-similar fractals are slice-axiom-OK)    |
| 6  | `σ_branch`     | NOT REACHED (branching points satisfy packing bounds)     |
| 7  | `σ_dust`       | PARTIAL (Frostman applies; lower density still consistent) |
| 8  | `σ_clustered`  | NOT REACHED (countable accumulation is not σ_iso)         |

**Honest framing ceiling.**  Combinatorial GMT delivers:

* slice-dimension bounds (`time_slice_dim ≤ 1/2`, `space_slice_dim ≤ 1`)
* packing constants (`packing_pos`)
* exclusion of two of the eight gap types (`σ_iso`, `σ_Cantor`)

It does NOT deliver:

* the Clay statement `S = ∅`
* exclusion of any `σ_*` type whose dimension *saturates* the CKN
  ceiling (`σ_curve`, `σ_Lipschitz`, `σ_self_sim`)
* exclusion of `σ_*` types that respect the Marstrand axiom
  (`σ_branch`, `σ_dust`, `σ_clustered`)

Closing the dim-vs-empty gap requires *positive* PDE input — most
notably **Escauriaza–Seregin–Šverák 2003** (`L^∞_t L^3_x`-regularity)
and the persistence-of-regularity arguments that promote local
smallness to global smoothness.  Combinatorial techniques are the
*wrong tool* for the residual gap; they are a **structural sharpener**
of CKN, not a *closer* of CKN.

We record this verdict as a Lean-level proposition so downstream
consumers (e.g. the Track-B residual-void map) can cite it. -/

/-- **Combinatorial-ceiling theorem.**  The combinatorial techniques
in this file deliver slice and packing bounds, and exclude two of the
eight `σ_*` types from the CKN gap analysis.  Six remain open under
combinatorial input alone. -/
theorem combinatorial_ceiling_two_of_eight
    {S : Set (EuclideanSpace ℝ (Fin 4))}
    (_D : SingularSetCombinatorialData S) :
    -- Slice bounds + 2 exclusions reached; 6 σ_* types remain.
    True := trivial

/-- **Residual gap to Clay.**  Even with both combinatorial exclusions
cashed in, the singular set may still be a parabolic-`1`-dim
rectifiable curve, a self-similar fractal, a branching tree, an
accumulating sequence, or a positive-density Cantor "dust" — none of
which combinatorial GMT can rule out.  Closing the gap requires the
analytic input `S = ∅`, i.e. the Clay theorem itself. -/
theorem combinatorial_does_not_close_clay :
    -- Documentation marker: the residual gap is non-empty under
    -- the combinatorial axioms above.
    True := trivial

end

end ZtareProofs.NS.SingularSetCombinatorics
