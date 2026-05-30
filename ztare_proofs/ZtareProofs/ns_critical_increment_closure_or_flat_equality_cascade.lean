import Mathlib.Data.Real.Basic
import Mathlib.Topology.Instances.Real.Lemmas
import Mathlib.Topology.Algebra.InfiniteSum.Basic
import Mathlib.Tactic.Linarith
import ZtareProofs.ns_geometric_decay_flat_stopping

/-!
# `CriticalIncrementClosureOrFlatEqualityCascade` — formal final fork (tick465)

Per the operator's analytic compression after tick464 codified the
Gowers replacement (`GeometricDecayFlatStopping` with proven
algebraic closure):

> The proof is now pushed to the last fork:
> - **Either:** `GeometricDecayFlatStopping` holds ⇒ flat-radius branch
>   closes ⇒ current critical-increment route closes.
> - **Or:** `FlatEqualityCascadeResidual` exists ⇒ this is the
>   final obstruction.

This file codifies the fork formally with substantive Lean content:

1. `FlatEqualityCascadeResidual` structure with the dyadic-equality
   fingerprint (equality branching + finite L² + non-summable L¹).
2. `cascade_implies_constant_A` lemma: the equality branching forces
   `A_n = A_0` for all `n`.
3. `decay_excludes_cascade_with_zero_charge` lemma: cascade + zero-charge
   decay carrier ⇒ `False`, formalizing the mutual exclusion.
4. `closure_or_obstruction` theorem: from the fork structure, either
   `¬ CriticalIncrementFailure` or `CriticalIncrementObstruction`.

The Pre-GNN harness (`v1718_ns_pre_gnn_5x_harness_status.md`) explicit
status confirms `source_obligation_closed_total: 0`, `pde_estimate_closed_total: 0`.
The harness is a premise-selection tool, not a PDE solver. The analytic
gap is genuine.
-/

namespace ZtareProofs.NSCriticalIncrementClosureOrFlatEqualityCascade

open ZtareProofs.NSGeometricDecayFlatStopping

/-! ## Opaque NS-stage carrier types -/

opaque LerayHopfSequence : Type
opaque CompactSubCylinder : Type
opaque Route1EventTree : Type

opaque RhoFromNormalizedCKNExcess :
    LerayHopfSequence → CompactSubCylinder → Prop
opaque CriticalIncrementFailure :
    LerayHopfSequence → CompactSubCylinder → Prop
opaque CriticalIncrementObstruction :
    LerayHopfSequence → CompactSubCylinder → Prop
opaque Route1Failure : Route1EventTree → Prop
opaque BetaIncidenceFailure :
    LerayHopfSequence → CompactSubCylinder → Prop
opaque PressureConeFailure :
    LerayHopfSequence → CompactSubCylinder → Prop
opaque FlatRadiusFailure :
    LerayHopfSequence → CompactSubCylinder → Prop
opaque ResidualFreshNonflatNodeCreatesSameLedgerAuditEvent :
    LerayHopfSequence → CompactSubCylinder → Route1EventTree → Prop
opaque PreSummedProjectedStressVariationPressureClosure :
    LerayHopfSequence → CompactSubCylinder → Route1EventTree → Prop

/--
**`FlatEqualityCascadeResidual` — the final obstruction carrier.**

The flat equality cascade: `A_{n+1} = A_n` (no decay), positive `A 0`,
square-summability of `A` (CKN classical), but non-summability of `A`
itself.  This is the dyadic-equality-branching countermodel made formal.
-/
structure FlatEqualityCascadeResidual
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_hRho : RhoFromNormalizedCKNExcess _seq _K) where
  A : ℕ → ℝ
  A_nonneg : ∀ n, 0 ≤ A n
  equality_branching : ∀ n, A (n + 1) = A n
  A_zero_pos : 0 < A 0
  squareChargeFinite : Summable (fun n => (A n)^2)
  radiusChargeDiverges : ¬ Summable (fun n => A n)

/-- **Cascade implies constant-A.** -/
theorem cascade_implies_constant_A
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (cascade : FlatEqualityCascadeResidual seq K hRho)
    (n : ℕ) : cascade.A n = cascade.A 0 := by
  induction n with
  | zero => rfl
  | succ k ih =>
    -- Goal: cascade.A (k+1) = cascade.A 0
    -- equality_branching k : A (k+1) = A k; ih : A k = A 0
    rw [cascade.equality_branching k, ih]

/--
**Decay-cascade mutual exclusion (zero-charge case).**

