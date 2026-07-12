# Strategy — machine-checked formalizations

Kernel-verified Lean 4 + Mathlib formalizations of game-theory / decision-theory results (strategic
complementarity, monotone comparative statics), produced end-to-end by
[LeanMill](../../../docs/concepts/leanmill_architecture.md) from natural-language blueprints — gated by the
faithfulness firewall (statement compiles, is non-trivial, round-trip faithful) and independently kernel-ratified
with a matched-negative-control receipt + axiom audit. Each file is self-contained (`import Mathlib`) and carries
a GENERATED provenance header from `promote_campaign_artifact.py` (not hand-authored).

> **Time accounting.** Headers report **`campaign span`** = real elapsed — the true wall; **`cost-to-closure
> total`** = summed active-solve time only (smaller — omits formalization / imports / gaps).

## Contents

### `TopkisMonotoneComparativeStatics.lean` — Topkis' monotonicity theorem
`topkisObjective_parametricArgmaxSet_isSublatticeSet`. The foundation of monotone comparative statics: for a
**supermodular** objective with **increasing differences** in the parameter, the parametric argmax set moves
monotonically — formalized here as the argmax set being a **sublattice**. The engine behind "complementarity ⇒
optimal choices rise with the parameter" (strategic complementarity in supermodular games). Non-vacuity of the
constructed argmax set is established (not vacuously true on the empty set).

### `TopkisOrdinalMonotoneComparativeStatics.lean` — ordinal (single-crossing) Topkis
`ordinalTopkis_compact_existence_and_strongSetMonotone_explicit`. The ordinal generalization (Milgrom–Shannon):
under the **single-crossing** property (an ordinal condition, weaker than cardinal supermodularity), optimal
choices are monotone in the **strong set order**, with explicit compactness/existence. The strict half of
single-crossing is load-bearing (a weak-only formulation is genuinely false — the kernel refutes it).

## Why "strategy" (and what is NOT here)

These are comparative-statics / game-theory results: how strategic choices respond to parameters. Finance results
(asset pricing, AMMs, capital-structure waterfalls) live in [`../finance/`](../finance/) — including the corporate
APR / pari-passu waterfalls, which are capital-structure (corporate finance), and the constant-product AMM
invariants, which are market-microstructure.

## Provenance & trust

- **Autoformalized, not hand-written** — the apparatus produced the Lean statements + proofs through the
  faithfulness firewall.
- **Kernel-ratified + axiom-clean** — `#print axioms` reports only `propext`, `Classical.choice`, `Quot.sound`
  and **no `sorryAx`**.

## Verify it yourself

```
lake env lean <file>.lean
```

It should elaborate with no errors and print the axiom audit (standard axioms only).

### Definitions

The vocabulary these theorems are stated over — read them to check the faithfulness boundary; each is documented at the top of its file.

**`TopkisMonotoneComparativeStatics.lean`**
- `IncreasingDifferences`
- `Supermodular`
- `ParametricArgmaxSet`
- `IsSublatticeSet`
- `StrongSetLE`
- `StrongSetMonotone`

**`TopkisOrdinalMonotoneComparativeStatics.lean`**
- `OrdinalSingleCrossing`
- `OrdinalStrictSingleCrossing`
- `OrdinalStrongSingleCrossing`
- `QuasiSupermodular`
- `IsGlobalMax {X α : Type*} [Preorder α] (g : X → α) (x : X) : Prop`
- `ArgmaxSet {X α : Type*} [Preorder α] (g : X → α) : Set X`
- `ParametricArgmaxSet`
- `StrongSetLE`

**`VcgDsicPivotIndependenceAndTwoUnitWitness.lean`**
- `socialWelfare`
- `othersWelfare`
- `updateReport`
- `IsWelfareMaximizer`
- `DominantStrategyTruthful`
- `DecreasingMarginals {K : Type*} [LE K] (m : TwoUnitMarginals K) : Prop`
- `twoUnitStepValue {K : Type*} [Zero K] [Add K] (m : TwoUnitMarginals K) (q : Nat) : K`
- `unitsForAgent0 (a : TwoUnitAllocation) : Nat := a.val`
- `unitsForAgent1 (a : TwoUnitAllocation) : Nat := 2 - a.val`
