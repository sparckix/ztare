import Mathlib.Topology.Algebra.InfiniteSum.Real
import Mathlib.Topology.Algebra.InfiniteSum.NatInt
import Mathlib.Logic.Equiv.Defs
import Mathlib.Logic.Equiv.Fin.Basic
import Mathlib.Data.Fintype.Basic
import ZtareProofs.ns_dini_sequence_block_decay_contradiction

/-!
# Residue-class lift to full summability (tick476)

Continuing the pincer from tick475.  Lifts residue-class summabilities
to full summability via `summable_prod_of_nonneg` + Fintype trivial
summability + `Nat.divModEquiv` bijection.
-/

namespace ZtareProofs.NSResidueClassLiftSummable

open ZtareProofs.NSDiniSequenceBlockDecayContradiction

/--
**Residue-class lift to full summability.**

If `f : ℕ → ℝ` is nonneg and each residue class `k ↦ f (k · L + r)`
is summable, then `f` is summable.
-/
theorem residue_class_lift_summable
    (f : ℕ → ℝ) (hf_nonneg : ∀ n, 0 ≤ f n)
    (L : ℕ) (hL_pos : 0 < L)
    (h_residue : ∀ r : Fin L, Summable (fun k : ℕ => f (k * L + r.val))) :
    Summable f := by
  haveI : NeZero L := ⟨Nat.pos_iff_ne_zero.mp hL_pos⟩
  -- Step 1: build a Summable family on ℕ × Fin L.
  let g : ℕ × Fin L → ℝ := fun p => f (p.1 * L + p.2.val)
  have hg_nonneg : 0 ≤ g := fun _ => hf_nonneg _
  -- Step 2: Summable g via summable_prod_of_nonneg.
  -- summable_prod_of_nonneg gives:
  --   Summable f ↔ (∀ x, Summable (fun y ↦ f (x, y))) ∧ Summable (fun x ↦ ∑' y, f (x, y))
  -- but the FIRST argument enumerates over (α : Type) of f : α × β → ℝ.
  -- With α = ℕ, β = Fin L: condition 1 = ∀ k : ℕ, Summable over Fin L (fintype, trivial);
  -- condition 2 = Summable over ℕ of `fun k ↦ ∑_{r ∈ Fin L} f (k·L + r)`.
  -- Hmm — neither matches h_residue directly. Swap: α = Fin L, β = ℕ.
  -- But summable_prod_of_nonneg in Mathlib uses α × β shape.  Need to convert.
  --
  -- Alternative cleaner path: directly via Equiv.summable_iff with Nat.divModEquiv.
  -- Nat.divModEquiv L : ℕ ≃ ℕ × Fin L sends n ↦ (n / L, n % L).
  -- So f n = g (n / L, n % L) = g (Nat.divModEquiv L n).
  -- Hence Summable f ↔ Summable (g ∘ Nat.divModEquiv L) = Summable g (via Equiv.summable_iff).
  --
  -- Now Summable g on ℕ × Fin L: use summable_prod_of_nonneg with α = ℕ, β = Fin L.
  -- Condition (1): ∀ k : ℕ, Summable (fun r : Fin L ↦ g (k, r)) — trivial since Fin L is Fintype.
  -- Condition (2): Summable (fun k : ℕ ↦ ∑' r : Fin L, g (k, r)).
  --     = Summable (fun k : ℕ ↦ ∑_{r ∈ Finset.univ} g (k, r))  [Fin L finite]
  --     = Summable (fun k : ℕ ↦ ∑_{r ∈ Fin L} f (k · L + r.val))
  -- The inner sum is over the L residue values; by Finset.sum_le_sum from h_residue
  -- on each r, applied separately... actually for this we need that the SUM over
  -- finite r of summable-in-k functions is summable.  Standard: Σ_{r ∈ Fin L} (summable
  -- in k) = summable in k (since finite sum of summables is summable).
  have h_g_summable : Summable g := by
    rw [summable_prod_of_nonneg hg_nonneg]
    refine ⟨?_, ?_⟩
    · -- (1) ∀ k : ℕ, Summable (fun r : Fin L ↦ g (k, r)) — Fin L is Fintype, trivial.
      intro k
      exact (hasSum_fintype _).summable
    · -- (2) Summable (fun k ↦ ∑' r, g (k, r))
      -- = Summable (fun k ↦ ∑_{r ∈ Finset.univ} g (k, r))  [tsum on Fintype = Finset.sum]
      -- = Summable (fun k ↦ ∑_{r ∈ Fin L} f (k · L + r.val))
      -- Use: finite sum of summables is summable (Finset.summable_sum).
      have h_tsum_eq_finset_sum :
          (fun k : ℕ => ∑' r : Fin L, g (k, r))
            = (fun k : ℕ => ∑ r : Fin L, g (k, r)) := by
        funext k
        rw [tsum_fintype]
      rw [h_tsum_eq_finset_sum]
      -- Σ_{r ∈ Fin L} of summable-in-k families is summable by induction on Finset.
      have h_finset_sum_summable :
          ∀ s : Finset (Fin L),
          Summable (fun k : ℕ => ∑ r ∈ s, g (k, r)) := by
        intro s
        refine s.induction_on ?_ ?_
        · -- base: s = ∅
          simp only [Finset.sum_empty]
          exact summable_zero
        · -- step: insert r₀ into s'
          intro r₀ s' hr₀_notin ih
          have h_r₀ : Summable (fun k : ℕ => g (k, r₀)) := h_residue r₀
          have h_add : Summable (fun k : ℕ => g (k, r₀) + ∑ r ∈ s', g (k, r)) :=
            h_r₀.add ih
          convert h_add using 1
          funext k
          rw [Finset.sum_insert hr₀_notin]
      exact h_finset_sum_summable Finset.univ
  -- Step 3: lift Summable g to Summable f via Nat.divModEquiv.
  -- Nat.divModEquiv L : ℕ ≃ ℕ × Fin L.  So:
  -- Summable f ↔ Summable (f ∘ (Nat.divModEquiv L).symm) via Equiv.summable_iff.
  -- And (f ∘ (Nat.divModEquiv L).symm) (k, r) = f ((Nat.divModEquiv L).symm (k, r)) = f (k * L + r.val) = g (k, r).
  -- So Summable f ↔ Summable g.
  have h_lift : f = g ∘ Nat.divModEquiv L := by
    funext n
    show f n = f (n / L * L + n % L)
    congr 1
    rw [Nat.mul_comm]
    exact (Nat.div_add_mod n L).symm
  rw [h_lift]
  exact h_g_summable.comp_injective (Nat.divModEquiv L).injective

end ZtareProofs.NSResidueClassLiftSummable
