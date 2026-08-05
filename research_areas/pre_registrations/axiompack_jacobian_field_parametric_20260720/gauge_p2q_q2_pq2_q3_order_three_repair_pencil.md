# Order-three \(Q^3\) cone repair after the rate-\(7/2\) prefix

## Claim boundary

This pencil tests the next forced radial cancellation in the explicit
coefficientwise-finite cone staircase.  It does not extrapolate the
successive Newton slopes and does not claim an unrestricted construction
from a finite prefix.

## Eigenquestion

Can a parameter-order-three cone coefficient cancel the unique
slope-\(7/2\) radial generator

\[
\frac{137}{1032192}u^9z^9
\]

without creating another source or target face of slope at least \(7/2\)?

## Forced cone coefficient

A seed cone monomial \(P^aQ^b\) has radial weight \(2a+3b\).  At weight
nine, the solution \(P^3Q\) is excluded by \(a\le2b\), while \(Q^3\) is in
the cone.  Since

\[
\operatorname{top}Q_0^3=-\frac1{64}u^9z^9
\]

and target Hamiltonians pull back with factor eight, the unique \(Q^3\)
coefficient canceling the cost-four velocity is

\[
\boxed{
\frac{137}{129024}s^3Q^3.
}
\]

Its source Hamiltonian pullback is

\[
\frac{137}{16128}s^3Q_s^3.
\]

## Discriminating replay

Add this term to

\[
-\frac{s}{168}P^2Q
+\frac{325s}{1344}Q^2
-\frac{s^2}{5376}PQ^2.
\]

Then:

1. reconstruct the complete source velocity without the old slope-four
   projection;
2. verify that \(u^9z^9\) disappears at cost four;
3. compute the new complete Newton polygon and a uniform tail bound;
4. identify every zero-grade generator in the new polygon;
5. run a side-typed forward-`dexp` round trip in the exact leading quotient;
6. derive an all-order terminal response before promoting sharpness;
7. verify the target envelope, including the added cubic.

## Success and kill conditions

The prefix advances the construction only if its exact symmetric upper rate
is below \(7/2\).  It is killed as an improvement if a cost-four degree
eighteen term survives, a later input gives an equal Newton slope, the
target cubic has rate at least \(7/2\), or the contact replay fails.

If the Newton slope drops but terminal survival is unresolved, retain only
the upper bound and the forced next coefficient.

## Exact Newton outcome

The \(Q^3\) coefficient cancels \(u^9z^9\) as predicted.  The complete
Hamiltonian degree profile through cost eight is

\[
(-\infty,10,14,16,20,22,24,24),
\]

and every later input has degree at most twenty-four.  The new source
grading

\[
G_{10/3}=3(a+b)-10q-12
\]

is nonpositive.  Its unique zero-grade velocity is

\[
\frac{11}{1792}u^7z^7
\quad\text{at cost three},
\]

so this prefix has the all-order source upper bound \(10/3\).

This also exposes a cheaper counterattack than an all-order sharpness proof
for the selected prefix.  The weight-seven cone monomial \(P^2Q\) was fixed
only at order one; an independent order-two coefficient remains available.
Because

\[
8\,\operatorname{top}(P_0^2Q_0)
=-\frac98u^7z^7,
\]

the coefficient

\[
\boxed{\frac{11}{2016}s^2P^2Q}
\]

cancels the newly exposed zero-grade velocity.  It can be used alongside
the already forced order-two \(PQ^2\) coefficient.

The disposition is therefore an exact upper-envelope drop, not a sharpness
theorem for the \(Q^3\)-only prefix.  The successor must solve each parameter
row as a coupled radial system rather than cancel only the current top
weight.
