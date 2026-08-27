import Mathlib.GroupTheory.SemidirectProduct
import Mathlib.Data.Nat.Choose.Sum
import Mathlib.Tactic

/-!
# Orbit extraction from a semidirect factorization

In a semidirect product `N ⋊ G`, a factorization of a pure `N` residual
with the pure `G` factor on the left has a forced orientation.  Projection
to `G` makes that factor the inverse of the `G` coordinate of the other
factor; projection to `N` then gives the corresponding orbit equation.

Putting the pure `G` factor on the right produces a different law: it does
not transport the `N` coordinate.  Keeping both statements in one owner
prevents a source/target composition convention from being changed silently.
-/

namespace FormalSemidirectFactorizationOrbit

open SemidirectProduct

variable {N G : Type*} [Group N] [Group G]

/-- A target factor on the left is forced to be the inverse source actor,
and its action transports the source module coordinate to the residual. -/
theorem targetLeft_factorization_forces_inverse_orbit
    (action : G →* MulAut N) (residual sourceModule : N)
    (targetActor sourceActor : G)
    (factorization :
      (SemidirectProduct.inl residual : N ⋊[action] G) =
        SemidirectProduct.inr targetActor *
          (⟨sourceModule, sourceActor⟩ : N ⋊[action] G)) :
    targetActor = sourceActor⁻¹ ∧
      residual = action sourceActor⁻¹ sourceModule := by
  have rightCoordinate := congrArg SemidirectProduct.right factorization
  have hproduct : targetActor * sourceActor = 1 := by
    simpa using rightCoordinate.symm
  have htarget : targetActor = sourceActor⁻¹ := by
    calc
      targetActor = targetActor * 1 := by simp
      _ = targetActor * (sourceActor * sourceActor⁻¹) := by simp
      _ = (targetActor * sourceActor) * sourceActor⁻¹ := by
        rw [mul_assoc]
      _ = sourceActor⁻¹ := by rw [hproduct, one_mul]
  have leftCoordinate := congrArg SemidirectProduct.left factorization
  have horbit : residual = action targetActor sourceModule := by
    simpa using leftCoordinate
  exact ⟨htarget, by simpa [htarget] using horbit⟩

/-- Orientation negative control: a pure actor on the right does not act on
the module coordinate already carried by the left source factor. -/
theorem targetRight_factorization_forces_untransported_module
    (action : G →* MulAut N) (residual sourceModule : N)
    (sourceActor targetActor : G)
    (factorization :
      (SemidirectProduct.inl residual : N ⋊[action] G) =
        (⟨sourceModule, sourceActor⟩ : N ⋊[action] G) *
          SemidirectProduct.inr targetActor) :
    targetActor = sourceActor⁻¹ ∧ residual = sourceModule := by
  have rightCoordinate := congrArg SemidirectProduct.right factorization
  have hproduct : sourceActor * targetActor = 1 := by
    simpa using rightCoordinate.symm
  have htarget : targetActor = sourceActor⁻¹ := by
    calc
      targetActor = 1 * targetActor := by simp
      _ = (sourceActor⁻¹ * sourceActor) * targetActor := by simp
      _ = sourceActor⁻¹ * (sourceActor * targetActor) := by
        rw [mul_assoc]
      _ = sourceActor⁻¹ := by rw [hproduct, mul_one]
  have leftCoordinate := congrArg SemidirectProduct.left factorization
  have hmodule : residual = sourceModule := by
    simpa using leftCoordinate
  exact ⟨htarget, hmodule⟩

/-- Aggregated orientation-typed semidirect orbit certificate. -/
theorem semidirect_factorization_orbit_terminal_certificate :
    (∀ (action : G →* MulAut N) (residual sourceModule : N)
      (targetActor sourceActor : G),
      (SemidirectProduct.inl residual : N ⋊[action] G) =
          SemidirectProduct.inr targetActor *
            (⟨sourceModule, sourceActor⟩ : N ⋊[action] G) →
      targetActor = sourceActor⁻¹ ∧
        residual = action sourceActor⁻¹ sourceModule) ∧
    (∀ (action : G →* MulAut N) (residual sourceModule : N)
      (sourceActor targetActor : G),
      (SemidirectProduct.inl residual : N ⋊[action] G) =
          (⟨sourceModule, sourceActor⟩ : N ⋊[action] G) *
            SemidirectProduct.inr targetActor →
      targetActor = sourceActor⁻¹ ∧ residual = sourceModule) := by
  exact ⟨targetLeft_factorization_forces_inverse_orbit,
    targetRight_factorization_forces_untransported_module⟩

