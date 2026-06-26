/-
  Consciousness paper (v2) — substrate-B revision-stability of the Čech holonomy obstruction. TEMPORARY placement.

  WHAT THIS PROVES (the §7.1 "the obstruction is robust" claim, the criterion's defining adjective made into a
  kernel-checked theorem): on the cyclic nerve `ZMod n` with abelian coefficients `G`, take a 1-cochain `g` with
  nonzero holonomy `∑ gᵢ ≠ 0` (a non-effective descent datum). A REFINEMENT subdivides each edge `i` into `k i`
  sub-edges and REDISTRIBUTES its label — sub-edge labels `g' i : Fin (k i) → G` with `∑ j, g' i j = g i`. Then
  `cyclic_holonomy_refinement_revision_stable` proves the FULL claim, all three conjuncts:
    (1) INVARIANCE      `∑ᵢ ∑ⱼ g' i j = ∑ᵢ g i`           — the refined total holonomy equals the original;
    (2) SURVIVAL        `∑ᵢ ∑ⱼ g' i j ≠ 0`                — hence still nonzero;
    (3) NON-EFFECTIVE   `¬ ∃ H, …`                         — the refined datum still admits NO global section
        (a refined section `H i : Fin (k i + 1) → G` per edge, with intra-edge coboundary `g' i j = H i (j+1) − H i j`
         and inter-edge gluing `H i (last) = H (i+1) (first)`).
  So the non-effective descent is invariant under every admissible subdivision/redistribution of the cover — it is
  REVISION-STABLE, not an artifact of the chosen cover. This does NOT touch invariance under arbitrary change of
  cover/language, nor the paper's central "every admissible procedure factors through effective descent" claim —
  those stay explicitly argued, NOT formalized (formalizing the latter would yield a vacuous tautology).

  PROOF SHAPE (the apparatus designed this decomposition itself): `iso_lemma2_segment` is the per-edge segment
  telescoping `∑ d j = a(m) − a(0)`, proved by INDUCTION on the segment length; `iso_lemma1` is the cyclic
  exact-sum `∑ (h(i+1) − h i) = 0` (telescoping around the outer cycle via the bijection `i ↦ i+1`); `iso_lemma2`
  composes them — a refined section makes each edge's labels telescope to `H i (last) − H i (0)`, the gluing turns
  that into `H (i+1)(0) − H i (0)`, and the outer cyclic exact-sum kills it — so the refined holonomy is 0,
  contradicting (2). The lemma names are the planner's generic ones; they are kept verbatim and namespaced.

  VERIFICATION: compiles clean against Mathlib (toolchain leanprover/lean4:v4.30.0-rc2), sorry-free; `#print
  axioms cyclic_holonomy_refinement_revision_stable` ⊆ {propext, Classical.choice, Quot.sound}.

  PROVENANCE: produced END-TO-END BY THE LEANMILL HARNESS (run consc_substrateB_revstab_0621j, 2026-06-22):
  the autoformalizer rendered the abstract NL into this elementary `ZMod`/`Fin` statement (firewall-admitted as
  faithful), the agent strategist chose DECOMPOSE (correctly — a genuine 3-conjunct target), the planner
  generated the sub-lemma DAG, the codex leaf proved each rung, and `composite_ratify` assembled + kernel-ratified
  the parent (5 closures / 5 ratified, axioms clean). Builds on the machine-closed detection nucleus
  (ConsciousnessCechHolonomy.lean). Verbatim harness output, wrapped in a namespace.
-/
import Mathlib

open scoped BigOperators

namespace ConsciousnessCechRevisionStability

universe u

theorem iso_lemma1 : ∀ {G : Type u} [AddCommGroup G]
    (n : ℕ) [NeZero n] (h : ZMod n → G), (∑ i : ZMod n, (h (i + 1) - h i)) = 0 := by
  intro G _ n _ h
  rw [Finset.sum_sub_distrib]
  have hshift : (∑ i : ZMod n, h (i + 1)) = ∑ i : ZMod n, h i := by
    refine Fintype.sum_equiv (Equiv.addRight (1 : ZMod n)) _ _ ?_
    intro i
    simp
  rw [hshift, sub_self]

theorem iso_lemma2_segment : ∀ {G : Type u} [AddCommGroup G]
    (m : ℕ) (a : Fin (m + 1) → G) (d : Fin m → G)
    (hd : ∀ j : Fin m,
      d j =
        a ⟨j.val + 1, Nat.succ_lt_succ j.isLt⟩ -
          a (j.castLT (Nat.lt_succ_of_lt j.isLt))), (∑ j : Fin m, d j) =
      a ⟨m, Nat.lt_succ_self m⟩ - a ⟨0, Nat.succ_pos m⟩ := by
  intro G _ m
  induction m with
  | zero =>
      intro a d hd
      simp
  | succ m ih =>
      intro a d hd
      rw [Fin.sum_univ_castSucc]
      let a0 : Fin (m + 1) → G := fun i => a (Fin.castSucc i)
      let d0 : Fin m → G := fun j => d (Fin.castSucc j)
      have hd0 : ∀ j : Fin m,
          d0 j =
            a0 ⟨j.val + 1, Nat.succ_lt_succ j.isLt⟩ -
              a0 (j.castLT (Nat.lt_succ_of_lt j.isLt)) := by
        intro j
        dsimp [a0, d0]
        simpa using hd (Fin.castSucc j)
      have hinit :
          (∑ j : Fin m, d (Fin.castSucc j)) =
            a (Fin.castSucc ⟨m, Nat.lt_succ_self m⟩) -
              a (Fin.castSucc ⟨0, Nat.succ_pos m⟩) := by
        simpa [a0, d0] using ih a0 d0 hd0
      have hlast :
          d (Fin.last m) =
            a ⟨m + 1, Nat.lt_succ_self (m + 1)⟩ -
              a (Fin.castSucc ⟨m, Nat.lt_succ_self m⟩) := by
        simpa using hd (Fin.last m)
      have hzero :
          (Fin.castSucc ⟨0, Nat.succ_pos m⟩ : Fin (m + 1 + 1)) =
            ⟨0, Nat.succ_pos (m + 1)⟩ := by
        ext
        rfl
      rw [hinit, hlast]
      abel_nf
      rw [add_comm]
      rw [hzero]

