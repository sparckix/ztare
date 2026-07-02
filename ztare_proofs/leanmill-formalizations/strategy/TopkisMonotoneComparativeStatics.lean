/-
LeanMill campaign provenance — topkisObjective_parametricArgmaxSet_isSublatticeSet
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=topkis_truer2_0623) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : math
  time        : wall 1124.43s launch→close = formalize 476.59s (theory+statement+firewall) + prove 647.84s (proof search) · prove p50 655.26s p95 987.95s
  compute     : cost-to-closure 266.47s mean · 464.94s total
  yield       : 6/15 attempts closed (9 failed)
  phases      : 109.6s formalize · 93.5s pool · 19.9s native · 0.2s govern.mnc
  reuse       : cited 0 banked rung(s)
  moves       : native_hammer×5 · claude_warm×5 · proposer_pool×4 · cache_reuse×1
  milestone   : campaign family 'topkis_truer2_0623' — 1 run(s) · REAL elapsed (launch→last) 988s (~16 min) = formalize 0s + prove/other · active-solve 464.9s · 6 closures [launch→last is the honest wall]
     - topkis_truer2_0623: 6/15 closed · elapsed 987.95s (~16.5 min)
-/
/-
Topkis monotone comparative statics — FULL theorem (lattice · supermodular · set-valued · Strong Set Order).

THE RESULT. For a supermodular objective with increasing differences on a lattice `X` parameterized by a
preorder `T`, the SET-VALUED parametric argmax correspondence `t ↦ argmax_x f(x,t)` (optima NOT assumed
unique) is MONOTONE in the Veinott STRONG SET ORDER. The genuine Topkis / Milgrom–Roberts monotone-
comparative-statics theorem — the multi-dimensional, multiple-optima result, not the 1-D unique-maximizer
corollary (that special case is subsumed here and in the ordinal sibling
`topkis_ordinal_monotone_comparative_statics.lean`).

PROVENANCE — every line below is LeanMill's VERBATIM output: the byte-exact `recompilable_probe` from the
closure certificate (reconstructed=False; sorry-free; `#print axioms` = `propext, Classical.choice,
Quot.sound`). Autoformalized + proved end-to-end from a full-ambition NL blueprint; NOTHING hand-edited.

DENOTATION (anti-decoy, §4.2b) — HONEST status: UNDERDETERMINED. LeanMill could not auto-anchor `StrongSetLE`
/ `IncreasingDifferences` to a Mathlib concept (the strong set order is not in Mathlib). By inspection they are
faithful (StrongSetLE is exactly the Veinott strong set order); both are pinnable by a weaker kernel anchor
(`StrongSetLE {a} {b} ↔ a ≤ b`; `IncreasingDifferences f ↔ ∀ x≤x', Monotone (fun t => f x' t - f x t)`),
verified off-file. A 2026-06-23 prompt improvement now has the apparatus seek such anchors itself; a re-run
will emit them IN-FILE and flip the verdict to PINNED. Until then the denotation is honestly UNDERDETERMINED.
-/
import Mathlib


def IncreasingDifferences
    {X T : Type*} [Preorder X] [Preorder T] (f : X → T → ℝ) : Prop :=
  ∀ ⦃x x' : X⦄ ⦃t t' : T⦄,
    x ≤ x' → t ≤ t' → f x' t - f x t ≤ f x' t' - f x t'

def Supermodular
    {X : Type*} [SemilatticeSup X] [SemilatticeInf X] (g : X → ℝ) : Prop :=
  ∀ x y : X, g x + g y ≤ g (x ⊔ y) + g (x ⊓ y)

def ParametricArgmaxSet
    {X T : Type*} (f : X → T → ℝ) (t : T) : Set X :=
  {x | ∀ y : X, f y t ≤ f x t}

def IsSublatticeSet
    {X : Type*} [SemilatticeSup X] [SemilatticeInf X] (s : Set X) : Prop :=
  (∀ ⦃x y : X⦄, x ∈ s → y ∈ s → x ⊓ y ∈ s) ∧
    (∀ ⦃x y : X⦄, x ∈ s → y ∈ s → x ⊔ y ∈ s)

structure TopkisObjective
    (X T : Type*) [SemilatticeSup X] [SemilatticeInf X] [Preorder T] where
  objective : X → T → ℝ
  supermodular_section : ∀ t : T, Supermodular (fun x : X => objective x t)
  increasing_differences : IncreasingDifferences objective

def StrongSetLE
    {X : Type*} [SemilatticeSup X] [SemilatticeInf X]
    (s u : Set X) : Prop :=
  ∀ ⦃x y : X⦄, x ∈ s → y ∈ u → x ⊓ y ∈ s ∧ x ⊔ y ∈ u

