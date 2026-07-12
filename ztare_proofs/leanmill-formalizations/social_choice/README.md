# Social choice — machine-checked formalizations

Kernel-verified Lean 4 + Mathlib formalizations of social-choice results, produced end-to-end by
[LeanMill](../../../docs/concepts/leanmill_architecture.md) from natural-language blueprints (through the
faithfulness firewall; each proof independently kernel-ratified with an axiom audit). Every file is
self-contained (`import Mathlib`) and carries a GENERATED provenance header emitted by
`promote_campaign_artifact.py` — not hand-authored.

## Contents

### `MedianVoterCondorcet.lean` — Black's median voter theorem
`median_voter_theorem`. With an odd electorate and single-peaked preferences over a linearly ordered policy
space, the median voter's ideal point is a **Condorcet winner**: it beats every alternative in pairwise majority
vote. The classical result that a majority-rule equilibrium exists and sits at the median, over an ordered field
of policy positions (no fixed decidable carrier). Axiom-clean `[propext, Classical.choice, Quot.sound]`.

### `deferred_acceptance_stability_and_quiescence_load_bearing.lean` — Gale-Shapley stability
`deferred_acceptance_stability_and_quiescence_load_bearing`. For finite two-sided deferred acceptance with strict
complete preferences, every quiescent proposal-run outcome is stable: no man and woman form a blocking pair. The
same theorem also carries the load-bearing counterexample: before quiescence, a reachable state can still have a
blocking pair. Axiom-clean `[propext, Classical.choice, Quot.sound]`.

### Definitions

The vocabulary the theorem is stated over — read them to check the faithfulness boundary; each is documented at
the top of its file.

**`MedianVoterCondorcet.lean`**
- `Prefers (u : A → B) (x y : A) : Prop`
- `SinglePeaked (peak : A) (u : A → B) : Prop`
- `supporters (u : V → A → B) (x y : A) : Finset V`
- `Beats (u : V → A → B) (x y : A) : Prop`
- `IsMedian [LinearOrder A] (peaks : V → A) (m : A) : Prop`
- `CondorcetWinner (u : V → A → B) (m : A) : Prop`

**`deferred_acceptance_stability_and_quiescence_load_bearing.lean`**
- `StrictPreference (Agent : Type u) (Alt : Type v)`
- `Matching (Man : Type u) (Woman : Type v)`
- `ProposalState (Man : Type u) (Woman : Type v)`
- `ProposalRun (prefW : StrictPreference Woman Man) : ProposalState Man Woman → List Man → ProposalState Man Woman → Prop`
- `Quiescent (state : ProposalState Man Woman) : Prop`
- `BlockingPair (prefM : StrictPreference Man Woman) (prefW : StrictPreference Woman Man) (μ : Matching Man Woman) (m : Man) (w : Woman) : Prop`
- `Stable (prefM : StrictPreference Man Woman) (prefW : StrictPreference Woman Man) (μ : Matching Man Woman) : Prop`