theorem iso_lemma2 : ∀ {G : Type u} [AddCommGroup G]
    (n : ℕ) [NeZero n]
    (k : ZMod n → ℕ)
    (g' : (i : ZMod n) → Fin (k i) → G), (∃ H : (i : ZMod n) → Fin (k i + 1) → G,
        (∀ (i : ZMod n) (j : Fin (k i)),
          g' i j =
            H i ⟨j.val + 1, Nat.succ_lt_succ j.isLt⟩ -
              H i (j.castLT (Nat.lt_succ_of_lt j.isLt))) ∧
        (∀ i : ZMod n,
          H i ⟨k i, Nat.lt_succ_self (k i)⟩ =
            H (i + 1) ⟨0, Nat.succ_pos (k (i + 1))⟩)) →
    (∑ i : ZMod n, ∑ j : Fin (k i), g' i j) = 0 := by
  intro G _ n _ k g' h
  rcases h with ⟨H, hdiff, hglue⟩
  have hinner :
      ∀ i : ZMod n,
        (∑ j : Fin (k i), g' i j) =
          H i ⟨k i, Nat.lt_succ_self (k i)⟩ -
            H i ⟨0, Nat.succ_pos (k i)⟩ := by
    intro i
    exact iso_lemma2_segment (m := k i) (a := H i) (d := g' i) (hd := hdiff i)
  have hstep :
      ∀ i : ZMod n,
        (∑ j : Fin (k i), g' i j) =
          H (i + 1) ⟨0, Nat.succ_pos (k (i + 1))⟩ -
            H i ⟨0, Nat.succ_pos (k i)⟩ := by
    intro i
    rw [hinner i, hglue i]
  calc
    (∑ i : ZMod n, ∑ j : Fin (k i), g' i j)
        = ∑ i : ZMod n,
            (H (i + 1) ⟨0, Nat.succ_pos (k (i + 1))⟩ -
              H i ⟨0, Nat.succ_pos (k i)⟩) := by
          exact Finset.sum_congr rfl (fun i _ => hstep i)
    _ = 0 := by
          exact iso_lemma1 (G := G) n
            (fun i : ZMod n => H i ⟨0, Nat.succ_pos (k i)⟩)

theorem cyclic_holonomy_refinement_revision_stable : ∀ {G : Type u} [AddCommGroup G]
    (n : ℕ) [NeZero n]
    (g : ZMod n → G) (k : ZMod n → ℕ)
    (g' : (i : ZMod n) → Fin (k i) → G)
    (hhol : (∑ i : ZMod n, g i) ≠ 0)
    (hrefine : ∀ i : ZMod n, (∑ j : Fin (k i), g' i j) = g i), (∑ i : ZMod n, ∑ j : Fin (k i), g' i j) = ∑ i : ZMod n, g i ∧
      (∑ i : ZMod n, ∑ j : Fin (k i), g' i j) ≠ 0 ∧
      ¬ ∃ H : (i : ZMod n) → Fin (k i + 1) → G,
        (∀ (i : ZMod n) (j : Fin (k i)),
          g' i j =
            H i ⟨j.val + 1, Nat.succ_lt_succ j.isLt⟩ -
              H i (j.castLT (Nat.lt_succ_of_lt j.isLt))) ∧
        (∀ i : ZMod n,
          H i ⟨k i, Nat.lt_succ_self (k i)⟩ =
            H (i + 1) ⟨0, Nat.succ_pos (k (i + 1))⟩) := by
  intro G _ n _ g k g' hhol hrefine
  have hsum :
      (∑ i : ZMod n, ∑ j : Fin (k i), g' i j) = ∑ i : ZMod n, g i := by
    exact Finset.sum_congr rfl (fun i _ => hrefine i)
  have hsum_ne : (∑ i : ZMod n, ∑ j : Fin (k i), g' i j) ≠ 0 := by
    intro hzero
    apply hhol
    rw [← hsum]
    exact hzero
  have hno :
      ¬ ∃ H : (i : ZMod n) → Fin (k i + 1) → G,
        (∀ (i : ZMod n) (j : Fin (k i)),
          g' i j =
            H i ⟨j.val + 1, Nat.succ_lt_succ j.isLt⟩ -
              H i (j.castLT (Nat.lt_succ_of_lt j.isLt))) ∧
        (∀ i : ZMod n,
          H i ⟨k i, Nat.lt_succ_self (k i)⟩ =
            H (i + 1) ⟨0, Nat.succ_pos (k (i + 1))⟩) := by
    intro hH
    exact hsum_ne (iso_lemma2 n k g' hH)
  exact ⟨hsum, hsum_ne, hno⟩

end ConsciousnessCechRevisionStability
