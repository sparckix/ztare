# Published enumeration database audit, orders 8–10

**Status:** Complete finite database audit; unrestricted question remains open.

Date: 2026-07-16

## Result

The replayable scanner parsed 5,251,733 published cycle-set tables:

| order | parsed tables | indecomposable | coprime-cycle counterexamples |
|---:|---:|---:|---:|
| 8 | 34,530 | 100 | 0 |
| 9 | 321,931 | 16 | 0 |
| 10 | 4,895,272 | 36 | 0 |

Every parsed table passed row-permutation and diagonal-permutation checks. All
152 indecomposable tables also passed an independent replay of the cycle-set
identity. The action orbit and row-cycle predicates were recomputed directly
from each table.

## Stronger finite pattern

Every indecomposable table has a prime divisor of the carrier size dividing
every nontrivial cycle length in every left translation:

- order 8: all 100 models have common prime `2`;
- order 9: all 16 models have common prime `3`;
- order 10: one model has profile `{2}`, fifteen have `{5}`, and twenty have
  `{10}`. Their common prime supports are `{2}`, `{5}`, and `{2,5}`.

This pattern is an empirical invariant candidate. It is stronger than merely
finding zero counterexamples, but it remains finite evidence.

## Source identity and reproduction

Source: `https://github.com/vendramin/enumeration.git`, commit
`92f85ee118ec73fdb7a397e4fd748f1265f02bc3`.

The source repository accompanies Akgün–Mereb–Vendramin, *Math. Comp.* 91
(2022), 1469–1481, DOI `10.1090/mcom/3696`. The order-8 and order-9 file
hashes and the filename-ordered order-10 manifest hash are frozen in the
script and structured receipt.

```bash
./venv/bin/python research_areas/pre_registrations/axiompack_cycle_coprime_frontier_v1_20260716/enumeration_database_audit.py \
  --repository /path/to/vendramin/enumeration --sizes 8 9 10
```

The replay took 572.527 seconds. Script SHA-256:
`18274b81042ca9629408f7f6bdac3b4d8c422db8250950e45b852a59dc852e93`.
Full audit-output receipt SHA-256:
`0cd344fb0391b449596a890b07ed0f4577f03af5de3b690b1f216768b25cd921`.
Structured summary receipt SHA-256:
`9d9c67c6cc85043d074e075554efd07fe0acc76865f34c07e6d55ab16996e8a4`.

## Claim boundary

The authors' enumeration and publication supply the completeness claim for
the database through order 10. This audit independently parses the listed
tables and recomputes the target predicates; it does not reconstruct their
isomorph-free enumeration proof. No unrestricted implication or priority
claim follows from this finite audit.
