# Filtered compiler and the unreachable ramification coinvariant

**Status:** exact substrate-neutral compiler, all-polynomial Jacobian symbol
and reachability theorem; unrestricted symmetric tail minimax remains open;
historical priority unassessed

## Compiler result

[`filtered_obstruction.py`](../../../src/ztare/common/filtered_obstruction.py)
now separates three algebraic categories over \(\mathbb Q\):

1. a same-space filtered coinvariant with moving-relation transport;
2. a cross-grade symbol cokernel with distinct domain and codomain; and
3. a forcing-span reachability calculation after a validated symbol
   cokernel.

Every action or symbol map is total on its declared basis, every nonzero
entry is checked against its declared filtration shift, and moving relations
must descend before rank is computed.  A surviving distinguished class
returns an exact annihilating row; a killed class returns exact decomposition
coefficients.  The reachability certificate reports the ambient cokernel
dimension and the rank of the supplied forcing span inside that quotient
separately.

The alien regressions include moving relations, a wrong shift, a missing
column, a bad relation descent, basis permutation, an unreachable surviving
class, and an excited surviving class.

## Universal Jacobian symbol

Let

\[
C=4P^3-P^2-18PQ+27Q^2+4Q
\]

and normalize \(C=0\) by

\[
P=r-\frac34r^2,
\qquad
Q=\frac14r^2(1-r).
\]

The characteristic field is

\[
X_C=(3r-2)^2\frac d{dr}.
\]

For the complete target-lift algebra

\[
\mathcal H_{\rm lift}=\mathbb Q+(P^3,PQ,Q^2),
\]

the filtration-order-minus-one contact leak has exact image

\[
r^2(3r-2)^3\mathbb Q[r].
\]

The equality follows from the generator restrictions and the Bezout identity

\[
-\frac{200}{3}\{P^3,C\}
-12(15r-22)\{PQ,C\}
=r^2(3r-2)^3.
\]

The forced source pole accounts for the smaller ideal

\[
r^2(3r-2)\mathbb Q[r],
\]

and every independent polynomial weighted-volume source symbol enlarges the
combined image to

\[
r^2(3r-2)^2\mathbb Q[r].
\]

Off-diagonal polar source terms do not enlarge this homogeneous image.  For
\(G=z^{-d}g(r)\), \(d\ge1\), their earliest negative layer is

\[
T_d(g)=-dU'(r)g-2U(r)g',
\qquad
U(r)=-\frac{(3r-2)^2}{16},
\]

whose leading coefficient on a degree-\(n\) polynomial is
\(9(n+d)/8\ne0\).  Descending from the largest polar offset removes every
finite homogeneous polar gauge difference.

The complete paired quotient is therefore

\[
\frac{\mathbb Q[r]}{r^2(3r-2)^2}
\cong
\frac{\mathbb Q[r]}{r^2}
\oplus
\frac{\mathbb Q[r]}{(3r-2)^2}.
\]

Its second summand is a two-dimensional ramification coinvariant.

## Reachability verdict

Put \(\tau=3r-2\).  On the local summand

\[
\mathbb Q[\tau]/(\tau^2),
\]

every contact-zero target leak is divisible by \(\tau^3\), while the
complete polynomial source image is divisible by \(\tau^2\).  Hence the
arbitrary coefficientwise-polynomial contact-zero backbone acts trivially
on both ramification jets.

The normalization is stationary at the ramification point:

\[
P'(2/3)=Q'(2/3)=0.
\]

It follows by the chain rule that every polynomial multiplier \(M(P,Q)\)
has zero first \(\tau\)-jet.  Its reachable image is the value line, and the
admissible control \(Q^2C\) spans that line because

\[
Q(2/3)^2=\frac1{729}.
\]

After quotienting by this control, the compiler returns

\[
\boxed{\dim\operatorname{coker}=1,
\qquad
\dim\operatorname{reachable\ coker}=0.}
\]

The surviving first-jet class remains unreachable under parameter transport:
Poisson brackets of polynomial Hamiltonians are polynomial, and polynomial
weighted-volume source fields are bracket-closed.  Target and source Magnus
coefficients consequently retain the same zero first-jet property at every
parameter order.

This local object differs from the earlier three-state principal-parts module
\(\mathcal J_{2/3}\).  That module realizes coefficient shift on a canonical
completed row.  The present object is an intrinsic two-jet cokernel after the
complete polynomial target and source symbol images, followed by a separate
family-reachability test.

## Verification and boundary

The deterministic Jacobian replay is
[`filtered_obstruction_compiler_jacobian_leak_symbol.py`](filtered_obstruction_compiler_jacobian_leak_symbol.py).
It checks the ideal generators, Bezout identity, exact-sequence ranks, sharp
source cost \(2w-5\), polar injectivity, local contact-zero action, and the
reachability certificate.  The focused compiler suite has twenty passing
tests.

The semantic primitive catalog contains the reachability compiler and recalls
it first for forcing-versus-cokernel queries.  The 29-query held-out
evaluation remains recall@5 \(=1.0\), MRR \(=0.891\).

The ramification coinvariant does not supply an unrestricted tail lower
bound because its surviving coordinate is unreachable.  The active residual
is the reachable value-line cancellation: compile the known \(Q^2C\) source
self-cascade modulo an arbitrary coefficientwise-polynomial contact-zero
backbone.  A lower theorem must keep its terminal response under every such
backbone; a construction must cancel it without creating an equal-or-higher
source or target logarithmic rate.