def StrongSetMonotone
    {X T : Type*} [SemilatticeSup X] [SemilatticeInf X] [Preorder T]
    (G : T → Set X) : Prop :=
  ∀ ⦃t t' : T⦄, t ≤ t' → StrongSetLE (G t) (G t')

theorem topkisObjective_parametricArgmaxSet_isSublatticeSet : ∀ {X T : Type*} [SemilatticeSup X] [SemilatticeInf X] [Preorder T]
    (F : TopkisObjective X T) (t : T), IsSublatticeSet (ParametricArgmaxSet F.objective t) := by
  intro X T _ _ _ F t
  constructor
  · intro x y hx hy z
    have hsup_le : F.objective (x ⊔ y) t ≤ F.objective x t := hx (x ⊔ y)
    have hy_le_x : F.objective y t ≤ F.objective x t := hx y
    have hx_le_y : F.objective x t ≤ F.objective y t := hy x
    have hsuper :
        F.objective x t + F.objective y t ≤
          F.objective (x ⊔ y) t + F.objective (x ⊓ y) t :=
      F.supermodular_section t x y
    have hx_le_inf : F.objective x t ≤ F.objective (x ⊓ y) t := by
      linarith
    exact le_trans (hx z) hx_le_inf
  · intro x y hx hy z
    have hinf_le : F.objective (x ⊓ y) t ≤ F.objective x t := hx (x ⊓ y)
    have hy_le_x : F.objective y t ≤ F.objective x t := hx y
    have hx_le_y : F.objective x t ≤ F.objective y t := hy x
    have hsuper :
        F.objective x t + F.objective y t ≤
          F.objective (x ⊔ y) t + F.objective (x ⊓ y) t :=
      F.supermodular_section t x y
    have hx_le_sup : F.objective x t ≤ F.objective (x ⊔ y) t := by
      linarith
    exact le_trans (hx z) hx_le_sup

#print axioms topkisObjective_parametricArgmaxSet_isSublatticeSet

theorem topkisObjective_parametricArgmaxSet_strongSetMonotone : ∀ {X T : Type*} [SemilatticeSup X] [SemilatticeInf X] [Preorder T]
    (F : TopkisObjective X T), StrongSetMonotone (ParametricArgmaxSet F.objective) := by
  intro X T _ _ _ F t t' htt' x y hx hy
  constructor
  · intro z
    have hinc :
        F.objective x t - F.objective (x ⊓ y) t ≤
          F.objective x t' - F.objective (x ⊓ y) t' :=
      F.increasing_differences inf_le_left htt'
    have hjoin_le_y :
        F.objective (x ⊔ y) t' ≤ F.objective y t' :=
      hy (x ⊔ y)
    have hsuper :
        F.objective x t' + F.objective y t' ≤
          F.objective (x ⊔ y) t' + F.objective (x ⊓ y) t' :=
      F.supermodular_section t' x y
    have hx_le_inf_t' :
        F.objective x t' ≤ F.objective (x ⊓ y) t' := by
      linarith
    have hx_le_inf_t :
        F.objective x t ≤ F.objective (x ⊓ y) t := by
      linarith
    exact le_trans (hx z) hx_le_inf_t
  · intro z
    have hinc :
        F.objective x t - F.objective (x ⊓ y) t ≤
          F.objective x t' - F.objective (x ⊓ y) t' :=
      F.increasing_differences inf_le_left htt'
    have hinf_le_x :
        F.objective (x ⊓ y) t ≤ F.objective x t :=
      hx (x ⊓ y)
    have hsup_le_y :
        F.objective (x ⊔ y) t' ≤ F.objective y t' :=
      hy (x ⊔ y)
    have hsuper_t' :
        F.objective x t' + F.objective y t' ≤
          F.objective (x ⊔ y) t' + F.objective (x ⊓ y) t' :=
      F.supermodular_section t' x y
    have hx_le_inf_t' :
        F.objective x t' ≤ F.objective (x ⊓ y) t' := by
      linarith
    have hx_le_inf_t :
        F.objective x t ≤ F.objective (x ⊓ y) t := by
      linarith
    have hx_eq_inf_t :
        F.objective x t = F.objective (x ⊓ y) t :=
      le_antisymm hx_le_inf_t hinf_le_x
    have hinf_le_x_t' :
        F.objective (x ⊓ y) t' ≤ F.objective x t' := by
      linarith
    have hx_eq_inf_t' :
        F.objective x t' = F.objective (x ⊓ y) t' :=
      le_antisymm hx_le_inf_t' hinf_le_x_t'
    have hy_le_sup_t' :
        F.objective y t' ≤ F.objective (x ⊔ y) t' := by
      linarith
    exact le_trans (hy z) hy_le_sup_t'

#print axioms topkisObjective_parametricArgmaxSet_strongSetMonotone
