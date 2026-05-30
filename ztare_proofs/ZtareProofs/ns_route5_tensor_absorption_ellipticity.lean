import Mathlib.Tactic
import ZtareProofs.ns_route5_offset_candidate_families

namespace ZtareProofs

/-!
`ns_route5_tensor_absorption_ellipticity` promotes the informative content of
iter 4 on the retargeted offset-family substrate.

The useful claim is not "tensor absorption wins." It is narrower:

* tensor absorption is the remaining smooth on-graph candidate after the
  topological mismatch and global singular-capacity objections,
* but it survives only if the effective metric never loses strict ellipticity.
-/

/-- Strict ellipticity of the effective tensor metric. -/
def effectiveMetricEllipticityTarget (lambdaMin : Real) : Prop :=
  0 < lambdaMin

/--
Repulsion-style sufficient condition: if the defect tensor never pushes the
metric below zero, the tensor-absorption branch remains alive.
-/
def tensorAbsorptionEllipticitySurvivalTarget
    (γ coerciveBudget pressureBurden residual offset lambdaMin : Real) : Prop :=
  tensorAbsorptionOffsetFamilyTarget
    γ coerciveBudget pressureBurden residual offset ∧
    effectiveMetricEllipticityTarget lambdaMin

/--
If the effective metric loses ellipticity even locally, the tensor-absorption
route collapses on the current proof graph.
-/
theorem tensor_absorption_collapses_without_ellipticity
    {γ coerciveBudget pressureBurden residual offset lambdaMin : Real}
    (hcollapse : ¬ effectiveMetricEllipticityTarget lambdaMin) :
    ¬ tensorAbsorptionEllipticitySurvivalTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin := by
  intro h
  exact hcollapse h.2

/--
Conversely, if tensor absorption already pays the route-5 offset burden and the
metric stays strictly elliptic, then the branch survives this iter-4
discriminator.
-/
theorem tensor_absorption_survives_if_elliptic
    {γ coerciveBudget pressureBurden residual offset lambdaMin : Real}
    (htensor :
      tensorAbsorptionOffsetFamilyTarget
        γ coerciveBudget pressureBurden residual offset)
    (hell :
      effectiveMetricEllipticityTarget lambdaMin) :
    tensorAbsorptionEllipticitySurvivalTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin := by
  exact ⟨htensor, hell⟩

/--
Iter-4 exact discriminator: tensor absorption is now the leading smooth
route-5 survivor, but only under a genuine ellipticity bound.
-/
def route5TensorAbsorptionNextDiscriminator
    (γ coerciveBudget pressureBurden residual offset lambdaMin : Real) : Prop :=
  tensorAbsorptionEllipticitySurvivalTarget
    γ coerciveBudget pressureBurden residual offset lambdaMin

end ZtareProofs
