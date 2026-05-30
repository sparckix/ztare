import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Set
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.ns_trackb_lean_dojo_energy_bridge

/-!
# Bridge: typed-companion → `WeakSolution.weak_initial_condition`

This file builds the structural bridge from a typed companion
`WeakInitialConditionData` (carrying the analytical content of
spectral-projection / Galerkin-truncation convergence at the initial
time) to the `weak_initial_condition` clause of lean-dojo's
`WeakSolution` structure
(see `Problems/NavierStokes/Navierstokes.lean`, lines 429–434):

```
weak_initial_condition :
  ∀ φ : Euc ℝ n → Euc ℝ n,
  ContDiff ℝ ⊤ φ →
  (∃ K : Set (Euc ℝ n), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
  ∫ x : Euc ℝ n, (∑ i : Fin n, u (pairToEuc 0 x) i * φ x i) =
  ∫ x : Euc ℝ n, (∑ i : Fin n, nse.initialVelocity x i * φ x i)
```

## Bridge interpretation

A Galerkin-truncation sequence `u_n` (e.g. the projection onto the
first `n` modes of a fixed orthonormal Stokes basis) is constructed so
that `u_n(0,·) = P_n u_0` (the spectral projection of the initial
datum). For each test function `φ` (smooth, compactly supported), the
matchings:

  Iₙ(φ) := ∫ ⟨u_n(0,·), φ⟩      (truncated initial pairing)
  I∞(φ) := ∫ ⟨u_∞(0,·), φ⟩      (limit initial pairing)
  J(φ)  := ∫ ⟨u_0, φ⟩            (target initial-data pairing)

satisfy:
  (1) Iₙ(φ) = ∫ ⟨P_n u_0, φ⟩      (truncation matches projection)
  (2) Iₙ(φ) → J(φ)  as n → ∞      (spectral approximation: P_n u_0 → u_0
                                    strongly in L², hence ⟨P_n u_0, φ⟩
                                    → ⟨u_0, φ⟩ trivially in ℝ since the
                                    inner product is continuous in the
                                    first slot for fixed `φ`)
  (3) Iₙ(φ) → I∞(φ) as n → ∞      (weak limit u_n ⇀ u_∞ at t=0; in fact
                                    if t=0 weak convergence is upgraded
                                    to STRONG convergence by Lions
                                    compactness, so this also holds)

The bridge then concludes `I∞(φ) = J(φ)` by uniqueness of limits in ℝ.

## Why this is structural

The lean-dojo `weak_initial_condition` clause is one of four clauses of
`WeakSolution`. The energy-inequality clause is discharged by
`ns_trackb_lean_dojo_energy_bridge.lean`. This file gives the analogous
structural reduction for the initial-condition clause. Together they
give the typed-companion architecture for two of the four clauses; the
weak-momentum and weak-incompressibility clauses are ZTARE-domain
follow-ups.

The PDE content (the existence of the Galerkin sequence with the two
required pairing convergences) is the only analytical hypothesis we
expose. Classical Lions-Galerkin theory provides it; we do not
reformalize that here. The mathematics of (2) is just continuity of
the L²-pairing: `P_n u_0 → u_0` in L² ⇒ `⟨P_n u_0, φ⟩ → ⟨u_0, φ⟩` in ℝ.

## File status

Sorry-free. The file uses `Filter.Tendsto` machinery and
`tendsto_nhds_unique` / equality of limits to discharge the bridge
corollary. We follow the abstract `VelocityFieldInterface` approach of
the energy bridge so that this file is standalone (does not require
copying the full lean-dojo NS source tree into the ztare_proofs Lake
build). The abstract types instantiate at composition time with the
concrete lean-dojo definitions when those files are vendored.
-/

namespace ZtareProofs.NS

noncomputable section

universe u

/-! ## Test-function pairing as a scalar functional

For the initial-condition clause we only need to track, for each
test function `φ`, the SCALAR pairing `∫ ⟨u(0,·), φ⟩`. We package this
as an opaque assignment on the abstract `VelocityFieldInterface`.

