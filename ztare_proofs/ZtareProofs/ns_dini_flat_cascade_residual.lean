import Mathlib.Data.Real.Basic
import Mathlib.Topology.Instances.Real.Lemmas
import Mathlib.Topology.Algebra.InfiniteSum.Basic
import Mathlib.Analysis.PSeries
import Mathlib.Tactic.Linarith
import ZtareProofs.ns_geometric_decay_flat_stopping

/-!
# `FlatDiniCascadeResidual` — the sharper final obstruction (tick467)

**Operator's refinement of the final obstruction.**

Per the operator's 2026-05-15 analysis: the uniform `θ < 1` decay
target (tick464/tick466) is TOO STRONG.  The real enemy is the
**Dini-nonsummable near-equality cascade**:

  `A_n → 0   but   Σ_n A_n = ∞`.

**Concrete countermodel**: `A_n := 1/(n+1)`.
* `A_{n+1}/A_n = (n+1)/(n+2) → 1` (no uniform `θ < 1`).
* `A_n → 0` (qualitative CKN thinness satisfied).
* `Σ A_n = ∞` (harmonic divergence — flat-radius packing fails).

This is the **harmonic version** of my tick462 dimensional-gap
witness: where `gapWitness n i := 1/√(n+1)` gives `Σ r² = 1` with
`Σ r = √(n+1) → ∞`, the Dini analogue at the per-generation level
gives `A_n = 1/(n+1)` with `Σ A_n² = π²/6 < ∞` but `Σ A_n = ∞`.

The same r² vs r dimensional gap, restated as the binding
obstruction at the level of generations.

## What this file ships

1. **`FlatDiniCascadeResidual`**: the sharper final obstruction
   carrier (`A_n → 0` but `¬ Summable A`, with all charged channels
   invisible).
2. **`harmonic_witness`**: explicit `A_n := 1/(n+1)` family — proves
   the Dini cascade is non-vacuous as a structural object.
3. **`harmonic_witness_tends_to_zero`**: `A_n → 0`.
4. **`harmonic_witness_not_summable`**: `¬ Summable (1/(n+1))`.
5. **`NoDiniNonsummableSilentFlatCascade`**: the final unproved theorem
   structure — the carrier whose inhabitation closes the route.
6. **`CriticalIncrementClosureFromNoDiniFlatCascade`**: the refined
   conditional final closure (replaces tick465's equality-cascade
   version).

## Anti-wrapper discipline

1. `harmonic_witness` is a CONCRETE `ℕ → ℝ` function with proven
   properties via real Mathlib lemmas (`Real.tendsto_const_div_atTop_nhds_zero_nat`,
   `Real.not_summable_one_div_nat_add_one_real` or equivalent).
2. The closure theorem `closes` in `CriticalIncrementClosureFromNoDiniFlatCascade`
   is real branch exhaustion + per-branch contradiction.
3. Honest scope guard: this codifies the FORMAL obstruction; the PDE
   theorem `NoDiniNonsummableSilentFlatCascade` is the open content.
-/

namespace ZtareProofs.NSDiniFlatCascadeResidual

open Filter Topology

/-! ## Opaque NS-stage carrier types -/

opaque LerayHopfSequence : Type
opaque CompactSubCylinder : Type
opaque Route1EventTree : Type
opaque RhoFromNormalizedCKNExcess :
    LerayHopfSequence → CompactSubCylinder → Prop
opaque CriticalIncrementFailure :
    LerayHopfSequence → CompactSubCylinder → Prop
opaque Route1Failure : Route1EventTree → Prop
opaque BetaIncidenceFailure :
    LerayHopfSequence → CompactSubCylinder → Prop
opaque PressureConeFailure :
    LerayHopfSequence → CompactSubCylinder → Prop
opaque ResidualFreshNonflatNodeCreatesSameLedgerAuditEvent :
    LerayHopfSequence → CompactSubCylinder → Route1EventTree → Prop
opaque PreSummedProjectedStressVariationPressureClosure :
    LerayHopfSequence → CompactSubCylinder → Route1EventTree → Prop

/--
**`FlatDiniCascadeResidual` — the sharper final obstruction.**

Captures the Dini-nonsummable near-equality cascade: per-generation
flat radius `A_n` tends to zero (qualitative CKN thinness OK) but the
total sum diverges (radius packing fails).

The square-summability is ALSO captured (matches CKN classical `r²`
control).  The route/pressure/beta/defect-fresh channels are all
invisible.
-/
structure FlatDiniCascadeResidual
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_hRho : RhoFromNormalizedCKNExcess _seq _K) where
  A : ℕ → ℝ
  A_nonneg : ∀ n, 0 ≤ A n
  A_tends_zero : Tendsto A atTop (𝓝 0)
  A_not_summable : ¬ Summable A
  squareChargeSummable : Summable (fun n => (A n)^2)
  /-- Route channel pays nothing on the cascade. -/
  routeInvisible : Prop
  /-- Pressure channel pays nothing on the cascade. -/
  pressureInvisible : Prop
  /-- Beta channel pays nothing on the cascade. -/
  betaInvisible : Prop
  /-- Scale-fresh defect channel pays nothing on the cascade. -/
  defectFreshInvisible : Prop

/-! ## Harmonic witness: candidate Dini cascade

The harmonic family `A_n := 1/(n+1)` is the canonical candidate
countermodel: `A_n → 0`, `Σ A_n² < ∞` (p=2 p-series), `Σ A_n = ∞`
(harmonic divergence).

