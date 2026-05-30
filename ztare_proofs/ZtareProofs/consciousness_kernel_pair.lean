/-
Paper 8: Kernel-pair non-factorization lemma (Lemma 1)

Statement:
  Given an observation map obs : H → O and a target map θ : H → Θ,
  if there exist a b : H with obs a = obs b but θ a ≠ θ b,
  then no function f : O → Θ satisfies θ = f ∘ obs.

This is the formal version of the §4 kernel-pair argument: necessary
non-identification holds when two hidden states share an observable
signature but diverge on the target.
-/

import Mathlib.Tactic

namespace ZtareProofs.Paper8

universe u v w

/-- Kernel-pair non-factorization: if two hidden states `a` and `b` agree
    under the observation map but disagree on the target, then no function
    on the observation space can recover the target from observations. -/
theorem kernel_pair_no_factor
    {H : Type u} {O : Type v} {Θ : Type w}
    (obs : H → O) (θ : H → Θ)
    (a b : H) (h_obs : obs a = obs b) (h_theta : θ a ≠ θ b) :
    ¬ ∃ f : O → Θ, θ = f ∘ obs := by
  intro ⟨f, hf⟩
  apply h_theta
  have ha : θ a = f (obs a) := congr_fun hf a
  have hb : θ b = f (obs b) := congr_fun hf b
  rw [ha, hb, h_obs]

/-- Contrapositive: if θ factors through obs, then obs separates target classes. -/
theorem factor_implies_separation
    {H : Type u} {O : Type v} {Θ : Type w}
    (obs : H → O) (θ : H → Θ)
    (hf : ∃ f : O → Θ, θ = f ∘ obs) :
    ∀ a b : H, obs a = obs b → θ a = θ b := by
  intro a b h_obs
  obtain ⟨f, hfact⟩ := hf
  have ha : θ a = f (obs a) := congr_fun hfact a
  have hb : θ b = f (obs b) := congr_fun hfact b
  rw [ha, hb, h_obs]

end ZtareProofs.Paper8
