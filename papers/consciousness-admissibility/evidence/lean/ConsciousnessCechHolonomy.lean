/-
  Consciousness paper (v2) — substrate-B (classical) DETECTION nucleus, machine-verified. TEMPORARY placement.

  WHAT THIS PROVES: the §7.1 holonomy obstruction as the elementary witness that Čech Ȟ¹ DETECTS non-effective
  descent. On the cyclic nerve (`ZMod n`, edges `i → i+1`, no filled triangles) with an abelian coefficient group
  `G`, a descent datum is a 1-cochain `g : ZMod n → G`; a global section realizing it is a 0-cochain `h` with
  `gᵢ = h(i+1) − h i`; the holonomy is `Σ gᵢ`. The DETECTION direction (all the paper's §-Čech argument needs):
  if the holonomy is nonzero the datum has NO global section — descent over the cover is non-effective (`D = 1`).
  This is the contrapositive of the *easy* telescoping direction (a section forces `Σ gᵢ = Σ(h(i+1)−h i) = 0`,
  since `i ↦ i+1` is a bijection of `ZMod n`); the hard backward construction is NOT needed for detection.
  Instance: `G = ZMod 2`, `n = 3`, `g ≡ 1` ⇒ holonomy `1+1+1 = 1 ≠ 0` ⇒ no global consistent labelling (the
  "product around the cycle is −1" obstruction). This soundly DETECTS the obstruction; it does not EXHAUST it
  (the kernel-pair example has Ȟ¹ = 0 but D = 1 — see consciousness_kernel_pair.lean) — that strictness gap is a
  separate rung.

  VERIFICATION: compiles clean against Mathlib (toolchain leanprover/lean4:v4.30.0-rc2), sorry-free; `#print
  axioms cyclic_holonomy_obstructs_effective_descent` ⊆ {propext, Classical.choice, Quot.sound}.

  PROVENANCE: this proof was produced END-TO-END BY THE LEANMILL HARNESS (run consc_substrateB_nucleus_0621h,
  2026-06-22), NOT hand-written: the autoformalizer rendered the abstract Čech NL into this elementary `ZMod n`
  statement (firewall-admitted as faithful), the agent strategist chose SOLVE_DIRECT (not decompose), and the
  codex leaf closed it directly in one round (155s); the kernel ratified it (axioms clean). It even factored out
  the telescoping helper `cyclic_exact_sum_zero` on its own. The earlier hand-simulated version is superseded by
  this machine-closed one.
-/
import Mathlib

open scoped BigOperators

universe u

/-- Telescoping around the cycle: any coboundary sums to zero, because `i ↦ i+1` is a bijection of `ZMod n`. -/
theorem cyclic_exact_sum_zero {G : Type u} [AddCommGroup G]
    (n : ℕ) [NeZero n] (h : ZMod n → G) :
    (∑ i : ZMod n, (h (i + 1) - h i)) = 0 := by
  rw [Finset.sum_sub_distrib]
  have hshift : (∑ i : ZMod n, h (i + 1)) = ∑ i : ZMod n, h i := by
    refine Fintype.sum_equiv (Equiv.addRight (1 : ZMod n)) _ _ ?_
    intro i
    simp
  rw [hshift, sub_self]

/-- §7.1 detection: nonzero holonomy ⇒ no global section ⇒ descent non-effective. -/
theorem cyclic_holonomy_obstructs_effective_descent {G : Type u} [AddCommGroup G]
    (n : ℕ) [NeZero n] (g : ZMod n → G) (hsum : (∑ i : ZMod n, g i) ≠ 0) :
    ¬ ∃ h : ZMod n → G, ∀ i : ZMod n, g i = h (i + 1) - h i := by
  rintro ⟨h, hh⟩
  apply hsum
  calc
    (∑ i : ZMod n, g i) = ∑ i : ZMod n, (h (i + 1) - h i) :=
      Finset.sum_congr rfl (fun i _ => hh i)
    _ = 0 := cyclic_exact_sum_zero n h

-- §7.1 witness instance: ZMod 2 on the 3-cycle, g ≡ 1, holonomy 1 ≠ 0 ⇒ no global section.
example : ¬ ∃ s : ZMod 3 → ZMod 2, ∀ i, (1 : ZMod 2) = s (i + 1) - s i :=
  cyclic_holonomy_obstructs_effective_descent 3 (fun _ => (1 : ZMod 2)) (by decide)
