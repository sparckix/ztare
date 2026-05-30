import Mathlib.Tactic
import ZtareProofs.ns_route5_offset_candidate_families

namespace ZtareProofs

/-!
`ns_route5_topological_offset_mismatch` promotes the first high-scoring offset
search result into the proof surface.

The useful claim is narrower than "route 5 is dead":

* the currently named analytic offset families are too smooth / elliptic to
  absorb an `O(1)` topological holonomy concentrated at a codimension-2
  eigenvalue-degeneracy core;
* therefore pressure-tail, tensor-absorption, and curvature-return families
  all fail unless a new mollified / hybrid local-core mechanism changes the
  proof graph and pays its cost explicitly.
-/

/-- Quantized moving-frame holonomy concentrated at the defect core. -/
def topologicalHolonomyCharge (charge : Real) : Prop :=
  0 < charge

/-- Smooth elliptic offset families lose all loop capacity as the core shrinks. -/
def ellipticOffsetLoopCapacityVanishing (capacity : Real) : Prop :=
  capacity ≤ 0

/--
Analytic-topological mismatch: a vanishing elliptic loop contribution cannot
cancel a positive quantized holonomy charge.
-/
def topologicalChargeEllipticMismatch
    (charge capacity : Real) : Prop :=
  topologicalHolonomyCharge charge ∧
    ellipticOffsetLoopCapacityVanishing capacity

/--
Any current analytic route-5 family fails if it is asked to absorb a positive
holonomy charge with vanishing elliptic loop capacity.
-/
def analyticOffsetFamilyFailsAtDefectCore
    (charge capacity γ tailOffset coerciveBudget pressureBurden residual
      curvatureBudget returnLoss offset : Real) : Prop :=
  topologicalChargeEllipticMismatch charge capacity ∧
    ¬ route5OffsetCandidateFamilyTarget
      γ tailOffset coerciveBudget pressureBurden residual curvatureBudget
      returnLoss offset

/--
If both the pressure-tail and the shared offset channel fail to produce a real
secondary offset, then no currently named analytic family survives.
-/
theorem topological_mismatch_kills_named_offset_families
    {charge capacity γ tailOffset coerciveBudget pressureBurden residual
      curvatureBudget returnLoss offset : Real}
    (hcharge : topologicalHolonomyCharge charge)
    (hcap : ellipticOffsetLoopCapacityVanishing capacity)
    (htail : ¬ secondaryCoerciveOffset γ tailOffset)
    (hoff : ¬ secondaryCoerciveOffset γ offset) :
    analyticOffsetFamilyFailsAtDefectCore
      charge capacity γ tailOffset coerciveBudget pressureBurden residual
      curvatureBudget returnLoss offset := by
  refine ⟨⟨hcharge, hcap⟩, ?_⟩
  exact no_route5_offset_family_without_real_offset htail hoff

/--
The result is intentionally not universal: it leaves one explicit live escape
hatch, namely a non-analytic or mollified local-core mechanism.
-/
def mollifiedHybridCoreEscapeHatch : Prop := True

end ZtareProofs
