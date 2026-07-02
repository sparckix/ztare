# Distributed systems — machine-checked formalizations

Kernel-verified Lean 4 + Mathlib formalizations of distributed-computing results (fault tolerance, quorum
systems, consensus), produced end-to-end by
[LeanMill](../../../docs/concepts/leanmill_architecture.md) from natural-language blueprints — gated by the
faithfulness firewall (statement compiles, is non-trivial, round-trip faithful) and independently kernel-ratified
with a matched-negative-control receipt + axiom audit. Each file is self-contained (`import Mathlib`) and carries
a GENERATED provenance header from `promote_campaign_artifact.py` (not hand-authored).

> **Time accounting.** Headers report **`campaign span`** = real elapsed — the true wall; **`cost-to-closure
> total`** = summed active-solve time only (smaller — omits formalization / imports / gaps).

## Contents

### `ByzantineQuorumIntersection.lean` — Byzantine quorum intersection: `n ≥ 3f + 1`
`byzantine_threshold_quorum_safe_available_iff_and_tight_witness`. The foundational counting theorem of
Byzantine fault tolerance — why state-machine-replication protocols (PBFT, Tendermint, and modern BFT chains)
need strictly more than three times as many nodes as the faults they tolerate. Over `Fin n` with an at-most-`f`
adversary (`1 ≤ f`), the threshold quorum system is characterized on three counts:

1. **Quorum-intersection safety (load-bearing).** If `n + f + 1 ≤ 2q`, then *any* two size-`≥ q` quorums and
   *any* faulty set of size `≤ f` still share a **correct** node: `((Q₁ ∩ Q₂) \ F).Nonempty`. Proved through
   `Finset` cardinality (`|Q₁ ∩ Q₂| ≥ 2q − n ≥ f + 1 > |F|`) — the set fact, not a bare numeric inequality.
2. **The `n ≥ 3f + 1` characterization (both directions).** A threshold size `q` that is simultaneously *safe*
   (`n + f + 1 ≤ 2q`) and *available* (`q + f ≤ n`, an all-correct quorum fits) **exists iff `3f + 1 ≤ n`** —
   forward by construction, reverse by the necessity bound.
3. **Non-degenerate tightness witness.** At `n = 3f + 1`, `q = 2f + 1`: two *distinct, proper* concrete quorums
   whose intersection retains a correct node against every admissible adversary; and at `n = 3f`, **no** `q` is
   simultaneously safe and available (impossibility at the boundary).

The `1 ≤ f` guard is load-bearing and stated (the `f = 0` no-fault case is vacuous). Safety is the set-nonemptiness
fact, not the arithmetic side condition; the intersection is quantified over *all* quorum pairs and *all*
admissible fault sets. `#print axioms` = `[propext, Classical.choice, Quot.sound]` — no `sorry`, no custom axioms.

The natural-language input is [`bft_quorum_intersection_blueprint.md`](./bft_quorum_intersection_blueprint.md)
in this folder.

*Honest caveat (advisory, not a false closure):* the denotation-faithfulness pass reports the def
`ThresholdSafeAndAvailableBound` as UNDERDETERMINED — its meaning is not pinned by a verified external anchor.
The composite statement is nonetheless kernel-proven and firewall-faithful; this only flags that one auxiliary
definition's *denotation* is argued, not independently certified.

## Why "distributed systems" (and what is NOT here)

This is a fault-tolerance / quorum-systems result: a property of the quorum system a consensus protocol's quorums
must form (intersection ⇒ safety, availability ⇒ liveness), not an execution/state-machine proof of a specific
protocol. It is deliberately about the *counting bound* — the reason `n > 3f` — proved over finite `Finset`s with
no measure theory. Nothing in Mathlib or (at the time of filing) any public Lean repository covers it.