This avoids re-introducing `Euc ℝ n`, `pairToEuc`, `partialDeriv` and
the lean-dojo measure-theoretic apparatus. At composition time, the
caller will instantiate `pairing u φ` with the concrete integral
`∫ x : Euc ℝ n, (∑ i, u (pairToEuc 0 x) i * φ x i)` from lean-dojo. -/

/-- Abstract scalar pairing functional `(u, φ) ↦ ⟨u(0,·), φ⟩`. -/
structure InitialPairingFunctional where
  /-- The opaque test-function space. At composition time this becomes
  the lean-dojo Schwartz-style space `Euc ℝ n → Euc ℝ n`. -/
  TestSpace : Type u
  /-- Smoothness predicate on a test function. -/
  IsTest : TestSpace → Prop
  /-- The scalar pairing `∫ ⟨u(0,·), φ⟩` evaluated against a velocity
  field at the initial time. -/
  initialPairing : VelocityFieldInterface 3 → TestSpace → ℝ
  /-- The scalar pairing `∫ ⟨u_0, φ⟩` evaluated against the abstract
  initial datum. -/
  initialDataPairing : TestSpace → ℝ

/-! ## Typed companion: the analytical content of the bridge

`WeakInitialConditionData` is the typed companion. It carries the two
PDE-side hypotheses (the truncation-matches-projection identity, and
the strong/weak convergence of the projected pairings) as Prop
fields, with the `Filter.Tendsto` shape Mathlib expects. -/

/-- Typed companion for the initial-condition bridge.

Captures: a Galerkin sequence `galerkinSeq` whose initial pairings
converge to two limits — the limit-solution's initial pairing and the
target initial-data pairing — and these two limits coincide for every
test function. -/
structure WeakInitialConditionData
    (F : InitialPairingFunctional)
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3) where
  /-- For each test `φ`, the truncated initial pairings converge to the
  target initial-data pairing. This is the spectral approximation
  `P_n u_0 → u_0` strongly in L², packaged as scalar convergence in ℝ
  via continuity of `⟨·, φ⟩`. -/
  pairing_to_initialData :
    ∀ φ : F.TestSpace, F.IsTest φ →
      Filter.Tendsto
        (fun n => F.initialPairing (galerkinSeq n) φ)
        Filter.atTop
        (nhds (F.initialDataPairing φ))
  /-- For each test `φ`, the truncated initial pairings ALSO converge
  to the limit-solution's initial pairing. At `t = 0` this is trivial
  if the truncation is constructed so that `u_n(0, ·) = P_n u_∞(0, ·)`
  and weak L² convergence holds (or, more strongly, by Lions
  compactness which gives strong L² convergence at fixed time). -/
  pairing_to_limit :
    ∀ φ : F.TestSpace, F.IsTest φ →
      Filter.Tendsto
        (fun n => F.initialPairing (galerkinSeq n) φ)
        Filter.atTop
        (nhds (F.initialPairing uInf φ))

/-! ## Main bridge corollary

From the typed companion, conclude the abstract analogue of
lean-dojo's `weak_initial_condition`: for every test `φ`, the
limit-solution's initial pairing equals the target initial-data
pairing. -/

/-- Bridge: produce the abstract `weak_initial_condition` clause from
the typed companion. -/
theorem weakInitialCondition_from_typed_companion
    {F : InitialPairingFunctional}
    {galerkinSeq : ℕ → VelocityFieldInterface 3}
    {uInf : VelocityFieldInterface 3}
    (data : WeakInitialConditionData F galerkinSeq uInf) :
    ∀ φ : F.TestSpace, F.IsTest φ →
      F.initialPairing uInf φ = F.initialDataPairing φ := by
  intro φ hφ
  -- Both `F.initialPairing uInf φ` and `F.initialDataPairing φ` are
  -- limits of the same sequence `n ↦ F.initialPairing (galerkinSeq n) φ`
  -- as `n → ∞`. Limits in ℝ are unique.
  have h_to_initialData :
      Filter.Tendsto (fun n => F.initialPairing (galerkinSeq n) φ)
        Filter.atTop (nhds (F.initialDataPairing φ)) :=
    data.pairing_to_initialData φ hφ
  have h_to_limit :
      Filter.Tendsto (fun n => F.initialPairing (galerkinSeq n) φ)
        Filter.atTop (nhds (F.initialPairing uInf φ)) :=
    data.pairing_to_limit φ hφ
  exact tendsto_nhds_unique h_to_limit h_to_initialData

