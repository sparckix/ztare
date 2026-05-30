# Riemann operator search: an informative null

Public digest of the `riemann_operator_search` (GP-125) substrate
probe. Raw run logs stay internal; this is the honest result.

## The question

Can a searched family of operators reproduce the Riemann-zero spacing
statistics (low reconstruction error together with the GUE-like
spacing coefficient-of-variation), i.e. land inside the
(low-MSE, target spacing-CV) box?

## The result

An informative null. Within the tested operator grammar at
`n_matrix = 250`, no combination crossed into the target box. Adding
off-diagonal arithmetic operators (log(gcd), adelic, prime-coupling,
divisor) to the polynomial backbone moved the loss by about 0.0014
(0.2253 to 0.2267), which is noise-level. The prior structural
negative (polynomial alone cannot reach the target CV) is reinforced,
not overturned.

## Honest labelling

A null, not a proven ceiling. Whether it is a true asymptotic barrier
or a finite-`n` / finite-grammar artifact is open; scaling `n_matrix`
to 500-1000, or moving to non-diagonal non-multiplicative operator
families, are the un-run next experiments. After two informative nulls
on structurally adjacent questions the branch was paused under
sunk-cost discipline rather than scaled further. The contribution is
the honest null plus the recorded decision to stop.
