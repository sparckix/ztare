# Finite localization-to-eliminant kernel

## Eigenquestion

If a finite polynomial prefix generates the unit ideal after the endpoint
coefficient ring is replaced by its fraction field, does one obtain a
nonzero polynomial in the endpoint variables inside the original prefix
ideal, without choosing or computing explicit Bezout coefficients?

## Governing identity

Let `A` be a domain, `K` a fraction field of `A`, and let

\[
f_i\in A[Y_1,\ldots,Y_r].
\]

The coefficientwise images of the `f_i` generate the unit ideal in
`K[Y_1,...,Y_r]` exactly when the extension of

\[
I=\langle f_i\rangle\subset A[Y_1,\ldots,Y_r]
\]

to the localization is the unit ideal.  Mathlib's
`IsLocalization.algebraMap_mem_map_algebraMap_iff` then supplies a member of
the localizing submonoid already lying in `I`.  For the fraction-field
localization this member is `C d`, where `d in A` is nonzero.  Thus

\[
C(d)\in\langle f_i\rangle,
\qquad d\ne0.
\]

In the coupled-Julia consumer, `A=K[F]` and the `Y_i` are hidden variables,
so `d(F)` is the required endpoint eliminant.

## Candidate theorem

Prove first for an arbitrary localization `S^-1 A` that mapped unit-ideal
generation yields a localizing element of the original ideal.  Then prove a
multivariate-polynomial corollary:

```text
Ideal.span (range (map (algebraMap A K) o generators)) = top
  -> exists d : A,
       d != 0 /\ C d in Ideal.span (range generators).
```

The theorem need not inspect the generators, compute a gcd, or construct
Bezout coefficients.  Finiteness of the derivative prefix belongs to the
caller that constructs `generators`; ideal localization performs exactly the
denominator-clearing step.

## Adversarial scope checks

- `A` must be a domain for the localizing witness to imply `d != 0`.
- Localizing all nonzero elements of `A[Y]` would return a hidden-dependent
  denominator and would not produce an endpoint eliminant.  Only the image
  of the nonzero base elements may be inverted.
- A common gcd equal to one in `A[Y]` is stronger than necessary.  The
  hypothesis is unit-ideal generation after base localization.
- Pairwise coprimality is insufficient for three or more generators unless
  it is converted to unit-ideal generation.
- Clearing denominators proves ideal membership, not that the eliminant has
  a prescribed degree, is squarefree, or is nonvanishing at a selected
  endpoint.
- No derivative, factorization, resultant, or filtered-obstruction solver is
  part of this kernel.

## Discriminating test

The focused Lean module must consume Mathlib's localization-of-ideals and
multivariate-polynomial localization instances, derive the nonzero base
witness, and compile without importing an aggregate project module.  A
statement that assumes the eliminant, allows a hidden-dependent denominator,
or merely returns a witness in the fraction field fails.

## Outcome

`FormalFiniteLocalizationEliminant` passes both direct focused compilation
and its named `lake build` target.  It proves the generic ideal-localization
lemma and the fraction-field multivariate-polynomial corollary.  The latter
localizes only at constant images of nonzero elements of `A`, so its witness
is exactly `C d` with `d != 0`; no hidden-dependent denominator can be
returned.  The aggregate proof import was not changed.

The kernel deliberately takes localized unit-ideal generation as its
coprimality surface.  Mathlib supplies pairwise `span_gcd` statements but no
needed finite-family bridge in this path.  Converting a caller's finite
factor-multiplicity conclusion to this unit-ideal statement remains a
separate PID step rather than being hidden in denominator clearing.
