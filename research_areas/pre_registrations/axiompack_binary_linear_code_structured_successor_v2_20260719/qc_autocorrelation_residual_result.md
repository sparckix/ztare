# Quasicyclic autocorrelation residual result

Date: 2026-07-19

## Deterministic outcome

The independently regenerated 125-member quotient was screened by every
binomial message `f=1+x^s` for `1 <= s < 20`. All 125 members were killed;
the residual set is empty.

| Minimum binomial weight | Members |
|---:|---:|
| 6 | 10 |
| 8 | 50 |
| 10 | 65 |

The screen receipt is
`1b3daf3acb372c58173e402bdc94ea7c3ad14446cec3e2561d317b8cd74f595e`.
Its histogram agrees exactly with the full `2^20-1`-message replay receipt
`b7d8d79d6b0ca8beecb6f3c399eae3d29fa8f38a30aef1f43370c6b6cc310dd7`.

## Information gained

The failure is fully visible in the cyclic autocorrelation spectrum; no
higher-support message is required to exclude a member. The companion pencil
artifact `qc_transversal_obstruction_pencil.md` explains the uniform upper
bound `d <= 10`: multiplication by `1+x^5` turns every phase multiplier into
the complement of a five-point residue transversal, and such a transversal
has a repeated nonzero cross-residue difference.

## Typed successor representation

The next graph-family producer should generate second-block multipliers under
the inequalities

\[
\operatorname{wt}(g(1+x^s))+\operatorname{wt}(b(1+x^s))\ge14
\quad(1\le s<20)
\]

before exact code verification. The selected complement-transversal chart is
excluded analytically. This successor is a multiplier-autocorrelation chart,
not a claim that the ambient `[50,20,14]` cell is empty.
