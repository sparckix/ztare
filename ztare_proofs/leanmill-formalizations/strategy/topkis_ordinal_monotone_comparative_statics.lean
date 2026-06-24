/-
LeanMill campaign provenance — ordinalTopkis_compact_existence_and_strongSetMonotone_explicit
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=topkis_litfirst2) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms [propext, Classical.choice, Quot.sound]
  domain      : math
  time        : time-to-closure 433.02s (first 433.02s · p50 433.02s · p95 433.02s) · campaign span 433.02s (lead 647.09s)
  compute     : cost-to-closure 73.08s mean · 73.08s total
  yield       : 1/5 attempts closed (3 failed)
  phases      : 180.9s formalize · 68.6s pool · 11.4s native · 0.1s govern.mnc
  reuse       : cited 0 banked rung(s)
  moves       : native_hammer×3 · proposer_pool×1 · claude_warm×1
-/
/-
Topkis ORDINAL monotone comparative statics — existence + Strong Set Order, NO cardinal subtraction.

THE RESULT. For a real-valued objective on a complete lattice `X` parameterized by a preorder `T`, under
ORDINAL strong single-crossing (`OrdinalStrongSingleCrossing := OrdinalSingleCrossing ∧ OrdinalStrictSingleCrossing`
— utility-free, no cardinal differences) and quasi-supermodular sections, with continuous sections on a compact
space: (1) the parametric argmax set is NONEMPTY for every parameter (EXISTENCE, via the extreme value theorem),
and (2) the set-valued argmax correspondence `t ↦ argmax_x f(x,t)` is MONOTONE in the Veinott STRONG SET ORDER
(optima NOT assumed unique). This is the ORDINAL (Milgrom–Shannon) counterpart to the cardinal
`IncreasingDifferences` / `Supermodular` version in `topkis_monotone_comparative_statics.lean` — it ELIMINATES the
real-number-subtraction restriction (the roadmap "strip out cardinal restrictions" upgrade), and adds existence.

