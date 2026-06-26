/-
Paper 8: Conservative Invariance (Proposition, finite-alias case)

Statement:
  An observation map `obs : H → O` admits a conservative expansion
  `augmentObs : H → O × O'` whenever `O'` is a function of `O`
  (alias condition). In that case any kernel pair under `obs` remains
  a kernel pair under `augmentObs`: the descent obstruction is preserved.

This is the operationally checkable case of the Proposition (Conservative
Invariance) in paper 8 §5.3. The full category-theoretic statement
(Morita-equivalent presentations preserve effective descent) lives one
level of abstraction up; this combinatorial case suffices to verify the
§A.4 benchmark and to demonstrate that the proposition is non-vacuous
in finite settings.
-/

import Mathlib.Tactic
import ZtareProofs.consciousness_kernel_pair

namespace ZtareProofs.Paper8

universe u v v' w

/-- A conservative alias of an observation map: `O'` is a function of `O`. -/
structure ConservativeAlias
    {H : Type u} {O : Type v} (obs : H → O) (O' : Type v') where
  alias_fn : O → O'

/-- The augmented observation map under a conservative alias. -/
def augmentObs
    {H : Type u} {O : Type v} {O' : Type v'}
    (obs : H → O) (a : ConservativeAlias obs O') :
    H → O × O' :=
  fun h => (obs h, a.alias_fn (obs h))

/-- Conservative expansion preserves observable equality. -/
theorem conservative_preserves_equality
    {H : Type u} {O : Type v} {O' : Type v'}
    (obs : H → O) (a : ConservativeAlias obs O') :
    ∀ x y : H, obs x = obs y → augmentObs obs a x = augmentObs obs a y := by
  intro x y h_obs
  unfold augmentObs
  rw [h_obs]

/-- Conservative invariance for the kernel-pair flag: a kernel pair under
    `obs` remains a kernel pair under `augmentObs obs a`. The descent
    obstruction count is therefore preserved under conservative expansion. -/
theorem conservative_invariance_finite_alias
    {H : Type u} {O : Type v} {O' : Type v'} {Θ : Type w}
    (obs : H → O) (a : ConservativeAlias obs O') (_θ : H → Θ)
    (x y : H) (h_obs : obs x = obs y) (h_theta : _θ x ≠ _θ y) :
    augmentObs obs a x = augmentObs obs a y ∧ _θ x ≠ _θ y :=
  ⟨conservative_preserves_equality obs a x y h_obs, h_theta⟩

/-- A non-conservative observable adds new structure: `new_obs` is NOT a
    function of `obs` (i.e., some hidden states share an `obs` value but
    differ on `new_obs`). The kernel-pair obstruction may resolve. -/
def nonConservativeResolves
    {H : Type u} {O : Type v} {O_new : Type v'}
    (obs : H → O) (new_obs : H → O_new) (x y : H) : Prop :=
  obs x = obs y ∧ new_obs x ≠ new_obs y

/-- A non-conservative observable that distinguishes a kernel pair makes the
    augmented map `(obs, new_obs)` separate them — the obstruction resolves. -/
theorem nonconservative_can_resolve
    {H : Type u} {O : Type v} {O_new : Type v'}
    (obs : H → O) (new_obs : H → O_new)
    (x y : H) (h : nonConservativeResolves obs new_obs x y) :
    (obs x, new_obs x) ≠ (obs y, new_obs y) := by
  obtain ⟨_, h_neq⟩ := h
  intro h_eq
  apply h_neq
  exact congr_arg Prod.snd h_eq

end ZtareProofs.Paper8
