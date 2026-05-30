[model: gpt-5]
Here are three targeted theorems that the structural signals suggest are missing and load‑bearing. Each is framed so it can be discharged by standard order/monotonicity lemmas (e.g., mul_le_mul_of_nonneg_left, max_le_iff), hence falsifiable. I also explain which signals point to each gap.

1) Monotonicity in the “ν × shell” direction (fills the top‑rank missing link “nu — shell”)

- Signal basis:
  - Diagnostic 2 (link prediction): The strongest missing edge is nu — shell (ranks 1 and 6). This is a classic place where a simple monotonicity lemma nu ≥ 0 ⇒ shell ≤ shell' ⇒ nu*shell ≤ nu*shell' closes obligations.
  - Diagnostic 1: nu is load‑bearing (rank 22), and R.shellN appears in top-25 (rank 25), reinforcing a ν–shell interaction pathway.
- Proposed theorem:
  theorem nu_mul_mono_on_shell {nu shell shell' : ℝ} (hν : 0 ≤ nu) (h : shell ≤ shell') :
    nu * shell ≤ nu * shell' :=
  mul_le_mul_of_nonneg_left h hν

2) Fractional collapse against a core floor (fills “coreFloor — fraction” gap)

- Signal basis:
  - Diagnostic 2 (link prediction): coreFloor — fraction is tied for 2nd–5th strongest missing edge. This is exactly the standard bound that multiplying a nonnegative baseline by a fraction in [0,1] cannot increase it.
- Proposed theorem:
  theorem coreFloor_mul_fraction_le_self {coreFloor fraction : ℝ}
      (hcf : 0 ≤ coreFloor) (hfr : fraction ≤ (1 : ℝ)) :
    coreFloor * fraction ≤ coreFloor :=
  by
    have h' : coreFloor * fraction ≤ coreFloor * 1 := mul_le_mul_of_nonneg_left hfr hcf
    simpa [mul_one] using h'

3) Assemble three branch-wise bounds into a single target (merging branchA/branchB/mixedC into threeProfileAssembledTax via max)

- Signal basis:
  - Diagnostic 3 (role clustering): The branch nodes (branchA, branchB, mixedC) and the aggregator threeProfileAssembledTax co-cluster tightly (cluster 2) with the highest k-core, indicating the need for a “merge branches via max” lemma.
  - Diagnostic 4 (robustness): branchA, branchB, mixedC, threeProfileAssembledTax are all 100% robust, meaning any missing max-assembly lemma here is likely load-bearing, not noise.
  - Diagnostic 1: threeProfileAssembledTax appears in the load-bearing set (rank 21).
- Proposed theorem:
  theorem assembled_tax_from_branches
      {branchA branchB mixedC threeProfileAssembledTax : ℝ}
      (hA : branchA ≤ threeProfileAssembledTax)
      (hB : branchB ≤ threeProfileAssembledTax)
      (hC : mixedC ≤ threeProfileAssembledTax) :
    max (max branchA branchB) mixedC ≤ threeProfileAssembledTax :=
  by
    have hAB : max branchA branchB ≤ threeProfileAssembledTax :=
      (max_le_iff).2 ⟨hA, hB⟩
    exact (max_le_iff).2 ⟨hAB, hC⟩

Notes:
- All three theorems are intentionally minimal and should be solvable by existing algebra/order lemmas (mul_le_mul_of_nonneg_left and max_le_iff). They directly bridge the high-score missing edges or perform the robust branch-to-aggregator merge that cluster/robustness diagnostics highlight.
- If “shell” is instantiated in the codebase as R.shellN (as suggested by Diagnostic 1), a variant of (1) with shell := R.shellN can be added verbatim.