/-! ## Formal semidirect exponential coefficients -/

section RationalLinear

open Finset

/-- Scalar convolution produced by multiplying the inverse actor exponential
on the left of the source semidirect exponential. -/
theorem targetLeftDuhamel_scalar_convolution (depth : ℕ) :
    (∑ actorDepth ∈ range (depth + 1),
        (-1 : ℚ) ^ actorDepth /
          ((actorDepth.factorial : ℚ) *
            ((depth - actorDepth + 1).factorial : ℚ))) =
      (-1 : ℚ) ^ depth / ((depth + 1).factorial : ℚ) := by
  have termIdentity : ∀ actorDepth ∈ range (depth + 1),
      (-1 : ℚ) ^ actorDepth /
          ((actorDepth.factorial : ℚ) *
            ((depth - actorDepth + 1).factorial : ℚ)) =
        ((-1 : ℚ) ^ actorDepth *
            ((depth + 1).choose actorDepth : ℚ)) /
          ((depth + 1).factorial : ℚ) := by
    intro actorDepth hactorDepth
    have hleDepth : actorDepth ≤ depth := by
      simpa using hactorDepth
    have hle : actorDepth ≤ depth + 1 :=
      hleDepth.trans (Nat.le_succ depth)
    have hsub : depth + 1 - actorDepth = depth - actorDepth + 1 := by
      omega
    have hfactorial :=
      Nat.choose_mul_factorial_mul_factorial hle
    rw [hsub] at hfactorial
    have hfactorialQ :
        ((depth + 1).choose actorDepth : ℚ) *
              (actorDepth.factorial : ℚ) *
              ((depth - actorDepth + 1).factorial : ℚ) =
            ((depth + 1).factorial : ℚ) := by
      exact_mod_cast hfactorial
    have hleft : (actorDepth.factorial : ℚ) ≠ 0 := by positivity
    have hright :
        ((depth - actorDepth + 1).factorial : ℚ) ≠ 0 := by
      positivity
    have htotal : ((depth + 1).factorial : ℚ) ≠ 0 := by positivity
    field_simp
    nlinarith
  rw [sum_congr rfl termIdentity]
  rw [← sum_div]
  have alternatingInteger :=
    Int.alternating_sum_range_choose_eq_choose
      (n := depth) (m := depth)
  have alternatingInteger' :
      (∑ actorDepth ∈ range (depth + 1),
          (-1 : ℤ) ^ actorDepth *
            ((depth + 1).choose actorDepth : ℤ)) =
        (-1 : ℤ) ^ depth := by
    simpa using alternatingInteger
  have alternatingRational :
      (∑ actorDepth ∈ range (depth + 1),
          (-1 : ℚ) ^ actorDepth *
            ((depth + 1).choose actorDepth : ℚ)) =
        (-1 : ℚ) ^ depth := by
    exact_mod_cast alternatingInteger'
  rw [alternatingRational]

variable {M : Type*} [AddCommGroup M] [Module ℚ M]

/-- The depth coefficient in the module coordinate of `exp(D,J)`. -/
def sourceSemidirectExponentialCoefficient
    (action : Module.End ℚ M) (module : M) (depth : ℕ) : M :=
  (1 / ((depth + 1).factorial : ℚ)) •
    (fun value => action value)^[depth] module

/-- The total-depth convolution obtained by applying the inverse actor
exponential on the left of the source group-module coordinate. -/
def targetLeftSemidirectExponentialCoefficient
    (action : Module.End ℚ M) (module : M) (depth : ℕ) : M :=
  ∑ actorDepth ∈ range (depth + 1),
    ((-1 : ℚ) ^ actorDepth /
        (actorDepth.factorial : ℚ)) •
      (fun value => action value)^[actorDepth]
        (sourceSemidirectExponentialCoefficient action module
          (depth - actorDepth))

