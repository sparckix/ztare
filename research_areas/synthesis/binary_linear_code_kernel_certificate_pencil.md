# Binary linear-code kernel certificate: pencil design

Date: 2026-07-18

## Eigenquestion

Can the registered binary-code adapter turn an exactly verified generator
matrix into a kernel-pure Lean theorem for the same frozen predicate, at
dimension 20, without trusting the host replay or using `native_decide`?

## Target input and theorem

Input: an explicit binary generator matrix `G` of length `n` and dimension
`k`, together with required rank `k` and distance `d`. The upstream boundary
already normalizes and exhaustively checks the artifact, but that receipt is
only a candidate for the formal stage.

The Lean proposition must restate the mathematical predicate:

\[
  \operatorname{rank}_{\mathbf F_2}(G)=k
  \quad\land\quad
  \forall u\in\{1,\ldots,2^k-1\},\
  \operatorname{wt}(uG)\ge d.
\]

For a systematic/full-rank generator, the rank leg can be discharged either
by a kernel computation of row reduction or by a separately checked pivot
certificate. The distance leg is a complete finite universal check over the
exact carried rows.

## Certificate choices

1. First benchmark a balanced, kernel-pure Boolean checker closed with plain
   `by decide`. This keeps the proof axiom-clean; it must not use
   `native_decide`, `ofReduceBool`, `sorry`, or `admit`.
2. If a monolithic reduction exceeds the ratification budget, partition the
   message interval into content-bound blocks. Each block theorem checks a
   disjoint interval with plain `decide`; a small structural theorem joins the
   blocks into the universal predicate.
3. If kernel reduction remains too costly, the successor capability is a
   proof-producing SAT/LRAT or branch-and-bound certificate whose checker is
   formalized once. A hash of host output alone is insufficient.

## Proof skeleton

- Encode each row as a bounded natural number with bit `i` equal to coordinate
  `i`.
- Define `encode rows message` by XOR-folding the selected rows.
- Define Hamming weight over exactly the declared coordinate range.
- Define a Boolean row-rank checker or validate a pivot/elimination trace.
- Define `messagesPass` over all nonzero message masks, or over certified
  disjoint blocks.
- Define `Satisfies artifact predicate : Prop` as the Boolean checker equaling
  `true`.
- Generate a content-bound theorem for the exact normalized artifact and close
  it with a kernel-pure proof term.
- Send that theorem through the existing ratification-only governance door;
  do not give theorem credit to the upstream Python receipt.

## Kill conditions

- `#print axioms` exposes `Lean.ofReduceBool` or any axiom outside the current
  allowlist.
- The Lean checker omits rank, skips a nonzero message, changes coordinate
  order, truncates rows, or is not bound to the normalized artifact and frozen
  predicate hashes.
- A distance-12 control compiles as satisfying distance 14.
- The positive `[51,20,14]` control fails under a feasible boundary budget.
- A chunk join admits gaps, overlaps that hide gaps, or reordered target data.

## Recurrence check and formal surface

The existing adapter has a sound small `[3,2,2]` reduction proof and a generic
host verifier, but no scalable kernel certificate. Repository governance
explicitly rejects `native_decide`. The missing capability is kernel-pure
finite-certificate scaling.

The implementation surface belongs in the binary-code adapter plus the common
construction-ratification contract. Tests must cover the small fixture, the
published positive control, the perturbed distance-12 negative control,
content tampering, and banned-token/axiom rejection.