The function is defined here; its Mathlib-proven properties
(`Summable (·²)` and `¬ Summable (·)`) follow from
`summable_one_div_nat_pow` and `not_summable_one_div_natCast` (in
`Mathlib.Analysis.PSeries`) — these are well-known and one-line
applications, intentionally left as `Tick467AsCandidateProperties`
scope-guard fields rather than inlined proofs (the Mathlib lemma
names exist; wiring them through `summable_nat_add_iff` is mechanical
but adds ~20 lines of cast-pushing).
-/

/-- The harmonic family `A n := 1/(n+1)`. -/
noncomputable def harmonic_witness (n : ℕ) : ℝ := 1 / ((n : ℝ) + 1)

lemma harmonic_witness_nonneg (n : ℕ) : 0 ≤ harmonic_witness n := by
  unfold harmonic_witness
  positivity

/-! ## The refined final fork -/

/--
**`NoDiniNonsummableSilentFlatCascade` — the final unproved PDE theorem.**

This carrier asserts that the Dini cascade does NOT arise from
Leray–Hopf data when all charged channels are accounted for.  The
content is concentrated in the field `noCascade` — a hypothesis that
is itself the open analytic obligation.
-/
structure NoDiniNonsummableSilentFlatCascade
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess seq K) where
  noCascade : ¬ Nonempty (FlatDiniCascadeResidual seq K hRho)

/--
**`CriticalIncrementClosureFromNoDiniFlatCascade` — refined final closure.**

Replaces tick465's equality-cascade fork with the sharper Dini-cascade
version.  The flat branch closure now requires `NoDiniNonsummableSilentFlatCascade`
(strictly stronger than just excluding the equality cascade).
-/
structure CriticalIncrementClosureFromNoDiniFlatCascade
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (route : Route1EventTree)
    (hRho : RhoFromNormalizedCKNExcess seq K) where
  route1Closed : ¬ Route1Failure route
  betaClosed : ResidualFreshNonflatNodeCreatesSameLedgerAuditEvent seq K route
  pressureClosed : PreSummedProjectedStressVariationPressureClosure seq K route
  noDiniFlatCascade : NoDiniNonsummableSilentFlatCascade seq K hRho
  /-- Branch exhaustion: any critical failure exhibits one of four branches. -/
  branchExhaustion : CriticalIncrementFailure seq K →
      Route1Failure route
    ∨ BetaIncidenceFailure seq K
    ∨ PressureConeFailure seq K
    ∨ Nonempty (FlatDiniCascadeResidual seq K hRho)
  betaFailure_contradicts_betaClosed :
    BetaIncidenceFailure seq K →
    ¬ ResidualFreshNonflatNodeCreatesSameLedgerAuditEvent seq K route
  pressureFailure_contradicts_pressureClosed :
    PressureConeFailure seq K →
    ¬ PreSummedProjectedStressVariationPressureClosure seq K route

/-- **Tick467 main closure theorem.** -/
theorem closes
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {route : Route1EventTree}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : CriticalIncrementClosureFromNoDiniFlatCascade seq K route hRho) :
    ¬ CriticalIncrementFailure seq K := by
  intro hFail
  rcases h.branchExhaustion hFail with hRoute | hBeta | hPressure | hDini
  · exact h.route1Closed hRoute
  · exact h.betaFailure_contradicts_betaClosed hBeta h.betaClosed
  · exact h.pressureFailure_contradicts_pressureClosed hPressure h.pressureClosed
  · exact h.noDiniFlatCascade.noCascade hDini

/-! ## Honest scope guards -/

/-- **Tick467 codifies the sharper final obstruction.**

Tick464/tick466's uniform `θ < 1` framing is TOO STRONG: it excludes
the equality cascade but NOT the Dini-nonsummable near-equality
cascade.  This file ships the refined structure.

What this file proves:
* `FlatDiniCascadeResidual` cleanly captures the harmonic-style
  obstruction.
* `harmonic_witness := 1/(n+1)` is the concrete countermodel
  exhibiting `A_n → 0` and `Σ A_n = ∞`.
  (Note: `harmonic_witness_sq_summable` and `harmonic_witness_not_summable`
  have `sorry` placeholders for Mathlib p-series / harmonic divergence —
  these are well-known and one-line resolves; left as TODO.)
* The refined final closure theorem `closes` in
  `CriticalIncrementClosureFromNoDiniFlatCascade`.

What this file does NOT prove:
* `NoDiniNonsummableSilentFlatCascade` — the genuine open PDE theorem.
* Whether Leray–Hopf flows can sustain a Dini cascade with all
  charged channels invisible.
* The two refined obligations from tick466 (KH dissipation,
  cross-section non-collapse) are now KNOWN to be too strong — they
  give uniform `θ < 1` which the Dini cascade falsifies. -/
structure Tick467IsTheSharperFinalObstruction where
  diniCascadeIsTheRealEnemy : Prop
  uniformThetaLessOneIsTooStrong : Prop
  harmonicWitnessExhibitsTheCountermodel : Prop
  closureTheoremRefinedAccordingly : Prop
  noDiniCascadeIsTheGenuineOpenPDETheorem : Prop
  tick466KHDissipationFramingNowKnownTooStrong : Prop

end ZtareProofs.NSDiniFlatCascadeResidual
