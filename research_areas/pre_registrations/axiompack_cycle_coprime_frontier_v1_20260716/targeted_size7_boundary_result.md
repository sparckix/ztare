# Targeted order-7 coprime-cycle boundary

**Status:** Exact bounded result; unrestricted question remains open.

Date: 2026-07-16

## Result

The order-7 counterexample query is `UNSAT` under two independently encoded
transitivity predicates. No nondegenerate cycle-set table on seven elements
simultaneously has a transitive left-translation action and a nontrivial row
cycle of length coprime to seven.

At prime order seven, every proper nontrivial cycle length `2` through `6` is
coprime to the carrier size. The query therefore covers every possible target
cycle length.

## Normalization and encodings

Simultaneous relabeling sends the witness row to `0`. There are exactly two
positions for the row index relative to a witnessed cycle: on the cycle or off
it. The script enumerates both normalized cases for every length `2` through
`6`.

Transitivity was checked in two ways:

- every nonempty proper subset has a membership-crossing left-translation
  edge;
- every point is reachable from `0` in the union of left-row action edges.

The subset-cut query returned `UNSAT` in 629,894 ms. The reachability query
returned `UNSAT` in 618,035 ms. Their SMT-LIB payload hashes are recorded in
the structured receipt.

## Matched controls

- A constant action by a transposition satisfies the cycle premise and the
  cycle-set laws while remaining decomposable.
- A constant action by a 7-cycle satisfies the cycle-set laws and transitivity
  while having no proper nontrivial row cycle.

Both controls pass a separate concrete replay of row bijectivity, diagonal
bijectivity, the cycle-set identity, cycle type, and action orbits.

## Reproduction

```bash
./venv/bin/python research_areas/pre_registrations/axiompack_cycle_coprime_frontier_v1_20260716/targeted_size7_boundary.py
```

Script SHA-256:
`a60fd9e8e5b13b08ada6869824176c76c3652e7c7c22d5bb093766de4636b582`.
Receipt SHA-256:
`62c3b9ad3901878f39e171acf21d4587183a3502a1b16c55a581530067db6d94`.

## Claim boundary

This result is exact for order 7 under the displayed finite encoding and
normalization. It supplies no unrestricted implication and no priority claim.
