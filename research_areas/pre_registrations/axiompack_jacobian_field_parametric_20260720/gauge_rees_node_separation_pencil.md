# Rees-node separation obstruction

**Status:** proof pencil after exact boundary orientation; before deterministic
replay and formalization

## Governing object

Use the diagonal Rees specialization

\[
s=\tau\varepsilon^2,\qquad
v=\frac{V}{\varepsilon},\qquad
t=\frac{T}{\varepsilon},
\]

and scale the two target coordinates by
\(\varepsilon^4,\varepsilon^6\).  If

\[
r=V\left(T-\frac32V\right),
\]

then the special-fiber family factors through the rank-one map

\[
f_\tau(r)=\bigl(p_\tau(r),q_\tau(r)\bigr),
\]

where

\[
p_\tau(r)=\tau r^3-3r^2,\qquad
q_\tau(r)=\frac34\tau r^4-2r^3.
\]

The owner of the obstruction is this parametrized boundary curve together
with its normalization map.  Compatibility is equality after a Hamiltonian
target velocity and an arbitrary source velocity.  The relevant equality
relation on the target is equality at two normalization points lying over
the same point of the curve.

## Eigenquestion

Can a coefficientwise-polynomial Hamiltonian series of target Rees slope
strictly below two generate the normal motion
\(\partial_\tau f_\tau\), modulo arbitrary source reparametrization?

Write

\[
K_\tau(P,Q)=
\sum_{n,i,j}k_{n,i,j}\tau^nP^iQ^j.
\]

The node substitution is

\[
P=-2\tau^{-2},\qquad Q=\tau^{-3}.
\]

It is defined as a generalized Laurent series whenever the support is
locally finite and bounded below under

\[
\nu_{\rm node}(\tau^nP^iQ^j)=n-2i-3j.
\]

In particular, it is defined if there are \(\delta>0\) and \(C\) such that

\[
4i+6j\le(2-\delta)n+C
\]

for every supported monomial.

## Boundary singularities

The derivatives satisfy

\[
p_\tau'(r)=3r(\tau r-2),\qquad
q_\tau'(r)=3r^2(\tau r-2)=r\,p_\tau'(r).
\]

Thus the normalization ramifies at \(r=0\) and \(r=2/\tau\).  At both
points the determinant of the second and third derivative vectors is
\(72\), so both are ordinary cusps.

The two further normalization points

\[
r_\pm=\frac{1\pm\sqrt3}{\tau}
\]

have the same target image:

\[
f_\tau(r_+)=f_\tau(r_-)
=\left(-\frac2{\tau^2},\frac1{\tau^3}\right).
\]

Their tangent slopes are \(r_+\) and \(r_-\), so the common image is an
ordinary node.

## Candidate theorem

There is no node-evaluable Hamiltonian series \(K_\tau\) and no source
coefficient \(a_\tau(r)\) satisfying

\[
\partial_\tau f_\tau
=X_{K_\tau}(f_\tau)+a_\tau(r)f_\tau'(r),
\qquad
X_K=(K_Q,-K_P).
\]

Consequently every node-boundary instantaneous Hamiltonian solution has

\[
\limsup_{n\to\infty}
\frac{
\max\{\,4i+6j:k_{n,i,j}\ne0\,\}
}{n}
\ge2.
\]

Since \(2i+3j\le3(i+j)\), this also gives the ordinary target-degree
consequence

\[
\limsup_{n\to\infty}
\frac{
\max\{\,i+j:k_{n,i,j}\ne0\,\}
}{n}
\ge\frac13.
\]

For a contact whose complete logarithm lies in one global subcritical
triangular Rees filtration, the same bound transfers to its logarithmic
velocity.  A tail-only limsup hypothesis is weaker: finitely many
supercritical noncommuting logarithmic coefficients can create infinitely
many critical `dexp` terms.  Removing or classifying that finite prefix is a
separate bridge to the previously defined asymptotic contact slope.

## Proof skeleton

Taking the determinant with \(f_\tau'\) kills every source-tangent term.
For a Hamiltonian field,

\[
\det(f_\tau',X_K(f_\tau))
=-\frac d{dr}K(f_\tau(r)).
\]

Direct calculation gives

\[
\det(f_\tau',\partial_\tau f_\tau)
=-\frac34r^5(\tau r-2).
\]

Therefore any solution must obey

\[
K_\tau(f_\tau(r))
=h_\tau(r)+c(\tau),
\qquad
h_\tau(r)=-\frac14r^6+\frac{3\tau}{28}r^7.
\]

At the two normalization points over the node,

\[
h_\tau(r_+)-h_\tau(r_-)
=\frac{72\sqrt3}{7\tau^6}\ne0.
\]

A node-evaluable target series has the same value at \(r_+\) and \(r_-\),
because both substitutions use the identical pair
\((-2\tau^{-2},\tau^{-3})\).  The additive constant cancels.  This is the
contradiction.

## Counterattacks and claim boundary

1. A source velocity need not descend to a function of \(r\).  If its
   complete Rees specialization is regular, it still enters through a
   multiple of \(f_\tau'\), so the determinant removes it.  A finite polar
   prefix can pass through the six vanishing Jacobian layers and contribute
   normally; see
   [`gauge_rees_node_polar_prefix_audit.md`](gauge_rees_node_polar_prefix_audit.md).
2. An unrestricted coefficientwise-polynomial target series need not be
   evaluable at the moving node.  Critical target support is forced only
   when the source Rees action is regular.  The exact pole-six source-only
   connection carries the same normal class with target Hamiltonian zero.
3. The conditional theorem uses the target filtration
   \(\deg_f(P,Q)=(4,6)\).  It gives only the displayed \(1/3\) lower bound
   for the earlier ordinary-degree contact metric; it does not prove that
   the ordinary symmetric slope equals two.
4. The theorem is a boundary consequence of a compatible formal contact
   only after the Rees specialization, polar-prefix regularity, and
   logarithmic-velocity transfer are checked against the exact normalized
   family.  Weighted divergence and the complete contact equation do not
   kill the polar class: the regular source-only connection satisfies both
   and spans \(\partial_\tau f_\tau\).
5. A limsup bound on the logarithmic tail does not control `dexp` by itself.
   For example, a finite noncommuting prefix can generate arbitrarily high
   iterated adjoints at critical Rees weight.  Thus the current theorem
   proves a weighted instantaneous-velocity obstruction.  It does not yet
   prove the \(1/3\) lower bound for \(\sigma_{\rm ct}\).

## Intended formal surface

The kernel endpoint should certify:

- the two cusp derivative factorizations;
- equality of the node images;
- nonzero separation of \(h_\tau\) on the two node branches after clearing
  the unit \(\tau\);
- the arithmetic implication from weighted slope below two to local
  finiteness of node evaluation.

The symbolic bridge separately binds the normalized family to
\(f_\tau\), the determinant identity, and the Rees support convention.
