# Byzantine quorum intersection: safe + available consensus quorums exist iff n ≥ 3f + 1

The foundational counting theorem of Byzantine fault tolerance — the reason state-machine-replication protocols
(PBFT, Tendermint, and every modern BFT chain) need strictly more than three times as many nodes as the faults
they tolerate. It is not an algorithm-specific fact: it is a property of the QUORUM SYSTEM the protocol quorums
must form. Two quorums must always share a correct node (so two conflicting decisions are impossible — SAFETY),
and some quorum must contain no faulty node (so the protocol can always make progress — AVAILABILITY/LIVENESS).
This blueprint targets the general characterization over `Fin n` with an at-most-`f`-sized adversary, plus the
tight non-degenerate witness at `n = 3f + 1` and the impossibility at `n = 3f`.

The distinctive output is the counting dependency, machine-checked. Safety comes from ONE cardinality fact —
two size-`q` subsets of an `n`-set meet in at least `2q − n` nodes — and availability from another. The bound
`n ≥ 3f + 1` is exactly where those two constraints stop conflicting. A kernel proof pins that: you cannot drop
`1 ≤ f`, you cannot weaken "any two quorums" to a lucky pair, and you cannot let safety collapse to a bare
numeric inequality divorced from an actual shared correct node. None of this vocabulary is in Mathlib — it is a
NEW domain (distributed systems), not a math result with a Lean proof already. Theory-building: probe Mathlib's
`Finset` cardinality API with Loogle and the warm checker; decompose however the kernel teaches. A non-closure is
an honest gap, never a fake closure, and never a silent restriction (no `f = 0` retreat, no fixed-fault-set
weakening).

## Domain
formalization-nonmath

## Theory file
byzantine_quorum_intersection.lean

The bespoke vocabulary Mathlib lacks — establish each once, over `Finset (Fin n)` (decidable, finite; pure
counting, no measure theory, no reals), and never "prove" a definition:

- **Nodes / faults** — `n f : ℕ` with `1 ≤ f` (a real adversary). Node set is `Finset.univ : Finset (Fin n)`.
- **Faulty set** — any `F : Finset (Fin n)` with `F.card ≤ f`. The adversary is quantified over ALL such `F`;
  a correct node is one in `Fᶜ` (outside `F`).
- **Quorum** — a `Finset (Fin n)`. A **threshold quorum system** of size `q` is the family of subsets of
  cardinality at least `q`.
- **Safety (intersection)** — a size-`q` threshold system is *safe against f* when every two quorums share a
  CORRECT node: `∀ Q₁ Q₂ : Finset (Fin n), q ≤ Q₁.card → q ≤ Q₂.card → ∀ F, F.card ≤ f → ((Q₁ ∩ Q₂) \ F).Nonempty`.
- **Availability (liveness)** — the system is *available against f* when, whoever the ≤`f` faulty nodes are, a
  full quorum of correct nodes exists: `∀ F, F.card ≤ f → ∃ Q, q ≤ Q.card ∧ Disjoint Q F`.

## Target
Over `Fin n` with an at-most-`f` adversary (`1 ≤ f`), DEFINE the threshold quorum system and its safety /
availability against `f`, and prove all three:

1. **Quorum-intersection safety (the load-bearing lemma).** If `n + f + 1 ≤ 2 * q`, then the size-`q` threshold
   system is SAFE against `f`: for ANY two quorums `Q₁ Q₂ : Finset (Fin n)` with `q ≤ Q₁.card` and `q ≤ Q₂.card`,
   and ANY faulty `F` with `F.card ≤ f`, the set `(Q₁ ∩ Q₂) \ F` is NONEMPTY — a common correct node.
   This must be the SET statement, proved through `Finset` cardinality (`|Q₁ ∩ Q₂| ≥ 2q − n ≥ f + 1 > |F|`), not
   a restatement of the numeric inequality. It is the reason safety holds, and it must be a proven rung.

2. **The `n ≥ 3f + 1` characterization (both directions).** A threshold size `q` that is SIMULTANEOUSLY safe
   (`n + f + 1 ≤ 2 * q`) and available (`q + f ≤ n`, so a quorum of correct nodes fits) EXISTS **iff**
   `3 * f + 1 ≤ n`. Prove BOTH directions: forward is the construction (a witnessing `q`); the reverse is the
   necessity bound (a safe + available `q` forces `3f + 1 ≤ n`) — prove it, do not assume it.