/-! ## Spectral-projection constructor

The TYPED COMPANION above can be FED from the underlying scalar L²
content of the spectral-projection convergence. This subsection
provides a constructor that builds `WeakInitialConditionData` from a
strictly weaker hypothesis: pointwise pairing convergence at every
test function (which is what spectral approximation actually delivers).

The constructor is the trivial identity at the level of the Prop
fields, but it documents the load-bearing analytical step:
`P_n u_0 → u_0` strongly in L² is what supplies the `Filter.Tendsto`
hypotheses. We expose this as a separate constructor so that the
PDE-content "this is just spectral approximation" reduction is
visible in the bridge type. -/

/-- Build `WeakInitialConditionData` from per-test-function scalar
convergences. This is the structural "spectral projection ⇒ weak IC"
step, made explicit. -/
def WeakInitialConditionData.fromScalarConvergences
    {F : InitialPairingFunctional}
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3)
    (h_to_data :
      ∀ φ : F.TestSpace, F.IsTest φ →
        Filter.Tendsto (fun n => F.initialPairing (galerkinSeq n) φ)
          Filter.atTop (nhds (F.initialDataPairing φ)))
    (h_to_limit :
      ∀ φ : F.TestSpace, F.IsTest φ →
        Filter.Tendsto (fun n => F.initialPairing (galerkinSeq n) φ)
          Filter.atTop (nhds (F.initialPairing uInf φ))) :
    WeakInitialConditionData F galerkinSeq uInf where
  pairing_to_initialData := h_to_data
  pairing_to_limit := h_to_limit

/-! ## Strong-L² discharge: `pairing_to_initialData` from norm convergence

When the spectral projection converges in L²-norm — i.e.
`‖P_n u_0 − u_0‖_{L²} → 0` — and the test function is L² (which it is,
being smooth + compactly supported), the scalar convergence
`⟨P_n u_0, φ⟩ → ⟨u_0, φ⟩` follows by Cauchy-Schwarz:

  |⟨P_n u_0, φ⟩ − ⟨u_0, φ⟩| = |⟨P_n u_0 − u_0, φ⟩| ≤ ‖P_n u_0 − u_0‖ · ‖φ‖.

The constructor below packages this Cauchy-Schwarz step structurally:
it takes the L²-norm convergence and the per-test L² boundedness of
`φ`, and produces the scalar `Filter.Tendsto`. -/

/-- Helper: scalar `Tendsto` from a Cauchy-Schwarz error bound by a
sequence going to 0. -/
private theorem tendsto_of_cauchySchwarz_bound
    {a : ℕ → ℝ} {L : ℝ} (errBound : ℕ → ℝ) (Cφ : ℝ)
    (h_errBound_to_zero : Filter.Tendsto errBound Filter.atTop (nhds 0))
    (h_Cφ_nonneg : 0 ≤ Cφ)
    (h_dominated :
      ∀ n, |a n - L| ≤ errBound n * Cφ) :
    Filter.Tendsto a Filter.atTop (nhds L) := by
  -- Strategy: show `|a n - L| ≤ |errBound n| * (Cφ + 1)` and use the
  -- squeeze: `|errBound n| * (Cφ + 1) → 0` because `errBound n → 0`.
  rw [Metric.tendsto_atTop]
  intro ε hε
  have h_pos : 0 < Cφ + 1 := by linarith
  have h_div_pos : 0 < ε / (Cφ + 1) := div_pos hε h_pos
  rw [Metric.tendsto_atTop] at h_errBound_to_zero
  obtain ⟨N, hN⟩ := h_errBound_to_zero (ε / (Cφ + 1)) h_div_pos
  refine ⟨N, fun n hn => ?_⟩
  have h_err : |errBound n - 0| < ε / (Cφ + 1) := hN n hn
  rw [sub_zero] at h_err
  have h_eb_le : errBound n ≤ |errBound n| := le_abs_self _
  have h_dist : dist (a n) L = |a n - L| := by simp [Real.dist_eq]
  rw [h_dist]
  -- Key chain:
  --   |a n - L| ≤ errBound n * Cφ              (h_dominated)
  --             ≤ |errBound n| * Cφ            (le_abs_self · Cφ)
  --             ≤ |errBound n| * (Cφ + 1)      (Cφ ≤ Cφ + 1, |·| ≥ 0)
  --             < (ε / (Cφ + 1)) * (Cφ + 1)    (h_err)
  --             = ε                             (cancel Cφ + 1 ≠ 0)
  have h_step1 : |a n - L| ≤ errBound n * Cφ := h_dominated n
  have h_step2 : errBound n * Cφ ≤ |errBound n| * Cφ :=
    mul_le_mul_of_nonneg_right h_eb_le h_Cφ_nonneg
  have h_step3 : |errBound n| * Cφ ≤ |errBound n| * (Cφ + 1) := by
    have h_abs_nonneg : 0 ≤ |errBound n| := abs_nonneg _
    have h_Cφ_le : Cφ ≤ Cφ + 1 := by linarith
    exact mul_le_mul_of_nonneg_left h_Cφ_le h_abs_nonneg
  have h_step4 : |errBound n| * (Cφ + 1) < (ε / (Cφ + 1)) * (Cφ + 1) :=
    mul_lt_mul_of_pos_right h_err h_pos
  have h_step5 : (ε / (Cφ + 1)) * (Cφ + 1) = ε := by
    field_simp
  linarith

