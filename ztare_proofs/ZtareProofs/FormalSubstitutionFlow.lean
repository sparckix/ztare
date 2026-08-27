import Mathlib.RingTheory.PowerSeries.Substitution
import Mathlib.Tactic

/-!
One-parameter formal substitution flows and exact time rescaling.

The governing object is the full additive-time action, not an isolated
time-one germ.  Its composition orientation is explicit:

`endpoint (s + t) = (endpoint s).subst (endpoint t)`.

The terminal theorem proves the algebraic part of the proportional-generator
reduction.  Once the second selected endpoint has been identified with time
`c` in the same flow, its composition with time one is time one in the
`(1+c)`-rescaled flow.  Analytic ODE uniqueness and continuation-branch
identification are deliberately outside this formal-semigroup theorem.
-/

namespace FormalSubstitutionFlow

open PowerSeries

variable {k : Type*} [Field k]

/-- An additive one-parameter action by zero-constant formal substitutions.

The order in `add_time` says that time `t` is applied first and time `s`
second. -/
structure SubstitutionFlow (k : Type*) [Field k] where
  endpoint : k → k⟦X⟧
  constantCoeff_endpoint : ∀ t : k, constantCoeff (endpoint t) = 0
  endpoint_zero : endpoint 0 = X
  add_time : ∀ s t : k,
    endpoint (s + t) = (endpoint s).subst (endpoint t)

theorem SubstitutionFlow.hasSubst (flow : SubstitutionFlow k) (t : k) :
    HasSubst (flow.endpoint t) :=
  HasSubst.of_constantCoeff_zero' (flow.constantCoeff_endpoint t)

/-- Scalar reparameterization `t ↦ c*t` of a substitution flow. -/
noncomputable def SubstitutionFlow.reparam
    (flow : SubstitutionFlow k) (c : k) : SubstitutionFlow k where
  endpoint t := flow.endpoint (c * t)
  constantCoeff_endpoint t := flow.constantCoeff_endpoint (c * t)
  endpoint_zero := by simp [flow.endpoint_zero]
  add_time s t := by
    rw [mul_add, flow.add_time]

@[simp]
theorem SubstitutionFlow.reparam_endpoint
    (flow : SubstitutionFlow k) (c t : k) :
    (flow.reparam c).endpoint t = flow.endpoint (c * t) :=
  rfl

@[simp]
theorem SubstitutionFlow.reparam_zero
    (flow : SubstitutionFlow k) :
    flow.reparam 0 =
      { endpoint := fun _ => X
        constantCoeff_endpoint := fun _ => by simp
        endpoint_zero := rfl
        add_time := fun _ _ => by simp } := by
  cases flow
  simp only [SubstitutionFlow.reparam]
  congr 1
  funext t
  simp_all

@[simp]
theorem SubstitutionFlow.reparam_one
    (flow : SubstitutionFlow k) :
    flow.reparam 1 = flow := by
  cases flow
  simp [SubstitutionFlow.reparam]

theorem SubstitutionFlow.reparam_mul
    (flow : SubstitutionFlow k) (a b : k) :
    (flow.reparam a).reparam b = flow.reparam (a * b) := by
  cases flow
  simp [SubstitutionFlow.reparam, mul_assoc]

/-- Time-one of the `a`-rescaled flow is time `a` of the original flow. -/
theorem SubstitutionFlow.reparam_time_one
    (flow : SubstitutionFlow k) (a : k) :
    (flow.reparam a).endpoint 1 = flow.endpoint a := by
  simp

/-- The two endpoint substitutions commute because they belong to one
additive-time action. -/
theorem SubstitutionFlow.endpoints_commute
    (flow : SubstitutionFlow k) (s t : k) :
    (flow.endpoint s).subst (flow.endpoint t) =
      (flow.endpoint t).subst (flow.endpoint s) := by
  rw [← flow.add_time s t, ← flow.add_time t s, add_comm]

/-- Composition at times one and `c` is time one of the `(1+c)`-rescaled
flow.  This is the exact formal-semigroup mechanism behind proportional
autonomous-flow reduction. -/
theorem proportional_composition_as_reparameterized_time_one
    (flow : SubstitutionFlow k) (c : k) :
    (flow.endpoint 1).subst (flow.endpoint c) =
      (flow.reparam (1 + c)).endpoint 1 := by
  rw [← flow.add_time 1 c]
  simp

/-- The opposite displayed composition orientation has the same endpoint. -/
theorem proportional_composition_as_reparameterized_time_one_rev
    (flow : SubstitutionFlow k) (c : k) :
    (flow.endpoint c).subst (flow.endpoint 1) =
      (flow.reparam (1 + c)).endpoint 1 := by
  rw [flow.endpoints_commute c 1]
  exact proportional_composition_as_reparameterized_time_one flow c

/-- Aggregated proposition used by formal-coverage adapters.  It exposes
both composition orientations and the exact scalar reparameterization law;
it does not identify an independently continued proportional-generator
branch with `flow.endpoint c`. -/
theorem proportional_substitution_flow_terminal_certificate :
    (∀ (flow : SubstitutionFlow k) (a : k),
      (flow.reparam a).endpoint 1 = flow.endpoint a) ∧
    (∀ (flow : SubstitutionFlow k) (c : k),
      (flow.endpoint 1).subst (flow.endpoint c) =
        (flow.reparam (1 + c)).endpoint 1) ∧
    (∀ (flow : SubstitutionFlow k) (c : k),
      (flow.endpoint c).subst (flow.endpoint 1) =
        (flow.reparam (1 + c)).endpoint 1) := by
  exact ⟨SubstitutionFlow.reparam_time_one,
    proportional_composition_as_reparameterized_time_one,
    proportional_composition_as_reparameterized_time_one_rev⟩

end FormalSubstitutionFlow
