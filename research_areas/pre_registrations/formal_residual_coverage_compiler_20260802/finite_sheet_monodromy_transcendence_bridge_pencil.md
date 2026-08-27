# Finite-sheet monodromy--polynomial bridge

## Eigenquestion

Suppose analytic continuation supplies infinitely many finite endpoint returns,
the endpoint values form an injective scalar monodromy orbit, and the
coefficient data at the return basepoint has only finitely many sheets.  Can a
nonzero polynomial relation hold at every retained return without invoking a
maximal-continuation theorem inside the algebraic contradiction?

## Target input and claim boundary

The algebraic input can be stripped to:

- a finite type of returned coefficient states `sheet`;
- a polynomial `P_i` for each state, with `P_i != 0` for every visited state;
- an injective endpoint sequence `Y_n`;
- a state sequence `sigma_n`; and
- `P_(sigma_n)(Y_n) = 0` for every retained finite return.

Then no such data exists.  Indeed,

\[
  \{Y_n:n\geq 0\}
  \subseteq \bigcup_i Z(P_i),
\]

and the set on the right is a finite union of finite sets, whereas the set on
the left is infinite.

Equivalently, one may first select an infinite subsequence on which the sheet
is constant and apply the fixed-polynomial root escape theorem.  The finite
union formulation is stronger operationally: it does not need to construct or
enumerate that subsequence.

## Scalar-orbit specialization

For

\[
  Y_n=\lambda^n Y_0,
\]

injectivity follows from

\[
  \lambda\ne0,\qquad Y_0\ne0,\qquad
  \lambda^N\ne1\quad(N>0).
\]

Thus a finite-sheet algebraic or meromorphic coefficient cover cannot make a
nonzero univariate polynomial relation compatible with every finite endpoint
return of a non-torsion scalar orbit.

Here "finite-return subsequence" means an infinite subsequence all of whose
endpoint values lie in the affine line.  A finite-length subsequence gives no
contradiction.  If the original continuation has infinitely many affine
returns, compose the endpoint, state, and relation sequences with an injective
enumeration of those return indices.

## Exact kill conditions

The statement fails or does not apply in each of the following cases:

1. A visited specialized polynomial is zero.  Its root condition is
   tautological, so nonvanishing is required state by state.
2. Only finitely many endpoint returns are affine.  Infinity-valued returns
   must be routed through the reciprocal/nonfinite carrier.
3. The endpoint orbit is not injective: zero initial value, zero multiplier,
   or positive torsion permits repetitions.
4. The returned polynomial family has infinite range.  Finite sheet labels
   alone are insufficient if an additional coefficient changes with the loop
   number and is not sheet-determined.
5. The relation is multivariate before coefficient specialization.  Each
   returned state must first yield one nonzero univariate polynomial in the
   endpoint.

Degree drops, repeated roots, common factors, sheet collisions, and nontrivial
finite deck permutations do not affect the argument.  They only shrink or
relabel the finite union.

## Existing coverage and missing carrier

`FormalComplexMonodromyFiniteRootEscape` proves escape from one fixed nonzero
polynomial for the irrational-residue scalar orbit.
`FormalSeparatedRelationFiniteOrbit` constructs one fixed nonzero polynomial
from `visible * p(Y) = scalar * q(Y)` and excludes an injective infinite orbit
in that fiber.

The missing reusable kernel is the finite-family bridge:

```text
Finite sheet_index
polynomial : sheet_index -> C[X]
endpoint : Nat -> C
Injective endpoint
sheet_at : Nat -> sheet_index
forall n, polynomial (sheet_at n) != 0
forall n, IsRoot (polynomial (sheet_at n)) (endpoint n)
--------------------------------------------------------
False
```

It needs no path-lift assumption.  It also cannot manufacture the sequences,
prove that every retained endpoint is finite, or prove that the returned
coefficient state has finite range.  Those are the remaining analytic and
projective path-lift obligations upstream.

## Intended formal surface

One isolated Lean file should contain the finite-family theorem and a scalar
non-torsion corollary reusing `scaled_power_orbit_injective`.  It should not
alter an aggregate import or claim construction of a continuation lift.
