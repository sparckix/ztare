# Single-valued eigenrow versus non-torsion monodromy

## Eigenquestion

After invariant-divisor specialization produces a nonzero scalar coefficient
`r` with

\[
  D_0 r = k L r,
\]

does the existing critical logarithmic-loop carrier already exclude
single-valuedness when the multiplier of `L` has infinite order?

## Exact loop formulation

Let `carrier` be the existing `LogarithmicCircleCarrier` for `L`, with
multiplier `mu`.  Let `weight` and `turns` be positive natural numbers.  Let
`r : R -> C` be the pullback of the specialized coefficient to the circle
parameter and suppose

\[
 r'(theta)=weight\,L(gamma(theta))\,gamma'(theta)\,r(theta)
\]

for every real `theta`.  Assume

\[
 r(0)\ne0,
 \qquad
 r(2\,pi\,turns)=r(0),
\]

and `mu^N != 1` for every positive natural `N`.  Then `False`.

The `turns` parameter absorbs a finite coefficient cover: a sheet that is
single-valued only after ramification degree `e` returns after `e` base
turns, and the contradiction uses `mu^(weight*e) != 1`.

## Proof skeleton

1. Scale the existing carrier by `weight`: scale its residue, regular
   coefficient, and regular primitive.  Its pulled-back coefficient is
   exactly `weight` times the original one, and its multiplier is
   `mu^weight`.
2. The existing `continuedValue` theorem constructs the explicit solution
   with initial value `r(0)` and gives its endpoint after `turns` turns.
3. The explicit solution never vanishes.  Both it and `r` solve the same
   pulled-back scalar equation.  The quotient `r / continuedValue` has
   derivative zero, hence is constant on `R` by Mathlib's existing
   derivative-zero theorem.  Therefore `r` equals the explicit solution.
4. Single-valuedness yields

   \[
   r(0)=r(0)\,mu^{weight\,turns}.
   \]

   Cancel `r(0)` and contradict positive-power non-torsion.

This reuses `FormalAnalyticLogarithmicLoop`; it does not introduce a second
ODE solver, path-lift type, or monodromy representation.

## Existing leaves

- `LogarithmicCircleCarrier.continuedValue_hasDerivAt` owns the pulled-back
  scalar ODE.
- `LogarithmicCircleCarrier.continuedValue_nat_turns` owns the endpoint law.
- `Complex.exp_ne_zero` owns nonvanishing of the explicit solution.
- `is_const_of_deriv_eq_zero` and quotient differentiation own uniqueness.
- the critical carrier already supplies positive-power non-torsion.
- `FormalInvariantDivisorEigenrowSpecialization` owns the upstream passage
  from the normalized cross row to the scalar eigenrow.

The missing binding is upstream, not inside this bridge: the specialized
coefficient ratio must be pulled back to the critical circle, shown to obey
the displayed equation, and shown to return after the declared number of
turns.

## Kill conditions

1. `r(0)=0`: the zero solution is single-valued.
2. `weight=0` or `turns=0`: the endpoint multiplier is the zeroth power.
3. `mu` is torsion, or merely `mu^(weight*turns)=1`: a nonzero single-valued
   solution is compatible with the equation.
4. The eigenrow is only formal at one point and has not been continued along
   the entire loop.
5. The coefficient depends on a moving `Y` not restricted to the invariant
   divisor; then `D_0` does not reduce to the scalar base derivative used by
   this theorem.
6. A finite cover is named but no positive return turn is supplied.
7. For a negative integer weight, the rows must first be swapped so that the
   nonzero weight difference is positive.  The zero difference is excluded.

No global nonvanishing hypothesis is needed once `r(0) != 0`; scalar-ODE
uniqueness forces nonvanishing along the loop.

## Intended Lean surface

One isolated file may add a natural scaling operation to the existing circle
carrier, prove its coefficient and multiplier identities, and prove the
positive-weight/positive-turn contradiction.  It must not alter aggregate
imports or claim the upstream invariant-divisor-to-loop binding.
