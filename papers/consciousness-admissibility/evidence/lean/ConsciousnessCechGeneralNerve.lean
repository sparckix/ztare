/-
  Consciousness paper (v2) — substrate-B general-nerve detection (§cech, made general). TEMPORARY placement.

  WHAT THIS PROVES: the §cech detection criterion on an ARBITRARY finite nerve, not just the cyclic one. The
  paper detects non-effective descent "by direct inspection of the cycle product: nontrivial holonomy that no
  admissible refinement of the pairwise site can trivialize" (Thm thm:descent, minimal illustration) — and the
  pairwise-observation architecture is an arbitrary finite graph (nerve). Here: for an abelian group `G`, an
  arbitrary vertex type `V`, and a CLOSED WALK `walk : Fin (m+1) → V` (returning to start, `walk (last) = walk 0`),
  a 1-cochain `g : Fin m → G` on the walk's edges with nonzero holonomy `∑ gᵢ ≠ 0` admits NO global section
  `h : V → G` (with `gᵢ = h(walk i.succ) − h(walk i.castSucc)`). So on any nerve, a cycle with nonzero holonomy
  detects non-effective descent. The cyclic nucleus (`ConsciousnessCechHolonomy.lean`) is the special walk on
  `ZMod n`; this is its arbitrary-nerve generalization.

  PROOF SHAPE: the walk's holonomy telescopes — `∑ gᵢ = h(walk m) − h(walk 0)` (the inductive segment lemma
  `iso_lemma2_segment`, with `a = h ∘ walk`) — and the closed-walk return condition `walk (last) = walk 0`
  collapses it to `0`, contradicting `∑ gᵢ ≠ 0`. The lemma name is the planner's generic one (verbatim,
  namespaced); it is the same segment-telescoping engine as the revision-stability rung.

  VERIFICATION: compiles clean against Mathlib (toolchain leanprover/lean4:v4.30.0-rc2), sorry-free; `#print
  axioms closed_walk_holonomy_obstructs_global_section` ⊆ {propext, Classical.choice, Quot.sound}.

  PROVENANCE: produced END-TO-END BY THE LEANMILL HARNESS (run consc_substrateB_generalnerve_0621k, 2026-06-22):
  the autoformalizer rendered the abstract NL into this elementary `Fin`/walk statement (firewall-admitted as
  faithful), the agent strategist chose SOLVE_DIRECT, the codex leaf closed it directly (2 attempts, 227s), and
  the kernel ratified it (axioms clean). Verbatim harness output, wrapped in a namespace.
-/
import Mathlib

open scoped BigOperators

namespace ConsciousnessCechGeneralNerve

universe u v

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

theorem closed_walk_holonomy_obstructs_global_section : ∀ {G : Type u} [AddCommGroup G]
    {V : Type v} (m : ℕ)
    (walk : Fin (m + 1) → V)
    (hclosed : walk (Fin.last m) = walk 0)
    (g : Fin m → G), (∑ i : Fin m, g i) ≠ 0 →
      ¬ ∃ h : V → G,
        ∀ i : Fin m, g i = h (walk i.succ) - h (walk i.castSucc) := by
  intro G _ V m walk hclosed g hsum_ne hglobal
  rcases hglobal with ⟨h, hh⟩
  apply hsum_ne
  have htel :
      (∑ i : Fin m, g i) =
        h (walk ⟨m, Nat.lt_succ_self m⟩) -
          h (walk ⟨0, Nat.succ_pos m⟩) := by
    refine iso_lemma2_segment (m := m)
      (a := fun i : Fin (m + 1) => h (walk i)) (d := g) ?_
    intro i
    simpa using hh i
  rw [htel]
  have hend : walk ⟨m, Nat.lt_succ_self m⟩ = walk ⟨0, Nat.succ_pos m⟩ := by
    simpa using hclosed
  rw [hend, sub_self]

end ConsciousnessCechGeneralNerve
