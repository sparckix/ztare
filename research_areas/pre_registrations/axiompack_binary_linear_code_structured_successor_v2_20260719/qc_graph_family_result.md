# Quasicyclic graph-family exact result

Date: 2026-07-19

## Outcome

The exact quotient covered all `5^5 = 3125` phase tuples as 125 cyclic-shift
orbits of size 25. The binary adapter then checked all `2^20-1 = 1,048,575`
nonzero messages for every canonical member.

No `[50,20,14]` witness occurred. The exact minimum-distance distribution was:

| Minimum distance | Members |
|---:|---:|
| 6 | 10 |
| 8 | 50 |
| 10 | 65 |

Every matrix had rank 20 and every encoded fixed message `f=1+x^10` had
weight 14, so the failure is caused by additional message cancellations, not
by the rank or universal-word derivations.

Oracle receipt SHA-256:
`b7d8d79d6b0ca8beecb6f3c399eae3d29fa8f38a30aef1f43370c6b6cc310dd7`.

## Claim boundary

This exhausts only the exact 125-member family in
`qc_graph_family_selected_pencil.md`. It gives no ambient nonexistence result
for binary `[50,20,14]` codes and grants no kernel-ratification authority.

## Next eigenquestion

The recurrent killing messages are dominated by binomials
`f=1+x^s`. The next discriminator is whether the family can be rejected almost
entirely by the cyclic autocorrelation spectrum

\[
  \operatorname{wt}(g(1+x^s))+\operatorname{wt}(ga(1+x^s)),
  \qquad 1\le s<20,
\]

leaving a small explicitly typed sparse-message residual. If so, future graph
families should generate multipliers under autocorrelation lower bounds before
calling the full exact verifier.