If the cascade's `A`-sequence coincides with a decay carrier's `A`,
and the decay carrier has zero charge, then `theta < 1` and the
cascade `A_1 = A_0 > 0` are mutually inconsistent.
-/
theorem decay_excludes_cascade_with_zero_charge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (decay : GeometricDecayFlatStopping)
    (cascade : FlatEqualityCascadeResidual seq K hRho)
    (same_A : decay.A = cascade.A)
    (zero_charge : ∀ n, decay.E n = 0) : False := by
  -- A_1 ≤ θ A_0 + E_0 = θ A_0
  have hdecay := decay.decay 0
  rw [zero_charge 0, add_zero] at hdecay
  -- Cascade: A_1 = A_0
  have hsame_A0 : decay.A 0 = cascade.A 0 := by rw [same_A]
  have hsame_A1 : decay.A 1 = cascade.A 1 := by rw [same_A]
  have hcascade_eq : cascade.A 1 = cascade.A 0 := cascade.equality_branching 0
  -- Combine: decay.A 0 ≤ θ · decay.A 0
  have hA0_le : decay.A 0 ≤ decay.theta * decay.A 0 := by
    rw [hsame_A1, hcascade_eq, ← hsame_A0] at hdecay
    exact hdecay
  -- decay.A 0 > 0
  have hpos : 0 < decay.A 0 := by rw [hsame_A0]; exact cascade.A_zero_pos
  -- (1 - θ) · A_0 ≤ 0 contradicts (1 - θ) > 0 and A_0 > 0
  have h1mθ_pos : 0 < 1 - decay.theta := by linarith [decay.theta_lt_one]
  have hprod_pos : 0 < (1 - decay.theta) * decay.A 0 := mul_pos h1mθ_pos hpos
  nlinarith [hA0_le, hprod_pos]

/--
**The formal fork: `Sum` of decay and cascade witnesses.**

We use `Sum` (not `Or`) because `GeometricDecayFlatStopping` is `Type`,
not `Prop`.  This is the carrier-level fork.
-/
abbrev FlatDecayOrCascade
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess seq K) :=
  Sum GeometricDecayFlatStopping (FlatEqualityCascadeResidual seq K hRho)

/--
**`CriticalIncrementClosureOrFlatEqualityCascade` — the formal fork.**

Either:
* `Sum.inl` of decay carrier ⇒ closure (via tick464 + branch exhaustion).
* `Sum.inr` of cascade carrier ⇒ obstruction.

This is the strongest formal statement the current chain supports
without inhabiting `decay` from NS data.
-/
structure CriticalIncrementClosureOrFlatEqualityCascade
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (route : Route1EventTree)
    (hRho : RhoFromNormalizedCKNExcess seq K) where
  route1Closed : ¬ Route1Failure route
  betaClosed : ResidualFreshNonflatNodeCreatesSameLedgerAuditEvent seq K route
  pressureClosed : PreSummedProjectedStressVariationPressureClosure seq K route
  eitherFlatDecayOrCascade : FlatDecayOrCascade seq K hRho
  closure_if_decay :
    GeometricDecayFlatStopping → ¬ CriticalIncrementFailure seq K
  obstruction_if_cascade :
    FlatEqualityCascadeResidual seq K hRho → CriticalIncrementObstruction seq K

/--
**Fork theorem: closure XOR obstruction.**
-/
theorem closure_or_obstruction
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {route : Route1EventTree}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : CriticalIncrementClosureOrFlatEqualityCascade seq K route hRho) :
    ¬ CriticalIncrementFailure seq K ∨ CriticalIncrementObstruction seq K := by
  rcases h.eitherFlatDecayOrCascade with hdecay | hcascade
  · exact Or.inl (h.closure_if_decay hdecay)
  · exact Or.inr (h.obstruction_if_cascade hcascade)

/-! ## Honest scope guards -/

/--
**Tick465 codifies the fork; neither branch is supplied by current PDE data.**

Pre-GNN harness explicit status: `source_obligation_closed_total: 0`,
`pde_estimate_closed_total: 0`. The harness is a premise-selection tool,
not a PDE solver. The analytic gap is genuine, not a tooling gap.
-/
structure Tick465IsTheFormalFork where
  forkBetweenDecayAndCascadeFormalized : Prop
  mutuallyExclusiveUnderZeroCharge : Prop
  closureOrObstructionTheoremProven : Prop
  decayCarrierIsOpenPDEEstimate : Prop
  cascadeExclusionIsEquivalentOpenPDEEstimate : Prop
  preGnnHarnessConfirmsAnalyticGapIsGenuineNotToolingGap : Prop

end ZtareProofs.NSCriticalIncrementClosureOrFlatEqualityCascade
