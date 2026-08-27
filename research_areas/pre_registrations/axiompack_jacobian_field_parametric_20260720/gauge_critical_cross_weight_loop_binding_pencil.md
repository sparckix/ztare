# Critical cross-weight row to loop contradiction

## Eigenquestion

Can the specialized cross-weight row already present in the Darboux lane be
bound to the exact July critical connection strongly enough that the
single-valued eigenrow/monodromy theorem applies without assuming its pulled-
back ODE or its return equation?

## Existing chain

The current kernels own four distinct stages:

1. `FormalFilteredDarbouxPolynomialBinding` turns Darboux divisibility into
   coefficient rows and a cross-multiplied eigenrow.
2. `FormalInvariantDivisorEigenrowSpecialization` evaluates the normalized
   row on the double equilibrium divisor and produces

   \[
     b D_0(a)-a D_0(b)=k L a b.
   \]

3. `FormalCriticalConnectionRationalization` and
   `FormalCriticalHolonomyLoop` identify the actual July connection with the
   explicit rational function and construct a circle carrier whose
   coefficient on the circle is exactly that connection.
4. `FormalSingleValuedEigenrowMonodromy` excludes a nonzero returning
   solution of the pulled-back scalar equation.

The absent adapter is between stages 2 and 4.

## Smallest exact one-sheet adapter

Let `first, second : C -> C` be single-valued coefficient functions near the
certified critical circle, with declared derivatives `firstDerivative` and
`secondDerivative`.  Assume on the circle:

\[
  second\,first'-first\,second'
   = k\,L\,first\,second,
\]

where `L` is the actual `criticalCoefficient`, `k>0`, `second` never
vanishes on the circle, and `first` is nonzero at the basepoint.  Define

\[
  r(theta)=\frac{first(gamma(theta))}{second(gamma(theta))}.
\]

Quotient differentiation and the cross row give

\[
  r'(theta)=k\,L(gamma(theta))\,gamma'(theta)\,r(theta).
\]

No return equation is assumed: periodicity of `circleMap` and single-valued
base functions gives `r(2*pi)=r(0)`.  The existing monodromy theorem then
gives a contradiction.

This adapter is reusable and bounded.  It consumes the actual critical
connection through `CriticalLoopRealization.coefficient_on_circle`, rather
than accepting a desired residue or multiplier identity as a premise.

## Finite-cover boundary

The one-sheet adapter does not manufacture a finite algebraic coefficient
cover.  If `first/second` lives on a cover rather than descending to a
single-valued base function, periodicity of the base circle does not imply
return of the lifted coefficient.  The existing monodromy theorem can consume
a positive return turn once supplied, but the repository still needs a
carrier with:

- a finite cover degree `e>0`;
- a lift of the critical circle through `e` turns;
- analytic realization of the specialized coefficient ratio on that lift;
- the pulled-back cross-row equation; and
- endpoint equality on the returned sheet.

Naming a finite extension or invoking finite deck monodromy does not provide
these data in Lean.

## Rational-residue alternative

`FormalRationalLogDerivativeResidueComparison` avoids loop lifting when the
specialized ratio is already rational in the base parameter.  It proves the
contradiction after being given exact numerator/denominator powers at the
critical pole and unit evaluations there.  Its own claim boundary is exact:
the repository does not yet construct those local factorizations for an
arbitrary specialized ratio, nor prove that a coefficient produced by the
persistent-prime argument belongs to the rational function field rather than
a finite algebraic extension.

Thus the residue route and the loop route expose the same classification
boundary in two forms: rational descent plus local factorization, or finite-
cover analytic realization plus returned lift.

## Kill conditions

1. An abstract derivation equation is not yet a pointwise complex derivative
   equation on the critical circle.
2. A zero first coefficient or a vanishing denominator allows the quotient
   construction to fail.
3. A circle chosen before the ratio is known need not avoid the ratio's zeros
   and poles; a compatible shrink/reconstruction theorem is required.
4. Negative weight must be made positive by swapping the two occupied rows;
   zero weight has no monodromy obstruction.
5. Base-circle periodicity proves return only for functions that descend to
   the base.  It cannot be used for an unspecified algebraic branch.
6. The local residue equation may not be assumed: it must follow from a
   rational or finite-cover local normal form.

## Claim boundary

The bounded adapter closes the critical monodromy endpoint for a supplied
single-valued one-sheet analytic cross row on a compatible critical circle.
It does not close the unconditional Darboux-weight lane.  The smallest live
leaf is the coefficient-field realization theorem: persistent specialized
coefficients must either descend rationally, with a local zero/pole
factorization, or be realized on a finite returned cover carrying the exact
cross row.