3. **A non-degenerate tightness witness.** With `1 ≤ f`:
   - At `n = 3 * f + 1`, `q = 2 * f + 1`: exhibit TWO DISTINCT, PROPER concrete quorums `Q₁ Q₂ : Finset (Fin (3f+1))`
     (each of card `2f + 1`, `Q₁ ≠ Q₂`, and neither equal to `Finset.univ`) such that for EVERY faulty `F` with
     `F.card ≤ f`, `((Q₁ ∩ Q₂) \ F).Nonempty` — a guaranteed common correct node — AND an available all-correct
     quorum exists.
   - At `n = 3 * f` (still `1 ≤ f`): NO threshold size `q` is simultaneously safe and available — the safe ∧
     available region is empty (impossibility at the boundary).
   This forbids the vacuous readings: `f = 0`, `Q₁ = Q₂`, a quorum equal to the whole node set, or safety that
   holds only for one lucky fault set.

**GUARDS — MANDATORY, DO NOT WEAKEN.**
- **`1 ≤ f`.** `f = 0` is the no-Byzantine-fault degeneracy: any single node is a safe+available quorum and
  `n ≥ 1` suffices, so the theorem is vacuous. The result is about TOLERATING faults — state and USE `1 ≤ f`.
- **Safety is the set fact `((Q₁ ∩ Q₂) \ F).Nonempty`, NOT the bare `n + f + 1 ≤ 2q`.** The inequality is a
  numeric side condition; the theorem's content is that it FORCES an actual shared correct node in every quorum
  pair under every admissible adversary. The proof MUST route through `Finset.card` intersection
  (`Finset.card_inter_add_card_union` / `card_union_le`, and `card A − card B ≤ card (A \ B)`), not stop at `omega`.
- **Universally quantified over `Q₁, Q₂` AND `F`.** Do not weaken to a fixed pair, to `Q₁ = Q₂`, or to a single
  fault set. In part 3 the witness quorums are DISTINCT and PROPER (`≠ univ`).
- **The characterization is genuinely an `iff`** — the necessity direction (`∃ safe+available q → 3f+1 ≤ n`) is
  the load-bearing bound, not a convenience; prove it.

## Idea
(Advisory planner context — a tractability steer, NOT a formalization mandate.) The whole result rests on one
counting inequality. For `Q₁ Q₂ ⊆ (univ : Finset (Fin n))`, `Finset.card_inter_add_card_union` gives
`|Q₁ ∩ Q₂| + |Q₁ ∪ Q₂| = |Q₁| + |Q₂|`, and `|Q₁ ∪ Q₂| ≤ n` (`Finset.card_le_univ`), so
`|Q₁ ∩ Q₂| ≥ |Q₁| + |Q₂| − n ≥ 2q − n`. With `n + f + 1 ≤ 2q` this is `≥ f + 1`. Since `|F| ≤ f`,
`|(Q₁ ∩ Q₂) \ F| ≥ |Q₁ ∩ Q₂| − |F| ≥ (f + 1) − f = 1 > 0` (`Finset.card_sdiff_ge` / `le_card_sdiff`), hence
`Nonempty` (`Finset.card_pos`). That single chain IS safety.

The characterization `(∃ q, n + f + 1 ≤ 2q ∧ q + f ≤ n) ↔ 3f + 1 ≤ n` is ℕ arithmetic once the quorum size is
existentially handled: forward, the minimal safe `q` needs `q + f ≤ n`, forcing `3f + 1 ≤ n` (`omega`); reverse,
`q := 2f + 1` at the tight point, or `q := n − f` in general, witnesses it (`omega`). Keep `q` an explicit ℕ.

Witness at `n = 3f + 1`: over `Fin (3f+1)`, take `Q₁ = univ.filter (fun x => (x : ℕ) < 2f+1)` (nodes `0 … 2f`)
and `Q₂ = univ.filter (fun x => f ≤ (x : ℕ))` (nodes `f … 3f`). Each has card `2f + 1`; `Q₁ ∩ Q₂` is nodes
`f … 2f`, card `f + 1`; `Q₁ ≠ Q₂` (node `0 ∈ Q₁ \ Q₂`) and both `≠ univ` (node `3f ∉ Q₁`). For any `F` with
`|F| ≤ f`, `|(Q₁ ∩ Q₂) \ F| ≥ (f+1) − f = 1`. Keep the quorums as concrete `Fin`-subsets so `Finset.card`
computes; a `decide` lever may help small legs but the general `∀ F` step is the cardinality chain above, not
`decide`. Everything is over `Finset (Fin n)` — pure counting, no reals, no measure theory.