WHY IT MATTERS — LeanMill non-gaming milestone (2026-06-23). The LITERAL NL claim ("ordinal single-crossing ⇒
monotone comparative statics") is FALSE: weak (≤) single-crossing admits ties that break the strong set order.
LeanMill formalized the literal, KERNEL-REFUTED it (proved ¬G), recorded the refutation, and then closed THIS
CORRECTED theorem with the STRICT half added — exactly the Milgrom–Shannon strengthening the counterexample
demands. No launder, no fake closure; the correction is disclosed and the engine's faithfulness firewall + kernel
gate it end-to-end.

PROVENANCE — every line below is LeanMill's VERBATIM output: the byte-exact `recompilable_probe` from the closure
certificate (sorry-free; `#print axioms` = `propext, Classical.choice, Quot.sound`). Autoformalized + proved
end-to-end from a full-ambition NL blueprint; NOTHING hand-edited.

DENOTATION (anti-decoy, §4.2b) — HONEST status: `StrongSetLE` is UNDERDETERMINED vs Mathlib (the Veinott strong
set order is not in Mathlib); by inspection it is the faithful Veinott order (`∀ x∈A, y∈B, x⊓y∈A ∧ x⊔y∈B`).
`OrdinalSingleCrossing` / `OrdinalStrictSingleCrossing` are the standard ordinal single-crossing predicates
(no real subtraction). `QuasiSupermodular` is the ordinal complementarity (weak + strict join/meet comparisons).
-/
import Mathlib


def OrdinalSingleCrossing
    {X T α : Type*} [Preorder X] [Preorder T] [Preorder α]
    (f : X → T → α) : Prop :=
  ∀ ⦃x x' : X⦄ ⦃t t' : T⦄,
    x ≤ x' → t ≤ t' → f x t ≤ f x' t → f x t' ≤ f x' t'

def OrdinalStrictSingleCrossing
    {X T α : Type*} [Preorder X] [Preorder T] [Preorder α]
    (f : X → T → α) : Prop :=
  ∀ ⦃x x' : X⦄ ⦃t t' : T⦄,
    x ≤ x' → t ≤ t' → f x t < f x' t → f x t' < f x' t'

def OrdinalStrongSingleCrossing
    {X T α : Type*} [Preorder X] [Preorder T] [Preorder α]
    (f : X → T → α) : Prop :=
  OrdinalSingleCrossing f ∧ OrdinalStrictSingleCrossing f

def QuasiSupermodular
    {X α : Type*} [SemilatticeSup X] [SemilatticeInf X] [Preorder α]
    (g : X → α) : Prop :=
  (∀ x y : X, g (x ⊓ y) ≤ g x → g y ≤ g (x ⊔ y)) ∧
    (∀ x y : X, g (x ⊓ y) < g x → g y < g (x ⊔ y))

def IsGlobalMax {X α : Type*} [Preorder α] (g : X → α) (x : X) : Prop :=
  ∀ y : X, g y ≤ g x

def ArgmaxSet {X α : Type*} [Preorder α] (g : X → α) : Set X :=
  {x | IsGlobalMax g x}

def ParametricArgmaxSet
    {X T α : Type*} [Preorder α] (f : X → T → α) (t : T) : Set X :=
  ArgmaxSet (fun x : X => f x t)

def StrongSetLE
    {X : Type*} [SemilatticeSup X] [SemilatticeInf X] (A B : Set X) : Prop :=
  ∀ ⦃x y : X⦄, x ∈ A → y ∈ B → x ⊓ y ∈ A ∧ x ⊔ y ∈ B

theorem ordinalTopkis_compact_existence_and_strongSetMonotone_explicit : ∀ {X T : Type*}
    [CompleteLattice X] [TopologicalSpace X] [CompactSpace X] [Nonempty X]
    [Preorder T]
    (f : X → T → ℝ)
    (h_continuous_sections : ∀ t : T, Continuous (fun x : X => f x t))
    (h_strong_single_crossing : OrdinalStrongSingleCrossing f)
    (h_quasiSupermodular : ∀ t : T, QuasiSupermodular (fun x : X => f x t)), (∀ t : T, ∃ x : X, x ∈ ParametricArgmaxSet f t) ∧
      (∀ ⦃t t' : T⦄,
        t ≤ t' →
          StrongSetLE (ParametricArgmaxSet f t) (ParametricArgmaxSet f t')) := by
  intro X T _ _ _ _ _ f h_continuous_sections h_strong_single_crossing h_quasiSupermodular
  constructor
  · intro t
    rcases isCompact_univ.exists_isMaxOn Set.univ_nonempty
        ((h_continuous_sections t).continuousOn) with
      ⟨x, _hx, hmax⟩
    exact ⟨x, by
      dsimp [ParametricArgmaxSet, ArgmaxSet, IsGlobalMax]
      intro y
      exact (isMaxOn_univ_iff.mp hmax) y⟩
  · intro t t' htt'
    intro x y hx hy
    constructor
    · dsimp [ParametricArgmaxSet, ArgmaxSet, IsGlobalMax] at hx hy ⊢
      intro z
      have hmeet_le_x_t : f (x ⊓ y) t ≤ f x t := hx (x ⊓ y)
      have hx_le_meet_t : f x t ≤ f (x ⊓ y) t := by
        by_contra hnot
        have hlt_t : f (x ⊓ y) t < f x t :=
          lt_of_le_not_ge hmeet_le_x_t hnot
        have hlt_t' : f (x ⊓ y) t' < f x t' :=
          h_strong_single_crossing.2 inf_le_left htt' hlt_t
        have hy_lt_join_t' : f y t' < f (x ⊔ y) t' :=
          (h_quasiSupermodular t').2 x y hlt_t'
        exact hy_lt_join_t'.not_ge (hy (x ⊔ y))
      exact le_trans (hx z) hx_le_meet_t
    · dsimp [ParametricArgmaxSet, ArgmaxSet, IsGlobalMax] at hx hy ⊢
      intro z
      have hmeet_le_x_t : f (x ⊓ y) t ≤ f x t := hx (x ⊓ y)
      have hmeet_le_x_t' : f (x ⊓ y) t' ≤ f x t' :=
        h_strong_single_crossing.1 inf_le_left htt' hmeet_le_x_t
      have hy_le_join_t' : f y t' ≤ f (x ⊔ y) t' :=
        (h_quasiSupermodular t').1 x y hmeet_le_x_t'
      exact le_trans (hy z) hy_le_join_t'

#print axioms ordinalTopkis_compact_existence_and_strongSetMonotone_explicit
