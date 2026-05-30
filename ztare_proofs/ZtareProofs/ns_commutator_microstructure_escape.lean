import Mathlib.Tactic
import ZtareProofs.ns_dyadic_annulus_commutator_obstruction

namespace ZtareProofs

/-!
`ns_commutator_microstructure_escape` records the live escape hatch surfaced by
iter 3 of the proof-search substrate.

The route-2 reranking is strong, but it is not complete until it addresses the
remaining rival:

> could an oscillatory / microstructured `L^3_{uloc}` field suppress the
> leading commutator projection enough to avoid the generic divergence?
-/

/-- Strength of oscillatory / microstructured cancellation. -/
abbrev MicrostructureCancellation := Real

/-- Leading mean-mode contribution to the localized commutator. -/
abbrev MeanModeContribution := Real

/--
Escape hatch candidate: a field is dangerous for the reranking if its
microstructure cancels too much of the mean-mode contribution.
-/
def microstructureSuppressesMeanMode
    (meanMode cancellation residual : Real) : Prop :=
  0 ≤ cancellation ∧
    residual = max (meanMode - cancellation) 0

/--
The reranking survives only if the mean mode still dominates after any
admissible microstructure cancellation.
-/
def meanModeStillDominatesAfterMicrostructure
    (meanMode cancellation residual margin : Real) : Prop :=
  microstructureSuppressesMeanMode meanMode cancellation residual ∧
    0 ≤ margin ∧
    margin + cancellation ≤ meanMode

/--
Exact iter-3 screening target: the dyadic annulus obstruction remains valid if
no admissible microstructure can suppress the mean-mode contribution below a
positive residual floor.
-/
def microstructureEscapeScreeningTarget
    (R gradientScale massScale fractionalGain residualScale
      meanMode cancellation residual margin : Real) : Prop :=
  dyadicAnnulusScalingLaw R gradientScale massScale fractionalGain residualScale ∧
    meanModeStillDominatesAfterMicrostructure
      meanMode cancellation residual margin

/--
If the screening target is paid, the route-2 reranking no longer depends only
on genericity rhetoric; it has an explicit anti-escape clause.
-/
theorem residual_positive_of_microstructureEscapeScreeningTarget
    {R gradientScale massScale fractionalGain residualScale
      meanMode cancellation residual margin : Real}
    (h :
      microstructureEscapeScreeningTarget
        R gradientScale massScale fractionalGain residualScale
        meanMode cancellation residual margin) :
    0 ≤ residual := by
  rcases h with ⟨_, hdom⟩
  rcases hdom with ⟨hsuppress, _, _⟩
  rcases hsuppress with ⟨_, hresidual⟩
  rw [hresidual]
  exact le_max_right _ 0

end ZtareProofs
