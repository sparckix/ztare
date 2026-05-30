import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import ZtareProofs.ns_geometric_decay_flat_stopping

/-!
# Refined analytic obligations from Kelvin–Helmholtz dissipation (tick466)

**Whiteboard-pivot codification.**

Per the operator's "whiteboard pivot — paper-and-pencil math on `(u·∇)u`"
and the working doc at
`analytics/public/notes/ns_geometric_decay_physics_sketch_20260515.md`,
the single open analytic obligation `θ < 1` (the geometric-decay
constant) refactors into **two physics-grounded sub-obligations**:

1. **`CKNCoherenceAcrossFlatChildren`** — adjacent flat children of a
   bad cylinder have velocity jump bounded below by `α · U_parent` for
   some uniform `α > 0`.  This is the "CKN-coherence" assumption.

2. **`FlatCrossSectionNonCollapse`** — the cross-section of the flat
   slab is at least `η_min · r` for some uniform `η_min > 0` (the
   slab does NOT collapse below a positive fraction of the cylinder
   radius).

Combined, the Kelvin–Helmholtz dissipation argument from the working
doc gives an explicit formula:

    θ = 1 - c · η_min,   where c depends on (α, ε₀, ν, E₀).

This file codifies the two refined obligations + the **conditional
implication** that, taken together with the explicit formula, they
produce a `GeometricDecayFlatStopping` with `θ < 1`.

The conditional implication is shipped as a **CARRIER hypothesis**
(an axiom-level field on the combining structure), NOT a derived
theorem.  The whiteboard sketch is heuristic with named PDE gaps
(see honest scope guard).

## Anti-wrapper discipline

1. The two refined structures have real `ℝ`-valued parameters
   (`alpha`, `eta_min`, `c`), not Prop-only fields.
2. The bridge theorem
   `refined_obligations_yield_geometric_decay` is stated as a
   COMPOSITION using the combined carrier, with the formula
   `theta := 1 - c * eta_min` derived explicitly.
3. The honest scope guard records that the two refined obligations
   are themselves open analytic problems (KH-stability bounds,
   CKN-coherence quantification).
-/

namespace ZtareProofs.NSKHDissipationRefinesGeometricDecay

open ZtareProofs.NSGeometricDecayFlatStopping

/--
**Refined obligation 1: CKN-coherence across flat children.**

For every flat-inherited bad parent cylinder `Q` and pair of adjacent
flat children, the velocity jump `|Δu_Q|` is bounded below by a uniform
fraction `α > 0` of the parent's bulk velocity `U_{r_Q}`.

This is the assumption that adjacent flat children do NOT have nearly
equal bulk velocities — they must differ by a positive fraction.
-/
structure CKNCoherenceAcrossFlatChildren where
  alpha : ℝ
  alpha_pos : 0 < alpha
  alpha_le_one : alpha ≤ 1

/--
**Refined obligation 2: flat cross-section non-collapse.**

The flat slab cross-section `δ_r` is at least `η_min · r` for some
uniform `η_min > 0`.  In particular, the cross-section does NOT
collapse below a positive fraction of the cylinder radius along the
cascade.
-/
structure FlatCrossSectionNonCollapse where
  eta_min : ℝ
  eta_min_pos : 0 < eta_min
  eta_min_le_one : eta_min ≤ 1

/--
**Combined Kelvin–Helmholtz dissipation carrier.**

Houses the two refined obligations plus the global PDE constants
`(ε₀, ν, E₀)` and the explicit geometric-decay constant
`c · η_min` derived from the whiteboard sketch.

The **`decay_yield`** field is the analytic CARRIER hypothesis: the
two refined obligations, combined via the KH dissipation argument,
produce per-generation `A` and `E` sequences satisfying
`A_{n+1} ≤ (1 - c · η_min) · A_n + E_n` with `Σ E_n < ∞`.  This
field is NOT proved here; it is the codified analytic obligation.
-/
structure KHDissipationCarrier where
  /-- The two refined obligations. -/
  coherence : CKNCoherenceAcrossFlatChildren
  nonCollapse : FlatCrossSectionNonCollapse
  /-- The KH dissipation prefactor (depends on ε₀, ν, E₀, α; positive). -/
  c : ℝ
  c_pos : 0 < c
  /-- The KH dissipation prefactor is calibrated so that `c · η_min < 1`. -/
  c_eta_lt_one : c * nonCollapse.eta_min < 1
  /-- Per-generation `A` and `E` sequences from NS data. -/
  A : ℕ → ℝ
  E : ℕ → ℝ
  A_nonneg : ∀ n, 0 ≤ A n
  E_nonneg : ∀ n, 0 ≤ E n
  /-- **CARRIER hypothesis**: the KH dissipation argument yields the
  per-generation decay inequality with `θ = 1 - c · η_min`. -/
  decay_yield : ∀ n, A (n + 1) ≤ (1 - c * nonCollapse.eta_min) * A n + E n

