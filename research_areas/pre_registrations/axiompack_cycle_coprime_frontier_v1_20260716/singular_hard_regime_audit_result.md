# Singularity audit of the displacement-transitive cycle sets

**Status:** closed bounded audit

## Result

None of the 33 published displacement-transitive examples at orders 8 and 9 is singular. Order 10 has no displacement-transitive example.

Two independent finite-group computations agree on every group order:

| Carrier | Models | `|G(X)|` distribution | `|Dis(X)|` distribution | Singular |
|---:|---:|---|---|---:|
| 8 | 30 | 16: 4; 32: 16; 64: 8; 128: 2 | 8: 12; 16: 8; 32: 8; 64: 2 | 0 |
| 9 | 3 | 81: 3 | 27: 3 | 0 |

The order-8 groups are 2-groups and the order-9 groups are 3-groups, so their prime supports introduce no prime absent from the carrier size. The explicit Cayley-graph closure and SymPy's Schreier–Sims implementation returned the same orders for all 33 models.

## Interpretation

Castelli observes that a counterexample to Question 30 must be singular: some prime divides `|G(X)|` but not `|X|`. The complete published hard stratum through order 10 never enters that necessary regime. Consequently, its common-prime cycle pattern does not yet identify a new unrestricted mechanism.

The next discriminating target is narrower and more consequential: construct a singular cycle set whose displacement group is transitive, or prove a structural obstruction. A positive construction would answer Castelli's stated challenge for a singular cycle set without finite primitive level, even if it did not yet supply a coprime-cycle counterexample.

## Claim boundary

This audit is exhaustive only for the pinned database stratum. It cannot rule out singular displacement-transitive examples at larger orders, establish priority, or resolve Question 30.

Machine-readable evidence: `singular_hard_regime_audit_receipt.json`. Executable audit: `singular_hard_regime_audit.py`. Frozen eigenquestion and kill conditions: `displacement_regime_pencil.md`.