/-- Strong-L² discharge of `pairing_to_initialData`: from L²-norm
convergence of the spectral projection plus a per-test L²-norm bound,
produce the scalar `Filter.Tendsto` for `pairing_to_initialData`.

The hypothesis `h_pairing_error_bound` packages Cauchy-Schwarz: the
scalar pairing error is bounded by `‖P_n u_0 − u_0‖ · ‖φ‖`. -/
theorem pairing_to_initialData_from_strong_L2
    (F : InitialPairingFunctional)
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (projectionError : ℕ → ℝ)
    (h_proj_to_zero :
      Filter.Tendsto projectionError Filter.atTop (nhds 0))
    (h_pairing_error_bound :
      ∀ φ : F.TestSpace, F.IsTest φ →
        ∃ Cφ : ℝ, 0 ≤ Cφ ∧
          ∀ n, |F.initialPairing (galerkinSeq n) φ
                  - F.initialDataPairing φ|
                ≤ projectionError n * Cφ) :
    ∀ φ : F.TestSpace, F.IsTest φ →
      Filter.Tendsto
        (fun n => F.initialPairing (galerkinSeq n) φ)
        Filter.atTop
        (nhds (F.initialDataPairing φ)) := by
  intro φ hφ
  obtain ⟨Cφ, hCφ_nonneg, h_dom⟩ := h_pairing_error_bound φ hφ
  exact tendsto_of_cauchySchwarz_bound projectionError Cφ
    h_proj_to_zero hCφ_nonneg h_dom

/-! ## Three-clause composition note

The energy-inequality bridge in
`ns_trackb_lean_dojo_energy_bridge.lean` consumes:
- a Galerkin sequence `galerkinSeq : ℕ → VelocityFieldInterface 3`
- a limit solution `uInf : VelocityFieldInterface 3`
- a typed-companion bound on prefix prices

This file's `weakInitialCondition_from_typed_companion` consumes:
- the SAME Galerkin sequence and SAME limit solution
- a typed-companion data record on test-function pairings

Hence the two bridges COMPOSE: the Galerkin sequence + limit solution
are shared inputs across both clauses. A future bridge for the
weak-momentum-equation clause will share the same `galerkinSeq` /
`uInf`; the typed companion for that clause will carry the
weak-momentum scalar pairings. The four clauses of `WeakSolution` are
discharged by four typed companions over a single shared Galerkin
construction.

This is the typed-companion architecture's load-bearing claim: each
PDE-content obligation of `WeakSolution` reduces to a SHAPED scalar
convergence statement, and the typed companion makes the reduction
explicit and Lean-checkable. -/

end

end ZtareProofs.NS
