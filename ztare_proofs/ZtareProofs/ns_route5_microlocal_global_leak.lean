import Mathlib.Tactic
import ZtareProofs.ns_route5_tensor_absorption_ellipticity

namespace ZtareProofs

/-!
`ns_route5_microlocal_global_leak` promotes the theorem burden exposed by the
micro-local diffusive absorption attempt.

The useful point is not "pseudo-differential smoothing exists." It is:

* even if local ellipticity is paid, the branch still needs a theorem that the
  residual leaks away globally on non-compact domains rather than accumulating.
-/

/-- Local micro-local dilution claim. -/
def microlocalDilutionTarget
    (rawPenalty diffusiveScale smoothingOrder dilutedPenalty : Real) : Prop :=
  0 ≤ rawPenalty ∧
    0 ≤ diffusiveScale ∧
    0 ≤ smoothingOrder ∧
    dilutedPenalty = rawPenalty * diffusiveScale ^ smoothingOrder ∧
    dilutedPenalty ≤ rawPenalty

/-- Global non-compact-domain leak control. -/
def noncompactGlobalLeakControlTarget
    (globalResidual decayBudget horizon : Real) : Prop :=
  0 ≤ globalResidual ∧
    0 ≤ decayBudget ∧
    0 ≤ horizon ∧
    globalResidual ≤ decayBudget * horizon

/-- Exact branch target for micro-local diffusive absorption. -/
def microlocalDiffusiveAbsorptionSurvivorTarget
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty
      globalResidual decayBudget horizon : Real) : Prop :=
  route5TensorAbsorptionNextDiscriminator
      γ coerciveBudget pressureBurden residual offset lambdaMin ∧
    microlocalDilutionTarget
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty ∧
    noncompactGlobalLeakControlTarget
      globalResidual decayBudget horizon

end ZtareProofs
