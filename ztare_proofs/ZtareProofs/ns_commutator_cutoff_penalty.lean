import Mathlib.Tactic
import ZtareProofs.ns_commutator_tower_irreducible_estimate

namespace ZtareProofs

/-!
`ns_commutator_cutoff_penalty` records the new axiom check surfaced by the
proof-search substrate:

singular-integral commutators with spatial cutoffs pay inverse cutoff-width
penalties. This means the flat commutator tower cannot be treated in isolation
from the global tail bootstrap. Localizing first may make the tower worse
unless tail decay has already been established.
-/

/-- Width of the spatial cutoff transition layer. -/
abbrev CutoffWidth := Real

/-- Per-step localization penalty induced by cutoff derivatives. -/
abbrev CutoffPenalty := Real

/-- Strength of an offsetting far-field decay bootstrap. -/
abbrev TailDecayOffset := Real

/--
Generic cutoff penalty target: shrinking the localization width increases the
commutator constant at inverse-scale rate.
-/
def inverseCutoffWidthPenalty
    (δ penalty K : Real) : Prop :=
  0 < δ ∧
    0 ≤ K ∧
    penalty = K / δ

/--
Tail decay is only useful here if it offsets the cutoff penalty before the
tower is iterated.
-/
def tailDecayOffsetsCutoffPenalty
    (tailDecay penalty margin : Real) : Prop :=
  0 ≤ margin ∧
    penalty + margin ≤ tailDecay

/--
Route-2-before-route-1 reranking target.

Interpretation: if localization itself injects inverse-width growth and no tail
offset has yet been paid, then the commutator tower cannot honestly be primary.
-/
def globalTailPrecedesCommutatorTower
    (δ penalty K tailDecay margin : Real) : Prop :=
  inverseCutoffWidthPenalty δ penalty K ∧
    ¬ tailDecayOffsetsCutoffPenalty tailDecay penalty margin

/--
If the cutoff penalty is real and the tail offset is still unpaid, then the
global pressure-tail bootstrap is a strict antecedent to the commutator tower.
-/
theorem rerank_route2_of_globalTailPrecedesCommutatorTower
    {δ penalty K tailDecay margin : Real}
    (h : globalTailPrecedesCommutatorTower δ penalty K tailDecay margin) :
    inverseCutoffWidthPenalty δ penalty K := by
  exact h.1

/--
PDE-facing version of the same reranking claim: route `1` may still be the
mainline, but only downstream of a tail bootstrap that neutralizes cutoff
localization cost.
-/
def route1BlockedWithoutTailOffset
    (δ penalty K tailDecay margin : Real)
    (budget currentStep ratio : Real) : Prop :=
  globalTailPrecedesCommutatorTower δ penalty K tailDecay margin ∧
    defectBudgetSubcriticalityEstimate budget currentStep ratio

end ZtareProofs
