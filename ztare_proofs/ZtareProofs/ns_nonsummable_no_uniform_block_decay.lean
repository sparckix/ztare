import ZtareProofs.ns_dini_sequence_block_decay_contradiction
import ZtareProofs.ns_residue_class_lift_summable

/-!
# Tick477: nonsummable ⇒ no uniform block decay (full pincer Part 1)

Composes tick475 (block subsequence summable per residue) +
tick476 (residue-class lift to full summability) + `summable_nat_add_iff`
(shift) to derive the contradiction with `¬ Summable A`.

This completes **Part 1 of the Dini→Perfect pincer**: nonsummable
flat cascade has no uniform geometric block decay.  Combined with
tick473 (perfect-flat cascade impossible under regularity), the
remaining open content is just the PDE compactness extraction.
-/

namespace ZtareProofs.NSNonsummableNoUniformBlockDecay

open ZtareProofs.NSDiniSequenceBlockDecayContradiction
open ZtareProofs.NSResidueClassLiftSummable

/--
**Tick477 main theorem.**

For nonneg `A : ℕ → ℝ`, if `¬ Summable A`, then no uniform geometric
block decay can hold: there is no `N₀, L > 0, θ ∈ [0,1)` such that
`A (n + L) ≤ θ · A n` for all `n ≥ N₀`.

Proof: assume block decay.  For each residue `r ∈ Fin L`, the
shifted sequence `k ↦ A (N₀ + r + k · L)` is summable by tick475
(applied with `N₀ + r` as the starting index).  Lift via tick476
to get `Summable (fun n => A (N₀ + n))`.  Apply `summable_nat_add_iff`
to get `Summable A`.  Contradicts `¬ Summable A`.
-/
theorem nonsummable_implies_no_uniform_block_decay
    (A : ℕ → ℝ) (hA_nonneg : ∀ n, 0 ≤ A n)
    (h_not_summable : ¬ Summable A)
    (L : ℕ) (hL_pos : 0 < L)
    (θ : ℝ) (hθ_nonneg : 0 ≤ θ) (hθ_lt_one : θ < 1) :
    ¬ ∃ N₀ : ℕ, ∀ n, N₀ ≤ n → A (n + L) ≤ θ * A n := by
  rintro ⟨N₀, h_decay⟩
  -- Step 1: For each r ∈ Fin L, apply tick475 with N₀' = N₀ + r.
  -- The block-decay hypothesis at N₀' = N₀ + r: ∀ n ≥ N₀ + r, A (n + L) ≤ θ · A n.
  -- This follows from h_decay since n ≥ N₀ + r ≥ N₀.
  have h_residue_summable :
      ∀ r : Fin L,
      Summable (fun k : ℕ => A ((N₀ + r.val) + k * L)) := by
    intro r
    have h_decay_shifted : ∀ n, (N₀ + r.val) ≤ n → A (n + L) ≤ θ * A n := by
      intro n hn
      have : N₀ ≤ n := le_trans (Nat.le_add_right N₀ r.val) hn
      exact h_decay n this
    exact block_subsequence_summable_under_decay A hA_nonneg (N₀ + r.val) L
      θ hθ_nonneg hθ_lt_one h_decay_shifted
  -- Step 2: Rearrange the index. We have Summable (k ↦ A (N₀ + r + k · L)).
  -- We need Summable (k ↦ f (k · L + r.val)) where f n = A (N₀ + n).
  -- (N₀ + r) + k · L = N₀ + (r + k · L) = N₀ + (k · L + r). ✓
  have h_residue_shifted :
      ∀ r : Fin L,
      Summable (fun k : ℕ => (fun n : ℕ => A (N₀ + n)) (k * L + r.val)) := by
    intro r
    have h := h_residue_summable r
    -- A ((N₀ + r) + k · L) = A (N₀ + (k · L + r))  via natural-number arithmetic
    have heq : (fun k : ℕ => A ((N₀ + r.val) + k * L))
             = (fun k : ℕ => A (N₀ + (k * L + r.val))) := by
      funext k; congr 1; ring
    rw [heq] at h
    exact h
  -- Step 3: apply tick476 (residue_class_lift_summable) to f := fun n => A (N₀ + n).
  have h_shifted_summable : Summable (fun n : ℕ => A (N₀ + n)) := by
    apply residue_class_lift_summable (fun n => A (N₀ + n))
      (fun n => hA_nonneg _) L hL_pos
    exact h_residue_shifted
  -- Step 4: lift to Summable A via summable_nat_add_iff (with shift N₀).
  -- summable_nat_add_iff k : Summable (fun n => f (n + k)) ↔ Summable f
  have h_shifted_summable' : Summable (fun n : ℕ => A (n + N₀)) := by
    have heq : (fun n : ℕ => A (n + N₀)) = (fun n : ℕ => A (N₀ + n)) := by
      funext n; rw [Nat.add_comm]
    rw [heq]; exact h_shifted_summable
  have h_summable_A : Summable A :=
    (summable_nat_add_iff (f := A) N₀).mp h_shifted_summable'
  -- Step 5: contradict h_not_summable.
  exact h_not_summable h_summable_A

end ZtareProofs.NSNonsummableNoUniformBlockDecay
