/-
Paper 8: Case 4 benchmark — formally verified

Replaces the Python assertions in paper 8 Appendix A Case 4 with
machine-checked equalities. Uses concrete observation maps over a
two-element hidden state space.

Verified:
  D_base_kernel           = 1   (kernel-pair obstruction)
  D_conservative_kernel   = 1   (conservative alias preserves obstruction)
  D_nonconservative_kernel = 0  (state-revealing observable resolves it)
  Δ_conservative           = 0
  Δ_nonconservative        = -1
  Z_conservative_only      = 1
  Z_with_nonconservative   = 0
-/

import Mathlib.Tactic
import ZtareProofs.consciousness_conservative_invariance

namespace ZtareProofs.Paper8.Case4

/-- Hidden state space: two states `a` and `b`. -/
inductive H : Type
  | a : H
  | b : H
  deriving DecidableEq

open H

/-- Target map: `a ↦ 0`, `b ↦ 1`. -/
def θ : H → Nat
  | a => 0
  | b => 1

/-- Base observable: both states map to `"same"` — kernel pair. -/
def obs_base : H → String
  | _ => "same"

/-- Conservative alias: adds a definitional duplicate of the same observable. -/
def obs_conservative : H → String × String
  | h => (obs_base h, obs_base h)

/-- Non-conservative observable: distinguishes the two hidden states. -/
def obs_nonconservative : H → String × String
  | a => ("same", "reveal_a")
  | b => ("same", "reveal_b")

/-- Descent obstruction flag for the two-state case: 1 iff `obs a = obs b`
    and `θ a ≠ θ b`. -/
def D {O : Type} [DecidableEq O] (obs : H → O) : Nat :=
  if obs a = obs b ∧ θ a ≠ θ b then 1 else 0

theorem D_base_kernel : D obs_base = 1 := by
  unfold D
  simp [obs_base, θ]

theorem D_conservative_kernel : D obs_conservative = 1 := by
  unfold D
  simp [obs_conservative, obs_base, θ]

theorem D_nonconservative_kernel : D obs_nonconservative = 0 := by
  unfold D
  simp [obs_nonconservative]

/-- Conservative expansion does not overturn the obstruction. -/
theorem delta_D_conservative :
    (D obs_conservative : Int) - (D obs_base : Int) = 0 := by
  rw [D_base_kernel, D_conservative_kernel]; decide

/-- Non-conservative expansion overturns the obstruction by exactly one. -/
theorem delta_D_nonconservative :
    (D obs_nonconservative : Int) - (D obs_base : Int) = -1 := by
  rw [D_base_kernel, D_nonconservative_kernel]; decide

/-- `Z = min over admissible revisions`: if only conservative revisions are
    admissible, Z = 1 (obstruction necessary). -/
theorem Z_conservative_only :
    min (D obs_base) (D obs_conservative) = 1 := by
  rw [D_base_kernel, D_conservative_kernel]; decide

/-- If a non-conservative state-revealing revision is admissible,
    Z = 0 (obstruction contingent). -/
theorem Z_with_nonconservative :
    min (min (D obs_base) (D obs_conservative)) (D obs_nonconservative) = 0 := by
  rw [D_base_kernel, D_conservative_kernel, D_nonconservative_kernel]; decide

end ZtareProofs.Paper8.Case4
