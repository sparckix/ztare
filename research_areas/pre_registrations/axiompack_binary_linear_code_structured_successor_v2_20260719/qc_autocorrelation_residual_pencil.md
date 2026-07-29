# Quasicyclic multiplier autocorrelation residual

Date: 2026-07-19

## Eigenquestion

Do the 19 binomial messages `f=1+x^s`, `1 <= s < 20`, provide a compact
obstruction certificate for the exhausted 125-member graph family?

## Falsifiable claim

For a graph code `(gf,gfa)`, a binomial message has weight

\[
  w_s(a)=\operatorname{wt}(g+x^s g)
        +\operatorname{wt}(ga+x^sga).
\]

The claim is that `min_s w_s(a) < 14` for at least 90% of the 125 canonical
multipliers. Success yields an autocorrelation-screen representation and an
explicit residual set. Failure means the exact negative depends on richer
multi-term cancellations and this coordinate is too weak.

## Kill and anti-overfit conditions

- Generate the 125 canonical multipliers independently from the exact phase
  domain; do not parse the prior verifier output.
- Evaluate all 19 binomials for every member and preserve every tied minimizing
  shift.
- Do not claim a member passes the target when all binomials have weight at
  least 14; it remains an unresolved residual requiring exact replay.
- Do not promote the screen into the common kernel. It is a binary
  quasicyclic representation candidate until cross-family reuse is shown.

## Intended next representation

Each multiplier receives a 19-coordinate binomial-weight spectrum, its minimum
margin from 14, and a residual flag. A future family producer should search
inside the nonnegative-margin region and leave full exact verification as the
referee.
