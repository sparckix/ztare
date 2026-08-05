# Fixed-rational odd-boundary positivity pencil

**Status:** exact positive boundary and full-shell prefix through order
forty-one; all-order profile recurrence remains open

## Eigenquestion

For

\[
Z(e,\ell)
=\log\!\left(
e^{-eY/2}e^{-(X+\ell Y)}e^{-eY/2}
\right),
\]

let \(z_{k,k-1}(e,\ell)\) be the coefficient of the boundary shell
\[
H_{k,k-1}=P^{k+2}.
\]

Is

\[
-z_{k,k-1}(e,\ell)
\]

a nonzero polynomial with nonnegative coefficients for every \(k\ge1\)?
Such a theorem would imply nonvanishing at \((e,\ell)=(1,3)\), and hence
close the odd subsequence of the fixed-rational BCH attack.

## Orientation

The first exact polynomials are

\[
\begin{aligned}
-z_{2,1}&=\frac32e,\\
-z_{3,2}&=\frac65e(3e+\ell),\\
-z_{4,3}&=\frac3{35}e
\left(132e^2+102e\ell+25\ell^2\right).
\end{aligned}
\]

After the Wick rotation the Bernoulli coefficients in the differential
equation are positive, but the full coefficient cone is not invariant.
The claim is therefore restricted to the boundary projection and must use
the correlations imposed by the symmetric BCH solution.

## Discriminating calculation

1. Evaluate the complete symmetric three-factor BCH recursion in the exact
   two-index shell algebra with symbolic \(e,\ell\).
2. Extract \(-z_{k,k-1}\) and test coefficient signs through a depth beyond
   the existing three polynomials.
3. Factor out forced monomials and search the coefficient arrays for a
   triangular recurrence, total-positivity transform, or algebraic
   generating equation.
4. Test any inferred recurrence on held-out exact orders before promotion.

## Success and kill conditions

The lane advances only if every checked boundary polynomial has nonnegative
coefficients and a recurrence-level explanation survives held-out orders.

One negative boundary coefficient kills coefficientwise positivity, even if
the evaluation at \((1,3)\) stays negative.  A positive finite prefix without
an all-order recurrence does not close the fixed-rational attack.

## Claim boundary

This pencil concerns one rational cusp BCH amplitude.  Even an all-order
boundary theorem would still need its previously declared connection to the
unrestricted symmetric contact minimax; it is not a standalone minimax
certificate.

## Outcome

The coefficientwise boundary hypothesis survives every exact order tested.
The dense symbolic replay
[`gauge_fixed_rational_odd_boundary.py`](gauge_fixed_rational_odd_boundary.py)
reproduces the displayed formulas and extends them through boundary index
nine.

The sparse bivariate replay
[`gauge_fixed_rational_odd_boundary_sparse.py`](gauge_fixed_rational_odd_boundary_sparse.py)
extends the exact check through logarithmic order forty-one, hence
boundary index twenty-one.  Every polynomial

\[
-z_{k,k-1}(e,\ell),\qquad 1\le k\le21,
\]

is nonzero and coefficientwise nonnegative.

The stronger observed pattern is that every Wick-rotated odd shell after
the linear \(Q^2\) term is coefficientwise nonnegative through the same
order.  The weighted-profile replay
[`gauge_fixed_rational_profile_cone.py`](gauge_fixed_rational_profile_cone.py)
adds an exact fixed-amplitude structure: through order forty-one every
higher one-variable profile has simple negative zeros, and consecutive
profiles strictly interlace.  It also verifies coefficientwise-positive
boundary parts for the even adjoints

\[
\operatorname{ad}_W^{2m}(Q^2)
\]

at depths \(2,4,6,8\), together with the first nonnegative boundary
Wronskian, through the same shell cap.

This identifies a sharper candidate invariant: the proper-position chain
of weighted profiles and its correlated even-adjoint cone.  The
unrestricted positive coefficient cone has an explicit counterexample.  A
termwise Magnus proof is unavailable: the raw velocity contribution is
already negative in the boundary shell at order five and is repaired by
inverse-`dexp` terms.  The lane therefore remains open until the
nonlinear profile recurrence is proved to preserve interlacing, or a later
exact order violates it.