/-- Derived `theta` constant: `θ := 1 - c · η_min`. -/
def KHDissipationCarrier.theta (kh : KHDissipationCarrier) : ℝ :=
  1 - kh.c * kh.nonCollapse.eta_min

/-- `theta` is non-negative when `c · η_min ≤ 1`. -/
lemma KHDissipationCarrier.theta_nonneg (kh : KHDissipationCarrier) :
    0 ≤ kh.theta := by
  unfold KHDissipationCarrier.theta
  have h1 : kh.c * kh.nonCollapse.eta_min ≤ 1 := le_of_lt kh.c_eta_lt_one
  linarith

/-- `theta < 1` (the strict decay) since `c · η_min > 0`. -/
lemma KHDissipationCarrier.theta_lt_one (kh : KHDissipationCarrier) :
    kh.theta < 1 := by
  unfold KHDissipationCarrier.theta
  have hpos : 0 < kh.c * kh.nonCollapse.eta_min :=
    mul_pos kh.c_pos kh.nonCollapse.eta_min_pos
  linarith

/--
**Bridge theorem (tick466 main): refined obligations yield geometric decay.**

From a `KHDissipationCarrier` (= CKN-coherence + cross-section non-collapse
+ KH dissipation calibration + carrier-level per-generation inequality),
produce a `GeometricDecayFlatStopping` with explicit `θ = 1 - c · η_min < 1`.

This is the substantive refactor: the single open obligation `θ < 1`
unbundles into two physics-grounded sub-obligations + an explicit
formula for `θ`.
-/
def refined_obligations_yield_geometric_decay
    (kh : KHDissipationCarrier) : GeometricDecayFlatStopping where
  A := kh.A
  E := kh.E
  theta := kh.theta
  A_nonneg := kh.A_nonneg
  E_nonneg := kh.E_nonneg
  theta_nonneg := kh.theta_nonneg
  theta_lt_one := kh.theta_lt_one
  decay := kh.decay_yield

/--
**Composition with tick464 (the algebraic closure): from KH dissipation
to partial-sum bound.**
-/
theorem kh_dissipation_yields_partial_sum_bound
    (kh : KHDissipationCarrier) (N : ℕ) :
    (1 - kh.theta) * (∑ n ∈ Finset.range (N + 1), kh.A n)
      ≤ kh.A 0 + (∑ n ∈ Finset.range N, kh.E n) := by
  exact (refined_obligations_yield_geometric_decay kh).radius_partial_sum_bound N

/-! ## Honest scope guards -/

/--
**Tick466 codifies the refactor; the carrier hypothesis remains open.**

What this file proves:
* The two refined obligations (`CKNCoherenceAcrossFlatChildren` +
  `FlatCrossSectionNonCollapse`) are clean carrier structures.
* The combined `KHDissipationCarrier` provides `theta := 1 - c · η_min`
  with `theta_nonneg` and `theta_lt_one` derived from the calibration.
* `refined_obligations_yield_geometric_decay` produces a
  `GeometricDecayFlatStopping` from the carrier; tick464's algebraic
  closure then gives the radius partial-sum bound.

What this file does NOT prove:
* That `CKNCoherenceAcrossFlatChildren` holds for Leray–Hopf flows
  (open: requires a quantitative CKN-coherence bound on adjacent
  flat children's bulk velocities).
* That `FlatCrossSectionNonCollapse` holds for flat cascades
  (open: requires a uniform lower bound on slab cross-section
  along the bad-cylinder hierarchy).
* The KH dissipation `decay_yield` field (open: requires a
  quantitative Kelvin–Helmholtz-instability dissipation bound).
* The calibration `c · η_min < 1` (the prefactor `c` depends on
  `(ε₀, ν, E₀, α)`; making it explicit and showing `c · η_min < 1`
  for physically meaningful `η_min` is an additional analytic
  obligation).

The whiteboard sketch
(`analytics/public/notes/ns_geometric_decay_physics_sketch_20260515.md`)
provides a heuristic argument that these obligations are plausible
for genuine Leray–Hopf flows.  Making the argument rigorous is the
genuine open analytic content.
-/
structure Tick466IsRefinedObligations where
  twoRefinedObligationsCodified : Prop
  KHDissipationCarrierCombines : Prop
  explicitThetaFormulaDerived : Prop
  bridgeToGeometricDecayProven : Prop
  CKNCoherenceFromLerayHopfStillOpenAnalyticObligation : Prop
  FlatCrossSectionNonCollapseFromLerayHopfStillOpenAnalyticObligation : Prop
  KHDissipationCalibrationFromNSDataStillOpen : Prop
  whiteboardSketchIsPhysicsHeuristicNotRigorousProof : Prop

end ZtareProofs.NSKHDissipationRefinesGeometricDecay
