# Fixed-rational weighted-profile cone

**Status:** exact negative-root/interlacing prefix through order forty-one;
all-order preservation remains open

## Eigenquestion

For the Wick-rotated symmetric logarithm

\[
W(e,\ell;P,Q)
=-\log\!\left(
e^{-eQ^2/2}e^{-(P^3+\ell Q^2)}e^{-eQ^2/2}
\right)(P,iQ),
\]

weighted homogeneity writes every odd coefficient uniquely as

\[
W_{2k-1}
=P^{k+2}F_k(u),
\qquad
u=\frac{Q^2}{P^3}.
\]

Apart from the known negative \(Q^2\) term in
\(F_1(u)=1-(e+\ell)u\), can the observed coefficientwise positivity of the
higher \(F_k\) be strengthened to an invariant profile cone that is
preserved by

\[
\partial_eW
=-Q^2+\sum_{m\ge1}
\frac{|B_{2m}|}{(2m)!}\operatorname{ad}_W^{2m}(Q^2)?
\]

The target is an all-order proof of the boundary inequality

\[
[Q^0]\operatorname{ad}_W^{2m}(Q^2)\succeq0
\]

for the actual correlated solution.  Positivity for arbitrary profiles is
already false.

## Exact profile algebra

Put \(x=Q/P^{3/2}\).  For weighted-homogeneous Hamiltonians

\[
H=P^a f(x),\qquad K=P^b g(x),
\]

the campaign bracket becomes

\[
\boxed{
[H,K]
=P^{a+b-5/2}
\left(bf'g-afg'\right).
}
\]

This compresses each two-variable homogeneous shell to a one-variable
profile.  In particular, the two generators obey

\[
(\operatorname{ad}_{P^3})^3(Q^2)=0,
\qquad
(\operatorname{ad}_{Q^2})^4(P^3)=0.
\]

Thus their generated algebra is a quotient of the positive rank-two
Kac--Moody algebra with generalized Cartan matrix

\[
\begin{pmatrix}2&-2\\-3&2\end{pmatrix}.
\]

No logarithmic-positivity theorem is inferred from that identification; it
only records the exact Serre envelope of the recurrence.

## First boundary inequalities

Write the even Hamiltonian as

\[
W=A(P)+B(P)Q^2+O(Q^4).
\]

Direct calculation gives

\[
\left.\operatorname{ad}_W^2(Q^2)\right|_{Q=0}
=2(A')^2,
\]

and

\[
\left.\operatorname{ad}_W^4(Q^2)\right|_{Q=0}
=16(A')^2\left(A'B'-BA''\right).
\]

The second factor is

\[
A'B'-BA''
=(A')^2\left(\frac{B}{A'}\right)'.
\]

Hence unrestricted coefficient positivity is insufficient even on the
boundary.  A viable correlated cone must control this Wronskian and its
higher analogues.

## Discriminating tests

1. Extract every exact \(F_k(u)\) through the current sparse replay depth
   and verify the profile bracket formula and the two Serre relations.
2. Test coefficient signs, root locations, and adjacent-profile
   interlacing after the specialization \((e,\ell)=(1,3)\).
3. Compute the boundary polynomials of
   \(\operatorname{ad}_W^{2m}(Q^2)\) separately by parameter order and
   identify the first Wronskian or Hankel inequality needed for their
   positivity.
4. Perturb one exact profile coefficient while preserving ordinary
   coefficient positivity.  If a boundary even-adjoint coefficient changes
   sign, record the missing correlation explicitly.
5. Promote only an inequality family that is closed under the
   \(e\)-differential recurrence and survives held-out exact orders.

## Success and kill conditions

The lane succeeds if a finite set of profile inequalities is proved
invariant and implies a nonzero positive boundary coefficient at every odd
order.

It is killed if an exact profile or boundary even-adjoint coefficient
becomes negative, or if the required inequalities proliferate with order
without a closed recurrence.  A longer positive prefix alone is not an
all-order result.

## Claim boundary

This is a discriminator for the prescribed rational cusp BCH
specialization.  Success would close that odd subsequence, not the
unrestricted coefficientwise-finite contact minimax.

## Outcome

The exact replay is
[`gauge_fixed_rational_profile_cone.py`](gauge_fixed_rational_profile_cone.py).
It verifies the profile bracket and both Serre relations, then evaluates the
complete bivariate symmetric BCH recursion at \((e,\ell)=(1,3)\).

Through logarithmic order forty-one:

1. every higher profile \(F_k\), \(2\le k\le21\), has positive
   coefficients;
2. every zero of every higher \(F_k\) is simple and negative, certified by
   rational Sturm isolating intervals;
3. consecutive higher profiles strictly interlace, including the steps at
   which the profile degree increases;
4. the first boundary Wronskian
   \(A'B'-BA''\) is coefficientwise nonnegative through the same parameter
   order; and
5. the complete bivariate boundary parts of
   \(\operatorname{ad}_W^{2m}(Q^2)\), for \(m=1,2,3,4\), are
   coefficientwise nonnegative through the same shell cap.

As an algebraic shadow of the interlacing, all thirty-nine adjacent
two-by-two coefficient minors available through order twenty-one are
strictly positive.  This is a finite total-positivity certificate expressed
entirely by rational inequalities, independent of root approximation.

There is also a parameter-uniform finite certificate through \(k=11\).
Every profile coefficient has the expected homogeneous amplitude degree.
After setting \(\ell=1\), every symbolic discriminant has strictly positive
coefficients and every adjacent resultant has coefficients of one nonzero
sign.  Homogeneity restores arbitrary \(e,\ell>0\).  The positive quadrant
is connected, so the exact negative roots and strict interlacing at
\((1,3)\) cannot change without a discriminant or adjacent resultant
vanishing.  Therefore the negative-root/interlacing statement holds for
all positive amplitudes through logarithmic order twenty-one.

The same discriminant sign check was separately extended through \(k=19\),
but the degree-seven computation becomes expensive and the complete
discriminant-plus-resultant replay is deliberately capped at \(k=11\).

The profile degrees advance in three residue classes, but none of those
subsequences satisfies a classical monic three-term recurrence on the
checked data.  A first-order differential transfer
\[
F_{k+1}=(au+b)F_k+(cu+d)F_k'
\]
also fails once the profile degree reaches three.  The new structure is
therefore a generalized Sturm/Pólya-frequency candidate rather than a
classical orthogonal-polynomial recurrence in disguise.

The negative-root pattern explains why the Wronskian is the correct
inequality carrier: interlacing is equivalent to a fixed Wronskian sign.
What remains is to show that the nonlinear even-adjoint differential
recurrence preserves the required proper-position chain.  The finite result
does not supply that preservation theorem.