/-- Iterating a rational-linear action preserves scalar multiplication. -/
theorem iterate_linear_smul
    (action : Module.End ℚ M) (depth : ℕ) (scalar : ℚ) (value : M) :
    (fun item => action item)^[depth] (scalar • value) =
      scalar • (fun item => action item)^[depth] value := by
  induction depth generalizing value with
  | zero => rfl
  | succ depth inductionHypothesis =>
      rw [Function.iterate_succ_apply, Function.iterate_succ_apply,
        action.map_smul, inductionHypothesis]

/-- Each target-left convolution summand has one common action iterate; only
its factorial scalar depends on the split of total depth. -/
theorem targetLeftSemidirectExponential_summand
    (action : Module.End ℚ M) (module : M) (depth actorDepth : ℕ)
    (hactorDepth : actorDepth ∈ range (depth + 1)) :
    ((-1 : ℚ) ^ actorDepth /
        (actorDepth.factorial : ℚ)) •
      (fun value => action value)^[actorDepth]
        (sourceSemidirectExponentialCoefficient action module
          (depth - actorDepth)) =
      ((-1 : ℚ) ^ actorDepth /
          ((actorDepth.factorial : ℚ) *
            ((depth - actorDepth + 1).factorial : ℚ))) •
        (fun value => action value)^[depth] module := by
  have hle : actorDepth ≤ depth := by
    simpa using hactorDepth
  rw [sourceSemidirectExponentialCoefficient, iterate_linear_smul,
    smul_smul]
  rw [← Function.iterate_add_apply]
  rw [Nat.add_sub_of_le hle]
  congr 1
  have hfirst : (actorDepth.factorial : ℚ) ≠ 0 := by positivity
  have hsecond :
      ((depth - actorDepth + 1).factorial : ℚ) ≠ 0 := by
    positivity
  field_simp

/-- Exact target-left Duhamel coefficient.  The inverse actor changes the
source coefficient only by `(-1)^depth`; the `(depth+1)!` shift is retained. -/
theorem targetLeftSemidirectExponentialCoefficient_eq
    (action : Module.End ℚ M) (module : M) (depth : ℕ) :
    targetLeftSemidirectExponentialCoefficient action module depth =
      ((-1 : ℚ) ^ depth / ((depth + 1).factorial : ℚ)) •
        (fun value => action value)^[depth] module := by
  rw [targetLeftSemidirectExponentialCoefficient]
  calc
    (∑ actorDepth ∈ range (depth + 1),
        ((-1 : ℚ) ^ actorDepth /
            (actorDepth.factorial : ℚ)) •
          (fun value => action value)^[actorDepth]
            (sourceSemidirectExponentialCoefficient action module
              (depth - actorDepth))) =
        ∑ actorDepth ∈ range (depth + 1),
          ((-1 : ℚ) ^ actorDepth /
              ((actorDepth.factorial : ℚ) *
                ((depth - actorDepth + 1).factorial : ℚ))) •
            (fun value => action value)^[depth] module := by
      apply sum_congr rfl
      intro actorDepth hactorDepth
      exact targetLeftSemidirectExponential_summand
        action module depth actorDepth hactorDepth
    _ = (∑ actorDepth ∈ range (depth + 1),
          (-1 : ℚ) ^ actorDepth /
            ((actorDepth.factorial : ℚ) *
              ((depth - actorDepth + 1).factorial : ℚ))) •
          (fun value => action value)^[depth] module := by
      rw [Finset.sum_smul]
    _ = ((-1 : ℚ) ^ depth /
          ((depth + 1).factorial : ℚ)) •
        (fun value => action value)^[depth] module := by
      rw [targetLeftDuhamel_scalar_convolution]

/-- Universal coefficient certificate for the source semidirect exponential
and its target-left inverse-actor transfer. -/
theorem semidirect_exponential_targetLeft_terminal_certificate :
    (∀ (action : Module.End ℚ M) (module : M) (depth : ℕ),
      sourceSemidirectExponentialCoefficient action module depth =
        (1 / ((depth + 1).factorial : ℚ)) •
          (fun value => action value)^[depth] module) ∧
    (∀ (action : Module.End ℚ M) (module : M) (depth : ℕ),
      targetLeftSemidirectExponentialCoefficient action module depth =
        ((-1 : ℚ) ^ depth / ((depth + 1).factorial : ℚ)) •
          (fun value => action value)^[depth] module) := by
  exact ⟨fun _ _ _ => rfl,
    targetLeftSemidirectExponentialCoefficient_eq⟩

end RationalLinear

end FormalSemidirectFactorizationOrbit
