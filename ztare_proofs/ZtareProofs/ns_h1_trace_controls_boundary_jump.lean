import Mathlib.Topology.Algebra.InfiniteSum.Real
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity

/-!
# `H1TraceControlsBoundaryJump` — codified (tick481)

Per the operator's analytic traversal (2026-05-15):
> For adjacent flat children, Poincaré/trace gives
>   `r_Q · |mean_Q u − mean_Q' u|² ≤ C · ∫_{bridge(Q,Q')} |∇u|²`
> up to cutoff geometry constants.

This file ships the ℝ-valued structural form with composition.
-/

namespace ZtareProofs.NSH1TraceControlsBoundaryJump

/--
**`H1TraceControlsBoundaryJump`** — H¹ trace controls per-pair flat
boundary-jump energy by the local gradient integral.
-/
structure H1TraceControlsBoundaryJump where
  /-- Universal trace constant (depends on geometry; `> 0`). -/
  C_tr : ℝ
  C_tr_pos : 0 < C_tr
  /-- Per-pair radius. -/
  radius : ℕ → ℝ
  radius_nonneg : ∀ n : ℕ, 0 ≤ radius n
  /-- Per-pair boundary jump magnitude. -/
  jump : ℕ → ℝ
  jump_nonneg : ∀ n : ℕ, 0 ≤ jump n
  /-- Per-pair bridge gradient integral. -/
  bridgeGradInt : ℕ → ℝ
  bridgeGradInt_nonneg : ∀ n : ℕ, 0 ≤ bridgeGradInt n
  /-- **Trace inequality**: `r_n · jump_n² ≤ C · bridgeGradInt_n`. -/
  trace_bound : ∀ n : ℕ, radius n * (jump n)^2 ≤ C_tr * bridgeGradInt n

/-- **Per-pair jump energy bound is non-negative.** -/
lemma traceJumpEnergy_nonneg (h : H1TraceControlsBoundaryJump) (n : ℕ) :
    0 ≤ h.radius n * (h.jump n)^2 := by
  apply mul_nonneg (h.radius_nonneg n)
  exact sq_nonneg _

/-- **Bridge gradient integral times C_tr is non-negative.** -/
lemma C_tr_bridgeGradInt_nonneg (h : H1TraceControlsBoundaryJump) (n : ℕ) :
    0 ≤ h.C_tr * h.bridgeGradInt n :=
  mul_nonneg (le_of_lt h.C_tr_pos) (h.bridgeGradInt_nonneg n)

/-- **Partial-sum trace bound**: sum of per-pair jump-energy ≤ C times sum of bridge gradients. -/
theorem traceJumpEnergy_partial_sum_le
    (h : H1TraceControlsBoundaryJump) (N : ℕ) :
    (∑ n ∈ Finset.range N, h.radius n * (h.jump n)^2)
      ≤ h.C_tr * (∑ n ∈ Finset.range N, h.bridgeGradInt n) := by
  rw [Finset.mul_sum]
  exact Finset.sum_le_sum (fun n _ => h.trace_bound n)

end ZtareProofs.NSH1TraceControlsBoundaryJump
