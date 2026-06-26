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

### `topkis_monotone_comparative_statics.lean` — Topkis' monotonicity theorem
`topkisObjective_parametricArgmaxSet_isSublatticeSet`. The foundation of monotone comparative statics: for a
**supermodular** objective with **increasing differences** in the parameter, the parametric argmax set moves
monotonically — formalized here as the argmax set being a **sublattice**. The engine behind "complementarity ⇒
optimal choices rise with the parameter" (strategic complementarity in supermodular games). Non-vacuity of the
constructed argmax set is established (not vacuously true on the empty set).

### `topkis_ordinal_monotone_comparative_statics.lean` — ordinal (single-crossing) Topkis
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
