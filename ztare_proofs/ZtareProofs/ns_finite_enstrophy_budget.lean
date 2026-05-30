import Mathlib.Topology.Algebra.InfiniteSum.Real
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import ZtareProofs.ns_h1_trace_controls_boundary_jump

/-!
# `FiniteEnstrophyBudget` — total trace-jump budget is summable (tick482)

Per the operator's traversal: Leray-Hopf gives `∫_K |∇u|² < ∞`, and
if bridge regions have bounded overlap, then total jump-energy
`Σ_Q radius_Q · jump_Q²` is finite.

Composes tick481 (per-pair trace bound) + summability of bridge
integrals (from finite enstrophy).
-/

namespace ZtareProofs.NSFiniteEnstrophyBudget

open ZtareProofs.NSH1TraceControlsBoundaryJump

/--
**`FiniteEnstrophyBudget`**: finite total enstrophy + bounded overlap
of bridge regions ⇒ summable total jump-energy.
-/
structure FiniteEnstrophyBudget where
  trace : H1TraceControlsBoundaryJump
  /-- Total enstrophy bound: `∫_K |∇u|² ≤ E_K < ∞`. -/
  E_K : ℝ
  E_K_pos : 0 < E_K
  /-- Bridge overlap multiplicity (each bridge region overlaps at most this many others). -/
  M_overlap : ℝ
  M_overlap_pos : 0 < M_overlap
  /-- Standard Leray-Hopf identity: sum of bridge gradient integrals
  ≤ M_overlap · total enstrophy. -/
  bridge_partial_sum_bound : ∀ N : ℕ,
      (∑ n ∈ Finset.range N, trace.bridgeGradInt n) ≤ M_overlap * E_K

/--
**Tick482 main theorem: total trace-jump energy is bounded.**

Composes tick481's per-pair trace bound with the finite enstrophy
budget to give `Σ_n radius_n · jump_n² ≤ C_tr · M_overlap · E_K`.
-/
theorem traceJumpEnergy_total_bound
    (h : FiniteEnstrophyBudget) (N : ℕ) :
    (∑ n ∈ Finset.range N, h.trace.radius n * (h.trace.jump n)^2)
      ≤ h.trace.C_tr * h.M_overlap * h.E_K := by
  have hpartial := traceJumpEnergy_partial_sum_le h.trace N
  have hbridge := h.bridge_partial_sum_bound N
  have hCtr_nonneg : 0 ≤ h.trace.C_tr := le_of_lt h.trace.C_tr_pos
  have hmul_le : h.trace.C_tr * (∑ n ∈ Finset.range N, h.trace.bridgeGradInt n)
                ≤ h.trace.C_tr * (h.M_overlap * h.E_K) :=
    mul_le_mul_of_nonneg_left hbridge hCtr_nonneg
  calc (∑ n ∈ Finset.range N, h.trace.radius n * (h.trace.jump n)^2)
      ≤ h.trace.C_tr * (∑ n ∈ Finset.range N, h.trace.bridgeGradInt n) := hpartial
    _ ≤ h.trace.C_tr * (h.M_overlap * h.E_K) := hmul_le
    _ = h.trace.C_tr * h.M_overlap * h.E_K := by ring

/-- **Summability of total trace-jump energy.** -/
theorem traceJumpEnergy_summable (h : FiniteEnstrophyBudget) :
    Summable (fun n : ℕ => h.trace.radius n * (h.trace.jump n)^2) := by
  apply summable_of_sum_range_le (c := h.trace.C_tr * h.M_overlap * h.E_K)
  · intro n; exact traceJumpEnergy_nonneg h.trace n
  · intro N; exact traceJumpEnergy_total_bound h N

end ZtareProofs.NSFiniteEnstrophyBudget
