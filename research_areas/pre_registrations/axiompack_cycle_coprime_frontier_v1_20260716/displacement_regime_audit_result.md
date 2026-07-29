# Displacement-regime audit of the published order-8/9/10 cycle sets

**Status:** closed bounded audit

## Result

The pinned Vendramin enumeration contains 5,251,733 raw tables and 152 indecomposable cycle sets at orders 8, 9, and 10. Recomputing the displacement action separates them as follows:

| Order | Indecomposable | Finite primitive level / intransitive `Dis(X)` | Transitive `Dis(X)` | Coprime-cycle candidate |
|---:|---:|---:|---:|---:|
| 8 | 100 | 70 | 30 | 0 |
| 9 | 16 | 13 | 3 | 0 |
| 10 | 36 | 36 | 0 | 0 |
| **Total** | **152** | **119** | **33** | **0** |

The order-8 and order-9 finite-primitive-level counts exactly reproduce the published 70 and 13. This independently checks the implementation of the displacement-group stratum. The 33 remaining examples are the discriminating complement: Castelli's finite-primitive-level proof does not cover them. Every one still has a prime dividing every nontrivial cycle of every left translation:

- all 30 order-8 hard-regime examples share the divisor 2;
- all three order-9 hard-regime examples share the divisor 3;
- the order-10 database contains no transitive-displacement example.

## What changed

The common-prime phenomenon is not confined to the finite-primitive-level class handled by the published quotient argument. It persists across every published example in the complementary displacement-transitive regime through order 10. This makes the transitive-displacement case a narrower theorem target rather than an undifferentiated empirical remainder.

## Claim boundary

This is exhaustive for the pinned published database, not for arbitrary finite cycle sets. It neither proves Question 30 nor establishes that the bounded pattern is absent from the literature. A frontier claim requires an unrestricted argument for the displacement-transitive regime, a counterexample, or an exact prior-art match.

Machine-readable evidence: `displacement_regime_audit_receipt.json`. Executable audit: `displacement_regime_audit.py`. Pencil target and kill conditions: `displacement_regime_pencil.md`.
